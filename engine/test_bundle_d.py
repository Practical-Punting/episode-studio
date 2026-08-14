#!/usr/bin/env python3
"""BUNDLE D — the sleep check (D11b) and the per-step watchdog's engine half (D13).

Written to FAIL on the unfixed tree. Nothing here reads this repo's own source: each
check drives a real function and asserts what it DOES.

REAL DATA THIS IS BUILT ON, measured 3 Aug 2026 on Jodie's machine AFTER she set the
power plan to never sleep:
    Current AC Power Setting Index: 0x00000000   ->    0s = never   ✓
    Current DC Power Setting Index: 0x000000b4   ->  180s = 3 min   ✗
She changed the setting sincerely and changed the WRONG HALF. Windows keeps separate
sleep timers for mains and battery, and EP14's fourteen lost hours happened on battery.
A person can do this correctly and still be wrong, so the engine must CHECK it.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine                                                       # noqa: E402
import supervisor as sup                                            # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                               # noqa: BLE001
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


# ============================================================ D11b — the sleep check
# powercfg output, verbatim in shape. 0x0 = never; anything else is seconds.
def pc(ac, dc):
    return (
        "Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)\n"
        "  Subgroup GUID: 238c9fa8-0aad-41ed-83f4-97be242c8f20  (Sleep)\n"
        "    Power Setting GUID: 29f6c1db-86da-48c5-9fdb-f2b67b1f44da  (Sleep after)\n"
        f"    Current AC Power Setting Index: 0x{ac:08x}\n"
        f"    Current DC Power Setting Index: 0x{dc:08x}\n")


def _the_real_machine_today_is_caught():
    """THE ACTUAL READING from Jodie's laptop after she 'fixed' it."""
    p = sup.standby_problem(lambda: pc(0x0, 0xb4))
    assert p, ("the check passes the machine as it ACTUALLY IS RIGHT NOW — mains set to "
               "never, battery still sleeping after 3 minutes. That is the exact state "
               "that cost fourteen hours, and it must not read as fine.")
    assert "battery" in p.lower(), f"the message does not say WHICH half is wrong:\n{p}"
    assert "3 min" in p or "180" in p, f"the message does not say how long:\n{p}"


case("sleep: the real machine today (AC never, DC 3 min) is CAUGHT",
     _the_real_machine_today_is_caught)


def _both_halves_never_is_the_only_pass():
    assert sup.standby_problem(lambda: pc(0x0, 0x0)) is None, \
        "both halves set to never should pass"


case("sleep: both halves at never is the only clean pass",
     _both_halves_never_is_the_only_pass)


def _mains_asleep_is_caught_too():
    p = sup.standby_problem(lambda: pc(0x384, 0x0))
    assert p and "mains" in p.lower(), \
        f"a machine that sleeps on MAINS was not caught: {p!r}"


case("sleep: the mains half is checked too, not just the battery half",
     _mains_asleep_is_caught_too)


def _it_fails_OPEN_when_it_cannot_tell():
    """A parsing bug must never brick the studio."""
    for bad in (lambda: "", lambda: "nonsense", lambda: (_ for _ in ()).throw(OSError("no powercfg"))):
        assert sup.standby_problem(bad) is None, (
            "the check REFUSED on output it could not parse. A guard that cannot read "
            "its input must fail open and say so, or a powercfg change stops the studio.")


case("sleep: it fails OPEN when it cannot read the settings",
     _it_fails_OPEN_when_it_cannot_tell)


def _the_supervisor_refuses_to_start_into_a_sleeping_machine():
    problem = sup.environment_problem(standby=lambda: pc(0x0, 0xb4))
    assert problem, ("the supervisor starts the engine on a machine that will fall "
                     "asleep under it. Sleep is the single largest cost in this "
                     "project's history and the supervisor already refuses to start "
                     "with no G: and no .env — this belongs in exactly that gate.")
    assert "sleep" in problem.lower() or "standby" in problem.lower(), \
        f"refused for an unclear reason:\n{problem}"


case("sleep: the supervisor REFUSES to start into a machine that will sleep",
     _the_supervisor_refuses_to_start_into_a_sleeping_machine)


def _a_healthy_machine_is_not_blocked():
    assert sup.environment_problem(standby=lambda: pc(0x0, 0x0)) is None, \
        "a machine set to never sleep was blocked anyway"


case("sleep: a machine set to never sleep starts normally",
     _a_healthy_machine_is_not_blocked)


# ============================================================ D13 — the engine half
def _the_engine_records_which_step_started_and_when():
    """Nothing today records the START of a step, only the finish of completed ones.

    So "how long has THIS step been running" is not computable, which is why EP14 sat
    for three and a half days with a healthy heartbeat and nothing could say so.
    """
    seen = {}

    class C:
        state = {}
        mock = False

        def check_alive(self):
            pass

        def save(self):
            seen["saved"] = dict(self.state)

    ctx = C()
    engine.mark_step_started(ctx, "assemble_passB")
    cur = ctx.state.get("current")
    assert cur, ("build_state carries no record of the step in flight, so the board "
                 "cannot tell a stuck step from a working one")
    assert cur.get("step") == "assemble_passB", f"wrong step recorded: {cur}"
    assert cur.get("started_at"), "no start time recorded"
    assert "budget_s" in cur, ("no expected duration recorded — without one the board "
                               "can say how long, but not whether that is ABNORMAL")
    assert seen.get("saved"), "the mark was never saved, so a stuck step loses it"


case("watchdog: the engine records which step is in flight, when it started, "
     "and what is normal", _the_engine_records_which_step_started_and_when)


def _steps_that_wait_on_a_human_have_no_budget():
    """poll_heygen waits for Jodie to run the HeyGen render. That can take days and
    there is no flag up. It must never be called stuck."""
    class C:
        state = {}
        mock = False

        def check_alive(self):
            pass

        def save(self):
            pass

    ctx = C()
    engine.mark_step_started(ctx, "heygen_download")
    assert ctx.state["current"]["budget_s"] is None, (
        "heygen_download has a time budget, so a legitimate wait for Jodie to do the "
        "render would raise a false alarm. A step that waits on a human BY DESIGN "
        "must be marked as such.")


case("watchdog: a step that waits on a human by design carries no budget",
     _steps_that_wait_on_a_human_have_no_budget)


def _a_finished_step_clears_the_marker():
    class C:
        state = {"current": {"step": "x", "started_at": "now", "budget_s": 60}}
        mock = False

        def check_alive(self):
            pass

        def save(self):
            pass

    ctx = C()
    engine.clear_step_started(ctx)
    assert not ctx.state.get("current"), \
        "the in-flight marker survived the step, so a finished episode reads as stuck"


case("watchdog: finishing a step clears the in-flight marker",
     _a_finished_step_clears_the_marker)




# ── C4 / 3b — HIBERNATE WAS THE HOLE IN THE SLEEP GUARD ───────────────────────
# `standby_problem` has read STANDBYIDLE since EP14 — both halves, because setting one
# and not the other looks fixed and is not. HIBERNATEIDLE is a THIRD and FOURTH timer and
# was never read at all: a machine set to "never sleep" can still hibernate out from under
# a build, suspending the engine the same way and costing the same hours.
#     The docstring's own lesson — a person can do this correctly and still be wrong —
# applied to the guard as much as to Jodie.
def pc2(s_ac, s_dc, h_ac, h_dc):
    """powercfg output for BOTH subgroups, in the order supervisor asks for them."""
    return pc(s_ac, s_dc) + (
        "  Subgroup GUID: 238c9fa8-0aad-41ed-83f4-97be242c8f20  (Sleep)\n"
        "    Power Setting GUID: 9d7815a6-7ee4-497e-8888-515a05f02364  (Hibernate after)\n"
        f"    Current AC Power Setting Index: 0x{h_ac:08x}\n"
        f"    Current DC Power Setting Index: 0x{h_dc:08x}\n")


def _hibernate_is_caught_when_sleep_is_already_off():
    """The state a careful person lands on: sleep set to never, hibernate untouched."""
    p = sup.standby_problem(lambda: pc2(0x0, 0x0, 0x0, 0x708))
    assert p, ("sleep is off on both halves and HIBERNATE still fires after 30 min on "
               "battery — the build is suspended just the same, and this read as fine")
    assert "hibernate" in p.lower(), f"the message does not name hibernate:\n{p}"
    assert "battery" in p.lower(), f"the message does not say WHICH half:\n{p}"
    assert "hibernate-timeout-dc 0" in p, f"the message does not say how to fix it:\n{p}"


case("hibernate: caught even when sleep is already set to never",
     _hibernate_is_caught_when_sleep_is_already_off)


def _all_four_timers_off_is_the_only_pass():
    assert sup.standby_problem(lambda: pc2(0x0, 0x0, 0x0, 0x0)) is None, \
        "all four timers at never should be the clean pass"


case("hibernate: all four timers at never is the only clean pass",
     _all_four_timers_off_is_the_only_pass)


def _sleep_and_hibernate_are_named_separately():
    p = sup.standby_problem(lambda: pc2(0x384, 0x0, 0x0, 0x708))
    assert "sleep on MAINS" in p, f"sleep half not named:\n{p}"
    assert "hibernate on BATTERY" in p, f"hibernate half not named:\n{p}"
    assert "standby-timeout-ac 0" in p and "hibernate-timeout-dc 0" in p, \
        f"the fix must name BOTH commands, or she fixes half of it again:\n{p}"


case("hibernate: sleep and hibernate are reported and fixed SEPARATELY",
     _sleep_and_hibernate_are_named_separately)


def _still_fails_open_and_still_handles_sleep_only_output():
    """Older powercfg, or a machine that reports only the one subgroup."""
    assert sup.standby_problem(lambda: pc(0x0, 0x0)) is None, \
        "sleep-only output with both halves off must still pass"
    p = sup.standby_problem(lambda: pc(0x0, 0xb4))
    assert p and "battery" in p.lower(), (
        "sleep-only output must still be graded — the hibernate change must not have "
        "made the original check depend on a subgroup that may not be reported")


case("hibernate: sleep-only output is still graded, and still fails open",
     _still_fails_open_and_still_handles_sleep_only_output)

print(f"\nbundle D: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
