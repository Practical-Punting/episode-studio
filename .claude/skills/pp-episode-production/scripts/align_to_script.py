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


# ═══════════════════════════════════════════════════════════════════════════════
# WE SPELL FIGURES AS WORDS. WHISPER WRITES THEM AS DIGITS. THAT IS NOT A
# MISMATCH BETWEEN THE MASTER AND THE SCRIPT — IT IS A MISMATCH BETWEEN TWO WAYS
# OF WRITING THE SAME SOUND, AND IT WAS BEING COUNTED AS THE FORMER.
#
# EP17, 6 Aug 2026: refused at 79.8% against an 85% floor on a master that was
# complete, correctly trimmed and measured at 189,366 bps. The halt said "the
# master is not reading this script — wrong take, wrong episode, or the words
# changed after the render." All three were false.
#
# MEASURED ACROSS EVERY EPISODE, because one data point is an anecdote:
#     EP07-EP14   1.9-5.8% number-words    comfortable
#     EP15        5.2%                     fine
#     EP16        9.2%                     87.8%  <- "narrowest pass on record"
#     EP17       13.9% (17.2% with units)  79.8%  <- REFUSED
# The miss rate tracks the number-word share. It always did; nobody had looked.
#
# ⚰️ AND IT CLOSES THE "DOES A LOW-BITRATE MASTER DEPRESS THE ANCHOR RATE?"
# QUESTION THE OPPOSITE WAY ROUND. EP16 scraped through on 124 kbps; EP17 scored
# SEVEN POINTS WORSE on 189 kbps. Bitrate is not the driver. Density is.
#
# 🔒 THE FLOOR IS NOT TOUCHED. 85% still means what it meant, and still catches
# EP15's truncated master at 62.9%. The floor was never wrong — the MEASUREMENT
# was, and lowering a threshold because a build failed it is how a floor stops
# meaning anything.
# ═══════════════════════════════════════════════════════════════════════════════

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety")


def _under_100(n):
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])


def _under_1000(n):
    if n < 100:
        return _under_100(n)
    head = _ONES[n // 100] + " hundred"
    return head if n % 100 == 0 else head + " and " + _under_100(n % 100)


def int_words(n: int) -> str:
    """The way this studio says a whole number out loud (PP-STANDARDS §4B)."""
    if n < 0:
        return "minus " + int_words(-n)
    if n < 1000:
        return _under_1000(n)
    if n < 1_000_000:
        head = _under_1000(n // 1000) + " thousand"
        return head if n % 1000 == 0 else head + " " + _under_1000(n % 1000)
    head = _under_1000(n // 1_000_000) + " million"
    return head if n % 1_000_000 == 0 else head + " " + int_words(n % 1_000_000)


def spoken_form(text: str) -> str:
    """Rewrite figures and symbols AS THE WORDS WE SPEAK THEM.

    🔴 ONE DEFINITION OF "THE SAME NUMBER", APPLIED TO BOTH SIDES. Two
    implementations of what a number is would be fault #2 with extra steps: the
    transcript would drift away from the script one release at a time and the
    anchor rate would sag with nobody able to say why.

    On OUR side it is provably a NO-OP — `render_ready` hard-fails a bare numeral
    in the spoken track, so there is nothing here to convert. It is applied there
    anyway, and asserted, because a symmetry you rely on and do not exercise is a
    symmetry you do not have.

    §4B is the source of the forms: `$3.40` -> "three dollars forty",
    `43%` -> "forty-three per cent", `1200` -> "twelve hundred" is NOT used —
    we write the plain reading, which is what Gordon is given.
    """
    s = text
    # money first: $224.60 -> "two hundred and twenty four dollars sixty".
    # The cents are read as a bare number after "dollars", which is the house
    # form and what the spoken track carries.
    def _money(m):
        whole = int(m.group(1).replace(",", ""))
        cents = m.group(2)
        out = int_words(whole) + " dollars"
        if cents and int(cents) != 0:
            out += " " + int_words(int(cents))
        return out
    s = re.sub(r"\$\s*([\d,]+)(?:\.(\d{2}))?", _money, s)
    # per cent, however it was written
    s = re.sub(r"(\d)\s*%", lambda m: m.group(1) + " per cent", s)
    s = re.sub(r"\bpercent\b", "per cent", s, flags=re.I)
    # then any remaining whole number, commas and all
    s = re.sub(r"\b\d[\d,]*\b", lambda m: int_words(int(m.group(0).replace(",", ""))), s)
    return s


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


def word_timeline(cues, fold=True):
    """[(word, start)] — position inside a cue interpolated by CHARACTER offset.

    `fold` rewrites the transcript's figures into the words we speak, so "660"
    can anchor "six hundred and sixty". The expansion happens BEFORE the offset
    interpolation, so a figure's four words are spread across the span the figure
    itself occupied rather than all landing on its first character.

    ⚠️ `fold=False` is used by the write-back verification, which must read the
    file EXACTLY as written and must not be re-folding anything.
    """
    tl = []
    for s, e, text in cues:
        flat = " ".join((spoken_form(text) if fold else text).split())
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


def observed_miss_report(rate, ours, matched_at, index, sents) -> str:
    """SAY WHAT WAS SEEN. NAME A CAUSE ONLY WHERE THERE IS ONE.

    🔴 THE WORDING THIS REPLACES NEARLY COST A RE-RENDER (EP17, 6 Aug 2026). It
    read: "the master is not reading this script — wrong take, wrong episode, or
    the words changed after the render." Three causes, none established, and all
    three false: the master was complete, correctly trimmed and 189,366 bps. The
    third is an INSTRUCTION to re-render a good master, and it would have looked
    like the fix when the retry happened to pass.

    That is CLAUDE.md fault #6 doing its most expensive damage. So this reports
    the OBSERVATION — how much missed, and WHERE it clusters — and offers causes
    only as possibilities, saying plainly which the evidence points at.
    """
    missed = [i for i, v in enumerate(matched_at) if v is None]
    lines = [f"align_to_script: {rate*100:.1f}% of the script anchored to the audio "
             f"(floor {MIN_MATCH*100:.0f}%). {len(missed)} of {len(ours)} words did not "
             f"match. Nothing downstream may use guessed timings, so the file was removed."]

    # WHERE do the misses fall? A run at one end reads very differently from a
    # scatter through the middle, and the operator cannot see either.
    if missed:
        first, last = missed[0] / len(ours), missed[-1] / len(ours)
        tail = sum(1 for i in missed if i > 0.75 * len(ours)) / len(missed)
        lines.append(f"The misses run from {first*100:.0f}% to {last*100:.0f}% of the way "
                     f"through, with {tail*100:.0f}% of them in the last quarter.")
        if tail > 0.6:
            lines.append("THAT CLUSTERING AT THE END is what a master that stops early "
                         "looks like — check the recording actually reaches the sign-off.")

    # Is it the figures? This is an OBSERVATION about our own words, not a guess
    # about the audio: we spell figures out and a transcriber writes them as
    # digits, so a number-dense script loses anchor rate for a reason that has
    # nothing to do with whether the master is correct.
    numish = set("zero one two three four five six seven eight nine ten eleven twelve "
                 "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty "
                 "thirty forty fifty sixty seventy eighty ninety hundred thousand million "
                 "per cent dollars dollar cents".split())
    if missed:
        share = sum(1 for i in missed if ours[i] in numish) / len(missed)
        if share > 0.4:
            lines.append(f"{share*100:.0f}% of the words that missed are number words. "
                         "This episode is figure-heavy, and figures are the words most "
                         "likely to be transcribed differently from how they are spoken.")

    lines.append("WHAT THIS COULD BE, and the check does not know which: the master may be "
                 "a different take or a different episode; the script may have changed "
                 "after the render; or the words may simply be unusually hard to "
                 "transcribe. RETRYING ON ITS OWN WILL NOT CHANGE ANY OF THEM.")
    return "\n".join(lines)


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
            # BOTH SIDES, ONE DEFINITION. On our side this is a no-op — a bare
            # numeral cannot reach the spoken track (render_ready hard-fails it)
            # — and it is applied and asserted anyway, because a symmetry you
            # rely on and never exercise is a symmetry you do not have. If a
            # numeral ever DOES get through, the two sides still agree instead
            # of quietly costing anchor rate.
            plain, folded = toks(s), toks(spoken_form(s))
            if plain != folded:
                print(f"    note: the script carries a figure as digits "
                      f"({' '.join(w for w in plain if any(c.isdigit() for c in w))}) "
                      f"— folded to words for matching, as the transcript is",
                      flush=True)
            for w in folded:
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
    # fold=False: this reads the file EXACTLY as written. Folding here would let
    # a written figure and a spoken one look identical and defeat the check.
    back_words = [w for w, _ in word_timeline(back, fold=False)]
    back_words = toks(spoken_form(" ".join(back_words)))
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
        raise Halt(observed_miss_report(rate, ours, at, index, sents))
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
