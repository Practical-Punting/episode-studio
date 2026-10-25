---
name: pp-promo-video
description: "Build a Practical Punting PROMOTIONAL / SALES video presented by Gordon — any product promo (PPD Club, FBX, Saturday Punter, a weekly results video, a free-guide promo, an EDM video). Use whenever the job is a promo, a sales video, a product video, a 'what is X' video or a results video, NOT a PP-EPnn episode. Holds the runbook, the questions to ask Jodie BEFORE building, every standing ruling, and the traps that cost re-renders."
---

# Practical Punting promo videos — the runbook

**Built from two real builds:** FBX (11 Oct 2026, `scripts/fbx/`) and the PPD Club promo "Bet Small, Win Big"
(25 Oct 2026, `scripts/ppd/` — approved after one change, the title page). **The PPD build is the worked example:
copy its shape.** Read `scripts/ppd/README.md` before writing a line.

A promo is NOT an episode: no rail row, no engine run, no e-book. Record it in `PP-ATLAS.md` (append mode, verified).
Media in `G:\My Drive\PP Videos\Promotional Videos\PP-<PRODUCT>-<NAME>\`; code in the repo, never on the Drive.

## 0. Before anything
1. Checkpoint (dated!) + Jodie's context set. Then `render_lock.py status`.
2. Start the HeyGen poller at once (`fbx_fetch.py <job> --name "<exact title>"` — by NAME, refuses 0 or 2 matches,
   byte-checked). If HeyGen says "processing", record the id, poll in the background, and read the brief meanwhile.
3. **Precedence when sources disagree:** Jodie's rulings (this skill, Atlas) > Hugh's brief (FACTS, must/must-not,
   brand) > the shot script > on-screen notes in the script. Say which you followed and why.

## 1. Ask Jodie BEFORE building — one question at a time, only what the brief does not already answer
These are the decisions that cost a rebuild when they were guessed (PPD's title page was rebuilt after her watch):
- **Title page / thumbnail** (they are ONE design; the thumbnail is the page at 1280x720, the title card the same
  page at 1.5x with small print). Her PPD answers are the default to OFFER, not to assume: timeless (no event name,
  no date) · the product logo BIG and CENTRAL · ONE hero figure much bigger than everything else (+326% PROFIT) ·
  the supporting figure small underneath · **no Gordon** · the hypothetical small print on the TITLE CARD ONLY.
- Is there b-roll, and roughly where? (Library first; Higgsfield only via `engine/hf_guard.py`, within the stated cap.)
- Any sound effects? (Default NO — the PP audio standard has none.)
- "18+" on the responsible-gambling slide if the brief asks for it — the STANDING slide is never edited by a build.
- Profit vs return wording: "+326% PROFIT" (the brief's word). "326% return" reads as 3.26x back.

## 2. Standing rulings (do not re-ask)
- **Opens on the title card** ("like the normal videos", Jodie, FBX 11 Oct): 7.0 s head, the standard PP sting, ONE
  clock — the head is added once in the cue sheet and every reader (cards, plan, assembly, QC, SRT) uses it.
- **Ending:** "Remember, never bet more than you can afford to lose." → the product closing card (builds ~1.3 s,
  holds 3 s) → the STANDARD PP warranty slide (6.7 s, unedited) → 0.5 s fade.
- **Product brand on every card**; PP only as endorser ("Brought to you by" + PP logo) and the logo chip on Gordon's
  shots. **No PP orange #DA532C** outside the PP logo.
- **Every results number carries the brief's hypothetical small print while it is on screen**, word for word —
  including the title card (PPD's first title card missed it).
- Bets in full ("Flemington Race 8 no.5 Cosmic Crusader"); dividends paid, never a listed price; misses fade to
  grey, no cross; never: tote, SP, bookmaker names/odds screens, "bet now", "guaranteed", "free trial" (it is a
  RISK-FREE trial), urgency, David Stanley. Price on screen only, in its own swappable card.
- **Proof data is lifted, never re-typed:** one data file per proof day, every total recomputed from the rows, the
  build HALTS on a disagreement, and a test proves each kind of tampering halts (`ppd_data.prove`, `test_ppd_data.py`).
- **Cues are measured:** phrases found IN ORDER (each after the previous) on `fbx_align.py`'s words — never the old
  transcript aligner (it mistimed W01's prices while reporting itself fine).
- **Two exports + SRT:** master 16:9, a captioned copy (short ≤ 60-character captions timed from the words; Roboto
  Bold on a dark rounded strip), the SRT (whole sentences, finished clock). Clips handed to Jodie are yuv420p.
- **Never automate a gate:** no new HeyGen render without asking (say the cost); no upload, publish, or send to Hugh.

## 3. Geometry measured on Gordon (Luke avatar, racecourse set) — design to these, QC still measures
| framing | Gordon's nearest jacket edge | so a left panel may reach |
|---|---|---|
| PUSH 136% (panel shots) | x ≈ 797-804 | x ≤ 748 (57 px clear) |
| WIDE 100% (lower thirds) | x ≈ 576 | x ≤ 564 (lower third 516 wide at x 48) |
- PP logo chip: 428x140 at bottom-right (40 px margin) → its top is **y 900**. Captions on Gordon's shots sit above it.
- **Full cards:** content in y ≤ 860; **y 860-990 is the caption band**; small print (2 lines max) and the endorser
  at the bottom; the product wordmark top right. A push FINISHES before its panel appears (start it ~0.6 s early).

## 4. Building the cards — the traps (each cost a re-render; the card lint now stops all of them)
Cards are HTML pages driven by `pp-anim.js` (seek, never play). Moves and pacing: the `pp-motion-graphics` skill
(Enter 260, Count 900-1200, Slam 1.18→1 in 340, data rows 240-320 ms apart, a 700-900 ms beat before a payoff,
hold ≥ 1.5 s). Then:
- **One property, one animation.** Animations fill BACKWARDS: a second animation on the same property wins from t=0.
  Use `seq()` (one animation through several moments) or two elements (outer travels, inner slams).
- **Never put opacity on a `preserve-3d` element** — it flattens the 3D (the book showed its last page). Fade a wrapper.
- **Raleway needs `lining-nums`** (its default figures drop below the line); counting numbers also `tabular-nums`.
- **A red edge straight against footage/grass smears orange** in 4:2:0 video: inset red bars inside charcoal.
- Never set Gordon's sentence on screen (a published quote the brief asks for is the exception — say so).
- **`scripts/promo/card_lint.py` runs automatically before every render** in `ppd_promo.py cards` and halts on: R1
  fighting animations · R2 opacity on preserve-3d · R3 Raleway digits without lining figures · R4 anything in the
  caption band on a full card · R5 small print over two lines · R6 text off the frame. Its controls:
  `scripts/promo/test_card_lint.py [cards_dir]` (each rule must be caught; real cards must be clean).

## 5. Look before you check
After rendering, LOOK at every card's `.last.png` (a 2-per-row sheet) AND at mid-motion frames in the finished file
(the book's flip, chips travelling, a fade). Ask: would this sit in a broadcast graphics package? The QC measures;
only looking finds the 3D book showing the wrong page.

## 6. QC — `ppd_qc.py` is the template (FBX: `fbx_promo_qc.py`)
Every check reads the FINISHED file against a source the build did not write: numbers vs the brief (parsed), small
print seen in the frames, 50+ elements timed at their real positions (±0.3 s), clearance on Gordon's jacket pixels,
the orange scan (exempt ONLY the PP logo's measured box; a cell counts when its orange pixels' median hue ≥ 11.5°;
controls pushed through the master's own x264 encode), b-roll md5 + placement, flutter, loudness (−14 ±1, TP ≤ −1),
structure + ending, SRT clock, captions clear of panels / small print / the chip, hard-nos in screen text + SRT +
script, the motion checklist per card, a seek test on counting numbers. It takes ~8 minutes — run it in the
background and do the Atlas entry meanwhile. A QC line that says MISMATCH must be pass/fail, never informational.

## 7. B-roll
Library first. Watch every candidate end to end (8 frames + 4 at full size) for: turf; every runner on ONE side of
the running rail (no runners both sides of two rails — EP37 "one horse clear" is banned); no rail across the horses;
no cut mid-clip; hats in a range of natural colours; no bookmaker signage. Record source, md5, why, and every
rejection in `broll\broll-sources.json`. Verdicts so far (do not re-watch):
- USED: EP37 crowd-at-the-rail-reacting (PPD) · EP25 five runners strung out, EP20 team round printouts, EP10 punter
  with form guide, EP30 favourite clear at the furlong (FBX).
- REJECTED: EP37 one-horse-clear-from-behind (rails) · EP47 big Saturday field from the stand (same-cream hats; rail
  over hooves) · EP26 field sweeping to the line (two rails down the middle) · EP42 field fanned wide (runner wrong
  side) · EP38 bunched at the turn (rail in front) · EP31 full lawn, EP15 cup-day grandstand, EP24 glamour crowd (each
  cuts mid-clip) · EP33 fight-for-third, EP40 strung-at-the-line (rail across/in front).

## 7b. The YouTube words — part of EVERY promo build (the PPD build forgot them until Jodie asked)
Write them as soon as the cut is approved (or alongside it), following `docs/youtube-metadata-kit.md`:
- `output\<NAME>-youtube.txt` in the HOUSE LAYOUT (`docs/youtube-copy-form.json` banners): ONE decided title
  ("<specific part> | How to Win at Horse Racing", ~50-70 chars, timeless, saying something DIFFERENT from the
  thumbnail); the description (first sentence carries "horse racing" + the search term without a promise; the
  product's links; chapters at 0:00 + the section starts from the cue sheet; the brief's small print, "Practical
  Punting is not a bookmaker." and the Gamble Responsibly line; no dividends or prices; exactly five hashtags at the
  end); the NOTES with the source of every figure.
- `output\<NAME>-youtube-tags.txt`: comma-separated, ≤ 500 characters as YouTube counts them (+2 per tag with a
  space), nothing from the kit's never-use list. Tags are unseen, so an event name may go there.
- Check both mechanically (layout, lengths, required lines word for word, banned words) and read them back from
  the Drive. PPD's approved set is the worked example (`PP-PPD-PROMO\output\`).

## 8. Report to Jodie
Facts only: where the files are, QC in three lines, every judgement call as a list, anything broken said straight
away. No verdict of your own. Then ONE question: "What do you think?" — her own words first, the checklist after.
Record each verdict on one line and every change as its own item (OPEN / DONE / DROPPED). Update Atlas and the
checkpoint, and tell her where.

## Planned (not built yet — Jodie, 25 Oct): a shared promo toolkit in `scripts/promo/` (brand file + common blocks:
title page, lower thirds, results rows with tick stamps, tiles, closing card, CTA, captions, QC) so a new product is a
brand file + data + its own cards; and a full b-roll library index with recorded verdicts.
