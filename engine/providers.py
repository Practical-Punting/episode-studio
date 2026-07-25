"""providers.py — the engine's external hands: real services vs mock.

The orchestrator (engine.py) never talks to tools directly; it calls a Provider.

MockProvider simulates everything (no credits, no network) — the 2a spine
acceptance ran on it. RealProvider drives the ACTUAL local toolchain (the
pp-episode-production skill's scripts: Chromium card renders, ffmpeg passes,
WeasyPrint e-book, QC) and is HONEST about the two things that can't run
autonomously yet: Higgsfield generation/balance (MCP, Claude-session-only) and
the HeyGen render itself (a sacred human step — the engine only downloads).

Spend policy (verify-before-spend): a staged asset is NEVER regenerated. The
credit estimate counts only what's actually missing.

Fault injection (mock only), via environment variables:
    MOCK_FAIL_STEP=<step>   that step fails EVERY attempt (shows needs_look)
    MOCK_FAIL_ONCE=<step>   that step fails its FIRST attempt (shows retry)
    MOCK_BALANCE=<n>        pretend Higgsfield balance (default 100)
    MOCK_STEP_SECS=<n>      how long each mock action takes (default 1.5)
    MOCK_BROLL_CLIPS=<n>    clips in the mock plan (default 3)
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path


class EngineFlag(Exception):
    """Raise to say: a HUMAN is needed. The engine flags needs_look with this
    message (plain English!) and does not retry — it isn't transient."""


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

    # -- steps ---------------------------------------------------------------
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
        self.pp = pp_videos
        self.scripts = pp_videos / ".claude/skills/pp-episode-production/scripts"
        self.assets = pp_videos / ".claude/skills/pp-episode-production/assets"
        self.logo = self.assets / "video-logo-chip.png"
        self.music = pp_videos / "PP-EP01-The-Trifecta-Mistake/music" / \
            "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"
        # Higgsfield CLI (B+ wiring, 2026-07-24): hands-off gens on PLAN credits.
        # One-time `hf auth login` per machine; token lives in ~/.config/higgsfield.
        # If the CLI is missing/unauthenticated, every gen path falls back to the
        # honest b-roll gate (Option B) — nothing breaks, a human stages clips.
        self.hf = Path(os.environ.get("HF_CLI", r"C:\Users\jlral\tools\hf\hf.exe"))
        self.broll_model = os.environ.get("ENGINE_BROLL_MODEL", "kling3_0_turbo")
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
            raise RuntimeError(f"card {cid}: expected exactly one clip matching "
                               f"{pat} in overlay/clips, found {len(hits)}")
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
                        "Cowork writes prompts (hats/ethnic-mix/turf wording baked "
                        "in). Add it, then clear this flag.")
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

    # -- steps ---------------------------------------------------------------
    def audit_inputs(self, ep) -> dict:
        d = self.dir(ep)
        missing = [rel for rel in ("docs/episode.json", "docs/spoken-words.txt")
                   if not (d / rel).is_file()]
        if missing:
            raise EngineFlag(
                f"Create-inputs are missing for {d.name}: {', '.join(missing)}. "
                "Cowork writes these (the create brain is Phase 4). Stage them, "
                "then clear this flag.")
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
            self.py("broll_registry_check.py", self.pp / "docs/broll-registry.md",
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

    def render_ebook_cover(self, ep) -> str:
        """Re-render from cover-src (never trust a handed PNG), then propagate
        to BOTH ebook/cover.png and overlay/export/ebook-cover.png — the cover
        must land before the card batch or the end card renders blank."""
        d = self.dir(ep)
        src = d / "ebook/cover-src/cover.html"
        cover = d / "ebook/cover.png"
        if src.is_file():
            w, h = 1600, 2263                       # A4-ish cover canvas
            ref = d / "ebook/cover-src/cover.png"
            if ref.is_file():                       # mirror the approved dims
                r = self.run(["ffprobe", "-v", "error", "-show_entries",
                              "stream=width,height", "-of", "csv=p=0", ref],
                             cwd=d, timeout=60)
                w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
            self.py("render_still.py", src, cover, w, h, cwd=d)
            # Overlap/clip QC (the EP09 cover lesson): fail rather than ship a
            # cover whose text collides or clips.
            self.py("cover_check.py", src, str(w), str(h), cwd=d, timeout=180)
        elif not cover.is_file():
            raise EngineFlag(
                f"No e-book cover for {d.name}: neither ebook/cover-src/cover.html "
                "nor ebook/cover.png exists. Stage one, then clear this flag.")
        shutil.copyfile(cover, d / "overlay/export/ebook-cover.png")
        return str(cover)

    def render_cards(self, ep) -> list[str]:
        d = self.dir(ep)
        self.py("render_cards_batch.py", d / "overlay/export", d / "overlay/clips", cwd=d)
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
        """Two hero options for the human pick. Staged locally, then PUBLISHED to
        Supabase storage so the board can actually SHOW them (the board renders
        https URLs only — local paths display as 'No cover yet'; EP09 lesson)."""
        d = self.dir(ep)
        a, b = d / "thumbnail/cover-A.png", d / "thumbnail/cover-B.png"
        if not (a.is_file() and b.is_file()):
            src_a, src_b = d / "ebook/cover-src/hero.png", d / "ebook/cover-src/hero-b.png"
            if src_a.is_file() and src_b.is_file():
                shutil.copyfile(src_a, a)
                shutil.copyfile(src_b, b)
            else:
                raise EngineFlag(
                    "Cover options A/B need two hero images and I can't generate them "
                    "autonomously yet (Higgsfield is session-only). Stage thumbnail/"
                    "cover-A.png + cover-B.png (or cover-src/hero.png + hero-b.png), "
                    "then clear this flag.")
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

    def self_qc(self, ep, final_path) -> str:
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
                f"{len(srcs)}. Stage the source (Cowork writes it), then clear this flag.")
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
                "The YouTube title/description file is missing (Cowork writes the copy "
                f"per the metadata kit). Save it as {d.name}/output/{ep_folder(ep)}-"
                "youtube.txt, then clear this flag.")
        return str(hits[0])
