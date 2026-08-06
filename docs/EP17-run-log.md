# EP17 — run log

**Started 6 August 2026.** *Where EP17 is · what was decided · what is waiting on a human.*

> **THE EPISODE:** *Testing the Numbers*, byline *The stats tell the story*.
> **Mr Money**, **Practical Punting, JANUARY 2007.** Not a numbered part — the article
> refers back to an earlier instalment on favouritism but carries no part line.
> Rail id `043682b8-7253-44bf-81d5-96e7b04e9fc0` · `ep_number` 17.

---

# 00. 🏁 THE FIRST LIVE COMMISSION. IT WORKED.
**`youtube_copy`, 12:18–12:22, 6 Aug 2026 — the first time this studio has ever had a
machine write one of its artefacts in a real build.**

```
wallet checked: max subscription — this costs rate limits, not money
commissioning the YouTube words — a writer is working, up to 900s, capped at $10.00
(the writer was refused 1 action(s): Edit - place scoping held)
the YouTube words written in 258s, $1.81, 19 turn(s)
```

| | live | the sandbox run | |
|---|---|---|---|
| time | **258s** | 123s | ~2× |
| cost | **$1.81** | $1.06 | ~1.7× |
| turns | **19** | 9 | ~2× |

> ### 📌 THE CAP NOW HAS EVIDENCE UNDER IT INSTEAD OF A GUESS.
> The design priced a run at **$10–30**. The real number is **$1.81** — an order of
> magnitude out. **The $10 cap is roughly 5× the observed cost**, which is the right shape
> for a runaway-turn bound. *And it is rate limits, not money: the wallet assertion ran
> first and said so.*

✅ **`check_youtube_title` PASSES** on what it produced: *"youtube title ok: Testing the
Numbers | How to Win at Horse Racing"* — the corrected lower-case "the", derived and not
re-cased. **10,008 bytes.**

✅ **PLACE SCOPING HELD IN A LIVE RUN, FOR THE FIRST TIME.** *"the writer was refused 1
action(s): Edit - place scoping held"* — proved on 5 Aug in a sandbox, observed here in a
real build.

### WHAT IT ACTUALLY WROTE — read before Jodie saw it
**Correct title verbatim. E-book placeholder left for the human. Responsible-gambling line
and Gambling Help Online present. Author credited as Mr Money.** Every figure traced, and
its notes name the trace source for each.
> 🔴 **AND IT HELD §0a-ii WITHOUT BEING TOLD TO.** The description names **number four
> only** for the short-favourite cut — *"which is what the ARTICLE'S OWN summing-up names…
> never a list with a hole in it"* — and keeps both category-3 figures out entirely. That
> rule was written this afternoon and lives in `PP-STANDARDS`, which it read.
> It also declined to headline the 50-per-cent payoff angle, on the grounds that *"a
> dollar price sitting in a description reads as an implied prospect"* — a brand-guardrail
> judgement nobody asked it for.

⚠️ **ONE HONEST GAP, AND IT IS THE ONE §4a EXISTS TO CLOSE.** Its notes say the verbatim
capture named in `episode.json -> source` **is not in the episode folder**, so it traced
against `episode.json`'s trace blocks and `spoken-words.txt` instead — **and it said so in
prose while returning `unread_sources: []`.** It was not wrong to proceed (both sources it
used are valid and in-place), but **the typed verdict did not carry what the prose knew.**
*That is exactly the reconciliation-against-a-manifest §4a describes, and it is still not
built.*

---

# 0a. 🖼 THE THUMBNAIL "DRIFT" — MEASURED, AND IT IS NOT DRIFT
> ### "The font sizes and location of the logo are very different. Why is the
> ### thumbnail not in line with the previous ones?" — **Jodie, 6 Aug 2026**, holding
> ### EP17's thumbnail flag after putting two pictures side by side.

**She is right that the two images differ. They are two DIFFERENT ARTEFACTS.**

| what she compared | actually | logo |
|---|---|---|
| the image she called EP15 | **EP15's THUMBNAIL** — part line, byline, 1280×720 | bottom-**LEFT** |
| the image she called EP17 | **EP17's TITLE CARD** (`title-preview.png`), 1920×1080 | bottom-**RIGHT** |

**EP15's TITLE CARD has the logo bottom-RIGHT too** — one-line headline with the
white/orange split inline, eyebrow with an orange rule to its left, byline in the lighter
face. **The two title cards match each other. The two thumbnails match each other.**
*The differences she saw are the differences BETWEEN the templates, and they are meant to
exist.*

### THE THUMBNAILS, MEASURED FROM THE PIXELS — EP11 to EP17
| ep | size | logo from left | logo from bottom |
|---|---|---|---|
| 11–17 | **1280×720, every one** | **56 px, every one** | **41 px, every one** |

**Seven episodes, identical.** `youtube-thumbnail-template.html` hard-codes
`.logo{left:56px; bottom:40px; width:210px}`, `.l1{96px}`, `.l2{150px}`, `.part{75px}`,
`.eyebrow{29px}`, `.strap{29px}` — one template, fixed numbers, in the repo.
*EP17's `NUMBERS` LOOKS bigger than EP15's `ODDS!` because it is a longer word at the
same 150px, and its strap sits higher because there is no part line to push it down.*

### ✅ AND IT ANSWERS A §B3 GAP — THE OPPOSITE WAY ROUND
`thumbnail-standard.md` and `thumbnail-hero-registry.md` are on Drive and not in the repo,
listed as *"real files the build cannot read"*. **Checked: `author_thumbnail.py` does not
read them, and never did.** Every number lives in the template in the repo.
> **So the risk is the INVERSE of the one recorded.** The build cannot drift from a
> standard it never opens. **The STANDARD can drift from the build** — and nobody would
> know, because the document has no reader.

### 📌 THE REAL FINDING, WHICH OUTLIVES TONIGHT
**NO CHECK IN THIS STUDIO COMPARES AN ARTEFACT WITH ITS PREDECESSORS.** Every guard asks
*"is this internally consistent?"* — `check_one_name`, `card_check`, `autofit`,
`self_qc`, the pre-flights. **A house style drifts by being internally consistent every
single time.** She found this by putting two pictures side by side, which is a thing
nothing automated does.
⚠️ **This time the answer was "no drift". That does not make the gap smaller** — it makes
it a gap we got a free look at.

---

# 0. 🔴 THE ALIGNMENT HALT — **79.8% AGAINST AN 85% FLOOR, AND THE FLAG NAMES THREE
# CAUSES THAT ARE ALL WRONG**

`align_to_script` refused at `heygen_download`, 10:48. Its words:
> *"the master is not reading this script — **wrong take, wrong episode, or the words
> changed after the render**."*

**All three are false, and the third would have sent Jodie to re-render a perfectly good
master.** *That is CLAUDE.md fault #6 exactly: a halt naming a cause it has not
established, in a way that makes the operator's next action look like the fix.*

### WHAT IT ACTUALLY IS — measured across every episode, not reasoned
**We spell every figure as WORDS for the TTS** (`six hundred and sixty`). **WhisperX
transcribes speech as DIGITS** (`660`). So **every spelled-out figure is a guaranteed
miss** — and EP17 is an article made almost entirely of figures.

| ep | words | number-words | share | anchored |
|---|---|---|---|---|
| EP07–EP14 | — | — | **1.9–5.8%** | comfortable |
| EP15 | 2,532 | 131 | **5.2%** | fine |
| **EP16** | 1,925 | 178 | **9.2%** | **87.8%** — "narrowest pass on record" |
| **EP17** | 1,537 | 213 | **13.9%** *(17.2% counting `per cent`/`dollars`)* | **79.8% — REFUSED** |

**The miss rate tracks the number-word share.** EP16→EP17: number-words **+4.7 points**,
miss rate **+8.0**. With units, **+6.7 against +8.0.**

> ### ⚰️ AND IT CLOSES THE OPEN QUESTION AT §1f — THE OPPOSITE WAY ROUND.
> That question was *"does a LOW-BITRATE master depress the anchor rate?"*, asked because
> EP16 scraped through on a 124 kbps master. **EP17's master is `ffprobe`-measured at
> 189,366 bps — the full API standard, complete, correctly trimmed — AND IT SCORED SEVEN
> POINTS WORSE.** **Bitrate is not the driver. Number density is.**

### 📌 THE FIX IS NOT THE FLOOR. IT IS THE COMPARISON.
**The 85% floor is not wrong; the MEASUREMENT is.** The matcher is comparing
*"six hundred and sixty"* against *"660"* and honestly recording a mismatch. **Lowering the
floor would treat the symptom and blind the guard that caught EP15's truncated master at
62.9%.** The fix is to fold number-words to digits (or the reverse) before matching, so a
figure we spelled out for Gordon's mouth can still anchor.
⚠️ **It changes the TIMINGS the whole episode is built from, so it is not a cosmetic
change** — but it produces MORE anchors and FEWER interpolations, which is the direction
the guard exists to push.

---

# 1. THE HALT TALLY — **THREE, AND TWO OF THEM ARE MINE.**
| # | at | what | whose |
|---|---|---|---|
| 1 | `audit_inputs` | `episode.json` missing — **Job Zero's second call site** | the studio's: a job not done |
| 2 | `heygen_download` | **the alignment refused at 79.8%** (§0 above) | **the machine's** — a matcher that never folded figures |
| 3 | `shot_map` | **C4, C8 and C10 are panel-push and I authored their beats MCU.** A panel-push card needs WIDE for its whole window or it lands on Gordon's face | **MINE** |
*(Plus the title-card crop flag at 10:23 — a DESIGNED human gate, cleared in five minutes. Not a halt.)*

> ### 📌 TWO OF THE THREE ARE THE BUILDER'S OWN AUTHORING FAULTS, AND THE TALLY SAYS SO.
> Halt 1 is `episode.json` not existing when the build asked for it. Halt 3 is framing I
> wrote wrongly. **Only halt 2 was the machine's.**
> **An honest tally where the builder owns two of three is worth more than a flattering
> one** — the whole value of counting is that the number can be compared with EP16's, and
> a count that quietly excludes the counter's own mistakes cannot be.
> ⚖️ **AND NONE OF THE THREE IS A RECURRENCE OF EP16's SIXTEEN.** #2, #3, #4, #9 and #10
> were all passed without firing, including #4's layout collision, which none of this
> week's work touched.

### ⚰️ WHAT THE REGRESSION DID TO AN OLD NUMBER — worth more than the fix
**EP15 went 91.1 → 95.9 and EP16 went 87.8 → 96.3.** So **every episode has been
UNDER-MEASURED since the matcher was written.** Two consequences, both of which change how
something already written down should be read:
- **EP16's 87.8% was called "the narrowest pass on record"** and used as evidence for the
  low-bitrate hypothesis. **It was neither narrow nor about bitrate** — it was a
  figure-dense episode measured by an instrument that could not see figures.
- **EP15's truncated master at 62.9% was a MORE decisive catch than anyone knew.** The
  honest comparison is against **~96, not ~88** — a 33-point gap, not a 25-point one.

**EP16's #2, #3, #4, #9 and #10 have all now been PASSED WITHOUT RECURRING** — including
#4, the layout collision, which this work never touched. `cards_render` completed with
15 pages, `check_page_images` clean, autofit fitting one page.



**EP17 is at the words gate.** Nothing has been claimed, nothing spent. Halts get counted
here from the LOG as they happen, individually, never from memory.

## 🔴 THE EP16 BASELINE — SETTLED 6 Aug 2026. **IT IS SIXTEEN.**

**Four, eight and nine were all in circulation.** Jodie's account of where they came
from: *"I counted eight partway through EP16's evening and kept saying eight while more
halts happened."* **None of the three was picked. They were counted.**

> ### THE CRITERION, STATED SO THE NUMBER MEANS SOMETHING
> **An `EngineFlag` that STOPPED THE BUILD and REQUIRED A HUMAN TO CLEAR IT** — which in
> the log is exactly the `!! NEEDS A LOOK [step]:` line.
> **NOT counted:** stale-code engine exits (2 on 5 Aug) and dead-zone recoveries.
> *Nothing waited on a human, so they cost time, not a gate.*
> **Every RAISE counted separately, including a second raise of the same step**, because
> each one separately stopped the build and separately needed a human.

**Counted from `engine/logs/engine-2026-08-05.log`. EP16's whole build was that one day —
the 4 Aug log holds only PP-EP99, the 6 Aug log holds no flags at all.**

| # | time | step | what | kind |
|---|---|---|---|---|
| 1 | 07:07:11 | `audit_inputs` | E26: *"the whole `build.leads` block is absent"* — **false positive; the fix was on disk and the running engine held stale code** | machine |
| 2 | 07:27:31 | `cards_render` | card **schema + job** faults | machine |
| 3 | 07:38:08 | `cards_render` | **trace gaps** — figures with no source sentence | machine |
| 4 | 07:41:52 | `cards_render` | **layout collision** (C8, C10) | machine |
| 5 | 08:14:20 | `cards_render` | *"Have a look at the title card"* | **human gate, by design** |
| 6 | 08:30:51 | `heygen_download` | download stopped early — server said 127,387,672 bytes | machine/external |
| 7 | 08:57:26 | `heygen_download` | **same short object, second time** | machine/external |
| 8 | 09:28:42 | `heygen_download` | audio **124 kbps** vs the 180 floor → **ruling A3** | machine/external |
| 9 | 09:44:16 | `shot_map` | **2 cues not in the SRT** (C1, C9) **+ 3 b-roll/card overlaps** | machine |
| 10 | 10:32:33 | `ebook_pdf` | capture has **no `ARTICLE TEXT` markers** | machine |
| 11 | 10:38:36 | `ebook_pdf` | a figure `src` was `table-1.jpg`, must be `figure-N.png` | machine |
| 12 | 10:47:31 | `thumbnail` | *"Have a look at the thumbnail"* | **human gate, by design** |
| 13 | 11:02:36 | `thumbnail` | `thumbnail.part 'Part 2'` not in the approved `ebook_title` | machine |
| 14 | 11:22:59 | `cards_render` | *"Have a look at the title card"* — **again, after the rename re-render** | **human gate, by design** |
| 15 | 11:53:01 | `youtube_copy` | the machine needs an **AUTHOR**, not an operator | author gap |
| 16 | 11:54:04 | `youtube_copy` | same, second raise | author gap |

> ## **16 = 11 MACHINE FAULTS · 3 DESIGNED HUMAN GATES · 2 AUTHOR GAP.**

### 🔴 AND THE CLAIM EP17 IS TESTING GETS SMALLER WHEN THE DENOMINATOR IS REAL
**"Five of EP16's eight halts should simply not occur"** was carried into today. Checked
against the sixteen, against what actually landed on 6 August:

| halt | prevented by | verdict |
|---|---|---|
| **#2** schema/job | `preflight_cards` → `author_cards.validate()` | ✅ **fully** |
| **#3** trace gaps | `preflight_cards` → `check_trace()` | ✅ **fully** |
| **#10** missing markers | `preflight_cards.capture_faults()` | ✅ **fully** |
| **#9** shot_map | the **cue** half yes; the **three overlaps** no — that check needs the SRT and only WARNS | ⚠️ **half** |

**Everything else is untouched**: #4's layout still runs at `cards_render`
(`layout_is_not_here()`), the three downloads, the thumbnail, both human gates, both
author-gap halts, and #1's stale code.

> ### SO THE HONEST CLAIM IS **THREE OF SIXTEEN FULLY, PLUS HALF OF A FOURTH** —
> ### not five of eight.
> **The "five" was roughly right and the denominator was twice as big as anyone said.**
> ⚠️ **And the `--force` fix (`696d303`) prevents NO halt at all.** It stops a correct fix
> from looking like a failed one — **which cost time BETWEEN halts, not a halt.** *Counting
> it as one would have been the same error in the other direction.*

---

# 2. THE ENCODING SCARE — CORRECTED. **THE PAGE IS CLEAN.**

A previous session recorded that this source page *"declares UTF-8 and serves bytes that
are not valid UTF-8"*, with apostrophes arriving as replacement characters — `we?ll`,
`hasn?t` — and cp1252 failing on byte `0x9d`. **It was carried into this session as an
established measurement not to be re-derived.**

> ### IT IS WRONG, AND THE TWO OBSERVATIONS BEHIND IT WERE BOTH REAL.
> **Measured off the wire, 6 Aug 2026: 104,214 bytes, `decode("utf-8")` succeeds.**
> Twenty proper `U+2019` apostrophes, two `U+2013` en dashes, two pairs of curly quotes.

**The corruption was in the READING.** A Windows console encodes its output as cp1252,
which has no `U+2019`, so a **correctly decoded** curly apostrophe **prints** as `?`. And
*"cp1252 fails on 0x9d"* is the same fact from the other side: `0x9d` is undefined in
cp1252 **precisely because these bytes are UTF-8**, where it is the third byte of `U+201D`.

✅ **THE SAME FAULT REPRODUCED ON PURPOSE THIS SESSION**, which is what settles it: a
`python -c` printing EP16's `episode.json` died with
`UnicodeEncodeError: 'charmap' codec can't encode characters in position 491-492`. **Same
console, same cause, a file nobody suspects of being corrupt.**

> ### WHY IT MATTERED ENOUGH TO WRITE DOWN
> **"Decode this site carefully" would have been carried forward into every future
> capture as a property of the SITE.** It is a property of the terminal. The instruction
> would have been followed forever, cost real care every episode, and protected nothing.
> *Fault #6: a wrong cause is worse than no cause, because the next action appears to fix
> it.*

---

# 3. WHAT THE ARTICLE IS, AND WHAT IS WRONG WITH IT

**24 body paragraphs. Zero `<table>` elements — every figure runs as prose inside a
sentence.** EP16's scanned-table problem does not arise; `ebook.source_figures` is `[]`.
All 74 `<img>` on the page are site furniture.

**Six data sets, all recomputed from the article's own strikes, rates and dividends at a
dollar a unit.** They reconcile nearly everywhere — number seven under the
two-to-three-dollar filter is published at a $108.10 loss, 50 per cent, and computes to
$106.29, 49.6 per cent.

## 🔴 TWO FIGURES CANNOT BE MADE TO WORK. BOTH CATEGORY 3. BOTH STAND.

**1. NON-METRO, NUMBER NINE: 48 wins at a 7 per cent strike rate** — that implies **686
runs in a sample of 356 races**. Its neighbours (8 → 20 wins at 7%, 10 → 17 at 6%) put the
real figure near 20, **but nothing forces ONE value**, so it is not category 2.
**Not spoken: Gordon does not recite that list at all.**

**2. FAVOURITE $2–$3, NUMBER SIX: "a profit of $32.80 or 12.5 per cent"** — the published
strike (28), rate (12%) and dividend ($7.20) give a **LOSS of $31.73, 13.6 per cent**: the
same magnitude, opposite sign. **And the article's own summing-up agrees with the
arithmetic rather than with itself** — paragraph 19 names only number four for this
filter and drops number six, which paragraph 10 had called "the better one".
> ### 🔒 RULED BY JODIE, 6 Aug 2026 — NOT SPOKEN. **Now `PP-STANDARDS` §0a-ii.**
> **A figure the source's own arithmetic contradicts is REPRODUCED, NOT VOICED**, because
> *Dave can check it* and a number that does not survive a calculator turns Mr Money's
> error into ours on delivery. It stands verbatim in the e-book with the discrepancy
> disclosed.
> ⚠️ **AND THE CONSTRAINT THAT DECIDED THE WORDING: omission must not change the finding.**
> Paragraph 10 ENUMERATES — *"only two of the numbers were profitable"*, then names six and
> four. **Naming four and quietly dropping six would make the video claim something
> different from the article, silently.** That is worse than speaking the bad figure.
> **SO BEAT 10 NAMES NO WINNERS AT ALL** — *"I'm going to leave that cut's figures on the
> page rather than read them at you. They are all in the e-book, set out in full."* — and
> keeps number seven's loss, which computes to 49.6% against the published 50%.
> **The later summing-up beat is the ARTICLE'S OWN summing-up**, which names only number
> four; four's figure survives a calculator (+8.0% computed against +5% published).

⚖️ **NEITHER IS A DEPARTURE. `ebook.departures` is `[]`** — nothing was repaired.
**Not voicing a figure is a SELECTION, never a departure.**

## THREE STRAY `?` GLYPHS — CATEGORY 1, REPRODUCED
Literal `0x3f` bytes in the source at `?In the following figures`, `?Next, we'll take`,
and `seemed ?to be`. **A reader recovers all three unaided, which is the whole of the
category-1 test, so they STAND.** *Category 2 is the narrow one and must stay narrow.*
The fourth — *"Number seven? Forget about it!"* — is Mr Money's own punctuation and his
closing joke. **Never tidy it.**

---

# 4. THE SCRIPT — WRITTEN, PROVED, AND ON THE RAIL

| | |
|---|---|
| capture | `PP Videos/docs/EP17-source-article-testing-the-numbers.md`, 12,759 bytes |
| script | **22 beats · ~1,500 spoken words · ~10 min at 150 wpm** |
| `render_ready` | **✓ RENDER-READY** — no bare numerals, no odd characters |
| midroll | **L7** (17 mod 10), verbatim, **~55% in** (target 45–55%), fresh vs EP08–EP16 |
| home | **`script_snapshot` on the rail** — 10,837 chars, sha `c40f2155a17b`. **No Doc.** |

**THE EDITORIAL DECISION THAT SHAPES THIS EPISODE: Gordon never reads a list of ten
numbers aloud** (§4I). This article is *mostly* lists — six of them — so the spoken track
states each set's one takeaway and the numbers live on the cards and in the e-book. **That
is why 24 article paragraphs become 22 beats and not 34.**

**Fidelity pass run beat-by-beat**, number-words folded out of both sides so a figure
written as `98` on one side and `ninety-eight` on the other does not score as invented
prose. **Sixteen of eighteen body beats sit at 62–100% article vocabulary.** The two
lowest are beat 6 (29%) and beats 7/17 (57%), and the reason is nameable: **their source
paragraphs are almost entirely digits**, so what remains to lift is a handful of words.
*Beat 6 carries the least of the article's own vocabulary of any beat in the episode.*

---

# 5. 🏁 THERE IS NO DOC. EP17 IS THE FIRST EPISODE WHOSE SCRIPT LIVES ON THE RAIL.

**Ruling A5 executed, mid-episode, commit `4780e42`.** The script is
`script_snapshot` on the rail — **10,837 chars, sha `c40f2155a17b`**, seated and read
back byte-identical, and `fetch_script` on the real EP17 row returns it from
*"the script box on the board"*.

### WHY IT MOVED TODAY RATHER THAN AFTER EP17
**Jodie had just done the manual share for the third episode running — and that share was
already stale.** Beat 10 changed when she ruled on number six, and **the Drive connector
has `create` but no `update`, `delete` or `rename`.** So the only alternative was a
**second Doc and a fourth manual share on the same episode**.

> ### ⚠️ THE ADVICE I HAD DRAFTED WAS THE OPPOSITE — *"she's already shared it, so this
> ### buys EP17 nothing"* — AND IT WAS WRONG BECAUSE I HAD NOT CHECKED THE DOC'S CONTENT.
> One `verify_doc.py` run turned the recommendation over. **The share worked (HTTP 200,
> clean text) and the words in it were superseded.**
> *A second, smaller find pointing the same way: the Doc does **not** round-trip
> byte-identically — Google's paragraph conversion inserts blank lines between every beat.
> Harmless (`strip_notes_header` filters them) but it means the approved snapshot was never
> exactly what was written. From the rail it is.*

### WHAT DID **NOT** CHANGE — the two that matter most
- **`assert_script_gate` is untouched.** It checks `title_approved` and `script_read` and
  has never mentioned the Doc. **A test now fails if it ever acquires an opinion about
  where the script lives.**
- **A Doc still wins whenever one exists.** EP01–EP16 read their Docs exactly as before;
  the Doc branch is byte-for-byte unchanged. **Not a migration** — old episodes keep their
  transport, new ones never acquire one.

### 🔒 AND THE GATE DID NOT WEAKEN, WHICH WAS THE POINT
**The board now shows the script itself, read-only, in the words card.** A tick saying
*"I've read the script"* against nothing on screen is a gutted gate dressed up as a moved
file. The tick is enabled when there is something **to read** — a Doc to open, or the words
in front of her — and never otherwise.
**It is a `<pre>`, not a textarea**, which is the whole safety argument for landing it
beside an unproven slice 1: *not an input*, so `harvestDrafts`/`restoreDrafts` and the 30s
refresh pause cannot see it, and the fields below behave exactly as they did. **Editing
there is slice 4.** A test fails if a textarea appears.

**17 cases, one section per constraint, PROVED BY MUTATION** — rail-beats-Doc, no
`spoken-words.txt` write, and an always-enabled tick each turn the suite red. **20/20
engine suites green.** Engine confirmed fresh from the log: `pid=79844`, started 17:49:20,
every watched `.py` older than the process.

## 5b. ⏸ WHAT JODIE DOES AT THE GATE
1. **Read the script** — it is on the card, no link to open, nothing to share.
2. **Fix the title**: the box reads **"Testing The Numbers"**; the house form is
   **"Testing the Numbers"**. Set hook `TESTING THE NUMBERS`, byline
   `The stats tell the story`.
3. **Tick "I've read the script"**, then approve.

**The fields are still hers to type** — EP17's words gate is the one observation editor
slice 1 is waiting on: she types, alt-tabs away, comes back and presses **ctrl+Z once**.
Writing them from here would remove the only chance to see it.

⚠️ **THE OLD DOC IS SUPERSEDED AND STILL EXISTS** in `PP-EP17/`. It holds the pre-ruling
beat 10. **Nothing reads it** — `script_doc_url` is NULL and the board no longer offers a
Doc field for a rail episode, so it cannot be linked by accident. **Deleting it is Jodie's
(A13).**

⚠️ **The board's title box reads "Testing The Numbers" with a capital T, which is WRONG.**
The article's headline is *TESTING THE NUMBERS*; the house form is **"Testing the
Numbers"**. **Jodie corrects it by hand at the gate.** The cause is recorded in
`HANDOVER.md` — `slugToTitle()` builds the name from the URL — and is deliberately not
fixed today.

---

# 6. WHAT IS NOT DONE

**`episode.json` does not exist yet** — cards, b-roll prompts, figures and `ebook/body.html`
are the next block of work, and **§9a says the card validators run the moment it is
written**, before the ticket goes anywhere. Nothing below the words gate can start until
the packaging is approved.
