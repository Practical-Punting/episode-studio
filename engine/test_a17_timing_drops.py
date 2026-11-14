"""twoway_run.a17_timing_drops: the replan's late AND early A17 faults are both taken off their beats.

    python engine/test_a17_timing_drops.py

Real lines from EP57's and EP58's replan logs (14 Nov 2026). EP58's C12 was up 8.4s before its
first point; the replan took only LATE cards off their beats, so twoway_render refused the plan.
CONTROL: a `REPORTED` note (a card entering ON its long sentence) is a fact, not a fault, and must
not be dropped; a log with no `!` line drops nothing.
"""
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import twoway_run as tr   # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


LOG = """\
  · REPORTED A17 C14: up 5.0s before its first point — it enters on the very sentence that point is in, and that sentence is long.
1 A17 violation(s)
  ! A17 C12: up 8.4s before its first point is said (limit 4s), and it entered BEFORE the sentence that point is in — an empty card the plan could have avoided.
  ! A17 C10 cols[1]: said 1.7s BEFORE the card is up, so the point arrives after its words.
"""
got = tr.a17_timing_drops(LOG)
check("EP58 C12 (early) is dropped", "C12" in got and "early" in got["C12"], str(got.get("C12")))
check("EP57-shape C10 (late) is dropped", "C10" in got and "late" in got["C10"], str(got.get("C10")))
check("CONTROL: the REPORTED note for C14 is NOT dropped", "C14" not in got, str(sorted(got)))
check("CONTROL: a log with only notes drops nothing",
      tr.a17_timing_drops(LOG.splitlines()[0]) == {})
print(f"\na17 timing drops: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
