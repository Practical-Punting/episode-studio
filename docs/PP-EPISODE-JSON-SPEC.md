# PP `episode.json` — the build contract (Claude Code writes it → the engine reads it)
*Single source of truth for the machine-readable spec. v2, 28 July 2026. **Claude Code writes `docs/episode.json` at the create step**; the engine's card authoring, assembler and e-book builder consume it — zero placement interpretation, zero invention.*

> **v2 CHANGED WHO WRITES THIS FILE, AND WHAT IT MUST CARRY.**
> The v1 header said *"Cowork writes it"*. That has been wrong since `WHO-DOES-WHAT.md`
> ruled that Cowork writes **not one line of anything that ships**.
>
> **The substantive change: `cards[]` must now carry `block`, `content{}` and `trace{}`.**
> Before 28 Jul 2026 a card's actual content lived as English prose in `detail`, and the
> engine could not author a card page from it — so an episode with no card pages halted
> and asked a browser operator to write HTML. The engine now authors those pages from
> `content{}`. **If these fields are absent the build still halts** — it has simply moved
> from *"write the pages yourself"* (impossible for Hugh) to *"card C4 is missing the key
> `payoff`"* (a sentence someone can act on). **Populate them at create time.**
> See `DESIGN-self-authoring-build.md` §5-§6.

## Shape
```jsonc
{
  "episode": "EP06",
  "title": "How to Win at Horse Racing: ...",
  "video_id": null,                     // filled after the ⏸ human HeyGen render (Jodie/Cowork)
  "spoken_words_file": "docs/EP06-spoken.txt",   // clean, one paragraph per beat, body + outro; #-comment setup notes only

  "beats": [
    {
      "n": 1,                            // beat number, 1-based, matches the spoken-words paragraph order
      "framing": "WIDE",                 // "MCU" | "WIDE"
      "line": "<exact narration line for this beat, verbatim>",
      "card": "C1",                      // card id on this beat, or null
      "broll": "broll-field-powering-turf"  // b-roll target name on this beat, or null
    }
    // ... one entry per beat, body + outro
  ],

  "cards": [
    {
      "id": "C1",
      "beat": 1,                         // which beat it sits on (explicit — never inferred)
      "page": "ep13-c01-most-of-them-lose.html",   // v2, REQUIRED: the file in overlay/export/
      "eyebrow": "Start Here, and Be Honest",
      "headline": "MOST OF THEM LOSE",   // the packaging-consistency value
      "headline_display": "Most of Them Lose",  // v2: what is SET on the card; may carry <br>
      "detail": "<one-line description of the card's content/animation>",
      "hero": true,                      // hero card (bigger moment) or not
      "layout": "fullscreen",            // FRAME: "fullscreen" | "panel-push"  (MUST be a MIX)
      "block": "stat",                   // v2, REQUIRED: which body template, or "bespoke"
      "job": "anchor",                   // v3, REQUIRED: what the card is FOR —
                                         //   "orient" | "locate" | "relate" | "anchor"
                                         // See the pp-visual-standard skill, which OWNS this
                                         // vocabulary. A card that does none of the four jobs
                                         // is decoration and must not be built (R2: no job,
                                         // no build). `orient` cards introduce the whole
                                         // structure, so their subject is the EPISODE, not one
                                         // sentence — they are exempt from the fit and
                                         // relevance window tests.
      "relates_to": "the day's track bias — four conditions, one outcome",
                                         // v3, REQUIRED when a LIST block (checklist,
                                         // slate) declares job "relate". Names what the
                                         // items connect TO. Many causes pointing at one
                                         // outcome is a relationship; a bare enumeration
                                         // with no subject is assertion wearing a list's
                                         // clothes and must declare "anchor" instead,
                                         // counting against the 40% cap. (R3a, the list
                                         // qualifier — Jodie, 29 Jul 2026.)
      "fit": {                           // v2, optional: MEASUREMENTS ONLY, never text
        "headline_size": "104px"
      },
      "content": {                       // v2, REQUIRED unless block is "bespoke"
        "figure": "60 Days+",
        "figure_sub": "Resuming from a spell",
        "payoff": "Most will lose at their first run back.",
        "note": null                     // EXPLICIT null = an empty slot a human chose
      },
      "trace": {                         // v2, REQUIRED for every figure-bearing key
        "figure": "Most horses resuming from a spell - say 60 days or more - will lose at their first run back."
      }
    }
    // ... every card, incl. standing TITLE / END CARD / WARRANTY
  ],

  "broll": [
    {
      "target": "broll-blanket-finish", // output filename stem in broll/
      "beat": 6,                          // which beat it covers (explicit)
      "line": "<exact narration line it plays under>",
      "flags": ["turf", "crowd-diverse"], // intent flags — see below
      "prompt": "<full Higgsfield prompt, with hats + ethnic-mix + turf wording baked in>"
    },
    {
      "target": "broll-weigh-in",
      "beat": 2,
      "line": "...",
      "flags": ["non-turf"],             // weigh-in/form/odds — tells turf-QC NOT to false-flag it
      "prompt": "..."
    }
    // ... every b-roll clip, no repeats within the episode
  ],

  "cover": {                             // the two e-book cover heroes (A/B) — REQUIRED
    "hero_a_prompt": "<full Higgsfield prompt, portrait 2:3, hats + ethnic-mix + turf baked in>",
    "hero_b_prompt": "<a DELIBERATELY DIFFERENT composition — the real alternative>",
    // v2, REQUIRED — the engine AUTHORS ebook/cover-src/cover.html from these
    "title_setup":  "Hidden",            // the setup word(s) — rendered WHITE
    "title_payoff": "Aces",              // the payoff word(s) — rendered ORANGE
    "part":         "Part 2",            // or null on a non-series episode
    "part_inline":  false,               // the SERIES PART TREATMENT — see below
    "byline":       "Reading the horse coming back from a spell · from the Practical Punting archives · with Gordon"
    // NOTE: the cover's SUBTITLE is not here. It is packaging.byline, verbatim.
  },

  "figures": [
    { "n": 1, "card": "C3" },            // e-book figure N = the print render of card CXX (one design, two uses)
    { "n": 2, "card": "C10" }
    // ... book figures map to cards; Claude Code renders straight from the card HTML (its print variant)
  ],

  "ebook": {                             // v2, REQUIRED — the e-book FIDELITY DECLARATION
    "departures": ["spaced-hyphen-em-dash"],
    "omit_paragraphs": ["FIRST-UPPERS AND THE VALUE FACTOR"]
  }
}
```

## Rules
- **`cover.hero_a_prompt` / `hero_b_prompt` are required** (locked order, 26 Jul 2026). The engine
  generates BOTH heroes upfront in the gens-first batch (~2 credits each) so the cover pick reaches
  the operator while Gordon is still rendering. They must be two genuinely different compositions —
  a real choice, not a near-duplicate. Missing prompts flag the episode before anything is spent.
- **card→beat and broll→beat are EXPLICIT** (in both `beats[]` and `cards[]/broll[]`). The assembler never decides placement.
- **b-roll `flags`:** `turf` (must be grass), `saddled`, `crowd-diverse` (~75/9/9/5 mix, ~50% in hats), and `non-turf` for weigh-in / form / odds-board / studio shots so Claude Code's turf-QC doesn't false-flag them. No clip repeats within an episode.
- **`layout` must be a MIX** — never all `fullscreen`; use `panel-push` on a good share of cards.

### v2 — `block` / `content{}` / `trace{}`, the fields the engine authors cards from

- **`block`** names a body template in
  `.claude/skills/pp-episode-production/assets/cards/blocks/`. Run
  `python author_cards.py` with an unknown one and it lists what exists. Today:
  `stat` `price` `slate` `checklist` `compare` `steps` `bars` `ratio` `statement`
  `slots` `chips`.
- **`block: "bespoke"` means hand-authored.** The engine never generates it and never
  overwrites it. Expect 2-3 an episode — it is what protects the mix Jodie asked for, not
  an escape hatch for a card nobody could be bothered specifying. **Say WHY in `detail`.**
- **Every key the block declares must be PRESENT.** Explicit `null` renders an empty slot
  and records that a human decided it is empty; a **missing** key HALTS, because absence
  records nothing. This is the EP12 `_placeholder` lesson: a placeholder that looks like
  data is worse than no data, because it defeats the check meant to catch it.
- **`trace{}` is required for any `content` value containing a figure**, keyed by the
  content key (or the list name). Its value is the **source sentence, verbatim**. The build
  checks two things: the sentence is a literal substring of the article named in `source`,
  **and** every number in the displayed value actually appears in that sentence. EP11's C7
  passed the first test and failed the second — the sentence was real, it just never stated
  the placings that had been inferred from listing order and put on screen as fact.
- **`fit{}` carries measurements, never text.** Values must be bare numbers with an
  optional `px`/`em`/`%`. It exists for per-card font and spacing nudges; a string in it
  halts.
- **The generator cannot invent.** There is no LLM in it — it copies a value from
  `content{}` into a slot or it fails. Anything you do not write here cannot appear on a
  card. That is the point.
- **A page without the generated marker comment is treated as hand-authored and left
  alone**, so a hand-fix survives every later run.

### v2 — `cover{}`, the fields the engine authors the e-book cover from

The cover is a four-slot substitution into `assets/ebook-cover-template.html`: the
`<title>` tag, `.title`, `.subtitle` and `.byline`. Everything else — the whole flow-band
layout that made EP09's overlap impossible by construction — is copied untouched.

- **`title_setup` / `title_payoff`** split the hook for colour: setup WHITE, payoff ORANGE,
  the same split the in-video title card and the thumbnail use. **They are checked against
  `packaging.hook`** — if `setup + " " + payoff` does not equal the approved hook, the build
  halts. The words were locked at the words gate and the cover does not get to differ from
  them (the EP08 rework lesson).
- **`part`** is `"Part 2"` or `null`. If set, it **must appear in `packaging.ebook_title`**.
- **`part_inline`** records the SERIES PART TREATMENT as a decision rather than inferring it
  from title length: `false` drops the em dash and sets Part N on its own line at about half
  size (a SHORT title — EP11, EP12); `true` keeps `— Part N` inline at full size (a LONG
  title — EP10). The rule is in the template header; **which side of it this episode falls on
  is a human call, so it is stored, not guessed.**
- **`byline`** is the cover's descriptive furniture line. **The SUBTITLE is not a cover
  field** — it is `packaging.byline` verbatim, so the promise line on the cover and the
  approved packaging cannot drift apart.

### v2 — `thumbnail{}`, the fields the engine authors the YouTube thumbnail from

```jsonc
"thumbnail": {
  "l1": "Hidden",              // setup word(s) — WHITE
  "l2": "Aces",                // payoff word(s) — ORANGE (the locked colour split)
  "part": "Part 2",            // or null on a non-series episode
  "strap_break_after": "horse",// which word the strap line breaks after, or null
  "hero_focus": "center 62%"   // CSS object-position — THE per-image placement value
}
```

- **`l1` / `l2` are checked against `packaging.hook`**, exactly as the cover's are. The
  eyebrow is **not** a field — it is LOCKED to *"How to Win at Horse Racing"* in the
  template, so it cannot drift again.
- **The strap is `packaging.byline` verbatim.** Only where it BREAKS is a layout choice, so
  `strap_break_after` names a word in the byline; a word that is not in it halts.
- **`hero_focus` is the one genuinely per-image value.** EP11 sat at `center`; EP12 needed
  `center 62%` because its field sits low in the frame. Everything else EP11 and EP12 tuned
  — scrim stops, copy box, type sizes, bar margins — they agreed on exactly, so those are
  now the template's defaults rather than per-episode settings.
- **PLACEMENT DOES NOT HALT THE BUILD (Jodie, 28 July 2026).** The page is authored at the
  standard placement, rendered, and a **clearable `needs_look` is raised with the PNG**.
  Halting until someone types coordinates would be a halt a browser operator cannot clear —
  a regression against the number this whole exercise drives down. It fires mid-build on
  purpose: an episode cannot go backwards, so a bad crop found at the four approvals is
  expensive and one found here is cheap. *(When "send it back a stage" exists, this flag
  could collapse into the existing thumbnail approval and disappear.)*

**The canvas is NOT an episode.json field.** The template declares it once
(`body{width;height}`), `author_cover.py` writes it into the page as a `pp-canvas` comment,
and the engine renders at exactly that. Before 28 Jul 2026 the page was 1588×2238 and the
render 1600×2263, so every cover shipped with a 12px white gutter down the right edge and
25px along the bottom. EP11 and EP12 shipped that way and are **not** being changed — they
are published. It cannot recur because there is no second number left to disagree.
### v2 — `ebook{}`, the fidelity declaration the e-book is GATED on

The e-book's shell, layout and figures are AUTHORED from the standing template. The
article **BODY is editorial** and lives in **`ebook/body.html`, written at SCRIPT
time** — when the article is in hand and the fidelity work is being done anyway.

**What replaces a human read of that body is a machine check.** `author_ebook.py`
hard-fails unless every plain `<p>` in the body is a **character-for-character**
reproduction of a paragraph of the article named in `source`, in order, after the
departures declared here are applied. It does not fold case, quotes, dashes or
punctuation, because every one of those is a thing §0a says must survive.

- **`departures[]`** — names from a **FIXED VOCABULARY**, not free text, so
  `episode.json` cannot describe an arbitrary transform. Today the vocabulary has
  exactly one member: **`spaced-hyphen-em-dash`** (the article's spaced hyphens
  ` - ` are set as em dashes for print — EP12's one disclosed departure). Adding a
  name is a code change, which means a diff and a reviewer. **There is no
  "normalise" departure and there must never be one.** Write `[]` if the body
  reproduces the article exactly; a MISSING key halts, and a departure that
  changes nothing in this article also halts, so the list cannot become
  boilerplate that gets copied forward and stops meaning anything.
- **`omit_paragraphs[]`** — every article paragraph the body does not reproduce,
  **quoted verbatim** from the article. You do not get to drop a paragraph without
  writing down which one. Most episodes need exactly one entry: the article's own
  headline line, which is set as the `h1.section` heading rather than as body prose.
- **Why a machine and not a person (Jodie, 28 Jul 2026):** the rejected option
  asked a human to eyeball twenty paragraphs for byte-level faithfulness — what
  humans are worst at and machines are best at. **EP11's `firstup` was normalised
  to `first-up`, disclosed, and got PAST human review.** And the human check does
  not disappear: the e-book is already one of the four approvals, so a mid-build
  read would be a second gate on the same document, which breaks *"a gate is only
  worth having if the thing behind it is worth stopping an episode for"*.
- **If `ebook/body.html` is missing the build HALTS naming the file** — the same
  data-halt shape as everywhere else. No body file means no fidelity check, which
  means no gate.

- **Figures reuse cards** — Cowork does NOT author separate illustration art; it maps `figure.n → card.id`.
  **The body must show exactly the figures `figures[]` maps, no more and no fewer** —
  checked both ways, so the book can neither print a broken image nor quietly drop
  a figure the engine rendered.
- **Timing:** Claude Code generates its own (WhisperX forced-align on the master) — no SRT is provided or expected.
- **Spoken-words file:** one paragraph per beat, body + standing outro, numbers as words; any setup note is a `#`-comment line (never a bare `[SETUP NOTE …]` block).

## packaging (REQUIRED from EP09 — PP-STANDARDS 25 Jul 2026)
`packaging {hook, byline, youtube_title, ebook_title}` — the LOCKED words for each
slot (they are deliberately different slots, not one title). QC hard-fails any asset
source carrying a stale value. Lock via the Words Gate before any visual is built.
