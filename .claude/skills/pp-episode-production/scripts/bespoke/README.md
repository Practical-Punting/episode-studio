# Bespoke card authoring — the last resort, and what now stands behind it

> ## ⚠️ FIRST: ASK WHETHER IT HAS TO BE BESPOKE AT ALL (16 Aug 2026)
> The two cards that made this folder necessary **are not bespoke any more.**
> * **A big TABLE is a `ladder` card** — five to seven anchor rows lifted from the
>   article's own table, the full chart staying in the e-book. *The video tells the
>   table's STORY; the data lives in the book.*
> * **A long LIST is a `checklist`** — it holds twelve now, and it resizes itself
>   rather than halting.
>
> Both are **generated**, so both get the schema, the job check, the trace gate and the
> invented-text gate. A page you write by hand gets none of those. **Reach for this
> folder only when no block can carry the card**, and expect to justify it.

A card with `block: "bespoke"` is **skipped entirely by `author_cards.py`**. There is no
trace gate, no invented-text gate, no schema and no card vocabulary behind it. It is the
one kind of card where a wrong number can reach the screen with nothing in its way.

**Two things changed on 16 Aug 2026, and they are the reason this is now survivable:**

1. **The ask comes at PLAN time, and it names every page at once.** `audit_inputs`
   raises ONE flag listing every bespoke page a human must write, before a credit
   moves — instead of `cards_render` halting on "C15 has no clip", then on C17.
2. **A page that stays bespoke is graded on the finished artefact.** Every figure on
   it must appear in the capture, and every word must come from the capture, the
   standing frame, or the card's own approved fields in episode.json. A studio line
   the article does not contain — *"the full chart is in the guide"* — is legitimate,
   and it belongs in the card's `content` where a human reviews it, or in
   `bespoke_licence` with its reason. **What must not exist is a sentence that lives
   only on a page nobody re-derives.**

> **So the data on a bespoke page is LIFTED FROM THE CAPTURE PROGRAMMATICALLY AND
> ASSERTED AGAINST IT, never typed.** (Jodie, 15 Aug 2026 — *"a number is a READING, not
> a value"*. Written about the e-book; it binds here for the same reason and with less
> protection.)

That is what these scripts are. One authors the pages, one reads the finished pages back
and prints every visible string beside the source it came from, so a human can check the
two side by side. **They are committed because they are the only audit trail an
ungated page has** — the page itself is on the Drive with the episode, and a page nobody
can re-derive is a page nobody can check.

## Per episode

| script | what it does |
|---|---|
| `author_ep27_bespoke.py` | EP27 C15 (the conversion ladder) and C17 (the ten questions) |
| `verify_ep27_bespoke.py` | reads both rendered pages back and checks every cell and item against the capture |

Run the author, render with `render_cards_batch.py`, then run the verifier and **look at
the frames**. `card_check.py` does not see these pages either, so the collision it would
have caught is yours to catch: EP27 C15's first draft overflowed its row and put "50.0"
into the descenders of the headline, and only a rendered frame showed it.

## The house frame

Both pages are built from `assets/cards/frame-fullscreen.html` by substitution, so the
eyebrow, headline, logo, fonts, colours and animation contract are the standing ones and
cannot drift from the generated cards around them. A bespoke page still has to expose
`window.ppDuration` (via `ppInit`) or `render_cards_batch.py` skips it.
