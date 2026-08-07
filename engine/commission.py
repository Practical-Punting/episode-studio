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
import sys
import time
from pathlib import Path


def _safe(s) -> str:
    """Flatten text that the engine's log stream cannot encode.

    🔴 FOUND BY RUNNING IT, NOT BY READING IT (6 Aug 2026, first real dry run).
    The relay had 74 green tests and died on its first live commission with
    `UnicodeEncodeError: 'charmap' codec can't encode '\\u2192'` — an ARROW, in
    text that came back from the writer.

    The engine's stdout is redirected to a log file, and on this machine that
    stream is cp1252. MODEL-DERIVED TEXT IS NOT ASCII: arrows, em dashes, curly
    quotes are all normal in prose. So any log line or halt message carrying the
    writer's own words could kill the step — at two in the morning, on EP17,
    with the cause looking nothing like the fault.

    Applied ONLY to text that came from the writer. Our own English is ASCII and
    stays exactly as written.
    """
    s = str(s)
    try:
        s.encode(sys.stdout.encoding or "utf-8")
        return s
    except (UnicodeEncodeError, LookupError, AttributeError, TypeError):
        return s.encode("ascii", "replace").decode("ascii")

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


# 🔴 THE WALLET ASSERTION — the guard that actually matters.
#
# ESTABLISHED 6 Aug 2026 by reading `claude auth status` from a spawn with every
# CLAUDE_CODE_* variable scrubbed: a commission runs on Jodie's Claude MAX
# SUBSCRIPTION (authMethod claude.ai, apiProvider firstParty). It is NOT a
# pay-as-you-go API balance. So what a commission costs is RATE LIMITS — Jodie's
# ability to work with Claude at nine o'clock at night — and not a bill.
#
#     ⚠️ AND THAT IS ONE SETTING AWAY FROM BEING FALSE.
#
# If ANTHROPIC_API_KEY is ever visible to the engine, or if anybody adds --bare
# (whose own help says "Anthropic auth is strictly ANTHROPIC_API_KEY or
# apiKeyHelper; OAuth and keychain are never read"), the CLI switches to API
# billing SILENTLY. --bare is documented as a SPEED flag: skip hooks, skip
# CLAUDE.md discovery. The person who reaches for it will be trying to make this
# faster and cheaper, in good faith, and will move it onto new money instead.
#
# THAT IS THE HEYGEN TRAP EXACTLY — exporting a key silently moved billing from
# plan credits at ~$6.60 an episode to a USD wallet at ~$21.48, invisibly. We are
# not repeating it in a mechanism designed to run unattended, three hundred times.
#
# A DOLLAR CAP WOULD NOT CATCH THIS. It caps the same notional number either way.
# Only asking WHICH WALLET catches it, so that is what this does — and it asks the
# CLI itself, every single time, because a check that ran this morning proves
# nothing about this afternoon.
WALLET_OK_METHODS = ("claude.ai",)
WALLET_OK_PROVIDERS = ("firstParty",)

# Names only. A value never appears in a log, a flag or an exception.
_BILLING_ENV_MARKERS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

_WALLET_REFUSAL = (
    "The studio was about to write part of this episode using a paid account "
    "instead of the subscription it normally uses, so it stopped before doing "
    "anything.\n"
    "Nothing was written and nothing was spent.\n"
    "This is a setting on the machine rather than anything to do with the "
    "episode. Retrying will not change it until someone has looked at the machine."
)


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

    ⚠️ `prompt` IS ACCEPTED AND DELIBERATELY NOT PLACED IN THE ARGV. See
    `strip_prompt_from_argv` below — it is kept in the signature so every existing
    test that asserts the scope keeps working and so the two stay in one place.
    """
    argv = [str(cli), "-p", prompt,
            "--output-format", "json",
            "--json-schema", json.dumps(VERDICT_SCHEMA),
            "--tools", ",".join(tools),
            # 🔴 --tools MAKES A TOOL AVAILABLE. IT DOES NOT GRANT PERMISSION.
            # Found on the first live dry run, 6 Aug 2026: the writer came back
            # saying "Write to output/ was declined, so here it is in full" and
            # dumped the copy into its answer as prose. Under `dontAsk` every
            # action is denied unless something allows it, so the commission
            # could READ its sources and could not WRITE its artefact.
            # The two flags are different questions and both must be answered.
            "--allowedTools", " ".join(tools),
            "--permission-mode", "dontAsk",     # hard-coded, see the docstring
            "--strict-mcp-config",              # no MCP servers, so no side doors
            "--max-budget-usd", str(budget_usd)]
    for d in add_dirs:
        argv += ["--add-dir", str(d)]
    if model:
        argv += ["--model", model]
    return argv


def strip_prompt_from_argv(argv: list[str], prompt: str) -> list[str]:
    """Take the brief OUT of the command line. It goes on STDIN instead.

    ══ WHY, AND IT IS MEASURED, NOT REASONED (6 Aug 2026) ══════════════════════
    `cli_path()` resolves to `claude.CMD` — a BATCH SHIM whose whole body is
    `"%dp0%\\node_modules\\...\\claude.exe" %*`. So **cmd.exe re-parses the entire
    command line**, and a 1,288-character, 15-line brief sitting in it does not
    survive. Everything AFTER the long element is lost with it.

    THREE RUNS, ONE EVENING, SAME INPUTS — the control is the important one:

      claude.CMD + brief in argv   -> NO artefact. Result is PROSE, not even JSON,
                                      and the writer says "the file write was
                                      declined". SIXTH reproduction.
      claude.CMD + brief on STDIN  -> artefact written, verdict conforms, status ok
      claude.exe + brief in argv   -> artefact written, verdict conforms, status ok

    THE FAILURE MODE EXPLAINS ITSELF: the control came back as PROSE. That means
    `--output-format json` never reached the CLI either — so it was not the writer
    refusing to write, it was `--allowedTools`, `--output-format` and
    `--json-schema` being eaten along with the brief. Five dry runs read that as
    "the writer declines to write its artefact"; it was a mangled command line.

    ⚠️ STDIN RATHER THAN THE .exe, AND THAT IS THE CHOICE WORTH RECORDING. Both
    fixes work. Calling `claude.exe` directly means hard-coding a path INSIDE
    node_modules, which moves when the CLI updates and is a name where an id
    should be. Taking the brief out of the argv fixes the CLASS: it works through
    a shim or without one, and it also removes any future collision with Windows'
    ~32k command-line limit as briefs grow.
    """
    out = list(argv)
    try:
        i = out.index("-p")
    except ValueError:
        return out
    if i + 1 < len(out) and out[i + 1] == prompt:
        del out[i + 1]                 # `-p` with no value == read the prompt from stdin
    return out


def assert_subscription_wallet(cli: Path, child_env: dict, *, runner, log=print) -> dict:
    """Refuse to commission unless this spawn resolves to the SUBSCRIPTION.

    Derived from `claude auth status`, which is machine-readable JSON and a
    LOCAL read — no API call, so the assertion is free and can run every time.
    Deriving it means a new authentication route cannot sneak past a list
    somebody maintains (CLAUDE.md fault #7): whatever the CLI says it resolved
    to is what gets checked.

    `child_env` is the EXACT environment the commission itself will run with, so
    the probe cannot measure one thing while the run uses another.

    Refuses and HALTS. It never warns and proceeds — a billing switch that
    reports itself and carries on is how the HeyGen one stayed invisible.
    """
    present = [k for k in _BILLING_ENV_MARKERS if child_env.get(k)]
    if present:
        raise CommissionHalt(
            _WALLET_REFUSAL,
            detail=("billing env var(s) visible to the child, so the CLI would "
                    f"bypass the subscription: {', '.join(present)} "
                    "(names only; values are never read or logged)"))
    try:
        r = runner([str(cli), "auth", "status"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=60, env=child_env)
        status = json.loads((r.stdout or "").strip())
    except Exception as e:
        raise CommissionHalt(
            _WALLET_REFUSAL,
            detail=("could not establish which account this spawn would use "
                    f"({type(e).__name__}). Refusing rather than assuming — an "
                    "unknown wallet is treated exactly like a paid one."))
    if not isinstance(status, dict) or not status.get("loggedIn"):
        raise CommissionHalt(
            _WALLET_REFUSAL,
            detail=_safe(f"auth status did not report a signed-in account: {str(status)[:300]}"))
    method, provider = status.get("authMethod"), status.get("apiProvider")
    if method not in WALLET_OK_METHODS or provider not in WALLET_OK_PROVIDERS:
        raise CommissionHalt(
            _WALLET_REFUSAL,
            detail=(f"wallet is authMethod={method!r} apiProvider={provider!r}; "
                    f"only {WALLET_OK_METHODS}/{WALLET_OK_PROVIDERS} is the "
                    "subscription. Anything else is new money."))
    log(f"    wallet checked: {status.get('subscriptionType') or '?'} "
        "subscription — this costs rate limits, not money")
    return status


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
            detail=_safe(f"unparseable envelope: {(r.stdout or '')[:800]}"))
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
            detail=_safe(f"is_error=true result={str(env.get('result'))[:800]}"))
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
            detail=_safe(f"verdict not an object: {str(env.get('result'))[:800]}"))

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
            detail=_safe("schema constraint breached: status=ok with "
                         f"unread_sources={unread!r}"))

    if status != "ok":
        # _safe() on the writer's own words: they reach BOTH the run log and the
        # operator's box, and an arrow in them must never be able to kill a step.
        saw = _safe(str(raw.get("what_i_saw") or "").strip()) or \
            "It did not say what it saw."
        could = [_safe(str(c).strip()) for c in (raw.get("what_it_could_be") or []) if str(c).strip()]
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
                             detail=_safe(f"writer halted: unread={unread!r}"))
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

    # ONE environment, computed once and used for BOTH the wallet probe and the
    # run itself — so the check cannot measure one thing while the commission
    # uses another. (One source of truth, or it drifts.)
    child_env = dict(os.environ)
    assert_subscription_wallet(cli, child_env, runner=runner, log=log)

    argv = strip_prompt_from_argv(
        build_argv(cli, prompt, add_dirs, tools, budget_usd, model), prompt)
    started = time.time()
    # ANYTHING THAT WAITS MUST SAY IT IS WAITING (CLAUDE.md fault #3): the START
    # of the work, not only its finish, and who it is waiting on.
    log(f"    commissioning {what} — a writer is working, up to {timeout}s, "
        f"capped at ${budget_usd:.2f}", flush=True)

    try:
        r = runner(argv, input=prompt, capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=timeout,
                   cwd=str(place), env=child_env)
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
        names = sorted({_safe(d.get("tool_name", "?")) for d in denials if isinstance(d, dict)})
        log(f"    (the writer was refused {len(denials)} action(s): "
            f"{', '.join(names)} - place scoping held)")
    log(f"    {what} written in {time.time() - started:.0f}s, "
        f"${float(env.get('total_cost_usd') or 0):.2f}, "
        f"{env.get('num_turns', '?')} turn(s)")

    verdict["_path"] = str(path)
    verdict["_cost_usd"] = float(env.get("total_cost_usd") or 0)
    return verdict


# ═══════════════════════════════════════════════════════════════════════════════
# THE BOUNDED, SELF-CORRECTING RETRY
#
# The first scratch run of the episode.json commission produced a good 67 KB file
# with ONE fault in it: a card's eyebrow carried a figure with no trace entry.
# preflight_cards said so precisely — it named the card, the key and what was
# missing — and the build halted a human with it.
#
#     A CHECKER THAT GOOD IS A SET OF INSTRUCTIONS. FEED IT BACK TO THE WRITER.
#
# 🚫 AND THE CONSTRAINT THAT SHAPES THE WHOLE THING: THE ENGINE STILL RUNS THE
# GATE. The obvious move is to give the writer the checker and let it iterate.
# That is the wrong move twice over — it needs a shell, which is scoped to
# nothing (Jodie's place-and-time rule), and it turns the acceptance test into
# the writer's own report. "I ran it and it passed" is a report, and this whole
# module exists because a report is not an artefact. So: the engine runs the
# gate, passes its OUTPUT back as text, and runs the gate again itself.
#
# ⚠️ THE GATE IS INJECTED, NOT REIMPLEMENTED. `gate` is a callable supplied by
# the caller and is THE SAME function the build halts on — not a copy of it
# living in a second file (fault #2, one source of truth or it drifts).
#
# SCOPE — NARROW ON PURPOSE. This retries GATE failures: the writer produced a
# file and the checks rejected it. A CommissionHalt — a mangled envelope, a
# timeout, a stale artefact, the wallet refusal — propagates immediately and
# unchanged, because commission() has already decided whether retrying helps and
# said so in words. Retrying a wallet refusal three times would be absurd.
_EXHAUSTED = (
    "The studio asked its writing assistant to draft {what}, checked the work, "
    "sent back what was wrong and asked again — {n} times in all. Something in it "
    "is still not right, so nothing has been built and nothing has been spent.\n"
    "It could be that this article needs something the studio's usual rules do not "
    "cover, or that the assistant is stuck on the same point and cannot get past "
    "it.\n"
    "Retrying will not fix this. This one is the studio's to sort out — it is not "
    "something to clear from the board."
)


def _repair_note(blockers) -> str:
    """The follow-up brief: THE CHECKER'S OWN WORDS, not a paraphrase of them.

    ⚠️ DELIBERATELY NOT PASSED THROUGH _safe(). This text goes to the CHILD on
    stdin, which is utf-8, and the blockers quote the ARTICLE — source sentences,
    figures, curly quotes, em dashes. Flattening those to ASCII here would hand
    the writer a corrupted version of the very sentences it has to reproduce
    character for character. _safe() is for OUR log stream, which is cp1252 on
    this machine, and it is applied there and only there.
    """
    lines = ["The studio's checks read what you wrote and rejected it. This is "
             "what they said, word for word:", ""]
    lines += [f"  - {b}" for b in blockers]
    lines += ["",
              "Fix exactly these and nothing else — each line names the thing it "
              "is about. Do not rewrite the parts nobody complained about.",
              "If one of these is wrong about the article, do NOT work around it: "
              "say so in what_i_saw and set status to halt."]
    return "\n".join(lines)


def commission_with_repair(*, attempt, gate, what: str, attempts: int = 3,
                           log=print) -> dict:
    """Commission, run the caller's gate, and give the writer its own faults back.

    `attempt(followup)` -> verdict. Supplied by the caller; `followup` is None on
        the first go and the checker's words on every one after it.
    `gate()` -> list of blocker strings. EMPTY MEANS PASS. It is the caller's
        real gate, so this cannot go stale against what the build actually runs.

    Returns the verdict of the attempt that PASSED THE GATE. Raises CommissionHalt
    when the attempts are used up — operator-shaped, no paths, no card names, no
    JSON; the checker's actual lines go to `.detail`, which is the run log's.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    blockers: list[str] = []
    for i in range(1, attempts + 1):
        if i > 1:
            # ANYTHING THAT WAITS MUST SAY IT IS WAITING (fault #3) — and say
            # WHY it is going round again, not merely that it is.
            log(f"    repair {i - 1} of {attempts - 1}: asking the writer to fix "
                f"{len(blockers)} thing(s) the studio's checks rejected", flush=True)
        verdict = attempt(_repair_note(blockers) if blockers else None)
        blockers = [str(b) for b in (gate() or [])]
        if not blockers:
            if i > 1:
                log(f"    the writer's own repair passed the studio's checks "
                    f"(attempt {i} of {attempts})", flush=True)
            return verdict
        log(f"    attempt {i} of {attempts} rejected by the studio's checks — "
            f"{len(blockers)} thing(s):", flush=True)
        for b in blockers:
            log(f"      x {_safe(b)}")          # OUR stream: flatten it (see above)
    raise CommissionHalt(
        _EXHAUSTED.format(what=what, n=attempts),
        detail=_safe(f"{attempts} attempt(s) all rejected by the gate; the last "
                     f"{len(blockers)} blocker(s) were: " + " | ".join(blockers)))
