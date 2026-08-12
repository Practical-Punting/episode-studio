#!/usr/bin/env python3
"""framing.py — WHICH BEATS MUST BE WIDE, in one place, because a layout change decides it.

🔴 WHY THIS EXISTS. On 12 Aug 2026 C21 was changed from `fullscreen` to `panel-push` to
clear a logo collision. That change is what decides whether its beat may be MCU — and
nothing re-derived the framing. The next day beat 32 halted EP23 at the shot map, and
`_framing_note` still listed beat 32 among the beats that are MCU *because their card is
fullscreen*. THE FIX MADE THE HALT, and the prose that would have caught it had already
been overtaken by the very edit that broke it.

    A LAYOUT IS NOT A LOOK. IT IS A CLAIM ABOUT WHERE GORDON IS IN THE FRAME.

THE RULE (PP-STANDARDS, §Motion-graphic cards): while an ON-SCREEN (panel-push) card is
visible the shot must be WIDE for the WHOLE window, entry to exit, so Gordon can glide
aside into the freed third. On an MCU the panel lands on his face — the EP11 failure.
Full-screen cards are unaffected; the host is not in shot.

⚠️ THIS MODULE ANSWERS THE HALF THAT NEEDS NO AUDIO, AND SAYS SO. A card's window can
spill past its own beat, and which beats it spills into cannot be known until the master
exists — that half is derive_card_timings' job, at shot_map, with the aligned SRT
(`--apply-wide`). What IS knowable the moment a layout is chosen is the card's OWN beat,
and that is precisely the case C21 was. Catching it here moves the discovery from the
shot map to audit_inputs — hours earlier, before a credit moves.

So: two checks, one rule, deliberately split by what each can know.
"""
from __future__ import annotations

WIDE = "WIDE"
ON_SCREEN_LAYOUTS = {"panel-push"}      # layouts that put the card IN Gordon's frame

# The machine-maintained tail on _framing_note. Idempotent: stripped and rewritten, so
# repeated re-derives leave one stamp, not a pile.
STAMP_MARK = "\n\n⚙️ RE-DERIVED — "


def needs_wide_own_beat(epj: dict) -> dict:
    """{beat_n: [card ids]} for beats an ON-SCREEN card SITS ON that are not WIDE.

    Only the card's own beat. Spill beats need the SRT; see the module docstring.
    """
    framing = {b.get("n"): b.get("framing") for b in epj.get("beats", [])}
    out: dict = {}
    for c in epj.get("cards", []):
        if c.get("layout") not in ON_SCREEN_LAYOUTS:
            continue
        n = c.get("beat")
        if n is None or n not in framing:
            continue
        if framing.get(n) != WIDE:
            out.setdefault(n, []).append(c.get("id"))
    return out


def own_beat_faults(epj: dict) -> list[str]:
    """Human-readable faults, for a checker that reports rather than writes."""
    faults = []
    for n, cids in sorted(needs_wide_own_beat(epj).items()):
        who = ", ".join(str(c) for c in cids)
        faults.append(
            f"beat {n} is not WIDE but carries the on-screen card(s) {who}. A panel-push "
            f"card needs WIDE for its whole window or it lands over Gordon's face (the "
            f"EP11 failure). This is decided by the card's LAYOUT, so it is knowable now "
            f"— it does not need the master.")
    return faults


def resync_own_beats(epj: dict) -> list[tuple]:
    """Apply the rule. Returns [(beat, was, cards)] — empty when nothing changed.

    Mutates `epj` and nothing else; the caller decides whether to write the file. WIDE is
    the only lawful answer here and widening a beat cannot lose a fact, so applying it is
    a chore, not a decision — the same argument as --apply-broll and --apply-wide.
    """
    # ⚠️ `bt`, NOT `b`. A bare `b` is this codebase's alias for the BUILD dict, and
    # test_preflight_build_written greps for `b[...] =` to prove every key the build
    # writes is declared. A beat loop named `b` reads to that guard as a build write and
    # blunts it. The name is load-bearing.
    by_n = {bt.get("n"): bt for bt in epj.get("beats", [])}
    changed = []
    for n, cids in sorted(needs_wide_own_beat(epj).items()):
        bt = by_n.get(n)
        if bt is None:
            continue
        changed.append((n, bt.get("framing"), list(cids)))
        bt["framing"] = WIDE
    return changed


def stamp_framing_note(epj: dict, changed) -> bool:
    """Mark `_framing_note` as overtaken, and say by what. True if it wrote anything.

    🔴 THE NOTE GOES STALE THE MOMENT FRAMING IS RE-DERIVED, and a stale note is worse
    than none because it is read as authority. EP23's still said "EIGHTEEN WIDE OF
    FORTY-ONE" when the answer was twenty, and it explained beat 32's MCU by a layout
    C21 no longer had.

    ⚠️ THE AUTHORED PROSE IS KEPT. It carries the reasoning for the framing design, which
    nothing else records; the stamp says which parts have been overtaken rather than
    deleting the argument. Stripped and rewritten each time, so it never piles up.
    """
    if not changed:
        return False
    note = epj.get("_framing_note")
    if not isinstance(note, str):
        return False
    base = note.split(STAMP_MARK)[0].rstrip()
    who = "; ".join(f"beat {n} {was or 'unset'}->WIDE for {', '.join(str(c) for c in cids)}"
                    for n, was, cids in changed)
    epj["_framing_note"] = (
        base + STAMP_MARK
        + f"framing has been re-derived since this was written: {who}. "
          "ANY COUNT OR PER-BEAT REASON ABOVE IS THE PRE-DERIVATION DESIGN and is no "
          "longer authoritative — beats[].framing is. The reasoning above is kept "
          "because nothing else records it.")
    return True
