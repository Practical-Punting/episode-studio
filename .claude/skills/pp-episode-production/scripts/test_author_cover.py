#!/usr/bin/env python3
"""Negative tests for the cover guards. Every one must HALT, in plain English.

    python test_author_cover.py

Includes the two that tie the cover to the APPROVED WORDS: a cover whose hook
does not reassemble into `packaging.hook`, and a `part` that is not in the
approved `packaging.ebook_title`. Those are the EP08 rework lesson — every
downstream asset carries the locked packaging verbatim — enforced somewhere a
machine can act rather than left to whoever is staging the page.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import author_cover as ac                                     # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                         # noqa: BLE001
        pass

PASS, FAIL = [], []


def episode(**cover_over):
    cover = {"title_setup": "Hidden", "title_payoff": "Aces", "part": "Part 2",
             "part_inline": False, "byline": "from the archives · with Gordon"}
    cover.update(cover_over)
    return {"packaging": {"hook": "Hidden Aces",
                          "byline": "How to spot the fresh horse that can actually win",
                          "ebook_title": "Hidden Aces — Part 2"},
            "cover": cover}


def case(name, ep, expect):
    try:
        ac.check(ep, ep["cover"])
    except ac.Halt as e:
        (PASS if expect.lower() in str(e).lower()
         else FAIL).append((name, str(e) if expect.lower() in str(e).lower()
                            else f"halted, but not about {expect!r}: {e}"))
        return
    FAIL.append((name, "DID NOT HALT — the guard did not fire"))


# control
try:
    ep = episode()
    ac.check(ep, ep["cover"])
    PASS.append(("control: a valid cover passes", "no halt, as expected"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("control: a valid cover passes", f"unexpected halt: {e}"))

# a MISSING key halts even though `part` is legitimately nullable
ep = episode()
del ep["cover"]["part"]
case("a MISSING cover key halts", ep, "missing")

# explicit null for a non-series episode is fine
try:
    ep = episode(part=None)
    ac.check(ep, ep["cover"])
    PASS.append(("explicit null part is allowed (non-series)", "no halt, as expected"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("explicit null part is allowed (non-series)", f"unexpected halt: {e}"))

case("an empty title_payoff halts", episode(title_payoff=""), "must have a value")

# THE WORDS GATE
case("a cover hook that drifts from packaging.hook halts",
     episode(title_setup="Secret"), "does not match the approved")
case("a part not in the approved ebook_title halts",
     episode(part="Part 9"), "does not appear in the approved")

# the subtitle comes from packaging, so an empty one is a halt not a blank cover
ep = episode()
ep["packaging"]["byline"] = ""
case("an empty packaging.byline halts", ep, "is the cover's subtitle")

# the four template slots must each exist exactly once (the comment-matching bug)
for slot in (ac.SLOT_TITLE_TAG, ac.SLOT_TITLE, ac.SLOT_SUBTITLE, ac.SLOT_BYLINE):
    n = open(ac.TEMPLATE, encoding="utf-8").read().count(slot)
    (PASS if n == 1 else FAIL).append(
        (f"slot occurs exactly once: {slot[:38]}…", f"found {n}"))

# the canvas is declared, and it is the template's own body rule
try:
    w, h = ac.read_canvas(open(ac.TEMPLATE, encoding="utf-8").read())
    PASS.append(("the template declares its canvas", f"{w}x{h}"))
except Exception as e:                                        # noqa: BLE001
    FAIL.append(("the template declares its canvas", str(e)))

# a page with no canvas at all halts rather than guessing a size
try:
    ac.read_canvas("<html><body>no dimensions here</body></html>")
    FAIL.append(("a page with no canvas halts", "DID NOT HALT"))
except ac.Halt as e:
    PASS.append(("a page with no canvas halts", str(e)))

print("\nCOVER NEGATIVE TESTS — every guard must fire\n" + "=" * 74)
for n, m in PASS:
    print(f"  ✓ {n}\n      {m[:110]}")
for n, m in FAIL:
    print(f"  ✗ {n}\n      {m[:160]}")
print("=" * 74)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
