"""The midroll window is a RANGE OF EPISODE NUMBERS, not "the nine nearest files".

🔴 THE FAULT (EP50, 27 Sep 2026). `midroll_window()` took the nine highest-numbered
earlier folders that HAD a `docs/spoken-words.txt`. The two-way EP49 has none — its
words live in turn/furniture files — so for EP50 the window slid back one, to EP40.
EP40 and EP50 both take pool line L0 (N mod 10), by design, exactly ten apart: the
one repeat the nine-window exists to allow. EP50 hard-failed a correct script at
`audit_inputs`, and "It's sorted — carry on" could not clear it, because a clear
re-runs the same check on the same files.

A missing episode must SHRINK the count compared, never WIDEN the reach.

Both copies are tested — render_ready.py (pre-render) and qc_episode.py (final QC)
carry the helper twice on purpose (qc_episode's integrity gate), so a fix to one
alone would have failed EP50 again at the very end of its build.

PROVED FAIL-FIRST: point SCRIPTS_DIR at the pre-fix copies and this goes red.

Run: python engine/test_midroll_window_gap.py
"""
import importlib.util
import os
import re
import shutil
import sys
import tempfile

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
    # its siblings (card_hold, …) come from the real scripts folder either way
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


def tree(root, eps, skip=(), dupe=None):
    """PP-EPnn folders whose midroll paragraph is L[n mod 10]; `skip` get no
    spoken-words.txt (the two-way shape); `dupe` = (ep, line_id) overrides one."""
    for n in eps:
        d = os.path.join(root, f"PP-EP{n:02d}-Some-Title", "docs")
        os.makedirs(d, exist_ok=True)
        if n in skip:
            open(os.path.join(d, "turns.json"), "w").write("[]")
            continue
        lid = dupe[1] if dupe and dupe[0] == n else f"L{n % 10}"
        open(os.path.join(d, "spoken-words.txt"), "w", encoding="utf-8").write(
            f"{FILLER}\n\n{POOL[lid]}\n\n{FILLER}\n")
    return lambda n: [p for p in os.listdir(root) if p.startswith(f"PP-EP{n:02d}")][0]


for modname in ("render_ready", "qc_episode"):
    mod = load(modname)
    print(f"\n── {modname}.py (window {mod.MIDROLL_WINDOW}) ──")
    root = tempfile.mkdtemp(prefix="midroll_gap_")
    try:
        # EXACTLY TODAY'S SHAPE: EP38..EP50, EP49 is a two-way with no spoken words.
        name = tree(root, range(38, 51), skip={49})
        ep50 = os.path.join(root, name(50))
        got = [n for n, _ in mod.midroll_window(ep50)]
        check(max(got) == 48 and min(got) >= 41,
              "EP50's window is EP41..EP49 by NUMBER, whatever exists", got)
        check(40 not in got, "  and EP40 (ten back, the pool's own repeat) is OUTSIDE it", got)
        which, compared = mod.midroll_clash(POOL["L0"], ep50)
        check(which is None, "EP50 taking L0 again after EP40 PASSES", which)
        check(compared == 8, "  and it says 8 compared, not a padded 9", compared)
        # the control: a genuine repeat inside the window still fails
        which, _ = mod.midroll_clash(POOL["L5"], ep50)
        check(which and which.startswith("PP-EP45"),
              "a real repeat inside the window (EP45's L5) still FAILS", which)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    root = tempfile.mkdtemp(prefix="midroll_gap_")
    try:
        # a duplicate AT the edge: EP41 carries L0 — nine back from EP50, inside.
        name = tree(root, range(38, 51), skip={49}, dupe=(41, "L0"))
        which, _ = mod.midroll_clash(POOL["L0"], os.path.join(root, name(50)))
        check(which and which.startswith("PP-EP41"),
              "a repeat NINE back (the window's edge) still FAILS", which)
    finally:
        shutil.rmtree(root, ignore_errors=True)

print(f"\nmidroll window gap: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
