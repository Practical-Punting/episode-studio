# Thumbnail standard (Practical Punting YouTube)
*Proven on EP02 + EP03, 2026-07-21. A thumbnail is a FINISHED artefact Jodie approves — build it fully, then show her once.*

> **This SUPERSEDES the older thumbnail guidance** in the `pp-episode-pipeline` skill that said to pull an expressive frame of Gordon and use Higgsfield only for backgrounds. The adopted, Jodie-directed method is the HYBRID below (Higgsfield hero + code-composited title). No Gordon frame was used for EP02/EP03. Also note: EP01 and EP02 had **no thumbnail at all** until this session — every episode needs one.

## The method: HYBRID (picture from Higgsfield, text from code)
AI image tools make gorgeous photos but **mangle text**, so we split the job:
1. **Higgsfield makes the photoreal hero** (the racing photo).
2. **Claude Code composites the title text** over it with pixel-perfect brand type.
This is the same "AI for pictures, code for words" rule we use for e-book graphics.

## Step 1 — Hero image (Cowork, via Higgsfield)
- Model `nano_banana_pro`, **aspect_ratio "16:9"**, generate **4 candidates** (expect 1–2 to fail — that's normal; pick from the rest).
- **Prompt shape:** cinematic, premium, dramatic horse-racing scene on **lush green turf** (TURF rule — never dirt), dramatic light, shallow depth of field, ultra-sharp subject. ALWAYS include: *"Deliberately leave clean darker negative space across the upper-left for a bold title to be added later. Absolutely NO text, NO letters, NO numbers, NO watermark anywhere in the image."*
- **Pick the most dramatic candidate that has a clear title zone** (a darker/open area, ideally upper-left) and the subject weighted to the right/lower-right.
- **Distinct composition per episode** — do not reuse the same shot or the same framing twice. EP02 used a tight three-abreast finish; EP03 used a single hero horse; keep varying (head-on field, lone leader, turn, etc.).
- Save strong unused candidates to the **hero library** `PP Videos/assets/thumbnail-heroes/` with descriptive names, for future episodes.

## Step 2 — Composite (Claude Code)
Hand Claude Code the chosen hero's URL + the text spec. It downloads the hero and builds a per-episode `epNN-thumbnail.html` from the standing thumbnail template, then renders to PNG. Locked layout (from EP02/EP03):
- **Full-bleed hero** (object-fit: cover).
- **Dark gradient scrim** over the title side (upper-left) so text stays legible over bright sky; fade it to clear across the subject so there are no visible band edges and the horses stay bright.
- **Kicker:** `PRACTICAL PUNTING` in burnt orange `#DA532C`, small, top-left.
- **Headline:** huge **white Anton** — very large (≈150px on the key word so it reads on a phone). Two short lines is fine.
- **Accent bar:** a burnt-orange `#DA532C` bar directly beneath the headline.
- **Strapline:** one line, white, bold Barlow.
- **Logo:** the PP horse-chip + wordmark, small, in a bottom corner (on a gentle scrim). **Use the WHITE-wordmark logo (`ebook-logo-white.png`) on dark art** — the charcoal logo disappears on dark racing photos.
- Keep ALL text clear of the horses/subject.
- **Output:** `PP-EPxx/output/PP-EPxx-thumbnail.png` at exactly **1280×720**, **under 2MB**.
- **Legibility check:** the headline must read at small size (test the key word at roughly 210 / 168 / 120px scales) — it's viewed on a phone first.

## Text rules
- **Thumbnail text ≠ video title.** They should complement, not repeat. (EP02 title = "How to Win at Horse Racing: Killer Trifecta Strategies"; EP02 thumbnail = "WIN THE TRIFECTA".)
- **Punchy hook, 2–4 big words.** Distinct per episode so a viewer scanning the channel can tell them apart.
- Examples: EP02 "WIN THE TRIFECTA" / strapline "Killer strategies the pros actually use". EP03 "10 KEY FACTORS" / strapline "What the pros look for in every race".

## Compliance
Thumbnails sell **strategy and curiosity only** — never guarantees, specific odds/returns, or gambling inducements ("win $X", "guaranteed"). Keep it in the same steady, no-hype brand voice as everything else.

## Handoff (who does what)
**Cowork** generates + picks the hero and writes the text spec; **Claude Code** composites + renders the PNG. Cowork QC's the finished PNG and presents ONE finished thumbnail to Jodie for approval.

## Gotchas
- Higgsfield CDN is firewalled from Cowork's cloud container — **Claude Code downloads the hero URL** (it has normal internet).
- Some Higgsfield generations fail; always request 4 and pick from what lands.
- View the hero before compositing and place the title where it reads cleanest — negative space can land anywhere depending on the shot.
