#!/usr/bin/env python3
"""test_long_list_card.py — a ten-item list FITS. It does not go bespoke.

    python test_long_list_card.py

EP27's C17 is the article's ten questions. Its own note in episode.json says why
it was hand-authored:

    "`checklist` and `chips` hold six, `steps` holds eight, `matrix` holds five
     rows: the largest list in the vocabulary is smaller than this list."

...and nine of ten would state a different method, so dropping one was never an
option. So it became `block:"bespoke"` — past the schema, the job check, the
trace gate and the invented-text gate, with a hand-rendered page nothing measured.
**A cap of six turned a layout limit into a hole in the gates.**

    A CARD THAT IS TOO FULL SHOULD RESIZE, THE WAY A LONG TITLE ALREADY DOES.
    It must AUTO-FIT, never halt — layout is a measurement, not a judgement
    (DESIGN-self-authoring-build §11, and autofit_cards.py is that rule built).

THE REFLOW is the block choosing its own type size and column count from HOW MANY
items it has, through the SAME numeric-only `fit` channel a human uses. It cannot
introduce a word: every value that reaches the page through it is a bare number,
and there is a case below that proves text is refused.

⚠️ AND THE CAP DOES NOT GO AWAY, IT MOVES. Twelve is a card; thirty is a data
dump, and the ladder's cap of seven exists for the same reason. What changes is
that the limit is now far above the article's actual lists instead of below them.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
CAPTURE = os.path.join(HERE, "testdata", "capture-odds-table-and-ten-questions.md")
sys.path.insert(0, HERE)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                        # noqa: BLE001
        pass

import author_cards as ac                                    # noqa: E402
import card_lift as cl                                       # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"\n         <- {why}" if not cond and why else ""))


def halts(fn):
    try:
        fn()
        return False, ""
    except ac.Halt as e:
        return True, str(e)


CAP_TEXT = open(CAPTURE, encoding="utf-8").read()
QUESTIONS = cl.numbered(CAP_TEXT)
BLK = ac.load_block("checklist")
FRAME = ac.load_frame("fullscreen")
CAP_MAX = BLK["schema"]["lists"]["items"]["max"]


def card(items=None, n=None, **over):
    c = {"id": "C17", "block": "checklist", "job": "relate",
         "relates_to": "the questions to ask before a bet",
         "page": "c17-the-ten-questions.html",
         "eyebrow": "Seventeen · The Questions",
         "headline": "The Ten Questions",
         "content": {"items": items if items is not None
                     else [f"QUESTION NUMBER {i} OF THE LIST" for i in range(1, n + 1)]},
         "trace": {}}
    c.update(over)
    return c


# ══ 1. TEN FIT, AND THEY ARE THE ARTICLE'S OWN WORDS ═════════════════════════
print("\n-- ten items, lifted from the capture, held by ONE card --")
lifted = {"id": "C17", "block": "checklist", "job": "relate",
          "relates_to": "the questions to ask before a bet",
          "page": "c17-the-ten-questions.html", "eyebrow": "Seventeen · The Questions",
          "headline": "The Ten Questions",
          "lift": {"from": "numbered", "into": "items"}, "content": {}, "trace": {}}
ac.apply_lifts([lifted], CAP_TEXT)
check("all ten arrive", len((lifted["content"] or {}).get("items") or []) == 10)
ok, why = halts(lambda: ac.validate(lifted, BLK))
check("🔴 TEN ITEMS VALIDATE — the cap of six is what sent C17 bespoke", not ok, why)
check("  and the card declares a job the block can do", ac.check_job(lifted) == [], ac.check_job(lifted))

page = ""
ok, why = halts(lambda: globals().__setitem__(
    "page", ac.render_card(lifted, BLK, FRAME)))
check("  it renders", not ok, why)
if page:
    vis = ac.visible_text(page)
    missing = [q for q in QUESTIONS if ac.norm(q).lower() not in vis]
    check("🔴 ALL TEN ARE ON THE PAGE, IN FULL AND VERBATIM", not missing,
          f"missing: {missing!r}")
    ok, why = halts(lambda: ac.assert_no_invented_text(page, lifted, FRAME, BLK))
    check("  the invented-text gate is satisfied", not ok, why)
    check("  and nothing was truncated with an ellipsis", "…" not in vis and "..." not in vis,
          vis[:200])

# ══ 2. IT AUTO-FITS ACROSS THE WHOLE RANGE, AND NEVER HALTS ══════════════════
print(f"\n-- every size from 2 to the cap of {CAP_MAX} is accepted, none halts --")
for n in range(2, CAP_MAX + 1):
    ok, why = halts(lambda n=n: ac.validate(card(n=n), BLK))
    check(f"  {n:>2} items", not ok, why)

print("\n-- and the cap is a REAL limit, stated in the halt --")
ok, why = halts(lambda: ac.validate(card(n=CAP_MAX + 1), BLK))
check(f"  {CAP_MAX + 1} items halts", ok, "the cap does not exist")
check("  and the halt says how many it can hold", str(CAP_MAX) in why, why)
check("🔴 the cap is ABOVE the article's real lists, not below them", CAP_MAX >= 10,
      f"cap is {CAP_MAX}; EP27's article prints ten questions, so a cap under ten "
      f"sends the card straight back to bespoke")

# ══ 3. THE REFLOW: the block sizes ITSELF from the item count ════════════════
print("\n-- the reflow is derived from the count, and carries numbers only --")
css_small = ac.fit_css(card(n=4), BLK)
css_big = ac.fit_css(card(n=10), BLK)
check("a four-item card and a ten-item card are laid out differently",
      css_small != css_big, f"{css_small!r} == {css_big!r}")
check("  the long one goes to more than one column",
      "column-count:2" in css_big.replace(" ", ""), css_big)
check("  the short one stays in a single column",
      "column-count:1" in css_small.replace(" ", ""), css_small)
def biggest_type(css):
    return max([float(x) for x in re.findall(r"font-size:\s*([\d.]+)", css)] or [0])


check("  and the type steps down as the list grows",
      biggest_type(css_big) < biggest_type(css_small),
      f"four items set {biggest_type(css_small)}px, ten items set "
      f"{biggest_type(css_big)}px — ten must be the smaller")
check("🔴 EVERY VALUE THE REFLOW EMITS IS A BARE NUMBER — no text can enter here",
      not re.search(r":[^;{}]*[A-Za-z]", re.sub(r"font-size|line-height|margin-top|"
                                                r"column-count|column-gap|letter-spacing|"
                                                r"px|em|%", "", css_big)),
      css_big)

print("\n-- and a SHORT list does not move: the first rung restates the base CSS --")
# 🔴 THE PROPERTY THAT MAKES IT SAFE TO CHANGE A BLOCK EVERY EPISODE HAS USED.
# Measured once against the previous version of the block — a six-item card,
# 1920x1080, ZERO differing pixels — and kept true here by deriving both sides
# from the block file itself, so an edit to one that forgets the other fails.
base = BLK["css"]
rung = ac.reflow_step(card(n=6), BLK).get("fit") or {}
for key, (sel, prop) in {"item_size": (".q", "font-size"),
                         "item_gap": (".q", "margin-top"),
                         "tick_size": (".q .t", "font-size")}.items():
    want = rung.get(key)
    decl = re.search(re.escape(sel) + r"\{[^}]*" + re.escape(prop) + r":([^;}]+)", base)
    got = decl.group(1).strip() if decl else None
    check(f"  at six items {prop} on {sel} is the block's own {got!r}",
          want == got, f"the reflow says {want!r} and the base CSS says {got!r} — "
                       f"a six-item card would move")

print("\n-- a human's own `fit` still wins over the automatic one --")
mine = card(n=10, fit={"item_size": "29"})
css_mine = ac.fit_css(mine, BLK)
check("the card's explicit fit overrides the reflow's choice",
      "font-size:29" in css_mine.replace(" ", ""), css_mine)
check("  and the rest of the reflow survives beside it",
      "column-count:2" in css_mine.replace(" ", ""), css_mine)

print("\n-- and the reflow cannot be turned into a text channel --")
bad = card(n=10, fit={"item_size": "48px solid red"})
ok, why = halts(lambda: ac.fit_css(bad, BLK))
check("a non-numeric fit value still halts", ok, "text reached the stylesheet")

# ══ 4. THE ARTEFACT — measured by the gate that stops the build ══════════════
print("\n-- card_check MEASURES the finished pages at 7, 10 and 12 items --")
tmp = tempfile.mkdtemp()
shutil.copyfile(os.path.join(ASSETS, "pp-anim.js"), os.path.join(tmp, "pp-anim.js"))
os.makedirs(os.path.join(tmp, "assets"), exist_ok=True)
shutil.copyfile(os.path.join(ASSETS, "assets/logo.png"), os.path.join(tmp, "assets/logo.png"))
# The real ten first, because it is the card that actually halted EP27.
open(os.path.join(tmp, "ten-real.html"), "w", encoding="utf-8", newline="\n").write(
    ac.render_card(lifted, BLK, FRAME))
for n in (7, 10, 12):
    c = card(n=n)
    c["page"] = f"list-{n:02d}.html"
    open(os.path.join(tmp, c["page"]), "w", encoding="utf-8", newline="\n").write(
        ac.render_card(c, BLK, FRAME))
r = subprocess.run([sys.executable, os.path.join(HERE, "card_check.py"), tmp],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=400)
out = (r.stdout or "") + (r.stderr or "")
check("🔴 EVERY ONE OF THEM IS CLEAN — no collision, nothing clipped, nothing overflowing",
      r.returncode == 0, out[-1200:])
print("    " + "\n    ".join(l for l in out.splitlines() if l.strip())[:1000])

print(f"\nlong list card: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
