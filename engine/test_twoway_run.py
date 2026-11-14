"""twoway_run: works out where an episode is from disk, runs the code steps, stops only at gates.

    python engine/test_twoway_run.py            sandbox + read-only checks
    python engine/test_twoway_run.py --live     + list HeyGen (read only) and resolve EP56's two titles
    python engine/test_twoway_run.py --clip     + put a sandbox script on the REAL clipboard and read it back

THE SANDBOX RUN: EP56's article, renumbered as a fake EP57 in a temp PP root (the runner hands
its root to every tool through PP_VIDEOS_DIR, so nothing reaches the real Drive). Driven by the
real `advance()`:
  · Stage 1 runs by itself — folder, split, episode.json, the web-address substitutions DRAFTED
    BY THE STANDING RULE (must equal EP56's four, which Jodie ruled by hand), then STOPS at the
    words gate; a DRAFT words file does not pass it; the APPROVED one is copied in and the scripts
    are composed — and they must equal the two scripts pasted into HeyGen for EP56, byte for byte.
  · a fresh Ep object (a "restart") resumes at the same step, from disk alone;
  · Stage 2 stops for the session (the commission) and, given EP56's, plans and moves on;
  · Stage 3 writes the render sheet (template NAMES, no ids, "clear the box first") and STOPS at
    the paste gate; a recorded verdict moves it to the b-roll session step.
CONTROLS: a SINGLE-format row is refused; a verdict with an OPEN change does not pass its gate;
an exact-title match never takes PP-EP5 for PP-EP57; two finished renders with one title stop
for Jodie. REAL EP56 (read only): every upstream step is recognised as done, and nothing on disk
changes.
"""
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_run as tr   # noqa: E402

REAL = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
EP56 = next(REAL.glob("PP-EP56-*"))
URL56 = ("https://practicalpunting.com.au/pp-online/a-z-of-betting/form-analysis/"
         "range-of-form-analysis-techniques/class-improvement-and-bias-blues-part-3-20040108")
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


# ── 0. real EP56, read only ─────────────────────────────────────────────────────
print("-- 0. real EP56, read only --")
snap = {p: p.stat().st_mtime for p in (EP56 / "docs").iterdir() if p.is_file()}
ep = tr.Ep(56, rail_row={"id": "x", "ep_number": 56, "format": "two-way", "status": "published",
                         "source_url": URL56}, offline=True)
w = tr.where(ep)
check("EP56 (built before the runner): every Stage-1 step recognised as done; next is the "
      "runner's own plan marker", w == (2, "plan", "code"), str(w))
check("  and nothing in EP56's docs changed", snap == {p: p.stat().st_mtime for p in snap})
check("folder names: EP56's real folder is what the rule makes",
      tr.folder_name(56, URL56) == EP56.name, tr.folder_name(56, URL56))
turns56 = json.loads((EP56 / "docs/turns.json").read_text(encoding="utf-8"))["turns"]
subs, odd = tr.draft_substitutions(turns56)
real = json.loads((EP56 / "docs/sanctioned-substitutions.json").read_text(encoding="utf-8"))["substitutions"]
check("the standing rule drafts EXACTLY EP56's four hand-ruled substitutions (turn, find, scope)",
      [(s["turn"], s["find"], s.get("scope")) for s in subs]
      == [(s["turn"], s["find"], s.get("scope")) for s in real] and not odd)
_, odd2 = tr.draft_substitutions([{"n": 1, "speaker": "BB", "text": "See it on www.example.com.au."}])
check("CONTROL: an address in a shape the rule does not cover is listed for a human",
      len(odd2) == 1, str(odd2))

# ── 1. the sandbox: EP56's article as a fake EP57 ───────────────────────────────
print("\n-- 1. sandbox stage 1 --")
SAND = pathlib.Path(tempfile.mkdtemp(prefix="twoway_run_"))
(SAND / "docs/two-way-words-drafts").mkdir(parents=True)
cap = next((REAL / "docs").glob("EP56-source-article-*.md"))
shutil.copy2(cap, SAND / "docs" / cap.name.replace("EP56", "EP57"))
row = {"id": "t", "ep_number": 57, "format": "two-way", "status": "queued", "source_url": URL56}

refused = False
try:
    tr.do_folder(tr.Ep(57, pp=SAND, rail_row=dict(row, format="single"), offline=True))
except tr.Stop as s:
    refused = "SINGLE" in s.message
check("CONTROL: a single-presenter row is refused (nothing made)",
      refused and not list(SAND.glob("PP-EP57*")))

ep = tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True)
s = tr.advance(ep)
check("stage 1 runs by itself and STOPS at the words gate", s and s.kind == "gate" and s.gate == "words",
      f"{s.kind if s else None} {s.step if s else ''}")
d = ep.dir
check("  the folder has EP55/EP56's layout", d is not None and all((d / x).is_dir() for x in tr.SUBFOLDERS))
check("  turns.json equals EP56's (the splitter, run by the runner)",
      json.loads((d / "docs/turns.json").read_text(encoding="utf-8"))["turns"] == turns56)
check("  episode.json carries the standing readers",
      json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))["speakers"]["BM"]["reader"] == "Steve")
drafted = json.loads((d / "docs/sanctioned-substitutions.json").read_text(encoding="utf-8"))["substitutions"]
check("  the substitutions were drafted by the standing rule (EP56's four)",
      [x["find"] for x in drafted] == [x["find"] for x in real])

appr = (EP56 / "docs/EP56-new-words-APPROVED.md").read_text(encoding="utf-8")
draft_f = SAND / "docs/two-way-words-drafts/Fundamentals-Part-3-new-words-APPROVED.md"
draft_f.write_text(appr.replace("Status: APPROVED", "Status: DRAFT"), encoding="utf-8")
s = tr.advance(tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True))
check("CONTROL: a words file whose Status is DRAFT does not pass the gate",
      s and s.gate == "words" and not (d / "docs/EP57-new-words-APPROVED.md").exists())
draft_f.write_text(appr, encoding="utf-8")
s = tr.advance(tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True))
check("the APPROVED words are handed over into the episode as EP57-new-words-APPROVED.md",
      (d / "docs/EP57-new-words-APPROVED.md").read_text(encoding="utf-8") == appr)
for code in ("BB", "BM"):
    check(f"  the composed {code} script == EP56's pasted one, byte for byte",
          (d / f"docs/spoken-words-{code}.txt").read_text(encoding="utf-8")
          == (EP56 / f"docs/spoken-words-{code}.txt").read_text(encoding="utf-8"))
check("  and the RENDER GATE opens straight away, at the words (the locked order — Jodie, 13 Nov)",
      s and s.kind == "gate" and s.gate == "render_paste", f"{s.kind if s else None} {s.step if s else ''}")
check("a fresh Ep (a restart) resumes at the same step, from disk alone",
      tr.where(tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True)) == (3, "render_paste", "gate"))
sheet = (d / "docs/HEYGEN-RENDER-EP57.md")
txt = sheet.read_text(encoding="utf-8") if sheet.is_file() else ""
check("  the render sheet names both templates, both titles, 'Clear the box first' and the midroll line",
      "Gordon two-way small" in txt and "Barry test 2 small" in txt and "PP-EP57-BB-full" in txt
      and "Clear the box first" in txt and "pool line" in txt)
check("  and carries NO HeyGen id (no 32-hex string)", not re.search(r"\b[0-9a-f]{32}\b", txt))
ep = tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True)
tr.record_verdict(ep, "render_paste", "approved", "both are generating", [])
s = tr.advance(ep)
check("a recorded paste verdict moves it on to the commission (built BEHIND the renders)",
      s and s.kind == "session" and s.step == "commission", f"{s.kind if s else None} {s.step if s else ''}")

# ── 2. stage 2 behind the renders ────────────────────────────────────────────────
print("\n-- 2. the plan, behind the renders --")
e56 = json.loads((EP56 / "docs/episode.json").read_text(encoding="utf-8"))
e57 = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
for k in ("beats", "cards", "broll", "turn_signals", "shape", "packaging", "cover", "title_card", "ebook"):
    if k in e56:
        e57[k] = e56[k]
(d / "docs/episode.json").write_text(json.dumps(e57, indent=1, ensure_ascii=False), encoding="utf-8")
s = tr.advance(tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True))
# EP56's commission ENDED with 4 b-roll slots (three numbered racing clips were removed on
# Jodie's ruling) — the rule is 6–8, so the plan step must send it back to the session.
check("REAL FINDING: EP56's final commission (4 b-roll slots) is sent back to the session at the plan",
      s and s.kind == "session" and s.step == "plan" and "b-roll slots" in s.message,
      f"{s.kind if s else None} {s.step if s else ''}: {(s.message if s else '')[:160]}")
# The session would fix the commission; the test stands in for that and records the plan as done.
tr._write_json(d / "output/run/plan-ok.json",
               {"episode_json_md5": tr._md5(d / "docs/episode.json"), "at": "test"})
ep = tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True)
s = tr.advance(ep)
check("with the plan done, it moves on to the b-roll SESSION step",
      s and s.kind == "session" and s.step == "broll_generate", f"{s.kind if s else None} {s.step if s else ''}"
      + (f": {s.message[:300]}" if s and s.kind == "fault" else ""))
# THE MEASURED PLAN SUPERSEDES THE ESTIMATE (14 Nov 2026): a later write to episode.json (the replan,
# card timing) staled plan-ok's md5, and a resume would have re-run the estimate plan over the
# measured one. CONTROL first: before any replan, an edited episode.json DOES re-open the plan.
ep = tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True)
e57 = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
e57.setdefault("build", {})["_touched_by_test"] = True
(d / "docs/episode.json").write_text(json.dumps(e57, indent=1, ensure_ascii=False), encoding="utf-8")
check("CONTROL: before any replan, an edited episode.json re-opens the estimate plan",
      not tr.step_plan_ok(ep))
tr._write_json(d / "output/run/replan.json", {"timeline_md5": "x", "at": "test"})
check("once the measured replan has written its record, the estimate plan is never re-run over it",
      tr.step_plan_ok(ep))
(d / "output/run/replan.json").unlink()
# THE E-BOOK'S KEYS DO NOT RE-TIME THE CARDS (EP57, 14 Nov 2026: writing `ebook` + `figures` after an
# approved cut would have re-rendered every graphic).
tr._write_json(d / "output/run/card-timing.json", {"episode_json_md5": tr._md5(d / "docs/episode.json"),
                                                   "inputs_md5": tr.timing_inputs_md5(ep), "at": "test"})
check("card timing recorded with its inputs fingerprint is done", tr.timing_done(ep))
e57 = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
e57["ebook"], e57["figures"] = {"departures": []}, [{"n": 1, "card": "C1"}]
(d / "docs/episode.json").write_text(json.dumps(e57, indent=2, ensure_ascii=False), encoding="utf-8")
check("writing the e-book's keys (and re-indenting the file) leaves the card timing done", tr.timing_done(ep))
e57["cards"][0]["headline"] = e57["cards"][0]["headline"] + " X"
(d / "docs/episode.json").write_text(json.dumps(e57, indent=1, ensure_ascii=False), encoding="utf-8")
check("CONTROL: a change to a CARD re-opens the card timing", not tr.timing_done(ep))
tr._write_json(d / "output/run/card-timing.json", {"episode_json_md5": tr._md5(d / "docs/episode.json"),
                                                   "at": "old"})
check("a record from before the fingerprint still passes on the whole-file md5", tr.timing_done(ep))
(d / "output/run/card-timing.json").unlink()
tr._write_json(d / "output/run/plan-ok.json",
               {"episode_json_md5": tr._md5(d / "docs/episode.json"), "at": "test"})

# ── 3. verdicts: split, and a change keeps the gate shut ─────────────────────────
print("\n-- 3. verdicts --")
(d / "output/PP-EP57-cut1.mp4").write_bytes(b"x")
v = tr.record_verdict(ep, "cut_watch", "changes", "Lovely, but two things",
                      ["the C8 card sits under the logo", "a pause before the close"])
check("a verdict with changes is ONE line plus each change as its OWN OPEN item",
      v["words"] == "Lovely, but two things" and [c["status"] for c in v["changes"]] == ["OPEN", "OPEN"])
check("CONTROL: with changes OPEN, the cut-watch gate is not passed", not ep.passed("cut_watch", 1))
check("  and a new cut is not wanted while a change is OPEN", not tr.cut_needed(ep))
g = ep.gates()
for c in g["cut_watch#1"]["changes"]:
    c["status"] = "DONE"
ep.save_gates(g)
check("once every change is DONE/DROPPED, the next cut is wanted", tr.cut_needed(ep))
v = tr.record_verdict(ep, "broll_cover", "approved", "EP57: C1 C3 C4 · cover B", [])
check("b-roll picks are read out of her line", v["picks"] == ["C1", "C3", "C4", "cover B"], str(v["picks"]))
_done = {s[1]: s[3] for s in tr.STEPS}
check("once her b-roll picks are in, the per-episode review page is not remade (no page on disk)",
      _done["broll_page"](ep) and not (d / "output/review/broll-review.html").exists())

# ── 4. render matching ───────────────────────────────────────────────────────────
print("\n-- 4. finding a finished render by EXACT title --")
vids = [{"video_title": "PP-EP5-BB-full", "status": "completed", "video_id": "a"},
        {"video_title": "PP-EP57-BB-full ", "status": "completed", "video_id": "b"},
        {"video_title": "PP-EP57-BM-full", "status": "processing", "video_id": "c"}]
check("exact title only: PP-EP5 is never taken for PP-EP57",
      [x["video_id"] for x in tr.find_finished(vids, "PP-EP57-BB-full")[1]] == ["b"])
check("a render still processing is found but not finished",
      [len(x) for x in tr.find_finished(vids, "PP-EP57-BM-full")] == [1, 0])
check("CONTROL: two finished renders with one title are both returned (the runner then asks)",
      len(tr.find_finished(vids + [dict(vids[1], video_id="d")], "PP-EP57-BB-full")[1]) == 2)
if "--live" in sys.argv:
    live = tr.heygen_list()
    rec = json.loads((EP56 / "renders/heygen-renders.json").read_text(encoding="utf-8"))["renders"]
    for title, r in rec.items():
        got = tr.find_finished(live, title)[1]
        check(f"LIVE (read only): {title} resolves to the id recorded on 11 Nov",
              [x["video_id"] for x in got] == [r["video_id"]], str([x["video_id"] for x in got]))

# ── 5. the clipboard ─────────────────────────────────────────────────────────────
if "--clip" in sys.argv:
    print("\n-- 5. the clipboard (REAL clipboard) --")
    ep = tr.Ep(57, pp=SAND, rail_row=dict(row), offline=True)
    g = ep.gates()
    g.get("render_paste", {}).pop("clipped", None)
    ep.save_gates(g)
    msg = tr.clip_next([ep])
    import subprocess
    back = subprocess.run(["powershell", "-NoProfile", "-Command",
                           "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"],
                          capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
    bb = (d / "docs/spoken-words-BB.txt").read_text(encoding="utf-8")
    check("the clipboard holds Gordon's script and NOTHING else",
          back.replace("\r\n", "\n").strip() == bb.strip() and "Gordon two-way small" in msg, msg[:120])
    msg2 = tr.clip_next([ep])
    back2 = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"],
                           capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
    check("the next --clip puts Steve's script up instead (one at a time)",
          back2.replace("\r\n", "\n").strip() == (d / "docs/spoken-words-BM.txt").read_text(
              encoding="utf-8").strip() and "Barry test 2 small" in msg2)
    check("a third --clip says they have all been given", "already" in tr.clip_next([ep]))

shutil.rmtree(SAND, ignore_errors=True)
print(f"\ntwo-way runner: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
