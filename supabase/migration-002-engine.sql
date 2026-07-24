-- Episode Studio — migration 002: engine + operator-v3 schema
-- Project: ydqzdzpyemrqttiyhpwp. Apply via Supabase MCP (Cowork) or the SQL editor (Jodie).
-- Claude Code does NOT run DDL. IDEMPOTENT (safe to re-run).
--
-- Adds to public.episodes: 4 approval booleans, cover A/B, needs-a-look flag+message,
-- progress, timing, cost, lease (single-writer), heartbeat, retries, build_state, publish links.
-- Creates public.messages (the Hugh<->engine thread) with RLS + realtime.
-- Status stays the 10-status contract; friendly lane labels live in the UI, not the DB.

begin;

-- ── episodes: new columns ────────────────────────────────────────────────
alter table public.episodes
  -- separate approvals (Title on its own), per the v3 mockup
  add column if not exists video_approved      boolean     not null default false,
  add column if not exists ebook_approved      boolean     not null default false,
  add column if not exists thumbnail_approved  boolean     not null default false,
  add column if not exists title_approved       boolean     not null default false,
  -- cover A/B gate (cover_choice already exists: 'A' | 'B')
  add column if not exists cover_a_url         text,
  add column if not exists cover_b_url         text,
  -- "Needs a look" — an ORTHOGONAL flag (episode keeps its status; board shows the red card)
  add column if not exists needs_look         boolean     not null default false,
  add column if not exists needs_look_message text,
  -- progress (human line + %) for the working-card display
  add column if not exists progress_step      text,
  add column if not exists progress_pct       integer     not null default 0,
  -- timing
  add column if not exists started_at         timestamptz,
  add column if not exists finished_at        timestamptz,
  add column if not exists build_seconds      integer,
  -- cost (flexible: {"higgsfield_credits":..,"heygen_credits":..,"aud":..})
  add column if not exists cost               jsonb       not null default '{}'::jsonb,
  -- lease-based single-writer claim (crash recovery: reclaim when lease_until < now())
  add column if not exists claimed_by         text,
  add column if not exists lease_until        timestamptz,
  -- engine liveness (board flags stale for working statuses — a frozen engine can't flag itself)
  add column if not exists heartbeat_at       timestamptz,
  add column if not exists retry_count        integer     not null default 0,
  -- resumable checkpoint: steps done + job IDs + last checkpoint (memoryless-wake resume)
  add column if not exists build_state        jsonb       not null default '{}'::jsonb,
  -- publish links
  add column if not exists ebook_link         text,       -- public e-book URL (pasted into YT copy)
  add column if not exists published_url      text;        -- the live YouTube URL

-- ── status contract guard (the 10 statuses) ──────────────────────────────
alter table public.episodes drop constraint if exists episodes_status_check;
alter table public.episodes add constraint episodes_status_check check (status in (
  'queued','building','awaiting_render','rendering','awaiting_cover',
  'assembling','awaiting_approval','revising','ready','published'));

-- ── auto-bump updated_at on every write (robust heartbeat/ordering) ───────
create or replace function public.set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;
drop trigger if exists trg_episodes_updated_at on public.episodes;
create trigger trg_episodes_updated_at before update on public.episodes
  for each row execute function public.set_updated_at();

-- ── messages: the per-episode Hugh <-> engine thread ─────────────────────
create table if not exists public.messages (
  id         uuid        primary key default gen_random_uuid(),
  episode_id uuid        not null references public.episodes(id) on delete cascade,
  created_at timestamptz not null default now(),
  sender     text        not null,                       -- 'hugh' | 'jodie' | 'engine' | 'cowork'
  kind       text        not null default 'note',        -- 'note' | 'change_request' | 'reply' | 'system'
  body       text        not null,
  handled    boolean     not null default false,          -- engine marks change_requests handled
  meta       jsonb       not null default '{}'::jsonb      -- e.g. {"asset":"thumbnail"}
);
create index if not exists messages_episode_created_idx on public.messages (episode_id, created_at);

-- RLS: authenticated users read + post; engine uses service_role (bypasses RLS) to reply/mark handled.
alter table public.messages enable row level security;
drop policy if exists "messages_select" on public.messages;
drop policy if exists "messages_insert" on public.messages;
create policy "messages_select" on public.messages for select to authenticated using (true);
create policy "messages_insert" on public.messages for insert to authenticated with check (true);
-- (no authenticated UPDATE/DELETE: humans post, they don't edit; the engine updates via service_role)

-- ── realtime: broadcast messages changes to the board (episodes already added in 001) ──
do $$
begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='messages') then
    execute 'alter publication supabase_realtime add table public.messages';
  end if;
end $$;

commit;

-- Sanity (run after commit):
-- select column_name from information_schema.columns where table_name='episodes' order by ordinal_position;
-- select * from public.messages limit 1;
-- select policyname, cmd from pg_policies where tablename in ('episodes','messages');
