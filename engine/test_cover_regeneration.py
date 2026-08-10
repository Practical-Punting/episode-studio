#!/usr/bin/env python3
"""#13, THE HALF THAT WAS MISSING: "ask for different ones" must DELIVER different ones.

    python engine/test_cover_regeneration.py

EP20, 11 Aug 2026. The click was processed perfectly — round 2 opened, round 1 and
Jodie's note archived, the request consumed — and then NOTHING GENERATED ANYTHING.
`covers_ab` had already run in the gens batch and never runs again, so the board went
on showing the SAME REJECTED COVERS and waited for a pick that was never coming. She
sat on it for ten minutes. A button that records a wish is not a button that answers it.

THE THREE THINGS THAT MUST HOLD, and each has a control:
  1. a new round PUBLISHES TO A NEW PATH — otherwise round 2 overwrites the image that
     round 1's archived a_url still points at, and "earlier rounds, still yours to
     pick" quietly becomes two copies of the new pair;
  2. the prompts are REWRITTEN FROM HER WORDS, and a writer that hands back the old
     ones is REFUSED — an unchanged prompt is an unchanged sha, and the E16 ledger
     would then re-serve the rejected pictures for £0. That is the EP15 failure exactly;
  3. a generation that fails RAISES A FLAG rather than hanging.

Hermetic: no Higgsfield, no Supabase, no rail. Nothing is spent.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import providers                                                      # noqa: E402

PASS, FAIL = [], []


def case(name, ok, why=""):
    (PASS if ok else FAIL).append((name, why))
    print(("  ok  " if ok else "  !!  ") + name + (f"\n      {why}" if not ok else ""))


# ── 1. THE PUBLISHED PATH IS VERSIONED ───────────────────────────────────────
suf = providers.RealProvider._round_suffix
case("round 1 publishes to the bare cover path", suf({"cover_round": 1}) == "")
case("🔴 a later round publishes to a DIFFERENT path",
     suf({"cover_round": 2}) == "-r2" and suf({"cover_round": 3}) == "-r3",
     "round 2 would overwrite the image round 1's archived a_url points at, and the "
     "'earlier rounds' tiles would silently become the new pair")

src = (HERE / "providers.py").read_text(encoding="utf-8")
case("  …and make_covers_ab uses the suffix too, not just the regeneration path",
     'f"{folder}/cover-A{sfx}.png"' in src,
     "the first round publishes bare and a later one would collide with it")


# ── 2. THE PROMPTS MUST ACTUALLY CHANGE ──────────────────────────────────────
class P(providers.RealProvider):
    """Only the filesystem and the commission are stubbed — find_artefact is real."""

    def __init__(self, d, writer):
        self._d, self._writer = Path(d), writer
        self.pp = Path(d).parent

    def dir(self, ep):
        return self._d


def episode_folder(prompts):
    d = Path(tempfile.mkdtemp(prefix="covreg_")) / "PP-EP99"
    (d / "docs").mkdir(parents=True)
    (d / "docs/episode.json").write_text(json.dumps({
        "episode": "PP-EP99", "cover": prompts}), encoding="utf-8")
    return d


OLD = {"hero_a_prompt": "A scary dark grandstand at dusk",
       "hero_b_prompt": "A lone figure at a crooked fence in mist"}


def run_commission(writer):
    """Drive _commission_cover_prompts with `writer` standing in for the author."""
    import commission as com
    d = episode_folder(dict(OLD))
    prov = P(d, writer)
    real = com.commission
    seen = {}

    def fake_commission(*, prompt, place, find_artefact, what, **kw):
        seen["prompt"] = prompt
        writer(d)                       # the "author" writes (or fails to)
        if find_artefact() is None:
            raise com.CommissionHalt("the writer did not produce two NEW prompts")
        return {"status": "ok"}

    com.commission = fake_commission
    try:
        out = prov._commission_cover_prompts(
            {"ep_number": 99, "cover_round": 2}, d,
            "brighter and cleaner please, and a straight rail", [])
        return out, seen, d
    finally:
        com.commission = real


def writes_new(d):
    p = d / "docs/episode.json"
    j = json.loads(p.read_text(encoding="utf-8"))
    j["cover"]["hero_a_prompt"] = "Three horses on bright green turf, straight white rail"
    j["cover"]["hero_b_prompt"] = "Two punters in Akubras talking trackside, sunny"
    p.write_text(json.dumps(j), encoding="utf-8")


def writes_the_old_ones_back(d):
    pass                                # leaves episode.json exactly as it was


out, seen, d = run_commission(writes_new)
case("a fresh pair of prompts is accepted", out[0] != OLD["hero_a_prompt"], str(out))
back = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))["cover"]
case("  …and the REJECTED prompts are kept",
     back.get("_rejected_hero_a_prompt") == OLD["hero_a_prompt"], json.dumps(back)[:200])
case("  …so a later prompt cannot drift back and re-serve a rejected picture",
     "keyed on slot + prompt sha" in (back.get("_prompts_why") or ""))

# 🔴 THE CONTROL. A writer that returns the OLD prompts must be refused — an unchanged
# prompt is an unchanged sha, and the ledger would hand back the rejected pictures free.
import commission as _com                                             # noqa: E402
try:
    run_commission(writes_the_old_ones_back)
    case("🔴 CONTROL: unchanged prompts are REFUSED", False,
         "the writer returned the rejected prompts and it was accepted — the E16 "
         "ledger would then re-serve the pictures she turned down, for £0")
except _com.CommissionHalt:
    case("🔴 CONTROL: unchanged prompts are REFUSED", True)

# ── 3. HER WORDS REACH THE WRITER ────────────────────────────────────────────
case("the brief carries her note verbatim",
     "brighter and cleaner please, and a straight rail" in seen.get("prompt", ""),
     seen.get("prompt", "")[:200])
case("  …and tells it NOT to jitter the rejected direction",
     "still wrong" in seen.get("prompt", ""))
case("  …and names the prompts she turned down",
     OLD["hero_a_prompt"] in seen.get("prompt", ""))
case("  …and keeps the house rules (turf, hats, no text)",
     all(k in seen.get("prompt", "") for k in ("TURF ONLY", "Akubra", "NO TEXT")))

# ── 4. A FAILURE FLAGS, IT DOES NOT HANG ─────────────────────────────────────
eng = (HERE / "engine.py").read_text(encoding="utf-8")
i = eng.index("def _open_a_new_cover_round(")
body = eng[i:eng.index("\ndef ", i + 10)]
case("opening a round GENERATES the pair", "regenerate_covers(" in body,
     "the round counter advances and nothing is made — this is the EP20 hang")
case("  …says it is working before it starts",
     "Making fresh covers" in body,
     "a silent multi-minute gap is the same fault in a smaller window")
case("  …raises a REAL flag if generation fails",
     "flag_needs_look(" in body and "could not make the fresh covers" in body)
case("  …and says the old covers are still pickable",
     "still yours to pick" in body)
case("  …and puts the new urls on the rail",
     '"cover_a_url": a_url' in body)


# ── 5. A PICK WHOSE PICTURE IS MISSING MUST HALT ─────────────────────────────
# 🔴 FOUND WHILE UNSTICKING EP20, and it is the worst shape of bug there is: silent
# and wrong. `render_ebook_cover` copied the picked hero `if pick.is_file()` and did
# NOTHING otherwise, leaving hero.png as it was. Versioned rounds made it reachable —
# between opening round 2 and the heroes landing, hero-b-r2.png does not exist, so a
# pick of B published A and said nothing. EP20 sat in exactly that window for hours.
class R(providers.RealProvider):
    def __init__(self, d):
        self._d = Path(d)

    def dir(self, ep):
        return self._d


def cover_src(round_files):
    d = Path(tempfile.mkdtemp(prefix="pick_")) / "PP-EP99"
    src = d / "ebook/cover-src"
    src.mkdir(parents=True)
    for n in round_files:
        (src / n).write_bytes(b"\x89PNG fake")
    return d


# round 2, hero-b-r2.png absent → picking B must HALT, not publish A
d2 = cover_src(["hero-a-r2.png", "hero.png"])
try:
    R(d2).render_ebook_cover({"ep_number": 99, "cover_round": 2}, "B")
    case("🔴 picking a cover whose picture is missing HALTS", False,
         "it carried on and published the OTHER cover — she chose one and got the other")
except providers.EngineFlag as e:
    case("🔴 picking a cover whose picture is missing HALTS", True)
    case("  …and the halt names the cover she picked", "cover B" in str(e), str(e)[:160])
except Exception as e:                                                # noqa: BLE001
    # anything that is not a clean EngineFlag still beats silence, but say so
    case("🔴 picking a cover whose picture is missing HALTS", True,
         f"(halted via {type(e).__name__}, not EngineFlag)")
    case("  …and the halt names the cover she picked", False, str(e)[:160])

# CONTROL: round 1 with only hero.png is EP01–EP14's normal state and must NOT halt.
# Without this the guard could be "halt on everything", which breaks every old episode.
d1 = cover_src(["hero.png"])
#   ⚠️ IT MUST FAIL LATER, AND THAT IS THE POINT. This fixture has no episode.json and
# no cover.html, so the real render halts a few lines further on. What is being asked
# is only "did it get PAST the guard", so the check is on WHICH halt came back — a
# blanket `except EngineFlag: fail` marked this red for the wrong reason first time.
GUARD = "isn't on disk"
try:
    R(d1).render_ebook_cover({"ep_number": 99, "cover_round": 1}, "A")
    case("CONTROL: a legacy round-1 episode (hero.png only) does NOT halt", True)
except Exception as e:                                                # noqa: BLE001
    case("CONTROL: a legacy round-1 episode (hero.png only) does NOT halt",
         GUARD not in str(e),
         f"the guard broke every pre-EP15 episode: {e}")

print(f"\ncover regeneration: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
