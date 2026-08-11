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
import subprocess
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
import script_fidelity                         # the drafting pass's own gate
from providers import (EngineFlag, MockProvider, RealProvider, ep_folder,
                       assert_standing_assets, pasteable_description,
                       assert_capture_for_script, find_capture, SKILL_DIR)

HUMAN_GATES = {"awaiting_render", "awaiting_cover", "awaiting_approval"}

# --- THE LOCKED ORDER (approved by Jodie, 26 Jul 2026) ----------------------
# Do NOT re-sequence without Jodie's explicit re-approval. The shape that
# matters: human turns 1-2-3 cluster back-to-back at the FRONT, then a long
# hands-off render window, then turn 4 at the END. The HeyGen render is the
# LONG POLE (5-45 min) and depends only on the spoken track — which is final at
# the Words Gate — so it starts EARLY, never last, and never behind the visuals.
LOCKED_ORDER = (
    "1 script + words · 2 SCRIPT GATE + WORDS GATE (read the script, approve "
    "title/hook/byline) · 3 RENDER GATE OPENS IMMEDIATELY — the render needs only the "
    "approved script and the project name, and both are final at the words gate · "
    "4 the episode.json commission, the gens batch (b-roll + cover heroes A/B) and the "
    "cards all run BEHIND the render, inside its window · 5 cover pick WHILE Gordon "
    "renders · 6 engine finishes hands-off · 7 master -> shot map -> assembly -> QC · "
    "8 the four approvals · 9 publish + Stage-8 close-out"
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


def log(msg, **_):
    # **_ so this can stand in anywhere a print-like logger is expected — the
    # commission relay calls its logger with flush=True, and the alternative was
    # letting those lines fall through to a bare print(), which would put half the
    # run log's lines under a timestamp and half of them not.
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
    # 🔴 RENDER FIRST. (Jodie, 9 Aug 2026 — a LOCKED-ORDER change, approved in terms.)
    # The render is the long pole, 5-45 minutes, and it needs exactly two things, both
    # final the instant she clicks Approve: the project name, and the approved script.
    # IT DOES NOT READ episode.json — the only step in the whole building phase that
    # does not, and the only one a human is waiting on.
    #     It sat behind `audit_inputs`, which was a four-second scan until it became a
    # COMMISSION on 7 Aug. The render silently inherited the wait: EP18, a clean run
    # that passed every check first time, still made Gordon wait 17m14s, of which the
    # commission was 98.7%. EP19 waited 31m53s. Nobody re-sequenced anything — the cost
    # arrived inside a step that had always been cheap.
    #     Nothing an episode.json fault can do changes a word Gordon says, so no card
    # fault can waste a render.
    "building":   ["script_sync", "render_gate", "audit_inputs", "credit_check",
                   "broll_submit", "covers_ab", "broll_collect",
                   "cover_pick", "ebook_cover", "cards_render"],
    "rendering":  ["heygen_download", "shot_map"],
    # 🔴 self_qc RUNS AFTER THE THINGS IT CHECKS. It used to sit third, straight after
    # the two assembly passes and BEFORE ebook_pdf and thumbnail — while its own
    # deliverables stage hard-fails on "no e-book PDF" and "no thumbnail PNG". On a
    # clean run it could not pass: it failed three times on EP19, on two artefacts the
    # next two steps were about to create.
    #     IT HID FOR TWO EPISODES because a re-run finds the PDF and the thumbnail left
    # by the previous attempt, so QC passes on artefacts from the run before. Only EP19,
    # assembled from nothing, ever asked the question honestly.
    # Jodie's requirement is that the machine QCs the assembled video BEFORE EVERY HUMAN
    # APPROVAL GATE — the gate is at the END of this phase, so QC still comes before it,
    # and now it can see the whole delivery rather than two thirds of it.
    # `web_copies` sits after `thumbnail` because it needs BOTH full-size pictures
    # — the one that step writes, and the e-book cover from `ebook_cover`. It is
    # additive and never fails the build (Jodie, 11 Aug 2026).
    "assembling": ["assemble_passA", "assemble_passB", "ebook_pdf", "thumbnail",
                   "web_copies", "self_qc", "youtube_copy"],
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
    "web_copies":     "Making the low-res web copies",
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
    # ── THE EIGHTH ASSERTION, AND ITS ABSENCE IS THE WHOLE STORY ─────────────────
    # 🔴 THE GUARD PERMITTED THE REGRESSION IT EXISTS TO CATCH. Nothing here ever said
    # the render must come before the COMMISSION, so when `audit_inputs` grew from a
    # four-second scan into a 17-32 minute commission on 7 Aug, this function stayed
    # green while the render slid behind it. Two episodes shipped that way and nobody
    # noticed, because every one of the seven assertions still held.
    #     A locked order guarded by seven rules is guarded against seven things.
    if not before("render_gate", "audit_inputs"):
        problems.append(
            "the render gate must open BEFORE audit_inputs — audit_inputs COMMISSIONS "
            "episode.json (17-32 minutes, measured on EP18 and EP19) and the render "
            "needs none of it. The render is the long pole and depends only on the "
            "approved script, so it is offered the moment the words are locked. "
            "Approved by Jodie 9 Aug 2026; the guard exists because the previous order "
            "regressed silently when this step grew from a scan into a commission.")
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

    # ── THE ASSEMBLING PHASE WAS NOT CHECKED HERE AT ALL, and that is how self_qc
    # came to run before the deliverables it hard-fails on. A step list this function
    # does not read is a step list nothing is guarding.
    a = PHASES["assembling"]

    def a_before(x, y):
        return x in a and y in a and a.index(x) < a.index(y)

    for made in ("ebook_pdf", "thumbnail"):
        if not a_before(made, "self_qc"):
            problems.append(
                f"self_qc must run AFTER {made} — its deliverables stage hard-fails on "
                f"a missing e-book PDF and a missing thumbnail, so running it first "
                f"fails on artefacts the very next step creates. (It did, three times, "
                f"on EP19. It hid on earlier episodes because a RE-RUN finds the files "
                f"left by the previous attempt.)")
    if "self_qc" in a and a.index("self_qc") != len(a) - 1 and \
            not a_before("self_qc", "youtube_copy"):
        problems.append("self_qc must still come before the phase ends — the machine "
                        "QCs the assembled episode before every human approval gate")
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

    # 🔴 ONCE A HUMAN HAS EDITED, THE HUMAN'S VERSION IS THE TRUTH.
    #
    # The script is the only artefact with TWO AUTHORS, and without a rule a
    # re-read silently overwrites her edits — the exact class of fault as board
    # bug 1, just slower and with no undo at all. `script_edited_by_human_at` is
    # set on her FIRST save in the board editor; from that moment the engine may
    # READ freely and must never WRITE over her.
    #     Reading is always safe. Writing over a person is not.
    #
    # ⚠️ IT COMPARES THE WORDS, NOT JUST THE FLAG. On the rail path this step
    # re-reads what she wrote and writes the same string back, which is a no-op
    # and must not halt a build. What must halt is the case where the incoming
    # text DIFFERS from hers — a Doc still holding the pre-edit version, or any
    # future path that regenerates the script. Flagging on the flag alone would
    # stop every episode she has ever touched, which is the version somebody
    # switches off.
    if ctx.ep.get("script_edited_by_human_at") and text != (ctx.ep.get("script_snapshot") or ""):
        raise EngineFlag(
            "The script for this episode was edited on the board, and the words "
            "the studio was about to build from are different ones. Nothing has "
            "been changed and nothing has been built.\n"
            "Your version is the one being kept. The studio will not write over "
            "words a person has edited — it stops and asks instead.\n"
            "Open the script, check it reads the way you want, and approve it "
            "again. If it is already right, clearing this is all that is needed.")

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
        # The raw lines ride along on the flag so the repair loop can hand them
        # to the writer verbatim. The MESSAGE is unchanged — it is what a person
        # reads; `.blockers` is what a machine reads.
        raise EngineFlag(
            "This episode's settings differ from the last two episodes in ways that "
            "will stop the build later on:\n"
            + "\n".join(f"      • {m}" for m in res["must"])
            + "\n    Every one of these has cost a build before. They are cheaper to "
              "fix now than eighteen steps in, which is why I look before I start.",
            blockers=res["must"])
    out = [f"config pre-flight: clean against {' + '.join(names)}"]
    out += [f"   note — {w}" for w in res["worth"]]
    return out


def _preflight_cards(ctx) -> list[str]:
    """Run the card pipeline's DATA and TEXT checks before a credit moves.

    Raises EngineFlag on a blocker. Warnings are logged and never block — they
    are estimates, and a build must not stop on arithmetic it cannot yet do.

    ⚠️ Like E26, this must NEVER be the reason a build cannot start. If the
    episode's files are not there to read, it says so and stands aside.
    """
    if ctx.mock or not ctx.ep.get("ep_number"):
        return ["card pre-flight: skipped (mock)"]
    import preflight_cards as pc

    d = ctx.provider.dir(ctx.ep)
    epj_path = d / "docs/episode.json"
    if not epj_path.is_file():
        return ["card pre-flight: no episode.json yet — nothing to check"]
    try:
        epj = json.loads(epj_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise EngineFlag(
            "The episode's own settings file could not be read, so nothing about "
            "this episode's cards could be checked. Nothing has been built and "
            "nothing spent.\n"
            f"It reported: {e}")

    def _read(p):
        try:
            return p.read_text(encoding="utf-8") if p and p.is_file() else None
        except Exception:
            return None

    # The approved script is on the rail; the file is its derived cache.
    script = ctx.ep.get("script_snapshot") or _read(d / "docs/spoken-words.txt") or ""
    capture = None
    rel = pc.capture_rel(epj)
    if rel:
        capture = _read(ctx.provider.pp / rel) or _read(d / rel)
    # check_trace compares figures against the ARTICLE TEXT ONLY — never the
    # capture's header notes about the scan repairs, which is the same trap the
    # marker check exists to stop.
    article = None
    if capture:
        try:
            import author_cards as ac
            article = ac.norm(capture.split(pc.MARKER_BEGIN)[-1])
        except Exception:
            article = None

    # capture_looked_for=True: this caller DID go to disk for it, so "named but not
    # there" is a real finding here and not merely an argument nobody supplied.
    res = pc.preflight_cards(epj, script_text=script, capture_text=capture,
                             article_norm=article, capture_looked_for=bool(rel))
    lines = pc.format_report(res).splitlines()
    if res["blockers"]:
        raise EngineFlag(
            "This episode's cards cannot be built as they are written. Nothing has "
            "been built and nothing has been spent — these were all found before "
            "anything started.\n"
            "Each line below names the card and what is wrong with it:\n"
            + "\n".join(f"  - {b}" for b in res["blockers"]),
            blockers=res["blockers"])
    return lines


# ONE write, then TWO repairs. Three goes in all, and the number is a judgement
# with its cost named rather than a round one: each attempt is bounded at 1800s,
# so a writer that thrashes costs about ninety minutes before the engine gives up.
# Jodie took that trade on 7 Aug 2026 — "a repair fixing a named fault is fast, so
# the realistic cost of the third is small; the ninety minutes is only a thrashing
# writer, which is genuinely stuck and should flag anyway."
EPJSON_ATTEMPTS = 3


def _epjson_gate(ctx) -> list[str]:
    """Run the build's OWN two gates and return their blocker lines. [] = pass.

    🔴 THE SAME FUNCTIONS THE BUILD HALTS ON, called here, not copied. A second
    implementation of the gate is a second thing to keep in step, and the whole
    point of commissioning at THIS spot is that a machine-written file is judged
    by exactly the mutation-proved checks a hand-written one is.

    ⚠️ BOTH GATES RUN, EVEN WHEN THE FIRST ONE FAILS. E26 raises before the card
    checks would ever run, so letting it short-circuit would spend one of three
    attempts fixing settings and the next one fixing cards. The writer gets every
    complaint at once.

    ⚠️ AND WHAT THIS FUNCTION CANNOT TELL YOU: both gates STAND ASIDE quietly when
    their inputs are not there — fewer than two reference episodes, no episode.json.
    An empty list means "nothing was found", which is not the same as "the file is
    good", and on a fresh target it can mean "nothing looked". The lines each gate
    returns say which of the two happened, which is why they are logged and not
    swallowed. (CLAUDE.md: a pass is a statement about what was MEASURED.)
    """
    blockers: list[str] = []
    for fn in (_preflight_config, _preflight_cards):
        try:
            for line in fn(ctx):
                log(f"   {line}")
        except EngineFlag as f:
            # `.blockers` is the checker's own lines. The fallback is the flag's
            # prose, so a raise site that has not been given blockers still says
            # something useful rather than silently contributing nothing.
            blockers += list(getattr(f, "blockers", None) or [str(f)])
    return blockers


def _commission_epjson_with_repair(ctx, d):
    """Commission episode.json, and give the writer the gate's own faults back.

    Returns the verdict of the attempt that passed. Raises CommissionHalt when
    the attempts are used up (operator-shaped) — the caller turns that into a flag.

    ⚠️ THE GATES RUN INSIDE THIS LOOP, so the caller must NOT run them again
    afterwards. It only returns when they are clean.
    """
    import commission as com

    # THE BOARD GETS THE ENGINE'S OWN SENTENCE, not the step name. This is the step
    # that ran 1029s on EP18 and 1907s on EP19 while the card said "Stuck — Checking
    # the inputs", and under the render-first order it is the first thing Jodie sees
    # after approving. Only the LABEL is re-stamped per attempt; the clock is not.
    return com.commission_with_repair(
        attempt=lambda followup: ctx.provider._commission_episode_json(
            ctx.ep, d, followup=followup,
            on_start=lambda text: set_step_label(ctx, text)),
        gate=lambda: _epjson_gate(ctx),
        what="this episode's settings and cards",
        attempts=EPJSON_ATTEMPTS,
        log=log)


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
    # ═══ COMMISSION THE SETTINGS RATHER THAN DEMAND THEM ═════════════════════
    # This is the halt Jodie met three minutes after approving EP17's words:
    # "Create-inputs are missing… Claude Code writes these at the create step."
    # A flag that names its own author and then asks a human to fetch him.
    #
    # 🔴 THE FOURTH GATE NEEDS NO NEW CODE, AND THAT IS THE POINT OF PUTTING IT
    # HERE. Immediately below, _preflight_config (E26) and _preflight_cards run
    # against whatever is on disk and HALT on anything they do not like. Placing
    # the commission just above them means the file a writer produced is judged
    # by exactly the same mutation-proved checks a hand-written one is — not by a
    # copy of them, and not by the writer's own report that it checked.
    #
    # ⚠️ `dir()` IS REAL-PROVIDER-ONLY — MockProvider has no such method, so the
    # lookup stays INSIDE the real-path guard. Computing it above the `if` cost a
    # red suite the moment it was written: test_step_call_sites drove the real
    # dispatch and got AttributeError, which is the same shape as the NameError
    # that killed EP15 and exactly what that suite exists to catch.
    commissioned = False
    if not ctx.mock and ctx.ep.get("ep_number"):
        d = ctx.provider.dir(ctx.ep)
        # 🔴 THE PRESENCE GUARD IS EVALUATED ONCE, HERE, ABOVE THE LOOP — and it
        # has to be. It asks whether episode.json is ABSENT, and the moment the
        # first attempt writes one it is not. Inside the loop, no repair would
        # ever fire; the second attempt would look at the file the first attempt
        # wrote and decide there was nothing to do.
        if (not (d / "docs/episode.json").is_file()
                and (d / "docs/spoken-words.txt").is_file()):
            import commission as com
            try:
                _commission_epjson_with_repair(ctx, d)
            except com.CommissionHalt as h:
                if h.detail:
                    log(f"   (commission detail, for the log: {com._safe(h.detail)})")
                raise EngineFlag(h.message)
            commissioned = True

    # JOB A — THE CARD PIPELINE'S CHECKS, MOVED HERE FROM cards_render/shot_map.
    # EP16's card faults were twenty schema/job, twenty-six trace, two bad cues
    # and three short beats — every one of them pure data or pure text, every one
    # knowable right here, and every one of them actually fired AFTER the render
    # gate, the credit check, seven paid clips, two paid heroes and a cover pick.
    #     THE CHECKS EXISTED. THEY RAN TOO LATE.
    #
    # ⚠️ EXACTLY ONCE PER PATH. The repair loop above runs these same two gates
    # itself and only returns when they are clean, so running them here as well
    # would be a second, pointless pass — and on the hand-written path they must
    # still raise their own flags, unchanged, exactly as they did before.
    if not commissioned:
        for line in _preflight_config(ctx):
            log(f"   {line}")
        for line in _preflight_cards(ctx):
            log(f"   {line}")
    meta = ctx.provider.audit_inputs(ctx.ep)
    ctx.ep_set({"drive_folder": ep_folder(ctx.ep)})
    return meta


def step_render_gate(ctx):
    """HUMAN TURN 2 opens HERE — the moment the words are locked, and nothing later.

    IT NEEDS EXACTLY TWO THINGS, AND BOTH ARE FINAL AT THE WORDS GATE: the project
    name (ep_number + the approved title) and the approved script, re-read from its
    home by script_sync immediately before. It deliberately does NOT wait for
    episode.json, the b-roll, the covers or the cards — it is the only step in the
    building phase that never reads episode.json, and the only one a human is
    waiting on.
        ⚠️ THE SENTENCE THIS REPLACES SAID "…and the spoken track has passed the
    render-ready scan". That scan is `audit_inputs`, which now runs BEHIND this step
    (Jodie, 9 Aug 2026), and a docstring describing a dependency that no longer
    exists is how the next person re-creates it.

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


def _open_a_new_cover_round(ctx, row):
    """Record the rejection, archive the pair, open the next round — AND MAKE THE PAIR.

    ⚠️ THIS SPENDS. Two 2k stills per round. It used to spend nothing, and the docstring
    here argued that was right: the new pictures would arrive "when the STUDIO writes
    fresh prompts into episode.json — a human decision." That reasoning was half sound
    and wholly broken in practice. Nobody was ever going to hand-edit episode.json while
    she waited, so the button recorded a wish and answered it never. EP20 hung at a board
    showing the pictures she had just rejected.

    The real objection was never to REGENERATING — it was to JITTERING: nudging the old
    prompt until the sha moved, which is a probabilistic dodge of a hash collision that
    fails quietly by re-offering rejected pictures as fresh ones. That is the EP15 shape.
    So the decision is still made by a writer, not by a random seed: `regenerate_covers`
    commissions a genuine re-brief FROM HER NOTE, and REFUSES prompts that came back
    unchanged. Automation eats the chore; her words still make the decision.
    """
    rnd = int(row.get("cover_round") or 1)
    history = list(row.get("cover_rounds") or [])
    note = (row.get("cover_more_note") or "").strip()
    # EVERY PAIR IS KEPT. Round 1's URLs stay here so the board can still offer them and
    # so the next prompts can be written knowing what was turned down and why. Her
    # reasons COMPOUND: round 3 is written having read the notes from 1 and 2.
    history.append({
        "round": rnd,
        "a_url": row.get("cover_a_url"),
        "b_url": row.get("cover_b_url"),
        "requested_at": row.get("cover_more_requested_at"),
        "note": note or None,
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        ctx.provider.record_cover_rejection(row)     # E16 part 2, on the ledger
    except Exception as e:                                            # noqa: BLE001
        log(f"   (could not mark the hero ledger rejected: {e})")
    ctx.ep_set({
        "cover_round": rnd + 1,
        "cover_rounds": history,
        "cover_more_requested_at": None,   # consumed; the button is live again
        "cover_more_note": None,
    })

    # ── AND NOW ACTUALLY MAKE THE NEW PAIR ────────────────────────────────────
    #
    # 🔴 THIS IS WHAT WAS MISSING, AND IT HUNG EP20. Opening the round advanced the
    # counter, archived the old pair and cleared the request — and then nothing
    # generated anything. `covers_ab` had already run in the gens batch and never runs
    # again, so the board went on showing the SAME REJECTED COVERS and waited for a pick
    # that was never coming. Jodie sat on it for ten minutes with no sign anything was
    # wrong. A button that records a wish is not a button that answers it.
    #
    # ⚠️ IT SAYS IT IS WORKING BEFORE IT STARTS. This takes minutes — a writer re-briefs
    # the prompts, then two 2k stills are generated — and a silent gap here is the same
    # fault in a smaller window.
    rail.progress(ctx.id, "Making fresh covers from your notes — a minute or two", 33)
    set_step_label(ctx, "Making fresh covers from your notes. You can still pick one of "
                        "the earlier pairs while this runs.")
    try:
        # 📌 THE ROUND IS PASSED EXPLICITLY, not read back off the rail. The publish path
        # is versioned BY THE ROUND (`cover-A-r2.png`), and `ep_set` falls back to the
        # STALE row if the update returns nothing — which would silently write round 2
        # to round 1's bare path and overwrite the image the archived a_url points at.
        a_url, b_url = ctx.provider.regenerate_covers(
            {**ctx.ep, "cover_round": rnd + 1}, note, history)
    except Exception as e:                                            # noqa: BLE001
        # NEVER HANG. The old pair is still on the board and still pickable, so this is
        # not an emergency — but she asked for something and must be told it did not
        # happen, rather than waiting on covers that are not coming.
        log(f"   cover round {rnd + 1}: could not generate a fresh pair — {e}")
        rail.flag_needs_look(
            ctx.id,
            f"I could not make the fresh covers you asked for.\n\n"
            f"WHY:\n{str(e)[:700]}\n\n"
            f"The covers already on the board are still there and still yours to pick — "
            f"nothing has been lost. This one is the studio's to sort out. Clearing this "
            f"flag lets the build carry on with the covers you have.")
        rail.progress(ctx.id, "Waiting on you — pick a cover (A or B)", 33)
        return
    ctx.ep_set({"cover_a_url": a_url, "cover_b_url": b_url})
    rail.progress(ctx.id, "Waiting on you — pick a cover (A or B)", 33)
    set_step_label(ctx, "")
    log(f"   cover round {rnd + 1} is on the board — a fresh pair, written from her "
        f"note rather than jittered")
    # A GENTLE, NON-BLOCKING NUDGE — never a halt. After a few rounds it is worth
    # saying out loud that the brief may be the problem rather than the pictures, but
    # nothing about that is Jodie's fault and nothing should stop because of it.
    nudge = ("  (that is round %d — if the direction still is not right, the BRIEF may "
             "be worth a look rather than more pictures)" % rnd) if rnd >= 3 else ""
    log(f"   cover round {rnd} turned down{' — ' + note if note else ''}. "
        f"Round {rnd + 1} is open; fresh prompts are the studio's to write, and "
        f"nothing has been spent.{nudge}")


def step_cover_pick(ctx):
    """HUMAN TURN 3. Both heroes have existed since the gens batch, so the board
    has been showing this pick for the whole b-roll collect — normally the answer
    is already in and this step just reads it. If it isn't, we wait here (status
    stays 'building', heartbeat live) rather than ping-ponging the status."""
    waited = 0
    asked_seen = None
    while True:
        ctx.check_alive()
        row = ctx.refresh()
        # ── "NEITHER — ASK FOR DIFFERENT ONES" (Option B, batch item 13) ──────────
        # A FREE SIGNAL, AND IT HALTS NOTHING. The click costs £0; the spend is a
        # separate, deliberate act by the studio when it writes fresh prompts. So this
        # records the rejection, opens the next round, and CARRIES ON WAITING — the old
        # tiles stay tappable, because a request is not a veto and she may still change
        # her mind. Nothing flags, nothing goes red, Gordon keeps rendering.
        asked = row.get("cover_more_requested_at")
        if asked and asked != asked_seen:
            asked_seen = asked
            _open_a_new_cover_round(ctx, row)
        choice = (row.get("cover_choice") or "").strip().upper()
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
import commission as _com        # for the derived commission budgets below

# 🔴 A STEP THAT COMMISSIONS IS ALLOWED WHAT THE COMMISSION IS ALLOWED — DERIVED,
# NEVER TYPED. `audit_inputs` had no entry here at all, so it fell to the 900s default
# while the commission it runs is bounded at EPJSON_ATTEMPTS x 1800s = 5400s. ITS ALARM
# WAS SET TO ONE SIXTH OF ITS OWN BOUND, and the board read that number straight off the
# row:
#     EP18  audit_inputs ran 1029s  -> "Stuck — Checking the inputs" for 2m 09s
#     EP19  audit_inputs ran 1907s  -> "Stuck — Checking the inputs" for 16m 47s
# Two out of two, and BOTH EPISODES WERE FINE. Once the render moves in front of this
# step (see PHASES), that lie is the first thing Jodie sees after approving — so moving
# the render without this would trade a delay for a lie.
#
# ⚠️ IT IS THE SAME TRADE JODIE ALREADY TOOK, in EPJSON_ATTEMPTS' own words: "a writer
# that thrashes costs about ninety minutes before the engine gives up… which is
# genuinely stuck and should flag anyway." The alarm now agrees with the bound.
# +300s of headroom covers the gates and the file writes either side of the commission.
def _commission_budget(attempts: int, timeout_s: int) -> int:
    return attempts * timeout_s + 300


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
    # the three steps that COMMISSION. Each reads the bound its own commission runs
    # under, from commission.py — the one place those timeouts are defined.
    "audit_inputs":    _commission_budget(EPJSON_ATTEMPTS, _com.TIMEOUT_EPJSON_S),
    "ebook_pdf":       _commission_budget(1, _com.TIMEOUT_S),
    "youtube_copy":    _commission_budget(1, _com.TIMEOUT_S),
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


def set_step_label(ctx, text: str):
    """Put the engine's OWN sentence on the in-flight marker, for the board to show.

    🔴 IT RE-STAMPS THE LABEL AND NEVER `started_at`. Resetting the clock on each
    commission attempt would make a genuinely wedged writer invisible for ever — which
    is the exact fault the watchdog was built for (EP14: three and a half days on
    assemble_passB behind a healthy six-second heartbeat). The outer clock keeps running
    against the derived budget, always.
    """
    cur = ctx.state.get("current")
    if not cur:
        return                      # not in a step: nothing to label
    cur["label"] = text
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


# ═══ EVERY ARTEFACT GETS A WEB ADDRESS ══════════════════════════════════════
# These three columns held `G:\My Drive\...` paths — a drive letter on ONE laptop,
# written into a link the board renders for a person who may not be sitting at it.
# Hugh has nothing but the browser, so "here is your e-book" pointed at a place he
# cannot reach.
#
# The VIDEO is deliberately NOT here. It is ~159 MB and Hugh gets it from Drive;
# its link is handled separately.
# ═════════════════════════════════════════════════════════════════════════════
def step_ebook_pdf(ctx):
    out = ctx.provider.build_ebook(ctx.ep)
    ctx.ep_set({"ebook_url": ctx.provider.publish_artefact(ctx.ep, out)})
    return {"ebook": out}


def step_thumbnail(ctx):
    out = ctx.provider.build_thumbnail(ctx.ep)
    ctx.ep_set({"thumbnail_url": ctx.provider.publish_artefact(ctx.ep, out)})
    return {"thumbnail": out}


def step_web_copies(ctx):
    """The two low-res pictures Hugh puts on the website (Jodie, 11 Aug 2026).

    Placed AFTER `thumbnail` because it needs both full-size pictures — the thumbnail
    that step writes, and the e-book cover from `ebook_cover` much earlier. It is
    additive: two new names in output/, nothing existing touched.
    """
    return {"report": ctx.provider.build_web_copies(ctx.ep, ctx.provider.dir(ctx.ep))}


def step_youtube_copy(ctx):
    """The copy needs no web address — it needs to BE on the card.

    It used to write "see G:\\...\\PP-EP16-youtube.txt", which is an instruction
    to go and open a file on a machine the reader may not have. The column is
    rendered straight onto the publish card, so the words themselves belong in
    it. The file stays on disk as the record, with its notes block.
    """
    out = ctx.provider.save_youtube_copy(ctx.ep)
    try:
        copy = pasteable_description(Path(out).read_text(encoding="utf-8"))
    except OSError:
        copy = f"see {out}"          # never lose the pointer if the file moved
    ctx.ep_set({"youtube_copy": copy})
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
    ("web_copies", step_web_copies), ("youtube_copy", step_youtube_copy),
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
REPO_DIR = ENGINE_DIR.parent.resolve()


def _watched_files() -> set[Path]:
    """Every .py the engine has actually imported FROM THIS REPO, plus itself.

    🔴 IT USED TO BE `p.parent == ENGINE_DIR`, AND THAT MISSED HALF THE CODEBASE.
    (EP20, 10 Aug 2026.) The engine imports the skill's scripts too — capture_article,
    author_ebook, qc_episode, derive_card_timings — and none of them lived in
    ENGINE_DIR, so a change to any of them never triggered the stale-code exit. The
    running engine kept them in memory indefinitely.

    THE BOUNDARY IS THE REPO, NOT A LIST OF FOLDERS. The first fix named engine/ and
    .claude/skills/ explicitly, which is a list somebody must remember to extend the
    day a module moves or a new directory appears — the same shape as every stale list
    this studio has been bitten by. Anything imported FROM THIS REPO is code the engine
    runs, and that is the whole rule.
        📌 SCRIPTS RUN AS SUBPROCESSES NEED NO WATCHING and are deliberately not here:
    render_cards_batch, card_check, author_cards and the rest are a fresh interpreter
    every time, so they cannot go stale. Staleness is only possible for a module held
    in THIS process's memory, which is exactly what sys.modules lists.
        It bit immediately: capture_article was fixed and pushed, and EP20 went on
    being refused every 25 seconds with the OLD message — "no byline of the form
    'By <Name>' was found" — from a module that no longer said that. The board looked
    like a broken fix; the engine was simply running yesterday's code, which is E11's
    exact concern ("this engine is running code older than the repo") for every file
    outside one directory.

    THE SCOPE FILTER STAYS, and the original reasoning for it is untouched: watching
    every loaded module would watch the whole stdlib and every site-package —
    thousands of stats per poll, and a pip install would restart the engine. The scope
    is simply the REPO rather than one folder inside it, which is what "the engine's
    own code" always meant.
    """
    files = {Path(__file__).resolve()}
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            p = Path(f).resolve()
        except (OSError, ValueError):
            continue
        if p.suffix != ".py":
            continue
        if p.is_relative_to(REPO_DIR):
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

    ⚠️ LETTING GO MATTERS, AND SO DOES HOW. Exiting while still holding the lease
    leaves the episode claimed by a worker that no longer exists, and `reclaim_stale()`
    cannot take it back until the lease expires. But `rail.release()` is worse: it nulls
    the owner, and a working status with `claimed_by: NULL` is the dead zone, which
    nothing picks up, ever.
        🔴 THAT WARNING WAS ALREADY WRITTEN HERE, IN THESE WORDS, AND THE CODE BELOW
    CALLED release() ANYWAY. EP19, 9 Aug 2026: the guard fired while the episode was
    flagged, the episode went ownerless at 33%, and it sat there with its flag already
    cleared until a human asked why nothing was moving. A comment describing a trap is
    not a guard against it. It now calls `rail.hand_back()`, which leaves a named owner
    and an expired lease so `reclaim_stale()` takes it on the next tick.

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
        rail.hand_back(ctx.id, WORKER, "exited for new code")
    except Exception as e:                                            # noqa: BLE001
        log(f"   (could not hand the lease back cleanly: {e} — it will expire)")
    raise SystemExit(0)


# 🔴 THE BOUND — A PASS THAT RUNS UNATTENDED MUST NOT BE ABLE TO SPEND FOREVER.
#
# EARNED ON THE FIRST LIVE RUN, 7 Aug 2026. A commission produced a complete,
# gate-passing script and returned is_error — so nothing was seated, and the very
# next pass commissioned another one. In production this loop fires every fifteen
# minutes, all night, with nobody watching: a deterministic fault would spend
# Jodie's rate limits indefinitely and the board would show nothing at all.
#
# THREE, THE SAME NUMBER AND THE SAME SHAPE AS THE episode.json REPAIR LOOP.
# Then it stops, says so in the run log, and LEAVES THE EPISODE ALONE.
#
# ⚠️ THE LEDGER IS A FILE, NOT THE RAIL, AND THAT IS I1. Recording attempts on the
# episode row would be a rail write beyond seat_script_if_empty — the one write
# this pass is allowed. It lives beside the artefact instead, so it survives a
# restart (an in-memory counter would reset and re-spend, which is the fault it
# exists to stop) and a human can clear it by deleting one file.
DRAFT_ATTEMPT_LIMIT = 3
_DRAFT_LEDGER = "docs/.draft-attempts.json"


def _draft_ledger_path(d) -> Path:
    return Path(d) / _DRAFT_LEDGER


def _approved_packaging_text(ep) -> str:
    """The episode's OWN approved words — the second source a spoken figure may have.

    Only fields a human signed off at the words gate: the hook and the byline are the
    approved packaging, and the episode number is the part this is. Nothing derived,
    nothing from the build, and deliberately NOT the script itself — licensing a figure
    against the text being checked would license everything.
    """
    bits = [str(ep.get("hook") or ""), str(ep.get("byline") or "")]
    n = ep.get("ep_number")
    if n is not None:
        # The part number as it is actually said. EP19 is "Part 1" of its article, and
        # the hook usually carries that already — this is the belt to its braces.
        bits.append(f"episode {n}")
    return " \n ".join(b for b in bits if b.strip())


STUCK_AFTER = 3          # consecutive failures of one task before the board is told


def _failure_ledger(d):
    return _draft_ledger_path(d).with_name(".task-failures.json")


def _note_failure(d, task: str, reason: str) -> int:
    """Count a CONSECUTIVE failure of `task`, and return the new count.

    🔴 THE SILENT FOREVER-RETRY, AND WHY THIS EXISTS. (Jodie, 11 Aug 2026, from EP20.)
    A studio-side stop went to the run log and nowhere else — A19: "a page we cannot
    read is the studio's problem, and badging her queue with it would ask for something
    nobody holding a browser can do." Correct for ONE failure. EP20 hit it every
    twenty-five seconds for hours: the capture refused, the kick-on-submit fired again,
    the capture refused again, and the board showed a serene "Writing the script…" the
    whole time.

    ⚠️ A19 IS NOT BEING OVERTURNED, IT IS BEING BOUNDED. Its point is that Jodie should
    not be handed work she cannot do. But an episode that will never progress is worse
    INVISIBLE than badged: she loses nothing by not being told once, and she loses the
    episode by never being told. So the first couple of failures stay in the run log,
    and a task that keeps failing says so — plainly, with the real reason, and saying
    whose job the fix is.

    On disk beside the draft ledger, so it survives a restart: a counter that resets
    when the process does is a counter that never reaches its bound.
    """
    p = _failure_ledger(d)
    try:
        book = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                                 # noqa: BLE001
        book = {}
    entry = book.get(task) or {}
    n = int(entry.get("consecutive", 0)) + 1
    book[task] = {"consecutive": n,
                  "last_reason": str(reason)[:600],
                  "last_at": datetime.now(timezone.utc).isoformat()}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8", newline="\n")
    except OSError:
        pass                      # a counter we cannot write is not worth a crash
    return n


def _clear_failures(d, task: str) -> None:
    """It worked. CONSECUTIVE means consecutive — a success resets the count."""
    p = _failure_ledger(d)
    try:
        book = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                                 # noqa: BLE001
        return
    if book.pop(task, None) is not None:
        try:
            p.write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8",
                         newline="\n")
        except OSError:
            pass


def _flag_stuck(ep, d, task: str, what: str, reason: str, whose: str) -> bool:
    """After STUCK_AFTER consecutive failures, tell the board. Returns True if flagged.

    The message is the shape Jodie asked for — "I couldn't do X, here's why" — and it
    says whose job the fix is, because most of these are the studio's and she should
    not be left wondering what she is meant to click.
    """
    n = _note_failure(d, task, reason)
    if n < STUCK_AFTER:
        return False
    try:
        rail.flag_needs_look(
            ep["id"],
            f"I could not {what}, and I have now tried {n} times. I have stopped "
            f"retrying so this does not sit here looking busy.\n\n"
            f"WHY IT FAILED (the last attempt, verbatim):\n{str(reason)[:700]}\n\n"
            f"{whose}\n"
            f"Nothing has been written and nothing has been spent. Clearing this flag "
            f"makes the studio try again.")
    except Exception as e:                                            # noqa: BLE001
        log(f"   (could not raise the stuck flag: {e})")
        return False
    log(f"   PP-EP{int(ep.get('ep_number') or 0):02d}: {task} has failed {n} times in a "
        f"row — flagged on the board and no longer retrying")
    return True


def _draft_attempts(d) -> int:
    """How many times this episode's script has already been commissioned."""
    try:
        return int(json.loads(_draft_ledger_path(d).read_text(encoding="utf-8"))
                   .get("attempts", 0))
    except Exception:                                                 # noqa: BLE001
        return 0                       # unreadable or absent == none yet


def _record_draft_attempt(d, note: str = "") -> int:
    """Count an attempt BEFORE it is made.

    ⚠️ BEFORE, NOT AFTER, AND THAT IS THE WHOLE POINT. Counting on the way out
    means a crash, a kill or a power cut during the commission never increments —
    and the loop that bound exists to stop is exactly the one where the run does
    not come back.
    """
    p = _draft_ledger_path(d)
    n = _draft_attempts(d) + 1
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "attempts": n,
            "last_at": datetime.now(timezone.utc).isoformat(),
            "last_note": note,
        }, indent=2), encoding="utf-8")
    except Exception as e:                                            # noqa: BLE001
        log(f"   (could not record the drafting attempt: {e})")
    return n


def _clear_draft_attempts(d) -> None:
    """A seated script closes the ledger. The next episode starts from zero."""
    try:
        _draft_ledger_path(d).unlink(missing_ok=True)
    except Exception:                                                 # noqa: BLE001
        pass


FAST_DRAFT_SECS = 25       # "hitting Build starts work in seconds, not a quarter hour"


def _a_brand_new_episode_is_waiting(provider) -> int | None:
    """The ep_number of a QUEUED episode that has NEVER been drafted, or None.

    🔴 THE POINT OF "BRAND NEW", AND IT IS A SPEND GUARD, NOT A NICETY. The drafting
    pass runs on a 900s timer because a commission takes minutes and costs tokens. If
    the fast path simply re-ran that pass every 25 seconds, an episode whose draft keeps
    FAILING would be retried 36 times an hour and burn its whole attempt bound before
    anyone looked at the board — turning "start sooner" into "give up sooner".

    So the fast path fires ONLY for an episode with ZERO recorded attempts: the case
    Jodie actually feels, which is hitting Build and watching nothing happen. Every
    retry stays on the slow timer, where it has always been.

    Cheap by construction: the same queued-list read the pass itself does, plus a file
    stat per candidate. No commission, no network beyond the rail.
    """
    try:
        for ep in rail.list_queued():
            nn = ep.get("ep_number")
            if not nn or ep.get("needs_look"):
                continue
            if (ep.get("script_snapshot") or "").strip():
                continue
            if (ep.get("script_doc_url") or "").strip():
                continue
            # ALREADY BEING WORKED, by this engine or another: leave it entirely.
            if ep.get("claimed_by"):
                continue
            if _draft_attempts(provider.dir(ep)) == 0:
                return int(nn)
    except Exception:                                                  # noqa: BLE001
        return None            # the slow pass will pick it up; never break the loop
    return None


def _draft_watch(provider):
    """THE PRE-CLAIM DRAFTING PASS — the engine writes the script it is waiting for.

    docs/DESIGN-the-pre-claim-drafting-pass.md, Shape A'. For a QUEUED episode with
    an empty script box and its article already captured: commission the script,
    seat it, stop. A human still reads it and still approves it.

    🔴 I1 — IT NEVER CLAIMS, NEVER SETS A STATUS, NEVER TOUCHES claim_next.
    The Script Gate's filter is not relaxed, not duplicated and not read. The
    invariant that survives because of this: NO STEP IN `PHASES` RUNS BEFORE THE
    GATE — `PHASES` is reachable only through claim_next, and this is not a step.

    WHY IT LIVES HERE. `_stage8_watch()` below already iterates the board and
    writes to episodes it has never claimed, from this exact branch, in this exact
    process. Pre-claim work is an existing pattern here, not a new one. And
    `_why_idle()` already prints "waiting on the Script Gate — PP-EP18: ..." every
    five minutes: this turns that sentence into an action.

    🔴 A19 — EVERY STOP THIS PASS PRODUCES IS THE STUDIO'S, NOT THE OPERATOR'S.
    A missing capture, an unreachable writer, a halt: Jodie can act on none of
    them, so none of them flags her queue. They go to the run log and the episode
    is left exactly as it was — still queued, still waiting on the gate, with
    `_why_idle` still saying so in the words it already uses.

    ⚠️ NAMED LIMITATION: a commission takes minutes and this blocks the idle loop
    for that long, so an episode approved mid-draft waits to be claimed. That is
    the cost of not building a second engine, it is measured on EP18, and Shape B
    is the fallback if it bites (design section 7).
    """
    if os.environ.get("ENGINE_COMMISSION", "1") == "0":
        return
    import commission as com
    try:
        for ep in rail.list_queued():
            nn = ep.get("ep_number")
            if not nn or ep.get("needs_look"):
                continue
            # THE BOX MUST BE EMPTY. Checked here to avoid commissioning something
            # that could never be seated — but this is NOT the guard. The guard is
            # rail.seat_script_if_empty()'s conditional write, because a human can
            # type in the minutes between this line and the seat (I2).
            if (ep.get("script_snapshot") or "").strip():
                continue
            # An episode with a Doc keeps its transport (A5: a Doc still wins
            # wherever one exists). EP01-EP16 are not drafted into.
            if (ep.get("script_doc_url") or "").strip():
                continue
            # THE CAPTURE STEP — the last hole in the hands-off chain (9 Aug 2026).
            # EP19 sat queued with a perfectly good source_url on the row and no
            # capture on disk, because `assert_capture_for_script` is a PRECONDITION
            # and nothing CREATED one. A19 already says this stop is the studio's and
            # not Jodie's; the honest conclusion is that the studio should do it.
            #
            # 🔴 IT PLACES A CAPTURE OR IT REFUSES — never a best-effort article of
            # record. The capture is what script_fidelity, check_trace and the e-book
            # body are measured against for the life of the episode, so a subtly wrong
            # one does not fail: it redefines the truth and every downstream check then
            # agrees with it. `capture_article` recognises the page or raises, and its
            # refusal lands in the run log like any other studio-side stop.
            if not find_capture(provider.pp, nn) and (ep.get("source_url") or "").strip():
                try:
                    sys.path.insert(0, str(SKILL_DIR / "scripts"))
                    import capture_article as cap
                    dest, _txt = cap.build(ep["source_url"], nn, provider.pp, write=True)
                    _clear_failures(provider.dir(ep), "capture")
                    log(f"drafting pass: PP-EP{int(nn):02d} — captured the article from "
                        f"its source_url -> {Path(dest).name}")
                except Exception as e:                              # noqa: BLE001
                    # THE RUN LOG FIRST, THE BOARD IF IT KEEPS FAILING. A19 says a page
                    # we cannot read is the studio's problem and Jodie should not be
                    # handed work she cannot do — right for one failure, wrong for a
                    # hundred. EP20 refused every 25 seconds for hours behind a serene
                    # "Writing the script…". See _note_failure for the full reasoning.
                    log(f"drafting pass: PP-EP{int(nn):02d} — could not capture the "
                        f"article, so nothing was written: {e}")
                    if _flag_stuck(
                            ep, provider.dir(ep), "capture",
                            "capture this episode's article from its source_url",
                            e,
                            "THIS ONE IS THE STUDIO'S TO FIX, not yours — the page is "
                            "laid out in a way the capture tool does not recognise. It "
                            "is on the board because an episode that cannot start "
                            "should not look like one that is working."):
                        continue
            try:
                capture = assert_capture_for_script(provider.pp, nn)
            except EngineFlag as f:
                log(f"drafting pass: PP-EP{int(nn):02d} — {f}")     # RUN LOG ONLY
                continue

            d = provider.dir(ep)
            # THE BOUND, CHECKED BEFORE A SINGLE TOKEN IS SPENT.
            done = _draft_attempts(d)
            if done >= DRAFT_ATTEMPT_LIMIT:
                log(f"drafting pass: PP-EP{int(nn):02d} has been attempted "
                    f"{done} times and is being left alone. Nothing more will be "
                    "spent on it. This one is the studio's to look at — the run "
                    f"log above says what went wrong each time, and clearing "
                    f"{_DRAFT_LEDGER} in the episode folder is what starts it again.")
                # 🔴 AND SAY SO ON THE BOARD, ONCE. The bound stops the spending, which
                # is what it is for — but until now it also stopped the TELLING: the
                # episode sat queued for ever, the card said "Writing the script…", and
                # the only record was a run-log line nobody is watching. An episode that
                # has given up must not be indistinguishable from one that is working.
                #     Guarded so it flags ONCE rather than on every pass: needs_look is
                # already set on the second visit, and this branch is reached every
                # 900s until a human acts.
                if not ep.get("needs_look"):
                    last = ""
                    try:
                        last = json.loads(_draft_ledger_path(d).read_text(
                            encoding="utf-8")).get("note", "")
                    except Exception:                                 # noqa: BLE001
                        pass
                    rail.flag_needs_look(
                        ep["id"],
                        f"I could not write this episode's script. I tried "
                        f"{done} times and have stopped, so nothing more is spent.\n\n"
                        f"THE LAST THING I WAS DOING: {last or 'commissioning the script'}\n"
                        f"The run log for this episode says what went wrong on each "
                        f"attempt.\n\n"
                        f"THIS ONE IS THE STUDIO'S TO SORT OUT, not yours. It is on the "
                        f"board because an episode that has given up should not look "
                        f"like one that is still working. Clearing this flag does NOT "
                        f"restart it — the attempt ledger does that.")
                continue

            n = _record_draft_attempt(d, "commissioning the script")
            log(f"drafting pass: PP-EP{int(nn):02d} has no script and its article "
                f"is captured — commissioning one (attempt {n} of "
                f"{DRAFT_ATTEMPT_LIMIT})")
            try:
                # THE GATE THE BUILD HALTS ON, HANDED TO THE WRITER'S RETRY LOOP.
                # Same function, same arguments, same file — read fresh each round,
                # because the writer rewrites it between rounds.
                _cap_text = capture.read_text(encoding="utf-8")

                # THE APPROVED PACKAGING, which is the studio's OWN approved words and
                # the only second source a figure may come from. It is on the RAIL at
                # this point — episode.json does not exist yet — and these are the
                # fields Jodie signs off at the words gate.
                _licensed = _approved_packaging_text(ep)

                def _fidelity_gate():
                    p = d / "docs/spoken-words.txt"
                    if not p.is_file():
                        return []          # nothing written yet is commission()'s fault
                    return script_fidelity.check(p.read_text(encoding="utf-8"),
                                                 _cap_text, _licensed)

                verdict = provider._commission_script(ep, d, gate=_fidelity_gate)
            except com.CommissionHalt as h:
                if h.detail:
                    log(f"   (commission detail, for the log: {com._safe(h.detail)})")
                log(f"   drafting pass stopped for PP-EP{int(nn):02d}: {h.message}")
                continue
            except EngineFlag as f:
                log(f"   drafting pass stopped for PP-EP{int(nn):02d}: {f}")
                continue

            text = Path(verdict["_path"]).read_text(encoding="utf-8").strip()

            # 🔴 THE FIDELITY GATE — THE ENGINE RUNS IT, NEVER THE WRITER.
            # The writer has no shell and was never asked to check itself: "I ran
            # it and it passed" is a report, and the whole relay exists because a
            # report is not an artefact. A script that states a figure the article
            # does not is NOT SEATED — the attempt already counted against the
            # bound above, so a writer that keeps inventing figures runs out of
            # goes rather than filling the box with something nobody can trust.
            try:
                waved = []
                problems = script_fidelity.check(
                    text, capture.read_text(encoding="utf-8"), _licensed, waved)
                # SAY WHAT WAS WAVED. An allowance nobody reads is an exemption, and
                # this gate's whole job is that no figure passes unaccounted for.
                for w in waved:
                    log(f"   fidelity: allowed by the approved packaging — {w}")
            except Exception as e:                                    # noqa: BLE001
                log(f"   drafting pass: could not check PP-EP{int(nn):02d}'s "
                    f"figures against the article ({type(e).__name__}), so the "
                    "draft was NOT used. Nothing unchecked is ever seated.")
                continue
            if problems:
                log(f"   drafting pass: PP-EP{int(nn):02d}'s draft states "
                    f"{len(problems)} figure(s) the article does not, so it was "
                    "NOT used and nothing was written to the script box:")
                for p in problems:
                    log(f"      x {p}")
                continue

            # 🔴 THE ONLY WAY THESE WORDS REACH THE RAIL. Never set_fields, never an
            # unconditional PATCH: the check and the set are one statement, so a
            # human who started typing while the writer was working keeps every
            # character (I2).
            row = rail.seat_script_if_empty(ep["id"], text)
            if row:
                _clear_draft_attempts(d)
                log(f"   seated {len(text.split())} words into PP-EP{int(nn):02d}'s "
                    "script box — it is waiting for a person to read and approve it")
            else:
                log(f"   PP-EP{int(nn):02d}'s script box was filled while the writer "
                    "was working — the draft was NOT used, and nothing was overwritten")
    except Exception as e:                                            # noqa: BLE001
        log(f"drafting pass skipped ({e})")


STAGE8_FLAG_MARK = "(Stage-8 close-out)"


def _approved_title(ep, d):
    """The title the folder should carry — episode.json first, the rail as backup."""
    try:
        pack = json.loads((d / "docs/episode.json").read_text(encoding="utf-8")
                          ).get("packaging") or {}
        for k in ("title", "ebook_title", "youtube_title"):
            if (pack.get(k) or "").strip():
                return pack[k].split("|")[0].strip()
    except Exception:                                                 # noqa: BLE001
        pass
    return (ep.get("hook") or "").strip()


def _stage8_watch():
    """Stage-8 close-out: rename a published episode's folder. AUTOMATICALLY.

    ⚠️ REWRITTEN 10 Aug 2026, AND THE OLD DOCSTRING IS THE POINT. It said: "Flag it in
    plain English — once per pass, never rename automatically (Drive sync + open files
    make that a human-timed step)." That reasoning produced a **needs_look that is not a
    decision** — a machine chore sitting in Jodie's queue — and it printed a raw shell
    command at her:

        Run, from the repo: python engine/rename_episode.py EP19 "<title>" --apply

    An A19 operator-box violation twice over: it badges her queue with the studio's own
    work, and it asks a person holding a browser to run a command they cannot run.
    PP-STANDARDS §WHAT DESERVES A GATE: remove the halt, do not word it better.
    (Jodie, 10 Aug 2026.)

    THE OLD WORRY IS HANDLED RATHER THAN OBEYED. A Drive sync or an open file can make
    a rename fail — so a failure is LOGGED AND RETRIED next pass, never converted into a
    human instruction. The rename tool is idempotent (the current folder name is its
    source of truth), so retrying is free and re-running converges.

    🔒 IT ONLY EVER CLEARS ITS OWN FLAG. A needs_look raised by anything else is a human
    being asked a real question, and this must never wipe one — so the message has to
    carry STAGE8_FLAG_MARK before it is touched.
    """
    try:
        for ep in rail.list_all():
            nn = ep.get("ep_number")
            if ep.get("status") != "published" or not nn:
                continue
            mine = STAGE8_FLAG_MARK in (ep.get("needs_look_message") or "")
            if ep.get("needs_look") and not mine:
                continue          # somebody is being asked a real question — leave it
            bare = PP_VIDEOS / f"PP-EP{int(nn):02d}"
            if not bare.is_dir():
                if mine:          # already renamed; the flag is just stale
                    rail.set_fields(ep["id"], {"needs_look": False,
                                               "needs_look_message": None})
                    log(f"stage-8: PP-EP{int(nn):02d} was already renamed — flag cleared")
                continue
            title = _approved_title(ep, bare)
            if not title:
                log(f"stage-8: PP-EP{int(nn):02d} has no approved title in episode.json "
                    f"or on the rail, so the folder cannot be named. Left as it is.")
                continue
            r = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("rename_episode.py")),
                 f"EP{int(nn):02d}", title, "--apply"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=600)
            if r.returncode != 0 or bare.is_dir():
                # Drive had it locked, or a file was open. Say so and try again next
                # pass — never hand it to a human as a command.
                log(f"stage-8: PP-EP{int(nn):02d} could not be renamed this pass "
                    f"(retrying next time): {(r.stderr or r.stdout).strip()[-200:]}")
                continue
            new = next((p for p in PP_VIDEOS.glob(f"PP-EP{int(nn):02d}-*") if p.is_dir()),
                       None)
            fields = {"needs_look": False, "needs_look_message": None}
            if new is not None:
                fields["drive_folder"] = new.name
            rail.set_fields(ep["id"], fields)
            log(f"stage-8: PP-EP{int(nn):02d} renamed to {new.name if new else '?'} "
                f"and closed out — no flag raised (it is a chore, not a decision)")
    except Exception as e:
        log(f"stage-8 close-out skipped ({e})")


def cmd_run(mock, watch):
    _acquire_lock()
    provider = MockProvider(MOCK_ROOT) if mock else RealProvider(PP_VIDEOS)
    log(f"engine up — worker={WORKER} pid={os.getpid()} provider={provider.name} watch={watch}")
    check_locked_order()
    idle_poll = 3 if mock else 30
    _s8_last = 0.0
    _gate_last = 0.0
    _draft_last = 0.0
    _draft_fast_last = 0.0
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
                # THE DRAFTING PASS — same branch, same process, same guards. It
                # runs ONLY when nothing was claimable, so it can never delay work
                # the engine could otherwise be doing; and on a long interval,
                # because it is the one thing here that can block for minutes.
                # KICK ON SUBMIT. The 900s timer is right for retries and wrong for the
                # thing a person does: pressing Build and watching nothing happen for up
                # to a quarter of an hour. So every FAST_DRAFT_SECS the engine asks one
                # cheap question — is there an episode that has never been drafted at
                # all? — and if so it starts now instead of waiting out the timer.
                # The slow pass stays exactly as it was: it is the safety net, and it is
                # the ONLY thing that retries. See _a_brand_new_episode_is_waiting.
                fast = False
                if not mock and time.time() - _draft_fast_last > FAST_DRAFT_SECS:
                    _draft_fast_last = time.time()
                    nn = _a_brand_new_episode_is_waiting(provider)
                    if nn is not None:
                        log(f"PP-EP{nn:02d} was just queued and has no script — "
                            f"starting on it now rather than waiting for the "
                            f"{900 // 60}-minute pass")
                        fast = True
                if not mock and (fast or time.time() - _draft_last > 900):
                    _draft_watch(provider)
                    _draft_last = time.time()
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
MOCK_RETIRED = "engine-mock-retired"

# ONE definition of the mock ticket, used by BOTH the insert and the reuse path.
# Two copies would be fault #2 with a throwaway row attached: the spine test would
# quietly exercise a different ticket depending on whether one had been retired.
_MOCK_FIELDS = {
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
    "needs_look": False, "needs_look_message": None,
}


def cmd_mock_episode():
    # REUSE A RETIRED MOCK IF THERE IS ONE. Cleanup no longer deletes (see
    # cmd_cleanup_mock and Jodie's 10 Aug ruling), so without this every spine run
    # would leave another PP-EP99 behind and the board would fill with them.
    retired = next((e for e in rail.list_all()
                    if e.get("created_by") == MOCK_RETIRED), None)
    if retired is not None:
        rail.set_fields(retired["id"], _MOCK_FIELDS)
        log(f"mock ticket REUSED (a retired one was on the rail): "
            f"PP-EP99 id={retired['id']}")
        return
    ep = rail.insert(dict(_MOCK_FIELDS))
    log(f"mock ticket created: PP-EP99 id={ep['id']}")


def cmd_cleanup_mock():
    """Retire the mock spine ticket. IT DOES NOT DELETE, AND MUST NOT.

    🔒 JODIE'S RULING, 10 Aug 2026: "production code stays strictly SELECT / INSERT /
    UPDATE, never DELETE — absolute." This used to call `rail.delete()` for every row
    whose `created_by` was "engine-mock" — a delete driven by a FILTER, not by an id
    this process created. One mistyped `created_by` on a real episode and its entire
    record goes: every timestamp, every approval, every cost figure, no undo.
        Found by test_production_never_deletes.py on its first run, which is the
    argument for the guard existing rather than the rule being written down again.

    Retiring instead of deleting also makes the mock spine RE-RUNNABLE without rows
    multiplying: cmd_mock_episode reuses a retired ticket if it finds one.
    """
    n = 0
    for ep in rail.list_all():
        if ep.get("created_by") == "engine-mock":
            rail.set_fields(ep["id"], {
                "created_by": MOCK_RETIRED,
                "status": "archived",
                "needs_look": False, "needs_look_message": None,
                "title": "Mock Episode — retired spine test (safe to ignore)",
            })
            n += 1
    if MOCK_ROOT.exists():
        shutil.rmtree(MOCK_ROOT)
    log(f"retired {n} mock ticket(s) (NOT deleted — production never deletes) "
        f"+ removed {MOCK_ROOT}")


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
