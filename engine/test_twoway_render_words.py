"""twoway_render_words: find what in a render is not the script, and cut only inside pauses.

    python engine/test_twoway_render_words.py                fast: the pure analysis, synthetic
    python engine/test_twoway_render_words.py --slow         + EP56's four real files (~20 min)

REAL DATA (--slow, EP56, 11–13 Nov 2026 — the three faults the old checks missed):
  · Steve's ORIGINAL render: the false start at the head AND the paste accident (Gordon's
    script and the render sheet read after his own) → both found; the proposed keep range
    lands within 0.35s of the hand-made master (3.56–243.24s).
  · Gordon's ORIGINAL render: the false start and the 24s of unscripted words → both found,
    the stray classed BETWEEN sentences; keeps within 0.35s of the hand cut (3.00–56.00,
    80.88–end).
  · Both shipped MASTERS → PASS (the controls the other way: a clean file is not flagged).
FIXTURES attack the classification: a stray inside a sentence must NOT be cut; a lost chunk
must be reported; a transcriber's mishearing (a substitution in place) must not count.
"""
import json
import os
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_render_words as trw   # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def heard_from(words, start=0.0, gap=0.3, pauses=None):
    """[(token, start, end)] — 0.3s per word, with extra pauses after given indices."""
    out, t = [], start
    for i, w in enumerate(words):
        out.append((w, t, t + 0.25))
        t += gap + (pauses or {}).get(i, 0.0)
    return out


SCRIPT = ("The first sentence is here. The second one follows it. "
          "<break time=\"6s\"/> A third sentence after the break. And the last one ends it.")
toks, ends = trw.script_with_sentence_ends(SCRIPT)
check("the script tokenises with sentence ends marked", ends.count(True) == 4, str(ends))

# clean
h = heard_from(toks, pauses={9: 6.0})
r = trw.analyse(h, toks, ends, h[-1][2] + 0.4)
check("a render that is just the script → ok, keeps everything", r["ok"] and len(r["keep_s"]) == 1,
      json.dumps(r["keep_s"]))

# a false start at the head
fs = ["the", "first", "sentence"]
h = heard_from(fs + toks, pauses={2: 0.7, 11: 6.0})
r = trw.analyse(h, toks, ends, h[-1][2] + 0.4)
s = r["stray"][0] if r["stray"] else {}
check("a false start is a HEAD stray and is cut", s.get("where") == "head" and r["keep_s"][0][0] > 0.8,
      json.dumps(r["stray"])[:200])

# words between two sentences, in a pause
mid = ["nothing", "quite", "like", "a", "big", "race"]
h = heard_from(toks[:5] + mid + toks[5:], pauses={4: 1.0, 10: 1.0, 15: 6.0})
r = trw.analyse(h, toks, ends, h[-1][2] + 0.4)
s = r["stray"][0] if r["stray"] else {}
check("unscripted words between sentences, in a pause → BETWEEN, cut",
      s.get("where") == "between" and len(r["keep_s"]) == 2, json.dumps(r["stray"])[:200])
check("  and the cut sits inside the pauses, never in a kept word",
      all(not (a < w[1] < b or a < w[2] < b) for a, b in [s.get("cut", [0, 0])]
          for w in h[:5] + h[11:]))

# CONTROL: the same words INSIDE a sentence → mid, NOT cut, Jodie's call
h = heard_from(toks[:2] + mid + toks[2:], pauses={14: 6.0})
r = trw.analyse(h, toks, ends, h[-1][2] + 0.4)
s = r["stray"][0] if r["stray"] else {}
check("CONTROL: the same stray INSIDE a sentence → MID, not cut, a question for Jodie",
      s.get("where") == "mid" and "cut" not in s and r["needs_jodie"], json.dumps(r["stray"])[:200])

# the wrong script read after his own (the paste accident)
other = "small detour then we are done with it if this video is landing".split()
h = heard_from(toks + other, pauses={9: 6.0, len(toks) - 1: 2.0})
r = trw.analyse(h, toks, ends, h[-1][2] + 0.4)
s = r["stray"][-1] if r["stray"] else {}
check("another script read after the last word → TAIL, cut", s.get("where") == "tail"
      and r["keep_s"][-1][1] < h[len(toks)][1], json.dumps(r["keep_s"]))

# a lost chunk
h = heard_from(toks[:3] + toks[11:], pauses={})
r = trw.analyse(h, toks, ends, h[-1][2] + 0.4)
check("six+ script words never heard → a LOST chunk, a question for Jodie",
      bool(r["lost"]) and r["needs_jodie"] and not r["ok"], json.dumps(r["lost"])[:160])

# a mishearing is a substitution in place
mis = list(toks)
mis[6:9] = ["the", "sekond", "won"]
h = heard_from(mis, pauses={9: 6.0})
r = trw.analyse(h, toks, ends, h[-1][2] + 0.4)
check("a transcriber's mishearing (substitution in place) is NOT a stray", r["ok"], json.dumps(r["stray"]))

if "--slow" in sys.argv:
    import ep_paths
    PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
    d = ep_paths.episode_dir(56, PP)
    print("\n-- slow: EP56's real renders --")
    for media, script, want_keep in (
            ("PP-EP56-BM-full.mp4", "spoken-words-BM.txt", [[3.56, 243.24]]),
            ("PP-EP56-BB-full.mp4", "spoken-words-BB.txt", [[3.00, 56.00], [80.88, None]])):
        r = trw.check(d / "renders" / media, (d / "docs" / script).read_text(encoding="utf-8"))
        keep = r["keep_s"]
        close = len(keep) == len(want_keep) and all(
            abs(k[0] - w[0]) <= 0.35 and (w[1] is None or abs(k[1] - w[1]) <= 0.35)
            for k, w in zip(keep, want_keep))
        check(f"{media}: the faults are found and the keep ranges match the hand cut ±0.35s",
              not r["ok"] and close, f"tool {keep} vs hand {want_keep}")
    for media, script in (("BM-master.mp4", "spoken-words-BM.txt"),
                          ("BB-master.mp4", "spoken-words-BB.txt")):
        r = trw.check(d / "renders" / media, (d / "docs" / script).read_text(encoding="utf-8"))
        check(f"CONTROL: the shipped {media} PASSES", r["ok"], json.dumps(r["stray"])[:160])

print(f"\nrender words: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
