#!/usr/bin/env python3
"""source_dupe_check.py — is this "new" article one we have already made?

    python source_dupe_check.py <candidate-source-article.md> [--media <PP Videos>]
                                [--report <out.md>] [--fail-at 40]

WHY THIS EXISTS — IT IS THE CHECK THAT WOULD HAVE CAUGHT EP12
--------------------------------------------------------------
EP12's first paste was **EP11's article text by mistake**. It scored **98.7%** against
EP11 and **nobody noticed by reading it** — the two parts of a series look alike, and a
human skimming a wall of racing prose for the second time in a week is the worst possible
detector. It was caught late, by hand, and only because someone went looking.

Nothing in the repo ran that comparison. The 98.7% figure lived in EP12's provenance
header as a NUMBER SOMEBODY TYPED, not as a check anybody could re-run. Per the
QC-per-fix rule — *a lesson written down but not enforced will recur; a lesson wired into
a check cannot* — it is a script now. Run it BEFORE creating a row, a folder or a script,
because everything downstream is wasted if the article is wrong.

WHAT IT COMPARES AGAINST
------------------------
Two corpora, because the archive is not uniform:
  * **source articles** — `docs/EP*-source-article-*.md`, the verbatim text between the
    `ARTICLE TEXT BEGINS/ENDS` markers. The direct comparison. Only EP11 and EP12 have
    one today; every new episode adds another.
  * **spoken tracks** — every episode's `docs/spoken-words.txt`. A PROXY, and a good one:
    the script is the article near-verbatim by the golden rule, so a duplicated article
    still scores high against the script made from it. This is what gives coverage of
    EP01-EP10, which have no source file. Expect a genuinely new article to score in the
    low single digits against these, and a duplicate to score far higher — but a script
    is not its article, so read a spoken-track hit as "look at this", not as proof.

THE TWO SIGNALS
---------------
  1. **Similarity** — difflib over WORD sequences, `autojunk=False`. Both matter: on
     character sequences longer than 200 chars difflib treats any character in >1% of the
     text as junk, which is every letter in prose, and scores near-identical paragraphs
     around 0.3.
  2. **Shared verbatim paragraphs** — the sharper signal, and the one EP12's own note
     quoted ("zero identical paragraphs"). Two articles by the same author about the same
     subject will share turns of phrase; they will not share whole paragraphs.
"""
import argparse
import difflib
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                          # noqa: BLE001
        pass

MIN_PARA_WORDS = 20          # a shared paragraph shorter than this is a stock phrase


def article_text(path):
    """The prose only. Never the provenance header — it is OUR writing, and two headers
    written to the same template would score high against each other and mean nothing."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    if "---- ARTICLE TEXT BEGINS ----" in raw:
        raw = raw.split("---- ARTICLE TEXT BEGINS ----")[1].split(
            "---- ARTICLE TEXT ENDS ----")[0]
    return raw


def paragraphs(text):
    return [re.sub(r"\s+", " ", p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip()]


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def similarity(a_words, b_words):
    return difflib.SequenceMatcher(None, a_words, b_words, autojunk=False).ratio()


def corpus(media):
    """(label, kind, text) for every prior episode text on disk."""
    out = []
    docs = os.path.join(media, "docs")
    if os.path.isdir(docs):
        for f in sorted(os.listdir(docs)):
            m = re.match(r"(EP\d+)-source-article-.*\.md$", f)
            if m:
                out.append((m.group(1), "source article", article_text(os.path.join(docs, f))))
    for folder in sorted(os.listdir(media)):
        m = re.match(r"(PP-EP\d+)", folder)
        if not m:
            continue
        p = os.path.join(media, folder, "docs", "spoken-words.txt")
        if os.path.isfile(p):
            out.append((m.group(1), "spoken track",
                        open(p, encoding="utf-8", errors="replace").read()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("--media", default=os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
    ap.add_argument("--report", help="write a markdown report here as well")
    ap.add_argument("--fail-at", type=float, default=40.0,
                    help="percent similarity that HARD-FAILS (default 40; EP12's bad "
                         "paste scored 98.7 and its good one 1.9, so the gap is wide)")
    a = ap.parse_args()

    cand = article_text(a.candidate)
    cw, cp = words(cand), paragraphs(cand)
    if not cw:
        print("the candidate article has no text between the ARTICLE TEXT markers",
              file=sys.stderr)
        return 2

    self_stem = re.match(r"(EP\d+)", os.path.basename(a.candidate))
    self_stem = self_stem.group(1) if self_stem else None

    rows, worst, problems = [], 0.0, []
    for label, kind, text in corpus(a.media):
        if self_stem and label.replace("PP-", "") == self_stem:
            continue                                   # never compare a file with itself
        pct = similarity(cw, words(text)) * 100
        other = set(paragraphs(text))
        shared = [p for p in cp if p in other and len(p.split()) >= MIN_PARA_WORDS]
        rows.append((label, kind, pct, len(shared)))
        worst = max(worst, pct)
        if pct >= a.fail_at:
            problems.append(f"{label} ({kind}): {pct:.1f}% similar — at or above the "
                            f"{a.fail_at:.0f}% fail line")
        if shared:
            problems.append(f"{label} ({kind}): {len(shared)} whole paragraph(s) shared "
                            f"verbatim, first one: {shared[0][:90]}…")

    rows.sort(key=lambda r: -r[2])
    lines = [f"# EP source duplicate check — {os.path.basename(a.candidate)}",
             "",
             f"Candidate: {len(cp)} paragraphs, {len(cw)} words.",
             f"Compared against {len(rows)} prior text(s). Fail line: {a.fail_at:.0f}%.",
             "",
             "| Prior | Kind | Similarity | Shared paragraphs |",
             "|---|---|---:|---:|"]
    for label, kind, pct, n in rows:
        lines.append(f"| {label} | {kind} | {pct:.1f}% | {n} |")
    lines += ["", f"**Highest similarity: {worst:.1f}%**", ""]
    lines.append("**VERDICT: FAIL — this looks like an article we have already used.**"
                 if problems else
                 "**VERDICT: PASS — no prior episode is close. This is a new article.**")
    for p in problems:
        lines.append(f"- ✗ {p}")
    report = "\n".join(lines)

    print(report)
    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        open(a.report, "w", encoding="utf-8", newline="\n").write(report + "\n")
        print(f"\nwrote {a.report}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
