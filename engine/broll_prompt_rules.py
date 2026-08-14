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

# A bend and a dead-straight rail cannot both be true. EP23 asked for both, twice.
BEND_WORDS = re.compile(r"\b(bend|turn for home|home turn|turning for home|curv\w*|"
                        r"rounding)\b", re.I)
STRAIGHT_RAIL = re.compile(r"dead straight|perfectly level", re.I)


def check_prompt(prompt: str) -> list[dict]:
    """Every standing line this prompt fails to state. Empty list = nothing to say."""
    out = []
    rules = []
    if has_horses(prompt):
        rules += RULES                 # a kitchen table is not a racing shot
    if CROWD_WORDS.search(prompt or ""):
        rules.append(CROWD_RULE)       # …and a crowd shot needs its hats, horses or not
    if not rules:
        return []
    for r in rules:
        if not any(re.search(p, prompt, re.I) for p in r["needs"]):
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
}

# The rail sentence depends on the shot, which is the whole point of A21's second finding:
# a straight line pasted into a bend is what produced the incoherent geometry.
RAIL_STRAIGHT = ("the whole field running on ONE side of a single white running rail — "
                 "the rail is the inside boundary of the track, open green turf infield "
                 "beyond it, no horses on the far side")
RAIL_BEND = ("the whole field running on ONE side of a single white running rail — on "
             "this bend the rail curves with the track and the field stays outside it, "
             "the rail is the inside boundary of the track with open green turf infield "
             "beyond it and no horses on the far side")


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
    if "straight-rail-on-a-bend" in gaps:
        fixed = re.sub(r"\s*dead straight and perfectly level\s*", " ", text)
        fixed = re.sub(r"\s{2,}", " ", fixed)
        if fixed != text:
            text = fixed
            applied.append('removed "dead straight and perfectly level" — the shot bends')
        else:
            unfixable.append('a "dead straight" rail in a shot that bends, and the '
                             "phrase could not be located to remove")

    # 2. The rail sentence, in the form this shot can actually be.
    if gaps & {"rail-side", "rail-beyond"}:
        text = _add_sentence(text, RAIL_BEND if bend else RAIL_STRAIGHT)
        applied.append("the field runs on ONE side of the rail, with open green turf "
                       "infield beyond it" + (" (bend wording)" if bend else ""))

    # 3. Everything else is a fact appended in the registry's own words.
    # `orientation` LAST, because it is a statement about the whole frame and reads as
    # the closing instruction rather than as one more fact about the horses.
    for key in ("strides", "silks", "turf", "anatomy", "hat-variety", "orientation"):
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
    """Add the orientation line if it is missing. Returns (prompt, changed)."""
    if not needs_orientation(prompt):
        return prompt, False
    return _add_sentence(prompt.rstrip(), ORIENTATION), True


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
