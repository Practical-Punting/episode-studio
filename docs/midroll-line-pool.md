# Midroll line pool — the ten approved spoken invitations

**Why this exists:** so the midroll invitation is never invented, never rewritten, and
never repeats itself anywhere near itself. Modelled on `broll-registry.md`, which exists
for the same reason: **a rule nobody can check is a rule that gets broken.**

**🔒 APPROVED AS A BATCH by Jodie, 28 July 2026.** These ten lines are **never rewritten.**
Changing any one of them is a **new batch approval**, not an edit.

---

## THE RULE

1. **Ten lines, `L0` … `L9`. Used STRICTLY IN ORDER: episode N takes `L[N mod 10]`.**
   EP13 → `L3`. EP14 → `L4`. EP20 → `L0`. The pool **wraps forever** — it never exhausts,
   so the build never halts for want of a line.
2. **The build never invents, paraphrases or rewrites.** It substitutes one paragraph.
   If the pool cannot supply a line, that is a bug, not a licence to write one.
3. **`episode.json` records the choice:** `build.midroll.line_id: "L3"`.
4. **Add a row to the registry below after the episode ships.**
5. **HARD FAIL if the midroll paragraph is byte-identical to that of any of the NINE
   immediately preceding episodes.** Enforced in `render_ready.py` (pre-render) and
   `qc_episode.py` (post-assembly).

### ⚠️ WHY THE WINDOW IS NINE AND NOT TEN — do not "correct" this
A pool of exactly ten used in strict order **recurs at exactly ten-episode intervals**:
`L3` runs at EP13 and again at EP23. If the window were *"the last 10 episodes"*, EP23's
window would be EP13–EP22 — **which contains EP13** — and the guard would hard-fail every
episode from EP23 onward, forever. At **nine**, the nearest legitimate prior use is always
exactly ten back and passes; any accidental duplication closer than that fails, which is
precisely the intent.

The check orders episodes by the number parsed from `PP-EP(\d+)`, **numerically, never by
file mtime** — `PP-EP98/` exists on disk and mtime ordering would drag it into every
window.

---

## THE FIXED SHAPE (PP-STANDARDS §Mid-video)

Every line hits it, in order:

**soft value hook (naming the video) → the ask (a like helps OTHERS find it; subscribe) →
the cadence line → a light wry nod → return to content.**

Warm, plain, wry, Australian, spoken to one person. No hype, no promises, no urgency, no
"smash that like button".

### Constraints every line satisfies
- **Names the episode as "this video"**, never a bare "this" — PP-STANDARDS §Mid-video,
  *name the video at every ask*. Once per line in the value hook, plus `L4` and `L7` where
  a later bare "this" also plainly means the episode. **Deliberately not more than that**
  (Jodie, 28 Jul 2026: *"your density judgement is right… don't add more"*) — five
  instances in eighty words reads as a machine filling a slot.
- **No bare numerals.** Every number is a word (`render_ready.py` hard-fails digits).
- **No characters outside the safe set** (ASCII + curly quotes, en/em dash, ellipsis).
- **Zero em dashes**, by choice (Jodie, 28 Jul 2026: *"no em dashes needed; leave them as
  they are"*).
- **The wry nod is varied across the ten** — a crowded paddock, a good suit, loud
  opinions, people who have it all worked out — because leaning on the same nod every
  time is the thing the old rule warned against.
- **None reuses EP11's or EP12's shipped wording**, or the three examples that used to sit
  in PP-STANDARDS §Mid-video.

### ⚠️ THE CADENCE IS BAKED IN
**All ten carry the DAILY cadence** ("a fresh one every day at the moment, weekly further
down the track"). **When the cadence actually moves to weekly, all ten go stale at once
and need a fresh batch approval.** That is the accepted cost of freezing the wording
(design doc §8f). It is not something to fix line-by-line.

---

## THE TEN LINES

### L0
> Quick word before we push on. If this video is earning its keep for you, a like is about the cheapest favour you can do somebody else who's after the same thing. There's a fresh one every day at the moment, weekly further down the track, so a subscribe saves you going looking. Racing's never short of loud opinions. I'd rather the careful ones found the people who want them. Right, where were we.

### L1
> Hold on a tick. If you're getting value out of this video, a like helps it find the next bloke doing the same homework you are. We're going out daily just now, weekly later on, so subscribe and they'll turn up without you chasing them. There's a lot of shouting in this caper. The quiet stuff deserves a hearing too, and it doesn't get one on its own. Anyway, on we go.

### L2
> One small thing, then we'll get back to it. If this video has done you any good, a like nudges it toward somebody else who'd want it, which is the whole point. A new one lands every day for now, weekly in time, so subscribe and you won't have to hunt for them. Every second voice out there has a system. Not many of them have a method. Righto, back to the form.

### L3
> Before the next bit, one honest ask. If this video has been worth your while, a like is what puts it in front of the next person, and it costs you nothing at all. Daily for the moment, weekly down the road, so subscribe and they'll come to you. You could fill a week with people telling you they've cracked this game. I'd sooner the sensible stuff reached the folk after it. That's it, back to it.

### L4
> A short interruption, and I'll keep it short. If this video is helping, a like carries it a bit further than it would ever go on its own. There's one going up every day just now, weekly later, so a subscribe means you don't miss them. Half the noise about racing is somebody selling something. This video isn't, and I'd like the people who'd use it to be the ones who find it. Enough of that, where were we.

### L5
> Just a moment before we carry on. If you've found something in this video worth having, a like is how the next person stumbles across it, and that's how these things travel. Fresh one daily at the moment, weekly a bit further on, so subscribe and they'll keep arriving. It's a crowded paddock out there. Most of what's in it is confidence rather than form study. Now then, back to the horses.

### L6
> Pause there a second. If this video has been worth your time so far, a like tells the thing to show it to somebody else like you, which is all I'd ask of you. New ones go out every day for now, weekly down the track, so subscribe and you'll not have to look. There's more confidence about this game than there is homework. I know which of the two I'd trust. Right you are. Where were we.

### L7
> Small detour, then we're done with it. If this video is landing for you, a like sends it out to the folk it was made for. We're daily just now, weekly in time, so subscribe and the next one finds you. Plenty of tips flying about, most of them somebody's guess in a good suit. This video is just a bloke reading the form. Done, let's get on.

> #### ✏️ AMENDED TWICE BY JODIE, 6 August 2026 — at EP17's words gate, the line's FIRST USE.
> **BOTH REMOVED FRAGMENTS, verbatim, so neither can be restored from an older copy:**
> | # | removed | replaced with |
> |---|---|---|
> | 1 | *"…, and it does more for them than it ever does for me."* | *(nothing — the sentence closes at "made for.")* |
> | 2 | *"…so subscribe and they'll find you instead."* | *"…so subscribe and the next one finds you."* |
>
> **HER OBJECTION TO THE SECOND, which is the useful part:**
> > *"the bit that says 'and they'll find you instead' does not make sense at all."*
> **She is right. "They" points back to "the folk it was made for"**, so it reads as the
> AUDIENCE coming to find her. **The line meant the VIDEOS would turn up on their own, and
> never said so.**
>
> Nothing else in L7 moved. The fixed shape is intact: value hook naming the video → the
> ask → the cadence line → the wry nod → return to content.
>
> **WHY THE POOL WAS AMENDED AND NOT JUST THE EPISODE:**
> 1. **The midroll must be VERBATIM from the pool.** An EP17 that differed from L7 would
>    either fail `render_ready`'s freshness check or quietly weaken it.
> 2. **The pool wraps.** Left in, those words return at **EP27**, on an episode nobody is
>    watching for them. *She said she disliked them; she should not have to say it twice.*
>
> ⚠️ **An AMENDMENT to the batch approval, made by the person who gave it.** Rule 7 above
> says changing a line is a new batch approval rather than an edit — **the other nine lines
> are untouched and are NOT re-opened by this.**
>
> ## 🔴 AND THE FINDING THAT MATTERS MORE THAN THE LINE
> **L7 was wrong TWICE, and both faults were found by one person reading it IN PLACE for
> the first time.** It was batch-approved on 28 July; **EP17 is its first use. The other
> NINE HAVE ALL SHIPPED.**
>
> > ### A BATCH APPROVAL IS A LIST SOMEBODY APPROVED ONCE AND NOBODY HAS SINCE READ.
> > **Ten lines were waved through together, nine went to air, and the tenth turned out to
> > have two faults in it the moment a human met it. The approval covered the BATCH;
> > nothing covered the LINES.**
>
> 📋 **OWED, AFTER EP17 IS MOVING AND NOT BEFORE: READ THE OTHER NINE IN PLACE.** Two
> questions only, and **not** to re-open them:
> - **does every sentence PARSE** — no dangling "they", no pronoun pointing at the wrong
>   noun (that is fault 2 above, exactly);
> - **does each still describe reality** — **all ten carry the DAILY cadence**, a live
>   setting that will one day be wrong in **ten places at once**.
>
> ⚖️ **NOTHING PUBLISHED IS TOUCHED** (Jodie, 4 Aug 2026: *found retrospectively does not
> mean fixed retrospectively*). Anything broken is fixed **for future use** and logged.

### L8
> Two seconds, then we're back on it. If there's something in this video for you, a like puts it in somebody else's evening, and that's the only advertising it ever gets. There's a new one every day at present, weekly further along, so a subscribe keeps them coming. The loud stuff always travels fastest, and it's rarely the useful stuff, is it. That's my bit. Back to it.

### L9
> Before we get to the meat of it. If this video has been worth sitting through, a like helps somebody else find it who's been asking the same questions you have. Every day at the moment, weekly down the line, so subscribe and they'll turn up on their own. There's no end of people in this game who'll tell you they've got it all worked out. I'm not one of them. Good. Let's pick it up again.

---

## THE REGISTRY — which episode used which line

Add a row after the episode ships. `line_id` must match `episode.json →
build.midroll.line_id`.

| Ep | Line | Notes |
|---|---|---|
| EP01–EP12 | — | **Pre-pool.** Each midroll was written fresh under the old "reword every episode" rule. **Not retro-fitted** — those episodes are shipped or at the publish gate |
| EP13 | `L3` | first pool episode (13 mod 10 = 3) |

### The next few, for reference
`EP14 → L4` · `EP15 → L5` · `EP16 → L6` · `EP17 → L7` · `EP18 → L8` · `EP19 → L9` ·
`EP20 → L0` · `EP21 → L1` · `EP22 → L2` · `EP23 → L3` (the first legitimate repeat, ten
back, which is exactly why the window is nine).

---

## THE ON-SCREEN CHIP IS SEPARATE — and it does NOT rotate

The lower-third chip is **fixed standing furniture, identical every episode** (Jodie,
28 Jul 2026). It has no pool and no rotation. It lives in the production skill's `assets/`
and is copied byte-identical, like the end card and the warranty slide.

Standing wording:

> **Doing its job? Like & Subscribe**
> new episodes daily · Practical Punting

**Two rules in that file exist for a reason. Record the reason beside the value so neither
is tidied away:**

| Rule | Why |
|---|---|
| Chip background is **opaque `#121212`**, never a transparency | The card sits on a `#00FF00` chroma-key field. At 92% opacity the green showed **through** and the chip rendered dark **green**, not charcoal |
| Both icons are a **white glyph on a SOLID orange tile** (`rgba(218,83,44,0.95)`) | The like icon was once an orange thumb on a 16% orange wash — invisible at broadcast size |

*"new episodes daily" is a cadence variable baked into a standing asset. When cadence
moves to weekly it is a one-file edit — better than today, where it lived in each
episode's own chip.*
