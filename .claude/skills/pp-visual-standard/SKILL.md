---
name: pp-visual-standard
description: >
  The editorial standard for Practical Punting motion-graphic cards — what a card
  is FOR, the ten rules every card must pass, and how a SEQUENCE of cards should
  read. ALWAYS use this skill when designing, authoring, choosing a block for, or
  reviewing PP episode cards, when writing the shot plan, when deciding which
  moments of an article deserve a card, or when critiquing a rendered contact
  sheet — even if it isn't named. It is the answer to "is this card any GOOD",
  which the mechanical checkers deliberately do not test. Grounded in Mayer's
  Cognitive Theory of Multimedia Learning. Does not cover b-roll (see
  pp-broll-brief) or rendering mechanics (see pp-episode-production).
---

# The PP visual standard — what makes a card good

**The mechanical checkers test whether a card is CORRECT** — traced to the source, fits its box, enters on its spoken cue, clears the logo. **This skill is the only thing that tests whether it is any GOOD.** Both must pass.

> **The finding that caused this standard.** EP13 shipped thirteen cards. Every one passed every gate. Jodie's verdict: *"not that interesting… they don't draw the viewer along with the ideas."* **Seven of thirteen were pure assertion, three restated the sentence being spoken, one announced "seven axioms" and only four ever appeared.** Correct, and worthless.

---

## 1. The research this rests on — do not argue with it from taste

Narrated video with graphics, teaching a method, is a heavily studied problem (Mayer, *Cognitive Theory of Multimedia Learning*; Ausubel on advance organizers). Four findings bind us:

- **REDUNDANCY.** On-screen text that duplicates the narration makes comprehension **worse than no text at all.** Not neutral — harmful. *A card that sets the sentence he is speaking is worse than no card.*
- **TEMPORAL CONTIGUITY.** A picture separated in time from its words loses most of its value. **Timing is a WINDOW, not a point: the card must be ON SCREEN WHILE THE WORDS IT ILLUSTRATES ARE SPOKEN.** *(This line used to read "Cue + 3.0s, verified against the transcript". That is the POINT rule, and it is not sufficient — it is exactly what put EP13's axiom-three card on screen as Gordon began axiom four, because the cue sat in the last five words of its own paragraph so cue+3.0s could only land in the next subject. Entry is still cue + 3.0s; **R10 is what makes it correct.**)*
- **PRE-TRAINING / ADVANCE ORGANIZER.** Naming the parts **before** explaining them measurably improves retention. *If the article has a numbered method, show the whole list first.*
- **SIGNALLING.** Cues showing what matters, and where the viewer is, reduce wasted effort. *"RULE 4 OF 7."*
- **COHERENCE.** Removing decorative material **improves** learning. A card that adds nothing is not free.

---

## 2. What a card is FOR

**Every card must do exactly one of four jobs, declared as `job` in `episode.json`. A card that does none is decoration and must not be built.**

| `job` | What it does | Typical block |
|---|---|---|
| **`orient`** | shows the shape of what is coming, before it is explained | `steps` ladder, `slate` |
| **`locate`** | shows where we are inside that shape | the rail modifier |
| **`relate`** | shows how two or more things connect — a chain, a contrast, a trade-off, a cause | `steps` cascade, `compare`, `bars`, `ratio` |
| **`anchor`** | holds ONE number still long enough to absorb | `stat` |

> ## ⭐ A CARD THAT STATES A FACT IS DECORATION. A CARD THAT SHOWS HOW TWO THINGS RELATE IS TEACHING.
> `orient`, `locate` and `relate` teach. **`anchor` is the only job that legitimately just asserts — and it is capped, because it is the easy one to reach for.**

---

## 3. The ten rules

Each says whether a machine enforces it. **A rule with no mechanism is a hope.**

**R1 · NEVER SET THE SENTENCE HE IS SPEAKING.** A card must not restate its own narration, and a card's headline must not restate its own body. *(Redundancy — the actively harmful one.)* → **halt: the echo test.**

**R2 · EVERY CARD DECLARES ITS JOB.** No `job`, no build. → **halt.**

**R3 · AT MOST 40% OF CONTENT CARDS MAY BE PURE ASSERTION.** **Measured on the BLOCK the card actually uses** (`stat`, `price`, or a bare `statement`) — **never on the declared `job`.** *A job is a CLAIM, not a fact: relabelling a `statement` as `relate` improves the number without changing a single pixel. EP13 as shipped was 54% by block; after the rebuild it is 20% by block — because the cards changed, not the labels.* → **halt.**

**R3a · THE DECLARED JOB MUST BE CONSISTENT WITH THE BLOCK.** `anchor` → `stat`/`price`; `relate` → `compare`/`steps`/`bars`/`ratio`; `orient` → `steps`/`slate`. A card cannot claim to relate two things while using a block that can only assert one. → **halt.**

**R4 · AN ANNOUNCED COUNT MUST BE KEPT.** If any card says "seven", seven must be shown and each member must carry its position. → **halt.**

**R5 · A NUMBERED METHOD GETS AN `orient` CARD FIRST AND `locate` MARKERS THROUGHOUT.** The highest-value pair in the research. → **halt once the argument shape is declared.**

**R6 · READING TIME MUST NOT EXCEED HOLD TIME.** Allow ~2.5 words/second plus 1.0s to notice the card arrive. If it cannot be read it cannot teach. → **halt.**

**R7 · THE SEQUENCE MUST CHANGE SHAPE.** No more than two consecutive cards on the same block. *From across the room EP13's C1, C5 and C10 were indistinguishable.* → **halt.**

**R8 · ONE IDEA PER CARD.** If it needs "and", it is two cards or the wrong block. → **flag, do not halt.**

**R9 · NOTHING ON SCREEN MAY CONTRADICT THE NARRATION.** → **halt.**
*EP13's C5 shouted "ENOUGH WEIGHT WILL STOP A TRAIN" — the claim Gordon states in order to demolish it — with his rebuttal in the smallest grey italic on the card. **A viewer skimming learned the opposite of the lesson.** When the article states a claim to reject it, the REBUTTAL takes the big type and the claim goes in the opposing column.*

**R10 · A CARD'S VISIBLE WINDOW MUST COVER THE WORDS IT ILLUSTRATES.** → **halt.**
- **ENTRY** — the card must enter **while its passage is still being spoken**: not before it starts, not after it ends.
- **RELEVANCE** — overlap ÷ card window **≥ 80%**. Most of a card's life is spent on its own subject.
- **TRESPASS** — hard fail if it is still up when **another card's subject begins**. It may outlive its own words; it may never sit on top of someone else's.
- **Timing is a WINDOW, not a point.** Mayer's temporal contiguity: words and picture must arrive **together**.

> **The failure that produced R10.** EP13's axiom-three card entered **0.8s AFTER its passage ended**, as Gordon said "Axiom four, class". Every instrument passed it, because every instrument asked *"did it enter at cue + 3.0s?"* — and it had. **Nobody asked whether the subject was still being discussed.** Jodie saw it by eye, three times, and was right every time.

> ⚠️ **R10 AND R6 TOGETHER EXPOSE A SCRIPTING FAULT, NOT A LAYOUT ONE.** If a card needs more seconds to be read than its passage lasts, the words on screen are not the problem — **the script has under-served the idea.** EP13 gives axiom three, the hinge of the entire method, **8.4 seconds**, and gives axiom four **25**. No layout can fix that. **Catch it in the shot plan, before HeyGen is paid:** *"this card needs 13s, this passage is 8s — one of them has to change."*

---

## 4. The sequence, not the card

**Cards are inspected one at a time and experienced one after another. That gap is where episodes go wrong.**

- **Build the contact sheet and critique it YOURSELF before anyone sees it.** Ask: does this read as a journey? Does the shape change? Is any card decoration? Does anything repeat? **Fix what you find, then report.** Jodie does not approve graphics — the standard does.
- **The first three cards must establish the shape of the episode.** Someone who leaves at ninety seconds should still know what the method *is*.
- **Prefer fewer, better cards.** Coherence says a weak card costs more than it gives.

---

## 5. Choosing a block — follow the argument, not the habit

**Declare the article's `shape` first**, from a closed vocabulary, then let it choose:

| Article shape | What it must produce |
|---|---|
| `numbered-method` | an `orient` spine card + `locate` rails on every member |
| `causal-chain` | at least one `relate` card showing the chain in stages |
| `myth-knocked-down` | a `compare`, with the rejected claim in the cross column |
| `comparison` | `compare` or `bars` |
| `worked-example` | `stat` anchors carrying the real figures, in order |

> **The trap that caused this.** `statement` always works, so it becomes the default and nothing pushes back. **The templated EP13 came out LESS varied than hand-made EP12.** *Anything the machine can always fall back on, it will.*

**Known blocks:** 3 assert (`statement`, `stat`, `price`) · 2 parallel (`compare`, `slate`) · 2 magnitude (`bars`, `ratio`) · 3 list · **1 progression (`steps`)**. `steps` is the only block that shows a sequence and it went unused for three episodes because it was capped at three items. **That cap is gone — it now takes up to eight, and from four up it lays out as a numbered ladder, so it carries a seven-rule spine.** **Reach for it.**

---

## 6. Hard constraints that override everything here

- **§0a is absolute.** The article's sentences are never rewritten to suit a nicer graphic. **What may change is WHICH sentence is chosen and HOW it is shown.** A shorter contiguous quote is legal — `check_trace` binds values containing digits only.
- **Every figure traces** to a literal sentence in the source article.
- **Tightening a gate needs no permission. Loosening one needs Jodie's ruling.**
- **One design, two uses** — every card renders twice, dark for the video and light for the e-book figure. Judge both.

## 7. What this skill cannot tell you
It cannot say whether something is beautiful, or whether a diagram lands emotionally. **Look at the cards.** When Jodie finds something wrong in a finished episode, that is not a re-render — **it is a finding that changes this file**, so it is wrong once rather than every time.
