"""The bars card's PRINT figure keeps its highlighted bar orange (EP58, 14 Nov 2026).

    python engine/test_bars_print.py

`body.print .bar{background:#B4B4B4}` out-ranked `.bar.hi{background:#DA532C}`, so in the e-book the
bar a card singles out printed grey like the rest: EP58's C5 "10 out of 500" and C8 "Exactly 2/1"
lost their emphasis (the ratio block's fault, cf1cdd1, in another block). REAL CARD: EP58's C8 page
(re-authored from the fixed block) is rendered by build_figures into a temp folder and its orange
bars counted. CONTROL: the same page with the print rule for the highlight taken out shows none.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
BLOCK = HERE.parent / ".claude/skills/pp-episode-production/assets/cards/blocks/bars.html"
PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
RULE = "body.print .bar.hi{background:#DA532C}"
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def orange_bars(page_dir: pathlib.Path, epj: dict, card: str) -> int:
    """Horizontal bars: count tall-enough runs of orange ROWS in the bar column band."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="bars_fig_"))
    (d / "episode.json").write_text(json.dumps(dict(epj, figures=[{"n": 1, "card": card}]),
                                               ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "build_figures.py"), str(d / "episode.json"),
                    str(page_dir), str(d)], check=True, capture_output=True, timeout=300)
    img = np.asarray(Image.open(d / "figure-1.png").convert("RGB")).astype(int)
    orange = (abs(img[..., 0] - 0xDA) < 30) & (abs(img[..., 1] - 0x53) < 30) & (abs(img[..., 2] - 0x2C) < 30)
    # a bar is an UNBROKEN run of orange across a row (orange text has gaps between letters),
    # and stands tall (the eyebrow's dash is a thin line): count runs of such rows >= 2% high
    w = img.shape[1]
    longest = np.zeros(img.shape[0], int)
    for y in np.nonzero(orange.sum(axis=1) > w * 0.08)[0]:
        r = np.concatenate(([0], orange[y].astype(int), [0]))
        edges = np.flatnonzero(np.diff(r))
        longest[y] = int(np.max(edges[1::2] - edges[0::2]))
    rows = longest > w * 0.08
    n, run = 0, 0
    for v in list(rows) + [False]:
        if v:
            run += 1
        else:
            n += run >= img.shape[0] * 0.02
            run = 0
    return int(n)


check("the bars block carries the print rule for the highlighted bar", RULE in BLOCK.read_text(encoding="utf-8"))
ep = next(PP.glob("PP-EP58-*"), None)
if ep is not None:
    epj = json.loads((ep / "docs/episode.json").read_text(encoding="utf-8"))
    export = ep / "overlay/export"
    n = orange_bars(export, epj, "C8")
    check("EP58's C8 print figure shows ONE orange bar — 'Exactly 2/1'", n == 1, f"{n}")
    ctl = pathlib.Path(tempfile.mkdtemp(prefix="bars_ctl_")) / "export"
    shutil.copytree(export, ctl)
    page = next(ctl.glob("ep58-c08-*.html"))
    page.write_text(page.read_text(encoding="utf-8").replace(RULE, ""), encoding="utf-8")
    n0 = orange_bars(ctl, epj, "C8")
    check("CONTROL: without the rule the same page prints no orange bar (the fault)", n0 == 0, f"{n0}")

print(f"\nbars print: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
