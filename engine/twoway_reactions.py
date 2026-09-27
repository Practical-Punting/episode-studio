#!/usr/bin/env python3
"""The reaction catalogue — the contract between the decision layer and the assembler.

    python engine/twoway_reactions.py [--assets DIR]

Build spec §8 writes `"reaction": "R9"` into `episode.json`. **Something has to turn that
into a file**, and that something is this: a catalogue Jodie builds once and the studio
reuses for every episode.

🔴 **IT VALIDATES ON LOAD.** Every id present, both presenters, every file on disk
(build spec §8). A catalogue with R9 for Brian but not Barry is half a vocabulary, and
the selector has no way to know which half it is allowed to use.

⚠️ **A MISSING REACTION FALLS BACK TO R1a AND SAYS SO IN THE RUN LOG.** It must never
fail the build and it must never be silent — a substitution nobody can see is how a
library quietly rots. The log line names the episode, the beat, what was asked for and
what was played.

📌 **`duration_s` IS MEASURED FROM THE FILE, NEVER TYPED** (`PP-TWO-WAY-REACTIONS.md`
§4). A typed duration is right until somebody re-renders a clip.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import twoway_beats as tb                                        # noqa: E402

ASSETS = HERE.parent / ".claude/skills/pp-episode-production/assets/reactions"
FALLBACK = "R1a"
"""What plays when a code has no file. R1a because it is the ONE clip that is proven to
exist (23 Aug 2026, ~30 credits, measured) and the only one that is never wrong — a
neutral listen under any line is dull; a laugh under the wrong line is a fault."""

SPEAKERS = ("BB", "BM")
CODES = tuple(tb.BEDS) + tuple(tb.PUNCT)

ENDS_NEUTRAL = {c: True for c in CODES}
ENDS_NEUTRAL["R10"] = False
"""🔴 R10 DELIBERATELY ENDS FORWARD, because a cut to that person always follows it.
Every other loop returns to the same neutral head position. Getting this wrong produces
a visible jump."""

LOOPABLE = {c: False for c in CODES}
LOOPABLE.update({"R1a": False, "R1b": False, "R11": False, "R2": True})
"""⚰️ THE BEDS USED TO BE LOOPABLE AND ARE NOT ANY MORE (Jodie, 16 Sep 2026): a listen
that outruns its bed CHAINS to a different bed, it never loops. R7 (a laugh) and R10
were never loopable — looping them is grotesque. If a non-loopable clip is shorter than
the span, play it once and hold its last frame, or fall back."""


class Invalid(Exception):
    """The catalogue cannot be trusted. Nothing that reads it may run."""


def _probe(path: pathlib.Path) -> float:
    import pp_paths
    r = subprocess.run([pp_paths.ffprobe() or "ffprobe", "-v", "error",
                        "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True, timeout=120)
    try:
        return round(float((r.stdout or "").strip()), 3)
    except ValueError:
        raise Invalid(f"{path.name}: ffprobe could not read a duration from it. A file "
                      f"that is present but unreadable is worse than a missing one — "
                      f"the catalogue would carry it as real.")


def filename(speaker: str, code: str) -> str:
    """`PP-TWO-WAY-REACTIONS.md` §4: assets/reactions/<BB|BM>-R<n>.mp4."""
    return f"{speaker}-{code}.mp4"


def build(assets: pathlib.Path = ASSETS, strict: bool = False) -> dict:
    """Read the clips on disk and write the catalogue. Durations MEASURED.

    `strict` raises on an incomplete library; the default reports what is missing and
    returns a catalogue the assembler can still run against — which is what lets the
    format ship on harvested pauses before the twelve loops are rendered.
    """
    reactions, missing = [], []
    for code in CODES:
        clips = {}
        for sp in SPEAKERS:
            p = assets / filename(sp, code)
            if p.is_file():
                clips[sp] = {"file": f"assets/reactions/{p.name}",
                             "duration_s": _probe(p)}
            else:
                missing.append(f"{sp}-{code}")
        reactions.append({"id": code, "kind": "bed" if code in tb.BEDS else "punct",
                          "clips": clips,
                          "ends_neutral": ENDS_NEUTRAL[code],
                          "loopable": LOOPABLE[code]})
    cat = {
        "_what_this_is": "The reaction clip library. R1a-R12 are defined in "
                         "PP-TWO-WAY-FORMAT.md §4 and PP-TWO-WAY-REACTIONS.md §3 — "
                         "those say what each one MEANS and how the footage is MADE; "
                         "this says where the footage IS. One home each.",
        "_durations": "MEASURED from the files by twoway_reactions.py, never typed.",
        "_fallback": f"A code with no file plays {FALLBACK} and the run log says so.",
        "reactions": reactions,
    }
    if missing and strict:
        raise Invalid(
            f"{len(missing)} clip(s) are not on disk: {missing[:8]}"
            f"{'…' if len(missing) > 8 else ''}. A catalogue with a code for one "
            f"presenter and not the other is half a vocabulary, and the selector has "
            f"no way to know which half it may use.")
    cat["_missing"] = missing
    return cat


def validate(cat: dict, assets: pathlib.Path = ASSETS) -> list[str]:
    """What is wrong with this catalogue, in plain English. Empty means it is sound."""
    out = []
    seen = {r["id"] for r in cat.get("reactions", [])}
    for code in CODES:
        if code not in seen:
            out.append(f"{code} is not in the catalogue at all — the selector can "
                       f"choose it and nothing could resolve it.")
    for r in cat.get("reactions", []):
        if r["id"] not in CODES:
            out.append(f"{r['id']} is in the catalogue and is not a code the format "
                       f"defines (PP-TWO-WAY-FORMAT.md §4).")
        for sp in SPEAKERS:
            c = (r.get("clips") or {}).get(sp)
            if not c:
                continue
            p = assets.parent.parent / c["file"] if not pathlib.Path(c["file"]).is_absolute() \
                else pathlib.Path(c["file"])
            p = assets / pathlib.Path(c["file"]).name
            if not p.is_file():
                out.append(f"{r['id']} names {c['file']} for {sp} and that file is not "
                           f"on disk.")
            elif not c.get("duration_s"):
                out.append(f"{r['id']} for {sp} has no measured duration.")
        if r["id"] == "R10" and r.get("ends_neutral"):
            out.append("R10 is marked ends_neutral, and it must not be: a cut to that "
                       "man always follows it, so it ends FORWARD.")
        if r["id"] in tb.BEDS and r.get("loopable"):
            out.append(f"{r['id']} is a BED marked loopable. Jodie, 16 Sep 2026: a bed "
                       f"is NEVER looped — a long listen chains to a different bed.")
    return out


def resolve(cat: dict, speaker: str, code: str, ep: str = "", beat: int | None = None,
            log: list | None = None) -> dict:
    """The file to play for (speaker, code) — or the fallback, said out loud.

    🔴 THE LOG LINE IS NOT OPTIONAL. Build spec §8: it names the episode, the beat, what
    was asked for and what was played.
    """
    by = {r["id"]: r for r in cat.get("reactions", [])}
    got = (by.get(code, {}).get("clips") or {}).get(speaker)
    if got:
        return dict(got, id=code, substituted=False)
    alt = (by.get(FALLBACK, {}).get("clips") or {}).get(speaker)
    line = (f"REACTION SUBSTITUTED — {ep or 'episode ?'} beat "
            f"{beat if beat is not None else '?'}: asked for {code} on {speaker}, "
            f"played {FALLBACK if alt else 'NOTHING — the pauses'} "
            f"({'no clip for that code yet' if alt else 'no clip at all yet'}).")
    if log is not None:
        log.append(line)
    else:
        print(line, flush=True)
    return dict(alt or {}, id=FALLBACK if alt else None, substituted=True,
                asked=code, why=line)


CUSTOM_MOTION_WINDOW_S = 10.0
"""How long HeyGen's Custom Motion actually governs. Past it the prompt stops holding."""

BED_WAKE_RATIO = 2.0
"""Mouth motion after the window, as a multiple of the first ten seconds, at which a bed
is FLAGGED. Not a hard fail — the eye decides whether it reads as fidgeting."""


def bed_wake_check(path, mouth_box, window_s: float = CUSTOM_MOTION_WINDOW_S) -> dict:
    """Does this bed wake up once Custom Motion lets go? (Reactions doc §2, item 7.)

    🔴 THE MOUTH IS COMPARED WITH THE WHOLE FACE, because a fixed box cannot tell a
    mouth opening from a head moving through it: if both rise together it is the head,
    and only the mouth rising faster is the fault the rule is about.
    """
    import subprocess
    import numpy as np
    W, H, FPS = 480, 270, 10.0
    buf = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-vf", f"fps={FPS},scale={W}:{H},format=gray", "-f", "rawvideo",
         "-pix_fmt", "gray", "-"], capture_output=True, timeout=1800).stdout
    n = len(buf) // (W * H)
    if n < int(window_s * FPS) + 20:
        return {"clip": str(path), "measurable": False,
                "why": f"only {n / FPS:.1f}s — shorter than the window plus a sample"}
    st = np.frombuffer(buf[: n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)
    d = np.abs(np.diff(st, axis=0))
    r0, r1, c0, c1 = mouth_box
    face = (max(0, r0 - 60), min(H, r1 + 22), max(0, c0 - 24), min(W, c1 + 24))
    k = int(window_s * FPS)

    def pair(box):
        b = d[:, box[0]:box[1], box[2]:box[3]]
        return float(b[:k].mean()), float(b[k:].mean())

    m0, m1 = pair((r0, r1, c0, c1))
    f0, f1 = pair(face)
    ratio = m1 / m0 if m0 else float("inf")
    fratio = f1 / f0 if f0 else float("inf")
    return {"clip": pathlib.Path(path).name, "measurable": True,
            "dur_s": round(n / FPS, 2),
            "mouth_first": round(m0, 4), "mouth_after": round(m1, 4),
            "mouth_ratio": round(ratio, 3),
            "face_first": round(f0, 4), "face_after": round(f1, 4),
            "face_ratio": round(fratio, 3),
            "flag": ratio > BED_WAKE_RATIO,
            "the_mouth_outran_the_head": ratio > fratio,
            "verdict": ("FLAG — mouth motion x%.2f after the %.0fs window%s"
                        % (ratio, window_s,
                           " and it outran the head" if ratio > fratio else "")
                        if ratio > BED_WAKE_RATIO else
                        "ok — mouth motion x%.2f, inside the %.1fx limit"
                        % (ratio, BED_WAKE_RATIO))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default=str(ASSETS))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    assets = pathlib.Path(a.assets)
    cat = build(assets)
    print(f"{len(cat['reactions'])} codes, {len(SPEAKERS)} presenters")
    have = sum(len(r["clips"]) for r in cat["reactions"])
    print(f"clips on disk: {have} of {len(CODES) * len(SPEAKERS)}")
    if cat["_missing"]:
        print(f"not yet rendered: {len(cat['_missing'])} — "
              f"{cat['_missing'][:6]}{'…' if len(cat['_missing']) > 6 else ''}")
        print(f"  every one of those falls back to {FALLBACK} and says so in the run "
              f"log. The build does not stop.")
    bad = validate(cat, assets)
    print("validation:", "sound" if not bad else "\n  - " + "\n  - ".join(bad[:6]))
    if a.write:
        dest = assets / "catalogue.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
        print(f"WROTE {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
