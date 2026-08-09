# 3 — RENDER FIRST: the render gate opens at APPROVAL, not behind the card commission
## …and the watchdog learns what a commission is, in the same landing

**`engine.py` · `app.js` · `commission.py` (one optional hook). NOT LANDED.**
**Approved by Jodie, 9 August 2026 — this is a LOCKED-ORDER change and she has ruled on it.**

> ## 🔴 DO NOT LAND THIS WHILE EP19 IS BUILDING.
> `CLAUDE.md`: **CODE FREEZE WHILE AN EPISODE IS RUNNING.** `_code_changed()` is checked
> only at the top of the outer acquire loop and inside the two `needs_look` waits — a
> *claimed, building* episode never reaches either. Editing `engine.py` mid-build does
> not deploy; it does nothing until a restart, and then only if the episode is flagged.
> **The safe window is: EP19 parked at `awaiting_approval`, or EP19 FLAGGED.** Confirm
> from the log (`engine up — … pid=`), never from having issued a start.

**The evidence for all of this:** `docs/EFFICIENCY-AUDIT-approval-to-render.md`, written
9 Aug from `engine/logs/engine-2026-08-08.log` and `engine-2026-08-09.log`. Every number
below comes from there. **Do not re-derive it.**

---

# THE FAULT, IN ONE TABLE

| episode | approval → `>> RENDER GATE OPEN` | of which was the `episode.json` commission |
|---|---|---|
| **EP18** (clean run, one commission, no repair) | **17m 14s** | **1021s — 98.7%** |
| **EP19** (one commission + one repair leg) | **31m 53s** | **1901s — 99.4%** |

**EP18 is the important one.** It commissioned once and passed every check first time,
and *still* made the longest job in the pipeline wait seventeen minutes. **This is not a
fault in the commission. It is the order.**

`step_render_gate` needs exactly two things, and both are final the instant Jodie clicks
*Approve*:

- **the project name** — `f"PP-EP{nn:02d} — {ep['title']}"`, from `ep_number` + the
  approved `title`;
- **the approved script** — `script_snapshot`, re-read from its home by `script_sync`.

**It does not read `episode.json`.** It is the only step in the whole building phase that
does not — and it is the only one a human is waiting on. Nobody re-sequenced anything:
`audit_inputs` was a four-second scan until it became a **commission** on 7 Aug, and the
render silently inherited the wait.

---

# 1 · THE CHANGE

## 1a · `engine.py:201` — `PHASES["building"]`

```python
# BEFORE
PHASES = {
    "building":   ["script_sync", "audit_inputs", "render_gate", "credit_check",
                   "broll_submit", "covers_ab", "broll_collect",
                   "cover_pick", "ebook_cover", "cards_render"],
```

```python
# AFTER — render_gate moves from index 2 to index 1
PHASES = {
    "building":   ["script_sync", "render_gate", "audit_inputs", "credit_check",
                   "broll_submit", "covers_ab", "broll_collect",
                   "cover_pick", "ebook_cover", "cards_render"],
```

**`script_sync` stays first and MUST.** A render may never be offered on text that has
not been re-read from its home — that is the Script Gate's whole point, and
`check_locked_order()` already asserts it.

**That single list is the change.** `step_render_gate` itself is untouched:
`assert_script_gate()`, `_script_drift_check()`, `ep_set({"heygen_name": …})`,
`stamp("render_offered_at")`, `rail.progress(…, 16)`. All correct where they are.

## 1b · `engine.py:608` — `step_render_gate`'s docstring

The docstring already says the right thing —

> *"HUMAN TURN 2 opens HERE — the moment the words are locked and the spoken track has
> passed the render-ready scan, NOT at the end of the build."*

**Correct the second half of that sentence.** After this change there is no scan in
front of it, and the docstring must not describe a dependency that no longer exists.
Replace with a line naming what it actually needs (the project name and the approved
script) and what it deliberately does **not** wait for (`episode.json`, the pictures).

## 1c · `engine.py:112` — the `LOCKED_ORDER` string

```python
# AFTER
LOCKED_ORDER = (
    "1 script + words · 2 SCRIPT GATE + WORDS GATE (read the script, approve "
    "title/hook/byline) · 3 RENDER GATE OPENS IMMEDIATELY — the render needs only the "
    "approved script and the project name, and both are final at the words gate · "
    "4 the episode.json commission, the gens batch (b-roll + cover heroes A/B) and the "
    "cards all run BEHIND the render, inside its window · 5 cover pick WHILE Gordon "
    "renders · 6 engine finishes hands-off · 7 master -> shot map -> assembly -> QC · "
    "8 the four approvals · 9 publish + Stage-8 close-out"
)
```

## 1d · The prose homes — write it ONCE, in each of its two homes

- `docs/PP-STANDARDS.md` — THE LOCKED ORDER section.
- `engine/README.md` — the same order.
- `CLAUDE.md` — the **THE LOCKED ORDER** bullet under Hard rules, which currently reads
  *"words gate → render gate AND the gens batch fire in parallel"*. It now reads: **the
  render gate opens at the words gate; the gens batch and the commission run behind it.**

⚠️ **Do not paraphrase it four different ways.** One sentence, copied. (Fault #2.)

## 1e · What does NOT change, and must not be "tidied"

| | why |
|---|---|
| `step_credit_check`, `step_broll_submit`, `step_covers_ab` stay **behind** `audit_inputs` | they genuinely read `episode.json` — the b-roll prompts and the cover wording are in it. **There is no parallelism to win there.** |
| the Higgsfield "verify before spend" property | `credit_check` still sits behind the pre-flights, unchanged. Only the **HeyGen** render — a different wallet, a human-pressed button — moves in front. |
| `PCT["building"] = (12, 40)` | leave it. `run_phase` derives the bar from the step index, so `render_gate` reports 15% instead of 18% and then `step_render_gate` sets 16 itself. Cosmetic, self-correcting, not worth a change. |
| `STEP_BUDGET_S["render_gate"] = None` | still right. The step returns immediately; `None` simply means "never alarm", which costs nothing. |

---

# 2 · THE LOCKED-ORDER APPROVAL, AND THE GUARD

## 2a · The approval, recorded

> ### ✅ **Jodie approved this locked-order change on 9 August 2026.**
> `CLAUDE.md` requires it in terms — *"Re-sequencing needs Jodie's explicit re-approval"*
> — and the approval is **for the reorder in §1a**: the render gate ahead of the
> `episode.json` commission, with the commission, covers, cards and assembly running
> behind it and inside the render window.
>
> **The reasoning she approved:** the render is the long pole (5–45 min) and depends only
> on the spoken track, which is final at the words gate. Nothing an `episode.json` fault
> can do changes a word Gordon says, so **no card fault can waste a render.**
>
> **This approval covers this reorder and nothing else.** Any further re-sequencing is a
> fresh ruling.

**Also write it into `docs/PP-RULINGS.md`** — that is the home for what was decided and
why, and a ruling that lives only in a landing-queue file disappears the day the file
is marked LANDED.

## 2b · `check_locked_order()` — all seven existing assertions still hold

Verified against the new order
`["script_sync", "render_gate", "audit_inputs", "credit_check", "broll_submit", "covers_ab", "broll_collect", "cover_pick", "ebook_cover", "cards_render"]`:

| # | assertion | old | new | holds? |
|---|---|---|---|---|
| 1 | `script_sync` < `audit_inputs` | 0 < 1 | **0 < 2** | ✅ |
| 2 | `script_sync` < `render_gate` | 0 < 2 | **0 < 1** | ✅ |
| 3 | `render_gate` < `broll_submit` | 2 < 4 | **1 < 4** | ✅ |
| 4 | `covers_ab` in building, not in rendering | ✅ | ✅ | ✅ |
| 5 | `covers_ab` < `broll_collect` | 5 < 6 | 5 < 6 | ✅ |
| 6 | `cover_pick` < `ebook_cover` | 7 < 8 | 7 < 8 | ✅ |
| 7 | `ebook_cover` < `cards_render` | 8 < 9 | 8 < 9 | ✅ |

### 🔴 **AND THAT IS EXACTLY THE PROBLEM — THE GUARD PERMITTED THE REGRESSION IT EXISTS TO CATCH.**

Nothing in `check_locked_order()` ever said the render must come before the commission,
so when `audit_inputs` grew from four seconds to twenty-two minutes **the guard stayed
green while the render slid behind it.** The absence of the eighth assertion is why
nobody noticed for two episodes.

**ADD IT, in the same commit as the reorder:**

```python
    if not before("render_gate", "audit_inputs"):
        problems.append(
            "the render gate must open BEFORE audit_inputs — audit_inputs COMMISSIONS "
            "episode.json (17-32 minutes, measured on EP18 and EP19) and the render "
            "needs none of it. The render is the long pole and depends only on the "
            "approved script, so it is offered the moment the words are locked. "
            "Approved by Jodie 9 Aug 2026; the guard exists because the previous order "
            "regressed silently when this step grew from a scan into a commission.")
```

⚠️ **The eighth assertion is the durable half of this landing.** The reorder is one list;
**the assertion is what stops the next slow step being inserted in front of the render.**
*(`CLAUDE.md`: a rule nothing enforces is a hope.)*

---

# 3 · PAIRED, AND NOT OPTIONAL — THE COMMISSION-AWARE WATCHDOG

> ## 🔴 LAND THESE TOGETHER. MOVING THE RENDER WITHOUT THIS TRADES A DELAY FOR A LIE.

Once the render is away, Jodie is looking at a board that says **"Stuck — Checking the
inputs"** for twenty-two minutes while a writer works normally. It already does:

| episode | `audit_inputs` ran | `budget_s` | what the board said |
|---|---|---|---|
| EP18 | **1029s** | 900 | **"Stuck — Checking the inputs"** for the last 2m 09s |
| EP19 | **1907s** | 900 | **"Stuck — Checking the inputs"** for the last 16m 47s |

**Two out of two, and both episodes were fine.** `STEP_BUDGET_S` (`engine.py:798`) has
**no entry for `audit_inputs`**, so it falls to `DEFAULT_STEP_BUDGET_S = 900`. The board
reads that number straight off the row (`app.js:279`):
`if (ran > cur.budget_s * 1000) return { …, state: "stuck" }`.

**The step is allowed 5400 seconds.** `EPJSON_ATTEMPTS = 3` × `1800s` per attempt. **Its
alarm is set to one sixth of its own bound.**

## 3a · THE BUDGET — derive it, never type it

```python
# engine.py — near EPJSON_ATTEMPTS (engine.py:474), so the two live together.
#
# 🔴 DERIVED FROM THE BOUND THE COMMISSION ACTUALLY RUNS UNDER, not a number somebody
# chose. A hand-typed budget is the next stale list (CLAUDE.md fault #7): change the
# timeout and this follows by itself.
#
# ⚠️ IT IS DELIBERATELY THE SAME TRADE JODIE ALREADY TOOK. The comment on
# EPJSON_ATTEMPTS says it out loud: "a writer that thrashes costs about ninety minutes
# before the engine gives up… the ninety minutes is only a thrashing writer, which is
# genuinely stuck and should flag anyway." THE ALARM MUST AGREE WITH THE BOUND. An
# alarm that fires while the studio is still deliberately waiting is not an alarm.
EPJSON_TIMEOUT_S = int(os.environ.get("ENGINE_COMMISSION_TIMEOUT_EPJSON", "1800"))
```

Then in `STEP_BUDGET_S`:

```python
    "audit_inputs":    EPJSON_ATTEMPTS * EPJSON_TIMEOUT_S + 300,   # 5700s
```

> ⚠️ **ONE VALUE, TWO READERS — SO READ IT FROM ONE PLACE.** `providers.py:2619` reads
> the same env var for the actual timeout. **Either import `EPJSON_TIMEOUT_S` there, or
> put it in one module both import.** Two `os.environ.get(…, "1800")` calls is the same
> value in two places with the fix reaching one reader (fault #2), and it will drift the
> day somebody raises the timeout.

**Do the same audit for the other commissioning steps** — `ebook_pdf` and `youtube_copy`
both commission at `ENGINE_COMMISSION_TIMEOUT` (900s) and both currently fall through to
the 900s default with no headroom at all. **Derive theirs too, in the same pass.**

## 3b · THE LABEL — say what is really happening

`build_state` is jsonb and already there. **No schema change** — the standing rule holds.

**Add `label` to the in-flight marker** (`mark_step_started`, `engine.py:812`), and let
`app.js` prefer it over the step name:

```js
// app.js — stageLine() / stepState()
// The engine knows what it is doing; the board should not have to guess from a step
// name. `label` is the engine's own sentence in the operator's words. Fall back to
// STEP_LABELS when there isn't one, so nothing regresses on a step that sets none.
if (ss && ss.state === "working" && cur.label) return cur.label;
```

**The two sentences that matter:**

| moment | today | after |
|---|---|---|
| the commission running | *"Checking the inputs"* | **"Writing the cards for this episode — a writer is working. Twenty minutes is normal."** |
| the render gate open | *"Waiting for the HeyGen render to be started"* | **"Render ready — start it in HeyGen."** |

The second is already nearly right and only needs sharpening: `STEP_LABELS.render_gate`
(`app.js:296`) reads *"Waiting for the HeyGen render to be started"*, which is passive
and sounds like the machine waiting on itself. **Under the new order it is the FIRST
thing she sees, so it must read as an instruction.**

**Where the label gets set.** `commission()` (`commission.py:623`) already logs the start
of the work to the run log — *"a writer is working, up to 1800s, capped at $10.00"*
(fault #3, done right). Give it one optional hook:

```python
def commission(*, prompt, place, find_artefact, what, …, on_start=None, …):
    ...
    if on_start:
        on_start(f"{what} — a writer is working. This normally takes 15-25 minutes.")
    r = runner(argv, input=prompt, …)
```

and pass a closure from `_commission_epjson_with_repair` (`engine.py:510`) that writes
`ctx.state["current"]["label"]` and saves.

> ## 🔴 RE-STAMP THE LABEL. NEVER RE-STAMP `started_at`.
> Resetting the clock on each attempt would make a genuinely wedged writer invisible
> for ever — **which is the exact fault the watchdog was built for** (EP14: three and a
> half days on `assemble_passB` with a healthy six-second heartbeat). **The outer clock
> keeps running against the 5700s bound, always.**
>
> If per-attempt resolution is wanted, add a **new** key — `attempt_started_at`,
> `attempt` — so the board can say *"second go, 6 minutes in"* while the outer clock is
> untouched. **A new key, never a reset.**

## 3c · ⚠️ A CORRECTION WORTH MAKING EXPLICITLY: DO NOT USE "IS THE PROCESS ALIVE"

It is tempting to prove the commission is working by asking whether the child process
exists, or whether there is API traffic. **Do not.** This repo has already paid for that
lesson twice:

- `CLAUDE.md` fault #1 — *assert the artefact, not the thing that reports on it.*
- the checkpoint, 8 Aug: *"`engine_pid()` asks whether the pid is alive, and a frozen
  process IS alive"* — pid 87536 was **suspended** by Modern Standby and the supervisor
  reported "running — would do nothing", and would have done so for ever.

**A live pid is a proxy. The bound is not.** The commission is bounded, `subprocess.run`
will time out and raise, and `commission()` turns that into an operator-shaped halt.
**The right signal is the budget the step is genuinely allowed** — §3a — and nothing else.

📌 **The honest alternative, and it is a CUT for now:** real movement would mean
`Popen` + streaming the child's stdout so the engine can see turns landing. That is a
genuine change to `commission.py`'s shape, it buys nothing Jodie can act on, and it
should not ride along with this landing. **Named so nobody thinks it was overlooked.**

---

# 4 · CONTROL-FIRST PROOFS — every one starts RED

> **`CLAUDE.md` 4b, Jodie's ruling of 8 Aug: a guard is not trustworthy until you have
> watched it FAIL. Write the failing case FIRST, watch it go red, then write the passing
> one.** And 🚫 **do not draft these ahead of being able to run them** — write them fresh
> when the freeze lifts, against real data.

## P1 · RED FIRST, ON TODAY'S CODE — the render gate opens after the commission

**Before changing anything**, write the assertion and watch it fail. Use EP19's real
`build_state` shape:

```
GIVEN  build_state.order.render_offered_at
  AND  build_state.steps.audit_inputs.at
ASSERT render_offered_at < audit_inputs.at
```

**On EP19's actual run this is FALSE** — `render_offered_at` is `04:13:50`,
`audit_inputs` completed `04:13:47`. **That failure is the control.** A test that has
never been seen red is not evidence the test works.

## P2 · STATIC — the order, and the guard that protects it

New `engine/test_locked_order_render_first.py`, in the shape of
`test_step_call_sites.py` (which walks the real dispatch rather than grepping source —
**fault #1a: read the syntax tree, not the text**):

1. `PHASES["building"].index("render_gate") < PHASES["building"].index("audit_inputs")`.
2. `PHASES["building"].index("script_sync") == 0` — the render is never offered on
   unread text.
3. 🔴 **THE FAILING CONTROL:** monkeypatch `PHASES["building"]` back to the OLD order
   and assert `check_locked_order()` **returns the new problem**. *A guard that has only
   ever been watched passing is not a guard.*
4. And the other direction: with the NEW order, `check_locked_order()` returns `[]`.

## P3 · THE BOARD — what a human actually receives

New cases in `test_board_watchdog.mjs` (or a sibling `.mjs` in the same style — it drives
`app.js`'s real functions in a `vm` sandbox and reads no source):

```
check("the render gate is offered before the cards are written", …)
```

Row: `status: "building"`, `heygen_name: "PP-EP20 — …"`, `render_started_at: null`,
`script_snapshot` non-empty, **`build_state.steps.audit_inputs` ABSENT**.

- `gateFor(ep)` returns the render gate;
- `showsScript(ep)` is `true` and `gateRender(ep)` carries the whole script to paste;
- both Copy buttons are present (the project name AND the script — stop 5, 3 Aug 2026).

**Today's board already does this correctly.** The case exists to pin the surface so the
reorder cannot break the thing it was done for.

## P4 · RED FIRST — a row 100 minutes into a commission

Two cases, and **the first must be run against today's `app.js` and go RED**:

```
check("a row 17 minutes into audit_inputs is NOT stuck", …)
   { step: "audit_inputs", started_at: 17 min ago, budget_s: 900 }
   -> stepState().state === "stuck"        // TODAY. This is EP18's real shape.
```

That is the proof the board genuinely says it, rather than my reading of the code.
Then, after §3a:

```
check("a row 100 minutes into a commission is not called stuck", …)
   { step: "audit_inputs", started_at: 100 min ago, budget_s: 5700 }
   -> state === "working",  and the stage line reads the honest label
```

## P5 · 🔴 THE FAILING CONTROL FOR THE WATCHDOG — WITHOUT IT THIS IS A SWITCHED-OFF ALARM

```
check("a commission past its own bound is STILL stuck", …)
   { step: "audit_inputs", started_at: 120 min ago, budget_s: 5700 }
   -> state === "stuck"
```

**A bigger budget that never fires is not a fix, it is a deletion.** And keep the case
that stops it regressing the other way: `budget_s: null` (`heygen_download`,
`cover_pick`, `render_gate`) must return `"waiting"`, **never** `"stuck"`, however long
it runs. That case already exists in `test_board_watchdog.mjs` — do not break it.

## P6 · THE ARTEFACT, ON THE NEXT REAL EPISODE — and this is the only proof that counts

Not a test. **From the run log, on EP20:**

```
[hh:mm:ss] claimed PP-EP20 (…) -> building
[hh:mm:ss] -- step script_sync
[hh:mm:ss] -- step render_gate
[hh:mm:ss] >> RENDER GATE OPEN — start Gordon's render for 'PP-EP20 — …' NOW
[hh:mm:ss] -- step audit_inputs          ← AFTER the gate, not before
```

**The number to report is `RENDER GATE OPEN` minus `claimed`. It should be under
twenty seconds.** *(EP18: 1034s. EP19: 1913s.)*

⚠️ **And name the case, never a pass count.** `CLAUDE.md` fault #4: a green suite that
does not name what you changed is not evidence about it.

---

# 5 · RISKS, AND WHAT DOWNSTREAM ASSUMES

## 5a · 🟠 THE REAL TRADE — HUMAN TURNS 2 AND 3 STOP BEING BACK-TO-BACK

**Name this loudly, because it is a genuine change to the shape Jodie approved in July**
and a fresh instance must not "fix" it back.

| | turn 2 (render) | turn 3 (cover pick) | apart |
|---|---|---|---|
| EP19, today | `04:13:50` | `04:16:03` | **2m 13s** |
| after this change | ~`T+10s` | ~`T+24m` | **~24 min** |

`covers_ab` reads the cover wording out of `episode.json`, so it **cannot** move in front
of the commission. The old order's *"human turns 1-2-3 cluster at the front"* becomes
**turn 2 at the front, turn 3 inside the render window.**

**That is the right trade and it is what was approved** — the render starts 17–32 minutes
earlier, the cover pick still lands well inside a 5–45 minute render window, and Jodie is
no longer sitting looking at nothing. **But it is one more context switch for her, and it
should be said out loud rather than discovered.**

## 5b · A render can now FINISH before the build phase does

New and real: a fast render (5 min) can complete while the commission is still running
(22 min). The master then **sits in HeyGen** until the engine walks out of `building` and
reaches `heygen_download`.

**Nothing breaks.** `run_phase`'s building→rendering transition (`engine.py:1091`) reads
`render_started_at` at the END of the phase, and `step_heygen_download` polls until the
master is there. **`_master_landed`'s order warning does not fire** — it checks
`covers_ready_at`, which is stamped in `covers_ab`, still inside the building phase.

⚠️ **But the board will read "building" while the render is already done**, which is
honest but not obvious. **Do not fix it in this landing.** Log it as a follow-on if it
actually bothers her on EP20 — *take an item off the list against a real fault in a real
episode* (fault #8).

## 5c · The script could still change after a render has started

**This is the one genuine downside.** Today `audit_inputs` is the last checkpoint before
any spend; after this change the HeyGen spend starts ~22 minutes earlier.

**Assessment:** the script is *locked at the words gate by design*, and changing it
already requires the deliberate "Unlock and re-approve" path (`1249c26`, scoped narrowly
by ruling). **No `episode.json` fault can change a word Gordon says**, so the class of
failure that *would* waste a render is exactly the class that is already gated behind a
human decision. **Name it as a known limitation; do not build around it.**

## 5d · Downstream — everything that reads these fields, checked

| reader | effect of the reorder |
|---|---|
| `engine.py:673` — `step_broll_submit`'s `order_warn` if `render_offered_at` is unset | **improves.** Under the new order it is always set by then; the warning becomes unreachable in the normal path, which is what it wanted. |
| `engine.py:733` / `852` — the covers/master order warnings | **unaffected.** Both compare `covers_ready_at` against `master_at`, neither of which moves. |
| `engine.py:1091` — building → `rendering` vs `awaiting_render` | **improves.** Jodie now has ~22 extra minutes to press *"I've started the render"*, so the `awaiting_render` park (an order breach the engine names out loud) becomes rare. |
| `app.js:1144` `showsScript()` / `1158` `gateFor()` | **unaffected — and this is the whole point.** Both already key on `heygen_name && !render_started_at` under `status === "building"`. **The board needs no change to surface the render earlier; it will simply surface it sooner.** |
| `providers.py:1931` — finding the finished render by `heygen_name` | **unchanged risk.** The title is final at the words gate, so this changes *when* the name is written, not *what*. The deeper fault — **finding a paid render by NAME instead of storing its id (E20, `CLAUDE.md` fault #0a)** — is untouched and is **not this piece.** ⚠️ It gets sharper as "Part 1 / Part 2" episodes arrive. |
| `engine.py:1643` — the mock ticket's pre-set `render_started_at` | **unaffected.** Still needed so `run --mock --watch` exercises the spine past the gate. |
| `test_script_on_rail.py:404` | asserts both field names appear; **unaffected.** |

## 5e · The mock path

`python engine/engine.py run --mock --watch` must still walk the whole spine. The mock
ticket pre-sets `render_started_at`, so the reorder changes only the order of two log
lines. **Run it, read the log, `cleanup-mock` after.**

---

# 6 · OPTIONAL, AND IT MAKES THE WIN MEASURABLE — `words_approved_at`

**The audit had to BOUND the headline number rather than measure it** (`≤30s` from the
click, inferred from the 30-second idle poll), because **the moment Jodie clicks
*Approve* is not recorded anywhere.**

**One column, one board write:**

- migration: `alter table episodes add column words_approved_at timestamptz;`
- `app.js` — the `approve-words` handler (`app.js:1649`) already writes a patch object:
  ```js
  const patch = {
    title, hook: val("hook"), byline: val("byline"),
    script_read: true, title_approved: true,
    words_approved_at: new Date().toISOString(),   // ← the only new line
  };
  ```
- then the number is a query: `render_offered_at - words_approved_at`, per episode, for
  ever.

> **Set it ONLY on the transition to approved, never on a re-save**, or it becomes a
> "last touched" field wearing an approval's name — and `SCHEMA.md` gets the sentence
> saying so.

⚠️ **Genuinely optional, and it is the LAST thing to do, not the first.** It changes the
schema, and the standing rule here is that `build_state` jsonb absorbs anything that does
not need a column. **This one does need a column** — it is a fact about the episode's
history, not about a build — but it earns its place only because *"how long from her
click to the render being startable"* is now the number this studio is managing. **Land
§1–§4 first; add this when someone wants the second data point.**

---

# 7 · THE ORDER TO BUILD IT

1. **P1 and P4's first half — RED, on today's untouched code.** Watch both fail. *(4b.)*
2. **§3a** — the derived budget. One line, plus the shared constant.
3. **§3b** — the label hook and the two sentences.
4. **P4 second half + P5** — green, **and the 120-minute failing control.**
5. **§1a + §2b** — the reorder AND the eighth assertion, **in the same commit.**
6. **P2, P3** — static and board, both directions.
7. **§1b–§1d + §2a** — the docstring and the four prose homes, written once and copied.
8. **§5e** — the mock walk, read out of the log.
9. **P6 on EP20 — the only proof that counts.** Report
   `RENDER GATE OPEN − claimed`, from the log, as a number.
10. **§6** — only if wanted.

**Commit message goes in a FILE** — `git commit -F <literal absolute path>`, never `-m`.
This studio's prose is made of apostrophes and quoted phrases, and `-m` has broken twice
on exactly that (`CLAUDE.md`, command hygiene, class 7).
