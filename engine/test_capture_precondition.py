#!/usr/bin/env python3
"""1a — the §4a capture is a precondition, and there is ONE lookup for it.

Piece 2 of docs/DESIGN-the-pre-claim-drafting-pass.md (invariant I3).

THE TWO FAULTS IT STANDS AGAINST, and they are different faults:

    one_glob_only        — the pattern was written inline inside
                           _commission_episode_json. Adding the script's own
                           precondition by COPYING it is fault #2 exactly: one
                           value in two places, and the fix reaching one reader.
                           This case greps the source and fails on a second copy.

    the_halt_is_for_a_person
                         — a studio halt that names a path, a glob or a file
                           extension is a halt written for the person who wrote
                           the code (A19 / docs/PP-operator-box-rule.md).

    ep01_does_not_match_ep10
                         — fault #0a, the glob that made two outro audits
                           confidently wrong. Closed by the SHAPE of the pattern,
                           so this case proves the shape rather than trusting it.

No real episode is touched: every case builds its own tree in a temp folder. One
case READS the real Drive to confirm the pattern matches what is actually there.

Run: python engine/test_capture_precondition.py
"""
from __future__ import annotations

import os
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

import providers                                                       # noqa: E402

PP_REAL = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def tree(*names) -> Path:
    """A throwaway PP-Videos-shaped folder holding the given capture files."""
    root = Path(tempfile.mkdtemp(prefix="pp-capture-"))
    (root / "docs").mkdir()
    for n in names:
        (root / "docs" / n).write_text("# A Headline\n", encoding="utf-8")
    return root


def halts(fn):
    try:
        fn()
    except providers.EngineFlag as e:
        return e
    return None


def main():                                                            # noqa: C901
    print("\n-- the capture is there --")
    root = tree("EP18-source-article-testing-the-numbers.md")
    found = providers.find_capture(root, 18)
    check("find_capture returns it", found is not None and found.name.startswith("EP18-"))
    got = providers.assert_capture_for_script(root, 18)
    check("  and the precondition passes, returning the same file", got == found)

    print("\n-- the capture is NOT there --")
    empty = tree()
    check("find_capture returns None", providers.find_capture(empty, 18) is None)
    e = halts(lambda: providers.assert_capture_for_script(empty, 18))
    check("  the precondition HALTS", e is not None)

    print("\n-- 🔴 THE HALT IS WRITTEN FOR A PERSON, NOT FOR ITS AUTHOR --")
    msg = str(e or "")
    print("     as it would be read:")
    for line in msg.splitlines():
        print(f"       | {line}")
    check("it says the article hasn't been captured",
          "hasn't been captured" in msg or "has not been captured" in msg)
    check("  it says nothing was written", "nothing has been written" in msg.lower())
    check("  it says plainly that retrying will not help",
          "retrying will not help" in msg.lower())
    for bad in ("/", "\\", ".md", ".py", "*", "glob", "EP", "docs", "{", "}", "_"):
        check(f"  it contains no {bad!r}", bad not in msg)
    check("  and no raw interpreter text", "Traceback" not in msg and "Error" not in msg)

    print("\n-- 🔴 ONE GLOB, NOT TWO (fault #2: one value in two places) --")
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    # ⚠️ COUNT THE CODE, NOT THE PROSE. The first version of this case counted the
    # substring across the whole file and failed at 3 — two of which were the
    # COMMENT explaining why the pattern is anchored. A guard that fires when
    # somebody documents the thing it guards is a guard that gets deleted, and it
    # is fault #1 in miniature: the count was a proxy for "a second lookup exists".
    code = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    n_glob = code.count("-source-article-")
    check("the capture pattern appears exactly ONCE in providers.py's CODE",
          n_glob == 1, f"found {n_glob} in code — a second lookup will drift")
    body = src.split("def find_capture")[1].split("\ndef ")[0]
    check("  and that once is inside find_capture", "-source-article-" in body)
    epj = src.split("def _commission_episode_json")[1].split("\n    def ")[0]
    check("  the episode.json commission calls the shared lookup",
          "find_capture(" in epj)
    check("  and no longer globs for itself", "-source-article-" not in epj)

    print("\n-- 🔴 EP01 DOES NOT MATCH EP10 (fault #0a, closed by the pattern) --")
    both = tree("EP01-source-article-the-first-one.md",
                "EP10-source-article-the-tenth-one.md")
    one = providers.find_capture(both, 1)
    ten = providers.find_capture(both, 10)
    check("EP1 resolves to EP01's capture", one is not None and "EP01-" in one.name,
          str(one))
    check("  EP10 resolves to EP10's capture", ten is not None and "EP10-" in ten.name,
          str(ten))
    check("  they are different files", one != ten)
    nine = tree("EP98-source-article-a-test-folder.md")
    check("  and EP9 does NOT pick up EP98's capture",
          providers.find_capture(nine, 9) is None)

    print("\n-- several matches resolve the same way every time --")
    many = tree("EP18-source-article-bbb.md", "EP18-source-article-aaa.md")
    picks = {providers.find_capture(many, 18).name for _ in range(5)}
    check("the pick is deterministic", len(picks) == 1, str(picks))
    check("  and it is the sorted-first one", picks == {"EP18-source-article-aaa.md"})

    print("\n-- against the REAL captures on Drive (read only) --")
    if (PP_REAL / "docs").is_dir():
        real = providers.find_capture(PP_REAL, 17)
        check("EP17's real capture is found by this pattern",
              real is not None and real.is_file(), str(real))
        check("  and it is EP17's, not a neighbour's",
              real is not None and real.name.startswith("EP17-source-article-"))
        missing = providers.find_capture(PP_REAL, 6)
        check("  an episode with no capture correctly returns None (EP06 has none)",
              missing is None)
    else:
        print("  --   skipped: PP Videos is not reachable from here")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
