"""SITTING 4a — the early e-book card is PLACED FROM THE SRT, never from a typed time.

Fail-first, end to end: the real derive_card_timings.py is run against a real episode's
files (EP18's, copied to a temp dir) with build.early_cta varied. A typed timestamp is
the EP15 `midroll.at = 235.0` fault waiting to happen, so the cases that matter are the
ones where the tool must REFUSE rather than guess.

Run: python engine/test_early_cta_timing.py
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
TOOL = REPO / ".claude/skills/pp-episode-production/scripts/derive_card_timings.py"
SRC = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP18")
PY = sys.executable

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


if not (SRC / "docs/episode.json").is_file():
    print("SKIP: EP18's files are not reachable, so there is nothing real to run against.")
    print("      (This suite deliberately uses a REAL episode — a hand-built fixture "
          "would be a lifecycle stage the tool never meets. CLAUDE.md 4a.)")
    sys.exit(0)


def run_with(early_cta):
    """Copy EP18 into a temp dir, set build.early_cta, run the tool, return stdout."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pp-cta-"))
    (tmp / "docs").mkdir()
    (tmp / "renders").mkdir()
    epj = json.loads((SRC / "docs/episode.json").read_text(encoding="utf-8"))
    if early_cta is None:
        epj["build"].pop("early_cta", None)
    else:
        epj["build"]["early_cta"] = early_cta
    (tmp / "docs/episode.json").write_text(json.dumps(epj, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
    for f in ("aligned.srt", "shot-map.json"):
        shutil.copyfile(SRC / "renders" / f, tmp / "renders" / f)
    r = subprocess.run([PY, str(TOOL), str(tmp)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout + r.stderr, tmp


ANCHOR = "One quick thing before we dig in"

print("\n=== FAIL FIRST: the tool must refuse, not guess ===\n")

out, _ = run_with({"clip": "end-card-template.mp4", "at": None, "dur": 6.0, "fade": 0.3})
check("early_cta with NO anchor is reported", "no `anchor`" in out,
      "a missing value must not quietly drop the card (A4)")
check("  and it says it is not guessing", "Not guessing" in out or "refusing to guess" in out)

out2, _ = run_with({"clip": "end-card-template.mp4", "anchor": "a line he never says",
                    "at": None, "dur": 6.0, "fade": 0.3})
check("an anchor that is not in the SRT is reported", "not in the SRT" in out2)
check("  and it names the phrase", "a line he never says" in out2)

print("\n=== and only now, the good case ===\n")

out3, tmp3 = run_with({"clip": "end-card-template.mp4", "anchor": ANCHOR,
                       "at": None, "dur": 6.0, "fade": 0.3})
m = re.search(r"early_cta\.at\s*:\s*([0-9.]+)", out3)
check("a real anchor places the card", m is not None, out3[-400:])
if m:
    at = float(m.group(1))
    # EP18's mention is spoken at 44.27 presenter; the card follows by 1.0s.
    check(f"  at = {at} — follows the mention by 1.0s", abs(at - 45.27) < 0.2,
          f"expected ~45.27, got {at}")
    check("  it is PRESENTER-clock, not final", at < 50,
          "final-clock would be ~52; the assembler adds title_head, not this tool")
check("ALL CHECKS PASS with the anchor set", "ALL CHECKS PASS" in out3, out3[-300:])

print("\n=== back-compat: episodes with no early_cta at all ===\n")
out4, _ = run_with(None)
check("no early_cta -> silent, no problem raised",
      "early_cta" not in out4 and "ALL CHECKS PASS" in out4,
      "EP11-EP17 carry no early_cta and must keep deriving cleanly")

print("\n=== --write puts the derived value in the file ===\n")
r = subprocess.run([PY, str(TOOL), str(tmp3), "--write"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
back = json.loads((tmp3 / "docs/episode.json").read_text(encoding="utf-8"))
wrote = (back["build"].get("early_cta") or {}).get("at")
check("--write persists early_cta.at", isinstance(wrote, (int, float)), str(wrote))
check("  and the anchor is left alone",
      (back["build"].get("early_cta") or {}).get("anchor") == ANCHOR)

print(f"\n{'=' * 66}")
print("EARLY CTA IS DERIVED, PROVED FAIL-FIRST" if not FAILED else f"FAILURES: {FAILED}")
sys.exit(1 if FAILED else 0)
