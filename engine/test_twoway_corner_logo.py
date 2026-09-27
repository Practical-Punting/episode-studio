#!/usr/bin/env python3
"""The corner logo is the CHANNEL'S standing mark, not a copy of a card's.

    python engine/test_twoway_corner_logo.py [<ep>] [<finished.mp4>]

🔴 WHAT WENT WRONG. Jodie, 20 Sep: *"the motion graphics logo is the correct one and it
should just be there throughout the whole video."* That was read as "make the persistent
corner logo IDENTICAL to a card's", and the two-way drew **214x65** where forty-two
published episodes wear **428x140** — half the linear size, a quarter of the area. Jodie
spotted it with EP34 and EP49 side by side.

⚖️ A card's logo is furniture ON a card. The corner mark is its own standing element:
PP-STANDARDS §Logo, *"PROMINENT: generous size (roughly double a subtle watermark)"* —
and "roughly double" turns out to be exactly double.

📌 THE SIZE IS NOT ASSERTED AS A NUMBER HERE. It is asserted to equal the ASSET'S own
dimensions, because that is where `assemble_episode` gets it (pass A overlays the chip
with no scale filter at all). A literal 428x140 in this file would be one more
description of a logo that already had four that disagreed.
"""
from __future__ import annotations

import io
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ep_paths                                                   # noqa: E402
import twoway_assemble as ta                                      # noqa: E402
import twoway_render as tr                                        # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")
PASS, FAIL, NOTE = [], [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'OK  ' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    return ok


def crop(src, t, box):
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
         "-vf", f"crop={box[2]}:{box[3]}:{box[0]}:{box[1]}",
         "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, timeout=600)
    return (np.asarray(Image.open(io.BytesIO(r.stdout)).convert("L"), dtype=np.float64)
            if r.stdout else None)


def main(ep=49, final=None) -> int:
    d = ep_paths.episode_dir(ep, PP)
    import json
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    plan = ta.build_plan(ep, PP)

    print("\n-- 1. the corner logo is the STANDING asset, at ITS OWN size --")
    g = tr.corner_logo(epj)
    asset = pathlib.Path(g["src"])
    check("it is the asset the single-presenter build uses",
          asset.name == "video-logo-chip.png", asset.name)
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of",
                        "default=nw=1:nk=1", str(asset)],
                       capture_output=True, text=True, timeout=120)
    aw, ah = (int(x) for x in r.stdout.split())
    check("it is drawn at the ASSET'S size, not at a number in the code",
          (g["w"], g["h"]) == (aw, ah), f"{g['w']}x{g['h']} vs asset {aw}x{ah}")
    check("it sits at the standing margin from the bottom-right corner",
          g["x"] == tr.W - aw - g["margin"] and g["y"] == tr.H - ah - g["margin"],
          f"({g['x']},{g['y']}) margin {g['margin']}")

    # 🔴 THE RELATIONSHIP, NOT THE PIXELS. The corner mark must be BIGGER than a card's,
    # which is the thing that was wrong; asserting 428 would pass even if the cards
    # changed underneath it.
    c = tr.card_logo_geometry(d, plan)
    check("and it is LARGER than the mark the cards carry — the whole point",
          g["w"] > c["w"] and g["h"] > c["h"],
          f"corner {g['w']}x{g['h']}, cards {c['w']}x{c['h']} "
          f"({g['w'] / c['w']:.2f}x linear)")
    check("CONTROL: the cards' geometry is what the OLD code drew, and it is smaller",
          (c["w"], c["h"]) != (g["w"], g["h"]), f"{c['w']}x{c['h']}")

    # 🔴 JODIE'S RULE, 27 Sep 2026, NOT EP48'S BEHAVIOUR. The chip runs the whole way
    # through: over the conversation, over the graphics and over the cards. EP48 does
    # the opposite — its cards cover the chip — and that comparison is deliberately NOT
    # made here any more. The presenter case below still compares against EP48, because
    # there the two agree.
    print("\n-- 2. the chip runs over the cards too, and the cards carry no mark --")
    check("no hold-off windows remain", tr.card_windows(plan) == [],
          f"{len(tr.card_windows(plan))}")
    # ⚖️ AND THE CARDS THEMSELVES MUST BE CLEAN. Covering was not enough: the chip is
    # near-opaque (alpha mean 203/255 over the card's mark) and the card's own logo
    # ghosted through at mean 9.79 of 255. So the clips are rendered logo-less, and
    # that is what this asserts — on the CLIPS, not on the pages, because the pages are
    # deliberately unchanged so the single-presenter path keeps its own mark.
    import io
    import numpy as np
    from PIL import Image
    box = (c["x"], c["y"], c["w"], c["h"])
    dirty = []
    for cid, path in sorted((plan.get("cards_on_disk") or {}).items()):
        r = subprocess.run(["ffmpeg", "-v", "error", "-sseof", "-0.1", "-i", str(path),
                            "-frames:v", "1", "-vf",
                            f"crop={box[2]}:{box[3]}:{box[0]}:{box[1]}",
                            "-f", "image2pipe", "-vcodec", "png", "-"],
                           capture_output=True, timeout=600)
        if not r.stdout:
            continue
        a = np.asarray(Image.open(io.BytesIO(r.stdout)).convert("L"), dtype=np.float64)
        if float((a > 110).mean() * 100) > 0.5:
            dirty.append(cid)
    check(f"no card clip has a mark where the chip lands "
          f"({len(plan.get('cards_on_disk') or {})} checked)", not dirty, f"{dirty}")
    # the AUTHORED PAGES must still carry theirs — the single-presenter path needs it
    pages = sorted((d / "overlay/export").glob("ep49-c[0-9][0-9]-*.html"))
    keep = [p.name for p in pages if 'id="logo"' in p.read_text(encoding="utf-8")]
    check(f"and every authored PAGE still declares its own logo ({len(keep)} of "
          f"{len(pages)}) — the single-presenter path is untouched",
          len(keep) == len(pages) and bool(pages))

    print("\n-- 3. and in the FINISHED FILM, if one was given --")
    if not final:
        NOTE.append("no mp4 given — checks against the pixels not run. "
                    "Pass the finished file as the second argument.")
        print("  .... skipped")
    else:
        f = pathlib.Path(final)
        box = (1400, 860, 520, 220)
        # a plain full-frame shot, and the middle of the first full-frame card
        plain = next(s for s in plan["segments"]
                     if not s.get("card") and not s.get("broll")
                     and s["layout"] != "two-box" and s["dur_s"] > 6)
        card = next(s for s in plan["segments"]
                    if s.get("card") and s["layout"] != "two-box")
        a = crop(f, plain["from_s"] + plain["dur_s"] / 2, box)
        b = crop(f, card["from_s"] + card["dur_s"] / 2, box)
        ep48 = (PP / "PP-EP48-Getting-Together-with-International-Experts-Part-1"
                   / "output"
                   / "PP-EP48-Getting-Together-with-International-Experts-Part-1-FINAL.mp4")
        # 🔴 THE CHIP'S OWN BOX inside that crop: bright pixels where the big chip is,
        # measured the same way in both films so the comparison means something.
        # 🔴 THE MEASURE IS "DOES EP49 MATCH EP48", NOT "IS EP49 UNDER A NUMBER I CHOSE".
        #
        # ⚠️ THE FIRST VERSION OF THIS ASSERTED `< 1.0%` ON A CARD AND FAILED — on a
        # cut that was right. EP48, the reference, reads **11.98%** in the same region,
        # because a full-frame card has its own artwork there; the threshold was
        # invented rather than derived, and it reported a fault that was not there.
        # That is the EP33 lesson exactly: a guard fed a number you picked yourself
        # manufactures a fault. The published episode is the reference, so compare
        # against it.
        def chip_ink(img):
            if img is None:
                return None
            # The 428x140 chip starts at (1452,900); inside a crop at (1400,860) that is
            # (52,40). `chip` is where the BIG mark's wordmark sits — the discriminating
            # region, empty when the chip is absent. `wide` is the whole corner, which
            # carries whatever is behind it and is reported for context, not asserted.
            chip = img[40:105, 52:266]
            wide = img[105:180, 52:480]
            return float((chip > 110).mean() * 100), float((wide > 110).mean() * 100)

        pa, pb = chip_ink(a), chip_ink(b)
        e48 = chip_ink(crop(ep48, 400.0, box))
        e48c = chip_ink(crop(ep48, 125.0, box))
        print(f"    {'':34s} {'chip region':>13s} {'whole corner':>14s}")
        for lbl, v in (("EP49 plain full-frame shot", pa),
                       ("EP49 full-frame card", pb),
                       ("EP48 plain presenter shot", e48),
                       ("EP48 full-frame card", e48c)):
            print(f"    {lbl:34s} {v[0]:12.2f}% {v[1]:13.2f}%")
        # the PRESENTER case still measures against EP48 — there the two agree
        check("on a plain shot the chip is THERE, and reads as EP48's does",
              abs(pa[0] - e48[0]) < 6.0 and pa[0] > 10.0,
              f"EP49 {pa[0]:.2f}% vs EP48 {e48[0]:.2f}%")
        # 🔴 THE CARD CASE IS JODIE'S RULE AND IS DELIBERATELY NOT EP48'S. EP48 reads
        # ~0% there because its card covers the chip; EP49 must read the SAME as its own
        # presenter shot, because the chip does not change across a card boundary.
        check("on a full-frame card the chip is STILL THERE — unchanged, not covered",
              abs(pb[0] - pa[0]) < 3.0,
              f"card {pb[0]:.2f}% vs presenter {pa[0]:.2f}% "
              f"(EP48's card is {e48c[0]:.2f}%, which is the behaviour we left)")
        check("the logo does not change across a card boundary at all",
              abs(pa[0] - pb[0]) < 3.0,
              f"{abs(pa[0] - pb[0]):.2f} points apart")

    print(f"\ncorner logo: {len(PASS)} passed, {len(FAIL)} failed")
    for n in NOTE:
        print(f"  ~ {n}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    raise SystemExit(main(int(a[0]) if a else 49, a[1] if len(a) > 1 else None))
