# B-roll registry — every clip we've ever used

**Why this exists:** so the same clip is never seen twice inside one episode, and so
every clip we own can be found and re-used when it genuinely fits.

## 🔴 THE NO-REPEAT LAW, AS IT NOW STANDS (Jodie, 18 September 2026)

> ### **No repeat WITHIN an episode. Cross-episode re-use is ALLOWED — when the clip
> ### MATCHES THE LINE it sits under.** Relevance is the test, not novelty.

⚠️ **THIS REPLACES THE OPENING LAW THIS FILE CARRIED FROM 21 JULY 2026** — *"so no b-roll
is ever repeated from an earlier episode … every new clip's subject must NOT already
appear below."* That rule made the library write-only: 278 clips nobody was allowed to
touch, and a new generation for every slot whether or not we already owned the shot.
**The library is now the FIRST place to look.**

📌 **WHAT DID NOT CHANGE, and is not softened by this:**
- **Within one episode, no subject twice.** That was Jodie's EP03 note and it stands.
- **Relevance to the line is the whole test.** A clip re-used because it is *there* and
  not because it *fits* is worse than a new one — it is the reason the old rule existed.
- **Turf only, crowd diversity, and every hard-fail below.** A clip that was acceptable
  once is not grandfathered: **a rejected clip stays rejected for every use**, and the
  EP46 rail-crossing clip at the foot of this file is the standing example.
- **After an episode ships, add its clips here** (episode, file, one-line subject).

🔴 **AND A LENGTH RULE THE OLD LAW NEVER HAD TO THINK ABOUT.** The two-way format asserts
**8–10s** b-roll (`twoway_beats.BROLL_DUR_MIN_S/MAX_S`). **267 of the 278 clips in this
library are exactly 5.0s and the longest is 8.1s**, so for a two-way episode re-use is
usually blocked by DURATION before relevance gets a say. Measured 18 Sep 2026.

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

### 5. THE WHOLE FIELD RUNS ON ONE SIDE OF THE RAIL — say which side, every racing shot
**(Hugh, from EP23 as shipped, 14 Aug 2026. EP24 onward. EP23 is published and is NOT
changed.) The fault: horses ran on BOTH SIDES of the rail.**

**Say it, every galloping / field / raceday shot:**
> *"The whole field runs on ONE side of a single white running rail — the rail is the
> inside boundary of the track, open green turf infield beyond it, no horses on the far
> side; on a bend the rail curves with the track and the field stays outside it."*

> ## 🔴 THE GAP, AND IT IS §2's GAP IN A NEW PLACE. **EP23's prompts DID name the rail —
> ## five of six of them. Not one said WHICH SIDE OF IT THE HORSES GO.**

Read what they actually asked for. In every case the rail is **scenery**:

| clip | how the rail was described |
|---|---|
| country-course-wide-sweep | *"…white running rail running away across the frame"* |
| roomy-circuit-long-straight | *"…white running rail alongside and open empty turf beyond it"* |
| tough-track-uphill-finish | *"…white running rail along one side"* |
| coming-from-well-back | *"…white running rail curving away on the inside"* |
| inside-barriers-turn-for-home | *"…the leaders tight against a … white running rail"* |

Every one of those places the rail **in the frame**. Not one states the **RELATIONSHIP**
between the field and the rail — that it is a BOUNDARY, that the runners are all on the
same side of it, and that what lies beyond it is empty turf. So the model drew the rail
it was asked for and filled both sides with the horses it was also asked for.
**It did what it was told; it was told the wrong thing** — §1's sentence, exactly.

**This is the same shape as §4:** hats were named, *the range* was not. Here the rail was
named, *the side* was not. **A model completes what you describe and improvises the rest,
so the thing that must be true has to be the thing you say.**

⚠️ **THE POSITIVE HALF IS THE HALF THAT WORKS: "open green turf infield beyond it."**
*"No horses on the far side"* is worth keeping as belt-and-braces, but a negation cannot
be drawn — the model has to render *something* beyond the rail, and if you do not say
what, it will reach for the subject you have spent the rest of the sentence describing.
**Give the far side a job (empty infield) and there is no room left for a horse.**

📌 **AND STOP SENDING "DEAD STRAIGHT AND PERFECTLY LEVEL" INTO A BEND.** EP23 asked for
*"a dead straight and perfectly level white running rail"* in `coming-from-well-back`
(*"curving away on the inside"*) and in `inside-barriers-turn-for-home` (*"sweeps around
a bend"*) — **a standing line pasted in unconditionally, contradicting the shot around
it.** Asking a model for a straight rail on a bend is asking for incoherent geometry, and
incoherent geometry is the soil the both-sides fault grows in.

> ## 🔴 THE LAW ON THE RAIL'S SHAPE (Jodie, 16 August 2026, after EP27 halted)
> **REAL RACING TRACKS CURVE.** A rail is WRONG only when it has an abrupt **kink, jag,
> zig-zag, wobble or warp**.
> - On a **BEND** — *turning for home*, *rounding the turn* — the white running rail
>   follows the track as **a single clean continuous line that SWEEPS in a long, smooth,
>   even curve.**
> - On a **STRAIGHT** it runs straight.
> - **NEVER force *"dead straight"*, *"straight and true"* or *"perfectly level"* onto a
>   shot that bends.**
>
> **The law is enforced in `engine/broll_prompt_rules.py`, and it is written out in full
> at the top of that file** — not referenced from here. A rule that lives in a doc and is
> enforced in code is two rules, and the doc is the one that goes stale.

⚠️ **THIS PARAGRAPH USED TO END "keep *dead straight and perfectly level* for the
straights, where it is true" — AND THAT SENTENCE IS WHY EP27 HALTED.** It is a ready-made
phrase, so it got copied; the copy landed in `broll-the-field-turning-for-home`, in capitals
and joined by a comma, and the whole episode stopped. **The phrase is no longer offered
here in any form.** Use the wording the code applies, which is stated positively and is
different for the two shots:

| the shot | the wording |
|---|---|
| **straight** | *the white running rail is one clean unbroken line running true and even along the track, evenly spaced upright posts and a level top rail* |
| **bend** | *the white running rail is one clean unbroken line that follows the track in a single smooth even sweeping curve, evenly spaced upright posts and a level top rail* |

**You do not have to remember which.** The engine detects the bend and applies the right
one; on a bend it also strips any *"dead straight"* claim it finds, in any casing and
however the words are joined.

---

## 🇦🇺 THE FULL AUSTRALIAN RACING SPEC — every racing shot, stated POSITIVELY
**(Consolidated 14 Aug 2026 with §5, so one block carries all of it. The sections above
are the REASONING and the evidence; this is the checklist.)**

> *Lush green Australian turf. A single white running rail as the inside boundary of the
> track, open green turf infield beyond it — the whole field on ONE side of it, no horses
> on the far side; on a bend the rail curves with the track and the field stays outside
> it. Thoroughbreds galloping, each horse at a different point of its stride, staggered
> strides, hooves landing at different moments, legs out of phase across the field.
> Anatomically correct horses — four legs, one head, no fused or extra limbs. Jockeys up
> and crouched in the irons, actively riding, in bright and VARIED Australian racing
> silks and matching caps, white or cream breeches, black riding boots, safety helmets
> with the silk cover on. Crowd in present-day Australian dress, Akubra-style hats in a
> VARIETY of natural colours — fawn, sand, tan, brown, grey, black, olive — worn at
> different angles, no two neighbours alike; the Australian ethnic mix and a wide range
> of ages. **The white running rail is ONE CLEAN UNBROKEN LINE that follows the track —
> true and even along the straights, a single smooth even sweeping curve through the
> bends — with evenly spaced upright posts and a level top rail.** Photoreal, cinematic.
> **Bright, warm and luminous light, generously exposed and richly cinematic — a low
> dramatic late-afternoon sun, long warm golden-hour light and a warm sunset glow.***

**Every clause is there because something went wrong without it** — the rail side (EP23),
the strides (EP16 1:25), the silks (EP16 8:11), the hat range (EP18), the turf (US dirt
is the model's default), **the rail's own LINE and the LIGHT (EP26, 15 Aug 2026)**.
**Nothing here is decoration and nothing here is a negation**, which is the rule the
whole file is built on: *describe the thing you want to SEE.*

### 💡 THE LIGHT IS NOT ONLY FOR RACING SHOTS (Fault 6, EP26, 15 Aug 2026)
**EP26's images came back too DARK, and a "man at a desk" card was discarded for nothing
but being dim and murky** — the composition was right, the credit was spent. So the
lighting line is the one standing line that applies to **EVERY generated image**: the
covers, the racing wides, the crowd shots, and the indoor scenes that contain no horse,
no crowd and no rail and are skipped by every other rule in the file.

> *An indoor, desk or portrait scene is warmly and generously lit — warm sunlight through
> a window, lamp-warm highlights, the subject bright and clearly visible.*

⚠️ **"Bright natural daylight" is not enough, and that is not a quibble.** The cover brief
already said exactly that while EP26 came back dim. A model cannot draw *"not dark"*: it
must choose an exposure, and told nothing specific it chooses the safe middle, which
prints murky. Name the warmth and the hour.

### 🚧 A CURVE IS CORRECT; A KINK IS NOT (Fault 7, EP26, 15 Aug 2026)
**EP26's running rail had an unnatural KINK.** This **extends** the rail-side rule (EP23)
rather than repeating it: *a rail can be perfectly one-sided and still jag.* A real
racecourse is an oval, so curves are expected and must not be argued away — what must
never appear is an abrupt kink, jag, zig-zag, wobble or warp. Since *"no kinks"* cannot be
drawn, the line describes **the line the rail should trace**: continuous, evenly posted,
level along the top.

⚠️ **And it is stated in the form the shot can be.** The straight wording and the bend
wording are different sentences, and neither contains *"dead straight"* or *"perfectly
level"* — those two phrases are what the straight-rail-on-a-bend contradiction check looks
for, and pasting one into a bend shot manufactures the very incoherent geometry this
family of faults grows in.

⚠️ **The rule applies to a picture that HAS a rail — asked directly, not inferred from a
horse.** EP26's cover hero is a man at a desk with framed racing photographs behind him:
it mentions racehorses, jockeys and galloping, and then says *"NO FENCE, NO RUNNING RAIL
AND NO RAILINGS anywhere."* Gated on horses, the rule wrote a running rail into it — not
a missing line but a **contradiction**, and a worse picture than the kink.

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


### 🎬 EP49 — THE FIRST TWO-WAY B-ROLL (18 September 2026). **JODIE REVIEWED EVERY CLIP.**

Four slots, generated at **8–10s** — the first clips in this library that meet the
two-way duration rule rather than the 5.04s default. **84.00 credits for the four plus
two regenerations**; the rest of EP49's slots stay unfilled until the full episode is
built.

| clip | Jodie's verdict | note |
|---|---|---|
| `broll-yearling-led-past-the-sale-ring-boards` (8s) | ✅ **KEEP** | *the horse reads
slightly odd* — accepted with that noted, in the spirit of the 5 Aug ruling that an
occasional odd clip is cheaper than the process that would catch it |
| `broll-trackwork-riders-at-dawn-in-the-mist` (10s) | ✅ **KEEP** | two riders cantering
away, rail on their inside and stable throughout |
| `broll-finish-line-clock-ticking-over-an-empty-straight` | 🚫 **REJECTED, AND NOT TO BE
REGENERATED AS A CLOCK** | take 1 showed numerals despite the prompt; take 2 showed
number- and letter-like marks that are not characters, and the hands moved wrongly. **The
subject is banned, not the wording** — see PP-STANDARDS §B-roll, *Nothing that carries
numerals or a mechanism*. Replaced by a punter at a kitchen table and a hand circling a
name in red biro. |
| `broll-field-rounding-the-turn-clues-everywhere` | 🚫 **REJECTED TWICE** | take 1: the
rail dissolved and the horses changed sides of it (the EP46 fault, caused by a prompt
asking for a rail between camera and field AND the field driving at the camera — an
impossible geometry). take 2: **the rail bent in an S and the field galloped in step.**
Regenerated once more under the new rules. |

📌 **The trackwork clip's KEEP came from asking.** It was the one clip Jodie's review did not name, and silence was held rather than read as approval — on the day the review rule was written, that is the only reading available. One word put it in the cut.

#### THE FINAL FOUR, ALL PASSED BY JODIE BEFORE THEY WERE FILED

| slot | clip | length |
|---|---|---|
| *"taking in breeding, sales prices"* | `broll-yearling-led-past-the-sale-ring-boards` | 8.0s |
| *"serious punters examining in greater detail"* | `broll-a-punter-over-the-formguide-at-the-kitchen-table` | 9.0s |
| *"was that fast workout an indication of something good"* | `broll-trackwork-riders-at-dawn-in-the-mist` | 10.0s |
| *"each race is a mystery"* | `broll-field-rounding-the-turn-clues-everywhere` (take 3) | 8.5s |

🔁 **THE SECOND SLOT WAS RENAMED.** It asked for a finish-line clock; the clock's SUBJECT
is now banned, so the slot became the shot that is actually in it — a man over the
formguide at a kitchen table under a lamp. **A clip must match its name and its recorded
prompt**, and a slot whose target describes a shot that will never exist is a halt
waiting to happen.

🚫 **AND ONE MORE REJECT, WITH A LESSON THAT IS NOT ABOUT RACING.** The second of the two
replacement ideas — *a hand circling a horse's name with a red biro* — came back with
Jodie's verdict **"he is drawing a long circle around nothing!"**, and she is right. The
prompt asked for the page to be *"heavily defocused into soft grey texture"* with *"only
the wet red ink sharp"*, to satisfy the no-legible-print rule — **and that removed the
thing the action was FOR.** Not regenerated: the slot it was offered for is filled by the
kitchen table, which Jodie picked. **Rule added to PP-STANDARDS: ask for the STRUCTURE
without the words — *"neat printed rows and columns of grey type, the individual words
too soft to read"* — so the pen still has something to circle.**

⚖️ **THREE OF MY PROMPTS BROKE THEIR OWN SHOTS IN ONE DAY**, each by making a rule true
and the shot impossible: a rail between camera and field that the field had to run
through; a dial with no numerals that came back as gibberish; a page blurred past the
point where a circle could land on it. **When a constraint is added, read the whole
prompt back and ask whether the SUBJECT still survives it.**

🔴 **AND THE FINDING THAT MATTERS MORE THAN ANY OF THE CLIPS.** Take 2 of the field was
checked by machine, passed, promoted and composited into a cut. **It was wrong in two
ways the checker had no rule for** — an S-bent rail and a synchronised field — and Jodie
found both by looking at it. Both are now standing rules and both are on the
watch-through list; and the process rule that came out of it is in PP-STANDARDS:
**she reviews every generated clip in the widget before it is filed or placed. The
automated watch-through is a floor, not the gate.**

⚠️ **THE OUT-OF-STEP WORDING WAS IN THAT PROMPT AND THE FIELD STILL GALLOPED IN STEP.**
Saying it once is not enough. The field must ALSO be described as **spread** — *"a spread
field, horses at different strides and different positions, staggered, no two in step"* —
because a bunched field is what the model synchronises.

### 🚫 EP46 — ONE CLIP REJECTED (Jodie, 15 September 2026)

| clip | why it is rejected |
|---|---|
| `broll-a-field-of-runners-sweeping-past-the-outside-rail-at-the-turn-seen-from-the-lawn` | **The horses change sides of the rail during the clip.** Every individual frame is plausible; the MOVEMENT is not. |

🔴 **THIS IS THE CLIP THAT BOUGHT THE ONE-PASS WATCH.** The rail rule at the top of this
file has been in force since 28 July and this clip still shipped — because the control
was the 6-up `broll-contact.png`, which **samples six frames**, and a fault that happens
*between* frames cannot appear in a sample of them. **A still is judged frame by frame; a
clip is not.** So every clip is now watched end to end once, or motion-mapped, and
anything crossing a rail or fence, morphing, or changing count is a REJECT.
Full rule: `PP-STANDARDS.md` §B-roll -> "NEW QC STEP: EVERY CLIP IS WATCHED THROUGH ONCE".

⚠️ **REJECTED FOR EVERY USE, NOT JUST THIS ONE** — the standing rule beside the cover
heroes applies here too. Do not lift a frame of it for a thumbnail or a cover.

📌 **EP46 ITSELF IS NOT BEING CHANGED.** It is a separate conversation, and the standing
ruling holds: *a guard prevents recurrence; it does not oblige us to go back.* The clip
file is left exactly where it is; this entry is the record.

## 🔴 FOUR RULES OUT OF FOUR REJECTED CLIPS — 20 SEPTEMBER 2026 (Jodie)

**Every one of these was written from a clip that was generated, paid for and looked at.
Three of the four faults were in prompts I wrote, and two of those had already been
written down on 18 Sep in another form.**

### a. 🔴 HIGGSFIELD CANNOT COUNT. NEVER ASK FOR MORE THAN **FOUR** HORSES OR PEOPLE.
*"a field"*, *"eight thoroughbreds"*, *"twelve saddled thoroughbreds"*, *"each led by a
strapper"* — all of them produce **horses that vanish mid-clip and handlers that
are simply missing**. EP49's field-of-eight lost a horse in front of the camera; its
walk-on of twelve gave most of the horses no strapper at all.
⭐ **A COUNT IN A PROMPT IS A WISH, NOT A SPECIFICATION.** Ask for four, get four.
Ask for twelve and the model will produce a crowd that does not survive nine seconds.

### b. 🔴 SADDLECLOTHS ARE PLAIN. SAY SO: *"plain saddlecloths, no numbers"*.
Numerals were banned outright on 18 Sep and the ban was read as being about **clocks and
boards**. It is not: **every saddlecloth in the field-of-eight carried the same number**,
which is both a numeral on screen and a racing impossibility. The positive instruction
works where the negative one did not — the same lesson as the skullcap.

### c. 🔴 THE WORD "JOCKEY" PRODUCES A RACING CROUCH, WHATEVER THE HORSE IS DOING.
The walk-on asked for *"jockeys up"* on horses **walking**, and got riders folded into a
racing crouch on horses at a walk — a shot no racegoer would believe.
⚙️ **SO: a walking or parading horse is RIDERLESS AND LED. A jockey appears
only on a horse at a gallop.** If the shot needs a person beside a walking horse, that
person is a strapper at its head, not a rider on its back.

### d. ↻ THE RAIL GOES BEHIND THE HORSES, NEVER BETWEEN THE CAMERA AND THE HORSES.
**Restated from 18 Sep because it was broken again on 20 Sep, twice, by me.** A rail in
the near foreground plus a subject that must cross that line is an impossible geometry,
and the model resolves it by drawing the rail THROUGH the horses' legs. Put the rail on
the far side of the action or leave it out of the prompt.

⚠️ **AND THE PATTERN UNDER ALL FOUR, WHICH IS THE PART WORTH KEEPING:** every
one of these faults came from asking for something SPECIFIC that the model cannot hold
— a count, a marking, a posture, a geometry — rather than from asking for too
little. **A prompt is a description of a photograph, not a list of requirements.** When
a constraint is added, read the whole prompt back and ask whether the SUBJECT survives
it.
