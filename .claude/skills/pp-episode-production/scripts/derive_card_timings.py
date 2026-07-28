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
  · The midroll chip must SPAN the spoken ask, not precede it, with >=6s full visibility.
  · CHECK ALL FOUR OVERLAP CLASSES: card-card, card-midroll, b-roll-card, b-roll-midroll.
  · While an ON-SCREEN (panel-push) card is visible the shot must be WIDE for the WHOLE
    window, entry to exit — not merely at the in-point. Full-screen cards are unaffected.
  · If a card cannot take the full shift, THAT IS A DECISION FOR JODIE. This tool reports
    it and refuses to write; it never silently shortens a card or quietly gives it a
    smaller offset.

IT NEVER GUESSES. If a cue phrase is not found in the SRT it is a HARD FAIL and nothing
is written — an unlocatable cue means the words changed or the master is wrong, and either
way a human needs to look. There is no fuzzy fallback on purpose.

NOT WIRED INTO THE ENGINE. Run by hand. Wiring it into shot_map/assemble is a separate
decision on the backlog.
"""
import json, re, sys, pathlib

ENTRY_DELAY = 3.0          # PP-STANDARDS: card entry = spoken cue + 3.0s
MIDROLL_MIN_FULL = 6.0     # >=6s of FULL visibility (fades on top)


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

    epj_path = d / "docs/episode.json"
    srt_path = d / "renders/generated.srt"
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
        if hold < min_hold:
            problems.append(f"{cid}: hold {hold}s is below min_card_hold {min_hold}s. "
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
    end_win = (round(beat_start.get(ec_beat, last_end) - float(build.get("endcard_lead", 1.5)), 2),
               round(last_end - float(build.get("warranty_tail", 6.7))
                     - float(build.get("warranty_lead", 0.3)), 2))
    warr_win = (round(last_end - float(build.get("warranty_tail", 6.7)), 2), round(last_end, 2))
    print(f"\nSTANDING CARDS — structural anchors, no cue")
    print(f"  TITLE     {title_win[0]:8.2f} -> {title_win[1]:8.2f}   "
          f"(silent head; measured hold {title_win[1]-title_win[0]:.2f}s "
          f"vs holds.TITLE {holds.get('TITLE')})")
    print(f"  END       {end_win[0]:8.2f} -> {end_win[1]:8.2f}   (beat {ec_beat} - endcard_lead)")
    print(f"  WARRANTY  {warr_win[0]:8.2f} -> {warr_win[1]:8.2f}   (last {build.get('warranty_tail')}s)")
    if abs((title_win[1] - title_win[0]) - float(holds.get("TITLE", 0))) > 0.75:
        notes.append(f"holds.TITLE is {holds.get('TITLE')}s but the real silent head is "
                     f"{title_win[1]-title_win[0]:.2f}s — update it.")
    windows["TITLE"], windows["END"], windows["WARRANTY"] = title_win, end_win, warr_win

    # ---- 4. midroll: must SPAN the spoken ask ------------------------------
    mid = build.get("midroll", {})
    dur, fade = float(mid.get("dur", 16.0)), float(mid.get("fade", 0.4))
    ask = mid.get("ask") or ["a like is what pushes it", "saves you hunting"]
    a0, a1 = find_phrase(tl, ask[0]), find_phrase(tl, ask[1])
    mid_at = None
    print(f"\nMIDROLL CHIP — must SPAN the ask, not precede it")
    if a0 is None or a1 is None:
        problems.append(f"midroll: ask phrase not found in the SRT "
                        f"({ask[0]!r} -> {'ok' if a0 else 'MISSING'}, "
                        f"{ask[1]!r} -> {'ok' if a1 else 'MISSING'}). Not guessing midroll.at.")
    else:
        a1_end = a1 + 1.2                       # let the closing phrase finish
        lo, hi = a1_end + fade - dur, a0 - fade
        print(f"  ask spoken      : {a0:.2f} -> {a1_end:.2f}  ({a1_end-a0:.2f}s)")
        print(f"  legal at range  : {lo:.2f} .. {hi:.2f}   (dur {dur}, fade {fade})")
        if lo > hi:
            problems.append(f"midroll: the ask runs {a1_end-a0:.2f}s but the chip only offers "
                            f"{dur-2*fade:.2f}s of full visibility. LENGTHEN dur — do not "
                            f"clip the ask. Jodie's call.")
        else:
            mid_at = round(max(lo, min(hi, a0 - fade)), 2)
            full = dur - 2 * fade
            print(f"  midroll.at      : {mid_at:.2f}   (full visibility {full:.2f}s)")
            if full < MIDROLL_MIN_FULL:
                problems.append(f"midroll: {full:.2f}s full visibility is under the "
                                f"{MIDROLL_MIN_FULL}s bar.")
            windows["MIDROLL"] = (mid_at, round(mid_at + dur, 2))

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

    cards_only = {k: v for k, v in windows.items() if k not in ("MIDROLL",)}
    pairs = 0
    print(f"\nOVERLAP CHECK — all four classes")
    ids = list(cards_only)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            pairs += 1
            ov = overlaps(cards_only[ids[i]], cards_only[ids[j]])
            if ov > 0.01:
                problems.append(f"CARD-CARD overlap {ids[i]}/{ids[j]}: {ov:.2f}s")
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
                                f"over a clip means one of them wasn't seen")
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
            problems.append(f"SHOT PLAN {cid}: on-screen card is up while beats {bad} are "
                            f"MCU. Set them WIDE, or the card lands over Gordon's face "
                            f"(the EP11 failure).")

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
    if problems:
        print(f"\n{len(problems)} PROBLEM(S) — NOTHING WRITTEN:")
        for p in problems:
            print(f"  !! {p}")
        print("\nThese are decisions, not auto-fixes. Shift windows, lengthen the chip or "
              "set beats WIDE, then re-run.")
        sys.exit(1)

    print("\nALL CHECKS PASS.")
    print(f"leads      = {json.dumps(leads)}")
    print(f"midroll.at = {mid_at}")
    if write:
        build["leads"] = leads
        if mid_at is not None:
            build["midroll"]["at"] = mid_at
        epj_path.write_text(json.dumps(epj, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        print(f"\nWROTE {epj_path} (build.leads and build.midroll.at only).")
    else:
        print("\nReport only. Re-run with --write to apply.")


if __name__ == "__main__":
    main()
