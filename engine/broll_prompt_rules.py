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
RACING_WORDS = re.compile(
    r"\b(racehorse|racehorses|horses|field of|gallop\w*|runner|runners|jockey|jockeys"
    r"|racecourse|race day|raceday|straight|home turn|barrier|barriers|furlong)\b",
    re.I)


def is_racing_shot(prompt: str) -> bool:
    """A galloping / field / raceday shot — the shots the rules below are about."""
    return bool(RACING_WORDS.search(prompt or ""))


# ── the standing lines ──────────────────────────────────────────────────────────
# Each rule is (key, human name, what it must SAY, why it exists). `needs` is a list of
# alternatives — any ONE satisfies it — so a prompt may phrase a line in its own words
# without the check demanding a copy-paste. The point is that the FACT is stated, not
# that a sentence is duplicated.
RULES = [
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
CROWD_WORDS = re.compile(r"\b(crowd|spectator\w*|punter\w*|rail-?side|grandstand|"
                         r"onlooker\w*|people)\b", re.I)
CROWD_RULE = dict(
    key="hat-variety",
    name="hats in a VARIETY of natural colours",
    needs=[r"variety of .{0,20}colours", r"varied .{0,20}(hats|colours)",
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
    if not is_racing_shot(prompt):
        return []                      # a kitchen table is not a racing shot
    out = []
    rules = list(RULES)
    if CROWD_WORDS.search(prompt):
        rules.append(CROWD_RULE)
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
