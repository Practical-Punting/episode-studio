#!/usr/bin/env python3
"""A6 — the YouTube title. REWRITTEN 2 Aug 2026 for Jodie's superseding ruling.

    YouTube title = the episode / e-book name, then " | How to Win at Horse Racing"

The old rule derived from `packaging.byline`, title-cased. It was measured against
EP11-EP13 and reproduced their hand-set titles exactly — a correct description of what
had been done, and still the wrong thing to do. **Across EP11-EP14 the episode name and
the YouTube title had NEVER ONCE MATCHED.** One name everywhere a viewer looks.

Every check here reads DATA — an episode.json, a copy file — or drives a real function.
Nothing greps this repo's source, so no quotation in a comment of mine can satisfy it.
"""
import json
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
# Jodie's ruling, 2 Aug 2026, quoted as the SPEC. The code has to match this.
HERS = "The Meaning of Form — Part 1 | How to Win at Horse Racing"

def episode_dir(n):
    """Resolve an episode folder by NUMBER, never by exact name.

    ⚠️ The stage-8 close-out RENAMES every published episode's folder
    (PP-EP13 -> PP-EP13-The-Ratings-Game-Part-1). A test that hard-codes the bare name
    is a test with a fuse in it: it passes until the process does the thing the
    standard requires of it. Three suites broke this way at once on 3 Aug.
    """
    hits = sorted(p for p in PP.glob(f"PP-EP{n}*") if p.is_dir())
    if not hits:
        raise AssertionError(f"no PP-EP{n}* folder under {PP}")
    return hits[0]


def shipped_copy(n):
    """The published YouTube copy file, found the way the ENGINE finds it.

    🔴 THE SECOND HALF OF THE FUSE ABOVE, AND IT WENT OFF ON 6 Aug 2026.
    `episode_dir()` was fixed on 3 Aug so the FOLDER rename could not break this
    suite — and this line went on hard-coding the FILE name, which the very same
    stage-8 close-out RESTEMS: EP14's copy is now
    `PP-EP14-The-Meaning-of-Form-Part-1-youtube.txt`.
    So the fix reached the folder and not the file, and the test failed the day
    EP14 was published — doing exactly what the docstring above describes.

    `save_youtube_copy` has always globbed `*youtube*.txt`. Deriving it the same
    way means there is no name here to go stale: the rename cannot break a lookup
    that never knew the name. (CLAUDE.md fault #7 — ask the folder, don't keep a
    list.)
    """
    hits = sorted((episode_dir(n) / "output").glob("*youtube*.txt"))
    if not hits:
        raise AssertionError(f"no *youtube*.txt in PP-EP{n}'s output folder")
    return hits[0]


SHIPPED = shipped_copy(14)

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
    p = episode_dir(n) / "docs/episode.json"
    if not p.is_file():
        raise AssertionError(f"EP{n} is not available to test against")
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 1 ------
def _reproduces_jodies_ruling():
    epj = epjson(14)
    got = yt.derive_from(epj)
    assert got == HERS, (f"the derivation does not reproduce her ruling.\n"
                         f"      title  : {epj['title']!r}\n"
                         f"      derived: {got!r}\n"
                         f"      hers   : {HERS!r}")


case("A6: EP14's title derives to Jodie's ruling, character for character",
     _reproduces_jodies_ruling)


def _it_is_the_name_verbatim_not_re_cased():
    """The episode name ships on the cover and the title card already cased.

    Re-casing it here could only introduce a difference, which IS the fault.
    """
    for n in (11, 12, 13, 14):
        epj = epjson(n)
        got = yt.derive_from(epj)
        assert got.startswith(epj["title"]), (
            f"EP{n}: the derived title does not open with the episode name VERBATIM.\n"
            f"      title  : {epj['title']!r}\n"
            f"      derived: {got!r}")
        assert got == epj["title"] + " | How to Win at Horse Racing", \
            f"EP{n}: wrong house form: {got!r}"
    print("      EP14 -> " + yt.derive_from(epjson(14)))


case("A6: the title is the episode name VERBATIM plus the suffix, never re-cased",
     _it_is_the_name_verbatim_not_re_cased)


def _the_retired_byline_derivation_is_gone():
    """A superseded rule must not be reachable, or it will be reached."""
    assert not hasattr(yt, "title_case"), \
        "title_case() still exists — the byline derivation is still reachable"
    assert not hasattr(yt, "byline_of"), "byline_of() still exists"
    epj = epjson(14)
    assert yt.derive_from(epj) != (
        "Which Parts of the Form Actually Matter | How to Win at Horse Racing"), \
        "the OLD byline-derived title is still what comes out"


case("A6: the retired byline derivation is gone, not merely unused",
     _the_retired_byline_derivation_is_gone)


# ------------------------------------------------------------------ 2 ------
# THE ASSERTION THAT WAS MISSING: one name in all three places.
def _one_name_passes_on_ep14():
    problems = yt.check_one_name(epjson(14))
    names = yt.episode_names(epjson(14))
    assert not problems, f"EP14 should agree with itself now:\n{names}\n{problems}"
    for k, v in names.items():
        print(f"      {v!r}  <- {k}")


case("A6: EP14 names the same episode on the card, the e-book and YouTube",
     _one_name_passes_on_ep14)


def _one_name_CATCHES_ep13():
    """The control. EP13 is the fault Jodie described, and the check must see it."""
    problems = yt.check_one_name(epjson(13))
    assert problems, (
        "the one-name check does NOT flag EP13 — but EP13's title card and e-book say "
        "'The Ratings Game — Part 1' while its YouTube title says 'How a Professional "
        "Assesses Race Form'. If this passes, the check is worthless.")
    msg = problems[0]
    assert "The Ratings Game" in msg and "How a Professional" in msg, \
        f"the halt does not quote all three names:\n{msg}"
    print("      EP13 correctly flagged (published; NOT retitled — the kit's standing rule)")


case("A6: the one-name check CATCHES EP13, the episode that shipped wrong",
     _one_name_CATCHES_ep13)


def _one_name_catches_a_drifted_ebook_title():
    epj = epjson(14)
    epj["packaging"]["ebook_title"] = "The Meaning of Form — Part 2"
    problems = yt.check_one_name(epj)
    assert problems, "a drifted e-book title was not caught"
    assert "Part 2" in problems[0] and "Part 1" in problems[0], \
        f"the halt does not quote both:\n{problems[0]}"


case("A6: a drifted e-book title is caught", _one_name_catches_a_drifted_ebook_title)


def _one_name_catches_a_drifted_title_card():
    epj = epjson(14)
    epj["cover"]["title_payoff"] = "OF FORMLINES"
    problems = yt.check_one_name(epj)
    assert problems, "a drifted title-card name was not caught"


case("A6: a drifted title-card name is caught", _one_name_catches_a_drifted_title_card)


# ------------------------------------------------------------------ 3 ------
def _the_shipped_file_carries_her_title_once():
    assert SHIPPED.is_file(), f"{SHIPPED} does not exist"
    text = SHIPPED.read_text(encoding="utf-8")
    first = text.split("\n")[0].rstrip()
    assert first == HERS, (f"line 1 of the file Jodie pastes from is not her title.\n"
                           f"      line 1: {first!r}\n      wanted: {HERS!r}")
    n = text.count(HERS)
    assert n == 1, f"the title appears {n} times; it must appear exactly once"
    assert not yt.check_text(text, HERS), yt.check_text(text, HERS)


case("A6: the SHIPPED PP-EP14-youtube.txt carries her title on line 1, exactly once",
     _the_shipped_file_carries_her_title_once)


def _episode_json_carries_it_too():
    stored = (epjson(14).get("packaging") or {}).get("youtube_title")
    assert stored == HERS, f"episode.json still says {stored!r}"


case("A6: EP14's episode.json carries the new title", _episode_json_carries_it_too)


# ------------------------------------------------------------------ 4 ------
def scratch(epj, text):
    d = Path(tempfile.mkdtemp(prefix="ytitle_"))
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "output").mkdir(parents=True, exist_ok=True)
    (d / "docs/episode.json").write_text(json.dumps(epj, ensure_ascii=False),
                                         encoding="utf-8")
    f = d / "output/PP-EP14-youtube.txt"
    f.write_text(text, encoding="utf-8")
    return d, f


def _missing_title_halts_naming_the_field():
    epj = epjson(14)
    epj.pop("title", None)
    d, f = scratch(epj, f"{HERS}\n\ncopy\n")
    msg = None
    try:
        providers.check_youtube_title(d, f)
    except providers.EngineFlag as e:
        msg = str(e)
    assert msg is not None, "a missing episode title did not halt"
    assert "title" in msg, f"the halt does not name the field:\n{msg}"


case("A6: a missing episode.json title halts, naming the field, with no fallback",
     _missing_title_halts_naming_the_field)


def _second_candidate_halts():
    epj = epjson(14)
    bad = (f"{HERS}\n\nDESCRIPTION\ncopy\n\nALTERNATIVE A:\n"
           f"Which Parts of the Form Actually Matter | How to Win at Horse Racing\n")
    d, f = scratch(epj, bad)
    try:
        providers.check_youtube_title(d, f)
        raise AssertionError("a file offering a SECOND title was accepted")
    except providers.EngineFlag as e:
        assert "SECOND TITLE" in str(e) or "menu" in str(e), f"unclear halt:\n{e}"


case("A6: a copy file containing a second candidate title halts", _second_candidate_halts)


def _the_gate_is_reached_from_the_real_step():
    class FakeProv(providers.RealProvider):
        def __init__(self):
            self.name = "test"

        def dir(self, ep):
            return d

    epj = epjson(14)
    epj["packaging"]["ebook_title"] = "Something Else Entirely"
    d, _f = scratch(epj, f"{HERS}\n\ncopy\n")
    try:
        FakeProv().save_youtube_copy({"id": "x", "ep_number": 14})
        raise AssertionError("save_youtube_copy accepted an episode named two things")
    except providers.EngineFlag as e:
        assert "DIFFERENT THINGS" in str(e), f"wrong halt:\n{str(e)[-400:]}"


case("A6: the one-name check is reached from the real save_youtube_copy",
     _the_gate_is_reached_from_the_real_step)


def _a_good_file_passes():
    d, f = scratch(epjson(14), f"{HERS}\n\nDESCRIPTION\nordinary copy.\n")
    out = providers.check_youtube_title(d, f)
    assert HERS in out, f"the good file was accepted but reported oddly: {out!r}"


case("A6: a correct file passes (the positive control)", _a_good_file_passes)

print(f"\nyoutube title: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
