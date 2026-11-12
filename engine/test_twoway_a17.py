"""A17: a card's points build ONE BY ONE, as the reader SAYS each one (Jodie, 6 Oct 2026).

And the two faults that making A17 honest exposed on EP56 (12 Nov 2026):
  · a graphic snapped to the sentence end nearest its ARITHMETIC position, not to the
    sentence the plan put it after (card C7 came out 13.9s after its own words);
  · the plan was made on the ESTIMATE clock (words / 2.6) and the real reading was 17%
    faster, so turn 8's fixed-length graphics no longer fitted (it overflowed by 11s).

Sections — each with a CONTROL that proves the check can fail:
  (a) author_cards.apply_a17 retimes the RIGHT elements, read off the block's own template
  (b) a card with no `_a17_points` is untouched — every page before EP56, byte for byte
  (c) twoway_beats: an A17 card aims at its FIRST POINT's sentence, not its paragraph's start
  (d) twoway_a17.measure: delay = said - entry, never before the block's own stagger,
      never closer than the readable cadence; faults for words said before the card
  (e) twoway_beats.measured_beats: paragraphs take their MEASURED lengths, summing to the turn
  (f) twoway_assemble.map_layout: a graphic lands after the sentence the PLAN named
  (g) REAL DATA: every non-A17 card of EP55 and EP48 authors identically to HEAD's author_cards

FAIL-FIRST: point BEATS=, ASSEMBLE= or AUTHOR= at the pre-change files and (c), (f) and
(a) go red.

Run: python engine/test_twoway_a17.py
"""
import glob
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))


def load(name, env, default):
    path = os.environ.get(env) or str(default)
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


ac = load("author_cards", "AUTHOR", SCRIPTS / "author_cards.py")
tb = load("twoway_beats", "BEATS", HERE / "twoway_beats.py")
ta = load("twoway_assemble", "ASSEMBLE", HERE / "twoway_assemble.py")
import twoway_a17 as ta17  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def raises(fn):
    try:
        fn()
    except Exception as e:                                         # noqa: BLE001
        return type(e).__name__
    return None


def entries(anim):
    return {e["sel"]: e for e in ac._anim_entries(anim)}


# ───────────────────────────────────────────────────────────────── (a) ──
print("\n-- (a) A17 RETIMES THE RIGHT ELEMENTS, READ OFF THE BLOCK'S OWN TEMPLATE --")
compare = {"id": "CX", "block": "compare", "eyebrow": "E", "headline": "H",
           "content": {"cols": [{"tone": "yes", "k": "A", "v": "one"},
                                {"tone": "no", "k": "B", "v": "two"}], "note": "a note"},
           "_a17_points": [["cols[1]", "alpha"], ["cols[2]", "beta"]],
           "_a17_delays": [1500, 4200]}
blk = ac.load_block("compare")
base = entries(ac.block_anim(compare, blk))
check(ac.a17_selector(compare, blk, "cols[2]") == "#c2", "a list point is the element its @each draws",
      ac.a17_selector(compare, blk, "cols[2]"))
check(ac.a17_floors(compare, blk) == [int(base["#c1"]["opts"]["delay"]),
                                      int(base["#c2"]["opts"]["delay"])],
      "the floors ARE the block's own stagger", str(ac.a17_floors(compare, blk)))
anim, on = ac.apply_a17(ac.block_anim(compare, blk), compare, blk)
e = entries(anim)
check(on and e["#c1"]["opts"]["delay"] == 1500 and e["#c2"]["opts"]["delay"] == 4200,
      "each point lands on its measured delay",
      f"#c1 {e['#c1']['opts']['delay']}, #c2 {e['#c2']['opts']['delay']}")
check(e["#c1"].get("a17") == "point" and e["#c2"].get("a17") == "point",
      "and is marked a17, so the build budget and cadence leave it out")
want_note = base["#note"]["opts"]["delay"] + (4200 - base["#c2"]["opts"]["delay"])
check(e["#note"]["opts"]["delay"] == want_note and e["#note"].get("a17") == "follows",
      "the note keeps its place after the point it followed", f"{e['#note']['opts']['delay']} vs {want_note}")

gap = {"id": "CG", "block": "gap", "eyebrow": "E", "headline": "H",
       "content": {"q": "A question?", "a": "AN ANSWER.", "note": None},
       "_a17_points": [["q", "x"], ["a", "y"]], "_a17_delays": [900, 6100]}
gblk = ac.load_block("gap")
check(ac.a17_selector(gap, gblk, "q") == "#gq" and ac.a17_selector(gap, gblk, "a") == "#ga",
      "a scalar point is the element whose whole body is {{key}}")
g0 = entries(ac.block_anim(gap, gblk))
ganim, _ = ac.apply_a17(ac.block_anim(gap, gblk), gap, gblk)
g = entries(ganim)
check(g["#gq"]["opts"]["delay"] == 900 and g["#ga"]["opts"]["delay"] == 6100, "q and a land on their words")
check(g["#grule"]["opts"]["delay"] == g0["#grule"]["opts"]["delay"] + (900 - g0["#gq"]["opts"]["delay"]),
      "the rule under the question follows the QUESTION, not the answer")

page = ac.render_card(dict(gap), gblk, ac.load_frame("fullscreen"))
check('data-pp-a17="1"' in page, "the page says it is an A17 page")

print("  controls:")
check(raises(lambda: ac.apply_a17(ac.block_anim(compare, blk),
                                  dict(compare, _a17_delays=[4000, 1000]), blk)) == "Halt",
      "CONTROL: delays that go backwards HALT")
check(raises(lambda: ac.a17_selector(compare, blk, "rows[1]")) == "Halt",
      "CONTROL: a point the block cannot draw HALTS")

print("\n-- (a2) AUTHORING NEEDS THE MEASUREMENT; THE COMMISSION DOES NOT (CLAUDE.md 4a) --")
bare = {k: v for k, v in compare.items() if k != "_a17_delays"}
a_bare = ac.block_anim(bare, blk)
check(ac.apply_a17(a_bare, bare, blk) == (a_bare, False),
      "at the commission (nothing measured yet) the block's own stagger stands")
check(raises(lambda: ac.a17_attach(bare, {"build": {}})) == "Halt",
      "CONTROL: AUTHORING an A17 card with no build.a17 HALTS (never a guessed time)")
meas = {"build": {"a17": {"CX": {"points": [{"key": "cols[1]", "anchor": "alpha", "delay_ms": 900},
                                            {"key": "cols[2]", "anchor": "beta", "delay_ms": 3000}]}}}}
check(ac.a17_attach(bare, meas).get("_a17_delays") == [900, 3000], "and attaches exactly the measured delays")
stale = json.loads(json.dumps(meas))
stale["build"]["a17"]["CX"]["points"][1]["anchor"] = "gamma"
check(raises(lambda: ac.a17_attach(bare, stale)) == "Halt",
      "CONTROL: a measurement for DIFFERENT anchors (stale) HALTS")
import preflight_cards as pc  # noqa: E402
check(pc.rehearsal_faults(ac, dict(bare), blk) == [],
      "the commission pre-flight passes an A17 card that has nothing measured yet")
badkey = dict(bare, _a17_points=[["cols[1]", "alpha"], ["rows[2]", "beta"]])
check(len(pc.rehearsal_faults(ac, badkey, blk)) == 1,
      "CONTROL: and FAILS one whose point names an element the block cannot draw")

# ───────────────────────────────────────────────────────────────── (b) ──
print("\n-- (b) A CARD WITH NO _a17_points IS UNTOUCHED --")
plain = {k: v for k, v in compare.items() if not k.startswith("_a17")}
a0 = ac.block_anim(plain, blk)
check(ac.apply_a17(a0, plain, blk) == (a0, False), "apply_a17 returns the spec unchanged")
check('data-pp-a17' not in ac.render_card(dict(plain), blk, ac.load_frame("fullscreen")),
      "and the page carries no A17 mark")

# ───────────────────────────────────────────────────────────────── (c) ──
print("\n-- (c) AN A17 CARD AIMS AT ITS FIRST POINT'S SENTENCE --")
S = ["This is the opening sentence of the paragraph and it sets up the idea.",
     "Here is a second sentence that carries on without any point in it.",
     "A third sentence also keeps going with more of the same talking.",
     "Now comes the bright idea that the card is all about for viewers.",
     "And a fifth sentence finishes the thought before the turn moves on.",
     "A sixth sentence rounds the whole paragraph off for good measure here.",
     "A seventh sentence gives the closing two-box its own room to breathe.",
     "And an eighth sentence hands the turn back with plenty of air left."]
line = " ".join(S)
beats = [
    {"n": 1, "turn": 1, "speaker": "BM", "line": "A short opening turn from the other man here.",
     "est_s": 3.5, "card": None, "broll": None, "para_in_turn": 1, "paras_in_turn": 1},
    {"n": 2, "turn": 2, "speaker": "BB", "line": line, "est_s": round(len(line.split()) / 2.6, 2),
     "card": "C1", "broll": None, "para_in_turn": 1, "paras_in_turn": 1},
]
first = {"C1": "the bright idea"}
# The placement step itself, one pass (the dwell loop may then move any graphic, A17 or not).
units = tb._split_turn_open(tb._units([dict(b) for b in beats]))
placed, _ = tb._place_graphics(units, {}, {"C1": 10.0}, a17_first=first)
lands = next((u["text"] for u in placed if u.get("card") == "C1"), None)
check(lands == S[3], "the card is placed on the sentence that carries its first point", str(lands)[:50])
placed0, _ = tb._place_graphics(units, {}, {"C1": 10.0})
lands0 = next((u["text"] for u in placed0 if u.get("card") == "C1"), None)
check(lands0 is not None and lands0 != S[3],
      "CONTROL: without A17 it lands at the paragraph's first legal sentence, as before",
      str(lands0)[:50])
segs, log = tb.plan_with_dwell([dict(b) for b in beats], {}, {"C1": 10.0}, a17_first=first)
c = [s for s in segs if s.get("card") == "C1"]
prefix = beats[0]["est_s"] + sum(u["est_s"] for u in units if u["turn"] == 2
                                  and u["text"] in S[:3])
check(bool(c) and c[0]["from_s"] <= prefix + 0.05,
      "and if the dwell law moves it, it moves EARLIER — never after its first point",
      f"entered {c[0]['from_s'] if c else None}, point sentence at {prefix:.2f}")

# ───────────────────────────────────────────────────────────────── (d) ──
print("\n-- (d) MEASURED DELAYS: SAID MINUS ENTRY, FLOORED, IN ORDER --")
cues = [{"start": 0.0, "end": 10.0, "text": "[BB] one two three alpha beta four five gamma delta six"}]
tl = [{"turn": 4, "kind": None, "from_s": 0.0, "to_s": 10.0}]
epj = {"beats": [{"n": 1, "turn": 4}],
       "cards": [{"id": "C1", "beat": 1, "_a17_points": [["cols[1]", "alpha beta"], ["cols[2]", "gamma delta"]],
                  "content": {"cols": [{"k": "A", "v": "one"}, {"k": "B", "v": "two"}]}}]}
import derive_card_timings as dct  # noqa: E402
W = dict(dct.word_timeline([(0.0, 10.0, "one two three alpha beta four five gamma delta six")]))
H = 7.0
seg = [{"card": "C1", "from_s": H + 2.0, "to_s": H + 9.8}]
m = ta17.measure(seg, cues, tl, epj, H, {"C1": [360, 680]})
p = m["C1"]["points"]
check(abs(p[0]["said_at_s"] - (W["alpha"] + H)) < 0.001,
      "the point is said where merged.srt says (tag stripped), on the FINISHED clock",
      f"{p[0]['said_at_s']} vs {W['alpha'] + H:.3f}")
tagged = dict(dct.word_timeline([(0.0, 10.0, cues[0]["text"])]))
check(tagged["alpha"] - W["alpha"] > 0.3,
      "CONTROL: timing the TAGGED text would have put it late", f"+{tagged['alpha'] - W['alpha']:.2f}s")
check(abs(p[0]["delay_ms"] - (W["alpha"] - 2.0) * 1000) <= 1, "delay = said - card entry",
      str(p[0]["delay_ms"]))
m2 = ta17.measure([{"card": "C1", "from_s": H + 4.0, "to_s": H + 9.8}], cues, tl, epj, H, {"C1": [360, 680]})
check(m2["C1"]["points"][0]["delay_ms"] == 360, "a point said before the card is up lands at the block's own stagger")
check(any("BEFORE the card is up" in v for v in ta17.violations(m2, epj)),
      "CONTROL: and that is a FAULT, not a quiet fix")
close = {"beats": epj["beats"], "cards": [dict(epj["cards"][0], _a17_points=[["cols[1]", "alpha"], ["cols[2]", "beta"]])]}
m3 = ta17.measure(seg, cues, tl, close, H, {"C1": [360, 680]})
d3 = [q["delay_ms"] for q in m3["C1"]["points"]]
check(d3[1] - d3[0] >= ta17.POINT_STEP_MIN_MS, "two anchors in one breath still arrive a cadence apart", str(d3))
miss = {"beats": epj["beats"], "cards": [dict(epj["cards"][0], _a17_points=[["cols[1]", "not said at all"]])]}
check(any("not found" in v for v in ta17.violations(ta17.measure(seg, cues, tl, miss, H), miss)),
      "CONTROL: an anchor nobody says is a SCRIPT fault")

# ───────────────────────────────────────────────────────────────── (e) ──
print("\n-- (e) THE PLAN ON THE MEASURED CLOCK --")
mb_beats = [{"n": 1, "turn": 1, "speaker": "BB", "line": "Alpha one two. Beta three four.", "est_s": 9.0},
            {"n": 2, "turn": 1, "speaker": "BB", "line": "Gamma five six seven.", "est_s": 9.0}]
mb_cues = [{"start": 0.0, "end": 2.0, "text": "[BB] Alpha one two."},
           {"start": 2.2, "end": 4.0, "text": "[BB] Beta three four."},
           {"start": 6.0, "end": 9.0, "text": "[BB] Gamma five six seven."}]
mb = tb.measured_beats(mb_beats, mb_cues, [{"turn": 1, "kind": None, "from_s": 0.0, "to_s": 9.0}])
check(abs(sum(b["est_s"] for b in mb) - 9.0) < 0.02, "the paragraphs sum to the turn's measured span",
      str([b["est_s"] for b in mb]))
check(abs(mb[0]["est_s"] - 6.0) < 0.05, "a paragraph runs to the NEXT paragraph's first spoken word",
      str(mb[0]["est_s"]))
check(mb[0]["est_s_words"] == 9.0 and len(mb[0]["est_sentence_s"]) == 2,
      "the estimate is kept for the record, and every sentence gets its own measured length")
check(mb_beats[0]["est_s"] == 9.0, "the input beats are not modified in place")

# ───────────────────────────────────────────────────────────────── (f) ──
print("\n-- (f) A GRAPHIC LANDS AFTER THE SENTENCE THE PLAN NAMED --")
mcues = [{"start": 0.0, "end": 6.0, "text": "[BB] First sentence is here."},
         {"start": 6.2, "end": 12.0, "text": "[BB] Sentence two ends here."},
         {"start": 12.2, "end": 18.0, "text": "[BB] Third one now."},
         {"start": 18.2, "end": 40.0, "text": "[BB] And a long fourth sentence runs on to the end."}]
plan = [{"n": 1, "turn": 1, "speaker": "BB", "layout": "two-box", "kind": "two-box", "from_s": 0.0, "to_s": 20.0,
         "snap_to_sentence": "First sentence is here.", "card": None, "broll": None},
        {"n": 2, "turn": 1, "speaker": "BB", "layout": "full", "kind": "card", "from_s": 20.0, "to_s": 30.0,
         "snap_to_sentence": "And a long fourth sentence runs on to the end.", "card": "C1", "broll": None},
        {"n": 3, "turn": 1, "speaker": "BB", "layout": "two-box", "kind": "two-box", "from_s": 30.0, "to_s": 60.0,
         "snap_to_sentence": "And a long fourth sentence runs on to the end.", "card": None, "broll": None}]
mtl = [{"turn": 1, "kind": None, "from_s": 0.0, "to_s": 40.0}]
mm = ta.map_layout(plan, mtl, mcues, 7.0)
card = [s for s in mm if s.get("card") == "C1"][0]
check(abs(card["from_s"] - (6.0 + 7.0)) < 0.01,
      "the card enters at the measured end of 'First sentence is here.'",
      f"entered {card['from_s']}, the sentence ends {6.0 + 7.0}")

# ───────────────────────────────────────────────────────────────── (g) ──
print("\n-- (g) REAL DATA: NON-A17 CARDS AUTHOR IDENTICALLY TO HEAD --")
repo = HERE.parent
head = subprocess.run(["git", "-C", str(repo), "show", "HEAD:.claude/skills/pp-episode-production/scripts/author_cards.py"],
                      capture_output=True, text=True, encoding="utf-8").stdout
# Beside the real one (it finds its templates relative to itself at import), deleted after.
hp = SCRIPTS / "_test_a17_author_cards_head.py"
hp.write_text(head, encoding="utf-8")
try:
    oldac = load("author_cards_head", "_NONE_", hp)
finally:
    hp.unlink(missing_ok=True)
n = same = 0
for pat in (r"G:\My Drive\PP Videos\PP-EP55-*\docs\episode.json", r"G:\My Drive\PP Videos\PP-EP48-*\docs\episode.json"):
    for p in glob.glob(pat):
        ep = json.load(open(p, encoding="utf-8"))
        for cc in ep.get("cards", []):
            if not cc.get("block") or cc["block"] == "bespoke":
                continue
            try:
                b1, b2 = ac.load_block(cc["block"]), oldac.load_block(cc["block"])
                f1, f2 = ac.load_frame(cc.get("layout", "fullscreen")), oldac.load_frame(cc.get("layout", "fullscreen"))
                p1, p2 = ac.render_card(json.loads(json.dumps(cc)), b1, f1), oldac.render_card(json.loads(json.dumps(cc)), b2, f2)
            except Exception as ex:                                # noqa: BLE001
                print(f"    (skipped {cc.get('id')}: {type(ex).__name__}: {str(ex)[:120]})")
                continue
            n += 1
            same += p1 == p2
check(n >= 10 and same == n, f"{same} of {n} real cards author byte-identically to HEAD")

print(f"\nA17: {('ALL PASS' if not fails else str(len(fails)) + ' FAILED')}")
sys.exit(1 if fails else 0)
