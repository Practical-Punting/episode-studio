"""The `price` block keeps a gap between the headline (or quote) and its figure.

🔴 EP51 C8, 27 Sep 2026. On the PANEL layout the price row followed the headline
directly, and Anton at 0.84 leading draws its figure's ink ABOVE its own line box, so a
360px "4/1" touched "FOR LONGSHOTS". The shipped EP28 C2 had the same fault into its
quote — "6/4" through "were the race to be run" — and nothing caught it. Shrinking is
the wrong lever (autofit took C8 to 69% and it still touched). Jodie chose a gap.

`.pgap` is 36px of air that SHRINKS TO NOTHING when a card has no room, so crowded cards
lay out exactly as before (measured: every full-screen price card 0px different, the
crowded panel cards 0px different, identical autofit sizes on all 16 older cards).

This renders EP51's real C8 with the CURRENT block and requires card_check to pass it
AT FULL SIZE, with no autofit — on the pre-gap block it fails with the overlap.

PROVED FAIL-FIRST: AUTHOR_CARDS=<a skill copy whose assets carry the old price.html>.

Run: python engine/test_price_gap.py
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ep_paths  # noqa: E402

SCRIPTS = os.path.join(os.path.dirname(HERE), ".claude", "skills", "pp-episode-production",
                       "scripts")
PATH = os.environ.get("AUTHOR_CARDS") or os.path.join(SCRIPTS, "author_cards.py")
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


sys.path.insert(0, os.path.dirname(PATH))
sys.path.append(SCRIPTS)
spec = importlib.util.spec_from_file_location("ac_price", PATH)
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)
blk = ac.load_block("price")

css = blk.get("css", "")
check(bool(blk["schema"].get("flex_frame")), "the price block asks for a flex frame")
check(re.search(r"\.pgap\{[^}]*flex:0 1 \d+px", css) is not None,
      "  with a SHRINKABLE gap (flex:0 1 Npx), not a fixed one", css[-200:])
check('class="pgap"' in blk["markup"], "  placed in the markup above the price row")

ep = ep_paths.episode_dir(51)
epj = ep / "docs" / "episode.json"
if not epj.is_file():
    print("  (EP51 not on this machine — the render half is SKIPPED, not assumed)")
else:
    c8 = next(c for c in json.load(open(epj, encoding="utf-8"))["cards"] if c["id"] == "C8")
    c8 = dict(c8, fit=None)                       # full size: no autofit, no card fit
    tmp = tempfile.mkdtemp(prefix="price_gap_")
    try:
        dst = os.path.join(tmp, "export")
        shutil.copytree(ep / "overlay" / "export", dst)
        page = ac.render_card(c8, blk, ac.load_frame(c8.get("layout", "fullscreen")))
        out = os.path.join(dst, "c08-test.html")
        open(out, "w", encoding="utf-8").write(page)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "card_check.py"), out],
                           capture_output=True, text=True, encoding="utf-8", timeout=300)
        txt = (r.stdout + r.stderr).strip()
        check(r.returncode == 0 and "1/1 clean" in txt,
              "EP51 C8's 360px '4/1' clears its headline at FULL size", txt[-160:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print(f"\nprice gap: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
