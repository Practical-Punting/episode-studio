"""test_end_frame.py — every episode ends on a plain branded frame, never on the
responsible-gambling text.

    YouTube draws its end-screen boxes — subscribe, next video, playlist — over the
    LAST 15-20 SECONDS, and the operator does not get to say where. Measured on
    EP20 as it shipped: the end card ran to ~426s and the WARRANTY SLIDE from ~427s
    to the final frame at 435.72. Nothing followed it, so those boxes landed on
    "For free and confidential support call 1800 858 858".

THE DISCRIMINATOR IS MEASURED, NOT GUESSED. The fraction of markedly-bright pixels,
taken off EP20's real file:

    end card          0.2155     the e-book picture and big type
    warranty slide    0.0645     paragraphs of near-white text
    plain end frame   0.0046     charcoal, one logo

so the 0.02 limit sits with a 14x margin below it and 3.2x above — an order of
magnitude either side, rather than a number picked to make a test pass.

Run: python engine/test_end_frame.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

import end_frame as ef                                           # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))
ASSETS = HERE.parent / ".claude/skills/pp-episode-production/assets"
LOGO = ASSETS / "video-logo-chip.png"
MUSIC = PP / "PP-EP01-The-Trifecta-Mistake/music" / \
    "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"

def episode_dir(n: int) -> Path:
    """BY NUMBER, never by a written-out name — stage-8 renames published folders,
    and this suite reaches into a real one for its readings."""
    hits = sorted(p for p in PP.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else PP / f"PP-EP{n:02d}"


PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def a_film(path: Path, seconds=8.0, texty=True):
    """A stand-in film whose tail is BUSY like the warranty slide, or plain.

    Built rather than copied: a 400 MB episode is not something to duplicate in a
    test, and what is being checked is the tail's BUSYNESS, which is reproducible.

    ⚠️ WHITE BOXES, NOT `drawtext`. The first version drew the warranty's real words
    and ffmpeg died with an access violation — this build has no font configured, so
    the test would have failed on every machine without one while telling you nothing
    about end frames. The boxes are DIALLED TO THE REAL READING instead: about 6.5%
    of the frame lit, which is what EP20's warranty slide actually measures (0.0645).
    A stand-in tuned to the measurement beats a stand-in that looks like the thing.
    """
    # 4 boxes x 100x37 on 640x360 = 14,800 of 230,400 px = 6.4%
    draw = ",".join(f"drawbox=x={20 + i * 150}:y=160:w=100:h=37:color=white@1:t=fill"
                    for i in range(4)) if texty else "null"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c=0x1E1E1E:s=640x360:r=25:d={seconds}",
         "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={seconds}",
         "-vf", draw, "-c:v", "libx264", "-crf", "20", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", str(path)], check=True, capture_output=True)
    return path


def main():
    if not LOGO.is_file():
        print(f"missing {LOGO}")
        return 1

    print("-- THE READINGS, off EP20's shipped film --")
    ep20 = next(iter(sorted((episode_dir(20) / "output").glob("*FINAL.mp4"))), None)
    if ep20 and ep20.is_file():
        total = ef.probe(ep20)["dur"]
        end_card = ef.brightish(ep20, total - 20)
        check(f"the end card is busy ({end_card:.4f})", end_card > 0.1, f"{end_card}")
    else:
        check("EP20 is on this machine", False, "cannot take the real readings")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        print("\n-- CONTROL: a film that ends on the warranty slide IS REFUSED --")
        warranty = a_film(d / "warranty-tail.mp4", 8.0, texty=True)
        w_read = ef.brightish(warranty, ef.probe(warranty)["dur"] - 1)
        check(f"a texty tail measures busy ({w_read:.4f})", w_read > 0.02, f"{w_read}")
        check("  so looks_plain() says NO", not ef.looks_plain(warranty, 7.0))
        check("  and already_there() says the end frame is missing",
              not ef.already_there(warranty, 18))

        print("\n-- APPENDING IT: the tail grows and becomes plain --")
        before = ef.probe(warranty)
        say = ef.append(warranty, LOGO, MUSIC, 18)
        after = ef.probe(warranty)
        grew = after["dur"] - before["dur"]
        check(f"the film grew by ~18s (got {grew:.2f}s)", 17.0 <= grew <= 19.5, f"{grew}")
        check("  and it says so in words for the run log", "end frame" in say and "s" in say)
        p_read = ef.brightish(warranty, after["dur"] - 1)
        check(f"the new tail is plain ({p_read:.4f})", p_read < 0.02, f"{p_read}")
        check("  plain 15s back too, so it is LONG enough",
              ef.looks_plain(warranty, after["dur"] - ef.MIN_SECONDS + 0.5))
        check("  already_there() now says yes", ef.already_there(warranty, 18))

        print("\n-- THE WARRANTY IS UNTOUCHED. Additive means additive. --")
        check("every second before the join still reads busy",
              ef.brightish(warranty, before["dur"] - 1) > 0.02,
              "the original tail was altered, which is the one thing this must not do")
        check("  the film before the join is the same length as it was",
              abs((after["dur"] - grew) - before["dur"]) < 0.1)

        print("\n-- IT DOES NOT DOUBLE UP ON A RE-RUN --")
        again = ef.append(warranty, LOGO, MUSIC, 18)
        check("a second call leaves it alone", "already" in again.lower(), again[:70])
        check("  and the duration did not move",
              abs(ef.probe(warranty)["dur"] - after["dur"]) < 0.1)

        print("\n-- A TOO-SHORT END FRAME IS REFUSED, not quietly accepted --")
        short = a_film(d / "short-tail.mp4", 6.0, texty=True)
        ef.append(short, LOGO, MUSIC, 6)          # deliberately under the 15s floor
        st = ef.probe(short)["dur"]
        check("a 6s end frame reads plain at the very end",
              ef.looks_plain(short, st - 1))
        check("  but NOT 15s back — which is how the QC catches it",
              not ef.looks_plain(short, st - ef.MIN_SECONDS + 0.5),
              "a short frame would pass a last-frame-only check and still let the "
              "boxes cover the warranty")

    print("\n-- the QC refuses to ship without it --")
    qc = (SCRIPTS / "qc_episode.py").read_text(encoding="utf-8")
    check("qc_episode checks the end frame", "end_frame" in qc and "MIN_SECONDS" in qc)
    check("  and it FAILS rather than notes",
          "does not end on the plain branded frame" in qc and "qc.fail(" in qc)
    check("  naming what is at stake", "support number" in qc)
    prov = (HERE / "providers.py").read_text(encoding="utf-8")
    check("the assembler appends it every episode",
          "append_end_frame(final)" in prov)
    check("  AFTER pass B is written, never inside the graph",
          prov.index("append_end_frame(final)") > prov.index('"-map", "[vout]"'),
          "woven into the graph it could move the warranty's timing")

    print(f"\nend frame: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
