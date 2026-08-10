#!/usr/bin/env python3
"""A′ — the pre-claim drafting pass. Piece 3 of the drafting design.

THE INVARIANT THIS SUITE EXISTS FOR, and it is the reason Shape A′ was chosen over
a `drafting` status:

    i1_never_claims  — the pass must NEVER claim, NEVER set a status and NEVER go
                       near claim_next. What survives because of that is bigger
                       than the pass itself: NO STEP IN `PHASES` RUNS BEFORE THE
                       SCRIPT GATE. This case drives the real function with a rail
                       that RAISES if any of those are touched.

    i2_never_overwrites
                     — the words reach the rail ONLY through
                       seat_script_if_empty. A set_fields() here would defeat
                       piece 1 entirely while every behavioural test still passed.

    the_brief_names_every_source_absolutely
                     — skill discovery walks up from the EPISODE folder and finds
                       nothing for pp-episode-script. Commit c7f4e77 records what
                       that costs: the v1.2 fidelity tightening "silently absent".

    a_missing_capture_is_a_log_not_a_flag
                     — A19: nobody holding a browser can capture an article.

Nothing here spawns a writer or touches the network: the provider and the rail are
both stand-ins. The REAL commission is proved separately on a scratch target.

Run: python engine/test_draft_watch.py
"""
from __future__ import annotations

import os
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

import engine                                                          # noqa: E402
import providers                                                       # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


class Rail:
    """A rail that RAISES on anything the pass is forbidden to do."""

    def __init__(self, queued, seat_returns="row"):
        self.queued = queued
        self.seated = []
        self.seat_returns = seat_returns
        self.forbidden = []

    def list_queued(self):
        return list(self.queued)

    def seat_script_if_empty(self, id, text):
        self.seated.append((id, text))
        return {"id": id} if self.seat_returns == "row" else None

    # --- everything below is a fault if it is ever called ---
    def _no(self, what):
        self.forbidden.append(what)
        raise AssertionError(f"the drafting pass called {what}")

    def claim_next(self, *a, **k):
        self._no("claim_next")

    def claim(self, *a, **k):
        self._no("claim")

    def update_status(self, *a, **k):
        self._no("update_status")

    def set_fields(self, *a, **k):
        self._no("set_fields")

    def flag_needs_look(self, *a, **k):
        self._no("flag_needs_look")

    def reclaim_stale(self, *a, **k):
        self._no("reclaim_stale")

    def release(self, *a, **k):
        self._no("release")

    def delete(self, *a, **k):
        self._no("delete")


class Provider:
    def __init__(self, pp, script_text="Gordon says a great many words.\n"):
        self.pp = Path(pp)
        self.script_text = script_text
        self.commissioned = []

    def dir(self, ep):
        return self.pp / f"PP-EP{int(ep['ep_number']):02d}"

    def _commission_script(self, ep, d, gate=None):
        self.commissioned.append(int(ep["ep_number"]))
        out = Path(d) / "docs/spoken-words.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.script_text, encoding="utf-8")
        return {"status": "ok", "_path": str(out)}


def episode(n, **kw):
    row = {"id": f"id-{n}", "ep_number": n, "status": "queued",
           "script_snapshot": None, "script_doc_url": None, "needs_look": False}
    row.update(kw)
    return row


# A capture shaped like a REAL one: a header with a byline, the article-text
# markers, and a body carrying a racing price. Without the markers the fidelity
# gate has nothing to compare against, and these cases would pass for the wrong
# reason — which is how the first version of this file ran.
CAPTURE = (
    "# A Headline\n"
    "By Roger Dedman — PRACTICAL PUNTING, MARCH 1988\n"
    "notes about repairing a scanner go here and are NOT traceable source\n"
    "---- ARTICLE TEXT BEGINS ----\n"
    "The favourite was 8-1 on the day, and a quarter of the odds is 2-1.\n"
    "---- ARTICLE TEXT ENDS ----\n"
)


def pp_tree(*captures) -> Path:
    root = Path(tempfile.mkdtemp(prefix="pp-draft-"))
    (root / "docs").mkdir()
    for c in captures:
        (root / "docs" / c).write_text(CAPTURE, encoding="utf-8")
    return root


def _calls_made(path: Path, func: str) -> set[str]:
    """Every function name CALLED inside `func`, read from the syntax tree.

    Derived, not grepped: a docstring that mentions claim_next is prose, and a
    call to it is a call. Only the tree can tell them apart.
    """
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == func)
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                # ⚠️ THE RECEIVER IS PART OF THE NAME. Bare method names made
                # `sys.path.insert(0, …)` — a line that writes to nothing — read as the
                # rail's `insert`, so "seat_script_if_empty is the ONLY rail write"
                # failed on a call that touches no rail. What these checks forbid is
                # writing to the RAIL, so the rail's own calls are recorded as such.
                out.add(f.attr)
                if isinstance(f.value, ast.Name) and f.value.id == "rail":
                    out.add(f"rail.{f.attr}")
    return out


def psrc_count(path: Path, needle: str) -> int:
    return path.read_text(encoding="utf-8").count(needle)


def real_brief() -> str:
    """THE BRIEF AS THE WRITER RECEIVES IT — assembled, not read off the source.

    ⚠️ THE FIRST VERSION OF THESE CASES GREPPED providers.py AND FAILED on "the
    opening framing line", because the source splits that phrase across two
    concatenated string literals. The writer never sees the source; it sees the
    assembled prompt. Assert the artefact, not the thing that produces it.
    """
    import commission as com
    pp = pp_tree("EP18-source-article-a-real-article.md")
    prov = providers.RealProvider.__new__(providers.RealProvider)
    prov.pp = pp
    grabbed = {}

    def fake(**kw):
        grabbed.update(kw)
        return {"status": "ok", "_path": "x"}

    prev = com.commission
    com.commission = fake
    try:
        prov._commission_script({"ep_number": 18},
                                Path(tempfile.mkdtemp(prefix="pp-brief-")))
    finally:
        com.commission = prev
    return grabbed["prompt"]


def run_pass(rail_stub, provider):
    lines = []
    prev_rail, prev_log = engine.rail, engine.log
    engine.rail = rail_stub
    engine.log = lambda m, **k: lines.append(str(m))
    try:
        engine._draft_watch(provider)
    finally:
        engine.rail, engine.log = prev_rail, prev_log
    return lines


def main():                                                            # noqa: C901
    print("\n-- the happy path: empty box + captured article -> a draft is seated --")
    pp = pp_tree("EP18-source-article-testing-the-numbers.md")
    prov = Provider(pp)
    r = Rail([episode(18)])
    lines = run_pass(r, prov)
    check("the script was commissioned", prov.commissioned == [18], str(prov.commissioned))
    check("  and seated", len(r.seated) == 1 and r.seated[0][0] == "id-18")
    check("  the seated words are the writer's words",
          r.seated[0][1] == prov.script_text.strip())
    check("  the run log says it is waiting for a person",
          any("waiting for a person" in ln for ln in lines))

    print("\n-- 🔴 I1: IT NEVER CLAIMS, NEVER SETS A STATUS --")
    # The Rail stand-in raises on every forbidden call, so this is not a promise.
    check("no claim, no status change, no flag, no release, no delete",
          r.forbidden == [], str(r.forbidden))

    # ⚠️ WHAT THIS CHECK LOOKS AT MATTERS. The first version grepped the function's
    # SOURCE for "claim_next" and failed — on the docstring sentence explaining that
    # it never calls claim_next. A guard that fires when somebody documents the
    # thing it guards is a guard that gets deleted. So it reads the CALLS, from the
    # syntax tree: prose cannot trip it and a real call cannot hide from it.
    calls = _calls_made(HERE / "engine.py", "_draft_watch")
    for forbidden in ("claim_next", "claim", "update_status", "flag_needs_look",
                      "reclaim_stale", "release", "delete", "set_fields",
                      "checkpoint", "progress"):
        check(f"  it never CALLS {forbidden}()", forbidden not in calls,
              f"calls: {sorted(calls)}")

    print("\n-- 🔴 I2: THE WORDS REACH THE RAIL ONLY THROUGH THE GUARD --")
    check("it calls seat_script_if_empty", "seat_script_if_empty" in calls,
          f"calls: {sorted(calls)}")
    # asked of the RAIL calls, so sys.path.insert cannot masquerade as rail.insert
    check("  which is the ONLY rail write it makes",
          {c.split(".", 1)[1] for c in calls if c.startswith("rail.")}
          & {"set_fields", "insert", "update_status", "checkpoint", "delete"} == set(),
          f"rail calls: {sorted(c for c in calls if c.startswith('rail.'))}")
    r2 = Rail([episode(18)], seat_returns="none")
    prov2 = Provider(pp)
    lines2 = run_pass(r2, prov2)
    check("  when the seat is refused it says nothing was overwritten",
          any("nothing was overwritten" in ln for ln in lines2), str(lines2[-1:]))
    check("  and it does NOT try again by another route", len(r2.seated) == 1)

    print("\n-- who is skipped, and why --")
    for kw, why in [({"script_snapshot": "Jodie already wrote this"}, "the box has text"),
                    ({"script_doc_url": "https://docs.google.com/x"}, "it has a Doc (A5)"),
                    ({"needs_look": True}, "it is flagged"),
                    ({"ep_number": None}, "it has no number")]:
        p = Provider(pp)
        run_pass(Rail([episode(18, **kw)]), p)
        check(f"  skipped: {why}", p.commissioned == [], str(p.commissioned))

    print("\n-- 🔴 A19: A MISSING CAPTURE IS A LOG LINE, NEVER JODIE'S QUEUE --")
    bare = pp_tree()                       # no captures at all
    p = Provider(bare)
    r3 = Rail([episode(18)])
    lines3 = run_pass(r3, p)
    check("nothing was commissioned", p.commissioned == [])
    check("  nothing was seated", r3.seated == [])
    check("  the episode was NOT flagged", r3.forbidden == [], str(r3.forbidden))
    said = " ".join(lines3)
    check("  the run log explains it in plain English",
          "hasn't been captured" in said or "has not been captured" in said, said)
    check("  and the pass carried on rather than dying", True)

    print("\n-- one bad episode does not stop the next --")
    two = pp_tree("EP19-source-article-a-real-one.md")
    p = Provider(two)
    run_pass(Rail([episode(18), episode(19)]), p)
    check("EP18 has no capture and is skipped; EP19 is drafted",
          p.commissioned == [19], str(p.commissioned))

    print("\n-- 🔴 THE BRIEF NAMES EVERY SOURCE BY ABSOLUTE PATH --")
    brief = real_brief()                     # the assembled prompt, not the source
    for needle, what in [
            ("pp-episode-script" + os.sep + "SKILL.md", "the craft skill"),
            ("pp-my-audience-avatar" + os.sep + "SKILL.md", "who Dave is"),
            ("PP-STANDARDS.md", "the governing standard"),
            ("midroll-line-pool.md", "the midroll pool"),
            ("PP-operator-box-rule.md", "how to word what_i_saw"),
            ("source-article", "the article itself")]:
        check(f"  it names {what}", needle in brief, needle)
    repo = str(providers.REPO_DIR)
    check("  every one is an ABSOLUTE path under the repo",
          brief.count(repo) >= 5, f"{brief.count(repo)} absolute repo paths")
    check("  no source is offered as a relative docs/ path",
          "  - docs/" not in brief)
    check("  and it warns the writer the episode has its own docs/",
          "DIFFERENT place" in brief)

    print("\n-- 🔴 THE RULE ABOVE ALL IS IN THE BRIEF, NOT IMPLIED --")
    check("the only-original-prose rule is stated",
          "ONLY ORIGINAL PROSE" in brief)
    check("  it names all four seams",
          all(s in brief for s in ("opening framing line", "transitions between beats",
                                   "midroll invitation", "outro wind-down")))
    check("  it says a paraphrase has FAILED",
          "HAS FAILED" in brief)
    check("  it says fidelity wins over craft", "FIDELITY WINS" in brief)
    check("  and it forbids correcting the article", "never correct the article" in brief)

    print("\n-- 🔴 THE CONCEPT-FINDER OVERRIDE (Jodie, 7 Aug) --")
    check("the brief overrides Step 2", "DO NOT" in brief and "concept finder" in brief)
    check("  and says where the hook comes from instead",
          "wound" in brief and "own language" in brief)

    print("\n-- the writer is never given a shell --")
    import commission as C
    check("Bash is not in the commission's tools", "Bash" not in C.DEFAULT_TOOLS)
    check("  the brief never asks the writer to check its own work",
          "run the check" not in brief.lower() and "python " not in brief)

    print("\n-- 🔴 THE VERDICT INSTRUCTIONS NAME EVERY REQUIRED FIELD --")
    # THE FAULT: the first live script commission wrote a complete, gate-passing
    # script and died returning the verdict. The transcript shows it called
    # StructuredOutput FIVE times with only `status` and `what_i_saw`; the schema
    # rejected all five for the same three missing fields. The old brief mentioned
    # unread_sources only CONDITIONALLY and never named the other two at all.
    #     THE INSTRUCTIONS AND THE SCHEMA DISAGREED, AND THE WRITER BELIEVED THE
    #     INSTRUCTIONS.
    import commission as C2
    for field in C2.VERDICT_SCHEMA["required"]:
        check(f"  the brief names {field!r}", field in brief)
    check("  it says ALL of them are required even when the work went fine",
          "EVEN WHEN THE WORK WENT PERFECTLY" in brief)
    check("  it says a missing field throws the whole job away",
          "thrown away" in brief)
    check("  and it asks for a SHORT what_i_saw (the essay is what broke it)",
          "SHORT" in brief)
    # DERIVED, so a new required field cannot be added without the brief saying so.
    check("  the field list is derived from the schema, not hand-written",
          all(f in C2.verdict_instructions() for f in C2.VERDICT_SCHEMA["required"]))
    src_c = (HERE / "commission.py").read_text(encoding="utf-8")
    vi = src_c.split("def verdict_instructions")[1].split("\ndef ")[0]
    check("  verdict_instructions() reads VERDICT_SCHEMA['required']",
          "VERDICT_SCHEMA['required']" in vi or 'VERDICT_SCHEMA["required"]' in vi)
    check("  and every OTHER call site uses the same text",
          psrc_count(HERE / "providers.py", "com.verdict_instructions()") == 4,
          f"{psrc_count(HERE / 'providers.py', 'com.verdict_instructions()')} call sites")

    print("\n-- 🔴 THE FIDELITY GATE, AS WIRED: A BAD FIGURE IS NOT SEATED --")
    # The module has its own suite. This proves the ENGINE runs it, on the way
    # from the writer to the rail — the wiring, not the checker.
    pp_f = pp_tree("EP18-source-article-a-real-one.md")
    liar = Provider(pp_f, script_text=(
        "He was sent off at eleven to four, which was generous.\n"))
    rl = Rail([episode(18)])
    lines_f = run_pass(rl, liar)
    check("a script stating a figure the article does not is NOT seated",
          rl.seated == [], str(rl.seated))
    said_f = " ".join(lines_f)
    check("  the run log names the figure", "eleven to four" in said_f, said_f[-300:])
    check("  and says nothing was written to the script box",
          "nothing was written to the script box" in said_f)
    check("  the attempt still counted against the bound",
          engine._draft_attempts(liar.dir({"ep_number": 18})) == 1)

    faithful = Provider(pp_f, script_text=(
        "The favourite was eight to one on the day, and a quarter of the odds "
        "is two to one.\n"))
    rl2 = Rail([episode(18)])
    run_pass(rl2, faithful)
    check("a faithful script IS seated", len(rl2.seated) == 1)
    check("  and the ledger is cleared", not engine._draft_ledger_path(
        faithful.dir({"ep_number": 18})).exists())

    print("\n-- 🔴 THE BOUND: A DETERMINISTIC FAULT CANNOT SPEND FOREVER --")
    pp_b = pp_tree("EP18-source-article-a-real-one.md")

    class Failing(Provider):
        def _commission_script(self, ep, d, gate=None):
            self.commissioned.append(int(ep["ep_number"]))
            import commission as C3
            raise C3.CommissionHalt("the writer fell over", detail="deterministic")

    fp = Failing(pp_b)
    lines_b = []
    for _ in range(8):                       # eight passes, as a long night would
        lines_b += run_pass(Rail([episode(18)]), fp)
    check("it stops after exactly 3 attempts, not 8",
          len(fp.commissioned) == engine.DRAFT_ATTEMPT_LIMIT,
          f"{len(fp.commissioned)} commissions")
    said_b = " ".join(lines_b)
    check("  and it says plainly it is being left alone",
          "left alone" in said_b and "Nothing more will be spent" in said_b)
    check("  it says whose problem it is (A19: the studio's)",
          "the studio's to look at" in said_b)
    check("  and how to start it again", ".draft-attempts.json" in said_b)

    print("\n-- the attempt is counted BEFORE the spend, so a crash still counts --")
    pp_c = pp_tree("EP18-source-article-a-real-one.md")

    class Crashing(Provider):
        def _commission_script(self, ep, d, gate=None):
            self.commissioned.append(int(ep["ep_number"]))
            raise KeyboardInterrupt("killed mid-commission")

    cp = Crashing(pp_c)
    for _ in range(5):
        try:
            run_pass(Rail([episode(18)]), cp)
        except KeyboardInterrupt:
            pass
    check("a run killed mid-commission still counts against the bound",
          len(cp.commissioned) == engine.DRAFT_ATTEMPT_LIMIT,
          f"{len(cp.commissioned)} commissions")

    print("\n-- a seated script clears the ledger --")
    pp_d = pp_tree("EP18-source-article-a-real-one.md")
    gp = Provider(pp_d)
    run_pass(Rail([episode(18)]), gp)
    check("the ledger is gone after a successful seat",
          not engine._draft_ledger_path(gp.dir({"ep_number": 18})).exists())

    print("\n-- the human gate is untouched --")
    check("claim_next still requires both halves of the Script Gate",
          "title_approved" in (HERE / "rail.py").read_text(encoding="utf-8")
          .split("def claim_next")[1].split("\ndef ")[0])
    check("  and the pass writes neither of them",
          "title_approved" not in str(r.seated) and "script_read" not in calls)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
