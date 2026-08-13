"""THE B-ROLL STANDING LINES MUST REACH THE GENERATED PROMPTS, NOT JUST THE REGISTRY.

EP23 shipped with **horses running on BOTH SIDES of the running rail** (Hugh, 14 Aug
2026). EP24 onward; EP23 is published and is NOT changed.

🔴 THE FINDING, AND IT IS THE USEFUL PART. EP23's prompts were not careless — they
carry the stride line and the silks line in every racing shot, because whoever wrote them
read `docs/broll-registry.md`. **Five of the six NAMED the white running rail.** Not one
said WHICH SIDE OF IT THE HORSES GO. The rail was placed in the frame as scenery
— *"running away across the frame"*, *"along one side"*, *"curving away on the inside"* —
and never as a BOUNDARY with a rule about it. So the model drew the rail it was asked for
and filled both sides with the horses it was also asked for.

    IT DID WHAT IT WAS TOLD; IT WAS TOLD THE WRONG THING.

Which is §1's sentence and §4's shape: hats were named, the RANGE was not. The rail was
named, the SIDE was not.

⚠️ SO A DOC WAS NEVER GOING TO BE ENOUGH — the doc was being read. The lines live in
`broll_prompt_rules.py` and are checked in `_broll_prompt`, which every generated prompt
comes through, before a credit is spent. This suite proves the check catches EP23's REAL
prompts and stays quiet on what EP23 got right.

🚫 NOT A REVIEW STEP. Nothing here asks a human to judge a picture (Jodie, 5 Aug 2026).
It reads text and names the missing sentence.

Run: python engine/test_broll_rail_rule.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import broll_prompt_rules as R                                        # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


def keys(prompt):
    return {g["key"] for g in R.check_prompt(prompt)}


# The line Hugh's ruling requires, as the registry states it.
GOOD_RAIL = ("The whole field runs on ONE side of a single white running rail — the rail "
             "is the inside boundary of the track, open green turf infield beyond it, no "
             "horses on the far side")
GOOD = ("Photoreal cinematic wide shot of a field of racehorses galloping on lush green "
        "turf at an Australian racecourse. " + GOOD_RAIL + ". The horses at clearly "
        "different points in their stride, legs out of phase across the field, "
        "anatomically correct with four legs and one head. Mounted jockeys crouched in "
        "bright racing silks, actively riding. Natural daylight.")

print("\n-- a prompt that states everything is quiet --")
check("the fully-specified racing shot raises nothing", keys(GOOD) == set(), keys(GOOD))

print("\n-- and each standing line is genuinely load-bearing --")
check("dropping the rail-side clause is caught",
      "rail-side" in keys(GOOD.replace(GOOD_RAIL, "a white running rail alongside")),
      "this is EP23's exact fault and it must not pass")
check("dropping what lies BEYOND the rail is caught",
      "rail-beyond" in keys(GOOD.replace(", open green turf infield beyond it", "")),
      "a negation cannot be drawn; the far side needs a job or a horse fills it")
check("dropping the stride line is caught",
      "strides" in keys(GOOD.replace("different points in their stride", "close together")
                        .replace("legs out of phase across the field", "bunched")))
check("dropping the silks is caught", "silks" in keys(GOOD.replace("racing silks", "gear")))
check("dropping the turf is caught",
      # BOTH mentions — the rail clause also says "open green turf infield", so replacing
      # only the first leaves the prompt still stating turf and the rule rightly quiet.
      "turf" in keys(GOOD.replace("lush green turf", "a track")
                     .replace("open green turf infield", "open ground")))
check("dropping the anatomy line is caught",
      "anatomy" in keys(GOOD.replace("anatomically correct with four legs and one head",
                                     "strong")))

print("\n-- a NON-racing shot is not graded as one --")
kitchen = ("Photoreal cinematic close overhead shot of a person's hands working at a "
           "kitchen table, one hand holding a pencil and marking a ruled notebook page, "
           "a mug and reading glasses beside it, warm daylight from a window.")
check("the kitchen-table clip raises nothing", keys(kitchen) == set(),
      "EP23's broll-ratings-pencil-and-weights is exactly this and must stay exempt; "
      "a guard everyone ignores is worse than no guard")

print("\n-- crowd lines are asked of crowd shots ONLY --")
crowd = GOOD + " A crowd of spectators along the fence in present-day Australian dress."
check("a crowd shot must name the hat RANGE", "hat-variety" in keys(crowd),
      "EP18: sixteen people, every hat the same pale cream")
check("  and a head-on gallop is not asked for hat colours",
      "hat-variety" not in keys(GOOD))
check("  a crowd shot that names the range is quiet",
      "hat-variety" not in keys(crowd + " Akubra-style hats in a variety of natural "
                                        "colours, no two neighbours alike."))

print("\n-- 'dead straight' must not be pasted into a bend --")
bend = GOOD.replace("a single white running rail",
                    "a dead straight and perfectly level white running rail") + \
    " The field sweeps around the bend."
check("a straight rail in a bend shot is caught",
      "straight-rail-on-a-bend" in keys(bend),
      "EP23 did this twice; asking for a straight rail on a bend is asking for "
      "incoherent geometry")
check("  and 'dead straight' on a STRAIGHT is fine",
      "straight-rail-on-a-bend" not in
      keys(GOOD.replace("a single white running rail",
                        "a dead straight and perfectly level white running rail")))

print("\n-- EP23 IS PUBLISHED AND IS NOT RE-GRADED --")
check("EP23 raises nothing", R.check_episode([{"target": "x", "prompt": "field of "
                                               "racehorses galloping"}], 23) == [])
check("  EP24 does", R.check_episode([{"target": "x", "prompt": "field of racehorses "
                                       "galloping"}], 24) != [])
check("  and the cut is a NUMBER, not a 'looks new' test", R.FROM_EP == 24,
      "so re-running an old episode for any other reason cannot halt it on wording "
      "nobody had written yet")

print("\n-- AGAINST EP23'S REAL PROMPTS (would it have caught Hugh's fault?) --")
try:
    import ep_paths                                                   # noqa: E402
    j = json.loads((ep_paths.episode_dir(23) / "docs/episode.json")
                   .read_text(encoding="utf-8"))
    broll = j.get("broll", [])
except Exception as e:                                                # noqa: BLE001
    print(f"  (EP23's episode.json is not readable here: {e})")
    broll = []

if broll:
    graded = {b["target"]: keys(b.get("prompt") or "") for b in broll}
    racing = [t for t, _ in graded.items() if R.is_racing_shot(
        next(b["prompt"] for b in broll if b["target"] == t))]
    check("EP23's racing clips are found", len(racing) == 5, racing)
    check("EVERY racing clip is caught missing the rail side",
          all("rail-side" in graded[t] for t in racing),
          {t: sorted(graded[t]) for t in racing})
    check("  and both bend shots are caught on the straight-rail contradiction",
          sum("straight-rail-on-a-bend" in v for v in graded.values()) == 2,
          "EP23 asked for a dead-straight rail in coming-from-well-back and "
          "inside-barriers-turn-for-home, both of which bend")
    check("the non-racing clip is left alone",
          graded.get("broll-ratings-pencil-and-weights") == set())
    # 🔴 AND THE QUIET HALF, WHICH IS WHAT MAKES THIS A CHECK AND NOT A COMPLAINT.
    check("it does NOT re-flag the lines EP23 already got right (strides, silks, turf)",
          all(not ({"strides", "silks", "turf"} & graded[t]) for t in racing),
          {t: sorted(graded[t]) for t in racing})

print("\n-- the check is wired where prompts are actually generated --")
prov = (HERE / "providers.py").read_text(encoding="utf-8")
check("_broll_prompt asks the rules module",
      "broll_prompt_rules.check_episode" in prov.split("def _broll_prompt")[1][:2000],
      "checked anywhere else and a prompt could still be submitted without the lines")
check("  and the flag names the file the wording lives in",
      "broll-registry.md" in prov.split("def _broll_prompt")[1][:2500],
      "a halt that does not say where the words are is a halt she cannot clear")

print("\n-- the registry carries the reasoning, which code cannot hold --")
reg = (HERE.parent / "docs/broll-registry.md").read_text(encoding="utf-8")
check("§5 is in the registry", "ONE SIDE OF THE RAIL" in reg)
check("  with the evidence table of what EP23 actually asked for",
      "running away across the frame" in reg)
check("  and it is stated POSITIVELY, per the file's own rule",
      "open green turf infield beyond it" in reg)

print(f"\nb-roll rail rule: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
