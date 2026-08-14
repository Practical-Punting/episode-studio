#!/usr/bin/env python3
"""card_hold.py — the shortest a card may be held, SCALED to what it asks you to read.

🔴 WHY THIS EXISTS. `min_card_hold` was one flat number — 10.0s for every card in the
episode, whether it carried four rows of a table or a single figure. EP21 C19 is two
rows of a two-column table and the payoff beat it belongs on can only give it 8.64s, so
a card that takes about five seconds to read halted the build on a floor set for a card
more than twice its size. Jodie, 12 Aug 2026: *"a two-row card is about half the reading
of the four-row original, so 8.6s is plenty — the blanket 10s is over-conservative for a
light card."*

    A FLOOR THAT IGNORES THE CONTENT IS A FLOOR THAT IS WRONG FOR MOST CARDS.

⚠️ THREE PLACES ENFORCED IT AND THEY ALL HAD THEIR OWN COPY — `derive_card_timings`
checked it, `assemble_episode` CLAMPED the hold up to it, and `qc_episode` did both. So
lowering it in one place would have let the shot map plan 8.6s while the assembler built
10.0s and put the card back over the end card, in the finished video, with every check
passing. That is the one-value-in-two-places fault this repo keeps paying for, so the
rule lives HERE and all three import it.

CALIBRATED TO THE NUMBER ALREADY IN USE, NOT INVENTED. The blanket 10.0s was chosen for
a card of about four items, and `BASE + PER_ITEM * 4` reproduces it exactly. So a
four-row card is held for precisely as long as it always was; only lighter cards gain.

    2 rows -> 8.0s      3 rows -> 9.0s      4 rows -> 10.0s      5+ -> the blanket

🔒 AND IT NEVER GOES BELOW `ABSOLUTE_FLOOR_S`, whatever the arithmetic says. A card is
a thing a person has to find, read and believe; there is a length below which that is
not possible no matter how little is on it.
"""
from __future__ import annotations

BASE_S = 6.0            # finding the card, taking in its headline, looking away
PER_ITEM_S = 1.0        # each row / step / bar / chip the eye has to take in
ABSOLUTE_FLOOR_S = 7.0  # never less, however light the card (Jodie's guardrail)


def reading_load(card: dict) -> int:
    """How many things this card asks the eye to take in.

    ⚠️ NOT simply the longest list. `columns` is a list too — a matrix card's HEADER —
    and counting it made C19 read as three items because it has three column headings
    over two rows. The header is read once on the way in; it is not a row of data.

    The rule, which holds for all ten blocks without naming one of them: an ITEM is a
    dict (a row, step, bar, chip, cell, slot, mark, col — each carries a label and its
    values), a HEADER is a list of bare strings. So take the longest list of dicts, and
    fall back to strings only when there are NO dicts at all — which is `checklist`,
    whose plain-string `items` genuinely are the reading load.

    A card with no list at all (a stat, a statement, a price) is ONE thing, not zero.
    """
    content = card.get("content") or {}
    if not isinstance(content, dict):
        return 1
    lists = [v for v in content.values() if isinstance(v, list)]
    items = [v for v in lists if any(isinstance(x, dict) for x in v)]
    pool = items or lists          # strings only count when nothing structured is there
    return max(1, max((len(v) for v in pool), default=0))


def min_hold_for(card: dict, build: dict) -> float:
    """The shortest this card may be held, in seconds.

    `build.min_card_hold` stays the ceiling: a heavy card is held for exactly as long
    as it always was, and an episode that sets no floor still has none.
    """
    blanket = float((build or {}).get("min_card_hold", 0.0) or 0.0)
    if blanket <= 0:
        return 0.0                      # this episode asks for no floor at all
    scaled = BASE_S + PER_ITEM_S * reading_load(card)
    return round(min(max(scaled, min(ABSOLUTE_FLOOR_S, blanket)), blanket), 2)


def options_for(card: dict, build: dict, available: float) -> str:
    """The ways this card could be made to fit `available` seconds, in plain English.

    🔴 WHY THIS EXISTS. The halt used to say a card "is too big for its beat" and stop.
    Every time — EP21 C18/C19, EP22 C18/C19 — a person then did the same arithmetic by
    hand: what window does it actually have, what does it need at its current size,
    what would it need if a row came out, and is it even possible. That is three
    numbers the tool already holds. Handing over the question without the numbers is
    what turned a two-minute decision into a full round trip.

    The lever is the READING LOAD, not the prose: the minimum scales at
    BASE + PER_ITEM x items, so folding a row out is what shortens the card. Tightening
    words changes how it LOOKS, never how long it must be held.
    """
    n = reading_load(card)
    need = min_hold_for(card, build)
    if need <= available:
        return f"it already fits — needs {need:.1f}s and has {available:.2f}s"
    lines = [f"it has {available:.2f}s and needs {need:.1f}s at {n} item(s) — "
             f"over by {need - available:.2f}s"]
    # the largest content this window WOULD take
    fits = [k for k in range(1, n)
            if min_hold_for({"content": {"rows": [None] * k}}, build) <= available]
    if fits:
        k = max(fits)
        got = min_hold_for({"content": {"rows": [None] * k}}, build)
        lines.append(f"FOLD to {k} item(s) and it fits ({got:.1f}s) — fold a row into "
                     f"its parent, never drop the fact")
        lines.append(f"or SPLIT it: {k} item(s) here and the rest on another cue")
        # 🔴 SAY WHICH HALF IS ACTUALLY BEING ASKED FOR. (EP25 C26, 14 Aug 2026.)
        # This message used to leave a person with TWO jobs and name only one: fold the
        # card, AND remember that folding lowers the floor without moving the planned
        # hold, so `build.holds` needs the new number too. A human who did the first and
        # not the second got the identical halt back and no clue why. The second half is
        # arithmetic and is applied automatically now, so the ask is one decision.
        lines.append(f"the ONLY thing needed from you is WHICH row folds into which — "
                     f"that changes what the card says, so it stays yours. The hold "
                     f"then comes down to {got:.1f}s by itself; you do not have to set "
                     f"build.holds, and nothing is dropped either way")
    else:
        lines.append(f"NOTHING FITS THIS WINDOW: even one item needs "
                     f"{ABSOLUTE_FLOOR_S:.1f}s and there are only {available:.2f}s, so "
                     f"tightening and splitting BOTH fail — this card has to move to a "
                     f"window with at least {ABSOLUTE_FLOOR_S:.1f}s, or come out")
    return "; ".join(lines)


def why(card: dict, build: dict) -> str:
    """One line for a run log or a halt, so the number is never a bare assertion."""
    n = reading_load(card)
    return (f"{min_hold_for(card, build):.1f}s minimum for {n} item(s) "
            f"({BASE_S:.0f}s to find and read it, {PER_ITEM_S:.0f}s each, "
            f"capped at the episode's {float((build or {}).get('min_card_hold', 0) or 0):.1f}s)")
