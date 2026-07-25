# Episode Studio — data model (the single source of truth)

Supabase holds **all state**; Google Drive holds **all artifacts** (renders, cards, e-books);
the repo stays local. This keeps the "brain" portable to a future rented media box.
Applied by migrations `migration.sql` (001) + `migration-002-engine.sql` (002)
+ `migration-003-locked-order.sql` (003).

## THE LOCKED ORDER (approved by Jodie, 26 Jul 2026 — do not re-sequence)
1. Paste article → script + words (title / hook / byline).
2. **Human turn 1 — Words Gate** (`title_approved`). Nothing builds before this.
3. On approval, **two things fire at once**: (a) **human turn 2** — start Gordon's
   HeyGen render (`render_started_at`), the LONG POLE, which depends only on the
   spoken track and so never waits on pictures; (b) the engine's gens batch —
   b-roll **plus both cover heroes** plus the motion cards.
4. **Human turn 3 — cover pick** (`cover_choice`), surfaced the moment
   `cover_a_url` + `cover_b_url` exist, i.e. *while* the render is still running.
5. Engine finishes b-roll / cover page / cards, hands-off.
6. Master lands → shot map → assembly → QC.
7. **Human turn 4** — the four approvals. 8. Publish → Stage-8 close-out.

The shape: turns 1-2-3 cluster at the FRONT, then a long hands-off render window,
then turn 4 at the END. `status` alone can't express "render running while
building" — that's what `render_started_at` is for.

## Status contract (unchanged) — DB `status`, 10 values
`queued → building → awaiting_render → rendering → awaiting_cover → assembling →
awaiting_approval → (change) revising → back to assembling → ready → published`
Enforced by a CHECK constraint. Under the locked order `awaiting_render` and
`awaiting_cover` are now **fallback parks**, not the normal route — both turns are
normally answered during `building`. **Friendly lane labels live in the UI, not the DB:**
- **Waiting** = `queued`
- **Engine working** = `building`, `rendering`, `assembling`, `revising` (a card here shows the
  red **"Needs a look"** treatment when `needs_look = true` — status is unchanged)
- **Your turn** = `awaiting_render`, `awaiting_cover`, `awaiting_approval`, and `ready` (Publish)
- **Done** = `published`

## Table: `public.episodes`
| Column | Type | Who writes | Purpose |
|---|---|---|---|
| id | uuid pk | — | episode id |
| ep_number | int | engine (at Start) | PP-EP number = max+1 |
| created_at / updated_at | timestamptz | DB (trigger bumps updated_at) | ordering |
| title | text | operator/create | episode title |
| source_url | text | operator | the article URL |
| status | text (checked) | engine/human | the 10-status contract |
| **needs_look** | bool | engine | ⚠ flag — problem needing a human (keeps its status) |
| **needs_look_message** | text | engine | plain-English problem (e.g. "a b-roll clip timed out") |
| **progress_step** | text | engine | "Building motion cards — 5 of 7" |
| **progress_pct** | int | engine | 0–100 for the bar |
| **heartbeat_at** | timestamptz | engine | liveness; board flags stale for working statuses |
| **claimed_by** | text | engine | which worker owns it (single-writer) |
| **lease_until** | timestamptz | engine | lease; expired → reclaimable after a crash |
| **retry_count** | int | engine | backoff bookkeeping |
| **build_state** | jsonb | engine | steps done + Higgsfield/HeyGen job IDs + checkpoint (resume) |
| **started_at / finished_at / build_seconds** | ts / ts / int | engine | timing (timers + "built in 41 min") |
| **cost** | jsonb | engine | `{higgsfield_credits, heygen_credits, aud}` |
| heygen_name | text | engine | `PP-EPnn — <Title>`, set EARLY (opens human turn 2) |
| **render_started_at** | timestamptz | human (board) | when the operator started the render — lets it run in parallel with `building` (003) |
| heygen_video_id | text | engine | HeyGen id once picked up |
| **cover_a_url / cover_b_url** | text | engine | the two cover-hero options (Drive links) |
| cover_choice | text | human | 'A' or 'B' |
| drive_folder | text | engine | `PP-EPnn` (artifacts live here on Drive) |
| video_url / ebook_url / thumbnail_url | text | engine | Drive links to the finished artifacts |
| **video_approved / ebook_approved / thumbnail_approved / title_approved** | bool | human | the 4 separate gates |
| youtube_copy | text | engine | recommended title + pointer to youtube.txt |
| **ebook_link** | text | human | public e-book URL (pasted into the YT copy at publish) |
| **published_url** | text | human | the live YouTube URL |
| notes | text | any | free notes |
| created_by | text | operator | who started it |

(**bold** = added in migration 002, except `render_started_at` = 003.)

The **hook** (the big thumbnail text) travels with the byline as a `Hook: …` line in
`notes`, and is shown on the Words Gate card so it is consciously approved (EP10 lesson).

## Table: `public.messages` (Hugh ↔ engine thread) — NEW
| Column | Type | Purpose |
|---|---|---|
| id | uuid pk | message id |
| episode_id | uuid fk → episodes(id) cascade | which episode |
| created_at | timestamptz | order |
| sender | text | 'hugh' / 'jodie' / 'engine' / 'cowork' |
| kind | text | 'note' / 'change_request' / 'reply' / 'system' |
| body | text | the message |
| handled | bool | engine marks a change_request done (drives Phase 3) |
| meta | jsonb | e.g. `{"asset":"thumbnail"}` |

Indexed on (episode_id, created_at). **Realtime on** (chat updates live), like `episodes`.

## Security (unchanged model)
RLS on both tables. Authenticated users (the 3 allow-listed) can **select/insert** episodes +
messages and **update** episodes (approvals, cover_choice, render-started, publish). The **engine**
uses the `service_role` key (bypasses RLS) for all its writes + marking messages handled.
Only the anon key is client-side.

## Never-freeze contract (how the flag works)
The engine bumps `heartbeat_at` every step. The **board** computes staleness client-side: if
`status` ∈ {building, rendering, assembling, revising} and `now − heartbeat_at` > threshold
(≈ a few min), it shows "Needs a look" — so a *frozen* engine is caught even though it can't
report its own freeze. Caught exceptions set `needs_look = true` + `needs_look_message` explicitly.

## Acceptance (Phase 0.5)
Final `episodes` + `messages` schema above; migration SQL in `migration-002-engine.sql`
(idempotent). No engine build. Next: Cowork/Jodie apply it → then Phase 1 (wire the v3 interface
to this schema).
