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

print("\nTHUMBNAIL NEGATIVE TESTS — every guard must fire\n" + "=" * 74)
for n, m in PASS:
    print(f"  ✓ {n}\n      {m[:110]}")
for n, m in FAIL:
    print(f"  ✗ {n}\n      {m[:160]}")
print("=" * 74)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
