"""The e-book drops EXACTLY the episode's sanctioned cuts — read from the same file the scripts use.

Jodie, 11 Nov 2026, EP56: NAME THE SITE, DROP THE ADDRESS (three web addresses inside the
dialogue). `author_ebook.apply_sanctioned` applies docs/sanctioned-substitutions.json to the
ARTICLE side of the fidelity comparison, so the body must equal the article-with-exactly-those-
cuts, character for character.

REAL DATA (EP56's own body, capture and cuts), copied to a temp folder so nothing on the Drive
is touched:
  1. EP56 as built                                   -> PASS, and the pass line names the cuts
  2. CONTROL: one address put back into the body     -> HALT (the book would print it)
  3. CONTROL: the cuts file withheld                 -> HALT (an undeclared change)
  4. EP55, which has no cuts file                    -> PASS, unchanged

FAIL-FIRST: with HEAD's author_ebook (no apply_sanctioned), case 1 halts.

Run: python engine/test_ebook_sanctioned.py
"""
import glob
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
AE = os.environ.get("AUTHOR_EBOOK") or str(HERE.parent / ".claude/skills/pp-episode-production/scripts/author_ebook.py")
PP = pathlib.Path(r"G:\My Drive\PP Videos")
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def gate(ep_dir: pathlib.Path):
    r = subprocess.run([sys.executable, "-X", "utf8", AE, str(ep_dir / "docs/episode.json"),
                        str(ep_dir / "ebook"), "--check-only"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def sandbox(src: pathlib.Path, with_subs=True, body_edit=None) -> pathlib.Path:
    """<tmp>/docs (the capture, as the gate resolves it: two levels above the episode's docs)
    and <tmp>/EP/docs + <tmp>/EP/ebook — a copy, never the Drive."""
    root = pathlib.Path(tempfile.mkdtemp())
    ep = root / "EP"
    (ep / "docs").mkdir(parents=True)
    (ep / "ebook").mkdir()
    epj = json.loads((src / "docs/episode.json").read_text(encoding="utf-8"))
    shutil.copy2(src / "docs/episode.json", ep / "docs/episode.json")
    shutil.copy2(src / "ebook/body.html", ep / "ebook/body.html")
    if with_subs and (src / "docs/sanctioned-substitutions.json").is_file():
        shutil.copy2(src / "docs/sanctioned-substitutions.json", ep / "docs/sanctioned-substitutions.json")
    rel = __import__("re").search(r"(docs/[\w\-.]+\.md)", epj["source"]).group(1)
    (root / "docs").mkdir()
    shutil.copy2(PP / rel, root / rel)
    for f in (src / "ebook").glob("figure-*.png"):
        shutil.copy2(f, ep / "ebook" / f.name)
    if body_edit:
        b = (ep / "ebook/body.html").read_text(encoding="utf-8")
        (ep / "ebook/body.html").write_text(body_edit(b), encoding="utf-8")
    return ep


EP56 = pathlib.Path(glob.glob(str(PP / "PP-EP56-*"))[0])
EP55 = pathlib.Path(glob.glob(str(PP / "PP-EP55-*"))[0])

print("\n-- EP56: THE THREE CUTS, AND ONLY THOSE --")
code, out = gate(sandbox(EP56))
check(code == 0 and "FIDELITY GATE: PASS" in out, "EP56 as built passes the fidelity gate", f"exit {code}")
check("sanctioned cuts applied to the article side (3)" in out, "and its pass line names the three cuts")

put_back = lambda b: b.replace("Phil Purser’s Just Racing website has",
                               "Phil Purser’s Just Racing website (www.justracing.com.au) has", 1)
code, out = gate(sandbox(EP56, body_edit=put_back))
check(code != 0 and "HALTED" in out, "CONTROL: a body that still prints an address HALTS", f"exit {code}")

code, out = gate(sandbox(EP56, with_subs=False))
check(code != 0 and "HALTED" in out, "CONTROL: withhold the cuts file and the cut body HALTS", f"exit {code}")

print("\n-- AN EPISODE WITH NO CUTS FILE IS UNCHANGED --")
code, out = gate(sandbox(EP55))
check(code == 0 and "FIDELITY GATE: PASS" in out and "sanctioned" not in out,
      "EP55 passes exactly as before, with no mention of cuts", f"exit {code}")

print(f"\ne-book sanctioned cuts: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
