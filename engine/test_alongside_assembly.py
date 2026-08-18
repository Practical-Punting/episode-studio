#!/usr/bin/env python3
"""THE SIDE STREAM MAY CHANGE THE CLOCK AND NOTHING ELSE.

    python engine/test_alongside_assembly.py

`test_tail_is_independent.py` proves the three tail steps never read the assembled
video. That is the SAFETY argument for building them during assembly, and it is only
half of what this change needs, because "does not read the video" is not "safe on a
second thread":

  · `thumbnail` RAISES A HUMAN FLAG (`thumbnail_placement_review`);
  · `ebook_pdf` writes `ebook_url` to the rail;
  · `thumbnail` writes `thumbnail_preview_url` into `ctx.state` and saves it;
  · and `rail.checkpoint` says, in its own docstring, "Single-writer per episode, so a
    full-object write is safe" — an invariant a second writer silently repeals.

🔴 SO THE SPLIT IS: THE WORK GOES ALONGSIDE, THE BOOKKEEPING AND THE ASK DO NOT.
The side thread may call exactly the three `_work_*` functions, which build artefacts
and return them. Every `ctx.state` write, every rail write and every flag stays on the
main thread at the same point in the order it has always been at.

What this file holds to:
  1. the side thread's functions touch no state, no rail and no flag — AST, not grep;
  2. a side stream that fails marks NOTHING, so the phase builds that step normally;
  3. the hand-off is POPPED, so a retry after a flag rebuilds instead of reusing;
  4. a step handed an early artefact does NOT build it a second time;
  5. the phase order, and the guard that keeps it — including the case that shipped.

⚠️ NOTHING HERE TOUCHES THE LIVE RAIL, THE NETWORK, OR A RUNNING ENGINE.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine                                                          # noqa: E402

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


SRC = (HERE / "engine.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)


def _fn(name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} is not in engine.py at all")


# ── 1. WHAT THE SIDE THREAD IS ALLOWED TO TOUCH ────────────────────────────────
# Asked of the CALLS, not of a regex over the text. `_work_thumbnail` mentions neither
# "save" nor "flag" anywhere in its body, and a grep would have called that proof.
FORBIDDEN_ATTRS = {"save", "ep_set", "checkpoint", "progress", "flag_needs_look",
                   "set_fields", "thumbnail_placement_review_for", "stamp"}


def _the_work_functions_write_nothing():
    for name in ("_work_ebook_pdf", "_work_thumbnail", "_work_web_copies"):
        node = _fn(name)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                f = sub.func
                attr = f.attr if isinstance(f, ast.Attribute) else None
                assert attr not in FORBIDDEN_ATTRS, (
                    f"{name} calls .{attr}() — the side thread must not write state, "
                    f"write the rail, or raise a flag. Move it to the step function, "
                    f"which runs on the main thread.")
            # `ctx.state[...] = x` is the other way to write state.
            if isinstance(sub, (ast.Assign, ast.AugAssign)):
                tgts = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                for t in tgts:
                    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute):
                        assert t.value.attr != "state", (
                            f"{name} assigns into ctx.state — that is a second writer "
                            f"to the thing rail.checkpoint promises has only one.")


case("the side thread's work functions write no state, no rail, no flag",
     _the_work_functions_write_nothing)


def _the_side_thread_calls_only_those():
    """CONTROL on the registry itself: the thread runs ALONGSIDE_WORK and nothing else.

    A future step added to ALONGSIDE without a `_work_` half would otherwise be run
    whole — flag and all — on the side thread, which is the fault this file exists for.
    """
    assert set(engine.ALONGSIDE) == set(engine.ALONGSIDE_WORK), (
        f"ALONGSIDE is {engine.ALONGSIDE} but ALONGSIDE_WORK covers "
        f"{sorted(engine.ALONGSIDE_WORK)} — every step that goes alongside needs a "
        f"work-only half, or the side thread would run its flag too.")
    body = ast.get_source_segment(SRC, _fn("_run_alongside")) or ""
    assert "ALONGSIDE_WORK[name](ctx)" in body, (
        "_run_alongside no longer dispatches through ALONGSIDE_WORK — if it reaches "
        "STEP_FNS instead it is running the bookkeeping and the ask off-thread.")


case("CONTROL — every alongside step has a work-only half, and the thread uses it",
     _the_side_thread_calls_only_those)


# ── 2. A FAILED SIDE STREAM CHANGES NOTHING ───────────────────────────────────
class FakeCtx:
    """The least ctx `_run_alongside` can be driven with."""

    def __init__(self):
        self.state = {"steps": {}}
        self.saves = 0
        self.alongside_done = {}

    def check_alive(self):
        return None

    def save(self):                      # must never be called from the side thread
        self.saves += 1


def _a_failing_side_stream_marks_nothing():
    ctx = FakeCtx()
    done = {}
    boom = {"ebook_pdf": lambda c: (_ for _ in ()).throw(RuntimeError("weasyprint died")),
            "thumbnail": lambda c: {"out": "t.png", "url": None}}
    real = engine.ALONGSIDE_WORK
    try:
        engine.ALONGSIDE_WORK = boom
        engine._run_alongside(ctx, ["ebook_pdf", "thumbnail"], done)
    finally:
        engine.ALONGSIDE_WORK = real
    assert done == {}, (
        f"the side stream failed and still handed something over: {done}. Nothing may "
        f"be marked, or the phase would skip a step that was never built.")
    assert ctx.state["steps"] == {}, "the side stream marked a step done"
    assert ctx.saves == 0, "the side stream saved state — it must never write"


case("a side stream that fails hands over nothing, and saves nothing",
     _a_failing_side_stream_marks_nothing)


def _it_stops_at_the_first_failure_and_does_not_raise():
    """It must not raise: an exception on that thread would be swallowed by threading
    and the phase would carry on believing the artefacts were coming."""
    ctx = FakeCtx()
    done = {}
    order = []

    def ok(name):
        def f(c):
            order.append(name)
            return {"out": name}
        return f

    def bad(c):
        order.append("bad")
        raise OSError("disk full")

    real = engine.ALONGSIDE_WORK
    try:
        engine.ALONGSIDE_WORK = {"a": ok("a"), "b": bad, "c": ok("c")}
        engine._run_alongside(ctx, ["a", "b", "c"], done)      # must not raise
    finally:
        engine.ALONGSIDE_WORK = real
    assert order == ["a", "bad"], f"it did not stop at the failure: {order}"
    assert list(done) == ["a"], f"it handed over past the failure: {done}"


case("it stops at the first failure and never raises on the side thread",
     _it_stops_at_the_first_failure_and_does_not_raise)


# ── 3. THE HAND-OFF IS POPPED ─────────────────────────────────────────────────
def _the_handoff_is_taken_not_borrowed():
    """A rejected thumbnail must be REBUILT on the retry, not handed back.

    `thumbnail` flags for a human look. If the answer is "no, fix the crop", the step
    runs again — and if the early artefact were still sitting there it would be handed
    the very picture that was just rejected, and pass.
    """
    ctx = FakeCtx()
    ctx.alongside_done = {"thumbnail": {"out": "hero.png", "url": "u"}}
    first = engine._alongside_result(ctx, "thumbnail")
    assert first is not None, "the hand-off was not picked up at all"
    again = engine._alongside_result(ctx, "thumbnail")
    assert again is None, (
        "the early artefact is still there on a second call — a retry after a flag "
        "would be handed the artefact a human just rejected.")


case("the hand-off is POPPED, so a retry rebuilds instead of reusing",
     _the_handoff_is_taken_not_borrowed)


# ── 4. NOTHING IS BUILT TWICE ─────────────────────────────────────────────────
def _an_early_artefact_is_not_built_again():
    """The saving is only real if the step does NOT redo the work it was handed."""
    calls = []

    class P:
        def build_web_copies(self, ep):
            calls.append("built")
            return "report"

    class C(FakeCtx):
        provider = P()
        ep = {"id": "PP-EP9001"}

    ctx = C()
    ctx.alongside_done = {"web_copies": {"report": "early report"}}
    meta = engine.step_web_copies(ctx)
    assert calls == [], "the step rebuilt an artefact the side stream already made"
    assert meta["report"] == "early report", f"it did not use the early artefact: {meta}"
    assert meta["alongside"] is True, "the meta does not record that it came early"

    # …and with nothing handed over it builds normally. Both halves, or this proves
    # only that a dict lookup works.
    ctx2 = C()
    meta2 = engine.step_web_copies(ctx2)
    assert calls == ["built"], "with no early artefact the step did not build one"
    assert meta2["alongside"] is False, "it claims an early artefact it never got"


case("a step handed an early artefact does not build it twice — and still builds "
     "normally without one", _an_early_artefact_is_not_built_again)


# ── 5. THE ORDER, AND THE GUARD THAT HOLDS IT ─────────────────────────────────
def _self_qc_is_strictly_last():
    a = engine.PHASES["assembling"]
    assert a[-1] == "self_qc", (
        f"self_qc is not last — anything after it is something it did not grade. "
        f"Order: {a}")
    assert a.index("youtube_copy") < a.index("self_qc"), (
        "youtube_copy still runs after self_qc, so QC keeps reporting 'no YouTube copy "
        "source found' about a file written three minutes later.")


case("self_qc is strictly last, and youtube_copy runs before it",
     _self_qc_is_strictly_last)


def _the_guard_rejects_the_order_that_shipped():
    """CONTROL: drive check_locked_order against the order main actually carried."""
    good = list(engine.PHASES["assembling"])
    shipped = ["assemble_passA", "assemble_passB", "ebook_pdf", "thumbnail",
               "web_copies", "self_qc", "youtube_copy"]
    try:
        engine.PHASES["assembling"] = shipped
        problems = engine.check_locked_order()
        assert [p for p in problems if "must be the LAST step" in p], (
            f"the guard accepts self_qc in the middle of the phase: {problems}")
        assert [p for p in problems if "youtube_copy must run BEFORE" in p], (
            f"the guard does not catch the false QC warning: {problems}")
        engine.PHASES["assembling"] = good
        left = [p for p in engine.check_locked_order()
                if "self_qc" in p or "youtube_copy" in p or "web_copies" in p]
        assert not left, f"the good order is being rejected: {left}"
    finally:
        engine.PHASES["assembling"] = good


case("CONTROL — the guard rejects the order that shipped, and accepts this one",
     _the_guard_rejects_the_order_that_shipped)


def _the_phase_joins_before_it_transitions():
    """An episode must never be handed on while a thread is still writing its folder."""
    body = ast.get_source_segment(SRC, _fn("run_phase")) or ""
    assert "finally:" in body and "_join_alongside" in body, (
        "run_phase does not join the side stream in a finally — a step that flags or "
        "raises would leave a thread writing into a folder nobody is watching.")
    j, f = body.index("_join_alongside(side)"), body.index("_finish_phase")
    assert j < f, ("run_phase transitions the episode before joining the side stream — "
                   "the join must come first, in the finally.")


case("the phase joins the side stream before it transitions the episode",
     _the_phase_joins_before_it_transitions)


print(f"\nalongside assembly: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
