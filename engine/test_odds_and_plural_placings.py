#!/usr/bin/env python3
"""test_odds_and_plural_placings.py — a price reads "X to Y", and "2nds" reads "seconds".

    python engine/test_odds_and_plural_placings.py

Jodie's rulings, 5 Oct 2026, on EP55's split (the second two-way):

  · RACING ODDS ARE NEVER READ "OVER". The writer's fold read the article's `3/1` and
    `66/1` as "three over one" and "sixty six over one" — `_frac_named` has no name for a
    denominator of one. A writer now speaks a slash with `_frac_said`.
  · A PLACING IN THE PLURAL IS SPELLED OUT. `two 2nds` and `no 2nds` were left as digits
    welded to letters, because the ordinal rule stopped at a `\\b` the "s" removes.

And what must NOT move: `1/9` is still "one ninth" (EP16), a mixed number still takes
"and" (EP53), a singular placing is still "second", and the gate's own readings are
untouched — `haystacks()` passes its fraction readings explicitly.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import script_fidelity as sf                                     # noqa: E402

PASS, FAIL = [], []


def check(name, cond, got=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else f"\n         <- {got!r}"))


def f(s):
    return sf.fold(s, unit_reading="hundreds")


print("odds — a price is read 'to', never 'over'")
check("3/1 -> three to one", "three to one" in f("home at around 3/1."), f("home at around 3/1."))
check("66/1 -> sixty six to one", "sixty six to one" in f("a 66/1 chance"), f("a 66/1 chance"))
check("10/1 -> ten to one", "ten to one" in f("at 10/1"), f("at 10/1"))
check("7/4 -> seven to four (a price, not 'seven quarters')", "seven to four" in f("about 7/4"),
      f("about 7/4"))
check("6/4 -> six to four", "six to four" in f("6/4 fav"), f("6/4 fav"))
check("no 'over' is ever produced for a price", " over " not in f("3/1, 66/1, 10/1, 7/4, 5/2"),
      f("3/1, 66/1, 10/1, 7/4, 5/2"))

print("\nwhat must not move")
check("1/9 is still one ninth (EP16's probability)", "one ninth" in f("a 1/9 chance"),
      f("a 1/9 chance"))
check("2 3/4 lengths is still 'two and three quarters'", "two and three quarters" in f("2 3/4 lengths"),
      f("2 3/4 lengths"))
check("a singular placing is still 'second'", f("ran 2nd last start").split()[1] == "second",
      f("ran 2nd last start"))
check("12th is still twelfth", "twelfth" in f("finished 12th"), f("finished 12th"))

print("\nplacings in the plural")
check("two 2nds -> two seconds", "two seconds" in f("five wins and two 2nds!"),
      f("five wins and two 2nds!"))
check("no 2nds -> no seconds", "no seconds" in f("with no 2nds, avoid him"), f("with no 2nds, avoid him"))
check("3rds -> thirds", "four thirds" in f("four 3rds"), f("four 3rds"))
check("no digit survives a plural placing", not re.search(r"\d", f("two 2nds and three 3rds")),
      f("two 2nds and three 3rds"))

print("\nthe gate is untouched: a script reading the price 'to' or 'over' still traces")
SRC = "header\n" + sf.MARKER_BEGIN + "\nKing brought the horse home at around 3/1.\n"
check("'three to one' traces against 3/1", not sf.check("at around three to one.", SRC),
      sf.check("at around three to one.", SRC))
check("'three over one' still traces (the gate keeps every reading it had)",
      not sf.check("at around three over one.", SRC), sf.check("at around three over one.", SRC))
check("an invented price is still refused", bool(sf.check("at around five to one.", SRC)))

# ── the real article: EP55's capture, through the two-way writer ──
PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
cap = sorted((PP / "docs").glob("EP55-source-article-*.md"))
if cap:
    import twoway_split as ts                                    # noqa: E402
    turns, speakers, _ = ts.split_turns(cap[0].read_text(encoding="utf-8"))
    said = " ".join(ts.spoken(t["text"]) for t in turns if t["speaker"] in speakers)
    print("\nEP55's real article, through twoway_split.spoken")
    check("EP55 says 'three to one'", "three to one" in said)
    check("EP55 says 'sixty six to one'", "sixty six to one" in said)
    check("EP55 never says 'over one'", "over one" not in said)
    check("EP55 says 'two seconds' and 'no seconds'", "two seconds" in said and "no seconds" in said)
    check("no digit survives anywhere in EP55's reading", not re.search(r"\d", said),
          re.findall(r"\S*\d\S*", said))
else:
    print("\n  (EP55's capture not on this machine — the real-article half is SKIPPED, not assumed)")

print(f"\nodds and plural placings: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
