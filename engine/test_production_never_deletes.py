#!/usr/bin/env python3
"""PRODUCTION CODE NEVER DELETES FROM THE RAIL. (Jodie's ruling, 10 August 2026.)

    python engine/test_production_never_deletes.py

> Production code stays strictly SELECT / INSERT / UPDATE, never DELETE — absolute.
> For a test only: it may delete ONLY the exact throwaway row it just created, by
> the id its own INSERT returned, and nothing else, ever.

`rail.delete()` exists and is labelled "admin/testing — destructive". Nothing stops a
future step from reaching for it, and the cost of one wrong call is an episode's whole
record — every timestamp, every approval, every cost figure — gone, with no undo and no
backup this side of Supabase's own retention.

A ruling that lives in a chat message protects nothing. This is the ruling as a gate.

═══ ⚖️ AMENDED 19 Aug 2026 — THE EXCEPTION IS A **SHAPE**, NOT A LIST OF FILENAMES ═══

It used to read `ALLOWED = {"test_dead_zone.py"}`. A second test needed the identical
thing — `test_yard_pickup.py`, proving the Script Gate holds on the Yard's new pick-up
path — and a filename list has only one answer to that: edit the list. **Jodie's ruling,
19 Aug: write the shape.**

> *"The danger the 10 Aug ruling names is a delete driven by a FILTER — one mistyped
> `created_by` and a real episode's record is gone. An id this process created a second
> earlier is a different animal."*

**THE SHAPE, AS ENFORCED BELOW:** a delete is permitted only when its argument is a NAME
that this module's own `rail.insert(...)` produced — directly, or through one hop of a
module-level helper that returns it — **and that name is never assigned from anything
else anywhere in the file.** Everything else is an offence: a literal, an attribute, a
filter string, a call this file cannot trace, or no argument at all.

🔴 **AND THE BAN ON PRODUCTION STAYS ABSOLUTE — THE SHAPE DOES NOT APPLY THERE.** A pure
shape rule would let `engine.py` delete a row it had just inserted, which is exactly the
widening Jodie's "absolute" forbids. So the shape is what a TEST must satisfy; a
non-test file calling `rail.delete` at all is an offence however tidy its argument.
*(Test = a file named `test_*.py`. That is a filename rule, deliberately: it decides WHO
may hold the exception, not WHAT the exception permits.)*

⚠️ **WHERE THIS CHECK IS HONESTLY WEAK — SAY IT RATHER THAN IMPLY OTHERWISE.** It is
SYNTACTIC. It proves the argument NAME traces to an insert; it cannot prove the VALUE
does at runtime. It closes the obvious hole (a name reassigned from something else fails
the check) but a determined enough indirection — two hops, a container, a class
attribute — would defeat it. **It is a guard against a mistake, not against intent**,
and that is the right ambition for this file: nobody is attacking the rail, somebody is
one day going to reach for a convenient delete.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []

# rail.py itself DEFINES delete(); defining it is not calling it.
DEFINES = {"rail.py"}


def case(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


def _is_rail_insert(node) -> bool:
    """Does this expression contain a `rail.insert(...)` call anywhere inside it?

    Covers `rail.insert({...})`, `rail.insert({...})["id"]`, `rail.insert(...)  or {}`
    — the subscript and the call are different nodes, so the walk is the honest test.
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "insert" and isinstance(n.func.value, ast.Name) \
                and n.func.value.id == "rail":
            return True
    return False


def _assignments(tree):
    """name -> [every value expression assigned to it, anywhere in the file]."""
    out: dict[str, list] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(n.value)
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign)) and isinstance(n.target, ast.Name):
            if n.value is not None:
                out.setdefault(n.target.id, []).append(n.value)
    return out


def _fns_returning_insert(tree) -> set[str]:
    """Module-level functions whose RETURN traces to a rail.insert — the one hop.

    `test_dead_zone.py` is written this way: `def make(): t = rail.insert(...); return
    t["id"]`, then `tid = make()`. One hop is enough for both real files and stops well
    short of chasing arbitrary indirection.
    """
    out = set()
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        local = _assignments(fn)
        for r in [n for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value]:
            if _is_rail_insert(r.value):
                out.add(fn.name); break
            # `return t["id"]` where t came from an insert in this function
            names = {x.id for x in ast.walk(r.value) if isinstance(x, ast.Name)}
            if any(any(_is_rail_insert(v) for v in local.get(nm, [])) for nm in names):
                out.add(fn.name); break
    return out


def _insert_derived(tree) -> set[str]:
    """Names this file can prove came from its OWN rail.insert, and nothing else."""
    assigns = _assignments(tree)
    hops = _fns_returning_insert(tree)

    def from_insert(val) -> bool:
        if _is_rail_insert(val):
            return True
        return (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                and val.func.id in hops)

    # EVERY assignment to the name must come from an insert. One reassignment from
    # anything else and the name is no longer provably the row this file created.
    return {nm for nm, vals in assigns.items()
            if vals and all(from_insert(v) for v in vals)}


def delete_calls(tree):
    """Every `rail.delete(...)` / bare `delete(...)` call node."""
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if (isinstance(f, ast.Attribute) and f.attr == "delete"
                and isinstance(f.value, ast.Name) and f.value.id == "rail") \
                or (isinstance(f, ast.Name) and f.id == "delete"):
            out.append(n)
    return out


offenders, allowed_hits = [], []
for p in sorted(REPO.rglob("*.py")):
    if ".git" in p.parts or p.name in DEFINES:
        continue
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        continue
    calls = delete_calls(tree)
    if not calls:
        continue
    rel = p.relative_to(REPO).as_posix()
    is_test = p.name.startswith("test_")
    safe = _insert_derived(tree) if is_test else set()
    bad = []
    for c in calls:
        ok = (is_test and len(c.args) == 1 and not c.keywords
              and isinstance(c.args[0], ast.Name) and c.args[0].id in safe)
        (allowed_hits if ok else bad).append(c.lineno)
    if bad:
        offenders.append((rel, sorted(bad),
                          "not a test file" if not is_test
                          else "argument is not an id this file's own INSERT returned"))

case("every rail.delete() is a test deleting the id its own INSERT returned",
     not offenders,
     "; ".join(f"{f}:{ls} ({why})" for f, ls, why in offenders))


# ── the shape must actually be ENFORCED, not merely described ────────────────────
# 🔴 FAIL-FIRST. A checker that cannot reject is not a checker, and this file's whole
# job is rejecting. Each snippet below is a delete the ruling forbids; if any of them
# now PASSES, the shape has been loosened and everything above is decoration.
REFUSALS = [
    ("a delete by filter, not id",
     "import rail\nrail.delete('created_by=eq.someone')\n"),
    ("a delete of a name that never came from an insert",
     "import rail\ntid = board_row['id']\nrail.delete(tid)\n"),
    ("a delete of a name reassigned from something else",
     "import rail\ntid = rail.insert({})['id']\ntid = other['id']\nrail.delete(tid)\n"),
    ("a delete with no argument at all",
     "import rail\nrail.delete()\n"),
    ("a delete of an attribute rather than a traced name",
     "import rail\nrail.delete(self.tid)\n"),
]
for label, code in REFUSALS:
    tree = ast.parse(code)
    safe = _insert_derived(tree)
    calls = delete_calls(tree)
    accepted = any(len(c.args) == 1 and not c.keywords
                   and isinstance(c.args[0], ast.Name) and c.args[0].id in safe
                   for c in calls)
    case(f"  refuses: {label}", not accepted,
         "this shape was ACCEPTED — the guard has been loosened")

# ...and the shape it exists to permit must still be accepted, or the guard is simply
# jammed shut and every future test gets rewritten around a gate that says no to all.
for label, code in [
        ("direct: tid = rail.insert(...)['id']",
         "import rail\ntid = rail.insert({})['id']\nrail.delete(tid)\n"),
        ("one hop: tid = make(), where make() returns the inserted id",
         "import rail\ndef make():\n    t = rail.insert({})\n    return t['id']\n"
         "tid = make()\nrail.delete(tid)\n")]:
    tree = ast.parse(code)
    safe = _insert_derived(tree)
    accepted = any(len(c.args) == 1 and isinstance(c.args[0], ast.Name)
                   and c.args[0].id in safe for c in delete_calls(tree))
    case(f"  permits: {label}", accepted,
         "the granted shape was REFUSED — the guard is jammed shut")

if allowed_hits:
    print(f"\n  (deletes permitted by the shape: {len(allowed_hits)})")

print(f"\nnever deletes: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
