#!/usr/bin/env python3
"""`interleave` — the one genuinely new step in the two-way pipeline (build spec §5).

    python engine/twoway_interleave.py <ep_number> [--pp DIR] [--write]

**In:** two presenter masters + their two SRTs + `turns.json`.
**Out:** one master timeline, one merged speaker-tagged SRT, one idle pool.

> ### The whole design rests on the merged SRT. After it exists, a two-way episode is
> ### indistinguishable from a normal one to every step that follows.

That is why this module is the only new step: cards, b-roll, music, logo, end card,
warranty, e-book, thumbnail and YouTube copy all work unchanged, on the same
`episode.json`, against the same SRT.

── 🔴 IT HALTS ON A MISMATCH, AND THAT IS THE POINT ──────────────────────────────────
A presenter with *n* turns must show exactly *n−1* internal silences. If the count is
wrong the conversation is misaligned, and a misaligned conversation is **unrecoverable
downstream and cheap to catch here** — every turn after the bad one is attributed to the
wrong man, and nothing further along has any way to notice.

📌 **DETECT IN THE AUDIO; NEVER TRUST THE SRT TO REPORT THE PAUSES.** The detector is
`providers.trim_master_lead_in`'s, with `d` raised to find the 4–5s gaps instead of the
silent head. Avatar IV leaves that head too — measured 6.35 / 6.36 / 6.39s on EP11–13,
**measured every time, never hardcoded**, because a constant here would be right until
the day it is silently wrong.

── THE PAUSES ARE THE IDLE POOL ──────────────────────────────────────────────────────
This step has just cut them out; it saves them rather than discarding them. They are the
listening footage, they are free, and they **cannot mismatch the speaking footage
because they came from the same render** — the one thing separately rendered idle loops
can never guarantee.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

PP = pathlib.Path("G:/My Drive/PP Videos")

SILENCE_DB = -38.0
"""How quiet a thing has to be for this module to go looking for a PAUSE there.

📌 THIS THRESHOLD FINDS PAUSES. IT DOES NOT DECIDE WHERE A WORD ENDS — `refine_edges`
does, and the two are separate jobs that were being done by one number.

🔴 WHAT ONE NUMBER COST. -38 dB is the level of an unvoiced fricative: the "s" of *gold
medals* runs 86.748–86.908 in BB-master at **-37 to -43 dB**, against real silence at
**-90**. So the detector called that "s" the start of the pause, and EP49 shipped with
the last consonant clipped off every turn. Jodie, 20 Sep 2026: *"before he even says the
S sound at the end of MEDALS, he's cut off — and this is happening each section."*

⚠️ AND THE OBVIOUS FIX — just lower it — IS WRONG, WHICH IS WHY THIS IS TWO STAGES.
Dropped to -60 the edges are lovely and **BM-master stops having pauses at all**: its
breaths and room tone sit above -60, so the four six-second gaps break into scraps and
`turn_spans` finds ONE internal silence where it needs four. A miscount here does not
stop the build, it gives Barry's words to Gordon from that point on. **A coarse
threshold is what makes a pause visible AS a pause; a fine one is what finds the edge of
a word. Asking one value to do both is what broke it.**

⚠️ `providers.trim_master_lead_in`, `providers` line 735 and `build_shot_map.py` each
hard-code `-38dB` separately — the "one definition" this docstring used to claim was
already four copies. They are the SINGLE-presenter path, no fault has been reported
there, and they are named so the next person finds them — not silently changed.
"""

EDGE_FLOOR_OVER_NOISE_DB = 15.0
"""How far above a master's OWN noise floor the edge of a word is looked for.

Derived per master, never chosen: these renders have true digital silence in the SSML
breaks, so the first-percentile 10ms window is the floor itself and +15 dB sits clear of
it while staying ~40 dB under the quietest sibilant. Measured on EP49: BB's floor lands
at -76.9 dB with the "s" at -37, which is not a close call in either direction.
"""

EDGE_FLOOR_RANGE_DB = (-85.0, -45.0)
"""The band a derived floor is clamped into. **A DERIVED NUMBER STILL NEEDS A RANGE.**

🔴 BM-master contains true digital-ZERO samples, so its first percentile is -180 dB and
the derivation returned **-165**. Nothing in any recording is ever below that, so the
search for "quiet" found only the digital zeros — and one pause edge moved **3.95
seconds**, swallowing a pause and a breath into Steve's turn. The derivation was right
in principle and produced a number no signal can satisfy.

⚠️ The lesson is not "clamp this one". It is that *derived, never chosen* removes the
chance to be arbitrarily WRONG and not the chance to be DEGENERATE — a percentile of a
signal that contains exact zeros is one of those. -80 is below anything audible in these
masters; -55 is above any plausible room tone; between them the derivation is free.
"""

MAX_REFINE_S = 0.50
"""How far `refine_edges` may move an edge before it gives up and keeps the coarse one.

A refinement corrects a threshold error of TENS OF MILLISECONDS. EP49's real corrections
ran 13–290ms. Something that moves an edge by seconds is not refining the edge, it is
choosing a different edge, and it should not be able to do that quietly. Past this it
keeps the detector's own answer — and the audio-integrity guard, which measures what was
actually discarded, is what then reports any speech still being lost.
"""

GAP_MIN_S = 2.0
"""How long a silence must be to count as a TURN BOUNDARY. The scripts ask for 4s, so 2s
is a wide margin against a slow attack — and it is comfortably longer than any pause a
reader leaves inside a sentence, which is what stops a comma being read as a turn."""

HANDLE_S = 0.15
"""How far inside a SILENCE a cut is kept from the speech either side of it.

🔴 THIS IS A PROPERTY OF A SILENCE, NOT OF A CUT, AND SAYING "either side of a cut"
IS WHAT BROKE EP49. The old docstring read *"Kept either side of a cut, on the speech
and on the silence alike. Enough that a consonant is not clipped"* — and the code then
did `a + HANDLE_S, b - HANDLE_S` to SPEECH spans as well as silences, moving both edges
INTO the speech and throwing away 150ms at each end of every turn. **A constant whose
stated purpose was to stop a consonant being clipped was subtracted in the one direction
that guarantees it.** Jodie heard the result in ten minutes of watching.

⚖️ The arithmetic is not wrong; it is right for ONE of the two things it was applied to.
Shrinking a SILENCE keeps an idle clip off the words either side. Shrinking a SPEECH
span eats the words. Same expression, opposite meanings — CLAUDE.md §2b — so the two
now have names that say which way they go, and neither takes a raw pair of numbers.
"""


def silence_inset(a: float, b: float) -> tuple[float, float]:
    """A silence, pulled IN so a clip cut from it cannot catch the speech either side."""
    return round(a + HANDLE_S, 3), round(b - HANDLE_S, 3)


def speech_span(prev_silence_end: float, next_silence_start: float) -> tuple[float, float]:
    """A turn, taken WHOLE — from where the speech starts to where it stops.

    No handle. The edges are the silence's own edges, so every sample the man uttered is
    inside the span and the only thing either side of it is the pause. This is what the
    18 Sep v5 proof did — its plan records `src_last + pause_after == src_first` of the
    next turn to four decimal places at every boundary, nothing discarded — and it is
    the version Jodie called beautiful.
    """
    return round(prev_silence_end, 3), round(next_silence_start, 3)


LATENCY_BEATS_S = (0.32, 0.45, 0.38, 0.50, 0.35, 0.42)
"""🔴 REAL CROSSES HAVE DELAY; A HARD BUTT-JOIN SOUNDS SCRIPTED. Build spec §5 asks for
0.3–0.5s and says DO NOT TIGHTEN IT. Cycled rather than fixed because identical gaps are
the tell — the same rule the singles follow."""

REGISTER_EXTRA_S = 0.5
"""🔴 A CHANGE OF REGISTER NEEDS MORE AIR THAN A HANDOVER (build spec A15, Jodie, 27 Sep
2026). Where Gordon steps OUT of the reading to speak as himself — or back into it — the
gap is a handover beat PLUS this. EP49 used one number for both and at ~13:21 she heard
*"he stops talking and starts talking again in the same breath. It's too rushed"*; her
remedy was *"another half second pause or something"*. So it is exactly that: the cycled
handover beat (still varied, so no two register gaps match either) plus half a second.
Two numbers, not one. The silence is already in the master — the furniture sits between
~6s SSML breaks — so nothing needs re-rendering; the assembler just takes more of it."""

AUDIO_OVERLAP_S = 0.5
"""How much of the next voice is carried under the outgoing window (build spec §6).
"This does more for 'these two are talking' than anything else in the build."
📌 IT IS A MIX, NOT A CUT: it changes what is heard, never the timeline, so the master
duration is still the turns plus the latency beats."""

MIN_IDLE_S = 3.5
"""An idle clip shorter than this is not worth banking — it cannot cover a listen and
cutting back to the speaker that fast is a twitch."""


class Mismatch(Exception):
    """The conversation does not line up. Nothing is written."""


# ───────────────────────────────────────────────────────────────── detection ──

def _ffmpeg() -> str:
    import pp_paths
    return pp_paths.ffmpeg() or "ffmpeg"


def silences(path, thresh_db: float = SILENCE_DB,
             min_d: float = GAP_MIN_S) -> list[tuple[float, float]]:
    """Every silence in the file, as (start, end). Measured, never assumed.

    ⚠️ `silencedetect` LOGS AT INFO. Run it at `-v error` and the filter works perfectly
    while every line it emits is discarded — a passing check and an absent check produce
    the identical output, which is the EP18 freeze-detect scar exactly (CLAUDE.md 4b).
    """
    r = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-nostats", "-i", str(path),
         "-af", f"silencedetect=n={thresh_db}dB:d={min_d}", "-f", "null", "-"],
        capture_output=True, text=True, timeout=600)
    log = (r.stderr or "") + (r.stdout or "")
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", log)]
    if len(ends) < len(starts):                    # a silence running to the end
        ends.append(duration(path))
    return [(max(0.0, s), e) for s, e in zip(starts, ends) if e > s]


ISLAND_MAX_S = 1.0
"""How long a scrap of sound may be and still sit INSIDE one turn boundary.

🔴 A BREATH SPLITS A SIX-SECOND BREAK IN TWO, AND THIS MODULE'S ASSERTION COUNTS THE
PIECES. Steve's master has a break at 147.3s that the detector reports as 147.3–150.4
and 151.0–153.7 — one pause with six tenths of a second of something in the middle. Five
silences where the script asked for four, so `turn_spans` halted with a message about a
misaligned conversation, on a render that is perfectly aligned.

⚠️ AND THIS IS THE FAULT WITH THE WORST FAILURE MODE IN THE PIPELINE. The count is not
advisory: the spans it produces are what attribute every turn to a man, so an extra
boundary here does not stop the build, it silently gives Barry's words to Gordon from
that point on. The halt is right; what was wrong was the counting.

The avatar is a picture of a man sitting still, and a man sitting still breathes. Kept
tight at one second, for the same reason as `twoway_render_qc.ISLAND_MAX_S`: at two it
would swallow a short sentence between two pauses and INVENT a boundary, which is the
same fault pointing the other way and much harder to see.
"""


def _env(path, t0: float, t1: float, sr: int = 16000, win: float = 0.010):
    """10ms RMS in dB across a window of a file. The measuring instrument, nothing more."""
    import numpy as np
    t0 = max(0.0, t0)
    r = subprocess.run([_ffmpeg(), "-v", "error", "-ss", f"{t0:.4f}",
                        "-t", f"{max(0.0, t1 - t0):.4f}", "-i", str(path), "-vn",
                        "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                       capture_output=True, timeout=900)
    a = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0
    n = int(win * sr)
    if a.size < n:
        return [], win
    w = a[:a.size // n * n].reshape(-1, n)
    rms = np.sqrt((w ** 2).mean(axis=1))
    return list(20 * np.log10(np.maximum(rms, 1e-9))), win


def noise_floor(path, pauses: list[tuple[float, float]] | None = None) -> float:
    """What a PAUSE sounds like in this master, plus a margin. Derived, never chosen.

    🔴 MEASURED INSIDE THE PAUSES, AND AS A MEDIAN. Two earlier versions of this took a
    low percentile of the WHOLE file, and both were wrong on the same master for
    opposite reasons:

      · the 1st percentile of BM-master is **-180 dB**, because the render contains a
        patch of true digital ZERO. Nothing can be quieter than that, so "find where it
        goes quiet" found only the zeros — 3.95 seconds away — and an edge tried to
        swallow a whole pause.
      · clamping that to -80 was no better: **BM's pauses are not silent at all.** They
        sit at about **-66 dB of room tone**, so a floor of -80 is BELOW the pause and
        the search could never fire anywhere except those same digital zeros.

    BB's pauses ARE digital silence at -90, so no single whole-file statistic describes
    both masters. **The pauses are already known — the coarse pass just found them — so
    the honest estimator is "what is the level in there, typically".** A median ignores
    both the zero patch and the breath, which is exactly what it is for.
    """
    import numpy as np
    if pauses:
        vals: list[float] = []
        for a, b in pauses:
            env, _ = _env(path, a, b)
            vals.extend(env)
        if vals:
            raw = float(np.median(vals)) + EDGE_FLOOR_OVER_NOISE_DB
            lo, hi = EDGE_FLOOR_RANGE_DB
            return round(min(hi, max(lo, raw)), 1)
    env, _ = _env(path, 0.0, 10 ** 6)
    if not env:
        return EDGE_FLOOR_RANGE_DB[0]
    raw = float(np.percentile(env, 10.0)) + EDGE_FLOOR_OVER_NOISE_DB
    lo, hi = EDGE_FLOOR_RANGE_DB
    return round(min(hi, max(lo, raw)), 1)


def refine_edges(path, sil: list[tuple[float, float]],
                 floor_db: float | None = None) -> list[tuple[float, float]]:
    """Move each pause's edges out to where the sound ACTUALLY stops and starts.

    🔴 STAGE TWO. `silences()` says roughly where the pauses are, using a threshold
    coarse enough that a breath cannot break one in half. That threshold is far too high
    to say where a WORD ends — at -38 dB it puts the edge in the middle of a sibilant.
    So each edge is walked, on the samples, out to the master's own noise floor:

      · the START of a pause moves LATER, past the tail of the last word;
      · the END of a pause moves EARLIER, in front of the first word after it.

    A pause can only ever SHRINK here, never grow, so a refined pause is still wholly
    inside the pause the detector found and the turn COUNT cannot change. That property
    is the point: the count is what attributes turns to men, and it is settled in stage
    one where a breath cannot reach it.

    ⚠️ Requires 50ms of sustained quiet, not one window — a single quiet frame inside a
    fricative is a dip between two bursts of it, and stopping there would clip the word
    exactly the way the coarse threshold did.
    """
    HOLD = 0.05
    out = []
    fl = noise_floor(path, sil) if floor_db is None else floor_db
    for a, b in sil:
        # 🔴 t0 IS WHAT `_env` ACTUALLY READ, NOT WHAT IT WAS ASKED FOR. `_env` clamps a
        # negative start to zero, and this used to keep the unclamped `a - 0.40` for its
        # index arithmetic — so for the pause at the HEAD of a master, where a ≈ 0,
        # every index was 0.40s out and the measured lead-in came back 5.99s instead of
        # 6.40s. Caught by the interleave suite's synthetic fixture, which is the only
        # place a pause starts at zero. **A clamp that one side of a calculation knows
        # about and the other does not is an offset waiting to be blamed on something
        # else.**
        t0 = max(0.0, a - 0.40)
        env, win = _env(path, t0, b + 0.40)
        if not env:
            out.append((a, b))
            continue
        hold = int(round(HOLD / win))

        def quiet_from(i: int) -> bool:
            return all(d <= fl for d in env[i:i + hold])

        ia, ib = int(round((a - t0) / win)), int(round((b - t0) / win))
        na = next((i for i in range(max(0, ia - hold), min(ib, len(env)))
                   if quiet_from(i)), ia)
        nb = next((i for i in range(min(ib, len(env) - 1), na, -1)
                   if quiet_from(max(0, i - hold))), ib)
        ra, rb = round(t0 + na * win, 3), round(t0 + nb * win, 3)
        # it may only SHRINK, it must stay a pause, and it may not move far — see
        # MAX_REFINE_S. An edge that wants to move seconds has found a different pause,
        # not this one's edge, so the detector's answer stands.
        ra, rb = max(a, min(ra, b)), min(b, max(rb, a))
        if ra - a > MAX_REFINE_S:
            ra = a
        if b - rb > MAX_REFINE_S:
            rb = b
        # and then, separately: is the last thing before this pause actually part of
        # the sentence? See MAX_INTRA_TURN_GAP_S. This moves the pause START earlier,
        # the opposite direction from everything above, and it is REPORTED because a
        # stray word in a paid render is a fact, not a tidy-up.
        da = drop_trailing_utterance(path, ra, rb, fl)
        if da < ra - 0.001:
            print(f"  !! {pathlib.Path(path).name}: dropped {ra - da:.3f}s of "
                  f"sound at {da:.3f}-{ra:.3f} — it sits more than "
                  f"{MAX_INTRA_TURN_GAP_S:.2f}s after the last word, so it is not part "
                  f"of the turn. LISTEN to it before trusting this.", flush=True)
            ra = da
        out.append((ra, rb) if rb - ra > 0.2 else (a, b))
    return out


MAX_INTRA_TURN_GAP_S = 0.60
"""How long a gap inside one turn may be before what follows is a SEPARATE utterance.

🔴 A TURN ENDS AT ITS LAST WORD, NOT AT ITS LAST SOUND. Fixing `HANDLE_S` made the spans
run correctly to the end of all SOUND — and at one break that exposed something that is
sound but is not speech-of-the-turn: an **isolated 260ms burst at -12.9 dB, 1.27 seconds
after Steve's last word**, sitting inside the span his own alignment labels
`<break time="6s"/>`. The avatar vocalised at the break tag. Jodie heard it on 20 Sep as
*"he says the word I as if he's starting a new sentence, and then he stops talking"*.

📌 **MEASURED, AND THE TWO POPULATIONS DO NOT OVERLAP.** Across EP49's fifteen turn
endings the gap in front of the final burst runs 0.03, 0.03, 0.05, 0.05, 0.07, 0.07,
0.16, 0.16, 0.19, 0.20, 0.25, 0.45, 0.48 — ordinary sentence-final phrasing — and then
**1.27s** for the stray. This sits in the empty space between 0.48 and 1.27.

⚠️ IT IS FITTED TO ONE EXAMPLE AND THAT IS WORTH SAYING (CLAUDE.md 4c). Two things guard
against it: dropping an utterance is **reported, loudly, every time it happens** — a
stray word in a paid render is a fact somebody should have, not a thing to tidy away —
and `test_twoway_sync` prints the whole gap distribution on every run, so a real
phrasing gap creeping toward 0.60 is visible long before it eats a word.
"""


def drop_trailing_utterance(path, a: float, b: float, floor_db: float) -> float:
    """Pull a pause's START back past an utterance detached from the sentence.

    Returns the new start, and it can only ever move EARLIER — the pause grows, the turn
    shrinks, and the only thing that can be lost is sound that stands on its own after a
    gap no speaker leaves mid-sentence.
    """
    import numpy as np                                             # noqa: F401
    look = max(0.0, a - 3.0)
    env, win = _env(path, look, a)
    if not env:
        return a
    runs, cur = [], None
    for i, dbv in enumerate(env):
        if dbv > -35.0:
            cur = [look + i * win, look + i * win] if cur is None else \
                [cur[0], look + i * win]
        elif cur is not None:
            runs.append(tuple(cur))
            cur = None
    if cur:
        runs.append(tuple(cur))
    runs = [r for r in runs if r[1] - r[0] >= 0.04]
    if len(runs) < 2 or runs[-1][0] - runs[-2][1] <= MAX_INTRA_TURN_GAP_S:
        return a
    # walk forward from the real last word to where the signal reaches the floor,
    # exactly as refine_edges does — never to a level threshold, which is what put a
    # cut inside a fricative in the first place.
    hold = int(round(0.05 / win))
    start = int(round((runs[-2][1] - look) / win))
    stop = int(round((runs[-1][0] - look) / win))
    idx = next((i for i in range(start, stop)
                if all(d <= floor_db for d in env[i:i + hold])), None)
    return round(look + idx * win, 3) if idx is not None else a


def merge_silences(sil: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """One pause is one pause, whatever a breath in the middle of it does to the log."""
    out: list[list[float]] = []
    for s, e in sil:
        if out and s - out[-1][1] <= ISLAND_MAX_S:
            out[-1][1] = e
        else:
            out.append([s, e])
    return [(a, b) for a, b in out]


def duration(path) -> float:
    import pp_paths
    r = subprocess.run([pp_paths.ffprobe() or "ffprobe", "-v", "error",
                        "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True, timeout=120)
    return float((r.stdout or "0").strip())


def turn_spans(path, n_turns: int) -> tuple[list, list, float]:
    """(speech spans, pause spans, the measured lead-in) for one presenter master.

    🔴 THE ASSERTION IS THE WHOLE VALUE OF THIS FUNCTION. n turns, n−1 internal
    silences. A mismatch halts and says both numbers, because "it did not line up" is
    not something anyone can act on.
    """
    total = duration(path)
    # 🔴 FIND THE PAUSES COARSE, THEN FIND THEIR EDGES FINE — in that order, and the
    # count is settled before any edge moves. `refine_edges` can only ever shrink a
    # pause, so the assertion below is answering the same question either way.
    sil = refine_edges(path, merge_silences(silences(path)))
    head, tail = 0.0, total
    internal = []
    for s, e in sil:
        if s <= 0.25:                     # the silent head Avatar IV leaves — MEASURED
            head = max(head, e)
        elif e >= total - 0.25:
            # 🔴 THE TAIL IS A BOUNDARY, NOT SOMETHING TO IGNORE. A first version
            # skipped it and let the last turn run to the end of the file, so every
            # master ended with the render's own 3s of silence welded onto the final
            # turn — three seconds of nothing before the close, on every episode,
            # and every other assertion passed.
            tail = min(tail, s)
        else:
            internal.append((s, e))
    if len(internal) != n_turns - 1:
        raise Mismatch(
            f"{pathlib.Path(path).name}: this speaker has {n_turns} turns, so the "
            f"render must contain {n_turns - 1} internal silences of at least "
            f"{GAP_MIN_S:.0f}s. I measured {len(internal)}"
            + (f" (at {[f'{s:.1f}-{e:.1f}' for s, e in internal][:6]})" if internal
               else "")
            + ". A misaligned conversation cannot be recovered downstream — every turn "
              "after the bad one would be attributed to the wrong man — so nothing has "
              "been written. Check the script's SSML breaks reached the render, and "
              "LISTEN for the tag being read aloud.")
    edges = [head] + [e for _, e in internal]
    outs = [s for s, _ in internal] + [tail]
    speech = [(round(a, 3), round(b, 3)) for a, b in zip(edges, outs)]
    return speech, [(round(a, 3), round(b, 3)) for a, b in internal], round(head, 3)


# ─────────────────────────────────────────────────────────────── the timeline ──

def _beat(i: int) -> float:
    return LATENCY_BEATS_S[i % len(LATENCY_BEATS_S)]


def episode_order(turns: list[dict], manifest: dict, host: str) -> list[dict]:
    """The order the finished episode plays in: the host's segments and the guest's turns.

    🔴 THE HOST'S MASTER IS NOT DIALOGUE ANY MORE. Since 20 Sep the furniture — the
    open, the e-book CTA, the midroll, the close, the outro and the RG line — is
    composed INTO his one render, so his master holds twelve segments of which five are
    his turns. The old walk assumed every segment of every master was a turn, which was
    true when the furniture was a second render and is now silently wrong: it would have
    attributed Barry's first turn to Gordon's OPEN and misaligned the entire episode.

    ⚠️ AND WHERE EACH PIECE GOES IS DATA, NOT A GUESS FROM ITS POSITION. Two furniture
    pieces sit between the same pair of host turns and belong on opposite sides of the
    guest's turn in between:

        the CTA   is "after-host-turn-1"           -> it follows Gordon immediately,
                                                      before Barry replies
        the midroll is "midpoint-handover-into-host" -> it is a HANDOVER, so Barry
                                                      finishes first

    Ordering them by their index in the manifest alone puts the midroll before Barry's
    turn nine, which is the midroll interrupting him. So the manifest carries each
    piece's `where` — the same placement rule `twoway_furniture` resolved when it wrote
    the script — and a handover flushes the guest's pending turns while a follow-on does
    not.
    """
    segs = manifest["segments"]
    dialogue = [t for t in turns if t["speaker"] != "NARR"]
    guest = [t for t in dialogue if t["speaker"] != host]
    host_turn_ns = [s["turn"] for s in segs if s["kind"] == "turn"]
    missing = [s["n"] for s in segs if s["kind"] == "furniture" and not s.get("where")]
    if missing:
        raise Mismatch(
            f"the script manifest does not say WHERE furniture segment(s) {missing} go. "
            f"Without it the walk has to infer a position from an index, and the CTA "
            f"and the midroll sit between the same two host turns on opposite sides of "
            f"the guest's. Re-run twoway_furniture.py to write the manifest again.")

    out, gi = [], 0

    def flush_before(turn_n):
        nonlocal gi
        while gi < len(guest) and guest[gi]["n"] < turn_n:
            out.append({"kind": "turn", "speaker": guest[gi]["speaker"],
                        "turn": guest[gi]["n"], "index": gi})
            gi += 1

    for k, s in enumerate(segs):
        if s["kind"] == "turn":
            flush_before(s["turn"])
            out.append({"kind": "turn", "speaker": host, "turn": s["turn"],
                        "index": k, "segment": s["n"], "name": s["name"]})
        else:
            if s.get("where") == "midpoint-handover-into-host":
                nxt = next((n for n in host_turn_ns if n > (out[-1]["turn"] or 0)),
                           None) if out else None
                flush_before(nxt if nxt is not None else 10 ** 9)
            elif s.get("where") == "after-dialogue":
                flush_before(10 ** 9)
            out.append({"kind": "furniture", "speaker": host, "turn": None,
                        "index": k, "segment": s["n"], "name": s["name"],
                        "id": s["id"], "where": s.get("where")})
    flush_before(10 ** 9)
    return out


def timeline(turns: list[dict], spans: dict[str, list],
             masters: dict[str, str], manifest: dict | None = None,
             host: str | None = None) -> list[dict]:
    """The master timeline: ordered segments, each with its source, in/out and speaker.

    The same shape the rest of the studio already consumes. With a `manifest` the host's
    furniture is carried too; without one this is the pre-20-Sep dialogue-only walk,
    unchanged.
    """
    if manifest and host:
        return _timeline_with_furniture(turns, spans, masters, manifest, host)
    used = {k: 0 for k in spans}
    out, clock = [], 0.0
    dialogue = [t for t in turns if t["speaker"] != "NARR"]
    for i, t in enumerate(dialogue):
        code = t["speaker"]
        a, b = spans[code][used[code]]
        used[code] += 1
        a, b = speech_span(a, b)      # a turn is taken WHOLE; see speech_span
        dur = round(b - a, 3)
        out.append({"n": len(out) + 1, "turn": t["n"], "speaker": code,
                    "source": masters[code], "in_s": a, "out_s": b, "dur_s": dur,
                    "from_s": round(clock, 3), "to_s": round(clock + dur, 3),
                    "audio_overlap_s": AUDIO_OVERLAP_S if i < len(dialogue) - 1 else 0.0})
        clock += dur
        if i < len(dialogue) - 1:
            beat = _beat(i)
            out.append({"n": len(out) + 1, "turn": None, "speaker": None,
                        "source": None, "kind": "latency",
                        "from_s": round(clock, 3), "to_s": round(clock + beat, 3),
                        "dur_s": beat})
            clock += beat
    return out


def _timeline_with_furniture(turns, spans, masters, manifest, host) -> list[dict]:
    """The same timeline, walking `episode_order` instead of the turn list.

    A furniture segment is FULL FRAME by nature — Gordon steps out of the reading to
    speak it, and there is no conversation to put in a two-box. It carries
    `layout: "full"` so the composite does not have to work that out from the absence
    of a turn number.
    """
    order = episode_order(turns, manifest, host)
    used = {k: 0 for k in spans}
    out, clock = [], 0.0
    speaking = [o for o in order]
    for i, item in enumerate(speaking):
        code = item["speaker"]
        a, b = spans[code][used[code]]
        used[code] += 1
        a, b = speech_span(a, b)      # a turn is taken WHOLE; see speech_span
        dur = round(b - a, 3)
        row = {"n": len(out) + 1, "turn": item["turn"], "speaker": code,
               "source": masters[code], "in_s": a, "out_s": b, "dur_s": dur,
               "from_s": round(clock, 3), "to_s": round(clock + dur, 3),
               "audio_overlap_s": AUDIO_OVERLAP_S if i < len(speaking) - 1 else 0.0}
        if item["kind"] == "furniture":
            row.update({"kind": "furniture", "layout": "full", "furniture": item["id"],
                        "name": item["name"], "audio_overlap_s": 0.0})
            # 🔴 NO AUDIO OVERLAP ACROSS FURNITURE. The half-second carry is what makes
            # two men sound like they are talking to each other; carrying Gordon's
            # e-book CTA under Barry's next sentence would make the studio's own words
            # sound like part of the conversation, which is the one thing the reading
            # format is built not to do.
            if out:
                out[-1]["audio_overlap_s"] = 0.0
        else:
            row["name"] = item.get("name")
        out.append(row)
        clock += dur
        if i < len(speaking) - 1:
            # A15: reading <-> Gordon-as-himself is a change of register, not a handover.
            register = (item["kind"] == "furniture") != (speaking[i + 1]["kind"] == "furniture")
            beat = round(_beat(i) + (REGISTER_EXTRA_S if register else 0.0), 3)
            out.append({"n": len(out) + 1, "turn": None, "speaker": None,
                        "source": None, "kind": "latency",
                        "pause": "register" if register else "handover",
                        "from_s": round(clock, 3), "to_s": round(clock + beat, 3),
                        "dur_s": beat})
            clock += beat
    return out


# ──────────────────────────────────────────────────────────────── the SRT ──

_CUE = re.compile(r"(\d+)\s*\n([\d:,.]+)\s*-->\s*([\d:,.]+)\s*\n(.*?)(?=\n\s*\n|\Z)",
                  re.S)


def _t(s: str) -> float:
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))


def _fmt(x: float) -> str:
    h, r = divmod(max(0.0, x), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def read_srt(text: str) -> list[dict]:
    return [{"start": _t(a), "end": _t(b), "text": " ".join(c.split())}
            for _, a, b, c in _CUE.findall(text)]


def merged_srt(tl: list[dict], srts: dict[str, list[dict]]) -> str:
    """One SRT for the whole conversation, each cue tagged with its speaker.

    Cues are carried from each presenter's own SRT and RETIMED onto the master
    timeline — the segment says where its speech now starts, and every cue inside it
    moves by the same offset. Everything downstream that hangs off the SRT today keeps
    working unchanged.
    """
    rows, n = [], 0
    for seg in tl:
        if seg.get("kind") == "latency":
            continue
        off = seg["from_s"] - seg["in_s"]
        for cue in srts[seg["speaker"]]:
            if cue["end"] <= seg["in_s"] + 0.01 or cue["start"] >= seg["out_s"] - 0.01:
                continue
            # 🔴 CLAMPED TO THE SEGMENT. The cut takes a HANDLE off each end, so a cue
            # that ran to the last frame of the render now runs past the last frame of
            # the segment — and a cue that outlives its own picture is a caption sitting
            # over the next man's face. Clamping is not cosmetic: everything downstream
            # hangs off this file, and a cue that overlaps the next one is exactly the
            # kind of small wrongness the rest of the studio would inherit silently.
            a = min(max(cue["start"], seg["in_s"]), seg["out_s"])
            b = min(max(cue["end"], seg["in_s"]), seg["out_s"])
            if b - a < 0.05:
                continue
            n += 1
            rows.append(f"{n}\n{_fmt(a + off)} --> "
                        f"{_fmt(b + off)}\n[{seg['speaker']}] {cue['text']}\n")
    return "\n".join(rows) + "\n"


# ─────────────────────────────────────────────────────────── the idle pool ──

def idle_pool(pauses: dict[str, list], masters: dict[str, str],
              out_dir: pathlib.Path, write: bool) -> list[dict]:
    """Bank the pauses. 📌 THE STEP HAS JUST CUT THEM OUT; SAVING THEM IS FREE."""
    made = []
    for code, spans in pauses.items():
        for i, (a, b) in enumerate(spans, start=1):
            a, b = silence_inset(a, b)   # a PAUSE, pulled in off the words
            d = round(b - a, 3)
            if d < MIN_IDLE_S:
                continue
            rel = f"renders/idle/{code}-{i:02d}.mp4"
            made.append({"file": rel, "speaker": code, "dur_s": d,
                         "source": masters[code], "in_s": a, "out_s": b})
            if write:
                dest = out_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run([_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                                "-ss", str(a), "-to", str(b), "-i", masters[code],
                                "-c", "copy", str(dest)], timeout=600, check=False)
    return made


# ──────────────────────────────────────────────── snapping the layout plan ──

_SENT = re.compile(r"[.!?][\"')\u201d]?\s*$")


def sentence_ends(cues: list[dict]) -> list[float]:
    """Every moment the merged SRT says a SENTENCE ends. The only legal boundary."""
    return [c["end"] for c in cues if _SENT.search(c["text"] or "")]


def snap_plan(plan: list[dict], cues: list[dict]) -> list[dict]:
    """Move every layout boundary to the nearest sentence end (Jodie, 16 Sep, ruling 2).

    The commission picked TARGET times against an estimate; this is where they meet
    measured audio. A boundary with no sentence end within reach stays put and says so,
    because inventing one would put a push in the middle of a clause.
    """
    ends = sentence_ends(cues)
    out = []
    for seg in plan:
        s = dict(seg)
        if ends and seg is not plan[0]:
            near = min(ends, key=lambda e: abs(e - seg["from_s"]))
            s["snapped_from_s"] = round(near, 3)
            s["snap_moved_s"] = round(near - seg["from_s"], 3)
        out.append(s)
    for a, b in zip(out, out[1:]):
        a["snapped_to_s"] = b.get("snapped_from_s", b["from_s"])
    if out:
        out[-1]["snapped_to_s"] = out[-1]["to_s"]
    return out


# ────────────────────────────────────────────────────────────────── the step ──

def run(turns: list[dict], masters: dict[str, str], srt_text: dict[str, str],
        out_dir: pathlib.Path, write: bool = False,
        manifest: dict | None = None, host: str | None = None) -> dict:
    # 🔴 THE HOST'S MASTER IS COUNTED IN SEGMENTS, NOT TURNS. His render holds
    # the furniture as well as his five turns, so the n-1 silence assertion has to be
    # about what is IN the file. Counting turns would halt every two-way from 20 Sep on
    # with a number that looks like a misalignment and is not one.
    counts = {c: sum(1 for t in turns if t["speaker"] == c) for c in masters}
    if manifest and host:
        counts[host] = len(manifest["segments"])
    spans, pauses, heads = {}, {}, {}
    for code, path in masters.items():
        sp, pa, head = turn_spans(path, counts[code])
        spans[code], pauses[code], heads[code] = sp, pa, head
    tl = timeline(turns, spans, masters, manifest, host)
    cues = {c: read_srt(t) for c, t in srt_text.items()}
    srt = merged_srt(tl, cues)
    idle = idle_pool(pauses, masters, out_dir, write)

    speech = sum(s["dur_s"] for s in tl if s.get("kind") != "latency")
    beats = sum(s["dur_s"] for s in tl if s.get("kind") == "latency")
    res = {"timeline": tl, "srt": srt, "idle": idle, "lead_in_s": heads,
           "speech_s": round(speech, 3), "beats_s": round(beats, 3),
           "total_s": round(speech + beats, 3), "turn_counts": counts}
    if write:
        d = out_dir / "renders"
        d.mkdir(parents=True, exist_ok=True)
        (d / "master-timeline.json").write_text(
            json.dumps({k: v for k, v in res.items() if k != "srt"},
                       indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
        (d / "merged.srt").write_text(srt, encoding="utf-8", newline="\n")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    import ep_paths
    d = ep_paths.episode_dir(a.ep_number, pathlib.Path(a.pp))
    turns = json.loads((d / "docs/turns.json").read_text(encoding="utf-8"))["turns"]
    masters, srts = {}, {}
    for code in ("BB", "BM"):
        m = d / f"renders/{code}-master.mp4"
        s = d / f"renders/{code}.srt"
        if not m.is_file() or not s.is_file():
            print(f"\n🚫 {code}: need {m.name} and {s.name} in renders/. "
                  f"interleave runs AFTER both presenter renders are downloaded; "
                  f"neither has been made yet.")
            return 1
        masters[code], srts[code] = str(m), s.read_text(encoding="utf-8")
    epj_p = d / "docs/episode.json"
    host, manifest = None, None
    if epj_p.is_file():
        epj = json.loads(epj_p.read_text(encoding="utf-8"))
        host = next((c for c, v in (epj.get("speakers") or {}).items()
                     if v.get("host")), None)
        mp = d / f"docs/script-manifest-{host}.json" if host else None
        if mp and mp.is_file():
            manifest = json.loads(mp.read_text(encoding="utf-8"))
            print(f"host {host}: {len(manifest['segments'])} segments "
                  f"({sum(1 for x in manifest['segments'] if x['kind'] == 'furniture')} "
                  f"furniture) from {mp.name}")
    try:
        res = run(turns, masters, srts, d, a.write, manifest, host)
    except Mismatch as e:
        print(f"\n🚫 {e}")
        return 1
    print(f"lead-in measured: {res['lead_in_s']}")
    print(f"{len(res['timeline'])} segments, {res['speech_s']:.1f}s of speech + "
          f"{res['beats_s']:.1f}s of latency beats = {res['total_s']:.1f}s")
    print(f"idle pool: {len(res['idle'])} clips, "
          f"{min((c['dur_s'] for c in res['idle']), default=0):.2f}s shortest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
