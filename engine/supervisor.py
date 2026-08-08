#!/usr/bin/env python3
"""supervisor.py — start the engine, and keep starting it. Run by Task Scheduler.

    python supervisor.py            # one tick: start the engine if it is not up
    python supervisor.py --status   # say what it would do, change nothing

WHY THIS EXISTS
---------------
The engine died overnight on 28 July 2026 and nothing noticed for hours. It has now
gone down twice in two days, and only ONE of those was a fault:

  1. A socket-level timeout on the Supabase poll in the idle loop went past
     `rail._request`'s `HTTPError`-only handler to the top of the process. Fixed (B6)
     — but a fix for one cause is not a supervisor.
  2. **The stale-code guard exiting on purpose.** `_code_changed()` ends the process
     whenever engine.py, providers.py or rail.py changes, so that months-old logic is
     never left running in memory. That is CORRECT behaviour, and it means **every
     deploy leaves the engine down until a human restarts it.**

Case 2 is the one that actually bit, twice, and it is not a bug to be fixed — it is a
design decision that needs a partner. This is the partner.

WHAT IT GUARANTEES, AND WHAT IT DELIBERATELY DOES NOT
-----------------------------------------------------
It starts the engine. It does **not** decide anything, clear anything, render
anything or publish anything. A supervisor that could do any of those would be
automation eating a decision; this one eats a chore — *"go and start it again"*.

THE THREE THINGS JODIE MADE REQUIREMENTS, NOT NOTES
---------------------------------------------------
1. **The working directory is set explicitly.** Task Scheduler's default cwd is
   `C:\\Windows\\System32`, and the engine resolves the skill and the lock relative to
   itself but the *scripts it shells out to* run with `cwd=` the episode folder. An
   implicit cwd is a difference between "it works when I run it" and "it works".
2. **`.env` is located explicitly.** `rail.py` looks for `PP_VIDEOS_DIR/.env` and
   then walks up from `__file__` — and since the repo moved off Drive, that walk
   reaches the repo root, which has no `.env` **and a .gitignore forbidding one**. So
   `PP_VIDEOS_DIR` is set here rather than left to a default that has already been
   wrong once.
3. **stdout goes to a DATED log file.** Without it a crash is invisible again, which
   is the entire fault being fixed. A supervisor whose failures are silent is worse
   than none, because it also removes the human habit of checking.

IT REFUSES TO START INTO A BROKEN ENVIRONMENT, LOUDLY. If G: is not mounted (Drive
not up yet after a boot) or the `.env` is unreadable, it writes WHY to the log and
exits 0 — the next tick five minutes later will find Drive up. Starting the engine
into a missing Drive would produce a confusing failure and a `needs_look` about an
episode, blaming the episode for the machine.
"""
import argparse
import datetime as _dt
import os
import re
import subprocess
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
REPO = ENGINE_DIR.parent
LOG_DIR = ENGINE_DIR / "logs"
LOCK = ENGINE_DIR / "engine.lock"

# Requirement 2, explicit. Overridable for a test rig, but never implicit.
PP_VIDEOS = Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))


def now():
    return _dt.datetime.now()


def log_path(t=None) -> Path:
    return LOG_DIR / f"engine-{(t or now()):%Y-%m-%d}.log"


def say(msg: str) -> None:
    """One line, to the dated log AND to stdout, stamped. Never swallowed."""
    line = f"[{now():%Y-%m-%d %H:%M:%S}] [supervisor] {msg}"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_path(), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    # THE FILE IS WRITTEN FIRST AND UNCONDITIONALLY. Under pythonw.exe `sys.stdout`
    # is None and this print would raise — a supervisor that dies trying to announce
    # itself is exactly the silent failure this whole thing exists to end.
    try:
        print(line, flush=True)
    except (AttributeError, OSError, ValueError):
        pass


def engine_pid():
    """The pid of a LIVE engine, or None. Mirrors engine._acquire_lock exactly.

    A lingering handle makes OpenProcess succeed on an exited process, so only exit
    code 259 (STILL_ACTIVE) counts as running — the same trap engine.py documents.
    """
    if not LOCK.exists():
        return None
    try:
        pid = int(LOCK.read_text().strip())
    except (ValueError, OSError):
        return None
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)
        if not h:
            return None
        code = ctypes.c_ulong()
        alive = k.GetExitCodeProcess(h, ctypes.byref(code)) and code.value == 259
        k.CloseHandle(h)
        return pid if alive else None
    except (OSError, AttributeError):
        return None


def _powercfg():
    """The raw sleep settings, as Windows reports them."""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "powercfg /q SCHEME_CURRENT SUB_SLEEP STANDBYIDLE"],
        capture_output=True, text=True, timeout=60)
    return r.stdout or ""


def _mins(seconds):
    if seconds % 60 == 0:
        m = seconds // 60
        return f"{m} min" if m else "never"
    return f"{seconds}s"


def standby_problem(query=_powercfg):
    """Will this machine fall asleep under a running build? CHECKED, not trusted.

    🔴 SLEEP IS THE SINGLE LARGEST COST IN THIS PROJECT'S HISTORY. EP14 lost FOURTEEN
    HOURS to Modern Standby, and the 2400s ffmpeg timeout — being wall-clock — then
    fired 13h34m late and destroyed 39 minutes of real compute on waking.

    ⚠️ AND A NOTE WOULD NOT HAVE BEEN ENOUGH. Jodie set the power plan to never sleep,
    sincerely, and set the WRONG HALF: Windows keeps SEPARATE timers for mains and
    battery. Measured on her machine immediately afterwards:
        Current AC Power Setting Index: 0x00000000  ->   0s = never  ✓
        Current DC Power Setting Index: 0x000000b4  -> 180s = 3 min  ✗
    and EP14's fourteen hours were lost on battery. A person can do this correctly and
    still be wrong, so BOTH halves are checked here rather than written down somewhere.

    FAILS OPEN. If powercfg is missing, silent or unparseable this returns None and the
    engine starts: a guard that cannot read its input must not brick the studio. It says
    so in the log rather than pretending it checked.
    """
    try:
        out = query()
    except Exception:                                             # noqa: BLE001
        return None
    ac = re.search(r"Current AC Power Setting Index:\s*0x([0-9a-fA-F]+)", out or "")
    dc = re.search(r"Current DC Power Setting Index:\s*0x([0-9a-fA-F]+)", out or "")
    if not (ac and dc):
        return None                                               # cannot tell -> allow
    bad = []
    if int(ac.group(1), 16):
        bad.append(f"on MAINS after {_mins(int(ac.group(1), 16))}")
    if int(dc.group(1), 16):
        bad.append(f"on BATTERY after {_mins(int(dc.group(1), 16))}")
    if not bad:
        return None
    return (
        "THIS MACHINE WILL FALL ASLEEP UNDER A BUILD — it is set to sleep "
        + " and ".join(bad) + ".\n"
        "    Sleep cost EP14 fourteen hours: the engine is suspended, the ffmpeg "
        "timeout is wall-clock so it fires late on waking and kills work that was "
        "nearly done.\n"
        "    Windows keeps SEPARATE timers for mains and battery, so setting one and "
        "not the other looks fixed and is not — which is exactly what happened here.\n"
        "    Fix BOTH, then this starts by itself within five minutes:\n"
        "      powercfg /change standby-timeout-ac 0\n"
        "      powercfg /change standby-timeout-dc 0")


def environment_problem(standby=_powercfg):
    """Why the engine must NOT be started right now — or None if it may be."""
    if not PP_VIDEOS.is_dir():
        return (f"{PP_VIDEOS} is not there. Google Drive is probably not mounted yet "
                f"(usual right after a boot). Not starting; the next tick will retry.")
    env = PP_VIDEOS / ".env"
    if not env.is_file():
        return (f"no .env at {env}. The engine cannot reach Supabase without it, and "
                f"it must NEVER be moved into the repo — the repo is public.")
    # The same gate that refuses a missing Drive refuses a machine that will sleep.
    # It retries every five minutes, so fixing the setting starts the engine by itself.
    return standby_problem(standby)


# ── E-b: "THE PID IS ALIVE" IS A PROXY FOR "IT IS WORKING" ────────────────────
# pid 87536 was SUSPENDED by Modern Standby on 8 Aug 2026: last log line "engine up",
# then nothing — no traceback, no exit. `engine_pid()` asks whether the pid exists, and
# a frozen process DOES exist, so this said "running — nothing to do" and would have
# said it forever. The BOARD already knew (it flags a stale heartbeat); the supervisor
# never looked.
#
# ⚠️ THE TRAP THIS IS DESIGNED AROUND, or the fix kills healthy engines: THE HEARTBEAT
# IS DELIBERATELY NOT BEATING AT A HUMAN GATE. `hb.active.clear()` runs at
# awaiting_render / awaiting_cover / awaiting_approval, and the board ignores staleness
# there on purpose. So a naive "stale => restart" would kill an engine parked correctly,
# waiting on Jodie. Restart only when some episode is in a WORKING status — and take
# that set from `rail.WORKING`, never retyped here (one source of truth).
STALE_SECS = 300          # the board's "a few min"; a step that beats every loop is far under
STOP_MARKER = ENGINE_DIR / "engine.stopped"


def frozen_work(_now=None):
    """(label, seconds_stale) if a WORKING episode's heartbeat has gone quiet."""
    try:
        sys.path.insert(0, str(ENGINE_DIR))
        import rail
    except Exception as e:                                        # noqa: BLE001
        say(f"could not read the rail to check liveness ({type(e).__name__}) — "
            "leaving the engine alone")
        return None
    now_ = _now or _dt.datetime.now(_dt.timezone.utc)
    worst = None
    for e in rail.list_all():
        if e.get("status") not in rail.WORKING:
            continue                       # a human gate: silence is correct there
        hb = e.get("heartbeat_at")
        if not hb:
            continue
        try:
            age = (now_ - _dt.datetime.fromisoformat(str(hb).replace("Z", "+00:00"))
                   ).total_seconds()
        except Exception:                                          # noqa: BLE001
            continue
        if age > STALE_SECS and (worst is None or age > worst[1]):
            worst = (f"PP-EP{e.get('ep_number')} ({e.get('status')})", age)
    return worst


def stopped_on_purpose():
    """A deliberate stop and a freeze look IDENTICAL from outside — both are a pid
    that is not beating. The difference is that somebody MEANT one of them, and only
    that person can say so. Whoever stops the engine on purpose writes this marker;
    the healer reads it and keeps its hands off.

    Learned the hard way on 8 Aug 2026: the engine was stopped deliberately to send
    EP18 back a stage, the board showed a stale heartbeat and "self_qc stuck 22 min",
    and a restart was asked for. Had this healer existed then, it would have fought
    the rewind and restarted the engine underneath a deliberate hold.
    """
    if not STOP_MARKER.exists():
        return None
    try:
        return STOP_MARKER.read_text(encoding="utf-8").strip() or "no reason given"
    except Exception:                                              # noqa: BLE001
        return "no reason given"


def start():
    problem = environment_problem()
    if problem:
        say(f"NOT STARTING — {problem}")
        return 0

    pid = engine_pid()
    if pid:
        why = stopped_on_purpose()
        if why:
            say(f"engine running (pid {pid}) and {STOP_MARKER.name} is present — "
                f"leaving it alone. Reason on file: {why}")
            return 0
        frozen = frozen_work()
        if not frozen:
            say(f"engine already running (pid {pid}) — nothing to do")
            return 0
        label, age = frozen
        say(f"engine pid {pid} is ALIVE BUT NOT WORKING — {label} has not beaten for "
            f"{int(age // 60)}m{int(age % 60):02d}s (a working status, so silence is "
            f"not a human gate). Stopping it so the next tick starts fresh code.")
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, text=True)
        except Exception as e:                                     # noqa: BLE001
            say(f"could not stop pid {pid}: {e}")
            return 0
        say(f"stopped pid {pid} — restarting now")
    elif stopped_on_purpose():
        say(f"{STOP_MARKER.name} is present — NOT starting. "
            f"Reason on file: {stopped_on_purpose()}")
        return 0

    env = dict(os.environ)
    env["PP_VIDEOS_DIR"] = str(PP_VIDEOS)          # requirement 2
    env["PYTHONUNBUFFERED"] = "1"                  # or the log lags the failure
    env["PYTHONIOENCODING"] = "utf-8"

    say(f"starting: {sys.executable} engine.py run --watch")
    say(f"  cwd            {ENGINE_DIR}")
    say(f"  PP_VIDEOS_DIR  {PP_VIDEOS}")
    say(f"  log            {log_path()}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_path(), "a", encoding="utf-8") as fh:
        # THE TASK INSTANCE LIVES AS LONG AS THE ENGINE. With the task set to ignore
        # a new instance while one is running, the 5-minute repetition is then a
        # no-op during normal operation and a restart within 5 minutes of any exit —
        # crash or the deliberate stale-code exit alike.
        r = subprocess.run(
            [sys.executable, str(ENGINE_DIR / "engine.py"), "run", "--watch"],
            cwd=str(ENGINE_DIR),                   # requirement 1
            env=env, stdout=fh, stderr=subprocess.STDOUT)
    say(f"engine exited {r.returncode} — the next tick will start it again")
    return 0


def status():
    pid = engine_pid()
    problem = environment_problem()
    print(f"engine        {'running, pid ' + str(pid) if pid else 'NOT running'}")
    print(f"lock          {LOCK} ({'present' if LOCK.exists() else 'absent'})")
    print(f"PP_VIDEOS_DIR {PP_VIDEOS} ({'ok' if PP_VIDEOS.is_dir() else 'MISSING'})")
    print(f"log today     {log_path()} "
          f"({log_path().stat().st_size} bytes)" if log_path().exists()
          else f"log today     {log_path()} (not written yet)")
    print(f"would         {'NOT start — ' + problem if problem else ('do nothing' if pid else 'START the engine')}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true",
                    help="report and change nothing")
    a = ap.parse_args()
    sys.exit(status() if a.status else start())
