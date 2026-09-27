#!/usr/bin/env python3
"""end_frame.py — the plain branded frame YouTube's end screens sit on.

    python end_frame.py <final.mp4> --logo <png> --music <mp3> [--seconds 18]

🔴 WHY IT EXISTS. YouTube's end-screen boxes — subscribe, next video, playlist —
are drawn over the last 15-20 seconds of a video, and the operator does not get to
say where. Today the WARRANTY SLIDE is the last thing on screen and runs to the
final frame, so those boxes land squarely on the responsible-gambling text and the
support line: "For free and confidential support call 1800 858 858". Covering that
is the one thing this channel cannot do.

Measured on EP20 before this existed: end card to ~t=426, warranty from ~t=427 to
the last frame at 435.72. Nothing followed it.

So a plain frame is APPENDED: charcoal, the PP logo, and nothing else. No warranty
text, no support number, nothing a box can hide that matters.

⚠️ IT IS APPENDED TO THE FINISHED FILE, NOT WOVEN INTO PASS B, and that is the whole
safety argument. Pass B's graph — the warranty's fade-in, its hold, the final
fade-out, every card lead and the music duck — is left byte-for-byte alone. This
concatenates one new clip onto the end. It cannot alter the warranty slide's content
or its timing, because it never touches the part of the file the warranty is in.

🔇 AND IT IS NOT SILENT. Cutting to digital black silence reads as the file breaking.
A soft bed continues under it and fades to nothing over the last few seconds, so the
episode ENDS rather than stops.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        pass

SECONDS = 18.0          # inside YouTube's 15-20s end-screen window
MIN_SECONDS = 15.0      # what qc_episode refuses to ship without
CHARCOAL = "0x1E1E1E"   # the cards' own background — see assets/cards/frame-*.html
# The logo, centred, as a FRACTION OF THE FRAME rather than a pixel count.
# ⚠️ IT WAS 360px FLAT AND THAT IS THE CLASS OF BUG THIS CODEBASE KEEPS PAYING FOR:
# right at 1920 wide, and at 640 it is more than half the picture — which made the
# end frame read as BUSY as the warranty slide and defeated its own detector. Caught
# by the suite building a small stand-in film. A proportion cannot go silently wrong
# when the canvas changes.
LOGO_FRAC = 0.1875      # 360/1920 — the size the end card uses, expressed honestly
MUSIC_TAIL = 24.0       # where in the bed to take the outro from
FADE = 4.0              # the bed fades to nothing over the last FADE seconds


class Halt(Exception):
    """A build-stopping problem, phrased for a human."""


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise Halt(f"could not read {path.name}: {(r.stderr or '').strip()[-300:]}")
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), {})
    return {"dur": float(d["format"]["duration"]),
            "w": int(v["width"]), "h": int(v["height"]),
            "fps": v.get("r_frame_rate", "25/1"),
            "pix": v.get("pix_fmt"), "vcodec": v["codec_name"],
            "acodec": a.get("codec_name"), "ar": a.get("sample_rate"),
            "ch": a.get("channels")}


def build_clip(out: Path, logo: Path, music: Path, spec: dict, seconds: float) -> Path:
    """The end frame itself, encoded to MATCH the film it will be joined to.

    Every parameter is read off the finished file rather than assumed, because the
    join is a stream COPY: a mismatch in size, rate or pixel format would either be
    refused or produce a file that plays wrong from the seam onward.
    """
    vf = (f"[1:v]scale={max(2, int(spec['w'] * LOGO_FRAC)) // 2 * 2}:-1[lg];"
          f"[0:v][lg]overlay=(W-w)/2:(H-h)/2:format=auto,"
          f"format={spec['pix'] or 'yuv420p'}[v]")
    af = (f"[2:a]atrim=start={MUSIC_TAIL}:duration={seconds},asetpts=PTS-STARTPTS,"
          f"volume=0.22,afade=t=in:st=0:d=1.2,"
          f"afade=t=out:st={round(seconds - FADE, 2)}:d={FADE},"
          f"aformat=sample_fmts=fltp:sample_rates={spec['ar'] or 48000}:"
          f"channel_layouts=stereo[a]")
    # 🔴 NO `-loop 1` ON THE LOGO. IT HANGS ffmpeg 8.1.2, AND IT HANGS IT ALONE.
    #
    # This read `-loop 1 -t {seconds} -i {logo}` from August until 22 Sep 2026, when it
    # stopped terminating: EP49's append sat for 43 minutes, burned 412 CPU-seconds and
    # never created its output file, while the process grew past 865 MB of RSS.
    #
    # ⚠️ AND THE FIRST TWO EXPLANATIONS WERE BOTH WRONG, which is why this comment can
    # be believed. It was not the Drive — the same command hangs writing to C:. It was
    # not the missing output `-t` — adding one changed nothing. Bisected at 2 seconds:
    # the colour source alone renders in **0.3s**, the music branch alone in **0.1s**,
    # and `-loop 1 -t 2 -i logo.png` hangs at 90s **with no overlay in the graph and the
    # image not even mapped**. The looped image demuxer is what never ends; everything
    # downstream of it was innocent.
    #
    # ✅ THE FIX IS TO STOP LOOPING IT. One still frame is all there ever was to show,
    # and `overlay` holds the last frame of its second input for the rest of the main
    # by default (`repeatlast=1`) — so the logo sits there for the whole clip without
    # anything having to generate 450 identical frames. Measured: **0.2s**, against a
    # 90-second timeout on the looped form.
    #
    # 📌 The ffmpeg in use is recorded on the way past, because this is a version
    # behaviour and the next person deserves to know which one it was:
    # `ffmpeg 8.1.2-full_build-www.gyan.dev`.
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i",
           f"color=c={CHARCOAL}:s={spec['w']}x{spec['h']}:r={spec['fps']}:d={seconds}",
           "-i", str(logo),
           "-i", str(music),
           "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]",
           "-t", str(seconds),
           "-c:v", "libx264", "-crf", "18", "-preset", "medium",
           "-pix_fmt", spec["pix"] or "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", str(spec["ar"] or 48000),
           "-movflags", "+faststart", "-map_metadata", "-1", "-dn", str(out)]
    # 🔴 AND A TIMEOUT, BECAUSE THIS STEP HAS NOW HUNG ONCE. An eighteen-second clip
    # that has not finished in five minutes is not slow, it is stuck — and a step with
    # no timeout is a step that reports nothing for forty-three minutes while somebody
    # watches a file that will never grow. CLAUDE.md fault #3: anything that waits must
    # say it is waiting, and say who it is waiting on.
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
    except subprocess.TimeoutExpired:
        out.unlink(missing_ok=True)
        raise Halt(
            "the end frame did not render in five minutes. Eighteen seconds of "
            "charcoal is a two-second job, so this is a hang, not slowness. It has "
            "happened once before, on ffmpeg 8.1.2, and the cause was a `-loop 1` "
            "image input that never ends — check the ffmpeg version and the input "
            "list above before anything else. Nothing was promoted.")
    if r.returncode or not out.is_file():
        raise Halt(f"the end frame would not render: {(r.stderr or '').strip()[-500:]}")
    return out


def already_there(final: Path, seconds: float) -> bool:
    """Has an end frame already been appended? Asked of the PICTURE, not a marker.

    A marker file beside the video would answer for the folder rather than for the
    film — and it is the film that gets uploaded. `looks_plain` reads the frames.
    """
    from_end = min(2.0, seconds / 2)
    return looks_plain(final, probe(final)["dur"] - from_end)


def brightish(final: Path, at: float) -> float:
    """The fraction of the frame that is markedly brighter than the background.

    THE DISCRIMINATOR, AND IT IS MEASURED RATHER THAN GUESSED. The warranty slide is
    paragraphs of near-white text on charcoal; the end frame is charcoal with one
    logo. Counting bright pixels separates them by more than an order of magnitude —
    the real numbers are in test_end_frame.py, taken off EP20's shipped file.
    """
    from PIL import Image
    import io
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(at, 0):.2f}",
                        "-i", str(final), "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True)
    if not r.stdout:
        raise Halt(f"could not read a frame of {final.name} at {at:.2f}s")
    im = Image.open(io.BytesIO(r.stdout)).convert("L").resize((480, 270))
    px = list(im.getdata())
    return sum(1 for p in px if p > 110) / len(px)


def looks_plain(final: Path, at: float, limit: float = 0.02) -> bool:
    return brightish(final, at) < limit


def append(final: Path, logo: Path, music: Path, seconds: float = SECONDS) -> str:
    spec = probe(final)
    if already_there(final, seconds):
        return (f"end frame: already on {final.name} — left alone "
                f"(the last frames are plain, not the warranty slide)")
    clip = final.parent / ".end-frame.mp4"
    build_clip(clip, logo, music, spec, seconds)
    lst = final.parent / ".concat.txt"
    lst.write_text(f"file '{final.name}'\nfile '{clip.name}'\n", encoding="utf-8")
    joined = final.parent / (".joined-" + final.name)
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(joined)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not joined.is_file():
        clip.unlink(missing_ok=True); lst.unlink(missing_ok=True)
        raise Halt(f"the end frame would not join on: {(r.stderr or '').strip()[-500:]}")
    after = probe(joined)
    grew = after["dur"] - spec["dur"]
    # 🔴 VERIFY BEFORE PROMOTING. A concat that silently drops the tail leaves a file
    # that plays perfectly and is missing the thing this whole script is for.
    if grew < seconds - 1.0:
        joined.unlink(missing_ok=True); clip.unlink(missing_ok=True); lst.unlink(missing_ok=True)
        raise Halt(f"the join produced only {grew:.2f}s of new tail, not {seconds:.0f}s "
                   f"— the original film is untouched and nothing was promoted.")
    joined.replace(final)
    clip.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)
    return (f"end frame: +{grew:.2f}s appended after the warranty slide "
            f"({spec['dur']:.2f}s -> {after['dur']:.2f}s), charcoal + logo, "
            f"bed fading out over the last {FADE:.0f}s")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("final")
    ap.add_argument("--logo", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--seconds", type=float, default=SECONDS)
    a = ap.parse_args(argv)
    print("  " + append(Path(a.final), Path(a.logo), Path(a.music), a.seconds))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Halt as e:
        print(f"END FRAME HALTED — {e}", file=sys.stderr)
        sys.exit(2)
