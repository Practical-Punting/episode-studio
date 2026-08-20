#!/usr/bin/env python3
"""ONE DEFINITION OF A SERIES PART, USED BY ALL THREE READERS. (EP34, 20 Aug 2026.)

    python engine/test_one_part_definition.py

EP34 halted THREE times in a single build. Two of the three were the same root: **how
the series part is written.**

There were THREE readers of "a series part" and they disagreed:

    providers._split_part              knew separators, not brackets   (E49 — unified)
    packaging_gate.strip_part          knew brackets and roman numerals
    youtube_title._fold                knew a HYPHEN, not brackets     (E53 — this file)

E49 unified the first two. `_fold` was left, and it is what halted EP34 the third time:
the title card is recomposed as `setup + payoff + " - " + part`, so
`'The Don Scott Interview (Part 1)'` folded to `...(PART 1)` while the card folded to
`...PART 1`. **The same name, reported as two different names** — and the raw title, an
INPUT, was blamed for disagreeing with a DERIVED output whose separator the check itself
had invented. **PP's own headline reads "(Part 2)", so the bracket form had never once
passed this check.**

⭐ **THE LAW THIS IS THE FOURTH INSTANCE OF** (E47, E49/50, E53):
> **WHEN TWO PARTS OF THE SYSTEM DISAGREE ABOUT THE SAME IDEA, UNIFY THE DEFINITION —
> DO NOT TEACH ONE OF THEM THE OTHER'S CASES.**
Teaching `_fold` about brackets would have left three readers and a longer list, and a
fourth reader would arrive next week. CLAUDE.md #2 and #7 meeting; it has now paid four
times in three days.

⛔ **NORMALISING THE TITLE AT THE WORDS GATE IS A HOUSE-STYLE QUESTION, NOT THIS FIX.**
It would also have prevented halts 1 and 3 — but it means changing what Jodie typed, so
it is only honest AT THE GATE where she approves the house form. Parked deliberately:
*normalising makes readers agree by NARROWING the input; one parser makes them agree by
WIDENING what they can read.*
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import packaging_gate as pg                                           # noqa: E402
import youtube_title as yt                                            # noqa: E402
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


def old_fold(s: str) -> str:
    """`_fold` as it stood before E53 — kept ONLY so the control can still go red."""
    s = re.sub(r"[‐-―−-]+", "-", (s or ""))
    s = re.sub(r"\s*-\s*", " ", s)
    return re.sub(r"\s+", " ", s).strip(" -").upper()


TITLE = "The Don Scott Interview (Part 1)"
CARD = "THE DON SCOTT INTERVIEW - Part 1"


# ── 1. RED FIRST. ────────────────────────────────────────────────────────────
def _red_first():
    assert old_fold(TITLE) != old_fold(CARD), (
        "the OLD fold now agrees on EP34's two names — it never did, so this control "
        "can no longer see the bug and every pass below is meaningless")


case("RED FIRST — the old fold calls one name two names", _red_first)


# ── 2. …and the shipped one agrees. ─────────────────────────────────────────
def _now_agrees():
    assert yt._fold(TITLE) == yt._fold(CARD), \
        f"{yt._fold(TITLE)!r} != {yt._fold(CARD)!r}"


case("EP34's title and title card are now ONE name", _now_agrees)


# ── 3. EVERY NOTATION READS THE SAME, THROUGH ALL THREE READERS. ────────────
SHAPES = ["Track Secrets (Part 4)", "Track Secrets - Part 4", "Track Secrets, Part 4",
          "Track Secrets — Part 4", "Track Secrets Part 4", "Track Secrets: Part 4"]


def _all_shapes_fold_alike():
    got = {t: yt._fold(t) for t in SHAPES}
    assert len(set(got.values())) == 1, (
        "the notations do not fold to one name:\n      "
        + "\n      ".join(f"{k!r} -> {v!r}" for k, v in got.items()))


def _all_three_readers_agree():
    """The invariant that makes it ONE definition rather than three that happen to match
    today. If a fourth notation is ever added, it must reach all three at once."""
    for t in SHAPES:
        a = pg.strip_part(t)
        b = _split_part(t)
        assert a[0] == b[0] and a[1] == (b[1] or ""), \
            f"{t!r}: gate {a!r} vs seater {b!r}"
        assert a[1].upper() in yt._fold(t), \
            f"{t!r}: the fold {yt._fold(t)!r} lost the part {a[1]!r}"


case("every notation folds to ONE name", _all_shapes_fold_alike)
case("gate, seater and fold all read the same part", _all_three_readers_agree)


# ── 4. NO SECOND DEFINITION MAY REAPPEAR. ───────────────────────────────────
def _fold_has_no_part_logic_of_its_own():
    src = (SCRIPTS / "youtube_title.py").read_text(encoding="utf-8")
    body = src[src.index("def _fold("):]
    body = body[:body.index("\ndef ")]
    assert "strip_part" in body or "_the_one_part_reader" in body, \
        "_fold no longer uses the one definition"
    assert "part" not in body.lower().split('"""')[-1] or "_the_one_part_reader" in body, \
        "_fold has grown its own part handling again"
    assert "re.compile" not in body, \
        "_fold has grown a pattern of its own — that is the fault, not the notation"


case("_fold carries no part definition of its own", _fold_has_no_part_logic_of_its_own)


# ── 5. NAMES THAT ARE NOT SERIES PARTS ARE UNTOUCHED. ───────────────────────
def _real_hyphens_still_fold():
    """The 11 Aug behaviour this function was written for must survive."""
    assert yt._fold("Each-Way Betting Forever!") == yt._fold("Each Way Betting Forever!")
    assert yt._fold("Hidden Aces") != yt._fold("Squeeze Those Odds")
    assert yt._fold("The Best Part of Betting") == "THE BEST PART OF BETTING", \
        "a title with 'part' in the middle was mistaken for a series position"


case("real hyphens and non-series names fold exactly as before", _real_hyphens_still_fold)


# ── 6. THE INERT CONTROL — nothing shipped may change its verdict. ──────────
def _only_ep34_changes():
    """🔴 THE ONE THAT MATTERS. This check runs over every episode's episode.json, so a
    change here can re-open a finished episode. EP24 was caught this way on E49."""
    # ⚠️ BY NUMBER, via ep_paths — never a written-out folder name. The stage-8
    # close-out RENAMES a folder on publish (`PP-EP24` -> `PP-EP24-Track-Secrets-Part-4`),
    # so a literal path passes for weeks and breaks ON THE DAY THE PROCESS SUCCEEDS.
    from ep_paths import PP, episode_dir
    if not PP.is_dir():
        raise AssertionError(f"{PP} is not reachable — this control did not run")
    changed, checked = [], 0
    for n in range(1, 60):
        d = episode_dir(n) / "docs/episode.json"
        if not d.is_file():
            continue
        try:
            e = json.loads(d.read_text(encoding="utf-8"))
        except Exception:                                             # noqa: BLE001
            continue
        checked += 1
        names = yt.episode_names(e)
        was = "FAULT" if len({old_fold(v) for v in names.values()}) > 1 else "clean"
        now = "FAULT" if yt.check_one_name(e) else "clean"
        if was != now:
            changed.append((f"EP{n}", was, now))
    assert checked >= 20, f"only {checked} episodes were readable — control too weak"
    assert all(w == "FAULT" and n == "clean" for _, w, n in changed), \
        f"an episode's verdict got WORSE: {changed}"
    assert len(changed) == 1, (
        f"{len(changed)} episodes changed verdict, expected exactly one (EP34): "
        f"{changed}. A fix that re-opens or silently repairs a shipped episode is worse "
        f"than the bug.")


case("INERT — of every episode on disk, only EP34's verdict changes (FAULT -> clean)",
     _only_ep34_changes)


# ── 7. It must work in the engine's own interpreter. ───────────────────────
def _clean_interpreter():
    """fault #4 — `packaging_gate` is not guaranteed on the path. This caught the E49
    delegation this morning, so the same control guards this one."""
    import subprocess
    code = (f"import sys; sys.path.insert(0, r'{SCRIPTS}')\n"
            "import youtube_title as yt\n"
            "assert yt._fold('X (Part 1)') == yt._fold('X - Part 1'), 'folds differ'\n"
            "print('ok')")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, (r.stderr or "").strip()[-400:]


case("_fold works in an interpreter that imported nothing else", _clean_interpreter)

print(f"\none part definition: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
