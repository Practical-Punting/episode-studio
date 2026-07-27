#!/usr/bin/env python3
"""cover_check.py — automatic overlap/clip QC for an e-book cover page.

The EP09 lesson (subtitle collided with the byline): measure the RENDERED
cover in headless Chromium and FAIL if any two text blocks overlap, or any
block is clipped outside the canvas, or band text spills past the band.

Usage:  python cover_check.py <cover.html> [width height]   (default 1588 2238)
Exit 0 = clean; exit 1 = problems (each printed in plain English).
"""
import http.server
import os
import socketserver
import sys
import threading

import pp_paths  # noqa: F401  (keeps import parity with sibling scripts)
from playwright.sync_api import sync_playwright

HTML = os.path.abspath(sys.argv[1])
W = int(sys.argv[2]) if len(sys.argv) > 3 else 1588
H = int(sys.argv[3]) if len(sys.argv) > 3 else 2238
SERVE = os.path.dirname(HTML)
PORT = 8137

SELECTORS = [".eyebrow", ".title", ".subtitle", ".byline", ".footrule", ".footer"]


def main():
    os.chdir(SERVE)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    problems = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": W, "height": H})
        page.goto(f"http://127.0.0.1:{PORT}/{os.path.basename(HTML)}", wait_until="load")
        page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
        rects = {}
        for sel in SELECTORS:
            el = page.query_selector(sel)
            if el:
                r = el.bounding_box()
                if r:
                    rects[sel] = r
        band = page.query_selector(".band")
        band_box = band.bounding_box() if band else None
        b.close()
    httpd.shutdown()

    def overlap(a, b):
        return not (a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"] or
                    a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"])

    names = list(rects)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            if overlap(rects[n1], rects[n2]):
                problems.append(f"{n1} OVERLAPS {n2} — text collision")
    for n, r in rects.items():
        if r["y"] < -1 or r["y"] + r["height"] > H + 1 or r["x"] < -1 or r["x"] + r["width"] > W + 1:
            problems.append(f"{n} is CLIPPED outside the {W}x{H} canvas")
    if band_box:
        for n in (".subtitle", ".byline", ".footrule", ".footer"):
            if n in rects:
                r = rects[n]
                if r["y"] + r["height"] > band_box["y"] + band_box["height"] + 1:
                    problems.append(f"{n} spills past the bottom of the white band")

    if problems:
        print(f"COVER CHECK FAILED — {len(problems)} problem(s):")
        for pr in problems:
            print(f"  ✗ {pr}")
        sys.exit(1)
    print(f"cover check ok — {len(rects)} text blocks, no overlap, no clipping")


if __name__ == "__main__":
    main()
