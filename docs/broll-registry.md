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

### EP08 — deliberate exception (2026-07-25, Jodie's call)
- **EP01 thumbnail hero (dramatic field-rounding-the-turn) reused as EP08's COVER hero.**
  EP01 was an unpublished test — never posted — so this image has never been seen by
  viewers; not a real repeat. Used on the EP08 e-book cover + end card only (not b-roll).
  Cover A/B autogen options were rejected; ~0 new credits.
