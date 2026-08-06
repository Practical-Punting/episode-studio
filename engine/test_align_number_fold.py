#!/usr/bin/env python3
"""The number fold in align_to_script — the guard for a change that moves the
timings EVERY card in EVERY future episode derives from.

WHY IT EXISTS: EP17 refused at 79.8% against an 85% floor on a master that was
complete, correctly trimmed and 189,366 bps. We spell figures as WORDS for the
TTS; a transcriber writes them as DIGITS. That is not the master disagreeing with
the script — it is two ways of writing the same sound, counted as the former.

MEASURED, and this file is what stops it silently regressing:
    EP15  91.1% -> 95.9%     EP16  87.8% -> 96.3%     EP17  79.8% -> 95.8%
    cue starts moved: median 0.000s, max 0.468s, ZERO cues past 1.0s

Run: python engine/test_align_number_fold.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / ".claude/skills/pp-episode-production/scripts"))
import align_to_script as A                                        # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                              # noqa: BLE001
        pass

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


# Every pair is a REAL figure from EP17's article beside the REAL wording from
# EP17's spoken track. A fold that produced plausible-but-different words would
# lift the anchor rate not at all and look like it had.
PAIRS = [
    ("660", "six hundred and sixty"),
    ("7,363", "seven thousand, three hundred and sixty-three"),
    ("98", "ninety-eight"), ("25", "twenty-five"),
    ("16%", "sixteen per cent"), ("5%", "five per cent"),
    ("$4.90", "four dollars ninety"),
    ("$224.60", "two hundred and twenty-four dollars sixty"),
    ("$32.90", "thirty-two dollars ninety"),
    ("262", "two hundred and sixty-two"),
    ("2,752", "two thousand, seven hundred and fifty-two"),
    ("304", "three hundred and four"), ("$22.10", "twenty-two dollars ten"),
    ("8%", "eight per cent"), ("59", "fifty-nine"),
    ("377", "three hundred and seventy-seven"),
    ("$25.40", "twenty-five dollars forty"), ("50%", "fifty per cent"),
    ("$2.40", "two dollars forty"), ("53%", "fifty-three per cent"),
    ("2007", "two thousand seven"),
]


def main():
    print("\n-- the fold produces the words OUR SCRIPT actually uses --")
    for digits, ours in PAIRS:
        check(f"{digits} -> {ours}",
              A.toks(A.spoken_form(digits)) == A.toks(ours),
              f"got {' '.join(A.toks(A.spoken_form(digits)))!r}")

    print("\n-- ONE definition, applied to BOTH sides --")
    # On our side it must be a NO-OP: render_ready hard-fails a bare numeral in
    # the spoken track, so there is nothing to convert. Applied and asserted
    # anyway — a symmetry you rely on and never exercise is not a symmetry.
    for d in sorted(Path(r"G:\My Drive\PP Videos").glob("PP-EP*")):
        sw = d / "docs/spoken-words.txt"
        if not sw.is_file() or not re.search(r"PP-EP(0[6-9]|1[0-7])", d.name):
            continue
        # THE PARAGRAPHS, not the raw file. align_to_script folds what
        # paragraphs() returns, and EP13-EP16 carry a `#` production-notes header
        # full of dates and pool arithmetic that Gordon never says. Reading the
        # raw file failed on four shipped episodes and the fold was innocent —
        # the test was measuring text the aligner never sees.
        body = " ".join(A.paragraphs(sw))
        check(f"the fold is a no-op on {d.name}'s spoken words",
              A.toks(body) == A.toks(A.spoken_form(body)))

    print("\n-- the floor is NOT moved --")
    check("MIN_MATCH is still 0.85", A.MIN_MATCH == 0.85,
          f"it is {A.MIN_MATCH} — moving a threshold because a build failed it is how "
          "a floor stops meaning anything. It caught EP15's truncated master at 62.9%.")

    print("\n-- the halt REPORTS, it does not diagnose (fault #6) --")
    ours = ["six", "hundred", "and", "sixty"] * 25
    at = [None] * len(ours)
    msg = A.observed_miss_report(0.40, ours, at, [0] * len(ours), [(0, "x")])
    for banned in ("wrong take", "wrong episode",
                   "the words changed after the render", "That means"):
        check(f"it does not assert {banned!r}", banned not in msg)
    check("it says how much anchored", "40.0%" in msg)
    check("it says WHERE the misses fall", "of the way through" in msg)
    check("it names the number-word clustering when that is what it sees",
          "number words" in msg)
    check("it offers causes as possibilities, not findings", "COULD BE" in msg)
    check("it says plainly whether a retry helps",
          "RETRYING ON ITS OWN WILL NOT" in msg)

    # A master that stops early has a DIFFERENT signature and must still be named.
    ours2 = ["word"] * 100
    at2 = [0.0] * 70 + [None] * 30
    msg2 = A.observed_miss_report(0.70, ours2, at2, [0] * 100, [(0, "x")])
    check("a tail-clustered miss is called out as an early-stopping master",
          "stops early" in msg2)

    print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} green")
    if FAIL:
        for f in FAIL:
            print("  - " + f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
