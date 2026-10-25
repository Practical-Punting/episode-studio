#!/usr/bin/env python3
"""ppd_thumbnail.py — the PPD promo thumbnail (brief §10.3), 1280x720, under 2 MB. It is ALSO the title card:
`ppd_promo.py <job> title` renders this same page at 1.5x = 1920x1080 (Jodie's FBX ruling: promos open on a title
card "like the normal videos").

    python ppd_thumbnail.py <job_dir> <isnet.onnx> [--t SECONDS]

Charcoal, Gordon cut out on the right, "$25 -> $106.50" with the $106.50 big in PPD red, the red tick, the PPD
logo; small "Brought to you by [PP logo]". Gordon is a REAL frame of the HeyGen render (ppd-promo.json ->
thumbnail_frame, picked by looking: warm, lips together, eyes to camera), cut out locally with ISNet (Apache-2.0,
fbx_thumbnail.isnet_matte) — nothing generated, nothing uploaded. Placed by measuring his head, like the FBX ones.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "fbx"))
import ppd_data as pdd  # noqa: E402
import fbx_thumbnail as ft  # noqa: E402

FONT_CSS = """@font-face{font-family:Raleway;src:url(assets/fonts/raleway-900.woff2) format('woff2');font-weight:900}
@font-face{font-family:Roboto;src:url(assets/fonts/roboto-700.woff2) format('woff2');font-weight:700}
html,body{margin:0;padding:0;overflow:hidden}
body{width:1280px;height:720px;background:#1E1F22;position:relative;font-family:Roboto,sans-serif;color:#fff}
.a{position:absolute}
.r9{font-family:Raleway;font-weight:900;line-height:1;letter-spacing:-.015em;white-space:nowrap;font-variant-numeric:lining-nums}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("model")
    ap.add_argument("--t", type=float, default=None)
    ap.add_argument("--x", type=int, default=1010, help="thumbnail x of the centre of his head")
    ap.add_argument("--head-top", type=int, default=70)
    ap.add_argument("--head-w", type=int, default=214)
    a = ap.parse_args()
    job = Path(a.job).resolve()
    promo, day = pdd.load(job)
    t = a.t if a.t is not None else promo["thumbnail_frame"]
    work = job / "overlay" / "thumbnail"
    (work / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    cards = job / "overlay" / "cards" / "assets"
    for n in ("raleway-900.woff2", "roboto-700.woff2"):
        shutil.copyfile(cards / "fonts" / n, work / "assets" / "fonts" / n)
    for n in ("ppd-wordmark.png", "pp-logo-on-dark.svg"):
        shutil.copyfile(cards / n, work / "assets" / n)

    # the master is Gordon on his own (no chip, no zoom); fbx_thumbnail.cut_out crops round him and mattes him
    cut_w, hair_top, face_x = ft.cut_out(job / "renders" / "presenter-master.mp4", t, Path(a.model), work)
    head = np.asarray(Image.open(work / "gordon-cutout.png"))[:, :, 3][hair_top:hair_top + 220] > 128
    cols = np.flatnonzero(head.sum(axis=0) > 3)
    head_px = (cols[-1] - cols[0]) if cols.size else 300
    scale = a.head_w / head_px
    W = round(cut_w * scale)
    left = round(a.x - face_x * scale)
    top = round(a.head_top - hair_top * scale)

    c = day["calc"]["win"]
    st, bk = pdd.money(c["staked"], 0), pdd.money(c["back"])
    tick = ('<svg class="a" viewBox="0 0 100 100" style="left:{l}px;top:{t}px;width:{s}px;height:{s}px">'
            '<circle cx="50" cy="50" r="50" fill="#F44336"/><polyline points="27,52 43,68 74,33" fill="none" stroke="#fff" '
            'stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    arrow = ('<svg class="a" viewBox="0 0 120 60" style="left:{l}px;top:{t}px;width:120px;height:60px">'
             '<path d="M4 30H96" stroke="#F44336" stroke-width="12" stroke-linecap="round"/>'
             '<path d="M76 8L104 30L76 52" stroke="#F44336" stroke-width="12" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    body = (f'<img id="g" src="gordon-cutout.png" alt="" class="a" style="left:{left}px;top:{top}px;width:{W}px">'
            f'<img src="assets/ppd-wordmark.png" alt="Practical Punting Daily" class="a" style="left:46px;top:40px;height:58px">'
            f'<div class="a" style="left:58px;top:150px;display:flex;align-items:center;gap:16px;color:#F44336;font-weight:700;'
            f'letter-spacing:.22em;font-size:22px;white-space:nowrap"><span style="width:44px;height:5px;background:#F44336"></span>'
            f'{day["label"].upper()}</div>'
            f'<div class="r9 a" style="left:54px;top:196px;font-size:132px">{st}</div>'
            + arrow.format(l=318, t=232)
            + f'<div class="r9 a" style="left:50px;top:350px;font-size:172px;color:#F44336">{bk}</div>'
            + tick.format(l=60, t=560, s=96)
            + f'<div class="r9 a" style="left:176px;top:572px;font-size:72px">{c["roi"][:-3]}%</div>'
            f'<div class="a" style="left:180px;top:652px;font-weight:700;letter-spacing:.2em;font-size:16px;color:#8A8B8F;white-space:nowrap">'
            f'PROFIT · $5 A BET</div>')
    page = work / "thumbnail.html"
    page.write_text(f'<!doctype html><html><head><meta charset="utf-8"><title>PPD promo thumbnail</title>'
                    f'<style>{FONT_CSS}</style></head><body>{body}</body></html>', encoding="utf-8")
    (job / "output").mkdir(exist_ok=True)
    ft.render(page, job / "output" / "PPD-PROMO-thumbnail.png", job / "output" / "qc" / "PPD-PROMO-thumbnail-small-sizes.png")
    print(f"frame {t:.2f}s of presenter-master.mp4; head {head_px}px -> {a.head_w}px (scale {scale:.3f})")
    (work / "frame.json").write_text(json.dumps({"t": t, "head_px": int(head_px), "scale": scale}), encoding="utf-8")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    import os
    os._exit(0)
