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

# ══ BATCH 6 — THE CARD CAPTURE IS SHARDED ACROSS WORKER PROCESSES ════════════
#
# Frame capture is the long pole of `cards_render`: ~260 CDP screenshots per card, one
# card after another, and every card is INDEPENDENT of every other. Each frame is
# `ppSeek(t_ms)` at an explicit animation time and then a screenshot — nothing reads the
# wall clock — so the cards can be rendered in any order, or at once.
#
# 🔴 WHY PROCESSES AND NOT THREADS, AND WHY THE INNER LOOP IS UNTOUCHED.
# Playwright's sync API is bound to the thread that created it, so threads would each
# need their own browser anyway. Sharding into PROCESSES buys the thing that actually
# matters: **the per-card code path below is byte-for-byte the code that has always
# run.** Frame-identity is preserved by construction rather than by care — which is the
# whole control for this change (`the control is FRAME-IDENTICAL MP4s`, Jodie).
#
# ⚠️ THE COST THAT DECIDES THE NUMBER: each shard launches its OWN browser and fetches
# the webfonts again — the very saving the header above describes. So the fastest
# setting is NOT "as many shards as cores"; it is where the parallel win stops paying
# for the fixed launch cost. That is measured, not reasoned about — see CARD_SHARDS.
#
# ⚠️ AND EVERY GATE IS UPSTREAM OF THIS FILE. `card_check`, `autofit_cards` and the three
# asserts all run in `render_cards` BEFORE this script is invoked, and the title-card
# review moved out to `step_cards_render` in Aug. **Nothing in here can stop and ask a
# human**, which is the structural reason this is safe to parallelise and the HeyGen
# fetch (E37) is not: there, two of the five things raise EngineFlag.
#
# ── THE NUMBER, AND WHAT LOST ────────────────────────────────────────────────
# Measured 18 Aug 2026 on EP30's REAL 20 cards, in a scratch directory, machine
# otherwise idle, 8 logical cores. Serial ran TWICE — 431s and 451s — so read ±5% into
# every figure below and do not treat a small win as real.
#
#     shards   elapsed   speed-up   frames vs SHIPPED
#     1        431/451s  —          20/20 identical   the baseline
#     2        256s      1.72×      20/20 identical
#     3        202s      2.18×      20/20 identical   ⚠️ see the note below
#     4        137s      3.22×      20/20 identical   ← CHOSEN
#     6        117s      3.77×      20/20 identical   faster, and NOT taken — see why
#
# 🔴 WHY 4 AND NOT 6, WHICH IS GENUINELY FASTER. 117s vs 137s is a real 15% win, well
# outside the noise; this is not a tie being broken. It is declined on purpose. The one
# hazard left in this file is the `wait_for_timeout(120)` below — a FIXED DURATION
# waiting for a freshly-swapped webfont to paint — and its failure mode is SILENT: a
# card rendered in a fallback font still produces a perfectly valid MP4 that nothing
# downstream would question. That risk is LOAD-DEPENDENT, so spare cores are the only
# cheap defence against it. 6 shards on 8 cores leaves none. **3.22× with two cores in
# hand beats 3.77× with nothing in hand**, and if that judgement ever looks wrong it is
# one edit away.
#
# ⚠️ 3 SHARDS IS UNEXPLAINED AND RECORDED AS MEASURED. 202s against an ideal ~147s is
# proportionally worse than both 2 and 4, and 20 cards split 7/7/6 does not account for
# it. Possibly the 8-logical/4-physical core split. **Nobody has explained it, so nobody
# should repeat the number as if it were understood** — it does not affect the choice.
#
# ✅ THE CONTROL, RUN THE WAY IT HAD TO BE. Frame-identity was checked at every count on
# an idle machine AND at the shipping count with the machine DELIBERATELY SATURATED —
# two 4-shard renders at once, 8 browsers on 8 cores, each render taking 203s and 205s
# against 137s quiet, so the contention was real. **20/20 byte-identical to the clips
# EP30 actually shipped, in both.** A green that only appears on a quiet machine would
# have been a RED result (`a gate that is green or red by what else is running fails in
# the dangerous direction`) — this is not one.
#
# A constant, so a bad night is one edit and a restart rather than a code change.
CARD_SHARDS = 4

SERVE = pathlib.Path(sys.argv[1]).resolve()
OUTDIR = pathlib.Path(sys.argv[2]).resolve()
rest = [a for a in sys.argv[3:] if a != "--worker"]
IS_WORKER = "--worker" in sys.argv[3:]
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

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

# ── THE COORDINATOR. Shard the card list and run each slice as this same script.
# Round-robin, not contiguous blocks: card durations vary and consecutive cards tend to
# be similar, so blocks would leave one shard holding all the long ones.
if not IS_WORKER and CARD_SHARDS > 1 and len(cards) > 1:
    k = min(CARD_SHARDS, len(cards))
    shards = [cards[i::k] for i in range(k)]
    log(f"sharding {len(cards)} card(s) across {k} worker(s) "
        f"(CARD_SHARDS={CARD_SHARDS}); each launches its own browser")
    procs = [subprocess.Popen(
        [sys.executable, __file__, str(SERVE), str(OUTDIR), str(TAIL), "--worker", *s])
        for s in shards if s]
    rcs = [p.wait() for p in procs]
    bad = [i for i, rc in enumerate(rcs) if rc != 0]
    if bad:
        sys.exit(f"FATAL: shard(s) {bad} exited {[rcs[i] for i in bad]}")
    got = sorted(p.stem for p in OUTDIR.glob("*.mp4"))
    log(f"BATCH DONE (sharded {k}x): {len(got)} clip(s) in {OUTDIR}")
    sys.stdout.flush()
    os._exit(0)

from playwright.sync_api import sync_playwright

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
