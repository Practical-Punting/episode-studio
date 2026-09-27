#!/usr/bin/env python3
"""test_twoway_assemble.py — the five faults that have actually bitten this build.

    python engine/test_twoway_assemble.py

Jodie, 20 Sep 2026: *"Tests first for the pieces that bit before: overlay-input
exhaustion, handover gap, seams, last-word tail, minimum dwell."*

🔴 EVERY CASE HAS A CONTROL THAT FAILS. A checker only ever seen to print PASS is
indistinguishable from one hard-wired to (Jodie, 30 Aug) — and three of these five
checks were WRONG on their first run against the real episode, in both directions:

  · overlay exhaustion reported TWELVE faults that were not there, because a card clip
    is an animation and is SUPPOSED to be shorter than its hold;
  · the dwell check reported four states at 0.0s, which were real — the snap had
    collapsed them — and would have shipped as cards nobody sees;
  · the b-roll clamp found two slots running 0.39s and 0.48s past their footage.

So the controls here are not ceremony. They are the difference between a check and a
decoration.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import twoway_assemble as ta                                      # noqa: E402
import twoway_beats as tb                                         # noqa: E402
import twoway_interleave as ti                                    # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR",
                                 str(pathlib.Path("G:/My Drive") / "PP Videos")))
EP_DIR = PP / "PP-EP49-Fighting-a-Complex-Game-Part-1"
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"  — {why}" if why and not cond else ""))


def seg(n, a, b, **kw):
    d = {"n": n, "from_s": a, "to_s": b, "dur_s": round(b - a, 3), "turn": 1,
         "speaker": "BB", "listener": "BM", "layout": "full", "kind": "single",
         "card": None, "broll": None, "beats": [n], "_why": ""}
    d.update(kw)
    return d


# ═══ the real plan, built once ═══════════════════════════════════════════════
plan = ta.build_plan(49, PP)
segs = plan["segments"]
print(f"\nEP49 plan: {plan['total_s']:.1f}s, {len(segs)} segments, "
      f"{len(plan['cards_on_disk'])} cards, {len(plan['broll_on_disk'])} b-roll\n")


# ═══ 1. overlay-input exhaustion ═════════════════════════════════════════════
print("-- 1. an overlay that runs out before its segment does --")

check("the real plan has no b-roll running past its clip",
      not [v for v in ta.violations(plan) if "B-ROLL RUNS OUT" in v],
      "; ".join(v for v in ta.violations(plan) if "B-ROLL RUNS OUT" in v))

# CONTROL — stretch a b-roll segment past its footage and it must be REPORTED
if plan["broll_on_disk"]:
    bad = json.loads(json.dumps(plan))
    tgt = next((s for s in bad["segments"] if s.get("broll")
                and s["broll"] in bad["broll_on_disk"]), None)
    if tgt:
        tgt["dur_s"] = round(tgt["dur_s"] + 30.0, 3)
        tgt["to_s"] = round(tgt["from_s"] + tgt["dur_s"], 3)
        check("CONTROL: b-roll stretched 30s past its clip IS reported",
              any("B-ROLL RUNS OUT" in v for v in ta.violations(bad)),
              "; ".join(ta.violations(bad))[:160])

# CONTROL — a CARD shorter than its hold is NOT a fault; longer than it IS
if plan["cards_on_disk"]:
    ok = json.loads(json.dumps(plan))
    c = next(s for s in ok["segments"] if s.get("card"))
    c["dur_s"], c["to_s"] = 30.0, c["from_s"] + 30.0
    check("a card held far longer than its animation is NOT a fault — it holds its "
          "finished state, which is the design",
          not any("CARD CUT OFF" in v for v in ta.violations(ok)))
    short = json.loads(json.dumps(plan))
    c2 = next(s for s in short["segments"] if s.get("card"))
    c2["dur_s"], c2["to_s"] = 0.4, c2["from_s"] + 0.4
    check("CONTROL: a card cut off mid-build IS reported",
          any("CARD CUT OFF" in v for v in ta.violations(short)),
          "; ".join(ta.violations(short))[:160])


# ═══ 2. the handover gap ═════════════════════════════════════════════════════
print("\n-- 2. the gap between one man and the next --")

tl = [x for x in plan["timeline"] if x.get("kind") != "latency"]
gaps = [round(b["from_s"] - a["to_s"], 3) for a, b in zip(tl, tl[1:])
        if a["speaker"] != b["speaker"]]
check("every handover has a latency beat in it",
      all(g >= 0.25 for g in gaps),
      f"min {min(gaps) if gaps else 0:.3f}s")
check("and the beats are not all the same length — identical gaps are the tell",
      len(set(gaps)) > 1, str(sorted(set(gaps))))
check("the real plan reports no tight handover",
      not [v for v in ta.violations(plan) if "HANDOVER TOO TIGHT" in v])

# CONTROL — butt two speakers together and it must be reported
bad = json.loads(json.dumps(plan))
btl = [x for x in bad["timeline"] if x.get("kind") != "latency"]
for a, b in zip(btl, btl[1:]):
    if a["speaker"] != b["speaker"]:
        b["from_s"] = a["to_s"]
        break
check("CONTROL: a butt-join between two speakers IS reported",
      any("HANDOVER TOO TIGHT" in v for v in ta.violations(bad)))


# ═══ 3. the seams — every picture change on a sentence end ═══════════════════
print("\n-- 3. the seams --")

cues = ti.read_srt((EP_DIR / "renders/merged.srt").read_text(encoding="utf-8"))
ends = set(round(e, 2) for e in ti.sentence_ends(cues))
# 🔴 COUNT THE BOUNDARIES THAT CAN MOVE, NOT ALL OF THEM. A10 rule 4a asks layout
# changes to land on sentence ends, and most of this episode's boundaries are not free
# to:
#   · a TURN START is where the timeline says the man starts speaking;
#   · a GRAPHIC'S END is its start plus its reading time — moving it would shorten the
#     card, which is the fault this suite exists to stop.
# What is free is a graphic's START and a boundary between two conversational shots.
#
# ⚠️ THE FIRST VERSION OF THIS TEST ASKED FOR 50% OF EVERYTHING and failed at 14/57 —
# a threshold written against the old behaviour, where every boundary snapped and
# collapsed segments doing it. A percentage of the wrong denominator is not a rule.
turn_starts = {round(s["turn_span"][0], 2) for s in segs}
free = []
for i, s in enumerate(segs):
    if round(s["from_s"], 2) in turn_starts or s["from_s"] <= ta.TITLE_HEAD_S + 0.01:
        continue
    prev = segs[i - 1] if i else None
    if prev is not None and prev.get("held") and not s.get("held"):
        continue                      # this boundary IS a graphic's end
    free.append(s)
# A free boundary that did NOT snap must have had nowhere to go. That is the
# rule as `twoway_interleave.snap_plan` states it — *"a boundary with no
# sentence end within reach stays put and says so"* — and it is the assertion
# worth making, because tuning a percentage until it passes proves nothing
# about the episode and everything about the percentage.
sorted_ends = sorted(ends)
unsnapped = []
for s in free:
    if round(s["from_s"] - ta.TITLE_HEAD_S, 2) in ends:
        continue
    # ⚠️ "IN REACH" MUST MEAN WHAT THE CODE MEANS BY IT, OR THE TEST IS ASKING A
    # DIFFERENT QUESTION. The first version measured reach against the whole TURN, which
    # is far wider than the real constraint: a boundary may only move as far as its two
    # NEIGHBOURING shots can give, each of which must keep the dwell floor. Measured the
    # loose way, one boundary looked like a miss with "8 ends in reach" when every one
    # of them would have pushed a neighbour under five seconds.
    i = segs.index(s)
    prev = segs[i - 1]
    lo = prev["from_s"] + tb.MIN_DWELL_S - ta.TITLE_HEAD_S
    hi = s["to_s"] - tb.MIN_DWELL_S - ta.TITLE_HEAD_S
    reachable = [e for e in sorted_ends if lo <= e <= hi]
    unsnapped.append((s["from_s"], s.get("card") or s.get("broll") or s["kind"],
                      len(reachable)))
on_end = len(free) - len(unsnapped)
check("every layout change that CAN land on a sentence end does",
      all(n == 0 for _, _, n in unsnapped),
      f"{on_end}/{len(free)} snapped; "
      + "; ".join(f"{t:.0f}s {w} had {n} end(s) in reach"
                  for t, w, n in unsnapped if n)[:200])
print(f"         ({on_end}/{len(free)} free boundaries on a sentence end, "
      f"{len(segs)} segments in all)")
# ⚖️ A GRAPHIC MAY BE LONGER THAN ITS HOLD, NEVER SHORTER. That is Jodie's rule in
# terms — *"a card MAY RUN PAST its sentence to finish reading time + 1.5s settle;
# never speed a card"* — and asserting exact equality was stricter than the rule.
# Absorbing a 0.3–0.5s latency beat into a card lengthens it, which is fine; the
# thing that must never happen is a second coming OFF.
held = [s for s in segs if s.get("held") and (s.get("card") or s.get("broll"))]
short = [(s.get("card") or s.get("broll"),
          round(s["est_to_s"] - s["est_from_s"], 2), s["dur_s"])
         for s in held
         if s["dur_s"] < round(s["est_to_s"] - s["est_from_s"], 3) - 0.06]
check("no graphic is ever SHORTER than its hold",
      not short, "; ".join(f"{n} {e}->{d}" for n, e, d in short))
over = [s for s in held
        if s["dur_s"] > round(s["est_to_s"] - s["est_from_s"], 3) + 1.01]
check("and none is stretched by more than a latency beat",
      not over,
      "; ".join(f"{s.get('card') or s.get('broll')} "
                f"+{s['dur_s'] - round(s['est_to_s'] - s['est_from_s'], 3):.2f}s"
                for s in over))
check("no segment has zero or negative length",
      all(s["dur_s"] > 0.001 for s in segs),
      str([s["n"] for s in segs if s["dur_s"] <= 0.001][:6]))
check("the segments are contiguous — no hole, no overlap",
      all(abs(a["to_s"] - b["from_s"]) < 0.002 for a, b in zip(segs, segs[1:])))

# CONTROL — the monotonic snap: two boundaries may not take the same sentence end
tlj = json.loads((EP_DIR / "renders/master-timeline.json").read_text(encoding="utf-8"))
epj = json.loads((EP_DIR / "docs/episode.json").read_text(encoding="utf-8"))
remapped = ta.map_layout(epj["layout_plan"], tlj["timeline"], cues, ta.TITLE_HEAD_S)
zero = [s for s in remapped if s["dur_s"] <= 0.001]
check("CONTROL: re-mapping from scratch still collapses nothing to zero",
      not zero, f"{len(zero)} collapsed")


# ═══ 4. the last-word tail, AND THE ORDER OF THE END SEQUENCE ════════════════
print("\n-- 4. air after the last word, and what comes last --")

# 🔴 THE END CARD COMES FIRST AND THE WARRANTY SLIDE COMES LAST. PP-STANDARDS
# §END SEQUENCE rule 2, locked 25 Jul 2026, in terms: the end card "fades in on the
# e-book beat and STAYS UP UNTIL THE WARRANTY TAKES OVER". Nothing follows the warranty
# slide, because the responsible-gambling line lives there and it is the last thing the
# viewer is left with.
#
# ⚠️ THIS TEST WAS WRITTEN TO FAIL. `twoway_assemble` had the two the wrong way round —
# warranty at 798.3s, end card at 801.8s — and every other check passed, because no
# check had ever been asked what ORDER the tail is in. Jodie caught it by reading
# assembly-plan.json.
if plan["end_card"]:
    check("the END CARD comes before the warranty slide",
          plan["end_card"]["from_s"] < plan["warranty"]["from_s"],
          f"end card {plan['end_card']['from_s']:.1f}s, "
          f"warranty {plan['warranty']['from_s']:.1f}s")
    check("and the warranty slide is the LAST thing on screen",
          plan["warranty"]["from_s"] + plan["warranty"]["dur_s"]
          >= plan["total_s"] - 0.01,
          f"warranty ends {plan['warranty']['from_s'] + plan['warranty']['dur_s']:.1f}s "
          f"of {plan['total_s']:.1f}s")
    # 🔴 "STAYS UP UNTIL THE WARRANTY TAKES OVER" IS A FLOOR, NOT AN EQUALITY.
    # This asserted the two met to within 10ms, which was true only while the end card
    # was a PIECE laid end to end with the warranty. It is now an OVERLAY that goes up
    # on the e-book beat and runs 0.6s PAST the warranty's entrance, so the two slides
    # cross rather than one leaving a hole — `assemble_episode`'s own arithmetic, and
    # measured on EP48 as a dip at 772.5-773.5s. An equality where the standard says
    # "until" turns a floor into a tightrope.
    check("the end card stays up until the warranty takes over — no gap",
          plan["end_card"]["from_s"] + plan["end_card"]["dur_s"]
          >= plan["warranty"]["from_s"] - 0.01,
          f"card out {plan['end_card']['from_s'] + plan['end_card']['dur_s']:.2f}s, "
          f"warranty in {plan['warranty']['from_s']:.2f}s")
    check("and it is ON SCREEN while he speaks the e-book line (rule 2)",
          plan["end_card"]["from_s"] < plan["speech_end_s"],
          f"card {plan['end_card']['from_s']:.2f}s, "
          f"last word {plan['speech_end_s']:.2f}s")
else:
    check("with no approved cover the end card is skipped and the warranty is last",
          plan["warranty"]["from_s"] + plan["warranty"]["dur_s"]
          >= plan["total_s"] - 0.01,
          f"total {plan['total_s']:.1f}s, warranty ends "
          f"{plan['warranty']['from_s'] + plan['warranty']['dur_s']:.1f}s")

# §END SEQUENCE rule 1: ~3s of settle, not half a second.
#
# 🔴 MEASURED TO THE END OF THE FILM, WHICH IS THE ONLY LANDMARK THAT STOPPED MOVING.
# This check has pointed at the wrong thing twice. It measured to the WARRANTY, which
# was right only while the tail was in the wrong order; it was then moved to the END
# CARD — and the end card has since gone back where the standard puts it, ON the
# e-book beat, so it now sits BEFORE the last word and the subtraction went to -19.48s.
# Rule 1 is about AIR after the last word — "he never talks right to the end; the end
# card + music breathe" — and the air is everything between the last word and the final
# frame, whatever happens to be drawn on it. **A landmark that moves cannot measure a
# distance.**
settle = plan["total_s"] - plan["speech_end_s"]
check("Gordon's last word lands about 3s before the film ends (end_settle)",
      settle >= ta.END_SETTLE_S - 0.2,
      f"{settle:.2f}s of film after the last word, "
      f"the standard is {ta.END_SETTLE_S:.1f}s")
check("the real plan reports no missing tail",
      not [v for v in ta.violations(plan) if "NO SETTLE" in v])

bad = json.loads(json.dumps(plan))
bad["total_s"] = bad["speech_end_s"] + 0.05
bad["warranty"] = {"from_s": bad["speech_end_s"], "dur_s": 0.05}
check("CONTROL: cutting 50ms after the last word IS reported as no settle",
      any("NO SETTLE" in v for v in ta.violations(bad)))


# ═══ 5. the minimum dwell law, ON THE MAPPED PLAN ════════════════════════════
print("\n-- 5. the dwell law, after the layout has been stretched --")

states = tb.picture_states(segs)
shortest = min(s["dur_s"] for s in states)
check(f"nothing on screen under {tb.MIN_DWELL_S:.0f}s after mapping",
      shortest >= tb.MIN_DWELL_S - 0.001, f"shortest {shortest:.2f}s")
check("the real plan reports no dwell breach",
      not [v for v in ta.violations(plan) if "DWELL LAW" in v],
      "; ".join(v for v in ta.violations(plan) if "DWELL LAW" in v)[:200])

# ⚠️ THE FIXTURE HAS TO ATTACK THE THING THE CHECK MEASURES, AND THE FIRST ONE DID
# NOT. `picture_states` merges CONTIGUOUS segments showing the same picture, so
# shortening a two-box segment whose neighbour is also a two-box shortens no STATE at
# all — the control failed while the code was right. A CARD is its own state by
# construction: the pictures either side of it are different, so squeezing one is the
# only way to squeeze a state.
bad = json.loads(json.dumps(plan))
i = next(k for k, s in enumerate(bad["segments"]) if s.get("card"))
s0 = bad["segments"][i]
s0["to_s"] = round(s0["from_s"] + 1.0, 3)
s0["dur_s"] = 1.0
bad["segments"][i + 1]["from_s"] = s0["to_s"]
bad["segments"][i + 1]["dur_s"] = round(
    bad["segments"][i + 1]["to_s"] - s0["to_s"], 3)
check("the fixture really does squeeze a state, not just a segment",
      min(x["dur_s"] for x in tb.picture_states(bad["segments"])) < 2.0,
      f"shortest state {min(x['dur_s'] for x in tb.picture_states(bad['segments'])):.2f}s")
check("CONTROL: a one-second shot IS reported",
      any("DWELL LAW" in v for v in ta.violations(bad)),
      "; ".join(ta.violations(bad))[:160])


# ═══ 5b. the furniture is IN the picture timeline ════════════════════════════
print("\n-- 5b. the furniture has its own place on screen --")

# 🔴 THE FAULT THIS EXISTS FOR, AND IT WAS FOUND WITH THE RENDERER ALREADY WRITTEN.
# The mapped dialogue came out exactly contiguous — 756.3s of segments over 756.3s of
# clock — and that clock contains 34 seconds of Gordon's e-book CTA and midroll. The
# contiguity pass had stretched the last shot of each turn straight over them. **The
# CTA and the midroll would have played under the wrong picture, at the wrong length,
# and the plan looked perfect** because "no holes" was the only thing being asked.
furn = [s for s in segs if s.get("kind") == "furniture"]
tlj2 = json.loads((EP_DIR / "renders/master-timeline.json").read_text(encoding="utf-8"))
tl_furn = [s for s in tlj2["timeline"] if s.get("kind") == "furniture"]
check("every furniture piece is on screen, in the picture timeline",
      len(furn) == len(tl_furn), f"{len(furn)} of {len(tl_furn)}")
check("each one keeps the seconds the render gives it",
      all(abs(f["dur_s"] - t["dur_s"]) < 1.01
          for f, t in zip(sorted(furn, key=lambda x: x["from_s"]),
                          sorted(tl_furn, key=lambda x: x["from_s"]))),
      str([(round(f['dur_s'], 2), round(t['dur_s'], 2))
           for f, t in zip(sorted(furn, key=lambda x: x["from_s"]),
                           sorted(tl_furn, key=lambda x: x["from_s"]))
           if abs(f['dur_s'] - t['dur_s']) >= 1.01]))
check("and every one is FULL FRAME — there is no conversation in it",
      all(f["layout"] == "full" for f in furn))
check("no dialogue segment overlaps a furniture piece",
      not [(a["seq"], b["seq"]) for a, b in zip(segs, segs[1:])
           if a["to_s"] > b["from_s"] + 0.002])
check("the picture timeline covers the speech end to end, with no black",
      abs(sum(s["dur_s"] for s in segs)
          - (segs[-1]["to_s"] - segs[0]["from_s"])) < 0.05,
      f"sum {sum(s['dur_s'] for s in segs):.2f}s over a span of "
      f"{segs[-1]['to_s'] - segs[0]['from_s']:.2f}s")


# ═══ 6. what it refuses to do ════════════════════════════════════════════════
print("\n-- 6. the refusals --")

check("an unapproved b-roll slot stays on the men, and says so",
      all(r["slot"] not in plan["broll_on_disk"]
          for r in plan["broll_reverted_to_speaker"]),
      str([r["slot"] for r in plan["broll_reverted_to_speaker"]]))
check("no reverted slot still carries a clip",
      not [s for s in segs if s.get("broll")
           and s["broll"] not in plan["broll_on_disk"]])
check("the end card is SKIPPED while there is no approved cover",
      (plan["end_card"] is None) == (not (EP_DIR / "ebook/cover.png").is_file()),
      f"end_card={plan['end_card']}, "
      f"cover on disk={(EP_DIR / 'ebook/cover.png').is_file()}")

# ═══ 7. a graphic keeps its hold through the mapping ═════════════════════════
print("\n-- 7. a graphic's duration is a HOLD, not a proportion --")

# 🔴 THE FAULT THIS SECTION EXISTS FOR. The first mapping scaled every segment by the
# same factor, so a card planned at 10.5s came out at 6.11s and a 9.8s clip at 5.93s —
# and every check passed, because the only duration test was the 5s dwell FLOOR. A card
# under its reading time cannot be read; that is a different number and a stricter one.
drift = [(s.get("card") or s.get("broll"),
          round(s["est_to_s"] - s["est_from_s"], 3), s["dur_s"])
         for s in segs if s.get("card") or s.get("broll")]
check("every graphic is on screen for exactly the seconds it was planned",
      all(abs(d - e) < 0.06 for _, e, d in drift),
      "; ".join(f"{n} {e}->{d}" for n, e, d in drift if abs(d - e) >= 0.06)[:200])
check("no card is under its reading time",
      not [v for v in ta.violations(plan) if "CARD TOO SHORT" in v],
      "; ".join(v for v in ta.violations(plan) if "CARD TOO SHORT" in v)[:200])
check("no b-roll is under the format's floor",
      not [v for v in ta.violations(plan) if "B-ROLL TOO SHORT" in v])

# CONTROL — squeeze a card below its hold and it must be REPORTED, even though it
# still clears the dwell floor. That gap is exactly where the fault lived.
bad = json.loads(json.dumps(plan))
cid = next(s["card"] for s in bad["segments"] if s.get("card")
           and bad["holds"].get(s["card"], 0) > 7.0)
for s in bad["segments"]:
    if s.get("card") == cid:
        s["dur_s"] = 6.0
        s["to_s"] = round(s["from_s"] + 6.0, 3)
vs = ta.violations(bad)
check(f"CONTROL: {cid} squeezed to 6.0s IS reported as unreadable",
      any("CARD TOO SHORT" in v for v in vs),
      "; ".join(vs)[:160])
check("CONTROL: and 6.0s clears the dwell floor, which is why the floor never "
      "caught it", 6.0 > tb.MIN_DWELL_S)

# CONTROL — the repair may never take seconds from a graphic
repaired = [s for s in segs if s.get("repaired")]
check("any repaired shot is a conversational one, never a graphic",
      all(not (s.get("card") or s.get("broll")) for s in repaired),
      f"{len(repaired)} repaired")

print(f"\ntwo-way assemble: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
