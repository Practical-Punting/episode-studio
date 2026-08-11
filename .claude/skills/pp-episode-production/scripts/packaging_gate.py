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
}


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
    return out


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
    what = "thumbnail" if kind == "thumbnail" else "title card"

    # 1 — the eyebrow is the series line and is not per-episode text at all.
    if fold(zones.get("eyebrow")) != fold(SERIES_EYEBROW):
        bad.append(
            f"{what}: the eyebrow reads {zones.get('eyebrow')!r} and it must be the "
            f"fixed series line {SERIES_EYEBROW!r}. That zone is a template literal — "
            f"if episode data has reached it, something is substituting where it "
            f"should be copying.")

    # 2 — the headline IS the title. Not the byline, not a hook written for it.
    if fold(zones.get("headline")) != fold(title):
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
        ok = allowed | (set(_words(part_source)) if zone == "part" else set())
        stray = [w for w in _words(text) if w not in ok]
        if stray:
            bad.append(
                f"{what}: the {zone} zone contains {stray[:8]}, which appear in NO rail "
                f"field — not the title, not the byline, not the series line. Nothing on "
                f"this picture may be written for it; every word is copied from the "
                f"approved packaging or the zone is left blank.")
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
