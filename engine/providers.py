"""providers.py — the engine's external hands: real services vs mock.

The orchestrator (engine.py) never talks to Higgsfield/HeyGen/ffmpeg directly;
it calls a Provider. MockProvider simulates everything (no credits, no network)
so the claim/lease/resume/never-freeze spine can be exercised safely — the
Phase 2a acceptance runs entirely on it. RealProvider wires the steps to the
actual toolchain where that's scriptable today, and is HONEST about the parts
that aren't wired yet (it flags them for a human rather than pretending).

Fault injection (mock only), via environment variables:
    MOCK_FAIL_STEP=<step>   that step fails EVERY attempt (shows needs_look)
    MOCK_FAIL_ONCE=<step>   that step fails its FIRST attempt (shows retry)
    MOCK_BALANCE=<n>        pretend Higgsfield balance (default 100)
    MOCK_STEP_SECS=<n>      how long each mock action takes (default 1.5)
"""
from __future__ import annotations
import os
import time
import uuid
from pathlib import Path


class EngineFlag(Exception):
    """Raise to say: a HUMAN is needed. The engine flags needs_look with this
    message (plain English!) and does not retry — it isn't transient."""


# --------------------------------------------------------------------------
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

    # -- fault injection ----------------------------------------------------
    def maybe_fail(self, step: str):
        if self._fail_always == step:
            raise RuntimeError(f"injected failure in {step} (MOCK_FAIL_STEP)")
        if self._fail_once == step and step not in self._failed_once:
            self._failed_once.add(step)
            raise RuntimeError(f"injected one-off failure in {step} (MOCK_FAIL_ONCE)")

    # -- helpers -------------------------------------------------------------
    def _artifact(self, folder: str, rel: str, note: str) -> str:
        p = self.root / folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"mock artifact: {note}\n", encoding="utf-8")
        return str(p)

    def _work(self):
        time.sleep(self.step_secs)

    # -- credits -------------------------------------------------------------
    def balance(self) -> float:
        return float(os.environ.get("MOCK_BALANCE", "100"))

    # -- inputs --------------------------------------------------------------
    def audit_inputs(self, ep) -> dict:
        self.maybe_fail("audit_inputs")
        self._work()
        folder = ep_folder(ep)
        for sub in ("docs", "renders", "overlay/export", "overlay/clips",
                    "broll", "ebook", "thumbnail", "output"):
            (self.root / folder / sub).mkdir(parents=True, exist_ok=True)
        self._artifact(folder, "docs/episode.json", "create inputs")
        self._artifact(folder, "docs/spoken-words.txt", "script")
        return {"folder": folder}

    # -- b-roll (the SPEND steps) --------------------------------------------
    def submit_broll(self, ep, clip: str) -> str:
        self.maybe_fail("broll_submit")
        self._work()
        return f"mock-hf-{clip}-{uuid.uuid4().hex[:8]}"

    def poll_broll(self, ep, clip: str, job_id: str, polls_so_far: int) -> str | None:
        """Returns the downloaded file path when done, None while still cooking.
        Mock: done on the second poll."""
        self.maybe_fail("broll_collect")
        self._work()
        if polls_so_far < 1:
            return None
        return self._artifact(ep_folder(ep), f"broll/{clip}.mp4", f"job {job_id}")

    # -- local renders -------------------------------------------------------
    def render_ebook_cover(self, ep) -> str:
        self.maybe_fail("ebook_cover")
        self._work()
        f = ep_folder(ep)
        self._artifact(f, "overlay/export/ebook-cover.png", "cover propagated")
        return self._artifact(f, "ebook/cover.png", "e-book cover")

    def render_cards(self, ep) -> list[str]:
        self.maybe_fail("cards_render")
        self._work()
        f = ep_folder(ep)
        return [self._artifact(f, f"overlay/clips/card-{i:02d}.mp4", "card clip")
                for i in range(1, 4)]

    # -- HeyGen --------------------------------------------------------------
    def poll_heygen(self, ep, polls_so_far: int) -> str | None:
        """Poll by PROJECT NAME; path to the downloaded 189k master when done.
        Mock: done on the second poll."""
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

    def make_covers_ab(self, ep) -> tuple[str, str]:
        self.maybe_fail("covers_ab")
        self._work()
        f = ep_folder(ep)
        return (self._artifact(f, "thumbnail/cover-A.png", "cover option A"),
                self._artifact(f, "thumbnail/cover-B.png", "cover option B"))

    # -- assembly ------------------------------------------------------------
    def assemble_passA(self, ep) -> str:
        self.maybe_fail("assemble_passA")
        self._work()
        return self._artifact(ep_folder(ep), "overlay/_passA.mp4", "pass A base motion")

    def assemble_passB(self, ep) -> str:
        self.maybe_fail("assemble_passB")
        self._work()
        return self._artifact(ep_folder(ep), "output/FINAL.mp4", "pass B final")

    def self_qc(self, ep, final_path: str) -> str:
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


# --------------------------------------------------------------------------
class RealProvider:
    """The real toolchain. Wired where today's scripts allow; HONEST flags where
    Phase 2a hasn't wired a step yet (principle: flag what you can't do well).

    NOTE (for the design doc): b-roll generation currently runs through the
    Higgsfield MCP inside a Claude session — there is no standalone API/key in
    .env — so autonomous generation from this engine isn't wired yet. The step
    checks for STAGED clips and flags if they're missing.
    """

    name = "real"

    def __init__(self, pp_videos: Path):
        self.pp = pp_videos

    def balance(self) -> float:
        # Higgsfield balance isn't reachable outside an MCP session (yet).
        # The credit guard therefore relies on the configured ceiling; a real
        # balance probe is an open item for 2a-real.
        raise EngineFlag(
            "I can't check the Higgsfield balance from the engine yet (it's only "
            "reachable in a Claude session). Confirm there are enough credits, then "
            "clear this flag to continue.")

    def audit_inputs(self, ep) -> dict:
        folder = self.pp / ep_folder(ep)
        missing = [str(rel) for rel in ("docs/episode.json", "docs/spoken-words.txt")
                   if not (folder / rel).is_file()]
        if missing:
            raise EngineFlag(
                f"Create-inputs are missing for {folder.name}: {', '.join(missing)}. "
                "Cowork writes these (Phase 4 moves them here). Stage them, then clear this flag.")
        return {"folder": str(folder)}

    def submit_broll(self, ep, clip):
        raise EngineFlag(
            "Autonomous b-roll generation isn't wired yet (Higgsfield runs via MCP "
            "in a Claude session). Generate/stage the clips into broll/, then clear this flag.")

    def poll_broll(self, ep, clip, job_id, polls_so_far):
        p = self.pp / ep_folder(ep) / "broll" / f"{clip}.mp4"
        return str(p) if p.is_file() else None

    # The remaining real steps shell out to the standing toolkit
    # (render_cards_batch.py, build_shot_map.py, assemble_episode.py,
    # qc_episode.py, build_ebook.py, render_still.py) exactly as documented in
    # the pp-episode-production skill. Wiring + a real-episode shakedown is the
    # 2a-real follow-up; in 2a they flag honestly instead of guessing.
    def _not_wired(self, what):
        raise EngineFlag(f"{what} isn't wired into the engine yet (2a built the spine "
                         "on mock; real wiring is the next step). Run it via the skill, "
                         "then clear this flag.")

    def render_ebook_cover(self, ep): self._not_wired("The e-book cover render")
    def render_cards(self, ep): self._not_wired("The card batch-render")
    def poll_heygen(self, ep, polls_so_far): self._not_wired("HeyGen poll/download")
    def build_shot_map(self, ep): self._not_wired("The shot map build")
    def make_covers_ab(self, ep): self._not_wired("Cover A/B generation")
    def assemble_passA(self, ep): self._not_wired("Pass A assembly")
    def assemble_passB(self, ep): self._not_wired("Pass B assembly")
    def self_qc(self, ep, final_path): self._not_wired("Self-QC")
    def build_ebook(self, ep): self._not_wired("The e-book PDF build")
    def build_thumbnail(self, ep): self._not_wired("The thumbnail build")
    def save_youtube_copy(self, ep): self._not_wired("The YouTube copy save")


def ep_folder(ep) -> str:
    """Working folder name for an episode (bare stem until the Stage-8 rename)."""
    nn = ep.get("ep_number")
    return f"PP-EP{int(nn):02d}" if nn is not None else f"PP-EP-{ep['id'][:8]}"
