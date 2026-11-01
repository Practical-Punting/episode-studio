-- 008 — youtube_title and cover_lowres_url: two things the publishing workflow needs.
-- Applied 1 Nov 2026 via Supabase MCP (name: 008_youtube_title_cover_lowres).
-- Approved by Jodie 1 Nov 2026 — the columns shown to her before running; the
-- https-only lock on cover_lowres_url added at her request ("so it matches the
-- e-book and thumbnail links").
--
-- WHY. The pp-publish-episode skill runs in Claude's cloud app with a browser and
-- reads the rail. It had to work around two gaps:
--   youtube_title     — it read line 1 of output\<folder>-youtube.txt from the
--                       laptop. youtube_copy holds the DESCRIPTION only.
--   cover_lowres_url  — a browser can't open a local file, so it rebuilt the
--                       e-book cover by rendering page 1 of the PDF.
--
-- WRITTEN BY THE ENGINE: youtube_title in step_youtube_copy (line 1 of the
-- -youtube.txt, trimmed, never re-cased); cover_lowres_url in step_web_copies
-- (episode-assets/PP-EPnn/PP-EPnn-cover-lowres.jpg). Both nullable: a missing
-- cover JPG is logged and skipped, never a stopped build.
--
-- THE LOCK. episodes_guard_web_addresses() (005) is replaced WHOLE, unchanged
-- except for one new block for cover_lowres_url, the same shape as the
-- thumbnail_url / ebook_url blocks: it guards the VALUE BEING WRITTEN, so NULL
-- stays allowed. The live definition was read back and compared with 005 before
-- this was written (identical).

alter table public.episodes
  add column if not exists youtube_title    text,
  add column if not exists cover_lowres_url text;

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

  -- ---- cover_lowres_url: NULL, or a https:// web address (008) --------------
  changed := (tg_op = 'INSERT') or (new.cover_lowres_url is distinct from old.cover_lowres_url);
  if changed and new.cover_lowres_url is not null
     and new.cover_lowres_url not like 'https://%' then
    raise exception
      'cover_lowres_url must be a https:// web address that anyone can open, not a '
      'file path on one machine. Refused: %',
      left(new.cover_lowres_url, 120)
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

comment on function public.episodes_guard_web_addresses() is
  'Refuses a laptop path in thumbnail_url/ebook_url/cover_lowres_url and a '
  'pointer-note in youtube_copy. Guards the VALUE BEING WRITTEN, never the row '
  'state, so the EP06-EP17 rows that still hold G:\ paths by decision remain '
  'updatable. video_url is exempt by decision. Job 1, 7 Aug 2026; '
  'cover_lowres_url added 1 Nov 2026 (008).';
