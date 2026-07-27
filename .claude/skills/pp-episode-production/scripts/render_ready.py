#!/usr/bin/env python3
"""render_ready.py — pre-HeyGen scan of the spoken-words track.

Run BEFORE Jodie renders, so a render is never wasted on a script that will
glitch. (PP-STANDARDS §PACKAGING, NUMBERS & RENDER-READY, 25 Jul 2026.)

Checks:
  1. BARE NUMERALS  — digits in the track (TTS wants numbers as words). HARD.
  2. ODD CHARACTERS — glyphs outside the safe set (ASCII + curly quotes,
     em/en dash, ellipsis). HARD.
  3. MIDROLL FRESHNESS — the midroll paragraph must not repeat VERBATIM any of
     the NINE immediately preceding episodes (HeyGen mangles repeated identical
     text). HARD.
     (Needs --episode for the midroll beat number; skipped without it.)

     NINE, NOT TEN — DO NOT "CORRECT" THIS (Jodie, 28 Jul 2026). The spoken
     midroll now comes from a fixed pool of TEN pre-approved lines used strictly
     in order (docs/midroll-line-pool.md): episode N takes L[N mod 10]. That
     cycle recurs at EXACTLY ten-episode intervals — L3 runs at EP13 and again
     at EP23. A ten-episode window would contain EP13 when EP23 is checked and
     would hard-fail every episode from EP23 onward, forever. At nine, the
     nearest legitimate prior use is always exactly ten back and passes; any
     accidental duplication closer than that fails, which is the intent.
  4. LENGTH — word count vs a sensible episode range (~150 wpm). WARN.

Usage:
    python render_ready.py <spoken-words.txt> [--episode episode.json]
Exits non-zero on any HARD problem; prints a plain-English report either way.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SAFE_EXTRA = set("‘’“”–—…é")  # ‘’“”–—…é
WPM = 150
WORDS_LO, WORDS_HI = 600, 2400

# How many PRECEDING episodes the midroll wording is compared against. NINE,
# because the pool of ten used in order repeats at exactly ten-episode
# intervals — see the module docstring. Changing this to 10 breaks every
# episode from EP23 on.
MIDROLL_WINDOW = 9


def _ep_num(folder_path):
    """Episode number parsed from a PP-EPnn folder path, or None.

    Handles both bare stems (PP-EP03) and post-Stage-8 renames
    (PP-EP01-The-Trifecta-Mistake). Returns None for unnumbered dev folders."""
    m = re.search(r"PP-EP(\d+)", os.path.basename(os.path.normpath(folder_path)))
    return int(m.group(1)) if m else None


def midroll_window(ep_dir, window=MIDROLL_WINDOW):
    """The spoken-words files of the `window` episodes immediately BEFORE this one.

    Ordered by EPISODE NUMBER, never by file mtime. PP-EP98 is a test folder that
    lives beside the real episodes; mtime ordering would drag it into every real
    episode's window, numeric ordering keeps it out."""
    mine = _ep_num(ep_dir)
    if mine is None:
        return []
    root = os.path.dirname(os.path.abspath(os.path.normpath(ep_dir)))
    found = []
    for other in glob.glob(os.path.join(root, "PP-EP*", "docs", "spoken-words.txt")):
        n = _ep_num(os.path.dirname(os.path.dirname(other)))
        if n is not None and n < mine:
            found.append((n, other))
    found.sort(key=lambda t: t[0], reverse=True)
    return found[:window]


def midroll_clash(mine_text, ep_dir, window=MIDROLL_WINDOW):
    """(episode folder name, count compared) — the first episode inside the window
    that already carries this exact wording, or (None, count)."""
    prior = midroll_window(ep_dir, window)
    for _n, other in prior:
        try:
            if mine_text and mine_text in open(other, encoding="utf-8").read():
                return os.path.basename(os.path.dirname(os.path.dirname(other))), len(prior)
        except OSError:
            continue
    return None, len(prior)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spoken_words")
    ap.add_argument("--episode", default=None)
    a = ap.parse_args()

    text = open(a.spoken_words, encoding="utf-8").read()
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    hard, warn = [], []

    # 1. bare numerals
    for i, p in enumerate(paras, 1):
        for m in re.finditer(r"\d[\d,./%:-]*", p):
            ctx = p[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
            hard.append(f"bare numeral '{m.group(0)}' in paragraph {i}: …{ctx}…")

    # 2. odd characters
    seen = {}
    for ch in text:
        if ord(ch) < 128 or ch in SAFE_EXTRA or ch in "\n\r\t":
            continue
        seen.setdefault(ch, 0)
        seen[ch] += 1
    for ch, n in sorted(seen.items()):
        hard.append(f"odd character {ch!r} (U+{ord(ch):04X}) ×{n} — TTS may glitch on it")

    # 3. midroll freshness
    if a.episode:
        try:
            ep = json.load(open(a.episode, encoding="utf-8"))
            mb = (ep.get("build", {}).get("midroll") or {}).get("beat")
            if mb and mb <= len(paras):
                mine = paras[mb - 1]
                ep_dir = os.path.dirname(os.path.dirname(os.path.abspath(a.episode)))
                which, compared = midroll_clash(mine, ep_dir)
                if which:
                    hard.append(
                        f"midroll wording reused VERBATIM from {which}, which is inside "
                        f"the {MIDROLL_WINDOW}-episode window — HeyGen corrupts repeats. "
                        "Take this episode's pool line (L[N mod 10] from "
                        "docs/midroll-line-pool.md). Do NOT reword it.")
                else:
                    print(f"ok: midroll wording is fresh "
                          f"({compared} prior episode(s) compared, window "
                          f"{MIDROLL_WINDOW})")
        except Exception as e:
            warn.append(f"midroll freshness check skipped ({e})")

    # 4. length
    words = len(text.split())
    mins = words / WPM
    if not (WORDS_LO <= words <= WORDS_HI):
        warn.append(f"length {words} words (~{mins:.1f} min) is outside the usual "
                    f"{WORDS_LO}-{WORDS_HI} range — double-check before rendering")
    else:
        print(f"ok: {words} words (~{mins:.1f} min), {len(paras)} paragraphs")

    for w in warn:
        print(f"WARN: {w}")
    if hard:
        print(f"\nNOT RENDER-READY — {len(hard)} problem(s):")
        for h in hard:
            print(f"  ✗ {h}")
        sys.exit(1)
    print("RENDER-READY ✓ — safe to paste into HeyGen")


if __name__ == "__main__":
    main()
