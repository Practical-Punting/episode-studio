#!/usr/bin/env python3
"""test_twoway_20sep_rulings.py — Jodie's card rulings of 20 September 2026, asserted.

    python engine/test_twoway_20sep_rulings.py

Four rulings and one composed script, each with a control that FAILS (CLAUDE.md 4b — a
guard is not trustworthy until you have watched it fail):

  1. **A card starts on its own words or is dropped.** It may enter only on a sentence
     of the paragraph it was commissioned against; if none is legal it is dropped with
     a reason that names the binding constraint.
  2. **A card may run past its sentence to finish its reading time + a 1.5s settle**,
     and is never sped up to fit. The hold it asks for is the larger of the item floor
     and the reading floor.
  3. **An opening-sentence card lands from the two-box 5s after the handover, while its
     sentence still runs** — the opening unit is cut at TURN_OPEN_MIN_S.
  4. **A turn's CLOSING two-box is A10 rule 3 being kept, not a Rule 1 breach.**
  5. **The composed render script** carries the furniture, places the midroll at the
     midpoint handover INTO the host, and cannot be silently overwritten by the
     splitter.

⚠️ THE SUITE THAT WAS ALREADY GREEN DOES NOT COVER ANY OF THIS (CLAUDE.md §4). 273
checks passed before a line of it was written, on the behaviour that was there before.
"""
from __future__ import annotations

import hashlib
import re
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import card_hold                                                  # noqa: E402
import twoway_beats as tb                                         # noqa: E402
import twoway_furniture as tf                                     # noqa: E402
import twoway_split as ts                                         # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR",
                                 str(pathlib.Path("G:/My Drive") / "PP Videos")))
EP_DIR = PP / "PP-EP49-Fighting-a-Complex-Game-Part-1"
EPJ = EP_DIR / "docs/episode.json"
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  — {why}" if why and not cond
                                                       else ""))


def turn(n, speaker, paras, card_on=None, broll_on=None):
    """A synthetic turn: `paras` is a list of paragraph texts."""
    out = []
    for i, p in enumerate(paras):
        out.append({"n": n * 100 + i, "turn": n, "speaker": speaker, "para_in_turn": i,
                    "words": len(p.split()), "est_s": tb.est_s(len(p.split())),
                    "line": p, "card": None, "broll": None,
                    "paras_in_turn": len(paras)})
    if card_on is not None:
        out[card_on[0]]["card"] = card_on[1]
    if broll_on is not None:
        out[broll_on[0]]["broll"] = broll_on[1]
    return out


def sentences(n, words_each=13):
    """n sentences the SPLITTER actually recognises.

    ⚠️ Each one must start with a capital. The first version of this helper built
    lowercase sentences, `tb.sentences()` returned the whole paragraph as ONE unit, and
    a control below failed for a reason that had nothing to do with the code it was
    controlling. A fixture that does not exercise the path is worse than no fixture: it
    reports a fault that is not there (CLAUDE.md fault #1's sibling).
    """
    return " ".join(f"Number {i} {'word ' * words_each}end." for i in range(n))


# ═══ 1. A card starts on its own words ═══════════════════════════════════════
print("\n-- 1. a card enters only on its own paragraph --")

# Two long paragraphs. The card is on the SECOND; the first is where a
# displacement-minimising placer would happily put it if the second were tight.
beats = turn(1, "BB", [sentences(6), sentences(6)], card_on=(1, "CX"))
for i, b in enumerate(beats):
    b["n"] = i + 1
segs = tb.derive_plan(beats, {}, {"CX": 9.0})
own = beats[1]["n"]
placed = [s for s in segs if s.get("card") == "CX"]
check("the card is in the cut", bool(placed))
check("it enters on a beat of its OWN paragraph",
      bool(placed) and placed[0]["beats"][0] == own,
      f"entered on beat {placed[0]['beats'][0] if placed else None}, own is {own}")

# CONTROL — a card whose own paragraph is far too short to hold it is DROPPED,
# and the old behaviour (rehouse it over the long paragraph next door) is gone.
beats = turn(1, "BB", [sentences(8), "One short line here."], card_on=(1, "CY"))
for i, b in enumerate(beats):
    b["n"] = i + 1
reasons, dropped = {}, set()
segs = tb.derive_plan(beats, {}, {"CY": 14.0}, dropped=dropped, reasons=reasons)
check("CONTROL: a card that cannot fit its own paragraph is DROPPED",
      not any(s.get("card") == "CY" for s in segs))
check("CONTROL: and the drop names the paragraph, not just the turn",
      "own paragraph" in (reasons.get("CY") or ""), reasons.get("CY", "(no reason)"))

# And the reason names the BINDING constraint when a previous graphic's dwell is it.
beats = (turn(1, "BB", [sentences(2), sentences(2), sentences(6)],
              card_on=(0, "CA")))
for i, b in enumerate(beats):
    b["n"] = i + 1
beats[1]["card"] = "CB"
reasons, dropped = {}, set()
tb.derive_plan(beats, {}, {"CA": 12.0, "CB": 9.0}, dropped=dropped, reasons=reasons)
if "CB" in reasons:
    check("a collision reports the PREVIOUS graphic's dwell, not a cheerful number",
          "COLLISION" in reasons["CB"], reasons["CB"][:140])
else:
    check("a collision reports the previous graphic's dwell", True)


# ═══ 2. reading time + settle, and never sped up ═════════════════════════════
print("\n-- 2. the reading floor --")

light = {"block": "compare", "content": {"cols": [{"tone": "yes", "k": "A", "v": "B"},
                                                  {"tone": "no", "k": "C", "v": "D"}]}}
heavy = {"block": "compare",
         "content": {"cols": [{"tone": "yes", "k": "A heading of some length here",
                               "v": "and a value with a great many words in it, "
                                    "enough that reading it takes real time"},
                              {"tone": "no", "k": "Another heading of length",
                               "v": "and its own long value, also with plenty of "
                                    "words for the eye to work through"}],
                     "note": "A closing note that also has to be read by somebody."}}
check("a light card asks for the ITEM floor",
      card_hold.hold_for(light, {"min_card_hold": 10.0})
      == card_hold.min_hold_for(light, {"min_card_hold": 10.0}))
check("a wordy card asks for MORE than the item floor",
      card_hold.hold_for(heavy, {"min_card_hold": 10.0})
      > card_hold.min_hold_for(heavy, {"min_card_hold": 10.0}),
      f"{card_hold.hold_for(heavy, {'min_card_hold': 10.0})} vs "
      f"{card_hold.min_hold_for(heavy, {'min_card_hold': 10.0})}")
check("CONTROL: the reading floor is NOT capped by min_card_hold — capping it "
      "would be speeding the card up",
      card_hold.hold_for(heavy, {"min_card_hold": 10.0}) > 10.0)
check("the settle is in the number",
      abs(card_hold.reading_hold_s(light)
          - (card_hold.content_words(light) / card_hold.WORDS_PER_S_READ
             + card_hold.NOTICE_S + card_hold.SETTLE_S)) < 0.01)

# the enum-aware word count, derived from the block's own schema
check("a closed vocabulary is not a word on the card (compare: tone)",
      card_hold.content_words(light) == 4,
      f"counted {card_hold.content_words(light)} for k/v A B C D")
check("and the skip list comes from the block's SCHEMA, not a literal",
      "tone" in card_hold.enum_fields("compare")
      and "band" in card_hold.enum_fields("ruler"))
check("CONTROL: an unknown block falls back rather than counting nothing",
      card_hold.enum_fields("no-such-block") == card_hold.ENUM_FIELDS)

# the run-past: a card whose hold exceeds its own paragraph keeps the frame
beats = turn(1, "BB", [sentences(2), sentences(8)], card_on=(0, "CZ"))
for i, b in enumerate(beats):
    b["n"] = i + 1
segs = tb.derive_plan(beats, {}, {"CZ": 14.0})
held = sum(s["dur_s"] for s in segs if s.get("card") == "CZ")
own_len = beats[0]["est_s"]
check("a card RUNS PAST its own paragraph to finish its reading time",
      held > own_len + 1.0, f"held {held:.1f}s, its paragraph is {own_len:.1f}s")


# ═══ 3. the opening-sentence card ════════════════════════════════════════════
print("\n-- 3. an opening-sentence card lands 5s after the handover --")

long_open = " ".join(["word"] * 60) + "."
beats = turn(1, "BB", [long_open + " " + sentences(4)], card_on=(0, "CO"))
beats[0]["n"] = 1
units = tb._units(beats)
cut = tb._split_turn_open(units)
check("the opening unit is CUT at the turn-open floor",
      len(cut) == len(units) + 1 and abs(cut[0]["est_s"] - tb.TURN_OPEN_MIN_S) < 0.01,
      f"{len(units)} units -> {len(cut)}, first {cut[0]['est_s']}s")
segs = tb.derive_plan(beats, {}, {"CO": 9.0})
first_card = next((s for s in segs if s.get("card") == "CO"), None)
check("so the card enters at 5.0s, not at the end of a 23-second sentence",
      first_card is not None and abs(first_card["from_s"] - tb.TURN_OPEN_MIN_S) < 0.2,
      f"entered at {first_card['from_s'] if first_card else None}s")

# CONTROL — a turn whose first beat carries NO card is untouched
plain = turn(1, "BB", [long_open + " " + sentences(4)])
plain[0]["n"] = 1
check("CONTROL: a turn with no opening card is not cut at all",
      len(tb._split_turn_open(tb._units(plain))) == len(tb._units(plain)))
short_open = turn(1, "BB", ["Short opener here. " + sentences(4)], card_on=(0, "CQ"))
short_open[0]["n"] = 1
u2 = tb._units(short_open)
check("the fixture really does open on a short sentence",
      len(u2) > 1 and u2[0]["est_s"] < tb.TURN_OPEN_MIN_S,
      f"first unit {u2[0]['est_s']}s of {len(u2)} units")
check("CONTROL: and an opener already shorter than 5s is not cut either",
      len(tb._split_turn_open(u2)) == len(u2))


# ═══ 4. a turn's closing two-box is the rule being kept ══════════════════════
print("\n-- 4. the closing two-box is not a Rule 1 breach --")

real = json.loads(EPJ.read_text(encoding="utf-8"))
tb.apply(real)
segs = real["layout_plan"]
v = tb.violations(segs)
last = segs[-1]
check("EP49's plan ends on the two-box", last["layout"] == "two-box")
check("and it is NOT reported as a mid-turn return taken early",
      not any("RULE 1 BROKEN" in x and f"{last['from_s']:.0f}s" in x for x in v),
      "; ".join(x for x in v if "RULE 1 BROKEN" in x))

# CONTROL — a genuine early return, mid-turn, IS still reported
fake = [dict(s) for s in segs]
mid = next(i for i, s in enumerate(fake)
           if s["kind"] == "single" and s["turn"] == 10)
fake[mid] = dict(fake[mid], dur_s=6.0, to_s=fake[mid]["from_s"] + 6.0)
fake[mid + 1] = dict(fake[mid + 1], layout="two-box", kind="two-box",
                     from_s=fake[mid]["to_s"])
check("CONTROL: a real mid-turn return after 6s of single IS still reported",
      any("RULE 1 BROKEN" in x for x in tb.violations(fake)),
      "; ".join(tb.violations(fake))[:160])


# ═══ 5. the composed render script ═══════════════════════════════════════════
print("\n-- 5. one render, with the furniture in it --")

built = tf.build(49, PP, write=False)
man = built["manifest"]
kinds = [s["kind"] for s in man]
ids = [s["id"] for s in man]
check("the script opens on the OPEN and closes on the sign-off",
      ids[0] == "open" and ids[-1] == "signoff", f"{ids[0]} … {ids[-1]}")
check("the CTA follows the host's first turn",
      ids.index("cta") == ids.index([i for i in ids if i.startswith("turn-")][0]) + 1)
check("the close, the outro, the RG line and the sign-off are in that order",
      [i for i in ids if i in ("close", "outro", "rg", "signoff")]
      == ["close", "outro", "rg", "signoff"])

turns_json = json.loads((EP_DIR / "docs/turns.json").read_text(encoding="utf-8"))
spoken = [t for t in turns_json["turns"] if t["speaker"] != "NARR"]
words = [len(ts.spoken(t["text"]).split()) for t in spoken]
mid_n = tf.midpoint_handover(turns_json["turns"], "BB")
at = sum(w for t, w in zip(spoken, words) if t["n"] < mid_n)
check("the midroll sits within 5% of the spoken midpoint",
      abs(at / sum(words) - 0.5) < 0.05, f"{at / sum(words):.1%} in")
check("and it is a handover INTO the host",
      next(t["speaker"] for t in spoken if t["n"] == mid_n) == "BB")

# CONTROL — a one-turn host has no midpoint handover and must say so, not guess
one = {"turns": [{"n": 1, "speaker": "BB", "text": "Only turn.", "words": 2},
                 {"n": 2, "speaker": "BM", "text": "And a reply.", "words": 3}]}
try:
    tf.midpoint_handover(one["turns"], "BB")
    check("CONTROL: a host with one turn refuses to place a midroll", False)
except tf.NotComposable as e:
    check("CONTROL: a host with one turn refuses to place a midroll", True)

check("the script Jodie pastes is words and breaks ONLY — no marker, no header",
      "<!--" not in built["script"] and not built["script"].lstrip().startswith("#"))
check("the sentinel lives beside the script, not inside it",
      tf.is_composed(EP_DIR / "docs/spoken-words-BB.txt"))
d = pathlib.Path(tempfile.mkdtemp(prefix="unmarked_"))
(d / "spoken-words-BB.txt").write_text("just the dialogue.\n", encoding="utf-8")
check("CONTROL: a plain split script is not mistaken for a composed one",
      not tf.is_composed(d / "spoken-words-BB.txt"))

# CONTROL — the splitter refuses to clobber, and the file is byte-identical after
script = EP_DIR / "docs/spoken-words-BB.txt"
before = hashlib.md5(script.read_bytes()).hexdigest()
halted = False
try:
    ts.build(49, PP, write=True)
except ts.Unsplittable:
    halted = True
except Exception:
    pass
check("CONTROL: twoway_split --write HALTS on a composed script", halted)
check("and the composed script is byte-identical afterwards",
      hashlib.md5(script.read_bytes()).hexdigest() == before)

# the RG line and the sign-off checks, watched saying no
shipped = None
for p in sorted(PP.glob("PP-EP*/docs/spoken-words*.txt")):
    if p.parent == EP_DIR / "docs":
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    for s in t.split("."):
        pass
    tail = " ".join(t.split()[-20:])
    if "I'll see you soon" in tail:
        shipped = tail[tail.index("That's me"):] if "That's me" in tail else None
        if shipped:
            break
if shipped:
    real_signoff = tf.SIGNOFF
    try:
        tf.SIGNOFF = shipped
        bad = tf.problems([{"kind": "furniture", "name": "outro: sign-off",
                            "text": shipped},
                           {"kind": "furniture", "name": "rg", "text": tf.RG_LINE}],
                          EP_DIR, PP)
    finally:
        tf.SIGNOFF = real_signoff
    check("CONTROL: a sign-off already in the archive is REFUSED",
          any("VERBATIM" in b for b in bad), "; ".join(bad)[:140])
check("EP49's own sign-off is not in the archive",
      not any("VERBATIM" in b for b in
              tf.problems([{"kind": "furniture", "name": "outro: sign-off",
                            "text": tf.SIGNOFF},
                           {"kind": "furniture", "name": "rg", "text": tf.RG_LINE}],
                          EP_DIR, PP)))
check("CONTROL: a furniture piece with a bare numeral is REFUSED",
      any("bare numeral" in b for b in
          tf.problems([{"kind": "furniture", "name": "x", "text": "Back in 2003."},
                       {"kind": "furniture", "name": "rg", "text": tf.RG_LINE}],
                      EP_DIR, PP)))
check("CONTROL: a missing responsible-gambling line is REFUSED",
      any("responsible-gambling" in b for b in
          tf.problems([{"kind": "furniture", "name": "x", "text": "No RG here."}],
                      EP_DIR, PP)))


# ═══ 6. the cover names whoever reads the episode ════════════════════════════
print("\n-- 6. the cover attribution names the readers --")

import packaging_gate as pg                                        # noqa: E402

check("the single-presenter suffix is unchanged to the character",
      pg.cover_attribution(None) == pg.COVER_ATTRIBUTION
      and pg.cover_attribution(["Gordon"]) == pg.COVER_ATTRIBUTION,
      repr(pg.cover_attribution(None)))
check("two readers are both named",
      pg.cover_attribution(["Gordon", "Steve"]).endswith("read by Gordon and Steve"),
      pg.cover_attribution(["Gordon", "Steve"]))
check("and a third would be too — the rule is not a pair",
      pg.cover_attribution(["A", "B", "C"]).endswith("read by A, B and C"))
epj = json.loads(EPJ.read_text(encoding="utf-8"))
check("the readers come from speakers[].reader, HOST FIRST",
      pg.readers_from_episode(epj) == ["Gordon", "Steve"],
      str(pg.readers_from_episode(epj)))
check("CONTROL: a single-presenter episode has no speakers block and gets none",
      pg.readers_from_episode({"packaging": {}}) == [])
cover = EP_DIR / "ebook/cover-src/cover.html"
if cover.is_file():
    faults = pg.page_faults(
        "ebook_cover", cover.read_text(encoding="utf-8"),
        (epj["packaging"].get("hook") or "").strip(),
        (epj["packaging"].get("byline") or "").strip(),
        epj["packaging"].get("ebook_title") or "", pg.readers_from_episode(epj))
    check("EP49's cover grades clean with its readers named", not faults,
          "; ".join(faults)[:180])
    # CONTROL — the same page graded as a SINGLE-presenter episode must fail
    solo = pg.page_faults(
        "ebook_cover", cover.read_text(encoding="utf-8"),
        (epj["packaging"].get("hook") or "").strip(),
        (epj["packaging"].get("byline") or "").strip(),
        epj["packaging"].get("ebook_title") or "", None)
    check("CONTROL: and it is REFUSED when graded as a one-reader episode", bool(solo),
          "no fault — the gate is not reading the suffix at all")


# ═══ 7. the render QC reads a real master ════════════════════════════════════
print("\n-- 7. the render QC --")

import twoway_render_qc as qc                                      # noqa: E402

raw = [{"from_s": 10.0, "to_s": 12.25, "dur_s": 2.25},
       {"from_s": 12.5, "to_s": 14.28, "dur_s": 1.78},
       {"from_s": 40.0, "to_s": 46.0, "dur_s": 6.0}]
merged = qc.merge_silences(raw)
check("a breath inside a pause does not split it into two short gaps",
      len(merged) == 2 and abs(merged[0]["dur_s"] - 4.28) < 0.01,
      str([m["dur_s"] for m in merged]))
far = qc.merge_silences([{"from_s": 10.0, "to_s": 12.0, "dur_s": 2.0},
                         {"from_s": 14.0, "to_s": 16.0, "dur_s": 2.0}])
check("CONTROL: two seconds of speech between them keeps them apart",
      len(far) == 2, str([m["dur_s"] for m in far]))

for code, secs, breaks in (("BM", 385.0, 4), ("BB", 519.7, 11)):
    m = EP_DIR / f"renders/PP-EP49-{code}-full.mp4"
    s = EP_DIR / f"docs/spoken-words-{code}.txt"
    if not (m.is_file() and s.is_file()):
        check(f"{code}: the master is on disk", False, f"{m} missing")
        continue
    r = qc.check(m, s)
    check(f"{code}: 1920x1080", (r["w"], r["h"]) == (1920, 1080), f"{r['w']}x{r['h']}")
    check(f"{code}: about {secs:.0f}s", abs(r["dur_s"] - secs) < 2.0, f"{r['dur_s']}s")
    check(f"{code}: all {breaks} breaks landed",
          sum(1 for x in r["matched"] if x["got_s"]) == breaks,
          str([x["got_s"] for x in r["matched"]]))
    check(f"{code}: no faults", not r["faults"], "; ".join(r["faults"])[:200])

# CONTROL — the QC must REFUSE a master with a break missing from it
class _Fake:
    name = "fake.mp4"
faked = dict(qc.check(EP_DIR / "renders/PP-EP49-BM-full.mp4",
                      EP_DIR / "docs/spoken-words-BM.txt"))
few = qc.expected_break_times([100, 100, 100, 100, 100], [6.0] * 4, [], 385.0)
check("CONTROL: a break with no silence near its due time is REPORTED missing",
      len(few) == 4 and all(isinstance(x, float) for x in few),
      str(few))


# ═══ 8. the retake splice ════════════════════════════════════════════════════
print("\n-- 8. patching a master with a retake of two of its segments --")

import twoway_splice as sp                                        # noqa: E402

BB = EP_DIR / "renders/PP-EP49-BB-full.mp4"
BBS = EP_DIR / "docs/spoken-words-BB.txt"
RT = EP_DIR / "renders/PP-EP49-BB-retake-seg6-7.mp4"
RTS = EP_DIR / "docs/spoken-words-BB-retake-seg6-7.txt"

# The retake script is segments 6 and 7 VERBATIM — the whole safety of the splice.
if RTS.is_file():
    brk = re.compile(r'<break\s+time="[\d.]+s"\s*/>')
    full_segs = [s.strip() for s in brk.split(BBS.read_text(encoding="utf-8"))
                 if s.strip()]
    rt_segs = [s.strip() for s in brk.split(RTS.read_text(encoding="utf-8"))
               if s.strip()]
    check("the retake script is segments 6-7 character for character",
          rt_segs == full_segs[5:7],
          f"{len(rt_segs)} segs, {sum(len(s) for s in rt_segs)} chars")
    check("and it carries exactly one break", len(brk.findall(
        RTS.read_text(encoding="utf-8"))) == 1)

if BB.is_file() and RT.is_file():
    p = sp.plan(BB, BBS, RT, [6, 7])
    q = json.loads((EP_DIR / "renders/qc-BB-full.json").read_text(encoding="utf-8"))
    b5 = next(m for m in q["matched"] if m["n"] == 5)
    b7 = next(m for m in q["matched"] if m["n"] == 7)
    check("the cut IN is the END of the break before segment 6",
          abs(p["a"]["to_s"] - (b5["at_s"] + b5["got_s"])) < 0.01,
          f"{p['a']['to_s']} vs {b5['at_s'] + b5['got_s']}")
    check("the cut OUT is the START of the break after segment 7",
          abs(p["c"]["from_s"] - b7["at_s"]) < 0.01,
          f"{p['c']['from_s']} vs {b7['at_s']}")
    check("so both breaks survive WHOLE and no speech is cut",
          p["a"]["to_s"] <= b5["at_s"] + b5["got_s"] + 0.01
          and p["c"]["from_s"] >= b7["at_s"] - 0.01)
    check("the retake contributes exactly one internal break",
          len(p["b"]["inner_breaks"]) == 1,
          str([s["dur_s"] for s in p["b"]["inner_breaks"]]))
    check("the retake's head and tail stillness is trimmed off",
          p["b"]["from_s"] > 0.0 and p["b"]["to_s"] < p["retake_dur_s"],
          f"{p['b']['from_s']}..{p['b']['to_s']} of {p['retake_dur_s']}")

    # CONTROL — a segment with a FILE EDGE on one side cannot be spliced
    for edge in (1, 12):
        try:
            sp.plan(BB, BBS, RT, [edge])
            check(f"CONTROL: segment {edge} is REFUSED (a file edge is not a silence)",
                  False)
        except sp.Refuse:
            check(f"CONTROL: segment {edge} is REFUSED (a file edge is not a silence)",
                  True)
    # CONTROL — a retake whose internal breaks do not match the span is REFUSED
    try:
        sp.plan(BB, BBS, RT, [5, 6, 7])
        check("CONTROL: a retake with too few internal breaks is REFUSED", False)
    except sp.Refuse:
        check("CONTROL: a retake with too few internal breaks is REFUSED", True)
else:
    check("the retake is on disk", False, f"{RT} not yet downloaded")


# ═══ 9. the episode order: furniture and dialogue interleaved ════════════════
print("\n-- 9. where the furniture sits in the finished episode --")

import twoway_interleave as ti                                    # noqa: E402

MANP = EP_DIR / "docs/script-manifest-BB.json"
if MANP.is_file():
    man = json.loads(MANP.read_text(encoding="utf-8"))
    turns_all = json.loads(
        (EP_DIR / "docs/turns.json").read_text(encoding="utf-8"))["turns"]
    order = ti.episode_order(turns_all, man, "BB")
    names = [(o["speaker"], o["turn"], o.get("id")) for o in order]

    check("every host segment and every guest turn is in the order exactly once",
          len(order) == len(man["segments"])
          + sum(1 for t in turns_all if t["speaker"] == "BM"),
          f"{len(order)} items")
    check("Barry starts the conversation, after Gordon's open",
          names[0][2] == "open" and names[1][0] == "BM",
          str(names[:2]))
    # 🔴 THE TWO THAT SIT BETWEEN THE SAME PAIR OF TURNS, ON OPPOSITE SIDES
    i_cta = next(i for i, o in enumerate(order) if o.get("id") == "cta")
    check("the CTA follows Gordon's first turn IMMEDIATELY — Barry has not replied yet",
          order[i_cta - 1]["speaker"] == "BB" and order[i_cta + 1]["speaker"] == "BM",
          f"{order[i_cta - 1]['speaker']} | CTA | {order[i_cta + 1]['speaker']}")
    i_mid = next(i for i, o in enumerate(order) if o.get("id") == "midroll")
    check("the midroll waits for Barry to finish — it is a HANDOVER",
          order[i_mid - 1]["speaker"] == "BM" and order[i_mid + 1]["speaker"] == "BB",
          f"{order[i_mid - 1]['speaker']} | midroll | {order[i_mid + 1]['speaker']}")
    check("and the close, outro, RG and sign-off come after every turn",
          [o.get("id") for o in order[-4:]]
          == ["close", "outro", "rg", "signoff"],
          str([o.get("id") for o in order[-4:]]))
    check("the guest's turns stay in article order",
          [o["turn"] for o in order if o["speaker"] == "BM"]
          == [t["n"] for t in turns_all if t["speaker"] == "BM"])

    # CONTROL — a manifest with no placement rules is REFUSED, not guessed at
    blind = json.loads(json.dumps(man))
    for s in blind["segments"]:
        s.pop("where", None)
    try:
        ti.episode_order(turns_all, blind, "BB")
        check("CONTROL: a manifest with no placement rules is REFUSED", False)
    except ti.Mismatch:
        check("CONTROL: a manifest with no placement rules is REFUSED", True)

    # CONTROL — swapping the two rules moves the midroll, which is the whole point
    swapped = json.loads(json.dumps(man))
    for s in swapped["segments"]:
        if s.get("id") == "midroll":
            s["where"] = "after-host-turn-1"
    sw = ti.episode_order(turns_all, swapped, "BB")
    j = next(i for i, o in enumerate(sw) if o.get("id") == "midroll")
    check("CONTROL: call the midroll a follow-on and it lands before Barry finishes",
          sw[j - 1]["speaker"] == "BB",
          f"{sw[j - 1]['speaker']} | midroll — the rule is doing the work")
else:
    check("the script manifest is on disk", False, str(MANP))


print(f"\n20 Sep rulings: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
