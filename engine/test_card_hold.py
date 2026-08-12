"""Prove the minimum card hold SCALES with what the card asks you to read.

The fault this closes: `min_card_hold` was one flat 10.0s for every card in the
episode, so EP21 C19 - two rows of a two-column table, about five seconds of
reading - HALTED the build on a floor sized for a four-row card. Jodie, 12 Aug
2026: the minimum must scale with the reading load, with a hard floor around
7-8s for a light card, and every existing value untouched.

CONTROL-FIRST. Steps 1 and 3 are the ones that matter: they assert the checks
still FAIL on the shapes that should fail. A test that only proves the happy
path proves that the code runs, not that it works.

  1. the floor still BITES  - a 6.0s hold on a 2-row card is still rejected
  2. the scale is calibrated - 4 items reproduces the blanket 10.0s EXACTLY,
     so no shipped four-row card moves by a frame
  3. the absolute floor holds - a 0-item card never drops under 7.0s
  4. no-floor episodes stay  - min_card_hold absent/0 still means no minimum
  5. ALL THREE ENFORCERS AGREE - derive/assemble/qc import the one module, so
     the map cannot plan 8.6s while the assembler builds 10.0s
  6. EP21 C19 specifically - 2 rows, 8.6s hold, passes; 7.9s does not

Run:  python test_card_hold.py
"""
import ast
import importlib.util
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(_REPO, ".claude", "skills", "pp-episode-production", "scripts")

spec = importlib.util.spec_from_file_location("ch", os.path.join(SCRIPTS, "card_hold.py"))
ch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ch)

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def card(n_rows, n_cols=2):
    """A card carrying n_rows rows under n_cols headings. 0 rows = a bare stat."""
    if n_rows == 0:
        return {"id": "X", "content": {"stat": "41%", "foot": "since 2019"}}
    return {"id": "X", "content": {"columns": [f"c{i}" for i in range(n_cols)],
                                   "rows": [{"label": f"r{i}", "cells": ["1", "2"]}
                                            for i in range(n_rows)]}}


BLANKET = {"min_card_hold": 10.0}

print("=" * 78)
print("STEP 1 - CONTROL: the floor still BITES on a hold that is genuinely too short")
print("=" * 78)
# If this passes, the whole change is a hole, not a fix.
two = card(2)
m2 = ch.min_hold_for(two, BLANKET)
check(6.0 < m2, "a 6.0s hold on a 2-row card is STILL below the minimum", f"min {m2}s")
check(4.0 < m2, "a 4.0s hold on a 2-row card is STILL below the minimum", f"min {m2}s")
check(m2 >= 7.0, "the 2-row minimum is a comfortable read, not a token one", f"{m2}s")

print()
print("=" * 78)
print("STEP 2 - CALIBRATED to the number already in use, so nothing shipped moves")
print("=" * 78)
four = ch.min_hold_for(card(4), BLANKET)
check(four == 10.0, "4 items reproduces the blanket 10.0s EXACTLY", f"{four}s")
check(ch.min_hold_for(card(5), BLANKET) == 10.0, "5 items is capped at the blanket")
check(ch.min_hold_for(card(9), BLANKET) == 10.0, "9 items is capped at the blanket")
for n, want in ((1, 7.0), (2, 8.0), (3, 9.0), (4, 10.0)):
    got = ch.min_hold_for(card(n), BLANKET)
    check(got == want, f"{n} item(s) -> {want}s", f"got {got}s")
check(all(ch.min_hold_for(card(n), BLANKET) <= ch.min_hold_for(card(n + 1), BLANKET)
          for n in range(0, 8)), "the minimum never DROPS as the card gets heavier")

print()
print("=" * 78)
print("STEP 3 - CONTROL: the absolute floor holds however light the card")
print("=" * 78)
zero = ch.min_hold_for(card(0), BLANKET)
check(zero >= ch.ABSOLUTE_FLOOR_S, "a card with no list at all never drops under 7.0s",
      f"{zero}s")
check(ch.reading_load(card(0)) == 1, "no list reads as ONE thing, not zero")
check(ch.reading_load({"content": None}) == 1, "a card with no content at all reads as 1")
check(ch.reading_load({}) == 1, "a card with no content KEY at all reads as 1")
check(ch.reading_load({"content": ["not", "a", "dict"]}) == 1, "malformed content reads as 1")

# THE BUG THIS TEST CAUGHT. `columns` is a list too, and counting it made C19 read
# as three items off three column HEADINGS over two rows of data - which is the
# header, read once on the way in, not a row.
wide = ch.reading_load(card(2, n_cols=6))
check(wide == 2, "SIX column headings over two rows still reads as TWO items",
      f"got {wide}")
check(ch.reading_load(card(4, n_cols=2)) == 4, "and rows are still counted in full")
# ...but a checklist's plain-string items ARE the load - there is no dict list there.
check(ch.reading_load({"content": {"items": ["a", "b", "c", "d", "e"]}}) == 5,
      "a checklist's five string items read as FIVE, not one")
check(ch.reading_load({"content": {"slots": [{"a": 1}] * 4, "chips": ["x"] * 9}}) == 4,
      "a dict list WINS over a longer string list beside it")
# and a mean blanket is never EXCEEDED by the floor
tight = ch.min_hold_for(card(1), {"min_card_hold": 5.0})
check(tight == 5.0, "a blanket TIGHTER than the floor is still the ceiling", f"{tight}s")

print()
print("=" * 78)
print("STEP 4 - an episode that asks for no floor still has none")
print("=" * 78)
for build, label in (({}, "no min_card_hold key"),
                     ({"min_card_hold": 0}, "min_card_hold 0"),
                     ({"min_card_hold": None}, "min_card_hold null")):
    got = ch.min_hold_for(card(2), build)
    check(got == 0.0, f"{label} -> no minimum", f"got {got}s")
check(ch.min_hold_for(card(2), None) == 0.0, "a missing build block -> no minimum")

print()
print("=" * 78)
print("STEP 5 - ALL THREE ENFORCERS USE THE ONE MODULE (the real fault mode)")
print("=" * 78)
# derive_card_timings CHECKS it, assemble_episode CLAMPS to it, qc_episode does
# both. Lowering it in one place would let the map plan 8.6s while the assembler
# built 10.0s and pushed the card over the end card, with every check passing.
for fn in ("derive_card_timings.py", "assemble_episode.py", "qc_episode.py"):
    src = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
    tree = ast.parse(src)
    imports_it = any(
        (isinstance(n, ast.Import) and any(a.name == "card_hold" for a in n.names))
        or (isinstance(n, ast.ImportFrom) and n.module == "card_hold")
        for n in ast.walk(tree))
    check(imports_it, f"{fn} imports card_hold")
    check("ch.min_hold_for(" in src or "min_hold_for(" in src,
          f"{fn} calls min_hold_for")
    # nobody may still be reading the blanket as a bare per-card minimum
    bare = [ln.strip() for ln in src.splitlines()
            if 'min_card_hold' in ln and 'card_hold.py' not in ln
            and not ln.strip().startswith("#")]
    check(all("ch.min_hold_for" in ln or "get(" in ln or '"' in ln or "'" in ln
              for ln in bare),
          f"{fn} has no bare min_card_hold comparison left",
          f"{len(bare)} mention(s)")

print()
print("=" * 78)
print("STEP 6 - EP21 C19, the card that started this")
print("=" * 78)
# Two rows, two columns: Rosehill and Warwick Farm. Its home is beat 29 - the
# payoff - which can give a card only 8.64s.
c19 = {"id": "C19", "content": {
    "columns": ["Track", "Sprint draws", "Longer trips"],
    "rows": [{"label": "Rosehill", "cells": ["a", "b"]},
             {"label": "Warwick Farm", "cells": ["a", "b"]}]}}
m = ch.min_hold_for(c19, BLANKET)
check(m == 8.0, "C19's minimum is 8.0s, not the blanket 10.0s", f"{m}s")
check(8.6 >= m, "the 8.6s hold Jodie asked for PASSES", f"8.6 vs min {m}")
check(8.64 >= m, "and it fits the 8.64s beat 29 can give it")
check(not (7.9 >= m), "CONTROL: 7.9s would still be REJECTED", f"7.9 vs min {m}")
check("8.0s minimum for 2 item(s)" in ch.why(c19, BLANKET),
      "the halt message states the number and its reason", ch.why(c19, BLANKET))

print()
print("=" * 78)
if fails:
    print(f"FAILED ({len(fails)}):")
    for f in fails:
        print(f"  - {f}")
    sys.exit(1)
print("ALL PASS - the minimum scales with the reading load, floors at 7.0s, caps at")
print("the episode's blanket, and all three enforcers read it from the one place.")
