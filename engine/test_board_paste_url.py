"""B6 — SAY NO AT THE PASTE, NOT EIGHTEEN STEPS IN.

A wrong link costs a claim, a capture, a commission and a halt before anybody finds out.
Two things are knowable the instant it is pasted — the host is in the string, and every
episode already on the rail is in memory — so both are checked there.

🔴 THE DUPLICATE IS THE EXPENSIVE ONE, and not merely untidy: the same article queued
twice takes a second episode number, a second capture, a second commission and a second
set of PAID b-roll, and the two only diverge once somebody notices.

⚠️ THINNESS IS DELIBERATELY NOT CHECKED AT PASTE TIME, and this suite asserts that it is
not pretended. It needs the article's TEXT; the board cannot fetch another origin (CORS);
and a guess from the URL would be a warning that is wrong half the time, which is the one
thing this studio refuses to ship (Jodie, 6 Aug 2026). It belongs to capture, where the
text exists.

RUNS THE REAL FUNCTIONS. app.js is not importable, so the two functions are sliced out of
it and executed in node — the behaviour is asserted, not the source text.

Run: python engine/test_board_paste_url.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP = Path(__file__).resolve().parent.parent / "app.js"
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


SRC = APP.read_text(encoding="utf-8")

# ── structure: it must run BEFORE anything is written ──────────────────────────
form = SRC.split('$("start-form").addEventListener')[1].split("\n});")[0]
check("the paste form asks before it inserts", "articleUrlProblem(url)" in form)
check("  and it returns without touching the database",
      form.index("articleUrlProblem(url)") < form.index("from(\"episodes\").insert"),
      "a check after the insert is not a check")
check("  and it does not disable the button first",
      form.index("articleUrlProblem(url)") < form.index('btn.disabled = true'),
      "a refused paste should leave the form usable, not greyed out")
check("thinness is NOT claimed to be checked here",
      "THINNESS IS DELIBERATELY NOT CHECKED" in SRC,
      "silence would read as covered; it needs the text and belongs to capture")

# ── behaviour: the real functions, in node ─────────────────────────────────────
node = shutil.which("node")
if not node:
    print("\n  (node not on PATH — the behaviour half is SKIPPED, not assumed)")
else:
    start, end = SRC.index("const PP_HOSTS"), SRC.index("/* messages.sender")
    harness = SRC[start:end] + """
const rows = JSON.parse(process.argv[1]);
globalThis.EPISODES = rows.rail;
const out = rows.cases.map((u) => articleUrlProblem(u));
console.log(JSON.stringify(out));
"""
    rail = [{"ep_number": 23, "status": "published",
             "source_url": "https://www.practicalpunting.com.au/track-secrets-part-3/"}]
    cases = [
        "https://practicalpunting.com.au/track-secrets-part-4/",          # 0 new
        "https://www.practicalpunting.com.au/track-secrets-part-3",       # 1 dupe
        "https://PRACTICALPUNTING.COM.AU/track-secrets-part-3/?utm=x#t",  # 2 dupe
        "https://example.com/some-article",                               # 3 wrong site
        "not a url",                                                      # 4 junk
        "https://blog.practicalpunting.com.au/x",                         # 5 subdomain
    ]
    r = subprocess.run([node, "-e", harness,
                        json.dumps({"rail": rail, "cases": cases})],
                       capture_output=True, text=True, timeout=60)
    got = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else None
    if got is None:
        check("the functions ran in node", False, r.stderr[-400:])
    else:
        check("a NEW Practical Punting article is allowed through", got[0] == "",
              got[0])
        check("the same article already on the rail is REFUSED", bool(got[1]), got[1])
        check("  and it names the episode it is already", "PP-EP23" in (got[1] or ""),
              "'already there' without saying WHERE is a dead end for the operator")
        check("  matched across www and a missing trailing slash", bool(got[1]),
              "the same article from a search result is the same article")
        check("  and across case, a query string and a fragment", bool(got[2]), got[2])
        check("a link to another site is REFUSED", bool(got[3]), got[3])
        check("  and it names the host it actually got",
              "example.com" in (got[3] or ""),
              "so she can see she pasted the wrong tab")
        check("something that is not a URL at all is REFUSED", bool(got[4]), got[4])
        check("a PP SUBDOMAIN is allowed", got[5] == "",
              "refusing these would be the guard inventing a rule nobody made")

print(f"\npaste-time url check: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
