#!/usr/bin/env python3
"""smoke_capture.py — CAN WE STILL READ THE SITE? Asked of every SHAPE, off-line.

    python engine/smoke_capture.py                 # every built episode's source_url
    python engine/smoke_capture.py --urls f.txt    # one URL per line instead
    python engine/smoke_capture.py --section a-z-of-betting   # just one section
    python engine/smoke_capture.py --refresh-corpus           # re-read the rail, cache it

🔴 WHY THIS EXISTS — THE ONE FAULT THAT HAS RECURRED EVERY TIME.

Capture has broken on a NEW ARTICLE SHAPE on episode after episode, and each time it was
fixed for that one shape:

    EP20   a profile with NO BYLINE where the parser required one
    EP23   a page carrying layout markers the parser had never seen

Every one of those was found DURING A LIVE RUN, by Jodie, with an episode already
queued and the studio apparently working. The fault is not any of the individual
shapes. **The fault is that we only ever learn about a shape when it stops a build.**

    A CLASS OF FAULT THAT IS ONLY EVER FOUND IN PRODUCTION IS A CLASS NOBODY IS TESTING.

So this reads one real article from EVERY SECTION OF THE SITE we have ever built from,
on a schedule, and says which shapes still parse. A shape that breaks is then found the
night before by a machine, not at 7am by a person holding a queued episode.

📚 THE CORPUS IS THE EPISODES THEMSELVES (Jodie, 13 Aug 2026). Every built episode's
`source_url` is on the rail, and between them they span the site's sections — the a-z
how-tos, the profiles, the form-analysis and racetrack pages. That corpus needs no
maintaining and grows by itself: the price of building an episode is that its shape is
covered for ever after. It is cached to `engine/smoke-corpus.json` so a run does not
depend on the rail being reachable.

⚠️ WHAT "PASS" MEANS HERE, AND WHAT IT DOES NOT. This proves the page can still be READ
and BOUNDED — a headline, an article body of plausible length, and both markers. It does
NOT prove the article is correctly interpreted; that is script_fidelity's job, against
the capture, later. A green smoke run means "the shapes still parse", not "the episodes
would be right".

🔒 IT NEVER WRITES A CAPTURE. `build(..., write=False)` — this must not be able to leave
an article of record behind, because a capture is what every downstream check measures
truth against for the life of an episode.
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
import urllib.parse
from contextlib import redirect_stdout

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
CORPUS = HERE / "smoke-corpus.json"
sys.path.insert(0, str(REPO / ".claude/skills/pp-episode-production/scripts"))
sys.path.insert(0, str(HERE))

MARKER_BEGIN = "---- ARTICLE TEXT BEGINS ----"
MARKER_END = "---- ARTICLE TEXT ENDS ----"
MIN_WORDS = 120          # below this it is a stub, a paywall, or a parse that lost the body


SECTION_DEPTH = 2        # measured against the real corpus — see below
SITE_PREFIX = "pp-online"


def section_of(url: str) -> str:
    """The site section a URL belongs to — the thing we want one of EACH of.

    ⚠️ THE DEPTH IS MEASURED, NOT GUESSED. Every article on this site sits under
    `/pp-online/`, so the first segment separates nothing: taking it produced ONE
    section for all fourteen built episodes, which would have made this whole test a
    single-shape check wearing a corpus. The next TWO segments are what actually vary:

        a-z-of-betting/form-analysis      racetracks, times, range-of-techniques
        a-z-of-betting/staking-plans      progression betting
        a-z-of-betting/statistics         tab-numbers
        a-z-of-betting/favourites         statistics
        professional-betting/professional-punters   the profiles (EP20's shape)
        professional-betting/professional-punting   betting strategies
        staking/staking-plans             money management

    Three segments would split on an article's own subject (`.../Bill-Benter/...`) and
    fragment the corpus into one section per episode, which covers no more shapes and
    costs a fetch each.
    """
    try:
        parts = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
        if parts and parts[0] == SITE_PREFIX:
            parts = parts[1:]
        if len(parts) <= 1:
            return "(root)"
        return "/".join(parts[:SECTION_DEPTH])
    except Exception:                                              # noqa: BLE001
        return "(unparsable)"


def corpus_from_rail() -> list[dict]:
    """Every built episode's source_url, newest first. Raises if the rail is unreachable."""
    import rail
    out = []
    for e in rail.list_all():
        url = (e.get("source_url") or "").strip()
        if not url:
            continue
        out.append({"ep": e.get("ep_number"), "url": url, "section": section_of(url)})
    out.sort(key=lambda r: -(r["ep"] or 0))
    return out


def load_corpus(refresh: bool) -> list[dict]:
    if not refresh and CORPUS.is_file():
        try:
            return json.loads(CORPUS.read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            pass
    rows = corpus_from_rail()
    CORPUS.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def one_per_section(rows: list[dict]) -> list[dict]:
    """One article from each section — the point is SHAPE coverage, not volume.

    Newest first, so the shape most likely to reflect the site as it is today is the one
    tried. Everything else stays available behind --all.
    """
    seen, out = set(), []
    for r in rows:
        if r["section"] in seen:
            continue
        seen.add(r["section"])
        out.append(r)
    return out


# 🔴 A REFUSAL ABOUT THE PAGE IS NOT A REFUSAL ABOUT THE SHAPE, and mixing them would
# wreck this test's only job. EP16's live page carries OCR damage — `l/s` where the
# article says `1/5` — and capture_article refuses it ON PURPOSE, permanently, because a
# subtly wrong article of record redefines truth for every downstream check. That refusal
# is CORRECT and it will never stop being true, so counting it as a failure would leave
# this run red for ever.
#
# ⚠️ AND A TEST THAT IS ALWAYS RED IS A TEST NOBODY READS — the same reasoning
# preflight_cards uses to emit no warnings at all: "a warning that is wrong about half
# the time trains people to stop reading warnings". So a damaged page is reported, loudly
# and by name, in its own category, and does not fail the run. --strict fails on it too.
PAGE_NOT_SHAPE = ("OCR damage",)


def check_capture(url: str) -> tuple[str, str]:
    """('pass'|'fail'|'page', why). Runs the real parser, writes nothing, never raises."""
    try:
        import capture_article as cap
    except Exception as e:                                         # noqa: BLE001
        return "fail", f"capture_article will not import ({type(e).__name__}: {e})"
    try:
        # build() prints a running commentary; a smoke run wants the verdict, not the log.
        buf = io.StringIO()
        with redirect_stdout(buf):
            _dest, text = cap.build(url, 0, pathlib.Path("."), write=False)
    except Exception as e:                                         # noqa: BLE001
        msg = f"{type(e).__name__}: {str(e)[:220]}"
        if any(m in str(e) for m in PAGE_NOT_SHAPE):
            return "page", msg
        return "fail", msg

    if not text:
        return "fail", "the parser returned nothing at all"
    head = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), "")
    if not head:
        return "fail", "no headline — the <h1> was not found or was empty"
    if MARKER_BEGIN not in text or MARKER_END not in text:
        return "fail", "the article body was not BOUNDED (a marker is missing)"
    body = text.split(MARKER_BEGIN)[-1].split(MARKER_END)[0]
    words = len(body.split())
    if words < MIN_WORDS:
        return "fail", (f"only {words} words between the markers — a stub, a paywall, or "
                        f"a parse that lost the body")
    return "pass", f"{head[:58]!r}, {words} words"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--urls", help="a file of URLs, one per line, instead of the rail")
    ap.add_argument("--section", help="only this site section")
    ap.add_argument("--all", action="store_true",
                    help="every corpus URL, not one per section")
    ap.add_argument("--refresh-corpus", action="store_true",
                    help="re-read the rail and rewrite the cache")
    ap.add_argument("--log-dir",
                    help="also append this run to <dir>/smoke-YYYY-MM-DD.log. Done HERE "
                         "rather than by a shell redirect because %DATE% is locale-"
                         "dependent (it produced 'smoke-08-13-Thu.log' on this machine, "
                         "which neither sorts nor survives a year change) and the cmd "
                         "quoting needed to work around that broke the task outright.")
    ap.add_argument("--strict", action="store_true",
                    help="fail on a damaged page too, not only on a broken shape")
    a = ap.parse_args(argv)

    if a.log_dir:
        import datetime
        d = pathlib.Path(a.log_dir)
        d.mkdir(parents=True, exist_ok=True)
        fh = open(d / f"smoke-{datetime.date.today().isoformat()}.log", "a",
                  encoding="utf-8")

        class _Tee:
            def write(self, s):
                fh.write(s)
                try:
                    sys.__stdout__.write(s)
                except Exception:
                    pass
            def flush(self):
                fh.flush()
        sys.stdout = _Tee()
        print(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} =====")

    if a.urls:
        rows = [{"ep": None, "url": u.strip(), "section": section_of(u.strip())}
                for u in pathlib.Path(a.urls).read_text(encoding="utf-8").splitlines()
                if u.strip() and not u.strip().startswith("#")]
    else:
        try:
            rows = load_corpus(a.refresh_corpus)
        except Exception as e:                                     # noqa: BLE001
            print(f"could not build a corpus: {type(e).__name__}: {e}")
            print("Pass --urls with a file of article links instead.")
            return 2

    if a.section:
        rows = [r for r in rows if r["section"] == a.section]
    if not a.all:
        rows = one_per_section(rows)
    if not rows:
        print("no URLs to try — nothing was checked, and that is NOT a pass.")
        return 2

    print(f"CAPTURE SMOKE TEST — {len(rows)} shape(s), "
          f"{len({r['section'] for r in rows})} section(s)\n")
    failures, damaged = [], []
    for r in rows:
        verdict, why = check_capture(r["url"])
        tag = {"pass": "PASS", "fail": "FAIL", "page": "PAGE"}[verdict]
        ep = f"EP{r['ep']:02d}" if r.get("ep") else "  —"
        print(f"  {tag}  {r['section']:<42} {ep}  {why[:150]}")
        if verdict == "fail":
            failures.append((r, why))
        elif verdict == "page":
            damaged.append((r, why))

    print()
    # NEVER SILENT. A damaged page is stated every run, with its URL, whether or not it
    # is being counted as a failure — a category that quietly absorbs things is how a
    # green run comes to mean nothing.
    if damaged:
        print(f"{len(damaged)} PAGE(S) THE SITE ITSELF HAS DAMAGED — the parser is fine, "
              f"the page is not{' (counted as failures: --strict)' if a.strict else ''}:")
        for r, why in damaged:
            print(f"  · {r['section']}  {r['url']}")
            print(f"      {why[:200]}")
        print()
    if a.strict:
        failures += damaged
    if failures:
        print(f"{len(failures)} SHAPE(S) NO LONGER PARSE — fix these before a fresh run:")
        for r, why in failures:
            print(f"  · {r['section']}  {r['url']}")
            print(f"      {why[:300]}")
        return 1
    print(f"all {len(rows) - len(damaged)} readable shape(s) still parse"
          + (f"; {len(damaged)} page(s) damaged at source." if damaged else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
