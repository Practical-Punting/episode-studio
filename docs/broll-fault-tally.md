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

**2. DO NOT POOL CLIPS WITH COVERS AND CARD IMAGES.** *(F7's resolution on 18 Aug made this sharper: **THREE** of the seven recorded faults — F5, F6 and F7 — were covers or card images caught at a pick and never shipped. Pooling them would both overstate the clip rate and hide that the picks are working.)* They have different detectors. A
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
| EP26 | 5 | 0 | — | — *(F7, the kinked rail, was the rejected COVER HERO — a still, caught at the pick. It is in the not-b-roll table below.)* | 2026-08-15 |
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
| F7 | EP26 | **cover hero**, the white rail had an abrupt kink | ✅ **RESOLVED 18 Aug 2026 by Jodie, who found it: it was the COVER HERO** — the rejected round-1 hero B (*"a full field of racehorses seen head-on"*). **Caught at the pick and never shipped**, and round 1 was regenerated entirely. NOT a b-roll clip and NOT in the rate. |

## 🟠 OPEN, UNRESOLVED AND UNCOUNTED — EP31's RED ARTEFACT (19 Aug 2026)

**Jodie, on EP31's new Peter render:** *"on the right hand side of the screen there is a
red thing that waves over the background. It is something wrong with the background."*

**A full-video scan found nothing there.** 58 frames sampled across all 580 seconds, plus
75 CONSECUTIVE frames at full rate, plus magnified crops of the far-right strip: the
right-hand region measures **static** (temporal σ ≈ 1.0 against a 4.2 frame average) and
carries no strongly-red pixels that are not Peter himself.

⚠️ **AND THE FIRST INSTRUMENT WAS WRONG, WHICH IS WHY THIS ROW SAYS "UNRESOLVED" AND NOT
"ABSENT".** A red-pixel detector fired on his **face, neck and hands** and produced
confident-looking counts; painting the mask and LOOKING is what caught it. Same family as
F7 — an unverified sighting is not a fault, and **"we looked and could not find it" is not
"it is not there."**

🔴 **IT IS PARKED, NOT DROPPED, AND NOT IN ANY RATE.** If it is real it is a **PRESENTER**
problem, not an EP31 problem: Peter's background is baked into his base look, so it would
be in all ~270 remaining episodes. **The deciding question, when it is picked up: is the
red thing visible in the BASE LOOK STILL?** If yes it is baked in and the fix is to edit
the base look (the tool that fixed his resting smile); if it appears only in motion, the
base look is fine and HeyGen's animation is inventing it. Those are different problems.
**What would settle it fastest is a timestamp.**
📌 A NEW PRESENTER IS A NEW GENERATOR WITH NEW FAILURE MODES. This is the first reported
one, and it belongs in the same family as F5, F6 and F7 — a generative artefact in an
image nobody checked before it shipped.

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
