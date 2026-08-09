#!/usr/bin/env python3
"""Negative tests for the card guards. Every one must HALT, in plain English.

    python test_author_cards.py

A guard that has never been seen to fire is a guard nobody has tested. These
build a minimal valid card, break one thing, and assert the halt message names
the card and the problem.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import author_cards as ac                                    # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                        # noqa: BLE001
        pass

ARTICLE = ac.norm(
    "Most horses resuming from a spell - say 60 days or more - will lose at their "
    "first run back. That's an iron-clad fact. He was sent out at 12/1. "
    "when he WON the prestigious Queensland Guineas, beating Juggler, Brave Warrior, "
    "Ivory's Irish and Danasinga!")

PASS, FAIL = [], []


def case(name, fn, expect):
    try:
        fn()
    except ac.Halt as e:
        if expect.lower() in str(e).lower():
            PASS.append((name, str(e)))
        else:
            FAIL.append((name, f"halted, but not about {expect!r}: {e}"))
        return
    except Exception as e:                                    # noqa: BLE001
        FAIL.append((name, f"raised {type(e).__name__} instead of a clean Halt: {e}"))
        return
    FAIL.append((name, "DID NOT HALT — the guard did not fire"))


def stat_card(**over):
    c = {"id": "C1", "block": "stat", "layout": "fullscreen", "job": "anchor",
         "eyebrow": "Start Here", "headline_display": "Most of Them Lose",
         "content": {"figure": "60 Days+", "figure_sub": "Resuming from a spell",
                     "payoff": "Most will lose at their first run back.",
                     "note": None},
         "trace": {"figure": "Most horses resuming from a spell - say 60 days or more - "
                             "will lose at their first run back."}}
    c.update(over)
    return c


def run(card, block=None):
    blk = ac.load_block(block or card["block"])
    ac.validate(card, blk)
    # check_job runs in main() alongside check_trace; mirror ALL of them here or the
    # suite reports green on a gate it never exercises.
    probs = (ac.check_job(card) + ac.check_trace(card, ARTICLE)
             + ac.check_converted_odds(card))
    if probs:
        raise ac.Halt(probs[0])
    ac.render_card(card, blk, ac.load_frame(card.get("layout", "fullscreen")))


# ---- the control: the valid card must NOT halt ---------------------------
try:
    run(stat_card())
    PASS.append(("control: a valid card renders", "no halt, as expected"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("control: a valid card renders", f"unexpected halt: {e}"))

# ---- 1. unknown block ----------------------------------------------------
case("unknown block halts",
     lambda: run({"id": "C9", "block": "notablock", "content": {}}), "unknown block")

# ---- 1b. pp-visual-standard R2: no job, no build -------------------------
def _nojob():
    c = stat_card()
    del c["job"]
    return run(c)


case("a card with NO job halts (visual standard R2)", _nojob, "MISSING 'job'")
case("an invented job halts — the vocabulary is closed",
     lambda: run(stat_card(job="explain")), "not one of")


def _job_block_clash():
    probs = ac.check_job({"id": "C2", "block": "statement", "job": "relate"})
    if probs:
        raise ac.Halt(probs[0])


case("a statement claiming 'relate' halts (R3a — a job is a claim)",
     _job_block_clash, "declares job 'relate' but uses block")


def _list_without_connection():
    probs = ac.check_job({"id": "C4", "block": "checklist", "job": "relate"})
    if probs:
        raise ac.Halt(probs[0])


case("a list block claiming 'relate' with nothing to relate TO halts",
     _list_without_connection, "relates_to")

# the positive control for the qualifier: name the connection and it builds
if ac.check_job({"id": "C4", "block": "checklist", "job": "relate",
                 "relates_to": "the day's track bias"}):
    FAIL.append(("a list block that NAMES its connection is allowed",
                 "unexpected halt"))
else:
    PASS.append(("a list block that NAMES its connection is allowed", "no halt, as expected"))

# ---- 2. unknown content key ---------------------------------------------
case("unknown content key halts",
     lambda: run(stat_card(content=dict(stat_card()["content"], sparkle="yes"))),
     "unknown key")

# ---- 3. MISSING key halts (the EP12 _placeholder lesson) ----------------
def _missing():
    c = stat_card()
    del c["content"]["note"]          # optional, but absence means nobody decided
    run(c)


case("a MISSING key halts even when optional", _missing, "missing")

# ---- 4. explicit null renders, does not halt ----------------------------
try:
    run(stat_card())                  # note is None above
    PASS.append(("explicit null renders an empty slot", "no halt, as expected"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("explicit null renders an empty slot", f"unexpected halt: {e}"))

# ---- 5. a required key set to null halts --------------------------------
case("null in a REQUIRED key halts",
     lambda: run(stat_card(content=dict(stat_card()["content"], figure=None))),
     "requires a value")

# ---- 6. a figure with no trace halts ------------------------------------
case("figure without a trace halts",
     lambda: run(stat_card(trace={})), "no trace entry")

# ---- 7. a trace that is not in the article halts ------------------------
case("trace not found in the source halts",
     lambda: run(stat_card(trace={"figure": "Most horses resuming from a spell of 90 days "
                                            "will lose at their first run back."})),
     "not a literal substring")

# ---- 8. THE EP11 C7 CASE: real sentence, figure it does not contain -----
# The traced sentence is genuinely in the article. It simply does not state the
# placings that were inferred from listing order and put on screen as fact.
case("a real sentence that does not carry the figure halts",
     lambda: run(stat_card(
         content=dict(stat_card()["content"], figure="2nd Juggler"),
         trace={"figure": "when he WON the prestigious Queensland Guineas, beating "
                          "Juggler, Brave Warrior, Ivory's Irish and Danasinga!"})),
     "do NOT appear in its own"),

# ---- 9. a figure in the HEADLINE needs a trace too ----------------------
case("an untraced figure in the headline halts",
     lambda: run(stat_card(headline_display="90 Days Is Not 180 Days")), "headline")

# ---- 10. fit carries measurements, never text ---------------------------
case("text in a fit value halts",
     lambda: run(stat_card(fit={"headline_size": "very big"})), "not a bare number")

# ---- 11. an unknown fit key halts ---------------------------------------
case("unknown fit key halts",
     lambda: run(stat_card(fit={"wobble": "3px"})), "unknown fit key")

# ---- 12. a style-variant field is a closed set --------------------------
case("an invented style variant halts",
     lambda: run({"id": "C4", "block": "compare", "layout": "panel-push",
                  "eyebrow": "x", "headline_display": "y",
                  "content": {"note": None,
                              "cols": [{"tone": "maybe", "k": "a", "v": "b"},
                                       {"tone": "no", "k": "c", "v": "d"}]}}),
     "closed set")

# ---- 13. a bar length must be a number, not a caption -------------------
case("a non-numeric bar value halts",
     lambda: run({"id": "C3", "block": "bars", "layout": "fullscreen",
                  "eyebrow": "x", "headline_display": "y",
                  "content": {"ask": None, "chip": None,
                              "bars": [{"label": "90 Days", "value": "ninety",
                                        "note": "n", "tone": "hi"},
                                       {"label": "180 Days", "value": "180",
                                        "note": "n", "tone": ""}]},
                  "trace": {"bars": "Most horses resuming from a spell - say 60 days or "
                                    "more - will lose at their first run back."}}),
     "bare number")

# ---- 14. list length is bounded -----------------------------------------
case("too few list items halts",
     lambda: run({"id": "C6", "block": "checklist", "layout": "panel-push",
                  "eyebrow": "x", "headline_display": "y",
                  "content": {"items": ["only one"]}}), "takes between")

# ---- 15. a converted price never goes on a card -------------------------
# 🔒 EP19 C8, verbatim as it shipped on 9 Aug 2026 before Jodie caught it. The card read
# "$1.75 to $3.25" over the caption "in tote terms". Every dollar figure there is the
# ARTICLE'S OWN bracketed gloss on its fractional odds — which is why "never add a fact
# the article does not state" did not catch it, in the brief or in anyone's head. The
# script brief had the rule and the spoken words were clean; the card brief did not.
ODDS_ARTICLE = ac.norm(
    "Look at pre-post favourites with odds in the range 8/11 to 9/4 inclusive (that is, "
    "in tote terms, $1.75 to $3.25).The second-favourite must be at least 4/1 ($5)."
    "Start with a bank of $1,000 and never add to it.")


def odds_card(**over):
    c = {"id": "C8", "block": "price", "layout": "panel-push", "job": "anchor",
         "eyebrow": "Eight", "headline_display": "The Price Window",
         "content": {"price": "$1.75 to $3.25", "said": "the pre-post favourite, in tote terms",
                     "quote": "The second-favourite must be at least 4/1 ($5)."},
         "trace": {"price": "Look at pre-post favourites with odds in the range 8/11 to "
                            "9/4 inclusive (that is, in tote terms, $1.75 to $3.25).",
                   "quote": "The second-favourite must be at least 4/1 ($5)."}}
    c["content"].update(over.pop("content", {}))
    c.update(over)
    return c


def run_odds(card):
    probs = ac.check_converted_odds(card) + ac.check_trace(card, ODDS_ARTICLE)
    if probs:
        raise ac.Halt(probs[0])


case("a tote conversion on a card halts", lambda: run_odds(odds_card()),
     "tote conversion")

# …and the other half of it: the FIXED card must sail through, and so must a plain
# dollar figure the article states as money. A guard that fires on everything is a
# guard that will be turned off.
for name, card in (
    ("the article's own odds pass",
     odds_card(content={"price": "8/11 to 9/4", "said": "the pre-post favourite",
                        "quote": "The second-favourite must be at least 4/1."})),
    ("a plain dollar bank passes",
     {"id": "C2", "content": {"figure": "$1,000"},
      "trace": {"figure": "Start with a bank of $1,000 and never add to it."}}),
):
    try:
        run_odds(card)
        PASS.append((f"control: {name}", "no halt, as expected"))
    except Exception as e:                                        # noqa: BLE001
        FAIL.append((f"control: {name}", f"the guard fired on a good card: {e}"))

# ---- 16. the MATRIX block — n columns x m rows, both axes labelled ------------
# 🔴 EP15 C12 AND EP19 C12 WERE BOTH HAND-AUTHORED because no block drew a grid, and a
# hand-authored page gets nothing for free: it must remember pp-anim.js or render_card
# waits 60s on window.ppDuration and gives up silently, and autofit will not touch it.
MATRIX_ARTICLE = ac.norm(
    "Take each race in turn and award form points for the last three runs of each "
    "horse. | Last start | 2nd-last start | 3rd-last start | | Win 9 pts | Win 6 pts | "
    "Win 3 pts | | 2nd 6 pts | 2nd 4 pts | 2nd 2 pts | | 3rd 3 pts | 3rd 2 pts | "
    "3rd 1 pt |")


def matrix_card(**over):
    c = {"id": "C12", "block": "matrix", "layout": "fullscreen", "job": "relate",
         "eyebrow": "Twelve", "headline_display": "The Form Points",
         "content": {
             "columns": ["Last start", "2nd-last start", "3rd-last start"],
             "rows": [{"label": "Win", "cells": ["9 pts", "6 pts", "3 pts"]},
                      {"label": "2nd", "cells": ["6 pts", "4 pts", "2 pts"]},
                      {"label": "3rd", "cells": ["3 pts", "2 pts", "1 pt"]}],
             "foot": None},
         "trace": {"columns": "| Last start | 2nd-last start | 3rd-last start |",
                   "rows": "| Win 9 pts | Win 6 pts | Win 3 pts | | 2nd 6 pts | "
                           "2nd 4 pts | 2nd 2 pts | | 3rd 3 pts | 3rd 2 pts | 3rd 1 pt |"}}
    c["content"].update(over.pop("content", {}))
    c.update(over)
    return c


def run_matrix(card):
    blk = ac.load_block("matrix")
    ac.validate(card, blk)
    probs = ac.check_job(card) + ac.check_trace(card, MATRIX_ARTICLE)
    if probs:
        raise ac.Halt(probs[0])
    return ac.render_card(card, blk, ac.load_frame("fullscreen"))


try:
    page = run_matrix(matrix_card())
    cells = page.count('class="mcell"')
    leftovers = [x for x in ("{{", "@each", "@endeach") if x in page]
    if cells == 9 and not leftovers:
        PASS.append(("control: a 3x3 matrix renders through the vocabulary",
                     f"9 cells, both axes, no template leftovers"))
    else:
        FAIL.append(("control: a 3x3 matrix renders through the vocabulary",
                     f"{cells} cells, leftovers {leftovers}"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("control: a 3x3 matrix renders through the vocabulary", f"halted: {e}"))

# THE RULE THAT MAKES IT WORTH A BLOCK. A short row does not look broken on the card —
# it silently shifts every value one column left and states something the article never
# said. EP19 C12's own note: "a viewer could not tell which figure belongs to which run".
case("a row with fewer cells than there are columns halts",
     lambda: run_matrix(matrix_card(content={
         "rows": [{"label": "Win", "cells": ["9 pts", "6 pts", "3 pts"]},
                  {"label": "2nd", "cells": ["6 pts", "4 pts"]},
                  {"label": "3rd", "cells": ["3 pts", "2 pts", "1 pt"]}]})),
     "shifts every value one column")

# EVERY CELL IS A FIGURE AND MUST BE TRACEABLE. Before walk_values recursed into a
# nested list, all nine were yielded as one LIST — which check_trace skips, because it
# only looks at strings. The block would have shipped nine untraced numbers on a card
# whose whole purpose is nine numbers, with every gate saying yes.
try:
    seen = [k for k, v in ac.walk_values(matrix_card()["content"])
            if isinstance(v, str) and any(ch.isdigit() for ch in v)]
    grid = [k for k in seen if ".cells[" in k]
    (PASS if len(grid) == 9 else FAIL).append(
        ("every one of the nine grid values is visible to trace-or-halt",
         f"{len(grid)} cells walked: {grid[:3]}…" if len(grid) == 9 else
         f"only {len(grid)} of 9 cells are walked — the rest escape the trace gate"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("every one of the nine grid values is visible to trace-or-halt", str(e)))

case("a cell figure with no traced sentence halts",
     lambda: run_matrix(matrix_card(
         content={"rows": [{"label": "Win", "cells": ["9 pts", "6 pts", "3 pts"]},
                           {"label": "2nd", "cells": ["6 pts", "4 pts", "2 pts"]},
                           {"label": "3rd", "cells": ["3 pts", "2 pts", "99 pts"]}]})),
     "do NOT appear in its own traced sentence")

# THE NESTED-EACH ENGINE IS LOAD-BEARING, and this is the control that proves it.
# The old expansion was a single non-greedy regex: with a loop inside a loop, `(.*?)`
# stops at the INNER <!--@endeach-->, so the outer region ends inside itself. Run that
# old pattern over the real matrix template and it must produce a BROKEN page —
# otherwise the depth-counting parser is not what is making this work.
try:
    import re as _re
    blk = ac.load_block("matrix")
    old = _re.sub(r"<!--@each (\w+)-->(.*?)<!--@endeach-->", lambda m: "",
                  blk["markup"], flags=_re.S)
    (PASS if "@endeach" in old or "{{ITEM" in old else FAIL).append(
        ("control: the OLD one-level regex mangles a nested template",
         "it leaves a stray @endeach / unexpanded {{ITEM}} — which is why a grid "
         "could not be templated before"
         if ("@endeach" in old or "{{ITEM" in old) else
         "the old regex handled it cleanly, so the new parser proves nothing"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("control: the OLD one-level regex mangles a nested template", str(e)))

print("\nNEGATIVE TESTS — every guard must fire\n" + "=" * 74)
for n, msg in PASS:
    print(f"  ✓ {n}\n      {msg[:110]}")
for n, msg in FAIL:
    print(f"  ✗ {n}\n      {msg[:160]}")
print("=" * 74)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
