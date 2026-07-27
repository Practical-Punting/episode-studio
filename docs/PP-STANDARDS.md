# PRACTICAL PUNTING — CANONICAL STANDARDS (the single source of truth)
**This file is THE one place the episode rules live.** Both Cowork Claude and Claude Code read from — and write to — this file, so the rules can never drift between them.

- **Location:** `docs/PP-STANDARDS.md` in the **episode-studio repo** (`github.com/Practical-Punting/episode-studio`), locally `C:\Users\jlral\repos\episode-studio\docs\`. **This line used to point at `G:\My Drive\PP Videos\docs\PP-STANDARDS.md`, which has been a 521-byte "MOVED — nothing here is authoritative" signpost since 27 Jul 2026** — the canonical file was pointing at its own tombstone. Fixed 28 Jul 2026. (§IF YOU MOVE A FILE, EVERY SIGNPOST AIMED AT IT MOVES WITH IT — including the one inside the file.)
- **Rule of the road:** any standard Jodie approves is written **once, here.** Change only on Jodie's say-so.
- **Division:** the *rules and facts* live here. Claude Code's *build recipes* (ffmpeg graphs, `assemble_episode.py`, `build_ebook.py`, etc.) stay in its `pp-episode-production` skill — **which lives in this repo at `.claude/skills/pp-episode-production/` from 28 Jul 2026** (CODE IN GITHUB, MEDIA ON DRIVE) — but they must obey these rules.
- **Last updated:** 28 Jul 2026 (later) — **HUGH'S RULING, co-owner, FINAL: the repo stays PUBLIC.** §WHERE RULES LIVE and §WHAT MAY BE STORED AND SHARED WHERE rewritten to match: TIER 2 is now **empty** (the `pp-episode-script` skill and `broll-registry.md` are marketing material, not trade secrets — the episodes come from articles PP already publishes openly), TIER 3 absorbs them plus all code, and **TIER 1 is unchanged, absolute and explicitly strengthened**. Earlier on 28 Jul 2026 — four Jodie rulings, all in §Mid-video / §END SEQUENCE / §Standing OUTRO / §Motion-graphic cards: (1) the **spoken midroll comes from a fixed pool of ten**, used in order, never rewritten — this SUPERSEDES "reword it every episode"; (2) the **verbatim window is the previous NINE episodes**, not all of them; (3) the **on-screen chip is fixed standing furniture**, identical every episode; (4) **name the video at every ask** (midroll + outro e-book line; narration exempt). Also fixed: the Location line above, which pointed at this file's own retired signpost. Previously 26 Jul 2026 — three Jodie rulings: the b-roll no-repeat clarification (composition, not subject, §B-roll), the series part treatment (§E-book), and never-fabricate-racing-data (§Motion-graphic cards + Hard never list). Previously 23 Jul 2026 by Cowork Claude: the standing outro and the mid-video like/subscribe rule.
- ✅ **Sign-off — RULED 27 Jul 2026.** The three documents were never in conflict: they held two
  valid instances of one shape. The sign-off is now recorded as a **pattern** in §Standing OUTRO
  and re-voiced each episode. The responsible-gambling line is separate and stays locked.

---

## ⚖️ WHAT DESERVES A GATE (Jodie, 27 Jul 2026) — read this BEFORE adding a QC check
**A gate is only worth having if the thing behind it is worth stopping an episode for.**
A check that halts a build over something Jodie does not care about is **worse than no check**,
because **Hugh cannot clear it and cannot know it did not matter.** He operates from a browser;
a red flag he can neither judge nor dismiss is a dead end, not a safety net.

So before adding any HARD FAIL, ask: *would Jodie genuinely want the episode stopped for this?*
- **Yes** → hard fail (invented data, a card over the host's face, a stale packaging value, an
  unverifiable figure, b-roll and a card sharing the screen).
- **No, but it's usually better** → **PREFERENCE**, written as guidance, never wired to a gate.
- **Worked example:** a proposed ≥1s clearance between b-roll and a card was *my* recommendation,
  not a ruling. Jodie looked at the actual video and ruled: *"It is ok if one comes straight
  after the other."* It stays as a preference in the production skill and must never become a
  hard fail. See also §Motion-graphic cards — b-roll and cards **overlapping** is still a hard
  fail; *adjacency* is not.

This sits alongside the QC-per-fix rule below, which says every recurring-risk fix gets a check.
Both are true: **check what matters, and only what matters.**

## ✅ THE QC-PER-FIX RULE (standing, 25 Jul 2026)
**Every recurring-risk fix must land in the standard AND the engine AND an automatic QC
check — never just a note. (Gawande: a checked rule enforces itself.)**
A lesson written down but not enforced will recur; a lesson wired into `qc_episode.py` (or an
engine gate/flag) cannot. When something goes wrong twice-capable: (1) write the rule here,
(2) make the engine/assembler obey it by default, (3) add the check that HARD-FAILS or flags a
breach. Precedents: the end-sequence checks, the thumbnail template-conformance guard, the
Words Gate, the b-roll registry check, the 180 kbps audio gate.

## 🚧 AN EPISODE CANNOT GO BACKWARDS — pre-EP12 improvement (found 27 Jul 2026)
**Once an episode parks at `awaiting_approval` the engine RELEASES its claim, and after that no
`acquire()` path can ever pick it up again.** Any correction found at or after the approvals
gate strands the episode until a human hand-writes the rail.

All three claim routes miss a released episode:
- `resume_own` — `claimed_by=eq.{worker}&status=in.(building,rendering,assembling,revising)`.
  **`claimed_by` is NULL after release**, so no match.
- `claim_next` — `status=eq.queued`. A corrected episode is `assembling`, not `queued`.
- `reclaim_stale` — `status=in.(WORKING)&claimed_by=not.is.null&…`. **Explicitly excludes null
  claims**, which is exactly the state a released episode is in.

So moving a corrected episode back to `assembling` WITHOUT also re-attaching `claimed_by` leaves
it permanently stranded — running, healthy-looking, and picked up by nothing.

**Worse, the board cannot dig it out either.** The per-approval **"undo"** buttons live in
`gateApprove()`, which only renders at status `awaiting_approval`. At `ready` the board renders
`gatePublish()` — a URL box and "Mark as published", **no approval list and no undo**. The only
board action that moves `ready → awaiting_approval` is the undo handler itself, which cannot be
reached from `ready`. Chicken and egg.

**Why this matters beyond us:** Hugh operates from a browser. He could never hand-write a rail
row, so today any post-approval correction is a dead end for him.

**THE FIX (pre-EP12):** a proper **"send it back a stage"** control on the board that, in one
click, moves the status back, re-attaches the claim to the engine's worker id, and clears the
approvals for the assets being rebuilt. Until it exists, post-approval corrections need two
scripted rail writes and are engine-operator work, not operator work.

## ⚙️ ENGINE OPERATIONS — A DROPPED CHECKPOINT CANNOT REACH A RUNNING ENGINE (27 Jul 2026)
**If you drop a step from `build_state` to force a rebuild, the engine MUST BE RESTARTED before
it takes effect. Clearing the red flag alone will NOT rebuild anything.**
- **Why:** when a step fails, `engine.py`'s `flag_and_wait()` parks *inside that step*. When the
  flag clears it does one thing — retries **that step only**. It never re-enters `run_phase`, so
  it never re-examines earlier steps, and it is still holding its own in-memory copy of
  `build_state` from before your edit. Your change to the rail is simply never read.
- **The trap:** `--watch` mode says nothing about this. Non-watch mode prints *"restart the
  engine after clearing the flag"* — so the one path that tells you is the path you are not on.
- **How it bit us (EP11, 27 Jul 2026):** `assemble_passB` was dropped so the video would rebuild
  with corrected card timings. The flag was cleared, the engine retried QC **against the same
  stale video**, and failed again. Proof it never rebuilt: `FINAL.mp4` byte-identical and
  unchanged in mtime, `passB_graph.txt` not regenerated, and a frame pulled at 47s still showed
  the card in its OLD window.
- **The order that works — three steps, never bundled:**
  1. **Stop** the engine (Ctrl+C in the engine window).
  2. **Clear** the flag on the board.
  3. **Start** the engine again (`python engine\engine.py run --watch`).
  The flag is cleared **between** the stop and the start — after stopping, before restarting.
- **Verify before trusting it:** a rebuild must change `FINAL.mp4`'s size or mtime. If neither
  moved, the assembly did not run, whatever the log says.

## 🛡 PACKAGING, NUMBERS & RENDER-READY (locked 25 Jul 2026 — enforced per the QC-per-fix rule)
1. **Packaging consistency.** The packaging slots are DELIBERATELY different (hook · byline ·
   e-book cover title · YouTube title — e.g. EP08's e-book is "Yes You Can Win" while its
   hook is "Bet Less, Win More"), so the check is NOT "all identical": each asset must carry
   the **currently-locked value for its slot**, declared in `episode.json` →
   `packaging {hook, byline, youtube_title, ebook_title}`. Title card + thumbnail must agree
   on the hook and the byline; the YouTube txt carries the locked YouTube title; the cover
   carries the locked e-book title. `qc_episode.py --episode` **HARD-FAILS any asset showing
   a STALE value** (the EP08 rework bug) with a plain-English flag naming the mismatch.
2a. **🔒 EVERY FIGURE MUST BE TRACED TO A SOURCE SENTENCE — AUTOMATICALLY, AND IT HALTS THE
   BUILD (Jodie, 27 Jul 2026; pre-EP12 improvement).**
   The fidelity rule already says *"if you cannot point to the source sentence, it does not
   ship"* — but it lived only in the script skill's prose, where no machine could act on it.
   **From EP12 the numbers check must EMIT THE TRACE, not just the list:** every figure on every
   card, thumbnail and e-book figure, printed **beside the exact sentence in the source article
   it came from**, grouped by card so a human compares two things side by side instead of
   hunting.
   - **Any figure that cannot be pointed at a source sentence is a HARD FAIL and HALTS the
     build**, exactly like an overlap. It is not a warning and not a human judgement call —
     an untraceable figure is invented data until proven otherwise.
   - **Why this is not theoretical (EP11, 27 Jul 2026):** card C7 displayed "2nd Juggler" and
     "3rd Brave Warrior". Alan's article names the four beaten horses and **never states where
     any of them finished** — the placings were inferred from the listing order and asserted on
     screen as fact. It passed every automated check, shipped into the built video AND into
     e-book figure 7, and was only caught because a human traced 41 figures back to the article
     by hand. A machine doing it every build would have stopped it before assembly.
   - **The trace must cover the e-book figures too**, not just the video cards — the same
     fabrication reached both.
2. **Numbers check.** Figures are editorial — a HUMAN ticks them. QC collects every number /
   worked example on the cards (and any stray digits in the spoken track) into
   `numbers-check.md` and WARNs for confirmation (the midroll-listen pattern). No unverified
   or garbled figure (the EP07 1992-scan lesson) reaches a card or narration unreviewed.
3. **Render-ready scan.** BEFORE Jodie renders, `render_ready.py` checks the spoken track:
   numbers as WORDS (bare numerals = fail), no odd characters, midroll wording fresh,
   sensible length. The engine runs it at audit (flags instead of building); run it manually
   any time a script is about to be pasted into HeyGen. A render is never wasted on a script
   that will glitch.

## Definition of Done — EVERY episode ships ALL of these (nothing optional)
An episode is NOT finished until every one of these exists and is approved:
1. **Final video** — `PP-EPxx-FINAL.mp4` (QC-passed).
2. **Captions** — the SRT.
3. **E-book PDF** — `PP-EPxx-ebook.pdf`.
4. **Thumbnail** — `PP-EPxx-thumbnail.png` (racing-photo style + hook). ← the one most likely to be forgotten; never skip it.
5. **YouTube title + description** — `PP-EPxx-youtube.txt` (recommended title + alternatives + full description; the real e-book link is pasted in at upload).
   **WHO WRITES IT: Claude Code.** Jodie's ruling, 26 Jul 2026 — ownership moved from Cowork to
   the build side. Claude Code writes the title and description into
   `PP-EPxx/output/PP-EPxx-youtube.txt` per `docs/youtube-metadata-kit.md`; **Jodie uploads.**
   *Stated here because this file is canonical and every other document defers to it — and
   because this exact ruling has gone wrong twice by living only in the documents that defer.*
6. **Assembly report.**
Jodie approves the video, e-book, thumbnail AND title. Do not declare an episode done if any of these is missing.

## 🔒 WORDS GATE — lock the words BEFORE any visuals (added 25 Jul 2026, Jodie's #1 fix from EP08)
The EP08 lesson: thumbnail, cover and title card were built, THEN the title/byline changed — rework
on three assets. Never again. **The words come first; every visual uses the locked words.**
- **What gets locked:** the episode TITLE, the **HOOK** (the big thumbnail text, e.g. "Bet Less,
  Win More"), the BYLINE (the one-line sentence-case promise, e.g. "How professional punters make
  punting pay"), and the signature concept. Draft them at create time (Cowork), surface them on the
  ticket (`title` column; `Hook: …` and `Byline: …` lines in `notes`).
- **The hook is shown on the gate card** (added 26 Jul 2026, EP10 lesson: the hook was never
  consciously signed off). Approving the words means approving the exact words the thumbnail will
  carry — if the hook line is missing, the card says so. Enforced by `app.js → gateWords()`.
- **The gate:** a queued episode is NOT claimable by the engine until Jodie/Hugh approve the words —
  the board's early **"Approve the words"** control (it sets `title_approved`). No thumbnail, cover,
  e-book, title card or video is built before that. (Mechanically: the engine's claim filter skips
  queued episodes with `title_approved = false`.)
- **Downstream:** the locked title/byline flow verbatim into the thumbnail hook+byline slots, the
  cover, the title card and the YouTube copy. At final approvals, Title shows as already approved
  (it was — early); un-approving it pulls the episode back before publish.
- Changing the words AFTER the gate = a deliberate revise (Phase 3 change-request), not a tweak.

## 🔒 SCRIPT GATE — a human reads the script before anything is built (Jodie, 26 Jul 2026)
**Approving the script is a DECISION, and decisions stay human — forever, including after HeyGen
auto-render lands. Starting a render is a CHORE and may be automated. Automation eats chores,
never decisions.**
- **ONE SCRIPT, ONE HOME.** The script lives as a **Google Doc in the episode's Drive folder**,
  written there by Claude Code at the create step (`pp-episode-script` skill). From the moment it
  exists, that Doc is the single source of truth. `docs/spoken-words.txt` is a **derived cache** the
  engine overwrites from the Doc at the start of every build — no second copy is authoritative.
- **The gate:** the board's words card carries a link that opens the Doc, editable boxes for
  title / hook / byline, and a tick box labelled exactly **"I've read the script"**. The gate passes
  only when **BOTH** are done — words approved AND the tick set. Until then the engine cannot claim
  the episode (`rail.claim_next` filters on both).
- **Re-read on approval.** The engine's first build step (`script_sync`) re-reads the Doc and builds
  from that text. The operator will have edited it; a studio that ignores its reviewer's edits is
  worse than no gate at all. The engine NEVER builds from its own cached draft.
- **Snapshot + lock.** On approval the exact approved text and its sha256 are stored on the episode
  record (`script_snapshot`, `script_sha256`) — the audit trail of what Gordon actually said.
- **Fail loud, never fall back.** If the Doc can't be read, the episode gets `needs_look` with a
  plain-English message. If the Doc changes AFTER approval, the card shows a flag (it does not block)
  and the build keeps using the approved snapshot.
- **HARD RULE, NO OVERRIDE:** auto-render may NEVER fire on a script that hasn't passed this gate.
  There is no flag, no fast path, no exception. Enforced in code by `engine.assert_script_gate()`,
  called at `script_sync`, `audit_inputs` and `render_gate` — any future auto-render path must call
  it too.

## 🔒 THE LOCKED ORDER — how an episode is built (approved by Jodie, 26 Jul 2026)
The EP10 lesson: the HeyGen render was triggered near the END, and the cover pick was surfaced
AFTER the render instead of during it — so a human waited on a machine that was waiting on a human.
**Do not re-sequence this without Jodie's explicit re-approval.**
1. Paste the article → Claude Code writes the script into a Google Doc in the episode's Drive
   folder, plus the words (title / hook / byline).
2. **HUMAN TURN 1 — Script Gate + Words Gate.** Read the Doc, edit it, tick "I've read the script",
   approve the words. Nothing builds before BOTH are done. The engine then re-reads the Doc.
3. On approval, **two things fire AT ONCE, in parallel:**
   (a) **HUMAN TURN 2 — start Gordon's HeyGen render.** This is the LONG POLE (5-45 min) and
   depends only on the spoken track, which is final at step 2 — so it starts EARLY, never last.
   (b) The engine's gens batch — b-roll **plus both cover heroes (A/B)** plus the motion cards.
4. **HUMAN TURN 3 — cover pick,** surfaced the moment the two heroes exist, i.e. WHILE Gordon
   is still rendering. Heroes A/B upfront → operator picks → cover page built from the pick →
   end card composites it.
5. The engine finishes b-roll / cards / cover page while the render cooks. Hands-off.
6. Master lands → auto-fetched → shot map (WhisperX) → assembly (with the picked cover) → QC.
7. **HUMAN TURN 4 — the four approvals** (video / e-book / thumbnail / title). Final human turn.
8. Publish → automatic Stage-8 close-out (folder rename, deliverables restemmed, rail links updated).

**The shape to preserve:** human turns 1-2-3 cluster back-to-back at the FRONT, then a long
hands-off render window, then turn 4 at the END. Never let the render be triggered last; never let
it become human-waits-machine-waits-human ping-pong.
**Enforced by** (per the QC-per-fix rule): the engine's step lists, `check_locked_order()` at engine
start, and the run-time `build_state.order` stamps that warn if the render is offered after the gens
batch starts or the cover pick lands after the master. See `episode-studio/engine/README.md`.

## Host, voice & render
- **Host** "Gordon", HeyGen avatar look `de774dd2f3ef4a52bc31dee6fc91f118` (the favourited "seated at desk" Floyd, under HeyGen **Public Avatars**). Render on **Avatar IV**.
- **Voice** the standing "Floyd"/PP Gordon voice baked into the template. It sounds Australian; it is **NEVER ElevenLabs** (that engine forces a US accent — it cost a full day on EP04). If ever set manually: voice engine **Auto**, accent **English (Australia)**.
- **Background** the saved grandstand/racecourse image — baked into the standing template; identical every episode.

## ⏸ HeyGen human step + standing template (the anti-bug)
- Presenter generation is a **human step** (Jodie, HeyGen web app, free-plan credits). The pipeline **pauses and waits**; it does **NOT** auto-generate.
- **Standing template `template_id: 5f4b2ed0e33a4351ae4debfbf804d7f2`** ("PP Gordon") bakes in avatar + voice + grandstand. Only actions: **paste the script → paste the video name in the Title field (top-right) → Captions OFF → Generate.** Nothing to mis-pick.
- **Give Jodie the exact video NAME to paste into the Generate dialog's Title field** (top-right corner) — she types it herself (programmatic set won't stick). Convention: **`PP-EPxx — <Episode Title>`** (e.g. `PP-EP06 — Early Pace Power Factors`). The runner/Cowork must surface this name at the human-step, not just the script.
- Do NOT automate the HeyGen create-v4 editor (screenshots come back blank; the rich script box rejects synthetic typing — it only accepts a synthetic `paste` event into an EMPTY box; the title field won't take programmatic text). Avoid all of that by using the template + human step.
- Captions must be **OFF** at generate (the toggle is unreliable).
- **Timing:** Claude Code **generates its own timing (WhisperX forced-alignment on the master)** — HeyGen's API returns **no SRT**, so do NOT put "pull the SRT" in a brief or wait for one. Cowork gives clean spoken-words (one paragraph per beat, body + outro) and the beat map in `episode.json`.
- Claude Code downloads the **~189 kbps master via the API `video_url`** (NEVER the web "Download" button, ~123 kbps robotic; QC fails < 180 kbps). `template_id` is a named, stored input — never hard-guessed.
- **Auto-pickup — no manual video_id hand-off.** Once the human render is kicked off, Claude Code does NOT wait idle and does NOT ask anyone for a video_id. It runs the parallel build, then **polls HeyGen for the render BY PROJECT NAME** (`PP-EPxx — <Title>`) via the HeyGen MCP: **first check ~25 minutes after the render started, then every 2 minutes** until it shows complete, then downloads the master itself and continues to assembly.
- **API automation (optional, not yet on):** HeyGen's API is a separate pay-as-you-go wallet ($0.00 now); web-plan credits don't cross over. Avatar IV via API ≈ $4 USD/min (~5× current); Avatar III via API ≈ $1 USD/min. Only pursue after an A/B quality test.

## Brand & on-screen
- Colours: burnt-orange `#DA532C` + white/charcoal `#1F1F1F`. Anton headlines; huge orange payoff figures that slam/scale in; generous space.
- **Bottom-right PP logo for the ENTIRE video, sitting on a semi-transparent black rounded panel** (reuse the EXACT EP02/03/04 dark-chip treatment — opacity, radius, padding, size, position). Never the bare logo. Bake into the standing logo template. Logo also appears on the warranty slide. Use the WHITE-wordmark logo on dark art.

## Motion-graphic cards
- **⏱ CARD ENTRY = SPOKEN CUE + 3.0 SECONDS (Jodie, 27 Jul 2026 — supersedes the old "on or just after the cue").**
  Jodie watched EP11's first build with cards entering 0.4s after the cue and they **still read
  as early**. The standing value is now **a full 3.0 seconds after the cue is spoken**, timed
  off the WhisperX-anchored shot map — never off QC's rounded entry times, which are
  rounded to the beat and will put you ~0.5s out.
  - **CARDS WITH NO CUE INHERIT THE SHIFT OF THE CARD THEY FOLLOW.** The card layer moves as
    ONE PIECE. An un-cued card has nothing for the +3.0s rule to grab, so if the cards around
    it move and it doesn't, the card before it lands on top of it. (EP11: C6 and C8 had no
    cue, stayed put, and were overrun by C5 and C7. Jodie's ruling: *"if they all move down
    then none should touch still"* — they are not exceptions.)
  - **SHIFT THE WINDOW, NEVER SHORTEN THE CARD.** Move the out-point with the in-point. A card's
    on-screen duration is a separate decision from when it enters; absorbing the delay by
    trimming the tail is not allowed.
  - **Re-verify after every shift** and before assembling: zero card-card overlaps, zero
    card-midroll overlaps, no hold below `min_card_hold`. If a card cannot take the full shift,
    that is a decision for Jodie — never silently shorten it or quietly give it a smaller offset.
- **Card sync (locked 25 Jul 2026; tightened after EP10 review; entry delay superseded above):** every card ENTERS on or just after its spoken cue (never before; timed off the WhisperX-anchored shot map) and HOLDS at least `min_card_hold` (10s from EP09) or until the next card needs the frame. When the cue is a phrase INSIDE the beat (not its opening line), give the card a `"cue"` field in episode.json — QC locates the phrase in the master's SRT and hard-fails a card that enters before the words are spoken. **HARD RULE: b-roll clips, motion cards and the midroll chip NEVER share the screen** — a card writing over a clip means one of them wasn't seen; QC computes every window (assembler maths: `broll_offsets` default +1.0, `broll_dur` 5s) and hard-fails any overlap. The midroll chip must SPAN the spoken ask (like -> subscribe), not precede it — anchor `midroll.at` to the SRT. `qc_episode.py --episode` hard-fails a breach of any of these.
- **Midroll lower-third (locked 25 Jul 2026; duration tightened in script-skill v1.1):** composited over Gordon during the invitation (`build.midroll.composite: true` from EP09) and ALWAYS carries visible like (thumbs-up) + subscribe icons, with **≥6s of full visibility** (fades on top of that — `midroll.dur - 2×fade ≥ 6s`; EP09 shipped 5.0s under the old bar). QC probes the chip region mid-invitation AND checks the visibility maths — hard-fails on either.
  **STANDING FURNITURE, IDENTICAL EVERY EPISODE (Jodie, 28 Jul 2026)** — it is copied
  byte-identical from the production skill's `assets/`, like the end card and the warranty
  slide, and is NOT authored per episode. Its wording, its opaque `#121212` background and
  its white-glyph-on-solid-orange icon tiles are locked, each with the reason recorded
  beside it in `docs/midroll-line-pool.md` §The on-screen chip. **The chip does not rotate;
  the SPOKEN line does** (§Mid-video).

- **🎥 WHILE AN ON-SCREEN CARD IS VISIBLE, THE SHOT MUST BE WIDE (Jodie, 27 Jul 2026).**
  **Binds ON-SCREEN (panel-push) cards ONLY.** Full-frame cards are unaffected — the host is
  not in shot, so there is nothing to crowd.
  **Preserve the mix.** Jodie, watching the rebuilt EP11: *"I love how you have a mix of whole
  screen and on the screen with the host."* The fix is never "make every card full-screen".
  **What went wrong (EP11, not retro-fixed — corrected from EP12 on):** the close/wide shot plan
  was derived from the card timings as they stood BEFORE the +2.6s card shift. The cards moved;
  the shot plan did not. Nothing recomputed it and nothing compared the two afterwards. So a
  card designed to sit beside Gordon in a wide shot was still on screen when the camera pushed
  in, and it landed over his face for a second or two.
  **THE ENGINE FIX (EP12 on):** the shot plan must be **DERIVED FROM the final card timings**,
  not computed alongside them, so it cannot go stale by construction. If it stays a separate
  step, it must run **after** the card windows lock and **re-run whenever they move**.
  **THE QC CHECK:** for every on-screen card window, assert the shot is WIDE for the **WHOLE
  window, entry to exit** — not merely at the in-point. Report the pair count checked, the way
  the four overlap classes are reported.
- **⚠️ THE GENERAL LESSON — WHEN A TIMING CHANGES, ASK WHAT WAS CALCULATED FROM IT.**
  This is the same failure four times over in one day: a value derived from something else,
  still pointing at where that something else used to be. `midroll.at = 235.0` was a word-count
  estimate that went stale. The b-roll offsets were fine until the cards moved onto them. The
  shot plan was derived from pre-shift card timings. A stale derived value passes every check
  that only looks at it in isolation. **Before declaring a timing change verified, list what
  else was computed from that timing and re-derive each one.**
- **🚫 NEVER CHANGE OR "CORRECT" THE SOURCE ARTICLE (Jodie, 27 Jul 2026 — standing rule).**
  **If Practical Punting made a mistake in 1995, it stands. Their article, their call. We
  reproduce, we do not improve.** No fixing a figure that looks wrong, no tidying a date, no
  correcting a name, no smoothing an inconsistency — not in the spoken track, not on a card,
  not in the e-book. If something looks wrong, **flag it to Jodie and reproduce it as written**
  while you wait. The only permitted departures are the ones already named: reading for the
  ear (numbers as words for TTS) and disclosed typographic tidies, each one listed in the
  build report.
  **This is the mirror of the rule below, and the pair must be read together:** *never add what
  the article does not say* (below), and *never remove or alter what it does* (here).
  **Where the line falls — the EP11 worked example:** card C7 displayed "2nd Juggler" and "3rd
  Brave Warrior". Alan listed four beaten horses and gave no placings. **Deleting those
  placings RESTORES the article; it does not edit it.** Adding them was the edit.
- **🚫 NEVER FABRICATE RACING DATA (Jodie, 26 Jul 2026 — standing rule).** Every figure, form
  line, price, margin, date, horse name and race name on a motion card, in an e-book figure or
  on a thumbnail must come from **the source article**. Do not invent a plausible-looking form
  line to fill a layout, do not make up an odds column to give a chart something to plot, do
  not round or "tidy" a figure into something neater.
  **Why:** a Practical Punting asset carries PP's authority. A reader who trusts the brand will
  read an invented form line as real, and act on it. That is a different and worse failure than
  an ugly card.
  **How to apply:** if a card design needs data the article does not supply, **change the
  design, not the data** — use the article's own words, dates or race names, or drop the
  element. Say so when you do. (EP11: a card specced "a column of form figures" for a magnifier
  to sweep; the figures did not exist in the article, so the sweep was rebuilt over the
  article's own clue phrases instead.) This sits alongside the existing numbers rule — figures
  are editorial and a HUMAN ticks them — and the never-narrate-an-unverified-number rule.
- All graphics are MOTION graphics (animated HTML on the shared engine), never statics, never text-in-Higgsfield.
- **A MIX of full-screen AND partial-screen "Panel-Push"** (centred Gordon glides right; left-third panel shows the graphic; push far enough that no panel ever touches him — overlap = QC fail). Do NOT make every card full-screen.
- Style: 16:9 charcoal, rounded corners, orange rule + eyebrow, Anton headlines, orange payoff figures, PP logo BR. One idea per card, real animation, numerals on cards (spoken track says them as words).
- Standing cards reused: TITLE, END CARD (real e-book cover + free-e-book link line; NO responsible-gambling elements here), WARRANTY (identical, sober near-black).
- **Dependency:** the END CARD composites the **real e-book cover**, so the cover (and its Higgsfield cover hero) must be built **before final video assembly** — the assembly gates on the cover, not just on the presenter master, b-roll and cards.

## B-roll & all generated imagery with people
- **HARD-FAIL list (locked 25 Jul 2026):** riderless / rider-detached / broken-anatomy horses;
  people undressed or partly undressed; any object passing through a body; extra/missing/fused
  limbs. Any clip showing these is regenerated — never shipped. The engine exports a 6-up
  `broll-contact.png` after collection for the human glance at the render gate, BEFORE assembly.
- **~50% of people wear a hat** (Akubra + fedora types included — Australian racing crowd).
- **Australian ethnic mix ≈ 75% white, 9% Asian, 9% Middle-Eastern, 5% Black, remainder a mix.** Wide age range. Reject uniform crowds at QC.
- **Turf only** — lush green grass track, never dirt (models default to US dirt — specify "lush green turf track" every time; reject dirt).
- Relevance is law: every clip matches the exact line it plays under. ~5 s each. **No clip repeats within an episode** (audit at assembly). Photoreal footage only; atmosphere over galloping.
- **🔁 THE NO-REPEAT LAW IS ABOUT COMPOSITION, NOT SUBJECT (Jodie, 26 Jul 2026).**
  **So long as the COMPOSITION is different, the idea or subject can be similar.** A clip is a
  repeat when it *looks* like one on screen — same framing, same angle, same action, same shot.
  Two clips that share a subject but are shot differently are two different clips.
  **Why this is the better rule:** across fifty racing episodes you run out of *subjects* long
  before you run out of *compositions*. There are only so many things that happen at a
  racecourse, but an unlimited number of ways to frame them. The old reading — treating a
  subject as "used up" forever — would have forced the series into worse and worse clip choices
  by about EP15, rejecting a good shot for the wrong reason.
  **Worked example (the ruling case):** EP11's `broll-02`, a tight close-up of a hand wiping a
  chalked price off a bookmaker's board, is **CLEARED** against EP05's `broll-punter-odds-board`,
  a punter standing watching a tote board. Same corner of the world, completely different
  composition — different subject in frame, different distance, different action. Not a repeat.
  **How to apply:** `broll_registry_check.py`'s subject-overlap warning stays **advisory** — it
  flags for a human eye, it does not fail a build. The hard no-repeat check remains the exact
  clip target, within and across episodes. When a check flags a subject echo, judge the
  *composition*: if it would read as a different shot on screen, it ships.
- Photo rights: only PP-owned/licensed or Jodie's own AI stills on published materials — never web images.

## Audio (measured EP02 mix, approved)
- loudnorm to −16 LUFS; music bed ~4%; sidechain-duck under speech (speech always clearly audible).
- Series sting "Sleeves Full of Aces" (Alexandra Woodward, Epidemic Sound): full 0–4.5 s → fade ~1 s → low bed once Gordon speaks → **returns at the end card → soft under the warranty slide**. The end is NEVER silent.

## 🔚 END SEQUENCE (locked 25 Jul 2026 — the EP08 lessons, enforced by QC)
Every episode's ending obeys these, and `qc_episode.py --episode` HARD-FAILS any breach:
1. **~3s settle** — Gordon's last word lands ~3s BEFORE the warranty tail begins (assembler
   `end_settle`, default 3.0). He never talks right to the end; the end card + music breathe.
2. **End card sync** — the end card (real e-book cover + free-link) fades in on the e-book beat
   and **stays up until the warranty takes over** (assembler default when `endcard_hold` is
   unset). It must be ON SCREEN while Gordon speaks the e-book line — never come-and-go early.
   QC also samples a frame at the mention (dark-card luminance check).
3. **End music** — the sting returns at the end card and sits soft under the warranty to the
   fade. **The end is NEVER silent** — QC measures the warranty window's RMS (fail ≤ −34 dB)
   on top of the existing last-8s silence check.
4. **Midroll QC** — the midroll invitation comes from the **standing pool of ten**
   (`docs/midroll-line-pool.md`), used strictly in order. **Verbatim reuse within the NINE
   immediately preceding episodes = QC HARD FAIL** (repeated identical text is what HeyGen
   mangled on EP08), and QC exports the midroll audio segment (`midroll-listen.wav`) for a
   human LISTEN — confirm the voice/accent stays Gordon before approving the video.
   **⚠️ NINE, NOT TEN — do not "correct" this.** A pool of exactly ten used in strict order
   recurs at exactly ten-episode intervals: `L3` runs at EP13 and again at EP23. A ten-episode
   window would contain EP13 when EP23 is checked, and would hard-fail **every episode from
   EP23 onward, forever.** At nine, the nearest legitimate prior use is always exactly ten
   back and passes; anything closer fails, which is the intent. Episodes are ordered by the
   number parsed from `PP-EP(\d+)`, **numerically, never by file mtime** — `PP-EP98/` exists
   on disk and mtime ordering would pull it into every window.
   *(Superseded 28 Jul 2026: "the midroll invitation is REWORDED every episode; verbatim
   reuse across ALL episodes = hard fail". The pool makes an across-all-episodes rule
   impossible to satisfy by construction.)*

## Standing OUTRO (every episode)
Gordon always speaks an outro after the last article line, before the end card, in this order:
1. Short warm topic wind-down (episode-specific, 1–2 lines — no hard cut).
2. Point to the FREE E-BOOK — a soft CTA: name the e-book, **"the link's just below this
   video"**, keep it beside you on race day. **"this video", never a bare "this"** — this is
   an ASK, so §Mid-video's *name the video at every ask* rule binds it (Jodie, 28 Jul 2026).
   *(Was: `soft CTA, "link below"`. `PP-episode-outro-standard.md`, the `pp-episode-script`
   skill and both EP11 and EP12 already said "below this video"; this file was the only one
   out of step.)*
3. 🔒 **Responsible-gambling line — MANDATORY AND WORD-FOR-WORD LOCKED:**
   "And remember — never bet more than you can afford to lose."
   **This is NOT part of the sign-off and is NEVER varied.** It is a responsibility line, not
   furniture. The sign-off below is deliberately re-voiced each episode; do not let that licence
   creep into this sentence by association.
4. **Warm sign-off — A PATTERN, NOT A FIXED SENTENCE (Jodie, 27 Jul 2026).**
   Jodie: *"I am happy for Gordon's sign off to be slightly different each time but very similar
   to what has been done so far. Either or a variation are fine."* Hit the shape, reword the words:
   - warm, brief, spoken to one person;
   - a **closing marker** — "That's me for now" / "That's me for this week" / a close variation;
   - **look after yourself**;
   - a **nod to their form study or their punting**;
   - **see you soon**.
   - **Never** a promise about winning, and **never** urgency. Not "Good punting"; no "this is
     just a game" line.
   **Reword it every episode; never repeat a previous episode's sign-off verbatim.** Same
   principle as the b-roll no-repeat law (composition, not subject) — recurring furniture
   gets re-voiced so it never sounds canned.
   *(Corrected 28 Jul 2026: this used to read "same principle as the midroll chip (reworded
   each episode)". **The chip is now fixed standing furniture, identical every episode**, so
   that analogy was factually wrong. The sign-off remains a re-voiced pattern; the midroll
   SPOKEN line is now a fixed pool of ten, which is a third thing again. Three different
   treatments — do not collapse them.)*
Rendered with the same avatar/voice/background. Only line 1 (the wind-down) and line 4 (the
sign-off) change per episode; lines 2 and 3 hold.

## Mid-video like/subscribe invitation (every episode — Hugh's standard, added 23 Jul 2026)
Gordon gives ONE gentle, authentic like-&-subscribe invitation in the MIDDLE of the video (there's a lot of competing content out there; we want the sensible stuff to reach the right people).
- **Placement:** at a natural breath/transition, roughly the middle (~45–55% through), on a beat boundary with Gordon on camera (MCU) — never over a card, never mid-concept, never near the outro. ONCE per episode.
- **Tone:** the outro voice — warm, plain, wry, Australian. NO hype, NO "smash that like button", NO promises. A quiet, honest ask tied to value, then straight back to the content.
- **Shape (fixed):** soft value hook ("if this video is helping you") → the ask (a like helps others find it; subscribe) → the cadence line (below) → a light, wry nod to the noise out there → return to content ("right — where were we").
- 🔒 **NAME THE VIDEO AT EVERY ASK (Jodie, 28 Jul 2026 — standing rule).**
  **Wherever Gordon ASKS something of the viewer — like, subscribe, get the e-book — name it
  "this video", never a bare "this".** Clarity drives action, and an ask is the one place
  vagueness costs something. *"If you're getting value out of this"* → *"If you're getting
  value out of **this video**"*.
  **NARRATION IS EXEMPT.** The opening framing line stays as written: it is a hook, and
  "this time" against "last time" is doing different work there. Forcing "video" into it
  makes it clunky.
  **This is a principle, not a list of places, so it generalises to asks we have not
  invented yet.** Today it binds the midroll invitation (here) and the outro e-book line
  (§Standing OUTRO item 2).
  *Origin: Jodie's own hand-edit at the EP12 Script Gate — "If this is doing its job" →
  "If this **video** is doing its job" — one of only two changes she made to twenty-six
  paragraphs, and not reported at the time. It is a rule now rather than a silent
  correction.*
- 🔒 **THE WORDING COMES FROM A POOL OF TEN — IT IS NEVER REWRITTEN (Jodie, 28 Jul 2026).**
  **This SUPERSEDES the previous "VARY it every episode / reword this slightly each episode
  / fresh phrasing" rule entirely. Do not restore that wording.** The old rule asked for
  fresh prose every episode, which meant the build was writing the ask — and a build that
  writes its own copy can write anything.
  - **Ten pre-approved lines, `L0`…`L9`, in `docs/midroll-line-pool.md`. Episode N takes
    `L[N mod 10]`, strictly in order.** The pool **wraps** rather than exhausting, so the
    build never halts for want of a line.
  - **The lines are never rewritten.** Changing one is a new batch approval, not an edit.
  - `episode.json` records the choice as `build.midroll.line_id`.
  - **HARD FAIL if the midroll paragraph is byte-identical to any of the NINE immediately
    preceding episodes** (see §END SEQUENCE item 4 for why nine, not ten).
- **THE ON-SCREEN CHIP IS SEPARATE AND DOES NOT ROTATE.** It is fixed standing furniture,
  identical every episode, copied byte-identical like the end card and the warranty slide.
  Wording, background opacity and icon treatment are locked in the standing asset with
  their reasons recorded beside them — see `docs/midroll-line-pool.md` §The on-screen chip.
- **Cadence line — LIVE VARIABLE:** current upload cadence is **DAILY** (as of Jul 2026), moving to **weekly** later — the line must reflect this ("a fresh one every day at the moment, weekly down the track"). **Update this when the cadence changes.**
- **In the build:** it's its own `episode.json` beat (`cta-midroll`), part of the spoken script Jodie renders in HeyGen (same avatar/voice/background); timing + assembly place it like any other beat.

**THE TEN APPROVED LINES LIVE IN `docs/midroll-line-pool.md`.** They are not duplicated
here — one home, per §WHERE RULES LIVE. That file also carries the `ep → line id` registry.

*The three "example variants" that used to sit here were removed on 28 Jul 2026 and are
NOT to be restored. They were examples of a rule that no longer exists (reword every
episode), and leaving illustrative prose beside a fixed pool is how someone ends up
writing an eleventh line.*

## Warranty slide (verbatim, every video, every e-book)
PP logo on the slide; warranty text at the TOP; at the BOTTOM the large heading "WHAT ARE YOU PREPARED TO LOSE TODAY?" then "For free and confidential support call 1800 858 858 or visit gamblinghelponline.org.au". No sales@ on the video slide. Full text in the standing template.

## E-book
- **"verify" markers are REVIEW-ONLY (locked 25 Jul 2026):** a cell whose source was unreadable renders as a highlighted "verify" during review, and MUST resolve to a real number or the standard insufficient-data dash before approval/publish. `qc_episode.py --episode` HARD-FAILS any build whose e-book source still contains a verify marker.
- **Cover layout (locked 25 Jul 2026):** built from the canonical `assets/ebook-cover-template.html` — the white band is a FLOW layout (subtitle → byline → footer stack; overlap impossible by construction), and `cover_check.py` auto-FAILS any overlapping or clipped cover text (the EP09 collision). Never position band text with absolute pixel offsets.
- **📚 SERIES PART TREATMENT (Jodie, 26 Jul 2026).** How "Part N" is set depends on the
  length of the title:
  - **Long title — keep the em dash, inline.** When the title is long enough that
    "— Part N" sits on a line with words beside it, leave it at full title size with the
    dash (as EP10, *"The 12 Vital Form Factors — Part 1"*).
  - **Short title — drop the dash, half size, own line.** When the title is short enough
    that "Part N" falls to a second line, **drop the em dash** and set "Part N" at about
    **half the title size** on its own line, still orange (as EP11, *"HIDDEN ACES / PART 1"*).
  - **Why:** on a short title the full-size dash lands alone at the start of a line and
    reads as a stray mark rather than punctuation.
  - **Applies to the cover, the in-video title card AND the thumbnail**, so a series reads
    consistently across all three assets. Decide once per episode from the title length and
    use the same treatment everywhere.
- Article near-verbatim, print-friendly light pages, warranty at the end, soft CTA to the tips service.
- **E-book figures = the print render of the video's motion cards** — ONE design source, so the book can never drift from the video. Cowork maps each figure to a card (`figure N = card CXX` in `episode.json`); Claude Code renders the figure **straight from the card HTML** (its e-book/print variant) to PNG with Playwright/Chromium. **Not Higgsfield.**
- Article-body HTML uses the template classes: `.kicker`, `h1.section`, `.byline`, `.lead`, `h2.rule`, `blockquote`/`.pullquote`, `img.illus` (+ `.portrait`), `.pagebreak`. Warranty + marketing pages come from the template.
- Claude Code owns the shell + `build_ebook.py` and BUILDS the book. **Page order: cover → body(+illustrations) → marketing (2nd-last) → warranty (last).** Logo on every page. Batch ALL illustrations, present the finished book for ONE approval.
- Cover: keep the established template (logo chip TL, orange eyebrow rule, big Anton title over a Higgsfield hero, white band w/ byline + footer). Footer reads "A Practical Punting guide · practicalpunting.com.au" — no source attribution on the cover. Build cover text as real HTML layers so wording changes never need a re-gen.

## Thumbnail — a MANDATORY, first-class deliverable (the step most likely to be forgotten)
- Every episode ships a thumbnail. It is on the **Definition of Done** checklist and has its own Jodie approval — never optional (EP05 shipped without one because it was informal). Since it's a racing photo (not a host frame), it no longer needs the finished video and can be produced in parallel with the build.
- **Racing-photo style (channel look — decided 23 Jul 2026; supersedes the old "real Gordon frame" rule):** the thumbnail is a striking racing scene/photo — lush green turf, atmosphere, from Higgsfield or a PP-owned/licensed still — NOT the host's face. 1280×720, <2 MB.
- Bold Anton caps, colour-split headline, orange eyebrow, small WHITE-wordmark logo in a corner. The thumbnail text is a HOOK (3–5 words), different from — but not contradicting — the title. Strategy/curiosity only; no odds/guarantees.
- ⚠️ **OUTSTANDING — the thumbnail template does NOT yet carry the series part treatment.**
  The §E-book SERIES PART TREATMENT rule (Jodie, 26 Jul 2026) applies to the cover, the
  in-video title card AND the thumbnail. `assets/ebook-cover-template.html` was given the
  opt-in `.part` class on 26 Jul 2026 and is done. **`assets/youtube-thumbnail-template.html`
  has NOT been updated** — it already does the colour split via `.l1`/`.l2` but has no
  "Part N" option at all. Until it does, a short-title series episode will need the
  treatment hand-added to its thumbnail page, which is exactly the drift the rule exists to
  prevent. **Not yet done, deliberately deferred — do not treat this bullet as satisfied.**

## Audience & voice
- Write everything for "Dave" (see the pp-my-audience-avatar skill). Gordon's voice: warm, plain, wry, Australian, zero AI-slop words.

## 🏠 WHERE RULES LIVE — ONE HOME (Jodie, 27 Jul 2026)
- **The GitHub repo is the single home for everything that governs behaviour**: code, standards,
  skills, specs, decisions.
- **The claude.ai project is a JOURNAL.** It holds **no rule text** — pointers only.
- **Google Drive** keeps media and episode outputs. **Supabase** keeps runtime state.
- **🧩 THE INSTANCE/RECIPE TEST — how to tell code from media when a file is both
  (Jodie, 28 Jul 2026).** Some files are *shaped* like code and *behave* like output.
  The test is not the file extension:
  > **The RECIPE lives in git. The INSTANCE lives on Drive.**
  A motion card's HTML template is a recipe → repo. The episode's rendered
  `ep12-c01-….html` and its `.mp4` are instances → Drive. **Worked example (the ruling
  case): `Channel-Branding/banner.html`, `thumbnail.html` and `PP-brand-kit.html` STAY
  ON DRIVE.** They are one-off channel assets built beside their large source PNGs, and
  their template — `assets/youtube-banner-template.html` — is already in the repo skill.
  Instance on Drive, recipe in git. **This is not an exception to CODE IN GITHUB, MEDIA
  ON DRIVE; it is what the principle means.** Ask "would I edit this to change every
  future episode, or did it come out of something I would edit?" The first is a recipe;
  the second is an instance.
- **Any rule Jodie approves is written ONCE, in the repo, by Claude Code. Cowork never writes
  rules.**
- **👥 WHO DOES WHAT — the division of labour lives in `docs/WHO-DOES-WHAT.md`** (ruled by Jodie,
  27 Jul 2026). In one line: **Claude Code creates and builds everything that ships** — script,
  motion cards, b-roll, e-book body and cover, thumbnail and its hero, YouTube copy. **Cowork
  plans, remembers, reviews and checks, and nothing else** — no episode assets, no rules, not one
  line of anything that ships. **Jodie approves and publishes** (Words Gate, Script Gate tick,
  cover hero pick, the four artefacts, the upload). **Hugh** is co-owner and reviewer, and the
  person the hands-off studio is for.
  *Named here as well as there for the same reason the YouTube-copy owner is: a ruling that lives
  only in documents which DEFER to this one is a ruling waiting to go wrong.*
- ✅ **FULLY IN FORCE — THE REPO IS PUBLIC AND STAYS PUBLIC (Hugh, co-owner, 28 Jul 2026. FINAL.
  DO NOT RE-OPEN).** `github.com/Practical-Punting/episode-studio` is PUBLIC
  (`gh repo view` → `"isPrivate": false`; anonymous fetch returns HTTP 200) and that is the
  settled, deliberate arrangement. **No split, no flip to private, no paid plan.**
  **Hugh's reasoning, recorded so nobody re-litigates it:** the `pp-episode-script` skill and
  `broll-registry.md` are **marketing material, not trade secrets** — the episodes are built
  from articles Practical Punting **already publishes openly**. There is nothing behind the
  curtain that is not already on the website. This is the co-owner's **commercial judgement**,
  and commercial judgement is his and Jodie's to make, not the build side's.
  **This SUPERSEDES the "middle road" of 27 Jul 2026**, which read: *"Genuinely commercial craft
  stays out: the `pp-episode-script` skill and `broll-registry.md`. The Tier 2 material still
  needs a private home."* **Do not restore that wording.** Its practical effect was a rule that
  the practice already ignored — and see §TIER 2 for why that is the dangerous kind of rule.
  **What survives unchanged is TIER 1** (below): secrets and subscriber data never go anywhere,
  public repo or not.
- **🧭 IF YOU MOVE A FILE, EVERY SIGNPOST AIMED AT IT MOVES WITH IT (27 Jul 2026).**
  A signpost pointing at a path that no longer exists is **worse than no signpost**: it reads as
  authoritative and sends the reader nowhere. Archiving `thumbnail-standard.md` into
  `docs/archive/` broke its Drive stub within the hour of writing it. **After any move or
  rename, re-audit every stub and every cross-reference and confirm each target actually
  resolves** — check the file is there, do not assume it is.

## 🔒 WHAT MAY BE STORED AND SHARED WHERE — THE TIERS (Hugh's ruling, 28 Jul 2026)
**Two live tiers, and the line between them is bright.** TIER 1 is absolute. Everything else
that governs behaviour goes in the public repo. TIER 2 is retained as a **named, empty**
category so there is a place to put something genuinely secret if it ever exists — but it has
**no members today, and adding one is a Jodie-and-Hugh decision, not a build-side judgement.**

**Still true, and the reason the tiers exist at all:** *link-sharing* means anyone with the
address — no login, no record, no attribution. A repo means named, logged, attributed access.
**They are not the same risk and must not be governed by the same sentence.**

### 🔴 TIER 1 — NEVER ANYWHERE. NO EXCEPTIONS. UNCHANGED AND ABSOLUTE.
- **`.env` and every secret in it** — the Supabase **service_role** key (bypasses RLS; reads and
  writes everything) and the **`HEYGEN_API_KEY`** (spends real money).
- **Subscriber data. E-book download lists.** Any future list of real people.
- `.env` is **deliberately never backed up**, and `.gitignore` blocks `.env` / `*.env`.
- **The repo being public changes NOTHING here.** It was never the thing protecting TIER 1;
  TIER 1 is protected by never being written down anywhere a machine can copy it.
- ⚠️ **THIS IS THE TIER THAT MATTERS, AND IT IS THE ONE AT RISK FROM A SLACK NEIGHBOUR.**
  TIER 2 was rewritten (not quietly ignored) precisely so this one keeps its force. **A rule
  nobody enforces teaches people to shrug at the tier that does matter.** A standard that says
  "never public" about something already sitting in a public repo trains the reader that the
  security section is aspirational — and the next thing they shrug at is the service_role key.
  **If TIER 2 ever needs a member again, say so out loud and give it a real home. Do not let
  TIER 1 drift by association.**

### ⚪ TIER 2 — genuinely secret material. **CURRENTLY EMPTY (Hugh, 28 Jul 2026).**
**Both former members were reclassified to TIER 3 by the co-owner** — the `pp-episode-script`
skill and `broll-registry.md`. **Reason: they are marketing material, not trade secrets.** Every
episode is built from an article Practical Punting **already publishes openly**; a document
describing how those public articles become videos gives away nothing that the website does not.
Commercial judgement, made by the co-owner.
**The retired wording, for the record, NOT to be restored:** *"TIER 2 — private repo only. Never
public, never link-shared. Method material — the punting methods themselves. `broll-registry.md`.
Reasoning is commercial, not safety: the methods are the product."*
**If something ever genuinely belongs here** — a paid-subscriber-only method, a commercial
partner's material — it needs a private home created for it **before** it is written down, and
a line in this section naming it. Empty is a state, not an invitation.

### 🟢 TIER 3 — everything that governs behaviour. **Fine in the PUBLIC repo.**
- Production standards: card timing, thumbnail rules, the episode JSON spec, `WHO-DOES-WHAT`,
  the outro and midroll standards, the shot-plan rule, the midroll line pool.
- **Code**: the engine, `rail.py`, the `pp-episode-production` build recipes and scripts, the
  standing templates.
- **`pp-episode-script`** and **`broll-registry.md`** (moved here by Hugh's ruling above).
- **Why public is actively better here, not merely tolerable:** every reader gets the IDENTICAL
  file instead of copies that drift, and the work gets history, backup, review and diffs for
  free. That is the whole reason for **CODE IN GITHUB, MEDIA ON DRIVE**.

### LINK-SHARING — narrowed to what it was always really protecting
**Only individual episode script Docs get link-shared. NEVER a whole folder, and never anything
holding TIER 1 material.** A single episode's script Doc is set to "anyone with the link can
view" because the engine has no Google login and reads it via the plain-text export URL; every
word of it is about to be broadcast on YouTube anyway and the URL is unguessable.
**Share the Doc, never the folder that contains it** — sharing a folder shares everything in it
now **and everything ever added to it**, which is how a TIER 1 file ends up shared by an
accident nobody made on purpose. That property is why the folder rule survives Hugh's ruling
untouched.
*(Amended 28 Jul 2026: the clause used to read "never anything holding subscriber data or method
material". "Method material" is no longer a protected class — it is TIER 3 — so the rule now
names TIER 1, which is what it was always for.)*

## Hard "never" list
**Never fabricate racing data** — every figure, form line, price, margin, date, horse or race on a card, e-book figure or thumbnail comes from the source article, or it does not appear (see §Motion-graphic cards); never ElevenLabs; never "tax"/"Agreement Tax"/"20% tax" framing; never hype/promises/guarantees; never a bare BR logo; never all-full-screen cards; never dirt tracks; never a repeated b-roll clip; never publish before the e-book exists; never let Jodie move files by hand; **never link-share a folder, and never link-share TIER 1 material (secrets, subscriber data, e-book lists) — individual episode script Docs only** (amended 28 Jul 2026: "method material" was removed, it is TIER 3 now); **never put a TIER 1 secret in the repo, public or private — that one has no exceptions and never will.**
