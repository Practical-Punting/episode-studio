"""SITTING 4c — machine-QC the E-BOOK PDF and the THUMBNAIL, proved fail-first.

`stage_packaging` already proves the SOURCES carry the locked words. This proves the
FILES are whole — a different claim, and the one that was missing. Every case below
breaks a REAL EP18 deliverable in a specific way and watches the stage catch it, then
runs the untouched originals and expects silence.

Run: python engine/test_deliverables_qc.py
"""
import pathlib
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import qc_episode as q          # noqa: E402

def _ep_dir(n: int) -> pathlib.Path:
    """Resolve an episode folder BY NUMBER, never by a written-out name.

    ⚠️ THE STAGE-8 CLOSE-OUT RENAMES EVERY PUBLISHED EPISODE'S FOLDER — PP-EP18 became
    PP-EP18-Those-Top-6-Favourites the day the close-out was automated — so a literal
    path is a fuse: it passes for weeks and then SKIPS, silently, the day the process
    does the thing the standard requires of it.
    """
    root = pathlib.Path(r"G:\My Drive\PP Videos")
    hits = sorted(p for p in root.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else root / f"PP-EP{n:02d}"


SRC = _ep_dir(18)


def _deliv(pattern: str) -> pathlib.Path:
    """A deliverable BY SUFFIX, because the rename restems files too.

    PP-EP18-ebook.pdf became PP-EP18-Those-Top-6-Favourites-ebook.pdf. A literal
    filename is the same fuse as a literal folder, one level down.
    """
    hits = sorted((SRC / "output").glob("PP-EP18*" + pattern))
    if not hits:
        raise FileNotFoundError(f"no EP18 deliverable matching *{pattern}")
    return hits[0]

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


class Rec:
    """Stands in for the QC object: remembers what was said, judges nothing."""
    def __init__(self):
        self.fails, self.warns, self.notes = [], [], []
    def fail(self, m): self.fails.append(m)
    def warn(self, m): self.warns.append(m)
    def note(self, m): self.notes.append(m)


if not (SRC / "docs/episode.json").is_file():
    print("SKIP: EP18's deliverables are not reachable.")
    sys.exit(0)


def build(mutate=None):
    """A throwaway episode folder holding real EP18 deliverables, optionally broken."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pp-deliv-"))
    (tmp / "ebook").mkdir()
    (tmp / "output" / "qc").mkdir(parents=True)
    (tmp / "docs").mkdir()
    shutil.copyfile(SRC / "docs/episode.json", tmp / "docs/episode.json")
    shutil.copyfile(_deliv("-ebook.pdf"), tmp / "output/PP-EP18-ebook.pdf")
    shutil.copyfile(_deliv("-thumbnail.png"),
                    tmp / "output/PP-EP18-thumbnail.png")
    if mutate:
        mutate(tmp)
    rec = Rec()
    q.stage_deliverables(rec, str(tmp / "docs/episode.json"), str(tmp),
                         str(tmp / "output/qc"))
    return rec


def said(rec, *words):
    return any(all(w.lower() in m.lower() for w in words) for m in rec.fails)


print("\n=== FAIL FIRST — break a real deliverable, watch it get caught ===\n")

r = build(lambda t: (t / "output/PP-EP18-ebook.pdf").unlink())
check("a MISSING e-book PDF is caught", said(r, "no e-book PDF"), str(r.fails))

r = build(lambda t: (t / "output/PP-EP18-ebook.pdf").write_bytes(b"%PDF-1.4 not really"))
check("a CORRUPT e-book PDF is caught", said(r, "will not open"), str(r.fails))

r = build(lambda t: (t / "output/PP-EP18-thumbnail.png").unlink())
check("a MISSING thumbnail is caught", said(r, "no thumbnail"), str(r.fails))

r = build(lambda t: (t / "output/PP-EP18-thumbnail.png").write_bytes(b"\x89PNG\r\n\x1a\n"))
check("a CORRUPT thumbnail is caught",
      said(r, "not decode") or said(r, "not a finished"), str(r.fails))

def _shrink(t):
    import subprocess
    p = t / "output/PP-EP18-thumbnail.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(p), "-vf", "scale=640:360",
                    str(p.with_name("small-thumbnail.png"))], capture_output=True)
    p.unlink()
r = build(_shrink)
check("the WRONG SIZE is caught", said(r, "not 1280x720"), str(r.fails))

def _tiny_black(t):
    import subprocess
    p = t / "output/PP-EP18-thumbnail.png"
    p.unlink()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=black:s=1280x720", "-frames:v", "1", str(p)],
                   capture_output=True)
r = build(_tiny_black)
check("a flat placeholder is caught (by size)", said(r, "not a finished"), str(r.fails))

# 📌 A RULE THAT WAS WRITTEN AND THEN REMOVED, recorded so it is not re-added blind.
# A "thumbnail is too dark" FAIL was in this stage and came out again: no realistic
# fixture would make it fire. A render that produces nothing produces a FLAT frame,
# which is a 4 KB PNG and is caught by size (proved above). Forcing the luma rule to
# fire needed a noise field scaled down — something this pipeline cannot emit — and a
# guard that only fires on an impossible input is decoration. (CLAUDE.md 4b.)
# Mean luma is reported as a note instead; the assertion below is that it is REPORTED,
# not that it judges.

print("\n=== FAIL FIRST: the reader must never be told about the transcription ===\n")
# The fixture is EP18's OWN e-book as Hugh found it — the pre-rebuild PDF, kept as a
# .bak precisely so this guard could be watched failing on the real artefact rather
# than on something invented for the occasion.
# the same fuse once more: the close-out restems this fixture too
WITH_NOTE = next(iter(sorted((SRC / "output").glob("PP-EP18*-ebook.with-note.pdf.bak"))),
                 SRC / "output/PP-EP18-ebook.with-note.pdf.bak")
if WITH_NOTE.is_file():
    def _swap_in_bad_pdf(t):
        (t / "output/PP-EP18-ebook.pdf").unlink()
        shutil.copyfile(WITH_NOTE, t / "output/PP-EP18-ebook.pdf")
    r = build(_swap_in_bad_pdf)
    check("EP18's e-book AS HUGH FOUND IT is caught",
          said(r, "tells the READER about transcription"), str(r.fails)[:220])
    check("  and it quotes the sentence back",
          any("reproduced as printed" in f for f in r.fails), str(r.fails)[:200])
    check("  and it says where the note belongs instead",
          any("capture, which is internal" in f for f in r.fails))
else:
    check("the pre-rebuild EP18 e-book is available as a fixture", False,
          f"{WITH_NOTE.name} not found — the guard has not been watched failing")

print("\n=== and the real, untouched deliverables must be SILENT ===\n")
r = build()
check("EP18's shipped PDF and thumbnail raise NO failures", not r.fails, str(r.fails))
check("  and it says what it examined", len(r.notes) >= 2, str(r.notes))
check("  the note reports the thumbnail's size and mean luma",
      any("1280x720" in n and "mean luma" in n for n in r.notes), str(r.notes))
check("  and the PDF's page count", any("pages" in n for n in r.notes), str(r.notes))
for n in r.notes:
    print(f"        {n}")
for w in r.warns:
    print(f"        (warn) {w}")

print(f"\n{'=' * 66}")
print("DELIVERABLE QC PROVED (fail-first)" if not FAILED else f"FAILURES: {FAILED}")
sys.exit(1 if FAILED else 0)
