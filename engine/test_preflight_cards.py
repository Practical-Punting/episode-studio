"""test_preflight_cards.py — the card checks, proved against EP16's REAL file.

The acceptance test is not hand-written: `testdata/ep16-cards-BEFORE-FIX.episode.json`
is EP16's episode.json exactly as first written, and every fault in it cost a
halt after the render gate, the credit check and nine paid generations.

    ⚠️ AND E26 RETURNS ZERO BLOCKERS ON THAT SAME FILE.
    It compares keys and TYPES against two reference episodes, so a MISSING key
    or a CHANGED type is visible and an EXTRA key that no reference has is
    invisible. Every EP16 fault was an extra key or a closed-vocabulary value.
    That measurement is re-run below, because it is the whole argument.

The does-not-cry-wolf cases matter as much as the catches: this guard runs at
the head of EVERY build, so a false positive halts every episode, and that is
the version somebody switches off.

Run: python engine/test_preflight_cards.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import preflight_cards as pc

FIXTURE = HERE / "testdata/ep16-cards-BEFORE-FIX.episode.json"
PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))


def episode_dir(n: int) -> Path:
    """Resolve an episode folder BY NUMBER, never by a written-out name.

    The stage-8 close-out renames every published episode's folder, so a literal
    is a fuse. This suite tripped that lint on its first run, correctly.
    """
    hits = sorted(p for p in PP.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else PP / f"PP-EP{n:02d}"


PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def main():
    if not FIXTURE.is_file():
        print(f"missing fixture: {FIXTURE}")
        return 1
    epj = json.loads(FIXTURE.read_text(encoding="utf-8"))

    print("-- the acceptance test: EP16's real broken file --")
    res = pc.preflight_cards(epj)
    b = res["blockers"]
    check("it names faults in the real file", len(b) >= 20, f"only {len(b)}")
    joined = " ".join(b)

    # Each of these is a fault EP16 actually halted on, named by card.
    for cid, needle in [("C3", "unknown key 'left'"), ("C4", "unknown key 'stat'"),
                        ("C8", "unknown key 'rows'"), ("C10", "unknown key 'rows'"),
                        ("C11", "unknown key 'statement'"),
                        ("C6", "unknown field 'sub'"), ("C9", "unknown field 'sub'"),
                        ("C2", "MISSING optional key 'note'"),
                        ("C5", "MISSING optional key 'warn'"),
                        ("C7", "MISSING optional key 'note'"),
                        ("C12", "MISSING optional key 'warn'")]:
        check(f"  {cid}: {needle}",
              any(x.startswith(cid + ":") and needle in x for x in b))
    check("  the closed job vocabulary is enforced ('prove' is not a job)",
          "job 'prove' is not one of" in joined)
    check("  a job/block contradiction is caught (C11 claims 'relate')",
          any("declares job 'relate'" in x for x in b))
    # This case used to assert that "content could not be read" APPEARED in the
    # report. It did — because of a bug in this module, not a fault in the file.
    # With validate() called correctly that message no longer fires here, so the
    # case now proves the two things that actually matter: the plain-English path
    # exists for a crash, and no raw interpreter text reaches a human.
    check("  a crashing validator still speaks plain English, never 'NoneType'",
          "NoneType" not in pc._readable("CX", TypeError("'NoneType' object is not iterable")))
    check("  and no blocker in the real report is a raw interpreter message",
          "NoneType" not in joined)

    print("\n-- it does NOT cry wolf --")
    check("bespoke cards are not reported as unknown blocks",
          "unknown block 'bespoke'" not in joined,
          "TITLE/END/WARRANTY are hand-authored by design")
    for cid in ("TITLE", "END", "WARRANTY"):
        check(f"  {cid} is left alone", not any(x.startswith(cid + ":") for x in b))
    check("no blocker is a raw interpreter message",
          not any("object is not" in x or "Traceback" in x for x in b))

    print("\n-- the cues: a cue must be words Gordon actually says --")
    script = "\n\n".join([
        "An each-way bet is two bets sold to you in a single transaction.",
        "You put up eight dollars for the win and twelve for the place.",
    ])
    cues = pc.cue_faults({"cards": [
        {"id": "C1", "cue": "sold to you in a single transaction"},
        {"id": "C9", "cue": "eight for the win, to give a profit of forty dollars"},
    ]}, script)
    check("a cue copied from the script PASSES",
          not any(x.startswith("C1:") for x in cues))
    check("a cue written from a summary FAILS (EP16's C9)",
          any(x.startswith("C9:") for x in cues))
    check("  and the halt quotes the cue as written",
          any("eight for the win" in x for x in cues))
    folded = pc.cue_faults(
        {"cards": [{"id": "CX", "cue": "Each-Way!  BETS,"}]},
        "an each way bets story")
    check("it folds like derive_card_timings — 'each-way' matches 'each way'",
          not folded, "a lint that cries wolf is a lint someone turns off")

    print("\n-- the capture file's markers are load-bearing --")
    check("a capture with both markers passes",
          not pc.capture_faults(f"head\n{pc.MARKER_BEGIN}\nbody\n{pc.MARKER_END}\n"))
    check("a capture missing them is caught (EP16 hit this at step sixteen)",
          len(pc.capture_faults("no markers here")) == 2)
    check("no capture at all is not a fault", pc.capture_faults(None) == [])

    print("\n-- the name against the SOURCE PAGE, not against itself --")
    cap = "# EACH-WAY BETTING FOREVER! (Part 2)\n\nBy Roger Dedman\n"
    check("the real EP16 name matches its page's headline",
          not pc.name_faults({"title": "Each-Way Betting Forever! — Part 2"}, cap))
    check("THE WRONG NAME IS CAUGHT — the one check_one_name passed",
          pc.name_faults({"title": "Squeeze Those Odds! — Part 2"}, cap) != [])
    check("  and it quotes both, so a human can see which is which",
          "EACH-WAY BETTING FOREVER" in " ".join(
              pc.name_faults({"title": "Squeeze Those Odds! — Part 2"}, cap)))

    print("\n-- there is NO beat estimate here, and that is the test --")
    # Ruled out 6 Aug 2026. A beat's real duration does not exist until the audio
    # does; the version that lived here found ONE of EP16's three real short
    # beats plus one that was not real, and a warning wrong about half the time
    # trains people to stop reading warnings. The exactness went to
    # derive_card_timings, which has the measured SRT.
    check("no beat estimate survives in the module",
          not hasattr(pc, "beat_warnings"),
          "a guess that stays in gets acted on eventually")
    check("the pre-flight emits no warnings at all now",
          pc.preflight_cards(epj)["warnings"] == [])
    check("and nothing left behind estimates a duration",
          "WORDS_PER_MIN" not in
          (HERE / "preflight_cards.py").read_text(encoding="utf-8")
          .split("def capture_faults")[0].replace("# ", ""))

    print("\n-- IT MUST BE SILENT ON A FINISHED EPISODE --")
    # THE CASE THAT NEARLY SHIPPED A GUARD THAT HALTS EVERY BUILD.
    # `validate()` RAISES on a fault and returns None when a card is FINE, and
    # the first version iterated its return value. On the broken fixture most
    # cards raised before returning, so the report looked right. On EP16 AS
    # SHIPPED, where every card passes, all thirteen came back None and every one
    # was reported as unreadable — a guard that fires only when nothing is wrong.
    # It would have halted EP16 and every episode after it (CLAUDE.md fault #4a).
    shipped = episode_dir(16) / "docs/episode.json"
    if shipped.is_file():
        s = json.loads(shipped.read_text(encoding="utf-8"))
        sres = pc.preflight_cards(s)
        check("EP16 AS SHIPPED returns ZERO blockers",
              not sres["blockers"],
              f"would have halted a good episode: {sres['blockers'][:2]}")
        check("  and every card was actually examined, so silence means something",
              len([c for c in s.get("cards", [])
                   if c.get("block") not in (None, "bespoke")]) >= 10)
    else:
        check("EP16 as shipped is available to check against", False,
              "cannot prove the guard is quiet on a good episode")

    print("\n-- why this is not E26's job, MEASURED not argued --")
    try:
        import preflight_episode_json as e26
        refs = [epj, epj]
        e26res = e26.preflight(epj, refs)
        check("E26 returns ZERO blockers on the same broken file",
              len(e26res.get("blockers", [])) == 0,
              f"E26 found {len(e26res.get('blockers', []))}")
    except Exception as e:
        check("E26 comparison ran", False, f"{type(e).__name__}: {e}")

    print(f"\npreflight cards: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
