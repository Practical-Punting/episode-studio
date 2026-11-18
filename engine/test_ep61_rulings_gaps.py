#!/usr/bin/env python3
"""EP61 (18 Nov 2026) — two gaps the script-notes route exposed. The writer was right 3 times.

1. "nineteen ninety to two thousand and two" — Hugh's approved note says "from August 1990 to
   2002". Each fold pass read every number one way, so no pass held the real spoken span
   ("twenty oh two" / "two thousand two"). Fix: a "year" reading saying the 2000s "two
   thousand and N". The notes, the key-points box and the dateline were ALREADY approved /
   article text — proved here (C) so nobody "fixes" them again.
2. Leave out: "(stats from www.racingandsports.com.au)" is a credit INSIDE the paragraph that
   gives gate 1's 13.8% — it cut the whole paragraph. Fix: a quote that opens a paragraph cuts
   the paragraph (EP60); one inside a paragraph cuts only those words.

    python engine/test_ep61_rulings_gaps.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import episode_rulings as R  # noqa: E402
import script_fidelity as sf  # noqa: E402

DOCS = Path(r"G:\My Drive\PP Videos\docs")
CAP61 = next(DOCS.glob("EP61-source-article-*.md")).read_text(encoding="utf-8")
CAP60 = next(DOCS.glob("EP60-source-article-*.md")).read_text(encoding="utf-8")
NOTES61 = ('Say that the Rosehill barrier figures run from August 1990 to 2002.\n'
           'Leave out: "(stats from www.racingandsports.com.au)"\n'
           'Leave out: "NEXT MONTH: More on barrier positions"\n'
           'Leave out: "Click here to read Part 2."\n'
           'Read "drawn in barrier I" as "barrier 1" (a typo in the article).\n'
           'No added lines beyond the article and the standard furniture.')
EP61 = {"ep_number": 61, "hook": "", "script_notes": NOTES61}
LIC61 = R.licensed_notes(EP61)
GOOD_13 = ("If we look at the Rosehill stats for eleven hundred metres to begin with, gate one "
           "has a thirteen point eight per cent winning record from four hundred and five races "
           "since August, nineteen ninety.")
fails: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


print("A. the year span, licensed by the approved note")
span = "The Rosehill barrier figures run from August nineteen ninety to two thousand and two."
check(sf.check(span, CAP61, LIC61) == [], "EP61's line passes with the note as licence")
check(sf.check(span, CAP61, "") != [], "CONTROL: without the note it is refused (the span is the note's, not the article's)")
bad = "The Rosehill barrier figures run from August nineteen ninety to two thousand and five."
check(sf.check(bad, CAP61, LIC61) != [], "CONTROL: an invented year (2005) is still refused")
bad2 = "The Rosehill barrier figures run from August nineteen eighty to two thousand and two."
check(sf.check(bad2, CAP61, LIC61) != [], "CONTROL: an invented start year (1980) is still refused")

print("B. the year reading is additive")
for said, src in (("in two thousand and two", "in 2002"), ("in twenty oh two", "in 2002"),
                  ("in nineteen ninety", "in 1990"), ("in two thousand and fifteen", "in 2015"),
                  ("in twenty fifteen", "in 2015"), ("over sixteen hundred metres", "over 1600m"),
                  ("in two thousand", "in 2000")):
    cap = f"---- ARTICLE TEXT BEGINS ----\n{src}.\n---- ARTICLE TEXT ENDS ----"
    check(sf.check(said + ".", cap) == [], f"'{said}' traces '{src}'")
cap = "---- ARTICLE TEXT BEGINS ----\nin 2002.\n---- ARTICLE TEXT ENDS ----"
check(sf.check("in two thousand and three.", cap) != [], "CONTROL: 'two thousand and three' does not trace 2002")

print("C. already article text (proved, not changed)")
check(sf.check("Barrier one won thirteen point eight per cent of four hundred and five races.",
               CAP61) == [], "a figure printed in the key-points box traces")
check(sf.check("First published in June two thousand and two.", CAP61) == [],
      "the dateline's year traces (June 2002)")

print("D. Leave out INSIDE a paragraph cuts only those words")
c = {q: (i, s) for q, i, s in R.cuts(CAP61, NOTES61)}
q1 = "(stats from www.racingandsports.com.au)"
check(q1 in c and c[q1][1] is not None, "the credit resolves to a SPAN, not its paragraph", str(c.get(q1)))
check(c.get("NEXT MONTH: More on barrier positions", (0, "x"))[1] is None,
      "a quote that opens a paragraph still cuts the paragraph")
check(R.check(GOOD_13, CAP61, EP61) == [], "the 13.8% sentence without the credit passes")
said_credit = GOOD_13[:-1] + " (stats from www.racingandsports.com.au)."
r = R.check(said_credit, CAP61, EP61)
check(any("only those words" in x for x in r), "CONTROL: saying the credit itself is caught", str(r)[:120])

print("E. EP60's whole-paragraph cuts are unchanged")
notes60 = ('Leave out: "If you are betting with a bookmaker using the Best Fluctuations option"\n'
           'Leave out: "When betting with bookmakers their percentages will vary"')
ep60 = {"ep_number": 60, "hook": "", "script_notes": notes60}
check(all(s is None for _, _, s in R.cuts(CAP60, notes60)), "both EP60 quotes cut whole paragraphs")
para = next(p for p in R.paragraphs(CAP60) if p.startswith("If you are betting with a bookmaker"))
lift = " ".join(para.split()[:14]) + "."
r = R.check(lift, CAP60, ep60)
check(any("whole paragraph" in x for x in r), "CONTROL: a lift from a cut EP60 paragraph is caught", str(r)[:120])

print("F. EP61's real last draft")
draft = Path(r"G:\My Drive\PP Videos\PP-EP61\docs\spoken-words.txt").read_text(encoding="utf-8")
check(sf.check(draft, CAP61, LIC61) == [], "figure check passes on the real draft")
check(R.check(draft, CAP61, EP61) == [], "rulings check passes on the real draft")
check(R.notes_problems(CAP61, EP61) == [], "the notes are obeyable (pre-attempt check)")

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILED: ' + '; '.join(fails)}")
sys.exit(1 if fails else 0)
