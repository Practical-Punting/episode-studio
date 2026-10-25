#!/usr/bin/env python3
"""test_ppd_data.py — the proof-day guard's own controls (a guard is not trusted until it has been seen to FAIL).

    python test_ppd_data.py <job_dir>

Real data first (the Cox Plate Day file must pass), then one tampered copy per kind of fault — each must HALT,
naming the figure. Nothing is written.
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ppd_data as pdd  # noqa: E402

job = Path(sys.argv[1]).resolve()
real = json.loads((job / "overlay" / "ppd-proof-day.json").read_text(encoding="utf-8"))
fails = 0


def case(name, mutate, expect):
    global fails
    d = copy.deepcopy(real)
    mutate(d)
    try:
        pdd.prove(d)
        got = None
    except pdd.Halt as e:
        got = str(e)
    ok = (got is None) if expect is None else (got is not None and expect in got)
    fails += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {name}: " + ("passed" if got is None else got.splitlines()[1].strip()))


def sel(d, horse):
    return next(s for s in d["selections"] if s["horse"] == horse)


case("the real Cox Plate Day file", lambda d: None, None)
case("Cosmic Crusader shown at the $8.00 LISTED price", lambda d: sel(d, "Cosmic Crusader").update(win="8.00"), "win back")
case("a place dividend typed wrong", lambda d: sel(d, "Juja Kibo").update(place="2.70"), "place back")
case("a miss given a win dividend", lambda d: sel(d, "Maidoff").update(win="4.00"), "Maidoff")
case("the headline ROI typed wrong", lambda d: d["stated"]["win"].update(roi="+362.0%"), "win roi")
case("strike rate typed wrong", lambda d: d["stated"].update(strike_rate="66.7%"), "strike_rate")
case("trifecta runners wrong (combinations follow)", lambda d: d["trifecta"]["races"][0].update(runners=12), "trifecta cost")
case("trifecta top two not the first two home", lambda d: d["trifecta"]["races"][2].update(result=[12, 7, 1]), "trifecta")
case("backing-two split not adding to $10", lambda d: d["backing_two"]["races"][0]["b"].update(stake="5.00"), "do not add")
case("example race missing from a strategy", lambda d: d.update(example_race={"meeting": "Caulfield", "race": 1}), "example race")
print(f"\n{'ALL CONTROLS BEHAVE' if not fails else str(fails) + ' CONTROL(S) WRONG'}")
sys.exit(1 if fails else 0)
