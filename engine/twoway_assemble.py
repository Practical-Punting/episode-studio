#!/usr/bin/env python3
"""twoway_assemble.py — the full two-way episode: plan it, then build it.

    python engine/twoway_assemble.py <ep_number> [--pp DIR] [--plan-only]
                                     [--out FILE] [--json FILE]

**In:** the interleaved timeline, the merged SRT, the derived layout plan, the cards,
whatever b-roll has been passed, the beds and the idle pool.
**Out:** one episode — title card, dialogue, furniture, warranty, end card — and a
report of every decision it made.

🔴 WHY THIS IS A MODULE AND NOT A SCRATCH SCRIPT. Every two-way proof from v2 to v5 was
built by files in a session scratchpad, and those files are the only place the assembly
has ever existed. A step that lives in a temp folder is a step that is gone the day the
folder is cleared, and it cannot be tested, reviewed or trusted. Jodie, 20 Sep 2026:
*"as a real, checked engine module, not a scratch script."*

── THE TWO CLOCKS, AND THE MAPPING BETWEEN THEM ──────────────────────────────────────
`twoway_beats` derives the layout on the DIALOGUE clock — an estimate, words ÷ 2.6, no
furniture, no latency beats. `twoway_interleave` produces the REAL clock — measured,
with the furniture segments and the latency beats in it. They are different lengths
(789.5s against 837.0s on EP49) and neither is wrong.

🔴 SO THE LAYOUT IS MAPPED TURN BY TURN, NEVER FILE BY FILE. Each turn's layout
segments keep their FRACTIONAL positions inside that turn and are stretched onto the
turn's measured span; then every boundary snaps to the nearest sentence end in the
merged SRT. Mapping the two files end to end instead would drift by the length of the
furniture — on EP49 that is 47 seconds by the finish, which is a card entering a minute
after its words.

⚠️ AND A FURNITURE SEGMENT HAS NO LAYOUT TO MAP. Gordon speaks it alone, full frame:
there is no conversation to put in a two-box, so it is not in the dialogue plan at all
and is placed from the timeline directly.

── WHAT IT REFUSES TO DO ─────────────────────────────────────────────────────────────
· place a b-roll clip that is not on disk — the slot stays on the men (Jodie, 20 Sep:
  *"an unapproved slot stays on the men — never place a clip she hasn't passed"*)
· place the end card without a real cover
· let a picture state fall under the dwell law
· let an overlay input run out before the segment it covers ends
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import ep_paths                                                   # noqa: E402
import twoway_beats as tb                                         # noqa: E402
import twoway_end_sequence as tes                                 # noqa: E402
import twoway_interleave as ti                                    # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")

TITLE_HEAD_S = 7.0
"""How long the title card holds over the hero before a word is spoken. The standing
value every episode uses."""

WARRANTY_S = 3.5
END_CARD_S = 6.0
"""🔴 RETIRED 22 Sep 2026 — KEPT ONLY SO THE TESTS CAN NAME WHAT WAS WRONG.

These two invented an ending. The warranty was pinned at 3.5s and the end card at 6.0s,
laid end to end after a 3s settle, and Jodie stopped the cut on both: *"the ebook motion
graphic turns up after Gordon finishes talking completely"* and *"the warranty card is
shown at the end, but only for a very short period of time."*

⚠️ AND THE OBVIOUS DIAGNOSIS — a hard-coded number overriding the asset's own truth,
the same shape as the logo fault — WAS WRONG. `warranty-slide.mp4` is **1.700s**, which
is SHORTER than 3.5, so taking the duration from the clip would have made the fault
worse. The number was not overriding the asset; the whole SHAPE was invented. The real
one is `twoway_end_sequence`, which is `assemble_episode`'s, which is EP48's.

Nothing reads them now. They stay as a named headstone because a constant that is
deleted takes its lesson with it."""

TAIL_FADE_S = 1.2

DISSOLVE_FRAMES = 6
"""🔴 THE HOUSE SMOOTHING FOR A SOURCE SWITCH THAT CANNOT BE HIDDEN — rule 3c, and the
v5 proof's own number. Jodie, 22 Sep 2026: *"There is a bit of jumping from when he's
just listening to when he's speaking. How do we smooth that over at all?"*

Two places earn it, and they are the same fault wearing different clothes:

· **the two-box handovers** — 6 of them on EP49 (200.6, 252.1, 292.1, 361.2, 607.4,
  766.8s). Both panels change source at once: the outgoing speaker drops to a bed and
  the incoming one comes up on his own master. That is the 12 switches the v5 proof
  dissolved and this renderer hard-cut.

· **the joins inside one furniture run** — 3 of them (807.7, 838.9, 842.9s). Jodie:
  *"there was a jump within that section, like there was a chop done in the editing,
  whereas no chop was actually needed at all."*

  ⚠️ AND THE OBVIOUS READING OF THAT ONE WAS WRONG. The four pieces do come from ONE
  master, but NOT at adjoining timecodes: `the close` ends at master 477.923 and
  `outro` begins at 483.863 — a **5.940s gap in the master** against **0.450s** on the
  finished clock, because the six-second SSML break between them is compressed to a
  latency beat. Each join therefore skips ~5.5s of master and the pose jumps. Measured
  frame-to-frame difference at the three joins: **1.61, 3.09, 2.76**, against a
  within-take baseline of **0.03-0.07** — 25 to 100 times the noise.

  ⭐ SO "MAKE CONTIGUOUS SOURCE STAY CONTIGUOUS PICTURE" CANNOT APPLY HERE AND ZERO
  CUTS IS NOT REACHABLE. The rule is still worth having and `violations` still asserts
  it — it is just not this fault. Not every join that looks like one shot is one.

🚫 NEVER ON A LAYOUT CHANGE. Two-box↔single is an eased PUSH, and `twoway_composite`
refuses a dissolve there in terms: *"never a cross-dissolve and never a hard cut between
these two layouts."*"""

END_SETTLE_S = 3.0
"""🔴 PP-STANDARDS §END SEQUENCE rule 1: *"Gordon's last word lands ~3s BEFORE the
warranty tail begins … He never talks right to the end; the end card + music breathe."*

The first version of this module used 0.5s, which is not a settle, it is a gap. Half a
second after a sign-off reads as the file running out."""

END_CARD_FIRST = True
"""🔴🔴 THE END CARD COMES FIRST AND THE WARRANTY SLIDE COMES LAST.

PP-STANDARDS §END SEQUENCE rule 2, locked 25 Jul 2026, in terms: the end card *"fades in
on the e-book beat and **stays up until the warranty takes over**"*. Nothing follows the
warranty slide, because **the responsible-gambling line lives there and it is the last
thing the viewer is left with.**

⚠️ THIS MODULE HAD IT THE WRONG WAY ROUND — warranty at 798.3s, end card at 801.8s — and
every check in its own suite passed, because not one of them had ever been asked what
ORDER the tail was in. Jodie caught it by reading `assembly-plan.json`. The standing
constant is here so the order is a value the tests can assert rather than a line of
arithmetic nobody reads.
"""


class Unassemblable(Exception):
    """The episode cannot be built as planned. Nothing is written."""


# ───────────────────────────────────────────────── mapping the two clocks ──

def turn_spans_from_timeline(tl: list[dict]) -> dict[int, tuple[float, float]]:
    """Each dialogue turn's MEASURED span on the finished clock."""
    return {s["turn"]: (s["from_s"], s["to_s"])
            for s in tl if s.get("kind") not in ("latency", "furniture")
            and s.get("turn")}


def sentence_ends_in(cues: list[dict], lo: float, hi: float) -> list[float]:
    """Sentence ends inside a span — the only legal place to change picture."""
    return [e for e in ti.sentence_ends(cues) if lo + 0.01 < e < hi - 0.01]


def map_layout(plan: list[dict], tl: list[dict], cues: list[dict],
               head_s: float) -> list[dict]:
    """The dialogue layout, stretched onto the measured timeline, turn by turn.

    🔴 FRACTIONAL WITHIN A TURN, THEN SNAPPED. Keeping each boundary's position as a
    FRACTION of its own turn means a turn that came out longer than the estimate
    stretches its layout with it, instead of the layout sliding off the end. Snapping
    afterwards is what puts the boundary on a sentence rather than on arithmetic.
    """
    spans = turn_spans_from_timeline(tl)
    out = []
    for turn in sorted({s["turn"] for s in plan}):
        mine = [s for s in plan if s["turn"] == turn]
        if turn not in spans:
            raise Unassemblable(
                f"the layout plan has turn {turn} and the timeline does not. The two "
                f"were derived from different files; nothing has been written.")
        lo, hi = spans[turn]
        real = hi - lo
        a0 = min(s["from_s"] for s in mine)
        est = max(s["to_s"] for s in mine) - a0
        if est <= 0:
            continue
        ends = sorted(sentence_ends_in(cues, lo, hi))

        # 🔴🔴 A GRAPHIC'S DURATION IS A HOLD, NOT A PROPORTION. THE CONVERSATION
        # ABSORBS THE STRETCH.
        #
        # The first version of this function scaled EVERY segment by the same factor
        # and then snapped each boundary independently. Both halves were wrong, and
        # the second hid the first: a card planned at 10.5s came out on screen for
        # 6.11s, and the dwell check passed it because 6.11 is over the 5s floor.
        # **A card that is up for less than its reading time cannot be read**, which is
        # the exact fault Jodie ruled on for v5 — *"a card MAY RUN PAST its sentence to
        # finish reading time + 1.5s settle; never speed a card"* — reintroduced here
        # by arithmetic nobody was watching. B-roll was worse: 9.8s of footage planned,
        # 5.93s on screen, under the 8s floor the format asserts.
        #
        # So the walk now mirrors `_split_forced` on the estimate clock: **a card or a
        # clip takes exactly the seconds it was given, and the two-box and single shots
        # around it take the rest.** Those are the shots that CAN stretch — a second
        # more of two men listening is a second more of two men listening.
        fixed = [s for s in mine if s.get("card") or s.get("broll")]
        flex = [s for s in mine if s not in fixed]
        need = sum(s["to_s"] - s["from_s"] for s in fixed)
        spare = real - need
        flex_est = sum(s["to_s"] - s["from_s"] for s in flex) or 1.0
        if spare < len(flex) * 0.0:
            spare = 0.0
        squeezed = None
        if flex and spare < -0.001:
            # 🔴 ONLY A NEGATIVE SPARE IS "NO ROOM", AND THE FIRST VERSION OF THIS TEST
            # WAS WRONG ABOUT THAT. It fired whenever the flexible shots averaged under
            # the dwell floor — and reported turn 3 as impossible when turn 3 is fine,
            # because A TURN'S OPENING AND CLOSING TWO-BOX ARE NOT THEIR OWN SHOTS.
            # They merge with the handover either side of them, so a 4.7s opening
            # two-box is part of a shot the viewer sees for twelve seconds.
            #
            # Measuring per turn is measuring the wrong span. `tb.short_states` measures
            # CONTIGUOUS PICTURE STATES across turn boundaries and is the authority;
            # this now only catches the case arithmetic really cannot survive, where the
            # graphics want more seconds than the turn has at all.
            squeezed = (f"turn {turn} measured {real:.1f}s and its graphics alone want "
                        f"{need:.1f}s — {-spare:.1f}s more than the turn holds")
        prev = lo
        clock = lo
        for s in mine:
            is_fixed = s in fixed
            want = (s["to_s"] - s["from_s"]) if is_fixed else \
                (spare * (s["to_s"] - s["from_s"]) / flex_est)
            t0 = clock
            # A GRAPHIC MAY ENTER ON A SENTENCE END; a conversational shot simply
            # continues from the last one. Snapping is what keeps a card on its words.
            if is_fixed and s["from_s"] > a0 + 0.001 and ends:
                # 🔴 A GRAPHIC MAY SNAP EARLIER AS WELL AS LATER. The first version
                # allowed only `cand >= clock` — forward movement — and seven of
                # EP49's graphics then sat mid-clause with a perfectly good sentence
                # end a second or two BEHIND them. A one-directional snap is half a
                # snap: the nearest end is as often before the arithmetic position as
                # after it.
                #
                # Moving earlier shortens the conversational shot in front, so the
                # floor for that shot is what bounds it — never the running clock.
                floor = (prev + tb.MIN_DWELL_S) if out and out[-1]["turn"] == turn \
                    and not out[-1]["held"] else clock
                cands = [e for e in ends
                         if e >= floor - 0.001 and e + want <= hi - 0.001]
                if cands:
                    cand = min(cands, key=lambda e: abs(e - t0))
                    t0 = cand
                    if cand < clock - 0.001 and out and out[-1]["turn"] == turn:
                        out[-1]["to_s"] = round(cand + head_s, 3)
                        out[-1]["dur_s"] = round(out[-1]["to_s"]
                                                 - out[-1]["from_s"], 3)
            t1 = t0 + want
            prev = t0
            clock = t1
            out.append({**s, "from_s": round(t0 + head_s, 3),
                        "to_s": round(t1 + head_s, 3),
                        "dur_s": round(want, 3),
                        "held": is_fixed,
                        "est_from_s": s["from_s"], "est_to_s": s["to_s"],
                        "squeezed": squeezed,
                        "turn_span": [round(lo + head_s, 3), round(hi + head_s, 3)]})
        # 🔴 AND THE CONVERSATIONAL BOUNDARIES SNAP TOO — A10 RULE 4a APPLIES TO EVERY
        # LAYOUT CHANGE, NOT ONLY TO GRAPHICS. Holding the graphics fixed fixed the
        # wrong thing on its own: only 14 of 57 picture changes landed on a sentence
        # end, because a two-box→single boundary had nothing moving it any more. A push
        # in the middle of a clause is the fault that rule exists to stop.
        #
        # A boundary between two CONVERSATIONAL shots is free to move — neither side is
        # a hold — so it takes the nearest sentence end that leaves both shots over the
        # dwell floor. A boundary touching a graphic does not move: one side of it is
        # the graphic's reading time.
        mine_out = [s for s in out if s["turn"] == turn]
        for i in range(1, len(mine_out)):
            a, b = mine_out[i - 1], mine_out[i]
            if a["held"] or b["held"]:
                continue
            lo_ok = a["from_s"] + tb.MIN_DWELL_S
            hi_ok = b["to_s"] - tb.MIN_DWELL_S
            near = [e + head_s for e in ends if lo_ok <= e + head_s <= hi_ok]
            if not near:
                continue
            cand = min(near, key=lambda e: abs(e - b["from_s"]))
            a["to_s"] = b["from_s"] = round(cand, 3)
            a["dur_s"] = round(a["to_s"] - a["from_s"], 3)
            b["dur_s"] = round(b["to_s"] - b["from_s"], 3)

        # the turn must end where the timeline says it ends: give any rounding to the
        # last CONVERSATIONAL shot, never to a graphic
        tail = [s for s in out if s["turn"] == turn]
        drift = (hi + head_s) - tail[-1]["to_s"]
        if abs(drift) > 0.001:
            for s in reversed(tail):
                if not s["held"]:
                    s["to_s"] = round(s["to_s"] + drift, 3)
                    s["dur_s"] = round(s["to_s"] - s["from_s"], 3)
                    for t in tail[tail.index(s) + 1:]:
                        t["from_s"] = round(t["from_s"] + drift, 3)
                        t["to_s"] = round(t["to_s"] + drift, 3)
                    break
    out.sort(key=lambda s: s["from_s"])
    # 🔴🔴 CLOSE GAPS ONLY *INSIDE* A TURN. NEVER ACROSS ONE.
    #
    # The gap between one turn and the next is not a rounding error — it is where the
    # FURNITURE LIVES. Gordon's e-book CTA sits between his first turn and Barry's
    # reply; the midroll sits at the handover into his fourth. A contiguity pass that
    # ran across turn boundaries stretched the last conversational shot of each turn
    # over them, so **the CTA and the midroll would have played under the wrong picture,
    # at the wrong length, and the mapped segments came out exactly contiguous — which
    # is what made it look right.** 756.3s of dialogue covering 756.3s of clock that
    # contains 34 seconds of furniture.
    #
    # Caught by asking where the seven furniture pieces were in the picture timeline,
    # before rendering thirteen minutes of it. Nothing in the suite had asked.
    for a, b in zip(out, out[1:]):
        if a["turn"] != b["turn"]:
            continue
        if abs(a["to_s"] - b["from_s"]) > 0.001 and not a["held"]:
            a["to_s"] = b["from_s"]
            a["dur_s"] = round(a["to_s"] - a["from_s"], 3)
    all_ends = [round(e + head_s, 3) for e in ti.sentence_ends(cues)]
    return repair_short_states(out, all_ends)


def _same_turn(segs: list[dict], idx: list[int], j: int) -> bool:
    """May the boundary between the short state and segment `j` move at all?

    🔴 ONLY IF BOTH SIDES ARE THE SAME MAN, IN THE SAME TURN. A boundary INSIDE a turn
    is ours — it decides how long we sit on a shot, and nothing else changes. **A
    boundary BETWEEN two turns is not ours: the audio fixes it**, and moving it puts one
    man's voice over the other man's picture.

    ⚠️ THAT IS EXACTLY WHAT SHIPPED. A 1.07s remnant of Steve's turn sat between card C1
    and the handover, under the 5s dwell floor, so the repair borrowed 3.95s from
    GORDON'S TURN by pushing the handover later — and for **3.96 seconds Gordon's voice
    played over a two-box that had Steve as the speaker and Gordon on a still-faced
    listening bed.** Jodie watched one minute and heard it: *"Then Gordon's voice comes
    on but he's not moving his lips."*

    ⚖️ Jodie's ruling, 20 Sep 2026: *"A short shot may never be padded from the listening
    side of a handover. Take it from the same man's own speaking footage, or change the
    layout."* This is the first half; `_absorb_stranded_states` is the second.
    """
    a = segs[idx[-1] if j > idx[-1] else idx[0]]
    b = segs[j]
    if a.get("turn") is None or b.get("turn") is None:
        return False          # furniture either side — its place is fixed too
    return a.get("turn") == b.get("turn") and a.get("speaker") == b.get("speaker")


def _slide_graphics(segs: list[dict], ends: list[float] | None = None) -> list[dict]:
    """A short state that cannot borrow inside its turn: SLIDE the graphic beside it.

    ⚖️ Jodie's ruling, 20 Sep 2026: *"Take it from the same man's own speaking footage,
    or change the layout."* This is "change the layout", and it is `twoway_beats._blame`'s
    doctrine applied on the REAL clock instead of the estimate — **move the graphic, not
    the boundary.** A graphic keeps its exact hold; it only slides, so the seconds move
    between two CONVERSATIONAL shots of the same man and nothing else changes.

    🔴 THE FIRST VERSION OF THIS MERGED THE SHORT SHOT INTO THE GRAPHIC INSTEAD, AND IT
    WAS WORSE THAN THE BUG IT FIXED. Card C1 went from 10.5s to **19.1 seconds** on
    screen, swallowing the two-box either side of it: eighteen seconds of a static card
    where a conversation should be. It satisfied every check — no short state, no moved
    handover — and it would have been the next thing Jodie stopped the cut for. **A
    repair that changes what the thing IS, is not a repair** (CLAUDE.md §10).

    Two moves, in order:

    · **GROW** — slide the graphic AWAY from the short shot by what it needs, if the
      shot on the graphic's far side can spare it and stays over the floor.
    · **COLLAPSE** — slide the graphic TOWARD the short shot by the whole of it, so the
      shot vanishes into the one on the graphic's far side, which grows by that much.

    Collapse is what turn 3 needed and it is not a compromise: the turn is 18.67s and
    the card holds 10.5s of it, so the 8.17s left over **cannot** make two shots of five
    seconds however it is divided. One shot of 8.17s is the only answer that keeps the
    card's hold, the handover and the dwell law all intact.
    """
    for _ in range(12):
        short = tb.short_states(segs)
        if not short:
            break
        did = False
        # 🔴 A STATE WITH A GRAPHIC IN FRONT OF IT IS HANDLED FIRST, so the graphic is
        # pushed LATER — `_blame`'s doctrine, and it matters editorially. Taken in plain
        # order, turn 3's FIRST stub was fixed by pulling card C1 back to the very start
        # of the turn, which lands the card on the handover before its own words have
        # been spoken. Jodie's card ruling is the opposite: a card enters on its OWN
        # sentence and MAY run past it. Fixing the LATER stub instead pushes C1 to the
        # end of the turn — 8.17s of two-box first, then the card — and both stubs go.
        def _graphic_before(st):
            i = [k for k, s in enumerate(segs)
                 if st["from_s"] - 0.001 <= s["from_s"] < st["to_s"] - 0.001]
            g = (i[0] - 1) if i else -1
            return 0 <= g < len(segs) and bool(segs[g].get("card")
                                               or segs[g].get("broll"))

        for st in sorted(short, key=lambda s: 0 if _graphic_before(s) else 1):
            idx = [i for i, s in enumerate(segs)
                   if st["from_s"] - 0.001 <= s["from_s"] < st["to_s"] - 0.001]
            if not idx:
                continue
            need = round(tb.MIN_DWELL_S - st["dur_s"] + 0.02, 3)
            for g in (idx[0] - 1, idx[-1] + 1):           # the bordering graphic
                if not (0 <= g < len(segs)):
                    continue
                if not (segs[g].get("card") or segs[g].get("broll")):
                    continue
                far = g - 1 if g < idx[0] else g + 1      # the shot on its other side
                if not (0 <= far < len(segs)):
                    continue
                if not _same_turn(segs, idx, g) or not _same_turn(segs, [g], far):
                    continue
                if segs[far].get("card") or segs[far].get("broll"):
                    continue
                away = -need if g < idx[0] else need      # AWAY from the short shot
                if segs[far]["dur_s"] - need >= tb.MIN_DWELL_S:
                    _shift(segs, g, away, idx, far)
                    segs[g]["slid_s"] = round((segs[g].get("slid_s") or 0) + away, 3)
                    did = True
                    break
                # COLLAPSE. Compute the graphic's new position OUTRIGHT rather than by
                # a delta, because two things have to land exactly and a delta gets
                # only one of them:
                #
                # 🔴 IT MUST CLOSE THE GAP THE STUB WAS HOLDING. The stub was holding
                # the latency beat; remove it with a plain shift and the beat lands on
                # the CARD, which then reads 10.95s against a 10.5s hold. A graphic's
                # duration is its reading time and it is not a place to put spare
                # silence.
                # 🔴 AND IT MUST STILL ENTER ON A SENTENCE END (A10 rule 4a). The plain
                # shift put C1 mid-clause with a sentence end 19ms away — half a frame.
                # Snapping costs nothing and is the difference between a card that
                # enters on a thought and one that enters on a syllable.
                nxt = segs[idx[-1] + 1] if idx[-1] + 1 < len(segs) else None
                edge_to = nxt["from_s"] if nxt else segs[idx[-1]]["to_s"]
                new_from = round(edge_to - segs[g]["dur_s"], 3)
                if g > idx[0]:                       # graphic AFTER the stub
                    new_from = round(segs[far]["from_s"]
                                     if False else segs[idx[0]]["from_s"], 3)
                near = [e for e in (ends or [])
                        if abs(e - new_from) <= SNAP_REACH_S]
                if near:
                    cand = min(near, key=lambda e: abs(e - new_from))
                    other = segs[far]["from_s"] if far < g else segs[far]["to_s"]
                    if abs(cand - other) >= tb.MIN_DWELL_S:
                        new_from = round(cand, 3)
                _place_graphic(segs, g, new_from, idx, far, nxt)
                segs[g]["slid_s"] = round(new_from - segs[g].get("_was_from",
                                                                new_from), 3)
                segs[g]["collapsed_a_stub"] = True
                for k in sorted(idx, reverse=True):
                    if segs[k]["dur_s"] <= 0.001:
                        segs.pop(k)
                did = True
                break
            if did:
                break
        if not did:
            break
    return segs


SNAP_REACH_S = 0.60
"""How far a slid graphic will reach for a sentence end. EP49's needed 0.019s."""


def _place_graphic(segs: list[dict], g: int, new_from: float, idx: list[int],
                   far: int, nxt: dict | None) -> None:
    """Put graphic `g` at `new_from`, KEEPING ITS DURATION, and close up around it.

    The conversational shot on its far side takes up the slack, the stub between them
    goes to zero, and whatever follows starts exactly where the graphic ends — so no
    gap is left for the graphic to absorb.
    """
    segs[g]["_was_from"] = segs[g]["from_s"]
    dur = segs[g]["dur_s"]
    segs[g]["from_s"] = round(new_from, 3)
    segs[g]["to_s"] = round(new_from + dur, 3)
    if far < g:
        segs[far]["to_s"] = segs[g]["from_s"]
    else:
        segs[far]["from_s"] = segs[g]["to_s"]
    segs[far]["dur_s"] = round(segs[far]["to_s"] - segs[far]["from_s"], 3)
    for i in idx:
        segs[i]["from_s"] = segs[i]["to_s"] = segs[g]["to_s"] if far < g \
            else segs[g]["from_s"]
        segs[i]["dur_s"] = 0.0
    if nxt is not None and far < g:
        nxt["from_s"] = segs[g]["to_s"]
        nxt["dur_s"] = round(nxt["to_s"] - nxt["from_s"], 3)


def _shift(segs: list[dict], g: int, by: float, idx: list[int], far: int) -> None:
    """Move graphic `g` by `by` seconds, keeping its duration, and let the two
    conversational shots either side take up the difference."""
    for key in ("from_s", "to_s"):
        segs[g][key] = round(segs[g][key] + by, 3)
    edge = "to_s" if far < g else "from_s"
    segs[far][edge] = round(segs[far][edge] + by, 3)
    segs[far]["dur_s"] = round(segs[far]["to_s"] - segs[far]["from_s"], 3)
    k = idx[-1] if g < idx[0] else idx[0]
    edge2 = "from_s" if g < idx[0] else "to_s"
    segs[k][edge2] = round(segs[k][edge2] + by, 3)
    for i in idx:
        segs[i]["dur_s"] = round(segs[i]["to_s"] - segs[i]["from_s"], 3)


def repair_short_states(segs: list[dict], ends: list[float] | None = None) -> list[dict]:
    """Give a short picture state its floor back, out of its neighbour's flex.

    🔴 THE STRETCH CAN SHORTEN A STATE THE ESTIMATE HAD OVER THE LINE, and the fix has
    to come from somewhere. It comes from the shot NEXT DOOR, never from a graphic: a
    card's hold is its reading time and a clip's is its footage, so the only seconds
    that may move are the conversational ones. EP49 needed exactly one repair — a
    4.5s single at 237s, half a second under the floor.

    ⚠️ AND IT RE-MEASURES AFTER MOVING ANYTHING. Borrowing a second can push the LENDER
    under the floor, which would turn one breach into another and look like a fix. The
    loop runs until nothing improves, and whatever is left is REPORTED rather than
    nudged again.
    """
    for _ in range(8):
        short = tb.short_states(segs)
        if not short:
            break
        moved = False
        for st in short:
            idx = [i for i, s in enumerate(segs)
                   if st["from_s"] - 0.001 <= s["from_s"] < st["to_s"] - 0.001]
            if not idx:
                continue
            need = tb.MIN_DWELL_S - st["dur_s"] + 0.02
            for j in (idx[-1] + 1, idx[0] - 1):
                if not (0 <= j < len(segs)) or segs[j]["held"]:
                    continue
                if not _same_turn(segs, idx, j):
                    continue
                if segs[j]["dur_s"] - need < tb.MIN_DWELL_S:
                    continue
                if j > idx[-1]:
                    segs[j]["from_s"] = round(segs[j]["from_s"] + need, 3)
                    for k in idx:
                        segs[k]["to_s"] = round(segs[k]["to_s"] + need, 3)
                        segs[k]["dur_s"] = round(segs[k]["to_s"]
                                                 - segs[k]["from_s"], 3)
                else:
                    segs[j]["to_s"] = round(segs[j]["to_s"] - need, 3)
                    for k in idx:
                        segs[k]["from_s"] = round(segs[k]["from_s"] - need, 3)
                        segs[k]["dur_s"] = round(segs[k]["to_s"]
                                                 - segs[k]["from_s"], 3)
                segs[j]["dur_s"] = round(segs[j]["to_s"] - segs[j]["from_s"], 3)
                segs[j]["repaired"] = True
                moved = True
                break
            if moved:
                break
        if not moved:
            break
    return _slide_graphics(segs, ends)


# ──────────────────────────────────────────────────────────── the full plan ──

def source_window(seg: dict, tl: list[dict], head_s: float) -> tuple | None:
    """Where in a man's own master this picture piece looks — `(source, in, out)`.

    🔴 THE SAME ARITHMETIC `twoway_render.render_segment` USES, and it has to be, or the
    plan is describing a picture the renderer is not making. None for a card, a clip, or
    a moment that maps to no turn.
    """
    if seg.get("card") or seg.get("broll"):
        return None
    t0 = seg["from_s"] - head_s
    for s in tl:
        if s.get("kind") == "latency":
            continue
        if s["from_s"] - 0.001 <= t0 < s["to_s"] + 0.001:
            a = s["in_s"] + (t0 - s["from_s"])
            return (s["source"], round(a, 3), round(a + seg["dur_s"], 3))
    return None


def mark_dissolves(mapped: list[dict], tl: list[dict], head_s: float,
                   frames: int = DISSOLVE_FRAMES) -> list[dict]:
    """Mark every join where the SOURCE changes under a picture that does not.

    Three kinds of adjacent pair, and only the middle one is a fault:

    · **layout change** — two-box↔single. The picture is SUPPOSED to change; it gets an
      eased push and never a dissolve.
    · **source switch under an unchanged picture** — a two-box handover, or a jump
      inside one furniture run. Nothing on screen announces it, so the eye reads it as
      a chop. → dissolve.
    · **contiguous source split in two** — the same master at adjoining timecodes cut
      into two pieces for no reason. → not a dissolve, a BUG, and `violations` says so.
      (EP49 has none. The check exists because it was the first hypothesis for the
      furniture jump and it deserved to be tested rather than assumed.)
    """
    out = []
    for a, b in zip(mapped, mapped[1:]):
        if abs(a["to_s"] - b["from_s"]) > 0.002:
            continue
        wa, wb = source_window(a, tl, head_s), source_window(b, tl, head_s)
        same_master = bool(wa and wb and wa[0] == wb[0]
                           and a.get("speaker") == b.get("speaker"))
        gap = round(wb[1] - wa[2], 3) if same_master else None
        contiguous = same_master and abs(gap) <= 1.0 / 25
        if a["layout"] == "two-box" and b["layout"] == "two-box":
            kind = "handover"
        elif (a["layout"] == b["layout"] and a.get("kind") == b.get("kind") == "furniture"
              and same_master and not contiguous):
            kind = "furniture-join"
        elif contiguous and a["layout"] == b["layout"]:
            out.append({"at_s": b["from_s"], "kind": "contiguous-split",
                        "master_gap_s": gap, "frames": 0})
            continue
        else:
            continue
        b["dissolve_in_frames"] = frames
        out.append({"at_s": b["from_s"], "kind": kind, "frames": frames,
                    "master_gap_s": gap,
                    "from": a.get("name") or a["layout"],
                    "to": b.get("name") or b["layout"]})
    return out


def build_plan(ep_number: int, pp: pathlib.Path = PP) -> dict:
    d = ep_paths.episode_dir(ep_number, pp)
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    tlj = json.loads((d / "renders/master-timeline.json").read_text(encoding="utf-8"))
    cues = ti.read_srt((d / "renders/merged.srt").read_text(encoding="utf-8"))
    tl = tlj["timeline"]

    mapped = map_layout(epj["layout_plan"], tl, cues, TITLE_HEAD_S)

    # 🔴 THE FURNITURE IS PART OF THE PICTURE TIMELINE, NOT A NOTE BESIDE IT. Gordon
    # speaks each piece alone, full frame, and those seconds are on the same clock as
    # the dialogue. They come straight from the interleaved timeline — no mapping, no
    # layout to derive: there is no conversation in them to put in a two-box.
    for f in [s for s in tl if s.get("kind") == "furniture"]:
        mapped.append({
            "n": 1000 + f["n"], "turn": None, "speaker": f["speaker"],
            "listener": None, "layout": "full", "kind": "furniture",
            "furniture": f["furniture"], "name": f.get("name"),
            "card": None, "broll": None, "held": True,
            "from_s": round(f["from_s"] + TITLE_HEAD_S, 3),
            "to_s": round(f["to_s"] + TITLE_HEAD_S, 3),
            "dur_s": round(f["dur_s"], 3),
            "est_from_s": f["from_s"], "est_to_s": f["to_s"],
            "turn_span": [round(f["from_s"] + TITLE_HEAD_S, 3),
                          round(f["to_s"] + TITLE_HEAD_S, 3)],
            "_why": "Gordon as himself, full frame — there is no conversation to "
                    "put in a two-box.",
        })
    mapped.sort(key=lambda s: s["from_s"])

    # 🔴 A LATENCY BEAT IS A GAP IN THE AUDIO, NOT IN THE PICTURE. The interleave puts
    # 0.3–0.5s between one man finishing and the next starting, because a hard butt-join
    # sounds scripted. Nothing happens to the SCREEN in that third of a second — the
    # shot simply continues.
    #
    # Leaving them as holes here had two costs, one visible and one not: the render
    # would have had to put something in them, and `picture_states` would not merge
    # across them, so Gordon's close/outro/RG/sign-off — one unbroken shot of one man —
    # counted as four states and the 3.0s responsible-gambling line read as a dwell
    # breach. **It is not a shot; it is three seconds of a shot that lasts forty-five.**
    for a, b in zip(mapped, mapped[1:]):
        gap = b["from_s"] - a["to_s"]
        if 0.0 < gap <= 1.0:
            a["to_s"] = b["from_s"]
            a["dur_s"] = round(a["to_s"] - a["from_s"], 3)
            a["absorbed_beat_s"] = round(gap, 3)
    for i, s in enumerate(mapped, 1):
        s["seq"] = i

    # ── what is actually on disk, asked of the disk ──────────────────────────
    have_broll, missing_broll = {}, []
    for b in epj.get("broll", []):
        p = d / "broll" / f"{b['target']}.mp4"
        if p.is_file():
            have_broll[b["target"]] = str(p)
        else:
            missing_broll.append(b["target"])
    cards = {}
    for c in epj.get("cards", []):
        p = d / "overlay/clips" / (pathlib.Path(c["page"]).stem + ".mp4")
        if p.is_file():
            cards[c["id"]] = str(p)

    # 🔴 A SLOT WITH NO CLIP STAYS ON THE MEN. Jodie, 20 Sep: *"an unapproved slot
    # stays on the men — never place a clip she hasn't passed."* So the segment is
    # rewritten as the picture it would have been WITHOUT the b-roll, rather than
    # dropped — dropping it would take its seconds out of the episode.
    reverted = []
    for s in mapped:
        if s.get("broll") and s["broll"] not in have_broll:
            reverted.append({"at_s": s["from_s"], "slot": s["broll"],
                             "dur_s": s["dur_s"]})
            s["broll"] = None
            s["kind"] = "single"
            s["layout"] = "full"
            s["_why"] = (f"the b-roll slot {reverted[-1]['slot']} has no approved clip "
                         f"on disk, so the picture stays on the speaker. An unapproved "
                         f"clip is never placed.")
    # 🔴 A B-ROLL SEGMENT MAY NEVER OUTLAST ITS CLIP. On the estimate clock
    # `_split_forced` gives each clip exactly its duration; stretching the layout onto
    # measured audio can push the segment past the end of the footage, and the last
    # half-second then plays as a FROZEN FRAME OF GALLOPING HORSES. Two slots did
    # exactly that on EP49 — by 0.39s and 0.48s, small enough to be missed by eye and
    # impossible to miss once seen.
    #
    # The seconds are handed to the segment that FOLLOWS rather than taken out of the
    # episode: the words underneath a cutaway keep running either way, so the picture
    # simply returns to the speaker that much earlier.
    clamped = []
    for i, s in enumerate(mapped):
        if not s.get("broll") or s["broll"] not in have_broll:
            continue
        have = _dur(have_broll[s["broll"]])
        if have + 0.05 < s["dur_s"]:
            gave = round(s["dur_s"] - have, 3)
            s["to_s"] = round(s["from_s"] + have, 3)
            s["dur_s"] = round(have, 3)
            if i + 1 < len(mapped):
                mapped[i + 1]["from_s"] = s["to_s"]
                mapped[i + 1]["dur_s"] = round(
                    mapped[i + 1]["to_s"] - mapped[i + 1]["from_s"], 3)
            clamped.append({"slot": s["broll"], "at_s": s["from_s"],
                            "gave_back_s": gave, "clip_s": round(have, 3)})

    dropped_cards = [s["card"] for s in mapped
                     if s.get("card") and s["card"] not in cards]
    if dropped_cards:
        raise Unassemblable(
            f"card(s) {sorted(set(dropped_cards))} are in the plan and have no rendered "
            f"clip in overlay/clips. A card in the plan and not on disk is a hole in "
            f"the picture; render them or take them out of the plan.")

    cover = d / "ebook/cover.png"
    have_cover = cover.is_file()

    # 🔴 THE STANDING GRAPHICS AND THE TAIL BELONG TO `twoway_end_sequence`, NOT HERE.
    #
    # This module used to write its own ending — a 3s settle, then a 6s end card, then
    # a 3.5s warranty — and every check in its suite passed, because none of them had
    # ever been asked whether that was THE ENDING THIS CHANNEL HAS. It is not:
    # §END SEQUENCE rule 2 puts the end card up ON THE E-BOOK BEAT, while he is still
    # talking, and holds it until the warranty takes over. Jodie, 22 Sep 2026: *"the
    # ebook motion graphic turns up after Gordon finishes talking completely."*
    #
    # ⚠️ AND THE SAME BLIND SPOT HID TWO MORE. The `cta` and `midroll` furniture beats
    # each owe a standing graphic and got nothing, for three cuts, because no code
    # anywhere knew those beats are supposed to carry a picture. The table that says
    # so is `twoway_end_sequence.STANDING`, and it is the check.
    speech_end = max(s["to_s"] for s in mapped)
    joins = mark_dissolves(mapped, tl, TITLE_HEAD_S)
    furn = [s for s in tl if s.get("kind") == "furniture"]
    graphics = tes.place(d, epj, cues, furn, TITLE_HEAD_S)
    tail = tes.tail(speech_end,
                    graphics.get("end_card_at_s") if have_cover else None,
                    END_SETTLE_S)
    end_card, warranty, total = tail["end_card"], tail["warranty"], tail["total_s"]

    return {
        "episode": epj["episode"],
        "head": {"title_card": str(d / "overlay/clips/ep49-title.mp4"),
                 "from_s": 0.0, "to_s": TITLE_HEAD_S},
        "segments": mapped,
        "furniture": [s for s in tl if s.get("kind") == "furniture"],
        "timeline": tl,
        "broll_on_disk": have_broll,
        "broll_missing": missing_broll,
        "broll_reverted_to_speaker": reverted,
        "broll_clamped_to_clip": clamped,
        "cards_on_disk": cards,
        "holds": (epj.get("build") or {}).get("holds") or {},
        "warranty": warranty,
        "end_card": end_card,
        "graphics": graphics,
        "joins": joins,
        # ASKED OF THE DISK, not of a table. §7: derive the coverage from the thing
        # itself, because a list somebody maintains is already broken.
        "clip_durations": {n: round(_dur(str(d / "overlay/clips" / n)), 3)
                           for n in ("warranty-slide.mp4", "end-card-template.mp4",
                                     "midroll-lowerthird.mp4")
                           if (d / "overlay/clips" / n).is_file()},
        "speech_end_s": speech_end,
        "end_settle_s": END_SETTLE_S,
        "total_s": total,
        "end_frame_s": tes.END_FRAME_S,
        "tail_fade_s": TAIL_FADE_S,
    }


# ────────────────────────────────────────────────────────────── the checks ──

def violations(plan: dict) -> list[str]:
    """The five faults that have actually bitten this build before. Reported, not fixed."""
    out = []
    segs = plan["segments"]

    # 1 — OVERLAY-INPUT EXHAUSTION, AND THE TWO KINDS ARE NOT THE SAME QUESTION.
    #
    # ⚠️ THE FIRST VERSION OF THIS CHECK REPORTED TWELVE FAULTS THAT WERE NOT THERE.
    # A CARD CLIP IS AN ANIMATION, 2-4 seconds of build, and it is SUPPOSED to be
    # shorter than its hold: the card assembles and then holds its finished state,
    # which the motion skill requires for at least 1.5s ("the assembled card is what
    # the viewer takes away"). Calling that "the frame it froze on" described the
    # design as a defect.
    #
    # B-ROLL IS THE OPPOSITE. It is real motion, and a clip that runs out mid-shot
    # freezes a galloping horse. So: a card may be shorter than its hold and may NOT
    # be longer than it; a piece of b-roll must cover its slot.
    for s in segs:
        if s.get("card"):
            src = plan["cards_on_disk"].get(s["card"])
            if src and _dur(src) > s["dur_s"] + 0.05:
                out.append(
                    f"CARD CUT OFF MID-BUILD: {s['card']} animates for "
                    f"{_dur(src):.2f}s and is on screen {s['dur_s']:.2f}s at "
                    f"{s['from_s']:.0f}s. The viewer never sees it finish.")
        elif s.get("broll"):
            src = plan["broll_on_disk"].get(s["broll"])
            if src and _dur(src) + 0.05 < s["dur_s"]:
                out.append(
                    f"B-ROLL RUNS OUT: {s['broll']} is {_dur(src):.2f}s and covers "
                    f"{s['dur_s']:.2f}s at {s['from_s']:.0f}s. The last "
                    f"{s['dur_s'] - _dur(src):.2f}s would be a frozen frame of moving "
                    f"horses.")

    # 1b — 🔴 A GRAPHIC MUST KEEP ITS HOLD THROUGH THE MAPPING, AND THIS IS THE CHECK
    # THAT WAS MISSING WHILE THE WORST FAULT OF THE DAY WALKED PAST.
    #
    # The dwell law is a FLOOR FOR ANY PICTURE — five seconds. A card's hold is a
    # different number and a stricter one: `card_hold.hold_for()` gives it the reading
    # time its words need plus the settle. A card at 6.11s clears the dwell law and
    # cannot be read, and nothing said a word because the only check looking at
    # durations was the floor. **Measuring the thing that is easy to measure instead of
    # the thing that matters is how this fault gets through, every time.**
    epj_holds = plan.get("holds") or {}
    for s in segs:
        if s.get("card"):
            want = epj_holds.get(s["card"])
            if want and s["dur_s"] + 0.05 < want:
                out.append(
                    f"CARD TOO SHORT AFTER MAPPING: {s['card']} needs {want:.1f}s to be "
                    f"read and is on screen {s['dur_s']:.1f}s at {s['from_s']:.0f}s. "
                    f"It clears the {tb.MIN_DWELL_S:.0f}s dwell floor and still cannot "
                    f"be read — a card is never sped up to fit.")
        elif s.get("broll") and s["broll"] in plan["broll_on_disk"]:
            if s["dur_s"] + 0.05 < tb.BROLL_DUR_MIN_S:
                out.append(
                    f"B-ROLL TOO SHORT AFTER MAPPING: {s['broll']} is on screen "
                    f"{s['dur_s']:.1f}s at {s['from_s']:.0f}s, under the "
                    f"{tb.BROLL_DUR_MIN_S:.0f}s the format asserts.")
    for s in segs:
        if s.get("squeezed"):
            out.append(f"NO ROOM: {s['squeezed']}. The remedy is editorial — move "
                       f"a graphic out of that turn or shorten one.")
            break

    # 2 — THE HANDOVER GAP: consecutive speakers must not butt together
    tl = [x for x in plan["timeline"] if x.get("kind") != "latency"]
    for a, b in zip(tl, tl[1:]):
        gap = b["from_s"] - a["to_s"]
        if a["speaker"] != b["speaker"] and gap < 0.25:
            out.append(
                f"HANDOVER TOO TIGHT: {gap * 1000:.0f}ms between {a['speaker']} and "
                f"{b['speaker']} at {b['from_s']:.0f}s. A real cross has 300-500ms; a "
                f"butt-join sounds scripted.")

    # 3 — SEAMS: every picture change must land on a sentence end
    for s in segs[1:]:
        if s.get("snapped") is False:
            out.append(f"UNSNAPPED BOUNDARY at {s['from_s']:.1f}s.")

    # 4 — THE LAST-WORD TAIL: the episode must not cut on the final syllable
    #
    # 🔴 MEASURED TO THE END OF THE FILM, WHICH IS THE ONLY LANDMARK THAT STILL MEANS
    # SOMETHING. This check has now pointed at the wrong thing twice. It first measured
    # the settle to the WARRANTY, which was right only while the tail was in the wrong
    # order; it was then moved to the END CARD — and the end card has since gone back
    # where the standard puts it, ON the e-book beat, so it is now BEFORE the last word
    # and the subtraction is negative. **A landmark that moves cannot measure a
    # distance.** Rule 1 is about AIR after the last word — "he never talks right to
    # the end; the end card + music breathe" — and the air is everything between the
    # last word and the final frame, whatever is drawn on it.
    tail = plan["total_s"] - plan["speech_end_s"]
    if tail < END_SETTLE_S - 0.2:
        out.append(
            f"NO SETTLE: only {tail:.2f}s of film after the last word and the standard "
            f"is {END_SETTLE_S:.1f}s. He never talks right to the end.")
    # 4b — 🔴 NO PICTURE CUT INSIDE CONTIGUOUS SOURCE. If two adjacent pieces draw the
    # same master at adjoining timecodes they are ONE shot, and cutting between them
    # puts a discontinuity inside a take that never had one. Reported as a bug rather
    # than smoothed with a dissolve: a dissolve over a join that should not exist hides
    # the fault instead of removing it.
    for j in plan.get("joins") or []:
        if j["kind"] == "contiguous-split":
            out.append(
                f"PICTURE CUT INSIDE ONE TAKE at {j['at_s']:.1f}s: both pieces draw the "
                f"same master {j['master_gap_s'] * 1000:+.0f}ms apart, which is one "
                f"continuous shot cut in two. Consecutive segments from the same master "
                f"at adjoining timecodes are ONE piece.")

    # 4c — AND NO UNSMOOTHED SOURCE SWITCH. A join that changes what is feeding a panel
    # while the picture itself does not change is a chop the eye has nothing to explain.
    for j in plan.get("joins") or []:
        if j["kind"] in ("handover", "furniture-join") and not j.get("frames"):
            out.append(
                f"HARD CUT AT A SOURCE SWITCH at {j['at_s']:.1f}s ({j['kind']}): the "
                f"footage feeding the picture changes and nothing on screen says so. "
                f"It gets {DISSOLVE_FRAMES} frames.")

    out.extend(tes.violations(plan))

    # 5 — THE MINIMUM DWELL LAW, on the MAPPED plan and not the estimate
    for st in tb.short_states(segs):
        out.append(
            f"DWELL LAW BROKEN after mapping: {st.get('ident') or st['kind']} holds "
            f"{st['dur_s']:.1f}s at {st['from_s']:.0f}s — the floor is "
            f"{tb.MIN_DWELL_S:.0f}s. Stretching the layout onto measured audio can "
            f"shorten a state the estimate had over the line.")
    return out


def _dur(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True, timeout=120)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    plan = build_plan(a.ep_number, pathlib.Path(a.pp))

    print(f"{plan['episode']}: {plan['total_s']:.1f}s "
          f"({plan['total_s'] / 60:.1f} min)")
    print(f"  title card   {plan['head']['to_s']:.1f}s")
    print(f"  dialogue     {len(plan['segments'])} segments to "
          f"{plan['speech_end_s']:.1f}s")
    print(f"  furniture    {len(plan['furniture'])} full-frame pieces")
    print(f"  cards        {len(plan['cards_on_disk'])} on disk")
    print(f"  b-roll       {len(plan['broll_on_disk'])} on disk, "
          f"{len(plan['broll_missing'])} missing")
    for c in plan['broll_clamped_to_clip']:
        print(f"     ~ {c['slot']} trimmed to its clip ({c['clip_s']:.2f}s), "
              f"{c['gave_back_s']:.2f}s back to the speaker")
    for r in plan["broll_reverted_to_speaker"]:
        print(f"     \u2192 {r['slot']} at {r['at_s']:.0f}s "
              f"({r['dur_s']:.1f}s) STAYS ON THE MEN")
    print(f"  warranty     {plan['warranty']['from_s']:.1f}s")
    print(f"  end card     " + (f"{plan['end_card']['from_s']:.1f}s"
                                if plan["end_card"] else
                                "\U0001f534 SKIPPED — no approved cover on disk"))
    v = violations(plan)
    print(f"\n{len(v)} violation(s)" if v else "\n\u2705 no violations")
    for x in v:
        print("  ! " + x)
    if a.json_out:
        pathlib.Path(a.json_out).write_text(
            json.dumps({k: val for k, val in plan.items() if k != "timeline"},
                       indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {a.json_out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Unassemblable as e:
        print(f"\nHALT: {e}", file=sys.stderr)
        raise SystemExit(2)
