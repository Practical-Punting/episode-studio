#!/usr/bin/env python3
"""autofit, proved by the cards it USED to wave through.

    python test_autofit_cards.py

WHY THIS SUITE EXISTS AT ALL
----------------------------
autofit had no tests, and it spent three episodes reporting success on pages the very
next gate rejected. EP16's run log wrote the diagnosis down in August:

    "offenders() tests two things — text under the logo chip, text clipped inside a
     scroll box. card_check reports a third: an element whose own box extends outside
     the card. Measured: card_check failed C8/C10 while autofit said '2 examined,
     0 fitted, 0 still failing' on the same pages. And the halt then blames the
     WORDS — 'a choice between the words and the layout' — when nothing ever tried
     to shrink it."

It stayed unfixed until EP19 halted on three cards at once. A written-down finding
that nothing enforces recurs; that is the whole argument for this file existing.

CONTROL-FIRST, THROUGHOUT. Every case here builds a DELIBERATELY OVER-LONG card from
the real templates, renders it, and first asserts it is genuinely broken — that the
gate rejects it — before asserting autofit repairs it. A fitter tested only on things
that already fit proves nothing at all.

It uses the REAL blocks and the REAL frames, never a copy, so a template whose leading
or box changes is tested as it now is rather than as it was when this was written.
Needs Chromium and a network (Anton comes from Google Fonts, as every card render does).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import author_cards as ac                                        # noqa: E402
import autofit_cards as af                                       # noqa: E402
import card_check as cc                                          # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
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
    except Exception as e:                                       # noqa: BLE001
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"  !!  {name}\n      {type(e).__name__}: {e}")


# --------------------------------------------------------------- fixtures --
# EP19's three real casualties, COPIED FIELD FOR FIELD from its episode.json. The
# values are the episode's own — a staking figure written in words, a price range, and
# day-pair bar labels — because inventing a long string would be inventing the fault too.
#
# ⚠️ `layout` AND THE `<br>` IN headline_display ARE PART OF THE FAULT, not decoration.
# The first draft of this file used layout "panel" and a headline with no break, and all
# three fixtures PASSED card_check — a suite full of green ticks testing cards that were
# never broken. panel-push is a different frame, and a two-line headline pushes the
# block down by a whole line. Copy the card, not the gist of it.
CARDS = {
    # A 300px figure that wraps and shoves the caption and payoff off the card.
    "stat": {
        "id": "C7", "block": "stat", "layout": "panel-push", "job": "anchor",
        "eyebrow": "Seven · What It Pays",
        "headline_display": "Two Winners<br>and You're Up",
        "content": {"figure": "Three to Seven", "figure_sub": "units of profit on the week",
                    "payoff": "If just two horses win.", "note": None},
        "trace": {"figure": "three to seven units of profit on the week"},
    },
    # A 360px price at 0.84 leading: two lines drawn straight through each other.
    "price": {
        "id": "C8", "block": "price", "layout": "panel-push", "job": "anchor",
        "eyebrow": "Eight · The Bookie Basher",
        "headline_display": "The Price<br>Window",
        "content": {"price": "$1.75 to $3.25", "said": "the pre-post favourite, in tote terms",
                    "quote": "The second-favourite must be at least 4/1 ($5)."},
        "trace": {"price": "between $1.75 and $3.25 in tote terms"},
    },
    # A figure too WIDE for the card and with nothing in it to break on. This one is
    # here because of what the control taught: disabling rule 3 left every other case
    # green, since a bottom overrun is caught by the biggest-type rule instead. Sideways
    # is the overflow only rule 3 sees, so without this the rule has no test at all.
    "wide": {
        "id": "C9", "block": "stat", "layout": "panel-push", "job": "anchor",
        "eyebrow": "Nine · The Whole Pool", "headline_display": "What The Pool<br>Paid Out",
        "content": {"figure": "$1,750,000,000", "figure_sub": "through the tote",
                    "payoff": "In a single season.", "note": None},
        "trace": {"figure": "$1,750,000,000 through the tote in a single season"},
    },
    # Bar labels that wrap to three lines each, pushing the ask clean off the bottom.
    "bars": {
        "id": "C6", "block": "bars", "layout": "fullscreen", "job": "anchor",
        "eyebrow": "Six · The Shape of the Week",
        "headline_display": "The Stakes<br>Come Down",
        "content": {"bars": [
            {"label": "Monday and Tuesday", "value": "3", "note": "2/1 shots", "tone": "hi"},
            {"label": "Wednesday and Thursday", "value": "1.5", "note": "4/1 shots", "tone": ""},
            {"label": "Friday and Saturday", "value": "1", "note": "6/1 shots", "tone": ""}],
            "ask": "Units staked on each bet, Monday to Saturday.", "chip": None},
        "trace": {"bars.1.value": "three units on monday and tuesday"},
    },
}


def build(*names):
    """An export folder holding the named cards and the furniture they need."""
    d = tempfile.mkdtemp(prefix="autofit_")
    ac_providers_stage(d)
    for n in names:
        card = CARDS[n]
        blk = ac.load_block(card["block"])
        page = ac.render_card(card, blk, ac.load_frame(card["layout"]))
        with open(os.path.join(d, f"{card['id'].lower()}-{n}.html"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(page)
    return d


def ac_providers_stage(d):
    """The fonts, the logo and pp-anim.js — staged by the engine's own routine, so a
    test card is furnished exactly the way a real one is."""
    import pathlib
    sys.path.insert(0, os.path.join(HERE, "../../../../engine"))
    import providers                                             # noqa: E402
    providers.stage_card_furniture(pathlib.Path(d))


def check(d):
    """card_check's verdict on a folder, as the build itself would get it."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "card_check.py"), d],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    return r.returncode, (r.stdout + r.stderr)


def autofit(d):
    r = subprocess.run([sys.executable, os.path.join(HERE, "autofit_cards.py"), d],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800)
    return r.returncode, (r.stdout + r.stderr)


# ------------------------------------------------------------------- 1 -----
def _the_selector_is_not_mangled():
    """The three-character bug that made every other fix pointless.

    card_check's PROBE is a RAW python string, so `/\\s+/` reached the browser doubled,
    name() never split, and an owner came back as "blabel anton". selector_for() then
    stripped the SPACE rather than the second class and emitted `.blabelanton` — which
    matches nothing. autofit could write CSS all day and never move a pixel.
    """
    got = af.selector_for("blabel anton")
    assert got == "#blabel, .blabel", (
        f"selector_for('blabel anton') = {got!r}. If this is '.blabelanton' the fitter "
        f"is writing rules that match no element, and every 'cannot be fitted' verdict "
        f"it gives is a lie.")


case("a multi-class owner still yields a selector that matches",
     _the_selector_is_not_mangled)


def _card_check_names_one_class():
    """And the root cause, fixed where it belongs rather than only worked around."""
    i = cc.PROBE.find("split(")
    frag = cc.PROBE[i:i + 14]
    assert "\\\\s" not in frag, (
        f"card_check's PROBE still ships {frag!r} to the browser. In a raw string the "
        f"doubled backslash is literal, so this regex matches a backslash followed by "
        f"'s' and className is never split.")


case("card_check's own name() splits on real whitespace", _card_check_names_one_class)


# ------------------------------------------------------------------- 2 -----
def _sees_text_outside_the_card():
    """EP16's finding, made into a gate.

    CONTROL: card_check must reject this page first. If it does not, the page is not
    broken and nothing below means anything.
    """
    d = build("stat")
    rc, out = check(d)
    assert rc != 0 and "CLIPPED" in out, (
        "CONTROL FAILED: card_check PASSED a card whose caption and payoff are pushed "
        f"off the bottom. Nothing here is testing a repair.\n{out[-500:]}")

    rc2, out2 = autofit(d)
    assert "0 fitted" not in out2, (
        "autofit examined the page and fitted NOTHING — the exact words EP16 recorded: "
        f"'0 fitted, 0 still failing' on pages card_check had just failed.\n{out2[-600:]}")
    rc3, out3 = check(d)
    assert rc3 == 0, f"autofit ran but card_check still fails the page:\n{out3[-600:]}"
    shutil.rmtree(d, ignore_errors=True)


case("a run that extends outside the card is seen, and fitted",
     _sees_text_outside_the_card)


# ------------------------------------------------------------------- 3 -----
def _shrinks_the_culprit_not_the_bystanders():
    """The line that falls off the bottom is usually not the one at fault.

    EP19 C7: a 300px figure wrapped and shoved a 46px caption and a 66px payoff off the
    card. card_check names the caption and the payoff — the two innocent parties. Taking
    THEM to the 60% floor buys about 52px against a 267px overflow, so a fitter that
    believes the accusation grinds to the floor and then blames words that were never
    the problem.
    """
    d = build("stat")
    _rc, out = autofit(d)
    sizes = dict(re.findall(r"(\w+): ([\d.]+)px -> [\d.]+px \((\d+)%", out) and
                 [(m[0], m[2]) for m in
                  re.findall(r"(\w+): ([\d.]+)px -> [\d.]+px \((\d+)%", out)])
    assert "big" in sizes, f"the figure was never touched:\n{out[-600:]}"
    assert int(sizes["big"]) < 100, \
        f"the figure kept its full size while the card overran: {sizes}"
    for innocent in ("sub", "pay"):
        if innocent in sizes:
            assert int(sizes[innocent]) == 100, (
                f"{innocent} was shrunk to {sizes[innocent]}% of its designed size. It "
                f"was pushed off the card by the figure above it; shrinking the figure "
                f"alone was enough, so the caption should still be at 100%.")
    shutil.rmtree(d, ignore_errors=True)


case("the biggest block type is shrunk, and the runs it pushed out are not",
     _shrinks_the_culprit_not_the_bystanders)


# ------------------------------------------------------------------- 4 -----
def _repairs_display_type_that_wraps_into_itself():
    """The defect card_check cannot see at all.

    "$1.75 to $3.25" at 0.84 leading wraps and draws its two lines THROUGH each other,
    and card_check calls the page clean: every rule it has is about one element hitting
    ANOTHER, and here an element hits ITSELF. So the control cannot be card_check — it
    has to be the geometry. Shrinking is not the answer either: at 0.84 the lines
    overlap at every size.
    """
    d = build("price")
    path = [p for p in os.listdir(d) if p.endswith("price.html")][0]

    def leading():
        """(line boxes, leading ratio) for the price, from the rendered page."""
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, args=["--hide-scrollbars"])
            pg = b.new_page(viewport={"width": cc.W, "height": cc.H})
            try:
                pg.goto("file:///" + os.path.join(d, path).replace("\\", "/"))
                pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
                # ⚠️ SEEK TO THE END FIRST, exactly as offenders() does. The price
                # animates in from `scale(0.46)`, and getBoundingClientRect reports the
                # TRANSFORMED box while getComputedStyle reports the untransformed
                # font-size. Measuring mid-animation gave a "leading ratio" of 0.47 —
                # which was the scale factor, not the leading. Worse, it made the
                # control pass for the wrong reason: 0.46 x 0.84 is under the threshold
                # whatever the leading actually is.
                pg.evaluate("() => { if (window.ppSeek && window.ppDuration) "
                            "window.ppSeek(window.ppDuration); }")
                pg.wait_for_timeout(300)
                # VISUAL lines, grouped with tolerance. Raw rect tops are not line
                # tops: display glyphs come back as several fragments per line whose
                # tops differ by a few px, and taking the first gap between distinct
                # tops read a two-line price as "0.47 leading" — a number describing
                # nothing. Group anything within a third of an em, then measure between
                # the groups.
                return pg.evaluate("""() => {
                  const el = document.getElementById('price');
                  const fs = parseFloat(getComputedStyle(el).fontSize);
                  const r = new Range(); r.selectNodeContents(el);
                  const tops = [...r.getClientRects()].filter(x => x.width > 0.5)
                                 .map(x => x.top).sort((a, b) => a - b);
                  const rows = [];
                  for (const t of tops) {
                    if (!rows.length || t - rows[rows.length - 1] > fs * 0.33) rows.push(t);
                  }
                  const lh = rows.length > 1 ? rows[1] - rows[0] : fs;
                  return {lines: rows.length, ratio: lh / fs};
                }""")
            finally:
                b.close()

    before = leading()
    assert before["lines"] >= 2 and before["ratio"] < af.TIGHT_LEADING, (
        f"CONTROL FAILED: the price renders as {before['lines']} line(s) at "
        f"{before['ratio']:.2f} leading, so it is not the overlapping-lines case and "
        f"this test is not testing the repair.")

    autofit(d)
    after = leading()
    if after["lines"] >= 2:
        assert after["ratio"] >= 1.0, (
            f"still two lines at {after['ratio']:.2f} leading — they are still drawn "
            f"through each other, and card_check will call the page clean.")
    rc, out = check(d)
    assert rc == 0, f"the repaired price card fails card_check:\n{out[-600:]}"
    shutil.rmtree(d, ignore_errors=True)


case("display type that wraps into itself has its leading relaxed",
     _repairs_display_type_that_wraps_into_itself)


# ------------------------------------------------------------------- 5 -----
def _tight_leading_comes_back_when_it_fits_one_line():
    """The repair must not outstay its welcome.

    The first version of it erased itself, and the second version overstayed: the loop
    writes CSS and THEN measures, so on the winning pass it kept the relaxed leading
    from the step before, and a figure that had stopped wrapping two steps earlier was
    left with the wrong leading. Tight display leading is what the template asked for
    and it must come back the moment it is safe.
    """
    d = build("stat")
    autofit(d)
    page = [p for p in os.listdir(d) if p.endswith("stat.html")][0]
    css = open(os.path.join(d, page), encoding="utf-8").read()
    block = re.search(re.escape(af.MARK_OPEN) + r".*?" + re.escape(af.MARK_CLOSE),
                      css, re.S)
    assert block, "autofit wrote no measured block at all"
    big = [ln for ln in block.group(0).splitlines() if ".big" in ln]
    assert big, f"the figure got no measured size:\n{block.group(0)}"
    assert "line-height" not in big[0], (
        f"the figure fits on one line now, so the template's tight display leading "
        f"should have been given back:\n      {big[0].strip()}")
    shutil.rmtree(d, ignore_errors=True)


case("relaxed leading is dropped once the value fits one line",
     _tight_leading_comes_back_when_it_fits_one_line)


# ------------------------------------------------------------------- 6 -----
def _all_three_together():
    """The whole of EP19's halt, in one folder, end to end."""
    d = build("stat", "price", "bars")
    rc, out = check(d)
    assert rc != 0, f"CONTROL FAILED: card_check passed all three broken cards:\n{out[-400:]}"
    broken = out.count("✗")
    assert broken == 3, f"expected all three to fail the gate, {broken} did:\n{out[-600:]}"

    _rc2, out2 = autofit(d)
    assert "still failing" in out2 and "0 still failing" in out2, \
        f"autofit could not fit them all:\n{out2[-800:]}"
    rc3, out3 = check(d)
    assert rc3 == 0, f"card_check still fails after autofit:\n{out3[-800:]}"
    print(f"      {out2.strip().splitlines()[-1]}")
    shutil.rmtree(d, ignore_errors=True)


case("all three of EP19's cards: gate fails, autofit fits, gate passes",
     _all_three_together)


# ------------------------------------------------------------------- 7 -----
def _sees_a_run_too_wide_for_the_card():
    """SIDEWAYS. The overflow only rule 3 can see — and the case that gives it a test.

    🔴 THIS CASE EXISTS BECAUSE THE CONTROL EMBARRASSED THE SUITE. With rule 3 ripped
    out of offenders(), every case above still passed: they all overrun the BOTTOM, and
    the biggest-type rule catches those on its own. Six green ticks and the rule under
    test disabled. A figure with no spaces in it cannot wrap, so it runs off the SIDE,
    where no other rule is looking.
    """
    d = build("wide")
    rc, out = check(d)
    assert rc != 0 and "CLIPPED" in out, (
        f"CONTROL FAILED: card_check passed a $1,750,000,000 figure at 300px in a "
        f"1680px box, so this is not the too-wide case:\n{out[-500:]}")
    assert "extends outside the card" in out, \
        f"the gate failed it for some other reason, so rule 3 is not what is on trial:\n{out[-500:]}"

    _rc2, out2 = autofit(d)
    assert "0 fitted" not in out2, (
        f"autofit fitted nothing — a run wider than the card is invisible to it "
        f"again:\n{out2[-600:]}")
    rc3, out3 = check(d)
    assert rc3 == 0, f"the too-wide figure still fails the gate:\n{out3[-600:]}"
    shutil.rmtree(d, ignore_errors=True)


case("a run too WIDE for the card is seen, and fitted",
     _sees_a_run_too_wide_for_the_card)


print(f"\nautofit: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
