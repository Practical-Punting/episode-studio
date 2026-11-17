#!/usr/bin/env python3
"""The false-start check runs on every Gordon master straight after download (Jodie, 18 Nov 2026).

`repeated_words.py` (EP56's false start) ran on the two-way path only. These cases prove the
WIRING in the single-presenter engine; the detector itself is proved on EP56's real
transcripts by test_repeated_words.py.

  A. RealProvider.poll_heygen CALLS check_false_starts after trim_master_lead_in and before
     align_to_script (an AST walk of the calls, not a grep). CONTROL: the same walk on the
     same source with that one call removed must fail.
  B. a clean master -> PASS line; the real script is run, on the master, against
     docs/spoken-words.txt, writing its result beside the master.
  C. resume on the same master -> the stored result is read; the transcriber is NOT re-run.
  D. CONTROL — a repeat -> EngineFlag, naming the time and the words, in plain English (no
     paths, no JSON), with an outstanding ask recorded.
  E. the flag cleared the way the engine clears it (answer_pending_gates) -> the step goes
     through without listening again.
  F. a NEW master (a re-render) is checked afresh and asks again.
  G. CONTROL — the check cannot run (exit 2, no result) -> EngineFlag, never a silent pass.

    python engine/test_false_start_gate.py
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import providers as P  # noqa: E402

fails: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


# ── A. the call is really there, in the right place ─────────────────────────
def call_order(src: str) -> list[str]:
    tree = ast.parse(src)
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for fn in cls.body:
            if isinstance(fn, ast.FunctionDef) and fn.name == "poll_heygen":
                calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Name)]
                names = [c.func.id for c in sorted(calls, key=lambda c: (c.lineno, c.col_offset))]
                if "trim_master_lead_in" in names:      # the REAL provider's, not the mock's
                    return names
    return []


def wired(names: list[str]) -> bool:
    need = ("trim_master_lead_in", "check_false_starts", "align_to_script")
    if not all(n in names for n in need):
        return False
    i = [names.index(n) for n in need]
    return i == sorted(i)


print("A. poll_heygen calls the check between the trim and the alignment")
src = (HERE / "providers.py").read_text(encoding="utf-8")
check(wired(call_order(src)), "RealProvider.poll_heygen: trim -> check_false_starts -> align")
cut = "\n".join(l for l in src.splitlines() if "check_false_starts(d, master)" not in l)
check(cut != src and not wired(call_order(cut)),
      "CONTROL: the same source with that call removed is caught")
check((HERE / "repeated_words.py").is_file(), "the script it runs exists beside providers.py")


# ── a fake transcriber run: writes what repeated_words.py would write ───────
class FakeRun:
    def __init__(self, result: dict | None, rc: int):
        self.result, self.rc, self.calls = result, rc, []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if self.result is not None:
            pathlib.Path(cmd[cmd.index("--json") + 1]).write_text(json.dumps(self.result),
                                                                 encoding="utf-8")
        return type("R", (), {"returncode": self.rc, "stdout": "", "stderr": "boom"})()


CLEAN = {"ok": True, "run_n": 3, "stretches": 212, "repeats": []}
REPEAT = {"ok": False, "run_n": 3, "stretches": 213, "repeats": [
    {"at_s": 1.24, "text": "This is part three of a conversation that",
     "first_ngram": "this is part", "heard": 2, "in_script": 1}]}


MADE: list[pathlib.Path] = []


def episode() -> tuple[pathlib.Path, pathlib.Path]:
    d = pathlib.Path(tempfile.mkdtemp(prefix="fsgate-"))
    MADE.append(d)
    (d / "renders").mkdir()
    (d / "docs").mkdir()
    (d / "docs/spoken-words.txt").write_text("This is part three of a conversation.\n",
                                             encoding="utf-8")
    m = d / "renders/presenter-master.mp4"
    m.write_bytes(b"\0" * 1000)
    return d, m


print("B. a clean master")
d, m = episode()
run = FakeRun(CLEAN, 0)
line = P.check_false_starts(d, m, run=run)
check(line.startswith("false starts: PASS"), "returns the PASS line", line[:70])
cmd = run.calls[0] if run.calls else []
check(len(run.calls) == 1 and pathlib.Path(cmd[1]).name == "repeated_words.py"
      and cmd[2] == str(m) and cmd[3] == str(d / "docs/spoken-words.txt"),
      "runs repeated_words.py on the master against docs/spoken-words.txt")
check(pathlib.Path(cmd[cmd.index("--json") + 1]).parent == d / "renders",
      "the result is kept beside the master")

print("C. resume on the same master")
P.check_false_starts(d, m, run=run)
check(len(run.calls) == 1, "the transcriber is not run a second time")

print("D. CONTROL — a repeat stops the build")
d, m = episode()
run = FakeRun(REPEAT, 1)
msg = ""
try:
    P.check_false_starts(d, m, run=run)
except P.EngineFlag as e:
    msg = str(e)
check(bool(msg), "EngineFlag raised")
check("0:01.2" in msg and "This is part three of a conversation that" in msg,
      "names the time and the words", msg[:90].replace("\n", " "))
check(not any(t in msg for t in (".json", ".mp4", "renders", "\\", "repeated_words")),
      "plain English: no paths, files or JSON in the box")
check(any((d / "renders").glob(".asked-repeats-*")), "an outstanding ask is recorded")

print("E. the flag cleared the way the engine clears it")
P.answer_pending_gates(d)
try:
    line = P.check_false_starts(d, m, run=run)
    ok = "let it through" in line
except P.EngineFlag:
    ok, line = False, "flagged again"
check(ok and len(run.calls) == 1, "goes through, without listening again", line[:70])

print("F. a NEW master (a re-render) is checked afresh")
with open(m, "ab") as f:
    f.write(b"\0" * 10)
os.utime(m, None)
msg = ""
try:
    P.check_false_starts(d, m, run=run)
except P.EngineFlag as e:
    msg = str(e)
check(len(run.calls) == 2 and bool(msg), "re-run on the new take, and it asks again")

print("G. CONTROL — the check cannot run")
d, m = episode()
run = FakeRun(None, 2)
msg = ""
try:
    P.check_false_starts(d, m, run=run)
except P.EngineFlag as e:
    msg = str(e)
check("could not run the false-start check" in msg, "EngineFlag, never a silent pass")
check(not any(t in msg for t in (".json", ".mp4", "boom")),
      "the box gets plain words; the details go to the run log")

for tmp in MADE:                       # the test's own temp episodes, nothing else
    shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
sys.exit(1 if fails else 0)
