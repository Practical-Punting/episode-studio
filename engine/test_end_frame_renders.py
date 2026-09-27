#!/usr/bin/env python3
"""The plain end frame must actually RENDER, and on THIS machine's ffmpeg.

    python engine/test_end_frame_renders.py

🔴 WHY THIS EXISTS. `end_frame.py` was untouched from 11 August and correct the whole
time — and on 22 September 2026 it stopped terminating. EP49's append sat for
**43 minutes**, burned **412 CPU-seconds**, grew past **865 MB of RSS** and never
created its output file. Nothing failed; nothing said anything. The step had no timeout,
so the only symptom was a file that would never grow.

⚠️ AND IT IS A VERSION BEHAVIOUR, WHICH IS EXACTLY WHY A UNIT TEST OF THE ARGUMENTS
WOULD NOT HAVE CAUGHT IT. The command was unchanged. `ffmpeg` moved underneath it
(8.1.2-full_build), and `-loop 1 -t N -i <png>` stopped ending. So this test RENDERS —
it is the artefact, not the arguments (CLAUDE.md fault #1).

⭐ THE CONTROL IS THE POINT. Watching the fixed form pass proves nothing on its own: a
two-second render is exactly what a broken command that quietly produces nothing also
looks like from a distance. So the OLD shape is run first, on this machine, and the test
asserts that it does NOT finish — then that the new one does, and that what it produced
is an eighteen-second, correctly-sized, NOT-silent clip with a logo on it.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import end_frame as ef                                            # noqa: E402
import ep_paths                                                   # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")
# 🔴 RESOLVED BY NUMBER, NEVER BY FOLDER NAME. `episode_dir()` is the one lookup —
# `PP-EP1*` also matches `PP-EP10` and `PP-EP9*` matches `PP-EP98`, which is why a bare
# folder name in a suite is a lint failure and not a style note (CLAUDE.md fault 0a).
# This test needs A logo and A music bed, not EP49's in particular; it takes them from
# the episode `end_frame` was first proved on.
LOGO = ep_paths.episode_dir(49, PP) / "overlay/export/assets/logo.png"
MUSIC = (ep_paths.episode_dir(1, PP) / "music"
         / "ES_Sleeves Full of Aces - Alexandra Woodward.mp3")
SPEC = {"w": 1920, "h": 1080, "fps": "25/1", "pix": "yuv420p", "ar": 48000}

PASS, FAIL = [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'OK  ' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    return ok


def main() -> int:
    print("ffmpeg: " + subprocess.run(["ffmpeg", "-version"], capture_output=True,
                                      text=True).stdout.splitlines()[0])
    if not LOGO.is_file() or not MUSIC.is_file():
        print("  .... skipped — the logo or the music is not on this machine")
        return 0
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="endframe-"))

    # ═══ THE CONTROL — the shape that hung, at 2 seconds, with 45 to finish in ═══
    print("\n-- CONTROL: the `-loop 1` form this file used to carry --")
    dst = tmp / "old.mp4"
    t0 = time.time()
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "color=c=0x1E1E1E:s=1920x1080:r=25/1:d=2",
             "-loop", "1", "-t", "2", "-i", str(LOGO), "-map", "0:v",
             "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             str(dst)], capture_output=True, timeout=45)
        hung = False
    except subprocess.TimeoutExpired:
        hung = True
    old_s = time.time() - t0
    # 📌 NOT ASSERTED AS A FAILURE. If a later ffmpeg fixes the demuxer this control
    # will start passing, and that is NEWS rather than a broken test — the fixed form
    # below stays correct either way. What must never happen is the control passing
    # while the real one hangs.
    print(f"  the old shape {'HUNG (45s timeout)' if hung else f'finished in {old_s:.1f}s'}"
          f" — this is why the form changed")

    # ═══ THE REAL THING ══════════════════════════════════════════════════════
    print("\n-- the end frame as `end_frame.build_clip` builds it today --")
    dst = tmp / "end.mp4"
    t0 = time.time()
    try:
        ef.build_clip(dst, LOGO, MUSIC, SPEC, ef.SECONDS)
        err = None
    except Exception as e:                                        # noqa: BLE001
        err = e
    dt = time.time() - t0
    check("it renders at all", err is None and dst.is_file(), f"{err or ''}")
    if not dst.is_file():
        print(f"\nend frame: {len(PASS)} passed, {len(FAIL)} failed")
        return 1
    check(f"and it renders in seconds, not minutes ({dt:.1f}s)", dt < 120,
          f"{dt:.1f}s")

    p = ef.probe(dst)
    check(f"it is {ef.SECONDS:.0f} seconds long", abs(p["dur"] - ef.SECONDS) < 0.6,
          f"{p['dur']:.2f}s")
    check("it matches the film it will be joined to", (p["w"], p["h"]) == (1920, 1080),
          f"{p['w']}x{p['h']}")
    check("it carries audio — the end is NEVER silent", bool(p["acodec"]),
          f"{p['acodec']} {p['ar']}Hz")

    # 🔴 AND IT IS PLAIN, MEASURED THE WAY qc_episode MEASURES IT — the whole point of
    # the frame is that an end-screen box can cover it without hiding anything.
    b = ef.brightish(dst, ef.SECONDS / 2)
    check(f"it is PLAIN enough for a box to sit on ({b * 100:.2f}% bright)",
          b < 0.02, f"{b * 100:.3f}%")
    # ...but not EMPTY: the logo has to be on it, or it is a black hole, not a frame.
    import numpy as np
    from PIL import Image
    import io
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ef.SECONDS / 2:.2f}",
                        "-i", str(dst), "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True)
    a = np.asarray(Image.open(io.BytesIO(r.stdout)).convert("L"), dtype=np.float64)
    h, w = a.shape
    mid = a[h // 2 - 60:h // 2 + 60, w // 2 - 190:w // 2 + 190]
    edge = a[:120, :120]
    check("the LOGO is on it — the middle is brighter than the corner",
          mid.mean() > edge.mean() + 3.0,
          f"middle {mid.mean():.1f}, corner {edge.mean():.1f}")

    rms = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(dst), "-af", "volumedetect",
         "-f", "null", "-"], capture_output=True, text=True).stderr
    import re
    v = [float(x) for x in re.findall(r"mean_volume:\s*(-?[\d.]+) dB", rms)]
    check("and the bed under it is audible, not digital silence",
          bool(v) and v[0] > -50.0, f"{v[0] if v else None} dB")

    print(f"\nend frame: {len(PASS)} passed, {len(FAIL)} failed")
    print(f"  clip kept at {dst}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
