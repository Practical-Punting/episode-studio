#!/usr/bin/env python3
"""BUNDLE A — the ceiling, the midroll chip, the title-card preview.

B1: every check below is written to FAIL on the unfixed engine, and the failure is
the evidence. NOTHING here reads this repo's own source — each one drives a real
function and asserts what it DOES, because a check that greps for a string can be
satisfied by a comment, and this project has been bitten by that twice.

No network, no live rail, no live episode.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine                                                       # noqa: E402
import providers                                                    # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                               # noqa: BLE001
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


# ================================================================= the ceiling
# MEASURED FROM EP14's OWN RAIL ROW: clip_cost 7.5, covers 4.0, 7 clips = 56.5.
# EP13 ran 6 clips, EP14 ran 7. The old ceiling of 60 leaves 3.5 credits of
# headroom — less than half a clip — so the NEXT episode with 8 clips halts before
# spending anything, and the flag says "raise ENGINE_CREDIT_CEILING", which is an
# environment variable Hugh cannot set from a browser.
CLIP_COST, COVER_COST = 7.5, 4.0


class FakeProv:
    """Just enough provider for step_credit_check. No network, no CLI."""
    def __init__(self, n_clips, balance=131.72):
        self.n = n_clips
        self._balance = balance

    def broll_plan(self, ep):
        return [f"broll-{i}" for i in range(self.n)]

    def broll_staged(self, ep, c):
        return False

    def cover_cost(self, ep):
        return COVER_COST

    def clip_cost(self, ep):
        return CLIP_COST

    def balance(self, *a, **k):
        return self._balance


class FakeCtx:
    def __init__(self, n_clips, balance=131.72):
        self.provider = FakeProv(n_clips, balance)
        self.ep = {"id": "x", "ep_number": 15}
        self.state = {}

    def check_alive(self):
        pass

    def save(self):
        pass


def estimate_for(n):
    return n * CLIP_COST + COVER_COST


def _eight_clips_must_not_halt():
    n = 8
    est = estimate_for(n)
    assert est == 64.0, f"arithmetic drifted: {n} clips = {est}"
    try:
        meta = engine.step_credit_check(FakeCtx(n))
    except engine.EngineFlag as f:
        raise AssertionError(
            f"EIGHT b-roll clips ({est} credits) HALTS at the ceiling of "
            f"{engine.CREDIT_CEILING:.0f}. EP13 ran 6, EP14 ran 7 — 8 is the next "
            f"step up and it stops the build before a credit is spent, asking for an "
            f"ENVIRONMENT VARIABLE Hugh cannot set.\n      flag: {f}")
    assert meta["estimate"] == est, f"estimate wrong: {meta['estimate']}"


case("ceiling: 8 b-roll clips (64 credits) does NOT halt", _eight_clips_must_not_halt)


def _nine_clips_must_still_halt():
    """The ceiling is a BUDGET guard too, not only a nuisance guard."""
    n, est = 9, estimate_for(9)
    assert est == 71.5, f"arithmetic drifted: {est}"
    try:
        engine.step_credit_check(FakeCtx(n))
        raise AssertionError(
            f"NINE clips ({est} credits) sailed through. With the balance this low "
            f"that is over half of what is left on one episode — it SHOULD halt.")
    except engine.EngineFlag as f:
        assert "ceiling" in str(f).lower(), f"halted for the wrong reason: {f}"


case("ceiling: 9 clips (71.5) still halts — it is a budget guard, not just a nuisance",
     _nine_clips_must_still_halt)


def _a_thin_balance_still_stops_the_spend():
    try:
        engine.step_credit_check(FakeCtx(8, balance=20.0))
        raise AssertionError("spent past the balance")
    except engine.EngineFlag as f:
        assert "available" in str(f) or "Top up" in str(f), f"wrong halt: {f}"


case("ceiling: a balance below the estimate still stops the spend",
     _a_thin_balance_still_stops_the_spend)


def _the_balance_is_recorded_for_the_board():
    """Hugh cannot run a CLI, so the number has to reach the page."""
    meta = engine.step_credit_check(FakeCtx(7))
    assert "balance" in meta, (
        "step_credit_check does not report the balance, so nothing downstream can "
        "put it on the board and the runway stays invisible until it runs out")
    assert meta["balance"] == 131.72, f"balance not carried through: {meta}"


case("ceiling: the balance reaches build_state so the board can show it",
     _the_balance_is_recorded_for_the_board)


# ============================================================ the midroll chip
def _the_chip_page_is_standing_furniture():
    d = Path(tempfile.mkdtemp(prefix="furniture_"))
    added = providers.stage_card_furniture(d)
    page = d / "midroll-lowerthird.html"
    assert page.is_file(), (
        "stage_card_furniture did NOT stage the midroll chip page. It stages the "
        "warranty slide and the end card — identical every episode — and the chip is "
        "the same kind of thing, so EP14 halted at pass B on a file nobody renders. "
        f"staged: {added}")
    src = (HERE.parent / ".claude/skills/pp-episode-production/assets/"
           "midroll-lowerthird.html")
    assert page.read_bytes() == src.read_bytes(), \
        "the staged chip is not byte-identical to the standing asset"


case("chip: the midroll page is staged as standing furniture",
     _the_chip_page_is_standing_furniture)


def _staging_never_overwrites_a_hand_fixed_chip():
    d = Path(tempfile.mkdtemp(prefix="furniture2_"))
    (d / "midroll-lowerthird.html").write_bytes(b"HAND-FIXED")
    providers.stage_card_furniture(d)
    assert (d / "midroll-lowerthird.html").read_bytes() == b"HAND-FIXED", \
        "staging overwrote a hand-fixed chip page"


case("chip: an existing chip page is never overwritten",
     _staging_never_overwrites_a_hand_fixed_chip)


# ====================================================== the title-card preview
def _the_preview_is_published_and_recorded():
    """Hugh cannot open G:\\ — the picture has to become a URL on the page."""
    assert hasattr(providers.RealProvider, "publish_title_preview"), (
        "there is no way to turn the title-card preview into something a browser can "
        "show. The flag carries a Windows path (G:\\...\\title-preview.png), which is "
        "not a thing Hugh can open — so the ONE clearable flag in the build is "
        "clearable only by someone sitting at this machine.")


case("preview: the provider can publish the title preview to a public URL",
     _the_preview_is_published_and_recorded)


def _the_review_flag_carries_the_url_not_a_windows_path():
    d = Path(tempfile.mkdtemp(prefix="review_"))
    (d / "overlay/export").mkdir(parents=True)
    png = d / "overlay/export/title-preview.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    url = "https://example.supabase.co/storage/v1/object/public/x/title-preview.png"
    msg = None
    try:
        providers.title_placement_review(d, png, url)
    except providers.EngineFlag as e:
        msg = str(e)
    except TypeError as e:
        raise AssertionError(
            f"title_placement_review cannot even be TOLD the URL: {e}. The flag can "
            f"only carry a Windows path, which Hugh cannot open.")
    assert msg, "no flag was raised"
    assert url in msg, (
        "the flag does not carry the public URL, so the board has nothing to show "
        f"and Hugh sees a path he cannot open:\n{msg}")


case("preview: the review flag carries the public URL",
     _the_review_flag_carries_the_url_not_a_windows_path)


def _the_url_is_saved_BEFORE_the_flag_is_raised():
    """The ordering IS the fix, so it is proved by driving the real step.

    A flag raised before the save means the URL is lost and the board has nothing to
    render — which is precisely why the review could not live inside render_cards.
    """
    order = []

    class P:
        def render_cards(self, ep):
            order.append("render")
            return ["a.mp4"]

        def publish_title_preview(self, ep):
            order.append("publish")
            return "https://example.test/title-preview.png"

        def title_placement_review_for(self, ep, url=None):
            order.append("review")
            assert url, "the review was raised without the URL"
            raise providers.EngineFlag(f"Have a look at the title card: {url}")

    class C:
        provider = P()
        ep = {"id": "x", "ep_number": 15}
        state = {}

        def save(self):
            order.append("save")

    ctx = C()
    try:
        engine.step_cards_render(ctx)
        raise AssertionError("the review flag was never raised")
    except providers.EngineFlag as f:
        assert "https://example.test/title-preview.png" in str(f), f"no URL in the flag: {f}"
    assert ctx.state.get("title_preview_url"), \
        "the preview URL is not in build_state, so the board cannot show the picture"
    assert order == ["render", "publish", "save", "review"], (
        f"wrong order: {order}. The URL must be published AND SAVED before the flag "
        f"interrupts the step, or it is lost.")


case("preview: the URL is published and SAVED to build_state before the flag",
     _the_url_is_saved_BEFORE_the_flag_is_raised)


print(f"\nbundle A: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
