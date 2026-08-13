"""THE END CARD IS PROVED BY THE DROP, NOT BY AN ABSOLUTE NUMBER. (EP23, 13 Aug 2026.)

Regression for the check that hard-failed EP23 three times at 87% with the end card
PLAINLY ON SCREEN, and that had passed EP22 by a single point of luma.

    EP22 sampled 69 -> PASSED, by one.     EP23 sampled 72 -> FAILED, by two.

Both numbers are the same standing asset composited over a presenter, so what the check
was really measuring was whatever happened to be BEHIND the card. EP22's own end card
sits at 72.1 steady — its pass was where the sample landed, not a healthier episode.

⚠️ EVERY NUMBER BELOW WAS MEASURED OFF THE REAL FILMS, not invented for the test:
    EP23  PP-EP23-FINAL.mp4  film 810-813s luma 129.4 -> 814s 71.5 -> 815-826s 75.1
    EP22  PP-EP22-FINAL.mp4  film ~501s    luma 119.9 -> 505.7s 69.0 -> 506.7s 71.8

Run: python engine/test_end_card_drop.py
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import qc_episode as q          # noqa: E402

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


# ── 1. THE THING JODIE ASKED FOR: a genuinely-present end card PASSES ──────────
print("\nan end card that IS there passes")

v, drop = q.end_card_verdict(129.4, 71.5)
check("EP23 (the episode this fixed) passes", v == "ok",
      f"verdict {v!r}, drop {drop}")
check("EP23 passes ON THE DROP, not on the old threshold",
      drop is not None and drop >= q.END_CARD_DROP_MIN and 71.5 > q.END_CARD_DARK_MAX,
      f"drop {drop}, luma 71.5 vs dark-max {q.END_CARD_DARK_MAX}")

v, drop = q.end_card_verdict(119.9, 69.0)
check("EP22 (which shipped) still passes", v == "ok", f"verdict {v!r}, drop {drop}")

# EP22's steady state, which the old check would have failed had it sampled 1s later.
v, _ = q.end_card_verdict(119.9, 72.1)
check("EP22 at its STEADY luma 72.1 passes too", v == "ok",
      "the old check passed EP22 only by where the sample landed")

# ── 2. FAIL-FIRST: the check must still catch a missing end card ───────────────
print("\nan end card that is NOT there still fails")

v, drop = q.end_card_verdict(129.4, 129.4)
check("card absent (nothing changed) fails", v == "fail", f"verdict {v!r}")

v, _ = q.end_card_verdict(130.0, 118.0)
check("card barely dims the frame (12) fails", v == "fail",
      "a 12-point dip is not a card landing")

v, _ = q.end_card_verdict(129.4, 71.5 + 40)
check("presenter still bright under a 'card' fails", v == "fail")

# ── 3. THE SECOND WAY TO PASS, and that it is never a way to FAIL ──────────────
print("\ndark-on-its-own is a second way to pass, never a way to fail")

v, drop = q.end_card_verdict(64.0, 60.0)
check("dark run-up + dark frame passes on the absolute test", v == "ok",
      f"verdict {v!r}, drop {drop} (below drop-min, but the frame is dark)")

v, _ = q.end_card_verdict(None, 55.0)
check("no baseline + a dark frame passes", v == "ok")

# ── 4. UNKNOWABLE IS A WARN, NEVER A SILENT PASS AND NEVER A HARD FAIL ─────────
print("\nwhat it cannot measure, it says so about")

v, _ = q.end_card_verdict(None, 129.0)
check("no baseline + a bright frame WARNS (does not fail)", v == "warn",
      "cannot tell -> ask for eyes, do not brick the build")

v, _ = q.end_card_verdict(129.0, None)
check("unsamplable frame warns", v == "warn")

# ── 5. THE OLD RULE WOULD HAVE FAILED EP23 — the regression is real ────────────
print("\nthe fault this closes")

check("the OLD rule (luma > 70) fails EP23", 71.5 > 70.0,
      "if this stops being true the test below proves nothing")
check("the NEW rule passes the same frame", q.end_card_verdict(129.4, 71.5)[0] == "ok")
check("EP22 and EP23 were 3 luma apart and got opposite verdicts under the old rule",
      69.0 <= 70.0 < 71.5, "the coin toss this replaces")

# ── 6. AGAINST THE REAL FILM, when it is there (never a skip in silence) ───────
print("\nagainst the real film")

import ep_paths as _ep          # stage-8 renames the folder AND restems the file
_d = _ep.episode_dir(23)
final = _d / "output" / f"{_d.name}-FINAL.mp4"
if not final.is_file():
    print(f"  SKIP  {final.name} not on this machine — the rule is proved above")
else:
    ec_ti = 813.04                       # beat 39 start + endcard_lead, in film time
    base = q._end_card_baseline(str(final), ec_ti)
    luma = q._mean_luma(str(final), ec_ti + 1.0)
    check("baseline sampled from the real film", base is not None)
    check("end-card frame sampled from the real film", luma is not None)
    if base is not None and luma is not None:
        v, drop = q.end_card_verdict(base, luma)
        print(f"        measured: run-up {base:.1f} -> card {luma:.1f} (drop {drop:.1f})")
        check("THE REAL EP23 FILM PASSES", v == "ok", f"verdict {v!r}")
        check("and it passes on the drop, as designed", drop >= q.END_CARD_DROP_MIN)

print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
