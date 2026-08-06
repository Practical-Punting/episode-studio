# EP17 — run log

**Started 6 August 2026.** *Where EP17 is · what was decided · what is waiting on a human.*

> **THE EPISODE:** *Testing the Numbers*, byline *The stats tell the story*.
> **Mr Money**, **Practical Punting, JANUARY 2007.** Not a numbered part — the article
> refers back to an earlier instalment on favouritism but carries no part line.
> Rail id `043682b8-7253-44bf-81d5-96e7b04e9fc0` · `ep_number` 17.

---

# 1. THE HALT TALLY — **ZERO SO FAR. THE BUILD HAS NOT STARTED.**

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
**Gordon speaks it as printed** (§0a: reproduce, do not improve) **and the video's
summing-up uses the article's own summing-up.**

⚖️ **NEITHER IS A DEPARTURE. `ebook.departures` is `[]`** — nothing was repaired.

## THREE STRAY `?` GLYPHS — CATEGORY 1, REPRODUCED
Literal `0x3f` bytes in the source at `?In the following figures`, `?Next, we'll take`,
and `seemed ?to be`. **A reader recovers all three unaided, which is the whole of the
category-1 test, so they STAND.** *Category 2 is the narrow one and must stay narrow.*
The fourth — *"Number seven? Forget about it!"* — is Mr Money's own punctuation and his
closing joke. **Never tidy it.**

---

# 4. THE SCRIPT — WRITTEN, PROVED, AND IN A DOC

| | |
|---|---|
| capture | `PP Videos/docs/EP17-source-article-testing-the-numbers.md`, 12,759 bytes |
| script | **22 beats · 1,508 spoken words · ~10 min at 150 wpm** |
| `render_ready` | **✓ RENDER-READY** — no bare numerals, no odd characters |
| midroll | **L7** (17 mod 10), verbatim, **54.9% in** (target 45–55%), fresh vs EP08–EP16 |
| Doc | `1N6RM2gmDh23OxMV4jGHOVDdp6tD5YBJPGOGXqKVojQk` |

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

# 5. ⏸ WAITING ON A HUMAN — TWO THINGS, AND ONE OF THEM IS A REAL LIMITATION

## 5a. 🔴 THE DOC IS NOT SHARED, AND THE MACHINE CANNOT SHARE IT
**Measured, not assumed:** the export URL the engine reads returns **HTTP 401**, and
`get_file_permissions` shows only `jlralph` (owner) and `hugh` (writer, inherited from the
folder). **There is no "anyone with the link" permission.**

> **The Drive connector has `get_file_permissions` and NO tool that SETS them.** This is
> exactly what ruling A5 records: *"the machine can create a Doc and physically cannot
> share it."* **It is a worked example of A5's own argument for moving the script onto the
> rail**, met on the first episode after the ruling.

⚠️ **SO THE DOC'S CONTENT IS NOT YET VERIFIED THROUGH THE ENGINE'S CHANNEL, AND IS NOT
CLAIMED TO BE.** It was verified through the Drive API instead, which markdown-escapes
(`\#` on every header line — the 4 Aug finding, reproduced here). **Every spoken paragraph
is present and correct and none carries an escape**, but the byte-level diff against the
proven local file **cannot run until the Doc is shared**. *A check that could not run is
not a check that passed.*

## 5b. THE WORDS GATE ITSELF — Jodie pastes, deliberately
The link and the packaging are **hers to paste**, not mine to write to the rail. **That is
the point:** EP17's words gate is the one observation editor slice 1 is waiting on — she
types, alt-tabs away, comes back and presses **ctrl+Z once**. Writing the fields from here
would remove the only chance to see it.

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
