#!/usr/bin/env python3
"""THE AUDIO IS ONE CONTINUOUS BED. NO PICTURE EVENT MAY TAKE A SAMPLE OF IT.

    python engine/test_twoway_audio_integrity.py [ep_number]

🔴 WHY THIS EXISTS. EP49's first cut clipped the last consonant off every turn. Jodie,
20 Sep 2026: *"Gordon says the term GOLD MEDALS, but before he even says the S sound at
the end of MEDALS, he's cut off — and this is happening each section."* She was exactly
right, including about it being every section.

**The cause was `HANDLE_S`, applied inward.** A turn's span is the SPEECH between two
silences, and the code did `a + HANDLE_S, b - HANDLE_S` — moving both edges INTO the
speech and discarding 150ms at each end of every turn. The constant's own docstring says
it is *"enough that a consonant is not clipped"*, and it was subtracted in the direction
that guarantees one. The same expression is CORRECT in `idle_pool`, which cuts out of a
SILENCE and must keep away from the speech either side: one arithmetic, two opposite
meanings, which is CLAUDE.md §2b.

⚠️ AND NOTE WHAT A DURATION CHECK WOULD HAVE SAID: nothing. The assembly reproduces the
timeline faithfully; it is the TIMELINE that had already thrown the samples away. So the
first check here does not ask "does the render match the plan" — that is a consistency
check, and consistency with a plan that is wrong is worth nothing. It asks the only
question that matters: **WHAT WAS DISCARDED, AND WAS IT SILENT?**
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import ep_paths                                                    # noqa: E402
import twoway_interleave as ti                                     # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")
SRF = 48000           # full rate, for the sample-equality check: no resampling
SR = 16000            # plenty for energy; a fricative is broadband and loud enough here
WIN = 0.010

MARGIN_DB = 6.0
"""How far over its master's floor a discarded strip has to peak before it is a WORD.

🔴 NOT A FUDGE, AND THE NUMBERS ARE WHY. The real faults this check found on EP49 sat
**+8 to +57 dB over the floor** — the "s" of *gold medals* at -45.9 against a -75.7
floor, Steve's clipped tails at -43.4 and -49.1 against -57.4, the worst at -22.5.
After the fix the loudest thing still being discarded anywhere is **+0.9 dB**, which is
the room tone of the pause it sits in. There is an empty 7 dB gap between the two
populations and this line is drawn in the middle of it, not against the survivor.

⚠️ Judged at floor + 0 the check fires on air, and **a check that fires on air is the
one somebody switches off** (CLAUDE.md 4b) — which would cost far more than the 0.9 dB
it is buying. Every margin is PRINTED on every run, so if the residue ever starts
climbing toward 6 it is visible long before it trips.
"""
PASSED, FAILED = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASSED if ok else FAILED).append(name)
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")


def pcm(src, t0: float, t1: float, sr: int = SR):
    import numpy as np
    if t1 <= t0:
        return np.zeros(0, np.float32)
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}",
                        "-t", f"{t1 - t0:.4f}", "-i", str(src), "-vn",
                        "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                       capture_output=True, timeout=900)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0


def peak_db(a) -> float:
    """The LOUDEST 10ms in a window. Peak, not mean — a mean over 250ms of which 150ms
    is a sibilant and 100ms is digital silence reports the silence."""
    import numpy as np
    n = int(WIN * SR)
    if a.size < n:
        return -180.0
    w = a[:a.size // n * n].reshape(-1, n)
    rms = np.sqrt((w ** 2).mean(axis=1))
    return float(20 * np.log10(max(float(rms.max()), 1e-9)))


def silence_floor(src) -> float:
    """The master's own noise floor — **`twoway_interleave`'s definition, not a copy.**

    🔴 THIS FUNCTION USED TO HAVE ITS OWN VERSION, AND IT CRIED WOLF WITHIN THE HOUR.
    BM-master contains true digital-ZERO samples, so a raw percentile returns -168 dB
    and every breath in the episode reads as "a voice". The guard reported six faults of
    which four were -78 to -87 dB — air. **A check that shares an idea with the code and
    keeps its own copy of it is the drift this repo is named for (§2), and a check that
    fires on air is the one somebody switches off (4b).** It calls the shipped function.
    """
    return ti.noise_floor(src, ti.merge_silences(ti.silences(src)))


def main() -> int:
    import numpy as np
    ep = int(sys.argv[1]) if len(sys.argv) > 1 else 49
    d = ep_paths.episode_dir(ep, PP)
    tlj = json.loads((d / "renders/master-timeline.json").read_text(encoding="utf-8"))
    TL = tlj["timeline"]
    spans = [s for s in TL if s.get("in_s") is not None]
    print(__doc__.splitlines()[0])
    print(f"\nEP{ep}: {len(spans)} spans, HANDLE_S = {ti.HANDLE_S}")

    def resolve(p):
        q = pathlib.Path(p)
        return q if q.is_absolute() else (d / "renders" / q.name)

    floors = {}
    for s in spans:
        src = resolve(s["source"])
        if src not in floors:
            floors[src] = silence_floor(src)
            print(f"  {src.name}: silence floor {floors[src]:+.1f} dB (derived)")

    # ── 1. WHAT WAS DISCARDED AT EACH EDGE, AND WAS IT SILENT? ────────────────
    print("\n-- 1. nothing discarded at a turn edge may be speech --")
    print(f"     a strip is judged against its master's floor + {MARGIN_DB:.0f} dB; "
          f"every margin is printed so the line is visible, not buried")
    # 🔴 ADJACENCY IS THE QUESTION, NOT LOUDNESS ANYWHERE NEARBY. A clipped word is
    # sound that runs RIGHT UP TO THE CUT: a phoneme lasts 50–150ms, so if a boundary
    # lands inside one there is sound within 50ms of it. The "s" of *gold medals* peaks
    # +33.5 dB over the floor in the 50ms straight after its cut.
    #
    # ⚠️ Whereas 130ms before one of Gordon's turns there is a 70ms IN-BREATH at -58 dB
    # with fifty milliseconds of DIGITAL SILENCE between it and his first phoneme. Over
    # a 250ms window that reads +17.7 dB and looks identical to a clipped word; touching
    # the cut, it reads +1.0. **It is not a word, nothing is clipped, and a guard that
    # cannot tell those two apart would have had me lengthening every turn to chase a
    # breath.** The wider window is still measured and PRINTED — so a detached sound is
    # visible — and only the adjacent one decides.
    NEAR, LOOK = 0.05, 0.25
    outs, ins, far = [], [], []
    for s in spans:
        src, fl = resolve(s["source"]), floors[resolve(s["source"])]
        out = s["in_s"] + s["dur_s"]
        outs.append((peak_db(pcm(src, out, out + NEAR)) - fl, s.get("speaker"), out))
        far.append((peak_db(pcm(src, out, out + LOOK)) - fl, "END", out))
        if s["in_s"] > LOOK:
            ins.append((peak_db(pcm(src, s["in_s"] - NEAR, s["in_s"])) - fl,
                        s.get("speaker"), s["in_s"]))
            far.append((peak_db(pcm(src, s["in_s"] - LOOK, s["in_s"])) - fl,
                        "START", s["in_s"]))
    for label, rows in (("END", outs), ("START", ins)):
        top = sorted(rows, reverse=True)[:4]
        print(f"     touching the cut, turn {label}: "
              + ", ".join(f"{m:+.1f} dB @{t:.1f}s ({w})" for m, w, t in top))
    det = [r for r in sorted(far, reverse=True)[:3] if r[0] > MARGIN_DB]
    if det:
        print("     (detached sound further out, not clipped, for information: "
              + ", ".join(f"{m:+.1f} dB {k} @{t:.1f}s" for m, k, t in det) + ")")
    bad_out = [r for r in outs if r[0] > MARGIN_DB]
    bad_in = [r for r in ins if r[0] > MARGIN_DB]
    check("no turn END throws away audible sound", not bad_out,
          f"{len(bad_out)} of {len(outs)} do; worst {max(outs)[0]:+.1f} dB over floor "
          f"at {max(outs)[2]:.1f}s" if bad_out else
          f"worst is {max(outs)[0]:+.1f} dB over floor — room tone")
    check("no turn START throws away audible sound", not bad_in,
          f"{len(bad_in)} of {len(ins)} do; worst {max(ins)[0]:+.1f} dB" if bad_in else
          f"worst is {max(ins)[0]:+.1f} dB over floor — room tone")

    # ── 2. AND THE ASSEMBLY REPRODUCES THE TIMELINE, SAMPLE FOR SAMPLE ────────
    #    Jodie asked for this explicitly. It may well PASS while check 1 fails —
    #    the render is faithful to a timeline that had already dropped the words —
    #    and that is the point worth seeing, not a formality.
    print("\n-- 2. the assembled speech is the timeline, in order, nothing removed --")
    import twoway_render as tr
    aud = tr.speech_path(d / "renders/_pieces", TL)   # ONE definition of the path
    if not aud.is_file():
        check("the assembled speech track exists", False, str(aud))
    else:
        want = round(sum(s["dur_s"] for s in TL), 3)
        got = len(pcm(aud, 0.0, 10 ** 6)) / SR
        check("total duration equals the timeline's", abs(got - want) < 0.05,
              f"{got:.3f}s vs {want:.3f}s ({got - want:+.3f}s)")
        # 🔴 SAMPLE-FOR-SAMPLE EQUALITY, AGAINST MASTERS DECODED WHOLE. Jodie asked for
        # exactly this — *"must contain every sample of the interleaved audio, in order,
        # with nothing removed"* — and it is literally testable, so it is tested
        # literally.
        #
        # ⚠️ THIS REPLACED A CROSS-CORRELATION CHECK THAT WAS WORSE THAN USELESS: IT
        # SHARED ITS SEEK WITH THE CODE IT WAS JUDGING. It read each master with the
        # same `-ss` the builder used, so when that seek landed on the wrong sample both
        # sides moved together and it reported a comfortable "+0.00ms" — on ten spans
        # that were NOT the master's samples at all. It then reported the corrected
        # build as the broken one, and I nearly reverted a working fix on its say-so.
        # **CLAUDE.md: a check that shares its source with the thing it checks is not a
        # check.** Decoding the master from the top uses no seek at all, so it cannot
        # inherit the bug.
        #
        # 📌 And correlation was the wrong instrument regardless: on speech a lag of one
        # pitch period (~8.2ms for a male voice at 122 Hz) scores nearly as well as
        # zero, so the "offsets" it reported changed whenever the window did.
        def whole(src):
            r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn",
                                "-ac", "1", "-ar", str(SRF), "-f", "s16le", "-"],
                               capture_output=True, timeout=1800)
            return np.frombuffer(r.stdout, np.int16)

        A = whole(aud)
        mas = {c: whole(resolve(next(s["source"] for s in spans
                                     if s.get("speaker") == c)))
               for c in {s.get("speaker") for s in spans}}
        diffs = []
        for s in spans:
            n = int(round(s["to_s"] * SRF) - round(s["from_s"] * SRF))
            a0, m0 = int(round(s["from_s"] * SRF)), int(round(s["in_s"] * SRF))
            a, m = A[a0:a0 + n], mas[s["speaker"]][m0:m0 + n]
            k = min(a.size, m.size)
            rms = (float(np.sqrt(((a[:k].astype(np.int32)
                                   - m[:k].astype(np.int32)).astype(float) ** 2).mean()))
                   if k else 1e9)
            diffs.append((rms, s.get("speaker"), s["from_s"]))
        same = sum(1 for r, _, _ in diffs if r < 1.0)
        w = max(diffs)
        print(f"     {same}/{len(diffs)} spans are the master's samples EXACTLY "
              f"(worst rms difference {w[0]:.1f} of 32768 full scale)")
        check("every span is the master's own samples, in order", same == len(diffs),
              f"{len(diffs) - same} differ; worst rms {w[0]:.1f} at {w[2]}s ({w[1]})")

        # no click at a join: a boundary must not be a step in the waveform
        steps = []
        for s in TL[1:]:
            t = s["from_s"]
            a = pcm(aud, max(0.0, t - 0.02), t + 0.02, sr=48000)
            if a.size < 100:
                continue
            h = a.size // 2
            jump = abs(float(a[h]) - float(a[h - 1]))
            local = float(np.abs(a).max()) or 1e-9
            if jump > 0.5 * local and local > 0.01:
                steps.append((t, jump, local))
        check("no discontinuity at any segment boundary", not steps,
              f"{len(steps)} boundaries step" if steps else
              f"{len(TL) - 1} boundaries checked")

    # ── 3. THE CONTROL — prove the check can fail once the build is fixed ─────
    # ── 3a. THE CONTROL THAT MATTERS: the boundary that actually shipped ──────
    #    Not a synthetic fixture. 86.738s in BB-master is where `HANDLE_S` put the end
    #    of Gordon's turn 4 in the cut Jodie watched, and the "s" of *gold medals* runs
    #    86.748–86.898 on the far side of it. If this check ever stops firing there, it
    #    has stopped being able to see the fault it was written for.
    print("\n-- 3a. CONTROL: the cut that shipped, at 86.738s in BB-master --")
    bb = resolve(next(s["source"] for s in spans if s.get("speaker") == "BB"))
    flb = floors[bb]
    shipped = peak_db(pcm(bb, 86.738, 86.738 + NEAR)) - flb
    check("CONTROL: the shipped boundary IS reported as clipping a word",
          shipped > MARGIN_DB, f"{shipped:+.1f} dB over floor")
    now = next((s["in_s"] + s["dur_s"] for s in spans if s.get("speaker") == "BB"
                and abs(s["in_s"] + s["dur_s"] - 86.9) < 0.4), None)
    check("and the boundary is no longer there", now is not None and now > 86.908,
          f"now {now}s, the s ends 86.908s" if now else "span not found")

    print("\n-- 3b. CONTROL: a deliberately mid-word cut must be REPORTED --")
    src = resolve(spans[0]["source"])
    fl = floors[src]
    # take a point that is unambiguously inside speech: the middle of the first span
    inside = spans[0]["in_s"] + spans[0]["dur_s"] / 2
    lvl = peak_db(pcm(src, inside, inside + LOOK))
    check("CONTROL: a cut in mid-sentence reads as speech", lvl > fl,
          f"{lvl:.1f} dB against a {fl:.1f} dB floor")
    # and a point inside a real SSML break must read as air
    sil = ti.merge_silences(ti.silences(src))
    if sil:
        a, b = sil[0]
        mid = (a + b) / 2
        q = peak_db(pcm(src, mid, mid + LOOK))
        check("CONTROL: the middle of a real pause reads as air", q <= fl,
              f"{q:.1f} dB against a {fl:.1f} dB floor")
        check("CONTROL: and the two are far apart", lvl - q > 20,
              f"{lvl - q:.1f} dB between speech and air")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  ! " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
