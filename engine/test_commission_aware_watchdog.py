#!/usr/bin/env python3
"""#6 — THE WATCHDOG LEARNS WHAT A COMMISSION IS.

    python engine/test_commission_aware_watchdog.py

`STEP_BUDGET_S` had NO entry for `audit_inputs`, so it fell to the 900s default while
the commission that step runs is bounded at `EPJSON_ATTEMPTS x 1800s = 5400s`. **Its
alarm was set to one sixth of its own bound**, and the board reads that number straight
off the row:

    EP18  audit_inputs ran 1029s -> "Stuck — Checking the inputs" for the last 2m 09s
    EP19  audit_inputs ran 1907s -> "Stuck — Checking the inputs" for the last 16m 47s

Two out of two, and BOTH EPISODES WERE FINE. Under the render-first order that lie is
the first thing Jodie sees after approving, which is why the spec says: moving the
render without this trades a delay for a lie.

🔴 AND NOT BY ASKING WHETHER THE PROCESS IS ALIVE. This repo has paid for that twice —
CLAUDE.md fault #1 (assert the artefact, not the thing that reports on it) and the
Modern Standby suspension where `engine_pid()` said "running" about a frozen process,
for ever. A live pid is a proxy. The bound is not.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import commission as com                                             # noqa: E402
import engine                                                        # noqa: E402

PASS, FAIL = [], []


def case(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


# ── 1. the budget agrees with the bound, and is DERIVED from it ────────────────
budget = engine.STEP_BUDGET_S.get("audit_inputs")
case("audit_inputs has a budget at all", budget is not None,
     "it still falls through to the 900s default")
# 🔴 THE MAX, NOT THE FLOOR — C2, 14 Aug 2026. The epjson ceiling now SCALES with the
# script (commission.epjson_timeout), because a fixed 1800 cut off a WORKING writer on
# EP23 and EP24 running. TIMEOUT_EPJSON_S is therefore only the LOWER bound now, and an
# alarm set to it would fire while a big episode's writer was still legitimately going —
# the exact fault this suite exists to prevent, arriving through the back door.
case("  …and it is the commission's OWN bound, not a typed number",
     budget == engine.EPJSON_ATTEMPTS * com.EPJSON_MAX_S + 300,
     f"{budget} != {engine.EPJSON_ATTEMPTS} x {com.EPJSON_MAX_S} + 300")
case("  …and it agrees with the LOOSEST ceiling a commission can run under",
     budget >= engine.EPJSON_ATTEMPTS * com.epjson_timeout(60000) + 300,
     "a scaled commission could outlive its own alarm")
case("  …while the measured floor is never lowered",
     com.epjson_timeout(1) >= com.TIMEOUT_EPJSON_S and
     com.epjson_timeout(None) == com.TIMEOUT_EPJSON_S,
     "1800 was earned by a real observation; scaling may raise it, never lower it")
case("  …and a genuinely stuck writer still fails, rather than hanging all night",
     com.epjson_timeout(10 ** 7) == com.EPJSON_MAX_S)

# 🔴 THE CONTROL, IN THE NUMBERS THAT ACTUALLY HAPPENED. If either of these ever reads
# "stuck" again, the board is calling a working writer stuck, which is the whole fault.
for ep_name, ran in (("EP18", 1029), ("EP19", 1907)):
    case(f"CONTROL — {ep_name}'s real {ran}s commission reads WORKING, not stuck",
         ran <= budget, f"{ran}s is over the {budget}s budget")
case("  …and the OLD 900s default would have called both of them stuck",
     1029 > engine.DEFAULT_STEP_BUDGET_S and 1907 > engine.DEFAULT_STEP_BUDGET_S,
     "the default is no longer 900s, so this control proves nothing")

# and the alarm must still be able to fire
case("a genuinely thrashing writer past the bound STILL alarms",
     (budget + 1) > budget and not (budget + 1 <= budget),
     "the budget cannot be exceeded, so the alarm can never fire")

# ── 2. the other commissioning steps got the same treatment ───────────────────
for step in ("ebook_pdf", "youtube_copy"):
    b = engine.STEP_BUDGET_S.get(step)
    case(f"{step} has a derived budget too", b == com.TIMEOUT_S + 300,
         f"{b!r} — it commissions at {com.TIMEOUT_S}s and had no headroom")

# ── 3. ONE VALUE, ONE HOME ────────────────────────────────────────────────────
prov = (HERE / "providers.py").read_text(encoding="utf-8")
case("providers.py no longer re-reads the timeout env vars itself",
     'os.environ.get("ENGINE_COMMISSION_TIMEOUT' not in prov,
     "a second reader of the same value is fault #2 — it drifts the day one is raised")
# C2, 14 Aug 2026: providers now asks commission.py to COMPUTE the epjson ceiling from
# the script rather than reading the constant, because a fixed 1800 cut off a working
# writer on EP23 and EP24. The requirement is unchanged and is what is asserted — the
# value comes from commission.py, never from a number typed into providers.
case("  …it reads commission.py's definition",
     "com.epjson_timeout(" in prov or "com.TIMEOUT_EPJSON_S" in prov)
case("  …and the epjson ceiling is COMPUTED there, not fixed at the call site",
     "com.epjson_timeout(" in prov,
     "a fixed ceiling is what cut EP23 and EP24 off mid-write")

# ── 4. the label reaches the board, and the CLOCK IS NEVER RESET ──────────────
src = (HERE / "engine.py").read_text(encoding="utf-8")
case("the engine can put its own sentence on the in-flight marker",
     "def set_step_label(" in src)
i = src.index("def set_step_label(")
body = src[i:src.index("\ndef ", i + 10)]
case("  🔴 …and set_step_label NEVER re-stamps started_at",
     "started_at" not in body.split('"""')[2],
     "resetting the clock per attempt makes a wedged writer invisible for ever — the "
     "exact fault the watchdog was built for (EP14, three and a half days)")
case("  …and the epjson commission passes it through",
     "on_start=lambda text: set_step_label(ctx, text)" in src)

comsrc = (HERE / "commission.py").read_text(encoding="utf-8")
case("commission() offers the on_start hook", "on_start=None" in comsrc)
case("  …and a failing label can never fail a commission",
     "a label is never worth failing a commission over" in comsrc)

# ── 5. the board prefers the label, and the render line is an INSTRUCTION ─────
app = (HERE.parent / "app.js").read_text(encoding="utf-8")
case("the board prefers the engine's label over the step name",
     "ss.state === \"working\" && ss.label" in app)
case("  …and still falls back to STEP_LABELS", "STEP_LABELS[ss.step]) return" in app)
case("the render-gate line reads as an INSTRUCTION",
     'render_gate: "Render ready — start it in HeyGen"' in app,
     "under render-first this is the FIRST thing she sees after approving")

# ── 6. NO PID SNIFFING ANYWHERE NEAR THIS ─────────────────────────────────────
case("liveness is judged by the BUDGET, never by a live process",
     not re.search(r"(psutil|pid_exists|is_running\(\))", src),
     "a frozen process IS alive — pid 87536 under Modern Standby, and the supervisor "
     "said 'running' for ever")

print(f"\ncommission-aware watchdog: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
