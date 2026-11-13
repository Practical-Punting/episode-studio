"""twoway_a17.measure: a card taken off its beat as LATE is a reported drop, not "not in the assembled plan".

    python engine/test_a17_late_dropped.py

EP57 (14 Nov 2026): do_replan took C5/C6/C10 off their beats (build.a17_late_dropped) and the
cut render then HALTED — measure() only recognised a planner drop, so the three late cards
came back as {"problem": "not in the assembled plan"} and twoway_render refused the plan.
CONTROL: a card missing from the plan with NO record of either drop is still a problem.
"""
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import twoway_a17 as ta   # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def card(cid):
    return {"id": cid, "block": "a17", "_a17_points": [["q", "a chance"], ["a", "the advantage"]]}


cards = [card("C5"), card("C6")]
check("fixture: the cards are A17", all(ta.is_a17(c) for c in cards))
late = {"cards": cards, "beats": [],
        "build": {"a17_late_dropped": [{"card": "C5", "why": "late"}]}}
out = ta.measure([], [], [], late, 0.0)
check("a card in build.a17_late_dropped is reported as DROPPED (late)",
      "dropped" in out.get("C5", {}) and "late" in out["C5"]["dropped"], str(out.get("C5")))
check("CONTROL: a card missing with no drop record is still a PROBLEM",
      out.get("C6") == {"problem": "not in the assembled plan"}, str(out.get("C6")))
planner = {"cards": [card("C6")], "beats": [],
           "build": {"_layout_placement": ["DROPPED C6 (no room)"]}}
check("a planner drop is still reported as the planner's",
      "planner" in ta.measure([], [], [], planner, 0.0)["C6"].get("dropped", ""))
print(f"\na17 late dropped: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
