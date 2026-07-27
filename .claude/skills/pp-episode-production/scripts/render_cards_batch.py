# Render MANY ppInit/ppSeek PP cards in ONE headless Chromium session — the
# browser launches once and webfonts are fetched once (cached for the rest), so
# a full episode's cards render in a fraction of render_card.py-per-card time
# (EP03: ~40s/card × 17 relaunching each time → one warm session instead).
#
# Usage:
#   python render_cards_batch.py <served_dir> <out_dir> [tail_secs=0.5] [name1.html name2.html ...]
# With no explicit names, renders every *.html in <served_dir> that exposes
# window.ppDuration (others — e.g. non-card pages — are skipped and reported).
# Output: <out_dir>/<card-stem>.mp4 for each card. Same encode as render_card.py
# (CRF 8 yuv444p, 30fps, in-animation + tail, final frame held over the tail).
import base64, subprocess, sys, time, pathlib, threading, functools, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

SERVE = pathlib.Path(sys.argv[1]).resolve()
OUTDIR = pathlib.Path(sys.argv[2]).resolve()
rest = sys.argv[3:]
TAIL = 0.5
if rest and rest[0].replace(".", "", 1).isdigit():
    TAIL = float(rest[0]); rest = rest[1:]
NAMES = [a for a in rest if a.endswith(".html")]
FPS = 30; W, H = 1920, 1080
OUTDIR.mkdir(parents=True, exist_ok=True)

handler = functools.partial(SimpleHTTPRequestHandler, directory=str(SERVE))
handler.log_message = lambda *a, **k: None
httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PORT = httpd.server_address[1]
cards = NAMES or sorted(p.name for p in SERVE.glob("*.html"))

from playwright.sync_api import sync_playwright
def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--force-color-profile=srgb", "--disable-lcd-text",
        "--hide-scrollbars", "--force-device-scale-factor=1"])
    done = 0; skipped = []
    for name in cards:
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        errs = []; page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(f"http://127.0.0.1:{PORT}/{quote(name)}?paused=1", wait_until="load")
        try:
            page.wait_for_function("typeof window.ppDuration === 'number'", timeout=8000)
        except Exception:
            skipped.append(name); page.close(); continue
        page.wait_for_function("document.fonts.status === 'loaded'", timeout=60000)
        page.wait_for_timeout(120)  # let a freshly-swapped webfont paint
        dur_ms = page.evaluate("window.ppDuration")
        n = round((dur_ms / 1000 + TAIL) * FPS)
        out = str(OUTDIR / (pathlib.Path(name).stem + ".mp4"))
        ff = subprocess.Popen([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "8",
            "-pix_fmt", "yuv444p", out], stdin=subprocess.PIPE)
        cdp = page.context.new_cdp_session(page)
        clip = {"x": 0, "y": 0, "width": W, "height": H, "scale": 1}
        for f in range(n):
            t_ms = min(f * 1000 / FPS, dur_ms)
            page.evaluate("t => ppSeek(t)", t_ms)
            shot = cdp.send("Page.captureScreenshot", {"format": "png", "clip": clip})
            ff.stdin.write(base64.b64decode(shot["data"]))
        ff.stdin.close(); rc = ff.wait()
        if errs: log(f"  PAGE ERRORS {name}: {errs[:2]}")
        page.close()
        if rc != 0: sys.exit(f"FATAL: ffmpeg exited {rc} on {name}")
        done += 1; log(f"{name}: ppDuration={dur_ms}ms -> {out}  ({done}/{len(cards)})")
    log(f"BATCH DONE: {done} rendered; skipped (no ppDuration): {skipped}")
    sys.stdout.flush(); os._exit(0)  # browser.close() hangs on this machine
