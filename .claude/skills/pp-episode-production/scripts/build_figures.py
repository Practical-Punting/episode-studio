# Render e-book figures straight from the motion-graphic CARD HTML (one design,
# two uses — per docs/PP-EPISODE-JSON-SPEC.md figures[]). Each figure is the print
# variant of its mapped card, rendered at 2x. No separate illustration art.
#
#   python build_figures.py <episode.json> <cards_html_dir> <ebook_out_dir> [--scale 2]
#
# For each figures[] {n, card}: find the card's HTML in cards_html_dir (matched by
# card id, case-insensitive substring), load it with ?print=1 (the card scaffold's
# light print theme), screenshot the card's OUTER BOX at the given scale, and write
# <ebook_out_dir>/figure-<n>.png.
#
# TWO BUGS FIXED 28 JUL 2026 — both had been wrong on every figure of every episode.
#
# 1. THE PRINT CHECK LOOKED IN THE WRONG PLACE, AND CHECKED THE WRONG THING.
#    It tested `.card.print`, the scaffold the SKILL documented. Not one shipped
#    card puts the class there — every card in the corpus, and both frame templates
#    the library emits, put it on `body` (`body.print .card{...}`). So `is_print`
#    was false for EVERY figure and the script printed "no print theme" twelve
#    times an episode while the figures were in fact correct. A warning that is
#    always wrong is worse than no warning: it trains you to skip the output.
#    It now asks the question that actually matters — DID THE FIGURE COME OUT LIGHT?
#    A dark figure is the real defect (a charcoal rectangle in a print book), and
#    it is caught by measuring the rendered background, not by naming a class. So
#    the check no longer depends on WHERE the switch lives, only on whether it worked.
#
# 2. THE SELECTOR MISSED PANEL-PUSH CARDS ENTIRELY.
#    It screenshot `.card`, which panel-push cards do not have — their box is
#    `.panel`, inset left:120 top:96 inside a 1920x1080 page. `query_selector`
#    returned None and the code fell through to `page`, so those figures were
#    shot as the WHOLE PAGE and shipped with ~188px of extra white surround the
#    other figures do not have. Measured on EP12's published book: figures 1 and 3
#    (fullscreen) start their ink at x=220, figures 2 and 4 (panel-push) at x=408.
#    EP11/EP12 are published and are NOT being re-rendered.
import functools, glob, json, os, sys, threading, pathlib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

for _s in (sys.stdout, sys.stderr):        # the Windows console is cp1252
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                      # noqa: BLE001
        pass

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

class _Quiet(SimpleHTTPRequestHandler):
    # Silencing was set on the functools.partial, which is not the handler class, so
    # every asset fetch was logged and buried the figure report in the engine log.
    def log_message(self, *a, **k):
        pass


handler = functools.partial(_Quiet, directory=os.path.abspath(HTML_DIR))
httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_address[1]

from playwright.sync_api import sync_playwright

# The card's outer box, in the order a card may declare it. `.card` is the
# fullscreen frame; `.panel` is the panel-push frame's inset rounded box. A card
# has exactly one of the two — there is no card in the corpus with neither, so
# finding neither is a real problem and says so rather than shooting the page.
BOX_SELECTORS = (".card", ".panel")

# Is the rendered figure LIGHT? This replaces a class-name test that was wrong on
# every card. Luminance of the box's own background, sampled after the print switch
# has run: anything below this is a dark card, which in a print book means a
# charcoal rectangle on white paper. 0.6 sits well clear of both real values —
# #fff is 1.0, #1F1F1F is 0.12.
PRINT_MIN_LUMA = 0.6

JS_BOX = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el);
  const m = cs.backgroundColor.match(/[\\d.]+/g) || [];
  const [r, g, b] = m.slice(0, 3).map(Number);
  const lin = (c) => { c = c / 255; return c <= 0.03928 ? c / 12.92
                       : Math.pow((c + 0.055) / 1.055, 2.4); };
  return {
    bg: cs.backgroundColor,
    luma: (m.length < 3) ? null : 0.2126*lin(r) + 0.7152*lin(g) + 0.0722*lin(b),
    printed: document.body.classList.contains('print') || el.classList.contains('print'),
    w: Math.round(el.getBoundingClientRect().width),
    h: Math.round(el.getBoundingClientRect().height),
  };
}"""

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

        # THE CARD'S OWN BOX — `.card` (fullscreen) or `.panel` (panel-push).
        el, box, sel = None, None, None
        for cand in BOX_SELECTORS:
            box = page.evaluate(JS_BOX, cand)
            if box:
                el, sel = page.query_selector(cand), cand
                break
        if el is None:
            # Do NOT quietly shoot the whole page. That is what the old code did,
            # and it is how four panel-push figures an episode shipped with margins.
            warn.append(f"figure {n} ({cid}): {os.path.basename(html)} has neither a "
                        f".card nor a .panel box, so there is nothing to frame the "
                        f"figure to — SKIPPED rather than shooting the whole page")
            page.close(); continue

        # DID IT COME OUT LIGHT? The question the old class test was trying to ask.
        if box["luma"] is None or box["luma"] < PRINT_MIN_LUMA:
            warn.append(f"figure {n} ({cid}): rendered DARK (background {box['bg']}) — "
                        f"the ?print=1 switch did not produce a light theme"
                        f"{'' if box['printed'] else ', and the print class never got set'}"
                        f". In a print book this is a charcoal rectangle on white paper.")

        out = os.path.join(OUT, f"figure-{n}.png")
        el.screenshot(path=out)
        page.close(); done += 1
        print(f"figure {n}: {os.path.basename(html)} [{sel} {box['w']}x{box['h']}] "
              f"-> {os.path.basename(out)}")
print(f"DONE: {done}/{len(figs)} figures rendered")
for w in warn:
    print("  !", w)

# A MISSING figure halts; a DARK one does not.
#
# Per PP-STANDARDS §WHAT DESERVES A GATE, ask whether Jodie would want the episode
# stopped for it. A figure that did not render leaves a HOLE in a Definition-of-Done
# deliverable — the book shows a broken image — so yes. A figure that rendered dark
# is ugly, not broken, and the e-book is one of the four human approvals, so a
# person is already going to look at it. Warn loudly, do not halt.
if done != len(figs):
    print(f"FAILED: {len(figs) - done} figure(s) did not render. The book would have a "
          f"hole in it, so this stops here rather than building a PDF with a broken "
          f"image in it.")
    sys.exit(2)
