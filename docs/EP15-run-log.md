# EP15 — run log

**Written 4 August 2026, ~19:50 mid-build; brought current ~20:20 after the end-card
fault.** *Everything a fresh session needs to finish this episode. Not a history of the
build — the rulings are in `CLAUDE.md`, the findings in the session checkpoint.*

---

## 1. WHERE EP15 IS

> ### ⏳ THIS SECTION IS A MID-BUILD SNAPSHOT OF 4 AUG ~20:00 AND IS HISTORICAL. DO NOT
> ### READ IT AS CURRENT STATE.
> The rebuild it describes **finished**: `output/PP-EP15-FINAL.mp4`, 196,581,107 bytes,
> 817.02s, written **20:12:35**, with `self_qc` **PASS** written after it at 20:15:02.
> **For where EP15 is now, read the session checkpoint and the rail — never this.**
> Kept because the proof test below is the reusable part.

**Rebuilding `assemble_passB` a SECOND time — for the end card, not for C10.**

**Done:** C10 rebuilt from four cells to three (four was illegible once the panel-push
composite scaled it to 810 wide, 42%, which no check caught because `card_check` and
`self_qc` both measure the page at 1920). FINAL rebuilt 19:55:29, 195,716,654 bytes,
817.02s — **all four proof conditions met** — and `self_qc` **PASSED** against it at
19:57:26. Every content card is fine.

**Then the stills found a fault that every check had passed. See §2.**

**Sequence still to run:**
1. `assemble_passB` → a new `output/PP-EP15-FINAL.mp4` *(carrying the fixed end card)*
2. `self_qc` **against that new file**
3. three stills, looked at first, then hand to Jodie

### THE PROOF TEST — four conditions, all required
A rebuilt FINAL is only accepted when **all four** hold. *Version 1 of this test accepted
the file at **0 bytes** — ffmpeg had created it and not yet written to it, and 0 == 0 ten
seconds later looked settled.*

| # | condition |
|---|---|
| 1 | mtime **later than the input that changed** *(now `overlay/clips/end-card-template.mp4`, 20:07:30)* |
| 2 | size **≥ 100 MB** |
| 3 | size **unchanged across two 20s samples** |
| 4 | `ffprobe` duration **within 5s of 817s** |

**And watch the PRODUCER, not only the file** — if `claimed_by` is null while the status
is in `WORKING`, nothing will ever write it (see §6).

*A calibration note, since my own watcher asserted otherwise: a finished PP episode runs
about **15 MB per minute** (EP14: 177,043,167 bytes / 688.5s). The docstring's remembered
"~1.0 GB" was wrong. **A remembered figure is a proxy like any other.***

---

## 2. 🔴 THE END CARD SHIPPED A BROKEN IMAGE, AND EVERY CHECK PASSED IT

**Found by looking at the third still. Nothing else found it.**

The end card rendered a **grey rectangle carrying browser ALT TEXT** — the words *"The
Practical Punting Guide — Killer Strategies for the Trifecta"*, **which is not even this
episode's title.** And page 1 of the shipped e-book PDF was **blank white.**

**One cause, both artefacts.** This morning's quarantine removed nine files composed from
the rejected cover hero. Two were never put back:

```
ebook/cover.png                 -> the e-book's <img src="cover.png">      PAGE 1 BLANK
overlay/export/ebook-cover.png  -> the end card's <img src="ebook-cover.png">  ALT TEXT
```

Everything downstream was then built **into the hole**: the end-card clip at 09:48:21
(**120,789 bytes**; with the photo in it, **798,050**), the PDF at 19:08, the FINAL at
19:55.

> ### WHY NOTHING CAUGHT IT
> `card_check` measures layout collisions, not whether an `<img>` resolves. `self_qc`
> returned an honest **PASS** — and even reported *"end card visible at the e-book beat
> (luma 33)"*, **because a grey box has a luma.** Every instrument was asking about the
> wrong thing. **This is fault #1 again: the artefact was never looked at.**

**And the code already knew.** `render_ebook_cover()`'s own docstring says *"the cover
must land before the card batch or the end card renders blank"*, and `SKILL.md` line 98
spells out *"missing `ebook-cover.png` → alt-text shows"*. **Both were written down and
neither was enforced** — which is the whole argument for guards over prose.

**THE THIRD BREACH IN ONE DAY of "quarantining leaves a hole, and the hole must be
refilled."** Written at 08:00, breached twice by 19:00, breached again here.

### THE FIX, and what proves it
| artefact | before | after |
|---|---|---|
| `ebook/cover.png` | missing | 2,710,310 · 20:05:52 |
| `overlay/export/ebook-cover.png` | missing | 2,710,310 · 20:06:00 |
| `overlay/clips/end-card-template.mp4` | 120,789 | **798,050** · 20:07:30 |
| `output/PP-EP15-ebook.pdf` | 2,679,995 (blank cover) | **5,377,935** · 20:07:53 |
| `output/PP-EP15-FINAL.mp4` | broken end card | rebuilding |

The pick was **not** re-decided: `hero.png`, `overlay/export/title-hero.png` and
`thumbnail/hero.png` are all sha256 `961b2c65…`, identical to `hero-a.png`. **Hero A,
already Jodie's choice, staged everywhere.** Composing a cover from an approved hero is a
chore. Stale originals kept in `superseded-blank-cover-2026-08-04/`.

### THE GUARD — `engine/check_page_images.py`
**For every page, does every image it references exist on disk?** No list to maintain, so
it cannot go stale as pages are added — which is exactly why the list-based guards missed
this (`assert_standing_assets()` names the standing pages; `stage_title_hero()` names the
title hero; **this file was on neither list**, and neither was the title hero that
rendered onto flat black eight hours earlier).

`engine/test_page_images.py` — **9 cases, and the one that proves it is
`test_missing_ebook_cover_is_caught`**, which copies the REAL
`assets/end-card-template.html` and asserts the check names `ebook-cover.png` while it is
absent. Six more assert it does **not** cry wolf (remote URLs, `data:` URIs, scripts,
unrendered template slots, query strings, subfolders). Clean on EP15 (17 pages) and EP14
(15 pages).

⚠️ **NOT YET WIRED INTO THE ENGINE — code freeze, EP15 is mid-build.** The call belongs
in `render_cards()` immediately after `stage_card_furniture()` and **before** the batch
render. **Land it with the rest of the landing queue, in one controlled restart.**

> ✅ **LANDED — that paragraph is now history.** `RealProvider.render_cards()` calls
> `assert_page_images(export)` at **`providers.py:1516`**, step 2c: after the pages are
> authored and autofitted, **before** `card_check` and before `render_cards_batch`.
> Verified by reading the function on **5 Aug 2026**, not by reading a status line.
> ⚠️ `MockProvider.render_cards()` does **not** call it, so `run --mock` cannot
> demonstrate it.

---

## 3. THE STILLS, AND THE RULE THAT MATTERS MOST

**Three stills: the title card · a PANEL-PUSH card at composited size · the end card.**

> ## 🔴 LOOK AT THEM YOURSELF BEFORE SENDING THEM.
> **This caught FOUR separate faults on 4 August**, each of which had passed every
> automated check:
> 1. the title card rendering onto **flat black** (its hero had been quarantined and
>    never re-staged)
> 2. C10's panel-push card **illegible** at composited scale — `card_check` 17/17 and
>    `self_qc` both green
> 3. the FINAL being **34 minutes older** than the clip it was supposed to contain
> 4. **the end card's broken image and alt text (§2) — on a FINAL that had just passed
>    a full `self_qc`**
>
> **It is the single most valuable thing to carry forward.** A panel-push still must be
> taken from the FINAL, never from the 1920 page — the page always looks right.

⚠️ **AND SAMPLE A CARD MORE THAN ONCE BEFORE CALLING IT BROKEN.** The C10 still at
480.0s showed the headline over an **empty black panel** and looked like a serious fault.
It was not: the cells arrive on a **staggered reveal**, and the frame had caught the card
mid-animation. Sampling the whole window at 1.5s showed the body-region luma settling
from 60 to 67 as the cells landed, and the frame at 486.0s is correct and legible.
***A single frame of an animated card is not evidence about the card.***

---

## 4. WHAT JODIE MUST BE TOLD BEFORE SHE PRESSES PLAY

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

## 5. TWO THINGS FROM JODIE TONIGHT THAT EXIST NOWHERE ELSE

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

## 6. THE TRAP THAT COST AN HOUR TONIGHT — read before touching the rail

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
