"""Every image a page asks for must exist. A page that references a missing file
renders ALT TEXT on a grey box, and nothing downstream notices.

THE FAULT THIS EXISTS TO STOP (EP15, 4 August 2026 — the third time in one day)
------------------------------------------------------------------------------
Nine artefacts were quarantined because they had been composed from a rejected cover
hero. Two were never put back: `ebook/cover.png` and `overlay/export/ebook-cover.png`.
Everything that consumed them was then built INTO THE HOLE:

  · `end-card-template.html` renders `<img src="ebook-cover.png">` — the finished film
    showed a grey rectangle with the browser's alt text, reading "The Practical Punting
    Guide — Killer Strategies for the Trifecta", which is not even this episode's title.
    The clip came out 120,789 bytes; with the photo in it, 798,050.
  · The e-book's `<img src="cover.png">` — page 1 of the shipped PDF was BLANK WHITE.

EVERY EXISTING CHECK PASSED. `card_check` measures layout collisions, not whether an
`<img>` resolves. `self_qc` PASSED the video twice. The end card was even confirmed
visible — "end card visible at the e-book beat (luma 33)" — because a grey box has a
luma. **The instruments were all asking about the wrong thing.**

WHY A GENERAL CHECK AND NOT ANOTHER SPECIAL ONE
-----------------------------------------------
`assert_standing_assets()` names the standing pages. `stage_title_hero()` names the
title hero. Both are lists of things someone thought of, and this file was on neither.
So this asks the only question that generalises: **for every page, does every image it
references exist on disk?** It needs no list and cannot go stale as pages are added.

Same shape as the title card that rendered onto flat black eight hours earlier — that
one was ALSO a staged image missing from `overlay/export`, and a list-based guard did
not cover it either.

USAGE
    python check_page_images.py <dir>            # exit 1 and name every broken ref
    python check_page_images.py <dir> --quiet    # print only failures
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

# src="..." / src='...' on any tag, plus CSS url(...) — both put a file on the page.
SRC = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""", re.I)
CSS_URL = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.I)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"}


def _is_local_image(ref: str) -> bool:
    """Skip anything we cannot check: remote URLs, data: URIs, template holes."""
    ref = ref.strip()
    if not ref or ref.startswith(("data:", "#", "//")):
        return False
    if urlparse(ref).scheme in ("http", "https", "file"):
        return False
    if "{{" in ref or "${" in ref:            # an unrendered template slot
        return False
    return Path(unquote(ref.split("?")[0].split("#")[0])).suffix.lower() in IMAGE_SUFFIXES


def scan_page(page: Path) -> list[tuple[str, Path]]:
    """Return [(reference, resolved path)] for every local image that is MISSING."""
    text = page.read_text(encoding="utf-8", errors="replace")
    refs = {m.group(1) for m in SRC.finditer(text)} | {m.group(1) for m in CSS_URL.finditer(text)}
    bad = []
    for ref in sorted(refs):
        if not _is_local_image(ref):
            continue
        rel = unquote(ref.split("?")[0].split("#")[0]).lstrip("/")
        resolved = (page.parent / rel).resolve()
        if not resolved.is_file():
            bad.append((ref, resolved))
    return bad


def scan_dir(d: Path) -> dict[Path, list[tuple[str, Path]]]:
    """Every .html in d (non-recursive — one export folder, one flat set of pages)."""
    return {p: bad for p in sorted(d.glob("*.html")) if (bad := scan_page(p))}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-3].strip())
        return 2
    d = Path(argv[1])
    quiet = "--quiet" in argv
    if not d.is_dir():
        print(f"not a directory: {d}")
        return 2

    pages = sorted(d.glob("*.html"))
    broken = scan_dir(d)
    if not broken:
        if not quiet:
            print(f"ok: {len(pages)} page(s) in {d.name}; every image they reference exists")
        return 0

    print(f"BROKEN IMAGE REFERENCES in {d}")
    print()
    for page, bad in broken.items():
        print(f"  {page.name}")
        for ref, resolved in bad:
            print(f"      <img src=\"{ref}\"> -> {resolved}  MISSING")
    print()
    n = sum(len(v) for v in broken.values())
    print(f"{n} missing image(s) across {len(broken)} page(s).")
    print("A page that cannot find its image renders ALT TEXT on a grey box, and every")
    print("downstream check still passes — the clip has a duration, the video has a luma.")
    print("Put the file back before rendering. Retrying without it will not help.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
