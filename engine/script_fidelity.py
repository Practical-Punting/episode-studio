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


def _year_pairs(m) -> str:
    """1988 -> "nineteen eighty eight". A YEAR IS NOT SPOKEN AS A CARDINAL.

    `int_words(1988)` gives "one thousand nine hundred and eighty eight", which
    nobody says and which is why EP16's approved script still failed after the
    byline was admitted: the date was in the source and in the wrong voice.
    """
    a, b = int(m.group(1)), int(m.group(2))
    if b == 0:
        return f"{int_words(a)} hundred"
    if b < 10:
        return f"{int_words(a)} oh {int_words(b)}"
    return f"{int_words(a)} {int_words(b)}"


def fold(text: str, frac=_frac_named, years: bool = False) -> str:
    """The article, written the way it is SAID. Racing notation first, because
    spoken_form's bare-integer rule would otherwise eat `8-1` as two numbers."""
    s = text or ""
    if years:
        # OFFERED AS AN EXTRA READING, NEVER AS A REPLACEMENT — see haystacks().
        s = re.sub(r"\b(1\d|20)(\d{2})\b", _year_pairs, s)
    s = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", frac, s)
    s = re.sub(r"\b(\d+)\s*-\s*(\d+)\s*\bON\b", _odds_on, s, flags=re.I)
    s = re.sub(r"\b(\d+)\s*-\s*(\d+)\b", _odds, s)
    return spoken_form(s)


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
        for years in (False, True):
            s = fold(src, frac, years=years)
            out.append(norm_words(s))
            out.append(norm_words(re.sub(r"\bdollars?\b", " ", s)))
    return out


# ------------------------------------------------- the figures a script says --
_ONES = set("zero one two three four five six seven eight nine ten eleven twelve "
            "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())
_TENS = set("twenty thirty forty fifty sixty seventy eighty ninety".split())
_SCALE = set("hundred thousand million".split())
_FRACW = set()
for _w in _FRACTION.values():
    _FRACW |= {_w, _w + "s"}
NUMBER_WORDS = _ONES | _TENS | _SCALE | _FRACW

# ⚠️ "half", "quarter" and "third" ALONE are ordinary English — "half the field",
# "a quarter of the odds", "in third place". They count as a figure only with a
# number word in front. Treating them as figures on their own put three false
# positives on an approved script in the first measurement.
BARE_WORDS = {"half", "halves", "quarter", "quarters", "third", "thirds"}

# Words that may sit INSIDE a spoken figure but never start or end one.
CONNECTORS = set("and to on per cent dollars dollar point in".split())

# 🔴 A CLAUSE BOUNDARY ENDS A FIGURE. norm_words strips punctuation, so without
# this "he still loses a hundred dollars: a three hundred dollar return" folds
# into ONE run and is then reported untraceable — a fault in the reader, blamed
# on the writer. That was four of the twenty first-pass false positives.
_CLAUSE = re.compile(r"[.,;:!?()\[\]—–\"'\n]")


def figures(text: str) -> list[str]:
    """Every figure the text SAYS, in the words it says it."""
    found = []
    for chunk in _CLAUSE.split(text or ""):
        run: list[str] = []
        for tok in norm_words(chunk) + ["\x00"]:
            if tok in NUMBER_WORDS or (run and tok in CONNECTORS):
                run.append(tok)
                continue
            while run and run[-1] in CONNECTORS:
                run.pop()
            if run and any(t in NUMBER_WORDS for t in run) \
                    and not (len(run) == 1 and run[0] in BARE_WORDS):
                found.append(" ".join(run))
            run = []
    return found


def _contiguous(needle: str, hays: list[list[str]]) -> bool:
    n = needle.split()
    return any(any(h[i:i + len(n)] == n for i in range(len(h) - len(n) + 1))
               for h in hays)


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
