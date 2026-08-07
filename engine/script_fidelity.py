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


def source_text(capture_text: str) -> str:
    """Everything a script's figures may be drawn from: the byline + the body."""
    body = (capture_text or "").split(MARKER_BEGIN)[-1]
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


def _frac_named(m) -> str:
    n, d = int(m.group(1)), int(m.group(2))
    w = _FRACTION.get(d)
    if not w:
        return f"{int_words(n)} over {int_words(d)}"
    return f"{int_words(n)} {w}" + ("s" if n > 1 else "")


def _frac_in(m) -> str:
    return f"{int_words(int(m.group(1)))} in {int_words(int(m.group(2)))}"


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


def fold(text: str, frac=_frac_named, pairs: bool = False,
         ordinal_dates: bool = False) -> str:
    """The article, written the way it is SAID.

    ORDER IS LOAD-BEARING. Racing notation and units go first, because
    spoken_form's bare-integer rule would otherwise eat `8-1` as two numbers and
    would never see `1600m` at all.
    """
    s = text or ""
    s = re.sub(r"\b(\d+)(st|nd|rd|th)\b",
               lambda m: ordinal_words(int(m.group(1))), s)
    if ordinal_dates:
        s = re.sub(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})\b",
                   lambda m: f"{m.group(1)} {ordinal_words(int(m.group(2)))}", s)
    # A RANGE CARRYING A UNIT, e.g. `2100-2300m`, BEFORE either half is folded
    # alone. Without this the unit rule eats "2300m" and the odds rule then finds
    # no pair, so the article never says "twenty one hundred TO twenty three
    # hundred" and EP13's approved script was called a liar for saying it.
    s = re.sub(r"\b(\d[\d,]*)\s*-\s*(\d[\d,]*)\s*(kg|km|m|f)\b",
               lambda m: (_num_readings(int(m.group(1).replace(",", "")), pairs)
                          + " to "
                          + _num_readings(int(m.group(2).replace(",", "")), pairs)
                          + " " + UNITS[m.group(3)]), s)
    s = re.sub(r"\b(\d[\d,]*)\s*(kg|km|m|f)\b",
               lambda m: (_num_readings(int(m.group(1).replace(",", "")), pairs)
                          + " " + UNITS[m.group(2)]), s)
    s = _decimals(s)
    if pairs:
        # OFFERED AS AN EXTRA READING, NEVER AS A REPLACEMENT — see haystacks().
        s = re.sub(r"\b(\d{4})\b", lambda m: _pairs(int(m.group(1))), s)
    s = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", frac, s)
    s = re.sub(r"\b(\d+)\s*-\s*(\d+)\s*\bON\b", _odds_on, s, flags=re.I)
    s = re.sub(r"\b(\d+)\s*-\s*(\d+)\b", _odds, s)
    return spoken_form(s)


def _num_readings(n: int, pairs: bool) -> str:
    return _pairs(n) if (pairs and 1000 <= n <= 9999) else int_words(n)


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
    """
    src = source_text(capture_text)
    out = []
    for frac in (_frac_named, _frac_in):
        for pairs in (False, True):
            for odates in (False, True):
                s = fold(src, frac, pairs=pairs, ordinal_dates=odates)
                out.append(norm_words(s))
                # A UNIT SAID ONCE FOR A PAIR. "$400 to $200" is read "four
                # hundred dollars to two hundred"; "2100m to 2300m" is read
                # "twenty one hundred to twenty three hundred". Dropping the
                # unit word is the same ear-reading in both, so it is offered
                # for both rather than for money alone.
                units = r"\b(?:" + "|".join(["dollars?"] + list(UNITS.values())) + r")\b"
                out.append(norm_words(re.sub(units, " ", s)))
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
        toks = norm_words(chunk)
        for tok in toks + ["\x00"]:
            if tok == "and" and not (run and run[-1] in _AND_AFTER):
                tok_is_connector = False
            else:
                tok_is_connector = tok in CONNECTORS
            if tok in NUMBER_WORDS or (run and tok_is_connector):
                if not run and tok in ("hundred", "thousand") and prev == "a":
                    run.append("one")
                run.append(tok)
                prev = tok
                continue
            while run and run[-1] in CONNECTORS:
                run.pop()
            if run and any(t in NUMBER_WORDS for t in run) and not _is_prose(run):
                found.append(" ".join(run))
            run = []
            prev = tok
    return found


def _is_prose(run: list[str]) -> bool:
    """Runs that are ordinary English wearing a number's clothes.

      · "half", "a quarter", "in third place" — bare position or proportion.
      · "the THIRD ONE" — an ordinal followed by the PRONOUN "one". EP15's only
        remaining false positive was this, and reading it as a figure would have
        the gate demanding the article state the number "three one".
    """
    if len(run) == 1 and run[0] in BARE_WORDS:
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
def check(script_text: str, capture_text: str) -> list[str]:
    """Blockers, in plain English. Empty means every spoken figure is the
    article's own.

    ONE DIRECTION ONLY, and that is §0a's selection rule: THE VIDEO SELECTS, THE
    E-BOOK REPRODUCES. A figure in the article that the script leaves out is an
    omission, and omission is not alteration. A figure in the SCRIPT that is not
    in the article is an invention, and that is what this refuses.
    """
    body = (capture_text or "").split(MARKER_BEGIN)[-1]
    if not body.strip():
        return ["the captured article has no article text to check the script "
                "against, so no figure in the script could be verified."]
    hays = haystacks(capture_text)
    seen, out = set(), []
    for fig in figures(script_text):
        if fig in seen or _contiguous(fig, hays):
            continue
        seen.add(fig)
        out.append(
            f"the script says {fig!r}, and the article never states that figure. "
            "Everything Gordon says about a number has to be the article's own "
            "number — never corrected, never rounded, never inferred.")
    return out
