#!/usr/bin/env python3
"""twoway_verify_cut.py — VOICE, LIPS AND WORDS, checked on the finished mp4.

    python engine/twoway_verify_cut.py <ep_number> <episode.mp4> [--samples N]

🔴 WHY THIS EXISTS. Three cuts of EP49 passed every plan-level check in this repo and
were wrong on screen. Jodie, 20 Sep 2026: *"An end-to-end check that runs on the FINISHED
FILE, not on the plan. Three cuts have now passed every plan-level check and been wrong
on screen."* A plan-level check can only say the plan is self-consistent; it never looks
at a pixel, so it cannot say the renderer put the right footage in the panel.

── IT ASKS "WHERE DID THIS COME FROM", NOT "HOW SIMILAR IS THIS" ─────────────────────
🔴 THE FIRST VERSION SCORED AN ABSOLUTE CORRELATION AND WAS WORTHLESS. A full-frame shot
matched its own master at **0.996** and a frame from thirty seconds away at **0.996** —
the same man, the same chair, the same lighting — so the number could not tell the two
apart, and it reported twelve faults on a cut that was fine. The audio half was worse: it
compared the FINISHED mix, which carries music and `loudnorm`, against the raw master,
and got correlations between -0.35 and +0.29 on audio that is provably correct.

**So nothing here is judged against a threshold I chose.** Each moment is compared with
the master at SEVEN offsets — -30, -5, -1, 0, +1, +5, +30 seconds — and the only thing
asserted is that **zero wins**. If the panel really holds that man's master at that
instant, no other instant of the same man can beat it; if the panel is holding a
listening bed, zero has no reason to win at all. A relative test needs no calibration
and cannot be fooled by two frames being generally alike.

📌 And the VOICE is compared as an ENVELOPE, for the same reason: the finished mix is
not the master's waveform — it has been loudness-normalised and has music under it — but
the shape of the speech survives both, and the argmax over offsets is what identifies it.
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

import ep_paths                                                    # noqa: E402
import twoway_assemble as ta                                       # noqa: E402
import twoway_composite as tc                                      # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")
SR = 16000
OFFSETS = (-30.0, -5.0, -1.0, 0.0, 1.0, 5.0, 30.0)
"""The candidates. Zero must win. ±1s is the sharpest — a second of the same man mid
sentence is the hardest thing to beat, and a bed has no reason to prefer any of them."""


def _run(cmd, timeout=900):
    return subprocess.run(cmd, capture_output=True, timeout=timeout).stdout


def panel_from_cut(ep, t, rect, w=240):
    import numpy as np
    x, y, cw, chh = rect
    out = _run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(ep),
                "-frames:v", "1", "-vf",
                f"crop={cw}:{chh}:{x}:{y},scale={w}:-2,format=gray",
                "-f", "rawvideo", "-pix_fmt", "gray", "-"])
    return np.frombuffer(out, np.uint8).astype(np.float32)


def panel_from_master(src, t, rect, dy=0.0, w=240):
    """The master put through the SAME scale+crop the composite uses, so the two are
    comparable. The grading is not applied — correlation is invariant to it."""
    import numpy as np
    _x, _y, cw, chh = rect
    out = _run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(src),
                "-frames:v", "1", "-vf",
                f"scale=-2:{chh},crop={cw}:{chh}:(iw-{cw})/2:(ih-{chh})/2+{dy:.1f},"
                f"scale={w}:-2,format=gray",
                "-f", "rawvideo", "-pix_fmt", "gray", "-"])
    return np.frombuffer(out, np.uint8).astype(np.float32)


def env_of(path, t0, t1, win=0.02):
    import numpy as np
    out = _run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t0):.4f}",
                "-t", f"{t1 - t0:.4f}", "-i", str(path), "-vn",
                "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    a = np.frombuffer(out, np.int16).astype(np.float32)
    n = int(win * SR)
    if a.size < n * 4:
        return np.zeros(0, np.float32)
    w = a[:a.size // n * n].reshape(-1, n)
    return np.sqrt((w ** 2).mean(axis=1))


def corr(a, b):
    import numpy as np
    n = min(a.size, b.size)
    if n < 16:
        return -2.0
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    den = float(np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
    return float(np.dot(a, b) / den)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("episode")
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args()

    pp = pathlib.Path(a.pp)
    d = ep_paths.episode_dir(a.ep_number, pp)
    ep = pathlib.Path(a.episode)
    plan = ta.build_plan(a.ep_number, pp)
    layout = tc.load_layout()
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    TL = json.loads((d / "renders/master-timeline.json").read_text(
        encoding="utf-8"))["timeline"]
    HEAD = ta.TITLE_HEAD_S
    side_of = {c: s["side"] for c, s in epj["speakers"].items()}
    reader = {c: s["reader"].upper() for c, s in epj["speakers"].items()}

    cues = []
    srt = ep.with_suffix(".srt")
    if srt.is_file():
        for b in re.split(r"\r?\n\r?\n", srt.read_text(encoding="utf-8").strip()):
            L = b.split("\n")
            m = re.match(r"(\d\d):(\d\d):(\d\d)[,.](\d\d\d) --> "
                         r"(\d\d):(\d\d):(\d\d)[,.](\d\d\d)", L[1]) if len(L) > 2 \
                else None
            if m:
                g = [int(x) for x in m.groups()]
                cues.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000,
                             g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000,
                             "\n".join(L[2:])))

    masters, offs = {}, {}
    for s in TL:
        if s.get("in_s") is None or s["speaker"] in masters:
            continue
        q = pathlib.Path(s["source"])
        masters[s["speaker"]] = q if q.is_absolute() else (d / "renders" / q.name)
    for c, m in masters.items():
        try:
            offs[c] = tc.measure_eye_line(m) or 0.0
        except Exception:                                          # noqa: BLE001
            offs[c] = 0.0

    shots = [s for s in plan["segments"]
             if not s.get("card") and not s.get("broll") and s.get("speaker")
             and s.get("turn") is not None and s["dur_s"] > 3.0]
    step = max(1, len(shots) // a.samples)
    picked = shots[::step][:a.samples]
    print(f"{ep.name}\n{len(picked)} moments sampled from {len(shots)} face shots")
    print(f"each compared with its master at {OFFSETS} seconds — ZERO MUST WIN\n")

    def span_at(t):
        x = t - HEAD
        return next((s for s in TL if s.get("in_s") is not None
                     and s["from_s"] - 1e-9 <= x < s["to_s"] - 1e-9), None)

    print(f"{'at':>9} {'who':4} {'layout':8} {'lips':>26} {'voice':>22}  words")
    bad_l, bad_a, bad_w, rows = [], [], [], []
    for s in picked:
        t = round(s["from_s"] + s["dur_s"] / 2, 3)
        sp = span_at(t)
        if sp is None:
            continue
        who = sp["speaker"]
        src_t = sp["in_s"] + (t - HEAD - sp["from_s"])
        rect = layout["panels"][side_of[who]]["rect"] if s["layout"] == "two-box" \
            else layout["single"]["rect"]

        got = panel_from_cut(ep, t, rect)
        lips = {o: corr(got, panel_from_master(masters[who], src_t + o, rect,
                                               offs.get(who, 0.0)))
                for o in OFFSETS}
        gv = env_of(ep, t, t + 1.2)
        voice = {o: corr(gv, env_of(masters[who], src_t + o, src_t + o + 1.2))
                 for o in OFFSETS}
        lw = max(lips, key=lips.get)
        vw = max(voice, key=voice.get)
        txt = next((x[2] for x in cues if x[0] <= t < x[1]), "")
        named = (reader[who] in txt.upper()) if txt else None
        rows.append((t, who, lw, vw, named, lips, voice))
        if lw != 0.0:
            bad_l.append((t, who, lw, lips[0.0], lips[lw]))
        if vw != 0.0:
            bad_a.append((t, who, vw, voice[0.0], voice[vw]))
        if named is False:
            bad_w.append((t, who))
        print(f"{t:9.2f} {who:4} {s['layout']:8} "
              f"{('WINS at %+.0fs' % lw) if lw else 'zero wins':>16}"
              f" {lips[0.0]:8.3f} "
              f"{('WINS at %+.0fs' % vw) if vw else 'zero wins':>14}"
              f" {voice[0.0]:6.3f}  "
              f"{'ok' if named else ('-' if named is None else 'WRONG')}")

    faults = []
    if bad_l:
        faults.append(
            f"{len(bad_l)} moment(s) match a DIFFERENT instant of that man better than "
            f"the one the plan says — a bed or an idle clip in the panel looks exactly "
            f"like this: "
            + ", ".join(f"{t:.1f}s {w} (best {o:+.0f}s, {c1:.2f} vs {c0:.2f})"
                        for t, w, o, c0, c1 in bad_l[:4]))
    if bad_a:
        faults.append(
            f"{len(bad_a)} moment(s) carry audio from a different instant: "
            + ", ".join(f"{t:.1f}s {w} (best {o:+.0f}s)" for t, w, o, _, _ in bad_a[:4]))
    if bad_w:
        faults.append(f"{len(bad_w)} moment(s) name the wrong man in the SRT")

    zl = sum(1 for r in rows if r[2] == 0.0)
    zv = sum(1 for r in rows if r[3] == 0.0)
    print(f"\nlips  : {zl}/{len(rows)} moments show the master the plan names")
    print(f"voice : {zv}/{len(rows)} moments carry that master's audio")
    print(f"words : {sum(1 for r in rows if r[4])}/{len(rows)} name the right man")
    if not faults:
        print("\n\u2705 at every sampled moment the finished file holds the right man's "
              "own footage, his own voice, and his name in the subtitle")
    else:
        print(f"\n{len(faults)} fault(s)")
    for f in faults:
        print("  ! " + f)
    return 1 if faults else 0


if __name__ == "__main__":
    raise SystemExit(main())
