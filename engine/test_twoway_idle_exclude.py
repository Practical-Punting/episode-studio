"""A pause a human has ruled out never becomes listening footage.

Jodie, 6 Oct 2026, on EP55: Steve's render vocalised gibberish and blips inside six of
his seven breaks. The audio can be cut; the PICTURE of those pauses still shows his mouth
moving. "Don't harvest any of those broken pauses as listening footage." Nothing could
say so: `idle_pool` banked every pause of 3.5s or more.

`build.idle_exclude` — {"speaker", "from_s", "to_s", "why"} on that man's master clock —
is passed to `idle_pool`, which skips any pause that overlaps one. No renders and no
writes: `idle_pool(..., write=False)` only lists.

FAIL-FIRST: INTERLEAVE=<pre-change twoway_interleave.py> -> red (no `exclude` argument).

Run: python engine/test_twoway_idle_exclude.py
"""
import importlib.util
import inspect
import os
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
path = os.environ.get("INTERLEAVE") or str(HERE / "twoway_interleave.py")
spec = importlib.util.spec_from_file_location("il_under_test", path)
il = importlib.util.module_from_spec(spec)
spec.loader.exec_module(il)
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


has = "exclude" in inspect.signature(il.idle_pool).parameters
check(has, "idle_pool takes a list of ruled-out pauses")
has_run = "idle_exclude" in inspect.signature(il.run).parameters
check(has_run, "and run() passes build.idle_exclude through to it")
if has:
    pauses = {"BM": [(24.9, 31.0), (109.4, 115.6), (158.9, 164.3)],
              "BB": [(38.4, 44.9)]}
    masters = {"BM": "bm.mp4", "BB": "bb.mp4"}
    ex = [{"speaker": "BM", "from_s": 25.16, "to_s": 30.36, "why": "blip at 28.7s"},
          {"speaker": "BM", "from_s": 159.06, "to_s": 163.9, "why": "blips"}]
    got = il.idle_pool(pauses, masters, pathlib.Path("."), False, ex)
    bm = [(c["in_s"], c["out_s"]) for c in got if c["speaker"] == "BM"]
    check(len(bm) == 1 and 109.4 < bm[0][0] < bm[0][1] < 115.6,
          "Steve keeps ONLY his clean pause; both ruled-out ones are not banked", bm)
    check(any(c["speaker"] == "BB" for c in got),
          "an exclusion for one man never touches the other's pauses")
    allin = il.idle_pool(pauses, masters, pathlib.Path("."), False, None)
    check(len([c for c in allin if c["speaker"] == "BM"]) == 3,
          "with no exclusions every pause is banked exactly as before")

print(f"\nidle exclude: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
