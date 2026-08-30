#!/usr/bin/env python3
"""A STEP THAT IS WAITING IS NOT A STEP THAT IS STUCK — AND A STUCK ONE MUST STILL SAY SO.

    python engine/test_waiting_is_not_stuck.py

This laptop now runs two production lines and they cannot both encode at once on
8 GB, so assembly will block behind a shared render lock. `started_at` is stamped
before the step runs and is never reset, so RAN stops meaning WORKED: forty
minutes of waiting plus fifteen of assembly reads as fifty-five against a
forty-five minute budget. Before this fix the board painted

    "⛔ Stuck — nobody is coming … Nothing is waiting on you — no flag is up — so
     it is not going to finish by itself. Restarting the engine picks it up where
     it left off and loses nothing."

— every clause false, and the last one an invitation to kill an engine that is
mid-ffmpeg. The fix SUBTRACTS the wait; it does not remove the budget.

🔴 IT IS PROVED IN BOTH DIRECTIONS, AND THE ALARM IS PROVED FIRST.
Jodie's instruction, 30 Aug 2026: *"a step that has been legitimately waiting must
NOT trip the alarm … a step that is genuinely hung, with no wait, MUST still trip
it exactly as it does today. If (b) stops working, the fix is worse than the
problem it solves."* So CONTROL B runs first: watch the alarm FIRE on a hung step,
then believe it staying quiet on a waiting one. A checker that cannot say "stuck"
proves nothing by saying "not stuck".

⚠️ IT RUNS THE REAL `stepState` AND `stageLine` OUT OF THE SHIPPED `app.js`, in
Chromium, with only the Supabase client stubbed. Reading app.js as TEXT is a proxy
(CLAUDE.md §1a) and would keep passing after somebody rewrote the comparison.

Nothing here touches the rail, the network, an episode folder or a running engine.
"""
from __future__ import annotations

import ast
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

import engine                                                         # noqa: E402

PASS, FAIL = [], []


def case(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'ok  ' if ok else '!!  '}{name}")
    if not ok and detail:
        print(f"      {detail}")


MIN = 60 * 1000
BUDGET = engine.STEP_BUDGET_S["assemble_passA"]          # read, never retyped

STUB = """
<script>
window.supabase = { createClient: () => ({
  auth: {
    getSession: async () => ({ data:{ session:null } }),
    onAuthStateChange: () => ({ data:{ subscription:{ unsubscribe(){} } } }),
    signInWithOtp: async () => ({ error:null }), signOut: async () => ({}),
  },
  from: () => new Proxy({}, { get: (_t, k) => (
    k === "then" ? (r) => r({ data:[], error:null })
                 : function(){ return this; }
  )}),
  channel: () => ({ on(){ return this; }, subscribe(){ return this; } }),
  removeChannel: () => {},
})};
</script>
"""


def serve(holder):
    root = str(REPO)

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=root, **k)

        def do_GET(self):                                    # noqa: N802
            if self.path.startswith("/index.html") or self.path == "/":
                html = (REPO / "index.html").read_text(encoding="utf-8")
                html = html.replace('<script src="https://cdn.jsdelivr.net/npm/'
                                    '@supabase/supabase-js@2"></script>', STUB)
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
        holder.append(httpd.server_address[1])
        httpd.serve_forever()


def episode(ran_ms, waited_s=None, waiting_on=None, status="assembling",
            needs_look=False, budget=BUDGET):
    """An episode row shaped exactly as the rail hands it to the board."""
    cur = {"step": "assemble_passA", "budget_s": budget,
           "started_at": "__STARTED_AT__", "_ran_ms": ran_ms}
    if waited_s is not None:
        cur["waited_s"] = waited_s
    if waiting_on:
        cur["waiting_on"] = waiting_on
    return {"id": "ep-test", "ep_number": 99, "status": status,
            "needs_look": needs_look, "heartbeat_at": "__NOW__",
            "build_state": {"current": cur}}


JS = """
(rows) => rows.map((ep) => {
  // started_at is computed HERE so the elapsed time is exact at the moment the
  // real function reads the clock — a fixture with a baked timestamp drifts.
  const cur = ep.build_state.current;
  cur.started_at = new Date(Date.now() - cur._ran_ms).toISOString();
  ep.heartbeat_at = new Date().toISOString();
  const ss = stepState(ep);
  return {
    state: ss ? ss.state : null,
    who: ss ? (ss.who || null) : null,
    waitingOn: ss ? (ss.waitingOn || null) : null,
    workingMin: ss ? Math.round(ss.working / 60000) : null,
    ranMin: ss ? Math.round(ss.ran / 60000) : null,
    stage: stageLine(ep),
    // What the OLD comparison would have said, so the control is visible rather
    // than asserted from memory.
    oldWouldSay: (cur.budget_s != null && cur._ran_ms > cur.budget_s * 1000)
                 ? "stuck" : "working",
  };
})
"""


def main():                                                            # noqa: C901
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
    print(f"-- running the SHIPPED stepState/stageLine from {url} --")
    print(f"-- assemble_passA's budget, read from the engine: {BUDGET // 60} min --\n")

    rows = [
        # 0  CONTROL B — genuinely hung, no wait at all: 55 min of nothing.
        episode(55 * MIN),
        # 1  the same 55 minutes, ALL of it spent waiting on the other line.
        #    The phrase is READ FROM THE ENGINE, never retyped here — it is the
        #    string the board prints verbatim, so a copy would drift (#2).
        episode(55 * MIN, waited_s=55 * 60,
                waiting_on=engine.WAITING_ON_OTHER_LINE),
        # 2  the real shape: 40 min waited, then 15 min of honest assembly.
        episode(55 * MIN, waited_s=40 * 60),
        # 3  🔴 THE ONE THAT MATTERS: waited 40, then HUNG for 50. Still stuck.
        episode(90 * MIN, waited_s=40 * 60),
        # 4  an episode from before today — no waited_s key at all.
        episode(55 * MIN),
        # 5  a healthy step, well inside budget.
        episode(10 * MIN),
        # 6  a flag up outranks everything.
        episode(90 * MIN, needs_look=True),
        # 7  a by-design human wait (heygen_download's shape).
        episode(90 * MIN, budget=None),
        # 8-10 rubbish in waited_s must never hide a hung step.
        episode(55 * MIN, waited_s=None),
        episode(55 * MIN, waited_s=-99999),
        episode(55 * MIN, waited_s="forty minutes"),
    ]

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(url)
        page.wait_for_function("typeof stepState === 'function'")
        r = page.evaluate(JS, rows)
        b.close()

    case("the shipped board loaded with no page errors", not errs, str(errs[:2]))

    # ── CONTROL B FIRST: THE ALARM MUST STILL FIRE ──────────────────────────
    print("\n-- (b) CONTROL — A GENUINELY HUNG STEP, NO WAIT --")
    print(f"   ran {r[0]['ranMin']} min · working {r[0]['workingMin']} min · "
          f"state {r[0]['state']!r} · stage {r[0]['stage']!r}")
    case("(b) a hung step with no wait is STILL 'stuck'", r[0]["state"] == "stuck",
         f"the alarm no longer fires — the fix is worse than the problem: {r[0]}")
    case("  …and the card still says 'Stuck —'", r[0]["stage"].startswith("Stuck —"),
         r[0]["stage"])
    case("  …which is exactly what it said before this change",
         r[0]["oldWouldSay"] == "stuck")

    print("\n-- (b) THE HARD HALF — WAITED FIRST, THEN GENUINELY HUNG --")
    print(f"   ran {r[3]['ranMin']} min · working {r[3]['workingMin']} min · "
          f"state {r[3]['state']!r} · stage {r[3]['stage']!r}")
    case("(b) 40 min waited THEN 50 min hung still trips the alarm",
         r[3]["state"] == "stuck",
         "the subtraction blinded the alarm after the wait ended — the EP14 fault")
    case("  …and it is judged on the WORKING 50, not the elapsed 90",
         r[3]["workingMin"] == 50, str(r[3]))

    # ── (a) A LEGITIMATE WAIT MUST NOT TRIP IT ──────────────────────────────
    print("\n-- (a) A STEP THAT HAS BEEN LEGITIMATELY WAITING --")
    print(f"   ran {r[1]['ranMin']} min · working {r[1]['workingMin']} min · "
          f"state {r[1]['state']!r} · stage {r[1]['stage']!r}")
    print(f"   the OLD comparison would have said: {r[1]['oldWouldSay']!r}")
    case("(a) a step blocked on the other line is NOT stuck", r[1]["state"] != "stuck",
         str(r[1]))
    case("  …it is 'waiting', which is a legitimate state that ends by itself",
         r[1]["state"] == "waiting", str(r[1]))
    case("  …and the card NAMES what it is waiting for (#3: say who)",
         r[1]["stage"] == "Waiting for " + engine.WAITING_ON_OTHER_LINE,
         r[1]["stage"])
    case("  …and it never says 'Stuck' or 'nobody is coming'",
         "Stuck" not in r[1]["stage"] and "nobody" not in r[1]["stage"].lower())
    case("CONTROL — and the OLD comparison WOULD have called it stuck",
         r[1]["oldWouldSay"] == "stuck",
         "the fixture does not reproduce the bug, so a green here proves nothing")

    print("\n-- (a) THE REAL SHAPE: 40 MIN WAITED, 15 MIN OF ASSEMBLY --")
    print(f"   ran {r[2]['ranMin']} min · working {r[2]['workingMin']} min · "
          f"state {r[2]['state']!r} · stage {r[2]['stage']!r}")
    case("(a) the wait is subtracted and 15 min of work is inside a 45 min budget",
         r[2]["state"] == "working" and r[2]["workingMin"] == 15, str(r[2]))
    case("CONTROL — the OLD comparison would have called THAT stuck too",
         r[2]["oldWouldSay"] == "stuck")

    # ── NOTHING ELSE MOVED ──────────────────────────────────────────────────
    print("\n-- the states that must not have changed --")
    case("an episode with no waited_s behaves exactly as before",
         r[4]["state"] == "stuck", str(r[4]))
    case("a healthy step is still 'working'", r[5]["state"] == "working", str(r[5]))
    case("a raised flag still outranks the alarm",
         r[6]["state"] == "waiting" and r[6]["who"] == "you", str(r[6]))
    case("a by-design human wait is still never an alarm",
         r[7]["state"] == "waiting" and r[7]["who"] == "a human step", str(r[7]))

    print("\n-- rubbish in waited_s must never hide a hung step --")
    for i, what in ((8, "null"), (9, "negative"), (10, "a string")):
        case(f"waited_s = {what}: the hung step is still stuck",
             r[i]["state"] == "stuck", str(r[i]))

    # ── THE ENGINE SIDE ─────────────────────────────────────────────────────
    print("\n-- what the engine actually writes --")

    class C:
        def __init__(self):
            self.state = {}
            self.saves = 0
            self.mock = False

        def save(self):
            self.saves += 1

    ctx = C()
    engine.mark_step_started(ctx, "assemble_passA")
    started = ctx.state["current"]["started_at"]
    engine.note_step_waiting(ctx, "the other production line's render", 1234.9)
    cur = ctx.state["current"]
    case("note_step_waiting records WHO and HOW LONG",
         cur.get("waiting_on") == "the other production line's render"
         and cur.get("waited_s") == 1234, str(cur))
    case("🔴 …and it NEVER resets started_at (set_step_label's reason)",
         cur["started_at"] == started, f"{cur['started_at']} != {started}")
    case("  …and it saves, or a killed engine loses the wait",
         ctx.saves >= 2)

    engine.clear_step_waiting(ctx)
    cur = ctx.state["current"]
    case("clear_step_waiting drops waiting_on", "waiting_on" not in cur, str(cur))
    case("🔴 …and KEEPS waited_s, or the alarm snaps back the moment work starts",
         cur.get("waited_s") == 1234, str(cur))
    case("  …started_at is still untouched", cur["started_at"] == started)

    empty = C()
    engine.note_step_waiting(empty, "x", 1)
    engine.clear_step_waiting(empty)
    case("neither function invents a marker when no step is in flight",
         empty.state == {} and empty.saves == 0, str(empty.state))

    # ── ASKED OF THE SYNTAX TREE, NOT OF A GREP (§1a) ───────────────────────
    TREE = ast.parse((HERE / "engine.py").read_text(encoding="utf-8"))

    def fn(name):
        for n in ast.walk(TREE):
            if isinstance(n, ast.FunctionDef) and n.name == name:
                return n
        raise AssertionError(f"{name} is not in engine.py")

    for name in ("note_step_waiting", "clear_step_waiting"):
        writes = [t.slice.value for n in ast.walk(fn(name))
                  if isinstance(n, ast.Assign)
                  for t in n.targets
                  if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)]
        case(f"{name} writes no 'started_at' anywhere in its body",
             "started_at" not in writes, str(writes))

    budgets = {k: v for k, v in engine.STEP_BUDGET_S.items() if k.startswith("assemble")}
    case("🔴 assemble_* still HAS a budget — the alarm was not switched off",
         budgets and all(v for v in budgets.values()), str(budgets))

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
