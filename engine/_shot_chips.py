import sys
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--force-color-profile=srgb','--disable-lcd-text','--hide-scrollbars','--force-device-scale-factor=1'])
    pg = b.new_page(viewport={'width':1920,'height':1080}, device_scale_factor=1)
    pg.goto(url, wait_until='load')
    pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60000)
    pg.screenshot(path=out, omit_background=True)
    b.close()
