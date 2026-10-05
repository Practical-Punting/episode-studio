"""The b-roll rules ask the right question of the right shot — and the four EP49 rules bite.

    python engine/test_broll_shot_aware_rules.py

Jodie's rulings, 5 Oct 2026 (EP55):
  · `silks` only on a RIDDEN horse; `turf` only on a horse ON A TRACK. Both used to fire
    on a led horse, a stabled horse and a horse walking past its owners — and applied,
    the silks fix writes "jockeys up and crouched" onto a led horse, which is the crouch
    rule (c) exists to stop. Neither may loosen anything for a ridden horse on a track.
  · The four rules written into docs/broll-registry.md on 20 Sep (a–d) after four rejected,
    paid-for clips — enforced nowhere until now:
      a. no more than FOUR horses or people (the out-of-focus crowd is the exception)
      b. saddlecloths are plain, no numbers
      c. a walking horse is riderless and led; a rider only at a gallop
      d. the rail stands BEHIND the horses
  · And CLAUDE.md §10 a second time: the corrector's own stride line ends "…across the
    field", which re-read as a racing shot and asked a led yearling for silks.

Every case here fails on the code before 5 Oct (run it against HEAD~ to watch it).
"""
from __future__ import annotations

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


def keys(p, shot=None):
    try:
        return {g["key"] for g in R.check_prompt(p, shot=shot)} if shot else \
               {g["key"] for g in R.check_prompt(p)}
    except TypeError:                                  # the old signature has no `shot`
        return {g["key"] for g in R.check_prompt(p)}


LED = ("Photoreal cinematic medium shot. A strapper in a flat cap leads one fit bay "
       "thoroughbred at a relaxed walk along a grass path beside the training track, no rider "
       "up, the horse calm with its head low.")
STABLE = ("Photoreal cinematic medium shot. A trainer runs a hand down a thoroughbred's "
          "foreleg in an Australian stable yard while a strapper holds the horse's head, no "
          "rider.")
GALLOP = ("Photoreal cinematic wide shot of three racehorses galloping on the course, jockeys "
          "crouched and riding hard.")

print("\n-- 1. silks: only a RIDDEN horse --")
check("a horse LED at a walk is not asked for silks", "silks" not in keys(LED), keys(LED))
check("a horse in a STABLE YARD is not asked for silks", "silks" not in keys(STABLE), keys(STABLE))
check("CONTROL: a ridden gallop with no silks named is STILL asked for them",
      "silks" in keys(GALLOP), keys(GALLOP))
check("CONTROL: a field rounding the turn with no rider named is still asked for silks",
      "silks" in keys("Four racehorses rounding the home turn on the course."))

print("\n-- 2. turf: only ON A TRACK --")
check("a stable yard is not asked for turf", "turf" not in keys(STABLE), keys(STABLE))
check("a led horse on a path beside the track is not asked for turf",
      "turf" not in keys(LED), keys(LED))
check("a mounting-yard lawn is not asked for turf",
      "turf" not in keys("Two owners on the lawn of a mounting yard watch their horse walk "
                         "past, led by its strapper, no rider up."))
check("CONTROL: a ridden gallop with no turf named is STILL asked for it",
      "turf" in keys(GALLOP), keys(GALLOP))
check("CONTROL: a gallop past a crowd on the lawn is still asked for turf",
      "turf" in keys(GALLOP + " A crowd watches from the lawn."))

print("\n-- 3a. no more than FOUR horses or people --")
for p, what in (("Wide shot of a field of racehorses galloping on green turf.", "a field"),
                ("Eight thoroughbreds walk onto the track, each led by a strapper.", "eight"),
                ("Twelve saddled thoroughbreds parade in the mounting yard.", "twelve"),
                ("Sixteen people stand along the rail.", "sixteen people"),
                ("A crowd of runners swings into the straight.", "a crowd of runners")):
    check(f"'{what}' is caught", "four-max" in keys(p), keys(p))
check("CONTROL: four horses is fine", "four-max" not in keys("Four racehorses gallop on turf."))
check("CONTROL: the out-of-focus background crowd is the exception",
      "four-max" not in keys(GALLOP + " A mixed crowd of fifty racegoers far out of focus "
                                      "in the background."))
check("CONTROL: 'the whole field' in the standing rail line is not a count",
      "four-max" not in keys(R.RAIL_STRAIGHT))
_f, _a, _u = R.apply_rules("Wide shot of a field of racehorses galloping on green turf.")
check("the corrector never rewrites a count — it hands it to a person",
      "a field of racehorses" in _f and any("FOUR" in u for u in _u), _u)

print("\n-- 3b. saddlecloths are plain --")
check("a named saddlecloth without 'plain … no numbers' is caught",
      "saddlecloth" in keys("Three horses gallop on turf, saddlecloths flapping, jockeys in silks."))
check("a ridden gallop is asked for it even when no saddlecloth is named",
      "saddlecloth" in keys(GALLOP))
_f, _a, _u = R.apply_rules(GALLOP)
check("the corrector adds the registry's own words",   # _add_sentence capitalises the line
      "plain saddlecloths, no numbers" in _f.lower(), _f[-300:])
check("CONTROL: a led horse with no saddlecloth named is not asked",
      "saddlecloth" not in keys(LED), keys(LED))

print("\n-- 3c. a walking horse is riderless and led --")
WALK_NO_HANDLER = "A bay thoroughbred walks slowly across the mounting yard."
check("a walking horse that never says who leads it is caught",
      "led" in keys(WALK_NO_HANDLER), keys(WALK_NO_HANDLER))
_f, _a, _u = R.apply_rules(WALK_NO_HANDLER)
check("  and the corrector adds 'riderless and led by a strapper'",
      "riderless and led by a strapper" in _f, _f)
JOCKEY_WALK = "Three horses walk onto the track with jockeys up, crouched in the irons."
check("a JOCKEY on a walking horse is a contradiction for a person",
      "rider-on-a-walking-horse" in keys(JOCKEY_WALK), keys(JOCKEY_WALK))
check("CONTROL: a jockey on a GALLOPING horse is fine",
      "rider-on-a-walking-horse" not in keys(GALLOP))
check("CONTROL: 'no rider up' on a led horse is not a rider",
      "rider-on-a-walking-horse" not in keys(LED))

print("\n-- 3d. the rail stands BEHIND the horses --")
RAIL = ("Three racehorses gallop on green turf beside a single white running rail, jockeys "
        "in silks.")
check("a rail with horses that never says where it stands is caught",
      "rail-behind" in keys(RAIL), keys(RAIL))
_f, _a, _u = R.apply_rules(RAIL)
check("  and the corrector says it is behind them, positively",
      "rail stands behind the horses" in _f and not _u, (_f[:300], _u))
check("a rail in the near FOREGROUND is a contradiction for a person",
      "rail-in-front" in keys("Three racehorses gallop on turf, the white running rail in "
                              "the near foreground, jockeys in silks."))
check("  and so is shooting THROUGH the rail",
      "rail-in-front" in keys("Seen through the running rail, three racehorses gallop on turf."))
check("CONTROL: a rail behind the field is fine",
      "rail-behind" not in keys(RAIL + " The rail runs behind the field."))

print("\n-- §10: the corrector may not reclassify the shot with its own words --")
YEARLING = ("Photoreal cinematic medium shot of a handler walking a leggy yearling slowly past "
            "the boards of an Australian sale ring, the young horse alert.")
_f, _a, _u = R.apply_rules(YEARLING)
check("a led yearling, once corrected, is not then asked for silks",
      not any("silks" in u or "saddlecloth" in u for u in _u), _u)
check("  and the corrector added no rider to it", "jockeys up" not in _f.lower(), _f[-300:])

# ══ SECOND BATCH (Jodie, 5 Oct 2026, after Cowork read EP55's six prompts) ══════════
print("\n-- 4. strides: only TWO OR MORE horses moving together --")
LONE = ("One saddled thoroughbred gallops alone along the turf straight at trackwork, the rider "
        "low over the withers.")
WALKERS = "Three horses walk round the mounting yard, each riderless and led by a strapper."
check("ONE galloping horse is not given the stride line", "strides" not in keys(LONE), keys(LONE))
check("a group at a WALK is not given it", "strides" not in keys(WALKERS), keys(WALKERS))
check("a horse standing in a stable yard is not given it", "strides" not in keys(STABLE))
check("CONTROL: three horses galloping still are", "strides" in keys(GALLOP), keys(GALLOP))

print("\n-- 5. orientation: track, turf and running only for a ridden horse on a track --")
for name, p in (("a stable yard", STABLE), ("a led horse at a walk", LED)):
    o = R.apply_rules(p)[0]
    tail = o[o.find("orientation"):] if "orientation" in o else ""
    check(f"{name}: the orientation line says no turf, track or running",
          tail and not any(w in tail.split(".")[0] for w in ("turf", "track", "running")),
          tail[:160])
check("CONTROL: a ridden gallop keeps the full line",
      "running along the ground" in R.apply_rules(GALLOP)[0])

print("\n-- 6. the rail line: the right count, and never twice --")
ONE_ON_RAIL = ("One saddled thoroughbred gallops along the turf beside a single white running "
               "rail, the rider in bright silks.")
o = R.apply_rules(ONE_ON_RAIL)[0]
check("one horse is 'the horse', never 'the whole field'",
      "the whole field" not in o and "behind the horse," in o, o[:260])
PLACED_ALREADY = ("Three racehorses gallop on green turf, jockeys in silks, one white running rail "
                  "runs straight behind the field with evenly spaced posts.")
o = R.apply_rules(PLACED_ALREADY)[0]
check("a prompt that already PLACES the rail is not given a second rail sentence",
      "open green turf infield beyond it" not in o and "stands behind" not in o, o[:300])
check("CONTROL: a rail with nowhere to stand still gets one", "stands behind" in R.apply_rules(RAIL)[0])

print("\n-- 7. lighting: OUTDOOR or INDOOR, never both --")
o = R.apply_rules(GALLOP)[0]
check("an outdoor shot gets golden hour and no window or lamp",
      "golden-hour" in o and "window" not in o and "lamp" not in o, o[-200:])
i = R.apply_rules(GALLOP + " One horse is clear on the inside of the rail.")[0]
check("'the inside' of the rail is a racing word, not a room — still outdoor",
      "golden-hour" in i and "window" not in i, i[-200:])
d = R.apply_rules("Photoreal close shot of a man's hands at a kitchen table, a ring binder open.")[0]
check("an indoor shot gets window and lamp and no sunset",
      "window" in d and "golden-hour" not in d and "sunset" not in d, d[-200:])

print("\n-- 8. jockey headgear (Jodie, 5 Oct 2026) --")
o = R.apply_rules(GALLOP)[0].lower()
check("a ridden shot is given the skull cap under a peaked silk cap",
      "racing skull cap covered by a silk cap" in o and "short peak" in o, o[-400:])
check("  and never a 'safety helmet'", "safety helmet" not in o)
w = R.apply_rules("One horse gallops on the turf, a woman rider in bright silks.")[0].lower()
check("a single woman rider is 'her silks'", "colours as her silks" in w, w[-300:])
check("'safety helmet' in a ridden prompt is a finding for a person",
      "old-headgear" in keys(GALLOP + " Each rider in a safety helmet."))
check("EP49's 'no brim, no peak' is too",
      "old-headgear" in keys(GALLOP + " Each in a skullcap, no brim, no peak."))

print("\n-- 8b. a jockey ON FOOT, no horse in frame (EP55 cover B) --")
ON_FOOT = ("Portrait cover hero. A woman jockey in bright silks stands with her trainer in the "
           "mounting yard, saddle over her arm, no horse in frame.")
o, _ = R.apply_frame_rules(ON_FOOT)
check("the cover funnel gives no 'running horse' orientation to a picture with no horse",
      "running along the ground" not in o and "upright orientation" in o, o[-260:])
check("  and no 'field of horses in the middle third'", "field of horses" not in o, o[-260:])
check("CONTROL: a galloping cover hero still gets both",
      all(x in R.apply_frame_rules("Portrait cover hero, four racehorses galloping on the "
                                   "turf, jockeys in silks.")[0]
          for x in ("running along the ground", "MIDDLE THIRD")))

print("\n-- 9. a crowd at a rail with NO horses is not a rail fault --")
check("people leaning over the rail with no horse in shot is fine",
      "rail-in-front" not in keys("A crowd of racegoers leans over the white rail on the lawn, "
                                  "no horses in shot."))

print("\n-- 10. the writer is told, so the backstop is not reached --")
import ast                                                            # noqa: E402
_src = (HERE / "providers.py").read_text(encoding="utf-8")
# There are TWO `_commission_episode_json`s in providers.py; the real one is the one that
# writes the brief, so pick it by the brief's own opening words rather than by order.
_fn = next(n for n in ast.walk(ast.parse(_src))
           if isinstance(n, ast.FunctionDef) and n.name == "_commission_episode_json"
           and any(isinstance(c, ast.Constant) and isinstance(c.value, str)
                   and "You are writing episode.json" in c.value for c in ast.walk(n)))
_calls = [n for n in ast.walk(_fn) if isinstance(n, ast.Call)
          and isinstance(n.func, ast.Attribute) and n.func.attr == "commission_brief"]
check("the episode.json commission CALLS broll_prompt_rules.commission_brief()", bool(_calls))
_b = R.commission_brief() if hasattr(R, "commission_brief") else ""
for phrase in ("four", "never 'a field'", "riderless and led", "behind the horses",
               "plain saddlecloths, no numbers", "skull cap", "short peak"):
    check(f"  and the brief says {phrase!r}", phrase in _b.lower() or phrase in _b, _b[:120])

print(f"\nshot-aware b-roll rules: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
