#!/usr/bin/env python3
"""THE LOCK IS IN THE RIGHT PLACE, AND ITS FAILURES REACH JODIE IN ENGLISH.

    python engine/test_render_lock_wiring.py

Two things are proved here, and the first is a placement:

🔴 THE `with` IS OUTSIDE `RealProvider.run()`, NOT INSIDE IT. `run()` is
`subprocess.run(..., timeout=PASS_TIMEOUT)` — 2400s — and that clock starts when
the ffmpeg child starts. Acquire the lock inside it and a forty-minute wait for the
other production line eats two thirds of the ffmpeg budget; the child is killed for
being slow; and `run_step` hands the operator a raw `TimeoutExpired` carrying the
whole ffmpeg command line. Out at the step, the wait happens before any child
exists.

🔴 AND THE MODULE'S OWN ERROR TEXT MAY NOT REACH THE BOARD. It names a lock file
path and tells the reader to run `python render_lock.py release --force`. Correct
for an engineer; banned by `docs/PP-operator-box-rule.md`, and Jodie is never to be
asked to run it. CASE 1 IS THE CONTROL: it shows the raw message really does
contain those things, so the re-wording is measured against a real problem rather
than an assumed one.

Nothing here touches the real lock file, the rail, the network or an episode: every
case runs against a lock in a throwaway temp directory.
"""
from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

import engine                                                         # noqa: E402
import render_lock                                                    # noqa: E402
from providers import EngineFlag                                      # noqa: E402

PASS, FAIL = [], []


def case(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'ok  ' if ok else '!!  '}{name}")
    if not ok and detail:
        print(f"      {detail}")


class Ctx:
    """Only what render_lock_held touches."""

    def __init__(self, mock=False):
        self.mock = mock
        self.state = {"current": {"step": "assemble_passA", "budget_s": 2700,
                                  "started_at": "2026-08-30T00:00:00+00:00"}}
        self.saves = 0

    def save(self):
        self.saves += 1


TMP = Path(tempfile.mkdtemp(prefix="pp-lockwire-"))
LOCK = TMP / "render.lock"
os.environ["EQUEST_RENDER_LOCK"] = str(LOCK)


def flag_from(make_holder_look_like):
    """Run render_lock_held against a lock in whatever state the caller sets up,
    and return the EngineFlag it produced (or None)."""
    make_holder_look_like()
    ctx = Ctx()
    try:
        with engine.render_lock_held(ctx, "PP-EP99 assembly (pass A)"):
            pass
        return None, ctx
    except EngineFlag as e:
        return e, ctx


def a_dead_holder():
    """Someone else holds it and stopped breathing 30 minutes ago."""
    for p in (str(LOCK) + ".beat", str(LOCK)):
        Path(p).unlink(missing_ok=True)
    h = render_lock.acquire("IW", "IWEP034 build", path=str(LOCK), say=None)
    h["heart"].stop()
    old = time.time() - (render_lock.STALE_AFTER_S + 1800)
    os.utime(str(LOCK) + ".beat", (old, old))
    os.utime(str(LOCK), (old, old))
    render_lock._as_a_foreign_process(str(LOCK))       # it is THEIRS, not ours


# ── 1. THE CONTROL — THE RAW MESSAGE IS NOT FIT FOR THE OPERATOR'S BOX ──────
a_dead_holder()
raw = ""
try:
    render_lock.acquire("PP", "x", path=str(LOCK), wait=False, say=None)
except render_lock.LockStale as e:
    raw = str(e)
print("-- CONTROL: what the shared module says on its own --")
for line in raw.strip().splitlines():
    print(f"   | {line}")
case("CONTROL — the raw message really does name a file path",
     str(LOCK) in raw, raw)
case("CONTROL — …and really does tell the reader to run a shell command",
     "release --force" in raw, raw)
print("   (so the re-wording below is fixing a real problem, not an assumed one)\n")

# ── 2. WHAT JODIE ACTUALLY GETS ────────────────────────────────────────────
flag, ctx = flag_from(a_dead_holder)
msg = str(flag or "")
print("-- what the operator's box shows instead --")
for line in msg.strip().splitlines():
    print(f"   | {line}")
print()
case("a dead holder raises a flag rather than stealing the lock", flag is not None)
case("🔴 the flag carries no file path, no backslash, no URL",
     not any(t in msg for t in (str(LOCK), "\\", "http", ".lock")), msg)
case("🔴 …and no shell command for Jodie to run",
     not any(t in msg.lower() for t in ("--force", "python ", "render_lock", "cmd")),
     msg)
case("it says the other line's render has stopped responding",
     "stopped responding" in msg.lower(), msg)
case("it says nothing was lost and nothing was spent",
     "nothing has been lost" in msg.lower() and "spent" in msg.lower(), msg)
case("it says this is a studio fault, not something to fix on the board",
     "not something to fix on the board" in msg.lower(), msg)
case("it says to tell whoever looks after the engine",
     "looks after the engine" in msg.lower(), msg)
case("it says plainly whether clearing the flag helps, and when (#6)",
     "clear this flag" in msg.lower() and "once they have sorted it" in msg.lower(),
     msg)
case("the lock was NOT stolen — it is still on disk, still theirs",
     LOCK.is_file() and (render_lock.read_holder(str(LOCK)) or {}).get("project") == "IW")

# ── 3. LockBusy IS RE-WORDED TOO ───────────────────────────────────────────
#
# ⚠️ ASKED OF THE SYNTAX TREE, AND THAT IS NOT LAZINESS. `render_lock_held` passes
# no `timeout_s`, so `acquire` waits indefinitely and LockBusy is UNREACHABLE
# through the wrapper today — driving it would simply hang this suite, which is
# exactly what it did the first time this file was run. The handler exists so that
# the day somebody adds a timeout, the operator does not meet the raw message; the
# honest test of an unreachable branch is its SHAPE.
TREE = ast.parse((HERE / "engine.py").read_text(encoding="utf-8"))


def fn(name):
    for n in ast.walk(TREE):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name} is not in engine.py")


held = fn("render_lock_held")
handlers = {}
for n in ast.walk(held):
    if isinstance(n, ast.ExceptHandler) and isinstance(n.type, ast.Attribute):
        raised = [x for x in ast.walk(n)
                  if isinstance(x, ast.Raise) and isinstance(x.exc, ast.Call)
                  and isinstance(x.exc.func, ast.Name)]
        handlers[n.type.attr] = [r.exc.func.id for r in raised]
case("both LockStale and LockBusy are caught",
     {"LockStale", "LockBusy"} <= set(handlers), sorted(handlers))
case("  …and each one raises an EngineFlag rather than letting the raw text out",
     all(v == ["EngineFlag"] for v in handlers.values()), str(handlers))

# ── 4. THE WAIT IS RECORDED WHILE IT IS HAPPENING ──────────────────────────
# A REAL CONTENDED WAIT, not a simulated one: the other line takes the lock, PP
# blocks on it, and a timer hands it over a second later. `_as_a_foreign_process`
# drops the in-memory record that we own it, or the nested-hold path would answer
# our own re-entry question and PP would never wait at all.
print("\n-- a real contended wait, recorded on the in-flight marker --")
for p in (str(LOCK) + ".beat", str(LOCK)):
    Path(p).unlink(missing_ok=True)
live = render_lock.acquire("IW", "IWEP035 build", path=str(LOCK), say=None)
render_lock._as_a_foreign_process(str(LOCK))
seen = {}
ctx = Ctx()
real_note = engine.note_step_waiting


def spy(c, who, waited):
    real_note(c, who, waited)
    seen.setdefault("first", dict(c.state["current"]))


engine.note_step_waiting = spy
render_lock.SAY_EVERY_S = 0.0            # say on the first pass, not after 60s
render_lock.POLL_S = 0.2
threading.Timer(1.2, lambda: (render_lock._HELD.__setitem__(
    os.path.abspath(str(LOCK)), live["token"]), render_lock.release(live))).start()
t0 = time.time()
with engine.render_lock_held(ctx, "PP-EP99 assembly (pass A)"):
    inside = dict(ctx.state["current"])
waited_for = time.time() - t0
engine.note_step_waiting = real_note

case("it really had to wait for the other line", waited_for > 1.0,
     f"only {waited_for:.2f}s — the contention did not happen, so this proves nothing")
case("while blocked, the marker NAMES what it is waiting for",
     seen.get("first", {}).get("waiting_on") == engine.WAITING_ON_OTHER_LINE,
     str(seen.get("first")))
case("  …and started_at was never moved",
     seen.get("first", {}).get("started_at") == "2026-08-30T00:00:00+00:00")
case("once the lock is granted, waiting_on is gone",
     "waiting_on" not in inside, str(inside))
case("🔴 …but waited_s is KEPT, so the board keeps subtracting it",
     "waited_s" in inside, str(inside))
case("and after the block the marker is not left saying 'waiting'",
     "waiting_on" not in ctx.state["current"], str(ctx.state["current"]))
case("the lock was given back", not LOCK.exists(), "still held after the block")

# ── 4b. A RAIL BLIP DURING A WAIT MUST NOT KILL A HEALTHY BUILD ────────────
# The marker updates end in a rail write and one of them runs INSIDE `acquire`'s
# wait loop, so an exception there comes out of `hold.__enter__`. Forty minutes
# into a legitimate wait, that would fail an assembly step for a bookkeeping
# reason. CONTROL: a ctx whose every save throws.
print("\n-- a rail blip while waiting is survivable --")


class BrokenRail(Ctx):
    def save(self):
        raise RuntimeError("PostgREST unreachable")


ran_body = {"yes": False}
try:
    with engine.render_lock_held(BrokenRail(), "PP-EP99 assembly (pass A)"):
        ran_body["yes"] = True
    survived = True
except Exception as e:                                                # noqa: BLE001
    survived = False
    print(f"      it raised {e.__class__.__name__}: {e}")
case("🔴 a rail that throws on every write does NOT fail the step",
     survived and ran_body["yes"],
     "bookkeeping killed a build that was doing nothing wrong")
case("  …and the lock was still given back afterwards", not LOCK.exists())

# ── 5. PLACEMENT — THE THING THAT MUST NOT DRIFT ───────────────────────────
print("\n-- placement --")


def calls_in(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                base = f.value.id if isinstance(f.value, ast.Name) else "?"
                out.add(f"{base}.{f.attr}")
    return out


for step in ("step_assemble_passA", "step_assemble_passB"):
    node = fn(step)
    withs = [w for w in ast.walk(node) if isinstance(w, ast.With)]
    case(f"{step} holds the render lock", "render_lock_held" in calls_in(node),
         str(sorted(calls_in(node))))
    inner = set().union(*[calls_in(w) for w in withs]) if withs else set()
    case(f"  …and the ffmpeg work is INSIDE the with",
         any(c.endswith("assemble_passA") or c.endswith("assemble_passB")
             for c in inner), str(sorted(inner)))

# the rail write must be OUTSIDE, so the machine is handed back before bookkeeping
passb = fn("step_assemble_passB")
inside_with = set().union(*[calls_in(w) for w in ast.walk(passb)
                            if isinstance(w, ast.With)])
case("🔴 passB's rail write is OUTSIDE the lock",
     not any(c.endswith("ep_set") for c in inside_with), str(sorted(inside_with)))

# and the lock must never appear inside the subprocess clock
PROV = ast.parse((HERE / "providers.py").read_text(encoding="utf-8"))
for node in ast.walk(PROV):
    if isinstance(node, ast.ClassDef) and node.name == "RealProvider":
        for sub in node.body:
            if isinstance(sub, ast.FunctionDef) and sub.name in (
                    "run", "py", "assemble_passA", "assemble_passB"):
                bad = {c for c in calls_in(sub) if "render_lock" in c or "hold" == c}
                case(f"🔴 RealProvider.{sub.name} does NOT take the lock "
                     f"(it would run inside PASS_TIMEOUT)", not bad, str(bad))

case("PASS_TIMEOUT is still the ffmpeg budget and nothing else",
     __import__("providers").RealProvider.PASS_TIMEOUT == 2400)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print(f"  FAILED: {f}")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
