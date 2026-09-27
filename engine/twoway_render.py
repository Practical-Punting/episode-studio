#!/usr/bin/env python3
"""twoway_render.py — turn a checked assembly plan into the episode.

    python engine/twoway_render.py <ep_number> [--pp DIR] [--out FILE]
                                   [--from S --to S] [--proof]

`twoway_assemble` decides WHAT is on screen and when, and refuses to hand over a plan
that breaks a rule. This renders it.

🔴 SEGMENT BY SEGMENT, THEN CONCAT — NOT ONE GIANT FILTER GRAPH. This machine has 8 GB
and shares it with another production line. A single graph over thirteen minutes with
two 1080p video inputs, fifteen card overlays and seven clips is the shape that pages,
and a job that pages on 8 GB does not run slowly, it dies mid-write. Per-segment pieces
are bounded, restartable, and each one can be looked at on its own when something is
wrong with it.

📌 AND IT MAKES A PROOF CHEAP. `--from/--to` renders any window of the episode with the
identical code path, so a minute of the real cut can be judged before committing an
hour to all of it. Every two-way proof before this one was a different code path from
the real build, which is how "it looked right in the proof" stops meaning anything.

── THE AUDIO IS NOT ASSEMBLED HERE ───────────────────────────────────────────────────
It comes from the interleaved timeline in one pass — each man's own master at his own
in/out, the latency beats as silence — and the music rides the standing envelope with
the speech as its sidechain key. That recipe is IMPORTED from `assemble_episode`, never
re-typed: one home for the thing that decides how loud the bed is under a voice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import ep_paths                                                   # noqa: E402
import twoway_assemble as ta                                      # noqa: E402
import twoway_composite as tc                                     # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")
MUSIC = PP / "PP-EP01-The-Trifecta-Mistake/music" / \
    "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"
FPS = 25
W, H = 1920, 1080
AUDIO_RECIPE = "2026-09-20/pcm-exact-samples-no-input-seek"
"""🔴 THE CACHE KEY MUST COVER THE RECIPE, NOT ONLY THE INPUTS.

The speech track is cached under a hash of the timeline — and when the timeline stayed
the same while the way it is CUT changed (AAC pieces to PCM; input seeking to trimming
by sample index), the key did not move and the old track would have been served as if
nothing had happened. That is the third cache in one day whose name did not describe
what was inside it, and the first where the inputs alone were not enough.

**Bump this string whenever `build_audio` changes what it produces.** A date and a
phrase, so a stale file is identifiable from its name rather than by elimination.
"""

SR = 48000
"""The audio's own clock. Named beside FPS because the two must telescope the same way:
`round(t*FPS)` for the picture, `round(t*SR)` for the sound, both off the plan's clock
and never off a piece's own duration. Getting one right and the other wrong is what put
EP49's picture 0.95s ahead of its words."""

PICTURE_RECIPE = "2026-09-27/cards-rendered-without-their-own-logo"
"""🔴 THE PIECE CACHE MUST COVER THE RECIPE, NOT ONLY THE FRAME COUNT.

`seg-NNN-<frames>f.mp4` keys on how LONG a piece is, which was enough while the only
thing that ever changed was its timing. It is not enough now: applying the presenter
grade to the full-frame path changes what is INSIDE a piece without changing its
length by a single frame, so every one of the 63 cached pieces would have been served
back unchanged and the fix would have looked like it did nothing.

That is the fourth cache in this build whose name did not describe its contents
(`_picture.mp4`, `_body.mp4`, `_speech.m4a`, and now this). **Bump this string whenever
`render_segment` changes what it draws.**"""

"""📌 The dissolve is a PLAN decision, not a render one — `twoway_assemble.DISSOLVE_FRAMES`
owns the number and the reasons, and marks the incoming segment. This module executes
`seg["dissolve_in_frames"]` and decides nothing."""


class Unrenderable(Exception):
    pass


def _ff() -> str:
    import pp_paths
    return pp_paths.ffmpeg() or "ffmpeg"


def run(cmd: list, timeout: int = 3600) -> None:
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode:
        raise Unrenderable(f"ffmpeg failed:\n{(r.stderr or '')[-1500:]}")


# ─────────────────────────────────────────────────── one segment's picture ──

def source_time(tlseg: dict, t: float) -> float:
    """Where in a man's own master the finished clock `t` is looking."""
    return tlseg["in_s"] + (t - tlseg["from_s"])


def timeline_at(tl: list[dict], t: float) -> dict | None:
    for s in tl:
        if s.get("kind") == "latency":
            continue
        if s["from_s"] - 0.001 <= t < s["to_s"] + 0.001:
            return s
    return None


def listener_source(idle: list[dict], beds: dict, code: str, want_s: float,
                    used: dict) -> tuple[str, float, float]:
    """Footage of a man who is NOT speaking, long enough to cover `want_s`.

    🔴 THE IDLE POOL FIRST, THE BEDS AFTER. The pauses came out of his OWN render
    minutes ago, in the same light, at the same size — nothing matches a master like
    the master. The beds are a separate render and are what the pool cannot cover.

    ⚠️ AND NOTHING IS REUSED WITHIN ~90s. A listener doing the identical head-tilt twice
    inside a minute and a half is the tell that the footage is looped, which is the one
    thing the format may not look like.
    """
    cands = [c for c in idle if c["speaker"] == code
             and c["dur_s"] >= want_s
             and used.get(c["file"], -999) < used["_t"] - 90.0]
    if cands:
        c = min(cands, key=lambda x: x["dur_s"])
        used[c["file"]] = used["_t"]
        return c["source"], c["in_s"], c["in_s"] + want_s
    for name, path in beds.get(code, []):
        d = probe_dur(path)
        if d >= want_s and used.get(str(path), -999) < used["_t"] - 90.0:
            used[str(path)] = used["_t"]
            return str(path), 0.0, want_s
    # Nothing long enough: take the longest bed and say so. A bed is never looped, so
    # the caller reports a shortfall rather than this function inventing a loop.
    if beds.get(code):
        name, path = max(beds[code], key=lambda p: probe_dur(p[1]))
        return str(path), 0.0, min(want_s, probe_dur(path))
    raise Unrenderable(f"no listening footage at all for {code}")


_DUR: dict[str, float] = {}


def probe_dur(path) -> float:
    k = str(path)
    if k not in _DUR:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=nw=1:nk=1", k],
                           capture_output=True, text=True, timeout=120)
        try:
            _DUR[k] = float((r.stdout or "0").strip())
        except ValueError:
            _DUR[k] = 0.0
    return _DUR[k]


def frames_between(t0: float, t1: float) -> int:
    """How many frames a piece running t0→t1 owns. TELESCOPING, on purpose.

    🔴 A PIECE'S LENGTH IS NOT ITS OWN BUSINESS. Every piece used to be cut to its own
    `dur_s`, and `trim=duration` rounds UP to a whole frame — so all 64 pieces rounded
    the same way and the errors ADDED. EP49's body came out +0.680s over 64 pieces
    (mean +0.27 frames each, no single piece more than one frame out), and the final
    `-t` hid it by trimming the tail: the file was the right LENGTH with the picture
    drifting up to 0.68s late against its own audio by the end.

    ⚠️ THIS IS CLAUDE.md FAULT 1b — the two clocks — inside the renderer. The audio is
    one continuous track and the picture is sixty-four pieces; if each piece measures
    itself, the two clocks separate a little at every join and nothing downstream can
    see it, because each individual piece is correct to within a frame.

    Taking both edges from the SHARED clock makes the sum telescope: piece i ends on
    exactly the frame piece i+1 starts on, so the total is `round(end*FPS) -
    round(start*FPS)` however many pieces there are. Drift is not reduced here, it is
    made arithmetically impossible — which is the difference between a fix and a
    tolerance. (§2b: one definition, not a correction applied per reader.)
    """
    return int(round(t1 * FPS) - round(t0 * FPS))


def piece_path(seg: dict, work: pathlib.Path) -> pathlib.Path:
    """Where segment `seg` lives on disk — ONE definition, used by the renderer and by
    the finisher, so they cannot disagree about which file is this segment's.

    The frame count is IN THE NAME. A piece cut to a different length is a different
    file, so re-timing the plan can never be served a stale piece from cache — the
    same reason `_picture-<key>.mp4` carries its key.

    🔴 AND SO IS THE RECIPE. The frame count answers "is this piece the right LENGTH";
    it says nothing about what is drawn on it, and the grade fix changes exactly that
    and nothing else. See `PICTURE_RECIPE`."""
    rk = hashlib.md5(PICTURE_RECIPE.encode()).hexdigest()[:6]
    return (work / f"seg-{seg['n']:03d}-"
                   f"{frames_between(seg['from_s'], seg['to_s'])}f-{rk}.mp4")


def final_piece_path(seg: dict, work: pathlib.Path) -> pathlib.Path:
    """The file the CONCAT uses — the dissolved variant where the plan asked for one.

    A second name rather than an in-place rewrite, so the raw piece survives: a
    dissolve can be re-cut, looked at beside the original, or dropped by changing the
    plan, without re-rendering the composite underneath it."""
    p = piece_path(seg, work)
    n = seg.get("dissolve_in_frames")
    return p.with_name(p.stem + f"-x{n}.mp4") if n else p


def apply_dissolve(before: pathlib.Path, piece: pathlib.Path, frames: int,
                   out: pathlib.Path) -> None:
    """Soften the join into `piece` by cross-fading out of `before`'s last frame.

    🔴 THE FRAME COUNT DOES NOT MOVE. The dissolve is painted INTO the incoming piece's
    first `frames` frames — the outgoing piece is not touched and the incoming one
    keeps its exact length — so the telescoping `frames_between` guarantees is
    untouched. A dissolve that needed handles would mean re-cutting both sides, and
    re-cutting is how the +0.680s drift got in.

    ⚠️ IT IS A FREEZE-DISSOLVE AND THAT IS SAID PLAINLY. The outgoing layer is
    `before`'s LAST FRAME, held for 240ms while its alpha runs to zero — not `before`
    continuing to move, because the pieces are already rendered and the listener
    footage a two-box piece used is not recorded anywhere it could be continued from.
    The alternative — replaying `before`'s last six frames — puts a 240ms BACKWARD step
    into the layer the eye is still tracking, which is worse than a hold. What it is
    not is a guess: 240ms of held picture inside a fade is what a dip looks like.
    """
    ff = _ff()
    n = int(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=nb_read_packets", "-of", "default=nw=1:nk=1",
         str(piece)], capture_output=True, text=True, timeout=900).stdout.strip() or 0)
    if n < frames:
        raise Unrenderable(
            f"{piece.name} is {n} frames and the dissolve is {frames} — a piece "
            f"shorter than its own transition is a piece that is all transition.")
    last = out.with_suffix(".last.png")
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-sseof", "-0.08",
         "-i", str(before), "-frames:v", "1", "-update", "1", str(last)])
    d = frames / FPS
    run([ff, "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(piece), "-loop", "1", "-t", f"{d:.3f}", "-i", str(last),
         "-filter_complex",
         f"[1:v]fps={FPS},scale={W}:{H},format=rgba,"
         f"fade=t=out:st=0:d={d:.3f}:alpha=1[ov];\n"
         f"[0:v][ov]overlay=0:0:enable='lt(t,{d:.3f})':eof_action=pass,"
         f"format=yuv420p[v]",
         "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-frames:v", str(n), "-pix_fmt", "yuv420p", str(out)])
    last.unlink(missing_ok=True)
    got = int(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=nb_read_packets", "-of", "default=nw=1:nk=1",
         str(out)], capture_output=True, text=True, timeout=900).stdout.strip() or 0)
    if got != n:
        raise Unrenderable(
            f"the dissolve changed {piece.name} from {n} frames to {got}. The picture "
            f"clock only telescopes while every piece delivers its exact count.")


def render_segment(seg: dict, ctx: dict, out: pathlib.Path) -> None:
    """One picture state, as its own mp4. Silent — the audio is built separately."""
    nf = frames_between(seg["from_s"], seg["to_s"])
    if nf < 1:
        raise Unrenderable(f"segment {seg['n']} is {seg['dur_s']}s — under one frame")
    # Read two frames MORE than we keep, then cut with `-frames:v`. The source must
    # never run out before the count is met, or the exactness is lost again silently.
    dur = round((nf + 2) / FPS, 3)
    keep = ["-frames:v", str(nf)]
    layout, side_of = ctx["layout"], ctx["side_of"]
    tl = ctx["timeline"]
    ff = _ff()

    if seg.get("card"):
        clip = ctx["cards"][seg["card"]]
        # A card ANIMATES and then HOLDS. `tpad` clones the last frame for the rest of
        # the hold, which is the design: the assembled card is what the viewer takes
        # away (pp-motion-graphics), and the hold is its reading time.
        run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", clip,
             "-vf", f"tpad=stop_mode=clone:stop_duration={dur},"
                    f"trim=duration={dur},setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             *keep, "-pix_fmt", "yuv420p", str(out)])
        return

    if seg.get("broll"):
        clip = ctx["broll"][seg["broll"]]
        # The `tpad` is a backstop, not a policy: the plan clamps a slot to its clip
        # rather than ask for footage that is not there, so this can only ever clone
        # the LAST TWO FRAMES, and only when a clip lands within a frame of its slot.
        run([ff, "-y", "-hide_banner", "-loglevel", "error", "-t", f"{dur}",
             "-i", clip,
             "-vf", f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H},tpad=stop_mode=clone:stop_duration=0.2,"
                    f"setpts=PTS-STARTPTS",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             *keep, "-pix_fmt", "yuv420p", str(out)])
        return

    # a man speaking: find where in his own master this moment lives
    tlseg = timeline_at(tl, seg["from_s"] - ctx["head_s"])
    if tlseg is None:
        raise Unrenderable(f"segment {seg['n']} at {seg['from_s']}s maps to no turn")
    a = source_time(tlseg, seg["from_s"] - ctx["head_s"])
    speaker_src = tlseg["source"]

    if seg["layout"] != "two-box":
        # 🔴 THE GRADE BELONGS TO THE MAN, NOT TO THE TWO-BOX. This line used to have no
        # `eq` on it at all, so every full-frame shot in the episode went out raw while
        # the two-box was graded — and both presenters stepped brightness at every
        # layout change. See `twoway_composite.grade_of` for the measurements.
        grade = tc.grade_filter(layout, seg["speaker"])
        run([ff, "-y", "-hide_banner", "-loglevel", "error",
             "-ss", f"{a:.3f}", "-t", f"{dur}", "-i", speaker_src,
             "-vf", f"fps={FPS},scale={W}:{H},{grade},"
                    f"tpad=stop_mode=clone:stop_duration=0.2,setpts=PTS-STARTPTS",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             *keep, "-pix_fmt", "yuv420p", str(out)])
        return

    # THE TWO-BOX. The graph comes from twoway_composite so the design stays data.
    sp = seg["speaker"]
    ls = seg.get("listener") or [c for c in side_of if c != sp][0]
    ctx["used"]["_t"] = seg["from_s"]
    lsrc, lin, _lout = listener_source(ctx["idle"], ctx["beds"], ls, dur, ctx["used"])
    graph = tc.composite_graph(layout, side_of,
                               [{"speaker": sp, "listener": ls}], ctx["offsets"])
    graph = graph.split("\n# push")[0]
    graph = (f"[0:v]fps={FPS},setpts=PTS-STARTPTS[{sp.lower()}0];\n"
             f"[1:v]fps={FPS},setpts=PTS-STARTPTS[{ls.lower()}0];\n" + graph)
    run([ff, "-y", "-hide_banner", "-loglevel", "error",
         "-ss", f"{a:.3f}", "-t", f"{dur}", "-i", speaker_src,
         "-ss", f"{lin:.3f}", "-t", f"{dur}", "-i", lsrc,
         "-filter_complex", graph, "-map", "[key0]",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         *keep, "-pix_fmt", "yuv420p", str(out)])


# ──────────────────────────────────────────────────────────── the finish ──

def speech_path(work: pathlib.Path, tl: list[dict]) -> pathlib.Path:
    """Where the assembled speech lives — ONE definition, so the renderer and anything
    checking it cannot disagree about which file is the current one. Keyed on the
    timeline AND on `AUDIO_RECIPE`, because both change what is inside it."""
    k = hashlib.md5((json.dumps(tl, sort_keys=True) + AUDIO_RECIPE).encode())
    return work / f"_speech-{k.hexdigest()[:10]}.wav"


def build_audio(tl: list[dict], plan: dict, work: pathlib.Path,
                out: pathlib.Path) -> None:
    """The conversation's audio, from each man's own master, with the beats as silence.

    🔴 EACH MAN'S OWN MASTER AT HIS OWN IN/OUT. There is no mixing to do between the two
    — only one of them is speaking at a time — so the audio is a concatenation, and the
    only things added are the latency beats. Re-recording, re-timing or stretching
    anything here would put the words out of step with the SRT that everything
    downstream hangs off.

    🔴 THE PIECES ARE PCM AND THE SAMPLE COUNTS COME OFF THE SHARED CLOCK. Both halves
    of that sentence are scars.

    **The pieces used to be AAC, concatenated with `-c copy`.** A lossy codec cannot be
    cut at an arbitrary sample: each piece was padded out to a whole 1024-sample frame,
    and every join re-inserted the encoder's priming delay. Measured on EP49: the 33
    pieces came to **+0.248s** between them and the concatenated track to **+0.952s** —
    the extra 0.704s being ~21ms of silence pushed in at each of the 33 joins. None of
    it is audible as a gap, and all of it is cumulative, so **the picture — built exactly
    to the timeline — ran up to 0.95s AHEAD of the words by the end of the episode.**
    Shot changes landing a fraction of a second before the line is what "lots of
    jumping" is.

    ⚠️ IT IS THE MORNING'S FRAME DRIFT AGAIN, IN THE OTHER MEDIUM AND BIGGER. Same
    shape: many pieces, each rounded the same way, errors adding, and a total that looks
    right because the last step trims to length. So the same cure — `round(to×SR) −
    round(from×SR)` off the shared clock, which telescopes — and PCM, so that asking for
    an exact number of samples actually gets you one.
    """
    ff = _ff()
    lst, pieces = work / "_audio.txt", []
    for i, s in enumerate(tl):
        n = int(round(s["to_s"] * SR) - round(s["from_s"] * SR))
        rk = hashlib.md5(AUDIO_RECIPE.encode()).hexdigest()[:6]
        p = work / f"aud-{i:03d}-{n}s-{rk}.wav"
        if not p.is_file():
            af = (f"aformat=sample_fmts=s16:sample_rates={SR}:"
                  f"channel_layouts=stereo,atrim=end_sample={n},asetpts=N/SR/TB")
            if s.get("kind") == "latency":
                run([ff, "-y", "-hide_banner", "-loglevel", "error",
                     "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=stereo",
                     "-t", f"{(n + 4096) / SR:.4f}", "-af", af,
                     "-c:a", "pcm_s16le", str(p)])
            else:
                # 🔴 NO `-ss`. THE SAMPLES ARE ASKED FOR BY INDEX. Input seeking on
                # these masters is not sample-accurate: measured across EP49's 17
                # spans, fifteen landed at +0.00ms and two at **-8.17ms and +23.00ms**
                # — the latter almost exactly one 1024-sample AAC frame. Correlation
                # was 1.000 at that offset, so the CONTENT was right and its PLACE was
                # not, which no duration check can see. Decoding from the top and
                # trimming by sample index costs a few seconds a piece and cannot miss.
                n0 = int(round(s["in_s"] * SR))
                run([ff, "-y", "-hide_banner", "-loglevel", "error",
                     "-i", s["source"], "-vn",
                     "-af", f"aresample={SR},apad=pad_len=4096,"
                            f"atrim=start_sample={n0}:end_sample={n0 + n},"
                            f"asetpts=N/SR/TB,"
                            f"aformat=sample_fmts=s16:sample_rates={SR}:"
                            f"channel_layouts=stereo",
                     "-c:a", "pcm_s16le", str(p)])
        pieces.append(p)
    lst.write_text("".join(f"file '{p.name}'\n" for p in pieces), encoding="utf-8")
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c:a", "pcm_s16le", str(out)], timeout=1800)
    got = int(round(probe_dur(out) * SR))
    want = int(round(tl[-1]["to_s"] * SR))
    if abs(got - want) > SR // 100:
        raise Unrenderable(
            f"the assembled speech is {got:,} samples and the timeline is {want:,} "
            f"({(got - want) / SR:+.3f}s). The audio and the picture are on different "
            f"clocks, which is the fault Jodie heard on 20 Sep as words cut off and "
            f"the picture jumping early.")


def finish(plan: dict, d: pathlib.Path, work: pathlib.Path,
           out: pathlib.Path) -> None:
    """Picture pieces + title + end card + warranty + logo + the ducked music mix."""
    ff = _ff()
    segs = plan["segments"]
    pieces = [final_piece_path(s, work) for s in segs]
    missing = [p.name for p in pieces if not p.is_file()]
    if missing:
        raise Unrenderable(f"{len(missing)} picture piece(s) not rendered: "
                           f"{missing[:5]}")

    # 1 — the dialogue picture, end to end
    bkey = hashlib.md5("|".join(p.name for p in pieces).encode()).hexdigest()[:10]
    body = work / f"_body-{bkey}.mp4"
    lst = work / f"_body-{bkey}.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in pieces), encoding="utf-8")
    if not body.is_file():
        run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
             "-safe", "0", "-i", str(lst), "-c", "copy", str(body)], timeout=3600)

    # 2 — the audio
    #
    # 🔴 KEYED ON THE TIMELINE, for the third time in one day and the same reason each
    # time: `_speech.m4a` was a fixed name, so the corrected timeline would have been
    # handed yesterday's audio and the fix would have looked like it did nothing.
    tlj = json.loads((d / "renders/master-timeline.json").read_text(encoding="utf-8"))
    aud = speech_path(work, tlj["timeline"])
    if not aud.is_file():
        build_audio(tlj["timeline"], plan, work, aud)

    # 3 — head and tail as their own pieces, so the concat stays a copy
    # Every tail piece is cut by FRAME COUNT off the same clock as the body — see
    # `frames_between`. And each one's NAME carries its count, so a piece rendered to
    # a different length can never be served from cache as if it were this one.
    hn = frames_between(0.0, ta.TITLE_HEAD_S)
    head = work / f"_head-{hn}f.mp4"
    if not head.is_file():
        run([ff, "-y", "-hide_banner", "-loglevel", "error",
             "-i", plan["head"]["title_card"],
             "-vf", f"tpad=stop_mode=clone:stop_duration={ta.TITLE_HEAD_S + 0.2},"
                    f"setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             "-frames:v", str(hn), "-pix_fmt", "yuv420p", str(head)])
    # 🔴 THE SETTLE NEEDS A PICTURE, AND THE FIRST BUILD GAVE IT NONE.
    #
    # PP-STANDARDS asks for ~3s between the last word and the tail — "he never talks
    # right to the end; the end card + music breathe". The PLAN had those three seconds
    # (speech ends 844.0s, end card at 847.0s) and the CONCAT did not: head + body +
    # end card + warranty came to 853.5s against a planned 856.5s, so the end card
    # arrived three seconds early and the last three seconds were BLACK.
    #
    # ⚠️ AND THE TWO FAULTS THE QC REPORTED WERE ONE FAULT. "57 frames short of the
    # header" and "blank frame at 854.8s" are the same missing three seconds seen from
    # two ends. A gap in a concat does not announce itself — it silently shifts
    # everything after it and pads the difference with nothing.
    #
    # What breathes is the last shot: Gordon, held, while the music swells.
    #
    # 🔴 IT NOW RUNS TO THE WARRANTY, NOT TO THE END CARD. The end card is no longer a
    # piece in this concat — §END SEQUENCE rule 2 puts it up ON THE E-BOOK BEAT, while
    # Gordon is still talking, so it is an OVERLAY that starts inside the outro and
    # holds until the warranty takes over. What is left between the last word and the
    # warranty is exactly the settle, and the end card is drawn over it.
    sn = frames_between(plan["speech_end_s"], plan["warranty"]["from_s"])
    settle = work / f"_settle-{sn}f.mp4"
    if sn > 0 and not settle.is_file():
        run([ff, "-y", "-hide_banner", "-loglevel", "error",
             "-sseof", "-0.08", "-i", str(body),
             "-vf", f"tpad=stop_mode=clone:stop_duration={(sn + 2) / FPS:.3f},"
                    f"setpts=PTS-STARTPTS,fps={FPS}",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             "-frames:v", str(sn), "-pix_fmt", "yuv420p", str(settle)])

    tail_parts = [settle] if sn > 0 else []
    wp = plan["warranty"]
    wn = frames_between(wp["from_s"], plan["total_s"])
    wa = work / f"_warranty-{wn}f.mp4"
    if not wa.is_file():
        run([ff, "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(d / "overlay/clips/warranty-slide.mp4"),
             "-vf", f"tpad=stop_mode=clone:stop_duration={(wn + 2) / FPS:.3f},"
                    f"setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
             "-frames:v", str(wn), "-pix_fmt", "yuv420p", str(wa)])
    tail_parts.append(wa)

    # 4 — one silent picture, then the logo over the DIALOGUE only
    #
    # 🔴 THE CACHE IS KEYED ON ITS INPUTS, NOT ON A FIXED NAME. `_picture.mp4` was a
    # constant, so when the piece list changed — a settle piece added — the `if not
    # whole.is_file()` guard happily served the OLD assembly and the fix appeared to
    # do nothing. A cache that cannot tell its inputs apart is a way to ship yesterday's
    # render with today's confidence.
    parts = [head, body] + tail_parts
    key = hashlib.md5("|".join(f"{p.name}:{p.stat().st_size}"
                               for p in parts).encode()).hexdigest()[:10]
    whole = work / f"_picture-{key}.mp4"
    wl = work / f"_whole-{key}.txt"
    wl.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    if not whole.is_file():
        run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
             "-safe", "0", "-i", str(wl), "-c", "copy", str(whole)], timeout=3600)
    assert_picture_reaches(whole, plan["total_s"])

    # 🔴 THE STANDING CORNER LOGO — the channel's, not the cards'. See `corner_logo`.
    #
    # ⚠️ THIS LINE USED TO READ THE CARDS' CSS AND DRAW 214x65. That made the corner mark
    # exactly HALF the linear size of the one forty-two published episodes wear, and it
    # came from reading "the motion graphics logo is the correct one" as "make the
    # corner logo a copy of a card's". A card's logo is furniture on a card; the corner
    # mark is its own standing element and PP-STANDARDS calls it PROMINENT.
    #
    # `card_logo_geometry` is kept and still answers a real question — where the CARDS
    # agree the logo goes, halting if they disagree — it is simply not the question the
    # corner is asking.
    lgeo = corner_logo(json.loads((d / "docs/episode.json").read_text(encoding="utf-8")))
    logo = pathlib.Path(lgeo["src"])
    lw, lh = lgeo["w"], lgeo["h"]
    lx, ly = lgeo["x"], lgeo["y"]
    cgeo = card_logo_geometry(d, plan)
    print(f"  corner logo {lw}x{lh} at ({lx},{ly}) — {logo.name} at its own size, "
          f"margin {lgeo['margin']}", flush=True)
    print(f"    (the cards carry their own {cgeo['w']}x{cgeo['h']} at "
          f"({cgeo['x']},{cgeo['y']}) — a different, smaller mark, by design)",
          flush=True)
    # 🔴 THE LOGO IS FRAME FURNITURE AND IT BELONGS TO THE EPISODE, NOT TO A PANEL — it
    # sits over the picture from the first word to the last and comes off for the end
    # card and the warranty slide, both of which carry their own.
    #
    # ⚠️ IT COMES OFF WHEN THE TAIL ARRIVES, NOT WHEN THE DIALOGUE STOPS. This used to
    # be `TITLE_HEAD_S + sum(segs)`, which was the same instant until the settle existed.
    # With three seconds of held picture between them it would have popped the logo off
    # mid-freeze — the picture stops moving AND the logo vanishes, three seconds before
    # anything explains why. The tail's own start is the boundary that MEANS something.
    #
    # 🔴 AND THE TAIL NOW STARTS WITH THE END CARD, MID-OUTRO, WHILE GORDON IS STILL ON
    # SCREEN — so the logo goes when the card is FULLY in, not when it begins to fade
    # in. Cutting it at the fade's start would take the logo off a picture the viewer
    # can still see through the card for three tenths of a second.
    ecp = plan.get("end_card")
    body_end = (round(ecp["from_s"] + ecp.get("fade_s", 0.3), 3) if ecp
                else plan["warranty"]["from_s"])
    total = plan["total_s"]
    mus_env = music_envelope(plan)

    # 🔴 THE "READING …" CHIPS. Generated since 16 Sep and never drawn until now — the
    # renderer had no reference to them at all, so three cuts shipped without the one
    # graphic that says who these two men are (build spec A7, the on-screen half of the
    # honesty rule). Jodie: *"that's disappeared. I really liked that."*
    #
    # ⚠️ THEY BELONG TO THE TWO-BOX, so they are on screen for the FIRST two-box run
    # inside the design's window and not a moment more. The window is the first 60s of
    # dialogue, but in that minute EP49 goes open → two-box → card → two-box, and
    # showing them whenever a panel exists would put them up, take them away for the
    # card, and bring them back — a flicker nobody designed. One appearance, when both
    # men are first on screen together, which is what the chip is FOR.
    ch = twoway_chips_window(plan, d)
    chips_who = next((s["speaker"] for s in plan["segments"]
                      if ch and s["layout"] == "two-box"
                      and s["from_s"] <= ch[0] < s["to_s"]), None)
    chips_png = d / f"overlay/export/twoway-chips-{chips_who}.png"
    if ch and not chips_png.is_file():
        raise Unrenderable(
            f"the two-box needs the 'reading ...' chips and {chips_png.name} is not "
            f"there. Run `python engine/twoway_chips.py <ep> {chips_who}` first — the "
            f"speaker is an argument because the orange rule belongs to whoever is "
            f"TALKING while they are up. It is a HALT and not a shrug because a silent "
            f"skip is exactly how they went missing from three cuts: build spec A7 "
            f"makes them the on-screen half of the honesty rule, and nothing noticed "
            f"they had never been drawn.")
    chips_fc = ""
    if ch:
        c0, c1 = ch
        fade = (layout_chips_move_ms(d) or 260) / 1000.0
        chips_fc = (f"[4:v]format=rgba,fade=t=in:st={c0:.2f}:d={fade:.2f}:alpha=1,"
                    f"fade=t=out:st={c1 - fade:.2f}:d={fade:.2f}:alpha=1[ch];\n")
        print(f"  chips on screen {c0:.2f}-{c1:.2f}s "
              f"({c1 - c0:.2f}s, fade {fade:.2f}s)", flush=True)

    # 🔴 THE THREE STANDING GRAPHICS. A furniture beat that owes a picture gets it here.
    #
    # They are the same three `assemble_episode` has drawn for forty-two episodes — the
    # early e-book card over the companion-guide mention, the like-and-subscribe chip
    # over the midroll ask, and the end card on the e-book beat in the outro — and this
    # renderer drew none of them. Jodie saw all three: *"there's an actual motion
    # graphic with the picture of the ebook… That did not come up"*, *"there's normally
    # a motion graphic when he does the please like and subscribe"*, *"the ebook motion
    # graphic turns up after Gordon finishes talking completely."*
    #
    # ⚠️ EVERY ONE OF THE THIRTEEN PLACED CARDS SAT INSIDE THE CONVERSATION, AND EVERY
    # FURNITURE BEAT WAS GORDON WITH NOTHING OVER HIM. That is the shape of the bug:
    # the renderer knew how to put a graphic on a card segment and had no idea that
    # furniture carries graphics too.
    #
    # WHERE they go is `twoway_end_sequence.place()`, derived from merged.srt. This
    # only draws them, and the input order is FIXED and read together with the `-i`
    # list below — the same pairing `assemble_episode` documents, for the same reason.
    g = plan.get("graphics") or {}
    gfx, gin = [], []
    nxt = 5 if ch else 4
    for key, lbl in (("open_card", "opc"), ("early_cta", "cta"), ("midroll", "mrl")):
        spec = g.get(key)
        if not spec:
            continue
        i, at, du, fa = nxt, spec["at_s"], spec["dur_s"], spec["fade_s"]
        nxt += 1
        gin.append(spec["clip"])
        # chromakey FIRST, then tpad — so the hold clones an already-keyed frame and
        # the chip does not grow a green edge when it freezes.
        keyer = "chromakey=0x00FF00:0.28:0.06," if spec.get("chromakey") else \
                "format=yuva420p,"
        gfx.append((lbl, at, round(at + du, 3),
                    f"[{i}:v]fps={FPS},{keyer}scale={W}:{H},"
                    f"tpad=stop_mode=clone:stop_duration={du:.3f},"
                    f"trim=duration={du:.3f},setpts=PTS-STARTPTS,"
                    f"fade=t=in:st=0:d={fa}:alpha=1,"
                    f"fade=t=out:st={round(du - fa, 3)}:d={fa}:alpha=1,"
                    f"setpts=PTS+{at:.3f}/TB[{lbl}];\n"))
        print(f"  {key} on screen {at:.2f}-{at + du:.2f}s ({du:.2f}s, fade {fa}s)",
              flush=True)
    if ecp:
        at, du, fa = ecp["from_s"], ecp["dur_s"], ecp.get("fade_s", 0.3)
        gin.append(str(d / "overlay/clips/end-card-template.mp4"))
        gfx.append(("ecd", at, round(at + du, 3),
                    f"[{nxt}:v]fps={FPS},format=yuva420p,scale={W}:{H},"
                    f"tpad=stop_mode=clone:stop_duration={du:.3f},"
                    f"trim=duration={du:.3f},setpts=PTS-STARTPTS,"
                    f"fade=t=in:st=0:d={fa}:alpha=1,"
                    f"fade=t=out:st={round(du - fa, 3)}:d={fa}:alpha=1,"
                    f"setpts=PTS+{at:.3f}/TB[ecd];\n"))
        nxt += 1
        print(f"  end card on screen {at:.2f}-{at + du:.2f}s ({du:.2f}s) — the e-book "
              f"line is spoken at {g.get('ebook_line_at_s', 0):.2f}s, "
              f"the warranty takes over at {plan['warranty']['from_s']:.2f}s",
              flush=True)

    # 🔴 THE CORNER LOGO COMES OFF WHILE A FULL-FRAME CARD IS UP — see `card_windows`.
    # `assemble_episode` gets this for free because the card is a LATER PASS and simply
    # covers the chip; the two-way overlays the chip last, so it has to be told. Without
    # it a 428x140 chip would sit on top of the 214x65 one the card already carries, in
    # the same corner.
    cwins = card_windows(plan)
    lg_enable = f"between(t,{ta.TITLE_HEAD_S},{body_end:.3f})" + "".join(
        f"*(1-between(t,{a:.3f},{b:.3f}))" for a, b in cwins)
    print(f"  corner logo on from {ta.TITLE_HEAD_S:.1f}s to {body_end:.2f}s — over "
          f"everything, including cards ({len(cwins)} hold-off window(s))", flush=True)
    print(f"    off for the tail: the chip's box overlaps the warranty slide's text "
          f"and its 1800 858 858 support line", flush=True)

    # the overlay chain: logo, chips, then the standing graphics in their fixed order.
    # `enable` as well as the PTS shift — belt and braces, and it means a graphic can
    # never be held on by an input that outlives its window.
    # 🔴 THE CHIP GOES LAST — OVER EVERYTHING, not under the graphics. Jodie, 27 Sep:
    # the bigger logo runs the whole way through. Drawn first it would have been covered
    # by the open card, the early e-book card and the end card, which is the same fault
    # the card hold-off was: the film's mark disappearing behind something.
    #
    # 📌 THE TAIL IS THE ONE EXCEPTION AND IT IS NOT A PREFERENCE. `lg_enable` still ends
    # at the end card, because past that lies the WARRANTY SLIDE — and the chip's box
    # (x 1452-1880, y 900-1040) OVERLAPS that slide's text (x 258-1660, y 93-1007),
    # including the "1800 858 858" support line. Covering that is the one thing this
    # channel cannot do; it is the entire reason `end_frame.py` exists. The end card and
    # the warranty carry their own marks and need no help.
    chain = []
    if ch:
        chain.append(("ch", f"between(t,{ch[0]:.3f},{ch[1]:.3f})", "0:0"))
    chain += [(lbl, f"between(t,{a0:.3f},{a1:.3f})", "0:0") for lbl, a0, a1, _ in gfx]
    chain.append(("lg", lg_enable, f"{lx}:{ly}"))
    vfc, cur = "", "[0:v]"
    for k, (lbl, en, pos) in enumerate(chain):
        dst = "[vout]" if k == len(chain) - 1 else f"[v{k}]"
        vfc += f"{cur}[{lbl}]overlay={pos}:enable='{en}':format=auto{dst};\n"
        cur = dst
    vfc = vfc.replace("[vout];\n", "[vpre];\n") + "[vpre]format=yuv420p[v];\n"

    # 📌 NO `scale` ON THE LOGO. The asset IS the size — that is what `corner_logo`
    # derives and what `assemble_episode`'s pass A does (it overlays the chip with no
    # scale filter at all). A scale here would be a fifth description of one mark.
    fc = ("[1:v]format=rgba[lg];\n" + chips_fc +
          "".join(x[3] for x in gfx) + vfc +
          f"[2:a]apad=whole_dur={total},atrim=duration={total},asetpts=PTS-STARTPTS,"
          f"adelay={int(ta.TITLE_HEAD_S * 1000)}|{int(ta.TITLE_HEAD_S * 1000)},"
          f"apad=whole_dur={total},atrim=duration={total},"
          f"loudnorm=I=-16:TP=-1.5:LRA=11,"
          f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
          f"asplit=2[sp][spkey];\n"
          f"[3:a]aloop=loop=-1:size=6000000,atrim=duration={total},"
          f"asetpts=PTS-STARTPTS,volume='{mus_env}':eval=frame,"
          f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
          f"[musraw];\n"
          f"[musraw][spkey]sidechaincompress=threshold=0.015:ratio=14:attack=12:"
          f"release=420:makeup=1:level_sc=2[mus];\n"
          f"[sp][mus]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    # 📌 THE INPUT ORDER IS THE GRAPH'S CONTRACT AND THE TWO ARE READ TOGETHER:
    # [0] picture · [1] logo · [2] speech · [3] music · [4] chips (only if there are
    # chips) · then the standing graphics in `gin` order, which is the order `gfx` was
    # built in. `assemble_episode` carries the same warning for the same reason: an
    # off-by-one here silently draws the wrong clip and every check still passes.
    run([ff, "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(whole), "-i", str(logo), "-i", str(aud), "-i", str(MUSIC),
         *(["-loop", "1", "-t", f"{total:.3f}", "-i", str(chips_png)] if ch else []),
         *sum((["-i", p] for p in gin), []),
         "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-t", f"{total:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out)],
        timeout=7200)


def assert_picture_reaches(whole: pathlib.Path, total_s: float,
                           tol_s: float = 0.15) -> float:
    """The concatenated picture must be as long as the plan says. Raises if not.

    🔴 A GAP IN A CONCAT DOES NOT ANNOUNCE ITSELF. `ffmpeg -f concat` joins whatever
    it is handed and reports success; if a piece is missing, everything after it simply
    slides earlier and the final `-t` pads the difference with BLACK. Nothing in the
    render path complains, and the output is the right LENGTH — which is how the missing
    3s settle reached a finished file (20 Sep 2026, EP49).

    ⚠️ AND IT SURFACED THREE CHECKS DOWNSTREAM, AS TWO FAULTS. The QC reported "57
    frames short of the header" and "BLANK FRAME at 854.8s" and they were one fault
    seen from two ends — both of them symptoms, measured on the finished file, long
    after the cheap question could have been asked. CLAUDE.md fault #1: assert the
    artefact at the point it is made, and say WHICH numbers disagree.

    Measured with `-count_packets`, not the header, for the reason in fault #1a: a
    faststart mp4 announces the length it intended. A concat copy has no faststart,
    but the habit is the point — the header is the thing being doubted.
    """
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-count_packets", "-show_entries",
                        "stream=nb_read_packets,r_frame_rate", "-of", "json",
                        str(whole)], capture_output=True, text=True, timeout=1800)
    st = (json.loads(r.stdout or "{}").get("streams") or [{}])[0]
    num, _, den = (st.get("r_frame_rate") or f"{FPS}/1").partition("/")
    got = int(st.get("nb_read_packets") or 0) / (float(num) / float(den or 1))
    if abs(got - total_s) > tol_s:
        raise Unrenderable(
            f"the concatenated picture is {got:.3f}s and the plan is {total_s:.3f}s "
            f"({got - total_s:+.3f}s). The pieces do not add up to the episode, so "
            f"everything after the gap is early and the tail will be black. Pieces:\n  "
            + "\n  ".join(f"{p.name}" for p in
                          [pathlib.Path(x.strip()[6:-1]) for x in
                           whole.with_name(whole.stem.replace("_picture", "_whole")
                                           + ".txt").read_text(encoding="utf-8")
                           .splitlines() if x.strip()]))
    return got


def layout_chips_move_ms(d: pathlib.Path) -> float:
    return float((tc.load_layout().get("chips") or {}).get("move_ms") or 260)


def twoway_chips_window(plan: dict, d: pathlib.Path) -> tuple[float, float] | None:
    """When the "reading …" chips are on screen: the FIRST two-box run inside the
    design's window, clipped to it. Returns None if there is no two-box in that minute.

    The window itself is `layout.chips.visible_s`, on the DIALOGUE clock, so it is
    shifted by the title card like every other time in this build (CLAUDE.md 1b).
    """
    vis = (tc.load_layout().get("chips") or {}).get("visible_s") or [0, 60]
    lo = ta.TITLE_HEAD_S + float(vis[0])
    hi = ta.TITLE_HEAD_S + float(vis[1])
    run = None
    for s in plan["segments"]:
        if s["layout"] != "two-box" or s["to_s"] <= lo or s["from_s"] >= hi:
            if run:
                break
            continue
        if run and abs(s["from_s"] - run[1]) < 0.001:
            run = (run[0], s["to_s"])
        elif run:
            break
        else:
            run = (s["from_s"], s["to_s"])
    if not run:
        return None
    a, b = max(run[0], lo), min(run[1], hi)
    return (round(a, 3), round(b, 3)) if b - a > 1.0 else None


def corner_logo(epj: dict) -> dict:
    """The STANDING corner logo — the one the channel has worn for forty-two episodes.

    🔴 THIS IS NOT THE CARDS' LOGO, AND READING IT AS THE CARDS' LOGO IS WHAT WENT
    WRONG. On 20 Sep Jodie said *"the motion graphics logo is the correct one and it
    should just be there throughout the whole video"*, and that was taken to mean the
    persistent corner mark should be IDENTICAL to a card's. It is not. A card's logo is
    furniture ON a card, 214x65. The video's corner mark is a separate, larger standing
    element — PP-STANDARDS §Logo: *"PROMINENT: generous size (roughly double a subtle
    watermark), near-opaque (~90%), clearly legible."*

    📏 MEASURED on EP48's finished film against EP49 cut #4: the published chip is
    **428x140**, EP49's was **214x65** — exactly half the linear size, a quarter of the
    area. Side by side it is the difference between a logo and a watermark.

    ⚖️ DERIVED, NEVER TYPED. The size is not a constant here; it is the ASSET'S OWN, read
    off the file, and the asset is the one `providers.RealProvider.logo` hands to
    `assemble_episode` — `assets/video-logo-chip.png`. `assemble_episode`'s pass A
    overlays it with NO scale filter at `logo_margin` (40) from the corner, so the file
    IS the size. That is the whole point: a logo nobody agrees about is what produced
    four descriptions of one mark, and a fifth description in a two-way constant would
    be the same fault wearing this module's name.

    ⚠️ `layout.json` names this asset and gives a `width` the overlay never applied —
    that dead `width` was the clue, noted on 20 Sep and not followed.
    """
    asset = HERE.parent / ".claude/skills/pp-episode-production/assets/video-logo-chip.png"
    if not asset.is_file():
        raise Unrenderable(
            f"the standing corner logo {asset.name} is not in the skill's assets. It is "
            f"what `providers.RealProvider.logo` hands the single-presenter build, so "
            f"the two-way cannot draw the channel's mark without it.")
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of",
                        "default=nw=1:nk=1", str(asset)],
                       capture_output=True, text=True, timeout=120)
    w, h = (int(x) for x in r.stdout.split())
    m = int(((epj.get("build") or {}).get("logo_margin", 40)))
    return {"src": str(asset), "w": w, "h": h, "margin": m,
            "x": W - w - m, "y": H - h - m}


def card_windows(plan: dict) -> list[tuple[float, float]]:
    """RETIRED 27 Sep 2026 — kept so the reason survives, and it returns nothing.

    🔴 JODIE OVERRULED THE BEHAVIOUR THIS PRODUCED. *"Why don't we have the nicer,
    bigger logo the whole way through the whole video? That's what I actually want."*

    It used to hold the chip off for every full-frame card, because `assemble_episode`
    gets that for free — it draws the chip in **pass A** and the cards in **pass B**, so
    a full-screen card COVERS the chip (measured on EP48 at 125.0s and 236.0s, where the
    corner carries only the card's own 214x65 mark). The two-way overlays the chip last,
    so it had to be told.

    ⚖️ THE TWO-WAY NOW DIVERGES FROM ALL 42 PUBLISHED EPISODES, DELIBERATELY. She has
    seen both and chosen. Whether the single-presenter path follows is a SEPARATE
    decision and `assemble_episode` has not been touched.

    ⚠️ AND COVERING WAS NOT ENOUGH, WHICH IS WHY THE CARDS THEMSELVES CHANGED. The chip
    is near-opaque, not opaque — alpha mean 203/255 over the card's mark, 9% of those
    pixels solid, the worst letting 26.3% through — so the card's own logo GHOSTED
    through it: mean 9.79 of 255, worst pixel 59, plainly visible as a second smaller
    logo inside the big one. The fix is that EP49's card clips are rendered with no logo
    at all, so nothing is there to ghost. Not a paint-out: a patch would have been a
    FIFTH description of where this logo goes, and four disagreeing descriptions are
    what cost two days.
    """
    return []


def card_logo_geometry(d: pathlib.Path, plan: dict) -> dict:
    """Where the MOTION-GRAPHICS cards put the PP logo — read off the cards themselves.

    🔴 THE CORNER LOGO AND THE CARDS' LOGO ARE ONE LOGO, SO THERE IS ONE PLACE THAT SAYS
    HOW BIG IT IS, AND IT IS THE CARDS. Jodie, 20 Sep 2026: *"There are two different PP
    logos in this video... when a card comes in, the card's logo lands over the top of a
    different logo. The MOTION-GRAPHICS LOGO IS THE CORRECT ONE."*

    They were never two files. `overlay/export/assets/logo.png` is 178×54 and BOTH used
    it — the cards scaled it to **214×65 at right:110 bottom:56**, and the renderer drew
    it at its **native 178×54 at (1474, 960)**, because the code hard-coded the filename
    and then read its size and position from a `layout.json` block that names a
    different asset (`video-logo-chip.png`), gives a `width` the overlay never applied,
    and states `right`/`bottom` where the code looked for `x`/`y`. **Four separate ways
    for one logo to be described, and no two of them agreeing.**

    ⚖️ So this does not copy the numbers into a better constant — that is one more
    description. It READS THE CARDS' OWN CSS, which is the thing on screen, and halts if
    the cards disagree among themselves. §7: derive the coverage from the thing itself,
    because a list somebody maintains is already broken.

    ⚠️ AND IT ASKS ONLY THE CARDS THAT ARE ACTUALLY IN THE BODY. Its first run halted
    because `ep49-title.html` puts the logo at `bottom:84` while all fifteen body cards
    use `bottom:56` — a real 28px difference, and the right answer is that the title
    card is not in the running: the corner overlay does not exist while it is on screen.
    The set comes from the PLAN's own card list, so it cannot include a surface the
    overlay never meets, and cannot go stale as cards are added or dropped.
    """
    import re
    pages = sorted({(d / "overlay/export" / (pathlib.Path(c).stem + ".html"))
                    for c in (plan.get("cards_on_disk") or {}).values()})
    pages = [p for p in pages if p.is_file()]
    found = {}
    for p in pages:
        m = re.search(r"\.logo\s*\{([^}]*)\}", p.read_text(encoding="utf-8"))
        if not m:
            continue
        body = m.group(1)
        vals = {k: float(v) for k, v in
                re.findall(r"(right|bottom|width|height)\s*:\s*(-?[\d.]+)px", body)}
        if len(vals) == 4:
            found.setdefault(tuple(sorted(vals.items())), []).append(p.name)
    if not found:
        raise Unrenderable(
            "no card page states where the PP logo goes, so the corner logo has "
            "nothing to match. Looked for a `.logo{...}` rule with right/bottom/"
            f"width/height in the {len(pages)} card pages this plan uses.")
    if len(found) > 1:
        raise Unrenderable(
            "the card pages do not agree where the PP logo goes, so there is no one "
            "answer for the corner logo to match:\n  "
            + "\n  ".join(f"{dict(k)} — {v[:3]}" for k, v in found.items()))
    g = dict(max(found, key=lambda k: len(found[k])))
    return {"w": int(g["width"]), "h": int(g["height"]),
            "x": W - int(g["right"]) - int(g["width"]),
            "y": H - int(g["bottom"]) - int(g["height"]),
            "pages": len(next(iter(found.values())))}


def music_envelope(plan: dict) -> str:
    """The standing bed envelope. 📌 THE SHAPE IS `assemble_episode`'s, not a new one.

    Up at the top, down under the voice, swelling back into the settle and soft under
    the warranty to the fade. The episode's own numbers go in; the shape does not
    change, because "how loud is the bed under a voice" is one decision for the channel
    and not a per-episode one.
    """
    se = plan["speech_end_s"]
    total = plan["total_s"]
    sw0, sw1 = round(se - 5.3, 2), round(se - 1.3, 2)
    blm, soft = round(se + 2.2, 2), round(total - 0.5, 2)
    return (f"if(lt(t,0.5),t/0.5,if(lt(t,5.0),1,if(lt(t,6.5),1-(t-5.0)/1.5*0.96,"
            f"if(lt(t,{sw0}),0.04,if(lt(t,{sw1}),0.04+(t-{sw0})/{round(sw1 - sw0, 2)}"
            f"*0.51,if(lt(t,{blm}),0.55,if(lt(t,{soft}),0.42,"
            f"max(0,0.42*(1-(t-{soft})/0.5)))))))))")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--out")
    ap.add_argument("--from", dest="t0", type=float, default=None)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--work")
    a = ap.parse_args()

    pp = pathlib.Path(a.pp)
    d = ep_paths.episode_dir(a.ep_number, pp)
    plan = ta.build_plan(a.ep_number, pp)
    v = ta.violations(plan)
    if v:
        raise Unrenderable("the plan has violations; nothing is rendered:\n  - "
                           + "\n  - ".join(v))
    tlj = json.loads((d / "renders/master-timeline.json").read_text(encoding="utf-8"))
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    layout = tc.load_layout()
    side_of = {c: s["side"] for c, s in epj["speakers"].items()}
    beds: dict[str, list] = {}
    for p in sorted((pp / "assets/reactions").glob("*-R*.mp4")):
        beds.setdefault(p.stem.split("-")[0], []).append((p.stem, p))
    offsets = {}
    for c, s in epj["speakers"].items():
        m = d / f"renders/{c}-master.mp4"
        if m.is_file():
            try:
                offsets[c] = tc.measure_eye_line(m) or 0.0
            except Exception:                                     # noqa: BLE001
                offsets[c] = 0.0
    ctx = {"layout": layout, "side_of": side_of, "timeline": tlj["timeline"],
           "idle": [dict(c, source=str(d / pathlib.Path(c["source"]).name)
                         if not pathlib.Path(c["source"]).is_absolute()
                         else c["source"]) for c in tlj["idle"]],
           "beds": beds, "cards": plan["cards_on_disk"],
           "broll": plan["broll_on_disk"], "offsets": offsets,
           "head_s": ta.TITLE_HEAD_S, "used": {"_t": 0.0}}

    work = pathlib.Path(a.work) if a.work else (d / "renders/_pieces")
    work.mkdir(parents=True, exist_ok=True)
    segs = plan["segments"]
    if a.t0 is not None:
        segs = [s for s in segs
                if s["to_s"] > a.t0 and s["from_s"] < (a.t1 or 10 ** 9)]
    print(f"{len(segs)} segment(s) to render into {work}")
    made = []
    for i, s in enumerate(segs, 1):
        out = piece_path(s, work)
        if not out.is_file():
            what = s.get("card") or s.get("broll") or s["layout"]
            print(f"  [{i}/{len(segs)}] {s['from_s']:7.1f}s {s['dur_s']:6.2f}s "
                  f"{what}", flush=True)
            render_segment(s, ctx, out)
        made.append(out)
    print(f"\n{len(made)} piece(s) in {work}")

    # 🔴 THE DISSOLVES, AFTER EVERY PIECE EXISTS AND NEVER BEFORE. Each one reads the
    # piece BEFORE it, so a partial render (--from/--to) must not attempt them: half a
    # dissolve is a join softened out of one shot and into no shot at all.
    if a.t0 is None:
        joins = [(i, s) for i, s in enumerate(segs) if s.get("dissolve_in_frames")]
        print(f"{len(joins)} join(s) to dissolve")
        for i, s in joins:
            dst = final_piece_path(s, work)
            if dst.is_file():
                continue
            n = s["dissolve_in_frames"]
            print(f"  {s['from_s']:7.1f}s  {n} frames out of "
                  f"{segs[i - 1].get('name') or segs[i - 1]['layout']} into "
                  f"{s.get('name') or s['layout']}", flush=True)
            apply_dissolve(piece_path(segs[i - 1], work), piece_path(s, work), n, dst)
    if a.out and a.t0 is None:
        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        print(f"\nfinishing into {out} ...", flush=True)
        finish(plan, d, work, out)

        # 🔴 THE PLAIN END FRAME — 18s of charcoal and one logo, APPENDED to the
        # finished film. It is not decoration and it is not new: `end_frame.py` has
        # done this for every published episode, and `qc_episode.py` HARD-FAILS below
        # 15s. YouTube draws its end-screen boxes over the last 15-20 seconds and the
        # operator does not choose where; without this the warranty slide is still on
        # screen and the boxes land on the responsible-gambling text and the
        # "1800 858 858" support line. Covering that is the one thing this channel
        # cannot do.
        #
        # ⚠️ AND IT IS WHY JODIE'S EIGHTH FAULT WAS NOT THE FIFTH ONE IN DISGUISE.
        # EP48's "39.4s tail" is 12.1s of end card, 9.2s of warranty and 18.1s of this
        # frame — and only the last of those is room for an end screen. The two-way
        # renderer appended nothing, so obeying rule 2 alone would still have shipped
        # an episode with no end-screen room at all.
        #
        # A COPY IS KEPT FIRST. The append rewrites the film in place, and a decision
        # this visible should be reversible in a file copy rather than a re-render.
        import end_frame
        import shutil
        # ⚠️ ALWAYS COPY, NEVER `if not pre.is_file()`. This guarded the copy so a
        # re-run would not overwrite it — which is exactly backwards: on the SECOND cut
        # it would have kept the FIRST cut's film under a name that says "this film,
        # before its end frame". A stale copy with a confident name is worse than none,
        # because the next person diffs against it.
        pre = out.with_name(out.stem + "-before-end-frame.mp4")
        shutil.copy2(out, pre)
        print("  " + end_frame.append(out, d / "overlay/export/assets/logo.png",
                                      MUSIC, plan.get("end_frame_s", 18.0)))
        got = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                              "format=duration,size", "-of",
                              "default=nw=1:nk=1", str(out)],
                             capture_output=True, text=True).stdout.split()
        print(f"WROTE {out}")
        print(f"  {float(got[0]):.2f}s, {int(got[1]):,} bytes "
              f"(planned {plan['total_s']:.2f}s film "
              f"+ {plan.get('end_frame_s', 18.0):.0f}s plain end frame)")
        print(f"  the film before the end frame is kept at {pre.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Unrenderable as e:
        print(f"\nHALT: {e}", file=sys.stderr)
        raise SystemExit(2)
