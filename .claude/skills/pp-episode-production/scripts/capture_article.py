"""Turn a Practical Punting URL into the episode's CAPTURE — the article of record.

    python capture_article.py <url> <ep_number> [--pp DIR] [--write]

Report-only by default; --write places PP Videos/docs/EPnn-source-article-<slug>.md.

🔴 WHAT THIS FILE BECOMES, AND WHY IT REFUSES RATHER THAN GUESSES.
The capture is what `script_fidelity`, `check_trace` and the e-book body are compared
against for the life of the episode. A capture that is subtly wrong does not fail — it
quietly redefines the truth, and every downstream check then agrees with it. So this
tool RECOGNISES a page or it HALTS. It never produces a best-effort article of record.

THE FIVE THINGS A NAIVE FETCH GETS WRONG (the first four found building EP19's by hand):
  1. paragraphs are `<br /><br />`, NOT `<p>` — strip the tags and the whole article
     runs into one block ("everything!As far as systems go")
  2. sub-headings are inline `<b>THE 10K SYSTEM</b>` and glue to the next sentence
  3. a real `<table>` must stay a table. Flattened it reads "Last start2nd-last
     start3rd-last startWin 9 pts…" and the figures stop tracing (the EP16 lesson)
  4. the article ends at the byline; after it is the site — Recommended Article,
     Sign up for Free Tips, Next To Jump, Buy Tips
  5. 🔴 A REAL `<ol>` MUST STAY A NUMBERED LIST. (EP25, 14 Aug 2026.) Fault 1 in its
     purest form, and it got past this file because `<li>` is not `<br>` and not `<p>`:
     the tag-strip removed it leaving NOTHING between the items, not even a space, so
     "…rather than one horse each-way." ran straight into "If you insist on backing…".
     **EP25's article is an `<ol>` of exactly 50 `<li>` and the capture made it ONE
     PARAGRAPH of 3,900 words.** The e-book then reproduced that paragraph faithfully —
     the fidelity gate was satisfied, because the gate compares the body to the CAPTURE
     and the capture was already wrong. A whole list lost its structure and every check
     downstream agreed with the loss.
     ⚠️ THE TELL, worth more than the fix: sentences that abut with NO SPACE. A `<br>`
     or a `<p>` at least leaves whitespace behind; a stripped `<li>` leaves nothing, so
     the damage reads as a typo rather than as a missing structure.

🔒 THE HEADLINE GOES INSIDE THE MARKERS. (Jodie, 9 Aug 2026, from EP19.)
An episode's own title is the article's own words, printed on the page, and usually the
most quotable line in it. EP19 is "10 SYSTEMS FOR ACTION-HUNGRY PUNTERS (Part 1)", the
writer naturally said "ten systems", and the fidelity gate rejected the draft TWICE —
correctly by its own lights, because the headline sat in this header, outside the
markers, where nothing downstream can see it.
    ONLY THE TITLE CROSSES. Everything else here — encoding, repairs, where the article
    ends — is a note ABOUT the article, not the article, and must never reach the script,
    the gate or the e-book. EP18 shipped an e-book with a transcription note on page two
    for exactly this blur.

AND THE EP17 RULING: a `?` glued to the FRONT of a word mid-sentence is scan noise and
is repaired HERE, at the capture, because the fidelity gate compares against this file.
A `?` that ENDS a sentence is the author's and survives untouched. Every repair is
listed in the header, so the edit is visible rather than silent.
"""
import argparse
import datetime as dt
import html as H
import pathlib
import re
import sys
import urllib.request

CONTAINER = '<div class="well-content"><div class="text">'
# 🔴 THE TWO DIVS ARE NO LONGER ADJACENT, AND THE LITERAL BROKE ON EVERY RECENT PAGE.
# (10 Aug 2026.) PP now embeds the finished YouTube episode on its own article page —
# EP19's page carries an <iframe> for M6irQAag7uU, the video this studio published —
# so `<div class="well-content"><div class="text">` stopped matching and the tool
# refused EP17, EP18 and EP19 outright. Nothing about the article changed; something
# was added ABOVE it, which is exactly what a page is allowed to do.
#     So the container is matched STRUCTURALLY: the first `.text` inside
# `.well-content`, whatever sits between them. A literal that assumes two tags touch is
# a literal that breaks the first time anyone edits the page.
CONTAINER_RE = re.compile(
    r'<div class="well-content"[^>]*>.*?<div class="text"[^>]*>', re.S | re.I)


def find_container(page):
    """(end_of_opening_tags, start_of_container) or (None, None)."""
    m = CONTAINER_RE.search(page)
    return (m.end(), m.start()) if m else (None, None)
FURNITURE = ("Recommended Article", "Sign up for Free Tips", "Next To Jump",
             "Buy Tips", "Insights into national thoroughbred racing")
MIN_WORDS = 300


class Unrecognised(Exception):
    """The page is not one we know how to read. Nothing is written."""


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PP capture)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        ctype = r.headers.get("Content-Type", "")
    try:
        raw.decode("utf-8")
        clean = True
    except UnicodeDecodeError:
        clean = False
    return raw, raw.decode("utf-8", "replace"), ctype, clean


def table_to_md(tbl_html):
    rows = []
    for r in re.findall(r"<tr.*?</tr>", tbl_html, re.S | re.I):
        cells = [re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh].*?</t[dh]>", r, re.S | re.I)]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return ("| " + " | ".join(rows[0]) + " |\n|" + "|".join(["---"] * width) + "|\n"
            + "\n".join("| " + " | ".join(r) + " |" for r in rows[1:]))


_LIST = re.compile(r"<(ol|ul)\b([^>]*)>(.*?)</\1\s*>", re.S | re.I)


def lists_to_blocks(frag):
    """Turn `<ol>`/`<ul>` into ONE BLOCK PER ITEM, numbered when the list is ordered.

    An ordered list becomes markdown's own numbered list — `1. …` through `50. …`, one
    per blank-line-separated block — so `article_paragraphs()` sees fifty paragraphs
    where it used to see one, and the e-book body can reproduce them as fifty `<li>`.
    An UNORDERED list becomes one block per item with no marker: the run-on is the bug,
    and a bullet the article does not number is not something to invent a number for.

    THE NUMBER IS THE ARTICLE'S OWN MARKUP, exactly as `**BOLD**` is for a heading —
    `<ol>` numbers its items whether or not the digits appear in the HTML, so writing
    them down is reproducing the page, not adding to it. `start=` is honoured because a
    list that begins at 7 says 7 on the page.

    NESTING REFUSES rather than guesses. A list inside a list has a numbering scheme
    (1/a/i, or restart-at-1) that this cannot know from the markup alone, and inventing
    one would put a wrong number in the article of record — the one thing this file
    exists to prevent.
    """
    def one(m):
        kind, attrs, inner = m.group(1).lower(), m.group(2) or "", m.group(3)
        if re.search(r"<(ol|ul)\b", inner, re.I):
            raise Unrecognised(
                "this article contains a list inside a list. How the inner one is "
                "numbered (1/a/i, or restarting at 1) is not something the markup "
                "settles, and guessing would put a number in the article of record "
                "that the page does not print. Capture this one by hand.")
        items = [i for i in re.split(r"<li\b[^>]*>", inner)[1:]]
        if not items:
            return "\n\n"
        n = 1
        sm = re.search(r'start\s*=\s*["\']?(\d+)', attrs, re.I)
        if sm:
            n = int(sm.group(1))
        out = []
        for raw in items:
            text = re.sub(r"</li\s*>.*", "", raw, flags=re.S | re.I)
            if not re.sub(r"<[^>]+>", "", text).strip():
                continue                      # an empty <li> is furniture, not an item
            out.append((f"{n}. " if kind == "ol" else "") + text.strip())
            n += 1
        return "\n\n" + "\n\n".join(out) + "\n\n"

    return _LIST.sub(one, frag)


def _container_end(frag):
    """Offset of the `</div>` that closes the article container, or None.

    DEPTH-COUNTED, because the article contains divs of its own and the FIRST `</div>`
    would cut it off mid-sentence. `frag` starts immediately after the opening
    `.well-content > .text`, so depth begins at 1.
    """
    depth = 1
    for m in re.finditer(r"<div\b|</div\s*>", frag, re.I):
        depth += 1 if m.group(0).lower().startswith("<div") else -1
        if depth == 0:
            return m.start()
    return None


def extract(page):
    """(body_markdown, byline, tables, repairs) or raise Unrecognised."""
    start, _ = find_container(page)
    if start is None:
        raise Unrecognised(
            "the article container (a `.text` div inside `.well-content`) is not on this "
            "page. Every PP article captured so far uses it; this page is built "
            "differently, and guessing which part of it is the article would put an "
            "invented article of record under the whole episode.")
    frag = page[start:]

    # ── WHERE THE ARTICLE ENDS ────────────────────────────────────────────────
    #
    # 🔴 THE BOUND IS THE CONTAINER'S OWN CLOSING TAG, not the byline. (EP20, 10 Aug
    # 2026.) It used to REQUIRE a `By <Name>` byline and refuse the page without one:
    #
    #     "no byline of the form 'By <Name>' was found, so there is no reliable mark
    #      for where the article ENDS."
    #
    # That is true of the a-z-of-betting features, which all sign off "By Mr Money".
    # It is NOT true of the professional-punters pieces — the Bill Benter article
    # carries no byline at all — and EP20 sat refused on every kick-on-submit tick.
    #
    # The container already says where the article ends: `.well-content > .text` is the
    # article, and everything after its closing </div> is the site. Counting to that
    # close is STRUCTURAL — it does not depend on the author having signed their name,
    # and it is the same answer the byline gave on the pages that have one.
    #
    # THE BYLINE STAYS, as an EARLIER cut and as provenance. On an a-z page the sign-off
    # sits inside the container, so cutting at the byline is still right and still what
    # happens — this only changes what occurs when there ISN'T one. A page with no
    # byline gets `byline = None`, and the capture says so plainly rather than inventing
    # an author: the article of record must never claim a name the page does not give.
    end = _container_end(frag)
    if end is None:
        raise Unrecognised(
            "the article container never closes on this page, so there is no reliable "
            "mark for where the article ENDS. Everything after the container is the "
            "site's own furniture, and including it would put 'Next To Jump' inside the "
            "article of record.")
    frag = frag[:end]

    m = re.search(r"By\s+([A-Z][A-Za-z.'\- ]{2,40})\s*<", frag)
    byline = m.group(1).strip() if m else None
    if m:
        frag = frag[:m.start()]

    # LISTS BEFORE ANYTHING ELSE TOUCHES THE TAGS. `<li>` carries no whitespace of its
    # own, so once the strip below has run there is nothing left to tell one item from
    # the next — see fault 5 in the header. Done here, each item is already its own
    # block by the time the `<br>` and `<p>` rules run, and they leave it alone.
    frag = lists_to_blocks(frag)

    tables = re.findall(r"<table.*?</table>", frag, re.S | re.I)
    for i, t in enumerate(tables):
        frag = frag.replace(t, f"\n@@TABLE{i}@@\n")
    # 🔴 AN EMPTY <b></b> IS NOT A HEADING (EP23, Track Secrets Part 3, 12 Aug 2026).
    # The cross-links at the foot of a multi-part feature read "Click here to read
    # Part 1 … Part 2 … Part 4" — and the part you are ON is bolded with NO link, so
    # the page emits a literal `<b></b>`. That produced a heading marker with nothing
    # in it, which then survived into the body and refused the whole article. The
    # refusal was right and the marker was the studio's own; a bold tag with nothing
    # inside it is not a heading and should never have made one.
    frag = re.sub(r"<b>\s*(.*?)\s*</b>",
                  lambda x: f"\n@@H@@{x.group(1)}\n" if x.group(1).strip() else "",
                  frag, flags=re.S | re.I)
    frag = re.sub(r"(?:<br\s*/?>\s*){2,}", "\n\n", frag, flags=re.I)
    frag = re.sub(r"<br\s*/?>", "\n", frag, flags=re.I)
    frag = re.sub(r"</p>|<p[^>]*>", "\n\n", frag, flags=re.I)
    text = H.unescape(re.sub(r"<[^>]+>", "", frag)).replace("\u00a0", " ")

    blocks = []
    for b in re.split(r"\n\s*\n", text):
        b = re.sub(r"[ \t]+", " ", b).strip()
        if not b:
            continue
        tm = re.search(r"@@TABLE(\d+)@@", b)
        if tm and int(tm.group(1)) >= len(tables):
            # 🔴 THE PAGE'S OWN TEXT CONTAINED SOMETHING SHAPED LIKE OUR SENTINEL.
            # Found by the control for EP23's marker fix: a body carrying a literal
            # "@@TABLE7@@" indexed straight into a table list that has no seventh
            # entry and died with IndexError — a CRASH, not a refusal, so the engine
            # would report an unexpected exception instead of "this page needs a
            # human". A guard that fails messily is one nobody trusts the next time.
            raise Unrecognised(
                f"the article text contains something shaped like this reader's own "
                f"table marker ({tm.group(0)}) and there is no such table on the page. "
                f"Either the extraction did not complete or the page really does say "
                f"that, and neither is safe to guess at.")
        if tm:
            before, after = b.split(tm.group(0), 1)
            if before.strip():
                blocks.append(re.sub(r"\s*\n\s*", " ", before).strip())
            blocks.append(table_to_md(tables[int(tm.group(1))]))
            if after.strip():
                blocks.append(re.sub(r"\s*\n\s*", " ", after).strip())
        elif b.startswith("@@H@@") and "@@H@@" not in b[5:]:
            blocks.append(f"**{b[5:].strip()}**")
        else:
            # ⚠️ A <b> USED FOR EMPHASIS INSIDE A PARAGRAPH IS NOT A HEADING EITHER,
            # and until now it leaked. The marker only becomes its own block when a
            # BLANK line follows the bold run; a bold phrase mid-sentence gets a single
            # newline, stays inside its paragraph, and `startswith` never sees it. So
            # any page that emphasises a few words mid-paragraph was refused outright.
            # The marker runs to the newline the substitution put after it, so it has
            # to be converted HERE, before the newlines are collapsed to spaces.
            b = re.sub(r"@@H@@([^\n]*)",
                       lambda m: f"**{m.group(1).strip()}**" if m.group(1).strip()
                       else "", b)
            blocks.append(re.sub(r"\s*\n\s*", " ", b).strip())
    body = "\n\n".join(blocks)

    # EP17 ruling — repair the glued '?', list every one, leave real ones alone.
    repairs = re.findall(r"\?([A-Za-z]\w*)", body)
    body = re.sub(r"\?([A-Za-z])", r"\1", body)

    words = len(body.split())
    if words < MIN_WORDS:
        raise Unrecognised(
            f"only {words} words came out of the article container, and a PP feature is "
            f"never that short. The page is laid out in a way this reader does not "
            "understand, and a truncated article of record is worse than none.")
    leaked = [f for f in FURNITURE if f in body]
    if leaked:
        raise Unrecognised(
            f"site furniture reached the article text — {leaked}. The bound did not hold "
            "on this page, so the boundary between the author and the site is not where "
            "this reader thinks it is. (The bound is the container's closing tag, and "
            "the byline when the page carries one — this page's article runs past both.)")
    if "@@" in body:
        raise Unrecognised("an internal marker survived into the body; the extraction "
                           "did not complete cleanly.")
    damage = scan_damage(body)
    if damage:
        bits = "; ".join(f"{toks} — {why}" for toks, why in damage)
        raise Unrecognised(
            f"this page carries OCR damage: {bits}.\n"
            "The capture becomes the article of record, and repairing scan damage is a "
            "judgement (§0a category 2) — guessing what a mangled token was meant to say "
            "would be WRITING the article, not capturing it. EP16 was proof-read by hand "
            "for exactly this. Capture this one by hand, or fix the source page.")
    return body, byline, tables, repairs


def scan_damage(body):
    """Marks of OCR damage — precise signals only, and finding one REFUSES the page.

    🔴 THE CONTROL PROOF FOUND THIS, and it is the boundary of what a tool may do.
    Re-capturing EP16 matched its file everywhere except TWELVE places, and every one
    is a human repairing the live page: it reads `l/s` for `1/5`, `Vs` for `3/5`, and
    `5-1 *` for `5-1;`. Someone proof-read that article when it was captured.

        THE TOOL CANNOT INVENT THOSE REPAIRS AND MUST NOT TRY. Guessing what a mangled
        token was meant to say is writing the article, not capturing it.

    ⚠️ AND IT CANNOT SEE ALL OF THEM. `Vs` is indistinguishable from a word by any rule
    this file can carry honestly; only `l/s` and the stray `*` have shapes that never
    occur in real prose. A DETECTOR THAT CATCHES SOME DAMAGE IS NOT A LICENCE TO PLACE
    THE REST — so what it catches, it refuses on, and a page that trips it goes to a
    human. The first version of this scored short mixed-case tokens and flagged "The",
    "You" and "If" on a perfectly clean article: a warning that is wrong half the time
    trains people to stop reading warnings (Jodie, 6 Aug).
    """
    hits = []
    for pat, why in (
        (r"\b[A-Za-z]/[A-Za-z]\b", "a fraction whose digits have been read as letters "
                                   "(EP16's live page has `l/s` where the article says `1/5`)"),
        (r"(?<=\d)\s\*(?=\s)", "a stray `*` standing where punctuation was "
                               "(EP16: `5-1 *` for `5-1;`)"),
        (r"\b[A-Za-z]\d{2,}\b", "a letter fused to a number"),
    ):
        found = re.findall(pat, body)
        if found:
            hits.append((sorted(set(found))[:6], why))
    return hits


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return re.sub(r"-+", "-", s)[:70]


def build(url, ep_number, pp: pathlib.Path, write=False):
    raw, page, ctype, clean = fetch(url)
    print(f"{len(raw):,} bytes off the wire, Content-Type: {ctype}")
    print(f"utf-8 decodes without error: {clean}")
    if not clean:
        raise Unrecognised("the page is not clean UTF-8. Every capture so far has been, "
                           "and a mojibake article of record is unfixable downstream.")

    t = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    full_title = H.unescape(re.sub(r"\s+", " ", t.group(1))).strip() if t else ""
    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", page, re.S | re.I)
    head_txt = H.unescape(re.sub(r"<[^>]+>", "", h1[0])).strip() if h1 else full_title

    body, byline, tables, repairs = extract(page)

    # headline vs standfirst: the <h1> runs them together, the shouted part is the head
    # The <h1> runs the standfirst and the headline together. The headline is the
    # SHOUTED run at the end — plus an optional "(Part n)", whose lowercase letters
    # would otherwise end the all-caps run and swallow the standfirst into the title.
    # EP19 ("…then take care10 SYSTEMS FOR ACTION-HUNGRY PUNTERS (Part 1)") is exactly
    # that case, and it matters now the headline is traceable article text.
    mm = re.search(r"(.*?)([A-Z0-9][A-Z0-9 '’\-&!?,\.]{9,}(?:\s*\(Part\s*\d+\))?)\s*$",
                   head_txt)
    standfirst = (mm.group(1).strip() if mm else "").strip()
    headline = (mm.group(2).strip() if mm else head_txt).strip()

    # 🔴 THE MASTHEAD IS ALL CAPS, AND `re.I` MADE IT SWALLOW PROSE. EP19's footer is
    # "PRACTICAL PUNTING - MAY 2004"; the Benter page has no footer at all, and with
    # re.I this matched the body sentence "Practical Punting writer counted 660
    # Australian horse rac…" and printed it as the dateline. A capture that states a
    # false provenance line is the same class of fault as a capture with furniture in
    # it — episode.json's `source` quotes this.
    #     It must also carry a DATE. A masthead without one is not a dateline, and
    #     "" is the honest answer for a page that does not give one.
    _, cstart = find_container(page)
    foot = re.search(r"(PRACTICAL PUNTING[^<]{0,40})", page[cstart:])
    dateline = re.sub(r"\s+", " ", foot.group(1)).strip() if foot else ""
    if dateline and not re.search(r"\d{4}", dateline):
        dateline = ""

    print(f"\nheadline   : {headline!r}")
    print(f"standfirst : {standfirst!r}")
    print(f"byline     : {byline!r}")
    print(f"dateline   : {dateline!r}")
    print(f"body       : {len(body.split()):,} words, {len(body):,} chars")
    print(f"tables kept: {len(tables)}")
    print(f"rogue '?' repaired: {len(repairs)} {repairs[:6]}")

    # THE PAGE'S OWN AUTHORSHIP, STATED HONESTLY. A professional-punters piece carries
    # no byline; the article of record must never claim a name the page does not give,
    # because episode.json's `source` quotes this line as provenance.
    by_line = (f"By {byline} — {dateline}" if byline
               else f"{dateline}" if dateline
               else "")
    by_note = (f'cut at the byline **"By {byline}"**' if byline
               else "bounded by the article container's own closing tag — **this page "
                    "carries no byline**, which is normal for the professional-punters "
                    "pieces and is why the bound is structural rather than textual")
    author_note = (f"**Author: {byline}**, named in the article's own byline."
                   if byline else
                   "**No author is named on this page.** The professional-punters pieces "
                   "are unsigned; nothing here invents one, and episode.json must not "
                   "either.")

    rep = ("**Zero rogue `?` on this page** — checked, not assumed."
           if not repairs else
           f"**{len(repairs)} rogue `?` glued to the front of a word were REPAIRED here, "
           f"at the capture, under the EP17 ruling** (the fidelity gate compares against "
           f"this file, so repairing it downstream would break the comparison). The words "
           f"affected: {', '.join(sorted(set(repairs))[:12])}. **A `?` that ENDS a "
           f"sentence is the author's and is untouched.**")
    tbl = ("**No `<table>` in the article body.**" if not tables else
           f"**{len(tables)} real `<table>` in the article body, kept AS tables.** "
           "Flattened they read as unreadable prose and the figures stop tracing "
           "(the EP16 lesson).")
    # THE LIST, RECORDED AS PROVENANCE. A downstream reader has to be able to tell a
    # numbered list from prose that happens to start with a digit, and the e-book gate
    # counts these items — so the count is written down where a human can check it
    # against the page rather than inferred from the markers alone.
    n_items = len(re.findall(r"(?m)^\d+\. ", body))
    lst = ("**No numbered list in the article body.**" if not n_items else
           f"**The article body is a NUMBERED LIST of {n_items} items, and it is kept "
           f"as one** — written below as `1.` … `{n_items}.`, one paragraph per item, "
           f"which is the article's own numbering. `<li>` carries no whitespace, so a "
           f"plain tag-strip runs every item into its neighbour with not even a space "
           f"between them (the EP25 lesson). The e-book reproduces this as an `<ol>` "
           f"of {n_items} `<li>` and `author_ebook.py` refuses a body that does not.")

    # An empty standfirst rendered as a bare `****`. Not every page has one, and a
    # header full of empty markup is a header nobody reads.
    stand_line = f"**{standfirst}**\n" if standfirst else ""

    text = f"""# {headline}

{stand_line}{by_line}

Source: {url}
Captured {dt.date.today().strftime('%-d %B %Y') if sys.platform != 'win32' else dt.date.today().strftime('%d %B %Y').lstrip('0')} by `capture_article.py`.

---

## THE ENCODING — CHECKED, AND THE PAGE IS CLEAN

**{len(raw):,} bytes off the wire, `{ctype}`, and `bytes.decode("utf-8")` succeeds
without error.** Verified against the raw bytes, not through a reader.

## THE ROGUE `?`

{rep}

## TABLES AND IMAGES

{tbl}

## LISTS

{lst}

## WHERE THE ARTICLE ENDS

The body is {by_note}. Everything after it on these pages is
the site — Recommended Article, Sign up for Free Tips, Next To Jump, Buy Tips — and the
capture refuses to place itself if any of that reaches the article text.

📌 Paragraph breaks are `<br /><br />` in the source, sub-headings are inline `<b>`, and
list items are `<li>`; all three are restored here. A plain tag-strip runs the whole
article into one block.

---

---- ARTICLE TEXT BEGINS ----

{headline}

{body}

---- ARTICLE TEXT ENDS ----

By {byline}

{dateline}
"""
    dest = pp / "docs" / f"EP{int(ep_number):02d}-source-article-{slug(headline)}.md"
    if write:
        if dest.exists():
            print(f"\n🚫 {dest.name} exists — refusing to overwrite the article of record.")
            return dest, text
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")
        print(f"\nWROTE {dest}")
    else:
        print(f"\nwould write {dest.name} (report only; pass --write)")
    return dest, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=r"G:\My Drive\PP Videos")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    try:
        build(a.url, a.ep_number, pathlib.Path(a.pp), a.write)
    except Unrecognised as e:
        print(f"\n🚫 CAPTURE REFUSED — {e}\n\nNothing has been written. This page needs a "
              "human to look at it; an article of record is not something to guess at.",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
