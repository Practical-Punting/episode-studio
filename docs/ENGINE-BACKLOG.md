# ENGINE BACKLOG — E1…E28, and what is closed

**Moved out of `session-checkpoint.md` on 6 August 2026, verbatim.** It had grown to
1,607 lines because a BACKLOG was living inside a file whose job is to be a SNAPSHOT —
and it sat in a machine-local memory silo that two of the three silos cannot see, while
the repo is the studio's stated one home.

> ## READ THE WARNING AT THE TOP OF THE LIST BEFORE YOU READ THE LIST.
> **A list of everything anyone noticed is not a plan.** Take an item off it against a
> REAL FAULT IN A REAL EPISODE, never because the list is long or the item is cheap.

**Where the other things live:** current state → `session-checkpoint.md` · where things
stand and today's order → `HANDOVER.md` · the rules → `PP-STANDARDS.md` · what was
decided and why → `PP-RULINGS.md` · the faults with evidence → `CLAUDE.md`.

*Nothing below was rewritten in the move. Status markers (✅ landed, ⚰️ superseded) are
as they were written; check them against git before acting on one.*

---

# 🆕 LOGGED 15 AUG 2026 — found by the control while baking in EP26 faults 6 and 7

## 🟠 THE A21 RAIL LINE IS GATED ON HORSES, AND IT HAS WRITTEN A RUNNING RAIL INTO INDOOR SHOTS

**Found on REAL EP26 prompts, by running the two funnels over them before writing a test —
not by reading the code.** Not fixed: this is a change to a landed rule (A21) with its own
history, EP26's clips are already generated, and re-gating it could change what every
genuine racing prompt receives. **It needs its own session and Jodie's call.**

`rail-side` / `rail-beyond` apply when `has_horses(prompt)` is true. That question is the
right one for silks and strides. It is the **wrong** question for a rail, and two of EP26's
b-roll prompts show why:

- **`broll-tab-counter-printout`** — *"Photoreal cinematic close shot at an Australian
  betting counter, a pair of hands taking a freshly printed ticket as it comes off the
  terminal…"* — an INDOOR close shot, hands and a terminal. The auto-inject appended
  *"The whole field running on ONE side of a single white running rail — the rail is the
  inside boundary of the track, open green turf infield beyond it, no horses on the far
  side."*
- **`broll-three-hours-over-the-form`** — a form-study scene. Same line, same reason.

**This is the fault the `HORSE_WORDS` note in `broll_prompt_rules.py` already warns
about**, arriving through a different rule than the one it was written for: *"NOW IT WOULD
WRITE HORSES INTO A SHOT OF A CROWD, which is a worse clip than the one the rule exists to
prevent."* It writes a RACECOURSE into a shot of a TAB counter.

⚠️ **The mechanism is already built and proved.** Fault 7's rule (`rail-smooth`, 15 Aug
2026) hit exactly this and answers it with `shows_a_rail()` — a rail is counted only where
the prompt affirms one, and a mention inside a negation does not count. Re-gating
`rail-side` / `rail-beyond` the same way is a small change; **what needs a human is the
consequence**, because a racing prompt that never mentions a rail would then stop being
given one at all, and A21's whole point was that the rail must be a BOUNDARY with a rule
about it. That is Jodie's decision, not a refactor.

📌 **Do not re-generate EP26's b-roll for this.** The clips exist and the episode is built.

---

# 🆕 LOGGED 15 AUG 2026 — found while re-publishing EP26's e-book

## 🟢 "PUBLISHED" IS NOT "THE READER GETS THE NEW FILE" — the publish check can pass on a stale cached copy

**Small hardening item. Logged for its own session; deliberately NOT taken during the
EP26 chart work, because nothing about EP26 was blocked by it.**

`RealProvider._publish_asset()` uploads with `x-upsert: true`, then verifies the public
URL by reading **64 bytes** and asserting the **Content-Type**. Both checks are good and
both were written against real faults (a PDF served as `image/png` downloads instead of
opening). **Neither of them proves the bytes are THIS build.**

**The observation, from a real re-publish.** EP26's e-book was rebuilt with its chart
moved beside its words and re-uploaded through `publish_artefact()`. The upload
succeeded — a cache-busted URL (`?v=…`) returned the new object immediately — but the
plain public URL served the **OLD** bytes for roughly twenty seconds, with a different
`etag` and `cache-control: no-cache`. It converged on its own.

> **A stale edge copy answers 200, with bytes, of the right content type.** It passes
> every check `_publish_asset` makes. The only reason this was noticed is that the
> re-publish script hashed the served copy against the local one — which the engine
> does not do.

**Why it matters, and why it is 🟢 and not 🟠.** The window is short and self-healing,
and the engine publishes an artefact once, well before anybody opens it — so this has
probably never bitten a real episode. It would bite exactly where it hurts most: an
artefact **RE-published after a fix**, where somebody is about to look at it precisely
because it changed. That is the EP25 shape one layer down — *the served bytes were not
the rebuild* — with the twist that here the upload is fine and the CDN is not.

**The fix, when it is taken:** after upload, fetch and compare by HASH rather than by
existence — cache-busting the URL, or retrying the plain URL until the hash matches with
a short bounded wait, and flagging if it never does. Keep both existing checks; they
answer different questions. **Do not "fix" it by trusting the upload response** — the
whole point of the visibility check is that we assert what a person receives, not what
we sent (see the comment already in `_publish_asset`).

⚠️ **AND CHECK WHETHER ANY OTHER CALLER NEEDS IT** before assuming this is one line:
`publish_artefact` is used for the video, the e-book and the thumbnail, and
`_publish_asset` also serves `publish_thumbnail_preview` / `publish_title_preview`,
where a stale preview beside a fresh flag is the same fault wearing different clothes.

---

# 🆕 LOGGED 14 AUG 2026 — found on EP24

## 🟠 A CARD'S CUE IS A QUOTE FROM THE SPOKEN TRACK — AND SPOKEN NUMBERS ARE WORDS

**EP24 C19. Editing a card AFTER the render orphaned its cue from the SRT, and the shot
map halted with one decision to make.**

⚠️ **THE CAUSE IS NARROWER THAN IT LOOKS, AND THE NARROW VERSION IS THE USEFUL ONE.**
The first reading was *"the card was tightened, so its cue phrase changed and no longer
matches what Gordon said"*. Half right, and the half that is wrong changes the rule.

When C19 was split, its new cue was written as
**`sprint races favour runners drawn 7 and inside`** — taken from the ARTICLE, via the
card's own `trace` entry, which reads *"Sprint races favour runners drawn 7 and inside."*
The aligned SRT says:

> **`Sprint races favour runners drawn seven and inside.`**

**The phrase was right. The `7` was the whole fault.** Gordon speaks a spoken-words
script, so **every number is spelled out**; the article and therefore every `trace`
sentence uses digits. **A cue copied from `trace` fails silently the moment it contains a
figure** — and figures are exactly what these cards are about, so it will keep happening.

Checked across the episode: **every other cue was in the SRT**, including the original
cue moved to C19B. Only the newly-authored one failed, and only on the digit.

**THE RULE, for the between-episode list:**
1. **A cue is a quote from the SPOKEN TRACK, never from the article and never from
   `trace`.** `trace` proves a FIGURE's source; the cue anchors to a SOUND. Two different
   jobs, two different strings, and they are not interchangeable.
2. **Numbers in a cue are spelled out**, because that is how they are said.
3. **A card edited after the render may change its DISPLAY text freely — its CUE must
   remain a phrase that is verbatim in `renders/aligned.srt`.** A tighten or a split must
   never orphan a cue from the spoken words.

🔒 **CANDIDATE GUARD, and it is a one-liner:** after any post-SRT card edit, assert every
`cards[].cue` is a case-insensitive substring of the aligned SRT. It would have caught
this before the shot map ran, and it needs no judgement — the SRT is right there.
*(Would also have caught it at authoring time on any episode whose SRT already exists.)*

📌 **AND THE SPLIT PULLED A SECOND, REAL ITEM WITH IT.** Moving C19 to beat 35 made its
window span **beat 36, which was MCU** — a card over Gordon's face, the EP11 failure. The
fix is mechanical (WIDE is the only lawful answer and widening cannot lose a fact) and is
**already an open backlog item below: "CARD OVER GORDON'S FACE → SET THE BEAT WIDE" SHOULD
AUTO-APPLY.** It halted for a human again here. **Second episode running.**
⚠️ `_framing_note` in `docs/episode.json` was amended by hand, because it counts WIDE
beats in prose and goes stale the moment framing is re-derived — the same trap that entry
already warns about.


## 🟠 THE CARD-WRITER OVER-FILLS COUNTRY-TRACK CARDS **(EP24 C19; EP23 C21 was the same family)**

**Jodie's ruling: this is for the AUTHOR to cap, before the next episode. It is a
recurrence, not a one-off, and the Track Secrets country episodes are where it recurs.**

EP24's `C19` put **four** country courses on one matrix card — two facts each, eight
cells. It did not fit **even at the autofit floor** (60% / 16px), and the automatic
layout swap (sibling frame → panel-push) was tried first and did not rescue it, so this
was genuinely over-full and not a layout fault: `mcell` shrank to 49.2px and still ran
under the logo chip, `mplace` to 37.2px and still left the card.

**FIXED ON THE EPISODE by the SPACE rule — tighten and keep, then split, never drop:**
1. Tightened the cells to **73%** of their characters (filler out: *"Favour those…"*,
   *"Give preference to those…"*, *"Runners drawn…"*). **Still did not fit.** That is the
   useful measurement — it says the card was over-full by a whole ROW, not by phrasing.
2. **Split into `C19` + `C19B`**, two tracks each. Both fitted with room to spare —
   88% and 94% of template size — and `card_check` reads 25/25 clean.

📌 **AND THE SPLIT FIXED A SECOND THING NOBODY HAD FLAGGED.** The beats run **one track
each** — 34 Murray Bridge, 35 Balaklava, 36 Strathalbyn, 37 Gawler — and the single card
sat on **beat 37**, showing all four tracks while **Gawler alone** was being spoken.
The two cards now sit on 35 and 37, each on screen while its own two tracks are talked
about. *An over-full card was also a mis-timed one, and only the overflow was visible.*

**WHAT THE AUTHOR SHOULD DO (the actual ask):** cap how much goes on one country-track
card — **two courses per card** is what fits with margin — and split many tracks across
consecutive cards **on the beats where they are spoken**, rather than gathering them onto
the last one. A four-row matrix of two-fact rows does not fit the panel-push card.

⚠️ **`C19B`, NOT A RENUMBER, AND THE REASON GENERALISES.** Inserting a `C20` would have
pushed the existing C20 to C21, and C20 is referenced in **`figures`, `ebook` AND
`build`** — three places to break, mid-build, for a cosmetic ordinal. Two screens of one
idea share the ordinal instead (*"Country Tracks"* / *"Country Tracks, continued"*).
📌 **The eyebrow first read *"(1 of 2)"* and the trace guard REFUSED it** — a numeral on
screen must quote a source sentence, and those digits are not in the article. Correct,
and the words-not-digits form passes. *That guard is doing real work.*

---

# 🆕 LOGGED 13 AUG 2026 — found on EP23, after the overnight Windows reboot

## 🔵 THE BEFORE-NEXT-EPISODE BATCH — **Jodie, 13 Aug 2026: log, do NOT fix now. EP23 first.**

Both found while EP23 sat at 87%. **They are the same fault twice: a derived number
that disagrees with the thing it describes, and nobody compared them.**

### B1 — THE END CARD IS IN THE WRONG PLACE IN THE OVERLAP CHECK (it fabricates overlaps)

**`derive_card_timings.py` places the end card at `beat − endcard_lead`. The assembler
places it at `beat + endcard_lead`, and THE ASSEMBLER IS RIGHT.**

| | end card entry (EP23, master time) |
|---|---|
| `derive_card_timings.py` (`END … (beat 39 - endcard_lead)`) | **803.04** |
| `assemble_episode.py:139` `bs(endcard_beat) + endcard_lead` | **806.04** |
| `qc_episode.py:452` `bs(ecb) + endcard_lead` | **806.04** |

**A 3.0s error, and it invented the halt that stopped EP23.** The reported
`CARD-CARD overlap C23/END: 1.51s` was **phantom**: C23 ran 796.55 → 804.55 against an
end card that does not arrive until 806.04. Its real window was **9.49s against a 9.0s
minimum — it fitted where it was.** C23 was moved to beat 37 on the strength of that
number (harmless, +3s hold, lands clean — kept), but the reasoning was false.

**Fix: `derive` must use `beat + endcard_lead`.** ⚠️ **Then re-check every past episode
whose card-card halt involved END** — this has been silently mis-measuring every one of
them, and the EP22 C18/C19 investigation is a candidate.

### B2 — THE QC END-CARD LUMA CHECK HAS NO MARGIN AND HARD-FAILS A GOOD EPISODE

`qc_episode.py:467` hard-fails on **whole-frame mean luma > 70** at one sampled frame.

**The end card was demonstrably ON SCREEN when EP23 failed.** Measured off
`PP-EP23-FINAL.mp4`: luma **129.4** at film 810–813s (Gordon alone), **71.5** at 814s
(the card lands), then **75.1** flat through to the warranty. The drop is unmistakable;
the absolute number is not.

**There is no margin anywhere in this check:**

| | sampled luma | verdict |
|---|---|---|
| EP22 | **69** | passed — **by one point** |
| EP23 | **72** | HARD FAIL — by two |

EP23's end card steady state is 75.1; **EP22's is 72.1**, so EP22's pass was the luck of
where its single sample landed, not a healthier episode. **The check has been a coin
toss on every episode that ever ran it.**

**Fix: measure the DROP (129 → 71 is unambiguous), or sample the card's own region —
not a bare whole-frame threshold.** ⚠️ **Do not just raise the number**: that keeps a
check whose pass/fail is decided by whatever is behind a semi-transparent card.

🔴 **AND IT BLOCKS EP23 UNTIL IT IS FIXED.** `flag_and_wait` RETRIES the step on clear,
QC is deterministic on an unchanged film, and there is **no waive, accept or override
path in `qc_episode.py`** — checked. Clearing the flag loops. See the checkpoint.


## ✅ CLOSED — A REBOOT SILENTLY PASSES A HUMAN GATE **(found on EP23, 13 Aug 2026)**

**CLOSED 13 Aug 2026** — `providers.ask_once()` / `answer_pending_gates()`, proved by
`engine/test_gate_answered.py` (20 cases). The ask and the answer are two files:
`.asked-<stem>` written before raising, `.answered-<stem>` written only when the engine
observes `needs_look` go false. Resume with only an ask recorded and the question is put
again — no special case needed, because an unanswered ask simply is not an answer.
All three gates in the class were converted (the listen gate and BOTH placement
reviews), and the suite asserts all three use it, since a shared fix one call site opts
out of reads as covered when it is not. Pre-C3 markers on EP01–EP23 are honoured as
answers, so nothing published or in flight is re-halted.

⚠️ **Two traps found while closing it, both worth keeping:**
1. **"Not flagged" also describes a flag that was never raised.** The engine can die
   between writing the ask and flagging the rail; on resume `needs_look` is false
   because *nobody was ever asked*. Promoting on that alone rebuilds the same silent
   pass one layer up. Promotion now requires `flag_step` in the state file — written
   at the moment the rail is flagged — as proof the question actually reached the
   board, and pops it afterwards so it cannot authorise a later gate's orphan ask.
2. **Two tests asserted the bug** (`test_listen_gate`, `test_title_card`). Both called
   the gate twice and required the second to fall through, describing that as "clearing
   the flag". A re-run is equally a crash, a reboot or a `--watch` restart — which is
   EP23 exactly. Neither could tell an answer from a restart, because neither could the
   code.

*Original entry, kept for the reasoning:*

**Jodie's ruling: leave it until EP23 is out the door, then fix it. It is a real fix,
not a note.**

`providers.listen_to_the_master` writes its `.listened-{size}-{mtime}` marker **before**
it raises `EngineFlag`. The marker therefore records that the gate ASKED, not that a
human ANSWERED. Windows updated overnight and killed the engine between the ask and the
answer; on resume the step found the marker and walked straight through into `shot_map`.

**Nothing was lost — the gate sits before the expensive half-hour and the shot map
halted 51s in — and Jodie confirms she had in fact listened. But it passed by accident,
not by design, and the next one may not be so lucky.**

⚠️ **This is a CLASS, not one step.** Any flag-once gate that writes its marker at
ask-time has the same hole. The candidate fix is to record ask-time and answer-time
SEPARATELY — a marker that means "asked" cannot also mean "answered" — and to re-raise
on resume when only the ask is recorded.

## 🟡 "CARD OVER GORDON'S FACE → SET THE BEAT WIDE" SHOULD AUTO-APPLY **(Jodie, 13 Aug 2026)**

**The same argument as the b-roll offsets in `65cbbbe`, and it is Jodie's own.** A
`SHOT PLAN` halt is **not a decision** — the EP11 rule is mechanical: a panel-push card
must have WIDE for its whole window, entry to exit, and `derive_card_timings.py` has
ALREADY computed exactly which beats are wrong (`bad = [n for n in spanned if
framing.get(n) != "WIDE"]`). It then halts so a human can retype `MCU` → `WIDE`.

**EP23 spent 2 of its 4 halts on this**, and both were typing, not thinking:
- **beat 7** — C3's window spilled past the beat boundary once the aligned SRT moved its
  cue later than the word-count estimate had it. `_framing_note` predicted this class
  ("a window that crosses a boundary needs BOTH beats WIDE and it is the thing most
  easily missed") and still missed this one, because it was worked out from word counts.
- **beat 32** — C21 was changed to **panel-push** on 12 Aug to clear the logo collision,
  and framing was never re-derived. `_framing_note` still lists 32 among the beats that
  are MCU *because their card is fullscreen*. **The fix created the halt.**

Auto-apply is safe in a way the card-size halt is not: WIDE is the only lawful answer, it
is already computed, and widening a beat cannot lose a fact. Follow `--apply-broll`'s
shape — apply, re-derive, and print what was changed rather than asking.

⚠️ **`_framing_note` in `docs/episode.json` goes stale the moment framing is re-derived**
(EP23's still says "EIGHTEEN WIDE OF FORTY-ONE"; it is now twenty). Whatever auto-applies
should say so, or the prose becomes a second, wrong source.

## 🟠 `why_card_beat` STILL NAMES THE SECOND CARD'S NUMBERS **(found on EP23, 13 Aug 2026)**

**The exact bug `which_gives_way`'s own docstring says was fixed — it was ADDED
ALONGSIDE, not instead.** In `derive_card_timings.py`:

```python
problems.append(f"CARD-CARD overlap {ids[i]}/{ids[j]}: {ov:.2f}s"
                + why_card_beat(ids[j])          # <- ids[j] is the SECOND card
                + which_gives_way(ids[i], ids[j]))
```

So EP23's C23/END message leads with **"beat 39 is 14.35s long and this card needs
19.80s … IT DOES NOT FIT AT ANY CUE POSITION"** — those are the **END card's** numbers
(beat 39, its 16.80s dwell + 3.0s), not C23's. C23 needs **9.0s** and has **6.49s**.

The docstring records this happening once already: *"which is how a brief came to
describe C19 as needing 18.26s when 18.26s was the END card's dwell."* **EP22 was told
18.26s; EP23 was told 19.80s. Same bug, one episode later.** It makes a card look
roughly twice as oversized as it is, and it is the FIRST thing on the board.

`which_gives_way` below it is correct and carries the real numbers — so the fix is
probably to drop the `why_card_beat(ids[j])` term from the card-card branch, or call it
on `ids[i]`, not to write anything new.

---

# 🆕 LOGGED 9 AUG 2026

## ✅ THE BEFORE-EP20 BATCH — CLOSED 10 AUGUST 2026. 13 of 13 items answered.

| # | item | commit |
|---|---|---|
| 1 | `heygen_video_id` recorded at resolution + refuses to guess | `a95e4a8` |
| 2 | name-vs-id sweep — `_clip` fixed, every other site assessed | `9e50b09` |
| 3 | fidelity gate RECOGNISES headings/figures | `4e9cf0b` |
| 4 | `matrix` block + the nested each | `90482f3` |
| 5 | **RENDER FIRST** + the missing 8th locked-order assertion | `b977dae` |
| 6 | commission-aware watchdog + the engine's own label | `f19787b` |
| 7 | board stops asking for words the machine owes | `33ac69d` |
| 7a | Stage-8 rename automatic at publish | `38553eb` |
| 8 | kick on submit (~25s, not 15 min) | `2d7eede` |
| 9 | bar-chart false blocker **and its `cards[].rail` sibling** | `7babdbf` |
| 10 | framing prose = a second APPROVED source | `007509e` |
| 11 | `words_approved_at` (migration 007, live) | `5ba4cac` |
| 12 | thumbnail redesign — **CLOSED BY JODIE**, no work | — |
| 13 | cover button, Option B + E16 part 2 | `8f76fcc` |

**Also landed on the way, each found by a guard rather than by review:**
`cmd_cleanup_mock` deleted rail rows by FILTER (Jodie's never-delete ruling, now a
gate) · `build.early_cta.at` unexempt in `BUILD_WRITTEN_KEYS`, which would have halted
EVERY episode at `audit_inputs` · four suites resolving EP18 by bare name, which went
SILENT the moment the stage-8 rename fired · two stale test doubles (`test_draft_watch`,
`test_commission_repair`) that had nothing to do with the drafting pass.

---

## 🟡 STILL OPEN AFTER THE BATCH — named, not implied

- 🔴 **`test_capture_article` — 5 failures, NOT investigated.** The capture tool and its
  test were untouched by this batch (git confirms). The page fetches fine (110,541
  bytes, HTTP 200) and the tool then refuses it, consistent with the structure/OCR
  refusals added before the batch. **Either the tool is now too strict for
  practicalpunting.com.au's current markup, or the test predates those refusals.** It
  matters because a capture is the article of record for tracing — worth a session of
  its own.
- 🟡 **`test_board_pause` 19/2** — fails identically against the pre-batch `app.js` and
  says so itself: *"STRUCTURAL ONLY — the caret/undo proof needs a browser and a
  session."* A real browser proof of caret/undo is the missing half.
- 🟡 **`_hero_paths` never checks the PNG against the ledger's `prompt_sha`.** The EP15
  fault in original form. Deferred all batch because it sits on the spend path; #13's
  versioned paths make a fresh round safe, but this specific check is still absent.
- 🟡 **E16's ledger is STILL UNPROVED AGAINST A MOVING BALANCE.** Its own entry says so.
  A spending guard is only proved by watching the number change; ~4 credits buys that.
- 🟡 **The board cannot tell "studio drafting" from "studio gave up"** — the attempt
  ledger is a file in the episode folder and never reaches the rail, so an exhausted
  episode reads "Writing the script…". Put the attempt count on the rail.
- 🟡 **`midroll_window` exists TWICE** (`qc_episode.py`, `render_ready.py`) and the
  copies have already drifted.
- 🟡 **`write_autofit` leaves a blank line per pass** — a fitted page never equals its
  own freshly-rendered definition.
- 🟡 **#13's remaining half:** the actual regeneration into round-N paths runs when the
  studio writes fresh prompts. That is Option B's design, not a gap — but nobody has
  driven a real second round end to end yet.

## ⚠️ BEFORE-EP20 RELIABILITY BATCH — "a finished render that nobody recorded"
**(Jodie, 9 Aug 2026, on EP19.)** She could see Gordon's render finished on HeyGen while
the board showed `heygen_video_id: null`. **Nothing had failed** — the render was
complete, 10m05s, created 04:19:23Z, thirteen seconds before she clicked "started". The
rail had simply never written the id down.

**PART OF IT IS FIXED (`a95e4a8`), AND THE REST IS THE BATCH ITEM.** `_heygen_fetch` now
writes the id the moment it resolves one, and refuses to choose between two completed
renders with the same title. What is still true, and is what belongs in the batch:

- 🔴 **THE ID IS STILL LEARNED LATE, NOT AT THE MOMENT OF SPEND.** E20's ideal fix —
  save it when the job is created — is **not available**: the render is started BY A
  HUMAN in HeyGen's own UI, so there is no creation event in our code to hang it on.
  **The real fix is at the board:** when Jodie clicks "I've started the render", the
  board already writes `render_started_at`; it should ALSO ask HeyGen for the newest
  video matching this episode and write the id then — at the moment a human asserts the
  spend happened, not twenty minutes later when a poller happens to look.
- 🔴 **NOTHING TOLD ANYONE.** The gap was invisible for four episodes and was found by
  Jodie looking at HeyGen, not by the system. **A paid render with no recorded id is a
  reportable state**: the board should say "render started 3h ago, id not yet recorded"
  rather than showing a blank.
- 📋 **AND THE SWEEP E20 ALREADY ASKED FOR IS STILL NOT DONE** — every place we match on
  a NAME where an id exists. It is listed under E20 below (`_clip()`'s glob,
  `_hero_paths`, `broll_registry_check`, `episode_dir()`, `midroll_window`'s folder
  scan, the b-roll job map). *An id is a promise, a name is a guess.*

⚠️ **AND THE META-POINT, because it is the second time today.** E20 was logged on EP15
with the correct diagnosis and the correct fix, and went unfixed until it cost an
investigation on EP19. So did EP16's autofit note, and so did the dead-zone warning
written in `_exit_if_code_changed`'s own docstring. **A finding in a run log is a TODO
with no owner.** Anything in this file that is worth keeping is worth either fixing or
giving a failing test.

## ✅ BEFORE-EP20 #10 — LANDED. A SECOND APPROVED SOURCE, NOT A SECTION EXEMPTION.
**Confirmed NOT landed before this batch** — `script_fidelity.check()` had no exemption
of any kind. Four parts of a script are the studio's own words (opening framing line,
transitions, midroll invitation, outro — `pp-episode-script/SKILL.md` §43), and a number
in one of them stalled the run over Gordon's own storytelling.

🔴 **THE OBVIOUS FIX WOULD HAVE PUNCHED A HOLE IN §0a, so it was refused.** Exempting
those SECTIONS means identifying them inside a plain-text file of undifferentiated
paragraphs, and every rule for that ("the first beat", "the last beat") is a guess that
hands back a hole: an invented racing figure in the outro walks straight through.

**So nothing is exempted by LOCATION.** A figure is allowed when it has a SECOND
APPROVED SOURCE — this episode's own packaging (hook, byline), which Jodie signs off at
the words gate and which is on the RAIL at drafting time, before `episode.json` exists.
"Part 1" and "10 Systems" are her words, written down and approved, so Gordon may say
them. A figure in NEITHER the article NOR the packaging still blocks — which is every
racing figure this gate was ever built for.
🔒 **AND IT IS DECLARED, NEVER SILENT:** each allowance is collected and written to the
run log ("allowed by the approved packaging — …"), so "the gate passed" always comes
with what it waved and why. Same principle as #3: recognise, do not excuse.

📋 **Controls:** the framing figures BLOCK when no packaging is supplied (so the pass
below is not vacuous); they are allowed when it is, and each allowance is recorded; an
invented racing figure still blocks; and a figure invented INSIDE the framing prose
still blocks — the packaging licenses the figures IT contains, not the sentences they
sit in.
⚠️ One test bug worth keeping: the first draft of those cases wrote "23 per cent" and
proved nothing. **A script is what Gordon SAYS**, so `figures()` reads number WORDS —
no script ever contains that string.
📌 **Regression against real shipped scripts:** EP18 and EP19 are unchanged (0 blockers
before and after) and nothing new was waved. EP17 carries ONE PRE-EXISTING blocker
("one to ten") that predates this change and shipped anyway — recorded here rather than
quietly absorbed.

## ✅ BEFORE-EP20 #7a — LANDED. THE STAGE-8 RENAME IS AUTOMATIC AT PUBLISH.
**(Jodie, 10 Aug 2026, on seeing EP19's close-out flag.)** A published episode whose
folder has not been renamed raises **needs_look** — and it is not a decision, it is a
chore. Worse, the message prints a raw command at the operator:
> *"Run, from the repo: `python engine/rename_episode.py EP19 "<approved title>" --apply`"*

**That is an A19 operator-box violation on both counts:** it badges her queue with the
machine's own work, and it asks a person holding a browser to run a shell command they
cannot run. Per PP-STANDARDS §WHAT DESERVES A GATE the fix is to REMOVE the halt, not to
word it better.
**The fix:** the rename becomes an automatic step at publish — the engine renames the
folder, updates `drive_folder` on the rail, and clears the flag itself, silently.
**LANDED 10 Aug 2026.** The close-out renames the folder, records `drive_folder` on
the rail and clears its own flag, silently. The old worry — Drive sync, open files — is
ANSWERED rather than obeyed: a locked folder is logged and retried next pass, never
turned into an instruction a browser operator cannot follow. `rename_episode.py` is
idempotent (the current folder name is its source of truth), so retrying is free.
🔒 **It may only ever clear ITS OWN flag**, matched on the message, because a
`needs_look` raised by anything else is a human being asked a real question. The control
proves it: with that check disabled, a thumbnail-crop question is silently wiped.
📌 **Backlog cleared:** EP16, EP17 and EP18 renamed by the new automatic pass; EP19 by
hand before it existed, with its stale `drive_folder` corrected afterwards.
**The board is now at zero — no episode needs anything.**

## ✅ BEFORE-EP20 #10 — LANDED. A SECOND APPROVED SOURCE, NOT A SECTION EXEMPTION.
**Confirmed NOT landed before this batch** — `script_fidelity.check()` had no exemption
of any kind. Four parts of a script are the studio's own words (opening framing line,
transitions, midroll invitation, outro — `pp-episode-script/SKILL.md` §43), and a number
in one of them stalled the run over Gordon's own storytelling.

🔴 **THE OBVIOUS FIX WOULD HAVE PUNCHED A HOLE IN §0a, so it was refused.** Exempting
those SECTIONS means identifying them inside a plain-text file of undifferentiated
paragraphs, and every rule for that ("the first beat", "the last beat") is a guess that
hands back a hole: an invented racing figure in the outro walks straight through.

**So nothing is exempted by LOCATION.** A figure is allowed when it has a SECOND
APPROVED SOURCE — this episode's own packaging (hook, byline), which Jodie signs off at
the words gate and which is on the RAIL at drafting time, before `episode.json` exists.
"Part 1" and "10 Systems" are her words, written down and approved, so Gordon may say
them. A figure in NEITHER the article NOR the packaging still blocks — which is every
racing figure this gate was ever built for.
🔒 **AND IT IS DECLARED, NEVER SILENT:** each allowance is collected and written to the
run log ("allowed by the approved packaging — …"), so "the gate passed" always comes
with what it waved and why. Same principle as #3: recognise, do not excuse.

📋 **Controls:** the framing figures BLOCK when no packaging is supplied (so the pass
below is not vacuous); they are allowed when it is, and each allowance is recorded; an
invented racing figure still blocks; and a figure invented INSIDE the framing prose
still blocks — the packaging licenses the figures IT contains, not the sentences they
sit in.
⚠️ One test bug worth keeping: the first draft of those cases wrote "23 per cent" and
proved nothing. **A script is what Gordon SAYS**, so `figures()` reads number WORDS —
no script ever contains that string.
📌 **Regression against real shipped scripts:** EP18 and EP19 are unchanged (0 blockers
before and after) and nothing new was waved. EP17 carries ONE PRE-EXISTING blocker
("one to ten") that predates this change and shipped anyway — recorded here rather than
quietly absorbed.

## ✅ BEFORE-EP20 #7a — LANDED. THE STAGE-8 RENAME IS AUTOMATIC AT PUBLISH.
**(Jodie, 10 Aug 2026, on seeing EP19's close-out flag.)** A published episode whose
folder has not been renamed raises **needs_look** — and it is not a decision, it is a
chore. Worse, the message prints a raw command at the operator:
> *"Run, from the repo: `python engine/rename_episode.py EP19 "<approved title>" --apply`"*

**That is an A19 operator-box violation on both counts:** it badges her queue with the
machine's own work, and it asks a person holding a browser to run a shell command they
cannot run. Per PP-STANDARDS §WHAT DESERVES A GATE the fix is to REMOVE the halt, not to
word it better.
**The fix:** the rename becomes an automatic step at publish — the engine renames the
folder, updates `drive_folder` on the rail, and clears the flag itself, silently.
**LANDED 10 Aug 2026.** The close-out renames the folder, records  on the
rail and clears its own flag, silently. The old worry — Drive sync, open files — is
ANSWERED rather than obeyed: a locked folder is logged and retried next pass, never
turned into an instruction. The rename tool is idempotent, so retrying is free.
🔒 **It may only ever clear ITS OWN flag** (matched on the message), because a
needs_look raised by anything else is a human being asked a real question. The control
proves it: with that check disabled, a thumbnail-crop question is silently wiped.
📌 **Backlog cleared:** EP16, EP17, EP18 renamed by the new automatic pass; EP19 by hand
before it existed, and its stale  corrected. **The board is now at zero.**

## 🟡 BEFORE-EP20 #2 — THE NAME-VS-ID SWEEP. ONE SITE FIXED, THE REST ASSESSED HONESTLY.
E20 asked for this on EP15 and listed the sites; nobody did it, and four episodes later
`heygen_video_id` cost an investigation. *An id is a promise, a name is a guess.* Each
site below has now been LOOKED AT rather than left on a list — with what was done.

- ✅ **`_clip()`'s glob** — FIXED. It matched `*c07*.mp4` when the card already carries
  `page`, and a clip is that page's stem. It now asks `episode.json` first; the glob
  stays as a fallback for older episodes and SAYS SO when it fires. Control: two files
  matching `*c07*` (a headline containing "c07" is all it takes) — before, that halted
  claiming *"most likely C7 is marked bespoke"* about a card that had rendered perfectly.
- ✅ **`heygen_video_id`** — fixed earlier in the batch (`a95e4a8`): resolved once, then
  WRITTEN DOWN, and a halt rather than a silent pick when two renders share a title.
- 🟡 **`_hero_paths`** — NOT the fault E20 named, and the real one is worse. The file
  names (`hero-a.png` / `hero-b.png` / `hero.png`) are a fixed convention, not a guess
  about which asset. **The guess is that the FILE matches the LEDGER**: `docs/hero-jobs.json`
  is keyed on slot + prompt_sha (E16), and nothing checks that the png on disk came from
  the prompt currently in `episode.json`. That is the EP15 fault in its original form —
  *"a status field, a fresh mtime, a byte count and a 'completed' job all said the images
  were new; only the unchanged balance told the truth."* **Deliberately not attempted in
  this batch:** it touches the spend path, and getting it wrong either re-serves a
  rejected cover or spends ~4 credits saying so. It needs its own controlled run.
- 🟡 **`broll_registry_check`'s `broll-[a-z0-9-]+` regex over prose** — reads TARGET
  NAMES out of the script's text. There is no id to use: the b-roll target IS its name,
  chosen when the prompt is written. Making it an id means giving b-roll entries ids in
  `episode.json` and referencing those — a schema change with no fault behind it yet.
  **Left alone, on the standard's own rule: take an item off against a REAL fault.**
- 🟡 **the b-roll job map keyed on target NAME in `build_state.jobs`** — same shape as
  above and the same answer. It is keyed on a name that is itself the identifier, and
  the double-spend guard already keys on `jobs[clip].job_id`, which IS an id.
- ✅ **`episode_dir()` (E18)** — already resolved by NUMBER with a regex anchored to
  `PP-EP<nn>` and guarded by tests (`test_no_hardcoded_episode_paths`, and the
  single-digit/two-digit cases in the preflight suite). Nothing to do; re-verified.
- ✅ **`midroll_window`'s folder scan** — checked, and it is ALREADY RIGHT: it globs
  `PP-EP*/docs/spoken-words.txt` but orders by EPISODE NUMBER via `_ep_num`, with its
  own docstring explaining why ("PP-EP98 is a test folder sitting beside the real
  episodes; mtime ordering would drag it into every real episode's window"). The glob
  only enumerates; identity comes from the number. Nothing to fix.
  🔴 **BUT THE CHECK FOUND SOMETHING ELSE, AND IT IS FAULT #2:** `midroll_window` exists
  TWICE — in `qc_episode.py` and in `render_ready.py` — and the two copies **have
  already drifted** (different docstring, different import placement). Cosmetic today;
  it is one lookup in two places, so the next real edit reaches one reader. **Not fixed
  here:** extracting it is a shared-module refactor across the QC path and the
  render-ready path, which is a regression surface out of proportion to a batch item.
  Logged as its own thing rather than folded in silently.

📌 **The honest summary: 4 of 7 need nothing further, 2 have no id to use and no fault
behind them, and 1 is real and deliberately deferred** — `_hero_paths` against the
ledger, because it sits on the spend path and getting it wrong either re-serves a
rejected cover or spends ~4 credits proving it. Plus one NEW finding the sweep turned
up: two drifting copies of `midroll_window`.

## ✅ BEFORE-EP20 #9 — LANDED. A CARD TYPE IS NEVER REQUIRED BY PRECEDENT.
**(Jodie's ruling, 9 Aug 2026: there is NEVER a requirement for a bar chart.)**
E26 walks every key path in `episode.json`, and a key both reference episodes carry is a
CONVENTION whose absence is a BLOCKER. Card content is walked too — so because both
references happened to use a `bars` card, an episode whose article has no comparison to
draw was told *"the whole `cards[].content.bars[]` block is absent"*. **The only way to
clear that is to invent a bar chart.** A gate that can only be satisfied by making
something up is worse than no gate.

**AND IT HAD A SIBLING**, found by asking rather than by waiting for it to bite:
`cards[].rail` is per-card optional furniture too, so an episode with no numbered spine
was blocked for having no position rail. Fixed as a CLASS, not an instance —
`cards[].content`, `cards[].trace` and `cards[].rail` are a card's own shape, chosen
from the article, never inherited from another episode.

⚠️ **ONLY THE *MISSING* TEST IS RELAXED.** A key both episodes carry at incompatible
types still blocks: that is two cards using the same block and disagreeing about it,
which no per-card freedom excuses. And card content is still guarded by the RIGHT
authority — each block's own `required`/`optional`/`enum` schema through
`author_cards.validate()`, plus `check_trace` and `check_job` — rather than by what a
different article happened to need.

📋 **Control-first:** with the exclusion disabled, 2 of the suite's 20 cases fail, naming
the exact bar-chart and position-rail blockers. Two further cases guard the other
direction: a genuinely missing top-level block and a type clash must both still block,
so the exclusion cannot quietly widen into "E26 switched off".
📌 **EP19's own C6 bar chart was checked and is GENUINE** — it traces to the article's
printed staking table (3 / 1.5 / 1 units, "stakes gradually diminish as each week goes
by"), so EP19's cards were left alone.

## ✅ BEFORE-EP20 #3 — LANDED. THE FIDELITY GATE RECOGNISES, IT IS NOT TOLD TO IGNORE.
**(EP19, 9 Aug 2026.)** `check_fidelity` compared the article against the body's **bare
`<p>`** paragraphs only, so an article line the body sets as a HEADING read as a
paragraph that had been dropped. The sanctioned answer was `omit_paragraphs` — and
declaring a heading "omitted" **tells the checker not to look for it**. EP19 ended with
seven declarations, five of them verified BY HAND, which is exactly what a gate replaces.

**NOW IT RECOGNISES BOTH SHAPES AND VERIFIES EACH:**
- an article paragraph reproduced as a HEADING is satisfied only when the words are
  IDENTICAL (the article's `**bold**` markers are its own markup, not part of the
  words). This generalises past Jodie's brief — it also covers the *original* case, the
  article's headline line set as `h1.section`, which is why **EP19's `omit_paragraphs`
  is now EMPTY**;
- a markdown-table paragraph is satisfied by the FIGURE that renders it, cross-checked
  against that card's own `content` in `episode.json`: every number the table states and
  every word of every cell must be there.

🔒 **AND THE HOLE IS SHUT FROM THE OTHER SIDE:** declaring a paragraph the body actually
reproduces is now itself a HALT. `omit_paragraphs` means only "deliberately left out".

📋 **Control-first, seven new cases, each good case paired with its near miss:** a
heading one letter wrong (`A SUB HEEDING`) still halts and the message shows the exact
difference; a heading dropped entirely halts and says what to do instead; a table whose
figure's card has one number wrong is NOT accepted as carrying it.
⚠️ Two bugs found by driving it rather than reading it: the cell comparison squashed
punctuation on one side only, so `2nd-last` was hunted for inside `2nd-laststart` and
never found; and the near-miss message used `closest()`, which compares WORD LISTS and
scored a one-letter heading typo at 0.40 — reporting "no such heading" about a heading
on the page. Both now use one normalisation and character-level distance.
📌 Regression: EP16, EP17 and EP18 all still pass unchanged, and the suite went from
**30 pass / 1 pre-existing FAIL to 38 pass / 0**. That red case had asserted the
opposite of the documented contract ever since the `--force` trap was closed — it
expected a hand tweak to a page still carrying the `PP-GENERATED` marker to survive,
while the marker itself says *"To take this page over by hand, delete this line."*
Rewritten to assert the real contract rather than left red.

## ✅ BEFORE-EP20 #4 — LANDED. A `matrix` BLOCK, SO A GRID NEVER NEEDS HAND-AUTHORING.
**(Jodie, 9 Aug 2026: "the 2nd hand-authored table in 5 episodes, so it's worth doing.")**
EP15 C12 and EP19 C12 were both written by hand because no block drew *n* columns by
*m* rows with BOTH AXES LABELLED. EP19 C12's own note is the argument: `steps` gives
three rungs reading "9 / 6 / 3" with the column headings gone, so a viewer cannot tell
which figure belongs to which run; `slate` caps at four cells against nine; `chips`
flattens it into a row. And a hand-authored page gets NOTHING for free — it must
remember `pp-anim.js`/`ppInit` or `render_card` waits 60s on `window.ppDuration` and
gives up silently, and autofit will not touch it (no `PP-GENERATED` marker).

**THE ACTUAL WORK WAS THE NESTED EACH, exactly as the note predicted.** `expand_each`
was one non-greedy regex, so with a loop inside a loop `(.*?)` stopped at the INNER
`<!--@endeach-->` and the outer region ended in the middle of itself. It is now a
depth-counting parser; inside an item, `<!--@each ITEM.field-->` walks that item's own
list with `{{CELL}}` and `{{J}}` — deliberately different tokens from `{{ITEM}}`/`{{I}}`
rather than shadowing them.

🔴 **AND A HOLE FOUND WHILE BUILDING IT, NOT AFTER.** `walk_values` did not recurse into
a list held by an item, so `rows[].cells[]` — the grid's nine actual numbers — were
yielded as a single LIST, which `check_trace` skips because it only inspects strings.
**The block would have shipped nine untraced figures on a card whose entire purpose is
nine figures, with every gate saying yes.** Fixed in the same commit.

**THE ONE RULE A MATRIX HAS:** every row must have exactly as many cells as there are
columns. A short row does not look broken — it silently shifts every value one column
left and states something the article never said.

📋 **Controls:** a short row halts; a cell figure with no traced sentence halts; all nine
cells are proved visible to the trace walk; and the OLD one-level regex is run against
the real template and must produce a MANGLED page — otherwise the new parser is not what
is making this work.
📌 **Regression, the strong kind:** every card of every episode on disk was re-rendered
and compared with the page that shipped — **83/87 byte-identical, and the same 83/87 on
the unmodified baseline**, so the rewrite changes nothing that already existed. (The
four are EP13 pages predating the position rail's addition to the frame.) EP19's C12
renders through the block identically to the hand-authored page and passes `card_check`.
⚠️ **Noticed in passing, NOT fixed:** `write_autofit` removes the previous measured
block but not the newline after it, so each pass leaves a blank line — EP19 C8 carries
nine. Cosmetic, but it means a fitted page never equals its own freshly-rendered
definition. Logged here rather than folded silently into an unrelated commit.

## 🔴 THE BOARD ASKS FOR WORDS THE MACHINE STILL OWES **(Jodie, 9 Aug 2026, on EP19)**
> **A queued episode with NO SCRIPT YET shows the "YOUR TURN — WORDS" chip and the
> Words Gate.** Jodie is being told to act at the exact moment the MACHINE owes her the
> script — the drafting pass has not run, or has run and is still writing.

**It should read "Writing the script… no action needed yet" until a script exists, and
flip to YOUR TURN — WORDS the moment one does.**

**Why it matters more than a wrong label:** this is the *Job-5 fault* — a YOUR TURN chip
with nothing to do. A queue that cries turn-taking when there is no turn to take is a
queue she stops believing, and the one time it means it she will scroll past. It also
sends her looking for a Doc that does not exist yet.

**The state to key on already exists on the row** — `script_snapshot` (and
`script_doc_url` for the older shape). The gate is asking `title_approved && script_read`
(`app.js` ~line 68 / ~529) and never asking whether there is anything to READ.
📌 **Derive it, do not add a status.** A fourth state in the 10-status contract to say
"the machine is writing" would be a second source of truth about the same fact; the
presence of a script is the fact.

⚠️ **AND SAY WHICH MACHINE STEP IS OWING**, or the new message is only a nicer lie: if
the drafting pass has HALTED (no capture — see the root cause below), "Writing the
script…" is false. The run log knows; the board does not. **A19 applies: that halt is
the studio's, not the operator's**, so the card should say *"the studio is preparing
this one"* rather than badge her with a job she cannot do.

## 🔴 NOTHING TURNS A `source_url` INTO A CAPTURE **(found chasing EP19, 9 Aug 2026)**
EP19 sat `queued` for six minutes with a perfectly good `source_url` on the row and the
engine idle-but-healthy. The drafting pass ran on time, reported plainly *"The article
for this episode hasn't been captured yet, so there is nothing to write the script
from"*, and stopped — correctly.

**The hands-off chain is `source_url` → [MISSING] → drafting pass → fidelity gate →
seat.** `assert_capture_for_script` is a PRECONDITION; nothing CREATES the capture.
`providers.py` says so out loud: *"nobody holding a browser can capture an article"* —
so it is the studio's step, by design (`DESIGN-the-pre-claim-drafting-pass.md` §4), and
on EP18 it was a scratch script run by hand.

**For "EP19 with zero human pastes" this is THE remaining hole.** Automating it is a
design decision, not a tidy-up: the capture becomes the article of record that the
fidelity gate, `check_trace` and the e-book body are compared against forever, and
building EP19's by hand tonight needed four judgements a naive fetch would have got
wrong — paragraph breaks that are `<br><br>`, sub-headings inline in `<b>`, a real
`<table>` that must stay a table (the EP16 lesson), and where the article ends before
the site furniture begins. **Jodie's call, with those costs on the table.**

---

# 📥 CARRIED IN WITH THE MOVE — two live items that were elsewhere in the checkpoint

## 🔴 THE RUN LOG SHOULD NOT DEPEND ON SOMEBODY REMEMBERING **(Jodie, 5 Aug 2026)**
> **Her question: *"do we need a fix for the fact that the run log did not just
> automatically happen?"*** EP16's exists because Cowork asked for it. **Twice.**

> ## THE SPLIT: **THE FACTS SHOULD BE AUTOMATIC. THE FINDINGS SHOULD NOT.**

**The engine already knows nine tenths of a run log** — every step with its timings, every
flag with its exact text, every retry, every spend, every byte count — **and writes all of
it to `engine-<date>.log`, where nobody assembles it.**
**THE FIX: the engine emits a factual run-log SKELETON per episode, as it goes, with the
halts in it.** Writing the log then stops being *"remember to write a document"* and
becomes *"add the findings to the file that is already there"*.
> ⭐ **SELF-LIMITING, which is why it will not become bureaucracy:** a boring episode
> produces a boring file **for free** and nobody writes anything.

**RANKED BELOW THE CARD-PIPELINE WORK — it does not make a wrong video.** But it
**compounds at 300 episodes**, and it is **the mechanism by which we learn anything at
all**: every rule in `PP-STANDARDS.md` and every fault in `CLAUDE.md` came out of somebody
writing down what happened, and that has been voluntary every single time.
*(EP17's run log was written by hand again, 6 Aug. Third episode running.)*

## ⚠️ `mock-episode` CREATES A TICKET THE REAL ENGINE WILL CLAIM
`claim_next()` does not filter on `created_by`, so a live `run --watch` engine picks up a
mock ticket. It flagged harmlessly when found — the mock Doc URL 404s at `script_sync`,
**before anything can spend** — but **a mock ticket with a readable Doc would walk into the
paid steps.** **One filter on `created_by` in `claim_next`.** Small; not urgent.

---

# 📋 THE LIST — everything noticed, NOT a plan

> ## ⚠️ READ THIS BEFORE YOU READ THE LIST. Jodie, 4 Aug 2026: **"We had it working!"**
> **A list of everything anyone noticed, stacked up as if it were all equally urgent, is
> not a plan.** I produced a 12–14 day pre-EP16 plan off this list and she cut it to
> ~3.5 days by asking one question: *which of these actually caused a fault?*
> **EP15 halted nine times from THREE causes** — and the three fixes are landed.
> **Everything still on this list waits for the day HUGH operates, and that day is not
> this month.** Take items off it against a real fault in a real episode, never because
> the list is long. *A machine that spends more effort proving itself correct than making
> episodes has stopped being a studio.*

**Bundle C — the create brain.** Kills stops 1, 3, 10, 11. Includes setting the script
Doc's sharing at creation (stop 2's real fix — **no Drive service account: a new secret
on a public repo is not a trade worth making**).

**Bundle E — the guards:**
- 🔴🔴🔴 **E28 — A MANUAL RAIL EDIT CAN BE SILENTLY OVERWRITTEN BY THE RUNNING ENGINE,
  AND BOARD BUG 5 MOVES UP BECAUSE OF IT.** *(EP15, 4 Aug 2026.)*
  `assemble_passB` and `self_qc` were removed from `build_state.steps` to force a
  rebuild after C10's card was fixed. **The read-back showed them gone.** The engine
  held a live lease, its own `ctx.save()` wrote the old state back, and **nothing
  anywhere said so**. It then ran `self_qc` against the **already-superseded** video,
  marked every remaining step done, and parked EP15 at **`awaiting_approval` with a
  stale film**. *Only comparing `FINAL.mp4`'s mtime (18:32) against C10's clip (19:06)
  caught it.*
  > **THE READ-BACK WAS A PROXY. The artefact is the file on disk.**
  **The root cause is board bug 5: there is NO SAFE WAY TO SEND AN EPISODE BACKWARDS.**
  Every attempt is a hand-edit racing a live writer. **Tonight it stopped being a
  nuisance and became the thing that nearly walked a stale video into Jodie's approval
  gate.** *Board bug 5 moves up the list.*
  **Interim discipline until it is fixed:** refuse to write while a lease is live —
  check `claimed_by` and `lease_until` first — and **prove the effect with a NEW OUTPUT
  FILE whose mtime is later than the input you changed**, never with a status field.
  > ### 🔴 THE DEAD ZONE — the mechanism, found the same night
  > There are **exactly two** ways an episode re-enters the engine:
  > `claim_next()` → `status=eq.queued` · `reclaim_stale()` → `claimed_by=not.is.null`
  > **AND A WORKING STATUS WITH NO OWNER MATCHES NEITHER.** EP15 sat at `assembling`
  > with `claimed_by: NULL` — **unreachable by anything, forever.** The engine was alive
  > (pid 76064) and had logged nothing for 48 minutes; the episode was simply invisible
  > to it. *My own reset created that state, by clearing steps and status without
  > realising the engine had released ownership when it parked at `awaiting_approval`.*
  > **RECOVERY, using the engine's OWN crash path rather than an invented one:** set
  > `claimed_by` to a name that is not the live worker and `lease_until` to the past —
  > which is what the episode factually is, one whose worker went away mid-assembly —
  > and `reclaim_stale()` takes it back. *It worked in under a minute:
  > `reclaimed a stale-leased episode PP-EP15 at assembling`.*
  > **THE FIX BELONGS IN THE ENGINE:** an owner-less episode in a WORKING status is
  > always a fault, and the idle loop should adopt it rather than ignore it.
- 🔴 **E19c — A WATCHER THAT WAITS ON AN OUTPUT MUST ALSO WATCH THE THING THAT MAKES IT.**
  *(Third sighting of E19's other half, and the sharpest.)* The rebuild watcher was
  correctly waiting on `FINAL.mp4`'s mtime — **and would have waited all night**, because
  nothing was producing it. **A dead engine and a slow one look identical from the file
  system.** Watch the producer (claim, heartbeat, current step) alongside the artefact,
  and say plainly when the producer is not running.
- 🟡 **E37 — BATCH 5 (HEYGEN FETCH IN THE BACKGROUND) IS DEFERRED PENDING MEASUREMENT.
  NOT DROPPED, NOT AN OVERSIGHT.** *(18 Aug 2026. Jodie: measure first.)*
  The plan said ~8.3 min an episode, and the `if hj.get("file"): skip` seam does exist.
  **The seam is not what the plan assumed.** `poll_heygen` is not a fetch — it does five
  things: `_heygen_fetch` (the download), `trim_master_lead_in` (**mutates the master**;
  EP30 trimmed 5.94s), `align_to_script` (**runs WhisperX forced alignment**), the
  **180 kbps floor gate** and the **missing-`_audio_kbps_floor_why` gate**.
  🔴 **TWO OF THE FIVE RAISE `EngineFlag` — human gates inside the thing we proposed
  moving to a background thread.** That is the thumbnail lesson exactly (and the second
  time in one day that "independent" work turned out to raise a flag).
  **WHAT IS ACTUALLY SEPARABLE:** the DOWNLOAD only. Split it as the alongside stream is
  split and the side thread may fetch, while trim, align and both gates stay on the main
  thread. **So the saving is the TRANSFER, not 8.3 minutes** — and nobody knows what
  fraction that is, because the step is timed as ONE number.
  ⚠️ **AND ALIGNMENT WOULD CONTEND WITH `cards_render` FOR CPU.** The overlap window is
  the building phase, whose long pole is the card capture — ~260 CDP screenshots per
  card. **Batch 6 parallelises exactly that, so it makes the contention WORSE.** Measure
  AFTER batch 6 has landed, or the number describes a machine we no longer have.
  **THE DECISION WAITS ON:** EP31's `poll_heygen` split timing (download / trim / align /
  gates — instrumented 18 Aug, free), measured on post-batch-6 code.
  ✅ **AND IF THE NUMBER SAYS ALIGNMENT DOMINATES, THIS BATCH SHRINKS TO ALMOST NOTHING
  OR IS DROPPED — AND THAT IS A GOOD OUTCOME.** A batch closed with a verdict is
  finished. "Everything, then automate" is satisfied by a batch that was measured and
  rejected; it is not satisfied by one that was guessed at and built.
- 🟢 **E35 — THE ONE CAPTURE WITH NO LIST PROVENANCE IS THE ARTICLE THE SECTION EXISTS
  BECAUSE OF.** *(Found 18 Aug 2026 while sweeping the captures for batch 4.)*
  **EP25's capture has no `## LISTS` section at all.** EP25 is *"50 Great Staking Ideas"* —
  an `<ol>` of exactly 50 `<li>` that the capture flattened into ONE 3,900-word paragraph,
  the e-book reproduced faithfully, and the fidelity gate passed. **That fault is why the
  LISTS section was added.** It was added *after* EP25 was captured, so the article that
  earned the section is the only one without it.
  🔴 **JODIE'S RULING (18 Aug): BACKLOG IT, DO NOT TOUCH IT.** EP25 is **published**, and
  *a shipped episode is not touched*. There is no live value in fixing it either: the
  section only matters at **e-book-writing time**, and EP25's book is long done.
  **Logged for the irony and for the next person who sweeps the captures and finds a gap
  where they expect a section — it is not damage, it is chronology.**
- 🟠 **E36 — A BULLETED LIST IS INVISIBLE TO THE NOTE, AND THERE IS NO LEGAL WAY TO PRINT
  ONE AS A LIST.** *(Found 18 Aug 2026, immediately after batch 4. NOT a regression — it
  has always worked this way, and nothing is broken today.)*
  `numbered_runs()` reads `^\d+\. `, so the LISTS note describes NUMBERED lists and is
  **silent about `<ul>`**. An article with bullets gets *"No numbered list in the article
  body"* — true, and it tells the e-book writer nothing about a list that IS there.
  **WHO HAS THEM:** **EP14** (3 bullets — system rules) and **EP20** (6 bullets — the
  Hong Kong points). *(EP25's single `*` is a footnote marker — "Indicates extract from
  Commonsense Punting" — not a list.)*
  **WHY NOTHING HAS BROKEN:** `<ul>` **is not in the e-book tag vocabulary at all**
  (`TAGS_OK` carries `ol` and `li`, no `ul`), so a bulleted list cannot be expressed as a
  list. EP14 and EP20 reproduced their bullets as ordinary paragraphs carrying the `•`/`*`
  character verbatim, and the fidelity gate is satisfied because the capture emits each
  bullet as its own block. **It works. It is just silent.**
  ⚠️ **THE TRAP, AND IT IS THE FAMILIAR SHAPE:** `li` IS allowed on its own. A writer who
  reaches for `<li>` for bullets gets `check_list_shape` seeing items with no numbered
  paragraphs, and the halt reads *"the source article has no numbered list in it. A list
  the article does not print is structure we invented."* **That would be factually wrong**
  — the article does print a list — and it sends the writer to delete a list the page has.
  Same shape as EP26's charts: *a rule that leaves no legal way to do the right thing has
  already chosen the wrong one.*
  **WHEN IT IS ITS TURN:** have the note describe bulleted lists too, and decide whether
  `<ul>` joins the vocabulary — **on the tightest possible terms**, as the chart table did.
- 🔴 **E34 — `publish_artefact` KEYS ON THE FILE'S NAME, AND THE CLOSE-OUT RENAMES THE
  FILE. SO ANY RE-PUBLISH AFTER PUBLICATION MINTS A NEW URL AND LEAVES THE OLD ONE LIVE
  AND WRONG.** *(Found 18 Aug 2026 while repairing EP30. LATENT, not a one-off.)*
  ```python
  def publish_artefact(self, ep, local):
      return self._publish_asset(local, f"{ep_folder(ep)}/{local.name}")
  ```
  `_publish_asset` sends `x-upsert: true` to that key, so it replaces **in place** — as
  long as the key is the same. But the **stage-8 close-out renames the folder AND the
  files on publish**: EP30's `PP-EP30/output/PP-EP30-ebook.pdf` became
  `PP-EP30-Feed-On-The-Favourites/output/PP-EP30-Feed-On-The-Favourites-ebook.pdf`.
  `ep_folder()` still returns the OLD folder name, so the key becomes
  `PP-EP30/PP-EP30-Feed-On-The-Favourites-ebook.pdf` — **a different object, a different
  URL**, while the URL on the rail and in anyone's hands goes on serving the old bytes.
  **THE DANGEROUS PART IS THAT IT LOOKS LIKE SUCCESS.** The upload returns 200, the
  visibility check passes, a fresh URL is written to the rail, and the stale one is never
  mentioned. Only `verify_published.py` against the ORIGINAL url would notice.
  **WORKED AROUND FOR EP30, NOT FIXED:** the corrected PDF was published to the EXISTING
  key by hand (`_publish_asset(pdf, "PP-EP30/PP-EP30-ebook.pdf")`), so the live link was
  replaced in place and nothing stale was left behind.
  **THE FIX, WHEN IT IS ITS TURN:** derive the object key from something that does NOT
  change at close-out — the episode NUMBER and the artefact KIND (`PP-EP30/ebook.pdf`),
  or reuse the key already recorded on the rail when one exists. Either way a re-publish
  must land on the URL that is already out in the world. ⚠️ Changing the scheme for
  EXISTING episodes would move their live URLs, so new episodes and old ones need
  different answers — reusing the recorded key handles both.
- 🟠 **E33 — IS EP30'S COPY ERROR ONE ARTICLE OR TWENTY? A READ-ONLY ARITHMETIC SWEEP
  OF THE SOURCE ARTICLES WE ALREADY HOLD.** *(Raised 18 Aug 2026. NOT STARTED — Jodie
  asked for it to be raised, not run.)*
  EP30's article prints *"$18.10 profit and 33 per cent POT"* on 103 bets. $18.10/103 is
  **17.5%**; the 33 is the STRIKE RATE from three words earlier, copied into the POT
  slot. Every other figure in that article checks out exactly — two days' bets, winners,
  profits and both daily POTs — so it is one slip, not a sloppy article.
  **WHY IT MATTERS BEYOND EP30:** these are 2008 articles and **~270 episodes are still
  to come**. The correction mechanism being designed for EP30 (`ebook.corrections[]`,
  §0a-ii amended) is either a one-off or a thing PP uses for years, and **nobody knows
  which**. A sweep of the ~20 source articles in `G:\My Drive\PP Videos\docs\` would
  say — it is read-only, it spends nothing, and it touches no shipped episode.
  **WHAT IT WOULD DO:** for each article, find sentences carrying a profit, a bet count
  and a percentage, recompute, and list only the ones that disagree with the article's
  own figures — using the TRUNCATION convention the articles themselves use (EP30 prints
  10.7 for 10.769, which rounds to 10.8; that single data point is what settles it).
  ⚠️ **A FINDING HERE IS ABOUT THE ARTICLE, NOT A LICENCE TO EDIT ONE.** §0a-ii still
  stands: reproduced, disclosed, and corrected only where Jodie and Hugh say so, per
  episode. And **a shipped episode is not touched** — a finding on one is logged CLOSED.
  🔴 **AND THE SWEEP IS WORTH MORE SINCE A27 WAS AMENDED (18 Aug, same day it was made).**
  The disclosure is now WAIVABLE, so **every article with a copy error has a path to a
  SILENT correction** — a book printing a figure `practicalpunting.com.au` does not, with
  nothing on the page saying so. The question this sweep answers is therefore no longer
  just *"how many articles?"* but **"how much silent divergence between the e-books and
  the website are we creating?"** That number is worth knowing BEFORE the pattern
  repeats across ~270 episodes, not after.
- ✅ **E32 — LANDED 18 Aug 2026 (batch 3).** Both safe changes, and **neither guesses**:
  1. **`author_thumbnail.inherit_hero_focus()`** — an unset `thumbnail.hero_focus`
     inherits `title_card.hero_focus` (same hero, same 16:9 window) and **says so in the
     build output**. An explicit thumbnail value is never overridden; with nothing to
     inherit, nothing is invented and `REQUIRED` still speaks.
  2. **`providers.crop_report()`** — the placement flag now MEASURES. On EP30 it says:
     *"this hero is PORTRAIT (1696×2528). A 1.78:1 window on it is 954px tall, so
     1,574px — 62% of the photograph — is NOT in the picture"*, then gives the band at
     the current value, at 0/50/100%, and that each 1% moves the window 15.7px.
     🔴 **It never says where the horses are.** A wrong automatic crop is worse than a
     wrong default — the default meets the review that already exists and a clever guess
     does not. The human still decides; they stop deciding blind.
  📋 Held by `engine/test_e32_crop.py` (9 cases), including the two controls that matter:
  **it must not claim to know the subject**, and **an explicit value must win**.
  ⚠️ **STILL OPEN, AND IT IS JODIE'S CALL, NOT A CODE CHANGE:** why the hero is portrait
  at all. The cover heroes are generated for the e-book cover, which IS portrait, and the
  title card and thumbnail then crop 16:9 out of it. **A hero commissioned in both shapes,
  or framed for the crop, removes the class rather than guarding it** — that changes what
  is generated, so it is a prompt decision and hers.
  *(Original entry kept below — it is the case that justified the work.)*
- 🔴 ~~**E32 — `center` IS THE WRONG DEFAULT CROP FOR A PORTRAIT HERO, AND IT COST TWO
  HUMAN CATCHES ON ONE EPISODE.**~~ *(EP30, 17 Aug 2026.)*
  EP30's picked cover hero is **1696 × 2528** — portrait. A 16:9 window on it is
  **954px tall**, so **1,574px of the photograph is discarded**. At the default
  (`center` / `center 50%`) the visible band is **y 787 → 1741**. The field of eleven
  horses occupies **y 1751 → 2098**.
  > ### THE CROP MISSED THE HORSES BY TEN PIXELS. Twice.
  Once on the **title card** and once on the **thumbnail** — two separate steps, the same
  hero, the same default, and **both were caught by Jodie's eye**, not by the studio.
  `center 72%` frames the field on both (verified: the authored pages are byte-identical
  to the previews she approved). EP12 needed `center 62%` for the same reason.
  **THE OBVIOUS FIX IS THE WRONG ONE.** "Detect the subject and crop to it" means guessing
  from pixels, and **a wrong automatic crop is worse than a wrong default**, because the
  default is caught by the review that already exists and a clever guess is not. Two
  changes that are safe and do not guess:
  1. **CARRY THE VALUE ACROSS THE ASSETS.** Both cards are 16:9 and use the SAME hero, so
     an unset `thumbnail.hero_focus` should inherit `title_card.hero_focus`. Jodie fixed
     the identical fault twice on one episode; once is enough.
  2. **MEASURE, AND SAY SO IN THE FLAG.** The placement review already stops for a human;
     it just tells them nothing. It knows the hero's dimensions and the window — so it can
     say *"this hero is portrait: a 16:9 window shows 31%–69% of it and discards 62%"* and
     name the value that would move the window down. **The human still decides**; they
     stop deciding blind.
  ⚠️ **AND ASK WHY THE HERO IS PORTRAIT AT ALL.** The cover heroes are generated for the
  e-book cover, which IS portrait; the title card and thumbnail then crop 16:9 out of it.
  A hero commissioned in both shapes, or framed for the crop, removes the class rather
  than guarding it — that is a b-roll/cover PROMPT question, and it is Jodie's call
  because it changes what is generated.
- 🟠 **E31 — "THE LATEST CUE THAT STILL FITS" READS AS AN INSTRUCTION TO GO LATER, AND
  IT MEANS THE OPPOSITE.** *(EP29, 16 Aug 2026. Jodie: "worth making that message
  clearer for Hugh's sake.")*
  The shot-map halt ends: *"beat 9 is 14.40s and the card needs 13.00s, so the latest cue
  that still fits starts at 154.91s."* Every word of that is true, and it is a **CEILING**
  — the cue must land at or BEFORE 154.91. Read quickly it sounds like a floor, and the
  operator goes hunting for a cue at or after that time, which is exactly the set of cues
  that CANNOT work. It sent this session's first reading the wrong way, and the person it
  is written for does not have a shot map to cross-check against.
  **THE FIX IS WORDING, NOT ARITHMETIC** — the number is right and nothing about the
  placement logic needs to move. Say the direction and the deficit in the operator's own
  terms, e.g.: *"C7's cue is spoken at 158.96s and must move EARLIER — to 154.91s or
  before — because the card needs 13.00s and beat 9 ends at 167.91s. It is 4.05s too
  late. The only earlier cue in this beat is 'Here's Roy again…' at 153.51s."*
  ⚠️ **And name the ONE candidate when there is only one.** The tool already knows the
  beat's spoken units; listing the cues that DO fit turns a decision into a choice, which
  is what the halt is for. *(Deliberately not done during EP29's build: it is engine code,
  and changing it would have exited a running engine mid-episode.)*
- 🟠 **E30 — AN OLD ARTICLE'S "TODAY" IS SPOKEN AS IF IT WERE TODAY, AND ITS "I" IS
  SPOKEN AS IF IT WERE GORDON.** *(Found by sweeping EP29's approved draft, 16 Aug 2026.
  Noted by Jodie as a FUTURE systemic improvement — EP29 itself ships as approved.)*
  These articles are twenty and thirty years old, and the writer reproduces their words
  faithfully — which is right, and is exactly what §0a asks for. Two classes come with
  it that no gate can see, because **every word is the article's own**:
  1. **THE ARTICLE'S PRESENT TENSE.** EP29 says *"introduced some **sixty years ago** by
     the late Rufe Naylor"* — the 1997 article means **1937**, and a listener in 2026
     hears 1966. Also *"the professionals **of today**"* and *"One pro told me
     **recently**"*. The episode does open with *"back in May nineteen ninety-seven"*,
     which carries most of it; the bare figure is the one that drifts.
  2. **THE AUTHOR'S FIRST PERSON.** The draft frames it well in places — *"Here's Roy
     again"*, *"He calls it the Super Target Plan"* — and elsewhere slides into Roy's
     "I" unframed: *"Many readers have contacted me **since I joined the team**"*,
     *"We have stated many times before **in this magazine**"*, *"the aim of **this
     article**"*. In Gordon's mouth those say he joined the team and is presenting a
     magazine.
  **WHY IT IS A BRIEF PROBLEM AND NOT A GATE PROBLEM.** A fidelity gate compares the
  script to the article and both classes PASS, correctly — the words are quoted exactly.
  What is wrong is the FRAME they are spoken in, and that is a decision the writer makes
  while drafting. So the fix belongs in `pp-episode-script`'s brief — say the year when
  the article says "today", and keep the author's "I" attributed — not in a checker.
  ⚠️ **AND IT IS NOT A LICENCE TO PARAPHRASE.** §0a still governs: the words stay the
  article's. This is about ATTRIBUTION and DATING around them.
- ✅ **E29 — LANDED 18 Aug 2026 (batch 2).** `TEST_EP_FLOOR = 9000` in `rail.py`, with
  `NOT_A_TEST` added to **both** doors: `list_queued()` (which feeds `claim_next`) and
  `reclaim_stale()` — the one caught in the act. Held by
  `engine/test_suite_tickets_are_not_food.py` (4 cases).
  ⚠️ **THE FIX PROPOSED BELOW WAS CHANGED ON PURPOSE, AND THE REASON MATTERS.** The
  entry says to key on "a `9xxx` test range … already the convention in the fixtures".
  The fixtures use **PP-EP96, 97, 98 and 99** — and **the plan is 300 episodes**, so
  those four are real episodes nobody has made yet. A prefix rule would have been green
  on the day it landed and would have quietly stopped the engine claiming four real
  episodes somewhere around next year. It keys on **`ep_number >= 9000`** instead: a
  number, not a shape, clear of 300 by any margin that matters. **NULL stays claimable**
  — a real ticket that has not been given a number yet must never be filtered out by a
  guard aimed at the suite.
  *(The original entry is kept below — it is the case that justified the work, and the
  proposed fix is kept as the record of what a plausible answer looked like.)*
- 🟠 ~~**E29 — THE SUITE WRITES TO THE LIVE RAIL, AND THE LIVE ENGINE EATS ITS TICKETS.**~~
  *(Found 16 Aug 2026, during the tables/lists batch.)*
  `test_dead_zone.py` creates a real rail row at a working status with a dead lease —
  **which is precisely the shape `reclaim_stale()` hunts for** — so a running engine
  takes it mid-test. Caught in the act, with the engine's own log as the evidence:
  ```
  [03:45:32] reclaimed a stale-leased episode PP-EP9019 at building
  [03:45:52] !! lost ownership of the episode (lease reclaimed) — stopping work
  ```
  `PP-EP9019` is the test's own synthetic ticket. The suite reported
  `dead zone: 2 passed, 1 failed`; the same test passes on its own, and passed in two
  earlier runs. **A gate that is green or red depending on what else is running is not
  a gate** — and the failure mode is the dangerous direction, because the natural
  reading of a red dead-zone test is "the dead zone is back".
  **THE WORKAROUND USED TODAY:** `python engine/stop_engine.py "<reason>"` before a full
  suite, `--release` after. It works and it is not a fix — it relies on whoever runs the
  suite remembering.
  **THE FIX, WHEN IT IS ITS TURN:** the rail-writing tests should use an episode-number
  range the engine's claim and reclaim filters EXCLUDE (a `9xxx` test range is already
  the convention in the fixtures, so the filter has something to key on), or a separate
  test table. Then the suite is honest with the engine running, which is how it will
  actually be run.
- 🔴 **E23c — THE STALE LABEL BECAME A SAFETY SURFACE.** `progress_step` read
  **"Waiting on you — four approvals"** while the episode was mid-rebuild with 16 of 18
  steps done. **The first two stale labels made Jodie think the machine had frozen. This
  one invited her to APPROVE A VIDEO WE KNEW WAS THE WRONG CUT.** *The label is not
  cosmetic.* Derive it, never store it — and never leave an approval prompt showing for
  an episode that is building.
- ✅ **E26 — LANDED 4 Aug 2026, `04da5fc`.** `engine/preflight_episode_json.py`, called
  from `step_audit_inputs`. **Keys+types catch five of the seven; a REFERENTIAL pass
  catches the `END` id and a SHAPE pass catches card-beats-on-WIDE.** Being QUIET was as
  much work as the diff: `_`-keys are never conventions, a missing BLOCK is separated
  from a missing leaf, blockers halt and the rest is merely named. EP15-as-shipped and
  EP14-judged-by-the-others both come back with **zero blockers**.
  ⚠️ **The shape pass asserts NO RATIO** — the framing is settled and a high WIDE count
  is not a fault; only ZERO is unlike every episode.
  📋 *16 tests, one per halt EP15 actually took. Two false positives were caught by the
  does-not-cry-wolf cases: an OPTIONAL field is not a type mismatch, and an empty list
  is a list of anything. Either would have fired on every episode from now on.*
  **Original entry kept below — it is the case that justified it.**
- 🔴🔴🔴 **E26 — NOTHING VALIDATES `episode.json`.** *(EP15, 4 Aug 2026.)*
  > ## SEVEN HALTS. ONE FILE. ONE EPISODE.
  `default_hold` · the `ask` TYPE · card-beats-on-WIDE · the `END` id ·
  `build.standing` · `midroll.dur` · `thumbnail.l1`
  **Every one found by running into it**, eighteen steps deep, hours apart, each costing
  a flag Jodie had to clear. **Every one a convention that EP11-EP14 all followed and
  that nothing anywhere states.** This is no longer an argument FOR the pre-flight — it
  is the whole case.
  **THE PRE-FLIGHT: diff the episode's `episode.json` against the LAST EPISODE THAT
  BUILT CLEANLY — keys, TYPES, and SHAPE — before the build starts.** *"Every previous
  episode put some card beats on WIDE; this one puts none"* is a sentence a diff could
  have produced before a credit was spent.
  ⚠️ **USE TWO REFERENCE EPISODES, NOT ONE.** A rule inferred from a single sample was
  wrong on all three axes an hour earlier (panel-push cells). A key is only a convention
  if BOTH references carry it.
  ✅ **DONE ONCE BY HAND ON 4 Aug** rather than discovering the eighth at the last step:
  17 keys missing against EP13 **and** EP14. Five were real — the whole `thumbnail`
  block — and filled. **Twelve are `build.*` tuning values whose CODE DEFAULTS equal
  what EP13/EP14 set**, and Pass A, Pass B and QC had already succeeded without them, so
  they were deliberately NOT filled: *a value you do not understand is not made safer by
  copying it.*
- 🔴🔴🔴 **E27 — NOTHING MEASURES A CARD AT THE SIZE IT IS ACTUALLY SHOWN. EP16.**
  *(EP15, 4 Aug 2026 — found by looking at a still, by nothing else.)*
  A **panel-push** card is chroma-keyed, **scaled to 810 wide (42%)** and dropped at
  `x=36, y=312`. `card_check` and `self_qc` **both measure the page at 1920**. EP15's C10
  used a **4-across slate**, giving each cell ~155px and body text at roughly **9px** —
  and it passed **17/17 plus QC** as a card nobody could read.
  > ## PANEL-PUSH BODY TEXT MUST REMAIN READABLE AT ITS COMPOSITED SCALE.
  **THE CHECK: render the card at 810 wide, measure the SMALLEST rendered text, fail
  below the threshold.** ⚠️ *A black-pixel test would have PASSED this — the pixels are
  not black, they are illegible.*
  **THE THRESHOLD: 11px, and here is exactly where it came from.** EP13 C8 bottoms out
  at ~14px composited; EP14 C5 at ~11px; both ship legibly. EP15 C10 at ~9px does not.
  **11px is the smallest text any APPROVED episode has actually used** — empirical, and
  it passes EP13/EP14 while failing EP15, which is the only test a threshold must meet.
  ⚠️⚠️ **BUT 11 IS NOT SACRED. It is computed from the CSS and a 0.42 scale factor, NOT
  read off rendered pixels. When E27 is built it MEASURES THE REAL THING, and if the
  number moves, the number moves. THE COMMITMENT IS TO THE METHOD, NOT THE VALUE.**
  🚫 **DO NOT WRITE "THREE CELLS, TWO LINES" INTO A STANDARD.** That was inferred from
  ONE sample and **the second sample killed it**: EP14 ships TWO cells with THREE-line
  values AND sub-lines. A count is a proxy; readability is the constraint. Cell guidance
  belongs in authoring notes as help for passing the check — never as the rule.
  ✅ *This makes the seventh convention the FIRST that cannot be silently forgotten.*
- ✅ **E22 — LANDED 4 Aug 2026, `04da5fc`.** `RealProvider._download_exact()`: read the
  stated size, compare after, refuse to promote, **name both numbers in plain English**.
  **Applied to the PAID Higgsfield clips and heroes too** — found by asking whether the
  fault had SIBLINGS rather than waiting for it to bite twice.
  🔬 **The 109 MiB boundary is STILL UNEXPLAINED and stays that way** — four re-pulls
  landed on exactly 114,294,784 bytes. The length check makes it LOUD, not understood.
  **Original entry kept below.**
- 🔴🔴🔴 **E22 — `_heygen_fetch` ACCEPTED A TRUNCATED DOWNLOAD AS THE MASTER.**
  *(EP15, 4 Aug 2026 — the whole two-hour false trail.)*
  ```python
  with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
      shutil.copyfileobj(r, f)      # no length check, EOF looks like success
  tmp.rename(master)                # promoted to THE MASTER regardless
  ```
  `urlopen` + `copyfileobj` **never compares against `Content-Length`.** A connection
  that drops mid-transfer ends the copy without raising, and the short file is renamed
  to `presenter-master.mp4`. **That is how 78,947,138 bytes became "the master" while
  the server had stated 114,395,315.**
  **THE FIX: read `Content-Length` before the copy, compare after, and refuse to rename
  on a mismatch** — naming both numbers. Nothing else changes.
  ### 🔬 THE 109 MiB BOUNDARY — logged as unexplained, on purpose
  Four separate re-pulls landed at **exactly 114,294,784 bytes = 109 MiB, to the byte**.
  The full file is 109.0959 MiB — it crosses that line by only **100,531 bytes**.
  **Four times on a round binary boundary is not a flaky line. Something in the chain
  has a fixed ceiling and I DO NOT KNOW WHERE.**
  *Best hypothesis, NOT established:* the re-pull used a **1 MiB read buffer**, so the
  transfer ended after the last WHOLE chunk and the final partial one was lost — which
  would make the boundary an artefact of my buffer size rather than a real cap. But
  attempt 7 succeeded with identical code, so it is not deterministic. **Candidates not
  ruled out: the CDN, the G: Drive virtual filesystem, Windows, or the client.**
  ⚠️ **At 300 episodes with bigger files this bites again — and next time there may be
  no stated byte count to catch it.** Whatever the cause, the LENGTH CHECK above makes
  it loud instead of silent.
- 🔴 **E24 — THE CODE'S OWN DEFAULTS CONTRADICT EACH OTHER, AND THE HALT CALLS IT
  "JODIE'S CALL".** *(EP15, 4 Aug 2026 — `derive_card_timings.py`.)*
  ```
  163:  return float(build.get("default_hold",   8.0))
  198:  min_hold  = float(build.get("min_card_hold", 10.0))
  ```
  **The default hold is BELOW the minimum hold, three lines apart in one file.** With
  nothing set in `episode.json`, EVERY non-hero card fails by construction — and the
  halt then asks a human to settle it, once per card. EP15 produced **seven identical
  "Jodie's call" lines to the decimal**, which is what a single wrong constant looks
  like when it is reported per-item.
  **EP13 and EP14 both SET `default_hold: 10.0` explicitly, so the broken default was
  never exercised.** EP15 was the first episode written without it. *Fault #2 (one
  source of truth) plus fault #0 (the machine asking a person for what it already
  knows).*
  **FIX: the code default must equal the floor, and a value that cannot satisfy its own
  check is a bug, never a question.**
- 🔴 **E25 — THE `ask` GUARD CANNOT SEE A WRONG TYPE.** `build.midroll.ask` must be a
  **LIST of two anchor phrases** (EP13/EP14 both are). EP15 had a **string**, so
  `ask[0]`/`ask[1]` were the CHARACTERS `'I'` and `'f'` from *"If you've found…"* — and
  the halt reported *"ask phrase not found in the SRT ('I' -> ok, 'f' -> MISSING)"*.
  The guard is `if not ask or len(ask) < 2` — **any string of two or more characters
  passes it.** The check built to catch a MISSING ask is blind to a MIS-TYPED one.
  *(Not the fuzzy-matching fault of E21 — a different failure with a similar smell.)*
- 📣 **E23 (operator's box, with board bug 7) — THE CARD WAS WRONG FOR TWO HOURS IN
  FRONT OF THE OPERATOR.** While the master was being diagnosed, the board went on
  showing *"wrong take, wrong episode, or the words changed after the render"* — **three
  causes, none of them the real one** — beneath a picture of a title card **that was
  never broken**, with a button offering to declare it sorted. Fault #6 on the flag text,
  fault #0a-adjacent on the picture, and a button that would have recorded a lie.
- 🔴🔴🔴 **E21 — NOTHING CHECKED THAT GORDON SAID THE WHOLE SCRIPT. HIGHEST.**
  *(EP15, 4 Aug 2026. E19's other half, proven in the worst way.)*
  **The file was complete. The duration matched HeyGen's to 0.02s. Every automated
  check passed. And the episode was two-thirds of a video.**
  Gordon stops **mid-word** — *"…not taking full advantage of the standard fractional
  bet"* + *"s available…"* — at **9:10 of a 13:31 file**, in **beat 18 of 24**. Missing:
  the $124 worked example the episode is NAMED for, Table 1, the rails passage, the
  minimum-price rule, the drifter caveat, and **the entire outro including the
  responsible-gambling line.**
  **THE ASSERTION IS CHEAP AND DECISIVE: the master must contain the LAST WORDS of the
  script.** One transcription of the tail, one substring test. It would have caught this
  before a single downstream step ran.
  > ### ⚠️ AND IT MUST BE FUZZY, NOT EXACT — OR IT SHIPS BROKEN.
  > **Found by the check failing on the very first real use.** My own version reported
  > the responsible-gambling line ABSENT because Whisper heard **"never *bit* more than
  > you can afford to lose"**. The line was spoken; the test was too strict. That is
  > exactly the mishearing `align_to_script`'s own docstring warns about
  > (*"whisper misheard 'Here's a claim' as 'He's a client'"*).
  > **Match on a WINDOW of the last N words with a similarity threshold, never an exact
  > substring.** A guard that cries wolf gets switched off — and we would have shipped
  > this one strict.
  *Caught only because `align_to_script` refused at 62.9% against an 85% floor and
  removed `aligned.srt` rather than let interpolated timings through — that guard,
  built after EP13's cards ran ahead of the words, is the only reason this was not
  assembled into a finished video.*
  ### 🔬 THE DIAGNOSIS — measured, and it killed two theories
  | | |
  |---|---|
  | EP15 stopped at | **9,224 chars / 1,677 words**, mid-word |
  | **EP13 rendered COMPLETE at** | **12,042 chars / 2,194 words** |
  | **EP14 rendered COMPLETE at** | **10,846 chars / 1,960 words** |
  **A length cap at ~9,224 CANNOT EXIST** — two longer scripts rendered whole. And the
  paste was not truncated either: **the file is 811s, and the FULL 2,466-word script at
  its own 182 wpm predicts 813s.** HeyGen was handed everything, allocated the right
  duration, then **rendered audio for the first 68% and left 4m18s of silence.**
  **A rendering failure at HeyGen's end, not a limit and not an operator error.**
  ⚠️ **The API says NOTHING is wrong:** `status: completed`, `error: None`, no
  truncation flag on any of EP13/EP14/EP15. **The provider's own success field is a
  proxy** — [[assert-the-artefact]].
- 🔴 **E20 — THE RAIL DOES NOT RECORD THE ID OF THE THING IT PAID FOR.**
  EP15's `heygen_video_id` was **NULL** while a completed, paid render sat on HeyGen.
  `_heygen_fetch` (providers.py:1506) falls back to **listing 100 videos and matching on
  `heygen_name`**. It works today and it is a guess.
  **THE FIX IS TO SAVE THE ID AT THE MOMENT THE JOB IS CREATED**, not to find it
  afterwards. *(EP15's was written by hand on 4 Aug once found — safe, because exactly
  one code path reads it and a non-null value only skips the title search.)*
  ⚠️ **"Part 1 / Part 2 / Part 3" of the same article are coming, and at 300 episodes
  titles will collide.** The failure then is not "not found" — it is **the wrong
  episode's render**, silently.
  📋 **SWEEP AFTER EP15 SHIPS — where else do we match on a NAME when an id exists:**
  `_heygen_fetch`'s title match · `_clip()`'s glob `*c{n:02d}*.mp4` (a card whose page
  is renamed stops matching) · `_hero_paths` keying on filenames rather than the ledger ·
  `broll_registry_check`'s `broll-[a-z0-9-]+` regex over prose · `episode_dir()` (E18) ·
  `midroll_window`'s folder scan · the b-roll job map keyed on target NAME in
  `build_state.jobs`. **Log only for now; do not touch mid-build.**
  *Pattern named in CLAUDE.md as fault #0a: an id is a promise, a name is a guess.*
  ⚖️ **FOR THE RECORD, so nobody fixes the wrong thing: none of this is why the download
  is slow.** The URL works and the bytes are arriving. **The missing id bit the
  INVESTIGATION, not the transfer.**
- 🔴🔴 **E19 — TIME SPENT WAITING FOR A PERSON IS BEING COUNTED AS TIME SPENT WORKING.
  ONE fault, TWO symptoms. Before EP16.** *(Jodie, 4 Aug 2026.)*
  > **Any clock shown to an operator, or used to raise an alarm, must count ONLY time
  > the machine was actually working.**
  **Symptom 1 — the board's card, which Jodie is looking at now:**
  *"Working for 15 hr 6 min · render cooking 12 hr 38 min"* — **the HeyGen render took
  about twenty minutes.** The board is counting wall-clock since the episode was created
  at 18:04 the previous evening: **Jodie asleep, and the title-card flag waiting for her
  all morning.** *It is not wrong about the arithmetic. It is wrong about what it is
  measuring.*
  **Symptom 2 — my own watcher**, which fired
  *"BUDGET EXCEEDED — cards_render has run 31 min against a 30 min budget"* on a step
  that was **flagged and waiting for Jodie to look at the title card.** The watcher built
  to tell SLOW from DEAD invented a third case and got it wrong: **"waiting for a person"
  is neither.**
  **THE FIX, both places:** a step that is **flagged (`needs_look` true) is a human
  wait, whatever its budget says** — and so is a step whose budget is `None`. **Both must
  STOP THE CLOCK, not merely suppress the alarm.**
  ⚠️ **Not fixed mid-build on purpose:** restarting the watcher now leaves exactly the
  gap we agreed not to leave.
  📣 **And the same line is engine vocabulary in the operator's box** — *"render
  cooking 12 hr 38 min"*. **Hugh reads twelve hours of cooking and reasonably concludes
  something is broken.** Whatever that line becomes once it counts the right thing, it
  must say the plain version: what is happening now, and roughly how long it has
  actually been doing it. See `docs/PP-operator-box-rule.md`.
- 🟡 **E17 — EXTEND THE HEAD-OF-BUILD ASSERTION TO THE EPISODE'S OWN STAGED INPUTS.**
  ✅ **HALF-ANSWERED 4 Aug by `engine/check_page_images.py`**, which catches any staged
  image a PAGE references — including the title hero and the e-book cover — without
  anyone maintaining a list. **What it does NOT cover is an input nothing references from
  a page** (a b-roll clip, a music file). That remainder is E17.
  `assert_standing_assets()` covers the STANDING pages — warranty, end card, midroll
  chip. It does **NOT** cover per-episode staged inputs: **`overlay/export/title-hero.png`
  and `thumbnail/hero.png`.** *EP15, 4 Aug: a correct quarantine removed the title hero,
  nothing re-staged one from the new pick, and the title card RE-RENDERED ONTO FLAT
  BLACK — then the board asked Jodie to judge "whether the horses are framed well" on a
  card with no horses.* **Same class as the midroll chip, which A2b existed to stop:** a
  knowable absence discovered at render instead of at the head of the build.
- ⚠️ **E18 — `episode_dir()` STILL HAS THE GLOB FLAW IT WAS WRITTEN TO PREVENT.**
  `pp.glob(f"PP-EP{n}*")` — **`PP-EP1*` matches `PP-EP10`, `PP-EP9*` matches `PP-EP98`.**
  Single-digit episodes resolve to the WRONG FOLDER. Written 4 Aug for exactly this
  class of fault, and it is **the same flaw that made the first two outro audits wrong**.
  Fix: anchor on a zero-padded pattern, `^PP-EP(\d{2})(?:$|[-_])`. *Noted 4 Aug and
  deliberately left; it is live in `test_hand_steps.py`, `test_title_card.py` and
  `test_youtube_title.py`, all of which currently pass only because they use 13, 14, 15.*
- 🟡 **E16 — THE MECHANISM LANDED 4 Aug 2026, `04da5fc`. NOT YET PROVED, AND THE BOARD
  HALF IS DEFERRED ON PURPOSE.** `hero-jobs.json` is now keyed on
  `slot + sha256(prompt)[:12]`. Same prompt → same key, so the double-spend guard works
  exactly as before; changed prompt → a genuine create. **Nobody has to remember to
  clear a file, which is the only kind of fix that holds.**
  ⏳ **THE WITNESS FOR A SPENDING GUARD IS THE BALANCE MOVING, AND IT HAS NOT BEEN
  WATCHED.** Both directions need two real generations. **Watch it on EP16's covers, and
  do not call E16 proved until then** — on EP15 a status field, a fresh mtime, a byte
  count and a "completed" job all said the images were new, and only the unchanged
  balance said otherwise.
  📋 **Deferred:** the board must never re-offer a rejected artefact and must say so on
  the card. The prompt hash fixes the mechanism that failed; **the label matters the day
  somebody who is not Jodie is looking at that card.**
  **Original entry kept below.**
- 🔴🔴🔴 **E16 — A REJECTED ARTEFACT CAME BACK AND WAS OFFERED TO THE OPERATOR AS A
  CHOICE.** *(EP15, 3-4 Aug 2026. The worst fault of the build.)*
  Both cover heroes were looked at and **ruled unusable** — A carried a competitor's
  brand, B had the prompt's own instruction text rendered across the sky. Jodie approved
  regenerating both. The files were moved aside. **The engine re-downloaded the SAME two
  images, the board offered them again with nothing on the card to say they had been
  rejected, and Jodie picked one in good faith.** Her choice then propagated to
  `overlay/export/title-hero.png` and `ebook/cover-src/hero.png`.
  > **She made a decision on bad information and had no way to know.**
  **That is worse than the original prompt bug**, which only wasted credits.
  **THE MECHANISM, named — it is not `build_state`:** `docs/hero-jobs.json` is a
  DOUBLE-SPEND GUARD. `_generate_heroes` stores a Higgsfield `job_id` the instant it
  exists, then on re-run:
        if not rec.get("job_id"):  ...create...
        self._hf_download(rec["job_id"], path, key)
  With an id present it **never calls create** — it re-downloads that job's output.
  **DELETING THE PNGs CANNOT INVALIDATE A STORED JOB ID.** Moving the files aside was
  treated as sufficient and it was not. *(Proven by the balance: 75.22 unchanged. Two
  heroes cannot be generated for free.)*
  **WHAT HAS TO CHANGE:**
  1. **Rejection must be RECORDED, not implied by absence.** A rejected job id belongs
     in the ledger marked rejected, so the guard can tell "already paid for" from
     "already paid for AND no good".
  2. **The board must never re-offer an artefact that was rejected**, and must say so
     on the card if one is somehow still present.
  3. **A regeneration is only proven by the BALANCE MOVING.** A status field, a fresh
     mtime, a byte count and a "completed" job all said these were new. Only the
     unchanged balance and a byte-compare said otherwise. [[assert-the-artefact]]
- ✅ **E14 — LANDED 16 Aug 2026, in three parts, on the back of EP27.**
  **The class is mostly GONE rather than guarded:** a big table is now a `ladder` card
  and a long list a `checklist` that holds twelve, so the two shapes that kept going
  bespoke are generated — and therefore schema-checked, trace-gated and
  invented-text-gated like everything else. What stays bespoke gets (a) **ONE ask at
  `audit_inputs` naming every page**, so a person is told the whole job before a credit
  moves rather than one deep halt at a time, and (b) **a words-and-figures gate on the
  finished page** plus the `ppDuration` check this entry asked for by name.
  ⚠️ **ONE CORRECTION TO THIS ENTRY, MEASURED:** *"a bespoke page gets the same CHECK
  with none of the FITTING"* is right about autofit and **wrong about `card_check`** —
  it is handed the whole `overlay/export` directory and has always measured every page
  in it. EP27's C15 collision survived because **the page did not exist when the step
  ran**, so it was hand-authored AND hand-rendered afterwards, outside the checked
  moment. Proved both ways in `engine/test_bespoke_gates.py`, which feeds card_check a
  deliberately colliding bespoke page and watches it fail.
  *Original entry kept below — it is the case that justified all of it.*
- 🔴 **E14 — A BESPOKE CARD CARRIES A LAYOUT RISK AUTHORED CARDS DO NOT, AND IT IS
  CAUGHT AT THE WRONG END.** *(EP15, 4 Aug 2026.)*
  **The ONE card in EP15 that nothing generates is the ONE that failed the layout
  gate** — C12, the Table 1 card, with two collisions: the gain column under the logo
  chip, and the footer clipped through the panel floor. **That is not bad luck.**
  `author_cards.py` lays generated cards out to a template *known to fit*; a bespoke
  page gets the same CHECK with none of the FITTING. **That is the cost of "bespoke",
  and nobody priced it.**
  Both faults came from one line — `table{margin-top:auto}` in a flex column, which
  pushed the table and everything after it onto the panel's bottom edge.
  **THE FIX: bespoke cards need the same pre-flight the generated ones get, run at
  AUTHORING time, not at render time.** Finding this at `cards_render`, twelve hours
  into a build, is the wrong end of the pipeline — the cheapest moment to catch it is
  the moment the page is written.
  > ### 🔴 PROVEN TWICE ON THE SAME CARD, 4 Aug — and the second one is the argument.
  > **Halt 1, LAYOUT:** `table{margin-top:auto}` pushed the gain column under the logo
  > and the footer through the panel floor.
  > **Halt 2, WIRING:** the page never rendered a clip at all, because
  > `render_card.py` waits on `typeof window.ppDuration === 'number'` **before** it
  > waits for fonts — and a hand-authored page that does not load `pp-anim.js` and call
  > `ppInit()` never defines it. Every generated card gets that free from
  > `author_cards.py`. **A bespoke page gets NOTHING for free.**
  > **THE PRE-FLIGHT MUST CHECK BOTH: that the page FITS, and that it declares
  > `ppDuration`.** One check would have caught neither the second time.
  ⚠️ **AND THIS GETS MORE IMPORTANT, NOT LESS:** if the Table 1 transcription ruling
  goes the way it looks like going, **bespoke cards become commoner**, and every one
  of them is an unfitted page checked only after a render has been paid for.
- 🔴🔴 **E15 — SELF-HOST THE FONTS. HIGH, SMALL, AND IT REMOVES A DEPENDENCY RATHER
  THAN WORKING AROUND ONE.** *(Jodie, 4 Aug 2026.)*
  Card pages pull Anton and Barlow from `fonts.googleapis.com` **at render time**, so
  `cards_render` has an **undeclared internet dependency in the middle of the build**.
  **The studio cannot render a card offline, and it has now cost an evening.**
  **The fonts are standing assets exactly like the warranty slide and the midroll
  chip:** ship them in the repo, reference them locally, and *the entire class of
  failure disappears* — including E15b below, which only bites when the CDN is
  unreachable.
- 🔴 **E15b — `card_check` ASSERTS A PROXY, NOT THE ARTEFACT. It is fault #1.**
  It waits for `document.fonts.status === 'loaded'` — which resolves when pending loads
  **SETTLE, success OR failure**. So the check can measure in a **fallback face and
  pass**, while `render_card`, which uses the strict `document.fonts.check()`, refuses
  to run at all.
  > **The proxy is "fonts finished doing something". The artefact is "the shipping face
  > is in use."**
  On EP15's C12 headline: **896px in Anton against 1327px in the fallback — a 48%
  difference, on a check whose whole job is deciding whether text fits.**
  *EP15's 17/17 is sound only because the font happened to be cached — luck, not
  design; verified explicitly on 4 Aug before the number was quoted.*
  **Fix: `fonts.check()` against each declared family, and HALT rather than measure in
  a substitute** — the way `render_card` already does. [[assert-the-artefact]]
- 🔴🔴 **E12 — NEVER RETRY A SPENDING STEP WITHOUT CHECKING THE WORK ALREADY EXISTS.
  HIGH.** *(3 Aug 2026, EP15, and it nearly cost a second batch.)*
  `covers_ab` **generated both heroes, was charged for them, downloaded them to disk** —
  and then failed in `_publish_asset` (the Supabase upload). The board reported a clean
  *"Generating the two cover heroes failed 3 times"* **and offered a retry.** Taking it
  would have spent another 4 credits for images already sitting in `ebook/cover-src/`.
  Balance measured: **131.72 → 75.22 = 56.5 exactly** = 52.5 (7 clips) + 4.0 (2 heroes).
  **The full batch was billed. Nothing was refunded. Three retries could burn a batch.**
  **THE RULE: before retrying anything that spends, check whether the work already
  exists at the provider.** Higgsfield's generation history is authoritative and cheap
  to read. **And the board must never offer a bare "retry" on a step that spends — it
  has to say what has already been paid for.**
  *Same shape as the stale-code guard: recovery that costs nothing when it works and
  real money when it doesn't.*
  ✅ **The step already handles this correctly** — `make_covers_ab` skips generation for
  any hero already on disk (*"staged ones are used as-is"*). The gap is entirely in what
  the BOARD tells a human to do.
- 🔴 **E13 — A PROMPT DESCRIBES THE PICTURE; IT NEVER INSTRUCTS THE GENERATOR.**
  EP15's `hero_b_prompt` opened *"…DELIBERATELY DIFFERENT from A: …"* and the model
  **rendered that phrase into the image** as a white headline across the top third.
  Hero A separately came back carrying a **real bookmaker's brand, legible twice** —
  unusable on a PP cover. **Every automated check passed both**: status completed,
  1696x2528, 2:3, 6MB, two genuinely different files. **Only looking caught it.**
  Guard: reject prompts containing meta-instruction (`DIFFERENT from`, `unlike`,
  `same as`, `option A/B`), require explicit NO-TEXT/NO-LOGO negatives on covers, and
  **put the generated image in front of a human before it is offered as a choice.**
  [[look-at-the-rendered-output]]
- 🟡 **E11 — PART 1 LANDED AND DEMONSTRATED 4 Aug 2026, `04da5fc`. PART 2 IS OPEN.**
  `_code_changed_exit()` in **BOTH** `needs_look` waits — the written patch covered only
  the outer one, and **EP15 sat in `flag_and_wait`**, the other. It RAISES rather than
  returning, because a bare `return` in `flag_and_wait` means *"retry the step"* on the
  code being escaped.
  🏁 **Observed for the first time:** flagged episode → touch `engine.py` → **8 seconds**
  → *"changed on disk while this episode was flagged"* → **pid 13420 → 44536.**
  🔴 **PART 2 STILL OPEN, and it is the half Hugh needs: THE BOARD CANNOT SAY "this
  engine is running code older than the repo."** Part 1 makes recovery automatic; part 2
  makes the state visible. For Hugh it is otherwise undiagnosable.
  **Original entry kept below.**
- 🔴🔴 **E11 — THE STALE-CODE GUARD ONLY FIRED WHEN THE ENGINE WAS IDLE.**
  *(Found 3 Aug 2026, the hard way.)*
  **`_code_changed()` has ONE call site: engine.py:941, at the top of the OUTER acquire
  loop.** Once an episode is claimed the engine drops into the inner `while True:` —
  step dispatch, and the 15-second `needs_look` poll — and **never returns to the outer
  loop until the episode is released.** So the guard cannot fire while an episode is
  held, building *or* flagged.
  **What that cost:** the NameError fix landed at 09:10. The running process had been
  holding EP15 since 08:47, so it kept the broken code in memory for **over an hour**,
  failed `audit_inputs` a fourth time at 10:03, and **Jodie cleared the flag and it
  walked straight back into the same bug.** Recovery needed a terminal.
  > **A deploy path that only works when the engine is healthy is no deploy path at
  > all, because the times you need it are exactly the times it is not.**
  And it is narrower than "healthy" — **kept verbatim, because this is the sharp end
  of it:**
  > **It only works when the engine is IDLE, and the one state where a stale-code exit
  > is both safe and necessary — parked on a flag with nothing in flight — is precisely
  > the state it cannot reach.**
  **TWO PARTS, AND THE SECOND IS THE ONE HUGH NEEDS:**
  1. Check `_code_changed()` inside the inner loop too — certainly in the `needs_look`
     wait, which is where a flagged engine spends all its time. A flagged episode is
     the safest possible moment to exit: nothing is in flight.
  2. **THE BOARD MUST BE ABLE TO SAY "this engine is running code older than the
     repo."** Today that state is completely invisible: the card shows the same flag,
     and clearing it does nothing, forever. **Hugh has no terminal — for him this is
     unrecoverable and undiagnosable.** The engine knows its own start time and can
     stat the three files; that comparison belongs on the rail and on the card.
  ⚠️ **AND CLAUDE.md IS WRONG WHERE IT SAYS THE GUARD "IS THE DEPLOY PATH".** It says
  never kill the engine by hand because the guard handles deploys. It does not. Until
  part 1 lands, a mid-episode code fix REQUIRES a manual restart — and the safe window
  is while the episode is FLAGGED, when nothing is computing.
- **E1** an engine that refuses to start must say WHY on the page, or the next person
  restarts it in a loop. *(The sleep guard is the worked example.)*
- **E2** `_publish_asset` must compress board assets — and build the deletion with it,
  see [[retention-ruling]].
- **E3** a standing **drift check**: assert the shot map against `aligned.srt` every
  build. The same re-point was missed three times and **every one was found by
  accident**. The fourth instrument should not need luck.
- **E4** a **pool-line wholeness** check — see
  [[a-gate-that-invites-an-edit-must-verify-it]].
- **E5** a halt with **one correct answer** is a chore wearing a decision's clothes —
  `derive_card_timings` should set those beats itself.
- 🔬 **E6 — TESTED 4 Aug 2026, AND THE RESULT IS SPLIT. CAUSE NOT ESTABLISHED. NOT
  PRE-EP16.** *Logged unexplained, on purpose.*
  | | |
  |---|---|
  | A Doc created through the Drive API **tonight**, read back | **CLEAN** — `—` `–` `‘’` `“”` `…` `é` all intact |
  | **EP15's real script Doc**, read via the export URL | **0 real em dashes**, mojibake present |
  | EP15's Doc, read via the Drive API instead | **the same corruption** |
  **Both read paths agree on EP15, so the corruption is in the STORED BYTES.** But a Doc
  created through that API tonight round-trips clean, and **I could not complete the
  comparison** — the new Doc cannot be shared from a session, so the export URL 401s and
  the clean result rests on one read path. **Do not name a cause.**
  > ### 🔴 AND THE TEST FOUND SOMETHING SHARPER, WHICH IS NOW GUARDED
  > **A document API's "text representation" MARKDOWN-ESCAPES the script**: EP15 comes
  > back as `\#` on every comment line and `Squeeze Those Odds\!`. Read via the export
  > URL it is clean. **Those backslashes would be frozen into `script_snapshot` as the
  > record of what was approved — and spoken.** `fetch_script` now asserts at the byte
  > level and flags in plain English. *(Landed `04da5fc`.)*
  **Original entry kept below.**
- 🔴 **E6 — A WRITE PATH THAT CORRUPTS, AND NO EDIT PATH TO REPAIR IT.** *(Upgraded from
  a note to a Bundle E item by Jodie, 3 Aug 2026, after it recurred.)*
  **The Drive API mangles em dashes on create** — `—` is written back as `â€"` (UTF-8
  read as cp1252). Seen on **EP14 (stop 4)** and again on **EP15**. And the MCP has
  **no update tool**, so it cannot be repaired in place: the only routes are a human
  editing the Doc by hand, or creating a second Doc — which the ONE-home rule forbids.
  **That combination is the item.** A corrupting writer would be survivable with an
  editor; an absent editor would be survivable with a clean writer. Together, every
  future episode's Doc header goes through a path that damages it and cannot be undone
  by the machine that did the damage.
  **THE FIX BELONGS AT THE WRITE END — and "pure ASCII headers" is NOT it.**
  ⚠️ *That was this file's stated remedy until 3 Aug and it was WRONG. Corrected after
  the third sighting:* `render_ready`'s allow-list is
  `SAFE_EXTRA = set("‘’“”–—…é")` — **a real U+2014 is explicitly permitted and would
  never have been flagged.** The gate rejects the CORRUPTION, never the punctuation.
  So ASCII headers were a workaround for a broken write path masquerading as a rule —
  **and in six months nobody would have been able to explain why the rule existed.**
  The write path must stop corrupting; that is the whole of it. Belt and braces: a
  post-create readback that halts if the bytes came back different, since the create
  call reports success (`fileSize: 1`) whatever it wrote. [[assert-the-artefact]]
  **THIRD SIGHTING, 3 Aug:** EP15's header again — this time reaching `spoken-words.txt`
  and hard-failing `render_ready`, because a `#` comment block is NOT inert to that
  checker. Two consecutive episodes have now lost time to it.
  ⚠️ **AND THE REASON IT RECURRED IS WORTH MORE THAN THE BUG.** EP14's fix was recorded
  as "ASCII header" against a stop that was marked ✅ fixed. **EP15 reintroduced it
  because the header was copied from EP14's local DRAFT, not from EP14's corrected
  DOC** — the draft still had the em dashes in it. *A fix applied to the artefact and
  not to the thing that generates the artefact will come back on the next episode.*
- **E7** the supervisor log: **one timezone with a label**, and **rotate by day**, not
  by engine start.
- ~~**E8** board bug **C6**~~ — **CLOSED BY RULING, 3 Aug 2026. Build nothing.** A
  finished stage stays finished. **Never propose a "use the current Doc" button or a
  re-runnable `script_sync`.** The record is in [[script-gate-decision-record]].
- **E9** `shape` has no field in `PP-EPISODE-JSON-SPEC.md` though the visual standard
  requires it; and the packaging split-brain.
- **E10** the b-roll registry: EP14's clips were never logged.

---

# ✅ CLOSED BY RULING — off the lists entirely, do NOT raise again

- ## 🔒 4a — "C1 CLOSING-CARD AUTO-MOVE" IS CLOSED AS ALREADY-COVERED. **(14 Aug 2026.)**
  ### THE HALT IT WOULD HAVE AUTOMATED DOES NOT EXIST ANY MORE.

  **"C1" is not defined anywhere in this repo** — the name outlived whatever note created
  it. What it was reaching for is the closing/hero recap card overflow seen twice:
  **EP22 C19** and **EP23 C23**.

  🔴 **BOTH WERE PHANTOMS, AND `7835087` IS WHY.** `derive_card_timings` placed the end
  card at `beat − endcard_lead` while `assemble_episode.py` builds it at
  `beat + endcard_lead`. The tool believed the end card arrived **3.0s (two leads) early**
  and invented overlaps against a card that had not appeared yet. EP23's C23 fitted where
  it was — a 9.49s window against a 9.0s minimum — and its one real fault was an 8.0s
  hold that wanted 9.0s: **a hold bump, not a move.**

  ✅ **VERIFIED, NOT INFERRED FROM THE COMMIT MESSAGE.** Every episode on this machine with
  an aligned SRT and a shot map — **sixteen of them, EP6 through EP25** — was re-derived
  read-only on its CURRENT state. **Card/END overlaps found: ZERO. Including EP22 and
  EP23 themselves.** (Three older episodes still report unrelated problems; none is an
  end-card overlap.)

  📌 **AND THE ONE GENUINE CARD/END OVERLAP SINCE IS NOT A MOVE.** EP25's `C26/END: 0.34s`
  was real — it is post-`7835087` — and it is a **size-and-hold** problem, not a placement
  one. Its mechanical half now applies itself under **A23** (`--apply-hold`), and its
  editorial half — which row folds into which — is a decision and stays one.

  > ### ⚠️ SO BUILDING A CLOSING-CARD AUTO-MOVE WOULD HAVE AIMED AN AUTO-APPLY AT THE
  > ### WRONG HALT — and an auto-apply pointed at a phantom moves cards that fit.
  > That is fault #6 with a fix attached: a wrong cause whose remedy appears to work.

  🔒 **GUARDED so it cannot come back quietly:** `engine/test_derive_card_timings.py` A2 —
  END is placed at `beat + endcard_lead`, a card that genuinely fits raises **no** phantom
  overlap, **and a card that genuinely does run into the end card is still caught.**
  Fixing a position must not blind a check.

- ## 🔒 THE TRUNCATION AUDIT IS CLOSED. EP01-EP15, ALL FIFTEEN ACCOUNTED FOR.
  *(4 Aug 2026. Recorded so nobody re-opens it in three weeks.)*
  **NO PUBLISHED EPISODE IS SHORT.** The E22 download bug (`_heygen_fetch` never checks
  `Content-Length`) has existed for all fifteen episodes and **bitten exactly once** —
  EP15, caught before assembly.
  | | |
  |---|---|
  | **EP06-EP15** | **12/12 on the fuzzy tail match** — the range where the standing outro existed |
  | EP02, EP03 | 11/12 — clean *(an EXACT test would have flagged both)* |
  | EP04, EP05 | script-on-disk differs from what shipped. **NOT truncation:** both end on COMPLETE SENTENCES with normal tails, where EP15's real truncation cut MID-WORD |
  | EP11-EP14 | masters match HeyGen's stated bytes **EXACTLY** |
  | **EP01** | ⚠️ **CANNOT BE VERIFIED — no surviving script.** Named, not glossed. The reason the script is now kept permanently: [[retention-ruling]] |
  📝 **NOTE FOR HUGH, NOT A TASK:** EP05 shipped without a responsible-gambling line. It
  **predates the standard, it is not a fault, and nothing about the video changes.**
  Compliance is his, so he should simply know it exists — whether a line in the
  description is worth adding is his call. **Do not raise it as work.**
  ⚖️ **AND THE PRINCIPLE THAT CLOSES IT:** *a guard prevents recurrence — it does not
  oblige us to go back.* Nothing published is re-rendered or re-cut. In CLAUDE.md.

- **THE CREDIT CONVERSATION IS HAD AND APPROVED (Jodie, 4 Aug 2026).** Hugh is happy
  for her to buy more credits. **NEVER RAISE COST AS AN OBJECTION TO GENERATING
  SOMETHING.** Report what a thing will cost when it is useful information; never offer
  "it's only N credits" as a reason for or against doing it, and never propose the
  cheaper option *because* it is cheaper. ⚠️ This does NOT touch
  [[jodie-spend-nothing-without-approval]] — **stopping at the cost boundary for a
  DECISION still stands.** What is gone is cost as an ARGUMENT.
- **THE E-BOOK LINK GAP IS A NON-ISSUE (Jodie, 4 Aug 2026).** `ebook_link` is NULL for
  **EP06-EP12** and that is fine. The publish card captures it going forward; **the old
  rows stay as they are.** Do not re-raise, do not propose a backfill, do not put it
  back on a list.

# ⚠️ STANDING — true regardless of what is in flight

- **EP11-EP13 are PUBLISHED.** Do not touch, re-cut or retitle.
- **Human gates are sacred.** Never auto-render, never auto-publish. **Stop at the cost
  boundary.** [[jodie-spend-nothing-without-approval]]
- **Jodie clears flags and publishes. Nothing touches YouTube but her.**
- **§0a is absolute** — the article's sentences are never rewritten. Only WHICH sentence
  and HOW it is shown may change.
- **Tighten a gate freely; loosening one needs Jodie's ruling.**
- **CODE FREEZE WHILE AN EPISODE IS RUNNING.** Never edit `engine.py`, `providers.py` or
  `rail.py` mid-build.
  ⚠️ **THIS BULLET USED TO SAY the stale-code guard exits the engine and the supervisor
  restarts it, and that "IS the deploy path". IT IS NOT — corrected 3 Aug 2026 after it
  cost an hour**, and the wrong version survived here in memory for a day after CLAUDE.md
  was fixed. `_code_changed()` is checked ONLY at the top of the outer acquire loop, so
  **a claimed episode never reaches it.** Until E11 part 1 lands, **a mid-episode fix
  needs a MANUAL restart**, and the safe window is while the episode is FLAGGED.
  *(This is why new checks land as NEW FILES — `check_page_images.py` did, and needed no
  restart to be written, tested and proved.)*
- **The rail is select / insert / update.** [[retention-ruling]] holds the one exception.
- [[assert-the-artefact]] · [[one-source-of-truth-or-it-drifts]] ·
  [[anything-that-waits-must-say-so]] · [[command-hygiene-for-permissions]] ·
  [[look-at-the-rendered-output]] · [[jodie-ship-it-and-who-runs-what]]

# 🏆 THE SENTENCES WORTH KEEPING

> **"A ruling is not a mechanism. If the answer is 'someone will remember', it isn't a
> rule, it's a hope."**

> **"A pipeline is only measured by the run nobody prepared for."**

> **"A file that asks a question is a halt wearing a text file's clothes."**

> **"An installed task that never fires is the hope it was meant to replace."**

> **"A halt with one correct answer is a chore wearing a decision's clothes."**

> **"A test that assumes a name the process is designed to change is a test with a fuse
> in it."**

> **"A lint that cries wolf is a lint someone turns off."**

> **"Written and reviewed is not landed."** *(The queued E11 patch was correct about the
> fault and wrong about which loop, and only building it showed that.)*

> **"An optional field is not a type mismatch."** *(Two false positives that would have
> fired on every episode from now on — caught by the tests written to stop the guard
> crying wolf, not by reading it.)*

> **"A grey box has a luma."** *(Why `self_qc` passed an end card that was a broken
> image: every instrument was measuring something real, and none of them was measuring
> the thing.)*

> **"A single frame of an animated card is not evidence about the card."**

> **"A gate is a NET, and a net you plan to land in is a bad plan."** *(Why the e-book
> chart became a SLOT the code fills rather than 201 cells a writer types: the
> cell-for-cell gate would have caught a wrong number, correctly, at ~8 minutes and ~$3
> a bounce. A guard that fires often is not a working guard — it is a design that has
> not been finished.)*

> **"A rule that leaves no legal way to do the right thing has already chosen the wrong
> one."** *(EP26 declared its charts omitted because the vocabulary had no `<table>` and
> no card carried 225 cells. The gate was right; the vocabulary was the bug.)*

> **"A rule that fails silently on the case it was built for is worse than no rule."**
> *(The chart matched ITSELF as the section it belongs beside, because its own paragraph
> carries its name. EP26 hid it — its table is the article's last block — and only a
> fixture with the table mid-article showed it.)*
