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

    print("\n-- 🔴 THE FIVE READINGS THE SECOND ARTICLE FORCED --")
    # EP16 was the only article the gate had met. Run against all seven shipped
    # scripts it produced 39 false alarms on APPROVED, PUBLISHED work. These are
    # the readings that closed them — accurate readings, never loose fallbacks.
    UNITS_CAP = ("x\n---- ARTICLE TEXT BEGINS ----\n"
                 "Won over 1600m at 57kg, beaten 3.9 lengths on September 23, "
                 "rated 2nd of 2020 starters over the 2100m to 2300m range, "
                 "at $100 to $50.\n---- ARTICLE TEXT ENDS ----\n")
    for phrase, why in [
            ("sixteen hundred metres", "a unit-suffixed distance, hundreds reading"),
            ("sixteen hundred", "the same distance with the unit left off"),
            ("one thousand six hundred", "and its cardinal reading"),
            ("fifty seven", "a weight in kilos"),
            ("three point nine", "a DECIMAL, not 'three' and 'nine'"),
            ("twenty third", "a cardinal date read as an ordinal"),
            ("second", "2nd read as a word"),
            ("two thousand and twenty", "the 'and' people say and int_words omits"),
            ("twenty twenty", "and its pair reading"),
            ("twenty one hundred to twenty three hundred", "a range carrying a unit"),
            ("a hundred to fifty", "'a hundred' is 'one hundred'")]:
        check(f"  {why}: {phrase!r}", F.check(f"It was {phrase}.", UNITS_CAP) == [],
              str(F.check(f"It was {phrase}.", UNITS_CAP)))

    print("\n-- and the readings did NOT open a door --")
    for phrase in ("seventeen hundred metres", "four point one", "twenty fourth",
                   "two thousand and thirty", "a hundred to sixty"):
        check(f"  a figure the article does not state is still caught: {phrase!r}",
              len(F.check(f"It was {phrase}.", UNITS_CAP)) == 1,
              str(F.check(f"It was {phrase}.", UNITS_CAP)))

    print("\n-- 'and' joins figures; it is only INSIDE one after hundred/thousand --")
    # EP17: "eleven dollars fifty for number EIGHT AND TWELVE dollars for number
    # nine" — treating "and" as internal glued two real figures into one that no
    # article states.
    two = F.figures("eleven dollars fifty for number eight and twelve dollars")
    check("two separate figures are not glued into one",
          not any("eight and twelve" in f for f in two), str(two))
    check("  but 'two thousand and twenty' stays one figure",
          any(f == "two thousand and twenty"
              for f in F.figures("rated two thousand and twenty")),
          str(F.figures("rated two thousand and twenty")))

    print("\n-- ordinary English is still not a figure --")
    for phrase in ("the third one was better", "half the field never fires",
                   "a quarter of the way up the straight"):
        check(f"  {phrase!r}", F.check(phrase, UNITS_CAP) == [],
              str(F.check(phrase, UNITS_CAP)))

    # ⚠️ BUT A FINISHING POSITION IS A CLAIM ABOUT THE WORLD, SO IT IS TRACED.
    # This case first asserted "he ran on for sixth" was prose — my assumption,
    # not a rule. Saying a horse ran sixth when the article says fourth is
    # exactly the kind of altered figure §0a forbids, and the seven-article table
    # shows tracing ordinals costs nothing: EP14, EP15 and EP16 stay clean and
    # EP11's and EP12's ordinal alarms went away once dates folded properly.
    check("a finishing position IS checked, not waved through",
          len(F.check("he ran on for sixth", UNITS_CAP)) == 1,
          str(F.check("he ran on for sixth", UNITS_CAP)))
    check("  and it passes when the article supports it",
          F.check("he was second", UNITS_CAP) == [],
          str(F.check("he was second", UNITS_CAP)))

    print("\n-- 🔴 A SLASH IS ODDS *AND* A FRACTION (EP18, 7 Aug 2026) --")
    # THE FAULT: EP18's first live draft was FAITHFUL and the gate blocked it. The
    # article says "an average dividend of $2.80 (about 7/4)"; the writer wrote
    # "about seven to four", which is how a price is said. The slash rule only
    # knew the FRACTION meaning (EP16's 1/9 = "one ninth"), so it produced "seven
    # quarters" and "seven in four" and matched neither.
    #     THE DRAFT WAS MORE CORRECT THAN THE CHECKER.
    SLASH_CAP = ("x\n---- ARTICLE TEXT BEGINS ----\n"
                 "An average dividend of $2.80 (about 7/4). The probability is "
                 "1/9, and three times that is 1/3.\n---- ARTICLE TEXT ENDS ----\n")
    for phrase, why in [
            ("seven to four", "7/4 read as ODDS — the EP18 case"),
            ("one ninth", "1/9 still reads as a FRACTION"),
            ("one in nine", "and in its other spoken form"),
            ("one third", "1/3 as a fraction"),
            ("one to nine", "a slash may also be said as odds")]:
        check(f"  {why}: {phrase!r}",
              F.check(f"It was {phrase}.", SLASH_CAP) == [],
              str(F.check(f"It was {phrase}.", SLASH_CAP)))

    print("\n-- and the WIDENING did not make it go soft --")
    # A gate that goes quiet is worse than one that false-alarms. Adding a reading
    # to what the ARTICLE may be said as must not admit a price it never states.
    for phrase in ("eleven to four", "seven to five", "nine to two",
                   "two ninths", "eight to four"):
        check(f"  a price the article never states is still caught: {phrase!r}",
              len(F.check(f"It was {phrase}.", SLASH_CAP)) == 1,
              str(F.check(f"It was {phrase}.", SLASH_CAP)))

    print("\n-- 🔴 BOTH HALVES, ACROSS EVERY SHIPPED EPISODE --")
    # "Zero false alarms" alone proves nothing: a gate that passes everything
    # scores zero too. Each script is ALSO planted with a racing price its own
    # article never states, and the gate must find it.
    clean, planted_caught, planted_tried = [], 0, 0
    for n in range(11, 18):
        cap = capture(n)
        sc = shipped_script(n)
        if not cap or not sc:
            continue
        base = F.check(sc, cap)
        if not base:
            clean.append(n)
        price = next((c for c in ("eleven to four", "fifteen to eight",
                                  "thirty three to one", "sixty six to one")
                      if F.check(f"He was at {c}.", cap)), None)
        if price:
            planted_tried += 1
            after = F.check(sc + f"\n\nHe was sent out at {price}.\n", cap)
            if any(price in b for b in after if b not in base):
                planted_caught += 1
    check("a fabricated price is caught in EVERY shipped episode",
          planted_tried > 0 and planted_caught == planted_tried,
          f"{planted_caught}/{planted_tried}")
    check("  and the articles that were clean stay clean",
          set(clean) >= {14, 15, 16}, f"clean: {clean}")

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
