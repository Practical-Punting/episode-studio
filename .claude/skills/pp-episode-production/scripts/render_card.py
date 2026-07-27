# Render a ppInit/ppSeek-based PP Design card (full-viewport 1920x1080 HTML)
# to video via headless Chromium frame capture.
# Usage: python render_card.py <card.html> <out.mp4> [tail_secs=0.5]
# Duration = page's window.ppDuration + tail (holds final frame over the tail).
import base64, subprocess, sys, time, pathlib, threading, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

HTML = pathlib.Path(sys.argv[1]).resolve()
OUT = sys.argv[2]
TAIL = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
FPS = 30
W, H = 1920, 1080

handler = functools.partial(SimpleHTTPRequestHandler, directory=str(HTML.parent))
httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{httpd.server_address[1]}/{quote(HTML.name)}?paused=1"

from playwright.sync_api import sync_playwright

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--force-color-profile=srgb", "--disable-lcd-text",
        "--hide-scrollbars", "--force-device-scale-factor=1"])
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_function("typeof window.ppDuration === 'number'", timeout=60_000)
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
    dur_ms = page.evaluate("window.ppDuration")
    n = round((dur_ms / 1000 + TAIL) * FPS)
    log(f"{HTML.name}: ppDuration={dur_ms}ms (+{TAIL}s tail) -> {n} frames")

    cdp = page.context.new_cdp_session(page)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "8",
        "-pix_fmt", "yuv444p", OUT], stdin=subprocess.PIPE)
    clip = {"x": 0, "y": 0, "width": W, "height": H, "scale": 1}
    for f in range(n):
        t_ms = min(f * 1000 / FPS, dur_ms)  # clamp: hold final frame through tail
        page.evaluate("t => ppSeek(t)", t_ms)
        shot = cdp.send("Page.captureScreenshot", {"format": "png", "clip": clip})
        ff.stdin.write(base64.b64decode(shot["data"]))
    ff.stdin.close()
    rc = ff.wait()
    if errs: log(f"PAGE ERRORS: {errs[:3]}")
    if rc != 0: sys.exit(f"FATAL: ffmpeg exited {rc}")
    log(f"done -> {OUT}")
    sys.stdout.flush()
    import os; os._exit(0)  # browser.close() hangs on this machine
