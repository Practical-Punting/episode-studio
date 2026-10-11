#!/usr/bin/env python3
"""fbx_render.py — render ppInit/ppSeek card pages to clips, ANY size, optionally WITH ALPHA.

    python fbx_render.py <out_dir> <page.html>:<W>x<H>[:alpha] [more pages ...]

Same protocol as render_card.py (it SEEKS and screenshots, it never plays — see the
seek-versus-play note in pp-anim.js), with two additions the FBX videos need:
  · any canvas size (1920x1080 cards AND 1080x1920 cards for the vertical Short);
  · alpha: a page marked `:alpha` is shot on a transparent background and written as
    QuickTime RLE (argb), so a panel can sit over Gordon without a green key.
Opaque pages are written as x264 CRF 8 yuv444p, exactly like render_card.py.

Every page is rendered in ONE Chromium session (fonts are local woff2 files, no CDN).
For each clip it also writes <name>.last.png (the final frame) so QC can READ it.
Frame rate is 25 — the presenter's own rate, so nothing is resampled at assembly.
"""
import base64
import functools
import os
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import quote

FPS = 25
TAIL = 0.5


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def render_all(out_dir: Path, jobs):
    """jobs: list of (html Path, W, H, alpha bool). All pages must share one directory."""
    from playwright.sync_api import sync_playwright
    root = jobs[0][0].parent
    if any(j[0].parent != root for j in jobs):
        sys.exit("all pages must live in one folder (it is served as the web root)")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    # Started and never stopped: closing the browser hangs on this machine, so the CALLER
    # ends the process with os._exit(0) once it has what it needs (render_card.py's rule).
    p = sync_playwright().start()
    if True:
        browser = p.chromium.launch(headless=True, args=[
            "--force-color-profile=srgb", "--disable-lcd-text", "--hide-scrollbars",
            "--force-device-scale-factor=1"])
        for html, W, H, alpha in jobs:
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            url = f"http://127.0.0.1:{httpd.server_address[1]}/{quote(html.name)}?paused=1"
            page.goto(url, wait_until="load")
            page.wait_for_function("typeof window.ppDuration === 'number'", timeout=60_000)
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
            # every @font-face must have LOADED, not merely been declared — a fallback font is
            # exactly how EP03's cover shipped wrong
            # (per FAMILY: Google Fonts splits a face into unicode-range subsets and the unused
            # ones — Vietnamese, Latin-extended — correctly never load)
            bad_fonts = page.evaluate(
                "(() => { const ok = new Set(), all = new Set();"
                " for (const f of document.fonts) { all.add(f.family); if (f.status === 'loaded') ok.add(f.family); }"
                " return [...all].filter(x => !ok.has(x)); })()")
            if bad_fonts:
                sys.exit(f"HALT {html.name}: fonts not loaded: {bad_fonts}")
            dur = page.evaluate("window.ppDuration")
            n = round((dur / 1000 + TAIL) * FPS)
            cdp = page.context.new_cdp_session(page)
            if alpha:
                cdp.send("Emulation.setDefaultBackgroundColorOverride",
                         {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})
                out = out_dir / (html.stem + ".mov")
                enc = ["-c:v", "qtrle", "-pix_fmt", "argb", str(out)]
            else:
                out = out_dir / (html.stem + ".mp4")
                enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "8", "-pix_fmt", "yuv444p", str(out)]
            ff = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe",
                                   "-framerate", str(FPS), "-i", "-"] + enc, stdin=subprocess.PIPE)
            clip = {"x": 0, "y": 0, "width": W, "height": H, "scale": 1}
            last = None
            for f in range(n):
                page.evaluate("t => ppSeek(t)", min(f * 1000 / FPS, dur))
                last = base64.b64decode(cdp.send("Page.captureScreenshot",
                                                 {"format": "png", "clip": clip})["data"])
                ff.stdin.write(last)
            ff.stdin.close()
            if ff.wait() != 0:
                sys.exit(f"HALT {html.name}: ffmpeg failed")
            (out_dir / (html.stem + ".last.png")).write_bytes(last)
            if errs:
                sys.exit(f"HALT {html.name}: page errors {errs[:3]}")
            log(f"{html.name}: {W}x{H}{' alpha' if alpha else ''} {dur:.0f}ms -> {n} frames -> {out.name}")
            results.append((html.name, str(out), n, dur))
            page.close()
    return results


def still(html: Path, out: Path, W: int, H: int, scale: float = 1.0):
    """One PNG of a static page, with the SAME Chromium flags as the clips. render_still.py has no
    --disable-lcd-text, and Chrome's LCD smoothing puts orange/blue fringes on small grey text —
    10 'orange' pixels inside "BROUGHT TO YOU BY" on the first evergreen thumbnail."""
    from playwright.sync_api import sync_playwright
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(html.parent)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True, args=[
        "--force-color-profile=srgb", "--disable-lcd-text", "--hide-scrollbars", "--force-device-scale-factor=1"])
    # scale > 1 renders the SAME layout at higher density (the 1280x720 thumbnail page as a crisp 1920x1080 title card)
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
    page.goto(f"http://127.0.0.1:{httpd.server_address[1]}/{quote(html.name)}", wait_until="load")
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
    page.wait_for_function("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)", timeout=60_000)
    bad = page.evaluate("(() => { const ok = new Set(), all = new Set();"
                        " for (const f of document.fonts) { all.add(f.family); if (f.status === 'loaded') ok.add(f.family); }"
                        " return [...all].filter(x => !ok.has(x)); })()")
    if bad:
        sys.exit(f"HALT {html.name}: fonts not loaded: {bad}")
    page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": W, "height": H})
    log(f"{html.name}: still {round(W * scale)}x{round(H * scale)} -> {out}")
    # caller ends the process with os._exit(0) — closing the browser hangs on this machine


def parse(spec):
    parts = spec.split(":")
    # Windows drive letters contain ':' — rebuild the path from the right
    alpha = parts[-1] == "alpha"
    if alpha:
        parts = parts[:-1]
    size = parts[-1]
    W, H = (int(x) for x in size.split("x"))
    return Path(":".join(parts[:-1])).resolve(), W, H, alpha


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    res = render_all(Path(sys.argv[1]), [parse(s) for s in sys.argv[2:]])
    sys.stdout.flush()
    os._exit(0)   # browser.close() hangs on this machine (render_card.py note)
