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
- **Human gates sacred** — parks at `awaiting_render` / `awaiting_cover` /
  `awaiting_approval`; only the board (a human) advances those.
- **Credit guard** — estimates the spend before firing gens; refuses to start
  (flags instead) if the balance can't cover it or it exceeds
  `ENGINE_CREDIT_CEILING`. Real Higgsfield balance probing is an open item —
  see below.
- **Locked build order** — b-roll gens are fired FIRST; local renders happen
  while they cook; the HeyGen render runs in parallel behind its human gate.

## Status → steps map

| status | engine steps |
|---|---|
| building | audit_inputs → credit_check → broll_submit → ebook_cover → cards_render → broll_collect → park `awaiting_render` (sets `heygen_name`) |
| rendering | heygen_download (poll by project name) → shot_map → covers_ab (sets `cover_a_url`/`b_url`) → park `awaiting_cover` |
| assembling | passA → passB → self_qc → ebook_pdf → thumbnail → youtube_copy → park `awaiting_approval` (writes links, `build_seconds`, releases claim) |
| revising | Phase 3 — flags honestly instead of guessing |

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

Still human / staged, on purpose:
- **The HeyGen render itself** — a sacred human step, unchanged; the engine
  only downloads the finished master.
- **Cover A/B heroes and the YouTube copy** — staged by the create side
  (Cowork) until the create brain (Phase 4). Registry `--append` after a
  generated episode also stays a create-side step for now.

Phase 2b (three in flight + the local render lock) builds on this spine.
