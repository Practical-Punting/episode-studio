# Episode Studio — repo guide

Turns Practical Punting articles into YouTube episodes + e-books. Hugh operates
from a browser; the engine does the work. Supabase is the single source of
truth; Google Drive holds artifacts; THIS repo stays local (Drive corrupts
`.git`) at `C:\Users\jlral\repos\episode-studio`, remote
`github.com/Practical-Punting/episode-studio`.

## Layout
- `index.html` / `app.js` / `styles.css` — the operator board (v3), deployed via
  GitHub Pages: https://practical-punting.github.io/episode-studio/
- `engine/` — the orchestrator (Phase 2a spine). See `engine/README.md`.
- `supabase/` — migrations + `SCHEMA.md` (the data contract — read it first).

## Hard rules
- The 10-status contract lives in the DB; friendly lane labels live in the UI.
- `needs_look` is ORTHOGONAL to status (the red card; status unchanged).
- Human gates are sacred: never auto-render, never auto-publish.
- Secrets only in `PP Videos/.env` (service_role, HeyGen). Only the anon key
  ships client-side (RLS on). Never commit keys.
- All Supabase access goes through `PP Videos/scripts/rail.py` — one client.
- Build principles: `G:\My Drive\Planning\Principles.md` (simple, small, real,
  one-source-of-truth, well-documented).

## Working here
- Commit small and focused; push to `main` (Pages deploys from it).
- `python engine/engine.py run --mock --watch` exercises the engine safely
  (no credits). `cleanup-mock` when done.
