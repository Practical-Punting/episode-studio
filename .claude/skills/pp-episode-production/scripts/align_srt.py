#!/usr/bin/env python3
# align_srt.py -- WhisperX forced-alignment -> sentence-level SRT
#
# Practical Punting pipeline. Produces a word-accurate SRT from a rendered
# presenter (clean TTS audio). The resulting SRT is fed to build_shot_map.py
# as its optional anchor-SRT argument, replacing pure interpolation.
#
# Usage:
#   python align_srt.py <audio_or_video_in> <out.srt> [--model base]
#
# Machine notes (this box): CPU-only torch/whisperx. Runs device="cpu",
# compute_type="int8". First run downloads the Whisper model + the wav2vec2
# alignment model (expected, one-time).

import os
import re
import sys
import shutil
import tempfile
import subprocess

# ---- args -------------------------------------------------------------------
def parse_args(argv):
    model = "base"
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--model":
            i += 1
            if i >= len(argv):
                sys.exit("error: --model needs a value")
            model = argv[i]
        elif a.startswith("--model="):
            model = a.split("=", 1)[1]
        else:
            positional.append(a)
        i += 1
    if len(positional) < 2:
        sys.exit("usage: python align_srt.py <audio_or_video_in> <out.srt> [--model base]")
    return positional[0], positional[1], model


IN_PATH, OUT_PATH, MODEL = parse_args(sys.argv[1:])

if not os.path.isfile(IN_PATH):
    sys.exit(f"error: input not found: {IN_PATH}")

# ---- ffmpeg -----------------------------------------------------------------
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".wma"}
ext = os.path.splitext(IN_PATH)[1].lower()

_tmp_wav = None


def make_wav(src):
    """Extract mono 16kHz PCM wav to a temp file; return its path."""
    global _tmp_wav
    if FFMPEG is None:
        sys.exit("error: ffmpeg not found on PATH (needed to extract audio).")
    fd, _tmp_wav = tempfile.mkstemp(suffix=".wav", prefix="align_srt_")
    os.close(fd)
    cmd = [FFMPEG, "-y", "-i", src, "-vn",
           "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", _tmp_wav]
    print(f"extracting 16kHz mono wav via ffmpeg -> {_tmp_wav}")
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        sys.exit("error: ffmpeg audio extraction failed.")
    return _tmp_wav


if ext in AUDIO_EXTS:
    # Even audio inputs get normalised to 16k mono wav for consistency/speed,
    # but only if ffmpeg is available; otherwise pass through and let whisperx
    # load it directly.
    audio_path = make_wav(IN_PATH) if FFMPEG else IN_PATH
else:
    audio_path = make_wav(IN_PATH)

# ---- heavy imports ----------------------------------------------------------
try:
    import whisperx
except Exception as e:  # pragma: no cover
    sys.exit(
        "error: could not import whisperx.\n"
        f"  {type(e).__name__}: {e}\n"
        "  Ensure whisperx + torch (CPU build) are installed for this python."
    )

DEVICE = "cpu"
COMPUTE = "int8"

# ---- transcribe -------------------------------------------------------------
print(f"loading whisper model '{MODEL}' (device={DEVICE}, compute={COMPUTE})...")
print("  (first run downloads the model -- this is expected)")
try:
    model = whisperx.load_model(MODEL, device=DEVICE, compute_type=COMPUTE, language="en")
except Exception as e:
    sys.exit(f"error: failed to load whisper model: {type(e).__name__}: {e}")

print("loading audio...")
audio = whisperx.load_audio(audio_path)

print("transcribing...")
result = model.transcribe(audio, batch_size=8)
if not result.get("segments"):
    sys.exit("error: transcription produced no segments (silent/empty audio?).")

# ---- align ------------------------------------------------------------------
print("loading wav2vec2 alignment model (first run downloads it)...")
try:
    model_a, metadata = whisperx.load_align_model(language_code="en", device=DEVICE)
except Exception as e:
    sys.exit(f"error: failed to load align model: {type(e).__name__}: {e}")

print("aligning...")
aligned = whisperx.align(
    result["segments"], model_a, metadata, audio, DEVICE,
    return_char_alignments=False,
)

# ---- collect words with timings --------------------------------------------
words = []
for seg in aligned.get("segments", []):
    for w in seg.get("words", []):
        txt = (w.get("word") or "").strip()
        if not txt:
            continue
        start = w.get("start")
        end = w.get("end")
        words.append({"word": txt, "start": start, "end": end})

# Backfill missing timings (WhisperX can leave start/end None on some tokens,
# e.g. pure punctuation or numerals) so every word has usable bounds.
_last = 0.0
for w in words:
    if w["start"] is None:
        w["start"] = _last
    else:
        _last = w["start"]
    if w["end"] is None:
        w["end"] = w["start"]
    _last = max(_last, w["end"])

if not words:
    sys.exit("error: alignment produced no words.")

# ---- group into sentence-level cues ----------------------------------------
MAX_CHARS = 84
SENT_END = re.compile(r"[.!?]$|[.!?][\"')\]]$")


def flush(buf):
    text = " ".join(w["word"] for w in buf).strip()
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)  # tidy space-before-punct
    return {"start": buf[0]["start"], "end": buf[-1]["end"], "text": text}


cues = []
buf = []
cur_len = 0
for w in words:
    add_len = len(w["word"]) + (1 if buf else 0)
    if buf and cur_len + add_len > MAX_CHARS:
        cues.append(flush(buf))
        buf, cur_len = [], 0
        add_len = len(w["word"])
    buf.append(w)
    cur_len += add_len
    if SENT_END.search(w["word"]):
        cues.append(flush(buf))
        buf, cur_len = [], 0
if buf:
    cues.append(flush(buf))

# ---- write SRT --------------------------------------------------------------
def fmt_ts(t):
    if t is None or t < 0:
        t = 0.0
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


lines = []
for idx, c in enumerate(cues, 1):
    lines.append(str(idx))
    lines.append(f"{fmt_ts(c['start'])} --> {fmt_ts(c['end'])}")
    lines.append(c["text"])
    lines.append("")

out_dir = os.path.dirname(os.path.abspath(OUT_PATH))
if out_dir and not os.path.isdir(out_dir):
    os.makedirs(out_dir, exist_ok=True)

with open(OUT_PATH, "w", encoding="utf-8", newline="\r\n") as f:
    f.write("\n".join(lines))

# ---- cleanup ----------------------------------------------------------------
if _tmp_wav and os.path.isfile(_tmp_wav):
    try:
        os.remove(_tmp_wav)
    except OSError:
        pass

# ---- summary ----------------------------------------------------------------
print()
print(f"wrote {len(cues)} cues -> {os.path.abspath(OUT_PATH)}")
print("first 3 cues:")
for c in cues[:3]:
    print(f"  {fmt_ts(c['start'])} --> {fmt_ts(c['end'])}  {c['text']}")
