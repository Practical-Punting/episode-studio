"""C2, THE ENGINE'S HALF — the "Paused" label must not OUTLIVE the flag.

Three times on 16 Aug 2026 the engine was rolling — fresh heartbeat, `needs_look`
false, a step genuinely in flight — and the rail's `progress_step` still read
**"Paused — needs a look (Rendering the motion cards)"**. A healthy build looked
stuck, which is the fault that scares an operator into intervening in something
that is working.

    THE MECHANISM. `flag_and_wait` STORES the sentence (engine.py), and when the
    flag clears it returns and retries the step WITHOUT REWRITING IT. Nothing
    rewrites `progress_step` until the NEXT step starts — so a long step carries
    the lie for its whole length. On `cards_render` that is hours.

E23c ruled on this class already, in these words: **derive it, never store it.**
`app.js` obeys it — `stageLine()` computes "Paused — needs a look (…)" from the
LIVE `needs_look`, and `test_board_stageline.mjs` pins that. The rail column
never got the same treatment, and the rail column is what the CLI, the engine's
own `status` output and anyone reading the row actually see.

So the rule this file pins is stronger than "rewrite it afterwards":

    🔒 THE STORED COLUMN NEVER CARRIES THE WORD "PAUSED" AT ALL.

A sentence that is never written cannot go stale. The pause is carried by
`needs_look`, which is a boolean that cannot lie about its own age, and the
wording is derived from it where a human reads it. What `progress_step` carries
is what it says on the tin: the step.

⚠️ AND IT IS WRITTEN AGAIN AT THE MOMENT OF CLEARING, not merely left alone.
`progress_pct` and the step can both have moved on while a human was away, and
"correct because nobody touched it" is not a property you can keep.

Run: python engine/test_flag_label_clears.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine as E                                                    # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"\n         <- {why}" if not cond and why else ""))


# ---------------------------------------------------------------- the doubles
class FakeRail:
    """The rail row, and a LEDGER of every write in order.

    The ledger is the point: the fault is not what the column ends up saying, it
    is what it says DURING the window between the clear and the next step.
    """

    def __init__(self):
        self.row = {"id": "EP-TEST", "needs_look": False, "progress_pct": 33,
                    "progress_step": "Rendering the motion cards — 10 of 10"}
        self.writes = []                       # [(what, value), ...] in order

    def flag_needs_look(self, _id, message):
        self.row["needs_look"] = True
        self.row["needs_look_message"] = message
        self.writes.append(("flag", True))
        return self.row

    def progress(self, _id, step_text, pct):
        self.row["progress_step"] = step_text
        self.row["progress_pct"] = pct
        self.writes.append(("progress", step_text))
        return self.row

    def checkpoint(self, _id, _state):
        return self.row

    def get_episode(self, _id):
        return dict(self.row)

    def set_fields(self, _id, fields):
        self.row.update(fields)
        return self.row


class FakeHB:
    class lost:
        @staticmethod
        def is_set():
            return False


class FakeProvider:
    def __init__(self, d):
        self._d = d

    def dir(self, _ep):
        return self._d


class Ctx:
    """The smallest thing flag_and_wait actually touches."""

    def __init__(self, rail, provider, clears_after=1):
        self._rail = rail
        self.provider = provider
        self.hb = FakeHB()
        self.watch = True
        self.mock = True
        self.state = {"steps": {}}
        self.ep = dict(rail.row)
        self._polls = 0
        self._clears_after = clears_after
        self.seen_while_flagged = []           # progress_step at each poll

    @property
    def id(self):
        return self.ep["id"]

    def save(self):
        pass

    def refresh(self):
        self._polls += 1
        if self._polls >= self._clears_after and self._rail.row["needs_look"]:
            self._rail.row["needs_look"] = False   # the human clears it on the board
            # STAMPED INTO THE SAME LEDGER as the writes, so "after the clear" is a
            # fact about ORDER rather than a guess from the final value. Without this
            # the assertion below passed vacuously: the only progress write in the
            # whole run was the flagged one, and it is trivially "last".
            self._rail.writes.append(("cleared", None))
        self.ep = dict(self._rail.row)
        self.seen_while_flagged.append(
            (self.ep.get("needs_look"), self.ep.get("progress_step")))
        return self.ep

    def check_alive(self):
        pass


def run_one(step="cards_render", clears_after=1):
    """Raise a flag on a step, let a human clear it, hand back the ledger."""
    rail = FakeRail()
    ctx = Ctx(rail, FakeProvider(Path(tempfile.mkdtemp())), clears_after)
    old_rail, old_sleep = E.rail, E.time.sleep
    E.rail = rail
    E.time.sleep = lambda _s: None             # the 3s mock poll, not waited on
    try:
        E.flag_and_wait(ctx, step, "something needs a human")
    finally:
        E.rail, E.time.sleep = old_rail, old_sleep
    return rail, ctx


PAUSED = "Paused"

print("\n-- while the flag is UP: the pause is a FLAG, not a stored sentence --")
rail, ctx = run_one()
flagged_writes = [v for w, v in rail.writes if w == "progress"]
check("the flag is raised on the rail",
      any(w == "flag" for w, _v in rail.writes))
check("🔴 the stored progress_step NEVER carries the word 'Paused'",
      not any(PAUSED in (v or "") for v in flagged_writes),
      f"progress_step was written as: {flagged_writes!r}. A stored sentence about "
      f"being paused outlives the pause — that is E23c, and it is why the board "
      f"derives its own line from live needs_look instead.")
check("  and what it does carry names the step in flight",
      any(E.STEP_LABEL["cards_render"] in (v or "") for v in flagged_writes),
      f"{flagged_writes!r}")

print("\n-- the moment it CLEARS: the column is rewritten, not merely left --")
kinds = [w for w, _v in rail.writes]
check("progress_step is written AFTER the flag was cleared",
      "cleared" in kinds and "progress" in kinds[kinds.index("cleared"):],
      f"the write ledger, in order, was {rail.writes!r} — the column has to be "
      f"re-stated on the way out, because pct and step can both have moved while "
      f"a human was away, and 'still correct because nobody touched it' is not a "
      f"property you can keep")
check("  and it reads as the TRUE current step",
      E.STEP_LABEL["cards_render"] in (rail.row.get("progress_step") or ""),
      f"progress_step = {rail.row.get('progress_step')!r}")
check("  and needs_look is false, so nothing anywhere says paused",
      rail.row.get("needs_look") is False and
      PAUSED not in (rail.row.get("progress_step") or ""),
      f"needs_look={rail.row.get('needs_look')} "
      f"progress_step={rail.row.get('progress_step')!r}")

print("\n-- THE WINDOW ITSELF: what a person reading the row would have seen --")
# This is the case that actually bit: not the end state, but every moment between
# the human clearing the flag and the next step starting.
bad = [(nl, ps) for nl, ps in ctx.seen_while_flagged
       if nl is False and PAUSED in (ps or "")]
check("🔴 there is NO moment where needs_look is false and the row says 'Paused'",
      not bad,
      f"{len(bad)} such moment(s): {bad[:3]!r}. This is exactly what was on the "
      f"board three times on 16 Aug — a rolling engine describing itself as paused.")

print("\n-- a long wait does not change the answer (several polls before the clear) --")
rail2, ctx2 = run_one(step="broll_collect", clears_after=4)
check("still never stores 'Paused' across four polls",
      not any(PAUSED in (v or "") for w, v in rail2.writes if w == "progress"),
      f"{[v for w, v in rail2.writes if w == 'progress']!r}")
check("  and ends on the step it was actually doing",
      E.STEP_LABEL["broll_collect"] in (rail2.row.get("progress_step") or ""),
      f"{rail2.row.get('progress_step')!r}")

print("\n-- the board's derived line is UNTOUCHED by this (the paired evidence) --")
# app.js must go on SAYING "Paused — needs a look (…)" while the flag is live; that
# half is pinned by test_board_stageline.mjs. Named here so the two are read together
# rather than one being taken for the whole rule.
board = (HERE.parent / "app.js").read_text(encoding="utf-8")
check("app.js still derives the pause wording from live needs_look",
      'if (ep.needs_look) {' in board and '"Paused — needs a look"' in board,
      "the wording must live exactly one place — where it is derived")

print(f"\nflag label: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
