#!/usr/bin/env python3
"""_download_exact must refuse a SHORT file and accept a COMPLETE one.

Both halves, because this guard has now failed in both directions:

  EP15, 4 Aug — a genuinely short master LOOKED complete (faststart puts `moov`
    at the front, so ffprobe read the full duration off a truncated file). The
    guard was built for that and it works.

  EP18, 8 Aug — a COMPLETE hero LOOKED short. covers_ab halted three times with
    an identical count: stated 9,629,496, "arrived" 9,437,184 — EXACTLY 9 MiB.
    The download was perfect; `tmp.stat().st_size` on GOOGLE DRIVE'S VIRTUAL
    FILESYSTEM had simply not caught up with the write.

    🔴 stat() IS A PROXY. THE BYTES WE COUNTED THROUGH OUR OWN HANDS ARE NOT.

So the size now comes from the copy loop's running total, and this suite proves
the guard still refuses a short read — that the fix did not buy a green light by
going blind.

Run: python engine/test_download_exact.py
"""
from __future__ import annotations

import io
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

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


class Resp(io.BytesIO):
    """A urlopen() stand-in: some bytes, and a Content-Length that may lie."""

    def __init__(self, body: bytes, stated=None, omit_length=False):
        super().__init__(body)
        # ⚠️ omit_length is NOT the same as stated=None. The first version made
        # stated=None mean "use len(body)", so the "server states nothing" cases
        # were quietly testing a server that stated the right answer — and the
        # empty-body case passed because 0 == 0. A stub that fills in the value
        # under test is a stub that tests nothing.
        self.headers = {} if omit_length else {
            "Content-Length": str(len(body) if stated is None else stated)}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def run(body, stated, dest, omit_length=False):
    real = providers.urllib.request.urlopen
    providers.urllib.request.urlopen = lambda *a, **k: Resp(body, stated, omit_length)
    try:
        providers.RealProvider._download_exact(str("http://x/y"), dest)
        return None
    except providers.EngineFlag as f:
        return f
    finally:
        providers.urllib.request.urlopen = real


def main():
    tmp = Path(tempfile.mkdtemp(prefix="pp-dl-"))
    body = b"x" * 9_629_496

    print("\n-- 🔴 A COMPLETE FILE IS ACCEPTED (the EP18 fault) --")
    d = tmp / "hero-a.png"
    flag = run(body, 9_629_496, d)
    check("a full download is kept", flag is None, str(flag)[:100])
    check("  and it is on disk in full", d.is_file() and d.stat().st_size == len(body))
    check("  no .part is left behind", not (tmp / "hero-a.part").exists())

    print("\n-- 🔒 A SHORT FILE IS STILL REFUSED (the EP15 fault) --")
    d2 = tmp / "master.mp4"
    flag = run(b"y" * 78_947_138, 114_395_315, d2)
    check("a truncated download is refused", flag is not None)
    check("  and NOT promoted — nothing is on disk", not d2.exists(),
          "the short file became the artefact, which is EP15 exactly")
    msg = str(flag or "")
    check("  the message names both numbers", "114,395,315" in msg and "78,947,138" in msg)
    check("  and says nothing was kept", "not kept" in msg.lower())

    print("\n-- the size comes from the COPY, not from the filesystem --")
    # ⚠️ READ THE SYNTAX TREE. The first version of these three cases stripped
    # `#` lines and grepped the rest — and fired on the word "copyfileobj" in
    # this function's own DOCSTRING, which explains that copyfileobj is what it
    # replaced. That is CLAUDE.md fault 1a for the FOURTH time today, in a suite
    # written AFTER the law was added. Grepping source keeps finding the prose.
    import ast
    tree = ast.parse((HERE / "providers.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_download_exact")
    calls, attrs = set(), set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            calls.add(n.func.attr)
        if isinstance(n, ast.Attribute):
            attrs.add(n.attr)
    check("it counts bytes as it writes them",
          any(isinstance(n, ast.AugAssign) for n in ast.walk(fn)))
    check("  and never stats the .part for the size", "stat" not in calls,
          "stat() on Google Drive lags the write and reported 9 MiB for a "
          "complete 9.6 MB file — three halts on a perfect download")
    check("  copyfileobj is gone from the CODE (it hid the count)",
          "copyfileobj" not in calls, str(sorted(calls)))

    print("\n-- a server that states nothing, and an empty body --")
    d3 = tmp / "nolen.bin"
    check("no Content-Length + real bytes is accepted",
          run(b"z" * 1000, None, d3, omit_length=True) is None)
    d4 = tmp / "empty.bin"
    f4 = run(b"", None, d4, omit_length=True)
    check("no Content-Length + EMPTY is refused", f4 is not None)
    check("  and nothing is left on disk", not d4.exists())

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
