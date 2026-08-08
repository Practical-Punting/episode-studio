"""Stop the engine ON PURPOSE, so the supervisor's healer keeps its hands off.

    python engine/stop_engine.py "sending EP18 back a stage"     # stop + mark
    python engine/stop_engine.py --release                       # let it start again

WHY THIS EXISTS. A deliberate stop and a freeze look IDENTICAL from outside: both are
a pid that is not beating. The supervisor now restarts a frozen engine by itself
(`frozen_work`), which is right — and would be exactly wrong in the middle of a
deliberate hold. On 8 Aug 2026 the engine was stopped by hand to send EP18 back a
stage; the board showed "self_qc stuck 22 min" and a restart was asked for. Had the
healer existed that night it would have fought the rewind.

The marker is the one thing the machine cannot infer: INTENT. Whoever stops it says so.
"""
import ctypes
import pathlib
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENGINE_DIR = pathlib.Path(__file__).resolve().parent
MARKER = ENGINE_DIR / "engine.stopped"
LOCK = ENGINE_DIR / "engine.lock"


def alive(pid):
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259


def main(argv):
    if "--release" in argv:
        if MARKER.exists():
            was = MARKER.read_text(encoding="utf-8").strip()
            MARKER.unlink()
            print(f"released — the supervisor may start the engine again.\n"
                  f"  (it had been held for: {was})")
        else:
            print("no hold in place — nothing to release.")
        return 0

    reason = " ".join(a for a in argv if not a.startswith("--")).strip()
    if not reason:
        print("A reason is required — the marker exists to record INTENT, and a "
              "marker with no reason is just a freeze somebody wrote down.\n"
              '  python engine/stop_engine.py "why you are stopping it"')
        return 2

    MARKER.write_text(reason, encoding="utf-8")
    print(f"wrote {MARKER.name}: {reason}")

    try:
        pid = int(LOCK.read_text().strip())
    except Exception:                                              # noqa: BLE001
        print("no engine.lock — nothing running to stop. The hold is in place.")
        return 0
    if not alive(pid):
        print(f"pid {pid} is not running. The hold is in place.")
        return 0

    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
    for _ in range(20):
        if not alive(pid):
            break
        time.sleep(0.5)
    print(f"pid {pid} {'stopped' if not alive(pid) else 'is STILL RUNNING'}.")
    print("⚠️ The engine will NOT be restarted until you run --release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
