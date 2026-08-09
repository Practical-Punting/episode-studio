#!/usr/bin/env python3
"""Negative tests for the E-BOOK FIDELITY GATE. Every one must HALT, in plain English.

    python test_author_ebook.py

WHY THIS FILE IS THE POINT OF THE WHOLE SLICE
---------------------------------------------
The fidelity gate replaced a proposed HUMAN read of the e-book body. A check that
only passes bodies which already pass is a green light I wrote myself, so every
way a body can silently drift has a test here that must FAIL.

THE TWO THAT MATTER MOST are the two §0a quirks Jodie named:
  * "firstup" as one word must survive — EP11 normalised it to "first-up",
    DISCLOSED it, and it got PAST human review.
  * lower-case "joie Denise" at first mention must survive.
Both are one-word changes in a sixty-word paragraph. That is exactly the class of
defect a person skimming twenty paragraphs will miss and a string comparison
cannot.

`--ep12` additionally runs the gate against EP12's REAL SHIPPED BODY and the real
source article, if the media root is on this machine. That is the golden test: the
reference implementation must pass unmodified.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import author_ebook as ae                                       # noqa: E402
from author_cards import Halt                                   # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                           # noqa: BLE001
        pass

PASS, FAIL = [], []

# A miniature article with all three shapes the real ones have: a headline line
# that becomes the h1 (and so is omitted from the body), spaced hyphens (the one
# declared departure), and the two §0a quirks.
ARTICLE = """# TEST ARTICLE
Notes above the marker must never be treated as prose.

---- ARTICLE TEXT BEGINS ----

TEST: FIRST-UPPERS AND THE VALUE FACTOR

Most horses resuming from a spell - say 60 days or more - will lose at their first run back. That's an iron-clad fact.

How many times has it won firstup? Is it capable of repeating the performance?

A recent instance of this was joie Denise's first-up win at Randwick in August. She was DOWN in class.

---- ARTICLE TEXT ENDS ----
"""

GOOD_BODY = """<div class="kicker">Practical Punting Guide</div>
<h1 class="section">Test Episode</h1>
<p class="lead">An editorial lead line, not article prose.</p>
<p class="byline">Practical Punting, December 1995.</p>

<h2 class="rule">First-Uppers &mdash; Be Careful</h2>
<p>Most horses resuming from a spell &mdash; say 60 days or more &mdash; will lose at their first run back. That's an iron-clad fact.</p>
<img class="illus" src="figure-1.png" alt="Most of them lose">
<p>How many times has it won firstup? Is it capable of repeating the performance?</p>
<p>A recent instance of this was joie Denise's first-up win at Randwick in August. She was DOWN in class.</p>
<img class="illus" src="figure-2.png" alt="Joie Denise at Randwick">
"""

EPISODE = {
    "episode": "PP-EP99",
    "source": "Test article. Verbatim source: docs/test-source-article.md",
    "figures": [{"n": 1, "card": "C1"}, {"n": 2, "card": "C2"}],
    "ebook": {
        "departures": ["spaced-hyphen-em-dash"],
        "omit_paragraphs": ["TEST: FIRST-UPPERS AND THE VALUE FACTOR"],
    },
}


def build(tmp, body=GOOD_BODY, ep_over=None, article=ARTICLE, write_body=True,
          ebook_block=...):
    """Lay out a throwaway episode the way a real one is laid out on disk.

    The source article sits one level ABOVE the episode folder, in `docs/`, which
    is where the real ones live and where author_cards resolves them from — the
    e-book and the cards must be checked against the SAME file.
    """
    root = os.path.join(tmp, "media")
    ep_dir, ebook = os.path.join(root, "PP-EP99", "docs"), os.path.join(root, "PP-EP99", "ebook")
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    os.makedirs(ep_dir, exist_ok=True)
    os.makedirs(ebook, exist_ok=True)
    open(os.path.join(root, "docs", "test-source-article.md"), "w",
         encoding="utf-8", newline="\n").write(article)
    ep = json.loads(json.dumps(EPISODE))
    for k, v in (ep_over or {}).items():
        if isinstance(v, dict) and isinstance(ep.get(k), dict):
            ep[k].update(v)
        else:
            ep[k] = v
    if ebook_block is not ...:          # REPLACE the whole block, don't merge into it
        ep["ebook"] = ebook_block
    json.dump(ep, open(os.path.join(ep_dir, "episode.json"), "w", encoding="utf-8"))
    if write_body:
        open(os.path.join(ebook, ae.BODY_FILE), "w", encoding="utf-8",
             newline="\n").write(body)
    return os.path.join(ep_dir, "episode.json"), ebook


def run(epj, ebook, force=False):
    """Drive the real entry point, so the tests exercise what the engine calls."""
    argv = sys.argv
    sys.argv = ["author_ebook.py", epj, ebook] + (["--force"] if force else [])
    out = []
    real_print = print
    try:
        import builtins
        builtins.print = lambda *a, **k: out.append(" ".join(str(x) for x in a))
        ae.main()
        return "\n".join(out)
    finally:
        import builtins
        builtins.print = real_print
        sys.argv = argv


def case(name, expect, **kw):
    """`expect` is a phrase the halt message must contain — so the test checks the
    guard fired for the RIGHT reason, not merely that something went wrong."""
    with tempfile.TemporaryDirectory() as tmp:
        epj, ebook = build(tmp, **kw)
        try:
            run(epj, ebook)
        except Halt as e:
            if expect.lower() in str(e).lower():
                PASS.append((name, str(e).replace("\n", " ")))
            else:
                FAIL.append((name, f"halted, but not about {expect!r}: {e}"))
            return
        except SystemExit as e:                                  # argparse etc.
            FAIL.append((name, f"exited {e.code} instead of halting"))
            return
        FAIL.append((name, "DID NOT HALT — the guard did not fire"))


def ok(name, **kw):
    with tempfile.TemporaryDirectory() as tmp:
        epj, ebook = build(tmp, **kw)
        try:
            out = run(epj, ebook)
            PASS.append((name, out.replace("\n", " | ")))
            return out
        except Exception as e:                                   # noqa: BLE001
            FAIL.append((name, f"unexpected halt: {e}"))
            return ""


# ---------------------------------------------------------------- the control
out = ok("control: a faithful body is authored")
if out and "authored" not in out:
    FAIL.append(("control writes the page", f"no 'authored' line: {out}"))

# ---------------------------------------------------------------- §0a quirks
# THE EP11 BUG, EXACTLY. One word in sixty. Disclosed, human-reviewed, shipped.
case("silent normalisation 'firstup' -> 'first-up' HALTS",
     "'firstup?'", body=GOOD_BODY.replace("won firstup?", "won first-up?"))

# The other quirk Jodie named: the source is inconsistent and BOTH forms stand.
case("silent capitalisation 'joie Denise' -> 'Joie Denise' HALTS",
     "'joie", body=GOOD_BODY.replace("was joie Denise", "was Joie Denise"))

# A tidied apostrophe is the same class of defect: a print-friendly nicety that
# quietly edits the article. It is not in the departure vocabulary, so it halts.
case("a curly apostrophe swapped for the article's straight one HALTS",
     "not in the source article",
     body=GOOD_BODY.replace("That's an iron-clad", "That\u2019s an iron-clad"))

# ---------------------------------------------------------------- prose integrity
case("an INVENTED sentence in the body HALTS", "not in the source article",
     body=GOOD_BODY.replace("That's an iron-clad fact.",
                            "That's an iron-clad fact. Most punters never learn it."))

case("a DROPPED article paragraph HALTS", "skips an article paragraph",
     body=GOOD_BODY.replace(
         "<p>How many times has it won firstup? Is it capable of repeating the "
         "performance?</p>\n", ""))

case("REORDERED paragraphs HALT", "fidelity",
     body="""<div class="kicker">Practical Punting Guide</div>
<h1 class="section">Test Episode</h1>
<p>A recent instance of this was joie Denise's first-up win at Randwick in August. She was DOWN in class.</p>
<p>Most horses resuming from a spell &mdash; say 60 days or more &mdash; will lose at their first run back. That's an iron-clad fact.</p>
<p>How many times has it won firstup? Is it capable of repeating the performance?</p>
<img class="illus" src="figure-1.png" alt="a">
<img class="illus" src="figure-2.png" alt="b">
""")

# ---------------------------------------------------------------- departures
case("an UNDECLARED departure HALTS (em dashes with no declaration)",
     "not in the source article", ep_over={"ebook": {"departures": []}})

case("an UNKNOWN departure name HALTS", "unknown declared departure",
     ep_over={"ebook": {"departures": ["normalise-hyphens"]}})

case("a MISSING departures key HALTS", "ebook.departures is MISSING",
     ebook_block={"omit_paragraphs": ["TEST: FIRST-UPPERS AND THE VALUE FACTOR"]})

case("a MISSING omit_paragraphs key HALTS", "omit_paragraphs is MISSING",
     ebook_block={"departures": ["spaced-hyphen-em-dash"]})

case("a MISSING ebook block HALTS", "ebook.departures is MISSING",
     ebook_block=None)

case("a departure that changes NOTHING HALTS",
     "changes nothing",
     article=ARTICLE.replace(" - say 60 days or more - ", " \u2014 say 60 days or more \u2014 "),
     body=GOOD_BODY)

# ---------------------------------------------------------------- omissions
case("an UNDECLARED omission HALTS (the article's own headline line)",
     "skips an article paragraph", ep_over={"ebook": {"omit_paragraphs": []}})

case("an omission quoting text that is NOT in the article HALTS",
     "matches the start of 0",
     ep_over={"ebook": {"omit_paragraphs": ["A HEADLINE THAT WAS NEVER PRINTED"]}})

# ---------------------------------------------------------------- the vocabulary
case("a NEW <p> class cannot smuggle prose past the check",
     "not in the e-book class vocabulary",
     body=GOOD_BODY.replace('<p>How many', '<p class="bodytext">How many'))

case("an unstyled <h2> HALTS", 'class="rule"',
     body=GOOD_BODY.replace('<h2 class="rule">', "<h2>"))

case("a <script> in the body HALTS", "<script",
     body=GOOD_BODY + '<script>alert(1)</script>')

case("a second copy of a STANDING page in the body HALTS", "standing",
     body=GOOD_BODY + '<h1 class="section">Please Gamble Responsibly</h1>')

# A HEADER COMMENT THAT TALKS ABOUT MARKUP IS NOT MARKUP.
# Found by running the gate on EP13 the day after writing it: EP13's body header
# explains the fidelity rule and says "every bare <p>", so the paragraph regex matched
# inside the comment, ran on to the next real </p>, and reported the COMMENT as a body
# paragraph missing from the article. Same bug the cover template records from 26 Jul
# 2026 — a script matching an example inside a header comment. Comments are stripped
# before any matching now, and this is the test that keeps them stripped.
ok("a header comment mentioning <p> and a standing page does NOT break the check",
   body=("<!-- Every bare <p> in this file reproduces an article paragraph.\n"
         "     Do not add a Please Gamble Responsibly page here; the shell has one.\n"
         "     Figures are <img class=\"illus\" src=\"figure-1.png\"> renders. -->\n")
        + GOOD_BODY)

# ---------------------------------------------------------------- figures
case("a figure the body shows but episode.json does not map HALTS",
     "does not map to any card",
     body=GOOD_BODY + '<img class="illus" src="figure-7.png" alt="x">')

case("a figure episode.json maps but the body never shows HALTS",
     "never shows",
     ep_over={"figures": [{"n": 1, "card": "C1"}, {"n": 2, "card": "C2"},
                          {"n": 3, "card": "C3"}]})

case("the same figure twice HALTS", "more than once",
     body=GOOD_BODY + '<img class="illus" src="figure-1.png" alt="x">')

case("an illustration that is not a figure-N.png render HALTS", "figure-N.png",
     body=GOOD_BODY.replace('src="figure-1.png"', 'src="my-diagram.png"'))

# ---------------------------------------------------------------- the data halt
case("a MISSING body file HALTS, naming the file", ae.BODY_FILE, write_body=False)

# ---------------------------------------------------------------- never overwrite
with tempfile.TemporaryDirectory() as tmp:
    epj, ebook = build(tmp)
    run(epj, ebook)
    out_page = os.path.join(ebook, "PP-EP99-ebook-source.html")
    hand = "<!-- a human took this over -->\n<html>hand-authored</html>\n"
    open(out_page, "w", encoding="utf-8", newline="\n").write(hand)
    run(epj, ebook, force=True)                    # even with --force
    after = open(out_page, encoding="utf-8").read()
    (PASS if after == hand else FAIL).append(
        ("a hand-authored page is NEVER overwritten, even with --force",
         "left exactly as it was" if after == hand else "IT WAS OVERWRITTEN"))

# ⚠️ REWRITTEN — THIS CASE ASSERTED THE OPPOSITE OF THE DOCUMENTED CONTRACT, and had
# been failing ever since. It expected a hand tweak to a page STILL CARRYING THE
# PP-GENERATED MARKER to survive a re-run. The marker's own words are: "DO NOT
# HAND-EDIT … To take this page over by hand, delete this line." When the --force trap
# was closed, this page stopped being skipped on mere existence and started being
# COMPARED against what the definition produces — so an edit that leaves the marker in
# place is, by design, overwritten. The stale expectation was left red rather than
# resolved, which is the worst of both: a suite nobody can read as green.
#
# The contract has TWO halves and both are now asserted — marker kept, page rebuilt;
# marker deleted, page untouched (the case above).
with tempfile.TemporaryDirectory() as tmp:
    epj, ebook = build(tmp)
    run(epj, ebook)
    out_page = os.path.join(ebook, "PP-EP99-ebook-source.html")
    first = open(out_page, encoding="utf-8").read()
    open(out_page, "a", encoding="utf-8").write("\n<!-- a hand tweak -->\n")
    run(epj, ebook)                                # no --force
    after = open(out_page, encoding="utf-8").read()
    (PASS if after == first else FAIL).append(
        ("a tweak that KEEPS the generated marker is rebuilt from the definition",
         "rebuilt — the definition is the source of truth"
         if after == first else
         "THE TWEAK SURVIVED: an edit that leaves the marker in place must not persist, "
         "or the page and its definition can drift apart silently"))

# the standing furniture is staged, byte-identical
with tempfile.TemporaryDirectory() as tmp:
    epj, ebook = build(tmp)
    run(epj, ebook)
    bad = []
    for name in ae.STANDING_ASSETS:
        dst, src = os.path.join(ebook, name), os.path.join(ae.ASSETS, name)
        if not os.path.exists(dst):
            bad.append(f"{name} not staged")
        elif open(dst, "rb").read() != open(src, "rb").read():
            bad.append(f"{name} is NOT byte-identical to the standing asset")
    (PASS if not bad else FAIL).append(
        ("standing assets are staged byte-identical", "; ".join(bad) or
         ", ".join(ae.STANDING_ASSETS)))

# the ONE slot exists exactly once in the standing template
n = open(ae.TEMPLATE, encoding="utf-8").read().count(ae.SLOT_BODY)
(PASS if n == 1 else FAIL).append(
    ("the ARTICLE BODY slot occurs exactly once in the template", f"found {n}"))

# and the template carries the two things EP11/EP12 each hand-fixed
tpl = open(ae.TEMPLATE, encoding="utf-8").read()
mk, wr = tpl.find("REUSABLE MARKETING PAGE"), tpl.find("Please Gamble Responsibly")
(PASS if 0 < mk < wr else FAIL).append(
    ("template page order: marketing SECOND-LAST, warranty LAST",
     f"marketing at {mk}, warranty at {wr}"))
import re as _re
slots = _re.findall(r'<img src="(cover[^"]*)"', tpl)     # the markup, not the header note
(PASS if slots == ["cover.png"] else FAIL).append(
    ("template cover slot is cover.png (what the engine writes)", f"slots: {slots}"))

# ---------------------------------------------------------------- golden: EP12
if "--ep12" in sys.argv:
    import re
    MEDIA = os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos")
    shipped = os.path.join(MEDIA, "PP-EP12", "ebook", "PP-EP12-ebook-source.html")
    if not os.path.exists(shipped):
        print(f"(--ep12 skipped: {shipped} is not on this machine)")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "media")
            epd, ebk = os.path.join(root, "PP-EP12", "docs"), os.path.join(root, "PP-EP12", "ebook")
            os.makedirs(os.path.join(root, "docs")); os.makedirs(epd); os.makedirs(ebk)
            src = open(shipped, encoding="utf-8").read()
            i = src.index('<div class="kicker">Practical Punting Guide</div>')
            j = src.index("<!-- =================== END ARTICLE BODY")
            open(os.path.join(ebk, ae.BODY_FILE), "w", encoding="utf-8",
                 newline="\n").write(src[i:j].strip())
            ep = json.load(open(os.path.join(MEDIA, "PP-EP12", "docs", "episode.json"),
                                encoding="utf-8"))
            ep["episode"] = "PP-EP12"
            ep["ebook"] = {"departures": ["spaced-hyphen-em-dash"],
                           "omit_paragraphs": ["FIRST-UPPERS AND THE VALUE FACTOR"]}
            json.dump(ep, open(os.path.join(epd, "episode.json"), "w", encoding="utf-8"))
            art = re.search(r"(docs/[\w\-.]+\.md)", ep["source"]).group(1)
            shutil.copyfile(os.path.join(MEDIA, art), os.path.join(root, art))
            try:
                argv = sys.argv
                sys.argv = ["author_ebook.py", os.path.join(epd, "episode.json"), ebk,
                            "--check-only"]
                ae.main()
                sys.argv = argv
                PASS.append(("GOLDEN: EP12's shipped body passes the gate unmodified",
                             "20/21 paragraphs verbatim, 1 declared omission, "
                             "1 declared departure"))
            except Exception as e:                              # noqa: BLE001
                sys.argv = argv
                FAIL.append(("GOLDEN: EP12's shipped body passes the gate unmodified",
                             str(e).replace("\n", " ")))

# ── RECOGNISE, DON'T EXCUSE (EP19, 9 Aug 2026) ──────────────────────────────────
#
# check_fidelity compares the article against the body's BARE <p> paragraphs, so an
# article line the body sets as a HEADING read as a paragraph that had been dropped.
# The sanctioned answer was omit_paragraphs — and declaring a heading "omitted" tells
# the checker NOT TO LOOK FOR IT. EP19 ended up with seven declarations, five of them
# verified BY HAND, which is exactly what a gate is meant to replace.
#
# So the gate now recognises a heading and a figure-carried table, and VERIFIES both.
# These cases exist to stop "recognise" ever softening into "ignore": every good case
# below is paired with the near-miss that must still halt.
HEADING = "**A SUB-HEADING**"
ART_H = ARTICLE.replace(
    "How many times has it won firstup?",
    f"{HEADING}\n\nHow many times has it won firstup?")
BODY_H = GOOD_BODY.replace(
    "<p>How many times",
    f'<h2 class="rule">A SUB-HEADING</h2>\n<p>How many times')
H1_ONLY = {"departures": ["spaced-hyphen-em-dash"],
           "omit_paragraphs": ["TEST: FIRST-UPPERS AND THE VALUE FACTOR"]}

out = ok("a heading in the article, set as a heading in the body, needs NO declaration",
         article=ART_H, body=BODY_H, ebook_block=H1_ONLY)
if out and "set as a heading: 'A SUB-HEADING'" not in out:
    FAIL.append(("the recognised heading is REPORTED, so a build can be audited",
                 f"the report does not say what it verified: {out!r}"))
else:
    PASS.append(("the recognised heading is REPORTED, so a build can be audited",
                 "the report names the heading it checked"))

# THE CONTROL FOR THAT PASS. One word different and it must still halt — otherwise
# "recognised" would mean "any heading will do" and a typo would ship in 62px type.
case("a heading whose words DIFFER is still a skipped paragraph",
     "not the same words",
     article=ART_H,
     body=GOOD_BODY.replace("<p>How many times",
                            '<h2 class="rule">A SUB HEEDING</h2>\n<p>How many times'),
     ebook_block=H1_ONLY)

# …and with no heading at all, it must say what to do rather than only that it failed.
case("an article heading the body drops entirely still halts",
     "no heading carrying these words",
     article=ART_H, body=GOOD_BODY, ebook_block=H1_ONLY)

# THE HOLE, CLOSED FROM THE OTHER SIDE: a declaration for something on the page is
# now itself a halt, because it silently switches the verification off.
case("declaring a paragraph the body REPRODUCES is refused",
     "actually REPRODUCES",
     article=ART_H, body=BODY_H,
     ebook_block={"departures": ["spaced-hyphen-em-dash"],
                  "omit_paragraphs": ["TEST: FIRST-UPPERS AND THE VALUE FACTOR",
                                      HEADING]})

# ── a markdown table, carried by the figure that renders it ─────────────────────
TABLE = "| Last | 2nd-last | |---|---| | Win 9 pts | Win 6 pts |"
ART_T = ARTICLE.replace("How many times has it won firstup?",
                        f"{TABLE}\n\nHow many times has it won firstup?")
CARD_OK = [{"id": "C1", "content": {"columns": ["Last", "2nd-last"],
                                    "rows": [{"place": "Win",
                                              "points": ["9 pts", "6 pts"]}]}}]
# the same card with ONE number wrong — the figure is there, but it is not this table
CARD_BAD = [{"id": "C1", "content": {"columns": ["Last", "2nd-last"],
                                     "rows": [{"place": "Win",
                                               "points": ["9 pts", "5 pts"]}]}}]

ok("a table carried by its figure's card needs no declaration",
   article=ART_T, body=GOOD_BODY, ebook_block=H1_ONLY, ep_over={"cards": CARD_OK})

case("a table whose figure's card gets a number wrong still halts",
     "does not carry",
     article=ART_T, body=GOOD_BODY, ebook_block=H1_ONLY, ep_over={"cards": CARD_BAD})

print("\nE-BOOK FIDELITY GATE — every guard must fire\n" + "=" * 76)
for n, m in PASS:
    print(f"  ✓ {n}\n      {m[:150]}")
for n, m in FAIL:
    print(f"  ✗ {n}\n      {m[:220]}")
print("=" * 76)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
