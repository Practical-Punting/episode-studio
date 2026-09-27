#!/usr/bin/env python3
"""twoway_end_sequence.py — the standing graphics and the tail, for the two-way.

    python engine/twoway_end_sequence.py <ep_number> [--pp DIR]

🔴 WHY THIS EXISTS. The two-way assembler wrote its own ending — a 3s settle, then a
6s end card, then a 3.5s warranty — and every check in its suite passed, because not
one of them had ever been asked whether that was the ENDING THIS CHANNEL HAS. It is
not. PP-STANDARDS §END SEQUENCE rule 2 says the end card *"fades in on the e-book beat
and stays up until the warranty takes over … It must be ON SCREEN while Gordon speaks
the e-book line — never come-and-go early"*, and `assemble_episode.py` has built it
that way for forty-two published episodes.

Measured on EP48's own pixels (published, correct):

    end card in   760.3s   (the e-book line is spoken at 758.8s, last word 771.9s)
    warranty in   772.4s   = last word + 0.3
    warranty out  781.6s   = last word + 9.7  — 9.2s on screen
    plain frame   781.6s -> 799.7s  — 18.1s of charcoal and one logo
    total         799.7s

and on EP49's rejected cut:

    end card in   852.5s   — 24.5s AFTER the e-book line at 827.9s
    warranty      858.5s -> 862.0s — 3.5s on screen
    plain frame   none
    total         862.0s

⚠️ AND THE OBVIOUS DIAGNOSIS WAS WRONG BOTH TIMES. The warranty is not short because a
hard-coded 3.5 overrode the clip's own duration: `warranty-slide.mp4` is **1.700s**,
SHORTER than 3.5, so taking the duration from the clip would have made it worse. And
the 39.4s of EP48 tail is not 39.4s of end card — it is 12.1s of end card, 9.2s of
warranty and 18.1s of a plain frame that nothing in the two-way path appended. **A
number that is true about the wrong quantity is a wrong answer.**

── WHAT IT OWNS ──────────────────────────────────────────────────────────────────────
· where the three STANDING GRAPHICS go — the early e-book card, the like-and-subscribe
  chip, the end card — each placed from the merged SRT by an anchor phrase, never typed
· the tail arithmetic, taken from `assemble_episode`'s own defaults and not re-invented
· the checks: a furniture beat that has a standing graphic MUST get it; the end card
  must be on screen while the e-book line is spoken

🔴 DERIVED, NEVER TYPED. `at` is measured off `renders/merged.srt` every build. EP18's
first attempt hard-coded 48.6 and it was wrong twice over — wrong clock and a number
nobody could re-check. The anchor PHRASE is the authored thing; the second is derived
from it, and if the words change the build halts instead of placing the card on the
wrong sentence.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import derive_card_timings as dct                                 # noqa: E402
import ep_paths                                                   # noqa: E402

# 🔴 EVERY NUMBER BELOW IS `assemble_episode.py`'s, NOT A NEW ONE. They are the defaults
# forty-two published episodes were built with; they are named here so the two-way can
# obey them, and they are NOT re-tuned. The three follow-delays come in by import from
# `derive_card_timings`, which is their one home — copying them would make two rules
# out of one the day either moves (§2b).
WARRANTY_LEAD_S = 0.3
"""`assemble_episode` B.get("warranty_lead", 0.3) — the warranty slide comes up this
long after the last word. NOT the settle: the settle is room in the TOTAL, below."""

WARRANTY_TAIL_S = 6.7
"""`assemble_episode` B.get("warranty_tail", 6.7). With END_SETTLE_S this is the whole
length of the film after the last word, so the warranty holds
`END_SETTLE_S + WARRANTY_TAIL_S - WARRANTY_LEAD_S` = 9.4s. EP48 measures 9.2s."""

ENDCARD_LEAD_S = 1.5
"""`assemble_episode` B.get("endcard_lead", 1.5) — the end card enters this long after
the e-book beat begins, exactly as the single-presenter pipeline builds it."""

ENDCARD_FADE_S = 0.3
ENDCARD_HANDOVER_S = 0.6
"""How far the end card runs PAST the warranty's entrance before it is gone. It is
`assemble_episode`'s own `(SPEECH_END + warranty_lead + 0.6) - ec_ti`: the two slides
cross rather than one leaving a hole. Measured on EP48 as a dip at 772.5-773.5s."""

EARLY_CTA_DUR_S = 6.0
EARLY_CTA_FADE_S = 0.3
MIDROLL_FADE_S = 0.4
MIDROLL_ASK_TAIL_S = 1.2
"""`derive_card_timings`' own `a1_end = a1 + 1.2` — let the closing phrase finish
before the chip goes."""

END_FRAME_S = 18.0
"""The plain charcoal frame YouTube's end-screen boxes sit on. `end_frame.py` owns it;
the number is repeated here only so the PLAN can say the tail is long enough before a
frame is rendered. `qc_episode.py` HARD-FAILS below `end_frame.MIN_SECONDS` (15s)."""

STANDING = {
    "open":    {"clip": None,                     "what": "the who-you-are-hearing card",
                "build_key": "open_card"},
    "cta":     {"clip": "end-card-template.mp4",  "what": "the early e-book card",
                "build_key": "early_cta"},
    "midroll": {"clip": "midroll-lowerthird.mp4", "what": "the like-and-subscribe chip",
                "build_key": "midroll"},
    "outro":   {"clip": "end-card-template.mp4",  "what": "the end card",
                "build_key": "end_card"},
}
"""🔴 WHICH FURNITURE BEATS OWE A GRAPHIC, KEYED ON THE BEAT'S ROLE AND NOT ITS NAME.

`twoway_furniture` gives every piece a stable role — open, cta, midroll, close, outro,
rg, signoff — while the NAME carries the episode ("midroll invitation L9"). Keying on
the name would break the day a pool line changed.

⚠️ THIS TABLE IS THE CHECK. Three cuts of EP49 shipped with a `cta` beat and a `midroll`
beat and nothing over either of them, and nothing said so, because no code anywhere knew
that those beats are supposed to carry a picture. A missing graphic is invisible; a
missing ROW is not.

📌 `clip: None` means the asset is the EPISODE'S, not the channel's, and `build.<key>.
clip` must name it. The open card is per-episode by nature — it prints these two
readers and these two authors — while the other three are copied byte-identical into
every folder. The mechanism is standing either way, which is the whole point of the
row existing."""
"""🔴 WHICH FURNITURE BEATS OWE A GRAPHIC, KEYED ON THE BEAT'S ROLE AND NOT ITS NAME.

`twoway_furniture` gives every piece a stable role — open, cta, midroll, close, outro,
rg, signoff — while the NAME carries the episode ("midroll invitation L9"). Keying on
the name would break the day a pool line changed.

⚠️ THIS TABLE IS THE CHECK. Three cuts of EP49 shipped with a `cta` beat and a `midroll`
beat and nothing over either of them, and nothing said so, because no code anywhere
knew that those beats are supposed to carry a picture. A missing graphic is invisible;
a missing ROW is not."""


class Unplaceable(Exception):
    """A standing graphic cannot be placed. Nothing is rendered."""


def _card_columns(page: pathlib.Path) -> list[dict]:
    """The CONTENT of a bespoke card, read off its own page.

    🔴 SO THE HOLD CANNOT DRIFT FROM WHAT IS PRINTED. `card_hold.hold_for` needs the
    words the viewer has to read; transcribing them into `episode.json` would make two
    descriptions of one card, and the page is the one on screen. Only the columns are
    taken — the eyebrow and the headline are signposts read in a glance on the way in,
    which is card_hold's own rule and why it excludes them.
    """
    from html.parser import HTMLParser

    class Cols(HTMLParser):
        def __init__(self):
            super().__init__()
            self.depth = 0
            self.cols: list[dict] = []
            self.key = None

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            cls = (a.get("class") or "").split()
            if "col" in cls and self.depth == 0:
                self.depth = 1
                self.cols.append({})
            elif self.depth:
                self.depth += 1
                self.key = next((c for c in cls
                                 if c in ("reader", "verb", "who", "role")), None)

        def handle_endtag(self, tag):
            if self.depth:
                self.depth -= 1

        def handle_data(self, data):
            if self.depth and self.key and data.strip():
                self.cols[-1][self.key] = (
                    self.cols[-1].get(self.key, "") + " " + data.strip()).strip()
                self.key = None

    if not page.is_file():
        raise Unplaceable(
            f"{page.name} is not beside the clip, so the card's own words cannot be "
            f"read and its reading hold cannot be computed. A hold typed instead of "
            f"computed is a hold nobody can re-check.")
    p = Cols()
    p.feed(page.read_text(encoding="utf-8"))
    if not p.cols:
        raise Unplaceable(
            f"{page.name} has no `.col` content to measure, so there is nothing to "
            f"compute a reading hold from.")
    return p.cols


def _spoken_at(tl, phrase: str, what: str, where: str) -> float:
    at = dct.find_phrase(tl, phrase)
    if at is None:
        raise Unplaceable(
            f"{what}: the anchor {phrase!r} is not in renders/merged.srt, so {where} "
            f"cannot be placed. Either the wording of that line changed or this is the "
            f"wrong master — and both need a human. NOT GUESSING: a graphic placed on "
            f"the wrong sentence is worse than one that is missing, because it looks "
            f"deliberate.")
    return at


def place(d: pathlib.Path, epj: dict, cues, furniture: list[dict],
          head_s: float) -> dict:
    """Where the three standing graphics go, on the FINISHED clock.

    `cues` and `furniture` are on the DIALOGUE clock (t=0 at the first word); every
    time returned here has `head_s` added, because the finished file puts the title
    card in front of them. That conversion happens once, here — CLAUDE.md fault 1b is
    two clocks and a number that crossed between them without saying so.
    """
    B = epj.get("build") or {}
    clips = d / "overlay/clips"
    tl = dct.word_timeline([(c["start"], c["end"], c["text"]) for c in cues])
    by_role = {f["furniture"]: f for f in furniture if f.get("furniture")}
    out: dict = {"placed": [], "owed": sorted(r for r in STANDING if r in by_role)}

    for role in out["owed"]:
        if not STANDING[role]["clip"]:
            continue                      # the episode's own asset — checked in place
        clip = clips / STANDING[role]["clip"]
        if not clip.is_file():
            raise Unplaceable(
                f"the {role} beat is in this episode and {STANDING[role]['clip']} is "
                f"not in overlay/clips. {STANDING[role]['what'].capitalize()} is "
                f"standing furniture — it is copied byte-identical into every episode, "
                f"and a beat that owes one and has none is a hole nobody can see.")

    # ── the who-you-are-hearing card, over the OPEN ──────────────────────────
    #
    # 🔴 WHY THE OPEN GETS A CARD AND NOT THE CHIPS. Jodie asked whether the "reading …"
    # chips appear over the opening. They do not, and they must not: the chips are
    # two-box furniture, and during the open Gordon speaks AS HIMSELF (build spec A1) —
    # so a "reading Brian Blackwell" chip under him would be FALSE at that moment. The
    # open gets its own card instead, which also covers the weakest stretch on screen:
    # thirty-five seconds of one man alone.
    #
    # It is FURNITURE, not a conversation card. It never enters the C1-C15 accounting,
    # never moves the placed count, never touches the layout plan — it lives in
    # `graphics`, like the other three, and `plan["segments"]` does not know it exists.
    oc = dict(B.get("open_card") or {})
    if "open" in by_role:
        anchor = str(oc.get("anchor") or "").strip()
        if not anchor:
            raise Unplaceable(
                "this episode has an `open` furniture beat and `build.open_card.anchor` "
                "is not set. It must quote the line the card belongs on, verbatim.")
        clip = clips / str(oc.get("clip") or "")
        if not oc.get("clip") or not clip.is_file():
            raise Unplaceable(
                f"the open beat owes {STANDING['open']['what']} and "
                f"{oc.get('clip') or 'build.open_card.clip'} is not in overlay/clips. "
                f"This card is the EPISODE'S, not the channel's — it prints these two "
                f"readers and these two authors — so unlike the other three there is "
                f"no standing file to fall back on.")
        o0 = _spoken_at(tl, anchor, "open_card", "the who-you-are-hearing card")
        # 🔴 THE HOLD IS COMPUTED FROM THE CARD'S OWN WORDS, NEVER TYPED. `card_hold`
        # owns that rule for every other card in the channel and it owns it here:
        # the larger of the item floor and the reading time, and a card is NEVER sped
        # up to fit. The words are read off the PAGE, so the hold cannot drift from
        # what is actually printed on it (§7 — derive the coverage from the thing).
        import card_hold as ch
        card = {"block": "bespoke", "content": {"cols": _card_columns(
            d / "overlay/export" / (clip.stem + ".html"))}}
        hold = ch.hold_for(card, B)
        asked = float(oc.get("dur") or 0.0)
        dur = round(max(hold, asked), 2)
        fade = float(oc.get("fade", EARLY_CTA_FADE_S))
        at = round(o0 + dct.EARLY_FOLLOW + head_s, 3)
        beat = by_role["open"]
        lo, hi = beat["from_s"] + head_s, beat["to_s"] + head_s
        if not (lo - 0.01 <= at and at + dur <= hi + 0.01):
            raise Unplaceable(
                f"the who-you-are-hearing card would run {at:.2f}-{at + dur:.2f}s and "
                f"the open is {lo:.2f}-{hi:.2f}s. The card belongs inside the open it "
                f"explains, and it is never shortened to fit — that is card_hold's "
                f"ruling, not a preference.")
        out["open_card"] = {
            "clip": str(clip), "at_s": at, "dur_s": dur, "fade_s": fade,
            "anchor": anchor, "spoken_at_s": round(o0 + head_s, 3),
            "beat": [round(lo, 3), round(hi, 3)], "full_frame": True,
            "hold_asked_s": asked, "hold_computed_s": hold,
            "content_words": ch.content_words(card),
        }
        out["placed"].append("open")

    # ── the early e-book card — the SAME card the end uses, over the spoken mention ──
    cta = dict(B.get("early_cta") or {})
    if "cta" in by_role:
        anchor = str(cta.get("anchor") or "").strip()
        if not anchor:
            raise Unplaceable(
                "this episode has an `cta` furniture beat and `build.early_cta.anchor` "
                "is not set. It must quote the opening words of the early "
                "companion-guide mention, verbatim, so the card is placed from the SRT "
                "instead of a typed timestamp.")
        c0 = _spoken_at(tl, anchor, "early_cta", "the early e-book card")
        dur = float(cta.get("dur", EARLY_CTA_DUR_S))
        fade = float(cta.get("fade", EARLY_CTA_FADE_S))
        at = round(c0 + dct.EARLY_FOLLOW + head_s, 3)
        beat = by_role["cta"]
        lo, hi = beat["from_s"] + head_s, beat["to_s"] + head_s
        if not (lo - 0.01 <= at and at + dur <= hi + 0.01):
            raise Unplaceable(
                f"the early e-book card would run {at:.2f}-{at + dur:.2f}s and its own "
                f"furniture beat is {lo:.2f}-{hi:.2f}s. The card belongs INSIDE the "
                f"beat that speaks it; outside it, it lands over the conversation.")
        out["early_cta"] = {
            "clip": str(clips / str(cta.get("clip") or STANDING["cta"]["clip"])),
            "at_s": at, "dur_s": round(dur, 3), "fade_s": fade,
            "anchor": anchor, "spoken_at_s": round(c0 + head_s, 3),
            "beat": [round(lo, 3), round(hi, 3)], "full_frame": True,
        }
        out["placed"].append("cta")

    # ── the like-and-subscribe chip — FOLLOWS the ask, never precedes or spans it ──
    mid = dict(B.get("midroll") or {})
    if "midroll" in by_role:
        ask = mid.get("ask")
        if not ask or len(ask) < 2 or not all(str(x).strip() for x in ask[:2]):
            raise Unplaceable(
                "this episode has a `midroll` furniture beat and `build.midroll.ask` "
                "is not set. It must quote THIS episode's pool line "
                "(docs/midroll-line-pool.md) — the first phrase of the ask and the "
                "last, verbatim. There is deliberately no default: the previous one "
                "was EP12's words, and a chip anchored to another episode's sentence "
                "is worse than no chip.")
        a0 = _spoken_at(tl, ask[0], "midroll", "the like-and-subscribe chip")
        a1 = _spoken_at(tl, ask[1], "midroll", "the like-and-subscribe chip")
        fade = float(mid.get("fade", MIDROLL_FADE_S))
        at = round(a0 + dct.MIDROLL_FOLLOW + head_s, 3)
        # 🔴 THE LENGTH IS SIZED TO THIS EPISODE'S ASK, NEVER COPIED. EP48's 13.0s was
        # thirty-four words of EP48's L8. Deriving it from the ask's own end means a
        # shorter pool line cannot leave the chip hanging over the return to content.
        end = round(a1 + MIDROLL_ASK_TAIL_S + head_s, 3)
        dur = round(max(end - at, 0.0), 3)
        full = round(dur - 2 * fade, 3)
        if full < dct.MIDROLL_MIN_FULL:
            raise Unplaceable(
                f"the chip would be fully visible for {full:.2f}s and §4E asks for "
                f"{dct.MIDROLL_MIN_FULL:.0f}s. The ask runs {a0:.2f}-{a1:.2f}s on the "
                f"dialogue clock; either the anchors are not the ask's real ends or "
                f"this pool line is too short to carry the chip.")
        beat = by_role["midroll"]
        lo, hi = beat["from_s"] + head_s, beat["to_s"] + head_s
        if not (lo - 0.01 <= at and at + dur <= hi + 0.01):
            raise Unplaceable(
                f"the chip would run {at:.2f}-{at + dur:.2f}s and the midroll beat is "
                f"{lo:.2f}-{hi:.2f}s. The chip belongs inside the invitation it "
                f"illustrates.")
        out["midroll"] = {
            "clip": str(clips / str(mid.get("clip") or STANDING["midroll"]["clip"])),
            "at_s": at, "dur_s": dur, "fade_s": fade, "ask": list(ask[:2]),
            "spoken_at_s": round(a0 + head_s, 3),
            "ask_ends_at_s": round(a1 + head_s, 3),
            "beat": [round(lo, 3), round(hi, 3)],
            "chromakey": True, "full_frame": False,
        }
        out["placed"].append("midroll")

    # ── the end card — ON THE E-BOOK BEAT, and it stays until the warranty ──
    ec = dict(B.get("end_card") or {})
    if "outro" in by_role:
        anchor = str(ec.get("anchor") or "").strip()
        if not anchor:
            raise Unplaceable(
                "this episode has an `outro` furniture beat and `build.end_card.anchor` "
                "is not set. It must quote the outro's e-book pointer verbatim — "
                "§END SEQUENCE rule 2 places the end card ON that line, and a beat "
                "number cannot say where inside a thirty-second outro it falls.")
        e0 = _spoken_at(tl, anchor, "end_card", "the end card")
        out["end_card_at_s"] = round(e0 + float(ec.get("lead", ENDCARD_LEAD_S))
                                     + head_s, 3)
        out["ebook_line_at_s"] = round(e0 + head_s, 3)
        out["placed"].append("outro")
    return out


def tail(speech_end_s: float, end_card_at_s: float | None,
         end_settle_s: float) -> dict:
    """The ending, built the way `assemble_episode` builds it. 🔴 NOT A NEW SHAPE.

    The end card is already up — it went up on the e-book beat, while he was still
    talking — so there is no 'settle then card then warranty' sequence to lay out.
    What happens after the last word is: the warranty takes over 0.3s later, and the
    film runs `end_settle + warranty_tail` seconds in total. That is the shape of every
    published episode.
    """
    warranty_at = round(speech_end_s + WARRANTY_LEAD_S, 3)
    total = round(speech_end_s + end_settle_s + WARRANTY_TAIL_S, 3)
    out = {
        "warranty": {"from_s": warranty_at,
                     "dur_s": round(total - warranty_at, 3)},
        "end_card": None,
        "total_s": total,
    }
    if end_card_at_s is not None:
        out["end_card"] = {
            "from_s": round(end_card_at_s, 3),
            "dur_s": round(warranty_at + ENDCARD_HANDOVER_S - end_card_at_s, 3),
            "fade_s": ENDCARD_FADE_S,
            "overlay": True,
        }
    return out


# ────────────────────────────────────────────────────────────────── checks ──

def violations(plan: dict) -> list[str]:
    """The end-sequence faults Jodie stopped the 20 Sep cut for. Reported, not fixed."""
    out = []
    g = plan.get("graphics") or {}
    speech_end = plan["speech_end_s"]

    # 1 — A FURNITURE BEAT WITH A STANDING GRAPHIC MUST GET IT.
    for role in g.get("owed", []):
        if role not in g.get("placed", []):
            out.append(
                f"STANDING GRAPHIC MISSING: the {role} beat is in this episode and "
                f"{STANDING[role]['what']} was not placed over it. Every furniture "
                f"beat in the table owes one.")

    # 2 — §END SEQUENCE RULE 2: the end card is ON SCREEN while he speaks the e-book
    #     line. Not near it, not after it — over it.
    ec = plan.get("end_card")
    line = g.get("ebook_line_at_s")
    if ec and line is not None:
        if ec["from_s"] > line + ENDCARD_LEAD_S + 0.5:
            out.append(
                f"END CARD LATE: it fades in at {ec['from_s']:.1f}s and the e-book line "
                f"is spoken at {line:.1f}s — {ec['from_s'] - line:.1f}s after. "
                f"§END SEQUENCE rule 2: it fades in ON the e-book beat and stays up "
                f"until the warranty takes over.")
        if ec["from_s"] >= speech_end:
            out.append(
                f"END CARD AFTER THE LAST WORD: it fades in at {ec['from_s']:.1f}s and "
                f"the last word is at {speech_end:.1f}s. Rule 2 says it must be on "
                f"screen WHILE Gordon speaks the e-book line — never come-and-go early, "
                f"and never arrive when there is nothing left to say.")
        if ec["from_s"] + ec["dur_s"] < plan["warranty"]["from_s"]:
            out.append(
                f"END CARD LEAVES EARLY: it is gone at "
                f"{ec['from_s'] + ec['dur_s']:.1f}s and the warranty does not arrive "
                f"until {plan['warranty']['from_s']:.1f}s. Rule 2: it stays up until "
                f"the warranty takes over.")

    # 3 — THE WARRANTY'S HOLD COMES FROM THE TAIL, AND IT IS NOT THREE AND A HALF
    #     SECONDS. EP48 holds it 9.2s.
    w = plan["warranty"]
    if w["dur_s"] < 6.0:
        out.append(
            f"WARRANTY TOO SHORT: {w['dur_s']:.1f}s on screen. The tail is "
            f"end_settle + warranty_tail after the last word, which is "
            f"{plan.get('end_settle_s', 3.0) + WARRANTY_TAIL_S - WARRANTY_LEAD_S:.1f}s "
            f"— EP48 measures 9.2s.")

    # 3b — A STANDING CLIP'S HOLD COMES FROM THE CLIP, NOT FROM A CONSTANT.
    #
    # ⚠️ AND THIS IS THE CHECK THAT WOULD NOT HAVE CAUGHT THE WARRANTY, SAID OUT LOUD.
    # `warranty-slide.mp4` is 1.700s and the old hold was 3.5s, so the clip DID finish;
    # the fault was the shape of the tail, not the arithmetic on one asset. The check is
    # still worth having — it is what catches an asset that grows — but a check written
    # against a hypothesis that turned out to be wrong must say so, or the next reader
    # will believe it covers something it does not.
    for name, hold in (("warranty-slide.mp4", w["dur_s"]),
                       ("end-card-template.mp4", (ec or {}).get("dur_s")),
                       ("midroll-lowerthird.mp4",
                        ((g.get("midroll") or {}).get("dur_s"))),
                       ("end-card-template.mp4",
                        ((g.get("early_cta") or {}).get("dur_s")))):
        if hold is None:
            continue
        clip = plan.get("clip_durations", {}).get(name)
        if clip is not None and hold + 0.05 < clip:
            out.append(
                f"STANDING CLIP CUT OFF: {name} runs {clip:.2f}s and is on screen "
                f"{hold:.2f}s. The hold is taken from the asset, never from a number "
                f"beside it — the viewer never sees it finish.")

    # 4 — ROOM FOR YOUTUBE'S END SCREEN, WITHOUT COVERING THE SUPPORT NUMBER.
    if not plan.get("end_frame_s"):
        out.append(
            "NO PLAIN END FRAME: nothing follows the warranty slide, so YouTube's "
            "end-screen boxes land on the responsible-gambling text and the 1800 858 "
            "858 support line. `end_frame.py` appends 18s of charcoal and one logo for "
            "exactly this reason, and qc_episode HARD-FAILS below 15s.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default="G:/My Drive/PP Videos")
    a = ap.parse_args()
    import twoway_assemble as ta
    plan = ta.build_plan(a.ep_number, pathlib.Path(a.pp))
    g = plan["graphics"]
    print(f"owed   : {g['owed']}")
    print(f"placed : {g['placed']}")
    for k in ("early_cta", "midroll"):
        if g.get(k):
            v = g[k]
            print(f"  {k:10s} {v['at_s']:8.2f}s +{v['dur_s']:.2f}s "
                  f"(spoken {v['spoken_at_s']:.2f}s)")
    print(f"  end card   {plan['end_card']['from_s']:8.2f}s "
          f"+{plan['end_card']['dur_s']:.2f}s "
          f"(e-book line {g['ebook_line_at_s']:.2f}s)")
    print(f"  warranty   {plan['warranty']['from_s']:8.2f}s "
          f"+{plan['warranty']['dur_s']:.2f}s")
    print(f"  total      {plan['total_s']:8.2f}s + {plan.get('end_frame_s', 0):.0f}s "
          f"plain end frame")
    v = violations(plan)
    print(f"\n{len(v)} violation(s)" if v else "\n\u2705 no end-sequence violations")
    for x in v:
        print("  ! " + x)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Unplaceable as e:
        print(f"\nHALT: {e}", file=sys.stderr)
        raise SystemExit(2)
