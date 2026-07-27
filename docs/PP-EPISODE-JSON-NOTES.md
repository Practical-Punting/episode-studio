# episode.json — build-side notes + proposed spec v2 additions
Claude Code's companion to `PP-EPISODE-JSON-SPEC.md`. Written after building
`assemble_episode.py` and validating it reproduces EP05 v2 exactly (Pass A
byte-identical; Pass B identical bar internal node-label names). — 2026-07-23

## How the assembler consumes the contract
`assemble_episode.py <episode.json> <shot-map.json> A|B` emits the Pass A / Pass B
ffmpeg graphs. It reads the **spec fields verbatim** (Cowork owns these):
`beats[]` (framing drives MCU/WIDE zoom; card/broll are informational), `cards[]`
(beat → cue time; hero → hold; layout → fullscreen vs panel-push), `broll[]`
(order = Pass A input order; beat → placement), `figures[]` (e-book = card renders).

## The `build` block — Claude-Code-side tuning (the "how")
Per WHO-DOES-WHAT, Claude Code owns build details. The spec omits fine-tuning
(deliberately minimal), so the assembler reads an OPTIONAL `build` object that
Claude Code fills. It never changes creative content — only timing/mix polish:
`title_head, warranty_tail, mcu_zoom, push_zoom, logo_margin, outro_mcu_from,
hero_hold, default_hold, holds{id}, leads{id}, broll_trim, broll_dur,
broll_offsets{target}, standing{title,endcard,warranty}, endcard_beat,
endcard_lead, signoff_beat, warranty_lead`. Defaults reproduce the approved
EP05/EP-standard look; Cowork can ignore this block entirely.

## Conventions the assembler uses for spec-omitted things
1. **Standing card roles** (title / end card / warranty) are identified via
   `build.standing` mapping to card ids. (Proposed: add a `role` field to `cards[]`
   in spec v2 so they're self-describing — `"role": "title|endcard|warranty|content"`.)
2. **Clip resolution** (card id → rendered `overlay/clips/*.mp4`) and the ffmpeg
   `-i` input order are handled by the render wrapper, not the graph. Pass A inputs:
   presenter, broll[] in order, logo chip. Pass B inputs: _passA, content cards in
   `cards[]` order (excl. standing), title, endcard, warranty, presenter-audio, music.
   (Proposed: pin a clip-name convention `<episode>-<cardid>.mp4` in spec v2.)
3. **Hold** = `build.holds[id]` if present, else `hero_hold` (hero) / `default_hold`.
4. **Timing** = WhisperX forced-align (`align_srt.py`) → `build_shot_map.py` anchors.
   No SRT is provided by Cowork (spec rule 67 confirmed).

## Proposed spec v2 additions (for alignment — not urgent)
- `cards[].role` (title|endcard|warranty|content) — replaces the id-convention guess.
- A pinned `<episode>-<cardid>.mp4` clip-name convention (or a `clip` field).
- Confirm **panel-push cards are green-screen** (chromakey `0x00FF00`) so the
  assembler keys them (it already emits `chromakey…scale=810…overlay x=36` for
  `layout:"panel-push"`; EP05 was all-fullscreen so this path is implemented but
  not yet render-validated — first real panel card will confirm it).
- Optional: allow the `build` block in the schema (it's additive; Cowork leaves it out).

## Status
- `assemble_episode.py` — built, **validated on EP05 (reproduces v2 exactly)**.
- Fullscreen layout: proven. Panel-push layout: implemented to the EP02 method,
  pending a real panel card to render-validate (no EP05 test case).
- EP05 `episode.json` fixture lives at `PP-EP05/docs/episode.json`.
