"""Turn a Practical Punting URL into the episode's CAPTURE — the article of record.

    python capture_article.py <url> <ep_number> [--pp DIR] [--write]

Report-only by default; --write places PP Videos/docs/EPnn-source-article-<slug>.md.

🔴 WHAT THIS FILE BECOMES, AND WHY IT REFUSES RATHER THAN GUESSES.
The capture is what `script_fidelity`, `check_trace` and the e-book body are compared
against for the life of the episode. A capture that is subtly wrong does not fail — it
quietly redefines the truth, and every downstream check then agrees with it. So this
tool RECOGNISES a page or it HALTS. It never produces a best-effort article of record.

THE FOUR THINGS A NAIVE FETCH GETS WRONG (all found building EP19's by hand):
  1. paragraphs are `<br /><br />`, NOT `<p>` — strip the tags and the whole article
     runs into one block ("everything!As far as systems go")
  2. sub-headings are inline `<b>THE 10K SYSTEM</b>` and glue to the next sentence
  3. a real `<table>` must stay a table. Flattened it reads "Last start2nd-last
     start3rd-last startWin 9 pts…" and the figures stop tracing (the EP16 lesson)
  4. the article ends at the byline; after it is the site — Recommended Article,
     Sign up for Free Tips, Next To Jump, Buy Tips

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


def extract(page):
    """(body_markdown, byline, tables, repairs) or raise Unrecognised."""
    if CONTAINER not in page:
        raise Unrecognised(
            f"the article container {CONTAINER!r} is not on this page. Every PP article "
            "captured so far uses it; this page is built differently, and guessing which "
            "part of it is the article would put an invented article of record under the "
            "whole episode.")
    frag = page[page.index(CONTAINER):]

    m = re.search(r"By\s+([A-Z][A-Za-z.'\- ]{2,40})\s*<", frag)
    if not m:
        raise Unrecognised(
            "no byline of the form 'By <Name>' was found, so there is no reliable mark "
            "for where the article ENDS. Everything after the byline on these pages is "
            "the site's own furniture, and including it would put 'Next To Jump' inside "
            "the article of record.")
    byline = m.group(1).strip()
    frag = frag[:m.start()]

    tables = re.findall(r"<table.*?</table>", frag, re.S | re.I)
    for i, t in enumerate(tables):
        frag = frag.replace(t, f"\n@@TABLE{i}@@\n")
    frag = re.sub(r"<b>\s*(.*?)\s*</b>", lambda x: f"\n@@H@@{x.group(1)}\n",
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
        if tm:
            before, after = b.split(tm.group(0), 1)
            if before.strip():
                blocks.append(re.sub(r"\s*\n\s*", " ", before).strip())
            blocks.append(table_to_md(tables[int(tm.group(1))]))
            if after.strip():
                blocks.append(re.sub(r"\s*\n\s*", " ", after).strip())
        elif b.startswith("@@H@@"):
            blocks.append(f"**{b[5:].strip()}**")
        else:
            blocks.append(re.sub(r"\s*\n\s*", " ", b))
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
            f"site furniture reached the article text — {leaked}. The byline cut did not "
            "hold on this page, so the boundary between the author and the site is not "
            "where this reader thinks it is.")
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

    foot = re.search(r"(PRACTICAL PUNTING[^<]{0,40})", page[page.index(CONTAINER):], re.I)
    dateline = re.sub(r"\s+", " ", foot.group(1)).strip() if foot else ""

    print(f"\nheadline   : {headline!r}")
    print(f"standfirst : {standfirst!r}")
    print(f"byline     : {byline!r}")
    print(f"dateline   : {dateline!r}")
    print(f"body       : {len(body.split()):,} words, {len(body):,} chars")
    print(f"tables kept: {len(tables)}")
    print(f"rogue '?' repaired: {len(repairs)} {repairs[:6]}")

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

    text = f"""# {headline}

**{standfirst}**
By {byline} — {dateline}

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

## WHERE THE ARTICLE ENDS

The body is cut at the byline **"By {byline}"**. Everything after it on these pages is
the site — Recommended Article, Sign up for Free Tips, Next To Jump, Buy Tips — and the
capture refuses to place itself if any of that reaches the article text.

📌 Paragraph breaks are `<br /><br />` in the source and sub-headings are inline `<b>`;
both are restored here. A plain tag-strip runs the whole article into one block.

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
