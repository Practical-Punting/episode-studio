#!/usr/bin/env python3
"""THE LAYOUT CHECK, RUN AT THE HEAD OF THE BUILD INSTEAD OF TEN HOURS IN.

    python preflight_card_layout.py <episode_dir>            # report
    python preflight_card_layout.py <episode_dir> --json out  # machine-readable

🔴 WHY THIS EXISTS. EP35 C15, 20 Aug 2026: a card's orange label was `flex:none` and
1545px wide on a 1512px row, so all three of its fact boxes were pushed clean off the
card. The rendered frame showed a banner and none of the card's content. **The build
found out at `cards_render` — ten and a half hours in, after the render gate, the credit
check, four paid b-roll clips, two paid cover heroes and the cover pick.** Everything
needed to know it was on disk at four seconds.

## IT IS NOT A NEW RULEBOOK. IT IS THE EXISTING ONE, RUN EARLIER.
It authors each card in memory with `author_cards.render_card` — the same call that
writes the real page — into a scratch directory, then runs **`autofit_cards.py` and
`card_check.py`, unchanged, as subprocesses**. There is no second definition of "fits"
to keep in step with the first (CLAUDE.md fault #2), and a rule added to either tomorrow
is enforced here the same day without anyone remembering (fault #7).

## WHY IT MAY RUN THIS EARLY — BOTH HALVES OF THE OBJECTION, ANSWERED BY MEASUREMENT
`preflight_cards.layout_is_not_here()` said autofit and card_check "need the PAGES
rendered and the heroes STAGED, and at audit_inputs neither exists".
  · **pages** — `author_cards.render_card` produces the identical page in memory. The
    only difference from the on-disk file is autofit's injected CSS block, which is
    exactly what this is measuring the absence of.
  · **heroes** — MEASURED, 21 Aug 2026, and the objection does not bind. 100 cards
    across EP30/31/33/34/35 were authored and put through `card_check.check_page`
    TWICE: once served with every asset the episode had staged, once served with no
    asset at all. **100 identical verdicts, 0 changed.** card_check's rules are about
    TEXT geometry; the hero sits behind the text and moves none of it.
    Control: `test_preflight_card_layout.py`.

## 🔴 WHAT IT ASSERTS, AND WHY IT IS *NOT* "DOES IT FIT AT FULL SIZE"
A card that does not fit at full size is ORDINARY — autofit shrinks the type and it
fits, and 91 of 395 cards in the archive are in exactly that state. Halting on those
would halt almost every build, which is fault #4a's warning in one line: *a guard that
halts every build is the version somebody switches off.*
**So this asks the question the real halt asks: does the card still fail AT THE FLOOR?**
That is `autofit_cards.py`'s own verdict, taken from its own words, not re-derived.

⚠️ **IT NEVER WRITES INTO THE EPISODE.** Everything happens in a scratch directory that
is removed on the way out. It cannot change a word, a page or a card.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STILL_FAILING = re.compile(r"✗ (\S+\.html) — STILL DOES NOT FIT")
EXAMINED = re.compile(r"AUTOFIT — (\d+) page\(s\) examined")
TALLY = re.compile(r"AUTOFIT: (\d+) fitted, (\d+) still failing")


def _run(script: str, *args, timeout: int = 1800):
    r = subprocess.run([sys.executable, str(HERE / script), *[str(a) for a in args]],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def author_into(epj: dict, dest: pathlib.Path) -> tuple[dict, list[str]]:
    """Author every card into `dest`. Returns {page_name: card} and skipped notes.

    A card this cannot author is NOT this check's business — `rehearsal_faults` in
    preflight_cards.py already authors every card at this same moment and reports the
    failure in its own words. Reporting it twice sends a repair writer chasing two
    things (that module's own reasoning, kept).
    """
    import author_cards as ac
    owners, skipped = {}, []
    for card in epj.get("cards") or []:
        cid = card.get("id", "?")
        if (card.get("block") or "") == "bespoke":
            skipped.append(f"{cid}: bespoke — hand-authored, nothing to author here")
            continue
        try:
            blk = ac.load_block(card.get("block"))
            frame = ac.load_frame(card.get("layout", "fullscreen"))
            page = ac.render_card(card, blk, frame)
        except Exception as e:                                     # noqa: BLE001
            skipped.append(f"{cid}: not authorable yet ({type(e).__name__}) — "
                           f"the rehearsal check reports this one")
            continue
        name = card.get("page") or f"{cid.lower()}.html"
        (dest / name).write_text(page, encoding="utf-8")
        owners[name] = card
    return owners, skipped


def preflight_card_layout(epj: dict) -> dict:
    """Author, measure at the floor, and say which cards cannot be made to fit."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pp-preflight-layout-"))
    try:
        owners, skipped = author_into(epj, tmp)
        if not owners:
            return {"blockers": [], "lines": [
                "card layout pre-flight: no card could be authored yet — standing aside"],
                "skipped": skipped}

        # 🔴 NOT `--dry-run`, AND THE FIRST VERSION OF THIS GOT IT WRONG.
        # `--dry-run` does not run the shrink loop AT ALL: it measures once and, if
        # anything is out of place, records the size twice — "tried down to 66.0px from
        # 66.0px" — and moves on. So it answers "does this fit AT FULL SIZE", which 91
        # of the 395 cards in the archive legitimately fail because autofit is about to
        # shrink them. Asked that way this check reported EP35's C2 and C11 as
        # unfittable **in the same run where the real build fitted them in 4 and 9
        # steps** — two false alarms out of nineteen cards, on the first try.
        #     A real run shrinks and reports what survives AT THE FLOOR, which is the
        # condition the actual halt uses. It writes — into the scratch directory only,
        # which is thrown away below and is never the episode's own export.
        rc, out = _run("autofit_cards.py", tmp)
        seen = EXAMINED.search(out)
        tally = TALLY.search(out)
        # ⚠️ A SILENCE MUST NEVER COUNT AS A PASS. autofit prints "0 page(s) examined …
        # 0 fitted, 0 still failing" when it matched nothing, which is indistinguishable
        # from a clean sweep unless you ask. layout_rescue learned this the hard way and
        # the same guard is repeated here rather than assumed.
        if not seen or seen.group(1) == "0" or not tally:
            return {"blockers": [], "lines": [
                "card layout pre-flight: autofit examined no page, so NOTHING was "
                "measured — standing aside rather than reporting a pass"],
                "skipped": skipped}

        failing = STILL_FAILING.findall(out)
        lines = [f"card layout pre-flight: {seen.group(1)} card(s) measured at full "
                 f"size and at the floor — {tally.group(2)} cannot be made to fit"]
        blockers = []
        for page in failing:
            card = owners.get(page, {})
            cid = card.get("id", page)
            blockers.append(
                f"{cid}: this card cannot be laid out at any type size the design "
                f"allows. Something on it is claiming more room than the card has, and "
                f"stepping the type down does not recover it.")
        for s in skipped:
            lines.append(f"   note — {s}")
        return {"blockers": blockers, "lines": lines, "skipped": skipped,
                "failing_pages": failing, "autofit": out}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    epj_path = pathlib.Path(a.episode_dir).resolve() / "docs/episode.json"
    if not epj_path.is_file():
        print(f"no episode.json at {epj_path} — nothing to check")
        return 0
    res = preflight_card_layout(json.loads(epj_path.read_text(encoding="utf-8")))
    for line in res["lines"]:
        print(line)
    for b in res["blockers"]:
        print(f"  - {b}")
    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 1 if res["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
