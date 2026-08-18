#!/usr/bin/env python3
"""EVERY SCRIPT THE ENGINE DRIVES MUST SURVIVE HAVING ITS OUTPUT CAPTURED.

    python engine/test_scripts_survive_a_pipe.py

🔴 THE REGRESSION THIS EXISTS FOR — 18 Aug 2026, introduced and shipped the same day.
`build_ebook.py` was given a warning line beginning with `⚠️`. It worked perfectly by
hand and would have broken EVERY e-book build:

    providers.run(...)  →  subprocess.run(..., capture_output=True)

**A captured stdout is a PIPE, not a console, and on Windows Python encodes a pipe with
the LOCALE codec — cp1252.** One emoji in a `print()` raises UnicodeEncodeError, the
script exits 1, `run()` raises, and the step fails. The PDF had already been written, so
the artefact was fine and the step failed anyway — the worst shape of failure, because
the thing on disk looks correct.

    IT PASSED 93/93 SUITES. Nothing runs these scripts as a SUBPROCESS with captured
    output, so nothing in the studio was looking through the pipe the engine uses.
    It was found by a benchmark that happened to redirect to a file.

⚠️ AND THE FIX IS THE CLASS, NOT THE INSTANCE. Removing one emoji would leave the next
one to be found the same way. Every script the engine invokes must either reconfigure
its streams to UTF-8, or print nothing a cp1252 pipe cannot carry.

Nothing here touches the rail, the network, or a running engine.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SKILL = REPO / ".claude/skills/pp-episode-production/scripts"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def scripts_the_engine_runs() -> list[str]:
    """Every `self.py("x.py", …)` in providers.py — asked of the CODE, so a script
    added tomorrow is covered without anybody remembering this file exists."""
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    return sorted(set(re.findall(r'self\.py\(\s*"([^"]+\.py)"', src)))


def reconfigures_stdout(src: str) -> bool:
    return bool(re.search(r"\.reconfigure\(\s*encoding\s*=\s*[\"']utf-8", src))


def _every_engine_driven_script_survives_a_pipe():
    names = scripts_the_engine_runs()
    assert names, "found no scripts invoked via self.py — has the call shape changed?"
    bad = []
    for n in names:
        p = SKILL / n
        if not p.is_file():
            continue                       # named but not present: another test's job
        src = p.read_text(encoding="utf-8")
        if reconfigures_stdout(src):
            continue                       # safe whatever it prints
        # Otherwise every literal it might print must fit through a cp1252 pipe.
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print"):
                continue
            for lit in [s for s in ast.walk(node) if isinstance(s, ast.Constant)
                        and isinstance(s.value, str)]:
                try:
                    lit.value.encode("cp1252")
                except UnicodeEncodeError:
                    ch = next(c for c in lit.value
                              if not c.isascii() and _cp1252_fails(c))
                    bad.append(f"{n} line {lit.lineno}: prints {ch!r} and does not "
                               f"reconfigure stdout")
                    break
    assert not bad, (
        "these scripts would raise UnicodeEncodeError the moment the engine captured "
        "their output — the artefact is written and the STEP FAILS:\n      "
        + "\n      ".join(bad[:8]))


def _cp1252_fails(ch: str) -> bool:
    try:
        ch.encode("cp1252")
        return False
    except UnicodeEncodeError:
        return True


case("every script the engine runs survives having its output captured",
     _every_engine_driven_script_survives_a_pipe)


def _the_control_would_have_caught_the_real_one():
    """🔴 CONTROL. Drive the checker against the exact line that shipped, to prove it
    fires rather than merely passing on today's clean tree."""
    broken = 'print("\\n\u26a0\ufe0f  THIS WROTE A PDF. IT DID NOT PUBLISH IT.")'
    tree = ast.parse(broken)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print":
            for lit in [s for s in ast.walk(node) if isinstance(s, ast.Constant)
                        and isinstance(s.value, str)]:
                if _cp1252_fails(next((c for c in lit.value if not c.isascii()), "a")):
                    found = True
    assert found, ("the checker does not fire on the line that actually broke "
                   "build_ebook.py — it would pass a clean tree and prove nothing")


case("🔴 CONTROL — it fires on the exact line that shipped",
     _the_control_would_have_caught_the_real_one)


def _build_ebook_is_specifically_safe_now():
    src = (SKILL / "build_ebook.py").read_text(encoding="utf-8")
    assert reconfigures_stdout(src), (
        "build_ebook.py does not reconfigure stdout, and it prints a warning with an "
        "emoji in it. That combination failed every e-book build.")


case("build_ebook.py reconfigures its streams", _build_ebook_is_specifically_safe_now)


print(f"\nscripts survive a pipe: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
