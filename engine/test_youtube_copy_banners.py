#!/usr/bin/env python3
"""The -youtube.txt reader matches BANNERS, not words — and refuses rather than guesses.

4 Sep 2026. EP45 halted at `youtube_copy`: the rail refused 99 characters. The reader,
`pasteable_description()`, took ANY line beginning with DESCRIPTION as the banner and ANY
line beginning with NOTES as the end of the description — and the writer had never been
told to emit either. So it ran past the real description into the notes, found a sentence
that began "DESCRIPTION CARRIES A CURLY APOSTROPHE…", and returned the one line under it.
EP39 had taken the same road weeks earlier and PASSED the 1000-character floor with 4,668
characters of notes that began mid-sentence. EP38 and EP40–44 found no banner at all and
got the WHOLE FILE. Six publish cards carried the notes; nothing noticed.

    THE GUARD CAUGHT EP45 BY LUCK. It tests length, and EP45's wrong answer happened to
    be short. EP39's wrong answer happened to be long.

CONTROLS FIRST (CLAUDE.md §4b): cases 1 and 2 are the two failing shapes, written to go
RED on the old reader, and they were watched going red before the reader was changed.
The fixtures ATTACK the reader (§4c) — a notes line that begins with the banner's first
word, no banners at all, a banner in the wrong place, a banner spelled with the wrong
dash, a second banner inside the notes — and the real EP38–EP45 files are read the way
the engine reads them (`*youtube*.txt` in the episode's output folder).

ONE HOME: the banners are read from docs/youtube-copy-form.json by the reader, by the mock
writer, and — through the kit — by the commissioned writer. Case 12 fails the day the kit
and the form disagree.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import providers                                                    # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                               # noqa: BLE001
        pass

PP = Path(r"G:\My Drive\PP Videos")
FORM = json.loads((REPO / "docs/youtube-copy-form.json").read_text(encoding="utf-8"))
DESC_BANNER = FORM["description_banner"]
NOTES_BANNER = FORM["notes_banner"]
RULE = FORM["rule"]
FLOOR = int(FORM["min_description_chars"])

# What the writer ACTUALLY emitted on EP38–EP45 before 4 Sep 2026: no DESCRIPTION banner
# at all, and this one fence line between the hashtags and the notes.
LEGACY_FENCE = "=== NOTES — not part of the description, do not paste ==="

TITLE = "20 Pitfalls to Avoid - Part 2 | How to Win at Horse Racing"

_PARA = ("In horse racing, around 30 per cent of favourites win in a racing season — which "
         "means 70 per cent lose. That is one of the pitfalls PB King set out for the poor "
         "old punter, and it is the shape of every trap in this episode: a habit that feels "
         "like judgement and is really a reflex. ")
DESC = (_PARA * 6).strip() + "\n\n#AustralianHorseRacing #FormAnalysis #BettingDiscipline " \
                            "#RacingTips #PracticalPunting"
assert len(DESC) > FLOOR + 200, "the fixture description must clear the floor comfortably"

# Notes whose ONE trap is a sentence that begins with the word DESCRIPTION — EP45's shape.
NOTES_WITH_TRAP = [
    'SOURCE for every phrase and every figure above: "DON’T PANIC UNDER PRESSURE (Part 2)".',
    "",
    "packaging.byline carries NO APOSTROPHE AT ALL in \"Dont\". 📌 NOTHING IN THE",
    "DESCRIPTION CARRIES A CURLY APOSTROPHE: every apostrophe above the notes line is a "
    "straight ASCII",
    "one, matching the body of the page, and the headline is not set in the description "
    "at all. ⚠️ THESE",
    "NOTES DO CARRY FOUR CURLY ONES, in the four places they reproduce the headline.",
    "",
    "HASHTAGS — slot 3 is #BettingDiscipline (8.5): the episode is about the punter's "
    "own habits.",
]
# Notes with nothing that begins with either banner word — EP38/EP40–44's shape.
NOTES_PLAIN = [
    'SOURCE for every figure and every quoted phrase above: "BASE IT ON CLASS (Part 1)".',
    "",
    "HASHTAGS — slot 3 is #HorseRacing101 (9.5): a foundations piece.",
    "",
    "PART NUMBER — Part 1, from the article's own headline.",
]


def old_shape(desc, notes, nl="\n"):
    """The file as the writer produced it for eight episodes: title, description, the
    legacy fence, notes. No DESCRIPTION banner anywhere."""
    return nl.join([TITLE, "", desc, "", "", LEGACY_FENCE, ""] + list(notes) + [""])


def new_shape(desc, notes, nl="\n", desc_banner=DESC_BANNER, notes_banner=NOTES_BANNER):
    """The house form, as docs/youtube-copy-form.json lays it out."""
    return nl.join([TITLE, "", desc_banner, RULE, "", desc, "", "", RULE, notes_banner,
                    RULE, ""] + list(notes) + [""])


def episode_dir(n):
    """PP-EP{n} or PP-EP{n}-<slug>, and NOTHING ELSE — `PP-EP4*` would match EP40–49
    (CLAUDE.md §0a)."""
    pat = re.compile(rf"^PP-EP{n:02d}(-|$)")
    hits = sorted(p for p in PP.iterdir() if p.is_dir() and pat.match(p.name))
    if len(hits) != 1:
        raise AssertionError(f"expected exactly one PP-EP{n} folder, found {hits}")
    return hits[0]


def copy_file(n):
    """Found the way save_youtube_copy finds it."""
    hits = sorted((episode_dir(n) / "output").glob("*youtube*.txt"))
    if not hits:
        raise AssertionError(f"no *youtube*.txt in PP-EP{n}'s output folder")
    return hits[0]


PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")
    except Exception as e:                                          # noqa: BLE001
        # On the OLD reader several cases die on a missing name rather than a wrong
        # answer. That is a failure too, and it must be counted, not skipped.
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"  !!  {name}\n      {type(e).__name__}: {e}")


def expect_refusal(text, why):
    """The reader must RAISE the studio's halt. Returns the flag for further checks."""
    try:
        got = providers.pasteable_description(text)
    except providers.EngineFlag as f:
        return f
    raise AssertionError(
        f"{why} — but the reader RETURNED {len(got)} characters instead of refusing.\n"
        f"      it begins: {got[:90]!r}")


# ------------------------------------------------------------ CONTROL 1 ----
def _control_notes_line_beginning_with_description_is_not_a_banner():
    """EP45 and EP39's shape. The old reader returned the one line between the notes'
    'DESCRIPTION CARRIES…' sentence and its 'NOTES DO CARRY…' sentence: 99 characters,
    mid-sentence. It must NEVER produce a fragment — refuse, or return the description."""
    text = old_shape(DESC, NOTES_WITH_TRAP)
    try:
        got = providers.pasteable_description(text)
    except providers.EngineFlag:
        return                                     # refused: honest, and the new behaviour
    assert got == DESC, (
        f"a notes sentence beginning with the word DESCRIPTION was taken as the banner: "
        f"the reader returned a {len(got)}-character FRAGMENT of the notes, mid-sentence:\n"
        f"      {got[:120]!r}")


case("CONTROL 1: a notes line that merely BEGINS with 'DESCRIPTION' must not yield a fragment",
     _control_notes_line_beginning_with_description_is_not_a_banner)


# ------------------------------------------------------------ CONTROL 2 ----
def _control_no_banners_must_not_return_the_whole_file():
    """EP38 and EP40–44's shape: no banner anywhere. The old reader's documented fallback
    returned the WHOLE FILE — title, description and thousands of words of notes — and
    the publish card showed all of it."""
    text = old_shape(DESC, NOTES_PLAIN)
    try:
        got = providers.pasteable_description(text)
    except providers.EngineFlag:
        return
    assert got == DESC, (
        f"with no banners the reader returned {len(got)} characters — the description is "
        f"{len(DESC)}. It fell back to the whole file: title on top "
        f"({got.startswith(TITLE)}), notes on the bottom ({LEGACY_FENCE in got}).")


case("CONTROL 2: a file with NO banners must not silently become the whole file",
     _control_no_banners_must_not_return_the_whole_file)


# ------------------------------------------------------------ the form -----
def _conforming_file_yields_exactly_the_description():
    got = providers.pasteable_description(new_shape(DESC, NOTES_WITH_TRAP))
    assert got == DESC, f"got {len(got)} chars, wanted {len(DESC)}; begins {got[:80]!r}"
    assert NOTES_BANNER not in got and "SOURCE for every" not in got


case("a file in the house form yields exactly the description — even with the trap in its notes",
     _conforming_file_yields_exactly_the_description)


def _crlf_reads_the_same():
    got = providers.pasteable_description(new_shape(DESC, NOTES_WITH_TRAP, nl="\r\n"))
    assert got == DESC.replace("\n", "\r\n") or got == DESC, \
        f"CRLF file parsed differently: {len(got)} chars, begins {got[:60]!r}"


case("a CRLF file (what the writer actually saves on this machine) reads the same",
     _crlf_reads_the_same)


def _dressing_is_forgiven_words_are_not():
    dressed = new_shape(DESC, NOTES_PLAIN,
                        desc_banner="=== Description - paste from here ===",
                        notes_banner="notes – FOR THE RECORD, not for pasting")
    got = providers.pasteable_description(dressed)
    assert got == DESC, "a banner fenced with === / hyphen / other case is still the banner"
    wrong_words = new_shape(DESC, NOTES_PLAIN, desc_banner="DESCRIPTION — paste from below")
    expect_refusal(wrong_words, "a banner with different WORDS is not the banner")


case("the fence, the case and the kind of dash are forgiven; the words are not",
     _dressing_is_forgiven_words_are_not)


def _banner_must_sit_at_the_top():
    text = "\n".join([TITLE, "", "A line of preamble nobody asked for.", "", DESC_BANNER,
                      RULE, "", DESC, "", RULE, NOTES_BANNER, RULE, ""] + NOTES_PLAIN)
    f = expect_refusal(text, "a description that does not begin at the top of the file")
    assert any("line 3" in b for b in f.blockers), \
        f"the run-log detail should name the stray line (line 3); got {f.blockers}"


case("a DESCRIPTION banner that is not at the top of the file is a parse failure",
     _banner_must_sit_at_the_top)


def _implausibly_short_is_a_parse_failure():
    short = "Two sentences do not make a description. #PracticalPunting"
    f = expect_refusal(new_shape(short, NOTES_PLAIN), "an implausibly short description")
    assert any(str(FLOOR) in b for b in f.blockers), \
        f"the run-log detail should name the floor ({FLOOR}); got {f.blockers}"


case("an implausibly short description is a parse failure, named as one — not a rail error later",
     _implausibly_short_is_a_parse_failure)


def _a_second_banner_is_refused_not_picked():
    notes = NOTES_PLAIN + ["", DESC_BANNER, "the notes quote the banner exactly, on a line of its own"]
    expect_refusal(new_shape(DESC, notes), "two DESCRIPTION banners")


case("a second exact banner line inside the notes is refused, not silently resolved to the first",
     _a_second_banner_is_refused_not_picked)


def _missing_notes_banner_is_refused():
    text = "\n".join([TITLE, "", DESC_BANNER, RULE, "", DESC, "", LEGACY_FENCE, ""] + NOTES_PLAIN)
    expect_refusal(text, "a DESCRIPTION banner with the legacy fence and no NOTES banner")


case("a DESCRIPTION banner closed by the legacy fence instead of the NOTES banner is refused",
     _missing_notes_banner_is_refused)


def _the_flag_is_operator_shaped_and_the_detail_is_for_the_log():
    f = expect_refusal(old_shape(DESC, NOTES_PLAIN), "no banners")
    msg = str(f)
    for bad in ("G:\\", ".txt", ".py", ".json", "Traceback"):
        assert bad not in msg, f"the operator's message carries {bad!r}: {msg}"
    assert "clear this flag" in msg.lower() or "clear the flag" in msg.lower(), msg
    assert f.blockers, "the machine-shaped detail must travel in .blockers for the run log"


case("the halt reads as plain English on the board; the line numbers travel in .blockers",
     _the_flag_is_operator_shaped_and_the_detail_is_for_the_log)


# ------------------------------------------------------------ one home -----
def _the_kit_quotes_the_form_verbatim():
    kit = (REPO / "docs/youtube-metadata-kit.md").read_text(encoding="utf-8")
    assert DESC_BANNER in kit, f"the kit does not show the writer {DESC_BANNER!r}"
    assert NOTES_BANNER in kit, f"the kit does not show the writer {NOTES_BANNER!r}"
    assert "youtube-copy-form.json" in kit, "the kit does not name the one home"


case("the kit (what the commissioned writer reads) quotes both banners exactly as the form spells them",
     _the_kit_quotes_the_form_verbatim)


def _the_rail_floor_and_the_form_floor_agree():
    sql = (REPO / "supabase/migration-005-web-addresses.sql").read_text(encoding="utf-8")
    m = re.search(r"length\(new\.youtube_copy\)\s*<\s*(\d+)", sql)
    assert m, "migration-005 no longer carries the youtube_copy length floor"
    assert int(m.group(1)) == FLOOR, f"rail floor {m.group(1)} != form floor {FLOOR}"


case("the rail's 1000-character floor and the form's min_description_chars are the same number",
     _the_rail_floor_and_the_form_floor_agree)


def _the_mock_writer_and_the_reader_agree():
    with tempfile.TemporaryDirectory() as td:
        mp = providers.MockProvider(Path(td))
        mp.step_secs = 0
        out = mp.save_youtube_copy({"id": "t", "ep_number": 9901})
        text = Path(out).read_text(encoding="utf-8")
        got = providers.pasteable_description(text)
        assert len(got) >= FLOOR, f"the mock's description is {len(got)} chars, under the floor"
        assert text.split("\n")[0].strip(), "the mock file has no title on line 1"


case("the mock provider writes a file the reader accepts (both read the same form)",
     _the_mock_writer_and_the_reader_agree)


def _the_commission_brief_points_at_the_layout():
    """Assert the ASSEMBLED brief (CLAUDE.md §1a), by catching what the writer would be
    handed — not by grepping the source that concatenates it."""
    import commission as com
    captured = {}

    def fake_commission(**kw):
        captured.update(kw)
        return {"status": "ok", "what_i_saw": "test", "unread_sources": [], "_cost_usd": 0}

    real = com.commission
    com.commission = fake_commission
    try:
        with tempfile.TemporaryDirectory() as td:
            prov = providers.RealProvider(PP)
            prov._commission_youtube_copy({"id": "t", "ep_number": 9901}, Path(td))
    finally:
        com.commission = real
    prompt = captured.get("prompt", "")
    assert "youtube-metadata-kit.md" in prompt, "the brief no longer points at the kit"
    assert "File layout" in prompt and "banner" in prompt.lower(), (
        "the brief does not tell the writer the layout is enforced:\n" + prompt[-600:])


case("the commission brief tells the writer the File layout is enforced and points at the kit",
     _the_commission_brief_points_at_the_layout)


# ------------------------------------------------------------ real data ----
def _ep45_parses_to_its_description():
    f = copy_file(45)
    got = providers.pasteable_description(f.read_text(encoding="utf-8"))
    assert got.startswith("In horse racing, around 30 per cent of favourites win"), got[:120]
    assert got.rstrip().endswith("#PracticalPunting"), got[-120:]
    assert "SOURCE for every" not in got and NOTES_BANNER not in got
    assert len(got) >= FLOOR
    print(f"      EP45: {len(got)} chars from {f.name}")


case("REAL: EP45's file (the one Jodie repaired by hand) parses to its description, top to hashtags",
     _ep45_parses_to_its_description)


def _ep38_to_ep45_all_parse_from_the_top():
    """Every file in the incident, read as the engine reads it. RED for EP38–44 until their
    banners are repaired; that red is the backfill's own control."""
    bad = []
    for n in range(38, 46):
        f = copy_file(n)
        text = f.read_text(encoding="utf-8")
        title = text.split("\n")[0].strip()
        try:
            got = providers.pasteable_description(text)
        except providers.EngineFlag as e:
            bad.append(f"EP{n}: refused — {e.blockers[:2]}")
            continue
        if title in got or "SOURCE for every" in got or LEGACY_FENCE in got:
            bad.append(f"EP{n}: {len(got)} chars, and it still carries the title or the notes")
            continue
        print(f"      EP{n}: {len(got):>5} chars, opens {got[:58]!r}")
    assert not bad, "\n      ".join(bad)


case("REAL: EP38–EP45 every file parses to a description that starts at the top and stops at the notes",
     _ep38_to_ep45_all_parse_from_the_top)


def _title_gate_still_passes_on_every_file():
    """Adding banners must not disturb the ONE-TITLE gate — the real check, the real
    arguments (docs/episode.json + the copy file), as save_youtube_copy calls it."""
    script = REPO / ".claude/skills/pp-episode-production/scripts/youtube_title.py"
    bad = []
    for n in range(38, 46):
        d = episode_dir(n)
        r = subprocess.run([sys.executable, str(script), "--check", str(d / "docs/episode.json"),
                            str(copy_file(n))], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        if r.returncode:
            bad.append(f"EP{n}: {(r.stderr or r.stdout).strip()[-300:]}")
    assert not bad, "\n      ".join(bad)


case("REAL: the title gate (youtube_title.py --check) still passes on every one of EP38–EP45",
     _title_gate_still_passes_on_every_file)


print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
