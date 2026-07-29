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
    # check_job runs in main() alongside check_trace; mirror BOTH here or the suite
    # reports green on a gate it never exercises.
    probs = ac.check_job(card) + ac.check_trace(card, ARTICLE)
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

print("\nNEGATIVE TESTS — every guard must fire\n" + "=" * 74)
for n, msg in PASS:
    print(f"  ✓ {n}\n      {msg[:110]}")
for n, msg in FAIL:
    print(f"  ✗ {n}\n      {msg[:160]}")
print("=" * 74)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
