#!/usr/bin/env python3
"""THE YARD: the second door into the engine, and the gate that guards it.

    python engine/test_yard_pickup.py

Until 19 Aug 2026 an episode entered the engine through exactly ONE door — `claim_next`
— and that door has carried the Script Gate since Jodie set it on 26 Jul: an episode is
claimable only once a human has approved the words (`title_approved`) AND ticked "I've
read the script" (`script_read`).

The Yard opens a SECOND door. The engine now RELEASES at `awaiting_render` and
`awaiting_cover` instead of sitting on the claim, so those episodes come back in through
`reclaim_stale` once the board advances their status. **A gate that guards one of two
doors is not a gate.** This file is the proof that the second door carries it too.

🔴 THE CONTROL RUNS FIRST AND IT MUST GO RED. Jodie's instruction, in her words: *"prove
the new pick-up path CANNOT take an episode whose Script Gate has not passed. Watch it
FAIL before you believe a pass."* So case 1 asks the OLD filter set — reclaim_stale as
it was written, without the gate — about an unapproved episode, and asserts that it IS
taken. That is the bug, reproduced deliberately. Only once the control has shown the
test can SEE the bug does a green on the real filters mean anything. A control that was
green from the start would have proved nothing at all, and this whole file would have
been a tick past the thing it was meant to check.

⚠️ IT NEVER CALLS reclaim_stale(), for `test_dead_zone.py`'s reason: that function
patches the FIRST eligible row it finds, with no way to say which, so pointing it at the
live rail could hand a real mid-build episode to a test. It asks PostgREST the exact
question reclaim_stale asks, SCOPED BY ID to its own throwaway ticket.

⚖️ **E46 GRANTED (Jodie, 19 Aug 2026).** This file may call `rail.delete()` on ONLY the
id its own INSERT returned — the same terms as `test_dead_zone.py`. Her reasoning: the
danger the 10 Aug ruling names is *a delete driven by a FILTER*; an id this process
created a second earlier is a different animal. And refusing would have left the Script
Gate's second door guarded permanently by a test that only READS SOURCE TEXT.
`test_production_never_deletes.py` now enforces that as a SHAPE rather than a filename.

⚠️ AND THE HAND-COPIED FILTER IS ITSELF A RISK — the test could keep passing after
somebody deleted the filter from rail.py, because the test holds its own copy. The last
case reads rail.py's source and asserts the fragments are really there, so drift between
this file and the code shows up as a failure rather than as a false green.

It creates one ticket and deletes it, and touches no episode folder.
"""
from __future__ import annotations

import datetime as dt
import inspect
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import rail                                                           # noqa: E402

PASS, FAIL = [], []
OWNER = "pp-engine@test-yard-owner"          # whoever parked it
ME = "pp-engine@test-yard-picker"            # the engine coming back for it


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def dead():
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)).isoformat()


def _ask(tid, worker, with_gate):
    """reclaim_stale's filters, asked as a read about ONE ticket.

    `with_gate=False` is the code as it stood before the Yard — the control.
    `with_gate=True` is what rail.reclaim_stale now sends.
    """
    stat = ",".join(sorted(rail.WORKING))
    gate = "&title_approved=is.true&script_read=is.true" if with_gate else ""
    rows = rail._request(
        "GET",
        f"?id=eq.{rail._q(tid)}&status=in.({stat})&claimed_by=not.is.null"
        f"&claimed_by=neq.{rail._q(worker)}{gate}"
        f"&lease_until=lt.{rail._ts(rail._now())}")
    return rows[0] if rows else None


def park(status, title_approved, script_read):
    """Put the ticket where a released, gate-parked episode sits."""
    rail.set_fields(tid, {"status": status,
                          "claimed_by": f"{OWNER} (parked at {status})",
                          "lease_until": dead(),
                          "title_approved": title_approved,
                          "script_read": script_read})


tid = rail.insert({
    "ep_number": 9021,
    "status": "rendering",
    "hook": "YARD PICK-UP TEST — delete me",
    "claimed_by": OWNER,
    "lease_until": dead(),
    "title_approved": True,
    "script_read": True,
})["id"]
print(f"  (test ticket {tid} — ep 9021)\n")

try:
    # ── 1. THE CONTROL. It must go RED, or nothing below means anything. ────────
    def _control_the_old_door_took_it():
        """THE BUG, REPRODUCED ON PURPOSE.

        An episode whose script NO HUMAN HAS READ, parked at a status the board
        advanced into WORKING. The pre-Yard filters take it without a murmur. If this
        assertion ever fails, the test has stopped being able to see the thing it
        exists to catch — treat a green below as meaningless until this is red again.
        """
        park("rendering", title_approved=False, script_read=False)
        got = _ask(tid, ME, with_gate=False)
        assert got is not None, (
            "THE CONTROL DID NOT REPRODUCE THE BUG. The pre-Yard filters refused an "
            "unapproved episode, which they never did — so this test cannot prove the "
            "gate holds, and every pass below is a false green.")

    case("CONTROL — without the gate, the pick-up path takes an UNAPPROVED episode",
         _control_the_old_door_took_it)

    # ── 2. …and the same ticket, same instant, against the real filters. ────────
    def _neither_flag():
        park("rendering", title_approved=False, script_read=False)
        assert _ask(tid, ME, with_gate=True) is None, \
            "the pick-up path took an episode with NEITHER half of the Script Gate"

    def _words_only():
        """Words approved, script NOT read — the half that is easiest to lose."""
        park("rendering", title_approved=True, script_read=False)
        assert _ask(tid, ME, with_gate=True) is None, \
            "the pick-up path took an episode whose script nobody has read"

    def _script_only():
        park("rendering", title_approved=False, script_read=True)
        assert _ask(tid, ME, with_gate=True) is None, \
            "the pick-up path took an episode whose words nobody has approved"

    case("both halves missing -> NOT picked up", _neither_flag)
    case("script_read missing -> NOT picked up", _words_only)
    case("title_approved missing -> NOT picked up", _script_only)

    # ── 3. The pass. Without this the filter could simply block everything. ─────
    def _both_flags():
        park("rendering", title_approved=True, script_read=True)
        assert _ask(tid, ME, with_gate=True) is not None, (
            "a fully approved episode was NOT picked up — the gate is not guarding, "
            "it is jammed shut, and the Yard would strand every episode it parks")

    case("both halves ticked -> picked up", _both_flags)

    # ── 4. A withdrawn approval stops the pick-up mid-flight. ───────────────────
    def _untick_strands_it():
        """The reason the filter is not redundant.

        Everything reclaimed here was claimable once, so the flags were true at some
        point. But they are a HUMAN'S flags and a human can untick them — on the
        board, after a script turns out to be wrong. The episode must then stop being
        picked up rather than carry on with an approval that has been withdrawn.
        """
        park("rendering", title_approved=True, script_read=True)
        assert _ask(tid, ME, with_gate=True) is not None, "should start reclaimable"
        rail.set_fields(tid, {"script_read": False})
        assert _ask(tid, ME, with_gate=True) is None, \
            "unticking 'I've read the script' did not stop the engine picking it back up"

    case("approval withdrawn mid-flight -> stops being picked up", _untick_strands_it)

    # ── 5. The gate statuses are INVISIBLE until a human acts. ──────────────────
    def _parked_at_a_gate_is_not_touched():
        """THE GATE ITSELF IS UNCHANGED, AND THIS IS WHERE THAT IS PROVED.

        A released episode waits at `awaiting_render` / `awaiting_cover`. Neither is
        in WORKING, so nothing can pick it up — not this path, not `resume_own`, not
        `claim_next`. It moves when Jodie clicks and not one moment before. That is
        the whole claim "what BLOCKS changed, what a human DECIDES did not".
        """
        for gate in ("awaiting_render", "awaiting_cover"):
            park(gate, title_approved=True, script_read=True)
            assert _ask(tid, ME, with_gate=True) is None, (
                f"an episode parked at {gate} was picked up with NO HUMAN ACTION — "
                f"the engine would sail straight through Jodie's gate")
            assert gate not in rail.WORKING, f"{gate} must never be a working status"

    case("parked at a gate -> nothing picks it up until a human acts",
         _parked_at_a_gate_is_not_touched)

    # ── 6. …and the moment she does, the board's own write makes it visible. ────
    def _the_board_hands_it_back():
        """app.js advances awaiting_render->rendering and awaiting_cover->assembling.
        Those are the writes that end the wait, so they are what this simulates."""
        for gate, after in (("awaiting_render", "rendering"),
                            ("awaiting_cover", "assembling")):
            park(gate, title_approved=True, script_read=True)
            assert _ask(tid, ME, with_gate=True) is None, "should be invisible at the gate"
            rail.set_fields(tid, {"status": after})          # <- the human's click
            assert _ask(tid, ME, with_gate=True) is not None, (
                f"after the board advanced {gate} -> {after} the engine still could "
                f"not see the episode — it would sit at a gate Jodie had already opened")

    case("human acts -> the board advances the status -> the engine picks it up",
         _the_board_hands_it_back)

    # ── 7. The dead zone is not re-opened by any of this. ───────────────────────
    def _hand_back_not_release():
        """`release` nulls the owner; at a WORKING status that is E11's dead zone.
        The Yard parks episodes for hours, so it MUST hand back, never release."""
        src = (HERE / "engine.py").read_text(encoding="utf-8")
        i = src.index("THE YARD (2) — RELEASE AT THE NON-APPROVAL GATES")
        body = src[i:src.index("break", i)]
        assert "rail.hand_back(" in body, \
            "the gate release does not call hand_back()"
        assert "rail.release(" not in body, (
            "the gate release calls rail.release(), which nulls the owner and drops "
            "the episode into the dead zone the moment the board advances its status")

    case("the gate release hands back (named owner), never releases (NULL owner)",
         _hand_back_not_release)

    # ── 8. The work-in-progress count. ─────────────────────────────────────────
    def _in_flight_identity():
        """Fed rows directly — this is the identity match, not the query.

        The bug being guarded is specific: a PostgREST `like.worker*` would count
        `pp-engine@box2`'s episode against `pp-engine@box`'s cap, silently.
        """
        rows = [
            {"ep_number": 1, "status": "building", "claimed_by": "pp-engine@box"},
            {"ep_number": 2, "status": "rendering",
             "claimed_by": "pp-engine@box (parked at awaiting_render)"},
            {"ep_number": 3, "status": "building", "claimed_by": "pp-engine@box2"},
            {"ep_number": 4, "status": "building", "claimed_by": None},
        ]
        real = rail._request
        rail._request = lambda *a, **k: rows
        try:
            got = {r["ep_number"] for r in rail.in_flight("pp-engine@box")}
        finally:
            rail._request = real
        assert got == {1, 2}, (
            f"in_flight matched {sorted(got)}; it must count the worker's own bare "
            f"name and its handed-back form, and NOTHING else (ep 3 is a different "
            f"worker whose name merely starts the same way)")

    def _in_flight_statuses():
        assert "awaiting_render" in rail.IN_FLIGHT and "awaiting_cover" in rail.IN_FLIGHT, \
            "the two non-approval gates must count against the cap — the engine WILL " \
            "come back to them, so they are work in progress"
        assert "awaiting_approval" not in rail.IN_FLIGHT, (
            "awaiting_approval must NOT count against the cap: the engine has no "
            "further work for it, and counting it would jam the yard shut behind "
            "episodes waiting on the four approvals and the publish")
        assert rail.WORKING <= set(rail.IN_FLIGHT), "every working status is in flight"

    case("in_flight counts this worker's episodes and not a lookalike's",
         _in_flight_identity)
    case("in_flight counts the two non-approval gates, never awaiting_approval",
         _in_flight_statuses)

    # ── 9. Drift guard: the filters really are in rail.py. ─────────────────────
    def _no_drift():
        src = inspect.getsource(rail.reclaim_stale)
        assert "title_approved=is.true" in src and "script_read=is.true" in src, (
            "rail.reclaim_stale no longer sends the Script Gate filter. Every case "
            "above asks a hand-written copy of it, so they would all still pass — "
            "this is the case that stops that being a false green.")

    def _acquire_order():
        """Finish what is started before starting more.

        Read as TEXT, not imported — `test_dead_zone.py`'s rule. Importing engine.py
        runs its module-level code against the live rail, which a test has no business
        doing to find out what order two calls appear in.
        """
        whole = (HERE / "engine.py").read_text(encoding="utf-8")
        i = whole.index("def acquire():")
        src = whole[i:whole.index("\ndef ", i + 1)]
        assert src.index("reclaim_stale") < src.index("claim_next"), (
            "acquire() tries claim_next before reclaim_stale, so a brand-new build "
            "would be started in front of an episode whose gate Jodie has already "
            "opened — the yard fills faster than it drains")
        assert "YARD_MAX" in src, "acquire() no longer respects the work-in-progress cap"

    case("rail.reclaim_stale really sends the gate filter (drift guard)", _no_drift)
    case("acquire() reclaims before it claims, and honours YARD_MAX", _acquire_order)


    # ── STRUCTURAL GUARDS. These need no rail; they catch a change to the WIRING
    # that the live cases above would sail straight past because they carry their
    # own copy of the filter. ────────────────────────────────────────────────────
    ENGINE_SRC = (HERE / "engine.py").read_text(encoding="utf-8")

    def _the_other_filters_survived():
        """The gate must be ADDED to reclaim_stale's filters, never swapped in."""
        src = inspect.getsource(rail.reclaim_stale)
        for frag, why in [
                ("claimed_by=not.is.null", "it would sweep up dead-zone rows"),
                ("claimed_by=neq.", "it would fight the live worker for its episode"),
                ("lease_until=lt.", "it would steal episodes whose lease is alive"),
                ("NOT_A_TEST", "it would eat the suite's own tickets (E29)"),
                ("status=in.", "it would reclaim at a status it cannot work")]:
            assert frag in src, f"reclaim_stale lost `{frag}` — {why}"

    def _hand_back_still_expires_the_lease():
        """hand_back is only a pick-up path because the lease is already dead."""
        src = inspect.getsource(rail.hand_back)
        assert "timedelta(seconds=1)" in src and "lease_until" in src,             "hand_back no longer expires the lease, so a parked episode waits it out"

    def _cap_exists_and_is_two():
        i = ENGINE_SRC.index("YARD_MAX = ")
        val = int(ENGINE_SRC[i:].split("=", 1)[1].splitlines()[0].strip())
        assert val == 2, (
            f"YARD_MAX is {val}. Jodie ruled the order — two, then three, then five — "
            f"so 2 stands until somebody MEASURES what 3 returns per hour.")

    def _cap_does_not_block_the_pickup():
        i = ENGINE_SRC.index("def acquire():")
        src = ENGINE_SRC[i:ENGINE_SRC.index(chr(10) + "def ", i + 1)]
        assert src.index("reclaim_stale") < src.index("YARD_MAX"), (
            "the cap is checked before reclaim_stale — a worker at its cap could not "
            "pick up its OWN parked episodes, or rescue a crashed one, and would jam")

    def _every_gate_still_stands():
        """The release moves the CLAIM and nothing a human decides."""
        i = ENGINE_SRC.index("THE YARD (2) — RELEASE AT THE NON-APPROVAL GATES")
        body = ENGINE_SRC[i:ENGINE_SRC.index("break", i)]
        for forbidden in ("title_approved", "script_read", "needs_look", "cover_choice"):
            assert forbidden not in body,                 f"the gate release touches `{forbidden}` — it must move only the claim"

    case("reclaim_stale's original filters all survived", _the_other_filters_survived)
    case("hand_back still expires the lease", _hand_back_still_expires_the_lease)
    case("YARD_MAX is 2 (Jodie: two, then three, then five)", _cap_exists_and_is_two)
    case("the cap cannot block the pick-up path", _cap_does_not_block_the_pickup)
    case("the release moves the claim and nothing a human decides",
         _every_gate_still_stands)

finally:
    rail.delete(tid)
    left = [r for r in rail.list_all() if r.get("ep_number") == 9021]
    print(f"\n  (test ticket deleted; {len(left)} left behind)")

print(f"\nyard pick-up: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
