#!/usr/bin/env python3
"""Piece 4 — every figure Gordon speaks must be the article's own figure.

THE CASES THAT MATTER, and each names what it stands against:

    the_approved_script_passes  — EP16 AS SHIPPED is approved, published and
                                  correct by construction. Anything reported
                                  against it is THIS GATE being wrong, not the
                                  script. It is the first case for that reason.
    an_altered_price_is_caught  — 8-1 changed to 5-1 is the fault the gate
                                  exists for: a real-looking racing price that
                                  the article never states.
    both_fraction_idioms_live   — the article writes 1/9; "one ninth" and "one
                                  in nine" are both house-correct, the second by
                                  demonstration (EP16 as shipped says it).
    the_byline_line_and_no_more — Jodie's ruling, 7 Aug: the date is traceable;
                                  the scan-repair commentary is not.

Reads the real captures and the real EP16 script. Writes nothing, changes nothing.
Run: python engine/test_script_fidelity.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import script_fidelity as F                                            # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def capture(n: int) -> str | None:
    hits = sorted((PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    return hits[0].read_text(encoding="utf-8") if hits else None


def episode_dir(n: int) -> Path | None:
    """Resolve an episode folder BY NUMBER, never by a written-out name.

    The stage-8 close-out RENAMES every published episode's folder, so a literal
    is a fuse: it passes for weeks and then fails the day the process does the
    thing it is designed to do. `test_no_hardcoded_episode_paths.py` caught this
    file's first version for exactly that — correctly.
    """
    hits = sorted(p for p in PP.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else None


def shipped_script(n: int) -> str | None:
    d = episode_dir(n)
    if d is None:
        return None
    p = d / "docs/spoken-words.txt"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def main():                                                            # noqa: C901
    cap16 = capture(16)
    ep16 = shipped_script(16)
    if not cap16 or not ep16:
        print("  --   skipped: EP16's capture or script is not reachable")
        return 0

    print("\n-- 🔴 THE APPROVED, PUBLISHED SCRIPT PASSES --")
    # If this fails, the gate is wrong. EP16 shipped.
    problems = F.check(ep16, cap16)
    for p in problems:
        print(f"       {p}")
    check("EP16 as shipped has NO untraceable figure", problems == [],
          f"{len(problems)} reported")
    check("  and the gate did look — it found figures to check",
          len(F.figures(ep16)) > 50, f"{len(F.figures(ep16))} figures")

    print("\n-- 🔴 THE RULING: THE BYLINE LINE, AND NOTHING ELSE FROM THE HEADER --")
    b = F.byline(cap16)
    check("the byline line is found", b is not None and b.startswith("By "))
    check("  it carries the author", b is not None and "Dedman" in b)
    check("  and the date", b is not None and "1988" in b)
    check("EP16 as shipped says the date out loud",
          "nineteen eighty" in " ".join(F.figures(ep16)))
    # Prove the ruling is load-bearing: take the byline away and the approved
    # script fails. Without this the case would pass for the wrong reason.
    without = "\n".join(ln for ln in cap16.splitlines()
                        if not ln.strip().startswith("By "))
    lost = F.check(ep16, without)
    check("  and WITHOUT the byline the approved script would fail",
          len(lost) == 1 and "nineteen eighty eight" in lost[0], str(lost))
    src = F.source_text(cap16)
    check("the scan-repair commentary is NOT traceable source",
          "the image is the primary source" not in src)
    check("  nor is the capture's note about correcting a scanner",
          "IT IS CORRECTING A SCANNER" not in src)
    check("  but the article body IS", "each way" in src.lower())

    print("\n-- 🔴 AN ALTERED RACING PRICE IS CAUGHT AND NAMED --")
    # ⚠️ THE FIRST VERSION OF THIS CASE ALTERED 8-1 TO 5-1 AND THE GATE PASSED IT
    # — CORRECTLY. The article states 5-1 as well (its prices are 2-1, 3-1, 4-1,
    # 5-1, 6-1, 6-4, 7-1, 7-2, 7-4, 8-1, 9-2, 13-4, 23-1). A "wrong" value that
    # is really in the source proves nothing, and would have been a green case
    # standing guard over nothing. 11-4 is a real racing price this article never
    # states, which is exactly the fault worth catching.
    good = "The theoretical probability of any given horse's winning is one ninth. " \
           "That is, odds of eight to one."
    bad = good.replace("eight to one", "eleven to four")
    check("the true price passes", F.check(good, cap16) == [],
          str(F.check(good, cap16)))
    got = F.check(bad, cap16)
    check("  the altered price is CAUGHT", len(got) == 1, str(got))
    check("  and the message names the figure",
          bool(got) and "eleven to four" in got[0], str(got))
    check("  and says the article never states it",
          bool(got) and "never states that figure" in got[0])
    check("  while a price the article DOES state is left alone",
          F.check(good.replace("eight to one", "five to one"), cap16) == [])

    print("\n-- an invented figure is caught too --")
    invented = "Roughly ninety-four per cent of favourites are beaten."
    got = F.check(invented, cap16)
    check("a figure that is nowhere in the article is caught", len(got) >= 1,
          str(got))

    print("\n-- 🔴 BOTH FRACTION IDIOMS SURVIVE (the article writes 1/9) --")
    for phrase in ("one ninth", "one in nine", "three fifths", "three in five",
                   "one third", "one in three"):
        check(f"  {phrase!r} traces", F.check(f"That is {phrase}.", cap16) == [],
              str(F.check(f"That is {phrase}.", cap16)))

    print("\n-- 🔴 GENUINE ODDS SURVIVE, IN THE FORMS WE SPEAK THEM --")
    for phrase in ("eight to one", "six to four on", "two to one", "seven to two",
                   "twenty three to one", "four to one"):
        check(f"  {phrase!r} traces", F.check(f"You get {phrase}.", cap16) == [],
              str(F.check(f"You get {phrase}.", cap16)))

    print("\n-- money reads with or without the second unit --")
    for phrase in ("four hundred dollars to two hundred",
                   "four hundred dollars to two hundred dollars"):
        check(f"  {phrase!r} traces", F.check(f"He takes {phrase}.", cap16) == [],
              str(F.check(f"He takes {phrase}.", cap16)))

    print("\n-- it does not cry wolf on ordinary English --")
    for phrase in ("half the field never fires",
                   "he finished in third place and was never nearer",
                   "a quarter of the way up the straight"):
        check(f"  {phrase!r} is not treated as a figure",
              F.check(phrase, cap16) == [], str(F.check(phrase, cap16)))

    print("\n-- a clause boundary ends a figure --")
    # Without this, "loses a hundred dollars: a three hundred dollar return"
    # folds into one run and is reported untraceable — the reader's fault,
    # blamed on the writer.
    line = ("If the horse is beaten, but runs a place, he still loses a hundred "
            "dollars: a three hundred dollar return for a four hundred dollar outlay.")
    check("figures are not merged across punctuation", F.check(line, cap16) == [],
          str(F.check(line, cap16)))

    print("\n-- omission is not alteration (§0a: the video SELECTS) --")
    check("a script that states NO figures passes",
          F.check("Gordon talks about the shape of a race.", cap16) == [])

    print("\n-- an unusable capture is a blocker, never a quiet pass --")
    check("no article text -> it says so rather than passing",
          len(F.check("He got eight to one.", "no markers here")) == 1)

    print("\n-- the render path was NOT touched (Jodie's ruling) --")
    import align_to_script as A
    check("spoken_form still renders 8-1 the old way (unchanged)",
          "eight to one" not in A.spoken_form("8-1"))
    check("  and the racing layer lives here instead",
          "eight to one" in F.fold("8-1"))
    check("  MIN_MATCH is untouched", A.MIN_MATCH == 0.85)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
