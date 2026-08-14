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
import packaging_gate as pg                                   # noqa: E402


def pack_hook(ep):
    """The headline's words. SEATED FROM THE RAIL by the engine before authoring —
    see providers.seat_packaging_from_rail. Here it is simply the approved title."""
    return ((ep.get("packaging") or {}).get("hook") or "").strip()


def pack_byline(ep):
    return ((ep.get("packaging") or {}).get("byline") or "").strip()

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


# ══ THE SERIES PART NEVER REACHES THE HEADLINE ═══════════════════════════════
# 🔴 EP24, 14 Aug 2026. Its rail title was typed with BRACKETS — "Track Secrets
# (Part 4)" — so the whole string became `packaging.hook`. `check()` below insists the
# headline equals the hook, so the split had nowhere to put the part except the
# headline, and the thumbnail read:
#     TRACK SECRETS  /  (PART 4)  /  Part 4
# EP24 shipped with a thumbnail rebuilt by hand. EP21-23 are the SAME SERIES and came
# out right for one accidental reason: their titles have no brackets, so the hook was
# "Track Secrets" and the part had only one place to go.
#
# ⚠️ SO THE BUG WAS A PUNCTUATION MARK IN A TITLE FIELD, three episodes after the
# feature worked. The part is design furniture with a line of its own; it is taken off
# the headline HERE, before l1 and l2 exist, and printed only by `.part`.
def headline_and_part(ep, th):
    """(l1, l2, part, note) — the headline with the series part taken out of it.

    The part is stripped from the authored l1 and l2 individually, so it cannot survive
    in either. If that empties one of them — which is what "(PART 4)" as the whole of l2
    does — the headline is re-split from the hook: everything but the last word is the
    SETUP (l1, white), the last word is the PAYOFF (l2, orange). That is exactly the
    shape EP21, EP22 and EP23 were authored in, so the rule is the one already shipping.
    """
    pack = ep.get("packaging") or {}
    base_hook, part_hook = pg.strip_part(pack_hook(ep))
    l1 = pg.strip_part(str(th.get("l1") or ""))[0]
    l2 = pg.strip_part(str(th.get("l2") or ""))[0]
    part = str(th.get("part") or "").strip() or part_hook \
        or pg.strip_part(str(pack.get("ebook_title") or ""))[1]
    note = ""
    if part_hook and not (l1 and l2):
        words = base_hook.split()
        if len(words) >= 2:
            l1, l2 = " ".join(words[:-1]).upper(), words[-1].upper()
            note = (f"series title split: {pack_hook(ep)!r} -> l1 {l1!r} + l2 {l2!r}, "
                    f"with {part!r} on the part line and nowhere else")
    return l1, l2, part, note


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
    # ⚠️ CASE-FOLDED, AS THE TITLE CARD'S IDENTICAL GATE ALWAYS WAS (11 Aug 2026).
    # This one compared raw strings while author_title_card compared `.upper()`, and
    # nothing noticed while `packaging.hook` was written in capitals BY THE SAME PASS
    # that wrote l1 and l2. The moment the hook started coming from the RAIL — where
    # a title is sentence case, "Bill Benter Professional Gambler" — the two gates
    # disagreed and this one halted a correct thumbnail. The headline is set in caps
    # by the design; the comparison is about WORDS, not keystrokes.
    # ⚠️ COMPARED WITH THE SERIES PART TAKEN OFF BOTH SIDES. The part has a line of its
    # own, so a headline that leaves it out is not a headline that differs from the
    # approved words — and demanding the whole string is exactly what forced EP24's
    # "(PART 4)" into l2. The WORDS are still locked; only the part is elsewhere.
    hook = f"{th['l1']} {th['l2']}".strip()
    want = pg.strip_part(pack.get("hook") or "")[0]
    if pack.get("hook") and pg.strip_part(hook)[0].upper() != want.upper():
        raise Halt(f"the thumbnail headline {hook!r} does not match the approved "
                   f"packaging.hook {pack['hook']!r}. The words were locked at the words "
                   f"gate; the thumbnail does not get to differ from them.")
    # 🔴 AND THE PART MUST NOT BE IN THE HEADLINE AT ALL. EP24's l2 was literally
    # "(PART 4)" — a bracketed series position set 150px tall in orange, above a part
    # line saying the same thing. Brackets in the payoff word are the tell, and there is
    # no legitimate reason for them: l2 is ONE word of the approved title.
    if any(c in str(th["l2"]) for c in "()[]"):
        raise Halt(f"thumbnail.l2 is {th['l2']!r} and carries brackets. l2 is the PAYOFF "
                   f"word of the headline, set large in orange — a bracketed aside "
                   f"belongs in no headline, and a bracketed SERIES PART belongs on the "
                   f"part line, which prints it already. This is EP24's fault exactly.")
    if pg.strip_part(str(th["l1"]))[1] or pg.strip_part(str(th["l2"]))[1]:
        raise Halt(f"the series part is inside the headline ({th['l1']!r} / {th['l2']!r}) "
                   f"as well as on the part line, so the thumbnail would print it twice.")
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


# ── THE COPY BLOCK MUST FIT ABOVE THE LOGO ───────────────────────────────────
# 🔴 EP19, 9 Aug 2026, AND IT WOULD HAVE SHIPPED. The template's type sizes are tuned
# for a SHORT payoff — the slot's own placeholder is "Key word", and EP11's was
# "HIDDEN ACES". EP19's is "ACTION-HUNGRY PUNTERS": 21 characters, which wrapped to
# THREE lines in the 660px copy box and pushed everything below it down 264px. Measured
# on the authored page: "Part 1" ran 597->663 against a logo chip at 623->680, a 40px
# collision across the chip's whole width, and the strapline landed at 719->791 on a
# 720px canvas — entirely off the picture.
#     NOTHING WOULD HAVE CAUGHT IT. card_check does not look at thumbnails, autofit only
# touches card pages, and the needs_look flag asks about the HERO CROP — so a human is
# shown a broken thumbnail and asked a question about something else. This is the title
# card's ruling (Jodie, same day: a long approved title AUTO-FITS, it does not halt)
# applied to the one other place the approved title is set large.
#     THE WHOLE BLOCK SCALES BY ONE FACTOR, not just the offending line. l1, l2 and the
# part line are a designed hierarchy — the payoff is bigger than the setup — and
# shrinking only l2 would invert it. The strapline keeps its size: it is body copy at
# 29px, not display type.
FIT_STEP = 0.94        # 6% a pass, small enough to stop just past the edge
FIT_FLOOR = 0.55       # never below 55% of the tuned sizes
FIT_GAP = 8            # clear air between the copy block and the logo chip
FIT_MARK = "/* == PP-THUMB-FIT (measured, not hand-set) == */"


def fit_copy(path: str) -> str:
    """Render the authored page and step the copy block down until it clears the logo.

    Returns a one-line report. Measured in a real browser at the real canvas size,
    because the wrap point is the whole question and no arithmetic here knows it.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:                                       # noqa: BLE001
        return "type fit SKIPPED — no Playwright; the copy block was not measured"

    base = {"l1": 96.0, "l2": 150.0, "part": 75.0}
    measure = """() => {
      const r = s => { const e = document.querySelector(s);
                       if (!e) return null; const b = e.getBoundingClientRect();
                       return {t: b.top, b: b.bottom}; };
      return {part: r('.part'), strap: r('.strap'), logo: r('.logo'), l2: r('.l2')};
    }"""
    with sync_playwright() as pw:
        br = pw.chromium.launch(headless=True, args=["--hide-scrollbars"])
        pg = br.new_page(viewport={"width": W, "height": H})
        try:
            k, steps, m = 1.0, 0, None
            while steps <= 12:
                pg.goto("file:///" + os.path.abspath(path).replace("\\", "/")
                        + f"?fit={steps}")
                pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
                pg.wait_for_timeout(120)
                m = pg.evaluate(measure)
                if not m["logo"]:
                    return "type fit SKIPPED — no logo chip on this page to clear"
                # The strapline shares the logo's x-range, so the whole block sits ABOVE
                # the chip; the part line is checked too for the case with no strap.
                bottom = max(x["b"] for x in (m["part"], m["strap"]) if x)
                if bottom <= m["logo"]["t"] - FIT_GAP:
                    break
                nxt = k * FIT_STEP
                if nxt < FIT_FLOOR:
                    raise Halt(
                        f"the thumbnail copy cannot be made to fit above the logo chip "
                        f"even at {FIT_FLOOR:.0%} of the tuned type sizes: the block "
                        f"still reaches {bottom:.0f}px against a chip at "
                        f"{m['logo']['t']:.0f}px. thumbnail.l1/l2 are the approved "
                        f"packaging, so this is a human choice between the words and "
                        f"the layout, not something to shrink away.")
                k = nxt
                steps += 1
                css = (f"{FIT_MARK}\n"
                       + " ".join(f".{sel}{{font-size:{px * k:.1f}px !important}}"
                                  for sel, px in base.items()))
                src = open(path, encoding="utf-8").read()
                src = re.sub(re.escape(FIT_MARK) + r".*?(?=</style>)", "", src, flags=re.S)
                open(path, "w", encoding="utf-8", newline="\n").write(
                    src.replace("</style>", css + "\n</style>", 1))
        finally:
            br.close()
    if k == 1.0:
        return "type fit: not needed — the copy block already clears the logo chip"
    return (f"type fit: copy block scaled to {k:.0%} of the tuned sizes in {steps} "
            f"step(s) — l2 {base['l2'] * k:.0f}px — so the strapline and the part line "
            f"clear the logo chip. MEASURED on the rendered page, not chosen.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_json")
    ap.add_argument("out_dir")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    ep = json.load(open(a.episode_json, encoding="utf-8"))
    th = dict(ep.get("thumbnail") or {})
    # THE SPLIT HAPPENS BEFORE ANYTHING ELSE SEES l1/l2 — including check(), which is
    # what used to demand the part be in there. A copy, not a write-back: episode.json
    # is the author's record and this is a rendering rule, so the page is what changes.
    l1, l2, part, note = headline_and_part(ep, th)
    if note:
        th["l1"], th["l2"], th["part"] = l1, l2, part
        print(f"  {note}")
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

    # 🔴 GRADE THE PAGE, NOT THE FIELDS IT WAS BUILT FROM. `check()` above compares
    # episode.json values with each other; this reads the finished markup and asks
    # what each ZONE actually says. EP20 passed every field comparison and still put
    # the byline in the headline with an invented sentence underneath, because both
    # halves of every comparison came out of the same file in the same pass.
    #     The engine runs the same gate against the RAIL, which is stronger. This one
    # runs on a hand invocation too, where there is no rail to hand.
    faults = pg.page_faults("thumbnail", page, pack_hook(ep), pack_byline(ep),
                            ((ep.get("packaging") or {}).get("ebook_title") or ""))
    if faults:
        raise Halt("the authored thumbnail does not carry the approved packaging:\n  - "
                   + "\n  - ".join(faults))

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
    # THE LOGO IS STAGED FIRST because the fit measures against it — the copy block has
    # to clear the chip, and a chip that is not on the page yet cannot be cleared.
    logo = os.path.join(a.out_dir, "pp-logo-on-dark.png")
    if not os.path.exists(logo):
        shutil.copyfile(os.path.join(ASSETS, "pp-logo-on-dark.png"), logo)

    # ⚠️ FIT BEFORE COMPARING, or the --force trap above reopens by the back door: the
    # fit rewrites the file, so a page compared BEFORE fitting never equals the page on
    # disk, every run reports "re-authored", and the comparison stops meaning anything.
    # So the fitted page is built beside the target and only then compared.
    # ⚠️ IT MUST END .html AND MUST NOT CONTAIN "thumbnail".
    #   .html — Chromium renders a file:// URL by extension, and a page served as plain
    #     text has no elements at all: the first version of this used ".fitting" and the
    #     fit reported "no logo chip on this page to clear" on a page that has one.
    #   not "thumbnail" — `existing_pages` above globs *thumbnail*.html, so a crash that
    #     left this behind would make the next run think a second thumbnail page exists.
    #   same directory — hero.png and the logo are relative, and they must resolve.
    tmp = os.path.join(a.out_dir, ".pp-copyfit.html")
    open(tmp, "w", encoding="utf-8", newline="\n").write(page)
    try:
        report = fit_copy(tmp)
        page = open(tmp, encoding="utf-8").read()
    except BaseException:
        # A halt here means the words genuinely do not fit. Leave no half-fitted page
        # behind for the next run to mistake for a finished one.
        os.remove(tmp)
        raise
    if os.path.exists(out) and not a.force:
        if open(out, encoding="utf-8").read() == page:
            os.remove(tmp)
            print("· thumbnail left alone: unchanged — episode.json still says the same thing")
            return
        print("~ thumbnail re-authored — its definition changed")
    os.replace(tmp, out)
    print(f"  {report}")
    print(f"authored {out} ({W}x{H}, hero_focus={focus})")


if __name__ == "__main__":
    try:
        main()
    except Halt as e:
        print(f"THUMBNAIL AUTHORING HALTED — {e}", file=sys.stderr)
        sys.exit(2)
