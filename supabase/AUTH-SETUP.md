# Supabase Auth setup — Episode Studio (dashboard steps)

These are the clicks that can't be done from code. ~3 minutes in the Supabase
dashboard for project **ydqzdzpyemrqttiyhpwp**. Do these **together with** running
`migration.sql` — RLS + Auth are one security change.

## 1. Enable email auth
Dashboard → **Authentication → Providers → Email** → toggle **Enabled** on.
(No password needed — we use magic-link/OTP sign-in.)

## 2. Allowed users — the allow-list
Our RLS policies grant every *authenticated* user access, so WHO can authenticate **is**
the access control. The **allow-list of 3 users is managed in Supabase Auth** (created
email-confirmed via the GoTrue admin API, so magic-link login works with public sign-ups
off). The actual addresses live **only in the Supabase dashboard — never in this repo**
(this is a public repo).

**To add a new user later:** create them via the admin API
(`POST /auth/v1/admin/users` with `email_confirm:true`, or the engine). **Supabase Auth
is the single source of truth** for who may access Episode Studio.

**Keep public sign-ups OFF** so no one outside the allow-list can self-register:
Authentication → **Sign In / Providers** (or **Settings**) → **"Allow new users to
sign up" = OFF**.

## 3. Allow the app's URL for magic-link redirects (IMPORTANT)
Magic links only redirect back to allow-listed URLs.
Authentication → **URL Configuration**:
- **Site URL:** `https://<your-github-username>.github.io/episode-studio/`
- **Redirect URLs:** add the same URL (and, for local testing, `http://localhost:*`).

(If this is skipped, login emails send but the click won't return to the board.)

## 4. Give the ENGINE its key (so rail.py survives RLS)
Once RLS is on, the anon key can no longer read/write the table — that's the point.
The **engine** (`scripts/rail.py`) must use the **service_role** key, which bypasses
RLS and stays secret on the machine:
1. Settings → **API** → copy the **`service_role`** key (NOT the anon key).
2. Add it to `G:\My Drive\PP Videos\.env` as `SUPABASE_SERVICE_ROLE_KEY=...`
   (or paste it to Claude Code and it'll store it — never printed, never in the web app/repo).

`rail.py` already prefers `SUPABASE_SERVICE_ROLE_KEY` when present.

## Verify
- Anon key alone (no login) can no longer read the table → RLS working.
- Hugh/Jodie can log into the web app and see EP06 → Auth + policies working.
- The engine (`python scripts/rail.py list`) still works → service key in `.env`.
