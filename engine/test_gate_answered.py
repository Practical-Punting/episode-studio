"""C3 — A REBOOT MUST NOT BE ABLE TO WALK A HUMAN GATE THROUGH.

EP23, 13 Aug 2026. `listen_to_the_master` wrote its marker and THEN raised the flag,
so the marker recorded that the gate had ASKED — while the file itself said "a human
has listened to this master". Windows updated overnight and killed the engine in the
gap. On resume the step found the marker and walked straight into shot_map.

Nothing was lost: the gate sits before the expensive half-hour, the shot map halted 51s
in, and Jodie confirms she HAD listened. IT PASSED BY ACCIDENT, NOT BY DESIGN.

    A GATE THAT A POWER CUT CAN PASS IS NOT A GATE.

And it was a CLASS, not a step: the listen gate and BOTH placement reviews had the
identical shape. So the fix is one helper the three call, and this suite proves the
helper AND that all three actually use it — a shared fix that one call site quietly
opts out of is worse than three separate ones, because it reads as covered.

Run: python engine/test_gate_answered.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import providers                                                      # noqa: E402
from providers import EngineFlag, ask_once, answer_pending_gates      # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


def asked(d: Path):
    return sorted(p.name for p in d.rglob(".asked-*"))


def answers(d: Path):
    return sorted(p.name for p in d.rglob(".answered-*"))


def raises(fn) -> bool:
    try:
        fn()
    except EngineFlag:
        return True
    return False


print("\n-- asking is not the same as being answered --")
d = Path(tempfile.mkdtemp())
g = d / "renders"

check("the first asking raises the flag",
      raises(lambda: ask_once(g, "listened-1-2", "listen to it")))
check("  and it records that it ASKED", asked(d) == [".asked-listened-1-2"], asked(d))
check("  and records NO answer", answers(d) == [], answers(d))

# THE EP23 CASE, EXACTLY: the process dies here. Nothing else runs. Resume:
check("A REBOOT BETWEEN THE ASK AND THE ANSWER ASKS AGAIN",
      raises(lambda: ask_once(g, "listened-1-2", "listen to it")),
      "this is the whole fix — the marker it finds says 'asked', not 'answered', "
      "and an unanswered ask is not an answer no matter how many times it is found")

print("\n-- and once a human has actually answered, it stops asking --")
done = answer_pending_gates(d)
check("clearing the flag promotes the ask to an answer", done == [".answered-listened-1-2"], done)
check("  the ask is gone, so it cannot be counted twice", asked(d) == [], asked(d))
check("  and the answer names what was answered", answers(d) == [".answered-listened-1-2"])
check("THE ANSWERED GATE DOES NOT ASK AGAIN",
      not raises(lambda: ask_once(g, "listened-1-2", "listen to it")),
      "a gate that re-asks after a real answer is a gate nobody can get past")
check("  and the record keeps BOTH times, so the log can be read later",
      "asked " in (g / ".answered-listened-1-2").read_text(encoding="utf-8")
      and "answered " in (g / ".answered-listened-1-2").read_text(encoding="utf-8"))

print("\n-- a DIFFERENT question is a different gate --")
# The stem carries the master's size and mtime, so a re-render asks again — EP20's case.
check("a new master asks again even though the old one was answered",
      raises(lambda: ask_once(g, "listened-9-9", "listen to the NEW one")),
      "inheriting the last master's approval is precisely the EP20 fault")

print("\n-- the pre-C3 markers on EP01–EP23 are still answers --")
d2 = Path(tempfile.mkdtemp())
g2 = d2 / "thumbnail"
g2.mkdir(parents=True)
(g2 / ".placement-reviewed").write_text("a human has looked\n", encoding="utf-8")
check("a legacy marker is honoured, so published episodes are not re-halted",
      not raises(lambda: ask_once(g2, "placement-reviewed", "look at it",
                                  legacy=g2 / ".placement-reviewed")),
      "twenty-three episodes carry these; re-asking would halt in-flight work for "
      "a question that was already answered")

print("\n-- ALL THREE GATES USE IT (it is a class, not a step) --")
import inspect                                                        # noqa: E402

for fn_name in ("listen_to_the_master", "thumbnail_placement_review",
                "title_placement_review"):
    fn = getattr(providers, fn_name, None)
    if fn is None:
        check(f"{fn_name} exists", False, "renamed or removed — this suite is now blind")
        continue
    src = inspect.getsource(fn)
    check(f"{fn_name} asks through the shared gate", "ask_once(" in src)
    check(f"  and no longer writes its own marker before raising",
          "write_text" not in src,
          "a marker written beside the raise is the EP23 bug, whatever it is named")

print("\n-- the answer is recorded where an answer can be SEEN --")
eng = (HERE / "engine.py").read_text(encoding="utf-8")
check("the engine records answers when a flag clears",
      "_record_gate_answers" in eng and "answer_pending_gates" in eng)
check("  it is called from the flag wait (the --watch path)",
      eng.count("_record_gate_answers(ctx)") >= 2,
      "one call site covers --watch only; the EP23 kill happened with nothing waiting")
check("  and it refuses to promote without proof the flag was really raised",
      'if not ctx.state.get("flag_step")' in eng,
      "'not flagged' alone also describes a flag that was never raised — promoting "
      "on that rebuilds the same silent pass one layer up")

print(f"\ngate answers: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
