#!/usr/bin/env python3
"""engine.py — the Episode Studio orchestrator spine (Phase 2a).

ONE episode at a time, crash-safe, never silently frozen. The conductor:
  * claims a queued episode via the LEASE (claimed_by + lease_until) — single
    writer; a stale lease (crashed worker) is reclaimable;
  * drives it through the status contract in THE LOCKED ORDER (below) — the
    render gate opens FIRST and the gens batch runs beside it, so the long
    pole starts early and the human turns cluster at the front;
  * checkpoints EVERY step into build_state (steps done + job IDs), so a
    memoryless restart resumes exactly where it left off — a finished gen or
    render is never re-run, credits are never double-spent;
  * heartbeats constantly while working; retries transient failures with
    backoff; if a step still fails, writes a plain-English "Needs a look"
    (the episode KEEPS its status) and waits for the flag to clear;
  * pauses at the sacred human gates — the words, the render, the cover pick,
    the four approvals — and never auto-renders, never auto-publishes. Turns
    2 and 3 (render + cover) are OFFERED early and waited on in place, so the
    operator answers them back-to-back at the front instead of ping-ponging;
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
import hashlib
import json
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
# 65, RAISED FROM 60 ON 3 AUG 2026 — and the number is arithmetic, not a round-up.
# MEASURED from EP14's own rail row: clip_cost 7.5, cover heroes 4.0. EP13 ran 6 b-roll
# clips, EP14 ran 7 = 56.5 against a ceiling of 60, i.e. THREE AND A HALF CREDITS OF
# HEADROOM — less than half a clip. The next episode needing 8 clips costs 64 and would
# have halted before spending anything, telling a browser operator to set an ENVIRONMENT
# VARIABLE. That is a stop Hugh cannot clear, and it was coming on arithmetic.
#
# WHY 65 AND NOT 75 (Jodie, 3 Aug): the balance is 131.72 credits on the "plus" plan —
# 2.3 episodes of runway. THE CEILING IS A BUDGET GUARD AS WELL AS A NUISANCE GUARD. At
# 75 a single episode could take well over half of what is left. 65 clears the stop that
# is actually coming (8 clips = 64) and still refuses a runaway: 9 clips = 71.5 HALTS,
# and while the balance is this low it should.
CREDIT_CEILING = float(os.environ.get("ENGINE_CREDIT_CEILING", "65"))  # per episode

# --- rail integrity gate (26 Jul 2026; git-backed from 28 Jul 2026) ---------
# rail.py holds the Script Gate's enforcement — the claim filter that refuses to
# hand out an episode nobody has read the script for. A revert would disable that
# guarantee SILENTLY: the engine keeps running and the board still looks healthy.
#
# It now lives IN THE REPO (engine/rail.py), so the gate compares it against git
# HEAD instead of against a checked-in duplicate. Stronger, not weaker: it catches
# an UNCOMMITTED edit, which the old reference-copy gate could not see, and it
# cannot be defeated by editing two files. See engine/gitgate.py for the full
# reasoning. No bypass flag, no environment variable, and --mock does NOT skip it
# (mock still writes to the real rail).
from gitgate import assert_committed      # noqa: E402  (must precede `import rail`)

RAIL_SHA = assert_committed(
    "engine/rail.py",
    gate="RAIL INTEGRITY GATE",
    why="rail.py carries the Script Gate's claim filter. Rather than run on a\n"
        "version nobody has reviewed, the engine stops here.",
    code=4)                            # runs BEFORE the import below. No bypass.

import rail  # the one shared Supabase client (RAIL-INTEGRATION.md)

import preflight_episode_json                  # E26 — the config pre-flight (module,
                                               # because engine.py imports NAMES from
                                               # providers and that is what bit EP15)
from providers import (EngineFlag, MockProvider, RealProvider, ep_folder,
                       assert_standing_assets)

HUMAN_GATES = {"awaiting_render", "awaiting_cover", "awaiting_approval"}

# --- THE LOCKED ORDER (approved by Jodie, 26 Jul 2026) ----------------------
# Do NOT re-sequence without Jodie's explicit re-approval. The shape that
# matters: human turns 1-2-3 cluster back-to-back at the FRONT, then a long
# hands-off render window, then turn 4 at the END. The HeyGen render is the
# LONG POLE (5-45 min) and depends only on the spoken track — which is final at
# the Words Gate — so it starts EARLY, never last, and never behind the visuals.
LOCKED_ORDER = (
    "1 script + words · 2 SCRIPT GATE + WORDS GATE (read the script, approve "
    "title/hook/byline) · 3 render gate AND the gens batch (b-roll + cover heroes "
    "A/B + cards) fire IN PARALLEL · 4 cover pick WHILE Gordon renders · 5 engine "
    "finishes hands-off · 6 master -> shot map -> assembly -> QC · 7 the four "
    "approvals · 8 publish + Stage-8 close-out"
)


# --- THE SCRIPT GATE (designed by Jodie, 26 Jul 2026) — NO OVERRIDE ------------
# Approving the script is a DECISION. Decisions stay human, forever — including
# after HeyGen auto-render lands. Starting a render is a CHORE and may one day be
# automated; what Gordon SAYS may not. Automation eats chores, never decisions.
#
# This is a guard, not a convention. There is no flag, no fast path, no exception,
# no environment variable and no --force that gets past it. Any future auto-render
# path MUST call assert_script_gate() before it submits anything to HeyGen. If you
# are reading this while adding auto-render: call it, don't route around it.
def assert_script_gate(ep):
    """Raise unless BOTH halves of the gate are set by a human. Callers that
    submit a render, or build anything from the script, must call this first."""
    if not ep.get("title_approved"):
        raise EngineFlag(
            "SCRIPT GATE: the words (title / hook / byline) aren't approved yet. "
            "Approve them on the board, then clear this flag. Nothing builds and "
            "nothing renders before the words are locked.")
    if not ep.get("script_read"):
        raise EngineFlag(
            "SCRIPT GATE: nobody has ticked \"I've read the script\" yet. Open the "
            "script Doc from the board, read it, tick the box, then clear this "
            "flag. Approving the script is a decision — it never happens "
            "automatically, and there is no way around this gate.")
    return True


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


# --- the step lists (THE LOCKED ORDER) --------------------------------------
# building: the render gate opens FIRST (step 3a — Gordon starts cooking), then
# the whole gens batch fires beside it (step 3b) — b-roll AND both cover heroes,
# so the cover pick (step 4) reaches the operator while the render is still
# running. Everything after the pick is hands-off (step 5).
PHASES = {
    "building":   ["script_sync", "audit_inputs", "render_gate", "credit_check",
                   "broll_submit", "covers_ab", "broll_collect",
                   "cover_pick", "ebook_cover", "cards_render"],
    "rendering":  ["heygen_download", "shot_map"],
    "assembling": ["assemble_passA", "assemble_passB", "self_qc",
                   "ebook_pdf", "thumbnail", "youtube_copy"],
}
PCT = {"building": (12, 40), "rendering": (52, 62), "assembling": (66, 92)}
STEP_LABEL = {
    "script_sync":    "Re-reading the approved script from Drive",
    "audit_inputs":   "Checking the inputs",
    "render_gate":    "Opening the render gate — Gordon can start now",
    "credit_check":   "Checking credits before spending",
    "broll_submit":   "Firing the b-roll generations",
    "covers_ab":      "Generating the two cover heroes (A and B)",
    "broll_collect":  "Collecting the b-roll clips",
    "cover_pick":     "Waiting on you — pick a cover",
    "ebook_cover":    "Rendering the e-book cover from your pick",
    "cards_render":   "Rendering the motion cards",
    "heygen_download": "Fetching the HeyGen master",
    "shot_map":       "Building the shot map",
    "assemble_passA": "Assembling — base motion (pass A)",
    "assemble_passB": "Assembling — cards + audio (pass B)",
    "self_qc":        "Checking my own work (QC)",
    "ebook_pdf":      "Building the e-book PDF",
    "thumbnail":      "Building the thumbnail",
    "youtube_copy":   "Saving the YouTube copy",
}


# --- the order guard (R5: the order can't silently regress) -----------------
def order_warn(ctx, what):
    """Name the breach AND the locked order, loudly, in the log and durably in
    build_state — so a re-sequencing shows up on the very next run instead of
    being discovered on a finished episode (the EP10 lesson)."""
    line = f"{what}. LOCKED ORDER (approved 26 Jul 2026): {LOCKED_ORDER}"
    warns = ctx.state.setdefault("order", {}).setdefault("warnings", [])
    if line not in warns:
        warns.append(line)
        ctx.save()
    log("!! LOCKED ORDER WARNING: " + line)


def check_locked_order():
    """Static self-check of the step lists, run at engine start. If someone
    re-sequences PHASES the engine says so before it touches an episode."""
    b, r = PHASES["building"], PHASES["rendering"]
    def before(x, y):
        return x in b and y in b and b.index(x) < b.index(y)
    problems = []
    if not before("script_sync", "audit_inputs"):
        problems.append("the script must be re-read from its Doc BEFORE the "
                        "render-ready scan — the scan has to check the words the "
                        "operator actually approved, not a stale local draft")
    if not before("script_sync", "render_gate"):
        problems.append("the script must be re-read from its Doc BEFORE the "
                        "render gate opens — a render must never be offered on "
                        "text nobody approved")
    if not before("render_gate", "broll_submit"):
        problems.append("the render gate must open BEFORE the gens batch fires "
                        "(the render is the long pole — it never waits on pictures)")
    if "covers_ab" not in b or "covers_ab" in r:
        problems.append("the two cover heroes must be generated in the BUILDING "
                        "gens batch, not after the HeyGen master lands")
    if not before("covers_ab", "broll_collect"):
        problems.append("the cover heroes must be made before the long b-roll "
                        "collect, so the pick reaches the operator during the render")
    if not before("cover_pick", "ebook_cover"):
        problems.append("the e-book cover page is built FROM the picked hero")
    if not before("ebook_cover", "cards_render"):
        problems.append("the end card composites the real e-book cover")
    for p in problems:
        log(f"!! LOCKED ORDER WARNING (step list): {p}. "
            f"LOCKED ORDER (approved 26 Jul 2026): {LOCKED_ORDER}")
    return problems


# --- step implementations ---------------------------------------------------
def _script_drift_check(ctx):
    """Has the Doc moved since the text we snapshotted? FLAG it on the card —
    never block, and never silently re-sync. The snapshot stays the record of
    what was actually approved and rendered; the flag tells the operator their
    later edit did NOT make it into this build."""
    baseline = ctx.ep.get("script_sha256")
    if not baseline:
        return
    try:
        _text, sha, _src = ctx.provider.fetch_script(ctx.ep, write=False)
    except Exception as e:
        log(f"   (couldn't re-check the script Doc for drift: {e}) — carrying on")
        return
    changed = sha != baseline
    if changed != bool(ctx.ep.get("script_changed_since_approval")):
        ctx.ep_set({"script_changed_since_approval": changed})
    if changed:
        log("!! the script Doc has CHANGED since it was approved. This build is "
            f"using the approved snapshot (sha {baseline[:12]}), NOT the current "
            "Doc. Flagged on the board — not blocking.")


def step_script_sync(ctx):
    """THE SCRIPT GATE, enforced — and the re-read that makes it mean something.

    The Google Doc is the ONE HOME of the script. The operator has just read it
    on the board and almost certainly edited it, so the engine throws away its
    own local draft and rebuilds docs/spoken-words.txt from the Doc. A studio
    that ignores its reviewer's edits is worse than no gate at all.

    If the Doc can't be read we FLAG — loudly, in plain English — and stop. We
    never quietly fall back to the stale local draft."""
    assert_script_gate(ctx.ep)                      # no override, ever
    text, sha, source = ctx.provider.fetch_script(ctx.ep)
    words = len(text.split())
    ctx.ep_set({
        "script_snapshot": text,                    # exactly what gets rendered
        "script_sha256": sha,
        "script_approved_at": datetime.now(timezone.utc).isoformat(),
        "script_locked_at": datetime.now(timezone.utc).isoformat(),
        "script_changed_since_approval": False,     # fresh read = fresh baseline
    })
    ctx.stamp("script_synced_at")
    log(f"   script re-read from {source} — {words} words, sha {sha[:12]} "
        "(this exact text is what gets built and rendered)")
    return {"words": words, "sha256": sha, "source": source}


def _preflight_config(ctx) -> list[str]:
    """Diff this episode's episode.json against the last two that built cleanly.

    Returns log lines. Raises EngineFlag on anything that will certainly cost a halt.

    ⚠️ IT MUST NEVER BE THE REASON A BUILD CANNOT START. If there are not two usable
    reference episodes — a fresh machine, an early episode, a mock run — it says so and
    stands aside. A pre-flight that blocks take-off because it cannot find its own
    paperwork is worse than no pre-flight.
    """
    nn = ctx.ep.get("ep_number")
    if ctx.mock or not nn:
        return ["config pre-flight: skipped (mock)"]
    target = ctx.provider.dir(ctx.ep) / "docs/episode.json"
    if not target.is_file():
        return ["config pre-flight: no episode.json yet — nothing to compare"]

    refs, names = [], []
    for n in range(int(nn) - 1, 0, -1):          # the most recent episodes, newest first
        if len(refs) == 2:
            break
        try:
            p = preflight_episode_json.ep_dir(n) / "docs/episode.json"
            refs.append(json.loads(p.read_text(encoding="utf-8")))
            names.append(f"EP{n:02d}")
        except Exception:                                             # noqa: BLE001
            continue
    if len(refs) < 2:
        return ["config pre-flight: fewer than two reference episodes — standing aside"]

    j = json.loads(target.read_text(encoding="utf-8"))
    res = preflight_episode_json.preflight(j, refs)
    if res["must"]:
        raise EngineFlag(
            "This episode's settings differ from the last two episodes in ways that "
            "will stop the build later on:\n"
            + "\n".join(f"      • {m}" for m in res["must"])
            + "\n    Every one of these has cost a build before. They are cheaper to "
              "fix now than eighteen steps in, which is why I look before I start.")
    out = [f"config pre-flight: clean against {' + '.join(names)}"]
    out += [f"   note — {w}" for w in res["worth"]]
    return out


def step_audit_inputs(ctx):
    # Defence-in-depth: even if a stale or foreign claim path got us here, never
    # build before the gate has passed (the EP09 zombie lesson).
    assert_script_gate(ctx.ep)
    # THE HEAD OF THE BUILD is where a knowable absence belongs. The standing assets
    # are identical every episode; a missing one used to surface at Pass B, after the
    # credits were spent and the render paid for. Three of them were found that way,
    # on three separate episodes.
    # ⚠️ THIS LINE READ `providers.assert_standing_assets()` AND KILLED EP15's BUILD.
    # engine.py imports NAMES from providers, never the module, so `providers` was
    # never bound — a guaranteed NameError the first time this step ran for real.
    # test_bundle_a.py was green throughout: it imported providers itself and called
    # the function directly, proving the function worked and never once proving the
    # ENGINE could call it. See test_step_call_sites.py.
    log(f"   {assert_standing_assets()}")
    # E26 — THE CONFIG PRE-FLIGHT. Seven of EP15's nine halts were one unvalidated
    # file, each found by running into it hours apart, each a convention EP11-EP14 all
    # followed that nothing anywhere states. Diffed here, at the head of the build,
    # against the last two episodes that built cleanly — TWO references, never one,
    # because a rule inferred from a single sample was wrong on all three axes when it
    # was tried. Blocks on what will certainly cost a halt; merely NAMES the rest.
    for line in _preflight_config(ctx):
        log(f"   {line}")
    meta = ctx.provider.audit_inputs(ctx.ep)
    ctx.ep_set({"drive_folder": ep_folder(ctx.ep)})
    return meta


def step_render_gate(ctx):
    """HUMAN TURN 2 opens HERE — the moment the words are locked and the spoken
    track has passed the render-ready scan, NOT at the end of the build.

    The HeyGen render is the LONG POLE (5-45 min) and depends only on the spoken
    track, which is final at the Words Gate. So it starts now and cooks while the
    engine makes the pictures. Nothing about this step blocks: the engine names
    the project, opens the gate, and carries straight on to the gens batch.

    THE HARD RULE: a render — this one by hand, and any future auto-render — may
    NEVER fire on a script that hasn't passed the Script Gate. Checked here, at
    the last moment before a human (or a machine) is invited to press go."""
    assert_script_gate(ctx.ep)                      # no override, ever
    _script_drift_check(ctx)
    nn = ctx.ep.get("ep_number")
    name = (f"PP-EP{int(nn):02d} — {ctx.ep.get('title') or 'Untitled'}"
            if nn is not None else (ctx.ep.get("title") or "Untitled"))
    ctx.ep_set({"heygen_name": name})
    ctx.stamp("render_offered_at")
    rail.progress(ctx.id, "Your turn — start the HeyGen render (I keep building)", 16)
    log(f">> RENDER GATE OPEN — start Gordon's render for {name!r} NOW; "
        "I'm firing the pictures at the same time (they run in parallel)")
    return {"heygen_name": name}


def step_credit_check(ctx):
    """Verify-before-spend: the estimate counts only what's actually MISSING —
    the b-roll clips AND the two cover heroes, which are part of the same
    gens-first batch. A fully staged episode (shakedown, resume) costs nothing
    and just passes."""
    jobs = ctx.state.get("jobs", {}).get("broll", {})
    clips = ctx.provider.broll_plan(ctx.ep)
    pending = [c for c in clips
               if not jobs.get(c, {}).get("job_id")
               and not ctx.provider.broll_staged(ctx.ep, c)]
    covers = ctx.provider.cover_cost(ctx.ep)      # 0 once both heroes are staged
    per_clip = ctx.provider.clip_cost(ctx.ep) if pending else 0.0
    if pending:
        ctx.state["clip_cost"] = per_clip
    estimate = len(pending) * per_clip + covers
    if estimate <= 0:
        log(f"   nothing to spend ({len(clips)} clips + both cover heroes "
            "already staged/submitted)")
        return {"estimate": 0, "pending": [], "covers": 0}
    log(f"   estimate ~{estimate:.0f} credits ({len(pending)} b-roll clips "
        f"+ {covers:.0f} for the cover heroes)")
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
    return {"estimate": estimate, "pending": pending, "covers": covers,
            "balance": balance}


def step_broll_submit(ctx):
    """Fire the gens batch. Each job_id is checkpointed the moment it exists —
    a submitted job is never re-submitted (that's the double-spend guard).
    A clip already staged on disk is recorded as such, never regenerated."""
    ctx.stamp("gens_started_at")
    if not ctx.state.get("order", {}).get("render_offered_at"):
        order_warn(ctx, "the gens batch started before the render gate was opened "
                        "— the long pole is being made to wait on the pictures")
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
    # contact sheet for the human glance BEFORE assembly (b-roll HARD-FAIL list).
    # Under the locked order the render gate is long past by now — this lands
    # while the operator is picking the cover, which is the right moment to look.
    if hasattr(ctx.provider, "broll_contact"):
        try:
            sheet = ctx.provider.broll_contact(ctx.ep, [j["file"] for _, j in sorted(jobs.items())])
            log(f"   b-roll contact sheet -> {sheet}")
        except Exception as e:
            log(f"   contact sheet skipped ({e})")
    return {"spent_credits": spent, "generated": generated}


def step_covers_ab(ctx):
    """The two cover heroes, generated UPFRONT in the gens-first batch (~4
    credits, previewed before the spend) — so the build never parks mid-run on
    "no e-book cover, needs a look", and so HUMAN TURN 3 can be surfaced while
    Gordon is still rendering."""
    a, b = ctx.provider.make_covers_ab(ctx.ep)
    ctx.ep_set({"cover_a_url": a, "cover_b_url": b})
    ctx.stamp("covers_ready_at")
    if ctx.state.get("order", {}).get("master_at"):
        order_warn(ctx, "the cover pick was surfaced AFTER the HeyGen master "
                        "landed — it belongs in the render window, not after it")
    log(">> COVER PICK is open (both heroes exist) — pick A or B on the board; "
        "the render keeps cooking while you do")
    return {"a": a, "b": b}


def step_cover_pick(ctx):
    """HUMAN TURN 3. Both heroes have existed since the gens batch, so the board
    has been showing this pick for the whole b-roll collect — normally the answer
    is already in and this step just reads it. If it isn't, we wait here (status
    stays 'building', heartbeat live) rather than ping-ponging the status."""
    waited = 0
    while True:
        ctx.check_alive()
        choice = (ctx.refresh().get("cover_choice") or "").strip().upper()
        if choice in ("A", "B"):
            ctx.stamp("cover_picked_at")
            log(f"   cover {choice} picked — building the cover page from it")
            return {"choice": choice}
        if ctx.mock and waited >= 2:
            # mock has no human; auto-answer so `run --mock --watch` exercises the
            # whole spine. NEVER reachable in real mode — the gate stays sacred.
            rail.set_fields(ctx.id, {"cover_choice": "A"})
            log("   (mock) no human here — auto-picking cover A to exercise the spine")
            continue
        if not ctx.watch:
            log("   the cover pick is yours and I'm not in --watch mode: exiting. "
                "Pick A or B on the board, then restart the engine.")
            raise SystemExit(3)
        if waited == 0:
            rail.progress(ctx.id, "Waiting on you — pick a cover (A or B)", 33)
            log(">> waiting on the cover pick (the render is still cooking)")
        waited += 1
        time.sleep(3 if ctx.mock else 15)


def step_ebook_cover(ctx):
    """Built FROM the pick: the chosen hero becomes the active hero, then the
    cover page re-renders over it. The end card composites this cover next."""
    choice = (ctx.ep.get("cover_choice") or "A").strip().upper()
    return {"cover": ctx.provider.render_ebook_cover(ctx.ep, choice),
            "from_hero": choice}


# ── the per-step watchdog (D13, 3 Aug 2026) ─────────────────────────────────
#
# THE HEARTBEAT PROVES THE ENGINE, NOT THE STEP. EP14 sat on assemble_passB for three
# and a half days with a healthy six-second heartbeat, and nothing anywhere could say
# so. Jodie noticed. Hugh will not be looking — that is the entire point.
#
# Three states currently look identical on the board and only ONE is a fault:
#     working            — making progress
#     waiting on a human — a flag is up, legitimate, may last days
#     stuck              — no flag, no progress, nobody coming
#
# The board can already see the second (needs_look). What it could not see was how long
# THIS step had been running, because build_state records only COMPLETED steps. So the
# engine now stamps the step in flight before running it.
#
# BUDGETS ARE MEASURED, NOT GUESSED, and generous — this is a "nobody is coming" alarm,
# not a performance target. `None` means the step waits on a human BY DESIGN and must
# never raise one: heygen_download polls until Jodie has run the render, which can
# legitimately take days with no flag up.
STEP_BUDGET_S = {
    "heygen_download": None,      # waits for Jodie's HeyGen render — no flag, no alarm
    "cover_pick":      None,      # waits for a human choice
    "render_gate":     None,      # waits for the render to be started
    "assemble_passA":  45 * 60,   # EP14 measured ~15 min at 688s of video
    "assemble_passB":  45 * 60,   # EP13 265s, EP14 ~10 min
    "cards_render":    30 * 60,   # EP14 ~4 min for 14 pages, plus Chromium start-up
    "broll_collect":   40 * 60,   # Higgsfield queue, 7 clips
    "ebook_build":     20 * 60,
    "self_qc":         20 * 60,
}
DEFAULT_STEP_BUDGET_S = 15 * 60


def mark_step_started(ctx, name):
    """Stamp the step in flight, and SAVE IT — a stuck step never gets to save later."""
    ctx.state["current"] = {
        "step": name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "budget_s": STEP_BUDGET_S.get(name, DEFAULT_STEP_BUDGET_S),
    }
    ctx.save()


def clear_step_started(ctx):
    """A finished step is not in flight. Left behind, it reads as stuck forever."""
    if ctx.state.pop("current", None) is not None:
        ctx.save()


def step_cards_render(ctx):
    """Render the cards, then ask for the ONE look that cannot be automated.

    THE ORDER HERE IS THE WHOLE POINT (3 Aug 2026). The review used to be raised from
    inside `render_cards`, which meant the step never returned and the engine never
    got to record anything — so the preview's location existed only in the flag's
    prose. The URL is now published and SAVED INTO build_state BEFORE the flag is
    raised, so the board has something to render an <img> from. build_state is jsonb
    and already there: no schema change, which has been a standing rule since the
    start and is not worth breaking for a preview URL.
    """
    cards = ctx.provider.render_cards(ctx.ep)
    url = ctx.provider.publish_title_preview(ctx.ep)
    if url:
        ctx.state["title_preview_url"] = url
        ctx.save()                       # saved BEFORE the flag, or it is lost
    ctx.provider.title_placement_review_for(ctx.ep, url)
    return {"cards": cards, "title_preview": url}


def _master_landed(ctx):
    """Stamp when the long pole finished, and check the order held: by now the
    cover heroes must have existed for a long while."""
    ctx.stamp("master_at")
    if not ctx.state.get("order", {}).get("covers_ready_at"):
        order_warn(ctx, "the HeyGen master landed before the cover heroes even "
                        "existed — the cover pick has been pushed to the end")


def step_heygen_download(ctx):
    hj = ctx.state.setdefault("jobs", {}).setdefault("heygen", {"polls": 0})
    if hj.get("file"):
        log("   master already downloaded — skipping")
        _master_landed(ctx)
        return {"file": hj["file"]}
    while True:
        ctx.check_alive()
        try:
            path = ctx.provider.poll_heygen(ctx.ep, hj["polls"])
        except RuntimeError as e:
            # "no completed render yet" — a WAIT, not a failure. The render is a
            # human step that can take as long as it takes; poll forever (the
            # heartbeat keeps the lease alive). EngineFlag still propagates.
            hj["polls"] += 1
            ctx.save()
            if hj["polls"] % 10 == 1:
                log(f"   HeyGen not ready yet (poll {hj['polls']}) — waiting ({e})")
            time.sleep(60)
            continue
        hj["polls"] += 1
        ctx.save()
        if path:
            hj["file"] = path
            ctx.save()
            _master_landed(ctx)
            return {"file": path}
        log(f"   HeyGen not ready yet (poll {hj['polls']}) — waiting")
        time.sleep(60)


def step_shot_map(ctx):
    return {"shot_map": ctx.provider.build_shot_map(ctx.ep)}


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
    ("script_sync", step_script_sync),
    ("audit_inputs", step_audit_inputs), ("render_gate", step_render_gate),
    ("credit_check", step_credit_check),
    ("broll_submit", step_broll_submit), ("covers_ab", step_covers_ab),
    ("broll_collect", step_broll_collect), ("cover_pick", step_cover_pick),
    ("ebook_cover", step_ebook_cover), ("cards_render", step_cards_render),
    ("heygen_download", step_heygen_download), ("shot_map", step_shot_map),
    ("assemble_passA", step_assemble_passA),
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

    def stamp(self, key):
        """Record WHEN a locked-order milestone happened (first time only, so a
        resume never rewrites history). These timestamps are what the order
        guard compares."""
        o = self.state.setdefault("order", {})
        if not o.get(key):
            o[key] = datetime.now(timezone.utc).isoformat()
            self.save()
        return o[key]

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
            mark_step_started(ctx, name)          # so a stuck step is visible
            meta = STEP_FNS[name](ctx)
            ctx.state["steps"][name] = {
                "done": True, "at": datetime.now(timezone.utc).isoformat(),
                "meta": meta or {}}
            clear_step_started(ctx)
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
        # E11 part 1 — THE STALE-CODE GUARD, WHERE IT IS ACTUALLY NEEDED.
        # `_code_changed()` is otherwise checked only at the top of the OUTER acquire
        # loop, which a claimed episode never returns to. This wait is where a flagged
        # engine spends all its time, and it is the safest possible moment to exit:
        # the step has already raised, so no ffmpeg, no HeyGen call and no Higgsfield
        # job is in flight.
        # ⚠️ THIS LOOP, NOT ONLY THE OUTER ONE. EP15, 3 Aug 2026: `audit_inputs` flagged
        # on a NameError, the fix landed at 09:10, and the process sat HERE running the
        # broken code until a manual restart at 10:08 — Jodie cleared the flag at 10:03
        # and it walked straight back into the same bug.
        _code_changed_exit(ctx, "while this episode was flagged")
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
        # The render gate opened at the START of this phase (step render_gate),
        # so by now Gordon is normally already rendering — we go straight to the
        # hands-off render window. Parking at awaiting_render means the operator
        # never took turn 2, which is an order breach worth naming.
        if ctx.ep.get("render_started_at"):
            rail.progress(ctx.id, "Gordon's render is cooking — I'll fetch the "
                                  "master the moment it lands", 48)
            ctx.ep_set({"status": "rendering"})
            log(">> render already running (started during the build, as the "
                "locked order intends) -> rendering")
        else:
            order_warn(ctx, "the whole gens batch finished and Gordon's render "
                            "still hasn't been started — the long pole is running last")
            rail.progress(ctx.id, "Waiting on you — start the HeyGen render", 45)
            ctx.ep_set({"status": "awaiting_render"})
            log(">> parked at awaiting_render (human gate — the render is yours)")
    elif status == "rendering":
        # The cover was picked back in the build (step cover_pick), so this is
        # normally a straight walk into assembly. The awaiting_cover park stays
        # as the honest fallback for an episode that skipped that step.
        if (ctx.ep.get("cover_choice") or "").strip().upper() in ("A", "B"):
            log(">> cover already picked during the render window — straight to assembling")
            ctx.ep_set({"status": "assembling"})
        else:
            order_warn(ctx, "the cover still isn't picked and the master has "
                            "landed — the pick should have been answered during the render")
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
def _why_idle():
    """Nothing claimable — say WHY, once. An engine sitting silently while a
    queued episode waits on a human gate is the most confusing failure there is,
    and the Script Gate makes it more likely (two halves to forget, not one)."""
    try:
        waiting = []
        for ep in rail.list_queued():
            missing = []
            if not ep.get("title_approved"):
                missing.append("words not approved")
            if not ep.get("script_read"):
                missing.append("\"I've read the script\" not ticked")
            if missing:
                waiting.append(f"PP-EP{ep.get('ep_number')}: {' + '.join(missing)}")
        if waiting:
            log("waiting on the Script Gate — " + "; ".join(waiting))
    except Exception as e:
        log(f"(couldn't explain the idle state: {e})")


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


# --- the stale-code watch list: DERIVED, NEVER ENUMERATED --------------------
#
# 🔴 THIS WAS A HAND-WRITTEN LIST OF THREE — engine.py, providers.py, rail.py —
# AND IT WENT STALE THE DAY THE ENGINE GREW A FOURTH MODULE.
#
# EP16, 5 Aug 2026: `preflight_episode_json.py` was fixed at 10:43 and the running
# engine went on using the broken copy for six hours, flagging EP16 on a false
# positive that no longer existed on disk. The guard was working perfectly — it ran
# roughly a thousand times that day — and saw nothing, because the file that changed
# was not one of its three. `check_page_images.py` and `gitgate.py` were equally
# invisible.
#
# THE FIX IS THE ONE THAT KEEPS WORKING: ask the INTERPRETER what it loaded, rather
# than asking a human to remember. A new module cannot be forgotten, because
# IMPORTING IT IS WHAT PUTS IT ON THE LIST.
#
# Same shape as check_page_images (ask the PAGE what images it needs) and
# test_preflight_build_written (grep the CODE for what the build writes).
# See CLAUDE.md fault #7.
def _watched_files() -> set[Path]:
    """Every .py the engine has actually imported from ENGINE_DIR, plus itself."""
    files = {Path(__file__).resolve()}
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            p = Path(f).resolve()
        except (OSError, ValueError):
            continue
        if p.suffix == ".py" and p.parent == ENGINE_DIR:
            files.add(p)
    return files


_CODE_MTIMES = {p: p.stat().st_mtime for p in _watched_files() if p.exists()}
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
    logic in memory. If any file it IMPORTED changed since start, exit so the
    next start loads fresh code.

    Re-derives the watch set each call, so a module imported lazily after start
    is BASELINED rather than reported as changed — otherwise the first sight of
    a late import would look like an edit and exit the engine for nothing.
    """
    for p in _watched_files():
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if p not in _CODE_MTIMES:
            _CODE_MTIMES[p] = m          # newly imported — baseline, do not fire
            continue
        if m != _CODE_MTIMES[p]:
            return p.name
    return None


def _code_changed_exit(ctx, when: str) -> None:
    """Exit cleanly if the code changed under us. RAISES SystemExit; never returns True.

    E11 part 1. Call this from anywhere the engine WAITS while holding an episode.

    ⚠️ IT RAISES RATHER THAN RETURNING A FLAG, and that is not a style choice. The two
    call sites want opposite things from a bare `return`: in the outer acquire loop it
    ends the run, but in `flag_and_wait` it means "the flag cleared, RETRY THE STEP" —
    which would retry it on exactly the stale code we are trying to escape. One
    behaviour, decided here, so no call site can get it subtly wrong.
    SystemExit derives from BaseException, so the `except Exception` handlers around
    the phase driver do not swallow it.

    ⚠️ `rail.release()` MATTERS: exiting while still holding the lease leaves the
    episode claimed by a worker that no longer exists, and `reclaim_stale()` cannot
    take it back until the lease expires. Worse, releasing WITHOUT clearing ownership
    is how an episode reaches a working status with `claimed_by: NULL` — the dead zone,
    which nothing can pick up, ever.

    THIS IS NOT A DEPLOY PATH ON ITS OWN. The board still cannot say "this engine is
    running code older than the repo", which is E11 part 2 and the half Hugh needs,
    because for him that state is undiagnosable.
    """
    changed = _code_changed()
    if not changed:
        return
    log(f"{changed} changed on disk {when} — exiting so fresh code loads "
        "(the supervisor restarts me; nothing is in flight, nothing is lost)")
    try:
        ctx.hb.active.clear()
        rail.release(ctx.id, WORKER)
    except Exception as e:                                            # noqa: BLE001
        log(f"   (could not release the lease cleanly: {e} — it will expire)")
    raise SystemExit(0)


def _stage8_watch():
    """Stage-8 rename watchdog (EP10 lesson, 25 Jul 2026): a PUBLISHED episode
    whose local folder still carries the bare PP-EP<NN> name missed its
    close-out rename. Flag it in plain English — once per pass, never rename
    automatically (Drive sync + open files make that a human-timed step)."""
    try:
        for ep in rail.list_all():
            nn = ep.get("ep_number")
            if ep.get("status") != "published" or not nn or ep.get("needs_look"):
                continue
            bare = PP_VIDEOS / f"PP-EP{int(nn):02d}"
            if bare.is_dir():
                rail.flag_needs_look(
                    ep["id"],
                    f"PP-EP{int(nn):02d} is published but its folder was never "
                    "renamed (Stage-8 close-out). Run, from the repo: python "
                    "engine/rename_episode.py "
                    f"EP{int(nn):02d} \"<approved title>\" --apply, then clear this flag.")
                log(f"stage-8 watchdog: flagged PP-EP{int(nn):02d} (published, folder not renamed)")
    except Exception as e:
        log(f"stage-8 watchdog skipped ({e})")


def cmd_run(mock, watch):
    _acquire_lock()
    provider = MockProvider(MOCK_ROOT) if mock else RealProvider(PP_VIDEOS)
    log(f"engine up — worker={WORKER} pid={os.getpid()} provider={provider.name} watch={watch}")
    check_locked_order()
    idle_poll = 3 if mock else 30
    _s8_last = 0.0
    _gate_last = 0.0
    while True:
        changed = _code_changed()
        if changed:
            log(f"{changed} changed on disk since start — exiting so fresh code loads "
                "(restart the engine)")
            return
        # THE IDLE LOOP MUST OUTLIVE THE NETWORK. This is where the engine was when
        # it died on 28 Jul: EP13 released and parked, nothing claimed, so the only
        # outbound calls in flight were these rail polls. rail retries the transient
        # family itself; RailUnavailable means it has been unreachable for minutes,
        # and the right answer to that is to wait and poll again, not to exit and
        # leave the board saying "working" all night.
        try:
            ep = acquire()
            if not ep:
                if not watch:
                    _why_idle()
                    log("nothing to do (no claimable episode) — exiting")
                    return
                if time.time() - _gate_last > 300:
                    _why_idle()
                    _gate_last = time.time()
                if not mock and time.time() - _s8_last > 600:
                    _stage8_watch()
                    _s8_last = time.time()
                time.sleep(idle_poll)
                continue
        except rail.RailUnavailable as e:
            if not watch:
                raise
            log(f"!! the rail is unreachable ({e}) — staying up and polling; "
                f"nothing is lost, the engine simply cannot see the board yet")
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
                        _code_changed_exit(ctx, "while this episode was flagged")
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
        # The mock pre-passes BOTH halves of the Script Gate so the spine can be
        # exercised. This is the only place either flag is ever set by code, and
        # it only ever runs against a throwaway PP-EP99 ticket.
        "title_approved": True,
        "script_read": True,
        # ...and pretends the human already started Gordon's render, for the same
        # reason and in the same throwaway-ticket-only way. Without this the spine
        # stops at awaiting_render and every step past it — assembly, QC, the
        # thumbnail, the YouTube copy — is never exercised. This is DATA on a mock
        # ticket, not a change to the gate: the real render gate is untouched and
        # still waits for a human.
        "render_started_at": "2026-07-28T00:00:00+00:00",
        "script_doc_url": "https://docs.google.com/document/d/MOCKmockMOCKmockMOCKmock/edit",
        "hook": "A Mock Hook",
        "byline": "a mock byline for the spine test",
        "notes": "Mock ticket for the engine spine test.",
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
