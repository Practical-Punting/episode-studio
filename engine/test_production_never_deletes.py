#!/usr/bin/env python3
"""PRODUCTION CODE NEVER DELETES FROM THE RAIL. (Jodie's ruling, 10 August 2026.)

    python engine/test_production_never_deletes.py

> Production code stays strictly SELECT / INSERT / UPDATE, never DELETE — absolute.
> For test_dead_zone.py only: it may delete ONLY the exact throwaway row it just
> created, by the id its own INSERT returned, and nothing else, ever.

`rail.delete()` exists and is labelled "admin/testing — destructive". Nothing stops a
future step from reaching for it, and the cost of one wrong call is an episode's whole
record — every timestamp, every approval, every cost figure — gone, with no undo and no
backup this side of Supabase's own retention.

A ruling that lives in a chat message protects nothing. This is the ruling as a gate.
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

# The ONE file allowed to call it, and only for the row its own INSERT returned.
ALLOWED = {"test_dead_zone.py"}
# rail.py itself DEFINES delete(); defining it is not calling it.
DEFINES = {"rail.py"}


def case(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


def rail_delete_calls(path: Path):
    """Every `rail.delete(...)` / bare `delete(...)` call site, with its line."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and f.attr == "delete" \
                and isinstance(f.value, ast.Name) and f.value.id == "rail":
            out.append(n.lineno)
        elif isinstance(f, ast.Name) and f.id == "delete":
            out.append(n.lineno)
    return out


offenders, allowed_hits = [], []
for p in sorted(REPO.rglob("*.py")):
    if ".git" in p.parts or p.name in DEFINES:
        continue
    hits = rail_delete_calls(p)
    if not hits:
        continue
    (allowed_hits if p.name in ALLOWED else offenders).append(
        (p.relative_to(REPO).as_posix(), hits))

case("no production file calls rail.delete()", not offenders,
     "DELETE reaches the rail from: "
     + "; ".join(f"{f}:{ls}" for f, ls in offenders))


# ── and the one exception must stay AS narrow as it was granted ────────────────
dz = HERE / "test_dead_zone.py"
if dz.is_file():
    src = dz.read_text(encoding="utf-8")
    case("the one exception deletes only the id its own INSERT returned",
         "rail.delete(tid)" in src and "tid = make()" in src,
         "test_dead_zone no longer deletes exactly the row it created — the exception "
         "was granted for that shape and nothing wider")
    # it must never delete by anything but that id
    bad = [ln for ln in src.splitlines()
           if "rail.delete(" in ln and "rail.delete(tid)" not in ln]
    case("  …and by nothing else", not bad, f"other delete calls: {bad}")
else:
    case("test_dead_zone.py is present to check", False, "file not found")

if allowed_hits:
    print(f"\n  (the granted exception: "
          + "; ".join(f"{f}:{ls}" for f, ls in allowed_hits) + ")")

print(f"\nnever deletes: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
