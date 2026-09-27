#!/usr/bin/env python3
"""robotic_voice_detector.py -- find stretches where a HeyGen render's voice has
gone flat/monotone or otherwise lost normal pitch movement, without a human
listening to the whole thing.

    python engine/robotic_voice_detector.py <video_or_wav> --out-csv OUT.csv
        [--out-plot OUT.png] [--suspects-out OUT.md] [--label "EP46"]
        [--window 3.0] [--hop 1.0] [--start 0] [--end 0]
        [--flag-below N] [--flag-percentile P]

🔴 WHY PITCH MOVEMENT, NOT LOUDNESS OR SPECTRAL SHAPE. Jodie's two named failure
modes -- "the voice sounds robotic" and "the Australian accent gets sort of
really, really broad ... you can't even understand it" -- are both, at bottom, a
collapse in how much the fundamental frequency (F0) moves from moment to moment.
Ordinary speech constantly rises and falls in pitch (that IS prosody); a flat/
monotone voice stops doing that; a mangled, over-broad rendering typically loses
the same normal micro-variation on its way to sounding wrong. Loudness and
spectral-tilt measures would catch neither reliably -- a robotic render can be
just as loud and just as spectrally ordinary as a good one, frame by frame.

THE UNIT: semitones, not Hz. F0 in Hz means different things at different
absolute pitches (10 Hz of wobble is huge at 100 Hz and tiny at 300 Hz).
Converting to semitones relative to an arbitrary reference (100 Hz here -- the
reference cancels out in a within-window standard deviation, so its exact value
does not matter) makes the variation measure comparable across a whole file and
across different renders of the same voice.

THE CORE SIGNAL is the standard deviation of semitone-F0 across the VOICED
frames inside a sliding window (default 3s windows, 1s hop -- tune with --window/
--hop if the validation step needs it, and re-validate if you do). A window
that is mostly silence (a paragraph pause) is not "flat voice", it is a pause --
so a window's std is only computed when enough of it is actually voiced
(--min-voiced-frac, default 0.3), otherwise it is written as an empty CSV cell
and excluded from flagging. F0 range (max-min semitones) and the mean
harmonics-to-noise ratio (HNR, via Praat's cross-correlation harmonicity) are
carried alongside as a second and third axis -- HNR in particular should tell
apart "flat but clean" from "flat and full of digital mush", which pitch alone
cannot.

⚠️ THIS IS THE MEASUREMENT INSTRUMENT ONLY. It is deliberately NOT wired into
qc_episode.py or any build step -- that is a separate decision, after a human
has seen it work on a real, known-bad render. See PP-EP46/output/qc/
ROBOT-DETECTOR-REPORT.md for the validation this was run against before anyone
trusted a single number out of it.

Needs `ffmpeg` on PATH and `pip install praat-parselmouth` (a thin, fast binding
to the Praat acoustic-analysis engine -- no browser, no GPU, runs in seconds on
a 12-minute file).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

REF_HZ = 100.0            # semitone reference -- cancels out in a within-window std
PITCH_FLOOR = 75.0        # Hz -- comfortably below an adult male voice's F0 floor
PITCH_CEILING = 500.0     # Hz -- comfortably above it, catches emphasis peaks
TIME_STEP = 0.01          # 10ms Praat analysis frames, well inside a 1s hop


def extract_wav(src: Path, wav_out: Path, sr: int = 16000) -> None:
    """Mono 16kHz PCM via ffmpeg. Pitch/HNR analysis needs none of a video's
    frames or a stereo mix in memory -- this keeps the whole pipeline to a few
    tens of MB, deliberately, on an 8GB machine shared with another project's
    builds."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src),
           "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(wav_out)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not wav_out.is_file():
        raise RuntimeError(f"ffmpeg could not extract audio from {src}: {(r.stderr or '').strip()[-500:]}")


def analyse(wav_path: Path, window_s: float, hop_s: float, min_voiced_frac: float):
    """Sliding-window pitch/HNR stats. Returns (rows, duration_s).

    Each row: t_start, t_end, voiced_frac, n_voiced_frames, f0_std_semitones,
    f0_range_semitones, hnr_mean_db -- the last three are None where the window
    is not voiced enough to mean anything (see module docstring)."""
    import parselmouth

    snd = parselmouth.Sound(str(wav_path))
    duration = snd.get_total_duration()

    pitch = snd.to_pitch(time_step=TIME_STEP, pitch_floor=PITCH_FLOOR, pitch_ceiling=PITCH_CEILING)
    p_times = np.asarray(pitch.xs())
    p_freqs = np.asarray(pitch.selected_array["frequency"])
    voiced_all = p_freqs > 0

    harm = snd.to_harmonicity_cc(time_step=TIME_STEP)
    h_times = np.asarray(harm.xs())
    h_vals = np.asarray(harm.values).flatten()

    rows = []
    t = 0.0
    while t < duration:
        t_end = min(t + window_s, duration)

        psel = (p_times >= t) & (p_times < t_end)
        n_frames = int(psel.sum())
        vsel = psel & voiced_all
        n_voiced = int(vsel.sum())
        voiced_frac = (n_voiced / n_frames) if n_frames else 0.0

        f0_std = f0_range = None
        if n_voiced >= 5 and voiced_frac >= min_voiced_frac:
            semis = 12.0 * np.log2(p_freqs[vsel] / REF_HZ)
            f0_std = round(float(np.std(semis)), 3)
            f0_range = round(float(np.max(semis) - np.min(semis)), 3)

        hsel = (h_times >= t) & (h_times < t_end)
        hvv = h_vals[hsel]
        hvv = hvv[hvv > -100.0]     # Praat's "undefined" sentinel is -200
        hnr_mean = round(float(np.mean(hvv)), 2) if hvv.size else None

        rows.append({
            "t_start": round(t, 2), "t_end": round(t_end, 2),
            "voiced_frac": round(voiced_frac, 3), "n_voiced_frames": n_voiced,
            "f0_std_semitones": f0_std, "f0_range_semitones": f0_range,
            "hnr_mean_db": hnr_mean,
        })
        t += hop_s
    return rows, duration


def write_csv(rows, out_csv: Path) -> None:
    import csv
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                            ["t_start", "t_end", "voiced_frac", "n_voiced_frames",
                             "f0_std_semitones", "f0_range_semitones", "hnr_mean_db"])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_plot(rows, out_png: Path, flagged_idx: set[int], label: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = [r["t_start"] for r in rows]
    y = [r["f0_std_semitones"] if r["f0_std_semitones"] is not None else float("nan") for r in rows]
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(t, y, color="#2b6cb0", linewidth=1.0, label="F0 std (semitones/window)")
    if flagged_idx:
        fx = [rows[i]["t_start"] for i in sorted(flagged_idx)]
        fy = [rows[i]["f0_std_semitones"] for i in sorted(flagged_idx)]
        ax.scatter(fx, fy, color="#c53030", s=14, zorder=3, label="flagged (flat)")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("F0 std within window (semitones)")
    ax.set_title(f"Pitch-variation over time -- {label}")
    ax.legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def mmss(t: float) -> str:
    m, s = divmod(int(round(t)), 60)
    return f"{m}:{s:02d}"


def flag_stretches(rows, threshold: float | None, percentile: float | None):
    """Which windows count as 'flat', and the contiguous stretches they form.

    Exactly one of threshold/percentile is used: an absolute f0_std_semitones
    ceiling, or a percentile of this file's OWN voiced-window distribution
    (useful for a first look; an absolute number, carried over from the
    validation step, is the trustworthy one -- see the module docstring)."""
    voiced_rows = [(i, r) for i, r in enumerate(rows) if r["f0_std_semitones"] is not None]
    if not voiced_rows:
        return set(), []
    if threshold is None:
        vals = np.array([r["f0_std_semitones"] for _, r in voiced_rows])
        threshold = float(np.percentile(vals, percentile if percentile is not None else 15.0))
    flagged = {i for i, r in voiced_rows if r["f0_std_semitones"] <= threshold}

    stretches = []
    cur = []
    for i, r in enumerate(rows):
        if i in flagged:
            cur.append(i)
        elif cur:
            stretches.append(cur)
            cur = []
    if cur:
        stretches.append(cur)

    out = []
    for s in stretches:
        vals = [rows[i]["f0_std_semitones"] for i in s]
        out.append({
            "t_start": rows[s[0]]["t_start"], "t_end": rows[s[-1]]["t_end"],
            "mean_f0_std": round(float(np.mean(vals)), 3),
            "min_f0_std": round(float(np.min(vals)), 3),
            "n_windows": len(s),
        })
    out.sort(key=lambda d: d["mean_f0_std"])   # worst (lowest variation) first
    return flagged, out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("input", help="video or audio file")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-plot")
    ap.add_argument("--suspects-out", help="write the plain suspect-timestamp list here (markdown)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--window", type=float, default=3.0)
    ap.add_argument("--hop", type=float, default=1.0)
    ap.add_argument("--min-voiced-frac", type=float, default=0.3)
    ap.add_argument("--start", type=float, default=0.0, help="analyse only from this many seconds in")
    ap.add_argument("--end", type=float, default=0.0, help="analyse only up to this many seconds (0 = whole file)")
    ap.add_argument("--flag-below", type=float, default=None,
                     help="absolute f0_std_semitones ceiling for 'flat' (from calibration)")
    ap.add_argument("--flag-percentile", type=float, default=None,
                     help="flag this file's own bottom P%% of voiced windows (first-look only)")
    args = ap.parse_args(argv)

    src = Path(args.input)
    label = args.label or src.stem

    tmp_wav = None
    try:
        if src.suffix.lower() in (".wav",):
            wav_path = src
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            tmp_wav = Path(tmp.name)
            extract_wav(src, tmp_wav)
            wav_path = tmp_wav

        rows, duration = analyse(wav_path, args.window, args.hop, args.min_voiced_frac)

        if args.start or args.end:
            end = args.end if args.end else duration
            rows = [r for r in rows if r["t_start"] >= args.start and r["t_end"] <= end]

        write_csv(rows, Path(args.out_csv))
        print(f"{label}: {len(rows)} windows over {duration:.1f}s -> {args.out_csv}")

        voiced_vals = [r["f0_std_semitones"] for r in rows if r["f0_std_semitones"] is not None]
        if voiced_vals:
            print(f"  f0_std_semitones over voiced windows: "
                  f"mean={np.mean(voiced_vals):.3f} median={np.median(voiced_vals):.3f} "
                  f"std={np.std(voiced_vals):.3f} min={np.min(voiced_vals):.3f} max={np.max(voiced_vals):.3f} "
                  f"n={len(voiced_vals)}/{len(rows)}")

        flagged_idx, stretches = set(), []
        if args.flag_below is not None or args.flag_percentile is not None:
            flagged_idx, stretches = flag_stretches(rows, args.flag_below, args.flag_percentile)
            print(f"  {len(stretches)} flagged stretch(es), worst first:")
            for s in stretches:
                print(f"    {mmss(s['t_start'])}-{mmss(s['t_end'])}  "
                      f"mean_f0_std={s['mean_f0_std']} min={s['min_f0_std']} windows={s['n_windows']}")

        if args.out_plot:
            write_plot(rows, Path(args.out_plot), flagged_idx, label)
            print(f"  plot -> {args.out_plot}")

        if args.suspects_out:
            p = Path(args.suspects_out)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"# Suspect stretches -- {label}\n\n")
                if not stretches:
                    f.write("No flagging threshold was given (--flag-below/--flag-percentile), "
                            "or none of this file's windows fell below it.\n")
                else:
                    f.write("Worst first (lowest mean pitch-variation):\n\n")
                    for s in stretches:
                        f.write(f"- **{mmss(s['t_start'])}-{mmss(s['t_end'])}** "
                                f"({s['t_start']}s-{s['t_end']}s) -- "
                                f"mean f0_std {s['mean_f0_std']} semitones, "
                                f"min {s['min_f0_std']}, {s['n_windows']} window(s)\n")
            print(f"  suspects -> {p}")

        return 0
    finally:
        if tmp_wav is not None:
            tmp_wav.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
