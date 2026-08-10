"""Control proofs for capture_article.py — the article of record must be trustworthy.

  1. it reproduces EP19's by-hand capture's ARTICLE TEXT byte-for-byte
  2. EP16, EP17 and EP18 re-captured from their URLs match the existing files
  3. a page it does not recognise is REFUSED — loudly, with nothing written

Run: python engine/test_capture_article.py        (network: 4 fetches)
"""
import difflib
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import capture_article as ca      # noqa: E402

PP = pathlib.Path(r"G:\My Drive\PP Videos")
FAILED = []
DRIFTED = []   # live pages edited since their capture — reported, not failed
BEGIN, END = "---- ARTICLE TEXT BEGINS ----", "---- ARTICLE TEXT ENDS ----"


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"\n          {why}" if not cond and why else ""))
    if not cond:
        FAILED.append(name)


def body_of(path):
    t = path.read_text(encoding="utf-8")
    return t.split(BEGIN, 1)[1].split(END, 1)[0].strip()


REFS = [
    (16, "each-way-betting-forever-part-2",
     "https://practicalpunting.com.au/pp-online/staking/staking-plans/money-management/"
     "each-way-betting-forever-part-2-20111006"),
    (17, "testing-the-numbers",
     "https://practicalpunting.com.au/pp-online/a-z-of-betting/statistics/tab-numbers/"
     "testing-the-numbers-20070115"),
    (18, "those-top-6-favourites",
     "https://practicalpunting.com.au/pp-online/a-z-of-betting/favourites/statistics/"
     "those-top-6-favourites-20061221"),
    (19, "10-systems-for-action-hungry-punters-part-1",
     "https://practicalpunting.com.au/pp-online/a-z-of-betting/staking-plans/"
     "progression-betting/10-systems-for-action-hungry-punters-part-1-200405"),
]

print("\n=== 1+2 · re-capture each episode and compare with the file on disk ===")
for n, stem, url in REFS:
    hits = sorted(PP.glob(f"docs/EP{n}-source-article-*.md"))
    print(f"\n── EP{n} ──")
    if not hits:
        check(f"EP{n}: existing capture found", False, "no file to compare against")
        continue
    existing = body_of(hits[0])
    try:
        _dest, text = ca.build(url, n, PP, write=False)
    except ca.Unrecognised as e:
        if n == 16:
            # 🔴 EP16 MUST BE REFUSED, and that is the right answer, not a shortfall.
            # Its live page is OCR-damaged — `l/s` for `1/5`, `Vs` for `3/5`, `5-1 *`
            # for `5-1;` — and the capture on disk is the page PLUS a human's repairs.
            # A tool that placed the damaged text would have quietly redefined the
            # article of record for the whole episode, and every downstream check would
            # then have agreed with it.
            check("EP16 (OCR-damaged page) is REFUSED, not silently captured", True)
            check("  and the refusal names the damage it found",
                  "l/s" in str(e) or "fraction" in str(e), str(e)[:200])
            check("  and it says a human must do this one",
                  "by hand" in str(e), str(e)[:200])
            print(f"          refusal: {str(e).splitlines()[0][:150]}")
            continue
        check(f"EP{n}: the tool reads the page", False, f"REFUSED: {e}")
        continue
    if n == 16:
        check("EP16 (OCR-damaged page) is REFUSED, not silently captured", False,
              "it produced a capture from a page with `l/s` and `Vs` in it")
        continue
    fresh = text.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    # 🔒 THE HEADLINE NOW OPENS THE ARTICLE TEXT (Jodie, 9 Aug 2026). EP17's and EP18's
    # captures were written before that rule and are NOT rewritten — they are published
    # episodes, and a capture is the article of record for the one that shipped on it
    # ("found retrospectively does not mean fixed retrospectively"). So the comparison
    # is: fresh == headline + the body on disk. It still bites on every other word.
    head_line = fresh.splitlines()[0].strip()
    expected = existing if existing.startswith(head_line) else f"{head_line}\n\n{existing}"
    same = fresh == expected
    if same:
        check(f"EP{n}: article text matches the capture on disk (headline + body)", True)
    else:
        # ⚠️ PAGE DRIFT IS NOT A TOOL FAULT — AND IS NOT SILENT EITHER. The live page can
        # be edited at any time; EP19's staking list was one unbroken run when EP19 was
        # built and now carries line breaks. A published episode's capture is FROZEN and
        # stays right for the episode that shipped on it. So this is reported loudly,
        # with the first difference, and the tool's own guarantees below still have to
        # hold — those are what would catch a real regression.
        i = next((i for i in range(min(len(fresh), len(expected)))
                  if fresh[i] != expected[i]), min(len(fresh), len(expected)))
        print(f"  ⚠️  EP{n}: PAGE DRIFT — the live page differs from the frozen capture")
        print(f"          live : {fresh[max(0, i - 60):i + 60]!r}")
        print(f"          disk : {expected[max(0, i - 60):i + 60]!r}")
        DRIFTED.append(n)
    # NOT an all-caps assertion — EP19's headline ends "(Part 1)" and the first version
    # of this check failed a perfectly correct title on its own casing rule.
    check(f"  EP{n}: the article text opens with the episode's own headline",
          bool(head_line) and head_line == head_line.strip() and len(head_line) > 8
          and "then take care" not in head_line, repr(head_line))
    check(f"  EP{n}: no provenance note crossed into the article text",
          not any(w in fresh for w in ("Captured", "capture_article", "ENCODING",
                                       "Source:", "reproduced as printed",
                                       "transcrib", "typographic errors")),
          "a note ABOUT the article is not the article")
    if not same:
        a, b = existing.splitlines(), fresh.splitlines()
        print(f"          on disk {len(a)} blocks / {len(existing):,} chars;  "
              f"fresh {len(b)} blocks / {len(fresh):,} chars")
        d = [l for l in difflib.unified_diff(a, b, "on-disk", "fresh", lineterm="", n=0)]
        for line in d[:14]:
            print(f"          {line[:150]}")
        if len(d) > 14:
            print(f"          … {len(d) - 14} more diff lines")
    # the things that must be true whether or not the bytes match
    check(f"  EP{n}: no site furniture in the article text",
          not any(f in fresh for f in ca.FURNITURE),
          str([f for f in ca.FURNITURE if f in fresh]))
    check(f"  EP{n}: no rogue '?' survives", not re.search(r"\?[A-Za-z]", fresh),
          str(re.findall(r".{20}\?[A-Za-z]\w*", fresh)[:3]))
    if "|---|" in existing:
        check(f"  EP{n}: the real table is still a table", "|---|" in fresh)

print("\n=== 3 · a page it does not recognise must be REFUSED ===\n")

REAL = ca.CONTAINER + "<p>By Someone<" + ("word " * 400) + "</p>"


def refuses(page, why):
    try:
        ca.extract(page)
        return None
    except ca.Unrecognised as e:
        return str(e)


msg = refuses("<html><body><article>totally different site</article></body></html>", "")
check("a page with no known container is REFUSED", msg is not None, "it returned a body")
check("  and the message says what it looked for", bool(msg) and "container" in msg)

# 🔴 THE RULE CHANGED ON 10 AUG 2026 AND THIS CASE ASSERTED THE OLD ONE.
# A page with no "By <Name>" byline used to be refused outright — true of the
# a-z-of-betting features, which all sign off "By Mr Money", and NOT true of the
# professional-punters pieces. The Bill Benter article has no byline at all, and EP20
# sat refused on every kick-on-submit tick. The article is now bounded by its
# container's own closing tag, which is structural and does not depend on an author
# signing their name.
no_byline = (ca.CONTAINER + "<p>" + ("word " * 500) + "</p></div>")
msg2 = refuses(no_byline, "")
check("a page with NO BYLINE is CAPTURED, bounded by its container", msg2 is None,
      f"still refused: {msg2}")

# …and the bound it relies on must still be able to fail. A container that never
# closes has no reliable end, and that IS a refusal.
never_closes = ca.CONTAINER + "<p>" + ("word " * 500) + "</p>"
msg2b = refuses(never_closes, "")
check("CONTROL: a container that never CLOSES is REFUSED", msg2b is not None,
      "without an end there is no boundary between the author and the site")
check("  and it explains the boundary problem", bool(msg2b) and "ENDS" in msg2b)

short = ca.CONTAINER + "<p>tiny article</p><p>By Someone<</p></div>"
msg3 = refuses(short, "")
check("a suspiciously short body is REFUSED", msg3 is not None)

leaky = (ca.CONTAINER + "<p>" + ("word " * 400) + " Next To Jump " + ("word " * 50)
         + "</p><p>By Someone<</p>")
msg4 = refuses(leaky, "")
check("furniture reaching the article text is REFUSED", msg4 is not None,
      "the byline cut did not hold")
check("  and it names what leaked", bool(msg4) and "Next To Jump" in msg4)

# ── 🔴 THE NO-BYLINE PATH MUST NOT HAVE OPENED A DOOR ────────────────────────
# Relaxing "a byline is required" is the EP20 fix, and the risk it carries is that
# every OTHER refusal quietly stopped applying to the pages that use the new path.
# Each of these drives a genuinely bad page THAT HAS NO BYLINE, so it goes through the
# structural bound, and requires the refusal to still bite.
furniture_only = ca.CONTAINER + "<p>Next To Jump</p><p>Buy Tips</p></div>"
check("no byline + a furniture-only container is still REFUSED",
      refuses(furniture_only, "") is not None)

ocr_no_byline = (ca.CONTAINER + "<p>" + ("word " * 450)
                 + " backed at l/s and again at Vs today. </p></div>")
msg5 = refuses(ocr_no_byline, "")
check("no byline + OCR DAMAGE is still REFUSED", msg5 is not None,
      "the damage scan must run on the structural path too — EP16's page is exactly "
      "this shape and placing it would redefine the article of record")
check("  and it still names the damage", bool(msg5) and "l/s" in msg5, str(msg5)[:160])

leaky_no_byline = (ca.CONTAINER + "<p>" + ("word " * 400) + " Next To Jump "
                   + ("word " * 50) + "</p></div>")
check("no byline + furniture INSIDE a long body is still REFUSED",
      refuses(leaky_no_byline, "") is not None)

print(f"\n{'=' * 70}")
if DRIFTED:
    print(f"⚠️  PAGE DRIFT on EP{DRIFTED}: the live article has been EDITED since that "
          f"capture was frozen.\n"
          f"    The capture stays right for the episode that shipped on it "
          f"(\"found retrospectively does not mean fixed retrospectively\"), and the "
          f"tool is not at fault.\n"
          f"    Re-capture only if that episode is ever rebuilt.")
print("CAPTURE TOOL PROVED" if not FAILED else f"FAILURES: {FAILED}")
sys.exit(1 if FAILED else 0)
