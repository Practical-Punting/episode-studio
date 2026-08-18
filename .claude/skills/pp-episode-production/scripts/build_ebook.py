# Build a Practical Punting e-book PDF from its HTML source.
# Usage: python build_ebook.py <source.html> <out.pdf>
# Renders with WeasyPrint (base_url = the HTML's folder so images/logo resolve),
# then QCs: page count, live links, and that every content page carries the
# header logo. Exits non-zero if a check fails.
import os, sys, pathlib

SRC = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).resolve()

# WeasyPrint needs the GTK runtime on Windows (installed 2026-07-20). If this
# path moves, install from github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
GTK = r"C:\Program Files\GTK3-Runtime Win64\bin"
if os.path.isdir(GTK):
    os.add_dll_directory(GTK)

from weasyprint import HTML

OUT.parent.mkdir(parents=True, exist_ok=True)
doc_pdf = HTML(filename=str(SRC), base_url=str(SRC.parent)).render()
target = OUT
try:
    doc_pdf.write_pdf(str(OUT))
except PermissionError:
    # OUT is open in a viewer (Windows locks it). Write a sibling so the build
    # still completes; the caller closes the viewer and renames/re-runs.
    target = OUT.with_name(OUT.stem + "-new" + OUT.suffix)
    doc_pdf.write_pdf(str(target))
    print(f"!! {OUT.name} is LOCKED (open in a viewer?) — wrote {target.name} "
          f"instead. Close it, then rename {target.name} -> {OUT.name}.")
print(f"built {target.name}")
OUT = target  # QC below runs on whatever was actually written

try:
    import fitz
except ImportError:
    print("(install pymupdf for QC: python -m pip install pymupdf)"); sys.exit(0)

doc = fitz.open(str(OUT))
n = len(doc)

# Make the running-footer web address clickable on every page. WeasyPrint can't
# turn @bottom-center margin-box generated content into a link, so we add the URI
# annotation over the footer address post-render (found by text search, per page).
FOOTER_URI = "https://www.practicalpunting.com.au"
footer_links = 0
for page in doc:
    band_top = page.rect.height - 50  # the footer sits in the bottom margin only
    for rect in page.search_for("practicalpunting.com.au"):
        if rect.y0 < band_top:
            continue  # a body occurrence (e.g. marketing page), not the footer
        if any(fitz.Rect(l["from"]).intersects(rect)
               for l in page.get_links() if l.get("from")):
            continue  # already linked
        page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": FOOTER_URI})
        footer_links += 1
if footer_links:
    doc.saveIncr()
    print(f"footer address linked on {footer_links} page(s)")

links = [l.get("uri") for p in doc for l in p.get_links() if l.get("uri")]
print(f"pages: {n}")
print(f"links ({len(links)}):")
for u in links: print(f"   {u}")

problems = []
if not any("practicalpunting" in (u or "") for u in links):
    problems.append("no practicalpunting.com.au link found")
if not any("gamblinghelponline" in (u or "") for u in links):
    problems.append("no gamblinghelponline.org.au link found")
if not any((u or "").startswith("mailto:") for u in links):
    problems.append("no mailto: link found")

# header logo: content pages (2..n-1) should each have an image in the top strip
for i in range(1, n-1):
    page = doc[i]
    top = fitz.Rect(0, 0, page.rect.width, 70)
    if not any(fitz.Rect(info["bbox"]).intersects(top) for info in page.get_image_info()):
        problems.append(f"page {i+1}: no header logo")

print("QC:", "PASS" if not problems else "ISSUES")
for p in problems: print("   !", p)

# 🚨 THIS WROTE A FILE. IT DID NOT PUBLISH ONE. (EP30, 18 Aug 2026.)
# EP30's e-book was corrected under ruling A27 by running this script directly — the
# right file, correctly built, verified by reading the PDF. But `publish_artefact` lives
# in `step_ebook_pdf`, which was never run, so the rail went on pointing at the copy
# uploaded during the ORIGINAL build. The board's link served the uncorrected book, and
# an eye caught it rather than a gate.
#
#     A SILENT STALE PUBLISH IS THE FAULT. A NOISY ONE IS AN INCONVENIENCE.
#
# So this says so every time, unconditionally: it cannot know whether the episode has
# been published, and a warning that is only sometimes printed is one nobody learns to
# expect. Cheap, and it points at the tool that answers the question properly.
print("\n⚠️  THIS WROTE A PDF. IT DID NOT PUBLISH IT.")
print("    If this episode has already been published, the link still serves the OLD")
print("    copy until the publish step re-runs. Check it — it takes seconds:")
print("        python engine/verify_published.py <episode number>")

sys.exit(1 if problems else 0)
