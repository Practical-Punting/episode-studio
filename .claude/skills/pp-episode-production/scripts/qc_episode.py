#!/usr/bin/env python3
"""One-command episode QC for the Practical Punting pipeline.

Usage:
    python qc_episode.py <final.mp4> <shot-map.json> <out_dir> [--head 7.0]

Runs a battery of checks against a finished episode and writes a QC report +
visual aids (contact sheet, logo crop) into <out_dir>:

  1. ffprobe   - duration / resolution / fps / video+audio codec / audio bitrate.
                 HARD FAIL if audio < 180 kbps, not 1920x1080, or not 25 fps.
  2. Frames    - one mid-beat frame per shot (labelled shot# + framing) plus 3
                 frames across the last 15s, tiled into a contact-sheet PNG.
  3. Logo crop - bottom-right crop at mid-body -> logo_br.png (eyeball the chip).
  4. Audio     - integrated loudness + true-peak (ebur128); RMS at ~5 windows
                 across the file; HARD FAIL if the last-8s RMS <= -40 dB
                 ("ending not silent" check - a real EP bug).
  5. Report    - PASS/ISSUES summary to stdout + <out_dir>/QC-REPORT.md.
                 Exits non-zero if any hard check fails.

shot-map.json times are PRESENTER-relative; the final has a title head prepended
(default 7.0s, override with --head), so `head` is added when sampling the final.

Every stage is wrapped defensively - a stage that blows up records an ISSUE and
the rest of the QC still runs.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# tool resolution
# ---------------------------------------------------------------------------
def _resolve(tool):
    """Find ffmpeg/ffprobe via PATH, else the winget Gyan.FFmpeg bin."""
    p = shutil.which(tool)
    if p:
        return p
    local = os.environ.get("LOCALAPPDATA", "")
    root = os.path.join(local, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(root):
        for dirpath, _dirs, files in os.walk(root):
            exe = tool + (".exe" if os.name == "nt" else "")
            if exe in files and "Gyan.FFmpeg" in dirpath:
                return os.path.join(dirpath, exe)
    # last resort: hope it's on PATH at call time
    return tool


FFMPEG = _resolve("ffmpeg")
FFPROBE = _resolve("ffprobe")
FONT = r"C\\:/Windows/Fonts/arialbd.ttf"         # drawtext path (colon double-escaped
                                                 # through ffmpeg's two-level filter parser)
FONT_FILE = r"C:/Windows/Fonts/arialbd.ttf"      # plain path, for existence test


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ---------------------------------------------------------------------------
# results container
# ---------------------------------------------------------------------------
class QC:
    def __init__(self):
        self.probe = {}
        self.loudness = {}
        self.rms = []            # list of (label, t0, t1, db)
        self.hard_fails = []     # each fails the run
        self.warnings = []       # noted, do not fail
        self.notes = []          # info lines
        self.artifacts = []      # produced files

    def fail(self, msg):
        self.hard_fails.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.notes.append(msg)


# ---------------------------------------------------------------------------
# stage 1 - ffprobe
# ---------------------------------------------------------------------------
def stage_probe(qc, final):
    try:
        r = run([FFPROBE, "-v", "error", "-print_format", "json",
                 "-show_format", "-show_streams", final])
        if r.returncode != 0:
            qc.fail(f"ffprobe failed: {r.stderr.strip()[:200]}")
            return None
        data = json.loads(r.stdout)
        v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
        a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
        fmt = data.get("format", {})

        dur = float(fmt.get("duration", 0) or 0)
        p = {"duration": dur}

        if v:
            p["width"] = int(v.get("width", 0))
            p["height"] = int(v.get("height", 0))
            rfr = v.get("r_frame_rate", "0/1")
            try:
                num, den = rfr.split("/")
                fps = float(num) / float(den) if float(den) else 0.0
            except Exception:
                fps = 0.0
            p["fps"] = fps
            p["vcodec"] = v.get("codec_name", "?")
        else:
            qc.fail("no video stream found")

        if a:
            p["acodec"] = a.get("codec_name", "?")
            abr = a.get("bit_rate")
            if abr in (None, "N/A", "", "0"):
                # fall back to format-level bitrate as a rough proxy
                abr = fmt.get("bit_rate")
            try:
                p["abitrate"] = int(abr) if abr not in (None, "N/A", "") else None
            except Exception:
                p["abitrate"] = None
            p["asample_rate"] = a.get("sample_rate", "?")
            p["achannels"] = a.get("channels", "?")
        else:
            qc.fail("no audio stream found")

        qc.probe = p

        # --- hard checks ---
        if v:
            if (p.get("width"), p.get("height")) != (1920, 1080):
                qc.fail(f"resolution {p.get('width')}x{p.get('height')} != 1920x1080")
            if abs(p.get("fps", 0) - 25.0) > 0.05:
                qc.fail(f"fps {p.get('fps'):.3f} != 25")
        if a:
            abr = p.get("abitrate")
            if abr is None:
                qc.warn("audio bitrate unavailable from probe")
            elif abr < 180_000:
                qc.fail(f"audio bitrate {abr/1000:.0f} kbps < 180 kbps")
        return p
    except Exception as e:
        qc.fail(f"probe stage error: {e}")
        return None


# ---------------------------------------------------------------------------
# stage 2 - frames + contact sheet
# ---------------------------------------------------------------------------
def _extract_frame(t, out_png, label=None):
    """Extract one 640px-wide frame at time t. Returns True on success."""
    vf = "scale=640:-1"
    if label:
        safe = label.replace(":", r"\:").replace("'", r"\'")
        vf = (f"scale=640:-1,drawtext=fontfile={FONT}:text='{safe}':"
              "x=12:y=10:fontsize=28:fontcolor=white:"
              "box=1:boxcolor=black@0.6:boxborderw=8")
    r = run([FFMPEG, "-y", "-ss", f"{t:.3f}", "-i", _extract_frame.src,
             "-frames:v", "1", "-vf", vf, out_png])
    return r.returncode == 0 and os.path.exists(out_png) and os.path.getsize(out_png) > 0


def stage_frames(qc, final, beats, head, out_dir):
    _extract_frame.src = final
    try:
        dur = qc.probe.get("duration", 0) or 0
        tmp = tempfile.mkdtemp(prefix="qc_frames_")
        frames = []
        drawtext_ok = os.path.exists(FONT_FILE)
        if not drawtext_ok:
            qc.warn(f"font {FONT_FILE} missing - contact sheet unlabelled")

        idx = 0
        # one mid-beat frame per shot
        for b in beats:
            try:
                mid = float(b["start"]) + head + (float(b["end"]) - float(b["start"])) / 2.0
                if dur and mid > dur:
                    mid = max(0.0, dur - 0.5)
                label = f"{b.get('shot','?')} {b.get('framing','')}".strip() if drawtext_ok else None
                out_png = os.path.join(tmp, f"f_{idx:04d}.png")
                ok = _extract_frame(mid, out_png, label)
                if not ok and label:  # drawtext may have failed - retry plain
                    ok = _extract_frame(mid, out_png, None)
                if ok:
                    frames.append(out_png)
                    idx += 1
            except Exception as e:
                qc.warn(f"beat {b.get('shot','?')} frame failed: {e}")

        # 3 frames across the last 15s (end sequence)
        if dur > 0:
            end_start = max(0.0, dur - 15.0)
            for k in range(3):
                t = end_start + (k + 0.5) * (min(15.0, dur) / 3.0)
                t = min(t, dur - 0.3)
                label = f"END {k+1}" if drawtext_ok else None
                out_png = os.path.join(tmp, f"f_{idx:04d}.png")
                ok = _extract_frame(t, out_png, label)
                if not ok and label:
                    ok = _extract_frame(t, out_png, None)
                if ok:
                    frames.append(out_png)
                    idx += 1

        if not frames:
            qc.warn("no frames extracted - contact sheet skipped")
            return

        n = len(frames)
        cols = int(math.ceil(math.sqrt(n)))
        rows = int(math.ceil(n / cols))
        qc.note(f"contact sheet: {n} frames, {cols}x{rows} grid")

        # renumber sequentially for image2 glob-free input
        seq = os.path.join(tmp, "seq_%04d.png")
        for i, fpng in enumerate(frames):
            os.replace(fpng, os.path.join(tmp, f"seq_{i:04d}.png"))

        sheet = os.path.join(out_dir, "contact-sheet.png")
        r = run([FFMPEG, "-y", "-framerate", "1", "-start_number", "0",
                 "-i", seq, "-frames:v", "1",
                 "-vf", f"tile={cols}x{rows}:padding=6:margin=6:color=0x202020",
                 sheet])
        if r.returncode == 0 and os.path.exists(sheet):
            qc.artifacts.append(sheet)
            qc.note(f"contact sheet -> {sheet}")
        else:
            qc.warn(f"tile failed: {r.stderr.strip()[-200:]}")
    except Exception as e:
        qc.warn(f"frames stage error: {e}")


# ---------------------------------------------------------------------------
# stage 3 - logo crop
# ---------------------------------------------------------------------------
def stage_logo(qc, final, out_dir):
    try:
        dur = qc.probe.get("duration", 0) or 0
        t = dur / 2.0 if dur else 60.0
        out_png = os.path.join(out_dir, "logo_br.png")
        r = run([FFMPEG, "-y", "-ss", f"{t:.3f}", "-i", final,
                 "-frames:v", "1", "-vf", "crop=620:260:1300:820", out_png])
        if r.returncode == 0 and os.path.exists(out_png):
            qc.artifacts.append(out_png)
            qc.note(f"logo crop @ {t:.1f}s -> {out_png}")
        else:
            qc.warn(f"logo crop failed: {r.stderr.strip()[-200:]}")
    except Exception as e:
        qc.warn(f"logo stage error: {e}")


# ---------------------------------------------------------------------------
# stage 4 - audio
# ---------------------------------------------------------------------------
def stage_loudness(qc, final):
    try:
        r = run([FFMPEG, "-hide_banner", "-i", final,
                 "-af", "ebur128=peak=true", "-f", "null", "-"])
        txt = r.stderr
        # ebur128 prints per-frame running values throughout, then a final
        # "Summary:" block. Parse ONLY the summary (per-frame I: starts at
        # -70 LUFS and would otherwise be matched first).
        si = txt.rfind("Summary:")
        summ = txt[si:] if si != -1 else txt
        mi = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", summ)
        mlra = re.search(r"LRA:\s*(-?[\d.]+)\s*LU", summ)
        tps = re.findall(r"Peak:\s*(-?[\d.]+)\s*dBFS", summ)
        if mi:
            qc.loudness["I"] = float(mi.group(1))
        if mlra:
            qc.loudness["LRA"] = float(mlra.group(1))
        if tps:
            qc.loudness["true_peak"] = float(tps[-1])
        if not mi:
            qc.warn("could not parse integrated loudness from ebur128")
    except Exception as e:
        qc.warn(f"loudness stage error: {e}")


def _rms_window(final, t0, dur):
    """Overall RMS level (dB) over [t0, t0+dur]. None on failure."""
    r = run([FFMPEG, "-hide_banner", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}",
             "-i", final, "-af", "astats=metadata=1", "-f", "null", "-"])
    vals = re.findall(r"RMS level dB:\s*(-?[\d.]+|-?inf)", r.stderr)
    if not vals:
        return None
    last = vals[-1]  # overall block is emitted last
    if last.lstrip("-").startswith("inf"):
        return -float("inf")
    try:
        return float(last)
    except Exception:
        return None


def stage_rms(qc, final):
    try:
        dur = qc.probe.get("duration", 0) or 0
        if dur <= 0:
            qc.warn("no duration - RMS windows skipped")
            return
        win = 3.0
        # ~5 windows across the body
        for frac in (0.10, 0.30, 0.50, 0.70, 0.90):
            t0 = max(0.0, min(dur - win, frac * dur))
            db = _rms_window(final, t0, win)
            qc.rms.append((f"{int(frac*100)}%", t0, t0 + win, db))

        # ending-not-silent check: last 8s
        end_len = min(8.0, dur)
        t0 = max(0.0, dur - end_len)
        end_db = _rms_window(final, t0, end_len)
        qc.rms.append(("last 8s", t0, t0 + end_len, end_db))
        if end_db is None:
            qc.warn("could not measure ending RMS")
        elif end_db <= -40.0:
            qc.fail(f"ending is silent: last-8s RMS {end_db:.1f} dB <= -40 dB")
        else:
            qc.note(f"ending not silent: last-8s RMS {end_db:.1f} dB")
    except Exception as e:
        qc.warn(f"RMS stage error: {e}")


# ---------------------------------------------------------------------------
# midroll wording window (Jodie, 28 Jul 2026)
#
# The spoken midroll now comes from a FIXED POOL OF TEN pre-approved lines used
# strictly in order (docs/midroll-line-pool.md): episode N takes L[N mod 10].
#
# NINE, NOT TEN - DO NOT "CORRECT" THIS. That cycle recurs at EXACTLY
# ten-episode intervals: L3 runs at EP13 and again at EP23. A ten-episode window
# would contain EP13 when EP23 is checked, and would hard-fail every episode
# from EP23 onward, forever. At nine, the nearest legitimate prior use is always
# exactly ten back and passes; any accidental duplication closer than that fails,
# which is the intent.
#
# These three helpers are DELIBERATELY DUPLICATED from render_ready.py rather
# than imported from a shared module. qc_episode.py is protected by a byte-for-
# byte integrity gate (engine/providers.py::_qc_integrity_gate); a shared import
# would be an UNGATED back door into the checker, which is precisely the drift
# the gate exists to stop. Twenty duplicated lines is the lesser evil. If you
# change one copy, change the other.
# ---------------------------------------------------------------------------
MIDROLL_WINDOW = 9


def _ep_num(folder_path):
    """Episode number parsed from a PP-EPnn folder path, or None.

    Handles bare stems (PP-EP03) and post-Stage-8 renames
    (PP-EP01-The-Trifecta-Mistake). None for unnumbered dev folders."""
    m = re.search(r"PP-EP(\d+)", os.path.basename(os.path.normpath(folder_path)))
    return int(m.group(1)) if m else None


def midroll_window(ep_dir, window=MIDROLL_WINDOW):
    """Spoken-words files of the `window` episodes immediately BEFORE this one.

    Ordered by EPISODE NUMBER, never by file mtime. PP-EP98 is a test folder
    sitting beside the real episodes; mtime ordering would drag it into every
    real episode's window, numeric ordering keeps it out."""
    import glob as _glob
    mine = _ep_num(ep_dir)
    if mine is None:
        return []
    root = os.path.dirname(os.path.abspath(os.path.normpath(ep_dir)))
    found = []
    for other in _glob.glob(os.path.join(root, "PP-EP*", "docs", "spoken-words.txt")):
        n = _ep_num(os.path.dirname(os.path.dirname(other)))
        if n is not None and n < mine:
            found.append((n, other))
    found.sort(key=lambda t: t[0], reverse=True)
    return found[:window]


def midroll_clash(mine_text, ep_dir, window=MIDROLL_WINDOW):
    """(episode folder name, count compared) - the first episode inside the
    window already carrying this exact wording, or (None, count)."""
    prior = midroll_window(ep_dir, window)
    for _n, other in prior:
        try:
            if mine_text and mine_text in open(other, encoding="utf-8").read():
                return os.path.basename(os.path.dirname(os.path.dirname(other))), len(prior)
        except OSError:
            continue
    return None, len(prior)


# ---------------------------------------------------------------------------
# stage 4b - end sequence + midroll (contract checks; needs --episode)
# ---------------------------------------------------------------------------
def _mean_luma(final, t):
    """Mean luminance (0-255) of one frame at t. None on failure."""
    import subprocess
    r = subprocess.run([FFMPEG, "-hide_banner", "-ss", f"{t:.3f}", "-i", final,
                        "-frames:v", "1", "-vf", "scale=64:36,format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return sum(r.stdout) / len(r.stdout)


def stage_end_sequence(qc, final, beats, head, episode_path, out_dir):
    """The EP08 lessons, made structural (outro + audio standards):
    1. breathing room - the last word lands well before the end;
    2. the end card is ON SCREEN through the e-book mention until the warranty;
    3. the sting sits audibly under the warranty (never silent);
    4. the midroll segment is exported for HUMAN ears + its wording must be
       unique across episodes (HeyGen mangles repeated identical text)."""
    try:
        ep = json.load(open(episode_path, encoding="utf-8"))
    except Exception as e:
        qc.warn(f"--episode unreadable ({e}) - end-sequence checks skipped")
        return
    B = ep.get("build", {})
    if not beats:
        qc.warn("no shot map - end-sequence checks skipped")
        return
    bs = lambda n: beats[n - 1]["start"] + head
    SPEECH_END = beats[-1]["end"] + head
    settle = B.get("end_settle", 3.0)
    wtail = B.get("warranty_tail", 6.7)
    war_ti = SPEECH_END + B.get("warranty_lead", 0.3)
    dur = qc.probe.get("duration") or 0

    # 1. breathing room (the ~3s tail)
    room = dur - SPEECH_END
    if room < settle + wtail - 0.7:
        qc.fail(f"speech runs too close to the end: last word at {SPEECH_END:.1f}s of "
                f"{dur:.1f}s ({room:.1f}s tail; standard wants ~{settle + wtail:.1f}s "
                "settle + warranty)")
    else:
        qc.note(f"end breathing room ok: {room:.1f}s after the last word")

    # 2. end card on screen through the e-book mention until the warranty
    cards = {c.get("id"): c for c in ep.get("cards", [])}
    end_id = B.get("standing", {}).get("endcard")
    ecb = B.get("endcard_beat", (cards.get(end_id) or {}).get("beat"))
    if ecb:
        ec_ti = bs(ecb) + B.get("endcard_lead", 1.5)
        if B.get("signoff_beat"):
            ec_end = bs(B["signoff_beat"]) - 0.3
        elif "endcard_hold" in B:
            ec_end = ec_ti + B["endcard_hold"]
        else:
            ec_end = war_ti + 0.6
        if ec_end < war_ti - 0.7:
            qc.fail(f"end card leaves at {ec_end:.1f}s but the warranty only takes over "
                    f"at {war_ti:.1f}s - it must stay up through the e-book mention "
                    "(drop endcard_hold to use the hold-to-warranty default)")
        t = min(ec_ti + 1.0, dur - 0.2)
        luma = _mean_luma(final, t)
        if luma is None:
            qc.warn("could not sample the end-card frame")
        elif luma > 70:
            qc.fail(f"end card not visibly on screen during the e-book beat "
                    f"(frame at {t:.1f}s luma {luma:.0f} - too bright for the dark card)")
        else:
            qc.note(f"end card visible at the e-book beat (luma {luma:.0f} at {t:.1f}s)")

    # 3. sting audible under the warranty
    if dur > war_ti + 2:
        db = _rms_window(final, war_ti + 0.8, max(1.5, dur - war_ti - 1.3))
        if db is None:
            qc.warn("could not measure warranty-window RMS")
        elif db <= -34.0:
            qc.fail(f"end music missing/too quiet under the warranty: RMS {db:.1f} dB "
                    "(the sting must return at the end card and sit soft under the warranty)")
        else:
            qc.note(f"end music present under the warranty: RMS {db:.1f} dB")

    # 4. midroll: export for human ears + wording uniqueness
    mb = (B.get("midroll") or {}).get("beat")
    if mb and mb <= len(beats):
        t0, t1 = bs(mb), beats[mb - 1]["end"] + head
        wav = os.path.join(out_dir, "midroll-listen.wav")
        try:
            run([FFMPEG, "-hide_banner", "-y", "-ss", f"{t0:.2f}", "-t",
                 f"{t1 - t0:.2f}", "-i", final, wav])
            qc.warn(f"LISTEN (human ears required): midroll segment ({t0:.0f}-{t1:.0f}s) "
                    f"saved to {os.path.basename(wav)} - confirm the voice/accent stays Gordon")
        except Exception as e:
            qc.warn(f"could not export the midroll segment ({e})")
        try:
            ep_dir = os.path.dirname(os.path.dirname(os.path.abspath(episode_path)))
            sw = os.path.join(ep_dir, "docs", "spoken-words.txt")
            paras = [p.strip() for p in
                     open(sw, encoding="utf-8").read().split("\n\n") if p.strip()]
            mine = paras[mb - 1] if mb <= len(paras) else None
            if mine:
                which, compared = midroll_clash(mine, ep_dir)
                if which:
                    qc.fail(f"midroll wording reused VERBATIM from {which}, which is "
                            f"inside the {MIDROLL_WINDOW}-episode window - HeyGen "
                            "corrupts repeats. Take this episode's pool line "
                            "(L[N mod 10] from docs/midroll-line-pool.md); do NOT "
                            "reword it")
                else:
                    qc.note(f"midroll wording is fresh within the last "
                            f"{MIDROLL_WINDOW} episodes ({compared} compared)")
        except Exception as e:
            qc.warn(f"midroll uniqueness check skipped ({e})")


def _norm_words(t):
    """Lowercased alphanumeric words only - for stale-vs-locked text comparison."""
    return " ".join(re.findall(r"[a-z0-9]+", (t or "").lower()))


def _html_text(path):
    """Visible-ish text of an HTML file (tags/scripts/styles stripped,
    entities unescaped - '&mdash;' must not read as the word 'mdash')."""
    import html as _html
    t = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<title.*?</title>", " ", t, flags=re.S | re.I)  # metadata, not on-asset text
    return _html.unescape(re.sub(r"<[^>]+>", " ", t))


def stage_packaging(qc, episode_path, ep_dir):
    """PACKAGING-CONSISTENCY (PP-STANDARDS 25 Jul 2026). The slots are
    DELIBERATELY different; the sin is a STALE value. Each asset SOURCE must
    carry the currently-locked value for its slot (episode.json "packaging"):
      hook         -> title card + thumbnail headline (must agree = the hook)
      byline       -> title card + thumbnail
      youtube_title-> the recommended title in output/*youtube*.txt
      ebook_title  -> ebook/cover-src/cover.html
    HARD FAIL names the asset showing stale words."""
    try:
        ep = json.load(open(episode_path, encoding="utf-8"))
    except Exception as e:
        qc.warn(f"packaging check skipped (episode.json unreadable: {e})")
        return
    pk = ep.get("packaging")
    if not pk:
        qc.warn("packaging check skipped: no packaging block in episode.json "
                "(EP09+ must declare hook/byline/youtube_title/ebook_title)")
        return
    import glob as _g

    def _one(label, pattern, locked, slot):
        if not locked:
            return
        hits = _g.glob(os.path.join(ep_dir, pattern))
        if not hits:
            qc.warn(f"packaging: no {label} source found ({pattern})")
            return
        txt = _norm_words(_html_text(hits[0]) if hits[0].endswith(("html", "htm"))
                          else open(hits[0], encoding="utf-8", errors="ignore").read())
        if _norm_words(locked) in txt:
            qc.note(f"packaging ok: {label} carries the locked {slot}")
        else:
            qc.fail(f"packaging STALE: {label} ({os.path.basename(hits[0])}) does not "
                    f"carry the locked {slot} ({locked!r}) - it is showing old words; "
                    "rebuild it from the locked packaging")

    _one("thumbnail", os.path.join("thumbnail", "*thumbnail*.html"), pk.get("hook"), "hook")
    _one("thumbnail", os.path.join("thumbnail", "*thumbnail*.html"), pk.get("byline"), "byline")
    _one("title card", os.path.join("overlay", "export", "*title*.html"), pk.get("hook"), "hook")
    _one("title card", os.path.join("overlay", "export", "*title*.html"), pk.get("byline"), "byline")
    _one("YouTube copy", os.path.join("output", "*youtube*.txt"), pk.get("youtube_title"), "YouTube title")
    _one("e-book cover", os.path.join("ebook", "cover-src", "cover.html"), pk.get("ebook_title"), "e-book title")
    # review-only 'verify' markers must be RESOLVED (number or dash) before any
    # build that could be approved/published (EP09 par-tables rule, 25 Jul 2026)
    for src in _g.glob(os.path.join(ep_dir, "ebook", "*.html")):
        body = open(src, encoding="utf-8", errors="ignore").read()
        if re.search(r">\s*verify\s*<", body, re.I):
            qc.fail(f"e-book source {os.path.basename(src)} still contains review-only "
                    "'verify' marker(s) - every cell must resolve to a real number or a "
                    "dash before this build can be approved/published")
            break


def stage_numbers(qc, episode_path, ep_dir, out_dir):
    """NUMBERS CHECK (PP-STANDARDS 25 Jul 2026). Correctness is editorial, so a
    HUMAN ticks the figures: collect every number on the cards + any digits in
    the spoken track into numbers-check.md and WARN for confirmation."""
    lines = ["# Numbers check - confirm every figure below is correct", ""]
    n = 0
    import glob as _g
    for card in sorted(_g.glob(os.path.join(ep_dir, "overlay", "export", "*.html"))):
        base = os.path.basename(card)
        if "warranty" in base or "lowerthird" in base:
            continue
        txt = re.sub(r"\s+", " ", _html_text(card))
        for m in re.finditer(r"[$]?\d[\d,./%:x-]*(?:\s*(?:%|per cent|each-way|to break|profit))?", txt):
            ctx = txt[max(0, m.start() - 45):m.end() + 45].strip()
            lines.append(f"- **{m.group(0).strip()}**  ({base}): ...{ctx}...")
            n += 1
    try:
        sw = json.load(open(episode_path, encoding="utf-8")).get("spoken_words_file")
        if sw:
            swp = os.path.join(ep_dir, sw)
            for i, p in enumerate(open(swp, encoding="utf-8").read().split("\n\n"), 1):
                for m in re.finditer(r"\d[\d,./%:-]*", p):
                    lines.append(f"- **{m.group(0)}**  (spoken-words para {i}) "
                                 "<- digits in the SPOKEN track: should be words!")
                    n += 1
    except Exception:
        pass
    out = os.path.join(out_dir, "numbers-check.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    if n:
        qc.warn(f"CONFIRM (human): {n} figure(s) listed in numbers-check.md - "
                "tick every number/worked example before approving")
    else:
        qc.note("numbers check: no figures found on the cards")


def stage_timing_proof(qc, episode_path, ep_dir, head):
    """One sentence per card and overlay, in the finished file's own clock:

        "X appears at real time T, while Gordon is saying '…', and holds N seconds."

    (Jodie's ruling, 8 Aug 2026: timing is verified against the ACTUALLY-CREATED video,
    not a predicted timeline — and the proof is that sentence.)

    🔴 WHY IT IS COMPUTED AND NOT DETECTED FROM PIXELS. The obvious move is to look at
    the frames and find the overlay. That was tried on EP18 the same night and the
    detector was flaky twice over: the card region separated by a luma gap of 120 and
    read cleanly, while the chip's best region separated by 23 and reported an exit
    SEVEN SECONDS after the truth. A measurement you cannot trust is worse than an
    honest calculation, because it looks like evidence.
    So this reads the two things that ARE reliable: the forced-aligned SRT (the words,
    measured off the real audio) and the window the assembler actually used, shifted by
    the ONE head conversion. What makes it a proof rather than a restatement is that
    the words come from the audio and the times come from the graph — two independent
    sources meeting on the page, where a human can see they agree.
    """
    windows = getattr(qc, "timing_windows", None)
    if not windows:
        qc.warn("timing proof skipped — the card-timing stage did not run, so there "
                "are no windows to describe")
        return
    srt = os.path.join(ep_dir, "renders", "aligned.srt")
    if not os.path.isfile(srt):
        qc.warn("timing proof skipped — renders/aligned.srt is not there, so there is "
                "nothing measured off the audio to check the words against")
        return
    cues = []
    try:
        blocks = re.split(r"\n\s*\n", open(srt, encoding="utf-8").read().strip())
        for b in blocks:
            lines = [x for x in b.splitlines() if x.strip()]
            tl = next((x for x in lines if "-->" in x), None)
            if not tl:
                continue
            m = re.findall(r"(\d+):(\d+):(\d+)[,.](\d+)", tl)
            if len(m) < 2:
                continue
            s, e = [int(x) for x in m[0]], [int(x) for x in m[1]]
            cues.append((s[0]*3600+s[1]*60+s[2]+s[3]/1000 + head,
                         e[0]*3600+e[1]*60+e[2]+e[3]/1000 + head,
                         " ".join(lines[lines.index(tl)+1:])))
    except Exception as e:                                             # noqa: BLE001
        qc.warn(f"timing proof skipped — aligned.srt could not be read ({e})")
        return

    def spoken_at(t):
        hit = next((c for c in cues if c[0] <= t <= c[1]), None)
        if hit:
            return f'"{hit[2]}"', round(t - hit[0], 2)
        nxt = next((c for c in cues if c[0] > t), None)
        if nxt:
            return f'(nothing — next words in {round(nxt[0]-t, 2)}s)', None
        return "(nothing — after the last word)", None

    everything = ([(k, v, "card") for k, v in windows["cards"].items()]
                  + [(k, v, "overlay") for k, v in windows["overlays"].items()])
    silent = []
    for label, (t0, t1), kind in sorted(everything, key=lambda x: x[1][0]):
        words, into = spoken_at(t0)
        when = f"{int(t0 // 60)}:{t0 % 60:05.2f}"
        qc.note(f"TIMING · {label} appears at {t0:.2f}s ({when}), holds "
                f"{t1 - t0:.1f}s — Gordon is saying {words}"
                + (f", {into}s in" if into is not None else ""))
        if into is None and kind == "overlay":
            silent.append(label)
    # An OVERLAY that lands where nothing is being said is the EP18 fault exactly: the
    # e-book card came up while Gordon was still on the hook line, and left before he
    # mentioned the guide. A card may legitimately outlast a sentence; an overlay that
    # ARRIVES in silence is arriving somewhere nobody chose.
    for label in silent:
        qc.fail(f"{label} appears while nothing is being spoken. Overlays are placed "
                "against the words — an arrival in silence means its anchor is wrong "
                "or the clock is.")


def stage_deliverables(qc, episode_path, ep_dir, out_dir):
    """The two things a reader RECEIVES besides the video: the e-book PDF and the
    thumbnail. (Jodie, 9 Aug 2026 — extend the machine QC to every approval gate.)

    `stage_packaging` already proves their SOURCES carry the locked words. This is the
    other half and the one that was missing: are the FILES THEMSELVES whole? A source
    can be perfect and the artefact still be a blank page, a missing image, or a 3-byte
    PNG — and every one of those reaches a human before it reaches a check.
    `build_ebook.py` QCs the PDF as it BUILDS it; this looks at what is on disk now,
    which is not the same claim.
    """
    import glob as _g
    ep = {}
    try:
        ep = json.load(open(episode_path, encoding="utf-8"))
    except Exception:
        pass

    # ---------------------------------------------------------------- the PDF
    # ASK BOTH PLACES. The built PDF lands in output/ beside the video; ebook/ holds
    # the sources it was made from. The first version of this looked only in ebook/
    # and reported EP18's shipped guide as missing — a check that cannot find the
    # artefact reports the wrong fault with total confidence.
    pdfs = (sorted(_g.glob(os.path.join(ep_dir, "output", "*.pdf")))
            or sorted(_g.glob(os.path.join(ep_dir, "ebook", "*.pdf"))))
    if not pdfs:
        qc.fail("no e-book PDF in output/ or ebook/ — the guide is a shipped "
                "deliverable and the video's call to action points at it")
    else:
        pdf = pdfs[-1]
        try:
            import fitz
        except Exception as e:                                        # noqa: BLE001
            qc.warn(f"e-book PDF not examined — PyMuPDF is not importable ({e}). "
                    "The file exists but nothing has looked inside it.")
        else:
            try:
                doc = fitz.open(pdf)
            except Exception as e:                                    # noqa: BLE001
                qc.fail(f"the e-book PDF will not open ({e}) — {os.path.basename(pdf)}")
                doc = None
            if doc is not None:
                n = doc.page_count
                if n < 4:
                    qc.fail(f"the e-book PDF has only {n} page(s) — that is not a guide")
                blank, noimg, texts = [], [], []
                for i, page in enumerate(doc, 1):
                    t = page.get_text().strip()
                    imgs = page.get_images(full=True)
                    texts.append(t)
                    if not t and not imgs:
                        blank.append(i)
                    elif not imgs and len(t) < 40:
                        noimg.append(i)
                if blank:
                    qc.fail(f"e-book page(s) {blank} are completely EMPTY — no text and "
                            "no image. A blank page in a guide reads as a fault in us.")
                if noimg:
                    qc.warn(f"e-book page(s) {noimg} carry almost nothing")
                body = "\n".join(texts)
                # 🔴 THE ROGUE '?' — EP17's ruling, and it recurred on EP18. The scans
                # carry a literal '?' glued to the front of a word mid-sentence. It is
                # repaired at the CAPTURE, so one arriving here means the repair was
                # missed or something downstream re-introduced it.
                rogue = re.findall(r"\?[A-Za-z]\w*", body)
                if rogue:
                    qc.fail(f"the e-book PDF contains {len(rogue)} rogue '?' glued to a "
                            f"word — {rogue[:5]}. These are scan noise (EP17 ruling) and "
                            "are repaired at the capture, not here.")
                if doc.page_count:
                    qc.note(f"e-book PDF: {n} pages, "
                            f"{sum(len(t) for t in texts):,} chars of text, "
                            f"{'no' if not blank else len(blank)} blank page(s)")
                doc.close()

    # ------------------------------------------------------------ the thumbnail
    thumbs = sorted(_g.glob(os.path.join(ep_dir, "output", "*thumbnail*.png")))
    if not thumbs:
        qc.fail("no thumbnail PNG in output/ — it is a first-class deliverable and the "
                "step most likely to be forgotten (PP-STANDARDS)")
        return
    th = thumbs[-1]
    size = os.path.getsize(th)
    if size < 20_000:
        qc.fail(f"the thumbnail is only {size:,} bytes — that is not a finished 1280x720 "
                "picture, it is a placeholder or a failed render")
    dim = _probe_png(th)
    if dim is None:
        qc.fail(f"the thumbnail will not decode — {os.path.basename(th)} is corrupt")
        return
    w, h, luma = dim
    if (w, h) != (1280, 720):
        qc.fail(f"the thumbnail is {w}x{h}, not 1280x720 — YouTube will rescale it and "
                "the type will soften")
    # 🚫 THERE IS NO "IS IT TOO DARK" FAIL HERE, AND THAT IS A DECISION.
    # One was written and then taken out, because it could not be made to FIRE on any
    # realistic fixture (CLAUDE.md 4b — a guard you have not watched fail does not ship).
    # The failure it was aimed at is a render that produced nothing, and that render
    # produces a FLAT frame, which is a 4 KB PNG — already caught by the size check
    # above, proved. To make the luma rule fire the fixture had to be a noise field
    # scaled down, which is not a thing this pipeline can emit.
    # Mean luma is still REPORTED, because it is the number a human would want if a
    # thumbnail ever did look wrong — but it judges nothing.
    qc.note(f"thumbnail: {w}x{h}, {size:,} bytes, mean luma "
            f"{'n/a' if luma is None else round(luma, 1)}")


def _probe_png(path):
    """(width, height, mean_luma) straight out of the file, or None if it will not
    decode. ffprobe/ffmpeg rather than a new image library — the toolchain already
    depends on them and a check should not add a way to fail."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            path], capture_output=True, text=True)
        w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    except Exception:                                                  # noqa: BLE001
        return None
    luma = None
    try:
        r2 = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-vf",
                             "signalstats,metadata=print", "-f", "null", "-"],
                            capture_output=True, text=True)
        m = re.search(r"lavfi\.signalstats\.YAVG=([0-9.]+)", r2.stderr)
        luma = float(m.group(1)) if m else None
    except Exception:                                                  # noqa: BLE001
        pass
    return w, h, luma


def stage_card_timing(qc, final, beats, head, episode_path):
    """Card-sync standard (25 Jul 2026): every card ENTERS no earlier than its
    spoken cue (beat start) and HOLDS at least the readable minimum. Verified
    from the same maths the assembler uses (config-drift guard). Also probes
    the midroll chip's presence and full-visibility duration (>=6s, fades on
    top) when compositing is on."""
    try:
        ep = json.load(open(episode_path, encoding="utf-8"))
    except Exception:
        return
    B = ep.get("build", {})
    if not beats:
        return
    bs = lambda n: beats[n - 1]["start"] + head
    cards = {c["id"]: c for c in ep.get("cards", [])}
    standing = set((B.get("standing") or {}).values())
    content = [c for c in cards if c not in standing]
    minh = B.get("min_card_hold", 9.0)
    enters = sorted((bs(cards[c]["beat"]) + B.get("leads", {}).get(c, 1.0), c) for c in content)
    nxt = {c: (enters[i + 1][0] if i + 1 < len(enters) else None)
           for i, (_t, c) in enumerate(enters)}
    ok = True
    windows = {}
    for t, c in enters:
        lead = B.get("leads", {}).get(c, 1.0)
        if lead < 0.3:
            qc.fail(f"card {c} enters {lead:.1f}s after its beat starts - too early "
                    "(cards must never lead their spoken cue; min lead 0.3s)")
            ok = False
        raw = (B.get("holds", {}) or {}).get(c) or (B.get("hero_hold", 12.0)
              if cards[c].get("hero") else B.get("default_hold", 8.0))
        hold = max(raw, B.get("min_card_hold", 0.0))
        if nxt[c] is not None:
            hold = max(3.0, min(hold, nxt[c] - t - 0.5))
        if hold < minh - 0.01 and (nxt[c] is None or nxt[c] - t - 0.5 >= minh):
            qc.fail(f"card {c} holds only {hold:.1f}s - under the readable minimum "
                    f"({minh:.0f}s; raise holds/min_card_hold)")
            ok = False
        windows[c] = (t, t + hold)
    if ok:
        qc.note(f"card timing ok: {len(content)} cards enter on-cue and hold >= "
                f"{minh:.0f}s (or to the next card)")
    # WORD-CUE anchor (Jodie, 25 Jul 2026): a card carrying a "cue" phrase must
    # never enter before that phrase is SPOKEN. Cue times come from the master's
    # SRT, scoped to the card's beat so repeated phrases can't mislead.
    # A CHECK THAT SHARES ITS SOURCE WITH THE THING IT CHECKS IS NOT A CHECK.
    # (Jodie, 29 Jul 2026.) renders/generated.srt is NOT a transcript --
    # build_shot_map.py CONSTRUCTS it from spoken-words.txt by interpolation, and the
    # card leads are derived from that same file. So this test was comparing a number
    # with itself and reported "enters on its spoken cue" for EP11, EP12 and three
    # rebuilds of EP13 while cards ran up to 12.3s AHEAD of the words. Jodie reported
    # the fault by eye on EP11 and was told, by measurement, that she was wrong.
    #
    # renders/aligned.srt carries timings from FORCED ALIGNMENT of the actual audio.
    # Prefer it always; if it is absent, say so loudly rather than quietly grading the
    # build against its own homework.
    _rend = os.path.join(os.path.dirname(os.path.dirname(episode_path)), "renders")
    aligned_path = os.path.join(_rend, "aligned.srt")
    srt_path = os.path.join(_rend, "generated.srt")
    cued = [c for c in content if cards[c].get("cue")]
    if os.path.isfile(aligned_path):
        srt_path = aligned_path
        qc.note("cue check reads renders/aligned.srt (forced alignment of the audio)")
    elif cued:
        qc.warn("NO renders/aligned.srt - the cue check is falling back to generated.srt, "
                "which is CONSTRUCTED from spoken-words.txt by the same interpolation the "
                "card leads came from. It cannot detect a card leading its cue. Treat every "
                "'enters on its spoken cue' note below as UNVERIFIED.")
    if cued and os.path.isfile(srt_path):
        def _t2s(x):
            h, m, rest = x.split(":"); s, ms = rest.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        segs = []
        for blk in re.split(r"\n\s*\n", open(srt_path, encoding="utf-8").read().strip()):
            ln = blk.strip().splitlines()
            m = re.match(r"([\d:,]+) --> ([\d:,]+)", ln[1]) if len(ln) >= 3 else None
            if m:
                segs.append((_t2s(m.group(1)) + head, _norm_words(" ".join(ln[2:]))))
        for c in cued:
            bn = cards[c]["beat"]
            b0 = bs(bn)
            b1 = beats[bn - 1]["end"] + head if bn <= len(beats) else b0 + 60
            # The phrase may STRADDLE two SRT blocks -- EP13's C6 ("put it in a special
            # bank") and C14 ("quantified as a numerical rating") both do. A
            # single-block search reports "not found", which downgrades a HARD FAIL to
            # a warning and leaves the card silently unchecked. Search rolling windows
            # of up to three consecutive blocks, and attribute the hit to the block the
            # phrase actually STARTS in -- i.e. the window still matches once, but the
            # tail alone does not.
            cue_n = _norm_words(cards[c]["cue"])
            inrange = [(s0, txt) for s0, txt in segs if b0 - 2 <= s0 <= b1]
            hit = None
            for i in range(len(inrange)):
                for w in (1, 2, 3):
                    if i + w > len(inrange):
                        break
                    joined = " ".join(t for _, t in inrange[i:i + w])
                    if cue_n in joined:
                        tail = " ".join(t for _, t in inrange[i + 1:i + w])
                        if cue_n not in tail:
                            hit = inrange[i][0]
                        break
                if hit is not None:
                    break
            if hit is None:
                qc.warn(f"card {c}: cue phrase {cards[c]['cue']!r} not found in the SRT "
                        f"near beat {bn} - check the cue text")
            elif windows[c][0] < hit - 0.05:
                qc.fail(f"card {c} enters at {windows[c][0]:.1f}s but its cue "
                        f"({cards[c]['cue']!r}) is spoken at {hit:.1f}s - the card must "
                        "never lead the spoken cue; raise its lead")
            else:
                qc.note(f"card {c} enters on its spoken cue ({cards[c]['cue']!r} at {hit:.1f}s)")
    elif cued:
        qc.warn("cue-anchored cards declared but renders/generated.srt is missing")
    # HARD RULE (Jodie, 25 Jul 2026): b-roll and motion cards NEVER share the
    # screen - a card writing over a clip means one of them wasn't seen.
    # Same maths as the assembler (broll_offsets default 1.0, broll_dur 5).
    clash = False
    overlay_windows = {}          # filled below; shared with the timing proof
    for br in ep.get("broll", []):
        r0 = bs(br["beat"]) + (B.get("broll_offsets", {}) or {}).get(br["target"], 1.0)
        r1 = r0 + B.get("broll_dur", 5)
        for c, (c0, c1) in windows.items():
            if min(r1, c1) - max(r0, c0) > 0.05:
                qc.fail(f"b-roll {br['target']} ({r0:.1f}-{r1:.1f}s) and card {c} "
                        f"({c0:.1f}-{c1:.1f}s) are on screen at the same time - "
                        "b-roll and cards must never overlap; move one")
                clash = True
    # The early e-book card is an overlay like any other and owes the same debts:
    # it must not share the screen with a card, and it must be provable against the
    # words. Adding an overlay without adding it here is how the chip went unchecked.
    cta_cfg = B.get("early_cta") or {}
    if cta_cfg.get("clip") and cta_cfg.get("at") is not None:
        e0 = cta_cfg["at"] + head
        e1 = e0 + cta_cfg.get("dur", 6.0)
        for c, (c0, c1) in windows.items():
            if min(e1, c1) - max(e0, c0) > 0.05:
                qc.fail(f"the early e-book card ({e0:.1f}-{e1:.1f}s) and card {c} "
                        f"({c0:.1f}-{c1:.1f}s) are on screen together - move one")
                clash = True
        overlay_windows["EARLY_CTA"] = (round(e0, 2), round(e1, 2))

    mid_cfg = B.get("midroll") or {}
    if mid_cfg.get("composite") and mid_cfg.get("beat"):
        # `at` is PRESENTER-CLOCK; every other time here is final-clock via bs().
        # This line read it raw, exactly as assemble_episode.py did — so the checker
        # and the thing it checks carried the SAME 7s error and agreed with each other.
        # "A check that shares its source with the thing it checks is not a check."
        # (Jodie, 29 Jul 2026 — the comment is already in this file, thirty lines up.)
        m0 = ((mid_cfg["at"] + head) if mid_cfg.get("at") is not None
              else bs(mid_cfg["beat"]) + mid_cfg.get("offset", 1.0))
        m1 = m0 + mid_cfg.get("dur", 5.0)
        overlay_windows["MIDROLL_CHIP"] = (round(m0, 2), round(m1, 2))
        for c, (c0, c1) in windows.items():
            if min(m1, c1) - max(m0, c0) > 0.05:
                qc.fail(f"midroll chip ({m0:.1f}-{m1:.1f}s) and card {c} ({c0:.1f}-{c1:.1f}s) "
                        "overlap - the chip must own its moment; move one")
                clash = True
    if not clash:
        qc.note("no b-roll/card/chip overlaps - every visual owns its moment")
    # 🔒 ONE COMPUTATION, TWO READERS. The timing proof does NOT recompute these — a
    # second copy of the window maths is a second thing to get wrong, and the whole
    # point of the proof is that it describes what the assembler actually did.
    qc.timing_windows = {"cards": dict(windows), "overlays": dict(overlay_windows)}
    mid = B.get("midroll") or {}
    if mid.get("composite") and mid.get("beat"):
        # ---------------------------------------------------------------------
        # DOES THE CHIP ACTUALLY EXIST? Asked FIRST, before anything is measured.
        #
        # TIGHTENED 28 Jul 2026, because these checks PASSED an episode that had no
        # chip at all. EP13 was assembled with no clip, no `clip` key and no chip
        # input in the pass B graph, and QC reported "midroll chip visibility ok:
        # 15.2s fully visible" and "midroll lower-third visible (chip luma 68)".
        #
        # Both were measuring the wrong thing:
        #   · the visibility line is ARITHMETIC ON episode.json (dur - 2*fade). It is
        #     true of the CONFIGURATION whether or not a chip was ever rendered.
        #   · the luma probe only fails when the region is TOO BRIGHT (>95). With no
        #     chip it measured Gordon's dark suit and the desk at luma 68 and passed.
        #     Brightness where a chip would be is not evidence that a chip is there.
        #     (With the real chip composited the region reads 55 — DARKER — so the
        #     old test could never have told the two cases apart.)
        #
        # So: assert the ARTEFACT, then measure it. Three things, cheapest first.
        # `providers.assemble_passB` only adds the chip input when `composite` AND
        # `clip` are both set, so a missing `clip` silently drops it from the build.
        ep_root = os.path.dirname(os.path.dirname(os.path.abspath(episode_path)))
        chip_ok = True
        clip_name = mid.get("clip")
        if not clip_name:
            qc.fail("midroll chip: build.midroll.composite is true but build.midroll.clip "
                    "is NOT SET, so the assembler never added the chip input and the "
                    "episode has NO on-screen like/subscribe chip. PP-STANDARDS "
                    "§Motion-graphic cards requires it every episode.")
            chip_ok = False
        else:
            clip_path = os.path.join(ep_root, "overlay", "clips", clip_name)
            if not os.path.isfile(clip_path):
                qc.fail(f"midroll chip: build.midroll.clip names {clip_name!r} but that "
                        f"file does not exist in overlay/clips/. Render it from the "
                        f"STANDING asset assets/midroll-lowerthird.html.")
                chip_ok = False
            graph = os.path.join(ep_root, "renders", "passB_graph.txt")
            if os.path.isfile(graph):
                g = open(graph, encoding="utf-8", errors="replace").read()
                if clip_name not in g and "[mrl]" not in g:
                    qc.fail(f"midroll chip: {clip_name!r} exists but is NOT REFERENCED in "
                            f"renders/passB_graph.txt, so it was not composited into this "
                            f"video. Re-emit the graph and re-run pass B.")
                    chip_ok = False
            else:
                qc.warn("midroll chip: renders/passB_graph.txt is missing, so I cannot "
                        "confirm the chip was composited (the clip and the config are "
                        "both fine)")
        if chip_ok:
            qc.note(f"midroll chip artefact ok: {clip_name} present in overlay/clips and "
                    f"referenced in the pass B graph")
        # ---------------------------------------------------------------------
        # v1.1 standard (25 Jul 2026): the like+subscribe chip needs >= 6s of FULL
        # visibility, with the fades on top of that (not inside it).
        dur, fade = mid.get("dur", 5.0), mid.get("fade", 0.4)
        full_vis = dur - 2 * fade
        if full_vis < 6.0 - 0.01:
            qc.fail(f"midroll chip full visibility is only {full_vis:.1f}s "
                    f"(dur {dur:.1f}s - 2x{fade:.1f}s fades) - the standard is >= 6s "
                    "fully visible; raise midroll.dur")
        else:
            qc.note(f"midroll chip visibility ok: {full_vis:.1f}s fully visible "
                    f"(dur {dur:.1f}s, fades {fade:.1f}s)")
        # 🔴 THE SECOND RAW `at` — found by the clock audit, 9 Aug 2026, and it had
        # survived the 8 Aug fix. That fix corrected the OVERLAP line and stopped there;
        # this line, which decides WHERE IN THE VIDEO to sample for the chip, kept
        # reading `at` as final-clock. So the probe looked 7 seconds before the chip and
        # reported "midroll lower-third visible (chip luma 55)" from whatever happened
        # to be on screen there. A green light from the wrong frame.
        #     FIXING THE INSTANCE IS NOT FIXING THE FAULT. The audit found the sibling
        #     the way E22's did: by asking whether the fault had one.
        mt = ((mid["at"] + head) if mid.get("at") is not None
              else bs(mid["beat"]) + mid.get("offset", 1.0)) + mid.get("dur", 5.0) / 2
        import subprocess
        r = subprocess.run([FFMPEG, "-hide_banner", "-ss", f"{mt:.2f}", "-i", final,
                            "-frames:v", "1", "-vf", "crop=700:260:70:790,scale=64:24,format=gray",
                            "-f", "rawvideo", "-"], capture_output=True)
        if r.returncode == 0 and r.stdout:
            luma = sum(r.stdout) / len(r.stdout)
            if luma > 95:
                qc.fail(f"midroll lower-third not visible at {mt:.0f}s (chip region luma "
                        f"{luma:.0f} - too bright; like+subscribe icons must be on screen)")
            else:
                qc.note(f"midroll lower-third visible at {mt:.0f}s (chip luma {luma:.0f})")
        else:
            qc.warn("could not probe the midroll chip region")


# ---------------------------------------------------------------------------
# stage 5 - report
# ---------------------------------------------------------------------------
def _fmt_db(v):
    if v is None:
        return "n/a"
    if v == -float("inf"):
        return "-inf"
    return f"{v:.1f} dB"


def build_report(qc, final, shot_map, head):
    p = qc.probe
    L = qc.loudness
    passed = not qc.hard_fails
    status = "PASS" if passed else "ISSUES"

    lines = []
    lines.append(f"# Episode QC Report - {status}")
    lines.append("")
    lines.append(f"- Final: `{final}`")
    lines.append(f"- Shot map: `{shot_map}`")
    lines.append(f"- Title head: {head:.1f}s")
    lines.append("")

    lines.append("## Probe")
    if p:
        abr = p.get("abitrate")
        abr_s = f"{abr/1000:.0f} kbps" if abr else "n/a"
        lines.append(f"- Duration: {p.get('duration',0):.1f}s")
        lines.append(f"- Resolution: {p.get('width','?')}x{p.get('height','?')}")
        lines.append(f"- FPS: {p.get('fps',0):.3f}")
        lines.append(f"- Video codec: {p.get('vcodec','?')}")
        lines.append(f"- Audio: {p.get('acodec','?')} {abr_s}, "
                     f"{p.get('asample_rate','?')} Hz, {p.get('achannels','?')} ch")
    else:
        lines.append("- (probe failed)")
    lines.append("")

    lines.append("## Loudness")
    lines.append(f"- Integrated: {L.get('I','n/a')} LUFS")
    lines.append(f"- LRA: {L.get('LRA','n/a')} LU")
    lines.append(f"- True peak: {L.get('true_peak','n/a')} dBFS")
    lines.append("")

    lines.append("## RMS windows")
    for label, t0, t1, db in qc.rms:
        lines.append(f"- {label:>7} ({t0:6.1f}-{t1:6.1f}s): {_fmt_db(db)}")
    lines.append("")

    lines.append("## Artifacts")
    for a in qc.artifacts:
        lines.append(f"- `{a}`")
    if not qc.artifacts:
        lines.append("- (none)")
    lines.append("")

    if qc.hard_fails:
        lines.append("## HARD FAILS")
        for f in qc.hard_fails:
            lines.append(f"- FAIL: {f}")
        lines.append("")
    if qc.warnings:
        lines.append("## Warnings")
        for w in qc.warnings:
            lines.append(f"- {w}")
        lines.append("")
    if qc.notes:
        lines.append("## Notes")
        for n in qc.notes:
            lines.append(f"- {n}")
        lines.append("")

    return status, "\n".join(lines)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="One-command episode QC.")
    ap.add_argument("final")
    ap.add_argument("shot_map")
    ap.add_argument("out_dir")
    ap.add_argument("--head", type=float, default=7.0,
                    help="title head prepended to the final (default 7.0s)")
    ap.add_argument("--episode", default=None,
                    help="episode.json - enables the end-sequence + midroll checks")
    args = ap.parse_args()

    if not os.path.exists(args.final):
        print(f"ERROR: final not found: {args.final}", file=sys.stderr)
        sys.exit(2)
    os.makedirs(args.out_dir, exist_ok=True)

    beats = []
    try:
        beats = json.load(open(args.shot_map, encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: could not read shot map ({e}) - "
              "beat frames will be skipped", file=sys.stderr)

    qc = QC()
    print(f"ffmpeg:  {FFMPEG}")
    print(f"ffprobe: {FFPROBE}")

    print("[1/5] ffprobe ...")
    stage_probe(qc, args.final)
    print("[2/5] frames + contact sheet ...")
    stage_frames(qc, args.final, beats, args.head, args.out_dir)
    print("[3/5] logo crop ...")
    stage_logo(qc, args.final, args.out_dir)
    print("[4/5] loudness ...")
    stage_loudness(qc, args.final)
    print("[5/5] RMS windows ...")
    stage_rms(qc, args.final)
    if args.episode:
        print("[4b] end sequence + midroll ...")
        stage_end_sequence(qc, args.final, beats, args.head, args.episode, args.out_dir)
        ep_dir = os.path.dirname(os.path.dirname(os.path.abspath(args.episode)))
        print("[4c] packaging consistency ...")
        stage_packaging(qc, args.episode, ep_dir)
        print("[4d] numbers check ...")
        stage_numbers(qc, args.episode, ep_dir, args.out_dir)
        print("[4e] card timing + midroll ...")
        stage_card_timing(qc, args.final, beats, args.head, args.episode)
        stage_timing_proof(qc, args.episode, ep_dir, args.head)
        stage_deliverables(qc, args.episode, ep_dir, args.out_dir)

    status, report = build_report(qc, args.final, args.shot_map, args.head)
    report_path = os.path.join(args.out_dir, "QC-REPORT.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    print(f"\nReport: {report_path}")
    print(f"RESULT: {status}")
    sys.exit(0 if not qc.hard_fails else 1)


if __name__ == "__main__":
    main()
