"""Stamp index.html's asset links with a hash of the assets themselves.

    python engine/stamp_assets.py            # report
    python engine/stamp_assets.py --write    # update index.html

🔴 WHY THIS EXISTS. `index.html` loaded `app.js` and `styles.css` with no version at
all, so a browser or the Pages CDN could serve yesterday's board and nothing on screen
would say so. It has bitten before, and it bit again on 9 Aug 2026: the editor's
clipping fix was proved in a headless browser against a LOCAL server, pushed nowhere,
and Jodie hard-reloaded to find her screen unchanged. Proving a fix against the files
is not proving it against what she loads.

THE VERSION IS DERIVED FROM THE BYTES, never typed. A hand-bumped number is a list
somebody maintains, which is the shape that goes stale the first busy day
(CLAUDE.md #7) — and it goes stale silently here, because a stale number looks exactly
like a fresh one. `test_asset_stamp.py` recomputes it and fails if index.html disagrees,
so the act of changing app.js is what makes the check notice.
"""
import hashlib
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = pathlib.Path(__file__).resolve().parent.parent
INDEX = REPO / "index.html"
ASSETS = ("app.js", "styles.css")


def stamp() -> str:
    """One short hash over every asset, so touching either invalidates both."""
    h = hashlib.sha256()
    for name in ASSETS:
        h.update((REPO / name).read_bytes())
    return h.hexdigest()[:10]


def current(html: str) -> dict:
    out = {}
    for name in ASSETS:
        m = re.search(rf'{re.escape(name)}(?:\?v=([0-9a-f]+))?["\']', html)
        out[name] = m.group(1) if m else None
    return out


def apply(html: str, v: str) -> str:
    for name in ASSETS:
        html = re.sub(rf'{re.escape(name)}(?:\?v=[0-9a-f]+)?(["\'])',
                      f"{name}?v={v}\\1", html, count=1)
    return html


def main(argv):
    want = stamp()
    html = INDEX.read_text(encoding="utf-8")
    have = current(html)
    print(f"assets hash : {want}")
    for k, v in have.items():
        print(f"  {k:12s} in index.html: {v or '(none)'}  "
              f"{'OK' if v == want else 'STALE' if v else 'MISSING'}")
    if all(v == want for v in have.values()):
        print("\n✅ index.html already points at these bytes.")
        return 0
    if "--write" not in argv:
        print("\nreport only — pass --write to stamp it")
        return 1
    INDEX.write_text(apply(html, want), encoding="utf-8", newline="\n")
    back = current(INDEX.read_text(encoding="utf-8"))
    print(f"\nWROTE index.html -> {back}")
    return 0 if all(v == want for v in back.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
