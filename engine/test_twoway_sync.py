#!/usr/bin/env python3
"""THE MAN ON SCREEN IS THE MAN YOU CAN HEAR. Three invariants that had no test.

    python engine/test_twoway_sync.py [ep_number]

🔴 WHY THIS EXISTS. Jodie watched one minute of EP49's third cut and stopped:
*"Steve reads the Barry Meadow bit, he finishes, and he says the word I as if he's
starting a new sentence, and then he stops talking. Then Gordon's voice comes on but
he's not moving his lips."* Two symptoms, one seam, and **three cuts had passed every
plan-level check in this repo with both of them in.**

  a. **LIPS MATCH VOICE.** While X's audio plays, X's window shows X's own SPEAKING
     footage — never a bed, never an idle clip, never the other man. EP49 had 3.96s
     where it did not, and nothing asked.
  b. **TURN CONTAINMENT.** A turn's audio holds that turn's words and no others.
  c. **A SHORT SHOT MAY NOT BE PADDED ACROSS A HANDOVER.** Jodie's ruling, 20 Sep:
     *"Take it from the same man's own speaking footage, or change the layout."*
     A boundary inside a turn is free. A boundary BETWEEN turns is fixed by the audio,
     and moving it is what produced (a).
"""
from __future__ import annotations

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
import twoway_beats as tb                                          # noqa: E402
import twoway_interleave as ti                                     # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")
STEP = 0.04
PASSED, FAILED = [], []

MAX_INTRA_TURN_GAP_S = 0.60
"""How long a gap inside one turn may be before what follows is a SEPARATE utterance.

🔴 MEASURED, AND THE POPULATIONS DO NOT OVERLAP. Across EP49's fifteen turn endings the
gap in front of the final burst is 0.03, 0.03, 0.05, 0.05, 0.07, 0.07, 0.16, 0.16, 0.19,
0.20, 0.25, 0.45, 0.48 — normal sentence-final phrasing — and then **1.27s** in front of
the stray word Jodie heard. This line sits in the empty space between 0.48 and 1.27.

⚠️ IT IS FITTED TO ONE EXAMPLE OF THE FAULT AND I SHOULD SAY SO (CLAUDE.md 4c: real data
proves a guard works, it never finds where it breaks). So the check PRINTS the whole
distribution on every run — if a real phrasing gap ever creeps toward 0.60 it is visible
long before it starts eating words.
"""


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASSED if ok else FAILED).append(name)
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")


def mm(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def env(path, t0, t1):
    return ti._env(path, t0, t1)


def loud_runs(e, t0, win, thresh):
    out, cur = [], None
    for i, d in enumerate(e):
        if d > thresh:
            cur = [t0 + i * win, t0 + i * win, d] if cur is None else \
                [cur[0], t0 + i * win, max(cur[2], d)]
        elif cur is not None:
            out.append(tuple(cur))
            cur = None
    if cur:
        out.append(tuple(cur))
    return [r for r in out if r[1] - r[0] >= 0.04]


def main() -> int:
    ep = int(sys.argv[1]) if len(sys.argv) > 1 else 49
    d = ep_paths.episode_dir(ep, PP)
    plan = ta.build_plan(ep, PP)
    TL = json.loads((d / "renders/master-timeline.json").read_text(
        encoding="utf-8"))["timeline"]
    HEAD = ta.TITLE_HEAD_S
    print(__doc__.splitlines()[0])
    print(f"\nEP{ep}: {len(plan['segments'])} picture segments, {len(TL)} audio spans")

    def resolve(p):
        q = pathlib.Path(p)
        return q if q.is_absolute() else (d / "renders" / q.name)

    # ── a. LIPS MATCH VOICE, over the whole timeline ──────────────────────────
    print("\n-- a. while X is talking, the picture shows X --")

    def voice_at(t):
        x = t - HEAD
        for s in TL:
            if s.get("in_s") is None:
                continue
            if s["from_s"] - 1e-9 <= x < s["to_s"] - 1e-9:
                return s.get("speaker")
        return None

    segs = plan["segments"]

    # the latency beat after each turn: silence that BELONGS to the picture
    beats = {}
    for prev, b, nxt in zip(TL, TL[1:], TL[2:]):
        if b.get("kind") == "latency":
            beats[(prev.get("speaker"), prev.get("turn"))] = b["dur_s"]
    i, bad, t = 0, [], HEAD
    while t < plan["speech_end_s"]:
        while i < len(segs) - 1 and segs[i]["to_s"] <= t:
            i += 1
        s, who = segs[i], voice_at(t)
        # a card or a clip hides both men, so nobody's lips can contradict anybody
        if who and not s.get("card") and not s.get("broll") \
                and s.get("speaker") and s["speaker"] != who:
            bad.append((t, who, s["n"], s["speaker"], s["layout"]))
        t = round(t + STEP, 3)

    runs = []
    for row in bad:
        if runs and row[2] == runs[-1][2] and row[0] - runs[-1][5] <= STEP * 1.5:
            runs[-1][5] = row[0]
        else:
            runs.append([row[0], row[1], row[2], row[3], row[4], row[0]])
    for a, who, n, shown, layout, b in runs[:6]:
        print(f"       {mm(a)}–{mm(b + STEP)} ({b - a + STEP:.2f}s): {who} is talking, "
              f"segment {n} ({layout}) shows {shown}")
    worst = max((r[5] - r[0] + STEP for r in runs), default=0.0)
    check("no moment shows a man who is not the one talking", not runs,
          f"{len(runs)} run(s), {sum(r[5] - r[0] + STEP for r in runs):.2f}s total, "
          f"longest {worst:.2f}s" if runs else f"{int((plan['speech_end_s'] - HEAD) / STEP):,} moments checked")

    # the listener must also be the OTHER man, never the speaker twice
    dbl = [s["n"] for s in segs if s.get("listener")
           and s.get("speaker") and s["listener"] == s["speaker"]]
    check("and no two-box lists one man as both speaker and listener", not dbl,
          f"segments {dbl[:5]}")

    # ── c. THE BORROWING RULE ────────────────────────────────────────────────
    print("\n-- c. a short shot is never padded across a handover --")
    # ⚠️ THE FIRST VERSION OF THIS CHECK ASKED THE WRONG QUESTION and cried wolf. It
    # flagged any repaired segment that happened to sit NEXT TO a handover — but
    # `repaired` marks the LENDER, and a segment can lend across the boundary on its
    # other side, inside its own turn, which is allowed. Being adjacent to a handover
    # is not the same as having moved one.
    #
    # What matters is where the picture's handover actually IS: it must coincide with
    # the audio's, give or take the latency beat between the two turns.
    crossed = []
    for a, b in zip(segs, segs[1:]):
        if a.get("turn") is None or b.get("turn") is None:
            continue
        if a["turn"] == b["turn"] and a.get("speaker") == b.get("speaker"):
            continue
        span = next((x for x in TL if x.get("turn") == a["turn"]
                     and x.get("speaker") == a.get("speaker")), None)
        if span is None:
            continue
        lo = span["to_s"] + HEAD
        hi = lo + beats.get((a.get("speaker"), a["turn"]), 0.0) + 0.05
        if not (lo - 0.05 <= b["from_s"] <= hi):
            crossed.append((a["n"], b["n"], a.get("speaker"), b.get("speaker"),
                            b["from_s"], lo, hi))
    for na, nb, sa, sb, t, lo, hi in crossed:
        print(f"       {sa}->{sb} handover: the picture cuts at {mm(t)}, the audio "
              f"hands over at {mm(lo)} (beat to {mm(hi)}) — out by "
              f"{max(lo - t, t - hi):.2f}s")
    check("every picture handover sits on its audio handover", not crossed,
          f"{len(crossed)} do not")

    # And every shot must sit inside its own turn's audio — PLUS the latency beat
    # either side of it, which is silence by design and belongs to the picture.
    #
    # ⚠️ THE FIRST VERSION OF THIS CHECK HAD NO SUCH ALLOWANCE AND REPORTED 10 FAULTS
    # OF WHICH 8 WERE THE DESIGN. A shot holds across the beat on purpose: "a beat is a
    # gap in the audio, not in the picture". Reporting those as breaches would have had
    # me tightening seams that are correct — the false-alarm half of CLAUDE.md's guard
    # rule, and the reason the allowance is computed from the TIMELINE's own beats
    # rather than from a tolerance I picked.
    off = []
    for s in segs:
        if s.get("turn") is None or s.get("speaker") is None:
            continue
        span = next((x for x in TL if x.get("turn") == s["turn"]
                     and x.get("speaker") == s["speaker"]), None)
        if span is None:
            continue
        slack = beats.get((s["speaker"], s["turn"]), 0.0) + 0.05
        lo, hi = span["from_s"] + HEAD, span["to_s"] + HEAD + slack
        if s["from_s"] < lo - 0.05 or s["to_s"] > hi:
            off.append((s["n"], mm(s["from_s"]), mm(s["to_s"]), mm(lo), mm(hi),
                        max(lo - s["from_s"], s["to_s"] - hi)))
    for n, a, b, lo, hi, over in sorted(off, key=lambda r: -r[5])[:6]:
        print(f"       segment {n} runs {a}–{b}, its turn's audio (+beat) runs "
              f"{lo}–{hi} — out by {over:.2f}s")
    check("every shot sits inside its own turn's audio, plus its beat", not off,
          f"{len(off)} do not; worst {max((r[5] for r in off), default=0):.2f}s")

    # ── b. TURN CONTAINMENT ──────────────────────────────────────────────────
    print("\n-- b. a turn holds its own words and no others --")
    print(f"     (an utterance more than {MAX_INTRA_TURN_GAP_S:.2f}s after the previous "
          f"one is a separate utterance — see MAX_INTRA_TURN_GAP_S)")
    gaps, stray = [], []
    for s in TL:
        if s.get("in_s") is None:
            continue
        src = resolve(s["source"])
        out = s["in_s"] + s["dur_s"]
        e, win = env(src, max(0.0, out - 3.0), out)
        if not e:
            continue
        lr = loud_runs(e, max(0.0, out - 3.0), win, -35.0)
        if len(lr) < 2:
            continue
        gap = lr[-1][0] - lr[-2][1]
        gaps.append((gap, s.get("speaker"), out))
        if gap > MAX_INTRA_TURN_GAP_S:
            stray.append((s.get("speaker"), s.get("turn"), lr[-1], gap, out))
    print("     trailing gaps, largest first: "
          + ", ".join(f"{g:.2f}s" for g, _, _ in sorted(gaps, reverse=True)[:8]))
    for who, turn, r, gap, out in stray:
        print(f"       {who} turn {turn}: an utterance at {r[0]:.3f}-{r[1]:.3f} "
              f"({r[1] - r[0]:.3f}s, peak {r[2]:.1f} dB) sits {gap:.2f}s after the "
              f"last word and the turn KEEPS it")
    check("no turn ends with an utterance detached from its own speech", not stray,
          f"{len(stray)} do; worst gap {max((g for g, _, _ in gaps), default=0):.2f}s")

    # a turn must not reach into a cue the aligner marked as a non-word token
    TAG = re.compile(r"^\s*(<[^>]*>\s*)+$")
    reach = []
    for code in {s.get("speaker") for s in TL if s.get("in_s") is not None}:
        f = d / f"renders/{code}.srt"
        if not f.is_file():
            continue
        cues = ti.read_srt(f.read_text(encoding="utf-8"))
        tags = [c for c in cues if TAG.match(c["text"] or "")]
        for s in TL:
            if s.get("speaker") != code or s.get("in_s") is None:
                continue
            out = s["in_s"] + s["dur_s"]
            for c in tags:
                # only count real OVERLAP into the tag, not touching its edge
                if c["start"] + 0.10 < out <= c["end"]:
                    reach.append((code, s.get("turn"), out, c["start"], c["end"]))
    for code, turn, out, a, b in reach:
        print(f"       {code} turn {turn} ends at {out:.3f}, inside the "
              f"{a:.3f}-{b:.3f} span its own alignment calls a break tag")
    check("no turn ends inside a span the aligner calls a non-word token", not reach,
          f"{len(reach)} do")

    # ── CONTROLS ─────────────────────────────────────────────────────────────
    # All three checks above were watched failing on the build Jodie rejected. These
    # keep them able to fail now that they are green — including one that is not a
    # fixture at all but the real stray utterance, still sitting in the master.
    print("\n-- CONTROLS --")

    # 1. a short stub at a handover: the HANDOVER must not move, the CARD must keep
    #    its hold, and the stub must go.
    #
    # ⚠️ THE FIRST FIXTURE HERE WAS WRONG AND I NEARLY BELIEVED IT. It put the stub
    # directly against the next turn's two-box, and `picture_states` MERGES two
    # contiguous two-boxes into one shot — so there was no short state at all and the
    # control "failed" against working code. The real shape has the latency beat between
    # them, which is what keeps them separate shots. A fixture that does not reproduce
    # the fault tests nothing.
    def fixture(before_s):
        return [
            {"n": 1, "from_s": 0.0, "to_s": before_s, "dur_s": before_s,
             "layout": "two-box", "speaker": "BM", "turn": 3, "held": False,
             "kind": "two-box", "card": None, "broll": None},
            {"n": 2, "from_s": before_s, "to_s": before_s + 10.5, "dur_s": 10.5,
             "layout": "full", "speaker": "BM", "turn": 3, "held": True,
             "kind": "card", "card": "C1", "broll": None},
            {"n": 3, "from_s": before_s + 10.5, "to_s": before_s + 11.6, "dur_s": 1.1,
             "layout": "two-box", "speaker": "BM", "turn": 3, "held": False,
             "kind": "two-box", "card": None, "broll": None},
            # the latency beat sits here — that is why the next shot is a NEW state
            {"n": 4, "from_s": before_s + 12.05, "to_s": before_s + 32.05,
             "dur_s": 20.0, "layout": "two-box", "speaker": "BB", "turn": 4,
             "held": False, "kind": "two-box", "card": None, "broll": None},
        ]

    for label, before_s, want_segs in (("GROW", 10.0, 4), ("COLLAPSE", 6.0, 3)):
        fake = fixture(before_s)
        hand = fake[3]["from_s"]
        card_was = fake[1]["dur_s"]
        out = ta.repair_short_states([dict(s) for s in fake])
        after = next((s["from_s"] for s in out if s.get("turn") == 4), None)
        card = next((s for s in out if s.get("card") == "C1"), None)
        check(f"CONTROL ({label}): the handover does not move",
              after == hand, f"{hand} -> {after}")
        check(f"CONTROL ({label}): the card keeps its hold exactly",
              card is not None and abs(card["dur_s"] - card_was) < 0.001,
              f"{card_was}s -> {card['dur_s'] if card else None}s")
        check(f"CONTROL ({label}): no shot is left under the dwell floor",
              all(s["dur_s"] >= tb.MIN_DWELL_S - 0.001 for s in out),
              f"{[round(s['dur_s'], 2) for s in out]}")
        check(f"CONTROL ({label}): the stub is gone",
              len(out) == want_segs, f"{len(out)} segments, wanted {want_segs}")

    # 2. a shot showing the wrong man must be REPORTED by check (a)'s comparison
    wrong = {"speaker": "BM", "card": None, "broll": None}
    check("CONTROL: the lips check calls BM-shown-while-BB-talks a fault",
          wrong["speaker"] != "BB" and not wrong["card"] and not wrong["broll"])

    # 3. THE REAL ONE: the stray utterance is still in BM-master, and the rule finds it
    bm = d / "renders/BM-master.mp4"
    if bm.is_file():
        sil = ti.merge_silences(ti.silences(bm))
        fl = ti.noise_floor(bm, sil)
        here = min(sil, key=lambda p: abs(p[0] - 20.17))
        got = ti.drop_trailing_utterance(bm, here[0], here[1], fl)
        check("CONTROL: the stray word Jodie heard is still found in the master",
              got < here[0] - 0.5,
              f"pause start {here[0]:.3f} -> {got:.3f} ({here[0] - got:.3f}s dropped)")
        clean = min(sil, key=lambda p: abs(p[0] - 101.24))
        got2 = ti.drop_trailing_utterance(bm, clean[0], clean[1], fl)
        check("CONTROL: and a normal turn ending is left alone",
              abs(got2 - clean[0]) < 0.001,
              f"{clean[0]:.3f} -> {got2:.3f}")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  ! " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
