# Render e-book figures straight from the motion-graphic CARD HTML (one design,
# two uses — per docs/PP-EPISODE-JSON-SPEC.md figures[]). Each figure is the print
# variant of its mapped card, rendered at 2x. No separate illustration art.
#
#   python build_figures.py <episode.json> <cards_html_dir> <ebook_out_dir> [--scale 2]
#
# For each figures[] {n, card}: find the card's HTML in cards_html_dir (matched by
# card id, case-insensitive substring), load it with ?print=1 (the card scaffold's
# light print theme), screenshot the .card element at the given scale, and write
# <ebook_out_dir>/NN-<card>@2x.png.  Cards authored with the standing print block
# (see the skill 'Card print mode' note) render light/print-ready; cards without it
# render as-is (flagged).
import base64, functools, glob, json, os, sys, threading, pathlib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

EPJ, HTML_DIR, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SCALE = 2
if "--scale" in sys.argv:
    SCALE = int(sys.argv[sys.argv.index("--scale") + 1])

EP = json.load(open(EPJ, encoding="utf-8"))
figs = EP.get("figures", [])
if not figs:
    print("no figures[] in episode.json — nothing to do"); sys.exit(0)
pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)

import re as _re
def resolve(card_id):
    cid = card_id.lower()
    files = glob.glob(os.path.join(HTML_DIR, "*.html"))
    kwmap = {"title": "title", "endcard": "end", "warranty": "warranty"}   # standing cards
    if cid in kwmap:
        for p in files:
            if kwmap[cid] in os.path.basename(p).lower():
                return p
    m = _re.match(r"c(\d+)$", cid)                                          # content cards: match by number (C3<->c03)
    if m:
        num = int(m.group(1))
        for p in files:
            if any(int(t) == num for t in _re.findall(r"c(\d+)", os.path.basename(p).lower())):
                return p
    for p in files:                                                        # fallback: substring
        if cid in os.path.basename(p).lower():
            return p
    return None

handler = functools.partial(SimpleHTTPRequestHandler, directory=os.path.abspath(HTML_DIR))
handler.log_message = lambda *a, **k: None
httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_address[1]

from playwright.sync_api import sync_playwright
done, warn = 0, []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--force-color-profile=srgb", "--hide-scrollbars"])
    for fig in figs:
        n, cid = fig["n"], fig["card"]
        html = resolve(cid)
        if not html:
            warn.append(f"figure {n}: no HTML found for card {cid}"); continue
        page = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=SCALE)
        page.goto(f"http://127.0.0.1:{PORT}/{quote(os.path.basename(html))}?print=1&paused=1", wait_until="load")
        try: page.wait_for_function("document.fonts.status === 'loaded'", timeout=30000)
        except Exception: pass
        # seek animations to their END state — ?paused=1 freezes them at t=0 (all hidden)
        try:
            page.wait_for_function("typeof window.ppDuration === 'number'", timeout=8000)
            page.evaluate("if (window.ppSeek) ppSeek(window.ppDuration)")
        except Exception: pass
        page.wait_for_timeout(200)
        is_print = page.evaluate("document.querySelector('.card') && document.querySelector('.card').classList.contains('print')")
        if not is_print:
            warn.append(f"figure {n} ({cid}): card has no print theme — rendered as-is (add the print block for a light figure)")
        el = page.query_selector(".card") or page
        out = os.path.join(OUT, f"figure-{n}.png")
        el.screenshot(path=out)
        page.close(); done += 1
        print(f"figure {n}: {os.path.basename(html)} -> {os.path.basename(out)}")
    import os as _o; _o._exit(0) if False else None
print(f"DONE: {done}/{len(figs)} figures rendered")
for w in warn: print("  !", w)
