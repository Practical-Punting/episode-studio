#!/usr/bin/env python3
"""test_fbx_data.py — the week's numbers guard must FAIL on a wrong total, and pass on the real week.

    python test_fbx_data.py <job_dir>

Control first (CLAUDE.md 4b): each mutation below is a believable typo in fbx-week.json; the
guard must refuse every one, naming the figure. Then the real W01 data must pass.
"""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fbx_data as fd  # noqa: E402

job = Path(sys.argv[1]).resolve()
real = json.loads((job / "overlay" / "fbx-week.json").read_text(encoding="utf-8"))


def attempt(wk):
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "overlay").mkdir()
        (Path(td) / "overlay" / "fbx-week.json").write_text(json.dumps(wk), encoding="utf-8")
        try:
            fd.load_week(Path(td))
            return None
        except fd.Halt as e:
            return str(e)


def mut(fn):
    w = copy.deepcopy(real)
    fn(w)
    return w


cases = {
    "win profit typo +5.57": mut(lambda w: w["stated_totals"]["win"].__setitem__("profit", "+5.57")),
    "ROI typo +98.5%": mut(lambda w: w["stated_totals"]["win"].__setitem__("roi", "+98.5%")),
    "a win price typo 2.09": mut(lambda w: w["selections"][1].__setitem__("win", "2.09")),
    "a place price dropped": mut(lambda w: w["selections"][0].__setitem__("place", None)),
    "tags out of order": mut(lambda w: w["selections"][3].__setitem__("tags", ["Core", "Value Select", "Victorian Select"])),
    "winner count 5": mut(lambda w: w["stated_totals"].__setitem__("won", 5)),
}
bad = 0
for name, wk in cases.items():
    r = attempt(wk)
    print(f"{'PASS' if r else 'FAIL'}  control '{name}' -> " + (r.splitlines()[1].strip() if r else "NOT CAUGHT"))
    bad += r is None
r = attempt(real)
print(f"{'PASS' if r is None else 'FAIL'}  real week {real['week']} accepted" + ("" if r is None else f": {r}"))
bad += r is not None
sys.exit(1 if bad else 0)
