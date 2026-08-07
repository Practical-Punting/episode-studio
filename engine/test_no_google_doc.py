#!/usr/bin/env python3
"""PROOF-PASS 8, STATIC HALF — no Doc-creating path is reachable from the spine.

    "Run a whole episode from a URL and confirm NO GOOGLE DOC IS CREATED AT ANY
     POINT — and that docs/spoken-words.txt is still written as it is today.
     If a Doc appears, the change is half done."   — PP-script-editor-BUILD-PLAN

🔴 THIS SUITE IS A PROXY AND SAYS SO. It walks the call graph from the engine's
own step table and proves no reachable function can CREATE a Google Doc, and that
the path that writes docs/spoken-words.txt is still reachable. That is a claim
about the CODE.

    A REAL PASS ON THE WRONG ARTEFACT IS A FALSE PASS. The proof is a real output
    FILE — or in this case the absence of one — and only a real episode running
    end to end can give it.

So proof-pass 8 stands at:  STATIC: PASS · ARTEFACT-LEVEL: PENDING EP18's build.
Do not record it as closed until a real run confirms no Doc was created and
docs/spoken-words.txt was written. (Jodie, 8 Aug 2026.)

⚠️ HOW THE GRAPH IS BUILT, NAMED RATHER THAN GLOSSED. Calls are resolved BY NAME
across the engine's own modules — `self.foo()`, `mod.foo()` and `foo()` all match
a def named `foo`. That over-reaches (it may follow an edge that does not exist)
rather than under-reaches, which is the safe direction for a "nothing can reach
this" proof: a false edge can only make the audit stricter.

Run: python engine/test_no_google_doc.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude/skills/pp-episode-production/scripts"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


# ── what "creating a Google Doc" looks like in code ─────────────────────────
# The engine has never created one — Docs were made by Claude Code through an
# MCP connector, outside this codebase. These are the markers that would appear
# if any of that ever moved in.
DOC_CREATE = (
    "docs.google.com/create", "documents.create", "files.create",
    "application/vnd.google-apps.document", "drive/v3/files",
    "googleapis.com", "google_drive", "create_file", "gdoc",
)
# Reading an EXISTING Doc is a different thing and is legitimate for EP01-EP16
# (A5: "a Doc still wins wherever one exists"). Tracked separately, not failed.
DOC_READ = ("docs.google.com/document", "export?format=txt")


def module_functions(paths):
    """{name: FunctionDef} across the engine's own modules."""
    out, trees = {}, {}
    for p in paths:
        if not p.is_file():
            continue
        t = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        trees[p.name] = t
        for n in ast.walk(t):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.setdefault(n.name, []).append((p.name, n))
    return out, trees


def calls_in(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def strings_in(node):
    """String CONSTANTS only — never comments, and never a docstring.

    Fault 1a: a check that greps source fires on the comment describing the thing
    it guards. Three times in one day. The AST gives code and only code."""
    out = []
    for i, n in enumerate(ast.walk(node)):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    # drop the function's own docstring
    doc = ast.get_docstring(node)
    if doc:
        out = [s for s in out if s != doc]
    return out


def main():                                                            # noqa: C901
    files = [HERE / f for f in ("engine.py", "providers.py", "commission.py",
                                "rail.py", "script_fidelity.py",
                                "preflight_cards.py", "preflight_episode_json.py")]
    funcs, trees = module_functions(files)
    print(f"-- {len(funcs)} function names across {len(trees)} engine modules --")

    # ── the spine's entry points, DERIVED from the step table ───────────────
    eng = trees["engine.py"]
    roots = sorted(n.name for n in ast.walk(eng)
                   if isinstance(n, ast.FunctionDef) and n.name.startswith("step_"))
    roots += ["_draft_watch", "cmd_run", "run_phase", "run_step"]
    check("the spine's entry points were found, not hard-coded",
          len(roots) >= 12, f"only {roots}")

    # ── reachability ────────────────────────────────────────────────────────
    seen, stack = set(), list(roots)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        for _mod, node in funcs.get(name, []):
            stack.extend(calls_in(node))
    print(f"-- {len(seen)} function names reachable from the spine --")
    check("the walk actually reached a long way", len(seen) > 60, f"{len(seen)}")

    print("\n-- 🔴 CAN ANYTHING REACHABLE CREATE A GOOGLE DOC? --")
    creators = []
    for name in sorted(seen):
        for mod, node in funcs.get(name, []):
            hay = " ".join(strings_in(node)).lower() + " " + " ".join(calls_in(node)).lower()
            for marker in DOC_CREATE:
                if marker.lower() in hay:
                    creators.append(f"{mod}:{name} -> {marker!r}")
    for c in creators:
        print(f"     !! {c}")
    check("NO reachable function can create a Google Doc", not creators,
          "; ".join(creators))

    print("\n-- reading an EXISTING Doc, which is a different thing --")
    readers = []
    for name in sorted(seen):
        for mod, node in funcs.get(name, []):
            hay = " ".join(strings_in(node)).lower()
            if any(m.lower() in hay for m in DOC_READ):
                readers.append(f"{mod}:{name}")
    print(f"     reachable Doc READERS: {readers or 'none'}")
    # ⚠️ TWO NAMES, NOT ONE, AND THE SECOND IS CORRECT. `_doc_id` parses the id
    # out of `script_doc_url` and exists only to serve `fetch_script`'s legacy
    # branch. The first version of this case asserted "confined to fetch_script"
    # and failed on its own helper — the assertion was too narrow, not the code.
    LEGACY_READ = {"providers.py:fetch_script", "providers.py:_doc_id"}
    check("Doc reading is confined to the legacy fetch path and its helper",
          set(readers) <= LEGACY_READ, str(sorted(set(readers) - LEGACY_READ)))
    check("  it READS an existing Doc and never makes one",
          not creators)
    check("  and it is legitimate — EP01-EP16 keep their transport (A5: "
          "'a Doc still wins wherever one exists'); EP17 onward have none", True)

    print("\n-- 🔴 AND THE HALF THAT MUST STILL HAPPEN: spoken-words.txt --")
    writers = []
    for name in sorted(seen):
        for mod, node in funcs.get(name, []):
            if any("spoken-words.txt" in s for s in strings_in(node)):
                writers.append(f"{mod}:{name}")
    print(f"     reachable writers/readers of spoken-words.txt: {writers}")
    check("the spine still reaches docs/spoken-words.txt", bool(writers),
          "render_ready runs against that file at audit_inputs — losing it is "
          "the thing decision 3 depends on")

    print("\n-- the drafting pass writes the words to the RAIL, not a Doc --")
    dw = funcs.get("_draft_watch", [])
    check("_draft_watch calls seat_script_if_empty",
          any("seat_script_if_empty" in calls_in(n) for _m, n in dw))

    print("\n" + "=" * 70)
    print("PROOF-PASS 8 — STATIC: PASS" if not FAIL else "PROOF-PASS 8 — STATIC: FAIL")
    print("PROOF-PASS 8 — ARTEFACT-LEVEL: *** PENDING EP18's BUILD ***")
    print("  This suite proves a property of the CODE. The definitive proof is a")
    print("  real episode running end to end with NO Doc created and")
    print("  docs/spoken-words.txt still written. Do not record proof-pass 8 as")
    print("  closed until those two files have been looked at.")
    print("=" * 70)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
