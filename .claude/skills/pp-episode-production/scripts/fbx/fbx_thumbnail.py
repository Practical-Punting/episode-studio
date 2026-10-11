#!/usr/bin/env python3
"""fbx_thumbnail.py — FBX thumbnails (visual brief §6), 1280x720, under 2 MB. Two layouts.

    weekly    python fbx_thumbnail.py weekly    <week_dir> <frame_s> <isnet.onnx>
    evergreen python fbx_thumbnail.py evergreen <out_dir> <frame_s> <isnet.onnx> --source <week_dir>

WEEKLY (approved W01, 11 Oct 2026): FBX charcoal, Gordon cut out on the right, the headline
"N WINNERS / FROM M" in Archivo 800 with the second line gold, the FBX logo small at top left.
EVERGREEN (Hugh, 11 Oct 2026: "something similar", FBX logo as the MAIN part, the Practical
Punting logo on it): charcoal, Gordon on the right, "WHAT IS" + the FBX logo big + a gold "?",
and "Brought to you by [PP logo]" bottom-left. No dates, no results — it must stay true for months.

THE FRAME is a real frame of a FINISHED FBX video, picked by the standing method
(assets/README.md "FRAME PICKING"): no card covering him, no blink, no mid-word mouth, a warm
closed-mouth smile with eyes to camera. The time is passed in; picking it is done by LOOKING.
THE CUT-OUT is ISNet "general use" (Apache-2.0, an ONNX file run locally with onnxruntime —
nothing generated, nothing uploaded). Gordon is placed by MEASURING the cut-out (top of his hair,
centre of his head), so a wide frame and a zoomed frame land the same way.

Writes <out>/FBX-…-thumbnail.png, <work>/{frame.png, gordon-cutout.png, thumbnail.html},
and <qc>/…thumbnail-small-sizes.png (how it reads at 120 px and 320 px wide).
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
FONT_CSS = """@font-face{font-family:Archivo;src:url(assets/fonts/Archivo-800.woff2) format('woff2');font-weight:800}
@font-face{font-family:Archivo;src:url(assets/fonts/Archivo-600.woff2) format('woff2');font-weight:600}
html,body{margin:0;padding:0;overflow:hidden}
body{width:1280px;height:720px;background:#1B2126;position:relative;font-family:Archivo,sans-serif;color:#F2F4F3}"""


def isnet_matte(img: Image.Image, model: Path) -> Image.Image:
    import onnxruntime as ort
    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    x = np.asarray(img.convert("RGB").resize((1024, 1024), Image.BICUBIC), np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([1.0, 1.0, 1.0], np.float32)
    pred = sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0, 0]
    pred = (pred - pred.min()) / max(pred.max() - pred.min(), 1e-6)
    return Image.fromarray((pred * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC)


def stage(work: Path, source_week: Path, pp_logo=False):
    (work / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    cards = source_week / "overlay" / "cards" / "assets"
    for n in ("Archivo-800.woff2", "Archivo-600.woff2"):
        shutil.copyfile(cards / "fonts" / n, work / "assets" / "fonts" / n)
    shutil.copyfile(cards / "fbx-logo-on-dark.svg", work / "assets" / "fbx-logo-on-dark.svg")
    if pp_logo:
        shutil.copyfile(cards / "pp-logo-on-dark.svg", work / "assets" / "pp-logo-on-dark.svg")


def cut_out(video: Path, t: float, model: Path, work: Path):
    """Frame t of the finished video -> gordon-cutout.png; returns (hair_top, face_x) in cut-out px."""
    frame = work / "frame.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                    str(frame)], check=True)
    im = Image.open(frame).convert("RGB")
    box = (380, 0, 1660, 1080)                      # around him, so he is large in the model's input
    crop = im.crop(box)
    m = np.asarray(isnet_matte(crop, model))
    # the PP logo chip (bottom-right of every Gordon shot) is not Gordon — keep it out of the cut-out
    m = m.copy()
    m[900 - 8:, 1452 - box[0] - 8:] = 0
    rgba = crop.copy()
    rgba.putalpha(Image.fromarray(m))
    rgba.save(work / "gordon-cutout.png")
    rows = np.flatnonzero((m > 128).sum(axis=1) > 20)
    hair_top = int(rows[0]) if rows.size else 40
    head = m[hair_top:hair_top + 220] > 128          # the head, not the shoulders
    face_x = float(np.nonzero(head)[1].mean()) if head.any() else crop.size[0] / 2
    return crop.size[0], hair_top, face_x


def render(page: Path, out: Path, qc_sheet: Path):
    sys.path.insert(0, str(HERE))
    import fbx_render
    fbx_render.still(page, out, 1280, 720)    # NOT render_still.py: it leaves LCD colour fringes on text
    size = out.stat().st_size
    if size >= 2 * 1024 * 1024:     # YouTube's limit — shrink losslessly, never by eye
        Image.open(out).convert("RGB").save(out, optimize=True)
        size = out.stat().st_size
    print(f"{out}  {size:,} bytes ({'under' if size < 2 * 1024 * 1024 else 'OVER'} 2 MB)")
    t = Image.open(out).convert("RGB")
    s120, s320 = t.resize((120, 68), Image.LANCZOS), t.resize((320, 180), Image.LANCZOS)
    sheet = Image.new("RGB", (120 * 4 + 20 + 320 * 2, 360), (255, 255, 255))
    sheet.paste(s120.resize((480, 272), Image.NEAREST), (0, 0))   # 120 px, blown up 4x to SEE it
    sheet.paste(s320.resize((640, 360), Image.NEAREST), (500, 0))
    qc_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(qc_sheet)
    print("small-size check ->", qc_sheet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("layout", choices=["weekly", "evergreen"])
    ap.add_argument("dir")
    ap.add_argument("t", type=float)
    ap.add_argument("model")
    ap.add_argument("--source", help="evergreen: the finished week folder the frame comes from")
    ap.add_argument("--x", type=int, default=1000, help="thumbnail x of the centre of his head")
    ap.add_argument("--head-top", type=int, default=56, help="thumbnail y of the top of his hair")
    ap.add_argument("--head-w", type=int, default=0, help="width of his head in the thumbnail (0 = layout default)")
    a = ap.parse_args()
    d = Path(a.dir).resolve()

    if a.layout == "weekly":
        source = d
        wk = json.loads((d / "overlay" / "fbx-week.json").read_text(encoding="utf-8"))
        name = f"FBX-{wk['week']}"
    else:
        source = Path(a.source).resolve()
        wk = json.loads((source / "overlay" / "fbx-week.json").read_text(encoding="utf-8"))
        name = "FBX-Evergreen"
    video = source / "output" / f"FBX-{wk['week']}-16x9.mp4"
    work = d / "overlay" / "thumbnail"
    stage(work, source, pp_logo=(a.layout == "evergreen"))
    cut_w, hair_top, face_x = cut_out(video, a.t, Path(a.model), work)

    # his head is measured, so scale by HEAD WIDTH: same size in the thumbnail whatever the framing
    head = np.asarray(Image.open(work / "gordon-cutout.png"))[:, :, 3][hair_top:hair_top + 220] > 128
    cols = np.flatnonzero(head.sum(axis=0) > 3)
    head_px = (cols[-1] - cols[0]) if cols.size else 300
    want = a.head_w or 228
    scale = want / head_px
    W = round(cut_w * scale)
    left = round(a.x - face_x * scale)
    top = round(a.head_top - hair_top * scale)
    gord = f'<img id="g" src="gordon-cutout.png" alt="" style="position:absolute;left:{left}px;top:{top}px;width:{W}px">'

    if a.layout == "weekly":
        won = len([s for s in wk["selections"] if s["finish"] == 1])
        body = (f'{gord}<img src="assets/fbx-logo-on-dark.svg" alt="FBX" style="position:absolute;left:56px;top:48px;height:58px">'
                f'<div style="position:absolute;left:60px;top:190px;width:84px;height:8px;background:#D9A441"></div>'
                f'<div style="position:absolute;left:56px;top:228px;font-weight:800;line-height:.96;letter-spacing:-.015em;'
                f'font-size:128px;white-space:nowrap">{won} WINNERS<br><span style="color:#D9A441">FROM {len(wk["selections"])}</span></div>')
    else:
        body = (f'{gord}'
                f'<div style="position:absolute;left:60px;top:118px;width:84px;height:8px;background:#D9A441"></div>'
                f'<div style="position:absolute;left:56px;top:150px;font-weight:800;line-height:1;letter-spacing:-.015em;'
                f'font-size:112px;white-space:nowrap">WHAT IS</div>'
                f'<img src="assets/fbx-logo-on-dark.svg" alt="FBX" style="position:absolute;left:56px;top:286px;height:176px;display:block">'
                # the "?" sits straight after the X — the logo image is wider than the letters
                # because FORM BEATER INDEX runs on under them (the X ends at ~74.7% of its width)
                f'<span style="position:absolute;left:{56 + round(176 * 201 / 64 * 0.747) + 12}px;top:302px;'
                f'font-weight:800;font-size:132px;line-height:1;color:#D9A441">?</span>'
                f'<div style="position:absolute;left:60px;bottom:52px;display:flex;align-items:center;gap:18px;color:#C3CBD1;'
                f'font-weight:600;letter-spacing:.22em;font-size:17px;white-space:nowrap"><span>BROUGHT TO YOU BY</span>'
                f'<img src="assets/pp-logo-on-dark.svg" alt="Practical Punting" style="height:44px"></div>')
    page = work / "thumbnail.html"
    page.write_text(f'<!doctype html><html><head><meta charset="utf-8"><title>{name} thumbnail</title>'
                    f'<style>{FONT_CSS}</style></head><body>{body}</body></html>', encoding="utf-8")
    (d / "output").mkdir(exist_ok=True)
    render(page, d / "output" / f"{name}-thumbnail.png", d / "output" / "qc" / f"{name}-thumbnail-small-sizes.png")
    print(f"frame {a.t:.2f}s of {video.name}; head {head_px}px -> {want}px (scale {scale:.3f})")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    import os
    os._exit(0)   # the still renderer leaves Chromium open; closing it hangs on this machine
