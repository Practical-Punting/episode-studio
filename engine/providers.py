"""providers.py — the engine's external hands: real services vs mock.

The orchestrator (engine.py) never talks to tools directly; it calls a Provider.

MockProvider simulates everything (no credits, no network) — the 2a spine
acceptance ran on it. RealProvider drives the ACTUAL local toolchain (the
pp-episode-production skill's scripts: Chromium card renders, ffmpeg passes,
WeasyPrint e-book, QC). Higgsfield gens (b-roll AND the two cover heroes) go
through the Higgsfield CLI; if it's missing, every gen path falls back to an
honest flag. The HeyGen render itself stays a sacred human step — the engine
only names the project and downloads the finished master.

Spend policy (verify-before-spend): a staged asset is NEVER regenerated. The
credit estimate counts only what's actually missing, and every spend is
previewed and capped first.

Fault injection (mock only), via environment variables:
    MOCK_FAIL_STEP=<step>   that step fails EVERY attempt (shows needs_look)
    MOCK_FAIL_ONCE=<step>   that step fails its FIRST attempt (shows retry)
    MOCK_BALANCE=<n>        pretend Higgsfield balance (default 100)
    MOCK_STEP_SECS=<n>      how long each mock action takes (default 1.5)
    MOCK_BROLL_CLIPS=<n>    clips in the mock plan (default 3)
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- repo + skill locations (the 28 Jul 2026 move) ---------------------------
# CODE IN GITHUB, MEDIA ON DRIVE (Jodie, 28 Jul 2026). The build recipes, their
# assets and the b-roll registry are versioned here; PP_VIDEOS keeps only episode
# media, the Google Docs and .env (TIER 1, never in the repo).
REPO_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_DIR / ".claude/skills/pp-episode-production"

# --- qc_episode.py integrity gate (26 Jul 2026; git-backed from 28 Jul 2026) -
# qc_episode.py is the checker that judges every finished episode. It once lived
# on Drive outside version control, in TWO copies that had already drifted — the
# spare was missing three hard-fail rules (card word-cue anchoring, b-roll/card
# overlap, midroll visibility). If the wrong one ran, an episode would PASS while
# being judged by weaker rules, and nothing would say so.
#
# It is now in the repo, so the gate compares it against git HEAD rather than a
# checked-in duplicate — see engine/gitgate.py. Checked IMMEDIATELY BEFORE
# shelling out to it. No bypass flag, no environment variable. (Mock mode never
# executes this script — it has its own self_qc — so there is nothing to bypass.)
QC_SCRIPT = "qc_episode.py"
QC_REL = ".claude/skills/pp-episode-production/scripts/qc_episode.py"


class EngineFlag(Exception):
    """Raise to say: a HUMAN is needed. The engine flags needs_look with this
    message (plain English!) and does not retry — it isn't transient."""


# --- card authoring (1d, 28 Jul 2026) ----------------------------------------
# The engine used to render cards it never authored, so an episode with no card
# pages halted with "Zero card HTML pages existed — stage them, then clear this
# flag": a message that asks a browser operator to write HTML. That halt is gone.
# Missing pages are now AUTHORED from the template library; missing DATA still
# halts, which is correct — a halt over an unwritten figure is a halt a human
# should clear.
#
# Never overwrite. author_cards.py refuses to touch a page that does not carry
# its generated marker, and the furniture below is copied only when absent, so a
# hand-fixed page survives every subsequent run.
CARD_DEPS = (                       # what an authored page needs beside it
    ("assets/pp-anim.js", "pp-anim.js"),
    ("assets/assets/logo.png", "assets/logo.png"),
)
STANDING_CARDS = (                  # design §4 Layer 3 — copied, never authored
    ("assets/warranty-slide.html", "warranty-slide.html"),
    ("assets/end-card-template.html", "end-card-template.html"),
)


def stage_card_furniture(export: Path) -> list[str]:
    """Copy the standing pages and the assets an authored card needs.

    Returns what it added. Existing files are left exactly as they are — this is
    the same find-or-build policy the rest of RealProvider uses.
    """
    added = []
    for src_rel, dst_rel in (*CARD_DEPS, *STANDING_CARDS):
        src, dst = SKILL_DIR / src_rel, export / dst_rel
        if dst.exists() or not src.is_file():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        added.append(dst_rel)
    return added


def author_missing_cover(ep_dir: Path) -> str:
    """Author ebook/cover-src/cover.html when it does not exist yet.

    Same guarantees as the cards: a hand-authored page (no generated marker) is
    never touched, nothing is invented, and a DATA problem halts naming the field.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/author_cover.py"),
         str(ep_dir / "docs/episode.json"), str(ep_dir / "ebook/cover-src")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if r.returncode:
        raise EngineFlag(
            "The e-book cover could not be authored from episode.json. This is a DATA "
            "problem, not a missing-file problem — fix the field it names in "
            f"docs/episode.json, then clear this flag.\n{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def cover_canvas(page: Path) -> tuple[int, int]:
    """THE cover canvas, read from the page itself — one place, one number.

    The page used to be built 1588x2238 while render_ebook_cover() rendered it
    1600x2263, so every cover shipped with a 12px white gutter down the right
    edge and 25px along the bottom where the photo should have bled off. EP11 and
    EP12 shipped that way and are NOT being changed — they are published. What
    stops it recurring is that there is no longer a second number to disagree
    with the first: the template declares the canvas, author_cover.py writes it
    into the page, and this reads it back.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/author_cover.py"),
         "--canvas", str(page)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if r.returncode:
        raise EngineFlag(
            f"The cover page does not declare its canvas, so there is no safe size to "
            f"render it at.\n{(r.stderr or r.stdout).strip()[-500:]}")
    w, h = r.stdout.split()
    return int(w), int(h)


def author_missing_cards(ep_dir: Path) -> str:
    """Author every card page that does not exist yet. Halts are human-shaped.

    author_cards.py exits 2 when a guard fires (unknown block, missing key,
    untraceable figure). That is a real halt and it is kept — but it names the
    card and the key, so it is something a person can act on, unlike "stage the
    pages yourself".
    """
    script = SKILL_DIR / "scripts/author_cards.py"
    r = subprocess.run(
        [sys.executable, str(script), str(ep_dir / "docs/episode.json"),
         str(ep_dir / "overlay/export")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode:
        raise EngineFlag(
            "The card pages could not be authored from episode.json. This is a DATA "
            "problem, not a missing-file problem — fix the field it names in "
            f"docs/episode.json, then clear this flag.\n{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def ep_folder(ep) -> str:
    """Working folder name for an episode (bare stem until the Stage-8 rename)."""
    nn = ep.get("ep_number")
    return f"PP-EP{int(nn):02d}" if nn is not None else f"PP-EP-{ep['id'][:8]}"


# ==========================================================================
class MockProvider:
    """Pretend externals. Artifacts are small text files under .mock/ so every
    step has a real, checkable output path — same shape as a real run."""

    name = "mock"

    def __init__(self, mock_root: Path):
        self.root = mock_root
        self.step_secs = float(os.environ.get("MOCK_STEP_SECS", "1.5"))
        self._fail_always = os.environ.get("MOCK_FAIL_STEP", "")
        self._fail_once = os.environ.get("MOCK_FAIL_ONCE", "")
        self._failed_once: set[str] = set()

    def maybe_fail(self, step: str):
        if self._fail_always == step:
            raise RuntimeError(f"injected failure in {step} (MOCK_FAIL_STEP)")
        if self._fail_once == step and step not in self._failed_once:
            self._failed_once.add(step)
            raise RuntimeError(f"injected one-off failure in {step} (MOCK_FAIL_ONCE)")

    def _artifact(self, folder: str, rel: str, note: str) -> str:
        p = self.root / folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        # A .png stub used to be a text file with a .png name. The end card
        # composites overlay/export/ebook-cover.png, so a fake one renders as an
        # alt-text box and the mock stops resembling a real run. Copy a real
        # image instead — it costs nothing and keeps the mock honest.
        #
        # A cover gets a PORTRAIT placeholder at the real 1:1.414 ratio. This is
        # not fussiness: the end card sizes itself from the cover, and a square
        # stand-in pushed its text out to x=2441 on a 1920px card — card_check
        # caught it, which is exactly what it is for.
        src = SKILL_DIR / "assets/pp-logo-on-dark.png"
        name = Path(rel).name
        if "cover" in name and rel.endswith(".png"):
            src = REPO_DIR / "engine/testdata/mock-ebook-cover.png"
        elif name.startswith("hero") and rel.endswith(".png"):
            # A real photograph, so the cover the mock builds is a cover: the
            # template scrims the hero and sets white type over it, and a
            # transparent logo would leave white-on-white that no geometric
            # check can see.
            src = SKILL_DIR / "assets/marketing-hero.png"
        if rel.endswith(".png") and src.is_file():
            shutil.copyfile(src, p)
        else:
            p.write_text(f"mock artifact: {note}\n", encoding="utf-8")
        return str(p)

    def _work(self):
        time.sleep(self.step_secs)

    # -- plan / credits ------------------------------------------------------
    def broll_plan(self, ep) -> list[str]:
        n = int(os.environ.get("MOCK_BROLL_CLIPS", "3"))
        return [f"broll-{i:02d}" for i in range(1, n + 1)]

    def broll_staged(self, ep, clip: str) -> bool:
        return False                       # mock always "generates"

    def balance(self) -> float:
        return float(os.environ.get("MOCK_BALANCE", "100"))

    def clip_cost(self, ep) -> float:
        return 4.0                         # pretend per-clip credits

    def cover_cost(self, ep) -> float:
        return 4.0                         # two pretend heroes @ 2 credits

    # -- steps ---------------------------------------------------------------
    def fetch_script(self, ep, write=True):
        """Pretend Doc read. Deterministic text so the drift check is stable."""
        self.maybe_fail("script_sync")
        self._work()
        text = (f"Mock script for {ep_folder(ep)}.\n"
                "Gordon says a few plain, wry Australian words about the form.\n")
        if write:
            self._artifact(ep_folder(ep), "docs/spoken-words.txt", "from mock Doc")
            p = self.root / ep_folder(ep) / "docs/spoken-words.txt"
            p.write_text(text, encoding="utf-8")
        return text, sha256_text(text), "the mock Doc"

    def audit_inputs(self, ep) -> dict:
        self.maybe_fail("audit_inputs")
        self._work()
        folder = ep_folder(ep)
        for sub in ("docs", "renders", "overlay/export", "overlay/clips",
                    "broll", "ebook", "thumbnail", "output"):
            (self.root / folder / sub).mkdir(parents=True, exist_ok=True)
        # A REAL episode.json, carrying block/content{}/trace{} exactly as a real
        # one must. Scaffolding the old shape would let a mock run prove the
        # render side works while hiding that a real episode arrives without the
        # fields the authoring needs — which is the trap this step exists to head
        # off. The source article goes beside it so trace-or-halt really runs.
        fixture = REPO_DIR / "engine/testdata/mock-episode.json"
        shutil.copyfile(fixture, self.root / folder / "docs/episode.json")
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_DIR / "engine/testdata/mock-source-article.md",
                        self.root / "docs/mock-source-article.md")
        self._artifact(folder, "docs/spoken-words.txt", "script")
        return {"folder": folder}

    def submit_broll(self, ep, clip: str) -> str:
        self.maybe_fail("broll_submit")
        self._work()
        return f"mock-hf-{clip}-{uuid.uuid4().hex[:8]}"

    def poll_broll(self, ep, clip, job_id, polls_so_far):
        self.maybe_fail("broll_collect")
        self._work()
        if polls_so_far < 1:
            return None
        return self._artifact(ep_folder(ep), f"broll/{clip}.mp4", f"job {job_id}")

    def render_ebook_cover(self, ep, choice="A") -> str:
        """Real authoring and a real render, like render_cards — local only.

        Faking this would leave the thing this slice changed unproven: that a
        clean folder with no cover.html now produces a cover instead of a halt
        telling a browser operator to stage one.
        """
        self.maybe_fail("ebook_cover")
        f = ep_folder(ep)
        d = self.root / f
        src = d / "ebook/cover-src/cover.html"
        cover = d / "ebook/cover.png"
        self._artifact(f, "ebook/cover-src/hero.png", f"active hero = {choice}")
        report = author_missing_cover(d)
        w, h = cover_canvas(src)
        try:
            self.run([sys.executable, SKILL_DIR / "scripts/render_still.py",
                      src, cover, str(w), str(h)], cwd=d, timeout=300)
            self.run([sys.executable, SKILL_DIR / "scripts/cover_check.py",
                      src, str(w), str(h)], cwd=d, timeout=180)
        except RuntimeError as e:
            raise EngineFlag(f"Mock cover render failed: {str(e)[-700:]}")
        (d / "overlay/export").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cover, d / "overlay/export/ebook-cover.png")
        print(f"    [mock] {report} — rendered {w}x{h}, cover_check clean")
        return str(cover)

    def render_cards(self, ep) -> list[str]:
        """The one mock step that does REAL work, on purpose.

        Authoring and rendering cards is local Chromium — no credits, no network,
        nothing external. Faking it would mean the mock could not prove the thing
        1d changed: that a clean folder with no card pages now produces cards
        instead of a halt a browser operator cannot clear.
        """
        self.maybe_fail("cards_render")
        f = ep_folder(ep)
        d = self.root / f
        export = d / "overlay/export"
        export.mkdir(parents=True, exist_ok=True)
        added = stage_card_furniture(export)
        report = author_missing_cards(d)
        try:
            self.run([sys.executable, SKILL_DIR / "scripts/card_check.py", export],
                     cwd=d, timeout=600)
            self.run([sys.executable, SKILL_DIR / "scripts/render_cards_batch.py",
                      export, d / "overlay/clips"], cwd=d, timeout=900)
        except RuntimeError as e:
            raise EngineFlag(f"Mock card render failed: {str(e)[-700:]}")
        print(f"    [mock] staged {len(added)} furniture file(s); {report}")
        return sorted(str(p) for p in (d / "overlay/clips").glob("*.mp4"))

    def run(self, args, cwd, timeout=None, tail=800):
        r = subprocess.run([str(a) for a in args], cwd=str(cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout or 600)
        if r.returncode != 0:
            raise RuntimeError(f"{Path(str(args[1])).name} exited {r.returncode}: "
                               f"…{(r.stderr or r.stdout or '').strip()[-tail:]}")
        return r

    def poll_heygen(self, ep, polls_so_far):
        self.maybe_fail("heygen_download")
        self._work()
        if polls_so_far < 1:
            return None
        return self._artifact(ep_folder(ep), "renders/presenter-master.mp4",
                              f"HeyGen master for {ep.get('heygen_name')}")

    def build_shot_map(self, ep) -> str:
        self.maybe_fail("shot_map")
        self._work()
        return self._artifact(ep_folder(ep), "renders/shot-map.json", "shot map + SRT")

    def make_covers_ab(self, ep):
        self.maybe_fail("covers_ab")
        self._work()
        f = ep_folder(ep)
        self._artifact(f, "ebook/cover-src/hero-a.png", "generated hero A")
        self._artifact(f, "ebook/cover-src/hero-b.png", "generated hero B")
        return (self._artifact(f, "thumbnail/cover-A.png", "cover option A"),
                self._artifact(f, "thumbnail/cover-B.png", "cover option B"))

    def assemble_passA(self, ep) -> str:
        self.maybe_fail("assemble_passA")
        self._work()
        return self._artifact(ep_folder(ep), "overlay/_passA.mp4", "pass A base motion")

    def assemble_passB(self, ep) -> str:
        self.maybe_fail("assemble_passB")
        self._work()
        return self._artifact(ep_folder(ep), "output/FINAL.mp4", "pass B final")

    def self_qc(self, ep, final_path) -> str:
        self.maybe_fail("self_qc")
        self._work()
        return self._artifact(ep_folder(ep), "output/QC-REPORT.md", "self-QC passed")

    def build_ebook(self, ep) -> str:
        self.maybe_fail("ebook_pdf")
        self._work()
        return self._artifact(ep_folder(ep), "output/ebook.pdf", "e-book PDF")

    def build_thumbnail(self, ep) -> str:
        self.maybe_fail("thumbnail")
        self._work()
        return self._artifact(ep_folder(ep), "output/thumbnail.png", "thumbnail")

    def save_youtube_copy(self, ep) -> str:
        self.maybe_fail("youtube_copy")
        self._work()
        return self._artifact(ep_folder(ep), "output/youtube.txt", "YT title + description")


# ==========================================================================
class RealProvider:
    """The real toolchain, driven exactly as the pp-episode-production skill
    documents it. Steps find-or-build: an artifact already on disk is used, not
    rebuilt (resumability + no re-spend). What can't run autonomously FLAGS."""

    name = "real"
    PASS_TIMEOUT = 2400          # ffmpeg passes / card batches can take a while

    def __init__(self, pp_videos: Path):
        self.pp = pp_videos                       # MEDIA: episode folders, .env
        self.scripts = SKILL_DIR / "scripts"      # CODE: versioned, in the repo
        self.assets = SKILL_DIR / "assets"
        self.logo = self.assets / "video-logo-chip.png"
        self.music = pp_videos / "PP-EP01-The-Trifecta-Mistake/music" / \
            "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"
        # Higgsfield CLI (B+ wiring, 2026-07-24): hands-off gens on PLAN credits.
        # One-time `hf auth login` per machine; token lives in ~/.config/higgsfield.
        # If the CLI is missing/unauthenticated, every gen path falls back to the
        # honest b-roll gate (Option B) — nothing breaks, a human stages clips.
        self.hf = Path(os.environ.get("HF_CLI", r"C:\Users\jlral\tools\hf\hf.exe"))
        self.broll_model = os.environ.get("ENGINE_BROLL_MODEL", "kling3_0_turbo")
        # Cover heroes: two stills, generated UPFRONT in the gens-first batch
        # (~2 credits each). Portrait 2:3 matches the A4-ish cover canvas.
        self.cover_model = os.environ.get("ENGINE_COVER_MODEL", "nano_banana_pro")
        self.cover_aspect = os.environ.get("ENGINE_COVER_ASPECT", "2:3")
        self.cover_res = os.environ.get("ENGINE_COVER_RES", "2k")
        self.cover_ceiling = float(os.environ.get("ENGINE_COVER_CEILING", "12"))
        self._registry_checked = False
        # let the skill's pp_paths put ffmpeg/ffprobe on PATH for our subprocesses
        sys.path.insert(0, str(self.scripts))
        try:
            import pp_paths
            pp_paths.ensure_path()
        except Exception:
            pass                                     # PATH may already be fine

    # -- Higgsfield CLI ------------------------------------------------------
    def _hf(self, *args, timeout=120):
        """Run the Higgsfield CLI with --json and parse the response."""
        r = subprocess.run([str(self.hf), *args, "--json"], capture_output=True,
                           text=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"hf {' '.join(args[:2])} exited {r.returncode}: "
                               f"{(r.stderr or r.stdout).strip()[-300:]}")
        return json.loads(r.stdout)

    def hf_ready(self) -> bool:
        return self.hf.is_file()

    # -- plumbing ------------------------------------------------------------
    def dir(self, ep) -> Path:
        return self.pp / ep_folder(ep)

    def epjson(self, ep) -> dict:
        return json.loads((self.dir(ep) / "docs/episode.json").read_text(encoding="utf-8"))

    def run(self, args, cwd, timeout=None, tail=800):
        """Run a tool; on failure raise with the stderr tail (goes into the
        plain-English flag if retries exhaust)."""
        r = subprocess.run([str(a) for a in args], cwd=str(cwd), capture_output=True,
                           text=True, timeout=timeout or self.PASS_TIMEOUT)
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip()[-tail:]
            raise RuntimeError(f"{Path(str(args[0])).name if not str(args[0]).endswith('py') else Path(str(args[1])).name} "
                               f"exited {r.returncode}: …{err}")
        return r

    def py(self, script, *args, cwd, timeout=None):
        return self.run([sys.executable, self.scripts / script, *args],
                        cwd=cwd, timeout=timeout)

    def _clip(self, ep, cid: str) -> Path:
        """Map an episode.json card id (C1, TITLE, END, WARRANTY) to its
        rendered clip in overlay/clips/ (files carry descriptive names)."""
        clips = self.dir(ep) / "overlay/clips"
        exact = clips / f"{cid}.mp4"
        if exact.is_file():
            return exact
        pats = {"TITLE": "*title*.mp4", "END": "end-card*.mp4", "WARRANTY": "warranty*.mp4"}
        pat = pats.get(cid) or f"*c{int(cid[1:]):02d}*.mp4"   # C7 -> *c07*.mp4
        hits = [p for p in sorted(clips.glob(pat)) if "lowerthird" not in p.name]
        if len(hits) != 1:
            # An EngineFlag, NOT a RuntimeError: a card that did not land is not a
            # transient fault, so retrying burns three full Chromium batch renders
            # before saying anything. Fail once, in plain English. (Design §16.11.)
            raise EngineFlag(
                f"Card {cid} has no clip in overlay/clips: expected exactly one file "
                f"matching {pat}, found {len(hits)}. Most likely {cid} is marked "
                f'block:"bespoke" in episode.json and its page has not been hand-authored '
                f"yet — bespoke cards are never generated, by design. Otherwise the page "
                f"is named so it does not match, or it failed to render. "
                f"Retrying will not fix any of those.")
        return hits[0]

    def _audio_kbps(self, path: Path) -> float:
        r = self.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                      "-show_entries", "stream=bit_rate", "-of", "csv=p=0", path],
                     cwd=path.parent, timeout=60)
        try:
            return float(r.stdout.strip()) / 1000.0
        except ValueError:
            return 0.0

    # -- plan / credits ------------------------------------------------------
    def broll_plan(self, ep) -> list[str]:
        return [b["target"] for b in self.epjson(ep).get("broll", [])]

    def broll_staged(self, ep, clip: str) -> bool:
        return (self.dir(ep) / "broll" / f"{clip}.mp4").is_file()

    def _broll_prompt(self, ep, clip: str) -> str:
        for b in self.epjson(ep).get("broll", []):
            if b["target"] == clip:
                if not b.get("prompt"):
                    raise EngineFlag(
                        f"B-roll clip '{clip}' has no prompt in episode.json — "
                        "Claude Code writes the b-roll prompts (hats / ethnic-mix / "
                        "turf wording baked in). Add it, then clear this flag.")
                return b["prompt"]
        raise RuntimeError(f"clip {clip} not found in episode.json broll[]")

    def balance(self) -> float:
        if self.hf_ready():
            return float(self._hf("account", "status")["credits"])
        raise EngineFlag(
            "I can't check the Higgsfield balance: the CLI isn't installed on this "
            "machine (see engine/README — install + `hf auth login` once). Either "
            "install it, or confirm credits manually and clear this flag.")

    def clip_cost(self, ep) -> float:
        """Exact per-clip estimate via the CLI's cost preview (no spend)."""
        if not self.hf_ready():
            return 8.0                     # conservative planning figure
        clips = self.broll_plan(ep)
        probe = next((c for c in clips if not self.broll_staged(ep, c)), None)
        if probe is None:
            return 0.0
        return float(self._hf("generate", "cost", self.broll_model,
                              "--prompt", self._broll_prompt(ep, probe))["credits"])

    # -- cover heroes (gens-first batch, alongside the b-roll) ---------------
    def _hero_paths(self, ep):
        """hero-a.png / hero-b.png are the two OPTIONS; hero.png is whichever one
        is currently ACTIVE (what cover.html draws). Older episodes only have
        hero.png + hero-b.png — hero.png IS option A there, so adopt it."""
        src = self.dir(ep) / "ebook/cover-src"
        a, b, active = src / "hero-a.png", src / "hero-b.png", src / "hero.png"
        if active.is_file() and not a.is_file():
            src.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(active, a)
        return a, b, active

    def _cover_prompts(self, ep):
        c = self.epjson(ep).get("cover") or {}
        a, b = c.get("hero_a_prompt"), c.get("hero_b_prompt")
        if not (a and b):
            raise EngineFlag(
                "The two cover-hero prompts are missing from episode.json. Add a "
                '"cover": {"hero_a_prompt": "…", "hero_b_prompt": "…"} block — two '
                "DIFFERENT compositions (Claude Code writes them, with the hats / "
                "ethnic-mix / turf wording baked in). The heroes are generated "
                "UPFRONT with the b-roll so the cover pick reaches you while "
                "Gordon is still rendering. Add them, then clear this flag.")
        return a, b

    def cover_cost(self, ep) -> float:
        """Exact preview of the cover-hero spend (no spend). 0 once both heroes
        are on disk — a staged asset is never regenerated."""
        a, b, _ = self._hero_paths(ep)
        missing = [p for p in (a, b) if not p.is_file()]
        if not missing:
            return 0.0
        if not self.hf_ready():
            return 2.0 * len(missing)      # conservative planning figure
        pa, _pb = self._cover_prompts(ep)  # flags EARLY if the prompts aren't written
        per = float(self._hf("generate", "cost", self.cover_model, "--prompt", pa,
                             "--aspect_ratio", self.cover_aspect,
                             "--resolution", self.cover_res)["credits"])
        return per * len(missing)

    def _generate_heroes(self, ep, want):
        """Fire the missing heroes, checkpointing each job id into
        docs/hero-jobs.json the instant it exists (same double-spend guard as
        the b-roll). Previewed and capped before anything is spent."""
        if not self.hf_ready():
            raise EngineFlag(
                "The two cover heroes aren't on disk and the Higgsfield CLI isn't "
                "installed (see engine/README). Either install it for hands-off "
                "gens, or stage ebook/cover-src/hero-a.png + hero-b.png, then "
                "clear this flag.")
        pa, pb = self._cover_prompts(ep)
        prompts = {"hero_A": pa, "hero_B": pb}
        ledger = self.dir(ep) / "docs/hero-jobs.json"
        book = json.loads(ledger.read_text(encoding="utf-8")) if ledger.is_file() else {}

        per = 0.0
        todo = [(k, p) for k, p in want if not book.get(k, {}).get("job_id")]
        if todo:
            per = float(self._hf("generate", "cost", self.cover_model,
                                 "--prompt", prompts[todo[0][0]],
                                 "--aspect_ratio", self.cover_aspect,
                                 "--resolution", self.cover_res)["credits"])
            est = per * len(todo)
            if est > self.cover_ceiling:
                raise EngineFlag(
                    f"The cover heroes are estimated at ~{est:.0f} Higgsfield credits, "
                    f"over the cover ceiling of {self.cover_ceiling:.0f}. Raise "
                    "ENGINE_COVER_CEILING or change ENGINE_COVER_MODEL, then clear "
                    "this flag.")
        for key, path in want:
            rec = book.setdefault(key, {})
            if not rec.get("job_id"):
                job = self._hf("generate", "create", self.cover_model,
                               "--prompt", prompts[key],
                               "--aspect_ratio", self.cover_aspect,
                               "--resolution", self.cover_res)
                rec["job_id"] = job[0] if isinstance(job, list) else job["id"]
                rec["model"] = self.cover_model
                rec["credits"] = per
                rec["note"] = f"engine gens-first batch -> {path.name}"
                ledger.parent.mkdir(parents=True, exist_ok=True)
                ledger.write_text(json.dumps(book, indent=1), encoding="utf-8")
            self._hf_download(rec["job_id"], path, key)

    def _hf_download(self, job_id, dest: Path, label: str):
        """Poll one Higgsfield job to completion and save the result. Stills are
        quick (well under a minute); the heartbeat keeps beating through this."""
        for _ in range(120):               # ~20 min ceiling, then flag honestly
            job = self._hf("generate", "get", job_id)
            status = job.get("status")
            if status in ("failed", "nsfw"):
                raise RuntimeError(f"Higgsfield job for {label} came back {status}")
            if status == "completed":
                url = job.get("result_url")
                if not url:
                    raise RuntimeError(f"job for {label} completed but has no result_url")
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".part")
                with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
                    shutil.copyfileobj(r, f)
                tmp.replace(dest)
                return str(dest)
            time.sleep(10)
        raise RuntimeError(f"Higgsfield job for {label} never completed ({job_id})")

    # -- the script's ONE home: the Google Doc --------------------------------
    DOC_ID = re.compile(r"/document/d/([A-Za-z0-9_-]{20,})")

    def _doc_id(self, ep) -> str:
        url = (ep.get("script_doc_url") or "").strip()
        if not url:
            raise EngineFlag(
                "No script Doc is linked to this episode. The script lives as a "
                "Google Doc in the episode's Drive folder — that Doc is the single "
                "source of truth. Paste its link into the words card on the board, "
                "then clear this flag. I will not build from a local draft.")
        m = self.DOC_ID.search(url)
        if not m:
            raise EngineFlag(
                f"The script Doc link doesn't look like a Google Doc URL ({url[:80]}). "
                "It should look like https://docs.google.com/document/d/<id>/edit — "
                "fix the link on the board, then clear this flag.")
        return m.group(1)

    def fetch_script(self, ep, write=True):
        """Read the script from its Google Doc and (by default) overwrite the local
        docs/spoken-words.txt from it. Returns (text, sha256, source).

        ONE SCRIPT, ONE HOME: the Doc is authoritative from the moment it is made.
        spoken-words.txt is a derived cache, rebuilt here every single build, so an
        operator edit can never be silently ignored.

        Reads via the Doc's plain-text export URL, which needs the Doc shared as
        "anyone with the link can view". Anything that isn't real text — a Google
        sign-in page, an empty body — FLAGS. We never fall back to the stale draft."""
        doc_id = self._doc_id(ep)
        url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pp-engine"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                ctype = (r.headers.get("Content-Type") or "").lower()
        except Exception as e:
            raise EngineFlag(
                f"I can't read the script Doc ({e}). The script is the single source "
                "of truth and I will NOT build from a stale local copy. Check the "
                "Doc still exists and is shared so anyone with the link can view it, "
                "then clear this flag.")
        if "text/plain" not in ctype:
            raise EngineFlag(
                "The script Doc didn't come back as plain text — Google returned "
                f"'{ctype or 'nothing'}', which usually means a sign-in page. Share "
                "the Doc so anyone with the link can VIEW it, then clear this flag. "
                "I will not guess at the script or use an old copy.")
        text = raw.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").strip()
        if len(text.split()) < 50:
            raise EngineFlag(
                f"The script Doc reads as only {len(text.split())} words — that's not "
                "a full episode script. Check the right Doc is linked and that it has "
                "content, then clear this flag.")
        if write:
            out = self.dir(ep) / "docs/spoken-words.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
        return text, sha256_text(text), f"the script Doc ({doc_id[:10]}…)"

    # -- steps ---------------------------------------------------------------
    def audit_inputs(self, ep) -> dict:
        d = self.dir(ep)
        missing = [rel for rel in ("docs/episode.json", "docs/spoken-words.txt")
                   if not (d / rel).is_file()]
        if missing:
            raise EngineFlag(
                f"Create-inputs are missing for {d.name}: {', '.join(missing)}. "
                "Claude Code writes these at the create step (the create brain is "
                "Phase 4). Stage them, then clear this flag.")
        # RENDER-READY SCAN (PP-STANDARDS 25 Jul 2026): catch a glitch-prone
        # script BEFORE Jodie spends a HeyGen render on it.
        try:
            self.py("render_ready.py", d / "docs/spoken-words.txt",
                    "--episode", d / "docs/episode.json", cwd=d, timeout=120)
        except RuntimeError as e:
            raise EngineFlag(
                f"The spoken-words track is NOT render-ready — fix it before "
                f"Jodie renders. {str(e)[-500:]}")
        for sub in ("renders", "overlay/export", "overlay/clips", "broll",
                    "ebook", "thumbnail", "output"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        return {"folder": str(d)}

    def submit_broll(self, ep, clip: str) -> str:
        if self.broll_staged(ep, clip):
            return f"staged-{clip}"        # already on disk — nothing to spend
        if not self.hf_ready():
            raise EngineFlag(
                f"B-roll clip '{clip}' isn't on disk and the Higgsfield CLI isn't "
                "installed (see engine/README). Either install it for hands-off "
                "gens, or generate/stage the clip into broll/, then clear this flag.")
        if not self._registry_checked:     # NO-REPEAT law: check BEFORE any spend
            self.py("broll_registry_check.py", REPO_DIR / "docs/broll-registry.md",
                    self.dir(ep) / "docs/episode.json", cwd=self.dir(ep), timeout=120)
            self._registry_checked = True
        job = self._hf("generate", "create", self.broll_model,
                       "--prompt", self._broll_prompt(ep, clip))
        return job[0] if isinstance(job, list) else job["id"]

    def poll_broll(self, ep, clip, job_id, polls_so_far):
        p = self.dir(ep) / "broll" / f"{clip}.mp4"
        if p.is_file():
            return str(p)
        if job_id.startswith("staged-"):
            if polls_so_far > 3:           # staged file vanished — don't spin
                raise RuntimeError(f"b-roll clip {clip} is missing from broll/")
            return None
        job = self._hf("generate", "get", job_id)
        status = job.get("status")
        if status in ("failed", "nsfw"):
            raise RuntimeError(f"Higgsfield job for {clip} came back {status}")
        if status != "completed":
            time.sleep(10)                 # pace the polling; heartbeat stays live
            return None
        url = job.get("result_url")
        if not url:
            raise RuntimeError(f"job for {clip} completed but has no result_url")
        tmp = p.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.rename(p)
        return str(p)

    def broll_contact(self, ep, files) -> str:
        """6-up contact sheet of b-roll stills — the human glance at the render
        gate BEFORE assembly (PP-STANDARDS b-roll HARD-FAIL list, 25 Jul 2026)."""
        d = self.dir(ep)
        out = d / "output/qc/broll-contact.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        n = len(files)
        cols = 3
        def pos(i):
            x = "+".join(["w0"] * (i % cols)) or "0"
            y = "+".join(["h0"] * (i // cols)) or "0"
            return f"{x}_{y}"
        layout = "|".join(pos(i) for i in range(n))
        fc = "".join(f"[{i}:v]scale=640:-1[t{i}];" for i in range(n)) + \
             "".join(f"[t{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}[out]"
        cmd = ["ffmpeg", "-y"]
        for f in files:
            cmd += ["-ss", "2.5", "-i", f]
        cmd += ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", out]
        self.run(cmd, cwd=d, timeout=300)
        return str(out)

    def render_ebook_cover(self, ep, choice="A") -> str:
        """Build the cover FROM THE PICK: activate the chosen hero (cover.html
        always draws hero.png), re-render from cover-src (never trust a handed
        PNG), then propagate to BOTH ebook/cover.png and
        overlay/export/ebook-cover.png — the cover must land before the card
        batch or the end card renders blank."""
        d = self.dir(ep)
        hero_a, hero_b, active = self._hero_paths(ep)
        pick = hero_b if str(choice).strip().upper() == "B" else hero_a
        if pick.is_file():
            shutil.copyfile(pick, active)          # hero.png = the picked hero
        src = d / "ebook/cover-src/cover.html"
        cover = d / "ebook/cover.png"
        # Author the page if it is missing. This is the halt that stopped EP12
        # first and the second of the four Hugh could not clear: it used to say
        # "stage one, then clear this flag" to a browser operator.
        author_missing_cover(d)
        if src.is_file():
            # The canvas comes from the page, which got it from the template.
            # The old hard-coded 1600x2263 (and the cover-src/cover.png override
            # that could disagree with both) are gone — see cover_canvas().
            w, h = cover_canvas(src)
            self.py("render_still.py", src, cover, w, h, cwd=d)
            # Overlap/clip QC (the EP09 cover lesson): fail rather than ship a
            # cover whose text collides or clips.
            self.py("cover_check.py", src, str(w), str(h), cwd=d, timeout=180)
        elif not cover.is_file():
            raise EngineFlag(
                f"No e-book cover for {d.name}: ebook/cover-src/cover.html could not be "
                "authored and no ebook/cover.png exists. Clear this flag once one does.")
        shutil.copyfile(cover, d / "overlay/export/ebook-cover.png")
        return str(cover)

    def render_cards(self, ep) -> list[str]:
        d = self.dir(ep)
        export = d / "overlay/export"
        export.mkdir(parents=True, exist_ok=True)
        # 1. the standing pages + the assets an authored card needs
        stage_card_furniture(export)
        # 2. author whatever is missing; hand-authored pages are left alone
        author_missing_cards(d)
        # 3. HARD GATE before we spend Chromium on clips: a card with a collision
        #    would ship into the video AND the matching e-book figure (design §12).
        try:
            self.py("card_check.py", export, cwd=d, timeout=600)
        except RuntimeError as e:
            raise EngineFlag(
                "A card page has a layout collision and must not be rendered — it "
                "would ship into the video and the matching e-book figure. Each "
                "problem below names the elements and the overlap.\n"
                f"{str(e)[-900:]}")
        # 4. render every page to a clip
        self.py("render_cards_batch.py", export, d / "overlay/clips", cwd=d)
        epj = self.epjson(ep)
        ids = [c["id"] for c in epj["cards"]]
        return [str(self._clip(ep, cid)) for cid in ids]     # verifies every card landed

    def poll_heygen(self, ep, polls_so_far):
        """The render is a HUMAN step; we only pick up the finished master via
        the API video_url (the ~189 kbps master — never the web download)."""
        d = self.dir(ep)
        master = d / "renders/presenter-master.mp4"
        if not master.is_file():
            self._heygen_fetch(ep, master)         # returns only when downloaded
        kbps = self._audio_kbps(master)
        if kbps and kbps < 180:
            raise EngineFlag(
                f"The presenter master's audio is {kbps:.0f} kbps — below the locked "
                "~189 kbps API standard (sounds compressed). It was probably saved via "
                "the web-app Download button. Re-pull it via the API video_url, then "
                "clear this flag.")
        return str(master)

    def _heygen_fetch(self, ep, master: Path):
        key = self._env("HEYGEN_API_KEY")
        vid = ep.get("heygen_video_id")
        if not vid:                        # fall back to poll-by-project-name
            name = ep.get("heygen_name") or ""
            req = urllib.request.Request(
                "https://api.heygen.com/v1/video.list?limit=100", headers={"x-api-key": key})
            with urllib.request.urlopen(req, timeout=30) as r:
                vids = json.load(r).get("data", {}).get("videos", [])
            hit = next((v for v in vids if name and name in (v.get("video_title") or "")
                        and v.get("status") == "completed"), None)
            if not hit:
                raise RuntimeError(f"no completed HeyGen render named {name!r} yet")
            vid = hit["video_id"]
        req = urllib.request.Request(
            f"https://api.heygen.com/v1/video_status.get?video_id={vid}",
            headers={"x-api-key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            url = json.load(r).get("data", {}).get("video_url")
        if not url:
            raise RuntimeError("HeyGen render found but no video_url yet")
        tmp = master.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.rename(master)

    def _env(self, name):
        env = self.pp / ".env"
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
        raise EngineFlag(f"{name} is missing from PP Videos/.env — add it, then clear this flag.")

    def build_shot_map(self, ep) -> str:
        d = self.dir(ep)
        self.py("build_shot_map.py", d / "renders/presenter-master.mp4",
                d / "docs/spoken-words.txt", d / "renders", cwd=d)
        sm = d / "renders/shot-map.json"
        if not sm.is_file():
            raise RuntimeError("build_shot_map ran but renders/shot-map.json is missing")
        return str(sm)

    def make_covers_ab(self, ep):
        """The two cover heroes, made UPFRONT in the gens-first batch so the pick
        reaches the operator DURING the render window (R7, 26 Jul 2026) — the
        build never parks mid-run on 'no e-book cover, needs a look'.

        Missing heroes are generated (previewed, ~2 credits each); staged ones are
        used as-is. Both are then PUBLISHED to Supabase storage, because the board
        renders https URLs only — local paths show as 'No cover yet' (EP09)."""
        d = self.dir(ep)
        hero_a, hero_b, active = self._hero_paths(ep)
        want = [(k, p) for k, p in (("hero_A", hero_a), ("hero_B", hero_b))
                if not p.is_file()]
        if want:
            self._generate_heroes(ep, want)
        if not active.is_file():
            shutil.copyfile(hero_a, active)        # A is active until a pick lands
        a, b = d / "thumbnail/cover-A.png", d / "thumbnail/cover-B.png"
        a.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(hero_a, a)
        shutil.copyfile(hero_b, b)
        folder = ep_folder(ep)
        return (self._publish_asset(a, f"{folder}/cover-A.png"),
                self._publish_asset(b, f"{folder}/cover-B.png"))

    def _publish_asset(self, local: Path, obj: str) -> str:
        """Upload to the public episode-assets bucket and return the https URL —
        VERIFIED reachable, so a cover that wouldn't show on the board flags
        instead of silently displaying 'No cover yet'."""
        base = self._env("SUPABASE_URL").rstrip("/")
        key = self._env("SUPABASE_SERVICE_ROLE_KEY")
        req = urllib.request.Request(
            f"{base}/storage/v1/object/episode-assets/{obj}",
            data=local.read_bytes(), method="POST",
            headers={"Authorization": f"Bearer {key}", "apikey": key,
                     "Content-Type": "image/png", "x-upsert": "true"})
        with urllib.request.urlopen(req, timeout=120) as r:
            r.read()
        pub = f"{base}/storage/v1/object/public/episode-assets/{obj}"
        with urllib.request.urlopen(pub, timeout=30) as r:      # visibility check
            if r.status != 200 or not r.read(64):
                raise EngineFlag(
                    f"Published {obj} but the public URL doesn't resolve — the board "
                    "can't show it. Check the episode-assets bucket, then clear this flag.")
        return pub

    # ---- assembly: emit the graph, then run the documented ffmpeg command ---
    def _emit_graph(self, ep, which: str) -> Path:
        d = self.dir(ep)
        out = d / f"renders/pass{which}_graph.txt"
        r = self.py("assemble_episode.py", d / "docs/episode.json",
                    d / "renders/shot-map.json", which, cwd=d, timeout=120)
        out.write_text(r.stdout, encoding="utf-8")
        return out

    def assemble_passA(self, ep) -> str:
        d = self.dir(ep)
        graph = self._emit_graph(ep, "A")
        # input order: [0]=presenter, [1..N]=broll (broll[] order), [N+1]=logo chip
        cmd = ["ffmpeg", "-y", "-i", d / "renders/presenter-master.mp4"]
        for b in self.epjson(ep)["broll"]:
            cmd += ["-i", d / "broll" / f"{b['target']}.mp4"]
        cmd += ["-i", self.logo, "-filter_complex_script", graph, "-map", "[vout]",
                "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-an",
                d / "overlay/_passA.mp4"]
        self.run(cmd, cwd=d)
        return str(d / "overlay/_passA.mp4")

    def assemble_passB(self, ep) -> str:
        d = self.dir(ep)
        graph = self._emit_graph(ep, "B")
        epj = self.epjson(ep)
        standing = epj["build"].get("standing", {})
        content = [c["id"] for c in epj["cards"] if c["id"] not in standing.values()]
        # input order: [0]=_passA, [1..M]=content cards, then title/endcard/
        # warranty, presenter (audio), music — the layout the graphs are built for
        cmd = ["ffmpeg", "-y", "-i", d / "overlay/_passA.mp4"]
        for cid in content:
            cmd += ["-i", self._clip(ep, cid)]
        for role in ("title", "endcard", "warranty"):
            cmd += ["-i", self._clip(ep, standing[role])]
        cmd += ["-i", d / "renders/presenter-master.mp4", "-i", self.music]
        mid = epj["build"].get("midroll") or {}
        if mid.get("composite") and mid.get("clip"):
            cmd += ["-i", d / "overlay/clips" / mid["clip"]]   # input MUSIC_IN+1
        final = d / "output" / f"{ep_folder(ep)}-FINAL.mp4"
        cmd += ["-filter_complex_script", graph, "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", "-map_metadata", "-1", "-dn", final]
        self.run(cmd, cwd=d)
        # ship the SRT beside the output, per the runbook
        srt = d / "renders/generated.srt"
        if srt.is_file():
            shutil.copyfile(srt, final.with_suffix(".srt"))
        return str(final)

    def _qc_integrity_gate(self):
        """Refuse to run QC unless qc_episode.py is exactly what is committed.
        Returns the HEAD blob sha; on any doubt it never returns."""
        from gitgate import assert_committed
        return assert_committed(
            QC_REL,
            gate="QC INTEGRITY GATE",
            why="qc_episode.py decides whether an episode is good enough to ship.\n"
                "Rather than judge this episode by rules nobody has reviewed, the\n"
                "engine stops here. The build so far is checkpointed and resumes.",
            code=5)

    def self_qc(self, ep, final_path) -> str:
        self._qc_integrity_gate()      # runs before we shell out. No bypass.
        d = self.dir(ep)
        head = str(self.epjson(ep).get("build", {}).get("title_head", 7.0))
        # --episode arms the end-sequence + midroll checks (the EP08 lessons)
        self.py("qc_episode.py", final_path, d / "renders/shot-map.json",
                d / "output/qc", "--head", head,
                "--episode", d / "docs/episode.json", cwd=d, timeout=900)
        return str(d / "output/qc/QC-REPORT.md")

    def build_ebook(self, ep) -> str:
        d = self.dir(ep)
        srcs = [p for p in (d / "ebook").glob("*.html")]
        if len(srcs) != 1:
            raise EngineFlag(
                f"Expected exactly one e-book source HTML in {d.name}/ebook/, found "
                f"{len(srcs)}. Claude Code writes the e-book source — the article body "
                "in the standing template's class vocabulary. Stage it, then clear "
                "this flag.")
        out = d / "output" / f"{ep_folder(ep)}-ebook.pdf"
        self.py("build_ebook.py", srcs[0], out, cwd=d, timeout=600)
        return str(out)

    def build_thumbnail(self, ep) -> str:
        d = self.dir(ep)
        pages = list((d / "thumbnail").glob("*thumbnail*.html"))
        if len(pages) != 1:
            raise EngineFlag(
                f"Expected exactly one *thumbnail*.html in {d.name}/thumbnail/, found "
                f"{len(pages)}. Stage it, then clear this flag.")
        # Standard-template conformance guard (EP08 lesson): the standing thumbnail
        # recipe always carries the PP logo chip. A page without it was hand-rolled
        # off-template — flag rather than render a non-standard thumbnail.
        if "pp-logo-on-dark" not in pages[0].read_text(encoding="utf-8", errors="ignore"):
            raise EngineFlag(
                f"{pages[0].name} doesn't reference pp-logo-on-dark.png — it isn't built "
                "on the standing thumbnail template (assets/youtube-thumbnail-template.html). "
                "Rebuild it from the template, then clear this flag.")
        out = d / "output" / f"{ep_folder(ep)}-thumbnail.png"
        self.py("render_still.py", pages[0], out, "1280", "720", cwd=d, timeout=300)
        return str(out)

    def save_youtube_copy(self, ep) -> str:
        d = self.dir(ep)
        hits = list((d / "output").glob("*youtube*.txt"))
        if not hits:
            raise EngineFlag(
                "The YouTube title/description file is missing. Claude Code writes the "
                "copy per docs/youtube-metadata-kit.md (Jodie's ruling, 26 Jul 2026 — "
                "ownership moved from Cowork to the build side; Jodie uploads). Save it "
                f"as {d.name}/output/{ep_folder(ep)}-youtube.txt, then clear this flag.")
        return str(hits[0])
