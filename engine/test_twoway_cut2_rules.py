"""Two rules landed for EP56 cut 2 (12 Nov 2026), each with a control that must FAIL.

  (a) broll_floor_s: a LIBRARY re-use (`library_from`) may play at its own length (Jodie: "The clips from
      the library can be 5s."); a generated clip keeps the 8s floor.
  (b) REAL EP56: the plan check passes the 5.04s EP37 clip WITH the floors; CONTROL: without them it is
      reported "outside the rule".
  (c) an A17 card whose only legal entries come AFTER its first point's sentence is DROPPED, with an A17
      reason, never placed late (EP56's C7: entered 40.5s, its point said at ~37s).
  (d) CONTROL: the same card whose first point is in a sentence it CAN enter on is placed there, not dropped.

Run: python engine/test_twoway_cut2_rules.py
"""
import copy
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_beats as tb  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


print("\n-- (a) THE PER-CLIP FLOOR --")
lib = {"target": "x", "dur_s": 5.04, "library_from": "PP-EP37"}
gen = {"target": "y", "dur_s": 5.04}
check(abs(tb.broll_floor_s(lib) - 5.04) < 1e-9, "a library re-use's floor is its own length", tb.broll_floor_s(lib))
check(tb.broll_floor_s(gen) == tb.BROLL_DUR_MIN_S, "CONTROL: a generated clip keeps the 8s floor",
      tb.broll_floor_s(gen))
check(tb.broll_floor_s({"target": "z", "dur_s": 9.5, "library_from": "PP-EP37"}) == tb.BROLL_DUR_MIN_S,
      "a long library clip's floor is still 8s, never above it")

print("\n-- (b) REAL EP56: THE 5.04s EP37 CLIP --")
EPJ = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP56-Class-Improvement-and-Bias-Blues-Part-3\docs\episode.json")
if EPJ.is_file():
    epj = json.loads(EPJ.read_text(encoding="utf-8"))
    rain = "broll-rain-falling-on-an-empty-turf-track"
    if any(b["target"] == rain for b in epj.get("broll", [])):
        with_f = [v for v in tb.violations(epj["layout_plan"], tb.broll_floors(epj)) if rain in v]
        without = [v for v in tb.violations(epj["layout_plan"]) if rain in v]
        check(not with_f, "with the floors: not reported", with_f)
        check(bool(without), "CONTROL: without them it IS reported", without[:1])
    else:
        print("  (EP56 does not carry the EP37 clip — skipped)")
else:
    print("  (EP56 not on disk — skipped)")


def words(n, tag):
    # Capitalised: `sentences()` only splits where a full stop is followed by a capital.
    return " ".join([tag.capitalize()] + ["word"] * (n - 2) + ["end."])


def beat(n, turn, spk, sents, card=None, broll=None):
    line = " ".join(sents)
    return {"n": n, "turn": turn, "speaker": spk, "line": line, "est_s": round(len(line.split()) / 2.6, 2),
            "card": card, "broll": broll, "para_in_turn": 1, "paras_in_turn": 1}


# turn 2: a 9s clip on beat 2 holds the screen, and its 5s dwell after it, past beat 3's first sentences
# (the planner settles it at 10s -> screen to 19s, dwell to 24s). Beat 3's sentences start every 5s from
# 10s to 45s, so a card can legally enter from 25s on, with room for its 8s hold.
BEATS = [beat(1, 1, "BM", [words(10, "open")]),
         beat(2, 2, "BB", [words(13, "alpha"), words(13, "bravo")], broll="clip-y"),
         beat(3, 2, "BB", [words(13, w) for w in ("charlie", "delta", "echo", "foxtrot", "golf", "hotel",
                                                  "india", "juliet")], card="C2")]


def place(anchor):
    return tb.plan_with_dwell(copy.deepcopy(BEATS), {"clip-y": 9.0}, {"C2": 8.0},
                              a17_first={"C2": anchor.capitalize()})


check(len([u for u in tb._units(BEATS) if u["beat"] == 3]) == 8, "fixture: beat 3 is eight sentences")


print("\n-- (c) AN A17 CARD THAT COULD ONLY ENTER LATE IS DROPPED --")
segs, log = place("charlie")
check(not any(s.get("card") == "C2" for s in segs), "C2 is not on screen", [s.get("card") for s in segs])
check(any(l.startswith("DROPPED C2") and "A17" in l for l in log), "and the log says why, naming A17",
      next((l[:120] for l in log if "C2" in l), log[:1]))

print("\n-- (d) CONTROL: THE SAME CARD WITH ITS POINT IN A SENTENCE IT CAN ENTER ON --")
segs, log = place("foxtrot")
c2 = [s for s in segs if s.get("card") == "C2"]
check(bool(c2), "C2 is placed", log[:2])
check(not any(l.startswith("DROPPED C2") for l in log), "and not dropped")

print(f"\ncut-2 rules: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
