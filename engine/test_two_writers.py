#!/usr/bin/env python3
"""ONCE A HUMAN HAS EDITED, THE HUMAN'S VERSION IS THE TRUTH.

Proof-pass 4: "Claude Code attempts to rewrite after an edit — refuses, raises a
flag."

The script is the only artefact with TWO AUTHORS. Without this rule a re-read
silently overwrites her edits — the same class of fault as board bug 1, slower
and with no undo at all.

    THE ENGINE MAY READ FREELY. IT MAY NEVER WRITE OVER HER.

⚠️ AND THE CASE THAT KEEPS THE GUARD USABLE: the guard compares the WORDS, not
just the flag. On the rail path `script_sync` re-reads what she wrote and writes
the same string straight back — a no-op. A guard that fired on the flag alone
would halt EVERY episode she has ever touched, which is the version somebody
switches off (CLAUDE.md #4a).

Run: python engine/test_two_writers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import engine                                                          # noqa: E402
import providers                                                       # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


class Ctx:
    """Enough of the real Ctx for step_script_sync, and no more."""

    def __init__(self, ep, incoming):
        self.ep = ep
        self.incoming = incoming
        self.provider = self
        self.mock = False
        self.written = None

    def fetch_script(self, ep, write=True):
        return self.incoming, "sha-" + str(len(self.incoming)), "the script box"

    def ep_set(self, patch):
        self.written = patch
        self.ep.update(patch)

    def stamp(self, key):
        pass

    def save(self):
        pass


def episode(**kw):
    row = {"id": "x", "ep_number": 18, "title": "Those Top 6 Favourites",
           "title_approved": True, "script_read": True,
           "script_snapshot": "HER EDITED WORDS.",
           "script_edited_by_human_at": None}
    row.update(kw)
    return row


def run(ep, incoming):
    ctx = Ctx(ep, incoming)
    prev = engine.log
    engine.log = lambda *a, **k: None
    try:
        engine.step_script_sync(ctx)
        return None, ctx
    except providers.EngineFlag as f:
        return f, ctx
    finally:
        engine.log = prev


def main():                                                            # noqa: C901
    print("\n-- 🔴 THE ENGINE REFUSES TO WRITE OVER HER --")
    ep = episode(script_edited_by_human_at="2026-08-08T07:00:00+00:00")
    flag, ctx = run(ep, "DIFFERENT WORDS THE MACHINE WANTS TO USE.")
    check("a re-read with different words is REFUSED", flag is not None)
    check("  and nothing was written", ctx.written is None,
          "it overwrote her script before flagging")
    check("  her words are untouched on the row",
          ep["script_snapshot"] == "HER EDITED WORDS.")

    print("\n-- the flag is for HER, and it reads like it --")
    msg = str(flag or "")
    print("     as she would read it:")
    for line in msg.splitlines():
        print(f"       | {line}")
    check("it says her version is the one being kept", "being kept" in msg)
    check("  it says nothing was changed or built", "nothing has been built" in msg)
    check("  it says what to do next", "approve it" in msg)
    for bad in ("script_snapshot", "script_edited_by_human_at", "_", "/", "\\",
                ".py", "None", "engine"):
        check(f"  no machine-shaped {bad!r}", bad not in msg)

    print("\n-- 🔴 BUT IT DOES NOT HALT A BUILD IT SHOULD NOT --")
    # The rail path re-reads HER OWN words and writes the same string back. A
    # guard keyed on the flag alone would stop every episode she ever touched.
    ep = episode(script_edited_by_human_at="2026-08-08T07:00:00+00:00")
    flag, ctx = run(ep, "HER EDITED WORDS.")
    check("re-reading the SAME words she wrote passes", flag is None, str(flag)[:90])
    check("  and the build carries on writing its snapshot", ctx.written is not None)

    print("\n-- and an episode she has never touched is unaffected --")
    ep = episode(script_edited_by_human_at=None)
    flag, ctx = run(ep, "CLAUDE'S FRESH DRAFT.")
    check("no human edit means no guard", flag is None, str(flag)[:90])
    check("  the snapshot is written as before",
          ctx.written and ctx.written.get("script_snapshot") == "CLAUDE'S FRESH DRAFT.")

    print("\n-- the Script Gate itself is untouched --")
    ep = episode(title_approved=False,
                 script_edited_by_human_at="2026-08-08T07:00:00+00:00")
    flag, _ = run(ep, "anything at all")
    check("the words gate still stops an unapproved episode first",
          flag is not None and "SCRIPT GATE" in str(flag), str(flag)[:90])

    print("\n-- the OTHER writer cannot reach her either --")
    # _draft_watch seats only through rail.seat_script_if_empty, whose conditional
    # write refuses a non-empty box. Two independent guards, different mechanisms.
    #
    # ⚠️ READ FROM THE SYNTAX TREE, NOT GREPPED. The first version searched the
    # function's source for "set_fields" and failed — on the COMMENT that says it
    # never calls set_fields. That is the third time today a check has fired on
    # the documentation of the thing it guards. Prose cannot trip an AST walk and
    # a real call cannot hide from one.
    import ast
    tree = ast.parse((HERE / "engine.py").read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "_draft_watch")
    calls = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            calls.add(f.id if isinstance(f, ast.Name) else
                      f.attr if isinstance(f, ast.Attribute) else "")
    check("the drafting pass CALLS seat_script_if_empty", "seat_script_if_empty" in calls)
    for forbidden in ("set_fields", "update_status", "checkpoint", "insert"):
        check(f"  and never CALLS {forbidden}()", forbidden not in calls,
              f"calls: {sorted(c for c in calls if c)}")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
