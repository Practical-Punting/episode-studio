"""The next pasted article must not be given a number that is already taken.

🔴 THE FAULT (found 27 Sep 2026, before it bit). The board numbers a paste
max(ep_number) + 1, and the rail is all it can see. The two-way EP49 has a Drive folder
and a capture but deliberately NO rail row, so with the rail at 48 the next paste would
also have been PP-EP49 — and `ep_paths.episode_dir(49)` globs `PP-EP49*`, so the engine
would have built a single-presenter episode straight into the two-way's folder, and
`twoway_split` would then have found two EP49 captures and refused.

The fix is `RESERVED_EPS` + `nextEpNumber()` in app.js. This asserts the behaviour by
running the real functions in node (the same slice test_board_paste_url uses), and then
— when the rail is reachable — asks the question that actually matters: does the number
the board would hand out RIGHT NOW already have a folder or a capture on the Drive?
That half derives from the Drive itself, so the next unrailed folder makes it go red
without anybody remembering to add a case.

Run: python engine/test_next_ep_number.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ep_paths  # noqa: E402

APP = HERE.parent / "app.js"
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


SRC = APP.read_text(encoding="utf-8")
form = SRC.split('$("start-form").addEventListener')[1].split("\n});")[0]
check("the paste numbers through nextEpNumber()", "nextEpNumber(" in form,
      "a bare max+1 in the form bypasses the reservations")

node = shutil.which("node")
if not node:
    print("\n  (node not on PATH — the behaviour half is SKIPPED, not assumed)")
    sys.exit(1 if FAIL else 0)

start, end = SRC.index("const PP_HOSTS"), SRC.index("/* messages.sender")
harness = SRC[start:end] + """
const a = JSON.parse(process.argv[1]);
globalThis.EPISODES = [];
console.log(JSON.stringify({
  next: a.maxes.map((m) => nextEpNumber(m)),
  reserved: RESERVED_EPS.map((r) => r.ep_number),
  paste: a.urls.map((u) => articleUrlProblem(u)),
}));
"""
EP49_URL = ("https://practicalpunting.com.au/pp-online/a-z-of-betting/form-analysis/"
            "range-of-form-analysis-techniques/fighting-a-complex-game-part-1-20031112")
EP55_URL = ("https://practicalpunting.com.au/pp-online/a-z-of-betting/form-analysis/"
            "range-of-form-analysis-techniques/is-the-trainer-so-important-part-2-20031210.html")
args = {"maxes": [48, 49, 50, 0, None, 54, 55],
        "urls": [EP49_URL, "https://www." + EP49_URL[8:] + "/",
                 "https://practicalpunting.com.au/some-new-article/", EP55_URL]}
r = subprocess.run([node, "-e", harness, json.dumps(args)],
                   capture_output=True, text=True, timeout=60)
got = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else None
if got is None:
    check("the functions ran in node", False, r.stderr[-400:])
    sys.exit(1)

nxt = got["next"]
check("rail at 48 -> the next paste is EP50, not EP49", nxt[0] == 50, nxt[0])
check("rail at 49 -> 50 (a reservation never pushes the number backwards)", nxt[1] == 50,
      nxt[1])
check("rail at 50 -> 51", nxt[2] == 51, nxt[2])
check("an empty rail still starts at 1", nxt[3] == 1 and nxt[4] == 1, nxt[3:])
check("pasting the two-way's own article is REFUSED", bool(got["paste"][0]),
      got["paste"][0])
check("  and it says which episode it already is", "PP-EP49" in got["paste"][0],
      got["paste"][0])
check("  across www and a trailing slash", bool(got["paste"][1]), got["paste"][1])
check("a new article is still allowed through", got["paste"][2] == "", got["paste"][2])
# EP55, the second two-way (5 Oct 2026): reserved the same way as EP49.
check("rail at 54 -> the next paste is EP56, not EP55", nxt[5] == 56, nxt[5])
check("rail at 55 -> 56", nxt[6] == 56, nxt[6])
check("pasting the second two-way's article is REFUSED as PP-EP55",
      "PP-EP55" in (got["paste"][3] or ""), got["paste"][3])

# ── the live question: is the number the board would hand out NOW already taken? ──
try:
    import rail
    rows = [x for x in rail.list_all() if x.get("ep_number") is not None
            and x["ep_number"] < rail.TEST_EP_FLOOR]
except Exception as e:  # noqa: BLE001 — offline is a skip, said out loud
    print(f"\n  (rail unreachable — the live half is SKIPPED, not assumed: {e})")
    rows = None

if rows is not None:
    mx = max((x["ep_number"] for x in rows), default=0)
    r = subprocess.run([node, "-e", harness, json.dumps({"maxes": [mx], "urls": []})],
                       capture_output=True, text=True, timeout=60)
    n = json.loads(r.stdout.strip().splitlines()[-1])["next"][0]
    folder = ep_paths.episode_dir(n)
    caps = sorted((ep_paths.PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    print(f"\n  rail max {mx} -> the next paste would be PP-EP{n:02d}")
    check(f"  PP-EP{n:02d} has no folder on the Drive yet", not folder.exists(),
          f"{folder} already exists — add it to RESERVED_EPS in app.js")
    check(f"  PP-EP{n:02d} has no capture in docs\\ yet", not caps,
          f"{[c.name for c in caps]} — add it to RESERVED_EPS in app.js")

print(f"\nnext episode number: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
