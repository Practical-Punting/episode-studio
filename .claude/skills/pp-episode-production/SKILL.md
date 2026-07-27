---
name: pp-episode-production
description: >
  End-to-end production pipeline for Practical Punting YouTube episodes:
  generate + download the HeyGen presenter render, build the shot map, batch-
  render motion-graphic cards to short clips, and assemble the final episode
  (digital zoom + panel push + b-roll + per-card composites + ducked music mix)
  with ffmpeg — AND build the matching e-book PDF and the 1280×720 YouTube
  thumbnail from the standing templates. Use this skill whenever the user
  mentions rendering an overlay or cards, assembling/exporting an episode, "PP
  EP" followed by a number, chroma key / green screen compositing, the Practical
  Punting design system, HeyGen video generation/download, producing the final
  episode MP4, the YouTube thumbnail, or building/fixing the episode e-book or
  its PDF, cover, warranty page or marketing page — even if they only ask for
  one stage. Proven on EP01–EP03; the methods here are approved standards —
  reuse, don't re-derive.
---

# PP Episode Production Pipeline

Proven on EP01 (2026-07-19) and refined on EP02 (2026-07-20, v3 approved).
Works alongside the master `pp-episode-pipeline` skill (process, gates, locked
brand facts) — THIS skill holds the working technical recipes and scripts.

**Folder naming standard (2026-07-24).** An episode folder is
`PP Videos/PP-EP<NN>-<Title-Slug>/` — the approved final title, slugified
(e.g. `PP-EP01-The-Trifecta-Mistake/`). It carries the standard subfolders
`docs/`, `renders/`, `overlay/`, `broll/`, `output/` (+ `music/` on EP01, the
shared music master). Two hard rules:
- **The slug is added at STAGE 8, once Jodie approves the FINAL TITLE** — you
  can't name the folder before the title is locked. Through Stages 0–7 the
  working folder is the bare `PP-EP<NN>/`; the close-out step renames it.
- **Reference every file RELATIVE TO THE EPISODE ROOT** (`overlay/export/…`,
  `output/…`, `renders/…`) — NEVER hardcode the `PP-EP<NN>` folder name or an
  absolute episode path in a script, an `episode.json`, or an ffmpeg graph. The
  folder name changes at Stage 8, so anything with a baked-in episode path
  breaks. (A shared asset in another episode — e.g. EP01's music master — is the
  one legitimate cross-episode reference; keep those few explicit and update them
  if that folder is ever renamed.)
Rename with `python rename_episode.py <NN> "<approved title>" --apply` (in the
`PP Videos/` root) — it renames the folder, restems the `PP-EP<NN>-*`
deliverables to match, greps the whole tree for straggler references, and prints
a before/after report.

**Locked build order** — the e-book COVER is built BEFORE the video, because the
video's end-card "free e-book" motion graphic composites the real cover.
Sequence every episode: **script → cards + b-roll → e-book cover → HeyGen
generate → shot map → assemble video → e-book PDF → thumbnail.**

**Approvals are for FINISHED artefacts only** (the video, the e-book, the
thumbnail). NEVER ask Jodie to approve the script (the article is pre-approved —
and no script email to Hugh), the motion-graphic cards, the b-roll, or
individual e-book illustrations, and NEVER surface tool plumbing for approval —
Higgsfield balance/credits or `models_explore`, or the HeyGen steps. Handle
credits and model choice silently; only raise a tool issue if it genuinely
blocks the build. See `docs/WHO-DOES-WHAT.md`.

## Episode runbook (the happy path — details in the stages below)
-1. **🔒 WORDS GATE (PP-STANDARDS, 25 Jul 2026 — before ANYTHING is built).** The episode's
   TITLE + BYLINE (+ signature concept) are drafted at create time and approved by a human
   on the board ("Approve the words" sets `title_approved`) BEFORE any visual asset exists.
   The engine's claim filter skips queued episodes whose words aren't approved. Byline
   travels as a `Byline: …` line in the ticket's `notes`. All downstream assets (thumbnail,
   cover, title card, YouTube copy) use the locked words verbatim — the EP08 rework lesson.
0. Audit inputs. **⏸ HUMAN STEP — Jodie generates the presenter** in the HeyGen web app from the locked TEMPLATE (open template → paste script → captions OFF → Generate). **Do NOT wait idle and do NOT ask for a video_id** — run the whole parallel build (cover, b-roll, cards, e-book), then **poll HeyGen BY PROJECT NAME yourself** and download the clean 189k master via the API `video_url`. (API auto-generate is a paid opt-in toggle — see Stage 0 + `docs/HEYGEN-HUMAN-STEP.md`.)
1. `build_shot_map.py <clean.mp4> <spoken-words.txt> renders/` → `shot-map.json` + SRT. **Check the real speech onset** (silencedetect); if the silent head is longer than the title window, trim to spec and put shot-map + SRT on the trimmed timeline.
2. **Re-render the e-book cover** from `ebook/cover-src/` (don't trust the handed PNG); propagate to `ebook/cover.png` + `overlay/export/ebook-cover.png`.
3. Copy the standing warranty + end-card into `overlay/export/`; **batch-render every card in one session**: `render_cards_batch.py overlay/export overlay/clips`.
4. B-roll: check `docs/broll-registry.md`, generate NEW clips (none repeated cross- or within-episode), append them to the registry after. **B-roll HARD-FAIL list (Jodie, 25 Jul 2026): riderless / rider-detached / broken-anatomy horses; people undressed or partly undressed; any object passing through a body; extra/missing/fused limbs.** The engine exports `output/qc/broll-contact.png` (6-up stills) after collection — a human glances it at the render gate BEFORE assembly.
5. Pass A `gen_passA_graph.py` (set `HEAD_TRIM` if you trimmed) → `_passA.mp4`; Pass B card composites + v3 audio → FINAL.
6. QC (frames + audio + reconcile speech-end / last-cue / total); `ASSEMBLY-REPORT.md`; copy the SRT beside the output.
7. E-book PDF `build_ebook.py`; thumbnail from a hero + `youtube-thumbnail-template.html` via `render_still.py`.
8. Save the YouTube title + description to `output/PP-EPxx-youtube.txt` — EVERY episode (WE write the copy per `docs/youtube-metadata-kit.md` — Jodie's ruling 26 Jul 2026, moved from Cowork; Jodie uploads).
9. **Stage-8 close-out — rename to the standard.** After Jodie approves the FINAL TITLE, run `python rename_episode.py <NN> "<approved title>" --apply` from `PP Videos/`: the working `PP-EP<NN>/` becomes `PP-EP<NN>-<Title-Slug>/` and the `PP-EP<NN>-*` deliverables restem to match. Do it LAST, once the title is locked; fix any stragglers it reports. **This step is watched (EP10 lesson, 25 Jul 2026): the engine's idle loop flags any PUBLISHED episode whose folder is still the bare `PP-EP<NN>` — the rename itself stays a human-timed step (Drive sync + open files), but it can no longer be forgotten.**
Pause for Jodie ONLY at the finished video / e-book / thumbnail (incl. the final title).

## Toolkit — the standing scripts (v2, 2026-07-23)
The pipeline is now driven by a script toolkit + one per-episode `episode.json`
(contract: `docs/PP-EPISODE-JSON-SPEC.md`; build-side notes + the `build` block:
`docs/PP-EPISODE-JSON-NOTES.md`). Prefer these over hand-building ffmpeg graphs:
- **`pp_doctor.py`** — one-shot toolchain check (`--install` / `--fix-path`). Run first on a new machine.
- **`pp_paths.py`** — `import pp_paths; pp_paths.ensure_path()` so scripts self-locate ffmpeg/ffprobe (no manual PATH prefix needed).
- **`align_srt.py <master.mp4> <out.srt>`** — WhisperX forced-align → word-accurate SRT; pass it as the anchor arg to build_shot_map.
- **`build_shot_map.py <master.mp4> <spoken-words.txt> <outdir> [aligned.srt]`** — shot map + SRT (auto-strips `[SETUP NOTE]` / `#` header blocks).
- **`assemble_episode.py <episode.json> <shot-map.json> A|B`** — emits Pass A / Pass B graphs from the contract; reproduces the proven method (title head, MCU/WIDE zoom, panel-push, b-roll, logo chip, fullscreen cards, outro end-sequence, v3 audio). Fill the `build` block for tuning. **Validated: reproduces EP05 v2 exactly.**
- **`qc_episode.py <final.mp4> <shot-map.json> <out_dir> [--head H] [--episode episode.json]`** — one-command QC: probe + gates, labelled contact sheet, logo crop, loudness/RMS + ending-not-silent check, `QC-REPORT.md`. **With `--episode` (the engine always passes it): the END-SEQUENCE checks** — ~3s settle before the warranty, end card on screen through the e-book mention until the warranty (incl. a dark-frame probe), sting audible under the warranty, midroll wording unique across episodes + a `midroll-listen.wav` exported for human ears (the EP08 lessons; see PP-STANDARDS §END SEQUENCE)), **the PACKAGING-CONSISTENCY check** (each asset source carries the currently-locked slot value from `episode.json → packaging{hook, byline, youtube_title, ebook_title}`; STALE value = HARD FAIL), and **the NUMBERS check** (`numbers-check.md` artifact + a human-confirm WARN).
- **`render_ready.py <spoken-words.txt> [--episode episode.json]`** — pre-HeyGen scan (numbers as words, odd characters, midroll freshness, length). The engine runs it at audit; run it manually before ANY script is pasted into HeyGen. Never waste a render.
- **`rename_episode.py <NN> "<title>" [--apply]`** (in the `PP Videos/` ROOT, not `scripts/`) — the Stage-8 folder rename + `PP-EP<NN>-*` restem + straggler grep + before/after report. See the naming standard up top.
- **`video-logo-chip.png`** (in `assets/`) — the standing bottom-right logo on the dark rounded panel; overlaid in Pass A (`overlay=x=W-w-40:y=H-h-40`).
The detailed Stages below remain the reference for the *how* (the exact ffmpeg
recipes the toolkit encodes). Worked example: `PP-EP05/docs/episode.json`.

## Parallel build + b-roll + e-book figures (v2 flow)
- **Run in parallel while Jodie does the ~2-min HeyGen render:** fire b-roll
  generation, card batch-render, and the e-book PDF concurrently (background tasks /
  subagents). Only final assembly waits on the presenter master. Halves wall-clock.
  **ORDERING CAUTION (EP06 lesson):** the cover chain must finish first — propagate the cover to
  `overlay/export/ebook-cover.png` BEFORE the card batch-render, or the END CARD renders blank
  (missing `ebook-cover.png` → alt-text shows). If batched early, re-render `end-card-template.html`
  after and re-run Pass B.
- **B-roll directly (no Cowork relay):** generate each `broll[]` clip via the
  **Higgsfield MCP** (`generate_video`, kling-style, 16:9, ~5s) from its `prompt`
  (hats + ethnic-mix + turf wording baked in per the standard), then download + QC.
  **Run `broll_registry_check.py <broll-registry.md> <episode.json>` FIRST** — it
  flags any target already logged (cross-episode) or duplicated within the episode;
  `--append EPNN` logs this episode's clips after. Honor the `flags` (`non-turf`
  skips the turf-QC). No clip repeats within an episode.
- **E-book figures = the cards (one design, two uses):** `build_figures.py
  <episode.json> <overlay/export> <ebook_out>` renders each `figures[] {n,card}`
  from the card HTML at 2x. Cards need the **print block** below to render light for
  print; without it they render as-is (the script warns).

**Card print mode (add to the card scaffold so figures render light):**
```html
<style>
 .card.print{background:#fff;color:#1e1e1e}
 .card.print .eyebrow .lbl{color:#DA532C}
 .card.print .anton,.card.print #hl{color:#1e1e1e}
 .card.print .rtxt,.card.print #sub{color:#333}
 .card.print .row,.card.print .box{background:#faf6f4;border-color:#e2c9bf}
 .card.print svg text{fill:#333} .card.print svg .svgnum{fill:#DA532C}
 .card.print .logo{display:none}   /* the e-book has its own header logo */
</style>
<script>if(new URLSearchParams(location.search).has('print')){var c=document.querySelector('.card');if(c)c.classList.add('print');}</script>
```
Refine per card (SVG fills, shadows) as needed; EP05's cards predate this (dark-only).

## Stage 0 — Inputs

**File audit first (always).** Browser downloads land in Downloads with random
or `.tmp` GUID names (EP02's design cards arrived as `<guid>.tmp` — actually a
zip; `file` + `zipfile.testzip` identified it). Locate by name/recency, verify
duplicates by checksum, move into the episode structure, and REPORT the layout
before rendering anything.

**HeyGen presenter** (see memory: heygen-api-setup):
- Key: `PP Videos/.env` → `HEYGEN_API_KEY`, header `x-api-key`. Never print it.
- **API auto-generate tooling (PAID OPT-IN — the ⏸ HUMAN STEP below is the default) — `python scripts/heygen_generate.py
  <spoken-words.txt> <renders/out.mp4>`.** It creates the render via the current
  `POST /v3/videos` endpoint with the locked Floyd avatar
  (`avatar_id de774dd2f3ef4a52bc31dee6fc91f118`) + the **LOCKED SERIES VOICE
  "PP Gordon Floyd"** (`voice_id a6d512a13a3c40c1b79fdd39856a2b72`, an instant
  clone of Jodie's real Floyd voice, engine **Auto**, accent **English
  (Australia)** — ear-confirmed PERFECT 2026-07-22; ends the Floyd/Patrick
  confusion for all ~50 videos). **🚫 NEVER switch the engine to ElevenLabs —
  it hides the Accent control and silently forces an American voice (the EP04
  voice bug that burned a full day); keep the payload engine-agnostic
  (voice_id only).** (Old "Patrick" voice
  `7e157ec62c9c45f1adca12faae72c86f` is SUPERSEDED — source of the wrong voice.)
  **captions OFF** (it omits the v3 `caption` field, so nothing is burned into
  the frame — EP03's burned-caption mess came from a captions-ON browser
  render), polls to completion (matching on `video_url` present — skips phantom
  pendings), and downloads the clean MP4. We build the SRT/shot map ourselves
  (below) — HeyGen's caption file is neither needed nor trusted. **⏸ HUMAN STEP
  (DEFAULT): Jodie generates the presenter in the web app from the locked
  TEMPLATE** — she opens the template (avatar + voice + grandstand backdrop all
  baked in, so nothing to pick or mis-pick), pastes the spoken-words script,
  captions OFF, clicks Generate, then says "it's rendered"; WE then download the
  master via the API `video_url`. Template **`template_id 5f4b2ed0e33a4351ae4debfbf804d7f2`** — record it
  here + in the `heygen-api-setup` memory once Jodie provides it (or fetch it FREE
  via `GET /v3/templates`, a metadata call — no render credits). Prep the script and
  give her the exact click list. **Then DON'T wait idle or ask for a video_id —
  AUTONOMOUS PICKUP (standing behaviour, 2026-07-23):** run the full parallel build,
  then poll HeyGen **by project name** for the render — first check **~25 min** after
  it was kicked off, then **every 2 min** until `status=completed` + `video_url`
  present — via `GET /v1/video.list` (or the HeyGen MCP once authed), matching the
  episode title; then pull the master and go to assembly. Keeps Jodie/Cowork out of
  the pickup entirely. Full detail: `docs/HEYGEN-HUMAN-STEP.md`. **Render path — the human web-app + template
  is the DEFAULT (free plan credits); API auto-generate is the PAID opt-in:** run
  `heygen_generate.py` (POST /v3/videos, or `POST /v3/templates/{template_id}` with
  the script as a text variable) only when API credits are topped up / the pool has quota.
  **`POST /v3/videos` returns `HTTP 402` when the render POOL is empty — this is
  SEPARATE from plan credits** (you can hold plan credits and still get a 402 on
  an empty render pool). On a 402, **render the presenter in the HeyGen web app
  instead** (as EP04 was), then return to the API to download it via `video_url`
  (see the LOCKED AUDIO STANDARD below). Two things to settle on the first
  CREDITED API run: confirm
  v3 accepts the legacy talking-photo `avatar_id`, and set the grandstand
  **background** (`--background-url`/`--background-asset-id`; the asset id isn't
  API-discoverable — flagged in the `heygen-api-setup` memory). `--dry-run`
  prints the payload without spending credits.
- `GET /v3/videos?limit=100` → match on `status=completed` + `video_url`
  present, NOT title alone (opening the HeyGen editor spawns phantom `pending`
  duplicates with the same title).
- `GET /v3/videos/{id}` → `video_url` MP4 → `renders/`. Confirm captions are
  NOT burned in (extract a frame and look).
- **🔒 LOCKED AUDIO STANDARD — always pull the presenter from the API
  `video_url` (the 189 kbps master), NEVER the web-app "Download" button** (it
  re-encodes to ~123 kbps AAC and sounds compressed/"robotic" — this was EP04's
  bug). Even when Gordon is generated MANUALLY in the web app, download the
  render via `video_url` (free — no generation credits). Baseline "great voice":
  AAC-LC, 48 kHz, stereo, ~189 kbps, ≈ −24 to −25 LUFS. **QC GATE: fail any
  episode whose presenter track is < ~180 kbps** —
  `ffprobe -select_streams a:0 -show_entries stream=bit_rate` before assembling.
- The exported SRT is often garbage (EP02: 8×60s auto-chunks, bogus tail) — we
  never rely on it. Run `scripts/build_shot_map.py <presenter.mp4>
  <spoken-words.txt> <outdir> [heygen.srt]` — silence-detects pauses,
  silence-verifies any HeyGen block boundaries as anchors, word-count-
  interpolates the paragraph bounds, snaps to pauses, and emits `shot-map.json`
  + a proper sentence-level SRT for YouTube. It **auto-strips a production-notes
  header** from `spoken-words.txt` (a "PASTE … BELOW" marker or leading pure-`#`
  blocks), so one paragraph = one shot. Set per-shot MCU/WIDE framing from the
  episode's shot script.
- **Verify the real lead-in.** EP03's render came back with a ~12.9s silent head
  vs the brief's 7s title window. `silencedetect` the true speech onset; if the
  head is longer than the title window, trim the excess (pure-silence only —
  don't clip the first word) and put the shot map + SRT on the trimmed timeline
  (subtract the offset from every time). Feed the trim to Pass A as `HEAD_TRIM`.
  Reconcile three numbers before rendering: speech end, last cue end, total.

**No RAM constraint on this machine.** The old 8 GB-Surface rule — keep ~1.5 GB
free per render, close Chrome before rendering, one heavy tool at a time — is
**RETIRED** (this Lenovo is 32 GB, 2026-07-22). Render freely; run concurrent
Chromium/x264 without babysitting. (The Stage-2 "RAM explosion" warning below is
an ffmpeg filtergraph rule, not a machine limit — it still applies regardless of
how much RAM the box has.)

## Stage 1 — Cards (per-card clips; NEVER one full-length overlay video)

Render each motion graphic as its own short clip (in-animation + ~0.5s tail),
then composite at cue time in Stage 2. EP02: 14 cards ≈ 13 min total vs EP01's
~1 hr full-length render. Re-cueable in minutes. **From EP04 we
aim for MORE motion-graphic cards per episode** — the per-card pipeline scales,
so lean into denser card coverage.

- **Standing cards** (in this skill's `assets/`, see its README): the APPROVED
  warranty slide (locked — never redesign), the end-card template (swap in the
  episode's REAL e-book cover; no responsible-gambling elements on it), plus
  `pp-anim.js` + logo. Copy into `PP-EPxx/overlay/export/` as siblings.
- **ppSeek-style Design cards** (`window.ppDuration`, `ppSeek(ms)`, `?paused=1`):
  `python scripts/render_card.py <card.html> <out.mp4> [tail]` for a single card.

- **🚧 AN EPISODE CANNOT GO BACKWARDS — pre-EP12 improvement (found 27 Jul 2026; full note in
  PP-STANDARDS).** When an episode parks at `awaiting_approval` the engine **releases its
  claim**. After that no `acquire()` route reaches it: `resume_own` needs `claimed_by` to match
  (it is NULL), `claim_next` only takes `queued`, and `reclaim_stale` explicitly excludes null
  claims. **Setting the status back to `assembling` without ALSO re-attaching `claimed_by` to
  the engine's worker id strands the episode permanently** — it looks healthy and nothing picks
  it up.
  The board cannot rescue it either: the per-approval **"undo"** buttons are in `gateApprove()`,
  which only renders at `awaiting_approval`; at `ready` the board renders `gatePublish()`, which
  has no approval list at all. So the one control that would move it back is unreachable from
  the state you need to move back from.
  **Until a "send it back a stage" board control exists, a post-approval correction is
  engine-operator work — two scripted rail writes — and is impossible for a browser-only
  operator like Hugh.**

- **🔒 TRACE EVERY FIGURE TO A SOURCE SENTENCE — AUTOMATICALLY, AND HALT ON ANY THAT WON'T
  (Jodie, 27 Jul 2026; pre-EP12 improvement. Also in PP-STANDARDS §PACKAGING, NUMBERS.)**
  `numbers-check.md` currently lists figures with a snippet of the CARD they sit on. That
  proves nothing — it shows the figure next to itself. **It must instead print each figure
  beside the exact sentence in the SOURCE ARTICLE it came from**, grouped by card.
  - **A figure with no matching source sentence is a HARD FAIL that halts the build**, like an
    overlap — not a warning, not a human judgement call.
  - **Cover the e-book figures too**, not only the video cards.
  - **EP11 proved why:** C7 showed "2nd Juggler" / "3rd Brave Warrior". The article names the
    four beaten horses and never gives a placing for any of them — inferred from listing order
    and put on screen as fact. Every automated check passed. It reached the finished video and
    e-book figure 7, and was caught only by tracing 41 figures back by hand.
  - The fidelity rule it enforces already existed in `pp-episode-script` §9: *"If you cannot
    point to the source sentence, it does not ship."* It simply was not enforced anywhere a
    machine could act on it.

- **🎥 SHOT PLAN MUST FOLLOW THE CARDS — WIDE FOR THE WHOLE ON-SCREEN CARD WINDOW
  (Jodie, 27 Jul 2026; also in PP-STANDARDS §Motion-graphic cards).**
  **While an on-screen (panel-push) card is visible, the shot must be WIDE.** Full-frame cards
  are unaffected — the host is not in shot. **Keep the mix**: Jodie, on the rebuilt EP11,
  *"I love how you have a mix of whole screen and on the screen with the host."* Never "solve"
  this by making every card full-screen.
  - **How it broke on EP11:** the MCU/WIDE plan in `episode.json → beats[].framing` was set
    against card timings from BEFORE the +2.6s card shift. The cards moved, the framing did
    not, and nothing recomputed or cross-checked it — so a card meant to sit beside Gordon was
    still up when the zoom pushed in, landing over his face. EP11 ships as-is; fixed from EP12.
  - **BUILD ORDER (EP12 on):** derive the shot plan **FROM the locked card windows**, not
    alongside them, so staleness is impossible by construction. If it remains a separate step
    it MUST run after the card windows lock and re-run every time a lead, hold or offset moves.
  - **ADD TO QC:** for every on-screen card window, assert WIDE across the **entire** window,
    in-point to out-point — not just at entry. Report the pair count, like the overlap classes.
  - **The general trap this belongs to:** a value DERIVED from a timing still pointing at where
    that timing used to be. Same shape as `midroll.at` (a stale word-count estimate) and the
    b-roll offsets (fine until the cards moved onto them). **When a timing changes, list
    everything computed from it and re-derive each one before calling the change verified.**

- **🚧 HARD ENGINE CONSTRAINT — keyframes only (learned EP11, 26 Jul 2026).**
  **Any animation that cannot be expressed as `element.animate()` keyframes is OFF THE TABLE.**
  `ppInit()` builds every animation with `element.animate()`, and the batch renderer draws
  frames by calling **`ppSeek(ms)`**, which sets `currentTime` on those animation objects. A
  JavaScript-driven effect — a numeric **count-up**, a `setInterval` ticker, a canvas loop, a
  typewriter that appends characters — is invisible to `ppSeek`. It does not rewind, so it
  renders **frozen at whatever value it happens to hold**, and the clip is silently wrong.
  Nothing in the toolchain catches this: the batch reports success, `ppDuration` looks
  sensible, and only a human looking at the clip would see it.
  - ✅ Expressible: opacity, transform (translate/scale/rotate), colour, `scaleX` bar wipes,
    staggered reveals via `delay`, multi-stop keyframes with `offset`, sweeps across a strip.
  - ❌ Not expressible: counting a number up, live text changes, anything needing JS per frame.
  - **If a card spec asks for a count-up, substitute the standing hero-figure treatment** — the
    figure scales/slams in (see EP09 C9, EP10 C9, EP11 C3/C5/C9/C12) — and say so, rather
    than shipping an animation that renders wrong.
  - *A number that must visibly climb would need a pre-rendered digit strip translated with
    `steps()` easing. Possible, fiddly; nobody has needed it yet.*
- **Batch-render the whole episode in ONE Chromium session (preferred):**
  `python scripts/render_cards_batch.py <served_dir> <out_dir> [tail] [names…]`
  — browser launches once and webfonts are fetched once (cached), so EP03's 17
  cards took ~3.5 min vs ~11 min relaunching per card. Renders every `*.html` in
  the dir that exposes `window.ppDuration`; reports any it skips.
- **EP01-engine cards** (om-seek protocol, `CUE_LIST`/`PART_WINDOW`): write a
  single-cue HTML per card (rewrite CUE_LIST/PART_WINDOW/TOTAL_RUNTIME; keep
  engine .jsx files as siblings) and render with
  `python scripts/render_overlay.py <html> <duration> <out.mp4>` at the EXACT
  cue duration — the engine bakes the exit animation at cue end.
- Referenced images must live INSIDE the served folder — the local HTTP server
  roots at the HTML's directory, so `../foo.png` 404s silently (alt-text box).
- Both render scripts already handle the hard-won gotchas: localhost serving
  (Babel can't fetch sibling .jsx over `file://`), sync seeks, scale-1 pinning,
  CRF 8 yuv444p piping (clean chroma edges), and `os._exit(0)` because
  `browser.close()` hangs forever on this machine. If a render ever looks
  stalled, ffprobe the output first — `nb_frames` complete means it finished.
- QC each new/changed card: extract the last frame and READ it (EP02 caught a
  broken cover image this way). Animations land ~2s after cue start — check
  2–4s in before declaring an element missing. **Confirm the Anton headline is
  the heavy CONDENSED font, not a thin fallback** — a webfont-load failure is
  exactly what shipped EP03's cover wrong; if it's fallen back, re-render.

## Stage 2 — Assembly (two passes)

**PASS A — base motion** (`scripts/gen_passA_graph.py` → filtergraph file):
- Presenter tpad-frozen to total runtime, fps=25 (presenter-native).
- Set `HEAD_TRIM` if Stage 0 found an over-long silent lead-in — the generator
  cuts that many seconds off the presenter head so speech lands on the title
  window (all shot-map/SRT times must already be on the trimmed timeline).
- `PUSH=[]` when every card is fullscreen (no left-third panels) — EP03 was
  all-fullscreen, so it had zero panel push.
- **Digital zoom + Panel Push as ONE zoompan program** — MCU 126% / WIDE 100%
  per the shot map, push 136% gliding the crop left (0.5s smoothstep) so Floyd
  sits right-third while left panels show; ~55px headroom bias when zoomed;
  merge adjacent panel cues (<2s gap) into one hold. Eased zoom moves ARE the
  approved transition (EP02) — no dissolves.
  NEVER build zoom/push from trim+overlay branches of the same input: each
  branch buffers the entire main stream until its window arrives → RAM
  explosion, encoder dies with 0 frames. Overlay layers are fine ONLY for
  separate-file inputs (b-roll, cards, logo).
- **B-roll**: separate inputs, 5s cuts, 0.3s alpha fades. **≥1s clear of a card
  cue is a PREFERENCE, NOT A GATE (Jodie, 27 Jul 2026)** — she watched it and
  ruled *"It is ok if one comes straight after the other."* Aim for the breathing
  room when the beat allows it; **never wire it to a hard fail, and never delay a
  build for it.** (b-roll and a card **OVERLAPPING** remains a hard fail — that is
  a different thing: adjacency is fine, sharing the screen is not.)
  *Why the distinction matters: a gate is only worth having if the thing behind it
  is worth stopping an episode for. A check that halts a build over something
  Jodie does not care about is worse than no check, because Hugh cannot clear it
  and cannot know it did not matter. See `docs/PP-STANDARDS.md` §What deserves a gate.* RELEVANCE law (clip must match the line), TURF law (green grass
  only — reject dirt), NO-REPEAT law — now **cross-episode AND within-episode**,
  enforced via `docs/broll-registry.md`: generate NEW clips every episode, never
  repeat a clip within an episode, check every new prompt's subject against the
  registry before generating, and append this episode's clips to the registry
  afterward (audit used/unused, report). **From EP04 we also use MORE b-roll per
  episode.** Upscale 720p.
- **Logo**: 428px wide @ 90% opacity bottom-right, full duration (locked spec,
  Jodie EP02). Under the card layer.
- Encode CRF 14 veryfast as `_passA.mp4` and KEEP it — card/music revisions
  become pass-B-only (~4 min).

**PASS B — cards + audio** (`scripts/assemble_passB_ep02v3_example.sh` is the
approved reference):
- EP01-engine card clips: chromakey `0x00FF00:0.28:0.06`, overlay at 0,0 at
  cue start (exit animation is baked in — no fades needed).
- Design panel cards: chromakey, scale to 810px, overlay x=36 (must never
  cross centre or touch the pushed presenter — overlap = QC fail), freeze-
  extend (tpad clone) to the cue window, 0.3s alpha fades.
- Fullscreen cards (title/stat/roughies/end/warranty): full-frame; solid-bg
  ones composite without keying. **Never let two full-frame cards cross-fade**
  — if the outgoing card fades while the incoming fades in, both go semi-
  transparent and the presenter flashes through (~0.5s, caught in EP02 v2).
  Hold the outgoing card solid past the incoming fade-in.
- **Audio (the approved v3 recipe — ratio is everything):**
  1. Speech `loudnorm=I=-16:TP=-1.5:LRA=11` (YouTube target; HeyGen output is
     ~9 dB too quiet). loudnorm resamples to 192k — follow with
     `aformat=...:sample_rates=48000` or the mix breaks.
  2. Music bed **0.04** under speech; sting full 0–4.5s → ~1s fade to 0.5 →
     bed by first words; rise ~0.5 at the end card; ~0.42 under the warranty;
     out by the fade-to-black.
  3. **Sidechain duck** music against the speech key (`asplit` the normalised
     speech): `sidechaincompress=threshold=0.015:ratio=14:attack=12:release=420:level_sc=2`.
     Music dips as he speaks, breathes back in pauses.
  4. `amix=inputs=2:duration=first:normalize=0` (essential — default rescales
     and buries speech), then `alimiter=limit=0.95`.
- **Validate volume expressions before encoding** (paren-balance + print
  levels at key times in python) — a mis-parened nested `if()` chain only
  fails after the whole graph builds; cost two encode rounds on EP02.
- Final encode: libx264 CRF 18 medium, yuv420p, AAC 192k 48 kHz, `+faststart`.
  Add `-map_metadata -1 -dn` to drop the stray `bin_data` track the HeyGen
  source carries through (harmless on YouTube, but cleaner without it).

## Stage 3 — QC (before calling anything done)

1. ffprobe: duration, 1920×1080@25, audio present.
2. Frames (READ them): title card; one MCU vs one WIDE; each panel moment
   (presenter fully clear of the card); each b-roll slot (relevant, turf,
   full-frame); logo legibility; end card (real cover, no RG elements);
   warranty slide (locked layout). Scrub the end-card→warranty handover at
   ~0.15s steps — a single frame either side misses the flash.
3. Audio RMS (`astats`) at: sting full, sting half, 3+ speech windows, end
   card, warranty. Speech should sit ≈ −18 dB RMS after loudnorm; whole-file
   integrated loudness ≈ −14 to −16 LUFS (`ebur128`).
4. Write `output/ASSEMBLY-REPORT[-vN].md`: decisions, placements, settings,
   b-roll used/unused audit, flags for Jodie. Copy the SRT beside the output.

## Stage 4 — E-book PDF (same pipeline, different artefact)

Cowork Claude creates the cover, illustrations and article body; THIS side
builds the PDF. See `PP Videos/docs/WHO-DOES-WHAT.md` for the full contract.

- **Standing furniture is in `assets/` and is APPROVED — never redesign:**
  `ebook-template.html` (whole shell: A4, Georgia, orange #DA532C, running
  footer, page numbers, header logo, cover slot, warranty page, marketing
  page), `ebook-logo-white.png` (header logo, transparent, for white pages),
  `ebook-logo.png` (dark chip, for photo/dark backgrounds),
  `marketing-hero.png`. Only the ARTICLE BODY changes per book.
- **Build + QC in one command:**
  `python scripts/build_ebook.py <source.html> <out.pdf>` — renders with
  WeasyPrint (base_url = the HTML's folder so images resolve) then checks page
  count, that all three links are live (site / gambling help / mailto), and
  that every content page carries the header logo. Non-zero exit on failure. If
  the out PDF is open in a viewer (Windows locks it) it writes a `-new` sibling
  and says so — close the viewer and rename, don't force.
- **Cover — build `ebook/cover-src/cover.html` by COPYING the canonical
  `assets/ebook-cover-template.html`** (flow-band layout — subtitle/byline/footer
  stack in normal flow and can never overlap; the EP09 collision lesson). Change only
  the title, subtitle and byline texts + the hero. **ALWAYS re-render with
  `render_still.py`; never trust a handed-over `cover.png`.** `cover_check.py`
  measures the rendered page and FAILS on overlapping/clipped text — the engine
  runs it automatically after every cover render. EP03's shipped
  cover had a font-fallback bug (Anton didn't load → thin generic sans, no
  eyebrow rule). Re-render on our online machine, compare the headline against
  `PP-EP02-Killer-Strategies-for-the-Trifecta/ebook/cover-fixed.png` (the
  approved reference cover), then propagate to BOTH `ebook/cover.png` and
  the end-card's `overlay/export/ebook-cover.png` (the template cover slot loads
  `cover-fixed.png`).
- **Hybrid illustrations + keep-together (in the standing template):**
  landscape code-diagrams use `class="illus"` (≤92% wide, 78mm tall); portrait
  pictures with a baked-in title/label (e.g. Canva 1200×1698) use
  `class="illus portrait"` → 57% of column width, centred, so they don't
  dominate. Any DATA TABLE + its heading/caption are kept together the same way (wrap the pair in a `.avoid` container; `h1.section`/`h2.rule` carry `page-break-after: avoid`) — no orphaned table headings (EP09 lesson). A heading + its paragraph + its figure never split across a page —
  `h2.rule{page-break-after:avoid}` + `p:has(+ .illus){page-break-inside:avoid}`
  + `.illus{page-break-before:avoid}` make the trio atomic (moves whole to the
  next page). To force a section onto a FRESH page, put `<div class="pagebreak">`
  before its `<h2 class="rule">`. (`:has()` needs WeasyPrint ≥61; we run 69.)
  The cover's header-logo bleed is handled by `@page :first{@top-right{content:""}}`.
- **Cover footer surgery:** `scripts/fix_cover_footer.py` removes words from a
  cover's BAKED-IN footer by splicing the original pixels (font matches
  exactly — never re-render the text). Run it once with no args to list the
  numbered word-segments, then `--keep 0-4,10`. Guessing the spec produces
  plausible-looking nonsense; ALWAYS open the before/after PNG it writes.
- **The justify trap:** the template's global `p { text-align: justify }`
  silently left-aligns centred single-line `<p>`s. Any centred paragraph needs
  its own `text-align:center`. This bit us twice on EP02 (the site link, then
  the warranty support line) — check every centred block in the rendered PDF,
  not the HTML.
- **Header logo pattern:** `@page { @top-right { content:
  url('ebook-logo-white.png'); image-resolution: 220dpi } }`. Suppress on the
  marketing page (it has its own big chip) via a named page:
  `@page marketing { @top-right { content: "" } }` + wrap that block in a div
  with `page: marketing`. Suppress it on the cover the SAME way —
  `@page :first { @top-right { content: "" } }`; `margin:0` alone does NOT
  suppress it (that was EP03's cover header-logo bleed).
- WeasyPrint needs the Windows GTK runtime (installed 2026-07-20 at
  `C:\Program Files\GTK3-Runtime Win64`); `build_ebook.py` adds it to the DLL
  path automatically.

## Stage 5 — YouTube thumbnail (1280×720)

**🔒 CANONICAL SPEC: `docs/PP-THUMBNAIL-TEMPLATE.md` (2026-07-25) + the standing
template `assets/youtube-thumbnail-template.html` — together the single source
of truth. BUILD BY COPYING THE TEMPLATE FILE; never author a fresh thumbnail
HTML from a description (EP08 drifted exactly that way; the engine now flags
off-template pages missing the logo chip). ALL FIVE elements required, every
episode: eyebrow · Anton white/orange colour-split headline · orange rule ·
byline (sentence case — never omit) · PP logo chip bottom-left.**

- Drop the hero as `PP-EPxx/thumbnail/hero.png`; copy `pp-logo-on-dark.png` in
  beside it. Copy the template to `ep-xx-thumbnail.html` and edit ONLY the four
  per-episode slots: `.l1`/`.l2` (the hook — setup words WHITE, payoff words
  ORANGE), `.strap` (the byline), the hero, and text placement for that hero.
  `.eyebrow` is LOCKED to **"How to Win at Horse Racing"** (canonical — NOT
  "Practical Punting", which was earlier drift). Build from the folder:
  `python scripts/render_still.py ep-xx-thumbnail.html ../output/PP-EPxx-thumbnail.png 1280 720`.
- Placement is the craft — VIEW the hero first, then decide. All text over the
  clearest, darkest, subject-free region (horses charging from the right → text
  upper-LEFT, EP02/EP03; a head-on field under a stormy sky → text in the dark
  sky/rail, EP01). Keep every line CLEAR of the horses; shrink `.l2` if its
  widest line collides.
- Scrim = full-bleed ANGLED linear gradient ONLY — never a part-height/width
  band (hard edges) or a radial (visible oval), the banner lesson. Dial opacity
  to the hero: bright sky/turf → strong; an already-dark stormy sky → lighter.
- Headline BIG and bold so it reads on a phone; real brand fonts (Anton
  headline; `render_still.py` waits for webfonts — confirm Anton didn't fall
  back). Spare heroes live in `PP Videos/assets/thumbnail-heroes/` (descriptive
  names) — check there before generating a new one.
- QC: READ the output at 1280×720 — kicker + orange accent bar present, headline
  legible over the scrim and clear of the subject, logo readable in its corner.
- **Save the YouTube copy (standing rule, every episode):** write the finished
  title + description to `output/PP-EPxx-youtube.txt`. WE write the copy
  (`docs/youtube-metadata-kit.md`) — Jodie's ruling 26 Jul 2026, moved from
  Cowork; Jodie uploads. It ships beside the episode outputs so every episode
  has its metadata on disk.

## Flutter / artefact masking (Avatar IV)

Rank 10s windows by frame-difference energy in the jacket/desk band
(`crop=1920:400:0:600,tblend=all_mode=difference,signalstats` → YAVG per
frame, aggregate), plus a contact-sheet visual scan. Bias b-roll/panels onto
the worst stretches; MCU crops trim edge artefacts; report what stays visible
with timestamps. (EP02 verdict: MCU framing hides most of it — low priority.)

## Known constraints

- **THE QC-PER-FIX RULE (PP-STANDARDS, 25 Jul 2026):** every recurring-risk fix lands in
  the standard AND the engine AND an automatic QC check — never just a note. A checked
  rule enforces itself; when you fix a repeat-capable problem, also add its check.

- Design cards (incl. "fullscreen" slides) have rounded margins — they don't
  cover 100% of the frame; the presenter shows at the corners by design. Flag,
  don't silently "fix".
- Never alter cue timings in card HTML — they're locked to the presenter audio.
- Reconcile three numbers before rendering: speech end, last cue end, total
  runtime (EP02: 390.83 speech → 401.9 warranty end → 402.3 total).
- Standing permissions are configured in `.claude/settings.json` (ffmpeg/
  python/file-ops/HeyGen/curl pre-approved; deletions and outside-project
  still prompt). Deletions are ALWAYS Jodie's call — flag files for purging
  (e.g. banned dirt clips), never delete them yourself.

## Legacy (EP01 method — superseded, kept for reference)

Full-length overlay renders (one 550s green video from Part 1/Part 2 HTML,
concat, single-pass assembly): see `scripts/assemble_ep01_example.sh` and
render_overlay.py's multi-cue mode. Only relevant if an episode ever truly
needs a continuous overlay; otherwise use per-card compositing.
