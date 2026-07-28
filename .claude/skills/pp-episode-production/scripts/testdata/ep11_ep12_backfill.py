#!/usr/bin/env python3
"""Back-fill block/content/trace onto EP11's and EP12's cards.

EVERY value below was EXTRACTED by reading the shipped hand-authored page. None
was inferred, tidied, or adjusted to make a template fit. Where a card's content
could not be expressed in one of the eleven agreed blocks without inventing
something, it is marked block:"bespoke" — that is a finding, not a failure.

verify() re-reads the shipped HTML afterwards and asserts every string here
actually occurs in it, so a transcription slip of mine cannot pass silently.
"""
import html
import json
import re
import sys
import unicodedata

Q = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = "".join(Q.get(c, c) for c in s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- EP11
EP11 = {
 "C1": dict(page="ep11-c01-prejudices.html", block="chips",
   fit={"headline_size": "104px", "headline_leading": "0.94", "headline_top": "24px"},
   content={
     "chips": [{"label": "wide barriers", "tone": ""},
               {"label": "a trainer", "tone": ""},
               {"label": "a jockey", "tone": ""},
               {"label": "anything over 10/1", "tone": "last"}],
     "foot": "— and that’s a horse you <b>never even looked at</b>"},
   trace={"chips": "We have a 'thing' about wide barriers, or maybe have always thought "
                   "that any horse over 10/1 is not worth looking at."}),

 "C2": dict(page="ep11-c02-see-each-horse.html", block="checklist",
   headline_display="See Each Horse<br>as an Individual",
   fit={"headline_size": "92px", "headline_leading": "0.94", "headline_top": "24px",
        "list_top": "54px", "item_gap": "38px"},
   content={"items": ["What are its claims to the race?",
                      "Has it recent form that lays a viable claim?",
                      "Is there a race you can relate to this one?"]},
   trace={}),

 "C5": dict(page="ep11-c05-turridu-12-1.html", block="price",
   fit={"headline_size": "130px", "headline_leading": "0.94", "headline_top": "22px",
        "quote_top": "26px"},
   content={
     "quote": "“more or less neglected in the pre-race summaries and in the betting”",
     "price": "12/1",
     "said": "a top chance —<br><b>a better one than his odds indicated</b>"},
   trace={"price": "He was sent out at 12/1."}),
}
# Everything else in EP11 is hand-authored. Reasons in BESPOKE_WHY below.
for cid in ("C3", "C4", "C6", "C7", "C8", "C9", "C10", "C11", "C12"):
    EP11[cid] = dict(block="bespoke")

# ---------------------------------------------------------------- EP12
EP12 = {
 "C1": dict(page="ep12-c01-most-of-them-lose.html", block="stat",
   fit={"headline_size": "104px", "headline_leading": "0.96", "headline_top": "24px"},
   content={"figure": "60 Days+", "figure_sub": "Resuming from a spell",
            "payoff": "Most will lose at their first run back.",
            "note": "“That’s an iron-clad fact.”"},
   trace={"figure": "Most horses resuming from a spell - say 60 days or more - will lose "
                    "at their first run back."}),

 "C2": dict(page="ep12-c02-the-first-up-line.html", block="slots",
   fit={"headline_size": "96px", "headline_leading": "0.94", "headline_top": "24px"},
   content={"tag": "First-up",
            # THE NULL CASE. The article names both columns and gives no figures.
            # Explicit null draws the dotted rule and records that a human decided
            # it is empty. Do not "fill these in" later.
            "slots": [{"k": "Wins first-up", "v": None},
                      {"k": "Placings", "v": None}],
            "said": "Years ago we didn’t have this. <b>Now we do.</b>",
            "chips": ["Best Bets"]},
   trace={}),

 "C3": dict(page="ep12-c03-90-days-is-not-180-days.html", block="bars",
   fit={"headline_size": "104px", "headline_leading": "0.96", "headline_top": "24px"},
   content={"bars": [{"label": "90 Days", "value": "90", "note": "won fresh off this",
                      "tone": "hi"},
                     {"label": "180 Days", "value": "180", "note": "back off this",
                      "tone": ""}],
            "ask": "Does the old form still count?",
            "chip": "The Wizard · days since last start"},
   trace={"bars": "A horse may have won fresh before after a spell of, say, 90 days. "
                  "But he may now be returning after being out for 180 days.",
          "headline": "A horse may have won fresh before after a spell of, say, 90 days. "
                      "But he may now be returning after being out for 180 days."}),

 "C4": dict(page="ep12-c04-it-depends-who-he-is-beating.html", block="compare",
   headline_display="It Depends Who<br>He Is Beating",
   fit={"headline_size": "88px", "headline_leading": "0.96", "headline_top": "24px"},
   content={"cols": [{"tone": "yes", "k": "Can win fresh", "v": "Class 1 and 2 company"},
                     {"tone": "no", "k": "Just cannot do it", "v": "Class 6 or Welter fields"}],
            "note": "Check the class he won fresh in — then look at the class of today’s race."},
   trace={"cols": "A horse coming through the grades might be able to win first-up against, "
                  "say, Class 1 and 2 company - but later when he has to race fresh against "
                  "Class 6 or Welter fields he just cannot do it."}),

 "C6": dict(page="ep12-c06-the-first-up-checklist.html", block="checklist",
   fit={"headline_size": "92px", "headline_leading": "0.94", "headline_top": "24px"},
   content={"items": ["How many times has it won first-up?",
                      "Is it capable of repeating the performance?",
                      "What weight did it carry then — and what now?",
                      "Is there a clue in the track gallops?"]},
   trace={}),

 "C8": dict(page="ep12-c08-class-carries-them-through.html", block="statement",
   headline_display="Class Carries<br>Them Through",
   fit={"headline_size": "92px", "headline_leading": "0.94", "headline_top": "24px"},
   content={"line": "They can win with <b>no first-up form at all</b> — if they are the "
                    "class horse of the race.",
            "note": "This is the exception worth hunting."},
   trace={}),

 "C9": dict(page="ep12-c09-joie-denise.html", block="slate",
   fit={"headline_size": "150px", "headline_leading": "0.94", "headline_top": "20px",
        "eyebrow_size": "36px", "eyebrow_tracking": "0.20em"},
   content={"cells": [{"k": "The race", "v": "1400m", "sub": "Handicap, fillies and mares"},
                      {"k": "Her weight", "v": "57kg", "sub": "Top weight, on a 51kg limit"},
                      {"k": "First-up record", "v": "Failed twice",
                       "sub": "Not even running placings"}],
            "warn": "On the face of it, unbackable."},
   trace={"cells": "A recent instance of this was joie Denise's first-up win at Randwick "
                   "(1400m) in August. She was in a handicap for fillies and mares and had "
                   "top weight of 57kg (on a 51kg Limit)."}),

 "C10": dict(page="ep12-c10-down-in-class.html", block="steps",
   fit={"headline_size": "104px", "headline_leading": "0.96", "headline_top": "20px",
        "eyebrow_size": "36px", "eyebrow_tracking": "0.20em"},
   content={"steps": [{"k": "Queensland Oaks", "v": "Won — in race record time"},
                      {"k": "Queensland Derby", "v": "10 June — 5th, beaten 3.3 lengths"},
                      {"k": "Today", "v": "A handicap for fillies and mares"}],
            "note": "The second mare in the handicap, Castle Song, had failed in a Sydney "
                    "Welter last start."},
   trace={"steps": "Her most recent start, back on June 10, was a 3.3 lengths 5th in the "
                   "Queensland Derby, and before that she had won the Queensland Oaks in "
                   "race record time."}),

 "C11": dict(page="ep12-c11-10-1.html", block="price",
   fit={"headline_size": "126px", "headline_leading": "0.94", "headline_top": "22px",
        "quote_top": "24px"},
   content={"quote": "“won careering away with a tremendous final burst”",
            "price": "10/1",
            "said": "a quality galloper resuming —<br><b>a few classes above the "
                    "opposition</b>"},
   trace={"price": "Joie Denise was sent out at 10/1 and won careering away with a "
                   "tremendous final burst."}),

 "C12": dict(page="ep12-c12-nine-out-of-ten.html", block="ratio",
   fit={"headline_size": "92px", "headline_leading": "0.96", "headline_top": "22px"},
   content={"marks": [{"tone": ""}] * 9 + [{"tone": "win"}],
            "payoff": "But then comes <b>the horse and the race</b> when the answer is yes."},
   trace={}),
}
for cid in ("C5", "C7"):
    EP12[cid] = dict(block="bespoke")

BESPOKE_WHY = {
 ("EP11", "C3"): "hero figure + an odds plaque + two summary cards — the `stat` block has a "
                 "figure/sub/payoff/note stack and no plaque and no card pair",
 ("EP11", "C4"): "a COLUMN of key/value rows; the `slate` block is a ROW of stacked cells. "
                 "Different shape, not a fit variant. Candidate new block: `rows`",
 ("EP11", "C6"): "hand-placed race lane — turf, winning post, two runners and a margin "
                 "bracket, all positioned by absolute offsets",
 ("EP11", "C7"): "list of beaten horses with a neutral marker and a callout tag. Candidate "
                 "new block: `namelist`. NOTE: this is the card whose invented placings "
                 "started the trace rule",
 ("EP11", "C8"): "horizontal timeline with an absolutely-positioned spine",
 ("EP11", "C9"): "price treatment AND a four-cell slate on one card; `price` has no cell row",
 ("EP11", "C10"): "then/now pair of multi-row panels with a linking arrow and pulsing "
                  "matches; `compare` is two mark/key/value columns. Candidate: `versus`",
 ("EP11", "C11"): "magnifier sweeping a clue strip, with a 9999px vignette",
 ("EP11", "C12"): "an arithmetic line (2 × 14 = 28 × 5) then a payoff pair — unique",
 ("EP12", "C5"): "hand-placed ink rings over abstract runner rows, two colours, offset "
                 "and rotated per ring",
 ("EP12", "C7"): "distance ruler whose tick positions are NOT a linear scale",
}


def scrape(page, sel_id):
    """Lift an element's inner HTML straight out of the shipped page.

    Used for the headline and the eyebrow so those two are EXTRACTED rather than
    retyped. It also surfaces drift: EP12's episode.json records C11's headline
    as "10/1" while the shipped card's headline is "Joie Denise" and 10/1 is the
    price. The card is what shipped, so the card is what we take.
    """
    t = open(page, encoding="utf-8").read()
    m = re.search(r'id="%s"[^>]*>(.*?)</div>' % sel_id, t, re.S)
    return html.unescape(m.group(1)).strip() if m else None


def apply(path, table, tag, export_dir):
    ep = json.load(open(path, encoding="utf-8"))
    n = 0
    for c in ep["cards"]:
        add = table.get(c["id"])
        if not add:
            continue
        for k, v in add.items():
            c[k] = v
        if add["block"] != "bespoke":
            page = f"{export_dir}/{add['page']}"
            c["headline_display"] = scrape(page, "hl")
            c["eyebrow"] = scrape(page, "eyb")
        n += 1
    json.dump(ep, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{tag}: annotated {n} cards")
    return ep


def verify(ep, table, export_dir, tag):
    """Every extracted string must occur in the shipped page it came from."""
    bad = 0
    for c in ep["cards"]:
        add = table.get(c["id"])
        if not add or add["block"] == "bespoke":
            continue
        shipped = norm(html.unescape(open(f"{export_dir}/{add['page']}", encoding="utf-8").read()))
        vals = []

        def collect(o):
            if isinstance(o, str):
                vals.append(o)
            elif isinstance(o, dict):
                [collect(v) for v in o.values()]
            elif isinstance(o, list):
                [collect(v) for v in o]
        collect(add["content"])
        for v in vals:
            plain = norm(re.sub(r"</?b>|<br>", " ", v))
            if plain and plain not in shipped:
                # a <br>/<b> split means the halves must each be present
                halves = [norm(x) for x in re.split(r"</?b>|<br>", v) if norm(x)]
                if all(h in shipped for h in halves):
                    continue
                print(f"  ✗ {tag} {c['id']}: NOT IN THE SHIPPED PAGE: {v!r}")
                bad += 1
    print(f"{tag}: verification {'FAILED' if bad else 'clean'} ({bad} mismatch)")
    return bad


TABLES = {"EP11": EP11, "EP12": EP12}


def run(work):
    """Annotate the episode.json COPIES under `work` and verify against the pages."""
    bad = 0
    for tag, table in TABLES.items():
        p = f"{work}/PP-{tag}/docs/episode.json"
        exp = f"{work}/PP-{tag}/overlay/export"
        ep = apply(p, table, tag, exp)
        bad += verify(ep, table, exp, tag)
    return bad


if __name__ == "__main__":
    bad = run(sys.argv[1] if len(sys.argv) > 1 else ".")
    print("\nBESPOKE, and why:")
    for (e, c), why in BESPOKE_WHY.items():
        print(f"  {e} {c}: {why}")
    sys.exit(1 if bad else 0)
