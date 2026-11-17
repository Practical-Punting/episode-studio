-- 010 — script_notes: per-episode instructions the SCRIPT WRITER reads.
-- Applied 17 Nov 2026 via Supabase MCP (name: 010_script_notes).
--
-- WHY. Hugh's Batch 1 rulings (approved 17 Nov 2026, EP60-EP69 + GH02-GH04) say
-- things only a human can decide about one episode's script: leave out these two
-- paragraphs, say this fact, add nothing beyond the article. The script commission
-- read NOTHING from the rail — not the hook, not the byline, not `notes` — so there
-- was no way for any of it to reach the writer. EP60 is the episode that showed it.
--
-- WHY A NEW COLUMN AND NOT `notes`. `notes` is already a shared scratch field: the
-- board appends "ebook_link skipped deliberately…" to it at publish, and it is the
-- legacy home of "Hook: …" / "Byline: …" lines that hookOf/bylineOf still read.
-- Instructions to the writer must contain the writer's instructions and nothing
-- else, or an operator's aside becomes a ruling.
--
-- FORMAT (read by engine/episode_rulings.py — the one parser):
--   · free text, one instruction per line, passed to the writer VERBATIM;
--   · a line starting "Leave out:" followed by the quoted opening words of an article
--     paragraph is ENFORCED: the paragraph must be findable in the article (checked
--     before an attempt is spent) and the script must not say it (checked at the gate).
--   · its figures count as approved words for script_fidelity, like the hook.
--
-- NULLABLE, NO DEFAULT, NO BACKFILL, NO TRIGGER. NULL or "" means "no notes", and the
-- writer's brief is then byte-identical to what it was before this column existed.

alter table public.episodes
  add column if not exists script_notes text;

comment on column public.episodes.script_notes is
  'Per-episode instructions for the SCRIPT WRITER, from the human gate (Hugh/Jodie). '
  'One per line, passed verbatim into the script commission. A line "Leave out: '
  '\"<opening words of a paragraph>\"" is enforced by engine/episode_rulings.py. '
  'NULL/empty = no notes = the brief is exactly as before. Migration 010, 17 Nov 2026.';
