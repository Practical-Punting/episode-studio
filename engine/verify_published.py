#!/usr/bin/env python3
"""verify_published.py — DOES THE LINK SERVE THE FILE WE THINK IT DOES?

    python engine/verify_published.py 30          # one episode
    python engine/verify_published.py --all       # every episode with a published URL
    python engine/verify_published.py --published # only status=published

🚨 THE FAULT THIS EXISTS FOR — EP30, 18 Aug 2026, AND IT WAS CAUGHT BY AN EYE.
EP30's e-book was corrected under ruling A27: a figure the article's own numbers
contradict, changed from "33 per cent POT" to "17.5% POT", with the disclosure waived by
Hugh. A ruling, two amendments, seventeen controls and most of a day.

**Jodie then opened the e-book FROM THE BOARD'S LINK and got the OLD ONE.** Not merely
uncorrected — the pristine original, printing `33 per cent POT` AND the superseded note
that says 17.6 per cent, the very paragraph Hugh had asked to be removed.

    WITHOUT HER EYE, EVERY SUBSCRIBER WOULD HAVE RECEIVED THE UNCORRECTED BOOK.

WHY IT HAPPENED. `step_ebook_pdf` is two actions in one breath:

    out = ctx.provider.build_ebook(ctx.ep)
    ctx.ep_set({"ebook_url": ctx.provider.publish_artefact(ctx.ep, out)})

The rebuild was done by running `author_ebook.py` and `build_ebook.py` DIRECTLY — the
right files, correctly built, verified by reading the PDF on disk. But `publish_artefact`
never ran, so the rail kept pointing at the copy uploaded during the original build. The
disk was right, the record was right, and **the thing the reader receives was wrong.**

🔴 SO THIS IS `assert the artefact` AT THE LAST MILE. Every check in the studio asks
whether the file we made is correct. **Not one of them asked whether the file we SENT is
the file we made.** A published URL is a second copy of the artefact, and a second copy
is a thing that can drift — the same lesson as `one source of truth, or it drifts`, one
hop further out than we had ever looked.

⚠️ AND IT MUST RUN STANDALONE, WHICH IS THE POINT. The rebuild happened AFTER `self_qc`,
AFTER the four approvals and AFTER the artefact was published. A check that only runs
during a normal build would not have caught this one. It is wired into `self_qc` so
ordinary builds are covered for nothing, and it stands alone so the DANGEROUS case — a
rebuild long after the build finished — can be checked by anybody, at any time.

Read-only. It fetches and compares. It publishes nothing and changes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ep_paths import episode_dir                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

# rail column -> where the file lives under the episode folder. The name on disk is
# derived the same way `publish_artefact` derives the object name, so the two cannot
# drift apart by being written down twice.
PUBLISHED = {
    "ebook_url":     "output/{f}-ebook.pdf",
    "thumbnail_url": "output/{f}-thumbnail.png",
}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(url: str, timeout: int = 120) -> tuple[bytes | None, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read(), (r.headers.get("cf-cache-status") or "")
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:                                             # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


# 🔴 THE CHECKER HAD A BLIND SPOT, AND IT TOOK AN HOUR TO FIND. (18 Aug 2026.)
# EP30's corrected e-book was re-published to the SAME object key, the upload reported
# success, and this file still said "THE LINK SERVES A DIFFERENT FILE". Both were true:
#
#     origin      → the corrected PDF, last-modified 18 Aug, sha 55805f3d
#     public URL  → the ORIGINAL, cf-cache-status: HIT, last-modified 17 Aug
#
# **Cloudflare's edge was serving a cached copy**, `cache-control: no-cache` notwithstanding.
# So a verifier that fetches the plain URL measures THE CDN, not the publish — and it can
# be wrong in BOTH directions: crying wolf after a good publish, and, worse, reporting
# "identical" from a cache while the origin holds something else entirely.
#
# So both are fetched and reported SEPARATELY, because they answer different questions:
#   · ORIGIN (cache-busted) — did our publish actually land? Ours to fix.
#   · EDGE (the plain URL)  — what does a reader get RIGHT NOW? Time, or a purge.
# A reader gets the edge, so a stale edge is still a real finding — it is just a
# different finding from a failed publish, and calling them the same thing sends the
# next person to fix the wrong end.
CACHE_BUSTER = "pp-verify"


def check_episode(ep: dict, fetch_fn=fetch) -> list[dict]:
    """One row per published artefact: does the URL serve the file on disk?

    `fetch_fn` is injected so the tests can drive every branch without a network.
    """
    n = ep.get("ep_number")
    d = episode_dir(int(n)) if n else None
    folder = d.name if d else ""
    out = []
    for col, tmpl in PUBLISHED.items():
        url = (ep.get(col) or "").strip()
        if not url:
            continue
        local = (d / tmpl.format(f=folder)) if d else None
        row = {"ep": n, "column": col, "url": url,
               "local": str(local) if local else "", "ok": False, "why": ""}
        if not local or not local.is_file():
            row["why"] = "no file on disk to compare against"
            out.append(row)
            continue
        disk = local.read_bytes()
        # ORIGIN first — did our publish land? Cache-busted, so no edge can answer for it.
        sep = "&" if "?" in url else "?"
        origin, oerr = fetch_fn(f"{url}{sep}{CACHE_BUSTER}=1")
        if origin is None:
            row["why"] = f"could not fetch the published copy ({oerr})"
            out.append(row)
            continue
        edge, cache = fetch_fn(url)
        row["origin_ok"] = origin == disk
        row["edge_ok"] = edge == disk
        if row["origin_ok"] and row["edge_ok"]:
            row["ok"] = True
            row["why"] = f"identical ({len(disk):,} bytes)"
        elif not row["origin_ok"]:
            row["why"] = (
                f"THE PUBLISHED FILE IS NOT THE ONE ON DISK — published "
                f"{len(origin):,} bytes (sha {_sha(origin)[:16]}), on disk "
                f"{len(disk):,} bytes (sha {_sha(disk)[:16]}). The publish never "
                f"happened, or happened from a different file. OURS TO FIX: re-run the "
                f"step that publishes it.")
        else:
            row["why"] = (
                f"published correctly, but THE LINK IS SERVING AN OLDER CACHED COPY "
                f"— edge {len(edge or b''):,} bytes"
                + (f" (cf-cache-status: {cache})" if cache else "")
                + f", origin and disk both {len(disk):,}. Not a bad publish: the "
                  f"origin is right. A reader following the link before the cache "
                  f"expires still gets the old file.")
        out.append(row)
    return out


def report(rows: list[dict]) -> str:
    bad = [r for r in rows if not r["ok"]]
    lines = []
    for r in rows:
        mark = "ok  " if r["ok"] else "🔴 "
        lines.append(f"  {mark} EP{r['ep']} {r['column']}: {r['why']}")
    lines.append("")
    if bad:
        lines.append(f"🔴 {len(bad)} of {len(rows)} published artefact(s) DO NOT MATCH "
                     f"the file on disk. Whoever follows that link gets a different "
                     f"document from the one we built and checked.")
    else:
        lines.append(f"✅ all {len(rows)} published artefact(s) match the file on disk.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="does the published link serve our file?")
    ap.add_argument("episode", nargs="?", help="episode NUMBER, e.g. 30")
    ap.add_argument("--all", action="store_true", help="every episode with a URL")
    ap.add_argument("--published", action="store_true", help="only status=published")
    a = ap.parse_args(argv)

    import rail                                                        # noqa: PLC0415
    rows = rail.list_all()
    if a.episode:
        n = int("".join(c for c in a.episode if c.isdigit()))
        rows = [r for r in rows if r.get("ep_number") == n]
    elif a.published:
        rows = [r for r in rows if (r.get("status") or "") == "published"]
    elif not a.all:
        ap.error("name an episode number, or use --all / --published")
    rows = [r for r in rows if r.get("ep_number")]
    rows.sort(key=lambda r: r["ep_number"])

    checked = []
    for ep in rows:
        checked += check_episode(ep)
    print(report(checked))
    return 1 if [r for r in checked if not r["ok"]] else 0


if __name__ == "__main__":
    raise SystemExit(main())
