#!/usr/bin/env python3
"""EP15's name carries an EXCLAMATION MARK. Prove the whole path survives it.

Jodie's ruling, 3 Aug 2026: the episode is `Squeeze Those Odds! — Part 1`, because
"it is Roger Dedman's article and his title". The bang belongs to the NAME, then the
em dash, then the part — not `Squeeze Those Odds — Part 1!`.

⚠️ WHY THIS IS A TEST AND NOT A READ-THROUGH. `derive()` looks obviously safe, and
`title_case()` — which WOULD have re-cased around punctuation — was deleted when the
rule changed on 2 Aug. But the one-name assertion folds its inputs before comparing
(case, dash flavour, spacing are deliberately noise), and **a fold that quietly ate
punctuation would make the check pass while the title card said something different
from the e-book.** That is the exact failure the check exists to catch, and the only
way to know is to feed it a mismatch and watch it fire.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import youtube_title as yt                                            # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                 # noqa: BLE001
        pass

NAME = "Squeeze Those Odds! — Part 1"
WANT = "Squeeze Those Odds! — Part 1 | How to Win at Horse Racing"

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def epj(title=NAME, setup="SQUEEZE THOSE", payoff="ODDS!", part="Part 1",
        ebook=NAME, ytt=WANT):
    return {"title": title,
            "cover": {"title_setup": setup, "title_payoff": payoff, "part": part},
            "packaging": {"ebook_title": ebook, "youtube_title": ytt}}


# ---------------------------------------------------------------- derivation --
def _derives_verbatim():
    got = yt.derive_from(epj())
    assert got == WANT, f"\n      got  {got!r}\n      want {WANT!r}"


case("the bang survives derivation, character for character", _derives_verbatim)


def _nothing_recases_or_strips():
    got = yt.derive(NAME)
    assert "!" in got, f"the exclamation mark was STRIPPED: {got!r}"
    assert got.startswith("Squeeze Those Odds! — Part 1"), \
        f"the name was altered before the suffix: {got!r}"
    assert not hasattr(yt, "title_case"), \
        "title_case() is back — it re-cases around punctuation and must stay deleted"


case("nothing strips the bang or re-cases around it", _nothing_recases_or_strips)


def _the_bang_is_on_the_name_not_the_part():
    """The shape Jodie ruled against, spelled out so it cannot drift back."""
    wrong = "Squeeze Those Odds — Part 1!"
    assert yt.derive(NAME) != yt.derive(wrong), "the two shapes derive identically"
    assert yt.derive(NAME).index("!") < yt.derive(NAME).index("Part"), \
        "the bang must sit on the NAME, before the em dash and the part"


case("the bang sits on the name, before the dash and the part",
     _the_bang_is_on_the_name_not_the_part)


# ------------------------------------------------------------- the one name --
def _all_three_agree():
    problems = yt.check_one_name(epj())
    assert not problems, f"a consistent set was rejected:\n      {problems}"


case("title card, e-book and YouTube all agree -> no complaint", _all_three_agree)


def _the_fold_does_not_eat_punctuation():
    """THE ONE THAT MATTERS. Drop the bang from the TITLE CARD only."""
    problems = yt.check_one_name(epj(payoff="ODDS"))
    assert problems, (
        "the one-name check PASSED while the title card said 'SQUEEZE THOSE ODDS' and "
        "the e-book said 'Squeeze Those Odds!'. The fold is eating punctuation, so the "
        "check cannot see exactly the kind of difference it exists to catch.")
    assert "different things in different places" in problems[0].lower()


case("dropping the bang from the TITLE CARD is caught", _the_fold_does_not_eat_punctuation)


def _ebook_mismatch_is_caught():
    problems = yt.check_one_name(epj(ebook="Squeeze Those Odds — Part 1"))
    assert problems, ("the e-book dropped the bang and the check stayed silent")


case("dropping the bang from the E-BOOK is caught", _ebook_mismatch_is_caught)


def _youtube_mismatch_is_caught():
    problems = yt.check_one_name(
        epj(ytt="Squeeze Those Odds — Part 1 | How to Win at Horse Racing"))
    assert problems, "the YouTube title dropped the bang and the check stayed silent"


case("dropping the bang from the YOUTUBE title is caught", _youtube_mismatch_is_caught)


def _case_and_dash_are_still_noise():
    """The fold must stay tolerant of what it is SUPPOSED to tolerate."""
    ok = yt.check_one_name(epj(setup="squeeze  those", payoff="odds!",
                               ebook="Squeeze Those Odds! - Part 1"))
    assert not ok, (
        "case, spacing or dash flavour now trips the check — those are deliberately "
        f"noise, and making them fatal would halt correct builds:\n      {ok}")


case("case, spacing and dash flavour are still tolerated", _case_and_dash_are_still_noise)


# ------------------------------------------------- the shipped copy file ------
def _copy_file_gate_accepts_the_bang():
    text = WANT + "\n\nSome description copy that mentions nothing else.\n"
    problems = yt.check_text(text, WANT)
    assert not problems, f"a correct copy file was rejected:\n      {problems}"


case("the shipped youtube.txt gate accepts a title with a bang",
     _copy_file_gate_accepts_the_bang)


def _copy_file_gate_still_catches_a_near_miss():
    text = "Squeeze Those Odds — Part 1 | How to Win at Horse Racing\n"
    problems = yt.check_text(text, WANT)
    assert problems, "line 1 lost the bang and the gate passed it"


case("...and still catches a line 1 that lost the bang",
     _copy_file_gate_still_catches_a_near_miss)

print(f"\nbang title: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
