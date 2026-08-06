-- 005 — EVERY ARTEFACT GETS A WEB ADDRESS: the lock.
-- Applied 7 Aug 2026 via Supabase MCP (name: 005_web_addresses_guard).
--
-- WHY. thumbnail_url and ebook_url held `G:\My Drive\...` — a drive letter on ONE
-- laptop, rendered by the board as a link for a person who may not be sitting at
-- it. Hugh has nothing but the browser. youtube_copy held "see G:\...\x.txt", an
-- instruction to open a file on a machine the reader may not have. The same rows
-- already carried real https URLs for the cover A/B pair and the published video,
-- which is exactly what made it invisible.
--
-- ═══ A TRIGGER, NOT A CHECK CONSTRAINT, AND THAT IS THE WHOLE DESIGN ═══════════
-- A CHECK — even NOT VALID — is evaluated against the ROW on every future write.
-- EP06–EP17 still hold G:\ paths BY DECISION (published history, deliberately not
-- backfilled), so a CHECK would reject any later UPDATE to those rows: clearing a
-- flag on a published episode would fail because of a column nobody touched.
-- That bricks history.
--
-- This guards THE VALUE BEING WRITTEN. It fires only when the column is actually
-- being SET to something bad, so an unrelated update to a legacy row still
-- succeeds. Proved below.
--
-- ⚠️ ONE CONSEQUENCE, NAMED RATHER THAN DISCOVERED LATER. Because the test is
-- `is distinct from`, re-writing the SAME bad value a row already holds is a
-- no-op and is allowed. That is the necessary price of not bricking history, and
-- it is harmless: it cannot make the data worse. A DIFFERENT bad value — which is
-- what a real regression looks like — is refused. Found by a test that was
-- written against EP17, whose columns already held the exact strings being
-- probed; the lock was right and the test was wrong.
--
-- video_url IS EXEMPT BY DECISION. It stays a Drive path — ~159 MB, Hugh gets it
-- from Drive, and its link is a separate job. Not constrained here at all.
--
-- THE 1000-CHARACTER FLOOR IS MEASURED, NOT PICKED. Across every row on 7 Aug:
-- the pointers are 60 chars (EP08–EP15, EP17), the longest false value is 105
-- (EP07), and the only real description is 1,963 (EP16). 1000 sits ~9x above the
-- largest false value and ~2x below the smallest true one.
-- 🚫 AND IT IS A LENGTH TEST, NOT A PATH SNIFF. A LIKE '%\\%' rule was tried and
-- defeated by escape-character handling; length cannot be escaped around.

create or replace function public.episodes_guard_web_addresses()
returns trigger
language plpgsql
as $$
declare
  changed boolean;
begin
  -- ---- thumbnail_url: NULL, or a https:// web address -----------------------
  changed := (tg_op = 'INSERT') or (new.thumbnail_url is distinct from old.thumbnail_url);
  if changed and new.thumbnail_url is not null
     and new.thumbnail_url not like 'https://%' then
    raise exception
      'thumbnail_url must be a https:// web address that anyone can open, not a '
      'file path on one machine. Refused: %',
      left(new.thumbnail_url, 120)
      using errcode = 'check_violation',
            hint = 'Upload it with providers.publish_artefact() and store the URL it returns.';
  end if;

  -- ---- ebook_url: NULL, or a https:// web address ---------------------------
  changed := (tg_op = 'INSERT') or (new.ebook_url is distinct from old.ebook_url);
  if changed and new.ebook_url is not null
     and new.ebook_url not like 'https://%' then
    raise exception
      'ebook_url must be a https:// web address that anyone can open, not a file '
      'path on one machine. Refused: %',
      left(new.ebook_url, 120)
      using errcode = 'check_violation',
            hint = 'Upload it with providers.publish_artefact() and store the URL it returns.';
  end if;

  -- ---- youtube_copy: NULL, or the real description --------------------------
  changed := (tg_op = 'INSERT') or (new.youtube_copy is distinct from old.youtube_copy);
  if changed and new.youtube_copy is not null
     and length(new.youtube_copy) < 1000 then
    raise exception
      'youtube_copy must hold the DESCRIPTION ITSELF, not a pointer to a file. '
      'Got % characters; a real description runs past 1000.',
      length(new.youtube_copy)
      using errcode = 'check_violation',
            hint = 'Use providers.pasteable_description() on the -youtube.txt file.';
  end if;

  return new;
end;
$$;

drop trigger if exists episodes_guard_web_addresses on public.episodes;

create trigger episodes_guard_web_addresses
  before insert or update on public.episodes
  for each row execute function public.episodes_guard_web_addresses();

comment on function public.episodes_guard_web_addresses() is
  'Refuses a laptop path in thumbnail_url/ebook_url and a pointer-note in '
  'youtube_copy. Guards the VALUE BEING WRITTEN, never the row state, so the '
  'EP06-EP17 rows that still hold G:\ paths by decision remain updatable. '
  'video_url is exempt by decision. Job 1, 7 Aug 2026.';

-- ─── PROVED AGAINST REAL DATA, 7 Aug 2026, every probe inside a ROLLBACK ──────
--  REFUSED  G:\ path      -> thumbnail_url (a real change, on EP16)
--  REFUSED  G:\ path      -> ebook_url     (a real change, on EP16)
--  REFUSED  "see G:\..."  -> youtube_copy  (60 chars)
--  REFUSED  bare filename -> thumbnail_url ("PP-EP07-thumb.png")
--  REFUSED  http://       -> ebook_url     (http is not https)
--  REFUSED  INSERT of a new row carrying a G:\ thumbnail_url
--  REFUSED  999 chars     -> youtube_copy  (the boundary, from below)
-- SUCCEEDED update status on EP17            — legacy row, G:\ paths, NOT bricked
-- SUCCEEDED clear a flag on EP12             — legacy row, G:\ paths, NOT bricked
-- SUCCEEDED youtube_copy -> NULL             — NULL stays allowed
-- SUCCEEDED real https:// URLs on both columns
-- SUCCEEDED 1,955-char description (EP16-sized)
-- SUCCEEDED 1000 chars exactly               — the boundary, from above
