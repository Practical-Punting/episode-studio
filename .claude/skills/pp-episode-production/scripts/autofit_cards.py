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


def selector_for(owner: str) -> str:
    """card_check's name() gives el.id or the first class, and the string alone cannot
    say which. Emit both — the one that does not exist simply matches nothing."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "", owner)
    return f"#{safe}, .{safe}" if safe else ""


def offenders(page, url, bust=0):
    """Which text runs are in trouble, and what should shrink.

    Uses card_check's PROBE so the geometry is the checker's, not a second opinion.
    Returns [(owner, current_font_size, why)].

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
    if logo:
        for r in runs:
            if cc.rects_overlap(r, logo):
                out.append((r["owner"], r["fs"], "runs under the logo chip"))
    # text clipped inside its own scroll box — the other length failure
    for b in boxes:
        if b["clip"] and (b["overflowX"] > 2 or b["overflowY"] > 2):
            inside = [r for r in runs if b["id"] in r["anc"]]
            for r in inside:
                out.append((r["owner"], r["fs"],
                            f"clipped inside {b['owner']} "
                            f"({b['overflowX']:.0f}x{b['overflowY']:.0f}px)"))
    # de-duplicate on the shrink target, keeping the smallest size seen
    best = {}
    for owner, fs, why in out:
        if owner not in best or fs < best[owner][0]:
            best[owner] = (fs, why)
    return [(o, v[0], v[1]) for o, v in best.items()]


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
            first = offenders(page, url, bust)
            if not first:
                continue
            if a.dry_run:
                stuck.append((f, [(o, why) for o, _fs, why in first],
                              {o: (fs, fs) for o, fs, _why in first}))
                continue

            original = {o: fs for o, fs, _why in first}
            sizes = dict(original)
            why0 = {o: why for o, _fs, why in first}
            steps = 0
            problems = first
            while problems and steps < MAX_STEPS:
                progressed = False
                for owner, fs, _why in problems:
                    base = original.setdefault(owner, fs)
                    floor = max(base * FLOOR_FRAC, FLOOR_PX)
                    nxt = max(sizes.get(owner, fs) * STEP, floor)
                    if nxt < sizes.get(owner, fs) - 0.01:
                        sizes[owner] = nxt
                        progressed = True
                if not progressed:
                    break                     # everything is at its floor
                css = "\n".join(f"{selector_for(o)} {{ font-size: {s:.1f}px !important; }}"
                                for o, s in sizes.items() if selector_for(o))
                write_autofit(path, css)
                steps += 1
                bust += 1
                problems = offenders(page, url, bust)

            if problems:
                # Put the page back the way authoring left it — a half-shrunk page is
                # worse than the original, because it hides how far off the design is.
                write_autofit(path, "")
                stuck.append((f, [(o, why) for o, _fs, why in problems],
                              {o: (original[o], sizes[o]) for o in sizes}))
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
    for f, problems, sizes in stuck:
        print(f"  ✗ {f} — STILL DOES NOT FIT at the floor "
              f"({FLOOR_FRAC:.0%} of the template size, or {FLOOR_PX:.0f}px)")
        for o, why in problems:
            was, now = sizes.get(o, (0, 0))
            print(f"      {o}: tried down to {now:.1f}px from {was:.1f}px — {why}")
        print("      The page was restored to what authoring produced. This is a REAL halt: "
              "the words are longer than the design can hold, so it is a human choice "
              "between the words and the layout — not something to shrink away.")

    if a.dry_run:
        print("(--dry-run: nothing was written)")
    print(f"AUTOFIT: {len(fitted)} fitted, {len(stuck)} still failing")
    return 2 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
