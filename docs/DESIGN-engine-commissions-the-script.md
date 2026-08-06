# DESIGN — the engine commissions the script

**Status: PRICED, RECOMMENDED, AND AGREED IN SEQUENCE. NOT BUILT. No code has been
written.**
*Written 5 August 2026 by Claude Code, from Jodie's question and a read of the engine.*

> **Jodie, 5 Aug 2026:** *"Could we fix that first step? That when I paste the url and hit
> the button 'Build episode' it takes the article and builds the script?"*

> # ⚠️ 6 Aug 2026 — **RULING A5 DELETES SLICE C. READ `PP-RULINGS.md` A5 BEFORE THIS FILE.**
> **The script is a field on the rail, not a Google Doc.** So **slice C — "the Doc leg,
> service account, create AND share at creation", 1.0 day — is DELETED, not absorbed**, and
> **§10 ("the Doc flow merges into this") is void.** The commission WRITES THE SCRIPT TO THE
> RAIL; the board edits it in a text box.
> **PHASE 1 IS THEREFORE ~2.0 DAYS, NOT 3.0** — this ruling made the work **smaller.**
> ⚠️ **Everything else in this document still stands**, and §4 (the typed verdict), §11 (the
> two missing skills) and §13a (the unreadable tables) are unaffected. **The service account
> is cancelled; do not build it.**

> ### 🔒 THE SEQUENCE IS DECIDED. **EP16 RUNS FIRST, UNCHANGED. THIS LANDS AFTER.**
> **PHASE 1 ONLY, THEN STOP.** `episode.json` is a different and harder job, and it now
> has a real acceptance test in E26's pre-flight — which is an argument for doing it
> SECOND, with the pre-flight watching, not for doing it at the same time.
> *This document does not change anything the engine runs, so it cannot compete with
> EP16's clean run. It exists because the analysis otherwise lived only in a conversation.*

---

## 0. THE NUMBER THAT DECIDES IT

**Phase 1 prices at ~3.0 working days. About 1.75 of those are already agreed** — the
script Doc flow queued as item 3 after EP16.

> # THE MARGINAL COST OF "THE MACHINE WRITES THE SCRIPT" IS ABOUT **1.25 DAYS**.
> ## TWO PROJECTS ARE ONE PROJECT.

The Doc flow's two open gaps are *"the CREATE is not automatic — a human makes the Doc"*
and *"the READ is anonymous"*. **If the engine commissions the script, the commission step
IS where the Doc gets created.** The create stops being separate work, and both halves
need the same folder-scoped service account. **Do not build the Doc flow separately.**

⚠️ **It is still not a one-day job, so the standing decision rule sends it after EP16.**
*Don't change two things when one of them is a test.*

---

## 1. "BUILDS THE SCRIPT" IS TWO ARTEFACTS, AND ONLY ONE OF THEM IS THE QUESTION

| artefact | measured size | who halts without it |
|---|---|---|
| `docs/spoken-words.txt` | 130 lines · ~3.6k tokens | `script_sync` — **this is what Jodie is asking for** |
| `docs/episode.json` | **815 lines · ~12.2k tokens** | `audit_inputs`, and everything that authors cards, cover, thumbnail, e-book |
| `output/<ep>-youtube.txt` | 113 lines · ~2.0k tokens | `save_youtube_copy` |

*(EP15's actual files. EP14's are 133 / 907 lines — the same shape.)*

**THREE HALTS IN THE SPINE ALREADY NAME CLAUDE CODE AS THE THING THAT FILLS THEM.** Not
as an aspiration — as the literal flag text a person reads on the board:

| where | what it says today |
|---|---|
| `providers.py` `audit_inputs` | *"Create-inputs are missing… **Claude Code writes these at the create step** (the create brain is Phase 4). Stage them, then clear this flag."* |
| `providers.py` `save_youtube_copy` | *"The YouTube title/description file is missing. **Claude Code writes the copy** per `docs/youtube-metadata-kit.md`… then clear this flag."* |
| `providers.py` `_doc_id` | *"No script Doc is linked to this episode… Paste its link into the words card on the board."* |

**The design was already written down. It was never wired up.** This document wires it up.

---

## 2. THE TWO SHAPES, AND WHY (a)

| | |
|---|---|
| **(a)** | the engine **invokes Claude Code headlessly** at the point where it currently halts, and waits for the script |
| **(b)** | the engine **calls an AI API directly**, with the standards rebuilt into a prompt |

### (a) wins, and the reason is fault #2 — one source of truth, or it drifts

**A writer must obey ~50,000 tokens of standards spread across eleven files**, measured:

| file | bytes | ≈tokens |
|---|---|---|
| `docs/PP-STANDARDS.md` | 68,992 | 17,248 |
| `.claude/skills/pp-episode-script/SKILL.md` | 37,353 | 9,338 |
| `docs/PP-EPISODE-JSON-SPEC.md` | 17,329 | 4,332 |
| `docs/youtube-metadata-kit.md` | 15,552 | 3,888 |
| `.claude/skills/pp-visual-standard/SKILL.md` | 12,140 | 3,035 |
| `docs/thumbnail-hero-registry.md` | 11,190 | 2,797 |
| `docs/midroll-line-pool.md` | 9,615 | 2,403 |
| `.claude/skills/pp-broll-brief/SKILL.md` | 8,870 | 2,217 |
| `docs/broll-registry.md` | 8,433 | 2,108 |
| `docs/PP-midroll-invitation-standard.md` | 5,509 | 1,377 |
| `docs/PP-episode-outro-standard.md` | 4,195 | 1,048 |

**(b) means copying that corpus into a prompt string.** The value then lives in two places
and the next edit to `PP-STANDARDS.md` reaches one reader. **That is the fault logged four
separate times in this repo.** (a) reads *the same files a working session reads*, so one
edit reaches both readers at once. **(a) is not merely more convenient — it is the
one-source-of-truth fix, and (b) is a fresh violation of it.**

**Secondary reasons (a) wins:** it already has tools (Read / WebFetch / Write / Glob),
a permission model, a spend ceiling and structured output. **(b) would mean building a
second Claude Code inside the engine** — an agent loop, a tool layer and a sandbox — to
end up somewhere worse.

### ⚖️ THE HONEST COST OF (a), which (b) does not have
**It adds a dependency on the CLI's authentication staying valid on that machine.**
An expired token is a new silent-failure mode, and *anything that waits must say it is
waiting*. **That is a flag to write, not a reason to choose (b).**

---

## 3. IS (a) POSSIBLE FROM THE ENGINE, IN FACT? — **YES, PROVED ON THIS MACHINE**

Not in principle. Observed, 5 August 2026:

```
claude -p "Reply with exactly the two words: HEADLESS OK" \
       --tools "" --permission-mode dontAsk --output-format json

→ {"is_error":false, "result":"HEADLESS OK", "num_turns":1,
   "stop_reason":"end_turn", "total_cost_usd":0.194965, "permission_denials":[]}
```

The CLI is installed at `C:\Users\jlral\AppData\Roaming\npm\claude.cmd`. It returns
**structured JSON carrying everything an engine step needs to decide pass or halt**:
`is_error`, `result`, `num_turns`, `stop_reason`, `total_cost_usd`, `permission_denials`.

### AND THE PLUMBING IS NOT NEW MACHINERY
`providers.py` already spawns work in exactly this shape, six times over — for
`author_cover.py`, `author_thumbnail.py`, `card_check.py`, `render_cards_batch.py`:

```python
r = subprocess.run([...], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=180)
if r.returncode:
    raise EngineFlag("…plain English…")
```

**Commissioning a writer is that call with a different executable.** The novelty in this
design is not the subprocess. It is §4.

---

## 4. 🔴 THE TYPED VERDICT — THE HEART OF THE DESIGN

**This is not an implementation detail. It is the whole safety argument.**

A commissioned writer returns a schema-validated object (`--json-schema`), not prose:

```jsonc
{
  "status":           "ok" | "halt",
  "what_i_saw":       "…",        // observation only
  "what_it_could_be": ["…","…"],  // list causes, ASSERT NONE
  "does_retry_help":  false,
  "unread_sources":   ["Table 1 (scanned image, could not be read)"]
}
```

> ## A WRITER THAT COULD NOT READ A SOURCE **MUST BE UNABLE** TO RETURN `ok`.
> **`unread_sources` non-empty ⇒ `status` must be `halt`. That is a schema constraint,
> not an instruction — the difference between impossible and unlikely.**

### WHY THIS IS THE CENTRE AND NOT THE EDGE

**Nothing we have checks fidelity to the article.** `render_ready.py` checks the spoken
track is renderable. `align_to_script.py` checks the transcript matches the script. **Both
judge the RENDER. Neither judges the WORDS against the source.** The `pp-episode-script`
skill's §0a and §9 fidelity pass are *craft instructions to the writer* — they are not
enforced by anything that executes.

**So the risk is not the wall. The risk is the quiet paraphrase.**

> **A headless writer that cannot read a scanned table does not necessarily stop. It may
> write smoothly around it** — and the result is a §0a breach (*"never add what the
> article does not say, and never remove or alter what it does"*) **that is invisible in
> the output, invisible to every checker we own, and reaches Jodie looking like a finished
> script.**

**The schema is the only thing standing there.** A `status` field the writer cannot set to
`ok` while `unread_sources` is non-empty converts an invisible failure into a visible halt.

### THE HALT'S WORDING IS ALSO FIXED BY THE SCHEMA
The three fields `what_i_saw` / `what_it_could_be[]` / `does_retry_help` **are the
CLAUDE.md fault-#6 template made mandatory**: *say what you saw · list what it could be,
asserting none · say plainly whether a retry helps.* A commissioned writer physically
cannot return a halt in the shape that misled Jodie on EP15's `cards_render`
(*"this is not a missing file, not a stale template, the content is simply too long"* —
a cause nobody had established, printed above its own disproof).

**The engine must also refuse a verdict it cannot parse.** An unparseable result is a
halt, never a pass. *(Fault #1: the exit code is a proxy; the verdict is the artefact.)*

---

## 4a. 🔴 THE ENGINE CAPTURES THE SOURCE. THE WRITER READS LOCAL FILES ONLY.
**(6 Aug 2026. §4 is the safety argument; this is what makes §4 true rather than hopeful.)**

> ### `unread_sources` AS DESIGNED IS SELF-REPORTED, SO THE SCHEMA BINDS THE **REPORT**
> ### AND NOT THE **REALITY**.

*"`unread_sources` non-empty ⇒ `status` must be `halt`"* is airtight **given a writer that
noticed.** A writer that never realises the page carried two JPEGs returns
`unread_sources: []` **honestly**, `status: ok`, and the schema is satisfied. **That is
fault #1 sitting inside the thing this design calls its whole safety argument** — the
verdict is a proxy for fidelity, and we would be asserting the proxy.

**§13a is the proof case and it is not hypothetical:** `WebFetch` refused EP16's article
outright, and the two tables the argument rests on exist **only as JPEGs**, on a page with
**zero `<table>` elements**. Nothing in the returned text says a picture was missed.

### THE DESIGN
**The ENGINE captures the source before it commissions anything** — raw HTML, plus **every
image the page references**, downloaded into the episode folder — and **writes a manifest of
exactly what it handed over.** The writer then reads **local files only**, and
**`WebFetch` comes OFF the tool list in §5.** The commission has no network at all.

> ## `unread_sources` STOPS BEING AN OPEN-ENDED SELF-REPORT AND BECOMES A
> ## **RECONCILIATION AGAINST A KNOWN LIST.**
> **Every manifest entry must be accounted for — read, or named as unread. Silence about an
> item the engine knows it handed over is a HALT, not a pass.**

**Same move as `check_page_images`: ask the artefact what it needs, rather than keeping a
list somebody maintains.** The coverage is derived from the page itself, so a source that
arrives with three tables next year cannot be silently skipped. **Fault #7's fix, applied
before the fault instead of after it.**

### WHAT ELSE IT FIXES, none of it the reason it exists
- **`WebFetch`'s copyright refusal stops mattering** — §0a needs the author's own sentences,
  and a summary cannot supply them. A local file is just a file.
- **The images become openable.** A picture in the episode folder can be looked at; a
  picture behind a fetch cannot.
- **The sandbox loses its network dependency**, which removes a silent-failure mode rather
  than adding a flag to describe one.

### ⚠️ WHAT IT DOES **NOT** FIX — named, not glossed
**The manifest proves HANDOVER, not COMPREHENSION.** A writer can open a scanned table,
fail to read a single figure off it, and still not list it as unread. **This closes the gap
where a source was never seen. It does not close the gap where a source was seen and
misunderstood** — that is the fidelity checker §13 puts out of scope, and it stays out of
scope. *The honest claim is that the invisible failure becomes a visible one, not that it
becomes impossible.*

---

## 4b. ⏸ PARKED 6 Aug 2026 — WHERE IT STOPPED, AND THE ONE LEAD NOT YET TESTED

**The relay is built, tested (80 cases) and OFF.** Five real dry runs against EP16's own
inputs; **none produced the artefact.** The writer returns PROSE instead of the typed
verdict and reports its write declined.

### ✅ WHAT IS ESTABLISHED (each one proved by a probe, not reasoned)
| | |
|---|---|
| the wallet | **Max subscription**, `claude.ai` / `firstParty`. Costs rate limits, not money |
| `--tools` vs `--allowedTools` | **different questions.** Without the second, the writer can READ and cannot WRITE |
| `--json-schema` | **works** — returns an object with exactly the five required keys |
| `--add-dir` reads | **work**, when named ABSOLUTELY |
| writing to a subdirectory | **works** |
| the exact argv from `build_argv()` | **writes the file and conforms** — with a SHORT prompt |
| the words themselves | **good.** Correct title with the bang, placeholder left, grounded in the article |

### 🔬 THE ONE LEAD, AND IT IS AN UNTESTED GUESS — DO NOT BUILD ON IT
> **The long multi-line brief is passed as an ARGV ELEMENT to `claude.CMD`, which is a
> BATCH SHIM, so `cmd.exe` re-parses it.**
> **Every short prompt works. Every long one does not.** That is the whole of the
> correlation, and a correlation is not a cause.

**Two cheap probes, in this order. Ten minutes. Neither has been run:**
1. **Pass the prompt on STDIN** instead of as an argument.
2. **Invoke the underlying script directly**, not through the `.CMD` shim.

⚠️ **A STDIN PROBE EXISTS IN THE SCRATCHPAD AND IT PROVES NOTHING.** It fed the prompt
through stdin and the file was written — **but the prompt it used had been truncated to 128
characters** by an argv capture that joined on newlines and split the multi-line brief into
separate elements. **It tested a short prompt through a second channel.** *Recorded because
a session reading "stdin probe: wrote the file" would take the lead as closed when it has
not been opened.*

🚫 **AND FOUR HYPOTHESES ARE ALREADY DEAD** — permission flags, `--json-schema`,
`--add-dir`, and the subdirectory write. **Do not re-derive them.** Parked at exactly this
point because disproving a fifth guess costs more than it returns; the next move is fresh
eyes, not more probes tonight.

---

## 5. PERMISSIONS — A PLACE AND A TIME, AND IT WAS MEASURED

> **Jodie's standing rule: a permission scoped to a PLACE and a TIME is safe. One scoped
> to a COMMAND PREFIX is not.**

### THE MEASUREMENT, 5 Aug 2026 — because a claim about behaviour is not evidence
A headless session was run in a sandbox folder with only the `Read` tool, and asked to
read one file inside that folder and one outside it.

```
permission_denials: [ { "tool_name": "Read",
                        "tool_input": {"file_path": "C:\\Users\\jlral\\repos\\episode-studio\\CLAUDE.md"} } ]
```

**The inside file was read. The outside file was refused, silently, without prompting —
and the refusal came back as machine-readable data the engine can log.** It also said so
plainly and did not attempt to route around it via a shell.

### THE SCOPE THIS DESIGN USES

| axis | value |
|---|---|
| **PLACE** | `cwd` = the episode's Drive folder; `--add-dir` the repo's `.claude/skills` and `docs` |
| **TIME** | one process per commission, spawned and dead — **no standing grant** |
| **TOOLS** | `--tools "Read,Write,Edit,Glob,Grep"` — **no Bash at all, and NO `WebFetch`** *(removed 6 Aug by §4a — the engine captures the source; the writer has no network)* |
| **CEILING** | `--max-budget-usd` — a hard currency cap per run |
| **MODE** | `--permission-mode dontAsk` (deny-by-default, no prompt) |
| **NEVER** | `--dangerously-skip-permissions` · `--permission-mode bypassPermissions` |

**There is no command prefix anywhere in this design.** It is a place and a time, which is
the rule exactly.

---

## 6. ⚠️ THE `--add-dir` CAVEAT — THE ONE PLACE THIS DOES NOT FIT THE RULE PERFECTLY

**Named here, in the design, and not in a footnote.**

The writer must READ the standards, and `--add-dir` grants **read *and* write** to the
directories it names. **There is no read-only variant.**

> ### SO A COMMISSIONED WRITER CAN, IN PRINCIPLE, EDIT THE STANDARDS IT IS JUDGED BY.

**The mitigations that already exist** — all three predate this design and none was built
for it:

| | |
|---|---|
| `git status --porcelain` | the skills and docs are version controlled; any edit is visible and diffable |
| `engine/gitgate.py` | already compares the working tree against HEAD (it replaced the two `.reference.py` integrity gates on 28 Jul 2026) |
| `_code_changed_exit()` | already watches `engine.py` / `providers.py` / `rail.py` mtimes and exits a flagged engine holding stale code |

**What none of them does is PREVENT the write.** They make it loud afterwards.

**The honest statement: this is a detection control, not a prevention control, and the
rest of the design is prevention.** It is the single weakest joint. Two candidate
hardenings, neither costed and neither recommended yet:
- copy the standards into the episode folder for the duration of the run (removes the
  grant entirely; costs a copy step and risks a stale copy — *one source of truth again*);
- assert the skills tree is clean against HEAD immediately **after** every commission,
  and halt if it is not (cheap, uses `gitgate.py`, still detection).

**Jodie should decide which, with the trade-off in front of her. It is not mine to pick.**

---

## 7. WHAT IS LOST IS THE RULINGS, NOT THE WORDS

**The words survive the move. The judgement does not.**

The `pp-episode-script` skill is 550 lines and unusually prescriptive — a voice bible for
Gordon, the golden rule, ten process steps, the craft reference, a QC checklist, a
hard-never list. **A one-shot run with that loaded produces a draft close to what a
conversation produces.**

📏 **ESTIMATE, AND IT IS A GUESS: ~85–90% as good on the words.** Grounded in reading the
skill against what actually happened on EP15 — not measured, because nothing has been run.

> ### BUT THE MISSING 10–15% IS NOT SPREAD EVENLY. IT IS CONCENTRATED EXACTLY WHERE
> ### RULINGS COME FROM.

**EP15's four, every one produced by a conversation and none of them in the skill:**

| what happened | what a headless run does |
|---|---|
| **Table 1 was a scanned image, and it was opened and read** | `WebFetch` returns text, not pictures. **It could not have looked at all.** |
| **Noticing this was Part 1 of TWO** (part two is each-way betting) | nothing in the skill asks; nothing on the rail records it |
| **The exclamation mark** — *"It is Roger Dedman's article and his title"* | a packaging choice made silently, with no ruling and no `test_bang_title.py` |
| **The 1988 "lady punters" aside** — reproduced in the e-book, not spoken | §0a says *flag it to Jodie*; headless there is nobody to flag it to except the board |

**A headless run produces no rulings. It produces a draft.** Those four became a written
standard, a test, a memory entry and a decision Jodie is still owed — and that only
happens in a conversation.

> ## THE GATE IS UNCHANGED. WHAT ARRIVES AT IT IS ONLY AS GOOD AS THE HALT.

Jodie still reads the script, edits it freely, and approves before a credit is spent.
**Only who carries the request across changes.** The cost of a slightly weaker draft is
her editing time, not a worse episode — **provided the odd bits reach her as a flag on the
board instead of as a surprise in the finished video.** That is §4's job, and it is why
§4 is the heart of this and not a detail.

---

## 8. ODD SHAPES — trace-or-halt with nobody to consult

**The skill already contains human gates.** They are not being imposed by this design:

- **Step 8:** *"Numbers get a **human tick** before the cards lock. Never animate a wrong
  number; never let Gordon narrate an unverified one."*
- **§0a:** *"If something looks wrong, **flag it to Jodie** and reproduce it as written."*

**A headless run cannot ask. So it must halt — and a halt is what happens TODAY anyway:
stop 1 IS a halt.** The change is not "a conversation becomes a wall". The change is that
a halt which used to be a person noticing becomes a halt the machine must raise itself.

**It is safe if and only if the halt is good**, which is §4, plus the operator-box rule in
`docs/PP-operator-box-rule.md`: the picture, the question, the buttons, nothing else.

⚠️ **The failure mode to fear is NOT the wall.** It is §4's quiet paraphrase. A wall costs
Jodie a click and a message. A paraphrase costs §0a and nobody finds out.

---

## 9. IT CLOSES THE YOUTUBE COPY TOO — same relay, one extra call

`save_youtube_copy` (`providers.py:1924`) is the same shape and the code says so out loud.
It is also **the cheapest place to prove the mechanism**:

- the artefact is small (113 lines);
- **an acceptance test already exists** — `check_youtube_title(d, hits[0])`, plus
  `engine/test_bang_title.py`;
- it sits at the END of the build, so a bad output costs a retry, never a render.

**One mechanism, three halts: stop 1 (the script), stop 3 (`episode.json`), stop 11 (the
YouTube copy).** With `ebook/body.html`, stop 10 as well. *Four of EP14's eleven stops were
always one missing thing; this is that thing.*

---

## 10. THE DOC FLOW MERGES INTO THIS

**The queued Doc flow (≈1.75 days) has two open gaps and this design closes both.**

1. **The CREATE is not automatic.** A human makes the Doc today. The commission step is
   the natural place for it — the writer produces the words, the engine files them.
2. **The READ is anonymous.** `fetch_script` uses the plain-text export URL, which is why
   every Doc must be *"anyone with the link can view"*, why fifteen scripts sit on public
   URLs, and why EP15 threw a 401.

> ### 🔴 AND THE CREATE NEEDS THE SAME CREDENTIAL AS THE READ, WHICH IS WHY THEY MERGE.
> **Recorded from EP15's 401: the Drive MCP can CREATE a Doc and READ one, and has no
> permission-creating tool at all.** So *"set the sharing at creation"* — EP14's recorded
> remedy for stop 2 — **assumes a capability that path does not have.** The MCP is also
> interactively authenticated, which makes it unreliable in a headless run regardless.

**⚖️ Jodie's ruling already points the right way:** revive the service account **for this
job and no other** — narrow, read-only where it can be, folder-scoped, and it **REMOVES
fifteen public URLs** rather than adding a capability. **It needs her clicks. Write her the
click-by-click guide, ONE STEP AT A TIME.**

**✅ Still ruled, still holds: NO SECOND DOC.** Google Docs keeps its own version history,
so version A survives the moment she edits, free, where she is already looking.

---

## 11. PREREQUISITE — TWO SKILLS EXIST BUT ARE NOT ON THE MACHINE

`pp-episode-script` instructs the writer to *"run the article through the
**`pp-signature-concept-finder`** skill"* (Step 2, where the hook comes from) and defers
Dave's definition to **`pp-my-audience-avatar`** (*"this skill defers to it and never
re-defines him"*). `PP-STANDARDS.md` names them too.

> **CORRECTION, Jodie 5 Aug 2026: BOTH SKILLS EXIST.** They live in her Claude account and
> Cowork can see them right now. **They are simply not on this machine** — no filesystem
> copy in the repo, in `~/.claude/skills`, or on the Drive tree.
> **The prerequisite is GET THEM ONTO THE MACHINE, not write them.** *(My first pass
> reported them as missing. They were missing from the machine, which is not the same
> thing, and the difference is a day of writing versus an hour of copying.)*

### HOW EVERY OTHER SKILL GOT HERE — the pattern to follow exactly
Established by commit `c7f4e77` (26 Jul 2026) and `6e42583`:

1. **The authoritative copy goes in the repo** at `.claude/skills/<name>/SKILL.md`,
   byte-for-byte identical to the original, verified by SHA-256 before the source is
   removed. It is then version controlled, diffable and reviewable.
2. **A rules-free SIGNPOST stub goes at user level**, `~/.claude/skills/<name>/SKILL.md`,
   because **Claude Code discovers project skills from the directory the session started
   in** — so a session launched anywhere else cannot see the repo copy.
3. **The stub carries no rules, deliberately** — *"a signpost that carries content is just
   a fork with better manners"* — and instructs the reader to STOP and say so plainly if
   the repo file is absent, rather than improvise.

> ### 🔴 WHY THIS MATTERS MORE FOR A COMMISSIONED RUN THAN FOR A HUMAN SESSION
> `c7f4e77`'s own message records the fault it was fixing: **the skill was NOT visible to
> a session launched from the repo, because it lived under `G:\My Drive\PP Videos\.claude`
> — so a script written in a normal session "would not have followed v1.2 at all, and the
> fidelity tightening we had just done would have been silently absent."**
>
> **A commissioned run starts in `G:\My Drive\PP Videos\PP-EP16`.** Walking up that tree
> it finds `G:\My Drive\PP Videos\.claude\skills\`, which today contains **one 669-byte
> signpost for `pp-episode-production` and nothing for `pp-episode-script`.**
> *(Checked 5 Aug: that file is a genuine signpost — "MOVED — this is no longer here",
> no rules, no summary. It is NOT drift, and it must not be reported as drift.)*
>
> **So the commission MUST pass `--add-dir` for the repo's skills tree, and the two
> incoming skills must land by the same route as the others.** Discovery-by-cwd is the
> exact fault that made this urgent once already.

**Cost: about an hour, and it is a hard prerequisite.** A dangling skill reference in a
conversation is something I notice and work around. **Headless, it is an instruction that
silently does nothing** — and the thing it silently skips is where the hook comes from.

---

## 12. THE PRICE — from reading the code, not from guessing

| | slice | days |
|---|---|---|
| A | `commission()` — subprocess, the JSON contract, the halt schema, the flag wording | 0.5 |
| B | `step_commission_script` at the head of the spine + writes `hook` / `title` / `byline` to the rail (**closes B7**) | 0.5 |
| C | **The Doc leg** — service account, create AND share at creation (**absorbs the queued Doc flow and stop 2**) | 1.0 |
| D | The board says *"the script is being written"* — **Bundle C's both-halves-or-neither rule** | 0.5 |
| E | Tests: a mock commission, `test_step_call_sites` coverage, one real dry run | 0.5 |
| | **PHASE 1 TOTAL — what Jodie asked for** | **3.0** |
| F | *(Phase 2, NOT NOW)* `episode.json` + `ebook/body.html` — E26's pre-flight is its acceptance test | 1.5 |
| G | *(Phase 3, NOT NOW)* the YouTube copy — reuses A entirely | 0.25 |

**Slice D is not optional and not cosmetic.** *"Closing stop 1 by silently writing scripts
would leave Hugh staring at the same 'read the script' card with no idea anything is
happening — the machine would be working and he would have no way to know."* **Bundle C
closes both halves or neither.**

### COST PER RUN — two measurements and one marked guess
| | |
|---|---|
| one-turn headless call, no tools | **$0.194965** (measured) |
| three-turn call reading two files | **$1.3698** (measured) |
| **a full script commission** | **GUESS: $10–30.** ~50k tokens of standards read, ~18k written, over many turns. **Not measured — nothing has been run.** |

**`--max-budget-usd` caps it hard, and the run can be pinned to a cheaper model.**
⚖️ *Recorded because it is useful information, never as an objection — the credit
conversation is had and approved, and cost is not an argument.*

---

## 13. WHAT IS DELIBERATELY NOT IN SCOPE

- **`episode.json` (Phase 2).** 815 lines against a 265-line spec. It is where E26's seven
  halts came from, **and E26's pre-flight is now its acceptance test** — which is the
  argument for doing it second, watched, rather than at the same time.
- **A fidelity checker.** Named in §4 as the real gap. Not built here; the schema makes the
  failure visible, it does not make it measurable.
- **Retrospective anything.** *A guard prevents recurrence — it does not oblige us to go
  back.* Nothing published is touched.

---

## 13a. 🔴 §4's CASE APPEARED ON THE VERY NEXT EPISODE, BEFORE THE THING WAS BUILT

**EP16's source article, read 5 August 2026 — one day after this document was written.**
*Logged here because a design's first real test arriving early is the most useful evidence
it will ever get, and it arrived by accident.*

**Both halves of the `unread_sources` argument fired at once, on a normal article:**

| what happened | which half |
|---|---|
| **`WebFetch` REFUSED to reproduce the article at all**, on copyright grounds — *"reproducing it verbatim would violate copyright"* — and offered a summary instead. **It is Practical Punting's own article, which the studio exists to republish.** | a summary is not the article; §0a needs the author's own SENTENCES and a summary cannot supply them |
| **The article's two data tables exist ONLY as JPEGs** (`19880310a.jpg`, `19880310b.jpg`). The page has **zero `<table>` elements.** `WebFetch` returns text; **it cannot see a picture.** | `unread_sources` — the writer cannot read the source and must not be able to say `ok` |

> ### AND THE ARTICLE'S PROSE IS UNINTELLIGIBLE WITHOUT THE PICTURES.
> The web text carries a paragraph beginning *"The straight-out price in **column 3** has
> been rounded up, so that any given combination in **columns 2 and 3**…"* — **which is the
> caption printed inside the image.** The transcription lifted the caption into the body and
> left the table behind. **A reader of the text gets a paragraph about three columns and no
> columns.**
> Worse, the article's central worked example — *"in fact **6-4 ON** is a reasonable price
> to accept for the place"*, and *"the best you can see eachway is **4-1**"* — **is one row
> of the other table**: `S = 5 · F = Evens · fair place odds 6–4 on · minimum acceptable
> each-way 4`. **Both quoted numbers come from a picture.**

**WHAT A HEADLESS RUN WOULD HAVE DONE, and it is exactly the fault §4 exists to stop:**
the prose reads smoothly without the tables. A writer that could not see them **would not
necessarily stop** — it would write around them, and the result is a §0a breach invisible
in the output and invisible to every checker we own. **That is the quiet paraphrase, not
the wall.**

✅ **WHAT AN INTERACTIVE SESSION DID INSTEAD, and it is the benchmark to beat:** noticed the
orphaned caption, fetched the raw HTML directly when `WebFetch` refused, **downloaded both
JPEGs and looked at them**, matched the article's numbers to a table row, and found six OCR
corruptions in PP's own transcription — `l/s` for `1/5`, `Vs` for `3/5` — each provable from
the article's own arithmetic. **None of that is in the skill. All of it is judgement.**

📋 **THREE THINGS THIS ADDS TO THE DESIGN, none of them costed here:**
1. **`WebFetch` is not sufficient to read a source article.** The commission needs a raw
   fetch it can hold verbatim, or the fidelity rule cannot be met.
2. **`unread_sources` must include IMAGES the page carries**, not only pages that failed to
   load. *An image the writer cannot open is an unread source even though the fetch
   succeeded.*
3. **A halt here is CORRECT and CHEAP** — it costs a flag before a credit is spent. The
   alternative is a script that reads beautifully and has quietly dropped the table the
   argument rests on.

---

## 14. THE OPEN QUESTIONS, NAMED RATHER THAN SMOOTHED

1. **Which `--add-dir` hardening (§6)?** Jodie's call, with the trade-off in front of her.
2. **The service-account clicks (§10).** Hers, and they need a click-by-click guide written
   one step at a time.
3. **The $10–30 per run is a GUESS.** It becomes a measurement on the first real
   commission, and it should be recorded when it does.
4. **~85–90% quality is a GUESS (§7).** It is a judgement from reading the skill, and it
   should be re-stated as a measurement the first time a commissioned draft is compared to
   a conversational one.

---

*Related: `docs/DESIGN-self-authoring-build.md` (the build authors its own ASSETS; this
authors its own WORDS) · `docs/PP-operator-box-rule.md` (what a halt may say) ·
`docs/PP-script-editor-REVIEW-4Aug.md` (the editor, queued after this) ·
`.claude/skills/pp-episode-script/SKILL.md` (the craft this commissions).*
