-- Episode Studio — migration 004: the SCRIPT GATE (designed by Jodie, 26 Jul 2026)
-- Project: ydqzdzpyemrqttiyhpwp. Apply via Supabase MCP (Cowork) or the SQL editor (Jodie).
-- Claude Code does NOT run DDL. IDEMPOTENT (safe to re-run).
--
-- WHY: approving the script is a DECISION, and decisions stay human forever — even
-- after HeyGen auto-render lands. Starting a render is a CHORE and may be automated.
-- Automation eats chores, never decisions.
--
-- The gate passes only when BOTH are true: title_approved AND script_read.
-- The Google Doc is the single source of truth for the script from the moment it is
-- created; docs/spoken-words.txt becomes a derived cache the engine overwrites from
-- the Doc at the start of every build.

begin;

alter table public.episodes
  -- the words, promoted out of the free-text `notes` so the board can EDIT them
  add column if not exists hook                text,   -- the big thumbnail text
  add column if not exists byline              text,   -- the one-line promise
  -- the script's ONE home
  add column if not exists script_doc_url      text,   -- Google Doc in the episode's Drive folder
  add column if not exists script_read         boolean not null default false,
  -- what was actually approved and rendered (requirement 8)
  add column if not exists script_snapshot     text,        -- exact approved text
  add column if not exists script_sha256       text,        -- hash of that text
  add column if not exists script_approved_at  timestamptz,
  add column if not exists script_locked_at    timestamptz,
  -- the Doc moved after approval — FLAG on the card, never block (requirement 9)
  add column if not exists script_changed_since_approval boolean not null default false;

comment on column public.episodes.script_doc_url is
  'Google Doc holding the episode script — the SINGLE SOURCE OF TRUTH. The engine '
  're-reads this at the start of every build and overwrites docs/spoken-words.txt '
  'from it, so an operator edit is never ignored. Script Gate, 26 Jul 2026.';
comment on column public.episodes.script_read is
  'Operator ticked "I''ve read the script". With title_approved, this is the Script '
  'Gate. Nothing builds until both are true. Never auto-set.';
comment on column public.episodes.script_snapshot is
  'The exact script text that passed the gate and was rendered. Written by the '
  'engine at script_sync; the audit trail for what Gordon actually said.';

commit;

-- Sanity (run after commit):
-- select column_name from information_schema.columns
--  where table_name='episodes'
--    and column_name in ('hook','byline','script_doc_url','script_read',
--                        'script_snapshot','script_sha256','script_approved_at',
--                        'script_locked_at','script_changed_since_approval')
--  order by column_name;
