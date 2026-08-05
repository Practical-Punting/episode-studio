"""commission.py — the engine commissions an AUTHOR, not an operator.

Three halts in the spine name "Claude Code writes this" as the thing that fills
them. They were never wired up, so the machine stops and waits for prose:
once for the script, once for the YouTube copy. Hugh can clear neither — no
amount of fixing checks removes a halt that needs WORDS WRITTEN, not a button
pressed. This module is the relay that closes them.

Design: docs/DESIGN-engine-commissions-the-script.md.
First user: RealProvider.save_youtube_copy — deliberately the CHEAPEST one.
Small artefact, an acceptance test that already exists (check_youtube_title),
and it sits at the END of the build, so a bad output costs a retry rather than
a render. Prove the mechanism where being wrong is cheap.

    🔴 THE TYPED VERDICT IS THE HEART OF THIS, NOT THE SUBPROCESS.

providers.py already spawns work in exactly this shape six times over. The
novelty is that a commissioned writer returns a SCHEMA-VALIDATED OBJECT rather
than prose, and that the engine refuses anything it cannot read.

    A WRITER THAT COULD NOT READ A SOURCE MUST BE UNABLE TO RETURN `ok`.

That is a schema constraint AND a check in this file — the difference between
impossible and unlikely. It is enforced twice on purpose: the schema constrains
what the model may EMIT, and _verdict_or_halt() constrains what the engine will
ACCEPT. A schema change, a CLI version bump or a model quirk cannot quietly
turn the guarantee off.

⚠️ AND THE ONE THIS FILE EXISTS TO STOP (CLAUDE.md fault #1):
    A VERDICT OF `ok` IS NOT EVIDENCE THAT A FILE WAS WRITTEN.
The verdict is a report; the artefact is the file on disk. So a commission is
only a pass when the artefact EXISTS and its mtime is LATER THAN THE RUN THAT
CLAIMED TO WRITE IT. A stale file left by an earlier attempt is exactly what
the --force trap taught us to expect: a correct fix that looks like a failed
one, and a failed one that looks like a pass.

SCOPE — a PLACE and a TIME, never a command prefix (Jodie's standing rule):
    PLACE   cwd = the episode folder; --add-dir for the standards it must read
    TIME    one process per commission, spawned and dead — no standing grant
    TOOLS   no Bash, ever. No WebFetch either — see §4a of the design: the
            ENGINE captures the source, the writer reads local files only.
    MONEY   --max-budget-usd, a hard cap per run
    MODE    --permission-mode dontAsk, deny-by-default, no prompt

There is deliberately NO permission-mode parameter on commission(). The mode is
hard-coded, so no call site can pass bypassPermissions by accident. A guard that
cannot be reached beats a guard someone must remember not to disable.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

# The five fields are CLAUDE.md fault #6's template made mandatory: say what you
# saw · list what it could be, ASSERTING NONE · say plainly whether a retry helps.
# A commissioned writer physically cannot return a halt in the shape that misled
# Jodie on EP15 ("this is not a missing file, not a stale template, the content
# is simply too long" — a cause nobody had established, printed above its own
# disproof).
VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["ok", "halt"],
            "description": "ok only if the work is complete AND every source was read.",
        },
        "what_i_saw": {
            "type": "string",
            "description": (
                "Plain English, for a person who has never seen this code. "
                "Observation only. No file paths, no filenames, no code, no JSON."
            ),
        },
        "what_it_could_be": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Possible causes. ASSERT NONE of them. Empty when status is ok.",
        },
        "does_retry_help": {
            "type": "boolean",
            "description": "Would running this again plausibly succeed?",
        },
        "unread_sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Anything you were given and could NOT read — including IMAGES. "
                "If this is not empty, status MUST be halt."
            ),
        },
    },
    "required": ["status", "what_i_saw", "what_it_could_be",
                 "does_retry_help", "unread_sources"],
    "additionalProperties": False,
}

# No Bash. No WebFetch. See the module docstring.
DEFAULT_TOOLS = ("Read", "Write", "Edit", "Glob", "Grep")

# Filesystem clock granularity, and the G: virtual filesystem, are both sloppier
# than a strict comparison allows. 5s is loose enough not to cry wolf and tight
# enough to catch what it is for: a file left behind by an EARLIER attempt, which
# is minutes or hours old, never five seconds.
FRESH_TOLERANCE_SECS = 5.0


class CommissionHalt(Exception):
    """A commission that did not produce a trustworthy artefact.

    `.message` is ALREADY operator-shaped — plain English, no paths, no
    filenames, no JSON, no stack trace (docs/PP-operator-box-rule.md).
    `.detail` is for the RUN LOG only.

    They are different readers and the same text cannot serve both, which is
    why this carries two strings instead of one.
    """

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


def cli_path() -> Path | None:
    """Where the Claude Code CLI is, or None. Env first, then PATH, then the
    known npm location on this machine."""
    env = os.environ.get("CLAUDE_CLI")
    if env:
        p = Path(env)
        return p if p.is_file() else None
    found = shutil.which("claude")
    if found:
        return Path(found)
    fallback = Path(os.path.expanduser(r"~\AppData\Roaming\npm\claude.cmd"))
    return fallback if fallback.is_file() else None


def build_argv(cli: Path, prompt: str, add_dirs, tools, budget_usd, model) -> list[str]:
    """The exact command line, built in one place so a test can assert the scope.

    Separated from commission() precisely so the PLACE-and-TIME claim is
    testable without spawning anything.
    """
    argv = [str(cli), "-p", prompt,
            "--output-format", "json",
            "--json-schema", json.dumps(VERDICT_SCHEMA),
            "--tools", ",".join(tools),
            "--permission-mode", "dontAsk",     # hard-coded, see the docstring
            "--strict-mcp-config",              # no MCP servers, so no side doors
            "--max-budget-usd", str(budget_usd)]
    for d in add_dirs:
        argv += ["--add-dir", str(d)]
    if model:
        argv += ["--model", model]
    return argv


def _envelope_or_halt(r, what: str) -> dict:
    """The CLI's own JSON wrapper. Unreadable is a HALT, never a pass."""
    if r.returncode and not (r.stdout or "").strip():
        raise CommissionHalt(
            f"The studio asked its writing assistant to draft {what} and the "
            "assistant stopped without answering. Nothing was saved.\n"
            "It could be that the assistant is not signed in on this machine, "
            "or that it was interrupted. Neither of those is something the "
            "episode can fix.\n"
            "Retrying is worth one attempt; if it stops again, the machine "
            "needs a look rather than the episode.",
            detail=f"exit={r.returncode} stderr={(r.stderr or '').strip()[-800:]}")
    try:
        env = json.loads((r.stdout or "").strip())
    except (ValueError, TypeError):
        raise CommissionHalt(
            f"The studio asked its writing assistant to draft {what} and got an "
            "answer it could not read. Nothing was saved.\n"
            "It could be that the assistant returned a message instead of an "
            "answer, or that its version has changed.\n"
            "Retrying is worth one attempt.",
            detail=f"unparseable envelope: {(r.stdout or '')[:800]}")
    if not isinstance(env, dict):
        raise CommissionHalt(
            f"The studio asked its writing assistant to draft {what} and got an "
            "answer in an unexpected shape. Nothing was saved.\n"
            "It could be a change in the assistant, or an interrupted run.\n"
            "Retrying is worth one attempt.",
            detail=f"envelope was {type(env).__name__}, not an object")
    if env.get("is_error"):
        raise CommissionHalt(
            f"The studio's writing assistant could not finish drafting {what}. "
            "Nothing was saved.\n"
            "It could be that it ran out of its allowance for this job, or that "
            "it hit a problem partway through.\n"
            "Retrying is worth one attempt.",
            detail=f"is_error=true result={str(env.get('result'))[:800]}")
    return env


def _verdict_or_halt(env: dict, what: str) -> dict:
    """The typed verdict, and the constraint that makes it mean something."""
    raw = env.get("result")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = None
    if not isinstance(raw, dict):
        raise CommissionHalt(
            f"The studio's writing assistant answered about {what} without saying "
            "whether the job was finished. Nothing was saved, because an answer "
            "the studio cannot check is not an answer.\n"
            "It could be a change in the assistant, or a run that was cut short.\n"
            "Retrying is worth one attempt.",
            detail=f"verdict not an object: {str(env.get('result'))[:800]}")

    missing = [k for k in VERDICT_SCHEMA["required"] if k not in raw]
    if missing:
        raise CommissionHalt(
            f"The studio's writing assistant gave an incomplete answer about "
            f"{what}. Nothing was saved.\n"
            "It could be a change in the assistant, or a run that was cut short.\n"
            "Retrying is worth one attempt.",
            detail=f"verdict missing keys: {', '.join(missing)}")

    unread = raw.get("unread_sources") or []
    status = raw.get("status")

    # 🔴 THE CONSTRAINT. Enforced here as well as in the schema, because the
    # schema binds what the model may EMIT and this binds what the engine will
    # ACCEPT — and only the second one survives a schema change.
    if unread and status == "ok":
        raise CommissionHalt(
            f"The studio's writing assistant said {what} was finished, and also "
            "said there was part of the source material it could not read. The "
            "studio does not accept both of those at once, so nothing was saved.\n"
            "It could be that part of the article is a picture rather than words, "
            "or that something it was given would not open.\n"
            "Retrying will not help. The source material needs a look.",
            detail=f"schema constraint breached: status=ok with "
                   f"unread_sources={unread!r}")

    if status != "ok":
        saw = str(raw.get("what_i_saw") or "").strip() or \
            "It did not say what it saw."
        could = [str(c).strip() for c in (raw.get("what_it_could_be") or []) if str(c).strip()]
        retry = bool(raw.get("does_retry_help"))
        lines = [f"The studio's writing assistant stopped rather than finish "
                 f"{what}, and this is what it said:", "", saw]
        if unread:
            lines += ["", "It could not read part of the source material."]
        if could:
            lines += ["", "It offered these as possibilities, without settling on any:"]
            lines += [f"  · {c}" for c in could]
        lines += ["", "Retrying is worth one attempt." if retry
                  else "Retrying will not fix this."]
        raise CommissionHalt("\n".join(lines),
                             detail=f"writer halted: unread={unread!r}")
    return raw


def _artefact_or_halt(find, started: float, what: str) -> Path:
    """🔴 THE VERDICT IS A REPORT. THE ARTEFACT IS THE FILE ON DISK.

    `find` is supplied by the CALLER and is the SAME lookup the caller's own
    checker uses — so this cannot go stale against it, and there is no second
    list of filenames for anyone to maintain (CLAUDE.md fault #7).
    """
    try:
        path = find()
    except Exception as e:                       # a broken lookup is not a pass
        raise CommissionHalt(
            f"The studio could not check whether {what} had actually been "
            "written. Nothing is being treated as finished.\n"
            "It could be that the episode's folder is not reachable.\n"
            "Retrying is worth one attempt.",
            detail=f"artefact lookup raised: {type(e).__name__}: {e}")
    if not path or not Path(path).is_file():
        raise CommissionHalt(
            f"The studio's writing assistant reported that {what} was finished, "
            "but no file was written. Nothing is being treated as finished.\n"
            "It could be that it wrote to somewhere unexpected, or that it "
            "described the work instead of doing it.\n"
            "Retrying is worth one attempt.",
            detail="verdict ok, artefact absent")
    path = Path(path)
    age = path.stat().st_mtime - started
    if age < -FRESH_TOLERANCE_SECS:
        raise CommissionHalt(
            f"The studio's writing assistant reported that {what} was finished, "
            "but the only file there was written before this attempt started. "
            "Nothing is being treated as finished.\n"
            "It could be that it left an earlier draft in place rather than "
            "writing a new one.\n"
            "Retrying will not fix this on its own — the old draft needs "
            "clearing first.",
            detail=f"stale artefact: mtime is {abs(age):.0f}s older than the run")
    return path


def commission(*, prompt: str, place: Path, find_artefact, what: str,
               add_dirs=(), tools=DEFAULT_TOOLS, budget_usd: float = 5.0,
               timeout: int = 900, model: str | None = None,
               runner=subprocess.run, log=print) -> dict:
    """Commission an author. Return the verdict; raise CommissionHalt otherwise.

    `find_artefact` is a zero-argument callable returning the produced file (or
    None). It is REQUIRED: a commission with nothing to check is a commission
    that trusts its own report.

    `runner` and `log` are injected so the whole mechanism is testable without
    spawning a process or writing to a real log.
    """
    cli = cli_path()
    if cli is None:
        raise CommissionHalt(
            f"The studio could not find the writing assistant it uses to draft "
            f"{what}. Nothing was written and nothing was spent.\n"
            "This is a setup problem on the machine rather than a problem with "
            "the episode.\n"
            "Retrying will not fix it until someone has looked at the machine.",
            detail="claude CLI not found (CLAUDE_CLI, PATH, npm fallback)")

    argv = build_argv(cli, prompt, add_dirs, tools, budget_usd, model)
    started = time.time()
    # ANYTHING THAT WAITS MUST SAY IT IS WAITING (CLAUDE.md fault #3): the START
    # of the work, not only its finish, and who it is waiting on.
    log(f"    commissioning {what} — a writer is working, up to {timeout}s, "
        f"capped at ${budget_usd:.2f}", flush=True)

    try:
        r = runner(argv, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=timeout, cwd=str(place))
    except subprocess.TimeoutExpired:
        raise CommissionHalt(
            f"The studio's writing assistant was asked to draft {what} and did "
            "not finish in the time allowed. Nothing was saved.\n"
            "It could be that the job was larger than expected, or that the "
            "assistant stalled.\n"
            "Retrying is worth one attempt.",
            detail=f"timeout after {timeout}s")

    env = _envelope_or_halt(r, what)
    verdict = _verdict_or_halt(env, what)
    path = _artefact_or_halt(find_artefact, started, what)

    # The run log gets the machine-readable facts. The operator's box never does.
    denials = env.get("permission_denials") or []
    if denials:
        names = sorted({d.get("tool_name", "?") for d in denials if isinstance(d, dict)})
        log(f"    (the writer was refused {len(denials)} action(s): "
            f"{', '.join(names)} — place scoping held)")
    log(f"    {what} written in {time.time() - started:.0f}s, "
        f"${float(env.get('total_cost_usd') or 0):.2f}, "
        f"{env.get('num_turns', '?')} turn(s)")

    verdict["_path"] = str(path)
    verdict["_cost_usd"] = float(env.get("total_cost_usd") or 0)
    return verdict
