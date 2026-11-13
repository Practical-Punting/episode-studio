#!/usr/bin/env python3
"""twoway_render_words.py — does this HeyGen render say the script, the whole script and nothing else?

    python engine/twoway_render_words.py <render.mp4> <spoken-words-XX.txt> [--json OUT] [--model small.en]

Exit 0 = the words are the script (a clean master, or a render that needs no cut).
Exit 1 = something to act on; the JSON says what, where, and the keep ranges that would fix it.
Exit 2 = could not run.

🔴 WHY IT EXISTS (EP56, 11–13 Nov 2026). Three faults in two renders, none caught by the
checks that existed:
  · Steve's render carried GORDON'S WHOLE SCRIPT after his own — the paste accident.
  · Gordon's render had ~24s of words in no script between two sentences.
  · BOTH opened with a false start.
`twoway_render_qc` measures shape and silences (it cannot hear words); `repeated_words`
fails only on words said TWICE, so a one-off stray stretch or a wrong script read once
passes it. This aligns every heard word to the script and reports everything that is not
the script, plus every chunk of the script that was not heard.

HOW: speech stretches from the AUDIO (silencedetect), each transcribed on its own —
`repeated_words`' own stretch-by-stretch pass, because whisper over a whole file folds a
false start away (memory: a-transcriber-folds-a-false-start). Aligned with difflib
(autojunk off). A transcriber's mishearing is a SUBSTITUTION in place and is ignored; an
INSERTION of RUN_N+ words is a stray; a DELETION of LOST_N+ words is a lost chunk.

WHAT IT PROPOSES — Jodie's standing ruling (12 Nov 2026): stray words between paragraphs
or in a pause are CUT OUT, the original kept, with a join WAV for her ear; a retake only
when they sit mid-sentence. So each stray is classed:
  · head    — before the first script word (a false start, or a wrong script first)
  · tail    — after the last script word (render-sheet notes, another man's script)
  · between — at a sentence end, with a pause both sides → cuttable
  · mid     — inside a sentence → NOT cut; Jodie's call (retake)
Every cut sits INSIDE a pause, never in speech: it keeps the pause before the stray and
ends a quarter-second before the next kept word.

⚠️ WORDLESS SOUNDS (the "vocalised break" — a breath or syllable the avatar makes in a
<break>) are REPORTED with their times for the listen, never cut or muted: a stretch the
transcriber heard no word in may still be a real short word it missed, and muting a real
word is worse than a breath.
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import repeated_words as rw    # noqa: E402  (one tokeniser, one stretch finder, one audio reader)

RUN_N = 3           # same as repeated_words: three unscripted words in a row is a stray
LOST_N = 6          # six script words in a row never heard is a lost chunk
LEAD_S = 0.25       # a cut ends this long before the next kept word
TAIL_PAD_S = 0.30   # the master runs this long past the last script word
SENT_END = re.compile(r"(?<=[.!?…])[\"'”’)\]]*\s+")


def script_with_sentence_ends(script_text: str) -> tuple[list[str], list[bool]]:
    """Script tokens, and for each one whether it ENDS a sentence (or a paragraph).

    Built sentence by sentence with the same tokeniser; if that does not reproduce the
    whole-script tokens exactly, every flag is False (=> no stray is ever called
    cuttable on a guess)."""
    whole = rw.script_tokens(script_text)
    toks, ends = [], []
    for para in rw.BREAK.sub("\n\n", script_text).split("\n\n"):
        for sent in SENT_END.split(para.strip()):
            t = rw.tokens(sent)
            if t:
                toks += t
                ends += [False] * (len(t) - 1) + [True]
    if toks != whole:
        return whole, [False] * len(whole)
    return toks, ends


def heard_words(media: pathlib.Path, model_name: str) -> tuple[list[tuple[str, float, float]], list]:
    """[(token, start_s, end_s)] in order, each speech stretch transcribed on its own."""
    from faster_whisper import WhisperModel
    a = rw._audio(media)
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    spans = rw.speech_stretches(media)
    out = []
    for s, e in spans:
        lo, hi = max(0, int((s - rw.PAD_S) * rw.SR)), min(a.size, int((e + rw.PAD_S) * rw.SR))
        segs, _ = model.transcribe(a[lo:hi], word_timestamps=True, beam_size=5,
                                   condition_on_previous_text=False, vad_filter=False)
        for sg in segs:
            for w in sg.words or []:
                for t in rw.tokens(w.word):
                    out.append((t, float(lo / rw.SR + w.start), float(lo / rw.SR + w.end)))
    return out, spans


def media_duration(media: pathlib.Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(media)], capture_output=True, text=True)
    return float(r.stdout)


def analyse(heard: list[tuple[str, float, float]], script: list[str], ends: list[bool],
            duration: float, spans: list | None = None) -> dict:
    """The pure part — no audio, no model — so it is tested on its own."""
    toks = [h[0] for h in heard]
    sm = difflib.SequenceMatcher(None, script, toks, autojunk=False)
    ops = sm.get_opcodes()
    matched = [j for op, i1, i2, j1, j2 in ops if op == "equal" for j in range(j1, j2)]
    stray, lost = [], []
    for op, i1, i2, j1, j2 in ops:
        extra = (j2 - j1) - (i2 - i1)
        if op == "insert" or (op == "replace" and extra >= RUN_N):
            if j2 - j1 < RUN_N:
                continue
            first_m = matched[0] if matched else None
            last_m = matched[-1] if matched else None
            if first_m is not None and j2 <= first_m:
                where = "head"
            elif last_m is not None and j1 > last_m:
                where = "tail"
            else:
                before = heard[j1 - 1][2] if j1 > 0 else 0.0
                after = heard[j2][1] if j2 < len(heard) else duration
                at_sentence_end = i1 > 0 and ends[i1 - 1]
                paused = (heard[j1][1] - before) >= 0.30 and (after - heard[j2 - 1][2]) >= 0.30
                where = "between" if (at_sentence_end and paused) else "mid"
            stray.append({"text": " ".join(toks[j1:j2]), "words": j2 - j1,
                          "from_s": round(heard[j1][1], 2), "to_s": round(heard[j2 - 1][2], 2),
                          "where": where, "j": [j1, j2], "script_at": i1})
        if op == "delete" or (op == "replace" and (i2 - i1) - (j2 - j1) >= LOST_N):
            if i2 - i1 >= LOST_N:
                near = heard[j1][1] if j1 < len(heard) else duration
                lost.append({"text": " ".join(script[i1:i2]), "words": i2 - i1,
                             "near_s": round(near, 2)})

    # the keep ranges: cut every head/tail/between stray, inside its pauses
    cuts = []
    for s in stray:
        j1, j2 = s["j"]
        nxt = heard[j2][1] if j2 < len(heard) else None
        prev_end = heard[j1 - 1][2] if j1 > 0 else 0.0
        if s["where"] == "head":
            a = 0.0
            b = max(heard[j2 - 1][2], nxt - LEAD_S) if nxt is not None else duration
        elif s["where"] == "tail":
            a = min(prev_end + TAIL_PAD_S, (prev_end + heard[j1][1]) / 2)
            b = duration
        elif s["where"] == "between":
            a = max(prev_end, heard[j1][1] - LEAD_S)
            b = max(heard[j2 - 1][2], nxt - LEAD_S) if nxt is not None else duration
        else:
            continue
        s["cut"] = [round(a, 2), round(b, 2)]
        cuts.append((a, b))
    # and the tail after the last script word even when nothing was SAID there
    if matched:
        last_end = heard[matched[-1]][2]
        if duration - last_end > TAIL_PAD_S + 0.5 and not any(s["where"] == "tail" for s in stray):
            cuts.append((last_end + TAIL_PAD_S, duration))
    cuts.sort()
    keep, t = [], 0.0
    for a, b in cuts:
        if a - t > 0.04:
            keep.append([round(t, 2), round(a, 2)])
        t = max(t, b)
    if duration - t > 0.04:
        keep.append([round(t, 2), round(duration, 2)])

    wordless = []
    for s0, e0 in spans or []:
        if not any(s0 - 0.1 <= h[1] <= e0 + 0.1 for h in heard):
            wordless.append([round(s0, 2), round(e0, 2)])

    mid = [s for s in stray if s["where"] == "mid"]
    return {"script_words": len(script), "heard_words": len(heard),
            "matched_words": len(matched),
            "coverage": round(len(matched) / max(1, len(script)), 4),
            "stray": stray, "lost": lost, "wordless_sounds": wordless,
            "keep_s": keep, "duration_s": round(duration, 2),
            "needs_jodie": [f"words not in the script INSIDE a sentence at {s['from_s']}s: "
                            f"\"{s['text'][:80]}\" — cut or retake is her call" for s in mid]
                           + [f"script words NOT HEARD near {x['near_s']}s: \"{x['text'][:80]}\" "
                              "— a lost chunk; retake" for x in lost],
            "ok": not stray and not lost}


def check(media: pathlib.Path, script_text: str, model_name: str = "small.en") -> dict:
    script, ends = script_with_sentence_ends(script_text)
    heard, spans = heard_words(media, model_name)
    res = analyse(heard, script, ends, media_duration(media),
                  [(float(s), float(e)) for s, e in spans])
    res.update({"media": str(media), "model": model_name,
                "heard": [[t, round(a, 2), round(b, 2)] for t, a, b in heard]})
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("media")
    ap.add_argument("script")
    ap.add_argument("--json")
    ap.add_argument("--model", default="small.en")
    a = ap.parse_args()
    import render_lock
    media, script = pathlib.Path(a.media), pathlib.Path(a.script)
    if not media.is_file() or not script.is_file():
        print(f"cannot run: missing {media if not media.is_file() else script}", file=sys.stderr)
        return 2
    with render_lock.hold("PP", f"render words {media.name}"):
        res = check(media, script.read_text(encoding="utf-8"), a.model)
    res["script"] = str(script)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"{media.name} vs {script.name}: heard {res['heard_words']} words, "
          f"{res['matched_words']} of {res['script_words']} script words matched "
          f"({res['coverage']:.1%})")
    for s in res["stray"]:
        print(f"  STRAY [{s['where']}] {s['from_s']}–{s['to_s']}s ({s['words']} words): "
              f"\"{s['text'][:100]}\"" + (f"  -> cut {s['cut']}" if "cut" in s else "  -> NOT cut"))
    for x in res["lost"]:
        print(f"  LOST near {x['near_s']}s ({x['words']} words): \"{x['text'][:100]}\"")
    for w in res["wordless_sounds"]:
        print(f"  sound with no words heard at {w[0]}–{w[1]}s (listen; not cut)")
    print(f"  keep: {res['keep_s']}")
    print("PASS: the words are the script." if res["ok"] else
          "ACT: the render is not just the script — see above.")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
