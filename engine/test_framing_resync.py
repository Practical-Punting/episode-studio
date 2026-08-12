"""A LAYOUT CHANGE DECIDES FRAMING — so changing one must re-derive it.

🔴 THE FAULT, EXACTLY. On 12 Aug 2026 C21 was changed `fullscreen` -> `panel-push` to
clear a logo collision. That edit is what decides whether its beat may be MCU. Nothing
re-derived framing. The next day beat 32 halted EP23 at the shot map — and
`_framing_note` still listed beat 32 among the beats that are MCU *because their card is
fullscreen*, which C21 no longer was. THE FIX MADE THE HALT, and the prose that should
have caught it had been overtaken by the very edit that broke it.

Two halves, split by what each can know without the master:
  · the card's OWN beat    -> knowable from episode.json alone, at audit_inputs. HERE.
  · the beats it SPILLS to -> needs the aligned SRT, at shot_map. derive_card_timings.

Run: python engine/test_framing_resync.py
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import framing as fr          # noqa: E402

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


def epj(cards, beats=None):
    return {
        "_framing_note": "EIGHTEEN WIDE OF FORTY-ONE, and beat 32 is MCU because its "
                         "card is fullscreen.",
        "beats": [{"n": n, "framing": f} for n, f in (beats or
                  [(31, "MCU"), (32, "MCU"), (33, "WIDE")])],
        "cards": cards,
    }


# ── THE C21 FIXTURE — the exact edit, and what it must now do ─────────────────
print("\nthe C21 fixture: fullscreen -> panel-push on an MCU beat")

d = epj([{"id": "C21", "beat": 32, "layout": "panel-push"}])
check("the fault is seen", fr.needs_wide_own_beat(d) == {32: ["C21"]},
      str(fr.needs_wide_own_beat(d)))
changed = fr.resync_own_beats(d)
check("it is applied", [(n, w) for n, w, _ in changed] == [(32, "MCU")], str(changed))
got = {b["n"]: b["framing"] for b in d["beats"]}
check("beat 32 is WIDE", got[32] == "WIDE", str(got))
check("beat 31 is untouched — only what the rule demands", got[31] == "MCU", str(got))
check("beat 33 stays WIDE", got[33] == "WIDE", str(got))
check("re-running changes nothing (idempotent)", fr.resync_own_beats(d) == [])

# ── the note must not go on lying ─────────────────────────────────────────────
print("\nthe stale note")

d2 = epj([{"id": "C21", "beat": 32, "layout": "panel-push"}])
ch2 = fr.resync_own_beats(d2)
check("the note is stamped", fr.stamp_framing_note(d2, ch2) is True)
note = d2["_framing_note"]
check("it keeps the authored reasoning", "EIGHTEEN WIDE OF FORTY-ONE" in note)
check("it says the count is no longer authoritative",
      "no longer authoritative" in note, note[-200:])
check("it names what changed", "beat 32" in note and "C21" in note, note[-200:])
fr.stamp_framing_note(d2, ch2)
check("stamping twice leaves ONE stamp, not a pile",
      d2["_framing_note"].count("RE-DERIVED") == 1, d2["_framing_note"][-300:])
check("a no-op change writes nothing", fr.stamp_framing_note(d2, []) is False)

# ── it must not widen what the rule does not reach ────────────────────────────
print("\nwhat it must NOT touch")

d3 = epj([{"id": "C20", "beat": 32, "layout": "fullscreen"}])
check("a FULLSCREEN card on an MCU beat is left alone (host not in shot)",
      fr.needs_wide_own_beat(d3) == {} and fr.resync_own_beats(d3) == [])

d4 = epj([{"id": "CX", "beat": 99, "layout": "panel-push"}])
check("a card whose beat is not in beats[] is ignored, not crashed on",
      fr.resync_own_beats(d4) == [])

d5 = epj([{"id": "C21", "beat": 33, "layout": "panel-push"}])
check("a panel-push card already on a WIDE beat raises nothing",
      fr.needs_wide_own_beat(d5) == {})

d6 = {"beats": [{"n": 1, "framing": "MCU"}],
      "cards": [{"id": "C1", "beat": 1, "layout": "panel-push"}]}
ch6 = fr.resync_own_beats(d6)
check("no _framing_note at all is not an error", fr.stamp_framing_note(d6, ch6) is False)
check("and the framing is still fixed", d6["beats"][0]["framing"] == "WIDE")

# ── several cards, several beats ──────────────────────────────────────────────
print("\nmore than one at a time")

d7 = epj([{"id": "CA", "beat": 31, "layout": "panel-push"},
          {"id": "CB", "beat": 32, "layout": "panel-push"},
          {"id": "CC", "beat": 32, "layout": "panel-push"},
          {"id": "CD", "beat": 33, "layout": "panel-push"}])
need = fr.needs_wide_own_beat(d7)
check("both offending beats are found", sorted(need) == [31, 32], str(need))
check("a beat carrying two cards names both", need[32] == ["CB", "CC"], str(need))
fr.resync_own_beats(d7)
check("all fixed", all(b["framing"] == "WIDE" for b in d7["beats"]),
      str({b["n"]: b["framing"] for b in d7["beats"]}))

print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
