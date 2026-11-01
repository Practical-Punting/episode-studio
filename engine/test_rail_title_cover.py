#!/usr/bin/env python3
"""THE YOUTUBE TITLE AND THE E-BOOK COVER GO ON THE RAIL (Jodie, 1 Nov 2026).

The publishing workflow runs in a browser that cannot open a laptop file. It read the
YouTube title from line 1 of output\\<folder>-youtube.txt and rebuilt the e-book cover
from page 1 of the PDF. Migration 008 added `youtube_title` and `cover_lowres_url`;
the engine now fills them:

  · step_youtube_copy writes line 1 of the -youtube.txt, trimmed, NEVER re-cased, in
    the same update as the description;
  · step_web_copies uploads <folder>-cover-lowres.jpg to the fixed name
    episode-assets/PP-EPnn/PP-EPnn-cover-lowres.jpg and writes the URL. No file, or a
    failed upload, is a log line and an empty column — never a stopped build (her ruling).

CONTROL FIRST (CLAUDE.md 4b): the same checks are run against the two step functions
AS THEY ARE AT git HEAD — before this change — and must FAIL there. A check that also
passes on the old code proves nothing about the new.

REAL DATA: EP52's own -youtube.txt and output folder, read only. Nothing is uploaded and
nothing touches the rail — the provider and the rail are fakes.

Run: python engine/test_rail_title_cover.py
"""
from __future__ import annotations

import ast
import subprocess
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

import engine                                                          # noqa: E402
import providers                                                       # noqa: E402

PASS, FAIL = [], []

EP52_DIR = Path(r"G:\My Drive\PP Videos\PP-EP52-Getting-together-with-the-International-Experts-Part-4")
EP52_TXT = EP52_DIR / "output" / (EP52_DIR.name + "-youtube.txt")
EP52_TITLE = "Getting together with the International Experts - Part 4 | How to Win at Horse Racing"


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


class FakeProvider:
    def __init__(self, cover=None, cover_raises=None, youtube_file=None):
        self.cover, self.cover_raises, self.youtube_file = cover, cover_raises, youtube_file

    def build_web_copies(self, ep):
        return "web copies: (fake)"

    def publish_cover_lowres(self, ep):
        if self.cover_raises:
            raise self.cover_raises
        return self.cover

    def save_youtube_copy(self, ep):
        return str(self.youtube_file)


class Ctx:
    def __init__(self, provider):
        self.provider = provider
        self.ep = {"id": "x", "ep_number": 52}
        self.writes = []

    def ep_set(self, fields):
        self.writes.append(dict(fields))


def written(ctx, key):
    return [w[key] for w in ctx.writes if key in w]


def head_versions():
    """step_web_copies and step_youtube_copy exactly as committed at HEAD, bound to the
    live engine module's globals — the CONTROL."""
    src = subprocess.run(["git", "show", "HEAD:engine/engine.py"], cwd=HERE.parent,
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    tree = ast.parse(src)
    wanted = {"step_web_copies", "step_youtube_copy"}
    mod = ast.Module(body=[n for n in tree.body
                           if isinstance(n, ast.FunctionDef) and n.name in wanted],
                     type_ignores=[])
    ns = dict(engine.__dict__)
    exec(compile(mod, "<HEAD engine.py>", "exec"), ns)               # noqa: S102
    return ns["step_web_copies"], ns["step_youtube_copy"]


def run_checks(web_step, yt_step, label, quiet=False):
    """The behaviour Jodie asked for. Returns the number of checks that failed."""
    results = []

    def c(name, cond):
        results.append(cond)
        if not quiet:
            check(f"{label}: {name}", cond)

    url = "https://ydqzdzpyemrqttiyhpwp.supabase.co/storage/v1/object/public/episode-assets/PP-EP52/PP-EP52-cover-lowres.jpg"
    ctx = Ctx(FakeProvider(cover=url))
    web_step(ctx)
    c("a published cover's URL is written to cover_lowres_url",
      written(ctx, "cover_lowres_url") == [url])

    ctx = Ctx(FakeProvider(cover=None))
    try:
        web_step(ctx)
        ok = True
    except Exception:                                                 # noqa: BLE001
        ok = False
    c("no cover file: the step carries on and writes nothing to cover_lowres_url",
      ok and written(ctx, "cover_lowres_url") == [] and hasattr(ctx.provider, "publish_cover_lowres"))

    ctx = Ctx(FakeProvider(cover_raises=RuntimeError("upload refused")))
    try:
        web_step(ctx)
        ok = True
    except Exception:                                                 # noqa: BLE001
        ok = False
    c("a failed upload: the step carries on (never a stopped build)", ok)

    ctx = Ctx(FakeProvider(youtube_file=EP52_TXT))
    yt_step(ctx)
    c("youtube_title is EP52's line 1, exactly", written(ctx, "youtube_title") == [EP52_TITLE])
    c("  in the SAME update as youtube_copy",
      any("youtube_title" in w and "youtube_copy" in w for w in ctx.writes))
    return results.count(False)


def main():
    print("\n-- youtube_title_line: line 1, trimmed, never re-cased --")
    f = providers.youtube_title_line
    check("EP52's real file -> its title, exactly", f(EP52_TXT.read_text(encoding="utf-8")) == EP52_TITLE)
    check("lower case stays lower case (EP53's form)",
          f("Getting together with the international experts  - Part 5 | How to Win at Horse Racing\nx")
          == "Getting together with the international experts  - Part 5 | How to Win at Horse Racing")
    check("  and the double space inside it is kept (trimmed at the ENDS only)",
          "experts  - Part" in f("  Getting together with the international experts  - Part 5  \n"))
    check("CRLF line endings: no stray \\r", f("Title | X\r\nmore") == "Title | X")
    check("a byte-order mark is dropped", f("\ufeffTitle | X\nmore") == "Title | X")
    check("a blank line 1 -> empty (the step then writes nothing)", f("\n\nDESCRIPTION") == "")

    print("\n-- where the cover is, and where it goes --")
    got = providers.cover_lowres_file(EP52_DIR)
    check("EP52 (renamed folder): finds the file web_copies.py actually wrote",
          got.name == EP52_DIR.name + "-cover-lowres.jpg" and got.is_file(), str(got))
    with tempfile.TemporaryDirectory() as td:
        bare = Path(td) / "PP-EP99"
        check("a mid-build bare folder: PP-EP99-cover-lowres.jpg",
              providers.cover_lowres_file(bare).name == "PP-EP99-cover-lowres.jpg")
    check("the bucket name is fixed: PP-EP52/PP-EP52-cover-lowres.jpg",
          providers.cover_lowres_object({"ep_number": 52}) == "PP-EP52/PP-EP52-cover-lowres.jpg")
    check("  never the long folder name",
          "Getting" not in providers.cover_lowres_object({"ep_number": 52}))
    for cls in (providers.MockProvider, providers.RealProvider):
        check(f"{cls.__name__} has publish_cover_lowres", callable(getattr(cls, "publish_cover_lowres", None)))

    print("\n-- 🔴 CONTROL: the same checks against the steps AS AT git HEAD must FAIL --")
    old_web, old_yt = head_versions()
    n_old = run_checks(old_web, old_yt, "HEAD", quiet=True)
    check(f"the checks catch the old code ({n_old} of 5 fail on HEAD)", n_old >= 3,
          "the checks pass on code that never wrote either field — they prove nothing")

    print("\n-- the steps as they are now --")
    run_checks(engine.step_web_copies, engine.step_youtube_copy, "NOW")

    print(f"\nrail title + cover: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
