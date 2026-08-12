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
    # The hook and byline are part of a normal row (12 Aug 2026): the fast path does
    # not fire for an episode still waiting on the operator's own words, because that
    # one is HER turn and waking the drafting pass every 25s to re-decide it cannot
    # start is exactly the churn the fast path was built to avoid. The missing-words
    # case has its own suite in test_packaging_entry.py.
    r = {"id": f"id{n}", "ep_number": n, "status": "queued", "needs_look": False,
         "hook": "A hook", "byline": "A byline",
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


# ------------------------------------------------------------------- 6 -----
# 🔴 A FAILED ATTEMPT RETRIES IN A MINUTE, NOT A QUARTER OF AN HOUR (EP22, 12 Aug).
# EP22's attempt 1 was rejected over one figure and its repair round halted at 05:27.
# The next attempt did not start until 05:40 and succeeded at 05:43 — so thirteen of
# the twenty minutes Jodie watched were the retry timer, not work.
#
# ⚠️ THIS REVERSES AN EARLIER TRADE-OFF ON PURPOSE, and case 2 above still holds.
# The fast path was deliberately kept to ZERO-attempt episodes so a failing draft
# could not be retried every 25 seconds and burn its bound "before anyone looked at
# the board". Two things make the reversal safe now:
#   · it is a SEPARATE question with its own ~60s cooldown, so the 25s hammering that
#     case 2 guards against still cannot happen — _a_brand_new_episode_is_waiting is
#     untouched and still answers only for a never-drafted episode;
#   · f552c00 put every attempt on the BOARD, so "gives up sooner" now means the
#     visible "needs a look" arrives sooner, which is the point rather than the risk.
def _mk(attempts, age_secs):
    """A provider whose episode has `attempts` recorded, `age_secs` ago."""
    import datetime
    import json
    prov = Prov({})
    d = prov.dir({"ep_number": 20})
    (d / "docs").mkdir(parents=True, exist_ok=True)
    when = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(seconds=age_secs))
    engine._draft_ledger_path(d).write_text(json.dumps(
        {"attempts": attempts, "last_at": when.isoformat(),
         "last_note": "commissioning the script"}), encoding="utf-8")
    return prov


def _ready(rows, attempts, age_secs):
    prov = _mk(attempts, age_secs)
    with Rail(rows):
        return engine._a_draft_is_ready_to_retry(prov)


def _a_failed_attempt_retries_within_a_minute_or_two():
    got = _ready([row(20)], attempts=1, age_secs=90)
    assert got == 20, (
        f"a part-drafted episode was not offered for retry ({got!r}), so a draft that "
        f"fails once still waits out the 15-minute pass")


def _but_not_instantly():
    got = _ready([row(20)], attempts=1, age_secs=5)
    assert got is None, (
        "an attempt that failed five seconds ago was retried at once — that is the "
        "tight loop the cooldown exists to prevent")


def _the_cap_is_unchanged():
    got = _ready([row(20)], attempts=engine.DRAFT_ATTEMPT_LIMIT, age_secs=600)
    assert got is None, (
        f"an episode at the {engine.DRAFT_ATTEMPT_LIMIT}-attempt cap was offered "
        f"again — the bound must not move, only the waiting between attempts")
    assert engine.DRAFT_ATTEMPT_LIMIT == 3, "the attempt cap changed"


def _a_never_drafted_one_is_not_this_question():
    got = _ready([row(20)], attempts=0, age_secs=600)
    assert got is None, (
        "a never-drafted episode came back from the RETRY question — that one belongs "
        "to _a_brand_new_episode_is_waiting, and two paths answering for the same "
        "episode is how it gets commissioned twice")


def _the_same_guards_apply():
    for kw, why in [({"needs_look": True}, "an open question"),
                    ({"claimed_by": "someone"}, "already being worked"),
                    ({"script_snapshot": "words"}, "already has words"),
                    ({"hook": None}, "waiting on HER words, not the writer")]:
        got = _ready([row(20, **kw)], attempts=1, age_secs=600)
        assert got is None, f"retried an episode that is {why}: {kw}"


def _the_loop_asks_the_retry_question_too():
    src = Path(engine.__file__).read_text(encoding="utf-8")
    i = src.index("def cmd_run(")
    body = src[i:]
    assert "_a_draft_is_ready_to_retry(provider)" in body, \
        "the idle loop never asks the retry question, so the fix is unreachable"
    assert "> 900" in body, "the 900s safety net has been removed"


case("a draft that failed is retried within a minute or two",
     _a_failed_attempt_retries_within_a_minute_or_two)
case("  but never instantly — the cooldown holds", _but_not_instantly)
case("  and the 3-attempt cap is untouched", _the_cap_is_unchanged)
case("  a never-drafted episode is NOT this question's job",
     _a_never_drafted_one_is_not_this_question)
case("  every other guard still applies", _the_same_guards_apply)
case("  and the idle loop actually asks it", _the_loop_asks_the_retry_question_too)


# ------------------------------------------------------------------- 7 -----
# WHAT IT ACTUALLY COSTS IN WALL-CLOCK, driven through the real function on a
# simulated clock rather than asserted from the constants.
def _wall_clock():
    """Seconds of WAITING across a draft that keeps failing, on a simulated clock.

    Counts only the gaps BETWEEN attempts — the commissions themselves take the same
    few minutes either way, so the gaps are the whole difference. Each gap is found by
    ageing the ledger until the real function says the episode is ready again, so this
    measures the shipped behaviour rather than restating the constant.
    """
    import datetime
    import json
    prov = _mk(attempts=1, age_secs=0)
    d = prov.dir({"ep_number": 20})
    total = 0.0
    for attempt in range(1, engine.DRAFT_ATTEMPT_LIMIT):
        age = 0.0
        while age < 4000:
            when = (datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(seconds=age))
            engine._draft_ledger_path(d).write_text(json.dumps(
                {"attempts": attempt, "last_at": when.isoformat()}), encoding="utf-8")
            with Rail([row(20)]):
                if engine._a_draft_is_ready_to_retry(prov) == 20:
                    break
            age += 5.0
        total += age
    return total


def _a_self_healing_draft_finishes_in_minutes():
    secs = _wall_clock()
    mins = secs / 60.0
    assert mins < 4, (
        f"a draft that fails and retries still waits {mins:.1f} minutes between "
        f"attempts — the 15-minute silence is not gone")
    # and say what it was, so the number is never a bare claim
    old = (900.0 * (engine.DRAFT_ATTEMPT_LIMIT - 1)) / 60.0
    print(f"        waiting across all {engine.DRAFT_ATTEMPT_LIMIT} attempts: "
          f"{mins:.1f} min (was {old:.0f} min on the 900s pass)")


def _all_three_failing_reaches_the_flag_quickly():
    secs = _wall_clock()
    # the bound is reached after the LAST attempt, so the waiting is the same figure;
    # what matters is that it is minutes, not the better part of an hour.
    assert secs < 300, (
        f"a draft that fails all {engine.DRAFT_ATTEMPT_LIMIT} attempts takes "
        f"{secs / 60:.1f} minutes of pure waiting to reach 'needs a look'")


case("a draft that fails then succeeds waits minutes, not fifteen",
     _a_self_healing_draft_finishes_in_minutes)
case("  and one that fails all 3 reaches 'needs a look' quickly",
     _all_three_failing_reaches_the_flag_quickly)


print(f"\nkick on submit: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
