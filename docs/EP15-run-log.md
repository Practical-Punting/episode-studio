# EP15 — run log · IN-FLIGHT HANDOVER

**Written 4 August 2026, ~19:50 local, mid-build.** *Everything a fresh session needs to
finish this episode. Not a history of the build — the rulings are in `CLAUDE.md`, the
findings in the session checkpoint.*

---

## 1. WHERE EP15 IS

**Rebuilding `assemble_passB`.** Card **C10** was rebuilt tonight from **four cells to
three** — four was illegible once the panel-push composite scaled the card to 810 wide
(42%), which no check caught because `card_check` and `self_qc` both measure the page at
1920. Every other card is fine.

**Sequence still to run:**
1. `assemble_passB` → a new `output/PP-EP15-FINAL.mp4`
2. `self_qc` **against that new file**
3. three stills, looked at first, then hand to Jodie

### THE PROOF TEST — four conditions, all required
A rebuilt FINAL is only accepted when **all four** hold. *Version 1 of this test accepted
the file at **0 bytes** — ffmpeg had created it and not yet written to it, and 0 == 0 ten
seconds later looked settled.*

| # | condition |
|---|---|
| 1 | mtime **later than `overlay/clips/ep15-c10-count-the-boards.mp4` (19:06:21)** |
| 2 | size **≥ 100 MB** |
| 3 | size **unchanged across two 20s samples** |
| 4 | `ffprobe` duration **within 5s of 817s** |

**And watch the PRODUCER, not only the file** — if `claimed_by` is null while the status
is in `WORKING`, nothing will ever write it (see §5).

---

## 2. THE STILLS, AND THE RULE THAT MATTERS MOST

**Three stills: the title card · a PANEL-PUSH card at composited size · the end card.**

> ## 🔴 LOOK AT THEM YOURSELF BEFORE SENDING THEM.
> **This caught three separate faults on 4 August**, each of which had passed every
> automated check:
> 1. the title card rendering onto **flat black** (its hero had been quarantined and
>    never re-staged)
> 2. C10's panel-push card **illegible** at composited scale — `card_check` 17/17 and
>    `self_qc` both green
> 3. the FINAL being **34 minutes older** than the clip it was supposed to contain
>
> **It is the single most valuable thing to carry forward.** A panel-push still must be
> taken from the FINAL, never from the 1920 page — the page always looks right.

---

## 3. WHAT JODIE MUST BE TOLD BEFORE SHE PRESSES PLAY

- **The framing.** EP15 runs **14 WIDE of 24 beats**, against EP14's 8 of 25 — **the
  widest episode she has made.** Watch whether it feels flat.
  **And the thing that may stop it feeling flat:** the extra WIDE beats are the
  **panel-push** beats, where Gordon steps aside and a card teaches beside him. **Those
  are the busiest shots in the episode, not the emptiest.**
- **C10's content was rebuilt tonight**, so six seconds of the episode are new since
  anything she has seen.
- **Keep an ear open at about 6:20.** QC asks for a human listen on the midroll,
  **379–404s**, saved as `output/qc/midroll-listen.wav`, confirming the voice stays
  Gordon. Better done while watching than as a separate chore.

---

## 4. TWO THINGS FROM JODIE TONIGHT THAT EXIST NOWHERE ELSE

### (a) ⚠️ THE FRAMING RULING IS **NOT** SETTLED
**She watched only up to the midroll — about 6:20 of 13:30.** Her *"the rest looked
good"* covers **the first half only**. Cowork recorded that as a verdict and she
corrected it.

> **DO NOT record a framing ruling until she has watched the finished cut end to end.**

When she does, whatever she says becomes a **written line in the visual standard with its
reason** — the way the layout mix already is. Not a number reverse-engineered from EP14.
*The MCU/WIDE ratio is currently the fourth convention doing real work while existing only
as a feel.*

### (b) A STANDING PREFERENCE — future episodes, not this one
> **"I would be happy with more motion graphics, but am happy with where we are."**

EP15 runs **thirteen cards across thirteen and a half minutes.**

**Whether that means MORE CARDS or MORE MOVEMENT WITHIN THEM is a deliberate decision,
not a drift.** And it **interacts with the framing**: more cards means more panel-push
beats, which means more WIDE beats — the two questions are one question.

---

## 5. THE TRAP THAT COST AN HOUR TONIGHT — read before touching the rail

**An episode in a WORKING status with `claimed_by: NULL` is invisible to the engine.**
There are exactly two ways back in:

```
claim_next()    → status=eq.queued
reclaim_stale() → claimed_by=not.is.null AND lease_until in the past
```

**A working status with no owner matches neither.** EP15 sat there for 48 minutes with
the engine alive (pid 76064) and silent.

**RECOVERY — use the engine's own crash path, invent nothing:** set `claimed_by` to a
name that is not the live worker and `lease_until` to the past. That is what the episode
factually is — one whose worker went away mid-assembly — and `reclaim_stale()` takes it
back within a minute.

**AND NEVER WRITE TO THE RAIL WHILE A LEASE IS LIVE.** An earlier reset was silently
overwritten by the running engine's own `ctx.save()`; the read-back showed the change had
landed and it had not. **Check `claimed_by` and `lease_until` first, and prove the effect
with a new output file — never with a status field.**
