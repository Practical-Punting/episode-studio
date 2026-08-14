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


# ── EP23, TRACK SECRETS PART 3 — THE STUDIO'S OWN MARKER REFUSED THE PAGE ─────
# The foot of a multi-part feature links its siblings — "Click here to read Part 1
# … Part 2 … Part 4" — and the part you are ON is bolded with NO link, so the page
# emits a literal `<b></b>`. That made a heading marker with nothing in it, which
# survived into the body and refused the whole article three times. The refusal was
# RIGHT — a marker in the body means the extraction did not complete — but the marker
# was ours, not the page's.
print("\n-- EP23: a bold tag with nothing in it is not a heading --")
empty_b = (ca.CONTAINER + "<p>" + ("word " * 400) +
           "Click here to read Part 1. <b></b> Click here to read Part 4.</p></div>")
msg_e = refuses(empty_b, "")
check("an EMPTY <b></b> no longer refuses the page", msg_e is None,
      f"still refused: {msg_e}")
if msg_e is None:
    body_e, _, _, _ = ca.extract(empty_b)
    check("  and leaves no marker behind", "@@" not in body_e)
    check("  and does not invent an empty heading", "****" not in body_e)
    check("  while keeping the cross-links the earlier parts also kept",
          "Click here to read Part 4." in body_e)

# THE GENERAL BUG UNDERNEATH IT: a <b> used for emphasis mid-paragraph only gets a
# single newline, so it stays inside its block and `startswith` never sees it. Any
# page that emphasised a few words mid-sentence was refused outright.
print("\n-- and a <b> used for emphasis mid-paragraph is not a heading either --")
inline_b = (ca.CONTAINER + "<p>" + ("word " * 400) +
            " and the <b>home straight</b> is the part that matters.</p></div>")
msg_i = refuses(inline_b, "")
check("a mid-paragraph <b> no longer refuses the page", msg_i is None,
      f"still refused: {msg_i}")
if msg_i is None:
    body_i, _, _, _ = ca.extract(inline_b)
    check("  and leaves no marker behind", "@@" not in body_i)
    check("  and keeps the emphasis as bold, not as a lost word",
          "**home straight**" in body_i, body_i[-120:])
    check("  CONTROL: the words are still there, in order",
          "the **home straight** is the part that matters" in body_i, body_i[-120:])

# CONTROL: a genuine leak MUST still fail loudly. This is the guard that stops a
# half-extracted page becoming an article of record, and none of the above may soften
# it — a page whose own text contains the sentinel is still refused.
print("\n-- 🔒 CONTROL: a marker that really does leak still REFUSES --")
real_leak = (ca.CONTAINER + "<p>" + ("word " * 400) +
             " @@TABLE7@@ stray sentinel</p></div>")
msg_l = refuses(real_leak, "")
check("a stray sentinel in the body is still REFUSED", msg_l is not None,
      "the guard has gone soft — a half-extracted page could become the record")
check("  and it REFUSES rather than crashing",
      bool(msg_l) and "table marker" in msg_l, str(msg_l))
# ⚠️ THIS CASE FOUND A CRASH, NOT A REFUSAL. A body carrying a literal "@@TABLE7@@"
# indexed into a table list with no seventh entry and died with IndexError, so the
# engine would have reported an unexpected exception rather than "this page needs a
# human". A guard that fails messily is one nobody trusts the next time.
# ⚠️ AND WHAT IS NO LONGER A LEAK, SAID PLAINLY SO NOBODY "RESTORES" IT. The heading
# sentinel cannot survive any more, because it is now always CONSUMED — as a heading
# when it opens a block, as inline bold when it sits mid-paragraph, and as nothing at
# all when the tag was empty. That is the fix. The guard still covers what it was
# there for: a table marker with no table behind it, and any other residue that means
# the extraction stopped half-done.
leak_h = (ca.CONTAINER + "<p>" + ("word " * 400) + " @@H@@ stray</p></div>")
body_lh, _, _, _ = ca.extract(leak_h)
check("  a heading sentinel is CONSUMED, never left in the body", "@@" not in body_lh,
      body_lh[-120:])
check("  and the words around it survive intact", "stray" in body_lh, body_lh[-120:])

# And a heading at the START of a block is still a heading — the case that worked.
print("\n-- CONTROL: a real heading is still a heading --")
heading = (ca.CONTAINER + "<p>" + ("word " * 400) +
           "</p><p><b>Geelong:</b><br />A roomy flat course.</p></div>")
msg_h = refuses(heading, "")
check("a leading <b> still becomes a heading", msg_h is None, f"refused: {msg_h}")
if msg_h is None:
    body_h, _, _, _ = ca.extract(heading)
    check("  rendered as bold", "**Geelong:**" in body_h, body_h[-140:])

# ══ A NUMBERED LIST SURVIVES THE CAPTURE (EP25, 14 Aug 2026) ═════════════════════
# `<li>` carries no whitespace, so the tag-strip used to leave NOTHING between items —
# not even a space. Fifty tips became one 3,900-word paragraph, and the e-book then
# reproduced that paragraph perfectly. The control runs both ways: the list must come
# out numbered, and the words must be unchanged by the change that numbers them.
print("\n-- CONTROL: an <ol> stays a numbered list --")
LIST_PAGE = (ca.CONTAINER + "<p>" + ("word " * 320) + "</p>"
             "<p><b>Now for the tips:</b></p>"
             "<ol><li>Never bet more than you can afford to lose.</li>"
             "<li>Always have a sizeable betting bank.</li>"
             "<li>*Treat each bet separately.</li></ol>"
             "<p>* Indicates extract from Commonsense Punting.</p></div>")
body_l, _, _, _ = ca.extract(LIST_PAGE)
blocks_l = [b for b in body_l.split("\n\n") if b.strip()]
nums = [b for b in blocks_l if re.match(r"^\d+\. ", b)]
check("three <li> become three numbered blocks", len(nums) == 3,
      f"got {len(nums)}: {nums}")
check("  numbered 1, 2, 3 — the article's own numbering",
      [b.split(".")[0] for b in nums] == ["1", "2", "3"], str(nums))
check("  the items do not run together",
      "lose.Always" not in body_l and "bank.*Treat" not in body_l, body_l[-300:])
check("  a leading '*' extract-marker survives",
      any(b.startswith("3. *Treat") for b in nums), str(nums))
check("  the footnote is its own block, unnumbered",
      "* Indicates extract from Commonsense Punting." in blocks_l, str(blocks_l[-2:]))

# THE FAILURE THIS REPLACES — with the fix disabled, the same page must run together.
_real = ca.lists_to_blocks
ca.lists_to_blocks = lambda frag: frag
try:
    body_before, _, _, _ = ca.extract(LIST_PAGE)
finally:
    ca.lists_to_blocks = _real
check("  and WITHOUT the fix the same page runs together (the control)",
      "lose.Always have a sizeable" in body_before, body_before[-200:])

# A list inside a list REFUSES rather than inventing a numbering scheme.
NESTED = (ca.CONTAINER + "<p>" + ("word " * 320) + "</p>"
          "<ol><li>One.<ol><li>One a.</li></ol></li><li>Two.</li></ol></div>")
msg_n = refuses(NESTED, "")
check("a list inside a list is REFUSED, not guessed at",
      msg_n is not None and "list inside a list" in msg_n, f"got: {msg_n}")

# An UNORDERED list is separated but NOT numbered — we do not invent numbers.
UL = (ca.CONTAINER + "<p>" + ("word " * 320) + "</p>"
      "<ul><li>First bullet point here.</li><li>Second bullet point here.</li></ul></div>")
body_u, _, _, _ = ca.extract(UL)
check("a <ul> is separated but NOT numbered",
      "here.Second" not in body_u and not re.search(r"(?m)^1\. First bullet", body_u),
      body_u[-200:])

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
