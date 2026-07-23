# PP Episode Studio — the web board

A tiny static web app (no build step) that shows Practical Punting episodes and their
live status from the Supabase `episodes` table. Login via Supabase Auth (magic link).
Deploys to GitHub Pages.

## Files
- `index.html`, `styles.css`, `app.js` — the whole app (static; supabase-js from CDN).
- `supabase/migration.sql` — ep_number + RLS + policies + realtime (run in SQL editor).
- `supabase/AUTH-SETUP.md` — the dashboard clicks (enable email auth, invite users, URLs).

## Security model
- The web app ships ONLY the Supabase **anon/publishable** key — safe once RLS is on.
- RLS: authenticated users can read/write; anon gets nothing.
- The **service_role** key and all HeyGen/Higgsfield keys live ONLY in the engine's
  local `.env` — never here, never in this repo.

## Go live (one-time)
1. **Supabase:** run `supabase/migration.sql` in the SQL editor, then do
   `supabase/AUTH-SETUP.md` (enable email auth, close signups, invite Hugh + Jodie,
   add the Pages URL to the redirect allow-list).
2. **Deploy to GitHub Pages:**
   ```
   # create the repo (once) and push these files to it
   git init && git add . && git commit -m "Episode Studio: secure live board"
   git branch -M main
   git remote add origin https://github.com/<user>/episode-studio.git
   git push -u origin main
   ```
   Then GitHub → repo **Settings → Pages → Deploy from a branch → `main` / root**.
   Your URL: `https://<user>.github.io/episode-studio/`
3. Put that URL into Supabase → Auth → URL Configuration (Site URL + Redirect URLs).

## Acceptance
Open the Pages URL, log in with an invited email's magic link, and see **EP06 "Early
Pace Power Factors"** as a live card with its status. Change the row's status in
Supabase and watch the card update without a refresh.

## Scope
This is Stage 1 — the secure, live, read-only board. The human-step buttons (Start,
Render started, Cover A/B, Approve, Publish) and the orchestrator come in later stages.
