"""B1 — SMOKE THIS ARTICLE'S OWN SHAPE BEFORE A FRESH RUN, and only its own.

Capture has broken on a NEW ARTICLE SHAPE on episode after episode — EP20 a profile with
no byline, EP23 a page carrying layout markers the parser had never seen — and every one
was found DURING A LIVE RUN, by Jodie, with an episode already queued and the studio
apparently working. `smoke_capture` exists to find that class off the clock, and it ran
NIGHTLY: which catches a regression by morning, but not before the episode that trips it.

⚠️ ONE SECTION, NEVER THE CORPUS — Jodie's decision, 14 Aug 2026. The full sweep is a
network fetch per shape; making every new episode wait on all of them buys early warning
with a delay on the path that is usually fine. **The full sweep stays the nightly job.**

🚫 AND IT NEVER BLOCKS. The capture attempt immediately after is the real test and gives
the specific error for THIS page. The pre-flight runs first so the log can already say
whether the SHAPE is broken or just this one article — the question somebody would
otherwise answer by hand at midnight. A pre-flight that turned a readable page away
because a SIBLING article failed would stop the studio for a fault the episode does not
have.

Run: python engine/test_capture_preflight.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine                                                         # noqa: E402
import smoke_capture                                                  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


URL = ("https://practicalpunting.com.au/pp-online/a-z-of-betting/form-analysis/"
       "racetracks/track-secrets-part-4-19860600")

print("\n-- it asks about THIS article's section, and nothing else --")
check("the section is derived from the pasted url",
      smoke_capture.section_of(URL) == "a-z-of-betting/form-analysis",
      smoke_capture.section_of(URL))

src = (HERE / "engine.py").read_text(encoding="utf-8")
fn = src.split("def _section_smoke")[1].split("\ndef ")[0]
check("the pre-flight passes --section to the smoke test", '"--section", section' in fn)
check("  and NEVER --all", "--all" not in fn,
      "the full sweep is the nightly job; a new episode must not wait on it")
check("  and never --refresh-corpus", "refresh-corpus" not in fn,
      "re-reading the whole rail is not a pre-flight")

print("\n-- it runs BEFORE the capture it precedes --")
body = src.split("_section_smoke(ep.get(\"source_url\"))")[1][:400]
check("it is called on the fresh-capture path", "_section_smoke(ep.get" in src)
check("  and before capture_article builds anything", "cap.build(" in body,
      "a pre-flight after the capture is a post-mortem")

print("\n-- IT NEVER BLOCKS THE RUN (the whole design) --")
check("it returns None, so no caller can branch on it", "-> None" in fn)
check("  a url it cannot section is survived", "log(f\"    capture pre-flight: skipped" in fn)
check("  a smoke test that cannot run is survived", "carrying on" in fn)
check("  and a failing shape is REPORTED, not raised",
      "raise" not in fn,
      "turning a readable page away because a SIBLING failed stops the studio for a "
      "fault this episode does not have")
check("  a failure says the SHAPE is at fault, not this page",
      "the SHAPE, not this" in fn,
      "that is the question somebody would otherwise answer by hand at midnight")

print("\n-- driven for real, not asserted from the source --")
calls = []
engine._section_smoke(None)
engine._section_smoke("")
check("no url does nothing at all", True, "")     # reaching here without raising is it

# A smoke run that times out MUST NOT propagate — driven with a 1s ceiling so the
# subprocess is guaranteed to be cut off.
try:
    engine._section_smoke(URL, timeout=1)
    survived = True
except Exception as e:                                                # noqa: BLE001
    survived = False
    calls.append(str(e))
check("a smoke run that times out is swallowed", survived,
      f"it propagated: {calls}")

print(f"\ncapture pre-flight: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
