"""The two-way commission fields: `speaker`, `listener`, `layout`, `reaction`.

Step 2 of the amended build order in `PP Videos/docs/PP-TWO-WAY-BUILD-SPEC.md`. Like
step 1 it is provable on the article alone — nothing rendered, nothing spent.

🔴 **LAYOUT IS DERIVED, NEVER AUTHORED** (build spec §4, thresholds replaced by A10 and
then again by Jodie's 16 Sep rulings). No human decides it per beat and no writer guesses
at it. That is why this is a module with a test and not a paragraph in a brief: the same
article must produce the same layout every time it is run, and a human must be able to
disagree with the RULE rather than with a hundred separate judgement calls.

🔴 **CARDS AND B-ROLL RUN FIRST, AND THIS DOES NOT TOUCH THEM.** `apply()` reads `card`
and `broll` off the beats it is given and computes the layout from what they already
decided. Nothing here may add, move or drop a card.

── THE UNIT IS A SENTENCE, AND THE BOUNDARY IS A TARGET ──────────────────────────────
**(Jodie, 16 Sep 2026, ruling 2 — replaces the paragraph-granularity first version.)**
The commission picks target TIMES; `interleave` snaps each to the nearest sentence end in
the aligned SRT. So this module works in sentences, and every boundary it emits carries
`snap_to_sentence` — the sentence whose END it means — so the snap can be audited before
a frame exists and re-made against real measured audio afterwards.

📌 **WHAT THAT BOUGHT.** At paragraph granularity two findings were unavoidable and both
are now closed: a single could only be a whole number of paragraphs, so on uniform ~23s
paragraphs *every single came out identical* — the exact thing A10 calls the tell — and
any overshoot past the hold ceiling had to be reported rather than avoided.

⚠️ **THESE TIMES ARE ESTIMATES** (`WORDS_PER_S`), not measurements. The real durations
arrive with the renders. Everything here is a plan to be snapped, not a cut list.

── THE REACTION: MECHANICAL PRECEDENCE, AUTHORED SIGNALS ─────────────────────────────
Build spec §8 chooses a reaction from **what the listener says next** — which is in the
text, at script time, for free. Half of §8's precedence is mechanical (is this the
handover? does this line carry a figure? is it mid-explanation?) and half is editorial
(does the next turn disagree, concede or agree?). The editorial half is authored ONCE PER
TURN, in `turn_signals`, each row carrying the words it was read from; the precedence
itself is code.

📌 **§8 WAS WRITTEN WHEN R1–R12 WERE TWELVE EQUAL LOOPS.** `PP-TWO-WAY-REACTIONS.md` §3
makes R1a/R1b/R11 long BEDS and the rest short punctuation, so two of §8's nine rules —
rule 5 (a figure is being spoken) and rule 9 (otherwise) — can no longer produce a clip
at all. A bed code in the precedence is therefore read as a statement about the BED, and
the search continues down §8's order for something to punctuate with. ✅ Approved by
Jodie, 16 Sep.

🔴 **A BED IS NEVER LOOPED** (Jodie, 16 Sep, ruling 3). A listen that outruns its bed
CHAINS to a different one — R1a → R11 → R1b — cutting on a blink where one is in reach.
A looped face is visibly a loop, and a loop is worse than a still.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import script_fidelity as sf                                     # noqa: E402

# ── PACE ──────────────────────────────────────────────────────────────────────────
WORDS_PER_S = 2.6

# ── A10 AS AMENDED BY JODIE, 16 SEPTEMBER 2026 ────────────────────────────────────
# Named, with the reason each exists, because a bare 15.0 in a walk is a number nobody
# can argue with. The first pass at these produced 72.3% two-box against a 55–65%
# expectation; all three numbers below are her correction of that.

FEWER_CUTS = True
"""🔴 RULE 1 — FEWER CUTS. (Jodie, 18 September 2026; amends A10 rules 1 and 3.)

Within ONE turn, once the layout has left the two-box for a card or b-roll it STAYS
on the speaker full frame, through any further cards and b-roll, until the handover
window. **No return to the two-box mid-turn, and no timer-driven pushes.**

Her reason, and it is the whole of it: THE PICTURE CHANGES ONLY FOR A REASON. Under
A10 rule 3 it also changed because an accumulator reached fifteen seconds, which is a
reason the machine has and the viewer does not.

⚠️ WHAT THIS TURNS OFF: `TWO_BOX_BEFORE_PUSH_S`, `SINGLE_TARGETS_S` and the cycle
that varied them are dead while it is True — there are no timed pushes left for them
to size. They are kept, not deleted, because Rule 1 is an amendment and an amendment
can be withdrawn.

⚠️ AND WHAT IT COSTS: A10's 35s ceiling on ONE PICTURE can no longer be enforced by
returning to the two-box, because returning is what this forbids. A long gap between
two graphics inside a turn holds the speaker for that whole gap. `violations()`
REPORTS it; it is not a hard fail, because the only fix available would be the timed
cut this rule removes."""

TWO_BOX_BEFORE_PUSH_S = 15.0
"""Accumulated two-box inside one turn before pushing to the speaker single.
🔴 WAS ~22s. Jodie, 16 Sep: "bring the singles back, gently" — at 22s with eight cards
chopping the long turns the accumulator almost never got there, and the episode came out
72.3% two-box with two singles in thirteen minutes."""

CARD_PAUSES_ACCUMULATOR = True
"""🔴 A CARD PAUSES THE TWO-BOX ACCUMULATOR; IT DOES NOT RESET IT. (Jodie, 16 Sep.)
"A card is a change of picture, not a fresh start." The first version reset it, which is
most of why the singles disappeared: every card sent the count back to zero and the
15–22s needed to earn a push was never accumulated again before the next card."""

SINGLE_MIN_S, SINGLE_MAX_S = 20.0, 35.0
"""A single runs 20–35s and 35 is a HARD CEILING. 🔴 ONE NUMBER NOW (Jodie, 16 Sep):
this replaces both A10's "~25–40s" and its separate "~30s without a change" rule, which
contradicted each other for any single over 30s, and the reaction doc's "~20s" (ruling 5)."""

SINGLE_TARGETS_S = (22.0, 31.0, 26.0, 34.0, 21.0, 29.0)
"""The single's target length, CYCLED — a cycle rather than a random draw because the
same article must derive the same episode every time. A random layout cannot be
reviewed."""

ADJACENT_SINGLE_GAP_S = 4.0
"""No two ADJACENT singles within this of each other (Jodie, 16 Sep). Enforced by
skipping forward in the cycle, and re-checked on the REALISED lengths by
`violations()` — the target is what we asked for, the realised length is what a viewer
gets, and "identical ones are the tell" is about what they get."""

RETURN_BEFORE_TURN_END_S = 9.0
"""The two-box must be back at least this long before the turn ends (A10 rule 3), which
is what makes the handover happen in the two-box rather than arriving as a cut."""

HANDOVER_TAIL_S = 2.0
"""The last of a turn, in the two-box, listener on R10 (A10 rule 4). Also the window in
which §8's rule 1 fires: "R10 if a cut to the listener follows within ~2s"."""

FINAL_APPROACH_S = 12.0
"""How far back from the handover the listener's NEXT turn starts colouring the reaction.
§8's rules 3, 4 and 6 read the next turn; they are about the approach to the cut, not a
paragraph two minutes earlier, or one signal would paint a whole turn."""

PUSH_MS = 750
"""The eased push between two-box and single — A10 rule 5, ~700–800ms, the house move.
Never a cross-dissolve and never a hard cut between these two layouts."""

CARD_HOLD_DEFAULT_S = 10.0
"""A card's on-screen length when `build.holds` does not name one — the assembler's own
`default_hold`. It is here because the DERIVATION now needs it: a card takes its hold and
the words underneath carry on, so a beat longer than the hold returns to the walk."""

TWO_BOX_MIN_S = 5.0
"""Below this a two-box is a flash, not a shot. The floor `violations()` measures
against, because Jodie asked to be shown any two-box under 5s."""

HANDOVER_FLOOR_S = HANDOVER_TAIL_S
"""The window at the end of a turn in which NOTHING takes the frame, not even a card.

🔴 IT IS THE TAIL, NOT THE TWO-BOX FLOOR, AND THE DIFFERENCE COST A CARD. It was briefly
max(tail, TWO_BOX_MIN_S) so the handover could not be a flash — and that squeezed EP49's
C6 to 4.1s against the 8.6s R6 asks for. The floor was the wrong lever: Rule 1 says the
handover window is "last ~2s AND THE FIRST SENTENCE OF THE NEXT TURN", so the two-box run
SPANS the boundary and clears five seconds easily. What was measuring it per SEGMENT was
`violations()`, and that is what changed instead — see `two_box_runs()`."""

MIN_DWELL_S = 5.0
"""🔴 THE MINIMUM DWELL LAW (Jodie, 18 September 2026). NO PICTURE STATE LIVES LESS
THAN THIS. Two-box, speaker single, card, b-roll — each holds five seconds before
anything changes.

Her words: *"If you're going to have something, have it on there for at least a certain
number of seconds. One or two seconds is not right."*

⚖️ IT IS A CONSTRAINT, NOT A CHECK. `TWO_BOX_MIN_S` is a floor that `violations()`
REPORTS after the fact; this is a floor the planner must SATISFY, and when it cannot,
the graphic moves to the next sentence in its turn or is dropped. **The picture is never
the thing that gives way** — that is the difference between a law and a warning.

📌 MEASURED ON CONTIGUOUS STATES, never on segments — see `picture_states()`. The plan
breaks a two-box at a turn boundary because the SPEAKER changes, and a viewer watching a
handover sees one unbroken shot of two men.

The one exception the brief allows is the handover LATENCY beat — the ~0.4s audio
overlap at a turn change. It is a sound event inside a shot and never a picture state,
so it does not appear in this list at all and needs no code."""

TURN_OPEN_MIN_S = 5.0
"""🔴 RULE 1, TURN START. The two-box holds through the handover AND the first five
seconds of the new turn — the whole first sentence if that is longer, because the walk
only ever changes picture at a sentence end.

Jodie: *"the two men talking and then the motion graphic coming on, like four or five
seconds into it."*

⚠️ AND THE TRIPLE THIS BANS. Under v4 a turn could open two-box, push to the speaker
single, and THEN bring a card up — three pictures in the first few seconds of a turn,
which is the opposite of what Rule 1 is for. A card due in the opening now lands
DIRECTLY from the two-box, and the picture falls back to the speaker single after it.
`violations()` fails a plan where a turn's first graphic is preceded by a single."""

MID_RETURN_TARGETS_S = (27.0, 33.0, 25.0, 31.0, 29.0, 35.0)
MID_RETURN_MIN_S, MID_RETURN_MAX_S = 25.0, 35.0
"""🔴 RULE 1, MID-TURN: HOW LONG THE SPEAKER SINGLE RUNS BEFORE THE TWO-BOX RETURNS.
Cycled rather than drawn at random, for the same reason `SINGLE_TARGETS_S` is: the same
article must derive the same episode every time, or the layout cannot be reviewed.

This is NOT the timer-driven push Rule 1 deleted. That one CUT AWAY from the home shot
because a clock said so; this one comes HOME when nothing else is asking for the frame.
The difference is which way the cut goes and what it costs: going home costs nothing,
because the two-box is where the conversation lives."""

TWO_BOX_REPORT_S = 60.0
"""How long ONE unbroken two-box may run before `violations()` mentions it.

Not a ceiling and not a failure — a REPORT, for the same reason v4's long singles were
reported: under Rule 1 the only way to cut a long shot is the timed push Jodie removed,
and a failure with no legal remedy is a failure nobody can act on. The remedy is
editorial — a graphic in the gap — and the line says so.

⚖️ 60s, NOT A10's 35s, AND THE DIFFERENCE IS THE POINT. A long SINGLE is one frozen
man. A long two-box has the listener alive in it — a bed, a blink every three to five
seconds, a punctuation clip every twenty-odd — so it survives length in a way a single
does not. Setting this to 35 would have buried the real finding (EP49 turn 10 runs 159.7s
on one picture) under a list of shots that are perfectly fine."""

GRAPHIC_LOOKAHEAD_S = 15.0
"""...and the two-box only returns if NO graphic is due within this. A return followed
straight away by a card is two cuts to show two seconds of conversation — the exact
flicker the dwell law exists to stop. If a graphic is close, the single simply holds
until it arrives."""

PUNCT_SPACING_S = 13.0
"""How often a punctuation clip may be cut into a long listen. Not a rule anybody wrote:
it is the spacing that keeps `R1` (bed alone, no clip) under §8's ~60% cap without
turning the listener into someone who twitches every ten seconds."""

# ── B-ROLL — STANDING RULES (Jodie, 15 Sep 2026; written into PP-STANDARDS §B-roll) ──
BROLL_SLOTS_MIN, BROLL_SLOTS_MAX = 6, 8
BROLL_DUR_MIN_S, BROLL_DUR_MAX_S = 8.0, 10.0
BROLL_DUR_SPREAD_S = 0.5
"""Six to eight slots an episode, each 8–10s, **lengths varied — never all equal**, and
the Higgsfield call passes the duration EXPLICITLY rather than taking the 5s default.
📌 B-ROLL IS DURATION-BOUNDED, NOT SENTENCE-BOUNDED: its IN point is a sentence start so
it enters cleanly, and its OUT point is the duration, because a cutaway plays under a
line that is still running. Only the two-box↔single boundaries snap at both ends."""

# ── THE REACTION LIBRARY (PP-TWO-WAY-REACTIONS.md §3) ─────────────────────────────
BEDS = ("R1a", "R1b", "R11")
PUNCT = ("R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R12")
BED_S = {"R1a": 60.0, "R1b": 45.0, "R11": 45.0}
BED_CHAIN = ("R1a", "R11", "R1b")
"""The order a listen chains through when it outruns a bed (Jodie, 16 Sep). Never a
loop — a different bed, cut on a blink where one is in reach."""
CLIP_S = {"R2": 6.0, "R3": 6.0, "R4": 6.0, "R5": 5.0, "R6": 6.0,
          "R7": 5.0, "R8": 6.0, "R9": 6.0, "R10": 5.0, "R12": 6.0}
"""⚠️ THE TABLE'S INTENDED LENGTHS, NOT MEASUREMENTS. The doc is explicit that
`duration_s` is measured from the file and never typed, so the moment the clips exist
the catalogue's measured values replace these and this dict goes away."""

R7_MAX_PER_EPISODE = 2          # §8 hard constraint
NO_REUSE_WITHIN_S = 90.0        # PP-TWO-WAY-REACTIONS.md §5

# ⚰️ §8's "R1 ≤ ~60% OF LISTENING TIME" IS RETIRED (Jodie, 16 Sep 2026).
# It guarded against a frozen five-second loop playing under half the episode. The
# listener is now always on a living BED, so the thing it protected against cannot
# happen — and the cap had two readings in the new vocabulary, both of which EP49 failed
# while looking perfectly good. **A rule with no unambiguous meaning is not a rule.**
#
# 🔴 WHAT REPLACES IT MEASURES THE THING WE ACTUALLY CARE ABOUT: does the listener DO
# anything often enough? Not "how much of the time is he neutral" — he is always
# something — but "how long can a viewer watch him before he moves".
PUNCT_MEAN_INTERVAL_MAX_S = 30.0
"""Mean gap between punctuation clips, measured in LISTENING time (two-box only).
Wall-clock would flatter it: a card or a single is time the listener is not on screen
at all, and counting it would let a busy episode hide a dead listener."""

PUNCT_GAP_MAX_S = 45.0
"""And no single stretch of listening longer than this without a clip. The mean can be
met by a flurry at one end and nothing at the other; this is the one a viewer feels.

🔴 RAISED FROM 35s BY JODIE, 16 Sep 2026, on evidence rather than on a preference. At 35
EP49 breached once, at 40.3s, in a stretch of short two-box segments where no 5-6s clip
fits — the material, not the selector. The floor and the mean (<=30s) do the work; this
is the outer bound, and an outer bound that the best available edit cannot meet is a
number, not a rule."""

PUNCT_FLOOR_TRIGGER_S = 22.0
"""When the density floor starts offering clips — WELL SHORT of the 35s ceiling, and
that margin is the whole point. A clip can only land where a sentence boundary and
enough room allow, so a floor that fires at 29s leaves the walk one or two chances and
misses: EP49 came back with gaps of 38.9s and 47.1s from a floor that was working
exactly as written. **A deadline you start working at is a deadline you miss.**"""

FLOOR_ORDER = ("R2", "R4", "R3", "R5", "R6", "R8", "R9", "R12", "R7", "R10")
"""What the density floor reaches for, least loaded first. R10 is LAST: a lean-in
promises a cut to that man, so away from a handover it is a promise the edit does not
keep. R7 is second-last — a soundless laugh at an arbitrary moment is worse than a nod."""
BLINK_EVERY_S = 4.0             # §5: a blink every 3–5s — the reach for a chain cut

RELATIONS = ("disagrees", "concedes", "agrees", "builds", "neutral")


def est_s(words: int) -> float:
    return round(words / WORDS_PER_S, 1)


# ─────────────────────────────────────────────────────── sentences and beats ──

_HEADING = re.compile(r"^\*\*[^*]+\*\*$")
# A full stop that really ends a sentence: followed by whitespace and a capital or a
# quote, or by the end of the text. ⚠️ NOT the article's spaced ellipsis — Brian writes
# "I circle, in green, these factors . . . like good trainer", and a naive split on "."
# turns one sentence into four, two of which are a single space.
_SENT_END = re.compile(
    r'(?<![.\s])(?<!\b[A-Z])([.!?]["”\')]?)(?=\s+["“(]?[A-Z0-9]|\s*$)')
"""⚠️ `(?<!\\b[A-Z])` IS THE INITIALS GUARD. The article names "very good judges like our
own E.J. Minnis, and Dennis Walker" — without it the stop after the `J` is followed by a
space and a capital, so `E.J.` became a sentence of its own and `Minnis` started another.
A word boundary immediately before a single capital is an initial; the `B` of `TAB.` has
a letter in front of it and is untouched."""


def sentences(text: str) -> list[str]:
    """The sentences of a beat, in order, verbatim. A paragraph break ends one too."""
    out = []
    for para in re.split(r"\n\s*\n", text or ""):
        para = para.strip()
        if not para:
            continue
        if _HEADING.match(para):
            out.append(para)
            continue
        parts = _SENT_END.sub(lambda m: m.group(1) + "\x00", para).split("\x00")
        out.extend(p.strip() for p in parts if p.strip())
    return out


def merge_headings(paras: list[str]) -> list[str]:
    """A sub-heading joins the paragraph it heads. Verbatim; only the grouping moves.

    🔴 THE ARTICLE'S INLINE `<b>` SUB-HEADINGS ARE NOT BEATS. Barry's turn 5 prints
    `ABILITY OF EACH HORSE` … `RACE SETUP` as their own paragraphs — one is a single
    word — so as beats they run **0.4 to 1.5 seconds**, too short to carry a layout, a
    reaction or a card cue. A heading belongs to its section, so it is read as one unit
    with the paragraph underneath it, which is also how a listener hears it. ✅ Approved
    by Jodie, 16 Sep. **Nothing is reworded, cut or reordered** and `turns.json` is
    untouched.
    """
    out: list[str] = []
    held: list[str] = []
    for p in paras:
        if _HEADING.match(p):
            held.append(p)
            continue
        out.append("\n\n".join(held + [p]))
        held = []
    if held:                       # a heading with nothing after it: keep it, alone
        out.append("\n\n".join(held))
    return out


def beats_from_turns(turns: list[dict]) -> list[dict]:
    """One beat per PARAGRAPH of dialogue, in article order. NARR paragraphs are not
    beats — neither reader speaks them, so a beat for one would have no audio under it.
    """
    out, n = [], 0
    for t in turns:
        if t["speaker"] == "NARR":
            continue
        for i, p in enumerate(merge_headings(
                [x.strip() for x in re.split(r"\n\s*\n", t["text"]) if x.strip()])):
            n += 1
            out.append({"n": n, "turn": t["n"], "speaker": t["speaker"],
                        "para_in_turn": i, "words": len(p.split()),
                        "est_s": est_s(len(p.split())), "line": p,
                        "card": None, "broll": None})
    for b in out:
        b["paras_in_turn"] = sum(1 for x in out if x["turn"] == b["turn"])
    return out


def _units(beats: list[dict]) -> list[dict]:
    """Every sentence in the episode, with its own estimated duration.

    The unit the layout walk moves in. A sentence's share of its beat is taken by WORD
    COUNT, which is the same estimate the beat itself carries — one definition of pace,
    not two.
    """
    out = []
    for b in beats:
        ss = sentences(b["line"]) or [b["line"]]
        words = [max(1, len(s.split())) for s in ss]
        total = sum(words)
        for s, w in zip(ss, words):
            out.append({"beat": b["n"], "turn": b["turn"], "speaker": b["speaker"],
                        "text": s, "est_s": round(b["est_s"] * w / total, 2),
                        "card": b["card"], "broll": b["broll"],
                        "para_in_turn": b["para_in_turn"],
                        "paras_in_turn": b["paras_in_turn"]})
    return out


def _split_turn_open(units: list[dict]) -> list[dict]:
    """Let a card on a turn's OPENING sentence land while that sentence is still running.

    🔴 JODIE, 20 Sep 2026: *"an opening-sentence card may land from the two-box 5s after
    the handover while its sentence still runs."*

    The walk changes picture only at a sentence END, which is right everywhere else and
    wrong here. A turn that opens with a fifty-word sentence owns the frame for nine
    seconds, so a card commissioned against that sentence could not enter until nine
    seconds in — and then had four fewer seconds before the handover than the rule
    allows it. On EP49 that is the whole of C1's problem: turn 3 is one paragraph of
    twenty seconds, the first sentence runs 9.2s, and the card wants 11.3s of reading
    with 2s of handover after it. Entering at 5.0s it fits with 1.7s to spare;
    entering at 9.2s it is dropped.

    So the opening unit is CUT at `TURN_OPEN_MIN_S` — the two-box keeps the first five
    seconds exactly as Rule 1 requires, and the card gets a legal entry at the moment
    the rule hands the frame over. The cut is made only where the ruling applies: the
    turn's FIRST beat carries a card, and its first sentence is longer than the opening
    the two-box owns. Everywhere else the unit list is untouched, so every other turn's
    plan is byte-identical to what it was.

    ⚠️ IT IS A CUT IN THE UNIT LIST, NOT A SPECIAL CASE IN THE WALK. A second rule
    inside the walk would be a second copy of Rule 1's opening — the fault the fixed
    point was built to remove. Here the walk's own `done < TURN_OPEN_MIN_S` test flips
    at exactly the new boundary and knows nothing about why it is there.
    """
    out: list[dict] = []
    for turn in sorted({u["turn"] for u in units}):
        tu = [u for u in units if u["turn"] == turn]
        first = tu[0]
        if (first.get("card") and first["est_s"] > TURN_OPEN_MIN_S + 0.05
                and all(v["beat"] != first["beat"] or v["card"] == first["card"]
                        for v in tu[:1])):
            head = dict(first, est_s=TURN_OPEN_MIN_S,
                        text=first["text"], _turn_open_head=True)
            tail = dict(first, est_s=round(first["est_s"] - TURN_OPEN_MIN_S, 2))
            out.extend([head, tail] + tu[1:])
        else:
            out.extend(tu)
    return out


def _other(code: str, speakers: list[str]) -> str:
    return [c for c in speakers if c != code][0]


# ────────────────────────────────────────────────────────── the layout plan ──

def _would_run(tu: list[dict], i: int, total: float, done: float,
               target: float) -> float:
    """How long a single started here would ACTUALLY hold, for this target.

    The walk cannot split a sentence, so a single overshoots its target by up to one
    sentence. Simulating that is the difference between varying the TARGETS and varying
    what a viewer sees — and "identical ones are the tell" is about what they see.
    """
    run, j, spent = 0.0, i, done
    while j < len(tu):
        u = tu[j]
        if u["card"] or u["broll"]:
            break
        if total - spent - u["est_s"] < RETURN_BEFORE_TURN_END_S:
            break
        if run >= target or run + u["est_s"] > SINGLE_MAX_S:
            break
        run += u["est_s"]
        spent += u["est_s"]
        j += 1
    return round(run, 2)


def _next_target(cycle_pos: int, last_actual: float | None, tu=None, i=0,
                 total=0.0, done=0.0) -> tuple[float, int]:
    """The next single's target, skipped forward until it is not a near-repeat.

    Jodie, 16 Sep: no two ADJACENT singles within ~4s of each other. Enforced by moving
    along the CYCLE rather than by nudging a number, so the targets stay the reviewed set
    and nothing invents a length nobody chose — and judged on the REALISED length, via
    `_would_run`, because a target of 22 against a previous realised 26.6 still produces
    a 23.1 and a gap of 3.5.
    """
    best = None
    for _ in range(len(SINGLE_TARGETS_S)):
        t = SINGLE_TARGETS_S[cycle_pos % len(SINGLE_TARGETS_S)]
        cycle_pos += 1
        if last_actual is None:
            return t, cycle_pos
        got = _would_run(tu, i, total, done, t) if tu else t
        gap = abs(got - last_actual)
        if gap >= ADJACENT_SINGLE_GAP_S:
            return t, cycle_pos
        if best is None or gap > best[0]:
            best = (gap, t, cycle_pos)
    return (best[1], best[2]) if best else (SINGLE_TARGETS_S[0], cycle_pos + 1)


def _place_graphics(units: list[dict], durs: dict[str, float],
                    holds: dict[str, float],
                    delays: dict[str, int] | None = None,
                    dropped: set | None = None,
                    reasons: dict | None = None) -> tuple[list[dict], list[str]]:
    """Move each turn's graphics to the earliest sentence the dwell law allows.

    A graphic is authored against a BEAT — the paragraph whose sentence it illustrates —
    and a beat can start half a second after the turn does. Rule 1 says the two-box owns
    the first five seconds, so the card waits for them; the dwell law says the gap
    between two graphics is a real shot, so the second waits five seconds for the first
    to finish. Both are satisfied HERE, by moving the graphic, and never by shortening a
    shot.

    `delays` pushes a named graphic further down its turn, one candidate sentence at a
    time. `plan_with_dwell()` fills it: this function proposes a placement and the real
    planner is what says whether it worked.

    ⚠️ ONLY ONE PREDICTION LIVES HERE, and it is about this function's own output: a
    graphic must have room for its FULL hold before the handover floor, because a
    truncated card cannot be repaired by moving it later — later is shorter. Everything
    else is left to the plan.
    """
    delays = delays or {}
    dropped = dropped if dropped is not None else set()
    reasons = reasons if reasons is not None else {}
    out = [dict(u) for u in units]
    log: list[str] = []
    for turn in sorted({u["turn"] for u in out}):
        idx = [i for i, u in enumerate(out) if u["turn"] == turn]
        tu = [out[i] for i in idx]
        total = sum(u["est_s"] for u in tu)
        prefix, run = [], 0.0
        for u in tu:
            prefix.append(round(run, 3))
            run += u["est_s"]
        order, want, first_at, own_beat = [], {}, {}, {}
        for j, u in enumerate(tu):
            for key in ("card", "broll"):
                ident = u[key]
                if ident and ident not in want:
                    order.append((key, ident))
                    first_at[ident] = prefix[j]
                    own_beat[ident] = u["beat"]
                    want[ident] = (durs.get(ident, BROLL_DUR_MIN_S) if key == "broll"
                                   else holds.get(ident, CARD_HOLD_DEFAULT_S))
        if not order:
            continue
        for u in tu:
            u["card"] = u["broll"] = None
        floor = TURN_OPEN_MIN_S
        for key, ident in order:
            if ident in dropped:
                continue
            w = want[ident]
            # 🔴 NEAREST TO WHERE THE AUTHOR PUT IT, NOT EARLIEST IN THE TURN. A card
            # is commissioned against the SENTENCE it illustrates, and
            # pp-visual-standard R10 requires its window to cover those words with >=80%
            # relevance. Ordering candidates by position rather than by DISTANCE moved a
            # b-roll eighty-nine seconds earlier than its own line — which is not moving
            # a graphic, it is re-commissioning it. Ties go to the later sentence: a
            # graphic that arrives a beat late is still about the thing just said.
            cands = [j for j in range(len(tu))
                     if prefix[j] >= floor - 0.001
                     and total - prefix[j] >= w + HANDOVER_FLOOR_S - 0.001]
            # 🔴 A CARD STARTS ON ITS OWN WORDS OR IT IS DROPPED. (Jodie, 20 Sep 2026,
            # closing v5's second breach.) v5 placed C3 and C4 at the nearest LEGAL
            # sentence, which was in the next paragraph, and both came out at 0.0%
            # relevance — on screen for ten and thirteen seconds while the speaker
            # talked about something else. Minimising displacement was a PROXY for
            # relevance and it failed exactly where the two come apart.
            #
            # So relevance is a CONSTRAINT SATISFIED HERE rather than a number
            # measured afterwards: a card may only enter on a sentence of the
            # paragraph it was commissioned against. It may still RUN PAST that
            # paragraph to finish its reading time — the loop below already carries it
            # across as many sentences as the hold needs — but it may not START
            # anywhere else. If no sentence of its own paragraph is legal, the card is
            # dropped and says so; it is never quietly rehoused over another idea.
            #
            # ⚠️ B-ROLL IS NOT UNDER THIS RULE. A cutaway illustrates a passage rather
            # than a sentence, its own line is matched loosely by design, and narrowing
            # it to one paragraph would drop clips that are already paid for.
            if key == "card":
                cands = [j for j in cands if tu[j]["beat"] == own_beat[ident]]
            cands.sort(key=lambda j: (abs(prefix[j] - first_at[ident]), -prefix[j]))
            n = delays.get(ident, 0)
            if n >= len(cands):
                dropped.add(ident)
                # 🔴 RECORDED ONCE, KEPT FOREVER. `reasons` outlives the round, so a
                # drop made on round 1 is still reported on round 9 — see this file's
                # patch note. The widest room any legal entry offers is named, because
                # that number is what tells a human whether to shorten the card or
                # lengthen the turn.
                scope = ([j for j in range(len(tu)) if tu[j]["beat"] == own_beat[ident]]
                         if key == "card" else list(range(len(tu))))
                # 🔴 NAME THE CONSTRAINT THAT ACTUALLY BOUND, NOT A CHEERFUL ONE.
                # `floor` is where the PREVIOUS graphic's dwell finished, and the first
                # version of this message ignored it: C4 was dropped and told it had
                # 51.4 seconds to play with, which is a message that sends a person
                # looking in the wrong place. A halt that misreports its cause is
                # fault #6 — the operator's next action appears to fix it.
                legal = [j for j in scope if prefix[j] >= floor - 0.001]
                best = max((total - prefix[j] - HANDOVER_FLOOR_S for j in legal),
                           default=0.0)
                where = (f"its own paragraph (beat {own_beat[ident]})"
                         if key == "card" else "that turn")
                if not legal:
                    early = max((total - prefix[j] - HANDOVER_FLOOR_S for j in scope),
                                default=0.0)
                    reasons.setdefault(ident, (
                        f"DROPPED {ident} from turn {turn}: every sentence of "
                        f"{where} starts before {floor:.1f}s into the turn, which is "
                        f"where the previous graphic's five-second dwell finishes. "
                        f"The paragraph itself could have given it {early:.1f}s, so "
                        f"this is a COLLISION, not a card that is too big: two "
                        f"graphics are commissioned against passages that are too "
                        f"close together. ⚠️ The remedies are human — move one of them "
                        f"to a different paragraph, or let one go."))
                    continue
                reasons.setdefault(ident, (
                    f"DROPPED {ident} from turn {turn}: it wants {w:.1f}s and the "
                    f"widest hold any legal entry in {where} can give it is "
                    f"{best:.1f}s. The turn is {total:.1f}s long, the two-box owns the "
                    f"first {TURN_OPEN_MIN_S:.0f}s and the handover the last "
                    f"{HANDOVER_FLOOR_S:.0f}s. ⚠️ THIS IS A SCRIPTING FAULT, NOT A "
                    f"LAYOUT ONE (pp-visual-standard R6/R10): a card that needs more "
                    f"seconds than its passage lasts means the script has under-served "
                    f"the idea. The remedies are all human: shorten the card, lengthen "
                    f"the passage, or let it go."))
                continue
            j = cands[n]
            got = 0.0
            k = j
            while k < len(tu) and got < w - 0.001:
                tu[k][key] = ident
                got += tu[k]["est_s"]
                k += 1
            if abs(prefix[j] - first_at[ident]) > 0.05:
                log.append(
                    f"MOVED {ident} in turn {turn}: {first_at[ident]:.1f}s -> "
                    f"{prefix[j]:.1f}s into the turn "
                    f"({prefix[j] - first_at[ident]:+.1f}s), to the nearest sentence "
                    f"that keeps every picture state at or over "
                    f"{MIN_DWELL_S:.0f}s.")
            floor = prefix[j] + w + MIN_DWELL_S
    return out, log


def _split_forced(units: list[dict], durs: dict[str, float],
                  holds: dict[str, float] | None = None) -> list[dict]:
    """Cut each b-roll beat's sentences at the clip's duration.

    🔴 B-ROLL IS AN OVERLAY, NOT A GAP IN THE NARRATION. A first version emitted a
    b-roll segment of `dur_s` and then skipped the whole BEAT, so **54 seconds of the
    episode simply disappeared** — 790s of dialogue came out as a 736s plan. The words
    under a cutaway keep running; only the picture changes. So the beat's units are
    split at the duration: the first part plays under the clip, the rest returns to the
    walk exactly as if the cutaway had not happened.

    The straddling sentence is divided by time, not by words — a cutaway's OUT point is
    a duration and never needs a sentence end (its IN point does, and it has one,
    because the clip starts where its beat's first sentence does).
    """
    holds = holds or {}
    out = []
    i = 0
    while i < len(units):
        u = units[i]
        # 🔴 A CARD IS AN OVERLAY TOO. It holds for `build.holds[id]` seconds and the
        # words underneath keep running — which is what the ASSEMBLER does, and what the
        # derivation used to disagree with by giving a card its whole beat.
        key = "broll" if u["broll"] else ("card" if u["card"] else None)
        if key is None:
            out.append(u)
            i += 1
            continue
        ident = u[key]
        want = (durs.get(ident, BROLL_DUR_MIN_S) if key == "broll"
                else holds.get(ident, CARD_HOLD_DEFAULT_S))
        got = 0.0
        while i < len(units) and units[i][key] == ident:
            v = units[i]
            if got + v["est_s"] <= want + 0.001:
                out.append(v)
                got += v["est_s"]
                i += 1
                continue
            head = round(want - got, 2)
            if head > 0.05:
                out.append(dict(v, est_s=head, text=v["text"]))
            out.append(dict(v, est_s=round(v["est_s"] - head, 2), **{key: None}))
            got = want
            i += 1
            break
        while i < len(units) and units[i][key] == ident:
            out.append(dict(units[i], **{key: None}))   # the rest of the beat, uncovered
            i += 1
    return out


def _split_broll(units: list[dict], durs: dict[str, float]) -> list[dict]:
    """Kept for `twoway_proof` and the tests, which call it by this name."""
    return _split_forced(units, durs)


def _forced_within(tu: list[dict], i: int, secs: float) -> bool:
    """Is a card or b-roll due within `secs` of here?

    🔴 DON'T START A SINGLE YOU CANNOT FINISH. The push is only worth making if there is
    room for a real one — a first version pushed whenever the accumulator crossed the
    threshold and produced thirteen singles of which twelve were UNDER the 20s floor,
    including one of 0.8s. A card arriving two sentences later is the change the push was
    reaching for, so the two-box simply holds and lets it land.
    """
    run = 0.0
    for u in tu[i + 1:]:
        if u["card"] or u["broll"]:
            return True
        run += u["est_s"]
        if run >= secs:
            return False
    return False


def derive_plan(beats: list[dict], broll_durs: dict[str, float] | None = None,
                card_holds: dict[str, float] | None = None,
                delays: dict[str, int] | None = None,
                dropped: set | None = None,
                place_log: list | None = None,
                reasons: dict | None = None) -> list[dict]:
    """The layout timeline: an ordered list of segments over the whole episode.

    Each segment is what a viewer sees without a change of picture. `to_s` is a TARGET;
    `snap_to_sentence` names the sentence whose end it means, and `interleave` moves it
    to that sentence's real end in the aligned SRT.
    """
    durs = broll_durs or {}
    holds = card_holds or {}
    # 🔴 THE GRAPHICS ARE PLACED BEFORE THEY ARE SPLIT. `_place_graphics` moves each
    # one to the earliest sentence the dwell law allows; `_split_forced` then gives it
    # exactly its hold and returns the rest of the beat to the walk. In that order a
    # card that has moved is split at its NEW position, which is the whole point.
    placed, _plog = _place_graphics(_split_turn_open(_units(beats)), durs, holds,
                                    delays, dropped, reasons)
    if place_log is not None:
        place_log.extend(_plog)
    units = _split_forced(placed, durs, holds)
    segs: list[dict] = []
    clock = 0.0
    cycle, last_single = 0, None
    mid_cycle = 0     # RULE 1 mid-turn: which 25-35s target this return is using.
                      # Carried ACROSS turns so consecutive returns differ even when
                      # each turn has only one.

    def emit(kind, layout, us, why, card=None, broll=None):
        nonlocal clock
        d = sum(u["est_s"] for u in us)
        if d <= 0:
            return
        segs.append({
            "n": len(segs) + 1, "layout": layout, "kind": kind,
            "turn": us[0]["turn"], "speaker": us[0]["speaker"],
            "beats": sorted({u["beat"] for u in us}),
            "from_s": round(clock, 2), "to_s": round(clock + d, 2),
            "dur_s": round(d, 2),
            "snap_to_sentence": us[-1]["text"][-90:],
            "card": card, "broll": broll, "transition_ms": PUSH_MS, "_why": why,
            "_units": us,
        })
        clock += d

    for turn in sorted({b["turn"] for b in beats}):
        tu = [u for u in units if u["turn"] == turn]
        total = sum(u["est_s"] for u in tu)
        done = 0.0
        acc = 0.0             # accumulated two-box inside this turn
        pending: list[dict] = []
        mode, kind = "two-box", "two-box"
        target, run = 0.0, 0.0
        left_two_box = False      # RULE 1: has a graphic taken this turn off the two-box

        def flush():
            nonlocal pending
            if pending:
                emit(kind, "two-box" if mode == "two-box" else "full", pending,
                     _why(mode, acc, target, run, came_home=left_two_box),
                     card=pending[0]["card"], broll=pending[0]["broll"])
                pending = []

        for i, u in enumerate(tu):
            forced = "card" if u["card"] else ("broll" if u["broll"] else None)
            left_after = total - done - u["est_s"]
            left_here = total - done

            # 🔴 A10 rule 4 wins at both ends of a turn, EVEN OVER A CARD. A card whose
            # source line is the turn's first or last sentence would otherwise take the
            # frame at the one moment the conversation needs both men on it.
            # 🔴 RULE 1, TURN START (Jodie, 18 Sep 2026). The two-box holds through the
            # handover AND the first TURN_OPEN_MIN_S of the new turn — and because the
            # walk changes picture only at a sentence end, that means the whole first
            # sentence when the sentence is longer. It used to be `i == 0`, one
            # sentence, which on a short opener was a two-second shot.
            if done < TURN_OPEN_MIN_S - 0.001 or (not pending and not segs):
                want, wkind = "two-box", "two-box"       # rule 4 — a turn opens open
            elif left_after < HANDOVER_FLOOR_S:
                want, wkind = "two-box", "two-box"       # rule 4 — and hands over open
            elif forced:
                want, wkind = "forced", forced
            elif left_after < RETURN_BEFORE_TURN_END_S:
                want, wkind = "two-box", "two-box"       # A10 rule 3 — back for the cut
            elif FEWER_CUTS:
                # 🔴 RULE 1 AS REVISED, 18 Sep 2026. Three states, in order:
                #
                # 1. This turn has not left the two-box yet -> it is home. A turn with
                #    no graphic in it never leaves at all, which is the correct answer
                #    and not an omission: the picture changes for a reason.
                # 2. It left, came back, and is home again -> it STAYS until a graphic
                #    or the handover. Coming home is not a temporary visit.
                # 3. It left and is on the speaker single -> the single runs its
                #    25-35s target and then the two-box RETURNS, but only if no graphic
                #    is due within GRAPHIC_LOOKAHEAD_S. If one is, the single simply
                #    holds until it lands, because returning for eight seconds and
                #    cutting away again is two cuts to show nothing.
                #
                # ⚖️ THIS IS NOT THE TIMED PUSH RULE 1 DELETED. That one cut AWAY from
                # the home shot on a clock the viewer cannot see. This comes HOME when
                # nothing else wants the frame — and v4 measured what its absence
                # costs: 18.6% two-box, down from 61%.
                if not left_two_box or mode == "two-box":
                    want, wkind = "two-box", "two-box"
                elif (mode == "single" and run >= target - 0.001
                      and not _forced_within(tu, i - 1, GRAPHIC_LOOKAHEAD_S)):
                    # 🔴 `mode == "single"` IS LOAD-BEARING, NOT DEFENSIVE. Coming off
                    # a card the mode is "forced", and BOTH `run` and `target` are 0 —
                    # run only counts while the picture is a single, target is only set
                    # when one begins. Without the state test the arithmetic reads
                    # 0 >= 0 and the two-box comes straight home off every graphic,
                    # which is the one thing the revised Rule 1 does not say.
                    want, wkind = "two-box", "two-box"       # the return
                else:
                    want, wkind = "single", "single"
            elif mode == "single":
                go_on = run < target and run + u["est_s"] <= SINGLE_MAX_S
                want, wkind = ("single", "single") if go_on else ("two-box", "two-box")
            elif (acc >= TWO_BOX_BEFORE_PUSH_S
                  and left_here >= SINGLE_MIN_S + RETURN_BEFORE_TURN_END_S
                  and not _forced_within(tu, i - 1, SINGLE_MIN_S)):
                want, wkind = "single", "single"
            else:
                want, wkind = "two-box", "two-box"

            if want == "forced":
                left_two_box = True
                if mode != "forced" or kind != wkind \
                        or (pending and pending[0]["card"] != u["card"]) \
                        or (pending and pending[0]["broll"] != u["broll"]):
                    flush()
                    if mode == "single":
                        last_single = run
                    mode, kind = "forced", wkind
                    # 🔴 A CARD PAUSES THE ACCUMULATOR, IT DOES NOT RESET IT.
                    if not CARD_PAUSES_ACCUMULATOR:
                        acc = 0.0
            elif want != mode:
                flush()
                if want == "single":
                    # Under Rule 1 a single is the gap between a graphic and the walk
                    # coming home, so its length is MID_RETURN_TARGETS_S and not the
                    # old push cycle — `_next_target` sizes a push nothing now makes.
                    if FEWER_CUTS:
                        target = MID_RETURN_TARGETS_S[mid_cycle
                                                      % len(MID_RETURN_TARGETS_S)]
                        mid_cycle += 1
                    else:
                        target, cycle = _next_target(cycle, last_single, tu, i,
                                                     total, done)
                    run = 0.0
                    acc = 0.0
                elif mode == "single":
                    last_single = run
                mode, kind = want, wkind

            pending.append(u)
            if mode == "single":
                run += u["est_s"]
            elif mode == "two-box":
                acc += u["est_s"]
            done += u["est_s"]
        flush()
    return segs


def _why(mode, acc, target, run, came_home=False):
    if mode == "two-box":
        if came_home:
            return (f"RULE 1 (revised): the two-box RETURNED after ~{run:.0f}s on the "
                    f"speaker, the target being "
                    f"{MID_RETURN_MIN_S:.0f}-{MID_RETURN_MAX_S:.0f}s, because no "
                    f"graphic was due within {GRAPHIC_LOOKAHEAD_S:.0f}s. It is home "
                    f"now and stays until a graphic or the handover.")
        # ⚠️ THE OLD SENTENCE QUOTED `TWO_BOX_BEFORE_PUSH_S`, A THRESHOLD RULE 1
        # SWITCHED OFF. A reason that names a number nothing reads is worse than no
        # reason: it sends the next person to tune a dial that is not connected.
        return ("the two-box is the home shot (A10 rule 1) and nothing has asked for "
                "the frame — under Rule 1 the picture changes for a reason or it does "
                "not change.")
    if mode == "single":
        return (f"pushed to the speaker single (A10 rule 3), target {target:.0f}s, held "
                f"{run:.0f}s \u2014 inside the {SINGLE_MIN_S:.0f}\u2013"
                f"{SINGLE_MAX_S:.0f}s window, {SINGLE_MAX_S:.0f}s the hard ceiling.")
    return ("A10 rule 2 \u2014 this beat carries a card or b-roll, which takes the "
            "whole frame. A cutaway's IN point is a sentence start; its OUT point is "
            "the duration, because the line underneath is still running.")


# ────────────────────────────────────────────────────────── §8: the reactions ──

def _has_figure(line: str) -> bool:
    """§8 rule 5 — asked of `script_fidelity.figures()` on the spoken form, so "a
    figure" means exactly what the studio's own gate means by it, in one place."""
    return bool(sf.figures(sf.fold(line, unit_reading="hundreds")))


def _pick(cands, recent, t, last_for_listener, r7_used, room):
    """The first candidate the hard constraints allow, or None.

    §8: never the same reaction twice running on one man; R7 at most twice an episode.
    `PP-TWO-WAY-REACTIONS.md` §5: no reaction clip reused within ~90s. And a clip that
    does not FIT the room it is given is not offered — a six-second nod in a two-second
    gap outruns its own moment and lands under whatever comes next.
    """
    for r in cands:
        if r == last_for_listener or CLIP_S.get(r, 6.0) > room:
            continue
        if r == "R7" and r7_used >= R7_MAX_PER_EPISODE:
            continue
        if t - recent.get(r, -1e9) < NO_REUSE_WITHIN_S:
            continue
        return r
    return None


def _bed_chain(dur: float, first: str) -> tuple[str, list[dict]]:
    """A listen longer than one bed CHAINS to a different bed. It never loops.

    (Jodie, 16 Sep, ruling 3.) The cut wants a blink, and a blink comes every 3–5s
    (`PP-TWO-WAY-REACTIONS.md` §5) — so the chain point is pulled back to the last whole
    blink interval inside the bed, which is where one is certainly in reach. Assembly
    still cuts on the actual blink; this says which bed and roughly when.
    """
    chain, at, cur = [], BED_S[first], first
    order = [b for b in BED_CHAIN if b != first]
    while at < dur and order:
        nxt = order.pop(0)
        cut = round(at - (at % BLINK_EVERY_S), 1) or round(at, 1)
        chain.append({"at_s": cut, "to": nxt,
                      "_why": f"the listen runs {dur:.0f}s and {cur} is "
                              f"{BED_S[cur]:.0f}s. A bed is NEVER looped (Jodie, "
                              f"16 Sep) — chain to {nxt} and cut on a blink; one comes "
                              f"every {BLINK_EVERY_S:.0f}s or so."})
        at, cur = cut + BED_S[nxt], nxt
        order.append(cur)
        if len(chain) > 6:
            break
    return first, chain


def derive_reactions(segs: list[dict], speakers: list[str],
                     signals: dict[int, dict]) -> list[dict]:
    """§8's precedence, applied across every two-box segment. Mutates and returns segs."""
    signals = {t: dict(s, tones={int(k): v
                                 for k, v in (s.get("tones") or {}).items()})
               for t, s in signals.items()}
    order = sorted({s["turn"] for s in segs})
    nxt = {t: (order[i + 1] if i + 1 < len(order) else None)
           for i, t in enumerate(order)}
    recent: dict[str, float] = {}
    last_for: dict[str, str] = {}
    bed_last_for: dict[str, str] = {}
    r7_used = 0
    listen_since = 0.0      # LISTENING seconds since the last clip, across segments

    turn_end = {t: max(s["to_s"] for s in segs if s["turn"] == t) for t in order}

    for seg in segs:
        seg["listener"] = _other(seg["speaker"], speakers)
        if seg["layout"] != "two-box":
            seg["reaction"] = None
            continue
        listener = seg["listener"]
        sig = signals.get(nxt[seg["turn"]] or -1, {})
        relation, opens = sig.get("relation", "neutral"), sig.get("opens", "")
        us = seg["_units"]
        dense = sum(1 for u in us if _has_figure(u["text"])) >= max(1, len(us) // 2)

        want = ["R11"] if dense else (["R1b", "R1a"] if relation in
                                      ("agrees", "concedes") else ["R1a", "R1b"])
        bed = next((r for r in want + list(BEDS) if r != bed_last_for.get(listener)),
                   BEDS[0])
        bed_last_for[listener] = bed
        bed, chain = _bed_chain(seg["dur_s"], bed)

        punct, t = [], seg["from_s"]
        for k, u in enumerate(us):
            at_end = (t + u["est_s"]) >= turn_end[seg["turn"]] - 0.01
            to_handover = turn_end[seg["turn"]] - (t + u["est_s"])
            approach = to_handover <= FINAL_APPROACH_S
            tone = (signals.get(seg["turn"], {}).get("tones") or {}).get(u["beat"])

            # 🔴 §8's PRECEDENCE, IN ORDER. Each rule that fires APPENDS its codes; the
            # first punctuation code that survives the hard constraints wins the clip,
            # and a bed code arriving before it has already spoken for the bed.
            cands, whys = [], []

            def rule(codes, text):
                cands.extend(codes)
                whys.append(text)

            if at_end:
                rule(["R10"], f"a cut to {listener} follows within "
                              f"~{HANDOVER_TAIL_S:.0f}s — §8 rule 1, which "
                              f"overrides everything.")
            if tone in ("aside", "joke"):
                rule(["R6", "R7"] if tone == "aside" else ["R7", "R6"],
                     f"the line is a dry {tone} — §8 rule 2.")
            if approach and relation == "disagrees":
                rule(["R8", "R9"],
                     f"{listener}'s next turn pushes back — “{opens[:80]}"
                     f"…” — §8 rule 3. The reaction foreshadows what "
                     f"he is about to say, which is what makes the cut feel earned.")
            if approach and relation == "concedes":
                rule(["R12"], f"{listener}'s next turn concedes — “"
                              f"{opens[:80]}…” — §8 rule 4.")
            if _has_figure(u["text"]):
                rule(["R11"], "a figure or a rule is being spoken — §8 rule 5.")
            if approach and relation in ("agrees", "builds"):
                rule(["R3", "R2"],
                     f"{listener}'s next turn {relation} on this — “"
                     f"{opens[:80]}…” — §8 rule 6.")
            if tone == "surprise":
                rule(["R5", "R4"], "a surprising claim — §8 rule 7.")
            if 0 < k < len(us) - 1:
                rule(["R2", "R4"], "mid-explanation — §8 rule 8.")

            beds_wanted = [c for c in cands if c in BEDS]
            cands = [c for c in cands if c in PUNCT]
            why = whys[0] if whys else ("§8 rule 9 — nothing asks for "
                                        "punctuation; the bed runs.")
            if beds_wanted and not cands:
                why = (f"§8 asks for {beds_wanted[0]}, which is a BED in the new "
                       f"library and not a clip — the bed carries it. ({why})")

            # 🔴 A FLOOR-DRIVEN CLIP GOES AT THE TOP OF THE SENTENCE, and that is not
            # a fudge to make the numbers work — `PP-TWO-WAY-REACTIONS.md` §5 asks for
            # exactly this: "bring the listener's reaction in a beat EARLY". It also
            # happens to be the only place with room: at 0.55 of a short sentence deep
            # in a 5s segment there were 1 to 5 seconds left, and EVERY refusal the
            # floor hit was `room`, never taste.
            floor_on = listen_since >= PUNCT_FLOOR_TRIGGER_S
            at = (round(u["est_s"] - HANDOVER_TAIL_S, 1) if at_end
                  else 0.0 if floor_on
                  else round(u["est_s"] * 0.55, 1))
            abs_at = t + at
            # 🔴 THE ROOM IS THE REST OF THE SEGMENT, NOT THE REST OF THE SENTENCE.
            # The listener is on screen for the whole two-box; a six-second nod that
            # starts inside one sentence and finishes inside the next is not overrunning
            # anything. Measured against the SENTENCE — which is what the paragraph-era
            # version did, and sentences are a third the length — almost no clip ever
            # fitted and the episode came out with NINE clips in thirteen minutes.
            room = 1e9 if at_end else seg["to_s"] - abs_at
            # 🔴 THE DENSITY FLOOR (Jodie, 16 Sep — the rule that replaced §8's
            # retired R1 cap). §8's precedence can legitimately produce NOTHING for a
            # long run: every rule that fires names a bed, or a constraint refuses the
            # clip. On EP49 that left 47.1s and 43.1s of unbroken listening, which is
            # the one a viewer feels. So when the listener has been still for nearly the
            # ceiling, the neutral "still with you" gestures are ADDED to whatever §8
            # asked for — never replacing it, so a rule that did fire still wins.
            if floor_on:
                # EVERY punctuation code is offered, in a "least loaded first" order —
                # R10 last because a lean-in away from a handover promises a cut that is
                # not coming. A first version offered only four and `_pick` refused all
                # of them (no repeat on one man, no reuse within 90s), so the floor
                # fired and changed nothing: a guard that cannot act is decoration.
                cands = cands + [c for c in FLOOR_ORDER if c not in cands]
                if not whys:
                    why = (f"nothing in §8 asked for a clip and "
                           f"{listen_since:.0f}s of listening have passed \u2014 the "
                           f"density floor ({PUNCT_GAP_MAX_S:.0f}s) puts one in.")
            elif listen_since + at < PUNCT_SPACING_S and not at_end:
                cands = []
            mine = {k[1]: v for k, v in recent.items() if k[0] == listener}
            r = _pick(cands, mine, abs_at, last_for.get(listener), r7_used,
                      room) if cands else None
            if r:
                recent[(listener, r)] = abs_at
                last_for[listener] = r
                r7_used += (r == "R7")
                listen_since = -at
                punct.append({"at_s": round(abs_at - seg["from_s"], 1), "r": r,
                              "_why": why})
            t += u["est_s"]
            listen_since += u["est_s"]

        seg["reaction"] = {"bed": bed, "bed_chain": chain, "punct": punct,
                           "_bed_why": (
                               f"{listener} is listening through a figure-dense stretch, "
                               f"so the bed is R11 (concentrating)." if dense else
                               f"{listener}'s next turn {relation} "
                               f"(“{opens[:60]}…”), so the bed is {bed}.")}
    return segs


# ───────────────────────────────────────────────────────────── what went wrong ──

def punct_intervals(segs: list[dict]) -> tuple[list[float], float]:
    """(gaps between clips in LISTENING time, total listening time).

    The listening clock runs only while a two-box is on screen. A gap is measured from
    the start of listening to the first clip, between consecutive clips, and from the
    last clip to the end — so a dead opening and a dead ending both count.
    """
    marks, clock = [], 0.0
    for s in segs:
        if s["layout"] != "two-box":
            continue
        for p in (s.get("reaction") or {}).get("punct", []):
            marks.append(clock + p["at_s"])
        clock += s["dur_s"]
    edges = [0.0] + sorted(marks) + [clock]
    return [round(b - a, 2) for a, b in zip(edges, edges[1:])], round(clock, 2)


def long_picture_runs(segs: list[dict]) -> list[dict]:
    """Runs of ONE uninterrupted picture longer than A10's 35s ceiling.

    Under RULE 1 the ceiling cannot be enforced by returning to the two-box, so this is
    what is left: measure the runs and say so. A `single` segment between two graphics
    IS one picture; a card or a b-roll ends the run because it changes the picture.
    """
    out = []
    for s in segs:
        if s["layout"] == "full" and s["kind"] == "single" \
                and s["dur_s"] > SINGLE_MAX_S:
            out.append({"from_s": s["from_s"], "to_s": s["to_s"],
                        "dur_s": s["dur_s"], "turn": s["turn"],
                        "speaker": s["speaker"]})
    return out


def two_box_runs_per_turn(segs: list[dict]) -> dict:
    """How many separate two-box appearances each turn has.

    🔴 THE TEST RULE 1 IS WRITTEN AGAINST (Jodie's own): within a turn the two-box
    appears AT MOST TWICE — the head, and the handover. Counted from the SEGMENTS, which
    is what a viewer sees, and not from the intent that produced them.
    """
    out: dict = {}
    for s in segs:
        out.setdefault(s["turn"], []).append(s["layout"])
    return {t: sum(1 for i, l in enumerate(ls)
                   if l == "two-box" and (i == 0 or ls[i - 1] != "two-box"))
            for t, ls in out.items()}


def two_box_runs(segs: list[dict]) -> list[dict]:
    """Every CONTIGUOUS run of two-box, merged across turn boundaries.

    What a viewer sees at a handover is one shot: the last of this turn and the first
    sentence of the next, both two-box. The segment list splits it in two because
    segments are per turn, so a floor measured on segments fires on shots that are long
    enough — and squeezes real content to satisfy a number about nothing.
    """
    runs = []
    for s in segs:
        if s["layout"] != "two-box":
            continue
        if runs and abs(runs[-1]["to_s"] - s["from_s"]) < 0.02:
            runs[-1]["to_s"] = s["to_s"]
            runs[-1]["dur_s"] = round(runs[-1]["to_s"] - runs[-1]["from_s"], 2)
            if s["turn"] not in runs[-1]["turns"]:
                runs[-1]["turns"].append(s["turn"])
        else:
            runs.append({"from_s": s["from_s"], "to_s": s["to_s"],
                         "dur_s": s["dur_s"], "turns": [s["turn"]]})
    return runs


def picture_states(segs: list[dict]) -> list[dict]:
    """The timeline as a VIEWER sees it: contiguous runs of one unchanging picture.

    🔴 THIS IS THE UNIT THE DWELL LAW IS MEASURED IN, and it is not the segment. The
    plan splits a two-box at a turn boundary because the SPEAKER field changes, but the
    picture does not change at a handover — both men are on screen before it and after
    it, and what a viewer sees is one shot. Two consecutive single segments of the same
    speaker are likewise one shot.

    What DOES end a state: the two-box becoming a single or the reverse, a card or a
    clip taking the frame, a different card, and the speaker changing while full frame.
    """
    out: list[dict] = []
    for s in segs:
        if s["layout"] == "two-box":
            key = ("two-box", None)
        elif s.get("card"):
            key = ("card", s["card"])
        elif s.get("broll"):
            key = ("broll", s["broll"])
        else:
            key = ("single", s["speaker"])
        if out and out[-1]["key"] == key \
                and abs(out[-1]["to_s"] - s["from_s"]) < 0.02:
            out[-1]["to_s"] = s["to_s"]
            out[-1]["dur_s"] = round(out[-1]["to_s"] - out[-1]["from_s"], 2)
            out[-1]["segs"].append(s["n"])
            if s["turn"] not in out[-1]["turns"]:
                out[-1]["turns"].append(s["turn"])
        else:
            out.append({"key": key, "kind": key[0], "ident": key[1],
                        "from_s": s["from_s"], "to_s": s["to_s"],
                        "dur_s": round(s["to_s"] - s["from_s"], 2),
                        "segs": [s["n"]], "turns": [s["turn"]]})
    return out


def short_states(segs: list[dict]) -> list[dict]:
    """Every picture state under the dwell law. Empty is the only acceptable answer."""
    return [st for st in picture_states(segs) if st["dur_s"] < MIN_DWELL_S - 0.001]


def _blame(segs: list[dict], st: dict) -> str | None:
    """Which graphic to move so this short state stops being short.

    🔴 WHICH ONE DEPENDS ON WHICH SIDE THE STATE IS SQUEEZED FROM, and getting it
    backwards makes the loop oscillate instead of converge:

    · a short gap BEFORE a graphic is widened by pushing THAT GRAPHIC later;
    · a short gap AFTER a graphic, running into the handover, is CLOSED by pushing the
      graphic later too — until it ends inside the handover window and the gap stops
      existing at all. A stub of single before the two-box comes home is not a shot.

    Both remedies push later, so the graphic that FOLLOWS is asked first and the one
    before it second.
    """
    nums = st["segs"]
    after = next((s for s in segs if s["n"] == nums[-1] + 1), None)
    if after and (after.get("card") or after.get("broll")):
        return after.get("card") or after.get("broll")
    before = next((s for s in segs if s["n"] == nums[0] - 1), None)
    if before and (before.get("card") or before.get("broll")):
        return before.get("card") or before.get("broll")
    if st["ident"]:
        return st["ident"]       # the short state IS a graphic
    return None


def plan_with_dwell(beats: list[dict], broll_durs: dict[str, float] | None = None,
                    card_holds: dict[str, float] | None = None,
                    max_rounds: int = 80) -> tuple[list[dict], list[str]]:
    """`derive_plan` under the MINIMUM DWELL LAW. Returns (segments, what it did).

    🔴 A FIXED POINT, NOT A PREDICTION — and that is the design, not an implementation
    detail. Working out in advance which placements would leave a state under five
    seconds means writing the planner's rules down a SECOND TIME, inside the placer,
    where they start drifting from the first copy the moment either side changes
    (fault #2). So: place, derive, MEASURE THE REAL PLAN, and if any state is short,
    push the graphic responsible one sentence and derive again. The planner is its own
    oracle and the two cannot disagree.

    It terminates because every round either delays a graphic — bounded by the number of
    sentences in its turn — or drops one, bounded by the number of graphics.

    ⚠️ A DROP IS A REPORTABLE EVENT, NOT A SILENT ONE. The log says which graphic, out
    of which turn, and why nothing in that turn could hold it.
    """
    delays: dict[str, int] = {}
    dropped: set = set()
    reasons: dict = {}      # 🔴 the drops, kept ACROSS rounds — see `_place_graphics`
    segs, log = [], []
    for _ in range(max_rounds):
        log = []
        segs = derive_plan(beats, broll_durs, card_holds, delays=delays,
                           dropped=dropped, place_log=log, reasons=reasons)
        short = short_states(segs)
        if not short:
            return segs, list(reasons.values()) + log
        st = short[0]
        who = _blame(segs, st)
        if who is None:
            kind, dur, frm = st["kind"], st["dur_s"], st["from_s"]
            log.append(
                f"UNFIXABLE: a {kind} of {dur:.1f}s at {frm:.0f}s is under the dwell "
                f"law and no graphic borders it, so there is nothing to move. This is "
                f"a fault in the WALK, not in the placement.")
            return segs, list(reasons.values()) + log
        delays[who] = delays.get(who, 0) + 1
    return segs, list(reasons.values()) + log + [
        f"GAVE UP after {max_rounds} rounds. Report this; do not ship a plan that did "
        f"not settle."]


def violations(segs: list[dict]) -> list[str]:
    """Where the rules and this article do not fit. REPORTED, never silently smoothed."""
    out = []
    gaps, listening = punct_intervals(segs)
    n = sum(len((s.get("reaction") or {}).get("punct", [])) for s in segs)
    if n and listening:
        mean = listening / n
        if mean > PUNCT_MEAN_INTERVAL_MAX_S:
            out.append(f"the listener moves once every {mean:.1f}s of listening — the "
                       f"rule is one clip per {PUNCT_MEAN_INTERVAL_MAX_S:.0f}s "
                       f"({n} clips across {listening:.0f}s).")
    if gaps and max(gaps) > PUNCT_GAP_MAX_S:
        out.append(f"{max(gaps):.1f}s of unbroken listening with no reaction clip — the "
                   f"ceiling is {PUNCT_GAP_MAX_S:.0f}s.")
    singles = [s for s in segs if s["kind"] == "single"]
    # 🔴 THE FLOOR IS ABOUT THE SHOT, SO IT IS MEASURED ON THE CONTIGUOUS RUN. A
    # handover is one two-box that spans the turn boundary — the tail of this turn and
    # the opening sentence of the next — and measuring the two halves separately
    # complains about a shot that is plainly long enough.
    for r in two_box_runs(segs):
        if r["dur_s"] < TWO_BOX_MIN_S:
            out.append(f"two-box of {r['dur_s']:.1f}s at {r['from_s']:.0f}s "
                       f"(turn{'s' if len(r['turns']) > 1 else ''} "
                       f"{', '.join(str(t) for t in r['turns'])}) — under the "
                       f"{TWO_BOX_MIN_S:.0f}s floor.")
    for s in segs:
        if s["kind"] == "single" and s["dur_s"] > SINGLE_MAX_S and not FEWER_CUTS:
            # Under RULE 1 this is reported by long_picture_runs() below instead: the
            # walk no longer chooses a single's length, so a breach here has no legal
            # remedy and a failure with no remedy is a failure nobody can act on.
            out.append(f"single of {s['dur_s']:.1f}s at {s['from_s']:.0f}s — over the "
                       f"{SINGLE_MAX_S:.0f}s HARD ceiling.")
        if s["kind"] == "broll" and not (BROLL_DUR_MIN_S <= s["dur_s"]
                                         <= BROLL_DUR_MAX_S):
            out.append(f"b-roll {s['broll']} is {s['dur_s']:.1f}s — outside the "
                       f"{BROLL_DUR_MIN_S:.0f}–{BROLL_DUR_MAX_S:.0f}s rule.")
    # 🔵 THE ADJACENT-LENGTH CHECK IS ABOUT CHOSEN LENGTHS. It guarded the cycle of
    # targets: two singles the walk SET to the same length read as a pattern. Under
    # RULE 1 nothing sets them — a single is the gap between two graphics — so a
    # coincidence of length is not the fault this was written for.
    for a, b in (zip(singles, singles[1:]) if not FEWER_CUTS else []):
        if abs(a["dur_s"] - b["dur_s"]) < ADJACENT_SINGLE_GAP_S:
            out.append(f"adjacent singles {a['dur_s']:.1f}s and {b['dur_s']:.1f}s are "
                       f"within {ADJACENT_SINGLE_GAP_S:.0f}s — identical ones are the "
                       f"tell.")
    for turn in sorted({s["turn"] for s in segs}):
        ts = [s for s in segs if s["turn"] == turn]
        if ts[0]["layout"] != "two-box":
            out.append(f"turn {turn} opens on a {ts[0]['kind']} — A10 rule 4 wants the "
                       f"first sentence in the two-box.")
        if ts[-1]["layout"] != "two-box":
            out.append(f"turn {turn} hands over from a {ts[-1]['kind']} — A10 rule 4 "
                       f"wants the last ~{HANDOVER_TAIL_S:.0f}s in the two-box.")
    brolls = [s for s in segs if s["kind"] == "broll"]
    if not (BROLL_SLOTS_MIN <= len(brolls) <= BROLL_SLOTS_MAX):
        out.append(f"{len(brolls)} b-roll slots — the rule is "
                   f"{BROLL_SLOTS_MIN}–{BROLL_SLOTS_MAX} an episode.")
    if len({s["dur_s"] for s in brolls}) <= 1 and len(brolls) > 1:
        out.append("every b-roll slot is the same length — the rule says vary them.")
    # RULE 1's named cost, REPORTED. A run over the ceiling is not a hard fail: the only
    # way to cut it would be the timer-driven return to two-box that Rule 1 removes.
    for r in long_picture_runs(segs):
        out.append(f"REPORTED (Rule 1): one picture held {r['dur_s']:.0f}s "
                   f"({r['from_s']:.0f}-{r['to_s']:.0f}s, {r['speaker']} in turn "
                   f"{r['turn']}), over A10's {SINGLE_MAX_S:.0f}s ceiling. Rule 1 "
                   f"forbids the mid-turn return that used to cap it; the fix is a "
                   f"graphic in the gap, not a cut.")
    # ⚰️ "AT MOST TWO TWO-BOXES PER TURN" IS RETIRED (Jodie, 18 Sep 2026). It was the
    # mechanical form of v4's Rule 1 — leave the two-box once and never come back — and
    # the revision is precisely that the two-box DOES come back, after 25-35s of single,
    # when nothing else wants the frame. A third appearance is now the rule WORKING.
    # What replaces it checks what made the old rule worth having: that a return is
    # EARNED by a real single, never taken by a timer.
    states = picture_states(segs)
    if FEWER_CUTS:
        for k, st in enumerate(states):
            if k == 0 or st["kind"] != "two-box":
                continue
            prev = states[k - 1]
            # A single running into the HANDOVER is not a mid-turn return; the return
            # is the one that happens with the turn still going, so the two states
            # share a turn and no boundary sits between them.
            if prev["kind"] != "single" or st["turns"] != prev["turns"]:
                continue
            # 🔴 AND NEITHER IS THE TURN'S CLOSING TWO-BOX. A10 rule 3 requires the
            # picture home at least RETURN_BEFORE_TURN_END_S before a turn ends, so the
            # last two-box of a turn is the rule being KEPT, not a return taken early.
            # On every turn but the last, that shot spans the handover and carries two
            # turn numbers, so the test above already skipped it — which is exactly why
            # this went unnoticed until an episode was planned to its END. EP49's final
            # turn has no next turn to share with, and a correct closing shot was
            # reported as a broken rule.
            turn_end = max(s["to_s"] for s in segs if s["turn"] in st["turns"])
            if st["to_s"] >= turn_end - 0.01:
                continue
            if prev["dur_s"] < MID_RETURN_MIN_S - 0.001:
                at, held = st["from_s"], prev["dur_s"]
                out.append(
                    f"RULE 1 BROKEN: the two-box returns at {at:.0f}s after only "
                    f"{held:.1f}s of single — a mid-turn return is earned by "
                    f"{MID_RETURN_MIN_S:.0f}-{MID_RETURN_MAX_S:.0f}s on the speaker.")

    # RULE 1 AS REVISED HAS ITS OWN COST AND IT IS THE MIRROR OF v4's. v4 left the
    # two-box and never came back, so the SINGLES ran long. v5 comes home and stays
    # home, so a turn with no graphic left in it holds the TWO-BOX for as long as it
    # takes. Reported, never failed — the fix is a graphic in the gap, not a cut.
    for r in two_box_runs(segs):
        if r["dur_s"] > TWO_BOX_REPORT_S:
            held, at = r["dur_s"], r["from_s"]
            turns = ", ".join(str(x) for x in r["turns"])
            out.append(
                f"REPORTED (Rule 1 as revised): the two-box holds {held:.0f}s "
                f"unbroken from {at:.0f}s (turn {turns}), over the "
                f"{TWO_BOX_REPORT_S:.0f}s report line. Nothing is asking for the frame "
                f"— the remedy is a graphic in that gap, not a timed cut.")

    # 🔴 THE MINIMUM DWELL LAW — THE HARD ONE. Measured on contiguous picture states,
    # because a handover is one shot that the segment list happens to split in two.
    for st in short_states(segs):
        name = st["ident"] or st["kind"]
        held, at = st["dur_s"], st["from_s"]
        turns = ", ".join(str(x) for x in st["turns"])
        out.append(f"DWELL LAW BROKEN: {name} holds only {held:.1f}s at {at:.0f}s "
                   f"(turn {turns}) — no picture state lives under "
                   f"{MIN_DWELL_S:.0f}s.")

    # 🔴 RULE 1, TURN START: no two-box -> single -> card triple at the head of a turn.
    # A card due in a turn's opening lands DIRECTLY from the two-box. Checked by asking
    # what picture preceded each turn's FIRST graphic; under the old behaviour it was a
    # single, and three pictures went by in the first few seconds of the turn.
    for turn in sorted({s["turn"] for s in segs}):
        opens = min((s["from_s"] for s in segs if s["turn"] == turn), default=None)
        firsts = [k for k, st in enumerate(states)
                  if st["kind"] in ("card", "broll") and turn in st["turns"]]
        if opens is None or not firsts or firsts[0] == 0:
            continue
        prev = states[firsts[0] - 1]
        if prev["kind"] == "single" and prev["from_s"] >= opens - 0.02:
            ident = states[firsts[0]]["ident"]
            out.append(
                f"RULE 1 BROKEN (turn start): turn {turn} opens two-box, pushes to a "
                f"single, and only then brings up {ident}. A graphic due in a turn's "
                f"opening lands DIRECTLY from the two-box — the picture must not "
                f"change three times in the first few seconds of a turn.")
    return out


def tally(segs: list[dict]) -> dict:
    total = sum(s["dur_s"] for s in segs)
    by = {k: sum(s["dur_s"] for s in segs if s["kind"] == k)
          for k in ("two-box", "single", "card", "broll")}
    beds: dict[str, float] = {}
    punct: dict[str, int] = {}
    bare = 0.0
    for s in segs:
        if not s.get("reaction"):
            continue
        beds[s["reaction"]["bed"]] = beds.get(s["reaction"]["bed"], 0.0) + s["dur_s"]
        for p in s["reaction"]["punct"]:
            punct[p["r"]] = punct.get(p["r"], 0) + 1
        covered = sum(CLIP_S.get(p["r"], 6.0) for p in s["reaction"]["punct"])
        bare += max(0.0, s["dur_s"] - covered)
    listening = by["two-box"]
    # ⚠️ §8's "R1 ≤ ~60% OF LISTENING TIME" HAS TWO READINGS NOW, AND NEITHER IS
    # OBVIOUSLY THE ONE IT MEANT. It was written when R1 was one of twelve
    # interchangeable clips; in the new library the listener is on a BED one hundred
    # per cent of the time, so:
    #   `r1_share`      — listening time carrying NO clip at all (R1 = "nothing is
    #                     happening"), and
    #   `neutral_share` — time on the two NEUTRAL beds R1a/R1b, against R11
    #                     (concentrating) which is not neutral.
    # Both are reported and NEITHER is tuned toward. Choosing bed codes to move a number
    # is the R3a scar exactly: a metric you can move by editing a label is not a metric.
    neutral = sum(v for k, v in beds.items() if k in ("R1a", "R1b"))
    return {"total_s": total, **{f"{k}_s": v for k, v in by.items()},
            "listening_s": listening, "bed_only_s": bare,
            "r1_share": (bare / listening) if listening else 0.0,
            "neutral_share": (neutral / listening) if listening else 0.0,
            "beds_s": beds, "punct_n": punct}


# ─────────────────────────────────────────────────────────────────── the step ──

DERIVED = ("listener", "layout", "_layout_why", "reaction", "_reaction_why",
           "transition_ms")
"""🔒 `speaker` is NOT in here. It comes from `turns.json` — the article's own labels —
so it is data, not a derivation."""


def apply(epj: dict) -> dict:
    """Re-derive every two-way field IN PLACE, and return it.

    🔒 IDEMPOTENT ON PURPOSE. Everything derived is thrown away and recomputed from
    `beats[].card`, `beats[].broll`, the b-roll durations and `turn_signals`, so running
    it twice is a no-op and running it after a card moves gives the layout that card now
    implies. That is what "derived, never authored" has to mean in practice: nothing a
    human typed into these keys can survive, so nobody is tempted to type into them.
    """
    beats = epj["beats"]
    speakers = list(epj["speakers"])
    signals = {int(s["turn"]): s for s in epj.get("turn_signals", [])}
    durs = {b["target"]: float(b["dur_s"]) for b in epj.get("broll", [])
            if b.get("dur_s")}
    # The card HOLDS, so a card's segment in the plan is its real on-screen length
    # rather than its whole beat — see `_split_forced`. Without this the plan and the
    # assembler would disagree about how long every card is up.
    holds = {k: float(v) for k, v
             in ((epj.get("build") or {}).get("holds") or {}).items()}
    for b in beats:
        for k in DERIVED:
            b.pop(k, None)
    # 🔴 THE PLAN COMES THROUGH THE DWELL LAW, NOT ROUND IT. `derive_plan` is still the
    # derivation; `plan_with_dwell` is that derivation run to a fixed point under the
    # 5s floor, moving a graphic rather than shortening a shot.
    segs, place_log = plan_with_dwell(beats, durs, card_holds=holds)
    epj.setdefault("build", {})["_layout_placement"] = place_log
    derive_reactions(segs, speakers, signals)

    # The beat keeps a SUMMARY so the file still reads beat by beat; the segment list is
    # the authoritative timeline, and `layout` on a beat that changes inside it says so
    # rather than picking a winner.
    for b in beats:
        mine = [s for s in segs if b["n"] in s["beats"]]
        kinds = {s["layout"] for s in mine}
        b["listener"] = _other(b["speaker"], speakers)
        b["layout"] = (mine[0]["layout"] if len(kinds) == 1 else "mixed") if mine \
            else "two-box"
        b["_layout_why"] = ("; ".join(dict.fromkeys(s["_why"] for s in mine))
                            if mine else "")
        b["transition_ms"] = PUSH_MS
    epj["layout_plan"] = [{k: v for k, v in s.items() if k != "_units"} for s in segs]
    return epj
