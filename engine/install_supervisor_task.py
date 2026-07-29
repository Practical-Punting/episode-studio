#!/usr/bin/env python3
"""install_supervisor_task.py — register (or show, or remove) the Task Scheduler entry.

    python install_supervisor_task.py --install
    python install_supervisor_task.py --show
    python install_supervisor_task.py --remove

THE SHAPE, and why each part of it (Jodie's approval, 29 July 2026):

  · TWO TRIGGERS: at logon, and a daily one from midnight **repeating every 5
    minutes, indefinitely**.
  · Runs `supervisor.py`, which runs `engine.py run --watch`.

⚠️ **THE REPETITION IS ON THE DAILY TRIGGER, NOT THE LOGON ONE, AND THAT MATTERS.**
Attached to the logon trigger it registered fine, reported `Next Run Time: N/A`, and
**would not have ticked once until the next logon** — a repetition only runs while
its own trigger's window is open, and the logon that mattered had already happened
before the task existed. **An installed task that never fires is precisely the hope
this is supposed to replace.** A daily trigger with a start boundary in the past is
active immediately and stays active, so the five-minute tick is live from the moment
it is registered. The logon trigger is kept for the cold start.
  · **IgnoreNew**: while an instance is running the 5-minute tick does nothing. The
    supervisor holds the task instance for as long as the engine lives, so the
    repetition is a no-op during normal operation and a restart within five minutes
    of any exit — a crash and the deliberate stale-code exit alike.
  · **The engine's own lock is the second guard**, not the first. Belt and braces:
    if a tick ever did overlap, `_acquire_lock()` refuses to start a second engine.

⚠️ WHY LOGON AND NOT "AT STARTUP", WHICH IS WHAT WAS ASKED FOR. The task runs **in
Jodie's interactive session** (LogonType InteractiveToken) because **G: is Google
Drive and only exists inside her session** — a task running as SYSTEM would find no
`G:\\My Drive\\PP Videos`, no `.env` and no episode folders at all. That has two
consequences, both stated rather than hidden:

  1. **A boot trigger could not fire before she logs in anyway**, so it would add
     nothing that the logon trigger does not already cover.
  2. **Registering a boot trigger requires administrator rights** — `schtasks`
     returned *Access is denied* — while a logon trigger in her own session does not.

So it is a LOGON trigger plus the 5-minute repetition, which between them cover a
cold start, a login, and every five minutes thereafter. **This is a deliberate
departure from the brief's wording and it loses nothing** — but it is a departure,
and if the machine is ever left running at the login screen with an episode
mid-flight, that is the gap.

⚠️ IT DOES NOT RUN AS ADMINISTRATOR (RunLevel LeastPrivilege). Nothing the engine
does needs it, and a supervisor with more power than the thing it supervises is a
liability, not a feature.
"""
import argparse
import getpass
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
SUPERVISOR = ENGINE_DIR / "supervisor.py"
TASK = "PP Episode Studio engine"

# The full path, never bare `python`: a bare `python` on this machine hits the
# Microsoft Store stub, which is not an interpreter and fails in a way that reads
# like a missing file.
PYTHON = Path(sys.executable)

XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Starts the Practical Punting episode engine and keeps it started.
Runs supervisor.py, which sets the working directory and PP_VIDEOS_DIR explicitly and
appends everything to engine/logs/engine-YYYY-MM-DD.log. It starts the engine and does
nothing else: it never renders, never publishes and never clears a flag.</Description>
    <URI>\\{task}</URI>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{user}</UserId>
    </LogonTrigger>
    <CalendarTrigger>
      <Enabled>true</Enabled>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Repetition>
        <Interval>PT5M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
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
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python}</Command>
      <Arguments>"{supervisor}"</Arguments>
      <WorkingDirectory>{cwd}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def whoami() -> str:
    r = subprocess.run(["whoami"], capture_output=True, text=True)
    return (r.stdout or "").strip() or f"{os.environ.get('USERDOMAIN')}\\{getpass.getuser()}"


def install():
    if not SUPERVISOR.is_file():
        raise SystemExit(f"no supervisor at {SUPERVISOR}")
    xml = XML.format(task=TASK, user=whoami(), python=PYTHON,
                     supervisor=SUPERVISOR, cwd=ENGINE_DIR)
    tmp = Path(tempfile.gettempdir()) / "pp-engine-task.xml"
    tmp.write_text(xml, encoding="utf-16")          # schtasks wants UTF-16
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK, "/XML", str(tmp), "/F"],
                       capture_output=True, text=True)
    print((r.stdout or "").strip() or (r.stderr or "").strip())
    if r.returncode:
        raise SystemExit(f"schtasks exited {r.returncode}")
    print(f"\ninstalled: {TASK}")
    print(f"  runs   {PYTHON} \"{SUPERVISOR}\"")
    print(f"  cwd    {ENGINE_DIR}")
    print(f"  log    {ENGINE_DIR / 'logs'}")
    return show()


def show():
    r = subprocess.run(["schtasks", "/Query", "/TN", TASK, "/V", "/FO", "LIST"],
                       capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    keep = ("TaskName", "Next Run Time", "Status", "Last Run Time", "Last Result",
            "Task To Run", "Start In", "Run As User", "Repeat: Every",
            "Schedule Type", "Scheduled Task State")
    for line in out.splitlines():
        if any(line.strip().startswith(k) for k in keep):
            print(line.rstrip())
    return r.returncode


def remove():
    r = subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"],
                       capture_output=True, text=True)
    print((r.stdout or "").strip() or (r.stderr or "").strip())
    return r.returncode


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--install", action="store_true")
    g.add_argument("--show", action="store_true")
    g.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    sys.exit(install() if a.install else remove() if a.remove else show())
