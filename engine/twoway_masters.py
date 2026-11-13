#!/usr/bin/env python3
"""twoway_masters.py — make a presenter MASTER from a HeyGen render: keep only the script.

    python engine/twoway_masters.py <ep> <CODE> --words <render-words.json> [--source R.mp4]
                                    [--out-dir DIR] [--force]
    python engine/twoway_masters.py <ep> <CODE> --keep 3.56-243.24 [--keep 80.88-end] …

Writes   renders/<CODE>-master.mp4                  the master the cut is built from
         renders/masters-EP<nn>.json                what was kept and removed, measured
         output/qc/joins/<CODE>-join-<k>.wav        3s either side of every join, for her ear

The ORIGINAL render is never touched. Keep ranges normally come from
`twoway_render_words.py` (its `keep_s`), which only ever cuts inside pauses: a false
start at the head, words after the last script word, stray words between sentences.
Mid-sentence strays are never in `keep_s` as a cut — they are Jodie's call.

This is EP56's `make_masters.py` (12–13 Nov 2026) as a tool, generalised from "one range"
and "two ranges" to any number:
  · every cut point is a WHOLE FRAME, so picture and sound move by the same amount;
  · a join (two kept ranges meeting) gets a 6-frame dissolve INSIDE the pause — the house
    smoothing for a join that skips master — and the audio is butt-joined with 5ms
    fades, so the length and A/V sync are exactly the audio's;
  · the result is MEASURED (decoded frame count and audio length) and refused if picture
    and sound differ by more than a frame.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ep_paths     # noqa: E402

XF = 6                       # dissolve frames at a join
FADE = 0.005                 # audio de-click at every cut
VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-g", "50"]
AENC = ["-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2"]


class MasterError(Exception):
    pass


def probe(p: pathlib.Path, count: bool = False) -> dict:
    args = ["ffprobe", "-v", "error"] + (["-count_frames"] if count else []) + [
        "-show_entries", "stream=codec_type,r_frame_rate,nb_read_frames,nb_frames,duration",
        "-show_entries", "format=duration", "-of", "json", str(p)]
    r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), {})
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    return {"fps": num / den, "video_frames": int(v.get("nb_read_frames") or v.get("nb_frames") or 0),
            "video_s": float(v.get("duration") or 0), "audio_s": float(a.get("duration") or 0),
            "format_s": float(d["format"]["duration"])}


def frames_for(keep_s: list, fps: float, total_frames: int) -> list[tuple[int, int]]:
    """Seconds → whole-frame [start, end) ranges, clamped, in order, non-empty."""
    out = []
    for a, b in keep_s:
        s = max(0, round(float(a) * fps))
        e = total_frames if b in (None, "end") else min(total_frames, round(float(b) * fps))
        if e - s < XF:
            raise MasterError(f"a keep range {a}–{b} is shorter than the {XF}-frame dissolve.")
        if out and s < out[-1][1]:
            raise MasterError(f"keep ranges overlap or are out of order at {a}s.")
        out.append((s, e))
    if not out:
        raise MasterError("nothing to keep.")
    return out


def filter_graph(ranges: list[tuple[int, int]], fps: float) -> str:
    """Video: trimmed pieces chained with xfade inside each join; audio: exact cuts, concat."""
    t = lambda f: round(f / fps, 6)          # noqa: E731
    half = XF // 2
    n = len(ranges)
    parts = []
    for k, (s, e) in enumerate(ranges):
        vs = s - (half if k > 0 else 0)
        ve = e + (half if k < n - 1 else 0)
        parts.append(f"[0:v]trim=start_frame={vs}:end_frame={ve},setpts=PTS-STARTPTS[v{k}]")
        dur = t(e - s)
        fades = f"afade=t=in:d={FADE}" if k > 0 or s > 0 else ""
        out_fade = f"afade=t=out:st={round(dur - FADE, 6)}:d={FADE}"
        chain = ",".join(x for x in ("asetpts=PTS-STARTPTS", fades, out_fade) if x)
        parts.append(f"[0:a]atrim=start={t(s)}:end={t(e)},{chain}[a{k}]")
    if n == 1:
        parts.append("[v0]null[v]")
    else:
        acc, kept = "v0", 0
        for k in range(1, n):
            kept += ranges[k - 1][1] - ranges[k - 1][0]
            out = "v" if k == n - 1 else f"x{k}"
            parts.append(f"[{acc}][v{k}]xfade=transition=fade:duration={t(XF)}:"
                         f"offset={t(kept - half)}[{out}]")
            acc = out
    parts.append("".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1[a]")
    return ";".join(parts)


def join_wavs(master: pathlib.Path, ranges: list[tuple[int, int]], fps: float,
              out_dir: pathlib.Path, code: str) -> list[str]:
    """3 seconds either side of every join, on the MASTER's clock, for Jodie's ear."""
    out_dir.mkdir(parents=True, exist_ok=True)
    made, at = [], 0
    for k in range(1, len(ranges)):
        at += ranges[k - 1][1] - ranges[k - 1][0]
        w = out_dir / f"{code}-join-{k}.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-ss",
                        f"{max(0.0, at / fps - 3):.3f}", "-t", "6", "-i", str(master),
                        "-vn", "-ac", "2", "-ar", "48000", str(w)], check=True, timeout=300)
        made.append(str(w))
    return made


def make(ep: int, code: str, keep_s: list, source: pathlib.Path | None = None,
         out_dir: pathlib.Path | None = None, force: bool = False, why: str = "",
         pp: pathlib.Path | None = None) -> dict:
    ep_dir = ep_paths.episode_dir(ep, pp) if pp else ep_paths.episode_dir(ep)
    renders = ep_dir / "renders"
    src = source or renders / f"PP-EP{ep:02d}-{code}-full.mp4"
    if not src.is_file():
        raise MasterError(f"no render at {src}.")
    dest_dir = out_dir or renders
    dest = dest_dir / f"{code}-master.mp4"
    if dest.exists() and not force:
        raise MasterError(f"{dest} already exists. It may be the master a cut was built from; "
                          "pass --force only on purpose (keep the old one under another name first).")
    info = probe(src, count=True)
    fps, total = info["fps"], info["video_frames"]
    ranges = frames_for(keep_s, fps, total)
    import render_lock
    tmp = dest.with_suffix(".part.mp4")
    with render_lock.hold("PP", f"EP{ep} {code} master"):
        print(f"  ffmpeg: {code} master from {src.name}, {len(ranges)} range(s) ...", flush=True)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", str(src),
                            "-filter_complex", filter_graph(ranges, fps), "-map", "[v]", "-map",
                            "[a]"] + VENC + ["-r", f"{fps:g}"] + AENC +
                           ["-movflags", "+faststart", str(tmp)],
                           capture_output=True, text=True, timeout=7200)
        if r.returncode:
            raise MasterError(f"ffmpeg failed making the {code} master:\n{r.stderr[-1500:]}")
    got = probe(tmp, count=True)
    want = sum(e - s for s, e in ranges)
    if abs(got["video_frames"] - want) > 1 or abs(got["audio_s"] - want / fps) > 1.5 / fps:
        raise MasterError(f"the {code} master measures {got['video_frames']} frames / "
                          f"{got['audio_s']:.3f}s audio; it should be {want} frames = "
                          f"{want / fps:.3f}s. Not promoted: {tmp}")
    tmp.replace(dest)
    joins = join_wavs(dest, ranges, fps, ep_dir / "output/qc/joins" if not out_dir
                      else dest_dir / "joins", code)
    rec = {"source": src.name, "out": dest.name, "made": time.strftime("%Y-%m-%d %H:%M"),
           "fps": fps, "kept_frames": [list(r) for r in ranges],
           "kept_s": [[round(s / fps, 3), round(e / fps, 3)] for s, e in ranges],
           "removed_s": ([[0, round(ranges[0][0] / fps, 3)]] if ranges[0][0] else []) +
                        [[round(ranges[k - 1][1] / fps, 3), round(ranges[k][0] / fps, 3)]
                         for k in range(1, len(ranges))] +
                        ([[round(ranges[-1][1] / fps, 3), round(total / fps, 3)]]
                         if ranges[-1][1] < total else []),
           "dissolve_frames": XF if len(ranges) > 1 else 0,
           "video_frames": got["video_frames"], "audio_s": round(got["audio_s"], 3),
           "bytes": dest.stat().st_size, "join_wavs": joins, "why": why,
           "tool": "engine/twoway_masters.py"}
    log = dest_dir / f"masters-EP{ep:02d}.json"
    allrec = json.loads(log.read_text(encoding="utf-8")) if log.is_file() else {}
    if code in allrec:
        allrec.setdefault("_history", []).append({code: allrec[code]})
    allrec[code] = rec
    log.write_text(json.dumps(allrec, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  {dest.name}: {got['video_frames']} frames = {got['video_frames'] / fps:.3f}s, "
          f"audio {got['audio_s']:.3f}s; removed {rec['removed_s']}; joins {len(joins)}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep", type=int)
    ap.add_argument("code")
    ap.add_argument("--words", help="the JSON written by twoway_render_words.py (uses keep_s)")
    ap.add_argument("--keep", action="append", default=[],
                    help="A-B in seconds (B may be 'end'); repeat for several ranges")
    ap.add_argument("--source")
    ap.add_argument("--out-dir")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--why", default="")
    a = ap.parse_args()
    if a.words:
        w = json.loads(pathlib.Path(a.words).read_text(encoding="utf-8"))
        if w.get("needs_jodie"):
            print("NOT MADE — the render has things only Jodie can rule on:", file=sys.stderr)
            for x in w["needs_jodie"]:
                print("  · " + x, file=sys.stderr)
            return 1
        keep = w["keep_s"]
    else:
        keep = [[x.split("-")[0], x.split("-")[1]] for x in a.keep]
    try:
        make(a.ep, a.code, keep, pathlib.Path(a.source) if a.source else None,
             pathlib.Path(a.out_dir) if a.out_dir else None, a.force, a.why)
    except MasterError as e:
        print(f"HALT: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
