"""twoway_cards.chip_content_px: no card content under the film's corner chip (EP56 cut 3, 13 Nov 2026).

The chip now runs over every two-way card; C8's "ruler" bottom row lost the end of "At others" under it.
  (a) CONTROL, REAL: EP56's cut-2 C8 clip -> content under the chip (the fault as found)
  (b) REAL: EP56's C8 re-rendered with --keep-clear -> clear
  (c) REAL: EP56's title card (a photograph) -> a PICTURE page, not judged
  (d) CONTROL, SYNTHETIC: a flat charcoal card with a white bar inside the chip's box -> flagged
  (e) SYNTHETIC: the same card with the bar 30px above the chip's top -> clear
  (f) keep_clear_css lifts the card's bottom padding to the chip's top + the gap (derived, not typed)

Run: python engine/test_twoway_card_chip_clear.py
"""
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_cards as tc  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


x0, y0, x1, y1 = tc.chip_box()
print(f"chip box {x0},{y0} - {x1},{y1}")


def clip_from(arr, td, name):
    png, mp4 = pathlib.Path(td) / f"{name}.png", pathlib.Path(td) / f"{name}.mp4"
    Image.fromarray(arr).save(png)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-loop", "1", "-framerate", "25", "-i", str(png),
                    "-frames:v", "10", "-pix_fmt", "yuv420p", str(mp4)], check=True, timeout=120)
    return mp4


print("\n-- synthetic --")
with tempfile.TemporaryDirectory() as td:
    card = np.full((1080, 1920, 3), 31, np.uint8)
    card[100:250, 110:1400] = 240                      # a headline, well clear
    bad = card.copy()
    bad[930:980, 1300:1500] = 240                      # a label running under the chip
    px, bb = tc.chip_content_px(clip_from(bad, td, "bad"))
    check(px and px > tc.CHIP_MAX_PX, "(d) CONTROL: text under the chip is flagged", (px, bb))
    ok = card.copy()
    ok[y0 - 80:y0 - 30, 1300:1700] = 240               # the same label lifted 30px clear
    px, bb = tc.chip_content_px(clip_from(ok, td, "ok"))
    check(px == 0, "(e) the label lifted clear of the chip is clear", (px, bb))

print("\n-- real EP56 --")
C = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP56-Class-Improvement-and-Bias-Blues-Part-3\overlay\clips")
P = "ep56-c08-where-the-winners-come-from.mp4"
for label, f, want in (("(a) CONTROL: cut 2's C8 has content under the chip", C / "_cut2" / P, "bad"),
                       ("(b) C8 with --keep-clear is clear", C / P, "clear"),
                       ("(c) the title card is a picture page, not judged", C / "ep56-title-nologo.mp4", "picture")):
    if not f.is_file():
        print(f"  SKIP  {label} — {f.name} not on this machine")
        continue
    px, bb = tc.chip_content_px(f)
    got = "picture" if px is None else ("bad" if px > tc.CHIP_MAX_PX else "clear")
    check(got == want, label, (px, bb))

print("\n-- (f) the lift --")
css = tc.keep_clear_css()
check(f"padding-bottom:{1080 - y0 + tc.CHIP_CLEAR_GAP}px" in css, "padding = 1080 - chip top + gap", css)

print()
if fails:
    print(f"FAILED {len(fails)}: {fails}")
    raise SystemExit(1)
print("ALL PASS")
