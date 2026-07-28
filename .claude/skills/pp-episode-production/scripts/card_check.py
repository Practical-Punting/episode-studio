#!/usr/bin/env python3
"""card_check.py — overlap / clip / logo-collision QC for motion-graphic cards.

    python card_check.py <card.html | dir-of-cards> [--json out.json]

Cards have never had what the cover has had since EP09. `cover_check.py` measures
the rendered cover and fails on collisions; nothing did that for the sixteen card
pages, and EP12's C10 shipped with its footnote overlapping the third step card
between 1040px and 1300px. It reached the finished video AND e-book figure 10, and
every automated check passed.

WHAT IT MEASURES, on the settled frame (every animation seeked to its end, because
mid-flight transforms legitimately overlap):
  · leaf text boxes that overlap each other
  · anything clipped outside the card / panel
  · anything sitting under the logo, which is painted last and wins
  · text that has overflowed its own scroll box (a long string breaking its container)

DISPLAY TYPE IS MEASURED BY ITS INK, NOT ITS LINE BOX (added 28 Jul 2026).
EP13 C11 shipped a collision straight through this checker: `.big` is Anton at
300px with line-height 0.86, so the LINE BOX is 258px while the glyphs are ~298px
— and the `g` of "10kg" hung 40px below the box, through the `.sub` line beneath.
The checker returned "1/1 clean" on it.

The blind spot was the fix for an earlier problem. Range rects are sized by the
FONT's ascent/descent, which overshoots Anton badly at display sizes and made
everything look like a collision; the line box was substituted to stop that. But
the line box is TOO SMALL for tight leading exactly as the font box is too big.
So above INK_FS the band now comes from canvas TextMetrics
`actualBoundingBox{Ascent,Descent}` — the TRUE inked extent of those very glyphs.
That is strictly tighter than the font box, so the false positives it was
introduced to prevent cannot come back; it is simply the right quantity.

Below INK_FS nothing changes: body text carries real leading, its ink sits inside
its line box, and the old behaviour is correct and proven. The ink band is used
for the text-vs-text and under-the-logo rules only. The foreign-panel rule keeps
its own INK fraction untouched, because that is what EP12 C10's regression test
is calibrated against.

WHAT IT CANNOT SEE — and this is the point of the memory note "checkers verify
structure, not appearance": it cannot tell you the headline went grey, that Anton
fell back to a thin face, or that a diagram communicates nothing. LOOK at the cards.
This is a backstop, not a substitute for eyes.

Exit 0 = clean, exit 1 = problems (each in plain English).
"""
import argparse
import functools
import json
import os
import pathlib
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

from playwright.sync_api import sync_playwright

# The Windows console defaults to cp1252 and cannot encode the tick/cross.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                    # noqa: BLE001
        pass

W, H = 1920, 1080

# We measure INKED TEXT RUNS, not element boxes.
#
# Measuring element boxes is what makes a naive card checker useless: a
# full-width .note block technically extends under the logo even when its one
# short line stops 900px short of it, and an inline <b> is geometrically inside
# its own parent, so a box-vs-box test reports both as collisions. Both are
# false. A Range over each text node gives the rectangle the reader actually
# sees, one per line.
#
# Runs are only compared ACROSS block containers. Inside one paragraph the
# Anton headlines run line-height 0.84-0.96, so consecutive line boxes overlap
# vertically on purpose; that is tight leading, not a collision.
PROBE_TMPL = r"""
(() => {
  const INK_FS = __INK_FS__;
  // TRUE inked band for one text run, from the glyphs themselves.
  //
  // A Range rect spans the FONT box: its height is fontBoundingBoxAscent +
  // fontBoundingBoxDescent, with the baseline that far below its top. Canvas
  // TextMetrics reports both that font box AND the actual inked extent of this
  // exact string, so the baseline can be located in the rect and the ink band
  // placed around it. `k` rescales for any disagreement between the CSS font
  // shorthand and what the element actually resolved to; if it disagrees by
  // more than a quarter we do not trust the reading and fall back.
  const _cv = document.createElement('canvas').getContext('2d');
  const inkChars = (cs, text, r) => {
    try {
      _cv.font = cs.fontStyle + ' ' + cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
      const m0 = _cv.measureText(text);
      const fa = m0.fontBoundingBoxAscent, fd = m0.fontBoundingBoxDescent;
      for (const v of [fa, fd, m0.width]) if (typeof v !== 'number' || !isFinite(v)) return null;
      const k = r.height / (fa + fd);
      if (!isFinite(k) || k < 0.8 || k > 1.25) return null;
      if (!(m0.width > 0)) return null;
      const sx = r.width / m0.width;
      if (!isFinite(sx) || sx < 0.8 || sx > 1.25) return null;
      const base = r.y + fa * k;
      const out = [];
      for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (!ch.trim()) continue;
        const x0 = r.x + _cv.measureText(text.slice(0, i)).width * sx;
        const x1 = r.x + _cv.measureText(text.slice(0, i + 1)).width * sx;
        const mc = _cv.measureText(ch);
        const aa = mc.actualBoundingBoxAscent, ad = mc.actualBoundingBoxDescent;
        if (typeof aa !== 'number' || typeof ad !== 'number' || !isFinite(aa) || !isFinite(ad))
          return null;
        out.push({ch, x: x0, w: Math.max(1, x1 - x0),
                  y: base - aa * k, h: Math.max(1, (aa + ad) * k)});
      }
      return out.length ? out : null;
    } catch (e) { return null; }
  };

  const root = document.querySelector('.card') || document.querySelector('.panel')
            || document.body;
  const runs = [], boxes = [];
  let blockSeq = 0;
  const blockOf = new Map();
  const blockId = (el) => {
    let n = el;
    while (n && n !== root && getComputedStyle(n).display.startsWith('inline')) n = n.parentElement;
    n = n || root;
    if (!blockOf.has(n)) {
      blockOf.set(n, ++blockSeq);
      // Tag it so the pixel confirmation below can isolate this block by selector.
      n.setAttribute('data-cc-block', String(blockOf.get(n)));
    }
    return {id: blockOf.get(n), el: n};
  };
  const name = (el) => el.id || (typeof el.className === 'string' && el.className.trim()
                 ? el.className.trim().split(/\\s+/)[0] : el.tagName.toLowerCase());
  const hidden = (el) => {
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return true;
    }
    return false;
  };

  // Index every element so ancestry can be decided from the DOM rather than
  // guessed from geometry.
  let seq = 0;
  const idx = new Map(), chain = new Map();
  (function tag(el, anc) {
    idx.set(el, ++seq);
    chain.set(el, anc);
    const mine = anc.concat([idx.get(el)]);
    for (const c of el.children) tag(c, mine);
  })(root, []);

  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    if (!el || hidden(el)) continue;
    const b = blockId(el);
    const cs = getComputedStyle(el);
    // Range rects are sized by the FONT's ascent/descent, which for Anton
    // overshoots the visible glyphs by tens of pixels at display sizes. The
    // CSS line box is what actually occupies the layout, so take the width
    // from the range (true ink width) and the height from the line box,
    // centred on the same baseline band.
    let lh = parseFloat(cs.lineHeight);
    if (!isFinite(lh)) lh = parseFloat(cs.fontSize) * 1.2;
    const rg = document.createRange();
    rg.selectNodeContents(n);
    const fs = parseFloat(cs.fontSize);
    const rects = rg.getClientRects();
    for (const r of rects) {
      if (r.width < 1 || r.height < 1) continue;
      const cy = r.y + r.height / 2;
      const common = {owner: name(el), block: b.id, blockName: name(b.el),
                      text: n.textContent.trim().slice(0, 40),
                      boxId: idx.get(b.el),
                      anc: chain.get(b.el).concat([idx.get(b.el)]),
                      fs: fs};
      // DISPLAY TYPE IS EMITTED ONE RECTANGLE PER CHARACTER.
      //
      // A single ink rectangle for the whole run is too blunt: EP12 C1's "60
      // Days+" drops its `y` into the vertical band of "RESUMING FROM A SPELL"
      // but lands in the WHITESPACE PAST the final L and touches nothing. A
      // run-wide rectangle calls that a collision; the published card is fine.
      // Per character, the `y` owns only its own columns, so it clears — while
      // C11's `g`, which sits directly above the sub line, still collides.
      // Only for one-line display runs: if it wrapped, the per-character x
      // mapping would not hold, so fall back to the line box.
      const chars = (fs >= INK_FS && rects.length === 1)
                  ? inkChars(cs, n.textContent.trim(), r) : null;
      if (chars) {
        for (const c of chars) {
          runs.push(Object.assign({}, common, {inked: true, ch: c.ch,
                    x: c.x, y: cy - lh / 2, w: c.w, h: lh,
                    iy: c.y, ih: c.h}));
        }
      } else {
        runs.push(Object.assign({}, common, {inked: false,
                  x: r.x, y: cy - lh / 2, w: r.width, h: lh,
                  iy: cy - lh / 2, ih: lh}));
      }
    }
  }

  const walk = (el) => {
    for (const c of el.children) {
      if (hidden(c)) continue;
      const cs = getComputedStyle(c);
      const r = c.getBoundingClientRect();
      if (r.width && r.height) {
        // An OPAQUE fill is a panel: text that is not its own must not sit on it.
        // A border-only or translucent decoration (the c11 magnifier, the c05 ink
        // rings) is meant to sit over things and is not a panel.
        const m = /rgba?\(([^)]+)\)/.exec(cs.backgroundColor);
        const alpha = m ? (m[1].split(',')[3] === undefined ? 1 : parseFloat(m[1].split(',')[3])) : 0;
        boxes.push({tag: c.tagName.toLowerCase(), owner: name(c),
                    id: idx.get(c), anc: chain.get(c).concat([idx.get(c)]),
                    opaque: alpha >= 0.9,
                    x: r.x, y: r.y, w: r.width, h: r.height,
                    overflowX: c.scrollWidth - c.clientWidth,
                    overflowY: c.scrollHeight - c.clientHeight,
                    clip: cs.overflow !== 'visible' && cs.overflow !== 'clip visible'});
      }
      walk(c);
    }
  };
  walk(root);
  const logo = document.querySelector('#logo, .logo');
  const lr = logo ? logo.getBoundingClientRect() : null;
  const rb = root.getBoundingClientRect();
  return {runs, boxes,
          logo: lr ? {x: lr.x, y: lr.y, w: lr.width, h: lr.height} : null,
          root: {x: rb.x, y: rb.y, w: rb.width, h: rb.height}};
})()
"""

# Above this font-size a run is judged on its INKED band, not its line box.
# 120px is comfortably above any body copy on a card and comfortably below every
# display size in the library (.big 300px, .hl 92-140px, .odds 96px), so it
# separates "type set with real leading" from "type set tight for effect".
INK_FS = 120

# Text that merely touches (adjacent words on a line) must not read as a clash.
TOUCH = 1.5
# Line-box rounding at the card edge is not a clipped word.
CLIP = 4
# Half-height of the inked band, as a fraction of font-size: roughly cap-height
# plus descender, i.e. the part of a line the eye actually sees.
INK = 0.36
# Smallest dimension a filled box must have before it counts as a PANEL that text
# should not sit on. Below this it is a graphic mark — EP11 c06's 10px winning
# post crosses the winner's name on purpose, and a strikethrough is 5px.
MIN_PANEL = 40

# One definition of the threshold, shared with the probe. Never two.
PROBE = PROBE_TMPL.replace("__INK_FS__", str(INK_FS))


def band(r):
    """The rectangle a run is JUDGED on: its ink above INK_FS, its line box below."""
    return dict(r, y=r["iy"], h=r["ih"])


# A pixel differing from the text-free baseline by more than this is that block's ink.
PIX_THRESH = 40
# Fewer confirmed pixels than this is antialiasing on two adjacent glyphs, not a clash.
PIX_MIN = 40

_HIDE_ALL = ("() => document.querySelectorAll('[data-cc-block]')"
             ".forEach(e => { e.style.visibility = 'hidden'; })")
_SHOW_ONE = ("(k) => { document.querySelectorAll('[data-cc-block]').forEach("
             "e => { e.style.visibility = e.getAttribute('data-cc-block') === k "
             "? 'visible' : 'hidden'; }); }")
_RESTORE = ("() => document.querySelectorAll('[data-cc-block]')"
            ".forEach(e => { e.style.visibility = ''; })")


def confirm_by_pixels(page, pairs):
    """Geometry PROPOSES a collision; the rendered pixels DISPOSE.

    Rectangles cannot settle this on their own, and the failure is not academic.
    EP12 C1's published "60 Days+" drops its `y` beside "RESUMING FROM A SPELL" —
    same columns, same vertical band, **and it touches nothing**, because within
    one glyph the ink bottom varies by column. Every rectangle approximation
    tried (run-wide ink, then per-character ink) called that card broken. It is
    not: look at it. Meanwhile EP13 C11's `g` genuinely crosses its sub line.

    So each proposed pair is rendered in isolation and its ink intersected. This
    runs ONLY for pairs geometry already flagged, so the common case — a clean
    card — costs nothing.

    CAVEAT, and it matters: this measures an element's whole ink, BACKGROUNDS AND
    BORDERS INCLUDED. It is glyph-true only for elements carrying colour alone.
    A chip with a fill would confirm on its fill; geometry is what decides such a
    pair is worth looking at in the first place.
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return set(pairs)          # no imaging: keep every proposal, never silently drop
    import io as _io

    def grab():
        return Image.open(_io.BytesIO(page.screenshot())).convert("RGB")

    def mask(base, k):
        page.evaluate(_SHOW_ONE, str(k))
        page.wait_for_timeout(40)
        d = ImageChops.difference(grab(), base).convert("L")
        return d.point(lambda v: 255 if v > PIX_THRESH else 0, mode="1")

    page.evaluate(_HIDE_ALL)
    page.wait_for_timeout(40)
    base = grab()
    cache, confirmed = {}, set()
    for a, b in pairs:
        for k in (a, b):
            if k not in cache:
                cache[k] = mask(base, k)
        shared = ImageChops.logical_and(cache[a], cache[b])
        if shared.getbbox() and shared.convert("L").histogram()[255] >= PIX_MIN:
            confirmed.add((a, b))
    page.evaluate(_RESTORE)
    page.wait_for_timeout(40)
    return confirmed


def rects_overlap(a, b, pad=TOUCH):
    return not (a["x"] + a["w"] <= b["x"] + pad or b["x"] + b["w"] <= a["x"] + pad or
                a["y"] + a["h"] <= b["y"] + pad or b["y"] + b["h"] <= a["y"] + pad)


def label(r):
    t = f' "{r["text"]}"' if r.get("text") else ""
    return f"{r['owner']}{t}"


def check_page(page, url):
    page.goto(url, wait_until="load")
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
    page.wait_for_function(
        "Array.from(document.images).every(i => i.complete || i.naturalWidth === 0)",
        timeout=30_000)
    # Settle every animation: this is the frame the viewer actually reads.
    page.evaluate("() => { if (window.ppSeek && window.ppDuration) "
                  "window.ppSeek(window.ppDuration); }")
    page.wait_for_timeout(120)
    data = page.evaluate(PROBE)
    runs, boxes, root, logo = data["runs"], data["boxes"], data["root"], data["logo"]
    problems, seen = [], set()

    # 1. text colliding with text from a DIFFERENT block container.
    # Geometry proposes; confirm_by_pixels() disposes. See its docstring.
    proposed = []
    for i, a in enumerate(runs):
        for b in runs[i + 1:]:
            if a["block"] == b["block"]:
                continue                       # same paragraph: tight leading, by design
            ab, bb = band(a), band(b)
            if not rects_overlap(ab, bb):
                continue
            key = tuple(sorted((a["blockName"], b["blockName"])))
            if key in seen:
                continue
            seen.add(key)
            ox = min(ab["x"] + ab["w"], bb["x"] + bb["w"]) - max(ab["x"], bb["x"])
            oy = min(ab["y"] + ab["h"], bb["y"] + bb["h"]) - max(ab["y"], bb["y"])
            how = " (measured on the INKED glyphs)" if (a["inked"] or b["inked"]) else ""
            proposed.append((tuple(sorted((a["block"], b["block"]))),
                             f"OVERLAP: {label(a)} collides with {label(b)} — "
                             f"{ox:.0f}x{oy:.0f}px shared, "
                             f"x {max(ab['x'], bb['x']):.0f}-"
                             f"{min(ab['x']+ab['w'], bb['x']+bb['w']):.0f}{how}"))
    if proposed:
        ok = confirm_by_pixels(page, [p for p, _ in proposed])
        problems.extend(msg for p, msg in proposed if p in ok)

    # 2. text sitting on a filled panel that is not its own.
    #
    # THIS IS THE RULE THAT CATCHES EP12's C10. The absolutely-positioned note
    # overran the third step CARD, not the third step's TEXT — the card's own
    # words stopped ~90px short of where the note began — so a text-vs-text test
    # alone passes the broken page. A panel is "not its own" when it is neither
    # an ancestor nor a descendant of the run's block container: a strikethrough
    # inside its chip is fine, a footnote lying across a sibling card is not.
    for r in runs:
        # Use the INK band, not the line box. A 36px line box carries ~9px of
        # leading above the glyphs, and counting that as contact makes a card
        # whose text merely sits close to a panel edge read the same as one
        # lying across it. EP12's shipped C10 grazes by exactly that leading.
        ink = dict(r, y=r["y"] + r["h"] / 2 - INK * r["fs"], h=2 * INK * r["fs"])
        for b in boxes:
            if not b["opaque"] or b["id"] == r["boxId"]:
                continue
            if min(b["w"], b["h"]) < MIN_PANEL:
                continue          # a rule, bar, pip or winning post is a mark, not a panel
            if b["id"] in r["anc"] or r["boxId"] in b["anc"]:
                continue
            if rects_overlap(ink, b):
                ox = min(r["x"] + r["w"], b["x"] + b["w"]) - max(r["x"], b["x"])
                problems.append(
                    f"ON A FOREIGN PANEL: {label(r)} lies across {b['owner']}, which it is "
                    f"not part of — {ox:.0f}px shared, "
                    f"x {max(r['x'], b['x']):.0f}-{min(r['x']+r['w'], b['x']+b['w']):.0f}")
                break

    # 3. text running under the logo, which is painted last and wins
    if logo:
        for r in runs:
            if rects_overlap(band(r), logo):
                problems.append(f"UNDER THE LOGO: {label(r)} runs beneath the logo chip")
                break

    # 3. text clipped outside the card / panel.
    # A few px of line-box rounding is not a defect; a word cut off is.
    for r in runs:
        if (r["x"] < root["x"] - CLIP or r["y"] < root["y"] - CLIP or
                r["x"] + r["w"] > root["x"] + root["w"] + CLIP or
                r["y"] + r["h"] > root["y"] + root["h"] + CLIP):
            problems.append(f"CLIPPED: {label(r)} extends outside the card "
                            f"({r['x']:.0f},{r['y']:.0f} {r['w']:.0f}x{r['h']:.0f})")

    # 4. a string that has burst its own container
    for b in boxes:
        if b["clip"] and (b["overflowX"] > 2 or b["overflowY"] > 2):
            problems.append(f"OVERFLOW: {b['owner']} has {b['overflowX']:.0f}x"
                            f"{b['overflowY']:.0f}px of content clipped inside it")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()

    target = pathlib.Path(a.target).resolve()
    if target.is_dir():
        serve, pages = target, sorted(p.name for p in target.glob("*.html"))
    else:
        serve, pages = target.parent, [target.name]
    if not pages:
        print(f"no card pages in {serve}")
        return 0

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *x):
            pass

    handler = functools.partial(Quiet, directory=str(serve))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]

    results, failed = {}, 0
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True, args=["--force-device-scale-factor=1",
                                                    "--hide-scrollbars"])
        pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for name in pages:
            try:
                probs = check_page(pg, f"http://127.0.0.1:{port}/{quote(name)}")
            except Exception as e:                       # noqa: BLE001
                probs = [f"could not measure this page: {e}"]
            results[name] = probs
            if probs:
                failed += 1
                print(f"✗ {name} — {len(probs)} problem(s)")
                for x in probs:
                    print(f"    {x}")
            else:
                print(f"✓ {name}")

    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\ncard check: {len(pages) - failed}/{len(pages)} clean")
    if failed:
        print("CARD CHECK FAILED — a card with a collision must not be rendered to a clip; "
              "it would ship into the video AND the matching e-book figure.")
    sys.stdout.flush()
    os._exit(1 if failed else 0)   # browser.close() hangs on this machine


if __name__ == "__main__":
    main()
