#!/usr/bin/env python3
"""twoway_cards.py — render a two-way's card pages WITHOUT their own logo, and prove it.

    python engine/twoway_cards.py <ep_number> <page.html> [<page.html> ...]
                                  [--as PAGE=OUT.mp4]

🔴 WHY A TWO-WAY'S CARDS CARRY NO LOGO. The film's big 428x140 corner chip runs over the
WHOLE two-way, cards included (Jodie, 27 Sep 2026), so a card's own 214x65 mark would sit
under it in the same corner — two logos. EP49's cards and its no-logo early-CTA copy were
made BY HAND, and nothing could make the next episode's. This is that, as a tool.

HOW: each page is copied beside itself with one rule injected —
`#logo,.logo{display:none!important}` — and both versions are rendered by the SAME
`render_cards_batch.py` the single-presenter engine uses. The page itself is never edited:
the e-book figures and any later render still get the logo.

🔴 AND IT PROVES EVERY CLIP, BECAUSE A HIDE THAT HIDES NOTHING LOOKS EXACTLY LIKE SUCCESS.
The final frames of the two renders are compared: they must differ (something was hidden),
the difference must be logo-sized, and it must sit in the bottom-right corner — and
NOTHING else on the card may have moved. Anything else HALTS and nothing is promoted.

Outputs: overlay/clips/<stem>.mp4 (no logo — what the two-way uses) and
overlay/clips/with-logo/<stem>.mp4 (the control, kept, as EP49's were). `--as` names the
no-logo output instead (the early CTA: end-card-template.html -> end-card-template-nologo.mp4,
leaving the tail's own end-card-template.mp4 untouched).
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ep_paths                                                    # noqa: E402

HIDE = "<style data-twoway-nologo>#logo,.logo{display:none!important}</style>"
CORNER = (1400, 850)          # the logo's corner: every PP card puts it bottom-right
MIN_DIFF_PX = 300             # a 214x65 mark is ~13,900 px; under 300 nothing was hidden
MAX_OUTSIDE_MAD = 0.5         # grey levels: the rest of the card must not move at all


class Halt(Exception):
    pass


def nologo_copy(page: pathlib.Path, tmpname: str) -> pathlib.Path:
    src = page.read_text(encoding="utf-8")
    if 'id="logo"' not in src and 'class="logo"' not in src:
        raise Halt(f"{page.name} has no #logo/.logo element, so there is nothing to hide "
                   f"and no way to prove the hide worked.")
    if "</head>" not in src:
        raise Halt(f"{page.name} has no </head>; the hide rule has nowhere to go.")
    out = page.with_name(tmpname)
    out.write_text(src.replace("</head>", HIDE + "</head>", 1), encoding="utf-8")
    return out


def batch(served: pathlib.Path, out_dir: pathlib.Path, names: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(SCRIPTS / "render_cards_batch.py"),
                        str(served), str(out_dir), "0.5", *names],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=7200)
    if r.returncode:
        raise Halt("render_cards_batch failed:\n" + (r.stderr or r.stdout)[-1200:])


def last_frame(clip: pathlib.Path):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-sseof", "-0.1", "-i", str(clip),
                        "-frames:v", "1", "-update", "1", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True, timeout=300)
    a = np.frombuffer(r.stdout, np.uint8)
    if a.size != 1920 * 1080:
        raise Halt(f"could not read the last frame of {clip.name}")
    return a.reshape(1080, 1920).astype(int)


def prove(with_logo: pathlib.Path, no_logo: pathlib.Path) -> str:
    import numpy as np
    a, b = last_frame(with_logo), last_frame(no_logo)
    diff = np.abs(a - b) > 12
    n = int(diff.sum())
    if n < MIN_DIFF_PX:
        raise Halt(f"{no_logo.name}: its last frame is the same as the with-logo render "
                   f"({n} px differ). The hide hid nothing — the logo is still there.")
    ys, xs = np.nonzero(diff)
    x0, y0 = int(xs.min()), int(ys.min())
    if x0 < CORNER[0] or y0 < CORNER[1]:
        raise Halt(f"{no_logo.name}: hiding the logo changed pixels at ({x0},{y0}), "
                   f"outside the bottom-right corner — something other than the logo moved.")
    outside = np.ones_like(diff)
    outside[CORNER[1]:, CORNER[0]:] = False
    mad = float(np.abs(a - b)[outside.astype(bool)].mean())
    if mad > MAX_OUTSIDE_MAD:
        raise Halt(f"{no_logo.name}: the card away from the logo differs by {mad:.2f} grey "
                   f"levels from the with-logo render — the layout changed when it should not.")
    return (f"{no_logo.name}: logo gone ({n:,} px in x{x0}+ y{y0}+), rest of the card "
            f"unchanged (MAD {mad:.2f})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--as", dest="rename", action="append", default=[],
                    help="PAGE=OUT.mp4 — name the no-logo clip for that page")
    a = ap.parse_args()
    d = ep_paths.episode_dir(a.ep_number)
    export, clips = d / "overlay/export", d / "overlay/clips"
    rename = dict(x.split("=", 1) for x in a.rename)
    pages = [export / p for p in a.pages]
    missing = [p.name for p in pages if not p.is_file()]
    if missing:
        raise Halt(f"no such page(s) in overlay/export: {missing}")

    tmps = []
    try:
        for p in pages:
            tmps.append(nologo_copy(p, f"_nologo_{p.name}"))
        with tempfile.TemporaryDirectory(dir=str(clips.parent)) as td:
            td = pathlib.Path(td)
            print(f"rendering {len(pages)} page(s) with their logo (the control) ...",
                  flush=True)
            batch(export, td / "with", [p.name for p in pages])
            print(f"rendering {len(pages)} page(s) WITHOUT their logo ...", flush=True)
            batch(export, td / "without", [t.name for t in tmps])
            done = []
            for p in pages:
                w = td / "with" / f"{p.stem}.mp4"
                n = td / "without" / f"_nologo_{p.stem}.mp4"
                print("  " + prove(w, n), flush=True)
                done.append((p, w, n))
            # promote only after EVERY clip has been proved
            (clips / "with-logo").mkdir(parents=True, exist_ok=True)
            for p, w, n in done:
                dest = clips / rename.get(p.name, f"{p.stem}.mp4")
                shutil.copy2(n, dest)
                if p.name not in rename:
                    shutil.copy2(w, clips / "with-logo" / f"{p.stem}.mp4")
                print(f"  -> {dest.relative_to(d)}", flush=True)
    finally:
        for t in tmps:
            t.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Halt as e:
        print(f"\nHALT: {e}", file=sys.stderr)
        raise SystemExit(2)
