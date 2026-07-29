#!/usr/bin/env python3
"""A6 — the YouTube title, proved against JODIE'S OWN STRING and the SHIPPED FILE.

The artefact is the title, not the code path that chose it. So the central proof is:
derive from EP13's real byline and assert the result equals, character for character,
the title she composed herself and published.

Every check here reads DATA — an episode.json, a copy file — or drives a real
function. Nothing greps this repo's source, so no quotation in a comment of mine can
satisfy any of it.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / ".claude/skills/pp-episode-production"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SKILL / "scripts"))
import providers                                                    # noqa: E402
import youtube_title as yt                                          # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                               # noqa: BLE001
        pass

PP = Path(r"G:\My Drive\PP Videos")
# The title Jodie composed and published herself, after the copy file failed to
# contain it. This constant is the SPEC; the code is what has to match it.
HERS = "How a Professional Assesses Race Form | How to Win at Horse Racing"
SHIPPED = PP / "PP-EP13/output/PP-EP13-youtube.txt"

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def epjson(n):
    p = PP / f"PP-EP{n}/docs/episode.json"
    if not p.is_file():
        raise AssertionError(f"EP{n} is not available to test against")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 1 ------
def _reproduces_jodies_own_title():
    epj = epjson(13)
    got = yt.derive_from(epj)
    assert got == HERS, (
        f"the derivation does not reproduce the title Jodie composed and published.\n"
        f"      byline : {epj['packaging']['byline']!r}\n"
        f"      derived: {got!r}\n"
        f"      hers   : {HERS!r}")


case("A6: EP13's byline derives to Jodie's own title, character for character",
     _reproduces_jodies_own_title)


def _the_other_two_bylines_title_case_sensibly():
    want = {
        11: "How to Look Beyond the Favourites | How to Win at Horse Racing",
        12: "How to Spot the Fresh Horse That Can Actually Win | How to Win at Horse Racing",
    }
    for n, expect in want.items():
        got = yt.derive_from(epjson(n))
        assert got == expect, f"EP{n}: {got!r}, wanted {expect!r}"
    print("      EP11 -> " + want[11])
    print("      EP12 -> " + want[12])


case("A6: EP11's and EP12's bylines title-case correctly too",
     _the_other_two_bylines_title_case_sensibly)


def _small_words_and_hyphens():
    checks = [
        ("how a professional assesses race form", "How a Professional Assesses Race Form"),
        ("the fresh horse that can actually win", "The Fresh Horse That Can Actually Win"),
        ("how to spot a first-up winner", "How to Spot a First-Up Winner"),
        ("what an edge is", "What an Edge Is"),          # `is` is small, but LAST
        ("is it worth the risk", "Is It Worth the Risk"),  # `is` first, `risk` last
        ("betting in the rain", "Betting in the Rain"),
    ]
    for src, want in checks:
        got = yt.title_case(src)
        assert got == want, f"{src!r} -> {got!r}, wanted {want!r}"


case("A6: small words stay lower case unless first or last; hyphens capitalise each part",
     _small_words_and_hyphens)


# ------------------------------------------------------------------ 2 ------
# THE SHIPPED FILE, at byte level.
def _the_shipped_file_carries_her_title_once():
    assert SHIPPED.is_file(), f"{SHIPPED} does not exist"
    text = SHIPPED.read_text(encoding="utf-8")
    first = text.split("\n")[0].rstrip()
    assert first == HERS, (
        f"line 1 of the file Jodie pastes from is not her title.\n"
        f"      line 1: {first!r}\n"
        f"      wanted: {HERS!r}")
    n = text.count(HERS)
    assert n == 1, (
        f"the title appears {n} times in the shipped file; it must appear exactly once. "
        f"A second copy is a second candidate, however it is labelled.")
    assert not yt.check_text(text, HERS), \
        f"the shipped file fails its own gate: {yt.check_text(text, HERS)}"


case("A6: the SHIPPED PP-EP13-youtube.txt carries her title on line 1, exactly once",
     _the_shipped_file_carries_her_title_once)


def _episode_json_carries_her_decision():
    """Her decision used to live only on YouTube and in a chat log."""
    stored = (epjson(13).get("packaging") or {}).get("youtube_title")
    assert stored == HERS, (
        f"episode.json still does not carry Jodie's decided title.\n"
        f"      stored: {stored!r}\n"
        f"      hers  : {HERS!r}\n"
        f"      This is the exact fault: she decided, and nothing wrote it back.")


case("A6: EP13's episode.json carries her decision, not the title she rejected",
     _episode_json_carries_her_decision)


def _ep11_and_ep12_are_left_alone():
    """They are live with the old prefix form. Nothing is served by churning them."""
    for n in (11, 12):
        t = (epjson(n).get("packaging") or {}).get("youtube_title") or ""
        assert t.startswith("How to Win at Horse Racing:"), (
            f"EP{n}'s stored youtube_title has been changed to {t!r} — it is PUBLISHED "
            f"under the old prefix form and must not be retitled.")


case("A6: EP11 and EP12 keep their published titles", _ep11_and_ep12_are_left_alone)


# ------------------------------------------------------------------ 3 ------
# The gate: every bad file must be refused.
def scratch(epj, text):
    d = Path(tempfile.mkdtemp(prefix="ytitle_"))
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "output").mkdir(parents=True, exist_ok=True)
    (d / "docs/episode.json").write_text(json.dumps(epj, ensure_ascii=False),
                                         encoding="utf-8")
    f = d / "output/PP-EP13-youtube.txt"
    f.write_text(text, encoding="utf-8")
    return d, f


def _second_candidate_halts():
    epj = epjson(13)
    bad = (f"{HERS}\n\nDESCRIPTION\nsome copy\n\n"
           f"ALTERNATIVE A — the promise stated plainly:\n"
           f"How a Ratings Man Measures a Racehorse | How to Win at Horse Racing\n")
    d, f = scratch(epj, bad)
    try:
        providers.check_youtube_title(d, f)
        raise AssertionError("a file offering a SECOND title was accepted")
    except providers.EngineFlag as e:
        assert "SECOND TITLE" in str(e) or "menu" in str(e), f"unclear halt:\n{e}"


case("A6: a copy file containing a second candidate title halts", _second_candidate_halts)


def _line_one_not_the_title_halts():
    epj = epjson(13)
    bad = f"PP-EP13 — YOUTUBE PUBLISHING COPY\n\n{HERS}\n\nDESCRIPTION\n"
    d, f = scratch(epj, bad)
    try:
        providers.check_youtube_title(d, f)
        raise AssertionError("a file whose line 1 is a preamble was accepted")
    except providers.EngineFlag as e:
        assert "line 1" in str(e), f"unclear halt:\n{e}"


case("A6: line 1 that is not the decided title halts", _line_one_not_the_title_halts)


def _wrong_house_form_halts():
    epj = epjson(13)
    bad = "How to Win at Horse Racing: How a Professional Assesses Race Form\n\ncopy\n"
    d, f = scratch(epj, bad)
    try:
        providers.check_youtube_title(d, f)
        raise AssertionError("the retired prefix form was accepted on a new episode")
    except providers.EngineFlag as e:
        assert "How to Win at Horse Racing" in str(e), f"unclear halt:\n{e}"


case("A6: line 1 not ending in the channel line halts", _wrong_house_form_halts)


def _missing_byline_halts_naming_the_field():
    """It must NEVER fall back to the episode title or to anything invented."""
    epj = epjson(13)
    epj["packaging"].pop("byline", None)
    d, f = scratch(epj, f"{HERS}\n\ncopy\n")
    msg = None
    try:
        providers.check_youtube_title(d, f)
    except providers.EngineFlag as e:
        msg = str(e)
    assert msg is not None, (
        "a missing byline did not halt — the title would have been composed from "
        "something nobody approved")
    assert "packaging.byline" in msg, f"the halt does not name the field:\n{msg}"
    # …and the episode title must not have been used as a stand-in.
    assert epj.get("title") and epj["title"] not in msg, \
        "the episode title leaked into the halt as a fallback"


case("A6: a missing packaging.byline halts, naming the field, with no fallback",
     _missing_byline_halts_naming_the_field)


def _stored_title_disagreeing_with_the_byline_halts():
    """The stored value is a RECORD of the derivation, not a second opinion."""
    epj = epjson(13)
    epj["packaging"]["youtube_title"] = "The Seven Rules a Ratings Man Lives By | " \
                                        "How to Win at Horse Racing"
    d, f = scratch(epj, f"{HERS}\n\ncopy\n")
    try:
        providers.check_youtube_title(d, f)
        raise AssertionError(
            "episode.json and the derived title were allowed to disagree — which is "
            "exactly the state EP13 sat in: the rejected title on disk, hers on YouTube")
    except providers.EngineFlag as e:
        assert "youtube_title" in str(e) and "byline" in str(e), f"unclear halt:\n{e}"


case("A6: a stored youtube_title that contradicts the byline halts",
     _stored_title_disagreeing_with_the_byline_halts)


def _a_good_file_passes():
    """The positive control — a gate that refuses everything proves nothing."""
    epj = epjson(13)
    d, f = scratch(epj, f"{HERS}\n\nDESCRIPTION\nsome perfectly ordinary copy.\n")
    out = providers.check_youtube_title(d, f)
    assert HERS in out, f"the good file was accepted but reported oddly: {out!r}"


case("A6: a correct file passes (the positive control)", _a_good_file_passes)


# ------------------------------------------------------------------ 4 ------
def _the_gate_is_on_the_real_step():
    """Drive the REAL save_youtube_copy, not a string search for a call."""
    class FakeProv(providers.RealProvider):
        def __init__(self):
            self.name = "test"

        def dir(self, ep):
            return d

    epj = epjson(13)
    bad = (f"{HERS}\n\nRECOMMENDED:\n"
           f"How a Ratings Man Measures a Racehorse | How to Win at Horse Racing\n")
    d, _f = scratch(epj, bad)
    try:
        FakeProv().save_youtube_copy({"id": "x", "ep_number": 13})
        raise AssertionError(
            "save_youtube_copy accepted a copy file with a menu in it — the gate is "
            "written but not reached")
    except providers.EngineFlag as e:
        assert "ONE decided title" in str(e), f"wrong halt:\n{str(e)[-300:]}"


case("A6: the gate is reached from the real save_youtube_copy step",
     _the_gate_is_on_the_real_step)


print(f"\nyoutube title: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
