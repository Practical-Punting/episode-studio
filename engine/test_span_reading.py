#!/usr/bin/env python3
"""A HYPHEN BETWEEN TWO NUMBERS IS ALSO READ "TO". (EP32, 19 August 2026.)

    python engine/test_span_reading.py

The article prints `10%-12%`; Gordon says "ten TO twelve per cent". The fold wrote
`ten per cent-twelve per cent`, found no "to", and reported the script as inventing a
figure the article states plainly. **EP32 lost FIVE drafting attempts to it and the
writer was right every time**, including diagnosing the gate itself unprompted.

⛔ **THE FIX JODIE REJECTED, so nobody proposes it again:** adding `%` to the unit list
in the range rule. That would have been the THIRD patch of ONE shape — metres (EP13),
dollars, per cent (EP32). CLAUDE.md fault 7: *"if a guard's coverage is a list somebody
maintains, it is already broken; you have simply not met the missing item yet."*
Her words: *"Proper way please. We have a lot of episodes to go!"*

✅ So the shipped rule **never learns what a marker means**. It knows only that a hyphen
between two numbers can be read "to", and hands both halves to the SAME per-number fold
that already speaks them. There is no list in it, which is the entire point.

═══ THESE ARE THE CONTROLS JODIE SET, AND THEY USE REAL HISTORY ═══════════════════
Not fixtures. Two real episodes, their real captures, and the real figures their
scripts were rejected for:

  POSITIVE · **EP32** — `10%-12%` and `4%-5%`. Blocked five times; must now pass.
  NEGATIVE · **EP18** — its writer invented `$1.75`-`$3.25`. **The capture contains
             neither figure in any notation, and the gate was RIGHT to refuse it four
             times.** It must STILL be refused. *If the fix passes EP18 it is not a fix,
             it is a deletion of the gate.*

🔴 **AND EVERY CASE GOES RED BEFORE IT GOES GREEN.** `spans_as_to=0` is, by construction,
the exact reading this module produced before the change — the parameter defaults to 0
and the rule is skipped — so the first cases below reproduce the bug deliberately. *A
green that was never red proves nothing.*

⚠️ **THE COST, RECORDED RATHER THAN DISCOVERED LATER.** Any `X-Y` now licences a script
saying "X to Y". EP18's own capture carries the phone number `051113-8566`, which may now
be spoken as a range and pass; date spans and scorelines behave the same way. The gate
checks a phrase APPEARS in the article, never that it is the same CLAIM — that boundary
is unchanged and still a human read.

⛔ **THE "and" LEAK IS OUT OF SCOPE BY RULING.** A script saying "ten and twelve" still
passes when the article states no range, because `figures()` splits on "and". Closing it
TIGHTENS the gate and would have refused EP32's legitimate "seven and eight". It is
raised separately, not ridden along.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import script_fidelity as sf                                          # noqa: E402

PASS, FAIL = [], []
DOCS = Path("G:/My Drive/PP Videos/docs")
EP32 = DOCS / "EP32-source-article-how-bookies-make-a-book.md"
EP18 = DOCS / "EP18-source-article-those-top-6-favourites.md"


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def _readings(text, spans):
    """haystacks' inner product, pinned to ONE value of the span axis."""
    out = []
    for frac in (sf._frac_named, sf._frac_in, sf._frac_odds):
        for reading in sf.READINGS:
            for odates in (False, True):
                out.append(sf.norm_words(sf.fold(
                    sf.source_text(text), frac, reading=reading,
                    ordinal_dates=odates, spans_as_to=spans)))
    return out


def traces(text, fig, spans=None):
    hs = sf.haystacks(text) if spans is None else _readings(text, spans)
    return any(sf._contiguous(fig, [h]) for h in hs)


# ── the captures must actually be here, or the controls prove nothing ──────────
def _captures_present():
    assert EP32.is_file(), f"EP32's real capture is missing: {EP32}"
    assert EP18.is_file(), f"EP18's real capture is missing: {EP18}"


case("both real captures are on disk (these controls are history, not fixtures)",
     _captures_present)

if not EP32.is_file() or not EP18.is_file():
    print("\n  !! cannot run the controls without the real captures")
    print(f"\nspan reading: {len(PASS)} passed, {len(FAIL)} failed")
    sys.exit(1)

ep32 = EP32.read_text(encoding="utf-8")
ep18 = EP18.read_text(encoding="utf-8")

# EP32's script said these, the article states both, and the gate refused both.
EP32_FIGURES = ["ten to twelve", "four to five"]
# EP18's script said this and the article states NOTHING of the kind.
EP18_INVENTED = "one dollar seventy five to three dollars twenty five"


# ── 1. RED FIRST. The pre-change reading must still reproduce the bug. ─────────
def _red_first():
    """`spans_as_to=0` IS the old code path — the parameter defaults to 0 and the
    rule is skipped, so this is not a simulation of the old behaviour, it is it."""
    for fig in EP32_FIGURES:
        assert not traces(ep32, fig, spans=0), (
            f"the pre-change reading now traces {fig!r}. The control can no longer "
            f"SEE the bug it exists to prove, so every green below is meaningless.")


case("RED FIRST — without the span axis, EP32's real figures are refused", _red_first)


# ── 2. …and with it, EP32 passes. ─────────────────────────────────────────────
def _ep32_now_passes():
    for fig in EP32_FIGURES:
        assert traces(ep32, fig), (
            f"EP32's script says {fig!r} and its article states it — still refused. "
            f"This is the episode the change exists for.")


case("EP32's five-times-blocked figures now trace", _ep32_now_passes)


# ── 3. THE NEGATIVE CONTROL. EP18 must stay refused. ──────────────────────────
def _ep18_still_refused():
    """The writer invented a price range; the capture holds $10.80 $2 $2.80 $3 $4.60
    $6.10 and no range at all. A gate that passes this is not a gate."""
    assert not traces(ep18, EP18_INVENTED), (
        "EP18's INVENTED figure now traces. The span axis has widened the gate into "
        "uselessness — this is the deletion Jodie named, not a fix.")
    for half in ("seventy five", "three dollars twenty five"):
        assert not traces(ep18, half), \
            f"{half!r} traces in EP18's article, which does not contain it"


case("NEGATIVE — EP18's invented $1.75-$3.25 is STILL refused", _ep18_still_refused)


# ── 4. …and anything nowhere in the article. ─────────────────────────────────
def _invented_still_refused():
    for fig in ("ninety nine", "ten to fifteen", "four hundred and twelve",
                "twenty to thirty"):
        for name, text in (("EP32", ep32), ("EP18", ep18)):
            assert not traces(text, fig), \
                f"{fig!r} is nowhere in {name}'s article and was accepted"


case("a figure that appears nowhere is still refused", _invented_still_refused)


# ── 5. PURELY ADDITIVE — nothing that matched before may stop matching. ───────
def _additive():
    """The axis may only WIDEN what the source can be read as. If a reading the old
    path produced has vanished, some other episode's approved script could start
    failing — a regression that would surface as a false halt weeks later."""
    for text, name in ((ep32, "EP32"), (ep18, "EP18")):
        before = {" ".join(h) for h in _readings(text, 0)}
        after = {" ".join(h) for h in sf.haystacks(text)}
        lost = before - after
        assert not lost, (
            f"{name}: {len(lost)} reading(s) the old path produced are GONE. The axis "
            f"must add readings and never replace them. First: {sorted(lost)[:1]}")


case("the axis is purely additive — no old reading was lost", _additive)


# ── 6. MARKER-AGNOSTIC BY CONSTRUCTION, not by a list. ───────────────────────
def _no_list():
    """The rule must not acquire a unit list. That is the whole ruling."""
    src = __import__("inspect").getsource(sf.ranges_as_to)
    for banned in ("%|", "kg", "km", "furlong", "dollar", "UNITS"):
        assert banned not in src, (
            f"ranges_as_to mentions {banned!r} — it has started to learn what markers "
            f"MEAN. That is the maintained list Jodie ruled against; the rule must "
            f"only know that a hyphen between two numbers reads 'to'.")


def _markers_it_was_never_taught():
    """Shapes nobody wired in: a marker invented for this test, and a bare range."""
    for raw, spoken in [("7-9 zorks", "seven to nine"),
                        ("1986-88", "nineteen eighty six to eighty eight"),
                        ("$4-$6", "four dollars to six dollars")]:
        got = sf.ranges_as_to(raw)
        assert " to " in got, f"{raw!r} was not read as a range: {got!r}"


case("the rule contains no unit list (fault 7 answered, not renamed)", _no_list)
case("it handles markers it was never taught, including a made-up one",
     _markers_it_was_never_taught)


# ── 7. THE RECORDED COST, asserted so it stays a known trade. ────────────────
def _the_cost_is_real_and_known():
    """EP18's capture carries a phone number. After this change it reads as a range.

    Asserted rather than merely commented so that if someone later narrows the rule
    and this stops being true, they are told they have changed the trade — not left
    to wonder whether the comment was ever accurate.
    """
    assert " to " in sf.ranges_as_to("051113-8566"), (
        "the documented cost is no longer real — the comment in script_fidelity.py "
        "and this file's docstring now describe behaviour that does not happen")


case("the documented cost (a phone number reads as a range) is real and known",
     _the_cost_is_real_and_known)

print(f"\nspan reading: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
