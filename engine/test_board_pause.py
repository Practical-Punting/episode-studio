"""test_board_pause.py — the refresh must not destroy what a human is editing.

⚠️ READ THIS BEFORE TRUSTING A GREEN RESULT.

    THIS SUITE IS STRUCTURAL, NOT BEHAVIOURAL.

There is no DOM harness in this repo, so these cases read `app.js` and assert the
SHAPE of the change. That is a proxy, and CLAUDE.md fault #1 says so plainly:
"a guard that greps for a string can be satisfied by a comment."

What it genuinely catches is REGRESSION — someone deleting the dirty check,
moving the banner inside `#lanes`, or forgetting to clear dirty on save. What it
CANNOT tell you is whether a caret survives a poll on Jodie's screen.

DRIVEN AGAINST THE LIVE BOARD, 6 Aug 2026. Three of the four requirements are
now proved BY MEASUREMENT, one is not:

  ✅ THE EP16 FAULT IS DEAD. Typed a URL, alt-tabbed away, two full refresh
     cycles, pasted a second URL over a select-all: the node was never rebuilt,
     the caret was still at 17, and the paste produced a CLEAN 55-character
     replacement. EP16 produced 168 characters with one URL inserted at offset 17.
  ✅ Node identity, selection and value: 10 rounds, 10/10 each.
  ✅ A NEW FLAG BREAKS THROUGH A PAUSED BOARD, announced by episode number, with
     the half-typed value and its node both intact.
  ✅ The pause RELEASES on save — board resumes itself, no reload.

  🔴 CTRL+Z IS UNPROVED BY MEASUREMENT. It is NOT proved and must not become
     "proved" through repetition.
     It FOLLOWS from node identity — the undo stack belongs to the element and
     the element demonstrably survives — but that is an ARGUMENT, not an
     observation, and an argument about behaviour is what this whole exercise
     exists to distrust.
     ⏳ AWAITING one observation at EP17's WORDS GATE: Jodie types a hook for
     real, alt-tabs away as she actually does, comes back and presses ctrl+Z
     once. Deliberately not rehearsed — no episode currently renders an editable
     field (all published or ready), so a standalone test would mean
     manufacturing the situation and she would be rehearsing rather than working.

  ⚠️ WHY IT COULD NOT BE DRIVEN, so the next person does not re-discover it:
     real keystrokes could not be delivered reliably to the focused field ACROSS
     tool calls — focus does not survive the round trip — and
     `document.execCommand("undo")` returns false on programmatically inserted
     text. It is deprecated and it is not a real undo stack.

  📏 AND A CORRECTION TO THIS SLICE'S OWN CLAIM: SCROLL DOES NOT SURVIVE, and it
     never did. Measured directly: scrollLeft set to 12 reads back as 12, then
     goes to 0 ON BLUR, before any refresh happens. That is native browser
     behaviour for a blurred text input — it predates this change, it happens
     with the refresh switched off, and the pause neither causes nor can fix it.

Run: python engine/test_board_pause.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app.js"
CSS = Path(__file__).resolve().parent.parent / "styles.css"
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def main():
    src = APP.read_text(encoding="utf-8")
    # Strip comments so a case cannot be satisfied by the prose explaining it —
    # the exact fault that made an earlier static check pass on its own comment.
    code = "\n".join(ln for ln in src.splitlines()
                     if not ln.strip().startswith("//") and not ln.strip().startswith("*")
                     and not ln.strip().startswith("/*"))

    # 📌 THE SINGLE-CARD REFRESH IS CARVED OUT OF THE TWO CHECKS BELOW, and the carve-out
    # is the point, so read this before widening it.
    # Two cases here used to assert the ABSENCE of `document.activeElement` and
    # `selectionStart` ANYWHERE in app.js. That was a fair proxy when the only rebuild
    # was the whole board: caret code could then only mean somebody was patching over a
    # destroyed node instead of not destroying it.
    #     It stopped being fair when refreshSeatedCards() landed — the deliberate, narrow
    # rebuild of ONE card, and only when a script has just arrived on it, because a
    # paused board was hiding seated scripts (EP19). That path SHOULD carry focus and
    # caret across: it rebuilds a node on purpose, and losing a caret is a smaller harm
    # than a script she cannot see. The old cases failed on correct code and said
    # nothing about the requirement.
    # So the requirement is now asserted where it lives: the pause DECISION must not
    # consult focus, and the WHOLE-BOARD rebuild must still be un-patched. Anything
    # outside refreshSeatedCards() is still forbidden to touch either.
    seat = re.search(r"function refreshSeatedCards\(\)[\s\S]*?\n\}", code)
    seated = seat.group(0) if seat else ""
    rest = code.replace(seated, "") if seated else code

    print("-- the pause is driven by DIRTY, not by focus --")
    check("there is a dirty set", "dirty: new Set()" in code)
    check("an input event marks a field dirty",
          re.search(r'addEventListener\("input"', code) is not None)
    check("it is DELEGATED, so fields that do not exist yet are covered",
          "document.addEventListener(\"input\"" in code,
          "a per-field listener would be a list somebody maintains")
    check("the single-card refresh was found, so the carve-outs below are real",
          bool(seated),
          "refreshSeatedCards() is gone or renamed — the two cases after this are now "
          "scanning the whole file and mean something different from what they say")
    check("FOCUS ALONE IS NOT THE TEST (Jodie had alt-tabbed away)",
          "document.activeElement" not in rest,
          "the pause is deciding on focus somewhere outside the single-card refresh; "
          "she alt-tabs away mid-edit and a blurred field is still an unsaved field")
    edit_fn = re.search(r"function editingNow\(\)[\s\S]*?\n\}", code)
    check("  and the pause decision itself reads the dirty set, never the focus",
          bool(edit_fn) and "UI.dirty" in edit_fn.group(0)
          and "activeElement" not in edit_fn.group(0),
          "editingNow() is what renderBoard asks before it rebuilds; it must answer "
          "from what is UNSAVED, not from what happens to be focused")
    check("renderBoard consults it before rebuilding",
          re.search(r"function renderBoard\(force\)[\s\S]{0,300}editingNow\(\)", code)
          is not None)
    check("and RETURNS rather than rebuilding when someone is editing",
          re.search(r"if \(editing\.length\)[\s\S]{0,200}return;", code) is not None)

    print("\n-- the node is never destroyed, which is the only way undo survives --")
    idx_guard = code.find("if (editing.length)")
    idx_html = code.find('host.innerHTML = out')
    check("the guard sits BEFORE the innerHTML write",
          0 < idx_guard < idx_html,
          "a rebuild after the check would destroy the node anyway")
    check("no attempt to save/restore a caret around the WHOLE-BOARD rebuild "
          "(it cannot restore undo)",
          "selectionStart" not in rest,
          "caret machinery outside the single-card refresh means somebody is patching "
          "over a destroyed node instead of not destroying it — and undo cannot be "
          "patched over at all: it dies with the element and no API exposes it")

    print("\n-- the ONE deliberate rebuild carries her work across, it does not drop it --")
    # 🔴 THE FAULT THIS CLOSED, 13 Aug 2026, found in a real browser and not in this file.
    # A script arriving is exactly what makes packagingEntryPending() stand down, so the
    # card flips from the entry step to the words gate IN THE SAME REBUILD that seats the
    # script: `pe-hook-…` ceases to exist and an empty `w-hook-…` takes its place.
    # restoreDrafts() looked for a box that was gone and put the half-typed hook nowhere.
    # SHE LOST THE WORD AT THE MOMENT THE SCRIPT ARRIVED, while the banner still said her
    # typing was being protected. D1 is what made it ordinary: the tab-return refetch runs
    # this the instant she looks back, which is precisely when a script has just seated.
    # Measured in test_board_editor_browser (old code: "boxes asking for it: w-hook=''").
    check("a value whose box has gone is carried to the box that now asks for that word",
          "wordAsked(" in code and "function wordAsked" in code,
          "the rebuilt card can ask for the same word under a different id; without "
          "this her unsaved hook is dropped on the floor")
    check("  the word is DERIVED from the id, never a map of gate prefixes",
          re.search(r"function wordAsked\([\s\S]*?indexOf\(\"-\"\)", code) is not None,
          "a map is a list somebody maintains, and a third gate asking for the hook "
          "would silently not be covered")
    check("  and it never overwrites a box that already holds something",
          re.search(r"got\.from === i\.id \|\| i\.value", code) is not None,
          "a box the server has since filled holds the saved truth")
    check("  the carried value keeps pausing the board, under its NEW id",
          re.search(r"UI\.dirty\.delete\(got\.from\)[\s\S]{0,200}UI\.dirty\.add", code)
          is not None,
          "editingNow() drops ids whose element is gone, so leaving the old mark "
          "behind ends the pause on work that is still unsaved")

    print("\n-- the banner is honest, specific, and OUTSIDE #lanes --")
    check("the banner is inserted as a SIBLING of #lanes",
          "insertBefore(bar, $(\"lanes\"))" in code,
          "inside #lanes it would be destroyed by the rebuild it announces")
    # The sentence is split across a JS concatenation, so match the contiguous
    # part plus the interpolation that carries the field name. Asserting the
    # whole phrase failed on a string that was correct — a test wrong about the
    # source, not a source wrong about the requirement.
    check("it names the field, not just 'paused'",
          "Not updating while you have unsaved" in src and "esc(what)" in code)
    check("the field name is ASKED OF THE FIELD, never a map of id prefixes",
          "el.labels" in code and 'getAttribute("aria-label")' in code)
    # Found by driving the real board: the script-Doc field has no label and its
    # placeholder is a SAMPLE URL, so the banner echoed a URL back at the
    # operator — not a name, and a URL in the operator's box is forbidden.
    check("  and NEVER from a placeholder, which is an example value",
          'getAttribute("placeholder")' not in code)
    check("there is a Refresh-anyway control", "pause-refresh" in code)
    check("  and it forces a real rebuild", "renderBoard(true)" in code)

    print("\n-- A PAUSED BOARD STILL BREAKS THROUGH FOR A NEW FLAG --")
    check("newly-flagged episodes are computed", "function newlyFlagged" in code)
    check("  against what was true at the LAST render, not the last poll",
          "LAST_FLAGS" in code and "function rememberFlags" in code)
    check("  and the flag is shown while paused", "pausebar-flag" in src)
    check("  it reaches her WITHOUT rebuilding the field she is in",
          idx_guard < code.find("pausebar-flag") or "pauseBanner(editing" in code)
    check("the flag reads louder than the pause beside it",
          ".pausebar-flag{" in CSS.read_text(encoding="utf-8"))

    print("\n-- the pause must not outlive the edit --")
    check("saving a field clears its dirty mark",
          re.search(r"UI\.dirty\.delete", code) is not None,
          "a guard that never lets go freezes the board until a reload")
    check("Refresh-anyway clears every dirty mark", "UI.dirty.clear()" in code)

    print(f"\nboard pause: {len(PASS)} passed, {len(FAIL)} failed")
    print("  (STRUCTURAL ONLY — the caret/undo proof needs a browser and a session)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
