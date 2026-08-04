"""Proof for E26 — measured against EP15's ACTUAL SEVEN HALTS, one test each.

"All green" means nothing unless the suite covers what you changed. A pass count proves
nothing here; what proves it is **naming the seven faults that cost a real episode a real
day and showing which of them this tool would have surfaced before the build started.**

So each of the seven gets its own test, named after the halt. They are reconstructed by
MUTATING A REAL episode.json rather than hand-writing a fixture, because a fixture is
something I invented and EP15 is something that happened.

  1 build.default_hold missing   -> surfaced (worth knowing; the real fix is E24's code default)
  2 build.midroll.ask is a STR   -> BLOCKS
  3 no card beat framed WIDE     -> BLOCKS  (shape pass)
  4 build.standing.endcard='ENDCARD' -> BLOCKS  (referential pass)
  5 build.standing block absent  -> BLOCKS
  6 build.midroll.dur missing    -> surfaced (worth knowing)
  7 thumbnail block absent       -> BLOCKS

FIVE BLOCK, TWO ARE SURFACED WITHOUT BLOCKING — and that split is deliberate, not a
shortfall. A missing tuning value whose code default may already be correct must NOT
halt a build: twelve of those were correctly left alone on EP15, and *a value you do not
understand is not made safer by copying it.* What matters is that all seven are VISIBLE
before a credit is spent instead of eighteen steps in.

Hermetic: reads the real episode.json files but writes nothing, and every mutation is on
an in-memory copy.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight_episode_json as pf


def load(n):
    return json.loads((pf.ep_dir(n) / "docs/episode.json").read_text(encoding="utf-8"))


try:
    EP13, EP14, EP15 = load(13), load(14), load(15)
    REFS = [EP13, EP14]
    HAVE_DRIVE = True
except Exception as exc:                                              # noqa: BLE001
    HAVE_DRIVE = False
    SKIP = f"episode files unavailable ({type(exc).__name__}: {exc})"


@unittest.skipUnless(HAVE_DRIVE, "needs the episode folders")
class TheSevenHalts(unittest.TestCase):
    """One test per halt EP15 actually took."""

    def must(self, j):
        return " ".join(pf.preflight(j, REFS)["must"])

    def worth(self, j):
        return " ".join(pf.preflight(j, REFS)["worth"])

    # -- the five that must BLOCK ------------------------------------------
    def test_2_ask_as_a_string_blocks(self):
        """`ask` was a STRING, so ask[0] was the letter 'I'. The old guard was
        `len(ask) < 2`, which any two-character string passes."""
        j = copy.deepcopy(EP15)
        j["build"]["midroll"]["ask"] = "If you've found something worth having"
        self.assertIn("build.midroll.ask", self.must(j))

    def test_3_no_card_beat_on_wide_blocks(self):
        j = copy.deepcopy(EP15)
        for b in j["beats"]:
            if b.get("card"):
                b["framing"] = "MCU"
        m = self.must(j)
        self.assertIn("WIDE", m)
        self.assertIn("panel-push", m)

    def test_4_endcard_id_pointing_at_nothing_blocks(self):
        """THE referential one. Key present, type right, name points at no card."""
        j = copy.deepcopy(EP15)
        j["build"]["standing"]["endcard"] = "ENDCARD"
        m = self.must(j)
        self.assertIn("ENDCARD", m)
        self.assertIn("no card with that id", m)

    def test_5_missing_standing_block_blocks(self):
        """The one that exposed the shallow-subtree bug: root `build` is PRESENT."""
        j = copy.deepcopy(EP15)
        del j["build"]["standing"]
        m = self.must(j)
        self.assertIn("build.standing", m)
        self.assertIn("block is absent", m)

    def test_7_missing_thumbnail_block_blocks(self):
        j = copy.deepcopy(EP15)
        del j["thumbnail"]
        m = self.must(j)
        self.assertIn("thumbnail", m)
        self.assertIn("block is absent", m)

    # -- the two that are surfaced but must NOT block ----------------------
    def test_1_default_hold_is_surfaced_not_blocked(self):
        j = copy.deepcopy(EP15)
        del j["build"]["default_hold"]
        res = pf.preflight(j, REFS)
        self.assertIn("build.default_hold", " ".join(res["worth"]))
        self.assertNotIn("build.default_hold", " ".join(res["must"]))

    def test_6_midroll_dur_is_surfaced_not_blocked(self):
        j = copy.deepcopy(EP15)
        del j["build"]["midroll"]["dur"]
        res = pf.preflight(j, REFS)
        self.assertIn("build.midroll.dur", " ".join(res["worth"]))
        self.assertNotIn("build.midroll.dur", " ".join(res["must"]))


@unittest.skipUnless(HAVE_DRIVE, "needs the episode folders")
class DoesNotCryWolf(unittest.TestCase):
    """A guard everyone ignores is worse than no guard."""

    def test_the_real_ep15_passes_clean(self):
        """EP15 AS SHIPPED — approved, published — must not raise a single blocker."""
        res = pf.preflight(EP15, REFS)
        self.assertEqual(res["must"], [], f"EP15 as shipped should be clean: {res['must']}")

    def test_ep14_against_ep13_and_ep15_passes_clean(self):
        """And a reference episode judged by the others. If the tool cannot agree that
        a SHIPPED episode is fine, its threshold is wrong."""
        res = pf.preflight(EP14, [EP13, EP15])
        self.assertEqual(res["must"], [], f"EP14 should be clean: {res['must']}")

    def test_comment_fields_are_never_conventions(self):
        """`_note` keys differ freely between episodes and mean nothing to the build.
        Five of the naive diff's seventeen findings were these."""
        conv = pf.conventions(EP13, EP14)
        self.assertFalse([k for k in conv if k.split(".")[-1].startswith("_")])
        self.assertFalse([k for k in conv if k.startswith("_")])

    def test_a_key_only_one_reference_has_is_not_a_convention(self):
        """TWO references, never one — a rule inferred from a single sample was wrong
        on all three axes when it was tried on panel-push cell counts."""
        a, b = pf.key_types(EP13), pf.key_types(EP14)
        only_a = set(a) - set(b)
        self.assertTrue(only_a, "expected EP13 to have at least one unique key")
        conv = pf.conventions(EP13, EP14)
        self.assertFalse(only_a & set(conv))


@unittest.skipUnless(HAVE_DRIVE, "needs the episode folders")
class EpisodeLookup(unittest.TestCase):
    """E18 — `PP-EP1*` matches PP-EP10, and published episodes get RENAMED."""

    def test_resolves_a_renamed_published_episode(self):
        self.assertTrue(pf.ep_dir(13).name.startswith("PP-EP13"))

    def test_single_digit_does_not_match_a_two_digit_folder(self):
        d = pf.ep_dir(5)
        self.assertRegex(d.name, r"^PP-EP05($|[-_])")

    def test_nine_does_not_match_ninety_eight(self):
        self.assertRegex(pf.ep_dir(9).name, r"^PP-EP09($|[-_])")


class Prefixes(unittest.TestCase):
    def test_absence_starting_at_a_leaf_is_a_leaf(self):
        blocks, lone = pf._subtree_missing({"build.mcu_zoom"}, {"build.default_hold"})
        self.assertEqual(blocks, {})
        self.assertEqual(lone, ["build.mcu_zoom"])

    def test_absence_starting_mid_path_is_a_block(self):
        blocks, lone = pf._subtree_missing(
            {"build.standing.title", "build.standing.endcard"}, {"build.default_hold"})
        self.assertEqual(lone, [])
        self.assertIn("build.standing", blocks)


if __name__ == "__main__":
    if not HAVE_DRIVE:
        print(f"NOTE: {SKIP}")
    unittest.main(verbosity=2)
