#!/usr/bin/env python3
"""A1 — the title card, proved by the bad build it refuses and by the PIXELS it makes.

B1: a checker is proved by the bad build it refused. And the lesson that keeps
recurring — the change must reach the ARTEFACT, not just the instrument. So the
central proof here is not "the file was written": it is EP13's title card DELETED,
re-authored from episode.json alone, RENDERED, and compared pixel-for-pixel with
the hand-made page that shipped.

Needs a network (Anton comes from Google Fonts, exactly as every card render does)
and a Chromium. It touches no live rail, no engine and no published artefact — the
real EP13 folder is only ever READ.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude/skills/pp-episode-production"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SKILL / "scripts"))
import providers                                                    # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                               # noqa: BLE001
        pass

def episode_dir(n):
    """Resolve an episode folder by NUMBER, never by exact name.

    ⚠️ The stage-8 close-out RENAMES every published episode's folder
    (PP-EP13 -> PP-EP13-The-Ratings-Game-Part-1). A test that hard-codes the bare name
    is a test with a fuse in it: it passes until the process does the thing the
    standard requires of it. Three suites broke this way at once on 3 Aug.
    """
    pp = Path(r"G:\My Drive\PP Videos")
    hits = sorted(p for p in pp.glob(f"PP-EP{n}*") if p.is_dir())
    if not hits:
        raise AssertionError(f"no PP-EP{n}* folder under {pp}")
    return hits[0]


EP13 = episode_dir(13)
SHIPPED = EP13 / "overlay/export/ep13-title.html"
PASS, FAIL = [], []
# Where the PNGs land for a human to look at. ON DRIVE, not in the repo: code in
# GitHub, media on Drive (CLAUDE.md, 28 Jul 2026), and _review is the folder Jodie
# already opens for things that want her eye.
ART = Path(r"G:\My Drive\PP Videos\_review\A1-title-card")


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def ep13_episode_json():
    p = EP13 / "docs/episode.json"
    if not p.is_file():
        raise AssertionError("EP13 is not available to test against")
    return json.loads(p.read_text(encoding="utf-8"))


def scratch(epj=None):
    """An episode folder holding ONLY what episode.json needs — and no title page.

    This is the deletion Jodie asked for, made repeatable: there is no title card
    here and no human to make one.
    """
    d = Path(tempfile.mkdtemp(prefix="titlecard_"))
    for sub in ("docs", "overlay/export", "overlay/clips", "ebook/cover-src"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "docs/episode.json").write_text(
        json.dumps(epj if epj is not None else ep13_episode_json(), ensure_ascii=False),
        encoding="utf-8")
    hero = EP13 / "ebook/cover-src/hero.png"
    if hero.is_file():
        shutil.copyfile(hero, d / "ebook/cover-src/hero.png")
    return d


def build_page(d):
    """Everything the engine does, in the engine's own order, with no human step."""
    providers.stage_card_furniture(d / "overlay/export")
    providers.stage_title_hero(d)
    providers.author_missing_title(d)
    hits = sorted((d / "overlay/export").glob("*title*.html"))
    assert len(hits) == 1, f"expected exactly one title page, got {[h.name for h in hits]}"
    return hits[0]


# ------------------------------------------------------------------ 1 ------
# EP13's page DELETED, and the engine builds an equivalent from episode.json alone.
def _authors_from_nothing():
    d = scratch()
    page = build_page(d)
    src = page.read_text(encoding="utf-8")
    epj = ep13_episode_json()
    assert providers.stage_title_hero.__doc__            # (staging is part of the step)
    assert (d / "overlay/export/title-hero.png").is_file(), \
        "no title-hero.png was staged — a human would still have to copy the photograph"
    for want in (epj["cover"]["title_setup"], epj["cover"]["title_payoff"],
                 epj["cover"]["part"], epj["packaging"]["byline"]):
        assert want in src, f"{want!r} did not reach the authored page"
    assert "PP-GENERATED" in src, "the page carries no generated marker, so nothing " \
                                  "downstream can tell it apart from a hand-made one"


case("A1: with NO title page and no human, one is authored from episode.json",
     _authors_from_nothing)


# ------------------------------------------------------------------ 2 ------
def _never_overwrites_hand_authored():
    """The real EP13 page is hand-made and must survive the engine untouched."""
    assert SHIPPED.is_file(), "EP13's shipped title page is not on disk"
    before = SHIPPED.read_bytes()
    d = scratch()
    shutil.copyfile(SHIPPED, d / "overlay/export/ep13-title.html")
    providers.author_missing_title(d)
    assert (d / "overlay/export/ep13-title.html").read_bytes() == before, (
        "a HAND-AUTHORED title page was overwritten — that is the engine overruling a "
        "human who built the page on purpose")
    assert SHIPPED.read_bytes() == before, "the real EP13 page was modified by a test"


case("A1: a hand-authored title page is never overwritten", _never_overwrites_hand_authored)


# ------------------------------------------------------------------ 3 ------
# THE ARTEFACT, NOT THE MARKUP. Render both and compare the pixels.
def _pixels_match_the_shipped_card():
    import numpy as np
    from PIL import Image
    d = scratch()
    page = build_page(d)
    mine = d / "authored.png"
    theirs = d / "shipped.png"

    # the hand-made page, rendered in the same folder so it draws the same
    # photograph, the same logo and the same script
    hand = d / "overlay/export/hand-ep13-title.html"
    shutil.copyfile(SHIPPED, hand)
    shot(page, mine)
    shot(hand, theirs)
    ART.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mine, ART / "ep13-title-AUTHORED.png")
    shutil.copyfile(theirs, ART / "ep13-title-HANDMADE.png")

    a = np.asarray(Image.open(mine).convert("RGB")).astype(int)
    b = np.asarray(Image.open(theirs).convert("RGB")).astype(int)
    assert a.shape == b.shape, f"different canvases: {a.shape} vs {b.shape}"
    diff = np.abs(a - b).max(axis=2)
    moved = int((diff > 12).sum())
    pct = 100.0 * moved / diff.size
    print(f"      pixels differing by more than 12/255: {moved:,} ({pct:.2f}% of frame); "
          f"worst channel delta {int(diff.max())}")
    Image.fromarray(((diff > 12) * 255).astype("uint8")).save(ART / "ep13-title-DIFF.png")
    # The authored card is NOT required to be byte-identical to the hand-made one —
    # the type size is measured rather than typed. It IS required to be the same
    # design: same furniture in the same places, differing only where the headline is.
    assert pct < 8.0, (
        f"the authored title card differs from the shipped one over {pct:.2f}% of the "
        f"frame — that is not a type-size difference, it is a different design. "
        f"Look at {ART / 'ep13-title-DIFF.png'}")


def shot(page: Path, out: Path):
    """Screenshot a card page with every animation run to its end state."""
    import functools
    import threading
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
    from urllib.parse import quote
    from playwright.sync_api import sync_playwright

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(page.parent)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/{quote(page.name)}"
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
                              args=["--force-color-profile=srgb", "--hide-scrollbars",
                                    "--force-device-scale-factor=1"])
        pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        pg.goto(url, wait_until="load")
        pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
        pg.wait_for_function(
            "Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)",
            timeout=60_000)
        pg.evaluate("() => { if (window.ppSeek && window.ppDuration) "
                    "window.ppSeek(window.ppDuration); }")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1920, "height": 1080})
        b.close()
    httpd.shutdown()


case("A1: the RENDERED card matches the shipped design (pixels, not markup)",
     _pixels_match_the_shipped_card)


# ------------------------------------------------------------------ 4 ------
def _type_size_is_measured_not_typed():
    """The size must come from the headline, not from a constant."""
    long_epj = ep13_episode_json()
    long_epj["cover"]["title_setup"] = "THE DRAW AND"
    long_epj["cover"]["title_payoff"] = "THE BIAS"
    long_epj["packaging"]["hook"] = "THE DRAW AND THE BIAS"
    short_epj = ep13_episode_json()
    short_epj["cover"]["title_setup"] = "HIDDEN"
    short_epj["cover"]["title_payoff"] = "ACES"
    short_epj["packaging"]["hook"] = "HIDDEN ACES"

    sizes = {}
    for tag, epj in (("long", long_epj), ("short", short_epj)):
        d = scratch(epj)
        page = build_page(d)
        src = page.read_text(encoding="utf-8")
        import re
        m = re.search(r"\.t1\{[^}]*font-size:(\d+)px", src)
        assert m, f"no measured headline size in the {tag} page"
        sizes[tag] = int(m.group(1))
        pt = re.search(r"\.pt\{[^}]*font-size:([\d.]+)px", src)
        assert pt and abs(float(pt.group(1)) - sizes[tag] / 2) < 0.01, \
            f"the part line is not half the headline on the {tag} page"
    print(f"      measured: short headline {sizes['short']}px, "
          f"long headline {sizes['long']}px")
    assert sizes["long"] < sizes["short"], (
        "a much longer headline got the same or a bigger type size — the size is not "
        "being measured, it is a constant wearing a measurement's clothes")
    assert sizes["short"] == 170, (
        f"'HIDDEN ACES' measured {sizes['short']}px; EP11 and EP12 both shipped it at "
        f"170px, so the rule no longer reproduces the evidence it was fitted to")


case("A1: the type size is MEASURED from the headline, not a constant",
     _type_size_is_measured_not_typed)


def _reproduces_ep13s_hand_set_size():
    d = scratch()
    src = build_page(d).read_text(encoding="utf-8")
    import re
    got = int(re.search(r"\.t1\{[^}]*font-size:(\d+)px", src).group(1))
    assert got == 150, (
        f"EP13's headline was hand-set at 150px and the measured rule gives {got}px. "
        f"The rule was fitted to the three shipped cards; if it no longer reproduces "
        f"them, it is not measuring what a human measured.")


case("A1: the measured rule reproduces EP13's hand-set 150px",
     _reproduces_ep13s_hand_set_size)


def _a_headline_too_long_for_the_design_halts():
    """The floor is still a real halt — but it is now the SECOND thing tried, not the first.

    ⚠️ SUPERSEDED AND REWRITTEN, 9 Aug 2026. This case used to assert that a headline
    too long for one line halted the build, on the reasoning that "the words are longer
    than the design can hold, so it is a human choice between the words and the layout".
    EP19 put that to Jodie for real — "10 SYSTEMS FOR ACTION-HUNGRY PUNTERS", 1423px in
    a 1260px box — and she answered: KEEP THE WORDS, wrap to two lines, and stop
    halting builds over it. The old assertion was not wrong about the floor; it was
    wrong that one line was the only layout on offer.
        WHAT SURVIVES: shrinking below the floor is still forbidden, and a title that
        cannot fit even as two lines still stops and asks. That is what this now proves
        — both halves of it, through the real provider entry point.
    """
    long_ = ep13_episode_json()
    long_["cover"]["title_setup"] = "THE COMPLETE BEGINNERS"
    long_["cover"]["title_payoff"] = "GUIDE TO STAYING SOLVENT"
    long_["packaging"]["hook"] = "THE COMPLETE BEGINNERS GUIDE TO STAYING SOLVENT"
    d = scratch(long_)
    providers.stage_card_furniture(d / "overlay/export")
    providers.stage_title_hero(d)
    providers.author_missing_title(d)
    pages = list((d / "overlay/export").glob("*title*.html"))
    assert pages, ("a headline too long for ONE line halted the build. Jodie's 9 Aug "
                   "ruling is that it wraps and carries on.")
    assert "<br>" in pages[0].read_text(encoding="utf-8"), \
        "the page was written, but on one line — so it was shrunk or clipped, not wrapped"

    # …and the halt that must SURVIVE: two lines offered, neither can be made to fit.
    word = "SUPERCALIFRAGILISTICEXPIALIDOCIOUSNESSNESS"
    imposs = ep13_episode_json()
    imposs["cover"]["title_setup"] = word
    imposs["cover"]["title_payoff"] = word
    imposs["packaging"]["hook"] = f"{word} {word}"
    d2 = scratch(imposs)
    providers.stage_card_furniture(d2 / "overlay/export")
    providers.stage_title_hero(d2)
    try:
        providers.author_missing_title(d2)
        raise AssertionError(
            "a headline no layout can hold was authored anyway — auto-fit has stopped "
            "being a fit and started being a promise")
    except providers.EngineFlag as e:
        assert "Two lines have already been tried" in str(e), \
            f"the halt does not tell the human that wrapping was attempted:\n{str(e)[-300:]}"
    assert not list((d2 / "overlay/export").glob("*title*.html")), \
        "a page was written that cannot hold its own headline"


case("A1: a long headline WRAPS; only one no layout can hold is a real halt",
     _a_headline_too_long_for_the_design_halts)


# ------------------------------------------------------------------ 5 ------
# A missing field HALTS, loudly, naming the field.
def _missing_field_halts_naming_it():
    checks = [
        (("cover", "title_setup"), "cover.title_setup"),
        (("cover", "title_payoff"), "cover.title_payoff"),
        (("packaging", "byline"), "packaging.byline"),
    ]
    for (obj, key), phrase in checks:
        epj = ep13_episode_json()
        epj[obj].pop(key, None)
        d = scratch(epj)
        providers.stage_card_furniture(d / "overlay/export")
        providers.stage_title_hero(d)
        try:
            providers.author_missing_title(d)
            raise AssertionError(
                f"a missing {phrase} did NOT halt — the card would be authored with a "
                f"hole in it, or with a word nobody approved")
        except providers.EngineFlag as e:
            assert phrase in str(e), \
                f"the halt for a missing {phrase} does not name the field:\n{str(e)[-300:]}"
        assert not list((d / "overlay/export").glob("*title*.html")), \
            f"a page was written despite the missing {phrase}"


case("A1: a missing headline field or byline halts, naming the field",
     _missing_field_halts_naming_it)


def _part_disagreeing_with_the_ebook_halts():
    epj = ep13_episode_json()
    epj["cover"]["part"] = "Part 4"
    d = scratch(epj)
    providers.stage_card_furniture(d / "overlay/export")
    providers.stage_title_hero(d)
    try:
        providers.author_missing_title(d)
        raise AssertionError("the video and the e-book were allowed to put the episode "
                             "at different points in the series")
    except providers.EngineFlag as e:
        assert "cover.part" in str(e) and "ebook_title" in str(e), \
            f"unclear halt:\n{str(e)[-300:]}"


case("A1: a part line that contradicts the approved e-book title halts",
     _part_disagreeing_with_the_ebook_halts)


def _hook_drift_halts():
    epj = ep13_episode_json()
    epj["cover"]["title_payoff"] = "RACKET"
    d = scratch(epj)
    providers.stage_card_furniture(d / "overlay/export")
    providers.stage_title_hero(d)
    try:
        providers.author_missing_title(d)
        raise AssertionError("the title card was allowed to say words that were never "
                             "approved at the words gate")
    except providers.EngineFlag as e:
        assert "packaging.hook" in str(e), f"unclear halt:\n{str(e)[-300:]}"


case("A1: a headline that drifts from the approved hook halts", _hook_drift_halts)


def _no_part_is_omitted_not_left_empty():
    epj = ep13_episode_json()
    epj["cover"].pop("part", None)
    d = scratch(epj)
    src = build_page(d).read_text(encoding="utf-8")
    assert 'id="pt"' not in src, "a part-less episode still carries an empty part line"
    assert '"sel":"#pt"' not in src, (
        "the part line's animation is still there with no part line to animate — "
        "pp-anim would be seeking an element that does not exist")
    assert "%%" not in src, "unfilled slots left in the page"


case("A1: with no part, the line is omitted rather than left empty",
     _no_part_is_omitted_not_left_empty)


# ------------------------------------------------------------------ 6 ------
# The needs_look: raised WITH the PNG, and clearing it lets the build continue.
def _review_is_raised_with_the_png():
    d = scratch()
    png = d / "overlay/export/title-preview.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    try:
        providers.title_placement_review(d, png)
        raise AssertionError("no review flag was raised, so nobody is ever asked to look "
                             "at the one value that cannot be measured")
    except providers.EngineFlag as e:
        msg = str(e)
    assert str(png) in msg, (
        f"the flag does not carry the PNG, so it asks a human to judge a crop they "
        f"cannot see:\n{msg}")
    assert "hero_focus" in msg and "title_card" in msg, \
        f"the flag does not say what to change if they are unhappy:\n{msg}"
    assert "Clear this flag" in msg, f"the flag does not say what to do if happy:\n{msg}"
    # …and clearing it lets the build through, instead of re-raising forever.
    providers.title_placement_review(d, png)          # must NOT raise the second time


case("A1: the review flag carries the PNG, and clearing it lets the build continue",
     _review_is_raised_with_the_png)


def _preview_comes_from_the_clip_that_ships():
    """The PNG must be a frame of the RENDERED CLIP, not a re-render of the page."""
    d = scratch()
    clip = d / "overlay/clips/ep13-title.mp4"
    clip.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "color=c=#DA532C:s=1920x1080:d=3", "-frames:v", "75",
         "-pix_fmt", "yuv420p", str(clip)],
        capture_output=True, text=True)
    assert clip.is_file(), f"could not build a stand-in clip: {r.stderr[-300:]}"
    out = providers.title_preview(d, clip)
    assert out.is_file() and out.stat().st_size > 1000, "no preview frame was taken"
    from PIL import Image
    im = Image.open(out).convert("RGB")
    assert im.size == (1920, 1080), f"the preview is {im.size}, not the card canvas"
    r, g, b = im.getpixel((960, 540))
    assert abs(r - 0xDA) < 12 and abs(g - 0x53) < 12 and abs(b - 0x2C) < 12, (
        f"the preview frame ({r},{g},{b}) is not the clip's own pixels — it was not "
        f"taken from the video that ships")


case("A1: the preview frame is taken from the rendered clip, not re-rendered",
     _preview_comes_from_the_clip_that_ships)


# ------------------------------------------------------------------ 7 ------
def _wired_into_the_real_render_cards():
    """Assert the wiring in the REAL RealProvider.render_cards, not in MockProvider.

    NOTE ON HOW THIS IS WRITTEN. A grep-based guard is defeated by quoting the string
    it looks for in a comment — that happened twice yesterday, in this very file's
    predecessor. So this searches the SLICED body of the real method and looks for a
    CALL SHAPE, and the assertions below never quote a retired string.

    AND IT ALREADY EARNED ITS KEEP: MockProvider defines render_cards too, and BOTH
    bodies shell out to render_cards_batch.py, so filtering on that picked the mock
    and the first version of this test passed a real method it had never looked at.
    The mock is now sliced out by name and checked separately, below.
    """
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    mock_at = src.index("class MockProvider")
    real_at = src.index("class RealProvider")
    lo, hi = (real_at, mock_at) if real_at < mock_at else (real_at, len(src))
    region = src[lo:hi]
    bodies = [b.split("\n    def ", 1)[0] for b in region.split("def render_cards")[1:]]
    assert bodies, "could not find RealProvider.render_cards"
    body = bodies[0]
    for call in ("stage_title_hero(", "author_missing_title("):
        assert call in body, f"{call}) is not called from the real render_cards"
    assert body.index("author_missing_title(") < body.index("card_check.py"), \
        "the title card is authored AFTER the checker judges it"
    # THE REVIEW MOVED OUT OF HERE ON 3 AUG 2026 and that is deliberate: raised from
    # inside render_cards it interrupted the step, so the engine never got to record
    # WHERE the preview lives and the flag could only name a local path. It is now
    # raised by step_cards_render, which publishes and saves the URL first. That
    # ordering is proved BEHAVIOURALLY in test_bundle_a.py — driving the real step —
    # rather than by grepping for a call, because a grep can be satisfied by a comment.
    assert "title_placement_review(" not in body, \
        "the review is back inside render_cards, where its URL cannot be recorded"


case("A1: the whole step is wired into the real render_cards, in the right order",
     _wired_into_the_real_render_cards)


def _the_mock_authors_it_too():
    """`engine.py run --mock` must exercise this, or the safe rehearsal lies.

    MockProvider.render_cards is the one mock step that does REAL work, and its own
    docstring says why: it exists to prove that a clean folder with no card pages
    produces cards instead of a halt a browser operator cannot clear. TITLE was the
    last halt in exactly that class.
    """
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    region = src[src.index("class MockProvider"):]
    bodies = [b.split("\n    def ", 1)[0] for b in region.split("def render_cards")[1:]]
    assert bodies, "could not find MockProvider.render_cards"
    for call in ("stage_title_hero(", "author_missing_title("):
        assert call in bodies[0], \
            f"{call}) is missing from the mock, so --mock would not rehearse the title card"


case("A1: --mock rehearses the title card too", _the_mock_authors_it_too)


def _the_old_halt_can_no_longer_fire_for_TITLE():
    """The halt this whole job exists to remove, driven for real.

    Not a grep: build an episode folder with everything the engine has at that point
    and assert a title clip is now reachable where EP11, EP12 and EP13 all stopped.
    """
    d = scratch()
    page = build_page(d)
    subprocess.run(
        [sys.executable, str(SKILL / "scripts/render_cards_batch.py"),
         str(d / "overlay/export"), str(d / "overlay/clips")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    hits = [p for p in sorted((d / "overlay/clips").glob("*title*.mp4"))
            if "lowerthird" not in p.name]
    assert len(hits) == 1, (
        f"after authoring, `Card TITLE has no clip in overlay/clips` would STILL fire: "
        f"expected exactly one *title*.mp4, found {[h.name for h in hits]}. "
        f"(page: {page.name})")
    out = providers.title_preview(d, hits[0])
    ART.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out, ART / "ep13-title-CLIP-FRAME.png")


case("A1: the halt that stopped EP11, EP12 and EP13 can no longer fire",
     _the_old_halt_can_no_longer_fire_for_TITLE)


def _passes_the_gate_that_now_judges_it():
    """render_cards runs card_check over the WHOLE export dir, so the authored title
    card is now judged by it. A page the engine writes and its own gate then rejects
    would be a halt of our own making."""
    d = scratch()
    build_page(d)
    r = subprocess.run(
        [sys.executable, str(SKILL / "scripts/card_check.py"), str(d / "overlay/export")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    assert r.returncode == 0, (
        "the authored title card FAILS card_check — the engine would write a page and "
        f"then halt on it:\n{(r.stdout + r.stderr)[-800:]}")


case("A1: the authored title card passes card_check", _passes_the_gate_that_now_judges_it)


# ------------------------------------------------------------------ 2 ------
# A LONG TITLE WRAPS; IT DOES NOT HALT THE BUILD. (Jodie, 9 Aug 2026.)
#
# EP19 stopped at cards_render because "10 SYSTEMS FOR ACTION-HUNGRY PUNTERS" measured
# 1423px against a 1260px box even at the 90px floor. Her ruling: keep the words, wrap
# to two lines. These cases are CONTROL-FIRST — each one first drives the behaviour
# that used to halt, watches it halt, and only then asserts the fix.
LONG_SETUP, LONG_PAYOFF = "10 SYSTEMS FOR", "ACTION-HUNGRY PUNTERS"
LONG_HOOK = f"{LONG_SETUP} {LONG_PAYOFF}"


def long_title_epj():
    """EP13's episode, repackaged with EP19's over-long approved hook.

    EP13's own words are kept everywhere else, so the ONLY thing under test is length.
    """
    epj = ep13_episode_json()
    epj["cover"]["title_setup"] = LONG_SETUP
    epj["cover"]["title_payoff"] = LONG_PAYOFF
    epj["packaging"]["hook"] = LONG_HOOK
    return epj


def _one_line_still_cannot_hold_it():
    """THE CONTROL. Same measurement, same words, no second line offered: it must halt.

    Without this, the case below would prove only that measure_size returns a number —
    not that it returns one for a headline that genuinely does not fit on one line.
    """
    import author_title_card as atc
    try:
        atc.measure_size(LONG_HOOK)
    except atc.Halt as e:
        assert "1260px box" in str(e) or "wider than" in str(e), \
            f"it halted, but not about width — so the control proves nothing:\n{e}"
        return
    raise AssertionError(
        f"{LONG_HOOK!r} was reported to FIT on one line. It measured 1423px against a "
        f"1260px box on EP19, so either the box grew or the measurement is broken — "
        f"and every 'it wraps' case below would then be passing on a false premise.")


case("A1: CONTROL — the over-long hook still does not fit on one line",
     _one_line_still_cannot_hold_it)


def _it_wraps_instead_of_halting():
    import author_title_card as atc
    size, width, two_line = atc.measure_size(
        LONG_HOOK, lines=[LONG_SETUP, LONG_PAYOFF])
    assert two_line, "it fitted on one line, which the control just disproved"
    assert size >= atc.FLOOR, \
        f"it wrapped but sized to {size}px, below the {atc.FLOOR}px floor"
    assert width * size / 100.0 <= atc.BOX + 1, (
        f"the longer half is {width * size / 100.0:.0f}px at {size}px, wider than the "
        f"{atc.BOX:.0f}px box — the wrap did not actually make it fit")


case("A1: over-long hook WRAPS to two lines instead of halting",
     _it_wraps_instead_of_halting)


def _an_impossible_title_still_halts():
    """The halt is MOVED, not removed.

    A single unbreakable word cannot be helped by a second line, and quietly shrinking
    it below the floor or clipping it would be worse than stopping. One unhelpable word
    is a real human decision, and it must still reach a human.
    """
    import author_title_card as atc
    word = "SUPERCALIFRAGILISTICEXPIALIDOCIOUSNESSNESS"
    try:
        atc.measure_size(f"{word} {word}", lines=[word, word])
    except atc.Halt as e:
        assert "Two lines have already been tried" in str(e), (
            f"it halted, but the message does not tell a human that wrapping was "
            f"attempted, so they cannot tell a fixable title from an unfixable one:\n{e}")
        return
    raise AssertionError(
        f"a {len(word)}-character unbreakable word was reported to fit. Auto-fit has "
        f"stopped being a fit and started being a promise.")


case("A1: a title no layout can hold STILL halts", _an_impossible_title_still_halts)


def _the_wrapped_page_really_fits_when_rendered():
    """The PAGE, measured where a viewer sees it — not the calculation that made it.

    ⚠️ card_check CANNOT JUDGE THIS, and the first version of this test found that out
    the useful way: it ran the un-wrapped page past card_check as a control and
    card_check PASSED it. The title card's own header comment claims `white-space:nowrap`
    is a safety net — "a headline that still overruns cannot wrap quietly, it overflows
    .card (which clips) and card_check hard-fails". It does not. `.inner` is a 1260px
    column inside a 1920px card at left:110, so a 1739px headline overruns the COLUMN
    while sitting comfortably inside the CARD. Nothing clips and nothing fails.
        So the real net is the measurement plus this test, and the comment has been
        corrected rather than left to be believed. (Reported to Jodie, 9 Aug 2026.)

    CONTROL FIRST, in the same browser and the same loaded Anton: the page as it was
    authored before today — nowrap, no break — must be measured as OVERRUNNING. Only
    then does the wrapped page's fit mean anything.
    """
    from playwright.sync_api import sync_playwright

    d = scratch(long_title_epj())
    page = build_page(d)
    html = page.read_text(encoding="utf-8")
    assert "<br>" in html and "white-space:normal" in html, (
        "the authored page has no line break in it, so nothing below is testing the "
        "two-line path at all")

    # Visual lines, NOT element rects: getClientRects() returns one rect per element and
    # text fragment, so the span, its text, the <br> and the tail read as four "lines".
    # Grouping by y-position is what a reader actually sees.
    measure = """() => {
      const t = document.getElementById('t1');
      const inner = document.querySelector('.inner');
      const r = new Range(); r.selectNodeContents(t);
      const rects = [...r.getClientRects()].filter(x => x.width > 0.5);
      const rows = new Map();
      for (const x of rects) {
        const k = Math.round(x.top / 8);
        const c = rows.get(k) || {l: Infinity, r: -Infinity};
        rows.set(k, {l: Math.min(c.l, x.left), r: Math.max(c.r, x.right)});
      }
      const ir = inner.getBoundingClientRect();
      return {
        lines: rows.size,
        widths: [...rows.values()].map(v => Math.round(v.r - v.l)),
        overrun: Math.round(Math.max(...rects.map(x => x.right)) - ir.right),
        top: Math.round(document.querySelector('.eyebrow').getBoundingClientRect().top),
        bottom: Math.round(document.getElementById('byl').getBoundingClientRect().bottom),
      };
    }"""

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, args=["--hide-scrollbars"])
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        try:
            pg.goto(page.as_uri() + "?print")
            pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
            pg.wait_for_timeout(500)
            good = pg.evaluate(measure)
            ART.mkdir(parents=True, exist_ok=True)
            pg.screenshot(path=str(ART / "long-title-WRAPPED.png"))
            # …now put the page back the way it was authored yesterday and re-measure.
            pg.evaluate("""() => {
              const t = document.getElementById('t1');
              t.style.whiteSpace = 'nowrap';
              t.innerHTML = t.innerHTML.replace('<br>', ' ');
            }""")
            pg.wait_for_timeout(150)
            bad = pg.evaluate(measure)
        finally:
            b.close()

    assert bad["overrun"] > 0, (
        f"CONTROL FAILED: on one line the headline overran its column by "
        f"{bad['overrun']}px — i.e. not at all. This measurement cannot tell a card "
        f"that fits from one that does not, so its verdict below is worthless.")
    assert good["lines"] == 2, \
        f"the wrapped page renders as {good['lines']} line(s), widths {good['widths']}"
    assert good["overrun"] <= 1, (
        f"the wrapped headline still overruns its {1260}px column by "
        f"{good['overrun']}px — widths {good['widths']}")
    assert good["top"] >= 0 and good["bottom"] <= 1080, (
        f"the second line pushed the block off the card: eyebrow top {good['top']}px, "
        f"byline bottom {good['bottom']}px of 1080px")
    print(f"      control overran by {bad['overrun']}px; wrapped renders "
          f"{good['widths']} inside 1260px, block {good['top']}–{good['bottom']}px")


case("A1: the wrapped page RENDERS as two lines inside its column",
     _the_wrapped_page_really_fits_when_rendered)


print(f"\ntitle card: {len(PASS)} passed, {len(FAIL)} failed")
if not FAIL:
    print(f"PNGs for a human to look at: {ART}")
sys.exit(1 if FAIL else 0)
