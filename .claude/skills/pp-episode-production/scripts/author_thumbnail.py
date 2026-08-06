#!/usr/bin/env python3
"""author_thumbnail.py — author the YouTube thumbnail page by PURE SUBSTITUTION.

    python author_thumbnail.py <episode.json> <thumbnail dir> [--force]

Same contract as author_cards.py and author_cover.py: it copies values out of
episode.json into the standing template's slots, or it fails. No LLM, no
inference, and the escaping comes from author_cards so there is one rule about
what a value may carry.

PLACEMENT IS A DEFAULT, NOT A DECISION (Jodie, 28 July 2026)
The template's own header calls placement "the craft — VIEW the hero first, then
decide". This does NOT halt waiting for a human to type coordinates: editing
placement fields in episode.json is not a browser action, so that would create a
halt Hugh cannot clear — a regression against the one number this whole exercise
is driving down. Instead the page is authored at the placement EP11 and EP12 both
converged on, rendered, and the engine raises a needs_look flag WITH THE PNG. He
looks at a picture and says yes or asks for a nudge.

Catching it there is also the cheap moment: an episode cannot currently go
backwards, so a bad crop found at the four-approvals gate is expensive, while the
same crop found mid-build is a flag the engine is still holding.

WHAT IS PER-IMAGE, AND ALL THAT IS
EP11 and EP12 are byte-identical in every tuned value — the scrim stops, the copy
box, the type sizes, the bar. The ONLY thing that differs is `object-position`:
EP11 sat at `center`, EP12 needed `center 62%` because its field sits low in the
frame. So that is the one placement value this script takes per episode, and the
one thing the look-at-it flag is really asking about.
"""
import argparse
import json
import os
import re
import shutil
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
TEMPLATE = os.path.join(ASSETS, "youtube-thumbnail-template.html")
GEN = "PP-GENERATED"
MARKER = (f"<!-- {GEN} by author_thumbnail.py — DO NOT HAND-EDIT. To change this "
          "thumbnail, change episode.json; to take it over by hand, delete this line. -->")

W, H = 1280, 720

SLOT_TITLE_TAG = "<title>PP YouTube Thumbnail — template</title>"
SLOT_L1 = '<div class="l1">Setup line</div>'
SLOT_L2 = '<div class="l2">Key word</div>'
SLOT_PART = '<div class="part">Part N</div><!-- DELETE on a non-series episode -->'
SLOT_STRAP = '<div class="strap">One-line hook the viewer wants</div>'
SLOT_HERO_POS = "object-position:center;display:block}"

# `center`, `center 62%`, or `40% 62%`. A closed shape, so no text can reach CSS.
FOCUS = re.compile(r"^(center|\d{1,3}%)( (center|\d{1,3}%))?$")

REQUIRED = ("l1", "l2", "part", "strap_break_after", "hero_focus")


def check(ep, th):
    pack = ep.get("packaging") or {}
    for k in REQUIRED:
        if k not in th:
            raise Halt(f"episode.json -> thumbnail is MISSING {k!r}. Write null if it is "
                       f"deliberately empty; a missing key halts on purpose, because "
                       f"absence records nothing.")
    for k in ("l1", "l2"):
        if not th.get(k):
            raise Halt(f"episode.json -> thumbnail.{k} must have a value.")
    if not pack.get("byline"):
        raise Halt("episode.json -> packaging.byline is empty, and it IS the thumbnail's "
                   "strap line. The thumbnail carries the approved words verbatim.")

    # THE WORDS GATE, same as the cover. Every asset uses the locked packaging.
    hook = f"{th['l1']} {th['l2']}".strip()
    if pack.get("hook") and hook != pack["hook"].strip():
        raise Halt(f"the thumbnail headline {hook!r} does not match the approved "
                   f"packaging.hook {pack['hook']!r}. The words were locked at the words "
                   f"gate; the thumbnail does not get to differ from them.")
    if th.get("part") and pack.get("ebook_title") and th["part"] not in pack["ebook_title"]:
        raise Halt(f"thumbnail.part {th['part']!r} does not appear in the approved "
                   f"packaging.ebook_title {pack['ebook_title']!r}.")
    if not FOCUS.match(str(th["hero_focus"] or "center")):
        raise Halt(f"thumbnail.hero_focus {th['hero_focus']!r} is not a CSS "
                   f"object-position like 'center' or 'center 62%'. It positions the "
                   f"photograph; it is a measurement, not a caption.")


def strap_html(ep, th):
    """The strap IS packaging.byline. Only where it BREAKS is a layout choice."""
    byline = ep["packaging"]["byline"]
    word = th.get("strap_break_after")
    if not word:
        return esc(byline)
    parts = byline.split()
    low = [w.strip(".,;:—-").lower() for w in parts]
    if word.lower() not in low:
        raise Halt(f"thumbnail.strap_break_after {word!r} is not a word in "
                   f"packaging.byline {byline!r}, so there is nowhere to break it.")
    i = low.index(word.lower())
    return esc(" ".join(parts[:i + 1])) + "<br>" + esc(" ".join(parts[i + 1:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_json")
    ap.add_argument("out_dir")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    ep = json.load(open(a.episode_json, encoding="utf-8"))
    th = ep.get("thumbnail") or {}
    check(ep, th)

    tpl = open(TEMPLATE, encoding="utf-8").read()
    focus = str(th["hero_focus"] or "center")
    subs = {
        SLOT_TITLE_TAG: (f"<title>{esc(ep.get('title') or '')} — YouTube thumbnail</title>\n"
                         f"<!-- pp-canvas: {W}x{H} — THE canvas; the engine renders at "
                         f"exactly this. -->\n{MARKER}"),
        SLOT_HERO_POS: f"object-position:{focus};display:block}}",
        SLOT_L1: f'<div class="l1">{esc(th["l1"])}</div>',
        SLOT_L2: f'<div class="l2">{esc(th["l2"])}</div>',
        SLOT_PART: (f'<div class="part">{esc(th["part"])}</div>' if th.get("part") else ""),
        SLOT_STRAP: f'<div class="strap">{strap_html(ep, th)}</div>',
    }
    for slot in subs:
        n = tpl.count(slot)
        if n != 1:
            raise Halt(f"the standing thumbnail template does not contain this slot "
                       f"exactly once (found {n}). The template has changed under this "
                       f"script — fix the pairing rather than loosening the match:\n"
                       f"  {slot[:90]}…")
    page = tpl
    for slot, val in subs.items():
        page = page.replace(slot, val)

    os.makedirs(a.out_dir, exist_ok=True)
    stem = (ep.get("episode") or "ep").lower().replace("pp-", "")
    out = os.path.join(a.out_dir, f"{stem}-thumbnail.html")
    existing_pages = [f for f in os.listdir(a.out_dir) if "thumbnail" in f and f.endswith(".html")]
    for f in existing_pages:
        if GEN not in open(os.path.join(a.out_dir, f), encoding="utf-8").read():
            print(f"· {f} left alone: hand-authored (no generated marker)")
            return
    # THE --force TRAP, closed the same way author_cards.py closes it: the freshly
    # rendered page is already in hand, so COMPARE IT rather than skipping on mere
    # existence. The engine never passes --force, so "already generated" meant a
    # packaging change could never reach the thumbnail — and the halt would look
    # identical before and after the fix. Nothing to keep in sync, and it cannot
    # go stale, because the comparison IS the definition.
    if os.path.exists(out) and not a.force:
        if open(out, encoding="utf-8").read() == page:
            print("· thumbnail left alone: unchanged — episode.json still says the same thing")
            return
        print("~ thumbnail re-authored — its definition changed")
    open(out, "w", encoding="utf-8", newline="\n").write(page)

    logo = os.path.join(a.out_dir, "pp-logo-on-dark.png")
    if not os.path.exists(logo):
        shutil.copyfile(os.path.join(ASSETS, "pp-logo-on-dark.png"), logo)
    print(f"authored {out} ({W}x{H}, hero_focus={focus})")


if __name__ == "__main__":
    try:
        main()
    except Halt as e:
        print(f"THUMBNAIL AUTHORING HALTED — {e}", file=sys.stderr)
        sys.exit(2)
