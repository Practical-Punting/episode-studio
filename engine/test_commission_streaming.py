#!/usr/bin/env python3
"""BATCH 7 — THE WRITER IS STREAMED, AND THE ENVELOPE IS THE SAME ENVELOPE.

    python engine/test_commission_streaming.py

🔴 THE FAULT. `audit_inputs` is the biggest step in the build and nearly all of it is ONE
commission. It ran as a single blocking `subprocess.run` on a wall clock, and three
commissions have burned their whole ceiling and saved NOTHING — two at 1800s and one at
**3208s (53.5 minutes)**, from the engine's own log. A clock cannot tell a writer that is
thinking from one that is dead.

⚠️ AND THE BLOCKER WAS NOT `subprocess.run` vs `Popen`. It was `--output-format json`:
one envelope, at the end. Nothing came out during the 25 minutes, so there was no silence
to measure against because there was no sound either. **A stream with no events in it is
not a stream.**

🔴 THE LOAD-BEARING ASSERTION, AND WHY IT IS THE WHOLE CONTROL. Twenty `CommissionHalt`
paths read the envelope's shape. If the streamed path handed them something merely
*equivalent*, the failure would move from here to a 3am halt with a confusing message. So
this proves the streamed envelope is **the same envelope, key for key** — measured
against a real `--output-format json` capture of the same prompt.

💰 AND IT COSTS NOTHING TO RUN. The two captures are committed as FIXTURES
(`engine/testdata/commission-stream-*.ndjson`), recorded once from the real CLI. This
suite spawns nothing and spends nothing, now or in 270 episodes' time — which is the only
honest way to keep a control over the one path that spends money.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import commission as com                                              # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                 # noqa: BLE001
        pass

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


DATA = HERE / "testdata"
STREAM = (DATA / "commission-stream-success.ndjson").read_text(encoding="utf-8")
TRUNC = (DATA / "commission-stream-truncated.ndjson").read_text(encoding="utf-8")
ENVJSON = json.loads((DATA / "commission-envelope-json.json").read_text(encoding="utf-8"))


def events(text):
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


# ── THE ONE THAT MATTERS ──────────────────────────────────────────────────────
def _the_streamed_envelope_is_the_same_envelope():
    res = [e for e in events(STREAM) if e.get("type") == "result"]
    assert len(res) == 1, f"expected exactly one result event, got {len(res)}"
    missing = set(ENVJSON) - set(res[0])
    extra = set(res[0]) - set(ENVJSON)
    assert not missing, (
        f"the streamed envelope is MISSING {sorted(missing)} that --output-format json "
        f"returns. Twenty halt paths read this shape; a reconstruction that is only "
        f"close moves the failure to a 3am halt with a confusing message.")
    assert not extra, f"the streamed envelope has keys json does not: {sorted(extra)}"


case("🔴 the streamed result event has the SAME KEYS as --output-format json",
     _the_streamed_envelope_is_the_same_envelope)


def _every_key_the_halt_paths_read_is_present():
    """Named individually, so adding a halt that reads a new key fails HERE rather than
    in production."""
    res = [e for e in events(STREAM) if e.get("type") == "result"][0]
    for k in ("is_error", "subtype", "result", "total_cost_usd", "num_turns",
              "permission_denials"):
        assert k in res, f"the streamed envelope has no {k!r} — a halt path reads it"


case("every key the twenty halt paths read is in the streamed envelope",
     _every_key_the_halt_paths_read_is_present)


def _the_envelope_parses_through_the_unchanged_halt_path():
    """The streamed result is handed to `_envelope_or_halt` exactly as subprocess.run's
    stdout was. If that needed changing, the batch would have touched the money path's
    error handling — which it must not."""
    line = [ln for ln in STREAM.splitlines()
            if ln.strip() and json.loads(ln).get("type") == "result"][0]
    r = com._Streamed(0, line, "", ["result"], [1.0], json.loads(line))
    env = com._envelope_or_halt(r, "the draft")
    assert env.get("is_error") is False, env.get("is_error")


case("_envelope_or_halt reads the streamed result UNCHANGED",
     _the_envelope_parses_through_the_unchanged_halt_path)


# ── THE SILENCE PATH ──────────────────────────────────────────────────────────
def _a_truncated_stream_has_no_envelope_and_halts():
    """The fixture cut off before the result event — a writer that died mid-job. It must
    HALT, not return a half-envelope."""
    assert not [e for e in events(TRUNC) if e.get("type") == "result"], \
        "the truncated fixture still contains a result event; it proves nothing"
    r = com._Streamed(0, "", "", ["assistant"], [1.0], events(TRUNC)[-1])
    try:
        com._envelope_or_halt(r, "the draft")
    except com.CommissionHalt:
        return
    raise AssertionError("a stream with no result event was accepted as an envelope")


case("🔴 a truncated stream halts rather than yielding a half-envelope",
     _a_truncated_stream_has_no_envelope_and_halts)


def _the_halt_says_how_far_it_got():
    """🔴 HALF THE PRIZE. Today a timeout returns NOTHING — 53 minutes and no information
    about what went wrong. The message must name what the writer last did."""
    evs = events(TRUNC)
    msg = com._stall_message(what="the draft", quiet=600.0,
                             events=[e.get("type") for e in evs], last=evs[-1],
                             started=com.time.time() - 1500, wall=False,
                             raw_path=r"G:\...\commission-stream-123.ndjson")
    assert "HOW FAR IT GOT" in msg, msg
    assert str(len(evs)) in msg, "it does not say how many steps it saw"
    assert "10.0 minutes" in msg, f"it does not say how long it was quiet:\n{msg}"
    assert "commission-stream-123.ndjson" in msg, (
        "it does not point at the partial output kept for diagnosis")


case("🔴 a stall names how far it got, how long it was quiet, and where the "
     "partial output is", _the_halt_says_how_far_it_got)


def _a_wall_clock_halt_still_reports_the_same_way():
    evs = events(STREAM)
    msg = com._stall_message(what="the draft", quiet=5.0,
                             events=[e.get("type") for e in evs], last=evs[-1],
                             started=com.time.time() - 1800, wall=True, raw_path=None)
    assert "did not finish in the time allowed" in msg and "HOW FAR IT GOT" in msg, msg


case("a wall-clock halt reports how far it got too", _a_wall_clock_halt_still_reports_the_same_way)


# ── THE GAPS, AND THE THRESHOLD THAT IS DELIBERATELY NOT SET ──────────────────
def _the_threshold_is_unset_and_that_is_deliberate():
    """A silence timeout needs a number and the number IS the design. The only capture
    available is a two-second trivial prompt — a sample of one, of the wrong shape. It
    ships MEASURING, not halting, until a real commission gives the distribution."""
    assert com.COMMISSION_SILENCE_S is None, (
        f"COMMISSION_SILENCE_S is set to {com.COMMISSION_SILENCE_S} — if that number was "
        f"measured off a real commission, record the rejected values beside it the way "
        f"CARD_SHARDS does and update this case. If it was guessed, remove it.")
    assert com.COMMISSION_STREAMING in (True, False)


case("the silence threshold is UNSET until a real commission measures it",
     _the_threshold_is_unset_and_that_is_deliberate)


def _the_gap_summary_reports_the_largest():
    s = com.gap_summary([1.0, 2.0, 30.0, 3.0])
    assert "largest 30.0s" in s, s
    assert "no gaps" in com.gap_summary([])


case("the gap summary names the LARGEST gap — the number a threshold is chosen from",
     _the_gap_summary_reports_the_largest)


# ── THE REVERT SWITCH, AND THE INJECTED RUNNER ───────────────────────────────
def _an_injected_runner_still_takes_the_old_path():
    """The suites drive `runner` to exercise the halt paths without spawning anything.
    A streamed Popen would ignore them, so streaming must stand aside when a runner is
    injected — otherwise this batch silently disables the tests that guard the money."""
    src = (HERE / "commission.py").read_text(encoding="utf-8")
    assert "runner is subprocess.run" in src, (
        "the streamed path does not stand aside for an injected runner — every existing "
        "commission test would stop exercising what it thinks it exercises")


case("🔴 an injected runner still takes the unstreamed path",
     _an_injected_runner_still_takes_the_old_path)


def _one_constant_reverts_it():
    src = (HERE / "commission.py").read_text(encoding="utf-8")
    assert "COMMISSION_STREAMING" in src and "ENGINE_COMMISSION_STREAMING" in src, (
        "there is no single switch to revert the money path — a bad night must be one "
        "edit and a restart, not a rollback at 3am")


case("one constant (and one env var) reverts the whole batch", _one_constant_reverts_it)


print(f"\ncommission streaming: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
