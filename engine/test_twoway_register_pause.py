"""A15: a change of register breathes longer than a handover. Two numbers, not one.

Jodie, 27 Sep 2026, on EP49 cut #4 at ~13:21 where the reading ran into Gordon's close:
"he stops talking and starts talking again in the same breath. It's too rushed" —
"another half second pause or something between those two."

The walk is driven with a hand-built conversation that has every kind of boundary:

    open -> T1 Gordon -> CTA -> T2 Steve -> T3 Gordon -> T4 Steve -> close -> outro

  · reading <-> Gordon-as-himself (open->T1, T1->CTA, CTA->T2, T4->close): REGISTER
  · reading -> reading between the two men (T2->T3, T3->T4): HANDOVER
  · furniture -> furniture (close->outro): HANDOVER-length — no register change

No renders: `_timeline_with_furniture` takes measured spans, so the spans are given.

FAIL-FIRST: INTERLEAVE=<pre-change twoway_interleave.py> -> red (every gap 0.3-0.5s).

Run: python engine/test_twoway_register_pause.py
"""
import importlib.util
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


turns = [{"n": 1, "speaker": "BB"}, {"n": 2, "speaker": "BM"}, {"n": 3, "speaker": "BB"},
         {"n": 4, "speaker": "BM"}]
manifest = {"segments": [
    {"n": 1, "kind": "furniture", "id": "open", "name": "open", "where": "before-dialogue"},
    {"n": 2, "kind": "turn", "turn": 1, "name": "T1"},
    {"n": 3, "kind": "furniture", "id": "early_cta", "name": "cta",
     "where": "after-host-turn-1"},
    {"n": 4, "kind": "turn", "turn": 3, "name": "T3"},
    {"n": 5, "kind": "furniture", "id": "close", "name": "close", "where": "after-dialogue"},
    {"n": 6, "kind": "furniture", "id": "outro", "name": "outro", "where": "after-dialogue"},
]}
spans = {"BB": [(0.5, 10.0), (16.0, 30.0), (36.0, 40.0), (46.0, 60.0), (66.0, 70.0),
                (76.0, 80.0)],
         "BM": [(0.5, 20.0), (26.0, 40.0)]}
masters = {"BB": "bb.mp4", "BM": "bm.mp4"}
tl = il._timeline_with_furniture(turns, spans, masters, manifest, "BB")
rows = [r for r in tl if r.get("kind") != "latency"]
gaps = [r for r in tl if r.get("kind") == "latency"]
names = [r.get("furniture") or f"T{r['turn']}" for r in rows]
print("  order:", " -> ".join(names))
print("  gaps: ", [g["dur_s"] for g in gaps])
check(names == ["open", "T1", "early_cta", "T2", "T3", "T4", "close", "outro"],
      "the walk puts the furniture where the manifest says")


def kind(a, b):
    return "register" if (a.get("kind") == "furniture") != (b.get("kind") == "furniture") \
        else "handover"


want = [kind(a, b) for a, b in zip(rows, rows[1:])]
reg = [g["dur_s"] for g, k in zip(gaps, want) if k == "register"]
hand = [g["dur_s"] for g, k in zip(gaps, want) if k == "handover"]
check(len(reg) == 4 and len(hand) == 3,
      "4 register boundaries (open->T1, T1->CTA, CTA->T2, T4->close) and 3 handovers",
      f"{len(reg)} / {len(hand)}")
check(all(0.30 <= h <= 0.50 for h in hand), "handovers stay 0.3-0.5s (spec §5)", hand)
check(all(0.80 <= r <= 1.00 for r in reg),
      "every register change is 0.8-1.0s — a handover plus half a second", reg)
check(min(reg, default=0) > max(hand, default=1),
      "the shortest register pause is longer than the longest handover — two numbers",
      f"{min(reg, default=0)} vs {max(hand, default=1)}")
check(len(set(reg)) > 1, "register pauses are varied too — identical gaps are the tell", reg)
labels = [g.get("pause") for g in gaps]
check(labels == want, "each gap is LABELLED with what it is, so a check can find it",
      labels)
check(all(abs(a["to_s"] - b["from_s"]) < 1e-6 for a, b in zip(tl, tl[1:])),
      "the timeline is contiguous: no gap and no overlap")
total = sum(r["dur_s"] for r in tl)
check(abs(tl[-1]["to_s"] - total) < 0.01, "and its length is the parts plus the gaps",
      f"{tl[-1]['to_s']} vs {total:.3f}")

print(f"\nregister pause: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
