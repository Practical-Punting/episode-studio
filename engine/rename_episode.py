#!/usr/bin/env python3
"""rename_episode.py — apply the PP episode folder-naming standard.

Standard (2026-07-24): an episode folder is  PP-EP<NN>-<Title-Slug>/  — the
approved final title, slugified. The rename happens at STAGE 8, once Jodie has
approved the final title (you can't name the folder before the title is locked).
Everything inside the folder is referenced RELATIVE TO THE EPISODE ROOT, so
renaming the folder never breaks the build; the only names that carry the
episode stem are the shared deliverables (PP-EP<NN>-FINAL.mp4, -thumbnail.png,
-youtube.txt, ...), which this script restems to match the folder.

What it does:
  1. Renames  PP-EP<NN>[-old-slug]/  ->  PP-EP<NN>-<new-slug>/
  2. Restems every file under it whose name starts with the current folder stem
     (PP-EP<NN>-FINAL.mp4 -> PP-EP<NN>-<new-slug>-FINAL.mp4). Case-sensitive on
     the canonical "PP-EP<NN>-" prefix, so lowercase intermediates are left alone.
  3. Greps the whole PP Videos tree for stragglers — references to the OLD folder
     path or the OLD deliverable names that the rename has just invalidated
     (these are the "absolute episode path" refs the standard forbids).
  4. Prints a before/after report.

Idempotent: the CURRENT folder name is the source of truth for the old slug, so
re-running with the same (or a new) title converges without doubling the slug.

Usage:
  python rename_episode.py <episode> "<approved title>" [--apply]

  <episode>  1 | 01 | EP01 | PP-EP01 | the current folder name
  --apply    actually rename. Without it, prints the plan and changes nothing.

Run from anywhere. The script roots itself at the MEDIA root — PP_VIDEOS_DIR,
defaulting to the Drive path — NOT at its own directory. It lives in the repo
(engine/) from 28 Jul 2026; the folders it renames stay on Drive.

NOTE: the straggler grep covers the MEDIA root only, as it always has. It does not
grep the repo, so a repo document naming an old folder path would not be reported.
Repo docs hold no deliverables, so the risk is low — but it IS a real change from
when an (abandoned) repo clone happened to sit inside PP Videos.

BACKLOG: Stage-8 close-out is a terminal script, so Hugh cannot run it from a
browser. The engine's idle loop already FLAGS a published episode whose folder is
still the bare PP-EP<NN>, but clearing that flag needs a machine. A "rename and
close out" board button is the obvious fix and is on the backlog.
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

# The Windows console defaults to cp1252, which chokes on em-dashes etc. that
# turn up in the file snippets we echo back. Force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# THE MEDIA ROOT IS ON DRIVE; THIS SCRIPT IS IN THE REPO (moved 28 Jul 2026 —
# "code in GitHub, media on Drive"). It used to root itself at its OWN directory,
# which worked only because it sat inside PP Videos. From the repo that would make
# ROOT the repo: it would find no episode folders at all, and would grep the wrong
# tree. Same fix as rail.py and heygen_generate.py — take the media root from
# PP_VIDEOS_DIR, defaulting to the Drive path.
ROOT = Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos")).resolve()
if not ROOT.is_dir():
    raise SystemExit(
        f"error: media root not found: {ROOT}\n"
        "       set PP_VIDEOS_DIR if the episode folders live somewhere else.")

# SELF stops the straggler grep flagging this script's own source. It now lives
# OUTSIDE ROOT, so the guard is a harmless no-op — kept because the script still
# works if a copy is ever placed inside the media root.
SELF = Path(__file__).resolve()

# Files we never treat as text when grepping, and dirs we never descend into.
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
TEXT_EXT = {".md", ".txt", ".py", ".sh", ".json", ".html", ".htm", ".css",
            ".js", ".jsx", ".srt", ".vtt", ".ini", ".env", ".csv", ".yml", ".yaml"}
MAX_GREP_BYTES = 3_000_000


def slugify(title: str) -> str:
    """A readable Title-Slug: keep the title's own casing, punctuation -> hyphens."""
    s = title.strip().replace("&", "and")
    s = re.sub(r"[’'`]", "", s)          # drop apostrophes so "Don't" -> "Dont"
    s = re.sub(r"[^0-9A-Za-z\- ]+", " ", s)  # any other punctuation -> space
    s = re.sub(r"\s+", "-", s.strip())        # spaces -> hyphens
    s = re.sub(r"-{2,}", "-", s).strip("-")   # collapse runs
    if not s:
        raise SystemExit("error: the title slugifies to nothing — check the title.")
    return s


def parse_nn(episode: str) -> str:
    m = re.search(r"(\d{1,3})", episode)
    if not m:
        raise SystemExit(f"error: could not read an episode number from {episode!r}.")
    return f"{int(m.group(1)):02d}"


def find_folder(nn: str) -> Path:
    pat = re.compile(rf"^PP-EP{nn}(-.*)?$")
    matches = [d for d in ROOT.iterdir() if d.is_dir() and pat.match(d.name)]
    if not matches:
        raise SystemExit(f"error: no folder matching PP-EP{nn}[-...] under {ROOT}")
    if len(matches) > 1:
        names = ", ".join(sorted(d.name for d in matches))
        raise SystemExit(f"error: {len(matches)} folders match PP-EP{nn}: {names}")
    return matches[0]


def iter_text_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.resolve() == SELF:      # never flag our own source
                continue
            if p.suffix.lower() in TEXT_EXT:
                yield p


def find_stragglers(old_folder_name: str, old_basenames: list[str]):
    """References to the old folder path or old deliverable names, tree-wide."""
    # old folder used as a path component: "PP-EP01/" or "PP-EP01\"
    path_ref = re.compile(re.escape(old_folder_name) + r"(?=[/\\])")
    name_refs = [re.compile(re.escape(b)) for b in old_basenames]
    hits = []
    for p in iter_text_files():
        try:
            if p.stat().st_size > MAX_GREP_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if path_ref.search(line) or any(r.search(line) for r in name_refs):
                rel = p.relative_to(ROOT).as_posix()
                hits.append((rel, i, line.strip()[:140]))
    return hits


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv[1:]
    if len(args) != 2:
        print(__doc__)
        return 2

    nn = parse_nn(args[0])
    new_slug = slugify(args[1])
    old_folder = find_folder(nn)
    old_name = old_folder.name
    new_name = f"PP-EP{nn}-{new_slug}"
    new_folder = ROOT / new_name

    prefix = old_name + "-"  # the canonical stem the deliverables carry
    # (old_file_abs, new_basename) for every PP-EP<NN>- deliverable inside the folder
    restem = []
    for p in sorted(old_folder.rglob("*")):
        if p.is_file() and p.name.startswith(prefix):
            restem.append((p, new_name + "-" + p.name[len(prefix):]))
    old_basenames = [p.name for p, _ in restem]

    # ---- report header ------------------------------------------------------
    mode = "APPLY" if apply else "DRY RUN"
    print("=" * 64)
    print(f"EPISODE RENAME - PP-EP{nn}   [{mode}]")
    print("=" * 64)
    print("\nFolder:")
    print(f"  {old_name}")
    print(f"  ->  {new_name}" + ("   (no change)" if old_name == new_name else ""))

    print(f"\nFiles restemmed ({len(restem)}):")
    if not restem:
        print("  (none — no PP-EP%s- deliverables inside the folder yet)" % nn)
    for p, new_base in restem:
        rel = p.relative_to(old_folder).as_posix()
        parent = Path(rel).parent.as_posix()
        shown_new = (parent + "/" if parent != "." else "") + new_base
        print(f"  {rel}")
        print(f"    ->  {shown_new}")

    # ---- apply --------------------------------------------------------------
    failures = []
    if apply:
        if old_name != new_name and new_folder.exists():
            raise SystemExit(f"error: target folder already exists: {new_name}")
        # restem files first (still inside the old folder), then rename the folder
        for p, new_base in restem:
            target = p.with_name(new_base)
            if target.exists() and target != p:
                print(f"  ! skip (target exists): {new_base}")
                continue
            try:
                os.rename(p, target)
            except OSError as e:  # locked by a player / Drive sync mid-write
                failures.append((p.name, str(e)))
        folder_renamed = old_name == new_name
        if old_name != new_name:
            try:
                os.rename(old_folder, new_folder)
                folder_renamed = True
            except OSError as e:
                failures.append((old_name + "  (the folder)", str(e)))
        active_folder = new_folder if folder_renamed else old_folder
    else:
        active_folder = old_folder

    # ---- stragglers ---------------------------------------------------------
    stragglers = find_stragglers(old_name, old_basenames)
    print(f"\nStragglers - old-name references still in the tree ({len(stragglers)}):")
    if not stragglers:
        print("  (none)")
    else:
        print("  These point at the OLD folder path or OLD file names. Make each")
        print("  relative to the episode root, or update it to the new name.")
        for rel, ln, snippet in stragglers:
            print(f"  {rel}:{ln}: {snippet}")

    print()
    if apply:
        if failures:
            print(f"INCOMPLETE — {len(failures)} item(s) could not be renamed "
                  "(locked by a player or Drive sync?). Close them and re-run "
                  "(the rename is idempotent):")
            for name, err in failures:
                print(f"  ! {name}: {err}")
            return 1
        print(f"DONE. Episode is now {new_name}/  ({len(restem)} files restemmed).")
        if stragglers:
            print(f"Review the {len(stragglers)} straggler(s) above.")
    else:
        print("DRY RUN — nothing changed. Re-run with --apply to execute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
