---
name: pp-episode-script
description: >
  Write a Practical Punting (PP) YouTube episode from a PP article — both the shot
  script and the HeyGen spoken-words track — in Gordon's voice, to the PP standard.
  Use this whenever turning a Practical Punting article into an episode script, or
  writing the midroll invitation, the standing outro, the packaging (title/byline/hook),
  the motion-card specs, or the b-roll prompts for an episode.
---

# PP Episode Script — the "create brain" skill

*v1.2 — fidelity tightening (near-verbatim), 25 Jul 2026.*
*(Retains the v1.1 EP09 calibration in full: thresholds tuned so the checklist passes our
approved best work cleanly and only flags real gaps.)*

This is the skill that turns a **Practical Punting article we already own** into a finished
episode **script package**. It is written so Claude Code (or any Claude) can do the creative
writing step end-to-end, to the same standard, every time — no drift, no AI-slop, no guesswork.

It pairs with the **`pp-episode-production`** build skill: this skill decides *what is said and
shown*; that skill *builds* it (render, ffmpeg, e-book, thumbnail). The canonical rules live in
`docs/PP-STANDARDS.md`; this skill is the *craft* of writing to them. If they ever disagree,
`PP-STANDARDS.md` wins and should be updated.

---

## 0. THE ONE GOLDEN RULE
**The article is the star. LIFT it across the line — do NOT rewrite it.** *(v1.2 — tightened after EP10 drifted into paraphrase.)*
Fidelity of **words**, not just facts. The article is **pre-approved content Hugh has signed off and PP owns** — so we publish *its* words, lightly tidied for the ear, **not a fresh paraphrase in our own words**. Keep the author's actual sentences and phrasing wherever they'll play aloud; reword only where the original genuinely won't lift to the spoken ear — and then as little as possible. (A heavy rewrite is effectively *new, unapproved* content and can quietly drift in meaning. Don't.)
The **ONLY original prose in the whole script** is: the **opening framing line**, short **transitions between beats**, the **midroll invitation**, and the **outro wind-down**. Everything else is the article's own sentences. Craft (hooks, loops, rhythm, signposting) is applied to how you **present and sequence** the article — **never** by re-writing its sentences, inventing facts, or reordering the argument. When craft pulls against fidelity, **fidelity wins.**

---

## 1. WHAT YOU PRODUCE (the outputs)

For each episode you deliver:

1. **The packaging block** — locked FIRST, at the Words Gate (see §3, Step 2).
2. **The shot script** — the beats (B1…Bn) with shot type (MCU/WIDE), `[GFX]` card cues, and
   `[B-ROLL]` cues.
3. **The HeyGen spoken-words `.txt`** — clean narration, one paragraph per beat (body + midroll +
   outro), **numbers as words**. The ~6–7s silent head and ~3s tail are *requested in the
   render/build* — the `.txt` itself carries no silence.
4. **The card specs** (C01…Cn) — one idea per card, payoff figure is the hero (see §4G).
5. **The b-roll prompts** — enough cuts that no talking-head stretch runs uncovered past ~40s (see §4H).
6. **The numbers list** — every figure, for the human tick before cards lock (see §3, Step 8).

These flow into `episode.json` (each beat carries shot type + card ref + b-roll ref + the
packaging block verbatim).

---

## 2. WHO IS TALKING — the two people to hold in your head

### Gordon (the host) — voice bible
A warm, plain-spoken, wry **Australian** racing veteran. A knowledgeable mate at the track — **not**
a lecturer, **not** a hype-man. Quietly confident; he has opinions and states them. He is generous:
he anticipates your doubt and answers it. He is an **AI avatar**, so the *writing* must carry all
the humanity — the visuals give no help.

- **Pronouns:** "I" (Gordon has views) and "you" (one listener). Never corporate "we".
- **Formality:** every line must pass *"would a sharp, friendly racing veteran actually say this out
  loud?"*
- **Signature habits** (use, but reword so they never feel canned): a cold, specific open; a plain
  transition ("Right — where were we."); the standing sign-off ("…I'll see you soon.").
- **Never:** hype, promises, guarantees, "tax" framing, "smash that like button", "Good punting",
  or a "this is just a game" line.

### Dave (the audience) — write to ONE person
Everything is written for **"Dave"** — an ordinary punting enthusiast who wants **practical help,
not hype**. Talk *to him*, directly ("you've probably…", "here's what I'd do"), never to "punters"
in the abstract. **For the full picture of Dave, use the `pp-my-audience-avatar` skill — this skill
defers to it and never re-defines him.**

---

## 3. THE PROCESS — step by step

### Step 1 — Read the whole article first
Understand the argument, its order, and the single core idea before writing a word. Note every
quote (with who said it) and every number.

### Step 2 — Lock the PACKAGING first (the Words Gate)
First, run the article through the **`pp-signature-concept-finder`** skill — it surfaces the ownable,
nameable idea (a short name, acronym, number-rule or simple diagram) hiding in the article. That
concept is usually the strongest **hook** and becomes the episode's signature concept.

Then decide and lock the **packaging** — these are the words every asset uses:

- **Eyebrow** — always `HOW TO WIN AT HORSE RACING`.
- **Hook** — the big 3–5-word thumbnail phrase, Anton caps, curiosity/strategy only (no odds, no
  guarantees). It should **complement, not repeat** the YouTube title.
- **Byline** — one supporting line that *explains the cryptic hook* in plain words.
- **YouTube title** — Hugh's SEO rule: lead with `How to Win at Horse Racing: ` then the specific
  promise/question.
- **E-book title.**

Put these in `episode.json` as `packaging {hook, byline, youtube_title, ebook_title}` **verbatim**.
The engine will not build assets until a human approves these on the board. Choose them with care —
**everything downstream copies them exactly** (a typo here ends up on the thumbnail, cover, title
card and video).

If any packaging word changes after drafting (it happens — EP09's byline did), **refresh the script
draft's packaging block at the same time.** `episode.json` stays the sole source of truth; a stale
draft block is a QC flag.

### Step 3 — Find the article's spine (a lens, not a rewrite)
Write the article's own arc in five lines to yourself — **Situation → Desire → Conflict → Change →
Result** (the Story Spine). This is a *lens* to keep the episode from sprawling; it does **not** give
you licence to reorder or invent. Identify the **single core idea** — everything serves it.

### Step 4 — Chunk into beats, near-verbatim, in the article's order
- Short spoken paragraphs (beats), **one idea each**, in the article's order. **Let the article set
  the count** — ~14–24 is typical (EP09 ran 16); never pad a short article to hit a number.
- Keep the words **near verbatim** — tidy lightly for the ear, never change meaning or advice.
- **Quotes → spoken attribution:** "As [name] says, …".
- Number the beats B1…Bn. Mark where a card (`[GFX Cxx]`) and where b-roll (`[B-ROLL …]`) land.

### Step 5 — Write the HeyGen spoken track (write for the *voice*, not the eye)
Produce the clean narration `.txt`, one paragraph per beat. Obey the **TTS + human-voice rules** in
§4B and §4C religiously — this is where scripts sound robotic if you're careless. In particular:
**every number, date, time, price and odd is spelled out as the words you want spoken** (§4B).
The ~6–7s silent head and ~3s tail are **render/build properties** — request them in the HeyGen
template / build config and verify them on the master; the `.txt` cannot hold silence.

### Step 6 — Craft the SEAMS (where your writing lives)
The seams are the only original prose. Make them excellent:
- **The opening** (§4A) — frame the article's start as a hook that earns the next 30 seconds.
- **Signposts & transitions** (§4A) — bridge beats so there's never a clean "you could leave now"
  moment; keep open loops.
- **The midroll invitation** (§4E) — the fixed shape, reworded fresh, ~45–55% through.
- **The outro** (§4F) — the standing structure, verbatim except the one wind-down line.

### Step 7 — Spec the visuals
- **Cards** (§4G) — MORE motion graphics than we used to run. **Every historical fact, date and
  number Gordon says gets an on-screen motion graphic.** One idea per card; payoff figure is the
  hero; each card must also work as a clean still (= the e-book figure).
- **B-roll** (§4H) — MORE cuts than we used to run, to cover talking-head stretches. Every clip
  matches the exact line; **mounted horses, everyone dressed**, lush turf, ~50% hats, Aus mix.
- **Tables** (§4I) — never read aloud; distilled to one idea on a card; full set in the e-book.

### Step 8 — Numbers-check
Collect **every figure** into the numbers list. Reproduce source tables exactly, check the
arithmetic, and flag/fix any garbled scan **before** anything goes on a card. Numbers get a **human
tick** before the cards lock. **Never animate a wrong number; never let Gordon narrate an unverified
one.**

### Step 9 — Self-review (do this before handing off)
**Compare-to-article fidelity pass (v1.2 — do this FIRST).** Put the spoken track beside the source
article and diff them beat by beat. For each beat ask: *is this the article's own sentence, lightly
tidied for the ear — or have I written a fresh one that means roughly the same thing?* **Flag any
beat that has drifted into paraphrase** (a heavy reword) rather than a light tidy, and pull it back
to the article's wording before going further. Expect only the opening framing line, the
transitions, the midroll and the outro to be original prose; everything else should be traceable,
sentence by sentence, to the article. If you cannot point to the source sentence, it does not ship.

Then run the **QC checklist** in §5. Then read the whole spoken track **aloud** in Gordon's voice —
every stumble, every unnatural pause, every line that sounds like a different narrator gets fixed.

---

## 4. THE CRAFT (reference)

### 4A — Hooks, loops & retention (applied in the seams, within fidelity)
- **Earn the first 30 seconds.** No logos, no "welcome back". Open on the article's most curious
  point — a **specific question Dave already has**, a **misconception to correct**, a **concrete
  number**, or the **promise of the payoff**. (EP09 opened on the three-track puzzle — that's the
  shape.)
- **Open a loop, don't close it.** End the opening with a question you answer later.
- **Build the body from Setup → Tension → Payoff loops** (~3–5 across the episode) and **overlap
  them** — open the next before fully closing the current ("that handles speed — but speed's useless
  without the second factor…"). Never leave a clean exit point.
- **Signpost.** Tell Dave where he is and what's coming; number points out loud.
- **Simple → advanced.** Plain-English first (so nobody's lost early), nuance layered on for the keen.
- **Re-hook at ~60–70%** to catch the late-video dip. A fresh tension, a named controversy, or a
  new evidence payoff all count (EP09 used the Plante & Scott turn) — a literal "coming up" teaser
  is not required, and usually isn't Gordon.
- **Dual-code numbers.** Show the figure on screen **and** speak its *meaning* ("forty-three per
  cent — nearly one in two"), not just the digits. (See §4G.)
- All of the above lives in the **seams and presentation** — the article's facts and order stay put.

### 4B — Numbers, dates, odds & symbols for TTS (spell what you want said)
The voice engine *guesses* and often guesses wrong on exactly the content we use most. **Write the
words you want to hear.** Never leave shorthand in the spoken track.

| You mean | DON'T write | DO write |
|---|---|---|
| Year | `2026` | twenty twenty-six |
| Decimal time | `70.3s` | seventy point three seconds |
| Distance | `1200m` | twelve hundred metres |
| Percent | `43%` | forty-three per cent |
| Odds (fraction) | `7/2`, `9/4` | seven to two, nine to four |
| Odds (each-way line) | `7/1` | seven to one |
| Range | `5-10` | five to ten (a hyphen may be read "minus") |
| Money/tote price | `$3.40` | three dollars forty (or "three-forty") |
| Date | `01/02/2026` | the first of February, twenty twenty-six |
| Decade | `1990s` | the nineties |
| Ordinal | `2nd` | second |
| Group/Race codes | `G1`, `R4` | Group One, Race four |
| Symbols | `%  &  +  =  £` | per cent, and, plus, equals, pounds |
| Abbrev. | `approx.` `e.g.` `etc.` | approximately, for example, and so on |

Rounding note: it's fine to **round in speech** for flow ("seventy-point-seven") while the **card
shows the precise figure** ("70.66") — that's intentional, not an error; just be consistent
(the spoken value must round *to* the card value).

### 4C — Writing that sounds human, not AI-slop
Gordon is already an AI avatar, so the writing must over-index on warmth and humanity.

**AVOID (the AI fingerprint):**
- Cliché words: *delve, dive in, unpack, navigate the landscape, in today's fast-paced world, when
  it comes to, unlock, unleash, elevate, harness the power of, game-changer, realm, tapestry,
  testament to, plays a crucial role, it's worth noting, needless to say.*
- Empty transitions: *Moreover, Furthermore, Additionally, In conclusion, Ultimately, That said,
  It's important to note that.*
- Hedging mush: *can help to, may potentially, tends to, in many cases, generally speaking.* (An
  expert states things.)
- The over-balanced *"not only… but also"* pile-up; triad overload ("faster, smarter, better");
  list-y sameness where every sentence is the same length.
- Hollow superlatives: *incredibly powerful, truly remarkable, seamless, robust, world-class.*
- **Em-dash overuse** — a strong AI tell. Dashes are great but ration them: a paired parenthetical
  (— like this —) counts as ONE use; budget **≤2 uses per paragraph**, and rework any paragraph
  that hits three.
- Fake enthusiasm: "Great question!", "Buckle up!", exclamation spam.

**PURSUE (human warmth):**
- **Specificity** — real races, tracks, prices, exact numbers.
- **A point of view** — Gordon takes sides ("I don't back odds-on favourites, full stop").
- **Direct address** to Dave; **rhythm through contrast** (long sentence, then a short one); **plain
  concrete verbs** (back, drift, firm, dodge, pounce); **deliberate fragments** ("Every time.");
  **conversational openers** ("Now,", "Here's the thing,", "But,").
- **Warmth through generosity** — answer the doubt before Dave voices it.

**Sentence craft for the ear:** write for the breath (≈8–20 words as the backbone); **vary length
deliberately**; front-load the point; one idea per sentence; break where a person would pause to
think. Punctuation is timing: comma = short breath; em dash = a beat before a reveal (sparingly);
ellipsis = a weightier hanging pause; full stop = finality; question mark = warmth + a rising,
engaging pitch (use real questions — "Sound familiar?").

**Homographs** (the biggest accuracy risk) — rephrase to force the meaning: *lead/led, read (reed/
red), live ("a live chance"), record, present, bow, minute.* Avoid tongue-twisters and stacked
sibilants.

### 4D — Bringing craft and fidelity together (the judgement call)
The article gives you **substance, order and advice** (fixed). You add **framing, rhythm,
signposting, presentation** (free). If a retention trick would require changing what the article
says or the order it says it in — **don't**. Where the article already hooks and loops well (most
do), amplify it in the seams rather than manufacturing your own.

### 4E — The midroll like/subscribe invitation (standing rule)
ONE gentle invitation, in the **MIDDLE** (~45–55%), on a beat boundary, Gordon on camera (MCU),
once only. It is the outro voice — warm, plain, wry, Australian. **No hype.** Tie the ask to the
listener's benefit and to helping *others* find it, not to "help me grow".

- **Fixed shape:** soft value hook → the ask (a like helps others find it; subscribe) → the
  **cadence line** → a light wry nod → return to content ("Right — where were we.").
- **Cadence line — LIVE VARIABLE:** currently **DAILY** ("a fresh one every day at the moment,
  weekly down the track"). Update when it changes.
- **VARY the wording every episode** — same shape, fresh phrasing; never reuse verbatim (identical
  text has previously corrupted the HeyGen render). Also **vary the "noise out there" line** — don't
  lean on it every time.
- **On screen:** its own `cta-midroll` beat; a **restrained lower-third** on the charcoal dark-chip
  — a small thumbs-up (like) **and** a Subscribe icon, orange accent, gentle fade. The chip must be
  **composited** (not just rendered) and the icons **present and visible**, with **≥ 6 seconds of
  full visibility** (fades on top of that — a 5s chip with 0.4s fades is under the bar; EP09
  shipped 5.0s, so stretch the chip from EP10 on). No loud animated YouTube buttons.

### 4F — The standing OUTRO (verbatim structure, every episode)
After the last article line, before the end card, in order:
1. **Short warm wind-down** of the topic (1–2 lines) — *the only part that changes per episode.*
2. **Point to the FREE E-BOOK** — soft, "the link's just below this video," frame it as *continuing
   to help* (see §4J). No hype.
3. **Responsible-gambling line — MANDATORY, verbatim intent:** "And remember — never bet more than
   you can afford to lose."
4. **Warm sign-off:** "That's me for now. Look after yourself, trust your form study, and I'll see
   you soon." (Never "Good punting"; no "it's just a game".)

Same avatar/voice/background; numbers as words. Approved by Hugh once, then verbatim (only line 1
changes).

### 4G — Motion cards (MORE of them; every fact/number gets one)
- **Standing rule (from EP09):** every **data fact, date and number** Gordon says — anything Dave
  might act on or want to verify — gets an on-screen motion graphic. A number inside a *story* beat
  (EP09's "Embarrassed" tale) may ride on b-roll instead, at the writer's judgement.
- **One idea per card; the payoff figure is the hero** (big orange numeral that slams/scales in). No
  single takeaway → it's two cards.
- **Dual-code:** show the figure, speak its *meaning*; **animate** the reveal (count up, grow a bar,
  fill a track) rather than a static slide; reveal complex data step-by-step in sync with narration.
- **Form:** a **MIX** of full-screen and Panel-Push (Gordon glides aside, graphic in the freed third;
  never overlap him). Not every card full-screen.
- **Timing/sync (standing rule, from EP09):** a card must **ENTER on (or just after) the moment
  Gordon says its matching line — never before — and HOLD long enough to read comfortably.** Drive
  it off the master's word-level timings (WhisperX/shot-map). Don't let a card overrun a b-roll cut.
- **E-book duality:** every card must also read as a clean **still**; the writer picks which stills
  become e-book figures (`figure N = card CXX`, rendered from the card HTML, not Higgsfield). Most
  cards should make the cut — skipping one is a deliberate choice, noted in the spec, never an
  oversight.
- A card spec carries: `card id` · beat · Anton headline · eyebrow · payoff figure(s) · the animation
  (what moves, order, timing) · full-screen or Panel-Push · the print/e-book note.

### 4H — B-roll (MORE cuts; mounted horses, everyone dressed)
- **Standing rule:** enough b-roll that **no talking-head stretch runs uncovered (no card, no
  b-roll) for more than ~40 seconds** — every clip matched to the exact line. (EP09's longest bare
  stretch, B12–B13, sat right on this line.)
- **Prompt shape:** subject + action → setting ("lush green turf racecourse") → crowd truth (~50% in
  hats incl. Akubra/fedora; the Australian ethnic mix ≈ 75% white / 9% Asian / 9% Middle-Eastern /
  5% Black; wide ages) → mood (photoreal, cinematic, natural light) → negatives (no dirt, no US
  signage, no repeated framing).
- **Horses must be MOUNTED** — riders up, jockeys in silks, saddles and bridles clearly visible.
- **Everyone fully and appropriately dressed; no AI anatomy/artifact weirdness** (no rider-detached
  horses, no object-through-body, no extra/missing/fused limbs). "Invisible at speed" is **not** the
  bar — these get caught and rejected. (Engine exports a 6-up contact sheet for a human glance.)
- **Turf only** (models default to US dirt — say "lush green turf" every time). **No clip repeats**
  within or across episodes — check `docs/broll-registry.md`, log new clips.

### 4I — Tables & dense data
- **Gordon never reads a table aloud.** The spoken track states the ONE takeaway and points to it;
  the numbers live on the card.
- The **video card is not the raw table** — distil to the single idea (pick the rows that prove it,
  colour-code the two sides, animate the eye to the payoff). **Name the takeaway** (EP07's value
  table → "The 7/1 Line").
- **If the full data matters, the E-BOOK figure carries it** — print can be dense. Same card HTML,
  two variants (distilled/animated video; full/static print).
- In the e-book, **keep every table with its heading on the same page** (no orphaned headings).
- **Verify the numbers first** (see Step 8). Insufficient-data cells render as a dash — never the
  word "verify" — in any published build.

### 4J — The e-book CTA (warm, never pushy)
Promote the free e-book as **you continuing to help**, not a transaction — "I couldn't fit
everything into one video, so I wrote the rest down for you." Lead with the **outcome/relief** (what
it lets Dave *do* or stop worrying about), not features (pages/chapters). Give it **one clear
promise.** If an email is needed, say so plainly with an easy out. Deliver the video's payoff first,
then offer the guide as the natural next step. Use **Link → Gap → Promise**: reference what he just
learned → open a small new question → promise what the guide/next step delivers.

---

## 5. QC / SELF-REVIEW CHECKLIST (run before hand-off)

**Fidelity & content**
- [ ] **Words lifted, not rewritten** — spot-check 3–4 beats against the source article: same
      sentences/phrasing, lightly tidied only. If it reads as a paraphrase in our own words, pull
      it back to the article's wording. Only the opening line, transitions, midroll and outro are
      original.
- [ ] Article's facts, advice and order kept faithfully; nothing invented or reordered.
- [ ] Any quotes attributed ("As … says") — pass if the article has none.
- [ ] One idea per beat; beat count sized to the article (~14–24 typical, never padded to a target).

**Packaging (Words Gate)**
- [ ] Eyebrow = HOW TO WIN AT HORSE RACING; hook 3–5 words complementing the title; byline explains
      the hook; YouTube title leads with "How to Win at Horse Racing:"; e-book title set. All in
      `episode.json` verbatim, spellchecked; the draft's packaging block matches `episode.json`
      (no stale words after a change).

**Spoken track (TTS)**
- [ ] Every number/date/time/price/odd spelled as words; symbols & abbreviations expanded.
- [ ] Homographs de-risked; no tongue-twisters/sibilant stacks.
- [ ] ~6–7s head + ~3s tail requested in the render/build and verified on the master (the `.txt`
      holds no silence).

**Voice / anti-slop**
- [ ] No slop words/transitions/hedging; em dashes rationed (a pair counts once; ≤2 uses/para);
      sentence lengths varied; spoken *to* Dave; Gordon's fixed voice throughout; read aloud and
      de-stumbled.

**Seams**
- [ ] Opening hooks + opens a loop; transitions bridge beats; re-hook near 60–70% (fresh tension,
      controversy or evidence payoff all count — no literal teaser required).
- [ ] Midroll: fixed shape, reworded fresh, cadence line current, ~45–55%, icons specified with
      ≥6s full visibility.
- [ ] Outro: standing structure verbatim (only wind-down changes); responsible-gambling line present;
      "see you soon" sign-off.

**Visuals**
- [ ] Every *data* fact/date/number has a card (story numbers may ride on b-roll, by choice); cards
      enter on-cue and hold long enough; mix of full-screen + Panel-Push; each card works as a
      still; e-book figure picks are deliberate.
- [ ] No talking-head stretch runs uncovered (no card, no b-roll) beyond ~40s; every clip matched
      to its line; mounted horses; everyone dressed; turf; no repeats.
- [ ] Tables: not read aloud; distilled on card; full set in e-book with headings kept together.

**Numbers**
- [ ] Numbers list compiled; source tables reproduced exactly; arithmetic checked; flagged for the
      human tick. No unverified number narrated or animated; no "verify" markers in a publish build.

---

## 6. HARD "NEVER" LIST
Never rewrite the article's advice or add facts · never hype/promises/guarantees · never "tax"
framing · never ElevenLabs (US accent) · never leave numerals/symbols in the spoken track · never
"smash that like button" / "Good punting" / "it's just a game" · never repeat a b-roll clip (within
or across episodes) · never dirt/sand tracks · never riderless horses or undressed people · never a
card that overlaps Gordon or overruns a b-roll · never narrate a broken/unverified number · never a
"verify" marker in a published e-book · never build assets before the packaging is approved at the
Words Gate.

---

## Where this skill sits (no overlap with the others)
This is the **create-brain / script-writing** step. It works *with*, and defers to, the existing PP skills:
- **`pp-episode-pipeline`** — the master end-to-end workflow. This skill is the "write the script & packaging" stage *within* it.
- **`pp-my-audience-avatar`** — the definition of Dave. Use it for the audience; this skill does not re-define him.
- **`pp-signature-concept-finder`** — run on the article at Step 2 to find the ownable concept/hook.
- **`pp-episode-production`** — the build skill (render, ffmpeg, e-book, thumbnail). This skill decides *what is said & shown*; that one *builds* it.

*Base standards: `docs/PP-STANDARDS.md`, `PP-midroll-invitation-standard`, `PP-episode-outro-standard`.
Keep this skill in `.claude/skills/pp-episode-script/SKILL.md` so Claude Code reads it whenever it writes an episode.*
