"""Proof for check_page_images.py — against THE page that actually failed.

"All green" means nothing unless the suite covers what you changed. So this does not
test a synthetic page with a made-up name. It copies the REAL
`assets/end-card-template.html` — the file whose `<img src="ebook-cover.png">` put a
grey box and the words "Killer Strategies for the Trifecta" into EP15's finished film —
into a temp folder and asserts the check fails on it while the image is absent and
passes once it is there.

Hermetic: nothing here touches G:. (That is also what the hardcoded-episode-path lint
requires of a suite in this folder.)
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_page_images as cpi

REPO = Path(__file__).resolve().parent.parent
END_CARD = REPO / ".claude/skills/pp-episode-production/assets/end-card-template.html"

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000100ffff03000006"
    "0005570cf50000000049454e44ae426082")


class RealEndCardPage(unittest.TestCase):
    """THE case. EP15, 4 Aug 2026."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.assertTrue(END_CARD.is_file(), f"the end card template moved: {END_CARD}")
        shutil.copyfile(END_CARD, self.d / "end-card-template.html")
        (self.d / "assets").mkdir()
        (self.d / "assets/logo.png").write_bytes(PNG)     # the page's other image

    def test_missing_ebook_cover_is_caught(self):
        """The exact hole: ebook-cover.png absent -> the check must name it."""
        bad = cpi.scan_page(self.d / "end-card-template.html")
        refs = [r for r, _ in bad]
        self.assertIn("ebook-cover.png", refs,
                      "the end card's cover slot was missing and the check did not say so — "
                      "this is the fault that shipped a grey box with alt text into EP15")

    def test_present_ebook_cover_passes(self):
        """And it must go quiet once the hole is refilled — a check that always fires
        is a check someone turns off."""
        (self.d / "ebook-cover.png").write_bytes(PNG)
        self.assertEqual(cpi.scan_page(self.d / "end-card-template.html"), [])
        self.assertEqual(cpi.scan_dir(self.d), {})

    def test_exit_code_and_message_name_the_file(self):
        """The operator has to be able to act on it without reading the repo."""
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cpi.main(["check_page_images.py", str(self.d)])
        out = buf.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("ebook-cover.png", out)
        self.assertIn("end-card-template.html", out)


class DoesNotCryWolf(unittest.TestCase):
    """A lint that cries wolf is a lint someone turns off."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)

    def _page(self, body):
        (self.d / "p.html").write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
        return cpi.scan_page(self.d / "p.html")

    def test_remote_urls_are_not_our_problem(self):
        self.assertEqual(self._page('<img src="https://x.test/a.png">'), [])

    def test_data_uris_are_not_our_problem(self):
        self.assertEqual(self._page('<img src="data:image/png;base64,iVBORw0=">'), [])

    def test_scripts_and_stylesheets_are_not_images(self):
        self.assertEqual(self._page('<script src="pp-anim.js"></script>'), [])

    def test_unrendered_template_slots_are_skipped(self):
        self.assertEqual(self._page('<img src="{{hero}}.png">'), [])

    def test_css_background_images_are_checked_too(self):
        bad = self._page('<div style="background:url(hero.png)"></div>')
        self.assertEqual([r for r, _ in bad], ["hero.png"])

    def test_query_strings_and_subfolders_resolve(self):
        (self.d / "assets").mkdir()
        (self.d / "assets/logo.png").write_bytes(PNG)
        self.assertEqual(self._page('<img src="assets/logo.png?v=3">'), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
