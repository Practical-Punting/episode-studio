-- 009 — two-way episodes get a normal rail row.
-- Approved by Jodie 13 Nov 2026 ("GO on the plan … including migration 009 in section A,
-- exactly as shown") — docs\PLAN-twoway-board-and-runner.md on the Drive, section A.
-- Applied via Supabase MCP (name: 009_two_way).
--
-- WHY. Two-way episodes (two readers: Gordon reads Brian Blackwell, Steve reads Barry
-- Meadow) had NO rail row: their numbers were held by hand in app.js (RESERVED_EPS), the
-- board could not show them, and every session had to be told where they stood.
--
--   format             'single' (every existing row, by the default) or 'two-way'.
--                      🔴 The single-presenter engine must never claim a two-way row:
--                      rail.list_queued() and claim_next() filter on format=single in the
--                      same change (engine/rail.py).
--   heygen_video_id_2  build spec A6: Steve's render id. heygen_video_id stays Gordon's.
--                      A render id (what HeyGen returned), never a template id — those
--                      live only in docs/HEYGEN-HUMAN-STEP.md.
--   twoway             written by the runner (engine/twoway_run.py) only:
--                      {"stage": 1-5, "step": "...", "gate": "words"|null, "gate_since": ts,
--                       "readers": {"BB": "Gordon", "BM": "Steve"}}
--
-- Status for a two-way uses the existing ten words (queued → building →
-- awaiting_approval → published). No change to the status check.

alter table public.episodes
  add column if not exists format text not null default 'single'
    check (format in ('single', 'two-way')),
  add column if not exists heygen_video_id_2 text,  -- A6: Steve's render id. heygen_video_id stays Gordon's.
  add column if not exists twoway jsonb;            -- written by the runner only
