# The script editor — build plan
### 4 August 2026. Answers *"Why is this not simple?"* and *"What else needs planning before we kick it off?"*
### ✅ **ALL THREE DESIGN DECISIONS SETTLED BY JODIE, 4 August.** Nothing is left to be decided mid-build.

---

# ⭐ WHY IT ISN'T SIMPLE, IN ONE LINE

> ## **The editing is simple. A big box that saves what you type is an afternoon.**
> ## **What is not simple is that the script is the only artefact with TWO AUTHORS and TWO HOMES — and we have never said who owns the words at which moment.**
>
> **It becomes simple the instant we do: Claude Code writes them · Jodie owns them the moment she touches them · approval freezes them.**
> **Everything else is a textarea and a three-second timer.**

---

# ✅ THE THREE DECISIONS — SETTLED

## 1 · VERSION HISTORY LIVES IN A NEW TABLE — **"no schema changes" broken, deliberately**
A purpose-built **`script_versions`** table. One row per saved version. **Insert-only, never deleted** — matching the rail's standing rule.

*The standing rule exists to stop churn. A version history is a genuinely new thing, not churn. The alternative — versions inside `build_state` — would have dragged every version across the wire on every engine heartbeat, on a connection that already drops.*

## 2 · `script_sync` STAYS IN THE LOCKED ORDER — **its job changes, not its existence**
| | |
|---|---|
| **Before** | fetch from the Doc → check → freeze |
| **After** | **check → freeze** |

**Its real job was never fetching** — that was only how it got the words. Its real job is ***"the script is ready, and now it is frozen"***, and that survives whole. **The locked phase order is untouched. Nothing keyed on step names breaks.**

## 3 · 🚫 **NO GOOGLE DOC. AT ALL.**
> **Jodie:** *"If there is a txt file somewhere that I can have for other reasons then that is all I need."*

**There is, and it already exists for every episode:**
`G:\My Drive\PP Videos\PP-EP<NN>\docs\spoken-words.txt`
*EP15's is **14,307 bytes** — the full script including its header, byte-identical to what the build works from.*

> ### ⭐ **AND IT COSTS NOTHING TO KEEP.**
> **The engine already writes it every episode** — HeyGen needs it and the caption timing is built from it. **It survives the change for free.** No new work, no new write path, no decision to revisit.

### What this deletes outright
| | |
|---|---|
| **Stop 2 — the 401** | **gone.** Nothing reads a Doc, so nothing needs one shared |
| **E6 — em-dash mangling** | **gone.** No Drive create path for scripts at all |
| **The service account** | **unnecessary.** Its only job was reading a Doc |
| **The sharing menu** | **gone from the operator guide** |
| **Fifteen scripts on public URLs** | **stops growing** *(the existing ones remain her call)* |

---

# 🚨 THE THING THAT WOULD OTHERWISE WASTE THE EVENING

> ## **THE EDITOR IS ONLY HALF THE CHANGE.**
> ## **Claude Code must stop writing the first draft into a Doc and write it into the RAIL.**

**Build the panel alone and you get a beautiful editor for something that still arrived by the old route.** Every problem it was meant to delete would survive it.

**It pairs exactly with B7**, from Jodie's own observation that she retyped a hook and byline the machine already knew. **One change: Claude Code writes the SCRIPT, the HOOK, the TITLE and the BYLINE straight into the rail.** Two list items, one piece of work, and the Words Gate arrives filled in.

---

# 🔗 SEQUENCING

## BEFORE — one small thing
**FLUSH THE LANDING QUEUE.** `docs/landing-queue/` holds two patches against the frozen files (E11's guard, E16's prompt-hash keying). **Land them, one restart, one proof pass**, so the editor is built on a clean base.

*E15 — self-host the fonts — is **not** a dependency, but it is small, it deletes a whole class of failure, and doing it first costs nothing.*

## WITH — two things that must ship alongside
**BOARD BUG 5 — "SEND IT BACK A STAGE."** Approval locks the script. **A lock with no way back strands her on the first typo spotted afterwards**, exactly as EP15's title did. **The lock and the way back are one feature.**

**B7 — Claude Code writes into the rail.**

## AFTER — safe to leave
Tier 2 comfort · Tier 3 *(cut)* · retiring the drift check.

---

# 🧊 THE THREE TIERS — build one, ship, then reconsider

| Tier | What | Size | Value |
|---|---|---|---|
| **1 · THE POINT** | Edit on the board · never lose it · Claude Code never clobbers it | **one evening** | **All of it** |
| **2 · COMFORT** | Typography, save-state indicator, counters | half a day | Real, but it works without |
| **3 · NICE-TO-HAVE** | Contents rail, find-within-script | open-ended | **CUT BOTH** |

**FIND — cut.** In a real `<textarea>` **the browser's Ctrl+F already works.**
**CONTENTS RAIL — cut from v1.** Needs a parser that will drift from the script format. **2,500 words scrolls fine.**

---

# 🔴 THE TWO THAT ARE GENUINELY HARD

## 1 · APPROVAL LOCKS THE SCRIPT — **the decision that removes the most complexity**
**Edit freely before approval — unlimited, which is BETTER than today's one shot.** Press approve and it freezes.

**It deletes an entire class of problem at a stroke:** no concurrent edit while the engine reads · no *"which version is being built"* · **no drift check.**

## 2 · WHAT HAPPENS WHEN A SAVE FAILS — **the only place real robustness is needed**
**Not theoretical: 59 rail transients in one evening, a nine-attempt give-up, fonts unreachable for hours. A save WILL fail mid-sentence.**

> ### **TEXT IS NEVER LOST BECAUSE A SAVE FAILED.**

| | |
|---|---|
| **Debounce** | ~3 seconds after typing stops. *15 KB every two seconds on a flaky line is chatter.* |
| **On failure** | **Retry with backoff, keep the text in the box, say so loudly.** Never silently revert — that is the C1 fault in a new hat. |
| **The indicator** | **Saving… · Saved 10:42 · ⚠️ NOT SAVED — still trying.** *Never a fourth state meaning "we don't know".* |
| **Leaving the page** | **Warn before navigating away** with anything unsaved. |

**And the standing rule on the two writers:** ***once a human has edited, the human's version is the truth.*** `script_edited_by_human_at` on her first save; **Claude Code may READ freely and must never WRITE** — if it thinks the script needs changing, it raises a flag and asks.

---

# 🛠️ WHAT TIER 1 ACTUALLY IS

| Piece | Effort |
|---|---|
| Full-height panel, real `<textarea>` — **70-char measure, ~19px, line-height 1.7, house colours** | small |
| Debounced autosave — *the C1 dirty-field guard already protects in-progress typing, proven 2 Aug* | small |
| Save-state indicator, three honest states | small |
| `script_versions` table, **boundaries only** — panel open, panel close, on approve, every ~5 min | small |
| "Back to what Claude Code wrote" — the first version, one click, always | small |
| `script_edited_by_human_at` + the engine guard | small |
| **Approval locks** — *ships with board bug 5* | small |
| **Claude Code writes into the rail** — *the half that is easy to forget* | small |

> **No new service, no API key, no model call. Ordinary board and rail work — and the hardest part already shipped on 2 August.**

---

# ✅ THE PROOF PASS
*Written before the build, because "all green means nothing unless the suite covers what you changed."*

1. **Type, alt-tab, wait through two refreshes, return — intact. Ten times.** *(The C1 test, on 2,500 words instead of a URL.)*
2. **Type, kill the network mid-save, keep typing, restore it.** *Nothing lost; the indicator told the truth throughout.* **The one that matters most.**
3. **Edit, close the panel, reopen — the edit is there.**
4. **Claude Code attempts to rewrite after an edit — refuses, raises a flag.**
5. **Approve, then try to edit — refused, with a clear route back a stage.**
6. **"Back to what Claude Code wrote" after fifteen edits — returns the original exactly.**
7. **Count version rows after 20 minutes — single figures, not hundreds.**
8. **Run a whole episode from a URL and confirm NO GOOGLE DOC IS CREATED AT ANY POINT** — and that `docs/spoken-words.txt` is still written as it is today. *If a Doc appears, the change is half done.*

---

# 🔗 WHAT THIS DECIDES ELSEWHERE

- **THE SERVICE ACCOUNT IS CANCELLED.** Its only job was reading a Doc that will no longer exist.
- **Stop 2 (the 401) stops existing.**
- **E6 (em-dash mangling) stops existing** — no Drive create path for scripts.
- **The drift check retires.**
- **Board bug 5 gains a second reason to exist.**
- **B7 is absorbed into this work.**
- **The operator guide loses the "share the Doc" step entirely** — one more paragraph gone, which is the measure of progress.
