#!/usr/bin/env python3
"""test_twoway_split.py — the two-way split reproduces the article, and loses nothing.

    python engine/test_twoway_split.py

Step 1 of the two-way build order is the one step that can be proved before a single
credit is spent, so it is proved HARD. Three assertions the brief asks for, and three
more that guard the ways this step can be wrong expensively:

  (a) THE DIALOGUE SURVIVES CHARACTER FOR CHARACTER. Every turn's text is found in the
      article body, in order — which catches an alteration — and everything BETWEEN the
      turns is whitespace or a speaker label and nothing else, which catches a loss. A
      test that only checked "the text appears" would pass while silently dropping a
      paragraph.
  (b) n TURNS, n−1 BREAKS, in each script. `interleave` asserts exactly this count
      against the detected silences and HALTS on a mismatch, so a script that leaves
      here with the wrong number of pauses costs two renders to discover.
  (c) NO LABEL IS SPOKEN. `BB:` in an avatar's mouth is the format announcing its own
      scaffolding.
  (d) THE STUDIO'S REAL FIDELITY GATE ACCEPTS BOTH SCRIPTS. `script_fidelity.check` is
      the gate an episode already has to pass; running it here proves the number fold
      is legal rather than asserting it.
  (e) THE FURNITURE GUARD ACTUALLY HALTS. `TAIL_MARKERS` is a short heuristic and will
      one day meet an article it does not know. The proof that this is survivable is a
      synthetic article whose tail carries a URL in a paragraph NO marker recognises —
      and the step refusing to write it.
  (f) A BYLINE THAT DOES NOT NAME TWO PEOPLE REFUSES. The speakers are derived from the
      article, and a derivation with no legal answer must say so rather than pick one.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import script_fidelity as sf                                     # noqa: E402
import twoway_split as tw                                        # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", str(pathlib.Path("G:/My Drive") / "PP Videos")))
EP = 49
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


# ── a synthetic two-way article, so the guards are provable off the Drive ──────────
def fake_capture(byline: str, body: str) -> str:
    return (f"# HEADLINE\n\n{byline}\n\nSource: http://example.invalid\n\n"
            f"{sf.MARKER_BEGIN}\n\nHEADLINE\n\n{body}\n\n{tw.MARKER_END}\n")


def main() -> int:
    hits = sorted((PP / "docs").glob(f"EP{EP:02d}-source-article-*.md"))
    if not hits:
        check(f"EP{EP}'s capture is on this machine", False,
              f"nothing matches {PP / 'docs'}/EP{EP:02d}-source-article-*.md")
        print(f"\ntwo-way split: {len(PASS)} passed, {len(FAIL)} failed")
        return 1
    capture = hits[0].read_text(encoding="utf-8")
    turns, speakers, narr = tw.split_turns(capture)
    body = capture.split(sf.MARKER_BEGIN, 1)[1].split(tw.MARKER_END, 1)[0]
    dialogue = [t for t in turns if t["speaker"] != "NARR"]
    scripts = {c: tw.script_for(c, turns) for c in speakers}

    print(f"-- the article: {hits[0].name} --")
    check("the two speakers are derived from the byline, not typed here",
          set(speakers) == {"BB", "BM"}, f"{speakers}")
    check("the article splits into turns at all", len(dialogue) >= 2, f"{len(dialogue)}")

    print("\n-- (a) THE DIALOGUE SURVIVES CHARACTER FOR CHARACTER --")
    # Nothing altered and nothing reordered: each turn is found verbatim, after the last.
    cursor, gaps, ok_order = 0, [], True
    for t in turns:
        i = body.find(t["text"], cursor)
        if i < 0:
            ok_order = False
            check(f"  turn n={t['n']} appears verbatim in the article, in order", False,
                  repr(t["text"][:60]))
            break
        gaps.append(body[cursor:i])
        cursor = i + len(t["text"])
    if ok_order:
        check("  every turn appears verbatim in the article, in article order", True)
    gaps.append(body[cursor:])

    # Nothing lost: what sits BETWEEN the turns is whitespace or a speaker label, full
    # stop. This is the half that catches a dropped paragraph.
    lab = tw.label_re(speakers)
    leftovers = [g for g in gaps if g.strip() and not re.fullmatch(
        r"\s*(?:" + "|".join(re.escape(x) for x in
                             list(speakers) + list(speakers.values())) + r")\s*:\s*", g)]
    check("  and nothing sits between them but whitespace and a speaker label",
          not leftovers, f"{[g[:60] for g in leftovers[:3]]}")

    # The literal form the brief asks for: re-interleave BB + BM in turns.json order and
    # compare against the article's dialogue — derived here independently, by removing
    # the NARR paragraphs and the labels from the body.
    expected = body
    for t in narr:
        expected = expected.replace(t["text"], "", 1)
    expected = "\n\n".join(
        lab.sub("", p.strip()) for p in re.split(r"\n\s*\n", expected) if p.strip())
    rejoined = "\n\n".join(t["text"] for t in dialogue)
    check("  BB + BM re-interleaved in turns.json order == the article's dialogue",
          rejoined == expected,
          f"{len(rejoined)} chars vs {len(expected)}")

    print("\n-- (b) n TURNS, n-1 BREAKS --")
    for code, name in speakers.items():
        n = sum(1 for t in turns if t["speaker"] == code)
        b = scripts[code].count(tw.BREAK)
        check(f"  {code} ({name}): {n} turns, {b} breaks", b == n - 1, f"expected {n - 1}")

    print("\n-- (c) NO SPEAKER LABEL IS SPOKEN --")
    labels = [f"{x}:" for x in list(speakers) + list(speakers.values())]
    for code in speakers:
        found = [l for l in labels if l in scripts[code]]
        check(f"  spoken-words-{code}.txt carries no label", not found, f"{found}")
    check("  and the full-name labels were read as labels, not as words",
          dialogue[0]["speaker"] == "BM" and not dialogue[0]["text"].startswith("Meadow"),
          f"{dialogue[0]['speaker']} / {dialogue[0]['text'][:40]!r}")

    print("\n-- (d) THE REAL FIDELITY GATE ACCEPTS BOTH SCRIPTS --")
    for code, name in speakers.items():
        out = sf.check(scripts[code], capture)
        check(f"  script_fidelity.check passes {code} ({name})", not out, f"{out[:1]}")

    print("\n-- A11: THE TWO READING RULES, AND THAT NEITHER NARROWED THE GATE --")
    check("  3YO reads 'three-year-old', not 'three why oh'",
          sf.fold("a $20,000 3YO filly claimer")
          == "a twenty thousand dollars three-year-old filly claimer",
          sf.fold("a $20,000 3YO filly claimer"))
    check("  a four-figure DISTANCE reads in hundreds",
          sf.fold("from 1200m to 1300m", unit_reading="hundreds")
          == "from twelve hundred metres to thirteen hundred metres",
          sf.fold("from 1200m to 1300m", unit_reading="hundreds"))
    check("  and MONEY on the same line is untouched by it",
          "eight thousand dollars" in sf.fold("1200m and $8000",
                                              unit_reading="hundreds"),
          sf.fold("1200m and $8000", unit_reading="hundreds"))
    check("  the one dial that used to do both still says 'eighty hundred dollars'"
          " — which is why there are two",
          "eighty hundred dollars" in sf.fold("$8000", reading="hundreds"))
    check("  unit_reading defaults to OFF, so the gate reads exactly as it did",
          sf.fold("from 1200m to 1300m")
          == "from one thousand two hundred metres to one thousand three hundred metres")
    # 🔒 The proof the YO rule is additive: the gate must still accept a script that
    # says the figure the OLD fold produced, and must still refuse an invented one.
    yo_art = fake_capture("By Ann Archer and Bob Bowman — PP - MARCH 1999",
                          "AA: A $20,000 3YO filly claimer.\n\nBB: Yes.")
    check("  a script saying 'three-year-old' now traces to the article's 3YO",
          not sf.check("A twenty thousand dollars three-year-old filly claimer.", yo_art),
          f"{sf.check('A twenty thousand dollars three-year-old filly claimer.', yo_art)[:1]}")
    check("  and an age the article never states still BLOCKS",
          bool(sf.check("A four-year-old filly claimer.", yo_art)))
    check("  both scripts on disk carry no bare digit but the SSML tags",
          all(not re.search(r"(?<!time=\")\b\d", s.replace(tw.BREAK, ""))
              for s in scripts.values()),
          {c: re.findall(r"\S*\d\S*", s.replace(tw.BREAK, ""))[:4]
           for c, s in scripts.items()})

    print("\n-- (e) THE FURNITURE GUARD HALTS, EVEN WHERE TAIL_MARKERS IS BLIND --")
    sneaky = fake_capture(
        "By Ann Archer and Bob Bowman — PRACTICAL PUNTING - MARCH 1999",
        "AA: First thing.\n\nBB: Second thing.\n\n"
        "Subscribe to the newsletter at www.example.invalid today.")
    caught = tail = None
    try:
        t2, s2, _ = tw.split_turns(sneaky)
        tail = any("www." in x["text"] for x in t2 if x["speaker"] == "NARR")
        for c in s2:
            tw.assert_no_furniture(tw.script_for(c, t2), c)
    except tw.Unsplittable as e:
        caught = str(e)
    check("  TAIL_MARKERS does NOT recognise a bare newsletter line (so the guard matters)",
          tail is False or tail is None, f"tail={tail}")
    check("  and the step REFUSES rather than shipping a URL to an avatar",
          caught is not None and "www.example.invalid" in (caught or ""),
          f"halted={caught is not None}; message did not quote the offending phrase: "
          f"{caught!r}")

    good = fake_capture("By Ann Archer and Bob Bowman — PRACTICAL PUNTING - MARCH 1999",
                        "AA: First thing.\n\nBB: Second thing.\n\n"
                        "* Ann Archer writes at www.example.invalid.")
    t3, s3, n3 = tw.split_turns(good)
    check("  the same line behind a recognised footnote marker is NARR, not speech",
          all("www." not in tw.script_for(c, t3) for c in s3)
          and any("www." in x["text"] for x in n3))

    print("\n-- (f) A BYLINE THAT CANNOT NAME TWO SPEAKERS REFUSES --")
    for byline, why in [("By Ann Archer — PRACTICAL PUNTING - MARCH 1999", "one author"),
                        ("PRACTICAL PUNTING - MARCH 1999", "no byline line"),
                        ("By Ann Archer and Alan Ashton — PP - MARCH 1999", "same initials")]:
        try:
            tw.split_turns(fake_capture(byline, "AA: One.\n\nBB: Two."))
            check(f"  refuses: {why}", False, "it did not raise")
        except tw.Unsplittable:
            check(f"  refuses: {why}", True)

    print(f"\ntwo-way split: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
