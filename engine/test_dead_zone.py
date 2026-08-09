#!/usr/bin/env python3
"""THE DEAD ZONE: a working episode that nothing will ever pick up.

    python engine/test_dead_zone.py

An episode at a working status with `claimed_by: NULL` is invisible to every path
that could rescue it — `reclaim_stale` filters `claimed_by=not.is.null`, `resume_own`
wants its own name, and `claim_next` wants a queued status. It sits there forever.

EP18 reached it in August. EP19 reached it on 9 Aug 2026, and the way it got there is
the point: `_exit_if_code_changed()` called `rail.release()` while the episode was still
`building`. Its own docstring warned, in those words, that "releasing WITHOUT clearing
ownership is how an episode reaches a working status with claimed_by: NULL — the dead
zone, which nothing can pick up, ever" — and the code did it anyway. The episode went
ownerless at 33% with its flag already cleared, and sat until a human asked why nothing
was moving. A comment describing a trap is not a guard against it. This is the guard.

⚠️ IT NEVER CALLS reclaim_stale(). That function patches the FIRST eligible row it
finds, with no way to say which — pointing it at the live rail while a real episode is
mid-build could hand somebody's episode to a test. Instead the test asks the database
the exact question reclaim_stale asks, SCOPED BY ID to its own throwaway ticket. Same
filters, same PostgREST, same answer about whether NULL matches `not.is.null` — and it
cannot touch anything else.

It creates one ticket and deletes it, and touches no episode folder.
"""
from __future__ import annotations

import datetime as dt
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
ME = "pp-engine@test-dead-zone"
RESCUER = "pp-engine@test-rescuer"


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def reclaimable_by(tid, worker):
    """reclaim_stale's OWN filters, asked as a read about one ticket.

    If this returns the row, reclaim_stale would take it; if it returns nothing,
    the row is unreachable and the episode is stranded.
    """
    stat = ",".join(sorted(rail.WORKING))
    rows = rail._request(
        "GET",
        f"?id=eq.{rail._q(tid)}&status=in.({stat})&claimed_by=not.is.null"
        f"&claimed_by=neq.{rail._q(worker)}&lease_until=lt.{rail._ts(rail._now())}")
    return rows[0] if rows else None


def make():
    """A throwaway ticket, claimed and building — an episode mid-flight."""
    t = rail.insert({
        "ep_number": 9019,
        "status": "building",
        "hook": "DEAD ZONE TEST — delete me",
        "claimed_by": ME,
        "lease_until": (dt.datetime.now(dt.timezone.utc)
                        + dt.timedelta(seconds=180)).isoformat(),
    })
    assert t and t.get("id"), "could not create a test ticket on the rail"
    return t["id"]


tid = make()
print(f"  (test ticket {tid} — ep 9019)\n")
try:
    def _control_release_strands_it():
        """CONTROL: the old behaviour, driven for real. It must STRAND the episode."""
        rail.set_fields(tid, {"claimed_by": ME,
                              "lease_until": (dt.datetime.now(dt.timezone.utc)
                                              - dt.timedelta(seconds=1)).isoformat()})
        rail.release(tid, ME)
        row = [r for r in rail.list_all() if r["id"] == tid][0]
        assert row["claimed_by"] is None, \
            f"release() left an owner ({row['claimed_by']!r}) — this is not the old path"
        assert row["status"] in rail.WORKING, \
            f"the ticket left the working statuses ({row['status']!r}), so it was never stranded"
        assert reclaimable_by(tid, RESCUER) is None, (
            "CONTROL FAILED: a working episode with claimed_by NULL was RECLAIMABLE. "
            "Then the dead zone does not exist as described, EP19 stalled for another "
            "reason, and the fix below is aimed at nothing.")

    case("CONTROL — release() on a working episode strands it forever",
         _control_release_strands_it)

    def _hand_back_leaves_it_reclaimable():
        rail.set_fields(tid, {"claimed_by": ME,
                              "lease_until": (dt.datetime.now(dt.timezone.utc)
                                              + dt.timedelta(seconds=180)).isoformat()})
        out = rail.hand_back(tid, ME, "exited for new code")
        assert out, "hand_back() matched no row — it did not let go at all"
        row = [r for r in rail.list_all() if r["id"] == tid][0]
        assert row["claimed_by"] and row["claimed_by"] != ME, (
            f"hand_back left claimed_by = {row['claimed_by']!r}. It must be a name that "
            f"is not the live worker and is not NULL.")
        assert "exited for new code" in row["claimed_by"], (
            f"the tombstone does not say why the worker left: {row['claimed_by']!r}. "
            f"Nobody reading the board can tell this from a crash.")
        got = reclaimable_by(tid, RESCUER)
        assert got is not None, (
            "hand_back() left the episode unreclaimable — the dead zone with extra steps.")

    case("hand_back() leaves it reclaimable, with a name that says why",
         _hand_back_leaves_it_reclaimable)

    def _the_engine_uses_it():
        """The fix has to be at the call site, not merely available.

        EP19's whole cost was a correct warning next to an incorrect call.
        """
        src = (HERE / "engine.py").read_text(encoding="utf-8")
        i = src.index("exiting so fresh code loads")
        j = src.index("raise SystemExit(0)", i)
        body = src[i:j]
        assert "rail.hand_back(" in body, (
            "the stale-code exit does not call rail.hand_back(). Whatever the comment "
            "above it says, this is the path that stranded EP19.")
        assert "rail.release(" not in body, \
            "the stale-code exit still calls rail.release(), which nulls the owner"

    case("the stale-code exit actually calls hand_back, not release",
         _the_engine_uses_it)

finally:
    rail.delete(tid)
    left = [r for r in rail.list_all() if r.get("ep_number") == 9019]
    print(f"\n  (test ticket deleted; {len(left)} left behind)")

print(f"\ndead zone: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
