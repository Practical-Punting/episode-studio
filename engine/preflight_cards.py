"""preflight_cards.py — the card pipeline's checks, run BEFORE a credit moves.

    THE CHECKS EXIST AND THEY RUN TOO LATE.
    Nothing on EP16 was undetectable. It was all detected, in the wrong order.

EP16's card faults — twenty schema/job, twenty-six trace, two bad cues, three
short beats — every one of them fired at `cards_render` or `shot_map`: AFTER the
render gate, after the credit check, after seven paid b-roll clips and two paid
cover heroes, and after Jodie picked a cover. All of them are pure data or pure
text, and every one was knowable at `audit_inputs`.

    THIS IS NOT A NEW CHECK. IT IS THE SAME CHECK, EARLIER.

The schema and trace half IMPORTS `author_cards` and calls the authoring code's
own validators. That is deliberate and it is the whole design: the vocabulary
lives in exactly one place, so a block added to `author_cards.py` tomorrow is
covered here today, and there is no second list for anyone to maintain
(CLAUDE.md fault #7 — derive the coverage from the thing itself).

⚠️ WHAT RUNS AT WHAT TIME — CLAUDE.md fault #4a, which this module could easily
have repeated. A check that runs at `audit_inputs` may only use inputs that
EXIST at `audit_inputs`:

    KNOWABLE  the episode.json, the approved script, the source-article capture.
              Pure data and pure text. These HALT.
    NOT YET   anything measured from the master — WhisperX timings, aligned.srt,
              the real duration of a beat. There is no audio at this point.

So there is NO beat-length check here. One was built, measured against EP16, and
REMOVED — see the note beside ENTRY_DELAY. The exactness lives in
`derive_card_timings`, which has the measured SRT.

The LAYOUT half (`autofit_cards`, `card_check`) is deliberately NOT here — see
`layout_is_not_here()`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SKILL_SCRIPTS = (Path(__file__).resolve().parent.parent
                 / ".claude/skills/pp-episode-production/scripts")

# Entry delay is the PHRASE ANCHOR ruling (PP-RULINGS A2): a card enters about
# three seconds after Gordon actually speaks the cue.
ENTRY_DELAY = 3.0
# 🚫 THERE IS NO BEAT-LENGTH CHECK HERE, AND THAT IS A DECISION.
# (Jodie, 6 Aug 2026, removing one this module briefly carried.)
#
# A beat's real duration DOES NOT EXIST until the audio does, so anything at
# audit_inputs is a guess. The version that was here found ONE of EP16's three
# real short beats, plus one that was not real.
#
#     A WARNING THAT IS WRONG ABOUT HALF THE TIME TRAINS PEOPLE TO STOP
#     READING WARNINGS. And a guess that stays in gets acted on eventually.
#
# The economics agree. The card and cue faults HAD to move early because they
# halted after fifty-eight credits were spent. The beat fault is caught at
# shot_map and fixed with DATA — on EP16 it was three numbers in a file, no
# re-render and no re-spend. Moving it earlier buys nothing and costs noise.
#
# The exactness belongs where the numbers already are: derive_card_timings has
# the measured SRT and reports the overlaps to the centisecond. What it was
# missing was the WHY, and that is where the work went instead.
MARKER_BEGIN = "---- ARTICLE TEXT BEGINS ----"
MARKER_END = "---- ARTICLE TEXT ENDS ----"


def norm_words(t: str) -> list[str]:
    """Fold exactly as derive_card_timings folds — word tokens, punctuation gone.

    ⚠️ THIS FOLD IS LOAD-BEARING. A first version of the cue check compared raw
    strings and CRIED WOLF on EP16's C13 ("each-way" against the script's "each
    way"), which the real tool matches perfectly. A lint that cries wolf is a
    lint someone turns off.
    """
    return re.findall(r"[a-z0-9]+", (t or "").lower())


def capture_rel(epj: dict) -> str | None:
    """The 'docs/<EP>-source-article-*.md' named in episode.json -> source.

    Lives here rather than in engine.py so the caller needs no regex of its own —
    and so there is one place that knows how a capture is named.
    """
    m = re.search(r"(docs/[\w\-.]+\.md)", str(epj.get("source") or ""))
    return m.group(1) if m else None


def _readable(cid: str, e: Exception) -> str:
    """A validator that CRASHES must still say something a person can act on.

    The first real run printed "C1: 'NoneType' object is not iterable" — a raw
    interpreter message in a report a human reads, which is fault #6. It happens
    when a card's `content` is absent or null: the validator walks it and finds
    nothing to walk. Say THAT.
    """
    # author_cards raises `Halt` with a message already written for a person.
    # Pass it straight through — wrapping it in "Halt while checking this card"
    # adds an engine word to a sentence that was already plain English.
    if type(e).__name__ == "Halt":
        return f"{cid}: {e}"
    if isinstance(e, TypeError) and "NoneType" in str(e):
        return (f"{cid}: its content could not be read at all — the card most "
                "likely has no 'content' block, or it is empty. Everything the "
                "card would display lives in there, so nothing else about it can "
                "be checked until it exists.")
    return f"{cid}: {type(e).__name__} while checking this card — {e}"


def _contiguous(needle: list[str], hay: list[str]) -> bool:
    if not needle:
        return False
    return any(hay[i:i + len(needle)] == needle
               for i in range(len(hay) - len(needle) + 1))


# --------------------------------------------------------------- the authoring
def authoring_faults(epj: dict, article_norm: str | None) -> list[str]:
    """Call author_cards' OWN validators. No vocabulary is restated here."""
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    try:
        import author_cards as ac
    except Exception as e:                       # pragma: no cover
        return [f"could not load the authoring validators ({type(e).__name__}: {e}), "
                "so the card checks did not run. That is a machine problem, not a "
                "problem with this episode."]

    out: list[str] = []
    # BESPOKE CARDS ARE HAND-AUTHORED BY DESIGN and author_cards.py never
    # generates them. Including them here reported TITLE, END and WARRANTY as
    # "unknown block 'bespoke'" on a perfectly good episode — three false
    # positives on the first real run, i.e. a guard that fires on every episode,
    # which is the version somebody switches off. Excluded the way the authoring
    # code excludes them.
    cards = [c for c in epj.get("cards", [])
             if c.get("block") and c.get("block") != "bespoke"]
    for c in cards:
        cid = c.get("id", "?")
        try:
            blk = ac.load_block(c["block"])
        except Exception as e:
            out.append(f"{cid}: {e}")
            continue
        # 🔴 `validate()` RAISES Halt on a fault and returns None when the card is
        # FINE. Its return value must not be iterated.
        #
        # Getting this wrong produced the worst possible failure: on EP16's real
        # broken fixture most cards raised before returning, so the report looked
        # right — and on EP16 AS SHIPPED, where every card passes, all thirteen
        # came back None and every one was reported as "content could not be
        # read". A GUARD THAT FIRES ONLY WHEN EVERYTHING IS FINE. It would have
        # halted EP16 and every episode after it.
        #
        # Caught by running it against a FINISHED episode as well as the broken
        # fixture — which is fault #4a's lesson exactly: ask what the input looks
        # like at the moment the check runs, not what a good example looks like.
        try:
            ac.validate(c, blk)
        except Exception as e:
            out.append(_readable(cid, e))
        try:
            out += [f"{cid}: {p}" for p in ac.check_job(c)]
        except Exception as e:
            out.append(f"{cid}: {e}")
        # A dead trace key needs no article, so it is checked even when the capture
        # is missing — it is a fault in the FILE, not in the comparison.
        try:
            out += [f"{cid}: {p}" for p in ac.check_dead_trace(c)]
        except Exception as e:
            out.append(f"{cid}: {e}")
        try:
            out += [f"{cid}: {p}" for p in ac.check_converted_odds(c)]
        except Exception as e:
            out.append(f"{cid}: {e}")
        if article_norm is not None:
            try:
                out += [f"{cid}: {p}" for p in ac.check_trace(c, article_norm)]
            except Exception as e:
                out.append(f"{cid}: {e}")
        # THE REHEARSAL. Everything above is a NAMED check; this is the rest of them.
        # See rehearsal_faults for why the coverage is derived rather than listed.
        if not [x for x in out if x.startswith(cid + ":")]:
            out += rehearsal_faults(ac, c, blk)
    try:
        out += ac.check_mix(cards)
    except Exception as e:
        out.append(str(e))
    return out


def rehearsal_faults(ac, card, blk) -> list[str]:
    """AUTHOR THE CARD IN MEMORY AND THROW THE PAGE AWAY. (11 Aug 2026)

    🔴 THE SWEEP THAT CLOSED THE CLASS. Calling author_cards' named validators
    covered the checks that RETURN a list of problems, and silently missed every
    condition that halts LATER — inside the substitution itself, or in the two
    asserts that run once a page exists. EP20 walked into one on 11 Aug:

        C5's bars[1] drew a bar of length 16 and captioned it "variables", so the
        finished card would have shown a bar and a dangling word with no number in
        front of it. EP18 C9 shipped exactly that shape. `assert_measured_items_
        show_a_figure` had existed since 8 Aug and caught it — AT cards_render,
        after the cover pick, seven paid clips and Gordon's render. Run against
        the same file, this pre-flight returned ZERO blockers. MEASURED, not
        assumed: that is the control in test_preflight_rehearsal.py.

    So the pre-flight now does what `author_cards.main` does, minus the write. Not
    a longer list of checks — THE SAME ACT. A halt condition added to the authoring
    code tomorrow is graded at the commission today, without anyone remembering to
    add it here, which is the property the schema half of this module already had
    and the render half did not (CLAUDE.md fault #7).

    ⚠️ IT IS SKIPPED WHEN THE CARD ALREADY HAS A FAULT, on purpose. A card that
    failed `validate` fails again inside `fill` in different words, and the same
    fault twice in one report is how a repair writer is sent chasing two things.

    ⚠️ AND IT NEEDS NOTHING THAT DOES NOT EXIST YET — no rendered page, no staged
    hero, no browser, no SRT. It is episode.json plus the block and frame templates
    out of the repo. That is what makes it legal here and `autofit_cards` not
    (see layout_is_not_here).
    """
    try:
        frame = ac.load_frame(card.get("layout", "fullscreen"))
        page = ac.render_card(card, blk, frame)
        ac.assert_no_invented_text(page, card, frame, blk)
        ac.assert_measured_items_show_a_figure(card, blk)
    except Exception as e:
        return [_readable(card.get("id", "?"), e)]
    return []


# ------------------------------------------------------------------ the cues
def cue_faults(epj: dict, script_text: str) -> list[str]:
    """Every cue must be a LITERAL substring of the approved script.

    EP16, both failures written from my own beat summaries rather than copied
    from Gordon's sentence:
        C1  "it is TWO bets sold in one transaction"
            -> he says "sold to you IN A SINGLE transaction"
        C9  "eight for the win, to give a profit of forty dollars"
            -> he says "eight DOLLARS for the win"
    This is trace-or-halt, which we already enforce on FIGURES, simply never
    applied to CUE TEXT. Pure string comparison: no credits, no render, no SRT.
    """
    hay = norm_words(script_text)
    out = []
    for c in epj.get("cards", []):
        cue = c.get("cue")
        if not cue:
            continue
        if not _contiguous(norm_words(cue), hay):
            out.append(f"{c.get('id', '?')}: its cue is not in the approved script. "
                       f"The card waits for words Gordon never says, so the shot map "
                       f"cannot place it. Cue as written: {cue!r}")
    return out


# --------------------------------------------------------------- the capture
def capture_faults(capture_text: str | None) -> list[str]:
    """The capture file must carry its ARTICLE TEXT markers.

    ⚠️ THE MARKERS ARE LOAD-BEARING, NOT TIDINESS. `author_ebook.py` reads ONLY
    between them. Without them the fidelity gate would have compared Roger's
    paragraphs against the capture's own HEADER NOTES about the scan repairs —
    it would have checked the article against a commentary on the article.
    EP16 hit this at `ebook_pdf`, step sixteen.
    """
    if capture_text is None:
        return []
    out = []
    for m in (MARKER_BEGIN, MARKER_END):
        if m not in capture_text:
            out.append("the source-article capture is missing its article-text "
                       f"marker line {m!r}. The e-book is built from the text "
                       "between those two lines, so without them it would be built "
                       "from the notes at the top of the file instead.")
    return out


# ------------------------------------------------------------------ the name
def name_faults(epj: dict, capture_text: str | None) -> list[str]:
    """The episode's name and byline against the SOURCE PAGE's own headline.

    > A CONSISTENCY CHECK PROVES SAMENESS, NEVER CORRECTNESS.
    `check_one_name` passed EP16 perfectly — title card, e-book and YouTube all
    agreed, ON THE WRONG NAME. Only the source can settle it, and the headline
    and standfirst are already captured as the first lines of the capture file.
    PP-RULINGS A1: the episode takes the article's headline.
    """
    if not capture_text:
        return []
    lines = [ln.strip() for ln in capture_text.splitlines()]
    head = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), "")
    if not head:
        return []
    title = str(epj.get("title") or "")
    out = []
    # Fold to word tokens: the page shouts its headline and adds "(Part 2)",
    # while the episode name uses an em dash. Neither difference is a fault —
    # A7 puts the part in its own line and A1 governs the NAME.
    # Drop the part designation from BOTH sides before comparing. A7 puts the
    # part on its own line and A1 governs the NAME, so "part" and its number are
    # shared by every episode in a series and say nothing about whether the name
    # is right. Leaving them in was enough to let "Squeeze Those Odds! — Part 2"
    # pass against a page headed "EACH-WAY BETTING FOREVER! (Part 2)" — the exact
    # wrong name this check exists to catch.
    def _name_tokens(s):
        return {w for w in norm_words(s) if w != "part" and not w.isdigit()}

    h, t = _name_tokens(head), _name_tokens(title)
    shared = h & t
    if len(shared) < max(1, min(len(h), len(t)) // 2):
        out.append(
            "the episode's name does not look like the source page's headline. "
            f"The page says {head!r} and the episode is called {title!r}. "
            "The episode takes the article's headline (ruled 5 Aug 2026), so one "
            "of these is wrong and it is almost certainly the episode.")
    return out


def layout_is_not_here() -> str:
    """Why `autofit_cards` and `card_check` are NOT run at audit_inputs yet.

    They need the PAGES rendered and the episode's heroes STAGED — a title hero,
    an e-book cover — and at audit_inputs neither exists. Running them here today
    would fail on every episode for a reason that has nothing to do with the
    cards, which is fault #4a exactly: a check fed inputs from a lifecycle stage
    it will never actually meet.

    Moving them earlier is real work, not a wiring change: the staging step has
    to move too. Logged, scoped, and NOT quietly half-done.
    """
    return ("layout (autofit + card_check) still runs at cards_render: it needs "
            "the pages rendered and the heroes staged, and neither exists yet at "
            "audit_inputs")


# ---------------------------------------------- the capture must BE THERE (E-a)
def capture_reference_faults(epj: dict, capture_text: str | None,
                             capture_looked_for: bool = False) -> list[str]:
    """`source` must name a capture that exists — this is a BLOCKER, not a shrug.

    🔴 WHY IT BLOCKS, when the rest of this module leans towards standing aside:
    the capture is the SWITCH FOR THE WHOLE TRACE REGIME. With it missing,
    `authoring_faults` skips `check_trace` (`if article_norm is not None`) and
    `capture_faults` returns [] on the spot — so the pre-flight reports CLEAN
    having checked nothing at all.

    EP18, 8 Aug 2026: the field named the right file as an ABSOLUTE Windows path
    inside a helpful sentence, so the `docs/....md` pattern matched nothing. The
    build passed audit_inputs, spent the cover pair, SEVEN PAID CLIPS and the
    e-book cover, and halted at step ten on eight trace faults that had been
    invisible from the start. **The one input whose absence blinds the checker
    cannot be the one input it forgives.** (Jodie's ruling, 8 Aug 2026.)
    """
    rel = capture_rel(epj)
    if not rel:
        src = str(epj.get("source") or "")
        return ["episode.json -> source does not name a source-article capture. It must "
                "contain a RELATIVE, forward-slash path of the form "
                "'docs/EPnn-source-article-....md' — an absolute path, backslashes, or a "
                "description of where the file lives will not do, because the whole "
                "figure-tracing regime is switched off when this cannot be read, and "
                "everything downstream then passes by default.\n"
                f"    source currently reads: {src[:200]!r}"]
    # ⚠️ "named but unreadable" fires ONLY when the caller says it actually looked.
    # The engine reads the capture off disk and passes capture_looked_for=True. A unit
    # test or a caller that simply has no capture to hand has not discovered a fault —
    # and treating "you didn't give me one" as "it is missing" halted EP16-as-shipped
    # in the existing suite the first time this was written.
    if capture_text is None and capture_looked_for:
        return [f"episode.json -> source names {rel!r} but that file could not be read. "
                "Figures cannot be traced to an article that is not there, so nothing "
                "after this point would be checked. Put the capture in place (it lives "
                "in the SHARED 'PP Videos/docs' folder), then re-run."]
    return []


# ------------------------------------------------------------------- the run
def preflight_cards(epj: dict, *, script_text: str = "",
                    capture_text: str | None = None,
                    article_norm: str | None = None,
                    capture_looked_for: bool = False) -> dict:
    """Return {'blockers': [...], 'warnings': [...]}. Callers decide to halt."""
    blockers = []
    blockers += capture_reference_faults(epj, capture_text, capture_looked_for)
    blockers += authoring_faults(epj, article_norm)
    if script_text:
        blockers += cue_faults(epj, script_text)
    blockers += capture_faults(capture_text)
    blockers += name_faults(epj, capture_text)
    # 🚫 STRAY TRACE KEYS ARE NOT REPORTED HERE, AND THAT IS THE SAME DECISION AS THE
    # BEAT-LENGTH CHECK ABOVE. This module emits NO warnings on purpose (Jodie, 6 Aug
    # 2026): "a warning that is wrong about half the time trains people to stop reading
    # warnings". A key that addresses nothing is harmless BY DEFINITION — nothing reads
    # it — so it has no business in a gate. `author_cards` prints it in the authoring
    # report, where it belongs: visible in the run log, never in front of an operator.
    return {"blockers": blockers, "warnings": []}


def format_report(res: dict) -> str:
    """Plain English for the RUN LOG. The operator's box gets the halt, not this."""
    b, w = res["blockers"], res["warnings"]
    lines = [f"card pre-flight: {len(b)} blocker(s), {len(w)} thing(s) to look at"]
    for p in b:
        lines.append(f"  x {p}")
    for p in w:
        lines.append(f"  ? {p}")
    lines.append(f"  ({layout_is_not_here()})")
    return "\n".join(lines)


def main(argv):                                  # pragma: no cover
    if len(argv) < 2:
        print("usage: preflight_cards.py <episode.json> [script.txt] [capture.md]")
        return 2
    epj = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    script = Path(argv[2]).read_text(encoding="utf-8") if len(argv) > 2 else ""
    cap = Path(argv[3]).read_text(encoding="utf-8") if len(argv) > 3 else None
    res = preflight_cards(epj, script_text=script, capture_text=cap)
    print(format_report(res))
    return 1 if res["blockers"] else 0


if __name__ == "__main__":                       # pragma: no cover
    sys.exit(main(sys.argv))
