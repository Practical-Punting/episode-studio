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

## Open items for 2a-real (deliberately not faked)

`RealProvider` wires what today's scripts allow and FLAGS the rest honestly:

- **B-roll generation** runs through the Higgsfield MCP inside a Claude
  session — no standalone API key in `.env` — so the engine can't fire gens
  autonomously yet. Real mode checks for staged clips and flags if missing.
- **Higgsfield balance** likewise isn't probeable outside a session; the credit
  guard leans on the ceiling until it is.
- The local render/assembly steps (cards, shot map, passes, e-book, thumbnail)
  shell out to the standing toolkit — wiring + a real-episode shakedown is the
  2a-real follow-up, gated on staged create-inputs for a test episode.

Phase 2b (three in flight + the local render lock) builds on this spine.
