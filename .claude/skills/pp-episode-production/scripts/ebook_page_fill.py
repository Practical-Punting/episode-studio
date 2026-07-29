#!/usr/bin/env python3
"""ebook_page_fill.py — how full is each page of the e-book, and is a gap a fault?

    python ebook_page_fill.py <ebook.pdf>

WHY THIS EXISTS. A stranded heading was fixed by adding `orphans: 3`, which welded
every paragraph to the figure below it; a block that would not fit then jumped whole
and took the white space with it. EP13's page 2 came out **25% full** with the text
that belonged there on page 3. Two faults, opposite in direction, and the eye only
ever saw one at a time — nothing measured either until Jodie looked at the page.

WHAT IT WILL NOT DO. It will not ask a figure to shrink. Those figures are the motion
cards, and their text is already marginal on a phone: shrinking content to satisfy a
measurement is the same fault as relabelling a card to move the assertion percentage —
optimising for the checker rather than the reader. **White space around a figure that
genuinely will not fit is typesetting, not a defect** (Jodie, 29 Jul 2026), and this
script says so in words rather than leaving an open flag.

FLAGGING THINGS THAT ARE FINE IS HOW A REAL GAP GETS IGNORED. So three kinds of short
page are named and excluded: the cover, the standing marketing/warranty pages, the last
page of the article — and a fourth is EXPLAINED rather than flagged: a page whose
successor opens with a figure too tall for the space that was left.
"""
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

FLOOR = 0.70                      # below this, on a body page, is worth a look
HEADER, FOOTER = 0.085, 0.075     # running header/footer bands, as a fraction of height


def page_rows(img):
    """Rows carrying ink inside the text band, as fractions of the band."""
    w, h = img.size
    top, bot = int(h * HEADER), int(h * (1 - FOOTER))
    band = img.crop((0, top, w, bot)).convert("L")
    bw, bh = band.size
    px = band.load()
    ink = [y for y in range(bh)
           if min(px[x, y] for x in range(0, bw, 3)) < 200]
    return ink, bh


def figure_pages(pdf):
    """Pages carrying a full-size figure. A card render is thousands of px wide;
    the running logo is 244. Nothing else in the book is an image."""
    out = set()
    for line in subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True,
                               text=True).stdout.splitlines()[2:]:
        f = line.split()
        if len(f) > 4 and f[2] == "image" and int(f[3]) >= 3000:
            out.add(int(f[0]))
    return out


# HOW MUCH ROOM A FIGURE NEEDS, taken from the template rather than guessed at:
#   .illus { max-height: 78mm; margin: 18px auto }  on an A4 page (297mm)
# 18px at 96dpi is 4.76mm, so the block wants 78 + 9.5 = 87.5mm ≈ 29.5% of the page,
# which is ~35% of the text band. If less than that is left, the figure cannot follow
# on this page whatever else happens.
#
# TWO PROBES WERE TRIED AND BOTH FAILED, which is why this one is arithmetic:
#   · colour — the PRINT figures are white-on-white at the top, so the first coloured
#     pixel is the orange eyebrow a fifth of the way in, and a figure sitting at the
#     top of a page went undetected;
#   · pdftotext -bbox — this box ships Xpdf's pdftotext, which HAS NO -bbox. The
#     parser silently returned nothing and every page fell back to its default, so the
#     exemption fired for the wrong reason and still printed a plausible-looking
#     number. A probe that cannot fail loudly is worse than no probe.
FIG_BLOCK_MM, PAGE_MM = 78 + 9.5, 297.0
FIG_BAND = (FIG_BLOCK_MM / PAGE_MM) / (1 - HEADER - FOOTER)   # share of the TEXT BAND


def main():
    pdf = pathlib.Path(sys.argv[1])
    txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout.split("\f")
    standing = next((i + 1 for i, t in enumerate(txt)
                     if "Thanks for downloading" in t or "Please Gamble Responsibly" in t),
                    len(txt))
    last_body = standing - 1

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", "50", "-png", str(pdf), f"{td}/p"],
                       capture_output=True)
        pages = sorted(pathlib.Path(td).glob("p-*.png"))
        figs = figure_pages(pdf)
        data = {}
        for p in pages:
            n = int(p.stem.split("-")[-1])
            ink, bh = page_rows(Image.open(p))
            data[n] = {"fill": (max(ink) + 1) / bh if ink else 0.0,
                       "has_figure": n in figs}

    print(f"PAGE FILL — {pdf.name}   ({len(data)} pages; article body ends on page {last_body})")
    print(f"{'page':>5} {'fill':>7}")
    faults = []
    for n in sorted(data):
        d = data[n]
        bar = "#" * int(d["fill"] * 30)
        nxt = data.get(n + 1)
        if n == 1:
            note = "cover"
        elif n >= standing:
            note = "standing page (marketing / warranty)"
        elif n == last_body:
            note = "last page of the article — short by nature"
        elif d["fill"] >= FLOOR:
            note = ""
        elif nxt and nxt["has_figure"] and (1 - d["fill"]) < FIG_BAND:
            note = (f"under {FLOOR*100:.0f}%: THE NEXT FIGURE WILL NOT FIT in the space "
                    f"remaining ({FIG_BAND*100:.0f}% of the text area needed, "
                    f"{(1-d['fill'])*100:.0f}% left) — typesetting, not a defect")
        else:
            note = "<-- GAP: content still to come and no figure explains it"
            faults.append(n)
        print(f"{n:>5} {d['fill']*100:>6.0f}%   {bar:<30}  {note}")

    print(f"\nunexplained gaps: {len(faults)}  {faults or ''}")
    print("A figure is NEVER shrunk to close a gap — the figures are the motion cards and "
          "their text is already marginal on a phone.")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
