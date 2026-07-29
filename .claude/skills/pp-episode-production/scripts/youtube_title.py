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

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                         # noqa: BLE001
        pass


class Halt(Exception):
    """A missing or malformed title is a DATA problem. Say which field, and stop."""


# --- THE HOUSE FORM. Change it here; it is used nowhere else. -----------------
CHANNEL_LINE = "How to Win at Horse Racing"
SEP = " | "

# Small words stay lower case unless they are first or last. Jodie's list, 29 Jul
# 2026, verbatim. `is` is on it, which most style guides would not do — it is her
# call and it is followed exactly, not "corrected".
SMALL = {"a", "an", "the", "and", "but", "or", "for", "nor",
         "at", "by", "in", "of", "on", "to", "up", "as", "if", "is"}

_WORD = re.compile(r"[A-Za-z0-9']+")


def _cap(word: str) -> str:
    """Capitalise, leaving an already-capitalised interior alone (PP, e-book)."""
    return word[:1].upper() + word[1:]


def title_case(s: str) -> str:
    """Title-case a byline. Hyphenated compounds capitalise each part."""
    tokens = s.split()
    out = []
    for i, tok in enumerate(tokens):
        first_or_last = i == 0 or i == len(tokens) - 1
        parts = tok.split("-")
        done = []
        for j, part in enumerate(parts):
            m = _WORD.search(part)
            if not m:
                done.append(part)
                continue
            word = m.group(0)
            # A HYPHEN'S LATER PARTS ARE ALWAYS CAPITALISED, small word or not:
            # EP12 shipped "First-Up", and treating `up` as a small word there gives
            # "First-up". The hyphen makes one compound word, not two words.
            small = j == 0 and not first_or_last and word.lower() in SMALL
            new = word.lower() if small else _cap(word)
            done.append(part[:m.start()] + new + part[m.end():])
        out.append("-".join(done))
    return " ".join(out)


def byline_of(epj: dict) -> str:
    b = ((epj.get("packaging") or {}).get("byline") or "").strip()
    if not b:
        raise Halt(
            "episode.json -> packaging.byline is missing or empty, and the YouTube "
            "title is DERIVED from it. There is no fallback on purpose: falling back "
            "to the episode title, or to anything composed here, would produce the one "
            "string a viewer sees first out of words nobody approved. That is the fault "
            "this rule exists to close.")
    return b


def derive(byline: str) -> str:
    return title_case(byline) + SEP + CHANNEL_LINE


def derive_from(epj: dict) -> str:
    return derive(byline_of(epj))


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
        stored = ((epj.get("packaging") or {}).get("youtube_title") or "").strip()
        if stored and stored != title:
            problems.append(
                f"episode.json -> packaging.youtube_title is {stored!r}, but the title "
                f"derived from packaging.byline is {title!r}. The stored value is a "
                f"RECORD of the derivation, not a second opinion — if the title should "
                f"change, the byline is what changes, at the Words Gate.")
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
