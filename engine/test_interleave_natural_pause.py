"""twoway_interleave: a natural pause inside a turn is set aside only when the breaks are CLEARLY longer.

    python engine/test_interleave_natural_pause.py

EP59 (14 Nov 2026): Gordon's master has 18 silences ≥ 2 s for 17 scripted breaks — a 2.07 s pause at a
paragraph inside turn 11; every real break ≥ 4.07 s. CONTROLS: an ambiguous extra (close in length to a
break) and a short "break" below the floor must still leave the count wrong, so interleave refuses.
"""
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import twoway_interleave as ti   # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


breaks = [(10.0, 15.2), (30.0, 34.9), (50.0, 54.07), (70.0, 75.5)]
extra = (40.0, 42.07)
got = ti._keep_turn_breaks(sorted(breaks + [extra]), 4)
check("EP59's shape: the 2.07 s paragraph pause is set aside, the four breaks kept in time order",
      got == breaks, str(got))
check("the same count as the script: nothing is changed", ti._keep_turn_breaks(breaks, 4) == breaks)
amb = (40.0, 43.0)   # 3.0 s — a 4.07 s break is not 1.5x it
check("CONTROL: an extra pause close to a break is NOT set aside (interleave will refuse)",
      len(ti._keep_turn_breaks(sorted(breaks + [amb]), 4)) == 5)
short = [(10.0, 12.6), (30.0, 34.9), (50.0, 54.07), (70.0, 75.5)]
check("CONTROL: a kept 'break' under the 3 s floor means no setting aside (interleave will refuse)",
      len(ti._keep_turn_breaks(sorted(short + [(40.0, 41.2)]), 4)) == 5)
print(f"\nnatural pause: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
