"""broll_prompt_rules.episode_mix — somebody in every shot, and horses racing (Jodie, 14 Nov 2026).

    python engine/test_broll_episode_mix.py

Her words, on EP59: "There was at least one b roll with zero people nor horses. And I don't think
there were any horses racing ... let's make sure we include them in the future."
REAL FINDING FIRST: EP59's own prompts, graded as if they were EP60's, must show exactly what she
saw (an empty clip, no racing). Then a clean set passes, and EP57–59 are not re-graded.
"""
import json
import os
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import broll_prompt_rules as R  # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
ep59 = next(PP.glob("PP-EP59-*"), None)
if ep59:
    b59 = json.loads((ep59 / "docs/episode.json").read_text(encoding="utf-8"))["broll"]
    f = R.episode_mix(b59, 60)
    check("REAL: EP59's prompts (graded as EP60) flag a clip with neither people nor horses",
          any("neither people nor horses" in x for x in f), str(f)[:200])
    check("REAL: ... and that no clip shows horses racing", any("RACING" in x for x in f))
    check("EP59 itself is not re-graded", R.episode_mix(b59, 59) == [])

good = [{"target": "a", "prompt": "Three racehorses gallop on bright turf, plain saddlecloths, the rail behind them."},
        {"target": "b", "prompt": "A man studies the formguide at a kitchen table."},
        {"target": "c", "prompt": "One bay racehorse looks over a stable door, ears pricked."}]
check("a set with somebody in every shot and horses racing is clean", R.episode_mix(good, 60) == [],
      str(R.episode_mix(good, 60)))
empty = good + [{"target": "d", "prompt": "Mist over an empty racecourse at dawn. No people and no horses."}]
check("CONTROL: an empty course is flagged (a negated 'people' does not count)",
      [x for x in R.episode_mix(empty, 60) if x.startswith("d —")] != [])
led = [{"target": "e", "prompt": "A strapper leads one horse at a walk across the yard."}]
check("CONTROL: a led horse is not a race", any("RACING" in x for x in R.episode_mix(led, 60)))
check("the writer's brief carries both rules",
      "SOMEBODY IN EVERY SHOT" in R.commission_brief() and "HORSES RACING" in R.commission_brief())

print(f"\nb-roll episode mix: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
