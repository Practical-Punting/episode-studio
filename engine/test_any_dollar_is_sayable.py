#!/usr/bin/env python3
"""EP60 — THE GATE COULD SAY "ONE DOLLAR FIFTY" BUT NOT "TWO DOLLAR FIFTY".

    python engine/test_any_dollar_is_sayable.py

EP60 "What Is The Best Type Of Bet?" burned all three script attempts (17 Nov 2026).
The writer twice halted with does_retry_help=false:

    "The check says the article never gives the figure two dollars fifty, but it
     does. … The script only says that figure in words. It isn't rounded,
     converted or invented."

THE WRITER WAS RIGHT. The article says "If a punter bets 100 times at the TAB on
$2.50 win chances …". The script said "two dollar fifty win chances".

THE CAUSE. The money fold always writes the plural — `$2.50` becomes "two dollarS
fifty". EP29 (16 Aug) hit the same wall for `$1.50` and was fixed by adding ONE
singular reading: `one dollars` -> `one dollar`. That taught the gate one case
rather than the rule (CLAUDE.md fault 2b — "it just needs to know about X as
well"). The rule is English: an amount used to DESCRIBE something takes the
singular whatever its size — "a two dollar fifty chance", "a ten dollar bet".
So the singular is now offered for EVERY amount, as one reading.

WHY THIS CANNOT LET AN INVENTED FIGURE THROUGH. The new reading changes only the
unit word's number (dollars -> dollar). No number word moves, so an amount the
article never prints is refused in the singular exactly as in the plural. The
"still blocks" cases below are the control, and they were run against the fix.
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

EP = 60                       # the episode this file is about, as a NUMBER


def capture(n: int):
    hits = sorted((PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    return hits[0].read_text(encoding="utf-8") if hits else None


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


# The article's own shapes, written for this suite: a price with cents, a whole
# stake, and a one-dollar price (EP29's case, which must keep passing).
CAP = """# A BET TYPES FIXTURE

---- ARTICLE TEXT BEGINS ----

# BET TYPES (TEST FIXTURE)

If a punter bets 100 times at the TAB on $2.50 win chances the punter needs to
overcome the roughly 15% the TAB takes. An each way bet is a $2 bet to win and a
$2 bet to place. Favourites at $1.50 and $1.60 rarely pay well. A $10 stake is
plenty.

---- ARTICLE TEXT ENDS ----
"""


def says(phrase):
    return F.check("Gordon says " + phrase + " here.", CAP, "")


print("\n-- the SINGULAR is sayable for ANY amount the article prints --")
check("🔴 'two dollar fifty' — the article prints $2.50 — PASSES",
      says("two dollar fifty win chances") == [],
      "this is EP60's block; the figure is in the article")
check("  the plural of the same figure still passes", says("two dollars fifty") == [])
check("  a whole amount said as a describing word ('a two dollar bet')",
      says("a two dollar bet") == [])
check("  and a bigger one ('a ten dollar stake')", says("a ten dollar stake") == [])
check("  EP29's case is unchanged ('one dollar fifty')", says("one dollar fifty") == [])
check("  and 'one dollar sixty'", says("one dollar sixty") == [])

print("\n-- 🔒 CONTROL: an invented amount still blocks, singular or plural --")
for phrase, why in (
        ("two dollar sixty", "$2.60 is nowhere in the article"),
        ("two dollars sixty", "the plural of an invented amount is still invented"),
        ("three dollar fifty", "$3.50 is not in the article"),
        ("a five dollar bet", "$5 is not in the article"),
        ("one dollar seventy", "$1.70 is not in the article"),
        ("eleven dollar", "an amount of a different size entirely")):
    got = says(phrase)
    check(f"  still blocks {phrase!r} — {why}", got != [],
          "THE GATE HAS BEEN WIDENED INTO DECORATION: this figure is not in the "
          "article and the gate let it through")

got = says("two dollar sixty")
check("  and the message names the invented figure",
      bool(got) and "two dollar sixty" in got[0], str(got))

# ── THE ARTEFACT: EP60's REAL captured article ──────────────────────────────
# The sentence is the writer's own, copied from the draft that was refused. The
# draft file itself is rewritten on the next attempt, so the sentence is kept here.
print("\n-- EP60's REAL captured article --")
cap60 = capture(EP)
if not cap60:
    check(f"EP{EP}'s capture is on this machine", False,
          "cannot run the acceptance case — the Drive file is not here")
else:
    line = ("If you bet a hundred times at the TAB on two dollar fifty win chances, "
            "you've got to get past roughly fifteen per cent.")
    got = F.check(line, cap60, "")
    check("🔴 the writer's sentence passes against the real article", got == [],
          "still rejected: " + " | ".join(g.split(".")[0] for g in got))
    got = F.check(line.replace("two dollar fifty", "two dollar sixty"), cap60, "")
    check("  and the same sentence with an invented price still blocks", got != [])

print(f"\nany dollar is sayable: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
