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
doors is not a gate.** This file is the standing proof that the second door carries it.

═══ ⚠️ WHAT THIS FILE CAN AND CANNOT PROVE, AND WHY. READ BEFORE TRUSTING A GREEN. ═══

**These cases are STRUCTURAL.** They read the source and the constants: that the filter
is really in `reclaim_stale`, that the release hands back rather than releases, that
`acquire()` reclaims before it claims, that the cap counts the right statuses and cannot
be fooled by a lookalike worker's name. **They do NOT ask PostgREST anything.**

🔴 **THE BEHAVIOURAL CONTROL WAS RUN, LIVE, RED-FIRST — AND IT IS NOT IN THIS FILE.**
On 19 Aug 2026 the full version ran against the real rail on a throwaway PP-EP9021
ticket: 13/13, and **the control went red first exactly as Jodie required** — asked with
the PRE-YARD filters, an episode with neither approval WAS taken; asked with the shipped
filters, the same ticket at the same instant was refused. It also proved a withdrawn
approval stops the pick-up mid-flight, that a gate-parked episode is invisible until a
human acts, and that the board's own `awaiting_render -> rendering` write is what makes
it visible again.

**It cannot live here, because cleaning up its ticket needs `rail.delete()`, and Jodie's
ruling of 10 Aug 2026 grants that to `test_dead_zone.py` and to nothing else** — *"For
test_dead_zone.py only ... and nothing else, ever."* `test_production_never_deletes.py`
enforces it by AST over the whole repo, so merely WRITING the call here fails the guard
even if it never runs. **Widening that set is Jodie's call, not mine, so it has not been
touched.** The alternative — leaving a permanent PP-EP9021 row behind — was rejected too:
the board does not filter test tickets, so it would appear on her board for ever.

⚠️ **SO THE STANDING COVER HERE IS WEAKER THAN THE PROOF THAT WAS RUN, AND SAYING SO IS
THE POINT.** If the exception is granted, restore the live cases; until then a green here
means *the wiring is still correct*, not *the database was asked again*.
"""
from __future__ import annotations

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
ENGINE_SRC = (HERE / "engine.py").read_text(encoding="utf-8")


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


# ── 1. THE GATE IS ON THE SECOND DOOR. ─────────────────────────────────────────
def _gate_on_the_pickup_path():
    """Both halves, in the PostgREST filter `reclaim_stale` actually sends.

    Not redundant with `claim_next`: everything reclaimed was claimable once, but the
    flags are a HUMAN'S and a human can untick them — on the board, mid-build, after a
    script turns out to be wrong. Without this the engine would carry straight on with
    an approval that had been WITHDRAWN.
    """
    src = inspect.getsource(rail.reclaim_stale)
    assert "title_approved=is.true" in src, \
        "reclaim_stale does not require title_approved — the second door is unguarded"
    assert "script_read=is.true" in src, \
        "reclaim_stale does not require script_read — the second door is unguarded"


def _the_other_filters_survived():
    """The gate must be ADDED to reclaim_stale's filters, never swapped in for them."""
    src = inspect.getsource(rail.reclaim_stale)
    for frag, why in [
            ("claimed_by=not.is.null", "it would sweep up dead-zone rows"),
            ("claimed_by=neq.", "it would fight the live worker for its own episode"),
            ("lease_until=lt.", "it would steal episodes whose lease is still alive"),
            ("NOT_A_TEST", "it would eat the suite's own tickets (E29)"),
            ("status=in.", "it would reclaim at a status the engine cannot work")]:
        assert frag in src, f"reclaim_stale lost `{frag}` — {why}"


case("the pick-up path requires BOTH halves of the Script Gate", _gate_on_the_pickup_path)
case("...and its original filters are all still there", _the_other_filters_survived)


# ── 2. THE GATE STATUSES ARE INVISIBLE UNTIL A HUMAN ACTS. ─────────────────────
def _gates_are_not_working_statuses():
    """THE CLAIM "WHAT BLOCKS CHANGED, WHAT A HUMAN DECIDES DID NOT" RESTS ON THIS.

    A released episode waits at `awaiting_render`/`awaiting_cover`. Neither is in
    WORKING, so `reclaim_stale` and `resume_own` cannot see it and `claim_next` wants
    `queued`. **Nothing can pick it up.** It moves when Jodie clicks and not before —
    the board advances awaiting_render->rendering and awaiting_cover->assembling, and
    only that write puts it back in reach.
    """
    for gate in ("awaiting_render", "awaiting_cover", "awaiting_approval"):
        assert gate not in rail.WORKING, (
            f"{gate} became a working status — the engine would pick an episode up "
            f"while it was still parked at a human gate")
    for after in ("rendering", "assembling"):
        assert after in rail.WORKING, \
            f"{after} is not a working status, so the human's click would strand it"


case("the human gates are not working statuses; the statuses they open into are",
     _gates_are_not_working_statuses)


# ── 3. THE DEAD ZONE IS NOT RE-OPENED. ────────────────────────────────────────
def _hand_back_not_release():
    """`release` NULLs the owner; at a working status that is E11's dead zone, which
    nothing can pick up ever. The Yard parks episodes for hours, so it MUST hand back."""
    i = ENGINE_SRC.index("THE YARD (2) — RELEASE AT THE NON-APPROVAL GATES")
    body = ENGINE_SRC[i:ENGINE_SRC.index("break", i)]
    assert "rail.hand_back(" in body, "the gate release does not call hand_back()"
    assert "rail.release(" not in body, (
        "the gate release calls rail.release(), which NULLs the owner and drops the "
        "episode into the dead zone the moment the board advances its status")


def _hand_back_still_expires_the_lease():
    """hand_back is only a pick-up path because the lease is already dead — otherwise
    reclaim_stale's `lease_until=lt.now` would skip it until the lease ran out."""
    src = inspect.getsource(rail.hand_back)
    assert "timedelta(seconds=1)" in src and "lease_until" in src, \
        "hand_back no longer expires the lease, so a parked episode waits it out first"


case("the gate release hands back (named owner), never releases (NULL owner)",
     _hand_back_not_release)
case("...and hand_back still expires the lease, or nothing would pick it up",
     _hand_back_still_expires_the_lease)


# ── 4. FINISH WHAT IS STARTED BEFORE STARTING MORE. ───────────────────────────
def _acquire_order():
    i = ENGINE_SRC.index("def acquire():")
    src = ENGINE_SRC[i:ENGINE_SRC.index("\ndef ", i + 1)]
    assert src.index("reclaim_stale") < src.index("claim_next"), (
        "acquire() tries claim_next before reclaim_stale, so a brand-new build would "
        "be started in front of an episode whose gate Jodie has already opened — the "
        "yard fills faster than it drains")
    assert "YARD_MAX" in src, "acquire() no longer respects the work-in-progress cap"
    assert src.index("reclaim_stale") < src.index("YARD_MAX"), (
        "the cap is checked before reclaim_stale — a worker at its cap could then not "
        "pick up its OWN parked episodes, or rescue a crashed one, and would deadlock")


def _cap_exists_and_is_two():
    i = ENGINE_SRC.index("YARD_MAX = ")
    val = int(ENGINE_SRC[i:].split("=", 1)[1].split("\n", 1)[0].strip())
    assert val == 2, (
        f"YARD_MAX is {val}. Jodie ruled the order — run two, then three, then five — "
        f"so 2 is the shipping value until somebody MEASURES what 3 returns per hour. "
        f"If it was raised on a measurement, write the number that lost beside it.")


case("acquire() reclaims before it claims, and the cap does not block the pick-up",
     _acquire_order)
case("YARD_MAX is 2 (Jodie: two, then three, then five)", _cap_exists_and_is_two)


# ── 5. THE WORK-IN-PROGRESS COUNT. ────────────────────────────────────────────
def _in_flight_identity():
    """Fed rows directly — this is the identity match, and it needs no rail.

    The bug guarded is specific: a PostgREST `like.worker*` would count
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
        f"in_flight matched {sorted(got)}; it must count the worker's own bare name "
        f"and its handed-back form, and NOTHING else (ep 3 is a different worker whose "
        f"name merely starts the same way; ep 4 is unowned)")


def _in_flight_statuses():
    assert "awaiting_render" in rail.IN_FLIGHT and "awaiting_cover" in rail.IN_FLIGHT, \
        ("the two non-approval gates must count against the cap — the engine WILL come "
         "back to them, so they are work in progress")
    assert "awaiting_approval" not in rail.IN_FLIGHT, (
        "awaiting_approval must NOT count against the cap: the engine has no further "
        "work for it, and counting it would jam the yard shut behind episodes waiting "
        "on the four approvals and the publish")
    assert rail.WORKING <= set(rail.IN_FLIGHT), "every working status is in flight"


case("in_flight counts this worker's episodes and not a lookalike's", _in_flight_identity)
case("in_flight counts the two non-approval gates, never awaiting_approval",
     _in_flight_statuses)


# ── 6. THE GATE ITSELF IS UNTOUCHED. ──────────────────────────────────────────
def _every_gate_still_stands():
    """The Yard changes what BLOCKS, never what a human decides. `awaiting_approval`
    still breaks out and waits, and the release path must never clear a flag or tick
    an approval on its way past."""
    i = ENGINE_SRC.index("THE YARD (2) — RELEASE AT THE NON-APPROVAL GATES")
    body = ENGINE_SRC[i:ENGINE_SRC.index("break", i)]
    for forbidden in ("title_approved", "script_read", "needs_look", "cover_choice"):
        assert forbidden not in body, (
            f"the gate release touches `{forbidden}` — it must move NO human decision, "
            f"only the claim")
    assert 'status == "awaiting_approval"' in ENGINE_SRC, \
        "awaiting_approval no longer breaks out of the loop on its own path"


case("the release moves the claim and nothing a human decides", _every_gate_still_stands)

print(f"\nyard pick-up (structural): {len(PASS)} passed, {len(FAIL)} failed")
if not FAIL:
    print("  ⚠️ structural only — the live red-first control is recorded in the "
          "docstring and needs Jodie's ruling to rejoin the suite")
sys.exit(1 if FAIL else 0)
