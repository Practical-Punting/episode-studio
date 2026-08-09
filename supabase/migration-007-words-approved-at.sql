-- 007 — words_approved_at: the moment a HUMAN approved the words.
-- Applied 10 Aug 2026 via Supabase MCP (name: 007_words_approved_at).
--
-- WHY A NEW COLUMN AND NOT script_approved_at, WHICH ALREADY EXISTS. They sound
-- like the same thing and they measure opposite ends of the wait:
--
--   script_approved_at  is written BY THE ENGINE, in step_script_sync, when the
--                       build re-reads the approved text. EP19's is 03:41:59 —
--                       TWO SECONDS after started_at. It records when the BUILD
--                       began, not when Jodie clicked.
--   words_approved_at   is written BY THE BOARD, in the approve-words handler,
--                       at the click itself.
--
-- The number Jodie wants is "approval -> render startable", and with only the
-- first of those it cannot be computed at all: the click happens at an unknown
-- time BEFORE the build starts, so the interval collapses to roughly zero and
-- looks excellent. A measurement that always reports success is not a
-- measurement. (Before-EP20 batch item 11.)
--
-- NULLABLE, AND NO BACKFILL. Every episode up to EP19 was approved before this
-- existed and there is no record of when — inventing one from started_at would
-- manufacture exactly the flattering number described above. NULL means "not
-- measured", which is the truth, and the first real reading is EP20's.
--
-- NO TRIGGER AND NO CONSTRAINT. It is a timestamp the board sets once; there is
-- no bad value to guard against, and 005's lesson is that a constraint on a
-- column nobody is writing can still brick an unrelated update to a legacy row.

alter table public.episodes
  add column if not exists words_approved_at timestamptz;

comment on column public.episodes.words_approved_at is
  'When a HUMAN approved the words on the board (the approve-words click). '
  'Distinct from script_approved_at, which the ENGINE writes at script_sync when '
  'the build re-reads the text — that one is ~2s after started_at and measures '
  'the build, not the wait. words_approved_at -> render_started_at is the real '
  '"approval to render startable" interval. NULL on every episode up to EP19: '
  'they were approved before this column existed and a backfill would invent a '
  'flattering number. Batch item 11, 10 Aug 2026.';
