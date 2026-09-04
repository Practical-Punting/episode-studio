#!/usr/bin/env python3
"""The number check does not read the approved midroll pool lines — and ONLY them.

JODIE'S RULING, 4 Sep 2026, verbatim in substance: the number check exists to stop the
WRITER inventing or altering a figure about the article. The midroll pool lines are not
the writer's output — they are standing furniture she approved, and they make no claim
about the article at all. So script text that is a VERBATIM, EXACT match to a line in
the approved pool is not writer-authored, and the check does not apply to it. Everything
else is checked exactly as it was.

    Exact match only. A pool line altered by a word, a comma or a dash is NOT the pool
    line and is checked in full. Matched against docs/midroll-line-pool.md itself.

WHAT IT COST BEFORE: EP46 burned all three drafting attempts on "Pause there a second"
(L6) being read as a figure the article never states. The same line lands on every tenth
episode, and L8 opens "Two seconds".

CONTROLS FIRST (CLAUDE.md §4b). Case (a) — the real rejected EP46 draft, L6 verbatim,
against the real EP46 capture and the packaging the build feeds — was watched going RED
on the old gate. Cases (b) and (c) must be caught on BOTH the old and the new gate; they
are here so nobody can widen the exemption without watching them go red.

THE LOOPHOLE CONTROLS are the ones Jodie said she cares about most: a writer must not be
able to escape the check by wrapping an invented figure in something that merely
resembles a pool line. A separate scratchpad control proved these fixtures BITE — a naive
"paragraph starts with a pool line" matcher lets the wrapped figure through.

Fixtures are the real artefacts, frozen on the day: engine/testdata/ep46-draft-REJECTED-
on-L6-2026-09-04.spoken-words.txt (attempt 3's script, as written) and
engine/testdata/ep46-capture-2026-09-04.md (the article as captured).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import script_fidelity as F                                            # noqa: E402

DRAFT = (HERE / "testdata/ep46-draft-REJECTED-on-L6-2026-09-04.spoken-words.txt").read_text(encoding="utf-8")
CAP = (HERE / "testdata/ep46-capture-2026-09-04.md").read_text(encoding="utf-8")

# The pool, parsed here INDEPENDENTLY of the module under test, with the contract the pool
# file itself names: "heading, then immediately the line". If the module's parser drifts
# from this, a case below says so.
POOL_MD = (REPO / "docs/midroll-line-pool.md").read_text(encoding="utf-8").replace("\r\n", "\n")
POOL = {m.group(1): m.group(2).strip()
        for m in re.finditer(r"^### (L\d)\n> (.+?)$", POOL_MD, re.M)}
L6, L8 = POOL["L6"], POOL["L8"]

# EP46's packaging AS THE BUILD FEEDS IT: the rail row's hook, byline and number, through
# the engine's own function (CLAUDE.md §1 sibling: pass exactly what the call site passes).
EP46_ROW = {"hook": "The Meaning of Form - Part 2", "byline": "Digging for Winners",
            "ep_number": 46}
try:
    import engine as E                                                 # noqa: E402
    LICENSED = E._approved_packaging_text(EP46_ROW)
except Exception as _e:                                                # noqa: BLE001
    LICENSED = "The Meaning of Form - Part 2 \n Digging for Winners \n episode 46"
    print(f"  (engine not importable here — {type(_e).__name__}; using the packaging text "
          f"verbatim as the rail holds it)")

INVENTED = "Roughly ninety-four per cent of favourites are beaten."   # nowhere in the article
PLAIN = "Ted and Alan say form is the record of a horse's past performances."

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def run(script, allowed=None):
    return F.check(script, CAP, LICENSED, allowed)


def figs(problems):
    """The figures a list of blockers names, for readable assertions."""
    return [m.group(1) for p in problems for m in [re.search(r"says '([^']+)'", p)] if m]


def main():                                                            # noqa: C901
    assert L6.startswith("Pause there a second."), L6
    assert L8.startswith("Two seconds,"), L8
    assert L6 in DRAFT, "the frozen EP46 draft no longer carries L6 verbatim"

    print("\n-- (a) CONTROL: the real EP46 draft, L6 verbatim, must PASS --")
    waved = []
    got = run(DRAFT, waved)
    check("the rejected EP46 draft has NO untraceable figure once L6 is not the writer's",
          got == [], f"{len(got)} blocker(s): {figs(got)}")
    check("  the gate still LOOKED — it found dozens of figures in the draft",
          len(F.figures(DRAFT)) > 40, f"{len(F.figures(DRAFT))} figures")
    check("  and the waiver is DECLARED, naming L6, never silent",
          any("L6" in w for w in waved), str(waved))

    print("\n-- (b) the same line ALTERED is not the pool line, and is checked in full --")
    inside = DRAFT.replace("worth your time so far", "worth your eleven to four so far")
    got = run(inside)
    check("a figure slipped INSIDE L6 is caught", "eleven to four" in figs(got), str(figs(got)))
    check("  and so is 'second', because the paragraph is no longer the pool line",
          "second" in figs(got), str(figs(got)))
    one_word = DRAFT.replace("worth your time so far", "worth your money so far")
    check("one word changed -> 'second' is caught as before",
          "second" in figs(run(one_word)), str(figs(run(one_word))))
    no_comma = DRAFT.replace("Right you are. Where were we.", "Right you are Where were we.")
    check("one full stop removed -> 'second' is caught as before",
          "second" in figs(run(no_comma)), str(figs(run(no_comma))))
    curly = DRAFT.replace("all I'd ask of you", "all I’d ask of you")
    check("one apostrophe changed straight -> curly is a different line -> caught",
          "second" in figs(run(curly)), str(figs(run(curly))))

    print("\n-- (c) an ordinary sentence with an invented figure is caught exactly as today --")
    got = run(DRAFT + "\n\n" + INVENTED)
    check("the invented figure is caught while L6 in the same script is still waived",
          figs(got) == ["ninety four"], str(figs(got)))
    check("  and the message is the gate's own wording, unchanged",
          bool(got) and "never states that figure" in got[0])
    got2 = run(PLAIN + "\n\n" + INVENTED)
    check("a script with NO pool line at all: the invented figure is caught",
          figs(got2) == ["ninety four"], str(figs(got2)))
    check("  and the true article figure passes as before",
          run("They regard recent form as being between one and fourteen days.") == [])

    print("\n-- 🔴 THE LOOPHOLE CONTROLS: resembling a pool line buys nothing --")
    wrapped = PLAIN + "\n\n" + L6 + " " + INVENTED
    got = run(wrapped)
    check("a sentence APPENDED to the invitation, same paragraph: its figure is caught",
          "ninety four" in figs(got), str(figs(got)))
    check("  while L6 itself was still waived (only 'ninety four per cent' reported)",
          figs(got) == ["ninety four"], str(figs(got)))
    prefixed = PLAIN + "\n\n" + INVENTED + " " + L6
    check("a sentence PREPENDED to the invitation: caught",
          "ninety four" in figs(run(prefixed)), str(figs(run(prefixed))))
    first_sentence = PLAIN + "\n\nPause there a second."
    check("the first sentence of L6 on its own is NOT the pool line -> 'second' caught",
          "second" in figs(run(first_sentence)), str(figs(run(first_sentence))))
    sandwiched = PLAIN + "\n\n" + L6.replace("Pause there a second. ",
                                            "Pause there a second. " + INVENTED + " ")
    check("an invented figure SANDWICHED inside the line: both it and 'second' caught",
          {"ninety four", "second"} <= set(figs(run(sandwiched))),
          str(figs(run(sandwiched))))
    two_lines = PLAIN + "\n\n" + L6 + "\n\n" + L8 + "\n\n" + INVENTED
    got = run(two_lines)
    check("two pool lines in one script are both waived; the invented figure is still caught",
          figs(got) == ["ninety four"], str(figs(got)))

    print("\n-- the ONE allowance is whitespace between words, because the file wraps --")
    wrapped_ws = PLAIN + "\n\n" + L6.replace(" a like tells the thing", "\na like tells the thing")
    check("L6 re-wrapped across a line break is still L6 -> passes", run(wrapped_ws) == [],
          str(figs(run(wrapped_ws))))
    crlf = (PLAIN + "\r\n\r\n" + L6).replace(" so subscribe", "\r\nso subscribe")
    check("  and with CRLF wraps", run(crlf) == [], str(figs(run(crlf))))
    wrap_plus_word = wrapped_ws.replace("the thing to show it", "the thing to show it to it")
    check("  but a wrap PLUS an added word is not L6 -> 'second' caught",
          "second" in figs(run(wrap_plus_word)), str(figs(run(wrap_plus_word))))

    print("\n-- only the approved bytes are removed; everything either side survives --")
    rest, cut = F.without_pool_lines("alpha " + L6 + " omega")
    check("the cut leaves exactly the words either side", rest.split() == ["alpha", "omega"],
          repr(rest[:80]))
    check("  and names the line it cut", cut == ["L6"], str(cut))
    rest2, cut2 = F.without_pool_lines(PLAIN + " " + INVENTED)
    check("a script with no pool line is returned untouched, nothing named",
          rest2 == PLAIN + " " + INVENTED and cut2 == [], str(cut2))
    waved2 = []
    run(PLAIN, waved2)
    check("  and nothing is declared as waived", waved2 == [], str(waved2))

    print("\n-- the pool is read from docs/midroll-line-pool.md, not from a copy --")
    mod = F.midroll_pool()
    check("the module's parse matches the independent parse of the same file", mod == POOL,
          f"module {sorted(mod)} vs file {sorted(POOL)}")
    check("  ten lines, L0..L9", sorted(mod) == [f"L{i}" for i in range(10)], str(sorted(mod)))

    print("\n-- every one of the ten lines, verbatim, passes; every one altered is checked --")
    for lid, line in sorted(POOL.items()):
        got = run(PLAIN + "\n\n" + line)
        check(f"{lid} verbatim passes", got == [], str(figs(got)))
        altered = line.replace("this video", "this clip", 1)
        rest, cut = F.without_pool_lines(PLAIN + "\n\n" + altered)
        check(f"  {lid} with one word changed is NOT cut out", cut == [] and altered in rest,
              str(cut))

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:")
        for f in FAIL:
            print("  -", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
