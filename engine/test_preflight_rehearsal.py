"""test_preflight_rehearsal.py — every way card authoring can HALT is graded at the
commission, and the controls are the BAD SHAPES.

    THE MEASUREMENT THAT STARTED IT, 11 Aug 2026.
    EP20 halted at cards_render on C5: two bars, the first captioned "variables"
    with no number in front of it — the EP18 C9 shape, caught by a guard that had
    existed for three days. Run against that same episode.json, `preflight_cards`
    returned ZERO blockers. So the writer was never told, the commission passed it,
    and the fault was met by a human after the cover pick, seven paid clips and
    Gordon's render.

The pre-flight called author_cards' validators — the ones that RETURN a list. Every
condition that halts LATER (inside the substitution, or in the asserts that run once
a page exists) was invisible to it. `rehearsal_faults` closes that by authoring the
card in memory and throwing the page away, so the coverage is the SAME ACT rather
than a longer list somebody has to remember to extend.

EVERY CASE BELOW IS CONTROL-FIRST: the bad shape is proved to FAIL before the good
shape is trusted to pass. A check that has never been seen to fire is not a check.

Run: python engine/test_preflight_rehearsal.py
"""
from __future__ import annotations

import copy
import glob
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import author_cards as ac
import preflight_cards as pc

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name
          + (f"  <- {why}" if not cond and why else ""))


def episode_dir(n: int) -> Path:
    """BY NUMBER, never by a written-out name — stage-8 renames published folders."""
    hits = sorted(p for p in PP.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else PP / f"PP-EP{n:02d}"


def load(n: int):
    p = episode_dir(n) / "docs/episode.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def card(epj, cid):
    return next(c for c in epj["cards"] if c["id"] == cid)


def blockers(epj, **kw):
    return pc.preflight_cards(epj, **kw)["blockers"]


# --------------------------------------------------------------------------
# The bad shapes. Each mutates a REAL episode.json — a fault invented on a
# hand-written stub proves the checker runs, never that it runs on real input.
# --------------------------------------------------------------------------
def main():
    ep20 = load(20)
    if ep20 is None:
        print("EP20's episode.json is not on this machine — cannot run.")
        return 1

    print("-- the shape that halted EP20, and every sibling of it --")

    def mutate(fn):
        d = copy.deepcopy(ep20)
        fn(d)
        return blockers(d)

    cases = [
        ("a bar drawn as a measurement with NO figure a viewer can read (EP20 C5)",
         lambda d: card(d, "C5")["content"]["bars"][0].__setitem__("note", "variables"),
         "shows NO figure"),
        ("a content value that is not a string (esc)",
         lambda d: card(d, "C7")["content"].__setitem__("figure", 24),
         "must be strings or null"),
        ("a fit value that is not a bare number (fit_css)",
         lambda d: card(d, "C5").__setitem__("fit", {"label_size": "huge"}),
         "is not a bare number"),
        ("a fit key the card does not have (fit_css)",
         lambda d: card(d, "C5").__setitem__("fit", {"nonsense": "12"}),
         "unknown fit key"),
    ]
    for name, fn, needle in cases:
        b = mutate(fn)
        check(name, any(needle in x for x in b), f"reported: {b[:1]}")

    # The rail cases need a trace entry for `rail.of`, which check_trace demands
    # BEFORE the rehearsal would ever run. Written out rather than folded into the
    # loop above, because a case that fails for the wrong reason proves nothing.
    SENT = ("(4) When Benter started applying his method he used only 16 variables "
            "for his form analysis. The increase in variables to 130 highlights the "
            "learning nature of Benter's method.")

    def with_rail(n, of, labels):
        def fn(d):
            c = card(d, "C5")
            c["rail"] = {"n": n, "of": of, "labels": labels}
            c["trace"]["rail"] = SENT
        return fn

    for name, fn, needle in [
        ("a rail position outside its own range (apply_rail)",
         with_rail(9, 3, None), "outside 1..3"),
        ("a rail with fewer labels than positions (apply_rail)",
         with_rail(1, 3, ["Alpha", "Beta"]), "carries 2 labels"),
        ("a rail lighting a rung the card never names (apply_rail)",
         with_rail(1, 3, ["Alpha", "Beta", "Gamma"]), "neither the eyebrow nor the headline"),
    ]:
        b = mutate(fn)
        check(name, any(needle in x for x in b), f"reported: {b[:1]}")

    print("\n-- and it is SILENT on the episodes that are right --")
    check("EP20 as it now stands: zero blockers", not blockers(ep20),
          f"{blockers(ep20)[:2]}")
    for n in (16, 17, 18, 19):
        e = load(n)
        if e is None:
            continue
        b = blockers(e)
        # EP14 predates the measured-figure guard and genuinely carries one of these
        # (C8's "lengths behind the leader" with no number). It is published; it is
        # not a false positive, and it is not asserted clean here.
        check(f"  EP{n} as shipped: zero blockers", not b, f"{b[:2]}")
    # 📌 EP15 IS OVER THE R3 ASSERTION CAP — 5 of 12 cards, 42% against 40% — and it
    # is published. `check_mix` has been called from this module since it was written,
    # so that finding is NOT the rehearsal's and NOT new. Asserting "zero blockers"
    # here would have been a green light bought by ignoring a real one; asserting the
    # SHAPE of what is there says exactly what was measured. (CLAUDE.md: a pass is a
    # statement about what was measured.)
    e15 = load(15)
    if e15:
        b15 = blockers(e15)
        check("EP15's only blocker is the R3 mix cap it shipped over — the sweep adds none",
              len(b15) == 1 and b15[0].startswith("EPISODE MIX"), f"{b15[:2]}")

    print("\n-- a figure spelled out is still a figure (EP17 C3) --")
    e17 = load(17)
    if e17:
        c3 = card(e17, "C3")
        blk = ac.load_block(c3["block"])
        try:
            ac.assert_measured_items_show_a_figure(c3, blk)
            ok = True
        except ac.Halt:
            ok = False
        check("EP17 C3 — bars captioned 'Sixteen per cent' — PASSES", ok,
              "it shipped, it is right, and a guard that halts it is one somebody switches off")
    # ...and the widening did not make the guard toothless.
    bad = {"id": "X", "content": {"bars": [
        {"label": "Start", "value": "5", "note": "per cent profit on turnover", "tone": ""},
        {"label": "Now", "value": "12", "note": "per cent profit on turnover", "tone": "hi"}]}}
    blk = ac.load_block("bars")
    try:
        ac.assert_measured_items_show_a_figure(bad, blk)
        fired = False
    except ac.Halt:
        fired = True
    check("  the EP18 C9 shape still HALTS ('per cent profit on turnover')", fired)

    print("\n-- a conversion has a DIRECTION (EP18 C4 against EP19 C8) --")
    E19 = ("Look at pre-post favourites with odds in the range 8/11 to 9/4 inclusive "
           "(that is, in tote terms, $1.75 to $3.25).The second-favourite must be at "
           "least 4/1 ($5).")
    E18 = ("Interestingly, favourites had an average dividend of $2.80 (about 7/4) but "
           "showed a dramatic 25 per cent loss on turnover.")
    conv = ac.check_converted_odds(
        {"id": "X", "content": {"v": "$1.75 to $3.25"}, "trace": {"v": E19}})
    own = ac.check_converted_odds(
        {"id": "Y", "content": {"v": "$2.80 average — 25% loss"}, "trace": {"v": E18}})
    check("EP19 C8's tote conversion is caught", conv != [])
    check("EP18 C4's OWN dividend is not (the odds are the gloss there)", own == [],
          f"{own[:1]}")
    check("  and the check now runs at the commission, not only at the render",
          any("check_converted_odds" in ln
              for ln in (HERE / "preflight_cards.py").read_text(encoding="utf-8").splitlines()
              if not ln.strip().startswith("#")))

    print("\n-- an empty slot draws nothing (EP20 C5's grey pill) --")
    bars = ac.load_block("bars")
    frame = ac.load_frame("fullscreen")
    base = card(copy.deepcopy(ep20), "C5")
    page_null = ac.render_card(base, bars, frame)
    check("chip: null leaves NO chip element behind",
          'id="chip"' not in page_null,
          "an empty pill is a thing on screen nobody wrote")
    filled = copy.deepcopy(base)
    filled["content"]["chip"] = "A real chip"
    page_full = ac.render_card(filled, bars, frame)
    check("  a chip WITH words is still drawn", 'id="chip"' in page_full)
    check("  and the bars themselves are untouched — they carry no placeholder",
          page_null.count('class="bar ') == 2)
    check("  the empty slot is gone from the VISIBLE text either way",
          "chip" not in ac.visible_text(page_null))

    print("\n-- the coverage is DERIVED, so tomorrow's halt is graded too --")
    src = (HERE.parent / ".claude/skills/pp-episode-production/scripts/author_cards.py"
           ).read_text(encoding="utf-8")
    reh = (HERE / "preflight_cards.py").read_text(encoding="utf-8").split(
        "def rehearsal_faults")[-1]
    check("the rehearsal calls render_card, not a copy of what it does",
          "ac.render_card(" in reh)
    check("  and the two post-render asserts as well",
          "assert_no_invented_text" in reh and "assert_measured_items_show_a_figure" in reh)
    check("  the measured-figure assert takes NO page, so it is honestly a data check",
          "def assert_measured_items_show_a_figure(card, blk)" in src)

    print(f"\npreflight rehearsal: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
