"""THE COUNTRY-TRACK CARD PAIR — a card born too big, and the cue its fix orphaned.

TWO FAULTS, ONE CAUSE, WHICH IS WHY THEY ARE ONE SUITE. EP24 C19 (and EP23 C21 before
it) were AUTHORED with more content than the card can hold; fixing that over-full card
rewrote its cue, and the rewritten cue no longer existed in the finished render. The
second fault was created by the first fix.

2a  A MATRIX CARD MUST NOT BE BORN TOO BIG.
    C19 arrived with four country courses, two facts each. It did not fit at the autofit
    floor (60%/16px), the automatic layout swap did not rescue it, and — the measurement
    that matters — TIGHTENING THE CELLS TO 73% OF THEIR CHARACTERS DID NOT RESCUE IT
    EITHER. Over-full by a ROW, not by phrasing. Split two-and-two: 88% and 94%.

2b  A POST-RENDER EDIT MUST KEEP THE CUE IN THE SRT.
    The split's new cue was taken from the card's own trace{} — the ARTICLE's words:
        cue   "sprint races favour runners drawn 7 and inside"
        SRT   "Sprint races favour runners drawn seven and inside."
    The phrase was right. The `7` was the whole fault: Gordon speaks a spoken-words
    script, so every number is spelled out, while the article and every trace sentence
    use digits. trace proves a FIGURE's source; the cue anchors to a SOUND.

Run: python engine/test_card_size_and_cue.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import preflight_cards as pc                                          # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


def matrix(n_rows, cell="A testing 400m run from the turn to the wire"):
    return {"cards": [{"id": "C19", "block": "matrix", "content": {"rows": [
        {"label": f"Track {i}", "cells": [cell, cell]} for i in range(n_rows)]}}]}


print("\n-- 2a: a matrix card must not be BORN too big --")
check("the four-row card EP24 halted on is refused", pc.overfull_faults(matrix(4)),
      "this is the exact shape that failed below the autofit floor, twice")
check("  and the message says to SPLIT, not to cut",
      "Split it across cards" in " ".join(pc.overfull_faults(matrix(4)))
      and "Nothing is dropped" in " ".join(pc.overfull_faults(matrix(4))),
      "tighten-and-keep then split, never drop a fact")
check("  and it says to put each card on the beat where its items are SPOKEN",
      "SPOKEN" in " ".join(pc.overfull_faults(matrix(4))),
      "the original sat on beat 37 showing all four while Gawler alone was spoken")
check("the two-row split that DID fit is allowed", pc.overfull_faults(matrix(2)) == [],
      "88% and 94% of template size — a guard that fails the fix is worse than none")
check("a matrix of SHORT chips is not refused for its row count",
      pc.overfull_faults(matrix(5, cell="7 and in")) == [],
      "row count alone is not the fault; a guard everyone ignores is worse than none")
check("a NON-matrix block is not graded by this rule",
      pc.overfull_faults({"cards": [{"id": "C1", "block": "slate", "content":
                                     {"rows": [{"cells": ["x" * 60]}] * 6}}]}) == [])
check("the cap is the MEASURED number, not an interpolation", pc.MATRIX_MAX_ROWS == 2,
      "3 rows has never been measured; a cap invented between two data points is a "
      "guess wearing a number")

print("\n-- 2b: a post-render edit must keep the cue in the SRT --")
SRT = """1
00:09:05,000 --> 00:09:12,000
Sprint races favour runners drawn seven and inside.

2
00:09:45,000 --> 00:09:50,000
Runners drawn inside seven have a distinct advantage.
"""
bad = {"cards": [{"id": "C19", "cue": "sprint races favour runners drawn 7 and inside"}]}
good = {"cards": [{"id": "C19", "cue": "Sprint races favour runners drawn seven and inside"}]}

f = pc.cue_in_srt_faults(bad, SRT)
check("EP24's ACTUAL orphaned cue is caught", bool(f), "the fault that halted the shot map")
check("  and the DIGIT is named as the cause", "DIGIT" in " ".join(f),
      "'7' vs 'seven' is the whole fault, and it will recur on every card about figures")
check("  and it explains trace{} vs the cue", "anchors to a sound" in " ".join(f),
      "a cue copied from trace fails silently the moment it carries a figure")
check("  and it offers the real spoken line to re-anchor to",
      "Sprint races favour runners drawn seven and inside." in " ".join(f),
      "a halt that does not say what to use instead is a halt she has to research")
check("the corrected cue passes", pc.cue_in_srt_faults(good, SRT) == [])
check("a card with no cue is not graded",
      pc.cue_in_srt_faults({"cards": [{"id": "C1"}]}, SRT) == [])

print("\n-- against EP24's REAL cards and REAL srt --")
try:
    import ep_paths                                                   # noqa: E402
    d = ep_paths.episode_dir(24)
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    srt = (d / "renders/aligned.srt").read_text(encoding="utf-8", errors="replace")
except Exception as e:                                                # noqa: BLE001
    print(f"  (EP24 is not readable here: {e})")
    epj = srt = None

if epj and srt:
    check("EP24 as it now stands has every cue in the SRT",
          pc.cue_in_srt_faults(epj, srt) == [], pc.cue_in_srt_faults(epj, srt))
    check("  and its split country cards are within the size cap",
          pc.overfull_faults(epj) == [], pc.overfull_faults(epj))
    # and the thing that would have caught it BEFORE the shot map ran:
    broken = json.loads(json.dumps(epj))
    for c in broken["cards"]:
        if c["id"] == "C19":
            c["cue"] = "sprint races favour runners drawn 7 and inside"
    check("  restoring the orphaned cue reproduces the halt",
          bool(pc.cue_in_srt_faults(broken, srt)),
          "if this passes, the guard would not have caught the real fault")

print("\n-- both are wired where they can actually fire --")
pf = (HERE / "preflight_cards.py").read_text(encoding="utf-8")
check("the size cap runs in the pre-flight, at audit_inputs",
      "blockers += overfull_faults(epj)" in pf,
      "layout (autofit/card_check) cannot run there — this is pure data and can")
prov = (HERE / "providers.py").read_text(encoding="utf-8")
sm = prov.split("def build_shot_map")[-1].split("\n    def ")[0]
check("the SRT cue check runs at shot_map, where the SRT first exists",
      "cue_in_srt_faults" in sm)
check("  and BEFORE the timings are derived",
      sm.index("cue_in_srt_faults") < sm.index("derive_timings(d)"),
      "otherwise derive_timings reports an unplaceable card as a decision to make")

print(f"\ncard size and cue: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
