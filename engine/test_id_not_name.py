#!/usr/bin/env python3
"""E20's SWEEP — an id is a promise, a name is a guess.

    python engine/test_id_not_name.py

E20 (EP15, 4 Aug 2026) asked for a sweep of every place a render or an asset is matched
by NAME where an id exists, and listed them. Nobody did it, and the entry sat in the
backlog while `heygen_video_id` bit EP19 four episodes later. This is that sweep given a
test, one site at a time.

The danger is not "not found" — that is loud and gets fixed. It is FINDING THE WRONG
THING: E20's own words, "at 300 episodes titles will collide … the failure then is not
'not found' — it is THE WRONG EPISODE'S RENDER, silently."

Hermetic: builds throwaway folders, touches no rail and no real episode.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import providers                                                      # noqa: E402

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


class FakeProvider(providers.RealProvider):
    """Only `dir()` is stubbed — everything under test is the real method."""

    def __init__(self, d):
        self._d = Path(d)

    def dir(self, ep):
        return self._d


def build(cards, clip_names):
    d = Path(tempfile.mkdtemp(prefix="idname_"))
    (d / "docs").mkdir(parents=True)
    (d / "overlay/clips").mkdir(parents=True)
    (d / "docs/episode.json").write_text(json.dumps({"cards": cards}), encoding="utf-8")
    for n in clip_names:
        (d / "overlay/clips" / n).write_bytes(b"x")
    return d


# ------------------------------------------------------------------- 1 -----
def _the_glob_can_pick_the_wrong_clip():
    """CONTROL. Two files match `*c07*` and only one of them is the card's own.

    This is not contrived: clip names are made from the card's headline, and a headline
    is written by a human. "Chapter 7" or a 2007 in a title is all it takes.
    """
    d = build(
        cards=[{"id": "C7", "page": "ep19-c07-two-winners-and-youre-up.html"}],
        clip_names=["ep19-c07-two-winners-and-youre-up.mp4",
                    "ep19-c11-the-c07-rule-explained.mp4"])
    clips = d / "overlay/clips"
    hits = sorted(p.name for p in clips.glob("*c07*.mp4"))
    assert len(hits) == 2, (
        f"CONTROL FAILED: the pattern matched {hits}, so this folder does not "
        f"reproduce the collision and nothing below is being proved.")
    got = FakeProvider(d)._clip({}, "C7")
    assert got.name == "ep19-c07-two-winners-and-youre-up.mp4", (
        f"_clip returned {got.name!r} — it is still choosing by pattern, and with two "
        f"matches the choice is alphabetical luck.")


case("a clip is found by the page episode.json NAMES, not by a pattern",
     _the_glob_can_pick_the_wrong_clip)


# ------------------------------------------------------------------- 2 -----
def _a_renamed_page_is_followed():
    """E20's stated failure: 'a card whose page is renamed stops matching'."""
    d = build(cards=[{"id": "C7", "page": "ep19-c07-renamed-by-a-human.html"}],
              clip_names=["ep19-c07-renamed-by-a-human.mp4"])
    got = FakeProvider(d)._clip({}, "C7")
    assert got.name == "ep19-c07-renamed-by-a-human.mp4", f"got {got.name!r}"


case("a renamed page is followed, because the card says its own name",
     _a_renamed_page_is_followed)


# ------------------------------------------------------------------- 3 -----
def _the_pattern_still_rescues_an_older_episode():
    """The fallback must survive: episodes authored before `page` was reliable, and
    the standing cards (TITLE/END/WARRANTY) that are not in cards[] at all."""
    d = build(cards=[], clip_names=["ep13-c07-something-old.mp4"])
    got = FakeProvider(d)._clip({}, "C7")
    assert got.name == "ep13-c07-something-old.mp4", (
        f"the pattern fallback is gone and an older episode can no longer be "
        f"assembled: {got!r}")


case("the pattern still rescues an episode whose json cannot say",
     _the_pattern_still_rescues_an_older_episode)


# ------------------------------------------------------------------- 4 -----
def _a_missing_clip_still_halts_in_plain_english():
    d = build(cards=[{"id": "C7", "page": "ep19-c07-two-winners.html"}], clip_names=[])
    try:
        FakeProvider(d)._clip({}, "C7")
    except providers.EngineFlag as e:
        assert "bespoke" in str(e), f"the halt lost its plain-English guidance: {e}"
        return
    raise AssertionError("a card with no clip at all did not halt")


case("a card with no clip still halts, naming the likely cause",
     _a_missing_clip_still_halts_in_plain_english)


print(f"\nid-not-name: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
