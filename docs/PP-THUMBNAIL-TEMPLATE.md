# PP YouTube Thumbnail — CANONICAL TEMPLATE
*The ONE template every episode thumbnail is built from. Defined 25 Jul 2026 after EP08 drifted. Companion to PP-STANDARDS.md.*

## THE BUILD RULE (this prevents drift — read first)
- **Source of truth = the standing template file `assets/youtube-thumbnail-template.html`.** COPY it; never author a fresh thumbnail HTML from a text description.
- Per episode you change **only these four slots:** (1) the hook lines + which word is orange, (2) the byline text, (3) the hero background image, (4) any text-placement note for that hero (so text stays clear of the horses).
- EP08 drifted because a thumbnail HTML was authored from a description instead of copying the template. **Guard shipped (commit f71d7c8):** the engine's `build_thumbnail` step now flags any thumbnail page that doesn't reference `pp-logo-on-dark.png` and pauses for a human rather than rendering an off-template page.

## THE ELEMENTS — left column, top → bottom (ALL REQUIRED, none optional)
1. **Eyebrow** — text **"HOW TO WIN AT HORSE RACING"**, orange `#DA532C`, bold, ALL CAPS, wide letter-spacing, small; top-left.
   - ⚠️ Canonical eyebrow is "HOW TO WIN AT HORSE RACING". Some earlier thumbnails drifted to "PRACTICAL PUNTING" here — do NOT; use the canonical text.
2. **Headline (the hook)** — **Anton**, ALL CAPS, **two lines**, **colour-split**: the setup word(s) **WHITE**, the punchy payoff word(s) **ORANGE `#DA532C`** (usually line 2). ~120/150px per the template. 3–5 words total.
3. **Orange rule** — a short horizontal orange bar (`#DA532C`) directly under the headline.
4. **Byline** — **ONE short descriptive promise line, WHITE, sentence case (NOT caps)**, under the rule. **REQUIRED every episode** (e.g. "How weight really decides races", "What the barrier is really worth"). This is a permanent element — never omit it.
5. **Logo** — the PP logo chip (`pp-logo-on-dark.png`, white wordmark) **bottom-left**, ~210px. Always present.

## THE IMAGE (hero)
Racing-action photo — horses + jockeys in colourful silks, **lush green turf**, dramatic/energetic; composed with room on the LEFT for the dark scrim + text; **NOT** the host's face; turf only (no dirt). PP-owned/licensed or generated.

## COLOUR · TYPE · SPECS
- Colours: orange `#DA532C`, white, dark charcoal scrim/gradient down the left.
- Type: headline + eyebrow in **Anton**; byline in a clean sans, sentence case.
- Caps: eyebrow ALL CAPS · headline ALL CAPS · byline Sentence case.
- **1280×720, PNG, <2MB.** (The duration badge is YouTube's own overlay — not part of our file.)

## EP08 values (apply now)
- Eyebrow: HOW TO WIN AT HORSE RACING
- Hook: **"BET LESS,"** (white) / **"WIN MORE"** (orange)
- Byline: **"How the professionals make punting pay"** (Jodie to confirm/adjust)
- Hero: the EP01 racing shot (same as the cover)
- Logo: standard PP chip, bottom-left
