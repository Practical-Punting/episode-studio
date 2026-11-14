"""twoway_splice.render keeps sound and picture in step across every join (EP58, 14 Nov 2026).

    python engine/test_twoway_splice_sync.py

A synthetic clip whose picture FLASHES white for one frame and whose sound BEEPS at the same
instant, every second. Spliced A + B + C at deliberately off-frame times (as real plans are:
47.750s, 137.68s …), then every flash is paired with its beep in the output. The first version
of render() left section C's sound one frame (40ms) early; here no pair may be more than half a
frame apart, in any section. Nothing touches the Drive (a temp folder).
"""
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_splice as ts  # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


d = pathlib.Path(tempfile.mkdtemp(prefix="splice_sync_"))
src = d / "src.mp4"
on = "between(mod(T,1),0.5,0.539)"
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c=black:s=320x240:r=25:d=20,geq=lum='if({on},235,16)':cb=128:cr=128",
                # sample-exact beep (aevalsrc evaluates per SAMPLE; a volume gate per audio frame
                # moves the edge by up to 23ms and the test would measure its own noise)
                "-f", "lavfi", "-i", "aevalsrc='0.5*sin(2*PI*1000*t)*between(mod(t,1),0.5,0.539)':s=44100:d=20",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src)],
               check=True, timeout=300)
plan = {"a": {"from_s": 0.0, "to_s": 7.3711}, "b": {"from_s": 3.1137, "to_s": 9.8263},
        "c": {"from_s": 12.2911, "to_s": 20.0}}
out = d / "out.mp4"
ts.render(plan, src, src, out)


def flashes(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-vf", "scale=32:24,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 32 * 24).mean(axis=1)
    idx = np.where(fr > 120)[0]
    return [i / 25 for i in idx if i == 0 or (i - 1) not in set(idx)]


def beeps(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-vn", "-ac", "1", "-ar", "8000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    a = np.abs(np.frombuffer(raw, np.int16).astype(np.float32))
    loud = np.where(a > 800)[0] / 8000
    out_, last = [], -9
    for t in loud:
        if t - last > 0.3:
            out_.append(t)
        last = t
    return out_


def offsets(f):
    """(flash time, signed beep-minus-flash) for every flash."""
    F, B = flashes(f), beeps(f)
    return [(x, min(B, key=lambda b: abs(b - x)) - x) for x in F] if B else []


# THE CLIP'S OWN BASELINE: flash and beep sit a fixed few ms apart before any splice (frame vs
# audio-packet resolution). A splice must not MOVE that — a one-frame slip moves it by 40ms.
base = offsets(src)
b0 = float(np.median([o for _, o in base])) if base else 0.0
got = offsets(out)
check("the output has a flash and a beep in every section (A, B and C)", len(got) >= 15, f"{len(got)} pairs")
drift = [abs(o - b0) for _, o in got] or [9.0]
check("no pair moves more than 10ms from the clip's own baseline, all the way through",
      max(drift) <= 0.010, f"baseline {b0 * 1000:+.0f}ms, worst move {max(drift) * 1000:.0f}ms")
late = [abs(o - b0) for x, o in got if x > 14.0] or [9.0]
check("section C (after the second join) has not moved", max(late) <= 0.010,
      f"worst in C {max(late) * 1000:.0f}ms")

print(f"\nsplice sync: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
