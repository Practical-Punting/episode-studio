"""A series episode carries two names; anything else is still one name. (Jodie, 5 Oct 2026.)

    python engine/test_one_name_series.py

`youtube_title.check_one_name` compared the title, the title card, the e-book and the YouTube
title and demanded ONE name. EP49 (the first two-way, a six-part series) failed it on purpose
from 27 Sep: its title is the episode's headline while the card and the e-book carry the
series. Jodie's ruling closes that: a SERIES episode properly carries the series with its
part and its own headline, and a surface may carry either or both — and any OTHER mismatch
still fails. EP49 and EP55 must pass; a single-presenter episode with a stray name must not.
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import youtube_title as Y                                              # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


PP = pathlib.Path(r"G:\My Drive\PP Videos")
REAL = {"EP49": PP / "PP-EP49-Fighting-a-Complex-Game-Part-1/docs/episode.json",
        "EP55": PP / "PP-EP55-Is-the-Trainer-So-Important-Part-2/docs/episode.json"}

print("\n-- the two real series episodes pass --")
for ep, f in REAL.items():
    if not f.is_file():
        print(f"  ({ep}'s episode.json is not on this machine — SKIPPED, not assumed)")
        continue
    e = json.loads(f.read_text(encoding="utf-8"))
    check(f"{ep} passes (series + part, its own name, and the two combined)",
          not Y.check_one_name(e), Y.check_one_name(e)[:1])

SERIES = {"title": "Is the Trainer So Important? - Part 2",
          "cover": {"title_setup": "The Fundamentals", "title_payoff": "of Handicapping",
                    "part": "Part 2"},
          "packaging": {"ebook_title": "The Fundamentals of Handicapping - Part 2",
                        "youtube_title": "The Fundamentals of Handicapping, Part 2: Is the Trainer So Important?",
                        "_series": {"name": "The Fundamentals of Handicapping", "parts": 6,
                                    "this_part": 2, "episode_name": "Is the Trainer So Important?"}}}
print("\n-- and any OTHER mismatch on a series episode still fails --")
check("CONTROL: the synthetic series episode passes", not Y.check_one_name(SERIES))
bad = copy.deepcopy(SERIES)
bad["packaging"]["ebook_title"] = "Trainers and Jockeys - Part 2"
check("a stray third name on the e-book FAILS", bool(Y.check_one_name(bad)))
check("  and the message names the place", "E-BOOK" in "".join(Y.check_one_name(bad)))
wrong_part = copy.deepcopy(SERIES)
wrong_part["cover"]["part"] = "Part 3"
check("the series with the WRONG part FAILS", bool(Y.check_one_name(wrong_part)))
half = copy.deepcopy(SERIES)
half["title"] = "Is the Trainer Important? - Part 2"
check("a near-miss of the episode name FAILS", bool(Y.check_one_name(half)))

print("\n-- a single-presenter episode is still held to ONE name --")
SINGLE = {"title": "The Meaning of Form - Part 2",
          "cover": {"title_setup": "The Meaning", "title_payoff": "of Form", "part": "Part 2"},
          "packaging": {"ebook_title": "The Meaning of Form - Part 2",
                        "youtube_title": "The Meaning of Form - Part 2 | How to Win at Horse Racing"}}
check("CONTROL: one name everywhere passes", not Y.check_one_name(SINGLE))
stray = copy.deepcopy(SINGLE)
stray["packaging"]["youtube_title"] = "Digging for Winners | How to Win at Horse Racing"
check("a stray third name FAILS", bool(Y.check_one_name(stray)))

print(f"\none name, series-aware: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
