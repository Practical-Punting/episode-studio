# PP — RULINGS

**The decisions that GOVERN the build. Dated, in Jodie's words where we have them, each
saying what it supersedes.**

> ## 🔴 WHY THIS FILE EXISTS
> **The machine that implements our rulings could not see them.** They lived in a Cowork
> project — a place Claude Code cannot read — so every session began with a human
> re-typing the parts they remembered into a prompt. **The rules survived only as long as
> one person's recall.**
>
> *Found 5 August 2026, when Claude Code was asked to price work "per the ruling in
> `PP-RULING-the-script-lives-on-the-rail.md`" and could not find that file in the repo,
> on Drive, or in memory — because it is not in any place it can read.*
>
> **This repo is public by Hugh's ruling and Claude Code reads it on waking. That makes it
> the right home.** Standards live in `PP-STANDARDS.md`; this file holds the DECISIONS and
> their reasons, which is a different thing — a standard says what to do, a ruling says
> what was decided and why, and the why is what stops it being re-litigated.

⚠️ **HOW TO ADD ONE.** Date it. Quote her if you have her words. Say what it supersedes.
**Never write a ruling you cannot source** — put it in §9 instead and let a human confirm.

---

## 1. THE SCRIPT LIVES ON THE RAIL. THE SERVICE ACCOUNT IS CANCELLED.
**Jodie, 5 August 2026.**

The script is **a field on the rail, not a document.** The Google Doc leg is deleted
rather than repaired.

**SUPERSEDES:** the Script Gate's "the Doc is the script's ONE HOME" (26 Jul 2026) and
everything built on it — and **cancels** the folder-scoped Drive service account that was
queued to fix the anonymous read.

**What goes away with it, counted in the code — 24 references across `engine/` and
`app.js`:** EP15's 401 on a private Doc · the Doc-URL field corrupting itself on the board
· `script_changed_since_approval` drift-checking · the readable-Doc gate · the
link-this-Doc button · the em-dash mangling on create · the service account · **and a
human relaying a URL between two machines.**

> **Her argument, which beat the deferral: fixing those individually is most of a week and
> still leaves a Doc.**

⚠️ **`fetch_script` also writes `docs/spoken-words.txt`, and `render_ready` runs against
that file at `audit_inputs`. That must not be lost when the Doc leg goes.**

---

## 2. THE ARTICLE'S OWN HEADLINE IS THE TITLE.
**Jodie and Hugh, evening of 5 August 2026.**

> ### "As a general rule we do need to stick with the article headlines.
> ### Go with the article headlines more than anything else."

| slot | comes from |
|---|---|
| **TITLE / HOOK** | the source page's **headline, verbatim** — punctuation and all |
| **PART LINE** | **the only place a series is expressed** |
| **BYLINE** | the source page's own **standfirst** |

**SUPERSEDES:** the "a series name carries the title" provision added to `PP-STANDARDS`
§1a on the **morning** of 5 August 2026 and **reversed the same night**. No "unless"
clause — *an exception is how it comes back.*

**COST, recorded so it is not repeated:** it produced exactly one wrong episode. EP16 was
written, rendered, assembled and QC-passed as *"Squeeze Those Odds! — Part 2"*; its page
says *EACH-WAY BETTING FOREVER! (Part 2)*. **Caught because Jodie showed Hugh a thumbnail
at nine o'clock at night.**

> ### 🔴 HER ACCOUNT OF THE MISTAKE, WHICH IS THE USEFUL PART:
> ### "I was trying to make the part 1 and part 2 fit together — but that is not a thing."

⚠️ **It reaches backwards: "Hidden Aces — Part 1 / Part 2" (EP11/EP12) was the same
habit.** Published episodes stay exactly as they are.

⚠️ **`check_one_name` CANNOT enforce this.** It passed EP16 perfectly — title card, e-book
and YouTube title all agreed, **on the wrong name**. *A consistency check proves SAMENESS,
never CORRECTNESS.* Only the source page can do that, and nothing compares them yet.

**Related, still standing:** the exclamation mark stays — *"It is Roger Dedman's article
and his title"* (Jodie, 3 August 2026).

---

## 3. CARD ENTRY IS ANCHORED TO THE PHRASE.
**Jodie, 5 August 2026.**

> ### A card enters about **3 seconds after Gordon ACTUALLY SPEAKS the cue**.
> ### It must **never** appear before he has said the words.

**SUPERSEDES:** the CUE-BLOCK anchor, which EP11 shipped — timing from when the SRT block
*containing* the phrase begins. A phrase can sit deep inside a block that started up to
3.5s earlier, so that anchor puts cards up **before their own words**.

**Her reasoning:** *a card that appears before the phrase pre-empts the presenter, and the
few seconds of extra delay cost nothing.*

**Measured on EP16:** the two anchors differ on **all 13 cards, by up to 6.41s**.
*Jodie twice found EP11's cards "still early" (0.4 → 2.6 → 3.0) — that correction was this
ruling arriving three episodes before it had a name.*

**Consequence:** a beat must be long enough to hold `3.0s + the card's hold` **after** its
cue is spoken. EP16 found three beats that are not.

---

## 4. EP16 SHIPS AT 124 kbps. THE FLOOR DID NOT MOVE.
**Jodie, 5 August 2026 — decided by LISTENING, not by number.**

> ### "It sounds fine in the middle."

**A documented one-off, not a new normal.** The floor stays **180 kbps** everywhere it is
not explicitly overridden; EP14 and EP15 both measure 189.4.

**Why this episode:** the HeyGen API's rendition was **truncated** — 127,387,672 stated,
126,877,696 delivered, **exactly 121.0 MiB, twice, at the identical byte.** The web
download button returned a **complete** file first go. That file is a **different encode,
not a degraded copy**: video *better* at 2522 kbps against ~2200, audio worse at 124.4
against 189.4. **The choice was between a complete file and a better soundtrack, and there
was no third option.**

**MECHANISM — now the house pattern for exceptions:** `build.audio_kbps_floor` plus a
**mandatory** `build._audio_kbps_floor_why` in `episode.json`. The guard **refuses to
apply the exception without a reason**, and **a used exception prints itself into the run
log** so it can never look like a clean pass.

> **An exception that can exist without a written reason becomes a silent normal.**

---

## 5. AUTOMATION EATS CHORES, NEVER DECISIONS.
**Jodie, 26 July 2026 — the Script Gate ruling.** *(Sourced from `PP-STANDARDS.md` and the
`script-gate-decision-record` memory.)*

Approving the script is a **decision**; decisions stay human. Starting a render is a
**chore** and may be automated. **Human gates are sacred: never auto-render, never
auto-publish.**

---

## 6. §0a — WE REPRODUCE, WE DO NOT IMPROVE.
**Jodie, 27 July 2026**, with the scan-damage amendment **§0a-i, 5 August 2026**.

If Practical Punting made a mistake in 1995, it stands. **Three categories:** a *legible*
oddity survives; damage that has *destroyed meaning* is repaired **only** where the repair
is forced by the article's own arithmetic or sentences; anything **unprovable** stands
exactly as printed.

**And:** *THE VIDEO SELECTS, THE E-BOOK REPRODUCES.* Omission is not alteration — but a
dropped clause must appear verbatim in the e-book, and what remains must still read
honestly.

**And:** *THE SCAN IS THE ARTICLE.* A scanned table is reproduced as the scan, never
hand-transcribed.

---

## 7. A LIST OF EVERYTHING NOTICED IS NOT A PLAN.
**Jodie, 4 August 2026: "We had it working!"**

A 12–14 day programme was cut to ~3.5 days by one question: **which of these actually
caused a fault?** *EP15 halted nine times from three causes.* **Take an item off the list
against a real fault in a real episode, never because the list is long.**

---

## 8. FOUND RETROSPECTIVELY DOES NOT MEAN FIXED RETROSPECTIVELY.
**Jodie, 4 August 2026.**

When a new check finds an old fault in published work, the check's job is **the next
episode**. Log it, name it, move on. *"A machine that spends more effort proving itself
correct than making episodes has stopped being a studio."*

---

# 9. ⚠️ THE HOLE — rulings I believe exist and CANNOT SOURCE

**Listed, not reconstructed. Please fill these in or delete them.**

| suspected ruling | why I think it exists | where I looked |
|---|---|---|
| **`PP-RULING-the-script-lives-on-the-rail.md` itself** | quoted to me by name | repo, Drive, memory — absent |
| The **framing / MCU-vs-WIDE** ruling | EP15's run log says a ruling is owed once Jodie has watched the finished cut end to end; §1 above records the ratio but not her verdict | `PP-STANDARDS`, run logs — the verdict is not there |
| **"More motion graphics"** — the standing preference | recorded in EP15's run log as *"I would be happy with more motion graphics, but am happy with where we are"*, explicitly NOT yet resolved into more cards vs more movement | EP15 run log §5b |
| The **thumbnail hero** ruling | `thumbnail-hero-registry.md` and a `thumbnail-standard.md` exist on Drive but not in the repo | Drive only |
| **Who may clear a flag** | exists as a memory file, never as a repo document | memory silo only |
| **Retention** — cover A/B deleted on publish, rail rows never | same: memory only | memory silo only |
| The **"lady punters" / 1988 asides** decision | EP15's run log says it is still owed | outstanding |
| Anything ruled in **Cowork before 23 July** | the studio predates the repo | unreachable |

> ### THE SIZE OF THE HOLE, honestly: **I can source about eight rulings and I suspect at
> ### least eight more.** Two of the four this file was asked to start with — the script
> ### on the rail, and the article headline — **existed nowhere I could read until tonight.**
> **Assume anything not in this file is invisible to Claude Code, and therefore does not
> govern anything.**

---

*Standards: `PP-STANDARDS.md`. Faults and their evidence: `CLAUDE.md`. Worked examples:
`EP15-run-log.md`, `EP16-run-log.md`. This file is the decisions and their reasons.*
