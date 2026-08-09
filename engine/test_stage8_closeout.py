#!/usr/bin/env python3
"""STAGE-8 CLOSE-OUT IS A CHORE, NOT A DECISION.

    python engine/test_stage8_closeout.py

A published episode whose folder still carries the bare PP-EP<NN> name used to raise
needs_look — and the message printed a raw shell command at a browser operator:

    Run, from the repo: python engine/rename_episode.py EP19 "<title>" --apply

An A19 operator-box violation twice over: it badges Jodie's queue with the studio's own
work, and asks a person holding a browser to run a command they cannot run. The old
docstring defended it — "never rename automatically (Drive sync + open files make that a
human-timed step)" — which is a real risk answered the wrong way: a lock means RETRY,
not "hand it to a human".

🔒 THE SAFETY PROPERTY THIS SUITE EXISTS FOR: the close-out may only ever clear ITS OWN
flag. A needs_look raised by anything else is a human being asked a real question, and
an automatic pass that wipes one is far worse than the chore it replaces.

Hermetic: rail and the rename tool are both stubbed, no folder is touched.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import engine                                                        # noqa: E402

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


class Harness:
    """The rail, the filesystem and the rename tool, all faked and all watched."""

    def __init__(self, rows, bare_dirs, rename_ok=True):
        self.rows, self.bare, self.rename_ok = rows, set(bare_dirs), rename_ok
        self.writes, self.renamed, self.logs = {}, [], []

    def __enter__(self):
        h = self
        self._o = (engine.rail.list_all, engine.rail.set_fields,
                   engine.rail.flag_needs_look, engine.subprocess.run,
                   engine.PP_VIDEOS, engine.log, engine._approved_title)

        class FakePath(type(Path())):
            pass

        engine.rail.list_all = lambda: h.rows
        engine.rail.set_fields = lambda i, f: h.writes.setdefault(i, {}).update(f)
        engine.rail.flag_needs_look = lambda i, m: h.writes.setdefault(
            i, {}).update({"needs_look": True, "needs_look_message": m})
        engine.log = lambda m: h.logs.append(str(m))
        engine._approved_title = lambda ep, d: "A Real Title"

        class Res:
            def __init__(self, ok):
                self.returncode = 0 if ok else 1
                self.stdout = ""
                self.stderr = "" if ok else "Drive says the folder is in use"

        def fake_run(args, **kw):
            nn = args[2]
            h.renamed.append(nn)
            if h.rename_ok:
                h.bare.discard(f"PP-{nn}")          # the rename succeeded
            return Res(h.rename_ok)

        engine.subprocess.run = fake_run

        class FakeRoot:
            def __truediv__(self, name):
                class D:
                    def is_dir(_s):
                        return name in h.bare
                    name_ = name
                return D()

            def glob(self, pat):
                stem = pat.replace("-*", "")
                if stem in h.bare:
                    return []
                class N:
                    name = stem + "-a-real-title"
                    def is_dir(_s):
                        return True
                return [N()]

        engine.PP_VIDEOS = FakeRoot()
        return self

    def __exit__(self, *a):
        (engine.rail.list_all, engine.rail.set_fields, engine.rail.flag_needs_look,
         engine.subprocess.run, engine.PP_VIDEOS, engine.log,
         engine._approved_title) = self._o
        return False


def row(n, **kw):
    r = {"id": f"id{n}", "ep_number": n, "status": "published",
         "needs_look": False, "needs_look_message": None}
    r.update(kw)
    return r


# ------------------------------------------------------------------- 1 -----
def _it_renames_and_raises_nothing():
    with Harness([row(16)], bare_dirs=["PP-EP16"]) as h:
        engine._stage8_watch()
    assert h.renamed == ["EP16"], f"the rename was not run: {h.renamed}"
    w = h.writes.get("id16", {})
    assert w.get("needs_look") is False, f"it raised or left a flag: {w}"
    assert w.get("drive_folder"), f"drive_folder was not recorded on the rail: {w}"
    assert not any("Run, from the repo" in x for x in h.logs), \
        "it is still printing a shell command at a human"


case("a published episode is renamed automatically, with no flag raised",
     _it_renames_and_raises_nothing)


# ------------------------------------------------------------------- 2 -----
def _it_clears_its_own_stale_flag():
    """The backlog case: the flag is already up from the old behaviour."""
    with Harness([row(17, needs_look=True,
                      needs_look_message="PP-EP17 … (Stage-8 close-out). Run, from …")],
                 bare_dirs=["PP-EP17"]) as h:
        engine._stage8_watch()
    assert h.renamed == ["EP17"], f"an already-flagged episode was skipped: {h.renamed}"
    assert h.writes.get("id17", {}).get("needs_look") is False, \
        f"its own flag was left up: {h.writes}"


case("it picks up an episode ALREADY carrying the old flag, and clears it",
     _it_clears_its_own_stale_flag)


# ------------------------------------------------------------------- 3 -----
def _it_never_touches_someone_elses_flag():
    """🔒 THE ONE THAT MATTERS. A real question must survive an automatic pass."""
    with Harness([row(18, needs_look=True,
                      needs_look_message="Have a look at the thumbnail: the hero crop "
                                         "needs your eye.")],
                 bare_dirs=["PP-EP18"]) as h:
        engine._stage8_watch()
    assert h.renamed == [], (
        "it renamed a folder for an episode whose flag is a HUMAN QUESTION — the "
        "rename may be harmless but the flag clear that follows is not")
    assert "id18" not in h.writes, (
        f"IT CLEARED A HUMAN'S FLAG: {h.writes}. A thumbnail-crop question would "
        f"vanish from the board and nobody would ever be asked it.")


case("a needs_look raised by anything else is left completely alone",
     _it_never_touches_someone_elses_flag)


# ------------------------------------------------------------------- 4 -----
def _a_locked_folder_is_retried_not_escalated():
    """Drive sync or an open file. The old code's worry, answered properly."""
    with Harness([row(19)], bare_dirs=["PP-EP19"], rename_ok=False) as h:
        engine._stage8_watch()
    assert "id19" not in h.writes or not h.writes["id19"].get("needs_look"), \
        f"a locked folder was escalated to a human: {h.writes}"
    assert any("retrying next time" in x for x in h.logs), \
        f"the failure was not logged for the next pass: {h.logs}"


case("a folder Drive has locked is logged and retried, never escalated",
     _a_locked_folder_is_retried_not_escalated)


# ------------------------------------------------------------------- 5 -----
def _an_unpublished_episode_is_ignored():
    with Harness([row(20, status="building")], bare_dirs=["PP-EP20"]) as h:
        engine._stage8_watch()
    assert h.renamed == [], "it renamed an episode that is still being built"


case("an episode that is not published is not touched", _an_unpublished_episode_is_ignored)


print(f"\nstage-8 close-out: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
