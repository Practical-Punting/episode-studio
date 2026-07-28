# Render a fixed-size HTML page to a PNG via headless Chromium.
# For channel art, thumbnails, or any still that needs the real brand fonts.
# Usage: python render_still.py <page.html> <out.png> <width> <height>
#
# Serves the HTML's folder over localhost (Chrome blocks sibling fetches on
# file://) and waits for webfonts + images before capturing.
import base64, functools, pathlib, re, sys, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote, unquote

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                    # noqa: BLE001
        pass

HTML = pathlib.Path(sys.argv[1]).resolve()
OUT = sys.argv[2]
W, H = int(sys.argv[3]), int(sys.argv[4])

# --- EVERY LOCAL IMAGE MUST EXIST, CHECKED BEFORE THE BROWSER STARTS ---------
#
# TIGHTENED 28 Jul 2026, after EP13's thumbnail step halted on this:
#     playwright._impl._errors.TimeoutError: Page.wait_for_function:
#     Timeout 60000ms exceeded
#
# Nothing was checking for the image. The wait below is
#     document.images.every(i => i.complete && i.naturalWidth > 0)
# and a 404 image is `complete` with `naturalWidth === 0`, so that condition can
# NEVER become true and the wait burns its full 60 seconds. THE TIMEOUT WAS
# ACTING AS THE GUARD BY ACCIDENT — the right outcome for the wrong reason, and
# the message it produces is a Python stack trace into site-packages that names
# neither the page nor the missing file. An operator working from a browser has
# no chance with it.
#
# So: resolve every local `src` in the page and fail on the missing ones, by
# name, before Chromium is even launched. Remote URLs and data: URIs are skipped
# — they are not ours to vouch for.
_src = re.findall(r'<img[^>]+src="([^"]+)"', HTML.read_text(encoding="utf-8",
                                                            errors="replace"))
_missing = []
for s in _src:
    if s.startswith(("http://", "https://", "data:", "//")):
        continue
    if not (HTML.parent / unquote(s)).is_file():
        _missing.append(s)
if _missing:
    print(f"MISSING IMAGE(S) for {HTML.name}: {', '.join(_missing)}\n"
          f"  Looked in: {HTML.parent}\n"
          f"  The page references them and they are not there, so the render would "
          f"hang until its 60s timeout and fail with a Playwright stack trace instead "
          f"of telling you this.\n"
          f"  If the missing file is hero.png, it is THE PICKED COVER HERO — Jodie's "
          f"ruling of 28 Jul 2026, 'THE THUMBNAIL HERO IS THE PICKED COVER HERO, unless "
          f"there is a specific reason not to'. Copy it from the episode's "
          f"ebook/cover-src/hero.png, which is whichever hero was picked at the cover "
          f"gate.", file=sys.stderr)
    sys.exit(2)

handler = functools.partial(SimpleHTTPRequestHandler, directory=str(HTML.parent))
handler.log_message = lambda *a, **k: None
httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{httpd.server_address[1]}/{quote(HTML.name)}"

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=[
        "--force-color-profile=srgb", "--hide-scrollbars",
        "--force-device-scale-factor=1"])
    page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
    page.wait_for_function(
        "Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)",
        timeout=60_000)
    page.wait_for_timeout(250)
    cdp = page.context.new_cdp_session(page)
    shot = cdp.send("Page.captureScreenshot", {
        "format": "png",
        "clip": {"x": 0, "y": 0, "width": W, "height": H, "scale": 1},
        "captureBeyondViewport": True})
    pathlib.Path(OUT).write_bytes(base64.b64decode(shot["data"]))
    if errs:
        print("PAGE ERRORS:", errs[:3])
    print(f"wrote {OUT} ({W}x{H})")
    sys.stdout.flush()
    import os; os._exit(0)   # browser.close() hangs on this machine
