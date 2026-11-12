"""twoway_render.assert_audio_in_step — the finished file's SOUND is where its picture is.

EP56 cut 1 (12 Nov 2026) shipped out of the renderer with an AAC track 6.85s longer than the
film and the speech 4.1s LATE inside it; lips matched the plan 16/16, so only the sound was off.
The guard decodes the finished file from its first sample and finds the speech by correlation.

Synthetic files (seconds to build), plus — if it is still on disk — the real broken EP56 cut 1:
  1. a mix with the speech at +7.0s                                -> passes
  2. CONTROL: the same speech at +11.1s (EP56's fault)             -> refused
  3. CONTROL: audio 6.9s longer than the film                      -> refused
  4. REAL: output/BROKEN-sound-4s-late_PP-EP56-cut1-before-end-frame.mp4, if present -> refused
  5. REAL: output/PP-EP56-cut1-before-end-frame.mp4 (the re-finished one), if present -> passes

Run: python engine/test_twoway_audio_in_step.py
"""
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_render as tr  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def refused(fn):
    try:
        fn()
    except tr.Unrenderable as e:
        return str(e)
    return None


td = pathlib.Path(tempfile.mkdtemp())
SR = 48000
rng = np.random.default_rng(56)
dur = 40.0
env = np.repeat(rng.random(int(dur * 4)) > 0.45, SR // 4)[: int(dur * SR)]       # speech-like bursts
speech = (rng.standard_normal(int(dur * SR)) * 0.2 * env).astype(np.float32)
sp = td / "speech.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", str(sp)],
               input=speech.tobytes(), check=True)
HEAD, TOTAL = 7.0, dur + 7.0


def film(name, delay_s, total_s):
    p = td / name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x36:r=25:d={total_s}",
                    "-i", str(sp), "-filter_complex",
                    f"[1:a]adelay={int(delay_s * 1000)}|{int(delay_s * 1000)},apad=whole_dur={total_s},"
                    f"atrim=duration={total_s}[a]", "-map", "0:v", "-map", "[a]", "-c:v", "libx264",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(p)], check=True)
    return p


good = film("good.mp4", HEAD, TOTAL)
r = refused(lambda: tr.assert_audio_in_step(good, sp, HEAD, TOTAL))
check(r is None, "the speech at +7.0s in a film of the right length passes", r or "")
late = film("late.mp4", HEAD + 4.1, TOTAL)
check(refused(lambda: tr.assert_audio_in_step(late, sp, HEAD, TOTAL)) is not None,
      "CONTROL: the speech 4.1s late (EP56 cut 1) is refused")
long_ = film("long.mp4", HEAD, TOTAL + 6.9)
check(refused(lambda: tr.assert_audio_in_step(long_, sp, HEAD, TOTAL)) is not None,
      "CONTROL: audio 6.9s longer than the film is refused")

broken = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP56-Class-Improvement-and-Bias-Blues-Part-3"
                      r"\output\BROKEN-sound-4s-late_PP-EP56-cut1-before-end-frame.mp4")
# The broken render was set aside under this name on 12 Nov; the plain name is now the FIXED
# file, which this guard correctly passes — so pointing here at the plain name fails the test.
speech56 = sorted(broken.parent.parent.glob("renders/_pieces/_speech-*.wav"))
if broken.is_file() and speech56 and "cut1" in broken.name:
    msg = refused(lambda: tr.assert_audio_in_step(broken, speech56[0], 7.0, 519.529))
    check(msg is not None, "REAL: the broken EP56 cut 1 is refused", (msg or "")[:110])
else:
    print("  (the broken EP56 cut 1 is not on disk — the real-data control is skipped)")

fixed = broken.with_name("PP-EP56-cut1-before-end-frame.mp4")
if fixed.is_file() and speech56:
    msg = refused(lambda: tr.assert_audio_in_step(fixed, speech56[0], 7.0, 519.529))
    check(msg is None, "REAL: the re-finished EP56 cut 1 passes", (msg or "")[:110])

print(f"\naudio in step: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
