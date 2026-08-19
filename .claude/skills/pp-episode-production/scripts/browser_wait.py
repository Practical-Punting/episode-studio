"""WAIT ON A CONDITION, NEVER ON A CLOCK.

⭐ THE LAW (19 Aug 2026, Jodie — written after the card pool made the machine busy):

    A SLEEP LONG ENOUGH ON AN IDLE MACHINE IS NOT LONG ENOUGH ON A BUSY ONE,
    AND IT FAILS SILENTLY. IN THE YARD, WAIT ON A CONDITION, NEVER A CLOCK.

⚠️ AND IT APPLIES TO **GATES** AS WELL AS TO OUTPUT — `card_check` is the case that
proves it. A late FONT gives a card in the wrong typeface: wrong, and visible to anyone
watching. A late **LAYOUT** gives a gate that measured the wrong thing, and that is one
of two worse outcomes:
  · a MISSED COLLISION — cards overlapping in the finished video, past a gate that said
    PASS; or
  · a FALSE HALT — a human interrupted for a card that was fine.
**Halts are unplanned visits, and visits are the throughput constraint.** *A gate that is
green or red by what else is running fails in the dangerous direction* — this is that.

🔴 WHY `wait_for_timeout(n)` IS THE WRONG TOOL AND A BIGGER `n` IS NOT THE FIX.
A fixed sleep is a bet that the browser will have finished in `n` milliseconds. The bet
was written on an idle machine. Batch 6 now runs FOUR Chromium shards at once, the Yard
will run several episodes at once, and Jodie runs a second studio on the same box — so
the bet gets worse exactly when the studio gets busier, and it loses SILENTLY: a card
measured mid-paint still produces a perfectly valid-looking verdict.

✅ WHAT TO WAIT ON INSTEAD. `requestAnimationFrame` fires before a paint; the SECOND one
therefore cannot run until the frame containing our change has been committed. That is
an event from the browser saying "it is on the screen", not a guess about how long that
takes — so it is correct at any load, and it returns as soon as it is true rather than
always costing the full sleep.
"""
from __future__ import annotations

# One rAF says "you are before the next paint"; the second cannot run until that paint
# has happened. Two is the smallest number that PROVES a frame went out.
_PAINTED = """() => new Promise(resolve =>
    requestAnimationFrame(() => requestAnimationFrame(() => resolve(true))))"""

# A hard ceiling, so a page that never paints fails loudly instead of hanging the build.
# ⚠️ THIS IS NOT THE OLD SLEEP IN DISGUISE. It is never waited out in the normal case —
# the promise resolves on the next frame, typically in single-digit milliseconds. It
# exists only so a broken page cannot stop an episode for ever.
PAINT_TIMEOUT_MS = 10_000


def wait_for_paint(page, timeout_ms: int = PAINT_TIMEOUT_MS) -> None:
    """Return once the browser has actually put the current DOM on the screen."""
    page.wait_for_function(_PAINTED, timeout=timeout_ms)


def wait_for_fonts_and_paint(page, timeout_ms: int = 60_000) -> None:
    """Return once webfonts are loaded AND a frame has been painted with them.

    `document.fonts.ready` resolves when the fonts are USABLE; it does not promise the
    page has been re-rendered with them. The paint wait is what closes that gap — which
    is the 120ms sleep this replaces, the one hazard left in the card capture after
    batch 6 sharded it.
    """
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=timeout_ms)
    page.evaluate("() => document.fonts.ready")
    wait_for_paint(page)
