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


print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
