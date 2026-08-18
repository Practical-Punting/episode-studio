#!/usr/bin/env python3
"""E29 — A RUNNING ENGINE MUST NOT EAT THE SUITE'S OWN TICKETS.

    python engine/test_suite_tickets_are_not_food.py

`test_dead_zone.py` creates a real rail row at a working status with a dead lease —
precisely the shape `reclaim_stale()` hunts for — and on 16 Aug 2026 a running engine
took it mid-test:

    [03:45:32] reclaimed a stale-leased episode PP-EP9019 at building
    [03:45:52] !! lost ownership of the episode (lease reclaimed) — stopping work

The suite reported `dead zone: 2 passed, 1 failed`; the same test passes on its own.
**A gate that is green or red depending on what else is running is not a gate.** The
workaround was `stop_engine.py` before a full suite and `--release` after, which works
and relies on whoever runs the suite remembering.

⚠️ THE FLOOR IS A NUMBER, NOT A PREFIX, AND THAT IS THE WHOLE CARE IN THIS FILE.
The backlog entry proposed "a 9xxx test range". The fixtures already use PP-EP96, 97,
98 and 99 — and **the plan is 300 episodes**, so those four are real episodes nobody
has made yet. A prefix rule would have quietly stopped the engine claiming them.

Nothing here touches the live rail, the network, or a running engine — it reads the
filters the module actually builds.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rail                                                            # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


SRC = (HERE / "rail.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)

# The two episodes-in-real-life numbers this must never collide with: the highest
# episode built so far, and where Hugh and Jodie are going.
BUILT_SO_FAR = 30
THE_PLAN = 300


def _source_of(name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(SRC, node) or ""
    raise AssertionError(f"{name} is not in rail.py")


def _the_floor_clears_the_whole_plan():
    assert rail.TEST_EP_FLOOR > THE_PLAN, (
        f"the test-ticket floor is {rail.TEST_EP_FLOOR}, and the plan is {THE_PLAN} "
        f"episodes. A floor inside the real range stops the engine claiming real work.")
    assert rail.TEST_EP_FLOOR > BUILT_SO_FAR


case(f"the floor clears all {THE_PLAN} planned episodes, not just the {BUILT_SO_FAR} "
     f"built", _the_floor_clears_the_whole_plan)


def _the_fixtures_ids_are_not_swept_up():
    """CONTROL — the numbers the fixtures ACTUALLY use, judged by the real rule.

    PP-EP96..99 are in the fixtures today AND are real episodes later. They must be
    claimable: it is the ep_number that decides, not the shape of the id.
    """
    def excluded(n):
        return n is not None and n >= rail.TEST_EP_FLOOR

    for n in (96, 97, 98, 99, 1, 30, 300):
        assert not excluded(n), (
            f"episode {n} would be filtered out as a test ticket — it is a real "
            f"episode, or will be.")
    for n in (9001, 9019, 9999):
        assert excluded(n), f"synthetic ticket {n} is still claimable by a live engine"
    assert not excluded(None), (
        "a ticket with no ep_number yet is being treated as a test ticket — a real "
        "episode that has not been numbered must still be claimable.")


case("CONTROL — 96..99 and 300 stay claimable, 9001/9019 do not, NULL is claimable",
     _the_fixtures_ids_are_not_swept_up)


def _null_is_claimable_in_the_filter_itself():
    """The SQL half of the case above. `ep_number=lt.9000` alone drops NULL rows,
    because a NULL comparison is not true — so the filter has to say so out loud."""
    assert "ep_number.is.null" in rail.NOT_A_TEST, (
        f"the filter is {rail.NOT_A_TEST!r} — a ticket with no number yet would be "
        f"silently unclaimable, which is a real episode stuck on the board forever.")
    assert f"ep_number.lt.{rail.TEST_EP_FLOOR}" in rail.NOT_A_TEST


case("the filter keeps un-numbered tickets claimable", _null_is_claimable_in_the_filter_itself)


def _both_doors_are_covered():
    """🔴 THE ONE THAT ATE PP-EP9019 WAS `reclaim_stale`. Both are checked, because
    covering one door is how the first version of a guard like this passes review and
    fails in production."""
    for fn in ("list_queued", "reclaim_stale"):
        body = _source_of(fn)
        assert "NOT_A_TEST" in body, (
            f"{fn}() does not exclude test tickets. `reclaim_stale` is the one caught "
            f"in the act; `list_queued` is what feeds claim_next.")


case("both claim_next's source and reclaim_stale exclude test tickets",
     _both_doors_are_covered)


print(f"\nsuite tickets are not food: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
