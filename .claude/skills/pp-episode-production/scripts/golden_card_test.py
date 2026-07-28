#!/usr/bin/env python3
"""GOLDEN-FILE TEST — regenerate EP11's and EP12's cards and diff the PNGs.

    python golden_card_test.py [workdir]

DESIGN-self-authoring-build.md §14.1: "If the library cannot reproduce two
episodes it has already seen, it certainly cannot handle EP13."

It copies both episodes into a scratch workdir (NEVER touching the originals —
both are at the publish gate), back-fills block/content/trace onto the COPIES
from ep11_ep12_backfill.py, authors the pages, and renders shipped vs generated
at the SETTLED frame — every animation seeked to ppDuration, because that is the
composition the viewer reads for most of a card's on-screen life and it is what
build_figures.py turns into the matching e-book figure.

Motion is reported separately, as data: the ppInit specs are compared so timing
differences are enumerated rather than hidden behind a still.

Exit 0 only if every card is pixel-identical or is on the EXPECTED list below,
with its reason.
"""
import base64
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "testdata"))

import ep11_ep12_backfill as bf                              # noqa: E402
import pp_paths                                              # noqa: E402,F401

from PIL import Image, ImageChops                            # noqa: E402
from playwright.sync_api import sync_playwright              # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                        # noqa: BLE001
        pass

W, H = 1920, 1080

# Differences that are DELIBERATE, with the reason. Anything not on this list
# and not pixel-equal fails the run.
EXPECTED = {
    "EP12/ep12-c10-down-in-class.html":
        "the steps stack sits 34px HIGHER than it shipped, and that is the point.\n"
        "    The cascade itself is reproduced exactly — 8.0px card-to-card overlap, same "
        "as shipped — using a NEGATIVE MARGIN in normal flow instead of absolute offsets "
        "(Jodie, 28 Jul 2026), so the collision class stays unrepresentable.\n"
        "    The 34px is the shipped card's own bug, not reproduced: .steps was given a "
        "fixed height:424px while its content actually runs 458px, so the third card "
        "overhung its container and the note grazed it by 8px. In flow the container is "
        "its content, so the note clears by the full 26px margin. The note itself lands "
        "at y=951.4 in BOTH, identical.",
}


def media_root():
    r = os.environ.get("PP_VIDEOS_DIR") or r"G:\My Drive\PP Videos"
    if not os.path.isdir(r):
        sys.exit(f"media root not found: {r} (set PP_VIDEOS_DIR)")
    return r


def build_work(work):
    src = media_root()
    if os.path.exists(work):
        shutil.rmtree(work)
    for ep in ("PP-EP11", "PP-EP12"):
        shutil.copytree(f"{src}/{ep}/overlay", f"{work}/{ep}/overlay")
        os.makedirs(f"{work}/{ep}/docs", exist_ok=True)
        shutil.copy(f"{src}/{ep}/docs/episode.json", f"{work}/{ep}/docs/episode.json")
    os.makedirs(f"{work}/docs", exist_ok=True)
    for f in os.listdir(f"{src}/docs"):
        if re.match(r"EP1[12]-source-article-.*\.md", f):
            shutil.copy(f"{src}/docs/{f}", f"{work}/docs/{f}")
    for d in ("shipped-png", "gen-png", "diff"):
        os.makedirs(f"{work}/{d}", exist_ok=True)


def serve(d):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    s = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(d)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s.server_address[1]


def shoot(page, url, out):
    page.goto(url, wait_until="load")
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
    page.wait_for_function(
        "Array.from(document.images).every(i => i.complete || i.naturalWidth === 0)",
        timeout=30_000)
    page.evaluate("() => { if (window.ppSeek && window.ppDuration) "
                  "window.ppSeek(window.ppDuration); }")
    page.wait_for_timeout(150)
    cdp = page.context.new_cdp_session(page)
    shot = cdp.send("Page.captureScreenshot",
                    {"format": "png",
                     "clip": {"x": 0, "y": 0, "width": W, "height": H, "scale": 1},
                     "captureBeyondViewport": True})
    open(out, "wb").write(base64.b64decode(shot["data"]))


def anim_spec(path):
    m = re.search(r"ppInit\(\[(.*?)\]\);", open(path, encoding="utf-8").read(), re.S)
    return json.loads("[" + m.group(1).rstrip().rstrip(",") + "]") if m else []


def main():
    work = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "_golden_work")
    print(f"work area: {work}\n(the shipped episodes are copied, never touched)\n")
    build_work(work)
    if bf.run(work):
        sys.exit("back-fill verification FAILED — a value is not in its shipped page")

    author = os.path.join(HERE, "author_cards.py")
    for ep in ("EP11", "EP12"):
        gen = f"{work}/gen/{ep}"
        os.makedirs(gen, exist_ok=True)
        r = subprocess.run([sys.executable, author,
                            f"{work}/PP-{ep}/docs/episode.json", gen],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout.strip())
        if r.returncode:
            sys.exit(f"{ep}: author_cards.py halted (exit {r.returncode})\n{r.stderr}")

    rows = []
    for ep in ("EP11", "EP12"):
        gen, ship = f"{work}/gen/{ep}", f"{work}/PP-{ep}/overlay/export"
        shutil.copy(f"{ship}/pp-anim.js", f"{gen}/pp-anim.js")
        if not os.path.isdir(f"{gen}/assets"):
            shutil.copytree(f"{ship}/assets", f"{gen}/assets")
        sp, gp = serve(ship), serve(gen)
        with sync_playwright() as p:
            br = p.chromium.launch(headless=True, args=[
                "--force-color-profile=srgb", "--hide-scrollbars",
                "--force-device-scale-factor=1"])
            pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            for name in sorted(x for x in os.listdir(gen) if x.endswith(".html")):
                a, b = f"{work}/shipped-png/{ep}-{name}.png", f"{work}/gen-png/{ep}-{name}.png"
                shoot(pg, f"http://127.0.0.1:{sp}/{name}", a)
                shoot(pg, f"http://127.0.0.1:{gp}/{name}", b)
                d = ImageChops.difference(Image.open(a).convert("RGB"),
                                          Image.open(b).convert("RGB"))
                bbox = d.getbbox()
                npx = sum(1 for px in d.getdata() if px != (0, 0, 0)) if bbox else 0
                if bbox:
                    d.point(lambda v: min(255, v * 8)).save(f"{work}/diff/{ep}-{name}.png")
                same = anim_spec(f"{ship}/{name}") == anim_spec(f"{gen}/{name}")
                rows.append((f"{ep}/{name}", npx, bbox, same))

    print(f"\n{'card':52s} {'diff px':>11s}  motion")
    exact = unexplained = 0
    for key, npx, bbox, same in rows:
        tag = "PIXEL-EQUAL" if npx == 0 else f"{npx:,}"
        print(f"{key[:52]:52s} {tag:>11s}  {'identical' if same else 'timings differ'}")
        if npx == 0:
            exact += 1
        elif key in EXPECTED:
            print(f"    EXPECTED — {EXPECTED[key]}")
            print(f"    bbox={bbox}  diff image: diff/{key.replace('/', '-')}.png")
        else:
            unexplained += 1
            print(f"    ✗ UNEXPLAINED DIFFERENCE  bbox={bbox}")

    print(f"\n{exact}/{len(rows)} pixel-identical, "
          f"{len(rows) - exact - unexplained} expected, {unexplained} unexplained")
    print("\nNOTE: motion 'timings differ' is a KNOWN, ACCEPTED difference — the blocks "
          "emit canonical stagger timings, while the hand-authored pages carry per-card "
          "nudges of a few tens of ms. It does not move a pixel in the settled frame, "
          "which is what the diff above measures.")
    sys.stdout.flush()
    os._exit(1 if unexplained else 0)


if __name__ == "__main__":
    main()
