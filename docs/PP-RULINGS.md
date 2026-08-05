# PP — RULINGS

**The decisions that GOVERN this studio, where the machine that implements them can read
them.** Dated. In Jodie's or Hugh's own words wherever we have them. Each entry says what
it **supersedes** and what it **does NOT cover**.

> ## 🔴 WHY THIS FILE EXISTS
> **Most of this studio's rulings lived in a Cowork project — a place Claude Code cannot
> read.** Every session therefore began with Cowork retyping the parts it remembered into
> a prompt, which means **our rules survived exactly as long as one machine's recall.**
>
> *That is how `PP-STANDARDS §1a` came to be written wrong on the morning of 5 August 2026
> and lived for a day — long enough to name, render and assemble an entire episode under a
> title nobody had chosen. It was caught because Jodie showed Hugh a thumbnail at nine
> o'clock at night.*
>
> **The repo is public by Hugh's ruling and Claude Code reads it on waking. That makes it
> the right home.**

**HOW THE THREE FILES DIFFER, so nothing lands in the wrong one:**
| file | holds |
|---|---|
| `PP-STANDARDS.md` | **what to do** — the rules the build follows |
| **`PP-RULINGS.md`** *(this)* | **what was DECIDED and WHY** — the reasoning that stops a rule being re-litigated |
| `CLAUDE.md` | **the faults** — what went wrong, with evidence |

⚠️ **HOW TO ADD ONE.** Date it. Quote the person if you have their words. Say what it
supersedes **and what it does not cover**. **Name keys and settings, never values.**
🚫 **NEVER write a ruling you cannot source.** Put it in §B instead. *"I believe there is a
rule here and I cannot find who made it"* is the useful answer.

---

# A. THE RULINGS

## A1 · 5 Aug 2026 — THE ARTICLE'S HEADLINE WINS
> ### "As a general rule we do need to stick with the article headlines.
> ### Go with the article headlines more than anything else."
**— Jodie, with Hugh.**

The episode's **title and hook** come from the source page's own headline, **verbatim,
punctuation and all**. The **part line** is the only place a series is expressed. The
**byline** is the page's own standfirst.

**SUPERSEDES:** `PP-STANDARDS §1a` as written on the morning of 5 Aug 2026 — the "a series
name carries the title" provision — **deleted, not narrowed.**
> **"Make Part 1 and Part 2 match" is not a rule and never was.** Jodie's account of the
> mistake: *"I was trying to make the part 1 and part 2 fit together — but that is not a
> thing."*

**DOES NOT COVER:** the spoken script or the e-book body — those are §0a's, untouched. It
does not settle how a *hook* is shortened from a long headline for the thumbnail, only
where it comes from.

⚠️ **`check_one_name` CANNOT ENFORCE THIS.** It passed EP16 perfectly — title card, e-book
and YouTube title all agreed, **on the wrong name**. *A consistency check proves SAMENESS,
never CORRECTNESS.* Only the source page can, and nothing compares them yet.

## A2 · 5 Aug 2026 — THE PHRASE ANCHOR
A card enters **about 3 seconds after Gordon actually speaks the cue**, and **never before
he has said the words**.

**SUPERSEDES:** EP11's cue-block behaviour — anchoring to the SRT block *containing* the
phrase, which can start several seconds early. *Measured on EP16: the two differ on all 13
cards, by up to 6.41s.*
**Her reasoning:** a card that appears before the phrase **pre-empts the presenter**, and
the few seconds of extra delay cost nothing.

**DOES NOT COVER:** how long a card holds, which beat it sits on, or what to do when a beat
is too short to contain `entry delay + hold` — that last is an open engineering problem, not
a ruling.

## A3 · 5 Aug 2026 — EP16 SHIPS AT 124 kbps
**Decided by LISTENING, not by number:** *"It sounds fine in the middle."*

**ONE EPISODE ONLY. The 180 kbps floor did not move.** The HeyGen API's rendition was
truncated; the web download was complete but a different, lower-audio encode. There was no
third option.

**SUPERSEDES:** nothing. It is an **exception under** the floor, declared per-episode in
`episode.json` via `build.audio_kbps_floor` with a **mandatory** `build._audio_kbps_floor_why`.

**DOES NOT COVER:** any other episode. **Copying the key forward is the failure mode this
ruling exists to prevent.**

## A4 · 5 Aug 2026 — NO B-ROLL APPROVAL STEP, EVER
> ### "We do not want a step to approve the b-roll. We know that this will mean there is
> ### the odd bit of b-roll that is weird. But do not add another step to our process
> ### around this. We will just add a few more rules over time."

**She has knowingly accepted the occasional odd clip as cheaper than the process that would
catch it.** 🚫 No approval gate, no review step, no preview card, no contact-sheet sign-off
— **now or later.**

> **THE ONLY ROUTE IS THE PROMPTS.** A fault found in a clip becomes a **rule in
> `broll-registry.md`**, never a checkpoint in the pipeline.

**DOES NOT COVER:** the HARD-FAIL list — riderless horses, fused limbs, a runner on the
wrong side of the running rail. Those are still rejected on sight. **It forbids a STEP, not
a glance.**

## A5 · 4 Aug 2026 — THE SCRIPT LIVES ON THE RAIL
The script is **a field, not a document**. **The Google service account is cancelled.**

**SUPERSEDES:** the Script Gate's *"the Doc is the script's ONE HOME"* (26 Jul 2026) and
everything built on it — the Doc-URL field, the anonymous-read gate, the drift check, the
link-this-Doc button, and a human relaying a URL between two machines.

**DOES NOT COVER:** `docs/spoken-words.txt`, which must still be written as a derived cache
— `render_ready` runs against that file at `audit_inputs`, and it currently exists only as a
side effect of `fetch_script`.

⚠️ *The ruling document itself, `PP-RULING-the-script-lives-on-the-rail.md`, is a Cowork
document and is not readable from here. This entry is written from Cowork's statement of it,
not from the source.*

## A6 · 4 Aug 2026 — THE SCALE: 300 EPISODES, ABOUT TEN MINUTES EACH
The target the whole studio is built against.

**DOES NOT COVER:** cadence. Publishing is currently **daily**, moving to weekly later — a
separate live setting recorded in `PP-midroll-invitation-standard.md`, and the whole midroll
pool is written against it.

## A7 · 3 Aug 2026 — THE BANG STAYS
> ### "It is Roger Dedman's article and his title."

The exclamation mark is part of the name and survives into every artefact. The bang sits on
the **NAME**, then the em dash, then the part — `Squeeze Those Odds! — Part 1`, never
`Squeeze Those Odds — Part 1!`.

**DOES NOT COVER:** the **byline**, which is a LABEL and whose exact form is Jodie's to set
each time. *EP16's page prints "EACH-WAY BETTING FOREVER!" and its byline carries neither the
hyphen nor the bang — chosen, not drifted.*

## A8 · 3 Aug 2026 — ONE SHOT AT EDITING THE SCRIPT, THEN APPROVE
The operator edits, then approves. **The drift notice is INFORMATION, not a question** — it
tells her a later edit did not make it into this build; it does not ask her to decide
anything and it never blocks.

**DOES NOT COVER:** what happens after the script moves to the rail (A5), where "drift"
between a Doc and a snapshot stops existing as a concept.

## A9 · 2 Aug 2026 — THE YOUTUBE TITLE IS THE EPISODE NAME
`youtube_title = <episode name> + " | How to Win at Horse Racing"`, verbatim, **no
re-casing**. Enforced in `scripts/youtube_title.py`, the only place the house form exists.

**SUPERSEDES:** the byline-derived form, and before that the *"How to Win at Horse Racing:
…"* lead. **EP11–EP13 stay exactly as published** — already-live listings are not retitled.

**DOES NOT COVER:** the description, the hashtags, or the thumbnail text.

## A10 · 28 Jul 2026 — THE REPO STAYS PUBLIC · **Hugh**
**Method and craft are marketing, not trade secrets.** The build recipes, the standards,
the skills and the checks all live in a public GitHub repo on purpose.

**DOES NOT EXTEND TO SECRETS.** Keys, tokens and credentials never enter the repo under any
reading of this ruling. See A14.

## A11 · 28 Jul 2026 — BETSTOP AND GAMBLING COMPLIANCE ARE HUGH'S
Not Cowork's call. **Not Jodie's task.** Compliance questions go to Hugh and stop there.

**DOES NOT COVER:** the standing responsible-gambling line in the outro and the warranty
slide, which are **mandatory build furniture** and are never varied or omitted — that is a
build rule, not a compliance judgement.

## A12 · STANDING — JODIE APPROVES AND PUBLISHES
**No machine touches YouTube.** Human gates are sacred: never auto-render, never
auto-publish. *Approving is a decision; decisions stay human. Starting a render is a chore
and may be automated — automation eats chores, never decisions.*

**DOES NOT COVER:** who may clear a **flag**, which is a different question — see §B.

## A13 · STANDING — DELETIONS ARE ALWAYS JODIE'S
**Quarantine, never delete.** A bad artefact is moved aside into a dated folder and the
reason is written down; it is not removed.
**The rail is SELECT / INSERT / UPDATE only.**

**DOES NOT COVER:** rebuilding an artefact in place during a build — a stale page deleted so
it can be re-authored is a build step, not a deletion of record. *(EP16 needed exactly that,
and the near-miss it caused is in `CLAUDE.md`.)*

## A14 · STANDING — THE THREE THINGS THAT ARE NEVER DONE
1. **Never export `HEYGEN_API_KEY`.** ⚠️ Exporting it **silently switches billing from plan
   credits to the USD wallet** — the failure is financial, immediate and invisible.
2. **Never commit `.env`.**
3. **Never link-share a Drive folder.**

*Named as keys and settings only. No value of any of these appears in this repo, and none
ever should.*

**DOES NOT COVER:** the per-Doc "anyone with the link can view" sharing the old Script Gate
required — that was a document setting, not a folder one, and A5 removes the need for it
entirely.

---

# B. ⚠️ SUSPECTED MISSING — the size of the hole

**Rulings whose EFFECTS are visible in the code or the standards, and whose SOURCE I cannot
find.** Listed, never reconstructed.

### B1 · Load-bearing numbers with no ruler named
*Each of these governs the build and appears as a bare fact.*

| number | where it acts | what I could not find |
|---|---|---|
| **180 kbps** audio floor | `providers.poll_heygen`; stated in `PP-STANDARDS` as *"QC fails < 180 kbps"* | who chose 180, and why not 185 or 150. EP14/EP15 both measure 189.4 |
| **0.85** script-match floor | `align_to_script.MIN_MATCH` — refuses the build below it | no mention anywhere in `docs/`. EP16 passed at 87.8%, i.e. **2.8 points** from halting on a number nobody has justified |
| **65** credit ceiling | quoted in episode notes and the credit check | not in `PP-STANDARDS` at all |
| **3.0s** card entry delay | `derive_card_timings.ENTRY_DELAY` | A2 rules the ANCHOR; the 3.0 itself predates it and is unsourced |
| **10.0 / 12.0** card holds | `build.default_hold`, `hero_hold`, `min_card_hold` | and the code's own defaults contradict each other (E24) |
| **5s / 0.3s** b-roll duration and trim | `build.broll_dur`, `BROLL_TRIM` | never stated as a decision |
| **6–7s head, 3s tail** silence | the HeyGen render settings | stated as fact in the standards |
| **40%** assertion-block cap | `author_cards.ASSERTION_BLOCKS` + the visual standard's R3 | the standard states it; no ruling records who set it |

### B2 · Decisions I can see were made, with no record of the making
- **The crowd-diversity mix** — *"roughly 75 percent white, 9 percent Asian, 9 percent
  Middle-Eastern, 5 percent Black"* appears verbatim in **every** b-roll prompt we have ever
  written and **nowhere in the standards or the registry.** It is being copied episode to
  episode from the previous episode's file.
- **"About half in hats including Akubras"** — same shape, same absence.
- **The midroll pool of ten**, *"approved as a batch, never rewritten"* — the pool is in
  `midroll-line-pool.md`; **the approval is not.**
- **The standing outro wording.** `PP-episode-outro-standard.md` says it *"must be approved
  by Hugh once… after that one approval it's reusable verbatim every episode."* **I cannot
  find any record that the approval happened.** Every episode since has used it.
- **The responsible-gambling line's exact wording** — described as word-for-word locked. By
  whom, and when, is not stated.

### B3 · Rulings known to exist and known to be unreadable from here
- **`PP-RULING-the-script-lives-on-the-rail.md`** — a Cowork document. A5 is written from
  Cowork's statement, not the source.
- **Who may clear a flag** — exists only as a memory file in a machine-local silo, never as
  a repo document. It governs an action taken several times a day.
- **The retention ruling** — cover A/B deleted on publish and logged, rail rows never. Same:
  memory only.
- **`thumbnail-standard.md`** and **`thumbnail-hero-registry.md`** — real files, **on Drive,
  not in the repo**, so the build cannot read them.
- **Anything ruled before 23 July 2026** — the studio predates the repo.

### B4 · Outstanding, not yet ruled *(listed so they are not mistaken for settled)*
- **The framing verdict** — MCU vs WIDE. EP15's run log says a ruling is owed once Jodie has
  watched the finished cut end to end. EP16 shipped at 14 WIDE of 27 with no verdict on
  either episode.
- **"More motion graphics"** — recorded as *"I would be happy with more motion graphics, but
  am happy with where we are"*, explicitly unresolved between **more cards** and **more
  movement within them**.
- **The 1988 "lady punters" aside** — reproduced in EP15's e-book per §0a, not spoken. Her
  call, still owed.

---

> ### THE SIZE OF IT: **14 rulings recorded. At least 20 gaps.**
> **Eight of them are numbers that stop or pass a build, and not one of them has a name
> against it.**
>
> ## ASSUME ANYTHING NOT IN THIS FILE IS INVISIBLE TO CLAUDE CODE, AND THEREFORE GOVERNS
> ## NOTHING.

*Standards: `PP-STANDARDS.md`. Faults and evidence: `CLAUDE.md`. Worked examples:
`EP15-run-log.md`, `EP16-run-log.md`.*
