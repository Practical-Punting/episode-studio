# Overnight builds — keeping the Lenovo awake (C4)

**A build runs for about half an hour of real compute and can sit waiting far longer. The
machine has to still be there in the morning.** This file says exactly which half is the
engine's job and which half is a Windows setting **only Jodie can click** — because the
two have been confused before, and the confusion cost fourteen hours.

> ## 🔴 THE RULE THIS FILE EXISTS FOR
> **The engine can survive being killed. It cannot stop Windows killing it.**
> Everything in §1 is already built and proved. Everything in §2 is a setting on the
> machine, and no amount of code will substitute for it.

---

## §1 — WHAT THE ENGINE ALREADY DOES (built, tested, nothing to action)

**1. It refuses to start on a machine that will suspend it.**
`supervisor.standby_problem()` reads `powercfg` before every start and will not launch the
engine if the machine is set to sleep **or hibernate**. It checks **all four timers** —
mains and battery, for each of sleep and hibernate — and names which one is wrong, how
long it is set to, and the exact command to fix it. It retries every five minutes, so
**fixing the setting starts the engine by itself**; you never have to come back and press
anything.

> ⚠️ **Why all four.** 3 Aug 2026: Jodie set the power plan to never sleep, sincerely, and
> set the wrong half — Windows keeps **separate** timers for mains and battery, and EP14's
> fourteen lost hours happened on battery. **14 Aug 2026** the same lesson landed on the
> guard itself: it had only ever read `STANDBYIDLE`, so a machine set to never sleep could
> still **hibernate** out from under a build and the check read it as fine. *A person can
> do this correctly and still be wrong — and so can a guard.*

**2. It fails OPEN.** If `powercfg` is missing, silent or unreadable the check returns
nothing and the engine starts anyway, saying so in the log. A guard that cannot read its
input must never brick the studio.

**3. A frozen engine is restarted by itself.** `frozen_work()` spots a WORKING episode
whose heartbeat has gone quiet and restarts it. It deliberately ignores staleness at a
human gate, where the heartbeat is meant to be still — otherwise it would kill an engine
parked correctly, waiting on you.

**4. A deliberate stop is left alone.** `engine.stopped` (written by
`engine/stop_engine.py`) tells the supervisor a human stopped the engine ON PURPOSE, and
the healer keeps its hands off until `--release`.

**5. 🔒 A REBOOT CANNOT WALK A HUMAN GATE THROUGH.** This is the one that matters most
overnight. A gate records the **asking** and the **answering** as two separate files, so
an engine killed between the two re-asks the question on resume rather than walking
through it. EP23 was killed by an overnight Windows update in exactly that gap and the
listen gate passed by accident; it cannot now. *(C3, `providers.ask_once` /
`answer_pending_gates`, proved in `engine/test_gate_answered.py`.)*

---

## §2 — WHAT JODIE HAS TO CLICK (the engine cannot do these)

**Do these once. They are not code and no future fix will replace them.**

### A. Never sleep, never hibernate — on BOTH power sources

The fastest and most reliable way is the four commands, in a terminal:

```
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-ac 0
powercfg /change hibernate-timeout-dc 0
```

*(`0` means never. `-ac` is plugged in, `-dc` is on battery.)*

Or by clicking, if you prefer to see it:
1. **Settings → System → Power & battery → Screen and sleep**
2. Set **"When plugged in, put my device to sleep after"** → **Never**
3. Set **"On battery power, put my device to sleep after"** → **Never**
4. **Control Panel → Power Options → Change plan settings → Change advanced power
   settings → Sleep → Hibernate after** → set **both** "On battery" and "Plugged in" to
   **Never**
5. In that same advanced panel, **Sleep → Allow hybrid sleep** → **Off**

✅ **How to know it worked:** the engine starts on its own within five minutes. If it does
not, the run log says which timer is still set and what to type.

### B. Stop Windows restarting the machine mid-build

**This is what killed EP23's engine overnight.**

### ✅ ACTIVE HOURS — DONE 14 Aug 2026, and the previous setting was the trap

**Set and verified: `ActiveHoursStart=18`, `ActiveHoursEnd=12`,
`SmartActiveHoursState=0` (Manual).** 18:00 → 12:00 is 18 hours, the maximum Windows
allows, and it **covers the overnight build window**.

> 🔴 **WHAT WAS THERE BEFORE READ AS FINE AND WAS EXACTLY WRONG.** Active hours were
> already `07:00 → 01:00` — also a full 18 hours, also looking thoroughly set — and the
> gap it left was **01:00 to 07:00**. That is precisely when an unattended overnight
> build runs, and when EP23's engine was killed by a Windows update. *A wide range is not
> the same as the RIGHT range, and only the gap matters.*

That leaves noon → 6pm as the restart window: hours she is normally at the machine and
not part-way through an overnight build.

### 🔒 STILL TO DO — needs an ADMINISTRATOR terminal

`NoAutoRebootWithLoggedOnUsers` lives under `HKLM\SOFTWARE\Policies\…`, which a normal
user cannot write. Run this in an **Administrator** PowerShell:

```powershell
New-Item -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' `
  -Name NoAutoRebootWithLoggedOnUsers -Value 1 -Type DWord
```

Verify it took:

```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' |
  Select-Object NoAutoRebootWithLoggedOnUsers
```

⚠️ **Active hours alone is not the whole guard.** It stops a restart *inside* the window;
this stops one while anybody is logged on. Both, or an update can still take the machine
at 12:30pm with a build running.

⚠️ **Active hours is a maximum of 18 hours**, so it cannot cover a whole day. Pick the
window that actually matters and accept a restart outside it — §1.5 means a restart can no
longer walk a gate through, so the cost is a delay rather than a wrong episode.

### C. Keep it plugged in

The battery timers are set to never above, but a laptop that runs out of power overnight
is a laptop that stopped. **Mains, every night there is a build.**

---

## §3 — WHAT IS STILL NOT COVERED, stated plainly

- **A forced Windows update restart is still possible** (Microsoft can push one outside
  the settings above). The engine survives it — the supervisor restarts, the episode
  resumes, and any unanswered human gate asks again — but the build is **delayed**, not
  protected.
- **The supervisor does not check the Windows Update settings.** §2B is unverified by
  code, unlike §2A which is checked before every start. If a restart ever costs an
  episode again, *checking active hours the way `standby_problem` checks powercfg* is the
  obvious next step, and it is not built.
- **A closed lid may still suspend the machine** depending on the lid-close action.
  Not read by any guard. **Control Panel → Power Options → Choose what closing the lid
  does → "Do nothing"** while a build runs, if you close it.
