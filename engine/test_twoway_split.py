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

import json
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
    body = body.replace(tw.SOFT_HYPHEN, "")   # typography; the turns carry none (11 Nov)
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
    # ONE definition of a label: the splitter's own (it widened on 11 Nov to `Barry (BM):`;
    # a second, hand-built list here would have gone stale the same day).
    lab = tw.label_re(speakers)
    leftovers = [g for g in gaps if g.strip() and not lab.fullmatch(g)]
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

    print("\n-- (g) EP56's PAGE, 11 Nov 2026: `Barry (BM):`, AN UNASTERISKED NOTE, SOFT HYPHENS --")
    # Each of these split WRONG, silently, before the fix: the bracketed labels folded the
    # first two turns into NARR, and the note ran on as the last speaker's words.
    art = fake_capture("By Ann Archer and Bob Bowman — PRACTICAL PUNTING - MARCH 1999",
                       "Ann (AA): First thing.\n\nMore of the first.\n\n"
                       "Bob (BB): Second thing.\n\nAA: Third improve­ment.\n\n"
                       "BB: Fourth.\n\nAnn Archer is one of the best writers, www.example.invalid.\n\n"
                       "Click here to read Part 2.")
    t4, s4, n4 = tw.split_turns(art)
    said = [(x["speaker"], x["text"]) for x in t4 if x["speaker"] != "NARR"]
    check("  `Ann (AA):` and `Bob (BB):` are read as labels",
          said[:2] == [("AA", "First thing.\n\nMore of the first."), ("BB", "Second thing.")],
          f"{said[:2]}")
    check("  four turns, alternating, nothing folded into NARR",
          [c for c, _ in said] == ["AA", "BB", "AA", "BB"], f"{[c for c, _ in said]}")
    check("  the unasterisked note about an author is NARR, not the last speaker's words",
          said[-1] == ("BB", "Fourth.") and any(x["text"].startswith("Ann Archer is")
                                                 for x in n4), f"{said[-1]}")
    try:
        for c in s4:
            tw.assert_no_furniture(tw.script_for(c, t4), c)
        halted = None
    except tw.Unsplittable as e:
        halted = str(e)
    check("  so the furniture guard passes both scripts (the note's URL never reaches one)",
          halted is None, halted)
    check("  the soft hyphen is gone from the turn text",
          said[2] == ("AA", "Third improvement.") and
          not any(tw.SOFT_HYPHEN in x["text"] for x in t4), f"{said[2]!r}")
    wrong = fake_capture("By Ann Archer and Bob Bowman — PRACTICAL PUNTING - MARCH 1999",
                         "AA: One.\n\nBob (AA): Not a label.\n\nBB: Two.")
    t5, _, _ = tw.split_turns(wrong)
    check("  a name with the OTHER speaker's initials (`Bob (AA):`) is not a label",
          [(x["speaker"], x["text"]) for x in t5][1:3]
          == [("AA", "One.\n\nBob (AA): Not a label."), ("BB", "Two.")],
          f"{[(x['speaker'], x['text']) for x in t5]}")
    mid = fake_capture("By Ann Archer and Bob Bowman — PRACTICAL PUNTING - MARCH 1999",
                       "AA: Ann is right, said Bob.\n\nBB: Ann Archer's view is sound.")
    t6, _, _ = tw.split_turns(mid)
    check("  a turn that merely MENTIONS an author is not cut as a note",
          [x["speaker"] for x in t6][1:] == ["AA", "BB"], f"{[x['speaker'] for x in t6]}")

    hit56 = sorted((PP / "docs").glob("EP56-source-article-*.md"))
    if hit56:
        cap56 = hit56[0].read_text(encoding="utf-8")
        t7, sp7, n7 = tw.split_turns(cap56)
        d7 = [x["speaker"] for x in t7 if x["speaker"] != "NARR"]
        check("  EP56 (real): ten turns, strictly alternating, Barry first",
              d7 == ["BM", "BB"] * 5, f"{d7}")
        check("  EP56 (real): four NARR rows — headline, standfirst, the note, the links",
              [x["text"][:20] for x in n7] == [
                  "CLASS, IMPROVEMENT A", "In the third article",
                  "Barry Meadow is one ", "Click here to read P"],
              f"{[x['text'][:20] for x in n7]}")
    else:
        print("  (EP56's capture is not on this machine — its real-article half is SKIPPED)")

    print("\n-- (h) SANCTIONED SUBSTITUTIONS: EXACTLY THE DECLARED CUTS, AND NOTHING ELSE --")
    art8 = fake_capture("By Ann Archer and Bob Bowman — PRACTICAL PUNTING - MARCH 1999",
                        "AA: See the Review at www.review.invalid. Then bet.\n\n"
                        "BB: Try the site (www.site.invalid) daily.")
    t8, s8, _ = tw.split_turns(art8)
    ok_sub = [{"id": "S1", "turn": 2, "speaker": "AA", "find": " at www.review.invalid",
               "replace": "", "before": "See the Review at www.review.invalid.",
               "after": "See the Review."},
              {"id": "S2", "turn": 3, "speaker": "BB", "find": " (www.site.invalid)",
               "replace": "", "before": "Try the site (www.site.invalid) daily.",
               "after": "Try the site daily."}]
    snapshot = [dict(x) for x in t8]
    r8 = tw.reading_turns(t8, ok_sub)
    check("  the declared cuts are applied, and only to the reading",
          [x["text"] for x in r8][1:] == ["See the Review. Then bet.", "Try the site daily."]
          and t8 == snapshot, f"{[x['text'] for x in r8]}")
    halted = None
    try:
        for c in s8:
            tw.assert_no_furniture(tw.script_for(c, r8), c)
    except tw.Unsplittable as e:
        halted = str(e)
    check("  the web-address guard passes the reading once the cuts are made", halted is None,
          halted)
    halted = None
    try:
        tw.assert_no_furniture(tw.script_for("BB", tw.reading_turns(t8, ok_sub[:1])), "BB")
    except tw.Unsplittable as e:
        halted = str(e)
    check("  and the guard is NOT relaxed: an address nobody ruled on still halts",
          halted is not None and "www.site.invalid" in halted, f"{halted!r}")
    check("  no substitutions -> the reading IS the article",
          tw.reading_turns(t8, []) == t8)

    def refuses(subs, why):
        try:
            tw.reading_turns(t8, subs)
            check(f"  refuses: {why}", False, "it did not raise")
        except tw.Unsplittable:
            check(f"  refuses: {why}", True)
    refuses([{**ok_sub[0], "speaker": "BB"}], "a cut declared for the other reader")
    refuses([{**ok_sub[0], "turn": 1}], "a cut on a NARR row")
    refuses([{**ok_sub[0], "find": " at www.nowhere.invalid"}], "words not in the turn")
    refuses([{**ok_sub[0], "find": "e"}], "words found more than once")
    refuses([{**ok_sub[0], "after": "See the Review!"}], "an 'after' the cut does not produce")
    refuses([{**ok_sub[0], "before": "Then bet."}], "a 'before' that does not hold the cut")
    sneaky = [dict(x) for x in r8]
    sneaky[2]["text"] = sneaky[2]["text"].replace("daily", "weekly")
    check("  the separate route catches a change outside the sanctioned sentences",
          bool(tw.reading_differences(t8, sneaky, ok_sub)))
    inside = [dict(x) for x in r8]
    inside[1]["text"] = inside[1]["text"].replace("See the Review.", "See the Revue.")
    check("  and a change INSIDE a sanctioned sentence that is not the approved 'after'",
          bool(tw.reading_differences(t8, inside, ok_sub)))

    # Both scripts are built from the reading: twoway_split's own build, and the furniture
    # step's composed host script. An AST walk of the CALLS, not a grep (CLAUDE.md 1a).
    import ast
    import twoway_furniture as tf
    for mod, fn in ((tw, "build"), (tf, "build")):
        tree = ast.parse(pathlib.Path(mod.__file__).read_text(encoding="utf-8"))
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn)
        calls = {(c.func.attr if isinstance(c.func, ast.Attribute) else getattr(c.func, "id", ""))
                 for c in ast.walk(node) if isinstance(c, ast.Call)}
        check(f"  {mod.__name__}.{fn}() calls reading_turns and load_substitutions",
              {"reading_turns", "load_substitutions"} <= calls, f"{sorted(calls)[:12]}")

    d56 = PP / "PP-EP56-Class-Improvement-and-Bias-Blues-Part-3" / "docs"
    if hit56 and (d56 / tw.SUBSTITUTIONS).is_file():
        subs56 = tw.load_substitutions(d56)
        tj56 = json.loads((d56 / "turns.json").read_text(encoding="utf-8"))["turns"]
        r56 = tw.reading_turns(tj56, subs56)
        changed = [a["n"] for a, b in zip(tj56, r56) if a["text"] != b["text"]]
        check("  EP56 (real): three substitutions, on turns 3, 4 and 10 only",
              len(subs56) == 3 and changed == [3, 4, 10], f"{changed}")
        lost = sum(a["words"] - b["words"] for a, b in zip(tj56, r56))
        check("  EP56 (real): four words come out (the three addresses and one 'at')",
              lost == 4, lost)
        halted = None
        try:
            for c in ("BB", "BM"):
                tw.assert_no_furniture(tw.script_for(c, r56), c)
        except tw.Unsplittable as e:
            halted = str(e)
        check("  EP56 (real): the web-address guard passes both scripts", halted is None,
              halted)
        check("  EP56 (real): the fidelity gate passes both scripts",
              all(not sf.check(tw.script_for(c, r56), cap56) for c in ("BB", "BM")))
        check("  EP56 (real): turns.json still equals a fresh split of the capture",
              tj56 == tw.split_turns(cap56)[0])
    else:
        print("  (EP56's substitutions are not on this machine — the real half is SKIPPED)")

    print(f"\ntwo-way split: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
