"""SITTING 2b — the supervisor heals a FROZEN engine, and only a frozen one.

Proved FAIL-FIRST in BOTH directions, because this guard is dangerous in both:
  · too shy  -> a suspended engine sits there forever saying "running, nothing to do"
                (pid 87536, 8 Aug 2026 — Modern Standby suspended it mid-build)
  · too keen -> it restarts an engine that is parked at a HUMAN GATE, where the
                heartbeat is deliberately stopped (`hb.active.clear()`), or one that a
                person stopped ON PURPOSE mid-rewind.

Run: python engine/test_supervisor_heartbeat.py
"""
import datetime as dt
import pathlib
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import supervisor as sv          # noqa: E402

FAILED = []
NOW = dt.datetime(2026, 8, 9, 12, 0, 0, tzinfo=dt.timezone.utc)


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


def ago(secs):
    return (NOW - dt.timedelta(seconds=secs)).isoformat()


def fake_rail(rows):
    m = types.ModuleType("rail")
    m.WORKING = {"building", "rendering", "assembling", "revising"}
    m.list_all = lambda: rows
    sys.modules["rail"] = m


print("\n=== frozen_work(): what counts as frozen ===\n")

# --- FAIL FIRST: a genuinely suspended engine mid-build -------------------
fake_rail([{"ep_number": 18, "status": "building", "heartbeat_at": ago(1400)}])
f = sv.frozen_work(NOW)
check("a WORKING episode gone quiet IS frozen", f is not None, "nothing reported")
check("  and it names the episode and the status",
      bool(f) and "PP-EP18" in f[0] and "building" in f[0], str(f))
check("  and the age is right (~23m)", bool(f) and 1390 < f[1] < 1410, str(f))

# --- FAIL FIRST the other way: a human gate is NOT frozen -----------------
fake_rail([{"ep_number": 18, "status": "awaiting_approval", "heartbeat_at": ago(90000)}])
check("a HUMAN GATE with a 25-hour-old heartbeat is NOT frozen",
      sv.frozen_work(NOW) is None,
      "this is the trap: hb.active.clear() runs at the gates on purpose")
fake_rail([{"ep_number": 18, "status": "awaiting_render", "heartbeat_at": ago(4000)}])
check("  awaiting_render likewise", sv.frozen_work(NOW) is None)
fake_rail([{"ep_number": 17, "status": "ready", "heartbeat_at": ago(99999)},
           {"ep_number": 16, "status": "published", "heartbeat_at": ago(99999)}])
check("  finished episodes likewise", sv.frozen_work(NOW) is None)

# --- and the healthy case -------------------------------------------------
fake_rail([{"ep_number": 18, "status": "assembling", "heartbeat_at": ago(20)}])
check("a WORKING episode beating normally is NOT frozen", sv.frozen_work(NOW) is None)
fake_rail([{"ep_number": 18, "status": "building", "heartbeat_at": None}])
check("no heartbeat recorded at all is not treated as frozen",
      sv.frozen_work(NOW) is None, "nothing to measure is not evidence of death")

# --- the WORKING set is DERIVED, not retyped ------------------------------
import ast                                                            # noqa: E402
src = ast.parse((HERE / "supervisor.py").read_text(encoding="utf-8"))
fn = next(n for n in ast.walk(src) if isinstance(n, ast.FunctionDef)
          and n.name == "frozen_work")
literals = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant)
            and isinstance(n.value, str)]
check("the status set is taken from rail.WORKING, not retyped",
      not any(s in literals for s in ("building", "rendering", "assembling", "revising")),
      f"found hard-coded statuses: {literals}")

print("\n=== start(): who gets restarted, and who is left alone ===\n")

calls = []

# 🔴 A TEST MUST NOT WRITE INTO THE OPERATIONAL LOG. The first run of this suite put
# five fabricated supervisor lines into engine/logs/engine-2026-08-09.log — including
# "engine running (pid 4242)" and "engine.stopped is present" — and hours later, while
# diagnosing why EP19 had not started, those lines were the newest thing in the file and
# read as a live engine being held back. They were mine.
#     A DIAGNOSIS IS ONLY AS GOOD AS THE LOG, AND A TEST THAT WRITES TO IT IS LYING TO
#     THE NEXT PERSON WHO READS IT — who is usually you, at one in the morning.
_TEST_LOG = pathlib.Path(tempfile.mkdtemp(prefix="pp-sv-log-")) / "supervisor-test.log"
sv.log_path = lambda *_a, **_k: _TEST_LOG


def real_ago(secs):
    """start() calls frozen_work() with no argument, so it uses the REAL clock.
    The fixed NOW above is for the direct unit calls only — anchoring these rows to
    it put the heartbeats in the FUTURE and the age came out negative."""
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=secs)).isoformat()


def arm(pid, rows, marker_text=None):
    calls.clear()
    fake_rail(rows)
    sv.engine_pid = lambda: pid
    sv.environment_problem = lambda *a, **k: None
    sv.subprocess = types.SimpleNamespace(
        run=lambda cmd, **k: (calls.append(list(map(str, cmd))),
                              types.SimpleNamespace(returncode=0))[1],
        STDOUT=None)
    if marker_text is None:
        sv.STOP_MARKER.unlink(missing_ok=True)
    else:
        sv.STOP_MARKER.write_text(marker_text, encoding="utf-8")


def killed():
    return any("taskkill" in c[0] for c in calls)


try:
    # --- FAIL FIRST: frozen and nobody said to leave it -> RESTART --------
    arm(4242, [{"ep_number": 18, "status": "building", "heartbeat_at": real_ago(1400)}])
    sv.start()
    check("a frozen engine IS stopped so it can restart", killed(),
          f"calls: {calls}")

    # --- FAIL FIRST the other way: deliberate stop -> HANDS OFF ----------
    arm(4242, [{"ep_number": 18, "status": "building", "heartbeat_at": real_ago(1400)}],
        marker_text="sending EP18 back a stage for the C9 fix")
    sv.start()
    check("a DELIBERATELY STOPPED engine is NOT touched", not killed(),
          f"calls: {calls}")

    # --- and the ordinary healthy tick -----------------------------------
    arm(4242, [{"ep_number": 18, "status": "building", "heartbeat_at": real_ago(15)}])
    sv.start()
    check("a healthy engine is not touched", not killed(), f"calls: {calls}")

    # --- marker with no engine running: do not start ---------------------
    arm(None, [], marker_text="held for maintenance")
    sv.start()
    check("with the marker present and no engine, it does NOT start one",
          not any("engine.py" in " ".join(c) for c in calls), f"calls: {calls}")

    # --- no marker, no engine: normal start ------------------------------
    arm(None, [])
    sv.start()
    check("with no marker and no engine, it DOES start one",
          any("engine.py" in " ".join(c) for c in calls), f"calls: {calls}")
finally:
    sv.STOP_MARKER.unlink(missing_ok=True)

print(f"\n{'=' * 66}")
print("ALL PROVED (fail-first, both directions)" if not FAILED else f"FAILURES: {FAILED}")
sys.exit(1 if FAILED else 0)
