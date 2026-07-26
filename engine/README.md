# Engine — the orchestrator spine (Phase 2a)

The conductor for Episode Studio: claims ONE queued episode from the rail and
drives it through the status contract, crash-safe, never silently frozen.
Built to `PP-engine-design-and-build.md` + the refined plan.

## Run it

```
python engine/engine.py run --mock --watch    # mock everything (no credits), keep going across gates
python engine/engine.py run --mock            # one leg: work until the next human gate, then exit
python engine/engine.py mock-episode          # create the PP-EP99 test ticket
python engine/engine.py status                # quick board glance
python engine/engine.py cleanup-mock          # remove mock tickets + .mock/ artifacts
```

Config comes from `PP Videos/.env` via `scripts/rail.py` (the ONE Supabase
client — service_role key, never client-side). Overrides:
`PP_VIDEOS_DIR`, `ENGINE_WORKER`, `ENGINE_CREDIT_CEILING`, `ENGINE_RETRY_DELAYS`,
`ENGINE_BROLL_MODEL`, `ENGINE_COVER_MODEL` / `_ASPECT` / `_RES` / `_CEILING`,
and the mock switches in `providers.py` (`MOCK_FAIL_STEP`, `MOCK_FAIL_ONCE`,
`MOCK_BALANCE`, `MOCK_STEP_SECS`, `MOCK_BROLL_CLIPS`).

## How it holds the principles

- **Single-writer lease** — claim sets `claimed_by` + `lease_until`; heartbeats
  renew it; a crashed worker's lease expires and the episode is reclaimable
  (`rail.reclaim_stale`). A heartbeat that comes back empty means ownership was
  lost, and the engine stops touching that episode.
- **Resumable** — every step checkpoints into `build_state` (`steps` done +
  `jobs` with per-clip Higgsfield job IDs and per-poll progress). A submitted
  job is checkpointed the instant it exists and is NEVER re-submitted; a
  memoryless restart skips done work exactly.
- **Never-freeze** — heartbeat thread beats every 20s through every retry and
  wait; transient failures retry with backoff (mock 2/4/6s, real 5/25/120s);
  exhaustion or an `EngineFlag` writes a plain-English `needs_look` message and
  waits ALIVE for the flag to clear (the board's stale-heartbeat check catches
  the case where the engine truly dies).
- **Human gates sacred** — the words, the render, the cover pick, the four
  approvals. The engine offers and waits; only a human answers.
- **Credit guard** — estimates the spend before firing gens (b-roll *and* the
  two cover heroes); refuses to start (flags instead) if the balance can't
  cover it or it exceeds `ENGINE_CREDIT_CEILING` / `ENGINE_COVER_CEILING`.

## THE SCRIPT GATE (Jodie, 26 Jul 2026) — no override

The script lives as a **Google Doc in the episode's Drive folder**. That Doc is
the single source of truth; `docs/spoken-words.txt` is a derived cache the engine
overwrites from it in the first build step (`script_sync`). The gate passes only
when a human has done BOTH — approved the words AND ticked "I've read the script"
(`title_approved` + `script_read`, enforced in `rail.claim_next`'s filter).

`assert_script_gate(ep)` is the guard, called at `script_sync`, `audit_inputs`
and `render_gate`. **Any future auto-render path must call it before submitting
anything to HeyGen.** There is no flag, no env var and no fast path past it —
approving the script is a decision, and decisions stay human.

If the Doc can't be read, the episode flags `needs_look` in plain English and the
build stops; it never falls back to the stale local draft. If the Doc changes
after approval, `script_changed_since_approval` is set (the card shows it) and the
build carries on using the approved snapshot.

### Known future upgrade — reading script Docs

The engine is a standalone Python process with no Google login. It cannot use the
Drive connector that Claude sessions use — that connector belongs to the session,
not to the machine. So today the engine reads a script Doc through the Doc's
plain-text export URL (`/export?format=txt`), which requires that Doc to be set to
**"anyone with the link can view"**.

The proper long-term fix is a **Google service account with read-only Drive
scope**: the engine authenticates as itself, reads the Doc directly, and no
sharing is needed at all. It can be swapped in later without undoing any of the
Script Gate work — only `RealProvider.fetch_script()` changes.

**This is a deliberate, accepted trade-off, not an oversight.** Decided by Jodie,
26 Jul 2026: every word of these scripts is published publicly on YouTube by
design, so a link-shared Doc exposes nothing that isn't about to be broadcast
anyway; the URLs are unguessable; and the `script_snapshot` + `script_sha256`
audit trail plus the drift flag cover what physical doc-locking would have
prevented. The sharing rule that goes with it — individual episode script Docs
ONLY, never a folder, never anything holding subscriber data or method material —
is a hard rule in `PP-STANDARDS.md`.

## THE LOCKED ORDER (approved by Jodie, 26 Jul 2026)

Do not re-sequence without her explicit re-approval.

1. Article → script + words. 2. **Words Gate** (title / hook / byline).
3. On approval, **in parallel**: (a) the render gate opens — Gordon starts
   cooking, the LONG POLE (5-45 min), which depends only on the spoken track
   and so must never wait on pictures; (b) the gens batch fires — b-roll **and**
   both cover heroes. 4. **Cover pick**, surfaced the moment both heroes exist,
   *during* the render. 5. Engine finishes cover page + cards, hands-off.
6. Master → shot map → assembly → QC. 7. The four approvals. 8. Publish →
   Stage-8 close-out.

The shape: human turns 1-2-3 back-to-back at the FRONT, one long hands-off
window, turn 4 at the END. Never render-last, never human-machine ping-pong.

**The guard.** `check_locked_order()` runs at engine start and warns (naming the
locked order) if the step lists have been re-sequenced. At run time the engine
stamps `build_state.order` — `render_offered_at`, `gens_started_at`,
`covers_ready_at`, `cover_picked_at`, `master_at` — and warns if the gens batch
started before the render gate opened, if the cover heroes appeared after the
master landed, or if the whole batch finished with the render still unstarted.
Warnings are logged AND kept in `build_state.order.warnings`.

## Status → steps map

| status | engine steps |
|---|---|
| building | **script_sync** (re-reads the Doc, snapshots it) → audit_inputs → **render_gate** (sets `heygen_name`, opens human turn 2) → credit_check → broll_submit → **covers_ab** (sets `cover_a_url`/`b_url`, opens human turn 3) → broll_collect → **cover_pick** (waits in place; status stays `building`) → ebook_cover (built from the pick) → cards_render → `rendering` if `render_started_at`, else park `awaiting_render` |
| rendering | heygen_download (poll by project name) → shot_map → `assembling` (the cover was picked back in the build) |
| assembling | passA → passB → self_qc → ebook_pdf → thumbnail → youtube_copy → park `awaiting_approval` (writes links, `build_seconds`, releases claim) |
| revising | Phase 3 — flags honestly instead of guessing |

`awaiting_render` and `awaiting_cover` are now **fallback parks**: reaching
either means a human turn wasn't taken during the build, and the engine says so.

## Real mode (2a-real, shaken down 2026-07-24)

`RealProvider` drives the standing toolkit for every scriptable step: cover
re-render (render_still), card batch (render_cards_batch), HeyGen master
pickup by project name via the API `video_url` (+ the ≥180 kbps audio gate),
shot map (build_shot_map), pass A/B (emit the graph with assemble_episode.py,
then run the documented ffmpeg command with the exact input layout), QC
(qc_episode), e-book (build_ebook/WeasyPrint), thumbnail (render_still).
Find-or-build everywhere: a staged artifact is used, never rebuilt or
re-spent. Proven end-to-end on a staged EP07-asset test episode (PP-EP98):
QC PASS, 0 credits, 0 retries.

### Higgsfield: hands-off gens via the CLI (B+, wired 2026-07-24)

The engine fires b-roll gens itself through the **Higgsfield CLI** on the
existing plan's credits: balance via `hf account status`, an EXACT per-clip
cost preview in the credit guard (no spend), the registry no-repeat check
before any spend, then per-clip `generate create` → poll → download with
job-id checkpoints (a submitted job is never re-submitted). Model:
`ENGINE_BROLL_MODEL` (default `kling3_0_turbo`, 5s 720p 16:9 — the b-roll
standard; ~7.5 credits/clip). If the CLI is absent or unauthenticated, every
gen path falls back to the honest b-roll gate (a flag naming the clips).

One-time install per machine (`npm i @higgsfield/cli` breaks under Git-Bash
tar on Windows, so install the release binary directly):
1. Download `hf_<ver>_windows_amd64.tar.gz` from github.com/higgsfield-ai/cli
   releases; extract `hf.exe` to `C:\Users\jlral\tools\hf\` (or set `HF_CLI`).
2. `hf auth login` (one browser approval; token → `~/.config/higgsfield/`).
3. `hf workspace set <id>` (see `hf workspace list`).

### Cover heroes: generated UPFRONT (R7, 26 Jul 2026)

Both cover heroes are part of that same gens-first batch — `nano_banana_pro`,
portrait 2:3, 2k, ~2 credits each (~4 total), previewed and capped by
`ENGINE_COVER_CEILING` before anything is spent. Prompts come from
`episode.json → cover.hero_a_prompt / hero_b_prompt` (Cowork writes them, two
DIFFERENT compositions); job ids are checkpointed into `docs/hero-jobs.json`
the instant they exist, so a restart never re-spends. Files:
`ebook/cover-src/hero-a.png` + `hero-b.png` are the two OPTIONS; `hero.png` is
whichever is ACTIVE (what `cover.html` draws) — `ebook_cover` copies the picked
one over it. Older episodes that only have `hero.png` + `hero-b.png` are adopted
as-is (`hero.png` IS option A).

Because they're made before the long b-roll collect, the pick reaches the
operator minutes into the build — never mid-run as "no e-book cover, needs a
look", and never after the master lands.

Still human / staged, on purpose:
- **The HeyGen render itself** — a sacred human step, unchanged; the engine
  names the project, opens the gate early, and downloads the finished master.
- **The cover PICK and the YouTube copy** — the pick is Jodie's/Hugh's; the
  copy is staged by the create side (Cowork) until the create brain (Phase 4).
  Registry `--append` after a generated episode also stays a create-side step.

Phase 2b (three in flight + the local render lock) builds on this spine.
