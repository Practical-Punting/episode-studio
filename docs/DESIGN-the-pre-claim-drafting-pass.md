# DESIGN — THE PRE-CLAIM DRAFTING PASS

**The last hand-off: the engine commissions the SCRIPT.**
*Decided 7 August 2026 by Jodie, after both alternatives were written up and costed.
This document is the design. Nothing in it is built.*

> ## THE FINDING THAT SHAPED EVERYTHING BELOW
> ### THE ENGINE CANNOT REACH AN EPISODE THAT HAS NO SCRIPT.
> `rail.claim_next` (`rail.py:288-295`) refuses to hand out an episode unless
> **`title_approved` AND `script_read`** are true — in the Python pre-check **and** in
> the PostgREST filter. `script_read` means *"I've read the script"*, which presupposes
> a script exists.
>
> **All three proved commission call sites run inside `building`, after that gate. The
> script commission must run before it.** So this is **not** "a fourth call site of the
> same relay", and treating it as one is the mistake this document exists to prevent.

**Read first:** `PP-RULINGS.md` A5 (the script lives on the rail), A12 (approving is a
decision), A17 (the script editable before EP18) · `docs/PP-operator-box-rule.md` ·
`DESIGN-engine-commissions-the-script.md` §4, §4a, §13 · `CLAUDE.md` faults #2 and #7.

---

# 1. THE SHAPE — `_draft_watch()` IN THE IDLE BRANCH

**A pass inside the engine that is already running.** Not a second process, not a new
status.

```
cmd_run's idle branch (engine.py:1301-1313) — where acquire() returned nothing:
    _why_idle()          every 300s   — already there
    _stage8_watch()      every 600s   — already there
    _draft_watch()       NEW          — same place, same process
```

**For each episode that is `queued`, has no `script_snapshot`, has no `script_doc_url`,
is not flagged, and whose §4a capture is present: commission the script, seat it on the
rail, and STOP.** The human still reads it and still approves it.

### WHY THIS PLACE AND NOT A NEW ONE — the precedent is already in the file
**`_stage8_watch()` (`engine.py:1256`) iterates `rail.list_all()` and WRITES to episodes
it has never claimed**, from this exact branch, in this exact process. *Pre-claim work
by the engine is not a new idea here; it is an existing pattern with one user.*

And **`_why_idle()` (`engine.py:1099`) already prints, every five minutes:**
> `waiting on the Script Gate — PP-EP18: "I've read the script" not ticked`

**The engine already knows which episode is missing a script and says so. This design
turns that sentence into an action.**

---

# 2. THE INVARIANTS — cite these by number

## 🔴 I1 · IT NEVER CLAIMS, NEVER SETS A STATUS, NEVER TOUCHES `claim_next`.
The Script Gate's filter is not relaxed, not duplicated and not read. `assert_script_gate()`
is untouched.

> **The invariant that survives BECAUSE of this choice: NO STEP IN `PHASES` RUNS BEFORE
> THE GATE.** `PHASES` is reachable only through `claim_next`, and `_draft_watch` is not
> in `PHASES`. **A design that added a `drafting` status would replace that invariant
> with *"…except these"* — an invariant with an exception list, which is `CLAUDE.md`
> fault #7 pointed at a guarantee instead of a filename.**

## 🔴 I2 · `script_snapshot` IS WRITTEN ONLY WHEN IT IS EMPTY. NEVER OVERWRITTEN.
**This is the rule, not a precaution.**

**WHY IT CANNOT WAIT:** A17 puts a `<textarea>` on the board writing **this same field**.
A machine writing it while a human is typing is EP16's corrupted `script_doc_url` — *an
insertion at offset 17, a paste landing where the caret used to be* — with the whole
script at stake instead of a URL.

> ### AND THE RACE IS REAL, NOT THEORETICAL: THE COMMISSION TAKES MINUTES.
> Checking "is it empty" when the pass STARTS and writing when it FINISHES leaves a
> window minutes wide in which Jodie can type. **The check must be part of the write.**

**WHERE IT IS ENFORCED — and the choice of place is the design:**

| layer | what it does | verdict |
|---|---|---|
| **`rail.seat_script_if_empty(id, text)`** — a conditional PATCH whose filter includes `script_snapshot=is.null` (or empty) | the write **lands or does not land, atomically** | ✅ **THIS IS THE ENFORCEMENT POINT** |
| a Python `if` in `_draft_watch` | re-reads, then writes — the window survives | ❌ not sufficient alone |
| a DB trigger, like migration 005 | would also block **the human**, whose overwrite is legitimate | ❌ **wrong shape** |

**The atomic conditional PATCH is exactly how `claim_next` already wins its race**
(`rail.py:291-300`) — filters in the URL, one writer gets the row back, the loser gets
nothing. **Same pattern, same file, no new mechanism.**

⚠️ **STATED PLAINLY: this protects the HUMAN from the MACHINE, not the machine from the
human.** Jodie overwriting a machine draft is her call and always was. A17's textarea is
not constrained by I2.

📌 **`rail.py` is behind the git integrity gate** (`assert_committed`, `engine.py:87`), so
adding this function means a commit before the engine will start. Expected, not a surprise.

## 🔴 I3 · THE CAPTURE IS A PRECONDITION. THE ENGINE DOES NOT MAKE IT (v1).
The §4a capture — `PP Videos/docs/EP{nn}-source-article-*.md`, with its
`---- ARTICLE TEXT BEGINS/ENDS ----` markers — must already exist. **If it is absent the
pass does nothing and says so once**; it does not guess, and it does not fetch.

**The lookup already exists and needs no `episode.json`:** `_commission_episode_json`
globs `EP{nn}-source-article-*.md` under `self.pp / "docs"` (`providers.py:2390`).

🚫 **1b — the engine capturing the article itself (§4a: raw HTML, images, a manifest) —
is EXPLICITLY NOT IN v1.** It is designed and unbuilt, it is 1.0–2.0 days on its own, and
bundling it doubles the risk of the piece that matters. **Named consequence, not glossed:
v1 does NOT remove the human step entirely — somebody still makes the capture.** It
removes the writing of 1,500 words, which is the expensive half.

## 🔴 I4 · THE ENGINE RUNS THE GATE. THE WRITER NEVER SELF-CHECKS.
No `Bash`, no `--force`, no "I ran it and it passed". `DEFAULT_TOOLS` stays
`Read, Write, Edit, Glob, Grep`. **A report is not an artefact** — proved three times
over on 6–7 Aug, and the bounded repair loop built on 7 Aug (`commission_with_repair`)
applies here unchanged.

---

# 3. THE FIDELITY GATE — WHY A VERBATIM GATE IS THE WRONG GATE

**The e-book reproduces the article character for character. The SCRIPT is the article
REWRITTEN to be spoken** — reworded, restructured, with a hook, a midroll and a standing
outro. `author_ebook`'s gate would fail every good script and pass nothing useful.

**`PP-STANDARDS §0a` already states the right rule for the spoken track** — *every figure
traced, nothing corrected* — and **THE VIDEO SELECTS, THE E-BOOK REPRODUCES.** So this is
not a new standard. **It is §0a with nothing enforcing it.**

> ## 🔴 AND THE REASON THE OBVIOUS IMPLEMENTATION FAILS:
> ## `check_trace` KEYS ON `\d`, AND A SCRIPT CONTAINS NO DIGITS BY LAW.
> `render_ready.py` **hard-fails a bare numeral** in the spoken track (TTS wants words).
> Point the existing trace-or-halt at a script and **it finds nothing and passes every
> episode.** *This is the `check_trace` gate-completeness gap met from the other side,
> where it is not a gap but total.*

### THE PIECE THAT MAKES IT WORK ALREADY EXISTS AND IS PROVED
**`align_to_script.spoken_form()`** rewrites digits, money and percentages into the words
this studio speaks — `$224.60` → *"two hundred and twenty four dollars sixty"* — and it
exists deliberately as **ONE definition of "the same number"** so two implementations
cannot drift. `test_align_number_fold.py` is 43/43 green.

**Fold the ARTICLE, compare against the SCRIPT.** Reusing it is what keeps this from
being fault #2 with extra steps.

⚠️ **ITS COVERAGE GAP IS EXACTLY OUR SUBJECT MATTER.** `8-1` folds to *"eight-one"*, not
*"eight to one"*; `1/9` to *"one/nine"*, not *"one ninth"*. **Racing odds and fractions
are the highest-value figures in a Practical Punting article and the ones the fold gets
wrong.** Closing that is part of 2b, and **it is the same work that closes the
`check_trace` word-figure gap already on the standing list** — one fix, two gates.

### THE THREE PARTS, and only two are buildable

| | what it proves | verdict |
|---|---|---|
| **2a · declared-trace validation** | every trace the writer declares is a real article sentence and contains the figure | **cheap** — reuses `check_trace`'s substring + `digit_runs` shape |
| **2b · figure completeness** | every figure the script **asserts** is declared | **this is trace-or-halt.** Needs number-word EXTRACTION — the inverse of `int_words` — plus racing notation |
| **2c · claims** | every non-numeric assertion traces to the article | ❌ **not mechanically checkable, ever** |

> ### 2b IS WHERE THE VALUE IS. 2a WITHOUT 2b VALIDATES WHATEVER THE WRITER CHOSE TO
> ### DECLARE, WHICH IS NEARLY WORTHLESS.
> **If only one is built, build 2b.**

**2c stays a human read**, consistent with `DESIGN-engine-commissions-the-script.md` §13
putting a fidelity checker out of scope, and with the standing finding that **the gate
does not cover taste**. *A prose claim cannot be enumerated, so a "claims gate" could
only ever be the writer's own declaration — a report, not an artefact.*

### WHAT THE WRITER DECLARES
A script-side trace artefact — the parallel of `episode.json`'s `trace{}` — mapping each
asserted figure to its verbatim source sentence. **It is a FILE**, so
`commission._artefact_or_halt`'s mtime-freshness check works unchanged, and the engine
seats the words onto the rail afterwards under **I2**.

---

# 4. THE HALT, WHEN IT CANNOT PROCEED

**Every stop this pass can produce is a STUDIO halt, not an operator one** (ruling A19:
*a flag whose remedy names a file, a script or a step is not for the operator*). The
capture is missing, the writer could not be reached, the fidelity gate refused three
times — **Jodie can act on none of them.**

**So `_draft_watch` does NOT flag the episode.** It logs, once per pass, and leaves the
board exactly as it was: **the episode is still `queued`, still waiting on the Script
Gate, and `_why_idle` still says so in the words it already uses.**

⚠️ **This is deliberate and it is a v1 limitation, named:** until A19's second lane
exists, a studio-side failure here is **visible in the run log and invisible on the
board.** *Adding an orange badge to Jodie's queue for a job she cannot do is the fault
A19 exists to stop, and it is worse than the silence.*

---

# 5. FAILURE MODES — named, not glossed

| # | mode | mitigation |
|---|---|---|
| 1 | **a commission BLOCKS the idle loop**, so an episode approved mid-draft waits to be claimed | the honest cost of this shape. Fires only when nothing is claimable. **See §7** |
| 2 | no `build_state`, so a crash re-runs the draft | costs rate limits, not correctness; `_artefact_or_halt` already refuses a half-written file |
| 3 | two engines would double-commission | prevented by `_acquire_lock`, which already exists |
| 4 | a human types while the pass is running | **I2's atomic conditional write.** The draft is discarded, not merged |
| 5 | the writer paraphrases the article smoothly | **2b.** This is the one that matters, and it is the reason the gate is not optional |

---

# 6. COST

| piece | estimate | confidence |
|---|---|---|
| **A′ · `_draft_watch` + the pass** | **0.75–1.5 d** | high — no new spine, one call in an existing branch |
| **1a · capture as a precondition** | **~0.25 d** | high — the pattern exists verbatim |
| **2a · declared-trace validation** | **0.5–1.0 d** | high — reuses `check_trace` + `spoken_form` |
| **2b · figure completeness + racing notation** | **1.0–2.0 d** | **shared with the `check_trace` word-figure gap** |
| **3 · the commission itself** (brief, artefact, wiring) | **0.5–1.0 d** | high — the relay is proved three times |
| | **≈ 3.0–5.75 d** | |

🚫 **NOT in this total, deliberately:** 1b (the engine captures the source, 1.0–2.0 d) and
2c (not buildable).

**Proof plan — the same three legs that proved the repair loop on 7 Aug:** deterministic
tests with the injected runner · one real run on a **scratch** target · **the gate shown
ENGAGED in its own words**, never a bare "no blockers". **I2 gets its own case: a write
attempted against a NON-empty `script_snapshot` must land nowhere.**

---

# 7. SHAPE B — THE MEASURED FALLBACK

**A new `drafting` status the main engine claims before the gate.** Written up, costed
**1.5–3.0 d**, and **not chosen.**

**It is taken only if EP18's REAL NUMBERS show failure mode 1 bites** — i.e. the idle-loop
delay measurably holds up a build. **Never on argument.**

**What it would cost that A′ does not:** a DB migration against the CHECK constraint on
`status`; the 10-status contract in `SCHEMA.md`, currently labelled *unchanged*; `PHASES`,
`PCT`, `STEP_LABEL`; a second claim path; the board's four-lane map; the stale-heartbeat
rule; `reclaim_stale`; `_why_idle`. **And the invariant in I1.**

> **THE TRIGGER TO WRITE DOWN NOW, so the decision is not re-litigated from memory:**
> if a drafting pass delays a claim by more than a few minutes **on a real episode**,
> that measurement is the argument for B. **Anything less is a preference.**

---

# 8. AND SHAPE A, FOR THE RECORD — why a separate loop was refused

**A separate pre-claim process has A′'s exact safety property and forces a SECOND COPY OF
THE ENGINE'S SPINE:** its own lock (`_acquire_lock` writes `LOCK` unconditionally and
would clobber the real engine's pid), its own worker identity, a heartbeat (**a commission
runs minutes against a 180-second lease**), `Ctx`/`build_state`, `run_step` +
`flag_and_wait`, `_code_changed`, and `RailUnavailable` handling.

**"Import them instead of copying" does not rescue it:** `run_step` dispatches through
`STEP_FNS[name]`, and `flag_and_wait`/`_code_changed_exit` close over `WORKER` and `LOCK`.
Reusing them means registering the drafting steps in `engine.py` anyway — **at which point
the separate process buys nothing but a second lock, a second restart procedure and a
second thing to confirm from the log.**

*That is `CLAUDE.md` fault #2 at the largest scale available in this codebase, and it is
why A′ exists.*
