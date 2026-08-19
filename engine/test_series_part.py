#!/usr/bin/env python3
"""ONE PARSER FOR "IS THERE A SERIES PART AT THE END OF THIS TITLE?" (EP34, 20 Aug 2026.)

    python engine/test_series_part.py

There were TWO, in two modules, and they disagreed:

    providers._PART_TAIL   \\s*[—–\\-:·]?\\s*\\b(Part\\s+\\d+)\\s*$      separators, no brackets
    packaging_gate.SERIES_PART  \\s*[(\\[]?\\s*\\bpart\\s+(\\d+|[ivxl]+)\\b\\s*[)\\]]?\\s*$   brackets, no separators

**Neither was a superset of the other, and each was right about what the other missed.**
So for `The Don Scott Interview (Part 1)` the SEATER found no part and left it inside
`packaging.hook`; the hook became the headline; and the GATE — reading with the other
pattern, which does know brackets — correctly refused a cover printing a series part in
the headline. **One half of the studio could not read what the other half wrote.**
EP34 sat flagged **nine and a quarter hours** with EP35 and EP32 waiting behind it.

⛔ **THE TWO FIXES JODIE REJECTED, so nobody re-proposes them:**
  · **Re-punctuating the title** to `- Part 1`. PP's own headline reads "(Part 2)", and
    the rule is that the title IS the website's headline. It fights her own convention
    and returns on every multi-part article.
  · **Teaching `_PART_TAIL` about brackets.** Its docstring admitted it knew only the
    notations it had SEEN — fault 7 for the third time in two days (metres, dollars,
    per cent, now this). Adding the missing item leaves the shape.

✅ **The fix is that there is only one.** `providers._split_part` delegates to
`packaging_gate.strip_part`. The pattern there is the UNION and not one character more.

⚠️ **THE COMMA IS DELIBERATELY EXCLUDED.** `"Thing, Part 5"` has always kept its comma on
the stem. A fix that quietly re-derives a SHIPPED episode's hook is worse than the bug.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import packaging_gate as pg                                           # noqa: E402
from providers import _split_part                                     # noqa: E402

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


# The pattern providers used to carry, kept ONLY so the control can still go red.
OLD_PART_TAIL = re.compile(r"\s*[—–\-:·]?\s*\b(Part\s+\d+)\s*$", re.I)


def _old_split(title):
    m = OLD_PART_TAIL.search(title or "")
    if not m:
        return (title or "").strip(), None
    return title[:m.start()].strip(), m.group(1).strip()


# ── 1. RED FIRST — the old seater could not see EP34's part. ──────────────────
def _red_first():
    name, part = _old_split("The Don Scott Interview (Part 1)")
    assert part is None and name == "The Don Scott Interview (Part 1)", (
        f"the OLD pattern split EP34's title ({name!r}, {part!r}) — it never did, so "
        f"this control can no longer see the bug and every pass below is meaningless")


case("RED FIRST — the old seater pattern does NOT see '(Part 1)'", _red_first)


# ── 2. …and the shipped one does. ────────────────────────────────────────────
def _ep34_now_splits():
    assert _split_part("The Don Scott Interview (Part 1)") == \
        ("The Don Scott Interview", "Part 1"), _split_part("The Don Scott Interview (Part 1)")


case("EP34's bracketed part now splits, so the hook loses it", _ep34_now_splits)


# ── 3. REGRESSION — every form that worked must work IDENTICALLY. ────────────
def _separators_unchanged():
    """These are what `_PART_TAIL` was written for. A fix that re-derives a shipped
    episode's hook is worse than the bug, so each must land exactly where it did."""
    for title, expect in [
            ("The Don Scott Interview - Part 2", ("The Don Scott Interview", "Part 2")),
            ("Hidden Aces — Part 2",             ("Hidden Aces", "Part 2")),
            ("Thing — Part 3",                   ("Thing", "Part 3")),
            ("Prices By Points - Part 2",        ("Prices By Points", "Part 2")),
            ("Track Secrets Part 1",             ("Track Secrets", "Part 1")),
            ("10 Systems For Action Hungry Punters Part 1",
             ("10 Systems For Action Hungry Punters", "Part 1"))]:
        assert _split_part(title) == expect, f"{title!r} -> {_split_part(title)!r}"


def _comma_still_kept():
    """Never widened to the comma — this is the one that guards shipped hooks."""
    assert _split_part("Thing, Part 5") == ("Thing,", "Part 5"), _split_part("Thing, Part 5")
    assert "," not in pg.SERIES_PART.pattern.split("part")[0], \
        "the comma has been added to the separator class — that re-derives shipped hooks"


def _a_title_about_parts_is_not_a_series():
    """Anchored at the END so 'The Best Part of Betting' is never mistaken for one."""
    assert _split_part("The Best Part of Betting") == ("The Best Part of Betting", None)
    assert _split_part("Part of the Game") == ("Part of the Game", None)


case("every separator form splits exactly as it always did", _separators_unchanged)
case("'Thing, Part 5' still keeps its comma (shipped hooks unmoved)", _comma_still_kept)
case("a title with 'part' in the middle is not a series", _a_title_about_parts_is_not_a_series)


# ── 4. THERE IS ONLY ONE PARSER. This is the actual fix. ─────────────────────
def _providers_has_no_local_pattern():
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    body = src[src.index("def _split_part"):]
    body = body[:body.index("\ndef ")]
    assert "re.compile" not in body and "_PART_TAIL.search" not in body, (
        "providers._split_part has grown its own pattern again. That is the fault "
        "itself, not the notation — two parsers WILL drift apart.")
    assert "strip_part" in body, "_split_part no longer delegates to the one parser"


def _the_two_agree_everywhere():
    """The invariant that makes it one concept: the seater and the grader must never
    disagree about where a series part begins."""
    for t in ["The Don Scott Interview (Part 1)", "The Don Scott Interview - Part 2",
              "Track Secrets (Part 4)", "Hidden Aces — Part 2", "Thing, Part 5",
              "Bet Your Own Prices Part 1", "The Best Part of Betting",
              "Something Part IV", "Nothing Here At All"]:
        a = _split_part(t)
        b = pg.strip_part(t)
        assert a[0] == b[0] and (a[1] or "") == b[1], \
            f"{t!r}: seater {a!r} vs grader {b!r} — they have drifted apart again"


case("providers carries no pattern of its own — it delegates",
     _providers_has_no_local_pattern)
case("the seater and the grader agree on every form", _the_two_agree_everywhere)


# ── 5. THE INERT SWEEP, and the ONE published episode it also moves. ─────────
def _only_the_bracket_form_moves():
    """Run both readings over every title shape the studio has used.

    🔴 EP24 ('Track Secrets (Part 4)') ALSO changes, and that is recorded rather than
    hidden: it SHIPPED with this fault — its `packaging.hook` is 'Track Secrets (Part 4)',
    its `cover.part` is None and its thumbnail printed '(PART 4)' AND 'Part 4'. That is
    verbatim the fault `packaging_gate` rule 5 names EP24 for. It is published, and a
    guard prevents recurrence without obliging us to go back, so nothing was done to it.
    """
    moved = []
    for t in ["The 12 Vital Form Factors — Part 1", "Hidden Aces — Part 1",
              "Hidden Aces — Part 2", "The Ratings Game — Part 1",
              "The Meaning of Form — Part 1", "Squeeze Those Odds! — Part 1",
              "Each-Way Betting Forever! — Part 2",
              "10 Systems For Action Hungry Punters Part 1", "Track Secrets Part 1",
              "Track Secrets Part 2", "Track Secrets Part 3", "Track Secrets (Part 4)",
              "Bet Your Own Prices Part 1", "Prices By Points - Part 2",
              "The Don Scott Interview - Part 2", "The Don Scott Interview (Part 1)",
              "Try The Triple Trick Attack", "How Bookies Make A Book", "6-point Star"]:
        if _split_part(t) != _old_split(t):
            moved.append(t)
    assert moved == ["Track Secrets (Part 4)", "The Don Scott Interview (Part 1)"], (
        f"the sweep moved {moved!r}. Exactly two titles may change — EP34, which is the "
        f"point, and EP24, which shipped with the same fault and is published. Anything "
        f"else means a shipped episode's hook would be silently re-derived.")


case("the sweep moves ONLY the two bracketed titles", _only_the_bracket_form_moves)


# ── 6. IT MUST WORK IN THE INTERPRETER THE ENGINE ACTUALLY RUNS. ────────────
def _works_with_only_engine_on_the_path():
    """🔴 THIS FILE CANNOT PROVE IT BY ITSELF — fault #4, and it caught me.

    `_split_part` imports `packaging_gate`, which lives in the SKILL's scripts folder.
    That folder is on `sys.path` when this test runs, because the test put it there —
    so a missing `sys.path.insert` inside `_split_part` passes every case above and
    then raises ModuleNotFoundError on the real build. **It did exactly that**: the
    cases above were green while a sandbox with only `engine/` on the path blew up.
    So this runs it in a subprocess that imports nothing but `providers`.
    """
    import subprocess
    code = ("import sys; sys.path.insert(0, r'%s')\n"
            "from providers import _split_part\n"
            "assert _split_part('X (Part 1)') == ('X', 'Part 1'), _split_part('X (Part 1)')\n"
            "print('ok')") % str(HERE)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, (
        "_split_part fails in an interpreter with only engine/ on the path — the "
        "engine's own interpreter. This is what the build sees:\n"
        + (r.stderr or "").strip()[-400:])


case("_split_part works with ONLY engine/ on the path (the engine's own interpreter)",
     _works_with_only_engine_on_the_path)

print(f"\nseries part: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
