"""test_commission.py — the cases that prove the commission relay.

"ALL GREEN" MEANS NOTHING UNLESS THE SUITE COVERS WHAT YOU CHANGED (CLAUDE.md
fault #4). So every case here names the fault it stands against, and the two
that matter most are the ones a green suite would otherwise never mention:

    ok_but_no_artefact          — the verdict is a REPORT; the file is the TRUTH
    unread_sources_with_ok      — the constraint the whole design rests on

Run: python engine/test_commission.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import commission as C

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def envelope(result, *, is_error=False, denials=None, cost=0.5, turns=3):
    return json.dumps({"is_error": is_error, "result": result, "num_turns": turns,
                       "stop_reason": "end_turn", "total_cost_usd": cost,
                       "permission_denials": denials or []})


def verdict(status="ok", unread=None, saw="All good.", could=None, retry=False):
    return json.dumps({"status": status, "what_i_saw": saw,
                       "what_it_could_be": could or [], "does_retry_help": retry,
                       "unread_sources": unread or []})


class R:
    """A stand-in for subprocess.run's CompletedProcess."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def runner_returning(stdout, stderr="", returncode=0):
    def run(argv, **kw):
        run.argv, run.kw = argv, kw
        return R(stdout, stderr, returncode)
    return run


def quiet(*a, **k):
    pass


def run_commission(tmp, stdout, *, find=None, returncode=0, runner=None, **kw):
    art = tmp / "output.txt"

    def default_find():
        return art if art.is_file() else None

    return C.commission(
        prompt="write it", place=tmp, what="the YouTube words",
        find_artefact=find or default_find,
        runner=runner or runner_returning(stdout, returncode=returncode),
        log=quiet, **kw)


def halts(fn) -> C.CommissionHalt | None:
    try:
        fn()
    except C.CommissionHalt as e:
        return e
    return None


def main():
    tmp = Path(tempfile.mkdtemp(prefix="pp-commission-"))
    os.environ["CLAUDE_CLI"] = str(tmp / "claude.cmd")
    (tmp / "claude.cmd").write_text("rem stub\n", encoding="utf-8")

    print("\n-- the happy path, so the rest means something --")
    art = tmp / "output.txt"
    art.write_text("PP-EP16 ...\n", encoding="utf-8")
    v = run_commission(tmp, envelope(verdict()))
    check("a good verdict with a fresh artefact returns the verdict",
          v.get("status") == "ok" and v.get("_path") == str(art))
    check("the cost is carried back for the run log", v.get("_cost_usd") == 0.5)

    print("\n-- fault #1: the verdict is a proxy; the ARTEFACT is the truth --")
    e = halts(lambda: run_commission(tmp, envelope(verdict()), find=lambda: None))
    check("ok with NO artefact is a halt, not a pass", e is not None)
    check("  and it says nothing was written",
          e and "no file was written" in e.message)

    stale = tmp / "stale.txt"
    stale.write_text("old draft\n", encoding="utf-8")
    os.utime(stale, (time.time() - 3600, time.time() - 3600))
    e = halts(lambda: run_commission(tmp, envelope(verdict()), find=lambda: stale))
    check("ok with a STALE artefact is a halt (the --force trap's shape)",
          e is not None)
    check("  and it says a retry alone will not fix it",
          e and "Retrying will not fix this on its own" in e.message)

    print("\n-- the constraint the design rests on --")
    e = halts(lambda: run_commission(
        tmp, envelope(verdict(status="ok", unread=["a table that is a picture"]))))
    check("unread_sources + status ok is FORCED to halt", e is not None)
    check("  and a retry is explicitly refused",
          e and "Retrying will not help" in e.message)
    check("  and the reason is in the run log, not the operator's box",
          e and "unread_sources" in e.detail and "unread_sources" not in e.message)

    print("\n-- an unreadable answer is a halt, never a pass --")
    for label, out, rc in [
        ("unparseable envelope", "this is not json", 0),
        ("envelope is not an object", json.dumps([1, 2, 3]), 0),
        ("CLI errored with no output", "", 1),
        ("is_error envelope", envelope("boom", is_error=True), 0),
        ("verdict is not an object", envelope("just some prose"), 0),
        ("verdict missing a required key",
         envelope(json.dumps({"status": "ok", "what_i_saw": "x"})), 0),
    ]:
        e = halts(lambda o=out, r=rc: run_commission(tmp, o, returncode=r))
        check(f"{label} -> halt", e is not None)

    print("\n-- a timeout says so, and says nothing was saved --")
    def timing_out(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout", 1))
    e = halts(lambda: run_commission(tmp, "", runner=timing_out))
    check("a timeout is a halt", e is not None)
    check("  and it says nothing was saved", e and "Nothing was saved" in e.message)

    print("\n-- fault #6: the writer's own halt is relayed in the right shape --")
    e = halts(lambda: run_commission(tmp, envelope(verdict(
        status="halt", saw="The article's two tables are pictures.",
        could=["the page stores them as images", "the transcription dropped them"],
        retry=False))))
    check("a writer halt is relayed", e is not None)
    check("  it quotes what the writer SAW",
          e and "two tables are pictures" in e.message)
    check("  it lists causes WITHOUT asserting one",
          e and "without settling on any" in e.message)
    check("  it says plainly that a retry will not help",
          e and "Retrying will not fix this." in e.message)

    print("\n-- the operator's box rule, applied to EVERY halt this file can raise --")
    banned = [".py", ".json", ".txt", ".md", "/", "\\", "{", "}", "Traceback",
              "unread_sources", "status=", "exit=", "stderr"]
    cases = [
        lambda: run_commission(tmp, "not json"),
        lambda: run_commission(tmp, "", returncode=1),
        lambda: run_commission(tmp, envelope("boom", is_error=True)),
        lambda: run_commission(tmp, envelope("prose")),
        lambda: run_commission(tmp, envelope(verdict(status="ok", unread=["x"]))),
        lambda: run_commission(tmp, envelope(verdict()), find=lambda: None),
        lambda: run_commission(tmp, envelope(verdict()), find=lambda: stale),
        lambda: run_commission(tmp, "", runner=timing_out),
    ]
    bad = []
    for i, c in enumerate(cases):
        e = halts(c)
        if not e:
            bad.append(f"case {i} did not halt")
            continue
        for b in banned:
            if b in e.message:
                bad.append(f"case {i} leaked {b!r}")
    check("no halt message carries a path, a filename, JSON, a field name or a trace",
          not bad, "; ".join(bad[:4]))
    check("every halt still carries maintainer detail somewhere",
          all((h := halts(c)) is not None and h.detail for c in cases))

    print("\n-- a broken artefact lookup is a halt, not an exception --")
    def boom():
        raise OSError("drive not reachable")
    e = halts(lambda: run_commission(tmp, envelope(verdict()), find=boom))
    check("a lookup that raises becomes a halt", e is not None)
    check("  and the drive error goes to the log, not the box",
          e and "drive not reachable" in e.detail
          and "drive not reachable" not in e.message)

    print("\n-- the scope is a PLACE and a TIME, asserted on the real command line --")
    run = runner_returning(envelope(verdict()))
    art.write_text("fresh\n", encoding="utf-8")
    C.commission(prompt="p", place=tmp, what="the YouTube words",
                 find_artefact=lambda: art, runner=run, log=quiet,
                 add_dirs=[tmp / "docs"], budget_usd=3.0, timeout=42)
    argv = run.argv
    check("the working directory is the place, not the repo", run.kw.get("cwd") == str(tmp))
    check("a time limit is always passed", run.kw.get("timeout") == 42)
    check("the permission mode is dontAsk",
          "--permission-mode" in argv and argv[argv.index("--permission-mode") + 1] == "dontAsk")
    check("bypassPermissions appears NOWHERE", "bypassPermissions" not in " ".join(argv))
    check("--dangerously-skip-permissions appears NOWHERE",
          "dangerously" not in " ".join(argv))
    tools = argv[argv.index("--tools") + 1]
    check("Bash is NOT in the tool list", "Bash" not in tools)
    check("WebFetch is NOT in the tool list (design 4a: no network)", "WebFetch" not in tools)
    check("Read and Write ARE in the tool list", "Read" in tools and "Write" in tools)
    check("a hard money cap is always passed",
          "--max-budget-usd" in argv and argv[argv.index("--max-budget-usd") + 1] == "3.0")
    check("MCP servers are excluded", "--strict-mcp-config" in argv)
    check("the verdict schema is passed to the CLI", "--json-schema" in argv)
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    check("the schema requires unread_sources",
          "unread_sources" in schema.get("required", []))
    check("the schema forbids extra fields", schema.get("additionalProperties") is False)
    check("the schema allows only ok or halt",
          schema["properties"]["status"]["enum"] == ["ok", "halt"])
    check("add_dirs are passed through", "--add-dir" in argv)

    print("\n-- there is no way to ask for a weaker permission mode --")
    import inspect
    params = inspect.signature(C.commission).parameters
    check("commission() takes no permission-mode parameter at all",
          not any("permission" in p for p in params))

    print("\n-- a refused action is logged, and never shown to the operator --")
    lines = []
    C.commission(prompt="p", place=tmp, what="the YouTube words",
                 find_artefact=lambda: art, log=lambda *a, **k: lines.append(a[0]),
                 runner=runner_returning(envelope(
                     verdict(), denials=[{"tool_name": "Read",
                                          "tool_input": {"file_path": "C:/secret"}}])))
    check("a permission denial reaches the run log",
          any("refused" in ln for ln in lines))
    check("  and the run log says the scoping held",
          any("place scoping held" in ln for ln in lines))
    check("the commission announces it is WAITING before it waits",
          any("a writer is working" in ln for ln in lines))

    print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} green")
    if FAIL:
        print("FAILED:")
        for f in FAIL:
            print("  - " + f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
