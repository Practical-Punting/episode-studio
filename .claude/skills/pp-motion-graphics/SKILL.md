---
name: pp-motion-graphics
description: "Design, build or review motion graphics cards for Practical Punting episodes — animated overlays, payoff figures, data graphics, title and end cards. Use whenever a card is authored, animated, restyled or QC'd, or when judging whether a graphic is good enough."
---

> **MIRROR — copied from Cowork's `pp-motion-graphics` skill on 15 Sep 2026 by Cowork, at Jodie's
> request, after Claude Code reported it could not find the skill on this machine.** The Cowork
> copy is the one Jodie edits through claude.ai; this file exists so Claude Code can read the same
> rules. A value with two homes drifts, so: **if the two ever disagree, the Cowork copy wins, and
> this file gets re-copied — never edited here.** Ask Jodie to say "refresh the motion-graphics
> skill in the repo" and Cowork will re-copy it.

# Practical Punting — motion graphics

The card library is the second presenter. Gordon carries the voice; the cards are supposed to carry everything the voice can't. Right now they don't, and this skill exists to fix that with rules that can be checked rather than argued about.

This is the motion-graphics specialist. For locked production facts — brand colours, the logo rule, the warranty slide, who builds what — defer to `pp-episode-pipeline` and the repo's `PP-STANDARDS.md`. Nothing here restates them.

## THE ONE TEST

**Could a viewer get the point of this card with the sound off?**

If the card only makes sense because Gordon is speaking over it, it is a subtitle in a box. Rebuild it or cut it. Every rule below is downstream of this one test.

## The nine rules

1. **Never set his words on screen.** No card carries a sentence Gordon is saying. Mayer's redundancy principle: on-screen text duplicating narration measurably *hurts* comprehension. This is the single most common fault in the existing library.
2. **Build, don't reveal.** The card assembles in step with the voice rather than appearing whole and sitting. Material drawn while the viewer watches held people 1.5–2× longer than finished slides.
3. **Pace data to reading speed.** A row the viewer must *read* needs time to be read before the next one lands. This is the most common way a good block still fails — the accumulation is visible but nothing is legible. See the pacing section; it is the rule most likely to be got wrong.
4. **Name the gap before you close it.** Question → beat of stillness → answer. Curiosity comes from a *specific, bounded, named* absence; the more precisely it's named, the harder it pulls. The silence before the payoff is the mechanism, not dead air.
5. **One relationship per card, not one fact.** "55 per cent" is a fact. "More than the other two put together" is a relationship — and a relationship can be drawn.
6. **Every graphic carries non-verbal information.** If it's there to be lively, it's a seductive detail. 68 studies say interesting-but-irrelevant material costs more than it earns.
7. **Alternate, don't default.** Gordon's face earns its place by trading off against material (46% vs 33% engagement). Long unbroken stretches of presenter are the weakest thing on screen.
8. **Don't slow *him* down for the graphics.** Faster delivery correlated with up to double the engagement. The graphics take their time from the card's own hold, not from the presenter's pace.
9. **Prefer fewer, better cards.** Eighteen per episode, roughly one per paragraph, is a quota not an edit. Put a card where a picture adds something, and nowhere else.

## Pacing — read this before setting any stagger

There are two kinds of element on a card and they do not share a speed.

**Structural elements** — the orange rule, the eyebrow, a headline, a container appearing. These carry nothing the viewer has to decode. They should be quick and get out of the way.

**Data elements** — a ledger row, a labelled bar segment, a band on a ruler, a figure. The viewer has to *read* these. If the next lands before this one has been read, the card shows accumulation without ever being legible. It feels impressive and teaches nothing.

| | Stagger between items |
|---|---|
| Structural elements | 90–140ms |
| **Data rows the viewer reads** | **240–320ms**, or the time to read the label, whichever is longer |

**Jodie's ruling, 15 Sep 2026, on the first ledger build: *"It could probably be a bit slower in the way it presented the data."*** That build used 120ms between rows — right for structure, too fast for anything carrying a word and a number.

This is **not** a return to the old library's 300ms. That was 300ms between seven *identical fades that taught nothing* — 3.57 seconds of nothing happening. The distinction is what the item carries, not the number on the clock. An element with nothing to read should be fast; an element with something to read gets the time to be read.

**Two guards on the other side**, so it doesn't drift back:

- **A card should finish assembling inside about 2.5 seconds.** Seven rows at 280ms is 1.96s — comfortable. If a card needs longer than 2.5s, it has too much on it; go back to rule 5.
- **Hold the finished state at least 1.5 seconds** before the card leaves. The assembled card is what the viewer takes away; a card that completes and immediately cuts has wasted its own build.

## The motion vocabulary

Six moves. Easings as CSS cubic-beziers for the Web Animations engine.

| Move | What it teaches | Duration | Easing |
|---|---|---|---|
| **Enter** | Arrival | 260ms | `cubic-bezier(0.2,0,0,1)` |
| **Count** | Magnitude — a figure climbing to its value | 900–1200ms | `cubic-bezier(0.05,0.7,0.1,1)` |
| **Fill** | Proportion — a bar growing to width | 600–800ms | `cubic-bezier(0.05,0.7,0.1,1)` |
| **Slam** | Payoff — scale from 1.18 to 1, hard stop | 340ms | `cubic-bezier(0.2,0,0,1)` |
| **Travel** | Position on a scale — a marker sliding | 520–700ms | `cubic-bezier(0.05,0.7,0.1,1)` |
| **Draw** | Connection or route — a line drawing itself | 800ms | `cubic-bezier(0.2,0,0,1)` |

**Anticipation before every payoff.** A beat of stillness — 700–900ms — then the figure lands. Without the pause there is no payoff, only an arrival.

**A running total ticks, it does not slide.** Where a figure is the sum of rows on screen, it steps to each cumulative value as its row lands. A smooth slide puts numbers on screen that are not the sum of the rows beside them — on a PP card, a figure that looks like the article's and isn't.

## The block library

Build each once; they recur across the whole form-and-ratings series.

| Block | What it is | Reuse | Status |
|---|---|---|---|
| **Points ledger** | Factors land one at a time, a total climbs | Highest | **Built 15 Sep 2026** |
| **Proportion bar** | One bar splitting into weighted segments | High | to build |
| **Banded ruler** | A quantity falling into bands, with a marker | High | to build |
| **Gap card** | Question, beat, answer | High | to build |
| **Weight scale** | Kilos and penalties shown as load, not digits | Medium | to build |
| **Form-line strip** | The figures a punter reads — 3‑1‑2 — with one run lit | Medium | to build |
| **Track plan** | Barrier draws and run positions on a plan view | Medium | to build |

When a card's content doesn't fit any block, that is usually a sign the content is a sentence rather than a relationship. Go back to rule 5 before inventing a block.

## Do not

- Do not put a sentence Gordon speaks onto a card.
- Do not use one animation move for everything. The library had exactly one — fade-and-slide 40px, 620ms, on every element of every card — and that is what this skill replaces.
- Do not animate decoration. Motion is for meaning.
- Do not land data faster than it can be read. See pacing.
- Do not give a long duration to an element that is merely arriving. 700ms and over belongs to a value the viewer is watching *change*, not to an entrance.
- Do not attempt text-bearing graphics in Higgsfield or any AI video generator. Generated video cannot render text, exact brand colour, or identical repeats.

## 🔴 The seek-versus-play trap — read before adding any Count, Fill or Travel

`render_card.py` does **not** play a card. It calls `ppSeek(t)` and screenshots, t by t. Anything driven by `requestAnimationFrame`, `setTimeout` or `Date.now()` previews perfectly in a browser and **renders wrong**, because seeking does not advance a wall clock. The preview is what lies.

**A value on screen must be a function of the timeline, never of a clock.** Drivers read their position from a real WAAPI animation's own `currentTime`. This is solved in `pp-anim.js` — read the note at the top of that file before extending it.

**Acceptance test for any new numeric move:** seek to at least eight points across the animation, including one millisecond either side of each tick, and confirm the value on the *rendered pixels* matches what the timeline says. A counter that is right when played and wrong when sought is exactly what this test exists to catch.

## 🔴 A clip for a human is encoded for playback, not for pipelining

Card clips render as H.264 **High 4:4:4 Predictive / yuv444p** — correct for an intermediate, since there's no chroma subsampling before compositing. **Windows Media Player cannot open it** (`0x80004005`, "unsupported encoding settings").

Any clip handed to Jodie must be converted first:

```
ffmpeg -i in.mp4 -vf format=yuv420p -c:v libx264 -profile:v high -crf 17 -movflags +faststart out.mp4
```

Leave the 4:4:4 original in place; the build may reference it.

## Why these rules — so nobody re-argues them

- **Guo, Kim & Rubin (MIT/edX, 6.9m watching sessions).** Median engagement ~6 minutes regardless of length; past 9 minutes viewers typically stop before halfway. Drawn-in-progress material held viewers 1.5–2× longer than finished slides. Instructor alternating with material 46% vs 33%. Faster speech up to 2× engagement. Their own recommendation: *"introduce motion and continuous visual flow."*
- **Mayer, principles of multimedia learning (200+ experimental comparisons).** Redundancy, multimedia, signalling, coherence, temporal contiguity, image principle.
- **Loewenstein, *The Psychology of Curiosity*.** Curiosity is a precisely named gap, not general mystery.
- **"Keep it Coherent" meta-analysis, 68 studies.** Seductive details hinder learning — but static images were found *more* harmful than animated content.
- **Heer & Robertson (Stanford).** Animated transitions improve graphical perception when **staged** into sequential steps rather than morphed at once.
- **Nielsen Norman Group.** Functional animation stays subtle, unobtrusive and brief.
- **Material Design 3 / Disney's twelve principles.** Duration bands, easing curves, anticipation and staging.

Full write-up with live before/after demos: the *Cards That Teach* artifact.

## How cards are actually built

Cards are 1920×1080 HTML pages, one file per card, generated by `author_cards.py` from `episode.json` into `PP-EPxx/overlay/export/`, then rendered to individual clips in `overlay/clips/` and composited per-card at assembly. The animation engine is `pp-anim.js` — Web Animations API, exposing `ppInit(spec)`, `ppSeek(ms)`, `ppPlay()`, plus seekable numeric drivers added 15 Sep 2026.

A running total is **computed from its own rows** via the `cumulative` schema key, never hand-typed — the same rule, for the same reason, as bar widths in `bars`.

Claude Code owns the build. This side makes the creative and brand decisions. Do not cross that line — see `pp-episode-pipeline`.

## Known bug to check

In the four-or-more-item ladder layout, both `.n` and `.k` are populated with the item index and both become visible once the ladder engages, so rows may render the number twice — "1  1  DATE OF LAST START". Inferred from the CSS and generated markup, not from a rendered frame. Still unchecked — the ledger block was built alongside it rather than replacing it.

## Review checklist

Run this on every card before it ships:

- [ ] Sound-off test passed — the card means something on its own.
- [ ] No sentence on screen that Gordon speaks.
- [ ] The card builds in step with the voice rather than appearing whole.
- [ ] **Data rows land no faster than 240ms apart, and slower if the label needs reading.**
- [ ] Structural elements are quick — 90–140ms — and don't steal time from the data.
- [ ] The card finishes assembling inside ~2.5s, then holds at least 1.5s.
- [ ] Any payoff figure has a beat of stillness before it and slams rather than fades.
- [ ] Any running total ticks to real cumulative values, never slides.
- [ ] Numeric moves pass the seek test on rendered pixels, not just in a browser.
- [ ] The card carries information the words don't.
- [ ] Legible at phone size — check body type as a percentage of frame height, not in pixels.
- [ ] Any clip going to Jodie is converted to yuv420p first.
- [ ] Episode-level: presenter and material alternate; no long unbroken stretch of Gordon alone.

## Still open

- **The one-tick lag.** On the first ledger build there was a ~200ms window where all rows were on screen and the total still read the previous sum. It may read as cause-and-effect and be right; it may read as a card that can't add up. Not yet ruled on.
- **Mobile legibility has never been measured.** The ledger's row label is 4.26% of frame height; the old library's body text was ~3.3%. Set a real minimum and check every block against it.
- **The cards are silent.** No tick as an item lands, no thud on a payoff. Audio-visual sync is a genuine attention mechanism and is entirely absent.
- **There is one accent colour.** Data graphics need categorical, sequential and semantic colour — see the `dataviz` skill.
- **Nothing is measured against real viewers.** YouTube's audience retention graph plus the per-episode card cue list would show which cards hold people and which lose them. Until that runs, every rule here is borrowed evidence rather than PP's own.