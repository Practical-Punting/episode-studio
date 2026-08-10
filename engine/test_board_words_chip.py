#!/usr/bin/env python3
"""THE JOB-5 FAULT: a "YOUR TURN" chip with nothing to do.

    python engine/test_board_words_chip.py            # against the local files
    BOARD_URL=https://…/episode-studio python engine/test_board_words_chip.py

A queued episode with NO SCRIPT YET showed "YOUR TURN — WORDS" and the Words Gate, at
the exact moment the MACHINE owed her the script. She is asked to read something that
does not exist, and sent looking for a Doc nobody has made.

> A queue that cries turn-taking when there is no turn to take is a queue she stops
> believing, and the one time it means it she will scroll past.

🔴 PROVED IN A REAL BROWSER AGAINST THE RENDERED BOARD, never by reading app.js. That
law was earned: a previous board fix was reported working from the source while the
deployed page still clipped, and the suite that "proved" it had served the repo locally.

Supabase is stubbed, so the board renders rows this test invents and touches no rail.
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


def serve(root: Path):
    """A local http server for the repo — used only when BOARD_URL is not set.

    🔴 BOARD_URL POINTS THIS AT THE DEPLOYED SITE, and that is the law: a previous board
    fix was proved against a locally-served copy of files that had never been pushed,
    while the deployed page still carried the bug.
    """
    import functools
    import http.server
    import socketserver
    import threading
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}"


def case(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


def row(n, **kw):
    r = {"id": f"id{n}", "ep_number": n, "status": "queued", "title": f"Episode {n}",
         "hook": "A hook", "byline": "A byline", "needs_look": False,
         "title_approved": False, "script_read": False,
         "script_snapshot": None, "script_doc_url": None,
         "progress_pct": 0, "heartbeat_at": None, "claimed_by": None}
    r.update(kw)
    return r


ROWS = [
    # the fault: queued, nothing written yet — the MACHINE owes the words
    row(20),
    # a script exists and is unapproved — genuinely HER turn
    row(21, script_snapshot="Gordon says something."),
    # an older episode whose words live in a Doc — also her turn (A5)
    row(22, script_doc_url="https://docs.google.com/document/d/x"),
    # 🔴 THE STUDIO HAS GIVEN UP: queued, no script, AND FLAGGED. "Writing the
    # script…" here would be a worse lie than the chip it replaced — it says there
    # is nothing to do while nothing is happening. (11 Aug 2026.)
    row(23, needs_look=True,
        needs_look_message="I could not capture this episode's article, and I have "
                           "now tried 3 times. I have stopped retrying."),
]


def render_and_read():
    from playwright.sync_api import sync_playwright

    # THE SAME STAND-IN test_board_editor_browser.py USES. Written once, borrowed here:
    # a second hand-rolled stub is a second thing that can be subtly wrong, and the
    # first version of this test failed for exactly that reason — it rendered no lanes
    # at all because the query builder was missing methods app.js chains.
    stub = """
    window.__rows = { episodes: window.__ROWS__, messages: [] };
    window.__realtime = [];
    function qb(table) {
      const t = {
        select(){ return t; }, order(){ return t; }, in(){ return t; }, eq(){ return t; },
        limit(){ return t; }, single(){ return t; },
        update(){ return t; }, insert(){ return t; }, upsert(){ return t; },
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
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1400, "height": 1000})
        pg.add_init_script(f"window.__ROWS__ = {json.dumps(ROWS)};")
        # ⚠️ THE STUB REPLACES THE LIBRARY, it does not sit in front of it. index.html
        # loads the real supabase-js from a CDN on the line ABOVE app.js, so an
        # init-script stub is overwritten before app.js ever runs — the board then shows
        # its SIGN IN screen and renders no lanes at all, which looks exactly like a
        # broken fix. Serving the stub AS the library is the only ordering that holds.
        pg.route("**/supabase-js*",
                 lambda r: r.fulfill(status=200, content_type="application/javascript",
                                     body=stub))
        try:
            # ⚠️ OVER HTTP, NEVER file://. The board bails on a file:// origin (its
            # auth client refuses one), so the first version of this rendered zero
            # lanes and looked like a broken fix rather than a broken harness.
            pg.goto((LIVE or LOCAL) + "/index.html", wait_until="load")
            pg.wait_for_timeout(2000)
            return pg.evaluate("""() => {
              const out = {};
              for (const n of [20, 21, 22, 23]) {
                const card = document.querySelector(`[data-card$="id${n}"], [data-card="id${n}"]`)
                          || [...document.querySelectorAll('article')].find(
                               a => a.textContent.includes('PP-EP' + n));
                out[n] = card ? {
                  text: card.textContent.replace(/\\s+/g, ' ').trim().slice(0, 400),
                  lane: (card.closest('section.lane')?.querySelector('h2')?.textContent || '').trim(),
                } : null;
              }
              out.lanes = [...document.querySelectorAll('section.lane h2')].map(h => h.textContent.trim());
              return out;
            }""")
        finally:
            b.close()


if not LIVE:
    LOCAL = serve(REPO)

try:
    seen = render_and_read()
except Exception as e:                                                # noqa: BLE001
    print(f"could not render the board: {type(e).__name__}: {e}")
    raise SystemExit(1)

print(f"  (source: {LIVE or 'local files'}; lanes rendered: {seen.get('lanes')})\n")

e20, e21, e22 = seen.get("20"), seen.get("21"), seen.get("22")

case("the board rendered the three episodes", bool(e20 and e21 and e22),
     f"missing: {[n for n, v in (('20', e20), ('21', e21), ('22', e22)) if not v]}")

if e20 and e21 and e22:
    # 1. THE FAULT ITSELF
    case("a queued episode with NO script does NOT say 'Your turn'",
         "Your turn — words" not in e20["text"],
         f"EP20 still badges her: {e20['text'][:160]}")
    case("  …it says the studio is writing it",
         "Writing the script" in e20["text"],
         f"EP20 chip reads: {e20['text'][:160]}")
    case("  …and it sits in Waiting, not in Your turn",
         e20["lane"] != "Your turn",
         f"EP20 is in lane {e20['lane']!r}")
    case("  …and it is NOT offered the Words Gate",
         "I've read the script" not in e20["text"]
         and "Approve" not in e20["text"],
         f"the gate is still on the card: {e20['text'][:200]}")

    # 2. THE CONTROL — the gate must STILL fire when there really are words.
    #    Without this the whole fix could be "never ask her anything".
    case("CONTROL: an episode WITH a script still says 'Your turn'",
         "Your turn — words" in e21["text"],
         f"the words gate has been switched off entirely: {e21['text'][:200]}")
    case("CONTROL: it is in the Your turn lane", e21["lane"] == "Your turn",
         f"EP21 is in lane {e21['lane']!r}")
    case("CONTROL: an episode whose words live in a Doc still says 'Your turn'",
         "Your turn — words" in e22["text"],
         f"A5 — a Doc keeps its transport: {e22['text'][:200]}")


# ── A STUDIO THAT HAS GIVEN UP MUST NOT LOOK BUSY ────────────────────────────
# 🔴 THE SECOND HALF OF THE SAME LESSON. Replacing a false "YOUR TURN" with a false
# "the studio is working" would be a worse trade: a turn chip at least makes her look.
# When the studio has failed the same task three times it raises a real flag and STOPS
# retrying, and the card must stop claiming that work is happening.
#     📌 THE BOARD ALREADY DOES THIS, in the chip (`nl ? "Needs a look" : st.label`) and
# again in stageLine(). A `&& !ep.needs_look` clause was added to studioIsWriting() and
# then removed once a control showed it changed nothing. These cases stay: they pin the
# PROPERTY rather than one implementation of it, so a refactor of either layer still has
# to keep a given-up episode from looking busy.
e23 = seen.get("23")
if e23:
    case("a FLAGGED script-less episode does NOT claim the studio is writing",
         "Writing the script" not in e23["text"],
         f"it still says work is happening while nothing is: {e23['text'][:200]}")
    case("  …it says it needs a look", "needs a look" in e23["text"].lower(),
         e23["text"][:220])
    case("  …and it still does not badge her with a WORDS turn",
         "Your turn — words" not in e23["text"], e23["text"][:200])
else:
    case("the flagged episode rendered at all", False, "EP23 card not found")

print(f"\nwords chip: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
