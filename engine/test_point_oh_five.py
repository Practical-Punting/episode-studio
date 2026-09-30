#!/usr/bin/env python3
"""EP54 — THE GATE COULD NOT SAY "POINT OH FIVE".

    python engine/test_point_oh_five.py

EP54 "Attainable Targets (Part 6)" burned all three script attempts on 30 Sep
2026. The article prints "handicappers who improve their skill by 10 per cent
... have tripled their profits (.05 to .15)". Every draft said "from point oh
five to point one five", and every draft was rejected for inventing the figure
'five to point one five'. Three writers refused to change it. THEY WERE RIGHT.

The gate was wrong on BOTH sides of the comparison, and either fault alone was
enough to block:

  (a) THE ARTICLE SIDE. `.05` has no digit in front of the point, so the decimal
      rule never saw it; spoken_form's bare-integer rule dropped the point and
      read it "five", and `.15` "fifteen". The article was being read as saying
      "five to fifteen" — a change of value, the one thing the gate refuses.
  (b) THE SCRIPT SIDE. "oh" was not a number word, so the reader broke the figure
      at it and traced the FRAGMENT "five to point one five": the tail of one
      figure glued to the whole of the next.

🔒 WHAT MUST NOT MOVE. A decimal the article does not print still blocks, said
with "oh", "zero" or "nought". "oh" outside a decimal is still English. Every
case below that begins "still blocks" is there to prove the gate is not wider.
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

EP = 54                       # the episode this file is about, as a NUMBER


def capture(n: int):
    hits = sorted((PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    return hits[0].read_text(encoding="utf-8") if hits else None


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


# The article's own notation, in a fixture written for this suite: decimals with
# no whole part, in running text AND in a table, as the old magazine set them.
CAP = """# A TARGETS FIXTURE

---- ARTICLE TEXT BEGINS ----

# ATTAINABLE TARGETS (TEST FIXTURE)

| Win % | Odds | Edge |
|---|---|---|
| 30% | 5-2 | .05 |
| 33% | 5-2 | .15 |

Notice that handicappers who improve their skill by 10 per cent have tripled
their profits (.05 to .15). A horse that wins by 1.05 lengths is close.

---- ARTICLE TEXT ENDS ----
"""


def says(phrase):
    return F.check("Gordon says " + phrase + " here.", CAP, "")


print("\n-- 🔴 the article's own figure, said the way a person says it --")
check("🔴 'from point oh five to point one five' — the article prints (.05 to .15) — PASSES",
      says("from point oh five to point one five") == [],
      "this is EP54's block: the figure is in the article, word for word")
check("  'point zero five' — the same figure said with zero — passes",
      says("point zero five") == [])
check("  'point nought five' — and with nought — passes",
      says("point nought five") == [])
check("  'point one five' on its own passes", says("point one five") == [])
check("  a whole part with an oh in the decimals ('one point oh five') passes",
      says("one point oh five lengths") == [],
      "the article prints 1.05; the oh broke this figure too")

print("\n-- 🔒 AND THE GUARD IS UNMOVED: a decimal the article does not print still blocks --")
for phrase, why in (
        ("from point oh five to point one seven", ".17 is nowhere in the article"),
        ("point oh seven", ".07 is not in the article"),
        ("point zero seven", "nor said with zero"),
        ("point nought seven", "nor said with nought"),
        ("point oh oh five", ".005 is a different figure from .05"),
        ("one point oh six lengths", "1.06 is a hair from 1.05, and not it"),
        ("five to fifteen", "the OLD misreading of (.05 to .15) — a change of value")):
    got = says(phrase)
    check(f"  still blocks {phrase!r} — {why}", got != [],
          "THE GATE HAS BEEN WIDENED: this figure is not in the article and it got through")

print("\n-- and the figure it names is the WHOLE figure, not a fragment --")
got = says("from point oh five to point one seven")
check("  the message names 'point zero five to point one seven'",
      bool(got) and "point zero five to point one seven" in got[0], str(got))

print("\n-- 'oh' outside a decimal is still English --")
check("  'Oh, and another thing' is not a figure",
      F.figures("Oh, and another thing.") == [], str(F.figures("Oh, and another thing.")))
check("  'oh five' with no point in front is not read as a decimal",
      "zero five" not in " ".join(F.figures("It was oh five hundred.")),
      str(F.figures("It was oh five hundred.")))
check("  'at this point two things matter' still reads the figure as 'two'",
      F.figures("At this point two things matter.") == ["two"],
      str(F.figures("At this point two things matter.")))

# ── THE ARTEFACT: EP54's REAL capture ──────────────────────────────────────
print("\n-- against EP54's REAL captured article --")
cap54 = capture(EP)
if not cap54:
    check(f"EP{EP}'s capture is on this machine", False,
          "cannot run the acceptance case — the Drive file is not here")
else:
    line = ("Notice that handicappers who improve their skill by ten per cent have "
            "tripled their profits, from point oh five to point one five.")
    check("🔴 EP54's line passes against the article it came from",
          F.check(line, cap54, "") == [], str(F.check(line, cap54, "")))
    check("  and a made-up figure in the same line still blocks",
          F.check(line.replace("one five", "one seven"), cap54, "") != [])

print(f"\npoint oh five is sayable: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
