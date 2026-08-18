#!/usr/bin/env python3
"""§0a-ii's ONE NARROW EXCEPTION, AND THE FIVE THINGS THAT KEEP IT NARROW.

    python engine/test_ebook_corrections.py

EP30's article prints "$18.10 profit and 33 per cent POT" over its own 103 bets.
18.10/103 is 17.5 per cent — the 33 is the STRIKE RATE from three words earlier, copied
into the POT slot. Every other figure in that article checks exactly, so it is one slip.

§0a-ii used to say such a figure is REPRODUCED, NOT REPAIRED. Ruling A27 (Jodie and
Hugh, 18 Aug 2026) amends it: a figure the article's OWN numbers contradict may be
corrected, declared per episode, with a note.

🔴 THE WHOLE VALUE OF THIS FILE IS THAT THE EXCEPTION STAYS THE SIZE IT WAS RULED.
The original objection to a departures engine — "anything that can do anything can hide
anything" — is answered by literals, one episode, and a reader-visible note. What is NOT
answered by any of those is expressive reach, and that is rule 4's job: only a FIGURE may
change. Without it, `"33 per cent POT" -> "the favourite always wins"` is a legal
correction, and the e-book becomes whatever episode.json says it is.

⚠️ AND THE ONE THE GUARDS CANNOT COVER, recorded because it was accepted knowingly:
they bound the MECHANISM, not the JUDGEMENT about when to invoke it. The protection
there is a named per-episode decision and a note the reader sees — not this file.

Nothing here touches the live rail, the network, a running engine, or any real episode.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(SKILL))

import author_ebook as ae                                              # noqa: E402

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


# EP30's real sentence, verbatim from the source article.
ART = ["The totals for the two days were 103 bets, 34 winners, 33 per cent strike rate, "
       "$18.10 profit and 33 per cent POT. Considering that we are betting on "
       "favourites, that’s a pretty good return."]
NOTE = "The article prints 33 per cent here; $18.10 from 103 bets is 17.5 per cent."
GOOD = {"from": "$18.10 profit and 33 per cent POT",
        "to": "$18.10 profit and 17.5% POT",
        "why": "18.10/103 = 17.5% truncated, the article's own convention.",
        "note": NOTE}


def run(corr, notes=(NOTE,), art=None):
    """Apply corrections to a COPY and give back the article as compared."""
    a = list(art if art is not None else ART)
    ae.apply_corrections(a, {"corrections": corr}, list(notes))
    return a


def halts(corr, notes=(NOTE,), art=None):
    try:
        run(corr, notes, art)
    except ae.Halt as h:
        return str(h)
    return None


# ── THE POSITIVE CASE: EP30 ────────────────────────────────────────────────────
def _ep30s_correction_applies():
    out = run([GOOD])
    assert "$18.10 profit and 17.5% POT" in out[0], out[0]
    assert "33 per cent strike rate" in out[0], (
        "the STRIKE RATE was corrected too — the correction was not anchored tightly "
        "enough and changed a figure that is right: " + out[0])


case("EP30's correction lands on the POT and leaves the strike rate alone",
     _ep30s_correction_applies)


def _the_symbol_wording_is_permitted():
    """Hugh asked for '17.5% POT'. Rule 4 strips digits, '.', '%' AND 'per cent', so
    both sides reduce to 'POT' — '%' and 'per cent' are one unit written two ways."""
    assert ae.figure_stripped("33 per cent POT") == ae.figure_stripped("17.5% POT"), (
        f"{ae.figure_stripped('33 per cent POT')!r} vs "
        f"{ae.figure_stripped('17.5% POT')!r} — Hugh's wording would be refused")
    assert halts([GOOD]) is None


case("'33 per cent' -> '17.5%' is permitted: one unit, two spellings",
     _the_symbol_wording_is_permitted)


# ── 1. EXACTLY ONCE ────────────────────────────────────────────────────────────
def _a_from_that_matches_twice_halts():
    # from/to are a MATCHED pair here, so rule 4 passes and rule 1 is what fires. (The
    # first version of this case left `to` as the full sentence, so it tripped rule 4
    # instead and proved nothing about anchoring.)
    h = halts([{**GOOD, "from": "33 per cent", "to": "17.5%"}])
    assert h and "appears 2 time(s)" in h, (
        f"a correction matching BOTH the strike rate and the POT was accepted: {h}. "
        f"It would have silently corrected a figure that is right.")


case("CONTROL — a `from` that matches twice halts (it would hit the strike rate too)",
     _a_from_that_matches_twice_halts)


def _a_from_that_matches_nothing_halts():
    h = halts([{**GOOD, "from": "42 per cent POT", "to": "17.5% POT"}])
    assert h and "appears 0 time(s)" in h, (
        f"a correction of something the article does not say was accepted: {h}")


case("CONTROL — a `from` the article does not contain halts",
     _a_from_that_matches_nothing_halts)


# ── 3/4. ONLY A FIGURE MAY CHANGE ──────────────────────────────────────────────
def _rewriting_the_sentence_halts():
    """🔴 THE HOLE RULE 4 CLOSES. Without it this is a legal correction."""
    h = halts([{**GOOD, "to": "$18.10 profit and the favourite always wins"}])
    assert h and "changes WORDS" in h, (
        f"a correction rewrote the article's PROSE and was accepted: {h}\n"
        f"    That is the e-book becoming whatever episode.json says it is.")


case("🔴 CONTROL — a correction that rewrites words, not a figure, halts",
     _rewriting_the_sentence_halts)


def _changing_a_single_word_halts():
    h = halts([{**GOOD, "to": "$18.10 profit and 17.5% POTS"}])
    assert h and "changes WORDS" in h, f"'POT' -> 'POTS' slipped through: {h}"


case("CONTROL — even a one-letter word change halts", _changing_a_single_word_halts)


def _a_correction_that_changes_nothing_halts():
    h = halts([{**GOOD, "to": GOOD["from"]}])
    assert h and "changes nothing" in h, f"a no-op correction was accepted: {h}"


case("CONTROL — a correction whose from and to are identical halts",
     _a_correction_that_changes_nothing_halts)


# ── 5. THE DISCLOSURE ──────────────────────────────────────────────────────────
def _a_correction_without_its_note_halts():
    h = halts([GOOD], notes=())
    assert h and "no <p class=\"note\">" in h, (
        f"a corrected figure was accepted with NO note: {h}\n"
        f"    That is the book printing a number PP's own page does not print, "
        f"silently — which is the one thing §0a-ii's amendment does not allow.")


case("🔴 CONTROL — a correction with no <p class=\"note\"> halts",
     _a_correction_without_its_note_halts)


def _a_note_about_something_else_does_not_count():
    h = halts([GOOD], notes=("A POT is profit on turnover.",))
    assert h and "no <p class=\"note\">" in h, (
        f"any old note satisfied the disclosure: {h}")


case("CONTROL — an unrelated note does not satisfy the disclosure",
     _a_note_about_something_else_does_not_count)


# ── 5b. THE WAIVER (A27's SECOND AMENDMENT, Hugh, 18 Aug 2026) ────────────────
# The disclosure became WAIVABLE hours after A27 was made. Rule 5 is NOT deleted — a
# missing note with no waiver still halts. What changed is that a human may decide the
# SUBSCRIBER does not see it, and must say so, by name, in the episode's own file.
#     What it costs: the book prints a figure PP's own website does not, with nothing on
# the page explaining the difference — the exact scenario the disclosure existed to
# prevent. Only the READER loses it; every audit trail survives.
WAIVER = ("Hugh, 18 Aug 2026 — the disclosure paragraph is editorial clutter in a "
          "subscriber e-book. PP owns the article and will correct it at source.")
WAIVED = {k: v for k, v in GOOD.items() if k != "note"} | {"note_waived": WAIVER}


def _a_declared_waiver_passes_with_no_note_at_all():
    assert halts([WAIVED], notes=()) is None, halts([WAIVED], notes=())
    out = run([WAIVED], notes=())
    assert "$18.10 profit and 17.5% POT" in out[0], out[0]


case("a DECLARED waiver passes with no note in the book at all",
     _a_declared_waiver_passes_with_no_note_at_all)


def _a_missing_note_with_no_waiver_still_halts():
    """🔴 THE RULE IS WAIVABLE, NOT DELETED. Silence is not a waiver."""
    bare = {k: v for k, v in GOOD.items() if k != "note"}
    h = halts([bare], notes=())
    assert h and "no note and no waiver" in h, (
        f"a correction with no note and nobody having waived it was accepted: {h}\n"
        f"    That is the book printing a figure PP's page does not, with no human "
        f"having decided that it should.")


case("🔴 CONTROL — a missing note with NO waiver still halts",
     _a_missing_note_with_no_waiver_still_halts)


def _a_waiver_with_no_reason_halts():
    for empty in ("", "   ", None):
        c = {k: v for k, v in GOOD.items() if k != "note"} | {"note_waived": empty}
        h = halts([c], notes=())
        assert h and "no note and no waiver" in h, (
            f"a waiver with no reason ({empty!r}) was accepted: {h}. A waiver whose "
            f"reason is blank records that somebody waived it and not who or why, "
            f"which is the same as not recording it.")


case("CONTROL — a waiver with no reason halts", _a_waiver_with_no_reason_halts)


def _a_note_and_a_waiver_together_halts():
    c = dict(GOOD) | {"note_waived": WAIVER}
    h = halts([c])
    assert h and "BOTH a note and a note_waived" in h, (
        f"a correction claiming both disclosure and waiver was accepted: {h}")


case("CONTROL — declaring both a note and a waiver halts",
     _a_note_and_a_waiver_together_halts)


def _the_note_is_matched_whitespace_folded():
    """The book wraps its notes across lines; the declaration is one string. Comparing
    them raw would fail on a line break, which is not a difference in the prose."""
    assert halts([GOOD], notes=("  The article prints 33 per cent here;\n  $18.10 from "
                                "103 bets is 17.5 per cent.  ",)) is None


case("the note matches with whitespace folded, so a wrapped line still counts",
     _the_note_is_matched_whitespace_folded)


# ── SHAPE ──────────────────────────────────────────────────────────────────────
def _every_field_is_required():
    """from/to/why are ALWAYS required. `note` is required only in the sense that a
    correction must carry either it or a declared waiver — held by the waiver cases
    above, not here, since A27's second amendment."""
    for drop in ("from", "to", "why"):
        c = {k: v for k, v in GOOD.items() if k != drop}
        h = halts([c])
        assert h and drop in h, f"a correction missing {drop!r} was accepted: {h}"


case("CONTROL — from, to and why are always required",
     _every_field_is_required)


def _absent_corrections_means_none():
    """The one place the 'a missing key halts' convention is not followed, on purpose:
    a forgotten correction cannot hide anything (the body would not match), and
    requiring the key would halt all 30 existing episodes to record a thing none do."""
    a = list(ART)
    ae.apply_corrections(a, {}, [])
    assert a == ART, "an absent corrections key changed the article"
    ae.apply_corrections(a, {"corrections": []}, [])
    assert a == ART


case("an absent corrections key means none, and disturbs no existing episode",
     _absent_corrections_means_none)


def _the_article_on_disk_is_never_touched():
    """Corrections are applied to the comparison copy. If they ever reached the source
    article the studio would lose the only record of what PP actually printed."""
    a = list(ART)
    run([GOOD], art=a)
    assert a == ART, "apply_corrections mutated the list it was handed a copy of"


case("the source article is never modified — only the comparison copy",
     _the_article_on_disk_is_never_touched)


print(f"\nebook corrections: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
