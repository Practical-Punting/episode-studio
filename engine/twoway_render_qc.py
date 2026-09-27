#!/usr/bin/env python3
"""twoway_render_qc.py — does this HeyGen master carry the script that was pasted?

    python engine/twoway_render_qc.py <master.mp4> <script.txt> [--json out.json]

Three questions, in the order they matter:

  1. **Is it the right shape?** 1920x1080, and long enough for the words plus the
     breaks. A master that is much shorter than the script has LOST A CHUNK, and that
     is the failure this exists to catch.
  2. **Did every break land?** The script declares `<break time="Ns"/>` between its
     segments; the render should show that many silences, in that order, each about
     that long. A gap that is missing, short, or has speech running through it means
     HeyGen did not honour the tag -- and the whole two-way cut is built on those
     silences being where the script says they are.
  3. **Is the picture actually there?** Duration from the container is METADATA. An
     mp4 written with `faststart` announces the length it INTENDED even when the tail
     never arrived (EP15: a "13:31" file that stopped mid-word at 9:10). So the frame
     count is read by DECODING, not from the header, and compared with duration x fps.

\U0001f534 SILENCE IS MEASURED ON THE AUDIO, NEVER INFERRED FROM THE SCRIPT. The script
says how many gaps to EXPECT; ffmpeg's `silencedetect` says how many there ARE. A check
that counted the tags and reported them back would be asking the file whether it agrees
with itself -- which is the consistency fault this repo already has scars from.

⚠️ AND THE THRESHOLD IS NAMED, NOT GUESSED. `-40dB` over `SILENCE_MIN_S`: a
HeyGen idle passage is not digital silence, it is a room tone under a still avatar, and
a floor tight enough for true silence finds none of them.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

SILENCE_DB = -40
SILENCE_MIN_S = 1.5
"""Below the 2.0s floor at which a pause counts as a turn boundary, on purpose: this
check has to be able to SEE a gap that came back short and say so, and a detector that
cannot see a 1.6s gap reports it as missing instead of as short. Naming a fault
correctly is most of what makes it fixable."""

GAP_TOL_S = 2.5
"""How far under the asked length a delivered gap may fall before it is called short.
Measured spread on 17-18 Sep: asked 4.000s, delivered 2.246-4.868s. At an asked 6s that
same spread lands 4.25-6.87s, so 2.5s below the ask is the edge of what has ever been
seen rather than a round number."""


def _run(cmd: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def probe(master: pathlib.Path) -> dict:
    r = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=width,height,r_frame_rate,nb_read_packets",
              "-count_packets", "-show_entries", "format=duration,bit_rate",
              "-of", "json", str(master)])
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    fmt = d.get("format") or {}
    num, _, den = (st.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    a = _run(["ffprobe", "-v", "error", "-select_streams", "a:0",
              "-show_entries", "stream=bit_rate,sample_rate,channels",
              "-of", "json", str(master)])
    au = (json.loads(a.stdout or "{}").get("streams") or [{}])[0]
    return {"w": st.get("width"), "h": st.get("height"), "fps": round(fps, 3),
            "frames": int(st.get("nb_read_packets") or 0),
            "dur_s": round(float(fmt.get("duration") or 0), 2),
            "video_kbps": round(int(fmt.get("bit_rate") or 0) / 1000),
            "audio_kbps": round(int(au.get("bit_rate") or 0) / 1000),
            "bytes": master.stat().st_size}


def silences(master: pathlib.Path, min_s: float | None = None) -> list[dict]:
    """Every stretch of near-silence, measured on the audio.

    `min_s` overrides the break-hunting floor. The splice uses a much finer one to find
    a render's opening and closing beat, which is a few tenths of a second and invisible
    at the floor this module hunts breaks with.
    """
    d = SILENCE_MIN_S if min_s is None else min_s
    r = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(master),
              "-af", f"silencedetect=noise={SILENCE_DB}dB:d={d}",
              "-f", "null", "-"])
    # 🔴 silencedetect LOGS AT INFO. Reading this at `-v error` would throw away every
    # line it writes and return an empty list that looks exactly like "no silences" —
    # the freezedetect fault of 8 Aug, which passed a clip frozen solid for two seconds.
    text = (r.stderr or "") + (r.stdout or "")
    out, start = [], None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)(?:\s*\|\s*silence_duration: "
                         r"([\d.]+))?", text):
        kind, val, dur = m.group(1), float(m.group(2)), m.group(3)
        if kind == "start":
            start = val
        elif start is not None:
            out.append({"from_s": round(start, 2), "to_s": round(val, 2),
                        "dur_s": round(float(dur) if dur else val - start, 2)})
            start = None
    return out


BREAK_RE = re.compile(r'<break\s+time="([\d.]+)s"\s*/>')


ISLAND_MAX_S = 1.0
"""How long a scrap of sound may be and still sit INSIDE one pause.

🔴 A BREATH SPLITS A SILENCE IN TWO, AND THE RAW DETECTION THEN READS AS TWO SHORT
GAPS. Steve's master shows the pattern three times: 2.25s of silence, a quarter-second
of something, then 1.78s more — reported as a 2.25s gap where the script asked for six,
which is a FAULT that is not there. Merged, it is one pause of 4.28s.

The avatar is not a synthesiser holding digital silence; it is a picture of a man
sitting still, and a man sitting still breathes. So two silences separated by less than
a second of sound are one pause, and the measurement says what a listener would say.

⚠️ THE MERGE IS DELIBERATELY TIGHT. At two seconds it would swallow a short SENTENCE
between two pauses and report a gap that never happened — which is the same fault in the
other direction and much harder to see.
"""


def merge_silences(sil: list[dict]) -> list[dict]:
    """One pause is one pause, whatever a breath in the middle of it does to the log."""
    out: list[dict] = []
    for s in sil:
        if out and s["from_s"] - out[-1]["to_s"] <= ISLAND_MAX_S:
            prev = out[-1]
            prev["to_s"] = s["to_s"]
            prev["dur_s"] = round(prev["to_s"] - prev["from_s"], 2)
            prev["islands"] = prev.get("islands", 0) + 1
        else:
            out.append(dict(s))
    return out


def asked_breaks(script: pathlib.Path) -> list[float]:
    return [float(x) for x in BREAK_RE.findall(script.read_text(encoding="utf-8"))]


def segments(script: pathlib.Path) -> list[int]:
    """Words in each segment, in order — what the breaks sit BETWEEN."""
    body = "\n".join(l for l in script.read_text(encoding="utf-8").splitlines()
                     if not l.startswith("#"))
    return [len(part.split()) for part in BREAK_RE.split(body)[::2]]


def spoken_words(script: pathlib.Path) -> int:
    return sum(segments(script))


MATCH_WINDOW_S = 20.0
"""How far from its predicted position a gap may be and still be THAT gap.

🔴 A GAP IS MATCHED BY POSITION, NOT BY ORDER, AND THIS IS WHY. The first version of
this check zipped the asked breaks against the detected silences in order, and on
Steve's master it paired break 1 with a NATURAL PAUSE 2.25s long and then reported
three of four breaks as short. Every number in that report was real and the conclusion
was wrong: an avatar pauses inside a paragraph too, so a silence list is longer than a
break list and position is the only thing that says which is which.

The prediction comes from the script's own word counts scaled to the master's own
speech time — no assumed words-per-second, so a fast or slow voice moves the prediction
with it rather than breaking the match."""


def expected_break_times(seg_words: list[int], asked: list[float],
                         sil: list[dict], dur: float) -> list[float]:
    """Where each break should START, on the master's clock.

    Speech time is what is left after every detected silence, so the rate is this
    render's own — measured, not assumed.
    """
    speech_s = max(0.1, dur - sum(s["dur_s"] for s in sil))
    total_w = max(1, sum(seg_words))
    rate = speech_s / total_w
    out, clock = [], 0.0
    for i, w in enumerate(seg_words[:-1]):
        clock += w * rate
        out.append(round(clock, 2))
        clock += asked[i] if i < len(asked) else 0.0
    return out


def check(master: pathlib.Path, script: pathlib.Path) -> dict:
    p = probe(master)
    asked = asked_breaks(script)
    words = spoken_words(script)
    sil = merge_silences(silences(master))
    # The gaps BETWEEN segments — a silence at the very head or tail of the file is the
    # render settling, not a break the script asked for.
    inner = [s for s in sil if s["from_s"] > 1.0 and s["to_s"] < p["dur_s"] - 1.0]

    faults, notes = [], []
    if (p["w"], p["h"]) != (1920, 1080):
        faults.append(f"the picture is {p['w']}x{p['h']}, not 1920x1080.")
    expect_s = words / 2.6 + sum(asked)
    if p["dur_s"] < expect_s * 0.75:
        faults.append(
            f"the master is {p['dur_s']:.0f}s and the script is about {expect_s:.0f}s "
            f"of words and breaks. That is {100 * (1 - p['dur_s'] / expect_s):.0f}% "
            f"short — a chunk of script is missing from the render.")
    exp_frames = round(p["dur_s"] * p["fps"])
    if p["frames"] and abs(p["frames"] - exp_frames) > p["fps"]:
        faults.append(
            f"{p['frames']:,} frames decoded against {exp_frames:,} the header "
            f"implies — the container announces a length the picture does not reach.")

    seg_w = segments(script)
    want_at = expected_break_times(seg_w, asked, inner, p["dur_s"])
    used, matched = set(), []
    for k, (a, at) in enumerate(zip(asked, want_at), 1):
        near = [(i, s) for i, s in enumerate(inner)
                if i not in used and abs(s["from_s"] - at) <= MATCH_WINDOW_S]
        if not near:
            matched.append((k, a, at, None))
            faults.append(
                f"break {k} (asked {a:.0f}s, due about {at:.0f}s) has NO silence within "
                f"{MATCH_WINDOW_S:.0f}s of it — the tag did not land, and the words on "
                f"either side of it run together.")
            continue
        i, g = max(near, key=lambda p_: p_[1]["dur_s"])
        used.add(i)
        matched.append((k, a, at, g))
        if g["dur_s"] < a - GAP_TOL_S:
            faults.append(
                f"break {k} came back {g['dur_s']:.2f}s against {a:.0f}s asked "
                f"(at {g['from_s']:.0f}s) — more than {GAP_TOL_S:.1f}s short.")
    for k, a, at, g in matched:
        if g:
            notes.append(f"break {k:>2}: asked {a:.0f}s, got {g['dur_s']:>5.2f}s at "
                         f"{g['from_s']:>7.1f}s  (due ~{at:.0f}s, "
                         f"{g['from_s'] - at:+.0f}s)")
        else:
            notes.append(f"break {k:>2}: asked {a:.0f}s, MISSING (due ~{at:.0f}s)")
    spare = [s for i, s in enumerate(inner) if i not in used]
    if spare:
        notes.append(f"{len(spare)} other silence(s) — natural pauses inside a "
                     f"paragraph, not breaks: "
                     + ", ".join(f"{s['dur_s']:.1f}s@{s['from_s']:.0f}s"
                                 for s in spare[:6]))
    return {"master": master.name, "script": script.name, **p,
            "words": words, "expect_s": round(expect_s, 1),
            "asked_breaks": asked, "gaps": inner,
            "matched": [{"n": k, "asked_s": a, "due_s": at,
                         "got_s": (g or {}).get("dur_s"),
                         "at_s": (g or {}).get("from_s")} for k, a, at, g in matched],
            "faults": faults, "notes": notes}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("master")
    ap.add_argument("script")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    r = check(pathlib.Path(a.master), pathlib.Path(a.script))
    print(f"{r['master']}")
    print(f"  {r['dur_s']:.1f}s  {r['w']}x{r['h']}  {r['fps']}fps  "
          f"{r['frames']:,} frames  {r['bytes']:,} bytes")
    print(f"  audio {r['audio_kbps']} kbps   script {r['words']:,} words, "
          f"{len(r['asked_breaks'])} breaks, expected ~{r['expect_s']:.0f}s")
    for n in r["notes"]:
        print("  " + n)
    if r["faults"]:
        print(f"\n  \U0001f534 {len(r['faults'])} FAULT(S):")
        for f in r["faults"]:
            print("   ! " + f)
    else:
        print("\n  ✅ clean — right shape, right length, every break where the "
              "script puts it.")
    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps(r, indent=1), encoding="utf-8")
    return 1 if r["faults"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
