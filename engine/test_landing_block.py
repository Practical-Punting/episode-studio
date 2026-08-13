"""Proof for the pre-EP16 landing block. ONE NAMED CASE PER THING CHANGED.

"All green" means nothing unless the suite covers what you changed. `test_bundle_a.py`
was 9/9 while `step_audit_inputs` held a guaranteed NameError, because its nine cases
were about the midroll chip, the credit ceiling, the copy button and the title preview —
it never mentioned the function that was broken. So this file is organised by FAULT, and
each test is named after the thing that actually went wrong.

  E22   a dropped download is promoted to THE MASTER
  E22b  the same fault on the PAID Higgsfield clips and heroes
  E11   the stale-code guard cannot fire in the one state where it is needed
  E16   a rejected hero comes back because the ledger is keyed on the slot
  ESC   a script read through the wrong channel gains backslashes
  IMG   a page renders alt text because its image is missing
"""
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import providers
from providers import EngineFlag, RealProvider


class _Resp(io.BytesIO):
    """A urlopen() result that STATES one size and DELIVERS another."""

    def __init__(self, body: bytes, stated=None, ctype="video/mp4"):
        super().__init__(body)
        h = {"Content-Type": ctype}
        if stated is not None:
            h["Content-Length"] = str(stated)
        self.headers = h
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# ---------------------------------------------------------------- E22
class TruncatedDownload(unittest.TestCase):
    """EP15: HeyGen stated 114,395,315 bytes; 78,947,138 landed. Gordon stopped
    mid-word at 9:10 of a '13:31' file and EVERY OTHER CHECK PASSED, because an mp4
    with `faststart` carries `moov` at the front and announces the full duration.

    🔴 EVERY CASE HERE SERVES A FRESH RESPONSE PER ATTEMPT — see `serving()` below,
    and do not go back to `return_value=`.
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.dest = self.d / "presenter-master.mp4"
        # E-c added THREE attempts to _download_exact. Real waits of 5s then 10s in a
        # unit test are 15 seconds of nothing per case, and this class has six.
        s = mock.patch.object(providers.time, "sleep", lambda *_: None)
        s.start()
        self.addCleanup(s.stop)

    @staticmethod
    def serving(*args, **kw):
        """A server that answers the SAME WAY EVERY TIME IT IS ASKED.

        🔴 THIS USED TO BE `return_value=_Resp(...)`, WHICH IS ONE OBJECT.
        `_download_exact` consumes the response inside a `with`, so attempt 1 closed it
        and attempts 2 and 3 got `ValueError: I/O operation on closed file` off the same
        exhausted BytesIO. The function then reported the LAST reason it failed, so the
        flag under test read "the connection failed" instead of "the download stopped
        early", and the cases asserting the stated size and the word "Retrying" failed
        — on correct engine code, against a fault invented entirely by the mock.
            The test predated the retry loop (E-c) and nobody re-read it when the loop
        landed. A stub that can only be used once does not stand in for a server.
        A real truncating server re-serves its truncated body on every attempt, so this
        builds a NEW response per call and the three attempts fail for the real reason.
        """
        return _Resp(*args, **kw)

    def test_a_short_download_is_refused_and_not_promoted(self):
        """EP15's real numbers as the STATED size — the body is kept small on purpose
        so the suite stays fast; what is under test is the comparison and the refusal,
        not ffmpeg's ability to write 79 MB."""
        with mock.patch.object(providers.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: self.serving(b"x" * 4096, 114_395_315)):
            with self.assertRaises(EngineFlag) as cm:
                RealProvider._download_exact("http://x.test/v.mp4", self.dest)
        msg = str(cm.exception)
        self.assertIn("114,395,315", msg, "the flag must name the size the server stated")
        self.assertIn("4,096", msg, "and the size that actually arrived")
        self.assertFalse(self.dest.exists(), "a short file must NEVER become the master")
        self.assertFalse(self.dest.with_suffix(".part").exists(), "no .part left behind")

    def test_the_message_says_whether_a_retry_is_hers_to_make(self):
        """A halt must say plainly whether retrying helps. This one does — and what
        that means changed when the MACHINE started doing the retrying.

        🔴 THE OLD ASSERTION WAS `assertIn("Retrying", msg)` AND IT WENT STALE THE DAY
        E-c LANDED. Back then the flag said retrying usually works and then asked a
        human to press the button that does it — a chore dressed as a decision. E-c
        made the engine take three verified attempts itself, so the message correctly
        stopped saying "Retrying": by the time she reads it, retrying is the thing that
        has ALREADY BEEN TRIED, three times.
            Demanding the word back would be demanding the chore back. The requirement
        underneath it never changed and is what is asserted now: SHE MUST NOT BE LEFT
        GUESSING WHETHER THE BUTTON IS HERS TO PRESS. So the message has to say the
        machine already tried, how many times, and where to look once that is ruled out.
        """
        with mock.patch.object(providers.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: self.serving(b"x" * 10, 100)):
            with self.assertRaises(EngineFlag) as cm:
                RealProvider._download_exact("http://x.test/v.mp4", self.dest)
        msg = str(cm.exception)
        self.assertRegex(msg, r"tried \d+ times",
                         "she must be told the machine already retried, or she will "
                         "press the button that does what has just been done 3 times")
        self.assertIn("connection", msg,
                      "and where the fault actually is, once retrying is ruled out")
        self.assertIn("not the render", msg,
                      "and where it is NOT — a re-render is the expensive wrong move")

    def test_the_message_has_no_paths_or_jargon(self):
        """The operator's box rule: no file paths, no code, in front of a person."""
        with mock.patch.object(providers.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: self.serving(b"x" * 10, 100)):
            with self.assertRaises(EngineFlag) as cm:
                RealProvider._download_exact("http://x.test/v.mp4", self.dest)
        msg = str(cm.exception)
        for banned in ("\\", ".py", "Content-Length", "urlopen", "{"):
            self.assertNotIn(banned, msg, f"{banned!r} does not belong in a flag")

    def test_a_complete_download_is_promoted(self):
        """And it must NOT cry wolf on the normal case."""
        body = b"y" * 4096
        with mock.patch.object(providers.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: self.serving(body, len(body))):
            RealProvider._download_exact("http://x.test/v.mp4", self.dest)
        self.assertEqual(self.dest.read_bytes(), body)

    def test_no_stated_length_still_rejects_an_empty_file(self):
        with mock.patch.object(providers.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: self.serving(b"", None)):
            with self.assertRaises(EngineFlag):
                RealProvider._download_exact("http://x.test/v.mp4", self.dest)

    def test_no_stated_length_allows_a_real_file(self):
        """Not every server states a size. Refusing those would be crying wolf."""
        with mock.patch.object(providers.urllib.request, "urlopen",
                               side_effect=lambda *a, **k: self.serving(b"z" * 900, None)):
            RealProvider._download_exact("http://x.test/v.mp4", self.dest)
        self.assertEqual(self.dest.stat().st_size, 900)

    def test_the_paid_higgsfield_path_uses_the_same_guard(self):
        """E22b — found by asking whether the fault had SIBLINGS, not by it biting
        twice. b-roll clips and cover heroes are PAID, and a short one plays."""
        import inspect
        src = inspect.getsource(RealProvider._hf_download)
        self.assertIn("_download_exact", src)
        self.assertNotIn("copyfileobj", src)


# ---------------------------------------------------------------- E11
class StaleCodeGuard(unittest.TestCase):
    """EP15, 3 Aug: the fix landed at 09:10 and the process ran the broken code until
    a manual restart at 10:08, because `_code_changed()` is only checked in the OUTER
    acquire loop and a claimed episode never returns to it."""

    def _ctx(self):
        c = mock.MagicMock()
        c.id = "ep-id"
        return c

    def test_it_exits_when_code_changed(self):
        import engine
        with mock.patch.object(engine, "_code_changed", return_value="providers.py"), \
             mock.patch.object(engine.rail, "hand_back") as hb:
            with self.assertRaises(SystemExit):
                engine._code_changed_exit(self._ctx(), "while this episode was flagged")
        hb.assert_called_once()

    def test_it_hands_the_lease_back_before_exiting(self):
        """Exiting while still holding the lease strands the episode until the lease
        expires. But RELEASING it is worse, and that is the whole point of this case.

        🔴 THIS TEST USED TO ASSERT THE BUG, and it is the third time that has been
        caught in this repo (see test_shot_map_flows, which demanded the end-card
        error). It patched `rail.release` and required it to have been called once —
        while its own docstring explained that nulling the owner on a working status is
        the DEAD ZONE, matched by neither claim_next nor reclaim_stale.
        EP19, 9 Aug 2026 proved the docstring right: the guard fired, the episode went
        ownerless at 33% and sat there with its flag already cleared until a human asked
        why nothing was moving. `_code_changed_exit` was corrected to `rail.hand_back()`
        — a NAMED owner with an EXPIRED lease, so reclaim_stale takes it on the next
        tick — and this case went on demanding the old call, so it failed on the fix.
        A test that fails when the bug is fixed is testing the bug.

        It now asserts the behaviour, both halves: hand it back, by name, AND never
        release it. The second half is the one that has teeth — asserting hand_back
        alone would still pass if somebody called both.
        """
        import engine
        with mock.patch.object(engine, "_code_changed", return_value="engine.py"), \
             mock.patch.object(engine.rail, "hand_back") as hb, \
             mock.patch.object(engine.rail, "release") as rel:
            with self.assertRaises(SystemExit):
                engine._code_changed_exit(self._ctx(), "x")
        self.assertEqual(hb.call_args[0][0], "ep-id",
                         "the lease must be handed back for THIS episode")
        rel.assert_not_called()  # nulling the owner on a working status is the dead zone
        self.assertTrue(any("code" in str(a).lower() for a in hb.call_args[0]),
                        "the hand-back must say WHY, so the next reader is not guessing")

    def test_it_does_nothing_when_code_is_unchanged(self):
        import engine
        with mock.patch.object(engine, "_code_changed", return_value=None), \
             mock.patch.object(engine.rail, "release") as rel:
            engine._code_changed_exit(self._ctx(), "x")     # must NOT raise
        rel.assert_not_called()

    def test_BOTH_wait_loops_check_it(self):
        """⚠️ THE QUEUED PATCH ONLY COVERED ONE. There are two `needs_look` waits:
        `flag_and_wait` (a step raised) and the outer acquire loop (already flagged
        on pickup). EP15 was held in THE FIRST ONE — the one the written patch did
        not touch."""
        import inspect, engine
        self.assertIn("_code_changed_exit", inspect.getsource(engine.flag_and_wait),
                      "flag_and_wait is where EP15 actually sat for an hour")
        self.assertIn("_code_changed_exit", inspect.getsource(engine.cmd_run),
                      "the outer acquire loop's own needs_look wait")

    def test_it_raises_rather_than_returning_a_flag(self):
        """In flag_and_wait a bare `return` means 'retry the step' — on the very code
        we are trying to escape. One behaviour, decided in one place."""
        import inspect, engine
        self.assertIn("raise SystemExit", inspect.getsource(engine._code_changed_exit))


# ---------------------------------------------------------------- E16
class RejectedHeroComesBack(unittest.TestCase):
    """EP15: both heroes were rejected, the prompts corrected, the PNGs moved aside —
    and the engine re-downloaded the same two pictures, because deleting a file cannot
    invalidate a stored job id. Jodie picked one in good faith."""

    def test_same_prompt_gives_the_same_key(self):
        a = RealProvider._prompt_key("hero_A", "a crowd at dusk")
        b = RealProvider._prompt_key("hero_A", "a crowd at dusk")
        self.assertEqual(a, b, "the double-spend guard must still work")

    def test_a_changed_prompt_gives_a_different_key(self):
        a = RealProvider._prompt_key("hero_A", "a crowd at dusk")
        b = RealProvider._prompt_key("hero_A", "a crowd at dusk, no text")
        self.assertNotEqual(a, b, "a corrected prompt must be able to reach a create")

    def test_the_slot_still_separates_a_from_b(self):
        self.assertNotEqual(RealProvider._prompt_key("hero_A", "x"),
                            RealProvider._prompt_key("hero_B", "x"))

    def test_the_key_carries_the_prompt_hash(self):
        p = "a crowd at dusk"
        self.assertTrue(RealProvider._prompt_key("hero_A", p).endswith(
            hashlib.sha256(p.encode()).hexdigest()[:12]))

    def test_the_ledger_is_no_longer_keyed_on_the_bare_slot(self):
        import inspect
        src = inspect.getsource(RealProvider._generate_heroes)
        self.assertIn("_prompt_key", src)
        self.assertNotIn("book.setdefault(key,", src.replace(" ", ""))


# ---------------------------------------------------------------- escaping
class ScriptEscaping(unittest.TestCase):
    """Measured 4 Aug 2026: read through the Drive API, EP15's script comes back as
    `\\#` on every comment line and `Squeeze Those Odds\\!` in the title. Read through
    the export URL it is clean. Those backslashes would be frozen into script_snapshot
    as the record of what was approved — and spoken."""

    def _fetch(self, body: str):
        p = RealProvider.__new__(RealProvider)
        ep = {"script_doc_url": "https://docs.google.com/document/d/" + "a" * 30 + "/edit"}
        with mock.patch.object(providers.urllib.request, "urlopen",
                               return_value=_Resp(body.encode(), None, "text/plain")):
            return p.fetch_script(ep, write=False)

    def test_backslash_escaped_text_is_refused(self):
        body = ("\\# PP-EP16 header\n" + "Squeeze Those Odds\\! " + "word " * 80)
        with self.assertRaises(EngineFlag) as cm:
            self._fetch(body)
        self.assertIn("backslash", str(cm.exception).lower())

    def test_a_clean_script_passes(self):
        text, sha, _ = self._fetch("# PP-EP16 header\nSqueeze Those Odds! " + "word " * 80)
        self.assertIn("Odds!", text)
        self.assertEqual(len(sha), 64)

    def test_real_punctuation_is_not_mistaken_for_escaping(self):
        """Em dashes, curly quotes and exclamation marks are NOT the fault."""
        self._fetch("Squeeze Those Odds! — Part 1 — “quoted” … é " + "word " * 80)


# ---------------------------------------------------------------- images
class PageImagesWired(unittest.TestCase):
    """The guard was 9/9 green and did nothing, because nothing called it."""

    def test_render_cards_calls_it_before_the_batch_render(self):
        import inspect
        src = inspect.getsource(RealProvider.render_cards)
        self.assertIn("assert_page_images", src)
        self.assertLess(src.index("assert_page_images"), src.index("render_cards_batch.py"),
                        "it must run BEFORE a single clip is rendered")

    def test_it_flags_in_plain_english(self):
        d = Path(tempfile.mkdtemp())
        (d / "p.html").write_text('<img src="ebook-cover.png">', encoding="utf-8")
        with self.assertRaises(EngineFlag) as cm:
            providers.assert_page_images(d)
        msg = str(cm.exception)
        self.assertIn("ebook-cover.png", msg)
        self.assertIn("grey box", msg)
        self.assertNotIn("Traceback", msg)

    def test_it_is_quiet_when_everything_resolves(self):
        d = Path(tempfile.mkdtemp())
        (d / "p.html").write_text('<img src="a.png">', encoding="utf-8")
        (d / "a.png").write_bytes(b"\x89PNG")
        self.assertIn("every image", providers.assert_page_images(d))


if __name__ == "__main__":
    unittest.main(verbosity=2)
