-- Episode Studio — Stage 1 migration
-- Project: ydqzdzpyemrqttiyhpwp  ·  table: public.episodes
-- Run this whole file in the Supabase SQL editor. It is IDEMPOTENT (safe to re-run).
-- It does three things: (a) ep_number + backfill, (c) RLS + policies in one shot,
-- and (2) turns on realtime so the board updates without refresh.
-- (Auth email + inviting Hugh/Jodie is dashboard config — see AUTH-SETUP.md.)

begin;

-- 1a. ep_number, and backfill EP06 = 6 -------------------------------------
alter table public.episodes add column if not exists ep_number integer;

update public.episodes
   set ep_number = 6
 where title = 'Early Pace Power Factors'
   and ep_number is null;

-- 1c. Enable RLS *with* policies in the SAME change ------------------------
--     (never enable RLS without policies, or everyone is locked out).
--     Rule: authenticated users get full read/write; anon gets nothing.
alter table public.episodes enable row level security;

drop policy if exists "authenticated_select" on public.episodes;
drop policy if exists "authenticated_insert" on public.episodes;
drop policy if exists "authenticated_update" on public.episodes;

create policy "authenticated_select" on public.episodes
  for select to authenticated using (true);

create policy "authenticated_insert" on public.episodes
  for insert to authenticated with check (true);

create policy "authenticated_update" on public.episodes
  for update to authenticated using (true) with check (true);
-- No DELETE policy on purpose: deletes are blocked via the API for everyone.
-- (The engine uses the service_role key, which bypasses RLS, for admin deletes.)

-- 2. Realtime: broadcast row changes to the board -------------------------
--    (guarded add — the publication can't take "if not exists").
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
     where pubname = 'supabase_realtime'
       and schemaname = 'public'
       and tablename  = 'episodes'
  ) then
    execute 'alter publication supabase_realtime add table public.episodes';
  end if;
end $$;

commit;

-- Sanity checks (optional — run after the commit):
-- select id, ep_number, title, status from public.episodes order by ep_number;
-- select relrowsecurity from pg_class where oid = 'public.episodes'::regclass;   -- expect: t
-- select policyname, cmd, roles from pg_policies where tablename = 'episodes';
