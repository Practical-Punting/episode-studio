"""Print the FULL on-card text of both bespoke pages, and check it against the source.

Bespoke pages skip author_cards.py entirely — no trace gate, no invented-text gate. This
is the substitute: every visible string is pulled out of the rendered page and compared
to the capture, so a human can read the two side by side.
"""
import html as H
import pathlib
import re
import sys

SK = r"C:\Users\jlral\repos\episode-studio\.claude\skills\pp-episode-production\scripts"
sys.path.insert(0, SK)
import author_ebook as ae                                          # noqa: E402

EXPORT = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP27\overlay\export")
CAP = r"G:\My Drive\PP Videos\docs\EP27-source-article-bet-your-own-prices-part-1.md"

blocks = ae.article_blocks(CAP)
table = [b for b in blocks if ae.MD_TABLE.match(re.sub(r"\s+", " ", b))][0]
rows = ae._md_table_rows(table)
PCT = {r[1]: r[2] for r in rows[1:] if len(r) == 3}
ITEMS = {}
for b in blocks:
    n, w = ae.split_number(re.sub(r"\s+", " ", b))
    if n is not None:
        ITEMS[n] = w


def visible(pathname):
    doc = pathlib.Path(EXPORT / pathname).read_text(encoding="utf-8")
    body = doc.split("<body>")[1].split("<script>")[0]
    body = re.sub(r"<br\s*/?>", " ", body)
    out = []
    for m in re.finditer(r">([^<>]+)<", body):
        t = H.unescape(m.group(1)).strip()
        if t:
            out.append(t)
    return out


print("=" * 78)
print("C15 — ep27-c15-the-bookies-percentages.html — FULL ON-CARD TEXT")
print("=" * 78)
v = visible("ep27-c15-the-bookies-percentages.html")
for t in v:
    print(f"   {t}")

print("\nC15 CELL CHECK — what is ON THE CARD vs what the CAPTURE says")
print(f"   {'price':<9}{'on card':<11}{'capture':<11}match")
pairs, bad = [], []
for i in range(1, len(v)):
    # A column renders as [percentage][price], in that order, so the price's own
    # percentage is the string IMMEDIATELY before it. (The first version reached back
    # two and reported seven mismatches against a card that was right — the checker was
    # wrong, not the card, and it said so in a way that looked like data corruption.)
    if v[i] in PCT:
        pairs.append((v[i], v[i - 1]))
for price, shown in pairs:
    ok = shown == PCT[price]
    if not ok:
        bad.append(price)
    print(f"   {price:<9}{shown:<11}{PCT[price]:<11}{'OK' if ok else 'MISMATCH'}")
print(f"   -> {len(pairs)} cells, {'ALL MATCH THE CAPTURE' if not bad else 'MISMATCH: ' + str(bad)}")
foot = [t for t in v if t.startswith("34 prices")]
print(f"   footer: {foot[0]!r}  (table has {len(rows) - 1} data rows)"
      if foot else "   footer MISSING")

print("\n" + "=" * 78)
print("C17 — ep27-c17-the-ten-questions.html — FULL ON-CARD TEXT")
print("=" * 78)
v17 = visible("ep27-c17-the-ten-questions.html")
for t in v17:
    print(f"   {t}")

print("\nC17 ITEM CHECK — verbatim against the capture's numbered list")
bad17 = []
for n in range(1, 11):
    on = [v17[i + 1] for i in range(len(v17) - 1) if v17[i] == str(n)]
    hit = ITEMS[n] in on
    if not hit:
        bad17.append(n)
    print(f"   {n:>2}. {'OK  ' if hit else 'MISS'} {ITEMS[n]}")
print(f"   -> 10 items, {'ALL VERBATIM' if not bad17 else 'MISMATCH: ' + str(bad17)}")
sys.exit(1 if (bad or bad17) else 0)
