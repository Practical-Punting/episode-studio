"""author_cards.a17_attach: a card the planner DROPPED is authored untimed; a MISSING measurement still halts.

    python engine/test_a17_dropped_card.py

Found on EP57's first real run (14 Nov 2026): twoway_a17 records a planner-dropped card as
build.a17[id] = {"dropped": "..."} with no points, and a17_attach treated that as a missing
measurement and halted the WHOLE authoring run — no page could be timed for any card.
CONTROLS: no record at all, and a record whose points do not match, must still halt.
"""
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import author_cards as ac   # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


card = {"id": "C3", "_a17_points": [["q", "a chance of paying nothing"], ["a", "the one advantage"]]}
ep = {"build": {"a17": {"C3": {"dropped": "dropped by the planner (see build._layout_placement)"}}}}
out = ac.a17_attach(card, ep)
check("a planner-DROPPED card is returned untimed, named as dropped, and does not halt",
      "_a17_delays" not in out and out.get("_a17_dropped", "").startswith("dropped"))


def halts(ep_):
    try:
        ac.a17_attach(card, ep_)
        return False
    except ac.Halt:
        return True


check("CONTROL: no build.a17 record at all still HALTS", halts({"build": {"a17": {}}}))
check("CONTROL: a record whose points do not match still HALTS",
      halts({"build": {"a17": {"C3": {"points": [{"key": "q", "anchor": "something else", "delay_ms": 500}]}}}}))
good = {"build": {"a17": {"C3": {"points": [{"key": "q", "anchor": "a chance of paying nothing", "delay_ms": 400},
                                            {"key": "a", "anchor": "the one advantage", "delay_ms": 2400}]}}}}
check("a measured card still gets its delays", ac.a17_attach(card, good).get("_a17_delays") == [400, 2400])
print(f"\na17 dropped card: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
