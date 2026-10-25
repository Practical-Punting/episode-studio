#!/usr/bin/env python3
"""card_lint.py — catch the card mistakes that cost re-renders, BEFORE anything is rendered.

    python card_lint.py <cards_dir> [page.html ...]       (no pages = every *.html except the standing warranty slide)

Each rule is a fault that actually shipped into a render on the PPD promo (25 Oct 2026) and was only found by looking:

  R1 FIGHTING ANIMATIONS  Two animations on the same property of one element whose FIRST keyframes differ. Web
                          Animations fill backwards, so the later one wins from t=0: a fade-out written after a fade-in
                          shows the element before it entered; a travel after a slam erases the slam. Use one
                          animation through several moments (ppd_cards.seq) or two elements.
  R2 FLATTENED 3D         Opacity (animated, or below 1) on an element with transform-style: preserve-3d. Chromium then
                          flattens the 3D and paints children in DOM order — the free guide showed its last leaf, not
                          its cover. Put the fade on a wrapper.
  R3 OLD-STYLE FIGURES    Raleway text containing a digit without lining-nums: its default figures drop below the line
                          ($9.50, no.5). Scoreboard numbers want lining figures.
  R4 CAPTION BAND         On a full-screen card, anything visible in y 860-990: the burned-in captions sit there. (The
                          small print, the endorser and the logo bug sit below/above it and are exempt.)
  R5 SMALL PRINT          More than two lines of small print (it then climbs into the caption band).
  R6 OFF THE FRAME        Visible text whose box runs outside 1920x1080.

Alpha pages (panels over Gordon / supers) are exempt from R4. Measured at each page's LAST frame (ppSeek(ppDuration)).
Exit 1 with a plain list of faults; exit 0 when clean. `lint(cards, names)` returns the list for a build to halt on.
"""
import functools
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

CAPTION_BAND = (860, 990)
EXEMPT_R4 = ".small, .preload, #end, #bug, #sp, [data-lint-exempt]"

JS = r"""
() => {
  const faults = [];
  const spec = window.ppSpec || [];
  // ---- R1: same element + same property, first keyframes that disagree
  const seen = new Map();          // element -> {prop: [firstValue, specIndex]}
  spec.forEach((s, k) => {
    if (!s.kf || !s.kf.length) return;
    document.querySelectorAll(s.sel).forEach(el => {
      const m = seen.get(el) || {};
      for (const [p, v] of Object.entries(s.kf[0])) {
        if (p === 'offset' || p === 'easing' || p === 'composite') continue;
        if (m[p] && String(m[p][0]) !== String(v)) {
          faults.push(`R1 fighting animations: ${s.sel} '${p}' is animated twice and the later one starts at ` +
                      `${JSON.stringify(v)} not ${JSON.stringify(m[p][0])} — it will show from t=0. Use seq() or a second element.`);
        } else if (!m[p]) { m[p] = [v, k]; }
      }
      seen.set(el, m);
    });
  });
  // ---- R2: opacity on a preserve-3d element
  for (const el of document.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.transformStyle !== 'preserve-3d') continue;
    const animatedOpacity = spec.some(s => s.kf && s.kf.some(f => 'opacity' in f) && [...document.querySelectorAll(s.sel)].includes(el));
    if (animatedOpacity || parseFloat(cs.opacity) < 1)
      faults.push(`R2 flattened 3D: #${el.id || el.tagName} has transform-style: preserve-3d AND opacity — the 3D is ` +
                  `flattened and children paint in DOM order. Fade a wrapper instead.`);
  }
  // ---- R3..R6: visible text and boxes at the last frame
  const alpha = getComputedStyle(document.body).backgroundColor === 'rgba(0, 0, 0, 0)';
  const visible = el => {
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false;
    }
    return true;
  };
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('.preload') || !visible(el)) continue;
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length);
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (own && /\d/.test(el.textContent) && cs.fontFamily.includes('Raleway') && !cs.fontVariantNumeric.includes('lining-nums'))
      faults.push(`R3 old-style figures: "${el.textContent.trim().slice(0, 40)}" is Raleway with digits but no lining-nums.`);
    // R5 is about the caption band, so (like R4) it applies to full-screen cards; a narrow panel beside Gordon may wrap
    if (!alpha && el.matches('.small')) {
      const lines = Math.round(r.height / parseFloat(cs.lineHeight));
      if (lines > 2) faults.push(`R5 small print runs to ${lines} lines (max 2) — it climbs into the caption band.`);
    }
    if (own && (r.right > 1921 || r.left < -1 || r.bottom > 1081 || r.top < -1) && r.width > 0)
      faults.push(`R6 off the frame: "${el.textContent.trim().slice(0, 40)}" box ${[r.left, r.top, r.right, r.bottom].map(Math.round)}.`);
    if (!alpha && !el.closest('""" + EXEMPT_R4 + r"""')) {
      // an <svg> is a CONTAINER (a full-frame one holding two arrows covers the band without painting there): judge
      // the shapes inside it, which getBoundingClientRect measures where they actually paint
      const shape = ['path', 'circle', 'polyline', 'polygon', 'rect', 'line', 'ellipse'].includes(el.tagName.toLowerCase());
      const paints = own || cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || el.tagName === 'IMG' || shape;
      if (paints && r.width > 0 && r.height > 0 && r.bottom > BAND0 && r.top < BAND1)
        faults.push(`R4 caption band: ${el.id ? '#' + el.id : el.tagName.toLowerCase()} "${(el.textContent || '').trim().slice(0, 30)}" ` +
                    `occupies y ${Math.round(r.top)}-${Math.round(r.bottom)}; keep full cards clear of y BAND0-BAND1.`);
    }
  }
  return [...new Set(faults)];
}
""".replace("BAND0", str(CAPTION_BAND[0])).replace("BAND1", str(CAPTION_BAND[1]))


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def lint(cards: Path, names=None):
    """{page name: [faults]} for every page (only pages with faults are listed)."""
    from playwright.sync_api import sync_playwright
    cards = Path(cards)
    names = names or sorted(p.name for p in cards.glob("*.html") if "warranty" not in p.name)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(cards)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True, args=["--force-color-profile=srgb", "--disable-lcd-text", "--force-device-scale-factor=1"])
    out = {}
    try:
        for n in names:
            pg = b.new_page(viewport={"width": 1920, "height": 1080})
            pg.goto(f"http://127.0.0.1:{httpd.server_address[1]}/{quote(n)}?paused=1", wait_until="load")
            pg.wait_for_function("typeof window.ppDuration === 'number'", timeout=60_000)
            pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
            pg.evaluate("ppSeek(window.ppDuration)")
            f = pg.evaluate(JS)
            if f:
                out[n] = f
            pg.close()
    finally:
        b.close()
        p.stop()
        httpd.shutdown()
    return out


def report(faults):
    if not faults:
        return "card lint: clean"
    return "card lint FAILED — fix these before rendering (nothing was rendered):\n" + "\n".join(
        f"  {page}:\n" + "\n".join(f"    - {x}" for x in fs) for page, fs in faults.items())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    res = lint(Path(sys.argv[1]), sys.argv[2:] or None)
    print(report(res))
    sys.exit(1 if res else 0)
