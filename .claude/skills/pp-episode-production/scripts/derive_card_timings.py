"""Derive card leads + midroll.at FROM the WhisperX SRT — never from estimates.

    python derive_card_timings.py <episode_dir> [--write]

Report-only by default. --write updates docs/episode.json (build.leads, build.midroll.at)
and NOTHING else. Run it AFTER shot_map has produced renders/generated.srt and
renders/shot-map.json, and RE-RUN it whenever a card window moves.

WHY THIS EXISTS — the EP11 lesson, four failures in one day (PP-STANDARDS §Motion-graphic
cards, "WHEN A TIMING CHANGES, ASK WHAT WAS CALCULATED FROM IT"):
  · midroll.at was a word-count estimate that went stale and landed 22s late, over a card.
  · b-roll offsets were fine until the cards moved onto them.
  · the shot plan was derived from PRE-shift card timings, so a panel-push card was still
    on screen when the camera pushed in and it landed over Gordon's face.
  · un-cued cards stayed put while the cards around them moved, and were overrun.
A stale derived value passes every check that only looks at it in isolation. This tool
derives ALL of them from one source of truth — the master's own SRT — in one pass.

THE RULES IT ENFORCES (all from PP-STANDARDS, none invented here):
  · CARD ENTRY = SPOKEN CUE + 3.0s, timed off the SRT, never off QC's rounded entry times.
  · `leads` are OFFSETS FROM THE BEAT START (confirmed against EP11's shipped values),
    so lead = (cue_start - beat_start) + ENTRY_DELAY.
  · SHIFT THE WINDOW, NEVER SHORTEN THE CARD — holds are read, never reduced.
  · Un-cued cards INHERIT THE SHIFT of the card they follow; they are not exceptions.
  · The midroll chip FOLLOWS the start of the spoken ask by 1.0s -- never precedes it,
    never spans it -- with >=6s full visibility.
  · CHECK ALL FOUR OVERLAP CLASSES: card-card, card-midroll, b-roll-card, b-roll-midroll.
  · While an ON-SCREEN (panel-push) card is visible the shot must be WIDE for the WHOLE
    window, entry to exit — not merely at the in-point. Full-screen cards are unaffected.
  · If a card cannot take the full shift, THAT IS A DECISION FOR JODIE. This tool reports
    it and refuses to write; it never silently shortens a card or quietly gives it a
    smaller offset.

IT NEVER GUESSES. If a cue phrase is not found in the SRT it is a HARD FAIL and nothing
is written — an unlocatable cue means the words changed or the master is wrong, and either
way a human needs to look. There is no fuzzy fallback on purpose.

WIRED INTO THE ENGINE (29 Jul 2026) — providers.derive_timings() calls it with --write
from build_shot_map, after the SRT exists and before any window is used.

For three episodes this docstring told the reader it was unwired and had to be run by
hand — and on EP13 nobody ran it: nine of thirteen cards entered BEFORE their spoken
cue, C1 by 9.6 seconds. (The old wording is deliberately not repeated here;
test_hand_steps.py greps this file for it, and a quotation would make that check pass
on nothing — the same trap as the EP12 ask phrases below.) A hand-run step is one Hugh cannot perform at all, and it gets skipped
exactly when it matters most — after a long build, when everyone is looking at the
render. It can still be run by hand for a report; --write is what the engine uses.
"""
import json, re, sys, pathlib
import card_hold as ch
import framing as _framing

ENTRY_DELAY = 3.0          # PP-STANDARDS: card entry = spoken cue + 3.0s
MIDROLL_MIN_FULL = 6.0     # >=6s of FULL visibility (fades on top)
MIDROLL_FOLLOW = 1.0       # the chip enters this long AFTER the ask starts (never before)


# ---------- SRT -> a word-level timeline ------------------------------------
def parse_srt(path):
    """Return [(start, end, text)] from an SRT. Tolerates the BOM and CRLF."""
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)",
                      "\n".join(lines))
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        s = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000.0
        e = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000.0
        text = " ".join(lines[lines.index(m.group(0)) + 1:]) if m.group(0) in lines else \
               " ".join(l for l in lines if not re.match(r"^\d+$", l) and "-->" not in l)
        out.append((s, e, text))
    return out


def norm_words(t):
    return re.findall(r"[a-z0-9]+", (t or "").lower())


def word_timeline(cues):
    """[(word, start)] — position inside a cue is interpolated by CHARACTER OFFSET,
    deliberately mirroring how build_shot_map.py builds the SRT in the first place
    (`d = span * len(c) / total`, i.e. character-proportional, not word-proportional).

    This matters. Equal-word spacing is a DIFFERENT model from the generator's and
    compounds a second approximation on top of the first — measured against EP11 it
    put cues up to 3.2s late, which would have turned Jodie's tuned 3.0s entry delay
    into 6.2s. Matching the generator's own model keeps one approximation, not two.

    Read the honest limit: generated.srt is NOT true word-level forced alignment. It
    is silence-verified WhisperX anchors at paragraph boundaries with proportional
    interpolation inside. Cue times are therefore tight near a beat/sentence start and
    loosest mid-paragraph. Treat a derived entry as accurate to a few tenths, not to
    the frame, and eyeball any card whose cue sits deep inside a long paragraph."""
    tl = []
    for s, e, text in cues:
        flat = " ".join(text.split())
        if not flat:
            continue
        span = e - s
        for m in re.finditer(r"[A-Za-z0-9]+", flat):
            tl.append((m.group(0).lower(), s + span * (m.start() / len(flat))))
    return tl


def find_phrase(tl, phrase):
    """Absolute start time of the first occurrence of `phrase`. None if absent."""
    r = find_phrase_x(tl, phrase)
    return None if r is None else r[0]


def find_phrase_x(tl, phrase, cues=None):
    """(time, slack) for `phrase`. `slack` is how far the phrase sits INSIDE its
    containing SRT cue, in seconds — i.e. how much of the answer is interpolation
    rather than a real anchor.

    WHY THIS IS REPORTED AND NOT HIDDEN: generated.srt is not word-level forced
    alignment (build_shot_map.py:91 spreads text inside each paragraph), so a cue
    landing at a cue boundary is near-exact while one deep inside a long paragraph
    is a proportional guess. Measured against EP11's shipped leads the two cards
    whose cues sit AT a boundary reproduced EXACTLY (C10 7.94, C12 3.00) while the
    deepest-set cue (C7) differed by 3.46s. Slack is therefore the honest signal for
    "eyeball this one before you trust it" — the difference between a derivation you
    can bank and one you must look at."""
    target = norm_words(phrase)
    if not target:
        return None
    words = [w for w, _ in tl]
    n = len(target)
    for i in range(len(words) - n + 1):
        if words[i:i + n] == target:
            t = tl[i][1]
            anchor = max([s for s, _, _ in (cues or []) if s <= t + 1e-9], default=t)
            return t, round(t - anchor, 2)
    return None


# ---------- windows ---------------------------------------------------------
def overlaps(a, b):
    """Seconds of overlap between two [start, end] windows (0 if none)."""
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def hold_for(cid, card, holds, build):
    """How long this card is on screen — THE SAME PRECEDENCE assemble_episode.py uses.

    This tool used to read `holds[cid]` else `default_hold`, and knew nothing about
    `hero_hold`. assemble_episode.py gives every card with `hero: true` the longer
    hero_hold (12s vs 10s), so for hero cards this tool was checking overlaps against
    a window TWO SECONDS SHORTER than the one that actually gets built.

    It cost a full re-encode on EP13: C1 was cleared here at 33.19-43.19, the stopwatch
    b-roll was placed to start at 44.18 — and the shipped episode put C1 up until 45.19,
    so qc_episode hard-failed on a b-roll under a card. The overlap checker has to model
    the assembler exactly, or it is checking a video nobody is going to build.
    """
    if cid in holds:
        return float(holds[cid])
    if card.get("hero"):
        return float(build.get("hero_hold", 12.0))
    return float(build.get("default_hold", 8.0))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = pathlib.Path(sys.argv[1]).resolve()
    write = "--write" in sys.argv
    apply_broll = "--apply-broll" in sys.argv
    # 🔴 THE REMEDY WAS ALREADY COMPUTED AND A HUMAN WAS RETYPING IT (12 Aug 2026).
    # A b-roll/card overlap is not a decision: why_broll_card below works out the exact
    # delay AND confirms the room exists at the back of the clip's own beat before it
    # says a word. It then printed "Set build.broll_offsets['x'] to 4.61" and stopped
    # the build so somebody could type 4.61 into a file. EP22 halted on FOUR of these
    # in one run and EP21 on one; every one was applied verbatim, unchanged, by hand.
    # With --apply-broll the tool writes what it already knows and runs again.
    #     Only the CONFIRMED branch is ever auto-applied — where slack >= need. The
    # other branch says "a decision rather than an adjustment" and still halts.
    broll_fixes: dict[str, float] = {}
    # A3 — the same argument, for the other halt that was never a decision. See the
    # SHOT PLAN block: WIDE is the only lawful answer and the beats are already known.
    apply_wide = "--apply-wide" in sys.argv
    wide_fixes: dict[int, list] = {}

    epj_path = d / "docs/episode.json"
    # PREFER FORCED ALIGNMENT. renders/generated.srt is CONSTRUCTED from
    # spoken-words.txt by interpolation, and deriving leads from it then checking them
    # against it is circular -- it put eleven of EP13's cards up to 12.3s AHEAD of the
    # words while every check said "on-cue" (Jodie, 29 Jul 2026).
    srt_path = d / "renders/aligned.srt"
    if not srt_path.is_file():
        srt_path = d / "renders/generated.srt"
        print("!! renders/aligned.srt is missing - falling back to the CONSTRUCTED SRT.\n"
              "   Leads derived from it cannot be trusted to land on the spoken cue.\n")
    map_path = d / "renders/shot-map.json"
    for p in (epj_path, srt_path, map_path):
        if not p.is_file():
            sys.exit(f"MISSING: {p}\nRun this only after shot_map has produced the SRT "
                     f"and the shot map. Nothing has been written.")

    epj = json.loads(epj_path.read_text(encoding="utf-8"))
    build = epj["build"]
    shots = json.loads(map_path.read_text(encoding="utf-8"))
    srt_cues = parse_srt(srt_path)
    tl = word_timeline(srt_cues)
    beat_start = {s["shot"]: s["start"] for s in shots}
    beat_end = {s["shot"]: s["end"] for s in shots}
    framing = {b["n"]: b.get("framing") for b in epj["beats"]}
    layout = {c["id"]: c.get("layout") for c in epj["cards"]}
    holds = build.get("holds", {})
    min_hold = float(build.get("min_card_hold", 10.0))
    problems, notes = [], []

    print(f"SOURCE: {srt_path.name} ({len(tl)} words) + {map_path.name} "
          f"({len(shots)} beats)\nENTRY DELAY: cue + {ENTRY_DELAY}s\n")

    # ---- 1. cued cards: lead = (cue_start - beat_start) + ENTRY_DELAY --------
    leads, windows = {}, {}
    print("CUED CARDS — derived from the SRT")
    print(f"  {'card':6} {'beat':>4} {'cue@':>8} {'beat@':>8} {'lead':>7} {'enters':>8} "
          f"{'hold':>6} {'exits':>8} {'slack':>6} {'ep11-way':>9}  cue")
    for c in epj["cards"]:
        cid, cue, beat = c["id"], c.get("cue"), c.get("beat")
        if not cue:
            continue
        if beat not in beat_start:
            problems.append(f"{cid}: beat {beat} is not in the shot map")
            continue
        hit = find_phrase_x(tl, cue, srt_cues)
        if hit is None:
            problems.append(f"{cid}: CUE NOT FOUND IN THE SRT -> {cue!r}. The words may have "
                            f"changed, or this is the wrong master. Not guessing.")
            continue
        t, slack = hit
        bs = beat_start[beat]
        # build.lead_extra {card: seconds} — a DELIBERATE extra delay beyond cue+3.0s,
        # used only to clear an overlap that cannot be resolved any other way. It is
        # additive and always LATER, never earlier, so it can never make a card lead its
        # cue. Recorded in episode.json and printed below so the deviation is visible and
        # reviewable — the rule forbids QUIETLY giving a card a different offset, not
        # having one. Anything here needs a reason in the report.
        extra = float((build.get("lead_extra") or {}).get(cid, 0.0) or 0.0)
        if extra < 0:
            problems.append(f"{cid}: lead_extra {extra} is NEGATIVE — that would pull the "
                            f"card toward its cue. Only later shifts are legal.")
            extra = 0.0
        lead = round(t - bs + ENTRY_DELAY + extra, 2)
        hold = hold_for(cid, c, holds, build)
        enter, exit_ = round(bs + lead, 2), round(bs + lead + hold, 2)
        leads[cid] = lead
        windows[cid] = (enter, exit_)
        print(f"  {cid:6} {beat:>4} {t:>8.2f} {bs:>8.2f} {lead:>7.2f} {enter:>8.2f} "
              f"{hold:>6.1f} {exit_:>8.2f} {slack:>6.2f} {round(lead - slack, 2):>9.2f}  {cue!r}"
              + (f"   <- +{extra}s DELIBERATE SHIFT" if extra else
                 "   <- DIFFERS" if slack > 0.25 else ""))
        if extra:
            notes.append(f"{cid}: carries a DELIBERATE +{extra}s shift beyond cue+{ENTRY_DELAY}s "
                         f"(entering at cue+{ENTRY_DELAY + extra:.2f}s) to clear an overlap that "
                         f"could not be resolved without shortening a card. Confirm by eye.")
        if slack > 0.25:
            notes.append(f"{cid}: PHRASE anchor {lead:.2f}s vs CUE-BLOCK anchor "
                         f"{lead - slack:.2f}s — {slack:.2f}s apart. See the anchoring note below.")
        if lead < ENTRY_DELAY - 0.01:
            problems.append(f"{cid}: lead {lead}s is less than the {ENTRY_DELAY}s entry "
                            f"delay — the cue resolves BEFORE its own beat starts.")
        # THE FLOOR SCALES WITH WHAT THE CARD ASKS YOU TO READ — see card_hold.py.
        # A flat 10s halted EP21 C19, two rows on a beat that could give it 8.64s.
        card_min = ch.min_hold_for(c, build)
        if hold < card_min - 0.01:
            problems.append(f"{cid}: hold {hold}s is below this card's minimum — "
                            f"{ch.why(c, build)}. "
                            f"Shift the window, never shorten the card — Jodie's call.")

    # ---- 2. un-cued cards INHERIT THE SHIFT of the card they follow ---------
    uncued = [c["id"] for c in epj["cards"]
              if not c.get("cue") and c["id"] not in ("TITLE", "END", "WARRANTY")]
    if uncued:
        print("\nUN-CUED CONTENT CARDS — inherit the shift of the card they follow "
              "(EP11: C6/C8 stayed put and were overrun)")
        order = [c["id"] for c in epj["cards"]]
        for cid in uncued:
            prev = next((p for p in reversed(order[:order.index(cid)]) if p in leads), None)
            base = float((build.get("leads") or {}).get(cid, 0.0) or 0.0)
            lead = round(base + ENTRY_DELAY, 2)
            beat = next(c["beat"] for c in epj["cards"] if c["id"] == cid)
            hold = hold_for(cid, c, holds, build)
            bs = beat_start.get(beat, 0.0)
            leads[cid] = lead
            windows[cid] = (round(bs + lead, 2), round(bs + lead + hold, 2))
            notes.append(f"{cid}: no cue — took the +{ENTRY_DELAY}s shift "
                         f"(following {prev or 'nothing'}). Confirm by eye.")
    else:
        print("\nUN-CUED CONTENT CARDS: none — every content card carries a cue, so the "
              "EP11 C6/C8 overrun cannot happen here.")

    # ---- 3. standing cards: structural, not cued ---------------------------
    first_speech = min(s["start"] for s in shots)
    last_end = max(s["end"] for s in shots)
    ec_beat = int(build.get("endcard_beat", 24))
    title_win = (float(build.get("title_head", 0.0)), round(first_speech, 2))
    # 🔴 PLUS endcard_lead, NOT MINUS — THE ASSEMBLER IS THE SOURCE OF TRUTH HERE.
    # assemble_episode.py:139 builds the film with `bs(endcard_beat) + endcard_lead`, and
    # qc_episode.py checks it at the same place. This tool subtracted it, so it believed
    # the end card arrived 3.0s (2 x lead) EARLIER than it does — and invented overlaps
    # against a card that was never there yet.
    #
    # ⚠️ IT FABRICATED A HALT AND MOVED A CARD. EP23's "CARD-CARD overlap C23/END: 1.51s"
    # was pure arithmetic: C23 ran to 804.55 and the end card lands at 806.04. Its real
    # window was 9.49s against a 9.0s minimum — IT FITTED WHERE IT WAS. The tool even
    # printed the contradiction beside itself, "it already fits", and nobody read the two
    # lines together. EP22's C18/C19 halt is the same shape and wants re-checking.
    end_win = (round(beat_start.get(ec_beat, last_end) + float(build.get("endcard_lead", 1.5)), 2),
               round(last_end - float(build.get("warranty_tail", 6.7))
                     - float(build.get("warranty_lead", 0.3)), 2))
    warr_win = (round(last_end - float(build.get("warranty_tail", 6.7)), 2), round(last_end, 2))
    print(f"\nSTANDING CARDS — structural anchors, no cue")
    print(f"  TITLE     {title_win[0]:8.2f} -> {title_win[1]:8.2f}   "
          f"(silent head; measured hold {title_win[1]-title_win[0]:.2f}s "
          f"vs holds.TITLE {holds.get('TITLE')})")
    print(f"  END       {end_win[0]:8.2f} -> {end_win[1]:8.2f}   (beat {ec_beat} "
          f"+ endcard_lead, as assemble_episode builds it)")
    print(f"  WARRANTY  {warr_win[0]:8.2f} -> {warr_win[1]:8.2f}   (last {build.get('warranty_tail')}s)")
    if abs((title_win[1] - title_win[0]) - float(holds.get("TITLE", 0))) > 0.75:
        notes.append(f"holds.TITLE is {holds.get('TITLE')}s but the real silent head is "
                     f"{title_win[1]-title_win[0]:.2f}s — update it.")
    windows["TITLE"], windows["END"], windows["WARRANTY"] = title_win, end_win, warr_win

    # ---- 4. midroll: FOLLOWS the ask, never precedes or spans it -----------
    mid = build.get("midroll", {})
    dur, fade = float(mid.get("dur", 16.0)), float(mid.get("fade", 0.4))
    # A5 — NO DEFAULT. This used to be `mid.get("ask") or [ ...two literal phrases... ]`
    # and those two literals were EP12'S WORDS, hardcoded. On EP13 it failed safe only
    # by luck: they happened to be absent from this master, so the lookup missed and
    # the tool refused to guess. Had EP13's pool line contained either, the chip would
    # have anchored to the WRONG SENTENCE and nothing would have said so.
    #
    # The phrases are deliberately NOT quoted here. A default nobody can copy back in
    # is safer than one sitting in a comment, and test_hand_steps.py greps this file
    # for them — a comment would make that check pass on nothing.
    #
    # The ask must quote THIS episode's pool line. A value nobody set is not a
    # default to fall back on — it is a question nobody answered.
    ask = mid.get("ask")
    if not ask or len(ask) < 2 or not all(str(x).strip() for x in ask[:2]):
        problems.append(
            "build.midroll.ask is not set — it must quote the ask from THIS episode's "
            "pool line (docs/midroll-line-pool.md), first phrase and last, verbatim. "
            "There is deliberately no default: the previous one was EP12's words, and a "
            "chip anchored to another episode's sentence is worse than no chip.")
        ask = None
    a0 = a1 = None
    if ask:
        a0, a1 = find_phrase(tl, ask[0]), find_phrase(tl, ask[1])
    mid_at = None
    print(f"\nMIDROLL CHIP — FOLLOWS the ask by {MIDROLL_FOLLOW}s; never precedes it, never spans it")
    if not ask:
        print("  build.midroll.ask is NOT SET — refusing to guess (see the problem above)")
    elif a0 is None or a1 is None:
        problems.append(f"midroll: ask phrase not found in the SRT "
                        f"({ask[0]!r} -> {'ok' if a0 else 'MISSING'}, "
                        f"{ask[1]!r} -> {'ok' if a1 else 'MISSING'}). Not guessing midroll.at.")
    else:
        # THE CHIP FOLLOWS THE ASK — it does not span it (Jodie, 29 Jul 2026,
        # SUPERSEDING "must SPAN the spoken ask"; PP-STANDARDS §Card sync amended in
        # the same commit).
        #
        # Spanning meant the chip arrived BEFORE Gordon began the ask — on EP13 by
        # 0.40s, WHICH JODIE HEARD. The picture was announcing the words instead of
        # following them: the same fault as a card entering before its cue.
        #
        # +1.0s, not the +3.0s a card gets. The card delay exists because a card
        # illustrates something being EXPLAINED — words first, picture after, so the
        # viewer hears the idea before seeing it drawn. The chip reinforces a direct
        # REQUEST, and 3.0s is a third of an 8.5s ask. 1.0s follows without lagging.
        a1_end = a1 + 1.2                       # let the closing phrase finish
        mid_at = round(a0 + MIDROLL_FOLLOW, 2)
        full = dur - 2 * fade
        print(f"  ask spoken      : {a0:.2f} -> {a1_end:.2f}  ({a1_end-a0:.2f}s)")
        print(f"  chip FOLLOWS by : {MIDROLL_FOLLOW}s  (never precedes; never spans)")
        print(f"  midroll.at      : {mid_at:.2f}   (full visibility {full:.2f}s)")
        if mid_at < a0:
            problems.append(f"midroll: at {mid_at:.2f} would precede the ask at {a0:.2f}.")
        if full < MIDROLL_MIN_FULL:
            problems.append(f"midroll: {full:.2f}s full visibility is under the "
                            f"{MIDROLL_MIN_FULL}s bar.")
        windows["MIDROLL"] = (mid_at, round(mid_at + dur, 2))

    # ---- 4b. the early e-book card: FOLLOWS the spoken mention, like the chip ----
    # Every episode carries an early companion-guide line near the top (script skill
    # §4J). The marketing card — the same one the end uses, the one with the e-book's
    # first page on it — is held over it for a few seconds.
    #
    # 🔴 `at` IS DERIVED, NEVER TYPED. EP18's first attempt hard-coded 48.6 and it was
    # wrong twice over: wrong clock (presenter read as final, so 7s early) and a number
    # nobody could re-check. A typed timestamp is the EP15 `midroll.at = 235.0` fault
    # waiting to happen — right on the day it was written, stale by the next re-render.
    # Give it an `anchor` phrase and the SRT places it, exactly as the chip is placed.
    EARLY_FOLLOW = 1.0
    cta = build.get("early_cta") or {}
    cta_at = None
    if cta:
        anchor = str(cta.get("anchor") or "").strip()
        cdur = float(cta.get("dur", 6.0))
        cfade = float(cta.get("fade", 0.3))
        print("\nEARLY E-BOOK CARD — FOLLOWS the spoken mention by "
              f"{EARLY_FOLLOW}s, never precedes it")
        if not anchor:
            # A4: a missing value must not QUIETLY drop the card.
            problems.append(
                "build.early_cta is set but has no `anchor`. It must quote the opening "
                "words of this episode's early companion-guide mention, verbatim, so the "
                "card is placed from the SRT instead of a typed timestamp. Not guessing.")
            print("  anchor NOT SET — refusing to guess (see the problem above)")
        else:
            c0 = find_phrase(tl, anchor)
            if c0 is None:
                problems.append(
                    f"early_cta: anchor {anchor!r} is not in the SRT, so the card cannot "
                    "be placed. The wording of the early e-book mention has changed, or "
                    "this is the wrong master. Not guessing early_cta.at.")
                print(f"  anchor {anchor!r} NOT FOUND in the SRT")
            else:
                cta_at = round(c0 + EARLY_FOLLOW, 2)
                print(f"  mention spoken  : {c0:.2f}")
                print(f"  early_cta.at    : {cta_at:.2f}  (holds {cdur}s, "
                      f"full visibility {cdur - 2 * cfade:.2f}s)")
                if cta_at < c0:
                    problems.append("early_cta: would precede its own mention.")
                windows["EARLY_CTA"] = (cta_at, round(cta_at + cdur, 2))

    # ---- 5. ALL FOUR OVERLAP CLASSES ---------------------------------------
    broll_dur = float(build.get("broll_dur", 5))
    offs = build.get("broll_offsets") or {}
    bwin = {}
    for b in epj.get("broll", []):
        bs = beat_start.get(b["beat"])
        if bs is None:
            continue
        o = float(offs.get(b["target"], 1.0))
        bwin[b["target"]] = (round(bs + o, 2), round(bs + o + broll_dur, 2))

    bbeat = {b["target"]: b["beat"] for b in epj.get("broll", []) if b.get("target")}

    def why_broll_card(target, cid, ov):
        """Say WHY the clip and the card collide, and name the remedy ONLY if it
        has been confirmed available.

        🔴 THE LESSON THIS ENCODES (EP16, 5 Aug 2026, and it was humbling):
        `build.broll_offsets{target: sec}` ALREADY EXISTED, per-clip, defaulting
        to 1.0s — and nobody reached for it through FOUR ROUNDS of proposals.
        What we proposed first, in order, was all wrong or worse: shorten the
        holds (forbidden by the standard), set the beats WIDE (they already
        were — the overlap is about TIME, not framing), move the cues earlier
        (puts each card in front of its own punchline), move the clips to other
        beats (editorial, and Jodie's).
        The answer was to DELAY THE CLIP INSIDE THE BEAT IT WAS ALREADY IN.
        Slack left over: 14.95s / 3.88s / 8.97s, against 0.01s for a cue move.

        So: ASK WHETHER THE SLACK IS ALREADY THERE, BEFORE ANYONE PROPOSES
        TOUCHING HOLDS, WIDTHS, CUES OR BEATS. The lever was there the whole
        time; this is not "we lacked a mechanism", it is "we designed four
        before looking for one".
        """
        n = bbeat.get(target)
        bs, be = beat_start.get(n), beat_end.get(n)
        if bs is None or be is None:
            return ""
        cur = float(offs.get(target, 1.0))
        # How much later could this clip start and still finish inside its beat?
        slack = round((be - bs) - (cur + broll_dur), 2)
        need = round(ov, 2)
        if slack >= need:
            # CONFIRMED AVAILABLE — record it so --apply-broll can write it. This is
            # the only branch that is ever auto-applied.
            broll_fixes[target] = round(cur + need, 2)
            return (f" — the clip starts {cur:.2f}s into beat {n} and there is "
                    f"{slack:.2f}s of unused room at the BACK of that same beat, "
                    f"so delaying it by {need:.2f}s clears this without touching "
                    f"the card, the cue, the hold or the framing. Set "
                    f"build.broll_offsets[{target!r}] to {cur + need:.2f}.")
        return (f" — the clip starts {cur:.2f}s into beat {n} and that beat has "
                f"only {max(slack, 0):.2f}s of room left at the back, which is "
                f"less than the {need:.2f}s needed. Delaying the clip inside its "
                f"own beat CANNOT clear this one, so it is a decision rather than "
                f"an adjustment.")

    def why_card_beat(cid):
        """A card that cannot fit its beat AT ANY CUE POSITION is not a cue
        problem. EP16's C4: the beat is 13.85s and the card needs 13.0s."""
        c = next((x for x in epj.get("cards", []) if x.get("id") == cid), None)
        if not c:
            return ""
        n = c.get("beat")
        bs, be = beat_start.get(n), beat_end.get(n)
        if bs is None or be is None:
            return ""
        w = windows.get(cid)
        if not w:
            return ""
        # Read the hold off the WINDOW THIS TOOL ALREADY COMPUTED rather than
        # re-deriving it from episode.json — one source of truth, and it cannot
        # disagree with the number in the overlap line beside it.
        hold = round(w[1] - w[0], 2)
        need = round(ENTRY_DELAY + hold, 2)
        length = round(be - bs, 2)
        if need > length:
            return (f" — beat {n} is {length:.2f}s long and this card needs "
                    f"{need:.2f}s ({ENTRY_DELAY:.1f}s before it enters, then "
                    f"{hold:.2f}s on screen), so IT DOES NOT FIT AT ANY CUE "
                    f"POSITION. That is a card that is too big for its beat, not "
                    f"a cue placed badly.")
        latest = round(bs + (length - need), 2)
        return (f" — beat {n} is {length:.2f}s and the card needs {need:.2f}s, so "
                f"the latest cue that still fits starts at {latest:.2f}s.")

    def which_gives_way(first, second):
        """WHICH of an overlapping pair has to change, and by how much.

        🔴 THE ARITHMETIC A HUMAN DID BY HAND EVERY TIME (EP21 C18/C19, EP22 C18/C19).
        In an overlap A/B, A is still up when B arrives — and B's entry is fixed by its
        CUE, which is a spoken word and not ours to move. So A is the one that gives
        way, and the window it actually has is B's entry minus A's entry. The old
        message said only "too big for its beat" and named the beat of the SECOND card,
        which is how a brief came to describe C19 as needing 18.26s when 18.26s was the
        END card's dwell. Name the card, give it its number, list its ways out.
        """
        a, b = windows.get(first), windows.get(second)
        card = next((c for c in epj.get("cards", []) if c.get("id") == first), None)
        if not a or not b or card is None:
            return ""
        available = round(b[0] - a[0], 2)
        if available <= 0:
            return (f" — {first} and {second} are cued at the same moment, so this is "
                    f"not a size problem: one of the two cues has to move.")
        return (f"\n       {first} IS THE ONE THAT GIVES WAY (its window runs to "
                f"{second}'s entry): " + ch.options_for(card, build, available))

    cards_only = {k: v for k, v in windows.items() if k not in ("MIDROLL",)}
    pairs = 0
    print(f"\nOVERLAP CHECK — all four classes")
    ids = list(cards_only)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            pairs += 1
            ov = overlaps(cards_only[ids[i]], cards_only[ids[j]])
            if ov > 0.01:
                # 🔴 why_card_beat DESCRIBES THE CARD THAT GIVES WAY — ids[i], NOT ids[j].
                # It was called on ids[j] and printed that card's beat and dwell as
                # "this card", directly after naming ids[i] as the one at fault. EP23's
                # C23 read "needs 19.80s" when it needed 9.0s; EP22's C19 read "18.26s".
                # Both numbers were the END CARD'S dwell, and both led a brief. It is the
                # same misattribution which_gives_way was written to end — that fix was
                # added ALONGSIDE this line instead of replacing it, so the wrong numbers
                # kept their place at the FRONT of the message, where they are read first.
                problems.append(f"CARD-CARD overlap {ids[i]}/{ids[j]}: {ov:.2f}s"
                                + why_card_beat(ids[i])
                                + which_gives_way(ids[i], ids[j]))
    print(f"  card-card       : {pairs} pairs checked")
    if "MIDROLL" in windows:
        n = 0
        for cid, w in cards_only.items():
            n += 1
            ov = overlaps(w, windows["MIDROLL"])
            if ov > 0.01:
                problems.append(f"CARD-MIDROLL overlap {cid}: {ov:.2f}s")
        print(f"  card-midroll    : {n} pairs checked")
    n = 0
    for t, w in bwin.items():
        for cid, cw in cards_only.items():
            n += 1
            ov = overlaps(w, cw)
            if ov > 0.01:
                problems.append(f"B-ROLL-CARD overlap {t}/{cid}: {ov:.2f}s — a card writing "
                                f"over a clip means one of them wasn't seen"
                                + why_broll_card(t, cid, ov) + why_card_beat(cid))
    print(f"  b-roll-card     : {n} pairs checked")
    if "MIDROLL" in windows:
        for t, w in bwin.items():
            ov = overlaps(w, windows["MIDROLL"])
            if ov > 0.01:
                problems.append(f"B-ROLL-MIDROLL overlap {t}: {ov:.2f}s")
        print(f"  b-roll-midroll  : {len(bwin)} pairs checked")

    # ---- 6. shot plan DERIVED FROM the final card windows -------------------
    print(f"\nSHOT PLAN — panel-push cards need WIDE for the WHOLE window, entry to exit")
    pp = [cid for cid in cards_only if layout.get(cid) == "panel-push"]
    if not pp:
        print("  no panel-push cards")
    for cid in pp:
        s, e = cards_only[cid]
        spanned = [b["shot"] for b in shots if overlaps((b["start"], b["end"]), (s, e)) > 0.01]
        bad = [n for n in spanned if framing.get(n) != "WIDE"]
        flag = "OK" if not bad else "NOT WIDE"
        print(f"  {cid:6} {s:8.2f} -> {e:8.2f}  spans beats {spanned}  {flag}")
        if bad:
            # 🔴 THIS IS NOT A DECISION, AND IT HALTED TWO OF EP23'S FOUR (Jodie, 13 Aug).
            # WIDE is the ONLY lawful answer — the rule has no second option — and the
            # offending beats are already computed, on the line above. It then stopped the
            # build so somebody could retype MCU as WIDE. Same argument as --apply-broll.
            #
            # ⚠️ AND WIDENING A BEAT CANNOT LOSE A FACT. That is what makes it safe to
            # apply where a card that is too big for its window is not: nothing is
            # shortened, nothing is dropped, no wording moves. The card-size halt stays
            # a halt precisely because it would have to give something up.
            if apply_wide:
                for n in bad:
                    wide_fixes.setdefault(n, []).append(cid)
            else:
                problems.append(f"SHOT PLAN {cid}: on-screen card is up while beats {bad} "
                                f"are MCU. Set them WIDE, or the card lands over Gordon's "
                                f"face (the EP11 failure).")

    # ---- report ------------------------------------------------------------
    print("\n" + "=" * 74)
    print("""ANCHORING — A DECISION FOR JODIE, NOT A DEFAULT THIS TOOL SHOULD MAKE ALONE.
  Two defensible anchors, and EP11 proves they are NOT the same:
    PHRASE anchor (this tool's `lead`): 3.0s after the cue PHRASE is actually spoken.
    CUE-BLOCK anchor (`ep11-way`):      3.0s after the SRT block CONTAINING it begins.
  Reproducing EP11's shipped leads from its own SRT showed |difference| == slack to
  within 0.01s on all 7 cued cards, i.e. EP11 shipped the CUE-BLOCK anchor. Where the
  phrase sits deep in a block that is up to 3.5s EARLIER than the phrase is spoken —
  and PP-STANDARDS says a card must ENTER ON OR JUST AFTER its cue, NEVER BEFORE.
  That is consistent with Jodie twice finding EP11's cards "still early" (0.4 -> 2.6
  -> 3.0). The PHRASE anchor is the stricter reading of the rule, so it is the default
  here — but it will run cards slightly later than EP11 did, and that is a visible
  change she should agree to rather than discover.""")
    for n in notes:
        print(f"NOTE    {n}")
    if problems or wide_fixes:
        # ⚠️ WRITTEN AND RE-RUN, NOT WRITTEN AND TRUSTED. The b-roll delay is computed
        # from a ROUNDED overlap, so one pass can leave a hundredth of a second still
        # touching — EP21 needed two rounds. Widening a beat can likewise move a card's
        # neighbours into view. The caller loops until nothing moves, and every problem
        # class that is a real DECISION still halts.
        applied = []
        if apply_broll and broll_fixes:
            offs_out = build.setdefault("broll_offsets", {})
            for t, v in sorted(broll_fixes.items()):
                was = offs_out.get(t)
                offs_out[t] = v
                print(f"   applied build.broll_offsets[{t!r}] = {v}"
                      + (f"  (was {was})" if was is not None else "  (was unset)"))
            applied.append(f"{len(broll_fixes)} b-roll offset(s)")
        if apply_wide and wide_fixes:
            by_n = {b["n"]: b for b in epj["beats"]}
            for n, cids in sorted(wide_fixes.items()):
                b = by_n.get(n)
                if b is None:                    # a beat the shot map has and the json does not
                    problems.append(f"SHOT PLAN: beat {n} needs WIDE but is not in "
                                    f"episode.json's beats[] — cannot apply.")
                    continue
                was = b.get("framing")
                b["framing"] = "WIDE"
                print(f"   applied beats[{n}].framing = WIDE  (was {was}) "
                      f"— for {', '.join(cids)}")
            applied.append(f"{len(wide_fixes)} beat framing(s)")
            # A4 — the authored note is now overtaken by what we just wrote. Say so in
            # the file, or the next reader trusts prose that describes a layout mix the
            # episode no longer has (EP23's still claimed "EIGHTEEN WIDE OF FORTY-ONE").
            if _framing.stamp_framing_note(
                    epj, [(n, None, cids) for n, cids in sorted(wide_fixes.items())]):
                print("   stamped _framing_note as re-derived")
        if applied:
            epj_path.write_text(json.dumps(epj, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
            print(f"\nAPPLIED {' and '.join(applied)} the tool had already worked out "
                  f"— re-deriving.\n")
            return "RETRY"
    if problems:
        print(f"\n{len(problems)} PROBLEM(S) — NOTHING WRITTEN:")
        for p in problems:
            print(f"  !! {p}")
        print("\nThese are decisions, not auto-fixes. Shift windows, lengthen the chip or "
              "set beats WIDE, then re-run.")
        sys.exit(1)

    print("\nALL CHECKS PASS.")
    print(f"leads        = {json.dumps(leads)}")
    print(f"midroll.at   = {mid_at}")
    if cta:
        print(f"early_cta.at = {cta_at}")
    if write:
        build["leads"] = leads
        if mid_at is not None:
            build["midroll"]["at"] = mid_at
        if cta_at is not None:
            build["early_cta"]["at"] = cta_at
        epj_path.write_text(json.dumps(epj, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        print(f"\nWROTE {epj_path} (build.leads, build.midroll.at"
              + (", build.early_cta.at" if cta_at is not None else "") + " only).")
    else:
        print("\nReport only. Re-run with --write to apply.")


if __name__ == "__main__":
    # --apply-broll and --apply-wide make main() return "RETRY" once they have written
    # what they already knew. Bounded, because a loop that cannot converge must stop and
    # say so rather than write the same value for ever.
    for _round in range(1, 6):
        if main() != "RETRY":
            break
    else:
        sys.exit("the mechanical fixes did not settle after 5 rounds — stopping rather "
                 "than writing the same values again. This one needs a look.")
