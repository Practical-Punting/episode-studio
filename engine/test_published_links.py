#!/usr/bin/env python3
"""IS THE FILE WE SENT THE FILE WE MADE?

    python engine/test_published_links.py

🚨 EP30, 18 Aug 2026 — THE WORST FAULT IN WEEKS, AND AN EYE CAUGHT IT.
EP30's e-book was corrected under ruling A27: "33 per cent POT" -> "17.5% POT", the
disclosure waived by Hugh. A ruling, two amendments, seventeen controls, most of a day,
and the PDF on disk verified by reading it.

**Jodie then opened the e-book from the BOARD'S LINK and got the old one** — printing
33 per cent AND carrying the superseded note Hugh had asked to be removed. Without her
eye, every subscriber would have received the uncorrected book.

WHY. `step_ebook_pdf` builds and publishes in one breath; the rebuild was done by
running the build scripts directly, so `publish_artefact` never ran and the rail kept
pointing at the original upload. **The disk was right, the record was right, and the
thing the reader receives was wrong.**

    EVERY CHECK IN THIS STUDIO ASKS WHETHER THE FILE WE MADE IS CORRECT.
    NOT ONE ASKED WHETHER THE FILE WE SENT IS THE FILE WE MADE.

`assert the artefact`, one hop further out than we had ever looked: a published URL is a
SECOND COPY, and a second copy is a thing that can drift (`one source of truth, or it
drifts`).

⚠️ AND THE TIMING IS THE HARD PART. The rebuild happened AFTER `self_qc`, AFTER the four
approvals, and AFTER the artefact was published. A check that only runs inside a normal
build would not have caught this one — which is why the verifier is wired into `self_qc`
AND stands alone.

No network here: `fetch_fn` is injected, so every branch is driven with bytes we choose.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_published as vp                                          # noqa: E402
import providers                                                       # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


class Fake:
    """An episode folder with a real file in it, and a controllable 'server'."""

    def __init__(self, disk=b"THE CORRECTED BOOK", served=None, missing=False,
                 unreachable=False, edge=None):
        # `unreachable` is its own flag on purpose. The first version of this used
        # `served=None` to mean "the link is dead", but None also meant "same as disk",
        # so the case served the right bytes and the control passed while proving
        # nothing. A sentinel that means two things tests neither.
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name) / "PP-EP9030"
        (self.dir / "output").mkdir(parents=True)
        if not missing:
            (self.dir / "output" / "PP-EP9030-ebook.pdf").write_bytes(disk)
        self.unreachable = unreachable
        self.served = disk if served is None else served      # what the ORIGIN holds
        self.edge = edge                                      # what the CDN is serving

    def __enter__(self):
        self.real = vp.episode_dir
        vp.episode_dir = lambda n: self.dir
        return self

    def __exit__(self, *a):
        vp.episode_dir = self.real
        self.td.cleanup()

    def fetch(self, url, timeout=120):
        if self.unreachable:
            return None, "HTTP 404"
        # The cache-busted fetch reaches the ORIGIN; the plain one reaches the EDGE.
        if vp.CACHE_BUSTER in url:
            return self.served, ""
        return (self.edge if self.edge is not None else self.served), "HIT"


EP = {"ep_number": 9030,
      "ebook_url": "https://example.invalid/episode-assets/PP-EP9030/PP-EP9030-ebook.pdf"}


def _identical_passes():
    with Fake() as f:
        rows = vp.check_episode(EP, f.fetch)
        assert len(rows) == 1 and rows[0]["ok"], rows
        assert "identical" in rows[0]["why"]


case("a link serving the same bytes passes", _identical_passes)


def _ep30s_fault_is_caught():
    """🔴 THE CASE. The link serves the OLD book; the disk has the corrected one."""
    with Fake(disk=b"...$18.10 profit and 17.5% POT...",
              served=b"...$18.10 profit and 33 per cent POT...") as f:
        rows = vp.check_episode(EP, f.fetch)
        assert not rows[0]["ok"], "a stale published copy passed as fine"
        why = rows[0]["why"]
        # Since the origin/edge split, EP30's shape — the ORIGIN holding the old file
        # because the publish never ran — is named as ours to fix rather than as a cache.
        assert "NOT THE ONE ON DISK" in why, why
        assert "sha" in why and "bytes" in why, (
            f"it says they differ without saying HOW: {why}")


case("🔴 EP30's fault — the link serves the OLD file — is caught",
     _ep30s_fault_is_caught)


def _a_one_byte_difference_is_caught():
    """Not a size check. A same-length file with one byte changed is still the wrong
    document, and a length comparison would wave it through."""
    with Fake(disk=b"A" * 4096, served=b"A" * 4095 + b"B") as f:
        rows = vp.check_episode(EP, f.fetch)
        assert not rows[0]["ok"], "a same-SIZE, different-CONTENT file passed"


case("a same-size file with one byte changed is caught", _a_one_byte_difference_is_caught)


def _an_unreachable_link_is_a_finding_not_a_pass():
    with Fake(unreachable=True) as f:
        rows = vp.check_episode(EP, f.fetch)
        assert not rows[0]["ok"], (
            "a link that could not be fetched was reported as fine. 'I could not check' "
            "must never read as 'I checked and it was good'.")
        assert "could not fetch" in rows[0]["why"]


case("🔴 CONTROL — a link that cannot be fetched is a FINDING, never a pass",
     _an_unreachable_link_is_a_finding_not_a_pass)


def _a_missing_local_file_is_a_finding():
    with Fake(missing=True) as f:
        rows = vp.check_episode(EP, f.fetch)
        assert not rows[0]["ok"] and "no file on disk" in rows[0]["why"]


case("a published URL with no local file is a finding", _a_missing_local_file_is_a_finding)


def _an_episode_with_nothing_published_is_silent():
    with Fake() as f:
        rows = vp.check_episode({"ep_number": 9030}, f.fetch)
        assert rows == [], f"an unpublished episode produced findings: {rows}"


case("an episode with no published URL produces nothing",
     _an_episode_with_nothing_published_is_silent)


def _a_stale_cdn_edge_is_told_apart_from_a_bad_publish():
    """🔴 THE BLIND SPOT THIS CHECKER SHIPPED WITH, FOUND THE HOUR IT WAS WRITTEN.

    EP30's corrected e-book was re-published to the same key, the upload succeeded, and
    this file still cried "the link serves a different file" — because Cloudflare's edge
    was serving a cached copy (`cf-cache-status: HIT`) while the ORIGIN was correct.

    A verifier that fetches only the plain URL measures THE CDN, not the publish, and is
    wrong in both directions: crying wolf after a good publish, and — far worse —
    reporting "identical" off a cache while the origin holds something else. The two are
    different findings with different owners, and calling them the same thing sends the
    next person to fix the wrong end.
    """
    with Fake(disk=b"NEW", served=b"NEW", edge=b"OLD CACHED COPY") as f:
        rows = vp.check_episode(EP, f.fetch)
        r = rows[0]
        assert not r["ok"], "a stale edge was waved through as fine"
        assert r["origin_ok"] is True, "the origin was wrongly blamed"
        assert r["edge_ok"] is False
        assert "CACHED" in r["why"].upper(), r["why"]
        assert "Not a bad publish" in r["why"], (
            f"it reads as a failed publish when the publish was correct: {r['why']}")


case("🔴 CONTROL — a stale CDN edge is reported as a CACHE, not as a bad publish",
     _a_stale_cdn_edge_is_told_apart_from_a_bad_publish)


def _a_bad_publish_is_still_blamed_on_us():
    """The other side of the same coin: origin wrong is OURS to fix, and must say so."""
    with Fake(disk=b"NEW", served=b"OLD", edge=b"OLD") as f:
        r = vp.check_episode(EP, f.fetch)[0]
        assert not r["ok"] and r["origin_ok"] is False
        assert "OURS TO FIX" in r["why"], r["why"]


case("a wrong ORIGIN is named as ours to fix, not blamed on a cache",
     _a_bad_publish_is_still_blamed_on_us)


def _the_report_names_the_damage():
    with Fake(disk=b"new", served=b"old") as f:
        rows = vp.check_episode(EP, f.fetch)
    text = vp.report(rows)
    assert "DO NOT MATCH" in text and "different document" in text, text


case("the report says plainly that a reader gets a different document",
     _the_report_names_the_damage)


# ── WHERE IT IS WIRED ─────────────────────────────────────────────────────────
def _self_qc_checks_the_links():
    import ast
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fns = [n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef) and n.name == "self_qc"]
    real = [ast.get_source_segment(src, n) or "" for n in fns]
    assert any("published_links_match" in s for s in real), (
        "self_qc does not check the published links. Ordinary builds would go on "
        "trusting that publishing happened because the step said so.")


case("self_qc checks the published links", _self_qc_checks_the_links)


def _it_never_fails_a_build():
    """A publish that has not caught up is a thing to TELL a human, not a reason to stop
    an episode that is otherwise finished."""
    out = providers.published_links_match({"ep_number": 999999})
    assert isinstance(out, str) and out, "it returned nothing to say"


case("the self_qc check never raises, whatever it finds", _it_never_fails_a_build)


def _the_rebuild_path_says_it_did_not_publish():
    """🔴 THE HOLE AT THE SOURCE. The rebuild that caused this was a direct script run.
    It must say, every time, that writing a file is not publishing one."""
    src = (HERE.parent / ".claude/skills/pp-episode-production/scripts/build_ebook.py"
           ).read_text(encoding="utf-8")
    assert "IT DID NOT PUBLISH IT" in src, (
        "build_ebook.py can still write a PDF over a published episode in silence")
    assert "verify_published.py" in src, (
        "the warning does not tell the reader how to check")


case("🔴 a direct rebuild says LOUDLY that it did not publish",
     _the_rebuild_path_says_it_did_not_publish)


print(f"\npublished links: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
