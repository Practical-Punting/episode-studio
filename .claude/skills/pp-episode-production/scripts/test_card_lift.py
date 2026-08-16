#!/usr/bin/env python3
"""test_card_lift.py — a big TABLE and a long LIST stop being bespoke.

    python test_card_lift.py

EP27 halted twice on this class in one build. C15 is a 34-row odds->percentage
chart and C17 is a ten-item checklist; the largest list in the whole card
vocabulary held six, so both went `block:"bespoke"` — hand-authored, and
therefore past the trace gate, the invented-text gate and the schema, with
nothing behind them at all.

    THE LAW THIS PINS (Jodie, 16 Aug 2026):
    the video tells the table's STORY — one hero number or trend, not a data
    dump; the FULL table lives in the e-book. Data is LIFTED from the capture
    and asserted, never typed.

So the `ladder` block shows the SHAPE: five to seven anchor rows drawn as bars
whose height is the percentage, under a footer that states how many prices there
are in all — and that count is asserted against the table's own row count, never
believed. The writer types no cell. It selects anchors; the code does the reading.

THE FIXTURE IS THE REAL CHART, AND IT IS CARRIED RATHER THAN COMPUTED.
`testdata/capture-odds-table-and-ten-questions.md` holds the 34-row conversion
chart verbatim (verified cell for cell against EP27's capture, 16 Aug 2026) with
synthetic prose around it. It is not derivable: `12-1` reads `07.4` where the
arithmetic says `7.7`. A lift proved against tidied data proves nothing about the
day it meets untidy data — which is every day.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
CAPTURE = os.path.join(HERE, "testdata", "capture-odds-table-and-ten-questions.md")
sys.path.insert(0, HERE)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                        # noqa: BLE001
        pass

import author_cards as ac                                    # noqa: E402
import author_ebook as ae                                    # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"\n         <- {why}" if not cond and why else ""))


def halts(fn):
    """(did it halt, what it said) — the message is evidence, so it is returned."""
    try:
        fn()
        return False, ""
    except ac.Halt as e:
        return True, str(e)


CAP_TEXT = open(CAPTURE, encoding="utf-8").read()
ART_NORM = ac.norm(CAP_TEXT)

# The capture's OWN cells, read independently of the code under test. Every
# expectation below is compared against THIS, never against a typed literal:
# a test that types the answer is testing the typist.
_blocks = ae.article_blocks(CAPTURE)
_table = [b for b in _blocks if ae.MD_TABLE.match(re.sub(r"\s+", " ", b))][0]
_rows = ae._md_table_rows(_table)
HEADER, DATA = _rows[0], _rows[1:]
PCT = {r[1]: r[2] for r in DATA}                 # price -> odds-against percentage
ANCHORS = ["Evens", "2-1", "4-1", "6-1", "10-1", "20-1", "100-1"]
QUESTIONS = [w for n, w in
             (ae.split_number(re.sub(r"\s+", " ", b)) for b in _blocks) if n is not None]


def ladder_card(**over):
    c = {
        "id": "C15", "block": "ladder", "job": "relate", "beat": 23,
        "page": "c15-the-bookies-percentages.html",
        "eyebrow": "Fifteen · The Chart",
        "headline": "The Bookies' Percentages",
        "headline_display": "The Bookies'<br>Percentages",
        "lift": {"from": "table", "table": 1,
                 "key_column": "PRICE", "value_column": "ODDS AGAINST",
                 "anchors": list(ANCHORS), "into": "rows", "count_in": "footer"},
        "content": {"footer": f"{len(DATA)} prices in all — the full chart is in the guide."},
        "trace": {},
    }
    c.update(over)
    return c


def list_card(n=10, **over):
    c = {
        "id": "C17", "block": "checklist", "job": "relate",
        "relates_to": "the questions to ask before a bet",
        "page": "c17-the-ten-questions.html",
        "eyebrow": "Seventeen · The Questions",
        "headline": "The Ten Questions",
        "lift": {"from": "numbered", "into": "items"},
        "content": {}, "trace": {},
    }
    c.update(over)
    return c


def lift(card, capture=CAP_TEXT):
    """apply_lifts on ONE card, returning it — the call the pipeline makes."""
    ac.apply_lifts([card], capture)
    return card


# ══ 1. THE TABLE BECOMES A LADDER, WITHOUT block:"bespoke" ═══════════════════
print("\n-- the conversion ladder is LIFTED from the capture --")
card = lift(ladder_card())
rows = (card.get("content") or {}).get("rows") or []
check("the anchors become rows without anyone typing one",
      len(rows) == len(ANCHORS), f"{len(rows)} row(s): {rows!r}")
check("🔴 EVERY CELL EQUALS THE CAPTURE'S OWN CELL",
      [(r.get("label"), r.get("value")) for r in rows]
      == [(a, PCT[a]) for a in ANCHORS],
      f"lifted {[(r.get('label'), r.get('value')) for r in rows]!r} against the "
      f"capture's {[(a, PCT[a]) for a in ANCHORS]!r}")
check("  and the order is the anchor order, so the shape reads left to right",
      [r.get("label") for r in rows] == ANCHORS)
check("  including the ones that are NOT arithmetic (the chart's own oddities)",
      PCT["10-1"] == "09.1" and rows[4]["value"] == "09.1",
      f"10-1 lifted as {rows[4]['value']!r}; the capture says {PCT['10-1']!r}")

print("\n-- the block is real, and the card passes every authoring gate --")
blk = None
ok, why = halts(lambda: globals().__setitem__("blk", ac.load_block("ladder")))
check("there is a `ladder` block in the vocabulary", not ok, why)
if blk:
    ok, why = halts(lambda: ac.validate(card, blk))
    check("  it validates against the block's schema", not ok, why)
    check("  it declares a job the block can actually do", ac.check_job(card) == [], ac.check_job(card))
    check("  THE TRACE GATE IS SATISFIED — no card is bespoke here",
          ac.check_trace(card, ART_NORM) == [], ac.check_trace(card, ART_NORM))
    page = ""
    ok, why = halts(lambda: globals().__setitem__(
        "page", ac.render_card(card, blk, ac.load_frame("fullscreen"))))
    check("  it renders", not ok, why)
    if page:
        ok, why = halts(lambda: ac.assert_no_invented_text(
            page, card, ac.load_frame("fullscreen"), blk))
        check("  THE INVENTED-TEXT GATE IS SATISFIED", not ok, why)
        ok, why = halts(lambda: ac.assert_measured_items_show_a_figure(card, blk))
        check("  and every measured row shows its figure on screen", not ok, why)
        vis = ac.visible_text(page)
        check("  every lifted percentage is VISIBLE on the finished page",
              all(PCT[a].lower() in vis for a in ANCHORS),
              f"missing from the page: {[a for a in ANCHORS if PCT[a].lower() not in vis]}")
        check("  and the footer's count is on it",
              f"{len(DATA)} prices in all" in vis, vis[:160])

# ══ 2. THE THINGS THAT MUST HALT ═════════════════════════════════════════════
print("\n-- a typed cell is REFUSED, exactly as the e-book's chart slot refuses one --")
typed = ladder_card()
typed["content"]["rows"] = [{"label": "Evens", "value": "50.0"}]
ok, why = halts(lambda: lift(typed))
check("🔴 rows typed into a lifted slot HALT", ok, "a typed cell was accepted")
check("  and the halt says the data is lifted, not typed",
      "lift" in why.lower() or "typed" in why.lower(), why)

print("\n-- an anchor the table does not have --")
ghost = ladder_card()
ghost["lift"]["anchors"] = ["Evens", "3-5", "4-1"]
ok, why = halts(lambda: lift(ghost))
check("🔴 an anchor missing from the table HALTS", ok, "a ghost anchor was accepted")
check("  and it NAMES the one that is missing", "3-5" in why, why)

print("\n-- the footer's count is asserted against the table, never believed --")
wrong = ladder_card()
wrong["content"]["footer"] = "30 prices in all — the full chart is in the guide."
ok, why = halts(lambda: lift(wrong))
check("🔴 a footer claiming the wrong number of prices HALTS", ok,
      "the card would have told the viewer there are 30 prices")
check("  and it states both numbers", "30" in why and str(len(DATA)) in why, why)

print("\n-- the capture is the switch: no capture, no lift, and it says so --")
ok, why = halts(lambda: ac.apply_lifts([ladder_card()], None))
check("🔴 a lift with no capture to read HALTS rather than passing empty", ok, why)

print("\n-- and the trace gate is NOT weakened for anything else on the card --")
sneak = lift(ladder_card())
sneak["content"]["footer"] = sneak["content"]["footer"]      # lifted-count key, fine
sneak["eyebrow"] = "Fifteen · 99 Chances"                    # a TYPED figure
probs = ac.check_trace(sneak, ART_NORM)
check("🔴 a typed figure elsewhere on a lifted card still needs a trace",
      any("eyebrow" in p for p in probs),
      f"the trace gate said {probs!r} — lifting one key must not license the rest")

# ══ 3. THE OTHER LIFT: a numbered list read straight out of the article ══════
# The CARD that holds ten of them is the next commit's job (test_long_list_card.py);
# what is proved here is the READING — that the items arrive verbatim and nobody
# types one.
print("\n-- the numbered items, lifted verbatim --")
lc = lift(list_card())
items = (lc.get("content") or {}).get("items") or []
check("all ten are lifted", len(items) == 10, f"{len(items)}")
check("🔴 VERBATIM — every item is the capture's own words",
      items == QUESTIONS, f"{items!r}")
typed_items = list_card()
typed_items["content"]["items"] = ["SOMETHING I MADE UP"]
ok, why = halts(lambda: lift(typed_items))
check("  and a typed item is refused like a typed cell", ok, "a typed item was accepted")

# ══ 4. THE ARTEFACT — the page a viewer would actually see ═══════════════════
# CLAUDE.md fault #1: a structure check is a proxy. This page is measured by the
# same card_check that gates the build, from a file on disk.
print("\n-- and card_check MEASURES the finished ladder (the artefact, not a proxy) --")
tmp = tempfile.mkdtemp()
shutil.copyfile(os.path.join(ASSETS, "pp-anim.js"), os.path.join(tmp, "pp-anim.js"))
os.makedirs(os.path.join(tmp, "assets"), exist_ok=True)
shutil.copyfile(os.path.join(ASSETS, "assets/logo.png"), os.path.join(tmp, "assets/logo.png"))
wrote = []
for c, b in ((card, blk),):
    if not b:
        continue
    p = os.path.join(tmp, c["page"])
    open(p, "w", encoding="utf-8", newline="\n").write(
        ac.render_card(c, b, ac.load_frame("fullscreen")))
    wrote.append(p)
if wrote:
    r = subprocess.run([sys.executable, os.path.join(HERE, "card_check.py"), tmp],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=400)
    out = (r.stdout or "") + (r.stderr or "")
    check("🔴 THE LADDER PAGE IS CLEAN under card_check", r.returncode == 0,
          out[-900:])
    print("    " + "\n    ".join(l for l in out.splitlines() if l.strip())[:1200])

print(f"\ncard lift: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
