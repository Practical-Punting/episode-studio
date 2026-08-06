#!/usr/bin/env python3
"""THE SCRIPT'S HOME MOVES TO THE RAIL (ruling A5) — proved, not asserted.

The four constraints Jodie set when she approved this, one section each:

  1. THE GATE DOES NOT WEAKEN — it still refuses both halves, with the script on
     the rail rather than in a Doc. The gate's meaning must survive its plumbing
     changing.
  2. AN EPISODE WITH A DOC STILL READS THE DOC — EP01..EP16 behave identically.
     Proved by making the Doc branch observable and checking it is the one taken.
  3. THE INPUT FIELDS ARE NOT TOUCHED — the board shows the script in a <pre>,
     which is not an input, so the refresh pause and the draft harvest cannot see
     it. Proved by reading app.js, because that is where the claim lives.
  4. spoken-words.txt IS STILL WRITTEN — it is the derived cache render_ready
     reads at audit_inputs, and it was the one thing hiding inside fetch_script.

Nothing here touches the network, the live rail, or a running engine.
"""
from __future__ import annotations
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import providers                                                   # noqa: E402
from providers import EngineFlag, RealProvider, sha256_text        # noqa: E402
import engine                                                      # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                              # noqa: BLE001
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
    except Exception as e:                                         # noqa: BLE001
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"  !!  {name}\n      {type(e).__name__}: {e}")


SCRIPT = ("Everyone has a lucky number. " * 30).strip()            # ~150 words
assert len(SCRIPT.split()) >= 50


class Prov(RealProvider):
    """A RealProvider whose disk is a temp dir and whose Doc read is observable.

    Subclassed rather than mocked so the REAL fetch_script branch logic runs —
    the thing under test is which branch it takes, and a mock of fetch_script
    would test nothing at all.
    """
    def __init__(self, root):
        self.root = Path(root)
        self.pp = Path(root)
        self.doc_reads = []

    def dir(self, ep):
        d = self.root / f"PP-EP{ep.get('ep_number', 99)}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _doc_read(self, doc_id):                                   # seam for the test
        self.doc_reads.append(doc_id)
        return SCRIPT + " From the Doc."


def _patch_doc_branch(p):
    """Redirect ONLY the network read, leaving every branch and guard real."""
    import urllib.request

    class FakeResp:
        def __init__(self, body):
            self._b = body.encode("utf-8")
            self.headers = {"Content-Type": "text/plain; charset=utf-8"}

        def read(self):
            return self._b

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        m = re.search(r"/document/d/([^/]+)/", url)
        return FakeResp(p._doc_read(m.group(1) if m else "?"))

    return urllib.request, fake_urlopen


def scratch():
    return Path(tempfile.mkdtemp(prefix="scriptrail_"))


# ---------------------------------------------------------------- constraint 1
def test_gate_refuses_no_title_with_rail_script():
    ep = {"script_snapshot": SCRIPT, "script_read": True, "title_approved": False}
    try:
        engine.assert_script_gate(ep)
    except EngineFlag as e:
        assert "aren't approved" in str(e), f"wrong message: {e}"
        return
    raise AssertionError("the gate PASSED with the words unapproved — it must refuse")


def test_gate_refuses_no_script_read_with_rail_script():
    ep = {"script_snapshot": SCRIPT, "script_read": False, "title_approved": True}
    try:
        engine.assert_script_gate(ep)
    except EngineFlag as e:
        assert "read the script" in str(e), f"wrong message: {e}"
        return
    raise AssertionError("the gate PASSED without 'I've read the script' — it must refuse")


def test_gate_passes_only_when_both_halves_set():
    ep = {"script_snapshot": SCRIPT, "script_read": True, "title_approved": True}
    assert engine.assert_script_gate(ep) is True, "both halves set and the gate still refused"


def test_gate_does_not_look_at_the_script_at_all():
    """The gate is about DECISIONS, not transport. It must not have acquired an
    opinion about where the script lives while we were moving it."""
    src = Path(engine.__file__).read_text(encoding="utf-8")
    body = src.split("def assert_script_gate(ep):")[1].split("\ndef ")[0]
    for forbidden in ("script_doc_url", "script_snapshot", "fetch_script"):
        assert forbidden not in body, (
            f"assert_script_gate now mentions {forbidden!r} — the gate must stay a "
            "check on two human decisions, whatever the script's home is")


# ---------------------------------------------------------------- constraint 2
def test_an_episode_with_a_doc_still_reads_the_doc():
    p = Prov(scratch())
    mod, fake = _patch_doc_branch(p)
    real, mod.urlopen = mod.urlopen, fake
    try:
        ep = {"ep_number": 15,
              "script_doc_url": "https://docs.google.com/document/d/" + "A" * 25 + "/edit",
              "script_snapshot": "THE RAIL COPY THAT MUST NOT BE USED " * 20}
        text, sha, source = p.fetch_script(ep)
    finally:
        mod.urlopen = real
    assert p.doc_reads == ["A" * 25], f"the Doc was not read: {p.doc_reads}"
    assert "From the Doc." in text, "returned the RAIL copy for an episode that has a Doc"
    assert "MUST NOT BE USED" not in text, "the rail snapshot leaked into a Doc episode"
    assert "script Doc" in source, f"source should name the Doc, got {source!r}"
    assert sha == sha256_text(text), "sha does not match the text returned"


def test_a_doc_episode_with_no_snapshot_is_unchanged():
    """The EP01..EP16 shape exactly: a Doc, and script_snapshot not yet written."""
    p = Prov(scratch())
    mod, fake = _patch_doc_branch(p)
    real, mod.urlopen = mod.urlopen, fake
    try:
        ep = {"ep_number": 12,
              "script_doc_url": "https://docs.google.com/document/d/" + "B" * 25 + "/edit"}
        text, _sha, source = p.fetch_script(ep)
    finally:
        mod.urlopen = real
    assert p.doc_reads == ["B" * 25], "a Doc episode with no snapshot did not read its Doc"
    assert "From the Doc." in text and "script Doc" in source


def test_a_blank_doc_url_is_not_a_doc():
    """An empty string is what a board write can leave behind. It must read as
    'no Doc' and not as a Doc whose id is missing — the difference between the
    rail path and a flag."""
    p = Prov(scratch())
    ep = {"ep_number": 17, "script_doc_url": "   ", "script_snapshot": SCRIPT}
    text, _sha, source = p.fetch_script(ep)
    assert "board" in source, f"a whitespace Doc URL did not fall through to the rail: {source!r}"
    assert text.startswith("Everyone has a lucky number")


# ---------------------------------------------------------------- constraint 4
def test_rail_script_writes_spoken_words():
    """THE ONE THING HIDING INSIDE fetch_script. render_ready reads this file at
    audit_inputs, so if the move forgets it the build stops one step later."""
    p = Prov(scratch())
    ep = {"ep_number": 17, "script_snapshot": SCRIPT}
    text, sha, source = p.fetch_script(ep)
    out = p.dir(ep) / "docs/spoken-words.txt"
    assert out.is_file(), "spoken-words.txt was NOT written from the rail"
    on_disk = out.read_text(encoding="utf-8")
    assert on_disk.strip() == text.strip(), "the file on disk is not the text returned"
    assert sha == sha256_text(text), "sha does not match"
    assert "board" in source, f"source should name the script box, got {source!r}"


def test_rail_script_write_false_writes_nothing():
    """_script_drift_check calls fetch_script(write=False) at the render gate."""
    p = Prov(scratch())
    ep = {"ep_number": 17, "script_snapshot": SCRIPT}
    p.fetch_script(ep, write=False)
    assert not (p.dir(ep) / "docs/spoken-words.txt").exists(), \
        "write=False still wrote spoken-words.txt"


def test_no_doc_and_no_script_flags_in_plain_english():
    p = Prov(scratch())
    try:
        p.fetch_script({"ep_number": 17})
    except EngineFlag as e:
        m = str(e)
        assert "no script" in m.lower(), f"message does not say what is missing: {m}"
        for jargon in ("script_snapshot", "None", "Traceback", "rail"):
            assert jargon not in m, f"engine vocabulary in an operator message: {jargon!r}"
        return
    raise AssertionError("no Doc and no script did not flag")


def test_a_short_rail_script_flags():
    p = Prov(scratch())
    try:
        p.fetch_script({"ep_number": 17, "script_snapshot": "Too short."})
    except EngineFlag as e:
        assert "words" in str(e), f"wrong message: {e}"
        return
    raise AssertionError("a two-word script was accepted as an episode")


def test_backslash_escaped_rail_script_flags():
    """A human pastes from a markdown tool. Same symptom as the Doc path's, and
    DELIBERATELY a different message, because it is a different cause."""
    p = Prov(scratch())
    bad = SCRIPT + r" Squeeze Those Odds\! And \#one."
    try:
        p.fetch_script({"ep_number": 17, "script_snapshot": bad})
    except EngineFlag as e:
        m = str(e)
        assert "backslash" in m.lower(), f"wrong message: {m}"
        assert "fault in me" not in m, (
            "the rail path is using the DOC path's diagnosis — on the rail the cause "
            "is a paste, not the engine reading through the wrong channel (CLAUDE.md #6)")
        return
    raise AssertionError("backslash-escaped punctuation was accepted")


def test_a_notes_header_on_a_rail_script_is_refused():
    """THE PANEL'S HEADING IS A CLAIM: "this is exactly what Gordon says". So the
    script box may hold nothing Gordon does not say.

    EP17 shipped to Jodie's screen with its Doc-era header on display — heading
    false, content telling her to edit a Doc that A5 had just deleted, and a word
    count of 1,954 against 1,495 actually spoken. Refused at the write end now."""
    p = Prov(scratch())
    withhdr = ('# PP-EP18 — "Something"\n'
               "# THIS DOC IS THE SCRIPT'S ONE HOME. Edit it here.\n"
               "# PASTE EVERYTHING BELOW THIS LINE INTO HEYGEN\n\n\n" + SCRIPT)
    try:
        p.fetch_script({"ep_number": 18, "script_snapshot": withhdr})
    except EngineFlag as e:
        m = str(e)
        assert "production notes" in m.lower(), f"wrong message: {m}"
        assert "run log" in m.lower(), "the message does not say where the notes should go"
        return
    raise AssertionError("a script with a notes header was accepted onto the rail")


def test_the_header_rule_is_derived_not_restated():
    """It must call render_ready's OWN strip_notes_header. A regex here would be a
    second definition of 'a notes header' drifting away from the three tools that
    already have one."""
    src = Path(providers.__file__).read_text(encoding="utf-8")
    body = src.split("def _script_checks")[1].split("\n    def ")[0]
    assert "strip_notes_header" in body, \
        "_script_checks no longer calls render_ready's strip_notes_header — if the rule " \
        "has been restated as a regex, it is now a second definition that can drift"


def test_a_clean_script_is_not_mistaken_for_a_header():
    """The does-not-cry-wolf case. A script that merely CONTAINS a hash somewhere,
    or starts with an ordinary sentence, must sail through."""
    p = Prov(scratch())
    for text in (SCRIPT, SCRIPT + " Number one, hash it out.", "Right.\n\n" + SCRIPT):
        t, _s, _src = p.fetch_script({"ep_number": 17, "script_snapshot": text}, write=False)
        assert t.strip(), "a clean script was rejected"


def test_crlf_is_normalised_on_the_rail_path():
    p = Prov(scratch())
    ep = {"ep_number": 17, "script_snapshot": SCRIPT.replace(". ", ".\r\n") + "\r\n"}
    text, _s, _src = p.fetch_script(ep)
    assert "\r" not in text, "CR survived into the approved snapshot"


# ---------------------------------------------------------------- constraint 3
APP = (HERE.parent / "app.js").read_text(encoding="utf-8")


def _gate_words():
    return APP.split("function gateWords(ep)")[1].split("\nfunction ")[0]


def test_the_script_view_is_not_an_input():
    """THE SAFETY ARGUMENT FOR LANDING THIS BESIDE AN UNPROVEN slice 1: a <pre>
    is not an input, so harvestDrafts/restoreDrafts and the refresh pause cannot
    see it and the fields' caret/undo behaviour is untouched.

    Asserted against the CODE because that is where the claim lives — if someone
    later 'improves' this into a textarea, that is the moment the pause has to be
    re-reasoned, and this test is what tells them."""
    g = _gate_words()
    assert "scriptbox" in g, "the script view is missing from the words card"
    box = g.split("scriptbox")[1][:400]
    assert "<pre>" in box, "the script view is no longer a <pre>"
    assert "<textarea" not in g, (
        "a TEXTAREA has appeared in the words card. That is slice 4, and it changes "
        "the refresh-pause reasoning: an input IS harvested and restored, so caret "
        "and undo come back into play. Do not land it without redoing that argument.")


def test_the_tick_is_enabled_only_when_there_is_something_to_read():
    g = _gate_words()
    assert "const readable = !!doc || !!script;" in g, \
        "the tick's enable condition is not derived from 'is there something to read'"
    assert "(readable ? \"\" : \" disabled\")" in g, \
        "the tick is no longer disabled when there is nothing to read"


def test_approve_refuses_when_there_is_no_script_at_all():
    """The old guard demanded a DOC. The new one demands a SCRIPT. It must not
    have quietly become no guard."""
    h = APP.split('if (act === "approve-words")')[1].split("\n  if (act ===")[0]
    assert 'ep.script_snapshot' in h, "approve-words no longer looks for a script"
    assert "no script for this episode yet" in h, "the refusal message is gone"
    assert "Link the script Doc first" not in h, \
        "approve-words still demands a Doc — the point of the change was to stop"


def test_the_words_gate_breaks_out_of_its_lane_when_there_is_a_script():
    """A 1,500-word script was being read through a 360px lane slot at 15px. This
    is the one human decision the studio can never automate; it may not look like
    a tooltip. The card spans the page when — and only when — she is reading."""
    body = APP.split("function cardFor(ep)")[1].split("\nfunction ")[0]
    assert "readingScript" in body, "the words-gate card no longer breaks out"
    assert 'wordsGatePending(ep) && !!(ep.script_snapshot' in body, \
        "the breakout is not conditional on there being a script to read"
    assert '" wide"' in body, "the wide class is not applied"
    css = (HERE.parent / "styles.css").read_text(encoding="utf-8")
    assert ".card.wide{grid-column:1/-1" in css, "the wide card does not span the lane"
    assert "max-width:66ch" in css, \
        "the reading column is not capped — full width must not mean full-width TEXT"
    m = re.search(r"\.card\.wide \.scriptbox pre\{font-size:(\d+)px", css)
    assert m and int(m.group(1)) >= 20, \
        f"the script type is {m.group(1) if m else '?'}px — it was 15px and that was the fault"


def test_a_rail_episode_never_writes_an_empty_doc_url():
    """An empty string is not NULL, and fetch_script branches on that value."""
    h = APP.split('if (act === "approve-words")')[1].split("\n  if (act ===")[0]
    assert 'if ($("w-doc-" + id)) patch.script_doc_url = doc;' in h, \
        "approve-words may write script_doc_url unconditionally, which would put '' " \
        "on a rail episode and send fetch_script down the Doc branch forever"


if __name__ == "__main__":
    print("THE SCRIPT MOVES TO THE RAIL — the four constraints\n")
    print("1. the gate does not weaken")
    for f in (test_gate_refuses_no_title_with_rail_script,
              test_gate_refuses_no_script_read_with_rail_script,
              test_gate_passes_only_when_both_halves_set,
              test_gate_does_not_look_at_the_script_at_all):
        case(f.__name__, f)
    print("\n2. an episode with a Doc still reads the Doc")
    for f in (test_an_episode_with_a_doc_still_reads_the_doc,
              test_a_doc_episode_with_no_snapshot_is_unchanged,
              test_a_blank_doc_url_is_not_a_doc):
        case(f.__name__, f)
    print("\n3. the input fields are not touched, and it is a reading surface")
    for f in (test_the_script_view_is_not_an_input,
              test_the_tick_is_enabled_only_when_there_is_something_to_read,
              test_approve_refuses_when_there_is_no_script_at_all,
              test_the_words_gate_breaks_out_of_its_lane_when_there_is_a_script,
              test_a_rail_episode_never_writes_an_empty_doc_url):
        case(f.__name__, f)
    print("\n4. spoken-words.txt is still written, and the guards still hold")
    for f in (test_rail_script_writes_spoken_words,
              test_rail_script_write_false_writes_nothing,
              test_no_doc_and_no_script_flags_in_plain_english,
              test_a_short_rail_script_flags,
              test_backslash_escaped_rail_script_flags,
              test_a_notes_header_on_a_rail_script_is_refused,
              test_the_header_rule_is_derived_not_restated,
              test_a_clean_script_is_not_mistaken_for_a_header,
              test_crlf_is_normalised_on_the_rail_path):
        case(f.__name__, f)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for n, e in FAIL:
            print(f"  FAIL {n}: {e}")
        sys.exit(1)
