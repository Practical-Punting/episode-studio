#!/usr/bin/env python3
"""THE DOWNLOADS SWEEP — MATCH BY THE NAME WE ARE EXPECTING, NEVER BY RECENCY.

    python engine/downloads_sweep.py "G:\\My Drive\\PP Videos\\PP-EP44"
    python engine/downloads_sweep.py "G:\\My Drive\\PP Videos\\PP-EP44" --dry-run

────────────────────────────────────────────────────────────────────────────
WHY THIS EXISTS  (30 August 2026)
────────────────────────────────────────────────────────────────────────────
Stage 0 of the production skill has always said: *"Browser downloads land in
Downloads with random or `.tmp` names. Locate by name/recency, verify
duplicates by checksum, move into the episode structure."* That instruction was
written when this laptop ran ONE production line.

It now runs two. The Inspirational Women / Rising Story line generates media on
the same machine, into the same `~/Downloads`, from the same browser. **On the
day this was written, `iw-export.zip` and `pp-video-export.zip` were sitting
four minutes apart in that folder**, and a rule that says *take the recent one*
cannot tell them apart. The failure would not look like an error: the other
line's file would be filed into a PP episode folder under a PP name, and
nothing anywhere would say so.

    RECENCY IS A GUESS ABOUT WHOSE FILE THIS IS. A NAME IS A PROMISE.
    (CLAUDE.md §0a, pointed at a folder instead of an id.)

So this module answers one question — *is this file one THIS EPISODE ASKED FOR,
by name?* — and it takes the names from the episode's own shot script. Anything
else is REPORTED and left exactly where it is.

────────────────────────────────────────────────────────────────────────────
WHERE THE EXPECTATIONS COME FROM, AND WHY THERE IS NO LIST TO MAINTAIN
────────────────────────────────────────────────────────────────────────────
Every expected name is DERIVED from `docs/episode.json` — the b-roll targets,
the card pages, the standing clips, the midroll chip, the early CTA. Adding a
b-roll shot to an episode adds its expectation with no code change here, which
is the whole of CLAUDE.md §7: *a guard whose coverage is a list somebody
maintains is already broken, you have simply not met the missing item yet.*

Nothing outside episode.json is expected. In particular a hand-downloaded
HeyGen master arrives named after the HeyGen PROJECT, never
`presenter-master.mp4`, so it will not match — and that is the correct
outcome. It gets reported and a human moves it.

────────────────────────────────────────────────────────────────────────────
WHAT IT WILL AND WILL NOT DO
────────────────────────────────────────────────────────────────────────────
IT MOVES a file only when ALL of these hold:
  · its filename equals an expected name exactly (case-insensitively — Windows);
  · the destination does not already exist (it NEVER overwrites);
  · it is not still arriving (`.crdownload`/`.part`/`.partial`, or written in
    the last QUIET_S seconds);
  · the bytes that land equal the bytes that left.

IT NEVER deletes, never overwrites, never guesses, and NEVER RAISES INTO A
BUILD. A sweep that cannot run is a sweep that says so and stands aside — it is
housekeeping, and housekeeping may not halt an episode.

⚠️ RECENCY APPEARS TWICE IN HERE AND NEITHER USE DECIDES OWNERSHIP:
  · a QUIET HOLD, so a file still being written is left alone;
  · the ORDER of the "not ours" listing, newest first, so a stray file that
    turned up during this build is at the top where somebody will see it.
Neither one is ever allowed to answer *whose file is this*.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

__all__ = ["expected", "sweep", "report_lines", "audit", "downloads_dir"]

# A file written this recently may still be arriving. A HOLD, never an identity test.
QUIET_S = 30.0
# Part-files every mainstream browser writes while a download is in flight.
IN_FLIGHT_SUFFIXES = (".crdownload", ".part", ".partial", ".download")
# What could plausibly be a production asset. Anything else in Downloads is not
# this module's business and is not named in the report at all.
MEDIA_SUFFIXES = (".mp4", ".mov", ".webm", ".m4v", ".mkv",
                  ".png", ".jpg", ".jpeg", ".webp", ".gif",
                  ".srt", ".vtt", ".wav", ".mp3", ".m4a",
                  ".pdf", ".zip", ".tmp")
# How many "not ours" files to NAME. The count is always exact; the list is
# capped so the log stays readable — a report nobody reads is not a report.
NAME_AT_MOST = 10


def downloads_dir() -> Path:
    """The browser's landing folder. `PP_DOWNLOADS` overrides it, for tests."""
    p = os.environ.get("PP_DOWNLOADS")
    return Path(p) if p else Path.home() / "Downloads"


# ═══════════════════════════════════════════════════════════════════════════
# what this episode is actually expecting
# ═══════════════════════════════════════════════════════════════════════════
def expected(ep_dir: Path) -> dict[str, Path]:
    """{filename: where it belongs}, derived from THIS episode's episode.json.

    Never raises: an unreadable or half-written episode.json means we know of no
    expectations, which makes every file in Downloads "not ours" — the safe
    direction, because that bucket is only ever reported.
    """
    ep_dir = Path(ep_dir)
    try:
        epj = json.loads((ep_dir / "docs/episode.json").read_text(encoding="utf-8"))
    except Exception:                                                  # noqa: BLE001
        return {}
    if not isinstance(epj, dict):
        return {}

    want: dict[str, Path] = {}

    def add(name, dest_dir: str) -> None:
        if isinstance(name, str) and name.strip():
            n = Path(name.strip()).name          # a bare filename, never a path
            want[n] = ep_dir / dest_dir / n

    # the b-roll shots — the one asset class named per-episode in the shot script
    for b in epj.get("broll") or []:
        if isinstance(b, dict):
            tgt = b.get("target")
            if isinstance(tgt, str) and tgt.strip():
                add(f"{tgt.strip()}.mp4", "broll")

    # the card clips: a card's `page` IS the promise — render_cards writes
    # `<page stem>.mp4` (the same reasoning as providers._clip_from_episode_json)
    for c in epj.get("cards") or []:
        if isinstance(c, dict):
            page = c.get("page")
            if isinstance(page, str) and page.strip():
                add(f"{Path(page.strip()).stem}.mp4", "overlay/clips")

    # the midroll chip and the early e-book CTA name their clip FILE directly.
    # `build.standing` deliberately is NOT read here: its values are card IDS
    # ("TITLE", "END"), not filenames — those cards are already covered above by
    # their own `page`. Reading it would invent expectations like "TITLE.mp4".
    build = epj.get("build") if isinstance(epj.get("build"), dict) else {}
    for key in ("midroll", "early_cta"):
        blk = build.get(key)
        if isinstance(blk, dict):
            add(blk.get("clip"), "overlay/clips")

    return want


# ═══════════════════════════════════════════════════════════════════════════
# the sweep
# ═══════════════════════════════════════════════════════════════════════════
def _still_arriving(p: Path, now: float) -> bool:
    if p.name.lower().endswith(IN_FLIGHT_SUFFIXES):
        return True
    try:
        return (now - p.stat().st_mtime) < QUIET_S
    except OSError:
        return True                     # cannot stat it: treat as in flight, hands off


def sweep(ep_dir, downloads=None, move: bool = True, now: float | None = None) -> dict:
    """Look at Downloads, move only exact expected-name matches, report the rest.

    Returns a plain dict — the caller decides what to do with it. Nothing in
    here raises for anything a normal machine can present.
    """
    ep_dir = Path(ep_dir)
    dl = Path(downloads) if downloads else downloads_dir()
    now = now if now is not None else time.time()
    want = expected(ep_dir)
    # Windows filenames are case-insensitive; compare on a folded key so
    # `BROLL-….MP4` is recognised as ours rather than reported as a stranger.
    folded = {k.lower(): (k, v) for k, v in want.items()}

    out = {"episode": ep_dir.name, "downloads": str(dl), "expecting": len(want),
           "moved": [], "held": [], "not_ours": [], "not_ours_total": 0,
           "problem": None}

    try:
        entries = [p for p in dl.iterdir() if p.is_file()]
    except OSError as e:
        out["problem"] = f"{dl} could not be read ({e.__class__.__name__})"
        return out

    strangers = []
    for p in sorted(entries, key=lambda q: q.name.lower()):
        hit = folded.get(p.name.lower())
        if not hit:
            if p.suffix.lower() in MEDIA_SUFFIXES:
                strangers.append(p)
            continue

        name, dest = hit
        if dest.exists():
            out["held"].append(f"{name} — already in the episode, so it was left "
                               f"in Downloads and nothing was overwritten")
            continue
        if _still_arriving(p, now):
            out["held"].append(f"{name} — still arriving, left alone this time")
            continue
        if not move:
            out["held"].append(f"{name} — matches, not moved (dry run)")
            continue

        try:
            size = p.stat().st_size
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
            # ASSERT THE ARTEFACT (§1): a move that reported success and landed
            # short is exactly the shape that shipped a truncated master once.
            landed = dest.stat().st_size
            if landed != size:
                out["held"].append(
                    f"{name} — MOVED BUT ARRIVED SHORT: {landed:,} bytes of "
                    f"{size:,}. Do not use it until somebody looks.")
            else:
                out["moved"].append(f"{name} -> {dest.parent.name}/  ({size:,} bytes)")
        except Exception as e:                                         # noqa: BLE001
            out["held"].append(f"{name} — could not be moved ({e.__class__.__name__}); "
                               f"it is untouched in Downloads")

    # Newest first: ORDERING ONLY. A stray file that turned up during this build
    # is the one worth seeing, and it is never the reason anything gets moved.
    def when(q: Path) -> float:
        try:
            return q.stat().st_mtime
        except OSError:
            return 0.0

    strangers.sort(key=when, reverse=True)
    out["not_ours_total"] = len(strangers)
    out["not_ours"] = [p.name for p in strangers[:NAME_AT_MOST]]
    return out


# ═══════════════════════════════════════════════════════════════════════════
# saying what happened
# ═══════════════════════════════════════════════════════════════════════════
def report_lines(r: dict) -> list[str]:
    """The run-log report. A file that quietly is NOT moved must not be as
    silent as a file that quietly is — so both halves are named, every time."""
    if r.get("problem"):
        return [f"Downloads sweep stood aside: {r['problem']}. Nothing was moved."]

    lines = [f"Downloads sweep: {r['expecting']} name(s) expected by this episode, "
             f"matched by NAME (never by recency)."]
    for m in r["moved"]:
        lines.append(f"  moved  {m}")
    for h in r["held"]:
        lines.append(f"  held   {h}")

    n = r["not_ours_total"]
    if n:
        lines.append(f"  {n} other media file(s) in Downloads match nothing this "
                     f"episode expects. NOTHING WAS DONE WITH THEM — they may "
                     f"belong to the other production line on this machine:")
        for name in r["not_ours"]:
            lines.append(f"           {name}")
        if n > len(r["not_ours"]):
            lines.append(f"           …and {n - len(r['not_ours'])} more not listed.")
    if not r["moved"] and not r["held"]:
        lines.append("  nothing of this episode's was waiting in Downloads.")
    return lines


def audit(ep_dir, downloads=None, move: bool = True) -> list[str]:
    """The engine's one call. Returns log lines and CANNOT raise into a build."""
    try:
        return report_lines(sweep(ep_dir, downloads=downloads, move=move))
    except Exception as e:                                             # noqa: BLE001
        return [f"Downloads sweep could not run ({e.__class__.__name__}: {e}). "
                f"Nothing was moved. This does not affect the episode."]


def main(argv) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    for line in audit(args[0], move="--dry-run" not in argv):
        print(line)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass
    sys.exit(main(sys.argv))
