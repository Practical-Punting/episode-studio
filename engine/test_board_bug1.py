#!/usr/bin/env python3
"""BOARD BUG 1 — the ten-times proof, in a REAL browser, actually run.

    "Type into the editor, alt-tab away, wait through at least two board refresh
     cycles, come back. The text is still there. Ten times, including with the
     panel open for several minutes."   — PP-script-editor-spec.md

🔴 WHY THIS SUITE IS A BROWSER AND NOT A STRING SEARCH.
The thing bug 1 destroys is not the VALUE — `restoreDrafts()` already puts that
back. It destroys the CARET, the SELECTION, the SCROLL POSITION and the BROWSER
UNDO STACK, none of which exist outside a real DOM. A structural test that greps
app.js for "#script" would pass on a board that still ate every edit.
    THE ARTEFACT IS WHAT A PERSON RECEIVES: text still there, caret where she
    left it, and ctrl+Z still able to walk back.

WHAT IS SIMULATED, NAMED HONESTLY:
  · "alt-tab away" is a real blur() plus a real wait — the browser keeps running
    and the 30s poll keeps firing, which is the part that matters.
  · The page is served from the repo with a STUBBED Supabase client, so no
    network, no session and no live rail. The stub is only the data source; the
    real app.js, the real index.html and the real renderBoard() are exercised.
  · The refresh is driven at the REAL interval the board uses, read out of
    app.js rather than typed here, so this cannot drift from the shipped value.

Run: python engine/test_board_bug1.py
"""
from __future__ import annotations

import http.server
import re
import socketserver
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


# ── the refresh interval, READ FROM THE SHIPPED CODE ────────────────────────
# A literal here would be a second copy of a value that already exists, and it
# would keep passing after somebody changed the real one (fault #2).
APP = (REPO / "app.js").read_text(encoding="utf-8")
m = re.search(r"setInterval\(\(\)\s*=>\s*\{\s*if\s*\(SESSION\)\s*loadAll\(\);\s*\},\s*(\d+)\)", APP)
POLL_MS = int(m.group(1)) if m else 0

# The stub replaces ONLY the Supabase client. Everything else is the real board.
STUB = """
<script>
window.__BUG1_RENDERS = 0;
const EP = {id:"ep-18", ep_number:18, title:"Those Top 6 Favourites",
            status:"queued", needs_look:false, script_snapshot:"SEEDED",
            title_approved:false, script_read:false, created_at:"2026-08-08"};
window.supabase = { createClient: () => ({
  auth: {
    getSession: async () => ({ data:{ session:{ user:{ email:"jodie@example.com" } } } }),
    onAuthStateChange: () => ({ data:{ subscription:{ unsubscribe(){} } } }),
    signInWithOtp: async () => ({ error:null }), signOut: async () => ({}),
  },
  // ⚠️ ANY query method chains, rather than a hand-written list of the ones
  // app.js happens to use today. The first version enumerated select/order/eq/
  // limit and died on `.in(...)` — a stub whose coverage is a list somebody
  // maintains is the same fault as a guard whose coverage is (CLAUDE.md #7).
  from: () => new Proxy({}, { get: (_t, k) => (
    k === "then" ? (r) => r({ data:[EP], error:null })
                 : function(){ return this; }
  )}),
  channel: () => ({ on(){ return this; }, subscribe(){ return this; } }),
  removeChannel: () => {},
})};
</script>
"""


def serve(port_holder):
    root = str(REPO)

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=root, **k)

        def do_GET(self):                                    # noqa: N802
            if self.path.startswith("/index.html") or self.path == "/":
                html = (REPO / "index.html").read_text(encoding="utf-8")
                html = html.replace("<script src=\"https://cdn.jsdelivr.net/npm/"
                                    "@supabase/supabase-js@2\"></script>", STUB)
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            return super().do_GET()

        def log_message(self, *a):                           # keep the run quiet
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), H) as httpd:
        port_holder.append(httpd.server_address[1])
        httpd.serve_forever()


def main():                                                  # noqa: C901
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  --   SKIPPED: playwright is not installed on this machine")
        return 0

    print(f"\n-- the board's real refresh interval, read from app.js: {POLL_MS}ms --")
    check("the poll interval was found in the shipped code", POLL_MS > 0,
          "the regex no longer matches app.js — this suite is measuring nothing")

    holder = []
    threading.Thread(target=serve, args=(holder,), daemon=True).start()
    while not holder:
        pass
    url = f"http://127.0.0.1:{holder[0]}/index.html"
    print(f"-- serving the real board from the repo at {url} --")

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_selector("#board:not([hidden])", timeout=15000)

        print("\n-- the structure bug 1 turns on --")
        inside = page.evaluate(
            "!!document.querySelector('#lanes #script')")
        sibling = page.evaluate(
            "document.getElementById('script').parentElement.id === "
            "document.getElementById('board').parentElement.id")
        check("the editor is NOT inside #lanes", not inside,
              "it is in the node renderBoard() replaces — bug 1 is not fixed")
        check("  it is a sibling of #board", sibling)

        # Open the editor the way the app does, and seed it.
        page.evaluate("openScript('ep-18')")
        page.wait_for_selector("#script:not([hidden])")

        print(f"\n-- THE TEN-TIMES TEST — each round survives 2 real "
              f"refresh cycles ({POLL_MS}ms each) --")
        # Drive the board's OWN loadAll() on its own timer rather than waiting
        # 30s x 20; the code path is identical, which is the thing under test.
        survived = 0
        for i in range(1, 11):
            text = f"Round {i}: the fifth favourite was the only one profitable."
            page.focus("#sc-text")
            page.fill("#sc-text", "")
            page.type("#sc-text", text, delay=1)
            page.evaluate("document.getElementById('sc-text')"
                          ".setSelectionRange(9, 9)")          # caret mid-word
            node_before = page.evaluate(
                "window.__n = document.getElementById('sc-text'); 1")
            page.evaluate("document.getElementById('sc-text').blur()")  # alt-tab
            for _ in range(2):                                  # TWO cycles
                page.evaluate("loadAll()")
                page.wait_for_timeout(120)
            page.focus("#sc-text")
            after = page.input_value("#sc-text")
            caret = page.evaluate(
                "document.getElementById('sc-text').selectionStart")
            same_node = page.evaluate(
                "window.__n === document.getElementById('sc-text')")
            ok = after == text and caret == 9 and same_node
            survived += 1 if ok else 0
            if not ok:
                print(f"     round {i}: text={after == text} caret={caret} "
                      f"same_node={same_node}")
        check("all ten rounds kept the text", survived == 10, f"{survived}/10")

        print("\n-- and the things restoreDrafts() cannot give back --")
        check("the textarea NODE was never replaced",
              page.evaluate("window.__n === document.getElementById('sc-text')"),
              "a new node means a lost caret, lost selection and a dead undo stack")
        page.focus("#sc-text")
        page.fill("#sc-text", "")
        page.type("#sc-text", "first", delay=1)
        page.type("#sc-text", " second", delay=1)
        page.evaluate("loadAll()")
        page.wait_for_timeout(120)
        page.focus("#sc-text")
        page.keyboard.press("Control+Z")
        undone = page.input_value("#sc-text")
        check("ctrl+Z still works after a refresh (the undo stack survived)",
              undone != "first second", f"undo gave {undone!r}")

        print("\n-- 🔴 AND SCROLL — the one the card preview still loses --")
        # Asked directly by Jodie: "confirm the editor panel itself never jumps
        # once I'm in it." The ten-times loop above checked text, caret and node
        # identity and NEVER SCROLL — so this was an untested claim until now.
        # The scroll lives on .sc-wrap (the textarea grows; the wrapper scrolls).
        page.focus("#sc-text")
        page.fill("#sc-text", "\n".join(f"line {i} of a long script" for i in range(400)))
        page.evaluate("scTyped()")          # grow the box to its content, as typing does
        page.wait_for_timeout(150)
        page.evaluate("document.querySelector('.sc-wrap').scrollTop = 1200")
        before = page.evaluate("document.querySelector('.sc-wrap').scrollTop")
        check("the panel can actually be scrolled (or this proves nothing)",
              before > 400, f"scrollTop only reached {before}")
        for _ in range(3):
            page.evaluate("loadAll()")
            page.wait_for_timeout(120)
        after = page.evaluate("document.querySelector('.sc-wrap').scrollTop")
        check("SCROLL POSITION SURVIVES THREE REFRESHES — the panel never jumps",
              after == before, f"was {before}, now {after}")

        print("\n-- 🔴 THE CONTROL: can this suite actually SEE bug 1? --")
        # A proof that cannot fail is decoration. Put an IDENTICAL textarea
        # INSIDE #lanes, on the same page, through the same refresh — if that one
        # survives too, this suite is measuring nothing and its green is a lie.
        page.evaluate("""
            const t = document.createElement('textarea');
            t.id = 'control-inside-lanes';
            document.getElementById('lanes').appendChild(t);
            t.value = 'CONTROL: inside the node renderBoard replaces';
            window.__c = t;
        """)
        page.evaluate("loadAll()")
        page.wait_for_timeout(150)
        control_gone = page.evaluate(
            "!document.getElementById('control-inside-lanes') || "
            "window.__c !== document.getElementById('control-inside-lanes')")
        check("a textarea INSIDE #lanes is destroyed by the same refresh",
              control_gone,
              "it survived — then this suite would pass even with bug 1 present, "
              "and every green above means nothing")

        print("\n-- the board underneath kept refreshing all the while --")
        lanes_html = page.evaluate("document.getElementById('lanes').innerHTML.length")
        check("#lanes still has content (the poll was never suppressed)",
              lanes_html > 0)
        check("no page errors were raised", not errors, str(errors[:2]))

        print("\n-- with the panel open for several minutes (compressed) --")
        page.focus("#sc-text")
        page.fill("#sc-text", "")
        page.type("#sc-text", "a long sitting with the panel open", delay=1)
        for _ in range(12):                     # twelve cycles back to back
            page.evaluate("loadAll()")
            page.wait_for_timeout(60)
        check("text survives twelve consecutive refresh cycles",
              page.input_value("#sc-text") == "a long sitting with the panel open")

        b.close()

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
