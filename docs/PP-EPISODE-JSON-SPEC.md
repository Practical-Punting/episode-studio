# PP `episode.json` — the agreed hand-off contract (Cowork writes it → Claude Code reads it)
*Single source of truth for the machine-readable spec. Both sides build to THIS. v1, 2026-07-22 (agreed from Claude Code's BUILD-TO-COWORK-FEEDBACK point 1 + Cowork's pipeline plugin). Cowork writes `docs/episode.json` per episode; Claude Code's assembler + e-book builder consume it — zero placement interpretation.*

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
      "eyebrow": "PRACTICAL PUNTING",
      "headline": "A MATTER OF WEIGHT",
      "detail": "<one-line description of the card's content/animation>",
      "hero": true,                      // hero card (bigger moment) or not
      "layout": "fullscreen"             // "fullscreen" | "panel-push"  (MUST be a MIX across the episode)
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
    "hero_b_prompt": "<a DELIBERATELY DIFFERENT composition — the real alternative>"
  },

  "figures": [
    { "n": 1, "card": "C3" },            // e-book figure N = the print render of card CXX (one design, two uses)
    { "n": 2, "card": "C10" }
    // ... book figures map to cards; Claude Code renders straight from the card HTML (its print variant)
  ]
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
- **Figures reuse cards** — Cowork does NOT author separate illustration art; it maps `figure.n → card.id`.
- **Timing:** Claude Code generates its own (WhisperX forced-align on the master) — no SRT is provided or expected.
- **Spoken-words file:** one paragraph per beat, body + standing outro, numbers as words; any setup note is a `#`-comment line (never a bare `[SETUP NOTE …]` block).

## packaging (REQUIRED from EP09 — PP-STANDARDS 25 Jul 2026)
`packaging {hook, byline, youtube_title, ebook_title}` — the LOCKED words for each
slot (they are deliberately different slots, not one title). QC hard-fails any asset
source carrying a stale value. Lock via the Words Gate before any visual is built.
