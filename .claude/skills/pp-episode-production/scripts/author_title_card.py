#!/usr/bin/env python3
"""author_title_card.py — author the episode title card by PURE SUBSTITUTION.

    python author_title_card.py <episode.json> <overlay/export dir> [--force]

Same contract as author_cards.py, author_cover.py and author_thumbnail.py: it
copies values out of episode.json into the standing template's slots, or it
fails naming the field. No LLM, no inference, and the escaping comes from
author_cards so there is one rule about what a value may carry.

WHY THIS EXISTS (A1, 29 July 2026)
----------------------------------
The title card was hand-made on EP11, EP12 and EP13 and halted every one of them
at `Card TITLE has no clip in overlay/clips`. That halt fires on EVERY episode,
and its message asks a browser operator to write and place an HTML page — which
Hugh cannot do. It is the last of the certain halts.

**It was never a design decision.** EP13's own header comment is the proof:
*"Built from EP12's shipped ep12-title.html … Only the per-episode slots changed:
the <title> tag, the hero, object-position, the headline spans, the part line and
the byline."* Something a human instantiates by substitution is a template.

TYPE SIZE IS A MEASUREMENT (the 28 Jul ruling, applied here)
------------------------------------------------------------
The three shipped cards used two sizes, and they were set by eye:

    EP11 "HIDDEN ACES"       170px — 815.8px wide, 64.7% of the 1260px box
    EP12 "HIDDEN ACES"       170px — same headline, same series
    EP13 "THE RATINGS GAME"  150px — 1061.8px wide, 84.3% of the box

That is text-length fitting, not craft — the same thing autofit_cards.py was
built for. MEASURED in the real Anton, the rule those three numbers describe is

    size = min(CAP, floor5(TARGET_FILL * BOX / width_at_100px * 100))

with CAP=170, TARGET_FILL=0.85, BOX=1260. It reproduces **all three** hand-set
sizes exactly: EP12 computes 223 and takes the 170 cap; EP13 computes 151.3 and
rounds to 150. The rule was fitted to the shipped evidence, not invented — and if
a future headline disagrees with it, the card is rendered and looked at before
anything ships.

The part line is exactly HALF the headline on all three. That is not "about half"
in practice, so it is written as half.

**THE MEASUREMENT MUST NOT BE ABLE TO LIE.** If Anton has not actually loaded,
Chromium silently substitutes a fallback face and the width comes back wrong —
a plausible number from the wrong font, which is worse than no number. So the
probe asserts `document.fonts.check('100px Anton')` and halts if it is false.

WHAT IS PER-IMAGE, AND ALL THAT IS
----------------------------------
`object-position` — where the hero sits inside the 16:9 window. EP11 and EP13 sat
at `center` / `center 50%`; EP12 needed `center 62%` because its field sits low
in the frame. It is authored at the default and the RENDER is put in front of a
human (providers.title_placement_review), for the same reason the thumbnail crop
is: editing a coordinate in episode.json is not a browser action, so halting for
one would just be a different halt Hugh cannot clear.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from author_cards import Halt, esc                            # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                         # noqa: BLE001
        pass

ASSETS = os.path.join(os.path.dirname(HERE), "assets")
TEMPLATE = os.path.join(ASSETS, "cards/title-card.html")
GEN = "PP-GENERATED"
MARKER = (f"<!-- {GEN} by author_title_card.py — DO NOT HAND-EDIT. To change this "
          "title card, change episode.json; to take it over by hand, delete this line. -->")

W, H = 1920, 1080

# --- the measured fit (see the module docstring for where these came from) ---
BOX = 1260.0          # .inner max-width — the width the headline has to live in
CAP = 170             # the largest size any shipped card used (EP11, EP12)
TARGET_FILL = 0.85    # EP13 sat at 84.3%; EP12 was capped well below its own fit
STEP = 5              # sizes are set in 5px steps, as every hand-set one was
FLOOR = 90            # below this a title is too small to be a title: a REAL halt

DEFAULT_FOCUS = "center 50%"

# `center`, `center 62%`, or `40% 62%`. The same closed shape author_thumbnail.py
# uses, so no text can ever reach a CSS declaration.
FOCUS = re.compile(r"^(center|\d{1,3}%)( (center|\d{1,3}%))?$")

PROBE = """<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Anton&display=swap" rel="stylesheet">
<style>body{margin:0}
span{font-family:'Anton',sans-serif;font-weight:400;font-size:100px;
     letter-spacing:0.01em;text-transform:uppercase;white-space:nowrap;
     display:inline-block;line-height:0.92;}</style>
<span id="p"></span>"""


def check(ep):
    cov = ep.get("cover") or {}
    pack = ep.get("packaging") or {}
    for k in ("title_setup", "title_payoff"):
        if not cov.get(k):
            raise Halt(
                f"episode.json -> cover.{k} is missing or empty, and it IS half of the "
                f"title card's headline. The card's colour split comes from cover.* so "
                f"that the title card, the e-book cover and the thumbnail cannot disagree "
                f"about which words are emphasised — there is nothing to substitute.")
    if not pack.get("byline"):
        raise Halt(
            "episode.json -> packaging.byline is missing or empty, and it IS the line "
            "under the title. The card carries the approved words verbatim; it does not "
            "get to write its own.")

    # THE WORDS GATE, same as the cover and the thumbnail. Every asset uses the
    # locked packaging, so none of them can drift from what was approved.
    head = f"{cov['title_setup']} {cov['title_payoff']}".strip()
    if pack.get("hook") and head.upper() != pack["hook"].strip().upper():
        raise Halt(
            f"the title card headline {head!r} does not match the approved "
            f"packaging.hook {pack['hook']!r}. The words were locked at the words gate; "
            f"the title card does not get to differ from them.")
    if cov.get("part") and pack.get("ebook_title") and cov["part"] not in pack["ebook_title"]:
        raise Halt(
            f"cover.part {cov['part']!r} does not appear in the approved "
            f"packaging.ebook_title {pack['ebook_title']!r}, so the video and the e-book "
            f"would put the episode at different points in the series.")

    focus = str(((ep.get("title_card") or {}).get("hero_focus")) or DEFAULT_FOCUS)
    if not FOCUS.match(focus):
        raise Halt(
            f"title_card.hero_focus {focus!r} is not a CSS object-position like 'center' "
            f"or 'center 62%'. It positions the photograph; it is a measurement, not a "
            f"caption.")
    return head, focus


def measure_size(headline: str, lines=None):
    """The largest 5px step at which the headline still fits the box.

    Returns (size_px, width_at_100px, two_line). Anton's advance widths scale
    linearly with font-size, so ONE measurement at a reference size answers it — no
    shrink loop.

    🔒 A LONG TITLE WRAPS; IT DOES NOT HALT THE BUILD. (Jodie, 9 Aug 2026.)
    EP19's "10 SYSTEMS FOR ACTION-HUNGRY PUNTERS" measured 1423px against a 1260px box
    even at the 90px floor, and the build stopped to ask a human to choose between the
    words and the layout. Her answer: KEEP THE WORDS. So when one line will not hold
    the approved hook, it breaks at the SETUP/PAYOFF boundary — the card's own
    semantic split, white then orange — and is sized to the LONGER of the two lines.
        THE BREAK IS NOT ARBITRARY. `title_setup` and `title_payoff` are already two
        fields, already coloured differently, already written as two halves of a
        sentence. The two-line form was latent in the design; nothing new is invented,
        and nothing is shrunk below the floor or cut.
    It halts only if even the longer HALF cannot make the floor — a title so long that
    no layout here can hold it, which is a real human decision.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:                                  # noqa: BLE001
        raise Halt(f"the title card's type size is MEASURED in the real Anton and "
                   f"Playwright is not available to measure it: {e}")
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, args=["--hide-scrollbars"])
        page = b.new_page(viewport={"width": W, "height": H})
        page.set_content(PROBE)
        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
            page.evaluate("() => document.fonts.load('100px Anton')")
            page.wait_for_timeout(250)
            # DO NOT TRUST A SILENT FALLBACK. With Anton unreachable Chromium happily
            # measures some other face and hands back a plausible, wrong number.
            if not page.evaluate("() => document.fonts.check('100px Anton')"):
                raise Halt(
                    "Anton did not load, so the headline cannot be measured. Chromium "
                    "would have silently measured a fallback face and returned a "
                    "plausible wrong size. Check the network to fonts.googleapis.com.")
            def w(t):
                return page.evaluate(
                    "t => { const s = document.getElementById('p'); s.textContent = t;"
                    "       return s.getBoundingClientRect().width; }", t)

            w100 = w(headline)
            # The halves are measured in the SAME browser session and the same loaded
            # Anton — measuring them anywhere else would be measuring a different face.
            w_lines = [w(x) for x in (lines or []) if x]
        finally:
            b.close()
    if not w100:
        raise Halt(f"the headline {headline!r} measured 0px wide.")
    # The target leaves air at the right-hand end, which is what the three shipped
    # cards did. GIVE UP THE AIR BEFORE GIVING UP THE CARD: a long headline drops
    # to whatever actually fits the box before this becomes a halt.
    size = min(CAP, int(TARGET_FILL * BOX / w100 * 100.0 // STEP) * STEP)
    if size < FLOOR:
        size = min(CAP, int(BOX / w100 * 100.0 // STEP) * STEP)
    if size >= FLOOR:
        return size, w100, False

    # ── one line will not hold it: break at the setup/payoff boundary ──────────
    if w_lines:
        widest = max(w_lines)
        two = min(CAP, int(TARGET_FILL * BOX / widest * 100.0 // STEP) * STEP)
        if two < FLOOR:
            two = min(CAP, int(BOX / widest * 100.0 // STEP) * STEP)
        if two >= FLOOR:
            return two, widest, True

    raise Halt(
        f"the headline {headline!r} is {w100 * FLOOR / 100:.0f}px wide on one line and "
        f"{(max(w_lines) if w_lines else w100) * FLOOR / 100:.0f}px on its longer half, "
        f"both wider than the {BOX:.0f}px box even at the smallest size a title card "
        f"may use ({FLOOR}px). Two lines have already been tried. Shrinking further is "
        f"not the answer: the approved packaging.hook is longer than the design can "
        f"hold on any layout here, so it is a human choice between the words and the "
        f"card.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_json")
    ap.add_argument("out_dir")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    ep = json.load(open(a.episode_json, encoding="utf-8"))
    head, focus = check(ep)
    cov, pack = ep["cover"], ep["packaging"]

    os.makedirs(a.out_dir, exist_ok=True)
    stem = (ep.get("episode") or "ep").lower().replace("pp-", "")
    out = os.path.join(a.out_dir, f"{stem}-title.html")

    # NEVER OVERWRITE A HAND-AUTHORED PAGE. Same guarantee author_cards.py gives:
    # a page with no generated marker was placed by a human and wins outright.
    for f in sorted(os.listdir(a.out_dir)):
        if "title" in f.lower() and f.endswith(".html"):
            if GEN not in open(os.path.join(a.out_dir, f), encoding="utf-8",
                               errors="replace").read():
                print(f"· {f} left alone: hand-authored (no generated marker)")
                return
    # 🔴 THE --force TRAP. The "already generated" skip USED TO SIT HERE, before
    # the page was built — and the engine never passes --force, so a renamed
    # episode kept its OLD title card while every step reported success. On EP16
    # that was worked around by DELETING the page and the clip by hand, and it
    # only worked because somebody knew to do it.
    #
    # Everything between here and the write is pure composition: it reads the
    # template and substitutes, and touches nothing on disk. So the check MOVES
    # DOWN to the write, where the rendered page can be compared. A reordering,
    # not a restructure.
    size, w100, two_line = measure_size(
        head, lines=[cov["title_setup"], cov["title_payoff"]])
    part = cov.get("part")
    part_line = (f'  <div id="pt" class="anton pt">{esc(part)}</div>\n' if part else "")
    part_anim = ('{"sel":"#pt","kf":[{"opacity":0,"transform":"translateY(28px)"},'
                 '{"opacity":1,"transform":"translateY(0)"}],"opts":{"duration":550,'
                 '"delay":1000,"easing":"cubic-bezier(0.16, 1, 0.3, 1)"}},\n'
                 if part else "")

    page = open(TEMPLATE, encoding="utf-8").read()
    page = page.replace("%%PART_LINE%%\n", part_line)
    page = page.replace("%%PART_ANIM%%", part_anim)
    subs = {
        "%%TITLE%%": esc(f"PP {ep.get('episode') or ''} — title"),
        "%%GENMARK%%": (f"<!-- pp-canvas: {W}x{H} — THE canvas; the engine renders at "
                        f"exactly this. -->\n{MARKER}\n"
                        f"<!-- type size {size}px MEASURED: {esc(head)} is {w100:.1f}px "
                        f"wide at 100px, so {TARGET_FILL:.0%} of the {BOX:.0f}px box is "
                        f"{TARGET_FILL * BOX / w100 * 100:.1f}px, stepped to {size}. Not "
                        f"typed by hand — see author_title_card.py."
                        + (" TWO LINES: the hook does not fit on one at the 90px floor, "
                           "so it breaks at the setup/payoff boundary and is sized to "
                           "the longer half. The words are kept whole." if two_line
                           else "") + " -->"),
        "%%TITLE_WRAP%%": "normal" if two_line else "nowrap",
        # A real <br> rather than letting it wrap where it likes: the break belongs at
        # the setup/payoff seam, which is where the sentence already divides.
        "%%TITLE_BREAK%%": "<br>" if two_line else " ",
        "%%HERO_FOCUS%%": focus,
        "%%TITLE_SIZE%%": str(size),
        "%%PART_SIZE%%": f"{size / 2:g}",
        "%%TITLE_SETUP%%": esc(cov["title_setup"]),
        "%%TITLE_PAYOFF%%": esc(cov["title_payoff"]),
        "%%BYLINE%%": esc(pack["byline"]),
    }
    for slot, val in subs.items():
        n = page.count(slot)
        if n != 1:
            raise Halt(f"the standing title template does not contain {slot} exactly "
                       f"once (found {n}). The template has changed under this script — "
                       f"fix the pairing rather than loosening the match.")
        page = page.replace(slot, val)
    if "%%" in page:
        raise Halt(f"unfilled slots left in the title card: "
                   f"{sorted(set(re.findall('%%[A-Z_]+%%', page)))}")

    # Compare the rendered page against what is there. Identical means there was
    # nothing to do; different means the cover or packaging changed and the card
    # must be re-authored. The comparison IS the definition, so nothing can go
    # stale — see author_cards.py for the full reasoning.
    if os.path.exists(out) and not a.force:
        if open(out, encoding="utf-8").read() == page:
            print("· title card left alone: unchanged — episode.json still says "
                  "the same thing")
            return
        print("~ title card re-authored — its definition changed")

    open(out, "w", encoding="utf-8", newline="\n").write(page)
    print(f"authored {out} ({W}x{H}, headline {size}px, part "
          f"{'none' if not part else f'{size / 2:g}px'}, hero_focus={focus})")


if __name__ == "__main__":
    try:
        main()
    except Halt as e:
        print(f"TITLE CARD AUTHORING HALTED — {e}", file=sys.stderr)
        sys.exit(2)
