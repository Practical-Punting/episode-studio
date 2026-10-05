"""No two-way module may name EP49's files in its CODE (comments and docstrings may).

The two-way was built on one episode, and EP49 leaked into the code as literals:
`twoway_assemble.build_plan` opened `overlay/clips/ep49-title.mp4` for EVERY episode, and
`twoway_cue_sheet` titled every cue sheet "EP49". Found 6 Oct 2026 building EP55.

Read off the syntax tree (CLAUDE.md 1a): a string CONSTANT that is not a docstring and not
a bare expression statement. `twoway_furniture.py` is the one known exception and is
listed by name — it holds EP49's spoken words as constants, recorded OPEN in the
checkpoint ("never run twoway_furniture.py 55 --write"); a new module is not exempt.

FAIL-FIRST: ENGINE=<a dir holding the pre-change twoway_assemble.py> -> red.

Run: python engine/test_twoway_no_ep49_literals.py
"""
import ast
import os
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = pathlib.Path(os.environ.get("ENGINE") or pathlib.Path(__file__).resolve().parent)
KNOWN = {"twoway_furniture.py": "holds EP49's words as constants — OPEN, recorded"}
hits = []
for f in sorted(E.glob("twoway_*.py")):
    if f.name in KNOWN:
        continue
    tree = ast.parse(f.read_text(encoding="utf-8"))
    prose = {id(n.value) for n in ast.walk(tree)
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                and id(n) not in prose and "ep49" in n.value.lower():
            hits.append(f"{f.name}:{n.lineno}: {n.value[:80]!r}")
for h in hits:
    print("  FAIL ", h)
print(f"  {'PASS' if not hits else 'FAIL'}  no two-way module names EP49 in its code "
      f"(known exception: {', '.join(KNOWN)})")
sys.exit(1 if hits else 0)
