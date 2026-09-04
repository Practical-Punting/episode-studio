# YouTube metadata kit (title + description)
*Proven on EP02 + EP03, 2026-07-21. **Claude Code writes these** (Jodie's ruling, 26 Jul 2026 — ownership moved from Cowork to the build side): write the title + description into `PP-EPxx/output/PP-EPxx-youtube.txt`, and Jodie uploads. Titles/descriptions are content Jodie publishes — she reviews before posting.*

## Title formula

> ## ⭐ THE TITLE IS DERIVED, NOT INVENTED, AND THE FILE CARRIES ONE OF THEM
> ### `youtube_title = episode.json -> title + " | How to Win at Horse Racing"`
> **VERBATIM. No re-casing.** The episode name is already cased the way it ships on the
> cover and the title card, so re-casing here could only introduce a difference.
> **ONE decided title, on line 1, alone. No recommendation. No alternatives. No menu.**
> Enforced by `scripts/youtube_title.py`, which is the ONLY place the house form exists
> — the kit describes it, that file *is* it. The engine refuses a copy file that carries
> a second candidate.

> ### 🔴 THIS LINE USED TO READ `TitleCase(packaging.byline)`. CORRECTED 5 Aug 2026.
> **The code stopped deriving from the byline on 2 Aug 2026 and this document did not.**
> `youtube_title.py` now calls `derive(title_of(epj))` and **`title_case()` was deleted**;
> its own comment records why — *"measured across EP11-EP14, THE EPISODE NAME AND THE
> YOUTUBE TITLE HAVE NEVER ONCE MATCHED. One name everywhere a viewer looks."*
> **The drift was invisible for three days because the byline and the title were
> near-identical on every episode.** EP16 is the first where they are DIFFERENT STRINGS
> (title `Squeeze Those Odds! — Part 2`, byline `Each Way Betting Forever`, per the series
> amendment in `PP-STANDARDS.md` §1a) — **so following this page as written would have
> produced `Each Way Betting Forever | How to Win at Horse Racing` and HALTED
> `check_one_name`.** *A rule that agrees with the code only while two values happen to
> match is not agreement.*

**WHY IT IS DERIVED (Jodie, 29 July 2026).** The YouTube title used to be composed at
**~86%, long after the last approval gate** — `title_approved` was already true on EP13
before the copy file was written. **So the one string a viewer sees first had no gate at
all.** `packaging.byline` is approved at the **Words Gate on turn 1**, so deriving from it
means the title **inherits an approval it already has**: no new gate, no new button for
Hugh, nothing invented late.

**THE MEASUREMENT THAT SETTLED IT.** Jodie's own EP13 title —
`How a Professional Assesses Race Form | How to Win at Horse Racing` — is the byline
(*"How a professional assesses race form"*) title-cased, with the channel line appended.
Word for word. Not the episode title, and not a written phrase.

**Title case:** small words stay lower case unless first or last —
*a, an, the, and, but, or, for, nor, at, by, in, of, on, to, up, as, if, is.*
Hyphenated compounds capitalise each part (`first-up` → `First-Up`).

> 🔴 **WHY "ONE TITLE" IS A RULE AND NOT A PREFERENCE.** EP13's copy file offered a
> recommendation and two alternatives, **none of which was the title Jodie wanted.** She
> composed her own, published it — and `episode.json` went on carrying the one she had
> rejected, because **nothing wrote her decision back.** Her words: *"The agreed title was
> not there — rather a set of other ideas!"*
> **A FILE THAT ASKS A QUESTION IS A HALT WEARING A TEXT FILE'S CLOTHES.** It looks
> finished and it is not, and nothing on the board is watching for the answer.

- 🔄 **THE ORDER: EPISODE-SPECIFIC PART FIRST, CHANNEL LINE LAST, PIPE SEPARATOR
  (Jodie, 28 July 2026; ✅ RULED THE SAME WAY BY HUGH, 28 July 2026 — in force from
  EP11/EP12 onward).** `<episode-specific hook> | How to Win at Horse Racing`
  - **Example:** `How a Professional Assesses Race Form | How to Win at Horse Racing`
  - ⚠️ **YOUTUBE COPY ONLY.** The **episode title**, the **e-book title** and the **folder
    name** are unaffected by this rule — it governs the YouTube title field and nothing else.
  - ⚠️ **ALREADY-PUBLISHED VIDEOS ARE NOT RETITLED.** The rule applies going forward; it is
    not a reason to go back and edit live listings.
  - **This SUPERSEDES the old form** — *"Lead with the SEO phrase 'How to Win at Horse
    Racing' (Hugh's request), then a colon/dash and the episode's specific hook"* — which
    produced EP02's `How to Win at Horse Racing: Killer Trifecta Strategies` and EP03's
    `How to Win at Horse Racing: The 10 Key Factors the Pros Use`. **Do not restore it.**
  - **Why the flip:** the first ~60 characters are what a viewer actually sees, and under the
    old form every episode spent them on the same seven words. The brand phrase still earns
    its keep at the end for search; the front of the title now belongs to the one thing that
    is different about *this* episode.
  - ✅ **THE OPEN FLAG IS CLOSED.** This entry used to read *"the retired form is attributed to
    Hugh… if Hugh wants the old shape back, that is his call to make."* **He made it, on 28 July
    2026, and he ruled for the NEW order.** Both names are now on the same rule, so there is
    nothing left to reconcile and nothing to revert.
- **THE YOUTUBE TITLE IS ALSO WHERE THE SIGNATURE CONCEPT GOES** when it does not belong in
  the hook. Jodie's ruling on EP13: a *series* hook has to work for **every part**, so a
  concept that lives mostly in Part 1 would make Part 2's thumbnail promise something it
  cannot keep. Each part has its own YouTube title, so being Part-1-specific is fine there.
  *(Her second reason, worth keeping: **"axioms" is not Dave's word — his is "rules".**
  Translate the source's vocabulary into his.)*
- Keyword-rich, ~50–70 characters, front-loaded (the first ~60 chars are what shows).
  *This is a property of the BYLINE now, not of a phrase written here. If a title comes
  out too long or too vague, the byline is what changes — at the Words Gate, where Jodie
  is already looking at it.*
- ~~Give Jodie one recommended title + two alternatives.~~ **RETIRED 29 July 2026.** See
  the derivation rule at the top: one decided title, and `packaging.youtube_title` is a
  RECORD of the derivation, not a second opinion.

## 🔎 THE OPENING SENTENCE — the indexed window (Jodie, 28 July 2026)
**The first sentence must carry the episode's real SEARCH TERM and the phrase "horse racing" —
without becoming a promise.**

- **The first ~150 characters are what YouTube indexes hardest and what shows in search
  results.** Anything that matters for being found has to be inside that window; everything
  after it is for the reader who already clicked.
- **Keep the honest hook. Lead on the real base rate, never a promise.** The keyword rule does
  not license hype — it constrains *which true words* you open with, not *how strong a claim*
  you make.
- **The article's own first move is usually the right one.** It was written to open a piece
  about exactly this subject; borrow its opening and swap in the searchable phrasing.

**WORKED EXAMPLE — EP12, before and after.**

> **Was:** *"Most horses coming back from a spell lose. That is not pessimism, it is an
> iron-clad fact, and it is why the fresh horse is the hardest puzzle in form study."*
>
> **Should have been:** *"Most horses resuming from a spell lose their first run back — an
> iron-clad fact of Australian horse racing form study. But roughly one first-upper in ten
> wins, and there's a way to tell which."*

The rewrite carries **horse racing**, **form study**, **first-up** and **Australian** inside the
indexed window **with no loss of honesty** — the base rate still leads, the promise is still
absent, and "roughly one in ten" is still the article's own number. Nothing was traded for the
keywords; they were simply put where they count.

## Description template
```
[Hook: 2–3 sentences that dramatise the episode's core idea.
 The FIRST sentence must obey §THE OPENING SENTENCE above.]

If you want to know how to win at horse racing through steady, sensible form study — not hype, and not luck — [one line tying to the episode].

What you'll learn:
• [point 1]
• [point 2]
• [point 3]
• [point 4]

📘 FREE e-book — "[E-BOOK TITLE]": download it free and keep the full method beside you every race day 👉 [PASTE E-BOOK LINK HERE]

Follow Practical Punting for steady, sensible form study [CADENCE] — no hype, no promises, just disciplined form study applied for you.

🔗 More: https://practicalpunting.com.au

Please gamble responsibly. If betting is affecting you or someone you know, call Gambling Help Online on 1800 858 858 or visit https://gamblinghelponline.org.au (Australia).

#AustralianHorseRacing #FormAnalysis #[EPISODE TAG] #RacingTips #PracticalPunting
```

## 📄 FILE LAYOUT — what `PP-EPxx-youtube.txt` must look like (ENFORCED, 4 Sep 2026)
The file carries THREE things — the title, the description, the notes — and the engine cuts
the middle one out for the publish card by two BANNER lines. **The banners are spelled in ONE
place, `docs/youtube-copy-form.json`, and the engine's reader takes them from there.** Copy
them exactly as they appear below (they are quoted from that file, and a test fails the day
this page and that file disagree):

```
<the decided title, alone>

DESCRIPTION — paste from here
==============================================================================

<the description — everything Jodie pastes, from the hook to the five hashtags>


==============================================================================
NOTES — for the record, not for pasting
==============================================================================

<the notes — the source for every figure, the hashtag reasoning, anything for the record>
```

- **A banner is the WHOLE line.** A sentence in the notes that merely *begins* with the word
  DESCRIPTION is not a banner. (The `===` fence either side of a banner, its case and the kind
  of dash are forgiven when matching; the words are not.)
- **The description starts at the top.** Nothing but the title may sit above the DESCRIPTION
  banner — no preamble, no menu, no note to the reader.
- **Both banners, once each, DESCRIPTION first.**
- 🔴 **A file without this layout is REFUSED.** The engine flags the episode, puts the reason in
  the run log, and writes NOTHING to the publish card. It no longer guesses.
- **Why (4 Sep 2026).** EP38–EP45 were written with a `=== NOTES — not part of the description,
  do not paste ===` fence and no DESCRIPTION banner, because this page never asked for one. The
  reader matched the first line that *began* with those words. Six episodes' publish cards got the
  whole file — the description with thousands of words of notes glued on — and EP39 and EP45 got
  a 99- or 4,668-character fragment of the notes, mid-sentence, because a notes sentence began
  "DESCRIPTION CARRIES A CURLY APOSTROPHE". The rail's 1000-character floor caught EP45 by luck
  and passed EP39 by luck. Nothing wrong went out: Jodie pastes from the file, not the card.

## #️⃣ HASHTAGS — EXACTLY FIVE, AT THE END, BEST FIRST
**(Jodie, 28 July 2026, from her own hashtag research — 129 tags scored. These are her
rulings.)**

```
#AustralianHorseRacing #FormAnalysis #{EPISODE TAG} #RacingTips #PracticalPunting
```

- **EXACTLY FIVE.** Best practice is 3–5. The technical cap is 15, and **exceeding 15 makes
  YouTube ignore ALL of them** — so the failure mode is silent and total, not gradual.
- **AT THE END, NEVER THE TOP.** The first ~150 characters are the indexed window; hashtags
  parked there push the keyword sentence out of it **for no gain** — a hashtag at the top is
  worth no more than the same hashtag at the bottom.
- **THE ORDER IS IDENTITY → CATEGORY → THIS EPISODE'S TOPIC.** The first three display above
  the video title, so those three slots are the only ones a viewer reads.
- **SLOT 3 ROTATES — the EPISODE TAG.** Scored options:

  | Tag | Score | | Tag | Score |
  |---|---|---|---|---|
  | `#HorseRacing101` | 9.5 | | `#RacingExplained` | 9.0 |
  | `#LearnToReadForm` | 9.3 | | `#FormGuide` | 8.9 |
  | `#HorseRacingAnalysis` | 9.2 | | `#BankrollManagement` | 8.5 |
  | `#HowToBetOnHorses` | 9.1 | | `#BettingDiscipline` | 8.5 |

  Plus **`#SpeedMaps` `#TrackBias` `#SectionalTimes` `#BarrierTrials` `#Blackbooker`
  `#Quaddie`** *where they genuinely fit the episode.*

  **TWO TESTS BEFORE THE SCORE — a high score does not win slot 3 on its own.**
  - **SLOT 3 MUST NOT RESTATE SLOT 2.** Slot 2 is fixed at `#FormAnalysis`, and slots 1–3 are
    the only ones a viewer reads. **An episode tag that means roughly what `#FormAnalysis`
    already means spends a display slot on nothing.** `#LearnToReadForm` (9.3) and
    `#HorseRacingAnalysis` (9.2) both score high and both fail this test most of the time —
    **check the pair before you check the number.**
  - **A NARROW TAG MUST MATCH WHAT THE EPISODE IS *ABOUT*, NOT ONE PART OF IT** (Jodie, EP13).
    The topical tags above earn slot 3 only when the episode is genuinely about that thing.
    **EP13 covers track bias in one axiom of seven, so `#TrackBias` would advertise a seventh
    of the episode** — it is saved for an episode that is actually about it. EP13 took
    `#HorseRacing101` (9.5): highest-scored, honest for a foundations piece, and it says
    something `#FormAnalysis` does not.

- 🔴 **NICHE BEATS VOLUME, DECISIVELY.** `#AustralianHorseRacing` scores **9.2** (~2,867 posts,
  competition **3/10**). `#HorseRacing` scores **6.1** (1.4–1.7M posts, competition **10/10**).
  **We are invisible in the mega tag.** **DO NOT add `#HorseRacing` back for its size** — its
  size is the whole problem. *(This kit prescribed it up to 28 Jul 2026; that was wrong.)*
- **`#RacingTips` STAYS.** Racing tips are what PP actually sells.

## 🚫 NEVER USE — compliance risk 8–10
```
#onlinebetting  #onlinegambling  #onlinecasino  #guaranteedwin  #bettingsite
#tab  #sportsbet  #ladbrokes  #horseracingkills  #nuptothecup
```
**We currently use none of these. Keep it that way.** They split into three kinds of trouble:
gambling-operator tags that read as advertising a bookmaker, `#guaranteedwin` which is a
promise the brand does not make, and the activist tags which attach the channel to a fight it
is not in.

## Cadence — a LIVE VARIABLE, not a fixed word (Jodie, 27 Jul 2026)
`[CADENCE]` in the template above is filled from the current upload cadence, which is
**DAILY now, moving to weekly further down the road**. Today write **"every day"**; when the
cadence changes, write "every week" — and change it **here**, once. It is deliberately a
placeholder rather than a hard-coded word so the template survives the change instead of going
stale, which is exactly how this file came to say "every week" while three other documents said
DAILY. The same live variable drives the midroll cadence line (`docs/PP-midroll-invitation-standard.md`)
and the sign-off's closing marker — one change, three places, all sourced from here.

## Brand rules for the copy
- **No hype, no promises, no guarantees, no inducements.** Steady, sensible, disciplined. This matches the on-screen warranty and the brand voice.
- 🔴 **NO LONG PRICE IN THE DESCRIPTION.** A price that appears in the video as *documented
  history* must not be lifted into the description. **EP12 deliberately kept Joie Denise's
  10/1 out:** on screen it is 1995 history with a date attached, but **a long price sitting in
  a description reads as an implied prospect** — the reader meets it with no race, no year and
  no context around it. **Part of this audience sits close to problem gambling**, and that is
  the distinction that matters. Probabilities, distances, weights and dates are fine; a
  quoted price is not.
- **EVERY FIGURE TRACES TO THE SOURCE ARTICLE.** No number in the copy may be rounded, tidied,
  averaged or invented. If it is not in the article, it does not go in the description — and
  the notes block at the bottom of the `-youtube.txt` file records where each one came from.

## ✍️ REPRODUCING HIS SENTENCE vs WRITING OUR OWN — two acts, two rules
**(Jodie, 28 July 2026. Decided once so it is not re-argued every episode.)**

> **REPRODUCING his sentence** — a card, an e-book figure, a quotation — **keeps his rendering
> EXACTLY.** `10 kgs`, `21 Ibs`, `firstup`, lower-case `joie Denise`. **We do not correct him.**
> That rule is unchanged and absolute.
>
> **WRITING OUR OWN SENTENCE that uses his figure** — a description, a title, a bullet — **uses
> OUR house style with HIS number untouched. Ten is ten, kilograms are kilograms.**

**THE WORKED EXAMPLE — EP13's weight axiom.** The article says *"it could take as much as
**10 kgs**-or **21 Ibs**-to change a result, all things being equal."*
- The **e-book body paragraph** reproduces that sentence and therefore carries **`10 kgs`** and
  **`21 Ibs`** exactly, scan artefact and all.
- The **YouTube description** is our own sentence about his figure, so it writes **`10kg`**.
  **Only a space and a non-standard plural differ, and "10 kgs" is a 1988 typographic quirk
  that reads as an error in 2026 public copy.**

**HOW TO TELL WHICH ACT YOU ARE PERFORMING.** Ask *whose sentence is this?* If a reader would
take the words as **his** — inside quotation marks, on a card that presents itself as his line,
in the reproduced article body — it is a reproduction and nothing may be touched. If the
sentence is **ours** and merely cites his number, house style applies to everything except the
number and its unit.

⚠️ **THE LIMIT OF WHAT IS ENFORCED.** `author_cards.py → check_trace()` compares **digit runs
only** (`digit_runs(norm(val))` against the traced sentence). So *"ten is ten"* **is** machine-
enforced — an invented `12kg` halts — but *"kilograms are kilograms"* **is not**: a card saying
`10lb` against a `10 kgs` sentence would pass today. **The unit half of this rule currently
rests on a human reading it.** *A ruling is not a mechanism.*
- **No "tax" framing** in titles/descriptions (even where an episode uses the idea internally).
- Always include the **responsible-gambling line** (Gambling Help Online 1800 858 858 / gamblinghelponline.org.au) and the **practicalpunting.com.au** link.
- The **e-book link** is the one thing the build side can't fill — leave `[PASTE E-BOOK LINK HERE]` and ask Jodie for the URL (offer to drop it in). *(Said "Cowork" until 28 Jul 2026; ownership moved to Claude Code on 26 Jul — see line 2.)*
- Keep the thumbnail hook and the title DIFFERENT (see thumbnail-standard.md) so they work together.

## Where this sits in the pipeline
YouTube title + description + thumbnail are the **publishing kit** — produced after the video + e-book cover exist, ready for Jodie to upload. Publishing itself (uploading, hitting publish, Mailchimp) is always Jodie's.
