#!/usr/bin/env python3
"""EP53 — THE GATE COULD NOT SAY "SIX POINT FIVE FURLONGS" OR "TWO AND THREE-QUARTER".

    python engine/test_unit_decimal_and_mixed_fraction.py

EP53 "Basic Mistakes (Part 5)" burned all three script attempts on 30 Sep 2026. The
article prints Quinn's "up close" standards as "Sprints to 6.5f (1300m) 2 3/4 lengths
... 8.5f (1700m) and longer 4 3/4 lengths". The script said them aloud and was told
it invented "six point five", "eight point five" and "three quarter". The writer
refused to strip the figures. IT WAS RIGHT, three times.

  (a) A UNIT AFTER A DECIMAL. The furlong rule ran on the whole part only, so `6.5f`
      folded to "six.five furlongs" and "six point five furlongs" matched nothing.
  (b) A MIXED NUMBER. `2 3/4` folded to "two three quarters" — no "and" — and only
      ever in the plural, while a fraction before a noun is said "three-quarter".
  (c) AND THE HOLE THE FIX HAD TO CLOSE. The reader split "five and three quarter" at
      the "and", so a made-up mixed number passed if both halves occur anywhere.

🔒 Every "still blocks" case below is there to prove the gate is not wider.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import script_fidelity as F                                            # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))
PASS, FAIL = [], []
EP = 53                       # the episode this file is about, as a NUMBER


def capture(n: int):
    hits = sorted((PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    return hits[0].read_text(encoding="utf-8") if hits else None


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


CAP = """# A DISTANCE-STANDARDS FIXTURE

---- ARTICLE TEXT BEGINS ----

# BASIC MISTAKES (TEST FIXTURE)

The up close standard varies with the distance, ie., Sprints to 6.5f (1300m)
2 3/4 lengths 7f and 1 Mile (1400m and 1600m) 3 3/4 lengths 8.5f (1700m) and
longer 4 3/4 lengths. A 3yo filly beat the 2yo's. Five horses ran.

---- ARTICLE TEXT ENDS ----
"""


def says(phrase):
    return F.check("Gordon says " + phrase + " here.", CAP, "")


print("\n-- (a) a decimal with a unit letter on it --")
check("🔴 'six point five furlongs' — the article prints 6.5f — PASSES",
      says("sprints up to six point five furlongs") == [], str(says("six point five furlongs")))
check("🔴 'eight point five furlongs' — the article prints 8.5f — PASSES",
      says("eight point five furlongs and longer") == [])
check("  the whole-number unit reading is unchanged ('seven furlongs')",
      says("seven furlongs") == [])

print("\n-- (b) a mixed number, said with 'and', singular or plural --")
for p in ("two and three-quarter lengths", "three and three quarter lengths",
          "four and three quarters lengths"):
    check(f"🔴 {p!r} passes", says(p) == [], str(says(p)))

print("\n-- ages in any case --")
check("  'a three-year-old filly' — the article prints 3yo — passes",
      says("a three-year-old filly") == [])
check("  'the two-year-olds' — the article prints 2yo's — passes",
      says("beat the two-year-olds") == [])

print("\n-- 🔒 AND THE GUARD IS UNMOVED: made-up figures still block --")
for p, why in (("six point seven furlongs", "6.7f is not in the article"),
               ("nine point five furlongs", "9.5f is not in the article"),
               ("two and five-eighths lengths", "2 5/8 is not in the article"),
               ("🔴 five and three quarter lengths",
                "5 3/4 is not in the article — and both halves ARE, so the old split let it through")):
    # (Not a case here: "six point five KILOS". The gate traces the NUMBER, never the unit
    # word after it — "seven kilos" passes against "7f" today, decimal or not.)
    phrase = p.replace("🔴 ", "")
    check(f"  still blocks {p!r} — {why}", says(phrase) != [],
          "THE GATE HAS BEEN WIDENED: this figure is not in the article and it got through")

print("\n-- against EP53's REAL captured article --")
cap = capture(EP)
if not cap:
    check(f"EP{EP}'s capture is on this machine", False, "the Drive file is not here")
else:
    line = ("Sprints up to six point five furlongs, two and three-quarter lengths. Eight point "
            "five furlongs and longer, four and three-quarter lengths.")
    check("🔴 EP53's distance standards pass against the article they came from",
          F.check(line, cap, "") == [], str(F.check(line, cap, "")))
    check("  and a made-up standard in the same line still blocks",
          F.check(line.replace("six point five", "six point seven"), cap, "") != [])

print(f"\nunit decimals and mixed fractions: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
