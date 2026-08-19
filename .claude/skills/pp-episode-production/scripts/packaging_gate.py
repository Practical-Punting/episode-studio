#!/usr/bin/env python3
"""packaging_gate.py — the thumbnail and the title card carry the RAIL's words, or
they do not ship.

    python packaging_gate.py <episode_dir> --title "..." --byline "..."

    THE WORDS WERE CORRECT ON THE RAIL AND THE PICTURES WERE WRONG.
    EP20, 11 Aug 2026. The rail said title="Bill Benter Professional Gambler" and
    byline="The power of 'deep state' handicapping". The thumbnail put the BYLINE in
    the big headline, and under it a sentence — "The method used by shrewd computer
    geeks to make millions of dollars on Hong Kong racing" — that appears in NO rail
    field at all. The in-video title card had the same scramble. Both are what a
    viewer sees first.

WHY NOTHING CAUGHT IT. Both builders had a "words gate" already, and it passed:
`thumbnail.l1 + l2 == packaging.hook`, `cover.title_setup + title_payoff ==
packaging.hook`. Every one of those values lives in episode.json, so the check asked
whether the file agreed WITH ITSELF. It did. That is the EP16 name fault exactly,
and the memory names it:

    A CONSISTENCY CHECK PROVES SAMENESS, NEVER CORRECTNESS.

So this gate is not another comparison inside episode.json. It reads the FINISHED
PAGE — the thing that becomes the PNG a human looks at — and grades every text zone
against the two fields on the rail, which is where the approved words live.

THE FIXED LAYOUT (the EP18 standard, every episode; Jodie, 11 Aug 2026):

    eyebrow   the fixed series line, "How to Win at Horse Racing"
    headline  the rail's TITLE, verbatim
    sub       the rail's BYLINE, verbatim
    part      a series designation, or nothing

NEVER GENERATE OR INVENT ANY OF IT. An empty field leaves its zone BLANK — it does
not license a sentence written to fill the space, which is what EP20's strap line was.

⚠️ RULE 4 IS THE ONE THAT WOULD HAVE CAUGHT EP20 ON ITS OWN. Rules 1-3 compare each
zone with the field it is supposed to hold; rule 4 asks the question those cannot —
is there a WORD anywhere on this page that is in none of the approved fields? It is
the same shape as author_cards' `assert_no_invented_text`, for the same reason: a
mapping check catches a swap, and only a provenance check catches an invention.
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from author_cards import norm                                    # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        pass

# The series line is a TEMPLATE LITERAL in both pages and reaches them from no data
# field. It is written here so the gate can say "that zone was tampered with" rather
# than "that zone is not any rail field", which would be true but unhelpful.
SERIES_EYEBROW = "How to Win at Horse Racing"

# The e-book cover's attribution line is standing furniture in the same way. Every
# episode's `cover.byline` is the approved byline followed by this exact suffix —
# EP16, EP17, EP18 and EP19 all carry it to the character. It is written here so the
# suffix's own words are approved vocabulary and do not read as an invention.
COVER_ATTRIBUTION = "from the Practical Punting archives · with Gordon"

# Where each zone lives in each page. The class and id names are part of the template
# contract — the same contract author_thumbnail and author_title_card substitute into.
ZONES = {
    "thumbnail": {
        "eyebrow":  [r'<div class="eyebrow">(.*?)</div>'],
        "headline": [r'<div class="l1">(.*?)</div>', r'<div class="l2">(.*?)</div>'],
        "part":     [r'<div class="part">(.*?)</div>'],
        "sub":      [r'<div class="strap">(.*?)</div>'],
    },
    "title_card": {
        "eyebrow":  [r'<div id="eyb" class="lbl">(.*?)</div>'],
        "headline": [r'<div id="t1"[^>]*>(.*?)</div>'],
        "part":     [r'<div[^>]*class="[^"]*\bpt\b[^"]*"[^>]*>(.*?)</div>'],
        "sub":      [r'<div id="byl"[^>]*>(.*?)</div>'],
    },
    # ⚠️ THE E-BOOK COVER HAS NO EYEBROW AND IT HAS A THIRD TEXT ZONE. Its `.byline`
    # is the ATTRIBUTION — the approved byline plus the standing suffix — and it is a
    # different thing from `.subtitle`, which is the byline alone. EP20 carried the
    # invented sentence in BOTH, so the same wrong copy appeared on the cover twice.
    # Added 11 Aug 2026 when Jodie asked for the cover to be re-rendered: it goes on
    # Hugh's website, so it has to be as right as the other two.
    "ebook_cover": {
        "headline": [r'<div class="title">(.*?)</div>'],
        "part":     [r'<span class="part">(.*?)</span>'],
        "sub":      [r'<div class="subtitle">(.*?)</div>'],
        "attribution": [r'<div class="byline">(.*?)</div>'],
    },
}

# Which zones a page is expected to HAVE. A kind that has no eyebrow must not be
# failed for the eyebrow being empty — and, just as important, a kind that HAS one
# must not quietly stop being checked because a template rename lost the match.
HAS_EYEBROW = {"thumbnail", "title_card"}


def _text(fragment: str) -> str:
    """The words a viewer reads: tags out, entities decoded, whitespace collapsed."""
    return norm(_html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")))


def fold(s: str) -> str:
    """Compare on WORDS, not on styling.

    The headline is set in capitals by the data and the eyebrow by CSS, while the rail
    carries sentence case; the pages use curly quotes and the rail straight ones.
    Folding case and quotes is what makes "verbatim" mean the words rather than the
    keystrokes. It deliberately does NOT fold punctuation or stem anything — widening
    it further would start hiding real differences, which is the note on
    author_cards.norm and it applies here unchanged.
    """
    return norm(s or "").lower()


# 🔴 THE E-BOOK COVER PUTS THE SERIES PART INSIDE THE TITLE. (EP21, 12 Aug 2026.)
# The title card and the thumbnail both keep it in an element of its own — `#pt` and
# `.part` — so the headline zone never sees it. `author_cover.build_title` does not:
# it appends the part INTO `<div class="title">`, in one of two shapes,
#     <span class="part">Part 1</span>          (a short title, its own line)
#     <br>&mdash; Part 1                        (a long title, kept inline — EP10)
# so the headline capture swallowed it. The gate then read the headline as
# "TRACK SECRETS Part 1" against a title field of "TRACK SECRETS" and flagged 'part'
# and '1' as words from nowhere — the very words the rail's title carries.
#
# EP21 IS THE FIRST "PART X" EPISODE THROUGH THIS GATE. It was written for EP20,
# which has no part, so this path had never once run.
COVER_PART_SPLIT = re.compile(
    r'<span class="part">|<br\s*/?>\s*(?:&mdash;|&#8212;|—|–)\s*', re.I)


def zones_from_page(kind: str, page: str) -> dict:
    """Pull every text zone out of a BUILT page. Missing zone -> ''. """
    out = {}
    for zone, patterns in ZONES[kind].items():
        parts = []
        for p in patterns:
            m = re.search(p, page, re.S)
            if m:
                parts.append(_text(m.group(1)))
        out[zone] = norm(" ".join(x for x in parts if x))
    if kind == "ebook_cover":
        m = re.search(ZONES[kind]["headline"][0], page, re.S)
        if m:
            bits = COVER_PART_SPLIT.split(m.group(1), maxsplit=1)
            out["headline"] = norm(_text(bits[0]))
            # The part is graded in its OWN zone, against its own approved source —
            # exactly as it is on the thumbnail and the title card.
            if len(bits) > 1:
                out["part"] = norm(_text(bits[1]))
    return out


# ══ THE SERIES PART IS PRINTED ONCE, IN THE PART ZONE ════════════════════════════
# 🔴 EP24, 14 Aug 2026 — "Track Secrets (Part 4)", and the thumbnail said PART TWICE.
#
# EP21, EP22 and EP23 are the same series and came out right, because their rail title
# is "Track Secrets Part 3" and their `packaging.hook` is "Track Secrets" — the part
# dropped out of the hook and only the `.part` line carried it. EP24's title was typed
# with BRACKETS, "Track Secrets (Part 4)", and the whole string became the hook. The
# thumbnail's headline must equal the hook (author_thumbnail.check), so the split had
# nowhere to put "(Part 4)" except the headline:
#     l1 "TRACK SECRETS"   l2 "(PART 4)"   part "Part 4"
# The picture then read TRACK SECRETS / (PART 4) / Part 4, and EP24 shipped with a
# thumbnail rebuilt by hand.
#
# ⚠️ NOTHING CAUGHT IT, and every check was honest. Rule 2 compares the headline to the
# title and the title genuinely does say "(Part 4)". Rule 4 allows any word that is in
# a rail field, and "part" and "4" both are. **A gate built on "does the page carry the
# rail's words" cannot see a word carried TWICE** — which is the shape worth remembering,
# because it is not a missing rule, it is a rule that counts to one and stops.
#
# The part is graded in its own zone on all three page kinds (the e-book cover splits it
# out explicitly above), so the headline never needs it. This says so and counts.
# ⭐ THE ONE PLACE THE STUDIO ASKS "IS THERE A SERIES PART AT THE END OF THIS TITLE?"
# (20 Aug 2026 — EP34 halted a whole night because there were TWO of these.)
#
# 🔴 THERE USED TO BE A SECOND ONE. `providers._split_part` carried its own pattern which
# knew the SEPARATOR forms (`- Part 2`, `: Part 2`, `— Part 3`) and NOT the bracket form;
# this one knew brackets and roman numerals and NOT separators. **Neither was a superset
# of the other, and each was right about exactly what the other missed.** So the seater
# left "(Part 1)" inside `packaging.hook`, the hook became the headline, and the gate —
# reading with THIS pattern — correctly reported a series part printed in the headline.
# **One half of the studio could not read what the other half wrote.** EP34 sat flagged
# for nine and a quarter hours with EP35 and EP32 waiting behind it.
#
# ⛔ THE TWO REJECTED FIXES, RECORDED SO NOBODY RE-PROPOSES THEM (Jodie, 20 Aug 2026):
#   · Re-punctuating the title to "- Part 1". **PP's own headline reads "(Part 2)"**, and
#     the rule is that the title IS the website's headline. That fights her own convention
#     and comes back on every multi-part article for ever.
#   · Teaching the OTHER pattern about brackets. Its docstring admitted it knew only the
#     notations it had SEEN — CLAUDE.md fault 7 for the third time in two days (metres,
#     dollars, per cent, now this). Adding the missing item leaves the shape untouched.
# ✅ **The fix is that there is only one of these now.** `providers._split_part` delegates
# here. Do not grow a second pattern anywhere; grow THIS one.
#
# ⚠️ THE SEPARATOR CLASS DELIBERATELY OMITS THE COMMA. "Thing, Part 5" has always kept its
# comma on the stem, and a fix that quietly re-derives a SHIPPED episode's hook is worse
# than the bug it fixes. The union is: what providers knew, plus what this knew, and not
# one character more.
SERIES_PART = re.compile(
    r"\s*[—–\-:·]?\s*[(\[]?\s*\bpart\s+(\d+|[ivxl]+)\b\s*[)\]]?\s*$", re.I)


def strip_part(title: str):
    """('Track Secrets', 'Part 4') from 'Track Secrets (Part 4)'.

    Anchored at the END, because that is where a series position is printed and a title
    with the word "part" in the middle of it ("The Best Part of Betting") must not be
    mistaken for one. Brackets are optional: the same series has been typed both ways.
    """
    m = SERIES_PART.search(title or "")
    if not m:
        return (title or "").strip(), ""
    return (title or "")[:m.start()].strip(), f"Part {m.group(1)}"


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", fold(s))


def zone_faults(kind: str, zones: dict, title: str, byline: str,
                part_source: str = "") -> list[str]:
    """The four rules. [] means the page carries the rail's words and nothing else.

    `part_source` is where a SERIES POSITION is approved — "Hidden Aces — Part 2".
    ⚠️ ITS WORDS ARE ALLOWED IN THE PART ZONE AND NOWHERE ELSE, which is the whole
    reason it is a separate argument rather than a third field poured into the shared
    vocabulary. A real rail title carries its own part ("Each-Way Betting Forever! —
    Part 2"), so on the engine's side this is usually redundant; it matters for the
    builders, which grade against `packaging.hook` — a hook that often drops the part
    because the part has its own line. Found by the existing thumbnail suite, whose
    EP12 fixture is exactly that shape (hook "Hidden Aces", part "Part 2").
    """
    bad = []
    what = {"thumbnail": "thumbnail", "title_card": "title card",
            "ebook_cover": "e-book cover"}[kind]

    # 1 — the eyebrow is the series line and is not per-episode text at all.
    #     Only two of the three kinds have one; the e-book cover has none.
    if kind in HAS_EYEBROW and fold(zones.get("eyebrow")) != fold(SERIES_EYEBROW):
        bad.append(
            f"{what}: the eyebrow reads {zones.get('eyebrow')!r} and it must be the "
            f"fixed series line {SERIES_EYEBROW!r}. That zone is a template literal — "
            f"if episode data has reached it, something is substituting where it "
            f"should be copying.")

    # 1b — the e-book cover's attribution: the approved byline, then the standing
    #      suffix, and nothing else. EP20 had the invented sentence here AS WELL as in
    #      the subtitle, so the same wrong copy appeared on one cover twice.
    if kind == "ebook_cover":
        want = f"{byline} · {COVER_ATTRIBUTION}" if byline else COVER_ATTRIBUTION
        if fold(zones.get("attribution")) != fold(want):
            bad.append(
                f"{what}: the attribution line reads {zones.get('attribution')!r} and it "
                f"must be {want!r} — the approved byline, then the standing suffix every "
                f"episode carries. It is not a second place to describe the episode.")

    # 2 — the headline IS the title. Not the byline, not a hook written for it.
    #     ⚠️ WITH OR WITHOUT THE SERIES PART. The part has a zone of its own on all three
    #     kinds, so a headline that leaves it out is not a headline that differs from the
    #     title — it is the title with the bit that is printed elsewhere taken off. EP24
    #     had nowhere to put "(Part 4)" but the headline precisely because this insisted
    #     on the whole string. Rule 5 below is what stops it appearing twice.
    title_no_part, _tp = strip_part(title)
    if fold(zones.get("headline")) not in (fold(title), fold(title_no_part)):
        bad.append(
            f"{what}: the big headline reads {zones.get('headline')!r} but the rail's "
            f"title is {title!r}. The headline is the TITLE field, verbatim. "
            + ("⚠️ IT IS THE BYLINE — the two are swapped, which is EP20's fault exactly."
               if fold(zones.get("headline")) == fold(byline) else
               "It is neither rail field as written."))

    # 3 — the small line IS the byline. An empty byline leaves the zone BLANK.
    if fold(zones.get("sub")) != fold(byline):
        bad.append(
            f"{what}: the line under the headline reads {zones.get('sub')!r} but the "
            f"rail's byline is {byline!r}. That zone is the BYLINE field, verbatim — "
            f"and when the byline is empty the zone stays empty. A sentence written to "
            f"fill it is invented copy, however good it reads.")

    # 4 — provenance. The rules above compare zone by zone and cannot see a word that
    # belongs to no field at all; this can. It is the last line of defence and the one
    # that catches the fault nobody predicted.
    allowed = set(_words(SERIES_EYEBROW)) | set(_words(title)) | set(_words(byline))
    for zone, text in zones.items():
        ok = set(allowed)
        if zone == "part":
            ok |= set(_words(part_source))
        if zone == "attribution":
            ok |= set(_words(COVER_ATTRIBUTION))
        stray = [w for w in _words(text) if w not in ok]
        if stray:
            bad.append(
                f"{what}: the {zone} zone contains {stray[:8]}, which appear in NO rail "
                f"field — not the title, not the byline, not the series line. Nothing on "
                f"this picture may be written for it; every word is copied from the "
                f"approved packaging or the zone is left blank.")

    # 5 — THE SERIES PART IS PRINTED ONCE, AND IN THE PART ZONE. (EP24.)
    #     Rules 2 and 4 both pass a page that says "Part 4" twice, because each of them
    #     asks whether a word BELONGS and neither counts. This counts.
    part = strip_part(title)[1] or strip_part(part_source)[1]
    if part:
        n = part.split()[-1].lower()
        phrase = re.compile(rf"\bpart\s+{re.escape(n)}\b")
        hits = {z: len(phrase.findall(fold(t))) for z, t in zones.items()}
        total = sum(hits.values())
        where = [z for z, c in hits.items() if c]
        if total > 1 or (total == 1 and hits.get("part", 0) != 1):
            if total > 1 and hits.get("headline"):
                why_ = ("The headline is carrying it AS WELL as the part line, so the "
                        "picture says it twice — EP24's fault exactly: TRACK SECRETS / "
                        "(PART 4) / Part 4. Take it out of the headline; the part line "
                        "is what prints it.")
            elif hits.get("headline"):
                why_ = ("It is in the HEADLINE instead of the part line. Every kind of "
                        "page here has a zone of its own for the part, styled for it — "
                        "a part set in headline type is the series position pretending "
                        "to be the title.")
            else:
                why_ = ("Every kind of page here has a zone of its own for the part, "
                        "and that is the only place it is printed.")
            bad.append(
                f"{what}: the series part {part!r} is printed {total} time(s), in "
                f"{where or ['no zone at all']} — it belongs in the part zone, once. "
                + why_)
    return bad


def page_faults(kind: str, page: str, title: str, byline: str,
                part_source: str = "") -> list[str]:
    return zone_faults(kind, zones_from_page(kind, page), title, byline, part_source)


# ------------------------------------------------------------------ the files
def built_pages(ep_dir: Path) -> dict:
    """The two built pages this gate grades, by kind. Missing ones are simply absent —
    a page that has not been authored yet is not a fault HERE."""
    found = {}
    for p in sorted((ep_dir / "thumbnail").glob("*-thumbnail.html")):
        found["thumbnail"] = p
        break
    for p in sorted((ep_dir / "overlay/export").glob("*-title.html")):
        found["title_card"] = p
        break
    p = ep_dir / "ebook/cover-src/cover.html"
    if p.is_file():
        found["ebook_cover"] = p
    return found


def check_episode(ep_dir: Path, title: str, byline: str,
                  part_source: str = "") -> dict:
    out = {"blockers": [], "checked": []}
    for kind, path in built_pages(ep_dir).items():
        out["checked"].append(f"{kind}: {path.name}")
        out["blockers"] += page_faults(kind, path.read_text(encoding="utf-8"),
                                       title, byline, part_source)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("episode_dir")
    ap.add_argument("--title", required=True, help="the rail's title field")
    ap.add_argument("--byline", required=True, help="the rail's byline field")
    a = ap.parse_args(argv)
    res = check_episode(Path(a.episode_dir), a.title, a.byline)
    for c in res["checked"]:
        print(f"  graded {c}")
    if not res["checked"]:
        print("  nothing built yet — nothing to grade")
    for b in res["blockers"]:
        print(f"  x {b}")
    print(f"packaging gate: {len(res['blockers'])} blocker(s)")
    return 1 if res["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
