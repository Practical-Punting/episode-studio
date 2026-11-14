"""The ratio card's PRINT figure keeps its winners orange (EP59, 14 Nov 2026).

    python engine/test_ratio_print.py

`body.print .m{background:#DADADA}` out-ranked `.m.win{background:#DA532C}`, so in the e-book the
nine winning meetings of EP59's C13 ("Net profits at nine of the 12 meetings") printed pale grey
and the three losers dark — the figure said 3 of 12. REAL CARD: EP59's C13 page (re-authored from
the fixed block) is rendered by build_figures into a temp folder and its bars counted by colour.
CONTROL: the same page with the print rule for winners taken out shows no orange bars.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
BLOCK = HERE.parent / ".claude/skills/pp-episode-production/assets/cards/blocks/ratio.html"
PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
RULE = "body.print .m.win{background:#DA532C}"
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def orange_bars(page_dir: pathlib.Path, epj: dict) -> int:
    d = pathlib.Path(tempfile.mkdtemp(prefix="ratio_fig_"))
    (d / "episode.json").write_text(json.dumps(dict(epj, figures=[{"n": 1, "card": "C13"}]),
                                               ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "build_figures.py"), str(d / "episode.json"),
                    str(page_dir), str(d)], check=True, capture_output=True, timeout=300)
    img = np.asarray(Image.open(d / "figure-1.png").convert("RGB")).astype(int)
    orange = (abs(img[..., 0] - 0xDA) < 30) & (abs(img[..., 1] - 0x53) < 30) & (abs(img[..., 2] - 0x2C) < 30)
    cols = orange.sum(axis=0) > img.shape[0] * 0.08          # a bar is a tall run of orange
    return int(np.sum(cols[1:] & ~cols[:-1]) + (1 if cols[0] else 0))


check("the ratio block carries the print rule for winners", RULE in BLOCK.read_text(encoding="utf-8"))
ep = next(PP.glob("PP-EP59-*"), None)
if ep is not None:
    epj = json.loads((ep / "docs/episode.json").read_text(encoding="utf-8"))
    export = ep / "overlay/export"
    n = orange_bars(export, epj)
    check("EP59's C13 print figure shows NINE orange bars — the nine winning meetings", n == 9, f"{n}")
    ctl = pathlib.Path(tempfile.mkdtemp(prefix="ratio_ctl_")) / "export"
    shutil.copytree(export, ctl)
    page = next(ctl.glob("ep59-c13-*.html"))
    page.write_text(page.read_text(encoding="utf-8").replace(RULE, ""), encoding="utf-8")
    n0 = orange_bars(ctl, epj)
    check("CONTROL: without the rule the same page prints no orange bars (the fault)", n0 == 0, f"{n0}")

print(f"\nratio print: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
