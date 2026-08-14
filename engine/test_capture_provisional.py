#!/usr/bin/env python3
"""B2 — A THIN CAPTURE IS PROVISIONAL UNTIL A HUMAN SAYS YES.

    python engine/test_capture_provisional.py

Jodie's ruling, 14 Aug 2026: *capture best-effort text, but it does NOT become the
article of record until a HUMAN has looked and said yes.* No hard halt, and nothing
silently trusted.

🔴 THE RULE IT HAD TO BE RECONCILED WITH, not waved past. `capture_article`'s own header
says it "places a capture or it HALTS — it never produces a best-effort article of
record", and that rule is load-bearing: the capture is what `script_fidelity`,
`check_trace` and the e-book body are measured against for the life of the episode, so a
subtly wrong one does not fail — it redefines the truth and every downstream check then
agrees with it.

    THE DANGER WAS NEVER BEST-EFFORT TEXT. IT WAS BEST-EFFORT TEXT NOBODY LOOKED AT.

So a human's confirmation satisfies the rule exactly. What this suite proves is that the
confirmation is REAL — that between the refusal and the yes, nothing anywhere can mistake
the provisional text for the article of record.

THE CASES, and each names what it stands against:
  1. a SHORT page yields provisional text; a page with no article container does NOT
     (there is nothing to offer, and offering nothing is how a rule gets hollowed out)
  2. contamination and §0a JUDGEMENTS are still hard refusals — a person cannot certify
     text whose edges they cannot see
  3. the provisional file is INVISIBLE to find_capture(), which is the guarantee
  4. promotion happens ONLY with an answer recorded, never on a re-run or a reboot
  5. the promoted file SAYS it was confirmed by a human, so nobody later reads a short
     article as a clean automatic capture
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import capture_article as cap                                          # noqa: E402
import providers as P                                                  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         {why}" if not cond else ""))


def page(body_words: int, container=True):
    inner = " ".join(f"word{i}" for i in range(body_words))
    if not container:
        return "<div class='other'><p>" + inner + "</p></div>"
    return cap.CONTAINER + "<p>" + inner + "</p></div>"


# ── 1. WHICH REFUSALS CARRY TEXT ────────────────────────────────────────────────
print("\n-- 1. only a THIN capture offers its words --")
try:
    cap.extract(page(40))
    check("a short page is refused", False, "it was accepted")
except cap.Unrecognised as e:
    check("a short page is refused", True)
    check("  and it carries the words it DID read", bool(e.provisional),
          "nothing to offer a human")
    check("  which are the article's own",
          "word0" in (e.provisional or "") and "word39" in (e.provisional or ""))

try:
    cap.extract(page(500, container=False))
    check("a page with no article container is refused", False, "it was accepted")
except cap.Unrecognised as e:
    check("a page with no article container is refused", True)
    check("  and offers NOTHING — there is no article text to offer",
          e.provisional is None, f"provisional={str(e.provisional)[:60]!r}")

# ── 2. CONTAMINATION AND JUDGEMENTS STAY HARD REFUSALS ──────────────────────────
print("\n-- 2. what a person could not certify is still a hard refusal --")
leaked = cap.CONTAINER + "<p>" + ("word " * 400) + " Next To Jump </p></div>"
try:
    cap.extract(leaked)
    check("site furniture in the article text is refused", False, "accepted")
except cap.Unrecognised as e:
    check("site furniture in the article text is refused", True)
    check("  and is NOT offered for a yes/no — the text is contaminated",
          e.provisional is None)

nested = (cap.CONTAINER + "<p>" + ("word " * 400) + "</p>"
          "<ol><li>One.<ol><li>One a.</li></ol></li><li>Two.</li></ol></div>")
try:
    cap.extract(nested)
    check("a list inside a list is refused", False, "accepted")
except cap.Unrecognised as e:
    check("a list inside a list is refused", True)
    check("  and is NOT offered — the numbering is a §0a judgement",
          e.provisional is None)

# ── 3. THE PROVISIONAL FILE IS INVISIBLE TO THE THING THAT FINDS CAPTURES ───────
print("\n-- 3. nothing can mistake it for the article of record --")
with tempfile.TemporaryDirectory() as t:
    pp = Path(t)
    # ⚠️ DELIBERATELY NOT GIVEN A REAL EPISODE-FOLDER NAME, and do not "tidy" it back.
    # Nothing here parses the folder name — write_provisional() and
    # promote_provisional() are both handed the episode NUMBER — and a literal episode
    # folder name in a suite is what test_no_hardcoded_episode_paths refuses, because
    # the Stage-8 rename turns those into stale paths that read as code regressions.
    # The number is the id; the folder name is a guess (CLAUDE.md 0a).
    # Everything below runs in this temp tree; no real media folder is touched.
    ep_dir = pp / "episode-under-test"
    (pp / "docs").mkdir(parents=True)
    ep_dir.mkdir()
    body = " ".join(f"word{i}" for i in range(40))
    prov = cap.write_provisional(ep_dir, "https://example.com/a", 77, body,
                                 "only 40 words came out")
    check("the provisional file is written", prov.is_file(), str(prov))
    check("  INSIDE the episode folder, not PP Videos/docs",
          prov.parent == ep_dir / "docs", str(prov.parent))
    check("  and find_capture() cannot see it — the LOCATION is the guarantee",
          P.find_capture(pp, 77) is None, str(P.find_capture(pp, 77)))
    check("  it says on its face that it is not the article of record",
          "PROVISIONAL" in prov.read_text(encoding="utf-8")
          and "NOT THE ARTICLE OF RECORD" in prov.read_text(encoding="utf-8").upper())
    check("  and it keeps the words, so a human has something to compare",
          "word0" in prov.read_text(encoding="utf-8"))

    # ── 4. PROMOTION NEEDS A RECORDED ANSWER ────────────────────────────────────
    print("\n-- 4. only a HUMAN's yes promotes it --")
    stem = "capture-provisional-77"
    # the ask, as the engine writes it
    try:
        P.ask_once(ep_dir / "docs", stem, "the question")
        check("asking raises the flag", False, "it did not raise")
    except P.EngineFlag:
        check("asking raises the flag", True)
    check("  and records the ASK, which is not an answer",
          (ep_dir / "docs" / f".asked-{stem}").exists()
          and not (ep_dir / "docs" / f".answered-{stem}").exists())
    check("  CONTROL: with only an ask, find_capture is STILL empty",
          P.find_capture(pp, 77) is None)

    # a re-run must ask again, never promote
    try:
        P.ask_once(ep_dir / "docs", stem, "the question")
        check("  a re-run RE-ASKS rather than assuming an answer", False, "did not raise")
    except P.EngineFlag:
        check("  a re-run RE-ASKS rather than assuming an answer", True)

    # now the human clears the flag on the board
    P.answer_pending_gates(ep_dir)
    check("  clearing the flag records the ANSWER",
          (ep_dir / "docs" / f".answered-{stem}").exists())

    dest = cap.promote_provisional(ep_dir, pp, 77, "A Short Feature")
    check("promotion writes the article of record", dest.is_file(), str(dest))
    check("  and find_capture() finds it NOW, and not before",
          P.find_capture(pp, 77) == dest, str(P.find_capture(pp, 77)))
    check("  the provisional copy is GONE — one article of record, never two",
          not prov.exists())

    # ── 5. THE PROMOTED FILE TELLS THE TRUTH ABOUT ITSELF ───────────────────────
    print("\n-- 5. the file says how it got there --")
    txt = dest.read_text(encoding="utf-8")
    check("it says the automatic capture REFUSED it",
          "REFUSED" in txt.upper(), txt[:200])
    check("  and that a human confirmed it",
          "CONFIRMED BY A HUMAN" in txt.upper())
    check("  and it carries the markers everything downstream reads",
          "---- ARTICLE TEXT BEGINS ----" in txt
          and "---- ARTICLE TEXT ENDS ----" in txt)
    check("  and the words survived the round trip",
          "word0" in txt and "word39" in txt)
    # AND IT PARSES AS AN ARTICLE — asked of the reader the e-book gate actually uses,
    # not of a split written here. A promoted file that the fidelity gate cannot read
    # would be an article of record in name only.
    import author_ebook as ae                                          # noqa: PLC0415
    paras = ae.article_paragraphs(str(dest))
    check("  it parses as an article for the gate that reads it",
          len(paras) >= 1 and "word0" in paras[0], str(paras)[:120])

    # promoting twice must not overwrite the article of record
    cap.write_provisional(ep_dir, "https://example.com/a", 77, "different words", "why")
    try:
        cap.promote_provisional(ep_dir, pp, 77, "A Short Feature")
        check("  CONTROL: a second promotion cannot overwrite the record", False,
              "it overwrote")
    except cap.Unrecognised as e:
        check("  CONTROL: a second promotion cannot overwrite the record",
              "refusing to overwrite" in str(e), str(e)[:120])

print(f"\n{'=' * 70}")
print(f"B2 provisional capture: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
