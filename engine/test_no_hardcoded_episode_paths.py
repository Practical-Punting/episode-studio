#!/usr/bin/env python3
"""No test may hard-code a bare episode folder name. A lint, and a fuse-detector.

⚠️ THE FAULT THIS EXISTS TO STOP, 3 Aug 2026. The stage-8 close-out renamed EP11, EP12
and EP13 — `PP-EP13` -> `PP-EP13-The-Ratings-Game-Part-1` — which is a rename the
standard REQUIRES of every published episode. **Three suites broke in the same minute**
(test_hand_steps, test_title_card, test_youtube_title), all for the same reason: each
had written the folder name out in full. They had passed for weeks. They would have gone
on passing right up until the process did the thing it is designed to do.

A test that assumes a name the process is designed to change is a test with a fuse in it.
The fix is `episode_dir(n)`: glob `PP-EP{n}*` and take the hit. This file makes sure the
next person cannot quietly go back to the literal.

Reads only this repo's own test sources — it is a lint, not a proof of behaviour.

⚠️ WHAT IT DELIBERATELY DOES NOT FLAG, and why. The first draft of this lint fired on
seven lines; **five of them were not faults.** `test_midroll_window.py` builds `PP-EP23`
and `PP-EP20` under a `tempfile.mkdtemp` root — folders it creates itself, which no
rename can reach. `test_board_bundle_a.mjs` passes a `PP-EP15` path to a string-to-URL
converter that never touches disk. **What makes a literal a fuse is that it reaches the
REAL filesystem**, so the lint is scoped to Python suites that reference the live Drive
root, which is exactly the three that broke. A lint that cries wolf is a lint someone
turns off.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

# `PP-EP13` followed by a path separator or a closing quote — i.e. the name USED as a
# whole folder. `PP-EP{n}*` (the glob in episode_dir) and `PP-EP14-youtube.txt` (a file
# inside a folder, stem never renamed) are both legal and must not trip.
LITERAL = re.compile(r"PP-EP\d+(?=[\\/\"'])")

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def scan(src, label="<source>"):
    """The predicate, on ONE source string. Importable, so it can be run against the
    versions of these files in git HEAD — proving a lint against the source you just
    fixed proves nothing at all."""
    if "PP Videos" not in src:
        return []                      # synthetic folders under a temp root — not a fuse
    hits = []
    for i, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith(("#", "//", "*")):
            continue                                       # a docstring may quote one
        if LITERAL.search(line):
            hits.append(f"{label}:{i}  {line.strip()[:88]}")
    return hits


def _no_literal_folder_names():
    hits = []
    for p in sorted(HERE.glob("test_*.py")):
        if p.name == Path(__file__).name:
            continue
        hits += scan(p.read_text(encoding="utf-8"), p.name)
    assert not hits, (
        "a test hard-codes an episode FOLDER name. The stage-8 rename will break it, "
        "and it will look like a code regression rather than a stale path.\n"
        "      Use episode_dir(n) — glob PP-EP{n}* — instead.\n      "
        + "\n      ".join(hits))


def _the_lint_can_actually_fail():
    """A lint that cannot fail is decoration — and one narrowed until it fires at
    nothing is worse, because it reads as a clean bill of health. Prove BOTH halves:
    the pattern catches the line that really broke, and the narrowing did not gut it."""
    bad = r'    ep = Path(r"G:\My Drive\PP Videos\PP-EP13")'
    assert LITERAL.search(bad), "the pattern does NOT catch the exact line that broke"
    good = [r'    hits = sorted(p for p in pp.glob(f"PP-EP{n}*") if p.is_dir())',
            r'    f = d / "output/PP-EP14-youtube.txt"',
            r'    SHIPPED = episode_dir(14) / "output/PP-EP14-youtube.txt"']
    for g in good:
        assert not LITERAL.search(g), f"the pattern false-positives on legal code: {g}"
    # the scope test, run over the REAL suites: at least one is in range, or the lint
    # is scanning nothing at all and its silence means nothing.
    in_range = [p.name for p in HERE.glob("test_*.py")
                if p.name != Path(__file__).name
                and "PP Videos" in p.read_text(encoding="utf-8")]
    assert len(in_range) >= 3, (
        f"the lint is only watching {in_range} — the three suites that broke "
        f"(hand_steps, title_card, youtube_title) must all be in scope")


def _every_suite_that_needs_one_has_it():
    """Any suite touching a real episode folder must define the resolver."""
    for p in sorted(HERE.glob("test_*.py")):
        src = p.read_text(encoding="utf-8")
        if "PP Videos" not in src or p.name == Path(__file__).name:
            continue
        assert "def episode_dir(" in src, \
            f"{p.name} reaches into PP Videos but has no episode_dir() resolver"


# Guarded so `scan()` can be IMPORTED without the suite running and calling sys.exit —
# which is exactly what killed the script that ran this predicate against git HEAD.
if __name__ == "__main__":
    case("no suite hard-codes a bare PP-EP<n> folder name", _no_literal_folder_names)
    case("the lint catches the line that broke, clears the legal shapes, and is in scope",
         _the_lint_can_actually_fail)
    case("every suite that reaches into PP Videos resolves by number",
         _every_suite_that_needs_one_has_it)

    print(f"\nhard-coded episode paths: {len(PASS)} passed, {len(FAIL)} failed")
    sys.exit(1 if FAIL else 0)
