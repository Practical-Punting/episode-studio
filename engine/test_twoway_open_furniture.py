"""The open of a two-way, from EP56 cut 3 (Jodie, 13 Nov 2026): the HOST PLATE and the title card.

  (a) host_plate_window: up by his FIRST WORD, down on the first sentence end >= 6s later
  (b) CONTROL: the WHO YOU'RE HEARING card arriving before the plate can clear -> REFUSED
  (c) CONTROL: a film that does not open on the host in full frame -> REFUSED
  (d) the plate's PAGE never contains "reading" (in the open Gordon is himself; the line
      would be untrue) — while the reading chips' page still does (CONTROL: the switch works)
  (e) title_card_nologo: missing -> REFUSED with how to make it; present -> used
  (f) the corner logo is on from the FIRST FRAME

Run: python engine/test_twoway_open_furniture.py
"""
import json
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_chips as tch  # noqa: E402
import twoway_composite as tc  # noqa: E402
import twoway_render as tr  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


SRT = """1
00:00:00,280 --> 00:00:04,880
[BB] This is part three of a conversation that ran in Practical Punting at the start of two thousand and four.

2
00:00:05,800 --> 00:00:08,450
[BB] On one side, the magazine's editor, Brian Blackwell.

3
00:00:09,000 --> 00:00:11,600
[BB] On the other, Barry Meadow, the American professional.
"""
EPJ = {"speakers": {"BB": {"reader": "Gordon", "name": "Brian Blackwell", "role": "editor", "side": "left"},
                    "BM": {"reader": "Steve", "name": "Barry Meadow", "role": "US handicapper", "side": "right"}}}


def plan(open_card_at=32.0, first=None):
    seg = first or {"n": 1001, "speaker": "BB", "layout": "full", "kind": "furniture", "furniture": "open",
                    "from_s": 7.0, "to_s": 42.0}
    return {"segments": [seg, {"n": 1, "layout": "two-box", "speaker": "BM", "from_s": 42.0, "to_s": 60.0}],
            "graphics": {"open_card": {"at_s": open_card_at}}, "end_card": {"from_s": 490.0},
            "head": {"title_card": ""}}


with tempfile.TemporaryDirectory() as td:
    d = pathlib.Path(td)
    (d / "renders").mkdir()
    (d / "docs").mkdir()
    (d / "renders/merged.srt").write_text(SRT, encoding="utf-8")
    (d / "docs/episode.json").write_text(json.dumps(EPJ), encoding="utf-8")

    print("\n-- (a) the window --")
    w = tr.host_plate_window(plan(), d)
    check(w["first_word_s"] == 7.28, "his first word is at 7.28s (0.28 + the 7.0s title)", w["first_word_s"])
    check(w["on_s"] <= w["first_word_s"] and w["on_s"] >= 7.0, "the plate is up BY his first word, not before the open",
          w["on_s"])
    check(w["sentence_end_s"] == 15.45, "it leaves on the first sentence end >= 6s on (15.45s, not 11.88s)",
          w["sentence_end_s"])
    check(w["name"] == "GORDON" and w["speaker"] == "BB", "it names the host, from episode.json", w["name"])

    print("\n-- (b) CONTROL: the next graphic too close --")
    try:
        tr.host_plate_window(plan(open_card_at=16.2), d)
        check(False, "REFUSED when the open card comes 0.5s after the plate leaves")
    except tr.Unrenderable as e:
        check("open card" in str(e), "REFUSED when the open card comes 0.5s after the plate leaves", str(e)[:90])

    print("\n-- (c) CONTROL: not the open --")
    try:
        tr.host_plate_window(plan(first={"n": 1, "speaker": "BM", "layout": "two-box", "from_s": 7.0,
                                         "to_s": 42.0}), d)
        check(False, "REFUSED when the film does not open on the host in full frame")
    except tr.Unrenderable:
        check(True, "REFUSED when the film does not open on the host in full frame")

    print("\n-- (e) the title card without its own logo --")
    (d / "overlay/clips").mkdir(parents=True)
    t = d / "overlay/clips/ep99-title.mp4"
    t.write_bytes(b"x")
    p = plan()
    p["head"]["title_card"] = str(t)
    try:
        tr.title_card_nologo(p)
        check(False, "CONTROL: REFUSED while ep99-title-nologo.mp4 does not exist")
    except tr.Unrenderable as e:
        check("twoway_cards.py" in str(e), "CONTROL: REFUSED while ep99-title-nologo.mp4 does not exist, says how",
              str(e)[:80])
    (d / "overlay/clips/ep99-title-nologo.mp4").write_bytes(b"x")
    check(tr.title_card_nologo(p).name == "ep99-title-nologo.mp4", "uses the no-logo title card once it exists")

print("\n-- (d) the plate never says 'reading' --")
layout = tc.load_layout()
plate = {"BB": {"name": "GORDON", "reading": None, "role": None, "x": 40, "bottom_y": 1016, "rule_colour": "#DA532C"}}
page = tch.page_html(plate, layout)
check("GORDON" in page and "reading" not in page.split("<body>")[1], "the host plate page: name, and no 'reading'")
chips = tc.chips_for(EPJ["speakers"], layout)
page2 = tch.page_html(chips, layout)
check("reading <b>Brian Blackwell</b>" in page2, "CONTROL: the reading chips' page still says 'reading Brian Blackwell'")

print("\n-- (f) the logo from the first frame --")
check(tr.logo_on_s() == 0.0, "the corner chip comes on at 0.0s")

print()
if fails:
    print(f"FAILED {len(fails)}: {fails}")
    raise SystemExit(1)
print("ALL PASS")
