"""
rail.py — Practical Punting "notice board" client.

The rail is a Supabase table ("episodes") that BOTH Cowork Claude and Claude Code
read and write, so episode jobs can be posted, picked up, and tracked in ONE shared
place. This module is the only thing that talks to the rail: keep all Supabase
access here (DRY — one place for the REST calls, headers and the status contract).

Config comes from the project .env — never hard-coded. Because the engine runs
server-side (no user login) and RLS is enabled on the table, it PREFERS the secret
SUPABASE_SERVICE_ROLE_KEY (which bypasses RLS) and falls back to SUPABASE_ANON_KEY for
pre-RLS / read-only use. The service_role key is a SECRET — keep it in this .env only,
NEVER in the web app or any repo.

Status vocabulary (THE contract — match these strings exactly):
    queued -> building -> awaiting_render -> rendering -> awaiting_cover ->
    assembling -> awaiting_approval -> revising -> ready -> published
(awaiting_* = a human step.)

Public functions:
    list_queued()             -> tickets with status "queued" (oldest first)
    list_all()                -> every ticket, newest first (a quick look at the board)
    get_episode(id)           -> one ticket dict, or None
    claim(id)                 -> queued -> building, ATOMICALLY (only if still queued)
    update_status(id, status) -> set status (validated against the vocabulary)
    set_fields(id, {...})     -> patch columns (video_url, ebook_url, thumbnail_url, notes, ...)
    insert(fields)            -> create a ticket (admin/testing) -> new ticket
    delete(id)                -> remove a ticket (admin/testing; destructive)

CLI (quick manual checks):
    python rail.py list
    python rail.py queued
    python rail.py get <id>
    python rail.py claim <id>
    python rail.py status <id> <status>
"""

import http.client
import os, sys, json, ssl, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

TABLE = "episodes"


class RailUnavailable(RuntimeError):
    """The rail could not be reached after retrying. NOT a fault in the data."""


# --- surviving the network (28/29 Jul 2026) ---------------------------------
# THE ENGINE DIED OVERNIGHT ON ONE SLOW HTTPS READ and stayed dead 10h51m. The
# traceback bottomed out in http/client.py `_read_status` — the request went out
# and the response never came — and `_request` caught ONLY HTTPError, so a
# socket-level TimeoutError went straight past it to the top of the process.
# A read timing out on a home connection at 22:05 is an ORDINARY EVENT, not an
# exception.
#
# WHAT IS TRANSIENT, and nothing else: timeouts, resets, DNS, TLS hiccups, and
# the server-side/back-off status codes. A 401, a 404, a 409 or a bad payload is
# a REAL FAULT and must still stop loudly — a blanket `except Exception` would
# trade a loud death for a silent zombie, which is worse.
TRANSIENT_STATUS = {408, 425, 429, 500, 502, 503, 504}
TRANSIENT_NET = (TimeoutError, ConnectionError, ssl.SSLError,
                 http.client.HTTPException, urllib.error.URLError)
RETRY_DELAYS = (2, 5, 10, 20, 30, 60, 60, 60)      # ~3.8 min, then give up loudly

# POST IS NEVER RETRIED. A timeout cannot tell us whether the insert landed, and
# a duplicate episode row is worse than a failed one. Every call that polls —
# the ones that actually killed the engine — is a GET or a PATCH, and a PATCH
# setting fields to fixed values is idempotent.
RETRYABLE_METHODS = {"GET", "PATCH"}

# The status contract, in order. Kept here so it lives in exactly one place.
STATUSES = [
    "queued", "building", "awaiting_render", "rendering", "awaiting_cover",
    "assembling", "awaiting_approval", "revising", "ready", "published",
]


# --- config (.env) ---------------------------------------------------------
# THE .env IS ON DRIVE AND STAYS THERE — TIER 1, never in the repo, deliberately
# never backed up. rail.py moved INTO the repo on 28 Jul 2026 ("code in GitHub,
# media on Drive"), so walking up from __file__ no longer reaches PP Videos/.env:
# it reaches the repo root, which has no .env and a .gitignore forbidding one.
# Look at PP_VIDEOS explicitly first, then keep the original parent walk so this
# still works if rail.py is ever run from somewhere under a folder holding a .env.
def _find_env():
    """Locate the .env: PP_VIDEOS first, then walk up from this file."""
    pp = os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos")
    candidate = os.path.join(pp, ".env")
    if os.path.isfile(candidate):
        return candidate
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        candidate = os.path.join(d, ".env")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            raise FileNotFoundError(
                f"no .env at {os.path.join(pp, '.env')} and none above {__file__}")
        d = parent


def _load_config():
    """Return (url, key). Prefer the service_role key (bypasses RLS — required for the
    engine once RLS is on); fall back to the anon key. Reads real env first, then .env."""
    cfg = dict(os.environ)
    try:
        for line in open(_find_env(), encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = (p.strip() for p in line.split("=", 1))
            cfg.setdefault(k, v)  # real environment wins over .env
    except FileNotFoundError:
        pass
    url = cfg.get("SUPABASE_URL")
    key = cfg.get("SUPABASE_SERVICE_ROLE_KEY") or cfg.get("SUPABASE_ANON_KEY")
    if not (url and key):
        raise RuntimeError("SUPABASE_URL and a key (SERVICE_ROLE or ANON) required in .env")
    return url.rstrip("/"), key


_URL, _KEY = _load_config()
_BASE = f"{_URL}/rest/v1/{TABLE}"


def _headers(write=False):
    h = {
        "apikey": _KEY,
        "Authorization": f"Bearer {_KEY}",
        "Content-Type": "application/json",
    }
    if write:
        h["Prefer"] = "return=representation"  # return the affected row(s)
    return h


def _log(msg):
    """One line, on stderr, so it lands in the engine's terminal without pretending
    to be engine output."""
    print(f"[rail] {msg}", file=sys.stderr, flush=True)


def _request(method, query="", body=None, write=False):
    """One place for every HTTP call to the rail — including surviving the network.

    Transient failures are retried with backoff and logged one line at a time.
    Real faults (401, 404, 409, a bad payload) are raised on the first try, loudly.
    """
    url = _BASE + query
    data = json.dumps(body).encode() if body is not None else None
    retryable = method in RETRYABLE_METHODS
    attempts = len(RETRY_DELAYS) + 1 if retryable else 1

    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers=_headers(write))
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode()
                if attempt > 1:
                    _log(f"recovered after {attempt} attempts: {method} {query[:60]}")
                return json.loads(raw) if raw else []
        except urllib.error.HTTPError as e:
            # HTTPError subclasses URLError, so it MUST be caught first or every
            # 401 would be treated as a network blip and retried into silence.
            if not (retryable and e.code in TRANSIENT_STATUS):
                raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode()}") from None
            why = f"HTTP {e.code}"
        except TRANSIENT_NET as e:
            why = f"{type(e).__name__}: {e}"

        # MUST be >= attempts, not > len(RETRY_DELAYS): with attempts == 1 (a POST)
        # the loop would otherwise fall off its end and RETURN None — a failed write
        # reported as success. The first version did exactly that and the test still
        # passed, because it only asserted the retry COUNT.
        if attempt >= attempts:
            raise RailUnavailable(
                f"{method} gave up after {attempt} attempt(s) ({why}). "
                + ("This is the network, not the data."
                   if retryable else
                   "A POST is never retried: a timeout cannot say whether the insert "
                   "landed, and a duplicate row is worse than a failed one."))
        delay = RETRY_DELAYS[attempt - 1]
        _log(f"{why} on {method} {query[:60] or '/'} — retry {attempt} in {delay}s")
        time.sleep(delay)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _q(id):
    return urllib.parse.quote(str(id))


# --- public API ------------------------------------------------------------
def list_all():
    """Every ticket on the board, newest first."""
    return _request("GET", "?select=*&order=created_at.desc")


# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 E29 — THE SUITE'S OWN TICKETS ARE NOT FOOD. (Landed 18 Aug 2026, batch 2.)
#
# `test_dead_zone.py` creates a real row at a working status with a DEAD LEASE, which
# is precisely the shape `reclaim_stale()` hunts for. A running engine took it
# mid-test, with its own log as the evidence:
#
#     [03:45:32] reclaimed a stale-leased episode PP-EP9019 at building
#     [03:45:52] !! lost ownership of the episode (lease reclaimed) — stopping work
#
# The suite reported `dead zone: 2 passed, 1 failed`; the same test passes alone. **A
# gate that is green or red depending on what else is running is not a gate** — and it
# fails in the dangerous direction, because a red dead-zone test reads as "the dead
# zone is back". The workaround was to remember to hold the engine. This is the fix.
#
# ⚠️ IT KEYS ON `ep_number`, NOT ON THE ID, AND THE FLOOR IS 9000 — NOT "9xxx".
# The ids in the fixtures include PP-EP96..99, and **Hugh and Jodie are making 300
# episodes**, so 96–99 are real episodes nobody has recorded yet. A prefix rule would
# have quietly stopped the engine claiming four real episodes somewhere around next
# year. Four digits from 9000 up is clear of 300 by any margin that matters.
#
# NULL is claimable: a real ticket that has not been given a number yet must never be
# filtered out by a guard aimed at the test suite.
TEST_EP_FLOOR = 9000
NOT_A_TEST = f"&or=(ep_number.is.null,ep_number.lt.{TEST_EP_FLOOR})"


def list_queued():
    """Tickets waiting to be picked up (status 'queued'), oldest first.

    Synthetic test tickets are excluded — see E29 above."""
    return _request("GET", "?select=*&status=eq.queued" + NOT_A_TEST
                    + "&order=created_at.asc")


def get_episode(id):
    """One ticket by id, or None if it doesn't exist."""
    rows = _request("GET", f"?select=*&id=eq.{_q(id)}")
    return rows[0] if rows else None


def claim(id):
    """Move queued -> building atomically.

    The status=eq.queued filter means the update only lands if the ticket is STILL
    queued, so two workers can't both claim it. Returns the ticket if we got it,
    or None if it was already taken / not queued.
    """
    rows = _request("PATCH", f"?id=eq.{_q(id)}&status=eq.queued",
                    {"status": "building", "updated_at": _now()}, write=True)
    return rows[0] if rows else None


def update_status(id, status):
    """Set a ticket's status (validated against the contract)."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}; allowed: {', '.join(STATUSES)}")
    return set_fields(id, {"status": status})


def set_fields(id, fields):
    """Patch arbitrary columns on a ticket (also stamps updated_at)."""
    payload = dict(fields)
    payload["updated_at"] = _now()
    rows = _request("PATCH", f"?id=eq.{_q(id)}", payload, write=True)
    return rows[0] if rows else None


# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 I2 — THE SCRIPT IS SEATED ONLY INTO AN EMPTY BOX. IT IS NEVER OVERWRITTEN.
#
# `script_snapshot` is the script's home (ruling A5). TWO writers are about to
# share it: the board's script textarea (A17, owed before EP18) and the machine's
# drafting pass (docs/DESIGN-the-pre-claim-drafting-pass.md).
#
#     THIS GUARD PROTECTS THE HUMAN FROM THE MACHINE. NEVER THE REVERSE.
#
# Jodie overwriting a machine draft is her call and always was — she is the editor.
# A machine landing 1,500 words on top of a sentence she is halfway through typing
# is EP16's corrupted script_doc_url with the whole script at stake: an insertion
# at offset 17, a paste arriving where the caret used to be.
#
# ⚠️ AND THE RACE IS REAL, NOT THEORETICAL, BECAUSE THE WRITER TAKES MINUTES.
# The measured episode.json commission ran 783 SECONDS. Reading "is it empty?" when
# a drafting pass STARTS and writing when it FINISHES leaves a window THIRTEEN
# MINUTES WIDE for a human to type into. A read-then-write in Python does not
# narrow that window, it merely moves it — the check and the set are two round
# trips and anything can happen between them.
#
#     SO THE CHECK IS NOT IN PYTHON. IT IS IN THE URL, AND THE DATABASE
#     EVALUATES IT AS PART OF THE UPDATE ITSELF.
#
# One statement: UPDATE ... WHERE id = ? AND (snapshot IS NULL OR snapshot = '').
# There is no "between check and set" to slip into, because there is no between.
# This is the SAME shape claim_next already uses to win its race (filters in the
# query string, one writer gets a row back, the loser gets nothing) — the same
# file, the same mechanism, nothing new to learn or to get subtly wrong.
#
# 🚫 WHY NOT A DATABASE TRIGGER, WHICH WOULD BE STRONGER STILL: migration 005's
# trigger is the right shape for the web-address columns because NOBODY should
# write a bad value there. Here the human SHOULD be able to overwrite. A trigger
# cannot tell the board apart from the engine, so it would block Jodie's own edit
# — enforcing the rule by breaking the thing the rule exists to protect.
#
# 📏 MEASURED, NOT ASSUMED (read-only probe, 7 Aug 2026): PostgREST parses
# `or=(script_snapshot.is.null,script_snapshot.eq.)` and it selects exactly the
# five NULL rows (EP06-EP10); the other seven carry 5,765-14,176 characters.
#
# ⚠️ WHITESPACE-ONLY COUNTS AS OCCUPIED, ON PURPOSE. A box holding " " refuses the
# machine's draft. That is the safe direction — the failure is "the studio wrote
# nothing", never "the studio wrote over somebody" — and it is stated here because
# it is a decision, not an oversight.
def seat_script_if_empty(id, text):
    """Seat a script into `script_snapshot` ONLY if the field is empty.

    Returns the updated ticket if the words landed, or None if they did not.

    None means EITHER the box already held text OR there is no such episode. The
    caller re-reads to say which — a read is safe; it is the WRITE that had to be
    conditional. (claim_next carries the same ambiguity for the same reason.)
    """
    if not str(text or "").strip():
        # Seating an empty script would leave the field "empty" by this very
        # function's definition, so the next pass would try again forever.
        raise ValueError("refusing to seat an empty script into script_snapshot")
    rows = _request(
        "PATCH",
        f"?id=eq.{_q(id)}&or=(script_snapshot.is.null,script_snapshot.eq.)",
        {"script_snapshot": text, "updated_at": _now()},
        write=True)
    return rows[0] if rows else None


def insert(fields):
    """Create a ticket (admin/testing). Returns the new ticket."""
    rows = _request("POST", "", fields, write=True)
    return rows[0] if rows else None


def delete(id):
    """Remove a ticket (admin/testing — destructive)."""
    _request("DELETE", f"?id=eq.{_q(id)}")
    return True


# --- engine support: lease, heartbeat, checkpoints (Phase 2a, 2026-07-24) ---
# The orchestrator claims an episode with a LEASE (claimed_by + lease_until):
# one writer per episode, and a crashed worker's lease simply expires, so the
# episode is reclaimable instead of orphaned. All timestamps are UTC.

WORKING = {"building", "rendering", "assembling", "revising"}  # engine-active statuses


def _ts(dt_iso):
    """URL-safe timestamp for a PostgREST filter."""
    return urllib.parse.quote(dt_iso)


def _now_plus(seconds):
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def claim_next(worker, lease_secs=180):
    """Claim the OLDEST queued episode: queued -> building, atomically, with a lease.

    SCRIPT GATE + WORDS GATE (Jodie, 26 Jul 2026): an episode is only claimable
    once a human has done BOTH — approved the words (title_approved: title, hook,
    byline) AND ticked "I've read the script" (script_read). Approving the script
    is a DECISION and stays human forever; starting a render is a chore and may
    one day be automated. Unapproved episodes stay queued on the board with the
    words + script card showing.

    Both halves are in the PostgREST filter as well as the pre-check, so the gate
    holds even if two workers race. The filters (status still queued, and
    unclaimed or lease expired) make the update land for exactly one worker; a
    loser gets no row back and tries the next ticket. Returns the claimed ticket,
    or None if nothing is claimable.
    """
    for ep in list_queued():
        if not (ep.get("title_approved") and ep.get("script_read")):
            continue                       # gate not passed — not claimable
        rows = _request(
            "PATCH",
            f"?id=eq.{_q(ep['id'])}&status=eq.queued&title_approved=is.true"
            f"&script_read=is.true"
            f"&or=(claimed_by.is.null,lease_until.lt.{_ts(_now())})",
            {"status": "building", "claimed_by": worker,
             "lease_until": _now_plus(lease_secs),
             "heartbeat_at": _now(), "started_at": ep.get("started_at") or _now(),
             "updated_at": _now()},
            write=True)
        if rows:
            return rows[0]
    return None


def resume_own(worker):
    """The episode THIS worker already owns in a working status, if any.

    Same worker identity == same single writer, so no lease check: after a crash
    or kill, the restarted engine takes straight over (and renews the lease).
    """
    stat = ",".join(sorted(WORKING))
    rows = _request("GET", f"?select=*&claimed_by=eq.{_q(worker)}&status=in.({stat})"
                           "&order=updated_at.asc")
    if not rows:
        return None
    ep = rows[0]
    heartbeat(ep["id"], worker)
    return get_episode(ep["id"])


def reclaim_stale(worker, lease_secs=180):
    """Take over another worker's episode whose lease has EXPIRED (it crashed).

    Only working statuses are eligible; the lease filter makes the takeover
    atomic (two rescuers -> one winner). Returns the ticket or None.

    🔴 AND IT DOES NOT EAT THE SUITE'S TICKETS — see E29 at the top of this file. This
    is the exact call that reclaimed PP-EP9019 out from under `test_dead_zone.py`.
    """
    stat = ",".join(sorted(WORKING))
    rows = _request(
        "PATCH",
        f"?status=in.({stat})&claimed_by=not.is.null&claimed_by=neq.{_q(worker)}"
        f"&lease_until=lt.{_ts(_now())}{NOT_A_TEST}&limit=1",
        {"claimed_by": worker, "lease_until": _now_plus(lease_secs),
         "heartbeat_at": _now(), "updated_at": _now()},
        write=True)
    return rows[0] if rows else None


def heartbeat(id, worker, lease_secs=180):
    """I'm alive: bump heartbeat_at and extend the lease — but ONLY if we still
    own the episode (guards against writing to a reclaimed ticket). Returns the
    row if the beat landed, None if ownership was lost."""
    rows = _request("PATCH", f"?id=eq.{_q(id)}&claimed_by=eq.{_q(worker)}",
                    {"heartbeat_at": _now(), "lease_until": _now_plus(lease_secs),
                     "updated_at": _now()}, write=True)
    return rows[0] if rows else None


def checkpoint(id, build_state):
    """Persist the resumable build state (steps done + job IDs + checkpoint).
    Single-writer per episode, so a full-object write is safe."""
    return set_fields(id, {"build_state": build_state})


def progress(id, step_text, pct):
    """Update the board's alive-feel: the human progress line + the bar %."""
    return set_fields(id, {"progress_step": step_text,
                           "progress_pct": max(0, min(100, int(pct)))})


def flag_needs_look(id, message):
    """A problem needs a human. The episode KEEPS its status — needs_look is the
    orthogonal red flag the board renders."""
    return set_fields(id, {"needs_look": True, "needs_look_message": message})


def release(id, worker):
    """Let go of an episode (parked at a human gate, or finished with it).

    ⚠️ ONLY SAFE WHEN THE EPISODE IS ALSO LEAVING A WORKING STATUS. On a working
    status this creates the dead zone — see hand_back() below, and use that instead.
    """
    rows = _request("PATCH", f"?id=eq.{_q(id)}&claimed_by=eq.{_q(worker)}",
                    {"claimed_by": None, "lease_until": None, "updated_at": _now()},
                    write=True)
    return rows[0] if rows else None


def hand_back(id, worker, reason="exited for new code"):
    """Let go of a WORKING episode in a state something can pick it up again.

    🔴 THE DEAD ZONE, AND WHY release() IS THE WRONG CALL HERE. reclaim_stale() filters
    `claimed_by=not.is.null`, deliberately — a null owner on a working status would
    otherwise be indistinguishable from a row mid-claim. So an episode left at a working
    status with claimed_by NULL is picked up by NOTHING, EVER. Not reclaim_stale (null),
    not resume_own (not ours), not claim_next (wrong status).
        The stale-code exit knew this — its own docstring says "releasing WITHOUT
    clearing ownership is how an episode reaches a working status with claimed_by: NULL
    — the dead zone, which nothing can pick up, ever" — and then called release()
    anyway. EP18 hit it in August. EP19 hit it on 9 Aug 2026: the guard fired while the
    episode was flagged, the episode went ownerless, and it sat at 33% with its flag
    already cleared until a human noticed. A comment warning about a trap is not a
    guard against it.

    So ownership goes to a TOMBSTONE — this worker's name plus why it left — with a
    lease already expired. reclaim_stale() sees a non-null owner that is not the live
    worker, with a dead lease, and takes it on the next tick: seconds, not never. The
    name is also readable on the board, which "NULL" never was.
    """
    from datetime import timedelta
    rows = _request(
        "PATCH", f"?id=eq.{_q(id)}&claimed_by=eq.{_q(worker)}",
        {"claimed_by": f"{worker} ({reason})",
         "lease_until": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
         "updated_at": _now()},
        write=True)
    return rows[0] if rows else None


# --- tiny CLI --------------------------------------------------------------
def _dump(x):
    print(json.dumps(x, indent=2, default=str))


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    if cmd == "list":
        _dump(list_all())
    elif cmd == "queued":
        _dump(list_queued())
    elif cmd == "get":
        _dump(get_episode(args[1]))
    elif cmd == "claim":
        _dump(claim(args[1]))
    elif cmd == "status":
        _dump(update_status(args[1], args[2]))
    else:
        print(__doc__)
