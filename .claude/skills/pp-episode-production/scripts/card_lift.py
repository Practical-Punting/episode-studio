#!/usr/bin/env python3
"""card_lift.py — a card's DATA is read out of the capture, never typed into it.

    apply_lifts(cards, capture_text)      # fills content{} in place, or HALTS

═══ THE LAW THIS IMPLEMENTS (Jodie, 16 Aug 2026, on the back of EP27) ══════════

    THE VIDEO TELLS THE TABLE'S STORY — one hero number or trend, not a data
    dump. The FULL table lives in the e-book. DATA IS LIFTED FROM THE CAPTURE
    AND ASSERTED, NEVER TYPED.

It is the ruling of 15 Aug — *"a number is a READING, not a value"* — moved from
the e-book, which has a cell-for-cell gate behind it, to the CARD, which has
less. `author_ebook.py` refuses a chart slot with rows typed into it; this
refuses a card with cells typed into it, in the same words and for the same
reason.

🔴 WHY IT EXISTS AT ALL. EP27's C15 was a 34-row conversion chart and C17 a
ten-item checklist. The largest list in the entire card vocabulary held six, so
both became `block:"bespoke"` — and a bespoke card is skipped by the schema, the
job check, the trace gate and the invented-text gate together. **The class of
article that most needs checking was the one class that got none.** Two halts,
one build, both of them a person's evening.

⚠️ WHAT THE WRITER STILL CHOOSES, AND WHY THAT IS RIGHT. It picks the ANCHORS —
which five to seven rows of thirty-four carry the shape. That is an editorial
judgement about what the story is, and automation eats chores, never decisions
(the Script Gate ruling). What it does NOT do is read a number off a page and
type it, which is the chore, and the only part that can be silently wrong.

⚠️ AND THE E-BOOK ROUTE IS UNCHANGED. A ladder shows 7 of 34 rows, so it does not
"render the grid" in the sense of PP-STANDARDS' chart rule: the book still takes
route (b), the empty `<table class="chart" data-article-table="N">` slot that
`author_ebook.py` fills cell for cell. A card carrying the SHAPE is not the same
artefact as a table carrying the DATA, and the standard wants both.

THE PROVENANCE MARKER
---------------------
A lifted value has better provenance than a traced one: it was READ from the
article by a program, not quoted by a writer. So `check_trace` accepts the lift
in place of a trace sentence for lifted keys ONLY — and it knows which those are
because `apply_lifts` records them in `card["_lifted"]`, in memory, on the card
it just filled.

🔒 `_lifted` IS NEVER WRITTEN TO DISK AND NEVER READ FROM ONE. A card arriving
from episode.json carrying that key is a card trying to turn the trace gate off
by hand, and it halts. (An `_`-key is never a convention — E26's rule.)
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


class Halt(Exception):
    """A build-stopping problem, phrased for a human.

    🔴 DEFINED HERE AND IMPORTED BY `author_cards`, WHICH IS BACKWARDS-LOOKING AND
    DELIBERATE. There is exactly ONE Halt class in the card pipeline —
    `author_ebook` already imported it from `author_cards`, and every caller writes
    `except ac.Halt`. Declaring a second one with the same name would produce an
    exception that reads identically in a traceback and is caught by nothing.
    This module sits at the BOTTOM of the import graph so that stays true.
    """


def _ae():
    """`author_ebook`, imported on FIRST USE rather than at module scope.

    ⚠️ NOT A STYLE CHOICE — it is the import cycle. author_ebook imports Halt from
    author_cards, author_cards imports this module for Halt, and a top-level
    `import author_ebook` here closes the ring: whichever of the three a caller
    imports first, one of them is half-built when the next one asks it for a name.
    Deferring the single edge that closes the loop is the whole fix, and it is the
    edge that is only needed when a card actually lifts something.
    """
    import author_ebook
    return author_ebook


# The two things a capture holds that a card can be built from. A closed set,
# exactly like the block names and the four jobs: a free-text `from` would let
# "from": "the article" through, and the whole point is that it names a READER.
SOURCES = ("table", "numbered")

# Every key a lift spec may carry. Closed, and checked — see the halt in apply_lifts.
KEYS = {"from", "into",                                  # both kinds
        "table", "key_column", "value_column", "anchors", "as", "footer_into"}

MARK = "_lifted"


def _capture_blocks(capture_text: str) -> list[str]:
    """The capture's blocks, RAW — the same split `author_ebook` uses.

    One implementation of "where does the article text begin", shared, so a
    card and the e-book can never disagree about what the article says.
    """
    return _ae().article_blocks_from_text(capture_text,
                                          where="the source-article capture")


def tables(capture_text: str) -> list[list[list[str]]]:
    """Every markdown table in the capture, as rows of cells (header first)."""
    ae = _ae()
    return [ae._md_table_rows(b) for b in _capture_blocks(capture_text)
            if ae.MD_TABLE.match(re.sub(r"\s+", " ", b))]


def numbered(capture_text: str) -> list[str]:
    """The capture's numbered items, in order, verbatim."""
    ae, out = _ae(), []
    for b in _capture_blocks(capture_text):
        n, w = ae.split_number(re.sub(r"\s+", " ", b))
        if n is not None:
            out.append(w)
    return out


def _digits(s: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", s or "")


def _one_table(capture_text: str, spec: dict, cid: str) -> list[list[str]]:
    ts = tables(capture_text)
    if not ts:
        raise Halt(f"card {cid}: this card lifts from a TABLE and the capture has none. "
                   f"Either the article does not print a table, or the capture did not "
                   f"keep it — and a card built from a table that is not there would "
                   f"have to invent one.")
    want = int(spec.get("table", 1))
    if not (1 <= want <= len(ts)):
        raise Halt(f"card {cid}: lift asks for table {want} and the capture has "
                   f"{len(ts)}. Tables are numbered from 1, in the order the article "
                   f"prints them.")
    return ts[want - 1]


def _column(header: list[str], name: str, cid: str, which: str) -> int:
    for i, h in enumerate(header):
        if h.strip().lower() == str(name).strip().lower():
            return i
    raise Halt(f"card {cid}: lift names {which} {name!r} and the table's columns are "
               f"{header}. The column is matched on the article's OWN heading, so a "
               f"renamed column stops the build instead of silently shifting which "
               f"figure the card is drawing.")


def _lift_table(card: dict, spec: dict, capture_text: str) -> tuple[list, list[str]]:
    """The anchor rows, as the block's list items — plus the values, for provenance."""
    cid = card.get("id", "<no id>")
    rows = _one_table(capture_text, spec, cid)
    header, data = rows[0], rows[1:]
    ki = _column(header, spec.get("key_column"), cid, "key_column")
    vi = _column(header, spec.get("value_column"), cid, "value_column")

    by_key: dict[str, str] = {}
    for r in data:
        if len(r) > max(ki, vi):
            by_key.setdefault(r[ki], r[vi])

    anchors = spec.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        raise Halt(f"card {cid}: a table lift needs `anchors` — the handful of rows that "
                   f"carry the shape. Which rows those are is an editorial judgement and "
                   f"stays with the writer; the CELLS are read from the article.")
    missing = [a for a in anchors if a not in by_key]
    if missing:
        near = ", ".join(list(by_key)[:8])
        raise Halt(
            f"card {cid}: anchor(s) {missing!r} are not in the table's {spec['key_column']!r} "
            f"column, so there is no cell to read for them. The column holds {len(by_key)} "
            f"value(s), beginning {near}. An anchor that is not in the table can only be "
            f"filled by inventing a figure, which is the one thing this refuses to do.")

    items, values = [], []
    lab = (spec.get("as") or {}).get("label", "label")
    val = (spec.get("as") or {}).get("value", "value")
    for a in anchors:
        items.append({lab: a, val: by_key[a]})
        values += [a, by_key[a]]
    return items, values


# ══ THE CANONICAL LADDER FOOTER (Jodie, 16 Aug 2026) ═════════════════════════
#
#     "<N> <unit> in all — the full chart is in the guide."
#
# 🔒 ONE SENTENCE, IN ONE PLACE, ON EVERY LADDER CARD THERE WILL EVER BE. It is
# the house line that sends a viewer from the card's SHAPE to the book's DATA, so
# it is furniture in exactly the sense the frame's "Rule N of M" is furniture —
# and furniture is written once, not re-composed per episode by whoever is writing.
#
# NOT ONE CHARACTER OF IT IS TYPED BY A WRITER:
#   · N        — the table's own data-row count, counted here.
#   · <unit>   — a CONTROLLED word chosen by the table's own key-column heading
#                (see UNITS). Not free text: an unknown heading halts and names
#                the known set, so widening it is a reviewed one-line change
#                rather than something a card can decide for itself.
#   · the rest — a literal in this file.
# So the whole footer is trusted by construction, and `assert_no_invented_text`
# has nothing to flag: every word of it arrives through content the same way a
# lifted cell does. (`bespoke_gate.STANDING_LINES` excuses the same sentence on a
# HAND-AUTHORED page, where there is no lift to vouch for it.)
LADDER_FOOTER = "{n} {unit} in all — the full chart is in the guide."

# The key column's heading -> the word for one of its rows, plural. A CLOSED SET,
# like the block names, the four jobs and `ebook.departures`: the point is that a
# card cannot invent the noun it counts. Add to it deliberately, in a commit.
UNITS = {
    "price": "prices", "prices": "prices",
    "odds": "prices",                       # an odds column IS a column of prices
    "row": "rows", "rows": "rows",
    "track": "tracks", "tracks": "tracks",
    "course": "courses", "courses": "courses",
    "horse": "horses", "horses": "horses",
    "runner": "runners", "runners": "runners",
    "race": "races", "races": "races",
    "start": "starts", "starts": "starts",
    "year": "years", "years": "years",
    "day": "days", "days": "days",
    "stake": "stakes", "stakes": "stakes",
    "bet": "bets", "bets": "bets",
}


def _unit_for(heading: str, cid: str) -> str:
    """The controlled noun for one row, taken from the table's own heading."""
    h = re.sub(r"[^a-z ]", " ", str(heading or "").lower()).strip()
    for word in [h] + h.split():
        if word in UNITS:
            return UNITS[word]
    raise Halt(
        f"card {cid}: the footer says how many rows the full chart has, and the word for "
        f"one of them is taken from the table's own key column — which is headed "
        f"{heading!r}, and that is not a word this knows. Known: "
        f"{', '.join(sorted(set(UNITS.values())))}.\n"
        f"    It is a CLOSED SET on purpose: the alternative is a writer typing the noun, "
        f"and the whole point of this footer is that no part of it is typed. Add the "
        f"heading to card_lift.UNITS in a commit, where somebody reviews it.")


def _canonical_footer(card: dict, spec: dict, n_rows: int, heading: str) -> list[str]:
    """Write the house footer into the card. Refuses a typed one.

    The number is the table's own row count, COUNTED — never believed. If the
    article's table gains a row the sentence changes with it, so a card cannot go
    on stating a figure the source has stopped agreeing with.
    """
    cid = card.get("id", "<no id>")
    key = spec.get("footer_into")
    if not key:
        return []
    content = card.setdefault("content", {})
    if content.get(key):
        raise Halt(
            f"card {cid}: {key!r} has a line TYPED into it, and this card's footer is the "
            f"house sentence — {LADDER_FOOTER.format(n='N', unit='<unit>')!r} — written "
            f"from the table itself. Leave it out of episode.json entirely. It is one or "
            f"the other, and it should be the standard: the count is the table's real row "
            f"count and the noun comes from its own column heading, so nothing in it can "
            f"be out of date or invented.\n"
            f"    It currently says: {str(content.get(key))[:120]!r}")
    content[key] = LADDER_FOOTER.format(n=n_rows, unit=_unit_for(heading, cid))
    return [key]


def apply_lifts(cards: list, capture_text: str | None) -> list:
    """Fill every card's lifted content from the capture, in place. HALTS on doubt.

    Returns the ids of the cards it filled, so a caller can say so in a run log.
    """
    todo = [c for c in cards if isinstance(c, dict) and c.get("lift")]
    for c in cards:
        if isinstance(c, dict) and MARK in c:
            raise Halt(
                f"card {c.get('id', '<no id>')}: this card carries {MARK!r}, which is the "
                f"IN-MEMORY marker recording that a value was lifted from the capture. It "
                f"is never written to a file. In episode.json it can only be an attempt to "
                f"tell the trace gate a figure has provenance it does not have.")
    if not todo:
        return []
    if not capture_text:
        raise Halt(
            f"card(s) {[c.get('id') for c in todo]!r} read their data out of the source "
            f"article, and the capture could not be read. Nothing is lifted and nothing is "
            f"guessed: a card whose figures come from an article that is not there cannot "
            f"be built at all. (The capture is named in episode.json -> source.)")

    done = []
    for c in todo:
        cid = c.get("id", "<no id>")
        spec = c.get("lift")
        if not isinstance(spec, dict):
            raise Halt(f"card {cid}: `lift` must be an object describing where the data is "
                       f"read from, e.g. "
                       f'{{"from": "table", "table": 1, "key_column": …}}')
        # 🔴 AN UNKNOWN KEY IN A LIFT SPEC HALTS. (16 Aug 2026, found by running the
        # real EP27 file through a renamed field.) `count_in` was replaced by
        # `footer_into` when the footer became the house sentence — and a card still
        # carrying the old key sailed straight through, silently unasserted, because
        # nothing reads a key that no longer exists. That is EP18's fault exactly:
        # *a field the machine cannot read turns a check OFF*, and the report comes
        # back clean having checked nothing. A closed vocabulary is the only version
        # of this that cannot happen.
        unknown = sorted(set(spec) - KEYS)
        if unknown:
            raise Halt(
                f"card {cid}: lift has key(s) {unknown} that this does not read. Known: "
                f"{', '.join(sorted(KEYS))}.\n"
                f"    A key nobody reads is worse than a missing one: the card looks "
                f"configured and the check it was meant to switch on never runs. If this "
                f"is `count_in`, it became `footer_into` when the footer became the house "
                f"sentence — delete the typed footer and the line is written for you.")
        src = spec.get("from")
        if src not in SOURCES:
            raise Halt(f"card {cid}: lift.from = {src!r} is not one of {list(SOURCES)}. "
                       f"This is a closed vocabulary: it names the READER that goes and "
                       f"gets the data, and there is no reader for anything else.")
        into = spec.get("into")
        if not into:
            raise Halt(f"card {cid}: lift needs `into` — the name of the list on this "
                       f"card that the lifted data fills.")
        content = c.setdefault("content", {})
        if not isinstance(content, dict):
            raise Halt(f"card {cid}: content must be an object.")
        # 🔴 THE E-BOOK'S OWN REFUSAL, IN THE SAME WORDS. A slot with rows typed into
        # it is one or the other, and it should be the slot.
        if content.get(into):
            raise Halt(
                f"card {cid}: {into!r} has values TYPED into it as well as a `lift` that "
                f"reads them from the article. It is one or the other, and it should be "
                f"the lift: write the slot empty and the article's own cells are read into "
                f"it. A number in this studio is a READING, not a value — nothing re-types "
                f"data the source already holds.")

        if src == "table":
            items, values = _lift_table(c, spec, capture_text)
            rows = _one_table(capture_text, spec, cid)
            counted = _canonical_footer(c, spec, len(rows) - 1,
                                        spec.get("key_column"))
            values += [content[k] for k in counted]      # the footer is lifted too
        else:
            items = numbered(capture_text)
            if not items:
                raise Halt(f"card {cid}: this card lifts the article's NUMBERED items and "
                           f"the capture has none.")
            values, counted = list(items), []
        content[into] = items
        c[MARK] = {"lists": [into], "keys": list(counted), "values": values}
        done.append(cid)
    return done


def lifted_lists(card: dict) -> set:
    return set(((card.get(MARK) or {}).get("lists")) or [])


def lifted_keys(card: dict) -> set:
    return set(((card.get(MARK) or {}).get("keys")) or [])
