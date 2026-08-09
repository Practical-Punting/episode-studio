# EFFICIENCY AUDIT — from "words approved" to "the render is startable"

**Written 9 August 2026, from `engine/logs/engine-2026-08-08.log` and
`engine-2026-08-09.log`, the checkpoint, and the code as it stands at `fc99f8b`.**

> ## 🔴 THIS FILE IS AN AUDIT AND A PLAN. NOTHING IN IT HAS BEEN BUILT.
> It was written by a **second** Claude Code instance, read-only, alongside the one
> building EP19. No code was changed, nothing was committed, the engine was not
> restarted. Every number below comes from a log line or from reading the code —
> none of it is remembered, and none of it is estimated unless it says so.

**The question:** EP19 took **thirty-two minutes** between Jodie approving the words
and the board being able to say *"start Gordon's render"*. It should take about a
minute. Where did the thirty-two minutes go, and what is actually on the critical
path?

**The one-sentence answer:** **31 minutes 41 seconds of it — 99.4% — was a
commissioned writer authoring `episode.json`, and the render does not need
`episode.json`.** The render needs the approved script and a project name, and both
of those exist the instant Jodie clicks *Approve*. The render is sitting behind a
step it has no dependency on.

---

# 1 · MEASURED — what actually happened

**A note on the clocks.** `engine.py` logs in **UTC**; the supervisor logs in **local
(AEST, UTC+10)**. Every engine timestamp below is UTC as it appears in the log file.
EP19's render gate opened at `04:13:50` UTC = **14:13:50** on Jodie's clock.

## 1a · EP19 — `10 Systems For Action Hungry Punters Part 1`

| at (UTC) | what the log says | elapsed |
|---|---|---|
| `03:35:26` | gate poll — *words not approved + "I've read the script" not ticked* | |
| `03:40:51` | gate poll — *words not approved* ← **the tick is now ticked** | |
| ~`03:41:3x` | **Jodie approves the words** (not logged; bounded below) | |
| `03:41:57` | `claimed PP-EP19 (…) -> building` | **≤ 30s** after the click |
| `03:41:58` | `-- step script_sync` | 1s |
| `03:41:59` | script re-read — 1748 words, sha `6a293aa0383b` | 1s |
| `03:42:00` | `-- step audit_inputs` | 1s |
| `03:42:01` | standing assets 5 present · wallet checked · **commission starts** | 1s |
| `04:04:01` | *this episode's settings and cards written in* **1320s** *, $6.15, 27 turns* | **22m 00s** |
| `04:04:04` | **attempt 1 rejected — 3 things** (one of them false; §1c) | 3s |
| `04:04:04` | `repair 1 of 2` — the same brief plus the checker's own words | |
| `04:13:45` | *written in* **581s** *, $4.30, 59 turns* | **9m 41s** |
| `04:13:47` | config pre-flight clean · card pre-flight 0 blockers · **passed** | 2s |
| `04:13:49` | `-- step render_gate` | 2s |
| `04:13:50` | **`>> RENDER GATE OPEN`** — the render is startable | 1s |

### **APPROVAL → RENDER STARTABLE: 31m 53s from the claim; ~32m from her click.**

| chunk | seconds | share |
|---|---|---|
| claim + `script_sync` + the head of `audit_inputs` | **4** | 0.2% |
| **the `episode.json` commission, attempt 1** | **1320** | **69.0%** |
| the two pre-flight gates running (both legs) | 5 | 0.3% |
| **the `episode.json` commission, repair leg** | **581** | **30.4%** |
| `render_gate` itself (`assert_script_gate` + drift check + name) | 3 | 0.2% |

**Two commissions = 1901s = 99.4% of the wall clock.** Everything else in the
window, added together, is **twelve seconds**.

## 1b · EP18 — `Those Top 6 Favourites` (the control)

| at (UTC) | what the log says | elapsed |
|---|---|---|
| `07:56:41` | gate poll — *words not approved* (the tick was already on) | |
| `08:00:54` | `claimed PP-EP18 (…) -> building` | **≤ 30s** after the click |
| `08:00:57` | `-- step audit_inputs` · wallet checked · **commission starts** | 3s |
| `08:18:04` | *written in* **1021s** *, $4.72, 18 turns* — **passed first time, no repair** | **17m 01s** |
| `08:18:08` | **`>> RENDER GATE OPEN`** | 4s |

### **APPROVAL → RENDER STARTABLE: 17m 14s. The commission was 1021s = 98.7% of it.**

> ## 📌 EP18 IS THE IMPORTANT NUMBER, NOT EP19.
> EP19 is easy to dismiss as a bad day — a false blocker, a repair leg, a writer that
> needed two goes. **EP18 had none of that.** It commissioned once, passed every check
> first time, and **still made the longest job in the pipeline wait seventeen minutes.**
> The delay is not a fault in the commission. **It is the ORDER.**

## 1c · The three things that rejected EP19's first attempt

```
x the whole 'cards[].content.bars[]' block is absent — both reference episodes
  have it (4 keys, e.g. cards[].content.bars[].label, …).
x C2: C2.eyebrow = 'Two · The 10K System' carries a figure and has NO trace entry.
x C3: C3.eyebrow = 'Three · The 10K System' carries a figure and has NO trace entry.
```

**Two of the three are real and the gate was right to hold them.** The eyebrows
carried a figure with no citation, which is exactly what trace-or-halt exists for.

**The first one is a false blocker, and it is the one Jodie has ruled on.** It comes
from `preflight_episode_json._subtree_missing()` — a key path both reference episodes
carry and this one does not is promoted to `must`, which halts. Under a `[]` segment
that reasoning breaks: *"both references have `cards[].content.bars`"* only means
**some card, somewhere, in each of them, drew a bar chart.** EP26's key/type diff has
no way to know that a bar chart is a **content decision about this article**, not a
convention of the file format.

> ### ⚖️ AND THE HONEST ACCOUNTING, BECAUSE IT MATTERS FOR THE PLAN.
> **The false blocker did NOT cost EP19 a repair leg on its own** — the two real trace
> gaps were in the same verdict, so the repair leg was happening regardless.
> What it *did* cost is visible in the artefact: the writer went away and **authored a
> whole new bar card, C6, to satisfy a checker.** The repair leg ran **59 turns** to fix
> three items, against 27 turns for the entire original file. And C6 turned out well —
> which is luck, not correctness. **The next episode whose only fault is this one pays
> a full ~10-minute repair leg for nothing.**

## 1d · What came BEFORE the approval — context, not the audited window

EP19's script was written by the machine, and that took from `00:06:49` to `02:09:18`:

| | |
|---|---|
| drafting-pass commissions | **6** — 295s, 342s, 254s, 283s, 227s, 251s = **1652s of writer time** |
| wall clock across them | **1h 31m 47s** (the pass fires at most every 900s, and only when idle) |
| drafts thrown away | **5**, all on the fidelity gate, and **the writer was never told why** |
| engine restarts (stale-code guard) | **5**, costing **~14m 24s** with no engine running at all |

**The five wasted drafts are already fixed** — `abe1737`, *"the script commission gets
its own faults back"*, landed today and puts the script commission on the same
`commission_with_repair` loop the cards use. **The 900-second interval and the
supervisor's 5-minute restart gap are not fixed**, and they are what §4 is about.

---

# 2 · UNDERSTOOD — the order, and what actually depends on what

## 2a · The order as coded

`engine.py:201` — `PHASES["building"]`:

```
script_sync → audit_inputs → render_gate → credit_check → broll_submit
            → covers_ab → broll_collect → cover_pick → ebook_cover → cards_render
```

`step_render_gate` (`engine.py:608`) is what makes the render startable. It does
three things and only three: `assert_script_gate()`, `_script_drift_check()`, and
`ctx.ep_set({"heygen_name": name})` where `name` is
`f"PP-EP{nn:02d} — {ep['title']}"`.

**On the board, `heygen_name` is the switch.** `app.js:1158`:

```js
case "building":
  return (ep.heygen_name && !ep.render_started_at ? gateRender(ep) : "") + …
```

`gateRender()` then needs exactly two things from the row: **the project name** and
**the script to paste** (`scriptPanel(ep, …)` reads `script_snapshot`).

## 2b · What each building step needs

| step | needs `episode.json`? | needs the approved script? |
|---|---|---|
| `script_sync` | no | yes — it *is* the script |
| **`audit_inputs`** | **it WRITES it** (the commission) | yes |
| **`render_gate`** | **NO** | **yes — and nothing else** |
| `credit_check` | yes — `broll_plan()` reads it | no |
| `broll_submit` | yes — the prompts are in it | no |
| `covers_ab` | yes — the cover wording is in it | no |
| `broll_collect` | via the job ids | no |
| `cover_pick` | no | no |
| `ebook_cover` / `cards_render` | yes | yes |

### 🔴 **`render_gate` IS THE ONLY STEP IN THE WHOLE BUILDING PHASE THAT DOES NOT NEED `episode.json`. IT IS ALSO THE ONLY ONE A HUMAN IS WAITING ON. IT IS CURRENTLY BEHIND THE MOST EXPENSIVE ONE.**

Everything else — b-roll, covers, the cards — genuinely reads `episode.json` and
genuinely has to wait for it. **There is no parallelism to win there.** The one
misplacement is the render, and moving it is the entire lever.

## 2c · What the LOCKED ORDER already says, and what it permits

`engine.py:112` — the order Jodie approved on 26 July:

> *"3 render gate AND the gens batch (b-roll + cover heroes A/B + cards) fire IN
> PARALLEL"* … *"The HeyGen render is the LONG POLE (5-45 min) and depends only on the
> spoken track — which is final at the Words Gate — so it starts EARLY, never last, and
> never behind the visuals."*

**The intent is already exactly right.** `step_render_gate`'s own docstring says the
gate opens *"the moment the words are locked … NOT at the end of the build."*
What has happened since is that **a twenty-minute writing job was inserted in front of
it** — `audit_inputs` used to be a scan, and became a commission on 7 August. Nobody
re-sequenced anything; the step in front simply grew from four seconds to twenty-two
minutes, and the render inherited the wait.

**`check_locked_order()` (`engine.py:245`) already permits the fix.** Its assertions
are `script_sync < audit_inputs`, `script_sync < render_gate`,
`render_gate < broll_submit`, and four more about the covers and cards. **Moving
`render_gate` to sit immediately after `script_sync` breaks none of them.** The guard
is not what is stopping this — only the ruling is, and that is Jodie's to give.

## 2d · The watchdog is calling both episodes "stuck", and both were fine

`STEP_BUDGET_S` (`engine.py:798`) **has no entry for `audit_inputs`**, so it falls
through to `DEFAULT_STEP_BUDGET_S = 15 * 60 = 900s`. The board reads that number
straight off the row (`app.js:279`):

```js
if (ran > cur.budget_s * 1000) return { ...out, state: "stuck" };
```

| episode | `audit_inputs` ran | budget | what the board said |
|---|---|---|---|
| EP18 | **1029s** | 900s | **"Stuck — Checking the inputs"** for the last 2m 09s |
| EP19 | **1907s** | 900s | **"Stuck — Checking the inputs"** for the last 16m 47s |

**Two episodes out of two.** And the budget cannot be right by accident: the
commission this step runs is bounded at **1800s per attempt × 3 attempts = 5400s**
(`ENGINE_COMMISSION_TIMEOUT_EPJSON`, `EPJSON_ATTEMPTS`). **The step's alarm is set to
one sixth of what the step is allowed to take.**

⚠️ **And the label is wrong as well as the clock.** For twenty-two minutes the board
said *"Checking the inputs"* while a writer was drafting a 67 KB file. That is the
fault this repo already names — **three states look identical and only one is a
fault** — except here the *working* state is being mislabelled as *stuck*, which is the
alarm crying wolf rather than sleeping. **A "stuck" that is wrong twice out of twice is
a "stuck" nobody will believe the day it is right.**

---

# 3 · THE PLAN — six items, none of them built

Each carries **what to change · the risk · how to prove it, control first**. Per
CLAUDE.md 4b: **write the failing case first, watch it go red, then write the passing
one.** Per fault #8: the cut is part of the deliverable, and two of these six do not
earn their place yet.

---

## 🥇 3.1 · RENDER FIRST — move the gate ahead of the commission
### **This one lever is worth 31m 41s of EP19's 32 minutes, and 17m 01s of EP18's 17m 14s.**

**What to change**

1. `engine.py:201` — reorder one list:
   ```
   "building": ["script_sync", "render_gate", "audit_inputs", "credit_check", …]
   ```
   *`script_sync` stays first and must* — a render may never be offered on text that
   has not been re-read from its home. That is already asserted.
2. `check_locked_order()` — **add** `before("render_gate", "audit_inputs")` with the
   reason spelled out, so the new order cannot silently regress the way the old one
   silently did. **The absence of this assertion is why nobody noticed.**
3. `LOCKED_ORDER` (the prose string), `docs/PP-STANDARDS.md` and `engine/README.md` —
   the re-approved wording, written once, in one place.
4. **Nothing else.** `step_render_gate` itself is unchanged. `run_phase`'s
   `render_started_at` branch is unchanged. The b-roll, the covers and the cards keep
   their existing order behind `audit_inputs`, because they really do need it.

**What it buys, measured against these two episodes**

| | today | after |
|---|---|---|
| EP18 approval → render startable | 17m 14s | **~10s** |
| EP19 approval → render startable | 31m 53s | **~10s** |

The 22-minute commission does not get faster. **It stops being on the critical path** —
it moves inside the render window, where the locked order always intended the pictures
to live.

**The risk — and it is a ruling, not a bug**

> 🔴 **THIS IS A RE-SEQUENCING OF THE LOCKED ORDER AND NEEDS JODIE'S EXPLICIT
> RE-APPROVAL.** CLAUDE.md: *"Re-sequencing needs Jodie's explicit re-approval."* Do
> not land it on the reasoning in this file.

| risk | assessment |
|---|---|
| A render is started, then `audit_inputs` halts | **The render is not wasted.** It is built from the approved script, and no `episode.json` fault can change a word Gordon says. The episode waits at a flag with its long pole already cooking — strictly better than waiting at a flag with nothing cooking. |
| A render is started, then the SCRIPT turns out to need changing | **This is the real one.** Today `audit_inputs` is the last moment before spend; after the change, spend starts earlier. But the script is *locked at the words gate by design* and changing it already requires "Unlock and re-approve" — a deliberate act, not a drift. **Name it as a known limitation; do not build around it.** |
| The pre-flights lose their "before a credit moves" property | **They keep it for Higgsfield.** `credit_check` and `broll_submit` still sit *behind* `audit_inputs`, unchanged. Only the HeyGen render — a different wallet, a human-pressed button, and a spend on words that are already final — moves in front. |
| `heygen_name` is set earlier, so title-matching finds the wrong render | Unchanged risk. The title is final at the words gate; this changes *when* the name is written, not *what*. (The deeper fault — finding a paid render by NAME instead of storing its id — is **E20**, and is not this piece.) |

**How to prove it — CONTROL FIRST**

1. **RED first, on today's code.** Write the assertion before the fix and watch it
   fail: on a `build_state` snapshot from **EP19's actual run**, assert that
   `heygen_name` was non-null while `steps.audit_inputs.done` was false. **It is
   false today** — that is the control that proves the test can fail.
2. **Static.** Extend `engine/test_step_call_sites.py`'s sibling (or a new
   `test_locked_order_render_first.py`) to assert the `PHASES["building"]` index of
   `render_gate` is less than that of `audit_inputs`, **and** that
   `check_locked_order()` returns that problem when it is not. Two directions, one
   test — the guard must be watched failing.
3. **The board, which is what a human actually receives** (fault #1). A `.mjs` case in
   the existing `test_board_*.mjs` family: a row with `heygen_name` set,
   `render_started_at` null, `status: "building"`, `build_state.steps.audit_inputs`
   **absent** → `gateFor(ep)` returns the render gate **and** `scriptPanel` carries the
   full script. Today's board already does this correctly; the test pins it so the
   reorder cannot break the surface it exists to reach.
4. **The artefact, on the next real episode.** From the rail, not from memory:
   `render_offered_at` minus the claim stamp **< 30 seconds**, with
   `build_state.steps.audit_inputs.done` still false at that moment. **That number in
   the run log is the proof.** Nothing else is.

---

## 🥈 3.2 · COMMISSION-AWARE WATCHDOG + honest working-state labels
### Do this **with** 3.1, not after it — 3.1 makes the false "stuck" more visible, not less.

Once the render is away, Jodie is watching a board that says *"Stuck — Checking the
inputs"* for twenty-two minutes while everything is fine. **Fixing the order without
fixing the label trades a delay for a lie.**

**What to change**

1. **Derive the budget from the bound, never type it** (fault #7 — a hand-typed budget
   is the next stale list). `audit_inputs`' budget is
   `EPJSON_ATTEMPTS × ENGINE_COMMISSION_TIMEOUT_EPJSON` + slack, read from the same
   constants the commission itself uses. Same shape for any step that commissions.
2. **An honest label while a writer is working.** `commission()` already logs
   *"a writer is working, up to 1800s"* to the run log (fault #3, done right). Give it
   a hook that re-stamps `build_state.current.label` with the same sentence in the
   operator's words — *"A writer is drafting this episode's cards. Twenty minutes is
   normal."* `STEP_LABELS` in `app.js` reads `current.label` when present and falls back
   to the step name.
   > ⚠️ **RE-STAMP THE LABEL AND THE BUDGET. NEVER RE-STAMP `started_at`.** Resetting
   > the clock each time a commission begins would make a genuinely wedged writer
   > invisible for ever — which is the exact fault the watchdog was built for (EP14,
   > three and a half days with a healthy heartbeat). The clock must keep running.
3. **Say which attempt it is on.** `commission_with_repair` knows `i of attempts`; the
   board does not. *"Second go — the checks sent back three things"* is the truth and
   is far less alarming than silence.

**The risk**

| risk | assessment |
|---|---|
| A bigger budget hides a real stall | **This is the whole risk, and it is why the failing control below is mandatory.** The budget must be the *bound the step is actually allowed*, so a step that exceeds it is genuinely past saving — not a number chosen to stop the alarm. |
| A second source of truth about step timing | Avoided by construction: the budget is *computed from* the commission constants, so changing the timeout changes the alarm. One value, two readers, no drift (fault #2). |

**How to prove it — CONTROL FIRST**

1. **RED, on today's code, from the real data.** `stepState()` fed
   `{step:"audit_inputs", started_at: 17 minutes ago, budget_s: 900}` — EP18's actual
   shape — **must return `"stuck"` today.** That is the proof the board really does say
   it, rather than my reading of the code.
2. **GREEN, after.** The same row with the derived budget returns `"working"`, and the
   stage line reads the honest label.
3. 🔴 **THE FAILING CONTROL, WITHOUT WHICH THE FIX IS JUST A SWITCHED-OFF ALARM:** a
   row **100 minutes** into `audit_inputs` must **still** return `"stuck"`. A guard is
   not trustworthy until it has been watched failing (4b).
4. And the one that stops it regressing the other way: a row with `budget_s: null`
   (`heygen_download`, `cover_pick`) must return `"waiting"`, never `"stuck"`, however
   long it has run. That case already exists; keep it named.

---

## 🥉 3.3 · KILL THE FALSE BLOCKER — E26 must not demand a bar chart
### Jodie's ruling. A key/type diff may not make a content decision.

**What to change** — `preflight_episode_json._subtree_missing()` / `preflight()`.

The fix that keeps working is **not** a list of exempt keys — that is fault #7, and it
would be the sixth instance. **Derive the discriminator from the shape of the path
itself:**

> **A subtree is a CONVENTION only if it is present on EVERY instance at its path in
> BOTH references. A subtree present on SOME instances is a CONTENT CHOICE.**

`cards[].content.bars` is present on **some** cards in EP17 and EP18 → content choice →
demoted to `worth`, reported and never blocking. `build.standing` — EP15's genuine
finding — has **no `[]` in its path**, is present in every reference by definition,
and **stays a blocker exactly as it is today.** The discriminator is in the data, not
in a list somebody maintains.

**The risk**

| risk | assessment |
|---|---|
| Demoting too much, and losing EP15's genuine finding | Directly testable, and the fixture already exists in the repo's habits. `build.standing`, `thumbnail.*` and every other structural block is unaffected — **prove that, do not assert it.** |
| A card block that genuinely IS required stops blocking | Then it was never E26's job. A block a card cannot render without is `preflight_cards`' business — it reads the actual page templates — and that check is unchanged. **Two checkers, two questions; this is the right one to narrow.** |

**How to prove it — CONTROL FIRST**

1. **Build the fixture from the real file, and RED first.** Take EP19's shipped
   `docs/episode.json`, **remove C6's `content.bars` and `trace.bars`**, save it as
   `engine/testdata/ep19-no-bars.episode.json`. Against EP18 + EP17, today's code
   **must** emit the exact line from the run log:
   *"the whole `cards[].content.bars[]` block is absent…"*. **That is the control that
   proves the test can fail** — and it reproduces the fault from the artefact rather
   than from a description of it.
2. **GREEN.** After the change, that fixture returns **zero** blockers, and the same
   absence appears under *"worth knowing"*.
3. 🔴 **THE FAILING CONTROL.** Take the same fixture and delete the whole
   **`thumbnail`** block. It must **still** be a blocker. **A narrowing that does not
   demonstrate what it still catches is a switched-off check.**
4. And the sibling question, asked once rather than waited for (the checkpoint's own
   lesson): **does this fault have a twin in `preflight_cards.py`?** Read it and say so
   either way before closing the item.

---

## 4th · 3.4 · KICK ON SUBMIT — stop the engine sleeping through a human's click
### Small at the approval gate (≤ 30s). **Large at the queue gate (up to 15 minutes).**

**Be honest about the size first.** At the approval gate the engine is on a 30-second
idle poll, and both EP18 and EP19 were claimed **inside 30 seconds** of the click.
**The 30 seconds is not where the thirty-two minutes went**, and this item must not be
sold as if it were.

**Where it is genuinely expensive is the OTHER click — "Build episode →".**
`_draft_watch` runs at most every **900 seconds**, and only when nothing is claimable
(`engine.py:1567`). A URL pasted just after a pass **waits fifteen minutes before
anything at all happens**, and `_draft_watch`'s own docstring names the second half:
a commission blocks the single-threaded idle loop for its whole duration (**227–342s**
observed on EP19), so an episode approved during one waits behind it.

**What to change**

1. **Drop the 900-second gate on `_draft_watch` and let the LEDGER be the brake.** The
   spend bound is already `DRAFT_ATTEMPT_LIMIT = 3`, recorded in a file **before** the
   spend, surviving restarts. The interval is a *second* brake doing the same job less
   well, and it is the one costing fifteen minutes.
2. **Re-check `acquire()` the instant `_draft_watch` returns**, rather than sleeping
   `idle_poll` first. A script seated at the top of the loop should not wait 30s to be
   noticed.
3. **Only if 1 and 2 are not enough:** Shape B from
   `DESIGN-the-pre-claim-drafting-pass.md` — the drafting pass in its own thread, so a
   commission can never sit in front of a claimable episode. **That is a real design
   piece and should not be reached for first.**

**The risk**

| risk | assessment |
|---|---|
| Removing the interval unbrakes the spend | **The ledger is the brake and always was.** Prove it: with the interval at zero in `--mock`, the third attempt must still stop and leave the episode alone. If it does not, the ledger was never the guard and the interval was load-bearing — **find that out before landing, not after.** |
| A tighter loop hammers the rail | `rail.list_queued()` on a handful of rows, and the loop already polls every 30s. Measure the call count over an hour before and after; do not assume. |

**How to prove it — CONTROL FIRST**

1. **RED:** with `DRAFT_ATTEMPT_LIMIT` reached and the interval removed, the mock loop
   must **not** spawn a fourth commission. Watch it try and be stopped.
2. **The artefact, not the code path:** the wall time in the run log between the
   episode row appearing and the first *"commissioning one (attempt 1 of 3)"* line.
   **On EP19 that was 15 minutes at worst. Name the new number from a log, not from a
   diff.**

---

## 5th · 3.5 · SPEED THE CARD COMMISSION (~22 min)
### 🔴 **RECOMMENDED CUT — for now. It stops being on the critical path the moment 3.1 lands.**

Per fault #8: *which of these actually caused a fault?* After the render moves in front
of it, **the 22-minute commission costs Jodie nothing** — it runs inside a render
window that is 5 to 45 minutes long anyway. Optimising it would be work taken against
the length of the list, not against a real fault. **So the recommendation is: do not
build this yet.** What follows is what to do *when* it earns its place.

**What the numbers say now, and they are two observations, not a distribution:**

| | attempt 1 | repair leg |
|---|---|---|
| EP18 | 1021s · 18 turns · $4.72 | — (passed first time) |
| EP19 | 1320s · 27 turns · $6.15 | **581s · 59 turns · $4.30** |

> ### 📌 THE TELL IS IN THE TURN COUNT, AND IT IS THE CHEAPEST THING HERE.
> **59 turns to fix three items, against 27 turns to write the entire 67 KB file.**
> Every repair is a **fresh spawn** (`providers.py:2576` says so), so the writer that
> fixes the file **has never seen it** and spends most of its turns re-reading. **The
> follow-up brief carries the complaints but not the objects the complaints are about.**

**When it earns its place, in this order:**

1. **Scope the repair, not the whole file.** Put the offending card objects *inline* in
   the follow-up alongside the checker's words. The engine already knows which cards —
   the blockers name them. **Smallest change, biggest share of the repair leg, and no
   new concurrency.**
2. **Then, and only if attempt 1 is still the problem: split the authoring.** A cheap
   *spine* pass (beats, card ids, layouts, cues, b-roll targets, packaging), then N
   parallel per-card *content + trace* passes writing one fragment each, then a
   **merge done in Python by the engine — never by a writer** — then the existing gate
   unchanged. The ids are fixed by the spine, so `check_references` is satisfied by
   construction.
   ⚠️ **The risk is real and it is not the code.** Trace-or-halt is the studio's most
   valuable check, and a writer that sees one card cannot see whether the episode
   repeats itself. **A split that produces sixteen locally-perfect, collectively
   incoherent cards is a worse outcome than a slow build.**
3. **Before either: measure.** The 1800s ceiling's own comment says it — *"one
   observation sets a floor, not a distribution."* **Get five episodes of
   elapsed/turns/cost first.** Two is not enough to optimise against.

---

## 6th · 3.6 · AUTO-FIT LONG TITLE CARDS — ✅ **ALREADY LANDED TODAY. NOTHING TO BUILD.**

`fc99f8b` — *"A long title WRAPS to two lines instead of halting the build"*, committed
9 Aug 15:08. `author_title_card.py` now tries two lines before halting, and its own
comment names EP19 as the case: *"'10 SYSTEMS FOR ACTION-HUNGRY PUNTERS' measured
1423px against a 1260px box even at the 90px floor."*

**What it cost before it landed, from the log:** the halt at `04:37:01`, cleared at
`05:08:43` — **31m 42s of human wait.** That sat **inside the render window**, not on
the approval→render path, which is why it is sixth here and not first.

**What remains, and it is correct as it stands:** a headline too wide even on two lines
at 90px still halts, and it should. That is a genuine choice between the approved words
and the design, and it is Jodie's. **Do not automate it away.**

📌 The engine has not yet re-run against the new code — `preflight_cards.py` and
`providers.py` both tripped the stale-code guard earlier today. **Confirm the fix from
the run log (`authored … TWO LINES`), not from the commit.**

---

# 4 · THE RECOMMENDED ORDER

| # | item | buys | risk | gate |
|---|---|---|---|---|
| **1** | **RENDER FIRST** (§3.1) | **~32 min → ~10s** | order re-sequencing | 🔴 **needs Jodie's explicit re-approval** |
| **2** | **watchdog + honest labels** (§3.2) | ends a false "stuck" seen 2/2 | low | none |
| **3** | **kill the `bars[]` false blocker** (§3.3) | ~10 min of repair leg, and a checker that stops making content decisions | low | Jodie's ruling already given |
| **4** | **kick on submit** (§3.4) | ≤30s at approval; **up to 15 min at queue** | low–medium | none |
| **5** | speed the card commission (§3.5) | 0 min once #1 lands | **high** | **CUT for now** |
| **6** | auto-fit long titles (§3.6) | — | — | ✅ **done (`fc99f8b`)** |

**1 and 2 belong in the same sitting.** Moving the render without fixing the label
leaves Jodie watching a board that says *"Stuck"* for twenty-two minutes while
everything is working — a delay traded for a lie.

**3 and 4 are independent** and can land in either order.

**5 is a cut, and the cut is the deliverable.** Revisit it after five episodes of
measured commission times, and start with the repair scoping — not the concurrency.

---

> ## 🔴 WHAT WOULD MAKE THIS AUDIT WORTH REPEATING
> **Nothing here needed a stopwatch. Every number came out of the run log**, because
> the engine already stamps the start of work and not only its finish (fault #3). The
> one number it does **not** stamp is **the moment Jodie clicked Approve** — so
> "approval → render startable" had to be bounded (`≤ 30s`) rather than measured.
> **A `words_approved_at` on the row would close that**, and it is one column and one
> board write. Then this audit becomes a query rather than an afternoon.
