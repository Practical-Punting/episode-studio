"""THE TITLE COMES FROM THE PAGE, NOT FROM THE URL. (B3.)

🔴 EP21 AND EP22 BOTH SHIPPED THROUGH AS "TRADE SECRETS". Nobody mistyped anything —
the URL slug said `trade` where the page said `track`, and the board pre-fills a new
ticket's title by title-casing the slug (app.js slugToTitle).

⚠️ AND THE PAGE HAD ALREADY BEEN READ. capture_article parses the <h1> and writes the
headline as the capture's first line. The headline was never unavailable; nothing
carried it back to the rail.

🔒 THE HALF THAT MATTERS IS WHAT IT REFUSES TO TOUCH. A title someone has edited or
approved is theirs. This may only ever replace a placeholder it can PROVE is untouched —
character-for-character what slugToTitle would have produced from this episode's own
source_url.

Run: python engine/test_title_from_headline.py
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E          # noqa: E402

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


# ── the placeholder rule must match the board exactly, or nothing else is safe ──
print("\nrecognising the board's placeholder (mirror of app.js slugToTitle)")

URL = "https://www.practicalpunting.com.au/a-z-of-betting/track-secrets-part-3"
check("slug -> title matches the board's rule",
      E._slug_title(URL) == "Track Secrets Part 3", E._slug_title(URL))
check("a trailing id is dropped",
      E._slug_title("https://x.com/a/trade-secrets-12345") == "Trade Secrets",
      E._slug_title("https://x.com/a/trade-secrets-12345"))
check("an extension is dropped",
      E._slug_title("https://x.com/a/track-secrets.html") == "Track Secrets",
      E._slug_title("https://x.com/a/track-secrets.html"))
check("a trailing slash is ignored",
      E._slug_title("https://x.com/a/track-secrets/") == "Track Secrets")
check("a genuinely empty tail falls back", E._slug_title("/") == "New episode",
      E._slug_title("/"))
check("a bare host still yields something rather than nothing",
      E._slug_title("https://x.com/") == "X", E._slug_title("https://x.com/"))
check("rubbish is not a crash", E._slug_title("") == "New episode")


# ── the headline, out of the capture ─────────────────────────────────────────
print("\nreading the headline the capture already wrote")

CAP = "# TRACK SECRETS (Part 3)\n\nBy Statsman\n\nSome body text.\n"
check("the shouted headline comes back in house form",
      E._title_from_capture(CAP) == "Track Secrets (Part 3)", E._title_from_capture(CAP))
check("a mixed-case headline is left as the author wrote it",
      E._title_from_capture("# The Best Courses in Victoria\n") ==
      "The Best Courses in Victoria")
check("digits are not mangled",
      "2026" in E._title_from_capture("# THE 2026 GUIDE\n"),
      E._title_from_capture("# THE 2026 GUIDE\n"))
check("no headline is empty, not a crash", E._title_from_capture("no heading here") == "")
check("empty input is empty", E._title_from_capture("") == "")


# ── THE REGRESSION JODIE ASKED FOR ───────────────────────────────────────────
print("\na slug that differs from the headline yields the HEADLINE")

WROTE = {}


class FakeRail:
    @staticmethod
    def set_fields(_id, fields):
        WROTE.update(fields)


real_rail, real_log = E.rail, E.log
E.rail, E.log = FakeRail, (lambda *a, **k: None)
try:
    # The exact EP21/EP22 fault: slug says `trade`, the page says `track`.
    ep = {"id": "x", "title": "Trade Secrets Part 3",
          "source_url": "https://www.practicalpunting.com.au/a/trade-secrets-part-3"}
    E._retitle_from_capture(ep, "# TRACK SECRETS (Part 3)\n")
    check("the rail is corrected to the page's headline",
          WROTE.get("title") == "Track Secrets (Part 3)", str(WROTE))
    check("and the row in hand is updated too", ep["title"] == "Track Secrets (Part 3)")

    # ── and everything it must NOT do ────────────────────────────────────────
    print("\nwhat it must never overwrite")

    WROTE.clear()
    ep2 = {"id": "x", "title": "A Title Jodie Typed Herself",
           "source_url": "https://www.practicalpunting.com.au/a/trade-secrets-part-3"}
    E._retitle_from_capture(ep2, "# TRACK SECRETS (Part 3)\n")
    check("an EDITED title is left alone", WROTE == {} and
          ep2["title"] == "A Title Jodie Typed Herself", str(WROTE))

    WROTE.clear()
    ep3 = {"id": "x", "title": "Trade Secrets Part 3", "title_approved": True,
           "source_url": "https://www.practicalpunting.com.au/a/trade-secrets-part-3"}
    E._retitle_from_capture(ep3, "# TRACK SECRETS (Part 3)\n")
    check("an APPROVED title is left alone even if it is the placeholder",
          WROTE == {}, str(WROTE))

    WROTE.clear()
    ep4 = {"id": "x", "title": "Track Secrets (Part 3)",
           "source_url": "https://www.practicalpunting.com.au/a/track-secrets-part-3"}
    E._retitle_from_capture(ep4, "# TRACK SECRETS (Part 3)\n")
    check("no write when it already agrees", WROTE == {}, str(WROTE))

    WROTE.clear()
    ep5 = {"id": "x", "title": "Trade Secrets Part 3",
           "source_url": "https://www.practicalpunting.com.au/a/trade-secrets-part-3"}
    E._retitle_from_capture(ep5, "no heading in this capture at all")
    check("no headline means no write", WROTE == {}, str(WROTE))

    WROTE.clear()
    ep6 = {"id": "x", "title": "Trade Secrets Part 3", "source_url": ""}
    E._retitle_from_capture(ep6, "# TRACK SECRETS (Part 3)\n")
    check("no source_url means no write (cannot prove it is a placeholder)",
          WROTE == {}, str(WROTE))

    # A rail that throws must never take the build down with it.
    class AngryRail:
        @staticmethod
        def set_fields(_id, _fields):
            raise RuntimeError("rail is down")

    E.rail = AngryRail
    ep7 = {"id": "x", "title": "Trade Secrets Part 3",
           "source_url": "https://www.practicalpunting.com.au/a/trade-secrets-part-3"}
    E._retitle_from_capture(ep7, "# TRACK SECRETS (Part 3)\n")   # must not raise
    check("a rail failure is swallowed, not fatal", True)
finally:
    E.rail, E.log = real_rail, real_log

print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
