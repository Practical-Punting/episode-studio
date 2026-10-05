#!/usr/bin/env python3
"""twoway_cue_sheet.py — the episode as a plain timecoded list, one line each.

    python engine/twoway_cue_sheet.py <ep_number> [--pp DIR] [--out FILE]

Jodie, 20 Sep 2026: *"Her notes will cite timecodes and I need them to land on something
you can act on without hunting."*

🔴 SO EVERY LINE CARRIES ITS OWN HANDLE. A note that says "the card at 7:12 is wrong"
has to reach a card id, a beat, a source file and a segment number without anybody
reading a JSON file to find them. mm:ss because that is what a person reads off a
player's scrubber, and the raw seconds beside it because that is what the tools take.

📌 BUILT FROM THE PLAN, NOT FROM THE RENDER. The plan is what the render is made of, so
a cue sheet from the plan describes what the file should be; if the two ever disagree
the QC's frame extraction is what finds it, and a cue sheet generated from the finished
file could not — it would agree with the fault.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ep_paths                                                   # noqa: E402
import twoway_assemble as ta                                      # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")


def mmss(t: float) -> str:
    return f"{int(t // 60):d}:{t % 60:04.1f}"


def build(ep_number: int, pp: pathlib.Path = PP) -> str:
    d = ep_paths.episode_dir(ep_number, pp)
    plan = ta.build_plan(ep_number, pp)
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    cards = {c["id"]: c for c in epj["cards"]}
    broll = {b["target"]: b for b in epj["broll"]}
    segs = plan["segments"]

    rows = []
    rows.append(("0:00.0", mmss(ta.TITLE_HEAD_S), "TITLE CARD",
                 f"{epj['packaging']['hook']} / {epj['packaging']['byline']}"))
    prev_speaker = None
    for s in segs:
        a, b = mmss(s["from_s"]), mmss(s["to_s"])
        if s.get("kind") == "furniture":
            rows.append((a, b, f"FURNITURE  {s['furniture'].upper()}",
                         f"{s.get('name')} — Gordon full frame, {s['dur_s']:.1f}s"))
            prev_speaker = s["speaker"]
            continue
        if s.get("card"):
            c = cards.get(s["card"], {})
            rows.append((a, b, f"CARD  {s['card']}",
                         f"{c.get('headline', '')} — {c.get('block', '')}, "
                         f"beat {c.get('beat')}, {s['dur_s']:.1f}s"))
            continue
        if s.get("broll"):
            bb = broll.get(s["broll"], {})
            rows.append((a, b, "B-ROLL",
                         f"{s['broll'].replace('broll-', '')} — \"{bb.get('line', '')}\""
                         f", {s['dur_s']:.1f}s"))
            continue
        if s["speaker"] != prev_speaker and prev_speaker is not None:
            rows.append((a, "", "HANDOVER",
                         f"{prev_speaker} \u2192 {s['speaker']}"
                         f"  ({'Gordon' if s['speaker'] == 'BB' else 'Steve'} takes "
                         f"turn {s['turn']})"))
        who = "Gordon" if s["speaker"] == "BB" else "Steve"
        what = "TWO-BOX" if s["layout"] == "two-box" else f"SINGLE  {who}"
        rows.append((a, b, what, f"turn {s['turn']}, {s['dur_s']:.1f}s"))
        prev_speaker = s["speaker"]

    # 🔴 THE SETTLE GETS ITS OWN ROW. It used to show up only as an unnamed gap between
    # the last furniture row and the end card — and a gap in a list of what is on screen
    # is exactly what nobody checks. The first cut shipped with those three seconds
    # BLACK because no piece was ever rendered for them, and the cue sheet could not
    # have told anyone: it named nothing there to be missing. Air is a shot too.
    # 🔴 THE TAIL BEGINS AT THE WARRANTY, NOT AT THE END CARD. The end card now goes up
    # ON THE E-BOOK BEAT, inside the outro, while Gordon is still talking — so it is not
    # the start of anything, and measuring the settle to it gave -19.5s.
    tail0 = plan["warranty"]["from_s"]
    if tail0 - plan["speech_end_s"] > 0.01:
        rows.append((mmss(plan["speech_end_s"]), mmss(tail0), "SETTLE",
                     f"the last shot held, music swelling — no speech, "
                     f"{tail0 - plan['speech_end_s']:.1f}s"))
    if plan["end_card"]:
        e = plan["end_card"]
        rows.append((mmss(e["from_s"]), mmss(e["from_s"] + e["dur_s"]), "END CARD",
                     f"the real e-book cover + the free-guide link line \u2014 OVER the "
                     f"outro, fading in on the e-book line at "
                     f"{mmss(plan['graphics']['ebook_line_at_s'])} and held until the "
                     f"warranty (\u00a7END SEQUENCE rule 2)"))
    w = plan["warranty"]
    rows.append((mmss(w["from_s"]), mmss(w["from_s"] + w["dur_s"]), "WARRANTY",
                 f"the responsible-gambling slide, {w['dur_s']:.1f}s"))
    if plan.get("end_frame_s"):
        rows.append((mmss(plan["total_s"]),
                     mmss(plan["total_s"] + plan["end_frame_s"]), "END FRAME",
                     f"charcoal + the PP logo, {plan['end_frame_s']:.0f}s \u2014 the "
                     f"room YouTube's end-screen boxes sit in, so they cannot cover "
                     f"the warranty text or the support number"))

    # \ud83d\udd34 THE OVERLAYS GET THEIR OWN ROWS. They sit ON TOP of a furniture beat rather
    # than beside it, so they have no row of their own in the picture timeline \u2014 which
    # is exactly how three cuts shipped without either of them and no list said so.
    # A graphic that is not in the cue sheet is a graphic nobody checks.
    g = plan.get("graphics") or {}
    for key, role, what in (("open_card", "open", "OVER  WHO YOU'RE HEARING"),
                            ("early_cta", "cta", "OVER  E-BOOK CARD"),
                            ("midroll", "midroll", "OVER  LIKE & SUBSCRIBE")):
        spec = g.get(key)
        if not spec:
            continue
        rows.append((mmss(spec["at_s"]), mmss(spec["at_s"] + spec["dur_s"]), what,
                     f"{pathlib.Path(spec['clip']).name}, {spec['dur_s']:.1f}s, over "
                     f"the {role} furniture \u2014 the words start at "
                     f"{mmss(spec['spoken_at_s'])}"))
    rows.sort(key=lambda r: (int(r[0].split(":")[0]) * 60 + float(r[0].split(":")[1])))

    out = [f"# {epj['episode']} — CUE SHEET",
           f"",
           f"**{epj['packaging']['youtube_title']}**",
           f"",
           f"Total **{mmss(plan['total_s'])}** ({plan['total_s']:.1f}s). Built from "
           f"`renders/assembly-plan.json`, not from the finished file.",
           f"",
           f"| in | out | what | detail |",
           f"|---|---|---|---|"]
    for a, b, what, detail in rows:
        out.append(f"| **{a}** | {b} | **{what}** | {detail} |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--out")
    a = ap.parse_args()
    text = build(a.ep_number, pathlib.Path(a.pp))
    if a.out:
        p = pathlib.Path(a.out)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        import os
        os.replace(tmp, p)
        print(f"wrote {p}  ({len(text):,} bytes, "
              f"{text.count(chr(10))} lines, re-read "
              f"{'ok' if p.read_text(encoding='utf-8') == text else 'MISMATCH'})")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
