"""The script commission's FEEDBACK LOOP, proved fail-first with a fake writer.

Six EP19 drafts died without the writer ever being told what it had done: the engine
ran the fidelity gate AFTER the commission returned and logged the rejection where only
we could see it. `commission_with_repair` already existed for the episode.json
commission — the script path just never used it.

The proof needs no network and spends nothing: a fake `attempt` plays a writer that
gets it wrong, is told, and fixes it.

Run: python engine/test_script_repair_loop.py
"""
import ast
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import commission as com     # noqa: E402

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


print("\n=== the loop hands the gate's own words back to the writer ===\n")

seen = []          # what the writer was told, round by round
state = {"draft": "the favourite paid one dollar seventy-five"}
BAD = "the script says 'one dollar seventy five', and the article never states that figure"


def attempt(followup):
    seen.append(followup)
    if followup and "one dollar seventy five" in followup:
        state["draft"] = "the favourite was eight to eleven"      # the writer fixes it
    return {"ok": True, "round": len(seen)}


def gate():
    return [BAD] if "dollar" in state["draft"] else []


v = com.commission_with_repair(attempt=attempt, gate=gate, what="this episode's script",
                               log=lambda *a, **k: None)
check("the loop returns the verdict of the attempt that PASSED", v["round"] == 2, str(v))
check("the first attempt is given no followup", seen[0] is None, repr(seen[0]))
check("the second is given the gate's ACTUAL sentence",
      seen[1] is not None and "one dollar seventy five" in seen[1], repr(seen[1])[:160])
check("  and the article's own wording is in the feedback",
      seen[1] is not None and "never states that figure" in seen[1])
check("it stopped as soon as the gate passed", len(seen) == 2, f"{len(seen)} attempts")

print("\n=== FAIL FIRST: a writer that never fixes it exhausts the bound ===\n")

seen2 = []


def stubborn(followup):
    seen2.append(followup)
    return {"ok": True}


try:
    com.commission_with_repair(attempt=stubborn, gate=lambda: [BAD],
                               what="this episode's script", attempts=3,
                               log=lambda *a, **k: None)
    halted = None
except com.CommissionHalt as e:
    halted = e
check("an unfixable draft HALTS rather than seating", halted is not None)
check("  it used exactly the bound, no more", len(seen2) == 3, f"{len(seen2)}")
check("  rounds 2 and 3 were both told what was wrong",
      all(s and "one dollar seventy five" in s for s in seen2[1:]))
check("  the halt keeps the checker's lines for the run log",
      halted is not None and "one dollar seventy five" in str(getattr(halted, "detail", "")))
check("  and the operator-facing text stays plain English",
      halted is not None and "one dollar seventy five" not in str(halted),
      "the blockers belong in .detail, not in her message")

print("\n=== the wiring: the script commission actually uses it ===\n")

src = (HERE / "providers.py").read_text(encoding="utf-8")
tree = ast.parse(src)
cls = next(n for n in ast.walk(tree)
           if isinstance(n, ast.ClassDef) and n.name == "RealProvider")
fn = next(n for n in ast.walk(cls)
          if isinstance(n, ast.FunctionDef) and n.name == "_commission_script")
calls = {c.func.attr for c in ast.walk(fn)
         if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)}
check("_commission_script can use commission_with_repair",
      "commission_with_repair" in calls, str(sorted(calls)))
check("  and takes the gate as an argument (not its own copy)",
      "gate" in [a.arg for a in fn.args.args], str([a.arg for a in fn.args.args]))

esrc = (HERE / "engine.py").read_text(encoding="utf-8")
etree = ast.parse(esrc)
dw = next(n for n in ast.walk(etree)
          if isinstance(n, ast.FunctionDef) and n.name == "_draft_watch")
seg = ast.get_source_segment(esrc, dw) or ""
check("the drafting pass passes the REAL fidelity gate in",
      "gate=_fidelity_gate" in seg and "script_fidelity.check" in seg,
      "the gate must be the one the build halts on, not a copy")

print(f"\n{'=' * 66}")
print("FEEDBACK LOOP PROVED" if not FAILED else f"FAILURES: {FAILED}")
sys.exit(1 if FAILED else 0)
