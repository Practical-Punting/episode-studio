"""twoway_render.logo_scores / logo_presence: is the standing corner chip IN THE FINISHED FILE?

EP56 cut 1 and cut 2 went to review with NO corner chip in a single frame while the render log
said "corner logo on from 7.0s" (found 13 Nov 2026). This is the detector the finish now runs
(`assert_logo_throughout`). CLAUDE.md 4b/4c: watch it FAIL first, and attack the statistic.

FIXTURES (built from the real asset, over a busy background):
  (a) the chip composited at its own alpha -> PRESENT
  (b) CONTROL: no chip -> absent
  (c) CONTROL: a plain charcoal card (31,31,31) where the chip would be -> absent
  (d) CONTROL: a ghost — the chip at HALF its alpha -> absent
  (e) CONTROL: the chip moved 12px left -> absent
  (f) CONTROL: a flat field of the chip's own mean colour -> absent
REAL FILES (skipped, and said so, if the Drive is not mounted):
  (g) CONTROL: EP56 cut 2, 8-60s -> absent in EVERY sample (the fault Jodie saw)
  (h) EP55 as approved, 8-60s -> present in every sample
  (i) EP54 (single presenter, published), 20-40s -> present: same asset, same place, same size

Run: python engine/test_twoway_logo_presence.py
"""
import pathlib
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_render as tr  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


geo = tr.corner_logo({})
asset = np.array(Image.open(geo["src"]).convert("RGBA"))
h, w = asset.shape[:2]
rng = np.random.default_rng(56)
yy, xx = np.mgrid[0:h, 0:w]
bg = np.clip(np.stack([60 + 90 * xx / w, 120 + 60 * yy / h, 90 + 0 * xx], -1) + rng.normal(0, 18, (h, w, 3)),
             0, 255)


def comp(base, alpha_scale=1.0, dx=0):
    a = np.roll(asset, dx, axis=1).astype(float)
    al = (a[..., 3:4] / 255.0) * alpha_scale
    return np.clip(a[..., :3] * al + base * (1 - al), 0, 255).astype(np.uint8)


def present(patch):
    r, wh = tr.logo_scores(patch, asset)
    return r <= tr.LOGO_MAD_MAX and wh <= tr.LOGO_MAD_MAX, (round(r, 1), round(wh, 1))


print("\n-- fixtures --")
ok, s = present(comp(bg))
check(ok, "(a) the chip at its own alpha is PRESENT", s)
ok, s = present(bg.astype(np.uint8))
check(not ok, "(b) CONTROL: no chip -> absent", s)
ok, s = present(np.full((h, w, 3), 31, np.uint8))
check(not ok, "(c) CONTROL: a charcoal card -> absent", s)
ok, s = present(comp(bg, 0.5))
check(not ok, "(d) CONTROL: a half-strength ghost -> absent", s)
ok, s = present(comp(bg, 1.0, -12))
check(not ok, "(e) CONTROL: the chip 12px out of place -> absent", s)
mean = (asset[..., :3].astype(float) * (asset[..., 3:4] / 255.0)).sum((0, 1)) / (asset[..., 3] / 255.0).sum()
ok, s = present(np.broadcast_to(mean, (h, w, 3)).astype(np.uint8))
check(not ok, "(f) CONTROL: a field of the chip's mean colour -> absent", s)

print("\n-- real files --")
PP = pathlib.Path(r"G:\My Drive\PP Videos")
real = [
    ("(g) CONTROL: EP56 cut 2 has NO chip", PP / "PP-EP56-Class-Improvement-and-Bias-Blues-Part-3/output/PP-EP56-cut2.mp4",
     8.0, 60.0, False),
    ("(h) EP55 as approved has the chip", PP / "PP-EP55-Is-the-Trainer-So-Important-Part-2/output/"
     "PP-EP55-The-Fundamentals-of-Handicapping-Part-2-Is-the-Trainer-So-Important.mp4", 8.0, 60.0, True),
    ("(i) EP54 (single presenter, published) has the same chip in the same place", PP /
     "PP-EP54-Getting-together-with-the-international-experts-Part-6/output/"
     "PP-EP54-Getting-together-with-the-international-experts-Part-6-FINAL.mp4", 20.0, 40.0, True),
]
for label, f, a, b, want in real:
    if not f.is_file():
        print(f"  SKIP  {label} — {f.name} not on this machine")
        continue
    got = tr.logo_presence(f, geo, a, b)
    n = sum(r["present"] for r in got)
    check(len(got) > 0 and all(r["present"] == want for r in got),
          f"{label}: {n} of {len(got)} samples present",
          f"icon {min(r['red'] for r in got)}-{max(r['red'] for r in got)}, "
          f"lettering {min(r['white'] for r in got)}-{max(r['white'] for r in got)}")

print()
if fails:
    print(f"FAILED {len(fails)}: {fails}")
    raise SystemExit(1)
print("ALL PASS")
