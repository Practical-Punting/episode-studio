#!/usr/bin/env python3
"""twoway_splice.py — patch a bad stretch of a HeyGen master with a retake of it.

    python engine/twoway_splice.py <master.mp4> <script.txt> <retake.mp4> \
        --segments 6,7 [--out patched.mp4] [--plan-only]

HeyGen's Patrick voice goes ROBOTIC now and then, and on a long render it can do it in
the MIDDLE: EP49's Gordon master is clean for four minutes, robotic from 4:14 to 6:48,
and clean again from the next break. Re-rendering ten minutes to fix two and a half is
the expensive answer; the cheap one is a retake of just those segments, spliced in.

🔴 THE CUT IS ALWAYS INSIDE A SILENCE, NEVER INSIDE SPEECH. The script puts a six-second
SSML break between every segment, and those breaks are what makes this safe: the join
happens where a man is sitting still saying nothing. Cut a frame into a word and the
seam is audible forever; cut into six seconds of idle and the only thing that changes is
the picture, between two shots of the same man in the same chair.

  A  = the master, from 0 to the END of the break BEFORE the first patched segment
  B  = the retake, from its first word to its last
  C  = the master, from the START of the break AFTER the last patched segment, to the end

So A ends with a whole break, C begins with a whole break, and B carries only speech and
its own internal breaks. Nothing is trimmed from anybody's words.

⚠️ AND THE BOUNDARIES ARE MEASURED, NEVER ASSUMED. They come from `twoway_render_qc`'s
own silence scan of each file — the same function that proved the breaks landed in the
first place — so the splice and the QC cannot disagree about where a break is.

📌 THE ORIGINAL IS NEVER TOUCHED. A new file is written; both masters stay on disk.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import twoway_render_qc as qc                                     # noqa: E402


class Refuse(Exception):
    pass


def boundaries(master: pathlib.Path, script: pathlib.Path) -> dict:
    """Where every break in this master starts and ends, matched to its script break."""
    r = qc.check(master, script)
    if any("MISSING" in n for n in r["notes"]):
        raise Refuse(f"{master.name}: a break is missing, so its segment boundaries "
                     f"cannot be trusted. Fix the render, not the splice.")
    return r


EDGE_MIN_S = 0.12
"""The shortest stretch of quiet that counts as the render's opening/closing beat.

🔴 THE EDGES NEED A FINER THRESHOLD THAN THE BREAKS DO, AND USING ONE THRESHOLD FOR BOTH
GETS THE TRIM WRONG. `twoway_render_qc` looks for silences of 1.5s and up, because it is
hunting six-second breaks and a 0.4s pause between sentences is noise to it. But a
HeyGen render's opening beat is **0.377s** on EP49's retake and its closing beat 0.360s
— both invisible at 1.5s, so the first version of this function found no edges and
planned to splice the WHOLE FILE.

That is not a disaster; it is 0.74s of extra stillness added to two breaks that are
already six seconds long. It is also not what was asked for, and the difference between
"there is no head silence" and "there is 0.377s of head silence and I could not see it"
is the difference between a measurement and a blind spot.
"""


def speech_span(retake: pathlib.Path) -> tuple[float, float, list[dict]]:
    """The retake's first word to its last — head and tail stillness trimmed off.

    A HeyGen render opens and closes on a beat of stillness. Keeping it would add that
    beat to a break that is already six seconds long, on both sides.
    """
    p = qc.probe(retake)
    dur = p["dur_s"]
    inner = [s for s in qc.merge_silences(qc.silences(retake))
             if s["from_s"] > 0.30 and s["to_s"] < dur - 0.30]
    fine = qc.merge_silences(qc.silences(retake, min_s=EDGE_MIN_S))
    head = next((s for s in fine if s["from_s"] <= 0.30), None)
    tail = next((s for s in reversed(fine) if s["to_s"] >= dur - 0.30), None)
    start = head["to_s"] if head else 0.0
    end = tail["from_s"] if tail else dur
    return round(start, 3), round(end, 3), inner


def plan(master: pathlib.Path, script: pathlib.Path, retake: pathlib.Path,
         segments: list[int]) -> dict:
    lo, hi = min(segments), max(segments)
    m = boundaries(master, script)
    n_breaks = len(m["asked_breaks"])
    if lo < 2 or hi > n_breaks:
        raise Refuse(
            f"segments {segments} cannot be spliced: this script has {n_breaks + 1} "
            f"segments and only ones with a break on BOTH sides can be patched. "
            f"Segment 1 and segment {n_breaks + 1} have a file edge on one side, and a "
            f"file edge is not a silence to hide a cut in.")

    # break index k (1-based) sits AFTER segment k. So the break before segment `lo` is
    # break lo-1, and the break after segment `hi` is break hi.
    before = next(x for x in m["matched"] if x["n"] == lo - 1)
    after = next(x for x in m["matched"] if x["n"] == hi)
    a_end = round(before["at_s"] + before["got_s"], 3)     # END of the break before
    c_start = round(after["at_s"], 3)                      # START of the break after

    b_start, b_end, b_inner = speech_span(retake)
    rp = qc.probe(retake)
    want_inner = hi - lo                                   # breaks INSIDE the patch
    if len(b_inner) != want_inner:
        raise Refuse(
            f"the retake should have {want_inner} break(s) between its segments and its "
            f"audio has {len(b_inner)}: "
            + ", ".join(f"{s['dur_s']:.2f}s@{s['from_s']:.1f}s" for s in b_inner)
            + ". A patch whose own breaks did not land is a patch that cannot be cut.")

    out_dur = a_end + (b_end - b_start) + (m["dur_s"] - c_start)
    return {
        "master": master.name, "retake": retake.name, "segments": segments,
        "a": {"from_s": 0.0, "to_s": a_end,
              "why": f"the master up to the END of break {lo - 1} "
                     f"({before['got_s']:.2f}s at {before['at_s']:.1f}s)"},
        "b": {"from_s": b_start, "to_s": b_end,
              "why": "the retake, first word to last; its head and tail stillness "
                     "trimmed so the breaks either side are not lengthened",
              "inner_breaks": b_inner},
        "c": {"from_s": c_start, "to_s": m["dur_s"],
              "why": f"the master from the START of break {hi} "
                     f"({after['got_s']:.2f}s at {after['at_s']:.1f}s) to the end"},
        "master_dur_s": m["dur_s"], "retake_dur_s": rp["dur_s"],
        "out_dur_s": round(out_dur, 2),
        "replaced_s": round(c_start - a_end, 2),
        "with_s": round(b_end - b_start, 2),
        "retake_probe": rp,
    }


def render(p: dict, master: pathlib.Path, retake: pathlib.Path,
           out: pathlib.Path) -> None:
    """Concatenate A + B + C. Re-encoded once, because the sources differ in GOP."""
    parts = [("a", master), ("b", retake), ("c", master)]
    tmp_dir = out.parent
    pieces = []
    for key, src in parts:
        seg = p[key]
        piece = tmp_dir / f".splice-{key}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-ss", f"{seg['from_s']:.3f}", "-to", f"{seg['to_s']:.3f}",
             "-i", str(src),
             "-c:v", "libx264", "-preset", "medium", "-crf", "16",
             "-pix_fmt", "yuv420p", "-r", "25",
             "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
             str(piece)], check=True, timeout=3600)
        pieces.append(piece)
    lst = tmp_dir / ".splice-list.txt"
    lst.write_text("".join(f"file '{p_.name}'\n" for p_ in pieces), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(out)],
                   check=True, timeout=3600, cwd=str(tmp_dir))
    for p_ in pieces:
        p_.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)


def joins_reach_the_screen(patched: pathlib.Path, splice: dict,
                           handle_s: float, min_idle_s: float) -> list[str]:
    """Does either splice join land in material the cut actually USES? [] means no.

    🔴 A JOIN THAT IS NOT IN THE CUT CANNOT JUMP, AND THAT IS BETTER THAN HIDING ONE.
    The interleave trims every clip inward by `handle_s` from its silence boundary, on
    the speaking clips and the idle clips alike. That leaves a ring of material at each
    end of every silence which goes into NEITHER — and a join placed at the outer edge
    of a break lands in that ring.

    ⚠️ AND THE MARGIN IS TENS OF MILLISECONDS, WHICH IS WHY THIS IS A GUARD AND NOT A
    MEASUREMENT. EP49's two joins clear the nearest used clip by 133ms and 99ms. Change
    the silence threshold, re-encode the master, or shorten the handle, and a join that
    was absent becomes a visible jump in the middle of a turn. Nothing would say so.
    """
    total = qc.probe(patched)["dur_s"]
    sil = [(s["from_s"], s["to_s"]) for s in qc.merge_silences(qc.silences(patched))]
    head, tail, internal = 0.0, total, []
    for s, e in sil:
        if s <= 0.25:
            head = max(head, e)
        elif e >= total - 0.25:
            tail = min(tail, s)
        else:
            internal.append((s, e))
    edges = [head] + [e for _, e in internal]
    outs = [s for s, _ in internal] + [tail]
    used = [(a + handle_s, b - handle_s) for a, b in zip(edges, outs)]
    used += [(a + handle_s, b - handle_s) for a, b in internal
             if (b - handle_s) - (a + handle_s) >= min_idle_s]

    a_end = splice["a"]["to_s"]
    joins = {"A": a_end,
             "B": round(a_end + (splice["b"]["to_s"] - splice["b"]["from_s"]), 3)}
    bad = []
    for name, t in joins.items():
        for lo, hi in used:
            if lo < t < hi:
                bad.append(
                    f"join {name} at {t:.3f}s is INSIDE a clip the cut uses "
                    f"({lo:.3f}-{hi:.3f}). The picture will jump mid-shot. Either the "
                    f"layout must hide it or the splice points must move.")
                break
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("master")
    ap.add_argument("script")
    ap.add_argument("retake")
    ap.add_argument("--segments", required=True)
    ap.add_argument("--out")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    segs = [int(x) for x in a.segments.split(",")]
    master, script, retake = (pathlib.Path(a.master), pathlib.Path(a.script),
                              pathlib.Path(a.retake))
    p = plan(master, script, retake, segs)

    print(f"splice segments {segs} of {p['master']} with {p['retake']}\n")
    for key in ("a", "b", "c"):
        s = p[key]
        print(f"  {key.upper()}  {s['from_s']:>8.3f}s -> {s['to_s']:>8.3f}s  "
              f"({s['to_s'] - s['from_s']:>7.2f}s)  {s['why']}")
    for s in p["b"]["inner_breaks"]:
        print(f"       the retake's own break: {s['dur_s']:.2f}s at {s['from_s']:.1f}s")
    print(f"\n  replacing {p['replaced_s']:.2f}s of the master with {p['with_s']:.2f}s "
          f"of retake")
    print(f"  {p['master_dur_s']:.2f}s -> {p['out_dur_s']:.2f}s")
    print(f"  retake: {p['retake_probe']['w']}x{p['retake_probe']['h']} "
          f"{p['retake_probe']['fps']}fps {p['retake_probe']['dur_s']}s")
    if a.json_out:
        pathlib.Path(a.json_out).write_text(
            json.dumps({k: v for k, v in p.items()}, indent=1), encoding="utf-8")
    if a.plan_only or not a.out:
        print("\n(plan only — nothing written)")
        return 0
    out = pathlib.Path(a.out)
    render(p, master, retake, out)
    got = qc.probe(out)
    print(f"\nWROTE {out} — {got['dur_s']:.2f}s {got['w']}x{got['h']} "
          f"{got['bytes']:,} bytes")
    if abs(got["dur_s"] - p["out_dur_s"]) > 1.0:
        print(f"  \U0001f534 expected {p['out_dur_s']:.2f}s and got "
              f"{got['dur_s']:.2f}s — the concat did not land as planned.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Refuse as e:
        print(f"HALT: {e}", file=sys.stderr)
        raise SystemExit(2)
