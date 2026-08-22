"""E55 — the like/subscribe chip is proved PRESENT by its own pixels, not by brightness.

WHAT WENT WRONG (EP35, 22 Aug 2026). `stage_card_timing` cropped a FIXED rectangle over
the bottom-left and hard-failed if its MEAN LUMA rose above 95. Two proxies stacked:

  · the rectangle was x70..770 y790..1050 and the chip is x96..1014 y833..975, so it
    missed the right quarter of the chip and averaged in ~45% BACKGROUND;
  · brightness is not presence. The check's own comment admitted this in 2026 — "with
    no chip it measured Gordon's dark suit at luma 68 and passed" — and it was left in.

So the number it produced was mostly a reading of THE ROOM, and it scraped through only
while the room stayed dark. The new presenter arrived on a bright racecourse backdrop:

    same rectangle, same chip, only the BACKDROP differs
      EP34  old dark studio        luma 63.9   pass
      EP35  new bright racecourse  luma 99.2   FAIL  (limit 95)

EP35 was CORRECT - Jodie watched the frame and the chip is there. The check was wrong,
and it would have failed every future episode on the new background.

WHAT THIS PROVES. `midroll_chip_match` compares the final frame against THE CHIP CLIP
ITSELF inside the chip's own opaque area, so the backdrop cannot enter the answer at
all. This file is the CONTROL FIRST (CLAUDE.md 4b): every case watches it go RED before
any case believes it on a GREEN.

THE CASE THAT PROVES THE FIX: `test_backdrop_cannot_change_the_verdict` composites the
SAME chip over a DARK and a BRIGHT background and requires the same verdict on both -
and asserts, in the same test, that the OLD mean-luma rule flips between them. That is
the EP35 fault reproduced and closed. Everything else here is scaffolding around it.

Synthetic on purpose: it needs no episode media, so it still runs when the Drive is not
mounted and it cannot rot when an episode folder is renamed or cleaned up.

Run: python engine/test_midroll_chip.py
"""
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import qc_episode as q          # noqa: E402

W, H = 640, 360
FAILURES = []


def check(name, ok, detail=""):
    print(f"  {'ok ' if ok else 'XX '}{name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def _run(args):
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg setup failed: {' '.join(args)}\n{r.stderr[-800:]}")


def make_chip(path):
    """A green-screen lower-third: the studio's own shape, in miniature."""
    _run([q.FFMPEG, "-y", "-v", "error", "-f", "lavfi",
          "-i", f"color=c=0x00FF00:s={W}x{H}:d=2:r=25",
          "-vf", "drawbox=x=60:y=250:w=380:h=70:color=white@1:t=fill,"
                 "drawbox=x=80:y=268:w=34:h=34:color=0x202020@1:t=fill",
          "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(path)])


def make_backdrop(path, brightness):
    _run([q.FFMPEG, "-y", "-v", "error", "-f", "lavfi",
          "-i", f"testsrc2=s={W}x{H}:d=2:r=25",
          "-vf", f"eq=brightness={brightness}", "-c:v", "libx264", "-crf", "12",
          "-pix_fmt", "yuv420p", str(path)])


def composite(bg, chip, out):
    """Keyed exactly as assemble_episode keys it, overlaid at 0:0 as providers does."""
    _run([q.FFMPEG, "-y", "-v", "error", "-i", str(bg), "-i", str(chip),
          "-filter_complex",
          "[1:v]chromakey=0x00FF00:0.28:0.06[k];[0:v][k]overlay=0:0[v]",
          "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
          str(out)])


def old_rule_luma(video, t):
    """The RETIRED check, kept here only so the regression can be demonstrated:
    mean luma of a fixed bottom-left rectangle, scaled to this fixture's size."""
    r = subprocess.run(
        [q.FFMPEG, "-hide_banner", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video),
         "-frames:v", "1", "-vf", "crop=233:86:23:263,format=gray",
         "-f", "rawvideo", "-"], capture_output=True)
    return sum(r.stdout) / len(r.stdout) if r.stdout else None


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="chipctl-"))
    chip = tmp / "chip.mp4"
    make_chip(chip)
    dark, bright = tmp / "dark.mp4", tmp / "bright.mp4"
    make_backdrop(dark, -0.45)
    make_backdrop(bright, 0.45)
    on_dark, on_bright = tmp / "on-dark.mp4", tmp / "on-bright.mp4"
    composite(dark, chip, on_dark)
    composite(bright, chip, on_bright)

    def match(video):
        frac, px, why = q.midroll_chip_match(str(video), str(chip), 0.0, 1.0)
        return frac, px, why

    print("\nA. THE CONTROL THAT PROVES IT CAN FAIL — the backdrop with no chip on it")
    for name, v in (("dark backdrop, no chip", dark), ("bright backdrop, no chip", bright)):
        frac, _, _ = match(v)
        check(f"{name} reads ABSENT", frac is not None and frac < q.CHIP_MATCH,
              f"match {100*frac:.1f}%" if frac is not None else "unmeasurable")

    print("\nB. AND GREEN ONLY THEN — the same backdrops with the chip composited")
    for name, v in (("dark backdrop + chip", on_dark), ("bright backdrop + chip", on_bright)):
        frac, px, _ = match(v)
        check(f"{name} reads PRESENT", frac is not None and frac >= q.CHIP_MATCH,
              f"match {100*frac:.1f}% of {px:,}px" if frac is not None else "unmeasurable")

    print("\nC. 🔴 THE CASE THAT PROVES THE EP35 FIX")
    print("   the SAME chip on a DARK and a BRIGHT backdrop — one verdict, both times")
    d_on = match(on_dark)[0]
    b_on = match(on_bright)[0]
    d_off = match(dark)[0]
    b_off = match(bright)[0]
    check("present on BOTH backdrops", d_on >= q.CHIP_MATCH and b_on >= q.CHIP_MATCH,
          f"dark {100*d_on:.1f}%  bright {100*b_on:.1f}%")
    check("absent on BOTH backdrops", d_off < q.CHIP_MATCH and b_off < q.CHIP_MATCH,
          f"dark {100*d_off:.1f}%  bright {100*b_off:.1f}%")
    check("the backdrop moves the reading by under 5 points",
          abs(d_on - b_on) < 0.05, f"gap {100*abs(d_on-b_on):.1f} points")

    print("\n   and the RETIRED rule, on the very same two files:")
    o_d, o_b = old_rule_luma(on_dark, 1.0), old_rule_luma(on_bright, 1.0)
    print(f"      mean luma with the chip present — dark {o_d:.1f}   bright {o_b:.1f}")
    check("the old brightness rule DID move with the backdrop "
          "(this is the fault, reproduced)", abs(o_d - o_b) > 20,
          f"gap {abs(o_d-o_b):.1f} luma")

    print("\nD. A DECOY — something that covers the area but is NOT the chip")
    decoy = tmp / "decoy.mp4"
    _run([q.FFMPEG, "-y", "-v", "error", "-f", "lavfi",
          "-i", f"color=c=0x303030:s={W}x{H}:d=2:r=25",
          "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(decoy)])
    frac, _, _ = match(decoy)
    check("a flat panel over the whole frame is NOT accepted as the chip",
          frac is not None and frac < q.CHIP_MATCH, f"match {100*frac:.1f}%")

    print("\nE. UNMEASURABLE INPUTS WARN, THEY DO NOT ACCUSE")
    print("   (a false alarm on a finished episode is the costlier of the two errors)")
    frac, _, why = q.midroll_chip_match(str(on_dark), str(tmp / "gone.mp4"), 0.0, 1.0)
    check("a missing chip clip returns 'cannot measure', not 'absent'",
          frac is None, why)
    frac, _, why = q.midroll_chip_match(str(tmp / "gone.mp4"), str(chip), 0.0, 1.0)
    check("a missing final returns 'cannot measure', not 'absent'", frac is None, why)

    print("\nF. NO CONSTANT IS A KNIFE EDGE")
    for tol in (4, 12, 40):
        on = q.midroll_chip_match(str(on_bright), str(chip), 0.0, 1.0, tol=tol)[0]
        off = q.midroll_chip_match(str(bright), str(chip), 0.0, 1.0, tol=tol)[0]
        check(f"tol {tol}: verdict unchanged", on >= q.CHIP_MATCH > off,
              f"present {100*on:.1f}%  absent {100*off:.1f}%")

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)} case(s): {FAILURES}")
        return 1
    print("PASS — the chip is proved by its own pixels, and the backdrop cannot "
          "change the answer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
