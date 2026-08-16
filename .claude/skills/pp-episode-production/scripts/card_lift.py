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


def _assert_count(card: dict, spec: dict, n_rows: int) -> list[str]:
    """`count_in` names the key that states HOW MANY there are in all.

    The number is the table's own row count, asserted — never believed. EP27's
    footer reads "34 prices in all"; if the article's table gains a row, the card
    stops the build instead of stating a number that is no longer true.
    """
    cid = card.get("id", "<no id>")
    key = spec.get("count_in")
    if not key:
        return []
    content = card.get("content") or {}
    if key not in content:
        raise Halt(f"card {cid}: lift.count_in names {key!r} and content has no such key.")
    text = content.get(key)
    if not isinstance(text, str) or not text.strip():
        raise Halt(f"card {cid}: lift.count_in names {key!r}, which must be a line of text "
                   f"stating how many rows the full table has.")
    found = _digits(text)
    if len(found) != 1:
        raise Halt(
            f"card {cid}: {key} = {text!r} carries {len(found)} figure(s) and must carry "
            f"exactly one — the number of rows in the full table. It is the only figure on "
            f"this card that is not lifted from a cell, so it is the only one that could be "
            f"wrong without anything noticing.")
    if found[0] != str(n_rows):
        raise Halt(
            f"card {cid}: {key} says {found[0]!r} and the article's table has {n_rows} data "
            f"row(s). The card would tell a viewer there are {found[0]} when there are "
            f"{n_rows}. Write {n_rows}; the count is asserted against the table itself, so "
            f"it cannot drift when the article does.")
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
            n_rows = len(_one_table(capture_text, spec, cid)) - 1
            counted = _assert_count(c, spec, n_rows)
        else:
            items = numbered(capture_text)
            if not items:
                raise Halt(f"card {cid}: this card lifts the article's NUMBERED items and "
                           f"the capture has none.")
            values, counted = list(items), _assert_count(c, spec, len(items))
        content[into] = items
        c[MARK] = {"lists": [into], "keys": list(counted), "values": values}
        done.append(cid)
    return done


def lifted_lists(card: dict) -> set:
    return set(((card.get(MARK) or {}).get("lists")) or [])


def lifted_keys(card: dict) -> set:
    return set(((card.get(MARK) or {}).get("keys")) or [])
