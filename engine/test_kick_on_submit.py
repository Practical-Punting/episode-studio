#!/usr/bin/env python3
"""KICK ON SUBMIT — pressing Build starts work in seconds, not a quarter of an hour.

    python engine/test_kick_on_submit.py

The drafting pass runs on a 900s timer, which is right for retries and wrong for the
thing a person actually does: queueing an episode and watching nothing happen for up to
fifteen minutes.

🔴 THE DANGEROUS VERSION OF THIS FIX, which is why the predicate is what it is: simply
running the pass every 25 seconds would retry a FAILING draft 36 times an hour and burn
its whole attempt bound before anyone looked at the board. "Start sooner" would become
"give up sooner", and it would spend tokens doing it. So the fast path fires ONLY for an
episode that has never been drafted at all; every retry stays on the slow timer.

Hermetic: the rail and the attempt ledger are stubbed. No commission is ever run.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import engine                                                        # noqa: E402

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


class Prov:
    def __init__(self, attempts):
        self.attempts = attempts
        self.root = Path(tempfile.mkdtemp(prefix="kick_"))

    def dir(self, ep):
        return self.root / f"PP-EP{int(ep['ep_number']):02d}"


class Rail:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        self._o = (engine.rail.list_queued, engine._draft_attempts)
        engine.rail.list_queued = lambda: self.rows
        return self

    def __exit__(self, *a):
        engine.rail.list_queued, engine._draft_attempts = self._o
        return False


def row(n, **kw):
    r = {"id": f"id{n}", "ep_number": n, "status": "queued", "needs_look": False,
         "script_snapshot": None, "script_doc_url": None, "claimed_by": None}
    r.update(kw)
    return r


def ask(rows, attempts_by_ep):
    prov = Prov(attempts_by_ep)
    with Rail(rows):
        engine._draft_attempts = lambda d: attempts_by_ep.get(d.name, 0)
        return engine._a_brand_new_episode_is_waiting(prov)


# ------------------------------------------------------------------- 1 -----
def _a_freshly_queued_episode_is_seen_at_once():
    got = ask([row(20)], {})
    assert got == 20, (
        f"a brand-new queued episode was not picked up ({got!r}), so Build still means "
        f"waiting out the 15-minute pass")


case("a freshly queued episode with no script is picked up immediately",
     _a_freshly_queued_episode_is_seen_at_once)


# ------------------------------------------------------------------- 2 -----
def _one_already_attempted_is_left_to_the_slow_timer():
    """🔴 THE ONE THAT PROTECTS THE ATTEMPT BOUND. Without this the fast path retries a
    failing draft every 25 seconds and exhausts it in minutes, spending tokens."""
    got = ask([row(20)], {"PP-EP20": 1})
    assert got is None, (
        "an episode that has ALREADY been drafted once was offered to the fast path. "
        "It would be retried every 25s and burn its whole attempt bound before anyone "
        "looked at the board — start sooner becoming give up sooner.")


case("an episode already attempted is NOT re-triggered — retries stay on the slow pass",
     _one_already_attempted_is_left_to_the_slow_timer)


# ------------------------------------------------------------------- 3 -----
def _one_being_worked_is_left_alone():
    got = ask([row(20, claimed_by="pp-engine@other")], {})
    assert got is None, "an episode another worker is holding was offered to the fast path"


case("an episode already claimed by a worker is left alone", _one_being_worked_is_left_alone)


# ------------------------------------------------------------------- 4 -----
def _an_episode_that_already_has_words_is_not_drafted():
    assert ask([row(20, script_snapshot="Gordon says hello.")], {}) is None, \
        "an episode that already has a script was offered for drafting"
    assert ask([row(20, script_doc_url="https://docs/…")], {}) is None, \
        "an episode with a Doc was offered for drafting — A5: a Doc keeps its transport"
    assert ask([row(20, needs_look=True)], {}) is None, \
        "an episode with a human question open was offered for drafting"


case("nothing that already has words, a Doc, or an open question is touched",
     _an_episode_that_already_has_words_is_not_drafted)


# ------------------------------------------------------------------- 5 -----
def _the_loop_actually_uses_it():
    """The fix has to be at the call site, not merely available — the EP19 lesson."""
    src = (HERE / "engine.py").read_text(encoding="utf-8")
    i = src.index("def cmd_run(")
    body = src[i:]
    assert "_a_brand_new_episode_is_waiting(provider)" in body, \
        "the idle loop never asks the fast question"
    assert "FAST_DRAFT_SECS" in body, "the fast interval is not used in the loop"
    # the slow pass must SURVIVE — it is the safety net and the only retry path
    assert "> 900" in body, "the 900s safety net has been removed"


case("the idle loop asks the fast question, and the 900s safety net survives",
     _the_loop_actually_uses_it)


print(f"\nkick on submit: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
