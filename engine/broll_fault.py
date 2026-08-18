#!/usr/bin/env python3
"""broll_fault.py — the b-roll fault tally. One command, one line, one denominator.

    python engine/broll_fault.py 31 --clean
    python engine/broll_fault.py 31 --faulty c02 --why "horses both sides of the rail"
    python engine/broll_fault.py 31 --faulty c02,c05 --why "identical stride"
    python engine/broll_fault.py --rate

WHY THIS EXISTS. EP30 shipped a clip with horses on both sides of the running rail and
the field in identical stride. Both rules were in the sent prompt, in positive form, on
all four clips — so the rules are not missing, they hold PROBABILISTICALLY. Three of
EP30's four clips were fine.

    AND THAT ONE-IN-FOUR IS A SINGLE OBSERVATION, BY EYE, ON ONE EPISODE.

There is no record of b-roll faults anywhere, so there is no rate — and the two real
fixes (generate two and keep one; inspect what comes back) cost credits and build time
across ~1,944 projected clips. Choosing between them on one data point is the expensive
guess this studio keeps avoiding. So: measure first, cheaply.

🔴 IT RECORDS THE REVIEW, NOT ONLY THE FAULT. A tally that only logs faults cannot
produce a rate, because a missing row is indistinguishable from an episode nobody looked
at, and the arithmetic silently treats "not reviewed" as "clean".

⚠️ BUT `--clean` IS AN OVERRIDE, NOT A DUTY, AND THAT MATTERS. Jodie's measure is how
many things Hugh must ATTEND to, not how many buttons he presses — and she has twice
refused a per-episode b-roll obligation. So the denominator comes from things that
already happen: **the fault file supplies the numerator** (a habit Jodie and Hugh already
keep), and **the four approvals supply the denominator** (an episode approved 4/4 is an
episode a human went through). `--clean` is for the case where somebody DID look and
there is no rail record of it.

🔴 AND THE RESULT IS A LOWER BOUND, BECAUSE APPROVAL IS NOT SCRUTINY. Approved 4/4 is
good evidence the episode was WATCHED and no evidence the b-roll was EXAMINED. EP23 was
approved 4/4, published on 13 Aug, and Hugh found horses on both sides of its running
rail on the 14th — the day after. So a fault-free row means "nothing was noticed", never
"nothing was there", and every number this file prints is the floor.

⚠️ THE DENOMINATOR IS NOT TYPED IN. The clip count comes from the episode's own
episode.json, so a human logging a fault never has to count anything — the one action
is naming the clip that was wrong. (Data is lifted, never re-typed.)

The file it writes is plain markdown, sorted, one row per episode, and is meant to be
read and hand-edited as easily as it is written. It only has to survive long enough to
give us a real denominator.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ep_paths import episode_dir                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

TALLY = HERE.parent / "docs" / "broll-fault-tally.md"
HEADER = """# B-ROLL FAULT TALLY

**One row per episode REVIEWED.** A missing row means nobody has looked yet — it does
NOT mean the episode was clean, and the rate below is computed over reviewed episodes
only. That distinction is the only reason this file is worth keeping.

Written by `engine/broll_fault.py`; hand-editing is fine, the format is the point.

    python engine/broll_fault.py 31 --clean
    python engine/broll_fault.py 31 --faulty c02 --why "horses both sides of the rail"
    python engine/broll_fault.py --rate

| episode | clips | faulty | which | what was wrong | reviewed |
|---|---|---|---|---|---|
"""
ROW = re.compile(r"^\|\s*(?:PP-)?EP(\d+)\s*\|", re.I)


def clip_count(n: int) -> int:
    """How many b-roll clips this episode has, from its OWN episode.json."""
    f = episode_dir(n) / "docs" / "episode.json"
    if not f.is_file():
        return 0
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:                                                  # noqa: BLE001
        return 0
    b = d.get("broll")
    items = (b.get("clips") if isinstance(b, dict) else b) or []
    return len(items)


def _rows(text: str) -> dict[int, str]:
    return {int(m.group(1)): ln for ln in text.splitlines() if (m := ROW.match(ln))}


def record(n: int, faulty: list[str], why: str) -> str:
    total = clip_count(n)
    if not total:
        print(f"  (warning: no b-roll clips found in EP{n}'s episode.json — the clip "
              f"count is recorded as 0 and the rate will ignore it)")
    today = _dt.date.today().isoformat()
    row = (f"| EP{n} | {total} | {len(faulty)} | {', '.join(faulty) or '—'} "
           f"| {why or '—'} | {today} |")
    text = TALLY.read_text(encoding="utf-8") if TALLY.is_file() else HEADER
    rows = _rows(text)
    was = rows.get(n)
    if was:
        text = text.replace(was, row)
        print(f"  replaced EP{n}'s existing row")
    else:
        text = text.rstrip("\n") + "\n" + row + "\n"
    TALLY.parent.mkdir(parents=True, exist_ok=True)
    TALLY.write_text(text, encoding="utf-8")
    return row


def rate() -> str:
    if not TALLY.is_file():
        return "no tally yet — nothing has been reviewed."
    eps = clips = bad = 0
    for ln in _rows(TALLY.read_text(encoding="utf-8")).values():
        cells = [c.strip() for c in ln.strip("|").split("|")]
        try:
            c, f = int(cells[1]), int(cells[2])
        except (IndexError, ValueError):
            continue
        eps, clips, bad = eps + 1, clips + c, bad + f
    if not clips:
        return f"{eps} episode(s) reviewed, no clips counted yet."
    pct = 100.0 * bad / clips
    out = [f"{bad} faulty of {clips} b-roll clips across {eps} reviewed episode(s) "
           f"— {pct:.1f}%, about 1 in {clips / bad:.0f}" if bad else
           f"0 faulty of {clips} clips across {eps} reviewed episode(s)"]
    # 🔴 IT IS A LOWER BOUND, AND EP23 IS THE PROOF. The denominator is episodes a human
    # went through at the four approvals — good evidence the episode was WATCHED, and no
    # evidence the b-roll was SCRUTINISED. EP23 was approved 4/4, published 13 Aug, and
    # Hugh found horses on both sides of its rail on the 14th. A fault-free row means
    # "nothing was noticed", never "nothing was there".
    out.append("  ⚠️ A LOWER BOUND, not the rate. A fault-free episode means nothing was "
               "NOTICED — EP23 was approved 4/4 and published, and its rail fault was "
               "found the next day.")
    out.append("  ⚠️ EP6–EP15 are not covered by the fault file: unknown, not clean, and "
               "not in the denominator.")
    if eps < 5:
        out.append(f"  ⚠️ {eps} episode(s) is NOT a rate yet. Revisit at ~5, as agreed.")
    # The one door this file must never be used to open. (Jodie, 5 and 14 Aug 2026.)
    out.append("  🔴 This measures the rate. It is NOT a case for a b-roll review step — "
               "that is settled: better prompts, never a human looking.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="record b-roll faults, one line per episode")
    ap.add_argument("episode", nargs="?", help="episode NUMBER, e.g. 31")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--clean", action="store_true", help="reviewed, nothing wrong")
    g.add_argument("--faulty", help="comma-separated clip ids, e.g. c02,c05")
    ap.add_argument("--why", default="", help="what was wrong, in a few words")
    ap.add_argument("--rate", action="store_true", help="print the running numbers")
    a = ap.parse_args(argv)

    if a.rate and not a.episode:
        print(rate())
        return 0
    if not a.episode:
        ap.error("name an episode number, or use --rate")
    if not (a.clean or a.faulty):
        ap.error("say --clean or --faulty; a review with neither records nothing, and "
                 "an episode with no row reads as 'not looked at yet'")
    n = int(re.sub(r"\D", "", a.episode))
    faulty = [c.strip() for c in (a.faulty or "").split(",") if c.strip()]
    if faulty and not a.why:
        ap.error("--faulty needs --why: 'c02' six months from now tells nobody what to fix")
    print("  " + record(n, faulty, a.why))
    print("  -> " + TALLY.as_posix())
    print(rate())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
