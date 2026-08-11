"""SITTING 5b + the two latent guards — proved fail-first.

  · stage_timing_proof   emits "X appears at real time T, while Gordon is saying '…',
                         holds N seconds" for every card AND overlay, and FAILS when an
                         overlay arrives where nothing is being said.
  · the rendered card    must SHOW every figure that is in the file (EP18 C9 shipped
                         two bars and a dangling "per cent profit on turnover").

Run: python engine/test_timing_proof_and_figures.py
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(SCRIPTS))
import author_cards as ac       # noqa: E402
import qc_episode as q          # noqa: E402

def episode_dir(n: int) -> pathlib.Path:
    """Resolve an episode folder BY NUMBER, never by a written-out name.

    ⚠️ THE STAGE-8 CLOSE-OUT RENAMES EVERY PUBLISHED EPISODE'S FOLDER — PP-EP18 became
    PP-EP18-Those-Top-6-Favourites the day the close-out was automated — so a literal
    path is a fuse: it passes for weeks and then SKIPS, silently, the day the process
    does the thing the standard requires of it.
    """
    root = pathlib.Path(r"G:\My Drive\PP Videos")
    hits = sorted(p for p in root.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else root / f"PP-EP{n:02d}"


SRC = episode_dir(18)
FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


class Rec:
    def __init__(self, windows):
        self.fails, self.warns, self.notes = [], [], []
        self.timing_windows = windows
    def fail(self, m): self.fails.append(m)
    def warn(self, m): self.warns.append(m)
    def note(self, m): self.notes.append(m)


print("\n=== the timing proof: a sentence per card and overlay ===\n")

if not (SRC / "renders/aligned.srt").is_file():
    print("SKIP: EP18's SRT is not reachable.")
else:
    HEAD = 7.0
    good = {"cards": {"C9": (452.13, 462.13)},
            "overlays": {"MIDROLL_CHIP": (322.13, 339.33),
                         "EARLY_CTA": (53.0, 59.0)}}
    r = Rec(good)
    q.stage_timing_proof(r, str(SRC / "docs/episode.json"), str(SRC), HEAD)
    joined = " ".join(r.notes)
    check("every window gets a sentence", len(r.notes) == 3, str(len(r.notes)))
    check("  it gives the real time and the hold",
          "appears at 322.13s" in joined and "holds 17.2s" in joined, joined[:200])
    check("  it quotes the words under it",
          "a like puts it in somebody else's evening" in joined)
    check("  and says how far into the line it lands", "1.0s in" in joined)
    check("  the early card lands inside the guide invitation",
          "free companion guide" in joined and "1.73s in" in joined)
    check("a correctly placed set raises NO failures", not r.fails, str(r.fails))

    print("\n=== FAIL FIRST: mis-place an overlay into silence ===\n")
    # 48.6s was EP18's real bug: the presenter-clock number read as final-clock, which
    # put the card 7s before the words. In the finished file that lands in a gap.
    bad = {"cards": {}, "overlays": {"EARLY_CTA": (48.6, 50.6)}}
    r2 = Rec(bad)
    q.stage_timing_proof(r2, str(SRC / "docs/episode.json"), str(SRC), HEAD)
    check("an overlay arriving in silence FAILS",
          any("EARLY_CTA" in f and "silence" in f for f in r2.fails), str(r2.fails))
    check("  and the note shows what it found instead",
          any("nothing" in n for n in r2.notes), str(r2.notes))

    print("\n=== it refuses to pretend when its inputs are missing ===\n")
    r3 = Rec(None)
    r3.timing_windows = None
    q.stage_timing_proof(r3, str(SRC / "docs/episode.json"), str(SRC), HEAD)
    check("no windows -> says so, does not invent", r3.warns and not r3.notes,
          str(r3.warns))

print("\n=== the rendered card must SHOW its figures (EP18 C9) ===\n")

BARS_BLOCK = ac.load_block("bars")
FRAME = ac.load_frame("fullscreen")


# 🔵 THE PAGE IS STILL RENDERED AND IT IS NO LONGER PASSED IN (11 Aug 2026). The
# assert took a `page` and never read it — it computed `visible_text(page)` into a
# variable nothing used — so it LOOKED like a render-time check and was filed with
# the ones that are. It is pure episode.json, which is what lets preflight_cards run
# it at the commission instead of meeting it at cards_render (EP20 C5). Rendering is
# kept here anyway: it proves these shapes still author, which is a real thing to know.
def render(notes):
    card = {"id": "C9", "block": "bars", "layout": "fullscreen",
            "eyebrow": "Nine", "headline": "IN TOWN", "headline_display": "In Town",
            "content": {"bars": [
                {"label": "Third favourite", "value": "5", "note": notes[0], "tone": ""},
                {"label": "Fifth favourite", "value": "12", "note": notes[1], "tone": "hi"}],
                "ask": None, "chip": None}}
    return card, ac.render_card(card, BARS_BLOCK, FRAME)


# FAIL FIRST: EP18's shipped C9 — the number lives only in the bar's WIDTH
card, page = render(["per cent profit on turnover", "per cent profit on turnover"])
try:
    ac.assert_measured_items_show_a_figure(card, BARS_BLOCK)
    caught = None
except ac.Halt as e:
    caught = str(e)
check("a bars card whose figures never render is CAUGHT", caught is not None,
      "this is exactly what EP18 shipped")
check("  and it names the item", bool(caught) and "Third favourite" in caught)
check("  and explains that `value` only sets the bar length",
      bool(caught) and "bar LENGTH" in caught)

# and the fixed version
card2, page2 = render(["5 per cent profit on turnover", "12 per cent profit on turnover"])
ok = True
try:
    ac.assert_measured_items_show_a_figure(card2, BARS_BLOCK)
except ac.Halt as e:
    ok = False
    print(f"        {e}")
check("the corrected card PASSES", ok)

# 🔴 THE NARROWING, AND WHY IT EXISTS. EP18's C3 SHIPPED and is right: it draws win
# counts as bar LENGTHS and labels them with strike rates. The first version of this
# guard demanded every figure be visible and halted C3 — a guard that bans a good card
# is the version somebody switches off (CLAUDE.md 4a). The rule is per ITEM: show SOME
# figure, not every figure.
card3, page3 = render(["26% strike rate", "10% strike rate"])
ok3 = True
try:
    ac.assert_measured_items_show_a_figure(card3, BARS_BLOCK)
except ac.Halt as e:
    ok3 = False
    print(f"        {e}")
check("EP18 C3's shape — measured by length, labelled with a DIFFERENT figure — passes",
      ok3, "the bar is the picture and the note is the number; both are wanted")

print(f"\n{'=' * 66}")
print("PROVED (fail-first)" if not FAILED else f"FAILURES: {FAILED}")
sys.exit(1 if FAILED else 0)
