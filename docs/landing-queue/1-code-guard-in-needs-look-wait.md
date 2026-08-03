# 1 — the stale-code guard must fire while an episode is FLAGGED

**E11 part 1. `engine.py`. NOT LANDED.**

## The fault

`_code_changed()` has ONE call site — the top of the outer acquire loop:

```python
while True:
    changed = _code_changed()          # engine.py:941 — the ONLY check
    if changed:
        log(...); return
    ...
    ep = acquire()
    ...
    while True:                        # THE INNER LOOP — never returns to the above
        status = ctx.refresh().get("status")
        if ctx.ep.get("needs_look"):
            hb.active.set()
            log("episode is flagged 'needs a look' — waiting (heartbeat live)")
            poll = 3 if mock else 15
            while ctx.refresh().get("needs_look"):
                ...                    # ← a fix can land here and NEVER be picked up
```

Once an episode is claimed the engine cannot reach the guard until the episode is
released. **A flagged episode can sit here for hours on stale code**, which is exactly
what EP15 did on 3 Aug: fix at 09:10, process still broken at 10:03, recovery by manual
restart at 10:08.

> **It only works when the engine is IDLE, and the one state where a stale-code exit is
> both safe and necessary — parked on a flag with nothing in flight — is precisely the
> state it cannot reach.**

## The change

In the `needs_look` wait loop, check the guard each pass and exit if code has changed.
**A flagged episode is the safest possible moment to exit**: no ffmpeg, no HeyGen call,
no Higgsfield job in flight, and the supervisor restarts within five minutes.

```python
            while ctx.refresh().get("needs_look"):
                # A FLAGGED EPISODE IS THE SAFEST MOMENT THERE IS TO EXIT: nothing is
                # in flight. It is also where the engine spends the most time when
                # something is wrong — so it is precisely where stale code has to be
                # caught. The outer-loop check cannot reach here (E11, 3 Aug 2026):
                # a fix landed at 09:10 and the process ran the broken code until a
                # manual restart at 10:08.
                changed = _code_changed()
                if changed:
                    log(f"{changed} changed on disk while this episode was flagged — "
                        "exiting so fresh code loads (the supervisor restarts me; "
                        "nothing is in flight, nothing is lost)")
                    hb.active.clear()
                    rail.release(ctx.id, WORKER)
                    return
                if hb.lost.is_set():
                    raise OwnershipLost()
                time.sleep(poll)
```

**`rail.release()` matters**: exiting while still holding the lease would leave the
episode claimed by a dead worker until the lease expires.

## What it does NOT fix

The board still cannot say *"this engine is running code older than the repo"* — that is
**E11 part 2**, and it is the half Hugh actually needs, because for him this state is
undiagnosable. Part 1 makes recovery automatic; part 2 makes the state visible.

## Proof required after landing

Not "the code reads correctly" — **demonstrate it**: flag an episode, touch `engine.py`,
and watch the engine EXIT and the supervisor bring it back. That behaviour has never
once been observed.
