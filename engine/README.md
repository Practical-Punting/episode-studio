# Engine — the orchestrator spine (Phase 2a)

The conductor for Episode Studio: claims ONE queued episode from the rail and
drives it through the status contract, crash-safe, never silently frozen.
Built to `PP-engine-design-and-build.md` + the refined plan.

## Run it

```
python engine/engine.py run --mock --watch    # mock everything (no credits), keep going across gates
python engine/engine.py run --mock            # one leg: work until the next human gate, then exit
python engine/engine.py mock-episode          # create the PP-EP99 test ticket
python engine/engine.py status                # quick board glance
python engine/engine.py cleanup-mock          # remove mock tickets + .mock/ artifacts
```

## THE SUPERVISOR — the engine starts itself (29 Jul 2026)

```
python engine/supervisor.py --status              # what it would do; changes nothing
python engine/install_supervisor_task.py --show   # the Task Scheduler entry
python engine/prove_supervisor.py                 # kill the engine, watch it come back
```

A Windows scheduled task, **"PP Episode Studio engine"**, runs `supervisor.py` at
logon and **every 5 minutes indefinitely**. The supervisor starts
`engine.py run --watch` and nothing else — it never renders, never publishes and
never clears a flag.

**Why.** The engine went down twice in two days and only one of those was a fault.
The other was the **stale-code guard exiting on purpose**: `_code_changed()` ends the
process whenever `engine.py`, `providers.py` or `rail.py` changes, which is correct —
and it means every deploy leaves the engine down until a human restarts it. That is
not a bug to fix; it is a design decision that needed a partner.

- **Working directory and `PP_VIDEOS_DIR` are set explicitly.** Task Scheduler's
  default cwd is `System32`, and since the repo moved off Drive `rail.py`'s parent
  walk no longer reaches `PP Videos/.env`.
- **Everything is appended to `engine/logs/engine-YYYY-MM-DD.log`** (gitignored). A
  supervisor whose failures are silent is worse than none.
- **It refuses to start into a broken environment, loudly** — no `G:`, no `.env` —
  and logs why rather than blaming an episode for the machine.
- **`IgnoreNew` + the engine's own lock.** The task instance lives as long as the
  engine, so the 5-minute tick is a no-op during normal running.
- ⚠️ **The repetition is on a DAILY trigger, not the logon one.** On the logon
  trigger it registered fine, reported `Next Run Time: N/A` and would not have ticked
  once until the next logon. *An installed task that never fires is the hope it was
  meant to replace.*
- ⚠️ **There is no boot trigger.** It runs in the interactive session because **G: is
  Google Drive and only exists there**; a boot trigger could not fire before login
  anyway, and registering one needs administrator rights.

**PROVED, not asserted (29 Jul 2026):** engine killed on pid 76464, back by itself on
pid 75784 **13 seconds later** with no human involved — the whole sequence in the
dated log. *13s because the kill landed just before a tick boundary; the guaranteed
bound is 5 minutes.*

### 🟦 OPTIONAL — "poke it awake", for when a person is watching and impatient

> ## 🚫 THIS IS NOT A STEP IN NORMAL RUNNING. NOBODY HAS TO DO THIS, EVER.
> ## THE DEFAULT IS THAT NOBODY POKES ANYTHING.
> **The engine picks work up by itself.** The drafting pass sweeps every **15 minutes**;
> everything else the engine does is driven by the board and the rail. If you do
> nothing at all, the machine still does the work — it may simply be up to fifteen
> minutes before it starts.
>
> **This note exists for ONE situation:** somebody is sitting there watching, has just
> put a capture in place, and does not want to wait for the next sweep. That is a
> convenience, not a duty. *(Written 7 Aug 2026 at Jodie's request, on EP18's first
> live draft, and labelled this way at her insistence so it can never read as a chore.)*

**If you are watching and do not want to wait, the safe nudge is A CLEAN ENGINE
RESTART.** A fresh process runs its first drafting sweep straight away, because the
sweep timer starts at zero; the supervisor brings the engine back within five minutes
of any exit, on its own.

```
python engine/supervisor.py --status     # is it even running, and on what pid
```

> ### 🔴 THE ONE RULE, AND IT IS THE WHOLE REASON THIS IS WRITTEN DOWN:
> ### **NEVER KILL A LIVE COMMISSION.**
> A commissioned writer runs for **three to five minutes**. Ending the engine while one
> is in flight throws that work away **and spends one of the three attempts** the
> drafting pass is allowed — so the nudge costs an attempt and gains nothing.
>
> **LOOK BEFORE YOU POKE.** The log says plainly whether a writer is working:
> ```
> commissioning this episode's script — a writer is working, up to 1200s
> ```
> If that line is the last thing in the log with no result under it, **a writer is
> working right now. Do nothing.**
> *Worked example, 7 Aug 2026: the nudge was asked for at 11:22 and the sweep had
> already fired by itself at 11:23:32. Poking would have aborted a live commission and
> burned an attempt, to save nothing at all.*

Config comes from `PP Videos/.env` via `scripts/rail.py` (the ONE Supabase
client — service_role key, never client-side). Overrides:
`PP_VIDEOS_DIR`, `ENGINE_WORKER`, `ENGINE_CREDIT_CEILING`, `ENGINE_RETRY_DELAYS`,
`ENGINE_BROLL_MODEL`, `ENGINE_COVER_MODEL` / `_ASPECT` / `_RES` / `_CEILING`,
and the mock switches in `providers.py` (`MOCK_FAIL_STEP`, `MOCK_FAIL_ONCE`,
`MOCK_BALANCE`, `MOCK_STEP_SECS`, `MOCK_BROLL_CLIPS`).

## How it holds the principles

- **Single-writer lease** — claim sets `claimed_by` + `lease_until`; heartbeats
  renew it; a crashed worker's lease expires and the episode is reclaimable
  (`rail.reclaim_stale`). A heartbeat that comes back empty means ownership was
  lost, and the engine stops touching that episode.
- **Resumable** — every step checkpoints into `build_state` (`steps` done +
  `jobs` with per-clip Higgsfield job IDs and per-poll progress). A submitted
  job is checkpointed the instant it exists and is NEVER re-submitted; a
  memoryless restart skips done work exactly.
- **Never-freeze** — heartbeat thread beats every 20s through every retry and
  wait; transient failures retry with backoff (mock 2/4/6s, real 5/25/120s);
  exhaustion or an `EngineFlag` writes a plain-English `needs_look` message and
  waits ALIVE for the flag to clear (the board's stale-heartbeat check catches
  the case where the engine truly dies).
- **Human gates sacred** — the words, the render, the cover pick, the four
  approvals. The engine offers and waits; only a human answers.
- **Credit guard** — estimates the spend before firing gens (b-roll *and* the
  two cover heroes); refuses to start (flags instead) if the balance can't
  cover it or it exceeds `ENGINE_CREDIT_CEILING` / `ENGINE_COVER_CEILING`.

## THE SCRIPT GATE (Jodie, 26 Jul 2026) — no override

The script lives as a **Google Doc in the episode's Drive folder**. That Doc is
the single source of truth; `docs/spoken-words.txt` is a derived cache the engine
overwrites from it in the first build step (`script_sync`). The gate passes only
when a human has done BOTH — approved the words AND ticked "I've read the script"
(`title_approved` + `script_read`, enforced in `rail.claim_next`'s filter).

`assert_script_gate(ep)` is the guard, called at `script_sync`, `audit_inputs`
and `render_gate`. **Any future auto-render path must call it before submitting
anything to HeyGen.** There is no flag, no env var and no fast path past it —
approving the script is a decision, and decisions stay human.

If the Doc can't be read, the episode flags `needs_look` in plain English and the
build stops; it never falls back to the stale local draft. If the Doc changes
after approval, `script_changed_since_approval` is set (the card shows it) and the
build carries on using the approved snapshot.

### Rail integrity gate — `rail.py` can't drift unnoticed

`rail.py` holds the Script Gate's enforcement: the `claim_next` filter that refuses
to hand out an episode nobody has read the script for. A revert there would disable
that guarantee **silently** — the engine would keep running and the board would
still look healthy. It is the one failure in the system that had no alarm on it.

**Step 2 landed on 28 Jul 2026.** `rail.py` now lives in the repo at
`engine/rail.py`, and the gate compares it against **git HEAD** instead of against a
checked-in duplicate (`engine/gitgate.py`). This is what the old note below called
"step 2 of two", and it is strictly stronger than what it replaces:

- it catches an **uncommitted local edit** — the actual risk — which the
  reference-copy gate could not see at all;
- it **cannot be defeated by editing two files**, which the old one could, because
  it compared two copies to each other rather than either to a reviewed baseline;
- there is **no duplicate to keep in sync**, so the "update the reference in the
  same commit or every build dies" footgun is gone.

It runs **before `import rail`**, exits **4** on any doubt, and every failure path is
fatal — `SystemExit` inherits `BaseException`, so the engine's own `except Exception`
handlers cannot swallow it. No bypass flag, no environment variable, and `--mock`
does not skip it (mock writes to the real rail).

**To change rail.py deliberately:** edit it and **commit**. That is the whole
procedure. The gate refuses to run on an uncommitted change, which is the point —
every version the engine has ever run is in the history, attributable.

*(Retired with this change: `engine/rail.reference.py`, its `-text` line in
`.gitattributes`, and the byte-comparison helper. The gate uses
`git status --porcelain`, which applies git's own clean filters, so it is immune to
the `core.autocrlf` conversion that made `-text` necessary.)*

### QC integrity gate — `qc_episode.py` can't drift unnoticed

`qc_episode.py` decides whether a finished episode is good enough to ship. It once
existed in TWO unversioned copies that had already drifted, the weaker one missing
three hard-fail rules (card word-cue anchoring, b-roll/card overlap, midroll
visibility). If the weaker one ever ran, an episode would **pass while being judged
by the wrong rules** — a silent quality failure.

It now lives in the repo at `.claude/skills/pp-episode-production/scripts/`, and
`RealProvider._qc_integrity_gate()` asserts it matches **git HEAD** immediately
before shelling out to it, inside `self_qc`. Any doubt prints to stderr and
**exits 5** (the rail gate uses 4). No bypass flag, no environment variable. Mock
mode never runs this script — it has its own `self_qc` — so there is nothing to skip.

Checking at the point of use rather than at startup means a drift introduced
mid-build is still caught. The cost is that it fires late, after credits are spent —
but the build is checkpointed, so fixing the file and restarting resumes at
`self_qc` rather than rebuilding.

**To change qc_episode.py deliberately:** edit it and **commit**. No reference file
to refresh.

*(Retired with this change: `engine/qc_episode.reference.py` and its `-text` line.
The second drifted copy in `pp-production-plugin/` is retired too — `plugin/pack.py`
now regenerates the bundle from the repo skill into a gitignored `plugin/dist/`, so
a checked-in second copy cannot exist to drift.)*

### Known future upgrade — reading script Docs

The engine is a standalone Python process with no Google login. It cannot use the
Drive connector that Claude sessions use — that connector belongs to the session,
not to the machine. So today the engine reads a script Doc through the Doc's
plain-text export URL (`/export?format=txt`), which requires that Doc to be set to
**"anyone with the link can view"**.

The proper long-term fix is a **Google service account with read-only Drive
scope**: the engine authenticates as itself, reads the Doc directly, and no
sharing is needed at all. It can be swapped in later without undoing any of the
Script Gate work — only `RealProvider.fetch_script()` changes.

**This is a deliberate, accepted trade-off, not an oversight.** Decided by Jodie,
26 Jul 2026: every word of these scripts is published publicly on YouTube by
design, so a link-shared Doc exposes nothing that isn't about to be broadcast
anyway; the URLs are unguessable; and the `script_snapshot` + `script_sha256`
audit trail plus the drift flag cover what physical doc-locking would have
prevented. The sharing rule that goes with it — individual episode script Docs
ONLY, never a folder, never anything holding subscriber data or method material —
is a hard rule in `PP-STANDARDS.md`.

## THE LOCKED ORDER (approved by Jodie, 26 Jul 2026)

Do not re-sequence without her explicit re-approval.

**AMENDED 9 Aug 2026 (approved):** the render gate opens AT THE WORDS GATE — it needs only the approved script and the project name, and both are final the instant she clicks Approve — and the episode.json commission, the gens batch and the cards all run BEHIND it, inside the render window.
(Re-sequenced 9 Aug 2026 with Jodie's explicit approval. It used to fire the render and the gens batch in parallel, which meant the render waited on `audit_inputs` — a four-second scan until it became a COMMISSION on 7 Aug. EP18, a clean run, still made Gordon wait 17m14s, 98.7% of it that commission.)


1. Article → script + words. 2. **Words Gate** (title / hook / byline).
3. On approval, **in parallel**: (a) the render gate opens — Gordon starts
   cooking, the LONG POLE (5-45 min), which depends only on the spoken track
   and so must never wait on pictures; (b) the gens batch fires — b-roll **and**
   both cover heroes. 4. **Cover pick**, surfaced the moment both heroes exist,
   *during* the render. 5. Engine finishes cover page + cards, hands-off.
6. Master → shot map → assembly → QC. 7. The four approvals. 8. Publish →
   Stage-8 close-out.

The shape: human turns 1-2-3 back-to-back at the FRONT, one long hands-off
window, turn 4 at the END. Never render-last, never human-machine ping-pong.

**The guard.** `check_locked_order()` runs at engine start and warns (naming the
locked order) if the step lists have been re-sequenced. At run time the engine
stamps `build_state.order` — `render_offered_at`, `gens_started_at`,
`covers_ready_at`, `cover_picked_at`, `master_at` — and warns if the gens batch
started before the render gate opened, if the cover heroes appeared after the
master landed, or if the whole batch finished with the render still unstarted.
Warnings are logged AND kept in `build_state.order.warnings`.

## Status → steps map

| status | engine steps |
|---|---|
| building | **script_sync** (re-reads the Doc, snapshots it) → audit_inputs → **render_gate** (sets `heygen_name`, opens human turn 2) → credit_check → broll_submit → **covers_ab** (sets `cover_a_url`/`b_url`, opens human turn 3) → broll_collect → **cover_pick** (waits in place; status stays `building`) → ebook_cover (built from the pick) → cards_render → `rendering` if `render_started_at`, else park `awaiting_render` |
| rendering | heygen_download (poll by project name) → shot_map → `assembling` (the cover was picked back in the build) |
| assembling | passA → passB → self_qc → ebook_pdf → thumbnail → youtube_copy → park `awaiting_approval` (writes links, `build_seconds`, releases claim) |
| revising | Phase 3 — flags honestly instead of guessing |

`awaiting_render` and `awaiting_cover` are now **fallback parks**: reaching
either means a human turn wasn't taken during the build, and the engine says so.

## Real mode (2a-real, shaken down 2026-07-24)

`RealProvider` drives the standing toolkit for every scriptable step: cover
re-render (render_still), card batch (render_cards_batch), HeyGen master
pickup by project name via the API `video_url` (+ the ≥180 kbps audio gate),
shot map (build_shot_map), pass A/B (emit the graph with assemble_episode.py,
then run the documented ffmpeg command with the exact input layout), QC
(qc_episode), e-book (build_figures → author_ebook → build_ebook/WeasyPrint),
thumbnail (render_still).
Find-or-build everywhere: a staged artifact is used, never rebuilt or
re-spent. Proven end-to-end on a staged EP07-asset test episode (PP-EP98):
QC PASS, 0 credits, 0 retries.

### The build authors its own assets (1d, 28 Jul 2026) — the four halts are gone

The engine used to RENDER assets it never AUTHORED, so an episode arriving
without them halted with a message asking a browser operator to write HTML.
Four such halts existed; all four are now closed, each in its own slice:
**cards** (`fd4fd4e`) · **cover** (`80963d2`) · **thumbnail** (`3764b60`) ·
**e-book**. Missing PAGES are authored from the standing templates; missing
DATA still halts, which is correct — but it now names the card and the field.
Nothing is ever overwritten: a page without the generated marker is treated as
hand-authored and left alone.

**`ebook_pdf` is the last of the four, and it does three things:**
1. `build_figures.py` renders the figures from the CARD pages in print mode —
   one design, two uses. Nothing ran this before; every earlier episode's
   figures were made by hand. A figure that fails to render HALTS.
2. `author_ebook.py` joins the standing shell to the episode's `ebook/body.html`
   **and runs the FIDELITY GATE** — the body must reproduce the source article
   character-for-character, departures aside, or the build stops naming the
   exact word. See PP-STANDARDS §E-book and `DESIGN-self-authoring-build.md` §3a.
3. `build_ebook.py` renders and QCs the PDF.

**None of this moved a step.** `PHASES` and `check_locked_order()` are
unchanged — authoring happens INSIDE the existing steps, which is why the
locked order cannot regress. The figures are built in ASSEMBLING from
`overlay/export`, which `cards_render` filled back in BUILDING.

### Higgsfield: hands-off gens via the CLI (B+, wired 2026-07-24)

The engine fires b-roll gens itself through the **Higgsfield CLI** on the
existing plan's credits: balance via `hf account status`, an EXACT per-clip
cost preview in the credit guard (no spend), the registry no-repeat check
before any spend, then per-clip `generate create` → poll → download with
job-id checkpoints (a submitted job is never re-submitted). Model:
`ENGINE_BROLL_MODEL` (default `kling3_0_turbo`, 5s 720p 16:9 — the b-roll
standard; ~7.5 credits/clip). If the CLI is absent or unauthenticated, every
gen path falls back to the honest b-roll gate (a flag naming the clips).

One-time install per machine (`npm i @higgsfield/cli` breaks under Git-Bash
tar on Windows, so install the release binary directly):
1. Download `hf_<ver>_windows_amd64.tar.gz` from github.com/higgsfield-ai/cli
   releases; extract `hf.exe` to `C:\Users\jlral\tools\hf\` (or set `HF_CLI`).
2. `hf auth login` (one browser approval; token → `~/.config/higgsfield/`).
3. `hf workspace set <id>` (see `hf workspace list`).

### Cover heroes: generated UPFRONT (R7, 26 Jul 2026)

Both cover heroes are part of that same gens-first batch — `nano_banana_pro`,
portrait 2:3, 2k, ~2 credits each (~4 total), previewed and capped by
`ENGINE_COVER_CEILING` before anything is spent. Prompts come from
`episode.json → cover.hero_a_prompt / hero_b_prompt` (Cowork writes them, two
DIFFERENT compositions); job ids are checkpointed into `docs/hero-jobs.json`
the instant they exist, so a restart never re-spends. Files:
`ebook/cover-src/hero-a.png` + `hero-b.png` are the two OPTIONS; `hero.png` is
whichever is ACTIVE (what `cover.html` draws) — `ebook_cover` copies the picked
one over it. Older episodes that only have `hero.png` + `hero-b.png` are adopted
as-is (`hero.png` IS option A).

Because they're made before the long b-roll collect, the pick reaches the
operator minutes into the build — never mid-run as "no e-book cover, needs a
look", and never after the master lands.

Still human / staged, on purpose:
- **The HeyGen render itself** — a sacred human step, unchanged; the engine
  names the project, opens the gate early, and downloads the finished master.
- **The cover PICK and the YouTube copy** — the pick is Jodie's/Hugh's; the
  copy is staged by the create side (Cowork) until the create brain (Phase 4).
  Registry `--append` after a generated episode also stays a create-side step.

Phase 2b (three in flight + the local render lock) builds on this spine.
