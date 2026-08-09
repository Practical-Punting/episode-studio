#!/usr/bin/env python3
"""E20 — THE RAIL MUST RECORD THE ID OF THE THING IT PAID FOR.

    python engine/test_heygen_id_recorded.py

Nothing in this repo ever wrote `heygen_video_id`. SCHEMA.md says "engine | HeyGen id
once picked up"; the engine only ever read it. So every episode carried NULL while a
completed, paid render sat on HeyGen, and `_heygen_fetch` found the render by listing
100 videos and matching a TITLE.

Logged as E20 on EP15, 4 Aug 2026, with the right fix and the right warning:

    "It works today and it is a guess. ⚠️ Part 1 / Part 2 / Part 3 of the same article
     are coming, and at 300 episodes titles will collide. The failure then is not
     'not found' — it is THE WRONG EPISODE'S RENDER, silently."

Unfixed, and on 9 Aug it bit EP19 — a Part 1 — where Jodie could see a finished render
and the board showed nothing.

THE BACKLOG'S IDEAL FIX IS NOT AVAILABLE. "Save the id at the moment the job is created"
assumes we create the job; the render is started BY A HUMAN in HeyGen's own UI, which is
precisely why there is no id to save. So the fix is: resolve by name once, REFUSE TO
GUESS between two paid renders, and write the id down the moment it is known.

No network and no rail: HeyGen's list endpoint and rail.set_fields are both stubbed, so
this asserts OUR behaviour rather than the provider's mood. Control first — each case
drives the situation and checks the wrong outcome is not the one we get.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import providers                                                      # noqa: E402
import rail                                                           # noqa: E402

PASS, FAIL = [], []
NAME = "PP-EP19 — 10 Systems For Action Hungry Punters Part 1"


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


class Harness:
    """HeyGen's list endpoint and the rail, both faked, both watched."""

    def __init__(self, videos, downloads=None):
        self.videos = videos
        self.written = {}
        self.downloaded = []
        self._real_open = providers.urllib.request.urlopen
        self._real_set = rail.set_fields
        self._real_dl = providers.RealProvider._download_exact
        self._real_env = providers.RealProvider._env

    def __enter__(self):
        harness = self

        def fake_open(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "video.list" in url:
                body = {"data": {"videos": harness.videos}}
            elif "video_status.get" in url:
                body = {"data": {"status": "completed",
                                 "video_url": "https://example.invalid/v.mp4"}}
            else:
                raise AssertionError(f"unexpected HeyGen call: {url}")
            return io.BytesIO(json.dumps(body).encode())

        class Ctx:
            def __init__(self, b):
                self.b = b

            def __enter__(self):
                return self.b

            def __exit__(self, *a):
                return False

        providers.urllib.request.urlopen = lambda req, timeout=None: Ctx(
            fake_open(req, timeout))
        rail.set_fields = lambda i, f: harness.written.setdefault(i, {}).update(f)
        providers.RealProvider._download_exact = staticmethod(
            lambda url, dest, attempts=3: harness.downloaded.append(url))
        providers.RealProvider._env = lambda self, k: "test-key"
        return self

    def __exit__(self, *a):
        providers.urllib.request.urlopen = self._real_open
        rail.set_fields = self._real_set
        providers.RealProvider._download_exact = self._real_dl
        providers.RealProvider._env = self._real_env
        return False


def vid(vid_id, title=NAME, status="completed", created=1786249163):
    return {"video_id": vid_id, "video_title": title, "status": status,
            "created_at": created}


def prov():
    return providers.RealProvider(Path("G:/My Drive/PP Videos"))


# ------------------------------------------------------------------- 1 -----
def _records_the_id_it_resolved():
    """The fix: found by title once, written down forever."""
    ep = {"id": "ep19-uuid", "heygen_name": NAME, "heygen_video_id": None}
    with Harness([vid("1652e1206a9649679833bf4e41c9df0f")]) as h:
        prov()._heygen_fetch(ep, Path("/tmp/master.mp4"))
    assert h.written.get("ep19-uuid", {}).get("heygen_video_id") == \
        "1652e1206a9649679833bf4e41c9df0f", (
        f"the render was found by title and the id was NOT written to the rail: "
        f"{h.written!r}. That is E20 exactly — the next reader repeats the search, and "
        f"the title stays load-bearing.")
    assert ep["heygen_video_id"] == "1652e1206a9649679833bf4e41c9df0f", \
        "the in-memory row was not updated, so this run still has no id"
    assert h.downloaded, "it recorded an id but never fetched the video"


case("an id resolved by title is written to the rail", _records_the_id_it_resolved)


# ------------------------------------------------------------------- 2 -----
def _refuses_to_guess_between_two_paid_renders():
    """CONTROL: two completed renders match. Taking the first is what it used to do.

    `next((v for v in vids if …))` silently returns whichever HeyGen listed first. That
    is a guess about which paid take a human meant to keep, and getting it wrong means
    the whole episode is narrated by the wrong one.
    """
    ep = {"id": "ep19-uuid", "heygen_name": NAME, "heygen_video_id": None}
    two = [vid("aaaa1111", created=1786249163), vid("bbbb2222", created=1786100000)]
    with Harness(two) as h:
        try:
            prov()._heygen_fetch(ep, Path("/tmp/master.mp4"))
        except providers.EngineFlag as e:
            assert "aaaa1111" in str(e) and "bbbb2222" in str(e), (
                f"it halted without naming both candidates, so a human cannot choose:"
                f"\n{e}")
            assert not h.downloaded, "it halted but had already downloaded something"
            assert "heygen_video_id" not in h.written.get("ep19-uuid", {}), \
                "it halted but had already written one of the two ids to the rail"
            return
    raise AssertionError(
        "two completed renders matched the same title and it picked one anyway. That is "
        "the failure E20 named: not 'not found', but the WRONG episode's render, "
        "silently.")


case("two matching renders halt rather than picking one",
     _refuses_to_guess_between_two_paid_renders)


# ------------------------------------------------------------------- 3 -----
def _an_id_already_on_the_rail_skips_the_search_entirely():
    """And the point of writing it down: the title is never consulted again.

    The harness serves a list that would match NOTHING, so if the search ran at all this
    would raise "no completed HeyGen render named …".
    """
    ep = {"id": "ep19-uuid", "heygen_name": NAME,
          "heygen_video_id": "1652e1206a9649679833bf4e41c9df0f"}
    with Harness([vid("zzzz9999", title="PP-EP99 — Something Else")]) as h:
        prov()._heygen_fetch(ep, Path("/tmp/master.mp4"))
    assert h.downloaded, "with a known id it still failed to fetch the video"
    assert not h.written, \
        f"it rewrote an id that was already correct: {h.written!r}"


case("a recorded id is used directly, with no title search",
     _an_id_already_on_the_rail_skips_the_search_entirely)


# ------------------------------------------------------------------- 4 -----
def _nothing_still_unrendered_is_treated_as_done():
    ep = {"id": "ep19-uuid", "heygen_name": NAME, "heygen_video_id": None}
    with Harness([vid("cccc3333", status="processing")]) as h:
        try:
            prov()._heygen_fetch(ep, Path("/tmp/master.mp4"))
        except RuntimeError as e:
            assert "no completed" in str(e), f"wrong error: {e}"
            assert not h.written, "it recorded an id for a render that is not finished"
            return
    raise AssertionError("a render still processing was treated as usable")


case("a render still processing is not recorded or fetched",
     _nothing_still_unrendered_is_treated_as_done)


print(f"\nheygen id: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
