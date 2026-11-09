"""THE MIDROLL RULE: every episode takes the pool line UNUSED LONGEST (Jodie, 9 Nov 2026).

It replaced `L[N mod 10]`, which broke when PP Greyhounds joined the pool: PP-GH01 took
L6 out of turn, so EP56 by N mod 10 would repeat it inside its own window — and every
horse episode after that would repeat the one before.

One definition: render_ready.pool_line_unused_longest(). The script commission names the
line it returns; twoway_furniture.pool_line() asks it too.

PROVED FAIL-FIRST: point SCRIPTS_DIR at the pre-change copies and this goes red (the
function does not exist there).

Run: python engine/test_midroll_pool_pick.py
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
REAL = r"G:\My Drive\PP Videos"

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


def make(root, folder, line_id, fname="spoken-words.txt"):
    d = os.path.join(root, folder, "docs")
    os.makedirs(d)
    if line_id:
        # wrapped across lines on purpose: whitespace between words is layout, not wording
        wrapped = POOL[line_id].replace(". ", ".\n", 2)
        open(os.path.join(d, fname), "w", encoding="utf-8").write(
            f"{FILLER}\n\n{wrapped}\n\n{FILLER}\n")
    time.sleep(0.05)
    return os.path.join(root, folder)


rr = load("render_ready")
pick = getattr(rr, "pool_line_unused_longest", None)
check(pick is not None, "render_ready has pool_line_unused_longest()")
if pick is None:
    print(f"\npool pick: {len(fails)} failed")
    sys.exit(1)

print("\n── synthetic ──")
root = tempfile.mkdtemp(prefix="midroll_pick_")
try:
    for n in range(46, 56):
        make(root, f"PP-EP{n}-Some-Title", f"L{n % 10}")
    ep56 = os.path.join(root, "PP-EP56-Some-Title")
    lid, text, last = pick(ep56)
    check(lid == "L6" and last.startswith("PP-EP46"),
          "no greyhound yet: EP56 gets L6, last used EP46 (same as N mod 10)", (lid, last))
    check(text == POOL["L6"], "  and the text is the pool's own line, verbatim")
    gh01 = make(root, "PP-GH01", "L6")
    lid, _, last = pick(gh01)
    check(lid == "L6" and last.startswith("PP-EP46"), "PP-GH01 gets L6 (its own L6 never counts)",
          (lid, last))
    lid, _, last = pick(ep56)
    check(lid == "L7" and last.startswith("PP-EP47"),
          "after PP-GH01 took L6, EP56 gets L7 — NOT N mod 10's L6", (lid, last))
    make(root, "PP-EP56-Some-Title", "L7")
    lid, _, _ = pick(ep56)
    check(lid == "L7", "EP56's own script does not change its answer", lid)
    lid, _, last = pick(os.path.join(root, "PP-EP57-Some-Title"))
    check(lid == "L8" and last.startswith("PP-EP48"),
          "EP57 gets L8 — N mod 10 would have given L7 and repeated EP56", (lid, last))
    # the window check agrees with the pick: the picked line is never inside the window
    which, _ = rr.midroll_clash(POOL["L8"], os.path.join(root, "PP-EP57-Some-Title"))
    check(which is None, "  and the repeat check passes EP57 on L8", which)
finally:
    shutil.rmtree(root, ignore_errors=True)

root = tempfile.mkdtemp(prefix="midroll_pick_")
try:
    # THE TWO-WAY SHAPE: EP49 keeps its midroll in a furniture file, not spoken-words.txt.
    for n in range(40, 50):
        make(root, f"PP-EP{n}-Some-Title", f"L{n % 10}",
             fname="twoway-furniture.txt" if n == 49 else "spoken-words.txt")
    lid, _, last = pick(os.path.join(root, "PP-EP50-Some-Title"))
    check(lid == "L0" and last.startswith("PP-EP40"),
          "control: EP49's L9 in a furniture file COUNTS — EP50 gets L0, not a 'never used' L9",
          (lid, last))
finally:
    shutil.rmtree(root, ignore_errors=True)

print("\n── the real folders ──")
if os.path.isdir(REAL):
    lid, _, last = pick(os.path.join(REAL, "PP-GH01"))
    check(lid == "L6", "real PP-GH01 → L6", (lid, last))
    lid, _, last = pick(os.path.join(REAL, "PP-EP56"))
    check(lid == "L7", "real EP56 → L7 (Jodie's ruling, 9 Nov)", (lid, last))
    # On the strict-rotation history the two rules agree from EP24 on. NOT EP23: EP14's
    # folder carries no pool line in any .txt (found 9 Nov 2026), so at EP23 L4 reads as
    # "never used" and unused-longest says L4 where N mod 10 said L3. History, not a fault.
    disagree = []
    for d in sorted(os.listdir(REAL)):
        m = re.match(r"PP-EP(\d+)", d)
        if not m or not (24 <= int(m.group(1)) <= 55):
            continue
        n = int(m.group(1))
        got = pick(os.path.join(REAL, d))[0]
        if got != f"L{n % 10}":
            disagree.append((n, got))
    check(not disagree, "EP24–EP55: unused-longest gives the same line N mod 10 did", disagree)
else:
    print("  (Drive not mounted — real-folder checks skipped)")

print(f"\npool pick: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
