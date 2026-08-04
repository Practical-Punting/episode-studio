# THE OPERATOR'S BOX — the picture, the question, the buttons. Nothing else.

**Board bug 7, second half. Jodie's ruling, 4 August 2026.**
**Ships with Bundle F (the ask card). Not a rewrite job for today — recorded so it is
not lost.**

---

## What happened

EP15's title-card flag asked a good question and was still unusable. Jodie:

> *"The description of the problem on the board is not very user (Hugh) friendly!
> But I am happy with this card."*

**The question itself was right** — *"are the horses framed well in the 16:9 window?"* is
a ten-second look anybody can answer, and it is exactly the kind of judgement that should
reach a human.

**What made it unusable was everything around it:**

| In the flag | Why it does not belong |
|---|---|
| a raw Supabase storage URL, as text | an address, not a picture |
| the path `docs/episode.json` | a file Hugh cannot open |
| `"title_card": {"hero_focus": "center 62%"}` | JSON, in a box for a person |
| "which is exactly what EP12 needed…" | another episode's history |
| a paragraph explaining the type size was measured, not chosen | reassurance about a part nobody asked about |

**Every line of that is true.** And every line of it is **the machine explaining itself
to its maintainer** in the one place reserved for the person doing the work.

---

## The rule

> # THE PICTURE · THE QUESTION · THE BUTTONS. NOTHING ELSE.

**Never, in the operator's box:**

- file paths or filenames
- JSON, field names, or code of any kind
- URLs as text — a picture is shown, not linked
- references to other episodes
- an explanation of the parts you are **not** asking about
- stack traces *(already banned — CLAUDE.md fault #6)*

> **If a sentence only makes sense to someone who has read the repo, it belongs in the
> run log, not the flag.**

The run log is not a lesser place. It is the right place: it is where a maintainer
looks, and the flag is where an operator looks. **They are different readers, and the
same text cannot serve both.**

---

## What the EP15 flag should have been

> **Have a look at the title card.**
> *[the picture]*
> **Are the horses framed well, and is every line of text clear of them?**
> **[ Looks right ]  [ Move the crop ]**

Everything else — the hero-focus value, the file it lives in, what EP12 needed, how the
type size was decided — goes to the run log.

---

---

## The same rule applied to CLOCKS (added 4 Aug 2026)

EP15's card, while Jodie was looking at it:

> **"Working for 15 hr 6 min · render cooking 12 hr 38 min"**

**The HeyGen render took about twenty minutes.** The board was counting wall-clock since
the episode was created at 18:04 the previous evening — **including Jodie asleep, and
including the title-card flag waiting for her all morning.**

**Two faults in one line:**

1. **It counts the wrong thing.** *Time spent waiting for a person is not time spent
   working.* A step that is flagged (`needs_look` true) is a human wait **whatever its
   budget says**, and so is a step whose budget is `None`. **Both must stop the clock.**
   *(Logged as E19. My own build watcher had the identical bug and raised a budget alarm
   on a step that was waiting for Jodie — one fault, two symptoms.)*
2. **"render cooking" is engine vocabulary.** **Hugh reads twelve hours of cooking and
   reasonably concludes something is broken.** Whatever the line becomes once it counts
   the right thing, it must say the plain version: **what is happening now, and roughly
   how long it has actually been doing it.**

---

## The principle behind it

**A halt is only cleared when the person standing in front of it can act without knowing
how the machine works.**

*Recorded because the failure was not that the words were wrong. It was that we fixed
the title card's PICTURE on the morning of 4 August and never read the WORDS printed
next to it — the same fault as everything else this week: the artefact a human actually
receives was never looked at.*

Related: `CLAUDE.md` faults #1 and #6 · Bundle F (the ask card) ·
`docs/PP-script-editor-REVIEW-4Aug.md`
