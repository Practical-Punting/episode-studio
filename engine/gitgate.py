"""gitgate.py — refuse to run on code that isn't exactly what is committed.

REPLACES the two `.reference.py` byte-comparison gates (28 Jul 2026).

WHY THE GATES EXISTED
`rail.py` carries the Script Gate's claim filter — the check that refuses to hand
out an episode nobody has read the script for. `qc_episode.py` decides whether a
finished episode is good enough to ship. Both used to live on Google Drive,
OUTSIDE version control, where a *revert* would disable the guarantee SILENTLY:
the engine keeps running, the board still looks healthy, and nothing says a word.

So the repo carried a byte-for-byte reference copy of each, and the engine
compared the live file against it before use.

WHY THAT MECHANISM IS NOW GONE
Both files are in the repo (28 Jul 2026, "code in GitHub, media on Drive"). A
checked-in copy of a file that lives three directories away IN THE SAME COMMIT
proves nothing that git does not already prove — and it cost real safety:

  * The duplicate had to be updated in the SAME COMMIT or every build died.
    Easy to forget; it nearly bit us on the midroll-window change.
  * It could be DEFEATED BY EDITING BOTH COPIES. The gate compared two files to
    each other, not either of them to a reviewed baseline.

Comparing the working file to **git HEAD** is strictly stronger:

  * It catches an UNCOMMITTED local edit — the actual risk — which the old gate
    could not see at all.
  * It cannot be defeated without committing, and a commit leaves a permanent,
    attributable record. That is the whole point.
  * There is no duplicate to keep in sync.

WHY `git status --porcelain` AND NOT A BYTE COMPARE
`core.autocrlf = true` on this machine. Git stores LF and checks out CRLF, so a
raw byte comparison of the working file against `git show HEAD:<path>` would
MISMATCH ON EVERY RUN. (That trap is why `.gitattributes` marks the old
reference files `-text`.) `git status --porcelain` applies git's own clean
filters before comparing, so it is immune to line-ending conversion — and it
catches modified, staged-not-committed, deleted AND untracked in one call.

FAIL CLOSED, ALWAYS
Missing git, not a repo, unreadable file, dirty file — every doubt stops the
engine. There is no bypass flag and no environment variable. `--mock` does NOT
skip the rail gate (mock still writes to the real rail).

WHAT THIS DOES NOT PROTECT
The gate cannot gate itself, and it cannot gate `engine.py` or `providers.py`
either — the same was true of the mechanism it replaces. It protects the two
files whose silent weakening would let a bad episode through.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent


def _die(gate: str, reason: str, detail: str, why: str, code: int):
    """The ONE exit path from a gate. Always fatal; never returns."""
    print("=" * 72, file=sys.stderr)
    print(f"{gate} FAILED — refusing to run.", file=sys.stderr)
    print(reason, file=sys.stderr)
    if detail:
        print(detail, file=sys.stderr)
    print(f"\n{why}\n"
          "Fix: commit the change deliberately (so it is reviewable and\n"
          "attributable), or restore the file with:\n"
          "    git restore <path>", file=sys.stderr)
    print("=" * 72, file=sys.stderr)
    raise SystemExit(code)


def assert_committed(rel_path: str, gate: str, why: str, code: int) -> str:
    """Refuse to continue unless rel_path is tracked and identical to HEAD.

    rel_path is repo-relative with forward slashes. Returns the HEAD blob sha
    on success; on any doubt at all it never returns.
    """
    target = REPO_DIR / rel_path
    if not target.is_file():
        _die(gate, f"The file is missing:\n  {target}", "", why, code)

    def git(*args):
        return subprocess.run(["git", "-C", str(REPO_DIR), *args],
                              capture_output=True, text=True, timeout=60)

    try:
        r = git("rev-parse", "--is-inside-work-tree")
    except FileNotFoundError:
        _die(gate, "git is not on PATH, so I cannot verify this file is the "
                   "reviewed version.", "", why, code)
    except Exception as e:      # timeout, permissions, anything
        _die(gate, f"Couldn't run git to verify the file: {e}", "", why, code)
    if r.returncode != 0 or r.stdout.strip() != "true":
        _die(gate, f"Not a git working tree:\n  {REPO_DIR}",
             (r.stderr or "").strip(), why, code)

    r = git("status", "--porcelain", "--", rel_path)
    if r.returncode != 0:
        _die(gate, f"git status failed for {rel_path}", (r.stderr or "").strip(),
             why, code)
    dirty = r.stdout.strip()
    if dirty:
        state = {"??": "is UNTRACKED — it has never been committed",
                 " M": "has UNCOMMITTED CHANGES",
                 "M ": "is STAGED but NOT COMMITTED",
                 "MM": "is STAGED and further MODIFIED",
                 " D": "has been DELETED from the working tree",
                 "AM": "is newly ADDED and modified"}.get(dirty[:2], "DIFFERS from HEAD")
        _die(gate, f"{rel_path} {state}.",
             f"  git status: {dirty}\n  path      : {target}", why, code)

    r = git("rev-parse", f"HEAD:{rel_path}")
    if r.returncode != 0:
        _die(gate, f"{rel_path} is not present in HEAD.", (r.stderr or "").strip(),
             why, code)
    return r.stdout.strip()
