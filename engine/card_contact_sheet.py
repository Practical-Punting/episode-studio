#!/usr/bin/env python3
"""Render a pacing CONTACT SHEET for every card block — a filmstrip per block.

    python engine/card_contact_sheet.py <out_dir> [label]

One row per block, eight frames across the build, seeked (never played) so the frame at
1.2s really is the frame at 1.2s. 🔴 `render_card.py` SEEKS and screenshots; a rAF or
`setTimeout` counter previews perfectly and renders wrong — see [[pp-seek-versus-play-trap]].

It exists so a pacing change can be JUDGED BY EYE side by side rather than argued about
in milliseconds, which is the only way "is 280ms slow enough to read" can be answered.
"""
from __future__ import annotations

import functools
import io
import json
import pathlib
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(HERE / "testdata"))

import author_cards as ac                                        # noqa: E402
from golden_blocks import GOLDEN                                 # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

# The frames a pacing eye wants: dense through the build, then the settled card.
TICKS_MS = (200, 500, 800, 1100, 1500, 2000, 2500, 3500)
THUMB_W = 320


def author(stem: str, card: dict) -> str:
    blk = ac.load_block(stem)
    frame = ac.load_frame(card.get("layout", "fullscreen"))
    return ac.render_card(card, blk, frame)


def shoot(pages: dict[str, str], out_dir: pathlib.Path, label: str) -> pathlib.Path:
    from playwright.sync_api import sync_playwright

    work = out_dir / f"_pages-{label}"
    work.mkdir(parents=True, exist_ok=True)
    # 🔴 THE PAGE NEEDS ITS ENGINE BESIDE IT. The frame loads `pp-anim.js` with a
    # RELATIVE src, so a page served from a scratch directory without it never defines
    # `ppDuration` and the wait times out after thirty seconds looking like a hang.
    (work / "pp-anim.js").write_bytes(
        (SKILL.parent / "assets/pp-anim.js").read_bytes())
    for stem, html in pages.items():
        (work / f"{stem}.html").write_text(html, encoding="utf-8")

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(work))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]

    rows, durations = [], {}
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True, args=["--force-device-scale-factor=1"])
        pg = br.new_page(viewport={"width": 1920, "height": 1080})
        for stem in pages:
            pg.goto(f"http://127.0.0.1:{port}/{stem}.html?paused=1")
            pg.wait_for_function("window.ppDuration !== undefined", timeout=30000)
            durations[stem] = pg.evaluate("window.ppDuration")
            shots = []
            for ms in TICKS_MS:
                pg.evaluate(f"window.ppSeek({ms})")
                shots.append(Image.open(io.BytesIO(pg.screenshot())))
            rows.append((stem, shots))
        br.close()
    httpd.shutdown()

    tw = THUMB_W
    th = round(tw * 1080 / 1920)
    pad, head = 8, 30
    W = pad + len(TICKS_MS) * (tw + pad)
    H = head + len(rows) * (th + head)
    sheet = Image.new("RGB", (W, H), (22, 22, 22))
    d = ImageDraw.Draw(sheet)
    for i, ms in enumerate(TICKS_MS):
        d.text((pad + i * (tw + pad) + 4, 8), f"{ms}ms", fill=(235, 235, 235))
    y = head
    for stem, shots in rows:
        d.text((pad, y + 6), f"{stem}   ppDuration {durations[stem]}ms",
               fill=(218, 83, 44))
        y += head
        for i, im in enumerate(shots):
            sheet.paste(im.resize((tw, th)), (pad + i * (tw + pad), y))
        y += th
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"contact-{label}.png"
    sheet.save(dest)
    (out_dir / f"durations-{label}.json").write_text(
        json.dumps(durations, indent=1) + "\n", encoding="utf-8")
    return dest


def main() -> int:
    out = pathlib.Path(sys.argv[1])
    label = sys.argv[2] if len(sys.argv) > 2 else "now"
    pages = {}
    for stem, body in GOLDEN.items():
        card = dict(body, id=f"G-{stem}", block=stem,
                    layout=body.get("layout", "fullscreen"),
                    headline=body["headline_display"].replace("<br>", " ").upper())
        pages[stem] = author(stem, card)
    dest = shoot(pages, out, label)
    print(f"WROTE {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
