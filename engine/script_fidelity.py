"""script_fidelity.py — every figure Gordon speaks must be the article's figure.

Piece 4 of docs/DESIGN-the-pre-claim-drafting-pass.md.

    THE E-BOOK REPRODUCES. THE SCRIPT IS THE ARTICLE REWRITTEN TO BE SPOKEN.

So `author_ebook`'s character-for-character gate is the WRONG gate here: it would
fail every good script. What §0a actually demands of the spoken track is narrower
and checkable — *every figure traced, nothing corrected* — and until now nothing
enforced it.

    🔴 AND THE OBVIOUS IMPLEMENTATION IS USELESS: A SCRIPT HAS NO DIGITS BY LAW.
`render_ready.py` hard-fails a bare numeral in the spoken track, because the voice
engine guesses and guesses wrong. Point `author_cards.check_trace` — which keys on
`\\d` — at a script and it finds nothing and passes every episode.

So the ARTICLE is folded into the words we speak, and the SCRIPT is compared
against that. `align_to_script.spoken_form()` already owns the fold, deliberately
as ONE definition of "the same number", and it is imported rather than copied.

⚠️ THE RACING LAYER LIVES HERE AND NOT IN `spoken_form()`, BY RULING (Jodie,
7 Aug 2026). `spoken_form` also drives the render alignment against
`align_to_script.MIN_MATCH = 0.85` — the threshold that refused EP17 at 79.8% —
and moving a build-stopping threshold in order to add a gate is the wrong trade.
`check_trace` can take this layer next; the render path is untouched.

WHAT IT CANNOT DO, NAMED RATHER THAN GLOSSED: a figure that IS in the article but
is used to claim something the article never claimed will pass. Prose claims are
not enumerable, so that stays a human read — the same boundary §13 of the
commissions design draws, and the same one the card gate draws. This narrows the
typing, not the judging.

MEASURED BEFORE IT WAS BUILT, on four real scripts against EP16's capture:
    EP16 AS SHIPPED (approved, published)   20 untraceable -> 9 with the racing
        layer -> 1 once figure extraction respected clause boundaries.
    three machine drafts                    17/15/17 -> 3/1/6 -> 1/0/0.
Every remaining hit was the same one: the article's DATE. See `byline()`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from align_to_script import int_words, spoken_form            # noqa: E402
from preflight_cards import MARKER_BEGIN, norm_words          # noqa: E402


# ---------------------------------------------------------------- the source --
def byline(capture_text: str) -> str | None:
    """The capture's own byline line, or None.

    🔴 RULED 7 Aug 2026 (Jodie): the traceable source is the ARTICLE BODY **plus
    this one line**, and nothing else from the header.

    WHY IT IS NEEDED AT ALL: EP16's APPROVED, PUBLISHED script says "nineteen
    eighty-eight". The date is in the capture — `By Roger Dedman — PRACTICAL
    PUNTING, MARCH 1988` — but in the HEADER, above the article-text marker. A
    gate built the obvious way blocks a script that already shipped, and a gate
    that is wrong about approved work is simply wrong.

    WHY NOT THE WHOLE HEADER: it also carries the capture's notes about scan
    repairs. Treating those as traceable source would let the script quote a
    commentary ON the article as though it were the article — the exact trap
    `preflight_cards.capture_faults` exists to stop.

    ✅ DERIVED FROM THE CAPTURE'S STRUCTURE, NOT A LIST SOMEBODY MAINTAINS
    (fault #7): the first line of the HEADER that begins "By ". Measured across
    all seven real captures — it finds EP14's, EP16's and EP17's, and finds
    nothing for EP11, EP12, EP13 and EP15, whose only "By" line sits INSIDE the
    article body and is therefore already traceable. Scoping it to the header is
    what stops EP17's article sentence "By applying this limitation..." being
    mistaken for a byline.
    """
    head = (capture_text or "").split(MARKER_BEGIN)[0]
    for line in head.splitlines():
        if line.strip().startswith("By "):
            return line.strip()
    return None


# 🔴 A LIST MARKER IS MARKUP, NOT A FIGURE THE ARTICLE STATES. (EP25, 14 Aug 2026.)
# The capture now writes an ordered list as its own numbered paragraphs — `1. …` through
# `50. …` — which is the article's own numbering restored (see capture_article fault 5).
# Left in, those fifty markers become fifty numbers a script is ALLOWED to say, and this
# gate goes quietly soft in exactly the place it had just proved itself: EP25's first
# fresh draft was rejected for inventing `'forty seven'`, a figure the article does not
# contain — and `47.` is now the forty-seventh tip's marker. The gate would have waved
# through the very invention it caught.
#
# ⚠️ THE SHAPE IS THE WARNING, not this instance. Making a capture richer makes the
# things measured against it more permissive, and nothing announces that. **Anything
# added to the article of record has to be asked: does this become a fact a script may
# now claim?** Stripped only at the LINE START, so a figure the article really states
# ("1. Always bet with money…" is a marker; "$45. The progression" is not) is untouched.
_LIST_MARKER = re.compile(r"(?m)^\d+\.[ \t]+")


def source_text(capture_text: str) -> str:
    """Everything a script's figures may be drawn from: the byline + the body."""
    body = _LIST_MARKER.sub("", (capture_text or "").split(MARKER_BEGIN)[-1])
    b = byline(capture_text)
    return f"{b}\n{body}" if b else body


# ------------------------------------------------------------------ the fold --
# The forms this studio speaks, on top of spoken_form's money/per-cent/integers.
# These are RACING notation, which is most of what a Practical Punting article's
# figures are made of, and the reason the plain fold left twenty untraceable
# figures on an approved script.
_FRACTION = {2: "half", 3: "third", 4: "quarter", 5: "fifth", 6: "sixth",
             7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
             11: "eleventh", 12: "twelfth", 16: "sixteenth", 20: "twentieth"}


def _odds(m) -> str:
    return f"{int_words(int(m.group(1)))} to {int_words(int(m.group(2)))}"


def _odds_on(m) -> str:
    return _odds(m) + " on"


def _decade(m) -> str:
    """`1930s` -> "nineteen thirties". A DECADE IS A PLURAL AND NOTHING READ IT.

    ══ EP25, 14 Aug 2026 — FOUND BEFORE IT BIT, FOR ONCE ═══════════════════════
    Folding EP25's article and looking for DIGITS THAT SURVIVED turned up exactly
    one: `1930s`, in "Eric Connolly, the well-known punter of the 1930s" — the
    sentence that carries the article's own punchline, "never bet more than you can
    afford to lose", which is this studio's standing outro. A script reaching for
    that story says "the nineteen thirties", and the gate would have called it an
    invention and cost the episode another drafting attempt.

    The four-figure rules could not reach it: `1930s` has no word boundary before
    the `s`, so neither the year reading nor the cardinal ever sees it.

    🔒 A reading, like every rule in this file — it spells the digits that are on
    the page and cannot turn one figure into another.
    """
    a, b = int(m.group(1)), int(m.group(2))
    if b == 0:
        return f"{int_words(a)} hundreds"
    w = int_words(b)
    return f"{int_words(a)} " + (w[:-1] + "ies" if w.endswith("y") else w + "s")


def _dec_words(x: str) -> str:
    """"12.5" -> "twelve point five"; "1" -> "one". One side of a price."""
    if "." not in x:
        return int_words(int(x))
    whole, frac = x.split(".", 1)
    return f"{int_words(int(whole))} point " + " ".join(
        int_words(int(d)) for d in frac)


def _odds_dec(m) -> str:
    """`12.5-1` READ AS ODDS — "twelve point five to one".

    ══ EP25, 14 Aug 2026 ═══════════════════════════════════════════════════════
    A PRICE COULD ONLY BE READ WHEN IT WAS WHOLE. The article says "a bet of $1
    each way on a winner at 20-1 means combined odds of only 12.5-1". `20-1` folded
    correctly and `12.5-1`, eleven words later in the SAME SENTENCE, did not: the
    decimal rule ran first, turned it into "twelve point five-1", and the hyphen
    rule below then found no digit in front of the hyphen to work with. So the
    article's own printed price was untraceable and every script that said it aloud
    was called an invention.

    It cost EP25 all three drafting attempts. Each one wrote a complete script, each
    was rejected for this one figure, and each writer refused to remove a number the
    article prints — which was the right call, three times over.

    🔒 IT FIRES ONLY WHERE A DECIMAL IS PRESENT, so every pair that folds correctly
    today takes exactly the path it takes today. This can only reach strings the fold
    was already getting wrong, which is the narrowest widening available.

    ⚠️ AND IT IS A READING, NEVER A CONVERSION. It spells the digits either side of
    the hyphen; it cannot turn one figure into another. FRACTIONAL ODDS STAY LOCKED
    (Jodie, 9 Aug 2026) — `6/4` never becomes 1.5, because nothing here touches a
    slash, and the suite proves both directions still refuse.
    """
    a, b = m.group(1), m.group(2)
    if "." not in a and "." not in b:
        return m.group(0)          # a whole pair — the existing rule's business
    return f"{_dec_words(a)} to {_dec_words(b)}"


# A `.5` PRICE IS SAID TWO WAYS AND THE STUDIO USED BOTH. EP25's first attempt said
# "twelve and a half to one", its second and third "twelve point five to one". Both
# are how the price is spoken, so both are offered — see haystacks().
_HALF_SAID = re.compile(r"\b(point five)\b")


def half_reading(s: str) -> str:
    """"twelve point five" -> "twelve and a half". A rendering, not a value change."""
    return _HALF_SAID.sub("and a half", s)


def _frac_named(m) -> str:
    n, d = int(m.group(1)), int(m.group(2))
    w = _FRACTION.get(d)
    if not w:
        return f"{int_words(n)} over {int_words(d)}"
    return f"{int_words(n)} {w}" + ("s" if n > 1 else "")


def _frac_in(m) -> str:
    return f"{int_words(int(m.group(1)))} in {int_words(int(m.group(2)))}"


def _frac_odds(m) -> str:
    """`7/4` READ AS ODDS — "seven to four".

    ══ EP18, 7 Aug 2026 ═══════════════════════════════════════════════════════
    A SLASH MEANS TWO THINGS IN RACING AND THE NOTATION CANNOT TELL YOU WHICH.
      · EP16's `1/9` is a genuine FRACTION — a probability, spoken "one ninth"
        or "one in nine". That is what the slash rule was built for.
      · EP18's `7/4` is ODDS — "an average dividend of $2.80 (about 7/4)",
        spoken "seven to four", exactly as the hyphen form `7-4` would be.

    The gate blocked EP18's first live draft on "seven to four" — a faithful
    reading of the article's own words. **The draft was more correct than the
    checker.** This is the same family as the existing hyphen-odds rule; the
    slash simply had only half its meanings.

    🔒 ADDED AS AN EXTRA READING, NEVER A REPLACEMENT. `_frac_named` and
    `_frac_in` are untouched, so a script that reads `a/b` as a FRACTION still
    passes exactly as before. Widening what the ARTICLE may be read as cannot
    narrow anything — and the planted-fabrication tests prove it did not go soft.
    """
    return f"{int_words(int(m.group(1)))} to {int_words(int(m.group(2)))}"


# ── ORDINALS ────────────────────────────────────────────────────────────────
# Articles write `2nd`, `3rd`, `4th`; scripts say "second", "the third". And a
# DATE written `September 23` is spoken "the twenty third of September" — the
# cardinal is on the page and the ordinal is in the mouth.
_ORD_ONES = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
             6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
             11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
             15: "fifteenth", 16: "sixteenth", 17: "seventeenth",
             18: "eighteenth", 19: "nineteenth"}
_ORD_TENS = {20: "twentieth", 30: "thirtieth", 40: "fortieth", 50: "fiftieth",
             60: "sixtieth", 70: "seventieth", 80: "eightieth", 90: "ninetieth"}
MONTHS = ("January February March April May June July August September October "
          "November December").split()


def ordinal_words(n: int) -> str:
    if n in _ORD_ONES:
        return _ORD_ONES[n]
    if n in _ORD_TENS:
        return _ORD_TENS[n]
    if n < 100:
        return f"{int_words(n - n % 10)} {_ORD_ONES[n % 10]}"
    return int_words(n) + "th"


# ── UNITS ───────────────────────────────────────────────────────────────────
# `1600m`, `57kg`. There is no word boundary before the letter, so NEITHER
# spoken_form NOR the pair reading touches them — the article keeps its digits
# while the script says "sixteen hundred" and "fifty seven", and the gate calls
# an approved script a liar. Sixteen of EP11's twenty false positives were this.
UNITS = {"m": "metres", "kg": "kilos", "km": "kilometres", "f": "furlongs"}


def _pairs(n: int) -> str:
    """1600 -> "sixteen hundred"; 1988 -> "nineteen eighty eight".

    A YEAR IS NOT SPOKEN AS A CARDINAL and NEITHER IS A DISTANCE.
    `int_words(1988)` gives "one thousand nine hundred and eighty eight", which
    nobody says; `int_words(1600)` gives "one thousand six hundred", where every
    approved script says "sixteen hundred".
    """
    a, b = n // 100, n % 100
    if b == 0:
        return f"{int_words(a)} hundred"
    if b < 10:
        return f"{int_words(a)} oh {int_words(b)}"
    return f"{int_words(a)} {int_words(b)}"


# The three ways a four-figure number is said aloud. EVERY ONE IS OFFERED, because
# the notation cannot tell you which the writer meant: 1988 is a year, 1600 is a
# distance, 2210 is a circumference, and they are said differently.
READINGS = ("cardinal", "pairs", "hundreds")


def _hundreds(n: int) -> str:
    """2210 -> "twenty two hundred and ten"; 1250 -> "twelve hundred and fifty".

    🔴 THE READING THAT JAMMED EP21. (11 Aug 2026.) The article says "more than
    2210 m in circumference" and "the 1200 m and 1250m journeys". `_pairs` reads
    those as "twenty two ten" and "twelve fifty" — the YEAR reading — and
    `int_words` as "two thousand two hundred and ten". The way an Australian
    actually says a race distance is NEITHER: it is "twenty two hundred and ten".

    So the drafting pass wrote the article's own figures, correctly, and the gate
    called them inventions three times. The writer refused to mangle Hugh's
    measurements and halted — which was the right call, and cost the episode a
    drafting cycle. It would have done that to EVERY episode with a four-figure
    distance in it, which is most of them.

    ⚠️ IT IS A READING, NOT A CONVERSION, and that distinction is the whole safety
    argument. This turns the article's DIGITS into words a person would say; it
    never turns one figure into a different figure. `6/4` is untouched by it —
    fractional odds are locked (Jodie, 9 Aug 2026) and nothing here can reach them,
    because this only ever fires on a bare four-digit integer.
    """
    a, b = n // 100, n % 100
    return f"{int_words(a)} hundred" + (f" and {int_words(b)}" if b else "")


def _decimals(s: str) -> str:
    """3.9 -> "three point nine". NEVER "three" and "nine" separately.

    spoken_form matches whole integers, so a decimal folds into two unrelated
    numbers and the script's "three point nine lengths" matches neither. The
    lookbehind keeps money out of it — `$224.60` is spoken_form's business.
    """
    def one(m):
        whole, frac = int(m.group(1)), m.group(2)
        digits = " ".join(int_words(int(d)) for d in frac)
        return f"{int_words(whole)} point {digits}"
    return re.sub(r"(?<![\d$.])(\d+)\.(\d+)(?!\d)", one, s)


def fold(text: str, frac=_frac_named, reading: str = "cardinal",
         ordinal_dates: bool = False) -> str:
    """The article, written the way it is SAID.

    ORDER IS LOAD-BEARING. Racing notation and units go first, because
    spoken_form's bare-integer rule would otherwise eat `8-1` as two numbers and
    would never see `1600m` at all.
    """
    s = text or ""
    # 🔴 THE AUTHOR'S OWN DOLLARS-AND-CENTS TYPING, UN-GLUED. (EP29, 16 Aug 2026.)
    # Philip Roy's 1997 worked example prints `$1.67c` — a dollar sign AND a cents
    # mark on the one figure, which is how these old pages were set. spoken_form
    # folds the `$1.67` and leaves the `c` welded to the last word, giving
    # "one dollars sixty sevenC": a token no human being will ever say. So EVERY
    # spoken form of that amount was refused — "one dollar sixty seven", the
    # plural, and the bare "sixty seven" alike.
    #
    #     THERE WAS NO LEGAL WAY TO COMPLY. The writer could not say the figure and
    #     could not delete it either, because deleting a figure the author printed
    #     is the same offence as inventing one. It spent all three attempts saying
    #     so, correctly, and stopped rather than damage the script.
    #
    # This is the racing layer's business and not spoken_form's, by the ruling at
    # the top of this module: it is PP's house typography, not how anyone speaks.
    # The `c` is dropped only where a dollar amount already carries its cents, so
    # a bare `50c` is untouched and still reads "fifty cents".
    s = re.sub(r"(\$\s?\d[\d,]*\.\d{2})\s*c\b", r"\1", s)
    s = re.sub(r"\b(\d+)(st|nd|rd|th)\b",
               lambda m: ordinal_words(int(m.group(1))), s)
    # A DECADE, before anything else can mistake it for a year. See `_decade`.
    s = re.sub(r"\b(\d{2})(\d0)s\b", _decade, s)
    if ordinal_dates:
        s = re.sub(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})\b",
                   lambda m: f"{m.group(1)} {ordinal_words(int(m.group(2)))}", s)
    # A RANGE CARRYING A UNIT, e.g. `2100-2300m`, BEFORE either half is folded
    # alone. Without this the unit rule eats "2300m" and the odds rule then finds
    # no pair, so the article never says "twenty one hundred TO twenty three
    # hundred" and EP13's approved script was called a liar for saying it.
    s = re.sub(r"\b(\d[\d,]*)\s*-\s*(\d[\d,]*)\s*(kg|km|m|f)\b",
               lambda m: (_num_readings(int(m.group(1).replace(",", "")), reading)
                          + " to "
                          + _num_readings(int(m.group(2).replace(",", "")), reading)
                          + " " + UNITS[m.group(3)]), s)
    s = re.sub(r"\b(\d[\d,]*)\s*(kg|km|m|f)\b",
               lambda m: (_num_readings(int(m.group(1).replace(",", "")), reading)
                          + " " + UNITS[m.group(2)]), s)
    # ODDS CARRYING A DECIMAL, BEFORE `_decimals` SPELLS THE POINT OUT. Once `12.5`
    # has become "twelve point five" there is no digit left in front of the hyphen
    # for the odds rule at the foot of this function to see. See `_odds_dec` for the
    # episode it cost. It is inert on a whole pair, so nothing else moves.
    # ⚠️ THE LOOKAHEAD ALLOWS A FULL STOP, and that is not a detail. Written `(?![\d.])`
    # it refused to match `12.5-1.` at the END OF A SENTENCE — which is exactly how
    # EP25's article prints it, so the synthetic test passed and the real capture still
    # failed. Only a following DIGIT may extend the figure; a full stop ends it.
    s = re.sub(r"(?<![\d$.,-])(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)(?!\.?\d)",
               _odds_dec, s)
    s = _decimals(s)
    if reading in ("pairs", "hundreds"):
        # OFFERED AS AN EXTRA READING, NEVER AS A REPLACEMENT — see haystacks().
        fn = _pairs if reading == "pairs" else _hundreds
        # 🔴 MONEY FIRST, AND THE BARE RULE MUST NOT REACH INSIDE IT. `$1250` was
        # becoming "$twelve hundred and fifty" — `spoken_form` then no longer
        # recognises it as money, so the word "dollars" was silently dropped and a
        # script saying "twelve hundred and fifty DOLLARS" matched nothing. The unit
        # is put on here instead, where the reading is chosen.
        s = re.sub(r"\$\s?(\d{4})\b",
                   lambda m: fn(int(m.group(1))) + " dollars", s)
        s = re.sub(r"(?<![$\d.,])\b(\d{4})\b", lambda m: fn(int(m.group(1))), s)
    s = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", frac, s)
    s = re.sub(r"\b(\d+)\s*-\s*(\d+)\s*\bON\b", _odds_on, s, flags=re.I)
    s = re.sub(r"\b(\d+)\s*-\s*(\d+)\b", _odds, s)
    return spoken_form(s)


def _num_readings(n: int, reading: str) -> str:
    """The one reading this pass is offering, for a number carrying a UNIT.

    `1600m` is "sixteen hundred metres" (pairs), "sixteen hundred metres"
    (hundreds) or "one thousand six hundred metres" (cardinal) — all three are
    things people say, so all three are offered across the passes rather than one
    being chosen here.
    """
    if 1000 <= n <= 9999:
        if reading == "pairs":
            return _pairs(n)
        if reading == "hundreds":
            return _hundreds(n)
    return int_words(n)


def haystacks(capture_text: str) -> list[list[str]]:
    """The source folded every way it may legitimately be READ ALOUD.

    A figure traces if it appears in ANY of these. Each variant is a different
    SPOKEN RENDERING of the same written figure — never an arithmetic conversion.
    §0a forbids the studio doing sums the article did not: "eleven per cent" is
    NOT an acceptable reading of `1/9`, and no variant here produces one.

      · `1/9` reads "one ninth" AND "one in nine" — EP16 AS SHIPPED says "one in
        nine", so both are house-correct by demonstration rather than by opinion.
      · `$400 to $200` is commonly read "four hundred dollars to two hundred",
        dropping the second unit, so a variant without the unit is offered too.
      · `1988` reads "nineteen eighty-eight" as a year AND "one thousand nine
        hundred and eighty-eight" as a cardinal. BOTH are kept, which is why the
        year pass is a variant and not a rewrite: if a four-digit number is not
        a year at all, its cardinal reading is still there to match.
      · `a/b` reads as a FRACTION ("one ninth", "one in nine") AND as ODDS
        ("seven to four"). The notation cannot tell you which it is — EP16's
        `1/9` is a probability and EP18's `7/4` is a price — so all three are
        offered and the script may legitimately say any of them.
      · `2210` reads "twenty two ten" (pairs), "twenty two hundred and ten"
        (hundreds) AND "two thousand two hundred and ten" (cardinal). The
        HUNDREDS reading is how a distance is actually said and it was the one
        missing — see `_hundreds` for the episode it cost.
    """
    src = source_text(capture_text)
    out = []
    for frac in (_frac_named, _frac_in, _frac_odds):
        for reading in READINGS:
            for odates in (False, True):
                s = fold(src, frac, reading=reading, ordinal_dates=odates)
                out.append(norm_words(s))
                # A UNIT SAID ONCE FOR A PAIR. "$400 to $200" is read "four
                # hundred dollars to two hundred"; "2100m to 2300m" is read
                # "twenty one hundred to twenty three hundred". Dropping the
                # unit word is the same ear-reading in both, so it is offered
                # for both rather than for money alone.
                units = r"\b(?:" + "|".join(["dollars?"] + list(UNITS.values())) + r")\b"
                out.append(norm_words(re.sub(units, " ", s)))
                # A HALF SAID AS A HALF. "twelve point five to one" is also spoken
                # "twelve and a half to one" — EP25 used both forms across its three
                # attempts. Offered exactly as the unit-less variant above is: an
                # EXTRA rendering of a figure the article already states, so it can
                # widen what the source may be READ as and never what it says.
                h = half_reading(s)
                if h != s:
                    out.append(norm_words(h))
                    out.append(norm_words(re.sub(units, " ", h)))
                # 🔴 A SINGLE DOLLAR IS SAID "ONE DOLLAR". (EP29, 16 Aug 2026.)
                # The money fold always writes the plural — `$1.50` becomes "one
                # dollarS fifty" — so the ONLY grammatical way to say it, "one
                # dollar fifty", matched nothing and was reported as an invented
                # figure. EP29's writer was told twice to delete an amount its
                # article prints twice, refused both times, and burned all three
                # attempts being right.
                #     THE PROOF IT IS GRAMMAR AND NOT FIGURES is inside that same
                # draft: it says "three dollars fifty" and that PASSED, while
                # "one dollar fifty" blocked. The gate was marking English.
                # Offered as an EXTRA reading beside the unit-less and half ones,
                # so the plural stays valid wherever it is the right word — this
                # widens what the SOURCE MAY BE READ AS and never what the script
                # may say. An amount the article does not print is still refused
                # in the singular exactly as it always was in the plural.
                sing = re.sub(r"\bone dollars\b", "one dollar", s)
                if sing != s:
                    out.append(norm_words(sing))
                    out.append(norm_words(re.sub(units, " ", sing)))
    return out


# ------------------------------------------------- the figures a script says --
_ONES = set("zero one two three four five six seven eight nine ten eleven twelve "
            "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())
_TENS = set("twenty thirty forty fifty sixty seventy eighty ninety".split())
_SCALE = set("hundred thousand million".split())
_FRACW = set()
for _w in _FRACTION.values():
    _FRACW |= {_w, _w + "s"}
_FRACW |= set(_ORD_ONES.values()) | set(_ORD_TENS.values())
NUMBER_WORDS = _ONES | _TENS | _SCALE | _FRACW

# ⚠️ "half", "quarter" and "third" ALONE are ordinary English — "half the field",
# "a quarter of the odds", "in third place". They count as a figure only with a
# number word in front. Treating them as figures on their own put three false
# positives on an approved script in the first measurement.
BARE_WORDS = {"half", "halves", "quarter", "quarters", "third", "thirds"}

# The ordinal words themselves, for the "every Nth" idiom in _is_prose. A finishing
# position is still traced — this set is only ever consulted behind the word "every".
_ORDINAL_WORDS = set(_ORD_ONES.values()) | set(_ORD_TENS.values())

# Words that may sit INSIDE a spoken figure but never start or end one.
CONNECTORS = set("and to on per cent dollars dollar point in".split())

# ⚠️ "and" IS ONLY A CONNECTOR WHERE A NUMBER ACTUALLY USES ONE — after "hundred"
# or "thousand", which is precisely where int_words emits it ("one hundred AND
# twenty"). Everywhere else it joins two SEPARATE figures, and treating it as
# internal glues them into one that no article ever states: EP17's approved
# script says "eleven dollars fifty for number EIGHT AND TWELVE dollars for
# number nine", and the gate demanded the article state "eight and twelve".
_AND_AFTER = {"hundred", "thousand"}

# 🔴 A CLAUSE BOUNDARY ENDS A FIGURE. norm_words strips punctuation, so without
# this "he still loses a hundred dollars: a three hundred dollar return" folds
# into ONE run and is then reported untraceable — a fault in the reader, blamed
# on the writer. That was four of the twenty first-pass false positives.
_CLAUSE = re.compile(r"[.,;:!?()\[\]—–\"'\n]")


def figures(text: str) -> list[str]:
    """Every figure the text SAYS, in the words it says it.

    "A HUNDRED" IS "ONE HUNDRED". A run beginning at "hundred" or "thousand"
    whose previous word was "a" is the indefinite article doing the work of the
    numeral — EP11 says "a hundred to one" where the fold writes "one hundred to
    one". Restoring the "one" is a READING, not a fallback: it changes nothing
    about which number is claimed.
    """
    found = []
    for chunk in _CLAUSE.split(text or ""):
        run: list[str] = []
        prev = ""
        before = ""      # the word immediately BEFORE the run began — see _is_prose
        toks = norm_words(chunk)
        for tok in toks + ["\x00"]:
            if tok == "and" and not (run and run[-1] in _AND_AFTER):
                tok_is_connector = False
            else:
                tok_is_connector = tok in CONNECTORS
            if tok in NUMBER_WORDS or (run and tok_is_connector):
                if not run:
                    # ⚠️ CAPTURED HERE AND NOWHERE ELSE. `prev` is overwritten on every
                    # token INSIDE the run, so by the time the run closes it holds the
                    # run's own last word, not the word in front of it. The lead-in has
                    # to be taken at the moment the run starts or it is already gone.
                    before = prev
                    if tok in ("hundred", "thousand") and prev == "a":
                        run.append("one")
                run.append(tok)
                prev = tok
                continue
            while run and run[-1] in CONNECTORS:
                run.pop()
            if run and any(t in NUMBER_WORDS for t in run) \
                    and not _is_prose(run, before):
                found.append(" ".join(run))
            run = []
            before = ""
            prev = tok
    return found


def _is_prose(run: list[str], before: str = "") -> bool:
    """Runs that are ordinary English wearing a number's clothes.

      · "half", "a quarter", "in third place" — bare position or proportion.
      · "the THIRD ONE" — an ordinal followed by the PRONOUN "one". EP15's only
        remaining false positive was this, and reading it as a figure would have
        the gate demanding the article state the number "three one".
      · "EVERY second voice" — the distributive idiom, meaning every other. `before`
        is the word in front of the run.

    🔴 "EVERY Nth" IS AN IDIOM, NOT A POSITION (EP22, 12 Aug 2026). EP22's first draft
    said "Every second voice out there has a system" and the gate called "second" a
    figure the article never states — costing a writing attempt and a repair round.
    The same sentence with "third" passed, because BARE_WORDS happens to name "third"
    and not "second". So the gate read one sentence two ways depending on which
    ordinal was in it.

    🔒 AND THE EXEMPTION IS THE IDIOM, NOT THE ORDINAL. Exempting bare ordinals
    outright was written, proved and REVERTED: a finishing position is a claim about
    the world and stays traced — "saying a horse ran sixth when the article says
    fourth is exactly the kind of altered figure §0a forbids". Keying on "every"
    cannot reach "ran sixth" or "finished fourth", because neither is preceded by it.
    An ORDINAL only: "every twelve starts" is a cardinal and stays checked.
    """
    if len(run) == 1 and run[0] in BARE_WORDS:
        return True
    if len(run) == 1 and before == "every" and run[0] in _ORDINAL_WORDS:
        return True
    return len(run) == 2 and run[0] in _FRACW and run[1] == "one"


def _drop_and(tokens: list[str]) -> list[str]:
    """"two thousand AND twenty" == "two thousand twenty".

    `int_words` writes "one hundred and twenty" but "two thousand twenty", while
    people say "and" in both. It is a stylistic connector carrying no numeric
    meaning, so it is removed from BOTH sides — symmetrically, which is what
    keeps this a normalisation rather than a loosening.
    """
    return [t for t in tokens if t != "and"]


def _in(n: list[str], h: list[str]) -> bool:
    return any(h[i:i + len(n)] == n for i in range(len(h) - len(n) + 1))


def _contiguous(needle: str, hays: list[list[str]]) -> bool:
    n = needle.split()
    if any(_in(n, h) for h in hays):
        return True
    # The same comparison with the stylistic "and" removed from BOTH sides.
    na = _drop_and(n)
    return na != n and any(_in(na, _drop_and(h)) for h in hays)


# ------------------------------------------------------------------- the gate --
def check(script_text: str, capture_text: str, licensed_text: str = "",
          allowed: list | None = None) -> list[str]:
    """Blockers, in plain English. Empty means every spoken figure is accounted for.

    ONE DIRECTION ONLY, and that is §0a's selection rule: THE VIDEO SELECTS, THE
    E-BOOK REPRODUCES. A figure in the article that the script leaves out is an
    omission, and omission is not alteration. A figure in the SCRIPT that is not
    in the article is an invention, and that is what this refuses.

    ── THE FRAMING PROSE, AND WHY IT IS NOT A SECTION EXEMPTION ──────────────────
    Four parts of the script are the studio's own words, not the article's: the
    opening framing line, the transitions between beats, the midroll invitation and
    the outro wind-down (pp-episode-script SKILL §43). A number in one of them — "part
    two", "ten systems" — is in no article sentence, so this gate stalled the run over
    Gordon's own storytelling.

    THE OBVIOUS FIX IS THE WRONG ONE. Exempting those SECTIONS means identifying them
    in a plain-text file of undifferentiated paragraphs, and every rule for doing that
    ("the first beat", "the last beat") is a guess that hands back a hole in §0a: an
    invented racing figure in the outro would walk straight through.

    So nothing is exempted by LOCATION. A figure is allowed when it has a SECOND
    APPROVED SOURCE — the episode's own packaging, which Jodie approves at the words
    gate: the hook, the byline, the part. "Part 1" and "10 Systems" are hers, written
    down and signed off, so Gordon may say them; they are not the studio inventing a
    number. Anything in NEITHER the article NOR the packaging still blocks, which is
    every racing figure that was ever the point of this gate.
        AND IT IS DECLARED, NEVER SILENT: each allowance is appended to `allowed` and
    logged by the caller, so "the gate passed" always comes with what it waved and why.
    """
    body = (capture_text or "").split(MARKER_BEGIN)[-1]
    if not body.strip():
        return ["the captured article has no article text to check the script "
                "against, so no figure in the script could be verified."]
    hays = haystacks(capture_text)
    # The approved packaging, folded exactly as the article is — same function, so
    # "ten" matching "10" is decided in ONE place and cannot drift between the two.
    lic = haystacks(licensed_text) if (licensed_text or "").strip() else []
    seen, out = set(), []
    for fig in figures(script_text):
        if fig in seen or _contiguous(fig, hays):
            continue
        seen.add(fig)
        if lic and _contiguous(fig, lic):
            if allowed is not None:
                allowed.append(
                    f"{fig!r} is not in the article, but it IS in this episode's "
                    f"approved packaging — so it is the studio's own framing, not an "
                    f"invented figure.")
            continue
        out.append(
            f"the script says {fig!r}, and the article never states that figure. "
            "Everything Gordon says about a number has to be the article's own "
            "number — never corrected, never rounded, never inferred. "
            "(The one exception is a figure from THIS EPISODE'S APPROVED PACKAGING — "
            "its part number, or a count that is already in the approved hook. If the "
            "number is neither, it is the studio's invention: say it without a "
            "figure.)")
    return out
