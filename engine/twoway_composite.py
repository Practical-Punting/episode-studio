#!/usr/bin/env python3
"""The two-box composite — build spec §6. DESIGN-AGNOSTIC BY CONSTRUCTION.

    python engine/twoway_composite.py --proof <out_dir>

Everything the picture looks like lives in `assets/twoway/layout.json`; everything the
picture DOES lives here. Cowork is writing the visual design with `pp-motion-graphics`
loaded, and it drops in by replacing values in that file — not by editing this one.

🔴 **THAT SPLIT IS THE WHOLE POINT OF BUILDING IT NOW.** The mechanism can be proved on
coloured placeholder windows and synthetic audio, before a single frame of real footage
exists, and the design arrives later as data. The alternative — waiting for the design,
then writing the mechanism against it — puts both risks in the same week.

── WHAT THE MECHANISM OWES THE FORMAT ────────────────────────────────────────────────
· speaker's window at full brightness; listener's slightly darker and a touch smaller
· 🔴 each head anchored on the EYES, never the frame bottom. MEASURED from the render
  (`measure_eye_line`) — 53px of difference between two renders that were otherwise the
  same size, 23 Aug 2026
· eased PUSHES, 700-800ms, two-box↔single, the house cubic-beziers. 🚫 never a
  cross-dissolve and never a hard cut between these two layouts
· the listener's window fed from the reaction catalogue, or from the harvested idle pool
  when a code has no file yet — and the substitution SAID OUT LOUD in the run log
· no reaction clip reused within ~90s; beds chain, never loop
· ~0.5s of the next voice carried under the outgoing window at every join
· the PP logo in the frame furniture, below and outside both windows — never inside a
  presenter's panel, which would quietly make it his

📌 **BACKGROUNDS ARE STILLS, BAKED INTO THE HEYGEN TEMPLATES.** Nothing here handles
them: Barry's study and Brian's commentary box are uploaded once, not per episode.
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
import twoway_reactions as rx                                    # noqa: E402

LAYOUT = HERE.parent / ".claude/skills/pp-episode-production/assets/twoway/layout.json"
IDLE_REUSE_S = tb.NO_REUSE_WITHIN_S


class Unbuildable(Exception):
    """The composite cannot be built as specified. Nothing is rendered."""


def load_layout(path: pathlib.Path = LAYOUT) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    for k in ("canvas", "panels", "source", "listener", "speaker", "eyes",
              "grade", "chips", "logo", "push", "single", "audio"):
        if k not in d:
            raise Unbuildable(
                f"{path.name} has no `{k}` section. This file is the CONTRACT between "
                f"the design and the mechanism; a missing section means the design has "
                f"not said something the composite cannot invent.")
    for side in ("left", "right"):
        if len(d["panels"][side]["rect"]) != 4:
            raise Unbuildable(f"panels.{side}.rect must be [x, y, w, h].")
    # 🔴 THE LISTENER MUST BE DARKER THAN THE SPEAKER. Asserted as a RELATIONSHIP, never
    # as a pixel — if this fails when a new design lands, the design has broken a rule of
    # the format rather than moved a placeholder.
    if not (d["listener"]["brightness"] < d["speaker"]["brightness"]):
        raise Unbuildable(
            "listener.brightness must be below speaker.brightness — the dimming is how "
            "the picture says who is not talking.")
    # 🔴 THE KEYLINE IS ON BOTH PANELS, ALWAYS — AND THIS GUARD IS THE OLD ONE
    # INVERTED, NOT RELAXED. Until 18 Sep 2026 it raised if the LISTENER had a
    # keyline; Jodie's ruling is that the orange frame belongs to the two-box and not
    # to whoever is talking, so the same sentence now refuses the opposite mistake. A
    # rule that is withdrawn leaves a hole; a rule that is turned around does not.
    ks, kls = d["speaker"].get("keyline"), d["listener"].get("keyline")
    if not ks or not kls:
        raise Unbuildable(
            "BOTH panels wear the keyline (Jodie, 18 Sep 2026). A keyline on one panel "
            "only moves when the speaker changes, and a line that moves reads as a cut "
            "inside a shot that has not changed.")
    if ks != kls:
        raise Unbuildable(
            f"the two keylines differ ({ks} vs {kls}). It is one frame around two "
            f"panels, so it is one set of numbers — if they can drift they will.")
    if not (1 <= int(ks["width"]) <= 8):
        raise Unbuildable(
            f"keyline.width is {ks['width']}px — a line, not a border. Jodie rejected "
            f"'a huge frame with a whole lot of stuff' at the design stage.")
    # 🔴 THE PER-PRESENTER GRADE. Two HeyGen templates on two different sets do not
    # come back at the same exposure — Steve's face measured +11.2% over Gordon's on
    # the pair-test renders, and Jodie saw it as "the Steve side is a lot brighter".
    # Declared per presenter CODE so a third presenter cannot silently inherit a value
    # measured on somebody else's face.
    g = d["grade"]
    if not g.get("gamma"):
        raise Unbuildable("grade.gamma must name a gamma per presenter code.")
    for who, v in g["gamma"].items():
        if not (0.6 <= float(v) <= 1.6):
            raise Unbuildable(
                f"grade.gamma[{who}] is {v}. Outside 0.6-1.6 this is not a grade, it is "
                f"a re-light — and a face that has to be re-lit needs a new TEMPLATE, "
                f"the way the framing did.")
    # MEETING IN THE MIDDLE IS THE RULE, not lifting one man to the other: one gamma
    # must sit below 1.0 and one above, or somebody has been re-exposed to match a set
    # that was never the reference.
    vals = [float(v) for v in g["gamma"].values()]
    if len(vals) > 1 and not (min(vals) < 1.0 < max(vals)):
        raise Unbuildable(
            "grade.gamma lifts or trims every presenter the same way. The design says "
            "the two faces MEET IN THE MIDDLE — one trimmed, one lifted.")
    return d


# ─────────────────────────────────────────────────────────── the eye line ──

def measure_eye_line(path, at_s: float = 1.0) -> float | None:
    """Where this presenter's eyes sit, as a percentage of frame height.

    🔴 MEASURED FROM THE RENDER, NEVER ASSUMED. Two renders that were otherwise the same
    size differed by 53px (23 Aug 2026), and bottom-aligned that reads as one man
    sitting lower than the other.

    Returns None when there is no picture to measure — a synthetic proof, an audio-only
    master — and the caller then uses the layout's target rather than a wrong number.
    📌 A GUESS DRESSED AS A MEASUREMENT IS WORSE THAN AN HONEST DEFAULT.
    """
    import pp_paths
    probe = subprocess.run(
        [pp_paths.ffprobe() or "ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=height", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=120)
    if not (probe.stdout or "").strip().isdigit():
        return None
    # The real detector is a face-landmark pass on a frame at `at_s`. It is not built
    # here because there is no face to find yet: the proof runs on placeholder windows.
    # What IS built is the contract — a number or an honest None — so the composite is
    # already written against a measurement rather than a constant.
    return None


def eye_offsets(layout: dict,
                measured: dict[str, float | None] | None = None) -> dict[str, float]:
    """How far each panel's content shifts, IN PANEL PIXELS, so the eye lines agree.

    The target is the design's; the offsets are the difference each presenter's own
    measurement makes. An unmeasured presenter shifts by zero — the honest answer, and
    📌 A GUESS DRESSED AS A MEASUREMENT IS WORSE THAN AN HONEST DEFAULT.

    Measurements default to the ones recorded in the layout, so the common case reads
    the numbers somebody actually measured rather than re-deriving them.
    """
    eyes = layout["eyes"]
    target = eyes["target_in_panel"]
    ph = layout["panels"]["left"]["rect"][3]
    k = ph / layout["canvas"]["h"]          # 1080-space measurement -> panel space
    m = measured if measured is not None else eyes.get("measured_1080", {})
    return {c: (0.0 if v is None else round(v * k - target, 1)) for c, v in m.items()}


# ───────────────────────────────────────────────── the listener's window ──

def listener_plan(plan: list[dict], cat: dict, idle: list[dict], ep: str = "",
                  log: list | None = None) -> list[dict]:
    """What plays in the listener's window, for every two-box segment.

    Reads the reaction the COMMISSION already chose (`twoway_beats` wrote it, with its
    reason) and resolves it to files. 🔴 ASSEMBLY DECIDES NOTHING — it executes what was
    written down. That is build spec §8's architecture and the reason a wrong reaction
    is caught in a text file rather than discovered in a finished video.
    """
    log = log if log is not None else []
    pool = {s: [c for c in idle if c["speaker"] == s] for s in rx.SPEAKERS}
    used_at: dict[tuple, float] = {}
    turn_idx = {s: 0 for s in rx.SPEAKERS}
    out = []
    for seg in plan:
        if seg.get("layout") != "two-box" or not seg.get("reaction"):
            continue
        who = seg["listener"]
        r = seg["reaction"]
        bed = rx.resolve(cat, who, r["bed"], ep, seg.get("beats", [None])[0], log)
        # 🔴 NO FILE FOR THE BED YET -> THE HARVESTED PAUSE. It came from the same
        # render as the speaking footage, so it cannot mismatch it — the one thing a
        # separately rendered loop can never guarantee.
        if bed.get("substituted") and not bed.get("file") and pool[who]:
            clip = pool[who][turn_idx[who] % len(pool[who])]
            turn_idx[who] += 1
            bed = {"file": clip["file"], "duration_s": clip["dur_s"], "id": "IDLE",
                   "substituted": True, "asked": r["bed"]}
            log.append(f"REACTION SUBSTITUTED — {ep or 'episode ?'} "
                       f"{seg['from_s']:.1f}s: asked for {r['bed']} on {who}, played "
                       f"the harvested pause {clip['file']} (no bed rendered yet).")
        chain = []
        for hop in r.get("bed_chain", []):
            got = rx.resolve(cat, who, hop["to"], ep, seg.get("beats", [None])[0], log)
            chain.append({"at_s": hop["at_s"], "id": hop["to"],
                          "file": got.get("file"), "substituted": got.get("substituted")})
        punct = []
        for p in r.get("punct", []):
            at_abs = seg["from_s"] + p["at_s"]
            last = used_at.get((who, p["r"]))
            if last is not None and at_abs - last < IDLE_REUSE_S:
                log.append(f"REACTION DROPPED — {ep or 'episode ?'} "
                           f"{at_abs:.1f}s: {p['r']} on {who} was played "
                           f"{at_abs - last:.0f}s ago, inside the "
                           f"{IDLE_REUSE_S:.0f}s no-reuse window.")
                continue
            got = rx.resolve(cat, who, p["r"], ep, seg.get("beats", [None])[0], log)
            used_at[(who, p["r"])] = at_abs
            punct.append({"at_s": p["at_s"], "id": p["r"], "file": got.get("file"),
                          "duration_s": got.get("duration_s"),
                          "substituted": got.get("substituted"),
                          "ends_neutral": rx.ENDS_NEUTRAL.get(p["r"], True)})
        out.append({"from_s": seg["from_s"], "to_s": seg["to_s"], "listener": who,
                    "speaker": seg["speaker"], "bed": bed, "bed_chain": chain,
                    "punct": punct})
    return out


# ───────────────────────────────────────────────────────── the ffmpeg graph ──

def _r(rect):
    return [int(round(v)) for v in rect]


def grade_of(layout: dict, who: str) -> float:
    """This presenter's gamma. 🔴 ONE HOME, BECAUSE A GRADE THAT LIVES IN THE COMPOSITE
    IS A GRADE THE REST OF THE EPISODE DOES NOT GET.

    Until 22 Sep 2026 `eq=gamma` was written only inside `composite_graph`, so it
    reached the TWO-BOX and nothing else. Every full-frame shot in the episode — every
    single, the open, the CTA, the midroll, the close, the outro, the RG line, the
    sign-off — went out raw. Jodie: *"The lighting in the Barry Meadow videos changes.
    It's not the contrast between Gordon and Steve, it's the contrast between STEVE's
    scenes."*

    📏 MEASURED, same master frame down both paths, four samples each:
    Steve's face **149.46 ungraded, 143.59 graded — 3.9% darker in the two-box**;
    Gordon's **124.90 ungraded, 130.72 graded — 4.7% brighter**. Both men stepped
    brightness at every layout change, all episode.

    ❌ AND THE PROPOSED CAUSE WAS NOT IT. His speaking master and his two beds were
    measured over twelve samples each on the panel crop: **160.85 / 160.86 / 160.83**,
    faces 146.06 / 145.76 / 145.75. Three sources, 0.2% apart. Nothing was wrong with
    the beds; the grade simply was not being applied to five sixths of the episode.
    """
    return float((layout["grade"]["gamma"] or {}).get(who, 1.0))


def grade_filter(layout: dict, who: str) -> str:
    """The grade as a filter fragment, for the FULL-FRAME path. Same value, same name,
    so the two paths cannot drift — §2b: one definition, not a correction per reader."""
    return f"eq=gamma={grade_of(layout, who)}"


def composite_graph(layout: dict, side_of: dict[str, str], segs: list[dict],
                    offsets: dict[str, float] | None = None) -> str:
    """The ffmpeg filter graph for one run of segments. Returned as text, not run.

    Returning the graph rather than running it is deliberate: it can be ASSERTED. A
    composite that is only ever judged by looking at the output is a composite nobody
    can test — and this is the step where "it looked right on the one clip I watched"
    has the furthest to fall.
    """
    c = layout["canvas"]
    pan = layout["panels"]
    li, sp_l = layout["listener"], layout["speaker"]
    p = layout["push"]
    kl = layout.get("keyline") or sp_l["keyline"]
    parts = [f"color=c={c['background']}:s={c['w']}x{c['h']}:d=1[bg]"]
    for i, seg in enumerate(segs):
        sp, ls = seg["speaker"], seg["listener"]
        for who, role in ((sp, "speaker"), (ls, "listener")):
            rect = _r(pan[side_of[who]]["rect"])
            g = sp_l if role == "speaker" else li
            dy = round((offsets or {}).get(who, 0.0), 1)
            # 🔴 THE PANEL IS FILLED, NEVER PADDED. A full-height panel that is scaled
            # down and padded shows the background through the gap, which is the framed
            # look Jodie rejected. The content is cropped to fit and shifted by the
            # EYE OFFSET — the crop is what makes the anchor possible.
            # 🔴 TWO CHAINED eq FILTERS, NEVER ONE MERGED FILTER. The per-presenter
            # GRADE runs first and the speaker/listener state second, so the listener's
            # .84 is relative to the GRADED value — which is what "keep the listener dim
            # relative to the graded value" means. Merged into one eq the order would be
            # ffmpeg's to choose and the dim would be measured against the raw render.
            gam = grade_of(layout, who)
            parts.append(
                f"[{who.lower()}{i}]scale=-2:{rect[3]},"
                f"crop={rect[2]}:{rect[3]}:(iw-{rect[2]})/2:(ih-{rect[3]})/2+{dy},"
                f"eq=gamma={gam},"
                f"eq=brightness={round((g['brightness'] - 1) / 2, 4)}:"
                f"saturation={g['saturation']}[{role}{i}]")
        for role, who in (("speaker", sp), ("listener", ls)):
            r = _r(pan[side_of[who]]["rect"])
            prev = "bg" if role == "speaker" else f"s{i}"
            tag = f"s{i}" if role == "speaker" else f"box{i}"
            parts.append(f"[{prev}][{role}{i}]overlay={r[0]}:{r[1]}[{tag}]")
        # 🔴 THE KEYLINE, ON BOTH PANELS — LEFT THEN RIGHT, NOT SPEAKER THEN LISTENER.
        # Drawing them in PANEL order rather than in ROLE order means these two lines
        # of the graph are byte-identical whoever is talking, which is the mechanical
        # form of "the frame does not move". Assert it and the rule cannot rot.
        for j, sd in enumerate(("left", "right")):
            r = _r(pan[sd]["rect"])
            src = f"box{i}" if j == 0 else f"kl{i}"
            dst = f"kl{i}" if j == 0 else f"key{i}"
            parts.append(f"[{src}]drawbox=x={r[0]}:y={r[1]}:w={r[2]}:h={r[3]}:"
                         f"color={kl['colour']}:t={kl['width']}[{dst}]")
    parts.append(f"# push {p['duration_ms']}ms {p['easing_out']} "
                 f"— never a dissolve, never a hard cut")
    return ";\n".join(parts)


def push_spec(layout: dict, frm: str, to: str) -> dict:
    """One transition. 🔴 A PUSH, ALWAYS — the layouts never dissolve into each other."""
    p = layout["push"]
    if not (700 <= p["duration_ms"] <= 800):
        raise Unbuildable(
            f"push.duration_ms is {p['duration_ms']}ms and A10 rule 5 says ~700-800ms. "
            f"The house move is a specific speed; a slower one reads as a wipe and a "
            f"faster one as a cut.")
    return {"from": frm, "to": to, "kind": "push", "duration_ms": p["duration_ms"],
            "easing": p["easing_out"] if to == "single" else p["easing_in"]}


def chips_for(speakers: dict, layout: dict) -> dict[str, dict]:
    """The "reading …" chips, GENERATED from `speakers`, never typed (build spec A2).

    Three lines, not one sentence — the design sets them as a name, then "reading X",
    then the role: "GORDON / reading Brian Blackwell / editor, Practical Punting".

    🔴 FIRST MINUTE ONLY. It is an introduction, and an introduction that never leaves
    is a caption.
    """
    ch = layout["chips"]
    out = {}
    for code, s_ in speakers.items():
        rect = layout["panels"][s_["side"]]["rect"]
        out[code] = {
            "name": s_["reader"].upper(),
            "reading": s_["name"],
            "role": s_["role"],
            "x": rect[0] + ch["left"],
            "bottom_y": rect[1] + rect[3] - ch["bottom"],
            "visible_s": list(ch["visible_s"]),
            "move_ms": ch["move_ms"],
            "rule_colour": ch["rule"]["colour"],
            "listener_rule_colour": ch["rule"]["listener_colour"],
        }
    return out


# kept so older callers get a clear error rather than a silent absence
def supers_for(*_a, **_k):
    raise Unbuildable(
        "supers_for() is gone: the approved design has no furniture band and no title "
        "strip, so there are no supers to place. Use chips_for() — the lower-thirds now "
        "sit OVER the picture, inside each panel, for the first minute only.")
