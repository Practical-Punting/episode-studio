# Render a fixed-size HTML page to a PNG via headless Chromium.
# For channel art, thumbnails, or any still that needs the real brand fonts.
# Usage: python render_still.py <page.html> <out.png> <width> <height>
#
# Serves the HTML's folder over localhost (Chrome blocks sibling fetches on
# file://) and waits for webfonts + images before capturing.
import base64, functools, pathlib, sys, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

HTML = pathlib.Path(sys.argv[1]).resolve()
OUT = sys.argv[2]
W, H = int(sys.argv[3]), int(sys.argv[4])

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
