#!/usr/bin/env python3
"""EP60, 18 Nov 2026 — "out of step" is said without the word "field".

Two standing rules from the same EP49 review contradicted each other: PP-STANDARDS told every
racing shot to say "a SPREAD field…", and rule (a) bans "a field" (Higgsfield reads it as many
horses). EP60's writer named three horses AND wrote "a spread field", and the count gate stopped
the build at b-roll. The prompts below are EP60's REAL ones, frozen here because the engine
rewrites episode.json when it corrects them.

    python engine/test_spread_out_is_four_or_fewer.py
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import broll_prompt_rules as R  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = HERE.parent

# EP60 docs/episode.json broll[2] — the slot that stopped the build (verbatim, 18 Nov 2026).
EP60_SLOT = (
    "Photoreal cinematic tracking shot, side-on at track level from the outside of the course: "
    "three Australian thoroughbred racehorses — a bay, a chestnut and a grey — gallop flat out "
    "down a lush green turf straight, a spread field at different strides and different "
    "positions, staggered, no two in step, the three of them almost level. Each has a jockey "
    "crouched low in plain bright silks of a different colour, plain saddlecloths, no numbers. "
    "Each jockey wears a racing skull cap covered by a silk cap in the same colours as his "
    "silks, with a short peak, goggles pushed up on the cap. One long straight white running "
    "rail on the far side of the horses, behind them, and a crowd far out of focus beyond it. "
    "Clods of green turf kicked up behind them. Warm golden-hour light from a low late-afternoon "
    "sun.")
# broll[5] — four horses head-on, same idiom; it would have stopped the build next.
EP60_HEAD_ON = (
    "Photoreal cinematic head-on shot on a long telephoto lens from track level, looking up a "
    "lush green turf home straight of an Australian racecourse: four thoroughbred racehorses "
    "race straight towards the camera — a chestnut a neck clear, then a bay, a grey and a dark "
    "brown — a spread field at different strides and different positions, staggered, no two in "
    "step. Each has a jockey crouched low in plain bright silks of a different colour, plain "
    "saddlecloths, no numbers. Each jockey wears a racing skull cap covered by a silk cap in the "
    "same colours as his silks, with a short peak, goggles pushed up on the cap. One long "
    "straight white running rail behind the horses on their far side, a crowd far out of focus "
    "beyond it. Turf kicked up behind them. Warm golden-hour light from a low late-afternoon "
    "sun.")
# cover.hero_b_prompt (first two sentences — the cover door reads the same standard).
EP60_COVER_B = (
    "Photoreal sports-press photograph, portrait 2:3 composition, present day, warm golden-hour "
    "light from a low late-afternoon sun. Three Australian thoroughbred racehorses — a bay, a "
    "chestnut and a grey — gallop head-on towards the camera down a lush green turf home "
    "straight, big and sharp across the middle third of the frame, a spread field at different "
    "strides, staggered, no two in step, nostrils flared, manes flying, small clods of turf "
    "kicked up behind them.")

passed = failed = 0


def ok(cond: bool, label: str) -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}")


def keys(prompt: str) -> set[str]:
    return {g["key"] for g in R.check_prompt(prompt)}


print("A. CONTROL — the gate really does stop EP60's slot as written")
ok(R.too_many(EP60_SLOT) == ["a spread field"], 'too_many(EP60 slot) == ["a spread field"]')
ok("four-max" in keys(EP60_SLOT), "check_prompt flags four-max on EP60's slot")

print("B. THE FIX — the corrector says it without 'field', and nothing else changes")
fixed, applied, unfixable = R.apply_rules(EP60_SLOT)
ok(unfixable == [], f"apply_rules leaves nothing unfixable (got {unfixable})")
ok(R.SPREAD_APPLIED in applied, "the translation is reported in `applied` (so it is written back)")
ok(not re.search(r"\bfield\b", fixed, re.I), "the word 'field' is gone from the prompt")
ok("spread out at different strides and different positions, staggered, no two in step" in fixed,
   "it says the horses are spread out, out of step")
ok("three Australian thoroughbred racehorses" in fixed, "the writer's count (three) is untouched")
ok("lush green turf" in fixed, "still lush green TURF")
ok(R.too_many(fixed) == [] and "four-max" not in keys(fixed), "the count gate passes")
ok("strides" not in keys(fixed), "the out-of-step rule is still satisfied")
ok(R.horses_racing(fixed), "it is still horses RACING (Jodie's 14 Nov rule)")
ok(R.check_prompt(fixed) == [], f"the corrected prompt has no gaps at all ({keys(fixed)})")
f5, a5, u5 = R.apply_rules(EP60_HEAD_ON)
ok(u5 == [] and "four thoroughbred racehorses" in f5 and "field" not in f5,
   "EP60's four-horse head-on slot is fixed the same way, count kept")
ok(R.episode_mix([{"target": "a", "prompt": fixed}, {"target": "b", "prompt": f5}], 60) == [],
   "the episode's set still has people/horses in every clip and horses racing")

print("C. THE COVER DOOR — same definition")
fc, ac = R.apply_frame_rules(EP60_COVER_B)
ok("field" not in re.sub(r"middle third", "", fc, flags=re.I).replace("the field of horses", ""),
   "cover hero B no longer asks for 'a spread field'")
ok(R.SPREAD_APPLIED in ac and "Three Australian thoroughbred racehorses" in fc,
   "cover: translation reported, count kept")

print("D. CONTROLS — the gate still bites where the count is not lawful")
no_count = ("Photoreal tracking shot: racehorses gallop down a lush green turf straight, a spread "
            "field at different strides and different positions, staggered, no two in step.")
_, _, u = R.apply_rules(no_count)
ok(any("FOUR" in x for x in u), "'a spread field' with NO count is still stopped")
five = ("Photoreal tracking shot: five thoroughbred racehorses gallop down a lush green turf "
        "straight, a spread field at different strides, staggered, no two in step.")
_, _, u = R.apply_rules(five)
ok(any("FOUR" in x for x in u), "five horses + 'a spread field' is still stopped")
three_plus_crowd = ("Photoreal tracking shot: three thoroughbred racehorses gallop down a lush "
                    "green turf straight, a spread field at different strides, staggered, no two "
                    "in step, twelve strappers watching from the rail.")
_, _, u = R.apply_rules(three_plus_crowd)
ok(any("FOUR" in x for x in u), "three horses but twelve strappers is still stopped")
eight = "Photoreal tracking shot: a field of eight gallops down a lush green turf straight."
_, _, u = R.apply_rules(eight)
ok(any("FOUR" in x for x in u), "'a field of eight' is still stopped")
untouched = "A punter at a lawn table turning a formguide sideways and laughing."
ok(R.spread_out(untouched) == (untouched, False), "a prompt without the idiom is not touched")

print("E. THE SOURCES THE WRITER READS no longer tell it to say 'field'")
std = (REPO / "docs/PP-STANDARDS.md").read_text(encoding="utf-8")
sec = std[std.index("A RAIL THAT DOES NOT WOBBLE"):]
sec = sec[:sec.index("\n### ")]
quotes = re.findall(r'^> \*"(.+?)"\*', sec, re.M | re.S) or []
said = " ".join(re.sub(r"\s*\n>\s*", " ", q) for q in re.findall(r'> \*"([^"]+)"\*', sec))
ok("SPREAD OUT" in said and R.too_many(said) == [],
   "PP-STANDARDS' prescribed wording passes the count gate")
ok(R.too_many('a SPREAD field, horses at different strides and different positions, staggered, '
              'NO TWO IN STEP') != [], "CONTROL: the OLD PP-STANDARDS wording fails it")
reg = (REPO / "docs/broll-registry.md").read_text(encoding="utf-8")
ok('*"a spread\nfield' not in reg and "spread out at different strides" in reg,
   "the registry's prescribed wording is the new one")
brief = R.commission_brief()
ok(R.SPREAD_OUT in brief and "Never 'a spread field'" in brief,
   "the writer's brief carries SPREAD_OUT and bans 'a spread field'")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
