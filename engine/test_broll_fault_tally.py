#!/usr/bin/env python3
"""THE TALLY MUST RECORD THE REVIEW, NOT ONLY THE FAULT.

    python engine/test_broll_fault_tally.py

A tally that only logs faults cannot produce a rate: a missing row is indistinguishable
from an episode nobody looked at, and the arithmetic silently counts "not reviewed" as
"clean". That is the whole reason `--clean` exists, and it is the one property of this
file worth a test — everything else is a markdown table.

The second property is the one that keeps it honest in a meeting: a number computed
from one or two episodes must SAY it is not a rate yet. EP30's 1-in-4 is a single
observation by eye, and the decisions waiting on it (generate two and keep one;
inspect returned footage) cost credits and build time across ~1,944 projected clips.

Nothing here touches the real tally file, the live rail or the network.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import broll_fault                                                     # noqa: E402

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


class Sandbox:
    """Point the module at a throwaway tally and a fixed clip count."""

    def __init__(self, clips=4):
        self.clips = clips

    def __enter__(self):
        self.td = tempfile.TemporaryDirectory()
        self.real_tally, self.real_count = broll_fault.TALLY, broll_fault.clip_count
        broll_fault.TALLY = Path(self.td.name) / "tally.md"
        broll_fault.clip_count = lambda n: self.clips
        return self

    def __exit__(self, *a):
        broll_fault.TALLY, broll_fault.clip_count = self.real_tally, self.real_count
        self.td.cleanup()


def _a_clean_review_is_recorded_not_omitted():
    """🔴 THE PROPERTY THE WHOLE FILE EXISTS FOR."""
    with Sandbox(clips=6):
        broll_fault.record(31, [], "")
        text = broll_fault.TALLY.read_text(encoding="utf-8")
        assert "| EP31 |" in text, (
            "a clean review left NO row. Then EP31 is indistinguishable from an episode "
            "nobody looked at, and its 6 good clips never reach the denominator — which "
            "biases the fault rate UPWARDS, towards spending credits we may not need to.")
        assert "of 6 clips across 1 reviewed" in broll_fault.rate(), broll_fault.rate()


case("🔴 a CLEAN review is recorded, so good clips reach the denominator",
     _a_clean_review_is_recorded_not_omitted)


def _the_denominator_is_lifted_not_typed():
    with Sandbox(clips=7):
        row = broll_fault.record(31, ["c02"], "both sides of the rail")
        assert "| 7 |" in row, (
            f"the clip count was not lifted from episode.json: {row!r}. A human logging "
            f"a fault must never have to count clips — that is a number re-typed.")


case("the clip count is lifted from episode.json, never typed in",
     _the_denominator_is_lifted_not_typed)


def _a_small_sample_says_so():
    with Sandbox(clips=4):
        broll_fault.record(30, ["c01"], "both sides of the rail")
        r = broll_fault.rate()
        assert "25.0%" in r, r
        assert "NOT a rate yet" in r, (
            "a 25% computed from ONE episode printed as a bare number. It will be "
            "quoted in a decision about credits across ~1,944 clips.")


case("one episode prints the number AND says it is not a rate yet", _a_small_sample_says_so)


def _every_number_carries_its_lower_bound_warning():
    """🔴 EP23 IS WHY. It was approved 4/4, published on 13 Aug, and Hugh found horses on
    both sides of its rail on the 14th. So 'approved' is evidence the episode was
    WATCHED and none that the b-roll was EXAMINED — and a fault-free row means nothing
    was noticed, never nothing was there. A number printed without that caveat gets
    quoted as the rate."""
    with Sandbox(clips=6):
        broll_fault.record(31, [], "")
        r = broll_fault.rate()
        assert "LOWER BOUND" in r, f"the rate printed with no lower-bound caveat: {r}"
        assert "EP23" in r, "the caveat does not carry the evidence that proves it"
        assert "EP6" in r, "the uncovered EP6–EP15 window is not named"


case("🔴 every number says it is a LOWER BOUND, and names EP23 as the proof",
     _every_number_carries_its_lower_bound_warning)


def _the_settled_ruling_travels_with_the_number():
    """The one door this file must never be used to open (Jodie, 5 and 14 Aug)."""
    with Sandbox(clips=6):
        broll_fault.record(31, ["c01"], "both sides of the rail")
        assert "NOT a case for a b-roll review step" in broll_fault.rate()


case("the number carries the settled ruling: better prompts, never a human looking",
     _the_settled_ruling_travels_with_the_number)


def _reviewing_again_replaces_the_row():
    """A second look at the same episode must not be a second row, or one episode is
    counted twice in both numerator and denominator."""
    with Sandbox(clips=4):
        broll_fault.record(31, [], "")
        broll_fault.record(31, ["c03"], "identical stride")
        text = broll_fault.TALLY.read_text(encoding="utf-8")
        assert text.count("| EP31 |") == 1, f"EP31 has {text.count('| EP31 |')} rows"
        assert broll_fault.rate().startswith("1 faulty of 4 b-roll clips across 1 "), \
            broll_fault.rate()


case("a re-review replaces the episode's row rather than adding a second",
     _reviewing_again_replaces_the_row)


def _faulty_without_why_is_refused():
    try:
        broll_fault.main(["31", "--faulty", "c02"])
    except SystemExit as e:
        assert e.code != 0
        return
    raise AssertionError("a fault was logged with no description — 'c02' six months "
                         "from now tells nobody what to fix")


case("--faulty without --why is refused", _faulty_without_why_is_refused)


def _a_review_that_says_nothing_is_refused():
    try:
        broll_fault.main(["31"])
    except SystemExit as e:
        assert e.code != 0
        return
    raise AssertionError("a bare episode number recorded nothing and said nothing, "
                         "which reads later as 'not looked at yet'")


case("a review with neither --clean nor --faulty is refused",
     _a_review_that_says_nothing_is_refused)


print(f"\nbroll fault tally: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
