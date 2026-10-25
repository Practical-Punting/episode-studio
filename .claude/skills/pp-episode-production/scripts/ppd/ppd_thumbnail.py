#!/usr/bin/env python3
"""ppd_thumbnail.py — the PPD promo thumbnail AND title card (one design, two pages), 1280x720 layout.

    python ppd_thumbnail.py <job_dir>

Jodie's design, 25 Oct 2026 (asked one question at a time, after she saw the first cut):
  · TIMELESS — no "Cox Plate Day", no date;
  · the PPD Club logo BIG and CENTRAL (the PPD lockup: the red tick, PPD, Practical Punting Daily);
  · "+326% PROFIT" is the big part — much bigger than "$25 -> $106.50", which stays, small, underneath;
    ("profit", the brief's word: "326% return" can be read as 3.26x back);
  · Gordon DROPPED — all graphic;
  · the brief §6 hypothetical small print on the TITLE CARD ONLY, not the thumbnail.

Writes overlay/thumbnail/thumbnail.html -> output/PPD-PROMO-thumbnail.png (1280x720, < 2 MB, with a small-size
legibility sheet), and overlay/thumbnail/title.html (the same page + the small print), which
`ppd_promo.py <job> title` renders at 1.5x = 1920x1080 for the 7.0 s title head.
"""
import html as _h
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "fbx"))
import ppd_data as pdd  # noqa: E402
import fbx_thumbnail as ft  # noqa: E402

FONT_CSS = """@font-face{font-family:Raleway;src:url(assets/fonts/raleway-900.woff2) format('woff2');font-weight:900}
@font-face{font-family:Roboto;src:url(assets/fonts/roboto-400.woff2) format('woff2');font-weight:400}
@font-face{font-family:Roboto;src:url(assets/fonts/roboto-700.woff2) format('woff2');font-weight:700}
html,body{margin:0;padding:0;overflow:hidden}
body{width:1280px;height:720px;background:#1E1F22;position:relative;font-family:Roboto,sans-serif;color:#fff}
.a{position:absolute}
.c{left:0;width:1280px;display:flex;justify-content:center;align-items:center}
.r9{font-family:Raleway;font-weight:900;line-height:1;letter-spacing:-.015em;white-space:nowrap;font-variant-numeric:lining-nums}"""


def page(day, lockup_w, with_small_print):
    c = day["calc"]["win"]
    st, bk = pdd.money(c["staked"], 0), pdd.money(c["back"])
    pct = c["roi"][:-3] + "%"                      # "+326.0%" -> "+326%"
    arrow = ('<svg viewBox="0 0 120 60" style="width:58px;height:29px;margin:0 22px">'
             '<path d="M4 30H96" stroke="#C9CACC" stroke-width="12" stroke-linecap="round"/>'
             '<path d="M76 8L104 30L76 52" stroke="#C9CACC" stroke-width="12" fill="none" stroke-linecap="round" '
             'stroke-linejoin="round"/></svg>')
    top = 40 if with_small_print else 52           # the thumbnail has no small print, so it sits a touch lower
    # every declared face is used once, off screen, so the renderer's "all fonts loaded" guard is satisfied honestly
    body = ('<div class="a" style="left:-9999px"><span style="font-weight:400">Aa</span><span style="font-weight:700">Aa</span></div>'
            f'<div class="a c" style="top:{top}px"><img src="assets/ppd-lockup.png" alt="PPD Club" style="width:{lockup_w}px"></div>'
            f'<div class="a c r9" style="top:{top + 188}px;font-size:236px;color:#F44336">{pct}</div>'
            f'<div class="a c r9" style="top:{top + 418}px;font-size:66px;letter-spacing:.14em">PROFIT</div>'
            f'<div class="a c r9" style="top:{top + 512}px;font-size:44px;color:#C9CACC">{st}{arrow}{bk}</div>')
    if with_small_print:
        body += (f'<div class="a c" style="bottom:22px"><div style="width:1040px;text-align:center;font-size:12.5px;'
                 f'line-height:1.34;color:#8A8B8F">{_h.escape(day["small_print"])}</div></div>')
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>PPD promo {"title card" if with_small_print else "thumbnail"}'
            f'</title><style>{FONT_CSS}</style></head><body>{body}</body></html>')


def main():
    job = Path(sys.argv[1]).resolve()
    promo, day = pdd.load(job)
    work = job / "overlay" / "thumbnail"
    (work / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    cards = job / "overlay" / "cards" / "assets"
    for n in ("raleway-900.woff2", "roboto-400.woff2", "roboto-700.woff2"):
        shutil.copyfile(cards / "fonts" / n, work / "assets" / "fonts" / n)
    shutil.copyfile(job / promo["pack_dir"] / "logos" / "PPD-lockup-onDark-transparent@2x.png", work / "assets" / "ppd-lockup.png")
    (work / "thumbnail.html").write_text(page(day, 560, False), encoding="utf-8")
    (work / "title.html").write_text(page(day, 560, True), encoding="utf-8")
    (job / "output").mkdir(exist_ok=True)
    ft.render(work / "thumbnail.html", job / "output" / "PPD-PROMO-thumbnail.png",
              job / "output" / "qc" / "PPD-PROMO-thumbnail-small-sizes.png")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    import os
    os._exit(0)
