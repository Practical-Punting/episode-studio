"""derive_card_timings.py — THE FLAG MUST DESCRIBE THE CARD IT NAMES.

Two faults found on EP23 (13 Aug 2026), both the same shape: a number that describes
one thing, printed as though it described another, with nothing comparing the two.

  A1  the card-card branch appended why_card_beat(ids[j]) — the SECOND card's dwell —
      so the card that GIVES WAY was described with the other card's numbers. EP23's
      C23 read "needs 19.80s" when it needed 9.0s; EP22's C19 read "18.26s". Both were
      the END card's dwell. which_gives_way, right beside it, had the true numbers.

  A2  the END card was placed at `beat − endcard_lead`. assemble_episode.py:139 and
      qc_episode.py both use `beat + endcard_lead`, AND THE ASSEMBLER IS THE ONE THAT
      BUILDS THE FILM. A 3.0s error that fabricated the C23/END overlap which moved
      C23 — it really had a 9.49s window against a 9.0s minimum and fitted where it was.

⚠️ THE FIXTURES ARE SYNTHETIC AND SELF-CONTAINED, on purpose. The real reproduction
needs a 132 KB episode.json, a 19 KB SRT and a Drive mount; a test that needs those runs
nowhere and rots. These build the exact geometry in a temp dir instead.

Run: python engine/test_derive_card_timings.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
TOOL = SCRIPTS / "derive_card_timings.py"

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


# ── fixture ───────────────────────────────────────────────────────────────────
def _ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_episode(root, beats, cards, build=None, srt=None):
    """A minimal episode dir derive_card_timings can run against.

    `beats`  [(n, start, end, framing)]
    `cards`  [{id, beat, cue, layout, items}]  -> items becomes that many chips
    `srt`    [(start, end, text)] — a cue phrase placed FIRST in its block starts at
             that block's start, because word_timeline interpolates by character offset.
    """
    root = pathlib.Path(root)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "renders").mkdir(parents=True, exist_ok=True)

    shots = [{"shot": n, "start": s, "end": e, "framing": f, "first_words": f"beat {n}"}
             for n, s, e, f in beats]
    (root / "renders/shot-map.json").write_text(json.dumps(shots, indent=1), encoding="utf-8")

    blocks = []
    for i, (s, e, text) in enumerate(srt or [], start=1):
        blocks.append(f"{i}\n{_ts(s)} --> {_ts(e)}\n{text}\n")
    (root / "renders/aligned.srt").write_text("\n".join(blocks), encoding="utf-8-sig")

    epj = {
        "episode": "EPTEST",
        "beats": [{"n": n, "framing": f, "card": None, "broll": None, "line": f"beat {n}"}
                  for n, s, e, f in beats],
        "cards": [{"id": c["id"], "beat": c["beat"], "cue": c.get("cue"),
                   "layout": c.get("layout", "fullscreen"),
                   "block": "chips",
                   "content": {"chips": [{"label": f"L{i}", "value": f"{i}"}
                                         for i in range(c.get("items", 2))]}}
                  for c in cards],
        "broll": [],
        "build": {"default_hold": 10.0, "hero_hold": 12.0, "min_card_hold": 10.0,
                  "endcard_beat": 5, "endcard_lead": 1.5,
                  "warranty_tail": 6.7, "warranty_lead": 0.3, "title_head": 0.0,
                  "standing": {"title": "TITLE", "endcard": "END", "warranty": "WARRANTY"},
                  "holds": {}, "broll_offsets": {},
                  # a complete episode, so an unrelated rule cannot mask the one on trial
                  "midroll": {"ask": ["second beat words", "while here"]}},
    }
    if build:
        epj["build"].update(build)
    (root / "docs/episode.json").write_text(json.dumps(epj, indent=2), encoding="utf-8")
    return root


def run(root, *args):
    r = subprocess.run([sys.executable, str(TOOL), str(root), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


# ══ A1 — the flag must name the numbers of the card that GIVES WAY ════════════
# CA is still up when CB arrives, so CA gives way (CB's entry is cue-fixed).
# CB's beat is deliberately TOO SHORT for CB, so the old message shouted
# "beat 3 ... DOES NOT FIT AT ANY CUE POSITION" — about the wrong card entirely.
print("\nA1 — the card-card flag describes the card that gives way")

with tempfile.TemporaryDirectory() as td:
    root = build_episode(
        td,
        beats=[(1, 0.35, 10.0, "MCU"), (2, 10.0, 25.0, "WIDE"), (3, 25.0, 33.0, "MCU"),
               (4, 33.0, 48.0, "MCU"), (5, 48.0, 63.0, "MCU")],
        cards=[{"id": "CA", "beat": 2, "cue": "alpha cue phrase", "items": 2},
               {"id": "CB", "beat": 3, "cue": "bravo cue phrase", "items": 2}],
        srt=[(0.35, 10.0, "opening words for the first beat of this test episode"),
             (10.0, 24.0, "second beat words carry on for a while here"),
             (24.0, 25.0, "alpha cue phrase"),
             (25.0, 30.0, "third beat words run along here too"),
             (30.0, 33.0, "bravo cue phrase"),
             (33.0, 48.0, "fourth beat words"),
             (48.0, 63.0, "fifth beat words the outro")])
    out = run(root)

    check("the fixture really does produce a CARD-CARD overlap",
          "CARD-CARD overlap CA/CB" in out, out[-700:])
    check("CA is named as the card that gives way", "CA IS THE ONE THAT GIVES WAY" in out)
    # THE REGRESSION. CB's beat is 8.0s and CB needs 13.0s, so the buggy build printed
    # "beat 3 is 8.00s and this card needs 13.00s ... DOES NOT FIT AT ANY CUE POSITION"
    # while blaming CA. CA's own beat is 15.0s and fits.
    line = next((l for l in out.splitlines() if "CARD-CARD overlap CA/CB" in l), "")
    check("the message does NOT describe CB's beat as 'this card'",
          "beat 3 is" not in line,
          f"still names the second card's beat: {line.strip()[:200]}")
    check("if it names a beat at all, it is CA's",
          ("beat 2 is" in line) or ("beat" not in line.split("overlap")[-1].split("—")[0]),
          f"line: {line.strip()[:200]}")
    check("the true numbers are still there (which_gives_way)",
          "it has" in out and "needs" in out)


# ══ A2 — the end card sits where the ASSEMBLER puts it ════════════════════════
# endcard_beat 5 starts at 48.0 with endcard_lead 1.5.
#     assembler & QC:  48.0 + 1.5 = 49.5      <- the film
#     derive (buggy):  48.0 - 1.5 = 46.5      <- 3.0s early, invents overlaps
# CC exits at 47.0 — inside that 3.0s gap. It genuinely fits; the bug says it does not.
print("\nA2 — the end card is placed where the assembler puts it")

with tempfile.TemporaryDirectory() as td:
    root = build_episode(
        td,
        beats=[(1, 0.35, 10.0, "MCU"), (2, 10.0, 25.0, "WIDE"), (3, 25.0, 33.0, "MCU"),
               (4, 33.0, 48.0, "MCU"), (5, 48.0, 63.0, "MCU")],
        cards=[{"id": "CC", "beat": 4, "cue": "charlie cue phrase", "items": 2}],
        srt=[(0.35, 10.0, "opening words for the first beat of this test episode"),
             (10.0, 25.0, "second beat words carry on for a while here"),
             (25.0, 33.0, "third beat words run along here too"),
             (33.0, 34.0, "fourth beat opens"),
             (34.0, 48.0, "charlie cue phrase and then some more words after it"),
             (48.0, 63.0, "fifth beat words the outro")])
    out = run(root)

    end_line = next((l for l in out.splitlines() if l.strip().startswith("END ")), "")
    check("END is placed at beat + endcard_lead (49.50), not beat - lead (46.50)",
          "49.50" in end_line and "46.50" not in end_line,
          f"END line: {end_line.strip()!r}")
    check("the label says + endcard_lead", "+ endcard_lead" in end_line,
          f"END line: {end_line.strip()!r}")
    # THE REGRESSION JODIE ASKED FOR: no phantom overlap on a card that genuinely fits.
    check("NO phantom CC/END overlap — CC exits 47.0, the end card lands 49.5",
          "CARD-CARD overlap CC/END" not in out,
          "the 3.0s error is back: a fitting card is being called an overlap")
    check("and the run is clean", "ALL CHECKS PASS" in out, out[-700:])

# The same geometry with the card genuinely overrunning MUST still be caught.
with tempfile.TemporaryDirectory() as td:
    root = build_episode(
        td,
        beats=[(1, 0.35, 10.0, "MCU"), (2, 10.0, 25.0, "WIDE"), (3, 25.0, 33.0, "MCU"),
               (4, 33.0, 48.0, "MCU"), (5, 48.0, 63.0, "MCU")],
        cards=[{"id": "CC", "beat": 4, "cue": "charlie cue phrase", "items": 2}],
        srt=[(0.35, 10.0, "opening words for the first beat of this test episode"),
             (10.0, 25.0, "second beat words carry on for a while here"),
             (25.0, 33.0, "third beat words run along here too"),
             (33.0, 41.0, "fourth beat opens and runs on for a good while yet"),
             (41.0, 48.0, "charlie cue phrase and then some more words after it"),
             (48.0, 63.0, "fifth beat words the outro")])
    out = run(root)
    check("a card that REALLY runs into the end card is still caught",
          "CARD-CARD overlap CC/END" in out,
          "fixing the position must not blind the check")

# ══ A3 — "card over Gordon's face" applies itself ════════════════════════════
# A panel-push card whose window crosses into an MCU beat. WIDE is the only lawful
# answer and the tool already knows which beats — it used to halt so somebody could
# retype it. TWO of EP23's four halts were this.
print("\nA3 — the WIDE fix applies itself instead of halting")

WIDE_BEATS = [(1, 0.35, 10.0, "MCU"), (2, 10.0, 25.0, "WIDE"), (3, 25.0, 40.0, "MCU"),
              (4, 40.0, 48.0, "MCU"), (5, 48.0, 63.0, "MCU")]
WIDE_SRT = [(0.35, 10.0, "opening words for the first beat of this test episode"),
            (10.0, 20.0, "second beat words carry on for a while here"),
            (20.0, 25.0, "delta cue phrase and more words after it"),
            (25.0, 40.0, "third beat words run along here too"),
            (40.0, 48.0, "fourth beat words"),
            (48.0, 63.0, "fifth beat words the outro")]
# CD enters 23.0, holds 10.0 -> exits 33.0: spans beat 2 (WIDE, ok) and beat 3 (MCU, bad)
WIDE_CARDS = [{"id": "CD", "beat": 2, "cue": "delta cue phrase", "items": 2,
               "layout": "panel-push"}]

with tempfile.TemporaryDirectory() as td:
    root = build_episode(td, beats=WIDE_BEATS, cards=WIDE_CARDS, srt=WIDE_SRT,
                         # the ask sits in beat 1 so the chip clears CD's window entirely —
                         # this fixture is on trial for framing, nothing else
                         build={"midroll": {"ask": ["opening words", "test episode"]}})
    out = run(root)                                   # no flag -> the old behaviour
    check("without --apply-wide it still reports the problem",
          "SHOT PLAN CD" in out and "beats [3]" in out, out[-500:])

with tempfile.TemporaryDirectory() as td:
    root = build_episode(td, beats=WIDE_BEATS, cards=WIDE_CARDS, srt=WIDE_SRT,
                         # the ask sits in beat 1 so the chip clears CD's window entirely —
                         # this fixture is on trial for framing, nothing else
                         build={"midroll": {"ask": ["opening words", "test episode"]}})
    out = run(root, "--apply-wide")
    check("with --apply-wide it does NOT halt on it", "SHOT PLAN CD" not in out, out[-600:])
    check("it says which beat it changed and why",
          "beats[3].framing = WIDE" in out and "CD" in out, out[-600:])
    check("it re-derives after applying", "re-deriving" in out)
    check("and the run then passes", "ALL CHECKS PASS" in out, out[-500:])
    epj = json.loads((pathlib.Path(root) / "docs/episode.json").read_text(encoding="utf-8"))
    got = {b["n"]: b["framing"] for b in epj["beats"]}
    check("beat 3 is WIDE on disk", got[3] == "WIDE", str(got))
    check("it widened ONLY what was needed — beat 4 is untouched", got[4] == "MCU", str(got))
    check("and beat 1 is untouched", got[1] == "MCU", str(got))

# 🔒 IT MUST NOT SILENCE THE HALT THAT IS A REAL DECISION.
with tempfile.TemporaryDirectory() as td:
    root = build_episode(
        td,
        beats=[(1, 0.35, 10.0, "MCU"), (2, 10.0, 25.0, "WIDE"), (3, 25.0, 33.0, "MCU"),
               (4, 33.0, 48.0, "MCU"), (5, 48.0, 63.0, "MCU")],
        cards=[{"id": "CA", "beat": 2, "cue": "alpha cue phrase", "items": 2},
               {"id": "CB", "beat": 3, "cue": "bravo cue phrase", "items": 2}],
        srt=[(0.35, 10.0, "opening words for the first beat of this test episode"),
             (10.0, 24.0, "second beat words carry on for a while here"),
             (24.0, 25.0, "alpha cue phrase"),
             (25.0, 30.0, "third beat words run along here too"),
             (30.0, 33.0, "bravo cue phrase"),
             (33.0, 48.0, "fourth beat words"),
             (48.0, 63.0, "fifth beat words the outro")])
    out = run(root, "--apply-wide")
    check("a genuine card-card overlap STILL halts under --apply-wide",
          "CARD-CARD overlap CA/CB" in out and "PROBLEM(S)" in out,
          "auto-applying the mechanical fix must not wave through a decision")

print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
