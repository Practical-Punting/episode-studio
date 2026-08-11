#!/usr/bin/env python3
"""web_copies.py — low-res web copies of the two pictures Hugh puts on the website.

    python web_copies.py <episode_dir>

Writes exactly TWO files into the episode's output/ folder and touches nothing else:

    PP-EPnn-thumbnail-lowres.jpg   from output/PP-EPnn-thumbnail.png
    PP-EPnn-cover-lowres.jpg       from ebook/cover.png

    LONGEST EDGE ~640px, aspect preserved, JPEG, target under ~100KB.

🔒 IT IS ADDITIVE AND THAT IS THE WHOLE CONTRACT (Jodie, 11 Aug 2026).
The full-size thumbnail, the cover, the e-book and everything else already in
output/ and ebook/ are READ and never written. This script opens exactly two paths
for writing, both of them new names, and `test_web_copies.py` hashes the entire
episode folder before and after to prove nothing else moved by a byte.

⚠️ .jpg IS LOAD-BEARING, NOT A PREFERENCE. `qc_episode.py` finds the thumbnail with
`glob("output/*thumbnail*.png")` and takes the LAST match, then fails the build if it
is not 1280x720. A file called `…-thumbnail-lowres.png` would sort after the real one,
become "the thumbnail" for QC, and hard-fail every episode at 640x360. The extension
is what keeps this addition out of every existing glob — `*.pdf`, `*youtube*.txt` and
`*thumbnail*.png` are the three that scan these folders, and .jpg matches none.

THE SOURCE FOR THE COVER IS ebook/cover.png — the cover IMAGE only. Not the PDF, not
a page rendered out of it, and not `overlay/export/ebook-cover.png`, which is the same
picture staged for the end card and would drift the day one of them is regenerated
without the other.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PIL import Image

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        pass

LONGEST_EDGE = 640
QUALITY = 82
SIZE_TARGET = 100_000          # ~100KB, Jodie's starting default
QUALITY_FLOOR = 70             # below this the picture is being mangled, so stop


class Halt(Exception):
    """A build-stopping problem, phrased for a human."""


def episode_slug(ep_dir: Path) -> str:
    """'PP-EP20' from the folder name, however the folder is suffixed.

    Read off the DIRECTORY rather than passed in, because the stage-8 close-out
    renames published folders and a caller holding an old name would write the
    files under it.
    """
    m = re.match(r"(PP-EP\d+)", ep_dir.name)
    if not m:
        raise Halt(f"{ep_dir.name!r} is not an episode folder — expected a name "
                   f"starting 'PP-EPnn', so there is no episode number to name these "
                   f"files after.")
    return m.group(1)


def shrink(src: Path, dst: Path) -> str:
    """One picture, resized and written. Returns a line for the run log."""
    with Image.open(src) as im:
        w, h = im.size
        scale = LONGEST_EDGE / max(w, h)
        # NEVER UPSCALE. A source already smaller than the target is copied at its
        # own size rather than blown up into a soft, bigger file.
        size = (w, h) if scale >= 1 else (max(1, round(w * scale)),
                                          max(1, round(h * scale)))
        im = im.convert("RGB").resize(size, Image.LANCZOS) if size != (w, h) \
            else im.convert("RGB")
        q = QUALITY
        while True:
            im.save(dst, "JPEG", quality=q, optimize=True, progressive=True)
            n = dst.stat().st_size
            if n <= SIZE_TARGET or q <= QUALITY_FLOOR:
                break
            q -= 4
    note = ""
    if n > SIZE_TARGET:
        # SAY SO rather than grind the quality down until it fits. A picture for a
        # website is allowed to be 110KB; a picture at quality 40 is not.
        note = (f"  ⚠️ still {n/1000:.0f}KB at the quality floor {QUALITY_FLOOR} — "
                f"over the ~{SIZE_TARGET//1000}KB target, and left legible on purpose")
    elif q != QUALITY:
        note = f"  (quality stepped {QUALITY} -> {q} to reach the size target)"
    return (f"{dst.name}  {size[0]}x{size[1]}, {n/1000:.0f}KB, q{q}"
            f"  <- {src.name} ({w}x{h})" + note)


def targets(ep_dir: Path) -> list[tuple[Path, Path]]:
    """(source, destination) for each copy. Sources are READ ONLY."""
    slug = episode_slug(ep_dir)
    out = ep_dir / "output"
    return [
        (out / f"{slug}-thumbnail.png", out / f"{slug}-thumbnail-lowres.jpg"),
        (ep_dir / "ebook/cover.png", out / f"{slug}-cover-lowres.jpg"),
    ]


def build(ep_dir: Path) -> list[str]:
    pairs = targets(ep_dir)
    missing = [s for s, _ in pairs if not s.is_file()]
    if missing:
        raise Halt(
            "the low-res web copies need the full-size pictures and they are not "
            "there yet:\n" + "\n".join(f"  - {p}" for p in missing)
            + "\nThis step runs AFTER the thumbnail and the e-book cover are built; "
              "if it has run early, that is an ordering fault, not a missing file.")
    (ep_dir / "output").mkdir(parents=True, exist_ok=True)
    return [shrink(s, d) for s, d in pairs]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("episode_dir")
    a = ap.parse_args(argv)
    for line in build(Path(a.episode_dir)):
        print(f"  + {line}")
    print("web copies: 2 file(s) written, nothing else touched")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Halt as e:
        print(f"WEB COPIES HALTED — {e}", file=sys.stderr)
        sys.exit(2)
