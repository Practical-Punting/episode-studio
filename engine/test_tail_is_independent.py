#!/usr/bin/env python3
"""THE TAIL DOES NOT READ THE ASSEMBLED VIDEO — the case for running it alongside assembly.

    python engine/test_tail_is_independent.py

MEASURED ON EP28's CLEAN RUN (84.7 min, from the rail's own build_state):

    assemble_passA   3.0 min   ─┐ the assembling phase runs these in a line
    assemble_passB   6.8 min   ─┘
    ebook_pdf        3.8 min   ─┐
    thumbnail        1.9 min    │ 5.7 minutes that need nothing passA or passB makes
    web_copies       0.0 min   ─┘
    self_qc          1.9 min     reads the video AND the PDF AND the thumbnail
    youtube_copy     3.5 min

`ebook_pdf`, `thumbnail` and `web_copies` are 5.7 minutes of work that could hide
inside assembly's 9.8. This file is the evidence for that claim, so the reordering
rests on something better than "it looks independent":

  · the three tail steps NEVER reach for the assembled video;
  · `self_qc` DOES reach for all three artefacts, so it stays last;
  · and the order still puts `youtube_copy` before `self_qc` — today it runs AFTER,
    which is why every episode's QC report carries a false "no YouTube copy source
    found" warning about a file that is written three minutes later.

🔴 WHY A STATIC AUDIT AND NOT A RUN. A behavioural proof would have to assemble an
episode twice, which is half an hour of ffmpeg per pass and needs a master, clips and
a shot map. The DEPENDENCY is a property of the code, not of one episode: what a step
reads is visible in what it calls. Derived from the source, so a step that starts
reading the video tomorrow fails this on the day it is written — the same shape as
test_step_call_sites.

⚠️ THIS FILE PROVES THE SAFETY OF THE REORDER, NOT THE SAVING. The saving is wall
clock and contended (WeasyPrint and Chromium against ffmpeg); it is measured on the
first real episode that runs the new order, and the number goes in the run log.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"\n         <- {why}" if not cond and why else ""))


PROVIDERS = (HERE / "providers.py").read_text(encoding="utf-8")
ENGINE = (HERE / "engine.py").read_text(encoding="utf-8")

# What "the assembled video" looks like in this codebase, however it is spelled.
VIDEO = re.compile(r"FINAL\.mp4|-FINAL|final_mp4|assembled|passB_out|final_video", re.I)


def method_source(src: str, name: str, cls: str | None = None) -> str:
    """The source of one method, from the REAL file — parsed, not grepped.

    A grep for `def build_ebook` catches the mock and the real provider both, and the
    mock is not what ships. The class is named, so the answer is about the code that
    actually runs an episode.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if cls and isinstance(node, ast.ClassDef) and node.name == cls:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == name:
                    return ast.get_source_segment(src, sub) or ""
        if not cls and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(src, node) or ""
    return ""


print("\n-- the three tail steps never reach for the assembled video --")
for meth in ("build_ebook", "build_thumbnail", "build_web_copies"):
    src = method_source(PROVIDERS, meth, cls="RealProvider")
    check(f"RealProvider.{meth} is found in the source", bool(src),
          "the audit cannot say anything about a method it did not find")
    if src:
        hits = sorted(set(VIDEO.findall(src)))
        check(f"  {meth} does NOT read the final video", not hits,
              f"it mentions {hits} — if it now needs the assembled video, it can no "
              f"longer run alongside assembly and this reorder is unsafe")

print("\n-- and self_qc DOES need the video, which is why it stays last --")
# ⚠️ ASKED OF THE SIGNATURE, NOT OF A REGEX OVER THE BODY. `self_qc(self, ep,
# final_path)` never spells "FINAL.mp4" — it is HANDED the assembled video and passes
# it straight to qc_episode.py. The first version of this case grepped the body, found
# nothing, and reported that QC does not read the video, which is the opposite of true.
# What a step RECEIVES is the dependency; what it happens to spell is not.
def params(src: str, name: str, cls: str | None = None) -> list:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if cls and not (isinstance(node, ast.ClassDef) and node.name == cls):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.FunctionDef) and sub.name == name:
                return [a.arg for a in sub.args.args]
    return []


qc_args = params(PROVIDERS, "self_qc", cls="RealProvider")
qc = method_source(PROVIDERS, "self_qc", cls="RealProvider")
check("self_qc is found", bool(qc))
check("  it is HANDED the assembled video", any("final" in a for a in qc_args),
      f"its parameters are {qc_args} — if QC no longer receives the video, the "
      f"ordering argument has changed and this reorder needs re-thinking")
check("  and it runs the QC script over it", "qc_episode.py" in qc, qc[:120])

print("\n-- the mirror: the tail steps are handed no video either --")
for meth in ("build_ebook", "build_thumbnail", "build_web_copies"):
    args = params(PROVIDERS, meth, cls="RealProvider")
    check(f"  {meth}{tuple(args)} receives no video path",
          not any("final" in a for a in args), str(args))

print("\n-- the phase order itself --")
import engine as E                                                    # noqa: E402

order = E.PHASES["assembling"]
print("   ", " -> ".join(order))
check("self_qc is LAST or last-but-none-that-write-artefacts",
      order.index("self_qc") > max(order.index(s) for s in
                                   ("assemble_passB", "ebook_pdf", "thumbnail", "web_copies")),
      "QC must run after everything it grades — EP19 failed three times on artefacts "
      "the next two steps were about to create")
check("🔴 youtube_copy runs BEFORE self_qc",
      order.index("youtube_copy") < order.index("self_qc"),
      "today it runs after, so self_qc reports 'no YouTube copy source found' on EVERY "
      "episode about a file written three minutes later — a warning that is always "
      "wrong is a warning nobody reads")
check("web_copies still runs after thumbnail",
      order.index("web_copies") > order.index("thumbnail"),
      "it needs the full-size thumbnail that step writes, and the e-book cover")

print(f"\ntail independence: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
