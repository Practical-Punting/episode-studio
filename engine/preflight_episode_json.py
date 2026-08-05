"""E26 — diff an episode.json against the last episodes that BUILT CLEANLY, before the
build starts, instead of discovering each fault eighteen steps in.

WHAT IT COST NOT TO HAVE THIS (EP15, 4 Aug 2026)
------------------------------------------------
SEVEN HALTS. ONE FILE. ONE EPISODE — `default_hold`, the `ask` TYPE, card-beats-on-WIDE,
the `END` id, `build.standing`, `midroll.dur`, `thumbnail.l1`. **Every one found by
running into it**, hours apart, each costing a flag a human had to clear. **Every one a
convention that EP11–EP14 all followed and that nothing anywhere states.**

*"Every previous episode put some card beats on WIDE; this one puts none"* is a sentence
a diff could have produced before a credit was spent.

TWO REFERENCES, NEVER ONE
-------------------------
A rule inferred from a SINGLE sample was wrong on all three axes when it was tried on
panel-push cell counts. **A key is only a convention if BOTH references carry it, with
the same type.** Anything only one reference has is dropped, silently and on purpose.

THE HARD PART IS BEING QUIET
----------------------------
A naive key diff of EP15 against EP13+EP14 produces **17 findings, and 5 are comment
fields**. A guard everyone ignores is worse than no guard, so:

  · `_`-prefixed keys are NOT conventions. They are notes to a human. Skipped entirely.
  · A missing WHOLE SUBTREE (`thumbnail.*` absent when both references have it) is a
    different animal from a missing leaf under a parent that is present. The first is
    almost always real — it was EP15's genuine finding. The second is usually a tuning
    value whose code default already matches, and **twelve of those were correctly left
    alone.** They are reported separately and never as errors.
  · **A value you do not understand is not made safer by copying it.** This tool never
    tells anyone to copy a value. It says what differs and who has to decide.

WHAT THE KEY/TYPE DIFF CANNOT SEE — and why there are two more passes
---------------------------------------------------------------------
Measured against EP15's seven: **the key/type diff catches five.** The other two are a
different kind of fault entirely and each gets its own pass:

  · REFERENTIAL — `build.standing.endcard: "ENDCARD"` when the card is `END`. The key is
    present and the type is right; the NAME POINTS AT NOTHING. *(Fault #0a: an id is a
    promise, a name is a guess.)*
  · SHAPE — no card beat framed WIDE. No key is missing; the SPREAD of values is wrong.

Usage:
    python preflight_episode_json.py <episode.json> [ref.json ref.json]
    python preflight_episode_json.py <episode.json> --refs 13 14
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PP_VIDEOS = Path(r"G:\My Drive\PP Videos")


# --------------------------------------------------------------------------- paths
def ep_dir(n: int, root: Path = PP_VIDEOS) -> Path:
    """Resolve an episode folder BY NUMBER, anchored.

    NOT `glob(f"PP-EP{n}*")` — that matches PP-EP10 for n=1 and PP-EP98 for n=9, and it
    made two outro audits confidently wrong (E18). And not a bare stem either: published
    episodes are RENAMED (`PP-EP13-The-Ratings-Game-Part-1`), so the stem is not there.
    """
    pat = re.compile(rf"^PP-EP{int(n):02d}(?:$|[-_])")
    hits = sorted(d for d in root.iterdir() if d.is_dir() and pat.match(d.name))
    if len(hits) != 1:
        raise LookupError(
            f"episode {n}: expected exactly one folder matching PP-EP{int(n):02d}, "
            f"found {[h.name for h in hits] or 'none'}")
    return hits[0]


# --------------------------------------------------------------------------- shapes
def key_types(o, pre: str = "", out: dict | None = None) -> dict[str, set[str]]:
    """Every key path -> the SET of types observed there.

    A SET, and every list item walked — not the first one. ⚠️ THE FIRST VERSION TOOK
    THE FIRST ITEM AND IT CRIED WOLF TWICE ON REAL SHIPPED EPISODES:

      · `beats[].card` is null on beats that carry no card. EP14's FIRST beat has none,
        so the whole field read as NoneType and the tool announced a type change against
        two episodes that were fine. **An OPTIONAL field is not a type mismatch.**
      · `ebook.omit_paragraphs` is `[]` in both references and populated in EP15, so a
        first-item read made `list[]` and `list[str]` look like different types. **An
        empty list is a list of anything.**

    Both were caught by the "does not cry wolf" tests rather than by review, which is
    the argument for having them: a lint nobody trusts gets switched off, and these two
    would have fired on every episode from now on.

    A list records `"list"` at its own path and recurses into `<path>[]`, so a value
    that should be a list and is a STRING still shows as a clean mismatch — which is
    E25's `ask` halt, where the old guard was `len(ask) < 2` and any two-character
    string passed it.
    """
    out = {} if out is None else out
    if isinstance(o, dict):
        for k, v in o.items():
            if k.startswith("_"):
                continue                      # a note to a human, not a convention
            key_types(v, f"{pre}.{k}" if pre else k, out)
    elif isinstance(o, list):
        out.setdefault(pre, set()).add("list")
        for item in o:
            key_types(item, f"{pre}[]", out)
    else:
        out.setdefault(pre, set()).add(type(o).__name__)
    return out


def _compatible(a: set[str], b: set[str]) -> bool:
    """Two type sets agree when they share any type once None is set aside.

    None means "optional here", never "a different type". If a field is null in every
    observed instance on one side, there is nothing to contradict.
    """
    a2, b2 = a - {"NoneType"}, b - {"NoneType"}
    return not a2 or not b2 or bool(a2 & b2)


def conventions(ref_a: dict, ref_b: dict) -> dict[str, set[str]]:
    """A key is a convention only when BOTH references carry it at COMPATIBLE types."""
    a, b = key_types(ref_a), key_types(ref_b)
    return {k: a[k] | b[k] for k in set(a) & set(b) if _compatible(a[k], b[k])}


def _fmt(t: set[str]) -> str:
    return "/".join(sorted(t - {"NoneType"}) or ["null"])


def _prefixes(key: str) -> list[str]:
    """'build.midroll.dur' -> ['build', 'build.midroll', 'build.midroll.dur']"""
    parts, out, cur = key.split("."), [], ""
    for p in parts:
        cur = f"{cur}.{p}" if cur else p
        out.append(cur)
    return out


def _subtree_missing(missing: set[str], present: set[str]) -> tuple[dict, list]:
    """Split missing keys into WHOLE SUBTREES and lone leaves — AT ANY DEPTH.

    ⚠️ THE FIRST VERSION OF THIS ONLY LOOKED AT THE FIRST PATH SEGMENT, and it was
    wrong on the real data: `build.standing` vanishing entirely — one of EP15's seven
    halts — has the root `build`, which IS present, so it was demoted to a lone leaf
    and would have been reported as "worth an eye". A missing BLOCK is never that.

    The question is not "is the top-level key present" but **"where does the absence
    START"**: the shortest ancestor of a missing key that is itself absent everywhere.

        build.standing.title   -> 'build' present, 'build.standing' absent -> BLOCK
        build.mcu_zoom         -> 'build' present, so the absence starts at the leaf
                                  -> a tuning value, worth knowing, never a blocker
    """
    present_prefixes = {p for k in present for p in _prefixes(k)}
    blocks: dict[str, list[str]] = {}
    lone: list[str] = []
    for k in sorted(missing):
        root = next((p for p in _prefixes(k) if p not in present_prefixes), k)
        if root == k:
            lone.append(k)                     # the absence starts at the leaf itself
        else:
            blocks.setdefault(root, []).append(k)
    return blocks, lone


# ----------------------------------------------------------------- referential pass
def _card_ids(j: dict) -> set[str]:
    return {c.get("id") for c in (j.get("cards") or []) if c.get("id")}


def _beat_ns(j: dict) -> set[int]:
    return {b.get("n") for b in (j.get("beats") or []) if isinstance(b.get("n"), int)}


def check_references(j: dict) -> list[str]:
    """Every id this file names must exist. THIS IS THE `END` HALT.

    `build.standing.endcard` said "ENDCARD"; the card was "END". Present, right type,
    pointing at nothing — and it surfaced at assembly, long after the money was spent.
    """
    problems, ids, beats = [], _card_ids(j), _beat_ns(j)
    build = j.get("build") or {}

    for role, cid in (build.get("standing") or {}).items():
        if cid not in ids:
            problems.append(
                f"build.standing.{role} names card {cid!r}, but there is no card with "
                f"that id. The cards are: {', '.join(sorted(ids)) or '(none)'}.")

    for f in (j.get("figures") or []):
        if f.get("card") and f["card"] not in ids:
            problems.append(f"figures[{f.get('n')}] names card {f['card']!r}, "
                            "which does not exist.")

    for b in (j.get("beats") or []):
        if b.get("card") and b["card"] not in ids:
            problems.append(f"beat {b.get('n')} names card {b['card']!r}, "
                            "which does not exist.")

    for c in (j.get("cards") or []):
        if c.get("beat") is not None and beats and c["beat"] not in beats:
            problems.append(f"card {c.get('id')!r} sits on beat {c['beat']}, but the "
                            f"beats run {min(beats)}–{max(beats)}.")

    for label, n in (("build.midroll.beat", (build.get("midroll") or {}).get("beat")),
                     ("build.endcard_beat", build.get("endcard_beat"))):
        if isinstance(n, int) and beats and n not in beats:
            problems.append(f"{label} is {n}, but the beats run "
                            f"{min(beats)}–{max(beats)}.")
    return problems


# ----------------------------------------------------------------------- shape pass
def _card_beat_framings(j: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for b in (j.get("beats") or []):
        if b.get("card"):
            f = b.get("framing")
            out[f] = out.get(f, 0) + 1
    return out


def _layouts(j: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in (j.get("cards") or []):
        if c.get("layout"):
            out[c["layout"]] = out.get(c["layout"], 0) + 1
    return out


def check_shape(j: dict, refs: list[dict]) -> list[str]:
    """Where both references show VARIETY, an episode showing none is an outlier.

    ⚠️ THIS DELIBERATELY DOES NOT ASSERT A RATIO. Jodie settled the framing on 4 Aug
    2026 having watched EP15 end to end: **a high proportion of WIDE beats is not a
    fault** — EP15 ran 14 of 24 against EP14's 8 of 25 and was approved, because a card
    beat is WIDE when its card is panel-push. So the only thing worth saying is that
    ZERO is unlike every reference. *A number reverse-engineered from one approved
    episode is that episode's arithmetic, not a rule.*
    """
    problems = []

    mine = _card_beat_framings(j)
    if refs and all(_card_beat_framings(r).get("WIDE", 0) > 0 for r in refs):
        if mine.get("WIDE", 0) == 0 and sum(mine.values()) > 0:
            problems.append(
                f"no card beat is framed WIDE ({sum(mine.values())} beats carry a card, "
                f"all {'/'.join(sorted(mine))}). Every reference episode frames some of "
                "them WIDE, because a panel-push card needs somewhere for Gordon to go. "
                "This is not a ratio rule — zero is simply unlike every episode so far.")

    ml = _layouts(j)
    if refs and all(len(_layouts(r)) > 1 for r in refs) and len(ml) == 1:
        problems.append(
            f"every card uses layout {next(iter(ml))!r}. Both reference episodes mix "
            "fullscreen and panel-push, and the mix is a written rule "
            "(PP-STANDARDS.md): 'I love how you have a mix of whole screen and on the "
            "screen with the host.'")
    return problems


# ------------------------------------------------------- keys the BUILD writes
#
# 🔴 THE PRE-FLIGHT RUNS AT `audit_inputs`, AT THE START OF A BUILD. Its reference
# episodes are FINISHED. So every key the build WRITES INTO episode.json later in
# the run is present in both references and absent from the file being judged —
# and was reported as a missing convention, as a BLOCKER, on every episode.
#
# FOUND ON EP16, 5 Aug 2026, the first time this was ever run on a genuinely
# script-time file. Until then it had only been measured against EP14 and EP15
# AS SHIPPED, both of which already carried these keys — written hours earlier by
# the very build stage that comes after this check. 16/16 green, and every
# fixture came from a lifecycle stage the guard will never encounter.
#
# ⚠️ THIS IS NOT A LIST SOMEBODY MUST REMEMBER TO UPDATE. `test_preflight_build_
# written.py` greps the engine and the skill for `build[...] = ` assignments and
# FAILS if any key it finds is missing here. That is the difference between a
# convention and a guard: assert_standing_assets() knew a list too, and the
# e-book cover was not on it.
BUILD_WRITTEN_KEYS = {
    # derive_card_timings.py: "Derive card leads + midroll.at FROM the WhisperX
    # SRT — never from estimates." Neither can exist before heygen_download.
    "build.leads",
    "build.midroll.at",
}


def _is_build_written(key: str) -> bool:
    """True if this key (or its parent block) is written BY the build, not authored."""
    return any(key == k or key.startswith(k + ".") for k in BUILD_WRITTEN_KEYS)


# -------------------------------------------------------------------------- report
def preflight(j: dict, refs: list[dict]) -> dict:
    """Returns {'must': [...], 'worth': [...], 'ok': bool}. `must` is halt-worthy."""
    must: list[str] = []
    worth: list[str] = []

    must += check_references(j)
    must += check_shape(j, refs)

    if len(refs) >= 2:
        # Drop the build-written keys from the CONVENTION side: they are present in
        # every finished episode and absent from every episode this check will ever
        # actually see. Judging an author for not having them is judging them for
        # not having run the build yet.
        conv = {k: v for k, v in conventions(refs[0], refs[1]).items()
                if not _is_build_written(k)}
        mine = key_types(j)

        wrong = sorted(k for k in set(conv) & set(mine)
                       if not _compatible(mine[k], conv[k]))
        for k in wrong:
            must.append(f"{k} is {_fmt(mine[k])}, but both reference episodes have it "
                        f"as {_fmt(conv[k])}.")

        missing = set(conv) - set(mine)
        blocks, lone = _subtree_missing(missing, set(mine))
        for root, keys in sorted(blocks.items()):
            must.append(f"the whole {root!r} block is absent — both reference episodes "
                        f"have it ({len(keys)} keys, e.g. "
                        f"{', '.join(sorted(keys)[:3])}).")
        if lone:
            worth.append(
                f"{len(lone)} key(s) both references set are not set here. That is "
                "often FINE — the code default may already be what the references "
                "spell out, and a value you do not understand is not made safer by "
                "copying it. Worth an eye, never a blocker:\n      " + "\n      ".join(
                    f"{k}  ({_fmt(conv[k])})" for k in lone))

    return {"must": must, "worth": worth, "ok": not must}


def format_report(res: dict, ep_name: str, ref_names: list[str]) -> str:
    out = [f"episode.json pre-flight — {ep_name}",
           f"  measured against: {', '.join(ref_names) or '(no references)'}"]
    if res["must"]:
        out.append("")
        out.append(f"  {len(res['must'])} thing(s) that will cost a halt later:")
        out += [f"    · {m}" for m in res["must"]]
    if res["worth"]:
        out.append("")
        out.append("  worth knowing:")
        out += [f"    · {w}" for w in res["worth"]]
    if res["ok"] and not res["worth"]:
        out.append("  nothing differs from the reference episodes.")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: preflight_episode_json.py <episode.json> [--refs N N | ref.json ...]")
        return 2
    target = Path(argv[1])
    j = json.loads(target.read_text(encoding="utf-8"))

    refs, names = [], []
    if "--refs" in argv:
        for n in argv[argv.index("--refs") + 1:]:
            p = ep_dir(int(n)) / "docs/episode.json"
            refs.append(json.loads(p.read_text(encoding="utf-8")))
            names.append(p.parent.parent.name)
    else:
        for a in argv[2:]:
            p = Path(a)
            refs.append(json.loads(p.read_text(encoding="utf-8")))
            names.append(p.parent.parent.name)

    res = preflight(j, refs)
    print(format_report(res, target.parent.parent.name, names))
    return 1 if res["must"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
