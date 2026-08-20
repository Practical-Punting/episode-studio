#!/usr/bin/env python3
"""youtube_title.py — THE one place the YouTube title is derived, and the gate on it.

    python youtube_title.py --derive <episode.json>
    python youtube_title.py --check  <episode.json> <PP-EPnn-youtube.txt>

WHY THIS EXISTS (A6, 29 July 2026)
----------------------------------
`PP-EP13-youtube.txt` handed Jodie a RECOMMENDATION PLUS TWO ALTERNATIVES and did
not contain the title she wanted. She composed it herself:

    "The agreed title was not there — rather a set of other ideas! I need the title
     to be the agreed title then How to win at Horse Racing, like we discussed."

**And her decision then went nowhere.** `episode.json` still carried the title she
had rejected; her choice existed only on YouTube and in a chat log. Nothing wrote
it back.

> ## A FILE THAT ASKS A QUESTION IS A HALT WEARING A TEXT FILE'S CLOTHES.
> It looks finished and it is not — which is worse than a flag, because a flag is
> visible on the board and a menu buried in a text file is not.

THE MEASUREMENT THAT SETTLES THE RULE
-------------------------------------
Across the three episodes, against `packaging.byline`:

    EP11  "How to look beyond the favourites"
    EP12  "How to spot the fresh horse that can actually win"
    EP13  "How a professional assesses race form"
          -> JODIE'S CHOICE: "How a Professional Assesses Race Form | How to Win at
             Horse Racing"

Her title is **the byline, title-cased, with the channel line appended** — word for
word. Not the episode title, and not an invented phrase.

WHY THIS IS THE WHOLE FIX AND NOT A COSMETIC ONE
-------------------------------------------------
The YouTube title was produced at ~86%, LONG AFTER the last approval gate —
`title_approved` was already true on EP13 before that file was written. **So the one
string a viewer sees first had no gate at all.** The byline is approved at the Words
Gate on Turn 1. Derive from it and the YouTube title **inherits an approval it
already has**: no new gate, no new button for Hugh, nothing invented late.

ONE PLACE, SO THE HOUSE FORM IS A ONE-LINE CHANGE. `CHANNEL_LINE` and `SEP` below
are the whole of the house form. The kit describes it; this file IS it. If Jodie
ever rules differently — back to a prefix, a different channel line — it changes
here and nowhere else.

**EP11 AND EP12 ARE NOT RETITLED.** They are live with the old
`How to Win at Horse Racing: X` prefix form and nothing is served by churning them.
"""
import argparse
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                         # noqa: BLE001
        pass


class Halt(Exception):
    """A missing or malformed title is a DATA problem. Say which field, and stop."""


# --- THE HOUSE FORM. ONE HOME, READ BY BOTH SIDES. ---------------------------
#
# These two strings used to be literals here. They moved into docs/house-form.json on
# 3 Aug 2026 because THE BOARD HAS TO SHOW HER THE TITLE HER WORDS WILL BECOME, before
# she approves them — and it must show it using the derivation this file ENFORCES
# later, not a JavaScript copy of it. A copy is a second source of truth, and a second
# source of truth has bitten this project three times: the shipped captions (A7), the
# self_qc cue check (B5) and the shot map's clock (1 Aug). Each time the fix reached
# one reader and missed another.
#   scripts/ -> pp-episode-production/ -> skills/ -> .claude/ -> the repo root
_HOUSE = Path(__file__).resolve().parents[4] / "docs/house-form.json"


def _house_form():
    try:
        d = json.loads(_HOUSE.read_text(encoding="utf-8"))
        return d["separator"], d["channel_line"]
    except Exception as e:                                    # noqa: BLE001
        raise Halt(
            f"the house form could not be read from {_HOUSE} ({e}). That file is the "
            f"ONE home for the YouTube title's separator and channel line — the board "
            f"reads it too, so the preview it shows and the title this enforces cannot "
            f"drift apart. Restore it rather than hard-coding the strings back.")


SEP, CHANNEL_LINE = _house_form()

# 🔒 SUPERSEDED 2 AUGUST 2026 — THE TITLE IS THE EPISODE NAME, NOT THE BYLINE.
#
# Jodie's ruling: "YouTube title = the episode / e-book name, then the suffix."
#     The Meaning of Form — Part 1 | How to Win at Horse Racing
#
# THE OLD RULE DERIVED FROM `packaging.byline`, TITLE-CASED. That was measured
# against EP11-EP13 and it reproduced their hand-set titles — so it was a correct
# description of what had been done, and still the wrong thing to do. WHY: the title
# card says "THE MEANING OF FORM / Part 1", the e-book says "The Meaning of Form —
# Part 1", and the YouTube title said something else entirely. MEASURED ACROSS
# EP11-EP14, THE EPISODE NAME AND THE YOUTUBE TITLE HAVE NEVER ONCE MATCHED.
# One name everywhere a viewer looks.
#
# `title_case()` and its small-word list are GONE with the byline derivation. The
# episode name is already cased the way it ships on the cover and the title card, so
# re-casing it here could only introduce a difference — which is the whole fault.
#
# ⚠️ NOT RETROSPECTIVE. EP11, EP12 and EP13 are published under the old form and the
# kit's standing rule is that already-published videos are NOT retitled. This binds
# from EP14. A rebuild of an older episode would now halt on it, correctly — that is
# a conversation, not a silent retitle.


def title_of(epj: dict) -> str:
    t = (epj.get("title") or "").strip()
    if not t:
        raise Halt(
            "episode.json -> title is missing or empty, and the YouTube title IS the "
            "episode name plus the channel line. There is no fallback on purpose: "
            "composing one here would put a name on YouTube that appears nowhere else "
            "the viewer looks, which is exactly the fault this rule closes.")
    return t


def derive(name: str) -> str:
    """The house form: the episode name, then the channel line. Verbatim, no re-casing."""
    return name.strip() + SEP + CHANNEL_LINE


def derive_from(epj: dict) -> str:
    return derive(title_of(epj))


# --- ONE NAME EVERYWHERE A VIEWER LOOKS --------------------------------------
#
# THE ASSERTION THAT WAS MISSING, AND ITS ABSENCE IS WHY THIS SHIPPED FOUR TIMES.
# Nothing in the build had ever compared the three places the episode is NAMED:
# the title card, the e-book, and YouTube. Each was checked against its own source
# and all three passed while disagreeing with each other.

def _the_one_part_reader(s: str):
    """`packaging_gate.strip_part` — THE studio's single definition of a series part.

    Imported here rather than reimplemented, and named so that anyone tempted to add a
    fifth reader meets the point first. ⚠️ The path insert is fault #4: this module's own
    folder is not guaranteed to be on `sys.path` when the engine imports it, and a test
    that imports `packaging_gate` first would hide that. Same trap that bit
    `providers._split_part` this morning.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import packaging_gate as _pg
    return _pg.strip_part(s or "")


def _fold(s: str) -> str:
    """Compare NAMES, not typography: case, dash flavour and spacing are noise here.

    ⚠️ A DASH BETWEEN WORDS IS A SEPARATOR, AND IT IS NOISE TOO (11 Aug 2026).
    The title card is composed as `setup + payoff + " - " + part`, so an episode whose
    rail title reads "Track Secrets Part 1" — no dash — was reported as being called
    two different things, purely because the card puts a hyphen where the title has a
    space. EP16 only escaped it by having an em dash in its own name.
        Both sides get the same treatment, so this cannot make two DIFFERENT names
    agree: it folds "Each-Way" and "Each Way" together, which are the same name, and
    nothing else. Caught on a copy of EP21's file before an artefact was built.

    ⭐ AND THE SERIES PART IS READ BY **THE ONE DEFINITION**, NOT BY THIS FUNCTION.
    (20 Aug 2026 — EP34's THIRD halt of one build.)

    🔴 THIS USED TO CARRY ITS OWN IDEA OF WHAT A SERIES PART LOOKS LIKE, and it knew a
    HYPHEN and not BRACKETS. The title card is recomposed as `setup + payoff + " - " +
    part`, so `'The Don Scott Interview (Part 1)'` folded to `...(PART 1)` while the card
    folded to `...PART 1`, and the check reported the SAME NAME as two different names.
    **PP's own headline reads "(Part 2)", so the bracket form had never once passed.**
    Worse, it blamed the raw title — an INPUT — for disagreeing with a DERIVED output
    whose separator this code invented.

    ⚠️ THE FIX IS NOT TO ADD BRACKETS TO THE LIST HERE. That was fault 7 for the fourth
    time in three days (metres, dollars, per cent, the part separators). `strip_part` in
    `packaging_gate` is the ONE place the studio decides where a series part begins;
    `providers._split_part` already delegates to it, and now so does this. Any notation
    it learns, all three readers learn at once.
    """
    name, part = _the_one_part_reader(s)
    name = re.sub(r"[‐-―−-]+", "-", name)
    name = re.sub(r"\s*-\s*", " ", name)      # a separating dash reads as a space
    # ⚠️ TRAILING PUNCTUATION GOES TOO, AND ONLY HERE. `strip_part` deliberately leaves a
    # comma on the stem ("Thing, Part 5") because moving it would re-derive a SHIPPED
    # episode's `packaging.hook` — see E49. But this function compares NAMES rather than
    # typography, and a dangling separator is exactly the typography it exists to ignore.
    # Both sides get the same treatment, so it cannot make two DIFFERENT names agree.
    name = re.sub(r"\s+", " ", name).strip(" -,;:").upper()
    # `strip_part` normalises every notation to "Part N", so the part contributes the
    # SAME token whatever punctuation the title used. That is the whole repair.
    return f"{name} {part.upper()}".strip()


def episode_names(epj: dict) -> dict:
    """The episode name as each of the three artefacts states it."""
    cov = epj.get("cover") or {}
    pack = epj.get("packaging") or {}
    card = f"{cov.get('title_setup', '')} {cov.get('title_payoff', '')}".strip()
    if cov.get("part"):
        card = f"{card} - {cov['part']}"
    yt = (pack.get("youtube_title") or "")
    if yt.endswith(SEP + CHANNEL_LINE):
        yt = yt[: -len(SEP + CHANNEL_LINE)]
    return {
        "episode.json -> title": epj.get("title") or "",
        "the TITLE CARD (cover.title_setup + title_payoff + part)": card,
        "the E-BOOK (packaging.ebook_title)": pack.get("ebook_title") or "",
        "YOUTUBE (packaging.youtube_title, suffix removed)": yt,
    }


def check_one_name(epj: dict) -> list[str]:
    """Halt-worthy problems if the three artefacts do not name the same episode."""
    names = episode_names(epj)
    folded = {k: _fold(v) for k, v in names.items()}
    distinct = set(folded.values())
    if len(distinct) <= 1:
        return []
    return ["THE EPISODE IS CALLED DIFFERENT THINGS IN DIFFERENT PLACES. A viewer "
            "meets this name on the title card, on the e-book cover and in the "
            "YouTube listing, and they must be the same name:\n"
            + "\n".join(f"       {v!r}\n         in {k}" for k, v in names.items())
            + "\n     Fix the one that is wrong in episode.json. Nothing in the build "
              "compared these until 2 Aug 2026, which is how four episodes shipped "
              "with a YouTube title that matched nothing else."]


# --- the gate on the shipped file --------------------------------------------
MENU = re.compile(r"^\s*(RECOMMENDED|RECOMMENDATION|ALTERNATIVE|OPTION)\b", re.I)


def check_text(text: str, title: str) -> list[str]:
    """What is wrong with the file a human will paste from. Empty list = nothing.

    Judged on the ARTEFACT — the bytes Jodie opens — not on the code that wrote it.
    """
    problems = []
    lines = text.split("\n")
    first = lines[0].rstrip() if lines else ""
    if first != title:
        problems.append(
            f"line 1 is not the decided title.\n"
            f"     line 1: {first[:110]!r}\n"
            f"     wanted: {title!r}\n"
            f"     The title goes on line 1, alone, so the first thing anyone opening "
            f"this file sees is the decision — not a preamble and not a menu.")
    if not first.endswith(SEP + CHANNEL_LINE):
        problems.append(
            f"line 1 does not end with {SEP + CHANNEL_LINE!r}. That is the house form: "
            f"the episode-specific part leads and the channel line closes.")
    n = text.count(title)
    if n != 1:
        problems.append(
            f"the title appears {n} times in the file; it must appear exactly once. "
            f"A second copy is a second candidate, however it is labelled.")
    for i, ln in enumerate(lines[1:], start=2):
        if ln.rstrip().endswith(SEP + CHANNEL_LINE) or ln.rstrip().endswith(
                ":" + " " + CHANNEL_LINE):
            problems.append(
                f"line {i} is a SECOND TITLE: {ln.strip()[:110]!r}. The file carries one "
                f"decided title. Offering a choice in a text file asks a question that "
                f"nothing on the board is watching for an answer to.")
        if MENU.match(ln):
            problems.append(
                f"line {i} offers a menu: {ln.strip()[:110]!r}. One decided title, no "
                f"recommendation and no alternatives.")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--derive", metavar="EPISODE_JSON")
    ap.add_argument("--check", nargs=2, metavar=("EPISODE_JSON", "COPY_TXT"))
    a = ap.parse_args()

    if a.derive:
        epj = json.load(open(a.derive, encoding="utf-8"))
        print(derive_from(epj))
        return 0
    if a.check:
        epj = json.load(open(a.check[0], encoding="utf-8"))
        title = derive_from(epj)
        text = open(a.check[1], encoding="utf-8").read()
        problems = check_text(text, title)
        problems += check_one_name(epj)
        stored = ((epj.get("packaging") or {}).get("youtube_title") or "").strip()
        if stored and stored != title:
            problems.append(
                f"episode.json -> packaging.youtube_title is {stored!r}, but the title "
                f"derived from episode.json -> title is {title!r}. The stored value is a "
                f"RECORD of the derivation, not a second opinion — if the title should "
                f"change, the EPISODE NAME is what changes — and it changes in all "
                f"three places at once, because they are one name.")
        if problems:
            print("YOUTUBE TITLE CHECK FAILED:", file=sys.stderr)
            for p in problems:
                print(f"  · {p}", file=sys.stderr)
            return 2
        print(f"youtube title ok: {title}")
        return 0
    ap.error("give --derive or --check")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Halt as e:
        print(f"YOUTUBE TITLE HALTED — {e}", file=sys.stderr)
        sys.exit(2)
