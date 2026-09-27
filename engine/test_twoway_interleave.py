#!/usr/bin/env python3
"""test_twoway_interleave.py — interleave, proved before a single render exists.

    python engine/test_twoway_interleave.py

🔴 THE POINT OF DOING IT THIS WAY. Build spec §5 calls `interleave` "the riskiest step,
done on real material, not last". Real material costs two HeyGen renders and Steve's
voice, neither of which exists yet — so the material here is SYNTHETIC and built to the
real shape: tone bursts of EP49's actual turn lengths, separated by 4s silences, behind
the ~6.4s silent head Avatar IV leaves (measured 6.35 / 6.36 / 6.39s on EP11-13).

What that proves and what it does not: it proves the DETECTION, the arithmetic, the
merge, the idle pool and the halt. It cannot prove that HeyGen honours the SSML break —
only listening to the pair test can, and that is build-order step 2½.

⚠️ AND THE CONTROL COMES FIRST (CLAUDE.md 4b): the mismatch case is built and watched to
FAIL before the good case is believed. A silence detector that found nothing and a
silence detector that is switched off produce the identical output — nothing.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import twoway_beats as tb                                        # noqa: E402
import twoway_interleave as il                                   # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR",
                                 str(pathlib.Path("G:/My Drive") / "PP Videos")))
TURNS = PP / "PP-EP49-Fighting-a-Complex-Game-Part-1/docs/turns.json"
HEAD_S, PAUSE_S, TAIL_S = 6.4, 4.0, 3.0
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"  <- {why}" if not cond and why else ""))


def fake_master(out: pathlib.Path, turn_durs: list[float], pause_s=PAUSE_S) -> None:
    """A presenter master that is the right SHAPE: head, turn, pause, turn, ... tail.

    A tone rather than speech, because what is being tested is where the SILENCE is.
    Freq varies per turn so a mis-cut is audible if anyone ever plays it.
    """
    parts = [f"anullsrc=r=48000:cl=mono:d={HEAD_S}"]
    for i, d in enumerate(turn_durs):
        parts.append(f"sine=frequency={220 + 40 * i}:r=48000:d={d:.3f}")
        if i < len(turn_durs) - 1:
            parts.append(f"anullsrc=r=48000:cl=mono:d={pause_s}")
    parts.append(f"anullsrc=r=48000:cl=mono:d={TAIL_S}")
    args = [il._ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"]
    for p in parts:
        args += ["-f", "lavfi", "-i", p]
    args += ["-filter_complex",
             "".join(f"[{i}:a]" for i in range(len(parts)))
             + f"concat=n={len(parts)}:v=0:a=1[a]",
             "-map", "[a]", "-c:a", "aac", "-b:a", "128k", str(out)]
    subprocess.run(args, check=True, timeout=600)


def fake_srt(turn_texts: list[str], turn_durs: list[float]) -> str:
    """A per-presenter SRT laid out exactly where the tones are, one cue per sentence."""
    rows, n, t = [], 0, HEAD_S
    for text, dur in zip(turn_texts, turn_durs):
        sents = tb.sentences(text) or [text]
        words = [max(1, len(s.split())) for s in sents]
        total = sum(words)
        at = t
        for s, w in zip(sents, words):
            d = dur * w / total
            n += 1
            rows.append(f"{n}\n{il._fmt(at)} --> {il._fmt(at + d)}\n{s}\n")
            at += d
        t += dur + PAUSE_S
    return "\n".join(rows) + "\n"


def main() -> int:
    if not TURNS.is_file():
        check("EP49's turns.json is on this machine", False, str(TURNS))
        print(f"\ninterleave: {len(PASS)} passed, {len(FAIL)} failed")
        return 1
    if not shutil.which("ffmpeg") and not il._ffmpeg():
        check("ffmpeg is on this machine", False, "no ffmpeg")
        print(f"\ninterleave: {len(PASS)} passed, {len(FAIL)} failed")
        return 1

    turns = json.loads(TURNS.read_text(encoding="utf-8"))["turns"]
    dialogue = [t for t in turns if t["speaker"] != "NARR"]
    by = {c: [t for t in dialogue if t["speaker"] == c] for c in ("BB", "BM")}
    durs = {c: [round(t["words"] / tb.WORDS_PER_S, 2) for t in ts]
            for c, ts in by.items()}

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pp-interleave-"))
    try:
        print("-- THE SYNTHETIC MASTERS, BUILT TO EP49's REAL TURN LENGTHS --")
        masters = {}
        for c in ("BB", "BM"):
            p = tmp / f"{c}-master.m4a"
            fake_master(p, durs[c])
            masters[c] = str(p)
            want = HEAD_S + sum(durs[c]) + PAUSE_S * (len(durs[c]) - 1) + TAIL_S
            got = il.duration(p)
            check(f"  {c}: {len(durs[c])} turns, {got:.1f}s built "
                  f"(wanted {want:.1f}s)", abs(got - want) < 0.6, f"{got:.2f}")

        print("\n-- 🔴 THE CONTROL FIRST: A MISMATCH MUST HALT --")
        bad = tmp / "BB-short.m4a"
        fake_master(bad, durs["BB"][:-1])          # one turn fewer than turns.json says
        try:
            il.turn_spans(bad, len(durs["BB"]))
            check("  a render with one turn missing HALTS", False, "it did not raise")
        except il.Mismatch as e:
            check("  a render with one turn missing HALTS", True)
            check("  and the halt names BOTH numbers, so it can be acted on",
                  str(len(durs["BB"]) - 1) in str(e) and "I measured" in str(e),
                  f"{str(e)[:120]}")
        glued = tmp / "BB-glued.m4a"
        fake_master(glued, durs["BB"], pause_s=0.4)   # breaks present but far too short
        try:
            il.turn_spans(glued, len(durs["BB"]))
            check("  pauses too SHORT to be turn boundaries also HALT", False,
                  "it did not raise")
        except il.Mismatch:
            check("  pauses too SHORT to be turn boundaries also HALT", True)

        print("\n-- DETECTION ON THE GOOD MASTERS --")
        spans, pauses = {}, {}
        for c in ("BB", "BM"):
            sp, pa, head = il.turn_spans(masters[c], len(durs[c]))
            spans[c], pauses[c] = sp, pa
            check(f"  {c}: {len(durs[c])} turns -> {len(pa)} internal silences",
                  len(pa) == len(durs[c]) - 1, f"{len(pa)}")
            check(f"  {c}: the lead-in is MEASURED at {head:.2f}s, not assumed",
                  abs(head - HEAD_S) < 0.4, f"{head}")
            worst = max(abs((b - a) - d) for (a, b), d in zip(sp, durs[c]))
            check(f"  {c}: every turn span matches its scripted length "
                  f"(worst {worst:.2f}s)", worst < 0.5)

        print("\n-- THE TIMELINE, THE MERGE AND THE POOL --")
        srts = {c: fake_srt([t["text"] for t in by[c]], durs[c]) for c in by}
        res = il.run(turns, masters, srts, tmp, write=False)
        tl = res["timeline"]
        speech = [s for s in tl if s.get("kind") != "latency"]
        beats = [s for s in tl if s.get("kind") == "latency"]
        check(f"  {len(speech)} speech segments, one per dialogue turn",
              len(speech) == len(dialogue), f"{len(speech)} vs {len(dialogue)}")
        check("  in turns.json order, alternating as the article does",
              [s["turn"] for s in speech] == [t["n"] for t in dialogue])
        check(f"  {len(beats)} latency beats — one between every pair",
              len(beats) == len(dialogue) - 1)
        check(f"  every beat is 0.3-0.5s (build spec §5 says do not tighten it)",
              all(0.30 <= s["dur_s"] <= 0.50 for s in beats),
              f"{sorted({s['dur_s'] for s in beats})}")
        check("  and they are VARIED — identical gaps are the tell",
              len({s["dur_s"] for s in beats}) > 1)
        check(f"  ~{il.AUDIO_OVERLAP_S}s of the next voice carried under every join "
              f"but the last",
              all(s["audio_overlap_s"] == il.AUDIO_OVERLAP_S for s in speech[:-1])
              and speech[-1]["audio_overlap_s"] == 0.0)
        # 🔴 THE CONSERVATION LAW. Every per-segment check can pass while time goes
        # missing — that is exactly how 54 seconds vanished out of the layout plan.
        want = round(sum(s["dur_s"] for s in speech)
                     + sum(s["dur_s"] for s in beats), 2)
        check("  total duration == the parts plus the beats, exactly",
              abs(res["total_s"] - want) < 0.01 and abs(tl[-1]["to_s"] - want) < 0.01,
              f"{res['total_s']} vs {want}, timeline ends {tl[-1]['to_s']}")
        check("  the timeline is contiguous: no gap and no overlap",
              all(abs(a["to_s"] - b["from_s"]) < 0.002 for a, b in zip(tl, tl[1:])))

        cues = il.read_srt(res["srt"])
        check(f"  the merged SRT carries {len(cues)} cues, every one speaker-tagged",
              bool(cues) and all(c["text"].startswith(("[BB]", "[BM]")) for c in cues))
        check("  its cues are in time order and inside the master's length",
              all(a["start"] <= b["start"] for a, b in zip(cues, cues[1:]))
              and cues[-1]["end"] <= want + 0.05,
              f"{cues[-1]['end']:.1f} vs {want:.1f}")
        first = next(c for c in cues)
        check("  and they are RETIMED onto the master, not left on the render clock",
              first["start"] < HEAD_S, f"{first['start']:.2f}s")

        idle = res["idle"]
        check(f"  the idle pool banks {len(idle)} clips from the pauses",
              len(idle) == sum(len(p) for p in pauses.values()), f"{len(idle)}")
        check(f"  every one is at least {il.MIN_IDLE_S}s",
              all(c["dur_s"] >= il.MIN_IDLE_S for c in idle),
              f"{min((c['dur_s'] for c in idle), default=0)}")
        check("  named renders/idle/BB-01.mp4 and so on, per build spec §5",
              any(c["file"] == "renders/idle/BB-01.mp4" for c in idle)
              and any(c["file"] == "renders/idle/BM-01.mp4" for c in idle))
        check("  and each says which master and which seconds it came from",
              all(c["source"] and c["out_s"] > c["in_s"] for c in idle))

        print("\n-- SNAPPING THE LAYOUT PLAN TO REAL SENTENCE ENDS --")
        ends = il.sentence_ends(cues)
        check("  the merged SRT yields sentence ends to snap to", len(ends) > 10,
              f"{len(ends)}")
        plan = [{"from_s": 0.0, "to_s": 40.0}, {"from_s": 40.0, "to_s": 95.0},
                {"from_s": 95.0, "to_s": 150.0}]
        snapped = il.snap_plan(plan, cues)
        moved = [s.get("snap_moved_s") for s in snapped[1:]]
        check("  every boundary but the first is moved onto a sentence end",
              all(m is not None for m in moved)
              and all(any(abs(s["snapped_from_s"] - e) < 0.002 for e in ends)
                      for s in snapped[1:]),
              f"{moved}")
        check("  and none is moved further than a sentence is long",
              all(abs(m) < 25.0 for m in moved), f"{moved}")
        check("  the snapped plan stays contiguous",
              all(abs(a["snapped_to_s"] - b["snapped_from_s"]) < 0.002
                  for a, b in zip(snapped[1:], snapped[2:])))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\ninterleave: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
