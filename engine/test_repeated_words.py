"""repeated_words.repeated_runs: FAIL on a run of 3+ words heard more often than the script says it.

Built on EP56's real fault (Jodie, 13 Nov 2026): Gordon's open said "This is part three of a
conversation that", paused, and said the whole sentence again. The words below are EP56's own
script and EP56's own transcriber output, so the controls are the real shapes, not inventions.

  (a) CONTROL — the false start as `small.en` / stretch-by-stretch heard it -> FAILS, at 0.00s.
  (b) the 12 Nov `base.en` whole-file transcript of the SAME audio (the repeat folded away) -> no
      repeat. Recorded on purpose: it is WHY the old checks passed — the detector can only judge
      what the transcriber heard, which is why `transcribe()` splits at the pauses.
  (c) the clean take -> PASS.
  (d) a phrase the SCRIPT itself says twice, heard twice -> PASS (counted against the script).
  (e) CONTROL — a whole sentence read again much later (Steve-reads-Gordon's-script shape) -> FAILS.
  (f) a two-word stutter ("the the") -> PASS: below RUN_N on purpose (Jodie kept Steve's "T-").
  (g) CONTROL — a repeat with a figure in it ("part 3" / "part three") is still caught: both sides fold.
  (h) script_tokens drops break tags and folds figures like the SRT step.

Run: python engine/test_repeated_words.py
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import repeated_words as rw  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def heard(text, t0=0.0, step=0.3):
    return [(t, round(t0 + i * step, 2)) for i, t in enumerate(rw.tokens(text))]


SCRIPT = ("This is part three of a conversation that ran in Practical Punting at the start of two thousand "
          "and four. On one side, the magazine's editor, Brian Blackwell. On the other, Barry Meadow, the "
          "American professional.\n\n<break time=\"6s\"/>\n\nI have to admit I've never been a breeding buff.")
S = rw.script_tokens(SCRIPT)

print("\n-- (a) CONTROL: EP56's false start, as heard stretch by stretch --")
h = heard("This is part three of a conversation that") + heard(
    "This is part three of a conversation that ran in Practical Punting at the start of 2004. "
    "On one side, the magazine's editor, Brian Blackwell.", t0=3.28)
r = rw.repeated_runs(h, S)
check(len(r) == 1, "one repeated run is found", r)
check(r and r[0]["at_s"] == 0.0 and r[0]["text"].startswith("this is part three of a conversation"),
      "it is the false start, at 0.00s", r and r[0]["text"])
check(r and r[0]["occurrences_s"] == [0.0, 3.28], "both takes are located (0.00s and 3.28s)",
      r and r[0]["occurrences_s"])

print("\n-- (b) the 12 Nov base.en transcript of the same audio: the repeat was never heard --")
b = [("this", 0.0), ("is", 0.44), ("part", 0.62), ("three", 0.82), ("of", 1.34), ("a", 1.64),
     ("conversation", 1.72), ("that", 2.16), ("ran", 2.64), ("in", 3.48)] + heard(
    "Practical Punting at the start of 2004. On one side, the magazine's editor, Brian Blackwell.", t0=5.56)
check(rw.repeated_runs(b, S) == [], "no repeat — the transcript had folded it away (why the old checks passed)")

print("\n-- (c) the clean take --")
check(rw.repeated_runs(heard(SCRIPT.replace('<break time="6s"/>', "")), S) == [], "the script as read: PASS")

print("\n-- (d) a phrase the script itself repeats --")
s2 = "Barry goes first this time. I'll read Brian's side. Barry goes first this time."
check(rw.repeated_runs(heard(s2), rw.script_tokens(s2)) == [], "said twice, scripted twice: PASS")

print("\n-- (e) CONTROL: a sentence read again much later --")
h = heard(SCRIPT.replace('<break time="6s"/>', "")) + heard("On the other, Barry Meadow, the American professional.",
                                                            t0=240.0)
r = rw.repeated_runs(h, S)
check(len(r) == 1 and "barry meadow the american professional" in r[0]["text"], "FAILS on the late repeat",
      r and r[0]["text"])
check(r and r[0]["occurrences_s"][-1] == 240.0, "and locates the second reading at 240s", r and r[0]["occurrences_s"])

print("\n-- (f) a two-word stutter is below the bar --")
h = heard("On one side, the the magazine's editor, Brian Blackwell.")
check(rw.repeated_runs(h, S) == [], "'the the' is not a repeated RUN (RUN_N = 3)")

print("\n-- (g) CONTROL: a figure on one side, words on the other --")
h = heard("This is part 3 of a conversation. This is part three of a conversation that ran in Practical Punting")
r = rw.repeated_runs(h, S)
check(len(r) == 1, "'part 3' and 'part three' fold to one phrase, so the repeat is caught", r)

print("\n-- (h) script folding --")
check("break" not in S and "time" not in S, "break tags are not script words")
fs = rw.script_tokens("at the start of 2004.")
check(not any(t.isdigit() for t in fs) and "thousand" in fs, "figures read as words (the SRT step's own fold)", fs)

print("\n-- (i) a phrase the script says twice, MISHEARD the same way both times (EP56, real) --")
s3 = ("I get some nagging flutters. When the flutters come, I know I'm not happy. That's me for now. "
      "When the flutters come, listen to them, and I'll see you next time.")
h = heard("I get some nagging flutters. When the flood has come, I know I'm not happy. That's me for now. "
          "When the flood has come, listen to them, and I'll see you next time.")
check(rw.repeated_runs(h, rw.script_tokens(s3)) == [], "'when the flood has come' x2 for scripted 'flutters' x2: PASS")

print("\n-- (j) figures spelled differently by the transcriber, twice (EP56 Steve, real) --")
s4 = ("A sire with a one hundred thousand dollars fee. A five hundred thousand dollars yearling. "
      "Collapses at anything over twelve hundred metres. Won a twelve hundred metres race.")
h = heard("A sire with a one hundred dollars zero fee. A five hundred dollars zero yearling. "
          "Collapses at anything over one thousand two hundred meters. Won a one thousand two hundred meters race.")
check(rw.repeated_runs(h, rw.script_tokens(s4)) == [], "'hundred dollars zero' / 'meters' spellings: PASS")

print("\n-- (k) REAL: the three EP56 master transcripts saved by the 13 Nov run --")
EPD = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP56-Class-Improvement-and-Bias-Blues-Part-3")
for name, code, want in (("BB-master-cut2", "BB", "this is part three"), ("BB-master-cut3", "BB", None),
                         ("BM-master", "BM", None)):
    f = EPD / f"output/qc/cut3/repeats-{name}.json"
    if not f.is_file():
        print(f"  SKIP  {name} — {f.name} not on this machine")
        continue
    import json
    j = json.loads(f.read_text(encoding="utf-8"))
    sc = rw.script_tokens((EPD / f"docs/spoken-words-{code}.txt").read_text(encoding="utf-8"))
    for p in ("stretches", "whole"):
        r = rw.repeated_runs([(t, s) for t, s in j["passes"][p]["words"]], sc)
        if want:
            if p == "stretches":
                check(len(r) == 1 and r[0]["text"].startswith(want) and r[0]["at_s"] < 0.5,
                      f"CONTROL: {name} ({p}) FAILS on the false start at 0.0s, and only that",
                      [(x["at_s"], x["text"][:50]) for x in r])
        else:
            check(r == [], f"{name} ({p}): no repeat", [(x["at_s"], x["text"][:50]) for x in r])

print()
if fails:
    print(f"FAILED {len(fails)}: {fails}")
    raise SystemExit(1)
print("ALL PASS")
