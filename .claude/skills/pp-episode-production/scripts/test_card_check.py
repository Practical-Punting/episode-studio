#!/usr/bin/env python3
"""Prove card_check.py actually catches the bug it exists for.

    python test_card_check.py

A checker that only ever passes things which already pass is a green light you
wrote yourself. This runs it against `testdata/ep12-c10-BEFORE-FIX.html` — EP12's
C10 as it stood before the collision was fixed — and requires a NON-ZERO exit.

The fixture's dependencies (pp-anim.js, assets/logo.png) are copied in from the
skill's canonical assets at run time rather than committed beside it, so there is
no second copy of either to drift.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
FIXTURE = os.path.join(HERE, "testdata", "ep12-c10-BEFORE-FIX.html")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                        # noqa: BLE001
        pass


def stage(tmp, page):
    shutil.copy(page, tmp)
    shutil.copy(os.path.join(ASSETS, "pp-anim.js"), tmp)
    os.makedirs(os.path.join(tmp, "assets"), exist_ok=True)
    shutil.copy(os.path.join(ASSETS, "assets", "logo.png"),
                os.path.join(tmp, "assets", "logo.png"))
    return os.path.join(tmp, os.path.basename(page))


def check(page):
    r = subprocess.run([sys.executable, os.path.join(HERE, "card_check.py"), page],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


fails = []
with tempfile.TemporaryDirectory() as tmp:
    rc, out = check(stage(tmp, FIXTURE))
    print(out.strip())
    if rc == 0:
        fails.append("card_check PASSED the pre-fix C10 — the checker does not work")
    elif "FOREIGN PANEL" not in out:
        fails.append("it failed, but not for the collision reason")
    else:
        print("\n  ✓ card_check FAILS the pre-fix C10, naming the collision")

    # And it must still pass the card as it actually shipped, or it is just noisy.
    media = os.environ.get("PP_VIDEOS_DIR") or r"G:\My Drive\PP Videos"
    shipped = os.path.join(media, "PP-EP12", "overlay", "export",
                           "ep12-c10-down-in-class.html")
    if os.path.exists(shipped):
        with tempfile.TemporaryDirectory() as t2:
            rc2, out2 = check(stage(t2, shipped))
            if rc2 != 0:
                fails.append(f"card_check FAILED the shipped, fixed C10:\n{out2}")
            else:
                print("  ✓ card_check PASSES the shipped, fixed C10")
    else:
        print(f"  · skipped the shipped-card half: {shipped} not present")

print()
for f in fails:
    print(f"  ✗ {f}")
print("card_check regression: " + ("FAILED" if fails else "PASS"))
sys.exit(1 if fails else 0)
