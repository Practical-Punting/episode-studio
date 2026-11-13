"""The next pasted article must not be given a number that is already taken.

🔴 THE FAULT (found 27 Sep 2026, before it bit). The board numbers a paste
max(ep_number) + 1, and the rail is all it can see. The two-way EP49 had a Drive folder
and a capture but NO rail row, so the next paste would also have been PP-EP49 — and
`ep_paths.episode_dir(49)` globs `PP-EP49*`, so the engine would have built a
single-presenter episode straight into the two-way's folder.

27 Sep – 13 Nov 2026 the fix was a hand-kept `RESERVED_EPS` list in app.js. 🔴 MIGRATION
009 (13 Nov 2026) RETIRED IT: two-ways now have normal rail rows (EP49, EP55, EP56
back-filled), so their numbers are on the rail and pasting their articles is refused by
the ordinary duplicate check. This test now proves:
  · `nextEpNumber` is plain max+1 and `RESERVED_EPS` is GONE (a list nobody maintains);
  · with the rail as it really is (two-way rows included), each two-way's article is
    refused as its own PP-EP number, in every spelling;
  · CONTROL: with the two-way rows taken OUT of the rail, the same paste is allowed —
    so it is the ROW doing the refusing, not a leftover list;
  · LIVE: the number the board would hand out now has no folder and no capture yet.

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
      "a bare max+1 in the form would be a second definition")
# Declared or USED, not merely named: the comment recording its retirement names it, and a
# guard that fires on the comment describing the thing is CLAUDE.md fault 1a.
import re  # noqa: E402
check("RESERVED_EPS is retired (no hand-kept list of numbers declared or used)",
      not re.search(r"(const|let|var)\s+RESERVED_EPS\b|RESERVED_EPS\s*\.", SRC))
check("the paste form writes format 'two-way' when the two-person box is ticked",
      'row.format = "two-way"' in form and "twowayin" in form)

node = shutil.which("node")
if not node:
    print("\n  (node not on PATH — the behaviour half is SKIPPED, not assumed)")
    sys.exit(1 if FAIL else 0)

B = ("https://practicalpunting.com.au/pp-online/a-z-of-betting/form-analysis/"
     "range-of-form-analysis-techniques/")
EP49_URL = B + "fighting-a-complex-game-part-1-20031112"
EP55_URL = B + "is-the-trainer-so-important-part-2-20031210"
EP56_URL = B + "class-improvement-and-bias-blues-part-3-20040108"
TWOWAY_ROWS = [{"ep_number": 49, "source_url": EP49_URL, "status": "published", "format": "two-way"},
               {"ep_number": 55, "source_url": EP55_URL, "status": "published", "format": "two-way"},
               {"ep_number": 56, "source_url": EP56_URL, "status": "published", "format": "two-way"}]

start, end = SRC.index("const PP_HOSTS"), SRC.index("/* messages.sender")
harness = SRC[start:end] + """
const a = JSON.parse(process.argv[1]);
globalThis.EPISODES = a.rows;
console.log(JSON.stringify({
  next: a.maxes.map((m) => nextEpNumber(m)),
  paste: a.urls.map((u) => articleUrlProblem(u)),
}));
"""


def run(rows, maxes, urls):
    r = subprocess.run([node, "-e", harness, json.dumps({"rows": rows, "maxes": maxes, "urls": urls})],
                       capture_output=True, text=True, timeout=60)
    if not r.stdout.strip():
        check("the functions ran in node", False, r.stderr[-400:])
        sys.exit(1)
    return json.loads(r.stdout.strip().splitlines()[-1])


urls = [EP49_URL, "https://www." + EP49_URL[8:] + "/", EP55_URL + ".html", EP55_URL,
        EP56_URL, EP56_URL + ".html", "https://practicalpunting.com.au/some-new-article/",
        "https://practicalpunting.com.au/some-new-article.html"]
got = run(TWOWAY_ROWS, [48, 54, 56, 0, None], urls)
nxt, p = got["next"], got["paste"]
check("rail at 56 (the two-ways on it) -> the next paste is EP57", nxt[2] == 57, nxt[2])
check("max+1 everywhere else (54 -> 55, 48 -> 49: nothing is skipped any more)",
      nxt[0] == 49 and nxt[1] == 55, nxt[:2])
check("an empty rail still starts at 1", nxt[3] == 1 and nxt[4] == 1, nxt[3:])
check("pasting EP49's article is REFUSED as PP-EP49", "PP-EP49" in (p[0] or ""), p[0])
check("  across www and a trailing slash", "PP-EP49" in (p[1] or ""), p[1])
check("EP55's article, .html and bare, both REFUSED as PP-EP55",
      "PP-EP55" in (p[2] or "") and "PP-EP55" in (p[3] or ""), p[2:4])
check("EP56's article, bare and .html, both REFUSED as PP-EP56",
      "PP-EP56" in (p[4] or "") and "PP-EP56" in (p[5] or ""), p[4:6])
check("a new article (with or without .html) is still allowed through",
      p[6] == "" and p[7] == "", p[6:])

ctl = run([], [56], [EP56_URL])
check("CONTROL: with the two-way rows taken off the rail, EP56's article is ALLOWED — "
      "so the refusal above comes from the ROW, not a leftover list", ctl["paste"][0] == "",
      ctl["paste"][0])

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
    n = run([], [mx], [])["next"][0]
    folder = ep_paths.episode_dir(n)
    caps = sorted((ep_paths.PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    print(f"\n  rail max {mx} -> the next paste would be PP-EP{n:02d}")
    check("  every two-way folder on the Drive has a rail row (49, 55, 56)",
          {49, 55, 56} <= {x["ep_number"] for x in rows if x.get("format") == "two-way"})
    check(f"  PP-EP{n:02d} has no folder on the Drive yet", not folder.exists(),
          f"{folder} already exists — it needs a rail row")
    check(f"  PP-EP{n:02d} has no capture in docs\\ yet", not caps,
          f"{[c.name for c in caps]} — it needs a rail row")

print(f"\nnext episode number: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
