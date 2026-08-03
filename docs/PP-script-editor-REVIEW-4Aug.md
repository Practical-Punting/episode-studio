# Script editor — design review, 4 August 2026

**Read-only review of the board and engine as they ACTUALLY ARE, plus a counter-proposal.**

> **DIVISION OF AUTHORITY (agreed 4 Aug).** This document is authoritative on **WHAT THE
> CODE IS**. The build plan stays the single plan and points here for the evidence.
> Where they disagree about the code, this wins; where they disagree about what to
> build, the plan wins.

*Written here rather than at `claude/…` because that is a Cowork project namespace, not
a filesystem path — only `Jodie-Cowork/context` exists on disk. The repo is version
controlled and diffable, which a design review should be.*

---

## 0. THE BLOCKER — the board destroys itself every 30 seconds

```js
setInterval(() => { if (SESSION) loadAll(); }, 30000);   // app.js:1196
host.innerHTML = out;                                     // renderBoard, ~app.js:491
restoreDrafts();                                          // restores .value ONLY
```

Every 30 seconds the whole board is rebuilt from HTML strings; `restoreDrafts()` puts
the **values** back and nothing else. Lost each cycle:

| | |
|---|---|
| caret position | `restoreDrafts()` does `i.value = v`, which forces the caret to the end |
| selection | gone with the node |
| scroll position inside the field | gone with the node |
| **browser undo stack** | **gone — undo does not survive node replacement** |

**Consequences for the plan.** A 15 KB textarea inside a card is unusable: type for
thirty seconds and the caret jumps mid-sentence. **And "browser undo covers the version
history" is not merely weak, it is already false today.**

**This is the root of the whole class.** C1's disappearing publish inputs, the harvest
skip-list, the `UI.drafts` / `UI.words` maps — all of it is scaffolding around one global
re-render. The editor should not extend that scaffolding; it should live outside it.

---

## 1. The estimate — 3-4 working days, not one evening

The board has **no component model**: string-templated `innerHTML` with a global rebuild.
Adding a long-lived, focus-holding, autosaving surface is an architectural change.

| Work | Est. |
|---|---|
| `script_versions` table, migration, RLS | 0.5 d |
| **Editor surface outside the render loop** | **1 d** — the real work |
| Dedicated writer: no `loadAll()`, queued trailing save | 0.5 d |
| Autosave + save-failure UX on a flaky line | 0.5 d |
| `script_sync` rewrite, `spoken-words.txt`, untangle `approve-words` | 0.5 d |
| Rewrite-invite (proposals, not overwrites) | 0.5 d |
| **Board bug 5 + B7** — neither optional | **1 d** |

---

## 2. The five questions, answered from the code

### 2.1 Does a full-height takeover panel fit how cards render today?
**Not inside a card** — it would be destroyed every 30s. **But there is a simpler shape
than surgery on `renderBoard()`:** `route()` (app.js:337) already shows and hides
top-level panels (`#login` / `#board`). **Add `#script` as a third sibling.** The poll
only touches `#lanes`. The editor becomes a **route, not an overlay**, and the card
renderer does not change at all.

### 2.2 Is the write path sane for 15 KB on a ~3s debounce?
**No, for two independent reasons** (`writeEpisode`, app.js:942):

1. It ends with **`await loadAll()`** — a full refetch of every episode *and* every
   message, plus a full rebuild. **Every 3 seconds while she types.**
2. `if (inflight.has(k)) return false;` — a concurrent save on the same key is
   **discarded, not queued**. Correct for a double-clicked button; for autosave it is
   **silently lost keystrokes**.

The editor needs its own writer: no `loadAll()`, last-write-wins, **one queued trailing
save**.

### 2.3 Does the C1 dirty-field guard protect a `<textarea>`?
**Yes** — `querySelectorAll("input[id], textarea[id]")` (app.js:922), covered by the
skip-list inversion. **But only the value.** It has never been exercised near 15 KB, and
it preserves the text while losing the place. See §0.

### 2.4 What is keyed on `script_doc_url`, and what breaks when it is never set?
| Where | What |
|---|---|
| app.js:656 / 677 / 720 | Words Gate renders the link and an input for it |
| **app.js:1009** | **`approve-words` writes `script_doc_url` + `script_read` + `title_approved` in ONE write** |
| providers.py:1235 | `_doc_id()` — flags "No script Doc is linked" |
| engine.py:1038 | mock fixture |

**The snag is app.js:1009** — approval and the Doc URL are the same write, and must be
untangled or approval breaks. **The reassurance is that `script_doc_url` is NOT in
`assert_script_gate()`** (engine.py:124), which checks only `title_approved` and
`script_read`. **Removing the Doc does not weaken the gate.**

### 2.5 What does `script_sync` do today, and what is left?
```
assert_script_gate()                    STAYS
fetch_script()                          GOES  ← the only Doc-shaped line
words = len(text.split())               STAYS
script_snapshot / script_sha256         STAYS — becomes a FREEZE of stored text
script_approved_at / script_locked_at   STAYS
script_changed_since_approval = False   STAYS
stamp("script_synced_at")               STAYS
```
⚠️ **One thing hides inside `fetch_script` and must not be lost: it writes
`docs/spoken-words.txt`** (providers.py ~1287). Jodie's decision 3 depends on that file,
and `render_ready` runs against it at `audit_inputs`.

**The new step:** assert gate → read approved text from the rail → **write
`spoken-words.txt`** → hash, freeze, stamp. Genuinely "check + freeze".

---

## 3. The standing furniture — VERIFIED, and there is a hole

All checks live in `render_ready.py`:

| Furniture | Check | If missing |
|---|---|---|
| No numerals / symbols | rules 1 + 2 | **hard fail** ✅ |
| Midroll freshness (9-episode window) | rule 3 | **hard fail** ✅ |
| Length | rule 4 | warn only |
| **Responsible-gambling line** | **NONE** | **🔴 IT SHIPS** |
| **Sign-off, e-book CTA** | **NONE** | **🔴 IT SHIPS** |

The responsible-gambling line exists only in the **warranty slide**, a separate standing
asset. `qc_episode.py` does not check the spoken track either. **Today the only thing
preventing an episode shipping without its mandatory line is that Claude writes it and
Jodie reads it.**

**A free-text editor makes deleting it one keystroke.** This is
`a-gate-that-invites-an-edit-must-verify-it` exactly, so the check is a **blocking
dependency of the editor**, not a follow-up.

### 3.1 Has it already been missed? — measured on the SHIPPED CAPTIONS

| EP | measured | resp-gambling |
|---|---|---|
| 01 | txt only (no `.srt`) | **ABSENT** |
| 02 | txt only (no `.srt`) | **ABSENT** |
| 03, 04, 05 | `output/*-FINAL.srt` | **ABSENT** |
| **06 → 15** | `output/*-FINAL.srt` | **present, 10 of 10** |

**The boundary is clean at EP06** — that is where the standing outro began, so this reads
as a policy start date, not a regression. **The check has never once failed since the
rule existed.** EP01/EP02 have no shipped captions, so their verdict is weaker than the
rest. **Whether the five pre-standard episodes matter is Jodie's call, not a bug.**

> ⚠️ **THIS TABLE IS THE THIRD ATTEMPT AND THE FIRST TWO WERE BOTH CONFIDENTLY WRONG.**
> v1 globbed `PP-EP1*` and measured EP01 against **EP10's folder**, reporting "NONE
> missing". v2 fixed the folders and then picked the wrong FILE — the early episodes use
> `gordon-spoken-words-epN-verbatim.txt`, and **EP05 keeps its outro in a separate file**
> — reporting EP02-EP05 missing. Both produced a clean table.
> **Only going to the artefact a viewer received — the shipped `.srt` — gave a stable
> answer.** [[assert-the-artefact]]
> *(The same globbing flaw is in `episode_dir()` in the test suites, written that
> morning for exactly this class of problem: `PP-EP1*` matches `PP-EP10`. Noted, unfixed.)*

### 3.2 The check to build
In `render_ready.py`, alongside rules 1-3, **HARD FAIL**:
- the responsible-gambling line, **word-for-word**, punctuation-normalised only
- a sign-off marker (`see you soon`)
- an e-book CTA marker
- **and "this video", never a bare "this", at every ask** (§4E, already a written rule
  with no mechanism)

---

## 4. THE SERVICE ACCOUNT IS CANCELLED — I was wrong, evidenced

I claimed it was still needed "for the e-book and cover assets on Drive". **It is not.**
Every Google reference in the engine:

| File:line | What |
|---|---|
| `engine.py:1038` | a mock fixture string |
| `providers.py:1246` | an error message |
| **`providers.py:1262`** | **`fetch_script`'s export URL — the ONLY network call** |

Everything else reaches Drive through the **mounted filesystem**,
`PP_VIDEOS = Path(r"G:\My Drive\PP Videos")` (`engine.py:50`), and covers publish to
**Supabase storage** (`_publish_asset`, providers.py:1579).

> **When the Doc goes away, ZERO Drive API calls remain.** The service account is
> cancelled and the plan's line stands.

---

## 5. Counter-proposal

**Tier 1, in order:**
1. **The outro/furniture hard-fail in `render_ready`.** Ships first — it is live today
   and the editor widens it.
2. **`#script` as a route**, sibling of `#board`, outside the 30s poll.
3. **A dedicated writer** — no `loadAll()`, queued trailing save, explicit
   "saved / saving / SAVE FAILED — your words are safe in this box" state. *The only
   place real robustness is needed is a save failing on her line.*
4. **`script_versions`, insert-only, THREE restore points** — *what Claude wrote* ·
   *last approved* · *current*. **No diff view in tier 1** (looks essential in a spec,
   gets used twice).
5. **`script_sync` → check + freeze**, still writing `spoken-words.txt`.
6. **Untangle `approve-words`** from `script_doc_url`.
7. **Board bug 5** and **B7**.

**Two design answers, both resolving against the plan's uncertainty:**

**Version history is NOT optional — it is the price of autosave.** Autosave removes
undo, and the 30s rebuild had already destroyed it. Ship autosave without versions and
her only recovery is retyping.

**Approval-lock is right, and not on UX grounds.** Unlimited-edit-with-a-version-
indicator **reopens C6**, which Jodie closed on 3 Aug: *one shot at editing, then
approve, and the build uses what was approved.* What to add instead is an explicit
**"unlock and re-approve"** — a recorded, deliberate act creating a new version and
re-running `script_sync`. Not drift; her changing her mind, the same shape as the EP15
cover switch.

**The rewrite invite (proposals, never overwrites).** Once a human has edited, Claude may
only ever write a **proposal**: a new `script_versions` row marked `proposed_by:'claude'`,
surfaced as *"Claude has a suggested rewrite — compare / accept / discard."* **The live
text she is typing into is never touched**, so a proposal arriving mid-edit cannot lose
a word.

---

## 6. What this deletes

Moving the words onto the board removes a **category**, not a list: stop 2's 401, E6's
em-dash mangling, the sharing menu, fifteen scripts on public link-shared URLs, and the
service-account project entirely.

**What it does NOT remove:** the script is still the only artefact with **two authors**.
That is why the proposal mechanism and the version table are the load-bearing parts —
not the textarea.
