#!/usr/bin/env python3
"""twoway_a17.py — A17: a card's points build ONE BY ONE, AS THE READER SAYS EACH ONE.

    python engine/twoway_a17.py <ep_number> [--pp DIR] [--write]

Jodie, 6 Oct 2026, watching EP55 cut 1 (amendment A17 in PP-TWO-WAY-BUILD-SPEC.md):
the graphics cards stay up longer, and their points build in one by one as the reader
says each one, timed to the speech — not all together on entry. From Fundamentals Part 3
(EP56) on; EP55 ships unchanged.

THIS MODULE IS THE ONE HOME OF THAT RULE. Three stages ask it three questions:

  1. THE PLAN (estimate clock) — `plan(epj)`. Where should an A17 card ENTER, and how
     long must it HOLD? It enters on the sentence that carries its FIRST point (never
     the paragraph's first sentence, which left EP56's C1/C2/C10 up 8-15s before their
     first point was said — `twoway_beats` asks `first_anchors()` for this), and it holds
     until its LAST point has been said, plus that point's reading time and the settle.
     The hold and the layout depend on each other, so this runs `twoway_beats.apply` to a
     fixed point. (This lived in a scratch commission script for EP56's stage 2; it is
     here so the next episode does not need one.)

  2. THE BUILD (measured clock) — `measure(plan, cues, tl, epj, head_s)`. When, on the
     FINISHED clock, is each point said? The anchor is the reader's own words, found in
     `renders/merged.srt` (derived, never typed — the same rule as the standing graphics),
     inside the card's own turn. Each point's entrance delay is `said - card entry`,
     never earlier than the block's own stagger and never closer than a readable
     cadence to the point before. Written to `episode.json -> build.a17`, where
     `author_cards` reads it.

  3. THE CHECK — `violations(a17)`. A point not spoken while its card is up is a SCRIPT
     fault for the plan stage, never a guessed time (A17's own words). A card up long
     before its first point is the fault the plan flagged on C1/C2/C10.

📌 THE ANCHOR is `_a17_points: [[key, "words of the article"], ...]` on each card, in
speaking order. `key` names what lands: `cols[2]` is the second item of the `cols` list;
`q` is the element that draws `{{q}}`. Which element that is, `author_cards` reads off the
block's own template — there is no table of selectors here to fall out of date.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

PP = pathlib.Path("G:/My Drive/PP Videos")

POINT_STEP_MIN_MS = 240
"""Two points never land closer than the readable cadence (card_check's
DATA_STEP_MIN_MS, the pp-motion-graphics pacing ruling). Two anchors said in the same
breath still arrive one after the other."""

FIRST_POINT_WAIT_MAX_S = 4.0
"""How long a card may be up before its first point is said. The plan flagged C1/C2/C10
at 8, 12 and 15 seconds of an empty card; a card on screen that long with nothing on it
but a headline is the fault, not a style."""

SAID_EARLY_TOLERANCE_S = 0.5
"""A point said up to half a second before its card is fully up still reads as said WITH
it (the card's own entrance takes ~0.4s); earlier than that, the words are gone before
the point arrives."""


class A17Fault(Exception):
    pass


# ───────────────────────────────────────────────────────────────── the anchors ──

def points(card: dict) -> list[tuple[str, str]]:
    return [(str(k), str(a)) for k, a in (card.get("_a17_points") or [])]


def is_a17(card: dict) -> bool:
    return bool(card.get("_a17_points"))


def first_anchors(cards: list[dict]) -> dict[str, str]:
    """{card id: the article words of its FIRST point}, for every A17 card."""
    return {c["id"]: points(c)[0][1] for c in cards if is_a17(c)}


def norm_words(text: str) -> list[str]:
    """ONE tokenisation, derive_card_timings.word_timeline's: runs of letters and digits,
    so "it's" is "it" + "s" on BOTH sides of every match (the SRT's and the anchor's)."""
    return re.findall(r"[a-z0-9]+", (text or "").lower())


_TAG = re.compile(r"^\s*\[[A-Z]{2}\]\s*")


def untagged(cues: list[dict]) -> list[tuple[float, float, str]]:
    """merged.srt's cues WITHOUT the `[BB] ` / `[BM] ` speaker tag, for word timing.

    🔴 The word timeline places a word by its CHARACTER position inside its cue, so a
    five-character tag at the front of every cue shifts every word in it later — about
    half a second on a typical sentence, more on the first word. Found by this module's
    own test (12 Nov 2026): a paragraph measured 6.58s that was 6.00s."""
    return [(c["start"], c["end"], _TAG.sub("", c["text"] or "")) for c in cues]


def spoken_words(article_words: str) -> list[str]:
    """The anchor as the reader SAYS it: the split's own figures-to-words fold, the same
    one that wrote the script, so "$100,000" finds "one hundred thousand dollars"."""
    import twoway_split as ts
    return norm_words(ts.spoken(article_words))


def point_text(card: dict, key: str) -> str:
    """The words the point puts on the card — what the viewer reads after it lands."""
    content = card.get("content") or {}
    m = re.fullmatch(r"(\w+)\[(\d+)\]", key)
    if m:
        items = content.get(m.group(1)) or []
        i = int(m.group(2)) - 1
        it = items[i] if 0 <= i < len(items) else None
        if isinstance(it, dict):
            return " ".join(str(v) for k, v in it.items()
                            if isinstance(v, (str, int, float)) and k not in ("tone", "band"))
        return "" if it is None else str(it)
    v = content.get(key)
    return "" if v is None else str(v)


# ─────────────────────────────────────────────── 1. the plan (estimate clock) ──

def _est_said(epj: dict, segs: list[dict], card: dict, which: int, end: bool) -> float:
    """Estimated plan time at which point `which` STARTS (end=False) or has been SAID
    (end=True) — the plan's own pace model: a beat's time shared by word count."""
    beats = epj["beats"]
    b0 = next(b for b in beats if b["n"] == card["beat"])
    turn = b0["turn"]
    t = min(s["from_s"] for s in segs if s["turn"] == turn)
    target = norm_words(points(card)[which][1])
    import twoway_beats as tb
    seen_card_beat = False
    for b in [x for x in beats if x["turn"] == turn]:
        words = norm_words(b["line"])
        if b["n"] == card["beat"]:
            seen_card_beat = True
        if seen_card_beat:
            for i in range(len(words) - len(target) + 1):
                if words[i:i + len(target)] == target:
                    upto = i + (len(target) if end else 0)
                    # 🔴 MEASURED SENTENCES WHEN THEY EXIST. Spreading a whole PARAGRAPH's
                    # time evenly over its words put EP56's C10 last point ~3s late and
                    # asked for a 15.6s hold that crowded a paid clip out of the turn; the
                    # sentence it is in, and its share of THAT sentence, is the honest model.
                    ss = tb.sentences(b["line"]) or [b["line"]]
                    meas = b.get("est_sentence_s")
                    if isinstance(meas, list) and len(meas) == len(ss):
                        k = 0
                        for s_txt, s_dur in zip(ss, meas):
                            n = len(norm_words(s_txt))
                            if upto <= k + n:
                                return round(t + s_dur * (upto - k) / max(1, n), 2)
                            k += n
                            t += s_dur
                        return round(t, 2)
                    return round(t + b["est_s"] * upto / max(1, len(words)), 2)
        t += b["est_s"]
    raise A17Fault(f"{card['id']}: point {which + 1} {points(card)[which][1]!r} is not in "
                   f"the reader's words in turn {turn} from beat {card['beat']} on.")


def plan(epj: dict, max_rounds: int = 8) -> dict:
    """`twoway_beats.apply` with every A17 card's hold raised to cover its last point.

    The hold is RECOMPUTED from the card's own reading floor each round, never ratcheted,
    so moving the entry later (onto the first point) shortens the hold again."""
    import card_hold as ch
    import twoway_beats as tb
    build = epj.setdefault("build", {})
    a17_cards = [c for c in epj.get("cards", []) if is_a17(c)]
    base = {c["id"]: ch.hold_for(c, build) for c in epj.get("cards", [])}
    # 🔴 START EVERY A17 CARD FROM ITS OWN READING FLOOR, NEVER FROM A STORED HOLD.
    # EP56's first run started from the hold the scratch commission had raised for a
    # paragraph-start entry (C10: 23.6s). On the first pass that over-long card crowded
    # the paid b-roll after it out of the turn, the dwell loop then pushed C10 EARLIER to
    # make room, the earlier entry needed a longer hold, and the loop settled there: an
    # 11s empty card and an approved clip dropped. From the floor, the hold only ever
    # rises as far as the card's last point actually needs.
    stored = dict(build.get("holds") or {})
    holds = {cid: (base[cid] if cid in {c["id"] for c in a17_cards} else stored.get(cid, base[cid]))
             for cid in base}
    report = {}
    for _ in range(max_rounds):
        build["holds"] = dict(holds)
        tb.apply(epj)
        segs = epj["layout_plan"]
        changed = False
        report = {}
        for c in a17_cards:
            cs = [s for s in segs if s.get("kind") == "card" and s.get("card") == c["id"]]
            if not cs:
                if abs(holds[c["id"]] - base[c["id"]]) > 0.05:
                    holds[c["id"]] = base[c["id"]]
                    changed = True
                report[c["id"]] = {"dropped": True}
                continue
            enter = cs[0]["from_s"]
            first = _est_said(epj, segs, c, 0, end=False)
            # the SAME definition the check uses (violations): a point LANDS as its phrase
            # starts, then gets its reading time + the settle. Timing it to the phrase's END
            # here asked for more than the check does, and that difference cost turn 12 a clip.
            last = _est_said(epj, segs, c, len(points(c)) - 1, end=False)
            read = len(point_text(c, points(c)[-1][0]).split()) / ch.WORDS_PER_S_READ
            need = round((last - enter) + read + ch.SETTLE_S, 2)
            # build.a17_hold_floor: what the MEASURED clock showed this card needs (written
            # by close_on_measured), so the estimate cannot talk the hold back down.
            extra = float((build.get("a17_hold_floor") or {}).get(c["id"], 0.0))
            want = round(max(base[c["id"]], need, extra), 1)
            report[c["id"]] = {"enter_s": enter, "first_point_s": first,
                               "last_point_said_s": last, "need_s": need, "hold_s": want}
            if abs(want - holds[c["id"]]) > 0.05:
                holds[c["id"]] = want
                changed = True
        if not changed:
            break
    build["holds"] = dict(holds)
    build["_a17_plan"] = report
    return epj


# ────────────────────────────────────────── 2. the build (measured clock) ──

def _turn_span(tl: list[dict], turn: int) -> tuple[float, float] | None:
    seg = [s for s in tl if s.get("turn") == turn and s.get("kind") != "latency"]
    if not seg:
        return None
    return min(s["from_s"] for s in seg), max(s["to_s"] for s in seg)


def _find(words: list[tuple[str, float]], target: list[str], lo: float, hi: float,
          after: float) -> float | None:
    """Start time of `target` inside [lo, hi], at or after `after`. Word timeline as
    derive_card_timings builds it (character-proportional inside a cue)."""
    n = len(target)
    for i in range(len(words) - n + 1):
        t = words[i][1]
        if t < lo - 0.01 or t > hi + 0.01 or t < after - 0.01:
            continue
        if [w for w, _ in words[i:i + n]] == target:
            return t
    return None


def measure(segments: list[dict], cues: list[dict], timeline: list[dict], epj: dict,
            head_s: float, base_delays: dict[str, list[int]] | None = None) -> dict:
    """Each A17 card's point times and entrance delays on the FINISHED clock.

    `segments` is the assembled plan (finished clock). `cues` are merged.srt and
    `timeline` the interleaved master timeline, both on the DIALOGUE clock; `head_s`
    crosses them (CLAUDE.md 1b — a time is a number in a frame).
    `base_delays` {card id: [the block's own delay for each point, ms]} is the floor a
    point may not land before; without it the floor is 0.
    """
    import derive_card_timings as dct
    words = dct.word_timeline(untagged(cues))
    beats = {b["n"]: b for b in epj.get("beats", [])}
    out = {}
    for c in epj.get("cards", []):
        if not is_a17(c):
            continue
        cs = [s for s in segments if s.get("card") == c["id"]]
        if not cs:
            dropped = any(str(x).startswith(f"DROPPED {c['id']} ")
                          for x in (epj.get("build") or {}).get("_layout_placement") or [])
            # A card taken off its beat as LATE (engine/twoway_run.do_replan, the standing rule:
            # dropped, never placed late — EP57, 14 Nov 2026) is a reported drop too, recorded in
            # build.a17_late_dropped by the step that made it.
            late = next((r for r in (epj.get("build") or {}).get("a17_late_dropped") or []
                         if r.get("card") == c["id"]), None)
            # A card the PLANNER dropped, and said so, is a reported drop with nothing to
            # time; a card that vanished between the plan and the mapping is a fault.
            out[c["id"]] = ({"dropped": "dropped by the planner (see build._layout_placement)"}
                            if dropped else
                            {"dropped": f"dropped — {late.get('why') or 'late'} "
                                        f"(see build.a17_late_dropped)"}
                            if late else {"problem": "not in the assembled plan"})
            continue
        enter, leave = min(s["from_s"] for s in cs), max(s["to_s"] for s in cs)
        turn = beats[c["beat"]]["turn"]
        span = _turn_span(timeline, turn)
        if span is None:
            out[c["id"]] = {"problem": f"turn {turn} is not in the master timeline"}
            continue
        lo, hi = span
        floors = (base_delays or {}).get(c["id"]) or [0] * len(points(c))
        pts, after, prev = [], lo, None
        for i, (key, anchor) in enumerate(points(c)):
            t = _find(words, spoken_words(anchor), lo, hi, after)
            row = {"key": key, "anchor": anchor}
            if t is None:
                row["problem"] = "not found in the reader's words in its own turn"
                pts.append(row)
                continue
            after = t
            said = round(t + head_s, 3)
            # the SENTENCE it is said in: a picture may only change on a sentence END (A10
            # 4a), so the latest a card could legally have entered and still be up for this
            # point is the last sentence end before it. NOT a cue start: one long sentence
            # can be split across several cues, and a cue start is not a legal entry.
            import twoway_interleave as ti
            prior = [e for e in ti.sentence_ends(cues) if e <= t + 1e-6]
            row["sentence_from_s"] = round((max(prior) if prior else lo) + head_s, 3)
            want = max(int(floors[i] if i < len(floors) else 0),
                       int(round((said - enter) * 1000)))
            if prev is not None:
                want = max(want, prev + POINT_STEP_MIN_MS)
            prev = want
            row.update(said_at_s=said, delay_ms=want)
            pts.append(row)
        out[c["id"]] = {"enter_s": round(enter, 3), "exit_s": round(leave, 3),
                        "turn": turn, "points": pts}
    return out


# ──────────────────────────────────────────────────────────────── 3. check ──

def violations(a17: dict, epj: dict) -> list[str]:
    import card_hold as ch
    cards = {c["id"]: c for c in epj.get("cards", [])}
    out = []
    for cid, r in a17.items():
        if r.get("dropped"):
            continue                      # reported by notes(); the planner's own drop log
        if r.get("problem"):
            out.append(f"A17 {cid}: {r['problem']}.")
            continue
        enter, leave = r["enter_s"], r["exit_s"]
        pts = r["points"]
        for p in pts:
            if p.get("problem"):
                out.append(f"A17 {cid} {p['key']}: {p['anchor']!r} {p['problem']}. A point "
                           f"whose words are not spoken is a SCRIPT fault, never a guessed time.")
        said = [p for p in pts if "said_at_s" in p]
        if not said:
            continue
        first = said[0]
        wait = first["said_at_s"] - enter
        if (wait > FIRST_POINT_WAIT_MAX_S
                and enter < first.get("sentence_from_s", enter) - SAID_EARLY_TOLERANCE_S):
            out.append(f"A17 {cid}: up {wait:.1f}s before its first point is said (limit "
                       f"{FIRST_POINT_WAIT_MAX_S:.0f}s), and it entered BEFORE the sentence "
                       f"that point is in — an empty card the plan could have avoided.")
        for p in said:
            if p["said_at_s"] < enter - SAID_EARLY_TOLERANCE_S:
                out.append(f"A17 {cid} {p['key']}: said {enter - p['said_at_s']:.1f}s BEFORE "
                           f"the card is up, so the point arrives after its words.")
        last = said[-1]
        read = len(point_text(cards[cid], last["key"]).split()) / ch.WORDS_PER_S_READ
        lands = enter + last["delay_ms"] / 1000.0
        if lands + read + ch.SETTLE_S > leave + 0.05:
            out.append(f"A17 {cid}: its last point lands at {lands:.1f}s and needs "
                       f"{read + ch.SETTLE_S:.1f}s to be read and settle, but the card "
                       f"leaves at {leave:.1f}s.")
    return out


def shortfalls(a17: dict, epj: dict) -> dict[str, float]:
    """{card: seconds} by which a card leaves before its last point has been read + settled
    on the MEASURED clock — the same arithmetic as `violations`, as a number."""
    import card_hold as ch
    cards = {c["id"]: c for c in epj.get("cards", [])}
    out = {}
    for cid, r in a17.items():
        said = [p for p in r.get("points") or [] if "delay_ms" in p]
        if r.get("problem") or not said:
            continue
        read = len(point_text(cards[cid], said[-1]["key"]).split()) / ch.WORDS_PER_S_READ
        short = r["enter_s"] + said[-1]["delay_ms"] / 1000.0 + read + ch.SETTLE_S - r["exit_s"]
        if short > 0.05:
            out[cid] = round(short, 2)
    return out


def close_on_measured(d, epj: dict, tl: list[dict], cues: list[dict], head_s: float,
                      floors: dict, rounds: int = 4) -> dict:
    """Plan → the render's own mapped segments → measure, until no card leaves before its
    last point is read. A shortfall raises that card's hold floor by exactly the shortfall
    (+0.1s) in `build.a17_hold_floor` and the plan is derived again. Returns the measure."""
    import twoway_assemble as ta
    res = {}
    for _ in range(rounds):
        plan(epj)
        segs = ta.mapped_segments(d, epj, tl, cues)["mapped"]
        res = measure(segs, cues, tl, epj, head_s, floors)
        short = shortfalls(res, epj)
        if not short:
            break
        fl = epj["build"].setdefault("a17_hold_floor", {})
        for cid, s in short.items():
            fl[cid] = round(max(float(fl.get(cid, 0.0)),
                                float(epj["build"]["holds"].get(cid, 0.0))) + s + 0.1, 1)
            print(f"  measured: {cid} short by {s:.2f}s -> hold floor {fl[cid]}s, re-planning")
    return res


def notes(a17: dict) -> list[str]:
    """Facts for a human, not faults: a card that enters ON its first point's sentence and
    still waits longer than the limit, because that sentence is long. Picture changes land
    on sentence ends (A10 4a), so the plan cannot do better; only the words could."""
    out = []
    for cid, r in a17.items():
        if r.get("dropped"):
            out.append(f"REPORTED A17 {cid}: {r['dropped']} — not on screen in this cut.")
            continue
        said = [p for p in r.get("points") or [] if "said_at_s" in p]
        if not said:
            continue
        wait = said[0]["said_at_s"] - r["enter_s"]
        if (wait > FIRST_POINT_WAIT_MAX_S
                and r["enter_s"] >= said[0].get("sentence_from_s", r["enter_s"]) - SAID_EARLY_TOLERANCE_S):
            out.append(f"REPORTED A17 {cid}: up {wait:.1f}s before its first point — it enters "
                       f"on the very sentence that point is in, and that sentence is long.")
    return out


# ─────────────────────────────────────────────────────────────────── main ──

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--write", action="store_true",
                    help="write build.a17 (and, with --replan, the plan) into docs/episode.json")
    ap.add_argument("--replan", action="store_true",
                    help="re-derive the plan on the MEASURED clock first "
                         "(twoway_beats.measured_beats), then measure the points")
    a = ap.parse_args()
    import ep_paths
    import twoway_assemble as ta
    import twoway_beats as tb
    import twoway_interleave as ti
    pp = pathlib.Path(a.pp)
    d = ep_paths.episode_dir(a.ep_number, pp)
    epj_p = d / "docs/episode.json"
    epj = json.loads(epj_p.read_text(encoding="utf-8"))
    tlj = json.loads((d / "renders/master-timeline.json").read_text(encoding="utf-8"))
    cues = ti.read_srt((d / "renders/merged.srt").read_text(encoding="utf-8"))
    import author_cards as ac
    floors = {c["id"]: ac.a17_floors(c, ac.load_block(c["block"]))
              for c in epj.get("cards", []) if is_a17(c)}
    if a.replan:
        epj["beats"] = tb.measured_beats(epj["beats"], cues, tlj["timeline"])
        close_on_measured(d, epj, tlj["timeline"], cues, ta.TITLE_HEAD_S, floors)
        t = tb.tally(epj["layout_plan"])
        print(f"RE-PLANNED ON THE MEASURED CLOCK: dialogue {t['total_s']:.1f}s, two-box "
              f"{100 * t['two-box_s'] / t['total_s']:.1f}%, single "
              f"{100 * t['single_s'] / t['total_s']:.1f}%, cards {100 * t['card_s'] / t['total_s']:.1f}%, "
              f"b-roll {100 * t['broll_s'] / t['total_s']:.1f}%")
        for line in epj["build"].get("_layout_placement") or []:
            print("  · " + line[:200])
        for v in tb.violations(epj["layout_plan"], tb.broll_floors(epj)):
            print("  plan: " + v[:220])
    # The SAME segments the render will use (b-roll clamps included) — never a second copy.
    segs = ta.mapped_segments(d, epj, tlj["timeline"], cues)["mapped"]
    res = measure(segs, cues, tlj["timeline"], epj, ta.TITLE_HEAD_S, floors)
    for cid, r in res.items():
        if r.get("problem") or r.get("dropped"):
            print(f"{cid}: {r.get('problem') or r.get('dropped')}")
            continue
        print(f"{cid}: up {r['enter_s']:.1f}-{r['exit_s']:.1f}s ({r['exit_s'] - r['enter_s']:.1f}s)")
        for p in r["points"]:
            if "said_at_s" in p:
                print(f"    {p['key']:<11} said {p['said_at_s']:7.2f}s  "
                      f"(+{p['said_at_s'] - r['enter_s']:5.2f}s)  lands +{p['delay_ms'] / 1000:5.2f}s  "
                      f"{p['anchor']!r}")
            else:
                print(f"    {p['key']:<11} {p['problem']}: {p['anchor']!r}")
    for x in notes(res):
        print("  \u00b7 " + x)
    v = violations(res, epj)
    print(f"\n{len(v)} A17 violation(s)" if v else "\n\u2705 A17: every point said while its card is up")
    for x in v:
        print("  ! " + x)
    if a.write:
        import os
        epj.setdefault("build", {})["a17"] = res
        # never truncate the file of record in place: temp file, re-read, then rename
        tmp = epj_p.with_name(epj_p.name + ".tmp")
        tmp.write_text(json.dumps(epj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        json.loads(tmp.read_text(encoding="utf-8"))
        os.replace(tmp, epj_p)
        print(f"wrote build.a17 for {len(res)} card(s)"
              + (" and the measured-clock plan" if a.replan else "") + f" into {epj_p.name}")
    return 1 if v else 0


if __name__ == "__main__":
    raise SystemExit(main())
