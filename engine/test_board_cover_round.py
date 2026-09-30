#!/usr/bin/env python3
"""EP53 — "NEITHER" TURNED DOWN A COVER ROUND SHE NEVER SAW.

    python engine/test_board_cover_round.py            # against the local files
    BOARD_URL=https://…/episode-studio python engine/test_board_cover_round.py

30 Sep 2026: after Jodie pressed Send on "Neither — ask for different ones", the card
kept showing the OLD pictures with her note still in the box, and the new round only
appeared after a manual refresh. So she pressed Send again, and round 2 was turned
down 15 seconds after it arrived, without her seeing it.

  cause 1  the note box counted as "being typed in", so renderBoard() paused the whole
           board after Send and nothing released it;
  cause 2  the engine opens a round BEFORE its pictures exist — cover_round goes up and
           the request is cleared while the rail still carries the OLD pair — so the
           board offered "Neither" again against a round that was still being made.

WHAT MUST HOLD, in a real browser against the rendered board:
  (a) after Send the card says "Making fresh covers from your notes…" at once, the box
      is gone, and there is no Send and no Neither until the new pair lands;
  (b) the new pair appears BY ITSELF — even while another box on the board is being
      typed in, which is what paused it;
  (c) a round cannot be turned down before it has been on the screen: a Send against a
      pair the rail has already replaced writes nothing;
  and an earlier round-1 tile names its round ("A1"), because a bare "A" is the pair
  on the board NOW.

Supabase is stubbed with a stand-in that REMEMBERS writes, so the board sees its own
Send and the test can play the engine's part. No rail is touched.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("BOARD_REPO") or HERE.parent)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []
LIVE = os.environ.get("BOARD_URL", "").rstrip("/")


def serve(root: Path):
    import functools, http.server, socketserver, threading          # noqa: E401
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    h.log_message = lambda *a, **k: None
    httpd = socketserver.TCPServer(("127.0.0.1", 0), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}"


def case(name, ok, why=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok and why else ""))


A1, B1 = "https://example.test/cover-A.png", "https://example.test/cover-B.png"
A2, B2 = "https://example.test/cover-A-r2.png", "https://example.test/cover-B-r2.png"
A3, B3 = "https://example.test/cover-A-r3.png", "https://example.test/cover-B-r3.png"

EP = {"id": "id53", "ep_number": 53, "status": "building", "title": "Basic Mistakes (Part 5)",
      "hook": "A hook", "byline": "A byline", "needs_look": False, "title_approved": True,
      "script_read": True, "script_snapshot": "Gordon says something.",
      "words_approved_at": "2026-09-30T10:48:00+00:00",
      "script_approved_at": "2026-09-30T10:48:00+00:00",
      "script_locked_at": "2026-09-30T10:48:00+00:00", "script_doc_url": None,
      "heygen_name": "PP-EP53 — Basic Mistakes (Part 5)",
      "render_started_at": "2026-09-30T10:50:00+00:00",
      "progress_pct": 33, "progress_step": "Waiting on you — pick a cover (A or B)",
      "heartbeat_at": None, "claimed_by": "pp-engine",
      "cover_round": 1, "cover_a_url": A1, "cover_b_url": B1, "cover_rounds": [],
      "cover_choice": None, "cover_more_requested_at": None, "cover_more_note": None}
# A second episode with a box on it, so the board can be PAUSED by typing elsewhere.
OTHER = {"id": "id60", "ep_number": 60, "status": "queued", "title": "Another episode",
         "hook": None, "byline": None, "needs_look": False, "title_approved": False,
         "script_read": False, "script_snapshot": None, "script_doc_url": None,
         "progress_pct": 0, "heartbeat_at": None, "claimed_by": None}

# The lingering card (30 Sep): "A2" was picked AND built from, and the card still asked.
PICKED = dict(EP, id="id54", ep_number=54, title="Picked from an earlier round",
              cover_round=3, cover_a_url=A3, cover_b_url=B3, cover_choice="A2",
              cover_rounds=[{"round": 1, "a_url": A1, "b_url": B1},
                            {"round": 2, "a_url": A2, "b_url": B2}])
# …and the control: a round that does not exist is NOT a pick, so the card stays.
NOT_PICKED = dict(PICKED, id="id55", ep_number=55, title="Not a real round", cover_choice="A4")

STUB = """
window.__rows = { episodes: window.__ROWS__, messages: [] };
window.__writes = [];
function qb(table) {
  const st = { f: [], patch: null, single: false };
  const t = {
    select(){ return t; }, order(){ return t; }, in(){ return t; }, limit(){ return t; },
    eq(k, v){ st.f.push([k, v]); return t; }, single(){ st.single = true; return t; },
    update(p){ st.patch = p; return t; }, insert(){ return t; }, upsert(){ return t; },
    then(res){
      const all = window.__rows[table] || [];
      const hit = all.filter((r) => st.f.every(([k, v]) => r[k] === v));
      if (st.patch) {
        hit.forEach((r) => Object.assign(r, JSON.parse(JSON.stringify(st.patch))));
        window.__writes.push({ table, patch: st.patch });
      }
      const data = st.single ? (hit[0] ? JSON.parse(JSON.stringify(hit[0])) : null)
                             : JSON.parse(JSON.stringify(hit));
      return Promise.resolve({ data, error: null }).then(res);
    },
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

CARD = """(id) => {
  const c = document.querySelector('[data-card="' + id + '"]');
  if (!c) return null;
  return {
    text: c.textContent.replace(/\\s+/g, ' ').trim(),
    imgs: [...c.querySelectorAll('.covers:not(.dim) img')].map((i) => i.getAttribute('src')),
    note: c.querySelector('textarea[id^="askwhy-"]')?.value ?? null,
    hasBox: !!c.querySelector('textarea[id^="askwhy-"]'),
    hasSend: !!c.querySelector('[data-act="cover-more"]'),
    hasNeither: !!c.querySelector('[data-act="cover-more-open"]'),
    olderPicks: [...c.querySelectorAll('.covers.dim [data-pick]')].map((b) => b.getAttribute('data-pick')),
  };
}"""


def rail_set(pg, fields):
    """Play the ENGINE's part: change EP53's row on the stand-in rail."""
    pg.evaluate("(f) => Object.assign(window.__rows.episodes.find((r) => r.id === 'id53'), f)", fields)


def run():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1400, "height": 1200})
        pg.add_init_script(f"window.__ROWS__ = {json.dumps([EP, OTHER, PICKED, NOT_PICKED])};")
        pg.route("**/supabase-js*", lambda r: r.fulfill(
            status=200, content_type="application/javascript", body=STUB))
        try:
            pg.goto((LIVE or serve(REPO)) + "/index.html", wait_until="load")
            pg.wait_for_timeout(1500)
            card = lambda: pg.evaluate(CARD, "id53")                  # noqa: E731
            c0 = card()
            case("the cover card is on the board with round 1's pair",
                 bool(c0) and c0["imgs"] == [A1, B1], str(c0 and c0["imgs"]))
            if not c0:
                return

            print("\n-- a pick from an earlier round closes the card, like 'A' or 'B' does --")
            p54, p55 = pg.evaluate(CARD, "id54"), pg.evaluate(CARD, "id55")
            case("🔴 'A2' picked (round 3 showing): the card no longer asks her to pick",
                 bool(p54) and "pick the cover" not in p54["text"],
                 (p54 or {}).get("text", "")[:200])
            case("  CONTROL: 'A4' (no such round) is not a pick, so the card still asks",
                 bool(p55) and "pick the cover" in p55["text"], (p55 or {}).get("text", "")[:200])

            # ── (a) SEND ─────────────────────────────────────────────────────────
            print("\n-- (a) she presses Send on 'Neither' with a note --")
            pg.click('[data-card="id53"] [data-act="cover-more-open"]')
            pg.fill('[data-card="id53"] textarea[id^="askwhy-"]', "Australian horses please")
            pg.click('[data-card="id53"] [data-act="cover-more"]')
            pg.wait_for_timeout(600)
            c1 = card()
            w = pg.evaluate("window.__writes")
            case("the request reached the rail, with her note",
                 any(x["patch"].get("cover_more_note") == "Australian horses please"
                     and x["patch"].get("cover_more_requested_at") for x in w), str(w))
            case("🔴 the card says 'Making fresh covers from your notes…' at once",
                 "Making fresh covers from your notes" in c1["text"], c1["text"][:300])
            case("🔴 her note is no longer sitting in the box",
                 not c1["note"], f"box still holds {c1['note']!r}")
            case("🔴 no Send and no Neither while the covers are being made",
                 not c1["hasSend"] and not c1["hasNeither"],
                 f"Send={c1['hasSend']} Neither={c1['hasNeither']}")

            # ── the engine opens round 2 — OLD pictures still on the rail ───────
            print("\n-- the engine opens round 2 before its pictures exist --")
            rail_set(pg, {"cover_round": 2, "cover_more_requested_at": None, "cover_more_note": None,
                          "cover_rounds": [{"round": 1, "a_url": A1, "b_url": B1,
                                            "note": "Australian horses please"}]})
            pg.evaluate("loadAll()")
            pg.wait_for_timeout(500)
            c2 = card()
            case("🔴 still 'Making fresh covers' — the request is taken, the pair is not here",
                 "Making fresh covers" in c2["text"] and not c2["hasNeither"],
                 f"Neither={c2['hasNeither']} text={c2['text'][:200]}")

            # ── (b) the new pair lands WHILE the board is paused by typing elsewhere
            print("\n-- (b) round 2's pair lands while she is typing on another card --")
            other = pg.evaluate("""() => { const i = document.querySelector(
                '[data-card="id60"] input[type="text"], [data-card="id60"] textarea');
                return i ? i.id : null; }""")
            case("there is a box on the other card to type in", bool(other), "no input on id60")
            if other:
                pg.fill("#" + other, "half-typed")
            rail_set(pg, {"cover_a_url": A2, "cover_b_url": B2})
            pg.evaluate("loadAll()")
            pg.wait_for_timeout(500)
            c3 = card()
            paused = pg.evaluate("!!document.getElementById('pausebar') && "
                                 "!document.getElementById('pausebar').hidden")
            case("  (the board IS paused by that half-typed box — the pause bar shows)", paused,
                 "no pause bar: this case would not prove (b)")
            case("🔴 round 2's pair is on the card by itself — no refresh",
                 c3["imgs"] == [A2, B2], f"card shows {c3['imgs']}")
            case("  and Neither is back, for THIS pair",
                 c3["hasNeither"] and "Making fresh covers" not in c3["text"], c3["text"][:200])
            case("  and her half-typed words on the other card survived",
                 pg.evaluate(f"document.getElementById('{other}')?.value") == "half-typed")
            case("  the round-1 tile names its round ('A1', 'B1') — a bare 'A' is the pair NOW",
                 c3["olderPicks"] == ["A1", "B1"], str(c3["olderPicks"]))

            # ── (c) a stale Send must write nothing ─────────────────────────────
            print("\n-- (c) the rail moves on to round 3 behind the card, then Send --")
            n_before = len(pg.evaluate("window.__writes"))
            rail_set(pg, {"cover_round": 3, "cover_a_url": A3, "cover_b_url": B3,
                          "cover_rounds": [{"round": 1, "a_url": A1, "b_url": B1},
                                           {"round": 2, "a_url": A2, "b_url": B2}]})
            pg.click('[data-card="id53"] [data-act="cover-more-open"]')
            pg.click('[data-card="id53"] [data-act="cover-more"]')
            pg.wait_for_timeout(700)
            w2 = pg.evaluate("window.__writes")[n_before:]
            case("🔴 a pair she has not seen is NOT turned down — nothing is written",
                 not any(x["patch"].get("cover_more_requested_at") for x in w2), str(w2))
            c4 = card()
            case("  and the card now shows the pair the rail actually holds",
                 c4["imgs"] == [A3, B3], f"card shows {c4['imgs']}")
        finally:
            b.close()


try:
    run()
except Exception as e:                                                # noqa: BLE001
    case(f"the board could be driven ({type(e).__name__}: {str(e)[:200]})", False)

print(f"\nboard cover round: {len(PASS)} passed, {len(FAIL)} failed  (source: {LIVE or REPO})")
sys.exit(1 if FAIL else 0)
