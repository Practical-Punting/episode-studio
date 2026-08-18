#!/usr/bin/env python3
"""run_suite.py — every suite in the studio, and it SAYS SO AS IT GOES.

    python engine/run_suite.py              # everything, both directories
    python engine/run_suite.py --engine     # engine/ only
    python engine/run_suite.py -k board     # only suites whose name contains "board"

TWO FAULTS THIS EXISTS FOR, BOTH PAID FOR ON 18 Aug 2026.

🔴 1. A LONG RUN THAT PRINTS NOTHING BREAKS OUR OWN LAW. The definitive suite ran **978
seconds in silence**. From outside, "still running" and "died quietly" are the same
picture — Jodie asked twice whether the machine was alive and nobody could tell her.
That is `anything that waits must say so`, which we fixed in the ENGINE and not in
OURSELVES. So this prints a line per suite as it finishes, with a running count and the
elapsed clock, and flushes every one.

    ⚠️ `test_title_card.py` TAKES ABOUT 555 SECONDS AND LOOKS HUNG. IT IS NOT.
    It renders real PNGs for a human to look at. It is named below so nobody kills it
    at eight minutes believing it has frozen — which is exactly what the silence
    invites.

🔴 2. THERE ARE SUITES OUTSIDE `engine/`, AND A GLOB THAT MISSES THEM REPORTS "ALL
GREEN" HAVING NEVER OPENED THEM. Eight live in `.claude/skills/pp-episode-production/
scripts/`, and one of them — `test_author_ebook.py` — is the ONLY suite covering the
e-book fidelity gate. A runner over `engine/test_*.py` said "80/80 green" while the file
that guards the standard was never run. `all green means nothing by itself`.

⚠️ AND THE TWO DIRECTORIES RUN **SEQUENTIALLY**, NEVER AT ONCE. Run together they
compete for CPU and the browser-driven suites time out — a red that is nothing but
contention, which is the worst kind because it sends someone hunting a fault that is
not there.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SKILLS = REPO / ".claude/skills/pp-episode-production/scripts"

# Suites that are legitimately slow, so a watcher knows the difference between slow and
# stuck. Measured, not guessed.
SLOW = {"test_title_card.py": 555, "test_cover_more_button.py": 127,
        "test_board_editor_browser.py": 104}

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass


def say(msg=""):
    print(msg, flush=True)          # flush: a buffered heartbeat is not a heartbeat


def run_dir(d: Path, tests: list[Path], t0: float, done: int, total: int):
    fails = []
    for t in tests:
        done += 1
        hint = f"  (~{SLOW[t.name]}s, this one is slow — not stuck)" if t.name in SLOW else ""
        say(f"  [{done}/{total}] {t.name} …{hint}")
        s = time.time()
        p = subprocess.run([sys.executable, str(t)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(d.parent),
                           timeout=1800)
        out = (p.stdout or "") + (p.stderr or "")
        lines = [ln for ln in out.strip().splitlines() if ln.strip()]
        tail = lines[-1][:100] if lines else "(no output)"
        mark = "ok  " if p.returncode == 0 else "FAIL"
        say(f"  [{done}/{total}] {mark} {t.name}  {time.time() - s:5.1f}s  {tail}"
            f"   · {time.time() - t0:.0f}s elapsed")
        if p.returncode:
            fails.append((t.name, p.returncode, out))
    return fails, done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", action="store_true", help="engine/ only")
    ap.add_argument("--skills", action="store_true", help="skills scripts only")
    ap.add_argument("-k", default="", help="only suites whose filename contains this")
    a = ap.parse_args(argv)

    groups = []
    if not a.skills:
        groups.append(("engine", HERE, sorted(HERE.glob("test_*.py"))))
    if not a.engine:
        groups.append(("skills", SKILLS, sorted(SKILLS.glob("test_*.py"))))
    if a.k:
        groups = [(n, d, [t for t in ts if a.k in t.name]) for n, d, ts in groups]

    total = sum(len(ts) for _n, _d, ts in groups)
    t0 = time.time()
    say(f"running {total} suite(s) across {len(groups)} directory(ies), SEQUENTIALLY "
        f"— they contend for CPU if run together.")
    fails, done = [], 0
    for name, d, tests in groups:
        say(f"\n── {name}: {len(tests)} suite(s) in {d} ──")
        f, done = run_dir(d, tests, t0, done, total)
        fails += f

    say(f"\n{total - len(fails)}/{total} suites green   ({time.time() - t0:.0f}s)")
    for name, rc, out in fails:
        say(f"\n{'=' * 78}\nFAILED: {name}  (exit {rc})\n{'=' * 78}")
        say("\n".join(out.strip().splitlines()[-40:]))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
