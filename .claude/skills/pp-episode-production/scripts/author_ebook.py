#!/usr/bin/env python3
"""author_ebook.py — author the e-book source page, and GATE its fidelity.

    python author_ebook.py <episode.json> <ebook dir> [--force] [--check-only]

WHAT THIS DOES, IN ONE LINE
---------------------------
It joins the standing shell (`assets/ebook-template.html`) to the episode's
hand-written ARTICLE BODY (`<ebook dir>/body.html`), and it refuses to do so if
the body has drifted from the source article.

THE DESIGN QUESTION THIS ANSWERS (Jodie, 28 Jul 2026)
-----------------------------------------------------
The e-book was the one asset in the self-authoring design with a real question in
it: where does the templated shell end and the editorial body begin? The shell,
the layout and the figures template cleanly. The BODY is §0a fidelity work —
reproducing "firstup" as one word and lower-case "joie Denise" is DELIBERATE
non-normalisation, and any automatic markup pass silently tidies exactly that.

Jodie's answer was **option A with a machine check, not a human halt**:

  * Claude Code writes the body file AT SCRIPT TIME, when the article is in hand
    and the fidelity work is already being done. So `ebook_pdf` does NOT stop and
    ask a person to read twenty paragraphs.
  * Instead THIS SCRIPT hard-fails if the body departs from the source article
    beyond a DECLARED list of departures.

Her reasoning, recorded so it is not re-litigated:

  * The rejected option asked a human to eyeball twenty paragraphs for BYTE-LEVEL
    faithfulness. That is what humans are worst at and machines are best at.
  * **EP11's "firstup" was normalised to "first-up" and got PAST human review.**
    The check that would have caught it is a string comparison.
  * The human check does not disappear. The e-book is already one of the four
    approvals, so a mid-build read would be a SECOND gate on the same document —
    and per PP-STANDARDS §WHAT DESERVES A GATE, "a gate is only worth having if
    the thing behind it is worth stopping an episode for".

WHAT THE FIDELITY CHECK ACTUALLY CHECKS
---------------------------------------
Every ARTICLE-PROSE paragraph in the body (a plain `<p>` with no class) must be
character-for-character equal to a paragraph of the source article, after the
DECLARED departures are applied to the article. In order. Each article paragraph
used at most once. Any article paragraph the body does not reproduce must be
declared in `ebook.omit_paragraphs[]`, quoted.

That single rule catches, without any of them being special-cased:
  * silent normalisation   — "firstup" -> "first-up" is not equal, so it halts
  * silent capitalisation  — "joie Denise" -> "Joie Denise" is not equal
  * an invented sentence   — matches no article paragraph
  * a dropped paragraph    — undeclared omission
  * a reordered argument   — the order pointer cannot go backwards

The comparison is EXACT. It does not fold case, quotes, dashes or punctuation,
because every one of those is a thing §0a says must survive. (That is the
opposite choice from `author_cards.py`'s `norm()`, which folds quotes and dashes
on purpose — a card TRACE is asking "is this sentence in the article", a much
weaker question than "is this the article".)

DEPARTURES ARE A FIXED VOCABULARY, NOT A REGEX FROM DATA
--------------------------------------------------------
`ebook.departures[]` holds NAMES from the table below. episode.json cannot
express an arbitrary transform, for the same reason `author_cards.py` has no LLM
in it: a departure engine that can do anything can hide anything. Adding a name
is a code change, which means a diff, a reviewer and Jodie's say-so.

A declared departure that changes NOTHING also halts. Otherwise the list becomes
boilerplate that gets copied forward and stops meaning anything.

NEVER OVERWRITE HAND-AUTHORED WORK — but ALWAYS run the check. The write is
skipped for a page that is hand-authored or already generated; the fidelity gate
runs every time regardless, because it is a gate and not an authoring step.
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
from author_cards import Halt                                   # noqa: E402

for _s in (sys.stdout, sys.stderr):        # the Windows console is cp1252
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                       # noqa: BLE001
        pass

ASSETS = os.path.join(os.path.dirname(HERE), "assets")
TEMPLATE = os.path.join(ASSETS, "ebook-template.html")
GEN = "PP-GENERATED"
MARKER = (f"<!-- {GEN} by author_ebook.py — DO NOT HAND-EDIT. The shell comes from "
          "assets/ebook-template.html and the article body from ebook/body.html; "
          "to change the book, change one of those. To take this page over by hand, "
          "delete this line. -->")

BODY_FILE = "body.html"

# The ONE slot, as an exact literal from the standing template. It must occur
# exactly once — see the template header for the 26 Jul 2026 bug where a script
# matched an example inside a comment and rewrote the comment.
SLOT_BODY = """<div class="kicker">Practical Punting Guide</div>
<h1 class="section">Book Title Here</h1>
<p class="lead">Opening lead paragraph.</p>
<p class="byline">Practical Punting, Month Year.</p>
<h2 class="rule">A Section Heading</h2>
<p>The article's own sentences, reproduced. Figures are the print renders of the
motion cards: <img class="illus" src="figure-1.png" alt="what the figure shows">.</p>"""

# Standing furniture: copied byte-identical, only when absent. Same find-or-build
# policy as stage_card_furniture() — an authored page that cannot render is no
# better than a missing one.
STANDING_ASSETS = ("ebook-logo-white.png", "ebook-logo.png", "marketing-hero.png")

# ------------------------------------------------------------------ departures
#
# name -> (transform applied to the ARTICLE text, plain-English description)
#
# EP12 declared exactly one, and it is the only one in the vocabulary today.
# EP11 declared normalising "firstup" to "first-up"; that is NO LONGER ALLOWED
# (PP-STANDARDS §0a, Jodie 27 Jul 2026) and is deliberately not representable
# here. There is no "normalise" departure and there must never be one.
DEPARTURES = {
    "spaced-hyphen-em-dash": (
        lambda s: s.replace(" - ", " — "),
        "the article's spaced hyphens ( - ) are set as em dashes for print"),
}

# ------------------------------------------------------------------ vocabulary
#
# The class vocabulary PP-STANDARDS §E-book names. Enforced, so the body cannot
# invent a class to escape the fidelity check by dressing article prose up as
# editorial furniture.
P_CLASSES = {None: "article prose", "lead": "editorial", "byline": "editorial",
             "note": "editorial", "pullquote": "quoted"}
IMG_CLASSES = {"illus", "illus portrait"}
DIV_CLASSES = {None, "kicker", "pagebreak", "avoid", "divider"}
TAGS_OK = {"p", "h1", "h2", "h3", "div", "span", "img", "br", "b", "strong",
           "i", "em", "blockquote", "a"}

# Text that belongs to the SHELL. If the body carries it too, the book would
# print the page twice — and the second copy would not be the approved one.
SHELL_TEXT = ("Please Gamble Responsibly", "Thanks for downloading",
              "What are you prepared to lose today")


def text_of(fragment: str) -> str:
    """Visible text of an HTML fragment: tags out, entities in, spaces collapsed.

    Whitespace collapsing is the ONLY normalisation. HTML cannot express the
    difference between a newline and a space, so a line break in the markup must
    not read as a difference in the prose. Everything else — case, quotes,
    hyphens, dashes, punctuation — is left exactly as written, because every one
    of those is a thing §0a says must survive.
    """
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def article_paragraphs(path: str) -> list[str]:
    """The source article's paragraphs, verbatim.

    Reads only between the ARTICLE TEXT BEGINS/ENDS markers, so the source file's
    provenance header, its fidelity notes and its 'HOW TO USE' block are never
    mistaken for prose the book has to reproduce.
    """
    raw = open(path, encoding="utf-8").read()
    if "---- ARTICLE TEXT BEGINS ----" not in raw or "---- ARTICLE TEXT ENDS ----" not in raw:
        raise Halt(f"the source article {os.path.basename(path)} has no "
                   f"'---- ARTICLE TEXT BEGINS ----' / '---- ARTICLE TEXT ENDS ----' "
                   f"markers, so there is no way to tell its prose from its header "
                   f"notes. Add the markers around the article text.")
    body = raw.split("---- ARTICLE TEXT BEGINS ----")[1] \
              .split("---- ARTICLE TEXT ENDS ----")[0]
    return [re.sub(r"\s+", " ", p.strip()) for p in re.split(r"\n\s*\n", body) if p.strip()]


def source_article_path(ep, ep_dir):
    """The verbatim source article named in episode.json -> source.

    Same resolution as author_cards.source_article_text, so the e-book and the
    cards are checked against the SAME file. If they could differ, a figure could
    be traced to one article while the book reproduced another.
    """
    m = re.search(r"(docs/[\w\-.]+\.md)", ep.get("source", ""))
    if not m:
        raise Halt("episode.json -> source does not name a 'Verbatim source: docs/....md' "
                   "file, so the e-book body cannot be checked against anything.")
    rel = m.group(1)
    for base in (os.path.dirname(os.path.dirname(os.path.abspath(ep_dir))), ep_dir):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    raise Halt(f"source article {rel!r} named in episode.json was not found on disk")


# ------------------------------------------------------------------ body parsing

def strip_comments(s: str) -> str:
    """Remove HTML comments before ANY matching. Comments are not content.

    FOUND BY USING THIS ON EP13, THE DAY AFTER IT WAS WRITTEN. EP13's body carries a
    header comment that explains the fidelity rule, and that explanation contains the
    words "every bare <p>". The paragraph regex matched that `<p>` inside the comment,
    ran on to the next real `</p>`, and reported the COMMENT as a body paragraph that
    is not in the source article.

    This is the same bug the cover template's header records from 26 Jul 2026: a script
    matched an EXAMPLE INSIDE A HEADER COMMENT and acted on it. It cost a real halt
    there and it cost one here. **A file's prose about its own markup will look like
    markup to anything that does not strip comments first.**

    The emitted page KEEPS its comments — they are the audit trail. Only the check
    strips them.
    """
    return re.sub(r"<!--.*?-->", " ", s, flags=re.S)


def parse_body(body: str):
    """Pull the body apart into what must be checked and what must not.

    Returns (prose, quoted, figures). `prose` is the plain `<p>` text in order —
    the article's own sentences. `quoted` is blockquote/pullquote text, which must
    be traceable into the article but need not be a whole paragraph. `figures` is
    the figure numbers referenced, in order.
    """
    body = strip_comments(body)
    for bad in ("<script", "<style", "<link", "<meta", "<iframe", "<html", "<body"):
        if bad in body.lower():
            raise Halt(f"ebook/{BODY_FILE} contains {bad!r}. The body is the ARTICLE BODY "
                       f"only — the shell (page setup, logo, cover slot, marketing and "
                       f"warranty pages) comes from assets/ebook-template.html and the "
                       f"body must not carry its own.")
    for phrase in SHELL_TEXT:
        if phrase.lower() in body.lower():
            raise Halt(f"ebook/{BODY_FILE} contains {phrase!r}, which belongs to a STANDING "
                       f"page in the shell. The marketing and warranty pages are copied "
                       f"byte-identical from the template; a second copy in the body would "
                       f"print the page twice and the second one would not be the approved "
                       f"text. Delete it from the body.")

    for tag in set(t.lower() for t in re.findall(r"<\s*([a-zA-Z][\w-]*)", body)):
        if tag not in TAGS_OK:
            raise Halt(f"ebook/{BODY_FILE} uses <{tag}>, which is not in the e-book class "
                       f"vocabulary (PP-STANDARDS §E-book). Allowed: "
                       f"{', '.join(sorted(TAGS_OK))}.")

    # headings must carry the template's classes, or the shell has no styling for them
    for tag, want in (("h1", "section"), ("h2", "rule")):
        for m in re.finditer(rf"<{tag}(\s[^>]*)?>", body):
            cls = re.search(r'class="([^"]*)"', m.group(0) or "")
            if not cls or cls.group(1).strip() != want:
                raise Halt(f'ebook/{BODY_FILE}: every <{tag}> must be '
                           f'<{tag} class="{want}"> (PP-STANDARDS §E-book names the class '
                           f'vocabulary, and the shell only styles those). Found: '
                           f'{m.group(0)}')

    for m in re.finditer(r"<img\b[^>]*>", body):
        cls = re.search(r'class="([^"]*)"', m.group(0))
        src = re.search(r'src="([^"]*)"', m.group(0))
        if not cls or cls.group(1).strip() not in IMG_CLASSES:
            raise Halt(f"ebook/{BODY_FILE}: a figure must be "
                       f'class="illus" (or "illus portrait"). Found: {m.group(0)[:120]}')
        if not src or not re.fullmatch(r"figure-(\d+)\.png", src.group(1)):
            raise Halt(f"ebook/{BODY_FILE}: a figure's src must be figure-N.png — the print "
                       f"render build_figures.py makes from the motion card, so the book "
                       f"cannot drift from the video. Found: {m.group(0)[:120]}")
        if 'alt="' not in m.group(0):
            raise Halt(f"ebook/{BODY_FILE}: every figure needs alt text. Found: "
                       f"{m.group(0)[:120]}")
    figures = [int(n) for n in re.findall(r'src="figure-(\d+)\.png"', body)]

    prose, quoted = [], []
    for m in re.finditer(r"<p(\s[^>]*)?>(.*?)</p>", body, re.S):
        cls = re.search(r'class="([^"]*)"', m.group(1) or "")
        key = cls.group(1).strip() if cls else None
        if key not in P_CLASSES:
            raise Halt(f'ebook/{BODY_FILE}: <p class="{key}"> is not in the e-book class '
                       f"vocabulary. Allowed: a bare <p> for the article's own prose, or "
                       f"{', '.join(repr(k) for k in P_CLASSES if k)}. A new class is not a "
                       f"way round the fidelity check.")
        t = text_of(m.group(2))
        if not t:
            continue
        (prose if key is None else quoted if key == "pullquote" else []).append(t)
    for m in re.finditer(r"<blockquote(\s[^>]*)?>(.*?)</blockquote>", body, re.S):
        t = text_of(m.group(2))
        if t:
            quoted.append(t)
    return prose, quoted, figures


# ------------------------------------------------------------------ the gate

def first_difference(a: str, b: str) -> str:
    """Point at the first word that differs. This message is the whole value of
    the check — 'the body does not match' is useless, 'firstup vs first-up' is
    the finding."""
    aw, bw = a.split(" "), b.split(" ")
    for i in range(max(len(aw), len(bw))):
        x = aw[i] if i < len(aw) else "<end of paragraph>"
        y = bw[i] if i < len(bw) else "<end of paragraph>"
        if x != y:
            lead = " ".join(aw[max(0, i - 6):i])
            return (f"word {i + 1}: the body says {x!r} where the article says {y!r}"
                    + (f"  (…{lead} ▸{x}◂ …)" if lead else ""))
    return "the paragraphs differ only in whitespace"


def closest(target: str, pool: list[str]) -> int:
    """Index of the article paragraph the body paragraph most likely IS.

    Compared as WORD sequences with autojunk off. Both matter: on character
    sequences longer than 200 chars difflib's autojunk heuristic treats any
    character occurring in more than 1% of the string as junk — which is every
    letter in a paragraph of prose — so a paragraph differing by ONE WORD scored
    0.32 and fell under the threshold. The failure message then said "no article
    paragraph is even close" about a paragraph that was 59 words out of 60
    identical, which is precisely the case this hint exists to explain.
    """
    import difflib
    tw = target.split(" ")
    best, score = -1, 0.0
    for i, cand in enumerate(pool):
        s = difflib.SequenceMatcher(None, tw, cand.split(" "), autojunk=False).ratio()
        if s > score:
            best, score = i, s
    return best if score > 0.5 else -1


def check_fidelity(prose, quoted, ep, article: list[str]):
    """HARD-FAIL unless the body reproduces the article, departures aside.

    Returns a plain-English report of what it verified, so a passing build says
    what it checked instead of only that it passed.
    """
    ebook = ep.get("ebook") or {}
    declared = ebook.get("departures")
    if declared is None:
        raise Halt("episode.json -> ebook.departures is MISSING. Write [] if the body "
                   "reproduces the article with no departures at all; a missing key halts "
                   "on purpose, because absence records nothing and this list is the only "
                   "thing standing between a print-friendly tidy and a silent rewrite.")
    if not isinstance(declared, list):
        raise Halt("episode.json -> ebook.departures must be a list of departure NAMES.")

    fns = []
    for name in declared:
        if name not in DEPARTURES:
            raise Halt(f"unknown declared departure {name!r}. Departures are a fixed "
                       f"vocabulary, not free text, so episode.json cannot describe an "
                       f"arbitrary transform. Known: "
                       f"{', '.join(sorted(DEPARTURES))}. Adding one is a code change.")
        fns.append((name, *DEPARTURES[name]))

    art = list(article)
    for name, fn, _desc in fns:
        after = [fn(p) for p in art]
        if after == art:
            raise Halt(f"declared departure {name!r} changes NOTHING in this article, so it "
                       f"is not a departure this episode makes. Remove it — a departure "
                       f"list that gets copied forward unchanged stops meaning anything.")
        art = after
    art_joined = " \n ".join(art)

    # omissions must be declared by QUOTING the paragraph, so nothing can be
    # dropped without writing down what was dropped
    omits = ebook.get("omit_paragraphs")
    if omits is None:
        raise Halt("episode.json -> ebook.omit_paragraphs is MISSING. Write [] if the body "
                   "reproduces every paragraph of the article. Most episodes need one "
                   "entry: the article's own headline line, which is set as the h1 section "
                   "heading rather than as body prose.")
    omitted = set()
    for quote in omits:
        hits = [i for i, p in enumerate(article) if p.startswith(quote.strip())]
        if len(hits) != 1:
            raise Halt(f"ebook.omit_paragraphs entry {quote[:60]!r} matches the start of "
                       f"{len(hits)} article paragraphs (needs exactly 1). Quote the "
                       f"paragraph you are leaving out, verbatim from the article — you do "
                       f"not get to drop a paragraph without saying which one.")
        omitted.add(hits[0])

    # every prose paragraph must be an article paragraph, in order, once each
    ai, matched = 0, 0
    for bp in prose:
        k = next((i for i in range(ai, len(art)) if art[i] == bp), None)
        if k is None:
            near = closest(bp, art[ai:])
            detail = (f"\n    Nearest article paragraph:\n      {first_difference(bp, art[ai + near])}"
                      if near >= 0 else
                      "\n    No article paragraph is even close — is this original prose? The "
                      "e-book body is the article, near-verbatim; the only original prose in "
                      "the whole episode is in the SPOKEN script.")
            raise Halt(
                f"E-BOOK FIDELITY: this body paragraph is not in the source article:\n"
                f"      {bp[:150]}{'…' if len(bp) > 150 else ''}{detail}\n"
                f"    Per PP-STANDARDS §0a we reproduce, we do not improve — if PP made a "
                f"mistake in 1995, it stands. If the change is a deliberate print tidy, it "
                f"has to be a DECLARED departure in episode.json -> ebook.departures, and "
                f"the vocabulary is: {', '.join(sorted(DEPARTURES))}.")
        for j in range(ai, k):
            if j not in omitted:
                raise Halt(
                    f"E-BOOK FIDELITY: the body skips an article paragraph that is not "
                    f"declared in ebook.omit_paragraphs:\n      {art[j][:150]}"
                    f"{'…' if len(art[j]) > 150 else ''}\n"
                    f"    §0a's mirror: never add what the article does not say, and never "
                    f"REMOVE what it does. Reproduce it, or declare the omission by quoting "
                    f"it.")
        ai = k + 1
        matched += 1
    for j in range(ai, len(art)):
        if j not in omitted:
            raise Halt(
                f"E-BOOK FIDELITY: the body stops before the end of the article. This "
                f"paragraph is neither reproduced nor declared as an omission:\n"
                f"      {art[j][:150]}{'…' if len(art[j]) > 150 else ''}")

    # quoted material need not be a whole paragraph, but must be IN the article
    for q in quoted:
        if q not in art_joined:
            raise Halt(f"E-BOOK FIDELITY: this pull-quote / blockquote is not in the source "
                       f"article verbatim:\n      {q[:150]}\n    A quote that is not a quote "
                       f"is an invention with quotation marks round it.")

    lines = [f"fidelity: {matched}/{len(article)} article paragraphs reproduced verbatim"]
    if omitted:
        lines.append(f"          {len(omitted)} declared omission(s): "
                     + "; ".join(article[i][:60] for i in sorted(omitted)))
    if quoted:
        lines.append(f"          {len(quoted)} quote(s) traced into the article")
    for name, _fn, desc in fns:
        lines.append(f"          departure {name!r}: {desc}")
    if not fns:
        lines.append("          no declared departures — the body is the article, exactly")
    return "\n".join(lines)


def check_figures(figures, ep):
    """The book's figures and episode.json's figures[] must agree, both ways."""
    want = [f["n"] for f in ep.get("figures", [])]
    if sorted(set(figures)) != sorted(set(want)):
        missing = sorted(set(want) - set(figures))
        extra = sorted(set(figures) - set(want))
        bits = []
        if missing:
            bits.append(f"episode.json maps figure(s) {missing} to cards, but the body never "
                        f"shows them")
        if extra:
            bits.append(f"the body shows figure(s) {extra}, which episode.json -> figures[] "
                        f"does not map to any card — so nothing renders them and the book "
                        f"would print a broken image")
        raise Halt("E-BOOK FIGURES: " + "; ".join(bits) + ".")
    if len(figures) != len(set(figures)):
        dupes = sorted({n for n in figures if figures.count(n) > 1})
        raise Halt(f"E-BOOK FIGURES: figure(s) {dupes} appear more than once in the body. "
                   f"Each figure is one card, shown once.")
    return f"figures: {len(figures)} in the body, matching episode.json -> figures[]"


# ------------------------------------------------------------------ main

def ep_stem(out_dir) -> str:
    """`PP-EPNN`, from the episode folder that contains ebook/.

    Taken from the folder rather than an episode.json field, and reduced to the
    bare `PP-EPNN` stem, because the folder is RENAMED at Stage-8 close-out
    (`PP-EP12` -> `PP-EP12-Hidden-Aces-Part-2`) while the deliverables keep the
    stem. The skill's naming standard is explicit that nothing may depend on the
    full folder name; the `PP-EP(\\d+)` part is the bit that survives.
    """
    folder = os.path.basename(os.path.dirname(os.path.abspath(out_dir)))
    m = re.match(r"(PP-EP\d+)", folder)
    if not m:
        raise Halt(f"the e-book directory is not inside a PP-EPNN episode folder "
                   f"(found {folder!r}), so there is no name to give the book.")
    return m.group(1)


def stage_standing(out_dir):
    added = []
    for name in STANDING_ASSETS:
        src, dst = os.path.join(ASSETS, name), os.path.join(out_dir, name)
        if os.path.exists(dst) or not os.path.isfile(src):
            continue
        shutil.copyfile(src, dst)
        added.append(name)
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_json")
    ap.add_argument("out_dir", help="the episode's ebook/ directory")
    ap.add_argument("--force", action="store_true",
                    help="rewrite a page that already carries the generated marker")
    ap.add_argument("--check-only", action="store_true",
                    help="run the fidelity gate and write nothing")
    a = ap.parse_args()

    ep_dir = os.path.dirname(os.path.abspath(a.episode_json))
    ep = json.load(open(a.episode_json, encoding="utf-8"))

    body_path = os.path.join(a.out_dir, BODY_FILE)
    if not os.path.exists(body_path):
        # A DATA halt, the same shape as every other one: it names the file.
        raise Halt(
            f"the e-book article body is missing: {os.path.join(a.out_dir, BODY_FILE)}\n"
            f"  The BODY is editorial — it is the article reproduced near-verbatim, and it "
            f"is written at SCRIPT time, when the article is in hand and the fidelity work "
            f"is being done anyway. The shell, the layout and the figures are all authored "
            f"from the standing template; only this file is written by hand.\n"
            f"  Write it as the ARTICLE BODY only (no page setup, no cover, no marketing or "
            f"warranty pages — those come from assets/ebook-template.html) using the class "
            f"vocabulary in PP-STANDARDS §E-book.\n"
            f"  An episode built before this existed (EP11, EP12) has no body.html: its "
            f"body lives inside its finished *-ebook-source.html and can be lifted out of "
            f"it.")
    body = open(body_path, encoding="utf-8").read().strip()

    article = article_paragraphs(source_article_path(ep, ep_dir))
    prose, quoted, figures = parse_body(body)
    report = [check_fidelity(prose, quoted, ep, article), check_figures(figures, ep)]

    if a.check_only:
        print("\n".join(report))
        print("FIDELITY GATE: PASS")
        return

    tpl = open(TEMPLATE, encoding="utf-8").read()
    n = tpl.count(SLOT_BODY)
    if n != 1:
        raise Halt(f"the standing e-book template does not contain the ARTICLE BODY slot "
                   f"exactly once (found {n}). The template has changed under this script — "
                   f"fix the pairing rather than loosening the match.")

    ebook = ep.get("ebook") or {}
    deps = ebook.get("departures") or []
    src_name = os.path.basename(source_article_path(ep, ep_dir))
    head = (f"{MARKER}\n"
            f"<!-- pp-fidelity: body checked against {src_name} — "
            f"{len(prose)}/{len(article)} paragraphs verbatim; "
            f"declared departures: {', '.join(deps) if deps else 'none'}; "
            f"declared omissions: {len(ebook.get('omit_paragraphs') or [])}. "
            f"The check is in author_ebook.py and it HARD-FAILS; it is not advisory. -->")
    page = tpl.replace(SLOT_BODY, head + "\n" + body)

    os.makedirs(a.out_dir, exist_ok=True)
    out = os.path.join(a.out_dir, f"{ep_stem(a.out_dir)}-ebook-source.html")
    added = stage_standing(a.out_dir)

    if os.path.exists(out):
        existing = open(out, encoding="utf-8").read()
        if GEN not in existing:
            print("\n".join(report))
            print(f"· {os.path.basename(out)} left alone: hand-authored (no generated marker)")
            return
        if not a.force:
            print("\n".join(report))
            print(f"· {os.path.basename(out)} left alone: already generated — "
                  f"pass --force to redo")
            return
    open(out, "w", encoding="utf-8", newline="\n").write(page)
    print("\n".join(report))
    if added:
        print(f"staged standing asset(s): {', '.join(added)}")
    print(f"authored {out}")


if __name__ == "__main__":
    try:
        main()
    except Halt as e:
        print(f"E-BOOK AUTHORING HALTED — {e}", file=sys.stderr)
        sys.exit(2)
