#!/usr/bin/env python3
"""EP53 — A PICK FROM AN EARLIER COVER ROUND WAS NEVER SEEN.

    python engine/test_cover_pick_earlier_round.py

Every earlier pair stays tappable on the board, and a tile from round N writes its
letter WITH the round: round 2's Cover A is "A2". On 30 Sep 2026 Jodie picked "A2"
while round 3 was showing. The engine accepted only "A" or "B", so EP53 sat at
"pick a cover" for good — and had she typed a plain "A", the book would have been
built from ROUND 3's A, a picture she did not choose.

WHAT MUST HOLD:
  · the pick step accepts "A2" and returns it (the old code never returned);
  · "A2" builds from hero-a-r2.png even while round 3 is on the board;
  · "A" / "B" still mean the pair on the board now, exactly as before;
  · a round that does not exist yet, or text that is not a pick, is NOT a pick.
"""
from __future__ import annotations

import sys
import tempfile
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
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


class _Ctx:
    """Just enough of a build context for step_cover_pick: one rail row, no human."""
    def __init__(self, row):
        self.row, self.id, self.mock, self.watch, self.stamped = row, "ep-test", False, False, []
    def check_alive(self): pass
    def refresh(self): return self.row
    def stamp(self, k): self.stamped.append(k)


def run_pick(row):
    """What step_cover_pick does with this row: its return value, or 'WAITS'."""
    try:
        return engine.step_cover_pick(_Ctx(row))
    except SystemExit:
        return "WAITS"      # not in --watch: it would have sat waiting on the pick


print("\n-- 🔴 the pick step, with EP53's real situation: 'A2' while round 3 shows --")
got = run_pick({"cover_choice": "A2", "cover_round": 3, "cover_more_requested_at": None})
check("🔴 'A2' is accepted as a pick (EP53 sat here forever)", got == {"choice": "A2"}, str(got))
got = run_pick({"cover_choice": "B3", "cover_round": 3, "cover_more_requested_at": None})
check("  'B3' — the current round named explicitly — is accepted", got == {"choice": "B3"}, str(got))
for c in ("A", "B"):
    got = run_pick({"cover_choice": c, "cover_round": 3, "cover_more_requested_at": None})
    check(f"  a plain {c!r} is still accepted, exactly as before", got == {"choice": c}, str(got))
for c, why in (("A4", "round 4 does not exist yet"), ("C", "there is no Cover C"),
               ("", "nothing picked"), ("A0", "there is no round 0"), ("Neither", "not a pick")):
    got = run_pick({"cover_choice": c, "cover_round": 3, "cover_more_requested_at": None})
    check(f"  {c!r} is NOT a pick — {why} — so it keeps waiting", got == "WAITS", str(got))

print("\n-- 🔴 which picture each pick builds from (real files, temp folder) --")
with tempfile.TemporaryDirectory() as tmp:
    pp = Path(tmp)
    prov = providers.RealProvider(pp)
    ep = {"ep_number": 9053, "title": "T", "cover_round": 3}
    d = prov.dir(ep)
    src = d / "ebook/cover-src"
    src.mkdir(parents=True)
    for name in ("hero-a.png", "hero-b.png", "hero-a-r2.png", "hero-b-r2.png",
                 "hero-a-r3.png", "hero-b-r3.png"):
        (src / name).write_bytes(name.encode())
    for choice, want in (("A2", "hero-a-r2.png"), ("B2", "hero-b-r2.png"),
                         ("A1", "hero-a.png"), ("A", "hero-a-r3.png"), ("B", "hero-b-r3.png"),
                         ("B3", "hero-b-r3.png")):
        pick, active = prov._picked_hero(ep, choice)
        mark = "🔴 " if choice == "A2" else "  "
        check(f"{mark}pick {choice!r} builds from {want} (round 3 on the board)",
              pick.name == want and active.name == "hero.png", f"got {pick.name}")

print(f"\ncover pick from an earlier round: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
