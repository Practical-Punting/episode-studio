#!/usr/bin/env python3
"""A card that will not fit ONE frame, tried in the OTHER one before anybody is asked.

    python layout_rescue.py <episode_dir>            # report what would happen
    python layout_rescue.py <episode_dir> --apply    # swap the ones that clearly fit

🔴 EP23 C21, 12 Aug 2026 — THE HALT THAT LOOKED LIKE A WORDING PROBLEM AND WAS NOT.
"Benalla and Tatura" would not fit at the 60% floor, so the build stopped and asked a
human to choose "between the words and the layout". Tightening was tried first and
could never have worked: the cell block is BOTTOM-ANCHORED, so shortening the value
made the block shorter (177px -> 110px) and left its bottom edge at y=966 to the pixel,
still under a logo chip that starts at y=959. The card was authored `fullscreen` while
its five sibling minor-track slates in the same episode were all `panel-push`. Moved to
panel-push it fits at FULL SIZE, zero shrink steps, without one word changing.

    OVERFLOW ON SPACE -> TIGHTEN. OVERFLOW ON TIME -> SPLIT. (Jodie, 12 Aug.)
    AND BEFORE EITHER: IS THIS CARD SIMPLY IN THE WRONG FRAME?

⚠️ THIS IS THE B-ROLL PATTERN, DELIBERATELY. A b-roll/card overlap was never a
decision — the tool computed the delay AND confirmed the room before it printed, then
halted so somebody could retype the number. This is the same shape: the tool can TRY
the sibling frame and MEASURE the answer, so handing over the question unanswered is
the waste. Making a card consistent with its siblings is not a design choice.

🔒 WHAT IT WILL NOT DO — the whole safety argument, and every one of these HALTS
instead, because a rescue that quietly changes the episode is worse than the halt:
  · it never touches a word. Only `layout` is written, and the rendered TEXT of the
    two pages is compared character for character before anything is kept.
  · it never accepts a marginal fit. The other frame must fit with ZERO shrink steps —
    if the swap only works by stepping the type down, that is not "the wrong frame",
    it is a card that is too big for both, and it is Jodie's call.
  · it never accepts a page card_check will not pass.
  · it restores episode.json and re-authors the page if any of that fails, so a
    refused rescue leaves the episode exactly as it found it.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SIBLING = {"fullscreen": "panel-push", "panel-push": "fullscreen"}


def _run(script, *args, timeout=900):
    r = subprocess.run([sys.executable, str(HERE / script), *[str(a) for a in args]],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def visible_text(html: str) -> str:
    """What a viewer would read, with the markup and the autofit block taken out.

    The comparison that guarantees "not one word changed". Scripts and styles carry
    the frame's own machinery and differ between frames by design; the words do not.
    """
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return " ".join(re.sub(r"<[^>]+>", " ", body).split())


def failing_pages(export: pathlib.Path) -> list[str]:
    """The page files autofit cannot fit even at the floor."""
    _rc, out = _run("autofit_cards.py", export, "--dry-run")
    return re.findall(r"✗ (\S+\.html) — STILL DOES NOT FIT", out)


def rescue(ep_dir: pathlib.Path, apply: bool) -> int:
    epj_path = ep_dir / "docs/episode.json"
    export = ep_dir / "overlay/export"
    if not epj_path.is_file():
        print(f"MISSING: {epj_path}")
        return 2
    pages = failing_pages(export)
    if not pages:
        print("no card is failing at the floor — nothing to rescue")
        return 0

    swapped, refused = [], []
    for page in pages:
        epj = json.loads(epj_path.read_text(encoding="utf-8"))
        card = next((c for c in epj.get("cards", []) if c.get("page") == page), None)
        if card is None:
            refused.append((page, "no card in episode.json owns this page"))
            continue
        was = card.get("layout")
        other = SIBLING.get(was)
        if not other:
            refused.append((page, f"layout {was!r} has no sibling frame to try"))
            continue

        cid = card["id"]
        stem = pathlib.Path(page).stem
        only = re.search(r"c\d+", stem, re.I)
        only = only.group(0).lower() if only else stem
        before_html = (export / page).read_text(encoding="utf-8")
        # 🔒 THE EXACT BYTES, so a refused or report-only rescue puts the episode back
        # as it FOUND it rather than as this tool would have written it. Re-serialising
        # JSON is not restoring: indentation and the trailing newline are enough to
        # make "nothing changed" false for anything comparing files.
        epj_bytes = epj_path.read_bytes()

        # ── try the other frame, in place, with a full rollback if it disappoints ──
        card["layout"] = other
        epj_path.write_text(json.dumps(epj, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        keep, why = False, ""
        try:
            rc, out = _run("author_cards.py", epj_path, export, "--only", cid, "--force")
            if rc:
                why = f"the author refused it as {other}: {out.strip()[-200:]}"
            else:
                after_html = (export / page).read_text(encoding="utf-8")
                if visible_text(before_html) != visible_text(after_html):
                    why = ("the two frames render DIFFERENT WORDS, so this is not a "
                           "like-for-like swap")
                else:
                    rc_f, out_f = _run("autofit_cards.py", export, "--only", only,
                                       "--dry-run")
                    fitted = re.search(r"AUTOFIT: (\d+) fitted, (\d+) still failing",
                                       out_f)
                    # ⚠️ DID IT ACTUALLY LOOK AT THE PAGE? autofit reports
                    # "0 page(s) examined … 0 fitted, 0 still failing" when its --only
                    # pattern matches nothing, which is indistinguishable from a
                    # perfect fit unless you ask. The first version of this read that
                    # as "fits at full size" and would have swapped a card nobody had
                    # measured. A silence must never count as a pass.
                    seen = re.search(r"AUTOFIT — (\d+) page\(s\) examined", out_f)
                    if not seen or seen.group(1) == "0":
                        why = (f"autofit examined no page for {only!r}, so nothing was "
                               f"measured — refusing rather than guessing")
                    elif not fitted:
                        why = "autofit did not report a result for the swapped page"
                    elif fitted.group(2) != "0":
                        why = f"it does not fit as {other} either"
                    elif fitted.group(1) != "0":
                        why = (f"as {other} it only fits by stepping the type DOWN — a "
                               f"marginal fit is not 'the wrong frame', it is a card "
                               f"too big for both, and that is Jodie's call")
                    else:
                        rc_c, out_c = _run("card_check.py", export / page)
                        if rc_c:
                            why = f"card_check still refuses it as {other}"
                        else:
                            keep = True
        finally:
            # 🔒 RESTORE THE EXACT BYTES, and re-author the page from them, so a
            # refused OR report-only run is indistinguishable from never having run.
            # Re-serialising the JSON is not restoring: the indentation and trailing
            # newline alone make "nothing changed" false for anything comparing files,
            # and this tool's whole licence to act is that it changes nothing else.
            if not keep or not apply:
                epj_path.write_bytes(epj_bytes)
                _run("author_cards.py", epj_path, export, "--only", cid, "--force")
            if not keep:
                refused.append((page, why or "the swap did not hold"))
        if keep:
            swapped.append((page, cid, was, other))

    # 🔴 A SWAP TO panel-push CHANGES WHERE GORDON HAS TO BE, so re-derive framing NOW.
    # This is the C21 fault with the hand taken out of it: on 12 Aug the swap was made by
    # hand, framing was never re-derived, and beat 32 halted the shot map the next day.
    # Automating the swap without this would reproduce that halt on EVERY rescue, for
    # ever — the tool would be manufacturing the fault it exists to prevent.
    #
    # Only the card's OWN beat is settled here; the beats a card SPILLS into need the
    # aligned SRT and are derive_card_timings' half at shot_map. See framing.py.
    if apply and swapped:
        try:
            import framing as _fr
            epj_now = json.loads(epj_path.read_text(encoding="utf-8"))
            changed = _fr.resync_own_beats(epj_now)
            if changed:
                _fr.stamp_framing_note(epj_now, changed)
                epj_path.write_text(json.dumps(epj_now, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
                for n, was_f, cids in changed:
                    print(f"  FRAMING   beat {n} {was_f or 'unset'} -> WIDE "
                          f"(now carries the on-screen card {', '.join(str(c) for c in cids)})")
        except Exception as e:                                     # noqa: BLE001
            # Never lose a good rescue over the follow-up; shot_map re-derives anyway.
            print(f"  FRAMING   not re-derived here ({type(e).__name__}: {e}) — "
                  f"the shot map will still apply it")

    for page, cid, was, other in swapped:
        print(f"  {'SWAPPED' if apply else 'WOULD SWAP'}  {cid} ({page})")
        print(f"      {was} -> {other}: fits at FULL SIZE, zero shrink steps, "
              f"card_check clean, and the rendered words are character-for-character "
              f"identical. Its siblings already use {other}.")
    for page, why in refused:
        print(f"  LEFT FOR A HUMAN  {page}")
        print(f"      {why}")
    if not apply and swapped:
        print("\n(report only — nothing was written. Re-run with --apply.)")
    return 1 if refused else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    return rescue(pathlib.Path(a.episode_dir).resolve(), a.apply)


if __name__ == "__main__":
    sys.exit(main())
