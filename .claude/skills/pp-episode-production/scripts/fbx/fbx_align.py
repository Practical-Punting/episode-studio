#!/usr/bin/env python3
"""fbx_align.py — word timings for an FBX weekly video, by TRUE forced alignment of OUR script.

    python fbx_align.py <job_dir>

Reads  renders/presenter-master.mp4 and docs/*-heygen-spoken.txt (the words Gordon read).
Writes renders/words-forced.json  (one entry per script word: word, start, end, score)
       renders/aligned.srt        (sentence cues, CRLF, our words, the audio's timings)
       renders/pause-check.txt    (every measured pause, and the words either side of it)

WHY NOT align_to_script.py (11 Oct 2026, FBX-W01). That tool transcribes first, then
force-aligns the TRANSCRIPT. The transcript writes money as digits ("$2.90"), wav2vec2 has
no characters for digits, and the whole results paragraph collapsed: six horses that Gordon
reads between 6.0s and 22.1s were stamped 6.0s-13.7s, with nothing at all until 22.6s.
align_to_script still reported "93.8% anchored ... verified" — it verifies the TEXT and the
ORDER, and both were right; only the TIMES were wrong, and nothing it checks can see that.

So here wav2vec2 aligns OUR script (every number already spelled out in words, because it
went into HeyGen that way), and the result is checked against something independent:
ffmpeg's silencedetect. A real pause must fall BETWEEN two words. A pause INSIDE a word means
the alignment is wrong, and this script exits non-zero rather than hand a guess to the cards.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

PAUSE_DB, PAUSE_MIN = -40, 0.25     # what counts as a measured pause
SLACK = 0.05                        # a word may overhang a pause edge by this much


def spoken_file(job: Path) -> Path:
    c = sorted((job / "docs").glob("*heygen-spoken.txt"))
    if len(c) != 1:
        sys.exit(f"expected exactly one docs/*heygen-spoken.txt in {job}, found {len(c)}")
    return c[0]


def pauses(media: Path):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-af",
                        f"silencedetect=n={PAUSE_DB}dB:d={PAUSE_MIN}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", e.stderr)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", e.stderr)]
    return list(zip(st, en))


def fmt(t):
    ms = int(round(max(t, 0) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def two_lines(s, width=42):
    if len(s) <= width:
        return s
    mid = len(s) // 2
    l, r = s.rfind(" ", 0, mid), s.find(" ", mid)
    cut = l if (r == -1 or (l != -1 and mid - l <= r - mid)) else r
    return s if cut == -1 else s[:cut] + "\n" + s[cut + 1:]


def main():
    job = Path(sys.argv[1]).resolve()
    master = job / "renders" / "presenter-master.mp4"
    spoken = spoken_file(job)
    text = spoken.read_text(encoding="utf-8")
    flat = " ".join(text.split())

    import whisperx  # heavy; imported only when we know the inputs exist
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a16k.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-vn", "-ac", "1",
                        "-ar", "16000", str(wav)], check=True)
        audio = whisperx.load_audio(str(wav))
    dur = len(audio) / 16000
    model, meta = whisperx.load_align_model(language_code="en", device="cpu")
    al = whisperx.align([{"text": flat, "start": 0.0, "end": dur}], model, meta, audio, "cpu",
                        return_char_alignments=False)
    words = [{"word": w["word"], "start": round(float(w["start"]), 3),
              "end": round(float(w["end"]), 3), "score": round(float(w.get("score", 0)), 3)}
             for s in al["segments"] for w in s["words"] if "start" in w]
    ours = flat.split()
    if [w["word"] for w in words] != ours:
        sys.exit(f"HALT: aligned {len(words)} words but the script has {len(ours)} — a word "
                 f"could not be placed. Nothing written.")

    # ---- the independent check: measured pauses must sit between words ----
    lines, inside = [], 0
    for a, b in pauses(master):
        bad = [w for w in words if w["start"] < a - SLACK and w["end"] > b + SLACK]
        before = [w for w in words if w["end"] <= a + 0.15]
        after = [w for w in words if w["start"] >= b - 0.15]
        inside += bool(bad)
        lines.append(f"pause {a:7.2f}-{b:7.2f}  after {before[-1]['word'] if before else '-'!r:>18}  "
                     f"before {after[0]['word'] if after else '-'!r}"
                     + (f"   <-- INSIDE {bad[0]['word']!r}" if bad else ""))
    lines.append(f"pauses inside a word: {inside}")
    (job / "renders" / "pause-check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if inside:
        sys.exit("HALT: a measured pause falls inside a word, so these timings are wrong. "
                 "words-forced.json was NOT written.")

    (job / "renders" / "words-forced.json").write_text(json.dumps(words, indent=1), encoding="utf-8")

    # ---- sentence cues from the forced words (the shipping SRT) ----
    cues, i = [], 0
    for para in [p for p in re.split(r"\n\s*\n", text) if p.strip()]:
        for sent in [x for x in re.split(r"(?<=[.!?])\s+", " ".join(para.split())) if x.strip()]:
            n = len(sent.split())
            ws = words[i:i + n]
            i += n
            cues.append([ws[0]["start"], ws[-1]["end"], sent])
    if i != len(words):
        sys.exit("HALT: sentence split did not consume every word")
    out = []
    for k, (s, e, t) in enumerate(cues):
        nxt = cues[k + 1][0] if k + 1 < len(cues) else e + 1.0
        out.append(f"{k + 1}\n{fmt(s)} --> {fmt(min(e + 0.4, nxt - 0.05))}\n{two_lines(t)}\n")
    srt = job / "renders" / "aligned.srt"
    srt.write_text("\n".join(out), encoding="utf-8-sig", newline="\r\n")
    print(f"words-forced.json: {len(words)} words, {words[0]['start']:.2f}s -> {words[-1]['end']:.2f}s")
    print(f"aligned.srt: {len(cues)} cues (forced alignment of the script; pauses all between words)")


if __name__ == "__main__":
    main()
