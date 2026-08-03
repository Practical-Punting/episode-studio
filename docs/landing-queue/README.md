# THE LANDING QUEUE — written, proven-by-reading, NOT LANDED

**Changes that are ready but touch the three frozen files (`engine.py`, `providers.py`,
`rail.py`) while an episode is running.**

> ## ⚠️ LAND THESE TOGETHER. ONE CONTROLLED RESTART. ONE PROOF PASS.
> **And confirm the new process FROM THE LOG** (`engine up — … pid=`), never from
> having issued a restart.

**Why a queue exists at all.** `CLAUDE.md` used to say the stale-code guard exits the
engine and the supervisor restarts it, and that this "IS the deploy path". **It is not.**
`_code_changed()` is checked only at the top of the OUTER acquire loop, so a claimed
episode never reaches it. On 3 Aug a fix landed at 09:10, the running process kept the
broken code in memory, and clearing the flag walked straight back into the same bug.
**An hour of EP15, and a recovery that needed a terminal Hugh does not have.**

So: frozen-file changes are written when they are understood, and landed when nothing is
running. Landing mid-episode is the exact pattern that cost the hour.

## In the queue

| # | Change | File | Fixes |
|---|---|---|---|
| 1 | `_code_changed()` inside the `needs_look` wait | `engine.py` | **E11 part 1** |
| 2 | key `hero-jobs.json` on a hash of the PROMPT | `providers.py` | **E16** |

**Land when:** EP15 is published and no episode is claimed.

**Proof pass, after landing:**
1. `python engine/test_step_call_sites.py` — no unbound globals, dispatch reaches its calls.
2. Full suite — every suite green, and **name the case that covers each change**
   (fault #4: a green total is not evidence about the thing you changed).
3. Restart, and read `engine up — … pid=` **out of the log**.
4. For #1: with an episode flagged, touch `engine.py` and watch the engine EXIT —
   that is the behaviour being bought, and it has never once been demonstrated.
5. For #2: change a hero prompt on a test episode and confirm a NEW job id is created;
   leave it unchanged and confirm the old id is reused. **The balance is the witness.**
