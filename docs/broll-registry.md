# B-roll registry — every clip we've ever used

**Why this exists:** so no b-roll is ever repeated from an earlier episode, and
none is repeated within an episode (Jodie's EP03 feedback, 2026-07-21).
**Rule:** before generating b-roll for a new episode, read this file. Every new
clip's subject must NOT already appear below. After an episode ships, add its
clips here (episode, file, one-line subject). Turf-only, relevant-to-the-line,
crowd diversity still all apply.

## 🔴 CHECK THE RUNNING RAIL ON EVERY CLIP (Jodie, 28 July 2026)

**NEVER a horse on the wrong side of the running rail, and NEVER runners on both sides of
it.** The rail divides the track; runners are only ever on one side. A clip that breaks this
is **racing-WRONG** and is rejected and regenerated, exactly like a riderless horse.
Full rule: `PP-STANDARDS.md` §B-roll & all generated imagery — HARD-FAIL list.

**Why it is in this file and not only in the standards:** it was found on a COVER HERO
(EP13's `hero-b.png`), but **the same generator makes the b-roll clips**, so the same fault
can appear in any of them — and a moving clip is *harder* to spot it in than a still, because
you see each frame for a fraction of a second.

**⚠️ AND IT IS A DIFFERENT KIND OF DEFECT FROM EVERYTHING ELSE ON THE HARD-FAIL LIST.** The
others — riderless horses, fused limbs, an object through a body — are things that are broken
*in the frame*. This one is a picture that is **geometrically and anatomically perfect and
still shows something that cannot happen on a racecourse.** No automated check can see it.
**Only a human who knows racing can.**

**So when you glance the 6-up `broll-contact.png` at the render gate, look for the rail** —
where it runs, and whether every runner is on the same side of it. That glance is the only
thing standing between this fault and a shipped episode. Prompt wording helps and is worth
writing ("the field on the inside of the running rail"), but the generator is not obliged to
obey it, so the wording is not the control — **the look is.**

## 🔒 THERE IS NO B-ROLL REVIEW STEP, AND THERE NEVER WILL BE (Jodie, 5 August 2026)

> ### "We do not want a step to approve the b-roll. We know that this will mean there is
> ### the odd bit of b-roll that is weird. But do not add another step to our process
> ### around this. We will just add a few more rules over time."

**She has KNOWINGLY ACCEPTED the occasional odd clip as cheaper than the process that
would catch it.** That is a trade she has made with the facts in front of her, not an
oversight to be helpfully corrected.

🚫 **DO NOT PROPOSE — now or later — a b-roll approval gate, a review step, a preview card,
a contact-sheet sign-off, or a "just one look before it renders".** They have all been
considered and declined.

> ## THE ONLY ROUTE IS THE PROMPTS. **A fault found in a clip becomes a RULE HERE, not a
> ## checkpoint in the pipeline.**

*(The 6-up `broll-contact.png` still exists and is still worth a glance at the render gate
— but glancing is not a step, and nothing waits on it.)*

---

## 🐎 THE STANDING SHOT TEMPLATE — three things EVERY prompt must state
**(Jodie and Hugh, 5 August 2026, from two faults in EP16's finished film.)**

> ### ⚠️ PHRASE EVERY ONE OF THESE POSITIVELY. **Negations are unreliable in these models**
> ### — "not synchronised" invites synchronised. Describe the thing you want to SEE.

### 1. HORSES OUT OF STEP WITH ONE ANOTHER
**Say it, every clip with more than one horse in motion:**
> *"each horse at a different point of its stride, staggered strides, hooves landing at
> different moments, legs out of phase across the field"*

**EP16 at 1:25 (`broll-nine-runners-turn`):** a rear view of the field with **every horse
in identical rhythm, hooves landing together.** Jodie: *"they land and run at slightly
different times."*
**THE GAP BETWEEN THE PROMPT AND THE CLIP, which is the useful part:** the prompt asked for
*"a closely bunched field … no horse clearly in front"* — it specified uniformity of
**POSITION**, and the model delivered uniformity of **GAIT** as well. Nothing in it said a
word about legs. *It did what it was told; it was told the wrong thing.*

### 2. AUSTRALIAN RACING ATTIRE, ON EVERY RIDER, EVERY TIME
**Say it, every clip containing a mounted rider — not only the racing ones:**
> *"jockeys in bright Australian racing silks and matching caps, white or cream breeches,
> black riding boots, safety helmets with the silk cover on"*

**EP16 at 8:11 (`broll-provincial-meeting-small-field`):** riders in **tweed jackets, flat
caps, waistcoats and cream jumpers** — English point-to-point clothing, on an Australian
provincial race day. Jodie: *"very strange."*
**THE GAP:** the prompt said *"a modest field of mounted racehorses"* and then described the
**CROWD'S** clothes in detail — *"present-day dress, about half in hats including Akubras"*
— **and never once described the RIDERS.** The model dressed the only people it had been
told about and improvised the rest.
⚠️ **"MOUNTED" IS NOT A COSTUME INSTRUCTION.** Two of EP16's three horse clips named silks;
the one that did not is the one that went wrong.

### 3. STATE THE MOTION EXPLICITLY — what moves, and how
**Every clip is a MOTION clip. A motion clip whose subjects are static is a FAULT.**
> *"the horses are galloping / walking forward / the boards are changing / the crowd is
> moving through frame"* — a verb, attached to the SUBJECT, in every prompt.

**EP16's `broll-provincial-meeting-small-field` was the only one of seven prompts with no
motion verb of any kind**, and it is the only one that came back static. **That is not a
coincidence and the audit proves it:**

| clip | motion words in the prompt |
|---|---|
| eachway-sign-ring | passing |
| nine-runners-turn | rounding, motion blur |
| oncourse-punter-boards | moving |
| shopping-the-ring | moving, tracking, walking |
| bookmaker-board-shorter | changing, mid-transition, reaching |
| **provincial-meeting-small-field** | **NONE** |
| placegetters-past-post | driving, motion blur |

⚠️ **AND "motion blur on the background" IS NOT A MOTION INSTRUCTION FOR THE SUBJECT** —
`nine-runners-turn` had it and still produced a field moving as one body. **Blur describes
the camera; a verb describes the horse.**

### 4. HATS ARE A VARIETY OF NATURAL COLOURS — name the range, every crowd clip
**(Jodie, 8 Aug 2026, from EP18 as shipped. Now a fourth standing item because it HAS gone
wrong, which is the bar this file uses.)**

**Say it, every clip containing a crowd:**
> *"Akubra-style hats in a VARIETY of natural colours — fawn, sand, tan, brown, grey, black,
> olive — worn at different angles, no two neighbours alike"*

**EP18 `broll-country-course-gums-and-rail`:** sixteen people along the rail, in sharp focus,
**and every single hat the same pale cream.** The crowd IS the subject of that shot.

> ## ⚖️ THE REASON, AND IT IS THE GENERAL ONE: **A MODEL FILLS A CROWD BY REPEATING ONE THING.**
> Asked for "hats", it does not sample a wardrobe — it picks a hat and clones it across every
> head. **Uniformity is the model's DEFAULT, not an accident**, so variety has to be demanded
> in words or it will not appear. The same reasoning covers shirts, caps and umbrellas the day
> one of them fills a frame.

⚠️ **STATE IT POSITIVELY — name the colours you want.** *"Not all white"* leaves the model to
choose the replacement and it will choose one replacement, for every head. **The fault is not
the colour white; it is the UNIFORMITY.** A rail of identical fawn hats is the same fault
wearing a different colour.
📌 **EP16's prompt already said *"about half in hats including Akubras"*** — hats were named,
the RANGE was not, and that is exactly the §2 gap in a new place: *the model dresses what it
is told about and improvises the rest.*

---

## 📋 STILL UNSPECIFIED — found by auditing all seven EP16 prompts, not yet gone wrong
*Recorded so the next fault is one we have not already seen coming.*

- **HELMETS.** No prompt has ever named one. Australian rules require them; *"silks"* alone
  does not imply a helmet, and EP16's riders wore flat caps.
- **THE CAMERA.** *"Cinematic wide shot"* says nothing about whether the camera holds,
  pans or tracks — so the generator decides, and a held camera on a slow subject reads as
  a still.
- **THE ACTION LASTING THE WHOLE CLIP.** Clips are trimmed to 5s. Nothing asks for the
  movement to continue across all of it, so a clip can start moving and settle.
- **THE COUNT.** `nine-runners-turn` illustrates *nine* evenly matched runners and the
  prompt says only *"a closely bunched field"*. The number in the article is not in the
  prompt.
- **THE RUNNING RAIL** is covered above and remains the one fault only a human eye catches.

## ⚠️ What went wrong on EP03 (the reason for this file)
EP03's b-roll folder carried over **5 identical clips from EP02** (same bytes):
`empty-track-golden`, `finish-rail-surge`, `grandstand-crowd`, `odds-board`,
`turf-field-race`. It also leaned on two very similar close-finish shots
(`finish-rail-surge` + `tight-finish`). From EP04 on, none of the subjects
below may be reused — generate fresh footage each time.

## Used so far

### EP01 (2026-07-19)
| File | Subject |
|---|---|
| ElevenLabs_video_Seedance 2.0_Aerial drone shot, wide angle | Aerial/drone wide over the course |
| ElevenLabs_video_Veo 3.1 Fast_Extreme close-up, macro lens | Macro extreme close-up |
| ElevenLabs_video_Veo 3.1 Fast_Medium close-up shot, static | Medium close-up, static |
| ElevenLabs_video_Veo 3.1 Fast_Medium shot, eye level, adult | Medium eye-level, person |
| ElevenLabs_video_Veo 3.1 Fast_Wide establishing shot | Wide establishing |
| ElevenLabs_video_Veo 3.1 Fast_Wide shot, low angle, a field | Wide low-angle field of runners |

### EP02 (2026-07-20)
| File | Subject |
|---|---|
| broll-empty-track-golden | Empty track, golden light |
| broll-finish-rail-surge | Field surging along the rail to the finish |
| broll-grandstand-crowd | Grandstand crowd |
| broll-odds-board | Odds / betting board |
| broll-ticket-tote-window | Tote / ticket window |
| broll-turf-field-race | Field racing on turf |

### EP03 (2026-07-21)
New this episode (keep): 
| File | Subject |
|---|---|
| broll-barriers-load | Horses loading into the barriers (saddled + jockeys) |
| broll-formguide-study | Studying the form guide |
| broll-tight-finish | Tight photo finish |
| broll-trackwork-dawn | Trackwork at dawn |

Carried over from EP02 (⚠️ do NOT reuse again): `empty-track-golden`,
`finish-rail-surge`, `grandstand-crowd`, `odds-board`, `turf-field-race`.

### EP04 (2026-07-21) — "Barriers"
All NEW, all authentically Australian turf (green grass + white running rails; no American dirt — Hugh's flag). QC'd frame-by-frame.
| File | Subject |
|---|---|
| broll-wet-track-wide | Wet/rain-affected turf, legs galloping, wet spray kicked up |
| broll-gate-burst-headon | Full field bursting from the gates, head-on |
| broll-home-turn-sweep | Single runner sweeping the home turn along the white rail |
| broll-wide-runner-labouring | Wide runner labouring around a turn, off the rail |
| broll-mounting-yard-au | Mounting yard — jockey getting a leg-up, connections watching |

### EP05 (2026-07-22) — "A Matter of Weight"
All 1080p/16:9/5s. Frame-QC'd 2026-07-22 — all authentically green Australian turf (no dirt), horses saddled + ridden; the three non-racing shots (crowd, weigh-in, form study) match their intended subjects.
| File | Subject |
|---|---|
| broll-field-powering-turf | Tight field powering down the turf straight |
| broll-racecourse-wide | Wide empty racecourse — grandstand + green straight, white rail |
| broll-blanket-finish | Horses locked together at the line, on the rail |
| broll-crowd-close-finish | Diverse crowd cheering a close finish |
| broll-winner-hits-line | Field driving to the line on turf |
| broll-two-horses-side-by-side | Two runners head-to-head, close on the rail |
| broll-sprinters-early-speed | Bunched sprinters, early-race speed |
| broll-jockey-weighing-in | Jockey + clerk of scales at the weigh-in (saddle + scales) |
| broll-horse-weakening-late | A tiring horse dropping back late |
| broll-horse-labouring-headon | Head-on close-up of a runner labouring late on turf (swap) |
| broll-punter-odds-board | Punter watching the tote odds-board (orange figures), ticket in hand (swap) |

✅ **Overlap resolved — swaps applied 2026-07-22:**
- `broll-punter-studying-form` → **retired** (moved to `broll/_retired/`), replaced by **`broll-punter-odds-board`** (tote odds-board angle — no longer repeats EP03's `broll-formguide-study`). Thematically adjacent to EP02's retired `broll-odds-board`, but a distinct punter-with-board composition, chosen by Jodie.
- `broll-horse-labouring-late` → **retired** (moved to `broll/_retired/`), replaced by **`broll-horse-labouring-headon`** (head-on close-up — distinct from `broll-horse-weakening-late` and from EP04's `broll-wide-runner-labouring`).
- Softer echoes kept as-is (distinct compositions): `crowd-close-finish` vs EP02 `grandstand-crowd`; `racecourse-wide` vs EP01 `wide establishing`.

## Subjects now "used up" — pick fresh ideas for EP04+
Aerial/drone wide · macro close-up · medium eye-level person · wide establishing
· wide field of runners · empty track golden light · rail surge to finish · tight
photo finish · grandstand crowd · odds/betting board · tote/ticket window · turf
field race · barriers loading · form-guide study · dawn trackwork.

Fresh ideas not yet used (examples): mounting yard / parade ring, jockey weigh-in
scales, saddling stall, hoof/leg detail in motion, winning-post shadow, mud/rain
meeting, night meeting under lights, strappers leading horses, close-up of silks,
binoculars in the stand, horses cooling down after the race.

### EP06 (auto-logged)
| File | Subject/line |
|---|---|
| broll-winner-hits-line | a horse finish strongly to win |
| broll-front-runners-pressing | several front-runners... keep them rolling |
| broll-leader-clear-front | the leaders... are ideally suited |
| broll-closer-making-ground | a horse six lengths back... within reach |
| broll-swooper-wins | backmarkers... capable of winning |
| broll-punter-form-study | build the study of pace into your form (non-turf, cafe) |
| broll-racecourse-wide | reading the speed shape of a race |

⚠️ **Reuse (Jodie-approved 2026-07-23):** `broll-winner-hits-line` and `broll-racecourse-wide` are reused from EP05 for these two connective shots — waived the no-repeat rule per Jodie's call. The other 5 are new, all turf + saddled (except `broll-punter-form-study`, an intentional non-turf cafe shot). Frame-QC'd 2026-07-23.

### EP18 (2026-08-08) — "Those Top 6 Favourites"
| File | Subject |
|---|---|
| broll-binoculars-lowered-stand | Punter lowering binoculars in the stand |
| broll-lone-outsider-trailing | Lone outsider trailing the field |
| broll-field-canters-to-barriers | Field cantering back to the barriers |
| broll-strapper-leads-winner-in | Strapper leading the winner in |
| broll-dividends-screen-after-race | Dividends screen after a race |
| broll-crossing-off-the-card | Hand crossing races off a card |
| broll-country-course-gums-and-rail | Quiet country course, gums and rail |

> #### ♻️ SUPERSEDED THE SAME DAY — the white-hat fix. **Jodie's call, 8 Aug 2026.**
> **`broll-country-course-gums-and-rail`** and **`broll-binoculars-lowered-stand`** were
> **regenerated**, replacing the first versions. The originals came back with a UNIFORM
> pale-cream hat on every head — sixteen of them along the rail in the first clip, in
> sharp focus. See standing shot template item 4 and ruling **A15a**.
> **What changed in the prompt** — the old line was *"About half in hats including
> Akubras"*, which names hats and not their range. Both now read:
> > *"About half the visible crowd in hats, Akubra-style in a variety of natural colours
> > - fawn, sand, tan, brown, grey, black and olive - worn at different angles, no two
> > neighbours in the same colour."*
> **The superseded versions are not in service** — the files were deleted before the
> regeneration, so nothing downstream can pick them up.
> 📌 **A REGENERATION IS NOT A REPEAT.** `broll_registry_check.py` excludes an episode's
> OWN section from the no-repeat comparison, so logging a replacement here is safe and a
> visual correction stays hands-off. *That rule exists because the first attempt at this
> fix hard-failed the build.*

### EP08 — deliberate exception (2026-07-25, Jodie's call)
- **EP01 thumbnail hero (dramatic field-rounding-the-turn) reused as EP08's COVER hero.**
  EP01 was an unpublished test — never posted — so this image has never been seen by
  viewers; not a real repeat. Used on the EP08 e-book cover + end card only (not b-roll).
  Cover A/B autogen options were rejected; ~0 new credits.
