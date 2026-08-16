"""Author EP27's two BESPOKE cards — C15 and C17 — from the CAPTURE, not from memory.

🔴 WHY THIS IS A SCRIPT AND NOT HAND-TYPED HTML. `author_cards.py` skips a bespoke card
entirely: there is no trace gate and no invented-text gate behind either of these pages.
The only protection available is that every character of data comes out of the article of
record programmatically and is asserted against it before a file is written. That is
Jodie's ruling of 15 Aug 2026 — "a number is a READING, not a value" — and it binds here
even though it was written about the e-book, because the risk is identical and here there
is no gate at all.

If ANY lifted cell disagrees with the capture, this halts and writes nothing.
"""
import html as H
import json
import pathlib
import re
import sys

SK = r"C:\Users\jlral\repos\episode-studio\.claude\skills\pp-episode-production\scripts"
sys.path.insert(0, SK)
import author_ebook as ae                                          # noqa: E402

EPDIR = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP27")
CAP = pathlib.Path(
    r"G:\My Drive\PP Videos\docs\EP27-source-article-bet-your-own-prices-part-1.md")
OUT = EPDIR / "overlay/export"

# ── THE SOURCE, READ ONCE ───────────────────────────────────────────────────────
blocks = ae.article_blocks(str(CAP))
tables = [b for b in blocks if ae.MD_TABLE.match(re.sub(r"\s+", " ", b))]
assert len(tables) == 1, f"expected one table in the article, found {len(tables)}"
rows = ae._md_table_rows(tables[0])
header, data = rows[0], rows[1:]
assert header == ["ODDS ON", "PRICE", "ODDS AGAINST"], header

# price -> odds-against percentage, straight off the capture's own rows
PCT = {r[1]: r[2] for r in data if len(r) == 3}
assert len(PCT) == len(data), "duplicate price in the source table"

# ── C15: THE CONVERSION LADDER ──────────────────────────────────────────────────
# Jodie's design, 16 Aug 2026: seven anchor prices showing the SHAPE — short odds eat
# your book, long odds barely dent it. The full 34-row chart is in the guide, which the
# spoken line promises and the e-book chart slot delivers.
ANCHORS = ["Evens", "2-1", "4-1", "6-1", "10-1", "20-1", "100-1"]
EXPECT = {"Evens": "50.0", "2-1": "33.3", "4-1": "20.0", "6-1": "14.3",
          "10-1": "09.1", "20-1": "04.8", "100-1": "01.0"}

print("C15 — CELL-BY-CELL CHECK AGAINST THE CAPTURE")
print(f"  {'price':<8}{'briefed':<10}{'capture':<10}match")
bad = []
for a in ANCHORS:
    got = PCT.get(a)
    ok = got == EXPECT[a]
    print(f"  {a:<8}{EXPECT[a]:<10}{str(got):<10}{'OK' if ok else 'MISMATCH'}")
    if not ok:
        bad.append(f"{a}: brief says {EXPECT[a]!r}, capture says {got!r}")
if bad:
    sys.exit("HALTED — a cell does not match the source:\n  " + "\n  ".join(bad))
LADDER = [(a, PCT[a]) for a in ANCHORS]          # values are the CAPTURE's, not EXPECT's
print(f"  all {len(LADDER)} cells lifted from the capture, verified\n")

FOOTER = "34 prices in all — the full chart is in the guide."
assert len(data) == 34, f"footer says 34 prices; the table has {len(data)} rows"

# ── C17: THE TEN QUESTIONS ──────────────────────────────────────────────────────
items = []
for b in blocks:
    n, w = ae.split_number(re.sub(r"\s+", " ", b))
    if n is not None:
        items.append((n, w))
assert [n for n, _ in items] == list(range(1, 11)), [n for n, _ in items]
print(f"C17 — {len(items)} numbered items lifted verbatim from the capture\n")

# ── THE HOUSE FRAME ─────────────────────────────────────────────────────────────
FRAME = pathlib.Path(SK).parent / "assets/cards/frame-fullscreen.html"
frame = FRAME.read_text(encoding="utf-8")
MARK = ('<!-- PP-BESPOKE, hand-authored per episode.json block:"bespoke". The DATA in '
        'this page was lifted programmatically from {cap} and asserted against it — '
        'author_cards.py does not check a bespoke page, so nothing else will. -->')


def build(title, eyebrow, headline, css, markup, anim, logo_delay):
    p = frame
    p = p.replace("%%TITLE%%", title)
    p = p.replace("%%GENMARK%%", MARK.format(cap=CAP.name))
    p = p.replace("%%EYEBROW%%", eyebrow)
    p = p.replace("%%HEADLINE%%", headline)
    p = p.replace("%%BLOCK_CSS%%", css)
    p = p.replace("%%BLOCK_PRINT%%", "")
    p = p.replace("%%FIT_CSS%%", "")
    p = p.replace("%%BLOCK_MARKUP%%", markup)
    p = p.replace("%%BLOCK_ANIM%%", anim.rstrip(",\n"))
    p = p.replace("%%LOGO_DELAY%%", str(logo_delay))
    # no position rail on either card
    p = re.sub(r"<!--@rail-->.*?<!--@endrail-->", "", p, flags=re.S)
    return p


# ── C15 markup ──────────────────────────────────────────────────────────────────
# 🔴 THE COLUMN IS TALLER THAN ITS BAR, and the first render proved it the hard way.
# A column is [percentage] + [bar] + [price], so the TALLEST column is MAXBAR plus both
# labels — 464px against a 430px row — and the overflow went UPWARDS, putting "50.0"
# into the descenders of "PERCENTAGES". That is the collision class `card_check` exists
# to catch, and a bespoke page is the one kind of card it never sees. Sized so the whole
# column fits inside the row with room to spare: 68 + 16 + 235 + 20 + 52 = 391 < 420.
MAXBAR = 235.0
top = max(float(v) for _, v in LADDER)
c15_css = """
.ladder{margin-top:52px;display:flex;align-items:flex-end;gap:34px;height:420px;}
.col{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;}
.col .pc{font-family:'Anton','Barlow',sans-serif;font-weight:400;font-size:68px;
  line-height:1.0;color:#DA532C;margin-bottom:16px;}
.col .bar{width:100%;background:#DA532C;border-radius:8px 8px 0 0;transform-origin:bottom center;}
.col .odds{margin-top:20px;font-family:'Anton','Barlow',sans-serif;font-weight:400;
  text-transform:uppercase;font-size:52px;color:#C9C9C9;letter-spacing:0.02em;}
.lfoot{margin-top:38px;font-size:40px;font-weight:600;font-style:italic;color:#8F8F8F;
  max-width:1400px;line-height:1.2;}
"""
cols, anim15 = [], []
for i, (odds, pct) in enumerate(LADDER, 1):
    h = max(8, round(float(pct) / top * MAXBAR))
    cols.append(f'    <div class="col" id="k{i}"><div class="pc">{H.escape(pct)}</div>'
                f'<div class="bar" style="height:{h}px"></div>'
                f'<div class="odds">{H.escape(odds)}</div></div>')
    anim15.append(
        f' {{"sel":"#k{i}","kf":[{{"opacity":0,"transform":"translateY(30px)"}},'
        f'{{"opacity":1,"transform":"translateY(0)"}}],'
        f'"opts":{{"duration":560,"delay":{1400 + (i - 1) * 320},'
        f'"easing":"cubic-bezier(0.16, 1, 0.3, 1)"}}}},')
anim15.append(' {"sel":"#lfoot","kf":[{"opacity":0},{"opacity":1}],'
              '"opts":{"duration":520,"delay":4300,"easing":"ease-out"}},')
c15_markup = ('  <div class="ladder">\n' + "\n".join(cols) + "\n  </div>\n"
              f'  <div class="lfoot" id="lfoot">{H.escape(FOOTER)}</div>')
c15 = build("PP C15", "Fifteen · The Chart", "The Bookies&#39;<br>Percentages",
            c15_css, c15_markup, "\n".join(anim15), 4800)

# ── C17 markup ──────────────────────────────────────────────────────────────────
c17_css = """
.qs{margin-top:44px;display:grid;grid-template-columns:1fr 1fr;
  column-gap:70px;row-gap:20px;}
.q{display:flex;align-items:flex-start;gap:22px;}
.q .n{flex:none;width:62px;height:62px;border-radius:12px;background:#DA532C;
  font-family:'Anton','Barlow',sans-serif;font-weight:400;font-size:40px;color:#fff;
  display:flex;align-items:center;justify-content:center;}
.q .t{font-size:35px;font-weight:700;line-height:1.16;color:#EDEDED;
  text-transform:uppercase;letter-spacing:0.01em;padding-top:6px;}
"""
qs, anim17 = [], []
for n, w in items:
    qs.append(f'    <div class="q" id="q{n}"><div class="n">{n}</div>'
              f'<div class="t">{H.escape(w)}</div></div>')
    anim17.append(
        f' {{"sel":"#q{n}","kf":[{{"opacity":0,"transform":"translateY(22px)"}},'
        f'{{"opacity":1,"transform":"translateY(0)"}}],'
        f'"opts":{{"duration":500,"delay":{1300 + (n - 1) * 300},'
        f'"easing":"cubic-bezier(0.16, 1, 0.3, 1)"}}}},')
c17_markup = '  <div class="qs">\n' + "\n".join(qs) + "\n  </div>"
c17 = build("PP C17", "Seventeen · The Questions", "The Ten<br>Questions",
            c17_css, c17_markup, "\n".join(anim17), 4600)

# ── WRITE ───────────────────────────────────────────────────────────────────────
ep = json.loads((EPDIR / "docs/episode.json").read_text(encoding="utf-8"))
pages = {c["id"]: c["page"] for c in ep["cards"]}
for cid, doc in (("C15", c15), ("C17", c17)):
    dst = OUT / pages[cid]
    dst.write_text(doc, encoding="utf-8", newline="\n")
    print(f"wrote {dst.name}  ({len(doc):,} bytes)")
