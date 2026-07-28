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
PROBE = r"""
(() => {
  const root = document.querySelector('.card') || document.querySelector('.panel')
            || document.body;
  const runs = [], boxes = [];
  let blockSeq = 0;
  const blockOf = new Map();
  const blockId = (el) => {
    let n = el;
    while (n && n !== root && getComputedStyle(n).display.startsWith('inline')) n = n.parentElement;
    n = n || root;
    if (!blockOf.has(n)) blockOf.set(n, ++blockSeq);
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
    for (const r of rg.getClientRects()) {
      if (r.width < 1 || r.height < 1) continue;
      const cy = r.y + r.height / 2;
      runs.push({owner: name(el), block: b.id, blockName: name(b.el),
                 text: n.textContent.trim().slice(0, 40),
                 boxId: idx.get(b.el),
                 anc: chain.get(b.el).concat([idx.get(b.el)]),
                 fs: parseFloat(cs.fontSize),
                 x: r.x, y: cy - lh / 2, w: r.width, h: lh});
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

    # 1. text colliding with text from a DIFFERENT block container
    for i, a in enumerate(runs):
        for b in runs[i + 1:]:
            if a["block"] == b["block"]:
                continue                       # same paragraph: tight leading, by design
            if not rects_overlap(a, b):
                continue
            key = tuple(sorted((a["blockName"], b["blockName"])))
            if key in seen:
                continue
            seen.add(key)
            ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            problems.append(
                f"OVERLAP: {label(a)} collides with {label(b)} — {ox:.0f}x{oy:.0f}px shared, "
                f"x {max(a['x'], b['x']):.0f}-{min(a['x']+a['w'], b['x']+b['w']):.0f}")

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
            if rects_overlap(r, logo):
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
