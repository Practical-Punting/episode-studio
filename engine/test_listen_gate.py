"""test_listen_gate.py — the build STOPS until a human has listened to the master.

    EP20, 11 Aug 2026. Jodie approved the HeyGen PREVIEW, the render generated, and
    nobody heard the GENERATED file until the whole episode was built and sitting at
    its four approvals. It cost a re-render and a full re-assembly.

🚫 AND THERE IS NO AUTOMATED AUDIO CHECK, WHICH IS THE DECISION, NOT AN OMISSION.
The bad take was measured against EP18 and EP19: integrated loudness within 0.5 LUFS,
true peak within 0.3 dB, LRA, bitrate, sample rate, channels, and every spectral band
from 0 to 20 kHz within 1 dB. NOTHING IN THE SIGNAL distinguished it — the defect was
the performance. A threshold check could not have fired, and one that cannot fire is
worse than none: it prints "audio OK" and trains everyone to stop listening.

So the gate is a HUMAN one, and these cases prove the two halves that matter:
the build HALTS at it, and clearing it lets the build go on.

Run: python engine/test_listen_gate.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine                                                    # noqa: E402
import providers                                                 # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def master_in(d: Path, body=b"not really a video, but it has a size and an mtime"):
    (d / "renders").mkdir(parents=True, exist_ok=True)
    p = d / "renders/presenter-master.mp4"
    p.write_bytes(body)
    return p


def main():
    print("-- WHERE IT SITS: after the download, before anything expensive --")
    r = engine.PHASES["rendering"]
    check("listen_check is in the rendering phase", "listen_check" in r, f"{r}")
    check("  AFTER the master is downloaded",
          r.index("heygen_download") < r.index("listen_check"),
          "there is nothing to listen to before it lands")
    check("  and BEFORE the shot map and every assembly pass",
          r.index("listen_check") < r.index("shot_map"), f"{r}")
    a = engine.PHASES["assembling"]
    check("  which is before both assembly passes, the e-book and QC",
          all(s in a for s in ("assemble_passA", "assemble_passB", "self_qc")))
    check("it waits on a HUMAN, so the watchdog must not call it stuck",
          engine.STEP_BUDGET_S.get("listen_check", "MISSING") is None,
          "a step that waits for a person needs no alarm — same as cover_pick")
    check("  and the board says who it is waiting on",
          "you" in (engine.STEP_LABEL.get("listen_check") or "").lower(),
          engine.STEP_LABEL.get("listen_check"))

    print("\n-- CONTROL: THE BUILD HALTS THERE --")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        m = master_in(d)
        try:
            providers.listen_to_the_master(d, m)
            check("an un-listened master raises the flag", False, "it returned instead")
        except providers.EngineFlag as f:
            msg = str(f)
            check("an un-listened master raises the flag", True)
            check("  it asks for the thing Jodie asked for",
                  "listen" in msg.lower() and "voice sounds right" in msg.lower())
            check("  it names the file to listen to", str(m) in msg)
            check("  it says what it costs to skip",
                  "half an hour" in msg or "25" in msg or "wasted" in msg)
            check("  it warns that the PREVIEW is not this file",
                  "preview" in msg.lower() and "not this file" in msg.lower(),
                  "that mistake is the entire reason this gate exists")
            check("  and it says an ear is the only detector",
                  "only an ear" in msg.lower())
            check("  it tells them what to do if it sounds WRONG",
                  "re-render" in msg.lower() and "nothing here is wasted" in msg.lower())

        print("\n-- A RERUN IS NOT AN ANSWER (C3, 13 Aug 2026) --")
        # 🔴 THIS CASE USED TO CALL THE GATE TWICE AND REQUIRE THE SECOND TO FALL
        # THROUGH, on the reasoning that "clearing the flag on the board re-runs the
        # step". Both halves of that are true and the conclusion still did not follow:
        # a re-run is ALSO what happens after a crash, a reboot or a `--watch` restart,
        # and this test could not tell those from a human clearing a flag — because
        # neither could the code. It asserted the EP23 bug. Windows updated overnight,
        # killed the engine between the ask and the answer, and the gate walked through.
        # The two events are now two records, so the two cases below are separable.
        second = "returned"
        try:
            providers.listen_to_the_master(d, m)
        except providers.EngineFlag:
            second = "raised again"
        check("re-running the step WITHOUT an answer asks again", second == "raised again",
              "a gate a power cut can pass is not a gate")

        print("\n-- AND CLEARING IT LETS THE BUILD CONTINUE --")
        # THE ANSWER, as the engine records it: the human cleared the flag.
        providers.answer_pending_gates(d)
        third = "returned"
        try:
            providers.listen_to_the_master(d, m)
        except providers.EngineFlag:
            third = "raised again"
        check("the answered master does NOT ask twice", third == "returned",
              "the episode could never proceed — the original requirement, unchanged")

        print("\n-- A NEW MASTER ASKS AGAIN. This is EP20's case exactly. --")
        m2 = master_in(d, b"a DIFFERENT take, re-rendered because the first was bad")
        asked = False
        try:
            providers.listen_to_the_master(d, m2)
        except providers.EngineFlag:
            asked = True
        check("a re-rendered master is listened to on its own merits", asked,
              "it inherited the old take's approval — the exact thing that would let a "
              "second bad take through unheard")

    print("\n-- IT IS A HUMAN GATE, NOT A MEASUREMENT --")
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    body = src.split("def listen_to_the_master(ep_dir")[1].split("\ndef ")[0]
    # ⚠️ STRIP THE DOCSTRING WITH THE PARSER, NOT WITH startswith(). The first version
    # dropped lines beginning with a quote, which leaves every CONTINUATION line of a
    # multi-line docstring behind — so the prose explaining why there is no LUFS check
    # was read as a LUFS check. A guard that fires on its own explanation is a guard
    # somebody deletes.
    import ast
    fn = next(n for n in ast.parse(src).body
              if isinstance(n, ast.FunctionDef) and n.name == "listen_to_the_master")
    stmts = fn.body[1:] if ast.get_docstring(fn) else fn.body
    code = "\n".join(ast.unparse(n) for n in stmts)
    for banned in ("loudnorm", "ebur128", "astats", "volumedetect", "silencedetect",
                   "ffprobe", "bit_rate", "LUFS"):
        check(f"  it does not measure the audio ({banned!r})", banned not in code,
              "a signal check CANNOT catch this and would say 'audio OK' on a bad take")
    check("  and the reasoning is written where the next person will read it",
          "PERFORMANCE" in body and "within 1 dB" in body)

    print("\n-- the step is wired, and reaches the provider --")
    check("step_listen_check exists", callable(getattr(engine, "step_listen_check", None)))
    check("  it is in the dispatch table",
          engine.STEP_FNS.get("listen_check") is getattr(engine, "step_listen_check"))
    for cls in (providers.MockProvider, providers.RealProvider):
        check(f"  {cls.__name__} answers listen_to_the_master",
              callable(getattr(cls, "listen_to_the_master", None)))

    print(f"\nlisten gate: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
