#!/usr/bin/env python3
"""The script editor's own behaviours — autosave, save-failure, revert, history.

🚫 DELIBERATELY NOT IN test_board_bug1.py. That suite answers ONE question — does
the editor survive the 30-second refresh — and it is the gate that had to pass
before a single editable character shipped. Folding these cases into it would
make "bug 1 green" quietly mean more than it does, and a gate that means several
things is a gate nobody can read. (Jodie, 8 Aug 2026.)

THE CASE THAT MATTERS MOST, and the build plan says so out loud:

    "Type, kill the network mid-save, keep typing, restore it. Nothing lost;
     the indicator told the truth throughout."

It is not theoretical: 59 rail transients in one evening, one nine-attempt
give-up, fonts unreachable for hours. A save WILL fail mid-sentence.

    🔴 TEXT IS NEVER LOST BECAUSE A SAVE FAILED.
Never silently revert to the stored value — that is the C1 fault in a new hat.

Run: python engine/test_script_editor.py
"""
from __future__ import annotations

import http.server
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


# A stub that can be made to FAIL on demand, and that records what it was asked
# to write. Everything else is the real app.js and the real index.html.
STUB = """
<script>
window.__FAIL = false;              // when true, every episode UPDATE errors
window.__UPDATES = [];              // what the writer sent, in order
window.__INSERTS = [];              // script_versions rows
const EP = {id:"ep-18", ep_number:18, title:"Those Top 6 Favourites",
            status:"queued", needs_look:false,
            script_snapshot:"CLAUDE WROTE THIS FIRST.",
            title_approved:false, script_read:false, created_at:"2026-08-08"};
function chain(rows){
  return new Proxy({}, { get: (_t, k) => (
    k === "then" ? (r) => r({ data: rows, error: null })
                 : function(){ return this; }
  )});
}
window.supabase = { createClient: () => ({
  auth: {
    getSession: async () => ({ data:{ session:{ user:{ email:"jodie@example.com" } } } }),
    onAuthStateChange: () => ({ data:{ subscription:{ unsubscribe(){} } } }),
    signInWithOtp: async () => ({ error:null }), signOut: async () => ({}),
  },
  from: (table) => ({
    select: () => chain(table === "script_versions" ? window.__INSERTS : [EP]),
    order: function(){ return this; }, eq: function(){ return this; },
    limit: function(){ return this; },
    in: function(){ return this; },
    then: (r) => r({ data:[EP], error:null }),
    update: (patch) => ({ eq: async () => {
      if (window.__FAIL) return { error: { message: "network down" } };
      window.__UPDATES.push(patch);
      Object.assign(EP, patch);
      return { error: null };
    }}),
    insert: async (row) => {
      window.__INSERTS.push(row);
      return { error: null };
    },
  }),
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

        def log_message(self, *a):
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

    holder = []
    threading.Thread(target=serve, args=(holder,), daemon=True).start()
    while not holder:
        pass
    url = f"http://127.0.0.1:{holder[0]}/index.html"

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(url)
        page.wait_for_selector("#board:not([hidden])", timeout=15000)

        print("\n-- 🔴 CAN A HUMAN ACTUALLY OPEN IT? (the case that was missing) --")
        # THE FAULT THIS STANDS AGAINST, and it shipped: the editor panel existed
        # for a whole landing with NOTHING ON THE BOARD THAT OPENED IT.
        # openScript() was defined and never called. Jodie could read EP18's
        # script and could not change a word.
        #
        # AND THE PROOF MISSED IT BECAUSE THE PROOF REACHED PAST THE DOOR: every
        # case below used page.evaluate("openScript('ep-18')") — calling the
        # function directly. They proved the panel WORKS once open and never that
        # a person can OPEN it. So this case clicks the REAL button on the REAL
        # rendered card, and everything after it inherits a panel opened the way
        # she opens it.
        btn = page.locator("#lanes [data-act='edit-script']").first
        check("the words card renders an edit button at all", btn.count() > 0,
              "there is no way in — the editor is orphaned")
        check("  and it says what it does",
              "Edit the script" in (btn.text_content() or ""),
              btn.text_content() or "")
        check("  the panel is shut before she clicks", page.is_hidden("#script"))
        btn.click()
        page.wait_for_selector("#script:not([hidden])", timeout=5000)
        check("CLICKING IT OPENS THE EDITOR", not page.is_hidden("#script"))
        check("  the board steps aside", page.is_hidden("#board"))
        check("  and the focus is in the words, ready to type",
              page.evaluate("document.activeElement.id") == "sc-text")

        print("\n-- the button survives the 30s rebuild that replaces it --")
        # It is delegated through #lanes, so the node is destroyed every cycle and
        # the handler is not. A listener bound to the button itself would die.
        page.evaluate("closeScript()")
        page.wait_for_selector("#board:not([hidden])")
        page.evaluate("loadAll()")
        page.wait_for_timeout(200)
        page.locator("#lanes [data-act='edit-script']").first.click()
        page.wait_for_selector("#script:not([hidden])", timeout=5000)
        check("it still opens after the board has been rebuilt",
              not page.is_hidden("#script"))

        print("\n-- it opens on what Claude Code wrote --")
        check("the box holds the seated script",
              page.input_value("#sc-text") == "CLAUDE WROTE THIS FIRST.")
        check("  and opening wrote an 'open' version row",
              page.evaluate("window.__INSERTS.some(r => r.reason === 'open')"))

        print("\n-- autosave, on a 3 second debounce --")
        page.fill("#sc-text", "")
        page.type("#sc-text", "Her first edit.", delay=1)
        page.wait_for_timeout(600)
        check("nothing is written while she is still typing",
              not any_update(page, "Her first edit."),
              "it saved immediately — the debounce is not working")
        check("  and the state says nothing yet", page.text_content("#sc-state") == "")
        page.wait_for_timeout(3200)
        check("it saves ~3s after typing stops", any_update(page, "Her first edit."))
        state = page.text_content("#sc-state")
        check("  and the state says so", state.startswith("Saved"), state)
        check("  her first save took ownership of the words",
              page.evaluate("window.__UPDATES.some(u => u.script_edited_by_human_at)"),
              "script_edited_by_human_at was never set — the engine could overwrite her")

        print("\n-- 🔴 THE ONE THAT MATTERS MOST: the network dies mid-save --")
        page.evaluate("window.__FAIL = true; window.__UPDATES.length = 0;")
        page.focus("#sc-text")
        page.fill("#sc-text", "")
        page.type("#sc-text", "Typed while the line was down.", delay=1)
        page.wait_for_timeout(3400)
        # 🔴 THE CONTROL. If the failure injection silently did nothing, the save
        # would succeed and EVERY assertion below would pass for the wrong reason
        # — a green outage test on a line that never went down. Prove the outage
        # was real before believing anything about how it was handled.
        check("the outage is REAL — nothing reached the rail while it was down",
              page.evaluate("window.__UPDATES.length === 0"),
              "the save succeeded, so this whole section is testing nothing")
        state = page.text_content("#sc-state")
        check("the indicator says NOT SAVED, loudly", "NOT SAVED" in state, state)
        check("  and tells her the words are safe", "safe in this box" in state, state)
        check("  THE TEXT IS STILL IN THE BOX",
              page.input_value("#sc-text") == "Typed while the line was down.",
              "it reverted to the stored value — the C1 fault in a new hat")

        # keep typing THROUGH the outage — the real thing she would do
        page.focus("#sc-text")
        page.type("#sc-text", " And more, still down.", delay=1)
        page.wait_for_timeout(3400)
        check("  she can keep typing while it is down",
              page.input_value("#sc-text").endswith("And more, still down."))
        check("  it is still honest about the failure",
              "NOT SAVED" in page.text_content("#sc-state"))

        page.evaluate("window.__FAIL = false;")               # the line comes back
        page.wait_for_timeout(6000)                           # the retry backoff
        check("when the line returns it saves the LATEST text, not the first",
              any_update(page, "Typed while the line was down. And more, still down."),
              "the words typed during the outage were lost")
        check("  and the state recovers to Saved",
              page.text_content("#sc-state").startswith("Saved"),
              page.text_content("#sc-state"))

        print("\n-- a save on the wire never drops the next keystrokes --")
        # ONE QUEUED TRAILING SAVE: writeEpisode() discards a concurrent save
        # (`if (inflight.has(k)) return false`), which is silently lost keystrokes
        # for autosave. The editor's own writer queues instead.
        page.evaluate("window.__UPDATES.length = 0;")
        page.focus("#sc-text")
        page.fill("#sc-text", "")
        page.type("#sc-text", "queued one", delay=1)
        page.wait_for_timeout(3200)
        page.type("#sc-text", " and two", delay=1)
        page.wait_for_timeout(3600)
        check("the final text reached the rail",
              any_update(page, "queued one and two"))

        print("\n-- edit, close, reopen — the edit is there (proof-pass 3) --")
        page.evaluate("closeScript()")
        page.wait_for_selector("#board:not([hidden])")
        page.evaluate("openScript('ep-18')")
        page.wait_for_selector("#script:not([hidden])")
        check("the reopened box holds her edit",
              page.input_value("#sc-text") == "queued one and two",
              page.input_value("#sc-text"))
        check("  closing wrote a 'close' version row",
              page.evaluate("window.__INSERTS.some(r => r.reason === 'close')"))

        print("\n-- 'Back to what Claude Code wrote', after fifteen edits (6) --")
        for i in range(15):
            page.focus("#sc-text")
            page.fill("#sc-text", f"edit number {i}")
            page.wait_for_timeout(60)
        page.evaluate("window.confirm = () => true;")
        page.evaluate("scRevert()")
        page.wait_for_timeout(500)
        check("it returns the ORIGINAL exactly",
              page.input_value("#sc-text") == "CLAUDE WROTE THIS FIRST.",
              page.input_value("#sc-text"))
        check("  and nothing was destroyed to do it — a row was kept first",
              page.evaluate("window.__INSERTS.some(r => r.reason === 'before-revert')"))

        print("\n-- version rows are BOUNDARIES, not keystrokes (proof-pass 7) --")
        n = page.evaluate("window.__INSERTS.length")
        check("single figures after all that typing, not hundreds", n < 10, f"{n} rows")
        check("  and every row carries the words in full, never a diff",
              page.evaluate("window.__INSERTS.every(r => typeof r.script === 'string')"))

        print("\n-- 🔴 APPROVED WORDS ARE FROZEN, AND THERE IS A WAY BACK (5) --")
        # The lock and its way back are ONE feature. A lock with no way back
        # strands her on the first typo spotted afterwards, exactly as EP15's
        # title did.
        page.evaluate("""
            const ep = EPISODES.find(e => e.id === 'ep-18');
            ep.title_approved = true; ep.script_read = true;
            openScript('ep-18');
        """)
        page.wait_for_timeout(300)
        check("an approved script opens READ-ONLY",
              page.evaluate("document.getElementById('sc-text').readOnly"))
        check("  it still shows the words (she can always read what was approved)",
              len(page.input_value("#sc-text")) > 0)
        check("  and says plainly that this is what the build is using",
              not page.is_hidden("#sc-lockmsg"))
        check("  the revert button is out of the way while locked",
              page.is_hidden("#sc-revert"))
        page.evaluate("window.__UPDATES.length = 0;")
        page.evaluate("document.getElementById('sc-text').value = 'SNEAKED IN';"
                      "scTyped();")
        page.wait_for_timeout(3400)
        check("  a save is refused while locked — nothing reaches the rail",
              page.evaluate("window.__UPDATES.length === 0"),
              "the freeze is cosmetic; the words could still be changed")

        check("THE WAY BACK IS RIGHT THERE", not page.is_hidden("#sc-unlock"))
        page.evaluate("window.confirm = () => true; scUnlock();")
        page.wait_for_timeout(400)
        check("  unlocking clears the approval, so she approves again knowingly",
              page.evaluate("window.__UPDATES.some(u => u.script_read === false)"))
        check("  and the box is editable again",
              not page.evaluate("document.getElementById('sc-text').readOnly"))
        check("  the unlock was RECORDED as a version boundary",
              page.evaluate("window.__INSERTS.some(r => r.reason === 'before-unlock')"),
              "an unlock nobody can see afterwards is not a recorded act")
        check("  and nothing was deleted to do it",
              page.evaluate("window.__INSERTS.length > 0"))

        print("\n-- the on-card preview keeps its place too (bug 1, in miniature) --")
        # Jodie, 8 Aug: reading the script on the card, it "jumps to the top every
        # ~30s". The editor is the real reading surface and is immune; the preview
        # still lives inside #lanes, so its place is harvested and restored the
        # same way the board already does for every input.
        page.evaluate("closeScript()")
        page.wait_for_selector("#board:not([hidden])")
        # THE REAL ELEMENT AND THE REAL CSS. `.scriptbox` is overflow:hidden; the
        # scroller is `.scriptbox > pre` (max-height:44vh, overflow:auto). An
        # earlier version of this case styled the box by hand and measured a
        # scroll that does not exist on the shipped board.
        # A REAL-LENGTH SCRIPT, or the <pre> never exceeds its 44vh and there is
        # no scroll to preserve. Earlier cases have whittled the fixture down to
        # a few words.
        page.evaluate("""(() => {
            const ep = EPISODES.find(e => e.id === 'ep-18');
            ep.script_snapshot = Array.from({length: 300},
                (_, i) => 'Line ' + i + ' of a script long enough to scroll.').join('\\n\\n');
            renderBoard();
        })()""")
        page.wait_for_timeout(150)
        page.evaluate("""(() => {
            const p = document.querySelector('.scriptbox > pre');
            p.scrollTop = 60;
        })()""")
        got = page.evaluate("document.querySelector('.scriptbox > pre').scrollTop")
        check("the preview can be scrolled (or this proves nothing)", got > 0,
              f"scrollTop {got} — the <pre> is not overflowing, so nothing is proved")
        page.evaluate("harvestDrafts(); loadAll();")
        page.wait_for_timeout(250)
        after = page.evaluate("document.querySelector('.scriptbox > pre').scrollTop")
        check("  and it keeps its place across a rebuild", after == got,
              f"was {got}, now {after}")

        print("\n-- and nothing threw --")
        check("no page errors", not errs, str(errs[:2]))
        b.close()

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


def any_update(page, text):
    return page.evaluate(
        "t => window.__UPDATES.some(u => u.script_snapshot === t)", text)


if __name__ == "__main__":
    raise SystemExit(main())
