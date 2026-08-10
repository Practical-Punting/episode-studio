#!/usr/bin/env python3
"""The bounded, self-correcting retry on the episode.json / cards commission.

THE FAULT IT STANDS AGAINST — 7 August 2026. The first scratch run of the
episode.json commission wrote a good 67 KB file with ONE thing wrong: a card's
eyebrow carried a figure with no trace entry. `preflight_cards` named the card,
the key and what was missing — and the build halted a human with it. A checker
that precise is a set of instructions, and nobody was reading them back to the
writer.

    "ALL GREEN" MEANS NOTHING UNLESS THE SUITE COVERS WHAT YOU CHANGED.

So every case below names what it stands against, and these four are the ones a
green suite would otherwise never mention:

    the_bound_holds              — an unbounded loop is how you spend an hour
                                   discovering the writer cannot fix it
    a_halt_is_not_retried        — a WALLET REFUSAL must not be attempted 3 times
    the_followup_is_verbatim     — the writer gets the CHECKER's words, not a
                                   paraphrase, and NOT flattened to ASCII
    the_gates_run_exactly_once   — the loop runs them; the caller must not repeat

Nothing here spawns a process, touches the rail, the network, or Drive.
Run: python engine/test_commission_repair.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import commission as C                                                 # noqa: E402
import engine                                                          # noqa: E402
import providers                                                       # noqa: E402

FIXTURE = HERE / "testdata/ep16-cards-BEFORE-FIX.episode.json"

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def quiet(*a, **k):
    pass


def verdict(tag="v"):
    return {"status": "ok", "what_i_saw": tag, "what_it_could_be": [],
            "does_retry_help": False, "unread_sources": []}


class Writer:
    """A stand-in author. Records the follow-up it was handed on every attempt."""

    def __init__(self, gate_results):
        # gate_results[i] is what the gate returns AFTER attempt i+1
        self.gate_results = list(gate_results)
        self.followups = []
        self.gate_calls = 0

    def attempt(self, followup):
        self.followups.append(followup)
        return verdict(f"attempt {len(self.followups)}")

    def gate(self):
        i = self.gate_calls
        self.gate_calls += 1
        return self.gate_results[i] if i < len(self.gate_results) else []


def main():                                                            # noqa: C901
    print("\n-- the happy path, so the rest means something --")
    w = Writer([[]])
    v = C.commission_with_repair(attempt=w.attempt, gate=w.gate,
                                 what="the settings", attempts=3, log=quiet)
    check("a file that passes the gate first time is commissioned ONCE",
          len(w.followups) == 1, f"{len(w.followups)} attempts")
    check("  and the first attempt is given no follow-up", w.followups[0] is None)
    check("  and the verdict comes back", v.get("what_i_saw") == "attempt 1")

    print("\n-- the repair: the writer fixes its own work --")
    fault = "C11: eyebrow carries the figure '4-1' with no trace entry."
    w = Writer([[fault], []])
    v = C.commission_with_repair(attempt=w.attempt, gate=w.gate,
                                 what="the settings", attempts=3, log=quiet)
    check("a gate failure sends it back once, and the pass stops the loop",
          len(w.followups) == 2, f"{len(w.followups)} attempts")
    check("  the verdict returned is the one that PASSED, not the first",
          v.get("what_i_saw") == "attempt 2")
    check("  the gate was re-run after the repair (the engine ran it, not the writer)",
          w.gate_calls == 2, f"{w.gate_calls} gate calls")

    print("\n-- the follow-up carries the CHECKER'S OWN WORDS --")
    note = w.followups[1]
    check("the writer is given the blocker verbatim", fault in note)
    check("  it is told the file already exists and to fix it in place",
          "reject" in note.lower())
    check("  it is told not to change what nobody complained about",
          "nothing else" in note.lower() or "do not rewrite" in note.lower())
    check("  and it is told to halt rather than work around a wrong complaint",
          "halt" in note.lower())

    print("\n-- and the follow-up is NOT flattened to ASCII --")
    # THE TRAP THIS STANDS AGAINST: _safe() exists because the LOG stream is
    # cp1252 on this machine. Applying it to the writer's brief would hand it a
    # corrupted copy of the article's own sentences — em dashes, curly quotes —
    # which are exactly what it has to reproduce character for character.
    curly = "C7: the source sentence is “over £400 — that’s the lot”."
    w2 = Writer([[curly], []])
    C.commission_with_repair(attempt=w2.attempt, gate=w2.gate,
                             what="the settings", attempts=3, log=quiet)
    check("an em dash in a blocker reaches the writer unchanged",
          "—" in w2.followups[1])
    check("  and so do curly quotes", "“" in w2.followups[1])
    check("  nothing was replaced with '?'", "?" not in w2.followups[1])

    print("\n-- THE BOUND HOLDS --")
    w3 = Writer([[fault], [fault], [fault], [fault], [fault]])
    halted = None
    try:
        C.commission_with_repair(attempt=w3.attempt, gate=w3.gate,
                                 what="this episode's settings and cards",
                                 attempts=3, log=quiet)
    except C.CommissionHalt as e:
        halted = e
    check("a writer that never passes stops at exactly 3 attempts",
          len(w3.followups) == 3, f"{len(w3.followups)} attempts")
    check("  and it HALTS rather than returning something unchecked",
          halted is not None)

    print("\n-- the exhaustion halt is OPERATOR-SHAPED (PP-operator-box-rule) --")
    msg = halted.message
    check("it says plainly that retrying will not fix it",
          "retrying will not fix" in msg.lower())
    check("  it says nothing was built and nothing spent",
          "nothing has been built" in msg.lower())
    check("  it names no file, path or extension",
          not any(t in msg for t in (".json", ".py", "/", "\\", "docs")))
    check("  it names no card and no key", "C11" not in msg and "eyebrow" not in msg)
    check("  it carries no JSON, no braces, no code", not any(t in msg for t in "{}[]<>"))
    check("  it tells the operator this one is not theirs to clear",
          "studio" in msg.lower() and "board" in msg.lower())
    check("  the checker's raw lines go to the RUN LOG half instead",
          "C11" in (halted.detail or ""))

    print("\n-- a CommissionHalt is NOT retried (the wallet refusal case) --")
    calls = {"n": 0}

    def refuses(followup):
        calls["n"] += 1
        raise C.CommissionHalt(C._WALLET_REFUSAL, detail="wallet")

    gate_calls = {"n": 0}

    def never_reached():
        gate_calls["n"] += 1
        return []

    got = None
    try:
        C.commission_with_repair(attempt=refuses, gate=never_reached,
                                 what="the settings", attempts=3, log=quiet)
    except C.CommissionHalt as e:
        got = e
    check("a wallet refusal is raised on the FIRST attempt, not tried three times",
          calls["n"] == 1, f"attempted {calls['n']} times")
    check("  the gate is never reached", gate_calls["n"] == 0)
    check("  and the refusal's own words survive, unchanged",
          got is not None and "paid account" in got.message)

    print("\n-- the engine's gate: the checker's lines, not the flag's prose --")
    tmp = Path(tempfile.mkdtemp(prefix="pp-repair-"))
    place = tmp / "PP-EP99"
    (place / "docs").mkdir(parents=True)
    shutil.copyfile(FIXTURE, place / "docs/episode.json")

    class Ctx:
        def __init__(self):
            self.ep = {"id": "x", "ep_number": 99, "title": "A Test",
                       "script_read": True, "title_approved": True,
                       "script_snapshot": ""}
            self.state = {}
            self.mock = False
            self.provider = self
            self.pp = tmp

        def dir(self, ep):
            return place

        def audit_inputs(self, ep):
            return {"folder": "test"}

        def ep_set(self, patch):
            pass

        def save(self):
            pass

    import preflight_episode_json as pj

    # 🔴 E26 IS PINNED SHUT HERE, AND IT HAS TO BE DONE LIKE THIS.
    # `ep_dir(n, root=PP_VIDEOS)` binds its root as a DEFAULT ARGUMENT, i.e. at
    # import time — so setting `pj.PP_VIDEOS` afterwards does nothing at all, and
    # the first version of this suite quietly read the REAL Drive and judged a
    # test fixture against EP17 and EP16. (An id is a promise, a name is a guess:
    # a module global you assume is read at call time is the same trap.) Patching
    # the FUNCTION is the only thing that actually controls it. E26 therefore
    # STANDS ASIDE in every case below — which is a limit of this suite, not a
    # pass, and it is why the scratch proof exists.
    def no_references(n, root=None):
        raise LookupError("no reference episodes in this test")

    prev_ep_dir, prev_log = pj.ep_dir, engine.log
    engine.log = quiet
    pj.ep_dir = no_references
    try:
        blockers = engine._epjson_gate(Ctx())
    finally:
        pj.ep_dir, engine.log = prev_ep_dir, prev_log

    check("the gate returns the CHECKER's lines from EP16's real broken file",
          len(blockers) >= 20, f"{len(blockers)} blockers")
    check("  they name cards, which is what the writer needs",
          any(b.startswith("C3:") for b in blockers))
    check("  and NOT the operator prose wrapped round them",
          not any("nothing has been spent" in b for b in blockers))
    # HONEST ABOUT WHAT DID NOT RUN: E26 stands aside with no references, and a
    # gate that stood aside is not a gate that passed. The scratch proof is where
    # both are shown ENGAGED; here only the card checks did the work.
    check("  E26 stood aside here (no references) — proved engaged on scratch, not here",
          not any("differ from the last two episodes" in b for b in blockers))

    print("\n-- a clean file gives an empty list, so the loop can end --")
    # "Clean" now includes NAMING THE CAPTURE — the gate refuses an episode.json
    # whose `source` does not, because the figure-tracing regime is switched off
    # when it cannot be read. A bare {"cards": []} stopped being a clean file the
    # day that check landed, and this fixture was never updated.
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs/EP99-source-article-test.md").write_text(
        "---- ARTICLE TEXT BEGINS ----\nSome words.\n"
        "---- ARTICLE TEXT ENDS ----\n", encoding="utf-8")
    (place / "docs/episode.json").write_text(json.dumps({
        "source": "Test article. Verbatim source: "
                  "docs/EP99-source-article-test.md",
        "cards": []}), encoding="utf-8")
    engine.log = quiet
    pj.ep_dir = no_references
    try:
        check("no blockers on a file with nothing to complain about",
              engine._epjson_gate(Ctx()) == [])
    finally:
        pj.ep_dir, engine.log = prev_ep_dir, prev_log

    print("\n-- THE GATES RUN EXACTLY ONCE PER PATH, through real dispatch --")
    place2 = tmp / "PP-EP98"
    (place2 / "docs").mkdir(parents=True)
    (place2 / "docs/spoken-words.txt").write_text("Some words.\n", encoding="utf-8")
    # A REAL CAPTURE, because the gate now (rightly) refuses an episode.json
    # whose `source` does not name one: "the whole figure-tracing regime is
    # switched off when this cannot be read". The passing attempt below names
    # it, exactly as a real episode.json does. Without this the "passing"
    # attempt is rejected too and the loop exhausts — which reads as a broken
    # repair loop and is really a fixture nobody updated when the gate grew.
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "docs/EP98-source-article-test.md").write_text(
        "---- ARTICLE TEXT BEGINS ----\nSome words.\n"
        "---- ARTICLE TEXT ENDS ----\n", encoding="utf-8")
    seen = {"attempts": [], "gates": 0}

    class Ctx2(Ctx):
        def __init__(self):
            super().__init__()
            self.ep["ep_number"] = 98

        def dir(self, ep):
            return place2

        def _commission_episode_json(self, ep, d, *, followup=None, on_start=None):
            seen["attempts"].append(followup)
            src = FIXTURE if len(seen["attempts"]) == 1 else None
            if src:
                shutil.copyfile(src, d / "docs/episode.json")
            else:
                (d / "docs/episode.json").write_text(json.dumps({
                    "source": "Test article. Verbatim source: "
                              "docs/EP98-source-article-test.md",
                    "cards": []}), encoding="utf-8")
            return verdict()

    real_gate = engine._epjson_gate

    def counting_gate(ctx):
        seen["gates"] += 1
        return real_gate(ctx)

    prev_assets, prev_script_gate = engine.assert_standing_assets, engine.assert_script_gate
    engine.assert_standing_assets = lambda: "assets ok"
    engine.assert_script_gate = lambda ep: True
    engine._epjson_gate = counting_gate
    engine.log = quiet
    pj.ep_dir = no_references
    try:
        engine.step_audit_inputs(Ctx2())
    finally:
        engine.assert_standing_assets = prev_assets
        engine.assert_script_gate = prev_script_gate
        engine._epjson_gate = real_gate
        pj.ep_dir, engine.log = prev_ep_dir, prev_log

    check("the step commissioned, was rejected, repaired, and carried on",
          len(seen["attempts"]) == 2, f"{len(seen['attempts'])} attempts")
    check("  the presence guard was read ONCE — the repair ran with the file there",
          seen["attempts"][1] is not None)
    check("  the repair was handed the checker's own line",
          "C3:" in (seen["attempts"][1] or ""))
    check("  the gates ran ONCE PER ATTEMPT and were not run a third time after",
          seen["gates"] == 2, f"{seen['gates']} gate runs")

    print("\n-- and a writer that NEVER passes halts the step, operator-shaped --")
    place4 = tmp / "PP-EP96"
    (place4 / "docs").mkdir(parents=True)
    (place4 / "docs/spoken-words.txt").write_text("Some words.\n", encoding="utf-8")
    tries = {"n": 0}

    class Ctx3(Ctx):
        def __init__(self):
            super().__init__()
            self.ep["ep_number"] = 96

        def dir(self, ep):
            return place4

        def _commission_episode_json(self, ep, d, *, followup=None, on_start=None):
            tries["n"] += 1
            shutil.copyfile(FIXTURE, d / "docs/episode.json")   # never fixes it
            return verdict()

    flag = None
    engine.assert_standing_assets = lambda: "assets ok"
    engine.assert_script_gate = lambda ep: True
    engine.log = quiet
    pj.ep_dir = no_references
    try:
        engine.step_audit_inputs(Ctx3())
    except providers.EngineFlag as e:
        flag = e
    finally:
        engine.assert_standing_assets = prev_assets
        engine.assert_script_gate = prev_script_gate
        pj.ep_dir, engine.log = prev_ep_dir, prev_log

    check("the step raises a flag rather than building on a rejected file",
          flag is not None)
    check("  after exactly 3 attempts, not more", tries["n"] == 3, f"{tries['n']}")
    fmsg = str(flag or "")
    check("  the flag a person reads is the operator-shaped one",
          "Retrying will not fix this" in fmsg)
    check("  it carries none of the 33 card faults into the operator's box",
          "C3" not in fmsg and "unknown key" not in fmsg)

    print("\n-- the writer is never given a shell --")
    check("Bash is not in the commission's tools", "Bash" not in C.DEFAULT_TOOLS)
    argv = C.build_argv(Path("claude"), "p", [], C.DEFAULT_TOOLS, 5.0, None)
    check("  and never reaches the command line", "Bash" not in " ".join(argv))
    check("  the follow-up never tells the writer to run the checker itself",
          "run the" not in note.lower() and "python" not in note.lower())

    print("\n-- the brief itself carries the repair block --")
    cap_dir = tmp / "docs"
    cap_dir.mkdir(exist_ok=True)
    (cap_dir / "EP97-source-article-x.md").write_text("# A Headline\n", encoding="utf-8")
    place3 = tmp / "PP-EP97"
    (place3 / "docs").mkdir(parents=True)
    prov = providers.RealProvider.__new__(providers.RealProvider)
    prov.pp = tmp
    grabbed = {}

    def fake_commission(**kw):
        grabbed.update(kw)
        return verdict()

    prev_commission = C.commission
    C.commission = fake_commission
    pj.ep_dir = no_references
    try:
        prov._commission_episode_json({"ep_number": 97}, place3, followup=None)
        first = grabbed["prompt"]
        prov._commission_episode_json({"ep_number": 97}, place3,
                                      followup="  - " + fault)
        repair = grabbed["prompt"]
    finally:
        C.commission = prev_commission
        pj.ep_dir = prev_ep_dir

    check("the first brief has no rejection block", "REJECTED" not in first)
    check("  the repair brief does", "REJECTED" in repair)
    check("  it says the file already exists", "ALREADY EXISTS" in repair)
    check("  it forbids starting again from nothing",
          "start again from nothing" in repair)
    check("  it carries the checker's line into the writer's brief", fault in repair)
    check("  and the original instructions are still there (it is a FRESH spawn)",
          "TRACE OR IT DOES NOT SHIP" in repair)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
