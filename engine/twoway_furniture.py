#!/usr/bin/env python3
"""Gordon's furniture, and the ONE full script that carries it.

    python engine/twoway_furniture.py <ep_number> [--pp DIR] [--write]

🔴 THE WORDS COME FROM THE EPISODE, NEVER FROM THIS FILE (13 Nov 2026). Until then the
open, CTA, wind-down and sign-off were EP49's words as module constants, so `--write` for
any later two-way would have put EP49's words in Gordon's mouth and claimed Hugh's
approval for them (EP55 and EP56 were composed by scratch scripts that patched them in
memory). Now every per-episode piece is lifted from `docs/EPnn-new-words-APPROVED.md`
(sections 1-8, the layout EP55 and EP56 were approved in) and the step refuses to run
without it. Only the two STANDING lines live here: the responsible-gambling line (locked)
and the close (Hugh, 20 Sep 2026, reused on every two-way since).

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

🔴 AND THE MIDROLL LINE ITSELF IS DRAWN BY THE POOL'S RULE — since 9 Nov 2026, THE LINE
UNUSED LONGEST across PP-EP and PP-GH (it replaced `L[N mod 10]`) — and lifted VERBATIM
by the pool's own documented parser. Never retyped.

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

CLOSE = (
    "That was Barry Meadow and Brian Blackwell, from the pages of Practical Punting — "
    "read by Steve and me.")
"""THE STANDING CLOSE — Hugh's one-time OK, 20 Sep 2026 (build spec A8), reused word for
word on EP55 and EP56. A different close is a NEW KIND OF LINE and goes to Hugh, so the
step refuses one rather than composing it."""

WORDS_FILE = "EP{n}-new-words-APPROVED.md"
"""The approved new words, in the episode's own docs/. Cowork writes it; Jodie approves
it; the runner copies it in when the episode gets its number."""

SECTIONS = {1: "open", 2: "handover", 3: "cta", 4: "midroll", 5: "close", 6: "outro",
            7: "rg", 8: "signoff"}
"""The section numbers of the approved-words file, as EP55's and EP56's are laid out."""


def approved_words(docs: pathlib.Path, ep_number: int) -> dict:
    """The eight pieces, lifted from the approved file — never retyped.

    Each section's words are its FIRST paragraph; notes in brackets, lists and the
    standfirst record follow it and are not words. The midroll section may name its
    pool line in the heading and carry no text (EP55's shape) — then the pool's own
    wording of that line is the text. Returns {piece: text, "approval": line,
    "midroll_id": "Ln" or None, "source": path}.
    """
    f = docs / WORDS_FILE.format(n=ep_number)
    if not f.is_file():
        raise NotComposable(
            f"no {f.name} in {docs} — the new words are not approved yet. Cowork writes "
            "them; Jodie approves them; this step only lifts them.")
    md = f.read_text(encoding="utf-8").replace("\r\n", "\n")
    status = next((ln.strip() for ln in md.splitlines()
                   if ln.lower().startswith("status:")), "")
    if "APPROVED" not in status.upper():
        raise NotComposable(f"{f.name} has no 'Status: APPROVED …' line — a draft is not "
                            "an approval.")
    heads = list(re.finditer(r"^## (\d+)\. (.+)$", md, re.M))
    out: dict = {"approval": status, "source": str(f), "midroll_id": None}
    for i, h in enumerate(heads):
        k = int(h.group(1))
        if k not in SECTIONS:
            continue
        body = md[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(md)]
        paras = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
        first = paras[0] if paras else ""
        if first.startswith(("(", "-", "#", ">")):
            first = ""
        if "\n" in first:
            raise NotComposable(f"{f.name} section {k} ({SECTIONS[k]}): the words must be "
                                "ONE paragraph — it runs over several lines.")
        out[SECTIONS[k]] = first
        if k == 4:
            m = re.search(r"\b(L\d)\b", h.group(2))
            out["midroll_id"] = m.group(1) if m else None
    missing = [n for k, n in SECTIONS.items()
               if not out.get(n) and n not in ("handover", "midroll")]
    if missing:
        raise NotComposable(f"{f.name} is missing words for: {', '.join(missing)}.")
    if out["rg"] != RG_LINE:
        raise NotComposable(f"{f.name} section 7: the responsible-gambling line is not the "
                            f"locked line word for word. Locked: {RG_LINE!r}")
    if out["close"] != CLOSE:
        raise NotComposable(
            f"{f.name} section 5: the close is not the standing close. A different close "
            "is a new kind of line and goes to Hugh (A8) — not composed here.")
    return out


def pool_line(ep_number: int, pp: pathlib.Path = None) -> tuple[str, str]:
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
    # THE RULE IS "THE LINE UNUSED LONGEST" (Jodie, 9 Nov 2026), across PP-EP AND
    # PP-GH — it replaced `L[N mod 10]`. One definition, in render_ready, used by the
    # solo commission too. The path need not exist: a PP-EP number is its position.
    scripts = REPO / ".claude/skills/pp-episode-production/scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from render_ready import pool_line_unused_longest    # noqa: PLC0415
    lid, _text, _last = pool_line_unused_longest(str((pp or PP) / f"PP-EP{ep_number:02d}"))
    return lid, lines[lid]


def pool_lines() -> dict:
    """{'L0': text, …} — the pool's CURRENT wording, by its own documented parser."""
    txt = (REPO / "docs/midroll-line-pool.md").read_text(encoding="utf-8")
    return dict(re.findall(r"^### (L\d)\n> (.+?)$", txt.replace("\r\n", "\n"), re.M))


def midroll_for(ep_number: int, words: dict,
                pp: pathlib.Path = None) -> tuple[str, str, str]:
    """(line id, text, how it was chosen) — the midroll Jodie APPROVED, checked.

    🔴 THE APPROVED LINE WINS, BECAUSE SHE READ IT (she asked to see the midroll on
    EP56). But it must be one of the ten, VERBATIM, and it must not repeat a line
    inside the nine-episode window — the window, not the draw, is the rule's purpose.
    If it differs from the pool's own draw ("unused longest") that is reported, not
    refused: in a batch the words are approved before the numbers exist, so the draw
    the writer saw can move. A section with no text but an `Ln` in its heading
    (EP55's shape) means that line's pool wording. No line at all → the draw.
    """
    pool = pool_lines()
    pp = pp or PP
    drawn, drawn_text = pool_line(ep_number, pp)
    text = words.get("midroll") or ""
    if not text and words.get("midroll_id"):
        lid = words["midroll_id"]
        if lid not in pool:
            raise NotComposable(f"the approved words name midroll line {lid}, which is "
                                "not in the pool.")
        text = pool[lid]
    if not text:
        return drawn, drawn_text, "the pool's draw (the line unused longest)"
    flat = " ".join(text.split())
    lid = next((k for k, v in pool.items() if " ".join(v.split()) == flat), None)
    if lid is None:
        raise NotComposable(
            "the approved midroll is not one of the pool's ten lines word for word. "
            "The midroll is lifted from the pool, never re-voiced.")
    scripts = REPO / ".claude/skills/pp-episode-production/scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    # The window is checked BY LINE, not by exact wording: the pool was re-worded on
    # 11 Nov 2026 (cadence out), so an earlier use of the same line carries the OLD
    # words and an exact-text match cannot see it. `lines_in_folder` knows every
    # wording a line has had — the same reading the pool's draw uses.
    from render_ready import (midroll_window, lines_in_folder,    # noqa: PLC0415
                              pool_wordings)
    wordings = pool_wordings()
    clash = None
    for _pos, f in midroll_window(str(ep_paths.episode_dir(ep_number, pp))):
        folder = os.path.dirname(os.path.dirname(f))
        if lid in lines_in_folder(folder, wordings):
            clash = os.path.basename(folder)
            break
    if clash:
        raise NotComposable(
            f"the approved midroll {lid} was already used by {clash}, inside the "
            f"nine-episode window. The pool's draw for this episode is {drawn}.")
    how = ("the approved line; it is the pool's draw" if lid == drawn else
           f"the approved line; the pool's draw today would be {drawn} — {lid} is "
           "still clear of the nine-episode window")
    return lid, pool[lid], how


def pieces(ep_number: int, words: dict, pp: pathlib.Path = None) -> list[dict]:
    """Every Gordon-as-Gordon piece, in spoken order, with where it goes and why.

    `where` is a PLACEMENT RULE, not a position. `place()` resolves it against the
    dialogue; nothing here knows how many turns this episode has. Every per-episode
    word comes from `words` (see `approved_words`).
    """
    lid, midroll, how = midroll_for(ep_number, words, pp)
    appr = f"APPROVED — {words['approval']}"
    return [
        {"id": "open", "name": "the open", "text": words["open"],
         "where": "before-dialogue", "provenance": appr},
        {"id": "cta", "name": "early e-book CTA", "text": words["cta"],
         "where": "after-host-turn-1",
         "provenance": f"{appr} — per-episode wording inside the approved shape"},
        {"id": "midroll", "name": f"midroll invitation {lid}", "text": midroll,
         "where": "midpoint-handover-into-host",
         "provenance": f"VERBATIM from the pool of ten ({lid}): {how}"},
        {"id": "close", "name": "the close", "text": CLOSE, "where": "after-dialogue",
         "provenance": "the standing close, approved by Hugh 20 Sep 2026 (A8), reused"},
        {"id": "outro", "name": "outro: wind-down and the e-book pointer",
         "text": words["outro"], "where": "after-dialogue",
         "provenance": f"{appr} — per-episode wording inside the approved shape"},
        {"id": "rg", "name": "responsible gambling", "text": RG_LINE,
         "where": "after-dialogue",
         "provenance": "WORD-FOR-WORD LOCKED, never varied"},
        {"id": "signoff", "name": "outro: sign-off", "text": words["signoff"],
         "where": "after-dialogue",
         "provenance": f"{appr} — a PATTERN re-voiced each episode, never a previous "
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


def place(turns: list[dict], host: str, ep_number: int, words: dict,
          pp: pathlib.Path = None) -> list[dict]:
    """The render's segments, in order: every furniture piece and every host turn.

    Returns the manifest — what segment 1, 2, 3 … of the BB render will contain. It is
    the thing `interleave` needs in order to know which silence it is looking at, and
    it is written out beside the script for exactly that reason. Each furniture
    segment carries its `where` — `twoway_interleave` refuses a manifest without it.
    """
    spoken = [t for t in turns if t["speaker"] != "NARR"]
    host_turns = [t for t in spoken if t["speaker"] == host]
    if not host_turns:
        raise NotComposable(f"no turns for the host {host}.")
    mid_turn = midpoint_handover(turns, host)
    by_where: dict[str, list[dict]] = {}
    for p in pieces(ep_number, words, pp):
        by_where.setdefault(p["where"], []).append(p)

    def furn(p: dict) -> dict:
        return {"kind": "furniture", "id": p["id"], "name": p["name"],
                "text": p["text"], "provenance": p["provenance"], "turn": None,
                "where": p["where"]}

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
        "# THE WORDS ARE LIFTED BY CODE from docs/" + WORDS_FILE.format(n=ep_number)
        + ", never retyped.",
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
    # 🔴 THE SIGN-OFF CHECKED IS THE ONE PLACED IN THIS MANIFEST (13 Nov 2026). It used
    # to test the module constant — EP49's words — so for every later episode it
    # checked the wrong line and failed on EP49's own folder.
    signoff = next((s["text"] for s in manifest if s.get("kind") == "furniture" and
                    (s.get("id") == "signoff" or "sign-off" in s.get("name", ""))), None)
    for p in sorted(pp.glob("PP-EP*/docs/spoken-words*.txt")) if signoff else []:
        if p.parent == ep_dir / "docs":
            continue
        try:
            tail = " ".join(p.read_text(encoding="utf-8", errors="replace").split()[-28:])
        except OSError:
            continue
        if signoff in tail:
            out.append(f"the sign-off repeats {p.parts[-3]} VERBATIM — the outro "
                       f"standard forbids it.")
    return out


# ───────────────────────────────────────────────────────────────── the step ──

def build(ep_number: int, pp: pathlib.Path = PP, write: bool = False,
          force: bool = False) -> dict:
    ep_dir = ep_paths.episode_dir(ep_number, pp)
    docs = ep_dir / "docs"
    tj = docs / "turns.json"
    if not tj.is_file():
        raise NotComposable(f"no {tj} — run twoway_split.py first; this step composes "
                            "the dialogue it wrote and never re-derives it.")
    words = approved_words(docs, ep_number)
    turns = json.loads(tj.read_text(encoding="utf-8"))["turns"]
    # 🔒 The host reads the READING, not the raw turns: exactly the episode's sanctioned
    # substitutions applied and proved (EP56's dropped web addresses, 11 Nov 2026). One
    # definition, in twoway_split — without this line the composed script would put the
    # cuts straight back. turns.json itself stays the article.
    turns = ts.reading_turns(turns, ts.load_substitutions(docs))

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

    manifest = place(turns, host, ep_number, words, pp)
    script = compose(manifest)
    bad = problems(manifest, ep_dir, pp)

    # 🔴 THE GUEST'S SCRIPT: the splitter's own, with Steve's approved handover in front
    # (A14, "Thanks, Gordon."), same paragraph. Written here so ONE step writes both
    # render scripts from the one approved file.
    guests = [c for c in (epj.get("speakers") or {}) if c != host]
    if len(guests) != 1:
        raise NotComposable(f"episode.json names {len(guests)} guest speakers; a two-way "
                            "has exactly one.")
    guest = guests[0]
    split = ts.build(ep_number, pp, write=False)
    if split["scripts"].get(host) != f"\n\n{BREAK}\n\n".join(
            s["text"] for s in manifest if s["kind"] == "turn") + "\n":
        bad.append("the host's reading segments are not twoway_split's script for "
                   f"{host} — turns.json and the capture disagree. Re-split first.")
    handover = words.get("handover") or ""
    guest_script = (handover + " " if handover else "") + split["scripts"][guest]

    mid = next(s for s in manifest if s["id"] == "midroll")
    lid = mid["name"].split()[-1]
    after = manifest[mid["n"] - 2]

    print(f"episode    : {ep_dir.name}")
    print(f"words      : {words['source']}")
    print(f"host       : {host}  (the furniture is the host's and no one else's)")
    print(f"guest      : {guest}  (handover: {handover or 'none'})")
    print(f"midroll    : {mid['provenance']}")
    print(f"placed at  : segment {mid['n']}, the handover into turn "
          f"{manifest[mid['n']]['turn']} — after {after['name']}")
    print()
    print(f"{'seg':>3}  {'kind':<9} {'words':>5}  {'est':>6}  what")
    total = 0
    for s in manifest:
        est = s["words"] / 2.6
        total += est
        print(f"{s['n']:>3}  {s['kind']:<9} {s['words']:>5}  {est:>5.1f}s  {s['name']}")
    n_words = sum(s["words"] for s in manifest)
    furn_w = sum(s["words"] for s in manifest if s["kind"] == "furniture")
    print(f"\n{len(manifest)} segments, {len(manifest) - 1} breaks of six seconds")
    print(f"{n_words:,} spoken words ({furn_w} furniture, {n_words - furn_w:,} reading), "
          f"~{total / 60:.1f} min at 2.6 words/s before breaks")
    print(f"+ {(len(manifest) - 1) * 6 / 60:.1f} min of breaks cut out at assembly")

    if bad:
        print("\nNOT WRITTEN — the furniture does not pass its own checks:")
        for x in bad:
            print("  ! " + x)
        raise NotComposable(f"{len(bad)} problem(s) in the furniture.")

    out = {f"furniture-{host}.txt": furniture_file(ep_number, manifest),
           f"spoken-words-{host}.txt": script,
           f"spoken-words-{guest}.txt": guest_script,
           MANIFEST.format(code=host): json.dumps(
               {"episode": f"EP{ep_number}", "host": host, "midroll_line_id": lid,
                "approval": words["approval"], "words_file": WORDS_FILE.format(n=ep_number),
                "guest_handover": {"speaker": guest, "text": handover},
                "segments": [{k: v for k, v in s.items() if k != "text"}
                             for s in manifest]},
               indent=2, ensure_ascii=False) + "\n"}

    if write:
        # 🔴 A COMPOSED RENDER SCRIPT IS NEVER OVERWRITTEN SILENTLY: it may be the one
        # Jodie pasted. "Composed" = the manifest is already beside it (the mark only this
        # step writes). The splitter's dialogue-only scripts, written before this step
        # ever ran, are not composed and were never pasted, so they are replaced freely.
        # Identical → left alone; composed and different → halt unless --force.
        composed = (docs / MANIFEST.format(code=host)).is_file()
        changed = [n for n, b in out.items() if composed and (docs / n).is_file()
                   and (docs / n).read_text(encoding="utf-8") != b
                   and n.startswith("spoken-words-")]
        if changed and not force:
            raise NotComposable(
                f"{', '.join(changed)} already exist and would change. They may be the "
                "scripts that were pasted into HeyGen. Pass --force only if the words "
                "were re-approved and no render has been made from the old ones.")
        for name, body in out.items():
            if (docs / name).is_file() and (docs / name).read_text(encoding="utf-8") == body:
                print(f"UNCHANGED {docs / name}")
                continue
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
            "line_id": lid, "out": out, "guest": guest, "guest_script": guest_script,
            "words": words}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="overwrite render scripts that already exist and differ")
    a = ap.parse_args()
    try:
        build(a.ep_number, pathlib.Path(a.pp), write=a.write, force=a.force)
    except (NotComposable, ts.Unsplittable) as e:   # Unsplittable: a bad substitution
        print(f"\nHALT: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
