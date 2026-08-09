"""THE BOARD, IN A REAL BROWSER, WITH EP19's REAL SCRIPT.

Two faults Jodie found reading EP19's seated script:
  1. the editor CLIPS a long script — the scrollbar reaches neither the first line
     nor the last
  2. the board did not refresh when the script seated (null -> set); she had to reload

🔴 WHY THIS IS A BROWSER TEST AND NOT A UNIT TEST. Both faults are about LAYOUT and
LIVENESS — a fixed height, an overflow rule, a re-render that does not arrive. None of
them is visible in the source, and every one of them would pass a test that asserted
about strings. The existing board suites run app.js in a VM with a fake DOM; they
cannot see a scrollbar. So this drives the actual page in headless Chromium and asks
the questions a person at the board would ask: can I see the first line, can I see the
last line, and did the card change by itself.

Run: python engine/test_board_editor_browser.py
"""
import functools
import http.server
import json
import pathlib
import socketserver
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from playwright.sync_api import sync_playwright  # noqa: E402

FAILED = []


def check(name, cond, why=""):
    # `why` is the FAILURE explanation and prints only on failure. The first version
    # printed it always, so PASS lines carried sentences like "still showing the
    # no-script state" — a green result reading like a red one, which is how a broken
    # test hides in its own output.
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"\n          {why}" if not cond and why else ""))
    if not cond:
        FAILED.append(name)


# ── EP19's REAL script, off the rail ────────────────────────────────────────
def real_script():
    try:
        import rail
        row = next(e for e in rail.list_all() if e.get("ep_number") == 19)
        s = row.get("script_snapshot")
        if s and len(s.split()) > 500:
            return row, s
    except Exception as e:                                            # noqa: BLE001
        print(f"  (could not read the rail: {e})")
    return None, None


ROW, SCRIPT = real_script()
if not SCRIPT:
    print("SKIP: EP19's seated script is not readable, and a shorter stand-in would "
          "not reproduce a clipping fault that only appears on a long one.")
    sys.exit(0)

FIRST_LINE = SCRIPT.strip().splitlines()[0].strip()
LAST_LINE = [l for l in SCRIPT.strip().splitlines() if l.strip()][-1].strip()
print(f"EP19's script: {len(SCRIPT.split()):,} words, {len(SCRIPT):,} chars, "
      f"{len(SCRIPT.splitlines())} lines")
print(f"  first: {FIRST_LINE[:70]}…")
print(f"  last : …{LAST_LINE[-70:]}")

EPISODE = {
    "id": "ep-19", "ep_number": 19, "status": "queued",
    "name": ROW.get("name") or "10 Systems For Action Hungry Punters Part 1",
    "title": ROW.get("title"), "script_snapshot": SCRIPT,
    "script_read": False, "title_approved": False, "needs_look": False,
    "hook": None, "byline": None, "heygen_name": None, "script_doc_url": None,
    "created_at": "2026-08-09T00:06:36Z", "updated_at": "2026-08-09T02:09:18Z",
    "build_state": {}, "progress_pct": 0,
}

# ── a Supabase stand-in, injected before app.js runs ────────────────────────
STUB = """
window.__rows = { episodes: [], messages: [] };
window.__realtime = [];
function qb(table) {
  const t = {
    _f: {},
    select(){ return t; }, order(){ return t; }, in(){ return t; }, eq(){ return t; },
    limit(){ return t; }, single(){ return t; },
    update(){ return t; }, insert(){ return t; }, upsert(){ return t; },
    then(res){ return Promise.resolve({ data: window.__rows[table] || [], error: null }).then(res); },
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
}) };
"""


def serve(root: pathlib.Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def open_board(page, port, episodes, ready='[data-act="edit-script"]'):
    # A card with no script has no Edit button, so the caller says what to wait for.
    page.add_init_script(STUB + f"\nwindow.__rows.episodes = {json.dumps(episodes)};")
    page.route("**/cdn.jsdelivr.net/**", lambda r: r.fulfill(status=200,
               content_type="application/javascript", body="/* stubbed */"))
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
    page.wait_for_selector(ready, timeout=15000)
    return errs


def visible_text_of_editor(page):
    """What a reader can actually SEE in the editable box right now."""
    return page.evaluate("""() => {
      const el = document.querySelector('#sc-body, #sc-text, .sc-body, textarea.sc, #script textarea, #script [contenteditable]');
      if (!el) return { found: false };
      const r = el.getBoundingClientRect();
      const isTA = el.tagName === 'TEXTAREA';
      return { found: true, tag: el.tagName, id: el.id,
               clientH: el.clientHeight, scrollH: el.scrollHeight, scrollTop: el.scrollTop,
               rectH: Math.round(r.height), styleH: getComputedStyle(el).height,
               overflowY: getComputedStyle(el).overflowY,
               value: isTA ? el.value : el.innerText };
    }""")


def run(page, port, label):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    errs = open_board(page, port, [EPISODE])
    if errs:
        print(f"  page errors: {errs[:2]}")
    page.click('[data-act="edit-script"]')
    page.wait_for_timeout(700)

    info = visible_text_of_editor(page)
    if not info.get("found"):
        check("the editor box exists", False, "no editable element matched")
        return
    print(f"  editor <{info['tag']}#{info['id']}>  client {info['clientH']}px  "
          f"scroll {info['scrollH']}px  css-height {info['styleH']}  "
          f"overflow-y {info['overflowY']}")

    check("the whole script is IN the editor",
          FIRST_LINE[:40] in (info["value"] or "") and LAST_LINE[-40:] in (info["value"] or ""),
          "" if FIRST_LINE[:40] in (info["value"] or "") else
          f"{len(info['value'] or '')} chars in the box vs {len(SCRIPT)} in the script")

    # 🔴 THE MEASUREMENT THAT MATTERS, AND THE ONE THE FIRST VERSION GOT WRONG.
    # Setting el.scrollTop from script SUCCEEDS on an overflow:hidden element, so a
    # test that scrolls that way reports a healthy editor while a person can move
    # nothing at all. It passed on the broken build, which is how it was caught.
    # A textarea holds no queryable text nodes either, so "is the last line visible"
    # has to be asked structurally: is any of the content clipped out of reach?
    clipped = info["scrollH"] - info["clientH"]
    check("NOTHING is clipped out of reach — the box is as tall as its words",
          clipped <= 2,
          f"{clipped}px of script is outside the box "
          f"(content {info['scrollH']}px, box {info['clientH']}px, "
          f"overflow-y:{info['overflowY']}) — unreachable by any gesture")

    # and prove a REAL gesture moves the document, using the wheel, not scrollTop
    page.mouse.move(720, 500)
    for _ in range(40):
        page.mouse.wheel(0, 400)
    page.wait_for_timeout(400)
    at_end = page.evaluate("""() => {
      const w = document.querySelector('.sc-wrap');
      const t = document.querySelector('#sc-text');
      const tr = t.getBoundingClientRect();
      return { wrapTop: Math.round(w.scrollTop),
               wrapMax: Math.round(w.scrollHeight - w.clientHeight),
               textBottom: Math.round(tr.bottom), vh: innerHeight,
               lastLineOnScreen: tr.bottom <= innerHeight + 4 };
    }""")
    check("WHEELING to the bottom brings the END of the script on screen",
          at_end["lastLineOnScreen"],
          f"the text box still ends {at_end['textBottom'] - at_end['vh']}px below the "
          f"window after wheeling (wrap at {at_end['wrapTop']} of {at_end['wrapMax']})")

    for _ in range(60):
        page.mouse.wheel(0, -400)
    page.wait_for_timeout(400)
    at_top = page.evaluate("""() => {
      const w = document.querySelector('.sc-wrap');
      const t = document.querySelector('#sc-text');
      const tr = t.getBoundingClientRect();
      return { wrapTop: Math.round(w.scrollTop), textTop: Math.round(tr.top),
               firstLineOnScreen: tr.top >= -4 };
    }""")
    check("WHEELING back to the top brings the FIRST line on screen",
          at_top["firstLineOnScreen"],
          f"the text box starts {at_top['textTop']}px above the window "
          f"(wrap at {at_top['wrapTop']})")


def run_refresh(page, port):
    print(f"\n{'=' * 70}\nBUG 2 — the card must update itself when a script seats\n{'=' * 70}")
    no_script = dict(EPISODE, script_snapshot=None)
    open_board(page, port, [no_script], ready="#lanes .card, #lanes [data-ep]")
    before = page.inner_text("#lanes")
    check("the card starts in the NO-SCRIPT state",
          FIRST_LINE[:30] not in before, "the script is already showing")

    # the script arrives, exactly as the drafting pass seats it
    page.evaluate("""(row) => { window.__rows.episodes = [row]; }""", EPISODE)
    # the board polls every 30s; give it a beat longer, and do NOT reload
    page.wait_for_timeout(34000)
    after = page.inner_text("#lanes")
    check("the card shows the script WITHOUT a reload",
          FIRST_LINE[:30] in after or "Edit the script" in after,
          "still showing the no-script state after 34s")

    # 🔴 NOW HER ACTUAL CONDITIONS. renderBoard() returns early whenever ANY field is
    # dirty — the C1 pause that protects her typing — so a board she has touched
    # freezes for everything, including a script arriving on a DIFFERENT card. A clean
    # idle page updates fine, which is why the first version of this test passed while
    # she was reloading to see her script.
    print("\n  — and again, with a field she has been typing in —")
    open_board(page, port, [no_script], ready="#lanes .card, #lanes [data-ep]")
    typed = page.evaluate("""() => {
      const el = document.querySelector('#lanes input[type=text], #lanes textarea, '
                                      + '#lanes input:not([type=checkbox])');
      if (!el) return null;
      el.focus(); el.value = (el.value || '') + 'x';
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return el.id || el.tagName;
    }""")
    check("a field on the board is dirty (her conditions)", typed is not None,
          "no editable field on the card to type into — cannot reproduce her state")
    if typed:
        print(f"          typed into <{typed}>; UI.dirty is now non-empty")
        before_val = page.evaluate("(id) => document.getElementById(id).value", typed)
        page.evaluate("""(row) => { window.__rows.episodes = [row]; }""", EPISODE)
        page.wait_for_timeout(34000)
        after2 = page.inner_text("#lanes")
        check("the script STILL appears while another field is being edited",
              FIRST_LINE[:30] in after2 or "Edit the script" in after2,
              "the card never updated — renderBoard() bailed on the dirty field, "
              "which is why she had to reload")
        # 🔴 AND IT MUST NOT COST HER THE THING THE PAUSE EXISTS TO PROTECT.
        # A fix that shows the script by throwing away her half-typed hook is a worse
        # bug than the one it replaces, and it would look identical in the check above.
        kept = page.evaluate("""(a) => {
          const el = document.getElementById(a.id);
          if (!el) return { gone: true };
          return { gone: false, value: el.value,
                   focused: document.activeElement === el,
                   caret: el.selectionStart };
        }""", {"id": typed})
        check("  her typing survived the refresh", not kept["gone"]
              and kept["value"] == before_val,
              f"was {before_val!r}, now {kept.get('value')!r}")
        check("  and the caret is still in her field",
              kept.get("focused") is True,
              f"focus moved away (caret {kept.get('caret')})")


def main():
    httpd, port = serve(REPO)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            run(pg, port, "BUG 1 — the editor must show the WHOLE script")
            run_refresh(pg, port)
            b.close()
    finally:
        httpd.shutdown()
    print(f"\n{'=' * 70}")
    print("BOTH PROOFS PASS" if not FAILED else f"STILL FAILING: {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
