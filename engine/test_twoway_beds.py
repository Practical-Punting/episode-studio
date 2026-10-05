"""The listening beds: reused, never looped, never the same stretch back to back.

Jodie's ruling, 5 Oct 2026: NO new beds and NO longer breaks for EP55 — the beds are
REUSED, never looped in a run, and never the same stretch back to back.

The old picker started every bed at 0:00 and, when nothing was free, took "the longest
bed" with no check at all — so Gordon, with ONE 64s bed, showed the identical opening
seconds every time he listened. Nothing asserted the rule anywhere.

What this pins (no renders — `plan_listeners` takes a duration function):
  1. Gordon's real situation (one 63.98s bed, many listening shots) plans with no
     stretch back to back and no shot longer than its source;
  2. the bed is WALKED — reuse moves on through the footage;
  3. his own clean pauses are used first;
  4. a shot longer than any source HALTS (never a loop, never a freeze);
  5. a shot whose only footage is the stretch just shown HALTS;
  6. `back_to_back` — the check twoway_qc runs on the finished film's ledger — FAILS
     the old picker's behaviour, replayed, and passes the new plan.

FAIL-FIRST: RENDER=<pre-change twoway_render.py> -> red (no planner, no check).

Run: python engine/test_twoway_beds.py
"""
import importlib.util
import os
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
path = os.environ.get("RENDER") or str(HERE / "twoway_render.py")
spec = importlib.util.spec_from_file_location("tr_under_test", path)
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


plan_listeners = getattr(tr, "plan_listeners", None)
back_to_back = getattr(tr, "back_to_back", None)
check(plan_listeners is not None, "the listening footage is PLANNED up front")
check(back_to_back is not None, "and there is a back-to-back check to run on a ledger")
if not (plan_listeners and back_to_back):
    print(f"\nbeds: {len(fails)} failed")
    sys.exit(1)

SIDE = {"BB": "left", "BM": "right"}
BEDS = {"BB": [("BB-R1a", "BB-R1a.mp4")],
        "BM": [("BM-R1a", "BM-R1a.mp4"), ("BM-R1b", "BM-R1b.mp4")]}
DURS = {"BB-R1a.mp4": 63.98, "BM-R1a.mp4": 68.98, "BM-R1b.mp4": 68.98, "short.mp4": 30.0}


def dur_of(p):
    return DURS[str(p)]


def segs_for(listener, lengths, gap=20.0, start=10.0):
    out, t = [], start
    for i, L in enumerate(lengths, 1):
        sp = "BM" if listener == "BB" else "BB"
        out.append({"n": i, "from_s": t, "to_s": t + L, "dur_s": L, "layout": "two-box",
                    "speaker": sp, "listener": listener})
        t += L + gap
    return out


# 1-2: Gordon, one bed, many shots (EP55's longest Gordon run is 38.5s)
g = segs_for("BB", [30.0, 20.0, 38.5, 25.0, 30.0, 15.0, 38.5])
picks = plan_listeners(g, [], BEDS, SIDE, dur_of)
led = [picks[s["n"]] for s in g]
check(len(led) == 7, "every Gordon listening shot has footage", len(led))
check(back_to_back(led) == [], "no stretch back to back and nothing looped",
      back_to_back(led)[:1])
check(all(e["out_s"] <= e["src_dur_s"] + 0.01 for e in led),
      "no shot runs past the end of its bed",
      [(e["in_s"], e["out_s"]) for e in led])
check(len({e["in_s"] for e in led}) > 1, "the bed is WALKED, not replayed from 0:00",
      [e["in_s"] for e in led])

# 3: his own clean pauses come first
idle = [{"speaker": "BB", "file": "renders/idle/BB-01.mp4", "source": "BB-master.mp4",
         "in_s": 100.15, "out_s": 105.85, "dur_s": 5.7}]
p3 = plan_listeners(segs_for("BB", [4.0]), idle, BEDS, SIDE, dur_of)
check(p3[1]["kind"] == "idle" and p3[1]["source"] == "BB-master.mp4",
      "a short listen uses his own clean pause before any bed", p3[1]["kind"])

# 4: longer than any source -> HALT
try:
    plan_listeners(segs_for("BB", [70.0]), [], BEDS, SIDE, dur_of)
    check(False, "a 70s listen with a 64s bed HALTS (never a loop, never a freeze)")
except tr.Unrenderable as e:
    check("HALTS" in str(e) or "halts" in str(e).lower(),
          "a 70s listen with a 64s bed HALTS (never a loop, never a freeze)")

# 5: only the stretch just shown -> HALT
try:
    plan_listeners(segs_for("BB", [29.0, 29.0], gap=200.0), [],
                   {"BB": [("short", "short.mp4")]}, SIDE, dur_of)
    check(False, "two 29s listens off one 30s bed HALT — the second could only repeat it")
except tr.Unrenderable:
    check(True, "two 29s listens off one 30s bed HALT — the second could only repeat it")

# 6: the check fails the OLD picker's behaviour, replayed (every bed from 0:00)
old = [dict(e, in_s=0.0, out_s=round(e["out_s"] - e["in_s"], 3)) for e in led]
check(len(back_to_back(old)) >= 1,
      "the checker FAILS the old behaviour — every listen from the bed's 0:00",
      f"{len(back_to_back(old))} fault(s)")
loop = [dict(led[0], out_s=led[0]["src_dur_s"] + 5.0)]
check(any("runs out" in f for f in back_to_back(loop)),
      "and FAILS a shot longer than its source")

# both men interleaved: Steve's two beds
both = segs_for("BM", [28.8, 20.0, 28.8, 25.0])
pb = plan_listeners(both, [], BEDS, SIDE, dur_of)
check(back_to_back(list(pb.values())) == [], "Steve's listening plans clean on his beds")

print(f"\nbeds: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
