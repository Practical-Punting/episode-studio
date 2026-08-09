"""SITTING 5a — THE CLOCK AUDIT. Every placed time must cross presenter->final ONCE.

THE FAULT THIS EXISTS FOR (EP18, 8 Aug 2026): `episode.json` times are PRESENTER-clock
— t=0 is Gordon's first word, because that is what aligned.srt measures. The finished
file prepends `title_head`. Cards cross over through `bs()`, which adds it.
`midroll.at` and `early_cta.at` were read RAW by BOTH assemble_episode.py AND
qc_episode.py, so both overlays sat SEVEN SECONDS before the words they belong to —
and the checker carried the same error, so it agreed with the assembler. Two green
checks, one wrong picture, found by a human watching the video.

    A TIME IS NOT A NUMBER. IT IS A NUMBER IN A FRAME.

HOW THIS AUDITS IT — behaviourally, not by reading the source. Emit the real Pass B
graph twice with DIFFERENT title_head values and compare every `setpts=PTS+t/TB[label]`
in it. Everything a viewer sees is anchored to Gordon's speech, so every one of those
times MUST move by exactly the delta. A time that does not move is a time that never
crossed the conversion — whatever it is called, whoever added it, however new it is.

That is why this is behavioural: a static rule would have to know the name of every
overlay, and the next overlay is by definition the one it does not know.

Run: python engine/test_clock_audit.py
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
SCRIPTS = REPO / ".claude/skills/pp-episode-production/scripts"
TOOL = SCRIPTS / "assemble_episode.py"
def _ep_dir(n: int) -> pathlib.Path:
    """Resolve an episode folder BY NUMBER, never by a written-out name.

    ⚠️ THE STAGE-8 CLOSE-OUT RENAMES EVERY PUBLISHED EPISODE'S FOLDER — PP-EP18 became
    PP-EP18-Those-Top-6-Favourites the day the close-out was automated — so a literal
    path is a fuse: it passes for weeks and then SKIPS, silently, the day the process
    does the thing the standard requires of it.
    """
    root = pathlib.Path(r"G:\My Drive\PP Videos")
    hits = sorted(p for p in root.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else root / f"PP-EP{n:02d}"


SRC = _ep_dir(18)
PY = sys.executable
FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


if not (SRC / "docs/episode.json").is_file():
    print("SKIP: EP18's files are not reachable; nothing real to audit against.")
    sys.exit(0)

PLACED = re.compile(r"setpts=PTS\+([0-9.]+)/TB\[([A-Za-z0-9_]+)\]")


def fixture():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pp-clock-"))
    (tmp / "docs").mkdir()
    (tmp / "renders").mkdir()
    shutil.copyfile(SRC / "docs/episode.json", tmp / "docs/episode.json")
    for f in ("aligned.srt", "shot-map.json"):
        shutil.copyfile(SRC / "renders" / f, tmp / "renders" / f)
    return tmp


def graph_times(tmp, head, tool=TOOL):
    """{label: placed_time} out of the REAL emitted Pass B graph."""
    p = tmp / "docs/episode.json"
    epj = json.loads(p.read_text(encoding="utf-8"))
    epj["build"]["title_head"] = head
    # early_cta needs an `at` to be placed at all; give it one in presenter-clock.
    if epj["build"].get("early_cta"):
        epj["build"]["early_cta"]["at"] = 46.0
    p.write_text(json.dumps(epj, indent=2, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([PY, str(tool), str(p), str(tmp / "renders/shot-map.json"), "B"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(tmp))
    if r.returncode != 0:
        print(f"    graph emit failed: {r.stderr[:400]}")
        return {}
    return {lbl: float(t) for t, lbl in PLACED.findall(r.stdout)}


print("\n=== the real assembler: every placed time must follow the head ===\n")
tmp = fixture()
a = graph_times(tmp, 7.0)
b = graph_times(tmp, 11.0)
check("the graph places things at all", len(a) >= 5, f"{sorted(a)}")
check("both runs place the SAME set of things", set(a) == set(b),
      f"{sorted(set(a) ^ set(b))}")

DELTA = 4.0
# THE ONE LEGITIMATE EXCEPTION, NAMED WITH ITS REASON RATHER THAN SKIPPED QUIETLY.
# `cdT` is the title card. It does not illustrate anything Gordon says — it IS the head,
# the silent run-in the head exists to hold, and it is anchored at 0.00 in the finished
# file by definition. A time that is genuinely final-clock is allowed not to move; a
# time that is SUPPOSED to be presenter-clock and does not move is the bug. Anything
# added to this set needs the same kind of sentence.
FINAL_CLOCK_BY_DESIGN = {"cdT"}
stuck, moved, fixed = [], [], []
for lbl in sorted(set(a) & set(b)):
    d = round(b[lbl] - a[lbl], 2)
    if lbl in FINAL_CLOCK_BY_DESIGN:
        fixed.append((lbl, a[lbl], b[lbl], d))
    else:
        (moved if abs(d - DELTA) < 0.011 else stuck).append((lbl, a[lbl], b[lbl], d))
for lbl, x, y, d in fixed:
    print(f"        {lbl:5s} {x:8.2f} -> {y:8.2f}   +{d}  (final-clock by design)")
check("the title card really is anchored at 0.00",
      all(x == 0.0 and y == 0.0 for _l, x, y, _d in fixed),
      "if it ever moves, the exception above is wrong and must be re-argued")
for lbl, x, y, d in moved:
    print(f"        {lbl:5s} {x:8.2f} -> {y:8.2f}   +{d}")
for lbl, x, y, d in stuck:
    print(f"     🔴 {lbl:5s} {x:8.2f} -> {y:8.2f}   +{d}  DID NOT FOLLOW THE HEAD")
check("EVERY placed time moved by exactly the head delta", not stuck,
      f"{[s[0] for s in stuck]} never crossed presenter->final")
check("  and that is more than one overlay's worth", len(moved) >= 5, f"{len(moved)}")

print("\n=== FAIL FIRST: plant an overlay that skips the conversion ===\n")
# A copy of the assembler with ONE line reverted to the EP18 bug: read `at` raw.
broken_dir = pathlib.Path(tempfile.mkdtemp(prefix="pp-clock-bad-"))
for f in SCRIPTS.glob("*.py"):
    shutil.copyfile(f, broken_dir / f.name)
shutil.copytree(SCRIPTS.parent / "assets", broken_dir.parent / "assets", dirs_exist_ok=True)
bad = broken_dir / "assemble_episode.py"
src = bad.read_text(encoding="utf-8")
needle = 'ct = round(CTA["at"] + HEAD, 2)'
check("the line the bug lived on is still recognisable", needle in src,
      "if this fails the audit below is testing nothing")
bad.write_text(src.replace(needle, 'ct = CTA["at"]'), encoding="utf-8")

tmp2 = fixture()
a2 = graph_times(tmp2, 7.0, tool=bad)
b2 = graph_times(tmp2, 11.0, tool=bad)
stuck2 = [lbl for lbl in sorted(set(a2) & set(b2))
          if lbl not in FINAL_CLOCK_BY_DESIGN
          and abs(round(b2[lbl] - a2[lbl], 2) - DELTA) >= 0.011]
print(f"        times that did not follow: {stuck2}")
check("the audit CATCHES an overlay read in the wrong clock", stuck2 == ["cta"],
      f"expected ['cta'], got {stuck2}")
check("  and everything else still passed, so it is specific",
      len(set(a2) & set(b2)) - len(stuck2) >= 5)

print("\n=== qc_episode must read `at` in the same clock as the assembler ===\n")
# The checker had the IDENTICAL bug on the matching line, which is why it agreed with
# the assembler instead of catching it. Read the syntax tree: every `["at"]` read that
# feeds a window must have `head` in the same expression.
import ast                                                            # noqa: E402
qsrc = (SCRIPTS / "qc_episode.py").read_text(encoding="utf-8")
qtree = ast.parse(qsrc)
bad_reads = []
for node in ast.walk(qtree):
    if not isinstance(node, ast.Assign):
        continue
    seg = ast.get_source_segment(qsrc, node) or ""
    if '"at"' not in seg and "'at'" not in seg:
        continue
    if "head" not in seg:
        bad_reads.append(seg.strip().splitlines()[0][:90])
check("no `at` is turned into a window without `head`", not bad_reads, str(bad_reads))

print(f"\n{'=' * 70}")
print("CLOCK AUDIT PROVED (and watched to fail)" if not FAILED else f"FAILURES: {FAILED}")
sys.exit(1 if FAILED else 0)
