#!/usr/bin/env python3
"""AN EPISODE CAN START WITH A TITLE AND NO BYLINE, AND NOTHING ASKS FOR ONE.

    python engine/test_packaging_entry.py
    BOARD_URL=https://…/episode-studio python engine/test_packaging_entry.py

EP22 is exactly this: a title, no byline. Two faults follow from it.

  1. THE BOARD LIES. A queued episode with no script says "Writing the script… no
     action needed yet" — the studio claiming it is on the job while it is in fact
     BLOCKED on words only Jodie can write. That is the Job-5 fault the words chip
     already fixed once, in its other direction.
  2. THE FIELDS CROSS. On EP21 the hook landed in the byline slot and the title in
     the hook slot, and had to be put right on the rail by hand.

So: ask for them, in their own boxes, before anything is drafted or built.

🔴 NULL MEANS NEVER SUPPLIED; "" MEANS SHE CHOSE TO LEAVE IT BLANK. That is the whole
mechanism, and it needs no new column. Checked against the real rail before relying on
it: every episode EP6-EP21 carries either a real string or NULL, and NOT ONE carries an
empty string, so "" is free to mean something. A field is never auto-filled and never
guessed — the only way to get "" is for a human to tick the box that says so.

THE FOUR THINGS THIS PROVES, which are the four the brief asks for:
  1. title but no byline/hook -> the build PAUSES cleanly at the entry step, no error,
     no red fault flag, no scramble, no invented words
  2. typing a hook and a byline lands EACH IN ITS OWN FIELD and the build carries on
  3. the fields CANNOT cross, and nothing is ever auto-invented
  4. an episode that already has both SKIPS the step entirely

🔴 THE BOARD HALF IS PROVED IN A REAL BROWSER against the rendered page, never by
reading app.js — that law was earned by a board fix reported working from the source
while the deployed page still carried the bug. Supabase is stubbed; no rail is touched.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []
LIVE = os.environ.get("BOARD_URL", "").rstrip("/")


def case(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


def serve(root: Path):
    import functools
    import http.server
    import socketserver
    import threading
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}"


# ══════════════════════════════════════════════════════════════════════════════
# PART A — THE ENGINE MUST NOT DRAFT, SPEND OR BUILD WITHOUT THE WORDS
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("PART A - the engine")
print("=" * 78)

spec = importlib.util.spec_from_file_location("eng", HERE / "engine.py")
eng = importlib.util.module_from_spec(spec)
sys.modules["eng"] = eng
try:
    spec.loader.exec_module(eng)
except Exception as e:                                                 # noqa: BLE001
    print(f"  !!  engine.py did not import: {e}")
    raise SystemExit(1)

HAS = hasattr(eng, "packaging_entry_pending")
case("engine.py exposes packaging_entry_pending()", HAS,
     "the predicate does not exist yet")

if HAS:
    p = eng.packaging_entry_pending
    case("a NULL hook is MISSING", p({"hook": None, "byline": "b"}) == ["hook"],
         repr(p({"hook": None, "byline": "b"})))
    case("a NULL byline is MISSING", p({"hook": "h", "byline": None}) == ["byline"],
         repr(p({"hook": "h", "byline": None})))
    case("both NULL -> both missing, hook first",
         p({"hook": None, "byline": None}) == ["hook", "byline"],
         repr(p({"hook": None, "byline": None})))
    case("an ABSENT key counts as missing (a brand-new row)",
         p({}) == ["hook", "byline"], repr(p({})))
    # THE DELIBERATE BLANK. "" is only ever written by a human ticking the box.
    case('"" is a DELIBERATE blank, not a missing one',
         p({"hook": "", "byline": ""}) == [], repr(p({"hook": "", "byline": ""})))
    case("both filled -> nothing pending",
         p({"hook": "h", "byline": "b"}) == [], repr(p({"hook": "h", "byline": "b"})))
    # CONTROL: whitespace is not a word. A space bar is not a decision.
    case("CONTROL: whitespace-only is still MISSING",
         p({"hook": "   ", "byline": "b"}) == ["hook"], repr(p({"hook": "   "})))
    # AND IT NEVER INVENTS. The predicate must not read title as a fallback.
    case("CONTROL: a TITLE does not stand in for a missing hook",
         p({"title": "Track Secrets", "hook": None, "byline": None}) == ["hook", "byline"])

print()
print("  the drafting pass must not spend a token on a wordless episode")


def _draft_watch_spy(rows):
    """Run the real _draft_watch over `rows` and report whether it commissioned."""
    spent = []
    seated = []

    fake_rail = types.SimpleNamespace(
        list_queued=lambda: rows,
        flag_needs_look=lambda *a, **k: spent.append(("FLAG", a)),
        seat_script_if_empty=lambda *a, **k: seated.append(a),
        set_fields=lambda *a, **k: None,
        progress=lambda *a, **k: None,
    )
    # ⚠️ THE SPY GOES ON `provider._commission_script`, WHICH IS WHAT THE PASS ACTUALLY
    # CALLS — not on the commission module. The first version of this test watched
    # `com.script`, a door the pass never opens, and _draft_watch's outer
    # `except Exception` swallowed the resulting AttributeError in silence. So the
    # CONTROL case reported "did not commission" for an episode that had every word it
    # needed, and would have called the guard proved for any implementation at all.
    fake_com = types.ModuleType("commission")
    fake_com.CommissionHalt = type("CommissionHalt", (Exception,),
                                   {"detail": None, "message": ""})
    fake_com._safe = lambda x: str(x)

    class Prov:
        pp = Path(os.environ["TMPDIR_PE"])

        def dir(self, ep):
            d = Prov.pp / f"PP-EP{int(ep['ep_number']):02d}"
            (d / "docs").mkdir(parents=True, exist_ok=True)
            return d

        def _commission_script(self, ep, d, gate=None):
            spent.append(("COMMISSION", ep.get("ep_number")))
            raise fake_com.CommissionHalt("stopped here on purpose — the spy has "
                                          "already seen what it needed to see")

    old_rail, old_com = eng.rail, sys.modules.get("commission")
    old_find, old_assert = eng.find_capture, eng.assert_capture_for_script
    eng.rail = fake_rail
    sys.modules["commission"] = fake_com
    # The capture EXISTS — so the only thing that can stop the pass is the words.
    cap = Prov.pp / "capture.md"
    cap.parent.mkdir(parents=True, exist_ok=True)
    cap.write_text("the article of record", encoding="utf-8")
    eng.find_capture = lambda *a, **k: cap
    eng.assert_capture_for_script = lambda *a, **k: cap
    try:
        eng._draft_watch(Prov())
    except Exception as e:                                             # noqa: BLE001
        spent.append(("RAISED", str(e)))
    finally:
        eng.rail, eng.find_capture, eng.assert_capture_for_script = \
            old_rail, old_find, old_assert
        if old_com is not None:
            sys.modules["commission"] = old_com
        else:
            sys.modules.pop("commission", None)
    return spent


import tempfile
with tempfile.TemporaryDirectory() as _td:
    os.environ["TMPDIR_PE"] = _td
    os.environ["ENGINE_COMMISSION"] = "1"

    wordless = [{"id": "a", "ep_number": 90, "status": "queued", "title": "A Title",
                 "hook": None, "byline": None, "needs_look": False,
                 "script_snapshot": None, "script_doc_url": None, "claimed_by": None,
                 "source_url": "https://example.invalid/x"}]
    out = _draft_watch_spy(wordless)
    case("a wordless episode is NOT commissioned (no tokens spent)",
         not any(k == "COMMISSION" for k, _ in out), repr(out))
    case("...and it is NOT given a red fault flag (this is her turn, not a fault)",
         not any(k == "FLAG" for k, _ in out), repr(out))
    case("...and the pass does not raise", not any(k == "RAISED" for k, _ in out),
         repr(out))

    # CONTROL: THE SAME EPISODE WITH ITS WORDS MUST STILL BE DRAFTED. Without this
    # the guard could be "never commission anything" and every case above would pass.
    worded = [dict(wordless[0], hook="A hook", byline="A byline", ep_number=91)]
    out2 = _draft_watch_spy(worded)
    case("CONTROL: an episode WITH its words still reaches the writer",
         any(k == "COMMISSION" for k, _ in out2) or any(k == "RAISED" for k, _ in out2),
         f"the pass stopped before commissioning even WITH words: {out2!r}")

    # And the fast path must not fire for a wordless episode either.
    if hasattr(eng, "_a_brand_new_episode_is_waiting"):
        old_rail = eng.rail
        eng.rail = types.SimpleNamespace(list_queued=lambda: wordless)

        class P2:
            pp = Path(_td)

            def dir(self, ep):
                return Path(_td) / "x"
        try:
            got = eng._a_brand_new_episode_is_waiting(P2())
        finally:
            eng.rail = old_rail
        case("the fast start path does not fire for a wordless episode", got is None,
             f"returned {got!r}")

# ══════════════════════════════════════════════════════════════════════════════
# PART B — THE BOARD, IN A REAL BROWSER
# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 78)
print("PART B - the board (real browser, stubbed Supabase)")
print("=" * 78)


def row(n, **kw):
    r = {"id": f"id{n}", "ep_number": n, "status": "queued", "title": f"Episode {n}",
         "hook": "A hook", "byline": "A byline", "needs_look": False,
         "title_approved": False, "script_read": False,
         "script_snapshot": None, "script_doc_url": None,
         "progress_pct": 0, "heartbeat_at": None, "claimed_by": None}
    r.update(kw)
    return r


ROWS = [
    # 1 — EP22 ITSELF: a title, and neither word. Her turn.
    row(22, title="Track Secrets — Part 2", hook=None, byline=None),
    # 2 — half-supplied: a hook but no byline. Still her turn.
    row(23, title="Half Way", hook="A hook that exists", byline=None),
    # 3 — DELIBERATELY BLANK: she ticked the box. NOT her turn any more.
    row(24, title="Blank On Purpose", hook="", byline=""),
    # 4 — the normal path: both words present, no script yet. The STUDIO's turn.
    row(25, title="Perfectly Normal", hook="A hook", byline="A byline"),
    # 5 — A SCRIPT ALREADY EXISTS and the byline is missing. The WORDS GATE owns this
    # one: it carries all three word boxes AND the script she approves them beside, so
    # the thin entry card must stand down rather than take the script off the screen.
    row(26, title="Script First", hook="A hook", byline=None,
        script_snapshot="Gordon says something."),
]

STUB = """
window.__rows = { episodes: window.__ROWS__, messages: [] };
window.__updates = [];
window.__realtime = [];
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
    signInWithOtp: async () => ({ error: null }),
    signOut: async () => ({ error: null }),
  },
  from: qb,
  channel: () => { const c = { on(){ return c; }, subscribe(cb){ if (cb) cb("SUBSCRIBED");
                   window.__realtime.push(c); return c; }, unsubscribe(){} }; return c; },
  removeChannel: () => {},
})};
"""


def run_board():
    from playwright.sync_api import sync_playwright
    base = LIVE or serve(REPO)
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1400, "height": 1200})
        pg.add_init_script(f"window.__ROWS__ = {json.dumps(ROWS)};")
        pg.route("**/supabase-js*", lambda r: r.fulfill(
            status=200, content_type="application/javascript", body=STUB))
        pg.route("**/*supabase*.js*", lambda r: r.fulfill(
            status=200, content_type="application/javascript", body=STUB))
        pg.goto(base + "/index.html", wait_until="networkidle")
        pg.wait_for_selector(".lane", timeout=15000)
        res = {}

        def card(n):
            return pg.query_selector(f"[data-card='id{n}']") or \
                pg.query_selector(f"#card-id{n}")

        res["html"] = pg.content()
        # Per-episode: the chip text, the lane it sits in, and the entry boxes.
        res["eps"] = {}
        for n in (22, 23, 24, 25, 26):
            info = pg.evaluate(
                """(n) => {
                  const all = [...document.querySelectorAll('.lane')];
                  let lane = null, cardEl = null;
                  for (const L of all) {
                    const c = [...L.querySelectorAll('*')].find(
                      e => e.textContent && e.textContent.includes('PP-EP' + n));
                    if (c) { lane = L.querySelector('h2')?.textContent?.trim(); break; }
                  }
                  const hook = document.getElementById('pe-hook-id' + n);
                  const by   = document.getElementById('pe-byline-id' + n);
                  const body = document.body.innerText;
                  return {
                    lane,
                    hasHookBox: !!hook, hasBylineBox: !!by,
                    hookVal: hook ? hook.value : null,
                    bylineVal: by ? by.value : null,
                    hookId: hook ? hook.id : null, bylineId: by ? by.id : null,
                    sameBox: !!hook && !!by && hook === by,
                  };
                }""", n)
            res["eps"][n] = info
        res["text"] = pg.inner_text("body")

        # ── point 2: TYPE the two words and save; capture the patch ──────────
        if pg.query_selector("#pe-hook-id22") and pg.query_selector("#pe-byline-id22"):
            pg.fill("#pe-hook-id22", "TRACK SECRETS")
            pg.fill("#pe-byline-id22", "What the track tells you before the race")
            btn = pg.query_selector('[data-act="packaging-entry"][data-ep="id22"]')
            if btn:
                btn.click()
                pg.wait_for_timeout(700)
            res["updates"] = pg.evaluate("window.__updates")
        else:
            res["updates"] = None
        b.close()
    return res


try:
    R = run_board()
except Exception as e:                                                 # noqa: BLE001
    print(f"  !!  the board did not render: {e}")
    R = None
    FAIL.append(("board render", str(e)))

if R:
    e22, e23, e24, e25, e26 = (R["eps"][n] for n in (22, 23, 24, 25, 26))
    txt = R["text"]

    print("\n  1) a title with NO byline/hook pauses cleanly at the entry step")
    case("EP22 is in the 'Your turn' lane", e22["lane"] == "Your turn",
         f"lane was {e22['lane']!r}")
    case("...it does NOT claim the studio is writing",
         "Writing the script" not in txt or "PP-EP22" not in txt.split("Writing the script")[0][-400:],
         "the board still says the studio is writing EP22")
    case("...the entry step is on screen with BOTH boxes",
         e22["hasHookBox"] and e22["hasBylineBox"],
         f"hook box {e22['hasHookBox']}, byline box {e22['hasBylineBox']}")
    case("...no red fault flag is raised for it",
         "Needs a look" not in txt)

    print("\n  3) the fields cannot cross, and nothing is invented")
    case("the hook box and the byline box are DIFFERENT elements",
         e22["hookId"] != e22["bylineId"] and not e22["sameBox"],
         f"{e22['hookId']} vs {e22['bylineId']}")
    case("the hook box starts EMPTY — the title is not poured into it",
         e22["hookVal"] == "", f"hook box held {e22['hookVal']!r}")
    case("the byline box starts EMPTY — nothing is guessed",
         e22["bylineVal"] == "", f"byline box held {e22['bylineVal']!r}")
    case("EP23's existing hook is shown in the HOOK box, not the byline box",
         e23["hookVal"] == "A hook that exists" and e23["bylineVal"] == "",
         f"hook={e23['hookVal']!r} byline={e23['bylineVal']!r}")

    print("\n  2) typing them lands each in its OWN rail field")
    ups = R["updates"] or []
    patch = next((u for u in ups if "hook" in u or "byline" in u), None)
    case("a patch was sent", patch is not None, f"updates seen: {ups!r}")
    if patch:
        case("hook -> hook", patch.get("hook") == "TRACK SECRETS", repr(patch))
        case("byline -> byline",
             patch.get("byline") == "What the track tells you before the race",
             repr(patch))
        case("the TITLE is not touched", "title" not in patch, repr(patch))
        # AND IT DOES NOT SMUGGLE AN APPROVAL. This step is the words, not the gate.
        case("it does NOT set title_approved (that is the words gate's click)",
             not patch.get("title_approved"), repr(patch))
        case("it does NOT set script_read", not patch.get("script_read"), repr(patch))

    print("\n  4) an episode that already has both skips the step entirely")
    case("EP25 gets NO entry boxes",
         not e25["hasHookBox"] and not e25["hasBylineBox"])
    case("EP25 still reads as the studio's turn, unchanged",
         e25["lane"] == "Waiting", f"lane was {e25['lane']!r}")
    case("EP24 (deliberately blank) also skips it",
         not e24["hasHookBox"] and not e24["hasBylineBox"])
    case("EP24 is back in Waiting, not badged as her turn",
         e24["lane"] == "Waiting", f"lane was {e24['lane']!r}")
    case("EP23 (half supplied) is STILL her turn",
         e23["lane"] == "Your turn" and e23["hasBylineBox"],
         f"lane {e23['lane']!r}, byline box {e23['hasBylineBox']}")

    print("\n  ordering: a script on the row means the WORDS GATE owns it, not this card")
    case("EP26 (script + missing byline) gets NO entry boxes",
         not e26["hasHookBox"] and not e26["hasBylineBox"],
         "the thin entry card replaced the words gate and took the script off screen")
    case("...and it is still her turn, on the words gate",
         e26["lane"] == "Your turn", f"lane was {e26['lane']!r}")
    case("...and the script is still reachable there",
         "w-byline-id26" in R["html"] or "edit-script" in R["html"],
         "the words gate did not render for it")

print()
print("=" * 78)
print(f"packaging entry: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    for n, w in FAIL:
        print(f"  - {n}" + (f"  [{w}]" if w else ""))
    raise SystemExit(1)
