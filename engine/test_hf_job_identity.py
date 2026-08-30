#!/usr/bin/env python3
"""A HIGGSFIELD ANSWER MUST BE ABOUT THE JOB WE LAUNCHED.

    python engine/test_hf_job_identity.py

Two production lines now generate on the SAME Higgsfield account and the same
balance. The engine has always asked by id — `generate get <id>` — and has
always checkpointed the id the instant it existed. What was missing was the
other half: nothing ever asked whether the ANSWER was about the job we asked
for. A wrong answer does not look like a failure. It looks like a b-roll clip,
and it gets composited into the episode and paid for.

🔴 THE CONTROL RUNS FIRST AND IT MUST GO RED FOR THE RIGHT REASON (§4b).
Case 1 hands the checker a perfectly well-formed, `completed` record with a
real-looking result URL — the other line's generation — and requires a refusal.
A checker that cannot fail on that is not a checker.

⚠️ REAL DATA AND A FIXTURE, BOTH (§4c). Cases 2-3 are the ACTUAL envelopes this
account returned on 30 Aug 2026 for one still (`nano_banana_pro`) and one clip
(`kling3_0_turbo`) — captured by asking the live CLI, so the guard is measured
against what Higgsfield really says, not against what it was assumed to say.
(The `params.prompt` field is trimmed here for size; the identity check never
reads it.) Cases 4-6 are fixtures built to ATTACK the check rather than to
imitate an episode.

NOTHING here touches the network, the CLI, the rail, an episode folder or a
running engine: `_hf` is replaced with a function that returns a canned record.
"""
from __future__ import annotations

import ast
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

import providers                                                      # noqa: E402

PASS, FAIL = [], []


def case(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'ok  ' if ok else '!!  '}{name}")
    if not ok and detail:
        print(f"      {detail}")


OURS = "a8aafe1d-8a22-4585-8803-fa8f2db559e0"      # EP44's first b-roll job, real
THEIRS = "3f9c1b40-77aa-4d21-9e55-0c4e8b91dd02"    # a plausible other-line id

CDN = "https://d8j0ntlcm91z4.cloudfront.net/user_3GikDJuRctSNEgHp2eeVZoOD1Im"

# The two REAL envelopes, as returned by the live account on 30 Aug 2026.
REAL_STILL = {
    "created_at": "2026-08-29T05:17:00.904302Z",
    "display_name": "Nano Banana Pro",
    "id": "62f0ef7d-5c0e-42ac-9a04-bf255249c567",
    "job_type": "nano_banana_pro",
    "min_result_url": f"{CDN}/hf_20260829_051700_62f0ef7d-…_min.webp",
    "params": {"aspect_ratio": "2:3", "prompt": "(trimmed)", "resolution": "2k"},
    "result_url": f"{CDN}/hf_20260829_051700_62f0ef7d-5c0e-42ac-9a04-bf255249c567.png",
    "status": "completed",
}
REAL_CLIP = {
    "created_at": "2026-08-30T04:51:11.372273Z",
    "display_name": "Kling 3.0 Turbo",
    "id": OURS,
    "job_type": "kling3_0_turbo",
    "min_result_url": None,
    "params": {"aspect_ratio": "16:9", "duration": 5, "prompt": "(trimmed)"},
    "result_url": f"{CDN}/hf_20260830_045111_{OURS}.mp4",
    "status": "completed",
}


def checker(record):
    """A RealProvider with nothing but `_hf` replaced. __init__ is not run, so
    no path, no .env and no CLI is touched — the method under test uses only
    `self._hf` and `print`."""
    p = providers.RealProvider.__new__(providers.RealProvider)
    p._hf = lambda *a, **k: record
    return p


def verdict(record, job_id=OURS, label="a b-roll clip"):
    """(returned_record | None, EngineFlag | None, what it printed)."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            return checker(record)._hf_job(job_id, label), None, buf.getvalue()
    except providers.EngineFlag as e:
        return None, e, buf.getvalue()


# ── 1. THE CONTROL — THE OTHER LINE'S GENERATION IS REFUSED ─────────────────
other_line = {"id": THEIRS, "status": "completed", "job_type": "kling3_0_turbo",
              "result_url": f"{CDN}/hf_20260830_045959_{THEIRS}.mp4"}
rec, flag, printed = verdict(other_line)
case("CONTROL — a well-formed record for a DIFFERENT job is REFUSED",
     rec is None and flag is not None,
     "it was accepted; the checker cannot fail, so it proves nothing")
case("  …and the run log names BOTH ids, so it can be diagnosed",
     OURS in printed and THEIRS in printed, printed)
case("  …and says plainly that nothing was downloaded",
     "Nothing was downloaded" in printed, printed)

# ── 2. THE REAL ENVELOPES THIS ACCOUNT ACTUALLY RETURNS ─────────────────────
rec, flag, _ = verdict(REAL_CLIP, job_id=OURS)
case("REAL DATA — the live clip envelope (kling3_0_turbo) is accepted",
     rec is REAL_CLIP and flag is None, str(flag))
rec, flag, _ = verdict(REAL_STILL, job_id="62f0ef7d-5c0e-42ac-9a04-bf255249c567")
case("REAL DATA — the live still envelope (nano_banana_pro) is accepted",
     rec is REAL_STILL and flag is None, str(flag))

# ── 3. FIXTURES BUILT TO ATTACK THE CHECK, NOT TO IMITATE AN EPISODE ────────
no_id_but_named = {"status": "completed",
                   "result_url": f"{CDN}/hf_20260830_045111_{OURS}.mp4"}
rec, flag, printed = verdict(no_id_but_named)
case("an envelope with NO top-level id but our id in the URL is accepted",
     rec is not None and flag is None, str(flag))
case("  …and it says so once, in the run log, rather than passing silently",
     "no top-level id" in printed, printed)

nameless = {"status": "completed", "result_url": f"{CDN}/hf_20260830_045959_"
            f"{THEIRS}.mp4"}
rec, flag, _ = verdict(nameless)
case("an envelope that names NO job of ours anywhere is REFUSED",
     rec is None and flag is not None)

rec, flag, _ = verdict(["not", "a", "record"])
case("a non-dict answer is REFUSED rather than indexed into",
     rec is None and flag is not None)

rec, flag, _ = verdict({"id": None, "status": "completed"})
case("an explicit null id with our id nowhere in the record is REFUSED",
     rec is None and flag is not None)

# ── 4. THE OPERATOR'S BOX (docs/PP-operator-box-rule.md) ────────────────────
_, flag, _ = verdict(other_line)
msg = str(flag)
case("the flag Jodie sees carries no job id, no path, no URL and no JSON",
     not any(t in msg for t in (OURS, THEIRS, "http", "\\", "{", "generate get")),
     msg)
case("  …and it says whether retrying helps",
     "retrying" in msg.lower(), msg)

# ── 5. BOTH CALL SITES GO THROUGH IT — ASKED OF THE SYNTAX TREE (§1a) ───────
TREE = ast.parse((HERE / "providers.py").read_text(encoding="utf-8"))


def _method(cls_name, fn_name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.ClassDef) and node.name == cls_name:
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == fn_name:
                    return sub
    raise AssertionError(f"{cls_name}.{fn_name} is not in providers.py")


def _self_calls(fn):
    out = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"):
            out.append((n.func.attr, [a.value for a in n.args
                                      if isinstance(a, ast.Constant)]))
    return out


for who in ("poll_broll", "_hf_download"):
    calls = _self_calls(_method("RealProvider", who))
    names = [c[0] for c in calls]
    case(f"{who} fetches the job through _hf_job", "_hf_job" in names, str(names))
    raw = [c for c in calls if c[0] == "_hf" and "get" in c[1]]
    case(f"  …and {who} never calls `generate get` behind its back", not raw, str(raw))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print(f"  FAILED: {f}")
sys.exit(1 if FAIL else 0)
