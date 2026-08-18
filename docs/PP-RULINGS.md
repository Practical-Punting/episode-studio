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
*The crowd's make-up is one of the prompt rules this ruling routes everything through — see
**A15**.*

## A5 · 4 Aug 2026, REINSTATED 5 Aug 2026 — THE SCRIPT LIVES ON THE RAIL
> ### "Do not build the service account. Do not automate the Google Doc.
> ### Put the script on the rail and edit it on the board."
**— Jodie.** Her challenge, which is what produced it:
> *"Are you 100% sure that this is the best way for this document to be managed? Surely
> there are a million applications where documents are managed better than this."*

**IT IS NOT A NEW DECISION.** It was already written on **4 August** in
`PP-script-editor-BUILD-PLAN.md`, in capitals — **"NO GOOGLE DOC. AT ALL."** — **quietly
reversed on the morning of 5 August**, and hereby reinstated.

### 🔴 THE REASONING, WHICH IS THE PART THAT STOPS IT BEING RE-LITIGATED
> ## THE SCRIPT IS NOT A DOCUMENT. IT IS A FIELD IN A RECORD.
> **One author, one editor, one reader, one moment where it freezes.**

**We treat it as a document only because it started life as one** — and a document drags in
**sharing, permissions, formats and corruption** that a text field simply does not have.
**The connector cannot set permissions at all: the machine can create a Doc and physically
cannot share it.**

### CONSEQUENCES
- **The service account is CANCELLED.** Its only job was to read a Doc that will not exist.
- **The "Doc leg" in `DESIGN-engine-commissions-the-script.md` — slice C, 1.0 day — is
  DELETED, NOT ABSORBED.** That makes the commissioning work **SIMPLER rather than harder.**
- **The first job after EP16 is THE BOX:** a text area on the board reading and writing the
  rail. **Not a credential.**
- **The fifteen existing public script Docs remain Jodie's call**, and **stop growing at
  EP17.**

**SUPERSEDES:** the Script Gate's *"the Doc is the script's ONE HOME"* (26 Jul 2026) and
everything built on it — the Doc-URL field, the anonymous-read gate, the drift check, the
link-this-Doc button, and a human relaying a URL between two machines.

### ⏳ WHEN IT APPLIES — AMENDED 6 Aug 2026. **A SCOPE CORRECTION, NOT A REVERSAL.**
> ## THE DOC LEG STANDS UNTIL **THE BOX EXISTS**.
> ### The first episode after the box is built is the first without a Doc.

**This entry said "This applies from EP17."** That was written on 5 August, when the box
was expected to land before the next episode. **It did not: the box is not built, so EP17
runs on a Doc** — and a ruling that says otherwise is a ruling the next reader will trust
and act on.

⚠️ **NOTHING ELSE MOVES.** The service account is **still cancelled**. The Doc is **still
being deleted**. The fifteen public script Docs **still stop growing** — at the first
episode after the box, rather than at EP17.

> ### 🔴 THIS IS THE SAME CLASS OF FAULT AS §1a: a rule that was RIGHT WHEN WRITTEN and
> ### became WRONG WHEN THE WORLD MOVED, with nothing linking the two.
> §1a produced an entire episode under a name nobody had chosen. **A date written into a
> ruling is a dependency on a plan, and plans move.** Bind the rule to the THING
> (*"until the box exists"*), never to the DATE you expect the thing by.

**AND WHY EP17 RUNS ON A DOC IS NOT ONLY THAT THE BOX IS LATE:** EP17 is the first real
test of what landed on 6 August — the card and cue checks moved to `audit_inputs`, and the
`--force` trap closed in all five authoring scripts. **Five of EP16's eight halts should
simply not occur, and that claim is worth nothing until an episode runs.** Building the box
into the same episode would make the run test two things and prove neither. *Don't change
two things when one of them is a test — this studio's own rule, and the reason EP16 ran on
a Doc as well.*

**DOES NOT COVER — and this is a real exclusion, not a formality: EP16 ran on a Doc
DELIBERATELY**, for the same reason.
**Nor does it cover** `docs/spoken-words.txt`, which must still be written as a derived
cache — `render_ready` runs against that file at `audit_inputs`, and it currently exists
only as a side effect of `fetch_script`.

> ### WHY THE DOCUMENT EXISTS AT ALL, in her words:
> ### "Please record this so we do not go through all this again."
**A decision made, reversed and remade within thirty-six hours is exactly the kind that gets
re-litigated by whoever next sees the cheaper option. THE CHEAPER OPTION IS THE DOC. IT IS
STILL THE WRONG ONE.**

✅ *Recorded 6 Aug 2026 from Jodie's verbatim statement. **This entry previously carried a
paraphrase**, flagged on its face as second-hand because
`PP-RULING-the-script-lives-on-the-rail.md` is a Cowork document and unreadable from here.
The paraphrase carried the decision and lost every word of the reasoning above — which is
the half that stops it being reversed a second time.*

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

### ⚠️ SUSPENDED FOR EXACTLY ONE EPISODE — EP17, 6 Aug 2026. **NAMED, NOT WAIVED.**
> ## TODAY SHE GETS **NO** SHOT AT EDITING. She can read the script and cannot change a
> ## word of it.

**A5 was executed mid-episode and half the box landed:** the script lives on the rail and
is shown on the board **read-only**. The `<textarea>` that lets her edit it there is slice
4, and it is **deliberately not built yet** — a textarea is an INPUT, so it lands inside
the refresh-pause reasoning whose last unproven piece is the ctrl+Z observation **at this
very gate, on a change already live on her board.** Building it now would mean that
observation happens against a surface that changed underneath it. *It also keeps EP17 a
clean test of Job A, which is the whole reason this episode ran before the box.*

**THE ROUTE WHILE IT IS SUSPENDED:** she says what she wants changed, **Claude Code writes
it to the rail.** One round trip. Not a blocker.

> ### 🔴 IT IS STILL A STEP BACKWARDS FROM WHAT SHE WAS PROMISED, AND IT IS RECORDED AS ONE.
> **Jodie's own words on 3 August were *"I get one shot at editing and then approving"*.**
> Writing this down as a cost rather than a detail is the point: **a promise quietly
> unfulfilled for "one episode" is how one episode becomes five.**

**SLICE 4 IS THE NEXT THING AFTER EP17 SHIPS — not "in the gaps while renders cook".**
*(Jodie, 6 Aug 2026.)* **DOES NOT COVER** any further suspension: this expires when EP17
ships, and extending it needs a new ruling.

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

## A14 · STANDING — THE THINGS THAT ARE NEVER DONE
1. **Never export `HEYGEN_API_KEY`.** ⚠️ Exporting it **silently switches billing from plan
   credits to the USD wallet** — the failure is financial, immediate and invisible.
   *Measured: ~$6.60 an episode on plan credits became ~$21.48 on the wallet.*
2. **Never commit `.env`.**
3. **Never link-share a Drive folder.**
4. 🆕 **Never set `ANTHROPIC_API_KEY` (or `ANTHROPIC_AUTH_TOKEN`) anywhere the engine can
   see it** — not in the environment, not in `.env`, not in a settings file.
5. 🆕 **Never pass `--bare` to a commissioned run.**

### 🔴 WHY 4 AND 5 ARE THE HEYGEN TRAP WEARING DIFFERENT CLOTHES (6 Aug 2026)
**Established, not reasoned:** a commission runs on **Jodie's Claude Max subscription**
(`authMethod: claude.ai`, `apiProvider: firstParty`), read from `claude auth status` in a
spawn with every inherited Claude variable scrubbed. **It is not a pay-as-you-go balance.**

> ### BOTH OF THESE SWITCH IT TO NEW MONEY, SILENTLY.
> **`--bare`'s own help says it:** *"Anthropic auth is strictly `ANTHROPIC_API_KEY` or
> `apiKeyHelper`; OAuth and keychain are never read."*

⚠️ **AND THIS IS WHY IT NEEDED A RULING AND NOT JUST A GUARD.** `--bare` is documented as a
**performance flag** — skip hooks, skip plugin sync, skip `CLAUDE.md` discovery. **Every
commission pays about 7,700 cache-creation tokens before it does any work**, and at 300
episodes somebody WILL find that overhead and go looking for a way to cut it. **They will be
acting in good faith, trying to make the studio faster and cheaper, and they will move it
onto a bill instead.** *That is exactly how the HeyGen key went.*
> ## WE ARE NOT TAKING THAT TRADE. THE OVERHEAD STAYS.

✅ **ENFORCED, not merely written:** `commission.assert_subscription_wallet()` runs **before
every single commission**, derives the answer from `claude auth status`, and **refuses and
halts** — it never warns and proceeds. **A dollar cap would not have caught this**, because
it caps the same notional number whichever wallet is paying. *Only asking WHICH WALLET
catches it.* Proved by mutation: breaking the guard three different ways turns the suite red.

*Named as keys and settings only. No value of any of these appears in this repo, and none
ever should.*

**DOES NOT COVER:** the per-Doc "anyone with the link can view" sharing the old Script Gate
required — that was a document setting, not a folder one, and A5 removes the need for it
entirely.

## A15 · STANDING — THE CROWD LOOKS LIKE AUSTRALIA
> ### "I requested the diversity in the audience because everyone in the videos was white,
> ### and Australia does not look like that. Not even at the races."
**— Jodie.**

The mix — **roughly 75% white, 9% Asian, 9% Middle-Eastern, 5% Black, and about half the
crowd in hats including Akubras** — is **a deliberate correction of a real defect in the
generator, which defaults to all-white crowds.**

> ## IT IS AN EDITORIAL STANDARD ABOUT HOW OUR AUDIENCE SEES ITSELF.
> ## IT IS NOT A PROMPT DETAIL.

**WHY THE REASON IS RECORDED AND NOT JUST THE NUMBERS:** without it this reads as an
arbitrary set of percentages, and **a future author tidies it away as clutter** — which is
precisely how it has survived so far, by being copied forward from the previous episode's
file. *The words were in the standards (§B-roll) and the script skill; the reason was
nowhere, and a rule whose reason is missing is a rule waiting to be deleted by someone
being helpful.*

**HOW IT IS ENFORCED: through the PROMPTS, per A4.** No approval step, no review gate. A
crowd that comes back uniform is regenerated on sight — the standards already say *"reject
uniform crowds at QC"*, and that is a glance, not a step.

**DOES NOT COVER:** the HARD-FAIL list, which is about pictures that are racing-wrong or
anatomically broken. **This one is about a picture that is technically perfect and still
does not look like this country.** *Nothing automated can see either.*

### A15a · 8 Aug 2026 — 🔴 HATS ARE A VARIETY OF NATURAL COLOURS
> ### "Akubra-style hats must be a variety of natural colours — fawn, sand, tan, brown,
> ### grey, black, olive — never a uniform white field."
**— Jodie, on EP18 as shipped.**

**Filed INSIDE A15 on purpose: it is the same defect one level down.** A15 records that the
generator *"defaults to all-white crowds"*; this is that same habit in the wardrobe — **asked
for "hats", the model picks ONE hat and clones it onto every head.** `broll-country-course-
gums-and-rail` came back with sixteen people at the rail, in focus, wearing the identical pale
cream hat. **Uniformity is the default, not the accident.**

⚠️ **STATE IT POSITIVELY — name the colours wanted.** *"Not all white"* hands the model the
choice of replacement and it will make ONE choice, for every head. **The fault is the
UNIFORMITY, not the colour**: a rail of identical fawn hats fails this ruling too.

**WHY IT NEEDED WRITING DOWN AND NOT JUST FIXING:** A15's own prompt language already said
*"about half the crowd in hats including Akubras"* — **hats were named, the RANGE was not.**
That is A15's lesson recurring: *the model dresses what it is told about and improvises the
rest.* Fixing EP18's clip without fixing the words would have bought one good clip and left
the next crowd to the same default.

**HOW IT IS ENFORCED:** through the PROMPTS, exactly as A15 — **now item 4 of the standing shot
template in `broll-registry.md`.** No approval step, no review gate; a uniform crowd is
regenerated on sight.

## A16 · 6 Aug 2026 — MIDROLL POOL LINE **L7** IS AMENDED, TWICE
Both amendments came from Jodie at EP17's words gate — **the line's first use** — in one
sitting. **BOTH REMOVED FRAGMENTS, quoted so neither can be restored from an older copy:**

| # | removed | replaced with |
|---|---|---|
| 1 | *"…, and it does more for them than it ever does for me."* | *(nothing — the sentence closes at "made for.")* |
| 2 | *"…so subscribe and they'll find you instead."* | *"…so subscribe and the next one finds you."* |

> ### HER OBJECTION TO THE SECOND, because the reasoning is the useful part:
> ### "the bit that says 'and they'll find you instead' does not make sense at all."
**She is right: "they" points back to "the folk it was made for"**, so the line reads as the
AUDIENCE coming to find her. **It meant the VIDEOS would turn up on their own and never
said so.** *A pronoun aimed at the wrong noun — invisible on a page, obvious out loud.*

**Nothing else in L7 moved.**

**WHY THE POOL AND NOT JUST THE EPISODE — she was not asked to rule on the pool
separately, and did not need to be:**
1. **The midroll must be VERBATIM from the pool.** An EP17 that differed from L7 would
   either fail `render_ready`'s freshness check or quietly weaken it.
2. **The pool wraps.** Left in, those words return at **EP27**, on an episode nobody is
   watching for them. *She said she dislikes them; she should not have to say it twice.*

**SUPERSEDES:** L7 as batch-approved 28 Jul 2026. **The other nine lines are untouched and
are NOT re-opened by this.** Full detail and the before/after: `docs/midroll-line-pool.md`.

**DOES NOT COVER:** the fixed SHAPE (§4E), which is unchanged and still satisfied.
*This also part-closes a §B2 gap: the pool's original batch approval has no record, but
this amendment is sourced.*

> ### 🔴 THE FINDING THAT OUTLIVES THE LINE — **A BATCH APPROVAL IS A LIST SOMEBODY
> ### APPROVED ONCE AND NOBODY HAS SINCE READ.**
> **L7 was wrong TWICE, and both faults were found by one person reading it IN PLACE for
> the first time.** Approved 28 July; **EP17 is its first use. THE OTHER NINE HAVE ALL
> SHIPPED.**
> **Ten lines were waved through together, nine went to air, and the tenth turned out to
> carry two faults the moment a human met it. The approval covered the BATCH; nothing
> covered the LINES.**
>
> **It is `CLAUDE.md` fault #7 in a new costume** — coverage that is a list somebody
> maintains, except here the list was *approved* rather than maintained, which is worse:
> **an approval feels like evidence.** *Ask of any batch: has anyone read the members since
> the day it was waved through?*
>
> 📋 **OWED, AFTER EP17 IS MOVING: read the other nine in place** — does every sentence
> PARSE, and does each still describe reality (all ten carry the **DAILY** cadence, one
> live setting that will be wrong in **ten places at once**). **Not to re-open them.**
> ⚖️ **Nothing published is touched** — *found retrospectively does not mean fixed
> retrospectively* (Jodie, 4 Aug). Fix for future use, log it, move on.

## A17 · 6 Aug 2026 — 🔴 THE SCRIPT MUST BE EDITABLE BEFORE EP18
> ### "Please make sure we are able to edit the script before the next episode."
**— Jodie.**

**Slice 4 — the `<textarea>` on the board — is a REQUIREMENT for EP18, not a preference.**

> ### ⚠️ THE EVIDENCE, AND IT IS THE WHOLE ARGUMENT: A8's SUSPENSION WAS TESTED WITHIN
> ### **MINUTES** OF THE GATE OPENING, AND FAILED IMMEDIATELY.
> **The first thing she tried to do at her own words gate was change a word, and she could
> not.** The suspension was recorded that same afternoon as lasting "exactly one episode"
> and as a cost worth naming — *it did not survive the first contact with the person it was
> imposed on.*

**SUPERSEDES:** nothing. It **ends** A8's suspension at EP17 and forbids extending it.
**DOES NOT COVER:** EP17 itself, which runs read-only. **The route until then: she says
what she wants changed and Claude Code writes it to the rail.**

## A18 · 6 Aug 2026 — 🔴 THE MACHINE FILLS THE NAME, HOOK AND BYLINE FROM THE ARTICLE
> ### "cc should be able to read the title and byline!"
**— Jodie.**

**A1 says the episode's name, hook and byline come from the source page. Nothing enforces
it at the moment they are first written**, so they are derived correctly by Claude Code,
relayed through two machines and a human, and then **typed in by hand.**

> ### IT IS THE SAME FAULT AS THE SCRIPT, ONE FIELD OVER.
> The script was a field on a record being treated as a document. **The packaging is three
> fields being treated as something a person types.**

**WORKED EXAMPLE, EP17:** all three were derived from the page on the morning of 6 Aug —
`Testing the Numbers` · `TESTING THE NUMBERS` · `The stats tell the story` — and there was
nowhere to put them. **Meanwhile `slugToTitle()` (`app.js:192`) filled the box from the URL
SLUG**, producing *"Testing The Numbers"* — **a capital T on a word the article sets lower
case.**

**WHAT IS RULED:** the name, hook and byline **come from the source page**.
- 🚫 **`slugToTitle()` guessing from a web address must STOP.**
- ⚠️ **`titleSmell()` suggesting after the fact is GRADE 1 where grade 2 was needed** — it
  would have flagged this exact string, and by design it only ever warns.

**DOES NOT COVER the mechanism, which is a design question, not a ruling:** whether the
create step reads the page, or the commission seats the fields, is open. *An empty box a
human fills is honest; a wrong box that looks authoritative is not.*

**NOT BUILT — recorded 6 Aug, deliberately, while EP17 runs.**

## A19 · 6 Aug 2026 — 🔴 EVERY FLAG DECLARES ITS AUDIENCE
> ### "I don't like that this says 'needs a look'. It is like it means that the user
> ### should be doing something. But what can we do?"
**— Jodie, at EP17's `audit_inputs` halt.**

**The chip says NEEDS A LOOK. The message says *"Claude Code writes these at the create
step (the create brain is Phase 4)"*. Same card.** It names a file she cannot make, a step
she cannot run and a phase number that means nothing to her — **then badges it as hers.**

> ## TWO KINDS OF HALT ARE CALLED THE SAME THING.
> | kind | example | whose |
> |---|---|---|
> | **a DECISION** | the hero crop, the midroll listen | **HERS.** These should live forever |
> | **a JOB NOT DONE** | the script, `episode.json`, the YouTube copy | **THE STUDIO'S.** She can only wait |

**THE FIX:** `operator` → **NEEDS A LOOK**, her lane, plain English, no path, no file name,
no phase number, no URL. `studio` → **a different lane and a different chip — "Waiting on
the studio"** — never an orange badge in her queue.

### ⚠️ DERIVED, NOT DECLARED — because a tag is a list somebody maintains
> ## **A FLAG WHOSE REMEDY NAMES A FILE, A SCRIPT OR A STEP IS BY DEFINITION NOT FOR THE
> ## OPERATOR.**
**That single test catches this flag, EP16's crop flag with its Supabase URL, and the
YouTube-copy halt — with nobody tagging anything.** *(Fault #7's shape done right: derive
the coverage from the thing itself.)*

**WHY IT IS NOT COSMETIC:** the measure this project is judged by is *"how many things can
Hugh NOT clear from a browser?"* **The board cannot tell the two piles apart, so it cannot
even COUNT the thing we are judged by.**

**DOES NOT COVER:** the WORDING of an operator flag, which `docs/PP-operator-box-rule.md`
already governs. This is about which pile a flag lands in, not how it reads once it is
there. **RECORDED 6 Aug, NOT BUILT — EP17 was mid-build.**

## A20 · 6 Aug 2026 — 🔴 PUT THE THING WHERE THE PERSON IS STANDING
> ### "But there was no script given to me so that I can start the render. This is
> ### an issue we have discussed several times! And still not fixed."
**— Jodie, blocked at EP17's render gate.**

**The render card told her to open HeyGen and render, and handed her the PROJECT NAME
on a Copy button — not the SCRIPT, which is the thing HeyGen actually consumes.** The
words card shows the script; **that card has CLOSED by the time she reaches the render
gate**, so at the exact moment she needed the words there were none on screen.

**Written down on 5 August as EP17-list item 5** — *"the render card asks for the one
thing it does not give"* — **and this is the THIRD episode.** It blocks the longest single
job in the pipeline: EP16's render cooked for over four hours, so every minute it holds
her up is a minute on the end of her night.

### ✅ FIXED THE SAME EVENING
1. **The render card shows the script** — the SAME read-only panel as the words card,
   extracted to one `scriptPanel()` used by both. **Not a second one that can drift.**
2. **A Copy button for the script itself**, beside the one for the project name — the
   whole thing on the clipboard in one action. *Copying 1,484 words by dragging a
   selection across a scrolling read-only panel is not a workflow.*
3. **Both buttons say what they are for.** *Two unlabelled Copy buttons would be a new
   confusion replacing an old one.*
🔒 **Still a `<pre>`, not an input** — the refresh-pause reasoning is unchanged.

> ## 🔴 FOUR INSTANCES, ONE FAULT — and this is the ruling, not the button.
> ## **THE MACHINE HAS THE THING, KNOWS SHE NEEDS IT, AND DOES NOT PUT IT WHERE SHE IS
> ## STANDING.**
> | # | what the machine had | where she was |
> |---|---|---|
> | 1 | the **SCRIPT** | at the words gate, told to read something with no box to read it in (A5) |
> | 2 | the **NAME, HOOK and BYLINE**, derived from the article that morning | typing them in by hand (A18) |
> | 3 | the **SCRIPT AGAIN** | at the render gate, told to render with no words on screen (here) |
> | 4 | **`episode.json`, the YouTube copy** | badged NEEDS A LOOK for jobs she cannot do (A19) |
>
> ⚖️ **It is the inverse of `CLAUDE.md` fault #0.** That one says *never ask a person for
> something the rail already knows.* **This one says: when the rail knows it and the
> person needs it, PUT IT IN FRONT OF THEM.** Same root — the machine holds something and
> the person is left to supply it — and **every one of the four was found by Jodie, not by
> a check.**

**DOES NOT COVER:** what a card SAYS once the thing is on it — `PP-operator-box-rule.md`
governs that. This is about whether the thing is there at all.

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
- ✅ ~~**The crowd-diversity mix** and **"about half in hats including Akubras"**~~ —
  **CLOSED 6 Aug 2026 BY RULING A15**, in Jodie's own words and with her reason attached.
  ⚠️ **AND THIS ENTRY WAS FACTUALLY WRONG, which is worth more than the closure.** It said
  the mix appears *"nowhere in the standards or the registry"*. **It is in
  `PP-STANDARDS.md:513-514`** (§B-roll, with *"reject uniform crowds at QC"*) **and in
  `.claude/skills/pp-episode-script/SKILL.md:432`.** *The NUMBERS were written down in two
  places. Only the REASON was missing — and I recorded that as the words being missing,
  which would have sent the next reader looking for the wrong thing.*
  > **A gap list is only useful if its claims are checked the way a ruling's are.**
- **The midroll pool of ten**, *"approved as a batch, never rewritten"* — the pool is in
  `midroll-line-pool.md`; **the approval is not.**
  ⚠️ **PART-CLOSED 6 Aug 2026 by A16**: L7's AMENDMENT is sourced to Jodie. **The original
  batch approval of the other nine is still unrecorded** — and A16 deliberately did not
  re-open them.
- **The standing outro wording.** `PP-episode-outro-standard.md` says it *"must be approved
  by Hugh once… after that one approval it's reusable verbatim every episode."* **I cannot
  find any record that the approval happened.** Every episode since has used it.
- **The responsible-gambling line's exact wording** — described as word-for-word locked. By
  whom, and when, is not stated.

### B3 · Rulings known to exist and known to be unreadable from here
- ✅ ~~**`PP-RULING-the-script-lives-on-the-rail.md`**~~ — **CLOSED 6 Aug 2026.** The Cowork
  document is still unreadable from here, but **Jodie gave the ruling verbatim** and A5 is
  now written from her words, not from a statement of them.
  ⚠️ **`PP-script-editor-BUILD-PLAN.md`, which A5 cites as the 4 Aug original, is STILL a
  document I cannot read** — the repo has only `PP-script-editor-REVIEW-4Aug.md`. The
  quoted line *"NO GOOGLE DOC. AT ALL."* is Jodie's report of it, not a read.
- **Who may clear a flag** — exists only as a memory file in a machine-local silo, never as
  a repo document. It governs an action taken several times a day.
- **The retention ruling** — cover A/B deleted on publish and logged, rail rows never. Same:
  memory only.
- **`thumbnail-standard.md`** and **`thumbnail-hero-registry.md`** — real files, **on Drive,
  not in the repo**, so the build cannot read them.
  ⚠️ **CHECKED 6 Aug 2026, AND THE RISK IS THE INVERSE OF THIS ENTRY.** `author_thumbnail.py`
  **does not read either file and never did** — every number is hard-coded in
  `assets/youtube-thumbnail-template.html`, which IS in the repo (`logo left:56px
  bottom:40px`, `l1 96px`, `l2 150px`, `part 75px`). **Measured across EP11–EP17: all seven
  thumbnails are 1280×720 with the logo at exactly 56px/41px.** The build cannot drift from
  a standard it never opens; **the STANDARD can drift from the build, and nobody would
  know, because the document has no reader.** *The gap is real and it points the other way.*
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

> ### THE SIZE OF IT: **19 rulings recorded. At least 17 gaps.**
> *(A16–A18 added 6 Aug 2026: L7 amended, the script editable before EP18, and the machine
> filling the name/hook/byline from the article. **All three came from Jodie speaking at a
> single words gate** — which is what a gate is for.)*
>
> **Eight of the gaps are numbers that stop or pass a build, and not one of them has a
> name against it.**
> *(Was 14 and 20, then 16 and 17. Everything closed so far — A5 sourced verbatim, A15
> recorded with its reason, A16's amendment — was closed by **Jodie speaking, not by
> anyone finding a document**, which is the only route several of the remaining ones have
> either.)*
>
> ## ASSUME ANYTHING NOT IN THIS FILE IS INVISIBLE TO CLAUDE CODE, AND THEREFORE GOVERNS
> ## NOTHING.

*Standards: `PP-STANDARDS.md`. Faults and evidence: `CLAUDE.md`. Worked examples:
`EP15-run-log.md`, `EP16-run-log.md`.*

## RENDER FIRST — the render gate opens at the words gate (9 August 2026)

**Jodie approved this locked-order change in terms.** The render gate opens at the words gate — it needs only the approved script and the project name, and both are final the instant she clicks approve — and the episode.json commission, the gens batch and the cards all run behind it, inside the render window.

**The reasoning she approved:** the render is the long pole (5-45 min) and depends only on the spoken track, which is final at the words gate. Nothing an `episode.json` fault can do changes a word Gordon says, so **no card fault can waste a render.**

**The evidence:** `docs/EFFICIENCY-AUDIT-approval-to-render.md`. EP18 — a clean run, one commission, no repair — still made the longest job in the pipeline wait **17m 14s**, of which the commission was **98.7%**. EP19 waited 31m53s. Nobody re-sequenced anything: `audit_inputs` was a four-second scan until it became a commission on 7 Aug, and the render silently inherited the wait.

⚠️ **This approval covers this reorder and nothing else.** Any further re-sequencing is a fresh ruling.

🔒 **Guarded:** `check_locked_order()` now asserts `render_gate` before `audit_inputs`. The absence of that eighth assertion is why the regression was invisible — all seven existing rules still held while the render slid behind the commission for two episodes.

## A21 · 14 Aug 2026 — 🐎 THE FIELD RUNS ON ONE SIDE OF THE RAIL, AND THE PROMPT SAYS SO · **Hugh**

**The fault, on EP23 as shipped: horses ran on BOTH SIDES of the running rail.**

**EP24 onward. EP23 is published and is NOT changed.** This is a **prompt rule**, routed
exactly where **A4** says every b-roll fault must go — into the words, never into a step.

**The line, stated positively, on every galloping / field / raceday shot:**
> *"The whole field runs on ONE side of a single white running rail — the rail is the
> inside boundary of the track, open green turf infield beyond it, no horses on the far
> side; on a bend the rail curves with the track and the field stays outside it."*

### 🔴 THE REASON, AND IT IS NOT "NOBODY MENTIONED THE RAIL"

**EP23's prompts NAMED the white running rail — five of the six racing shots did.** They
also carried the stride line and the silks line, because whoever wrote them had read
`broll-registry.md`. **Not one of them said WHICH SIDE OF IT THE HORSES GO.**

In every case the rail was placed as **scenery** — *"running away across the frame"*,
*"along one side"*, *"curving away on the inside"*, *"the leaders tight against a … white
running rail"* — and never as a **BOUNDARY with a rule about it**. So the model drew the
rail it was asked for and filled both sides with the horses it was also asked for.

> ### It did what it was told. It was told the wrong thing.

**That is the same shape as the hat ruling (A15) and as the two EP16 faults: a model
completes what you describe and improvises the rest.** Hats were named, the RANGE was
not. The rail was named, the SIDE was not. **The thing that must be true has to be the
thing you say.**

⚠️ **THE POSITIVE CLAUSE IS THE ONE THAT WORKS: *"open green turf infield beyond it."***
*"No horses on the far side"* is kept as belt-and-braces, but **a negation cannot be
drawn** — the model must render *something* beyond the rail, and if it is not told what,
it reaches for the subject the rest of the prompt is about. **Give the far side a job and
there is no room left for a horse.**

📌 **AND A SECOND FAULT FOUND WHILE WRITING THIS.** EP23 sent *"a dead straight and
perfectly level white running rail"* into **two shots that bend** — `coming-from-well-back`
(*"curving away on the inside"*) and `inside-barriers-turn-for-home` (*"sweeps around a
bend"*). **A standing line pasted in unconditionally, contradicting the shot around it.**
Asking a model for a straight rail on a bend is asking for incoherent geometry, and
incoherent geometry is the soil the both-sides fault grows in.

**SUPERSEDES:** nothing. It **extends** the rail item that has been in
`broll-registry.md` since 28 Jul 2026, which until now was a *"look at the contact
sheet"* rule that said prompt wording *"helps"* but *"is not the control"*. The wording is
now a standing line in its own right, and the glance is still the last line of defence.

**DOES NOT COVER:** the glance itself, which stands (A4). It does not add a step, a gate,
an approval or a sign-off, and **must not be read as licence to.**

🔒 **GUARDED, because a rule that is only written down recurs.** The lines live once in
`engine/broll_prompt_rules.py` and are checked in `providers._broll_prompt` — the function
**every generated prompt comes through** — so a prompt that does not state them cannot be
submitted, and it halts **before a credit is spent**, not after the clip comes back wrong.
`engine/test_broll_rail_rule.py` (26 cases) proves it against **EP23's real prompts**: it
catches all five racing clips on the missing rail side and both bend shots on the
contradiction, leaves the kitchen-table clip alone, and **does not re-flag the strides,
silks or turf EP23 already got right** — a check that complains about everything is one
nobody reads.

⚠️ **This is not a review step and the guard is not a judgement.** It reads text and names
the missing sentence. **A4 forbids a step, not a spellcheck.**

## A22 · 14 Aug 2026 — 🖼️ EVERY RACING IMAGE SAYS WHICH WAY UP IT IS · **Jodie**

**The fault, on EP24: cover B came back UPSIDE DOWN.**

**The line, stated positively, on both cover heroes and every racing hero image:**
> *"Correct upright orientation — horizon level and near the middle, sky at the top, green
> turf and track at the bottom, camera at eye level; horses upright and running along the
> ground."*

### 🔴 THE REASON: THE A/B PICK IS A SAFETY NET, AND IT WAS BEING RELIED ON

The cover pick caught it, exactly as designed — **that is not the point.** One of the two
options was **wasted**, so the "choice" was not a choice, and **had both come back wonky
the pick would have been between two unusable covers.** A net that has to be used is a net
being relied on. This does not replace the pick; it makes a wonky one **rarer**.

⚠️ **AND IT MUST NOT BE A NEGATION.** *"Not upside down"* cannot be drawn. **A model has to
put the horizon somewhere**, and if it is not told where, it will put it anywhere — so the
line says where everything GOES: sky up, turf down, horizon level and central, camera at
eye level, horses upright and on the ground. **Same reasoning as A21's *"open green turf
infield beyond it"*: give the thing a job and there is no room for the wrong answer.**

**SUPERSEDES:** nothing. It sits beside A21 as the second standing line applied to
generated imagery.

**DOES NOT COVER:** the cover pick itself, which stands and remains Jodie's (A12, and the
human gates). It does not add a step, a gate or an approval.

🔒 **GUARDED, and APPLIED rather than asked.** The line lives once in
`engine/broll_prompt_rules.py`, as one entry in `RULES`, so **both** funnels read the same
definition: `apply_rules()` for the racing b-roll and `providers._cover_prompts` for the
cover heroes. Written back to `episode.json`, because that file is the audit trail for the
image that was bought. Proved in `engine/test_broll_rail_rule.py`, including that a
non-racing image is NOT given racing orientation, and that applying it twice does not
double it.

> ### 🔴 CORRECTED 14 Aug 2026, THE DAY AFTER — **"THE SINGLE FUNNEL" WAS TWO FUNNELS.**
> This paragraph used to say the line was applied in `providers._cover_prompts`, *"the
> single funnel every generated hero comes through"*. **It is not.** The cover heroes come
> through that one; the **racing b-roll** comes through `apply_rules()`, and the rule was
> installed at only the first. EP25's two cover prompts carried the line correctly — and
> **all six of its racing b-roll prompts had no orientation at all.**
>
> ⚠️ **AND THE TEST FILE WAS GREEN THROUGHOUT.** It asserted the cover funnel, which was
> genuinely working. **A guard installed at one funnel says nothing about the other, and a
> passing suite will not tell you there is another one** — the words *"the single funnel"*
> were the whole of the evidence that there wasn't, and they were written by the same hand
> that installed the guard. **Ask what ELSE reaches the thing you are protecting, and
> answer it by reading the callers, not by describing the design.**
📌 **The ledger (`_prompt_key`) is keyed on the prompt, so a rewritten prompt is a
different image to E16 — which costs nothing here: a hero already ON DISK is never
re-bought, so only a hero that was going to be generated anyway is generated from the
better words.**

## A24 · 14 Aug 2026 — 📄 A THIN CAPTURE IS PROVISIONAL UNTIL A HUMAN SAYS YES · **Jodie**

**The ruling:** *capture best-effort text, but it does NOT become the article of record —
what `script_fidelity`, `check_trace` and the e-book body are measured against — until a
HUMAN has looked and said yes.*

> **No hard halt, and nothing silently trusted.** On a thin or partial capture the
> best-effort text is kept as **PROVISIONAL**, and a plain-English **question** goes on the
> board: *"this article came out shorter than a PP feature normally is — open it and tell
> me whether that is all of it."*

### 🔴 HOW THIS SITS WITH "IT PLACES A CAPTURE OR IT REFUSES", WHICH IS NOT WEAKENED

`capture_article`'s own header says it never produces a best-effort article of record, and
that rule is load-bearing: **a subtly wrong capture does not fail — it redefines the truth,
and every downstream check then agrees with it.**

> ### THE DANGER WAS NEVER BEST-EFFORT TEXT. IT WAS BEST-EFFORT TEXT NOBODY LOOKED AT.
> **A human's confirmation satisfies the original rule exactly.** What had to be built was
> not the fallback — it was the guarantee that between the refusal and the yes, nothing
> anywhere can mistake the text for the article of record.

🔒 **AND THAT GUARANTEE IS THE FILE'S LOCATION, NOT ITS BANNER.** The provisional text is
written into the EPISODE's folder, never `PP Videos/docs/`, so `find_capture()` — which
globs `docs/EPnn-source-article-*.md` — **cannot see it at all.** A banner is a comment,
and this repo has paid for trusting those. **Promotion is a MOVE, and the move is the
moment it becomes true.**

### WHAT IS OFFERED FOR A YES, AND WHAT IS STILL A HARD REFUSAL

| offered as provisional | still refused outright |
|---|---|
| **SHORTNESS** — the words are the article's own; the only doubt is whether they are all of it, and **that is a question a person answers by looking at the page** | **no article container / it never closes** — there are no words to offer |
| | **furniture leaked · a surviving sentinel** — the text is CONTAMINATED, and asking someone to certify text whose edges they cannot see is not a confirmation |
| | **OCR damage · a list inside a list** — §0a JUDGEMENTS about what the article SAYS, which is a different question from "is this all of it" |

⚖️ **The answer is OBSERVED, never assumed.** It reuses the C3 gate (`ask_once` /
`answer_pending_gates`): an `.asked-…` becomes an `.answered-…` **only when the flag
actually went down on the board**, so a restart, a reboot or a re-run cannot promote
anything by itself. An unanswered ask simply is not an answer.

📌 **And the promoted file says how it got there** — "the automatic capture REFUSED this
page for being too short… a person compared it with the source and confirmed it" — so
nobody reading it in three months mistakes a short article for a clean automatic capture.

🔒 **GUARDED:** `engine/test_capture_provisional.py`, 28 cases, including that
`find_capture()` returns nothing while the question is outstanding, that a re-run re-asks,
and that a second promotion cannot overwrite the record.

## A23 · 14 Aug 2026 — ⏱️ A MECHANICAL FIX APPLIES ITSELF; ONLY THE EDITORIAL HALF HALTS · **Jodie**

**The fault, on EP25: `CARD-CARD overlap C26/END: 0.34s`.** Three tenths of a second
stopped the build and waited for a person.

### THE RULE

> **When a card overruns the next and the arithmetic alone can clear it — the card FITS
> the room it has, at its own lawful floor — the engine BRINGS THE HOLD DOWN and carries
> on. It never asks.**
> **When clearing it means deciding WHICH ROW FOLDS INTO WHICH, it halts, because that
> changes what the card says.**
> **`SPLIT` is offered as the alternative. `DROP` never is — a fact does not come out to
> save three tenths of a second.**

### 🔴 THE TWO-PART CATCH, WHICH IS THE WHOLE REASON THIS KEPT COMING BACK

**Folding a row lowers the FLOOR. It does not move the PLANNED HOLD.** `hold_for()`
returns `build.holds[cid]` if it exists and otherwise the episode default — so a card
folded from four items to three has a floor of 9.0s and is **still planned at 10.0s, and
still overlaps.**

> **A human who folds the card and stops has fixed nothing, and gets the identical halt
> back with no clue why.** EP25 needed **both** writes and a person did **both** by hand.

**So the floor moving is now what MAKES the hold move.** The mechanical half can no longer
be forgotten, because nobody has to remember it. *That is the general shape, and it is the
point of the ruling: when a fix has an obvious half and a bookkeeping half, the bookkeeping
half is where it silently half-lands — automate that one FIRST.*

### WHERE THE LINE IS, AND WHY IT IS THERE

**Automation eats chores, never decisions** (A12, and the Script Gate record). Bringing a
hold down to a floor the tool already computed is a chore: **no fact moves, no cue moves,
nothing a viewer reads changes.** Choosing that "the bank" and "the stake" share one cell —
which is what EP25's fix actually was — **changes what the card says**, and stays Jodie's.

**SUPERSEDES:** nothing. It is the third of the same argument: `--apply-broll` (12 Aug),
`--apply-wide` (13 Aug), and now `--apply-hold`. **Every one was a halt that had never
been a decision, and every one was applied verbatim by hand before it was automated.**

**DOES NOT COVER:** a card that does not fit **even at its floor** (still halts, and must);
a card too big for **any** window (`NOTHING FITS THIS WINDOW` — it moves or it comes out,
and that is a decision); the midroll and b-roll overlap classes, which have their own rules.

🔒 **GUARDED.** `--apply-hold` in `derive_card_timings.py`, one derived condition —
*floor fits the window AND the planned hold is above the floor* — so no episode is named
and no list is maintained. Proved in `engine/test_shot_map_flows.py` **PART D**, on EP25's
real C26: the four-cell card still halts and `build.holds` is left untouched; the folded
card with its hold unset is brought down to **9.0**, which is exactly the number the human
wrote. EP22's pre-fix halts still halt, and EP19/20/21 still derive clean and unchanged.
📌 **And the halt now names the one thing it wants** — *"the ONLY thing needed from you is
WHICH row folds into which… the hold then comes down by itself; you do not have to set
build.holds"* — so the person in front of it is asked for a judgement, never for arithmetic.

---

## A25 · 17 Aug 2026 — 🤖 THE HEYGEN RENDER MAY BE FULLY AUTOMATED · **Jodie**

**Supersedes:** the blanket reading of `CLAUDE.md`'s *"never automate the human gates"*,
**for the render and for nothing else**. Builds on **A26 below (11 Aug)**, which stands.

> **THE HEYGEN RENDER RULING — Jodie, 17 August 2026. FULL AUTO, RENDER ONLY.**
> The CLAUDE.md line "never automate the human gates" is AMENDED FOR THE RENDER ONLY.
> The studio may fill the HeyGen template AND click Generate/Submit itself.
> This does NOT extend to any other gate. The words/script gate, the cover pick, the four
> approvals and the publish all remain HUMAN and are not to be automated.
> Conditions, all of which must hold:
> - browser automation of the HeyGen web app on subscription credits — NEVER the API or
>   Make (the 11 Aug ruling stands)
> - generate AT MOST ONCE per episode, ever; the rail marker is written BEFORE the click,
>   not after, so a crash cannot double-generate
> - a dry-run fill-only mode must exist and be proven first
> - the click must RE-VERIFY the live fields immediately before pressing — a screenshot is
>   a proxy, not evidence
> - the popup settings are verified: 1080p / MP4 / My Projects / Watermark Off /
>   correct title
> - the Script Gate stays: no render before the script is approved
> - listen_check stays: Jodie listens to the WHOLE render before it is used
> - manual fallback always; STOP and ask on a login wall or captcha; never guess a selector

**THE REASONING, AND WHY IT IS NOT A WEAKENING.** The human-gate rule protects **who
decides**, and every gate it protects is a JUDGEMENT — is this cover right, are these
words right, is this good enough to ship. **The render is not a judgement. It is typing.**
Jodie's script is already approved at the Script Gate before a render may start, and she
still hears the finished take at `listen_check` before a frame of it is used. What sat
between those two was a keyboard — and on 17 Aug it stopped her working at all: away from
her desk with only an iPhone, HeyGen's mobile app and mobile web could not drive the
template flow, so EP30 sat finished-but-for-the-render while every other artefact was
built and waiting.

⚠️ **WHAT THIS DOES NOT SAY.** It does not say automation may spend twice, guess at a
page, or proceed past a login wall. Those are the conditions above, and they are
conditions rather than suggestions **because the failure modes were named before the
ruling was made**: a screenshot is a proxy for a live page (fault #1), and a marker
written after a click cannot survive a crash between the two (the hero-jobs double-spend
lesson, where deleting the PNGs did not invalidate a stored job id).

## A26 · 11 Aug 2026 — 🚫 AUTO-RENDER IS BROWSER AUTOMATION, NEVER THE API · **Jodie**

> **"HEYGEN AUTO-RENDER = browser automation, NEVER the API/Make"**, alongside
> **"generate AT MOST ONCE per episode"**.

**Recorded here 17 Aug 2026, and the delay is the point.** This ruling was made on 11
August and lived only in a Cowork doc and in one machine's memory — so the engine that
implements it could not read it, and a session that reasoned from `heygen-render-routes`
alone would have concluded auto-render was refused outright. **A rule that lives only in
Cowork is invisible to the machine**, which is the whole reason this file exists.

**Why browser and never API:** the two billing pools are separate. The account's API
wallet is empty, so a REST/CLI render spends **real dollars** (~$21/episode at Avatar IV
photo-avatar rates) while the web app spends the **plan credits** already paid for. The
MCP route cannot hold the background either — its only video-creating tool takes no
background parameter, and Gordon's grandstand comes from the locked template's scene, not
from his avatar. A template-free render puts him in a corporate office.
**Does NOT cover:** anything about WHO clicks — that is A25 above.
