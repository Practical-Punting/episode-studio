# Remove words from a cover PNG's baked-in footer line WITHOUT re-rendering
# text — splice the original pixels so the font matches exactly.
# Built for EP02: "A Practical Punting guide · Adapted from Barry Meadow ·
# practicalpunting.com.au"  ->  drop the credit.
#
# TWO STEPS (deliberate — segments are per-WORD, so guessing gets it wrong):
#   1. python fix_cover_footer.py <cover.png>
#        lists the numbered word-segments it found. Read them.
#   2. python fix_cover_footer.py <cover.png> <out.png> --keep 0-4,10
#        keeps those segment indices, drops the rest, closes the gap.
#        (EP02: 0-4 = "A Practical Punting guide ·", 10 = the URL.)
#
# ALWAYS open the _before_after.png it writes — a wrong --keep looks plausible
# in the terminal and obviously broken in the image.
import sys, pathlib
import numpy as np
from PIL import Image, ImageDraw

SRC = pathlib.Path(sys.argv[1])
im = Image.open(SRC).convert("RGB")
a = np.array(im).astype(int); H, W = a.shape[:2]

band_top = H - 250
band = a[band_top:H]
# grey ink only (the orange rule has R >> B, so it's excluded)
grey = (band.mean(axis=2) < 150) & (np.abs(band[:, :, 0] - band[:, :, 2]) < 40)
rows = np.nonzero(grey.sum(axis=1) > 5)[0]
r0, r1 = rows.min(), rows.max()
cols = np.nonzero(grey[r0:r1 + 1].sum(axis=0) > 0)[0]

segs, start, prev = [], cols[0], cols[0]
for c in cols[1:]:
    if c - prev > 12:
        segs.append((start, prev)); start = c
    prev = c
segs.append((start, prev))

print(f"footer rows {band_top+r0}-{band_top+r1}; {len(segs)} segments:")
for i, (s, e) in enumerate(segs):
    print(f"   [{i:>2}] cols {s:>5}-{e:<5} w={e-s+1}")

if len(sys.argv) < 3 or "--keep" not in sys.argv:
    print("\nNo --keep given. Re-run with e.g.:  --keep 0-4,10")
    sys.exit(0)

OUT = pathlib.Path(sys.argv[2])
spec = sys.argv[sys.argv.index("--keep") + 1]
keep = set()
for part in spec.split(","):
    if "-" in part:
        lo, hi = part.split("-"); keep.update(range(int(lo), int(hi) + 1))
    else:
        keep.add(int(part))
keep = sorted(k for k in keep if k < len(segs))
print(f"\nkeeping segments {keep}")

TOP, BOT = band_top + r0 - 13, band_top + r1 + 17
# lift each kept segment (with a little side padding) before we erase
pieces = [(k, im.crop((segs[k][0] - 6, TOP, segs[k][1] + 7, BOT))) for k in keep]
ImageDraw.Draw(im).rectangle([segs[0][0] - 10, TOP, W - 1, BOT], fill=(255, 255, 255))

# re-lay kept segments left-to-right, preserving each ORIGINAL inter-word gap
# where segments were adjacent, else using the median gap as the separator.
gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
median_gap = int(np.median(gaps))
x = segs[0][0] - 6
for n, (k, piece) in enumerate(pieces):
    im.paste(piece, (x, TOP))
    if n + 1 < len(pieces):
        nxt = pieces[n + 1][0]
        gap = (segs[nxt][0] - segs[k][1]) if nxt == k + 1 else median_gap
        x += piece.width - 13 + gap
im.save(OUT)
print(f"wrote {OUT.name}")

before = Image.open(SRC).convert("RGB").crop((0, H - 250, W, H))
after = im.crop((0, H - 250, W, H))
cmp = Image.new("RGB", (W, 508), "white")
cmp.paste(before, (0, 0)); cmp.paste(after, (0, 258))
cmp_path = OUT.with_name(OUT.stem + "_before_after.png")
cmp.save(cmp_path)
print(f"REVIEW THIS IMAGE: {cmp_path}")
