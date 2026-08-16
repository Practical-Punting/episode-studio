"""E14 — A BESPOKE PAGE IS NOT LICENSED, IT IS UNPROTECTED.

    python engine/test_bespoke_gates.py

A card with `block: "bespoke"` is skipped ENTIRELY by `author_cards.py` — no
schema, no job check, no trace gate, no invented-text gate. EP27 paid for that
twice in one build:

  * `cards_render` halted on "Card C15 has no clip" — because a bespoke page is
    never generated and nobody had written it. A person wrote C15. **C17 was
    sitting behind it, identical, unmentioned**, and would have halted next.
  * C15's first render put "50.0" into the descenders of "PERCENTAGES", and the
    only thing that caught it was a person looking at the frame.

TWO FIXES, AND THEY ARE DIFFERENT SHAPES:

1. **ASK FOR ALL OF THEM, AT PLAN TIME.** One flag at `audit_inputs` naming every
   page a human must write, before a credit moves — instead of one deep halt per
   page, hours apart. *A check that reports one fault per attempt cannot be used
   in a loop*, and that rule was already written down twice in this codebase.
2. **GATE WHAT STAYS BESPOKE.** The words and figures on the finished page,
   against the capture — `assert_no_invented_text` asked of the ARTEFACT, because
   for a bespoke card episode.json is empty and the page is all there is.

⚠️ AND ONE CORRECTION TO THE FOLKLORE, WHICH THIS FILE MEASURES RATHER THAN
REPEATS. "card_check never sees a bespoke page" is FALSE: it is handed the whole
export directory and has always measured every page in it. The case below proves
that by feeding it a deliberately colliding bespoke page. The real hole was that
nothing required the page to EXIST at the moment the checking happens — which is
fix 1, not a third checker.

🔒 THE CRY-WOLF CONTROL IS THE MOST IMPORTANT CASE IN THIS FILE. TITLE, END and
WARRANTY are `block:"bespoke"` on EVERY episode ever built. A guard that asked a
human to write those would fire on every episode for ever, which is the version
somebody switches off.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SKILL = HERE.parent / ".claude/skills/pp-episode-production"
sys.path.insert(0, str(SKILL / "scripts"))

import preflight_cards as pc                                          # noqa: E402
import bespoke_gate as bg                                             # noqa: E402
from providers import pipeline_authors_page                           # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"\n         <- {why}" if not cond and why else ""))


CAPTURE = """# A TEST ARTICLE

---- ARTICLE TEXT BEGINS ----

# BETTING TO A HUNDRED PER CENT

Every bookmaker builds a book, and the book is what the percentages add up to.
A fair book adds to one hundred; the margin is whatever sits above it.

Most rails bookmakers work to a book of 115 per cent on a good day.

---- ARTICLE TEXT ENDS ----
"""

# The three standing pages, exactly as every episode carries them, plus two
# content cards a person would have to write.
EPJ = {"cards": [
    {"id": "C4", "block": "stat", "page": "ep99-c04-a-generated-card.html"},
    {"id": "C15", "block": "bespoke", "page": "ep99-c15-the-chart.html",
     "detail": "A 34-row table nothing in the vocabulary holds."},
    {"id": "C17", "block": "bespoke", "page": "ep99-c17-the-questions.html",
     "detail": "Ten questions; the largest list holds six."},
    {"id": "TITLE", "block": "bespoke", "page": "ep99-title.html"},
    {"id": "END", "block": "bespoke", "page": "end-card-template.html"},
    {"id": "WARRANTY", "block": "bespoke", "page": "warranty-slide.html"},
]}

# ══ 1. THE CRY-WOLF CONTROL, FIRST ═══════════════════════════════════════════
print("\n-- standing furniture is NOT a job for a human --")
want = bg.needs_a_human(EPJ["cards"], pipeline_authors_page)
ids = sorted(c["id"] for c in want)
check("🔴 TITLE, END and WARRANTY are not asked for",
      ids == ["C15", "C17"],
      f"it wants {ids} — TITLE/END/WARRANTY are block:'bespoke' on every episode "
      f"ever built, so asking for them fires on every build for ever")
for cid in ("TITLE", "END", "WARRANTY"):
    card = next(c for c in EPJ["cards"] if c["id"] == cid)
    check(f"  {cid} ({card['page']}) is produced by the build itself",
          pipeline_authors_page(card))
check("  and a real content card IS asked for",
      not pipeline_authors_page(next(c for c in EPJ["cards"] if c["id"] == "C15")))

# ══ 2. ONE FLAG, NAMING EVERY PAGE, NOT ONE HALT PER PAGE ════════════════════
print("\n-- it stands aside when the caller has not LOOKED --")
# The same rule capture_reference_faults already carries, for the same reason: EP15
# and EP19 each shipped one genuine bespoke card, so a version that halted without
# a folder to look in reported two finished episodes as unbuildable — in the
# existing suite, on the first run. "You did not give me a folder" is not "the page
# is missing". Caught by test_preflight_rehearsal's shipped-episode cases.
check("🔴 no pages folder means no ask", pc.bespoke_faults(EPJ, pages_dir=None) == [],
      pc.bespoke_faults(EPJ, pages_dir=None))

print("\n-- the ask happens at PLAN time, and it is ONE ask --")
empty = Path(tempfile.mkdtemp())            # the export folder of a fresh build
blockers = pc.bespoke_faults(EPJ, pages_dir=empty)
check("🔴 ONE blocker, not two", len(blockers) == 1, f"{len(blockers)} blockers")
msg = blockers[0] if blockers else ""
check("  and it names BOTH pages in that one message",
      "C15" in msg and "C17" in msg,
      "this is EP27 exactly: C15 halted, a person wrote it, and C17 was behind it")
check("  it names the FILES a person has to create",
      "ep99-c15-the-chart.html" in msg and "ep99-c17-the-questions.html" in msg, msg)
check("  it carries each card's own note, so the person knows what it is for",
      "34-row table" in msg and "Ten questions" in msg, msg)
check("  and it says to ask whether it must be bespoke at all",
      "ladder" in msg and "checklist" in msg, msg)

print("\n-- and it CLEARS by doing the work, with no gate edited --")
d = Path(tempfile.mkdtemp())
(d / "ep99-c15-the-chart.html").write_text("<html></html>", encoding="utf-8")
half = pc.bespoke_faults(EPJ, pages_dir=d)
check("with one page written, only the other is still asked for",
      len(half) == 1 and "C17" in half[0] and "ep99-c15" not in half[0], half)
(d / "ep99-c17-the-questions.html").write_text("<html></html>", encoding="utf-8")
check("🔴 with both written, the ask is GONE", pc.bespoke_faults(EPJ, pages_dir=d) == [],
      pc.bespoke_faults(EPJ, pages_dir=d))

print("\n-- an episode with no bespoke content cards is never bothered --")
clean = {"cards": [c for c in EPJ["cards"] if c["id"] not in ("C15", "C17")]}
check("🔴 zero blockers on an all-generated episode, even with the folder EMPTY",
      pc.bespoke_faults(clean, pages_dir=Path(tempfile.mkdtemp())) == [],
      pc.bespoke_faults(clean, pages_dir=Path(tempfile.mkdtemp())))

# ══ 3. THE WORDS AND FIGURES ON A PAGE THAT STAYS BESPOKE ════════════════════
print("\n-- what a hand-authored page is allowed to say --")
FRAME = (SKILL / "assets/cards/frame-fullscreen.html").read_text(encoding="utf-8")


def page(body, extra="<script>window.ppDuration=5000;</script>"):
    return (f"<html><head><style>.x{{font-size:40px}}</style></head><body>"
            f"<div class='card'><div class='hl'>THE BOOK</div>{body}</div>"
            f"{extra}</body></html>")


card15 = {"id": "C15", "block": "bespoke", "page": "x.html",
          "headline": "The Book", "eyebrow": "Fifteen · The Chart"}

good = page("<div class='x'>A fair book adds to one hundred</div>"
            "<div class='y'>115 per cent on a good day</div>")
check("a page quoting the article passes",
      bg.page_faults(card15, good, CAPTURE, FRAME) == [],
      bg.page_faults(card15, good, CAPTURE, FRAME))

made_up = page("<div class='x'>A fair book adds to one hundred</div>"
               "<div class='y'>127 per cent on a good day</div>")
probs = bg.page_faults(card15, made_up, CAPTURE, FRAME)
check("🔴 A FIGURE THAT IS IN NO ARTICLE IS CAUGHT", any("127" in p for p in probs),
      f"{probs!r} — on a generated card this is structurally impossible; on a "
      f"bespoke page it is one keystroke")

invented = page("<div class='x'>Randwick was heavy on Saturday</div>")
probs = bg.page_faults(card15, invented, CAPTURE, FRAME)
check("🔴 PROSE THAT IS IN NO ARTICLE IS CAUGHT",
      any("randwick" in p.lower() for p in probs), probs)

no_anim = page("<div class='x'>A fair book adds to one hundred</div>", extra="")
probs = bg.page_faults(card15, no_anim, CAPTURE, FRAME)
check("  a page that never defines ppDuration is caught BEFORE it renders no clip",
      any("ppDuration" in p for p in probs),
      "E14's second halt: render_card waits on it before it waits for fonts")

print("\n-- the licence is a DECLARATION, not a silent exception --")
licensed = dict(card15, bespoke_licence={"34": "the source table has 34 data rows"})
# The WORDS still have to come from the article — only the declared figure is
# excused. That is why this line is built out of the capture's own vocabulary.
ok = page("<div class='x'>34 per cent of the book</div>")
check("a declared figure is allowed", bg.page_faults(licensed, ok, CAPTURE, FRAME) == [],
      bg.page_faults(licensed, ok, CAPTURE, FRAME))
check("  and an UNdeclared one beside it is not",
      any("99" in p for p in bg.page_faults(licensed, page(
          "<div class='x'>34 per cent of the book, 99 above it</div>"), CAPTURE, FRAME)))
check("  a licence excuses the FIGURE, never the prose beside it",
      any("randwick" in p.lower() for p in bg.page_faults(
          licensed, page("<div class='x'>34 per cent at Randwick</div>"), CAPTURE, FRAME)),
      "a declaration about one number must not open the whole page")

print("\n-- the studio's standing line is furniture, like the frame's own words --")
# 🔒 JODIE'S RULING, 16 Aug 2026, on EP27's C15 footer: "the full chart is in the
# guide" is a LEGITIMATE LINE, not an error. It points at the e-book, so no article
# will ever contain it, and it appears on every ladder card there will ever be.
#     A GENERATED ladder card never needed this — its footer is a content value in
# episode.json and is allowed like any other (pinned in test_card_lift). This is
# the HAND-AUTHORED case, and the excuse is deliberately narrow.
standing = page("<div class='x'>the full chart is in the guide</div>")
check("🔴 the standing footer does NOT flag 'full' on a hand-authored page",
      not any("full" in p for p in bg.page_faults(card15, standing, CAPTURE, FRAME)),
      bg.page_faults(card15, standing, CAPTURE, FRAME))
check("  it is the PHRASE that is excused, never the words in it",
      any("full" in p for p in bg.page_faults(
          card15, page("<div class='x'>the full field went round</div>"),
          CAPTURE, FRAME)),
      "excusing the WORDS would open a hole the width of the vocabulary")
counted = page("<div class='x'>34 per cent, the full chart is in the guide</div>")
check("🔴 and the COUNT beside it still has to be declared",
      any("34" in p for p in bg.page_faults(card15, counted, CAPTURE, FRAME)),
      "on a ladder card card_lift asserts that count against the table's own row "
      "count; a bespoke page states it on its own authority and must declare it")

print("\n-- and with no capture it REFUSES rather than passing --")
check("🔴 no capture means nothing was checked, and it says so",
      bg.page_faults(card15, good, None, FRAME) != [],
      "a bespoke page has no other gate; silence here would be a pass by default")

# ══ 4. THE COLLISION — MEASURED, NOT ASSERTED ════════════════════════════════
print("\n-- card_check on a deliberately colliding BESPOKE page --")
fx = HERE / "testdata/bespoke-collision-BEFORE-FIX.html"
tmp = Path(tempfile.mkdtemp())
shutil.copyfile(SKILL / "assets/pp-anim.js", tmp / "pp-anim.js")
(tmp / "assets").mkdir()
shutil.copyfile(SKILL / "assets/assets/logo.png", tmp / "assets/logo.png")
shutil.copyfile(fx, tmp / fx.name)
r = subprocess.run([sys.executable, str(SKILL / "scripts/card_check.py"), str(tmp)],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=400)
out = (r.stdout or "") + (r.stderr or "")
check("🔴 card_check FAILS the colliding bespoke page", r.returncode != 0,
      f"it passed it:\n{out[-600:]}")
check("  and it names the collision in plain English",
      "OVERLAP" in out or "UNDER THE LOGO" in out or "CLIPPED" in out, out[-600:])
print("    " + "\n    ".join(l for l in out.splitlines() if l.strip())[:700])
check("  (so the folklore was wrong: it was never blind to these pages — "
      "the hole was that nothing made the page EXIST in time)", True)

# ══ 5. THE CALL SITE, IN AN INTERPRETER THAT SET NOTHING UP ══════════════════
# 🔴 CLAUDE.md FAULT #4, AND IT ALREADY BIT ONCE HERE. Every check above imports
# `bespoke_gate` at the top of this file — which puts the skill's scripts folder on
# sys.path — so the render-time call site passed the whole suite while raising
# ModuleNotFoundError in the engine, where only `engine/` is on the path. That is
# EP15's NameError in a new costume: a call site proved by a suite that set up the
# very thing the real process does not.
#     So this case runs it in a SUBPROCESS that imports nothing but `providers`.
print("\n-- the render-time call site works in a clean interpreter --")
probe = f'''
import sys
sys.path.insert(0, r"{HERE}")
import providers


class P:
    pp = r"{HERE}"

    def epjson(self, ep):
        return {{"cards": [{{"id": "C9", "block": "bespoke", "page": "nope.html"}}]}}


try:
    providers.assert_bespoke_pages_are_sound({{}}, P(), r"{HERE}", r"{HERE}")
    print("RETURNED")
except providers.EngineFlag:
    print("FLAGGED")          # the page is missing — the right answer, and it got there
except Exception as e:
    print("BROKE", type(e).__name__, e)
'''
r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=120)
said = (r.stdout or "").strip().splitlines()[-1:] or [(r.stderr or "").strip()[-200:]]
check("🔴 it reaches its verdict without the test's own sys.path help",
      said[0] in ("FLAGGED", "RETURNED"),
      f"the engine would have hit this at cards_render: {said[0]}")

print(f"\nbespoke gates: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
