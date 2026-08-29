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
def authoring_faults(epj: dict, article_norm: str | None,
                     capture_text: str | None = None) -> list[str]:
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
    # 🔴 LIFT FIRST, EXACTLY AS `author_cards.main` DOES. A card that reads its data
    # out of the article arrives here with an EMPTY slot where its rows go, so every
    # check below would grade a card nobody will ever see — and would report a card
    # with no rows, which is true and useless.
    #     THE SAME ACT, EARLIER: this is the rehearsal principle applied to the lift.
    # A capture whose table has gained a row, a renamed column, an anchor that is no
    # longer in the chart — every one of those is knowable HERE, at audit_inputs,
    # before a credit moves, rather than at cards_render twelve hours in. It needs
    # nothing that does not exist yet: episode.json and the capture, both on disk.
    # 🔒 ON A DEEP COPY, AND THAT IS LOAD-BEARING. The lift fills a card's rows and
    # stamps `_lifted` on it, and `card_lift` HALTS on a `_lifted` key that arrives
    # from disk — it can only mean somebody hand-wrote provenance a figure does not
    # have. Meanwhile `engine._preflight_cards` writes episode.json back after the
    # framing re-derive. Today that write happens BEFORE this runs, so filling the
    # live object would be harmless; it would stop being harmless the day somebody
    # reorders two blocks, and the symptom would be an episode that halts on a key
    # it never contained. Copying costs nothing and removes the whole class.
    import copy
    cards_for_checks = copy.deepcopy(list(epj.get("cards") or []))
    try:
        ac.apply_lifts(cards_for_checks, capture_text)
    except Exception as e:
        out.append(_readable("the card data", e))
    # BESPOKE CARDS ARE HAND-AUTHORED BY DESIGN and author_cards.py never
    # generates them. Including them here reported TITLE, END and WARRANTY as
    # "unknown block 'bespoke'" on a perfectly good episode — three false
    # positives on the first real run, i.e. a guard that fires on every episode,
    # which is the version somebody switches off. Excluded the way the authoring
    # code excludes them.
    # …and every check below reads the FILLED copy, never the file's own cards.
    # A lifted card is an empty slot in episode.json; grading the unfilled version
    # would report "this card has no rows", which is true and useless.
    cards = [c for c in cards_for_checks
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


# ------------------------------- and it must STILL be in the SRT afterwards (2b)
#
# 🔴 `cue_faults` ABOVE ALREADY CHECKS THE CUE — AGAINST THE APPROVED SCRIPT, AT
# audit_inputs. EP24 C19 walked past it because the card was edited AFTERWARDS: the
# over-full-card fix tightened and split it long after the pre-flight had run and long
# after Gordon had recorded. The cue was rewritten; the recording was not.
#
#     A CHECK THAT RUNS ONCE PROTECTS THE VERSION IT RAN ON.
#
# ⚠️ AND THE ACTUAL FAULT WAS ONE CHARACTER, WHICH IS WHY THIS SAYS SO OUT LOUD.
# The new cue was taken from the card's own `trace` entry — the ARTICLE's words:
#       cue   "sprint races favour runners drawn 7 and inside"
#       SRT   "Sprint races favour runners drawn seven and inside."
# The phrase was right; the `7` was the whole fault. Gordon speaks a spoken-words script,
# so EVERY NUMBER IS SPELLED OUT, while the article — and therefore every trace sentence —
# uses digits. A cue copied from `trace` fails silently the moment it contains a figure,
# and figures are what these cards are ABOUT.
#     trace proves a FIGURE's source. The cue anchors to a SOUND. Two jobs, two strings.
_DIGIT = re.compile(r"\d")


def _nearest_spoken(cue: str, lines: list[str]) -> str | None:
    """The spoken line sharing the most words with the cue — the re-anchor candidate."""
    want = set(norm_words(cue))
    if not want:
        return None
    best, score = None, 0
    for ln in lines:
        n = len(want & set(norm_words(ln)))
        if n > score:
            best, score = ln, n
    return best if score >= 2 else None


def cue_in_srt_faults(epj: dict, srt_text: str) -> list[str]:
    """Every cue must be a literal phrase in the ALIGNED SRT — the finished render.

    Run this after ANY post-render change to a card, so a tighten or a split can never
    again leave a card waiting for words that were never spoken.
    """
    lines = [ln.strip() for ln in srt_text.splitlines()
             if ln.strip() and "-->" not in ln and not ln.strip().isdigit()]
    hay = norm_words(" ".join(lines))
    out = []
    for c in epj.get("cards", []):
        cue = c.get("cue")
        if not cue or _contiguous(norm_words(cue), hay):
            continue
        msg = (f"{c.get('id', '?')}: its cue is not in the aligned SRT, so the card is "
               f"waiting for words that are not in the finished render. "
               f"Cue as written: {cue!r}")
        if _DIGIT.search(cue):
            msg += (" — and it contains a DIGIT. Gordon speaks every number as a word, "
                    "so a cue carrying '7' can never match a render that says 'seven'. "
                    "This is what a cue copied from the article or from trace{} looks "
                    "like: trace proves a figure's source, the cue anchors to a sound.")
        near = _nearest_spoken(cue, lines)
        if near:
            msg += f" Nearest spoken line, verbatim: {near!r}"
        out.append(msg)
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
# 🔴 §1a IS NOT EDITED, NARROWED OR GIVEN AN UNLESS-CLAUSE BY ANY OF THIS.
# The rule was ruled by Jodie WITH HUGH on the evening of 5 Aug 2026 — the same
# night a series-name rule produced EP16, rendered, assembled and QC-passed under a
# borrowed name and caught only by chance — and it says in terms: "the series-name
# provision is DELETED, not qualified — AN EXCEPTION IS HOW IT COMES BACK."
#
# What follows is therefore NOT an exception to the rule. It is a RECORDED,
# PER-EPISODE, AUDITED ESCAPE HATCH with four properties, and every one of them is
# what keeps it from becoming the unless-clause §1a forbids:
#   1. It NEVER GENERALISES. It is a key inside ONE episode.json and is read from
#      that file only. Nothing copies it forward; the next episode has no such key
#      and halts exactly as before.
#   2. IT NAMES WHAT IT COVERS. It records the TITLE it excuses and the HEADLINE it
#      was excused against, and it applies only while BOTH still match. Re-title the
#      episode, or re-capture the page, and the override LAPSES ON ITS OWN rather
#      than silently covering a fault nobody has looked at.
#   3. IT IS NEVER SILENT. An honoured override prints a note into the run log
#      saying what was overridden, when and why. A rule that is being set aside
#      without saying so is a rule nobody can audit.
#   4. IT CANNOT BE INFERRED FROM PROSE. It is a STRUCTURED declaration and nothing
#      reads `_title_note` to decide anything. EP41's own `_title_note` argues BOTH
#      sides — the override AND the §1a reasoning against it, kept for the record —
#      so a prose match would have been a coin toss on which paragraph it hit first.
#      ("Mentioned is not declared": parse declarations, never mentions.)
OVERRIDE_KEY = "_title_override"


def title_override(epj: dict, head: str):
    """A recorded §1a override for THIS episode against THIS headline, or None.

    Every field is required and is checked. A half-written override is NOT an
    override — it is a fault nobody finished describing, and the safe reading of
    it is that the rule still applies.
    """
    ov = epj.get(OVERRIDE_KEY)
    if not isinstance(ov, dict):
        return None
    if str(ov.get("rule") or "").strip() != "1a":
        return None
    # THE TWO IT NAMES. Change either and the override lapses, by design.
    if str(ov.get("title") or "") != str(epj.get("title") or ""):
        return None
    if str(ov.get("headline") or "") != head:
        return None
    if not str(ov.get("date") or "").strip():
        return None
    if not str(ov.get("reason") or "").strip():
        return None
    return ov


def title_override_notes(epj: dict, capture_text: str | None) -> list[str]:
    """Run-log lines for an override that is being honoured. Never an operator flag.

    Emitted whether or not the fault would have fired, so the log records the
    override's PRESENCE and not merely its effect — an override sitting in a file
    that no longer needs it is worth seeing before it is worth trusting.
    """
    head = _capture_headline(capture_text)
    if not head:
        return []
    ov = title_override(epj, head)
    if not ov:
        return []
    return [f"§1a name check OVERRIDDEN for this episode only — recorded "
            f"{ov['date']}: {ov['reason']} (page headline {head!r}, episode "
            f"{str(epj.get('title') or '')!r}). It does not travel: the next "
            f"episode halts on §1a exactly as before."]


def _capture_headline(capture_text: str | None) -> str:
    """The source page's own headline — the capture's first `# ` line."""
    if not capture_text:
        return ""
    for ln in capture_text.splitlines():
        ln = ln.strip()
        if ln.startswith("# "):
            return ln.lstrip("# ").strip()
    return ""


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
    head = _capture_headline(capture_text)
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
        # THE OVERRIDE IS CONSULTED HERE AND NOWHERE ELSE — after the fault has been
        # FOUND, never before it is looked for. The check still runs in full and still
        # reaches the same verdict; all a recorded override changes is whether that
        # verdict stops the build. So the rule is never narrowed, the log always says
        # what was found, and deleting the key restores the halt with nothing else to
        # undo.
        if title_override(epj, head) is not None:
            return []
        out.append(
            "the episode's name does not look like the source page's headline. "
            f"The page says {head!r} and the episode is called {title!r}. "
            "The episode takes the article's headline (ruled 5 Aug 2026), so one "
            "of these is wrong and it is almost certainly the episode.\n"
            "      If this episode's name is right and you clear this, I will "
            "record a one-off exception for THIS EPISODE ONLY, with today's date, "
            "and I will say so in the log every time it is used. The next episode "
            "stops here again and needs the same decision.")
    return out


# ─────────────── the pages a human has to write, ALL OF THEM, AT ONCE (E14) ──
def bespoke_faults(epj: dict, pages_dir=None, is_pipeline_page=None) -> list[str]:
    """Every `block:"bespoke"` page nobody is going to author unless a person does.

    🔴 ONE FLAG, LISTING EVERY ONE, AT PLAN TIME. EP27 raised this fault the worst
    possible way: `cards_render` halted on "Card C15 has no clip", a person wrote
    C15 — and C17 was sitting behind it, identical, unmentioned. TWO DEEP HALTS,
    hours apart, when one sentence at the head of the build would have described
    the whole job.

        A CHECK THAT REPORTS ONE FAULT PER ATTEMPT CANNOT BE USED IN A LOOP.
        That rule is already written into `_epjson_gate` ("the writer gets every
        complaint at once") and into assert_measured_items_show_a_figure. This is
        the same rule, applied to the one class of work that goes to a HUMAN.

    ⚠️ AND IT IS THE CHEAPEST POSSIBLE MOMENT. At audit_inputs nothing has been
    spent: no b-roll, no covers, no Chromium. The person is being told what the
    episode needs from them BEFORE the machine spends anything on it, instead of
    twelve hours in with a paid render already sitting on the disk.

    STANDING FURNITURE IS NOT A JOB FOR A HUMAN — see providers.pipeline_authors_page
    for why that is derived and not a list of ids.

    ⚠️ IT FIRES ONLY WHEN THE CALLER SAYS IT LOOKED — `pages_dir` is that signal,
    and it is the SAME rule `capture_reference_faults` already carries two hundred
    lines down, for the same reason and at the same cost. "You did not give me a
    folder" is not "the page is missing": EP15 and EP19 each shipped one genuine
    bespoke card, so a version that halted without looking reported both of those
    finished episodes as unbuildable in the existing suite, which is how this
    class of guard gets switched off. The engine always passes the folder.
    """
    if pages_dir is None:
        return []
    if is_pipeline_page is None:
        from providers import pipeline_authors_page as is_pipeline_page
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import bespoke_gate as bg

    want = bg.needs_a_human(epj.get("cards") or [], is_pipeline_page)
    # A page a person has ALREADY written is not an ask. This is what lets the
    # flag clear: author the pages, clear it, and the same check passes.
    missing = [c for c in want
               if not (pages_dir and (Path(pages_dir) / str(c.get("page") or "")).is_file())]
    if not missing:
        return []
    lines = [f"    · {c.get('id', '?')} — {c.get('page', '?')}"
             + (f"\n        {str(c.get('detail') or '').strip()[:240]}"
                if c.get("detail") else "")
             for c in missing]
    n = len(missing)
    return ["THIS EPISODE NEEDS {} HAND-AUTHORED CARD PAGE{} BEFORE IT CAN BE BUILT, "
            "AND HERE THEY ALL ARE:\n{}\n"
            "    These cards are marked block:\"bespoke\", which means nothing generates "
            "them — not now and not at cards_render, where this used to surface one "
            "page at a time as \"has no clip\".\n"
            "    Before writing one by hand, ask whether it still has to be: a big TABLE "
            "is a `ladder` card (five to seven anchor rows lifted from the article, the "
            "full chart staying in the e-book) and a long LIST is a `checklist`, which "
            "now holds twelve. Both are generated, and both are checked. A page that "
            "stays bespoke is checked too, but only for what a machine can see.\n"
            "    If it must be bespoke: scripts/bespoke/README.md, and the data comes "
            "out of the capture programmatically."
            .format(n, "" if n == 1 else "S", "\n".join(lines))]


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


# ------------------------------------------- a card must not be BORN too big (2a)
#
# 🔴 THE CARD-WRITER OVER-FILLS COUNTRY-TRACK CARDS. EP24 C19, and EP23 C21 before it.
# C19 arrived with FOUR country courses on one matrix, two facts each. It did not fit at
# the autofit floor (60%/16px), the automatic layout swap did not rescue it, and — the
# measurement that matters — TIGHTENING THE CELLS TO 73% OF THEIR CHARACTERS DID NOT
# RESCUE IT EITHER. It was over-full by a ROW, not by phrasing. Split two-and-two, both
# halves fitted at 88% and 94%.
#
# ⚠️ AND THIS IS THE ONE OVER-FULL CHECK THAT CAN RUN HERE. `layout_is_not_here()` above
# explains why autofit and card_check cannot: they need rendered pages and staged heroes.
# THIS needs neither. Row count and cell length are pure data in episode.json, knowable at
# audit_inputs — which is fault #4a's test, and it passes it.
#
# 📌 CALIBRATED ON REAL CARDS, AND THE LIMIT OF THAT IS STATED ON PURPOSE:
#       4 rows of ~42-char cells  — FAILED below the floor, twice (before and after
#                                   tightening to 73%)
#       2 rows of ~42-char cells  — fitted at 88% and 94%
#       3 rows                    — NEVER MEASURED.
# So the cap is the measured-good number, not an interpolation. When a 3-row card is
# genuinely measured, move it and say so here. A cap invented between two data points is
# a guess wearing a number.
MATRIX_MAX_ROWS = 2          # measured, not chosen — see above
LONG_CELL_CHARS = 25         # below this a row is a chip, not a paragraph


def overfull_faults(epj: dict) -> list[str]:
    """Matrix cards that are too big to fit before anyone renders them."""
    out = []
    for card in epj.get("cards") or []:
        if (card.get("block") or "") != "matrix":
            continue
        rows = ((card.get("content") or {}).get("rows")) or []
        if len(rows) <= MATRIX_MAX_ROWS:
            continue
        longest = max((len(str(c)) for r in rows for c in (r.get("cells") or [])),
                      default=0)
        if longest <= LONG_CELL_CHARS:
            continue                      # short chips; the row count is not the problem
        out.append(
            f"{card.get('id', '?')}: a matrix card with {len(rows)} rows and cells up to "
            f"{longest} characters will not fit — {MATRIX_MAX_ROWS} such rows is what has "
            f"been measured to fit, and EP24's four-row version failed even after its "
            f"cells were tightened to 73%. Split it across cards, and put each card on "
            f"the beat where its own items are SPOKEN rather than gathering them onto the "
            f"last one. Nothing is dropped: every row moves to one card or the other.")
    return out


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
                    capture_looked_for: bool = False,
                    pages_dir=None) -> dict:
    """Return {'blockers': [...], 'warnings': [...]}. Callers decide to halt."""
    blockers = []
    blockers += capture_reference_faults(epj, capture_text, capture_looked_for)
    blockers += authoring_faults(epj, article_norm, capture_text)
    blockers += bespoke_faults(epj, pages_dir)
    if script_text:
        blockers += cue_faults(epj, script_text)
    blockers += capture_faults(capture_text)
    blockers += name_faults(epj, capture_text)
    blockers += overfull_faults(epj)
    # A RECORDED OVERRIDE IS A NOTE, NEVER A WARNING AND NEVER SILENCE. Jodie's
    # 6 Aug ruling bans warnings from this module — "a warning that is wrong about
    # half the time trains people to stop reading warnings" — and this is not one:
    # it is a statement of fact about a rule that was set aside, addressed to the
    # run log and to a maintainer, never to the operator's box.
    notes = title_override_notes(epj, capture_text)
    # 🚫 STRAY TRACE KEYS ARE NOT REPORTED HERE, AND THAT IS THE SAME DECISION AS THE
    # BEAT-LENGTH CHECK ABOVE. This module emits NO warnings on purpose (Jodie, 6 Aug
    # 2026): "a warning that is wrong about half the time trains people to stop reading
    # warnings". A key that addresses nothing is harmless BY DEFINITION — nothing reads
    # it — so it has no business in a gate. `author_cards` prints it in the authoring
    # report, where it belongs: visible in the run log, never in front of an operator.
    return {"blockers": blockers, "warnings": [], "notes": notes}


def format_report(res: dict) -> str:
    """Plain English for the RUN LOG. The operator's box gets the halt, not this."""
    b, w = res["blockers"], res["warnings"]
    n = res.get("notes") or []
    lines = [f"card pre-flight: {len(b)} blocker(s), {len(w)} thing(s) to look at"]
    for p in b:
        lines.append(f"  x {p}")
    for p in w:
        lines.append(f"  ? {p}")
    # AFTER the faults, so a note can never be mistaken for one, and never omitted.
    for p in n:
        lines.append(f"  ! {p}")
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
