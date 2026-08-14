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

1. **Settings → Windows Update → Advanced options → Active hours**
2. Change **"Adjust active hours"** from *Automatically* to **Manually**
3. Set the range to **cover the hours you build overnight** (Windows will not
   auto-restart inside active hours)
4. On the same page, turn **OFF** *"Restart this device as soon as possible when a restart
   is required to install an update"*
5. Turn **ON** *"Notify me when a restart is required to finish updating"* — so a pending
   restart is something you choose, at a moment you pick

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
