-- 006 — SCRIPT VERSIONS: no edit is ever unrecoverable.
--
-- WHY A NEW TABLE, when "no schema changes" was the standing preference.
-- Broken deliberately, and the build plan says so out loud: "A version history is
-- a genuinely new thing, not churn." The alternative — versions inside
-- `build_state` — would have dragged EVERY VERSION ACROSS THE WIRE ON EVERY
-- ENGINE HEARTBEAT, on a connection that already drops (59 rail transients in one
-- evening, one nine-attempt give-up). The standing rule exists to stop churn; a
-- second copy of a 15 KB script on every beat IS churn.
--
-- ═══ VERSION HISTORY IS NOT OPTIONAL — IT IS THE PRICE OF AUTOSAVE ═══════════
-- Autosave removes the deliberate act of saving, and with it the mental model of
-- "I can always not save". The browser undo stack was the fallback, and the
-- 30-second rebuild had ALREADY DESTROYED IT (board bug 1). Ship autosave without
-- versions and her only recovery from a bad edit is retyping from memory.
--   (PP-script-editor-REVIEW-4Aug §5.)
--
-- 🔒 INSERT-ONLY, and here is exactly how far that goes.
-- The RLS policies below grant `authenticated` SELECT and INSERT and NOTHING
-- ELSE. RLS denies by default, so for THE BOARD — which is the only thing a
-- human drives — there is no UPDATE path and no DELETE path at all. A history
-- the editor can rewrite is not a history.
--
-- ⚠️ AND THE HONEST LIMIT: `service_role` BYPASSES RLS. The engine holds that
-- key, so the database does not stop the ENGINE deleting a version row — the
-- standing rail discipline does (select/insert/update, never delete; deletions
-- are Jodie's, ruling A13). Saying "enforced by the database" without this
-- sentence would be the kind of overclaim that gets believed later by someone
-- deciding they need not check.
--
-- ⚠️ BOUNDARIES, NOT KEYSTROKES. A row is written at panel open, panel close, on
-- approve, and about every five minutes of active editing — NOT on every autosave
-- (which is a 3-second debounce). The proof pass tests this directly: "count
-- version rows after 20 minutes — single figures, not hundreds."

create table if not exists public.script_versions (
  id            uuid primary key default gen_random_uuid(),
  episode_id    uuid not null references public.episodes(id) on delete cascade,
  created_at    timestamptz not null default now(),

  -- The words as they stood at this boundary. Never a diff: a diff needs its
  -- base to be reconstructable, and a chain of diffs is exactly the thing that
  -- cannot survive one bad row.
  script        text not null,

  -- WHO, and it is a closed vocabulary on purpose.
  --   'claude'  the first draft, written by the drafting pass
  --   'human'   Jodie editing on the board
  --   'approve' the freeze taken at the moment she approves
  author        text not null check (author in ('claude', 'human', 'approve')),

  -- Why this row exists — 'open' | 'close' | 'tick' | 'approve' | 'seed'.
  -- Free text on purpose: it is a note for a person reading the history, not a
  -- value anything branches on. A closed vocabulary here would be a list somebody
  -- has to maintain for no gain.
  reason        text,

  -- Cheap identity for "is this the same words as that". Lets the board skip
  -- writing a boundary row when nothing actually changed.
  sha256        text
);

-- The only query this table serves: "this episode's history, newest first",
-- and "the FIRST thing Claude wrote" for the revert button.
create index if not exists script_versions_episode_created_idx
  on public.script_versions (episode_id, created_at desc);

alter table public.script_versions enable row level security;

-- 🔒 SELECT and INSERT ONLY. No update policy and no delete policy exist, so
-- neither operation has a path — RLS denies by default. That is the insert-only
-- rule enforced by the database rather than by everyone remembering it.
drop policy if exists script_versions_read on public.script_versions;
create policy script_versions_read
  on public.script_versions for select
  to authenticated
  using (true);

drop policy if exists script_versions_insert on public.script_versions;
create policy script_versions_insert
  on public.script_versions for insert
  to authenticated
  with check (true);

-- ── THE OTHER HALF: who owns the words ──────────────────────────────────────
-- "Once a human has edited, the human's version is the truth." The engine may
-- READ freely — reading is always safe — and must never WRITE over her. If it
-- thinks the script needs changing it raises a flag and asks, the same way it
-- does for everything else it cannot decide alone.
alter table public.episodes
  add column if not exists script_edited_by_human_at timestamptz;

comment on column public.episodes.script_edited_by_human_at is
  'Set on Jodie''s first save in the board editor. While it is set, the engine '
  'must NOT overwrite script_snapshot — it raises a flag instead. Claude Code '
  'may always read.';
