# DESIGN — the build authors its own assets

**Status: PROMPT 1a COMPLETE. AGREED, NOT BUILT. No code has been written.**
*Written 28 July 2026 by Claude Code, across seven Jodie rulings of the same date.*

| What | State |
|---|---|
| The design (frame × block, scope, schema, guards) | **AGREED** |
| The ten spoken midroll lines, v2 | **🔒 APPROVED AS A BATCH — never rewritten** |
| The standing chip wording + its two rationales | **DECIDED** (EP12's) |
| The nine-episode verbatim window, ten-line pool | **RULED** |
| Name-the-video-at-every-ask | **RULED** — midroll + outro; narration exempt |
| The 12px cover gutter | **DEFERRED — flag, do not touch** |
| Implementation | **1b SHIPPED** (`3b4e1cf`). **1b′ SHIPPED** (the skill/registry/rail move). **1c PART ONE SHIPPED** — the template library, `author_cards.py`, `card_check.py` and their tests. The rest of 1c (cover / thumbnail / e-book authoring and the `providers.py` wiring) is **not started**. |
| §4's coverage claim | **CORRECTED 28 Jul 2026 after building it** — see the box at the top of §4. Only `price` and `checklist` repeat; EP11 is 75% bespoke. |
| EP11 + EP12 | **PUBLISHED to YouTube, 28 Jul 2026.** Two defects found afterwards are recorded in §14a as note-only. |

> ⚠️ **This document is a RECORD of the 1a design, not a live spec.** Two things it
> describes have since changed and are NOT to be followed from here:
> **(1)** the `pp-episode-production` skill is **in this repo**, not on Drive (§10 is
> updated; the reasoning that said "moving it breaks the engine" was three path
> literals and one `.env` lookup).
> **(2)** the two `.reference.py` integrity gates **no longer exist** — they were
> replaced on 28 Jul 2026 by a `git status --porcelain` comparison against HEAD
> (`engine/gitgate.py`). Wherever this document says "update the reference in the
> same commit", there is no reference to update; just commit the file.

*On the go-ahead this becomes the implementation brief and the thirteen rule changes in
§9 land in `PP-STANDARDS.md` and the two skills.*

---

## 1. The problem, in one table

The engine renders assets it never authors. On EP12 that produced **eight stop points,
of which Hugh could clear two.**

| # | Step | What stopped it | Hugh? |
|---|---|---|---|
| 1 | create | Wrong article pasted (EP11's text, 98.7% match) | **NO** |
| 2 | `script_sync` | Doc not link-shared, HTTP 401 | **YES** |
| 3 | `script_sync` | Approved before sharing, engine claimed and parked | **YES** |
| 4 | `ebook_cover` | No `cover.html` staged | **NO** |
| 5 | `cards_render` | Zero card HTML pages existed | **NO** |
| 6 | `ebook_pdf` | No `ebook/*.html` | **NO** |
| 7 | `thumbnail` | No `thumbnail/*thumbnail*.html` (latent) | **NO** |
| 8 | `youtube_copy` | No `output/*youtube*.txt` (latent) | **NO** |

Halts 4-8 are five faces of one bug. Each is an `EngineFlag(… "Stage it, then clear
this flag")` — a message that asks a browser operator to write HTML, stage a PNG into a
directory that does not exist yet, and run a headless render.

**Per PP-STANDARDS §WHAT DESERVES A GATE that is the worst class of halt there is:**
one the operator can neither judge nor dismiss.

## 2. The governing principle

> **Turn every halt Hugh cannot clear into either no halt at all, or a halt he can clear
> by looking.**

## 3. Scope — the build authors the FURNITURE only (Jodie, 28 Jul 2026)

Automating an editorial decision would breach *automation eats chores, never decisions* —
the same rule that keeps the Script Gate human forever.

| Asset | Today | Agreed |
|---|---|---|
| `ebook/cover-src/cover.html` | halt (NO) | **authored** from the standing template + `packaging` |
| The 16 card pages | halt (NO) | **authored** from the template library + `episode.json` |
| `thumbnail/ep-NN-thumbnail.html` | halt (NO) | **authored**; hero choice + registry row stay a decision |
| E-book **shell, layout, figures** | halt (NO) | **authored** — the layout is the beautiful part and it templates cleanly |
| E-book **BODY** | halt (NO) | **editorial.** Straight from the article, §0a fidelity, no normalising. Drafted, then a *read-this* flag |
| `output/*youtube*.txt` | halt (NO) | **editorial.** Stays Claude Code's to write; the flag text stops naming Cowork |

Both remaining halts convert from *"author the pages"* (impossible in a browser) to
*"read this and say yes"* (a click). That is the whole point of the exercise.

---

## 4. The template library — FRAME × BLOCK

**Rejected: a flat list mixing `panel-push`/`fullscreen` (the frame) with `stat`/`ratio`
(the content).** Held flat you need `stat-fullscreen`, `stat-panel`, and every other
pairing. The EP11/EP12 corpus factors cleanly into two independent axes.

### ⚠️ CORRECTED 28 JULY 2026, AFTER BUILDING IT — READ THIS BEFORE THE TABLE BELOW

**The claim this section made was too strong, and the golden-file test found it out.**
All 24 content cards were read line by line during 1c. What the corpus actually supports:

- **Only TWO blocks have two precedents: `price` and `checklist`.** The 13-line diff below
  is real, but it is evidence for `price` alone. The other **nine blocks generalise from a
  single card each**, which makes them reasonable templates but not demonstrated ones.
- **Coverage is badly lopsided. EP12: 10 of 12 cards. EP11: 3 of 12 — EP11 is 75%
  bespoke.** The library was derived from EP12 and mostly describes EP12.
- **Three precedent claims in the table below were wrong.** They are different shapes, not
  fit variants of one shape:

| Claimed | Actually |
|---|---|
| `slate` = EP11 c04 + EP12 c09 | c04 is a **column of key/value rows**; c09 is a **row of stacked cells** |
| `compare` = EP11 c10 + EP12 c04 | c10 is a **then/now pair of multi-row panels** with a linking arrow; c04 is **two mark/key/value columns** |
| `stat` = EP11 c03 + EP12 c01 | c03 is **hero figure + odds plaque + two summary cards**; c01 is **figure/sub/payoff/note** |

The table below has been corrected to list only the precedent each block actually has.
Candidate blocks for the three orphaned shapes — `rows` (EP11 c04), `versus` (EP11 c10),
`namelist` (EP11 c07) — were **deliberately not built**: each would have exactly one
precedent, and inventing them to make a coverage number look better is the same mistake in
a different costume.

> **THE HONEST CONCLUSION (Jodie, 28 July 2026).** Templates speed up the repetitive cards.
> **A meaningful share of every episode stays hand-made, and that is the expected outcome,
> not a shortfall to engineer away.** §4 Layer 4 already said bespoke is first-class; this
> is what that costs and what it buys. Judge the library by whether it removes a halt Hugh
> cannot clear, not by what percentage of cards it swallows.

### The evidence

`ep11-c05-turridu-12-1.html` vs `ep12-c11-10-1.html` is a **13-line diff, nine of which
are the comment**:

```
< .name{font-size:130px;…}      > .name{font-size:126px;…}
< .quiet{margin-top:26px;…}     > .quiet{margin-top:24px;…}
< lbl>The Actual Winner         > lbl>The Payoff
< name>Turridu                  > name>Joie Denise
< price>12/1                    > price>10/1
< said>a top chance…            > said>a quality galloper resuming…
```

Two of those are font-size nudges to fit a longer string. **The cards are already a
template, instantiated by copy-paste. Nobody wrote the template down.** Same for the
title card (EP11 vs EP12 differ in four things) and the thumbnail (four things).

### Layer 1 — FRAMES (2)

Everything outside the body block, taken verbatim from the shipped cards.

- **`fullscreen`** — `body{background:#1F1F1F}`, `.card` full-bleed 1920×1080, padding
  `84px 110px`.
- **`panel-push`** — `body{background:#00FF00}` (chroma-keyed in pass B at
  `0x00FF00:0.28:0.06`, overlaid at `x=36:y=312`, scaled to 810 wide), `.panel` inset
  `left:120 top:96 1680×888 radius:40`.

Both carry the identical scaffold: `.eyebrow{#rule + #eyb}` → `#hl` (Anton) → **★ body
block ★** → `.logo` (right 110 / bottom 56, 214×65), the `body.print{…}` theme, and the
`ppInit([...])` + `?print=1` switch.

### Layer 2 — BLOCKS (11)

The ★ body ★. Each is a partial with a declared content schema.

Precedents below are the ones that **actually exist**, corrected 28 Jul 2026 against the
shipped corpus. Two precedents means the shape was observed to repeat; one means it is a
reasonable template nobody has yet reused.

| Block | Renders | Precedent | Repeats? |
|---|---|---|---|
| `price` | `.priceline` — giant price beside a said-line | EP11 c05, EP12 c11 | **yes** |
| `checklist` | N ticked questions, staggered reveal | EP11 c02, EP12 c06 | **yes** |
| `stat` | huge Anton figure + sub + payoff + note | EP12 c01 | one only |
| `slate` | 2-4 stacked key/value cells + optional warn line | EP12 c09 | one only |
| `compare` | two mark/key/value columns + note | EP12 c04 | one only |
| `steps` | 2-3 cascading cards **in flow** + note | EP12 c10 | one only |
| `bars` | 2-3 labelled bars, `scaleX` wipe, length **computed** from the traced figure | EP12 c03 | one only |
| `ratio` | N marks, M highlighted | EP12 c12 | one only |
| `statement` | one big line + one small line | EP12 c08 | one only |
| `slots` | tag + labelled slots, **values may be null** | EP12 c02 | one only |
| `chips` | pill row + foot line | EP11 c01 | one only |

*(EP11 c02's questions and EP12 c02's chip row were previously cited as second precedents
for `checklist` and `chips`. The first is correct; the second is not — EP12 c02's chips are
a sub-part of the `slots` block, not an instance of `chips`.)*

### Layer 3 — STANDING (4)

No per-episode content; copied byte-identical.

- `title` — hero image + `packaging` + the series-part rule
- `end-card` — composites `overlay/export/ebook-cover.png`
- `warranty` — locked, never redesigned
- **`midroll-lowerthird` — NEW to this list (Jodie, 28 Jul 2026).** Previously authored
  per episode; now fixed furniture. See §7.

### Layer 4 — BESPOKE, first-class

`"block": "bespoke"` means *this page is hand-authored; do not generate, do not
overwrite*. EP12's `c05` (hand-placed ring sweep) and `c07` (hand-tuned distance ruler
— I checked, the tick positions are not a linear scale) declare it.

**This is what protects the craft.** Jodie on the rebuilt EP11: *"I love how you have a
mix of whole screen and on the screen with the host."* Templates are the **floor, not
the ceiling.** Expect 2-3 bespoke cards an episode, as EP11 and EP12 both had.

### Honest coverage — MEASURED 28 July 2026, both episodes

Counting the 12 content cards per episode (the standing pages are copied, not authored):

| | Block-covered | Bespoke |
|---|---|---|
| **EP12** (the episode the library was derived from) | **10** | 2 — c05 ink rings, c07 non-linear ruler |
| **EP11** (the episode it had not seen) | **3** | **9** |

**EP11 is 75% bespoke.** That gap is the honest measure of how far the library generalises,
and it is why the golden-file test was worth running before writing anything else.
The nine: c03 hero+plaque+cards · c04 key/value rows · c06 race lane · c07 beaten-horse
list · c08 horizontal timeline · c09 price+cells · c10 then/now pair · c11 magnifier ·
c12 arithmetic line.

---

## 5. How `episode.json` drives each card

### The gap today

`cards[]` carries `id · beat · cue · eyebrow · headline · detail · hero · layout`. A
template can consume four of those. **The card's actual content is prose in `detail`:**

```json
"detail": "Hero figure: a huge orange '60 DAYS+' slams in, with 'RESUMING FROM A SPELL'
           beneath it. Then the payoff line lands in white: 'most will lose at their
           first run back'. Small grey footnote, the article's own words: 'That's an
           iron-clad fact.'"
```

A generator that mines strings out of English prose is doing exactly the
invent-plausible-data thing the standard forbids. **And there is no trace field anywhere
in the schema**, so PP-STANDARDS §2a (every figure printed beside its source sentence,
hard fail) has nowhere to live.

### The additions

`detail` **stays exactly as it is** — it is the human-readable spec and the audit trail.

```jsonc
{
  "id": "C1",
  "beat": 2,
  "cue": "sixty days or more",
  "eyebrow": "START HERE, AND BE HONEST",
  "headline": "MOST OF THEM LOSE",
  "layout": "fullscreen",          // FRAME — existing field, narrowed meaning
  "block":  "stat",                // NEW — which body template
  "content": {                     // NEW — validated against the block's schema
    "figure":     "60 Days+",
    "figure_sub": "Resuming from a spell",
    "payoff":     "Most will lose at their first run back.",
    "note":       "“That’s an iron-clad fact.”"
  },
  "trace": {                       // NEW — REQUIRED for every figure-bearing key
    "figure": "Most horses which are resuming from a spell of 60 days or more will lose
               first-up. That's an iron-clad fact."
  },
  "detail": "…unchanged prose spec…"
}
```

### The empty-slot case is first-class, not a workaround

```jsonc
{ "id": "C2", "layout": "panel-push", "block": "slots",
  "content": {
    "tag": "First-up",
    "slots": [ {"k": "Wins first-up", "v": null},
               {"k": "Placings",      "v": null} ],
    "said":  "Years ago we didn’t have this. <b>Now we do.</b>",
    "chips": ["Best Bets"]
  },
  "trace": { "slots": "The First-up line tells you how many times a horse has won
                       first-up and how many times it has run a placing." } }
```

**Explicit `null` renders the dotted empty slot. A MISSING key HALTS.**

That distinction is the EP12 `_placeholder` lesson applied directly: *a placeholder that
looks like data is worse than an empty dict, because it defeats the very "is it set?"
check meant to catch it.* Explicit null says **a human decided this is empty**. Absence
says **nobody decided.**

Standing cards need no new fields — TITLE reads `packaging.ebook_title` +
`packaging.byline` + the series-part rule; END reads the rendered cover; WARRANTY is a
straight copy.

---

## 6. Never fabricate — three guards, in order

1. **Schema validation before render.** Unknown `block`, unknown key for that block,
   missing required key → **HALT**, naming the card and the key. Not a warning.
2. **Trace-or-halt.** Any `content` value containing a digit (and any horse or race
   name) must have a `trace` entry, and that entry must be a **literal substring of
   `docs/EP-NN-source-article-*.md`**, normalised for whitespace only. Not fuzzy, not a
   similarity score. If it is not in the article verbatim, the build stops. This is
   §2a finally enforced somewhere a machine can act.
3. **The generator cannot invent a string.** There is no LLM in it. It is a substitution
   engine: it copies a value from `content` into a slot, or it fails. **There is no code
   path that produces text absent from `episode.json`.** That is the structural answer
   to "never fabricate" — not a rule the generator follows, a capability it does not
   have.

And per §0a's mirror: **the generator never normalises.** `firstup` stays one word,
`joie Denise` stays lower-case, wherever they appear in `content`.

---

## 7. Local HTML render only — never Higgsfield

The generator emits HTML into `overlay/export/`, `ebook/cover-src/`, `thumbnail/` and
`ebook/`. The **existing** `render_cards_batch.py` / `render_still.py` render them in
local headless Chromium. **No new render path, no new network call, no MCP tool.**

The only Higgsfield calls in the engine are `submit_broll` (`providers.py:561`) and
`_generate_heroes` (`providers.py:411`). Neither is touched. Higgsfield produces
*photographs* — b-roll, cover heroes, thumbnail heroes — and nothing else, ever.

**Hard engine constraint carried forward:** every animation the templates emit is an
`element.animate()` keyframe spec through `ppInit`. No count-ups, no `setInterval`, no
canvas — `ppSeek(ms)` is how frames are drawn, and JS-driven effects render **frozen and
silently wrong** with the batch reporting success. The generator emits only from a fixed
vocabulary of keyframe patterns (fade, translate, scale-slam, `scaleX` wipe, staggered
reveal). Same principle as guard 3: **it cannot emit a broken animation because it
cannot emit an arbitrary one.**

---

## 8. Midroll (Jodie, 28 Jul 2026)

### 8a. The ON-SCREEN CHIP is identical every episode

Fixed furniture. One standing lower-third in `assets/`, copied byte-identical like
`end-card-template.html` and `warranty-slide.html`. **No pool, no rotation, no
per-episode authoring.** Nothing checks chip text today, so no rule breaks.

Two fixes must be carried into the standing file (both were EP11 lessons, both are in
EP12's chip, neither may regress):
1. The chip is **opaque `#121212`**. At 92% the green key field showed through and it
   rendered dark green, not charcoal.
2. **Both icons are a WHITE glyph on a SOLID orange tile.** The like icon was once an
   orange thumb on a 16% orange wash and was invisible at broadcast size.

**✅ DECIDED (Jodie, 28 Jul 2026) — the standing chip is EP12's wording:**

> **Doing its job? Like & Subscribe**
> new episodes daily · Practical Punting

Chosen over EP11's *"Worth five minutes? / a fresh video every day"* because it names both
actions explicitly and already carries both fixes below.

**WHY THE TWO CSS DECISIONS EXIST — record this in the standing file itself, so neither
can regress by someone "tidying" it:**

| Rule | Why | What went wrong without it |
|---|---|---|
| Chip background is **opaque `#121212`**, never a transparency | The card sits on a `#00FF00` chroma-key field | At 92% opacity the green field showed **through** the chip, so it rendered dark **GREEN**, not charcoal, and the contrast died |
| Both icons are a **WHITE glyph on a SOLID orange tile** (`rgba(218,83,44,0.95)`) | Broadcast size is small; the glyph needs maximum separation from its tile | The like icon was once an **orange thumb on a 16% orange wash** — effectively invisible at playback size |

Both were EP11 lessons, both are in EP12's shipped chip, and the standing file must carry
the reasons beside the values.

**Note the cadence trap:** *"new episodes daily"* is baked into a standing asset. When
cadence moves to weekly it is a one-file edit — which is an improvement on today, where
it lives in every episode's chip separately.

### 8b. The SPOKEN midroll — a pool of exactly TEN, used strictly in order

- Ten pre-approved lines, `L0`…`L9`. **Episode N takes `L[N mod 10]`.**
- The pool **WRAPS rather than exhausting**, so the build never halts for this.
- The build **never invents, never paraphrases, never rewrites.** It substitutes one
  paragraph.
- `episode.json → build.midroll.line_id: "L3"`, and the registry records `ep → line id`
  exactly as `broll-registry.md` records clips.

### 8c. ⚠️ THE OFF-BY-ONE THAT WOULD HARD-FAIL EVERY EPISODE FROM EP23

A pool of exactly ten used in strict order **recurs at exactly ten-episode intervals**.
`L3` is used at EP13 and again at EP23.

If the softened check reads *"never verbatim within the **last 10** episodes"*, then at
EP23 the window is EP13-EP22 — **which contains EP13.** The guard would hard-fail every
single episode from EP23 onward, forever.

**✅ RULED (Jodie, 28 Jul 2026): keep TEN lines, make the window NINE. No eleventh line.**

> **HARD FAIL if the midroll paragraph is byte-identical to that of any of the NINE
> immediately preceding episodes** (by episode number, not file mtime).

With a strict ten-cycle the nearest prior use is always exactly ten back, so it passes.
Any accidental duplication closer than that fails. That is precisely the intent.

### 8d. Implementation notes for the softened check

- Both `render_ready.py` (pre-render, HARD) and `qc_episode.py` (post-assembly, HARD)
  currently glob **every** `PP-EP*/docs/spoken-words.txt` with no ordering and no
  window. They must instead parse the episode number from the folder stem
  (`PP-EP(\d+)`), sort numerically, and compare against the nine nearest **below** the
  current number.
- **`PP-EP98/` exists on disk.** Ordering by episode number rather than mtime naturally
  keeps it out of any real episode's window. Ordering by mtime would not.
- Folders are renamed at Stage-8 close-out; the `PP-EP(\d+)` stem survives that.
- **`qc_episode.py` and `engine/qc_episode.reference.py` must change in the SAME
  COMMIT** or every build dies at the integrity gate (`providers.py:816-837`).

### 8e. NEW STANDING RULE — NAME THE VIDEO AT EVERY ASK (Jodie, 28 Jul 2026)

> **Wherever Gordon ASKS something of the viewer — like, subscribe, get the e-book — name
> it "this video", never a bare "this". Clarity drives action, and an ask is the one place
> vagueness costs something.**
>
> **Narration is left alone.** The opening framing line stays as written: it is a hook, and
> *"this time"* against *"last time"* is doing different work there. Forcing "video" into
> it makes it clunky.

**Written as a principle, not a list of places, so it generalises to asks we have not
invented yet.** Today it binds two: the **midroll like/subscribe invitation** and the
**outro e-book line**. Any future CTA inherits it without anyone having to remember.

**Where it came from:** Jodie's own hand-edit at the EP12 Script Gate. She changed *"If
this is doing its job"* to *"If this **video** is doing its job"* in the Doc before
approving. That was one of only two edits she made to twenty-six paragraphs, and it was
**not reported at the time** — it surfaced in the word-arithmetic reconciliation
afterwards. It is now a rule rather than a silent correction, which is the whole point of
writing it down.

**Density — how it is applied in the pool:** once per line in the **value-hook clause**
(the place Jodie's edit landed), plus any later sentence where a bare "this" plainly means
the episode (L4's *"This video isn't"*, L7's *"This video is just a bloke reading the
form"*). **Deliberately not everywhere** — five instances of "video" in eighty words reads
as a machine filling a slot, and Gordon would not say it. ✅ *Density confirmed correct by
Jodie, 28 Jul 2026: "once per line in the value hook, plus L4 and L7. Don't add more."*

**✅ THE OUTRO ALREADY COMPLIES — only PP-STANDARDS is out of step.** Verified 28 Jul:
- `docs/PP-episode-outro-standard.md:10` — *"the link's below **this video**"* ✓
- `pp-episode-script/SKILL.md:284` — *"the link's just below **this video**"* ✓
- **`docs/PP-STANDARDS.md:364` — *"Point to the FREE E-BOOK (soft CTA, 'link below', keep
  it beside you on race day)"* ✗ no "video"**
- EP11 and EP12 both shipped *"The link's just below this video."* ✓

So extending the rule to the outro is **not a change to how scripts are written** — it is
bringing the canonical file into line with its own two subordinate documents and with two
shipped episodes. Cheap, and it closes a drift nobody had noticed.

### 8f. The trade-off being accepted

The pool **bakes the cadence line into ten frozen lines.** Today the line is reworded
per episode, so it tracks reality automatically. Once frozen, **the day cadence moves
from daily to weekly, all ten lines go stale at once and need a fresh batch approval.**
That is a real cost, accepted knowingly in exchange for never inventing wording.

---

## 9. Exact wording being replaced

Thirteen sites. Nothing is deleted without a replacement.

| # | File | Lines | What goes |
|---|---|---|---|
| 1 | `docs/PP-STANDARDS.md` §Mid-video | 391 | *"**VARY it every episode (do NOT reuse verbatim):** Hugh approved the style; unlike the standing outro, reword this slightly each episode — same shape, beats and tone, fresh phrasing — so it never sounds canned."* |
| 2 | `docs/PP-STANDARDS.md` §Mid-video | 395-398 | *"**Example variants (style approved — rotate / reword each episode):**"* + the three numbered examples → becomes **the pool of ten, used in order** |
| 3 | `docs/PP-STANDARDS.md` §END SEQUENCE item 4 | 356-359 | *"the midroll invitation is REWORDED every episode (verbatim reuse across episodes = QC HARD FAIL…)"* → *"comes from the standing pool of ten, used in order; verbatim reuse **within the previous nine episodes** = QC HARD FAIL"* |
| 4 | `docs/PP-STANDARDS.md` §Standing OUTRO item 4 | 381 | *"Same principle as the midroll chip (reworded each episode)"* — **now factually wrong**, the chip is fixed. Replace the analogy |
| 5 | `docs/PP-STANDARDS.md` §Motion-graphic cards | 255 | additive only: the lower-third is standing furniture, copied not authored |
| 6 | `docs/PP-midroll-invitation-standard.md` | 13-14 | the whole *"## VARY it every episode (do NOT reuse verbatim)"* section |
| 7 | `docs/PP-midroll-invitation-standard.md` | 19-22 | *"## Example variants (style approved — rotate / reword)"* + 3 examples → the pool |
| 8 | `.claude/skills/pp-episode-script/SKILL.md` §4E | 272-274 | *"**VARY the wording every episode** — same shape, fresh phrasing; never reuse verbatim… Also **vary the 'noise out there' line**"* |
| 9 | `.claude/skills/pp-episode-script/SKILL.md` checklist | 390 | *"Midroll: fixed shape, **reworded fresh**, cadence line current…"* |
| 10 | `scripts/render_ready.py` 64-84 · `scripts/qc_episode.py` 430-450 · `engine/qc_episode.reference.py` | | all-episodes glob → nine-episode window, `PP-EP(\d+)` sorted numerically |
| 11 | `docs/PP-STANDARDS.md` §Mid-video **Shape (fixed)** | 390 | **ADD** the name-the-video-at-every-ask principle (§8e) |
| 12 | `.claude/skills/pp-episode-script/SKILL.md` §4E **Fixed shape** | 268-269 | **ADD** the same, so a hand-written script obeys it too |
| 13 | `docs/PP-STANDARDS.md` §Standing OUTRO item 2 | 364 | *"Point to the FREE E-BOOK (soft CTA, **'link below'**, keep it beside you on race day)"* → **"the link's just below this video"**, matching what the outro standard, the script skill and EP11/EP12 already say |

**New file:** `docs/midroll-line-pool.md` — the ten approved lines **and** the `ep → line
id` registry in one file, mirroring `broll-registry.md`'s shape. **Tier 3** (channel
furniture, not method material), so the repo is its correct home.

---

## 10. Files touched

**Engine — `episode-studio/engine/` (repo)**
- `providers.py` — `render_ebook_cover` (623) · `render_cards` (655) · `build_ebook`
  (849) · `build_thumbnail` (860): flag → **author, then flag only if authoring fails**.
  `save_youtube_copy` (879): stays a flag, text corrected.
- `providers.py` — fix the five stale "Cowork writes it" strings: **347, 391, 545, 855,
  884**. `WHO-DOES-WHAT.md` says Cowork writes *not one line of anything that ships*;
  these send the operator to the wrong place.
- `providers.py` — `_clip` (321) raises `RuntimeError`, so a missing card burns three
  full Chromium batch renders before flagging. Make it an `EngineFlag`.
- **`engine.py` — no change to `PHASES` or `check_locked_order`.** Authoring happens
  *inside* the existing steps. **The locked order cannot regress if the step list does
  not move.**

**Production skill — `.claude/skills/pp-episode-production/` (IN THIS REPO)**
*(moved off Drive 28 Jul 2026. This section used to say "stays on Drive: moving it breaks
the engine" — that turned out to be three path literals and one `.env` lookup, all fixed.)*
- `assets/cards/frame-fullscreen.html`, `frame-panel.html`, `blocks/*.html`
- `assets/midroll-lowerthird.html` — the new standing chip
- `scripts/author_cards.py` · `author_cover.py` · `author_thumbnail.py` · `author_ebook.py`
- **`scripts/card_check.py`** — the missing overlap/clip checker
- `scripts/build_figures.py` — fix `is_print` (73) and the `.card`/`.panel` selector (76)
- `SKILL.md` — the print scaffold (113-124) to match reality; the `≥1s` line (342) to
  read as a preference, per Jodie's ruling that adjacency is fine
- `assets/README.md` — delete the superseded frame-picking section (59-66)
- `assets/youtube-thumbnail-template.html` — add `.part`; fix the `.eyebrow`

**Docs — repo `docs/`**
- `PP-EPISODE-JSON-SPEC.md` — the `block`/`content`/`trace` schema; the ownership header;
  the missing sections (`cue`, `build{}`, `thumbnail_hook`, `signature_concepts`, `source`)
- `PP-STANDARDS.md` — the ten wording sites; **and line 4, which still says its own
  location is the Drive path that is now a 521-byte tombstone**
- `PP-THUMBNAIL-TEMPLATE.md` · `pp-episode-script/SKILL.md` — the `+3.0s` entry rule and
  the count-up ban
- `thumbnail-hero-registry.md` — the missing EP12 row and Jodie's unanswered ruling
- new `midroll-line-pool.md`

---

## 11. What genuinely cannot be templated

The build generates a sensible default and **surfaces it as a look-at-this** — never
guesses, never silently ships.

1. **Title-hero `object-position`.** EP11 needed 32%, EP12 needed 62%; at 32% EP12's
   hero cropped to empty sky with the jockeys sliced off the bottom. Per-image, always.
   → render it, then `needs_look: "check the hero crop"` with the PNG on the board. **A
   halt Hugh CAN clear — he looks at a picture and says yes.**
2. **Thumbnail scrim strength and text placement.** The template's own header: *"this is
   the craft — VIEW the hero first, then decide."* Same treatment.
3. **Thumbnail hero CHOICE + registry check.** Cannot be automated while the rule itself
   is unresolved (`thumbnail-hero-registry.md` still says *"Needs Jodie's ruling before
   EP12"*, and EP12 shipped without it).
4. **The e-book article BODY.** §0a fidelity is the whole job — reproducing `firstup` and
   lower-case `joie Denise` is *deliberate non-normalisation*, and any automatic markup
   pass will silently tidy them.
5. **YouTube title + description.** EP12's call — that the 1995 headline promises a value
   factor the article never delivers, so don't inherit a promise the episode can't keep;
   and keep Joie Denise's 10/1 out of the description so a long price can't read as a tip
   — is not a substitution.
6. **Which cards are bespoke.** Declaring `block: "bespoke"` is a design decision.

### Designed out rather than delegated

**The C10 collision is NOT a human judgement call.** It happened because the footnote was
absolutely positioned at the right of `.steps` while the third step card started at
`left:360` and ran 940px wide, so they overlapped 1040-1300px. The fix was normal flow.
**Blocks are flow-only, which makes that entire class of bug unrepresentable** — the same
way the cover's flow band made cover overlaps impossible by construction after EP09.
`card_check.py` is the backstop, not the primary defence.

> **✅ RESOLVED 28 July 2026 — the look and the guarantee, not one or the other.**
> Flow-only first looked like it cost the deck-of-cards cascade: the shipped steps overlap
> each other by 8px, which came from absolute offsets (`top:0/150/300` against a 158px
> card), and a naive flow version separated them by a 12px gap instead.
> **Jodie's answer was a third option: keep normal flow, restore the overlap with a
> NEGATIVE MARGIN.** `.st + .st{margin-top:-8px}`. Measured result: **8.0px card-to-card
> overlap, identical to shipped**, while every box stays in normal flow — so the note is
> still the next box down and cannot be overrun by any step count or string length.
>
> It also fixed a defect nobody had noticed. The shipped `.steps` carried a hand-set
> `height:424px` while its own content runs **458px**, so the third card overhung its
> container and the note grazed it by 8px — a smaller instance of the very bug that was
> fixed. In flow the container is its content, so the note clears by the full 26px. The
> note lands at y=951.4 in both; only the stack sits 34px higher, which is exactly the
> container-height bug not being reproduced.
>
> **The general lesson: "flow-only" constrains WHERE a box may be, not how it may look.
> A negative margin is still flow.**

**Font-size auto-fit** is also automatable, not a judgement: the two font nudges between
EP11 c05 and EP12 c11 (130→126, 26→24) are pure text-length fitting. Measure the rendered
overflow and step down.

---

## 12. New QC checks (per the QC-per-fix rule)

Every one of these is a lesson currently written down but not enforced.

| Check | Level | Catches |
|---|---|---|
| `card_check.py` — overlap / clip / logo collision on every rendered card | **HARD** | EP12's C10, which would have shipped into the video **and** e-book figure 10 |
| `trace` present + literal substring of the source | **HARD** | EP11's C7 fabricated placings |
| Schema validation of `content` against `block` | **HARD** | missing-key silence |
| `layout` must be a MIX, never all-fullscreen | **HARD** | already a Hard-never; nothing checks it today |
| Midroll verbatim within the previous **nine** episodes | **HARD** | the EP08 HeyGen mangle |
| Title-hero crop review | **FLAG** (clearable) | EP12's sliced jockeys |
| Thumbnail placement review | **FLAG** (clearable) | per-hero craft |
| E-book body read | **FLAG** (clearable) | §0a fidelity |

---

## 13. Risks

1. **Templating makes fabrication EASIER.** A `stat` block with an empty `figure:` slot
   is an invitation to fill it. **Trace-or-halt is the only thing standing against this.
   If that guard is weak, the whole proposal is net-negative.**
2. **A halt is information; removing it removes the look.** EP12's two worst defects —
   the C10 collision and the sliced-off jockeys — **were found only because the build
   stopped and a human authored the pages by hand.** Generate them and nobody looks.
   Mitigated by `card_check.py` and the crop-review flag, but per *"checkers verify
   structure, not appearance"* neither is a substitute for eyes.
3. **Series sameness.** Eleven blocks × two frames is twenty-two shapes. By EP25 the
   channel looks like a slide deck. Mitigated by keeping `bespoke` first-class.
4. **Overwrite risk.** If someone hand-fixes a generated page and the next run
   regenerates it, the fix vanishes. **Rule: never overwrite an existing file** — this
   matches RealProvider's existing find-or-build policy exactly. Generated pages carry a
   marker comment; a page without one is treated as hand-authored and left alone.
5. **The QC integrity gate will kill the build** if `qc_episode.py` and its committed
   reference drift by one byte.
6. **Scope.** Five engine steps, four new scripts, a template library and eight
   documents. Not a one-sitting change, and per Jodie's own ruling **it must not start
   while an episode is mid-build.**

---

## 14. Test plan

**The golden-file test is the one that matters, and it is free** — EP11 and EP12 are
both on disk, complete, with shipped and approved outputs.

1. **Regenerate EP11's and EP12's pages from their own `episode.json` + the new library.
   Render both sets. Diff the PNGs, not the HTML.** Target: the ~11 block cards per
   episode render pixel-equal or differ only explicably. **Any card that comes out
   different is either a template bug or an un-modelled variation, and both are
   findings.** If the library cannot reproduce two episodes it has already seen, it
   certainly cannot handle EP13.
2. **Negative tests, each must HALT in plain English:** missing `trace` on a figure ·
   `trace` not a literal substring of the source · unknown `block` · missing required
   content key · `layout` all-fullscreen.
3. **The `null` test:** `"v": null` renders the dotted empty slot; the key *absent*
   halts. Both, explicitly.
4. **Run `card_check.py` against EP12's C10 AS IT WAS BEFORE THE FIX** (absolute-
   positioned note, overlap 1040-1300px). **It must FAIL.** A checker that only passes
   things which already pass is a green light I wrote myself and must not trust.
5. **Midroll window test:** simulate EP13 through EP24 with the ten-line cycle. **EP23
   must PASS** (nearest prior use exactly ten back). Inject a duplicate at EP20 and it
   **must FAIL**.
6. **`python engine/engine.py run --mock --watch`** end-to-end: zero halts through
   `building` and `assembling`. Then `cleanup-mock`.
7. **A real dry run on a scratch copy of EP11's folder.** Nothing touches a shipped
   episode.
8. **Look at every rendered page.** Not the report — the pixels.

---

## 14a. Found by the golden-file test in EP11/EP12 — NOTE ONLY, NOTHING TO CHANGE

**Both episodes were PUBLISHED to YouTube on 28 July 2026.** Neither of these is being
fixed; they are recorded so they are not rediscovered as new.

1. **EP12 C10's fix left an 8px residue, and it has shipped.** `.steps` was given a fixed
   `height:424px` while its absolutely-positioned content runs to 458px, so the third step
   card overhangs its container and the note's line box grazes it by exactly **8.0px**.
   Sub-visual — the inked glyphs miss by a few px, which is why `card_check.py` does not
   hard-fail it. The 260px collision that was fixed is genuinely gone. Same root cause:
   absolute positioning plus a hand-set container height. **The `steps` block cannot
   reproduce it, so it cannot recur.**

2. **DATA-CONTRACT DRIFT, for a future episode — EP12 C11's headline.**
   `episode.json` records `headline: "10/1"`; the shipped card's headline is
   **"Joie Denise"**, with 10/1 as the price. The only such mismatch across 24 cards.
   It matters because the packaging-consistency check and any future authoring both read
   `episode.json` as the source of truth for what is on the card, and here it is wrong.
   **Fix forward: when a card's headline and its hero figure are different things, the
   headline field must hold the headline.** `author_cards.py` currently sidesteps this by
   taking the headline from the page during back-fill; new episodes must not need that.

## 15. Deferred, flagged, NOT to be fixed now

**The 12px white gutter on EP11's and EP12's shipped e-book covers.**
`ebook-cover-template.html` sets `body{width:1588px;height:2238px}`, but
`render_ebook_cover` (`providers.py:637`) renders at **1600×2263** when no
`cover-src/cover.png` reference exists — and neither episode has one. Verified by pixel
sample: both `ebook/cover.png` files are 1600×2263 with `(255,255,255)` at the top-right,
where the photo should reach the edge. `cover_check.py` cannot see it (it tests text
rects against `W`, and 1588 < 1600 passes).

**Both episodes are at the publish gate. Jodie's ruling 28 Jul 2026: flag it, do not
touch it, decide separately.** When it is decided, the canvas must come from ONE place
or the generator bakes the defect in permanently.

---

## 16. Contradictions found in Pass 3 and not yet resolved

Recorded here so they are not lost. None blocks this design; several are cheap.

1. Five engine flags name Cowork as the author (`providers.py` 347, 391, 545, 855, 884).
2. `PP-STANDARDS.md:4` gives its own location as the Drive path, which is now a 521-byte
   *"MOVED — nothing here is authoritative"* stub.
3. `PP-EPISODE-JSON-SPEC.md` is headed *"Cowork writes it"* and omits `cue`, `build{}`,
   `thumbnail_hook`, `signature_concepts`, `source`.
4. The skill's documented print scaffold (`.card.print`) matches no shipped card (all use
   `body.print`), so **`build_figures.py:73` reports "no print theme" on every figure of
   every episode** while the figures are in fact correct.
5. `build_figures.py:76` screenshots `.card`; panel-push cards have only `.panel`.
6. `pp-episode-script/SKILL.md:308` asks for a **count-up**; the production skill says a
   count-up renders **frozen and silently wrong**.
7. Card entry `+3.0s` vs "on or just after" — the script skill carries only the old rule,
   unmarked.
8. `youtube-thumbnail-template.html` has no `.part` and its eyebrow says *"Practical
   Punting"* where the standard locks *"How to Win at Horse Racing"*. Two episodes of
   hand-added drift.
9. `assets/README.md:59-66` still teaches pulling an MCU frame of Gordon for the
   thumbnail — superseded 23 Jul 2026 and explicitly listed as do-not-follow.
10. `pp-episode-production/SKILL.md:342` states `≥1s` b-roll/card clearance as a rule;
    PP-STANDARDS names that exact case as a recommendation Jodie overruled.
11. `_clip` failure is a `RuntimeError`, so a missing card costs three retries.
12. `PP-EPISODE-JSON-SPEC.md:74` requires a `layout` MIX; nothing checks it.
13. `thumbnail-hero-registry.md` has no EP12 row and its *"Needs Jodie's ruling before
    EP12"* question went unanswered.
14. Cards have no overlap/clip checker while the cover does.

---

## 17. APPENDIX — the ten spoken midroll lines · ✅ APPROVED (Jodie, 28 July 2026)

> **🔒 SIGNED OFF AS A BATCH, v2, 28 July 2026. THESE ARE NEVER REWRITTEN.**
> Jodie: *"APPROVED as v2. Jodie signs them off as the batch. Your density judgement is
> right — once per line in the value hook, plus L4 and L7. Don't add more. No em dashes
> needed; leave them as they are."*
>
> Changing any one of them is a new batch approval, not an edit.

Used strictly in order: **episode N takes `L[N mod 10]`.** EP13 takes `L3`, EP14 takes
`L4`, EP20 takes `L0`, and so on, wrapping forever.

Every line hits the fixed shape from §Mid-video: **soft value hook (naming the video) →
the ask (a like helps OTHERS find it) → the cadence line → a light wry nod → return to
content.** Warm, plain, wry, Australian, spoken to one person. No hype, no promises, no
urgency, no "smash that like button".

**Built to pass the render-ready scan:** no bare numerals (every number is a word), no
characters outside the safe set, and **zero em dashes** — the house punctuation uses one
per line, so if that look is wanted, say so and I will place one in each.

**None of the ten reuses EP11's or EP12's shipped wording, or the three examples
currently in the standards.** The "noise out there" beat is deliberately varied — a
crowded paddock, a good suit, loud opinions, people who have it all worked out — because
the old rule warned against leaning on the same nod every time.

**"video" placement:** once per line in the value hook, plus L4 and L7 where a later bare
"this" also plainly means the episode. Not everywhere — see §8e for why.

---

**L0**
> Quick word before we push on. If **this video** is earning its keep for you, a like is
> about the cheapest favour you can do somebody else who's after the same thing. There's a
> fresh one every day at the moment, weekly further down the track, so a subscribe saves
> you going looking. Racing's never short of loud opinions. I'd rather the careful ones
> found the people who want them. Right, where were we.

**L1**
> Hold on a tick. If you're getting value out of **this video**, a like helps it find the
> next bloke doing the same homework you are. We're going out daily just now, weekly later
> on, so subscribe and they'll turn up without you chasing them. There's a lot of shouting
> in this caper. The quiet stuff deserves a hearing too, and it doesn't get one on its own.
> Anyway, on we go.

**L2**
> One small thing, then we'll get back to it. If **this video** has done you any good, a
> like nudges it toward somebody else who'd want it, which is the whole point. A new one
> lands every day for now, weekly in time, so subscribe and you won't have to hunt for
> them. Every second voice out there has a system. Not many of them have a method. Righto,
> back to the form.

**L3**
> Before the next bit, one honest ask. If **this video** has been worth your while, a like
> is what puts it in front of the next person, and it costs you nothing at all. Daily for
> the moment, weekly down the road, so subscribe and they'll come to you. You could fill a
> week with people telling you they've cracked this game. I'd sooner the sensible stuff
> reached the folk after it. That's it, back to it.

**L4**
> A short interruption, and I'll keep it short. If **this video** is helping, a like
> carries it a bit further than it would ever go on its own. There's one going up every day
> just now, weekly later, so a subscribe means you don't miss them. Half the noise about
> racing is somebody selling something. **This video** isn't, and I'd like the people who'd
> use it to be the ones who find it. Enough of that, where were we.

**L5**
> Just a moment before we carry on. If you've found something in **this video** worth
> having, a like is how the next person stumbles across it, and that's how these things
> travel. Fresh one daily at the moment, weekly a bit further on, so subscribe and they'll
> keep arriving. It's a crowded paddock out there. Most of what's in it is confidence
> rather than form study. Now then, back to the horses.

**L6**
> Pause there a second. If **this video** has been worth your time so far, a like tells the
> thing to show it to somebody else like you, which is all I'd ask of you. New ones go out
> every day for now, weekly down the track, so subscribe and you'll not have to look.
> There's more confidence about this game than there is homework. I know which of the two
> I'd trust. Right you are. Where were we.

**L7**
> Small detour, then we're done with it. If **this video** is landing for you, a like sends
> it out to the folk it was made for, and it does more for them than it ever does for me.
> We're daily just now, weekly in time, so subscribe and they'll find you instead. Plenty
> of tips flying about, most of them somebody's guess in a good suit. **This video** is
> just a bloke reading the form. Done, let's get on.

**L8**
> Two seconds, then we're back on it. If there's something in **this video** for you, a
> like puts it in somebody else's evening, and that's the only advertising it ever gets.
> There's a new one every day at present, weekly further along, so a subscribe keeps them
> coming. The loud stuff always travels fastest, and it's rarely the useful stuff, is it.
> That's my bit. Back to it.

**L9**
> Before we get to the meat of it. If **this video** has been worth sitting through, a like
> helps somebody else find it who's been asking the same questions you have. Every day at
> the moment, weekly down the line, so subscribe and they'll turn up on their own. There's
> no end of people in this game who'll tell you they've got it all worked out. I'm not one
> of them. Good. Let's pick it up again.

*(The bold on "this video" is markup for review only. The lines go into the pool file and
into each script as plain text.)*

---

## 18. PROMPT 1b — the proposed first build step

**Not started. This is the shape of it, so Jodie can decide when.**

**1b = the words, and nothing that renders.** It is deliberately the cheapest, most
reversible slice: it changes no pixel, spends nothing, touches no episode asset, and can
be reverted with `git revert`.

1. Create `docs/midroll-line-pool.md` — the ten approved lines plus the `ep → line id`
   registry, one file, `broll-registry.md`'s shape.
2. Land the thirteen wording changes in §9 (`PP-STANDARDS.md`, the outro standard, the
   midroll standard, both skills).
3. Change the verbatim guard to the nine-episode window in `render_ready.py` **and**
   `qc_episode.py` **and** `engine/qc_episode.reference.py` — **one commit, all three.**
4. Fix the five stale "Cowork writes it" flags in `providers.py` (347, 391, 545, 855, 884)
   and `PP-STANDARDS.md:4`'s pointer at its own tombstone. Pure string changes, no logic.
5. Test: the EP13-EP24 cycle simulation (EP23 must PASS, an injected duplicate at EP20
   must FAIL), then `engine.py run --mock --watch`.

**Why this order:** it retires the whole midroll ruling and the worst documentation
contradictions before a single template exists, so when the template work starts the
standards it builds against are already correct. **Building templates against stale
standards is how the shot plan went stale on EP11.**

**1c would then be** the card template library + `author_cards.py` + `card_check.py`,
validated by the golden-file test against EP11 and EP12 (§14.1) — the first step that
produces pixels, and the first that needs a careful look rather than a passing test.

---

### The registry that goes with them

`docs/midroll-line-pool.md` carries this table alongside the ten lines, mirroring
`broll-registry.md`:

| Ep | Line | Notes |
|---|---|---|
| EP01-EP12 | — | pre-pool; each was written fresh. Not retro-fitted |
| EP13 | `L3` | first pool episode |
| EP14 | `L4` | |

**⚠️ Every one of the ten carries the DAILY cadence.** When cadence moves to weekly, all
ten go stale at once and need a fresh batch approval. That is the accepted cost of
freezing the wording (§8e).
