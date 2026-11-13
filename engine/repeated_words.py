#!/usr/bin/env python3
"""repeated_words.py — FAIL on any run of words a presenter says more often than the script does.

    python engine/repeated_words.py <master.mp4> <spoken-words.txt> [--json OUT] [--model small.en]

Exit 0 = no repeated run; exit 1 = at least one (each printed with where it is heard);
exit 2 = could not run.

🔴 WHY IT EXISTS (EP56, Jodie, 13 Nov 2026). Gordon's render opened with a FALSE START —
*"This is part three of a conversation that"*, a pause, then the whole sentence again — and
every transcript check before cut 2 passed it. Jodie heard it on her first watch.

WHY THEY PASSED, measured on the real file, not guessed:
  1. THE TRANSCRIBER NEVER HEARD THE REPEAT. faster-whisper `base.en` over the whole master
     folds a restart into the sentence that follows: it wrote ONE "This is part three of a
     conversation that ran in…", stretching "in" over 3.48-5.56s (the 12 Nov plain pass) or
     "of" over 1.36-4.94s. The 12 Nov proof's "two independent passes" were the SAME model
     with the same habit, so the second pass agreed with the first — two copies of one
     blind spot. `small.en` on the same 12s hears both takes; so does `base.en` when each
     side of the pause is transcribed on its own.
  2. AND A COVERAGE CHECK CANNOT SEE A DUPLICATE ANYWAY. "Is every script word heard, in
     order?" is true of a take that says a sentence twice — the extra copy is not a missing
     word. And `align_to_script` writes the SCRIPT's text into the SRT by design, so an SRT
     can never show a word the script does not have.

SO THIS CHECK DOES TWO THINGS DIFFERENTLY:
  * It transcribes EACH STRETCH OF SPEECH BETWEEN PAUSES ON ITS OWN (the pauses found in the
    audio, -40 dB for 0.25s), so no decoder can merge a restart across the pause that always
    follows a false start — plus one whole-file pass with the stronger model, for a repeat
    said with no pause at all. A repeat heard by EITHER pass fails.
  * It aligns what was heard against the script and flags a run of RUN_N+ heard words that
    has NO PLACE IN THE SCRIPT and is said again elsewhere (`repeated_runs`). A phrase the
    script itself repeats is not a fault, at any distance; a transcriber's consistent
    mishearing is not a fault (it is a substitution, not an insertion); a repeat anywhere —
    a false start at 0:01, or a whole paragraph read twice at 4:00 — is.

🔴 THE SCRIPT MUST BE IN THE ORDER IT IS HEARD. For one presenter's master that is his
spoken-words file. For a FINISHED TWO-WAY FILM it is `renders/merged.srt`'s text (the two
scripts' own words, interleaved as the film plays them) — NOT one script then the other. Fed
Gordon's script followed by Steve's, every one of Steve's turns aligns as an insertion and the
check reports eight "repeats" in a clean film (EP56 cut 3, 13 Nov 2026 — my own QC input).

📌 RUN_N = 3. A two-word stutter ("the the") is below it on purpose: EP56's isolated "T—"
before "These individuals" was heard and KEPT by Jodie (12 Nov). This check is for a phrase
said twice, which is a take fault; a stutter is a judgement for the ear.

⚠️ WHAT IT CANNOT DO: find a repeat the transcriber mishears differently each time so that no
three-word run matches. It reports what it heard, with times, so a human can listen to any
flagged spot; a pass is a statement about what two transcriptions heard, nothing more.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

RUN_N = 3
SR = 16000
SILENCE_DB = -40.0
SILENCE_MIN_S = 0.25
PAD_S = 0.08
BREAK = re.compile(r"<break[^>]*/>")


def tokens(text: str) -> list[str]:
    """Both sides folded the SRT step's own way (figures to words), hyphens split."""
    import align_to_script as ats
    s = ats.spoken_form(text.replace("’", "'").replace("-", " ").replace("—", " "))
    return re.findall(r"[a-z0-9']+", s.lower())


def script_tokens(script_text: str) -> list[str]:
    return tokens(BREAK.sub(" ", script_text))


def repeated_runs(heard: list[tuple[str, float]], script: list[str], n: int = RUN_N) -> list[dict]:
    """Every run of >= n heard words that has NO PLACE IN THE SCRIPT and is said elsewhere too.

    `heard` is [(token, time_s)] in order. A pure function — no audio, no model — so it is
    tested on its own (`test_repeated_words.py`).

    HOW: align what was heard against the script (difflib, autojunk off — CLAUDE.md's own
    `autojunk` trap). A false start or a paragraph read twice is an INSERTION: words heard with
    no script words under them. A transcriber's SPELLING ("one hundred dollars zero" for "one
    hundred thousand dollars", "meters" for "metres", "flood has" for "flutters") is a
    SUBSTITUTION in place, so it can never qualify — which matters, because a phrase the
    script says twice is misheard the same way twice.

    ⚠️ THE FIRST VERSION COUNTED n-GRAMS ("heard more often than scripted") and on EP56's real
    masters it flagged exactly those three mishearings, each one twice, as repeats: a misheard
    phrase has a script count of ZERO, so hearing it twice looks like a repeat. Counting cannot
    tell a repeat from a consistent mishearing; alignment can.

    An inserted run counts when one of its n-grams is ALSO heard outside the run, or is in the
    script — i.e. it is said again, not merely unscripted. Returns one dict per run: its text,
    start, the n-gram that repeats, and every time that n-gram is heard.
    """
    import difflib
    toks = [t for t, _ in heard]
    if len(toks) < n:
        return []
    sm = difflib.SequenceMatcher(None, script, toks, autojunk=False)
    cand = [False] * len(toks)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "insert" or (op == "replace" and (j2 - j1) - (i2 - i1) >= n):
            for k in range(j1, j2):
                cand[k] = True
    sgrams = {tuple(script[i:i + n]) for i in range(len(script) - n + 1)}
    hpos: dict[tuple, list[int]] = {}
    for i in range(len(toks) - n + 1):
        hpos.setdefault(tuple(toks[i:i + n]), []).append(i)
    out, i = [], 0
    while i < len(toks):
        if not cand[i]:
            i += 1
            continue
        j = i
        while j < len(toks) and cand[j]:
            j += 1
        if j - i >= n:
            for k in range(i, j - n + 1):
                g = tuple(toks[k:k + n])
                elsewhere = [p for p in hpos.get(g, []) if not (i <= p < j)]
                if elsewhere or g in sgrams:
                    out.append({"text": " ".join(toks[i:j]), "at_s": round(heard[i][1], 2),
                                "first_ngram": " ".join(g), "heard": len(hpos[g]),
                                "in_script": sum(1 for x in range(len(script) - n + 1)
                                                 if tuple(script[x:x + n]) == g),
                                "occurrences_s": [round(heard[p][1], 2) for p in hpos[g]]})
                    break
        i = j
    return out


def _audio(media: pathlib.Path):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, timeout=1800).stdout
    return np.frombuffer(raw, np.float32).copy()


def speech_stretches(media: pathlib.Path) -> list[tuple[float, float]]:
    """The stretches of speech between pauses, from the AUDIO (never from an SRT)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-vn", "-af",
                        f"silencedetect=n={SILENCE_DB}dB:d={SILENCE_MIN_S}", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=1800)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "default=nw=1:nk=1", str(media)], capture_output=True, text=True).stdout)
    edges, t = [], 0.0
    for s, e in zip(starts, ends + [dur] * (len(starts) - len(ends))):
        if s - t > 0.15:
            edges.append((t, s))
        t = e
    if dur - t > 0.15:
        edges.append((t, dur))
    return edges


def transcribe(media: pathlib.Path, model_name: str = "small.en") -> dict:
    """Two passes: each speech stretch on its own, and the whole file. [(token, time_s)] each."""
    from faster_whisper import WhisperModel
    a = _audio(media)
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    out = {"stretches": [], "whole": []}
    spans = speech_stretches(media)
    for s, e in spans:
        lo, hi = max(0, int((s - PAD_S) * SR)), min(a.size, int((e + PAD_S) * SR))
        segs, _ = model.transcribe(a[lo:hi], word_timestamps=True, beam_size=5,
                                   condition_on_previous_text=False, vad_filter=False)
        for sg in segs:
            for w in sg.words or []:
                for t in tokens(w.word):
                    out["stretches"].append((t, lo / SR + w.start))
    segs, _ = model.transcribe(a, word_timestamps=True, beam_size=5,
                               condition_on_previous_text=False, vad_filter=False)
    for sg in segs:
        for w in sg.words or []:
            for t in tokens(w.word):
                out["whole"].append((t, w.start))
    out["n_stretches"] = len(spans)
    return out


def check(media: pathlib.Path, script_text: str, model_name: str = "small.en") -> dict:
    sc = script_tokens(script_text)
    heard = transcribe(media, model_name)
    res = {"media": str(media), "model": model_name, "run_n": RUN_N, "script_words": len(sc),
           "stretches": heard["n_stretches"], "passes": {}}
    for p in ("stretches", "whole"):
        res["passes"][p] = {"heard_words": len(heard[p]), "repeats": repeated_runs(heard[p], sc),
                            "words": [[t, round(s, 2)] for t, s in heard[p]]}
    found = {}
    for p in ("stretches", "whole"):
        for r in res["passes"][p]["repeats"]:
            found.setdefault(r["first_ngram"], dict(r, passes=[]))["passes"].append(p)
    res["repeats"] = sorted(found.values(), key=lambda r: r["at_s"])
    res["ok"] = not res["repeats"]
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
    with render_lock.hold("PP", f"repeated_words {media.name}"):
        res = check(media, script.read_text(encoding="utf-8"), a.model)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"{media.name} vs {script.name}: {res['stretches']} speech stretches; heard "
          f"{res['passes']['stretches']['heard_words']} / {res['passes']['whole']['heard_words']} words "
          f"(stretch-by-stretch / whole file) against {res['script_words']} in the script")
    if res["ok"]:
        print(f"PASS: no run of {RUN_N}+ words is said that the script does not say there "
              f"(no false start, nothing read twice).")
        return 0
    print(f"FAIL: {len(res['repeats'])} run(s) said again that the script does not repeat "
          f"(a false start, a re-read, or — if every hit is a long passage — the script fed out "
          f"of the order it is heard):")
    for r in res["repeats"]:
        print(f"  {r['at_s']:8.2f}s  \"{r['text']}\"  — '{r['first_ngram']}' heard {r['heard']}x, "
              f"script {r['in_script']}x, at {r['occurrences_s']}s  [{' + '.join(r['passes'])}]")
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
