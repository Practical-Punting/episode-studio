# Render a PP overlay HTML to video via headless Chromium frame capture.
# Usage: python render_overlay.py <html_path> <duration_secs> <out_mp4>
# Protocol: dispatch CustomEvent 'data-om-seek-to-time-frame' with
# detail {time, frame, sync: true} on the svg[data-om-exportable-video-with-duration-secs],
# then CDP-screenshot the svg's 1920x1080 box. PNGs piped into ffmpeg.
import base64, subprocess, sys, time, pathlib, threading, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

HTML = pathlib.Path(sys.argv[1]).resolve()
DURATION = float(sys.argv[2])
OUT = sys.argv[3]
FPS = 30
W, H = 1920, 1080
N_FRAMES = round(DURATION * FPS)

# Serve the HTML's folder over localhost — Babel fetches sibling .jsx files,
# which Chrome blocks on file:// origins.
handler = functools.partial(SimpleHTTPRequestHandler, directory=str(HTML.parent))
handler.log_message = lambda *a, **k: None
httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PAGE_URL = f"http://127.0.0.1:{httpd.server_address[1]}/{quote(HTML.name)}"

from playwright.sync_api import sync_playwright

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--force-color-profile=srgb",
        "--disable-lcd-text",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
    ])
    page = browser.new_page(viewport={"width": W + 80, "height": H + 160}, device_scale_factor=1)
    page_errors = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("console", lambda m: page_errors.append(f"console.{m.type}: {m.text[:200]}")
            if m.type == "error" else None)
    page.goto(PAGE_URL, wait_until="load")

    # Babel-compiled React app: wait for the exportable svg, then fonts.
    page.wait_for_selector("svg[data-om-exportable-video-with-duration-secs]", timeout=120_000)
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=120_000)
    # engine advertises sync seek + inlined fonts when ready
    page.wait_for_function(
        "document.querySelector('svg[data-om-exportable-video-with-duration-secs]')"
        ".hasAttribute('data-om-sync-seek')", timeout=60_000)
    try:
        page.wait_for_function(
            "document.querySelector('svg[data-om-exportable-video-with-duration-secs]')"
            ".hasAttribute('data-om-fonts-inlined')", timeout=30_000)
        log("fonts inlined")
    except Exception:
        log("WARN: data-om-fonts-inlined never appeared; continuing (document.fonts loaded)")

    dur_attr = page.eval_on_selector(
        "svg[data-om-exportable-video-with-duration-secs]",
        "el => el.getAttribute('data-om-exportable-video-with-duration-secs')")
    log(f"page ready; engine duration={dur_attr}s, rendering {N_FRAMES} frames @ {FPS}fps")
    if abs(float(dur_attr) - DURATION) > 0.01:
        log(f"WARN: engine duration {dur_attr} != requested {DURATION}")

    # pin canvas at scale 1, kill shadow, hide everything after it (playback bar)
    page.add_style_tag(content="""
      svg[data-om-exportable-video-with-duration-secs] {
        transform: none !important; box-shadow: none !important; }
    """)
    page.wait_for_timeout(200)
    box = page.eval_on_selector(
        "svg[data-om-exportable-video-with-duration-secs]",
        "el => { const r = el.getBoundingClientRect();"
        " return {x: r.x, y: r.y, w: r.width, h: r.height}; }")
    log(f"canvas box: {box}")
    if round(box["w"]) != W or round(box["h"]) != H:
        sys.exit(f"FATAL: canvas box is {box['w']}x{box['h']}, expected {W}x{H}")
    clip = {"x": box["x"], "y": box["y"], "width": W, "height": H, "scale": 1}

    cdp = page.context.new_cdp_session(page)

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "8",
        "-pix_fmt", "yuv444p", "-g", "150", OUT,
    ], stdin=subprocess.PIPE)

    seek_js = """([t, f]) => {
      const el = document.querySelector('svg[data-om-exportable-video-with-duration-secs]');
      el.dispatchEvent(new CustomEvent('data-om-seek-to-time-frame',
        { detail: { time: t, frame: f, sync: true } }));
    }"""

    t0 = time.time()
    for f in range(N_FRAMES):
        t = f / FPS
        page.evaluate(seek_js, [t, f])
        shot = cdp.send("Page.captureScreenshot", {
            "format": "png", "clip": clip, "captureBeyondViewport": True})
        ff.stdin.write(base64.b64decode(shot["data"]))
        if f % 600 == 0 and f > 0:
            rate = f / (time.time() - t0)
            eta = (N_FRAMES - f) / rate / 60
            log(f"frame {f}/{N_FRAMES} ({rate:.1f} fps, ~{eta:.1f} min left)")

    ff.stdin.close()
    rc = ff.wait()
    if page_errors:
        log(f"PAGE ERRORS ({len(page_errors)}): " + " | ".join(page_errors[:5]))
    if rc != 0:
        sys.exit(f"FATAL: ffmpeg exited {rc}")
    log(f"done in {(time.time()-t0)/60:.1f} min -> {OUT}")
    # browser.close() reliably hangs on this setup after long CDP screenshot
    # sessions (observed EP01: python zombies stuck for 35+ min while the MP4
    # was already complete). The video is finalized at this point, so skip
    # teardown entirely rather than leave zombie processes behind.
    sys.stdout.flush()
    import os
    os._exit(0)
