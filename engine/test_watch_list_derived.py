"""THE STALE-CODE WATCH LIST MUST BE DERIVED, NOT ENUMERATED.

WHY (EP16, 5 Aug 2026). `_CODE_FILES` was a hand-written list of three files.
`preflight_episode_json.py` was fixed at 10:43; the running engine kept the broken
copy in memory for six hours and flagged EP16 on a false positive that no longer
existed on disk. The guard ran about a thousand times that day and saw nothing,
because the file that changed was not one of its three.

    IF A GUARD'S COVERAGE IS A LIST SOMEBODY MAINTAINS, IT IS ALREADY BROKEN.
    YOU HAVE SIMPLY NOT MET THE MISSING ITEM YET.   (CLAUDE.md fault #7)

The case that proves the fix: the three modules that were INVISIBLE before are
watched now, and nobody had to name them.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine

ENGINE_DIR = Path(__file__).resolve().parent


class WatchListIsDerived(unittest.TestCase):

    def test_the_three_that_were_invisible_are_now_watched(self):
        """THE CASE THAT PROVES IT — named, per CLAUDE.md fault #4.

        preflight_episode_json is the one that actually cost the hour. The other
        two were equally unwatched and nobody had noticed.
        """
        watched = {p.name for p in engine._watched_files()}
        for name in ("preflight_episode_json.py", "check_page_images.py", "gitgate.py"):
            self.assertIn(name, watched,
                          f"{name} is imported by the engine and must be watched")

    def test_the_original_three_are_still_watched(self):
        """The derivation must not have LOST anything the hand-list had."""
        watched = {p.name for p in engine._watched_files()}
        for name in ("engine.py", "providers.py", "rail.py"):
            self.assertIn(name, watched)

    def test_nothing_outside_the_engine_directory_is_watched(self):
        """Scope: the engine's own code, not every module Python has loaded.

        Without the parent-directory filter this would watch the whole stdlib and
        every site-package — thousands of stats per poll, and a pip install would
        restart the engine.
        """
        for p in engine._watched_files():
            self.assertEqual(ENGINE_DIR, p.parent,
                             f"{p} is outside ENGINE_DIR and should not be watched")
            self.assertEqual(".py", p.suffix)

    def test_a_changed_mtime_is_detected_and_named(self):
        """End to end, on a real file, without touching anything that matters."""
        probe = ENGINE_DIR / "preflight_episode_json.py"
        self.assertIn(probe, engine._CODE_MTIMES,
                      "the probe file must be in the baseline to test a change")
        original = engine._CODE_MTIMES[probe]
        try:
            engine._CODE_MTIMES[probe] = original - 1234.0     # pretend it moved
            self.assertEqual(probe.name, engine._code_changed(),
                             "a changed mtime on an imported module must be reported "
                             "BY NAME, so the log says which file")
        finally:
            engine._CODE_MTIMES[probe] = original
        self.assertIsNone(engine._code_changed(), "and must go quiet again after")

    def test_a_late_import_is_baselined_not_reported_as_changed(self):
        """A module imported AFTER start must not look like an edit.

        Otherwise the first lazy import would exit the engine for nothing — a
        guard that cries wolf is a guard someone switches off.
        """
        probe = ENGINE_DIR / "preflight_episode_json.py"
        saved = engine._CODE_MTIMES.pop(probe)                 # pretend it is new
        try:
            self.assertIsNone(engine._code_changed(),
                              "a newly seen module must be baselined, not reported")
            self.assertIn(probe, engine._CODE_MTIMES,
                          "and it must be added to the baseline so a LATER edit fires")
        finally:
            engine._CODE_MTIMES[probe] = saved


if __name__ == "__main__":
    unittest.main(verbosity=2)
