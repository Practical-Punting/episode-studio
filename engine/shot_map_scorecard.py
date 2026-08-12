#!/usr/bin/env python3
"""Did the shot-map fix actually save the time? Score a run from the engine's own log.

    python engine/shot_map_scorecard.py EP23
    python engine/shot_map_scorecard.py EP23 --log logs/engine-2026-08-14.log

🔴 WHY THIS EXISTS RATHER THAN SOMEBODY WATCHING. Jodie asked for one number when
EP23 runs: how many halts survived, against the six EP22 had, and whether any were
the mechanical b-roll kind that should now be applied silently. Nobody can be sitting
at the board when it happens, and a measurement that depends on someone watching is
one that quietly stops being taken. The engine already writes everything down; this
reads it back.

WHAT IT COUNTS, and the distinction is the whole point:
  · AUTO-APPLIED — "applied build.broll_offsets[...]" lines. Work the tool used to
    stop and ask a human to retype. These should be SILENT wins.
  · SURVIVED — "!!" problems in a shot_map halt. Real decisions that still cost a
    round trip.

THE BASELINE IT COMPARES AGAINST is EP22's own run on 12 Aug 2026, read from the same
log format: SIX problems from the tool — four b-roll overlaps and two card-card. ⚠️ The
BOARD only ever showed three of them, because the flag was cut at 900 characters; that
truncation is itself part of what the fix addressed, so the honest baseline is the
six the tool found, not the three she saw.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

# EP22, 12 Aug 2026 — what the tool found, before any of this landed.
BASELINE = {"episode": "EP22", "broll": 4, "decisions": 2, "shown_on_board": 3}


def score(text: str, ep: str) -> dict:
    """Count what the shot map cost THIS episode, from the run log.

    ⚠️ ATTRIBUTED BY CLAIM, NOT BY PROXIMITY. The run log interleaves episodes and a
    halt line carries no episode number — "!! NEEDS A LOOK [shot_map]" looks identical
    whichever episode it belongs to. The 12 Aug log holds EP21's halt at 01:29 and
    EP22's at 07:21; a scorecard that read the file naively would score one episode's
    halts against the other and hand back a confident wrong number. The engine writes
    "claimed PP-EPnn" when it takes an episode and "parked at …; released" when it lets
    go, so that is what says who owns the lines in between.
    """
    applied, halts, cur, owner = [], [], None, None
    for line in text.splitlines():
        m = re.search(r"claimed (PP-EP\d+)", line)
        if m:
            owner = m.group(1).replace("PP-", "")
            cur = None
            continue
        if "released" in line or "parked at" in line:
            owner, cur = None, None
            continue
        if owner != ep:
            continue                      # another episode's lines — not ours to count
        a = re.search(r"applied build\.broll_offsets\[(.+?)\]\s*=\s*([\d.]+)", line)
        if a:
            applied.append((a.group(1), a.group(2)))
        if "NEEDS A LOOK [shot_map]" in line:
            cur = []
            halts.append(cur)
        elif cur is not None and line.strip().startswith("!!"):
            cur.append(line.strip())
        elif cur is not None and line.strip() and not line.startswith(" "):
            cur = None
    problems = [p for h in halts for p in h]
    kinds = {
        "b-roll (should now be silent)": sum(1 for p in problems if "B-ROLL-CARD" in p),
        "card-card (a real decision)": sum(1 for p in problems if "CARD-CARD" in p),
        "other": sum(1 for p in problems
                     if "B-ROLL-CARD" not in p and "CARD-CARD" not in p),
    }
    return {"episode": ep, "auto_applied": applied, "halt_blocks": len(halts),
            "problems": problems, "kinds": kinds}


def report(s: dict) -> int:
    ep = s["episode"]
    print("=" * 74)
    print(f"SHOT-MAP SCORECARD — {ep}")
    print("=" * 74)
    print(f"\nAUTO-APPLIED SILENTLY (used to be a halt and a human retyping a number):")
    if s["auto_applied"]:
        for t, v in s["auto_applied"]:
            print(f"   · {t.strip(chr(39))} -> {v}")
    else:
        print("   (none — this episode had no b-roll/card overlaps at all)")
    print(f"\nHALTS THAT SURVIVED: {len(s['problems'])} "
          f"(in {s['halt_blocks']} visit(s) to the board)")
    for k, n in s["kinds"].items():
        if n:
            print(f"   · {n}  {k}")
    for p in s["problems"]:
        print(f"     !! {p[3:90]}")

    b = BASELINE
    was = b["broll"] + b["decisions"]
    now = len(s["problems"])
    if ep == b["episode"]:
        # Scoring the baseline against itself is not a measurement. EP22 ran on the
        # OLD code, so 0-applied and a surviving b-roll halt are the CORRECT reading
        # of that run, not a failure of the fix.
        print(f"\nTHIS IS THE BASELINE ITSELF, and it ran BEFORE the fix landed — so "
              f"0 applied silently and a b-roll overlap on the board are what that run "
              f"genuinely looked like. Nothing to compare it against.")
        print(f"   the tool found {was} ({b['broll']} b-roll + {b['decisions']} "
              f"decisions); the board showed {b['shown_on_board']}, the rest lost to "
              f"a 900-character cut.")
        return 0
    print(f"\nAGAINST {b['episode']}: {was} problem(s) from the tool "
          f"({b['broll']} b-roll + {b['decisions']} decisions), of which only "
          f"{b['shown_on_board']} ever reached the board.")
    print(f"          {ep}: {len(s['auto_applied'])} applied silently, "
          f"{now} left for a human.")
    if s["kinds"]["b-roll (should now be silent)"]:
        print("\n⚠️  A B-ROLL OVERLAP STILL REACHED THE BOARD. That is the case "
              "--apply-broll was meant to absorb, so either the room was not there "
              "(a real decision, and the message will say so) or the flag is not "
              "being passed. Worth reading the run log around it.")
    saved = was - now
    print(f"\n{'SAVED' if saved > 0 else 'NO CHANGE'}: "
          f"{saved} fewer problem(s) needing a person than {b['episode']}.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ep = sys.argv[1].upper().replace("PP-", "")
    if "--log" in sys.argv:
        logs = [Path(sys.argv[sys.argv.index("--log") + 1])]
    else:
        logs = sorted((HERE / "logs").glob("engine-*.log"))
    if not logs:
        sys.exit("no engine logs found")
    # Only the lines belonging to this episode's shot map. The run log interleaves
    # episodes, so a naive read would score another episode's halts as this one's.
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in logs)
    if ep not in text:
        print(f"{ep} does not appear in {len(logs)} log file(s) yet — it has not run.")
        return 2
    return report(score(text, ep))


if __name__ == "__main__":
    sys.exit(main())
