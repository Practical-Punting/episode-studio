#!/usr/bin/env python3
"""bespoke_gate.py — the checks a HAND-AUTHORED card page gets, at last.

    needs_a_human(cards, is_pipeline_page)   -> the bespoke pages a person must write
    page_faults(card, page_html, capture, frame_tpl) -> what is wrong with one of them

🔴 WHY. A card with `block: "bespoke"` is skipped ENTIRELY by `author_cards.py`:
no schema, no job check, no trace gate, no invented-text gate. It is the one kind
of card where a wrong number can reach the screen with nothing in its way — and
EP27 proved the cost twice in one build. C15's first render put "50.0" into the
descenders of "PERCENTAGES", and only a human eye caught it.

    HAND-AUTHORED MEANS UNPROTECTED, NOT LICENSED. It needs MORE discipline than
    a generated card, not less.

WHAT THIS ADDS, AND WHAT WAS ALREADY THERE
------------------------------------------
⚠️ `card_check.py` IS NOT ADDED HERE, BECAUSE IT WAS NEVER ACTUALLY MISSING, and
saying otherwise would leave the real hole open. It is handed the whole
`overlay/export` DIRECTORY, so a bespoke page sitting on disk when `cards_render`
runs has always been measured with everything else. What happened on EP27 is
narrower and worse: **the page did not exist when the step ran** (that is the
"C15 has no clip" halt), so it was hand-authored AND hand-rendered afterwards,
out of band — and the collision lived entirely inside that window. The fix for
that is not another checker, it is `needs_a_human()` below raising at PLAN time
so the pages exist before the checked moment ever arrives.

What genuinely had nothing behind it is the WORDS AND FIGURES on the page, and
that is what `page_faults` is: `author_cards.assert_no_invented_text` and the
trace gate, asked of the ARTEFACT instead of of episode.json — because for a
bespoke card episode.json is empty, and the page is the only thing that exists.

    Every FIGURE a viewer can read must appear in the source article.
    Every WORD must come from the article, the standing frame, or the card's
    own approved fields.

THE ONE ESCAPE, AND IT IS A DECLARATION
---------------------------------------
`bespoke_licence` on the card: a mapping of the exact string to the reason it is
allowed. It is the `ebook.departures` mechanism — a human writing down, in the
file, that they know. A licence is REVIEWABLE; a silent exception is not.
"""
from __future__ import annotations

import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import card_lift                                             # noqa: E402
from card_lift import Halt                                   # noqa: E402,F401


def _ac():
    """author_cards, on first use — see card_lift._ae for why this is deferred."""
    import author_cards
    return author_cards


# Pages some step of the BUILD produces, even though the card says "bespoke".
# TITLE, END and WARRANTY are all block:"bespoke" on every episode ever built —
# they are standing furniture, staged or authored by the pipeline itself. A guard
# that listed them as "needs a human" would fire on EVERY episode, which is the
# version somebody switches off (CLAUDE.md 4a).
def needs_a_human(cards, is_pipeline_page) -> list:
    """The bespoke cards NOBODY is going to author unless a person does.

    `is_pipeline_page(card)` is supplied by the caller rather than decided here,
    so the answer comes from the code that actually AUTHORS those pages — one
    source of truth, and a page that stops being standing tomorrow stops being
    excused here on the same day.
    """
    return [c for c in cards or []
            if (c.get("block") or "") == "bespoke" and not is_pipeline_page(c)]


# ── THE STUDIO'S STANDING CARD SENTENCES (Jodie, 16 Aug 2026) ────────────────
# Furniture, not claims about the article — the same standing as the frame's own
# "Rule N of M". The pointer from a card showing a table's SHAPE to the book that
# carries the whole thing is a house line: it appears on every ladder card there
# will ever be, and it is about the E-BOOK, so no article will ever contain it.
#
# 🔒 IT EXCUSES THE PHRASE, NOT THE WORDS IN IT. The whole sentence is lifted out
# of the page before the word check, so "full" is allowed HERE and nowhere else —
# a hand-authored page that says "the full field went round" still has to answer
# for it. Excusing the words themselves would open a hole the width of the
# vocabulary, which is how an allowlist quietly becomes a bypass.
#
# ⚠️ AND IT DOES NOT TOUCH THE FIGURE CHECK, on purpose. "34 prices in all" makes
# a claim about the article — how many rows the chart has — and on a bespoke page
# NOTHING asserts it. On a generated `ladder` card `card_lift` asserts that count
# against the table's own row count before a byte is written, which is exactly the
# difference between the two kinds of page. A bespoke page states the number on
# its own authority and must therefore declare it in `bespoke_licence`.
# 🔴 DERIVED FROM THE CANONICAL FOOTER, NEVER RETYPED HERE. `card_lift` owns the
# sentence; this takes the standing half of it — everything after the dash, which
# is the part that carries no figures and is identical on every ladder card. Copy
# it instead and the day the house line is reworded is the day a hand-authored
# page starts flagging a sentence the generated cards are still printing. That is
# the one-value-in-two-places fault this repo keeps paying for.
_STANDING_TAIL = card_lift.LADDER_FOOTER.split("—")[-1].strip().rstrip(".")
STANDING_LINES = (
    re.escape(_STANDING_TAIL.lower()),
)


def _visible(page_html: str) -> str:
    return _ac().visible_text(page_html)


def _without_standing_lines(vis: str) -> str:
    out = vis
    for pat in STANDING_LINES:
        out = re.sub(pat, " ", out)
    return out


def _allowed_text(card, capture_text, frame_tpl) -> str:
    """Everything a bespoke page is allowed to say, normalised and lower-cased."""
    ac = _ac()
    parts = [ac.norm(html.unescape(re.sub(r"<[^>]+>", " ", frame_tpl))).lower(),
             ac.norm(capture_text or "").lower()]
    for fld in ("eyebrow", "headline", "headline_display", "relates_to"):
        if card.get(fld):
            parts.append(ac.norm(str(card[fld])).lower())
    for _k, v in ac.walk_values(card.get("content") or {}):
        if isinstance(v, str):
            parts.append(ac.norm(html.unescape(re.sub(r"<[^>]+>", " ", v))).lower())
    for k in (card.get("bespoke_licence") or {}):
        parts.append(ac.norm(str(k)).lower())
    return " ".join(parts)


# A figure is a run of digits. `01.0` and `1.0` are the same reading of the same
# cell, so the comparison is on the digits themselves as they are written AND with
# leading zeros stripped — a card that writes the article's "09.1" as "9.1" is
# quoting it, not inventing it.
def _figures(s: str) -> list:
    return re.findall(r"\d+(?:\.\d+)?", s)


def _figure_ok(fig: str, allowed: str) -> bool:
    if fig in allowed:
        return True
    bare = fig.lstrip("0") or "0"
    return bare in allowed


def page_faults(card, page_html: str, capture_text: str | None,
                frame_tpl: str = "") -> list:
    """What is wrong with ONE hand-authored page. [] when it is sound."""
    cid = card.get("id", "<no id>")
    out = []
    if capture_text is None:
        return [f"{cid}: this page is hand-authored and the source-article capture "
                f"could not be read, so nothing on it could be checked against "
                f"anything. A bespoke page has no other gate — this is a refusal, "
                f"not a pass."]
    vis = _visible(page_html)
    allowed = _allowed_text(card, capture_text, frame_tpl)
    licensed = {str(k).lower() for k in (card.get("bespoke_licence") or {})}

    bad_figs = sorted({f for f in _figures(vis)
                       if not _figure_ok(f, allowed) and f.lower() not in licensed})
    if bad_figs:
        out.append(
            f"{cid}: the finished page shows figure(s) {bad_figs} that appear NOWHERE "
            f"in the source article, in this card's own approved fields, or in the "
            f"standing frame. A bespoke page is skipped by the trace gate, so this is "
            f"the only thing standing between a made-up number and the screen. If it "
            f"is genuinely right — a count of the article's own rows, say — declare it "
            f"in `bespoke_licence` with the reason, the way ebook.departures does.")

    # ⚠️ PUNCTUATION IS NOT A WORD, and comparing it as one cries wolf. Run over
    # EP27's real C15 the first version reported "guide." as absent from an article
    # that says "guide" — a full stop the card's own sentence ends on. The WORD is
    # what has to come from somewhere real; where the sentence happens to break is
    # not a claim about anything. (The figures half is untouched: a digit run has
    # no punctuation in it.)
    words = [w.strip(".,;:!?()[]\"'“”‘’…-–—")
             for w in _without_standing_lines(vis).split()]
    stray = sorted({w for w in words
                    if w and not w.replace(".", "").isdigit()
                    and w not in allowed and w not in licensed})
    if stray:
        out.append(
            f"{cid}: the finished page shows word(s) {stray[:8]} that are in neither "
            f"the source article, nor this card's approved fields, nor the standing "
            f"frame. On a generated card `assert_no_invented_text` makes this "
            f"impossible; a hand-authored page can simply type it.\n"
            f"        IF THE WORDS ARE RIGHT, RECORD THEM. A studio line that is not "
            f"in the article — \"the full chart is in the guide\" — is perfectly "
            f"legitimate and belongs in this card's `content` in episode.json, where "
            f"a human reviews it and this gate can see it. What must not happen is a "
            f"sentence existing ONLY on a page nobody re-derives. (EP27's own C15 is "
            f"this exact case: its footer was typed onto the page and recorded "
            f"nowhere.)")

    # E14's SECOND halt, which cost EP15 a whole extra round on the same card:
    # a hand-authored page that never defines window.ppDuration renders NO CLIP AT
    # ALL, because render_card.py waits on it before it waits for fonts. Every
    # generated card gets it free from the frame. A bespoke page gets nothing free.
    if "ppDuration" not in page_html and "ppInit" not in page_html:
        out.append(
            f"{cid}: this page never defines `window.ppDuration` (normally via "
            f"`ppInit`), so `render_cards_batch.py` will skip it and the card will "
            f"have no clip — the halt EP15 took on its second attempt at the same "
            f"page. Build a bespoke page from assets/cards/frame-fullscreen.html by "
            f"substitution and it comes with the animation contract already in it.")
    return out
