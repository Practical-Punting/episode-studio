#!/usr/bin/env python3
"""E32 — A PORTRAIT HERO, A 16:9 WINDOW, AND A HUMAN DECIDING BLIND.

    python engine/test_e32_crop.py

EP30's picked cover hero is **1696 × 2528** — portrait. A 16:9 window on it is 954px
tall, so **1,574px of the photograph is discarded**. At the default (`center`) the
visible band is y787–1741. The field of eleven horses sits at y1751–2098.

    THE CROP MISSED THE HORSES BY TEN PIXELS. TWICE — once on the title card and once
    on the thumbnail. Two steps, the same hero, the same default, and BOTH were caught
    by Jodie's eye rather than by the studio.

🔴 THE OBVIOUS FIX IS THE WRONG ONE. "Detect the subject and crop to it" means guessing
from pixels, and **a wrong automatic crop is worse than a wrong default** — the default
is caught by the review that already exists, and a clever guess is not. So neither
change here guesses:

  1. **CARRY THE VALUE ACROSS THE ASSETS.** The title card and the thumbnail are both
     16:9 on the SAME hero, so an unset `thumbnail.hero_focus` inherits
     `title_card.hero_focus`. Jodie fixed the identical fault twice on one episode;
     once is enough.
  2. **MEASURE, AND SAY SO IN THE FLAG.** The placement review already stops for a
     human — it just tells them nothing. It knows the hero's size and the window, so it
     can say what is off the picture and what the arithmetic of moving it is. **The
     human still decides. They stop deciding blind.**

⚠️ WHAT THIS DELIBERATELY DOES NOT DO: say where the horses are. Nothing in the studio
knows that, and pretending to is the wrong fix.

Nothing here touches the live rail, the network, or a running engine.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SKILL))

import providers                                                       # noqa: E402
import author_thumbnail as at                                          # noqa: E402

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


# EP30's real numbers, from its own hero.png.
W, H = 1696, 2528
FIELD_TOP, FIELD_BOTTOM = 1751, 2098          # where the horses actually are


# ── 2. THE MEASUREMENT ────────────────────────────────────────────────────────
def _it_measures_ep30s_hero():
    r = providers.crop_report(W, H, "center")
    assert r, "a portrait hero produced no measurement at all"
    for want in ("1696", "2528", "954", "1,574", "62%"):
        assert want in r, f"the measurement does not mention {want!r}:\n{r}"
    assert "787" in r and "1741" in r, (
        f"it does not say WHICH BAND the default shows (y787-1741):\n{r}")


case("it measures EP30's hero: 954px window, 1,574px (62%) discarded, band y787–1741",
     _it_measures_ep30s_hero)


def _it_shows_what_a_different_value_would_do():
    """The human decides; the arithmetic is ours. `center 72%` is the value Jodie
    settled on for BOTH assets, and the report must let her reach it without guessing."""
    r = providers.crop_report(W, H, "center")
    assert "100%" in r, f"it never says what the extremes show:\n{r}"
    r72 = providers.crop_report(W, H, "center 72%")
    assert "1133" in r72 and "2087" in r72, (
        f"at 'center 72%' the band is y1133-2087 and the report does not say so:\n{r72}")


case("it says what other values show, so the human can reach 72% by arithmetic",
     _it_shows_what_a_different_value_would_do)


def _it_refuses_to_guess_where_the_subject_is():
    """🔴 THE FIX THAT WOULD BE WORSE THAN THE FAULT. A wrong automatic crop is worse
    than a wrong default, because the default meets a review and a clever guess does
    not. The report must not claim to know where the horses are."""
    r = providers.crop_report(W, H, "center").lower()
    for forbidden in ("horse", "subject detected", "recommend", "best crop", "should be"):
        assert forbidden not in r, (
            f"the measurement claims to know where the subject is ({forbidden!r}) — "
            f"that is the guess E32 says not to make:\n{r}")


case("🔴 CONTROL — it measures and never guesses where the subject is",
     _it_refuses_to_guess_where_the_subject_is)


def _a_landscape_hero_says_little_or_nothing():
    """The fault is portrait heroes. A 16:9-ish hero discards almost nothing and must
    not produce a wall of arithmetic nobody needs — a flag that always shouts is a flag
    nobody reads."""
    r = providers.crop_report(1920, 1080, "center")
    assert not r, f"a 16:9 hero produced a crop warning:\n{r}"


case("a 16:9 hero produces no crop report at all", _a_landscape_hero_says_little_or_nothing)


def _the_flag_carries_the_measurement():
    """The whole point: the message a human is shown must contain it."""
    msg = providers.thumbnail_placement_message(
        Path("hero.png"), None, hero_size=(W, H), focus="center")
    assert "1,574" in msg or "1574" in msg, (
        f"the placement flag still tells the human nothing about the crop:\n{msg}")
    assert "HERO CROP" in msg, "the flag lost its original instruction"


case("the placement flag carries the measurement", _the_flag_carries_the_measurement)


def _the_flag_is_unchanged_when_there_is_nothing_to_say():
    msg = providers.thumbnail_placement_message(Path("hero.png"), None)
    assert "HERO CROP" in msg and "1,574" not in msg


case("with no hero size known, the flag is exactly what it always was",
     _the_flag_is_unchanged_when_there_is_nothing_to_say)


# ── 1. CARRY THE VALUE ACROSS THE ASSETS ──────────────────────────────────────
def _an_unset_thumbnail_focus_inherits_the_title_cards():
    ep = {"title_card": {"hero_focus": "center 72%"}, "thumbnail": {}}
    th = dict(ep["thumbnail"])
    note = at.inherit_hero_focus(ep, th)
    assert th.get("hero_focus") == "center 72%", (
        f"thumbnail.hero_focus did not inherit: {th.get('hero_focus')!r}. Jodie fixed "
        f"the identical fault twice on EP30 — once is enough.")
    assert note and "title_card" in note, (
        "it inherited SILENTLY. A value that appears from another field without saying "
        "so is the next hour somebody spends wondering where it came from.")


case("an unset thumbnail.hero_focus inherits title_card's, and says so",
     _an_unset_thumbnail_focus_inherits_the_title_cards)


def _an_explicit_thumbnail_focus_is_never_overridden():
    """🔴 CONTROL. The thumbnail and the title card are the same hero but not the same
    picture — different text, different safe areas. A deliberate value must win."""
    ep = {"title_card": {"hero_focus": "center 72%"},
          "thumbnail": {"hero_focus": "center 40%"}}
    th = dict(ep["thumbnail"])
    note = at.inherit_hero_focus(ep, th)
    assert th["hero_focus"] == "center 40%", (
        f"an explicit thumbnail value was overwritten by the title card's: "
        f"{th['hero_focus']!r}")
    assert not note


case("🔴 CONTROL — an explicit thumbnail.hero_focus is never overridden",
     _an_explicit_thumbnail_focus_is_never_overridden)


def _neither_set_still_leaves_it_missing():
    """Inheritance must not invent a value. With no title_card focus there is nothing
    to carry across, and the existing REQUIRED check must still be the thing that
    speaks — this change may not weaken it."""
    ep = {"title_card": {}, "thumbnail": {}}
    th = dict(ep["thumbnail"])
    at.inherit_hero_focus(ep, th)
    assert not th.get("hero_focus"), (
        f"inheritance invented {th.get('hero_focus')!r} out of nothing")


case("CONTROL — with nothing to inherit, nothing is invented",
     _neither_set_still_leaves_it_missing)


print(f"\nE32 crop: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
