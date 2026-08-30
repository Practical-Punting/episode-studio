#!/usr/bin/env python3
"""THE DOWNLOADS SWEEP MUST MATCH BY NAME, AND THE CONTROL PROVES RECENCY DOES NOT.

    python engine/test_downloads_sweep.py

🔴 THE CONTROL RUNS FIRST AND IT SHOWS THE BUG. (CLAUDE.md §4b: a guard is not
trustworthy until you have watched it fail. Here the thing that must be watched
failing is the OLD RULE, because that rule is what is being replaced.)

Case 1 reproduces Stage 0's old instruction — *"locate by name/recency"* — on a
Downloads folder holding one PP file and one file from the other production line
on this laptop, with the other line's file NEWER. Recency picks the wrong one.
Only once that is on the screen does a green on the name rule mean anything.

Everything runs in a throwaway temp directory. NOTHING touches ~/Downloads, an
episode folder, the rail, the network or a running engine.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

import downloads_sweep as ds                                          # noqa: E402

PASS, FAIL = [], []


def case(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'ok  ' if ok else '!!  '}{name}")
    if not ok and detail:
        print(f"      {detail}")


OURS = "broll-three-horses-hitting-the-line-together-seen-side-on.mp4"
THEIRS = "iw-chapter-04-render.mp4"
OLD = time.time() - 3600            # comfortably outside the quiet hold


def build(tmp: Path, extra_broll=()):
    """A minimal episode + a Downloads folder holding one of each kind of file."""
    ep = tmp / "PP-EP99"
    (ep / "docs").mkdir(parents=True, exist_ok=True)
    broll = [{"target": Path(OURS).stem}] + [{"target": t} for t in extra_broll]
    (ep / "docs/episode.json").write_text(json.dumps({
        "broll": broll,
        "cards": [{"id": "C1", "page": "ep99-c01-a-card.html"}],
        "build": {"standing": {"title": "TITLE", "endcard": "END"},
                  "midroll": {"composite": True, "clip": "midroll-lowerthird.mp4"}},
    }), encoding="utf-8")

    dl = tmp / "Downloads"
    dl.mkdir(parents=True, exist_ok=True)
    (dl / OURS).write_bytes(b"PP" * 5000)
    (dl / THEIRS).write_bytes(b"IW" * 9000)
    (dl / "holiday-photo.png").write_bytes(b"\x89PNG")
    (dl / "notes.docx").write_bytes(b"zzz")            # not media: never named
    os.utime(dl / OURS, (OLD, OLD))                     # ours is the OLDER file
    os.utime(dl / THEIRS, (OLD + 1800, OLD + 1800))     # theirs is the NEWER one
    os.utime(dl / "holiday-photo.png", (OLD, OLD))
    return ep, dl


# ── 1. THE CONTROL — THE OLD RULE PICKS THE OTHER LINE'S FILE ────────────────
def the_old_recency_rule_picks_the_wrong_file():
    tmp = Path(tempfile.mkdtemp(prefix="pp-sweep-control-"))
    _, dl = build(tmp)
    media = [p for p in dl.iterdir()
             if p.is_file() and p.suffix.lower() in ds.MEDIA_SUFFIXES]
    newest = max(media, key=lambda p: p.stat().st_mtime)
    shutil.rmtree(tmp, ignore_errors=True)
    return newest.name


chosen = the_old_recency_rule_picks_the_wrong_file()
case("CONTROL — 'take the most recent' picks the OTHER LINE'S file",
     chosen == THEIRS,
     f"recency chose {chosen!r}; the bug is only reproduced when it chooses {THEIRS!r}")
print(f"      (recency chose {chosen!r} — that is the fault this module removes)")


# ── 2. THE NAME RULE TAKES OURS AND ONLY OURS ───────────────────────────────
tmp = Path(tempfile.mkdtemp(prefix="pp-sweep-"))
ep, dl = build(tmp)
r = ds.sweep(ep, downloads=dl)

case("the name rule MOVES the file this episode named",
     (ep / "broll" / OURS).is_file(), f"moved={r['moved']} held={r['held']}")
case("  …and it lands in broll/, byte for byte",
     (ep / "broll" / OURS).read_bytes() == b"PP" * 5000)
case("  …and it is gone from Downloads", not (dl / OURS).exists())
case("the OTHER LINE'S file is NOT moved", (dl / THEIRS).is_file())
case("  …and no PP folder received it",
     not (ep / "broll" / THEIRS).exists() and not (ep / "overlay/clips" / THEIRS).exists())

# ── 3. WHAT WAS LEFT BEHIND IS NAMED, NOT SILENT ────────────────────────────
lines = ds.report_lines(r)
blob = "\n".join(lines)
case("the file that was NOT moved is NAMED in the report", THEIRS in blob, blob)
case("  …and the report says plainly that nothing was done with it",
     "NOTHING WAS DONE WITH THEM" in blob, blob)
case("the file that WAS moved is named too — a quiet move is as bad as a quiet skip",
     OURS in blob and "moved" in blob, blob)
case("a non-media file is not reported as a stranger",
     "notes.docx" not in blob, blob)
case("the stranger COUNT is exact", r["not_ours_total"] == 2,
     f"counted {r['not_ours_total']}, expected iw-chapter + holiday-photo")

# ── 4. THE EXPECTATIONS ARE DERIVED FROM episode.json, NOT MAINTAINED HERE ──
tmp2 = Path(tempfile.mkdtemp(prefix="pp-sweep-derived-"))
ep2, _ = build(tmp2, extra_broll=("broll-a-brand-new-shot-nobody-has-coded-for",))
want = ds.expected(ep2)
case("§7 — adding a b-roll shot adds its expectation with no code change here",
     "broll-a-brand-new-shot-nobody-has-coded-for.mp4" in want, sorted(want))
case("  …a card page's clip is expected from the page's own stem",
     "ep99-c01-a-card.mp4" in want, sorted(want))
case("  …and the midroll chip's clip is expected by the name build.midroll gives it",
     "midroll-lowerthird.mp4" in want, sorted(want))
case("  …while build.standing's CARD IDS never become filenames",
     "TITLE.mp4" not in want and "END.mp4" not in want, sorted(want))

# ── 5. THE REFUSALS ─────────────────────────────────────────────────────────
tmp3 = Path(tempfile.mkdtemp(prefix="pp-sweep-refuse-"))
ep3, dl3 = build(tmp3)
(ep3 / "broll").mkdir(parents=True, exist_ok=True)
(ep3 / "broll" / OURS).write_bytes(b"ALREADY HERE")
r3 = ds.sweep(ep3, downloads=dl3)
case("a destination that already exists is NEVER overwritten",
     (ep3 / "broll" / OURS).read_bytes() == b"ALREADY HERE")
case("  …the source is left in Downloads, untouched", (dl3 / OURS).is_file())
case("  …and the report says so", any("already in the episode" in x for x in r3["held"]),
     str(r3["held"]))

tmp4 = Path(tempfile.mkdtemp(prefix="pp-sweep-inflight-"))
ep4, dl4 = build(tmp4)
(dl4 / OURS).unlink()
part = dl4 / (OURS + ".crdownload")
part.write_bytes(b"half")
os.utime(part, (OLD, OLD))
still = dl4 / "broll-a-second-shot.mp4"
(ep4 / "docs/episode.json").write_text(json.dumps(
    {"broll": [{"target": "broll-a-second-shot"}]}), encoding="utf-8")
still.write_bytes(b"arriving right now")          # mtime = now: inside the hold
r4 = ds.sweep(ep4, downloads=dl4)
case("a part-file is never moved", part.is_file() and not r4["moved"], str(r4))
case("a file still being written is HELD, not moved",
     still.is_file() and any("still arriving" in h for h in r4["held"]), str(r4["held"]))

# ── 6. CASE, AND THE THINGS THAT MUST NEVER RAISE ───────────────────────────
tmp5 = Path(tempfile.mkdtemp(prefix="pp-sweep-case-"))
ep5, dl5 = build(tmp5)
shouty = dl5 / OURS.upper()
(dl5 / OURS).rename(shouty)
os.utime(shouty, (OLD, OLD))
r5 = ds.sweep(ep5, downloads=dl5)
case("a Windows filename in the wrong case is still recognised as ours",
     len(r5["moved"]) == 1, str(r5))

case("a Downloads folder that is not there does not raise",
     ds.sweep(ep5, downloads=tmp5 / "no-such-folder")["problem"] is not None)
case("  …and audit() turns it into a line, never an exception",
     isinstance(ds.audit(ep5, downloads=tmp5 / "no-such-folder"), list))
bad = Path(tempfile.mkdtemp(prefix="pp-sweep-bad-"))
(bad / "docs").mkdir(parents=True)
(bad / "docs/episode.json").write_text("{ this is not json", encoding="utf-8")
case("an unreadable episode.json means NO expectations, not a crash",
     ds.expected(bad) == {})
case("  …so every file is a stranger, and every stranger is only reported",
     ds.sweep(bad, downloads=dl5)["moved"] == [])

# ── 7. THE CALL SITE — ASKED OF THE SYNTAX TREE, NEVER OF A GREP (§1a) ──────
TREE = ast.parse((HERE / "providers.py").read_text(encoding="utf-8"))


def _method(cls_name, fn_name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.ClassDef) and node.name == cls_name:
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == fn_name:
                    return sub
    raise AssertionError(f"{cls_name}.{fn_name} is not in providers.py")


def _calls(fn):
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                base = f.value.id if isinstance(f.value, ast.Name) else (
                    "self" if isinstance(f.value, ast.Attribute) else "?")
                out.add(f"{base}.{f.attr}")
            elif isinstance(f, ast.Name):
                out.add(f.id)
    return out


audit_calls = _calls(_method("RealProvider", "audit_inputs"))
case("the ENGINE'S first step really reaches the sweep (a call, not a comment)",
     "downloads_sweep.audit" in audit_calls, sorted(audit_calls))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print(f"  FAILED: {f}")
for t in (tmp, tmp2, tmp3, tmp4, tmp5, bad):
    shutil.rmtree(t, ignore_errors=True)
sys.exit(1 if FAIL else 0)
