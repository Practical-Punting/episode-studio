#!/usr/bin/env python3
"""engine.py — the Episode Studio orchestrator spine (Phase 2a).

ONE episode at a time, crash-safe, never silently frozen. The conductor:
  * claims a queued episode via the LEASE (claimed_by + lease_until) — single
    writer; a stale lease (crashed worker) is reclaimable;
  * drives it through the status contract in the locked build order
    (Higgsfield gens fired FIRST; the HeyGen render runs in parallel with the
    human gate);
  * checkpoints EVERY step into build_state (steps done + job IDs), so a
    memoryless restart resumes exactly where it left off — a finished gen or
    render is never re-run, credits are never double-spent;
  * heartbeats constantly while working; retries transient failures with
    backoff; if a step still fails, writes a plain-English "Needs a look"
    (the episode KEEPS its status) and waits for the flag to clear;
  * pauses at the sacred human gates (awaiting_render / awaiting_cover /
    awaiting_approval) — it never auto-renders, never auto-publishes;
  * checks credits BEFORE a spend — if it can't finish, it flags rather
    than starts.

Usage:
  python engine.py run [--mock] [--watch]   work (watch = keep going across gates)
  python engine.py mock-episode             create the mock ticket (ep 99)
  python engine.py status                   quick board glance
  python engine.py cleanup-mock             delete mock tickets + artifacts

Mock mode (--mock) exercises the whole spine with zero external calls and zero
credits — see providers.py for the fault-injection switches.
"""
from __future__ import annotations
import argparse
import os
import shutil
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

try:  # Windows console defaults to cp1252 — force UTF-8 so log lines never crash
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- config ----------------------------------------------------------------
PP_VIDEOS = Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
ENGINE_DIR = Path(__file__).resolve().parent
MOCK_ROOT = ENGINE_DIR / ".mock"

WORKER = os.environ.get("ENGINE_WORKER", f"pp-engine@{socket.gethostname()}")
LEASE_SECS = 180
HEARTBEAT_SECS = 20
MAX_ATTEMPTS = 3
CREDITS_PER_BROLL = 4                      # conservative planning figure
CREDIT_CEILING = float(os.environ.get("ENGINE_CREDIT_CEILING", "60"))  # per episode

sys.path.insert(0, str(PP_VIDEOS / "scripts"))
import rail  # the one shared Supabase client (RAIL-INTEGRATION.md)

from providers import EngineFlag, MockProvider, RealProvider, ep_folder

HUMAN_GATES = {"awaiting_render", "awaiting_cover", "awaiting_approval"}


def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def _retry_delays(mock):
    env = os.environ.get("ENGINE_RETRY_DELAYS")
    if env:
        return [float(x) for x in env.split(",")]
    return [2, 4, 6] if mock else [5, 25, 120]


# --- heartbeat thread ------------------------------------------------------
class Heartbeat:
    """Beats heartbeat_at + renews the lease every HEARTBEAT_SECS while active.
    If a beat comes back empty, we no longer own the episode (someone reclaimed
    it) — the spine aborts rather than double-writing."""

    def __init__(self, ep_id):
        self.ep_id = ep_id
        self.active = threading.Event()
        self.lost = threading.Event()
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self):
        while not self._stop.is_set():
            if self.active.is_set():
                try:
                    if rail.heartbeat(self.ep_id, WORKER, LEASE_SECS) is None:
                        log("!! lost ownership of the episode (lease reclaimed) — stopping work")
                        self.lost.set()
                        self.active.clear()
                except Exception as e:      # network blip: keep trying, never die
                    log(f"heartbeat hiccup (will keep beating): {e}")
            self._stop.wait(HEARTBEAT_SECS)

    def stop(self):
        self._stop.set()


class OwnershipLost(Exception):
    pass


# --- the step lists (locked build order) -----------------------------------
# building: gens FIRST (submit b-roll before local renders), collect after.
PHASES = {
    "building":   ["audit_inputs", "credit_check", "broll_submit",
                   "ebook_cover", "cards_render", "broll_collect"],
    "rendering":  ["heygen_download", "shot_map", "covers_ab"],
    "assembling": ["assemble_passA", "assemble_passB", "self_qc",
                   "ebook_pdf", "thumbnail", "youtube_copy"],
}
PCT = {"building": (12, 40), "rendering": (52, 62), "assembling": (66, 92)}
STEP_LABEL = {
    "audit_inputs":   "Checking the inputs",
    "credit_check":   "Checking credits before spending",
    "broll_submit":   "Firing the b-roll generations",
    "ebook_cover":    "Rendering the e-book cover",
    "cards_render":   "Rendering the motion cards",
    "broll_collect":  "Collecting the b-roll clips",
    "heygen_download": "Fetching the HeyGen master",
    "shot_map":       "Building the shot map",
    "covers_ab":      "Preparing cover options A and B",
    "assemble_passA": "Assembling — base motion (pass A)",
    "assemble_passB": "Assembling — cards + audio (pass B)",
    "self_qc":        "Checking my own work (QC)",
    "ebook_pdf":      "Building the e-book PDF",
    "thumbnail":      "Building the thumbnail",
    "youtube_copy":   "Saving the YouTube copy",
}


# --- step implementations ---------------------------------------------------
def step_audit_inputs(ctx):
    # WORDS GATE, defense-in-depth: even if a stale/foreign claim path got us
    # here, never build before the words are approved (the EP09 zombie lesson).
    if not ctx.ep.get("title_approved"):
        raise EngineFlag(
            "Words Gate: the title + byline aren't approved yet — approve the "
            "words on the board, then clear this flag. Nothing is built before "
            "the words are locked.")
    meta = ctx.provider.audit_inputs(ctx.ep)
    ctx.ep_set({"drive_folder": ep_folder(ctx.ep)})
    return meta


def step_credit_check(ctx):
    """Verify-before-spend: the estimate counts only what's actually MISSING.
    A fully staged episode (shakedown, resume) costs nothing and just passes."""
    jobs = ctx.state.get("jobs", {}).get("broll", {})
    clips = ctx.provider.broll_plan(ctx.ep)
    pending = [c for c in clips
               if not jobs.get(c, {}).get("job_id")
               and not ctx.provider.broll_staged(ctx.ep, c)]
    if not pending:
        log(f"   nothing to spend ({len(clips)} clips already staged/submitted)")
        return {"estimate": 0, "pending": []}
    per_clip = ctx.provider.clip_cost(ctx.ep)     # exact preview (no spend)
    ctx.state["clip_cost"] = per_clip
    estimate = len(pending) * per_clip
    if estimate > CREDIT_CEILING:
        raise EngineFlag(
            f"This build is estimated at ~{estimate} Higgsfield credits, over the "
            f"per-episode ceiling of {CREDIT_CEILING:.0f}. Raise the ceiling "
            "(ENGINE_CREDIT_CEILING) or trim the plan, then clear this flag.")
    balance = ctx.provider.balance()
    if balance < estimate:
        raise EngineFlag(
            f"Not starting the b-roll generation: it needs about {estimate} credits "
            f"and only {balance:.0f} are available. Top up, then clear this flag.")
    return {"estimate": estimate, "pending": pending, "balance": balance}


def step_broll_submit(ctx):
    """Fire the gens FIRST. Each job_id is checkpointed the moment it exists —
    a submitted job is never re-submitted (that's the double-spend guard).
    A clip already staged on disk is recorded as such, never regenerated."""
    jobs = ctx.state.setdefault("jobs", {}).setdefault("broll", {})
    clips = ctx.provider.broll_plan(ctx.ep)
    for clip in clips:
        ctx.check_alive()
        if jobs.get(clip, {}).get("job_id"):
            log(f"   {clip}: job already submitted ({jobs[clip]['job_id']}) — skipping")
            continue
        job_id = ctx.provider.submit_broll(ctx.ep, clip)
        jobs[clip] = {"job_id": job_id, "polls": 0}
        ctx.save()                       # checkpoint IMMEDIATELY after the spend
        log(f"   {clip}: {'staged on disk' if job_id.startswith('staged-') else 'submitted'} -> {job_id}")
    return {"clips": clips}


def step_broll_collect(ctx):
    """Poll each job until its clip lands. One bad clip flags the episode; it
    doesn't kill it — finished clips keep their checkpoints."""
    jobs = ctx.state["jobs"]["broll"]
    for clip, job in sorted(jobs.items()):
        ctx.check_alive()
        if job.get("file"):
            log(f"   {clip}: already downloaded — skipping")
            continue
        while True:
            ctx.check_alive()
            path = ctx.provider.poll_broll(ctx.ep, clip, job["job_id"], job["polls"])
            job["polls"] += 1
            ctx.save()
            if path:
                job["file"] = path
                ctx.save()
                log(f"   {clip}: done -> {path}")
                break
    # staged clips cost nothing — only clips we actually submitted count
    generated = sum(1 for j in jobs.values() if not j["job_id"].startswith("staged-"))
    spent = generated * ctx.state.get("clip_cost", CREDITS_PER_BROLL)
    ctx.ep_set({"cost": {"higgsfield_credits": spent, "aud": 0}})
    # contact sheet for the human glance at the render gate (b-roll HARD-FAIL list)
    if hasattr(ctx.provider, "broll_contact"):
        try:
            sheet = ctx.provider.broll_contact(ctx.ep, [j["file"] for _, j in sorted(jobs.items())])
            log(f"   b-roll contact sheet -> {sheet}")
        except Exception as e:
            log(f"   contact sheet skipped ({e})")
    return {"spent_credits": spent, "generated": generated}


def step_ebook_cover(ctx):
    return {"cover": ctx.provider.render_ebook_cover(ctx.ep)}


def step_cards_render(ctx):
    return {"cards": ctx.provider.render_cards(ctx.ep)}


def step_heygen_download(ctx):
    hj = ctx.state.setdefault("jobs", {}).setdefault("heygen", {"polls": 0})
    if hj.get("file"):
        log("   master already downloaded — skipping")
        return {"file": hj["file"]}
    while True:
        ctx.check_alive()
        path = ctx.provider.poll_heygen(ctx.ep, hj["polls"])
        hj["polls"] += 1
        ctx.save()
        if path:
            hj["file"] = path
            ctx.save()
            return {"file": path}
        log(f"   HeyGen not ready yet (poll {hj['polls']}) — waiting")


def step_shot_map(ctx):
    return {"shot_map": ctx.provider.build_shot_map(ctx.ep)}


def step_covers_ab(ctx):
    a, b = ctx.provider.make_covers_ab(ctx.ep)
    ctx.ep_set({"cover_a_url": a, "cover_b_url": b})
    return {"a": a, "b": b}


def step_assemble_passA(ctx):
    return {"passA": ctx.provider.assemble_passA(ctx.ep)}


def step_assemble_passB(ctx):
    out = ctx.provider.assemble_passB(ctx.ep)
    ctx.ep_set({"video_url": out})
    return {"final": out}


def step_self_qc(ctx):
    final = (ctx.state["steps"].get("assemble_passB") or {}).get("meta", {}).get("final")
    return {"qc": ctx.provider.self_qc(ctx.ep, final)}


def step_ebook_pdf(ctx):
    out = ctx.provider.build_ebook(ctx.ep)
    ctx.ep_set({"ebook_url": out})
    return {"ebook": out}


def step_thumbnail(ctx):
    out = ctx.provider.build_thumbnail(ctx.ep)
    ctx.ep_set({"thumbnail_url": out})
    return {"thumbnail": out}


def step_youtube_copy(ctx):
    out = ctx.provider.save_youtube_copy(ctx.ep)
    ctx.ep_set({"youtube_copy": f"see {out}"})
    return {"file": out}


STEP_FNS = {name: fn for name, fn in [
    ("audit_inputs", step_audit_inputs), ("credit_check", step_credit_check),
    ("broll_submit", step_broll_submit), ("ebook_cover", step_ebook_cover),
    ("cards_render", step_cards_render), ("broll_collect", step_broll_collect),
    ("heygen_download", step_heygen_download), ("shot_map", step_shot_map),
    ("covers_ab", step_covers_ab), ("assemble_passA", step_assemble_passA),
    ("assemble_passB", step_assemble_passB), ("self_qc", step_self_qc),
    ("ebook_pdf", step_ebook_pdf), ("thumbnail", step_thumbnail),
    ("youtube_copy", step_youtube_copy),
]}


# --- the run context --------------------------------------------------------
class Ctx:
    def __init__(self, ep, provider, hb, watch, mock):
        self.ep = ep
        self.provider = provider
        self.hb = hb
        self.watch = watch
        self.mock = mock
        self.state = ep.get("build_state") or {}
        self.state.setdefault("phase", "2a")
        self.state["mock"] = mock
        self.state.setdefault("steps", {})

    @property
    def id(self):
        return self.ep["id"]

    def save(self):
        rail.checkpoint(self.id, self.state)

    def ep_set(self, fields):
        self.ep = rail.set_fields(self.id, fields) or self.ep

    def refresh(self):
        self.ep = rail.get_episode(self.id) or self.ep
        return self.ep

    def check_alive(self):
        if self.hb.lost.is_set():
            raise OwnershipLost()


# --- never-freeze step runner ----------------------------------------------
def run_step(ctx, name):
    """Retry transient failures with backoff; flag (and wait) on real trouble.
    The heartbeat thread keeps beating through every sleep — no silent hangs."""
    delays = _retry_delays(ctx.mock)
    attempt = 0
    while True:
        ctx.check_alive()
        attempt += 1
        try:
            meta = STEP_FNS[name](ctx)
            ctx.state["steps"][name] = {
                "done": True, "at": datetime.now(timezone.utc).isoformat(),
                "meta": meta or {}}
            ctx.save()
            return
        except OwnershipLost:
            raise
        except EngineFlag as f:                       # a human is needed — no retry
            flag_and_wait(ctx, name, str(f))
            attempt = 0
        except Exception as e:
            if attempt >= MAX_ATTEMPTS:
                flag_and_wait(ctx, name, (
                    f"{STEP_LABEL[name]} failed {attempt} times "
                    f"(last error: {e}). I've paused this episode — "
                    "when it's sorted, clear this flag and I'll pick it back up."))
                attempt = 0
                continue
            delay = delays[min(attempt - 1, len(delays) - 1)]
            log(f"   {name} attempt {attempt} failed ({e}) — retrying in {delay:.0f}s")
            rail.set_fields(ctx.id, {"retry_count": (ctx.ep.get("retry_count") or 0) + 1})
            ctx.refresh()
            time.sleep(delay)


def flag_and_wait(ctx, name, message):
    """Set the red flag (status unchanged), then wait — heartbeat stays LIVE the
    whole time, so the board shows a paused-but-alive engine, never a dead one."""
    log(f"!! NEEDS A LOOK [{name}]: {message}")
    rail.flag_needs_look(ctx.id, message)
    rail.progress(ctx.id, f"Paused — needs a look ({STEP_LABEL[name]})",
                  ctx.ep.get("progress_pct") or 0)
    if not ctx.watch:
        log("   (not in --watch mode: exiting; restart the engine after clearing the flag)")
        raise SystemExit(3)
    poll = 3 if ctx.mock else 15
    while True:
        ctx.check_alive()
        time.sleep(poll)
        ep = ctx.refresh()
        if not ep.get("needs_look"):
            log(f"   flag cleared — retrying {name}")
            return


# --- phase driver -----------------------------------------------------------
def run_phase(ctx):
    status = ctx.ep["status"]
    steps = PHASES[status]
    lo, hi = PCT[status]
    for i, name in enumerate(steps):
        if ctx.state["steps"].get(name, {}).get("done"):
            log(f"   [{name}] already done — skipping (resume)")
            continue
        pct = lo + (hi - lo) * i // max(1, len(steps) - 1)
        rail.progress(ctx.id, f"{STEP_LABEL[name]} — {i + 1} of {len(steps)}", pct)
        log(f"-- step {name} ({status})")
        run_step(ctx, name)

    # phase complete -> transition
    if status == "building":
        nn = ctx.ep.get("ep_number")
        name = f"PP-EP{int(nn):02d} — {ctx.ep.get('title') or 'Untitled'}" if nn else ctx.ep.get("title")
        ctx.ep_set({"heygen_name": name})
        rail.progress(ctx.id, "Waiting on you — start the HeyGen render", 45)
        ctx.ep_set({"status": "awaiting_render"})
        log(">> parked at awaiting_render (human gate — the render is yours)")
    elif status == "rendering":
        rail.progress(ctx.id, "Waiting on you — pick a cover", 62)
        ctx.ep_set({"status": "awaiting_cover"})
        log(">> parked at awaiting_cover (human gate — pick A or B)")
    elif status == "assembling":
        started = ctx.ep.get("started_at")
        secs = None
        if started:
            secs = int((datetime.now(timezone.utc)
                        - datetime.fromisoformat(started)).total_seconds())
        ctx.ep_set({"status": "awaiting_approval", "build_seconds": secs,
                    "finished_at": datetime.now(timezone.utc).isoformat()})
        rail.progress(ctx.id, "Waiting on you — four approvals", 92)
        rail.release(ctx.id, WORKER)
        log(">> parked at awaiting_approval — my 2a job on this episode is done; released")


# --- main loop ---------------------------------------------------------------
def acquire():
    ep = rail.resume_own(WORKER)
    if ep:
        log(f"resuming my episode PP-EP{ep.get('ep_number')} at {ep['status']}")
        return ep
    ep = rail.claim_next(WORKER, LEASE_SECS)
    if ep:
        log(f"claimed PP-EP{ep.get('ep_number')} ({ep.get('title')!r}) -> building")
        return ep
    ep = rail.reclaim_stale(WORKER, LEASE_SECS)
    if ep:
        log(f"reclaimed a stale-leased episode PP-EP{ep.get('ep_number')} at {ep['status']}")
        return ep
    return None


_CODE_FILES = [Path(__file__).resolve(),
               Path(__file__).resolve().parent / "providers.py",
               PP_VIDEOS / "scripts" / "rail.py"]
_CODE_MTIMES = {p: p.stat().st_mtime for p in _CODE_FILES if p.exists()}
LOCK = ENGINE_DIR / "engine.lock"


def _acquire_lock():
    """Single-instance guard (the EP09 zombie lesson): a stray old engine must
    never share the worker identity with a new one."""
    if LOCK.exists():
        try:
            other = int(LOCK.read_text().strip())
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, other)
            if h:
                # OpenProcess also succeeds on exited processes whose handles
                # linger — only exit code 259 (STILL_ACTIVE) means running.
                code = ctypes.c_ulong()
                alive = k.GetExitCodeProcess(h, ctypes.byref(code)) and code.value == 259
                k.CloseHandle(h)
                if alive:
                    raise SystemExit(
                        f"another engine (pid {other}) is already running — refusing to "
                        "start a second one. Stop it first (engine.lock).")
        except (ValueError, OSError):
            pass                          # stale/unreadable lock — take over
    LOCK.write_text(str(os.getpid()))


def _code_changed():
    """Stale-code guard: a long-lived watch engine must not keep months-old
    logic in memory. If any core file changed since start, exit so the next
    start loads fresh code."""
    for p, m in _CODE_MTIMES.items():
        try:
            if p.stat().st_mtime != m:
                return p.name
        except OSError:
            pass
    return None


def cmd_run(mock, watch):
    _acquire_lock()
    provider = MockProvider(MOCK_ROOT) if mock else RealProvider(PP_VIDEOS)
    log(f"engine up — worker={WORKER} pid={os.getpid()} provider={provider.name} watch={watch}")
    idle_poll = 3 if mock else 30
    while True:
        changed = _code_changed()
        if changed:
            log(f"{changed} changed on disk since start — exiting so fresh code loads "
                "(restart the engine)")
            return
        ep = acquire()
        if not ep:
            if not watch:
                log("nothing to do (no claimable episode) — exiting")
                return
            time.sleep(idle_poll)
            continue

        hb = Heartbeat(ep["id"])
        ctx = Ctx(ep, provider, hb, watch, mock)
        try:
            while True:
                status = ctx.refresh().get("status")
                if ctx.ep.get("needs_look"):
                    # flagged (maybe by a previous run) — wait for the human
                    hb.active.set()
                    log("episode is flagged 'needs a look' — waiting (heartbeat live)")
                    poll = 3 if mock else 15
                    while ctx.refresh().get("needs_look"):
                        ctx.check_alive()
                        time.sleep(poll)
                    log("flag cleared — carrying on")
                    continue
                if status in PHASES:
                    hb.active.set()
                    run_phase(ctx)
                    hb.active.clear()
                elif status in HUMAN_GATES:
                    hb.active.clear()          # board ignores heartbeat at gates
                    if status == "awaiting_approval" or not watch:
                        log(f"parked at {status} — done here for now")
                        break
                    time.sleep(idle_poll)      # watch: wait for the gate to open
                elif status == "revising":
                    hb.active.set()
                    flag_and_wait(ctx, "audit_inputs",
                                  "A change was requested, but the revise loop is "
                                  "Phase 3 — I can't do targeted re-dos yet. Make the "
                                  "change manually, set the status forward, then clear this flag.")
                else:                           # ready / published / unknown
                    rail.release(ctx.id, WORKER)
                    log(f"episode is {status} — nothing for the engine; released")
                    break
        except OwnershipLost:
            log("stopped work on the episode (ownership lost) — moving on")
        except SystemExit:
            raise
        finally:
            hb.stop()
        if not watch:
            return


# --- admin commands ----------------------------------------------------------
def cmd_mock_episode():
    ep = rail.insert({
        "ep_number": 99, "title": "Mock Episode — Spine Test", "status": "queued",
        "source_url": "https://example.com/mock-article",
        "created_by": "engine-mock",
        "title_approved": True,   # mock pre-passes the Words Gate (claim filter)
        "notes": "Byline: a mock byline for the spine test",
    })
    log(f"mock ticket created: PP-EP99 id={ep['id']}")


def cmd_cleanup_mock():
    n = 0
    for ep in rail.list_all():
        if ep.get("created_by") == "engine-mock":
            rail.delete(ep["id"])
            n += 1
    if MOCK_ROOT.exists():
        shutil.rmtree(MOCK_ROOT)
    log(f"cleaned up {n} mock ticket(s) + {MOCK_ROOT}")


def cmd_status():
    for ep in rail.list_all():
        flag = " ⚠NEEDS-LOOK" if ep.get("needs_look") else ""
        lease = f" lease={ep.get('claimed_by')}" if ep.get("claimed_by") else ""
        print(f"PP-EP{ep.get('ep_number')}  {ep.get('status'):<18} "
              f"{(ep.get('progress_step') or ''):<44}{lease}{flag}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["run", "mock-episode", "status", "cleanup-mock"])
    ap.add_argument("--mock", action="store_true", help="mock providers (no credits)")
    ap.add_argument("--watch", action="store_true", help="keep working across gates")
    a = ap.parse_args()
    if a.cmd == "run":
        cmd_run(a.mock, a.watch)
    elif a.cmd == "mock-episode":
        cmd_mock_episode()
    elif a.cmd == "status":
        cmd_status()
    elif a.cmd == "cleanup-mock":
        cmd_cleanup_mock()
