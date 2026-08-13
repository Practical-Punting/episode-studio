"""Resolve an episode folder BY NUMBER, never by a written-out name.

🔴 THE FUSE THIS DEFUSES. The stage-8 close-out RENAMES every published episode's
folder — `PP-EP23` became `PP-EP23-Track-Secrets-Part-3` the moment EP23 published, and
EP20, EP21 and EP22 are all renamed too. So a literal path passes for weeks and then
breaks, silently, ON THE DAY THE PROCESS DOES THE THING THE STANDARD REQUIRES OF IT.

It bit exactly that way on 13 Aug 2026: `test_layout_rescue` and `test_shot_map_flows`
were green all morning, EP23 was published at lunchtime, and both went red — not because
the code changed, but because the studio did its job. Ten minutes were spent proving the
merge innocent.

    A TEST THAT BREAKS WHEN THE PROCESS SUCCEEDS IS TESTING THE WRONG THING.

`test_deliverables_qc` had already learned this and carried its own copy of the fix. A
rule kept in two places is the one-value-in-two-places fault this repo keeps paying for
(see card_hold.py's header), so it lives here now and the tests import it.
"""
from __future__ import annotations

import os
import pathlib

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))


def episode_dir(n: int, pp: pathlib.Path | None = None) -> pathlib.Path:
    """The folder for episode `n`, renamed or not. The unrenamed name if it is missing."""
    root = pp or PP
    hits = sorted(p for p in root.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else root / f"PP-EP{n:02d}"


def have(n: int, *parts: str, pp: pathlib.Path | None = None) -> bool:
    """Is this file present inside episode `n`'s folder, whatever it is called?"""
    return (episode_dir(n, pp).joinpath(*parts)).is_file()
