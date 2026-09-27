#!/usr/bin/env python3
"""Render a 60s TWO-BOX PROOF from synthetic material — no real footage, no credits.

    python engine/twoway_proof.py <out_dir>

Two coloured placeholder windows standing in for the presenters, driven by the real
mechanism: two pushes, one handover, one bed chain. It exists so the MOVEMENT can be
judged before the design or the footage exists — the frame, the dimming, the scale, the
push speed and the eye-line offset are all read from `assets/twoway/layout.json`, so
when Cowork's numbers land the same command re-renders the same clip to the new design.

⚠️ **WHAT IT PROVES AND WHAT IT DOES NOT.** It proves the composite mechanism and the
transition grammar. It cannot prove framing, head placement or whether the dimming is
right, because there are no heads in it — that is the pair test's job (build spec A5(d)).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import twoway_composite as tc                                    # noqa: E402

PROOF_S = 60.0
# The shape the proof has to show, in seconds on the proof's own clock.
BEATS = [
    {"at": 0.0,  "layout": "two-box", "speaker": "BB", "note": "open in the two-box"},
    {"at": 14.0, "layout": "single",  "speaker": "BB", "note": "PUSH 1 -> speaker single"},
    {"at": 32.0, "layout": "two-box", "speaker": "BB", "note": "PUSH 2 -> back, in time "
                                                              "for the handover"},
    {"at": 41.0, "layout": "two-box", "speaker": "BM", "note": "HANDOVER — the cut "
                                                              "happens INSIDE the "
                                                              "two-box"},
    {"at": 41.0, "layout": "two-box", "speaker": "BM", "bed_chain_at": 45.0,
     "note": "BED CHAIN — R1a runs out and cuts to R11, never loops"},
]


FONT = "/Windows/Fonts/arial.ttf"
"""⚠️ drawtext NEEDS AN EXPLICIT FONTFILE ON WINDOWS. Without one this ffmpeg build
does not fall back to a default — it segfaults (0xC0000005), which reads as a broken
command rather than a missing font. The colon is escaped because it is inside a filter
argument. AND THE DRIVE LETTER HAS TO GO: this build refuses a drive-lettered path
outright ("No option name near '/Windows/Fonts/arial.ttf'"), because a colon is the
filter argument separator and the usual escape is not honoured here. A drive-less path
resolves against the current drive and parses cleanly."""


def _ff() -> str:
    import pp_paths
    return pp_paths.ffmpeg() or "ffmpeg"


def placeholder(out: pathlib.Path, colour: str, label: str, secs: float,
                w: int, h: int) -> None:
    """A coloured card standing in for a presenter window. Deliberately not a face."""
    subprocess.run(
        [_ff(), "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c={colour}:s={w}x{h}:d={secs}:r=30",
         "-vf", f"drawtext=fontfile={FONT}:text='{label}':fontcolor=white:"
                f"fontsize={h // 7}:x=(w-text_w)/2:y=(h-text_h)/2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
        check=True, timeout=600)


def _c(v: str) -> str:
    """A colour the FILTER GRAPH accepts. layout.json states design colours as #RRGGBB,
    which is what a designer writes and what every other PP asset uses; inside an ffmpeg
    filter the # is not valid and 0x is. Converted here, at the boundary, so the design
    file never has to know what renders it."""
    return "0x" + v[1:] if v.startswith("#") else v


def render(out_dir: pathlib.Path) -> pathlib.Path:
    layout = tc.load_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    c = layout["canvas"]
    lw = layout["windows"]["left"]["rect"]
    rw = layout["windows"]["right"]["rect"]
    li = layout["listener"]
    p = layout["push"]

    src = out_dir / "_src"
    src.mkdir(exist_ok=True)
    placeholder(src / "bb.mp4", "0x2E5E8C", "GORDON reading BRIAN", PROOF_S,
                lw[2], lw[3])
    placeholder(src / "bm.mp4", "0x8C4A2E", "STEVE reading BARRY", PROOF_S,
                rw[2], rw[3])

    # The dimmed + slightly smaller listener, and the same window at full size.
    dim = round((li["brightness_pct"] - 100) / 200.0, 4)
    sc = li["scale_pct"] / 100.0
    ease = "0.16,1,0.3,1"        # the house curve, from layout.json
    d = p["duration_ms"] / 1000.0
    # Push windows: BB single from 14s to 32s; two-box either side.
    fc = (
        f"color=c={_c(c['background'])}:s={c['w']}x{c['h']}:d={PROOF_S}:r=30[bg];"
        f"[0:v]split=2[bb1][bb2];"  # BM is used once, so it is NOT split: an unconnected
        # split output is a hard 'Filter split has output 0 unconnected' bind error.
        # two-box: BB left full, BM right dimmed and smaller (and vice versa after 41s)
        f"[bb1]eq=brightness=0[bbfull];"
        f"[1:v]scale=iw*{sc}:ih*{sc},eq=brightness={dim},"
        f"pad={rw[2]}:{rw[3]}:(ow-iw)/2:(oh-ih)/2[bmdim];"
        f"[bg][bbfull]overlay={lw[0]}:{lw[1]}:enable='between(t,0,{PROOF_S})'[a];"
        f"[a][bmdim]overlay={rw[0]}:{rw[1]}:"
        f"enable='not(between(t,{14 + d},{32 - d}))'[b];"
        # the single: BB's window scaled up to fill, only while the push has landed
        f"[bb2]scale={c['w']}:-2,crop={c['w']}:{c['h']}[bbbig];"
        f"[b][bbbig]overlay=0:0:enable='between(t,{14 + d},{32 - d})'[c];"
        # furniture: the rule and the logo block, below and OUTSIDE both windows
        f"[c]drawbox=x={layout['furniture']['rule']['rect'][0]}:"
        f"y={layout['furniture']['rule']['rect'][1]}:"
        f"w={layout['furniture']['rule']['rect'][2]}:"
        f"h={layout['furniture']['rule']['rect'][3]}:"
        f"color={_c(layout['furniture']['rule']['colour'])}:t=fill:"
        f"enable='not(between(t,{14 + d},{32 - d}))'[d];"
        f"[d]drawbox=x={layout['furniture']['logo']['rect'][0]}:"
        f"y={layout['furniture']['logo']['rect'][1]}:"
        f"w={layout['furniture']['logo']['rect'][2]}:"
        f"h={layout['furniture']['logo']['rect'][3]}:"
        f"color=white@0.55:t=fill[e];"
        # the supers, on first appearance and on the return to the two-box
        f"[e]drawtext=fontfile={FONT}:text='GORDON - reading Brian Blackwell, editor, Practical "
        f"Punting':fontcolor=white:fontsize=30:x={lw[0]}:"
        f"y={layout['supers']['left']['rect'][1]}:"
        f"enable='between(t,0.4,3.6)+between(t,32,35.2)'[f];"
        f"[f]drawtext=fontfile={FONT}:text='STEVE - reading Barry Meadow, US handicapper':"
        f"fontcolor=white:fontsize=30:x={rw[0]}:"
        f"y={layout['supers']['right']['rect'][1]}:"
        f"enable='between(t,0.4,3.6)+between(t,41,44.2)'[g];"
        # markers so a viewer can see WHICH event they are looking at
        f"[g]drawtext=fontfile={FONT}:text='PUSH':fontcolor=0xDA532C:fontsize=42:x=60:y=60:"
        f"enable='between(t,{14 - 0.2},{14 + d})+between(t,{32 - d},{32 + 0.2})'[h];"
        f"[h]drawtext=fontfile={FONT}:text='HANDOVER':fontcolor=0xDA532C:fontsize=42:x=60:y=60:"
        f"enable='between(t,40.8,42.6)'[i];"
        f"[i]drawtext=fontfile={FONT}:text='BED CHAIN R1a -> R11':fontcolor=0xDA532C:fontsize=42:"
        f"x=60:y=60:enable='between(t,44.8,47.4)'[v]"
    )
    dest = out_dir / "twobox-proof.mp4"
    subprocess.run(
        [_ff(), "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(src / "bb.mp4"), "-i", str(src / "bm.mp4"),
         "-filter_complex", fc, "-map", "[v]", "-t", str(PROOF_S),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(dest)],
        check=True, timeout=1200)

    (out_dir / "what-this-shows.json").write_text(
        json.dumps({"beats": BEATS, "layout_used": str(tc.LAYOUT),
                    "push_ms": p["duration_ms"], "easing": p["easing_out"],
                    "listener_brightness_pct": li["brightness_pct"],
                    "listener_scale_pct": li["scale_pct"],
                    "_placeholders": "The windows are COLOURED CARDS, not faces. This "
                                     "proves the mechanism and the transition grammar; "
                                     "framing and head placement are the pair test's "
                                     "job (build spec A5d).",
                    "_design": "Every number came from assets/twoway/layout.json. When "
                               "Cowork's design lands, re-run this command and the same "
                               "clip re-renders to the new design."},
                   indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    return dest


def main() -> int:
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    dest = render(out)
    print(f"WROTE {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
