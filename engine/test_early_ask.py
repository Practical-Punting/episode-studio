#!/usr/bin/env python3
"""THE ASK GOES UP EARLY. THE BUILD STILL WAITS WHERE IT ALWAYS WAITED.

    python engine/test_early_ask.py

RAISING a question and WAITING on the answer are two different things, and only the
second costs a build any time. The thumbnail placement ask used to be both at once,
after assembly — the machine idle, the whole stall equal to however long it took a
human to notice. The picture is now built DURING assembly (see
test_alongside_assembly.py), so the question can be asked during it too.

  · RAISE at the assemble_passA/passB seam, on the MAIN thread.
  · WAIT at `step_thumbnail`, exactly where it waits today.
  · Answered by then → no stall at all. Not answered → nothing is worse than before.

🔴 THE TRAP THIS FILE EXISTS FOR — BEING ASKED THE SAME QUESTION TWICE. `ask_once`
returns silently only if `.answered-` exists, and only `answer_pending_gates` writes
that, and `_record_gate_answers` refuses to promote anything unless `flag_step` proves
a flag was really raised. Miss any link and Jodie answers on the board during assembly
and is asked again ten minutes later. Across 270 episodes that is not a saving, it is
an irritation with a saving attached.

🔴 AND THE OPPOSITE TRAP, WHICH IS WORSE. `_record_gate_answers` does NOT check that
anybody answered — its CALLERS do, by looking at `needs_look`. Promote without that
guard and an UNANSWERED human gate is marked answered and walked through in silence.
That is EP23's fault rebuilt one layer up, and it is why `_take_early_answer` refreshes
the row and reads the flag before it promotes anything.

⚠️ NOTHING HERE TOUCHES THE LIVE RAIL, THE NETWORK, OR A RUNNING ENGINE.
"""
from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine                                                          # noqa: E402
import providers                                                       # noqa: E402

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
    for n in ast.walk(TREE):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name} is not in engine.py")


class FakeProvider:
    def __init__(self, root, message="LOOK AT THE THUMBNAIL",
                 preview="https://example.invalid/thumb-preview.png"):
        self.root, self.message, self.asked = Path(root), message, []
        self.preview = preview

    def dir(self, ep):
        return self.root

    def early_ask_message(self, ep, step):
        return self.message, (self.preview if self.message else None)


class FakeRail:
    def __init__(self):
        self.flagged = []

    def flag_needs_look(self, id, message):
        self.flagged.append((id, message))


class FakeCtx:
    def __init__(self, root, needs_look=False, message="LOOK AT THE THUMBNAIL",
                 preview="https://example.invalid/thumb-preview.png"):
        self.ep = {"id": "PP-EP9001", "needs_look": needs_look}
        self.state = {"steps": {}}
        self.provider = FakeProvider(root, message, preview)
        self.saves = 0

    @property
    def id(self):
        return self.ep["id"]

    def save(self):
        self.saves += 1

    def refresh(self):
        return self.ep


def _with_fake_rail(fn):
    real = engine.rail
    fake = FakeRail()
    try:
        engine.rail = fake
        return fn(fake)
    finally:
        engine.rail = real


# ── 1. THE ORDER THAT MAKES THE SEAM WORTH ANYTHING ───────────────────────────
def _thumbnail_is_built_first_alongside():
    """CONTROL for the whole feature: with ebook_pdf first (3.8 min) the picture does
    not exist at the 3.0-minute seam and the early ask buys NOTHING."""
    assert engine.ALONGSIDE[0] == "thumbnail", (
        f"the side stream builds {engine.ALONGSIDE[0]} first, so at the "
        f"assemble_passA/passB seam there is no thumbnail to ask about. Order: "
        f"{engine.ALONGSIDE}")
    assert engine.ALONGSIDE.index("web_copies") > engine.ALONGSIDE.index("thumbnail"), \
        "web_copies needs the full-size thumbnail this stream writes"
    # …and the PHASE order is NOT the side-stream order. The serial fallback keeps its
    # own sequence, and the guard still holds it.
    a = engine.PHASES["assembling"]
    assert a.index("thumbnail") < a.index("web_copies")


case("the side stream builds the thumbnail FIRST, so the seam has a picture to ask about",
     _thumbnail_is_built_first_alongside)


# ── 2. THE RAISE DOES NOT WAIT ────────────────────────────────────────────────
def _the_early_raise_never_blocks():
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td)

        def go(fake):
            engine._raise_early_ask(ctx, "thumbnail")     # must not raise, must not wait
            return fake

        fake = _with_fake_rail(go)
        assert fake.flagged, "the ask never reached the board"
        assert fake.flagged[0][1] == "LOOK AT THE THUMBNAIL", fake.flagged
        marker = Path(td) / "thumbnail" / ".asked-placement-reviewed"
        assert marker.is_file(), (
            "no .asked- marker was written, so ask_once would ask again from scratch "
            "at the step and nothing could ever be promoted")
        assert ctx.state.get("flag_step") == "thumbnail", (
            "flag_step was not written. It is the PROOF a flag was really raised, and "
            "without it _record_gate_answers promotes nothing — Jodie gets asked twice.")
        assert ctx.state["early_ask"]["thumbnail"] is True


case("the early raise flags the board, writes the marker and RETURNS — it never waits",
     _the_early_raise_never_blocks)


def _it_asks_once_not_at_every_seam():
    """There are several seams in the assembling phase. The ask goes up at the first
    one that has a picture, and the rest must be silent — a board that re-flags the
    same question every few minutes is noise, and it would re-flag one Jodie has
    already cleared."""
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td)

        def go(fake):
            for _seam in range(4):
                engine._raise_early_ask(ctx, "thumbnail")
            return fake

        fake = _with_fake_rail(go)
        assert len(fake.flagged) == 1, (
            f"the ask was put on the board {len(fake.flagged)} times — every seam "
            f"re-raised it, including seams after Jodie may have cleared it.")


case("it asks at ONE seam, not at every seam", _it_asks_once_not_at_every_seam)


def _no_picture_no_ask():
    """An ask that points at a file which is not there yet is worse than no ask."""
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td, message=None)          # provider says: not ready

        def go(fake):
            engine._raise_early_ask(ctx, "thumbnail")
            return fake

        fake = _with_fake_rail(go)
        assert not fake.flagged, "an ask went up with no artefact behind it"
        assert not (Path(td) / "thumbnail" / ".asked-placement-reviewed").exists()
        assert not ctx.state.get("early_ask"), (
            "it recorded an early ask it never made, so the real seam later would "
            "skip it and the ask would never go up early at all")


case("no picture yet → no ask, and nothing recorded (the next seam tries again)",
     _no_picture_no_ask)


def _a_legacy_answer_is_honoured():
    """🔴 EP01–EP23 CARRY PRE-C3 MARKERS. `ask_once` returns SILENTLY on one, so an
    early raise that only looked for `.answered-` would put a settled question back on
    the board — on exactly the old episodes least able to absorb it. The early raise
    must be blind in the same places the gate is."""
    with tempfile.TemporaryDirectory() as td:
        legacy = Path(td) / "thumbnail"
        legacy.mkdir()
        (legacy / ".placement-reviewed").write_text("answered under the old scheme")
        ctx = FakeCtx(td)

        def go(fake):
            engine._raise_early_ask(ctx, "thumbnail")
            return fake

        fake = _with_fake_rail(go)
        assert not fake.flagged, (
            "a question answered under the pre-C3 scheme was put back on the board")
        assert not (legacy / ".asked-placement-reviewed").exists()


case("🔴 a pre-C3 legacy answer is honoured — an old episode is not re-asked",
     _a_legacy_answer_is_honoured)


# ── 3. 🔴 THE DOUBLE-ASK TRAP ─────────────────────────────────────────────────
def _an_answer_given_during_assembly_is_taken():
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td)
        _with_fake_rail(lambda f: engine._raise_early_ask(ctx, "thumbnail"))
        ctx.ep["needs_look"] = False                  # Jodie cleared it during assembly

        took = engine._take_early_answer(ctx, "thumbnail")
        assert took is True, "the answer given during assembly was not taken"
        answered = Path(td) / "thumbnail" / ".answered-placement-reviewed"
        assert answered.is_file(), (
            "the ask was not promoted to .answered-, so ask_once at the step would "
            "raise the SAME question again — Jodie answers twice per episode.")
        # and the real gate now returns silently, which is the whole point
        providers.thumbnail_placement_review(Path(td), Path(td) / "t.png", None)


case("🔴 answered during assembly → promoted, and the step's gate then asks NOTHING",
     _an_answer_given_during_assembly_is_taken)


def _an_unanswered_ask_is_never_promoted():
    """🔴 THE DANGEROUS DIRECTION. Promoting without checking needs_look would mark a
    human gate answered that nobody answered, and walk it through in silence."""
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td)
        _with_fake_rail(lambda f: engine._raise_early_ask(ctx, "thumbnail"))
        ctx.ep["needs_look"] = True                   # still flagged — nobody answered

        took = engine._take_early_answer(ctx, "thumbnail")
        assert took is False, "an UNANSWERED gate was reported as answered"
        assert not (Path(td) / "thumbnail" / ".answered-placement-reviewed").exists(), (
            "an unanswered ask was promoted to .answered-. The build would sail past a "
            "human gate nobody has answered — EP23's fault, one layer up.")


case("🔴 CONTROL — an ask still flagged is NEVER promoted (the gate still stops)",
     _an_unanswered_ask_is_never_promoted)


def _no_early_ask_means_no_promotion():
    """Belt and braces: with no early ask recorded there is nothing to take, whatever
    the board says. A cleared flag from some OTHER gate must not answer this one."""
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td)
        assert engine._take_early_answer(ctx, "thumbnail") is False


case("a flag cleared for something else does not answer an ask we never raised",
     _no_early_ask_means_no_promotion)


# ── 4. WHERE IT IS WIRED ──────────────────────────────────────────────────────
def _the_seam_is_after_a_step_not_inside_one():
    body = ast.get_source_segment(SRC, _fn("_run_phase_steps")) or ""
    assert "_raise_early_ask" in body, "no seam raises the early ask at all"
    assert body.index("run_step(ctx, name)") < body.index("_raise_early_ask"), (
        "the early ask is raised BEFORE the step runs. The main thread is inside a "
        "blocking subprocess during a step; the seam is after it returns.")


case("the raise sits at a seam AFTER a step returns, on the main thread",
     _the_seam_is_after_a_step_not_inside_one)


def _the_step_still_waits_where_it_always_did():
    body = ast.get_source_segment(SRC, _fn("step_thumbnail")) or ""
    assert "_take_early_answer" in body, "step_thumbnail never takes the early answer"
    assert body.index("_take_early_answer") < body.index(
        "thumbnail_placement_review_for"), (
        "the early answer is taken AFTER the gate is called, which is too late — the "
        "gate would already have raised and the build already stopped.")
    assert "thumbnail_placement_review_for" in body, (
        "step_thumbnail no longer raises the placement review. The WAIT must stay "
        "exactly where it was; only the RAISING moved.")


case("the WAIT stays in step_thumbnail — only the raising moved",
     _the_step_still_waits_where_it_always_did)


PROV_SRC = (HERE / "providers.py").read_text(encoding="utf-8")
PROV_TREE = ast.parse(PROV_SRC)


def _the_message_has_one_source():
    assert hasattr(providers, "thumbnail_placement_message"), (
        "the ask's words are not in a shared function, so the early ask and the step "
        "ask can drift and the board changes its wording mid-build for no reason.")
    for fname in ("thumbnail_placement_review", "early_ask_message"):
        nodes = [n for n in ast.walk(PROV_TREE)
                 if isinstance(n, ast.FunctionDef) and n.name == fname]
        assert nodes, f"{fname} is not in providers.py"
        # early_ask_message exists on both providers; the REAL one must use the shared
        # words. The mock's returns None and has no message of its own.
        assert any("thumbnail_placement_message" in (ast.get_source_segment(PROV_SRC, n) or "")
                   for n in nodes), f"{fname} builds its own copy of the message text"
case("the ask's words come from ONE function, so early and late cannot drift",
     _the_message_has_one_source)


def _the_board_gets_a_picture_with_the_early_flag():
    """🔴 EP31, 19 Aug 2026. The early ask fired correctly at the assemble seam and the
    board had NO PICTURE to show: `_raise_early_ask` wrote the marker, the flag and the
    message but never the preview url — that line lived only in `step_thumbnail`, which
    did not run for another THIRTEEN MINUTES. Jodie had to click a link out of the
    message text. It worked, and it is not what the feature promised.

    The url must be in state BEFORE the flag — `saved BEFORE the flag, or it is lost`,
    the rule `step_thumbnail` already states one line above its own flag."""
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td)
        _with_fake_rail(lambda f: engine._raise_early_ask(ctx, "thumbnail"))
        got = ctx.state.get("thumbnail_preview_url")
        assert got == "https://example.invalid/thumb-preview.png", (
            f"the board has no picture for the early flag: {got!r}. The url is "
            f"published by early_ask_message and must be written into state before "
            f"the flag goes up.")


case("🔴 the early flag leaves the board able to SHOW the picture",
     _the_board_gets_a_picture_with_the_early_flag)


def _no_preview_url_still_asks():
    """A missing preview must never stop the ask — a flag with no picture beats no flag."""
    with tempfile.TemporaryDirectory() as td:
        ctx = FakeCtx(td, preview=None)

        def go(fake):
            engine._raise_early_ask(ctx, "thumbnail")
            return fake

        fake = _with_fake_rail(go)
        assert fake.flagged, "the ask was skipped just because there was no preview url"
        assert "thumbnail_preview_url" not in ctx.state


case("a missing preview url still raises the ask", _no_preview_url_still_asks)


print(f"\nearly ask: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
