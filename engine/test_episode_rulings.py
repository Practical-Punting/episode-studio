#!/usr/bin/env python3
"""ONE EPISODE'S OWN RULINGS REACH THE WRITER — AND ARE CHECKED. (EP60, 17 Nov 2026.)

    python engine/test_episode_rulings.py
    BOARD_URL=https://…/episode-studio python engine/test_episode_rulings.py

Hugh's Batch 1 rulings (EP60-EP69, GH02-GH04) are per-episode decisions about the
script. Until today the script commission read nothing from the rail, so none of them
could reach the writer. EP60's draft opened on the studio's own hook, kept the two
bookmaker paragraphs Hugh cut, and added a line nobody approved.

WHAT THIS PROVES, on EP60's REAL captured article:
  A. the hook gate — a draft that does not open on the approved hook is refused; one
     that does passes (curly/straight apostrophe and case forgiven on both sides);
  B. the leave-out gate — the notes' quotes resolve to EXACTLY the two paragraphs meant;
     a lift from one, or a figure only they print, is refused; the kept TAB paragraph's
     own figures ("two dollar fifty", "roughly fifteen per cent") still pass;
  C. notes no draft could obey (a quote matching no paragraph, too short, ambiguous) are
     caught BEFORE an attempt;
  D. a fact the notes tell Gordon to say is approved words for the figure check (EP61's
     "Rosehill barrier figures run to 2002"), and a "Leave out:" quote licenses nothing;
  E. 🔒 THE CONTROL: no hook and no notes changes NOTHING — empty brief, empty gate, the
     same licence, and no rulings block in the writer's brief (proved byte-identical to
     the pre-route providers.py, e4c899b, on 17 Nov 2026 — see the note at that case);
  F. the board, in a real browser: the notes box saves to `script_notes`, and an empty
     box sends the patch the board always sent.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import episode_rulings as R                                            # noqa: E402
import script_fidelity as sf                                           # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))
LIVE = os.environ.get("BOARD_URL", "").rstrip("/")
PASS, FAIL = [], []
EP = 60


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


def capture(n: int):
    hits = sorted((PP / "docs").glob(f"EP{n:02d}-source-article-*.md"))
    return hits[0] if hits else None


HOOK = ("What\u2019s a roving banker? Why does a place bet sometimes pay nothing? "
        "Every horse racing bet type in plain words.")
NOTES = ('Leave out: "If you are betting with a bookmaker using the Best Fluctuations option"\n'
         'Leave out: "When betting with bookmakers their percentages will vary"\n'
         'Keep the TAB "roughly 15%" paragraph. "Tote take" is fine; never say "tax".\n'
         "No added lines beyond the article and the standard furniture.\n"
         "Credit: the Practical Punting team (no byline).")
EP60 = {"ep_number": 60, "hook": HOOK, "byline": "What Is the Best Type of Bet?",
        "script_notes": NOTES}

cap_path = capture(EP)
if not cap_path:
    print(f"EP{EP}'s capture is not on this machine — cannot run the real-article cases")
    sys.exit(1)
CAP = cap_path.read_text(encoding="utf-8")
OPEN = ("What's a roving banker? Why does a place bet sometimes pay nothing? Every horse "
        "racing bet type in plain words. ")
TAB = ("If you bet a hundred times at the TAB on two dollar fifty win chances, you've got "
       "to get past roughly fifteen per cent.")

print("\n-- A. the hook gate --")
got = R.check("You've probably had a go at most of them by now. " + TAB, CAP, EP60)
check("🔴 EP60's refused opening (the studio's own hook) is refused",
      any("open with the approved hook" in g for g in got), str(got))
check("  a draft that opens on the hook passes",
      R.check(OPEN + TAB, CAP, EP60) == [], str(R.check(OPEN + TAB, CAP, EP60)))
check("  case and the straight/curly apostrophe are forgiven",
      R.check(OPEN.upper().replace("'", "\u2019") + TAB, CAP, EP60) == [])
check("  CONTROL: a line BEFORE the hook is refused",
      R.check("G'day. " + OPEN + TAB, CAP, EP60) != [])
check("  CONTROL: a hook with one word changed is refused",
      R.check(OPEN.replace("roving", "rolling") + TAB, CAP, EP60) != [])

print("\n-- B. the leave-out gate --")
found, probs = R.resolve(CAP, NOTES)
paras = R.paragraphs(CAP)
check("both quotes resolve, no problems", len(found) == 2 and probs == [], f"{found} {probs}")
check("  to the Best Fluctuations paragraph",
      bool(found) and paras[found[0][1]].startswith("If you are betting with a bookmaker"))
check("  and to the one after it",
      len(found) > 1 and paras[found[1][1]].startswith("When betting with bookmakers")
      and found[1][1] == found[0][1] + 1)
lift = (OPEN + "If you bet Best Fluctuation on a horse and it opens at eleven dollars but "
        "is so heavily backed it starts at four dollars you still receive the odds.")
got = R.check(lift, CAP, EP60)
check("🔴 a lift from the cut paragraph is refused", any("still says it" in g for g in got), str(got))
# Asked of the figure the gate's OWN reader extracts — it reads this one as 'eleven' (the
# "but" ends the figure), and the test is about the refusal, not the tokenising.
check("🔴 $11.00 — printed ONLY in the cut paragraph — is refused as a figure",
      any("only place the article prints it" in g and "eleven" in g for g in got), str(got))
got = R.check(OPEN + "The bookmaker may be betting a one hundred and ten per cent market.",
              CAP, EP60)
check("🔴 '110%' — printed only in the paragraph after it — is refused",
      any("leave out" in g.lower() for g in got), str(got))
got = R.check(OPEN + TAB + " Every horse in all six races is a four dollar chance.", CAP, EP60)
check("  the kept paragraphs' figures pass ($2.50, 15%, and $4.00 which a kept "
      "paragraph also prints)", got == [], str(got))
whole = R.check(OPEN + TAB, CAP, dict(EP60, script_notes=""))
check("  CONTROL: without the notes, the same lift is NOT refused by this gate",
      not any("leave out" in g.lower() for g in R.check(lift, CAP, dict(EP60, script_notes=""))))

print("\n-- C. notes no draft could obey are caught before an attempt --")
check("EP60's real notes: no problems", R.notes_problems(CAP, EP60) == [],
      str(R.notes_problems(CAP, EP60)))
check("  a quote in no paragraph is a problem",
      R.notes_problems(CAP, {"script_notes": 'Leave out: "The moon is made of cheese"'}) != [])
check("  a two-word quote is a problem (too short to pick one out)",
      R.notes_problems(CAP, {"script_notes": 'Leave out: "Best Fluctuations"'}) != [])
check("  an ambiguous quote is a problem",
      R.notes_problems(CAP, {"script_notes": "Leave out: the TAB takes"}) != []
      or R.notes_problems(CAP, {"script_notes": 'Leave out: "you need to"'}) != [])
check("  a trailing … is 'and the rest', not text",
      R.leave_out_quotes('Leave out: "When betting with bookmakers their percentages will vary…"')
      == ["When betting with bookmakers their percentages will vary"])

print("\n-- D. the notes as approved words for figures --")
spec = importlib.util.spec_from_file_location("eng_rulings_test", HERE / "engine.py")
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)
ep61 = {"ep_number": 61, "hook": "", "byline": "",
        "script_notes": "Say the Rosehill barrier figures run to 2002."}
line = "The Rosehill barrier figures run to two thousand and two."
check("🔴 a fact the notes give (2002) passes the figure check",
      sf.check(line, CAP, eng._approved_packaging_text(ep61)) == [])
check("  CONTROL: the same line without the notes is refused",
      sf.check(line, CAP, eng._approved_packaging_text(dict(ep61, script_notes=""))) != [])
check("  a 'Leave out:' line licenses nothing",
      "Best Fluctuations" not in R.licensed_notes(EP60) and "Credit" in R.licensed_notes(EP60))

print("\n-- E. 🔒 THE CONTROL: no hook and no notes changes nothing --")
for name, ep in (("no keys", {"ep_number": 60}),
                 ("NULLs", {"ep_number": 60, "hook": None, "script_notes": None}),
                 ("deliberate blanks", {"ep_number": 60, "hook": "", "script_notes": ""})):
    check(f"  {name}: empty brief", R.brief(ep) == "")
    check(f"  {name}: empty gate, whatever the script says",
          R.check("Anything at all, eleven dollars, " + paras[-1], CAP, ep) == [])
    check(f"  {name}: no notes problems", R.notes_problems(CAP, ep) == [])
old = {"ep_number": 60, "hook": "h", "byline": "b"}
check("  the licence is the old formula exactly when there are no notes",
      eng._approved_packaging_text(old) == "h \n b \n episode 60")


def brief_from(mod, ep, pp):
    """The prompt `_commission_script` builds, with the writer stubbed out."""
    seen = {}
    fake = types.ModuleType("commission")
    fake.TIMEOUT_SCRIPT_S = 1
    fake.verdict_instructions = lambda: "<<verdict>>"
    fake.commission = lambda **kw: seen.setdefault("prompt", kw["prompt"]) and {"_path": ""}
    fake.commission_with_repair = lambda **kw: kw["attempt"]()
    old_mod = sys.modules.get("commission")
    sys.modules["commission"] = fake
    try:
        prov = object.__new__(mod.RealProvider)
        prov.pp = pp
        d = pp / "PP-EP60"
        mod.RealProvider._commission_script(prov, ep, d)
    finally:
        if old_mod is not None:
            sys.modules["commission"] = old_mod
        else:
            sys.modules.pop("commission", None)
    return seen.get("prompt", "")


import providers as P_now                                              # noqa: E402
# ⚠️ THE ONE-TIME PROOF AND THE STANDING ONE ARE DIFFERENT CHECKS. On 17 Nov 2026 the
# no-hook brief was compared BYTE FOR BYTE against the pre-route providers.py (commit
# e4c899b) and was identical. That comparison cannot stand as a test — every later,
# legitimate edit to the brief would fail it. What stays true for good is below: with no
# hook and no notes there is NO rulings block, and EP60's brief differs from the bare one
# by EXACTLY that block and nothing else.
with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    pp = tdp / "pp"
    (pp / "docs").mkdir(parents=True)
    (pp / "docs" / cap_path.name).write_text(CAP, encoding="utf-8")
    bare = {"ep_number": 60, "title": "x", "hook": "", "byline": "", "script_notes": None}
    b_bare = brief_from(P_now, bare, pp)
    b_ep60 = brief_from(P_now, EP60, pp)
    check("🔒 no hook, no notes: the writer's brief has NO rulings block",
          bool(b_bare) and "THIS EPISODE'S OWN RULINGS" not in b_bare)
    check("🔒 ...and EP60's brief is the bare brief plus EXACTLY the rulings block",
          b_ep60.replace(R.brief(EP60), "", 1) == b_bare and R.brief(EP60) != "",
          f"bare {len(b_bare)} chars, EP60 {len(b_ep60)} chars, block {len(R.brief(EP60))}")
    check("  EP60's brief carries the hook word for word", HOOK in b_ep60)
    check("  ...and every line of the notes", all(l in b_ep60 for l in NOTES.splitlines()))
    check("  ...and says the hook replaces the writer's own opening",
          "REPLACES your opening framing line" in b_ep60)

# ══════════════════════════════════════════════════════════════════════════════
print("\n-- F. the board, in a real browser (Supabase stubbed, no rail touched) --")
STUB = """
window.__rows = { episodes: window.__ROWS__, messages: [] };
window.__updates = [];
function qb(table) {
  const t = {
    select(){ return t; }, order(){ return t; }, in(){ return t; }, eq(){ return t; },
    limit(){ return t; }, single(){ return t; },
    update(p){ window.__updates.push(p); return t; },
    insert(){ return t; }, upsert(){ return t; },
    then(res){ return Promise.resolve(
      { data: window.__rows[table] || [], error: null }).then(res); },
  };
  return t;
}
window.supabase = { createClient: () => ({
  auth: {
    getSession: async () => ({ data: { session: { user: { email: "jlralph@gmail.com" } } } }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe(){} } } }),
    signInWithOtp: async () => ({ error: null }), signOut: async () => ({ error: null }),
  },
  from: qb,
  channel: () => { const c = { on(){ return c; }, subscribe(cb){ if (cb) cb("SUBSCRIBED");
                   return c; }, unsubscribe(){} }; return c; },
  removeChannel: () => {},
})};
"""


def row(n, **kw):
    r = {"id": f"id{n}", "ep_number": n, "status": "queued", "title": f"Episode {n}",
         "hook": None, "byline": None, "needs_look": False, "title_approved": False,
         "script_read": False, "script_snapshot": None, "script_doc_url": None,
         "progress_pct": 0, "heartbeat_at": None, "claimed_by": None, "format": "single"}
    r.update(kw)
    return r


def serve(root: Path):
    import functools
    import http.server
    import socketserver
    import threading
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}"


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
if sync_playwright is None:
    check("playwright is installed for the board half", False, "pip install playwright")
else:
    base = LIVE or serve(REPO)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1400, "height": 1200})
        pg.add_init_script("window.__ROWS__ = " + json.dumps(
            [row(61, title="The Draw Part 1"), row(62, title="No Notes Here")]) + ";")
        for pat in ("**/supabase-js*", "**/*supabase*.js*"):
            pg.route(pat, lambda r: r.fulfill(status=200, content_type="application/javascript",
                                              body=STUB))
        pg.goto(base + "/index.html", wait_until="networkidle")
        pg.wait_for_selector(".lane", timeout=15000)
        check("the entry card has a notes box", pg.query_selector("#pe-notes-id61") is not None)
        lbl = pg.inner_text("[data-card='id61']") if pg.query_selector("[data-card='id61']") else ""
        check("  and calls the hook Gordon's first spoken line",
              "first spoken line" in lbl.lower(), lbl[:300])
        # 61 — with notes
        pg.fill("#pe-hook-id61", "Does the draw matter?")
        pg.fill("#pe-byline-id61", "What the barriers really tell you")
        pg.fill("#pe-notes-id61", "Say the Rosehill barrier figures run to 2002.")
        pg.click("[data-act='packaging-entry'][data-ep='id61']")
        pg.wait_for_timeout(600)
        ups = pg.evaluate("window.__updates")
        p61 = next((u for u in ups if u.get("hook") == "Does the draw matter?"), None)
        check("🔴 the notes save to script_notes, beside hook and byline",
              bool(p61) and p61.get("script_notes") == "Say the Rosehill barrier figures run to 2002."
              and p61.get("byline") == "What the barriers really tell you", repr(ups))
        # 62 — CONTROL: no notes typed
        pg.fill("#pe-hook-id62", "A hook")
        pg.fill("#pe-byline-id62", "A byline")
        pg.click("[data-act='packaging-entry'][data-ep='id62']")
        pg.wait_for_timeout(600)
        ups = pg.evaluate("window.__updates")
        p62 = next((u for u in ups if u.get("hook") == "A hook"), None)
        check("🔒 CONTROL: an empty notes box sends exactly the old patch {hook, byline}",
              p62 == {"hook": "A hook", "byline": "A byline"}, repr(p62))
        b.close()

print(f"\nepisode rulings: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
