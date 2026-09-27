#!/usr/bin/env python3
"""The eight faults Jodie stopped the 20 Sep cut for, as checks.

    python engine/test_twoway_end_sequence.py [<ep_number>] [<finished.mp4>]

🔴 EVERY CHECK HERE WAS WATCHED FAILING ON THE BUILD SHE REJECTED. Each one carries a
CONTROL built from that build's own shape — not a synthetic fixture — so a check that
passes for the wrong reason has somewhere to be caught.

What they cover, and which of her eight faults each one answers:

  1 · a furniture beat that has a standing graphic MUST get it          (faults 1, 4)
  2 · every picture state of one man carries the SAME grade             (fault 2)
  3 · no source switch is a hard cut                                    (faults 3, 6)
  4 · no picture cut inside contiguous source                           (fault 6, ruled out)
  5 · the end card is on screen while the e-book line is spoken         (fault 5)
  6 · a standing clip's hold comes from the clip                        (fault 7)
  7 · there is room at the end for YouTube's end screen                 (fault 8)

⚠️ CHECK 7 IS THE ONLY ONE THAT MUST READ THE FINISHED FILE, and that is not a detail.
The PLAN says an 18s end frame is intended; the plan is what asked for it. Asking the
plan whether the end frame is there is asking a thing to confirm itself — the same
mistake as the audio checker that shared its seek with the code it was judging and
reported +0.00ms on ten spans that were wrong. So the end frame is measured in PIXELS,
at the last frame of the mp4, or not at all.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import twoway_assemble as ta                                      # noqa: E402
import twoway_composite as tc                                     # noqa: E402
import twoway_end_sequence as tes                                 # noqa: E402

PASS, FAIL, NOTE = [], [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'OK  ' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    return ok


def _rejected_shape(plan: dict) -> dict:
    """The 20 Sep cut's own tail, rebuilt from the constants it used.

    settle 3.0s -> end card 6.0s -> warranty 3.5s, nothing after it, and no standing
    graphic over any furniture beat. This is the CONTROL: every check below has to
    fire on it, or it is not testing what it says it is.
    """
    # 🔴 THE TIMELINE STAYS IN THE CONTROL. `violations` reads it for the handover-gap
    # check, and a control that is missing a field the checker needs does not test the
    # checker, it crashes it — which is a pass nobody gets.
    bad = json.loads(json.dumps(plan))
    se = bad["speech_end_s"]
    bad["end_card"] = {"from_s": round(se + ta.END_SETTLE_S, 3),
                       "dur_s": ta.END_CARD_S, "fade_s": 0.3, "overlay": False}
    bad["warranty"] = {"from_s": round(se + ta.END_SETTLE_S + ta.END_CARD_S, 3),
                       "dur_s": ta.WARRANTY_S}
    bad["total_s"] = round(bad["warranty"]["from_s"] + ta.WARRANTY_S, 3)
    bad["graphics"] = {"owed": plan["graphics"]["owed"], "placed": [],
                       "ebook_line_at_s": plan["graphics"].get("ebook_line_at_s")}
    bad["end_frame_s"] = 0
    for s in bad["segments"]:
        s.pop("dissolve_in_frames", None)
    bad["joins"] = [dict(j, frames=0) for j in bad.get("joins", [])]
    return bad


def main(ep=49, final=None) -> int:
    pp = pathlib.Path("G:/My Drive/PP Videos")
    plan = ta.build_plan(ep, pp)
    bad = _rejected_shape(plan)
    layout = tc.load_layout()

    # ═══ 1. A FURNITURE BEAT WITH A STANDING GRAPHIC MUST GET IT ═════════════
    # Jodie, faults 1 and 4: *"there's an actual motion graphic with the picture of the
    # ebook that comes up as well. That did not come up in this version"* and *"there's
    # normally a motion graphic that comes on the screen when he does [the like and
    # subscribe]."* Three cuts shipped without either, because nothing in the code knew
    # a furniture beat can owe a picture.
    print("\n-- 1. every furniture beat that owes a standing graphic has one --")
    g = plan["graphics"]
    check(f"  the table names what is owed ({', '.join(g['owed'])})",
          set(g["owed"]) <= set(tes.STANDING), f"{g['owed']}")
    check("  every owed graphic is placed",
          set(g["owed"]) == set(g["placed"]),
          f"owed {g['owed']}, placed {g['placed']}")
    for key, role in (("early_cta", "cta"), ("midroll", "midroll")):
        if role not in g["owed"]:
            continue
        spec = g[key]
        lo, hi = spec["beat"]
        check(f"  the {role} graphic sits INSIDE its own beat",
              lo - 0.01 <= spec["at_s"] and spec["at_s"] + spec["dur_s"] <= hi + 0.01,
              f"{spec['at_s']:.2f}-{spec['at_s'] + spec['dur_s']:.2f}s "
              f"in {lo:.2f}-{hi:.2f}s")
        check(f"  ...and FOLLOWS the words, never precedes them",
              spec["at_s"] >= spec["spoken_at_s"] - 0.01,
              f"graphic {spec['at_s']:.2f}s, spoken {spec['spoken_at_s']:.2f}s")
    if g.get("midroll"):
        full = g["midroll"]["dur_s"] - 2 * g["midroll"]["fade_s"]
        check(f"  the chip is fully visible for at least 6s (§4E)",
              full >= 6.0, f"{full:.2f}s")
    check("CONTROL: the rejected cut IS reported as missing its graphics",
          len([v for v in tes.violations(bad) if "STANDING GRAPHIC MISSING" in v])
          == len(g["owed"]),
          f"{len([v for v in tes.violations(bad) if 'STANDING GRAPHIC' in v])} of "
          f"{len(g['owed'])}")

    # ═══ 2. EVERY PICTURE STATE OF ONE MAN CARRIES THE SAME GRADE ════════════
    # Jodie, fault 2: *"The lighting in the Barry Meadow videos changes. It's not the
    # contrast between Gordon and Steve, it's the contrast between STEVE's scenes."*
    #
    # 📏 The grade lived inside `composite_graph`, so the two-box got it and every
    # full-frame shot went out raw. Same master frame down both paths: Steve 149.46
    # ungraded / 143.59 graded (3.9% apart), Gordon 124.90 / 130.72 (4.7%). The check
    # is on the GRAPH, not on a rendered pixel, because a graph can be asserted.
    print("\n-- 2. the grade reaches every picture state, not only the two-box --")
    side_of = {"BB": "left", "BM": "right"}
    graph = tc.composite_graph(layout, side_of,
                               [{"speaker": "BB", "listener": "BM"}], {})
    for who in layout["grade"]["gamma"]:
        gam = tc.grade_of(layout, who)
        full = tc.grade_filter(layout, who)
        check(f"  {who}: the full-frame path names the same gamma as the two-box",
              full == f"eq=gamma={gam}", full)
    check("  the two-box graph still carries both gammas",
          all(f"eq=gamma={tc.grade_of(layout, w)}" in graph
              for w in ("BB", "BM")),
          "; ".join(f"{w}={tc.grade_of(layout, w)}" for w in ("BB", "BM")))
    # 🔴 THE RULE AS A RELATIONSHIP, NOT A PIXEL: the two men MEET IN THE MIDDLE.
    vals = [float(v) for v in layout["grade"]["gamma"].values()]
    check("  one presenter is trimmed and one is lifted — neither is re-lit",
          min(vals) < 1.0 < max(vals), f"{layout['grade']['gamma']}")
    check("CONTROL: an ungraded full-frame path IS a different filter",
          tc.grade_filter(layout, "BM") != "eq=gamma=1.0",
          tc.grade_filter(layout, "BM"))

    # ═══ 3. NO SOURCE SWITCH IS A HARD CUT ═══════════════════════════════════
    # Jodie, fault 3: *"There is a bit of jumping from when he's just listening to when
    # he's speaking. How do we smooth that over at all?"* and fault 6: *"there was a
    # jump within that section … whereas no chop was actually needed at all."*
    print("\n-- 3. every unhideable source switch is dissolved, not cut --")
    joins = plan["joins"]
    hand = [j for j in joins if j["kind"] == "handover"]
    furn = [j for j in joins if j["kind"] == "furniture-join"]
    check(f"  {len(hand)} two-box handover(s) found", len(hand) > 0)
    check(f"  {len(furn)} join(s) inside a furniture run found", len(furn) > 0)
    check("  every one of them is dissolved",
          all(j["frames"] == ta.DISSOLVE_FRAMES for j in hand + furn),
          f"{sorted({j['frames'] for j in hand + furn})}")
    check("  and the dissolve is marked on the INCOMING piece, where it is painted",
          all(any(abs(s["from_s"] - j["at_s"]) < 0.002
                  and s.get("dissolve_in_frames") == ta.DISSOLVE_FRAMES
                  for s in plan["segments"]) for j in hand + furn))
    # 🚫 and never on a layout change — that is a push.
    changes = [(a, b) for a, b in zip(plan["segments"], plan["segments"][1:])
               if abs(a["to_s"] - b["from_s"]) < 0.002 and a["layout"] != b["layout"]]
    check(f"  no layout change is dissolved ({len(changes)} of them)",
          not any(b.get("dissolve_in_frames") for _a, b in changes))
    check("CONTROL: the rejected cut IS reported as hard-cutting every switch",
          len([v for v in ta.violations(bad) if "HARD CUT AT A SOURCE SWITCH" in v])
          == len(hand) + len(furn),
          f"{len([v for v in ta.violations(bad) if 'HARD CUT' in v])} reported")

    # ═══ 4. NO PICTURE CUT INSIDE CONTIGUOUS SOURCE ══════════════════════════
    # ⚠️ THIS IS THE HYPOTHESIS THAT TURNED OUT TO BE WRONG, KEPT AS A CHECK.
    # The four furniture pieces DO come from one master — and not at adjoining
    # timecodes: 5.94s, 5.93s and 5.80s of six-second SSML break sit between them, and
    # the finished clock leaves 0.45s, 0.38s and 0.50s. So the picture must skip ~5.5s
    # at each join and ZERO cuts is not reachable. The rule is still right; it is just
    # not what was wrong. A check written for a wrong guess is worth keeping and worth
    # labelling.
    print("\n-- 4. no piece of contiguous source is cut in two --")
    split = [j for j in joins if j["kind"] == "contiguous-split"]
    check("  no adjacent pair draws the same master at adjoining timecodes",
          not split, f"{len(split)} found")
    for j in furn:
        NOTE.append(f"furniture join at {j['at_s']:.1f}s skips "
                    f"{j['master_gap_s']:.2f}s of master — a real discontinuity, "
                    f"dissolved, not removable")
    fake = json.loads(json.dumps(bad))
    fake["joins"] = [{"at_s": 100.0, "kind": "contiguous-split",
                      "master_gap_s": 0.0, "frames": 0}]
    check("CONTROL: a contiguous pair cut in two IS reported",
          any("PICTURE CUT INSIDE ONE TAKE" in v for v in ta.violations(fake)))

    # ═══ 5. THE END CARD IS ON SCREEN WHILE HE SPEAKS THE E-BOOK LINE ════════
    # §END SEQUENCE rule 2, locked 25 Jul 2026. Jodie, fault 5: *"the ebook motion
    # graphic turns up after Gordon finishes talking completely."*
    print("\n-- 5. §END SEQUENCE rule 2: the end card is ON the e-book beat --")
    ec, line, se = plan["end_card"], g["ebook_line_at_s"], plan["speech_end_s"]
    check("  the end card fades in while he is still talking",
          ec["from_s"] < se, f"card {ec['from_s']:.2f}s, last word {se:.2f}s")
    check("  ...on the e-book line, within the standing lead",
          line <= ec["from_s"] <= line + tes.ENDCARD_LEAD_S + 0.5,
          f"line {line:.2f}s, card {ec['from_s']:.2f}s "
          f"(+{ec['from_s'] - line:.2f}s)")
    check("  and it stays up until the warranty takes over",
          ec["from_s"] + ec["dur_s"] >= plan["warranty"]["from_s"] - 0.01,
          f"card out {ec['from_s'] + ec['dur_s']:.2f}s, "
          f"warranty in {plan['warranty']['from_s']:.2f}s")
    check("  the warranty slide is still the LAST thing in the film",
          plan["warranty"]["from_s"] + plan["warranty"]["dur_s"]
          >= plan["total_s"] - 0.01)
    check("CONTROL: an end card after the last word IS reported",
          any("END CARD AFTER THE LAST WORD" in v for v in tes.violations(bad)),
          f"control card at {bad['end_card']['from_s']:.2f}s")

    # ═══ 6. A STANDING CLIP'S HOLD COMES FROM THE CLIP ═══════════════════════
    print("\n-- 6. no standing clip is cut off before it finishes --")
    cd = plan["clip_durations"]
    check("  the clip durations were read off the DISK, not a table",
          set(cd) >= {"warranty-slide.mp4", "end-card-template.mp4",
                      "midroll-lowerthird.mp4"}, f"{cd}")
    check("  the warranty holds at least as long as its own clip",
          plan["warranty"]["dur_s"] >= cd["warranty-slide.mp4"],
          f"hold {plan['warranty']['dur_s']:.2f}s, clip "
          f"{cd['warranty-slide.mp4']:.2f}s")
    check("  ...and long enough to read — EP48 measures 9.2s",
          plan["warranty"]["dur_s"] >= 6.0, f"{plan['warranty']['dur_s']:.2f}s")
    check("CONTROL: a 3.5s warranty IS reported as too short",
          any("WARRANTY TOO SHORT" in v for v in tes.violations(bad)),
          f"control hold {bad['warranty']['dur_s']:.2f}s")
    grown = json.loads(json.dumps(plan))
    grown["clip_durations"]["warranty-slide.mp4"] = 30.0
    check("CONTROL: a clip that outgrows its hold IS reported",
          any("STANDING CLIP CUT OFF" in v for v in tes.violations(grown)))

    # ═══ 7. ROOM FOR YOUTUBE'S END SCREEN — MEASURED IN PIXELS ═══════════════
    print("\n-- 7. the plain end frame, asked of the FINISHED FILE --")
    if not final:
        NOTE.append("no finished mp4 given — check 7 not run. Pass the mp4 as the "
                    "second argument. The PLAN cannot answer this one.")
        print("  .... skipped (no mp4 given)")
    else:
        import end_frame as ef
        fp = pathlib.Path(final)
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(fp)],
            capture_output=True, text=True, timeout=900).stdout.strip())
        b_end = ef.brightish(fp, dur - 1.0)
        b_back = ef.brightish(fp, dur - ef.MIN_SECONDS + 0.5)
        b_war = ef.brightish(fp, dur - ef.SECONDS - 2.0)
        check("  the last frame is a PLAIN frame, not the warranty slide",
              b_end < 0.02, f"{b_end * 100:.2f}% bright pixels")
        check(f"  ...and still plain {ef.MIN_SECONDS:.0f}s back",
              b_back < 0.02, f"{b_back * 100:.2f}% bright pixels")
        check("  the warranty slide is what it replaced — busy, as it should be",
              b_war > 0.02, f"{b_war * 100:.2f}% bright pixels at "
                            f"{dur - ef.SECONDS - 2.0:.1f}s")
        check("  the film is the plan plus the end frame",
              abs(dur - (plan["total_s"] + plan["end_frame_s"])) < 1.5,
              f"{dur:.2f}s vs {plan['total_s'] + plan['end_frame_s']:.2f}s")
    check("CONTROL: a film with nothing after the warranty IS reported",
          any("NO PLAIN END FRAME" in v for v in tes.violations(bad)))

    # ═══════════════════════════════════════════════════════════════════════
    print(f"\ntwo-way end sequence: {len(PASS)} passed, {len(FAIL)} failed")
    if NOTE:
        print("\nREPORTED (not failures):")
        for n in NOTE:
            print(f"  ~ {n}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    raise SystemExit(main(int(a[0]) if a else 49, a[1] if len(a) > 1 else None))
