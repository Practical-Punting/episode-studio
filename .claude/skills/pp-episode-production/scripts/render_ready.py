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
     midroll now comes from a fixed pool of TEN pre-approved lines
     (docs/midroll-line-pool.md); since 9 Nov 2026 every episode, PP-EP and
     PP-GH, takes THE LINE UNUSED LONGEST (pool_line_unused_longest), which
     replaced L[N mod 10]. Either way the
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


def _series_num(folder_path):
    """('EP', n) or ('GH', n) from a PP-EPnn / PP-GHnn folder path, or None."""
    m = re.match(r"PP-(EP|GH)(\d+)", os.path.basename(os.path.normpath(folder_path)))
    return (m.group(1), int(m.group(2))) if m else None


def _born(path):
    """When the folder was CREATED (Windows birth time; ctime elsewhere)."""
    st = os.stat(path)
    return getattr(st, "st_birthtime", st.st_ctime)


def _midroll_sequence(root):
    """The ONE shared midroll sequence, oldest first: [(position, folder-or-None)].

    PP-EP AND PP-GH SHARE ONE POOL (Jodie, 9 Nov 2026), so they share one sequence.
    - PP-EP n sits at position n, and EVERY number 1..highest gets a slot whether or
      not its folder exists — so a missing episode still occupies its place and can
      never widen the reach (the EP50 rule below).
    - PP-GH g has no number in the horse sequence, so it sits just AFTER the PP-EP
      folder that was CREATED most recently before its own folder (+0.5, then by GH
      number). DERIVED from the folders themselves — no list anybody maintains.
      Measured 9 Nov 2026: folder creation times on the Drive run in step with the
      EP numbers EP05..EP55, and PP-GH01 lands after PP-EP55.
      ⚠️ PP-EP98 (a test folder, created 24 Jul) would become a GH episode's anchor
      only if it were the newest PP-EP folder when that GH folder was made."""
    eps, ghs = {}, []
    for d in glob.glob(os.path.join(root, "PP-EP*")) + glob.glob(os.path.join(root, "PP-GH*")):
        k = _series_num(d)
        if k is None or not os.path.isdir(d):
            continue
        if k[0] == "EP":
            eps[k[1]] = d
        else:
            ghs.append((k[1], d))
    born_eps = sorted((_born(d), n) for n, d in eps.items())
    slots = [(n, eps.get(n)) for n in range(1, max(eps, default=0) + 1)]
    for g, d in ghs:
        t = _born(d)
        before = [n for b, n in born_eps if b < t]
        slots.append(((before[-1] if before else 0) + 0.5 + g / 10000.0, d))
    slots.sort(key=lambda s: s[0])
    return slots


def midroll_window(ep_dir, window=MIDROLL_WINDOW):
    """The spoken-words files of the `window` episodes immediately BEFORE this one,
    across PP-EP AND PP-GH (one pool, one sequence — see _midroll_sequence).

    Ordered by EPISODE NUMBER (and a GH episode's derived place), never by file
    mtime. PP-EP98 is a test folder that lives beside the real episodes; mtime
    ordering would drag it into every real episode's window, numeric ordering keeps
    it out.

    🔴 THE WINDOW IS THE NINE SLOTS BEFORE THIS ONE — NOT "THE NINE NEAREST FILES"
    (fixed 27 Sep 2026, EP50). It used to take the nine highest-numbered earlier
    folders that HAD a spoken-words.txt. The two-way EP49 has none (its words are in
    two furniture/turn files), so for EP50 the window silently slid back to EP40 —
    exactly ten back, the pool's own legitimate repeat of L0 — and hard-failed a
    correct script. A missing episode must shrink the count compared, never widen
    the reach. With no PP-GH episodes the nine slots are exactly N-9 … N-1, as
    before; a PP-GH episode in between takes one of the nine."""
    k = _series_num(ep_dir)
    if k is None:
        return []
    root = os.path.dirname(os.path.abspath(os.path.normpath(ep_dir)))
    slots = _midroll_sequence(root)
    if k[0] == "EP":
        mine = k[1]
    else:
        me = os.path.normcase(os.path.abspath(os.path.normpath(ep_dir)))
        hit = [p for p, d in slots if d and os.path.normcase(os.path.abspath(d)) == me]
        if not hit:
            return []
        mine = hit[0]
    prior = [s for s in slots if s[0] < mine][-window:]
    found = []
    for pos, d in prior:
        sw = os.path.join(d, "docs", "spoken-words.txt") if d else None
        if sw and os.path.exists(sw):
            found.append((pos, sw))
    found.sort(key=lambda t: t[0], reverse=True)
    return found


POOL_MD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "..", "..", "..", "docs", "midroll-line-pool.md"))


def midroll_pool(pool_md=POOL_MD):
    """{'L0': text, …} parsed with the pool file's own documented contract:
    `^### (L\\d)\\n> (.+?)$` — the heading, then the line IMMEDIATELY under it."""
    md = open(pool_md, encoding="utf-8").read().replace("\r\n", "\n")
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"^### (L\d)\n> (.+?)$", md, re.M)}


# A retired sentence and the one that replaced it, as the pool file's §NO CADENCE table
# records them: `> | `L0` | *"old"* | *"new"* |`.
_RETIRED_ROW = re.compile(r'^> \| `(L\d)` \| \*"(.+?)"\* \| \*"(.+?)"\* \|$', re.M)


def pool_wordings(pool_md=POOL_MD):
    """{'L0': [current text, every retired text], …} — EVERY wording each line has had.

    🔴 WHY (11 Nov 2026): the pool was re-approved with the cadence sentence taken out of
    all ten lines. `pool_line_unused_longest` finds which line an earlier episode used by
    matching its WORDS, so the moment the words changed every past episode stopped
    matching and every line read as never used: every episode would have got L0, and
    the rotation's whole history was gone. An earlier episode used L5 whether it said
    the old L5 or the new one.

    The retired wordings are DERIVED from the pool file's own record of what changed
    (each retired sentence beside its replacement), never kept as a second copy of the
    lines. Raises if a recorded replacement is not in its line exactly once, so a later
    edit to a line cannot quietly break the derivation.

    ⚠️ FOR RECOGNISING PAST USE ONLY. What an episode SAYS is the current line
    (`midroll_pool`); the number check's exemption is the current lines only
    (`script_fidelity.without_pool_lines`). A retired wording in a NEW script is not an
    approved line and is checked in full.
    """
    pool = midroll_pool(pool_md)
    md = open(pool_md, encoding="utf-8").read().replace("\r\n", "\n")
    out = {lid: [text] for lid, text in pool.items()}
    for m in _RETIRED_ROW.finditer(md):
        lid, old, new = m.groups()
        cur = pool.get(lid)
        if cur is None or cur.count(new) != 1:
            raise ValueError(f"midroll pool: the retired-wording row for {lid} names a "
                             f"replacement that is not in the current {lid} exactly once")
        out[lid].append(cur.replace(new, old))
    return out


def lines_in_folder(folder, pool):
    """Pool line ids found VERBATIM (any whitespace between words) in any .txt under
    the episode's docs/ — not only spoken-words.txt, because a two-way episode keeps
    its midroll in furniture/turn files (EP49, EP55). `pool` maps each id to its text,
    or to a LIST of every wording it has had (`pool_wordings`); any of them is a use."""
    found = set()
    texts = []
    for t in glob.glob(os.path.join(folder, "docs", "**", "*.txt"), recursive=True):
        try:
            texts.append(" ".join(open(t, encoding="utf-8", errors="replace").read().split()))
        except OSError:
            continue
    for lid, lines in pool.items():
        for line in ([lines] if isinstance(lines, str) else lines):
            flat = " ".join(line.split())
            if any(flat in t for t in texts):
                found.add(lid)
                break
    return found


def pool_line_unused_longest(ep_dir, pool_md=POOL_MD):
    """THE MIDROLL RULE (Jodie, 9 Nov 2026): every episode, horse AND greyhound,
    takes THE POOL LINE UNUSED LONGEST. Replaces `L[N mod 10]`, which broke the
    moment PP Greyhounds joined the pool (PP-GH01 took L6, so EP56 by N mod 10
    would have repeated it inside its own window, and every episode after it the same).

    Returns (line_id, text, last_used_by) — `last_used_by` is the folder name of the
    most recent EARLIER episode that used it, or None if no earlier episode ever has.

    Looks only at episodes BEFORE this one in the shared sequence
    (`_midroll_sequence`), so the answer for an episode never changes once later
    episodes are made, and an episode's own script never counts against itself.
    A line never used comes first; ties go to the lower id. Over a full pool this is
    a strict rotation again — each line recurs exactly ten episodes later, which is
    why the nine-episode window stays right."""
    pool = midroll_pool(pool_md)
    wordings = pool_wordings(pool_md)      # past episodes may carry a retired wording
    k = _series_num(ep_dir)
    if k is None:
        raise ValueError(f"not an episode folder: {ep_dir}")
    root = os.path.dirname(os.path.abspath(os.path.normpath(ep_dir)))
    slots = _midroll_sequence(root)
    if k[0] == "EP":
        mine = k[1]
    else:
        me = os.path.normcase(os.path.abspath(os.path.normpath(ep_dir)))
        hit = [p for p, d in slots if d and os.path.normcase(os.path.abspath(d)) == me]
        if not hit:
            raise ValueError(f"PP-GH folder not found on disk: {ep_dir}")
        mine = hit[0]
    last = {lid: (float("-inf"), None) for lid in pool}
    for pos, d in slots:
        if pos >= mine or not d:
            continue
        for lid in lines_in_folder(d, wordings):
            if pos > last[lid][0]:
                last[lid] = (pos, os.path.basename(d))
    lid = min(pool, key=lambda i: (last[i][0], i))
    return lid, pool[lid], last[lid][1]


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


def strip_notes_header(raw: str) -> list[str]:
    """The spoken paragraphs, with any production-notes header removed.

    THE SAME RULE `build_shot_map.py` USES, deliberately identical: prefer an explicit
    "PASTE … BELOW …" marker line, otherwise drop leading blocks that are pure `#`
    comments or a bracketed `[SETUP NOTE …]` block.

    ⚠️ FIXED 28 Jul 2026, FOUND BY RUNNING EP13 FOR REAL. build_shot_map stripped this
    header and render_ready did not — two tools reading the SAME FILE with different
    ideas of its format. So a spoken-words file with an ordinary header ("# PP-EP13 —
    … Part 1") failed the pre-render scan with four bare-numeral errors that were all
    in the COMMENT, while the spoken track itself was clean. The engine runs this at
    `audit_inputs`, so that is a halt on every episode whose script file has a header —
    and the halt names numerals a human cannot find in anything Gordon says.

    Nothing is masked by this: a numeral inside a real spoken paragraph is still caught.
    """
    mk = re.search(r"(?im)^.*paste\b.*\bbelow\b.*$", raw)
    if mk:
        raw = raw[mk.end():]
    paras = [p.strip() for p in raw.split("\n\n") if p.strip()]
    while paras and (all(ln.lstrip().startswith("#") for ln in paras[0].splitlines())
                     or paras[0].lstrip().startswith("[")):
        paras.pop(0)
    return paras


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spoken_words")
    ap.add_argument("--episode", default=None)
    a = ap.parse_args()

    text = open(a.spoken_words, encoding="utf-8").read()
    paras = strip_notes_header(text)
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
                    try:
                        want = pool_line_unused_longest(ep_dir)[0]
                    except Exception:                      # noqa: BLE001
                        want = "the line unused longest"
                    hard.append(
                        f"midroll wording reused VERBATIM from {which}, which is inside "
                        f"the {MIDROLL_WINDOW}-episode window — HeyGen corrupts repeats. "
                        f"Take this episode's pool line, {want} (the line unused longest, "
                        "from docs/midroll-line-pool.md). Do NOT reword it.")
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
