"""index.html must point at the bytes that are actually in the repo.

A cache-buster is only worth having if it CHANGES when the asset does. A number
somebody bumps by hand is the shape that goes stale on the first busy day — and this
one goes stale silently, because a stale hash looks exactly like a fresh one and the
browser cheerfully serves the old file.

So the hash is derived from the assets and this recomputes it: change app.js without
re-stamping and the suite goes red. The act of changing the file is what makes the
check notice (CLAUDE.md #7 — derive the coverage from the thing itself).

Run: python engine/test_asset_stamp.py
"""
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stamp_assets as st      # noqa: E402

FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"\n          {why}" if not cond and why else ""))
    if not cond:
        FAILED.append(name)


html = st.INDEX.read_text(encoding="utf-8")
want = st.stamp()
have = st.current(html)
print(f"  assets hash from the bytes: {want}")

for name in st.ASSETS:
    check(f"index.html versions {name}", have[name] is not None,
          "no ?v= at all — a browser may serve any age of this file, and nothing on "
          "screen would say so")
    check(f"  and it matches the current {name}", have[name] == want,
          f"index.html says {have[name]}, the bytes hash to {want} — re-run "
          "`python engine/stamp_assets.py --write` after changing an asset")

# the stamp must actually CHANGE when an asset does, or it is decoration
mutated = html
probe = st.apply(html, "deadbeef01")
check("stamping rewrites both links together",
      probe.count("?v=deadbeef01") == len(st.ASSETS), probe[:0])
check("  and a changed asset would produce a different hash",
      st.stamp() == want and want != "deadbeef01")

print(f"\n{'ASSET STAMP OK' if not FAILED else 'FAILURES: ' + str(FAILED)}")
sys.exit(1 if FAILED else 0)
