# Episode Studio — repo guide

**Before working, read `G:\My Drive\Jodie-Cowork\context\claude.md` and the three
files it points to** (how-i-talk / how-you-work / who-i-am) — Jodie's context set.

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
- **`docs/` — THE HOME OF THE GOVERNING STANDARDS.** Read `docs/PP-STANDARDS.md`
  first for any episode work.

## Where the rules live — ONE HOME (Jodie, 27 Jul 2026)
- **`docs/` in THIS repo is the single home for the governing standards.** Read
  them here. Write them here. Never anywhere else.
- **The Drive copies at `G:\My Drive\PP Videos\docs\` are BEING RETIRED.** They
  were moved in byte-for-byte on 27 Jul 2026 and are on their way to becoming
  signposts. **Do not edit them, and do not read them as authoritative** — if
  the two ever differ, the repo wins.
- **The claude.ai project is a JOURNAL.** It holds no rule text, pointers only.
  Google Drive keeps media and episode outputs; Supabase keeps runtime state.
- **Any rule Jodie approves is written ONCE, here, by Claude Code. Cowork never
  writes rules.**
- **EVERYTHING CODE-SHAPED IS NOW IN THE REPO (28 Jul 2026): CODE IN GITHUB,
  MEDIA ON DRIVE.** The `pp-episode-production` skill, `broll-registry.md` and
  `rail.py` all moved in. The engine resolves the skill from
  `providers.py` → `SKILL_DIR`, and `PP_VIDEOS` now points at **media only**:
  episode folders, the Google Docs and `.env`. *(This bullet used to read "two
  things deliberately did NOT move… moving either breaks the engine." They moved;
  nothing broke.)*
- `docs/*.md` is marked `-text` in `.gitattributes` so `core.autocrlf` cannot
  rewrite LF as CRLF and break byte-identity with the originals.

## Hard rules
- The 10-status contract lives in the DB; friendly lane labels live in the UI.
- `needs_look` is ORTHOGONAL to status (the red card; status unchanged).
- Human gates are sacred: never auto-render, never auto-publish.
- **SCRIPT GATE** (Jodie, 26 Jul 2026): the script lives as a Google Doc in the
  episode's Drive folder — its ONE home. The gate passes only when the words are
  approved AND "I've read the script" is ticked. The engine re-reads the Doc on
  approval and builds from that, never from a cached draft. Auto-render may NEVER
  fire on a script that hasn't passed — `assert_script_gate()`, no override.
  Approving the script is a DECISION; decisions stay human. Starting a render is
  a chore and may be automated. Automation eats chores, never decisions.
- **THE LOCKED ORDER** (approved 26 Jul 2026, in `PP-STANDARDS.md` + `engine/README.md`):
  words gate → render gate AND the gens batch fire in parallel → cover pick
  during the render window → hands-off finish → four approvals → publish.
  Human turns 1-2-3 at the front, turn 4 at the end. Never render-last.
  Re-sequencing needs Jodie's explicit re-approval.
- Secrets only in `PP Videos/.env` (service_role, HeyGen). Only the anon key
  ships client-side (RLS on). Never commit keys.
- All Supabase access goes through `engine/rail.py` — one client, in the repo
  since 28 Jul 2026 (was `PP Videos/scripts/rail.py`).
- Build principles: `G:\My Drive\Planning\Principles.md` (simple, small, real,
  one-source-of-truth, well-documented).

## Working here
- Commit small and focused; push to `main` (Pages deploys from it).
- `python engine/engine.py run --mock --watch` exercises the engine safely
  (no credits). `cleanup-mock` when done.
