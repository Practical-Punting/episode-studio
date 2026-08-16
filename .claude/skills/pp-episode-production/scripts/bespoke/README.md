# Bespoke card authoring — the pages nothing else checks

A card with `block: "bespoke"` is **skipped entirely by `author_cards.py`**. There is no
trace gate, no invented-text gate, no schema and no card vocabulary behind it. It is the
one kind of card where a wrong number can reach the screen with nothing in its way.

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
