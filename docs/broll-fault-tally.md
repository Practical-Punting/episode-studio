# B-ROLL FAULT TALLY

**Seeded 18 Aug 2026 from Jodie's fault file (kept since 5 Aug), not from scratch.**
Written and read by `engine/broll_fault.py`; hand-editing is fine, the format is the point.

    python engine/broll_fault.py 31 --clean
    python engine/broll_fault.py 31 --faulty c02 --why "horses both sides of the rail"
    python engine/broll_fault.py --rate

## 🔴 THREE THINGS TO READ BEFORE QUOTING ANY NUMBER FROM THIS FILE

**1. THE RATE IS A LOWER BOUND, AND EP23 IS THE PROOF.** The denominator is episodes a
human has been through at the four approvals — which is good evidence the episode was
**watched**, and is NOT evidence the b-roll was **scrutinised**. EP23 was approved 4/4,
**published on 13 Aug, and Hugh found horses on both sides of its running rail on 14 Aug
— the day after.** So a fault-free row means "nothing was noticed", never "nothing was
there". Every number below is the floor, not the figure.

**2. DO NOT POOL CLIPS WITH COVERS AND CARD IMAGES.** They have different detectors. A
bad cover meets the cover-pick step and never ships; a bad card image is discarded at the
pick. **A bad b-roll clip has nothing between it and the finished video.** Pooling would
overstate the b-roll rate *and* hide that two of the seven recorded faults were caught by
design, working exactly as intended. The non-clip faults are listed separately below and
are **excluded** from the rate.

**3. EP6–EP15 ARE NOT COVERED.** The fault file opens at EP16. Those ten episodes are
**unknown, not clean**, and they are not in the denominator.

## The tally — b-roll CLIPS only

| episode | clips | faulty | which | what was wrong | reviewed |
|---|---|---|---|---|---|
| EP16 | 7 | 2 | @1:25, @8:11 | the field galloping in perfect unison, hooves landing together (F1); riders not in Australian attire AND standing still in a motion clip (F2) | 2026-08-05 |
| EP17 | 7 | 0 | — | — | 2026-08-05 |
| EP18 | 7 | 1 | crowd clip | all hats white in some scenes (F3) | 2026-08-08 |
| EP19 | 7 | 0 | — | — | 2026-08-08 |
| EP20 | 7 | 0 | — | — | 2026-08-11 |
| EP21 | 6 | 0 | — | — | 2026-08-13 |
| EP22 | 6 | 0 | — | — | 2026-08-13 |
| EP23 | 6 | 1 | — | horses running on BOTH sides of the running rail (F4) — ⚠️ found by Hugh 14 Aug, the day AFTER it published with 4/4 approval | 2026-08-14 |
| EP24 | 6 | 0 | — | — | 2026-08-14 |
| EP25 | 6 | 0 | — | — | 2026-08-14 |
| EP26 | 5 | 0 | — | ⚠️ SEE F7 BELOW — the rail kink may belong here; nobody has established whether it was a clip or a still, so it is NOT counted | 2026-08-15 |
| EP27 | 5 | 0 | — | — | 2026-08-16 |
| EP28 | 4 | 0 | — | — | 2026-08-17 |
| EP29 | 5 | 0 | — | — | 2026-08-17 |
| EP30 | 4 | 1 | c01 | ONE clip carrying TWO faults: horses both sides of the rail AND the field in identical stride | 2026-08-17 |

### 🔴 EP30 IS F4 AND F1 RECURRING
Not new faults — the **second appearance** of two we had already written rules for, and
both rules were in the sent prompt, in positive form, on all four clips. That is what
makes "the rules hold probabilistically" the right reading, and it is why no rewording
gets this to 100%.

## Not b-roll — recorded, deliberately NOT in the rate

| # | episode | what | outcome |
|---|---|---|---|
| F5 | EP24 | **cover B upside down** | ✅ **caught by the cover-pick step — never shipped** |
| F6 | EP26 | **card image**, man at a desk, too dark | ✅ **discarded at the pick — never shipped** |
| F7 | EP26 | the white rail had an abrupt kink | ⚠️ **UNKNOWN whether clip or still.** The record points to a clip — `broll-the-field-sweeping-to-the-line.mp4` is EP26's only asset with a running rail, since its cover hero is a man at a desk with framed photographs. **Not visually confirmed, so not counted.** Counting it moves the rate from 5/88 to 6/88. |

## 🔴 THE ANSWER IS SETTLED — DO NOT RE-PROPOSE A REVIEW STEP

Jodie, **5 Aug 2026**, verbatim:

> *"We do not want a step to approve the b-roll. We know that this will mean there is the
> odd bit of b-roll that is weird. But do not add another step to our process around this.
> We will just add a few more rules over time."*

Confirmed again **14 Aug**, on the EP23 rail fault:

> *"I do not want to have to approve each b-roll. Just make it awesome like Australian
> horse racing."*

At 300 episodes that is ~2,100 clips; ten seconds each is **seven hours** hunting a
handful of odd frames. **The occasional weird clip is cheaper than the process that would
catch it**, and **the answer to a bad clip is always a better prompt, never a human
looking.**

**Her ruling anticipated EP30** — *"we know this will mean the odd bit of b-roll that is
weird"* — so the recurrence is **not** new information that reopens it. This tally exists
to measure the rate, **not** to build a case for a review step. If a future session
proposes "generate two and keep one" or "inspect returned footage", this is the answer.
