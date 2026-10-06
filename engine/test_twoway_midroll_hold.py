"""The like-and-subscribe chip is never on screen for less than its own animation.

Jodie's ruling, 6 Oct 2026, the standing rule for two-ways (as single-presenter): "the
chip's on-screen time is at least its own animation length, never cut short by a short
ask." EP55's L5 ask is 6.56s; sizing the chip to the ask gave 6.76s on screen — under
§4E's 6s of full visibility and cutting `midroll-lowerthird.mp4` (7.70s) off mid-animation.
The build halted.

  1. EP55 itself (real merged.srt, real clips): the plan builds, the chip holds >= 7.70s,
     full visibility >= 6s, and no STANDING CLIP CUT OFF violation;
  2. a synthetic SHORT ask: the chip is held for the clip's length, not the ask's;
  3. the beat still rules: a beat too short to hold the clip HALTS (never runs over the
     return to the reading).

FAIL-FIRST: TES=<pre-change twoway_end_sequence.py> -> red (EP55 halts at 5.96s).

Run: python engine/test_twoway_midroll_hold.py
"""
import importlib.util
import os
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
path = os.environ.get("TES") or str(HERE / "twoway_end_sequence.py")
spec = importlib.util.spec_from_file_location("twoway_end_sequence", path)
tes = importlib.util.module_from_spec(spec)
sys.modules["twoway_end_sequence"] = tes          # so twoway_assemble imports THIS one
spec.loader.exec_module(tes)
import ep_paths                                    # noqa: E402
import twoway_assemble as ta                       # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


d55 = ep_paths.episode_dir(55)
clip = d55 / "overlay/clips/midroll-lowerthird.mp4"
if not (d55 / "renders/merged.srt").is_file() or not clip.is_file():
    print("  (EP55's merged.srt or midroll clip not on this machine — real half SKIPPED)")
else:
    own = 7.70
    try:
        plan = ta.build_plan(55, pathlib.Path("G:/My Drive/PP Videos"))
        m = plan["graphics"]["midroll"]
        full = m["dur_s"] - 2 * m["fade_s"]
        check(m["dur_s"] >= own - 0.01, "EP55 (L5): the chip holds for its own 7.70s",
              f"{m['at_s']:.2f}+{m['dur_s']:.2f}s")
        check(full >= 6.0, "and is fully visible for at least §4E's 6s", f"{full:.2f}s")
        cut = [v for v in ta.violations(plan) if "CUT OFF" in v]
        check(not cut, "and nothing reports the standing clip cut off", cut[:1])
        check(m["at_s"] + m["dur_s"] <= m["beat"][1] + 0.01,
              "and it comes down inside the midroll beat",
              f"down at {m['at_s'] + m['dur_s']:.2f}s, beat ends {m['beat'][1]:.2f}s")
    except Exception as e:                                        # noqa: BLE001
        check(False, "EP55 (L5): the plan builds", f"{type(e).__name__}: {str(e)[:120]}")

    # 2-3: synthetic — a 3-second ask, inside beats of two lengths
    cues = [{"start": 10.0, "end": 13.0, "text": "a like helps and subscribe now"},
            {"start": 13.5, "end": 30.0, "text": "back to the horses and the form"}]
    epj = {"build": {"midroll": {"ask": ["a like helps", "subscribe now"]}}}

    def place(beat_to):
        furn = [{"furniture": "midroll", "from_s": 9.0, "to_s": beat_to}]
        return tes.place(d55, epj, cues, furn, 0.0)

    try:
        g = place(40.0)["midroll"]
        check(g["dur_s"] >= own - 0.01, "a 3s ask: the chip is held for the clip, not the ask",
              f"{g['dur_s']:.2f}s")
    except Exception as e:                                        # noqa: BLE001
        check(False, "a 3s ask: the chip is held for the clip, not the ask",
              f"{type(e).__name__}: {str(e)[:100]}")
    try:
        place(15.0)
        check(False, "a beat too short for the clip HALTS — never runs over the reading")
    except tes.Unplaceable as e:
        check("inside" in str(e), "a beat too short for the clip HALTS — never runs over "
                                  "the reading", str(e)[:70])

print(f"\nmidroll hold: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
