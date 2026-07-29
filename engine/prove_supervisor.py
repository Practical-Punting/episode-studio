#!/usr/bin/env python3
"""prove_supervisor.py — kill the engine and watch the scheduled task bring it back.

    python prove_supervisor.py

**An installed scheduled task that has never been observed to fire is a hope, not a
supervisor** (Jodie, 29 July 2026). This is the observation.

What it does, and it is deliberately blunt about it: it takes the running engine's
pid, KILLS it — the crash, simulated — and then polls until a DIFFERENT live pid
appears. It asserts the new pid is not the old one, so "it came back" cannot be
satisfied by the process that never died.

It changes nothing else. It does not clear a flag, touch an episode or write to the
rail. The engine it kills is the one the task started a moment earlier.
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import supervisor as sup                                            # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                               # noqa: BLE001
        pass

WAIT_S = 12 * 60          # the tick is every 5 minutes; this is generous
POLL_S = 10


def main():
    before = sup.engine_pid()
    if not before:
        print("NOTHING TO PROVE: no engine is running, so there is nothing to kill. "
              "Wait for the task's next tick to start one, then re-run this.")
        return 2

    print(f"engine running, pid {before}")
    print(f"log: {sup.log_path()}")
    sup.say(f"[PROOF] killing the engine (pid {before}) to prove the task restarts it")

    r = subprocess.run(["taskkill", "/PID", str(before), "/F"],
                       capture_output=True, text=True)
    print((r.stdout or r.stderr).strip())
    if r.returncode:
        print("could not kill it — nothing proved")
        return 2

    t0 = time.time()
    time.sleep(3)
    gone = sup.engine_pid()
    print(f"after the kill: engine_pid() -> {gone}")
    if gone:
        print("it did not die — nothing proved")
        return 2

    print(f"waiting up to {WAIT_S // 60} minutes for the task to bring it back…")
    while time.time() - t0 < WAIT_S:
        time.sleep(POLL_S)
        now = sup.engine_pid()
        if now and now != before:
            elapsed = time.time() - t0
            print(f"\nBACK BY ITSELF after {elapsed:.0f}s — new pid {now} "
                  f"(was {before}, and {now} != {before})")
            sup.say(f"[PROOF] engine is back on pid {now} after {elapsed:.0f}s, "
                    f"started by the scheduled task with no human involved")
            print("\n--- tail of the log ---")
            lines = sup.log_path().read_text(encoding="utf-8",
                                             errors="replace").splitlines()
            for ln in lines[-18:]:
                print(ln)
            return 0
        print(f"  {time.time() - t0:5.0f}s — still down")

    print(f"\nSTILL DOWN after {WAIT_S}s. The task did not restart it, and an "
          f"unproved supervisor must not be reported as working.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
