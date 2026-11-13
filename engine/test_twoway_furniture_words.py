"""twoway_furniture reads the episode's OWN approved words, and the midroll window sees two-ways.

    python engine/test_twoway_furniture_words.py

🔴 THE PROOF IS EP56. Its scripts were composed on 11 Nov by a scratch script
(`compose_ep56.py`) that patched EP49's constants in memory. The tool, fed nothing but
EP56's `EP56-new-words-APPROVED.md`, must now produce the SAME render scripts that were
pasted into HeyGen — byte for byte — and the same manifest.

CONTROLS (each must fail):
  · the code as it was at HEAD~ (EP49 constants) composes a DIFFERENT EP56 script;
  · no approved file, a draft status, a re-voiced midroll, a different close → refused;
  · a sign-off already in the archive → refused (the check now tests the PLACED line);
  · a midroll line inside the nine-episode window → refused (needs the window to see
    the two-ways: EP55 used L5, and before 13 Nov EP55 was invisible to the window);
  · render scripts already on disk that would change → refused without --force.
Read-only on the real Drive: every write goes to a temp sandbox.
"""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(SCRIPTS))

import ep_paths                # noqa: E402
import render_ready as rr      # noqa: E402
import twoway_furniture as tf  # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def refused(label, fn, needle):
    try:
        fn()
        check(label, False, "it composed")
    except (tf.NotComposable, Exception) as e:     # noqa: BLE001
        check(label, needle.lower() in str(e).lower(), str(e)[:120])


ep56 = ep_paths.episode_dir(56, PP)
d56 = ep56 / "docs"

# ── 1. EP56, real data: the tool reproduces what was pasted ─────────────────────
print("-- 1. EP56 from its own approved file --")
built = tf.build(56, PP, write=False)
for name in ("spoken-words-BB.txt", "spoken-words-BM.txt"):
    disk = (d56 / name).read_text(encoding="utf-8")
    check(f"{name} == the file pasted into HeyGen, byte for byte",
          built["out"][name] == disk, f"{len(built['out'][name])} vs {len(disk)} chars")
body = lambda s: "\n".join(ln for ln in s.splitlines() if not ln.startswith("#")).strip()  # noqa: E731
check("furniture-BB.txt pieces == EP56's, word for word (header aside)",
      body(built["out"]["furniture-BB.txt"])
      == body((d56 / "furniture-BB.txt").read_text(encoding="utf-8")))
shipped = json.loads((d56 / "script-manifest-BB.json").read_text(encoding="utf-8"))
mine = json.loads(built["out"]["script-manifest-BB.json"])
key = lambda m: [(s["n"], s["kind"], s["id"], s.get("turn"), s.get("where"), s["words"])  # noqa: E731
                 for s in m["segments"]]
check("the manifest's segments (order, kind, id, turn, where, words) == EP56's",
      key(mine) == key(shipped))
check("the midroll is L7, as approved", mine["midroll_line_id"] == "L7",
      mine["midroll_line_id"])

# ── 2. CONTROL: the old code, with EP49's constants, does NOT give EP56's script ──
print("\n-- 2. CONTROL: the pre-change module --")
old_src = subprocess.run(["git", "-C", str(HERE.parent), "show",
                          "7b5166c:engine/twoway_furniture.py"],
                         capture_output=True, text=True, encoding="utf-8").stdout
check("CONTROL: the pre-change module still holds EP49's open",
      "Right — Barry starts." in old_src)
tmpmod = pathlib.Path(tempfile.mkdtemp(prefix="oldtf_")) / "old_tf.py"
tmpmod.write_text(old_src, encoding="utf-8")
spec = importlib.util.spec_from_file_location("old_tf", tmpmod)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
old.REPO = HERE.parent          # it resolves the pool from its own location; point it home
try:
    old_script = old.build(56, PP, write=False)["script"]
except Exception as e:                                # noqa: BLE001
    old_script = f"(raised {e})"
# The old code goes wrong one of two ways, both recorded 5 Oct (memory
# twoway-furniture-is-ep49-hardcoded): it composes EP49's open into EP56, or its sign-off
# check tests EP49's constant and halts on EP49's own folder. Either is the control.
check("CONTROL: the old code cannot give EP56's pasted script (EP49's words, or it halts on EP49)",
      old_script != (d56 / "spoken-words-BB.txt").read_text(encoding="utf-8")
      and ("Right — Barry starts." in old_script or "problem(s) in the furniture" in old_script),
      old_script[:60])

# ── 3. the refusals, in a sandbox copy of EP56 ──────────────────────────────────
print("\n-- 3. controls in a sandbox --")
sand = pathlib.Path(tempfile.mkdtemp(prefix="tfsand_"))
(sand / "docs").mkdir()
for c in (PP / "docs").glob("EP56-source-article-*.md"):
    shutil.copy2(c, sand / "docs" / c.name)
sdocs = sand / ep56.name / "docs"
sdocs.mkdir(parents=True)
for n in ("turns.json", "episode.json", "sanctioned-substitutions.json",
          "EP56-new-words-APPROVED.md"):
    shutil.copy2(d56 / n, sdocs / n)
appr = (sdocs / "EP56-new-words-APPROVED.md").read_text(encoding="utf-8")


def with_words(text):
    (sdocs / "EP56-new-words-APPROVED.md").write_text(text, encoding="utf-8")
    return lambda: tf.build(56, sand, write=False)


check("the sandbox composes cleanly (no prior episodes, so nothing in the window)",
      tf.build(56, sand, write=False)["out"]["spoken-words-BB.txt"]
      == built["out"]["spoken-words-BB.txt"])
(sdocs / "EP56-new-words-APPROVED.md").unlink()
refused("CONTROL: no approved-words file → refused",
        lambda: tf.build(56, sand, write=False), "not approved yet")
refused("CONTROL: a DRAFT status line → refused",
        with_words(appr.replace("Status: APPROVED", "Status: DRAFT")), "draft is not")
pool = tf.pool_lines()
refused("CONTROL: a midroll re-voiced by one word → refused",
        with_words(appr.replace(pool["L7"], pool["L7"].replace("Small detour", "Quick detour"))),
        "not one of the pool")
refused("CONTROL: a different close → refused (it is Hugh's line)",
        with_words(appr.replace("read by Steve and me.", "read by the two of us.")),
        "standing close")
import re as _re  # noqa: E402
# Cowork's batch files (Parts 4-6) carry a bare "## 4. MIDROLL" heading and the line
# "midroll: from the pool" — no line id anywhere, because the numbers did not exist yet.
batch = _re.sub(r"## 4\. MIDROLL[^\n]*\n[^\n]+", "## 4. MIDROLL\nmidroll: from the pool", appr, count=1)
(sdocs / "EP56-new-words-APPROVED.md").write_text(batch, encoding="utf-8")
b = tf.build(56, sand, write=False)
mid = next(s for s in b["manifest"] if s["id"] == "midroll")
drawn, _t = tf.pool_line(56, sand)
check("a batch's bare 'midroll: from the pool' composes with the pool's OWN draw (no id given)",
      "## 4. MIDROLL\nmidroll: from the pool" in batch and "L7" not in batch.split("## 4.")[1].split("## 5.")[0]
      and mid["provenance"].endswith("the pool's draw (the line unused longest)")
      and mid["name"].endswith(drawn), f"{mid['name']} / {mid['provenance']}")
(sdocs / "EP56-new-words-APPROVED.md").write_text(appr, encoding="utf-8")

# the sign-off archive check now tests the PLACED line
ep55_bb = (ep_paths.episode_dir(55, PP) / "docs/spoken-words-BB.txt").read_text(encoding="utf-8")
ep55_signoff = ep55_bb.strip().split(tf.BREAK)[-1].strip()
bad = tf.problems([{"kind": "furniture", "id": "signoff", "name": "outro: sign-off",
                    "text": ep55_signoff},
                   {"kind": "furniture", "id": "rg", "name": "rg", "text": tf.RG_LINE}],
                  sand / ep56.name, PP)
check("CONTROL: EP55's own sign-off, placed in another episode → refused as a repeat",
      any("VERBATIM" in b and "EP55" in b for b in bad), "; ".join(bad)[:120])
bad = tf.problems([s for s in built["manifest"]], ep56, PP)
check("EP56's placed sign-off is not a repeat of any other episode", not bad, "; ".join(bad))

# ── 4. the midroll window sees two-ways (E3), and the composer uses it ───────────
print("\n-- 4. the midroll window sees the two-ways --")
win57 = [os.path.basename(os.path.dirname(os.path.dirname(f)))[:7]
         for _p, f in rr.midroll_window(str(PP / "PP-EP57-Not-Yet"))]
check("EP57's window includes EP55 and EP56 (two-ways)",
      "PP-EP55" in win57 and "PP-EP56" in win57, ", ".join(win57))
check("and EP49 is in EP50's window now (it was the gap that started all this)",
      any(os.path.basename(os.path.dirname(os.path.dirname(f))).startswith("PP-EP49")
          for _p, f in rr.midroll_window(str(PP / "PP-EP50-x"))))
import qc_episode as qe   # noqa: E402
check("qc_episode's own copy of the window agrees with render_ready's",
      [f for _p, f in qe.midroll_window(str(PP / "PP-EP57-Not-Yet"))]
      == [f for _p, f in rr.midroll_window(str(PP / "PP-EP57-Not-Yet"))])
wordings = rr.pool_wordings()
used55 = rr.lines_in_folder(str(ep_paths.episode_dir(55, PP)), wordings)
check("EP55 used L5 (old wording)", "L5" in used55, ",".join(sorted(used55)))
# put L5 into EP56's real words, real archive: EP55 is inside EP56's window
real_words = tf.approved_words(d56, 56)
refused("CONTROL: L5 for EP56 → refused, EP55 used it inside the window",
        lambda: tf.midroll_for(56, dict(real_words, midroll=pool["L5"]), PP), "PP-EP55")

# ── 5. never silently overwrite a pasted script ──────────────────────────────────
print("\n-- 5. writing --")
# The splitter writes dialogue-only scripts BEFORE this step: not composed, never pasted,
# so they are replaced without --force (no manifest beside them yet).
(sdocs / "spoken-words-BB.txt").write_text("the splitter's dialogue only\n", encoding="utf-8")
tf.build(56, sand, write=True)
check("a dialogue-only script (no manifest yet) is replaced without --force",
      (sdocs / "spoken-words-BB.txt").read_text(encoding="utf-8")
      == (d56 / "spoken-words-BB.txt").read_text(encoding="utf-8"))
check("first write lands in the sandbox, guest script included",
      (sdocs / "spoken-words-BM.txt").read_text(encoding="utf-8")
      == (d56 / "spoken-words-BM.txt").read_text(encoding="utf-8"))
tf.build(56, sand, write=True)
check("a second identical write changes nothing (no error)", True)
(sdocs / "spoken-words-BB.txt").write_text("a script someone pasted\n", encoding="utf-8")
refused("CONTROL: a different script already on disk → refused without --force",
        lambda: tf.build(56, sand, write=True), "already exist")
check("and the file on disk was left alone",
      (sdocs / "spoken-words-BB.txt").read_text(encoding="utf-8") == "a script someone pasted\n")

shutil.rmtree(sand, ignore_errors=True)
shutil.rmtree(tmpmod.parent, ignore_errors=True)
print(f"\nfurniture words: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
