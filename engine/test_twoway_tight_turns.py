"""build.tight_turns — a PER-EPISODE override (EP56, Jodie 12 Nov 2026), and the mapping it needs.

Jodie: in turns 8, 11 and 12 ONLY, let graphics sit closer than the 5-second gap; keep every other
rule — the dwell floor included. So "closer" can only mean a BUTT JOIN: the next graphic follows
with no shot between, the previous one lengthened to meet it (a card always may; a clip only up to
its real length), and a clip may be used shorter (never under 8s) to fit before the handover.

  (a) in a tight turn a clip butts onto the card before it; the card is lengthened; no short state
  (b) CONTROL: the same turn NOT listed keeps the 5s gap (the clip lands >= 5s later or is dropped)
  (c) a clip is never lengthened past its own length (clip_s) to meet the next graphic
  (d) a clip may be used shorter to fit before the handover, never under 8s
  (e) map_layout holds a card on to meet a butting graphic; a HOLE is a violation (control)
  (f) turn_open_entry: a turn-open CARD maps to lo + 5s mid-sentence (Jodie, 20 Sep); a clip does not
  (g) EP49 / EP55 / no override: plans unchanged

Run: python engine/test_twoway_tight_turns.py
"""
import copy
import glob
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import twoway_assemble as ta  # noqa: E402
import twoway_beats as tb  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def words(n, tag):
    return " ".join([tag] + ["word"] * (n - 2) + ["end."])


def beat(n, turn, spk, sents, card=None, broll=None):
    line = " ".join(sents)
    return {"n": n, "turn": turn, "speaker": spk, "line": line, "est_s": round(len(line.split()) / 2.6, 2),
            "card": card, "broll": broll, "para_in_turn": 1, "paras_in_turn": 1}


# turn 1: Steve, short. turn 2: Gordon — a card on beat 2, a clip on beat 3 whose first sentence starts
# ~1.9s after the card's 10s hold ends (the shape that made EP56's turns 11 and 12 drop a clip).
B2 = [words(13, "alpha"), words(13, "bravo"), words(18, "charlie")]
B3 = [words(13, "delta"), words(13, "echo"), words(13, "foxtrot"), words(13, "golf")]


def shape(turn2=2):
    return [beat(1, 1, "BM", [words(10, "open")]),
            beat(2, turn2, "BB", B2, card="C1"),
            beat(3, turn2, "BB", B3, broll="clip-x")]


def plan(beats, tight=None, holds=None, durs=None):
    return tb.plan_with_dwell(copy.deepcopy(beats), durs or {"clip-x": 9.0}, holds or {"C1": 10.0},
                              tight=tight)


def seg_of(segs, ident):
    return next((s for s in segs if s.get("card") == ident or s.get("broll") == ident), None)


print("\n-- (a) A TIGHT TURN: THE CLIP BUTTS ONTO THE CARD --")
T = {"turns": [2], "clip_s": {"clip-x": 9.0}}
segs, log = plan(shape(), T)
c, x = seg_of(segs, "C1"), seg_of(segs, "clip-x")
check(bool(c and x) and abs(x["from_s"] - c["to_s"]) < 0.01, "the clip starts the moment the card ends",
      f"card {c and c['to_s']}, clip {x and x['from_s']}")
check(bool(c) and c["to_s"] - c["from_s"] > 10.0 + 0.5, "the card was LENGTHENED to meet it (never shortened)",
      f"{c and round(c['to_s'] - c['from_s'], 2)}s")
check(not tb.short_states(segs), "and no picture is under the dwell floor")
check(any(l.startswith("TIGHT") for l in log), "the plan says what it did", "; ".join(l[:60] for l in log))

print("\n-- (b) CONTROL: THE SAME SHAPE, TURN NOT LISTED --")
segs0, _ = plan(shape(), {"turns": [99], "clip_s": {"clip-x": 9.0}})
c0, x0 = seg_of(segs0, "C1"), seg_of(segs0, "clip-x")
check(x0 is None or x0["from_s"] - c0["to_s"] >= tb.MIN_DWELL_S - 0.01,
      "outside the listed turns the 5s gap stands", f"gap {x0 and round(x0['from_s'] - c0['to_s'], 2)}")
segsN, _ = plan(shape())
check(json.dumps(segsN, sort_keys=True) == json.dumps(segs0, sort_keys=True),
      "and an override naming other turns plans byte-identically to none at all")

print("\n-- (c) A CLIP IS NEVER STRETCHED PAST ITS OWN LENGTH --")
sw = [beat(1, 1, "BM", [words(10, "open")]),
      beat(2, 2, "BB", B2, broll="clip-x"),
      beat(3, 2, "BB", B3, card="C1")]
segs_c, _ = plan(sw, {"turns": [2], "clip_s": {"clip-x": 9.0}}, durs={"clip-x": 9.0})
xc = seg_of(segs_c, "clip-x")
check(bool(xc) and xc["to_s"] - xc["from_s"] <= 9.0 + 0.01, "the clip stays within its 9.0s",
      f"{xc and round(xc['to_s'] - xc['from_s'], 2)}s")

print("\n-- (d) A CLIP MAY BE USED SHORTER TO FIT, NEVER UNDER 8s --")
# the clip enters at ~16.9s into turn 2 and the turn is ~27.7s: 8.75s of room before the 2s handover
short_turn = [beat(1, 1, "BM", [words(10, "open")]),
              beat(2, 2, "BB", B2, card="C1"),
              beat(3, 2, "BB", [words(13, "delta"), words(15, "echo")], broll="clip-x"),
              beat(4, 3, "BM", [words(13, "close"), words(13, "after")])]
segs_d, log_d = plan(short_turn, T, durs={"clip-x": 9.5})
xd = seg_of(segs_d, "clip-x")
dur_d = xd and round(xd["to_s"] - xd["from_s"], 2)
check(xd is not None and 8.0 - 0.01 <= dur_d < 9.5 - 0.1,
      "the clip IS placed, used shorter than its 9.5s and not under 8s", f"{dur_d}")
check(any("used at" in l for l in log_d), "and the shortening is logged")
segs_d0, _ = plan(short_turn, {"turns": [99]}, durs={"clip-x": 9.5})
check(seg_of(segs_d0, "clip-x") is None, "CONTROL: without the override the same clip does not fit at all")
too_short = [short_turn[0], short_turn[1],
             beat(3, 2, "BB", [words(13, "delta"), words(8, "echo")], broll="clip-x"), short_turn[3]]
segs_e, _ = plan(too_short, T, durs={"clip-x": 9.5})
xe = seg_of(segs_e, "clip-x")
check(xe is None or xe["to_s"] - xe["from_s"] >= 8.0 - 0.01,
      "CONTROL: with under 8s of room it is NOT squeezed below the floor", f"{xe and round(xe['to_s'] - xe['from_s'], 2)}")

print("\n-- (e) THE MAPPING: A CARD IS HELD ON TO MEET A BUTTING GRAPHIC; A HOLE IS A VIOLATION --")
cues = [{"start": 0.0, "end": 9.8, "text": "[BB] One sentence opens the turn here."},
        {"start": 10.0, "end": 21.8, "text": "[BB] The card sentence runs on here."},
        {"start": 22.0, "end": 33.8, "text": "[BB] The clip sentence starts here now."},
        {"start": 34.0, "end": 45.0, "text": "[BB] And the turn closes on this one."}]
P = [{"n": 1, "turn": 1, "speaker": "BB", "layout": "two-box", "kind": "two-box", "from_s": 0.0, "to_s": 10.0,
      "snap_to_sentence": "One sentence opens the turn here.", "card": None, "broll": None},
     {"n": 2, "turn": 1, "speaker": "BB", "layout": "full", "kind": "card", "from_s": 10.0, "to_s": 20.0,
      "snap_to_sentence": "The card sentence runs on here.", "card": "C1", "broll": None},
     {"n": 3, "turn": 1, "speaker": "BB", "layout": "full", "kind": "broll", "from_s": 20.0, "to_s": 29.0,
      "snap_to_sentence": "The clip sentence starts here now.", "card": None, "broll": "x"},
     {"n": 4, "turn": 1, "speaker": "BB", "layout": "two-box", "kind": "two-box", "from_s": 29.0, "to_s": 45.0,
      "snap_to_sentence": "And the turn closes on this one.", "card": None, "broll": None}]
TL = [{"turn": 1, "kind": None, "from_s": 0.0, "to_s": 45.0}]
mm = ta.map_layout(P, TL, cues, 7.0)
mc, mx = seg_of(mm, "C1"), seg_of(mm, "x")
check(abs(mc["to_s"] - mx["from_s"]) < 0.01 and mc.get("butt_join"),
      "the card is held on until the clip enters — no hole", f"card to {mc['to_s']}, clip from {mx['from_s']}")
check(ta.holes(mm) == [], "and the mapped turn has no hole")
hole = [{"turn": 1, "from_s": 0.0, "to_s": 10.0, "layout": "full", "broll": "x"},
        {"turn": 1, "from_s": 12.0, "to_s": 20.0, "layout": "full", "card": "C1"}]
check(len(ta.holes(hole)) == 1, "CONTROL: twoway_assemble.holes finds a 2s gap after a clip (nothing can stretch it)")
check(ta.holes([dict(hole[0]), dict(hole[1], turn=2)]) == [],
      "and a gap BETWEEN turns is not a hole (that is where the furniture lives)")

print("\n-- (f) THE TURN-OPEN ENTRY ON THE MEASURED CLOCK --")
TO = [{"turn": 1, "layout": "two-box", "kind": "two-box", "from_s": 0.0, "to_s": tb.TURN_OPEN_MIN_S,
       "card": None, "broll": None},
      {"turn": 1, "layout": "full", "kind": "card", "from_s": 5.0, "to_s": 15.0, "card": "C1", "broll": None}]
check(ta.turn_open_entry(TO, TO[1], 100.0) == 100.0 + tb.TURN_OPEN_MIN_S,
      "a card straight after a 5s opening two-box enters at the turn's start + 5s")
TOb = [TO[0], dict(TO[1], card=None, broll="x", kind="broll")]
check(ta.turn_open_entry(TOb, TOb[1], 100.0) is None, "CONTROL: a CLIP is not given the card's ruling")
TOc = [dict(TO[0], to_s=7.0), TO[1]]
check(ta.turn_open_entry(TOc, TOc[1], 100.0) is None, "CONTROL: an opening two-box that is not the 5s head is not it")

print("\n-- (g) EPISODES WITH NO OVERRIDE ARE UNCHANGED --")
for pat in (r"G:\My Drive\PP Videos\PP-EP49-*\docs\episode.json", r"G:\My Drive\PP Videos\PP-EP55-*\docs\episode.json"):
    for p in glob.glob(pat):
        epj = json.load(open(p, encoding="utf-8"))
        before = copy.deepcopy(epj["layout_plan"])
        tb.apply(epj)
        check(json.dumps(before, sort_keys=True) == json.dumps(epj["layout_plan"], sort_keys=True),
              f"{pathlib.Path(p).parts[-3][:12]} re-plans byte-identically")

print(f"\ntight turns: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
