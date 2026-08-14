"""test_spoken_numbers.py — a spoken figure equals its digits, and an invented one
still blocks.

    EP21, 11 Aug 2026. The article says "more than 2210 m in circumference" and
    "the 1200 m and 1250m journeys". The drafting pass wrote them the way an
    Australian says a distance — "twenty two hundred and ten", "twelve hundred and
    fifty" — and the fidelity gate called all three inventions. The writer refused
    to mangle Hugh's measurements and HALTED, which was the right call and cost the
    episode a drafting cycle.

THE CAUSE WAS ONE MISSING READING, IN FOUR DISGUISES. A four-figure number is said
three ways and the fold offered two: `_pairs` gives the YEAR reading ("twenty two
ten") and `int_words` the CARDINAL ("two thousand two hundred and ten"). The
HUNDREDS reading — the one people actually use for a distance — was not there.

⚠️ AND THE FIX IS A READING, NOT A VALUE COMPARISON. Normalising both sides to
numbers would be simpler and would open a hole this studio has ruled shut:
FRACTIONAL ODDS ARE LOCKED (Jodie, 9 Aug 2026) — `6/4` must never become 1.5, in
either direction. A reading turns the article's DIGITS into words a person would
say; it can never turn one figure into a different figure. The odds cases below are
in this suite to keep that true.

Run: python engine/test_spoken_numbers.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import script_fidelity as sf                                     # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))
M = sf.MARKER_BEGIN
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def says(article: str, spoken: str) -> bool:
    """Would the gate accept `spoken` from a script, given `article` as the source?"""
    return sf._contiguous(spoken, sf.haystacks(f"header\n{M}\n{article}\n"))


def main():
    print("-- THE READING THAT WAS MISSING: N hundred and M --")
    for art, spoken in [
        ("the track is 2210 m in circumference", "twenty two hundred and ten"),
        ("the 1250m journey",                    "twelve hundred and fifty"),
        ("the 1100 m start",                     "eleven hundred"),
        ("run over 1600m",                       "sixteen hundred"),
        ("a 2400 m staying race",                "twenty four hundred"),
        ("back in 1988",                         "nineteen hundred and eighty eight"),
        ("it paid $1250",                        "twelve hundred and fifty dollars"),
    ]:
        check(f"{spoken!r} reads {art.split()[-1]}", says(art, spoken))

    print("\n-- and the OTHER readings still work, because none was replaced --")
    for art, spoken in [
        ("back in 1988",              "nineteen eighty eight"),          # the year
        ("back in 1988",              "one thousand nine hundred and eighty eight"),
        ("the 1250m journey",         "one thousand two hundred and fifty"),
        ("the track is 2210 m round", "two thousand two hundred and ten"),
        ("108,633 bytes off the wire",
         "one hundred and eight thousand six hundred and thirty three"),
        ("a strike rate of 24 per cent", "twenty four per cent"),
        ("the 4th race",              "fourth"),
        ("2100-2300m races",          "twenty one hundred to twenty three hundred"),
    ]:
        check(f"  {spoken[:44]!r}", says(art, spoken))

    print("\n-- 🔴 IT MUST STILL CATCH AN INVENTED NUMBER. This is the guardrail. --")
    for art, spoken in [
        ("the track is 2210 m round", "twenty two hundred and twenty"),   # 2220
        ("the track is 2210 m round", "twenty three hundred and ten"),    # 2310
        ("the 1250m journey",         "thirteen hundred and fifty"),      # 1350
        ("the 1250m journey",         "twelve hundred and sixty"),        # 1260
        ("back in 1988",              "nineteen eighty nine"),            # 1989
        ("back in 1988",              "nineteen hundred and eighty nine"),
        ("a strike rate of 24 per cent", "twenty five per cent"),
        ("it paid $1250",             "thirteen hundred and fifty dollars"),
        ("the 1100 m start",          "eleven hundred and fifty"),
    ]:
        check(f"  {spoken!r} is REFUSED", not says(art, spoken),
              "the gate has gone soft — this figure is not in the article")

    print("\n-- 🔒 FRACTIONAL ODDS ARE LOCKED. Never converted, never flagged. --")
    for art, spoken, want in [
        ("at odds of 6/4", "six to four", True),
        ("at odds of 7/4", "seven to four", True),
        ("at odds of 6/4", "one point five", False),
        ("at odds of 7/4", "one point seven five", False),
        ("at odds of 7/4", "two dollars seventy five", False),
        ("beaten at 8-1",  "eight to one", True),
        ("beaten at 8-1",  "nine", False),
    ]:
        got = says(art, spoken)
        check(f"  {art.split()[-1]} {'reads' if want else 'is NOT'} {spoken!r}",
              got == want,
              "odds must stay fractional — converting them is forbidden in BOTH "
              "directions (Jodie, 9 Aug 2026)")

    print("\n-- 🔴 EP25: ODDS MAY CARRY A DECIMAL, AND A HALF IS SAID TWO WAYS --")
    # EP25, 14 Aug 2026. The article says "a bet of $1 each way on a winner at 20-1
    # means combined odds of only 12.5-1". THREE drafting attempts wrote that figure
    # faithfully and the gate called it an invention all three times, so the episode
    # parked with no attempts left and no script saved.
    #
    # The cause was ORDER, not arithmetic: `_decimals` ran before the odds rule, so
    # `12.5-1` became "twelve point five-1" and the hyphen was never read as "to" —
    # while `20-1` in the very same sentence folded correctly. The gate could read a
    # price only when it was whole.
    #
    # AND A `.5` PRICE IS SAID BOTH WAYS. Attempt 1 said "twelve and a half to one";
    # attempts 2 and 3 said "twelve point five to one". Both are how an Australian
    # says that price, so both must trace or the next run re-parks on a coin toss.
    for art, spoken in [
        ("combined odds of only 12.5-1", "twelve point five to one"),
        ("combined odds of only 12.5-1", "half to one"),      # "twelve AND A half to one"
        ("combined odds of only 12.5-1", "twelve"),
        ("a winner at 20-1",             "twenty to one"),    # unchanged, same sentence
        ("returned 2.5-1",               "two point five to one"),
        ("returned 2.5-1",               "half to one"),
        ("at 7.5-2 in the market",       "seven point five to two"),
    ]:
        check(f"{art.split()[-1]} reads {spoken!r}", says(art, spoken))

    print("\n-- 🔴 AND A DECIMAL PRICE DOES NOT BECOME A DIFFERENT ONE --")
    for art, spoken in [
        ("combined odds of only 12.5-1", "thirteen to one"),
        ("combined odds of only 12.5-1", "twelve to one"),
        ("combined odds of only 12.5-1", "twelve point six to one"),
        ("combined odds of only 12.5-1", "twelve point five to two"),
        ("returned 2.5-1",               "two and a quarter to one"),
        # 🔒 The lock, from the other side: reading a HALF must not start converting
        # fractional odds. 6/4 is 1.5 in arithmetic and must stay "six to four".
        ("at odds of 6/4",               "one and a half"),
        ("at odds of 6/4",               "one point five to one"),
    ]:
        check(f"  {spoken!r} is REFUSED", not says(art, spoken),
              "the gate has gone soft — this figure is not in the article")

    print("\n-- 🔴 EP25: A DECADE IS A PLURAL, AND NOTHING READ IT --")
    # Found by folding EP25's article and looking for DIGITS THAT SURVIVED, rather
    # than by an episode failing on it: `1930s` was the only one. It sits in "Eric
    # Connolly, the well-known punter of the 1930s" — the sentence carrying the
    # article's own "never bet more than you can afford to lose", which is the
    # studio's standing outro, so a draft was very likely to reach for it.
    for art, spoken in [
        ("the well-known punter of the 1930s", "nineteen thirties"),
        ("back in the 1980s",                  "nineteen eighties"),
        ("the 1900s were different",           "nineteen hundreds"),
        ("racing in the 1920s",                "nineteen twenties"),
    ]:
        check(f"{art.split()[-1]} reads {spoken!r}", says(art, spoken))
    for art, spoken in [
        ("the well-known punter of the 1930s", "nineteen forties"),
        ("back in the 1980s",                  "nineteen nineties"),
        ("the well-known punter of the 1930s", "nineteen thirty one"),
    ]:
        check(f"  {spoken!r} is REFUSED", not says(art, spoken),
              "the gate has gone soft — this figure is not in the article")
    check("  and a plain year is untouched by the decade rule",
          says("back in 1988", "nineteen eighty eight")
          and not says("back in 1988", "nineteen eighties"))

    print("\n-- the readings are OFFERED, never chosen for you --")
    check("all three readings are declared in one place", len(sf.READINGS) == 3,
          f"{sf.READINGS}")
    check("  and the fold answers to each of them",
          all(sf.fold("run over 1600m", reading=r) for r in sf.READINGS))
    check("  _hundreds does not touch a number without four figures",
          sf._hundreds(2210) == "twenty two hundred and ten"
          and sf._hundreds(1600) == "sixteen hundred", sf._hundreds(2210))

    print("\n-- THE WHOLE GATE, on EP21's REAL article --")
    cap = PP / "docs/EP21-source-article-track-secrets-part-1.md"
    if cap.is_file():
        art = cap.read_text(encoding="utf-8")
        good = ("Being more than twenty two hundred and ten metres in circumference, "
                "it gives runners room.\n\nBarriers one and two have a good record "
                "over the twelve hundred and fifty metres journey.\n\nThe eleven "
                "hundred metres start has only a short run to the elbow.\n")
        check("EP21's real figures, spoken correctly, PASS", not sf.check(good, art),
              f"{sf.check(good, art)[:1]}")
        bad = good.replace("twenty two hundred and ten",
                           "twenty three hundred and ten")
        out = sf.check(bad, art)
        check("  and ONE altered digit still blocks", len(out) == 1, f"{out}")
        check("    naming the figure it refused",
              bool(out) and "twenty three hundred and ten" in out[0])
    else:
        check("EP21's capture is on this machine", False)

    print("\n-- THE WHOLE GATE, on EP25's REAL article: FIFTY ideas, one long line --")
    # 🔴 THE SHAPE THAT HID IT. This article is fifty numbered tips and its whole body
    # arrives as ONE unbroken line, so it carries far more figures per page than any
    # episode before it — prices, stakes, banks, percentages and unit counts, mixed.
    # A gate that reads a price only when it is whole will meet a decimal somewhere in
    # fifty tips, and it did. This keeps EP25's own sentence in the suite so the hole
    # cannot silently reopen on the next many-item article.
    cap25 = PP / "docs/EP25-source-article-50-great-staking-ideas.md"
    if cap25.is_file():
        art25 = cap25.read_text(encoding="utf-8")
        good25 = (
            "Here is the trap in each way betting, and it is worth hearing twice.\n\n"
            "A bet of one dollar each way on a winner at twenty to one means combined "
            "odds of only twelve point five to one.\n\nIf your twenty to one chance "
            "runs second or third you lose the one dollar win stake and win five "
            "dollars for the place bet.\n")
        out25 = sf.check(good25, art25)
        check("EP25's real figures, spoken correctly, PASS", not out25, f"{out25[:1]}")
        half25 = good25.replace("twelve point five to one",
                                "twelve and a half to one")
        out_h = sf.check(half25, art25)
        check("  and the same price said 'twelve and a half' passes too",
              not out_h, f"{out_h[:1]}")
        bad25 = good25.replace("twelve point five to one", "thirteen to one")
        out_b = sf.check(bad25, art25)
        check("  and rounding that price to a whole one still BLOCKS",
              len(out_b) == 1, f"{out_b}")
        check("    naming the figure it refused",
              bool(out_b) and "thirteen to one" in out_b[0])
    else:
        check("EP25's capture is on this machine", False)

    print(f"\nspoken numbers: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
