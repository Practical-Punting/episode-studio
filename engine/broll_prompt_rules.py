"""The b-roll standing lines, as something a machine can check. **EP24 ONWARD.**

WHY THIS IS CODE AND NOT ONLY A DOC
-----------------------------------
`docs/broll-registry.md` has carried the standing shot template since 5 Aug 2026, and
the template WORKED — EP23's prompts carry the stride line and the silks line in every
racing shot, because whoever wrote them read the file. Then EP23 shipped with horses on
both sides of the running rail.

    THE REGISTRY IS NOT THE FAULT. A rule a human has to remember to type is obeyed
    until the day a new rule is added and the old file is read from memory instead.

So the standing lines live HERE, once, and the b-roll step asks this module rather than
asking a person to have remembered. `docs/broll-registry.md` keeps the reasoning and the
evidence — which is the half a machine cannot hold — and this keeps the words.

🚫 THIS IS NOT A B-ROLL REVIEW STEP, AND MUST NEVER BECOME ONE. Jodie, 5 Aug 2026:
*"We do not want a step to approve the b-roll… We will just add a few more rules over
time."* Nothing here asks for a human judgement about a picture. It reads text, before a
credit is spent, and says which sentence is missing from which prompt. **The only route
is the prompts** — this is that route, mechanised.

⚠️ EP24 ONWARD, AND EP23 IS NOT TOUCHED. EP23 is published. `FROM_EP` is a NUMBER and not
a "does the file look new" test, so re-running an older episode for any other reason
cannot suddenly halt it on wording nobody had written yet.
"""
from __future__ import annotations

import re

# Hugh's ruling, EP23, 14 Aug 2026. Earlier episodes are published and are not re-graded.
FROM_EP = 24

# ── what makes a shot a RACING shot ─────────────────────────────────────────────
# Asked of the prompt, not listed per clip: a registry of clip names would be a list
# somebody maintains, and the next racing clip added would be graded as a kitchen table.
# (`broll-ratings-pencil-and-weights` is EP23's non-racing clip and must stay exempt.)
#
# 🔴 IT ASKS FOR HORSES, NOT FOR A RACECOURSE — corrected 14 Aug 2026 on EP24, and the
# correction matters more since these rules started AUTO-APPLYING.
# The first version also matched `racecourse`, `race day`, `straight`, `barrier` and
# `furlong` — words that describe a VENUE. EP24's `broll-glamour-raceday-crowd` is a shot
# of people on the lawn with no horse in it, and it was graded as a racing shot and told
# to add jockeys' silks and out-of-phase strides.
#     WHEN THE ONLY CONSEQUENCE WAS A HALT THAT WAS NOISE. NOW IT WOULD WRITE HORSES INTO
#     A SHOT OF A CROWD, which is a worse clip than the one the rule exists to prevent.
# A rule may only be applied to a shot it is actually about.
HORSE_WORDS = re.compile(
    r"\b(racehorse|racehorses|horse|horses|field of|gallop\w*|runner|runners"
    r"|jockey|jockeys|mounted|thoroughbred\w*)\b", re.I)


def has_horses(prompt: str) -> bool:
    """A galloping / field shot — the shots the rail and rider rules are about."""
    return bool(HORSE_WORDS.search(prompt or ""))


# Kept as the older name; `has_horses` is what it always meant.
is_racing_shot = has_horses


# ── COVER AND RACING-HERO ORIENTATION ───────────────────────────────────────────
#
# 🔴 EP24's COVER B CAME BACK UPSIDE DOWN. (Jodie, 14 Aug 2026.)
# The A/B pick caught it, as it is designed to — but the pick is a SAFETY NET, and a net
# that has to be used is a net being relied on. One of the two options was wasted, and had
# both been wonky the choice would have been between two unusable covers.
#
# ⚠️ NOT A NEGATION. "Not upside down" cannot be drawn: a model must place a horizon
# somewhere, and if it is not told where, it will put it anywhere. The line says where
# everything GOES — sky up, turf down, horizon level and central, camera at eye level —
# which is the same reasoning as the rail's "open green turf infield beyond it" (A21).
ORIENTATION = ("Correct upright orientation — horizon level and near the middle, sky at "
               "the top, green turf and track at the bottom, camera at eye level; horses "
               "upright and running along the ground")
ORIENTATION_NEEDS = [r"upright orientation", r"horizon level", r"sky at the top",
                     r"horizon .{0,20}(level|middle|centre|center)"]

# ── FAULT 6, THE LIGHT ──────────────────────────────────────────────────────────
#
# 🔴 EP26's IMAGES CAME BACK TOO DARK. (Jodie, 15 Aug 2026.) A "man at a desk" card was
# discarded for nothing but being dim and murky — the composition was right, the picture
# was unusable, and the credit was spent.
#
# ⚠️ THIS ONE IS UNIVERSAL, AND THAT IS THE WHOLE POINT OF WHERE IT LIVES. Every other
# rule in this file is about horses, a rail or a crowd, so every other rule is gated on
# the shot containing one. **The light is a property of every generated image** — the
# cover, the racing wides, and the indoor desk scene that has no horse in it and would
# be skipped by every gate below. So it sits in UNIVERSAL, not in RULES.
#
# ⚠️ NOT A NEGATION — the same reasoning as ORIENTATION, and it matters more here. A
# model cannot draw "not dark": it has to choose an exposure, and told nothing it chooses
# the safe middle, which prints murky. The line says what the light IS, and names the
# indoor case explicitly because "golden hour" means nothing at a desk.
LIGHTING = (
    "Bright, warm and luminous light, generously exposed and richly cinematic — a low "
    "dramatic late-afternoon sun, long warm golden-hour light and a warm sunset glow "
    "through the scene; an indoor, desk or portrait scene is warmly and generously lit, "
    "warm sunlight through a window and lamp-warm highlights, the subject bright and "
    "clearly visible")
# Any ONE of these says the fact. "Bright natural daylight" is deliberately NOT enough:
# it is what the cover brief already said while EP26 came back dim, and a pattern that
# the failing prompts already match is a rule that changes nothing.
LIGHTING_NEEDS = [r"golden.?hour", r"late.?afternoon sun", r"low,? dramatic sun",
                  r"warm (golden |afternoon |sunset )?light", r"sunset glow",
                  r"warmly (and generously )?lit", r"luminous", r"generously exposed",
                  r"lamp.?warm", r"warm sunlight through a window"]

# ── FAULT 7, THE RUNNING RAIL'S LINE ────────────────────────────────────────────
#
# 🔴 EP26's RAIL HAD AN UNNATURAL KINK. (Jodie, 15 Aug 2026.)
# This EXTENDS A21/Fault 4 rather than repeating it: that rule says the field is all on
# ONE SIDE of the rail. This one says the rail is a smooth, true line. A rail can be
# perfectly one-sided and still jag.
#
# ⚠️ CURVES ARE CORRECT AND EXPECTED — a real racecourse is an oval. The fault is an
# abrupt kink, and "no kinks" is unrenderable, so the line describes the line the rail
# SHOULD trace: continuous, evenly posted, level along the top.
#
# ⚠️ AND IT IS SHOT-AWARE, for A21's second finding: a straight line pasted into a bend
# is the incoherent geometry this whole family of faults grows in. Two variants, and
# NEITHER contains "dead straight" or "perfectly level" — those two phrases are what
# STRAIGHT_RAIL looks for, and injecting one into a bend shot would manufacture the very
# contradiction the checker halts on.
RAIL_SMOOTH_STRAIGHT = (
    "the white running rail is one clean unbroken line running true and even along the "
    "track, evenly spaced upright posts and a level top rail")
RAIL_SMOOTH_BEND = (
    "the white running rail is one clean unbroken line that follows the track in a "
    "single smooth even sweeping curve, evenly spaced upright posts and a level top rail")
# The FACT is smoothness and regularity, so a prompt that already says it in its own
# words passes. Deliberately NOT satisfied by "a single white running rail" — that is the
# A21 rail-side line, and letting it count here would mean this rule never fires.
RAIL_SMOOTH_NEEDS = [r"unbroken line", r"continuous line",
                     r"smooth[^.]{0,30}(curve|sweep)", r"sweeping curve",
                     r"level top rail", r"evenly[ -]spaced[^.]{0,20}post",
                     r"true and even"]

# 🔴 ON A BEND, ONLY THE CURVE WORDING WILL DO. (Jodie's law, 16 Aug 2026.)
# The list above is satisfied by "true and even along the track" — which is right for a
# straight and says nothing about a shot that bends. A bend shot has to state the SWEEP
# positively, because that is the whole instruction: the rail follows the track in one
# long, smooth, even curve. Saying only "unbroken" leaves the model to choose the line,
# and the line it chooses when it is not told is the one that kinked.
RAIL_CURVE_NEEDS = [r"smooth[^.]{0,30}(curve|sweep)", r"sweeping curve",
                    r"curves? with the track", r"follows the track[^.]{0,40}curve"]


def rail_smooth_for(text: str) -> str:
    """The smoothness line in the form THIS shot can be — curve wording only on a bend."""
    return RAIL_SMOOTH_BEND if BEND_WORDS.search(text or "") else RAIL_SMOOTH_STRAIGHT


# 🔴 A RULE MAY ONLY BE APPLIED TO A SHOT IT IS ACTUALLY ABOUT — and this rule is about a
# RAIL, not about a horse. FOUND BY THE CONTROL, ON A REAL COVER, BEFORE ANY TEST WAS
# WRITTEN, which is the only reason it was found at all.
#
# EP26's cover hero A is a man at a desk with FRAMED RACING PHOTOGRAPHS on the wall behind
# him. It mentions racehorses, jockeys and galloping — so `has_horses` is true, correctly
# — and it ends with:
#
#     "NO FENCE, NO RUNNING RAIL AND NO RAILINGS anywhere in the photograph or inside
#      any of the framed pictures."
#
# Gated on horses, this rule appended "The white running rail is one clean unbroken
# line…" to a prompt that had just spent a clause excluding one. **That is not a missing
# line, it is a contradiction** — the same fault `_BEYOND_NON_TURF` exists to refuse, and
# a worse picture than the kink it was written to prevent.
#
# So the gate is: DOES THIS PICTURE HAVE A RAIL IN IT. Not "is there a horse", and not a
# plain search for the word — the word is present in that cover, three times, every one
# of them inside a negation.
RAIL_WORDS = re.compile(r"\brail(?:s|ing|ings)?\b", re.I)
_NEGATED = re.compile(r"\b(no|without|never|not)\b", re.I)


def shows_a_rail(prompt: str) -> bool:
    """True when the picture actually contains a running rail.

    Every mention of the rail is examined, and one that sits inside a NEGATION does not
    count — "no running rail anywhere" is a prompt saying there is no rail, however many
    times the word appears in it. The look-back stops at a sentence boundary so a
    negation about something else, a clause earlier, cannot suppress a real rail.
    """
    for m in RAIL_WORDS.finditer(prompt or ""):
        back = (prompt or "")[max(0, m.start() - 60):m.start()]
        back = back[back.rfind(".") + 1:]          # this sentence only
        if not _NEGATED.search(back):
            return True                            # an affirmative rail: the rule applies
    return False

# ── the standing lines ──────────────────────────────────────────────────────────
# Each rule is (key, human name, what it must SAY, why it exists). `needs` is a list of
# alternatives — any ONE satisfies it — so a prompt may phrase a line in its own words
# without the check demanding a copy-paste. The point is that the FACT is stated, not
# that a sentence is duplicated.
RULES = [
    # 🔴 ORIENTATION IS ONE OF THESE, AND IT WAS NOT. (14 Aug 2026, the day after A22.)
    # A22 was landed into `providers._cover_prompts` — the cover A/B funnel — and that
    # worked: EP25's two hero prompts both carry the line. **But the RACING B-ROLL
    # prompts go through `apply_rules`, which is a different funnel, and all six of
    # EP25's still had no orientation at all.** The ruling says "cover_a, cover_b AND
    # the racing hero prompts"; two of the three were covered.
    #
    # ⚠️ SO THE RULE WAS RIGHT, LIVE, AND PROVED — ON ONE OF THE TWO PATHS. A guard
    # installed at one funnel says nothing about the other, and the tell is that A22's
    # own test passed the whole time. It is a first-class rule here now, so
    # `check_prompt`, `apply_rules`, the re-check and `check_episode` all see it and
    # there is no second path to keep in step.
    dict(
        key="orientation",
        name="which way up the picture goes",
        needs=ORIENTATION_NEEDS,
        why=("EP24's cover B came back UPSIDE DOWN. A model has to put the horizon "
             "somewhere, and told nothing it puts it anywhere. Stated positively — "
             "sky at the top, turf at the bottom, horizon level, horses upright."),
    ),
    dict(
        key="rail-side",
        name="the whole field on ONE side of the rail",
        needs=[r"one side of (a|the|a single) .{0,30}rail",
               r"all on the same side of the .{0,20}rail",
               r"the (whole )?field .{0,40}(on|to) one side"],
        why=("EP23 shipped with horses on BOTH SIDES of the running rail (Hugh, "
             "14 Aug 2026). Five of six prompts NAMED the rail and not one said which "
             "side the horses go, so the model drew the rail and filled both sides."),
    ),
    dict(
        key="rail-beyond",
        name="what lies BEYOND the rail (open turf infield)",
        needs=[r"(open|empty) .{0,20}(turf|grass|infield)",
               r"infield beyond", r"beyond it,? (open|empty)"],
        why=("The positive half is the half that works. A model must render SOMETHING "
             "beyond the rail; unless the far side is given a job it reaches for the "
             "subject the rest of the prompt describes — a horse."),
    ),
    dict(
        key="strides",
        name="horses out of step with one another",
        needs=[r"different point.{0,20}stride", r"out of phase", r"staggered stride"],
        why="EP16 at 1:25 — every horse in identical rhythm, hooves landing together.",
    ),
    dict(
        key="silks",
        name="Australian racing silks on every rider",
        needs=[r"silks?\b"],
        why=("EP16 at 8:11 — tweed jackets and flat caps on an Australian provincial "
             "race day. 'Mounted' is not a costume instruction."),
    ),
    dict(
        key="turf",
        name="lush green Australian turf",
        needs=[r"(green|lush).{0,20}turf", r"turf.{0,20}(course|racecourse|track)"],
        why="These models default to American dirt. Say turf every time.",
    ),
    dict(
        key="anatomy",
        name="anatomically correct horses",
        needs=[r"anatomic\w*", r"four legs", r"no fused"],
        why=("The HARD-FAIL list. An extra or fused limb is not 'invisible at speed' — "
             "these get caught and rejected, after the credit is spent."),
    ),
]

# ── THE UNIVERSAL TIER — asked of EVERY generated image, whatever is in it ───────
#
# 🔴 EVERYTHING IN `RULES` IS GATED ON THE SHOT CONTAINING A HORSE, and that is right for
# every rule that was in it: a kitchen table needs no silks. **The light is not like
# that.** EP26's discarded card was a man at a desk — no horse, no crowd, no rail — and
# it would be skipped by every gate in this file. A rule that only reaches racing shots
# would have missed the exact picture that caused it.
#
# This is the third tier, beside RULES (horses) and CROWD_RULE (people). Adding one here
# means it applies to the covers, the racing wides, the crowd shots and the desk scenes
# alike — which is what "every generated image" has to mean if it is to mean anything.
UNIVERSAL = [
    dict(
        key="lighting",
        name="bright, warm, generously exposed light",
        needs=LIGHTING_NEEDS,
        why=("EP26's images came back too DARK (Jodie, 15 Aug 2026) and a 'man at a "
             "desk' card was discarded for nothing but being dim and murky. A model "
             "cannot draw 'not dark' — told nothing it picks the safe middle, which "
             "prints murky. State the light positively, and name the indoor case, "
             "because 'golden hour' means nothing at a desk."),
    ),
]

# ── THE CONDITIONAL TIER — a rule with its own question about the shot ───────────
# `RULES` asks "are there horses", `CROWD_RULE` asks "are there people". Fault 7 asks a
# third question — "is there a rail" — and it has to be its own, because the two are not
# the same picture: an empty-track wide shot has a rail and no horses, and EP26's desk
# cover has horses (in framed photographs) and explicitly no rail. Each rule carries the
# question it is entitled to be applied on.
CONDITIONAL = [
    dict(
        key="rail-smooth",
        name="the rail as one smooth, true, evenly-posted line",
        needs=RAIL_SMOOTH_NEEDS,
        # THE SHOT DECIDES WHAT SATISFIES IT — a bend must say it SWEEPS.
        needs_for=lambda p: (RAIL_CURVE_NEEDS if BEND_WORDS.search(p or "")
                             else RAIL_SMOOTH_NEEDS),
        when=shows_a_rail,
        why=("EP26's running rail had an unnatural KINK (Jodie, 15 Aug 2026). This "
             "EXTENDS the one-side rule rather than repeating it: a rail can be "
             "perfectly one-sided and still jag. Curves are correct and expected — a "
             "racecourse is an oval — so the line describes the line the rail should "
             "trace, because 'no kinks' cannot be drawn."),
    ),
]

# THE FRAME RULES — the ones that describe the PICTURE rather than the horses in it, and
# so the ones a portrait cover hero takes. This is the list the cover funnel asks for;
# see apply_frame_rules() at the foot of this file. Keys, not copies, so there is exactly
# one definition of each line and both funnels read it.
FRAME_KEYS = ("lighting", "orientation", "rail-smooth")

# ══ FAULT 8 — FRAME THE PORTRAIT HERO SO THE 16:9 CROP LANDS ON THE HORSES ═══
# (Jodie, 18 Aug 2026, after E32. Her answer to "why is the hero portrait at all".)
#
# The cover heroes are generated PORTRAIT because the e-book cover is portrait; the
# title card and the thumbnail then crop 16:9 out of the same picture. On EP30 that
# window missed the field BY TEN PIXELS, twice, and both were caught by her eye.
#
# 🔴 THE CHEAPER FIX IS NOT A SECOND IMAGE — IT IS FRAMING THE ONE WE HAVE. And the
# arithmetic says the middle third is almost exactly right. On EP30's 1696×2528 hero:
#     · a 16:9 window is 954px — 37.7% of the image height;
#     · at the DEFAULT `center` it sees 31.1%–68.9% of the frame;
#     · the middle third is 33.3%–66.7% — INSIDE that, with ~2 points of margin
#       top and bottom.
# So a field framed to the middle third lands in the default window with room to spare,
# and needs no per-episode `hero_focus` at all. (EP30's field sat at 69.3%–83.0% — wholly
# below the window, which is the miss.) Stated POSITIVELY, like every rule here.
#
# ⚠️ THIS IS A PROMPT RULE, SO IT HOLDS PROBABILISTICALLY. It improves the odds that the
# crop is right by construction; it does NOT close the case, and nobody may report it as
# having done so — the same footing as the rail and stride lines, which were in EP30's
# prompt in positive form on all four clips and still came back wrong once.
#     THE PAIRING IS THE POINT: this makes the good crop likely, and `crop_report` in
# providers.py shows a human the measurement when it was not.
#
# 🔴 AND IT IS A **COVER** RULE ONLY — DELIBERATELY NOT IN `RULES`.
# The first version of this put it in RULES, where `check_prompt` grades every b-roll
# prompt, and the suite went red on 28 cases: every racing clip was told it was missing
# a line, and a human would have been halted over it on every episode. **B-roll clips
# are delivered 16:9 already and are never cropped out of a portrait picture** — the
# whole fault is about a PORTRAIT COVER HERO that two 16:9 cards crop from. A rule may
# only be applied to the thing it is actually about (the same correction HORSE_WORDS
# needed when it graded a shot of a crowd as a racing shot).
MIDDLE_THIRD_NEEDS = [r"middle third", r"centre third", r"center third"]
MIDDLE_THIRD = ("the field of horses fills the MIDDLE THIRD of the frame, with open sky "
                "above them and turf below, so a 16:9 crop through the middle of the "
                "picture lands on the horses")

# Only where the clip actually contains a crowd — demanding hat colours of a head-on
# gallop would be noise, and a guard everyone ignores is worse than no guard.
# ⚠️ `grandstand` WAS IN HERE AND IS NOT A CROWD. It is a building, and it stands in the
# background of wide course shots with nobody in them — EP24's
# `broll-metropolitan-circuit-wide-sweep` was told to name hat colours for a crowd it does
# not contain. PEOPLE WORDS ONLY.
CROWD_WORDS = re.compile(r"\b(crowd|crowds|spectator\w*|punter\w*|onlooker\w*|people"
                         r"|men and women|racegoer\w*)\b", re.I)
CROWD_RULE = dict(
    key="hat-variety",
    name="hats in a VARIETY of natural colours",
    # "a RANGE of natural colours" is the same requirement in the other common wording,
    # and EP24 already said it. Demanding one synonym over another is asking for a
    # copy-paste, not for the fact. (The registry itself says "a VARIETY"; both pass.)
    needs=[r"(variety|range|mix) of .{0,25}colours", r"varied .{0,20}(hats|colours)",
           r"no two neighbours alike"],
    why=("EP18 — sixteen people along the rail and every hat the same pale cream. "
         "A model fills a crowd by repeating ONE thing; uniformity is its default."),
)

# ══ THE LAW ON THE RAIL'S SHAPE, WRITTEN HERE BECAUSE HERE IS WHERE IT IS ENFORCED ══
# (Jodie, 16 Aug 2026, on EP27's halt. Embedded, not referenced: a rule that lives in a
# doc and is enforced in code is two rules, and the doc is the one that goes stale.)
#
#   REAL RACING TRACKS CURVE. A rail is WRONG only when it has an abrupt KINK, jag,
#   zig-zag, wobble or warp.
#
#   · On a BEND — "turning for home", "rounding the turn" — the white running rail
#     follows the track as a single clean continuous line that SWEEPS in a long, smooth,
#     even curve.
#   · On a STRAIGHT it runs straight.
#   · NEVER force "dead straight", "straight and true" or "perfectly level" onto a shot
#     that bends.
#
# A bend and a dead-straight rail cannot both be true. EP23 asked for both, twice; EP27
# asked for both again in different words, and THAT is the fault below.
BEND_WORDS = re.compile(r"\b(bend|turn for home|home turn|turning for home|curv\w*|"
                        r"rounding)\b", re.I)

# 🔴 ONE PATTERN, READ BY BOTH THE DETECTOR AND THE REMOVER. (EP27, 16 Aug 2026.)
# This is what halted EP27, and it is fault #2 in its purest form — two descriptions of
# the same thing, drifted apart:
#
#     detector: re.compile(r"dead straight|perfectly level", re.I)   ← flexible, any case
#     remover:  re.sub(r"\s*dead straight and perfectly level\s*",…) ← ONE literal, CASE
#                                                                      SENSITIVE, joined
#                                                                      by the word "and"
#
# EP27's prompt says "a single DEAD STRAIGHT, PERFECTLY LEVEL white running rail" — upper
# case, comma-joined. **The detector fired and the remover could not find a thing that was
# certainly there**, so the tool reported "the phrase could not be located to remove" and
# halted a human over a phrase it was staring at.
#
# The claims are now listed ONCE. `STRAIGHT_RAIL` finds them and `_STRAIGHT_RUN` removes
# them, and both are built from `_STRAIGHT_CLAIMS`, so a new wording cannot be detectable
# and unremovable at the same time.
_STRAIGHT_CLAIMS = (r"dead[- ]straight", r"perfectly level", r"straight and true",
                    r"dead[- ]level", r"perfectly straight", r"absolutely straight",
                    r"ruler[- ]straight")
_CLAIM = "(?:" + "|".join(_STRAIGHT_CLAIMS) + ")"
STRAIGHT_RAIL = re.compile(r"\b" + _CLAIM + r"\b", re.I)

# A RUN of them — "DEAD STRAIGHT, PERFECTLY LEVEL", "dead straight and perfectly level" —
# taken out together with the connector between them, because removing them one at a time
# leaves the "and" or the comma stranded and the sentence reads like a mistake. Trailing
# comma swallowed too, so "a single DEAD STRAIGHT, PERFECTLY LEVEL white rail" comes back
# as "a single white rail" and not "a single , white rail".
_STRAIGHT_RUN = re.compile(
    r"\s*\b" + _CLAIM + r"\b(?:\s*(?:,|and|&|,\s*and)\s*\b" + _CLAIM + r"\b)*\s*,?\s*",
    re.I)


def strip_straight_claims(text: str) -> tuple[str, list[str]]:
    """Remove every "dead straight"-family claim. Returns (text, what was removed).

    Best-effort AND VERIFIED: the caller re-checks, so a claim this cannot remove cleanly
    still reaches a human rather than being generated. What it must never do again is
    fail to find one it can see.
    """
    found = [m.group(0) for m in STRAIGHT_RAIL.finditer(text or "")]
    if not found:
        return text, []
    out = _STRAIGHT_RUN.sub(" ", text)
    # Tidy what the removal leaves behind, so the prompt reads like a sentence. These
    # are read by a person as often as by a model when somebody is working out why a
    # clip came back wrong, and a prompt that reads like a mistake gets treated as one.
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r",\s*,", ",", out)
    out = re.sub(r"\s+\.", ".", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out, found


def check_prompt(prompt: str) -> list[dict]:
    """Every standing line this prompt fails to state. Empty list = nothing to say."""
    out = []
    # THE UNIVERSAL TIER FIRST, and unconditionally. A prompt with no horses, no crowd
    # and no rail still has a light in it, and EP26's discarded desk card is why that
    # sentence had to be written down. Every other rule below stays gated on the shot
    # actually being about the thing the rule is about (the HORSE_WORDS note).
    rules = list(UNIVERSAL)
    if has_horses(prompt):
        rules += RULES                 # a kitchen table is not a racing shot
    if CROWD_WORDS.search(prompt or ""):
        rules.append(CROWD_RULE)       # …and a crowd shot needs its hats, horses or not
    # …and a rule that carries its own question answers it here. One place, so a new
    # conditional rule cannot be added and then forgotten by one of the three callers.
    rules += [r for r in CONDITIONAL if r["when"](prompt or "")]
    if not (prompt or "").strip():
        return []                      # nothing to grade; an empty prompt is a different fault
    for r in rules:
        # `needs_for` lets a rule ask a DIFFERENT question of a different shot — the rail
        # on a bend must say it sweeps, where the same rail on a straight need only say
        # it is unbroken and evenly posted. One rule, one key, one fix; the shot decides
        # what counts as stating it.
        pats = r["needs_for"](prompt) if r.get("needs_for") else r["needs"]
        if not any(re.search(p, prompt, re.I) for p in pats):
            out.append({"key": r["key"], "name": r["name"], "why": r["why"]})
    # THE CONTRADICTION, which is its own fault and not a missing line.
    if BEND_WORDS.search(prompt) and STRAIGHT_RAIL.search(prompt):
        out.append({
            "key": "straight-rail-on-a-bend",
            "name": 'a "dead straight" rail in a shot that bends',
            "why": ("EP23 sent 'dead straight and perfectly level' into two bend shots — "
                    "a standing line pasted in unconditionally, contradicting the shot "
                    "around it. On a bend the rail curves with the track and the field "
                    "stays outside it. Asking for a straight rail on a bend is asking "
                    "for incoherent geometry, which is the soil this fault grows in."),
        })
    return out


# ── APPLYING, RATHER THAN ASKING ────────────────────────────────────────────────
#
# 🔴 A HALT HERE IS NOT A DECISION, SO IT MUST NOT BE A HALT. (Jodie, 14 Aug 2026.)
# EP24 stopped at the credit check because six prompts were missing standing lines. The
# machine knew WHICH lines, and it knew the exact words — they are in this file — and it
# stopped to ask a human to copy them in. That is a chore wearing a decision's clothes,
# and it is the same argument as the auto-WIDE and auto-broll-offset rulings: when the
# lawful answer is already computed, apply it and say what was changed.
#
#     AND A HALT WAS ACTIVELY WORSE THAN NOISE HERE. `_broll_prompt` is per clip, so it
#     reported ONE clip when SIX were short — six halts, one at a time, each needing a
#     human to clear it before the next appeared.
#
# ⚠️ WHAT IT MAY NOT DO IS INVENT THE SHOT. It appends the standing FACTS every racing
# shot must state; it never writes the subject, the framing or the action. And it applies
# a rule only to a shot the rule is about — see the HORSE_WORDS note above, which is the
# fault this feature would otherwise have shipped: writing jockeys into a crowd shot.
FIXES = {
    "rail-side": None,          # handled with rail-beyond, in one sentence
    "rail-beyond": None,
    "strides": ("each horse at a different point of its stride, staggered strides, "
                "hooves landing at different moments, legs out of phase across the field"),
    "silks": ("jockeys up and crouched in the irons, actively riding, in bright and "
              "varied Australian racing silks and matching caps, white or cream breeches, "
              "black riding boots, safety helmets with the silk cover on"),
    "turf": "lush green Australian turf",
    "anatomy": ("anatomically correct horses — four legs, one head, no fused or extra "
                "limbs"),
    "hat-variety": ("Akubra-style hats in a variety of natural colours — fawn, sand, tan, "
                    "brown, grey, black, olive — worn at different angles, no two "
                    "neighbours alike"),
    # A22, and the one line the cover funnel shares with this one. Stated POSITIVELY —
    # see the note by ORIENTATION: "not upside down" cannot be drawn.
    "orientation": ORIENTATION,
    # Fault 8 — see MIDDLE_THIRD. A prompt rule, so it improves the odds and does not
    # close the case; crop_report() is what shows a human when it did not work.
    "middle-third": MIDDLE_THIRD,
    # Fault 6. Universal, so this is the one fix that can land on a prompt with no horse
    # in it. Stated positively for the same reason as orientation.
    "lighting": LIGHTING,
    # Fault 7 is SHOT-AWARE and so cannot be a constant here — see rail_smooth_for().
    "rail-smooth": None,
}

# The rail sentence depends on the shot, which is the whole point of A21's second finding:
# a straight line pasted into a bend is what produced the incoherent geometry.
# 🔴 THE TRAILING NEGATION IS GONE, AND THE SENTENCE MOVED TO THE FRONT.
# (EP30, 18 Aug 2026 — and this is the SECOND time these two faults have shipped.)
#
# EP30 came back with horses on both sides of the rail AND the field in identical
# stride, and BOTH rules were in the sent prompt, in positive form, on all four clips.
# So the rules did not fail to be written and they did not fail to be applied: the
# model did not follow them on one clip in four. Three of the four were correct, which
# is the part worth saying out loud — **this is a rule that holds probabilistically,
# not a rule that is missing.** No wording gets that to 100%.
#
# What we changed, because it is free and it is the only lever that costs nothing:
#   · the sentence ENDED on "no horses on the far side" — a negation carrying the very
#     words it forbids (horses / far side). It is dropped. What is beyond the rail is
#     already stated positively, and a positive statement of the same fact is what the
#     b-roll brief has asked for since 14 Aug: *"Name what must be true rather than
#     what must not. Negative prompts are less reliable than positive statements."*
#   · it was appended into a pile of ~2,400 characters of constraint, roughly 60% of
#     the way through. It now goes IN THE SCENE, straight after the opening shot
#     sentence, which is where the brief says the racing situation belongs.
#
# ⚠️ AND NOBODY MAY CLAIM THIS WORKED. At 6.5 clips an episode it would take 15–30
# episodes per arm to tell a 25% fault rate from 15%. This is a free change made on
# principle, not a measured fix, and the tally (docs/broll-fault-tally.md) is the only
# thing that will ever turn it into a number.
RAIL_STRAIGHT = ("the whole field running on ONE side of a single white running rail — "
                 "the rail is the inside boundary of the track, open green turf infield "
                 "beyond it")
RAIL_BEND = ("the whole field running on ONE side of a single white running rail — on "
             "this bend the rail curves with the track and the field stays outside it, "
             "the rail is the inside boundary of the track with open green turf infield "
             "beyond it")


# 🔴 A COMPETING CLAIM ABOUT WHAT IS BEYOND THE RAIL IS A HUMAN'S CALL.
# EP24's `broll-metropolitan-circuit-wide-sweep` already said the rail had "a grandstand
# and gum trees beyond". Appending "open green turf infield beyond it" left the prompt
# asserting TWO different far sides — and that is not a missing line, it is a
# contradiction, which is the exact soil A21 says this fault grows in. It also has a real
# answer that depends on the shot: a far-side rail is the OUTSIDE boundary and a
# grandstand beyond it is correct, so the tool cannot know which claim to keep.
# It stops and says so. That is the halt worth having.
_BEYOND_NON_TURF = re.compile(
    r"\b(grandstand|stands?|building\w*|car ?park|house\w*|road|fence|trees?|scrub|"
    r"hill\w*|marquee\w*|tent\w*|crowd\w*)\b[^.]{0,40}\bbeyond\b"
    r"|\bbeyond\b[^.]{0,40}\b(grandstand|stands?|building\w*|car ?park|house\w*|road|"
    r"trees?|marquee\w*|tent\w*|crowd\w*)\b", re.I)


def _add_sentence(text: str, clause: str) -> str:
    """Append a clause as a PROPER SENTENCE.

    The first version did `text + ". " + clause`, which left the prompt reading
    "…no repeated framing. the whole field running on ONE side…" — a lower-case fragment
    hanging off the end. These strings are read by a person as often as by a model when
    somebody is working out why a clip came back wrong, and a prompt that reads like a
    mistake gets treated as one.
    """
    return text.rstrip(". ") + ". " + clause[0].upper() + clause[1:] + "."


def _add_sentence_early(text: str, clause: str) -> str:
    """Put a clause IN THE SCENE — straight after the opening shot sentence.

    The rail fact is a fact about the picture, not one of the trailing production
    constraints, and the b-roll brief says so: *"State the racing situation first."*
    Appended at the end it sat ~60% of the way through 2,400 characters of constraint,
    behind the anatomy line, the no-text line and the not-a-painting line.

    The FIRST sentence still leads, because that is the shot itself — putting the rail
    before "Photoreal cinematic side-on shot of…" would describe a rail before saying
    there is a picture. Falls back to appending if there is no sentence break to find,
    so a one-sentence prompt is never silently left without the rule.
    """
    body = text.rstrip()
    cut = body.find(". ")
    if cut == -1:
        return _add_sentence(text, clause)
    head, tail = body[:cut + 1], body[cut + 2:]
    return f"{head} {clause[0].upper() + clause[1:]}. {tail}"


def apply_rules(prompt: str) -> tuple[str, list[str], list[str]]:
    """Add every standing line this prompt is missing.

    Returns (new_prompt, applied, unfixable). `unfixable` is what a human still has to
    look at — kept deliberately, because a tool that claims to fix everything is one
    nobody checks.
    """
    gaps = {g["key"] for g in check_prompt(prompt)}
    if not gaps:
        return prompt, [], []
    text = prompt.rstrip()
    applied, unfixable = [], []
    bend = bool(BEND_WORDS.search(text))

    # Before touching anything: is the far side already spoken for by something that is
    # not turf? Then the rail clause is a contradiction, not an addition.
    if gaps & {"rail-side", "rail-beyond"} and _BEYOND_NON_TURF.search(text):
        m = _BEYOND_NON_TURF.search(text)
        return prompt, [], [
            "this prompt already says what lies beyond the rail "
            f'("…{m.group(0).strip()}…"), and the standing line says open green turf '
            "infield. Two different far sides is a contradiction, and which one is right "
            "depends on the shot — a FAR-SIDE rail is the outside boundary and a "
            "grandstand beyond it is correct, while an inside rail must have empty "
            "infield beyond it. Decide which rail this is and write that one clause."]

    # 1. THE CONTRADICTION FIRST, because it is a REWRITE and the rail sentence added
    #    below has to agree with what is left behind.
    #
    # 🔴 THE REMOVER IS THE DETECTOR'S OWN PATTERN NOW (EP27, 16 Aug 2026). It used to be
    # a case-sensitive literal — "dead straight and perfectly level" — while the detector
    # was case-insensitive and matched either half. EP27 said "DEAD STRAIGHT, PERFECTLY
    # LEVEL", so the check fired and the fix could not find a phrase that was plainly
    # there. See the note by _STRAIGHT_CLAIMS.
    if "straight-rail-on-a-bend" in gaps:
        fixed, removed = strip_straight_claims(text)
        if removed and not STRAIGHT_RAIL.search(fixed):
            text = fixed
            applied.append("removed " + ", ".join(f'"{r}"' for r in removed)
                           + " — the shot bends, and a bend is not a fault")
        else:
            # It is still worth halting when the claim survives the removal, and the
            # message now QUOTES what it found rather than naming a phrase that may not
            # be the one in the prompt.
            unfixable.append(
                'a "dead straight" rail in a shot that bends — found '
                + ", ".join(f'"{r}"' for r in (removed or ["it"]))
                + ", and it could not be removed cleanly")

    # 2. The rail sentence, in the form this shot can actually be — placed EARLY, in
    #    the scene, rather than appended to the constraint pile. See RAIL_STRAIGHT.
    if gaps & {"rail-side", "rail-beyond"}:
        text = _add_sentence_early(text, RAIL_BEND if bend else RAIL_STRAIGHT)
        applied.append("the field runs on ONE side of the rail, with open green turf "
                       "infield beyond it" + (" (bend wording)" if bend else ""))

    # 2b. The rail's LINE, which is a different claim from which side the field is on.
    #
    # 🔴 RE-ASKED HERE, AGAINST THE UPDATED TEXT, AND NOT READ OFF `gaps`. The gaps were
    # computed before step 2 ran, and step 2 may have just INTRODUCED the rail — a racing
    # prompt that never mentioned one is given "…a single white running rail…" and only
    # then has a rail whose line can be wrong. Read off the stale `gaps`, this rule never
    # fired on exactly those prompts, and the re-check at the foot of this function
    # reported "rail-smooth — still missing after auto-apply", which is the tool telling
    # a human to do something the tool could do. Caught by the existing auto-inject
    # tests, which is what they are for.
    if any(g["key"] == "rail-smooth" for g in check_prompt(text)):
        text = _add_sentence(text, rail_smooth_for(text))
        applied.append("the rail is one smooth, true, evenly-posted line"
                       + (" (bend wording)" if BEND_WORDS.search(text) else ""))

    # 3. Everything else is a fact appended in the registry's own words.
    # `orientation` and `lighting` LAST, because they are statements about the whole
    # frame and read as the closing instruction rather than as one more fact about the
    # horses. Lighting last of all: it is the only one that lands on every picture.
    for key in ("strides", "silks", "turf", "anatomy", "hat-variety", "orientation",
                "lighting"):
        if key in gaps and FIXES.get(key):
            text = _add_sentence(text, FIXES[key])
            applied.append(FIXES[key][:60] + "…")

    # 4. RE-CHECK. If applying the rules did not satisfy the rules, the tool is wrong and
    #    must say so rather than quietly generating a clip that breaks them — the one
    #    thing genuinely worth a human here.
    left = {g["key"] for g in check_prompt(text)}
    for key in sorted(left):
        unfixable.append(f"{key} — still missing after auto-apply")
    return text, applied, unfixable


# ── COVER AND RACING-HERO ORIENTATION ───────────────────────────────────────────
# The rule itself now lives in RULES, at the top, so ONE definition serves the b-roll
# funnel (`apply_rules`) and the cover funnel (`providers._cover_prompts`). These two
# helpers are the cover funnel's door into it — the covers are portrait stills and do
# not take the rail, silks or strides lines, so they ask for this rule alone.


def needs_orientation(prompt: str) -> bool:
    """True when a racing image does not say which way up it is.

    ⚠️ ASKED OF `check_prompt`, NOT OF A SECOND COPY OF THE PATTERNS. It used to test
    ORIENTATION_NEEDS itself, which was the same list read twice — and while that was
    true it was also the only thing that knew about orientation, so the b-roll path
    never gained it. One reader, one rule.
    """
    return any(g["key"] == "orientation" for g in check_prompt(prompt or ""))


def apply_orientation(prompt: str) -> tuple[str, bool]:
    """Add the orientation line if it is missing. Returns (prompt, changed).

    ⚠️ KEPT, AND NARROW. `apply_frame_rules` is what the cover funnel calls now — this
    remains because it says one thing and says it plainly, and a caller that genuinely
    wants only the orientation line should not have to ask for three.
    """
    if not needs_orientation(prompt):
        return prompt, False
    return _add_sentence(prompt.rstrip(), ORIENTATION), True


def apply_frame_rules(prompt: str) -> tuple[str, list[str]]:
    """Add every FRAME rule this image prompt is missing. Returns (prompt, applied).

    🔴 THIS IS THE DOOR THE COVER FUNNEL COMES THROUGH, and it is deliberately the SAME
    definitions the b-roll funnel uses — FRAME_KEYS names keys, and the words come from
    UNIVERSAL/RULES/FIXES. A22's whole lesson was that a guard installed at one funnel
    says nothing about the other; the answer is not to install it twice, it is to have
    one set of words with two doors onto it.

    Why the covers take these three and not the rest: a portrait cover hero is a still,
    and the strides / silks / rail-side lines are about a field of horses in motion.
    Orientation, the light and the rail's own line are properties of the PICTURE, which
    is what a cover is.
    """
    gaps = {g["key"] for g in check_prompt(prompt or "")} & set(FRAME_KEYS)
    if not gaps:
        return prompt, []
    text, applied = (prompt or "").rstrip(), []
    # Same order as apply_rules, and for the same reason: the rail is a fact about the
    # scene, orientation and the light are statements about the whole frame.
    if "rail-smooth" in gaps:
        text = _add_sentence(text, rail_smooth_for(text))
        applied.append("the rail is one smooth, true, evenly-posted line")
    for key in ("orientation", "lighting"):
        if key in gaps and FIXES.get(key):
            text = _add_sentence(text, FIXES[key])
            applied.append({"orientation": "the upright-orientation line",
                            "lighting": "the bright, warm lighting line"}[key])
    # Fault 8 — asked HERE and not through `gaps`, because this rule is about a PORTRAIT
    # COVER HERO and must never be graded against a b-roll clip. See MIDDLE_THIRD.
    # Gated on horses: a cover of a man at a desk has no field to put in the middle third.
    if has_horses(text) and not any(re.search(p, text, re.I) for p in MIDDLE_THIRD_NEEDS):
        text = _add_sentence(text, MIDDLE_THIRD)
        applied.append("the field in the MIDDLE THIRD, so a 16:9 crop lands on it")
    return text, applied


def check_episode(broll: list[dict], ep_number: int | None) -> list[str]:
    """Human-readable findings for one episode's `broll[]`. Empty = clean.

    Returns SENTENCES, not codes: whatever halts on this has to be fixable by the person
    reading it, and 'rail-side' tells them nothing (docs/PP-operator-box-rule.md).
    """
    if ep_number is None or ep_number < FROM_EP:
        return []                      # EP23 and earlier are published; not re-graded
    findings = []
    for b in broll or []:
        gaps = check_prompt(b.get("prompt") or "")
        for g in gaps:
            findings.append(f"{b.get('target', '?')} — needs {g['name']}.\n"
                            f"      why: {g['why']}")
    return findings
