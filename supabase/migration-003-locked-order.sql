-- Episode Studio — migration 003: the locked build order (approved 26 Jul 2026)
-- Project: ydqzdzpyemrqttiyhpwp. Apply via Supabase MCP (Cowork) or the SQL editor (Jodie).
-- Claude Code does NOT run DDL. IDEMPOTENT (safe to re-run).
--
-- ✅ APPLIED 26 Jul 2026 by Cowork via Supabase MCP, at Jodie's instruction.
--    Verified present in information_schema; read/write confirmed through rail.py.
--    Do NOT run it again — it is idempotent, but there is nothing left to do.
--
-- ONE new column. Under the locked order the HeyGen render (the long pole, 5-45 min)
-- is started by the operator WHILE the engine is still building the pictures — so
-- "the render has been started" can no longer be carried by `status` alone
-- (status is 'building' at that moment). render_started_at is that fact, written by
-- the human on the board and read by the engine, which then walks itself from
-- building -> rendering without a second human turn.
--
-- Until this lands the board degrades honestly: the render button still works at the
-- awaiting_render park, and says so if it can't record the stamp.

begin;

alter table public.episodes
  add column if not exists render_started_at timestamptz;   -- human hit render (turn 2)

comment on column public.episodes.render_started_at is
  'When the operator started Gordon''s HeyGen render. Set by the board (human turn 2), '
  'read by the engine to move building -> rendering. Locked order, 26 Jul 2026.';

commit;

-- Sanity (run after commit):
-- select column_name from information_schema.columns
--  where table_name='episodes' and column_name='render_started_at';
