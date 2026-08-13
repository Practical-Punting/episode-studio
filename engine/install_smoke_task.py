#!/usr/bin/env python3
"""install_smoke_task.py — the nightly capture smoke test, as a Task Scheduler entry.

    python engine/install_smoke_task.py --install
    python engine/install_smoke_task.py --show
    python engine/install_smoke_task.py --remove

🔴 A TASK SCHEDULER ENTRY, NOT A CRON, AND THAT IS A RULING NOT A PREFERENCE.
CLAUDE.md, 26 July 2026: the last session-scoped cron **died silently and went stale for
three days without anyone noticing**. A schedule that only exists while some session is
alive is not a schedule. This is registered with Windows, survives logout and reboot, and
is inspectable with `--show` by anyone, for ever.

    A CHECK THAT RUNS ONLY WHEN SOMEBODY REMEMBERS IS THE THING BEING REPLACED.

WHAT IT RUNS. `smoke_capture.py`, which reads one real article from every section of the
site we have ever built an episode from and reports which SHAPES still parse. Capture has
broken on a new shape on episode after episode — EP20's byline-less profile, EP23's
layout markers — and every one was found during a live run, by Jodie, holding a queued
episode. This finds it at 03:30 instead.

⚠️ **03:30, AND `WakeToRun` IS FALSE ON PURPOSE.** The machine must be allowed to be
asleep; waking a laptop nightly to fetch seven articles is not worth the battery, and
`StartWhenAvailable` means a missed run happens at the next opportunity instead. The one
thing this must never do is become a reason the machine is awake at 3am.

🚫 IT WRITES NOTHING AND DECIDES NOTHING. `smoke_capture` runs with `write=False`, so it
cannot leave an article of record behind. Its whole output is a log file and an exit
code. It never touches the rail, never queues an episode and never clears a flag.

📄 WHERE THE ANSWER GOES: `engine/logs/smoke-YYYY-MM-DD.log`, same shape as the engine's
own dated logs, because a scheduled job whose failures are invisible is worse than none.
"""
from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
SMOKE = ENGINE_DIR / "smoke_capture.py"
RUNNER = ENGINE_DIR / "run_smoke.cmd"
TASK = "PP Episode Studio capture smoke test"
PYTHON = Path(sys.executable)

# A tiny .cmd so the dated log file is named by the SHELL at run time. Putting a
# redirect in the task's Arguments does not work — Task Scheduler execs the binary
# directly, so `>` is passed to python as an argument rather than interpreted.
RUNNER_BODY = """@echo off
rem Written by install_smoke_task.py. The nightly capture smoke test.
rem ONE LINE ON PURPOSE. The dated log is opened by smoke_capture.py itself (--log-dir),
rem because %DATE% is locale-dependent and the cmd quoting needed to work around it
rem broke the scheduled task outright (LastTaskResult 255, no log at all).
setlocal
set "PYTHONIOENCODING=utf-8"
set "PP_VIDEOS_DIR=G:\My Drive\PP Videos"
"{python}" "{smoke}" --log-dir "{logs}"
"""

XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Nightly capture smoke test for the Practical Punting studio. Reads one
real article from every site section an episode has been built from and reports which
article SHAPES still parse. Writes nothing, decides nothing, never touches the rail —
its whole output is engine/logs/smoke-YYYY-MM-DD.log and an exit code.</Description>
    <URI>\\{task}</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <Enabled>true</Enabled>
      <StartBoundary>2026-01-01T03:30:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{runner}</Command>
      <WorkingDirectory>{cwd}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def whoami() -> str:
    r = subprocess.run(["whoami"], capture_output=True, text=True)
    return (r.stdout or "").strip() or f"{os.environ.get('USERDOMAIN')}\\{getpass.getuser()}"


def install() -> int:
    if not SMOKE.is_file():
        raise SystemExit(f"no smoke test at {SMOKE}")
    logs = ENGINE_DIR / "logs"
    RUNNER.write_text(RUNNER_BODY.format(python=PYTHON, smoke=SMOKE, logs=logs),
                      encoding="utf-8")
    xml = XML.format(task=TASK, user=whoami(), runner=RUNNER, cwd=ENGINE_DIR)
    tmp = Path(tempfile.gettempdir()) / "pp-smoke-task.xml"
    tmp.write_text(xml, encoding="utf-16")          # schtasks wants UTF-16
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK, "/XML", str(tmp), "/F"],
                       capture_output=True, text=True)
    print((r.stdout or "").strip() or (r.stderr or "").strip())
    if r.returncode:
        raise SystemExit(f"schtasks exited {r.returncode}")
    print(f"\nregistered  {TASK}")
    print(f"  runs      {RUNNER.name} -> smoke_capture.py, daily at 03:30")
    print(f"  log       {logs / 'smoke-YYYY-MM-DD.log'}")
    print("  wakes the machine: NO. A missed run happens at the next opportunity.")
    print("\nTry it now without waiting for 03:30:")
    print(f'  schtasks /Run /TN "{TASK}"')
    return 0


def show() -> int:
    r = subprocess.run(["schtasks", "/Query", "/TN", TASK, "/V", "/FO", "LIST"],
                       capture_output=True, text=True)
    out = (r.stdout or "").strip()
    if r.returncode or not out:
        print(f"{TASK}: NOT REGISTERED — run --install")
        return 1
    for line in out.splitlines():
        if any(k in line for k in ("TaskName", "Status", "Next Run Time", "Last Run Time",
                                   "Last Result", "Task To Run", "Schedule Type")):
            print("  " + line.strip())
    return 0


def remove() -> int:
    r = subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"],
                       capture_output=True, text=True)
    print((r.stdout or "").strip() or (r.stderr or "").strip())
    RUNNER.unlink(missing_ok=True)
    return r.returncode


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--install", action="store_true")
    g.add_argument("--show", action="store_true")
    g.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    sys.exit(install() if a.install else show() if a.show else remove())
