#!/usr/bin/env python3
"""autofit_cards.py — measure the rendered card and step the type down until it fits.

    python autofit_cards.py <cards_dir> [--only c06,c10] [--dry-run]

WHY THIS EXISTS
---------------
Two episodes in a row have hit the same wall: an auto-authored card whose text is
correct but too long for its box, so it runs under the logo chip and `card_check.py`
hard-fails the build. EP12 hit it by hand (the 130px -> 126px and 26px -> 24px nudges
between EP11 c05 and EP12 c11 were exactly this, done with a human eye). EP13 hit it
three times in one episode.

**That is not a judgement call, and `DESIGN-self-authoring-build.md` §11 already said so:**
*"Font-size auto-fit is also automatable, not a judgement: the two font nudges between EP11
c05 and EP12 c11 are pure text-length fitting. Measure the rendered overflow and step down."*
This is that, built.

**It should stop being a halt at all.** A card whose words are right and whose type is two
points too big is not something to stop an episode for, and it is certainly not something a
browser operator can fix. Per PP-STANDARDS §WHAT DESERVES A GATE, the fix is to remove the
halt, not to make the message friendlier.

THE ONE THING THIS MUST NEVER DO
--------------------------------
**It never changes a word.** It sets `font-size` and nothing else. Content, traced figures and
the article's own notation are untouched — the whole point is that the TEXT is already correct
and only the TYPE is wrong. Rewording a traced value to make it fit would break trace-or-halt,
and dropping one would be worse.

HOW IT DECIDES IT HAS SUCCEEDED
-------------------------------
**It imports `card_check.py` and uses the checker's OWN probe and OWN verdict.** So "shrink
until it fits" means, literally, "shrink until the checker that gates the build stops
complaining" — the two cannot drift apart, because there is only one implementation of what a
collision is. After this runs, `card_check.py` runs again for real, from the file on disk.

WHAT IT WILL NOT DO
-------------------
* It only touches pages carrying the `PP-GENERATED` marker. **A hand-authored page is never
  modified**, the same guarantee `author_cards.py` gives.
* It will not shrink past the FLOOR (below). If a card cannot be made to fit at the floor,
  that is a REAL halt: the content is genuinely too long for the design and a human has to
  choose between the words and the layout. It says so, names the card, and writes nothing.
"""
import argparse
import functools
import os
import re
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import card_check as cc                                          # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        pass

GEN = "PP-GENERATED"
MARK_OPEN = "/* == PP-AUTOFIT (measured, not hand-set) =="
MARK_CLOSE = "/* == end PP-AUTOFIT == */"

STEP = 0.94          # 6% per iteration — small enough to stop just past the edge
MAX_STEPS = 14       # 0.94^14 ~= 0.42, well past the floor; a guard, not a target
FLOOR_FRAC = 0.60    # never below 60% of the size the template chose
FLOOR_PX = 16.0      # and never below legibility on a 1920x1080 card

# The frame's own furniture — the eyebrow and the headline. Every card in the series
# carries them at the same size, so they are the look of the family rather than this
# episode's content. When a card overruns, the thing to shrink is the BLOCK type that
# varies episode to episode, not the furniture that makes the cards look like a set.
FURNITURE = {"eyb", "hl", "rail", "rlbl", "logo"}

# LEADING TIGHTER THAN THIS IS A ONE-LINE SETTING. Anton wants tight leading at display
# size, so .big is set at 0.86 and .price at 0.84 — beautiful on one line, and a pile-up
# the moment the text wraps, because the second line's caps are drawn INTO the first
# line's descender space. The frame headline is set at 0.94 and is designed to wrap over
# two lines, which is why the threshold sits between them rather than at 1.0: the
# template's own leading says whether wrapping was ever in the design.
TIGHT_LEADING = 0.90
RELAXED_LEADING = 1.02   # enough to clear Anton's caps; still tight for display type


def selector_for(owner: str) -> str:
    """card_check's name() gives el.id or the first class, and the string alone cannot
    say which. Emit both — the one that does not exist simply matches nothing.

    🔴 THE `.split()[0]` IS LOAD-BEARING, even though name() is supposed to have done it.
    It did not: card_check's PROBE is a RAW python string, so its `/\\s+/` reached the
    browser doubled and split on nothing, handing back the whole className. This
    function then stripped the SPACE rather than the second class and emitted
    `.blabelanton` — a selector matching NO element. autofit wrote CSS, measured no
    change, wrote smaller CSS, and finally declared the words unfittable, having never
    once altered the page. The root cause is fixed in card_check; this split stays,
    because a selector built from a multi-class owner must never silently miss.
    """
    first = owner.split()[0] if owner.split() else ""
    safe = re.sub(r"[^A-Za-z0-9_-]", "", first)
    return f"#{safe}, .{safe}" if safe else ""


def _line_boxes(runs):
    """(owner, text) -> the DISTINCT line-box tops that run is drawn on.

    One definition, shared by the wrapped-run rule and the leading check below, so
    the two can never disagree about what "wrapped" means.
    """
    tops = {}
    for r in runs:
        tops.setdefault((r["owner"], r["text"]), set()).add(round(r["y"], 1))
    return {k: sorted(v) for k, v in tops.items()}


def offenders(page, url, bust=0, shrinking=()):
    """Which text runs are in trouble, and what should shrink.

    Uses card_check's PROBE so the geometry is the checker's, not a second opinion.
    Returns [(owner, current_font_size, why)].

    ⚠️ `shrinking` IS ACCEPTED AND DELIBERATELY UNUSED FOR NOW. Chasing a wrapped run
    PAST the point the card regains its room — to force it back onto one line — broke
    EP19 C8: its price value is DESIGNED to wrap ("a long value is set to WRAP properly
    rather than halt", 9 Aug 2026) and cannot be un-wrapped at any legible size, so the
    loop ground to the floor and halted a card that fits. The codebase's answer to a
    designed wrap is to relax its LEADING, not to shrink it away. Un-wrapping is
    therefore pursued only while the card is genuinely out of room.

    ⚠️ `bust` IS NOT OPTIONAL DECORATION. Re-loading the SAME url after rewriting the
    file serves Chromium's cached copy, so every re-measure reported the ORIGINAL font
    size and the loop "shrank" all the way to the floor while measuring a page that had
    not changed. It looked exactly like "this content cannot be made to fit". The card's
    own script only tests for `?print=1`, so an unrelated query param is inert.
    """
    if bust:
        url = f"{url}{'&' if '?' in url else '?'}fit={bust}"
    page.goto(url, wait_until="load")
    page.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
    page.evaluate("() => { if (window.ppSeek && window.ppDuration) "
                  "window.ppSeek(window.ppDuration); }")
    page.wait_for_timeout(120)
    data = page.evaluate(cc.PROBE)
    runs, boxes, logo = data["runs"], data["boxes"], data["logo"]

    out = []
    hit_logo = False
    if logo:
        for r in runs:
            if cc.rects_overlap(r, logo):
                hit_logo = True
                out.append((r["owner"], r["fs"], "runs under the logo chip", 0))
    # text clipped inside its own scroll box — the other length failure
    for b in boxes:
        if b["clip"] and (b["overflowX"] > 2 or b["overflowY"] > 2):
            inside = [r for r in runs if b["id"] in r["anc"]]
            for r in inside:
                out.append((r["owner"], r["fs"],
                            f"clipped inside {b['owner']} "
                            f"({b['overflowX']:.0f}x{b['overflowY']:.0f}px)", 0))

    # ── 3. A RUN WHOSE OWN BOX EXTENDS OUTSIDE THE CARD ────────────────────────
    # card_check's third rule, and the one this function was blind to for three
    # episodes. EP16's run log wrote it down and it went unfixed: "card_check failed
    # C8/C10 while autofit said '2 examined, 0 fitted, 0 still failing' on the same
    # pages. And the halt then blames the WORDS — 'a choice between the words and the
    # layout' — when nothing ever tried to shrink it." EP19 halted the same way on
    # three cards at once. Same geometry as card_check's own rule, same CLIP tolerance,
    # so the two cannot disagree about what "outside" means.
    root = data["root"]
    def outside(r):
        return (r["x"] < root["x"] - cc.CLIP or r["y"] < root["y"] - cc.CLIP or
                r["x"] + r["w"] > root["x"] + root["w"] + cc.CLIP or
                r["y"] + r["h"] > root["y"] + root["h"] + cc.CLIP)

    over = [r for r in runs if outside(r)]
    for r in over:
        out.append((r["owner"], r["fs"], "extends outside the card", 1))

    # ── 3b. A RUN LYING ACROSS A PANEL THAT IS NOT ITS OWN ────────────────────
    # 🔴 EP22 C16, 12 Aug 2026 — THE EP16 SHAPE FOR THE THIRD TIME. card_check has had
    # a foreign-panel rule all along and this function could not see it, so autofit
    # reported "0 fitted, 0 still failing" on a page the very next gate refused, and
    # the halt blamed the WORDS: "a choice between the words and the layout". On a
    # bars card the words are TRACK NAMES. "Flemington" is one word at 78px in a 300px
    # label column — it cannot wrap, cannot be abbreviated, and spilled 26px into
    # bar1. There was no choice to make; the only honest lever is type SIZE.
    #
    # ⚠️ DERIVED, NOT NAMED — the same discipline as the wrapped-run rule below. It
    # says nothing about bars or labels: it asks which runs lie on a panel they are
    # not part of. A matrix cell over a neighbouring row, a note across a sibling
    # card, a chip over the wrong step — all covered, in any block, and each shrinks
    # through its own block's declared fit key. Shrinking is by OWNER, so a bars
    # card's three labels share `.blabel` and step down together: uniform by
    # construction, never one label smaller than its neighbours.
    #
    # 🔒 THE GEOMETRY IS CARD_CHECK'S OWN, field for field — the INK band rather than
    # the line box, the opacity test, the MIN_PANEL floor that keeps a rule or a bar
    # from counting as a panel, and the ancestry test that lets a strikethrough sit
    # inside its own chip. A second opinion here is exactly how the fitter and the
    # checker come to disagree about what "overlapping" means, which is the fault
    # this rule exists to close.
    for r in runs:
        ink = dict(r, y=r["y"] + r["h"] / 2 - cc.INK * r["fs"], h=2 * cc.INK * r["fs"])
        for b in boxes:
            if not b["opaque"] or b["id"] == r["boxId"]:
                continue
            if min(b["w"], b["h"]) < cc.MIN_PANEL:
                continue          # a rule, bar, pip or winning post is a mark, not a panel
            if b["id"] in r["anc"] or r["boxId"] in b["anc"]:
                continue
            if cc.rects_overlap(ink, b):
                out.append((r["owner"], r["fs"],
                            f"lies across {b['owner']}, which it is not part of", 0))
                break

    # ⚠️ THE LINE THAT FALLS OFF THE BOTTOM IS USUALLY NOT THE ONE AT FAULT.
    # EP19 C7: a 300px figure reading "Three to Seven" wrapped to two lines and shoved
    # the 46px caption and the 66px payoff off the card. card_check named the caption
    # and the payoff — the two innocent parties. Shrinking THEM to the 60% floor buys
    # about 52px against a 267px overflow, so autofit would have ground to the floor and
    # then blamed words that were never the problem. EP16 saw the same thing and said so:
    # "the overflow was VERTICAL and the box was 354px wide in a 1700px area. Shortening
    # '6-4 ON' would not have moved the bottom edge one pixel."
    #     So when a card overruns its BOTTOM edge, the primary target is the biggest
    # piece of BLOCK type on it — the element that owns the vertical budget — and the
    # runs that were pushed out are demoted to secondary. The main loop only escalates
    # to the secondaries once the primary is at its floor, which keeps a caption at its
    # designed size whenever shrinking the figure alone is enough.
    off_bottom = any(r["y"] + r["h"] > root["y"] + root["h"] + cc.CLIP for r in runs)
    # ⚠️ THE LOGO CHIP COUNTS AS A BOTTOM EDGE. C18 never passed the card's own
    # boundary — its lowest run ended at 985px on a 1080px card — it collided with
    # the chip. Same vertical squeeze, same cure, so the rules below fire for both.
    # Scoped to the CARD-EDGE case alone, the wrapped-run rule sat there and never ran.
    if off_bottom or hit_logo:
        body = [r for r in runs if r["owner"] not in FURNITURE]
        if body:
            tall = max(body, key=lambda r: r["fs"])
            out.append((tall["owner"], tall["fs"],
                        "the biggest type on a card that overruns its bottom edge"
                        if off_bottom else
                        "the biggest type on a card whose lower rows reach the logo", 0))
        # ── AND A RUN THAT HAS WRAPPED COSTS A WHOLE LINE OF HEIGHT ────────────
        # 🔴 EP21 C18, 12 Aug 2026. "the biggest type" is the right primary on a
        # stacked card and the WRONG one in a table, where a row is as tall as its
        # tallest cell. C18's four Sydney tracks overran the bottom by 96.7px and the
        # only wrapped run on the page was the ROW LABEL "Warwick Farm" — 360px of
        # text in a 290px column, two line boxes, making its row 220px against 127px
        # for the other three. `mcell` was the biggest type at 82px, so autofit
        # shrank THAT, all the way to the 60% floor, and the overlap did not move a
        # pixel. It then blamed the words — and the words were already as tight as
        # they go, every cell on one line.
        #     Un-wrapping a run is the cheapest vertical win there is: it removes an
        # entire line box rather than trimming a few pixels off every line. So a
        # wrapped run is a PRIMARY target alongside the biggest type.
        #
        # ⚠️ DERIVED, NOT NAMED. It says nothing about matrices or row labels — it
        # asks which runs wrapped. Any block's long label, in any card, is covered by
        # it, and each shrinks through its own block's declared fit key (`.mplace` is
        # `label_size` in the matrix's own fit map). Furniture is excluded exactly as
        # above: the frame headline is DESIGNED to wrap over two lines.
        for (owner, text), tops in _line_boxes(runs).items():
            if owner in FURNITURE or len(tops) < 2:
                continue
            fs = max(r["fs"] for r in runs
                     if r["owner"] == owner and r["text"] == text)
            out.append((owner, fs,
                        f"wrapped onto {len(tops)} lines on a card that is out of "
                        f"vertical room — un-wrapping it frees a whole line", 0))

    # ── 4. DISPLAY TYPE THAT HAS WRAPPED INTO ITSELF ──────────────────────────
    # card_check cannot see this one at all, and EP19 C8 proved it: "$1.75 to $3.25" at
    # 360px wrapped to two lines whose glyphs drew straight through each other, and
    # card_check called the page CLEAN — every rule it has is about one element hitting
    # ANOTHER, and here an element is hitting ITSELF. Shrinking cannot fix it either:
    # at 0.84 leading the lines overlap at every size. The leading has to give.
    #     Same shape as the title-card ruling of the same day — a long value is set to
    # WRAP properly rather than halt — so this reports the owners whose leading must be
    # relaxed, and the caller writes it alongside the measured size.
    # owner -> (how many line boxes, the leading ratio it is CURRENTLY drawn at)
    ratios = {}
    for (owner, _text), tops in _line_boxes(runs).items():
        fs = max(r["fs"] for r in runs if r["owner"] == owner)
        if len(tops) < 2 or fs <= 0:
            ratios.setdefault(owner, (1, 1.0))
            continue                       # one line box: the tight leading is correct
        lh = min(t2 - t1 for t1, t2 in zip(tops, tops[1:]))
        ratios[owner] = (len(tops), lh / fs)
        if lh / fs < TIGHT_LEADING:
            out.append((owner, fs,
                        f"wrapped to {len(tops)} lines at {lh / fs:.2f} leading — "
                        f"the lines are drawn through each other", 0))

    # de-duplicate on the shrink target, keeping the smallest size and the best priority
    best = {}
    for owner, fs, why, prio in out:
        cur = best.get(owner)
        if cur is None or prio < cur[2] or (prio == cur[2] and fs < cur[0]):
            best[owner] = (fs, why, prio)
    return [(o, v[0], v[1], v[2]) for o, v in best.items()], ratios


def needs_leading(ratios: dict, designed: dict) -> set:
    """Which owners must have their leading relaxed, right now.

    Two facts, from two different moments, and mixing them up cost a whole round:
      • IS IT WRAPPED — read from the CURRENT rendering. Leading cannot change a line's
        width, so this answer is unaffected by any repair already applied.
      • WAS IT DESIGNED TO WRAP — read from the FIRST measurement, before autofit wrote
        anything, because that is the only moment the template's own leading is visible.

    The first attempt used the current leading for both, and it erased itself: with the
    repair applied the element measured 1.02, "not tight", so the repair was dropped —
    which put the overlap straight back. A repair whose justification disappears the
    moment it works has to be judged against the design, not against itself.
    """
    return {o for o, (n, _r) in ratios.items()
            if n >= 2 and designed.get(o, 1.0) < TIGHT_LEADING}


def build_css(sizes: dict, leading) -> str:
    """The measured stylesheet: a size for every target, and relaxed leading only for
    those that are wrapping and were never designed to."""
    return "\n".join(
        f"{selector_for(o)} {{ font-size: {s:.1f}px !important;"
        + (f" line-height: {RELAXED_LEADING} !important;" if o in leading else "")
        + " }"
        for o, s in sizes.items() if selector_for(o))


def write_autofit(path: str, css: str) -> None:
    """Put the measured sizes into the page, replacing any previous autofit block.

    Inserted last inside <style> so it wins on source order, and marked !important
    because a block's own rules can be compound selectors (`.priceline .said`) with
    higher specificity than a single class. This is a MEASURED machine override, and
    it should beat the template's guess — that is the whole point of measuring.
    """
    page = open(path, encoding="utf-8").read()
    page = re.sub(re.escape(MARK_OPEN) + r".*?" + re.escape(MARK_CLOSE), "", page, flags=re.S)
    block = (f"{MARK_OPEN}\n"
             f"   Set by autofit_cards.py from the RENDERED page, not by hand. The words were\n"
             f"   already right and only the type was too big for its box. Re-run authoring to\n"
             f"   regenerate; re-run autofit to re-measure. */\n"
             f"{css}\n{MARK_CLOSE}\n")
    if "</style>" not in page:
        raise SystemExit(f"{os.path.basename(path)} has no </style> to insert into")
    page = page.replace("</style>", block + "</style>", 1)
    open(path, "w", encoding="utf-8", newline="\n").write(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cards_dir")
    ap.add_argument("--only", help="comma-separated substrings of filenames")
    ap.add_argument("--dry-run", action="store_true",
                    help="measure and report, write nothing")
    a = ap.parse_args()

    d = os.path.abspath(a.cards_dir)
    pages = sorted(f for f in os.listdir(d) if f.endswith(".html"))
    if a.only:
        want = [s.strip().lower() for s in a.only.split(",")]
        pages = [p for p in pages if any(w in p.lower() for w in want)]

    handler = functools.partial(SimpleHTTPRequestHandler, directory=d)

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *x):
            pass
    handler = functools.partial(Quiet, directory=d)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]

    from playwright.sync_api import sync_playwright
    fitted, skipped, stuck = [], [], []

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
                              args=["--force-color-profile=srgb", "--hide-scrollbars"])
        page = b.new_page(viewport={"width": cc.W, "height": cc.H})
        for f in pages:
            path = os.path.join(d, f)
            src = open(path, encoding="utf-8", errors="replace").read()
            if GEN not in src:
                skipped.append((f, "hand-authored (no generated marker)"))
                continue

            url = f"http://127.0.0.1:{port}/{quote(f)}"
            bust = 0
            first, ratios = offenders(page, url, bust)
            # THE TEMPLATE'S OWN LEADING, captured before autofit writes a single rule.
            # After the first write it is no longer observable anywhere.
            designed = {o: r for o, (_n, r) in ratios.items()}
            if not first:
                continue
            if a.dry_run:
                stuck.append((f, [(o, why) for o, _fs, why, _p in first],
                              {o: (fs, fs) for o, fs, _why, _p in first}, []))
                continue

            original = {o: fs for o, fs, _why, _p in first}
            sizes = dict(original)
            why0 = {o: why for o, _fs, why, _p in first}
            steps = 0
            problems = first
            while problems and steps < MAX_STEPS:
                progressed = False
                # PRIMARIES FIRST, and only fall through to the runs that were merely
                # pushed out once every primary is at its floor. A caption keeps its
                # designed size whenever shrinking the figure above it is enough.
                for level in (0, 1):
                    for owner, fs, _why, prio in problems:
                        if prio != level:
                            continue
                        base = original.setdefault(owner, fs)
                        floor = max(base * FLOOR_FRAC, FLOOR_PX)
                        nxt = max(sizes.get(owner, fs) * STEP, floor)
                        if nxt < sizes.get(owner, fs) - 0.01:
                            sizes[owner] = nxt
                            progressed = True
                    if progressed:
                        break
                if not progressed:
                    break                     # everything is at its floor
                # The leading repair is NOT sticky: it is rebuilt from the LAST
                # measurement every time. If shrinking pulls the value back onto one
                # line, the tight display leading the template asked for comes straight
                # back, and the card looks the way it was designed to. Leading cannot
                # affect width, so dropping it can never re-wrap the line — no oscillation.
                write_autofit(path, build_css(sizes, needs_leading(ratios, designed)))
                steps += 1
                bust += 1
                problems, ratios = offenders(page, url, bust, set(sizes))
                for o, (_n, r) in ratios.items():
                    designed.setdefault(o, r)     # first sighting is the design

            # ONE LAST WRITE FROM THE LAST MEASUREMENT. The loop writes CSS and THEN
            # measures, so on the winning pass it exits carrying the leading repair from
            # the step before — and EP19 C7 ended up with `line-height:1.02` on a figure
            # that had stopped wrapping two steps earlier. Re-emitting from the final
            # measurement gives the template's tight display leading back the moment it
            # is safe. Then verify, because a page nobody measured after writing is a
            # page nobody has checked. (Relaxing leading only ever makes an element
            # SHORTER, so this cannot re-break the fit.)
            if not problems:
                write_autofit(path, build_css(sizes, needs_leading(ratios, designed)))
                bust += 1
                problems, ratios = offenders(page, url, bust)

            if problems:
                # Put the page back the way authoring left it — a half-shrunk page is
                # worse than the original, because it hides how far off the design is.
                write_autofit(path, "")
                # 🔴 SAY WHAT IS ACTUALLY OFF THE CARD, NOT ONLY WHAT WE SHRANK.
                # (EP30 C04, 17 Aug 2026.) The list above holds SHRINK TARGETS chosen
                # by the rules at the top of this file — for a bottom overrun that is
                # "the biggest type on the card", which is the right lever and is very
                # often not the fault. C04's halt named `k5` at 52px; what was hanging
                # 217px off the card was the FOOTER, pushed out by chips that had
                # wrapped to four rows. A person reading that message looks at the
                # wrong element, and I did.
                #     Measured on the RESTORED page — the one the human will open —
                # with card_check's own verdict, so the halt and the gate cannot
                # describe the same page differently.
                try:
                    verdict = cc.check_page(page, f"{url}?fin={bust + 1}")
                except Exception as e:                              # noqa: BLE001
                    verdict = [f"(could not measure the restored page: {e})"]
                stuck.append((f, [(o, why) for o, _fs, why, _p in problems],
                              {o: (original[o], sizes[o]) for o in sizes}, verdict))
            else:
                fitted.append((f, steps,
                               {o: (original[o], sizes[o]) for o in sizes},
                               why0))

    print(f"AUTOFIT — {len(pages)} page(s) examined")
    for f, steps, sizes, why0 in fitted:
        print(f"  ✓ {f} — fitted in {steps} step(s)")
        for o, (was, now) in sizes.items():
            pct = 100.0 * now / was
            print(f"      {o}: {was:.1f}px -> {now:.1f}px ({pct:.0f}% of the template size)"
                  f"   [{why0.get(o, '')}]")
    for f, why in skipped:
        print(f"  · {f} — left alone: {why}")
    for f, problems, sizes, verdict in stuck:
        print(f"  ✗ {f} — STILL DOES NOT FIT at the floor "
              f"({FLOOR_FRAC:.0%} of the template size, or {FLOOR_PX:.0f}px)")
        if verdict:
            print("      WHAT IS ACTUALLY OFF THE CARD (measured on the restored page):")
            for v in verdict:
                print(f"        {v}")
        if problems:
            print("      WHAT WAS SHRUNK TRYING TO FIX IT — the lever, which is often "
                  "NOT the element above:")
        for o, why in problems:
            was, now = sizes.get(o, (0, 0))
            print(f"        {o}: tried down to {now:.1f}px from {was:.1f}px — {why}")
        print("      The page was restored to what authoring produced. This is a REAL halt: "
              "the words are longer than the design can hold, so it is a human choice "
              "between the words and the layout — not something to shrink away.")

    if a.dry_run:
        print("(--dry-run: nothing was written)")
    print(f"AUTOFIT: {len(fitted)} fitted, {len(stuck)} still failing")
    return 2 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
