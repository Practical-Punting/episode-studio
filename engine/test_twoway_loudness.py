"""The two-way publishes at the same loudness as everything else: -14 LUFS, TP <= -1.0 dBTP.

Jodie's ruling, 27 Sep 2026, landed in `assemble_episode` (9b89f1c) and NOT in
`twoway_render`, which kept its own -16 recipe with the limiter's auto-level ON. EP49
shipped at -15.9 by her choice; EP55 must not.

What this pins:

  1. the two-way's audio graph — the very string `finish()` uses — normalises speech to
     the publish target, lifts the bed and the duck threshold by the same LIFT, and ends
     on a limiter with level=0 under the true-peak target;
  2. its numbers are `publish_loudness`'s, the module `assemble_episode` reads, so the two
     mixers cannot drift apart again;
  3. `twoway_qc.main` actually CALLS the loudness check (AST, not grep);
  4. MEASURED, not assumed: EP49's own speech + music mixed through that graph and
     encoded the way the finish encodes it lands inside qc_episode's verdict.
     ⚠️ EP49 is NOT re-mixed — Jodie ruled it ships as is. This writes one audio file to
     the scratch dir given by TWOWAY_LOUDNESS_TMP (default: the system temp dir).

FAIL-FIRST: `RENDER=<pre-change twoway_render.py> QCMOD=<pre-change twoway_qc.py>`
goes red.

Run: python engine/test_twoway_loudness.py
"""
import ast
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude" / "skills" / "pp-episode-production" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
RENDER = os.environ.get("RENDER") or str(HERE / "twoway_render.py")
QCMOD = os.environ.get("QCMOD") or str(HERE / "twoway_qc.py")
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


import publish_loudness as pl  # noqa: E402

tr = load("tr_under_test", RENDER)
graph_fn = getattr(tr, "audio_graph", None)
check(graph_fn is not None, "twoway_render has ONE audio graph that finish() uses")
fin = next((n for n in ast.walk(ast.parse(open(RENDER, encoding="utf-8").read()))
            if isinstance(n, ast.FunctionDef) and n.name == "finish"), None)
calls = {c.func.id for c in ast.walk(fin) if isinstance(c, ast.Call)
         and isinstance(c.func, ast.Name)} if fin else set()
check("audio_graph" in calls, "and finish() builds its audio by calling it",
      sorted(calls & {"audio_graph"}))

g = graph_fn(900.0, "1") if graph_fn else ""
m = re.search(r"loudnorm=I=(-?[\d.]+)", g)
check(m and float(m.group(1)) == pl.TARGET_LUFS == -14.0,
      "speech is normalised to -14 LUFS", m and m.group(1))
mv = re.search(r"volume='([\d.]+)\*\(", g)
check(mv and abs(float(mv.group(1)) - 10 ** (2 / 20)) < 1e-4,
      "the bed is lifted by the same +2 dB", mv and mv.group(1))
th = re.search(r"sidechaincompress=threshold=([\d.]+)", g)
check(th and abs(float(th.group(1)) / 10 ** (2 / 20) - 0.015) < 1e-5,
      "the duck threshold is lifted too, so the ducking is unchanged", th and th.group(1))
lim = re.search(r"alimiter=([^\[]+)\[a\]", g)
opts = dict(kv.split("=") for kv in lim.group(1).split(":")) if lim else {}
check(opts.get("level") == "0", "the limiter's auto-level is OFF", lim and lim.group(1))
check(float(opts.get("limit", 1)) <= 10 ** (-1.0 / 20),
      "and its ceiling is under -1.0 dBTP", opts.get("limit"))
check(abs(pl.TARGET_LUFS - load("qce", str(SCRIPTS / "qc_episode.py")).LOUDNESS_TARGET) < 1e-9,
      "qc_episode judges against the same target the mixer aims at")

qsrc = ast.parse(open(QCMOD, encoding="utf-8").read())
qmain = next((n for n in ast.walk(qsrc)
              if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
qcalls = {c.func.id for c in ast.walk(qmain) if isinstance(c, ast.Call)
          and isinstance(c.func, ast.Name)} if qmain else set()
check("loudness" in qcalls, "twoway_qc.main measures the finished file's loudness")

# ── 4: measured on EP49's own inputs ──────────────────────────────────────────
try:
    import ep_paths
    import twoway_assemble as ta
    d = ep_paths.episode_dir(49)
    plan = ta.build_plan(49, pathlib.Path("G:/My Drive/PP Videos"))
    tl = json.loads((d / "renders/master-timeline.json").read_text(encoding="utf-8"))
    speech = tr.speech_path(d / "renders/_pieces", tl["timeline"])
    have = speech.is_file() and graph_fn is not None
except Exception as e:                                            # noqa: BLE001
    have, why = False, f"{type(e).__name__}: {e}"
else:
    why = f"{speech.name} not on disk" if not speech.is_file() else "no audio_graph"
if not have:
    print(f"  (EP49's inputs unavailable — {why} — measured half SKIPPED, not assumed)")
else:
    total = plan["total_s"]
    out = pathlib.Path(os.environ.get("TWOWAY_LOUDNESS_TMP") or tempfile.gettempdir()) \
        / "twoway-loudness-ep49.m4a"
    fc = graph_fn(total, tr.music_envelope(plan))
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", "color=c=black:s=16x16:r=1:d=1",
                        "-f", "lavfi", "-i", "color=c=black:s=16x16:r=1:d=1",
                        "-i", str(speech), "-i", str(tr.MUSIC),
                        "-filter_complex", fc, "-map", "[a]", "-t", f"{total:.3f}",
                        "-c:a", "aac", "-b:a", "256k", str(out)],
                       capture_output=True, text=True, timeout=1800)
    check(r.returncode == 0, "EP49's speech + music mix through the graph", r.stderr[-300:])
    tw = load("twoway_qc_under_test", QCMOD)
    meas = getattr(tw, "loudness", None)
    if meas and out.is_file():
        q = meas(out)
        I, tp = q.loudness.get("I"), q.loudness.get("true_peak")
        check(not q.failed, f"EP49's inputs land at {I} LUFS / {tp} dBTP — inside the "
                            f"publish verdict", "; ".join(q.failed) or "no fail")
    else:
        check(False, "twoway_qc can measure a file's loudness")

print(f"\ntwo-way loudness: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
