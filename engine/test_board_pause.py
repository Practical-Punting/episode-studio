"""test_board_pause.py — the refresh must not destroy what a human is editing.

⚠️ READ THIS BEFORE TRUSTING A GREEN RESULT.

    THIS SUITE IS STRUCTURAL, NOT BEHAVIOURAL.

There is no DOM harness in this repo, so these cases read `app.js` and assert the
SHAPE of the change. That is a proxy, and CLAUDE.md fault #1 says so plainly:
"a guard that greps for a string can be satisfied by a comment."

What it genuinely catches is REGRESSION — someone deleting the dirty check,
moving the banner inside `#lanes`, or forgetting to clear dirty on save. What it
CANNOT tell you is whether a caret survives a poll on Jodie's screen.

    THE BEHAVIOURAL PROOF IS OUTSTANDING and needs a browser with a session:
    type into a hook, alt-tab away, wait past thirty seconds, come back and
    check the caret, the selection, the scroll and ctrl-Z.

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

    print("-- the pause is driven by DIRTY, not by focus --")
    check("there is a dirty set", "dirty: new Set()" in code)
    check("an input event marks a field dirty",
          re.search(r'addEventListener\("input"', code) is not None)
    check("it is DELEGATED, so fields that do not exist yet are covered",
          "document.addEventListener(\"input\"" in code,
          "a per-field listener would be a list somebody maintains")
    check("FOCUS ALONE IS NOT THE TEST (Jodie had alt-tabbed away)",
          "document.activeElement" not in code)
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
    check("no attempt to save/restore a caret (it cannot restore undo)",
          "selectionStart" not in code)

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
          "el.labels" in code and "getAttribute(\"placeholder\")" in code)
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
