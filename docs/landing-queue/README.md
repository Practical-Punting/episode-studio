# THE LANDING QUEUE — ✅ EMPTY. Both changes LANDED 4 Aug 2026.

**Kept as the record of what was held, why, and what actually happened when it landed.
Do not delete: the queue's value is the discipline, and the discipline needs its
worked example.**

> ## ✅ LANDED — one controlled restart, one proof pass, 4 Aug 2026 ~21:30
> New process confirmed **from the log**: `engine up — worker=pp-engine@Jodie-Lenovo
> pid=44536 provider=real watch=True`.

**Why the queue exists.** `CLAUDE.md` used to say the stale-code guard exits the engine
and the supervisor restarts it, and that this "IS the deploy path". **It is not.**
`_code_changed()` was checked only at the top of the OUTER acquire loop, so a claimed
episode never reached it. On 3 Aug a fix landed at 09:10, the running process kept the
broken code in memory, and clearing the flag walked straight back into the same bug.
**An hour of EP15, and a recovery that needed a terminal Hugh does not have.**

## What landed

| # | Change | File | Fixes |
|---|---|---|---|
| 1 | `_code_changed_exit()` in **BOTH** `needs_look` waits | `engine.py` | **E11 part 1** |
| 2 | key `hero-jobs.json` on slot + hash of the PROMPT | `providers.py` | **E16** (code half) |

### ⚠️ TWO CORRECTIONS THE WRITTEN PATCH NEEDED, FOUND ONLY BY BUILDING IT

**1. There are TWO `needs_look` wait loops, and the patch covered the wrong one.**
The written version patched the outer acquire loop's wait — the one entered when an
episode is *already* flagged on pickup. **EP15 was held in the other one:**
`flag_and_wait`, entered when a step raises. That is where the engine sat for an hour.
Both are patched now, and `test_landing_block.py::test_BOTH_wait_loops_check_it` asserts
it stays that way.

**2. It must RAISE, not return a flag.** The two call sites want opposite things from a
bare `return`: in the acquire loop it ends the run, but in `flag_and_wait` it means
*"the flag cleared, retry the step"* — **on exactly the stale code we are escaping.**
One behaviour, decided in `_code_changed_exit`, so no call site can get it subtly wrong.

## The proof pass, as actually run

1. ✅ `test_step_call_sites.py` — 5/5. **It caught a real fault**: the E26 pre-flight
   needed `ctx.mock` and the dispatch stub did not have it. An `AttributeError` on the
   first real execution — EP15's NameError in a new costume, caught before an episode.
2. ✅ **13/13 suites.** The cases that cover these changes are named in
   `test_landing_block.py` (23) and `test_preflight_episode_json.py` (16), not quoted
   as a total.
3. ✅ Restart read out of the log, `pid 13420 → 44536`.
4. ✅ **E11 DEMONSTRATED — the first time this behaviour has ever been observed.**
   A mock ticket flagged at `script_sync`; the engine parked in `flag_and_wait`;
   `engine.py`'s mtime was touched (content unchanged); **eight seconds later** the log
   read *"engine.py changed on disk while this episode was flagged — exiting so fresh
   code loads"*, and the supervisor brought it back on the new code.
5. ⏳ **E16 NOT demonstrated with the balance, and it is not claimed as proved.**
   Both directions need two real Higgsfield generations, which is a spend on a decision
   nobody has asked for. The mechanism is unit-tested — same prompt → same key, changed
   prompt → different key — but **the witness for a spending guard is the balance
   moving, and it has not been watched.** It gets watched on EP16's covers.

## Still open from these two

- **E11 part 2 — the board cannot say "this engine is running code older than the repo."**
  Part 1 makes recovery automatic; part 2 makes the state VISIBLE, and it is the half
  Hugh needs, because for him that state is undiagnosable.
- **E16's board half** — the board must never re-offer a REJECTED artefact, and must say
  so on the card. Deferred on purpose: the prompt hash fixes the mechanism that failed;
  the label matters the day somebody who is not Jodie is looking at that card.
