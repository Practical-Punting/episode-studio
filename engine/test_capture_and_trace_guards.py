"""SITTING 1 — the two episode.json guards, proved FAIL-FIRST.

CLAUDE.md 4b: a guard is not trustworthy until you have watched it FAIL. Every case
below writes a deliberately-broken input FIRST and asserts the guard catches it, then
asserts a good input passes. A test that only ever sees good input proves nothing.

  (a) preflight_cards.capture_reference_faults — `source` must name a capture that
      exists, because a missing capture switches the whole trace regime OFF and the
      pre-flight then reports CLEAN having checked nothing (EP18, 8 Aug 2026).
  (b) author_cards.check_dead_trace — a trace key matching no content value is a dead
      citation. EP18's nine 0-based keys were all dead; it surfaced as eight unrelated
      trace faults.

Run: python engine/test_capture_and_trace_guards.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import author_cards as ac        # noqa: E402
import preflight_cards as pc     # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if detail:
        print(f"          {detail}")
    if not cond:
        FAILED.append(name)


GOOD_SOURCE = ("'THOSE TOP 6 FAVOURITES', Practical Punting, DECEMBER 2006 (PP-owned). "
               "Verbatim source: docs/EP18-source-article-those-top-6-favourites.md")
BAD_SOURCE = ("'THOSE TOP 6 FAVOURITES', Practical Punting, DECEMBER 2006 (PP-owned). "
              "Verbatim source capture: G:\\My Drive\\PP Videos\\docs\\"
              "EP18-source-article-those-top-6-favourites.md - note that this capture "
              "lives in the SHARED PP Videos docs folder.")
ARTICLE = "the fifth favourite won 12 per cent on turnover and the third won 5 per cent"
# A REALISTIC capture carries the article-text markers. The first version of this test
# used the bare sentence, and `capture_faults` rightly objected — the guard was correct
# and the FIXTURE was wrong. (CLAUDE.md 4a: test a check against inputs as they exist at
# the moment it runs, not against the tidiest thing to hand.)
CAPTURE = (f"notes about the scan\n\n{pc.MARKER_BEGIN}\n{ARTICLE}\n{pc.MARKER_END}\n")

print("\n=== (a) THE CAPTURE REFERENCE MUST BE REAL ===\n")

# --- FAIL FIRST: the exact EP18 wording, an absolute Windows path ---------
bad = {"source": BAD_SOURCE, "cards": []}
f = pc.capture_reference_faults(bad, None)
check("a bare Windows path is REJECTED", len(f) == 1,
      f.__len__() and f[0].split(".")[0][:96])
check("...and the message shows the operator what the field says",
      bool(f) and "source currently reads" in f[0])

# --- FAIL FIRST: named, but the file is not there -------------------------
named_missing = {"source": GOOD_SOURCE, "cards": []}
f2 = pc.capture_reference_faults(named_missing, None, capture_looked_for=True)
check("named but unreadable is REJECTED (caller looked)", len(f2) == 1,
      f2[0][:96] if f2 else "")
check("...and it is a DIFFERENT message from 'names nothing'",
      bool(f) and bool(f2) and f[0] != f2[0])
# and the narrowing that keeps it from halting good episodes:
check("...but NOT when the caller never looked",
      pc.capture_reference_faults(named_missing, None) == [],
      "a caller that supplied no capture has not discovered a missing file")

# --- and only now, the good case -----------------------------------------
good = {"source": GOOD_SOURCE, "cards": []}
check("a real relative capture PASSES", pc.capture_reference_faults(good, CAPTURE) == [])

# --- it must actually BLOCK the run, not just warn ------------------------
res_bad = pc.preflight_cards(bad, capture_text=None, article_norm=None)
res_good = pc.preflight_cards(good, capture_text=CAPTURE, article_norm=ARTICLE)
check("preflight_cards BLOCKS on the broken source", len(res_bad["blockers"]) >= 1,
      f"{len(res_bad['blockers'])} blocker(s)")
check("preflight_cards does not block on the good one",
      len(res_good["blockers"]) == 0, f"{res_good['blockers']}")

print("\n=== (b) A TRACE KEY MATCHING NOTHING IS A FAULT ===\n")

BARS = [{"label": "Third favourite", "value": "5", "note": "5 per cent profit", "tone": ""},
        {"label": "Fifth favourite", "value": "12", "note": "12 per cent profit", "tone": "hi"}]

# --- FAIL FIRST: EP18's real shape — 0-based keys -------------------------
zero_based = {"id": "C9", "content": {"bars": BARS},
              "trace": {"bars[0].value": ARTICLE, "bars[1].value": ARTICLE}}
p = ac.check_dead_trace(zero_based)
check("a 0-based key is REJECTED", any("bars[0].value" in x for x in p),
      p[0][:110] if p else "nothing reported")
check("...and it names the 1-based range", bool(p) and "bars[1] to bars[2]" in p[0])
check("...and it explains the 0-based cause", bool(p) and "0-based key" in p[0])
check("the in-range key bars[1].value is NOT reported",
      not any("bars[1].value" in x for x in p))

# --- the severity split: dangerous vs merely untidy -----------------------
# A misaddressed citation (real list, wrong index) is a BLOCKER — that is EP18's
# fault. A key addressing nothing at all is a WARNING: EP16 c02 shipped with
# trace["Three chances"], and halting on that would block an episode that was fine.
nonsense = {"id": "C4", "content": {"cols": [{"k": "a", "v": "5%"}]},
            "trace": {"Three chances": ARTICLE}}
check("a key addressing nothing does NOT halt", ac.check_dead_trace(nonsense) == [])
p2 = ac.check_stray_trace(nonsense)
check("...but it IS reported as a warning", len(p2) == 1, p2[0][:110] if p2 else "")
check("a misaddressed index is NOT downgraded to a warning",
      ac.check_stray_trace(zero_based) == [],
      "bars[0].value stays a blocker, not a warning")

# --- FAIL FIRST: an index past the end of the list ------------------------
past_end = {"id": "C6", "content": {"bars": BARS},
            "trace": {"bars[3].value": ARTICLE}}
check("an index past the end is REJECTED", len(ac.check_dead_trace(past_end)) == 1)

# --- and only now, the good cases ----------------------------------------
one_based = {"id": "C9", "content": {"bars": BARS},
             "trace": {"bars[1].value": ARTICLE, "bars[2].value": ARTICLE}}
check("correct 1-based keys PASS", ac.check_dead_trace(one_based) == [])
whole_list = {"id": "C9", "content": {"bars": BARS}, "trace": {"bars": ARTICLE}}
check("a whole-list key PASSES", ac.check_dead_trace(whole_list) == [])
headline = {"id": "C1", "content": {"cells": [{"k": "a", "v": "660"}]},
            "headline": "SIX HUNDRED", "trace": {"headline": ARTICLE, "cells": ARTICLE}}
check("headline/eyebrow keys PASS", ac.check_dead_trace(headline) == [])
check("a card with no trace at all is not reported",
      ac.check_dead_trace({"id": "X", "content": {"bars": BARS}}) == [])

print(f"\n{'=' * 66}")
print(f"{'ALL GUARDS PROVED (fail-first, then pass)' if not FAILED else 'FAILURES: ' + str(FAILED)}")
sys.exit(1 if FAILED else 0)
