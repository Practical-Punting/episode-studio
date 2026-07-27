"""Prove the nine-episode midroll window.

Builds a synthetic PP-EP13..PP-EP24 tree whose midroll paragraphs are the real
pool lines used in order (L[N mod 10]), plus a PP-EP98 decoy, then:

  1. every episode EP13..EP24 must PASS  (EP23 is the one that matters - its
     legitimate repeat of L3 sits exactly ten back at EP13)
  2. PP-EP98 must never enter a window   (numeric ordering, not mtime)
  3. an injected duplicate at EP20 must FAIL
  4. the same, end to end through render_ready.py as a subprocess

Run:  python test_midroll_window.py
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(_REPO, ".claude", "skills", "pp-episode-production", "scripts")
POOL_MD = os.path.join(_REPO, "docs", "midroll-line-pool.md")

# --- load render_ready.py as a module so we can test its helpers directly ----
spec = importlib.util.spec_from_file_location("rr", os.path.join(SCRIPTS, "render_ready.py"))
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

fails = []
def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)

# --- parse the ten lines out of the pool file -------------------------------
md = open(POOL_MD, encoding="utf-8").read()
POOL = {}
for m in re.finditer(r"^### (L\d)\n> (.+?)$", md, re.M):
    POOL[m.group(1)] = m.group(2).strip()

print("=" * 78)
print("STEP 0 - the pool file parses and holds exactly ten lines")
print("=" * 78)
check(len(POOL) == 10, "ten lines found in docs/midroll-line-pool.md", f"got {len(POOL)}")
check(sorted(POOL) == [f"L{i}" for i in range(10)], "ids are L0..L9", ",".join(sorted(POOL)))
check(all(not re.search(r"\d", t) for t in POOL.values()), "no bare numerals in any line")
check(all("\u2014" not in t for t in POOL.values()), "no em dashes in any line")
check(all("this video" in t.lower() for t in POOL.values()), "every line says 'this video'")
uniq = len({t for t in POOL.values()})
check(uniq == 10, "all ten are distinct", f"{uniq} distinct")
print(f"  MIDROLL_WINDOW = {rr.MIDROLL_WINDOW}")
check(rr.MIDROLL_WINDOW == 9, "window is NINE, not ten")

FILLER = ("Gordon talks plainly about the form here, with no numbers in it at all, "
          "because the render ready scan hard fails on bare numerals and this is "
          "filler text for the synthetic episode used only by this test harness.")


def build_tree(root, override=None):
    """PP-EP13..PP-EP24 with midroll = L[N mod 10], plus a PP-EP98 decoy."""
    for n in list(range(13, 25)) + [98]:
        d = os.path.join(root, f"PP-EP{n:02d}", "docs")
        os.makedirs(d, exist_ok=True)
        # PP-EP98 is a DECOY: it carries L3, the line EP23 legitimately uses.
        # If the window were built by mtime or by a naive glob it would clash.
        line = POOL["L3"] if n == 98 else POOL[f"L{n % 10}"]
        if override and n in override:
            line = override[n]
        paras = [FILLER, FILLER, line, FILLER, FILLER]
        open(os.path.join(d, "spoken-words.txt"), "w", encoding="utf-8").write(
            "\n\n".join(paras) + "\n")
        json.dump({"episode": f"EP{n}", "build": {"midroll": {"beat": 3}}},
                  open(os.path.join(d, "episode.json"), "w", encoding="utf-8"))


root = tempfile.mkdtemp(prefix="pp-midroll-window-")
try:
    build_tree(root)

    print()
    print("=" * 78)
    print("STEP 1 - the clean cycle EP13..EP24 (unit level: midroll_clash)")
    print("=" * 78)
    for n in range(13, 25):
        ep_dir = os.path.join(root, f"PP-EP{n:02d}")
        mine = POOL[f"L{n % 10}"]
        which, compared = rr.midroll_clash(mine, ep_dir)
        check(which is None, f"EP{n} (uses L{n % 10}) is clean",
              f"{compared} prior compared, clash={which}")

    print()
    print("=" * 78)
    print("STEP 2 - EP23 is THE case: its window must span EP22..EP14 and EXCLUDE EP13")
    print("=" * 78)
    win = rr.midroll_window(os.path.join(root, "PP-EP23"))
    nums = [n for n, _ in win]
    print(f"  window = {nums}")
    check(len(nums) == 9, "exactly nine episodes in the window", str(len(nums)))
    check(nums == list(range(22, 13, -1)), "window is EP22..EP14 descending")
    check(13 not in nums, "EP13 is OUTSIDE the window (its L3 is ten back, so legal)")
    check(98 not in nums, "PP-EP98 decoy never enters the window (numeric ordering)")
    w, c = rr.midroll_clash(POOL["L3"], os.path.join(root, "PP-EP23"))
    check(w is None, "EP23 PASSES on L3 even though EP13 and EP98 both carry L3",
          f"clash={w}, compared={c}")

    print()
    print("=" * 78)
    print("STEP 3 - a TEN-episode window would have broken EP23 (the off-by-one)")
    print("=" * 78)
    w10, _ = rr.midroll_clash(POOL["L3"], os.path.join(root, "PP-EP23"), window=10)
    check(w10 is not None, "with window=10, EP23 FAILS against EP13 - the bug avoided",
          f"clash={w10}")

    print()
    print("=" * 78)
    print("STEP 4 - injected duplicate at EP20 must FAIL")
    print("=" * 78)
    # EP20 legitimately takes L0. Inject EP19's line (L9) instead - EP19 is one
    # episode back, well inside the window.
    build_tree(root, override={20: POOL["L9"]})
    w, c = rr.midroll_clash(POOL["L9"], os.path.join(root, "PP-EP20"))
    check(w is not None, "EP20 carrying EP19's line is caught", f"clash={w}, compared={c}")
    check(w == "PP-EP19", "and it names the right episode", str(w))

    print()
    print("=" * 78)
    print("STEP 5 - END TO END through render_ready.py (subprocess, real exit codes)")
    print("=" * 78)
    build_tree(root)                       # back to the clean cycle

    def run_rr(n):
        d = os.path.join(root, f"PP-EP{n:02d}", "docs")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "render_ready.py"),
                            os.path.join(d, "spoken-words.txt"),
                            "--episode", os.path.join(d, "episode.json")],
                           capture_output=True, text=True)
        return r.returncode, (r.stdout + r.stderr)

    rc, out = run_rr(23)
    midline = [l for l in out.splitlines() if "midroll" in l.lower()]
    check(rc == 0, "EP23 render_ready exits 0 (clean)", f"rc={rc}")
    print("     " + (midline[0].strip() if midline else "(no midroll line printed)"))

    build_tree(root, override={20: POOL["L9"]})
    rc, out = run_rr(20)
    midline = [l for l in out.splitlines() if "midroll" in l.lower()]
    check(rc != 0, "EP20 with the injected duplicate exits NON-ZERO", f"rc={rc}")
    check(any("VERBATIM" in l for l in midline), "and says VERBATIM in plain English")
    for l in midline:
        print("     " + l.strip())

    print()
    print("=" * 78)
    print(f"RESULT: {'ALL CHECKS PASS' if not fails else str(len(fails)) + ' FAILURE(S)'}")
    for f in fails:
        print("  ! " + f)
    print("=" * 78)
finally:
    shutil.rmtree(root, ignore_errors=True)

sys.exit(1 if fails else 0)
