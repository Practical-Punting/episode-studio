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
# ⚠️ THE LAST CLAUSE WAS ADDED 14 Aug 2026, WHEN ORIENTATION BECAME A STANDING RULE
# RATHER THAN A COVER-ONLY ONE. Without it this fixture is no longer "fully specified":
# a complete racing prompt now says which way up the picture goes, and the b-roll funnel
# is where EP25's six prompts were found with no orientation at all. Every case below
# derives from GOOD by REMOVING one clause, so the fixture has to state everything the
# rules ask for or the removals stop being the only difference.
# ⚠️ AND THE LAST TWO CLAUSES WERE ADDED 15 Aug 2026, FOR THE SAME REASON A THIRD TIME
# (EP26 faults 6 and 7 — the dark images and the kinked rail). "Fully specified" is not a
# fixed sentence, it is whatever the standing rules currently ask for; every time a rule
# is added, this fixture has to gain its line or every case below starts failing for a
# reason that has nothing to do with the clause it removes.
GOOD = ("Photoreal cinematic wide shot of a field of racehorses galloping on lush green "
        "turf at an Australian racecourse. " + GOOD_RAIL + ". The horses at clearly "
        "different points in their stride, legs out of phase across the field, "
        "anatomically correct with four legs and one head. Mounted jockeys crouched in "
        "bright racing silks, actively riding. Natural daylight, horizon level and near "
        "the middle with sky at the top and turf at the bottom, horses upright. The rail "
        "is one clean unbroken line, evenly spaced upright posts and a level top rail. "
        "Warm golden-hour light, generously exposed.")

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
# ⚠️ "RAISES NOTHING" BECAME "RAISES NO RACING LINE" ON 15 Aug 2026, and the change is
# the rule, not a loosening. Fault 6 put the LIGHT in the universal tier deliberately —
# EP26's discarded card was a man at a desk, so a lighting rule that skipped the
# kitchen-table clip would skip the exact picture it was written for. What must still
# never appear here is a racing line: no rail, no silks, no strides.
check("the kitchen-table clip raises no RACING line", keys(kitchen) <= {"lighting"},
      "EP23's broll-ratings-pencil-and-weights is exactly this and must stay exempt; "
      "a guard everyone ignores is worse than no guard")
check("  …and it IS asked for the light, which is the point of the universal tier",
      keys(kitchen) == {"lighting"}, keys(kitchen))

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
    check("the non-racing clip is given no RACING line",
          graded.get("broll-ratings-pencil-and-weights", set()) <= {"lighting"},
          graded.get("broll-ratings-pencil-and-weights"))
    # 🔴 AND THE QUIET HALF, WHICH IS WHAT MAKES THIS A CHECK AND NOT A COMPLAINT.
    check("it does NOT re-flag the lines EP23 already got right (strides, silks, turf)",
          all(not ({"strides", "silks", "turf"} & graded[t]) for t in racing),
          {t: sorted(graded[t]) for t in racing})

print("\n-- IT APPLIES, IT DOES NOT ASK (Jodie, 14 Aug 2026) --")
# EP24 stopped at the credit check for six prompts missing lines the machine already had
# the exact words for. A halt is for a DECISION, and there is none here: the lawful
# wording is computed and there is one of it. Same ruling as auto-WIDE and auto-broll.
# And the halt was worse than noise — _broll_prompt runs PER CLIP, so it named one clip
# when six were short: six halts in a row, each needing a human before the next appeared.
bare = ("Photoreal cinematic wide shot of a field of racehorses galloping on lush green "
        "turf at an Australian racecourse, mounted jockeys in bright silks, the horses at "
        "clearly different points in their stride. Present day, natural daylight.")
fixed, applied, unfixable = R.apply_rules(bare)
check("a prompt missing standing lines is CORRECTED, not refused", bool(applied), applied)
check("  and the corrected prompt satisfies the rules", not R.check_prompt(fixed),
      sorted(g["key"] for g in R.check_prompt(fixed)))
check("  with nothing left for a human", unfixable == [], unfixable)
check("  it says what it changed", all(isinstance(a, str) and a for a in applied),
      "a silent rewrite of the words that produced a clip is not auditable")
check("  and it does not touch a prompt that is already right",
      R.apply_rules(GOOD) == (GOOD, [], []))

print("\n-- what it adds is FACTS, never the shot --")
check("it does not invent a subject, framing or action",
      all(w not in fixed.lower().replace(bare.lower(), "")
          for w in ("close-up", "tracking shot", "slow motion", "aerial")),
      "the rules state what must be true; they do not direct the clip")
check("the bend wording is used on a bend and the straight wording on a straight",
      "curves with the track" in R.apply_rules(bare + " The field rounds the bend.")[0]
      and "curves with the track" not in fixed,
      "a straight line pasted into a bend is A21's second finding, rebuilt by the fixer")

print("\n-- THE HALT THAT IS LEFT: what it genuinely cannot decide --")
# EP24's wide sweep already said the rail had "a grandstand and gum trees beyond".
# Appending "open green turf infield beyond it" leaves TWO different far sides — a
# contradiction, not a missing line, and which one is right depends on the shot: a
# FAR-SIDE rail is the outside boundary and a grandstand beyond it is correct.
conflict = ("Photoreal wide shot of a field of racehorses galloping on lush green turf, "
            "a white running rail running away across the frame with a grandstand and "
            "gum trees beyond, mounted jockeys in bright silks, the horses at clearly "
            "different points in their stride.")
c_fixed, c_applied, c_unfix = R.apply_rules(conflict)
check("a competing claim about what lies beyond the rail STOPS for a person",
      bool(c_unfix), "auto-adding a second far side is how incoherent geometry is made")
check("  and it changes NOTHING while it asks", c_fixed == conflict,
      "a half-applied contradiction is worse than the original")
check("  and it explains the choice rather than naming a rule key",
      "outside boundary" in " ".join(c_unfix) and "grandstand" in " ".join(c_unfix),
      "'rail-beyond' tells her nothing (docs/PP-operator-box-rule.md)")

print("\n-- a crowd shot with no horses is NOT given horses --")
# 🔴 THE FAULT AUTO-APPLY WOULD OTHERWISE HAVE SHIPPED. EP24's broll-glamour-raceday-crowd
# is people on the lawn with no horse in it. The first classifier matched "racecourse" and
# "race day", so it was graded as a racing shot — a halt was only noise, but a FIXER would
# have written jockeys' silks and out-of-phase strides into a shot of a crowd.
lawn = ("Photoreal cinematic medium wide shot of a busy Australian racecourse lawn on a "
        "big race day, a mixed present-day crowd of men and women standing and talking "
        "in the sunshine, about half in Akubra-style broad-brimmed hats in a range of "
        "natural colours, a grandstand thrown well out of focus behind.")
check("a lawn crowd shot is not treated as a racing shot", not R.has_horses(lawn))
l_fixed, l_applied, l_unfix = R.apply_rules(lawn)
# The LIGHT is added — it is added to every picture — and nothing else is. That is the
# assertion that survives Fault 6: what this case has always been about is that no RACING
# line reaches a shot of a crowd, and a lighting line is not a racing line.
check("  only the light is added to it — no racing line",
      [a for a in l_applied if "Bright, warm" not in a] == [] and l_unfix == [],
      (l_applied, l_unfix))
check("  no silks are written into it", "silks" not in l_fixed)
check("  and no rail is written into it", "running rail" not in l_fixed)
check("  and 'a RANGE of natural colours' counts as the hat range",
      "hat-variety" not in keys(lawn),
      "demanding the synonym 'variety' asks for a copy-paste, not for the fact")
check("a grandstand in the background is NOT a crowd",
      "hat-variety" not in keys(GOOD + " A grandstand stands beyond the far turn."),
      "a building is not people; this asked a wide course shot for hat colours")

print("\n-- the fixer is wired where prompts are actually generated --")
prov = (HERE / "providers.py").read_text(encoding="utf-8")
# To the NEXT def, not a character count — the first version sliced 3000 chars and the
# function outgrew it, so two cases failed on code that was right. A test that measures
# in characters is measuring the wrong thing.
body = prov.split("def _broll_prompt")[1].split("\n    def ")[0]
check("_broll_prompt applies the rules", "broll_prompt_rules.apply_rules" in body,
      "applied anywhere else and a prompt could still be submitted without the lines")
check("  and returns the CORRECTED prompt, not the original",
      "return fixed" in body, "the fix must be what is actually generated")
check("  the correction is written back to episode.json",
      "_save_broll_prompt" in body,
      "the file is the audit trail; it must show the words that produced the clip")
check("  it still halts on what it cannot decide", "unfixable" in body)
check("  and that halt names the file the wording lives in",
      "broll-registry.md" in body,
      "a halt that does not say where the words are is a halt she cannot clear")

print("\n-- the registry carries the reasoning, which code cannot hold --")
reg = (HERE.parent / "docs/broll-registry.md").read_text(encoding="utf-8")
check("§5 is in the registry", "ONE SIDE OF THE RAIL" in reg)
check("  with the evidence table of what EP23 actually asked for",
      "running away across the frame" in reg)
check("  and it is stated POSITIVELY, per the file's own rule",
      "open green turf infield beyond it" in reg)

print("\n-- 1b: WHICH WAY UP (EP24's cover B came back upside down) --")
# 🔴 The A/B pick caught it, as designed — but the pick is a SAFETY NET, and one of two
# options was wasted. Had both been wonky the choice was between two unusable covers.
# ⚠️ NOT A NEGATION: "not upside down" cannot be drawn. A model must put the horizon
# somewhere, and untold it puts it anywhere. The line says where everything GOES.
hero = ("Portrait 2:3 cover hero, photoreal, a field of thoroughbred racehorses "
        "galloping on lush green Australian turf, jockeys up in bright varied silks.")
oriented, changed = R.apply_orientation(hero)
check("a racing hero with no orientation stated gets the line", changed)
check("  and it says where the sky and the turf GO, positively",
      all(s in oriented for s in ("sky at the top", "horizon level", "at the bottom")),
      oriented[-160:])
check("  and it says the horses are upright and on the ground",
      "horses upright and running along the ground" in oriented)
check("  applying it twice does not double it",
      R.apply_orientation(oriented) == (oriented, False))
check("a hero that already states orientation is left alone",
      R.apply_orientation(hero + " Horizon level near the middle.")[1] is False)
check("a NON-racing image is not given racing orientation",
      R.apply_orientation("Close overhead shot of hands marking a ruled notebook page.")
      == ("Close overhead shot of hands marking a ruled notebook page.", False),
      "orientation is stated for the racing images, not for every picture")

prov_cov = prov.split("def _cover_prompts")[1].split("\n    def _save_cover_prompts")[0]
check("_cover_prompts applies the frame rules to BOTH heroes",
      prov_cov.count("apply_frame_rules(") == 2,
      "one hero left unstated is the one that comes back wrong")
check("  and returns the CORRECTED prompts", "return fa, fb" in prov_cov)
check("  and writes them back to episode.json",
      "_save_cover_prompts" in prov_cov,
      "the file is the audit trail for the image that was bought")

# 🔴 THE OTHER FUNNEL, WHICH A22 DID NOT REACH. (14 Aug 2026, the day after.)
# Everything above passed the whole time and the racing B-ROLL prompts still had no
# orientation: the covers go through `providers._cover_prompts`, the b-roll goes through
# `apply_rules`, and A22 was installed at one of them. **A guard installed at one funnel
# says nothing about the other** — and the tell was that this file was entirely green
# while EP25 carried six unoriented racing prompts.
print("\n-- 1b, second funnel: the RACING B-ROLL prompts, not only the covers --")
bare = ("Photoreal cinematic wide shot of a field of racehorses galloping on lush green "
        "turf at an Australian racecourse. " + GOOD_RAIL + ". The horses at clearly "
        "different points in their stride, legs out of phase across the field, "
        "anatomically correct with four legs and one head. Mounted jockeys crouched in "
        "bright racing silks, actively riding. The rail is one clean unbroken line, "
        "evenly spaced upright posts and a level top rail. Warm golden-hour light, "
        "generously exposed.")
check("a racing b-roll prompt with everything BUT orientation is not clean",
      keys(bare) == {"orientation"}, keys(bare))
fixed_b, applied_b, unfix_b = R.apply_rules(bare)
check("  apply_rules — the b-roll funnel — adds the line by itself",
      not R.needs_orientation(fixed_b) and not unfix_b,
      f"still missing; unfixable={unfix_b}")
check("  and says it did", any("upright orientation" in a for a in applied_b),
      str(applied_b))
check("  and the prompt's own words are kept, the line appended",
      fixed_b.startswith(bare.rstrip(". ")), fixed_b[:120])
check("  CONTROL: a non-racing b-roll prompt is not given orientation",
      "upright orientation" not in
      R.apply_rules("Close overhead shot of hands marking a ruled notebook page.")[0])
check("  ONE definition serves both funnels",
      R.FIXES["orientation"] is R.ORIENTATION,
      "a second copy of the line is a second thing to keep in step")

# ══ FAULTS 6 AND 7 — THE LIGHT, AND THE RAIL'S OWN LINE (Jodie, 15 Aug 2026) ══════
#
# EP26's images came back too DARK, and its running rail had an unnatural KINK. Both are
# stated POSITIVELY, because a model cannot draw "not dark" or "no kink": told nothing it
# picks the safe middle exposure and an arbitrary line.
print("\n-- Fault 6: the LIGHT, on EVERY generated image --")

DESK = ("Photoreal close shot of a man at a desk in a quiet room, a printed form guide "
        "open in front of him and a pen in his hand.")
check("a desk scene has no horses, no crowd and no rail",
      not R.has_horses(DESK) and not R.CROWD_WORDS.search(DESK)
      and not R.shows_a_rail(DESK))
check("  …and is STILL asked for the light — the universal tier",
      keys(DESK) == {"lighting"}, keys(DESK))
lit, applied_l, unfix_l = R.apply_rules(DESK)
check("  apply_rules lights it, with no other line added",
      "golden-hour" in lit and "running rail" not in lit and not unfix_l, lit[-140:])
check("  and the indoor case is named — 'golden hour' means nothing at a desk",
      "indoor, desk or portrait scene is warmly and generously lit" in lit)
check("  EP26's actual complaint is answered: the subject is bright and visible",
      "subject bright and clearly visible" in lit)

# THE CONTROL THAT MAKES THE RULE WORTH HAVING. The cover brief ALREADY said "bright
# natural daylight" while EP26 came back dim — a pattern the failing prompts match is a
# rule that changes nothing.
check('  "bright natural daylight" alone does NOT satisfy it',
      "lighting" in keys("A man at a desk in bright natural daylight, clean and cheerful."))
check("  a prompt that already says golden hour is left alone",
      "lighting" not in keys(DESK + " Warm golden-hour light across the room."))
check("  …and so is one that says it in its own words",
      "lighting" not in keys(DESK + " The room is warmly and generously lit."))

print("\n-- Fault 7: the RAIL is one smooth, true line --")
RAILED = ("Photoreal wide shot of a field of racehorses on lush green turf, the whole "
          "field running on ONE side of a single white running rail, open green turf "
          "infield beyond it.")
check("a shot with a rail is asked for the rail's LINE",
      "rail-smooth" in keys(RAILED), keys(RAILED))
r_fixed, r_applied, _ = R.apply_rules(RAILED)
# ⚠️ THE TAIL, NOT THE WHOLE STRING. `_add_sentence` capitalises the first letter as it
# appends, so the constant itself — which starts lower-case, to read as a clause — is
# never literally present in the result. Asserting the constant tested the capitalisation,
# not the wording.
check("  the line is added, and it is the STRAIGHT wording here",
      "running true and even along the track" in r_fixed
      and "sweeping curve" not in r_fixed, r_fixed[-200:])
check("  it says the posts are even and the top rail level",
      "evenly spaced upright posts and a level top rail" in r_fixed)
b_fixed, _, _ = R.apply_rules(RAILED + " The field rounds the home turn.")
check("  on a BEND it is the sweeping-curve wording, because a curve is CORRECT",
      "single smooth even sweeping curve" in b_fixed)
# 🔴 THE COLLISION THIS RULE COULD HAVE CAUSED. `STRAIGHT_RAIL` looks for "dead straight"
# and "perfectly level"; either phrase inside these lines would manufacture the
# straight-rail-on-a-bend contradiction the checker already halts on.
for _name, _line in (("straight", R.RAIL_SMOOTH_STRAIGHT), ("bend", R.RAIL_SMOOTH_BEND)):
    check(f"  the {_name} wording cannot trip the straight-rail-on-a-bend contradiction",
          not R.STRAIGHT_RAIL.search(_line), _line)
check("  and neither leaves anything missing after auto-apply",
      not keys(b_fixed) and not keys(r_fixed), f"{keys(r_fixed)} / {keys(b_fixed)}")

# 🔴 THE REGRESSION, AND IT IS EP26'S REAL COVER. Hero A is a man at a desk with FRAMED
# RACING PHOTOGRAPHS behind him: it mentions racehorses, jockeys and galloping — so
# `has_horses` is true, correctly — and then spends a clause saying there is no rail.
# Gated on horses, this rule appended "The white running rail is one clean unbroken
# line…" to it. That is not a missing line, it is a CONTRADICTION, and a worse picture
# than the kink the rule exists to prevent. Found by the control, on the real artefact,
# before this test existed.
print("\n-- the rail rule may only be applied to a picture that HAS a rail --")
NO_RAIL = ("Photoreal portrait of a man at a desk, framed horse racing photographs on "
           "the wall behind him — racehorses and mounted jockeys galloping on lush green "
           "turf. NO FENCE, NO RUNNING RAIL AND NO RAILINGS anywhere in the photograph "
           "or inside any of the framed pictures.")
check("EP26's cover hero A shape: horses ARE mentioned", R.has_horses(NO_RAIL))
check("  …but the picture has no rail, and the word appears only inside negations",
      not R.shows_a_rail(NO_RAIL))
check("  so the rail rule does not fire", "rail-smooth" not in keys(NO_RAIL), keys(NO_RAIL))
nr_fixed, nr_applied = R.apply_frame_rules(NO_RAIL)
check("  and the cover funnel never writes a rail into it",
      "unbroken line" not in nr_fixed, nr_fixed[-160:])
check("  while the LIGHT still reaches it — the point of the universal tier",
      "golden-hour" in nr_fixed)
check("  an affirmative rail in the SAME prompt would still count",
      R.shows_a_rail("No dirt or sand. A single white running rail runs along the inside."))
check("  a negation in an EARLIER sentence does not suppress a real rail",
      R.shows_a_rail("There are no hats in this shot. The white running rail curves away."))

print("\n-- both new rules come through BOTH funnels, from ONE definition --")
check("the cover funnel calls apply_frame_rules, not a second copy of the words",
      prov_cov.count("apply_frame_rules(") == 2
      and "apply_orientation(" not in prov_cov,
      "providers must ask this module for the lines")
check("  FRAME_KEYS is what a cover takes: the light, which way up, the rail's line",
      set(R.FRAME_KEYS) == {"lighting", "orientation", "rail-smooth"}, str(R.FRAME_KEYS))
check("  ONE definition of the light serves both funnels",
      R.FIXES["lighting"] is R.LIGHTING)
check("  the rail's line is SHOT-AWARE, so it is derived not stored",
      R.FIXES["rail-smooth"] is None and R.rail_smooth_for("a bend") is R.RAIL_SMOOTH_BEND)
_cov_railed, _cov_applied = R.apply_frame_rules(
    "Portrait hero, racehorses galloping past a single white running rail on green turf.")
check("  a cover that DOES show a rail gets the rail line through the cover funnel",
      "unbroken line" in _cov_railed, str(_cov_applied))

# ══ EP27 — A BEND MUST NEVER RECEIVE "DEAD STRAIGHT" (Jodie's law, 16 Aug 2026) ═══
#
# 🔴 EP27 HALTED ON `broll-the-field-turning-for-home`, and the halt was correct: nothing
# was generated and nothing was charged. The CAUSE was fault #2 in its purest form — two
# descriptions of one thing, drifted apart:
#
#     detector: re.compile(r"dead straight|perfectly level", re.I)    ← any case, either
#     remover:  re.sub(r"\s*dead straight and perfectly level\s*",…)  ← ONE literal, CASE
#                                                                       SENSITIVE, "and"
#
# The prompt said "a single DEAD STRAIGHT, PERFECTLY LEVEL white running rail". The check
# fired; the fix could not find a phrase that was plainly there; the tool halted a human
# over words it was looking straight at.
#
# THE LAW: real racing tracks curve. A rail is wrong only when it KINKS. On a bend it
# sweeps in a long, smooth, even curve; on a straight it runs straight; and "dead
# straight" / "straight and true" / "perfectly level" are never forced onto a bend.
print("\n-- EP27: the straight-rail claim is found AND removed, in any wording --")

EP27_SHAPE = ("Photoreal cinematic wide side-on shot of a full field of racehorses "
              "sweeping around a bend and straightening for home. The whole field "
              "running on ONE side of a single DEAD STRAIGHT, PERFECTLY LEVEL white "
              "running rail — the rail is the inside boundary of the track, open green "
              "turf infield beyond it and no horses on the far side. The white running "
              "rail is one clean unbroken line that follows the track in a single smooth "
              "even sweeping curve, evenly spaced upright posts and a level top rail. "
              "Warm golden-hour light, generously exposed.")
check("EP27's shape is a bend shot carrying a dead-straight claim",
      bool(R.BEND_WORDS.search(EP27_SHAPE)) and bool(R.STRAIGHT_RAIL.search(EP27_SHAPE)))
e_fixed, e_applied, e_unfix = R.apply_rules(EP27_SHAPE)
check("  it is REMOVED, not reported as unlocatable", not e_unfix, str(e_unfix))
check("  and the claim is gone", not R.STRAIGHT_RAIL.search(e_fixed),
      [m.group(0) for m in R.STRAIGHT_RAIL.finditer(e_fixed)])
check("  the sentence still reads — no stranded comma left behind",
      "single white running rail" in e_fixed and " , " not in e_fixed
      and ", ," not in e_fixed, e_fixed[:200])
check("  the message QUOTES what it removed", any("DEAD STRAIGHT" in a for a in e_applied),
      str(e_applied))
check("  nothing is left failing", not keys(e_fixed), keys(e_fixed))

# EVERY WORDING THE PHRASE HAS EVER ARRIVED IN, and the ones Jodie's law names. The point
# is that DETECTION AND REMOVAL CANNOT DISAGREE — they are built from one list now.
BENDY = ("Wide shot of a field of racehorses rounding the home turn on lush green turf, "
         "the whole field on ONE side of a single white running rail, open green turf "
         "infield beyond it, jockeys in silks at different points of stride, "
         "anatomically correct, horizon level and sky at the top, warm golden-hour light.")
for _variant in ("dead straight and perfectly level", "DEAD STRAIGHT, PERFECTLY LEVEL",
                 "Dead Straight and Perfectly Level", "dead-straight", "straight and true",
                 "perfectly level", "ruler-straight", "perfectly straight"):
    _p = BENDY.replace("a single white running rail",
                       f"a single {_variant} white running rail")
    _f, _a, _u = R.apply_rules(_p)
    check(f"  {_variant!r} is detected and removed",
          R.STRAIGHT_RAIL.search(_p) and not R.STRAIGHT_RAIL.search(_f) and not _u,
          f"unfix={_u}")

# 🔴 THE STRUCTURAL ASSERTION, and it is the one that stops EP27 recurring in a NEW
# wording: every claim the DETECTOR knows about must also be removable, because they are
# generated from the same list. Read off `_STRAIGHT_CLAIMS` itself, so a claim added
# later is covered the day it is added, with nothing to remember here.
for _pat in R._STRAIGHT_CLAIMS:
    _sample = _pat.replace("[- ]", " ")
    _p = BENDY.replace("a single white running rail",
                       f"a single {_sample} white running rail")
    _f, _a, _u = R.apply_rules(_p)
    check(f"  every DETECTED claim is also REMOVABLE: {_sample!r}",
          bool(R.STRAIGHT_RAIL.search(_p)) and not R.STRAIGHT_RAIL.search(_f) and not _u,
          f"detectable-but-unremovable is the EP27 halt; unfix={_u}")

print("\n-- a bend must SAY it sweeps; a straight must not be given a curve --")
# On a bend, "true and even along the track" is not enough: it is right for a straight and
# says nothing about the shot. The model chooses the line it is not told, and the line it
# chose is the one that kinked.
_bend_flat = BENDY + " The rail is one clean unbroken line running true and even along " \
                     "the track, evenly spaced upright posts and a level top rail."
check("straight wording does NOT satisfy the rule on a bend",
      "rail-smooth" in keys(_bend_flat), keys(_bend_flat))
_bf, _ba, _bu = R.apply_rules(_bend_flat)
check("  and the CURVE wording is applied",
      "sweeping curve" in _bf and not _bu, _bf[-180:])

# THE OTHER DIRECTION, which is the control: a straight shot keeps the straight wording
# and is never handed a curve it does not have.
STRAIGHTY = ("Wide shot of a field of racehorses galloping down the straight on lush "
             "green turf, the whole field on ONE side of a single white running rail, "
             "open green turf infield beyond it, jockeys in silks at different points of "
             "stride, anatomically correct, horizon level and sky at the top, warm "
             "golden-hour light.")
check("a straight shot is not a bend", not R.BEND_WORDS.search(STRAIGHTY))
_sf, _sa, _su = R.apply_rules(STRAIGHTY)
check("  it gets the STRAIGHT wording",
      "running true and even along the track" in _sf and not _su, _sf[-180:])
check("  and is never given a sweeping curve", "sweeping curve" not in _sf)
check("  and no dead-straight claim is invented for it",
      not R.STRAIGHT_RAIL.search(_sf),
      "the fix removes the phrase; it must never ADD it")

# ══ THE AUTO-INJECT, SWEPT OVER THE REAL EPISODES (0b20c05, verified 14 Aug 2026) ══
#
# Every case above is a FIXTURE — a prompt written here to have the gap being tested.
# That proves the rule and says nothing about the prompts episodes actually carry, which
# is the same distance as "the check works" from "the check is reaching the artefact".
# This reads the real `broll[]` of every episode A21 grades and asserts the property that
# matters: after the auto-apply, a human is left with NO MECHANICAL WORK — only genuine
# ambiguity may survive. The coverage is DERIVED from what is on disk, so the next
# episode is swept the day it exists, with nothing to add here.
import os                                                            # noqa: E402
PP = Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
import ep_paths as _ep                        # renamed on publish; resolve by NUMBER

print(f"\n-- the auto-inject over REAL prompts, EP{R.FROM_EP} forward --")
#
# 🆕 EXTENDED 15 AUG 2026 FOR FAULTS 6 AND 7, AND THE EXTENSION IS THE POINT.
# It used to sweep the B-ROLL only, and only the prompts with horses or a crowd in them —
# which is exactly the coverage that would have missed both new faults: the light belongs
# on the DESK scenes this loop skipped, and the covers go through the OTHER funnel, which
# it never opened at all. **A sweep that only looks where the old rules applied is a
# sweep that can only confirm the old rules.** It now reads EVERY generated-image prompt
# on this machine — both funnels, every clip, covers included — and asserts the two
# properties Jodie asked for:
#     · EVERY generated image carries the light;
#     · the rail's line lands ONLY where the picture actually has a rail.
graded, injected, leftovers, covers, unlit, wrong_rail = 0, 0, [], 0, [], []
for _d in sorted(PP.glob("PP-EP*")):
    try:
        _n = int(_d.name.split("-")[1][2:])
    except (IndexError, ValueError):
        continue
    _epj = _d / "docs/episode.json"
    if _n < R.FROM_EP or not _epj.is_file():
        continue
    _ep = json.loads(_epj.read_text(encoding="utf-8"))

    # ── FUNNEL 1: the cover heroes, which this sweep never used to open ──────────
    for _slot in ("hero_a_prompt", "hero_b_prompt"):
        _p = (_ep.get("cover") or {}).get(_slot)
        if not _p:
            continue
        covers += 1
        _new, _applied = R.apply_frame_rules(_p)
        _after = {g["key"] for g in R.check_prompt(_new)}
        if "lighting" in _after:
            unlit.append(f"EP{_n} {_slot}")
        if "unbroken line" in _new and "unbroken line" not in _p \
                and not R.shows_a_rail(_p):
            wrong_rail.append(f"EP{_n} {_slot}: a rail written into a picture with none")

    # ── FUNNEL 2: every b-roll prompt, INCLUDING the ones with no horses in them ──
    for _b in _ep.get("broll") or []:
        _p = _b.get("prompt") or ""
        if not _p.strip():
            continue
        graded += 1
        _new, _applied, _unfix = R.apply_rules(_p)
        if _applied:
            injected += 1
        _after = {g["key"] for g in R.check_prompt(_new)}
        if "lighting" in _after:
            unlit.append(f"EP{_n} {_b.get('target', '?')}")
        if "unbroken line" in _new and "unbroken line" not in _p \
                and not R.shows_a_rail(_p):
            wrong_rail.append(f"EP{_n} {_b.get('target', '?')}: a rail written in")
        # The older assertion, kept, but now only for the shots the older rules grade.
        if (R.has_horses(_p) or R.CROWD_WORDS.search(_p)) and _after:
            leftovers.append(f"EP{_n}: {sorted(_after)} still missing after auto-apply")
        # A CONTRADICTION is allowed to survive as unfixable — that is the decision.
        # A merely ABSENT line is not.
        if _unfix and not R._BEYOND_NON_TURF.search(_p):
            leftovers.append(f"EP{_n}: halted a human over {_unfix}")

if graded or covers:
    check(f"{graded} real b-roll prompt(s) and {covers} real cover hero(es) swept — "
          f"BOTH funnels, {injected} had lines injected", True)
    check("  a MECHANICALLY short prompt never reaches a human",
          not leftovers, "; ".join(leftovers[:4]))
    check("  FAULT 6: every generated image on this machine carries the light",
          not unlit, "; ".join(unlit[:6]))
    check("  FAULT 7: the rail's line lands ONLY where the picture has a rail",
          not wrong_rail, "; ".join(wrong_rail[:6]))
else:
    print(f"  ·  skipped — no episode from EP{R.FROM_EP} on this machine")

print(f"\ntotal: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
