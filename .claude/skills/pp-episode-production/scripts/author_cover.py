#!/usr/bin/env python3
"""author_cover.py — author ebook/cover-src/cover.html by PURE SUBSTITUTION.

    python author_cover.py <episode.json> <cover-src dir> [--force]
    python author_cover.py --canvas <cover.html>      # prints "W H"

Same contract as author_cards.py, and the same one property: it copies values
out of episode.json into the standing template's four per-episode slots, or it
fails. There is no LLM, no inference, and no code path that produces a string
absent from the file. The escaping is imported from author_cards so there is one
implementation of what a content value may carry.

EP12's hand-staged cover is the reference implementation. Against the standing
template it differs in exactly four things: the <title> tag, the .title markup,
the .subtitle and the .byline. Everything else — the whole flow-band layout that
made EP09's overlap impossible by construction — is copied untouched.

WHY THE SLOTS ARE MATCHED AS EXACT LITERALS
The template's own header records the bug this defends against: on 26 Jul 2026 a
substitution script matched the FIRST `div class="title"` in the file, which was
an EXAMPLE INSIDE THE HEADER COMMENT, and silently rewrote the comment instead of
the real title. So every slot here must occur EXACTLY ONCE in the template or the
build halts. A slot that matches twice is a bug, not something to guess at.

THE CANVAS COMES FROM ONE PLACE (28 Jul 2026)
The template declares `body{width:...;height:...}`. This script reads that and
writes it back as a machine-readable `pp-canvas` comment, and the engine renders
at exactly those dimensions. Before this, the page was built 1588x2238 while
render_ebook_cover() rendered 1600x2263, leaving a 12px white gutter down the
right edge and 25px along the bottom where the photo should have bled off. That
shipped on EP11 and EP12. It cannot recur, because there is no longer a second
number to disagree with the first.
"""
import argparse
import html
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
TEMPLATE = os.path.join(ASSETS, "ebook-cover-template.html")
GEN = "PP-GENERATED"
MARKER = (f"<!-- {GEN} by author_cover.py — DO NOT HAND-EDIT. To change this cover, "
          "change episode.json; to take it over by hand, delete this line. -->")

# The four per-episode slots, as exact literals from the standing template.
SLOT_TITLE_TAG = "<title>PP e-book cover — CANONICAL TEMPLATE</title>"
SLOT_TITLE = '<div class="title">Episode<br>Title Here</div>'
SLOT_SUBTITLE = ('<div class="subtitle">The promise line goes here &mdash; it may run to '
                 "<b>two or three lines</b> without ever colliding.</div>")
SLOT_BYLINE = ('<div class="byline">From the Practical Punting archives &middot; '
               "with Gordon</div>")

REQUIRED = ("title_setup", "title_payoff", "part", "part_inline", "byline")


def read_canvas(page_html: str):
    """The ONE place the cover's canvas is declared."""
    m = re.search(r"pp-canvas:\s*(\d+)x(\d+)", page_html)
    if not m:
        m = re.search(r"body\{width:(\d+)px;height:(\d+)px", page_html)
    if not m:
        raise Halt("the cover page does not declare its canvas — expected a "
                   "'pp-canvas: WxH' comment or a body{width:..px;height:..px} rule")
    return int(m.group(1)), int(m.group(2))


def build_title(cover) -> str:
    """Compose the .title markup from separate fields.

    The colour split and the series-part treatment are DECISIONS, so they are
    stored as data rather than inferred. `part_inline` records the rule in the
    template header: a long title keeps "— Part N" inline at full size; a short
    one drops the dash and sets Part N on its own line at about half size,
    because otherwise the dash lands alone at the start of a line and reads as
    a stray mark.
    """
    setup, payoff = esc(cover["title_setup"]), esc(cover["title_payoff"])
    out = f'<span class="w">{setup}</span> {payoff}' if setup else payoff
    part = cover.get("part")
    if part:
        out += (f"<br>&mdash; {esc(part)}" if cover.get("part_inline")
                else f'<span class="part">{esc(part)}</span>')
    return f'<div class="title">{out}</div>'


def check(ep, cover):
    """Guards. A data problem halts, naming the field."""
    pack = ep.get("packaging") or {}
    for k in REQUIRED:
        if k not in cover:
            raise Halt(f"episode.json -> cover is MISSING {k!r}. Write null if it is "
                       f"deliberately empty (as `part` is on a non-series episode); a "
                       f"missing key halts on purpose, because absence records nothing.")
    for k in ("title_setup", "title_payoff", "byline"):
        if not cover.get(k):
            raise Halt(f"episode.json -> cover.{k} must have a value.")
    if not pack.get("byline"):
        raise Halt("episode.json -> packaging.byline is empty, and it IS the cover's "
                   "subtitle. The cover must carry the approved words verbatim.")

    # THE WORDS GATE, ENFORCED. All downstream assets use the locked packaging
    # verbatim — that is the EP08 rework lesson. If the cover's hook does not
    # reassemble into packaging.hook, the cover has drifted from what was approved.
    hook = " ".join(x for x in (cover["title_setup"], cover["title_payoff"]) if x).strip()
    if pack.get("hook") and hook != pack["hook"].strip():
        raise Halt(f"the cover title {hook!r} does not match the approved "
                   f"packaging.hook {pack['hook']!r}. The words were locked at the words "
                   f"gate; the cover does not get to differ from them.")
    part = cover.get("part")
    if part and pack.get("ebook_title") and part not in pack["ebook_title"]:
        raise Halt(f"cover.part {part!r} does not appear in the approved "
                   f"packaging.ebook_title {pack['ebook_title']!r}.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_json", nargs="?")
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--canvas", help="print the WxH a cover page declares, then exit")
    a = ap.parse_args()

    if a.canvas:
        w, h = read_canvas(open(a.canvas, encoding="utf-8").read())
        print(f"{w} {h}")
        return
    if not (a.episode_json and a.out_dir):
        raise Halt("usage: author_cover.py <episode.json> <cover-src dir>")

    ep = json.load(open(a.episode_json, encoding="utf-8"))
    cover = ep.get("cover") or {}
    check(ep, cover)

    tpl = open(TEMPLATE, encoding="utf-8").read()
    w, h = read_canvas(tpl)

    ebook_title = (ep.get("packaging") or {}).get("ebook_title") or ep.get("title") or ""
    subs = {
        SLOT_TITLE_TAG: (f"<title>{esc(ebook_title)} — e-book cover</title>\n"
                         f"<!-- pp-canvas: {w}x{h} — THE canvas. The engine renders at "
                         f"exactly these dimensions (author_cover.py --canvas), so the "
                         f"page size and the render size cannot disagree. They used to: "
                         f"the page was 1588x2238 and the render 1600x2263, which left a "
                         f"12px white gutter down the right edge on EP11 and EP12. -->\n"
                         f"{MARKER}"),
        SLOT_TITLE: build_title(cover),
        SLOT_SUBTITLE: f'<div class="subtitle">{esc(ep["packaging"]["byline"])}</div>',
        SLOT_BYLINE: f'<div class="byline">{esc(cover["byline"])}</div>',
    }
    for slot in subs:
        n = tpl.count(slot)
        if n != 1:
            raise Halt(f"the standing cover template does not contain this slot exactly "
                       f"once (found {n}). The template has changed under this script — "
                       f"fix the pairing rather than loosening the match:\n  {slot[:90]}…")
    page = tpl
    for slot, val in subs.items():
        page = page.replace(slot, val)

    os.makedirs(a.out_dir, exist_ok=True)
    out = os.path.join(a.out_dir, "cover.html")
    if os.path.exists(out):
        existing = open(out, encoding="utf-8").read()
        if GEN not in existing:
            print(f"· cover.html left alone: hand-authored (no generated marker)")
            return
        if not a.force:
            print("· cover.html left alone: already generated — pass --force to redo")
            return
    open(out, "w", encoding="utf-8", newline="\n").write(page)

    # the logo the template's chip draws; hero.png is activated by the engine
    logo_dst = os.path.join(a.out_dir, "assets", "pp-logo-on-dark.png")
    if not os.path.exists(logo_dst):
        os.makedirs(os.path.dirname(logo_dst), exist_ok=True)
        shutil.copyfile(os.path.join(ASSETS, "pp-logo-on-dark.png"), logo_dst)
    print(f"authored {out} ({w}x{h})")


if __name__ == "__main__":
    try:
        main()
    except Halt as e:
        print(f"COVER AUTHORING HALTED — {e}", file=sys.stderr)
        sys.exit(2)
