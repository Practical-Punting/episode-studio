"""THE SMOKE TEST'S OWN LOGIC, PROVED WITHOUT THE NETWORK.

smoke_capture reads one real article per site section and says which SHAPES still parse.
Its own correctness must not depend on the site being up, so everything decidable
off-line is decided here: which section a URL belongs to, which articles get tried, and
how a verdict is classified.

🔴 THE FAULT IT GUARDS. Capture has broken on a NEW SHAPE every time — EP20's missing
byline, EP23's layout markers — and each was found DURING A LIVE RUN by Jodie. A class of
fault only ever found in production is a class nobody is testing.

⚠️ AND THE FIRST VERSION OF THE SECTION RULE WAS WRONG IN A WAY THAT WOULD HAVE HIDDEN
THAT. Taking the first path segment gave ONE section for all fourteen episodes, because
every article lives under /pp-online/ — a corpus-shaped single-shape check. The real
URLs are pinned below so that cannot come back.

Run: python engine/test_smoke_capture.py
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import smoke_capture as S          # noqa: E402

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


# Real source_urls off the rail, verbatim — the corpus this runs against.
REAL = {
    23: "https://practicalpunting.com.au/pp-online/a-z-of-betting/form-analysis/racetracks/track-secrets-part-3-19860504",
    20: "https://practicalpunting.com.au/pp-online/professional-betting/professional-punters/Bill-Benter/Bill-Benter-Professional-Gambler",
    19: "https://practicalpunting.com.au/pp-online/a-z-of-betting/staking-plans/progression-betting/10-systems-for-action-hungry-punters-part-1-200405",
    18: "https://practicalpunting.com.au/pp-online/a-z-of-betting/favourites/statistics/those-top-6-favourites-20061221",
    16: "https://practicalpunting.com.au/pp-online/staking/staking-plans/money-management/each-way-betting-forever-part-2-20111006",
    7:  "https://practicalpunting.com.au/pp-online/professional-betting/professional-punting/betting-strategies/when-do-you-bet-each-way-part-3-20150625",
}

print("\nsections — the thing we want one of EACH of")

check("the /pp-online/ prefix is not mistaken for a section",
      all(S.section_of(u) != "pp-online" for u in REAL.values()))
check("racetracks -> a-z-of-betting/form-analysis",
      S.section_of(REAL[23]) == "a-z-of-betting/form-analysis", S.section_of(REAL[23]))
check("the PROFILE shape gets its own section (EP20's, the byline-less one)",
      S.section_of(REAL[20]) == "professional-betting/professional-punters",
      S.section_of(REAL[20]))
check("an article's own subject does not become a section",
      "Bill-Benter" not in S.section_of(REAL[20]), S.section_of(REAL[20]))
check("staking sits apart from a-z staking-plans",
      S.section_of(REAL[16]) == "staking/staking-plans" and
      S.section_of(REAL[19]) == "a-z-of-betting/staking-plans",
      f"{S.section_of(REAL[16])} vs {S.section_of(REAL[19])}")
check("punters and punting are not confused",
      S.section_of(REAL[20]) != S.section_of(REAL[7]))

# THE REGRESSION FOR THE BUG I SHIPPED FIRST: the real corpus must not collapse to one.
got = {S.section_of(u) for u in REAL.values()}
check("the real corpus yields MANY sections, not one",
      len(got) >= 5, f"only {len(got)}: {sorted(got)}")

check("a URL with no path is not a crash", S.section_of("https://x.com") == "(root)")
check("rubbish is not a crash", S.section_of("") in ("(root)", "(unparsable)"))


print("\npicking what to try")

rows = [{"ep": ep, "url": u, "section": S.section_of(u)} for ep, u in
        sorted(REAL.items(), reverse=True)]
picked = S.one_per_section(rows)
check("one article per section", len({r["section"] for r in picked}) == len(picked))
check("every section is represented",
      {r["section"] for r in picked} == {r["section"] for r in rows})
check("the NEWEST article of a section is the one tried",
      next(r["ep"] for r in picked if r["section"] == "a-z-of-betting/form-analysis") == 23)


print("\nclassifying a verdict (the parser stubbed out)")

BODY = "word " * 400
GOOD = f"# A HEADLINE\n\n{S.MARKER_BEGIN}\n{BODY}\n{S.MARKER_END}\n"


class FakeCap:
    result = None
    @staticmethod
    def build(url, n, pp, write=False):
        if isinstance(FakeCap.result, Exception):
            raise FakeCap.result
        return "dest", FakeCap.result


sys.modules["capture_article"] = FakeCap

FakeCap.result = GOOD
check("a good capture passes", S.check_capture("u")[0] == "pass", str(S.check_capture("u")))

FakeCap.result = f"# H\n\n{S.MARKER_BEGIN}\nonly a few words\n{S.MARKER_END}\n"
check("a body too short to be an article FAILS", S.check_capture("u")[0] == "fail")

FakeCap.result = f"{S.MARKER_BEGIN}\n{BODY}\n{S.MARKER_END}\n"
check("no headline FAILS (this is the EP21/EP22 title fault's other half)",
      S.check_capture("u")[0] == "fail")

FakeCap.result = f"# A HEADLINE\n\n{BODY}\n"
check("an UNBOUNDED body FAILS — B2's whole case", S.check_capture("u")[0] == "fail")

FakeCap.result = ""
check("nothing at all FAILS", S.check_capture("u")[0] == "fail")

# 🔒 the distinction the nightly depends on
FakeCap.result = RuntimeError("this page carries OCR damage: ['l/s'] — a fraction")
v, why = S.check_capture("u")
check("a page the SITE damaged is 'page', not 'fail'", v == "page", f"{v}: {why}")

FakeCap.result = RuntimeError("Unrecognised: no article body found on this page")
check("a shape the PARSER cannot read is 'fail'", S.check_capture("u")[0] == "fail")

FakeCap.result = RuntimeError("boom")
check("an unexpected explosion is a fail, not a crash",
      S.check_capture("u")[0] == "fail")

print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
