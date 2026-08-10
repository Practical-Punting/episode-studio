#!/usr/bin/env python3
"""#13 — "NEITHER — ASK FOR DIFFERENT ONES" (Option B, the free request-signal).

    python engine/test_cover_more_button.py
    BOARD_URL=https://…/episode-studio python engine/test_cover_more_button.py

Jodie chose Option B over "make more (new pictures)", and the design note's reading of
the code is why:

> A "make more" button that only changes the prompt DOES NOTHING AT ALL. make_covers_ab
> generates only heroes that are MISSING, so with both PNGs on disk it returns the same
> two files, re-publishes them to the same two paths, and the board re-offers the same
> two pictures for £0 — the EP15 shape exactly, re-armed and reachable from a button.

So the click records a REQUEST and spends nothing; the studio writes fresh prompts as a
separate, deliberate act. "Automation eats chores, never decisions."

WHAT THIS SUITE HOLDS DOWN, all of it in a real browser against the rendered board:
  · the click writes a request and NOTHING that costs money;
  · it is not a veto — the current pair stays tappable;
  · every earlier round stays on the card and stays tappable;
  · the nudge after ~3 rounds is a sentence, never a gate;
  · opening the box is not sending.
"""
from __future__ import annotations

import json
import os
import sys
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
LOCAL = ""


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


def row(**kw):
    r = {"id": "cov1", "ep_number": 20, "status": "awaiting_cover",
         "title": "Episode 20", "hook": "h", "byline": "b", "needs_look": False,
         "title_approved": True, "script_read": True,
         "script_snapshot": "words", "progress_pct": 60,
         "cover_a_url": "https://example.invalid/a.png",
         "cover_b_url": "https://example.invalid/b.png",
         "cover_choice": None, "cover_round": 1, "cover_rounds": [],
         "cover_more_requested_at": None, "cover_more_note": None,
         "build_state": {}, "heartbeat_at": None, "claimed_by": None}
    r.update(kw)
    return r


STUB = """
window.__rows = { episodes: window.__ROWS__, messages: [] };
window.__writes = [];
function qb(table) {
  const t = {
    select(){ return t; }, order(){ return t; }, in(){ return t; }, eq(){ return t; },
    limit(){ return t; }, single(){ return t; },
    update(p){ window.__writes.push(p); return t; },
    insert(p){ window.__writes.push(p); return t; }, upsert(){ return t; },
    then(res){ return Promise.resolve({ data: window.__rows[table] || [], error: null }).then(res); },
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


def board(rows, then=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1400, "height": 1200})
        pg.add_init_script(f"window.__ROWS__ = {json.dumps(rows)};")
        # the stub must REPLACE supabase-js: index.html loads it on the line above app.js
        pg.route("**/supabase-js*",
                 lambda r: r.fulfill(status=200, content_type="application/javascript",
                                     body=STUB))
        try:
            pg.goto((LIVE or LOCAL) + "/index.html", wait_until="load")
            pg.wait_for_timeout(1800)
            if then:
                then(pg)
                pg.wait_for_timeout(700)
            return pg.evaluate("""() => ({
              text: document.body.innerText.replace(/\\s+/g,' '),
              writes: window.__writes,
              tiles: [...document.querySelectorAll('button.cover')].map(b => ({
                pick: b.getAttribute('data-pick'),
                disabled: b.disabled === true,
              })),
              hasGhost: !!document.querySelector('[data-act="cover-more-open"]'),
              boxHidden: (document.querySelector('.askbox') || {}).hidden,
            })""")
        finally:
            b.close()


if not LIVE:
    LOCAL = serve(REPO)

# ── 1. the button is there, and opening the box is NOT sending ────────────────
s = board([row()])
case("the cover gate offers a ghost 'ask for different ones' button", s["hasGhost"],
     s["text"][:200])
case("  …and the reason box starts closed", s["boxHidden"] is True)
case("  …and no write happens just by rendering", not s["writes"], str(s["writes"]))

s = board([row()], then=lambda pg: pg.click('[data-act="cover-more-open"]'))
case("opening the box is not sending", not s["writes"], str(s["writes"]))
case("  …the box is now open", s["boxHidden"] is False)

# ── 2. THE CLICK COSTS NOTHING, and says why ──────────────────────────────────
def _send_with_note(pg):
    pg.click('[data-act="cover-more-open"]')
    pg.fill("textarea", "no grandstand crowds please, and keep it on turf")
    pg.click('[data-act="cover-more"]')


s = board([row()], then=_send_with_note)
w = s["writes"][0] if s["writes"] else {}
case("sending writes a request", bool(w.get("cover_more_requested_at")), str(s["writes"]))
case("  …and carries her note", "grandstand" in (w.get("cover_more_note") or ""), str(w))
# 🔴 THE ONE THAT MATTERS: a £0 click. Nothing here may touch a spend-adjacent field.
SPENDY = ("cover_a_url", "cover_b_url", "cover_choice", "status", "cost",
          "needs_look", "build_state")
case("🔴 the click spends NOTHING and changes no artefact",
     not [k for k in SPENDY if k in w],
     f"it wrote {[k for k in SPENDY if k in w]} — the click must cost £0 and the "
     f"spend must stay a separate, deliberate act")

# ── 3. A REQUEST IS NOT A VETO ────────────────────────────────────────────────
s = board([row(cover_more_requested_at="2026-08-10T10:00:00Z")])
case("after asking, the current pair is STILL tappable",
     len([t for t in s["tiles"] if not t["disabled"]]) >= 2,
     str(s["tiles"]))
case("  …and the card says nothing is stuck", "Nothing is stuck" in s["text"],
     s["text"][:240])
case("  …and the episode is not flagged red by it", "needs a look" not in s["text"].lower())

# ── 4. EVERY EARLIER ROUND STAYS SELECTABLE ───────────────────────────────────
hist = [{"round": 1, "a_url": "https://example.invalid/r1a.png",
         "b_url": "https://example.invalid/r1b.png", "note": "too much crowd",
         "rejected_at": "2026-08-10T10:00:00Z"}]
s = board([row(cover_round=2, cover_rounds=hist,
               cover_a_url="https://example.invalid/r2a.png",
               cover_b_url="https://example.invalid/r2b.png")])
picks = sorted(t["pick"] for t in s["tiles"])
case("round 1's pair is still on the card alongside round 2",
     len(s["tiles"]) == 4, f"tiles: {picks}")
case("  …and each names its round, so a pick is unambiguous",
     "A" in picks and "A1" not in picks and any(p and p.endswith("1") is False
                                                for p in picks),
     f"picks: {picks}")
case("  …and none of the old ones is disabled",
     not [t for t in s["tiles"] if t["disabled"]], str(s["tiles"]))
case("  …and her earlier reason is shown back to her",
     "too much crowd" in s["text"], s["text"][:300])

# ── 5. THE NUDGE IS A SENTENCE, NOT A GATE ────────────────────────────────────
s = board([row(cover_round=3, cover_rounds=hist)])
case("after ~3 rounds a gentle nudge appears", "round 3" in s["text"].lower(),
     s["text"][:260])
case("  …and it still does not block or flag anything",
     s["hasGhost"] and "needs a look" not in s["text"].lower(),
     "the nudge has turned into a gate")

# ══ THE ENGINE HALF — versioned paths, and the rejection written down ═════════
sys.path.insert(0, str(HERE))
import providers                                                      # noqa: E402

import tempfile                                                       # noqa: E402


class P(providers.RealProvider):
    def __init__(self, d):
        self._d = Path(d)

    def dir(self, ep):
        return self._d


tmp = Path(tempfile.mkdtemp(prefix="covers_"))
(tmp / "ebook/cover-src").mkdir(parents=True)
(tmp / "docs").mkdir()

# 🔴 THE CONTROL FOR VERSIONING, and it is the fault that made the button pointless.
# With fixed hero-a.png / hero-b.png, round 2 writes over round 1 — and if Jodie sees
# round 2 and prefers an original, it is gone. It ALSO means make_covers_ab (which only
# generates heroes that are MISSING) finds the files present and silently returns the
# rejected pair for £0: the EP15 shape.
a1, b1, _ = P(tmp)._hero_paths({"cover_round": 1})
a2, b2, _ = P(tmp)._hero_paths({"cover_round": 2})
case("round 1 keeps the bare hero names (every shipped episode has them)",
     a1.name == "hero-a.png" and b1.name == "hero-b.png", f"{a1.name} / {b1.name}")
case("🔴 round 2 gets DIFFERENT paths, so it cannot overwrite round 1",
     a2.name != a1.name and b2.name != b1.name,
     f"round 2 would write to {a2.name} / {b2.name} — the same files as round 1, "
     f"destroying a pair Jodie may still want AND making the regeneration a £0 no-op")
case("  …named by their round so the folder reads honestly",
     a2.name == "hero-a-r2.png", a2.name)

# and a later round must not inherit an old file through the hero.png fallback
(tmp / "ebook/cover-src/hero.png").write_bytes(b"old")
a2b, _b, _c = P(tmp)._hero_paths({"cover_round": 2})
case("  …and round 2 never adopts the legacy hero.png", not a2b.is_file(),
     "a later round inherited an older episode's active hero")

# ── the rejection is RECORDED — E16 part 2 ────────────────────────────────────
ledger = tmp / "docs/hero-jobs.json"
ledger.write_text(json.dumps({
    "hero_A:abc123": {"job_id": "j1", "file": "hero-a.png"},
    "hero_B:def456": {"job_id": "j2", "file": "hero-b.png"},
}), encoding="utf-8")
P(tmp).record_cover_rejection({"cover_round": 1})
book = json.loads(ledger.read_text(encoding="utf-8"))
case("every hero of the rejected round is marked rejected on the ledger",
     all(e.get("rejected") for e in book.values()), json.dumps(book))
case("  …with when, and which round", all(e.get("rejected_at") and e.get("rejected_round") == 1
                                          for e in book.values()), json.dumps(book))
case("  …and the job ids are KEPT, not deleted — the record survives",
     all(e.get("job_id") for e in book.values()), json.dumps(book))

print(f"\ncover-more button: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
