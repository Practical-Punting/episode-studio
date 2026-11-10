"""author_ebook.ep_stem names a book from its episode folder: PP-EPNN (horse), PP-GHNN (PP Greyhounds)
and PP-HRNN (PP Harness, e-book only — Jodie, 11 Nov 2026).

    python test_ebook_stem.py

Fails on the pre-change code (PP-GH01 halted: 'not inside a PP-EPNN episode folder'), and the PP-HR
cases fail on the PP-GH-only version.
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import author_ebook as ae

fails = []


def check(ok, label, detail=""):
    print(("  ok   " if ok else "  FAIL ") + label + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def stem(folder):
    try:
        return ae.ep_stem(os.path.join("G:\\x", folder, "ebook"))
    except ae.Halt as h:
        return f"HALT: {h}"


check(stem("PP-EP54-Getting-together-Part-6") == "PP-EP54", "horse folder (renamed) -> PP-EP54", stem("PP-EP54-Getting-together-Part-6"))
check(stem("PP-EP09") == "PP-EP09", "horse folder (bare) -> PP-EP09")
check(stem("PP-GH01") == "PP-GH01", "PP Greyhounds folder -> PP-GH01", stem("PP-GH01"))
check(stem("PP-GH12-Some-Title") == "PP-GH12", "renamed PP-GH folder -> PP-GH12")
check(stem("PP-HR01") == "PP-HR01", "PP Harness folder -> PP-HR01", stem("PP-HR01"))
check(stem("PP-HR07-Some-Title") == "PP-HR07", "renamed PP-HR folder -> PP-HR07")
check(stem("PP-HRX01").startswith("HALT"), "CONTROL: PP-HRX01 is not a PP-HR folder")
check(stem("Inspirational-Women").startswith("HALT"), "CONTROL: any other folder still halts")
check(stem("PP-XX01").startswith("HALT"), "CONTROL: an unknown series still halts")
print(f"\nebook stem: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
