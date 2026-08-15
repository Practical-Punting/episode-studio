#!/usr/bin/env python3
"""author_ebook.py — author the e-book source page, and GATE its fidelity.

    python author_ebook.py <episode.json> <ebook dir> [--force] [--check-only]

WHAT THIS DOES, IN ONE LINE
---------------------------
It joins the standing shell (`assets/ebook-template.html`) to the episode's
hand-written ARTICLE BODY (`<ebook dir>/body.html`), and it refuses to do so if
the body has drifted from the source article.

THE DESIGN QUESTION THIS ANSWERS (Jodie, 28 Jul 2026)
-----------------------------------------------------
The e-book was the one asset in the self-authoring design with a real question in
it: where does the templated shell end and the editorial body begin? The shell,
the layout and the figures template cleanly. The BODY is §0a fidelity work —
reproducing "firstup" as one word and lower-case "joie Denise" is DELIBERATE
non-normalisation, and any automatic markup pass silently tidies exactly that.

Jodie's answer was **option A with a machine check, not a human halt**:

  * Claude Code writes the body file AT SCRIPT TIME, when the article is in hand
    and the fidelity work is already being done. So `ebook_pdf` does NOT stop and
    ask a person to read twenty paragraphs.
  * Instead THIS SCRIPT hard-fails if the body departs from the source article
    beyond a DECLARED list of departures.

Her reasoning, recorded so it is not re-litigated:

  * The rejected option asked a human to eyeball twenty paragraphs for BYTE-LEVEL
    faithfulness. That is what humans are worst at and machines are best at.
  * **EP11's "firstup" was normalised to "first-up" and got PAST human review.**
    The check that would have caught it is a string comparison.
  * The human check does not disappear. The e-book is already one of the four
    approvals, so a mid-build read would be a SECOND gate on the same document —
    and per PP-STANDARDS §WHAT DESERVES A GATE, "a gate is only worth having if
    the thing behind it is worth stopping an episode for".

WHAT THE FIDELITY CHECK ACTUALLY CHECKS
---------------------------------------
Every ARTICLE-PROSE paragraph in the body (a plain `<p>` with no class) must be
character-for-character equal to a paragraph of the source article, after the
DECLARED departures are applied to the article. In order. Each article paragraph
used at most once. Any article paragraph the body does not reproduce must be
declared in `ebook.omit_paragraphs[]`, quoted — EXCEPT a paragraph the body
reproduces in another element, which is RECOGNISED and verified rather than
declared away: a heading whose words are identical, a figure of the card that
renders the article's table, or a `<table class="chart">` checked cell for cell.
A CHART MAY NEVER BE DECLARED OMITTED (Jodie, 15 Aug 2026 — see TABLE_CLASSES).

That single rule catches, without any of them being special-cased:
  * silent normalisation   — "firstup" -> "first-up" is not equal, so it halts
  * silent capitalisation  — "joie Denise" -> "Joie Denise" is not equal
  * an invented sentence   — matches no article paragraph
  * a dropped paragraph    — undeclared omission
  * a reordered argument   — the order pointer cannot go backwards

The comparison is EXACT. It does not fold case, quotes, dashes or punctuation,
because every one of those is a thing §0a says must survive. (That is the
opposite choice from `author_cards.py`'s `norm()`, which folds quotes and dashes
on purpose — a card TRACE is asking "is this sentence in the article", a much
weaker question than "is this the article".)

DEPARTURES ARE A FIXED VOCABULARY, NOT A REGEX FROM DATA
--------------------------------------------------------
`ebook.departures[]` holds NAMES from the table below. episode.json cannot
express an arbitrary transform, for the same reason `author_cards.py` has no LLM
in it: a departure engine that can do anything can hide anything. Adding a name
is a code change, which means a diff, a reviewer and Jodie's say-so.

A declared departure that changes NOTHING also halts. Otherwise the list becomes
boilerplate that gets copied forward and stops meaning anything.

NEVER OVERWRITE HAND-AUTHORED WORK — but ALWAYS run the check. The write is
skipped for a page that is hand-authored or already generated; the fidelity gate
runs every time regardless, because it is a gate and not an authoring step.
"""
import argparse
import difflib
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from author_cards import Halt                                   # noqa: E402

for _s in (sys.stdout, sys.stderr):        # the Windows console is cp1252
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                       # noqa: BLE001
        pass

ASSETS = os.path.join(os.path.dirname(HERE), "assets")
TEMPLATE = os.path.join(ASSETS, "ebook-template.html")
GEN = "PP-GENERATED"
MARKER = (f"<!-- {GEN} by author_ebook.py — DO NOT HAND-EDIT. The shell comes from "
          "assets/ebook-template.html and the article body from ebook/body.html; "
          "to change the book, change one of those. To take this page over by hand, "
          "delete this line. -->")

BODY_FILE = "body.html"

# ══ THE ROGUE QUESTION MARK (Jodie, 7 Aug 2026, after Hugh read EP17) ═════════
# A stray "?" — one starting a paragraph, or sitting mid-word where nobody asks
# anything — is scan damage, and it is stripped from the e-book.
#
# 🔴 SCOPED TO GENERATED FURNITURE ONLY, AND THAT IS THE WHOLE OF THE CARE HERE.
# The fidelity gate requires every BARE <p> to reproduce a source paragraph
# character for character, folding nothing. A rule that edited article prose
# would not "clean the book" — it would BREAK THE GATE on the very next run and
# take the fidelity guarantee with it. So this touches classed paragraphs
# (.lead/.byline/.note/.pullquote), .kicker, headings and figure alt text, and it
# CANNOT see a bare <p>.
#
# ⚠️ CONSEQUENCE, NAMED RATHER THAN LEFT TO BE DISCOVERED: EP17's three stray "?"
# are inside BARE <p> — they are the article's own bytes, reproduced deliberately
# under §0a-i as category 1. THIS RULE DOES NOT REACH THEM AND MUST NOT. Removing
# those is an omission decision about the article of record, not a render-time
# tidy; the place for it is the CAPTURE file, disclosed, where §0a-i puts every
# other repair.
_ROGUE_Q = re.compile(
    r"(?:(?<=^)|(?<=>)|(?<=\s))\?(?=[A-Za-z])"      # ?Word — opens or mid-flow
)


def strip_rogue_question_marks(fragment: str) -> str:
    """Remove stray '?' glyphs from a piece of GENERATED FURNITURE.

    A real question mark FOLLOWS a word and precedes a space or end of text
    ("Number seven? Forget about it!"). A rogue one PRECEDES a letter with
    nothing sensible before it. Only the second shape matches.
    """
    return _ROGUE_Q.sub("", fragment)


# Everything the rule may touch. Bare <p> is deliberately absent.
_FURNITURE = re.compile(
    r"(<p\s+class=\"[^\"]+\"[^>]*>)(.*?)(</p>)"
    r"|(<div\s+class=\"kicker\"[^>]*>)(.*?)(</div>)"
    r"|(<h[12][^>]*>)(.*?)(</h[12]>)",
    re.S)


def clean_furniture(body: str) -> tuple[str, int]:
    """Apply the rogue-'?' rule to furniture only. Returns (body, how many)."""
    removed = [0]

    def one(m):
        groups = [g for g in m.groups() if g is not None]
        open_t, inner, close_t = groups[0], groups[1], groups[2]
        cleaned = strip_rogue_question_marks(inner)
        removed[0] += inner.count("?") - cleaned.count("?")
        return open_t + cleaned + close_t

    out = _FURNITURE.sub(one, body)
    # figure alt text is furniture too, and it is written by the studio
    def alt(m):
        cleaned = strip_rogue_question_marks(m.group(2))
        removed[0] += m.group(2).count("?") - cleaned.count("?")
        return m.group(1) + cleaned + m.group(3)
    out = re.sub(r'(alt=")([^"]*)(")', alt, out)
    return out, removed[0]

# The ONE slot, as an exact literal from the standing template. It must occur
# exactly once — see the template header for the 26 Jul 2026 bug where a script
# matched an example inside a comment and rewrote the comment.
SLOT_BODY = """<div class="kicker">Practical Punting Guide</div>
<h1 class="section">Book Title Here</h1>
<p class="lead">Opening lead paragraph.</p>
<p class="byline">Practical Punting, Month Year.</p>
<h2 class="rule">A Section Heading</h2>
<p>The article's own sentences, reproduced. Figures are the print renders of the
motion cards: <img class="illus" src="figure-1.png" alt="what the figure shows">.</p>"""

# Standing furniture: copied byte-identical, only when absent. Same find-or-build
# policy as stage_card_furniture() — an authored page that cannot render is no
# better than a missing one.
STANDING_ASSETS = ("ebook-logo-white.png", "ebook-logo.png", "marketing-hero.png")

# ------------------------------------------------------------------ departures
#
# name -> (transform applied to the ARTICLE text, plain-English description)
#
# EP12 declared exactly one, and it is the only one in the vocabulary today.
# EP11 declared normalising "firstup" to "first-up"; that is NO LONGER ALLOWED
# (PP-STANDARDS §0a, Jodie 27 Jul 2026) and is deliberately not representable
# here. There is no "normalise" departure and there must never be one.
DEPARTURES = {
    "spaced-hyphen-em-dash": (
        lambda s: s.replace(" - ", " — "),
        "the article's spaced hyphens ( - ) are set as em dashes for print"),
}

# ------------------------------------------------------------------ vocabulary
#
# The class vocabulary PP-STANDARDS §E-book names. Enforced, so the body cannot
# invent a class to escape the fidelity check by dressing article prose up as
# editorial furniture.
P_CLASSES = {None: "article prose", "lead": "editorial", "byline": "editorial",
             "note": "editorial", "pullquote": "quoted"}
IMG_CLASSES = {"illus", "illus portrait"}
DIV_CLASSES = {None, "kicker", "pagebreak", "avoid", "divider"}
TAGS_OK = {"p", "h1", "h2", "h3", "div", "span", "img", "br", "b", "strong",
           "i", "em", "blockquote", "a", "ol", "li",
           # ── A CHART IS KEPT, NOT DROPPED (Jodie, 15 Aug 2026 — EP26) ──────────
           # See the long note by TABLE_CLASSES. These tags exist ONLY to reproduce
           # a table the article itself prints, and every cell is checked against it.
           "table", "tbody", "thead", "tr", "th", "td"}

# ══ THE CHART THE BOOK MUST KEEP (EP26, 15 Aug 2026) ═════════════════════════
# "Betting — It's a serious business" prints three staking charts as ONE 45-row
# <table>, and its prose points at them by name eleven times ("Chart B shows the
# results", "see Chart C"). The e-book writer had nowhere to put them:
#   · the class vocabulary said, in terms, "a table in the article is carried by
#     its FIGURE, not by markup — there is no <table> here";
#   · and no motion card carries 225 cells, nor should one — the SPOKEN script
#     correctly refers to the charts rather than reading them out.
# So the only door left open was `omit_paragraphs`, and the writer took it. The
# gate refused, rightly, and the halt was the system working; but a rule that
# leaves no legal way to do the right thing has already chosen the wrong one.
#
# 🔴 JODIE'S RULING: the charts MUST APPEAR IN THE E-BOOK. A chart is a FIGURE
# that is kept — never a paragraph that is quoted away. So the vocabulary gains
# ONE element, on the tightest possible terms:
#   · a <table class="chart"> is legal ONLY if its cells are, in order and
#     character for character, the cells of a table THE ARTICLE PRINTS;
#   · a card figure that renders the same table is still preferred and still
#     recognised (EP19) — and doing BOTH is refused, because that prints the same
#     numbers twice, which is the exact fault EP19 was pulled up for;
#   · a chart may never appear in `omit_paragraphs`, whatever it is quoted as.
# This is not a loophole in the fidelity gate. It is a stricter check than the
# card path: every cell must match, not merely every number and word.
TABLE_CLASSES = {"chart"}

# ══ A NUMBERED LIST IS A STRUCTURE, NOT A PARAGRAPH ══════════════════════════
# (EP25, 14 Aug 2026 — "50 Great Staking Ideas".)
#
# The article is an `<ol>` of exactly 50 `<li>`. The CAPTURE flattened it — `<li>`
# carries no whitespace, so stripping it left the fifty tips abutting with no space
# at all — and the e-book body then reproduced that one 3,900-word paragraph
# FAITHFULLY. **The fidelity gate passed.** It compares the body to the capture, the
# capture had already lost the structure, and so every check downstream agreed.
#
# 🔴 THAT IS THE LESSON, AND IT IS FAULT #1 AT ONE REMOVE: the gate asserted the
# artefact it was given, and nobody asked whether the artefact still had the article's
# SHAPE in it. A reproduction can be character-perfect and still not be the article.
#
# The capture now writes an ordered list as markdown's own `1. …` blocks
# (`capture_article.lists_to_blocks`), so the article of record has fifty paragraphs
# where it had one. This file's side of that bargain:
#   · a NUMBERED article paragraph must be reproduced by an `<li>`, never a bare `<p>`;
#   · an UNNUMBERED one must be reproduced by a bare `<p>`, never an `<li>`;
#   · N numbered items in the article means EXACTLY N `<li>` in the body — the check
#     the whole fix hangs on, and the one that would have caught EP25 on sight;
#   · the figures sit WITH THE TIP THEY ILLUSTRATE, derived from each card's own
#     trace, because EP25's six all went to the end where they illustrate nothing.
# The number itself is the article's OWN MARKUP, exactly as `**BOLD**` is for a
# heading — an `<ol>` numbers its items whether or not the digits are in the HTML —
# so it is stripped before the words are compared, and the words are still compared
# character for character, folding nothing.
NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$", re.S)


def split_number(paragraph: str):
    """('12', 'the words') for a numbered article paragraph, else (None, the words)."""
    m = NUMBERED.match(paragraph)
    return (int(m.group(1)), m.group(2).strip()) if m else (None, paragraph)

# Text that belongs to the SHELL. If the body carries it too, the book would
# print the page twice — and the second copy would not be the approved one.
SHELL_TEXT = ("Please Gamble Responsibly", "Thanks for downloading",
              "What are you prepared to lose today")


def text_of(fragment: str) -> str:
    """Visible text of an HTML fragment: tags out, entities in, spaces collapsed.

    Whitespace collapsing is the ONLY normalisation. HTML cannot express the
    difference between a newline and a space, so a line break in the markup must
    not read as a difference in the prose. Everything else — case, quotes,
    hyphens, dashes, punctuation — is left exactly as written, because every one
    of those is a thing §0a says must survive.
    """
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def article_blocks(path: str) -> list[str]:
    """The source article's blocks, RAW — line breaks and all.

    Reads only between the ARTICLE TEXT BEGINS/ENDS markers, so the source file's
    provenance header, its fidelity notes and its 'HOW TO USE' block are never
    mistaken for prose the book has to reproduce.

    ⚠️ SEPARATED FROM article_paragraphs() FOR ONE REASON: a markdown table's ROW
    STRUCTURE lives entirely in its newlines, and the whitespace collapse below
    destroys it. The fidelity comparison wants the collapsed form (a line break in
    markup is not a difference in the prose); the chart EXPANSION wants the raw one.
    Same blocks, same order, one split — so the two can never disagree about which
    block is which.
    """
    raw = open(path, encoding="utf-8").read()
    if "---- ARTICLE TEXT BEGINS ----" not in raw or "---- ARTICLE TEXT ENDS ----" not in raw:
        raise Halt(f"the source article {os.path.basename(path)} has no "
                   f"'---- ARTICLE TEXT BEGINS ----' / '---- ARTICLE TEXT ENDS ----' "
                   f"markers, so there is no way to tell its prose from its header "
                   f"notes. Add the markers around the article text.")
    body = raw.split("---- ARTICLE TEXT BEGINS ----")[1] \
              .split("---- ARTICLE TEXT ENDS ----")[0]
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def article_paragraphs(path: str) -> list[str]:
    """The source article's paragraphs, verbatim, with whitespace collapsed."""
    return [re.sub(r"\s+", " ", b) for b in article_blocks(path)]


# ══ THE CHART SLOT — THE MODEL NEVER TYPES A NUMBER ══════════════════════════
# (Jodie, 15 Aug 2026, on the back of EP26.)
#
# 🔴 THE STUDIO'S RULE: DATA IS LIFTED FROM THE SOURCE, NEVER RE-TYPED BY THE MODEL.
# A number is a READING, not a value. It is the same rule that makes every e-book
# figure a render of a motion card rather than fresh art, and the same one behind
# §0a-i's "the scan IS the article" — reproducing beats re-drawing, every time.
#
# EP26's chart is 201 cells. Asking a writer to transcribe it is asking for a wrong
# number at some rate above zero, and the cell-for-cell gate would then bounce the
# whole body — correct, and ~8 minutes and ~$3 per bounce. The gate is a NET, and a
# net you plan to land in is a bad plan.
#
# So the body declares a SLOT and this code fills it, exactly as the standing
# template declares ONE SLOT for the body itself:
#
#     <table class="chart" data-article-table="1"></table>
#
# `data-article-table` is the 1-based index of the markdown table in the article, and
# it is OPTIONAL — slots bind to the article's tables in document order, and an index,
# where given, must agree with that order. The slot must be EMPTY: a slot with rows
# typed into it is the transcription this exists to remove, and it halts.
#
# ⚠️ `ebook/body.html` KEEPS THE SLOT. It is not rewritten. The expansion happens on
# the way to the page, which is the same arrangement the figures already have — the
# body carries `<img src="figure-3.png">`, not a picture. The editorial file stays
# editorial, and the data stays lifted.
#
# THE GATE IS UNCHANGED AND STILL RUNS. Filling the slot from the article means the
# cell-for-cell check passes by construction — which is the point, not a reason to
# drop it. It is what proves the lift worked, and it still catches a literal table in
# a hand-authored body (EP11/EP12 have no slots and never will).
CHART_TABLE = re.compile(r'<table\s+class="chart"([^>]*)>(.*?)</table>', re.S)
_SLOT_INDEX = re.compile(r'data-article-table\s*=\s*"?(\d+)"?')


def _md_table_rows(block: str) -> list[list[str]]:
    """A raw markdown-table block as rows of cells, the separator row dropped.

    The cells are the article's own, stripped of the surrounding pipes and of the
    padding whitespace `table_to_md` writes — and of nothing else.
    """
    rows = []
    for line in block.strip().split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
            continue                       # the |---|---| separator is markup, not data
        rows.append(cells)
    return rows


def _chart_html(rows: list[list[str]]) -> str:
    """Rows of cells as an e-book chart table, the structure DERIVED from the shape.

    Nothing about the layout is declared anywhere. Three rules, in order, and each of
    them is a fact about the markdown rather than a preference:

      · a full-width row whose ONLY value sits in the FIRST column is a SECTION
        HEADING — "CHART A" — and is set as one <th colspan>. EP26's page writes
        exactly that, a colspan-5 <th>, and markdown can only render it as a row of
        padding cells.
      · the row FOLLOWING a section heading is that section's COLUMN HEADERS.
      · otherwise the first row of the table is the column header row, because a
        markdown table always heads its columns before the separator.

    ⚠️ THE CLOSING-BALANCE ROW IS WHY RULE ONE SAYS "FIRST COLUMN", and it was found
    by looking at the rendered page rather than at the code: EP26's `|  | 5200 |  |  |`
    is also a row with one value, and the first draft printed it as a chart title in PP
    orange — a fourth chart called 5200. It is a data row; the source prints it as one.
    """
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    out, head_next = ['<table class="chart">'], False
    for i, r in enumerate(rows):
        r = r + [""] * (width - len(r))
        filled = [c for c in r if c]
        if len(filled) == 1 and r[0]:
            out.append(f'<tr><th colspan="{width}">{html.escape(r[0])}</th></tr>')
            head_next = True
            continue
        tag = "th" if (head_next or i == 0) else "td"
        head_next = False
        out.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in r)
                   + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def expand_chart_slots(body: str, blocks: list[str]) -> tuple[str, list[str]]:
    """Fill every chart SLOT in the body from the article's own tables.

    Returns (body, [what was filled]). A body with no slots comes back untouched, so
    a hand-authored book that carries a literal table is unaffected.
    """
    tables = [b for b in blocks if MD_TABLE.match(re.sub(r"\s+", " ", b))]
    filled, seen = [], 0

    def one(m):
        nonlocal seen
        attrs, inner = m.group(1) or "", m.group(2)
        if "<tr" in inner.lower():
            if _SLOT_INDEX.search(attrs):
                raise Halt(
                    "ebook/body.html: a chart slot has rows typed into it as well as a "
                    "data-article-table index. It is one or the other, and it should be "
                    "the slot: write <table class=\"chart\" data-article-table=\"N\"></table> "
                    "EMPTY and the article's own cells are lifted into it.\n"
                    "    A number in this studio is a READING, not a value — nothing "
                    "re-types data the source already holds.")
            return m.group(0)              # a literal hand-authored table; leave it
        seen += 1
        want = int(_SLOT_INDEX.search(attrs).group(1)) if _SLOT_INDEX.search(attrs) else seen
        if want != seen:
            raise Halt(
                f"ebook/body.html: chart slot {seen} declares data-article-table="
                f"\"{want}\". Slots fill the article's tables IN ORDER, so this one is "
                f"table {seen}. Renumber it, or move the slot — the order on the page "
                f"has to be the order in the article.")
        if want > len(tables):
            raise Halt(
                f"ebook/body.html: chart slot declares data-article-table=\"{want}\" and "
                f"the source article contains {len(tables)} markdown table(s). A slot "
                f"names a table the article prints; there is nothing to lift here.")
        rows = _md_table_rows(tables[want - 1])
        htm = _chart_html(rows)
        # THE CONTROL, RUN EVERY TIME AND NOT ONLY IN A TEST. What the gate will read
        # off this table must be what it reads off the article — if the two ever
        # disagree, the lift is wrong and this is the moment to say so, not three
        # checks later where it would read as the writer's mistake.
        got = [t for t in (text_of(c.group(2)) for c in
                           re.finditer(r"<t[dh](\s[^>]*)?>(.*?)</t[dh]>", htm, re.S)) if t]
        expect = _table_cells(re.sub(r"\s+", " ", tables[want - 1]))
        if got != expect:
            raise Halt(
                f"CHART LIFT FAILED on article table {want} — the table this built is "
                f"not the table the article prints:\n      "
                f"{_first_cell_difference(expect, got)}\n"
                f"    This is a fault in author_ebook.py's own expansion, not in the "
                f"body. Nothing was written.")
        filled.append(f"article table {want} lifted into the body: {len(rows)} rows, "
                      f"{len(expect)} cells, verbatim from the capture")
        return htm

    return CHART_TABLE.sub(one, body), filled


# A paragraph OPENS WITH A HEADING when its first thing is a bold run. Both shapes the
# article uses count: "<b>WET TRACKS BETTING</b><br>prose" and "<b>AXIOM 2: Time and
# Distance.</b> prose". Requiring the <br> caught only 6 of 13 and left every axiom
# heading invisible to the layout engine.
#
# A heading that starts MID-paragraph cannot be helped by a paragraph-level class —
# EP13's AXIOM 1 sits after a <br> inside the opening paragraph, exactly as the source
# prints it, and §0a forbids moving it. Reported below rather than silently skipped.
HEAD_LEAD = re.compile(r"(<p)(\s[^>]*)?(>)(\s*<b>.*?</b>)", re.S | re.I)
MID_LEAD = re.compile(r"<br\s*/?>\s*<b>", re.I)


def mark_headings(body):
    """Tell the layout engine which paragraphs OPEN WITH A HEADING.

    The article writes its headings as inline bold at the head of a paragraph —
    "AXIOM 3: Track Variant." then a <br> then the prose — and §0a reproduces them
    exactly there. To the layout engine they are simply line one of a <p>, so it
    cannot keep a heading with its text, which is why `orphans` was reached for as a
    workaround: a blunt instrument that also welded ordinary paragraphs to figures
    and left a quarter-full page 2.

    This is MARKUP, NOT WORDS. It adds a class to the <p> and wraps nothing; every
    character of the article's text is untouched, and the fidelity gate — which
    strips tags before comparing — must still pass 28/28. That is asserted below.
    """
    marked = [0]

    def add_class(m):
        marked[0] += 1
        attrs = m.group(2) or ""
        if "class=" in attrs:
            attrs = re.sub(r'class="([^"]*)"', lambda c: f'class="{c.group(1)} haslead"', attrs)
        else:
            attrs += ' class="haslead"'
        return m.group(1) + attrs + m.group(3) + m.group(4)

    out = HEAD_LEAD.sub(add_class, body)
    mid = len(MID_LEAD.findall(body))
    print(f"headings marked: {marked[0]} paragraph(s) open with a bold lead-in "
          f"(markup only — the text is untouched)")
    if mid:
        print(f"  note: {mid} heading(s) sit MID-paragraph, where the source prints them. "
              f"A paragraph-level rule cannot keep those with their text, and §0a forbids "
              f"moving them.")
    return out


def source_article_path(ep, ep_dir):
    """The verbatim source article named in episode.json -> source.

    Same resolution as author_cards.source_article_text, so the e-book and the
    cards are checked against the SAME file. If they could differ, a figure could
    be traced to one article while the book reproduced another.
    """
    m = re.search(r"(docs/[\w\-.]+\.md)", ep.get("source", ""))
    if not m:
        raise Halt("episode.json -> source does not name a 'Verbatim source: docs/....md' "
                   "file, so the e-book body cannot be checked against anything.")
    rel = m.group(1)
    for base in (os.path.dirname(os.path.dirname(os.path.abspath(ep_dir))), ep_dir):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    raise Halt(f"source article {rel!r} named in episode.json was not found on disk")


# ------------------------------------------------------------------ body parsing

def strip_comments(s: str) -> str:
    """Remove HTML comments before ANY matching. Comments are not content.

    FOUND BY USING THIS ON EP13, THE DAY AFTER IT WAS WRITTEN. EP13's body carries a
    header comment that explains the fidelity rule, and that explanation contains the
    words "every bare <p>". The paragraph regex matched that `<p>` inside the comment,
    ran on to the next real `</p>`, and reported the COMMENT as a body paragraph that
    is not in the source article.

    This is the same bug the cover template's header records from 26 Jul 2026: a script
    matched an EXAMPLE INSIDE A HEADER COMMENT and acted on it. It cost a real halt
    there and it cost one here. **A file's prose about its own markup will look like
    markup to anything that does not strip comments first.**

    The emitted page KEEPS its comments — they are the audit trail. Only the check
    strips them.
    """
    return re.sub(r"<!--.*?-->", " ", s, flags=re.S)


def declared_source_figures(ebook: dict) -> dict:
    """`ebook.source_figures[]` — images that reproduce the SOURCE, not a card.

    THE RULE THIS EXISTS BESIDE, WHICH IS UNCHANGED: every figure in the book is a
    print render of a motion card, so the book cannot drift from the video.

    THE CASE IT DOES NOT COVER (PP-STANDARDS §0a-i, ratified 4 Aug 2026): a source
    table that exists only as a SCAN on the original page. "The scan IS the article.
    Embedding it is the most faithful reproduction available, not the least." EP16's
    two Dedman tables carry ~500 cells between them and hand-transcribing them would
    invent a new way to publish a wrong number.

    ⚠️ IT NAMES FILES, IT DOES NOT OPEN A CLASS. Only the exact filenames declared
    here may appear, each with a written reason. A new class must never become a way
    round the fidelity check.
    """
    out = {}
    for i, entry in enumerate(ebook.get("source_figures") or [], 1):
        if not isinstance(entry, dict):
            raise Halt(f"episode.json -> ebook.source_figures[{i}] must be an object "
                       f'like {{"src": "table-1.jpg", "why": "..."}}.')
        src = str(entry.get("src") or "").strip()
        why = str(entry.get("why") or "").strip()
        if not src:
            raise Halt(f"episode.json -> ebook.source_figures[{i}] has no 'src'.")
        if not why:
            # THE REASON IS NOT OPTIONAL — same discipline as build.audio_kbps_floor.
            # An exception that can exist without a written reason becomes a silent
            # normal: the next episode copies the key and nobody remembers why the
            # book stopped being a render of the video.
            raise Halt(
                f"episode.json -> ebook.source_figures[{i}] declares {src!r} but gives "
                f"no reason, so I have not applied it. Reproducing a SOURCE image "
                f"instead of a card render is allowed; doing it without writing down "
                f"WHY is not, because the next episode copies the key and the book "
                f"quietly stops being a render of the video. Add 'why'.")
        out[src] = why
    return out


def parse_body(body: str, source_figures: dict | None = None):
    """Pull the body apart into what must be checked and what must not.

    Returns (prose, quoted, figures). `prose` is the plain `<p>` text in order —
    the article's own sentences. `quoted` is blockquote/pullquote text, which must
    be traceable into the article but need not be a whole paragraph. `figures` is
    the figure numbers referenced, in order.

    `source_figures` is {filename: why} from ebook.source_figures[] — the ONLY
    non-figure-N.png images permitted, and only by exact name.
    """
    source_figures = source_figures or {}
    body = strip_comments(body)
    # THE ROGUE-'?' RULE, applied BEFORE the fidelity comparison so that anything
    # it changes is visible to the gate rather than slipped past it. It cannot
    # touch a bare <p>, so the comparison is unaffected by construction — and if
    # that ever stopped being true, the gate would fail loudly on the next run
    # rather than quietly shipping edited prose.
    body, _rogues = clean_furniture(body)
    if _rogues:
        print(f"rogue '?' removed from furniture: {_rogues} "
              f"(article prose is never touched — see the note by _ROGUE_Q)")
    for bad in ("<script", "<style", "<link", "<meta", "<iframe", "<html", "<body"):
        if bad in body.lower():
            raise Halt(f"ebook/{BODY_FILE} contains {bad!r}. The body is the ARTICLE BODY "
                       f"only — the shell (page setup, logo, cover slot, marketing and "
                       f"warranty pages) comes from assets/ebook-template.html and the "
                       f"body must not carry its own.")
    for phrase in SHELL_TEXT:
        if phrase.lower() in body.lower():
            raise Halt(f"ebook/{BODY_FILE} contains {phrase!r}, which belongs to a STANDING "
                       f"page in the shell. The marketing and warranty pages are copied "
                       f"byte-identical from the template; a second copy in the body would "
                       f"print the page twice and the second one would not be the approved "
                       f"text. Delete it from the body.")

    for tag in set(t.lower() for t in re.findall(r"<\s*([a-zA-Z][\w-]*)", body)):
        if tag not in TAGS_OK:
            raise Halt(f"ebook/{BODY_FILE} uses <{tag}>, which is not in the e-book class "
                       f"vocabulary (PP-STANDARDS §E-book). Allowed: "
                       f"{', '.join(sorted(TAGS_OK))}.")

    # headings must carry the template's classes, or the shell has no styling for them
    for tag, want in (("h1", "section"), ("h2", "rule")):
        for m in re.finditer(rf"<{tag}(\s[^>]*)?>", body):
            cls = re.search(r'class="([^"]*)"', m.group(0) or "")
            if not cls or cls.group(1).strip() != want:
                raise Halt(f'ebook/{BODY_FILE}: every <{tag}> must be '
                           f'<{tag} class="{want}"> (PP-STANDARDS §E-book names the class '
                           f'vocabulary, and the shell only styles those). Found: '
                           f'{m.group(0)}')

    for m in re.finditer(r"<img\b[^>]*>", body):
        cls = re.search(r'class="([^"]*)"', m.group(0))
        src = re.search(r'src="([^"]*)"', m.group(0))
        if not cls or cls.group(1).strip() not in IMG_CLASSES:
            raise Halt(f"ebook/{BODY_FILE}: a figure must be "
                       f'class="illus" (or "illus portrait"). Found: {m.group(0)[:120]}')
        if not src or not re.fullmatch(r"figure-(\d+)\.png", src.group(1)):
            name = src.group(1) if src else ""
            if name in source_figures:
                # A DECLARED SOURCE FIGURE — announce it, so a reproduction of the
                # original page can never be mistaken for a render of a card.
                print(f"    ⚠️ SOURCE FIGURE, NOT A CARD RENDER: {name} — "
                      f"{source_figures[name][:300]}", file=sys.stderr)
            else:
                raise Halt(
                    f"ebook/{BODY_FILE}: a figure's src must be figure-N.png — the print "
                    f"render build_figures.py makes from the motion card, so the book "
                    f"cannot drift from the video. Found: {m.group(0)[:120]}\n"
                    f"    If this image reproduces the SOURCE ARTICLE rather than a card "
                    f"(PP-STANDARDS §0a-i — a scanned table is reproduced as the scan), "
                    f"declare it by name in episode.json -> ebook.source_figures[] with a "
                    f"'why'. It must be declared file by file; there is no class or "
                    f"pattern that lets one through.")
        if 'alt="' not in m.group(0):
            raise Halt(f"ebook/{BODY_FILE}: every figure needs alt text. Found: "
                       f"{m.group(0)[:120]}")
    figures = [int(n) for n in re.findall(r'src="figure-(\d+)\.png"', body)]
    # THE HEADINGS, IN ORDER, as text. Collected so check_fidelity can RECOGNISE that an
    # article line the body promotes to a heading has been reproduced — see the note on
    # `headings` there. They are already known to carry the right class (checked above).
    headings = [t for t in
                (text_of(m.group(2))
                 for m in re.finditer(r"<h([123])(?:\s[^>]*)?>(.*?)</h\1>", body, re.S))
                if t]

    # ── THE ORDERED WALK: bare <p> AND <li>, in the order they appear on the page ──
    # One sweep over both, because the fidelity walk is about ORDER and two separate
    # passes cannot say which came first. `prose` is a list of (kind, text) pairs —
    # ONE list, so the kind can never drift away from the words it describes.
    prose, quoted = [], []
    for m in re.finditer(r"<p(\s[^>]*)?>(.*?)</p>|<li(\s[^>]*)?>(.*?)</li>", body, re.S):
        if m.group(0)[:2].lower() == "<p":
            cls = re.search(r'class="([^"]*)"', m.group(1) or "")
            key = cls.group(1).strip() if cls else None
            if key not in P_CLASSES:
                raise Halt(f'ebook/{BODY_FILE}: <p class="{key}"> is not in the e-book '
                           f"class vocabulary. Allowed: a bare <p> for the article's own "
                           f"prose, or {', '.join(repr(k) for k in P_CLASSES if k)}. A new "
                           f"class is not a way round the fidelity check.")
            t = text_of(m.group(2))
            if not t:
                continue
            if key is None:
                prose.append(("p", t))
            elif key == "pullquote":
                quoted.append(t)
        else:
            t = text_of(m.group(4))
            if not t:
                continue
            prose.append(("li", t))
    for m in re.finditer(r"<blockquote(\s[^>]*)?>(.*?)</blockquote>", body, re.S):
        t = text_of(m.group(2))
        if t:
            quoted.append(t)

    # THE CHART TABLES, as cell lists, in order. Collected the same way headings are,
    # and for the same reason: so check_fidelity can RECOGNISE that the article's table
    # is on the page and then VERIFY it, rather than being told it is absent.
    tables = []
    for m in re.finditer(r"<table(\s[^>]*)?>(.*?)</table>", body, re.S):
        cls = re.search(r'class="([^"]*)"', m.group(1) or "")
        key = cls.group(1).strip() if cls else None
        if key not in TABLE_CLASSES:
            raise Halt(
                f'ebook/{BODY_FILE}: every table must be <table class="chart">, which is '
                f"the ONE element allowed to reproduce a table the article prints, and it "
                f"is checked cell for cell against it. Found: {m.group(0)[:120]}")
        inner = m.group(2)
        for bad in ("<p", "<li", "<img", "<h1", "<h2", "<blockquote"):
            if bad in inner.lower():
                raise Halt(
                    f'ebook/{BODY_FILE}: a <table class="chart"> contains {bad!r}. A chart '
                    f"table carries the article's CELLS and nothing else — article prose "
                    f"lives in a bare <p> where the fidelity walk can see it, and a "
                    f"paragraph hidden inside a table cell would never be compared to "
                    f"anything.")
        tables.append([t for t in (text_of(c.group(2))
                                   for c in re.finditer(r"<t[dh](\s[^>]*)?>(.*?)</t[dh]>",
                                                        inner, re.S))
                       if t])

    # EACH LIST ITEM AND THE FIGURES INSIDE IT. This is what lets the gate say that
    # figure 3 sits with tip 23 rather than in a pile at the end of the book.
    items = [(text_of(m.group(1)),
              [int(n) for n in re.findall(r'src="figure-(\d+)\.png"', m.group(1))])
             for m in re.finditer(r"<li(?:\s[^>]*)?>(.*?)</li>", body, re.S)]
    items = [(t, f) for t, f in items if t]
    ols = [m.group(1) or "" for m in re.finditer(r"<ol(\s[^>]*)?>", body)]
    return prose, quoted, figures, headings, items, ols, tables


# ------------------------------------------------------------------ the gate

def first_difference(a: str, b: str) -> str:
    """Point at the first word that differs. This message is the whole value of
    the check — 'the body does not match' is useless, 'firstup vs first-up' is
    the finding."""
    aw, bw = a.split(" "), b.split(" ")
    for i in range(max(len(aw), len(bw))):
        x = aw[i] if i < len(aw) else "<end of paragraph>"
        y = bw[i] if i < len(bw) else "<end of paragraph>"
        if x != y:
            lead = " ".join(aw[max(0, i - 6):i])
            return (f"word {i + 1}: the body says {x!r} where the article says {y!r}"
                    + (f"  (…{lead} ▸{x}◂ …)" if lead else ""))
    return "the paragraphs differ only in whitespace"


def closest(target: str, pool: list[str]) -> int:
    """Index of the article paragraph the body paragraph most likely IS.

    Compared as WORD sequences with autojunk off. Both matter: on character
    sequences longer than 200 chars difflib's autojunk heuristic treats any
    character occurring in more than 1% of the string as junk — which is every
    letter in a paragraph of prose — so a paragraph differing by ONE WORD scored
    0.32 and fell under the threshold. The failure message then said "no article
    paragraph is even close" about a paragraph that was 59 words out of 60
    identical, which is precisely the case this hint exists to explain.
    """
    import difflib
    tw = target.split(" ")
    best, score = -1, 0.0
    for i, cand in enumerate(pool):
        s = difflib.SequenceMatcher(None, tw, cand.split(" "), autojunk=False).ratio()
        if s > score:
            best, score = i, s
    return best if score > 0.5 else -1


# ── AN ARTICLE LINE THE BODY SETS AS A HEADING, OR SHOWS AS A FIGURE ─────────────
#
# 🔴 EP19, 9 Aug 2026, AND THIS IS THE "RECOGNISE, DON'T EXCUSE" FIX. check_fidelity
# walks the article's paragraphs against the body's BARE <p> paragraphs, so any article
# line the body promotes to a HEADING read as a paragraph that had been skipped. The
# sanctioned answer was `omit_paragraphs`, whose own halt message says so: "Most
# episodes need one entry: the article's own headline line, which is set as the h1
# section heading rather than as body prose."
#
# EP19 was the first article whose SUB-headings are standalone paragraphs, so it needed
# SIX of those entries plus a seventh for its table. THAT IS A HOLE, NOT A FIX:
#   · declaring a heading "omitted" tells the checker NOT TO LOOK FOR IT, so a body
#     whose <h2> said "THE 10K PLAN" would sail through;
#   · seven declarations is enough for a genuinely dropped paragraph to hide among.
# EP19's five were verified BY HAND, which is exactly what a gate is meant to replace.
#
# So the gate now RECOGNISES both shapes, and VERIFIES each:
#   · a bold-only article paragraph is satisfied by a heading whose text is IDENTICAL;
#   · a markdown-table paragraph is satisfied by a figure of the CARD that renders it,
#     cross-checked cell by cell against that card's own content in episode.json.
# Neither is a free pass: if the words differ, it is still a skipped paragraph and the
# build still halts. `omit_paragraphs` goes back to meaning only "deliberately left out".
BOLD_ONLY = re.compile(r"^\*\*(.+?)\*\*$")
MD_TABLE = re.compile(r"^\|.*\|.*\|-{2,}")


def _squash(s: str) -> str:
    """Letters and digits only, lowercased — for comparing a table cell to a card.

    ONE function, used on BOTH sides of every comparison below. Two different
    normalisations is not a comparison, it is two descriptions of different things that
    happen to be tested against each other.
    """
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _table_cells(paragraph: str) -> list[str]:
    """The values in a markdown-table paragraph, separators dropped."""
    out = []
    for cell in paragraph.split("|"):
        c = cell.strip()
        if c and not re.fullmatch(r":?-{2,}:?", c):
            out.append(c)
    return out


def _card_for_figure(ep: dict, n: int) -> dict | None:
    cid = next((f.get("card") for f in ep.get("figures") or [] if f.get("n") == n), None)
    return next((c for c in ep.get("cards") or [] if c.get("id") == cid), None)


def _why_not(paragraph: str, headings, near_misses) -> str:
    """Say WHY a heading or table was not recognised, rather than only that it wasn't.

    Without this the message reads "the body skips **THE 10K SYSTEM**" about a body that
    has THE 10K PLAN on the page in 62px type — true, useless, and the reader concludes
    the gate is broken rather than that the words are wrong.
    """
    m = BOLD_ONLY.fullmatch(paragraph.strip())
    if m:
        want = re.sub(r"\s+", " ", m.group(1)).strip()
        # ⚠️ CHARACTER-LEVEL, not `closest()`. closest() compares WORD LISTS, which is
        # right for a paragraph and useless for a heading: "A SUB-HEADING" against
        # "A SUB HEEDING" shares one word out of two-or-three and scores 0.40, so the
        # nearest match was reported as "no match" and the writer was told the body had
        # no such heading while it sat on the page one letter wrong.
        best, score = None, 0.0
        for h in headings:
            s = difflib.SequenceMatcher(None, h, want, autojunk=False).ratio()
            if s > score:
                best, score = h, s
        if best is not None and score >= 0.55:
            return (f"\n    This is a HEADING in the article, and the body has one near "
                    f"it — but not the same words:\n"
                    f"      {first_difference(best, want)}\n"
                    f"    A heading is recognised only when its text is IDENTICAL. Fix "
                    f"the heading; do not declare it omitted.")
        return ("\n    This is a HEADING in the article and the body has no heading "
                "carrying these words. Set it as <h2 class=\"rule\">, and it will be "
                "recognised and checked word for word.")
    if MD_TABLE.match(paragraph.strip()):
        # THE CHART CASE ALWAYS SAYS WHAT TO DO. Before this, a table with no card and
        # no near miss produced no explanation at all, and the only move the writer
        # could see was `omit_paragraphs` — which is exactly how EP26 came to declare a
        # chart dropped. There is a legal way to keep it; the halt has to name it.
        return ("\n    " + "\n    ".join(near_misses) if near_misses else "") + (
            "\n    THIS IS A CHART, AND A CHART IS KEPT. Declare an EMPTY SLOT where "
            "the article prints it —\n"
            '      <table class="chart" data-article-table="1"></table>\n'
            "    — and the article's own cells are lifted into it. DO NOT TYPE THE "
            "CELLS: data is lifted from the source, never re-typed, and a slot with "
            "rows in it is refused. If one of this episode's motion CARDS already "
            "renders the grid, place that figure instead and it will be recognised. "
            "Do not do both, and never declare a chart omitted: the prose refers to "
            "it, and a book without it prints sentences about a table the reader "
            "cannot see.")
    return ""


def _card_missing(card: dict, paragraph: str, cells: list[str]) -> tuple[list, list]:
    """What a card LACKS of the article table it claims to render: (numbers, cells).

    Empty and empty means the card carries the table. ONE function, because two places
    now ask this question — the recognition loop, and the double-print check that has
    to know whether a card carries a table the body ALSO typed out. Two copies of a
    comparison is two comparisons that drift.

    WHAT "THE CARD CARRIES THIS TABLE" HAS TO MEAN, and the naive version does not
    work: a cell reads "Win 9 pts" while the card holds place:"Win" and
    points:["9 pts"] separately, so the cell text never appears contiguously. Comparing
    the whole cell would reject a card that renders the table perfectly. So: EVERY
    NUMBER THE TABLE STATES must be in the card, and every word of every cell must be
    too. The numbers are the claim — a card missing one is not a reproduction of this
    table, whatever it looks like.

    ⚠️ BOTH SIDES SQUASHED BY THE SAME FUNCTION. The first version stripped all
    punctuation from the word but only whitespace from the card, so "2nd-last" became
    "2ndlast" and was hunted for inside "2nd-laststart" — never found, and the table was
    reported unreproduced by a card that reproduces it exactly. Asymmetric normalisation
    is a comparison between two different things.
    """
    blob = json.dumps(card.get("content") or {}, ensure_ascii=False).lower()
    flat = _squash(blob)
    want_nums = sorted(re.findall(r"\d+(?:\.\d+)?", paragraph))
    have_nums = re.findall(r"\d+(?:\.\d+)?", blob)
    lost_n = [x for x in want_nums if x not in have_nums]
    lost_w = [c for c in cells
              if any(_squash(w) and _squash(w) not in flat for w in c.split())]
    return lost_n, lost_w


def _first_cell_difference(want: list[str], got: list[str]) -> str:
    """Point at the first cell that differs, the way first_difference points at a word.

    "the table does not match" sends the writer back to re-type 225 cells. "cell 47:
    the body says '1182' where the article says '1187'" is the finding.
    """
    for i in range(max(len(want), len(got))):
        a = want[i] if i < len(want) else "<end of table>"
        b = got[i] if i < len(got) else "<end of table>"
        if a != b:
            return (f"cell {i + 1}: the article says {a!r} where the body says {b!r}"
                    f"  ({len(want)} cells in the article, {len(got)} in the body)")
    return "the tables differ only in whitespace"


def _satisfied_elsewhere(art, ep, headings, figures, tables=None) -> tuple[dict, list]:
    """Which article paragraphs the body reproduces somewhere other than a bare <p>.

    Returns ({index: why}, [complaints]). A complaint is a NEAR miss — the body has a
    heading or a figure in that position but the words do not match — and it is a
    complaint precisely so that "recognise" can never soften into "ignore".
    """
    got, notes = {}, []
    pool = list(headings)
    tpool = [list(t) for t in (tables or [])]      # consumed as headings are consumed
    for i, p in enumerate(art):
        # THE BOLD MARKERS ARE THE ARTICLE'S OWN MARKUP, not part of the words — an
        # article that writes "**THE 10K SYSTEM**" and a body that sets "THE 10K SYSTEM"
        # as a heading say the same thing. A paragraph with no markers is compared as it
        # stands, which is what closes the ORIGINAL case this hole was opened for: the
        # article's headline line, set as h1.section. With that recognised too,
        # `omit_paragraphs` finally means only "deliberately left out" and EP19 needs no
        # entries at all.
        m = BOLD_ONLY.fullmatch(p.strip())
        want = re.sub(r"\s+", " ", (m.group(1) if m else p)).strip()
        if want in pool:
            pool.remove(want)              # consumed: two identical headings need two
            got[i] = f"set as a heading: {want!r}"
            continue
        if m:
            continue                       # a heading in the article, absent from the body
        if MD_TABLE.match(p.strip()):
            cells = _table_cells(p)
            # ── FIRST: IS THE CHART ON THE PAGE AS A CHART? ──────────────────────
            # Cell for cell, in order, folding nothing but whitespace — a stricter
            # comparison than the card path below, because here the body claims to BE
            # the table rather than to picture it. Matched by content, not position,
            # and consumed, so two identical charts need two tables in the body.
            as_table = next((k for k, t in enumerate(tpool) if t == cells), None)
            if as_table is not None:
                tpool.pop(as_table)
                # 🔴 BOTH IS A DOUBLE PRINT, AND THAT IS THE EP19 FAULT VERBATIM: the
                # body typed the grid AND placed the card figure of the same grid, and
                # the same nine numbers appeared twice on the page. Recognising the
                # table must not quietly make that legal.
                def _also_a_card(n, _p=p, _cells=cells):
                    c = _card_for_figure(ep, n)
                    return bool(c) and not any(_card_missing(c, _p, _cells))
                twice = next((n for n in figures if _also_a_card(n)), None)
                if twice is not None:
                    raise Halt(
                        f"E-BOOK CHART: the article's table is on the page TWICE — once "
                        f'as a <table class="chart"> and again as figure {twice}, the '
                        f"render of card {_card_for_figure(ep, twice).get('id')}, which "
                        f"carries the same values.\n"
                        f"    Print it ONE way. The card figure is the better one where "
                        f"a card genuinely renders the grid, because the book then cannot "
                        f"drift from the video; the chart table is for a data chart no "
                        f"card carries. EP19 did both and the same nine numbers appeared "
                        f"twice on the page.")
                got[i] = (f"reproduced as a chart table — all {len(cells)} cells, in "
                          f"order, character for character")
                continue
            # SECOND: does a CARD carry it? (EP19 — the grid the video already draws.)
            for n in figures:
                card = _card_for_figure(ep, n)
                if not card:
                    continue
                lost_n, lost_w = _card_missing(card, p, cells)
                if not lost_n and not lost_w:
                    got[i] = (f"carried by figure {n} — the render of card "
                              f"{card.get('id')}, which holds every number it states "
                              f"and every word of its {len(cells)} cells")
                    break
                notes.append(
                    f"figure {n} (card {card.get('id')}) is the nearest thing to the "
                    f"article's table, but it does not carry "
                    + (f"the number(s) {lost_n[:4]}" if lost_n
                       else f"the cell(s) {lost_w[:3]}")
                    + " — so it is not a reproduction of it")
            # THIRD: say what the body's OWN tables got wrong, if it has any. Without
            # this, a chart typed with one digit out reports as "the body skips this
            # paragraph" about a chart sitting on the page — true, useless, and the
            # writer's next move is to declare it omitted.
            if i not in got:
                for t in tpool:
                    notes.append(
                        'a <table class="chart"> in the body is close to the article\'s '
                        "table but is not it — " + _first_cell_difference(cells, t))
    # WHAT IS LEFT OVER IS THE OTHER HALF OF THE BARGAIN. A body table that reproduces
    # NO article table has never been compared to anything — it would be the one place
    # in the book where words appear unchecked, which is precisely what the vocabulary
    # was closed to prevent. The caller refuses it.
    return got, notes, tpool


def check_list_shape(art: list[str], items, ols):
    """THE CHECK EP25 WOULD HAVE FAILED ON SIGHT: N numbered items, N list items.

    The article of record either is a numbered list or it is not, and that question is
    answered by COUNTING the article's own numbered paragraphs — nothing is configured,
    nothing is declared, and no episode can opt out. If the source numbers fifty tips
    and the body carries one paragraph, this says so and stops.

    It also pins the RENDERED numbering, which is the part a reader actually sees: one
    `<ol>` holding all of them, starting where the article starts. Split the list across
    two `<ol>`s and the second silently restarts at 1 — the book would print two tip
    ones, and every word in it would still be character-perfect.
    """
    numbered = [split_number(p)[0] for p in art if split_number(p)[0] is not None]
    if not numbered:
        if items:
            raise Halt(
                f"ebook/{BODY_FILE} uses {len(items)} <li> list item(s), but the source "
                f"article has no numbered list in it. A list the article does not print "
                f"is structure we invented, and §0a's mirror applies to shape as well as "
                f"to words: never add what the article does not say.")
        return None
    n = len(numbered)
    if len(items) != n:
        raise Halt(
            f"E-BOOK LIST SHAPE: the source article is a NUMBERED LIST of {n} items, and "
            f"the body contains {len(items)} list item(s).\n"
            f"    The article numbers them {numbered[0]} to {numbered[-1]}; each one is "
            f"its own paragraph in the capture and each one must be its own <li>.\n"
            f"    This is EP25's fault exactly: all {n} tips were reproduced inside a "
            f"single <p>, every character correct, and the book printed a 3,900-word "
            f"block where the article prints a numbered list. A reproduction can be "
            f"character-perfect and still not be the article.")
    if numbered != list(range(numbered[0], numbered[0] + n)):
        raise Halt(
            f"E-BOOK LIST SHAPE: the article's numbering is not contiguous — it runs "
            f"{numbered[:3]}…{numbered[-3:]}. The capture writes the article's own "
            f"numbers, so this says the SOURCE skips or repeats one. That is an "
            f"editorial judgement about the article of record, not something to "
            f"renumber quietly.")
    if len(ols) != 1:
        raise Halt(
            f"E-BOOK LIST SHAPE: the body has {len(ols)} <ol> element(s) and needs "
            f"exactly one. An <ol> restarts at 1 unless told otherwise, so splitting "
            f"{n} items across {len(ols)} lists would print more than one item number "
            f"{numbered[0]} — with every word still correct. Put a figure INSIDE the "
            f"<li> it illustrates rather than breaking the list around it.")
    m = re.search(r'start\s*=\s*"?(\d+)', ols[0] or "")
    start = int(m.group(1)) if m else 1
    if start != numbered[0]:
        raise Halt(
            f"E-BOOK LIST SHAPE: the article's list starts at {numbered[0]} and the "
            f'body\'s <ol> starts at {start}. Write <ol start="{numbered[0]}"> so the '
            f"printed numbers are the article's own.")
    return (f"list shape: {n} numbered items, one <ol> starting at {numbered[0]} — "
            f"the article's own numbering")


def check_figure_placement(ep, art: list[str], items, figures):
    """A figure belongs BESIDE THE TIP IT ILLUSTRATES, and the card says which one.

    🔴 EP25's six figures were all placed after the last tip, where they illustrate
    nothing — the reader meets a picture of the betting bank thirty-nine tips after the
    tip about the betting bank. Nothing caught it, because `check_figures` only asks
    whether the right figures are PRESENT.

    WHICH tip is DERIVED, never declared (rule #7): each figure maps to a card, and the
    card already carries a `trace` whose values are the article's own sentences. The tip
    a figure belongs to is the numbered item those sentences live in. So the coverage
    cannot go stale — adding a figure adds its own answer, and a card whose trace does
    not reach the list is simply not required to sit in it.
    """
    if not items:
        return None
    numbered = [(i, split_number(p)) for i, p in enumerate(art)]
    tips = [(num, words) for _i, (num, words) in numbered if num is not None]
    where = {}                       # figure -> the tip number its card traces into
    for n in sorted(set(figures)):
        card = _card_for_figure(ep, n)
        if not card:
            continue
        sentences = [v for v in (card.get("trace") or {}).values()
                     if isinstance(v, str) and len(v.split()) >= 4]
        if not sentences:
            continue
        score = {}
        for num, words in tips:
            hit = sum(1 for s in sentences if _squash(s) and _squash(s) in _squash(words))
            if hit:
                score[num] = max(score.get(num, 0), hit)
        if score:
            where[n] = max(score, key=lambda k: (score[k], -k))
    if not where:
        return None

    first = tips[0][0]
    holder = {}                      # figure -> the tip number whose <li> holds it
    for idx, (_text, figs) in enumerate(items):
        for f in figs:
            holder[f] = first + idx
    wrong, missing = [], []
    for n, tip in sorted(where.items()):
        if n not in holder:
            missing.append((n, tip))
        elif holder[n] != tip:
            wrong.append((n, tip, holder[n]))
    if missing or wrong:
        bits = []
        for n, tip in missing:
            bits.append(f"figure {n} illustrates tip {tip} and does not sit in it — "
                        f"it is outside the list altogether")
        for n, tip, got in wrong:
            bits.append(f"figure {n} illustrates tip {tip} but sits in tip {got}")
        raise Halt(
            "E-BOOK FIGURES: a figure belongs beside the tip it illustrates.\n      "
            + "\n      ".join(bits)
            + f"\n    Each figure is the print render of a card, and that card's trace "
              f"names the article sentence it came from — which is how the tip above "
              f"was worked out, not from a list anybody maintains. Put the <img> "
              f"INSIDE that <li>, after the tip's words.\n"
              f"    EP25 put all six at the end of the book, where a picture of the "
              f"betting bank landed thirty-nine tips after the tip about the betting "
              f"bank. Every figure was present and correct; not one of them was next "
              f"to the thing it explains.")
    return (f"figure placement: {len(where)} figure(s) sit in the tip their card traces "
            f"to (" + ", ".join(f"figure {n}->tip {t}" for n, t in sorted(where.items()))
            + ")")


def check_fidelity(prose, quoted, ep, article: list[str], headings=None, figures=None,
                   tables=None):
    """HARD-FAIL unless the body reproduces the article, departures aside.

    Returns a plain-English report of what it verified, so a passing build says
    what it checked instead of only that it passed.
    """
    ebook = ep.get("ebook") or {}
    declared = ebook.get("departures")
    if declared is None:
        raise Halt("episode.json -> ebook.departures is MISSING. Write [] if the body "
                   "reproduces the article with no departures at all; a missing key halts "
                   "on purpose, because absence records nothing and this list is the only "
                   "thing standing between a print-friendly tidy and a silent rewrite.")
    if not isinstance(declared, list):
        raise Halt("episode.json -> ebook.departures must be a list of departure NAMES.")

    fns = []
    for name in declared:
        if name not in DEPARTURES:
            raise Halt(f"unknown declared departure {name!r}. Departures are a fixed "
                       f"vocabulary, not free text, so episode.json cannot describe an "
                       f"arbitrary transform. Known: "
                       f"{', '.join(sorted(DEPARTURES))}. Adding one is a code change.")
        fns.append((name, *DEPARTURES[name]))

    art = list(article)
    for name, fn, _desc in fns:
        after = [fn(p) for p in art]
        if after == art:
            raise Halt(f"declared departure {name!r} changes NOTHING in this article, so it "
                       f"is not a departure this episode makes. Remove it — a departure "
                       f"list that gets copied forward unchanged stops meaning anything.")
        art = after
    art_joined = " \n ".join(art)

    # omissions must be declared by QUOTING the paragraph, so nothing can be
    # dropped without writing down what was dropped
    omits = ebook.get("omit_paragraphs")
    if omits is None:
        raise Halt("episode.json -> ebook.omit_paragraphs is MISSING. Write [] if the body "
                   "reproduces every paragraph of the article. Most episodes need one "
                   "entry: the article's own headline line, which is set as the h1 section "
                   "heading rather than as body prose.")
    omitted = set()
    for quote in omits:
        # 🔴 A CHART IS NEVER "LEFT OUT" (Jodie, 15 Aug 2026). Asked BEFORE the match,
        # because EP26's entry matched nothing — and "it matches 0 paragraphs" sends the
        # writer off to re-quote a table it must not be quoting at all. The ruling is
        # about the CHART, not about the quoting of it, so the message has to be too.
        if MD_TABLE.match(re.sub(r"\s+", " ", quote.strip())):
            raise Halt(
                f"ebook.omit_paragraphs declares a CHART: {quote[:60]!r}…\n"
                f"    A CHART IS KEPT. A chart the article prints goes IN THE BOOK — it "
                f"is a figure that is "
                f"kept, never a paragraph that is quoted away — the article's prose points "
                f"at these charts by name, and a book that drops them prints sentences "
                f"about a table the reader cannot see.\n"
                f"    Declare an EMPTY SLOT where the article prints it — "
                f'<table class="chart" data-article-table="1"></table> — and the '
                f"article's own cells are lifted into it. DO NOT TYPE THE CELLS. If a "
                f"motion CARD already renders this grid, place that figure instead; do "
                f"not do both.")
        # WHITESPACE IS COLLAPSED ON BOTH SIDES, and it has to be. article_paragraphs()
        # collapses a paragraph's own line breaks (a newline in markup is not a
        # difference in the prose — the same reasoning as text_of), so a quote copied
        # out of the capture file with its line breaks intact could NEVER match a
        # multi-line block. That is not a strictness, it is a comparison between two
        # different things: EP26's table quote was character-perfect and matched 0.
        q = re.sub(r"\s+", " ", quote.strip())
        hits = [i for i, p in enumerate(article) if p.startswith(q)]
        if len(hits) != 1:
            raise Halt(f"ebook.omit_paragraphs entry {quote[:60]!r} matches the start of "
                       f"{len(hits)} article paragraphs (needs exactly 1). Quote the "
                       f"paragraph you are leaving out, verbatim from the article — you do "
                       f"not get to drop a paragraph without saying which one.")
        omitted.add(hits[0])

    # …and what the body reproduces somewhere OTHER than a bare <p>: a heading with
    # identical words, or a figure of the card that renders the article's table. These
    # are RECOGNISED and verified, never declared away — see the note by BOLD_ONLY.
    elsewhere, near_misses, spare = _satisfied_elsewhere(
        art, ep, headings or [], figures or [], tables or [])
    if spare:
        # WHICH FAULT IT IS DEPENDS ON WHETHER THERE WAS A TABLE TO REPRODUCE. A chart
        # typed with one digit out and a chart invented from nothing are different
        # mistakes with different fixes, and "reproduces no table in the source article"
        # about a 225-cell grid that is 224 cells right would send the writer to retype
        # the lot instead of to cell 47.
        if near_misses:
            raise Halt(
                'E-BOOK CHART: the body\'s <table class="chart"> is not the article\'s '
                "table.\n      " + "\n      ".join(near_misses[:3])
                + "\n    A chart is checked cell for cell, in order, folding nothing but "
                  "whitespace — it is the article's own grid or it is not. Fix the cell; "
                  "do not declare the chart omitted.")
        raise Halt(
            f'E-BOOK CHART: the body carries {len(spare)} <table class="chart"> that '
            f"reproduces no table in the source article. Its first cells are "
            f"{spare[0][:6]}.\n"
            f"    A chart table is allowed for ONE reason — to keep a chart the article "
            f"prints — and it is checked cell for cell against it. A table the article "
            f"does not print is invented structure with invented numbers in it, and it "
            f"would be the only place in the book where words appear unchecked.\n"
            f"    §0a's mirror: never add what the article does not say.")
    # AN ENTRY THAT IS NOW REDUNDANT IS A BUG, NOT A TIDY. If a paragraph is both
    # declared omitted AND visibly reproduced, one of the two is wrong, and the
    # dangerous one is the declaration: it stops the checker looking at words that ARE
    # on the page. Say so rather than silently preferring either.
    both = sorted(set(omitted) & set(elsewhere))
    if both:
        raise Halt(
            "ebook.omit_paragraphs declares paragraph(s) the body actually REPRODUCES:\n"
            + "\n".join(f"      {art[i][:70]!r} — {elsewhere[i]}" for i in both)
            + "\n    omit_paragraphs means DELIBERATELY LEFT OUT. Declaring something "
              "that is on the page stops the checker verifying its words, which is how "
              "a typo in a heading would ship. Remove the entry; the gate now "
              "recognises it on its own.")
    accounted = omitted | set(elsewhere)

    # every prose paragraph must be an article paragraph, in order, once each — AND IN
    # THE RIGHT ELEMENT. A numbered article paragraph is reproduced by an <li>, an
    # unnumbered one by a bare <p>; the number is the article's own markup and is
    # stripped before the words are compared, so the comparison still folds nothing.
    ai, matched, as_items = 0, 0, 0
    for kind, bp in prose:
        def fits(i, _bp=bp, _kind=kind):
            num, words = split_number(art[i])
            return words == _bp and (num is not None) == (_kind == "li")
        k = next((i for i in range(ai, len(art)) if fits(i)), None)
        if k is None:
            # BEFORE BLAMING THE WORDS, ASK WHETHER ONLY THE ELEMENT IS WRONG. The body
            # reproducing a numbered tip inside a <p> is a STRUCTURE fault, and saying
            # "this paragraph is not in the source article" about words that are in it,
            # character for character, is fault #6 — a wrong cause whose fix makes it
            # worse, because the writer's next move is to edit the article's own prose.
            misplaced = next((i for i in range(len(art))
                              if split_number(art[i])[1] == bp), None)
            if misplaced is not None:
                num = split_number(art[misplaced])[0]
                raise Halt(
                    f"E-BOOK FIDELITY: the right words in the wrong element.\n"
                    f"      {bp[:120]}{'…' if len(bp) > 120 else ''}\n"
                    + (f"    The article prints this as item {num} of a numbered list, so "
                       f"the body must reproduce it as an <li> inside the <ol>. It is a "
                       f"bare <p> here.\n"
                       if kind == "p" else
                       f"    The article prints this as an ordinary paragraph, not as a "
                       f"numbered item, so the body must reproduce it as a bare <p>. It "
                       f"is an <li> here.\n")
                    + f"    The words are correct — do not change them.")
            near = closest(bp, [split_number(p)[1] for p in art[ai:]])
            detail = (f"\n    Nearest article paragraph:\n      "
                      f"{first_difference(bp, split_number(art[ai + near])[1])}"
                      if near >= 0 else
                      "\n    No article paragraph is even close — is this original prose? The "
                      "e-book body is the article, near-verbatim; the only original prose in "
                      "the whole episode is in the SPOKEN script.")
            raise Halt(
                f"E-BOOK FIDELITY: this body paragraph is not in the source article:\n"
                f"      {bp[:150]}{'…' if len(bp) > 150 else ''}{detail}\n"
                f"    Per PP-STANDARDS §0a we reproduce, we do not improve — if PP made a "
                f"mistake in 1995, it stands. If the change is a deliberate print tidy, it "
                f"has to be a DECLARED departure in episode.json -> ebook.departures, and "
                f"the vocabulary is: {', '.join(sorted(DEPARTURES))}.")
        for j in range(ai, k):
            if j not in accounted:
                raise Halt(
                    f"E-BOOK FIDELITY: the body skips an article paragraph that is not "
                    f"declared in ebook.omit_paragraphs:\n      {art[j][:150]}"
                    f"{'…' if len(art[j]) > 150 else ''}\n"
                    f"    §0a's mirror: never add what the article does not say, and never "
                    f"REMOVE what it does. Reproduce it, or declare the omission by quoting "
                    f"it." + _why_not(art[j], headings or [], near_misses))
        ai = k + 1
        matched += 1
        as_items += 1 if kind == "li" else 0
    for j in range(ai, len(art)):
        if j not in accounted:
            raise Halt(
                f"E-BOOK FIDELITY: the body stops before the end of the article. This "
                f"paragraph is neither reproduced nor declared as an omission:\n"
                f"      {art[j][:150]}{'…' if len(art[j]) > 150 else ''}"
                + _why_not(art[j], headings or [], near_misses))

    # quoted material need not be a whole paragraph, but must be IN the article
    for q in quoted:
        if q not in art_joined:
            raise Halt(f"E-BOOK FIDELITY: this pull-quote / blockquote is not in the source "
                       f"article verbatim:\n      {q[:150]}\n    A quote that is not a quote "
                       f"is an invention with quotation marks round it.")

    lines = [f"fidelity: {matched}/{len(article)} article paragraphs reproduced verbatim"
             + (f" ({as_items} of them as numbered list items)" if as_items else "")]
    # SAY WHAT WAS RECOGNISED, not merely that nothing halted. A build that reports only
    # a count cannot be audited, and this is the line that shows a heading was compared
    # WORD FOR WORD rather than waved through by a declaration.
    if elsewhere:
        lines.append(f"          {len(elsewhere)} reproduced outside a <p>, and verified:")
        for i in sorted(elsewhere):
            lines.append(f"            {art[i][:52]!r} — {elsewhere[i]}")
    if omitted:
        lines.append(f"          {len(omitted)} declared omission(s): "
                     + "; ".join(article[i][:60] for i in sorted(omitted)))
    if quoted:
        lines.append(f"          {len(quoted)} quote(s) traced into the article")
    for name, _fn, desc in fns:
        lines.append(f"          departure {name!r}: {desc}")
    if not fns:
        lines.append("          no declared departures — the body is the article, exactly")
    return "\n".join(lines)


def check_figures(figures, ep):
    """The book's figures and episode.json's figures[] must agree, both ways."""
    want = [f["n"] for f in ep.get("figures", [])]
    if sorted(set(figures)) != sorted(set(want)):
        missing = sorted(set(want) - set(figures))
        extra = sorted(set(figures) - set(want))
        bits = []
        if missing:
            bits.append(f"episode.json maps figure(s) {missing} to cards, but the body never "
                        f"shows them")
        if extra:
            bits.append(f"the body shows figure(s) {extra}, which episode.json -> figures[] "
                        f"does not map to any card — so nothing renders them and the book "
                        f"would print a broken image")
        raise Halt("E-BOOK FIGURES: " + "; ".join(bits) + ".")
    if len(figures) != len(set(figures)):
        dupes = sorted({n for n in figures if figures.count(n) > 1})
        raise Halt(f"E-BOOK FIGURES: figure(s) {dupes} appear more than once in the body. "
                   f"Each figure is one card, shown once.")
    return f"figures: {len(figures)} in the body, matching episode.json -> figures[]"


# ------------------------------------------------------------------ main

def ep_stem(out_dir) -> str:
    """`PP-EPNN`, from the episode folder that contains ebook/.

    Taken from the folder rather than an episode.json field, and reduced to the
    bare `PP-EPNN` stem, because the folder is RENAMED at Stage-8 close-out
    (`PP-EP12` -> `PP-EP12-Hidden-Aces-Part-2`) while the deliverables keep the
    stem. The skill's naming standard is explicit that nothing may depend on the
    full folder name; the `PP-EP(\\d+)` part is the bit that survives.
    """
    folder = os.path.basename(os.path.dirname(os.path.abspath(out_dir)))
    m = re.match(r"(PP-EP\d+)", folder)
    if not m:
        raise Halt(f"the e-book directory is not inside a PP-EPNN episode folder "
                   f"(found {folder!r}), so there is no name to give the book.")
    return m.group(1)


def stage_standing(out_dir):
    added = []
    for name in STANDING_ASSETS:
        src, dst = os.path.join(ASSETS, name), os.path.join(out_dir, name)
        if os.path.exists(dst) or not os.path.isfile(src):
            continue
        shutil.copyfile(src, dst)
        added.append(name)
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_json")
    ap.add_argument("out_dir", help="the episode's ebook/ directory")
    ap.add_argument("--force", action="store_true",
                    help="rewrite a page that already carries the generated marker")
    ap.add_argument("--check-only", action="store_true",
                    help="run the fidelity gate and write nothing")
    a = ap.parse_args()

    ep_dir = os.path.dirname(os.path.abspath(a.episode_json))
    ep = json.load(open(a.episode_json, encoding="utf-8"))

    body_path = os.path.join(a.out_dir, BODY_FILE)
    if not os.path.exists(body_path):
        # A DATA halt, the same shape as every other one: it names the file.
        raise Halt(
            f"the e-book article body is missing: {os.path.join(a.out_dir, BODY_FILE)}\n"
            f"  The BODY is editorial — it is the article reproduced near-verbatim, and it "
            f"is written at SCRIPT time, when the article is in hand and the fidelity work "
            f"is being done anyway. The shell, the layout and the figures are all authored "
            f"from the standing template; only this file is written by hand.\n"
            f"  Write it as the ARTICLE BODY only (no page setup, no cover, no marketing or "
            f"warranty pages — those come from assets/ebook-template.html) using the class "
            f"vocabulary in PP-STANDARDS §E-book.\n"
            f"  An episode built before this existed (EP11, EP12) has no body.html: its "
            f"body lives inside its finished *-ebook-source.html and can be lifted out of "
            f"it.")
    body = open(body_path, encoding="utf-8").read().strip()

    blocks = article_blocks(source_article_path(ep, ep_dir))
    article = [re.sub(r"\s+", " ", b) for b in blocks]

    # THE CHART SLOTS ARE FILLED BEFORE ANYTHING LOOKS AT THE BODY, so every check
    # downstream sees the page as it will print. `body.html` on disk is untouched —
    # it keeps the slot, the way it keeps <img src="figure-3.png"> rather than a
    # picture. See the note by CHART_TABLE for why the model never types a cell.
    body, lifted = expand_chart_slots(body, blocks)

    # DECLARED SOURCE FIGURES: each must EXIST, and must be NAMED IN THE CAPTURE FILE.
    # The second check is the provenance one — it ties the image to the studio's own
    # record of the article, so a stray picture cannot be waved through by adding a
    # line to episode.json. A declaration is not a passport.
    src_figs = declared_source_figures(ep.get("ebook") or {})
    if src_figs:
        cap_path = source_article_path(ep, ep_dir)
        cap = open(cap_path, encoding="utf-8", errors="replace").read()
        for name, why in sorted(src_figs.items()):
            on_disk = os.path.join(a.out_dir, name)
            if not os.path.exists(on_disk):
                raise Halt(
                    f"episode.json declares source figure {name!r} but it is not in "
                    f"{a.out_dir}. A declared exception still has to point at a real "
                    f"file.")
            if name not in cap:
                raise Halt(
                    f"episode.json declares source figure {name!r}, but the capture "
                    f"file {os.path.basename(cap_path)} never mentions it. A source "
                    f"figure must come FROM THE ARTICLE and the capture is where that "
                    f"is recorded — otherwise 'source figure' is just a way to put any "
                    f"picture in the book. Name it in the capture, or do not declare it.")
            print(f"    source figure {name} — {os.path.getsize(on_disk):,} bytes, "
                  f"named in {os.path.basename(cap_path)}", file=sys.stderr)

    prose, quoted, figures, headings, items, ols, tables = parse_body(body, src_figs)
    # THE SHAPE BEFORE THE WORDS. EP25 passed every word-level check ever written while
    # printing a numbered list as one paragraph, so the shape is asked FIRST — and its
    # message is the useful one when both are wrong.
    report = [f"chart lift: {line}" for line in lifted]
    report += [r for r in (check_list_shape(article, items, ols),) if r]
    report += [check_fidelity(prose, quoted, ep, article, headings, figures, tables),
               check_figures(figures, ep)]
    report += [r for r in (check_figure_placement(ep, article, items, figures),) if r]

    if a.check_only:
        print("\n".join(report))
        print("FIDELITY GATE: PASS")
        return

    tpl = open(TEMPLATE, encoding="utf-8").read()
    n = tpl.count(SLOT_BODY)
    if n != 1:
        raise Halt(f"the standing e-book template does not contain the ARTICLE BODY slot "
                   f"exactly once (found {n}). The template has changed under this script — "
                   f"fix the pairing rather than loosening the match.")

    ebook = ep.get("ebook") or {}
    deps = ebook.get("departures") or []
    src_name = os.path.basename(source_article_path(ep, ep_dir))
    head = (f"{MARKER}\n"
            f"<!-- pp-fidelity: body checked against {src_name} — "
            f"{len(prose)}/{len(article)} paragraphs verbatim; "
            f"declared departures: {', '.join(deps) if deps else 'none'}; "
            f"declared omissions: {len(ebook.get('omit_paragraphs') or [])}. "
            + (f"{len(lifted)} chart(s) LIFTED from the capture into a slot the body "
               f"declared — no cell was re-typed. " if lifted else "")
            + f"The check is in author_ebook.py and it HARD-FAILS; it is not advisory. -->")
    page = tpl.replace(SLOT_BODY, head + "\n" + mark_headings(body))

    os.makedirs(a.out_dir, exist_ok=True)
    out = os.path.join(a.out_dir, f"{ep_stem(a.out_dir)}-ebook-source.html")
    added = stage_standing(a.out_dir)

    if os.path.exists(out):
        existing = open(out, encoding="utf-8").read()
        if GEN not in existing:
            print("\n".join(report))
            print(f"· {os.path.basename(out)} left alone: hand-authored (no generated marker)")
            return
        # THE --force TRAP, closed as author_cards.py closes it: the rendered page
        # is already in hand, so COMPARE it rather than skipping on existence.
        # The engine never passes --force, so a change to the body, the title or
        # a declared departure could never reach the e-book source — and on EP16
        # the workaround was deleting this file by hand before anything would
        # rebuild.
        if existing == page and not a.force:
            print("\n".join(report))
            print(f"· {os.path.basename(out)} left alone: unchanged — "
                  "episode.json still says the same thing")
            return
        if not a.force:
            print("~ e-book source re-authored — its definition changed")
    open(out, "w", encoding="utf-8", newline="\n").write(page)
    print("\n".join(report))
    if added:
        print(f"staged standing asset(s): {', '.join(added)}")
    print(f"authored {out}")


if __name__ == "__main__":
    try:
        main()
    except Halt as e:
        print(f"E-BOOK AUTHORING HALTED — {e}", file=sys.stderr)
        sys.exit(2)
