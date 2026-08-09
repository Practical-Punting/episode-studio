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


class CardShapeIsNotAConvention(unittest.TestCase):
    """A card's shape is chosen from the ARTICLE, never inherited from another episode.

    🔴 EP19, 9 Aug 2026. Both reference episodes happened to use a `bars` card, so
    `cards[].content.bars[]` became a convention and an episode whose article has no
    comparison to draw was handed a BLOCKER whose only remedy is TO INVENT A BAR CHART.
    Jodie's ruling: there is never a requirement for a bar chart.

    Every case here is built in memory from a minimal episode, so it states the fault
    exactly rather than depending on which blocks EP13/EP14 happen to use this month —
    a fixture that drifts would quietly stop testing this.
    """

    @staticmethod
    def card(cid, block, content, **extra):
        c = {"id": cid, "beat": 1, "page": f"{cid}.html", "layout": "fullscreen",
             "block": block, "job": "anchor", "eyebrow": "x", "headline": "X",
             "headline_display": "X", "content": content, "trace": {}}
        c.update(extra)
        return c

    @staticmethod
    def episode(cards):
        return {"episode": "PP-EP99", "source": "x",
                "beats": [{"n": 1, "framing": "WIDE", "card": "C1"}],
                "packaging": {"hook": "h"}, "build": {}, "ebook": {}, "thumbnail": {},
                "cover": {}, "cards": cards, "broll": [], "figures": []}

    def refs_using(self, block, content, **extra):
        return [self.episode([self.card("C1", block, content, **extra)]),
                self.episode([self.card("C2", block, copy.deepcopy(content), **extra)])]

    def test_a_bar_chart_in_both_references_is_not_required_here(self):
        refs = self.refs_using("bars", {"bars": [{"label": "90 Days", "value": "90",
                                                  "note": "n", "tone": "hi"}],
                                        "ask": "a", "chip": None})
        mine = self.episode([self.card("C1", "statement", {"line": "A plain claim."})])
        must = pf.preflight(mine, refs)["must"]
        self.assertFalse([m for m in must if "bars" in m],
                         f"a bar chart is being demanded because other episodes had "
                         f"one; the only way to clear it is to invent one: {must}")

    def test_a_position_rail_in_both_references_is_not_required_here(self):
        """The sibling, found by asking rather than by waiting for it to bite."""
        rail = {"n": 1, "of": 7, "segs": ["a", "b"]}
        refs = self.refs_using("statement", {"line": "x"}, rail=rail)
        mine = self.episode([self.card("C1", "statement", {"line": "z"})])
        must = pf.preflight(mine, refs)["must"]
        self.assertFalse([m for m in must if "rail" in m],
                         f"an episode with no numbered spine is blocked for having no "
                         f"position rail: {must}")

    # ---- and the half that must NOT be lost ----------------------------------
    def test_a_genuinely_missing_top_level_block_still_blocks(self):
        """CONTROL FOR THE FIX ITSELF. If this ever passes with the thumbnail gone,
        the exclusion has been widened past card payloads and E26 is switched off."""
        refs = self.refs_using("statement", {"line": "x"})
        mine = self.episode([self.card("C1", "statement", {"line": "z"})])
        del mine["thumbnail"]
        for r in refs:
            r["thumbnail"] = {"l1": "a", "l2": "b", "part": "P", "hero_focus": "center"}
        must = pf.preflight(mine, refs)["must"]
        self.assertTrue([m for m in must if "thumbnail" in m],
                        f"a whole missing top-level block is no longer a blocker — the "
                        f"card-payload exclusion has been widened too far: {must}")

    def test_two_cards_on_one_block_disagreeing_about_a_type_still_blocks(self):
        """Only 'you do not have what they had' is relaxed. A type clash is still a
        clash: that is two cards using the SAME block and disagreeing about it."""
        refs = self.refs_using("bars", {"bars": [{"label": "L", "value": "90",
                                                  "note": "n", "tone": "hi"}],
                                        "ask": "a", "chip": None})
        mine = self.episode([self.card("C1", "bars",
                                       {"bars": [{"label": "L", "value": 90,
                                                  "note": "n", "tone": "hi"}],
                                        "ask": "a", "chip": None})])
        must = pf.preflight(mine, refs)["must"]
        self.assertTrue([m for m in must if "value" in m],
                        f"a bar value that is an int where both references have a "
                        f"string is no longer reported: {must}")


if __name__ == "__main__":
    if not HAVE_DRIVE:
        print(f"NOTE: {SKIP}")
    unittest.main(verbosity=2)
