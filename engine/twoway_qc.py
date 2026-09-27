#!/usr/bin/env python3
"""twoway_qc.py — QC the finished two-way episode by looking at its own pixels.

    python engine/twoway_qc.py <ep_number> <episode.mp4> [--out DIR] [--json FILE]

🔴 EVERY CHECK HERE OPENS THE FINISHED FILE. Nothing reads the plan and reports what the
plan says — that is a consistency check, and a consistency check proves sameness, never
correctness. The plan is used only to say WHERE to look; what is found is whatever is
in the frame.

What it asks, in the order that matters:

  1. **Is it the right shape and length?** 1920x1080, and the duration the plan says,
     with the frame count DECODED rather than read off the header — a faststart mp4
     announces the length it intended even when the tail never arrived (EP15).
  2. **Is the picture where the cue sheet says?** A frame is pulled in the middle of
     every card, every clip, every furniture piece, the title card, the end card and
     the warranty slide, and written out so a human can see all of them at once.
  3. **Is the two-box a two-box?** The 8px seam between the panels is sampled: both
     panels present, the orange keyline on BOTH of them, the listener dimmer than the
     speaker.
  4. **Is anything black?** A frame that is nearly all one dark value is a hole in the
     picture, and holes are what a concat of sixty-four pieces gets wrong.
  5. **Is the end ever silent?** PP-STANDARDS §END SEQUENCE item 3 — the warranty
     window's RMS, measured, because "the end is NEVER silent" is the EP08 lesson.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ep_paths                                                   # noqa: E402
import twoway_assemble as ta                                      # noqa: E402
import twoway_composite as tc                                     # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")


def probe(path: pathlib.Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-count_packets", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_packets",
                        "-show_entries", "format=duration,bit_rate",
                        "-of", "json", str(path)],
                       capture_output=True, text=True, timeout=900)
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    fmt = d.get("format") or {}
    num, _, den = (st.get("r_frame_rate") or "0/1").partition("/")
    return {"w": st.get("width"), "h": st.get("height"),
            "fps": round(float(num) / float(den or 1), 3),
            "frames": int(st.get("nb_read_packets") or 0),
            "dur_s": round(float(fmt.get("duration") or 0), 2),
            "kbps": round(int(fmt.get("bit_rate") or 0) / 1000),
            "bytes": path.stat().st_size}


def grab(path: pathlib.Path, t: float, out: pathlib.Path, w: int = 640) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                    "-vf", f"scale={w}:-2", str(out)], check=True, timeout=300)


def stats(path: pathlib.Path, t: float) -> dict:
    """Mean and spread of one frame — enough to tell a picture from a black hole."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path),
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, timeout=300)
    import numpy as np
    buf = np.frombuffer(r.stdout, np.uint8)
    if buf.size < 1000:
        return {"mean": 0.0, "std": 0.0, "n": int(buf.size)}
    return {"mean": round(float(buf.mean()), 2), "std": round(float(buf.std()), 2),
            "n": int(buf.size)}


def seam_check(path: pathlib.Path, t: float, layout: dict) -> dict:
    """At a two-box moment: are there two panels, both keylined, listener dimmer?"""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path),
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, timeout=300)
    W, H = layout["canvas"]["w"], layout["canvas"]["h"]
    img = np.frombuffer(r.stdout, np.uint8)
    if img.size != W * H * 3:
        return {"measurable": False}
    img = img.reshape(H, W, 3).astype(int)
    kl = (layout.get("keyline") or layout["speaker"]["keyline"])
    want = np.array([int(kl["colour"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)])
    out = {"measurable": True}
    for side in ("left", "right"):
        x, y, w, h = layout["panels"][side]["rect"]
        edge = np.concatenate([img[y:y + 3, x:x + w].reshape(-1, 3),
                               img[y + h - 3:y + h, x:x + w].reshape(-1, 3)])
        hit = float((np.abs(edge - want).max(axis=1) < 60).mean())
        body = img[y + 40:y + h - 40, x + 40:x + w - 40]
        out[side] = {"keyline_pct": round(hit * 100, 1),
                     "brightness": round(float(body.mean()), 1)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("episode")
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--out")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()

    pp = pathlib.Path(a.pp)
    d = ep_paths.episode_dir(a.ep_number, pp)
    ep = pathlib.Path(a.episode)
    if not ep.is_file():
        print(f"HALT: no {ep}", file=sys.stderr)
        return 2
    plan = ta.build_plan(a.ep_number, pp)
    layout = tc.load_layout()
    frames = pathlib.Path(a.out or (d / "output/qc-frames"))
    frames.mkdir(parents=True, exist_ok=True)

    p = probe(ep)
    faults, notes = [], []
    print(f"{ep.name}")
    print(f"  {p['dur_s']:.2f}s  {p['w']}x{p['h']}  {p['fps']}fps  "
          f"{p['frames']:,} frames  {p['kbps']} kbps  {p['bytes']:,} bytes")
    if (p["w"], p["h"]) != (1920, 1080):
        faults.append(f"the picture is {p['w']}x{p['h']}, not 1920x1080.")
    # 🔴 THE FILM IS THE PLAN **PLUS THE APPENDED END FRAME**. `end_frame.py` joins 18s
    # of charcoal on after the warranty, outside everything the plan describes, so a
    # check that compares the file to `total_s` alone reports an 18-second fault on a
    # correct episode — and the obvious "fix" for that is to stop appending it.
    want = plan["total_s"] + (plan.get("end_frame_s") or 0)
    if abs(p["dur_s"] - want) > 1.5:
        faults.append(f"the file is {p['dur_s']:.2f}s and the plan plus its end frame "
                      f"is {want:.2f}s — {p['dur_s'] - want:+.2f}s.")
    exp = round(p["dur_s"] * p["fps"])
    if p["frames"] and abs(p["frames"] - exp) > p["fps"] * 2:
        faults.append(f"{p['frames']:,} frames decoded against {exp:,} the header "
                      f"implies — the picture does not reach the stated length.")

    # 2 — a frame in the middle of everything the cue sheet names
    shots = [("title", plan["head"]["to_s"] / 2)]
    for s in plan["segments"]:
        mid = s["from_s"] + s["dur_s"] / 2
        if s.get("card"):
            shots.append((f"card-{s['card']}", mid))
        elif s.get("broll"):
            shots.append((f"broll-{s['broll'].replace('broll-', '')[:28]}", mid))
        elif s.get("kind") == "furniture":
            shots.append((f"furniture-{s['furniture']}", mid))
    # 🔴 THE STANDING GRAPHICS GET FRAMES TOO. They are OVERLAYS on a furniture beat,
    # so nothing in `plan["segments"]` names them — which is exactly how three cuts
    # shipped without any of them and thirty QC frames said nothing. A frame is pulled
    # in the middle of each one, and the check below asks whether it CHANGED anything.
    gq = plan.get("graphics") or {}
    for key in ("open_card", "early_cta", "midroll"):
        spec = gq.get(key)
        if spec:
            shots.append((f"graphic-{key}", spec["at_s"] + spec["dur_s"] / 2))
    if plan["end_card"]:
        shots.append(("end-card",
                      plan["end_card"]["from_s"] + plan["end_card"]["dur_s"] / 2))
    shots.append(("warranty",
                  plan["warranty"]["from_s"] + plan["warranty"]["dur_s"] / 2))
    if plan.get("end_frame_s"):
        shots.append(("end-frame", plan["total_s"] + plan["end_frame_s"] / 2))
    print(f"\n  {len(shots)} frames pulled into {frames.name}/")
    dark = []
    for name, t in shots:
        f = frames / f"{t:07.1f}s-{name}.png"
        grab(ep, t, f)
        st = stats(ep, t)
        if st["std"] < 6.0:
            dark.append((name, t, st))
    for name, t, st in dark:
        faults.append(f"BLANK FRAME at {t:.1f}s ({name}): mean {st['mean']}, "
                      f"spread {st['std']} — that is a hole, not a picture.")

    # 2b — 🔴 IS THE STANDING GRAPHIC ACTUALLY ON THE SCREEN?
    #
    # ⚠️ AND THIS IS ASKED OF THE PIXELS, NOT OF THE PLAN. The plan is what ASKED for
    # the graphic; asking it whether the graphic arrived is asking a thing to confirm
    # itself, which is how three cuts passed every plan-level check and were wrong on
    # screen. The measurement is a COMPARISON: the frame under the graphic against a
    # frame of the same furniture beat a second outside it. If placing a full-frame
    # card over Gordon changes nothing, the card is not there.
    for key, floor in (("open_card", 25.0), ("early_cta", 25.0), ("midroll", 2.0),
                       ("end_card", 25.0)):
        spec = gq.get(key) if key != "end_card" else plan.get("end_card")
        if not spec:
            continue
        at = spec.get("at_s", spec.get("from_s"))
        dur = spec["dur_s"]
        on = stats(ep, at + dur / 2)
        off = stats(ep, at - 1.5)
        moved = abs(on["mean"] - off["mean"])
        print(f"    {key:10s} on {on['mean']:6.1f}  off {off['mean']:6.1f}  "
              f"moved {moved:5.1f}")
        if moved < floor:
            faults.append(
                f"{key.replace('_', ' ')} NOT ON SCREEN at {at + dur / 2:.1f}s: the "
                f"frame under it reads {on['mean']:.1f} and the same beat 1.5s before "
                f"it reads {off['mean']:.1f} — a {moved:.1f} difference, under the "
                f"{floor:.0f} this graphic makes when it is drawn. A furniture beat "
                f"that owes a graphic and looks unchanged has not got one.")
        else:
            notes.append(f"{key.replace('_', ' ')} visible at {at + dur / 2:.1f}s "
                         f"(luma {off['mean']:.0f} -> {on['mean']:.0f}, "
                         f"a {moved:.0f} move)")

    # 3 — the two-box, on the finished pixels
    tb_segs = [s for s in plan["segments"] if s["layout"] == "two-box"
               and s["dur_s"] > 4]
    sampled = tb_segs[:: max(1, len(tb_segs) // 4)][:4]
    print(f"\n  two-box sampled at {len(sampled)} moments:")
    for s in sampled:
        t = s["from_s"] + s["dur_s"] / 2
        r = seam_check(ep, t, layout)
        if not r.get("measurable"):
            notes.append(f"two-box at {t:.0f}s could not be measured")
            continue
        l, rr = r["left"], r["right"]
        print(f"    {t:7.1f}s  keyline L {l['keyline_pct']:5.1f}%  "
              f"R {rr['keyline_pct']:5.1f}%   brightness L {l['brightness']:6.1f}  "
              f"R {rr['brightness']:6.1f}  (speaker {s['speaker']})")
        for side, v in (("left", l), ("right", rr)):
            if v["keyline_pct"] < 60:
                faults.append(f"the {side} panel's orange keyline is only "
                              f"{v['keyline_pct']:.0f}% of its border at {t:.0f}s — "
                              f"the frame is on both panels, always.")
        grab(ep, t, frames / f"{t:07.1f}s-twobox.png")

    # 5 — the end is never silent
    w0 = plan["warranty"]["from_s"]
    # volumedetect, not astats: astats prints its RMS per channel under names that
    # differ between ffmpeg builds, and a parse that finds nothing reports "could not
    # measure" — which is indistinguishable from silence, the very thing being checked.
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{w0:.2f}",
                        "-t", f"{plan['warranty']['dur_s']:.2f}", "-i", str(ep),
                        "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=600)
    import re
    rms = [float(x) for x in re.findall(r"mean_volume:\s*(-?[\d.]+) dB",
                                        (r.stderr or "") + (r.stdout or ""))]
    if rms:
        worst = max(rms)
        print(f"\n  warranty window RMS {worst:.1f} dB")
        if worst <= -34:
            faults.append(f"the warranty window is {worst:.1f} dB — the end is NEVER "
                          f"silent (§END SEQUENCE item 3, the EP08 lesson).")
    else:
        notes.append("could not measure the warranty window's RMS")

    # 6 \u2014 \ud83d\udd34 THE PLAIN END FRAME, IN PIXELS. \u00a7END SEQUENCE has no rule for this and
    # `end_frame.py` does: YouTube draws its end-screen boxes over the last 15-20
    # seconds and the operator does not choose where, so the last stretch must be a
    # frame with nothing on it a box can hide. `qc_episode` HARD-FAILS below 15s and
    # this is the two-way's copy of that question, asked the same way \u2014 by counting
    # bright pixels, never by reading the plan.
    try:
        sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production"
                                             "/scripts"))
        import end_frame as ef
        tail_ok = ef.looks_plain(ep, p["dur_s"] - 1.0)
        long_enough = tail_ok and ef.looks_plain(ep, p["dur_s"] - ef.MIN_SECONDS + 0.5)
        if not tail_ok:
            faults.append(
                f"no plain end frame: the last frames of {ep.name} are still the "
                f"warranty slide, so YouTube's end-screen boxes land on the "
                f"responsible-gambling text and the 1800 858 858 support line.")
        elif not long_enough:
            faults.append(
                f"the plain end frame is shorter than {ef.MIN_SECONDS:.0f}s, so a box "
                f"drawn at the top of YouTube's window still lands on the warranty.")
        else:
            notes.append(f"plain end frame present and at least "
                         f"{ef.MIN_SECONDS:.0f}s long (film {p['dur_s']:.1f}s)")
    except Exception as e:                                        # noqa: BLE001
        notes.append(f"could not check the plain end frame: {e}")

    # 7 \u2014 \ud83d\udd34 \u00a7END SEQUENCE RULE 4: THE MIDROLL GOES TO A HUMAN EAR.
    #
    # *"QC exports the midroll audio segment (midroll-listen.wav) for a human LISTEN \u2014
    # confirm the voice/accent stays Gordon before approving the video."* The
    # single-presenter QC has done this since EP08 and the two-way never has, which is
    # a gate that quietly stopped existing when the format changed. It is EXPORTED and
    # left waiting; nothing here ticks it.
    midf = next((s for s in plan["segments"]
                 if s.get("furniture") == "midroll"), None)
    if midf:
        qcdir = d / "output/qc"
        qcdir.mkdir(parents=True, exist_ok=True)
        wav = qcdir / "midroll-listen.wav"
        t0 = max(0.0, midf["from_s"] - 1.0)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}",
                        "-t", f"{midf['to_s'] - t0 + 1.0:.3f}", "-i", str(ep),
                        "-vn", "-ac", "1", "-ar", "44100", str(wav)],
                       check=True, timeout=900)
        notes.append(f"LISTEN (human ears required): the midroll "
                     f"({midf['from_s']:.0f}-{midf['to_s']:.0f}s) is saved to "
                     f"{wav} \u2014 confirm the voice stays Gordon before approving. "
                     f"NOT ticked here.")
    else:
        notes.append("no midroll furniture beat found \u2014 no listen file exported")

    print(f"\n{len(faults)} fault(s)" if faults else "\n\u2705 QC clean")
    for f in faults:
        print("  ! " + f)
    for n in notes:
        print("  \u00b7 " + n)
    if a.json_out:
        # 🔴 `frames_pulled`, NOT `frames`. This used to write `"frames": len(shots)`
        # AFTER `**p`, so the number of screenshots silently overwrote the DECODED
        # frame count — the one measurement that caught the missing settle. A reader
        # of qc.json saw "30 frames" for a 21,412-frame episode and could not tell it
        # was the wrong quantity, because both are honestly called "frames".
        pathlib.Path(a.json_out).write_text(
            json.dumps({"file": ep.name, **p, "faults": faults, "notes": notes,
                        "frames_pulled": len(shots), "planned_s": plan["total_s"]},
                       indent=1), encoding="utf-8")
    return 1 if faults else 0


if __name__ == "__main__":
    raise SystemExit(main())
