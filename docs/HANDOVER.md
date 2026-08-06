# HANDOVER — written 6 August 2026, for a session that was not here

**You cannot ask me anything. Everything below is written on that assumption.**
Read `PP-RULINGS.md` and `CLAUDE.md` first; this file is what those two do not carry —
**where things stand, what to do next, and the specific ways this build wastes a night.**

---

# 1. WHERE EP16 STANDS

**`Each-Way Betting Forever! — Part 2`** · rail id `3d08f141-751a-47ad-8a87-2f64297a5ef5`
· folder `PP-EP16` (not yet renamed — that is Stage 8, after publish).

| | |
|---|---|
| status | **`awaiting_approval`**, 18/18 steps done, not claimed, no flag |
| `PP-EP16-FINAL.mp4` | rebuilt under the new name · **QC PASS** |
| e-book PDF | 10 pages, Roger's two tables reproduced as his own 1988 scans |
| YouTube copy | written, `[PASTE E-BOOK LINK HERE]` left for Jodie |
| **all four approvals** | **FALSE** |

> ### ⚠️ `title_approved` IS FALSE ON PURPOSE. DO NOT "FIX" IT.
> It was ticked on 5 Aug against **"Squeeze Those Odds! — Part 2"**, a title that no longer
> exists. **An approval granted against a value that has since changed is not an approval**
> (`PP-STANDARDS`, 2 Aug). It was reset so Jodie approves the real name. The publish card
> only asks about approvals that are still false — leave it alone and she will be asked.

**WAITING ON:** Jodie's four approvals, and **Hugh's public e-book link** (`ebook_link` is
NULL; the publish card warns but does not block).

### 🚫 EP16 SHIPS AS IT IS — Jodie's explicit ruling. Do not touch this episode.
Two b-roll faults were found by Jodie and Hugh watching the finished film:
**1:25** `broll-nine-runners-turn` — the whole field in identical stride, hooves landing
together. **8:11** `broll-provincial-meeting-small-field` — riders in tweed and flat caps,
standing still in a motion clip.
**Both are fixed as PROMPT RULES in `broll-registry.md`, not as a re-render.** See
`PP-RULINGS.md` A4: **there is no b-roll approval step and there never will be.**

**EP16's halt tally: 9** — 7 machine faults, 2 human gates. **Every machine fault was
catchable before a credit moved.** That sentence is the whole argument for Job A.

---

# 2. TODAY'S ORDER

## JOB ZERO — THE ENGINE COMMISSIONS THE AUTHOR. **Biggest item. Nine days overdue.**
**Design already written and priced: `docs/DESIGN-engine-commissions-the-script.md`.**
Headless Claude Code invoked from the engine at the point it currently halts.
**~3.0 days, of which ~1.75 is the Doc-flow work already agreed — marginal cost ~1.25 days.**

**Proved on this machine, 5 Aug, not assumed:** headless runs (`claude -p … --output-format
json`), and **place-scoping HOLDS** — a sandboxed run with only `Read` was refused a file
outside its cwd, and the refusal came back as machine-readable `permission_denials`.

> **The heart of it is the TYPED VERDICT, not the subprocess.** `status` · `what_i_saw` ·
> `what_it_could_be[]` (asserting none) · `does_retry_help` · `unread_sources[]`.
> **A writer that could not read a source MUST BE UNABLE to return `ok`.** Nothing we own
> checks fidelity to the article — `render_ready` and `align_to_script` judge the RENDER —
> so **the risk is not the wall, it is the quiet paraphrase.**

⚠️ **EP16 proved §4's case before the thing was built:** `WebFetch` **refused** to reproduce
PP's own article, and the article's two tables exist **only as JPEGs** it cannot see. See
§13a of the design.

**And `save_youtube_copy` is its cheapest second user** — small artefact, an acceptance test
that already exists (`check_youtube_title`), and a failure that costs a retry, not a render.
**Two places the machine needs an AUTHOR, not an operator; Hugh can clear neither.**

## FIRST SMALL JOB AFTER JOB ZERO — the 0.85 archaeology
`align_to_script.MIN_MATCH = 0.85` **refuses a whole build** and appears **nowhere in
`docs/`**. EP16 passed at **87.8% — 2.8 points from halting.**
**It is archaeology, not a ruling request:** `git log` and `git blame` on
`align_to_script.py`, and establish **what `MIN_MATCH` actually measures** (share of OUR
words landing on a real aligned word; the rest interpolated).
🚫 **Do not ask Jodie to rule on the number until we can say what it means.**

## JOB A — MOVE EVERY FREE CHECK TO `audit_inputs`
**Runs alongside the editor. Different files, zero overlap.**
1. 🔴 **The `--force` fix first** — see §3.1. It is the nastiest item on the list.
2. Run the **whole card pipeline at authoring time**: `author_cards.validate` →
   `check_trace` → `autofit` → `card_check`. **Chromium and HTML. No API call, no credit.**
   *EP16's card faults — 20 schema/job, 26 trace, 3 layout — all fired at `cards_render`,
   after the render gate, the credit check and nine paid generations.*
3. **Capture-file structure**: `---- ARTICLE TEXT BEGINS/ENDS ----` markers present · every
   cue a literal substring of the approved script (**fold with `norm_words`, or it cries
   wolf on hyphens**) · every beat long enough for `3.0s + its card's hold` after its cue.
4. **Name and byline vs the source page's headline and standfirst — HALT, not warn.**
   *`check_one_name` cannot do this: it passed EP16 perfectly, on the wrong name.*

**Acceptance test already exists:** `engine/testdata/ep16-cards-BEFORE-FIX.episode.json` is
the real broken file. **E26 returns ZERO blockers on it** — that is the argument in one
measurement.

## 🚫 RECORDED, DELIBERATELY NOT BUILT — THE EPISODE NAME IS GUESSED FROM THE URL
**(Found 6 Aug 2026. Jodie's instruction: record it, do not build it today.)**

> ### `slugToTitle()` (`app.js:192`) BUILDS THE EPISODE NAME FROM THE WEB ADDRESS.
> **That is ruling A1 unenforced at the very first step a human touches.**

It takes the last URL segment, strips a trailing date, splits on hyphens and Title-Cases
every word. `…/testing-the-numbers-20070115` therefore created EP17 as
**"Testing The Numbers"** — capital T on "The", which is **not** the article's headline.
**A1 says the name comes from the page's own headline; nothing at create time has read
the page.**

⚠️ **AND THE BOARD HALF-KNEW.** `titleSmell()` (`app.js:111`) tests the title against a
`SMALL_WORDS` list that **contains "The"**, so it would have flagged this exact string —
and by design it only ever **suggests, never blocks**. *Grade 1 where grade 2 was needed.*
📌 **NAMING CORRECTION:** an earlier note called this function `looksLikeSlugCaps()`. **No
such function exists** — grepping that name finds nothing. It is `titleSmell()`.

**THE FIX, for when it is time:** the create step should leave the title **EMPTY** rather
than guess it from the web address, and say on the card that the studio fills it from the
article. **An empty box a human fills is honest; a wrong box that looks authoritative is
not.**

### WHY IT IS NOT BEING BUILT TODAY — and this is the reasoning, not the excuse
**The board already carries one unproven change from this morning:** the refresh pause
(`c087b7d`, `b7d7046`), whose **ctrl+Z behaviour is deliberately waiting on Jodie's hands
at EP17's words gate** — it follows from node identity, which is an argument, not an
observation. **A second `app.js` change now means EP17 tests two things and proves
neither.** *Same rule that made EP16 run on a Doc (A5), applied to the board instead of
the engine.*

## JOB B — BIND APPROVALS TO WHAT WAS APPROVED
Every approval flag is a **bare boolean**; nothing records which value it was given against,
so any later edit silently inherits consent. **Twice now — EP14 and EP16 — and both times a
human happened to look.**
**The shape already exists in the codebase:** `script_sha256` + `script_changed_since_approval`
do exactly this for the script and nothing else.
⚠️ **Half-absorbed by the editor** — it touches `approve-words` (app.js ~1009), the same
knot the editor untangles. **Doing them separately means untangling it twice.**

## THE SCRIPT EDITOR — SLICES 1–3 ONLY
**Priced 5 Aug: 2.75–4.5 days total, slice 5 unbounded.** Jodie has decided the direction;
the order is what was open.
- **Slice 1 · the refresh stops destroying what a human is editing — 0.75–1.5 d.**
  **Nothing else is possible until this exists.** `renderBoard()` does
  `host.innerHTML = out` every 30s; `restoreDrafts()` restores **value only** — caret,
  selection, scroll and undo die with the node. *This is what corrupted EP16's Doc URL:
  an insertion at offset 17, i.e. a paste landing where the caret used to be.*
  ⚠️ **Land it BETWEEN episodes** — it changes the surface Jodie uses at every gate.
- **Slice 2 · the editor as a ROUTE, not an overlay — 0.5–1 d.** `route()` already
  shows/hides `#login` and `#board`; add `#script` as a third sibling. **The card renderer
  does not change at all**, which is why a half-built editor cannot make the current path
  worse.
- **Slice 3 · a dedicated writer — 0.5–1 d.** `writeEpisode()` ends with `await loadAll()`
  — a full refetch **every 3 seconds while she types** — and **discards** a concurrent save
  rather than queueing it. Correct for a button, **silently lost keystrokes** for autosave.

**EP17 can run on the current Doc flow throughout.** Only slice 4 (`script_sync`) must land
whole, and it lands between episodes.

---

# 3. THE TRAPS — each of these cost real time on 5 August

## 3.1 🔴 THE `--force` TRAP — **the nastiest, because it inverts the evidence**
`author_cards`, `author_title_card`, `author_thumbnail`, `author_cover` and `author_ebook`
**all skip a file that already exists** (*"already generated — pass `--force` to redo"*), and
**the engine calls none of them with `--force`.**

> ## A CORRECT FIX LOOKS LIKE A FAILED ONE, TWICE.
> **It breaks nothing. It makes the truth invisible** — and the natural next move is to undo
> a change that was right, or hunt a second cause that is not there.

**ALWAYS delete the affected pages before re-checking.** *The layout fix's real effect — a
box moving from `(204,838)` to `(110,787)` — would otherwise have been completely hidden.*
**Fix:** re-author when the card's definition changed (mtime or a hash in the generated
marker). **Never blanket `--force`** — it would destroy hand-authored bespoke pages.

## 3.2 🔴 E28 — THE ENGINE HOLDS `build_state` IN MEMORY
`Ctx.state` is read **once, at claim**. A manual `build_state` write while the engine owns
the episode is **overwritten by the next `ctx.save()`**, and the read-back looks fine.

**THE ORDERING THAT BEATS IT, in this order:**
1. set `claimed_by` to a name that is **not** the live worker, and `lease_until` **in the
   FUTURE** — so `reclaim_stale` cannot grab it mid-edit;
2. **leave `needs_look` TRUE** so the engine stays parked and does no work;
   *(I cleared the flag in the same write once and the engine woke, retried a step and saved
   over my rewind — E28 caused by my own ordering)*
3. **wait, and confirm from the LOG** that it released (`lost ownership of the episode`);
4. **then** write `build_state`;
5. **last**, move `lease_until` into the past → `reclaim_stale` takes it with a **fresh
   Ctx**, which is what re-reads `build_state`.

## 3.3 🔴 REWINDING A STEP IN A PHASE THE ENGINE WILL NOT RE-ENTER DOES NOTHING
`PHASES[status]` decides which steps run. `cards_render` and `ebook_cover` are in
**`building`**; `assemble_*`, `self_qc`, `ebook_pdf`, `thumbnail`, `youtube_copy` are in
**`assembling`**.
**I rewound `cards_render` and `ebook_cover` while `status` was `assembling`. Both were
skipped.** **You must move `status` back to the phase as well.**
⚠️ **What that nearly cost:** I had deleted `ebook/cover.png` and
`overlay/export/ebook-cover.png`. Without `ebook_cover` re-running, the end card renders a
**grey box with alt text** and the e-book gets a **blank white page 1** — EP15's exact
failure. `check_page_images` catches it, **but it lives inside `cards_render`, which also
was not going to run.** Only a missing title clip halted Pass B in time.

## 3.4 🔴 THE DEAD ZONE AFTER ANY CODE CHANGE
The stale-code watch list is now **derived** (`_watched_files()` — every `.py` the engine
imported from `ENGINE_DIR`), so **ANY `.py` edit under `engine/` exits the running engine.**
`_code_changed_exit` then **releases the lease and leaves the working status**, producing
`status='building', claimed_by=NULL` — which `claim_next` (queued only) and `reclaim_stale`
(owner not null) **both ignore. Invisible forever.**

**RECOVERY — use the engine's own crash path, invent nothing:** set `claimed_by` to a name
that is **not** the live worker and `lease_until` to the past. `reclaim_stale` takes it back
within ~30s.
**Skill scripts under `.claude/skills/` are NOT watched** — editing `author_ebook.py` does
not exit the engine. **Editing `providers.py` does.**

## 3.5 🔴 A DELETE THAT CANNOT TELL "GONE" FROM "NEVER THERE"
My clean-up printed `(absent)` for four filenames that **do not exist in this pipeline at
all** — the title card is **`ep16-title.html` / `ep16-title.mp4`**, not `title-card.*`.
**Every one of those lines looked like a successful clean-up.**
**Combined with 3.1, the old name would have stayed burned into the film while every step
reported success.** The only thing that caught it was listing the directory by hand.
> **Derive a clean-up from what the build PRODUCES, and make "absent" an ERROR when the file
> was expected — never a quiet pass.**

## 3.6 SMALLER, BUT THEY EACH COST TIME
- **Film time ≠ shot-map time.** The title card shifts them by an amount I could only
  bracket at 6–11s. **To identify a clip, open the clip.**
- **`autofit` is blind to a whole class of "too big"** — it tests text under the logo and
  text clipped in a scroll box; `card_check` also reports an element whose box leaves the
  card. **The halt then blames the WORDS when nothing ever tried to shrink it.**
- **`_s` in `author_ebook.py` is a loop variable, not `sys`.** `file=_s.stderr` throws.
- **The `.mp4.mp4` trap.** Windows hides extensions, so *"rename it to
  `presenter-master.mp4`"* produces `presenter-master.mp4.mp4`, which `poll_heygen` cannot
  find. **Tell a human to type the name WITHOUT the extension.**

---

# 4. THE GAPS — do not rediscover these

**`PP-RULINGS.md` §B lists them in full.** The headline: **14 rulings recorded, at least 20
gaps**, and **eight of the gaps are numbers that stop or pass a build with no name against
them** — 180 kbps, **0.85**, 65 credits, 3.0s entry delay, the card holds, b-roll
duration/trim, the silent head and tail, the 40% assertion cap.

**Two worth knowing today:**
- **The crowd-diversity mix** appears verbatim in **every b-roll prompt ever written and
  nowhere in the standards.** It survives by being copied from the previous episode's file.
- **The standing outro says it "must be approved by Hugh once".** I can find **no record
  that the approval happened**, and every episode since has used it.

---

# 5. HOW TO WORK HERE — my own record, kept honestly

## MY ESTIMATES ARE UNRELIABLE UNLESS I HAVE READ THE CODE
- The pre-EP16 block: **I said 12–14 days. Jodie cut it to ~3.5. It landed in one evening.**
- The one time I was right was where I had read the file (`card_check.py` → one day, not
  three).
- **I reported "38 faults" twice from memory.** Rebuilding the file and measuring gave
  **20 in the first pass, 48 across three rounds** — wrong in both directions at once.
> **Give a wide honest range, or say "uncertain". Never a confident middle number.**

## ✅ THE TWO REFUSALS THAT WERE RIGHT — KEEP DOING THIS
Cowork asked for two things on 5 August that I declined, and it endorsed both refusals.

**1 · THE THEATRE TEST.** Asked to listen at two timestamps to check whether Gordon actually
said two missing cues, **I refused**: the words were already present in `aligned.srt` at
sensible timestamps, **which is stronger evidence than a level reading.** Running the test
anyway would have been theatre. *The cues were wrong; the master was fine.*

**2 · THE POINTLESS RE-RUN.** Asked to re-run `derive_card_timings` "to apply" the phrase
anchor, **I proved arithmetically that the tool already defaulted to it** (`enters = beat@ +
lead`, to 0.01s on every card) **and that the numbers would not move.** Re-running to
demonstrate a change that had already happened would have been theatre too.

> ### AND THE ONE THAT MATTERS MOST: **option (a) was already in place.**
> Asked whether setting three beats to WIDE would fix three overlaps, I checked — **all
> three were already WIDE.** Setting them would have changed nothing and been reported as a
> fix.
> **Setting values that do nothing and reporting it as fixed is precisely how a list stops
> being true.**

**The rule this comes from: assert the ARTEFACT, not the thing that reports on it — and
that applies to instructions as much as to code.** If a step cannot change the outcome, say
so and say why, rather than performing it.

---

*Written at 99% of context, deliberately, because knowledge in one machine's head is not
knowledge. Next: `PP-RULINGS.md`, then `CLAUDE.md`, then the checkpoint in memory.*
