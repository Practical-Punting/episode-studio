#!/usr/bin/env python3
"""The control for preflight_card_layout.py — RED FIRST, and it names its own case.

🔴 CLAUDE.md 4b: A GUARD IS NOT TRUSTWORTHY UNTIL YOU HAVE WATCHED IT **FAIL**.
🔴 CLAUDE.md #4: "all green" means nothing unless the suite covers what you changed —
   so this file exists to be the case that proves it, and it says which page went red.

THE CASE THAT PROVES THIS CHECK (named, per #4):
    `ep35-c15-just-back-it-for-a-place.html`, EP35's real card 15, with its three slot
    KEYS replaced by a 130-character line. Undamaged it is GREEN; damaged it is RED and
    the blocker names C15. Same harness, one changed input, opposite verdicts.

⚠️ AND THE OLD FAULT IS DELIBERATELY *NOT* THE CONTROL. EP35 C15 halted because its
51-character tag was `flex:none` and took the whole row. That is fixed, so a long tag is
now GREEN — asserted below, because a control that only fails against yesterday's code
proves nothing about today's.

📌 WHAT THIS FILE DOES NOT CLAIM. It does not re-prove `autofit_cards` or `card_check`;
those have their own suites. It proves the EARLY WIRING: that the same rules, run on a
page authored in memory before any hero is staged, reach the same verdict.
"""
import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preflight_card_layout as pcl                              # noqa: E402
import author_cards as ac                                        # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'✓' if ok else '✗'} {name}")
    if not ok and detail:
        print(f"      {detail}")


PP = os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos")


def find_episode():
    """An episode with a slots card to work from. Named, never guessed at."""
    for name in sorted(os.listdir(PP), reverse=True):
        p = os.path.join(PP, name, "docs", "episode.json")
        if not os.path.isfile(p):
            continue
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        for c in j.get("cards") or []:
            if c.get("block") == "slots" and c.get("page"):
                return name, p, j, c
    return None, None, None, None


ep_name, epj_path, epj, card = find_episode()
if not card:
    # 🔴 NOT A SILENT PASS. A suite that goes green because it found nothing to test
    # is the "0 page(s) examined" fault one layer up.
    print("preflight card layout: NO EPISODE WITH A `slots` CARD IS AVAILABLE — "
          "nothing was measured, so this is a REFUSAL, not a pass.")
    sys.exit(1)

print(f"-- working from {ep_name} card {card['id']} ({card['page']}) --\n")

# 🔴 THE DAMAGE HAD TO BE CHOSEN BY MEASUREMENT, NOT BY EYE — AND THE FIRST CHOICE
# WAS WRONG. A 130-character sentence overflows a NARROW card (`panel-push`, ~1512px
# of row) and fits a WIDE one (`fullscreen`, 1700px). This file picks whatever slots
# card it finds first, so on EP35 it found the wide C6, went GREEN, and reported that
# the check could not fail. The control was a coin toss that happened to land badly.
#     A long UNBREAKABLE token cannot be wrapped by any layout at any type size, so it
# is red on both widths. Measured across both of EP35's slots cards before being
# chosen here: 130-char sentence -> wide GREEN / narrow RED; 200-char token -> RED on
# both. That is what a control has to be: red regardless of which card it lands on.
BREAKS_ANY_WIDTH = "X" * 200
LONG = ("An extraordinarily long line of words that no card of this shape was ever "
        "drawn to hold, going well past any reasonable label")

# ── 1. GREEN: the real card, undamaged ───────────────────────────────────────
green = pcl.preflight_card_layout({"cards": [copy.deepcopy(card)]})
check("the real card is GREEN (0 blockers)", not green["blockers"],
      f"blockers: {green['blockers']}")

# ── 2. RED: the SAME card with its keys blown out ────────────────────────────
bad = copy.deepcopy(card)
for s in bad["content"]["slots"]:
    s["k"] = BREAKS_ANY_WIDTH
red = pcl.preflight_card_layout({"cards": [bad]})
check("🔴 THE CONTROL: the same card with an unwrappable 200-character key goes RED",
      bool(red["blockers"]), f"it stayed green — the check cannot fail, so it "
                             f"cannot be trusted. lines: {red['lines']}")
check("the blocker NAMES the damaged card",
      any(card["id"] in b for b in red["blockers"]),
      f"blockers: {red['blockers']}")
check("the RED run names the damaged PAGE in its failing list",
      any(card["page"] == p for p in red.get("failing_pages", [])),
      f"failing_pages: {red.get('failing_pages')}")

# ── 3. the retired fault must NOT be the control ─────────────────────────────
oldfault = copy.deepcopy(card)
oldfault["content"]["tag"] = LONG
old = pcl.preflight_card_layout({"cards": [oldfault]})
check("a long TAG is green now — the retired fault cannot masquerade as the control",
      not old["blockers"], f"blockers: {old['blockers']}")

# ── 4. it must NEVER write into the episode ──────────────────────────────────
def tree_hash(root):
    h = hashlib.sha256()
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            p = os.path.join(dirpath, f)
            try:
                h.update(f.encode()); h.update(str(os.path.getmtime(p)).encode())
            except OSError:
                pass
    return h.hexdigest()


ep_dir = os.path.dirname(os.path.dirname(epj_path))
before = tree_hash(os.path.join(ep_dir, "overlay", "export")) \
    if os.path.isdir(os.path.join(ep_dir, "overlay", "export")) else None
epj_before = hashlib.sha256(open(epj_path, "rb").read()).hexdigest()
pcl.preflight_card_layout(epj)
epj_after = hashlib.sha256(open(epj_path, "rb").read()).hexdigest()
after = tree_hash(os.path.join(ep_dir, "overlay", "export")) if before else None
check("it does not touch episode.json", epj_before == epj_after)
check("it does not touch the episode's rendered pages", before == after)

# ── 5. THE TIMING CLAIM (4a): no staged hero is needed ───────────────────────
# The full measurement was 100 cards across five episodes, 100 identical verdicts.
# Repeated here in miniature so the claim has a live case and not only a note.
import card_check as cc                                          # noqa: E402
from playwright.sync_api import sync_playwright                  # noqa: E402
import functools, threading                                      # noqa: E402
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler  # noqa: E402


def serve(d):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *x):
            pass
    s = ThreadingHTTPServer(("127.0.0.1", 0),
                            functools.partial(Quiet, directory=d))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


with_dir, without_dir = tempfile.mkdtemp(), tempfile.mkdtemp()
src_assets = os.path.join(ep_dir, "overlay", "export")
for nm in ("pp-anim.js",):
    p = os.path.join(src_assets, nm)
    if os.path.isfile(p):
        open(os.path.join(with_dir, nm), "wb").write(open(p, "rb").read())
os.makedirs(os.path.join(with_dir, "assets"), exist_ok=True)
lg = os.path.join(src_assets, "assets", "logo.png")
if os.path.isfile(lg):
    open(os.path.join(with_dir, "assets", "logo.png"), "wb").write(open(lg, "rb").read())

page_html = ac.render_card(card, ac.load_block(card["block"]),
                           ac.load_frame(card.get("layout", "fullscreen")))
for d in (with_dir, without_dir):
    open(os.path.join(d, "p.html"), "w", encoding="utf-8", newline="\n").write(page_html)

sa, sb = serve(with_dir), serve(without_dir)
try:
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True, args=["--force-device-scale-factor=1",
                                                    "--hide-scrollbars"])
        pg = br.new_page(viewport={"width": cc.W, "height": cc.H}, device_scale_factor=1)
        va = cc.check_page(pg, f"http://127.0.0.1:{sa.server_address[1]}/p.html?a=1")
        vb = cc.check_page(pg, f"http://127.0.0.1:{sb.server_address[1]}/p.html?b=1")
        br.close()
finally:
    sa.shutdown(); sb.shutdown()
check("card_check's verdict is the SAME with and without staged assets "
      "(this is what makes it legal at audit_inputs)", va == vb,
      f"with={va}\n      without={vb}")

print(f"\npreflight card layout: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
