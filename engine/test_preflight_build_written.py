"""THE SET OF BUILD-WRITTEN KEYS MUST NOT GO STALE — so a machine keeps it honest.

WHY THIS EXISTS (EP16, 5 Aug 2026). The pre-flight runs at `audit_inputs`, at the
START of a build, and measures the episode against two FINISHED episodes. Every key
the BUILD writes into episode.json later in the run is therefore present in both
references and absent from the file being judged — and was reported as a missing
convention, as a BLOCKER. `build.leads` would have halted EP16, and every episode
after it, at the first step of the build.

    A CHECK THAT RUNS AT TIME T MUST BE TESTED AGAINST INPUTS AS THEY EXIST AT TIME T.

E26 was 16/16 green. Every fixture was a finished episode.json — the right FILE at
the wrong MOMENT.

⚠️ AND THE FIX MUST NOT BE A LIST SOMEBODY REMEMBERS TO UPDATE. That is the exact
shape that let EP15's e-book cover through: assert_standing_assets() knew a list of
standing pages, and `ebook-cover.png` was not on it. So this test GREPS THE CODE for
places that write into a build dict and fails if any key it finds is not exempt.
The next build-written key cannot silently start blocking episodes.
"""
import ast
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight_episode_json as pf

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude/skills/pp-episode-production/scripts"

# Files that write into episode.json's build{} block. Kept broad on purpose: the
# point is to catch a NEW writer, so we scan whole directories rather than naming
# the files we already know about.
SCAN_DIRS = (REPO / "engine", SKILL)

# `build["leads"] = ...`  ·  `build['midroll']['at'] = ...`  ·  b["leads"] = ...
ASSIGN = re.compile(
    r"""\b(?:build|b|B)\s*((?:\[\s*["'][\w.]+["']\s*\])+)\s*=(?!=)""")


def _keys_from_subscripts(chain: str) -> str:
    """['midroll']['at']  ->  build.midroll.at"""
    parts = re.findall(r"""\[\s*["']([\w.]+)["']\s*\]""", chain)
    return "build." + ".".join(parts)


def _writes_found() -> dict[str, list[str]]:
    """{dotted key: [where it is written]} across every scanned file."""
    found: dict[str, list[str]] = {}
    for d in SCAN_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.py")):
            if p.name.startswith("test_"):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                for m in ASSIGN.finditer(line):
                    key = _keys_from_subscripts(m.group(1))
                    found.setdefault(key, []).append(f"{p.name}:{i}")
    return found


class BuildWrittenKeysStayHonest(unittest.TestCase):

    def test_every_build_write_in_the_code_is_exempt(self):
        """THE CASE THAT PROVES IT: grep for build[...] = and demand each key be exempt.

        If someone adds `build["holds"] = ...` to derive_card_timings.py tomorrow and
        does not exempt it, this fails — instead of every episode halting at
        audit_inputs and somebody switching the pre-flight off.
        """
        found = _writes_found()
        self.assertTrue(found, "the grep found NO build[...] = assignments at all, "
                               "which means the pattern has stopped matching and this "
                               "test is asleep. Fix the pattern, do not delete the test.")
        unexempt = {k: v for k, v in found.items() if not pf._is_build_written(k)}
        self.assertEqual(
            {}, unexempt,
            "these keys are WRITTEN BY THE BUILD but are not exempt in "
            "preflight_episode_json.BUILD_WRITTEN_KEYS, so the pre-flight will report "
            "them as a missing convention and HALT every episode at audit_inputs:\n"
            + "\n".join(f"      {k}   written at {', '.join(v)}" for k, v in sorted(unexempt.items())))

    def test_leads_is_the_key_that_caused_this(self):
        """Name the specific case, per CLAUDE.md fault #4: build.leads is the one
        that would have halted EP16, and it must stay exempt."""
        self.assertTrue(pf._is_build_written("build.leads"))
        self.assertTrue(pf._is_build_written("build.midroll.at"))

    def test_an_authored_key_is_NOT_exempt(self):
        """The exemption must not be so broad it swallows real conventions.

        build.standing is AUTHORED, and its absence crashes assemble_episode.py with
        a raw KeyError: None in front of the operator. It must still be caught.
        """
        for authored in ("build.standing", "build.standing.endcard",
                         "build.default_hold", "build.midroll.dur", "build.music"):
            self.assertFalse(pf._is_build_written(authored),
                             f"{authored} is authored by a human and must stay checked")

    def test_a_script_time_file_missing_only_leads_is_CLEAN(self):
        """END TO END, at the moment the check actually runs.

        A file identical to a finished episode except that the build has not run yet
        must come back with NO blockers. This is the case E26's own 16 tests could not
        express, because every one of their fixtures was a finished episode.
        """
        import copy
        ref = {
            "build": {"default_hold": 10.0, "leads": {"C1": 5.0, "C2": 6.0},
                      "midroll": {"at": 300.0, "dur": 16.0},
                      "standing": {"title": "TITLE", "endcard": "END",
                                   "warranty": "WARRANTY"}},
            "beats": [{"n": 1, "framing": "WIDE", "card": "C1", "broll": None}],
            "cards": [{"id": "C1", "beat": 1, "layout": "panel-push"},
                      {"id": "TITLE", "beat": 1, "layout": "fullscreen"},
                      {"id": "END", "beat": 1, "layout": "fullscreen"},
                      {"id": "WARRANTY", "beat": 1, "layout": "fullscreen"}],
        }
        script_time = copy.deepcopy(ref)
        del script_time["build"]["leads"]              # not written until the SRT exists
        script_time["build"]["midroll"]["at"] = None   # ditto

        res = pf.preflight(script_time, [copy.deepcopy(ref), copy.deepcopy(ref)])
        self.assertEqual([], res["must"],
                         "a script-time file that is missing ONLY the build-written "
                         "keys must not be blocked:\n  " + "\n  ".join(res["must"]))

    def test_the_same_file_missing_an_AUTHORED_key_still_halts(self):
        """The other direction — the exemption must not have disarmed the check."""
        import copy
        ref = {
            "build": {"default_hold": 10.0, "leads": {"C1": 5.0},
                      "standing": {"title": "TITLE", "endcard": "END",
                                   "warranty": "WARRANTY"}},
            "beats": [{"n": 1, "framing": "WIDE", "card": "C1", "broll": None}],
            "cards": [{"id": "C1", "beat": 1, "layout": "panel-push"},
                      {"id": "TITLE", "beat": 1, "layout": "fullscreen"},
                      {"id": "END", "beat": 1, "layout": "fullscreen"},
                      {"id": "WARRANTY", "beat": 1, "layout": "fullscreen"}],
        }
        broken = copy.deepcopy(ref)
        del broken["build"]["leads"]
        del broken["build"]["default_hold"]            # AUTHORED — must still fire
        res = pf.preflight(broken, [copy.deepcopy(ref), copy.deepcopy(ref)])
        self.assertTrue(
            any("default_hold" in m for m in res["must"]) or res["worth"],
            "dropping an AUTHORED key must still be reported")


if __name__ == "__main__":
    unittest.main(verbosity=2)
