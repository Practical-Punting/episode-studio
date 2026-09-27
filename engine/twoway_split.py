"""Split a two-way article into its turns, and write the two HeyGen scripts.

    python engine/twoway_split.py <ep_number> [--pp DIR] [--write]

Report-only by default; --write places three files in the episode's `docs/`:

    docs/turns.json           the manifest — the spine of everything downstream
    docs/spoken-words-BB.txt  Brian's turns only, article order, SSML pauses between
    docs/spoken-words-BM.txt  Barry's turns only, article order, SSML pauses between

Step 1 of the build order in `PP Videos/docs/PP-TWO-WAY-BUILD-SPEC.md` (as amended
15 Sep 2026). It is provable on the article alone: nothing is rendered and nothing is
spent, which is the whole reason this step is first.

🔴 DIALOGUE ONLY. No open, no close, no e-book CTA, no midroll, no outro, no
responsible-gambling line. Those are Gordon speaking AS GORDON, stepping out of the
reading (PP-TWO-WAY-PRESENTATION.md §2), they are NEW words Hugh has not seen, and they
are added in a later step. A file this step writes contains the article's words and
nothing else — which is also why `spoken-words-BM.txt` is complete as it stands: Steve
reads Barry's turns and never steps out of the reading at all.

── WHAT IS DERIVED, AND WHY NOTHING HERE IS TYPED PER EPISODE ────────────────────────
The speaker codes come from the capture's own byline. `By Brian Blackwell and Barry
Meadow — …` gives `BB` and `BM`, which is exactly what the article then uses as its
labels. Typing `{"BB": "Brian Blackwell"}` into this file would make it the second home
for a value the article already states (fault #2), and the first two-way episode with a
different pair of authors would inherit the first one's names.

⚠️ AND THE LABELS ARE NOT UNIFORM. EP49's article opens `Barry Meadow:` and `Brian
Blackwell:` in full and only then settles into `BM:` / `BB:`. A splitter that knew only
the initials would have folded the first two turns into the standfirst and lost them
without a word. So both spellings of every derived speaker are accepted, and the count
of turns is reported so a human can compare it against the page.

── 🔴 THE TAIL IS NOT DIALOGUE, AND IT COSTS CREDITS TO FIND THAT OUT LATE ───────────
These pages end with the magazine's own furniture — `NEXT MONTH: …`, the asterisked
author footnote, a newsletter website, `Click here to read Part 2.` A parser that runs
each turn "until the next label" swallows every one of them into the last speaker's
turn, and the first anyone hears of it is an avatar reading a URL aloud in a render
that has already been paid for.

So the tail is cut, by an explicit and SHORT list of markers (`TAIL_MARKERS`), and:

  · the cut is made at the FIRST marker and runs to the end of the article. That is
    what lets `Information on Barry's newsletter…` go without needing a pattern of its
    own — it is not recognised, it is simply after the footnote.
  · every paragraph cut is kept in `turns.json` as `NARR`, never discarded, and printed
    by this tool. A substitution nobody can see is how a library quietly rots.
  · and `assert_no_furniture()` is a HARD guard on the spoken text, not a pattern: a URL
    or a `Click here` reaching a script halts the step. The marker list is a heuristic
    and will meet an article it does not know; the guard is what makes that failure loud
    and cheap instead of silent and expensive.

── NUMBERS ARE SPOKEN BY THE STUDIO'S EXISTING FOLD, NOT BY A NEW OPINION ────────────
`script_fidelity.fold()` already turns the article's digits into the words a person
says, and `script_fidelity.check()` is the gate that decides whether a script's figures
trace. This step writes its spoken text by folding the article's own sentences, so the
figures trace BY CONSTRUCTION — and the test then runs the real gate over the result
rather than taking that on trust.

📌 `turns.json` keeps the text VERBATIM, digits and all. The fold is a reading for the
ear; the manifest is the article of record's own words, and the e-book, the fidelity
gate and the interleave all want those.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ep_paths                                                  # noqa: E402
import script_fidelity as sf                                     # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))

MARKER_END = "---- ARTICLE TEXT ENDS ----"

# The pause between every turn. 🔴 SSML, written straight into the script text, so it
# arrives with Jodie's paste and nothing has to be clicked — proven by render on
# 30 Aug 2026 (`docs/HEYGEN-HUMAN-STEP.md`). It is load-bearing three times over: it
# resets the delivery, it gives `interleave` a boundary it cannot miss, and the silence
# IS the idle footage. Keep it generous; it costs render seconds and returns an asset.
BREAK = '<break time="6s"/>'
"""🔴 SIX, NOT FOUR — RAISED ON MEASUREMENT, 18 Sep 2026.

Asked 4.000s and got 4.170/3.564 (Steve) and 4.082/3.977 (Gordon) on 16 Sep, then
2.246/3.898 and 3.973/4.868 on 17 Sep. HeyGen delivers the ask plus or minus nearly two
seconds, and two floors sit under that spread:

  · `twoway_interleave.GAP_MIN_S` = 2.0s. Under it a pause is not a turn boundary, the
    count is wrong and the build HALTS (correctly — a misaligned conversation cannot be
    recovered downstream). Steve's 2.246s cleared it by a quarter of a second.
  · `MIN_IDLE_S` = 3.5s after the 0.15s handles. Under it the pause banks no listening
    footage. THREE OF THE LAST FOUR PAUSES MISSED IT.

At 6s the same spread lands at 4.25-6.87: clear of the halt floor by 2.25s and of the
idle floor by 0.45s at worst. ⚠️ A pause is not a cost — it is where the listening
footage comes from, and the render seconds buy an asset."""

# How a figure carrying a unit is READ (Jodie, build spec A11, 15 Sep 2026). "hundreds"
# gives "twelve hundred metres" for `1200m`; money is deliberately NOT on this dial and
# stays "eight thousand dollars". See `script_fidelity.fold(unit_reading=…)`.
UNIT_READING = "hundreds"

# ⚠️ SSML SUPPORT IS PER VOICE. A pass on one voice proves nothing about another, and
# the failure mode is the avatar reading the tag aloud. The pair test (build spec A5)
# listens to both before an episode is spent.

# The magazine's own end-of-article furniture. SHORT on purpose: every entry here is a
# guess about a future article, and `assert_no_furniture` is what catches the ones this
# list does not know.
TAIL_MARKERS = (
    re.compile(r"^\s*NEXT\s+(?:MONTH|ISSUE|WEEK)\b", re.I),   # the trailer for part n+1
    re.compile(r"^\s*\*\s+\S"),                               # the asterisked footnote
    re.compile(r"Click here to read", re.I),                  # the site's own part links
)

# What must never reach a script. Not a pattern to classify by — a guard to halt on.
FURNITURE_IN_SPEECH = (
    re.compile(r"\bClick here\b", re.I),
    re.compile(r"\bwww\.", re.I),
    re.compile(r"https?://", re.I),
)


class Unsplittable(Exception):
    """The article is not one we know how to read as a dialogue. Nothing is written."""


# ───────────────────────────────────────────────────────────── the speakers ──

def speakers_from_byline(capture_text: str) -> dict[str, str]:
    """`By Brian Blackwell and Barry Meadow — …` -> {"BB": "Brian Blackwell", …}.

    In article order, which is the order the byline names them. Raises rather than
    guessing: a two-way article whose byline does not name two people is not a
    two-way article, and a best-effort answer here would be wrong quietly.
    """
    line = sf.byline(capture_text)
    if not line:
        raise Unsplittable(
            "the capture has no byline line, so the two speakers cannot be derived. "
            "A two-way article names both men in its own byline; if this one does "
            "not, it is not the article this step is for.")
    names = re.split(r"\s+and\s+|\s*,\s*", re.split(r"\s+[—–-]\s+", line[3:])[0].strip())
    names = [n.strip() for n in names if n.strip()]
    if len(names) != 2:
        raise Unsplittable(
            f"the byline names {len(names)} author(s) ({names!r}), and a two-way needs "
            "exactly two. Nothing is written.")
    codes = ["".join(w[0] for w in n.split() if w).upper()[:2] for n in names]
    if codes[0] == codes[1]:
        raise Unsplittable(
            f"both authors give the same initials {codes[0]!r}, so a label in the "
            "article cannot be attributed. Nothing is written.")
    return dict(zip(codes, names))


def label_re(speakers: dict[str, str]) -> re.Pattern:
    """A paragraph-opening speaker label — the initials OR the name in full.

    Both, because EP49's article uses both: it opens `Barry Meadow:` and `Brian
    Blackwell:` and only settles into `BM:` / `BB:` from the third turn on.
    """
    alts = []
    for code, name in speakers.items():
        alts.append(re.escape(code))
        alts.append(re.escape(name))
    # Longest first so `Brian Blackwell` is tried before anything that prefixes it.
    alts.sort(key=len, reverse=True)
    return re.compile(r"^\s*(" + "|".join(alts) + r")\s*:\s*")


# ─────────────────────────────────────────────────────────────── the article ──

def article_paragraphs(capture_text: str) -> list[str]:
    """The article's own paragraphs, between the markers, headline included.

    The headline sits inside the markers on purpose (Jodie, 9 Aug 2026 — an episode's
    title is the article's own words and the fidelity gate must be able to see it), so
    it arrives here as the first paragraph and is classified like any other unlabelled
    one: `NARR`, and never spoken by either reader.
    """
    if sf.MARKER_BEGIN not in capture_text:
        raise Unsplittable("the capture has no article-text marker; there is nothing "
                           "to split.")
    body = capture_text.split(sf.MARKER_BEGIN, 1)[1].split(MARKER_END, 1)[0]
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def tail_starts_at(paras: list[str]) -> int | None:
    """Index of the first end-of-article furniture paragraph, or None.

    From there to the end is furniture — see the header. Cutting at the FIRST marker
    rather than testing each paragraph is what carries the unrecognised ones out with
    the recognised ones.
    """
    for i, p in enumerate(paras):
        if any(m.search(p) for m in TAIL_MARKERS):
            return i
    return None


def split_turns(capture_text: str) -> tuple[list[dict], dict[str, str], list[dict]]:
    """(turns, speakers, narr) — the manifest, the derived speakers, the NARR rows.

    A turn opens at a labelled paragraph and runs through the unlabelled paragraphs
    that follow it, until the next label or the start of the tail. `text` is verbatim
    and carries no label: the label's whole content is the `speaker` field, and a value
    with two homes drifts.
    """
    speakers = speakers_from_byline(capture_text)
    lab = label_re(speakers)
    by_name = {name: code for code, name in speakers.items()}

    paras = article_paragraphs(capture_text)
    cut = tail_starts_at(paras)
    head, tail = (paras[:cut], paras[cut:]) if cut is not None else (paras, [])

    rows: list[dict] = []
    for p in head:
        m = lab.match(p)
        if m:
            token = m.group(1)
            code = token if token in speakers else by_name[token]
            rows.append({"speaker": code, "paras": [p[m.end():].strip()]})
        elif rows and rows[-1]["speaker"] != "NARR":
            rows[-1]["paras"].append(p)       # a continuation of the turn in progress
        else:
            rows.append({"speaker": "NARR", "paras": [p]})   # standfirst, intro, headline
    for p in tail:
        rows.append({"speaker": "NARR", "paras": [p]})

    # NARR paragraphs stay ONE ROW EACH — they are not a turn and they are not spoken,
    # and listing them individually is what lets a human check each one off the page.
    out: list[dict] = []
    for r in rows:
        if r["speaker"] == "NARR":
            for p in r["paras"]:
                out.append({"speaker": "NARR", "text": p})
        else:
            out.append({"speaker": r["speaker"], "text": "\n\n".join(r["paras"])})

    turns = []
    for n, r in enumerate(out, start=1):
        turns.append({"n": n, "speaker": r["speaker"],
                      "words": len(r["text"].split()), "text": r["text"]})
    if not any(t["speaker"] in speakers for t in turns):
        raise Unsplittable(
            f"no paragraph in the article opens with a speaker label for "
            f"{list(speakers)}. This article is not marked up as a dialogue.")
    narr = [t for t in turns if t["speaker"] == "NARR"]
    return turns, speakers, narr


# ───────────────────────────────────────────────────────────── the two scripts ──

def spoken(text: str) -> str:
    """One turn's verbatim text, written the way it is said.

    Two changes, both disclosed, and nothing else:

      1. **Numbers become the words to be spoken**, through the studio's existing
         `script_fidelity.fold()`. Folding the article's own sentence is what makes
         every figure trace by construction rather than by hope.
         🔴 `unit_reading="hundreds"` is Jodie's A11 ruling: a four-figure DISTANCE
         reads "twelve hundred metres", while money stays "eight thousand dollars".
         It is named here, at the point of choice, and the two dials are separate
         because one dial gave "eighty hundred dollars". `3YO` is handled inside the
         fold itself, because the gate has to be able to read it too.
      2. **The capture's `**bold**` markers come off.** They are the capture restoring
         the page's inline `<b>` sub-headings — typography, not words. The WORDS are
         the author's and stay exactly as printed; only the asterisks go, because an
         avatar will otherwise read them.
    """
    return sf.fold(re.sub(r"\*\*(.+?)\*\*", r"\1", text), unit_reading=UNIT_READING)


def assert_no_furniture(script_text: str, who: str) -> None:
    """Halt if the site's furniture reached a script. See the header.

    🔴 FAIL LOUDLY. This is the guard the `TAIL_MARKERS` heuristic is allowed to be
    imperfect behind, and it names what it found so the marker list can be widened
    on evidence rather than on imagination.
    """
    for pat in FURNITURE_IN_SPEECH:
        m = pat.search(script_text)
        if m:
            # The MATCH alone ('www.') is not enough to act on. Quote the phrase it sits
            # in, so the marker list can be widened on what the page actually said.
            lo, hi = max(0, m.start() - 40), min(len(script_text), m.end() + 40)
            ctx = re.sub(r"\s+", " ", script_text[lo:hi]).strip()
            raise Unsplittable(
                f"{who}'s script contains {m.group(0)!r}, in …{ctx}… "
                f"— that is the page's own "
                f"furniture, not the dialogue, and an avatar would read it aloud in a "
                f"render that has already been paid for. TAIL_MARKERS did not "
                f"recognise the paragraph it came from; widen it and run again.")


def script_for(code: str, turns: list[dict], limit: int | None = None) -> str:
    """One speaker's turns, article order, an SSML pause between every pair.

    `limit` takes only the first n turns — the PAIR TEST (build spec A5).
    """
    mine = [spoken(t["text"]) for t in turns if t["speaker"] == code]
    if limit:
        mine = mine[:limit]
    return f"\n\n{BREAK}\n\n".join(mine) + "\n"


PAIR_TEST_TURNS = 3
"""🔴 THE PAIR TEST IS THE ARTICLE'S OWN WORDS, NOT A TEST SCRIPT (build spec A5).
The first ~3 turns per speaker, verbatim, folded exactly as the real scripts are and
separated by the same SSML break. It proves four things on real material before an
episode is spent on it: that SSML is honoured on BOTH voices (support is per voice, and
the 30 Aug test does not record which one it ran on); that silence detection finds n−1
gaps; that `interleave` joins the two; and that a two-box preview exists to judge framing
by.

📌 **AND IT IS NOTHING NEW FOR HUGH.** The words are the article's, so the pair test
needs no approval that the episode itself will not already have had."""


# ────────────────────────────────────────────────────────────────── the step ──

def build(ep_number: int, pp: pathlib.Path = PP, write: bool = False) -> dict:
    hits = sorted((pp / "docs").glob(f"EP{ep_number:02d}-source-article-*.md"))
    if not hits:
        raise Unsplittable(
            f"no capture found at {pp / 'docs'}\\EP{ep_number:02d}-source-article-*.md. "
            "Run capture_article.py first — this step reads the article of record and "
            "never the web.")
    if len(hits) > 1:
        raise Unsplittable(f"{len(hits)} captures for EP{ep_number:02d}: "
                           f"{[h.name for h in hits]}. Which is the article of record?")
    capture = hits[0]
    text = capture.read_text(encoding="utf-8")

    turns, speakers, narr = split_turns(text)
    scripts = {code: script_for(code, turns) for code in speakers}
    for code, s in scripts.items():
        assert_no_furniture(s, speakers[code])

    ep_dir = ep_paths.episode_dir(ep_number, pp)
    docs = ep_dir / "docs"

    print(f"capture    : {capture.name}")
    print(f"episode    : {ep_dir.name}")
    print(f"speakers   : " + ", ".join(f"{c} = {n}" for c, n in speakers.items()))
    print()
    for code, name in speakers.items():
        mine = [t for t in turns if t["speaker"] == code]
        vw = sum(t["words"] for t in mine)
        sw = len(scripts[code].replace(BREAK, " ").split())
        print(f"{code} ({name}): {len(mine)} turns, {vw:,} words verbatim / "
              f"{sw:,} spoken, {scripts[code].count(BREAK)} breaks, "
              f"~{sw / 2.6 / 60:.1f} min at 2.6 words/s")
    print(f"NARR       : {len(narr)} paragraph(s), spoken by neither reader:")
    for t in narr:
        one = re.sub(r"\s+", " ", t["text"])
        print(f"   n={t['n']:<3} {one[:96]}{'…' if len(one) > 96 else ''}")

    short = [t for t in turns if t["speaker"] in speakers and t["words"] < 20]
    print(f"\nunder 20 words ({len(short)}) — the two-box candidates "
          f"(⚠️ `layout` is DERIVED at commission time from duration, card and b-roll; "
          f"this is a count, not a decision):")
    for t in short:
        print(f"   n={t['n']:<3} {t['speaker']}  {t['words']:>3}w  "
              f"{re.sub(r'\\s+', ' ', t['text'])[:70]}")

    out = {"turns.json": json.dumps({"turns": turns}, indent=2, ensure_ascii=False) + "\n"}
    for code in speakers:
        out[f"spoken-words-{code}.txt"] = scripts[code]
        pair = script_for(code, turns, limit=PAIR_TEST_TURNS)
        assert_no_furniture(pair, speakers[code])
        out[f"pairtest-{code}.txt"] = pair

    print("\npair test (build spec A5) — the first "
          f"{PAIR_TEST_TURNS} turns each, article words only:")
    for code, name in speakers.items():
        p = out[f"pairtest-{code}.txt"]
        w = len(p.replace(BREAK, " ").split())
        print(f"   pairtest-{code}.txt  {w:>4} words, {p.count(BREAK)} breaks, "
              f"~{w / 2.6 / 60:.1f} min at 2.6 words/s   ({name})")

    if write:
        docs.mkdir(parents=True, exist_ok=True)
        # 🔴 THIS STEP WRITES THE DIALOGUE, AND THE RENDER SCRIPT IS NOT ONLY THE
        # DIALOGUE. `twoway_furniture.py` composes the host's script from this
        # file's output PLUS the open, the e-book CTA, the midroll, the close and
        # the outro, and writes it back over `spoken-words-<host>.txt`. Re-running
        # this step would throw all of that away without a word, and the first
        # anyone would know is a render with no outro in it -- after it had been
        # paid for.
        #
        # So a composed script HALTS the write rather than losing it. The mark is
        # an HTML comment only that step can put there, never a phrase: a sentence
        # can occur in the words being checked, which is how an 'already patched'
        # guard fired on a docstring on 18 Sep.
        import twoway_furniture as tf                            # noqa: PLC0415
        clobber = [n for n in out
                   if n.startswith("spoken-words-") and tf.is_composed(docs / n)]
        if clobber:
            raise Unsplittable(
                f"{', '.join(clobber)} already carries the furniture — the open, "
                f"the e-book CTA, the midroll, the close and the outro. Writing "
                f"the dialogue over it would delete them silently. Re-run this "
                f"step with --write ONLY when the dialogue itself has changed, "
                f"and then run `python engine/twoway_furniture.py {ep_number} "
                f"--write` straight after it to put the furniture back.")
        for name, body in out.items():
            (docs / name).write_text(body, encoding="utf-8", newline="\n")
            print(f"\nWROTE {docs / name}")
    else:
        print(f"\nwould write {', '.join(out)} into {docs} (report only; pass --write)")
    return {"turns": turns, "speakers": speakers, "narr": narr,
            "scripts": scripts, "docs": docs, "capture": capture}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    try:
        build(a.ep_number, pathlib.Path(a.pp), a.write)
    except Unsplittable as e:
        print(f"\n🚫 {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
