"""episode_rulings.py — one episode's own script rulings: the hook, and the script notes.

    THE WRITER NEVER SAW THEM. (EP60, 17 Nov 2026.)

Hugh's Batch 1 rulings (EP60-EP69, GH02-GH04, approved 17 Nov 2026) are per-episode
decisions about the SCRIPT: open on this hook word for word; leave out these two
paragraphs; say this fact; add nothing beyond the article. The script commission read
nothing from the rail — not the hook, not the byline, not `notes` — and told the writer
to write its own opening. EP60's draft opened on the studio's own hook, kept the
paragraphs Hugh cut, and added a line nobody approved.

THIS MODULE IS THE ROUTE, AND THE ONE PARSER OF IT. Three readers use it and none of
them parses the notes for itself (CLAUDE.md fault 2):
    · `providers._commission_script`  -> `brief(ep)`, appended to the writer's brief;
    · the drafting pass, BEFORE an attempt is spent -> `notes_problems()`;
    · the drafting pass's gate, beside script_fidelity -> `check()`.
And `licensed_notes(ep)` joins the approved packaging that script_fidelity treats as a
second source of figures, so a fact the notes tell Gordon to say can be said.

WHAT IS ENFORCED, AND WHAT IS ONLY ASKED — named, not glossed:
    ENFORCED  the hook is the first thing Gordon says, word for word (case, punctuation
              and digits-as-words forgiven, on both sides, by the fidelity module's own
              fold);
    ENFORCED  a "Leave out:" paragraph is findable in the article (before any attempt),
              and the script neither lifts eight words in a row from it nor states a
              figure that ONLY that paragraph prints;
    ASKED     everything else in the notes ("no added lines", "never say tax", a credit).
              They are prose rulings; prose claims are not enumerable, which is the same
              boundary script_fidelity draws. They reach the writer verbatim and the human
              reads the result at the words gate.

🔒 NO HOOK AND NO NOTES MEANS NOTHING CHANGES. `brief()` returns "" and `check()` and
`notes_problems()` return [] — so an episode without them gets the brief, the gate and
the build it had before this file existed. test_episode_rulings.py holds that control.
"""
from __future__ import annotations

import re

import script_fidelity as sf
from preflight_cards import MARKER_BEGIN, MARKER_END, norm_words

# A paraphrase is not caught by this, by design (see the docstring). Eight words in a
# row is a LIFT: long enough that two different paragraphs do not share it by chance,
# and runs that a kept paragraph also contains are subtracted before looking.
LIFT_WORDS = 8
MIN_QUOTE_WORDS = 3

_LEAVE_OUT = re.compile(r"^\s*leave\s*out\s*:\s*(.+?)\s*$", re.I)
_QUOTED = re.compile(r"[\"“”]([^\"“”]+)[\"“”]")
_TRAIL = re.compile(r"[\s.…,;:!?]+$")


def hook_of(ep) -> str:
    return str((ep or {}).get("hook") or "").strip()


def notes_of(ep) -> str:
    return str((ep or {}).get("script_notes") or "").strip()


# ------------------------------------------------------------- the notes ------
def leave_out_quotes(notes: str) -> list[str]:
    """The paragraph openings named by "Leave out:" lines, in order.

    One line per paragraph. The opening words may be in straight or curly quotes, or
    bare; a trailing "…" or "..." is the operator saying "and the rest", not text.
    """
    out = []
    for line in (notes or "").splitlines():
        m = _LEAVE_OUT.match(line)
        if not m:
            continue
        rest = m.group(1)
        q = _QUOTED.search(rest)
        out.append(_TRAIL.sub("", q.group(1) if q else rest).strip())
    return [q for q in out if q]


def licensed_notes(ep) -> str:
    """The notes as a second source of FIGURES — minus the "Leave out:" lines.

    A leave-out line quotes the very paragraph Gordon must not say; licensing its words
    would license the figures the ruling exists to keep out.
    """
    return "\n".join(l for l in notes_of(ep).splitlines() if not _LEAVE_OUT.match(l))


def paragraphs(capture_text: str) -> list[str]:
    """The article body's paragraphs, as the capture lays them out (blank-line split)."""
    body = (capture_text or "").split(MARKER_BEGIN)[-1].split(MARKER_END)[0]
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def resolve(capture_text: str, notes: str) -> tuple[list[tuple[str, int]], list[str]]:
    """[(quote, paragraph index)] for every "Leave out:" line, and plain-English problems.

    A quote must name EXACTLY ONE paragraph: it matches the paragraph's opening words,
    or failing that a run of words inside it. None or several is a problem — the studio
    will not guess which paragraph Hugh meant.
    """
    paras = paragraphs(capture_text)
    toks = [norm_words(p) for p in paras]
    found, problems = [], []
    for q in leave_out_quotes(notes):
        nq = norm_words(q)
        if len(nq) < MIN_QUOTE_WORDS:
            problems.append(
                f'the script notes say to leave out "{q}", but that is too few words to '
                f"pick out one paragraph. Quote the first several words of the paragraph.")
            continue
        hits = [i for i, t in enumerate(toks) if t[:len(nq)] == nq]
        if not hits:
            hits = [i for i, t in enumerate(toks) if sf._in(nq, t)]
        if len(hits) == 1:
            found.append((q, hits[0]))
        elif not hits:
            problems.append(
                f'the script notes say to leave out the paragraph starting "{q}", and no '
                f"paragraph of the article has those words. Check the quote against the "
                f"article and correct the notes.")
        else:
            problems.append(
                f'the script notes say to leave out "{q}", and {len(hits)} paragraphs of '
                f"the article have those words. Quote more of the one that is meant.")
    return found, problems


def _span(paragraph: str, quote: str) -> tuple[int, int] | None:
    """Where the quoted words sit in the RAW paragraph text, or None.

    Exact substring first; otherwise the quote's words in order with any punctuation or
    spacing between them (so a missing full stop or curly quote does not lose the match)."""
    i = paragraph.find(quote)
    if i >= 0:
        return i, i + len(quote)
    words = re.findall(r"\w+", quote)
    if not words:
        return None
    m = re.search(r"\W*".join(re.escape(w) for w in words), paragraph, re.I)
    return (m.start(), m.end()) if m else None


def cuts(capture_text: str, notes: str) -> list[tuple[str, int, tuple[int, int] | None]]:
    """What each "Leave out:" line removes: (quote, paragraph index, span).

    🔴 A QUOTE THAT OPENS A PARAGRAPH REMOVES THE PARAGRAPH; ONE THAT SITS INSIDE A
    PARAGRAPH REMOVES ONLY THOSE WORDS (span is set). (EP61, 18 Nov 2026.) Hugh's note
    `Leave out: "(stats from www.racingandsports.com.au)"` meant the bracketed credit at
    the END of the paragraph that gives gate 1's 13.8% from 405 races — and this used to
    cut the whole paragraph, so the gate told the writer to drop the article's opening
    Rosehill figure. The writer refused, rightly, three times. EP60's quotes open their
    paragraphs, so EP60 is cut exactly as before."""
    paras = paragraphs(capture_text)
    out = []
    for q, i in resolve(capture_text, notes)[0]:
        nq, nt = norm_words(q), norm_words(paras[i])
        if nt[:len(nq)] == nq:
            out.append((q, i, None))
        else:
            out.append((q, i, _span(paras[i], q)))
    return out


def notes_problems(capture_text: str, ep) -> list[str]:
    """Checked BEFORE an attempt is spent: notes the writer could not possibly obey.

    A notes quote that names no paragraph is the NOTES' fault, not the writer's, and
    rejecting three drafts over it would burn the bound on something no draft can fix.
    """
    return resolve(capture_text, notes_of(ep))[1] if notes_of(ep) else []


# ------------------------------------------------------------- the brief ------
def brief(ep) -> str:
    """The writer's per-episode block. "" when there is no hook and no notes."""
    hook, notes = hook_of(ep), notes_of(ep)
    if not hook and not notes:
        return ""
    h = ("======== THIS EPISODE'S OWN RULINGS — APPROVED AT THE HUMAN GATE. WHERE THEY "
         "DIFFER FROM ANYTHING ABOVE, THEY WIN ========\n")
    if hook:
        h += ("GORDON'S FIRST SPOKEN WORDS ARE THE APPROVED HOOK, WORD FOR WORD:\n"
              f"    {hook}\n"
              "docs/spoken-words.txt begins with exactly these words — nothing before "
              "them. The hook REPLACES your opening framing line: do not write a hook of "
              "your own (the 'one override' about finding Dave's wound does not apply to "
              "this episode), and do not add a second opening after it. Go from the hook "
              "into the article; the free-guide mention may follow as usual. If the hook "
              "has a figure in it, write the figure as words (section 4B) — that is the "
              "only change allowed. The studio checks this.\n\n")
    if notes:
        h += ("THIS EPISODE'S SCRIPT NOTES — follow every line:\n"
              + "\n".join("    " + l for l in notes.splitlines()) + "\n"
              "How to read them:\n"
              "  - A line 'Leave out: \"…\"' quotes the article. If the quoted words OPEN "
              "a paragraph, Gordon says NOTHING from that paragraph — not its sentences, "
              "not its figures, not a summary of it. If they sit INSIDE a paragraph (a "
              "bracket, a credit, one sentence), only those words go and the rest of the "
              "paragraph stays. The studio checks this.\n"
              "  - A note that tells Gordon to say a fact is approved words: say it as "
              "the note gives it.\n"
              "  - If a note says no added lines, then the ONLY words not taken from the "
              "article are the standard furniture: the hook, the free-guide line, the "
              "midroll line and the outro. No asides, no 'if you've been at this for "
              "years' lines, no bridges of your own beyond the shortest transitions.\n\n")
    return h


# ------------------------------------------------------------- the gate -------
def _spoken(text: str) -> list[str]:
    """One fold for the script AND the thing it is compared with — the fidelity
    module's own, so "10" and "ten", "What's" and "What’s" are the same words."""
    return norm_words(sf.fold(text or ""))


def _shingles(tokens: list[str], k: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


def check(script_text: str, capture_text: str, ep) -> list[str]:
    """Blockers in plain English, addressed to the writer. Empty means the rulings hold."""
    hook, notes = hook_of(ep), notes_of(ep)
    out: list[str] = []
    said = _spoken(script_text)

    if hook:
        # 🔴 THE HOOK IS READ THE WAY IT IS SAID — EVERY WAY. (EP63, 20 Nov 2026.) One
        # fold compared letter for letter could not accept "a one minute nine point three
        # second run" for the approved "a 1m 9.3s run", though the brief tells the writer
        # to write the hook's figures as words. The hook is now read by the same reader
        # as the article (`sf.readings`), and unit words are compared in the singular on
        # both sides — grammar only; no number word moves, so a wrong figure, a changed
        # word or anything before the hook still blocks.
        said_u = sf.unit_singular(said)
        wants = [sf.unit_singular(w) for w in [_spoken(hook)] + sf.readings(hook)]
        if not any(said_u[:len(w)] == w for w in wants):
            opening = " ".join((script_text or "").split()[:len(hook.split()) + 6])
            out.append(
                f'the script must open with the approved hook, word for word: "{hook}". '
                f'It opens with: "{opening}…". Put the hook first, exactly as approved, '
                f"with nothing before it, and do not write an opening of your own.")

    if notes:
        out.extend(resolve(capture_text, notes)[1])
        found = cuts(capture_text, notes)
        if found:
            paras = paragraphs(capture_text)
            # What is KEPT: whole-paragraph cuts dropped, inside cuts excised from their
            # paragraph (later spans first, so earlier offsets stay valid).
            kept_paras = list(paras)
            removed: list[tuple[str, str, bool]] = []      # (quote, removed text, whole?)
            for q, i, span in found:
                if span is None:
                    removed.append((q, paras[i], True))
                    kept_paras[i] = ""
            for q, i, span in sorted((c for c in found if c[2]), key=lambda c: -c[2][0]):
                removed.append((q, paras[i][span[0]:span[1]], False))
                kept_paras[i] = kept_paras[i][:span[0]] + " " + kept_paras[i][span[1]:]
            kept_text = "\n\n".join(p for p in kept_paras if p.strip())
            kept_tokens = _spoken(kept_text)
            for q, gone, whole_para in removed:
                g = _spoken(gone)
                # A short cut (a bracketed credit) is shorter than a lift: then saying
                # ALL of it is the lift. A whole paragraph keeps the eight-word rule.
                k = min(LIFT_WORDS, len(g)) or 1
                lifted = sorted((_shingles(g, k) - _shingles(kept_tokens, k))
                                & _shingles(said, k))
                if lifted:
                    what = (f'the paragraph starting "{q}"' if whole_para
                            else f'the words "{q}" (only those words — the rest of their '
                                 f"paragraph stays)")
                    out.append(
                        f"the script notes say to leave out {what}, and the script still "
                        f'says it ("{" ".join(lifted[0])}"). Leave '
                        + ("that whole paragraph out." if whole_para else "those words out."))
            # A FIGURE ONLY THE CUT PARAGRAPHS PRINT. Traced with script_fidelity's own
            # readings: it traces against the whole article and not against what is kept.
            whole = sf.haystacks(capture_text)
            # Same capture, cut paragraphs removed, everything outside the body kept —
            # so the two haystacks differ ONLY by the paragraphs Hugh cut.
            after = capture_text.split(MARKER_END)[-1] if MARKER_END in capture_text else ""
            kept_cap = (capture_text.split(MARKER_BEGIN)[0] + MARKER_BEGIN + "\n\n"
                        + kept_text + "\n\n" + MARKER_END + after)
            kept_h = sf.haystacks(kept_cap)
            lic = sf.haystacks(hook + "\n" + licensed_notes(ep))
            text, _ = sf.without_pool_lines(script_text)
            seen = set()
            for fig in sf.figures(text):
                if fig in seen:
                    continue
                seen.add(fig)
                if (sf._contiguous(fig, whole) and not sf._contiguous(fig, kept_h)
                        and not sf._contiguous(fig, lic)):
                    out.append(
                        f"the script says {fig!r}, and the only place the article prints "
                        f"it is a paragraph the script notes say to leave out. Leave it "
                        f"out with the paragraph.")
    return out
