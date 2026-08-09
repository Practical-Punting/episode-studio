# ENGINE BACKLOG — E1…E28, and what is closed

**Moved out of `session-checkpoint.md` on 6 August 2026, verbatim.** It had grown to
1,607 lines because a BACKLOG was living inside a file whose job is to be a SNAPSHOT —
and it sat in a machine-local memory silo that two of the three silos cannot see, while
the repo is the studio's stated one home.

> ## READ THE WARNING AT THE TOP OF THE LIST BEFORE YOU READ THE LIST.
> **A list of everything anyone noticed is not a plan.** Take an item off it against a
> REAL FAULT IN A REAL EPISODE, never because the list is long or the item is cheap.

**Where the other things live:** current state → `session-checkpoint.md` · where things
stand and today's order → `HANDOVER.md` · the rules → `PP-STANDARDS.md` · what was
decided and why → `PP-RULINGS.md` · the faults with evidence → `CLAUDE.md`.

*Nothing below was rewritten in the move. Status markers (✅ landed, ⚰️ superseded) are
as they were written; check them against git before acting on one.*

---

# 🆕 LOGGED 9 AUG 2026

## 🔴 THE BOARD ASKS FOR WORDS THE MACHINE STILL OWES **(Jodie, 9 Aug 2026, on EP19)**
> **A queued episode with NO SCRIPT YET shows the "YOUR TURN — WORDS" chip and the
> Words Gate.** Jodie is being told to act at the exact moment the MACHINE owes her the
> script — the drafting pass has not run, or has run and is still writing.

**It should read "Writing the script… no action needed yet" until a script exists, and
flip to YOUR TURN — WORDS the moment one does.**

**Why it matters more than a wrong label:** this is the *Job-5 fault* — a YOUR TURN chip
with nothing to do. A queue that cries turn-taking when there is no turn to take is a
queue she stops believing, and the one time it means it she will scroll past. It also
sends her looking for a Doc that does not exist yet.

**The state to key on already exists on the row** — `script_snapshot` (and
`script_doc_url` for the older shape). The gate is asking `title_approved && script_read`
(`app.js` ~line 68 / ~529) and never asking whether there is anything to READ.
📌 **Derive it, do not add a status.** A fourth state in the 10-status contract to say
"the machine is writing" would be a second source of truth about the same fact; the
presence of a script is the fact.

⚠️ **AND SAY WHICH MACHINE STEP IS OWING**, or the new message is only a nicer lie: if
the drafting pass has HALTED (no capture — see the root cause below), "Writing the
script…" is false. The run log knows; the board does not. **A19 applies: that halt is
the studio's, not the operator's**, so the card should say *"the studio is preparing
this one"* rather than badge her with a job she cannot do.

## 🔴 NOTHING TURNS A `source_url` INTO A CAPTURE **(found chasing EP19, 9 Aug 2026)**
EP19 sat `queued` for six minutes with a perfectly good `source_url` on the row and the
engine idle-but-healthy. The drafting pass ran on time, reported plainly *"The article
for this episode hasn't been captured yet, so there is nothing to write the script
from"*, and stopped — correctly.

**The hands-off chain is `source_url` → [MISSING] → drafting pass → fidelity gate →
seat.** `assert_capture_for_script` is a PRECONDITION; nothing CREATES the capture.
`providers.py` says so out loud: *"nobody holding a browser can capture an article"* —
so it is the studio's step, by design (`DESIGN-the-pre-claim-drafting-pass.md` §4), and
on EP18 it was a scratch script run by hand.

**For "EP19 with zero human pastes" this is THE remaining hole.** Automating it is a
design decision, not a tidy-up: the capture becomes the article of record that the
fidelity gate, `check_trace` and the e-book body are compared against forever, and
building EP19's by hand tonight needed four judgements a naive fetch would have got
wrong — paragraph breaks that are `<br><br>`, sub-headings inline in `<b>`, a real
`<table>` that must stay a table (the EP16 lesson), and where the article ends before
the site furniture begins. **Jodie's call, with those costs on the table.**

---

# 📥 CARRIED IN WITH THE MOVE — two live items that were elsewhere in the checkpoint

## 🔴 THE RUN LOG SHOULD NOT DEPEND ON SOMEBODY REMEMBERING **(Jodie, 5 Aug 2026)**
> **Her question: *"do we need a fix for the fact that the run log did not just
> automatically happen?"*** EP16's exists because Cowork asked for it. **Twice.**

> ## THE SPLIT: **THE FACTS SHOULD BE AUTOMATIC. THE FINDINGS SHOULD NOT.**

**The engine already knows nine tenths of a run log** — every step with its timings, every
flag with its exact text, every retry, every spend, every byte count — **and writes all of
it to `engine-<date>.log`, where nobody assembles it.**
**THE FIX: the engine emits a factual run-log SKELETON per episode, as it goes, with the
halts in it.** Writing the log then stops being *"remember to write a document"* and
becomes *"add the findings to the file that is already there"*.
> ⭐ **SELF-LIMITING, which is why it will not become bureaucracy:** a boring episode
> produces a boring file **for free** and nobody writes anything.

**RANKED BELOW THE CARD-PIPELINE WORK — it does not make a wrong video.** But it
**compounds at 300 episodes**, and it is **the mechanism by which we learn anything at
all**: every rule in `PP-STANDARDS.md` and every fault in `CLAUDE.md` came out of somebody
writing down what happened, and that has been voluntary every single time.
*(EP17's run log was written by hand again, 6 Aug. Third episode running.)*

## ⚠️ `mock-episode` CREATES A TICKET THE REAL ENGINE WILL CLAIM
`claim_next()` does not filter on `created_by`, so a live `run --watch` engine picks up a
mock ticket. It flagged harmlessly when found — the mock Doc URL 404s at `script_sync`,
**before anything can spend** — but **a mock ticket with a readable Doc would walk into the
paid steps.** **One filter on `created_by` in `claim_next`.** Small; not urgent.

---

# 📋 THE LIST — everything noticed, NOT a plan

> ## ⚠️ READ THIS BEFORE YOU READ THE LIST. Jodie, 4 Aug 2026: **"We had it working!"**
> **A list of everything anyone noticed, stacked up as if it were all equally urgent, is
> not a plan.** I produced a 12–14 day pre-EP16 plan off this list and she cut it to
> ~3.5 days by asking one question: *which of these actually caused a fault?*
> **EP15 halted nine times from THREE causes** — and the three fixes are landed.
> **Everything still on this list waits for the day HUGH operates, and that day is not
> this month.** Take items off it against a real fault in a real episode, never because
> the list is long. *A machine that spends more effort proving itself correct than making
> episodes has stopped being a studio.*

**Bundle C — the create brain.** Kills stops 1, 3, 10, 11. Includes setting the script
Doc's sharing at creation (stop 2's real fix — **no Drive service account: a new secret
on a public repo is not a trade worth making**).

**Bundle E — the guards:**
- 🔴🔴🔴 **E28 — A MANUAL RAIL EDIT CAN BE SILENTLY OVERWRITTEN BY THE RUNNING ENGINE,
  AND BOARD BUG 5 MOVES UP BECAUSE OF IT.** *(EP15, 4 Aug 2026.)*
  `assemble_passB` and `self_qc` were removed from `build_state.steps` to force a
  rebuild after C10's card was fixed. **The read-back showed them gone.** The engine
  held a live lease, its own `ctx.save()` wrote the old state back, and **nothing
  anywhere said so**. It then ran `self_qc` against the **already-superseded** video,
  marked every remaining step done, and parked EP15 at **`awaiting_approval` with a
  stale film**. *Only comparing `FINAL.mp4`'s mtime (18:32) against C10's clip (19:06)
  caught it.*
  > **THE READ-BACK WAS A PROXY. The artefact is the file on disk.**
  **The root cause is board bug 5: there is NO SAFE WAY TO SEND AN EPISODE BACKWARDS.**
  Every attempt is a hand-edit racing a live writer. **Tonight it stopped being a
  nuisance and became the thing that nearly walked a stale video into Jodie's approval
  gate.** *Board bug 5 moves up the list.*
  **Interim discipline until it is fixed:** refuse to write while a lease is live —
  check `claimed_by` and `lease_until` first — and **prove the effect with a NEW OUTPUT
  FILE whose mtime is later than the input you changed**, never with a status field.
  > ### 🔴 THE DEAD ZONE — the mechanism, found the same night
  > There are **exactly two** ways an episode re-enters the engine:
  > `claim_next()` → `status=eq.queued` · `reclaim_stale()` → `claimed_by=not.is.null`
  > **AND A WORKING STATUS WITH NO OWNER MATCHES NEITHER.** EP15 sat at `assembling`
  > with `claimed_by: NULL` — **unreachable by anything, forever.** The engine was alive
  > (pid 76064) and had logged nothing for 48 minutes; the episode was simply invisible
  > to it. *My own reset created that state, by clearing steps and status without
  > realising the engine had released ownership when it parked at `awaiting_approval`.*
  > **RECOVERY, using the engine's OWN crash path rather than an invented one:** set
  > `claimed_by` to a name that is not the live worker and `lease_until` to the past —
  > which is what the episode factually is, one whose worker went away mid-assembly —
  > and `reclaim_stale()` takes it back. *It worked in under a minute:
  > `reclaimed a stale-leased episode PP-EP15 at assembling`.*
  > **THE FIX BELONGS IN THE ENGINE:** an owner-less episode in a WORKING status is
  > always a fault, and the idle loop should adopt it rather than ignore it.
- 🔴 **E19c — A WATCHER THAT WAITS ON AN OUTPUT MUST ALSO WATCH THE THING THAT MAKES IT.**
  *(Third sighting of E19's other half, and the sharpest.)* The rebuild watcher was
  correctly waiting on `FINAL.mp4`'s mtime — **and would have waited all night**, because
  nothing was producing it. **A dead engine and a slow one look identical from the file
  system.** Watch the producer (claim, heartbeat, current step) alongside the artefact,
  and say plainly when the producer is not running.
- 🔴 **E23c — THE STALE LABEL BECAME A SAFETY SURFACE.** `progress_step` read
  **"Waiting on you — four approvals"** while the episode was mid-rebuild with 16 of 18
  steps done. **The first two stale labels made Jodie think the machine had frozen. This
  one invited her to APPROVE A VIDEO WE KNEW WAS THE WRONG CUT.** *The label is not
  cosmetic.* Derive it, never store it — and never leave an approval prompt showing for
  an episode that is building.
- ✅ **E26 — LANDED 4 Aug 2026, `04da5fc`.** `engine/preflight_episode_json.py`, called
  from `step_audit_inputs`. **Keys+types catch five of the seven; a REFERENTIAL pass
  catches the `END` id and a SHAPE pass catches card-beats-on-WIDE.** Being QUIET was as
  much work as the diff: `_`-keys are never conventions, a missing BLOCK is separated
  from a missing leaf, blockers halt and the rest is merely named. EP15-as-shipped and
  EP14-judged-by-the-others both come back with **zero blockers**.
  ⚠️ **The shape pass asserts NO RATIO** — the framing is settled and a high WIDE count
  is not a fault; only ZERO is unlike every episode.
  📋 *16 tests, one per halt EP15 actually took. Two false positives were caught by the
  does-not-cry-wolf cases: an OPTIONAL field is not a type mismatch, and an empty list
  is a list of anything. Either would have fired on every episode from now on.*
  **Original entry kept below — it is the case that justified it.**
- 🔴🔴🔴 **E26 — NOTHING VALIDATES `episode.json`.** *(EP15, 4 Aug 2026.)*
  > ## SEVEN HALTS. ONE FILE. ONE EPISODE.
  `default_hold` · the `ask` TYPE · card-beats-on-WIDE · the `END` id ·
  `build.standing` · `midroll.dur` · `thumbnail.l1`
  **Every one found by running into it**, eighteen steps deep, hours apart, each costing
  a flag Jodie had to clear. **Every one a convention that EP11-EP14 all followed and
  that nothing anywhere states.** This is no longer an argument FOR the pre-flight — it
  is the whole case.
  **THE PRE-FLIGHT: diff the episode's `episode.json` against the LAST EPISODE THAT
  BUILT CLEANLY — keys, TYPES, and SHAPE — before the build starts.** *"Every previous
  episode put some card beats on WIDE; this one puts none"* is a sentence a diff could
  have produced before a credit was spent.
  ⚠️ **USE TWO REFERENCE EPISODES, NOT ONE.** A rule inferred from a single sample was
  wrong on all three axes an hour earlier (panel-push cells). A key is only a convention
  if BOTH references carry it.
  ✅ **DONE ONCE BY HAND ON 4 Aug** rather than discovering the eighth at the last step:
  17 keys missing against EP13 **and** EP14. Five were real — the whole `thumbnail`
  block — and filled. **Twelve are `build.*` tuning values whose CODE DEFAULTS equal
  what EP13/EP14 set**, and Pass A, Pass B and QC had already succeeded without them, so
  they were deliberately NOT filled: *a value you do not understand is not made safer by
  copying it.*
- 🔴🔴🔴 **E27 — NOTHING MEASURES A CARD AT THE SIZE IT IS ACTUALLY SHOWN. EP16.**
  *(EP15, 4 Aug 2026 — found by looking at a still, by nothing else.)*
  A **panel-push** card is chroma-keyed, **scaled to 810 wide (42%)** and dropped at
  `x=36, y=312`. `card_check` and `self_qc` **both measure the page at 1920**. EP15's C10
  used a **4-across slate**, giving each cell ~155px and body text at roughly **9px** —
  and it passed **17/17 plus QC** as a card nobody could read.
  > ## PANEL-PUSH BODY TEXT MUST REMAIN READABLE AT ITS COMPOSITED SCALE.
  **THE CHECK: render the card at 810 wide, measure the SMALLEST rendered text, fail
  below the threshold.** ⚠️ *A black-pixel test would have PASSED this — the pixels are
  not black, they are illegible.*
  **THE THRESHOLD: 11px, and here is exactly where it came from.** EP13 C8 bottoms out
  at ~14px composited; EP14 C5 at ~11px; both ship legibly. EP15 C10 at ~9px does not.
  **11px is the smallest text any APPROVED episode has actually used** — empirical, and
  it passes EP13/EP14 while failing EP15, which is the only test a threshold must meet.
  ⚠️⚠️ **BUT 11 IS NOT SACRED. It is computed from the CSS and a 0.42 scale factor, NOT
  read off rendered pixels. When E27 is built it MEASURES THE REAL THING, and if the
  number moves, the number moves. THE COMMITMENT IS TO THE METHOD, NOT THE VALUE.**
  🚫 **DO NOT WRITE "THREE CELLS, TWO LINES" INTO A STANDARD.** That was inferred from
  ONE sample and **the second sample killed it**: EP14 ships TWO cells with THREE-line
  values AND sub-lines. A count is a proxy; readability is the constraint. Cell guidance
  belongs in authoring notes as help for passing the check — never as the rule.
  ✅ *This makes the seventh convention the FIRST that cannot be silently forgotten.*
- ✅ **E22 — LANDED 4 Aug 2026, `04da5fc`.** `RealProvider._download_exact()`: read the
  stated size, compare after, refuse to promote, **name both numbers in plain English**.
  **Applied to the PAID Higgsfield clips and heroes too** — found by asking whether the
  fault had SIBLINGS rather than waiting for it to bite twice.
  🔬 **The 109 MiB boundary is STILL UNEXPLAINED and stays that way** — four re-pulls
  landed on exactly 114,294,784 bytes. The length check makes it LOUD, not understood.
  **Original entry kept below.**
- 🔴🔴🔴 **E22 — `_heygen_fetch` ACCEPTED A TRUNCATED DOWNLOAD AS THE MASTER.**
  *(EP15, 4 Aug 2026 — the whole two-hour false trail.)*
  ```python
  with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
      shutil.copyfileobj(r, f)      # no length check, EOF looks like success
  tmp.rename(master)                # promoted to THE MASTER regardless
  ```
  `urlopen` + `copyfileobj` **never compares against `Content-Length`.** A connection
  that drops mid-transfer ends the copy without raising, and the short file is renamed
  to `presenter-master.mp4`. **That is how 78,947,138 bytes became "the master" while
  the server had stated 114,395,315.**
  **THE FIX: read `Content-Length` before the copy, compare after, and refuse to rename
  on a mismatch** — naming both numbers. Nothing else changes.
  ### 🔬 THE 109 MiB BOUNDARY — logged as unexplained, on purpose
  Four separate re-pulls landed at **exactly 114,294,784 bytes = 109 MiB, to the byte**.
  The full file is 109.0959 MiB — it crosses that line by only **100,531 bytes**.
  **Four times on a round binary boundary is not a flaky line. Something in the chain
  has a fixed ceiling and I DO NOT KNOW WHERE.**
  *Best hypothesis, NOT established:* the re-pull used a **1 MiB read buffer**, so the
  transfer ended after the last WHOLE chunk and the final partial one was lost — which
  would make the boundary an artefact of my buffer size rather than a real cap. But
  attempt 7 succeeded with identical code, so it is not deterministic. **Candidates not
  ruled out: the CDN, the G: Drive virtual filesystem, Windows, or the client.**
  ⚠️ **At 300 episodes with bigger files this bites again — and next time there may be
  no stated byte count to catch it.** Whatever the cause, the LENGTH CHECK above makes
  it loud instead of silent.
- 🔴 **E24 — THE CODE'S OWN DEFAULTS CONTRADICT EACH OTHER, AND THE HALT CALLS IT
  "JODIE'S CALL".** *(EP15, 4 Aug 2026 — `derive_card_timings.py`.)*
  ```
  163:  return float(build.get("default_hold",   8.0))
  198:  min_hold  = float(build.get("min_card_hold", 10.0))
  ```
  **The default hold is BELOW the minimum hold, three lines apart in one file.** With
  nothing set in `episode.json`, EVERY non-hero card fails by construction — and the
  halt then asks a human to settle it, once per card. EP15 produced **seven identical
  "Jodie's call" lines to the decimal**, which is what a single wrong constant looks
  like when it is reported per-item.
  **EP13 and EP14 both SET `default_hold: 10.0` explicitly, so the broken default was
  never exercised.** EP15 was the first episode written without it. *Fault #2 (one
  source of truth) plus fault #0 (the machine asking a person for what it already
  knows).*
  **FIX: the code default must equal the floor, and a value that cannot satisfy its own
  check is a bug, never a question.**
- 🔴 **E25 — THE `ask` GUARD CANNOT SEE A WRONG TYPE.** `build.midroll.ask` must be a
  **LIST of two anchor phrases** (EP13/EP14 both are). EP15 had a **string**, so
  `ask[0]`/`ask[1]` were the CHARACTERS `'I'` and `'f'` from *"If you've found…"* — and
  the halt reported *"ask phrase not found in the SRT ('I' -> ok, 'f' -> MISSING)"*.
  The guard is `if not ask or len(ask) < 2` — **any string of two or more characters
  passes it.** The check built to catch a MISSING ask is blind to a MIS-TYPED one.
  *(Not the fuzzy-matching fault of E21 — a different failure with a similar smell.)*
- 📣 **E23 (operator's box, with board bug 7) — THE CARD WAS WRONG FOR TWO HOURS IN
  FRONT OF THE OPERATOR.** While the master was being diagnosed, the board went on
  showing *"wrong take, wrong episode, or the words changed after the render"* — **three
  causes, none of them the real one** — beneath a picture of a title card **that was
  never broken**, with a button offering to declare it sorted. Fault #6 on the flag text,
  fault #0a-adjacent on the picture, and a button that would have recorded a lie.
- 🔴🔴🔴 **E21 — NOTHING CHECKED THAT GORDON SAID THE WHOLE SCRIPT. HIGHEST.**
  *(EP15, 4 Aug 2026. E19's other half, proven in the worst way.)*
  **The file was complete. The duration matched HeyGen's to 0.02s. Every automated
  check passed. And the episode was two-thirds of a video.**
  Gordon stops **mid-word** — *"…not taking full advantage of the standard fractional
  bet"* + *"s available…"* — at **9:10 of a 13:31 file**, in **beat 18 of 24**. Missing:
  the $124 worked example the episode is NAMED for, Table 1, the rails passage, the
  minimum-price rule, the drifter caveat, and **the entire outro including the
  responsible-gambling line.**
  **THE ASSERTION IS CHEAP AND DECISIVE: the master must contain the LAST WORDS of the
  script.** One transcription of the tail, one substring test. It would have caught this
  before a single downstream step ran.
  > ### ⚠️ AND IT MUST BE FUZZY, NOT EXACT — OR IT SHIPS BROKEN.
  > **Found by the check failing on the very first real use.** My own version reported
  > the responsible-gambling line ABSENT because Whisper heard **"never *bit* more than
  > you can afford to lose"**. The line was spoken; the test was too strict. That is
  > exactly the mishearing `align_to_script`'s own docstring warns about
  > (*"whisper misheard 'Here's a claim' as 'He's a client'"*).
  > **Match on a WINDOW of the last N words with a similarity threshold, never an exact
  > substring.** A guard that cries wolf gets switched off — and we would have shipped
  > this one strict.
  *Caught only because `align_to_script` refused at 62.9% against an 85% floor and
  removed `aligned.srt` rather than let interpolated timings through — that guard,
  built after EP13's cards ran ahead of the words, is the only reason this was not
  assembled into a finished video.*
  ### 🔬 THE DIAGNOSIS — measured, and it killed two theories
  | | |
  |---|---|
  | EP15 stopped at | **9,224 chars / 1,677 words**, mid-word |
  | **EP13 rendered COMPLETE at** | **12,042 chars / 2,194 words** |
  | **EP14 rendered COMPLETE at** | **10,846 chars / 1,960 words** |
  **A length cap at ~9,224 CANNOT EXIST** — two longer scripts rendered whole. And the
  paste was not truncated either: **the file is 811s, and the FULL 2,466-word script at
  its own 182 wpm predicts 813s.** HeyGen was handed everything, allocated the right
  duration, then **rendered audio for the first 68% and left 4m18s of silence.**
  **A rendering failure at HeyGen's end, not a limit and not an operator error.**
  ⚠️ **The API says NOTHING is wrong:** `status: completed`, `error: None`, no
  truncation flag on any of EP13/EP14/EP15. **The provider's own success field is a
  proxy** — [[assert-the-artefact]].
- 🔴 **E20 — THE RAIL DOES NOT RECORD THE ID OF THE THING IT PAID FOR.**
  EP15's `heygen_video_id` was **NULL** while a completed, paid render sat on HeyGen.
  `_heygen_fetch` (providers.py:1506) falls back to **listing 100 videos and matching on
  `heygen_name`**. It works today and it is a guess.
  **THE FIX IS TO SAVE THE ID AT THE MOMENT THE JOB IS CREATED**, not to find it
  afterwards. *(EP15's was written by hand on 4 Aug once found — safe, because exactly
  one code path reads it and a non-null value only skips the title search.)*
  ⚠️ **"Part 1 / Part 2 / Part 3" of the same article are coming, and at 300 episodes
  titles will collide.** The failure then is not "not found" — it is **the wrong
  episode's render**, silently.
  📋 **SWEEP AFTER EP15 SHIPS — where else do we match on a NAME when an id exists:**
  `_heygen_fetch`'s title match · `_clip()`'s glob `*c{n:02d}*.mp4` (a card whose page
  is renamed stops matching) · `_hero_paths` keying on filenames rather than the ledger ·
  `broll_registry_check`'s `broll-[a-z0-9-]+` regex over prose · `episode_dir()` (E18) ·
  `midroll_window`'s folder scan · the b-roll job map keyed on target NAME in
  `build_state.jobs`. **Log only for now; do not touch mid-build.**
  *Pattern named in CLAUDE.md as fault #0a: an id is a promise, a name is a guess.*
  ⚖️ **FOR THE RECORD, so nobody fixes the wrong thing: none of this is why the download
  is slow.** The URL works and the bytes are arriving. **The missing id bit the
  INVESTIGATION, not the transfer.**
- 🔴🔴 **E19 — TIME SPENT WAITING FOR A PERSON IS BEING COUNTED AS TIME SPENT WORKING.
  ONE fault, TWO symptoms. Before EP16.** *(Jodie, 4 Aug 2026.)*
  > **Any clock shown to an operator, or used to raise an alarm, must count ONLY time
  > the machine was actually working.**
  **Symptom 1 — the board's card, which Jodie is looking at now:**
  *"Working for 15 hr 6 min · render cooking 12 hr 38 min"* — **the HeyGen render took
  about twenty minutes.** The board is counting wall-clock since the episode was created
  at 18:04 the previous evening: **Jodie asleep, and the title-card flag waiting for her
  all morning.** *It is not wrong about the arithmetic. It is wrong about what it is
  measuring.*
  **Symptom 2 — my own watcher**, which fired
  *"BUDGET EXCEEDED — cards_render has run 31 min against a 30 min budget"* on a step
  that was **flagged and waiting for Jodie to look at the title card.** The watcher built
  to tell SLOW from DEAD invented a third case and got it wrong: **"waiting for a person"
  is neither.**
  **THE FIX, both places:** a step that is **flagged (`needs_look` true) is a human
  wait, whatever its budget says** — and so is a step whose budget is `None`. **Both must
  STOP THE CLOCK, not merely suppress the alarm.**
  ⚠️ **Not fixed mid-build on purpose:** restarting the watcher now leaves exactly the
  gap we agreed not to leave.
  📣 **And the same line is engine vocabulary in the operator's box** — *"render
  cooking 12 hr 38 min"*. **Hugh reads twelve hours of cooking and reasonably concludes
  something is broken.** Whatever that line becomes once it counts the right thing, it
  must say the plain version: what is happening now, and roughly how long it has
  actually been doing it. See `docs/PP-operator-box-rule.md`.
- 🟡 **E17 — EXTEND THE HEAD-OF-BUILD ASSERTION TO THE EPISODE'S OWN STAGED INPUTS.**
  ✅ **HALF-ANSWERED 4 Aug by `engine/check_page_images.py`**, which catches any staged
  image a PAGE references — including the title hero and the e-book cover — without
  anyone maintaining a list. **What it does NOT cover is an input nothing references from
  a page** (a b-roll clip, a music file). That remainder is E17.
  `assert_standing_assets()` covers the STANDING pages — warranty, end card, midroll
  chip. It does **NOT** cover per-episode staged inputs: **`overlay/export/title-hero.png`
  and `thumbnail/hero.png`.** *EP15, 4 Aug: a correct quarantine removed the title hero,
  nothing re-staged one from the new pick, and the title card RE-RENDERED ONTO FLAT
  BLACK — then the board asked Jodie to judge "whether the horses are framed well" on a
  card with no horses.* **Same class as the midroll chip, which A2b existed to stop:** a
  knowable absence discovered at render instead of at the head of the build.
- ⚠️ **E18 — `episode_dir()` STILL HAS THE GLOB FLAW IT WAS WRITTEN TO PREVENT.**
  `pp.glob(f"PP-EP{n}*")` — **`PP-EP1*` matches `PP-EP10`, `PP-EP9*` matches `PP-EP98`.**
  Single-digit episodes resolve to the WRONG FOLDER. Written 4 Aug for exactly this
  class of fault, and it is **the same flaw that made the first two outro audits wrong**.
  Fix: anchor on a zero-padded pattern, `^PP-EP(\d{2})(?:$|[-_])`. *Noted 4 Aug and
  deliberately left; it is live in `test_hand_steps.py`, `test_title_card.py` and
  `test_youtube_title.py`, all of which currently pass only because they use 13, 14, 15.*
- 🟡 **E16 — THE MECHANISM LANDED 4 Aug 2026, `04da5fc`. NOT YET PROVED, AND THE BOARD
  HALF IS DEFERRED ON PURPOSE.** `hero-jobs.json` is now keyed on
  `slot + sha256(prompt)[:12]`. Same prompt → same key, so the double-spend guard works
  exactly as before; changed prompt → a genuine create. **Nobody has to remember to
  clear a file, which is the only kind of fix that holds.**
  ⏳ **THE WITNESS FOR A SPENDING GUARD IS THE BALANCE MOVING, AND IT HAS NOT BEEN
  WATCHED.** Both directions need two real generations. **Watch it on EP16's covers, and
  do not call E16 proved until then** — on EP15 a status field, a fresh mtime, a byte
  count and a "completed" job all said the images were new, and only the unchanged
  balance said otherwise.
  📋 **Deferred:** the board must never re-offer a rejected artefact and must say so on
  the card. The prompt hash fixes the mechanism that failed; **the label matters the day
  somebody who is not Jodie is looking at that card.**
  **Original entry kept below.**
- 🔴🔴🔴 **E16 — A REJECTED ARTEFACT CAME BACK AND WAS OFFERED TO THE OPERATOR AS A
  CHOICE.** *(EP15, 3-4 Aug 2026. The worst fault of the build.)*
  Both cover heroes were looked at and **ruled unusable** — A carried a competitor's
  brand, B had the prompt's own instruction text rendered across the sky. Jodie approved
  regenerating both. The files were moved aside. **The engine re-downloaded the SAME two
  images, the board offered them again with nothing on the card to say they had been
  rejected, and Jodie picked one in good faith.** Her choice then propagated to
  `overlay/export/title-hero.png` and `ebook/cover-src/hero.png`.
  > **She made a decision on bad information and had no way to know.**
  **That is worse than the original prompt bug**, which only wasted credits.
  **THE MECHANISM, named — it is not `build_state`:** `docs/hero-jobs.json` is a
  DOUBLE-SPEND GUARD. `_generate_heroes` stores a Higgsfield `job_id` the instant it
  exists, then on re-run:
        if not rec.get("job_id"):  ...create...
        self._hf_download(rec["job_id"], path, key)
  With an id present it **never calls create** — it re-downloads that job's output.
  **DELETING THE PNGs CANNOT INVALIDATE A STORED JOB ID.** Moving the files aside was
  treated as sufficient and it was not. *(Proven by the balance: 75.22 unchanged. Two
  heroes cannot be generated for free.)*
  **WHAT HAS TO CHANGE:**
  1. **Rejection must be RECORDED, not implied by absence.** A rejected job id belongs
     in the ledger marked rejected, so the guard can tell "already paid for" from
     "already paid for AND no good".
  2. **The board must never re-offer an artefact that was rejected**, and must say so
     on the card if one is somehow still present.
  3. **A regeneration is only proven by the BALANCE MOVING.** A status field, a fresh
     mtime, a byte count and a "completed" job all said these were new. Only the
     unchanged balance and a byte-compare said otherwise. [[assert-the-artefact]]
- 🔴 **E14 — A BESPOKE CARD CARRIES A LAYOUT RISK AUTHORED CARDS DO NOT, AND IT IS
  CAUGHT AT THE WRONG END.** *(EP15, 4 Aug 2026.)*
  **The ONE card in EP15 that nothing generates is the ONE that failed the layout
  gate** — C12, the Table 1 card, with two collisions: the gain column under the logo
  chip, and the footer clipped through the panel floor. **That is not bad luck.**
  `author_cards.py` lays generated cards out to a template *known to fit*; a bespoke
  page gets the same CHECK with none of the FITTING. **That is the cost of "bespoke",
  and nobody priced it.**
  Both faults came from one line — `table{margin-top:auto}` in a flex column, which
  pushed the table and everything after it onto the panel's bottom edge.
  **THE FIX: bespoke cards need the same pre-flight the generated ones get, run at
  AUTHORING time, not at render time.** Finding this at `cards_render`, twelve hours
  into a build, is the wrong end of the pipeline — the cheapest moment to catch it is
  the moment the page is written.
  > ### 🔴 PROVEN TWICE ON THE SAME CARD, 4 Aug — and the second one is the argument.
  > **Halt 1, LAYOUT:** `table{margin-top:auto}` pushed the gain column under the logo
  > and the footer through the panel floor.
  > **Halt 2, WIRING:** the page never rendered a clip at all, because
  > `render_card.py` waits on `typeof window.ppDuration === 'number'` **before** it
  > waits for fonts — and a hand-authored page that does not load `pp-anim.js` and call
  > `ppInit()` never defines it. Every generated card gets that free from
  > `author_cards.py`. **A bespoke page gets NOTHING for free.**
  > **THE PRE-FLIGHT MUST CHECK BOTH: that the page FITS, and that it declares
  > `ppDuration`.** One check would have caught neither the second time.
  ⚠️ **AND THIS GETS MORE IMPORTANT, NOT LESS:** if the Table 1 transcription ruling
  goes the way it looks like going, **bespoke cards become commoner**, and every one
  of them is an unfitted page checked only after a render has been paid for.
- 🔴🔴 **E15 — SELF-HOST THE FONTS. HIGH, SMALL, AND IT REMOVES A DEPENDENCY RATHER
  THAN WORKING AROUND ONE.** *(Jodie, 4 Aug 2026.)*
  Card pages pull Anton and Barlow from `fonts.googleapis.com` **at render time**, so
  `cards_render` has an **undeclared internet dependency in the middle of the build**.
  **The studio cannot render a card offline, and it has now cost an evening.**
  **The fonts are standing assets exactly like the warranty slide and the midroll
  chip:** ship them in the repo, reference them locally, and *the entire class of
  failure disappears* — including E15b below, which only bites when the CDN is
  unreachable.
- 🔴 **E15b — `card_check` ASSERTS A PROXY, NOT THE ARTEFACT. It is fault #1.**
  It waits for `document.fonts.status === 'loaded'` — which resolves when pending loads
  **SETTLE, success OR failure**. So the check can measure in a **fallback face and
  pass**, while `render_card`, which uses the strict `document.fonts.check()`, refuses
  to run at all.
  > **The proxy is "fonts finished doing something". The artefact is "the shipping face
  > is in use."**
  On EP15's C12 headline: **896px in Anton against 1327px in the fallback — a 48%
  difference, on a check whose whole job is deciding whether text fits.**
  *EP15's 17/17 is sound only because the font happened to be cached — luck, not
  design; verified explicitly on 4 Aug before the number was quoted.*
  **Fix: `fonts.check()` against each declared family, and HALT rather than measure in
  a substitute** — the way `render_card` already does. [[assert-the-artefact]]
- 🔴🔴 **E12 — NEVER RETRY A SPENDING STEP WITHOUT CHECKING THE WORK ALREADY EXISTS.
  HIGH.** *(3 Aug 2026, EP15, and it nearly cost a second batch.)*
  `covers_ab` **generated both heroes, was charged for them, downloaded them to disk** —
  and then failed in `_publish_asset` (the Supabase upload). The board reported a clean
  *"Generating the two cover heroes failed 3 times"* **and offered a retry.** Taking it
  would have spent another 4 credits for images already sitting in `ebook/cover-src/`.
  Balance measured: **131.72 → 75.22 = 56.5 exactly** = 52.5 (7 clips) + 4.0 (2 heroes).
  **The full batch was billed. Nothing was refunded. Three retries could burn a batch.**
  **THE RULE: before retrying anything that spends, check whether the work already
  exists at the provider.** Higgsfield's generation history is authoritative and cheap
  to read. **And the board must never offer a bare "retry" on a step that spends — it
  has to say what has already been paid for.**
  *Same shape as the stale-code guard: recovery that costs nothing when it works and
  real money when it doesn't.*
  ✅ **The step already handles this correctly** — `make_covers_ab` skips generation for
  any hero already on disk (*"staged ones are used as-is"*). The gap is entirely in what
  the BOARD tells a human to do.
- 🔴 **E13 — A PROMPT DESCRIBES THE PICTURE; IT NEVER INSTRUCTS THE GENERATOR.**
  EP15's `hero_b_prompt` opened *"…DELIBERATELY DIFFERENT from A: …"* and the model
  **rendered that phrase into the image** as a white headline across the top third.
  Hero A separately came back carrying a **real bookmaker's brand, legible twice** —
  unusable on a PP cover. **Every automated check passed both**: status completed,
  1696x2528, 2:3, 6MB, two genuinely different files. **Only looking caught it.**
  Guard: reject prompts containing meta-instruction (`DIFFERENT from`, `unlike`,
  `same as`, `option A/B`), require explicit NO-TEXT/NO-LOGO negatives on covers, and
  **put the generated image in front of a human before it is offered as a choice.**
  [[look-at-the-rendered-output]]
- 🟡 **E11 — PART 1 LANDED AND DEMONSTRATED 4 Aug 2026, `04da5fc`. PART 2 IS OPEN.**
  `_code_changed_exit()` in **BOTH** `needs_look` waits — the written patch covered only
  the outer one, and **EP15 sat in `flag_and_wait`**, the other. It RAISES rather than
  returning, because a bare `return` in `flag_and_wait` means *"retry the step"* on the
  code being escaped.
  🏁 **Observed for the first time:** flagged episode → touch `engine.py` → **8 seconds**
  → *"changed on disk while this episode was flagged"* → **pid 13420 → 44536.**
  🔴 **PART 2 STILL OPEN, and it is the half Hugh needs: THE BOARD CANNOT SAY "this
  engine is running code older than the repo."** Part 1 makes recovery automatic; part 2
  makes the state visible. For Hugh it is otherwise undiagnosable.
  **Original entry kept below.**
- 🔴🔴 **E11 — THE STALE-CODE GUARD ONLY FIRED WHEN THE ENGINE WAS IDLE.**
  *(Found 3 Aug 2026, the hard way.)*
  **`_code_changed()` has ONE call site: engine.py:941, at the top of the OUTER acquire
  loop.** Once an episode is claimed the engine drops into the inner `while True:` —
  step dispatch, and the 15-second `needs_look` poll — and **never returns to the outer
  loop until the episode is released.** So the guard cannot fire while an episode is
  held, building *or* flagged.
  **What that cost:** the NameError fix landed at 09:10. The running process had been
  holding EP15 since 08:47, so it kept the broken code in memory for **over an hour**,
  failed `audit_inputs` a fourth time at 10:03, and **Jodie cleared the flag and it
  walked straight back into the same bug.** Recovery needed a terminal.
  > **A deploy path that only works when the engine is healthy is no deploy path at
  > all, because the times you need it are exactly the times it is not.**
  And it is narrower than "healthy" — **kept verbatim, because this is the sharp end
  of it:**
  > **It only works when the engine is IDLE, and the one state where a stale-code exit
  > is both safe and necessary — parked on a flag with nothing in flight — is precisely
  > the state it cannot reach.**
  **TWO PARTS, AND THE SECOND IS THE ONE HUGH NEEDS:**
  1. Check `_code_changed()` inside the inner loop too — certainly in the `needs_look`
     wait, which is where a flagged engine spends all its time. A flagged episode is
     the safest possible moment to exit: nothing is in flight.
  2. **THE BOARD MUST BE ABLE TO SAY "this engine is running code older than the
     repo."** Today that state is completely invisible: the card shows the same flag,
     and clearing it does nothing, forever. **Hugh has no terminal — for him this is
     unrecoverable and undiagnosable.** The engine knows its own start time and can
     stat the three files; that comparison belongs on the rail and on the card.
  ⚠️ **AND CLAUDE.md IS WRONG WHERE IT SAYS THE GUARD "IS THE DEPLOY PATH".** It says
  never kill the engine by hand because the guard handles deploys. It does not. Until
  part 1 lands, a mid-episode code fix REQUIRES a manual restart — and the safe window
  is while the episode is FLAGGED, when nothing is computing.
- **E1** an engine that refuses to start must say WHY on the page, or the next person
  restarts it in a loop. *(The sleep guard is the worked example.)*
- **E2** `_publish_asset` must compress board assets — and build the deletion with it,
  see [[retention-ruling]].
- **E3** a standing **drift check**: assert the shot map against `aligned.srt` every
  build. The same re-point was missed three times and **every one was found by
  accident**. The fourth instrument should not need luck.
- **E4** a **pool-line wholeness** check — see
  [[a-gate-that-invites-an-edit-must-verify-it]].
- **E5** a halt with **one correct answer** is a chore wearing a decision's clothes —
  `derive_card_timings` should set those beats itself.
- 🔬 **E6 — TESTED 4 Aug 2026, AND THE RESULT IS SPLIT. CAUSE NOT ESTABLISHED. NOT
  PRE-EP16.** *Logged unexplained, on purpose.*
  | | |
  |---|---|
  | A Doc created through the Drive API **tonight**, read back | **CLEAN** — `—` `–` `‘’` `“”` `…` `é` all intact |
  | **EP15's real script Doc**, read via the export URL | **0 real em dashes**, mojibake present |
  | EP15's Doc, read via the Drive API instead | **the same corruption** |
  **Both read paths agree on EP15, so the corruption is in the STORED BYTES.** But a Doc
  created through that API tonight round-trips clean, and **I could not complete the
  comparison** — the new Doc cannot be shared from a session, so the export URL 401s and
  the clean result rests on one read path. **Do not name a cause.**
  > ### 🔴 AND THE TEST FOUND SOMETHING SHARPER, WHICH IS NOW GUARDED
  > **A document API's "text representation" MARKDOWN-ESCAPES the script**: EP15 comes
  > back as `\#` on every comment line and `Squeeze Those Odds\!`. Read via the export
  > URL it is clean. **Those backslashes would be frozen into `script_snapshot` as the
  > record of what was approved — and spoken.** `fetch_script` now asserts at the byte
  > level and flags in plain English. *(Landed `04da5fc`.)*
  **Original entry kept below.**
- 🔴 **E6 — A WRITE PATH THAT CORRUPTS, AND NO EDIT PATH TO REPAIR IT.** *(Upgraded from
  a note to a Bundle E item by Jodie, 3 Aug 2026, after it recurred.)*
  **The Drive API mangles em dashes on create** — `—` is written back as `â€"` (UTF-8
  read as cp1252). Seen on **EP14 (stop 4)** and again on **EP15**. And the MCP has
  **no update tool**, so it cannot be repaired in place: the only routes are a human
  editing the Doc by hand, or creating a second Doc — which the ONE-home rule forbids.
  **That combination is the item.** A corrupting writer would be survivable with an
  editor; an absent editor would be survivable with a clean writer. Together, every
  future episode's Doc header goes through a path that damages it and cannot be undone
  by the machine that did the damage.
  **THE FIX BELONGS AT THE WRITE END — and "pure ASCII headers" is NOT it.**
  ⚠️ *That was this file's stated remedy until 3 Aug and it was WRONG. Corrected after
  the third sighting:* `render_ready`'s allow-list is
  `SAFE_EXTRA = set("‘’“”–—…é")` — **a real U+2014 is explicitly permitted and would
  never have been flagged.** The gate rejects the CORRUPTION, never the punctuation.
  So ASCII headers were a workaround for a broken write path masquerading as a rule —
  **and in six months nobody would have been able to explain why the rule existed.**
  The write path must stop corrupting; that is the whole of it. Belt and braces: a
  post-create readback that halts if the bytes came back different, since the create
  call reports success (`fileSize: 1`) whatever it wrote. [[assert-the-artefact]]
  **THIRD SIGHTING, 3 Aug:** EP15's header again — this time reaching `spoken-words.txt`
  and hard-failing `render_ready`, because a `#` comment block is NOT inert to that
  checker. Two consecutive episodes have now lost time to it.
  ⚠️ **AND THE REASON IT RECURRED IS WORTH MORE THAN THE BUG.** EP14's fix was recorded
  as "ASCII header" against a stop that was marked ✅ fixed. **EP15 reintroduced it
  because the header was copied from EP14's local DRAFT, not from EP14's corrected
  DOC** — the draft still had the em dashes in it. *A fix applied to the artefact and
  not to the thing that generates the artefact will come back on the next episode.*
- **E7** the supervisor log: **one timezone with a label**, and **rotate by day**, not
  by engine start.
- ~~**E8** board bug **C6**~~ — **CLOSED BY RULING, 3 Aug 2026. Build nothing.** A
  finished stage stays finished. **Never propose a "use the current Doc" button or a
  re-runnable `script_sync`.** The record is in [[script-gate-decision-record]].
- **E9** `shape` has no field in `PP-EPISODE-JSON-SPEC.md` though the visual standard
  requires it; and the packaging split-brain.
- **E10** the b-roll registry: EP14's clips were never logged.

---

# ✅ CLOSED BY RULING — off the lists entirely, do NOT raise again

- ## 🔒 THE TRUNCATION AUDIT IS CLOSED. EP01-EP15, ALL FIFTEEN ACCOUNTED FOR.
  *(4 Aug 2026. Recorded so nobody re-opens it in three weeks.)*
  **NO PUBLISHED EPISODE IS SHORT.** The E22 download bug (`_heygen_fetch` never checks
  `Content-Length`) has existed for all fifteen episodes and **bitten exactly once** —
  EP15, caught before assembly.
  | | |
  |---|---|
  | **EP06-EP15** | **12/12 on the fuzzy tail match** — the range where the standing outro existed |
  | EP02, EP03 | 11/12 — clean *(an EXACT test would have flagged both)* |
  | EP04, EP05 | script-on-disk differs from what shipped. **NOT truncation:** both end on COMPLETE SENTENCES with normal tails, where EP15's real truncation cut MID-WORD |
  | EP11-EP14 | masters match HeyGen's stated bytes **EXACTLY** |
  | **EP01** | ⚠️ **CANNOT BE VERIFIED — no surviving script.** Named, not glossed. The reason the script is now kept permanently: [[retention-ruling]] |
  📝 **NOTE FOR HUGH, NOT A TASK:** EP05 shipped without a responsible-gambling line. It
  **predates the standard, it is not a fault, and nothing about the video changes.**
  Compliance is his, so he should simply know it exists — whether a line in the
  description is worth adding is his call. **Do not raise it as work.**
  ⚖️ **AND THE PRINCIPLE THAT CLOSES IT:** *a guard prevents recurrence — it does not
  oblige us to go back.* Nothing published is re-rendered or re-cut. In CLAUDE.md.

- **THE CREDIT CONVERSATION IS HAD AND APPROVED (Jodie, 4 Aug 2026).** Hugh is happy
  for her to buy more credits. **NEVER RAISE COST AS AN OBJECTION TO GENERATING
  SOMETHING.** Report what a thing will cost when it is useful information; never offer
  "it's only N credits" as a reason for or against doing it, and never propose the
  cheaper option *because* it is cheaper. ⚠️ This does NOT touch
  [[jodie-spend-nothing-without-approval]] — **stopping at the cost boundary for a
  DECISION still stands.** What is gone is cost as an ARGUMENT.
- **THE E-BOOK LINK GAP IS A NON-ISSUE (Jodie, 4 Aug 2026).** `ebook_link` is NULL for
  **EP06-EP12** and that is fine. The publish card captures it going forward; **the old
  rows stay as they are.** Do not re-raise, do not propose a backfill, do not put it
  back on a list.

# ⚠️ STANDING — true regardless of what is in flight

- **EP11-EP13 are PUBLISHED.** Do not touch, re-cut or retitle.
- **Human gates are sacred.** Never auto-render, never auto-publish. **Stop at the cost
  boundary.** [[jodie-spend-nothing-without-approval]]
- **Jodie clears flags and publishes. Nothing touches YouTube but her.**
- **§0a is absolute** — the article's sentences are never rewritten. Only WHICH sentence
  and HOW it is shown may change.
- **Tighten a gate freely; loosening one needs Jodie's ruling.**
- **CODE FREEZE WHILE AN EPISODE IS RUNNING.** Never edit `engine.py`, `providers.py` or
  `rail.py` mid-build.
  ⚠️ **THIS BULLET USED TO SAY the stale-code guard exits the engine and the supervisor
  restarts it, and that "IS the deploy path". IT IS NOT — corrected 3 Aug 2026 after it
  cost an hour**, and the wrong version survived here in memory for a day after CLAUDE.md
  was fixed. `_code_changed()` is checked ONLY at the top of the outer acquire loop, so
  **a claimed episode never reaches it.** Until E11 part 1 lands, **a mid-episode fix
  needs a MANUAL restart**, and the safe window is while the episode is FLAGGED.
  *(This is why new checks land as NEW FILES — `check_page_images.py` did, and needed no
  restart to be written, tested and proved.)*
- **The rail is select / insert / update.** [[retention-ruling]] holds the one exception.
- [[assert-the-artefact]] · [[one-source-of-truth-or-it-drifts]] ·
  [[anything-that-waits-must-say-so]] · [[command-hygiene-for-permissions]] ·
  [[look-at-the-rendered-output]] · [[jodie-ship-it-and-who-runs-what]]

# 🏆 THE SENTENCES WORTH KEEPING

> **"A ruling is not a mechanism. If the answer is 'someone will remember', it isn't a
> rule, it's a hope."**

> **"A pipeline is only measured by the run nobody prepared for."**

> **"A file that asks a question is a halt wearing a text file's clothes."**

> **"An installed task that never fires is the hope it was meant to replace."**

> **"A halt with one correct answer is a chore wearing a decision's clothes."**

> **"A test that assumes a name the process is designed to change is a test with a fuse
> in it."**

> **"A lint that cries wolf is a lint someone turns off."**

> **"Written and reviewed is not landed."** *(The queued E11 patch was correct about the
> fault and wrong about which loop, and only building it showed that.)*

> **"An optional field is not a type mismatch."** *(Two false positives that would have
> fired on every episode from now on — caught by the tests written to stop the guard
> crying wolf, not by reading it.)*

> **"A grey box has a luma."** *(Why `self_qc` passed an end card that was a broken
> image: every instrument was measuring something real, and none of them was measuring
> the thing.)*

> **"A single frame of an animated card is not evidence about the card."**
