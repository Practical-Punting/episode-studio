#!/usr/bin/env python3
"""Backfill youtube_title + cover_lowres_url for EP50-EP54 (Jodie, 1 Nov 2026).

    python C:\\Users\\jlral\\repos\\episode-studio\\engine\\backfill_title_cover.py           (dry run)
    python C:\\Users\\jlral\\repos\\episode-studio\\engine\\backfill_title_cover.py --write   (upload + write)

Migration 008 added the two columns; the engine fills them for every episode built from
now on (step_youtube_copy, step_web_copies). This fills them for the five episodes that
already have the files. Jodie's list, in her words: "Please backfill EP50, EP51, EP52,
EP53 and EP54. Leave EP55 out for now." EP55 is DROPPED for now, not forgotten.

Writes ONLY youtube_title and cover_lowres_url (rail.set_fields also stamps updated_at, as
every engine write does). Uses the engine's OWN definitions — youtube_title_line,
cover_lowres_file, cover_lowres_object, _publish_asset — so a backfilled row is exactly
what a build would have written. _publish_asset verifies the public URL answers and is
served as image/jpeg. A value already on the rail that differs is NOT overwritten.

The folder is found by its exact name (PP-EPnn, or PP-EPnn-<slug>), never by a loose glob,
and the rail's drive_folder is not used: EP50's still reads "PP-EP50" while its folder has
been renamed.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import rail                                                            # noqa: E402
from providers import (RealProvider, cover_lowres_file, cover_lowres_object,  # noqa: E402
                       youtube_title_line)

PP = Path(r"G:\My Drive\PP Videos")
EPISODES = [50, 51, 52, 53, 54]


def folder_for(n: int) -> Path:
    stem = f"PP-EP{n:02d}"
    hits = [p for p in PP.iterdir()
            if p.is_dir() and (p.name == stem or p.name.startswith(stem + "-"))]
    if len(hits) != 1:
        raise SystemExit(f"{stem}: expected exactly one folder, found {[p.name for p in hits]}")
    return hits[0]


def main() -> int:
    write = "--write" in sys.argv[1:]
    prov = RealProvider(PP)
    base = prov._env("SUPABASE_URL").rstrip("/")
    problems = 0
    print("MODE:", "WRITE" if write else "DRY RUN (nothing uploaded, nothing written)")
    for n in EPISODES:
        rows = rail._request("GET", "?select=id,ep_number,title,youtube_title,cover_lowres_url"
                                    f"&ep_number=eq.{n}")
        if len(rows) != 1:
            print(f"\nEP{n:02d}: expected one rail row, found {len(rows)} — SKIPPED")
            problems += 1
            continue
        row = rows[0]
        d = folder_for(n)
        txt = d / "output" / f"{d.name}-youtube.txt"
        cover = cover_lowres_file(d)
        missing = [p.name for p in (txt, cover) if not p.is_file()]
        if missing:
            print(f"\nEP{n:02d}: missing {missing} — SKIPPED")
            problems += 1
            continue
        title = youtube_title_line(txt.read_text(encoding="utf-8"))
        obj = cover_lowres_object(row)
        url = f"{base}/storage/v1/object/public/episode-assets/{obj}"
        print(f"\nEP{n:02d}  rail title : {row['title']}")
        print(f"      folder     : {d.name}")
        print(f"      youtube_title    -> {title!r}")
        print(f"      cover (local)    : {cover.name}  {cover.stat().st_size:,} bytes")
        print(f"      cover_lowres_url -> {url}")
        if not title:
            print("      line 1 is blank — SKIPPED")
            problems += 1
            continue
        clash = [(k, row[k]) for k, v in (("youtube_title", title), ("cover_lowres_url", url))
                 if row.get(k) not in (None, v)]
        if clash:
            print(f"      ALREADY HOLDS A DIFFERENT VALUE {clash} — SKIPPED, not overwritten")
            problems += 1
            continue
        if not write:
            continue
        pub = prov._publish_asset(cover, obj)
        if pub != url:
            print(f"      uploaded, but the URL came back as {pub} — NOT written")
            problems += 1
            continue
        got = rail.set_fields(row["id"], {"youtube_title": title, "cover_lowres_url": pub})
        ok = bool(got) and got.get("youtube_title") == title and got.get("cover_lowres_url") == pub
        print("      WRITTEN (read back from the update: matches)" if ok
              else "      write returned something unexpected — CHECK THE ROW")
        problems += 0 if ok else 1
    print(f"\n{len(EPISODES)} episodes, {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
