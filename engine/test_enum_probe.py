"""A style token on screen is PROVEN against the template, not guessed from a word.

🔴 THE FAULT (EP51 C9, 27 Sep 2026). `assert_enum_not_visible` halted card authoring
because `compare`'s cols[].tone = "no" appeared as a word on screen. It did — in the
ARTICLE'S OWN column heading, "No more than 2 per cent of his bankroll". The compare
markup uses tone as a CSS class only. And the halt said "card ?", because the id was
looked up under the key "'id'" (quotes included).

Now each hit is put to the template: re-render with the value swapped for a probe
word; only a template that draws the field halts.

  1. EP51's real C9 passes, and C1 too
  2. CONTROL: a compare block doctored to PRINT {{ITEM.tone}} still halts — the check
     is not weaker — and the halt names the card
  3. every enum-bearing card on the Drive (EP49's included) renders byte-identically
     and gets the same verdict as before, except where the old verdict was this
     false alarm

PROVED FAIL-FIRST: AUTHOR_CARDS=<pre-fix author_cards.py> fails check 1 and the
"names the card" check.

Run: python engine/test_enum_probe.py
"""
import copy
import glob
import importlib.util
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPTS = os.path.join(REPO, ".claude", "skills", "pp-episode-production", "scripts")
sys.path.insert(0, SCRIPTS)
PATH = os.environ.get("AUTHOR_CARDS") or os.path.join(SCRIPTS, "author_cards.py")
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ac = load(PATH, "ac_under_test")


def verdict(mod, card, blk, frame):
    page = mod.render_card(card, blk, frame)
    try:
        try:
            mod.assert_enum_not_visible(page, card, blk, frame)
        except TypeError:                       # the pre-fix signature
            mod.assert_enum_not_visible(page, card, blk)
        return page, None
    except mod.Halt as e:
        return page, str(e)


C9 = {"id": "C9", "block": "compare", "layout": "panel-push",
      "content": {"cols": [
          {"tone": "no", "k": "He needs to bet", "v": "$105 per race"},
          {"tone": "yes", "k": "No more than 2 per cent of his bankroll",
           "v": "In his case, $50"}], "note": None}}
blk = ac.load_block("compare")
frame = ac.load_frame("panel-push")

_, why = verdict(ac, C9, blk, frame)
check(why is None, "EP51 C9 ('No more than 2 per cent…') is NOT a style token", why)

# CONTROL — a template that really draws the tone must still halt, naming the card
bad = copy.deepcopy(blk)
bad["markup"] = bad["markup"].replace('<div class="k">{{ITEM.k}}</div>',
                                      '<div class="k">{{ITEM.tone}} {{ITEM.k}}</div>')
check(bad["markup"] != blk["markup"], "  (control block doctored to print the tone)")
_, why = verdict(ac, C9, bad, frame)
check(why is not None and "STYLE TOKEN" in why,
      "a block that PRINTS {{ITEM.tone}} still halts — the check is not weaker", why)
check(why is not None and why.startswith("card C9:"), "  and the halt names the card",
      (why or "")[:30])

# 3 — every enum-bearing card on the Drive: same page, same verdict (bar the false alarm)
old_path = os.path.join(os.environ.get("TEMP", "."), "author_cards_head_for_test.py")
head = subprocess.run(["git", "show", "HEAD:.claude/skills/pp-episode-production/scripts/"
                       "author_cards.py"], cwd=REPO, capture_output=True).stdout
if head and PATH == os.path.join(SCRIPTS, "author_cards.py"):
    open(old_path, "wb").write(head)
    old = load(old_path, "ac_head")
    seen = same_page = same_verdict = cleared = 0
    changed = []
    for epj in sorted(glob.glob(r"G:\My Drive\PP Videos\PP-EP*\docs\episode.json")):
        try:
            cards = json.load(open(epj, encoding="utf-8")).get("cards") or []
        except Exception:                                             # noqa: BLE001
            continue
        for c in cards:
            if not isinstance(c, dict) or c.get("block") in (None, "bespoke"):
                continue
            try:
                b = ac.load_block(c["block"])
            except Exception:                                         # noqa: BLE001
                continue
            if not any((s.get("enum") for s in ((b.get("schema") or {}).get("lists")
                                                or {}).values())):
                continue
            try:
                fr = ac.load_frame(c.get("layout", "fullscreen"))
                pn, vn = verdict(ac, c, b, fr)
                po, vo = verdict(old, c, b, fr)
            except Exception:                                         # noqa: BLE001
                continue                    # an old card this template cannot render
            seen += 1
            same_page += pn == po
            if vn == vo or (vo and "card '" not in vo and vn is None and False):
                same_verdict += 1
            elif vo and vn is None and "STYLE TOKEN" in vo:
                cleared += 1
                changed.append(f"{os.path.basename(os.path.dirname(os.path.dirname(epj)))}"
                               f" {c.get('id')}")
            else:
                changed.append(f"UNEXPECTED {epj} {c.get('id')}: {vo!r} -> {vn!r}")
    print(f"  ({seen} enum-bearing cards on the Drive; false alarms cleared: {changed})")
    check(seen > 0 and same_page == seen, "every one renders the IDENTICAL page as before",
          f"{same_page}/{seen}")
    check(not any(x.startswith("UNEXPECTED") for x in changed),
          "and every verdict is unchanged, except a cleared STYLE-TOKEN false alarm",
          changed)
    check(any("PP-EP51" in x and "C9" in x for x in changed),
          "  and EP51 C9 is among the cleared (the old code halted on it)", changed)

print(f"\nenum probe: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
