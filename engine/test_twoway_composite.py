#!/usr/bin/env python3
"""test_twoway_composite.py — the two-box mechanism and the reaction catalogue.

    python engine/test_twoway_composite.py

🔴 EVERYTHING HERE IS ABOUT THE MECHANISM, NOT THE DESIGN. The design is data
(`assets/twoway/layout.json`) and Cowork is writing it; these assertions must stay true
whatever numbers it carries, which is why they check RELATIONSHIPS — the listener is
darker than the speaker, the push is in the house window, the logo is outside both
windows — and never a specific pixel.

If a test here starts failing when the design lands, the design has broken a rule of the
format and not merely a placeholder.
"""
from __future__ import annotations

import json
import pathlib
import os
import copy
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import twoway_beats as tb                                        # noqa: E402
import twoway_composite as tc                                    # noqa: E402
import twoway_reactions as rx                                    # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"  <- {why}" if not cond and why else ""))


def overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


SPEAKERS = {
    "BB": {"name": "Brian Blackwell", "role": "editor, Practical Punting",
           "reader": "Gordon", "template": "brian", "side": "left", "host": True},
    "BM": {"name": "Barry Meadow", "role": "US handicapper",
           "reader": "Steve", "template": "barry", "side": "right", "host": False},
}


def _refuses(layout_dict, needle):
    """True when load_layout REFUSES this layout, for the stated reason.

    The candidate is written to a real file and handed to the REAL guard, so the
    test exercises load_layout rather than a second copy of its reasoning. A test
    that re-implements the rule it is checking passes when the rule is deleted.
    """
    import json, tempfile, pathlib as _pl
    fd = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    fd.write(json.dumps(layout_dict)); fd.close()
    try:
        tc.load_layout(_pl.Path(fd.name))
        return False
    except tc.Unbuildable as e:
        return needle in str(e)
    finally:
        os.unlink(fd.name)

def main() -> int:
    print("-- THE LAYOUT FILE IS A CONTRACT, AND IT IS CHECKED --")
    lay = tc.load_layout()
    check("  it loads and carries every section the composite needs", bool(lay))
    for missing in ("panels", "push", "chips", "logo", "source", "speaker"):
        cut = json.loads(json.dumps(lay))
        cut.pop(missing)
        tmp = HERE / f"_t-{missing}.json"
        tmp.write_text(json.dumps(cut), encoding="utf-8")
        try:
            tc.load_layout(tmp)
            check(f"  a layout with no `{missing}` is REFUSED", False, "it loaded")
        except tc.Unbuildable:
            check(f"  a layout with no `{missing}` is REFUSED", True)
        finally:
            tmp.unlink(missing_ok=True)

    print("\n-- THE FRAME'S RULES, WHATEVER THE DESIGN'S NUMBERS ARE --")
    L, R = lay["panels"]["left"]["rect"], lay["panels"]["right"]["rect"]
    check("  the two panels do not overlap each other", not overlaps(L, R))
    check("  left really is left of right", L[0] + L[2] <= R[0], f"{L} {R}")
    # 🔴 THE MEN FILL THE SCREEN. The approved design is two FULL-HEIGHT panels edge to
    # edge — v1's inset 16:9 windows were rejected ("a huge frame with a whole lot of
    # stuff"), so a panel that came back landscape would be the old design creeping back.
    check("  each panel is TALLER than it is wide — full height, not an inset window",
          all(h > w for w, h in ((L[2], L[3]), (R[2], R[3]))),
          f"{L[2]}x{L[3]}, {R[2]}x{R[3]}")
    check("  together they very nearly fill the frame",
          (L[2] + R[2]) / lay["canvas"]["w"] > 0.95
          and L[3] / lay["canvas"]["h"] > 0.95,
          f"{(L[2]+R[2])/lay['canvas']['w']:.3f} wide, "
          f"{L[3]/lay['canvas']['h']:.3f} tall")
    check("  the gap between them matches the outer margin",
          R[0] - (L[0] + L[2]) == lay["panels"]["gap"] == L[0])
    check("  both fit inside the canvas",
          all(r[0] >= 0 and r[1] >= 0 and r[0] + r[2] <= lay["canvas"]["w"]
              and r[1] + r[3] <= lay["canvas"]["h"] for r in (L, R)))

    print("\n-- THE LOGO IS THE CHANNEL'S, NOT A PRESENTER'S --")
    # There is no furniture band any more, so the logo sits OVER the picture. What must
    # stay true is that it never lands inside either man's CHIP, where it would read as
    # belonging to him. (Build spec §6, carried across to the new design.)
    lg = lay["logo"]
    lg_rect = [lay["canvas"]["w"] - lg["right"] - lg["width"],
               lay["canvas"]["h"] - lg["bottom"] - 128, lg["width"], 128]
    ch = lay["chips"]
    chips_rects = [[r[0] + ch["left"], r[1] + r[3] - ch["bottom"] - 150, 420, 150]
                   for r in (L, R)]
    check("  the logo is OUTSIDE both presenters' chips",
          not any(overlaps(lg_rect, c) for c in chips_rects), f"{lg_rect}")
    check("  it sits in the bottom-right corner of the FRAME",
          lg_rect[0] > lay["canvas"]["w"] * 0.6
          and lg_rect[1] > lay["canvas"]["h"] * 0.6, f"{lg_rect}")
    check("  and it is not fully opaque", 0.5 <= lg["opacity"] <= 1.0,
          f"{lg['opacity']}")

    print("\n-- THE LISTENER IS DARKER. HE IS NOT SMALLER ANY MORE. --")
    li, spk = lay["listener"], lay["speaker"]
    check("  darker than the speaker", li["brightness"] < spk["brightness"])
    check("  but not so dark he reads as switched off",
          li["brightness"] >= 0.6, f"{li['brightness']}")
    check("  and a touch less saturated", li["saturation"] < spk["saturation"])
    check("  BOTH panels wear the keyline, identically (Jodie, 18 Sep 2026)",
          spk["keyline"] == li.get("keyline") and spk["keyline"]["width"] > 0,
          f"speaker {spk['keyline']} / listener {li.get('keyline')}")
    check("  the keyline is thin — a line, not a border",
          1 <= spk["keyline"]["width"] <= 8, f"{spk['keyline']['width']}px")
    # the CONTROL: a layout where the listener is brighter must be refused outright.
    bad = json.loads(json.dumps(lay))
    bad["listener"]["brightness"] = 1.2
    tmp = HERE / "_t-bright.json"
    tmp.write_text(json.dumps(bad), encoding="utf-8")
    try:
        tc.load_layout(tmp)
        check("  a listener BRIGHTER than the speaker is REFUSED", False, "it loaded")
    except tc.Unbuildable:
        check("  a listener BRIGHTER than the speaker is REFUSED", True)
    finally:
        tmp.unlink(missing_ok=True)

    print("\n-- THE PUSH: THE HOUSE MOVE, NEVER A DISSOLVE --")
    spec = tc.push_spec(lay, "two-box", "single")
    check("  700-800ms, per A10 rule 5", 700 <= spec["duration_ms"] <= 800,
          f"{spec['duration_ms']}ms")
    check("  it is a PUSH and says so", spec["kind"] == "push")
    check("  eased on the house cubic-bezier",
          spec["easing"].startswith("cubic-bezier"), spec["easing"])
    check("  and both directions are declared",
          tc.push_spec(lay, "single", "two-box")["kind"] == "push")
    bad = json.loads(json.dumps(lay))
    bad["push"]["duration_ms"] = 1400
    try:
        tc.push_spec(bad, "two-box", "single")
        check("  a push outside the window is REFUSED", False, "it was accepted")
    except tc.Unbuildable:
        check("  a push outside the window is REFUSED", True)

    print("\n-- THE EYE LINE IS MEASURED, AND AN HONEST NONE WHEN IT CANNOT BE --")
    off = tc.eye_offsets(lay, {"BB": None, "BM": 430.0})
    check("  an unmeasured presenter shifts by zero, not by a guess",
          off["BB"] == 0.0, f"{off}")
    k = L[3] / lay["canvas"]["h"]
    check("  a measured one shifts onto the target",
          abs(off["BM"] - (430.0 * k - lay["eyes"]["target_in_panel"])) < 0.05,
          f"{off}")
    # 🔴 THE REAL MEASUREMENTS ARE IN THE FILE, and the default path uses them.
    dflt = tc.eye_offsets(lay)
    check("  with no argument it uses the measurements the layout records",
          set(dflt) == set(lay["eyes"]["measured_1080"]), f"{dflt}")
    check("  the two men end up on the SAME line, which is the whole point",
          abs((lay["eyes"]["measured_1080"]["BM"] * k - dflt["BM"])
              - (lay["eyes"]["measured_1080"]["BB"] * k - dflt["BB"])) < 0.05,
          f"{dflt}")

    print("\n-- THE CHIPS ARE GENERATED FROM `speakers`, NEVER TYPED --")
    chips = tc.chips_for(SPEAKERS, lay)
    check("  Gordon's chip names the reader, the man and the role",
          (chips["BB"]["name"], chips["BB"]["reading"], chips["BB"]["role"])
          == ("GORDON", "Brian Blackwell", "editor, Practical Punting"),
          f"{chips['BB']}")
    check("  Steve's too",
          (chips["BM"]["name"], chips["BM"]["reading"], chips["BM"]["role"])
          == ("STEVE", "Barry Meadow", "US handicapper"), f"{chips['BM']}")
    check("  each sits inside its own man's panel",
          chips["BB"]["x"] > L[0] and chips["BB"]["x"] < L[0] + L[2]
          and chips["BM"]["x"] > R[0] and chips["BM"]["x"] < R[0] + R[2])
    # 🔴 FIRST MINUTE ONLY. An introduction that never leaves is a caption.
    check("  they are a FIRST-MINUTE device, not a permanent caption",
          chips["BB"]["visible_s"][0] == 0 and 30 <= chips["BB"]["visible_s"][1] <= 90,
          f"{chips['BB']['visible_s']}")
    check("  the listener's rule is a different colour from the speaker's",
          chips["BB"]["rule_colour"] != chips["BB"]["listener_rule_colour"])
    # the OLD entry point must fail loudly rather than quietly not exist
    try:
        tc.supers_for(SPEAKERS, lay)
        check("  supers_for() is gone and SAYS SO", False, "it returned")
    except tc.Unbuildable as e:
        check("  supers_for() is gone and SAYS SO", "chips_for" in str(e))

    print("\n-- THE CATALOGUE (build spec §8) --")
    cat = rx.build()
    ids = [r["id"] for r in cat["reactions"]]
    check(f"  every code the format defines is in it ({len(rx.CODES)})",
          set(ids) == set(rx.CODES), f"{sorted(set(rx.CODES) - set(ids))}")
    check("  it validates as sound", not rx.validate(cat), f"{rx.validate(cat)[:2]}")
    check("  R10 is the ONE clip that does not end neutral",
          [r["id"] for r in cat["reactions"] if not r["ends_neutral"]] == ["R10"])
    check("  no BED is marked loopable — a bed chains, it never loops",
          not [r["id"] for r in cat["reactions"]
               if r["id"] in tb.BEDS and r["loopable"]])
    check("  filenames follow REACTIONS §4",
          rx.filename("BB", "R1a") == "BB-R1a.mp4"
          and rx.filename("BM", "R12") == "BM-R12.mp4")
    # ⚠️ THE CONTROL: an incomplete library must be VISIBLE, not silently half-used.
    try:
        rx.build(strict=True)
        check("  --strict REFUSES an incomplete library",
              not cat["_missing"], "it accepted a library with gaps")
    except rx.Invalid as e:
        check("  --strict REFUSES an incomplete library", True)
        check("  and names how many clips are missing", "clip(s) are not on disk" in str(e))

    print("\n-- THE FALLBACK IS LOUD, ALWAYS --")
    log = []
    got = rx.resolve(cat, "BB", "R9", ep="EP49", beat=12, log=log)
    check("  a code with no file still resolves — the build never stops",
          got is not None)
    check("  it is marked as a substitution", got["substituted"] is True)
    check("  and the log line names episode, beat, asked and played",
          log and "EP49" in log[0] and "beat 12" in log[0] and "R9" in log[0],
          f"{log[:1]}")

    print("\n-- THE LISTENER'S WINDOW, DRIVEN BY THE COMMISSION'S OWN CHOICES --")
    plan = [
        {"layout": "two-box", "listener": "BB", "speaker": "BM", "from_s": 0.0,
         "to_s": 50.0, "beats": [1],
         "reaction": {"bed": "R1a", "bed_chain": [{"at_s": 44.0, "to": "R11"}],
                      "punct": [{"at_s": 10.0, "r": "R2"}, {"at_s": 30.0, "r": "R4"}]}},
        {"layout": "full", "listener": "BB", "speaker": "BM", "from_s": 50.0,
         "to_s": 70.0, "beats": [2], "reaction": None},
        {"layout": "two-box", "listener": "BB", "speaker": "BM", "from_s": 70.0,
         "to_s": 100.0, "beats": [3],
         "reaction": {"bed": "R1b", "bed_chain": [],
                      "punct": [{"at_s": 5.0, "r": "R2"}]}},
    ]
    idle = [{"file": f"renders/idle/BB-{i:02d}.mp4", "speaker": "BB", "dur_s": 3.7}
            for i in (1, 2, 3)]
    log = []
    lp = tc.listener_plan(plan, cat, idle, ep="EP49", log=log)
    check("  one entry per TWO-BOX segment, none for a full frame", len(lp) == 2)
    check("  with no clips rendered yet, the bed falls back to a harvested pause",
          all(e["bed"]["file"].startswith("renders/idle/") for e in lp),
          f"{[e['bed'].get('file') for e in lp]}")
    check("  and a different pause each time — never the same clip twice running",
          lp[0]["bed"]["file"] != lp[1]["bed"]["file"])
    # R2 at 10s and again at 75s: 65s apart, inside the 90s window, so the second goes.
    played = [p["id"] for e in lp for p in e["punct"]]
    check(f"  a clip inside the {tc.IDLE_REUSE_S:.0f}s no-reuse window is DROPPED",
          played.count("R2") == 1, f"{played}")
    check("  and the drop is in the run log, not silent",
          any("REACTION DROPPED" in x for x in log), f"{log[-2:]}")
    check("  the bed chain is carried through to the assembler",
          lp[0]["bed_chain"] and lp[0]["bed_chain"][0]["id"] == "R11")
    check("  every substitution is logged",
          sum(1 for x in log if "SUBSTITUTED" in x) >= 2, f"{len(log)} lines")

    print("\n-- THE GRAPH IS RETURNED AS TEXT, SO IT CAN BE ASSERTED --")
    g = tc.composite_graph(lay, {"BB": "left", "BM": "right"},
                           [{"speaker": "BB", "listener": "BM"}], {"BB": 0.0, "BM": 2.0})
    check("  the speaker is at full brightness", "eq=brightness=0.0" in g
          or "eq=brightness=0," in g or "brightness=0.0," in g, g[:200])
    check("  the listener is not", "eq=brightness=-" in g)
    check("  both panels are overlaid at their declared rects",
          f"overlay={L[0]}:{L[1]}" in g and f"overlay={R[0]}:{R[1]}" in g)
    check("  the panel is FILLED, never padded — a pad would show the background",
          "crop=" in g and "pad=" not in g, g[:300])
    check("  BOTH panels get the keyline (Jodie, 18 Sep 2026)",
          g.count("drawbox") == 2 and f"drawbox=x={L[0]}" in g
          and f"drawbox=x={R[0]}" in g, f"{g.count(chr(34))} quotes, graph {len(g)}")
    # 🔴 AND THE FRAME DOES NOT MOVE WHEN THE SPEAKER DOES. The two drawbox lines are
    # emitted in PANEL order, not in speaker/listener order, so they come out
    # byte-identical in both directions. A keyline that changed sides was reading as a
    # cut inside a shot that had not changed, and this is that fix made mechanical.
    _kl = lambda gr: [x.strip() for x in gr.split(chr(59)) if "drawbox" in x]
    _flip = tc.composite_graph(lay, {"BB": "left", "BM": "right"},
                               [{"speaker": "BM", "listener": "BB"}],
                               {"BB": 0.0, "BM": 2.0})
    check("  the keyline is identical whoever is speaking",
          _kl(g) == _kl(_flip), f"{_kl(g)} vs {_kl(_flip)}")
    check("  and the graph says what the transition is",
          "push" in g and "never a dissolve" in g)

    print('\n-- THE PER-PRESENTER GRADE: THE TWO FACES MEET IN THE MIDDLE --')
    check("  each presenter's own gamma is in the graph",
          f"eq=gamma={lay['grade']['gamma']['BB']}" in g
          and f"eq=gamma={lay['grade']['gamma']['BM']}" in g, g[:400])
    check("  the grade runs BEFORE the speaker/listener state, so .84 is "
          "relative to the GRADED value",
          all(gg.index("eq=gamma=") < gg.index("eq=brightness=")
              for gg in g.split(";") if "eq=gamma=" in gg), g[:400])
    # the RELATIONSHIPS, never the pixels: one man trimmed, one lifted.
    _gm = [float(v) for v in lay["grade"]["gamma"].values()]
    check("  one man is trimmed and one is lifted", min(_gm) < 1.0 < max(_gm), f"{_gm}")

    bad = copy.deepcopy(lay); bad["grade"]["gamma"] = {"BM": 1.05, "BB": 1.09}
    check("  a grade that lifts BOTH men is REFUSED — that is a re-light, not a match",
          _refuses(bad, "MEET IN THE MIDDLE"))
    bad = copy.deepcopy(lay); bad["grade"]["gamma"] = {"BM": 0.4, "BB": 1.9}
    check("  a gamma outside 0.6-1.6 is REFUSED — it needs a TEMPLATE, not a filter",
          _refuses(bad, "re-light"))
    bad = copy.deepcopy(lay); del bad["grade"]
    check("  a layout with no grade section at all is REFUSED",
          _refuses(bad, "no `grade` section"))

    print(f"\ntwo-box composite: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
