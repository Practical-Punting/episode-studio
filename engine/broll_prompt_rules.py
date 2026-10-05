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

# ── DOES THE PICTURE ACTUALLY CONTAIN IT? ONE TEST, EVERY GATE ──────────────────
# 🔴 THREE GATES ASK THE SAME QUESTION AND ONLY ONE OF THEM KNEW HOW. (EP37, 23 Aug
# 2026.) `shows_a_rail` has ignored negated mentions since 15 August, because a cover
# saying "NO RUNNING RAIL" three times is a picture with no rail in it. `has_horses` and
# the crowd gate were plain searches, so "NO HORSES IN SHOT" read as horses and "no
# crowd" read as a crowd — and EP37 was told to add strides, silks and a spread of
# Akubras to a shot it had spent a clause emptying.
#     Teaching each gate its own negation handling would be three copies of one idea and
# a fourth gate along next month (#2b: unify the definition, do not teach one reader the
# other's cases). So the question is asked once, here, and every gate uses it.
_NEGATED = re.compile(r"\b(no|without|never|not)\b", re.I)


def _affirms(words: re.Pattern, prompt: str) -> bool:
    """True when the prompt AFFIRMS one of `words` — a mention inside a negation does
    not count. The look-back stops at a sentence boundary so a negation about something
    else, a clause earlier, cannot suppress a real one."""
    text = prompt or ""
    for m in words.finditer(text):
        back = text[max(0, m.start() - 60):m.start()]
        back = back[back.rfind(".") + 1:]          # this sentence only
        if not _NEGATED.search(back):
            return True
    return False


# 🔴 A RIDER IS NOT A HORSE. (EP37, 23 Aug 2026.) `HORSE_WORDS` counts `jockey`, and it
# is right to: a mounted jockey implies the animal, and the silks and anatomy lines are
# about the rider anyway. But a jockey walking a saddle across the enclosure is a shot
# with a rider and NO HORSE, and `strides` — "each horse at a different point of its
# stride… across the field" — was appended to a prompt that had just said "no horses".
# Auto-applied, silently, with no halt: the build would have gone on and PAID for a clip
# of a field of horses in an empty mounting yard.
#     So the stride rule asks the narrower question it is entitled to: are there
# actually HORSES, not merely somebody dressed to ride one.
HORSE_ANIMAL_WORDS = re.compile(
    r"\b(racehorse|racehorses|horse|horses|field of|gallop\w*|runner|runners"
    r"|mounted|thoroughbred\w*)\b", re.I)


def shows_actual_horses(prompt: str) -> bool:
    """True when the picture contains the ANIMAL, not just a rider."""
    return _affirms(HORSE_ANIMAL_WORDS, prompt)


def has_horses(prompt: str) -> bool:
    """A galloping / field shot — the shots the rail and rider rules are about.

    🔴 NEGATION-AWARE SINCE EP37 (23 Aug 2026), AND IT IS THE SAME TEST `shows_a_rail`
    HAS ALWAYS USED. This was a plain search, so "NO HORSES IN SHOT" counted as horses
    and EP37's crowd shot and its empty rain-on-the-track shot were both graded as
    field-of-horses shots — and told to add out-of-phase strides and silks.
    That is the HORSE_WORDS note's own warning arriving through the gate the note is
    attached to: *"NOW IT WOULD WRITE HORSES INTO A SHOT OF A CROWD, which is a worse
    clip than the one the rule exists to prevent."*
    """
    return _affirms(HORSE_WORDS, prompt)


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
ORIENTATION = ("Correct upright orientation — horizon level, sky at the top, turf at the "
               "bottom, camera at eye level, horses upright and running along the ground")
# 🔴 AND A PLAIN ONE FOR A HORSE THAT IS NOT RACING. (Jodie, 5 Oct 2026, EP55.) The line
# above landed on a horse standing in a stable yard and one led at a walk, and told the
# model about "turf and track at the bottom" and horses "running along the ground" — a
# track in a stable yard, and running in a walk. A horse off the track gets the frame
# facts only: level horizon, eye-level camera.
ORIENTATION_PLAIN = ("Correct upright orientation — horizon level, camera at eye level, "
                     "verticals upright and true")
# One ridden horse is "the horse", never "horses" — the same count rule as the rail line.
ORIENTATION_ONE = ORIENTATION.replace("horses upright", "the horse upright")
# 🔴 AND A VERSION FOR A PICTURE WITH NO HORSE IN IT. (EP37, 23 Aug 2026.)
# Orientation is UNIVERSAL — it lands on the desk shots, the TAB counter and the
# enclosure as well as the gallops — and the line above ends "horses upright and running
# along the ground". So the corrector wrote HORSES into a shot that had just said it had
# none, and then its own re-check read the prompt back as a horse shot and started asking
# for strides and equine anatomy. A fix that changes what the picture IS is not a fix.
#     Shot-aware, exactly as `rail_smooth_for` already is: same fact, said about whatever
# is actually in the frame.
ORIENTATION_NO_HORSES = ("Correct upright orientation — horizon level and near the "
                         "middle, sky at the top, ground at the bottom, camera at eye "
                         "level, verticals upright and true")


def orientation_for(text: str) -> str:
    """The orientation line in the form THIS shot can be: track, turf and running only for
    a ridden horse on a track; a plain frame line for a horse off it; and no horses at
    all where there are none."""
    t = text or ""
    # A jockey ON FOOT is "ridden" by the word list but has no horse in the picture: the
    # running-horse line is only for a picture that actually contains one (EP55 cover B).
    if is_ridden(t) and shows_actual_horses(t):
        return ORIENTATION if several_horses(t) else ORIENTATION_ONE
    return ORIENTATION_PLAIN if shows_actual_horses(t) else ORIENTATION_NO_HORSES
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
LIGHTING_OUTDOOR = ("Warm golden-hour light from a low late-afternoon sun, bright and "
                    "generously exposed")
LIGHTING_INDOOR = ("Warmly and generously lit, warm sunlight through a window and lamp-warm "
                   "highlights, the subject bright and clearly visible")
# 🔴 TWO VARIANTS, NEVER BOTH. (Jodie, 5 Oct 2026, EP55.) This used to be ONE sentence
# carrying the golden-hour sun AND the indoor window-and-lamp case, so every outdoor clip
# was told about a desk and every desk about a sunset, at 330 characters. The fact is
# the same — say what the light IS — and the shot decides which half it needs.
# Golden hour is Jodie's 15 Aug rule and it stands: "Bright overcast daylight" was never
# a ruling; it crept into EP49's prompts.
LIGHTING = LIGHTING_OUTDOOR
INDOOR_WORDS = re.compile(
    r"\b(indoors?|kitchen|desk|office|room|study|lounge|interior|weighing room|"
    r"lamp\w*)\b", re.I)
"""⚠️ NOT "inside": on a racecourse "the inside" is the rail side of the track, and EP55's
two gallops ("clear on the inside", "along the inside of the rail") were lit as a kitchen."""


def lighting_for(text: str) -> str:
    """The lighting line in the form THIS shot can be — indoor or outdoor, never both."""
    return LIGHTING_INDOOR if _affirms(INDOOR_WORDS, text or "") else LIGHTING_OUTDOOR
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


def shows_a_rail(prompt: str) -> bool:
    """True when the picture actually contains a running rail.

    Every mention of the rail is examined, and one that sits inside a NEGATION does not
    count — "no running rail anywhere" is a prompt saying there is no rail, however many
    times the word appears in it. This was the original home of that idea; it now shares
    `_affirms` with the horse and crowd gates, which had the same question and no answer.
    """
    return _affirms(RAIL_WORDS, prompt)


def a_rail_with_horses(prompt: str) -> bool:
    """The question the FIELD-vs-RAIL rules are entitled to be applied on.

    🔴 EP37 IS WHY. `rail-side` says the field runs on ONE side of the rail, and
    `rail-beyond` says what lies on its far side. Both lived in the HORSES tier and so
    fired whenever a jockey was mentioned:
      · a jockey carrying a saddle across an ENCLOSURE has no running rail at all — it
        has a low timber fence — and the correction tried to write "open green turf
        infield beyond" over the prompt's own "fence and soft green lawn beyond". The
        engine spotted the contradiction and asked a HUMAN which rail it was. There was
        no rail. That is a rule firing where it does not belong, dressed up as a
        decision for somebody;
      · a crowd shot with a blur of rail at the bottom and NO HORSES was told the field
        must be on one side of it.

    ⚠️ HORSES ALONE IS TOO LOOSE AND A RAIL ALONE IS TOO TIGHT, and the second half is
    the one that needed measuring rather than guessing. Requiring a rail to be MENTIONED
    would drop A21's whole point — a trackside gallop that never names a rail would stop
    being given the boundary rule, and EP23 shipped horses on BOTH SIDES of one exactly
    because five of six prompts named a rail and none said which side. The suite catches
    it: a bare gallop prompt must still be given the rail.

    🔴 THE GATE IS STRICT — A RAIL MUST BE IN THE PICTURE — AND THE BACKLOG CALLED THIS
    JODIE'S DECISION, SO HERE IS THE EVIDENCE THAT SETTLES IT RATHER THAN AN OPINION.
    The worry (logged 15 Aug, EP26) was that a trackside gallop which never names a rail
    would stop being given one, losing A21's protection. Three measurements:

      1. **A21's FOUNDING FAULT IS UNAFFECTED.** EP23 shipped horses on both sides, and
         its own note says why: *"Five of six prompts NAMED the rail and not one said
         which side the horses go."* They named it. A strict gate fires on every one of
         them and adds the side clause, which is the whole rule.
      2. **NOTHING IN THE ARCHIVE RELIES ON INJECTION.** Across all 61 governed horse
         shots, not one has a rail that came from the corrector — every genuine trackside
         prompt names its own. Measured with the corrector's own sentences stripped back
         out, because the prompts on disk have already been through it.
      3. **THE LOOSE GATE IS ITSELF A BUG, TWICE OVER.** It wrote a running rail into
         EP26's TAB-counter and desk shots (logged, never landed) and into EP37's
         enclosure (halted the build). A middle version that skipped only prompts
         describing their own far side was tried and REJECTED here: it fixed EP37 and
         left EP26's desk cover taking a rail, because a desk has horses on the wall, no
         rail, and says nothing about a far side. There is no test that separates a desk
         from a gallop except whether a rail is in the picture.

    So: a rule about a rail applies where there is a rail. The cost is a hypothetical the
    archive has never produced; the saving is two real faults.
    """
    return shows_a_rail(prompt) and has_horses(prompt)


# ══ IS THE HORSE RIDDEN? IS THE SHOT ON A TRACK? (Jodie, 5 Oct 2026, EP55) ══════
#
# 🔴 TWO RULES WERE FIRING ON SHOTS THEY DO NOT FIT. EP55's six prompts were graded
# against the whole file and got 31 findings, and two of them were plainly wrong:
#   · `silks` asked for "Australian racing silks on every rider" on a horse being LED
#     at a walk, a horse standing in a stable yard and a horse walking past its
#     owners — three shots with no rider in them, because the 20 Sep rule (c) says a
#     walking horse is riderless and led. Applied, the fix writes "jockeys up and
#     crouched in the irons" onto a led horse: the exact crouch-at-a-walk fault rule
#     (c) was written to stop.
#   · `turf` asked for "lush green Australian turf" in a stable yard.
# Same family as HORSE_WORDS, `shows_actual_horses` and `a_rail_with_horses`: a rule may
# only be applied to a shot it is actually about. Both ask their own narrower question.
#
# ⚠️ AND NEITHER MAY LOOSEN A RIDDEN HORSE ON A TRACK — the dry run against every prompt
# on the Drive is the proof, not this comment. So the race words below lean WIDE: a
# runner, a field, a barrier, a turn, a gallop or a canter all count as ridden racing,
# whether or not a rider is named, because a field rounding the turn has riders on it
# whether the prompt says so or not.
RIDER_WORDS = re.compile(
    r"\b(jockey|jockeys|rider|riders|mounted|ridden|in the irons)\b", re.I)
RACE_WORDS = re.compile(
    r"\b(gallop\w*|canter\w*|breez\w*|runners?|field|rounding|home straight|"
    r"finishing post|winning post|barriers?|starting gates?|turn for home|in a race|"
    r"blur\w*|thunder\w*|racing|races?(?!\s*-?\s*day))\b",
    re.I)
"""⚠️ `blur`, `racing` and `race` were added after the dry run, not before: EP9's
`broll-04` is "a feature-race crowd … horses blurring past on brilliant green turf" — a
race with its riders implied and never named — and the first version of this list let it
lose its silks line. "race-day" (clothes, hats) is not a race."""


def is_ridden(prompt: str) -> bool:
    """A horse with somebody on it, or a horse racing — the shots `silks` is about."""
    p = prompt or ""
    return has_horses(p) and (_affirms(RIDER_WORDS, p) or _affirms(RACE_WORDS, p))


# Where a horse can be that is NOT the track. A ridden or racing horse is on the track
# wherever the prompt says it is, so this only ever exempts an UNRIDDEN horse.
OFF_TRACK_WORDS = re.compile(
    r"\b(stables?|stable yard|stall|barn|mounting yard|parade ring|enclosure|lawn|"
    r"indoors?|kitchen|desk|office|sales? ring|weighing room|path|float)\b", re.I)


def on_a_track(prompt: str) -> bool:
    """The shots `turf` is about: horses on the racing or training surface."""
    p = prompt or ""
    return has_horses(p) and (is_ridden(p) or not _affirms(OFF_TRACK_WORDS, p))


# ══ THE FOUR EP49 RULES (docs/broll-registry.md, 20 Sep 2026, a–d) ══════════════
# Written down after four rejected, paid-for clips — and enforced nowhere until 5 Oct.
# "A rule nothing enforces is a hope." Each is either a positive LINE the corrector can
# append, or a CONTRADICTION it cannot resolve and must hand to a person.
#
# (a) HIGGSFIELD CANNOT COUNT. More than FOUR horses or people, named or implied, makes
# horses vanish mid-clip and handlers go missing. Implied = "a field", "a crowd of
# runners". A count is the writer's choice of SUBJECT, so the corrector never rewrites
# it: it is a finding for a person. The one exception is the background crowd far out
# of focus, which is texture, not subjects.
_NUM_OVER_FOUR = (r"(?:five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                  r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|"
                  r"dozens?|[5-9]|[1-9]\d+)")
_SUBJECTS = (r"(?:racehorses?|horses?|runners?|thoroughbreds?|jockeys?|riders?|people|"
             r"men|women|strappers?|handlers?|owners?|racegoers?|punters?|spectators?)")
OVER_FOUR = re.compile(
    r"\b" + _NUM_OVER_FOUR + r"\b(?:\s+\w+){0,3}?\s+" + _SUBJECTS + r"\b"
    r"|\ba\s+(?:\w+\s+)?field\b"
    r"|\b(?:a\s+)?crowd\s+of\s+(?:runners|horses|jockeys|riders|thoroughbreds)\b", re.I)


def too_many(prompt: str) -> list[str]:
    """Every phrase asking for more than four horses or people. Negated mentions, and a
    sentence that puts its crowd far out of focus, do not count."""
    out = []
    for sent in re.split(r"(?<=\.)\s+", prompt or ""):
        if re.search(r"out of focus", sent, re.I):
            continue
        for m in OVER_FOUR.finditer(sent):
            back = sent[max(0, m.start() - 60):m.start()]
            if not _NEGATED.search(back):
                out.append(m.group(0))
    return out


# (b) SADDLECLOTHS ARE PLAIN. EP49's field-of-eight carried the SAME number on every
# cloth — a numeral on screen and a racing impossibility. Any saddlecloth in the
# picture: named, or implied by a horse being ridden.
SADDLECLOTH_WORDS = re.compile(r"\bsaddle\s?cloths?\b", re.I)


def shows_a_saddlecloth(prompt: str) -> bool:
    p = prompt or ""
    return _affirms(SADDLECLOTH_WORDS, p) or is_ridden(p)


# (c) "JOCKEY" PRODUCES A RACING CROUCH, WHATEVER THE HORSE IS DOING. A walking or
# parading horse is RIDERLESS AND LED; a rider appears only on a horse at a gallop.
WALK_WORDS = re.compile(r"\b(walk\w*|parad\w*|led|leads?|leading|amble\w*|stroll\w*)\b",
                        re.I)
GALLOP_WORDS = re.compile(r"\b(gallop\w*|canter\w*|breez\w*)\b", re.I)


def a_walking_horse(prompt: str) -> bool:
    """A HORSE walking — the walk word and a horse word in the SAME sentence.

    ⚠️ SENTENCE-LEVEL, FROM THE DRY RUN: EP30's "two friends … walking away towards the
    gates" is PEOPLE walking, and a prompt-wide test called it a walking horse because a
    horse is mentioned in another sentence."""
    p = prompt or ""
    if _affirms(GALLOP_WORDS, p):
        return False
    return any(_affirms(WALK_WORDS, s) and _affirms(HORSE_ANIMAL_WORDS, s)
               for s in re.split(r"(?<=[.;])\s+", p))


# (d) THE RAIL GOES BEHIND THE HORSES, NEVER BETWEEN THE CAMERA AND THE HORSES. A
# foreground rail plus horses that must cross that line is impossible geometry, and the
# model draws the rail through their legs.
RAIL_IN_FRONT = re.compile(
    r"\brail\w*\s+(?:in|across)\s+the\s+(?:near\s+)?foreground\b"
    r"|\bforeground\b[^.]{0,30}\brail"
    r"|\b(?:through|over|across)\s+the\s+(?:white\s+)?(?:running\s+)?rail\b", re.I)


def rail_in_front(prompt: str) -> list[str]:
    p = prompt or ""
    return [m.group(0) for m in RAIL_IN_FRONT.finditer(p)
            if not _NEGATED.search(p[max(0, m.start() - 60):m.start()])]


# ══ COUNT-AWARE AND SHOT-AWARE STANDING LINES (Jodie, 5 Oct 2026, EP55) ═══════════
# Cowork read EP55's six prompts: "the subjects are good, the appended lines are the
# problem." The stride line told ONE horse standing in a stable yard about "each horse …
# across the field"; the rail line called one galloping horse "the whole field". Each line
# now asks the narrower question it is about.
PLURAL_HORSES = re.compile(
    r"\b(racehorses|horses|runners|thoroughbreds|mounts|field|string|pair|two|three|four|"
    r"several|both)\b", re.I)


def several_horses(prompt: str) -> bool:
    """More than one horse in the picture."""
    return _affirms(PLURAL_HORSES, prompt or "")


def a_moving_group(prompt: str) -> bool:
    """TWO OR MORE horses moving together — the only shot the stride line is about. One
    horse has nobody to be out of step with; a walk or a standstill has no stride to stagger."""
    p = prompt or ""
    return (shows_actual_horses(p) and several_horses(p) and not a_walking_horse(p)
            and (_affirms(GALLOP_WORDS, p) or _affirms(RACE_WORDS, p)))


RAIL_PLACED = [r"rail[^.]{0,80}\bbehind\b", r"\bbehind\b[^.]{0,40}\brail",
               r"rail[^.]{0,60}far side of (the|them)"]
"""A prompt that already says where the rail STANDS. Jodie, 5 Oct: don't add the rail line
if the prompt already places the rail — EP55's slots 3 and 5 described it twice."""


def rail_line_for(prompt: str) -> str:
    """ONE rail sentence, in the form this shot can be: the right count, the bend if there
    is one, the rail behind the horses, and a job for the far side."""
    p = prompt or ""
    who = "the horses" if several_horses(p) else "the horse"
    # ⚠️ The bend form must NOT say "curves with the track": that phrase satisfies the
    # kink rule (`rail-smooth`) by itself, and then the stronger "single smooth even
    # sweeping curve" line is never added. Where the rail stands is this line's job; how
    # it bends is `rail_smooth_for`'s.
    where = "on this bend " if BEND_WORDS.search(p) else ""
    return (f"{where}the running rail stands behind {who}, on the far side from the "
            f"camera, open green turf infield beyond it")


# 🔴 JOCKEY HEADGEAR — Jodie's ruling, 5 Oct 2026. It REPLACES both the old "safety
# helmets with the silk cover on" and EP49's "no brim, no peak". The Rules of Racing
# require a helmet (AR 122); in racing it is called a SKULL CAP, and the silk cap over it
# is in the owner's colours and, in flat racing, normally has a short peak. "Safety
# helmet" alone made the model draw a generic riding or bike helmet that did not match
# the silks. ⚠️ Watch the first test clip for the peak turning into a baseball cap.
WOMAN_WORDS = re.compile(r"\b(woman|women|female|she|her)\b", re.I)


def headgear_for(prompt: str) -> str:
    p = prompt or ""
    if several_horses(p):
        pron = "their"           # a mixed field: one sentence must cover every rider
    else:
        pron = "her" if _affirms(WOMAN_WORDS, p) else "his"
    return (f"each jockey wears a racing skull cap covered by a silk cap in the same "
            f"colours as {pron} silks, with a short peak, goggles pushed up on the cap")


def a_rider_in_shot(prompt: str) -> bool:
    p = prompt or ""
    return is_ridden(p)


OLD_HEADGEAR = re.compile(r"\bsafety helmets?\b|\bno brim, no peak\b|\bno peak\b", re.I)


# The findings that are the writer's choice of SUBJECT rather than a missing fact: the
# corrector may not resolve them, so they are the ones that legitimately reach a person.
# ONE list, read by `apply_rules` and by the archive sweep in test_broll_rail_rule.
CONTRADICTION_KEYS = frozenset({"straight-rail-on-a-bend", "four-max",
                                "rider-on-a-walking-horse", "rail-in-front",
                                "old-headgear"})

# The lines whose WORDS depend on the shot. Read from the ORIGINAL prompt (§10).
SHOT_AWARE_FIXES = {"orientation": orientation_for, "lighting": lighting_for,
                    "headgear": headgear_for}

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
    # 📌 `rail-side` and `rail-beyond` USED TO LIVE HERE, gated on horses alone. They
    # are rules about a RAIL and they moved to CONDITIONAL on 23 Aug 2026 — see
    # `a_rail_with_horses`. Nothing about the rules changed; only the question they are
    # asked on.
    # 📌 `strides` USED TO LIVE HERE too. It moved to CONDITIONAL on 23 Aug 2026 for the
    # same reason the rail rules did — see `shows_actual_horses`. A rider is not a horse.
    # 📌 `silks` and `turf` USED TO LIVE HERE, gated on horses alone. They moved to
    # CONDITIONAL on 5 Oct 2026 (EP55) — see `is_ridden` and `on_a_track`. Nothing about
    # the lines changed; only the question they are asked on.
    # 📌 `anatomy` MOVED TO CONDITIONAL on 23 Aug 2026, for the same reason as `strides`.
    # Its correction reads "anatomically correct HORSES — four legs, one head" and it was
    # gated on a word list that counts a jockey, so a horse-free shot missing the line
    # was given one about horses. Found by the control, on a fixture, before it shipped.
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
        key="silks",
        name="Australian racing silks on every rider",
        needs=[r"silks?\b"],
        when=is_ridden,
        why=("EP16 at 8:11 — tweed jackets and flat caps on an Australian provincial "
             "race day. 'Mounted' is not a costume instruction. Asked only of a RIDDEN "
             "horse since 5 Oct 2026: a led or stabled horse has no rider to dress."),
    ),
    dict(
        key="turf",
        name="lush green Australian turf",
        needs=[r"(green|lush).{0,20}turf", r"turf.{0,20}(course|racecourse|track)"],
        when=on_a_track,
        why=("These models default to American dirt. Say turf every time the horses are "
             "on a track — not in a stable yard, on a mounting-yard lawn or indoors."),
    ),
    dict(
        key="saddlecloth",
        name="plain saddlecloths with no numbers",
        needs=[r"plain saddle\s?cloths?", r"saddle\s?cloths?[^.]{0,20}no numbers?"],
        when=shows_a_saddlecloth,
        why=("EP49's field-of-eight carried the SAME number on every saddlecloth — a "
             "numeral on screen and a racing impossibility (registry, 20 Sep 2026, b). "
             "The positive instruction works where the numeral ban did not."),
    ),
    dict(
        key="led",
        name="a walking horse is riderless and led",
        needs=[r"riderless", r"no rider", r"\bled\b", r"\bleads?\b", r"\bleading\b",
               r"strapper"],
        when=a_walking_horse,
        why=("The word 'jockey' produces a racing crouch whatever the horse is doing; "
             "EP49's walk-on got riders folded into a crouch at a walk (registry, "
             "20 Sep 2026, c). A walking horse is riderless and led by a strapper."),
    ),
    dict(
        key="rail-behind",
        name="the rail BEHIND the horses",
        needs=RAIL_PLACED,
        when=lambda p: a_rail_with_horses(p) and on_a_track(p),
        why=("A rail between the camera and the horses is impossible geometry, and the "
             "model draws it through their legs (registry, 18 and 20 Sep 2026, d). Say "
             "where it IS: behind the horses."),
    ),
    dict(
        key="headgear",
        name="the jockey's skull cap and peaked silk cap",
        needs=[r"skull ?cap.{0,120}short peak"],
        when=a_rider_in_shot,
        why=("Jodie, 5 Oct 2026: the Rules of Racing require a helmet (AR 122), called a "
             "SKULL CAP in racing, under a silk cap in the owner's colours with a short "
             "peak. 'Safety helmet' alone draws a generic riding or bike helmet that does "
             "not match the silks."),
    ),
    dict(
        key="strides",
        name="horses out of step with one another",
        needs=[r"different point.{0,20}stride", r"out of phase", r"staggered stride",
               r"no two in step"],
        when=a_moving_group,
        why="EP16 at 1:25 — every horse in identical rhythm, hooves landing together.",
    ),
    dict(
        key="anatomy",
        name="anatomically correct horses",
        needs=[r"anatomic\w*", r"four legs", r"no fused"],
        when=shows_actual_horses,
        why=("The HARD-FAIL list. An extra or fused limb is not 'invisible at speed' — "
             "these get caught and rejected, after the credit is spent."),
    ),
    dict(
        key="rail-side",
        name="the whole field on ONE side of the rail",
        needs=[r"one side of (a|the|a single) .{0,30}rail",
               r"all on the same side of the .{0,20}rail",
               r"the (whole )?field .{0,40}(on|to) one side"] + RAIL_PLACED,
        when=lambda p: a_rail_with_horses(p) and on_a_track(p),
        why=("EP23 shipped with horses on BOTH SIDES of the running rail (Hugh, "
             "14 Aug 2026). Five of six prompts NAMED the rail and not one said which "
             "side the horses go, so the model drew the rail and filled both sides."),
    ),
    dict(
        key="rail-beyond",
        name="what lies BEYOND the rail (open turf infield)",
        needs=[r"(open|empty) .{0,20}(turf|grass|infield)",
               r"infield beyond", r"beyond it,? (open|empty)"] + RAIL_PLACED,
        when=lambda p: a_rail_with_horses(p) and on_a_track(p),
        why=("The positive half is the half that works. A model must render SOMETHING "
             "beyond the rail; unless the far side is given a job it reaches for the "
             "subject the rest of the prompt describes — a horse."),
    ),
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


def check_prompt(prompt: str, shot: str | None = None) -> list[dict]:
    """Every standing line this prompt fails to state. Empty list = nothing to say.

    `shot` is the text the GATES classify the picture from — which rules this shot is
    about — and defaults to the prompt itself. `apply_rules` passes the ORIGINAL prompt.

    🔴 CLAUDE.md §10, A SECOND TIME (EP55, 5 Oct 2026): "never let a fixer re-read its
    own writing as evidence about the input." The stride line the corrector appends ends
    "…across the field", and `field` is a race word, so a led yearling at a sale ring was
    re-checked AFTER correction as a racing shot and asked for silks and saddlecloths it
    could never have. Whether a line is PRESENT is still asked of the corrected text;
    WHAT THE SHOT IS is asked of the shot as written.
    """
    out = []
    cls = prompt if shot is None else shot
    # THE UNIVERSAL TIER FIRST, and unconditionally. A prompt with no horses, no crowd
    # and no rail still has a light in it, and EP26's discarded desk card is why that
    # sentence had to be written down. Every other rule below stays gated on the shot
    # actually being about the thing the rule is about (the HORSE_WORDS note).
    rules = list(UNIVERSAL)
    if has_horses(cls):
        rules += RULES                 # a kitchen table is not a racing shot
    if _affirms(CROWD_WORDS, cls):
        rules.append(CROWD_RULE)       # …and a crowd shot needs its hats, horses or not
    # …and a rule that carries its own question answers it here. One place, so a new
    # conditional rule cannot be added and then forgotten by one of the three callers.
    rules += [r for r in CONDITIONAL if r["when"](cls or "")]
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
    # 🔴 THREE MORE CONTRADICTIONS (registry, 20 Sep 2026, a, c, d). Each is the writer's
    # choice of SUBJECT, so the corrector may not rewrite it — a person does.
    many = too_many(prompt)
    if many:
        out.append({
            "key": "four-max",
            "name": "no more than FOUR horses or people",
            "why": ("asks for " + ", ".join(f'"{m}"' for m in many) + ". Higgsfield "
                    "cannot count: EP49's field of eight lost a horse in front of the "
                    "camera and its walk-on of twelve left most horses with no strapper. "
                    "Ask for four or fewer by name; a crowd far out of focus is the one "
                    "exception."),
        })
    if a_walking_horse(prompt) and _affirms(RIDER_WORDS, prompt):
        out.append({
            "key": "rider-on-a-walking-horse",
            "name": "a rider on a walking horse",
            "why": ("a walking or parading horse is RIDDEN in this prompt. The word "
                    "'jockey' gives a racing crouch at a walk (EP49's walk-on). Make it "
                    "riderless and led, or make it a gallop."),
        })
    if is_ridden(prompt) and OLD_HEADGEAR.search(prompt):
        out.append({
            "key": "old-headgear",
            "name": "the old jockey headgear wording",
            "why": ('says "' + OLD_HEADGEAR.search(prompt).group(0) + '". Jodie, 5 Oct '
                    "2026: each jockey wears a racing skull cap covered by a silk cap in "
                    "his colours, with a SHORT PEAK. 'Safety helmet' draws a bike helmet, "
                    "and EP49's 'no peak' is now wrong. Replace the phrase."),
        })
    front = rail_in_front(prompt)
    if front and shows_actual_horses(prompt):    # a crowd at a rail is not a rail fault
        out.append({
            "key": "rail-in-front",
            "name": "a rail between the camera and the horses",
            "why": ("puts the rail " + ", ".join(f'"{f}"' for f in front) + ". The rail "
                    "goes BEHIND the horses; in front of them the model draws it through "
                    "their legs."),
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
    "strides": "the horses staggered, each at a different point of its stride",
    "silks": "jockeys in bright, varied Australian racing silks, white breeches, black boots",
    "turf": "lush green Australian turf",
    # The registry's 20 Sep wording, exactly — the positive instruction that worked.
    "saddlecloth": "plain saddlecloths, no numbers",
    "led": "the horse riderless and led by a strapper at its head",
    "rail-behind": "the running rail stands behind the horses, on the far side of them "
                   "from the camera",
    "anatomy": "anatomically correct, four legs each",
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
    # 🔴 ONE SENTENCE NOW, NOT THREE (Jodie, 5 Oct 2026, EP55). The side, the far side and
    # where the rail stands were three appended lines, and the side line called a single
    # galloping horse "the whole field". `rail_line_for` says all three at once, with the
    # right count — and a prompt that already PLACES the rail is not given one at all.
    if gaps & {"rail-side", "rail-beyond", "rail-behind"}:
        text = _add_sentence_early(text, rail_line_for(prompt))
        applied.append("the rail stands behind the horse(s), open turf infield beyond it"
                       + (" (bend wording)" if bend else ""))

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
    if any(g["key"] == "rail-smooth" for g in check_prompt(text, shot=prompt)):
        text = _add_sentence(text, rail_smooth_for(text))
        applied.append("the rail is one smooth, true, evenly-posted line"
                       + (" (bend wording)" if BEND_WORDS.search(text) else ""))

    # 3. Everything else is a fact appended in the registry's own words.
    # `orientation` and `lighting` LAST, because they are statements about the whole
    # frame and read as the closing instruction rather than as one more fact about the
    # horses. Lighting last of all: it is the only one that lands on every picture.
    for key in ("strides", "silks", "headgear", "saddlecloth", "led", "turf", "anatomy",
                "hat-variety", "orientation", "lighting"):
        if key in gaps and (FIXES.get(key) or key in SHOT_AWARE_FIXES):
            # orientation, lighting and headgear are SHOT-AWARE — read through their
            # resolvers, and from the ORIGINAL prompt (§10), so a horse-free picture is
            # never handed the horses clause and a desk is never handed a sunset.
            words = SHOT_AWARE_FIXES[key](prompt) if key in SHOT_AWARE_FIXES else FIXES[key]
            text = _add_sentence(text, words)
            applied.append(words[:60] + "…")

    # 4. RE-CHECK. If applying the rules did not satisfy the rules, the tool is wrong and
    #    must say so rather than quietly generating a clip that breaks them — the one
    #    thing genuinely worth a human here. A CONTRADICTION is not a missing line, so it
    #    says what it found and why, not "still missing".
    for g in check_prompt(text, shot=prompt):
        if g["key"] == "straight-rail-on-a-bend":
            continue                   # reported by step 1 with the phrase it found
        if g["key"] in CONTRADICTION_KEYS:
            unfixable.append(f"{g['name']} — this prompt {g['why']}")
        else:
            unfixable.append(f"{g['key']} — still missing after auto-apply")
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
        if key in gaps:
            # shot-aware, and through the SAME resolver the b-roll funnel uses — the
            # cover door must not have its own idea of what the line says (A22).
            words = SHOT_AWARE_FIXES[key](prompt or "")
            text = _add_sentence(text, words)
            applied.append({"orientation": "the upright-orientation line",
                            "lighting": "the bright, warm lighting line"}[key])
    # Fault 8 — asked HERE and not through `gaps`, because this rule is about a PORTRAIT
    # COVER HERO and must never be graded against a b-roll clip. See MIDDLE_THIRD.
    # Gated on horses: a cover of a man at a desk has no field to put in the middle third.
    # The FIELD in the middle third — only where horses are actually in the picture. A
    # jockey on foot with "no horse in frame" was being told about a field of horses.
    if shows_actual_horses(text) and not any(re.search(p, text, re.I) for p in MIDDLE_THIRD_NEEDS):
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


# ══ THE WRITER'S BRIEF — the same rules, said to whoever WRITES the prompts ═══════
# (Jodie, 5 Oct 2026.) The checker is the BACKSTOP. Rule (a) and its siblings are a
# finding for a person, so a commissioned prompt that asks for "a field" stops the
# single-presenter engine at b-roll. The cure is upstream: tell the writer, in the brief
# that writes the prompts, so the backstop is never reached. ONE home for the words — the
# checker that enforces them — and `providers._commission_episode_json` reads this.
def commission_brief() -> str:
    return (
        "B-ROLL PROMPTS — the rules every prompt is checked against before a credit is "
        "spent. Write them in, so nothing is stopped:\n"
        "  - FOUR AT MOST. Never more than four horses or people in a shot, named or "
        "implied: never 'a field', never a count over four, never 'a crowd of runners'. "
        "Ask for two, three or four horses by number. (A crowd far out of focus in the "
        "background is fine.) Higgsfield cannot count; a field of eight lost a horse "
        "mid-clip.\n"
        "  - A WALKING OR PARADING HORSE IS RIDERLESS AND LED by a strapper at its head. "
        "A jockey appears ONLY on a horse at a gallop or canter — the word 'jockey' "
        "produces a racing crouch whatever the horse is doing.\n"
        "  - THE RAIL STANDS BEHIND THE HORSES, never between the camera and them: no "
        "rail in the foreground, no shot through or over the rail.\n"
        "  - SADDLECLOTHS ARE PLAIN: write 'plain saddlecloths, no numbers' on any ridden "
        "horse.\n"
        "  - JOCKEY HEADGEAR: '" + headgear_for("one jockey") + "' (use 'her' for a "
        "woman rider). Never 'safety helmet', never 'no peak'.\n"
        "  - Light is warm golden hour outdoors, warm window and lamp light indoors.\n"
        "  - Subject first; keep each prompt short — a prompt is a description of a "
        "photograph, not a list of requirements.\n\n")
