"""PP-EP and PP-GH share ONE midroll pool, so the repeat check must see both.

(Jodie, 9 Nov 2026.) PP Greyhounds (PP-GH01, PP-GH02 …) draws its midroll from the
same ten lines as the horse episodes. Before this, `midroll_window()` only globbed
`PP-EP*` and returned nothing at all for a PP-GH folder, so:
  - a PP-GH episode was never checked against anything, and
  - a PP-EP episode could repeat a PP-GH episode's line and pass.

A PP-GH episode takes its place in the shared sequence just after the PP-EP folder
created most recently before its own folder (derived from the folders, no list).

Both copies are tested — render_ready.py (pre-render) and qc_episode.py (final QC)
carry the helpers twice on purpose (qc_episode's integrity gate).

PROVED FAIL-FIRST: point SCRIPTS_DIR at the pre-change copies and this goes red.

Run: python engine/test_midroll_window_gh.py
"""
import importlib.util
import os
import re
import shutil
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.environ.get("SCRIPTS_DIR") or os.path.join(
    _REPO, ".claude", "skills", "pp-episode-production", "scripts")
POOL_MD = os.path.join(_REPO, "docs", "midroll-line-pool.md")

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def load(name):
    real = os.path.join(_REPO, ".claude", "skills", "pp-episode-production", "scripts")
    if real not in sys.path:
        sys.path.insert(0, real)
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


POOL = {m.group(1): m.group(2).strip() for m in
        re.finditer(r"^### (L\d)\n> (.+?)$", open(POOL_MD, encoding="utf-8").read(), re.M)}
FILLER = "Gordon talks plainly about the form here with no numbers in it at all."


def make(root, folder, line_id):
    d = os.path.join(root, folder, "docs")
    os.makedirs(d)
    open(os.path.join(d, "spoken-words.txt"), "w", encoding="utf-8").write(
        f"{FILLER}\n\n{POOL[line_id]}\n\n{FILLER}\n")
    time.sleep(0.05)            # creation order is the GH anchor; keep it unambiguous
    return os.path.join(root, folder)


def short(which):
    return which[:7] if which else which


for modname in ("render_ready", "qc_episode"):
    mod = load(modname)
    print(f"\n── {modname}.py (window {mod.MIDROLL_WINDOW}) ──")

    # TODAY'S SHAPE: EP47..EP55 on L[n mod 10], then PP-GH01 made after EP55.
    root = tempfile.mkdtemp(prefix="midroll_gh_")
    try:
        for n in range(47, 56):
            make(root, f"PP-EP{n}-Some-Title", f"L{n % 10}")
        gh01 = make(root, "PP-GH01", "L6")
        got = sorted(int(p) for p, _ in mod.midroll_window(gh01))
        check(got == list(range(47, 56)), "PP-GH01's window is EP47..EP55", got)
        which, compared = mod.midroll_clash(POOL["L6"], gh01)
        check(which is None and compared == 9, "PP-GH01 on L6 (last used EP46) PASSES",
              (which, compared))
        which, _ = mod.midroll_clash(POOL["L1"], gh01)
        check(short(which) == "PP-EP51", "control: PP-GH01 on L1 FAILS against EP51", which)

        # the horse episode AFTER it: GH01 takes one of its nine slots
        ep56 = make(root, "PP-EP56-Some-Title", "L6")
        win = mod.midroll_window(ep56)
        check(len(win) == 9 and min(p for p, _ in win) == 48,
              "EP56's window is PP-GH01 + EP48..EP55 (EP47 drops out)",
              [p for p, _ in win])
        which, _ = mod.midroll_clash(POOL["L6"], ep56)
        check(short(which) == "PP-GH01", "control: EP56 on L6 FAILS against PP-GH01", which)
        which, _ = mod.midroll_clash(POOL["L7"], ep56)
        check(which is None, "EP56 on L7 (EP47, now outside) PASSES", which)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # REGRESSION: with no PP-GH folder at all, nothing about PP-EP changes.
    root = tempfile.mkdtemp(prefix="midroll_gh_")
    try:
        for n in range(46, 57):
            make(root, f"PP-EP{n}-Some-Title", f"L{n % 10}")
        got = sorted(p for p, _ in mod.midroll_window(os.path.join(root, "PP-EP56-Some-Title")))
        check(got == list(range(47, 56)), "no PP-GH: EP56's window is still EP47..EP55", got)
        which, _ = mod.midroll_clash(POOL["L6"], os.path.join(root, "PP-EP56-Some-Title"))
        check(which is None, "no PP-GH: EP56 on L6 (ten back) still PASSES", which)
    finally:
        shutil.rmtree(root, ignore_errors=True)

print(f"\nmidroll window GH: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
