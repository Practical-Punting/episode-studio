#!/usr/bin/env python3
"""A card in the wrong frame is not a wording problem, and must not be handed over as one.

    python engine/test_layout_rescue.py

🔴 EP23 C21, 12 Aug 2026. "Benalla and Tatura" would not fit at the 60% floor, so the
build halted and asked a human to choose "between the words and the layout". Tightening
was tried first and could never have worked: the cell block is BOTTOM-ANCHORED, so a
shorter value made the block shorter (177px -> 110px) while its bottom edge stayed at
y=966 to the pixel, still under a logo chip starting at y=959. The card was authored
`fullscreen`; its five sibling minor-track slates in the same episode were all
`panel-push`. In panel-push it fits at FULL SIZE without one word changing.

Same shape as the b-roll fix: the tool can TRY the other frame and MEASURE the answer,
so stopping to ask is the waste. Making a card consistent with its siblings is not a
design choice.

⚠️ THE CASES THAT MATTER ARE THE REFUSALS. A rescue that quietly reshapes an episode is
worse than the halt it replaces, so this asserts what it will NOT do: no marginal fits,
no word changes, and a refused rescue must leave the episode byte-for-byte as it found
it — including the page on disk, not just episode.json.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPTS = REPO / ".claude/skills/pp-episode-production/scripts"
PP = Path(r"G:\My Drive\PP Videos")
import ep_paths as _ep                      # renamed on publish; resolve by NUMBER
SRC = _ep.episode_dir(23, PP)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def check(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


def run(script, *args, timeout=900):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *[str(a) for a in args]],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def stage(tmp, mutate=None):
    """A working copy of EP23 the author can actually author into.

    The source article is resolved from episode.json -> source, looked for beside the
    episode AND one level up, so it is copied to both — a scratch tree that cannot
    author would make every case below pass for the wrong reason.
    """
    d = Path(tmp) / "PP-EP23"
    (d / "docs").mkdir(parents=True)
    shutil.copytree(SRC / "overlay/export", d / "overlay/export")
    epj = json.loads((SRC / "docs/episode.json").read_text(encoding="utf-8"))
    if mutate:
        mutate(epj)
    (d / "docs/episode.json").write_text(json.dumps(epj, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    for art in PP.glob("docs/EP23-source-article-*.md"):
        (Path(tmp) / "docs").mkdir(exist_ok=True)
        shutil.copy(art, Path(tmp) / "docs" / art.name)
        shutil.copy(art, d / "docs" / art.name)
    return d


def author(d, cid):
    return run("author_cards.py", d / "docs/episode.json", d / "overlay/export",
               "--only", cid, "--force")


def autofit(d, only=None):
    args = [d / "overlay/export", "--dry-run"]
    if only:
        args[1:1] = ["--only", only]
    return run("autofit_cards.py", *args)


def layout_of(d, cid):
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    return next(c for c in epj["cards"] if c["id"] == cid)["layout"]


HAVE = (SRC / "docs/episode.json").is_file()
if not HAVE:
    print("EP23 is not on this machine — cannot run")
    raise SystemExit(2)

def to_fullscreen(e):
    next(c for c in e["cards"] if c["id"] == "C21")["layout"] = "fullscreen"


print("=" * 74)
print("PART A - EP23 C21: the real halt, rescued")
print("=" * 74)
with tempfile.TemporaryDirectory() as t:
    d = stage(t, to_fullscreen)
    rc_a, out_a = author(d, "C21")
    check("CONTROL: the scratch tree can author (or every case below is hollow)",
          rc_a == 0, out_a.strip()[-200:])
    _rc, out = autofit(d, "c21")
    check("CONTROL: as fullscreen it does NOT fit at the floor",
          "1 still failing" in out, out.strip()[-200:])

    before_page = (d / "overlay/export/ep23-c21-benalla-and-tatura.html").read_text(
        encoding="utf-8")
    rc_r, out_r = run("layout_rescue.py", d, "--apply")
    check("the rescue swaps it", "SWAPPED  C21" in out_r, out_r.strip()[-300:])
    check("  to its siblings' frame", layout_of(d, "C21") == "panel-push",
          layout_of(d, "C21"))
    check("  and says it fits at full size with no shrinking",
          "zero shrink steps" in out_r)
    _rc2, out2 = autofit(d, "c21")
    check("  and it really does — 0 fitted, 0 failing",
          "AUTOFIT: 0 fitted, 0 still failing" in out2, out2.strip()[-200:])

    # NOT ONE WORD CHANGED — asserted on the rendered pages, not on intent.
    import re as _re
    def words(h):
        b = _re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=_re.S | _re.I)
        return " ".join(_re.sub(r"<[^>]+>", " ", b).split())
    after_page = (d / "overlay/export/ep23-c21-benalla-and-tatura.html").read_text(
        encoding="utf-8")
    check("  and NOT ONE WORD CHANGED on the rendered page",
          words(before_page) == words(after_page))
    for fact in ("1880 m", "400 m home straight", "1600 m", "445 m home straight",
                 "Benalla", "Tatura", "1400m"):
        check(f"    {fact!r} is still on the card", fact in words(after_page))

print()
print("=" * 74)
print("PART B - the refusals, which are the point")
print("=" * 74)

# A frame with no sibling to try must be left exactly where it is, untouched.
def orphan_frame(e):
    next(x for x in e["cards"] if x["id"] == "C21")["layout"] = "fullscreen"

with tempfile.TemporaryDirectory() as t:
    d = stage(t, orphan_frame)
    author(d, "C21")
    epj_before = (d / "docs/episode.json").read_bytes()
    page_before = (d / "overlay/export/ep23-c21-benalla-and-tatura.html").read_bytes()
    # rename the frame AFTER authoring, so the rescue meets a layout it has no
    # sibling for — the "I have nothing to try" branch
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    next(c for c in epj["cards"] if c["id"] == "C21")["layout"] = "some-new-frame"
    (d / "docs/episode.json").write_text(json.dumps(epj, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    epj_before = (d / "docs/episode.json").read_bytes()
    rc_r, out_r = run("layout_rescue.py", d, "--apply")
    check("a frame with no sibling is LEFT FOR A HUMAN",
          "LEFT FOR A HUMAN" in out_r and "no sibling frame" in out_r,
          out_r.strip()[-300:])
    check("  and nothing is written", (d / "docs/episode.json").read_bytes() == epj_before)
    check("  and the page is untouched",
          (d / "overlay/export/ep23-c21-benalla-and-tatura.html").read_bytes()
          == page_before)

# ⚠️ NOT COVERED BY A LIVE FIXTURE, AND SAID SO RATHER THAN FAKED: "fails in BOTH
# frames" and "the swap needs shrinking". Both branches exist and are read straight
# off autofit's own summary line, but no fixture drives them here. Bloating a real
# card does not work — author_cards refuses untraceable text (exit 2), so the page is
# never re-authored and autofit then measures the STALE page and reports a fit. That
# false green is exactly the shape this suite exists to prevent, so the case was
# removed rather than left passing for the wrong reason. Driving it needs a synthetic
# card whose every figure traces to a real article; worth doing if either branch is
# ever touched.
print("  ·   'fails in both frames' / 'only fits by shrinking' — branches exist, no")
print("      live fixture (see the note in the source); not claimed as proved")

# Report mode must write nothing at all.
with tempfile.TemporaryDirectory() as t:
    d = stage(t, to_fullscreen)
    author(d, "C21")
    epj_before = (d / "docs/episode.json").read_bytes()
    rc_r, out_r = run("layout_rescue.py", d)
    check("report mode says WOULD SWAP", "WOULD SWAP" in out_r, out_r.strip()[-200:])
    check("  and writes nothing", (d / "docs/episode.json").read_bytes() == epj_before)

# An episode with nothing failing is not touched at all.
with tempfile.TemporaryDirectory() as t:
    d = stage(t)                       # C21 already panel-push — the shipped state
    epj_before = (d / "docs/episode.json").read_bytes()
    rc_r, out_r = run("layout_rescue.py", d, "--apply")
    check("an episode with no failing card is left alone",
          "nothing to rescue" in out_r, out_r.strip()[-200:])
    check("  and writes nothing", (d / "docs/episode.json").read_bytes() == epj_before)

print()
print("=" * 74)
print(f"layout rescue: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    for n, _w in FAIL:
        print(f"  - {n}")
    raise SystemExit(1)
