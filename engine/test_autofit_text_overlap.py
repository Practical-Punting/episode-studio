"""autofit must see what card_check fails: text colliding with text.

🔴 EP51 C8, 27 Sep 2026. A panel `price` card — the 360px "4/1" sat 6px into the
headline's second line. card_check failed it ("hl collides with price — measured on
the INKED glyphs"); autofit reported "0 still failing" on the same page, because it had
rules for the logo, clipping, the card edge and foreign panels and NONE for
text-on-text, card_check's first rule. Nothing was shrunk and the build halted.

This runs autofit in --dry-run (it writes nothing) on a COPY of EP51's own export and
asks whether it sees C8 at all. On the pre-fix autofit_cards.py it does not.

Run: python engine/test_autofit_text_overlap.py
"""
import os
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
AUTOFIT = os.environ.get("AUTOFIT") or os.path.join(SCRIPTS, "autofit_cards.py")
PAGE = "ep51-c08-often-shoots-for-longshots.html"
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


src = ep_paths.episode_dir(51) / "overlay" / "export"
if not (src / PAGE).is_file():
    print(f"  ({PAGE} not on this machine — SKIPPED, not assumed)")
    sys.exit(0)
tmp = tempfile.mkdtemp(prefix="autofit_overlap_")
try:
    dst = os.path.join(tmp, "export")
    shutil.copytree(src, dst)
    page = open(os.path.join(dst, PAGE), encoding="utf-8").read()
    # the page as AUTHORING left it: drop any autofit rule a later run may have written
    import re
    page = re.sub(r"/\*PP-AUTOFIT\*/.*?/\*/PP-AUTOFIT\*/", "", page, flags=re.S)
    open(os.path.join(dst, PAGE), "w", encoding="utf-8").write(page)
    r = subprocess.run([sys.executable, AUTOFIT, dst, "--only", "c08", "--dry-run"],
                       capture_output=True, text=True, encoding="utf-8", timeout=300,
                       env=dict(os.environ, PYTHONPATH=SCRIPTS))
    out = r.stdout + r.stderr
    check("1 still failing" in out,
          "autofit SEES the headline/price collision card_check fails", out.strip()[-200:])
    check("collides with hl" in out and "price" in out,
          "  and names the price as the lever, the headline as what it hits",
          out.strip()[-200:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\nautofit text overlap: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
