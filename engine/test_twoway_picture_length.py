#!/usr/bin/env python3
"""The concatenated picture must be as long as the plan says — with a CONTROL.

    python engine/test_twoway_picture_length.py

🔴 WHY THIS TEST EXISTS. EP49's first cut was the right LENGTH and the last three
seconds were black: the 3s settle had no piece in the concat, so the end card arrived
early and ffmpeg's final `-t` padded the hole with nothing. Every step succeeded. The
fault surfaced three checks later, on the finished file, as two symptoms that were one
fault — "57 frames short of the header" and "blank frame at 854.8s".

**CLAUDE.md 4b: a guard is not trustworthy until you have watched it FAIL.** So the
control comes first here, and it is the EXACT shape of the real fault — a piece list
with a piece missing from the middle — not a hand-written short number. If the control
ever stops raising, this file has stopped being evidence about anything.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import twoway_render as tr                                         # noqa: E402

FPS = tr.FPS
PASSED, FAILED = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASSED if ok else FAILED).append(name)
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")


def make_piece(path: pathlib.Path, seconds: float, colour: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i",
                    f"color=c={colour}:s=320x180:r={FPS}:d={seconds}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
                    "-pix_fmt", "yuv420p", str(path)], check=True, timeout=300)


def concat(work: pathlib.Path, pieces: list[pathlib.Path],
           stem: str) -> pathlib.Path:
    """Named exactly as finish() names them, so the guard's own path arithmetic —
    `_picture-<key>.mp4` -> `_whole-<key>.txt` — is under test too, not bypassed."""
    lst = work / f"_whole-{stem}.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in pieces), encoding="utf-8")
    out = work / f"_picture-{stem}.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out)], check=True, timeout=600)
    return out


def main() -> int:
    print(__doc__.splitlines()[0])
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        head = work / "_head.mp4"
        body = work / "_body.mp4"
        settle = work / "_settle.mp4"
        card = work / "_endcard.mp4"
        make_piece(head, 2.0, "black")
        make_piece(body, 4.0, "green")
        make_piece(settle, 3.0, "blue")          # the piece that went missing
        make_piece(card, 2.0, "white")
        total = 11.0

        # ── THE CONTROL, FIRST: the settle left out, exactly as it was on the night.
        print("\n  CONTROL — the settle piece missing from the list:")
        short = concat(work, [head, body, card], "control")
        raised = None
        try:
            tr.assert_picture_reaches(short, total)
        except tr.Unrenderable as e:                               # noqa: PERF203
            raised = str(e)
        check("a missing piece RAISES", raised is not None,
              "the guard cannot fail, so it proves nothing" if raised is None else "")
        if raised:
            check("it names the measured length", "8.0" in raised, raised[:70])
            check("it names the planned length", "11.0" in raised, raised[:70])
            check("it names the signed difference", "-3.0" in raised, raised[:70])
            check("it lists the pieces it did concatenate",
                  "_head.mp4" in raised and "_endcard.mp4" in raised)
            check("and the missing one is absent from that list",
                  "_settle.mp4" not in raised)

        # ── ONLY NOW the good input.
        print("\n  the real shape — every piece present:")
        whole = concat(work, [head, body, settle, card], "good")
        got = None
        try:
            got = tr.assert_picture_reaches(whole, total)
        except tr.Unrenderable as e:                               # noqa: PERF203
            check("a complete list passes", False, str(e)[:90])
        if got is not None:
            check("a complete list passes", True, f"measured {got:.3f}s")
            check("and it returns what it measured", abs(got - total) < 0.05)

        # ── the tolerance is a tolerance, not a shrug: one frame either way is fine,
        #    a quarter of a second is not.
        print("\n  the tolerance:")
        one_frame = 1.0 / FPS
        ok_small = True
        try:
            tr.assert_picture_reaches(whole, total + one_frame)
        except tr.Unrenderable:
            ok_small = False
        check("one frame of drift is tolerated", ok_small)
        caught_big = False
        try:
            tr.assert_picture_reaches(whole, total + 0.30)
        except tr.Unrenderable:
            caught_big = True
        check("a third of a second is NOT tolerated", caught_big)

        # ── and it must not be reading the header, which is the thing being doubted.
        print("\n  it counts packets, it does not trust the header:")
        src = pathlib.Path(tr.__file__).read_text(encoding="utf-8")
        fn = src.split("def assert_picture_reaches", 1)[1].split("\ndef ", 1)[0]
        check("-count_packets is in the probe", "-count_packets" in fn)
        check("format=duration is NOT", "format=duration" not in fn)

    # ── the drift itself, as arithmetic. The guard above catches a wrong TOTAL; this
    #    catches the thing a right total can still hide — pieces that are individually
    #    a frame out, in the same direction, sixty-four times.
    print("\n  frame arithmetic — every piece starts where the plan says:")
    import math
    import random
    rng = random.Random(49)
    t, cuts = 0.0, [0.0]
    for _ in range(64):                       # awkward times on purpose: nothing lands
        t += round(rng.uniform(1.7, 22.3), 3)  # on a frame boundary by luck
        cuts.append(round(t, 3))
    segs = [{"n": i + 1, "from_s": cuts[i], "to_s": cuts[i + 1],
             "dur_s": round(cuts[i + 1] - cuts[i], 3)} for i in range(64)]

    cum, off = 0, []
    for s in segs:
        if cum != tr.frames_between(0.0, s["from_s"]):
            off.append(s["n"])
        cum += tr.frames_between(s["from_s"], s["to_s"])
    check("no segment starts on the wrong frame", not off,
          f"{len(off)} of 64 do" if off else "")
    check("and the pieces sum to the whole",
          cum == tr.frames_between(0.0, cuts[-1]),
          f"{cum} vs {tr.frames_between(0.0, cuts[-1])}")

    # THE CONTROL — the algorithm that was actually there, on the same cuts.
    cum_old, off_old = 0, []
    for s in segs:
        if cum_old != tr.frames_between(0.0, s["from_s"]):
            off_old.append(s["n"])
        cum_old += math.ceil(round(s["dur_s"], 3) * FPS)   # each piece measures itself
    check("CONTROL: the old per-piece rounding DOES drift", bool(off_old),
          f"{len(off_old)} of 64 land on the wrong frame, "
          f"ending {(cum_old - cum) / FPS:+.3f}s out")
    check("CONTROL: and the drift is one-directional", cum_old >= cum,
          f"old {cum_old}f vs exact {cum}f")

    # and the piece NAME must move when the length does, or a stale piece is served.
    print("\n  a re-timed piece is a different file:")
    w = pathlib.Path(".")
    a = tr.piece_path({"n": 7, "from_s": 10.0, "to_s": 20.0}, w).name
    b = tr.piece_path({"n": 7, "from_s": 10.0, "to_s": 20.5}, w).name
    check("a different length gives a different filename", a != b, f"{a} / {b}")
    check("the same length gives the same filename",
          a == tr.piece_path({"n": 7, "from_s": 10.0, "to_s": 20.0}, w).name)

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  ! " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
