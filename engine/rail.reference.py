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

import os, sys, json, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

TABLE = "episodes"

# The status contract, in order. Kept here so it lives in exactly one place.
STATUSES = [
    "queued", "building", "awaiting_render", "rendering", "awaiting_cover",
    "assembling", "awaiting_approval", "revising", "ready", "published",
]


# --- config (.env) ---------------------------------------------------------
def _find_env():
    """Walk up from this file until a .env is found (project root holds it)."""
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        candidate = os.path.join(d, ".env")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            raise FileNotFoundError(f"no .env found above {__file__}")
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


def _request(method, query="", body=None, write=False):
    """One place for every HTTP call to the rail."""
    url = _BASE + query
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=_headers(write))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode()}") from None


def _now():
    return datetime.now(timezone.utc).isoformat()


def _q(id):
    return urllib.parse.quote(str(id))


# --- public API ------------------------------------------------------------
def list_all():
    """Every ticket on the board, newest first."""
    return _request("GET", "?select=*&order=created_at.desc")


def list_queued():
    """Tickets waiting to be picked up (status 'queued'), oldest first."""
    return _request("GET", "?select=*&status=eq.queued&order=created_at.asc")


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
    """
    stat = ",".join(sorted(WORKING))
    rows = _request(
        "PATCH",
        f"?status=in.({stat})&claimed_by=not.is.null&claimed_by=neq.{_q(worker)}"
        f"&lease_until=lt.{_ts(_now())}&limit=1",
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
    """Let go of an episode (parked at a human gate, or finished with it)."""
    rows = _request("PATCH", f"?id=eq.{_q(id)}&claimed_by=eq.{_q(worker)}",
                    {"claimed_by": None, "lease_until": None, "updated_at": _now()},
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
