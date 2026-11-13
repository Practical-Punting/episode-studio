#!/usr/bin/env python3
"""A TWO-WAY ROW ON THE RAIL IS NEVER PICKED UP BY THE SINGLE-PRESENTER ENGINE (migration 009).

    python engine/test_twoway_not_claimable.py

From 13 Nov 2026 a two-way episode has a normal rail row from the paste, sitting at
`queued` like any other. It is built by `engine/twoway_run.py`. If the single engine
claimed one, it would start a single-presenter build in a two-way's folder.

Both doors are tested on the LIVE rail with one throwaway ticket (ep 9056), asked as a read
SCOPED BY ID — the `test_yard_pickup.py` method, so a running engine is never offered it:
  · the claim door  (`list_queued` → `claim_next`, and `claim`)
  · the pick-up door (`reclaim_stale`: a working status, someone else's dead lease)
Each with a CONTROL first: the same filters WITHOUT `SINGLE_ONLY` must return the ticket,
or the test cannot see what it exists to catch. Then the same ticket as `single` must
still come back WITH the filter — the guard must not drop real work.

It deletes only the id its own insert returned (E46's terms, enforced by shape in
`test_production_never_deletes.py`), and touches no episode folder.
"""
from __future__ import annotations

import ast
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rail                                                            # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PASS, FAIL = [], []
ME = "pp-engine@test-twoway-picker"


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


def ask_claim(tid, single_only):
    """claim_next's filters, as a read about ONE ticket (NOT_A_TEST left off on purpose:
    the ticket is a test number, and the question here is the FORMAT filter)."""
    f = rail.SINGLE_ONLY if single_only else ""
    rows = rail._request("GET", f"?id=eq.{rail._q(tid)}&status=eq.queued"
                                f"&title_approved=is.true&script_read=is.true{f}")
    return rows[0] if rows else None


def ask_reclaim(tid, single_only):
    stat = ",".join(sorted(rail.WORKING))
    f = rail.SINGLE_ONLY if single_only else ""
    rows = rail._request("GET", f"?id=eq.{rail._q(tid)}&status=in.({stat})"
                                f"&claimed_by=not.is.null&claimed_by=neq.{rail._q(ME)}"
                                f"&title_approved=is.true&script_read=is.true"
                                f"&lease_until=lt.{rail._ts(rail._now())}{f}")
    return rows[0] if rows else None


tid = rail.insert({"ep_number": 9056, "status": "queued", "format": "two-way",
                   "hook": "TWO-WAY NOT-CLAIMABLE TEST — delete me",
                   "title_approved": True, "script_read": True})["id"]
print(f"  (test ticket {tid} — ep 9056)\n")
try:
    case("CONTROL — without the format filter, the claim door takes a queued TWO-WAY",
         lambda: (_ for _ in ()).throw(AssertionError("control did not reproduce"))
         if ask_claim(tid, False) is None else None)
    case("with SINGLE_ONLY, the claim door does NOT see it",
         lambda: (_ for _ in ()).throw(AssertionError("a two-way is claimable"))
         if ask_claim(tid, True) is not None else None)

    rail.set_fields(tid, {"status": "building", "claimed_by": "someone-else (crashed)",
                          "lease_until": dead()})
    case("CONTROL — without the format filter, the pick-up door takes a two-way with a dead lease",
         lambda: (_ for _ in ()).throw(AssertionError("control did not reproduce"))
         if ask_reclaim(tid, False) is None else None)
    case("with SINGLE_ONLY, the pick-up door does NOT see it",
         lambda: (_ for _ in ()).throw(AssertionError("a two-way is reclaimable"))
         if ask_reclaim(tid, True) is not None else None)

    rail.set_fields(tid, {"format": "single", "status": "queued", "claimed_by": None,
                          "lease_until": None})
    case("the same ticket as SINGLE is still claimable with the filter (no real work lost)",
         lambda: (_ for _ in ()).throw(AssertionError("the filter drops single rows"))
         if ask_claim(tid, True) is None else None)
finally:
    rail.delete(tid)
    left = [r for r in rail.list_all() if r.get("ep_number") == 9056]
    print(f"\n  (test ticket deleted; {len(left)} left behind)")

# ── drift: the filter is really in every door of rail.py (the copies above are the test's) ──
SRC = (HERE / "rail.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)


def body(name):
    n = next(x for x in ast.walk(TREE) if isinstance(x, ast.FunctionDef) and x.name == name)
    return {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}


for fn in ("list_queued", "claim", "claim_next", "reclaim_stale", "resume_own"):
    case(f"rail.{fn}() really uses SINGLE_ONLY (read off the syntax tree)",
         lambda fn=fn: None if ("SINGLE_ONLY" in body(fn) or
                               (fn == "claim_next" and "list_queued" in
                                {x.func.id for x in ast.walk(next(
                                    y for y in ast.walk(TREE) if isinstance(y, ast.FunctionDef)
                                    and y.name == fn)) if isinstance(x, ast.Call)
                                 and isinstance(x.func, ast.Name)}))
         else (_ for _ in ()).throw(AssertionError(f"{fn} lost the format filter")))
case("SINGLE_ONLY is the format=single filter",
     lambda: None if rail.SINGLE_ONLY == "&format=eq.single"
     else (_ for _ in ()).throw(AssertionError(rail.SINGLE_ONLY)))

print(f"\ntwo-way not claimable: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
