#!/usr/bin/env python3
"""Negative tests for the thumbnail guards. Every one must HALT, in plain English.

    python test_author_thumbnail.py

Also asserts the STANDING TEMPLATE no longer carries the drift that EP11 and EP12
each hand-corrected: the eyebrow must be the locked "How to Win at Horse Racing",
the payoff line must carry the orange colour split, and the .part class must exist.
Two episodes fixing the same three things by hand is the definition of a template
that is wrong.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import author_thumbnail as at                                 # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                         # noqa: BLE001
        pass

PASS, FAIL = [], []


def episode(**over):
    th = {"l1": "Hidden", "l2": "Aces", "part": "Part 2",
          "strap_break_after": "horse", "hero_focus": "center 62%"}
    th.update(over)
    return {"packaging": {"hook": "Hidden Aces",
                          "byline": "How to spot the fresh horse that can actually win",
                          "ebook_title": "Hidden Aces — Part 2"},
            "thumbnail": th}


def case(name, ep, expect):
    try:
        at.check(ep, ep["thumbnail"])
        at.strap_html(ep, ep["thumbnail"])
    except at.Halt as e:
        (PASS if expect.lower() in str(e).lower() else FAIL).append(
            (name, str(e) if expect.lower() in str(e).lower()
             else f"halted, but not about {expect!r}: {e}"))
        return
    FAIL.append((name, "DID NOT HALT — the guard did not fire"))


try:
    ep = episode()
    at.check(ep, ep["thumbnail"])
    html = at.strap_html(ep, ep["thumbnail"])
    assert html == ("How to spot the fresh horse<br>that can actually win"), html
    PASS.append(("control: a valid thumbnail passes", f"strap = {html}"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("control: a valid thumbnail passes", f"unexpected: {e}"))

ep = episode()
del ep["thumbnail"]["part"]
case("a MISSING key halts", ep, "missing")

try:
    ep = episode(part=None)
    at.check(ep, ep["thumbnail"])
    PASS.append(("explicit null part is allowed", "no halt, as expected"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("explicit null part is allowed", f"unexpected halt: {e}"))

case("a headline that drifts from packaging.hook halts",
     episode(l1="Secret"), "does not match the approved")
case("a part not in the approved ebook_title halts",
     episode(part="Part 9"), "does not appear in the approved")
case("a strap break word not in the byline halts",
     episode(strap_break_after="unicorn"), "is not a word in")
case("text in hero_focus halts",
     episode(hero_focus="somewhere nice"), "not a CSS")
case("an empty l2 halts", episode(l2=""), "must have a value")

# --- THE TEMPLATE ITSELF: the drift EP11 and EP12 each fixed by hand ---------
tpl = open(at.TEMPLATE, encoding="utf-8").read()
checks = [
    ("eyebrow is the LOCKED text, not 'Practical Punting'",
     '<div class="eyebrow">How to Win at Horse Racing</div>' in tpl),
    ("the eyebrow drift is gone from the markup",
     '<div class="eyebrow">Practical Punting</div>' not in tpl),
    ("the .part class exists (series part treatment)",
     re.search(r"\.part\{[^}]*font-size", tpl) is not None),
    ("the payoff line carries the ORANGE colour split",
     re.search(r"\.l2\{[^}]*color:#DA532C", tpl) is not None),
]
for name, ok in checks:
    (PASS if ok else FAIL).append((f"template: {name}", "yes" if ok else "NO"))

for slot in (at.SLOT_TITLE_TAG, at.SLOT_L1, at.SLOT_L2, at.SLOT_PART,
             at.SLOT_STRAP, at.SLOT_HERO_POS):
    n = tpl.count(slot)
    (PASS if n == 1 else FAIL).append(
        (f"slot occurs exactly once: {slot[:38]}…", f"found {n}"))

# ── THE COPY BLOCK MUST CLEAR THE LOGO CHIP ─────────────────────────────────────
# 🔴 EP19 WOULD HAVE SHIPPED A BROKEN THUMBNAIL, and nothing was watching. Its payoff
# is "ACTION-HUNGRY PUNTERS" — 21 characters where the slot's own placeholder is "Key
# word" and EP11's was "HIDDEN ACES". At the tuned 150px it wrapped to THREE lines in
# the 660px copy box: "Part 1" collided with the logo chip by 40px across the chip's
# whole width, and the strapline landed at 719->791 on a 720px canvas, entirely off the
# picture. card_check does not look at thumbnails and autofit only touches card pages,
# so the only human check is a needs_look flag that asks about the HERO CROP — a person
# shown a broken thumbnail and asked about something else.
#
# CONTROL FIRST, both ways: the long payoff must be seen to BREAK the layout before the
# fit runs, and a short one must be left completely alone. A fitter that shrinks
# everything is as wrong as one that shrinks nothing.
def _the_copy_block_clears_the_logo():
    import json
    import shutil
    import subprocess
    import tempfile

    from playwright.sync_api import sync_playwright

    HERE_ = os.path.dirname(os.path.abspath(__file__))
    ASSETS_ = os.path.join(os.path.dirname(HERE_), "assets")

    def author(l1, l2, part):
        d = tempfile.mkdtemp(prefix="thumbfit_")
        # the hero and the logo must be real files or nothing lays out
        shutil.copyfile(os.path.join(ASSETS_, "marketing-hero.png"),
                        os.path.join(d, "hero.png"))
        ep = {"episode": "PP-EP99",
              "packaging": {"hook": f"{l1} {l2}",
                            "byline": "If you must have a go at lots of races, then take care",
                            "ebook_title": f"{l1} {l2} — {part}"},
              "thumbnail": {"l1": l1, "l2": l2, "part": part,
                            "strap_break_after": "lots", "hero_focus": "center"}}
        j = os.path.join(d, "episode.json")
        with open(j, "w", encoding="utf-8") as fh:
            json.dump(ep, fh)
        r = subprocess.run([sys.executable, os.path.join(HERE_, "author_thumbnail.py"),
                            j, d, "--force"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        assert r.returncode == 0, f"authoring failed:\n{(r.stdout + r.stderr)[-600:]}"
        page = [f for f in os.listdir(d) if f.endswith("-thumbnail.html")][0]
        return d, os.path.join(d, page), r.stdout

    def measure(path, unfitted=False):
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, args=["--hide-scrollbars"])
            pg = b.new_page(viewport={"width": at.W, "height": at.H})
            try:
                pg.goto("file:///" + path.replace("\\", "/"))
                pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
                if unfitted:      # strip the measured block: the layout as authored
                    pg.evaluate("() => { for (const s of document.querySelectorAll('style'))"
                                "  s.textContent = s.textContent.split('PP-THUMB-FIT')[0]; }")
                    pg.wait_for_timeout(150)
                pg.wait_for_timeout(200)
                return pg.evaluate("""() => {
                  const g = s => { const e = document.querySelector(s); if (!e) return null;
                    const b = e.getBoundingClientRect();
                    return {t: Math.round(b.top), b: Math.round(b.bottom)}; };
                  return {part: g('.part'), strap: g('.strap'), logo: g('.logo')};
                }""")
            finally:
                b.close()

    # 1. THE CONTROL — EP19's real payoff, with the fit stripped back out.
    d, page, out = author("10 SYSTEMS FOR", "ACTION-HUNGRY PUNTERS", "Part 1")
    raw = measure(page, unfitted=True)
    bottom = max(raw["part"]["b"], raw["strap"]["b"])
    assert bottom > raw["logo"]["t"], (
        f"CONTROL FAILED: at the tuned sizes this copy block ends at {bottom}px against "
        f"a logo chip at {raw['logo']['t']}px — it does not collide, so this is not the "
        f"case that broke EP19 and the fit below proves nothing.")

    # 2. …and fitted, it clears.
    fit = measure(page)
    bottom = max(fit["part"]["b"], fit["strap"]["b"])
    assert bottom <= fit["logo"]["t"] - at.FIT_GAP, (
        f"the fitted copy block still ends at {bottom}px against a chip at "
        f"{fit['logo']['t']}px")
    assert fit["strap"]["b"] <= at.H, (
        f"the strapline ends at {fit['strap']['b']}px on a {at.H}px canvas — off the "
        f"picture, which is how EP19's shipped")
    assert at.FIT_MARK in open(page, encoding="utf-8").read(), \
        "the page carries no measured block, so the sizes were not written down"
    shutil.rmtree(d, ignore_errors=True)

    # 3. A SHORT PAYOFF IS LEFT ALONE. EP11's own words: the tuned design must survive.
    d2, page2, out2 = author("Hidden", "Aces", "Part 2")
    assert at.FIT_MARK not in open(page2, encoding="utf-8").read(), (
        "a short payoff was shrunk anyway — the tuned type sizes are the design and a "
        "fitter that touches everything will be turned off")
    assert "not needed" in out2, f"expected 'not needed' in the report, got: {out2!r}"
    shutil.rmtree(d2, ignore_errors=True)


try:
    _the_copy_block_clears_the_logo()
    PASS.append(("a long payoff is FITTED so the copy clears the logo; a short one is not",
                 "control collides, fitted clears, short payoff untouched"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("a long payoff is FITTED so the copy clears the logo; a short one is not",
                 f"{type(e).__name__}: {e}"))

# ══ THE SERIES PART IS PRINTED ONCE (EP24, 14 Aug 2026) ══════════════════════════
# EP24's rail title was typed with BRACKETS — "Track Secrets (Part 4)" — so the whole
# string became packaging.hook, check() insisted the headline equal it, and the split
# had nowhere to put the part but the headline:
#     TRACK SECRETS  /  (PART 4)  /  Part 4
# EP24 shipped a thumbnail rebuilt by hand. EP21-23 are the SAME SERIES and were right
# only because their titles carry no brackets — so the fixture here is both shapes.
import packaging_gate as _pg                                  # noqa: E402


def series_ep(hook, l1, l2, part="Part 4"):
    return {"packaging": {"hook": hook,
                          "byline": "What the track is telling you before the race",
                          "ebook_title": hook},
            "thumbnail": {"l1": l1, "l2": l2, "part": part,
                          "strap_break_after": "telling", "hero_focus": "center"}}


# --- the fault, exactly as EP24's episode.json still holds it ---------------------
case("a bracketed series part in l2 HALTS",
     series_ep("Track Secrets (Part 4)", "TRACK SECRETS", "(PART 4)"), "brackets")
case("an unbracketed series part inside the headline HALTS",
     series_ep("Track Secrets Part 4", "TRACK", "SECRETS PART 4"), "print it twice")

# --- the split that replaces it --------------------------------------------------
e24 = series_ep("Track Secrets (Part 4)", "TRACK SECRETS", "(PART 4)")
g = at.headline_and_part(e24, e24["thumbnail"])
if (g[0], g[1], g[2]) == ("TRACK", "SECRETS", "Part 4"):
    PASS.append(("'Track Secrets (Part 4)' splits to TRACK / SECRETS / Part 4",
                 f"l1={g[0]!r} l2={g[1]!r} part={g[2]!r}; {g[3]}"))
else:
    FAIL.append(("'Track Secrets (Part 4)' splits to TRACK / SECRETS / Part 4",
                 f"got {g[:3]}"))

# …and the split must then PASS its own gate — a fix that trips the guard it was
# written for is not a fix.
try:
    at.check(e24, {**e24["thumbnail"], "l1": g[0], "l2": g[1], "part": g[2]})
    PASS.append(("the split headline passes check()", "no halt"))
except at.Halt as e:                                          # noqa: BLE001
    FAIL.append(("the split headline passes check()", str(e)[:160]))

# --- CONTROL: an episode that was already right must not move --------------------
ok21 = series_ep("Track Secrets", "TRACK", "SECRETS", "Part 1")
g21 = at.headline_and_part(ok21, ok21["thumbnail"])
if (g21[0], g21[1], g21[2], g21[3]) == ("TRACK", "SECRETS", "Part 1", ""):
    PASS.append(("CONTROL: a hook with no part is left exactly alone",
                 "TRACK / SECRETS / Part 1, and no split was made"))
else:
    FAIL.append(("CONTROL: a hook with no part is left exactly alone", f"got {g21}"))

# --- the RENDERED PAGE is what the gate counts, and it counts to one --------------
def _zone_page(l1, l2, part):
    return (f'<div class="eyebrow">How to Win at Horse Racing</div>'
            f'<div class="l1">{l1}</div><div class="l2">{l2}</div>'
            f'<div class="part">{part}</div>'
            f'<div class="strap">What the track is telling you before the race</div>')


twice = _pg.page_faults("thumbnail", _zone_page("TRACK SECRETS", "(PART 4)", "Part 4"),
                        "Track Secrets (Part 4)",
                        "What the track is telling you before the race",
                        "Track Secrets (Part 4)")
if any("printed 2 time(s)" in f for f in twice):
    PASS.append(("the packaging gate REFUSES a page printing the part twice",
                 next(f for f in twice if "printed 2" in f)[:130]))
else:
    FAIL.append(("the packaging gate REFUSES a page printing the part twice",
                 f"faults={twice}"))

once = _pg.page_faults("thumbnail", _zone_page("TRACK", "SECRETS", "Part 4"),
                       "Track Secrets (Part 4)",
                       "What the track is telling you before the race",
                       "Track Secrets (Part 4)")
if not once:
    PASS.append(("CONTROL: the same page with the part ONCE passes", "no faults"))
else:
    FAIL.append(("CONTROL: the same page with the part ONCE passes", f"faults={once}"))

# …and a title whose words merely CONTAIN "part" is not a series title.
notseries = _pg.strip_part("The Best Part of Betting")
if notseries == ("The Best Part of Betting", ""):
    PASS.append(("CONTROL: 'The Best Part of Betting' is not a series part", str(notseries)))
else:
    FAIL.append(("CONTROL: 'The Best Part of Betting' is not a series part", str(notseries)))

print("\nTHUMBNAIL NEGATIVE TESTS — every guard must fire\n" + "=" * 74)
for n, m in PASS:
    print(f"  ✓ {n}\n      {m[:110]}")
for n, m in FAIL:
    print(f"  ✗ {n}\n      {m[:160]}")
print("=" * 74)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
