#!/usr/bin/env python3
"""Gordon's furniture, and the ONE full script that carries it.

    python engine/twoway_furniture.py <ep_number> [--pp DIR] [--write]

`twoway_split` writes the DIALOGUE. This step writes the pieces Gordon speaks AS
GORDON — the open, the early e-book CTA, the midroll invitation, the close, the outro
and the responsible-gambling line — and then composes the two into the single script
Jodie pastes into HeyGen:

    docs/furniture-BB.txt        the pieces, in spoken order, one per segment
    docs/spoken-words-BB.txt     THE RENDER SCRIPT — furniture and dialogue interleaved
    docs/script-manifest-BB.json what each segment of that render will be

🔴 ONE RENDER, NOT TWO. Until 20 Sep 2026 the furniture was a SEPARATE render whose
segments were dropped into the cut at marked times. One render is fewer clicks, fewer
ids to keep straight, and — the real reason — it removes a class of fault nothing was
checking: two renders can disagree about the avatar, the voice, the framing or the day
they were made, and the first anyone would hear of it is a jump cut in the finished
episode. Jodie's brief of 20 Sep names two renders for the whole episode, BB and BM,
and this is what makes that true.

── WHERE EACH PIECE GOES, AND WHY NONE OF IT IS TYPED ────────────────────────────────
The open is first; the CTA follows Gordon's FIRST turn; the close follows the LAST turn
of the dialogue; the outro, the RG line and the sign-off follow the close in the order
`PP-episode-outro-standard.md` sets.

The midroll goes at **the handover nearest the midpoint of the episode, on a handover
INTO Gordon** — computed from the turns' own word counts, never chosen. Gordon has to
have the floor to speak it, so only his own turn starts are candidates; the midpoint is
where the spoken clock says it is. Typing "after turn six" would be a second home for
something the script already states, and the first two-way with a different shape would
inherit EP49's answer.

🔴 AND THE MIDROLL LINE ITSELF IS DRAWN BY THE POOL'S RULE — episode N takes
`L[N mod 10]` — and lifted VERBATIM by the pool's own documented parser. Never retyped.

── THE BREAKS ARE WHAT MAKE THE SEGMENTS CUTTABLE ────────────────────────────────────
Every Gordon-as-Gordon piece is its own paragraph with a six-second SSML break on BOTH
sides, so `twoway_interleave`'s silence detection finds it as its own segment and the
cut can take it, move it or drop it without touching a word of the reading. Six seconds
and not four is the 18 Sep measurement: asked for four, HeyGen returned 2.246s on one
voice, a quarter of a second above the 2.0s floor below which a pause is not a turn
boundary at all.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ep_paths                                                  # noqa: E402
import script_fidelity as sf                                     # noqa: E402
import twoway_split as ts                                        # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
REPO = HERE.parent
BREAK = ts.BREAK

MARKER = "# EP49 — STANDING FURNITURE"
"""Not used for parsing — see `is_composed()`. Kept only so the file says what it is."""

MANIFEST = "script-manifest-{code}.json"
"""🔴 THE SENTINEL LIVES BESIDE THE SCRIPT, NEVER INSIDE IT.

`twoway_split --write` will happily overwrite `spoken-words-BB.txt` with the dialogue
alone, which would silently throw the furniture away — and the first anyone would know
is a render with no outro in it. So something has to mark a composed script, and the
splitter refuses to clobber one.

⚠️ AND THE FIRST VERSION OF THAT MARK WAS A FAULT: an HTML comment on the script's own
first line. **THE SCRIPT IS PASTED INTO HEYGEN WHOLE.** Anything in it is spoken, so a
sentinel inside it is a sentinel the avatar reads out — caught here by looking at the
written file rather than at the plan for it.

The mark is therefore this MANIFEST beside the script: a file only this step writes,
that never goes near HeyGen, and that has a job of its own (it tells `interleave` what
each silence in the render is separating). A sentinel with an independent reason to
exist is one nobody is tempted to delete as clutter.
"""


class NotComposable(Exception):
    pass


# ─────────────────────────────────────────────────────── the pieces, as data ──

RG_LINE = "And remember — never bet more than you can afford to lose."
"""WORD-FOR-WORD LOCKED by the outro standard. Never varied, never re-voiced."""

OPEN = (
    "Back in two thousand and three, Practical Punting's editor Brian Blackwell sat "
    "down with the American handicapper Barry Meadow to work through the fundamentals "
    "of handicapping — how you actually go about picking a race. It ran in the "
    "magazine as a conversation, in six parts, and it's too good to summarise, so "
    "you're getting it the way it was written. Now, I'm not Brian, and my colleague "
    "Steve is not Barry. We're two readers. I'll read Brian's side of the "
    "conversation, Steve will read Barry's, and every word you hear is theirs, exactly "
    "as they wrote it. Right — Barry starts.")

CLOSE = (
    "That was Barry Meadow and Brian Blackwell, from the pages of Practical Punting — "
    "read by Steve and me.")

APPROVAL = "Hugh, 20 September 2026 (build spec A8 — his one-time OK on the open and the close)"
"""🔴 A8 IS SATISFIED AND THIS IS THE RECORD OF IT.

The open and the close are the only words in the episode that are neither the article's
nor a standing studio line, so A8 gated them on Hugh's one-time approval. Jodie relayed
that approval on 20 Sep 2026. It covers THESE TWO PIECES and nothing else — the CTA, the
wind-down and the sign-off are studio furniture inside shapes already approved, and
Gordon's script has no other gate.
"""

CTA = (
    "One quick thing before we get into it. There's a free guide to go with this "
    "video, with the whole conversation in it, Barry's five categories and all. The "
    "link's in the description below. Grab it and you can follow along as we go.")

WINDDOWN = (
    "So that's the fundamentals, from two men who do not go about it the same way. "
    "Barry wanting everything he can learn about a race before he forms an opinion, "
    "Brian sticking up for instinct and a sensible system, and the pair of them "
    "agreeing the game is far too complex to be reduced to one rule. I've put the "
    "whole conversation in a free guide, Barry's five categories and Brian's own "
    "routine included, so you've got it beside you on a Saturday. The link's just "
    "below this video.")

SIGNOFF = (
    "That's me for this one. Look after yourself, give the guesswork the respect it "
    "deserves, and I'll see you soon.")
"""⚠️ THE FIRST DRAFT OF THIS LINE WAS AN EXACT MATCH OF THIRTEEN SHIPPED EPISODES.
"That's me for now. Look after yourself, take your time over the form, and I'll see you
soon." is the most-used sign-off on the channel and it was reached for without knowing
that — which is the whole argument for the archive check below rather than for memory.
The nod here is EP49's own subject and appears nowhere in the archive."""


def pool_line(ep_number: int) -> tuple[str, str]:
    """The midroll invitation, drawn by the pool's rule and lifted by its own parser.

    The pool file documents its contract as `^### (L\\d)\\n> (.+?)$` — the heading, then
    the line IMMEDIATELY under it. A note once wedged between the two made the WARNING
    the pool line and failed three checks on prose, so the documented parser is used
    exactly as written rather than re-invented here.
    """
    txt = (REPO / "docs/midroll-line-pool.md").read_text(encoding="utf-8")
    lines = dict(re.findall(r"^### (L\d)\n> (.+?)$", txt.replace("\r\n", "\n"), re.M))
    if len(lines) != 10:
        raise NotComposable(
            f"the midroll pool parsed {len(lines)} lines, not ten: {sorted(lines)}. "
            "The pool is a batch Jodie approved; a pool that has lost a line is not "
            "that batch and the draw is meaningless.")
    lid = f"L{ep_number % 10}"
    return lid, lines[lid]


def pieces(ep_number: int) -> list[dict]:
    """Every Gordon-as-Gordon piece, in spoken order, with where it goes and why.

    `where` is a PLACEMENT RULE, not a position. `place()` resolves it against the
    dialogue; nothing here knows how many turns this episode has.
    """
    lid, midroll = pool_line(ep_number)
    return [
        {"id": "open", "name": "the open", "text": OPEN, "where": "before-dialogue",
         "provenance": f"NEW WORDS — approved by {APPROVAL}"},
        {"id": "cta", "name": "early e-book CTA", "text": CTA,
         "where": "after-host-turn-1",
         "provenance": "per-episode wording inside the approved shape"},
        {"id": "midroll", "name": f"midroll invitation {lid}", "text": midroll,
         "where": "midpoint-handover-into-host",
         "provenance": "VERBATIM from the pool of ten, drawn by N mod ten"},
        {"id": "close", "name": "the close", "text": CLOSE, "where": "after-dialogue",
         "provenance": f"NEW WORDS — approved by {APPROVAL}"},
        {"id": "outro", "name": "outro: wind-down and the e-book pointer",
         "text": WINDDOWN, "where": "after-dialogue",
         "provenance": "per-episode wind-down inside the approved shape"},
        {"id": "rg", "name": "responsible gambling", "text": RG_LINE,
         "where": "after-dialogue",
         "provenance": "WORD-FOR-WORD LOCKED, never varied"},
        {"id": "signoff", "name": "outro: sign-off", "text": SIGNOFF,
         "where": "after-dialogue",
         "provenance": "a PATTERN re-voiced each episode, never a previous "
                       "episode's words"},
    ]


# ───────────────────────────────────────────────────────────── the placement ──

def midpoint_handover(turns: list[dict], host: str) -> int:
    """The host turn whose START is nearest the middle of the spoken episode.

    🔴 COMPUTED, NEVER CHOSEN. The midroll is Gordon speaking as himself, so it can
    only sit where Gordon already has the floor — which makes the candidates his own
    turn starts and nothing else. Among those, the one nearest half the spoken clock
    wins. `words / WORDS_PER_S` is the same estimate every other step in this pipeline
    uses; a second definition of pace here would be a second home for it.
    """
    spoken = [t for t in turns if t["speaker"] != "NARR"]
    if not spoken:
        raise NotComposable("no spoken turns — there is no episode to place a midroll in.")
    words = [len(ts.spoken(t["text"]).split()) for t in spoken]
    total = sum(words)
    starts, run = [], 0
    for t, w in zip(spoken, words):
        starts.append((t["n"], t["speaker"], run))
        run += w
    mine = [(n, at) for n, code, at in starts if code == host]
    if len(mine) < 2:
        raise NotComposable(
            f"{host} has {len(mine)} turn(s); a midroll needs a handover INTO the host "
            "that is not the episode's own opening.")
    half = total / 2.0
    # The opening turn is never a midpoint, whatever the arithmetic says.
    return min(mine[1:], key=lambda p: abs(p[1] - half))[0]


def place(turns: list[dict], host: str, ep_number: int) -> list[dict]:
    """The render's segments, in order: every furniture piece and every host turn.

    Returns the manifest — what segment 1, 2, 3 … of the BB render will contain. It is
    the thing `interleave` needs in order to know which silence it is looking at, and
    it is written out beside the script for exactly that reason.
    """
    spoken = [t for t in turns if t["speaker"] != "NARR"]
    host_turns = [t for t in spoken if t["speaker"] == host]
    if not host_turns:
        raise NotComposable(f"no turns for the host {host}.")
    mid_turn = midpoint_handover(turns, host)
    by_where: dict[str, list[dict]] = {}
    for p in pieces(ep_number):
        by_where.setdefault(p["where"], []).append(p)

    def furn(p: dict) -> dict:
        return {"kind": "furniture", "id": p["id"], "name": p["name"],
                "text": p["text"], "provenance": p["provenance"], "turn": None}

    out = [furn(p) for p in by_where.get("before-dialogue", [])]
    for i, t in enumerate(host_turns):
        if i and t["n"] == mid_turn:
            for p in by_where.get("midpoint-handover-into-host", []):
                out.append(furn(p))
        out.append({"kind": "turn", "id": f"turn-{t['n']}", "name": f"turn {t['n']}",
                    "text": ts.spoken(t["text"]), "provenance": "the article, verbatim, "
                    "folded for the ear", "turn": t["n"]})
        if i == 0:
            for p in by_where.get("after-host-turn-1", []):
                out.append(furn(p))
    for p in by_where.get("after-dialogue", []):
        out.append(furn(p))
    for i, s in enumerate(out, 1):
        s["n"] = i
        s["words"] = len(s["text"].split())
    return out


# ─────────────────────────────────────────────────────────────── the writing ──

def spoken_only(script_text: str) -> str:
    """The words and the breaks, with any header lines taken off.

    A render script has no header — it is pasted whole — so on EP49 this returns the
    file. It exists for the older per-episode scripts that do carry `#` lines.
    """
    keep = [ln for ln in script_text.splitlines() if not ln.startswith("#")]
    return "\n".join(keep).strip()


def is_composed(path: pathlib.Path) -> bool:
    """Does this script carry the furniture? See `MANIFEST` — the mark is NOT inside it.

    `path` is the script; the answer is whether its manifest sits beside it and claims
    it. Reading the script for a mark is what put an HTML comment in front of the
    avatar, so the question is asked of the folder instead.
    """
    m = re.fullmatch(r"spoken-words-([A-Z]{2})\.txt", path.name)
    if not m:
        return False
    beside = path.parent / MANIFEST.format(code=m.group(1))
    try:
        d = json.loads(beside.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return bool(d.get("segments")) and any(s.get("kind") == "furniture"
                                           for s in d["segments"])


def compose(manifest: list[dict]) -> str:
    """The render script: every segment, a six-second break between each pair.

    🔴 NOTHING BUT WORDS AND BREAKS. This file is pasted into HeyGen exactly as it is,
    so a comment, a header or a marker in it is a line the avatar says out loud.
    """
    return f"\n\n{BREAK}\n\n".join(s["text"] for s in manifest) + "\n"


def furniture_file(ep_number: int, manifest: list[dict]) -> str:
    """The human-readable record of the pieces — what they are and where each goes."""
    furn = [s for s in manifest if s["kind"] == "furniture"]
    head = [
        f"# EP{ep_number} — GORDON AS GORDON: the pieces that are not the reading.",
        "#",
        '# Render on the HeyGen template "Gordon two-way small", with the dialogue,',
        "# in ONE script: docs/spoken-words-BB.txt. This file is the record of what",
        "# each piece is and where it goes; it is not pasted anywhere on its own.",
        "#",
        "# Each piece is its own paragraph with a six-second SSML break either side, so",
        "# the cut can take it, move it or drop it without touching a word of the",
        "# reading (build spec A1, presentation doc section 4).",
        "#",
        f"# THE OPEN AND THE CLOSE ARE APPROVED: {APPROVAL}.",
        "#",
    ]
    for i, s in enumerate(furn, 1):
        head.append(f"# {i}. {s['name']} — {s['provenance']}  "
                    f"[segment {s['n']} of {len(manifest)}]")
    return "\n".join(head) + "\n\n" + f"\n{BREAK}\n".join(s["text"] for s in furn) + "\n"


# ─────────────────────────────────────────────── the checks, before anything ──

def problems(manifest: list[dict], ep_dir: pathlib.Path, pp: pathlib.Path) -> list[str]:
    """Everything a human would find by reading it aloud, found before the render."""
    out = []
    for s in manifest:
        if s["kind"] != "furniture":
            continue
        for d in sorted(set(re.findall(r"\d", s["text"]))):
            out.append(f"{s['name']}: bare numeral {d!r} — every number is a word; "
                       f"render_ready hard-fails digits.")
        if "  " in s["text"] or s["text"] != s["text"].strip():
            out.append(f"{s['name']}: stray whitespace.")
    if not any(s["text"] == RG_LINE for s in manifest):
        out.append("the responsible-gambling line is not present VERBATIM — it is "
                   "word-for-word locked and may not be re-voiced.")
    # 🔴 THE SIGN-OFF AGAINST THE WHOLE ARCHIVE, NOT AGAINST MEMORY. The outro standard
    # forbids repeating a previous episode's sign-off verbatim, and the reason this is
    # a check and not a habit is that the first draft of EP49's WAS one of thirteen.
    for p in sorted(pp.glob("PP-EP*/docs/spoken-words*.txt")):
        if p.parent == ep_dir / "docs":
            continue
        try:
            tail = " ".join(p.read_text(encoding="utf-8", errors="replace").split()[-28:])
        except OSError:
            continue
        if SIGNOFF in tail:
            out.append(f"the sign-off repeats {p.parts[-3]} VERBATIM — the outro "
                       f"standard forbids it.")
    return out


# ───────────────────────────────────────────────────────────────── the step ──

def build(ep_number: int, pp: pathlib.Path = PP, write: bool = False) -> dict:
    ep_dir = ep_paths.episode_dir(ep_number, pp)
    docs = ep_dir / "docs"
    tj = docs / "turns.json"
    if not tj.is_file():
        raise NotComposable(f"no {tj} — run twoway_split.py first; this step composes "
                            "the dialogue it wrote and never re-derives it.")
    turns = json.loads(tj.read_text(encoding="utf-8"))["turns"]

    epj_path = docs / "episode.json"
    epj = json.loads(epj_path.read_text(encoding="utf-8")) if epj_path.is_file() else {}
    host = next((c for c, s in (epj.get("speakers") or {}).items() if s.get("host")),
                None)
    if host is None:
        raise NotComposable(
            "episode.json does not say which speaker is the HOST. The furniture is "
            "Gordon's and only the host's script may carry it; guessing 'the first "
            "one' would put the outro in Steve's mouth on the first episode that "
            "opened the other way round.")

    manifest = place(turns, host, ep_number)
    script = compose(manifest)
    bad = problems(manifest, ep_dir, pp)

    lid, _ = pool_line(ep_number)
    mid = next(s for s in manifest if s["id"] == "midroll")
    after = manifest[mid["n"] - 2]

    print(f"episode    : {ep_dir.name}")
    print(f"host       : {host}  (the furniture is the host's and no one else's)")
    print(f"midroll    : {lid}, drawn by {ep_number} mod ten")
    print(f"placed at  : segment {mid['n']}, the handover into turn "
          f"{manifest[mid['n']]['turn']} — after {after['name']}")
    print()
    print(f"{'seg':>3}  {'kind':<9} {'words':>5}  {'est':>6}  what")
    total = 0
    for s in manifest:
        est = s["words"] / 2.6
        total += est
        print(f"{s['n']:>3}  {s['kind']:<9} {s['words']:>5}  {est:>5.1f}s  {s['name']}")
    words = sum(s["words"] for s in manifest)
    furn_w = sum(s["words"] for s in manifest if s["kind"] == "furniture")
    print(f"\n{len(manifest)} segments, {len(manifest) - 1} breaks of six seconds")
    print(f"{words:,} spoken words ({furn_w} furniture, {words - furn_w:,} reading), "
          f"~{total / 60:.1f} min at 2.6 words/s before breaks")
    print(f"+ {(len(manifest) - 1) * 6 / 60:.1f} min of breaks cut out at assembly")

    if bad:
        print("\nNOT WRITTEN — the furniture does not pass its own checks:")
        for x in bad:
            print("  ! " + x)
        raise NotComposable(f"{len(bad)} problem(s) in the furniture.")

    out = {f"furniture-{host}.txt": furniture_file(ep_number, manifest),
           f"spoken-words-{host}.txt": script,
           MANIFEST.format(code=host): json.dumps(
               {"episode": f"EP{ep_number}", "host": host, "midroll_line_id": lid,
                "segments": [{k: v for k, v in s.items() if k != "text"}
                             for s in manifest]},
               indent=2, ensure_ascii=False) + "\n"}

    if write:
        for name, body in out.items():
            tmp = docs / (name + ".tmp")
            tmp.write_text(body, encoding="utf-8", newline="\n")
            os.replace(tmp, docs / name)
            back = (docs / name).read_text(encoding="utf-8")
            if back != body:
                raise NotComposable(f"{name} did not read back as written.")
            print(f"WROTE {docs / name}  ({len(body):,} bytes, re-read OK)")
    else:
        print(f"\nwould write {', '.join(out)} into {docs} (report only; pass --write)")
    return {"manifest": manifest, "script": script, "host": host, "docs": docs,
            "line_id": lid, "out": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    try:
        build(a.ep_number, pathlib.Path(a.pp), write=a.write)
    except NotComposable as e:
        print(f"\nHALT: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
