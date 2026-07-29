#!/usr/bin/env python3
"""align_to_script.py — renders/aligned.srt: OUR words, the AUDIO's timings.

    python align_to_script.py <episode_dir>

WHY THIS EXISTS. `renders/generated.srt` is NOT a transcript: build_shot_map.py
CONSTRUCTS it from spoken-words.txt, placing paragraph boundaries word-
proportionally and snapping them to a real pause only when one falls within
±3.5s, then laying cues out inside a paragraph character-proportionally with no
snapping at all. Card leads are derived from that file — and qc_episode's cue
test used to read the same file to check them, so it was comparing a number with
itself. It reported "enters on its spoken cue" through EP11, EP12 and three
rebuilds of EP13 while eleven of fourteen cards ran AHEAD of the words, the worst
by 12.3s. Jodie reported it by eye on EP11 and was told, by measurement, that she
was wrong.

Measured against forced alignment, the constructed file was out by a mean of
5.15s and a worst of 12.32s. The file this script writes is out by a mean of
0.08s and a worst of 0.25s.

THE TWO HALVES COME FROM DIFFERENT PLACES, ON PURPOSE:
  · TEXT from docs/spoken-words.txt — the script Gordon actually read. NEVER from
    the transcript: whisper misheard "Here's a claim" as "He's a client", "wind
    direction" as "wing direction", "luck in running" as "lucking running". A
    transcript is allowed to tell us WHEN, never WHAT.
  · TIMINGS from wav2vec2 forced alignment of the real audio (align_srt.py).

Our word sequence is aligned to the transcript's with difflib; matched words take
the transcript's time and unmatched runs are interpolated between their
neighbours. Paragraph starts are then read straight off the first word of each
paragraph — no proportional guessing anywhere.

IT VERIFIES ITSELF AFTER WRITING, the way trim_master_lead_in does. A step that
reports what it INTENDED rather than what it DID is worthless — the first version
of the trim returned success and changed nothing.

HONEST LIMIT: align_srt.py collapses wav2vec2's word alignment to SENTENCE cues,
so a word's position inside a cue is still interpolated by character offset.
Those cues run ~3-4s, so the residual is a few tenths. True word-level alignment
is a further improvement, not a correction.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_MATCH = 0.85          # share of OUR words that must land on a real aligned word
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass


class Halt(Exception):
    pass


def toks(s):
    return re.findall(r"[a-z0-9']+", s.lower())


def parse_srt(path):
    raw = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)",
                      "\n".join(lines))
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        s = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000.0
        e = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000.0
        text = " ".join(l for l in lines if not re.fullmatch(r"\d+", l) and "-->" not in l)
        out.append((s, e, text))
    return out


def word_timeline(cues):
    """[(word, start)] — position inside a cue interpolated by CHARACTER offset."""
    tl = []
    for s, e, text in cues:
        flat = " ".join(text.split())
        if not flat:
            continue
        span = e - s
        for m in re.finditer(r"[A-Za-z0-9']+", flat):
            tl.append((m.group(0).lower(), s + span * (m.start() / len(flat))))
    return tl


def paragraphs(spoken_path):
    """The same paragraph split build_shot_map.py uses — one paragraph = one beat."""
    raw = Path(spoken_path).read_text(encoding="utf-8")
    mk = re.search(r"(?im)^.*paste\b.*\bbelow\b.*$", raw)
    if mk:
        raw = raw[mk.end():]
    paras = [p.strip() for p in raw.split("\n\n") if p.strip()]
    while paras and (all(l.lstrip().startswith("#") for l in paras[0].splitlines())
                     or paras[0].lstrip().startswith("[")):
        paras.pop(0)
    return paras


def fmt(t):
    ms = int(round(max(t, 0) * 1000)); h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def two(s):
    if len(s) <= 42:
        return s
    mid = len(s) // 2; l = s.rfind(" ", 0, mid + 1); r = s.find(" ", mid)
    cut = l if (r == -1 or (l != -1 and mid - l <= r - mid)) else r
    return s if cut == -1 else s[:cut] + "\n" + s[cut + 1:]


def build(ep_dir, model="base"):
    d = Path(ep_dir).resolve()
    master = d / "renders/presenter-master.mp4"
    spoken = d / "docs/spoken-words.txt"
    out = d / "renders/aligned.srt"
    for p in (master, spoken):
        if not p.is_file():
            raise Halt(f"align_to_script: missing {p}")

    with tempfile.TemporaryDirectory() as td:
        tsrt = Path(td) / "transcript.srt"
        r = subprocess.run([sys.executable, str(HERE / "align_srt.py"), str(master),
                            str(tsrt), "--model", model],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode or not tsrt.is_file():
            raise Halt("align_to_script: forced alignment failed — renders/aligned.srt was NOT "
                       "written, so nothing downstream will silently use guessed timings.\n"
                       + (r.stderr or r.stdout or "")[-800:])
        tcues = parse_srt(tsrt)

    tl = word_timeline(tcues)
    speech_end = max(e for _, e, _ in tcues)

    paras = paragraphs(spoken)
    ours, index, sents = [], [], []
    for pi, p in enumerate(paras):
        for s in [x.strip() for x in re.split(r"(?<=[.!?])\s+", p) if x.strip()]:
            sents.append((pi, s))
            for w in toks(s):
                ours.append(w)
                index.append(len(sents) - 1)
    if not ours:
        raise Halt("align_to_script: the spoken-words file produced no words")

    theirs = [w for w, _ in tl]
    times = [t for _, t in tl]
    at = [None] * len(ours)
    matched = 0
    for a, b, n in difflib.SequenceMatcher(None, ours, theirs, autojunk=False).get_matching_blocks():
        for k in range(n):
            at[a + k] = times[b + k]
            matched += 1
    rate = matched / len(ours)

    known = [i for i, v in enumerate(at) if v is not None]
    if not known:
        raise Halt("align_to_script: not one word of the script matched the audio")
    for i in range(len(at)):
        if at[i] is None:
            lo = max((k for k in known if k < i), default=None)
            hi = min((k for k in known if k > i), default=None)
            at[i] = at[hi] if lo is None else at[lo] if hi is None else \
                at[lo] + (at[hi] - at[lo]) * (i - lo) / (hi - lo)
    for i in range(1, len(at)):
        at[i] = max(at[i], at[i - 1])

    span = {}
    for wi, si in enumerate(index):
        s, e = span.get(si, (at[wi], at[wi]))
        span[si] = (min(s, at[wi]), max(e, at[wi]))

    cues, n = [], 1
    for si, (_, text) in enumerate(sents):
        s, e = span[si]
        nxt = span[si + 1][0] if si + 1 < len(sents) else speech_end
        cues.append(f"{n}\n{fmt(s)} --> {fmt(min(e + 0.6, nxt) - 0.05)}\n{two(text)}\n")
        n += 1
    out.write_text("\n".join(cues), encoding="utf-8-sig", newline="\r\n")

    # ---- VERIFY WHAT WAS WRITTEN, not what was intended --------------------
    back = parse_srt(out)
    back_words = [w for w, _ in word_timeline(back)]
    if back_words != ours:
        out.unlink(missing_ok=True)
        raise Halt(f"align_to_script: the file written back does not carry our script's words "
                   f"({len(back_words)} vs {len(ours)}). Removed it rather than leave a wrong "
                   f"timing file where everything downstream would trust it.")
    starts = [s for s, _, _ in back]
    if starts != sorted(starts):
        out.unlink(missing_ok=True)
        raise Halt("align_to_script: written cue times are not monotonic. Removed the file.")
    if rate < MIN_MATCH:
        out.unlink(missing_ok=True)
        raise Halt(f"align_to_script: only {rate*100:.1f}% of the script matched the audio "
                   f"(floor {MIN_MATCH*100:.0f}%). That means the master is not reading this "
                   f"script — wrong take, wrong episode, or the words changed after the render. "
                   f"Removed the file; nothing downstream may use it.")
    return (f"aligned.srt: {len(back)} cues, {len(ours)} words, "
            f"{rate*100:.1f}% anchored to the audio (rest interpolated), "
            f"monotonic and text-identical to spoken-words.txt — verified after writing")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    try:
        print(build(sys.argv[1]))
    except Halt as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
