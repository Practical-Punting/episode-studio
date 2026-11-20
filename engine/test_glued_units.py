#!/usr/bin/env python3
"""EP63 — A UNIT STUCK TO A NUMBER IS STILL THAT NUMBER.

    python engine/test_glued_units.py

EP63 "Timely Tips (Part 2)" stopped at script writing on 20 Nov 2026. The article prints
times the way racing pages do — "1m 9.3s into 1m 11.1s", "45.8s down to 45.2s" — and the
writer said them aloud, correctly. The figure check said the article "never states" nine
point three, eleven point one, forty-six, forty-five point eight or forty-five point two,
and the hook check refused the approved hook said as words. The writer stopped rather
than damage the script. IT WAS RIGHT.

  (a) "9.3s" read as "nine point threes" — the "s" welded to the last digit — and
      "1m 9.3s" read as one METRE nine point threes.
  (b) The hook gate compared ONE fold of the hook letter for letter, so "a 1m 9.3s run"
      could never be said "a one minute nine point three second run".

Jodie's list of styles from upcoming episodes (20 Nov 2026) is tested too, so they do
not hit the same wall: 1m 9.3s, 45.8s, 1m 34s, 1.08.56, 2.00.6, 33.40, 4.5 lengths, $50,
1x5x11, 56.5 kg.

🔒 Every "still blocks" case proves the gate did not get wider: a WRONG value in the
same style is still refused.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import script_fidelity as F                                            # noqa: E402
import episode_rulings as R                                            # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


CAP = """# A RACE-TIMES FIXTURE

---- ARTICLE TEXT BEGINS ----

# TIMELY TIPS (TEST FIXTURE)

Just 1.5 kg extra can turn a 1200m run of 1m 9.3s into 1m 11.1s.

The leader ran anywhere from 45.8s down to 45.2s. Faster than 45.2s and they were
beaten; at 46s or slower they won.

The mile went in 1m 34s. The track record is 1.08.56 and the 2000m took 2.00.6.

He clocked 33.40 for the last 600m and won by 4.5 lengths.

A $50 bet on a 1x5x11 trifecta, carrying 56.5 kg.

---- ARTICLE TEXT ENDS ----
"""


def says(phrase):
    return F.check("Gordon says " + phrase + " here.", CAP, "")


print("\n-- the styles, said aloud, PASS --")
for p in ("one minute nine point three seconds",
          "a one minute nine point three second run",
          "one minute eleven point one seconds",
          "forty-five point eight seconds down to forty-five point two seconds",
          "faster than forty-five point two seconds",
          "forty-six seconds or slower",
          "one minute thirty-four seconds",
          "one minute eight point five six seconds",
          "one oh eight point five six",
          "two minutes zero point six seconds",
          "thirty-three point four zero",
          "thirty-three point four oh",
          "four point five lengths",
          "four and a half lengths",
          "fifty dollars",
          "a fifty dollar bet",
          "a one by five by eleven trifecta",
          "fifty-six point five kilos",
          "fifty-six and a half kilos"):
    got = says(p)
    check(f"🔴 '{p}' PASSES", got == [], str(got)[:300])

print("\n-- a WRONG value in the same style still BLOCKS --")
for p in ("one minute nine point four seconds",
          "forty-five point nine seconds",
          "forty-seven seconds or slower",
          "one minute thirty-five seconds",
          "one minute eight point five seven seconds",
          "two minutes zero point seven seconds",
          "thirty-three point five",
          "four point six lengths",
          "sixty dollars",
          "a one by five by thirteen trifecta",
          "fifty-seven and a half kilos"):
    got = says(p)
    check(f"🔒 '{p}' still BLOCKS", got != [], "the gate let a wrong figure through")

print("\n-- the hook gate reads the hook the way it is SAID --")
HOOK = "One and a half kilos can turn a 1m 9.3s run into 1m 11.1s. Here's how weight, lengths and time fit together."
EP = {"hook": HOOK, "script_notes": ""}
OPEN = ("One and a half kilos can turn a one minute nine point three second run into one minute "
        "eleven point one seconds. Here's how weight, lengths and time fit together. ")
hook_bad = [x for x in R.check(OPEN + "Then the article.", CAP, EP) if "approved hook" in x]
check("🔴 EP63's hook said as words opens the script — no hook complaint", hook_bad == [], str(hook_bad)[:300])
wrong = OPEN.replace("nine point three", "nine point four")
check("🔒 the hook with a WRONG figure still BLOCKS",
      any("approved hook" in x for x in R.check(wrong + "Then the article.", CAP, EP)))
check("🔒 anything BEFORE the hook still BLOCKS",
      any("approved hook" in x for x in R.check("Hello there. " + OPEN, CAP, EP)))
other = OPEN.replace("Here's how weight", "Here's why weight")
check("🔒 a changed WORD in the hook still BLOCKS",
      any("approved hook" in x for x in R.check(other, CAP, EP)))

print("\n-- the real EP63 draft against the real article --")
cap = next(iter(sorted((PP / "docs").glob("EP63-source-article-*.md"))), None)
draft = PP / "PP-EP63" / "docs" / "spoken-words.txt"
if cap and draft.is_file():
    import rail                                                        # noqa: E402
    row = rail._request("GET", "?select=hook,byline,script_notes,ep_number&ep_number=eq.63")[0]
    lic = " \n ".join(b for b in [row["hook"] or "", row["byline"] or "",
                                  f"episode {row['ep_number']}", R.licensed_notes(row)] if b.strip())
    c, t = cap.read_text(encoding="utf-8"), draft.read_text(encoding="utf-8")
    fig = F.check(t, c, lic)
    rul = R.check(t, c, row)
    check("🔴 EP63's real 1,262-word draft: no figure blockers", fig == [], str(fig)[:300])
    check("🔴 EP63's real draft: no rulings blockers (hook, leave-out)", rul == [], str(rul)[:300])
else:
    print("  (skipped: EP63's capture or draft is not on this machine)")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
