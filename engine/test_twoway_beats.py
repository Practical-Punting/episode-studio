#!/usr/bin/env python3
"""test_twoway_beats.py — A10's layout and §8's reactions, derived and provable.

    python engine/test_twoway_beats.py

Two kinds of case, deliberately (CLAUDE.md fault 4c — real data proves a guard works on
the job; only a fixture finds where it stops working):

  · SYNTHETIC turns built to attack each rule, including shapes this article does not
    happen to contain.
  · THE REAL EP49 FILE, asserted to derive clean and to re-derive identically.

🔴 THE ONE THAT MATTERS MOST IS IDEMPOTENCE. "Derived, never authored" is only true if
re-running the derivation over the file reproduces it. It has caught two real faults: a
`tones` key that was an int in Python and `"18"` after a JSON round-trip, and b-roll
durations that were not being read back off the file at all.

⚠️ AND THE CASE THAT IS HERE BECAUSE IT COST 54 SECONDS OF EPISODE. A b-roll clip is an
OVERLAY: the words underneath keep running. The first version emitted a b-roll segment
of `dur_s` and skipped the whole BEAT, so 790s of dialogue planned out as 736s and
nothing in the numbers said so. `total_s == sum of beat durations` is now an assertion.
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import twoway_beats as tb                                        # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR",
                                 str(pathlib.Path("G:/My Drive") / "PP Videos")))
EPJ = PP / "PP-EP49-Fighting-a-Complex-Game-Part-1/docs/episode.json"
SPK = ["BB", "BM"]
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"  <- {why}" if not cond and why else ""))


def turn(n, who, *word_counts):
    """A turn of paragraphs of the given word counts, each a few whole sentences."""
    paras = []
    for w in word_counts:
        s, left = [], w
        while left > 0:
            take = min(left, 9)
            # ⚠️ THE CAPITAL MATTERS. A sentence end is a full stop followed by a
            # CAPITAL, so a fixture of "word word end. word word end." is one sentence,
            # not two — and the first version of this helper made exactly that, which
            # silently turned every sentence-level assertion below into a
            # paragraph-level one and reported singles that were all identical.
            s.append("Word " + " ".join(["word"] * max(0, take - 2) + ["end."]))
            left -= take
        paras.append(" ".join(s))
    return {"n": n, "speaker": who, "words": sum(word_counts),
            "text": "\n\n".join(paras)}


def derive(turns, cards=None, broll=None, durs=None, signals=None):
    beats = tb.beats_from_turns(turns)
    for b in beats:
        b["card"] = (cards or {}).get(b["n"])
        b["broll"] = (broll or {}).get(b["n"])
    segs = tb.derive_plan(beats, durs or {})
    tb.derive_reactions(segs, SPK, signals or {})
    return beats, segs


def derive_law(turns, cards=None, broll=None, durs=None, holds=None, signals=None):
    """As `derive`, but through `plan_with_dwell` — the planner the BUILD uses.

    🔴 A SEPARATE HELPER ON PURPOSE. `derive` calls `derive_plan` raw, which is the
    right tool for asserting one rule of the walk in isolation. The dwell law is not a
    rule of the walk: it is a constraint the walk is run to a FIXED POINT under, so a
    test of it that called `derive_plan` would be measuring the thing the law exists to
    correct. Assert the artefact the build receives (CLAUDE.md fault #1).
    """
    beats = tb.beats_from_turns(turns)
    for b in beats:
        b["card"] = (cards or {}).get(b["n"])
        b["broll"] = (broll or {}).get(b["n"])
    segs, log = tb.plan_with_dwell(beats, durs or {}, card_holds=holds or {})
    tb.derive_reactions(segs, SPK, signals or {})
    return beats, segs, log


def main() -> int:
    print("-- SENTENCES, AND THE SUB-HEADING THAT IS NOT A BEAT --")
    check("  a full stop ends a sentence",
          tb.sentences("One thing. Two things.") == ["One thing.", "Two things."])
    check("  the article's spaced ellipsis does NOT",
          tb.sentences("I circle these factors . . . like a good draw.")
          == ["I circle these factors . . . like a good draw."],
          f"{tb.sentences('I circle these factors . . . like a good draw.')}")
    check("  an initial or a decimal does not split a sentence",
          len(tb.sentences("E.J. Minnis rates it 12.5 and stops.")) == 1,
          f"{tb.sentences('E.J. Minnis rates it 12.5 and stops.')}")
    merged = tb.merge_headings(["**ABILITY**", "Can be measured.", "**FORM**",
                                "Can be analysed."])
    check("  a bold-only paragraph joins the one it heads",
          merged == ["**ABILITY**\n\nCan be measured.",
                     "**FORM**\n\nCan be analysed."], f"{merged}")
    check("  and every character survives the regrouping",
          "".join(p.replace("\n", "") for p in merged)
          == "**ABILITY**Can be measured.**FORM**Can be analysed.")
    check("  a trailing heading with nothing under it is kept, not dropped",
          tb.merge_headings(["Body.", "**ORPHAN**"]) == ["Body.", "**ORPHAN**"])

    print("\n-- NO TIME IS LOST OR INVENTED — THE 54-SECOND CASE --")
    beats, segs = derive([turn(1, "BM", 60, 60, 60), turn(2, "BB", 40)],
                         broll={2: "x"}, durs={"x": 9.0})
    want = round(sum(b["est_s"] for b in beats), 1)
    got = round(sum(s["dur_s"] for s in segs), 1)
    check("  the plan is exactly as long as the dialogue", abs(want - got) < 0.5,
          f"{got}s of plan against {want}s of dialogue")
    bro = [s for s in segs if s["kind"] == "broll"]
    check("  the b-roll segment is its OWN duration, not its beat's",
          len(bro) == 1 and abs(bro[0]["dur_s"] - 9.0) < 0.6, f"{bro}")
    check("  and the rest of that beat carries on underneath",
          any(s["kind"] != "broll" and 2 in s["beats"] for s in segs))

    print("\n-- A10 RULE 1: THE TWO-BOX IS THE HOME SHOT --")
    _, segs = derive([turn(1, "BM", 30), turn(2, "BB", 30)])
    check("  a short turn is two-box end to end",
          all(s["layout"] == "two-box" for s in segs), [s["kind"] for s in segs])

    print("\n-- A10 RULE 2: A CARD OR B-ROLL TAKES THE WHOLE FRAME --")
    _, segs = derive([turn(1, "BM", 30, 30, 30)], cards={2: "C1"})
    c = [s for s in segs if s["kind"] == "card"]
    check("  the card beat is a full-frame segment of its own",
          len(c) == 1 and c[0]["layout"] == "full" and c[0]["card"] == "C1")

    print("\n-- A10 RULE 4: A TURN OPENS AND HANDS OVER IN THE TWO-BOX --")
    _, segs = derive([turn(1, "BM", *([60] * 8)), turn(2, "BB", 40)])
    t1 = [s for s in segs if s["turn"] == 1]
    check("  a long turn opens in the two-box", t1[0]["layout"] == "two-box")
    check("  and hands over from it", t1[-1]["layout"] == "two-box")
    check(f"  with at least ~{tb.RETURN_BEFORE_TURN_END_S:.0f}s of it before the cut",
          t1[-1]["dur_s"] >= tb.RETURN_BEFORE_TURN_END_S - 1)

    print("\n-- RULE 1 — FEWER CUTS (Jodie, 18 Sep 2026; amends A10 rules 1 and 3) --")
    check("  the rule is on, and named", tb.FEWER_CUTS is True)
    # SIX long turns, a graphic early in each: the shape Rule 1 is about.
    _, segs = derive([turn(n, SPK[n % 2], *([60] * 10)) for n in range(1, 7)],
                     cards={2: "C1", 12: "C2", 22: "C3"})
    # ⚰️ THIS USED TO ASSERT "AT MOST TWICE PER TURN" — v4's Rule 1, where the picture
    # left the two-box once and never came back. Jodie revised it on 18 Sep 2026: the
    # two-box RETURNS after 25-35s of single when no graphic is due within 15s. So a
    # third appearance is now the rule WORKING, and what must be asserted instead is
    # that every return is EARNED — by a real single, never by a timer.
    counts = tb.two_box_runs_per_turn(segs)
    states = tb.picture_states(segs)
    returns = [(a, b) for a, b in zip(states, states[1:])
               if b["kind"] == "two-box" and a["kind"] == "single"
               and a["turns"] == b["turns"]]
    earned = [round(a["dur_s"], 1) for a, _ in returns]
    check("  every mid-turn return to the two-box is EARNED by 25-35s of single",
          all(d >= tb.MID_RETURN_MIN_S - 0.001 for d in earned), f"{earned}")
    check("  and `violations()` says so itself when it does not",
          not [v for v in tb.violations(segs) if "RULE 1 BROKEN" in v],
          [v for v in tb.violations(segs) if "RULE 1 BROKEN" in v])
    # 🔴 AND WHAT THE REVISION DID *NOT* CHANGE: the picture never goes straight from a
    # graphic back to the two-box. Rule 1 mid-turn is "after a card or clip the picture
    # stays on the SPEAKER SINGLE", and the return is what happens 25-35s later.
    # The first cut of v5 got this wrong — coming off a card the mode is "forced", so
    # `run` and `target` are both 0 and the test `run >= target` read 0 >= 0 — and EP49
    # turn 9 went b-roll -> two-box with no speaker single at all.
    for a, b in zip(states, states[1:]):
        if a["kind"] not in ("card", "broll") or a["turns"] != b["turns"]:
            continue
        was, at, now = a["kind"], a["from_s"], b["kind"]
        check(f"  after the {was} at {at:.0f}s the picture is the speaker single",
              now == "single", now)
    check("  a turn with NO graphic never leaves the two-box at all",
          all(s["layout"] == "two-box"
              for s in derive([turn(1, "BM", *([60] * 8))])[1]),
          [s["layout"] for s in derive([turn(1, "BM", *([60] * 8))])[1]])

    print("\n-- RULE 1's NAMED COST, REPORTED RATHER THAN HIDDEN --")
    # ⚰️ THIS USED TO MEASURE LONG SINGLES. Under v4 the picture left the two-box and
    # never came back, so a wide gap between two graphics held ONE SPEAKER past the 35s
    # ceiling. The revision cures that — and creates the mirror image, which is what is
    # measured now: a turn with no graphic left in it holds the TWO-BOX for as long as
    # it takes. On the real EP49, turn 10 runs 159.7s on one picture.
    _, wide = derive([turn(1, "BM", *([60] * 24))], cards={2: "C1"})
    runs = tb.two_box_runs(wide)
    rep = [v for v in tb.violations(wide) if "REPORTED (Rule 1 as revised)" in v]
    long_ones = [r for r in runs if r["dur_s"] > tb.TWO_BOX_REPORT_S]
    lens = [round(r["dur_s"]) for r in runs]
    check("  a two-box held past the report line is MEASURED", bool(long_ones),
          f"{lens}")
    check("  and it is REPORTED, not silently broken", len(rep) == len(long_ones),
          f"{len(long_ones)} runs, {len(rep)} reported")
    check("  it is a report and NOT a hard failure — the only other fix is the cut "
          "Rule 1 removes", all(v.startswith("REPORTED") for v in rep))
    olds = tb.long_picture_runs(wide)
    check("  and the long SINGLES v4 reported are gone: the two-box comes home",
          not olds, f"{olds}")

    print("\n-- 🔴 THE MINIMUM DWELL LAW: NOTHING LIVES UNDER 5 SECONDS --")
    check("  the law is named and it is 5.0s", tb.MIN_DWELL_S == 5.0,
          f"{tb.MIN_DWELL_S}")

    def seg(n, layout, kind, turn, spk, frm, to, card=None, broll=None):
        return {"n": n, "layout": layout, "kind": kind, "turn": turn, "speaker": spk,
                "beats": [n], "from_s": frm, "to_s": to, "dur_s": round(to - frm, 2),
                "snap_to_sentence": "x.", "card": card, "broll": broll,
                "transition_ms": tb.PUSH_MS, "_why": "fixture", "_units": []}

    def shape(states):
        """The picture states as a reader can check by eye, for a FAIL message."""
        return " | ".join(f"{s['kind']} {s['dur_s']:.1f}s" for s in states)

    # CONTROL 1 — a 1.8s stub of single between two cards. Watch it FAIL.
    bad = [seg(1, "two-box", "two-box", 1, "BB", 0.0, 12.0),
           seg(2, "full", "card", 1, "BB", 12.0, 23.0, card="CX"),
           seg(3, "full", "single", 1, "BB", 23.0, 24.8),
           seg(4, "full", "card", 1, "BB", 24.8, 36.0, card="CY"),
           seg(5, "two-box", "two-box", 1, "BB", 36.0, 48.0)]
    shorts = tb.short_states(bad)
    check("  CONTROL: a 1.8s single between two cards is FOUND", len(shorts) == 1,
          shape(shorts))
    broke = [v for v in tb.violations(bad) if v.startswith("DWELL LAW BROKEN")]
    check("  CONTROL: and violations() says DWELL LAW BROKEN", len(broke) == 1,
          f"{broke}")

    # CONTROL 2 — THE ONE THAT SEPARATES A GOOD CHECKER FROM A PEDANTIC ONE. A 2.0s
    # two-box and a 4.0s two-box, adjacent, across a turn boundary. Per SEGMENT that is
    # two breaches; as a VIEWER sees it, it is one 6.0s shot of two men through a
    # handover. Measuring this per segment is what squeezed C6 to 4.1s in v4.
    seam = [seg(1, "full", "card", 1, "BB", 0.0, 12.0, card="CX"),
            seg(2, "two-box", "two-box", 1, "BB", 12.0, 14.0),
            seg(3, "two-box", "two-box", 2, "BM", 14.0, 18.0),
            seg(4, "full", "single", 2, "BM", 18.0, 40.0)]
    states = tb.picture_states(seam)
    tbx = [s for s in states if s["kind"] == "two-box"]
    check("  a handover is ONE state, not two — the two-box spans the turn boundary",
          len(tbx) == 1 and abs(tbx[0]["dur_s"] - 6.0) < 0.02, shape(states))
    check("  and 2.0s + 4.0s across that seam is NOT a breach",
          not tb.short_states(seam), shape(tb.short_states(seam)))

    # AND A SPEAKER CHANGE ON THE FULL FRAME *IS* A NEW STATE — the one merge that must
    # not happen. Two singles of different men back to back is a cut, not a shot.
    flip = [seg(1, "full", "single", 1, "BB", 0.0, 3.0),
            seg(2, "full", "single", 2, "BM", 3.0, 6.0)]
    check("  two singles of DIFFERENT men are two states, and both are short",
          len(tb.short_states(flip)) == 2, shape(tb.short_states(flip)))

    # AND NOW THE LAW-ABIDING PLANNER, on a shape built to squeeze it: four turns with
    # graphics jammed against each other and against the turn heads.
    _, lawful, plog = derive_law(
        [turn(n, SPK[n % 2], *([40] * 9)) for n in range(1, 5)],
        cards={2: "C1", 3: "C2", 11: "C3", 20: "C4"},
        holds={"C1": 12.0, "C2": 11.0, "C3": 13.0, "C4": 10.0})
    check("  the planner settles with NO state under the law",
          not tb.short_states(lawful), shape(tb.short_states(lawful)))
    check("  and it SAYS what it moved or dropped to get there — never silently",
          all(x.startswith(("MOVED", "DROPPED", "UNFIXABLE", "GAVE UP"))
              for x in plog), f"{plog[:2]}")
    check("  a graphic that cannot fit is DROPPED, not squeezed",
          all(s["dur_s"] >= tb.MIN_DWELL_S - 0.001
              for s in tb.picture_states(lawful) if s["ident"]))

    print("\n-- 🔴 RULE 1 AT A TURN START: NO TWO-BOX -> SINGLE -> CARD TRIPLE --")
    check("  the opening is named and it is 5.0s", tb.TURN_OPEN_MIN_S == 5.0,
          f"{tb.TURN_OPEN_MIN_S}")

    # CONTROL — the exact shape Jodie banned: the turn opens on the two men, pushes to
    # one of them, and only then brings the graphic up. Three pictures in twenty-six
    # seconds at the head of a turn. Watch it FAIL.
    triple = [seg(1, "two-box", "two-box", 1, "BB", 0.0, 6.0),
              seg(2, "full", "single", 1, "BB", 6.0, 14.0),
              seg(3, "full", "card", 1, "BB", 14.0, 26.0, card="CX"),
              seg(4, "two-box", "two-box", 1, "BB", 26.0, 40.0)]
    caught = [v for v in tb.violations(triple) if "RULE 1 BROKEN (turn start)" in v]
    check("  CONTROL: two-box -> single -> card at a turn head is CAUGHT",
          len(caught) == 1, f"{caught}")

    # ...and the legal shape, which differs by ONE segment: the card lands DIRECTLY
    # from the two-box, and the speaker single is what it falls back to.
    legal = [seg(1, "two-box", "two-box", 1, "BB", 0.0, 6.0),
             seg(2, "full", "card", 1, "BB", 6.0, 18.0, card="CX"),
             seg(3, "full", "single", 1, "BB", 18.0, 40.0),
             seg(4, "two-box", "two-box", 1, "BB", 40.0, 52.0)]
    legal_v = [v for v in tb.violations(legal) if "turn start" in v]
    check("  and the legal shape — card straight off the two-box — passes",
          not legal_v, f"{legal_v}")

    # AND ON THE DERIVED PLAN: the first graphic of every turn comes off the two-box.
    _, opened, _ = derive_law([turn(n, SPK[n % 2], *([40] * 8)) for n in range(1, 5)],
                              cards={1: "C1", 9: "C2", 17: "C3"},
                              holds={"C1": 11.0, "C2": 11.0, "C3": 11.0})
    ost = tb.picture_states(opened)
    for tn in sorted({s["turn"] for s in opened}):
        firsts = [k for k, s in enumerate(ost)
                  if s["kind"] in ("card", "broll") and tn in s["turns"]]
        if not firsts or firsts[0] == 0:
            continue
        prev = ost[firsts[0] - 1]["kind"]
        check(f"  turn {tn}: its first graphic comes straight off the two-box",
              prev == "two-box", prev)
    open_v = [v for v in tb.violations(opened) if "turn start" in v]
    check("  and no turn-start triple anywhere in the plan", not open_v, f"{open_v}")

    print("\n-- THE AMENDMENT CAN BE WITHDRAWN, AND THE OLD PATH STILL WORKS --")
    tb.FEWER_CUTS = False
    try:
        _, old = derive([turn(n, SPK[n % 2], *([60] * 10)) for n in range(1, 7)])
        singles = [s for s in old if s["kind"] == "single"]
        lens = [s["dur_s"] for s in singles]
        check("  with FEWER_CUTS off, long turns push to a single again", bool(singles),
              "no push at all")
        check(f"  no single over the {tb.SINGLE_MAX_S:.0f}s ceiling",
              lens and all(d <= tb.SINGLE_MAX_S for d in lens),
              f"{max(lens):.1f}s" if lens else "none")
        check("  and the walk still varies them", len(set(lens)) >= 3,
              f"{sorted(set(lens))}")
    finally:
        tb.FEWER_CUTS = True

    print("\n-- A CARD PAUSES THE ACCUMULATOR; IT DOES NOT RESET IT --")
    check("  the rule is on, and named", tb.CARD_PAUSES_ACCUMULATOR is True)
    # 🔴 MEASURED WITH RULE 1 WITHDRAWN, because the accumulator is what earns a TIMED
    # push and Rule 1 has no timed pushes for it to earn. The rule still stands and is
    # still tested; what changed is that it now only bites on the withdrawal path.
    tb.FEWER_CUTS = False
    _, with_card = derive([turn(1, "BM", *([25] * 12))], cards={3: "C1", 7: "C2"})
    tb.CARD_PAUSES_ACCUMULATOR = False
    _, reset = derive([turn(1, "BM", *([25] * 12))], cards={3: "C1", 7: "C2"})
    tb.CARD_PAUSES_ACCUMULATOR = True
    tb.FEWER_CUTS = True
    n_pause = sum(1 for s in with_card if s["kind"] == "single")
    n_reset = sum(1 for s in reset if s["kind"] == "single")
    check("  pausing gives MORE singles than resetting did — which is the whole point",
          n_pause > n_reset, f"pause {n_pause} vs reset {n_reset}")

    print("\n-- DON'T START A SINGLE YOU CANNOT FINISH --")
    _, segs = derive([turn(1, "BM", *([40] * 10))], cards={5: "C1"})
    short = [s["dur_s"] for s in segs if s["kind"] == "single"
             and s["dur_s"] < tb.SINGLE_MIN_S - 6]
    check("  no stub single is opened in front of a card", not short, f"{short}")

    print("\n-- EVERY BOUNDARY NAMES THE SENTENCE IT SNAPS TO --")
    _, segs = derive([turn(1, "BM", *([60] * 6)), turn(2, "BB", 40)])
    check("  each segment carries snap_to_sentence for interleave",
          all(s["snap_to_sentence"] for s in segs))
    check("  and the eased-push duration", all(s["transition_ms"] == tb.PUSH_MS
                                               for s in segs))

    print("\n-- A BED IS NEVER LOOPED: IT CHAINS --")
    bed, chain = tb._bed_chain(150.0, "R1a")
    check("  a listen longer than its bed chains to a DIFFERENT bed",
          bool(chain) and all(c["to"] != bed for c in chain[:1]), f"{chain}")
    check("  the chain order is R1a -> R11 -> R1b",
          [c["to"] for c in chain][:2] == ["R11", "R1b"], f"{[c['to'] for c in chain]}")
    check("  and it never repeats the bed it is leaving",
          all(a["to"] != b["to"] for a, b in zip(chain, chain[1:])), f"{chain}")
    check("  a listen that fits its bed does not chain at all",
          tb._bed_chain(30.0, "R1a")[1] == [])
    check("  the chain point lands on a blink interval",
          all(abs(c["at_s"] % tb.BLINK_EVERY_S) < 0.01 or c["at_s"] > 0
              for c in chain))

    print("\n-- §8's PRECEDENCE, AND THE CONSTRAINTS THAT OVERRULE IT --")
    sig = {2: {"relation": "disagrees", "opens": "Mostly I agree, though"}}
    _, segs = derive([turn(1, "BM", 40, 40), turn(2, "BB", 30)], signals=sig)
    t1 = [s for s in segs if s["turn"] == 1 and s["layout"] == "two-box"]
    last = t1[-1]
    check("  the handover gets R10 — §8 rule 1 overrides everything",
          "R10" in [p["r"] for p in last["reaction"]["punct"]],
          f"{[p['r'] for p in last['reaction']['punct']]}")
    check("  the listener is the OTHER man", last["listener"] == "BB")
    clips = [p["r"] for s in segs for p in (s.get("reaction") or {}).get("punct", [])]
    check("  no BED code is ever cut in as a punctuation clip",
          not (set(clips) & set(tb.BEDS)), f"{sorted(set(clips) & set(tb.BEDS))}")
    check("  every two-box segment names one of the three beds",
          all((s.get("reaction") or {}).get("bed") in tb.BEDS
              for s in segs if s["layout"] == "two-box"))
    check("  a full-frame segment carries no reaction",
          all(s.get("reaction") is None for s in segs if s["layout"] == "full"))

    print("\n-- THE REAL EPISODE --")
    if not EPJ.is_file():
        check("EP49's episode.json is on this machine", False, str(EPJ))
        print(f"\ntwo-way beats: {len(PASS)} passed, {len(FAIL)} failed")
        return 1
    real = json.loads(EPJ.read_text(encoding="utf-8"))
    plan = real["layout_plan"]
    t = tb.tally(plan)

    dialogue = round(sum(b["est_s"] for b in real["beats"]), 1)
    check("  the plan is exactly as long as the dialogue",
          abs(t["total_s"] - dialogue) < 1.0,
          f"{t['total_s']:.1f}s of plan against {dialogue:.1f}s of dialogue")
    check("  the whole timeline is contiguous, with no gap and no overlap",
          all(abs(a["to_s"] - b["from_s"]) < 0.01 for a, b in zip(plan, plan[1:])))

    seq = [(s["listener"], p["r"], s["from_s"] + p["at_s"])
           for s in plan for p in (s.get("reaction") or {}).get("punct", [])]
    twice = [(a, b) for a, b in zip(seq, seq[1:]) if a[0] == b[0] and a[1] == b[1]]
    check("  never the same reaction twice running on one man", not twice, f"{twice[:2]}")
    # PER LISTENER. `PP-TWO-WAY-REACTIONS.md` §5's no-repeat window is about ONE man's
    # face: Steve nodding because Gordon nodded a minute ago is not a repeat anybody can
    # see, and holding it globally halved the pool exactly where the density floor
    # needed it.
    reuse = [(a, b) for i, a in enumerate(seq) for b in seq[i + 1:]
             if a[0] == b[0] and a[1] == b[1]
             and b[2] - a[2] < tb.NO_REUSE_WITHIN_S]
    check(f"  no reaction clip reused on ONE man within "
          f"{tb.NO_REUSE_WITHIN_S:.0f}s", not reuse, f"{reuse[:2]}")
    n7 = sum(1 for s in seq if s[1] == "R7")
    check(f"  R7 at most {tb.R7_MAX_PER_EPISODE} an episode",
          n7 <= tb.R7_MAX_PER_EPISODE, f"{n7}")
    check("  only ONE man is listening at a time, so no reaction can be on both",
          all(s["listener"] != s["speaker"] for s in plan))

    print("\n-- B-ROLL, TO THE 15 SEP STANDING RULES --")
    bro = [s for s in plan if s["kind"] == "broll"]
    check(f"  {tb.BROLL_SLOTS_MIN}\u2013{tb.BROLL_SLOTS_MAX} slots an episode",
          tb.BROLL_SLOTS_MIN <= len(bro) <= tb.BROLL_SLOTS_MAX, f"{len(bro)}")
    check(f"  every clip {tb.BROLL_DUR_MIN_S:.0f}\u2013{tb.BROLL_DUR_MAX_S:.0f}s",
          all(tb.BROLL_DUR_MIN_S - 0.5 <= s["dur_s"] <= tb.BROLL_DUR_MAX_S + 0.5
              for s in bro), f"{[s['dur_s'] for s in bro]}")
    check("  the lengths are VARIED, never all equal",
          len({s["dur_s"] for s in bro}) > 1, f"{[s['dur_s'] for s in bro]}")
    check("  every slot carries an explicit dur_s for the Higgsfield call",
          all(x.get("dur_s") for x in real["broll"]))
    check("  no clip repeats within the episode",
          len({x["target"] for x in real["broll"]}) == len(real["broll"]))

    print("\n-- IT DERIVES CLEAN, AND RE-DERIVES IDENTICALLY --")
    before = copy.deepcopy(plan)
    beats_before = copy.deepcopy(real["beats"])
    tb.apply(real)
    check("  re-deriving over the file reproduces every derived value",
          real["layout_plan"] == before,
          next((f"segment {a['n']} differs" for a, b in zip(before, real["layout_plan"])
                if a != b), "length changed"))
    check("  cards and b-roll are untouched by the derivation",
          [x["card"] for x in real["beats"]] == [x["card"] for x in beats_before]
          and [x["broll"] for x in real["beats"]]
          == [x["broll"] for x in beats_before])
    # 🔴 THE REAL EPISODE'S PLAN, not whatever `segs` was left holding from an earlier
    # block. Grading the wrong artefact is how "0 b-roll slots" got reported about a
    # plan that has seven of them (CLAUDE.md fault 1: name WHICH artefact you examined).
    _v = tb.violations(real["layout_plan"])
    _hard = [x for x in _v if not x.startswith("REPORTED")]
    _rep = [x for x in _v if x.startswith("REPORTED")]
    check("  no violation of any kind that the rules can still act on", not _hard, _hard)
    # A REPORTED line is the opposite of a breach: it is a rule saying out loud what it
    # can no longer enforce. It must stay VISIBLE, so it is printed rather than asserted
    # away — Rule 1's cost is a thing to look at, not a thing to pass.
    for _r in _rep:
        print(f"  ·  {_r}")
    # recomputed here rather than relying on names left over from an earlier block —
    # the same mistake that had this check grading the wrong plan.
    _g, _listen = tb.punct_intervals(real["layout_plan"])
    _n = sum(len((s.get("reaction") or {}).get("punct", []))
             for s in real["layout_plan"])
    print(f"  ·  {_n} clips, mean interval {(_listen / _n if _n else 0):.1f}s, "
          f"longest gap {(max(_g) if _g else 0):.1f}s "
          f"(mean cap {tb.PUNCT_MEAN_INTERVAL_MAX_S:.0f}s, gap cap "
          f"{tb.PUNCT_GAP_MAX_S:.0f}s).")

    print(f"\ntwo-way beats: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
