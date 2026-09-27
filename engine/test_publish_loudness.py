"""The publish loudness: -14 LUFS integrated, true peak no higher than -1.0 dBTP.

Jodie's ruling, 27 Sep 2026, from EP50 on. YouTube plays at about -14 LUFS and turns
loud videos DOWN but never quiet ones UP, so the old -16 master played ~2 dB softer
than most of YouTube ("a bit soft").

What this pins, on the REAL assembly graph (generated from a published episode's own
episode.json + shot-map.json, resolved by number):

  1. the speech is normalised to -14, not -16
  2. the WHOLE mix moves: the music bed and the duck threshold are scaled by the SAME
     lift as the speech, so the speech-over-music balance and the ducking are unchanged
  3. the final limiter is a real ceiling — `level=0` — under the true-peak target.
     alimiter's auto-level is ON by default and turned every master up to full scale,
     so the old `limit=0.95` never limited anything (EP48's rebuilt mix peaked at -0.1)
  4. qc_episode FAILS a master at the old numbers and passes one at the new

PROVED FAIL-FIRST: run with ASSEMBLE=<the pre-change assemble_episode.py> and
QC=<the pre-change qc_episode.py> and it goes red.

Run: python engine/test_publish_loudness.py
"""
import importlib.util
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ep_paths  # noqa: E402

SCRIPTS = os.path.join(os.path.dirname(HERE), ".claude", "skills", "pp-episode-production",
                       "scripts")
ASSEMBLE = os.environ.get("ASSEMBLE") or os.path.join(SCRIPTS, "assemble_episode.py")
QC = os.environ.get("QC") or os.path.join(SCRIPTS, "qc_episode.py")
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


# ── 1–3: the graph the assembler actually emits ────────────────────────────────
ep = ep_paths.episode_dir(48)
epj, smj = ep / "docs" / "episode.json", ep / "renders" / "shot-map.json"
if not (epj.is_file() and smj.is_file()):
    print(f"  (no {epj.parent.parent.name} inputs on this machine — graph half SKIPPED, "
          "not assumed)")
else:
    env = dict(os.environ, PYTHONPATH=SCRIPTS)
    g = subprocess.run([sys.executable, ASSEMBLE, str(epj), str(smj), "B"], env=env,
                       capture_output=True, text=True, encoding="utf-8").stdout
    audio = g[g.find("loudnorm="):] if "loudnorm=" in g else ""
    check(bool(audio), "the pass-B graph has an audio chain")
    m = re.search(r"loudnorm=I=(-?[\d.]+)", audio)
    check(m and float(m.group(1)) == -14.0, "speech is normalised to -14 LUFS",
          m and m.group(1))
    lift = 10 ** (2 / 20)
    mv = re.search(r"volume='([\d.]+)\*\(", audio)
    check(mv and abs(float(mv.group(1)) - lift) < 1e-4,
          "the music bed is lifted by the same +2 dB as the speech",
          mv and mv.group(1))
    th = re.search(r"sidechaincompress=threshold=([\d.]+)", audio)
    check(th and abs(float(th.group(1)) / lift - 0.015) < 1e-5,
          "the duck threshold is lifted too, so the ducking is unchanged",
          th and th.group(1))
    lim = re.search(r"alimiter=([^\[]+)\[aout\]", audio)
    opts = dict(kv.split("=") for kv in lim.group(1).split(":")) if lim else {}
    check(opts.get("level") == "0",
          "the final limiter has auto-level OFF (level=0), so its limit is a ceiling",
          lim and lim.group(1))
    check(float(opts.get("limit", 1)) <= 10 ** (-1.0 / 20),
          "and that ceiling is under the -1.0 dBTP target", opts.get("limit"))

# ── 4: qc_episode's verdict ────────────────────────────────────────────────────
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
spec = importlib.util.spec_from_file_location("qce", QC)
qce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qce)


class Q:
    def __init__(self):
        self.failed, self.notes, self.warned = [], [], []

    def fail(self, m): self.failed.append(m)
    def note(self, m): self.notes.append(m)
    def warn(self, m): self.warned.append(m)


verdict = getattr(qce, "loudness_verdict", None)
check(verdict is not None, "qc_episode has a loudness verdict (not just a report)")
if verdict:
    for I, tp, ok, why in [(-15.6, -0.1, False, "the old recipe's own output, EP48 inputs"),
                           (-16.0, -1.6, False, "the old -16 target"),
                           (-12.6, 0.3, False, "a -14 lift without a real ceiling"),
                           (-14.5, -1.6, True, "the new recipe, EP48 inputs"),
                           (-14.0, -1.0, True, "exactly on target and ceiling")]:
        q = Q()
        verdict(q, I, tp)
        check((not q.failed) == ok,
              f"{I} LUFS / {tp} dBTP {'passes' if ok else 'FAILS'} ({why})",
              "; ".join(q.failed) or "no fail")

print(f"\npublish loudness: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
