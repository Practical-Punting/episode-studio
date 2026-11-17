#!/usr/bin/env python3
"""EP60, 18 Nov 2026 — a title that only squeezes onto one line takes two lines if two are larger.

"HORSE RACING BET TYPES EXPLAINED" (32 characters, 1359px at 100px) fitted ONE line only by
giving up the air, at exactly the 90px floor — while EP54's longer title failed one line, got
two, and came out at 100px. Jodie saw a 32-character title smaller than a 46-character one.
`choose_layout` now compares the squeezed one-line size with the two-line size at the
setup/payoff seam and takes the larger.

  A. the decision, from MEASURED widths (no browser): EP60 -> two lines at 155px.
  B. CONTROLS that must not change: a title that fits WITH the air stays one line (EP13's real
     width); EP19's real case still wraps; EP54's widest half still gives 100px on two lines;
     a tie stays on one line; nothing fits -> Halt.
  C. CONTROL — the OLD rule, written out here, gives EP60 one line at 90px (the fault).
  D. real Anton (Playwright + Google Fonts): EP60's real words measure to two lines at 155px.
  E. end to end: author_title_card.py on EP60's real episode.json (copied to a temp dir) writes
     a page with the <br> at the seam and font-size 155px; the one-line control (EP13-like
     words) writes nowrap with no <br>.

    python engine/test_title_two_lines.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import author_title_card as T  # noqa: E402

fails: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


# Widths at 100px measured in real Anton on 18 Nov 2026 (see D, which re-measures them live).
EP60_ONE, EP60_HALVES = 1359.06, [689.5, 645.1]

print("A. the decision")
r = T.choose_layout("HORSE RACING BET TYPES EXPLAINED", EP60_ONE, EP60_HALVES)
check(r[0] == 155 and r[2] is True, "EP60: two lines at 155px", str(r))

print("B. controls that must not change")
# EP13's 1061.8px in author_title_card's docstring is its width AT 150px -> 707.9px at 100px.
r = T.choose_layout("THE RATINGS GAME", 707.9, [480.0, 250.0])
check(r == (150, 707.9, False), "EP13 (fits with the air) stays ONE line at 150px", str(r))
r = T.choose_layout("10 SYSTEMS FOR ACTION-HUNGRY PUNTERS", 1423 / 0.9, [700.0, 800.0])
check(r[2] is True, "EP19 (fails one line outright) still wraps", str(r))
r = T.choose_layout("GETTING TOGETHER WITH THE INTERNATIONAL EXPERTS", 1500.0, [1060.6, 900.0])
check(r == (100, 1060.6, True), "EP54's widest half still gives 100px on two lines", str(r))
r = T.choose_layout("TIE", 1300.0, [1300.0, 10.0])
check(r[2] is False, "a tie stays on ONE line", str(r))
try:
    T.choose_layout("TOO LONG", 5000.0, [3000.0, 2000.0])
    check(False, "nothing fits -> Halt")
except T.Halt:
    check(True, "nothing fits -> Halt")


def old_rule(w100, w_lines):
    """The rule as it stood before 18 Nov 2026, verbatim in effect."""
    s = min(T.CAP, int(T.TARGET_FILL * T.BOX / w100 * 100.0 // T.STEP) * T.STEP)
    if s < T.FLOOR:
        s = min(T.CAP, int(T.BOX / w100 * 100.0 // T.STEP) * T.STEP)
    if s >= T.FLOOR:
        return s, w100, False
    widest = max(w_lines)
    return T._fit(widest), widest, True


print("C. CONTROL — the old rule reproduces the fault")
r = old_rule(EP60_ONE, EP60_HALVES)
check(r == (90, EP60_ONE, False), "old rule: EP60 on ONE line at 90px", str(r))

print("D. real Anton")
r = T.measure_size("HORSE RACING BET TYPES EXPLAINED", ["HORSE RACING BET", "TYPES EXPLAINED"])
check(r[0] == 155 and r[2] is True, "measured live: two lines at 155px", str(r))

print("E. end to end through author_title_card.py")
EPJ = Path(r"G:\My Drive\PP Videos\PP-EP60\docs\episode.json")
tmp = Path(tempfile.mkdtemp(prefix="titlecard-"))
try:
    src = json.loads(EPJ.read_text(encoding="utf-8"))
    (tmp / "a").mkdir()
    (tmp / "a/episode.json").write_text(json.dumps(src), encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPTS / "author_title_card.py"),
                        str(tmp / "a/episode.json"), str(tmp / "a")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    page = next((f.read_text(encoding="utf-8") for f in (tmp / "a").glob("*-title.html")), "")
    check(p.returncode == 0 and "font-size:155px" in page and "white-space:normal" in page
          and re.search(r'HORSE RACING BET</span><br>', page) is not None,
          "EP60's real episode.json -> 155px, two lines, break at the seam",
          (p.stderr or p.stdout).strip()[-120:])
    one = dict(src)
    one["cover"] = dict(src["cover"], title_setup="THE RATINGS", title_payoff="GAME")
    one["packaging"] = dict(src["packaging"], hook="THE RATINGS GAME")
    (tmp / "b").mkdir()
    (tmp / "b/episode.json").write_text(json.dumps(one), encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPTS / "author_title_card.py"),
                        str(tmp / "b/episode.json"), str(tmp / "b")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    page = next((f.read_text(encoding="utf-8") for f in (tmp / "b").glob("*-title.html")), "")
    check(p.returncode == 0 and "white-space:nowrap" in page and "</span><br>" not in page,
          "CONTROL: a title that fits with the air is still ONE line, no <br>",
          (p.stderr or p.stdout).strip()[-120:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
sys.exit(1 if fails else 0)
