#!/usr/bin/env python3
"""THE SHOT MAP MUST STOP BEING THE PLACE EPISODES GO TO DIE.

    python engine/test_shot_map_flows.py

It is the biggest time sink in a build — 30 to 60 minutes, every episode, on the
critical path, because the HeyGen render overlaps card-building and the card/shot-map
phase is what everything else waits on. EP21 halted on C18/C19. EP22 halted on
C18/C19 AND four b-roll overlaps. Same shape both times.

TWO DIFFERENT FAULTS WERE BEING TREATED AS ONE, and only one of them was ever a
decision:

  1. A B-ROLL/CARD OVERLAP IS NOT A DECISION. `why_broll_card` computes the exact
     delay and CONFIRMS the room exists at the back of the clip's own beat before it
     says a word — then printed "Set build.broll_offsets['x'] to 4.61" and halted the
     build so a person could type 4.61 into a file. Four of EP22's six halts were
     this. Every one was applied verbatim, unchanged, by hand.

  2. A CARD TOO BIG FOR ITS WINDOW IS a decision — but it was handed over WITHOUT THE
     NUMBERS. The message said "too big for its beat" and named the beat of the wrong
     card, so a human re-derived the same three figures by hand every time: what
     window does it really have, what does it need at its current size, and is it
     even possible. That arithmetic is what turned a two-minute call into a round trip.

⚠️ WHAT THIS SUITE DOES NOT CLAIM. Cards are NOT born knowing their beat. They are
authored at `audit_inputs`, and the beat geometry comes from `renders/aligned.srt`,
which does not exist until `heygen_download` — a whole phase later. Estimating beat
length from word counts was measured across all 13 aligned episodes before being
rejected: 357 beats, mean error -0.03s but STDEV 4.55s, worst over-estimate +13.28s,
and it reads LONG half the time. On a ~10s beat that is not a check, it is a coin
toss that would wave the too-big card through with false confidence.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPTS = REPO / ".claude/skills/pp-episode-production/scripts"
PP = Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def check(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


spec = importlib.util.spec_from_file_location("ch", SCRIPTS / "card_hold.py")
ch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ch)


def derive(d, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / "derive_card_timings.py"), str(d),
                        *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ep22_copy(tmp, mutate=None):
    """A working copy of EP22 with its REAL SRT and shot map, optionally rewound."""
    src = _ep.episode_dir(22, PP)
    d = Path(tmp)
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "renders").mkdir(parents=True, exist_ok=True)
    for f in ("aligned.srt", "shot-map.json"):
        shutil.copy(src / "renders" / f, d / "renders" / f)
    epj = json.loads((src / "docs/episode.json").read_text(encoding="utf-8"))
    if mutate:
        mutate(epj)
    (d / "docs/episode.json").write_text(json.dumps(epj, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    return d


import ep_paths as _ep                      # renamed on publish; resolve by NUMBER
HAVE_EP22 = _ep.have(22, "renders", "aligned.srt", pp=PP)

# ══════════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("PART A - the arithmetic a human did by hand, every time")
print("=" * 78)
# EP22 C18: it enters 479.38 and C19 enters 488.28, so its real window is 8.90s, and a
# three-cell slate asks 9.0s. Over by 0.10s — not the "~2s" the brief guessed, because
# the old message quoted the wrong card's beat.
c18 = {"id": "C18", "content": {"cells": [1, 2, 3]}}
o = ch.options_for(c18, {"min_card_hold": 10.0}, 8.90)
check("it names the shortfall exactly", "over by 0.10s" in o, o)
check("  and the fold that fixes it", "FOLD to 2 item(s)" in o, o)
check("  and offers the split as the alternative", "SPLIT" in o, o)
check("  and forbids dropping the fact", "never drop the fact" in o, o)

# EP22 C19: 6.43s of window against a 7.0s absolute floor. No size fits.
c19 = {"id": "C19", "content": {"rows": [1, 2, 3]}}
o2 = ch.options_for(c19, {"min_card_hold": 10.0}, 6.43)
check("a window under the floor is called IMPOSSIBLE, not 'tighten it'",
      "NOTHING FITS THIS WINDOW" in o2, o2)
check("  and it says tightening AND splitting both fail",
      "tightening and splitting BOTH fail" in o2, o2)
check("  and names the floor it is short of", "7.0s" in o2, o2)
check("  CONTROL: it does NOT offer a fold that cannot exist",
      "FOLD to" not in o2, o2)

# CONTROL: a card that fits is not told to change.
check("CONTROL: a card that fits is left alone",
      "already fits" in ch.options_for(c18, {"min_card_hold": 10.0}, 12.0))

print()
print("=" * 78)
print("PART B - EP22's real halt, reproduced and then cleared")
print("=" * 78)
if not HAVE_EP22:
    check("EP22's aligned SRT is on this machine", False, "cannot run the real case")
else:
    # ---- the four b-roll halts -------------------------------------------------
    with tempfile.TemporaryDirectory() as t:
        d = ep22_copy(t, lambda e: e["build"].pop("broll_offsets", None))
        rc, out = derive(d)
        n = out.count("B-ROLL-CARD overlap")
        check("CONTROL: without the offsets EP22 halts on 4 b-roll overlaps",
              rc != 0 and n == 4, f"rc={rc} n={n}")
        rc2, out2 = derive(d, "--apply-broll")
        check("  --apply-broll clears all four and the map derives",
              rc2 == 0 and "ALL CHECKS PASS" in out2, out2[-400:])
        applied = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
        got = applied["build"].get("broll_offsets", {})
        check("  and it wrote the tool's OWN numbers", got.get(
            "broll-shifting-ground-down-the-straight") == 4.61, str(got))

    # ---- the C18/C19 timing halt ----------------------------------------------
    def rewind_cards(e):
        c18 = next(x for x in e["cards"] if x["id"] == "C18")
        c19 = next(x for x in e["cards"] if x["id"] == "C19")
        c18["content"]["cells"] = [
            {"k": "1000 m and 1200 m sprints",
             "v": "Runners drawn wide are disadvantaged", "sub": None},
            {"k": "The 1400 m start",
             "v": "A nice even run of 500 m to the first bend",
             "sub": "Plenty of time to settle down"},
            {"k": "Minus factors", "v": "Horses drawn 12 and wider", "sub": None}]
        c19["beat"] = 32
        c19["cue"] = "So there it is"
        e["build"].get("holds", {}).pop("C18", None)

    with tempfile.TemporaryDirectory() as t:
        d = ep22_copy(t, rewind_cards)
        rc, out = derive(d, "--apply-broll")
        check("CONTROL: the pre-fix C18/C19 still HALT on time", rc != 0, out[-300:])
        check("  and C18 is named as the one that gives way",
              "C18 IS THE ONE THAT GIVES WAY" in out, out[-500:])
        check("  with its real window, not the other card's beat",
              "it has 8.90s and needs 9.0s at 3 item(s)" in out, out[-500:])
        # 🔴 CHANGED 13 AUG 2026 — THE OLD ASSERTION WAS PINNING A BUG IN PLACE.
        # It demanded "NOTHING FITS THIS WINDOW" for C19. That verdict came from the end
        # card being placed at `beat - endcard_lead`, 3.0s early, so C19 was measured
        # against room that had not run out yet. With the end card where
        # assemble_episode actually builds it, C19 has 9.43s and needs 9.0s:
        #
        #     C19 IS THE ONE THAT GIVES WAY (its window runs to END's entry):
        #     it already fits — needs 9.0s and has 9.43s
        #
        # EP22's C19 was a PHANTOM too, the same shape as EP23's C23. The 0.57s overlap
        # is real, but it is a HOLD to bring down — 10.0s authored against 9.43s
        # available, floor 9.0s — not a card that fits nowhere. Keeping the old wording
        # would re-pin the 3.0s error, which is how it survived two episodes unnoticed.
        c19_msg = out.split("C19/END")[-1][:600]
        check("  and C19 is NOT called impossible — it fits, at its floor",
              "NOTHING FITS THIS WINDOW" not in c19_msg, c19_msg)
        check("  C19's overlap is reported as a hold that fits, with the numbers",
              "it already fits" in c19_msg and "9.43s" in c19_msg, c19_msg)
        check("  and no 'does not fit' sits beside 'already fits'",
              "IT DOES NOT FIT AT ANY CUE POSITION" not in c19_msg, c19_msg)

    # ---- and the shipped fix passes -------------------------------------------
    with tempfile.TemporaryDirectory() as t:
        d = ep22_copy(t)
        rc, out = derive(d, "--apply-broll")
        check("EP22 as it was RIGHT-SIZED derives clean",
              rc == 0 and "ALL CHECKS PASS" in out, out[-400:])

print()
print("=" * 78)
print("PART D - EP25 C26: the hold follows the floor, the FOLD stays a decision")
print("=" * 78)
# 🔴 THE HALT, AND WHY IT WAS DONE TWICE BY HAND. EP25 halted with
#     CARD-CARD overlap C26/END: 0.34s — it has 9.66s and needs 10.0s at 4 item(s)
# A human folded C26 from four cells to three AND set build.holds["C26"] = 9.0. Both
# were needed, and only the first is a decision: folding lowers the FLOOR, but
# `hold_for` returns build.holds[cid] or the episode default, so the PLANNED hold does
# not move with it. Fold and stop, and the identical halt comes back.
HAVE_EP25 = _ep.have(25, "renders", "aligned.srt", pp=PP)


def ep25_copy(tmp, mutate=None):
    src = _ep.episode_dir(25, PP)
    d = Path(tmp)
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "renders").mkdir(parents=True, exist_ok=True)
    for f in ("aligned.srt", "shot-map.json"):
        shutil.copy(src / "renders" / f, d / "renders" / f)
    epj = json.loads((src / "docs/episode.json").read_text(encoding="utf-8"))
    if mutate:
        mutate(epj)
    (d / "docs/episode.json").write_text(json.dumps(epj, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    return d


def unfold(e):
    """C26 back to the FOUR cells it halted on — the bank and the stake split apart,
    which is precisely the pair the human merged."""
    c = next(x for x in e["cards"] if x["id"] == "C26")
    cells = c["content"]["cells"]
    c["content"]["cells"] = [
        {"k": "The bank", "v": "Preferably 50 times your flat level stake", "sub": None},
        {"k": "The stake", "v": "Most professional punters say level stake betting is "
                                "the best and safest", "sub": None},
        cells[1], cells[2]]
    e["build"].pop("holds", None)


if not HAVE_EP25:
    print("  ·  skipped — EP25's aligned SRT is not on this machine")
else:
    # ---- the EDITORIAL half: no arithmetic clears it, so it must still halt -------
    with tempfile.TemporaryDirectory() as t:
        d = ep25_copy(t, unfold)
        rc, out = derive(d, "--apply-broll", "--apply-wide", "--apply-hold")
        check("a card that does not fit EVEN AT ITS FLOOR still halts",
              rc != 0 and "CARD-CARD overlap C26/END" in out, out[-400:])
        check("  and --apply-hold did NOT touch build.holds",
              "C26" not in ((json.loads((d / "docs/episode.json").read_text(
                  encoding="utf-8")).get("build") or {}).get("holds") or {}),
              "a fold was applied without a human")
        check("  and the halt names the ONE decision it wants",
              "WHICH row folds into which" in out, out[-500:])
        check("  and promises the hold follows by itself",
              "you do not have to set build.holds" in out, out[-500:])
        check("  and never offers to DROP a fact",
              "never drop the fact" in out and "DROP it" not in out, out[-400:])

    # ---- the MECHANICAL half: folded, holds unset — the half that got forgotten ---
    with tempfile.TemporaryDirectory() as t:
        d = ep25_copy(t, lambda e: e["build"].pop("holds", None))
        rc0, out0 = derive(d, "--apply-broll", "--apply-wide")
        check("CONTROL: folded but with the hold left at the default, it HALTS",
              rc0 != 0 and "CARD-CARD overlap C26/END" in out0, out0[-400:])
        rc1, out1 = derive(d, "--write", "--apply-broll", "--apply-wide", "--apply-hold")
        got = (json.loads((d / "docs/episode.json").read_text(
            encoding="utf-8")).get("build") or {}).get("holds", {}).get("C26")
        check("  --apply-hold brings it down and the map derives",
              rc1 == 0 and "ALL CHECKS PASS" in out1, out1[-400:])
        check("  and it wrote exactly what the human wrote by hand (9.0)",
              got == 9.0, f"build.holds['C26'] = {got}")
        check("  and it said so, with the arithmetic behind it",
              "applied build.holds['C26'] = 9.0" in out1 and "for 3 item(s)" in out1,
              out1[-400:])

# 🔴 AND IT MUST BE WIRED WHERE THE ENGINE ACTUALLY CALLS THE TOOL. Everything above
# drives derive_card_timings directly, which proves the FLAG and says nothing about
# whether a build ever passes it. That is the A22 lesson from the same day: the
# orientation rule was correct, tested and green while the funnel that mattered never
# called it. So this reads the engine's own invocation.
# ⚠️ SCOPED TO THE FUNCTION, and that took a second go. `derive_timings` is module
# level, so splitting on a 4-space `def ` ran past it to the first CLASS METHOD —
# 39,000 characters, in which almost any string would be found. A check whose window is
# most of the file is a check that cannot fail. Cut at the next TOP-LEVEL def.
_prov_src = (REPO / "engine/providers.py").read_text(encoding="utf-8")
_derive = _prov_src.split("def derive_timings")[1].split("\ndef ")[0]
# The bound is a SCOPE guard, not a style rule: derive_timings is ~5.7k characters
# because it carries the three auto-apply reasonings in full. What it must never be is
# the 39k the first version read. If this ever trips, the split stopped matching — fix
# the split, do not raise the number.
check(f"the wiring check reads derive_timings ONLY ({len(_derive)} chars)",
      len(_derive) < 9000, "the window is too wide to prove anything")
for _flag in ("--apply-broll", "--apply-wide", "--apply-hold"):
    check(f"providers.derive_timings passes {_flag}", _flag in _derive,
          "the tool can apply it and the build never asks it to")
check("  CONTROL: a flag that is NOT wired is reported as missing",
      "--apply-nonsense" not in _derive)

print()
print("=" * 78)
print("PART C - nothing already shipped moves")
print("=" * 78)
for name in ("PP-EP19-10-Systems-for-Action-Hungry-Punters-Part-1",
             "PP-EP20-Bill-Benter-Professional-Gambler",
             "PP-EP21-Track-Secrets-Part-1"):
    src = PP / name
    if not (src / "renders/aligned.srt").is_file():
        print(f"  ·  skipped {name[:34]} — not on this machine")
        continue
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "docs").mkdir(); (d / "renders").mkdir()
        for f in ("aligned.srt", "shot-map.json"):
            shutil.copy(src / "renders" / f, d / "renders" / f)
        raw = (src / "docs/episode.json").read_bytes()
        (d / "docs/episode.json").write_bytes(raw)
        rc, out = derive(d, "--apply-broll")
        check(f"{name[:30]} still derives clean", rc == 0, out[-300:])
        check(f"  and --apply-broll wrote NOTHING to it",
              (d / "docs/episode.json").read_bytes() == raw,
              "a shipped episode's episode.json was rewritten")

print()
print("=" * 78)
print(f"shot map flows: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    for n, w in FAIL:
        print(f"  - {n}")
    raise SystemExit(1)
