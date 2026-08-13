"""test_web_copies.py — the low-res web copies ADD two files and change nothing else.

Jodie, 11 Aug 2026: low-res thumbnail + e-book cover for Hugh's website, EP20 onwards.
    "ADDITIVE ONLY. Never modify, move, shrink, or delete the existing full-size
     thumbnail, the cover, the ebook, or anything else already in the output/ebook
     folders."

So the acceptance test is not "did it write two files" — it is **did it write two
files AND leave every other byte in the episode folder exactly as it was**. That is
checked by hashing the whole tree before and after, which is the only version of the
claim that cannot be true-by-inspection-of-the-code.

It runs against a COPY of a real episode folder, never the real one.

Run: python engine/test_web_copies.py
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

import web_copies as wc                                          # noqa: E402
from PIL import Image                                            # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def episode_dir(n: int) -> Path:
    """BY NUMBER, never by a written-out name — stage-8 renames published folders."""
    hits = sorted(p for p in PP.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else PP / f"PP-EP{n:02d}"


def tree(d: Path) -> dict:
    """Every file under d, by relative path -> (size, sha256). The whole claim."""
    out = {}
    for p in sorted(d.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(d))] = (p.stat().st_size,
                                          hashlib.sha256(p.read_bytes()).hexdigest())
    return out


def stage(n: int, dst: Path) -> Path:
    """A COPY of the two source pictures in a real episode's shape. Nothing else is
    needed, and copying 100MB of video to test a resize would be silly."""
    src = episode_dir(n)
    ep = dst / src.name
    (ep / "output").mkdir(parents=True)
    (ep / "ebook").mkdir(parents=True)
    # THE STAGE-8 RENAME RESTEMS THE FILES, NOT ONLY THE FOLDER:
    # PP-EP20/output/PP-EP20-thumbnail.png became
    # PP-EP20-Bill-Benter-Professional-Gambler/output/
    #   PP-EP20-Bill-Benter-Professional-Gambler-thumbnail.png.
    # Rebuilding "PP-EP20" from the first two segments looked for a file that
    # stopped existing the day EP20 published, and the test then reported the
    # artefacts as "not built yet" — a stale path wearing a missing-input message.
    slug = src.name
    pairs = [(src / "output" / f"{slug}-thumbnail.png",
              ep / "output" / f"{slug}-thumbnail.png"),
             (src / "ebook/cover.png", ep / "ebook/cover.png")]
    for s, d in pairs:
        if not s.is_file():
            return None
        shutil.copyfile(s, d)
    # A few innocent bystanders, so "nothing else changed" has something to be about.
    (ep / "output" / f"{slug}-FINAL.mp4").write_bytes(b"not really a video" * 100)
    (ep / "output" / f"{slug}-ebook.pdf").write_bytes(b"%PDF-1.7 not really" * 100)
    (ep / "output" / f"{slug}-youtube.txt").write_text("a title\n", encoding="utf-8")
    (ep / "ebook" / f"{slug}-ebook-source.html").write_text("<html>", encoding="utf-8")
    return ep


def main():
    if not episode_dir(20).is_dir():
        print("EP20 is not on this machine — cannot run")
        return 1

    with tempfile.TemporaryDirectory() as td:
        ep = stage(20, Path(td))
        if ep is None:
            print("EP20's thumbnail or cover is not built yet — cannot run")
            return 1

        before = tree(ep)
        lines = wc.build(ep)
        after = tree(ep)

        print("-- it ADDS exactly two files --")
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        slug = ep.name          # restemmed by stage-8; see stage()
        want = sorted([f"output\\{slug}-thumbnail-lowres.jpg".replace("\\", os.sep),
                       f"output\\{slug}-cover-lowres.jpg".replace("\\", os.sep)])
        check("exactly two files appear", len(added) == 2, f"{added}")
        check("  and they are the two names Jodie specified", added == want,
              f"got {added}, wanted {want}")
        check("  nothing was removed", not removed, f"{removed}")

        print("\n-- and EVERY pre-existing file is byte-identical --")
        changed = [k for k in before if before[k] != after.get(k)]
        check("no pre-existing file changed by a single byte", not changed,
              f"{changed}")
        check("  including the full-size thumbnail it was made FROM",
              before[f"output{os.sep}{slug}-thumbnail.png"]
              == after[f"output{os.sep}{slug}-thumbnail.png"])
        check("  and the e-book cover",
              before[f"ebook{os.sep}cover.png"] == after[f"ebook{os.sep}cover.png"])
        check("  and the e-book PDF, the video and the YouTube copy",
              all(before[k] == after[k] for k in before
                  if k.endswith((".pdf", ".mp4", ".txt", ".html"))))

        print("\n-- the spec: ~640px longest edge, under ~100KB --")
        for rel in want:
            p = ep / rel
            with Image.open(p) as im:
                w, h = im.size
                fmt = im.format
            n = p.stat().st_size
            check(f"{Path(rel).name}: longest edge is {max(w, h)}px",
                  max(w, h) == wc.LONGEST_EDGE, f"{w}x{h}")
            check(f"  it is a JPEG, not a PNG", fmt == "JPEG", fmt)
            check(f"  {n/1000:.0f}KB is under ~{wc.SIZE_TARGET//1000}KB",
                  n <= wc.SIZE_TARGET, f"{n:,} bytes")

        print("\n-- aspect ratio is preserved, not squashed --")
        for src, dst in wc.targets(ep):
            with Image.open(src) as a, Image.open(dst) as b:
                ra, rb = a.size[0] / a.size[1], b.size[0] / b.size[1]
            check(f"{dst.name}: {a.size[0]}x{a.size[1]} -> {b.size[0]}x{b.size[1]}",
                  abs(ra - rb) < 0.01, f"aspect {ra:.4f} -> {rb:.4f}")

        print("\n-- .jpg keeps it out of every glob that scans these folders --")
        # ⚠️ THE ONE THAT WOULD HAVE BITTEN. qc_episode takes the LAST match of
        # output/*thumbnail*.png and hard-fails anything that is not 1280x720, so a
        # lowres PNG would have become "the thumbnail" and failed every episode.
        import glob as _g
        pngs = sorted(_g.glob(str(ep / "output" / "*thumbnail*.png")))
        check("output/*thumbnail*.png still matches only the full-size one",
              len(pngs) == 1 and pngs[-1].endswith(f"{slug}-thumbnail.png"),
              f"{[Path(p).name for p in pngs]}")
        with Image.open(pngs[-1]) as im:
            check("  and the one QC would pick is still 1280x720", im.size == (1280, 720),
                  f"{im.size}")
        check("output/*.pdf is unaffected",
              len(_g.glob(str(ep / "output" / "*.pdf"))) == 1)
        check("output/*youtube*.txt is unaffected",
              len(_g.glob(str(ep / "output" / "*youtube*.txt"))) == 1)

        print("\n-- running it twice is a no-op, not a second pair --")
        again = tree(ep)
        wc.build(ep)
        third = tree(ep)
        check("no new files on a re-run", set(third) == set(again),
              f"{sorted(set(third) - set(again))}")

        print("\n-- it never upscales a picture that is already small --")
        small = Path(td) / "small"
        (small / "output").mkdir(parents=True)
        (small / "ebook").mkdir(parents=True)
        tiny = small / "output/PP-EP99-thumbnail.png"
        Image.new("RGB", (320, 180), "red").save(tiny)
        Image.new("RGB", (200, 300), "blue").save(small / "ebook/cover.png")
        small_ep = Path(td) / "PP-EP99"
        shutil.move(str(small), str(small_ep))
        wc.build(small_ep)
        with Image.open(small_ep / "output/PP-EP99-thumbnail-lowres.jpg") as im:
            check("a 320x180 source stays 320x180", im.size == (320, 180), f"{im.size}")

        print("\n-- a missing source HALTS and says which one --")
        bare = Path(td) / "PP-EP98"
        (bare / "output").mkdir(parents=True)
        try:
            wc.build(bare)
            check("a missing picture halts", False, "it returned instead")
        except wc.Halt as e:
            check("a missing picture halts", True)
            check("  and names the file that is not there", "thumbnail.png" in str(e))

        print("\n-- the log line says what it did, for the run log --")
        check("each line names the size, the weight and the source",
              all("KB" in l and "<-" in l and "x" in l for l in lines), f"{lines}")

    print(f"\nweb copies: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
