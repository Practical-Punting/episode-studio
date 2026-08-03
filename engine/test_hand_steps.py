#!/usr/bin/env python3
"""The five hand-steps (A2, A3, A4, A5, A7) — proved by the bad build each refuses.

B1, and the lesson from this morning's own bug: counting calls is not enough.
Assert what the caller RECEIVES — and for A7, assert the bytes of the artefact a
viewer actually gets, not the code path that chose it.

Nothing here touches the network, the live rail, or a running engine.
"""
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import providers                                                   # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                              # noqa: BLE001
        pass

PASS, FAIL = [], []


def episode_dir(n):
    """Find an episode folder by NUMBER, not by exact name.

    ⚠️ These tests hard-coded `PP Videos\\PP-EP13` and broke the moment the stage-8
    close-out renamed it to PP-EP13-The-Ratings-Game-Part-1 — which is a rename the
    standard REQUIRES on every published episode. A test that assumes a folder name
    the process is designed to change is a test with a fuse in it.
    """
    pp = Path(r"G:\My Drive\PP Videos")
    hits = sorted(p for p in pp.glob(f"PP-EP{n}*") if p.is_dir())
    if not hits:
        raise AssertionError(f"no PP-EP{n}* folder under {pp}")
    return hits[0]


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


def scratch():
    d = Path(tempfile.mkdtemp(prefix="handsteps_"))
    for sub in ("renders", "thumbnail", "ebook/cover-src", "output", "overlay/clips", "docs"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- A7 ------
def _a7_ships_aligned():
    d = scratch()
    (d / "renders/generated.srt").write_bytes(b"CONSTRUCTED - the bad one\n")
    (d / "renders/aligned.srt").write_bytes(b"ALIGNED - measured from the audio\n")
    src, why = providers._shipping_srt(d)
    dest = d / "output/EP-FINAL.srt"
    shutil.copyfile(src, dest)
    # THE ARTEFACT, not the code path: what does a viewer actually receive?
    assert dest.read_bytes() == (d / "renders/aligned.srt").read_bytes(), (
        "the shipped .srt is not byte-identical to aligned.srt — this is the exact "
        "shape of the EP13 fault, where the shipped captions matched generated.srt")
    assert dest.read_bytes() != (d / "renders/generated.srt").read_bytes(), \
        "the shipped .srt is byte-identical to the CONSTRUCTED file"


case("A7: the shipped .srt is byte-for-byte the ALIGNED one", _a7_ships_aligned)


def _a7_fallback_is_loud():
    d = scratch()
    (d / "renders/generated.srt").write_bytes(b"CONSTRUCTED\n")
    src, why = providers._shipping_srt(d)
    assert src == d / "renders/generated.srt", "should still ship something"
    assert why.startswith("!!"), f"the fallback is not loud: {why!r}"
    assert "12.32" in why or "interpolated" in why, \
        f"the warning does not say WHY the fallback is bad: {why!r}"


case("A7: falling back to the constructed SRT warns loudly", _a7_fallback_is_loud)


# ---------------------------------------------------------------- A3 ------
def _a3_stages_hero():
    d = scratch()
    (d / "ebook/cover-src/hero.png").write_bytes(b"PICKED-HERO-BYTES")
    assert not (d / "thumbnail/hero.png").exists()
    msg = providers.stage_thumbnail_hero(d)
    got = d / "thumbnail/hero.png"
    assert got.is_file(), f"the hero was NOT staged — a human would have to copy it: {msg}"
    assert got.read_bytes() == b"PICKED-HERO-BYTES", "staged the wrong bytes"


case("A3: a missing thumbnail hero is staged from the picked cover hero",
     _a3_stages_hero)


def _a3_never_overwrites():
    d = scratch()
    (d / "ebook/cover-src/hero.png").write_bytes(b"PICKED")
    (d / "thumbnail/hero.png").write_bytes(b"HAND-PLACED-CROP")
    providers.stage_thumbnail_hero(d)
    assert (d / "thumbnail/hero.png").read_bytes() == b"HAND-PLACED-CROP", (
        "an EXISTING thumbnail hero was overwritten — that is the engine overruling a "
        "human who placed a different crop on purpose")


case("A3: an existing thumbnail hero is never overwritten", _a3_never_overwrites)


def _a3_no_source_is_honest():
    d = scratch()
    msg = providers.stage_thumbnail_hero(d)
    assert not (d / "thumbnail/hero.png").exists(), "invented a hero from nowhere"
    assert "no picked cover hero" in msg, f"unclear message: {msg!r}"


case("A3: with no picked hero it says so rather than inventing one",
     _a3_no_source_is_honest)


# ---------------------------------------------------------------- A5 ------
def _a5_missing_ask_halts():
    import derive_card_timings as dct
    src = Path(dct.__file__).read_text(encoding="utf-8")
    assert "a like is what pushes it" not in src, (
        "EP12's ask phrases are STILL reachable as a default in derive_card_timings.py "
        "— on EP13 that failed safe only because those words happened to be absent from "
        "the master")
    assert "build.midroll.ask is not set" in src, \
        "there is no loud failure for a missing build.midroll.ask"


case("A5: EP12's phrases are gone and a missing ask fails loudly", _a5_missing_ask_halts)


def _a5_halts_on_real_episode_data():
    """Run the real tool against a real episode with `ask` removed."""
    import subprocess
    ep = episode_dir(13)
    if not (ep / "docs/episode.json").is_file():
        raise AssertionError("EP13 not available to test against")
    d = scratch()
    for rel in ("renders/aligned.srt", "renders/shot-map.json"):
        shutil.copyfile(ep / rel, d / rel)
    epj = json.loads((ep / "docs/episode.json").read_text(encoding="utf-8"))
    epj["build"]["midroll"].pop("ask", None)                       # the fault under test
    (d / "docs/episode.json").write_text(json.dumps(epj), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(HERE.parent /
         ".claude/skills/pp-episode-production/scripts/derive_card_timings.py"), str(d)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode != 0, "a missing build.midroll.ask did NOT fail"
    assert "build.midroll.ask is not set" in out, f"wrong message:\n{out[-400:]}"
    assert "a like is what pushes it" not in out, \
        "the EP12 default was still reached"


case("A5: a real build with no `ask` halts, naming the field",
     _a5_halts_on_real_episode_data)


# ---------------------------------------------------------------- A2 ------
def _a2_is_wired_in():
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    assert "derive_timings(" in src, \
        "derive_card_timings is still not called from the engine"
    # providers.py defines build_shot_map TWICE — MockProvider and RealProvider — so
    # take the body that actually shells out to build_shot_map.py, not the first match.
    bodies = [b.split("\n    def ", 1)[0] for b in src.split("def build_shot_map")[1:]]
    real = [b for b in bodies if "build_shot_map.py" in b]
    assert real, "could not find the real build_shot_map"
    assert "derive_timings(" in real[0], \
        "derive_timings is not called from the REAL build_shot_map, where the SRT first exists"
    doc = (HERE.parent / ".claude/skills/pp-episode-production/scripts/"
           "derive_card_timings.py").read_text(encoding="utf-8")
    assert "NOT WIRED INTO THE ENGINE" not in doc, \
        "the docstring still says it must be run by hand"


case("A2: derive_card_timings is wired into build_shot_map", _a2_is_wired_in)


def _a2_no_aligned_halts():
    d = scratch()
    (d / "renders/generated.srt").write_bytes(b"CONSTRUCTED\n")   # the bad one present
    try:
        providers.derive_timings(d)
        raise AssertionError(
            "a build with NO aligned.srt did not halt — it would silently derive every "
            "card window from the interpolated SRT, which is what put nine of EP13's "
            "cards ahead of their cue")
    except providers.EngineFlag as e:
        assert "aligned.srt" in str(e), f"the halt does not name the missing file: {e}"
        assert "12.32" in str(e) or "5.15" in str(e), \
            f"the halt does not say what the fallback costs: {e}"


case("A2: a build with no aligned.srt HALTS rather than using the constructed SRT",
     _a2_no_aligned_halts)


# ---------------------------------------------------------------- A4 ------
def _a4_missing_clip_halts():
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    assert 'if mid.get("composite") and mid.get("clip"):' not in src, (
        "the silent-drop condition is still there — a missing clip would assemble a "
        "video with no like/subscribe chip, which is what EP13 shipped")
    # Again: MockProvider defines assemble_passB too. Take the one that builds ffmpeg.
    bodies = [b.split("\n    def ", 1)[0] for b in src.split("def assemble_passB")[1:]]
    real = [b for b in bodies if "ffmpeg" in b]
    assert real, "could not find the real assemble_passB"
    assert "build.midroll.clip is not set" in real[0], \
        "the real assemble_passB does not fail loudly on a missing clip"
    assert "clip_path.is_file()" in real[0], \
        "it checks the FIELD but never that the clip FILE exists"


case("A4: a missing midroll clip halts instead of silently dropping the chip",
     _a4_missing_clip_halts)


def _a4_halts_on_real_call():
    """Drive the real assemble_passB with composite set and clip removed."""
    ep = episode_dir(13)
    if not (ep / "docs/episode.json").is_file():
        raise AssertionError("EP13 not available to test against")
    epj = json.loads((ep / "docs/episode.json").read_text(encoding="utf-8"))
    epj["build"]["midroll"].pop("clip", None)

    class FakeProv(providers.RealProvider):
        def __init__(self):                       # no env, no network
            self.name = "test"
        def dir(self, ep):
            return ep_dir
        def epjson(self, ep):
            return epj
        def _emit_graph(self, ep, which):
            return ep_dir / "renders/passB_graph.txt"
        def _clip(self, ep, cid):
            return ep_dir / "overlay/clips/x.mp4"
        def run(self, *a, **k):
            raise AssertionError("ffmpeg was reached — the halt did not fire")

    ep_dir = scratch()
    (ep_dir / "renders/passB_graph.txt").write_text("", encoding="utf-8")
    p = FakeProv()
    p.music = "music.mp3"
    try:
        p.assemble_passB({"id": "x", "ep_number": 13})
        raise AssertionError("assemble_passB did NOT halt on a missing clip")
    except providers.EngineFlag as e:
        assert "midroll.clip" in str(e), f"wrong halt: {e}"


case("A4: the real assemble_passB halts before ffmpeg when clip is missing",
     _a4_halts_on_real_call)

print(f"\nhand-steps: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
