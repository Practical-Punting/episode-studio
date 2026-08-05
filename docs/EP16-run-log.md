# EP16 — run log

**Written 5 August 2026 while the build was running, for someone who was not here.**
*Where EP16 is · what is left · what Jodie must be told · what is still unproved.*

> **THE EPISODE:** *Squeeze Those Odds! — Part 2*, byline *Each Way Betting Forever*.
> Roger Dedman, **Practical Punting, MARCH 1988**. Part 2 of two; part one is EP15, and
> the article links to it by its own *"Click here to read Part 1"*.
> Rail id `3d08f141-751a-47ad-8a87-2f64297a5ef5`.

---

# 1. THE HALT TALLY — **FOUR**

**EP16 was meant to be the clean run. It was not.** Counted from the log, not from
memory:

| # | at | what |
|---|---|---|
| 1 | `07:07:11` `audit_inputs` | **E26 false positive** — *"the whole `build.leads` block is absent"*. The fix was on disk; the running engine was holding stale code. |
| 2 | `07:27:31` `cards_render` | **card schema + job faults** — invented jobs (`prove`, `consolidate`), invented content keys, missing optional keys |
| 3 | `07:38:08` `cards_render` | **trace gaps** — figures with no source sentence |
| 4 | `07:41:52` `cards_render` | **layout collision** — the price block overflowing the card, C8 and C10 |

*(Two engine exits and one dead-zone recovery also happened. They are NOT halts —
nothing waited on a human. See §5.)*

> # THE FINDING THAT REDEEMS IT
> ## EVERY ONE WAS CATCHABLE BEFORE A CREDIT MOVED.
> **THE CHECKS EXIST AND THEY RUN TOO LATE.**
> **Nothing tonight was undetectable. It was all detected, in the wrong order.**

Halts 2, 3 and 4 all fired at `cards_render` — **after** the render gate opened, **after**
the credit check, **after** seven b-roll clips and two cover heroes were generated and
paid for, and **after** Jodie picked a cover. Authoring pages and checking them is
**Chromium and HTML: no API call, no credit, no spend.** It is the front half of
`cards_render` and it could run at authoring time for nothing.

**That is EP17 item 1, and it is the whole lesson of the night.**

---

# 2. WHERE EP16 IS

**`building`, claimed, healthy.** Past `cards_render`; rendering card clips, then
`heygen_download`.

**Done:** script Doc read (2,171 words, sha `17a205155b4b`) · both gates ticked ·
`audit_inputs` clean · render gate open · credit check ~56 credits · **7 b-roll clips
generated and downloaded** · **cover heroes A/B generated, Jodie picked B** · e-book cover
built · **17/17 cards clean**.

✅ **`check_page_images` FIRED IN A REAL BUILD AND PASSED** — *"page images: 17 page(s),
every image they reference is present"*. That is the 4 Aug guard doing its job on an
episode for the first time. **It is the reason nobody has to wonder whether the end card
is alt text this time.**

**Still to run:** card clips → `heygen_download` → `shot_map` → `assemble_passA` →
`assemble_passB` → `self_qc` → `ebook_pdf` → `thumbnail` → `youtube_copy` → four
approvals.

---

# 3. 🔴 THE NEXT STEP IS E22's FIRST LIVE TEST — WATCH IT AND WRITE DOWN WHAT IT SAYS

`heygen_download` is next. **E22 has never fired in anger.**

> **Why it exists:** EP15's master arrived **35 MB short** — HeyGen stated
> **114,395,315 bytes**, **78,947,138** landed. `ffprobe` reported the right duration
> anyway, because an mp4 written with `faststart` carries `moov` at the FRONT, so **the
> container announces the full intended length even when the tail never arrived.**
> **Gordon stopped mid-word at 9:10 of a "13:31" file. Every other check passed.**

**RECORD, AS IT HAPPENS:**
- the **stated `Content-Length`** and the **bytes that actually arrived**;
- whether they matched **first time**, or took retries;
- ⚠️ **the 109 MiB boundary** — EP15 saw four separate re-pulls land on exactly
  **114,294,784 bytes = 109 MiB to the byte**. Still unexplained. If it recurs, say so.

**A guard that has never fired is a guard we believe in rather than know.**

### AND E21 BEHIND IT — the master must contain the LAST WORDS of the script
One transcription of the tail, **fuzzily matched**, never an exact substring: EP15's own
check reported the responsible-gambling line ABSENT because Whisper heard *"never **bit**
more than you can afford to lose"*. **The line was spoken; the test was too strict.**
EP16's last words are: *"…back your own form study, and I'll see you soon."*

---

# 4. WHAT JODIE MUST BE TOLD BEFORE SHE WATCHES

1. **The e-book carries something the video does not.** Roger's **two tables** are
   reproduced as his own 1988 scans (`table-1.jpg`, `table-2.jpg`) — about five hundred
   cells between them. Only **one row** reaches a card. She should look at the e-book
   figures.
2. **Six scan repairs, disclosed.** `l/s`→`1/5` and `Vs`→`3/5` and four more, each forced
   by the article's own arithmetic. **The e-book says so to the reader** in one sentence.
   Full list in the capture file's header.
3. **One thing NOT repaired and NOT spoken:** *"the place tote will be offering an average
   return of only 83 cents"* — unprovable, so it stands as printed in the e-book and
   Gordon does not say it. **She should confirm the paragraph reads honestly without it**,
   since that judgement was mine.
4. **Beat 6 says "That's" where Roger wrote "i.e."** — ruled fine, flagged so she sees it.
5. **The framing:** 14 WIDE of 27. ⚠️ **She still owes a framing ruling on EP15's finished
   cut** — do not treat EP16's ratio as settled practice until she has given it.
6. **The midroll is pool line L6**, verbatim, at beat 15 — on the article's own hinge.

---

# 5. THE THINGS THAT WENT WRONG IN THE MACHINE, AND HOW TO RECOVER THEM

## 🔴 `author_cards` SKIPS PAGES THAT ALREADY EXIST — **the nastiest trap of the night**
*"already generated — pass `--force` to redo"*, and the engine calls it **without**
`--force`. **So changing `episode.json` and clearing the flag re-checks the STALE HTML and
returns a byte-identical halt.**
> ## A CORRECT FIX LOOKS LIKE A FAILED ONE, TWICE.
> **It breaks nothing. It makes the truth invisible.**
**DELETE THE AFFECTED PAGES BEFORE EVERY RE-CHECK.** The layout fix's real effect — the
box moving from `(204,838)` to `(110,787)` — would otherwise have been completely hidden,
and the natural next move would have been to undo a change that was right.

## 🔴 THE DEAD ZONE IS REAL AND IT WILL HAPPEN AGAIN
`_code_changed_exit` releases the lease and **leaves the working status**, so the episode
lands at `status='building', claimed_by=NULL` — which `claim_next` (queued only) and
`reclaim_stale` (owner not null) **both ignore**. Its own docstring warns about this state
and its code produces it. Cost an hour on 4 Aug; **four minutes on 5 Aug, only because we
were watching for it.**
**RECOVERY — use the engine's own crash path, invent nothing:** set `claimed_by` to a name
that is **not** the live worker (`reclaim_stale` filters `claimed_by=neq.<worker>`) and
`lease_until` to the past. `reclaim_stale()` takes it back within 30s.
⚠️ **It will now fire MORE often, because the stale-code watch list is wider.**

## 🔴 `autofit` IS BLIND TO A WHOLE CLASS OF "TOO BIG"
`offenders()` tests two things — text under the logo chip, text clipped inside a scroll
box. `card_check` reports a third: **an element whose own box extends outside the card.**
Measured: card_check failed C8/C10 while autofit said *"2 examined, 0 fitted, 0 still
failing"* on the same pages. **And the halt then blames the WORDS** — *"a choice between
the words and the layout"* — when nothing ever tried to shrink it.
*On EP16 the words were irrelevant: the overflow was VERTICAL and the box was 354px wide
in a 1700px area. Shortening "6-4 ON" would not have moved the bottom edge one pixel.*

---

# 6. WHAT IS STILL UNPROVED

## ⏳ E16 — THE COVER LEDGER. **A TEST WE HAVE NOT RUN — not a reading we missed.**

⚠️ **CORRECTED, because the difference changes what the proof IS.** My first draft called
EP16's covers *"E16's chance, and it went past"*. **There was no chance.** EP16's cover
prompts were **NEW** — new episode, new prompts, new job ids. **They were always going to
spend.** That is not the guard being tested; **that is the guard not applying.**

> ### E16's ACTUAL CLAIM: **SAME PROMPT → SAME KEY → the stored job is reused and NOTHING
> ### IS SPENT.**
> That only happens on a **RE-generation**, which did not occur and had no reason to.
> **So waiting for a natural opportunity means waiting forever, because the natural case
> is "generate once".**

**THE PROOF HAS TO BE DELIBERATE. Here it is, in full:**
1. a **test episode** with two cover prompts;
2. run `covers_ab` — read `RealProvider.balance()` either side. **Expect it to MOVE.**
3. run it again **UNCHANGED** — read the balance either side. **Expect it NOT to move**,
   and **the same job ids** in `docs/hero-jobs.json`.
4. change **one prompt by one word** — expect a **NEW job id** and the balance to **MOVE**
   again.

**Two real generations, about 4 credits, against 1,012 remaining. That is the price of
knowing, and it is cheap.** *On EP15 a status field, a fresh mtime, a byte count and a
"completed" job all said the images were new; only the unchanged balance told the truth.*

## ⏳ E11 PART 2 — the board still cannot say *"this engine is running code older than the
repo"*. **That is the half Hugh needs**, because for him the state is undiagnosable.

## ✅ E11 PART 1 IS NOW PROVED IN **BOTH** LOOPS — corrected here, because it was on the
## owed list and it should not be
Tonight demonstrated it twice, in two different states, and the **wording tells them
apart**:
| when | log line | which loop |
|---|---|---|
| `07:19:55` | *"engine.py changed on disk **while this episode was flagged**"* | `flag_and_wait` |
| `07:21:39` | *"preflight_episode_json.py changed on disk **since start**"* | **the OUTER idle loop** |
At 07:21:39 EP16 was in the dead zone and therefore invisible, so the engine was genuinely
**idle** — the state it spends almost all its life in, and the state nobody had ever
tested. **Both loops fire. The guard was never the problem; the WATCH LIST was.**

✅ **AND THE DERIVED WATCH LIST IS PROVED ON A NON-CORE MODULE.** `_CODE_FILES` was a
hand-written list of three; `preflight_episode_json.py` was invisible to it and the engine
ran six hours of stale code. It now derives from `sys.modules` filtered to `ENGINE_DIR`,
and the 07:21:39 exit **named a module that could not previously be seen at all.**

---

# 7. THE NUMBERS, MEASURED

| | |
|---|---|
| script | **1,876 words**, 27 beats, `render_ready` ✓ · the Doc reads 2,171 with its header |
| cards | **13 authored + 3 standing**, 17/17 clean · 8 fullscreen / 5 panel-push · 5 hero |
| b-roll | 7 clips, all downloaded |
| **credits — MEASURED** | **58.5 spent.** Balance **1,071.22 → 1,012.72**, read from the API |
| credits — estimated | 56.5 (7 clips × 7.5 + 2 heroes × 2), ceiling 65 |
| card faults found | **20** schema/job in the first pass, **26** trace behind them, **48** across three rounds |

⚠️ **THE SPEND IS 2 CREDITS ABOVE THE ESTIMATE — 58.5 against 56.5 — AND I HAVE NOT
ESTABLISHED WHY.** Recorded as a discrepancy, not explained away. *EP15's lesson was
exactly this shape: a 35 MB gap was noticed, then talked away with a plausible cause, and
the plausible cause was wrong.* **If EP17 comes in 2 over as well, it is the cover model's
price and the ceiling arithmetic needs updating; one observation is not a pattern.**

⚠️ **I twice reported "38 faults" from memory during the build. Rebuilding the file as a
fixture and measuring gave the numbers above.** *The estimate was wrong in both directions
at once, which is what remembered numbers do.* The real file is kept at
`engine/testdata/ep16-cards-BEFORE-FIX.episode.json` — **and E26 returns ZERO blockers on
it**, which is the whole argument for EP17 item 1 in one measurement.

---

*Related: `docs/EP15-run-log.md` (the previous worked example) · `docs/PP-STANDARDS.md`
§0a-i (scan damage, three categories) and §1a (the series naming amendment) ·
`CLAUDE.md` faults #4a and #7 · the EP17 list in the session checkpoint.*
