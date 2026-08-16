#!/usr/bin/env python3
"""EP29 — THE GATE COULD NOT SAY "ONE DOLLAR FIFTY".

    python engine/test_one_dollar_is_sayable.py

EP29 "Stake Your Claim" burned all three script attempts. The writer produced a
complete 2,445-word draft, was told twice to delete two dollar amounts, and each
time refused and stopped:

    "The studio's checks asked me to remove two dollar amounts from the script,
     saying the original article never prints them. IT DOES. … Because both
     objections are mistaken about what the article says, I have left the script
     exactly as it was rather than deleting figures the author actually wrote."

THE WRITER WAS RIGHT. The article prints `$1.50` twice and `$1.67c` once, in its
own worked examples. The gate was wrong, in two separate ways, and this file
holds one case for each:

  (a) THE FOLD ALWAYS WROTE THE PLURAL. `$1.50` became "one dollarS fifty", so
      the only correct English rendering — "one dollar fifty" — matched nothing.
      The proof it is a grammar fault and not a figures fault is inside the same
      script: it says "three dollars fifty" and that PASSED, while "one dollar
      fifty" blocked.

  (b) A TRAILING CENTS MARK GLUED ITSELF ON. `$1.67c` — the author's own
      typing, a dollar sign AND a cents mark on one figure — folded to
      "sixty sevenC", a non-word. EVERY spoken form was refused: "one dollar
      sixty seven", "one dollars sixty seven", "sixty seven". There was NO
      legal way to comply while keeping the author's figure.

That is [[a-rule-with-no-legal-way-to-comply]]: the guard is right and the
vocabulary is the bug — the same shape as EP26's charts, where the writer was
also blamed for a hole in what it was allowed to say.

🔒 WHAT MUST NOT MOVE. The gate exists to stop the studio inventing a number,
and every case below that begins "still blocks" is there to prove it still does.
Widening what the SOURCE may be READ as is not the same as widening what the
script may SAY, and the moment those two are confused this gate is decoration.
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

EP = 29                       # the episode this file is about, as a NUMBER


def capture(n: int):
    hits = sorted((PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    return hits[0].read_text(encoding="utf-8") if hits else None


def episode_dir(n: int):
    """Resolve the folder BY NUMBER, never by a written-out name.

    ⚠️ THE FIRST VERSION OF THIS FILE GLOBBED "PP-EP29*" AND `test_no_hardcoded_
    episode_paths` CAUGHT IT — correctly, and with the same words it used on
    `test_script_fidelity`'s first version. The stage-8 close-out RENAMES a
    published episode's folder, so a literal is a fuse: it passes for weeks and
    then fails the day the process does the thing it is designed to do.
    """
    hits = sorted(p for p in PP.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else None


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


# A capture in the article's own notation — generic staking arithmetic, written
# for this suite. `$1.67c` is the shape that mattered: the old magazines print a
# dollar sign and a cents mark on the same figure.
CAP = """# A STAKING FIXTURE

---- ARTICLE TEXT BEGINS ----

# STAKE YOUR CLAIM (TEST FIXTURE)

The first bet is lost. This calls for a half unit (50c) increase in stake, so the
2nd bet would be $1.50 eachway. With the horse missing a place, you now increase
to $1.50 eachway for the fifth bet. Let's say your stake had grown to $3.50
eachway.

This $5 is divided by the divisor, which is three, calling for a bet of $1.67c,
which is rounded to $2.

---- ARTICLE TEXT ENDS ----
"""


def says(phrase):
    return F.check("Gordon says " + phrase + " here.", CAP, "")


print("\n-- (a) the SINGULAR is how a person says one dollar --")
check("🔴 'one dollar fifty' — the article prints $1.50 — PASSES",
      says("one dollar fifty") == [],
      "this is EP29's first block, and the figure is in the article twice")
check("  and the plural stays valid too, for anyone who wrote it that way",
      says("one dollars fifty") == [])
check("  and the bare reading a person also uses", says("one fifty") == [])
check("  the plural is still right where it IS right ('three dollars fifty')",
      says("three dollars fifty") == [])

print("\n-- (b) the author's own dollar-and-cents typing must be sayable --")
check("🔴 'one dollar sixty seven' — the article prints $1.67c — PASSES",
      says("one dollar sixty seven") == [],
      "EP29's second block, and the one with NO legal way to comply: every "
      "spoken form was refused because the fold produced 'sixty sevenc'")
check("  the plural form of the same figure passes",
      says("one dollars sixty seven") == [])
check("  and so does the bare reading", says("sixty seven") == [])
check("  the rounding the author states is sayable as well ('two dollars')",
      says("two dollars") == [])

print("\n-- 🔒 AND THE GUARD IS UNMOVED: an invented amount still blocks --")
for phrase, why in (
        ("one dollar eighty", "$1.80 is nowhere in the article"),
        ("one dollars eighty", "the plural of an invented amount is still invented"),
        ("one eighty", "and the bare reading of it"),
        ("two dollars forty", "$2.40 is not in the article"),
        ("one dollar sixty eight", "a cent away from a real figure is not it"),
        ("one dollar fifty one", "nor is a cent away from the other one"),
        ("nine dollars", "an amount of a different size entirely")):
    got = says(phrase)
    check(f"  still blocks {phrase!r} — {why}", got != [],
          "THE GATE HAS BEEN WIDENED INTO DECORATION: this figure is not in the "
          "article and the gate let it through")

print("\n-- and the figure it names is the one that is wrong --")
got = says("one dollar eighty")
check("  the message names the invented figure",
      bool(got) and "one dollar eighty" in got[0], str(got))

print("\n-- rounding and inference are still refused (the rule's whole point) --")
check("  a figure the article ROUNDS to is only sayable as printed",
      says("one dollar seven") != [],
      "$1.07 appears nowhere; a plausible-looking cents value must not pass")
check("  a sum the article never does still blocks",
      says("five dollars sixty seven") != [],
      "the article divides $5 by three; it never prints $5.67")

# ── THE ARTEFACT: EP29's REAL draft against its REAL capture ────────────────
# The words are the writer's, unchanged and unrewritten. This is the acceptance
# case Jodie set: the draft that exists must pass the fixed gate.
print("\n-- EP29's REAL 2,445-word draft, against its REAL captured article --")
cap29 = capture(EP)
_d = episode_dir(EP)
draft = (_d / "docs/spoken-words.txt") if _d else None
if not cap29 or not draft or not draft.is_file():
    check(f"EP{EP}'s capture and draft are on this machine", False,
          "cannot run the acceptance case — the Drive files are not here")
else:
    scr29 = draft.read_text(encoding="utf-8")
    words = len(scr29.split())
    check(f"the draft is the 2,445-word one ({words} words)", words == 2445,
          f"{words} words — is this still the draft the writer stopped on?")
    got = F.check(scr29, cap29, "")
    check("🔴 THE WRITER'S DRAFT PASSES THE GATE, UNCHANGED", got == [],
          "still rejected:\n           " + "\n           ".join(g.split(".")[0] for g in got))
    # ⚠️ ASKED OF THE GATE'S OWN READER, never of a literal. The draft writes
    # "one dollar sixty-SEVEN" with a hyphen, so a typed string comparison failed
    # here on a draft that is perfectly correct — which is this whole episode's
    # fault in miniature: the check disagreeing with the words over punctuation.
    spoken = F.figures(scr29)
    check("  and it still says the two figures it was blamed for",
          "one dollar fifty" in spoken and "one dollar sixty seven" in spoken,
          f"the draft no longer speaks them — has it been rewritten? It must not "
          f"be. Money figures found: {[f for f in spoken if 'dollar' in f][:6]}")

print(f"\none dollar is sayable: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
