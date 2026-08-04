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
- **THE RAIL IS SELECT / INSERT / UPDATE. NO DELETE.** One exception, ruled
  3 Aug 2026: the cover A/B pair may be deleted when an episode is published,
  and it must log what it removed. **The rows themselves are NEVER deleted** —
  they are the studio's memory, and every structural fix this week came from
  comparing episodes to each other. Deletions are otherwise Jodie's.
- **CODE FREEZE WHILE AN EPISODE IS RUNNING.** Never edit `engine.py`,
  `providers.py` or `rail.py` mid-build.
  ⚠️ **THIS BULLET USED TO SAY the stale-code guard exits the engine and the
  supervisor restarts it, and that "IS the deploy path". IT IS NOT — corrected
  3 Aug 2026 after it cost an hour.** `_code_changed()` is checked ONLY at the top
  of the outer acquire loop, so **a claimed episode never reaches it** — building or
  flagged. A fix landed at 09:10; the process kept the broken code in memory until a
  manual restart at 10:08, and clearing the flag just re-ran the bug.
  **Until E11 lands: a mid-episode fix needs a MANUAL restart**, and the safe window
  is while the episode is FLAGGED — nothing is in flight then. Confirm the new
  process from the LOG (`engine up — … pid=`), never from having issued a start.
- Build principles: `G:\My Drive\Planning\Principles.md` (simple, small, real,
  one-source-of-truth, well-documented).

## 🔍 THE SEVEN FAULTS THAT KEEP COMING BACK
*(Named here because each recurred AFTER being written down somewhere weaker.
Full evidence in the memory files; these seven lines are the whole of it.)*

0a. **AN ID IS A PROMISE. A NAME IS A GUESS.**
   **And a name that is unique today is not unique at 300 episodes.** When a system
   hands you an id, STORE IT AT THE MOMENT IT EXISTS — never rediscover the thing later
   by matching its name.
   **Three symptoms of the one habit, all found in a week:**
   - **E18** — `episode_dir()` globs `PP-EP{n}*`, so **`PP-EP1*` also matches `PP-EP10`**
     and `PP-EP9*` matches `PP-EP98`. It made two outro audits confidently wrong.
   - **E20** — a **paid** HeyGen render was found by matching its *title*, because the
     rail never recorded the `video_id` of the thing it bought.
   - **board bug 5** — an episode cannot go backwards, the same shape.
   ⚠️ **"Part 1 / Part 2 / Part 3" of the same article are already coming.** Titles are
   about to stop being unique, and the failure will look like a wrong episode rather
   than a missing one.

0. **NEVER ASK A PERSON FOR SOMETHING THE RAIL ALREADY KNOWS.** *(Numbered zero because
   it comes before the others: it is about where you REACH.)*
   **Three times on 4 Aug alone, all the same shape** — reported "EP15 right now" from
   memory instead of reading the rail; let Jodie retype a hook and byline that were
   already written, because they went into a draft and not into the board (B7); asked
   whether Gordon's render had started when **`render_started_at` is a column**, set
   twelve hours earlier.
   **Every time the reach was toward the HUMAN rather than the SOURCE OF TRUTH.**
   ⚖️ **It is the exact inverse of Bundle F.** That one says *put the question where the
   person is standing*; this one says *do not ask at all if you can look*. **Same root:
   the machine holds something and the person is asked for it anyway.**

1. **ASSERT THE ARTEFACT, NOT THE THING THAT REPORTS ON IT.** An exit code, a
   call count, a code path, a cached read and your memory of what happened are
   all proxies. Ask what a human actually RECEIVES, and check that.
   *A guard that greps for a string can be satisfied by a comment.*
   > ### 🔴 A FILE THAT IS THE RIGHT LENGTH IS NOT THE RIGHT FILE.
   > **Duration is METADATA. Byte count is the truth — and the server gives it to you.**
   > *EP15, 4 Aug 2026:* HeyGen reported **114,395,315 bytes**; **78,947,138** landed.
   > `ffprobe` reported the right duration anyway, because an mp4 written with
   > `faststart` carries `moov` at the FRONT — **the container announces the full
   > intended length even when the tail never arrived.** Gordon stopped mid-word at 9:10
   > of a "13:31" file. Every other check passed.
   > ⚠️ **AND THE 35 MB GAP HAD ALREADY BEEN SEEN AND TALKED AWAY.** I noticed it, said
   > it worried me, then explained it as re-encoding *because the duration matched* —
   > a plausible cause, accepted without evidence, which is fault #6 pointed at a size
   > discrepancy. **An observation you explain away is worse than one you never made:
   > it leaves you confident.** *(Two hours and a near-miss re-render of a video that
   > was already complete and paid for.)*
   > **Verify a download against the byte count the server stated. Exactly. Not "about
   > right", not "the duration matches".**
2. **ONE SOURCE OF TRUTH, OR IT DRIFTS.** Four times a value lived in two places
   and the fix reached one reader. When two things must agree, make the shared
   value DATA that both read — and add the check that compares them.
3. **ANYTHING THAT WAITS MUST SAY IT IS WAITING.** Silence and death look
   identical. Emit a heartbeat, `flush=True`, record the START of work and not
   only its finish, and say who it is waiting on.
4. **"ALL GREEN" MEANS NOTHING UNLESS THE SUITE COVERS WHAT YOU CHANGED.**
   Before reporting a fix as proven, **name the specific case that proves it.**
   If you cannot name one, **say so** instead of quoting a total.
   *This is the mechanism by which fault #1 gets past someone who is being careful:
   the artefact you assert becomes the PASS COUNT, and a pass count is a proxy like
   any other.* **A green suite that never names the thing you changed is not evidence
   about it.**
   **What it cost, 3 Aug 2026:** `step_audit_inputs` was wired to
   `providers.assert_standing_assets()` while `engine.py` imports only names from
   `providers` — a guaranteed `NameError` on first real execution. It was reported to
   Jodie as fix #1 of the round, "9/9 green". **`test_bundle_a.py` never mentioned
   `assert_standing_assets` at all** — its nine cases were the midroll chip, the credit
   ceiling, the copy button and the title preview. **EP15 was dead in the water for
   22 minutes and retried three times**, on a line added that morning and reported as
   proven. Guarded now by `engine/test_step_call_sites.py` — static unbound-name audit
   across `engine.py` and `providers.py`, plus the real dispatch actually reaching the
   call.
5. **A DERIVED ARTEFACT INHERITS THE FAULT WITHOUT INHERITING THE BYTES.**
   When you quarantine a bad artefact, ask **what was BUILT from it**, not only what
   EQUALS it. **Chasing copies finds copies; it does not find children.**
   *EP15, 4 Aug 2026:* two cover heroes were rejected and every byte-identical copy was
   hunted down by hashing the whole episode folder — **nine found, all quarantined,
   scan clean.** But `ebook/cover.png` had been **composed** from the rejected hero with
   the title set over it, so **it hashed differently and the copy-scan could not see
   it.** It would have shipped as the e-book cover. Found only by asking separately
   which downstream artefacts had *consumed* the bad one.
   **The check is a dependency question, not an equality question:** list what the step
   PRODUCED, not what matches. Same shape as fault #1 — the hash was a proxy for
   "contaminated", and equality is not contamination.
   > **THE METHOD: take the output list from the CODE THAT WRITES. Never from the places
   > you can think of.** Read the function, list every path it writes, quarantine those.
   > **That is the FIRST move, not the recovery.**
   ⚠️ **AND A RULE YOU WROTE THIS MORNING IS NOT A RULE YOU HAVE.** This rule was
   written at 08:00 on 4 Aug and **breached twice in one operation the same evening** —
   paths guessed, not read. `overlay/export/ebook-cover.png`, three megabytes, built
   from the rejected hero, was found **by accident**. Reading `render_ebook_cover()` and
   taking its actual three-path output list took under a minute and would have found it
   first time.
   > ### 🔴 THE OTHER HALF: QUARANTINING A CONTAMINATED ARTEFACT LEAVES A HOLE, AND THE
   > ### HOLE MUST BE REFILLED, NOT JUST LEFT.
   > **Everything you removed was there because something NEEDED it.**
   > *EP15:* nine files were quarantined **correctly** — and nothing re-staged
   > `overlay/export/title-hero.png` from the new pick, so `ep15-title.html` re-rendered
   > **onto flat black** and the board asked Jodie to judge the hero crop of a card with
   > no hero on it. **A clean-up is only finished when every consumer has been given
   > back what it needs.** List the consumers, then refill, then look.
   ⚠️ **AND THE STRUCTURAL GAP IT EXPOSED:** `assert_standing_assets()` covers the
   STANDING pages — warranty, end card, midroll chip. It does **not** cover the
   episode's own **staged inputs** (title hero, thumbnail hero), which is exactly why
   this reached a render. Same class as the midroll chip, which A2b existed to stop.
6. **A WRONG CAUSE IS WORSE THAN NO CAUSE, BECAUSE THE OPERATOR'S NEXT ACTION APPEARS
   TO FIX IT.** **OBSERVE, NEVER SPECULATE.** A halt may say what it saw and what it
   could not do. It may NOT name a cause it has not established — *"this is not a
   missing file, not a stale template, the content is simply too long"* — and it must
   never ask a human to decide something on that basis.
   *EP15, 4 Aug 2026:* `cards_render` flagged with exactly that wording and **printed
   its own disproof underneath** — `Page.goto: Timeout 30000ms exceeded`. **The page
   never opened, so nothing was ever measured.** The real cause was the Google Fonts
   CDN hanging. *(Proved after: the stylesheet fetches in 0.4s, the page loads in 5.8s,
   and a deliberately BLOCKED CDN fails in 0.0s — only a HANGING one burns 30s.)*
   **Why it is worse than silence:** had Jodie shortened those words, the retry would
   have succeeded — **because the CDN came back, not because of anything she did** — and
   she would have learned a superstition. *A flag that guesses does not mislead once; it
   manufactures false evidence that the operator's action worked, and that lesson
   persists.*
   Also: **no raw stack traces in the operator's box.** Unreadable for Jodie,
   frightening for Hugh, in the one place a person most needs plain English.
   > ## 🔴 A HALT IS ONLY CLEARED WHEN THE PERSON IN FRONT OF IT CAN ACT WITHOUT
   > ## KNOWING HOW THE MACHINE WORKS.
   > **THE PICTURE · THE QUESTION · THE BUTTONS. NOTHING ELSE.** No paths, no
   > filenames, no JSON, no URLs as text, no other episodes, no explanation of the
   > parts you are NOT asking about. **If a sentence only makes sense to someone who
   > has read the repo, it belongs in the RUN LOG, not the flag** — different readers,
   > and the same text cannot serve both. Full rule: `docs/PP-operator-box-rule.md`.
   > *EP15's title-card flag asked a GOOD question — "are the horses framed well?" —
   > wrapped in a storage URL, a file path, a JSON fragment, another episode's history
   > and a paragraph about a decision nobody had queried. **We fixed that card's
   > PICTURE that morning and never read the WORDS printed beside it.***
   > **THE TEMPLATE — the right shape, from the same build an hour later:**
   > *"Card C12 has no clip in overlay/clips: expected exactly one file matching
   > `*c12*.mp4`, found 0. Most likely C12 is marked `block:"bespoke"` and its page has
   > not been hand-authored yet — bespoke cards are never generated, by design.
   > Otherwise the page is named so it does not match, or it failed to render.
   > **Retrying will not fix any of those.**"*
   > **SAY WHAT YOU SAW · LIST WHAT IT COULD BE, ASSERTING NONE · SAY PLAINLY WHETHER A
   > RETRY HELPS.** When board bug 7 is fixed, this message is the model.
   ⚠️ **AND A SYMPTOM THAT TWO CAUSES SHARE IS NOT EVIDENCE FOR EITHER.** On 4 Aug two
   different failures produced the same-looking Playwright timeout — a `goto` hanging on
   the font CDN, and a `wait_for_function` on a `ppDuration` the page never defined —
   **and I merged them**, blaming the CDN for both. The second was never the fonts:
   `render_card.py` waits for `ppDuration` FIRST. *Separate the causes before naming
   one, or you will fix the wrong thing and believe you fixed the right one.*

## ⚖️ A GUARD PREVENTS RECURRENCE — IT DOES NOT OBLIGE US TO GO BACK
**(Jodie, 4 Aug 2026.)** *"Jodie is not actually going to go back and change any of the
previous videos or e-books as Hugh has approved them."*

> ### FOUND RETROSPECTIVELY DOES NOT MEAN FIXED RETROSPECTIVELY.

When a new check finds an old fault in published work, the check's job is **the next
episode**. Published episodes are approved, live, and closed. **Log the finding, name it
plainly, and move on** — do not propose a re-render, a re-cut or a backfill.

⚠️ **THE RISK THIS GUARDS AGAINST IS REAL AND IT IS US.** Eight checks were added in a
single day. *A machine that spends more effort proving itself correct than making
episodes has stopped being a studio.* Every guard must earn its place against the next
episode, never against the archive.

*Same family as the closed e-book-link ruling: fix it FORWARD.*

## 🚫 COMMAND HYGIENE — THE ONE RULE
**(Jodie, 28 Jul 2026. A HARD RULE, not a preference. Replaces the earlier
version, which was a growing LIST of banned shapes — see "why one rule" below.)**

> ### EVERY Bash command must be dead simple:
> ### ONE tool · LITERAL absolute paths · NO variables · NO chaining · NO quoting tricks.
> ### Anything more complicated goes in a `.py` file and is run as a file.

**WHY IT MATTERS TO JODIE, and why "I'll be careful" is not good enough:** when
the harness cannot cleanly parse a command it flags it — *"expansion
obfuscation"*, *"newline followed by #"* — and **withholds the "don't ask again"
button.** The prompt is then **UNAPPROVABLE**: the identical shape asks her
again, and again, forever, and **there is no action she can take to make it
stop.** Every one of these I type is a permanent tax on her attention, not a
one-off. She is the operator and she runs nothing herself, so a prompt is pure
friction for her — never a safety net she asked for.

**WHY ONE RULE AND NOT A LIST.** The first version of this section banned
multi-line `python -c`, heredocs, nested quotes and braces. It said nothing
about `cd` chained to a write, or shell variables — **and those two are exactly
what kept prompting her all afternoon.** A list only ever bans the shapes
someone already got wrong; the next new shape sails straight through. So the
rule is now about what a command may BE, not about what it may not contain.

**AND IT IS HERE BECAUSE A MEMORY DID NOT HOLD.** This started as the
`command-hygiene-for-permissions` memory and was breached twice within the hour,
under build momentum. A memory surfaces when something makes it relevant;
CLAUDE.md loads every session before anything else, and momentum cannot skip it.

### The six classes that broke it today — all of these go in a file
| # | Shape | Example of what NOT to type |
|---|---|---|
| 1 | **Multi-line `python -c`** | `python -c "` … newline … `"` |
| 2 | **Heredoc** | `python - <<'PY'` … `PY` |
| 3 | **Shell variables** | `SP="C:/…/scratchpad"` then `python "$SP/x.py"` |
| 4 | **Chaining** | `cd repo && rm -rf "$D" && mkdir -p "$D" && python x.py` |
| 5 | **Loops** | `for t in test_*.py; do python $t; done` |
| 6 | **Quoting / expansion tricks** | quotes inside quotes inside quotes · `echo "exit=$?"` · `$(…)` round a quoted block |

**The replacement for every one of them is the same:** write the logic to a `.py`
file in the session scratchpad, then run `python <literal absolute path>`. That
command is simple, savable, reviewable, and re-runnable — and it leaves a record
of what was actually done.

### Before running ANY Bash command, ask
1. More than one tool invocation? → **file.**
2. Any `$`, `&&`, `;`, `|`, `<<`, `$(`, backtick, or a `for`/`while`? → **file.**
3. A path that is not a plain literal? → **file.**
4. Longer than about one screen line? → **file.**
5. Otherwise: one command, literal arguments. Good — run it.

**Prefer the Read / Glob / Grep / Edit tools over shelling out at all** — they
never prompt, and Glob in particular cannot delete, which is why `find` came off
the allow-list on 28 Jul 2026 (prefix matching cannot exclude `find … -delete`).

*Done right today: `clear_ep13_wrong_article.py`, `create_ep13_row.py`,
`update_ep13_row.py`, `verify_ep13_gate.py`, `rerun_check.py` — each one a file,
each one a clean `python <path>` call, each one a record of what it did.*

## Working here
- Commit small and focused; push to `main` (Pages deploys from it).
- `python engine/engine.py run --mock --watch` exercises the engine safely
  (no credits). `cleanup-mock` when done.
