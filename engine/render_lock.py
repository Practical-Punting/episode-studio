# -*- coding: utf-8 -*-
"""
ONE HEAVY RENDER AT A TIME — the cross-project render lock.
Built 29 August 2026, after Jodie asked to run Inspirational Women and
Practical Punting on the same machine at the same time.

    import render_lock
    with render_lock.hold("IW", "IWEP034 build"):
        ...the CPU-bound half...

    python render_lock.py status
    python render_lock.py selftest

────────────────────────────────────────────────────────────────────────────
WHY THIS EXISTS
────────────────────────────────────────────────────────────────────────────
Two production lines now share one 8 GB laptop: this one, and Practical
Punting (a different client, a different repo, its own Claude Code). Their
front halves do not compete — painting, downloading, narrating and packaging
are network- and API-bound, and `make_episode --prepare` already exists
precisely because those steps are free while something else renders.

Their back halves compete for the whole machine. Two ffmpeg jobs on 8 GB do
not run at half speed; they page to disk and one of them eventually dies
mid-write. That is the same class of event that produced 26,956 corrupt
packets in August, and it is worth exactly one small file to make impossible.

So: the lock guards ONLY the CPU-bound half. Everything before it stays
concurrent on purpose. The overlap Jodie wants is the whole point — this
narrows what has to be serialised to the one thing that actually must be.

────────────────────────────────────────────────────────────────────────────
WHAT THIS FILE MAY NEVER DO  (make_episode rule 4, inherited)
────────────────────────────────────────────────────────────────────────────
**It never kills, never relaunches, and never steals a lock on its own.**

A stale lock is detected by a heartbeat that has stopped advancing — which is
a liveness signal, and liveness signals are allowed to be wrong here for
exactly one reason: nothing automatic acts on them. When this module decides a
lock looks stale it REPORTS and RAISES. A human clears it. The moment someone
"improves" that into an automatic steal, a wrong signal starts two encoders
again and August is back.

Rule 3 is the belt to this braces: every attempt already writes a unique
filename, so even a wrongly-cleared lock cannot put two encoders on one path.
Neither guard is trusted alone.

────────────────────────────────────────────────────────────────────────────
WHERE THE LOCK LIVES, AND WHY NOT ON G:
────────────────────────────────────────────────────────────────────────────
%LOCALAPPDATA%\\equest-render\\render.lock  (override: $EQUEST_RENDER_LOCK)

Not on G:. Google Drive syncs on its own schedule, and a lock whose existence
is eventually-consistent is not a lock. Local, per-user, no admin needed, and
both Claude Code instances run as the same user so both can see it.

The holder writes a sidecar `.beat` file rather than rewriting the lock, so a
reader can never catch the lock file half-written.
"""
import errno
import io
import json
import os
import socket
import sys
import tempfile
import threading
import time

__all__ = ["hold", "acquire", "release", "read_holder", "status_line",
           "LockBusy", "LockStale"]

BEAT_EVERY_S = 30.0        # how often the holder proves it is alive
STALE_AFTER_S = 900.0      # 15 min of no heartbeat -> report, do not steal
POLL_S = 20.0              # how often a waiter re-checks
SAY_EVERY_S = 60.0         # how often a waiter prints that it is still waiting

# Paths THIS process currently owns, so a nested hold can be told apart from a
# genuinely competing one. Kept in memory on purpose: inferring re-entry from
# the pid on disk would also match a different tool that happened to reuse a
# recycled pid.
_HELD = {}


class LockBusy(Exception):
    """Someone else holds the lock and is demonstrably alive."""


class LockStale(Exception):
    """The lock is held by something that stopped breathing. A HUMAN decides."""


# ═══════════════════════════════════════════════════════════════════════════
# where
# ═══════════════════════════════════════════════════════════════════════════
def lock_path():
    """The one path both projects agree on."""
    p = os.environ.get("EQUEST_RENDER_LOCK")
    if p:
        return p
    base = (os.environ.get("LOCALAPPDATA")
            or os.environ.get("XDG_RUNTIME_DIR")
            or os.path.expanduser("~"))
    return os.path.join(base, "equest-render", "render.lock")


def _beat_path(path):
    return path + ".beat"


def _disabled():
    return os.environ.get("EQUEST_RENDER_LOCK_DISABLE", "").strip() in ("1", "true", "TRUE")


# ═══════════════════════════════════════════════════════════════════════════
# reading
# ═══════════════════════════════════════════════════════════════════════════
def read_holder(path=None):
    """Who holds it, or None. Never raises on a malformed or vanishing lock —
    a lock we cannot parse is reported as an unknown holder, not as free."""
    path = path or lock_path()
    try:
        with io.open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (IOError, OSError):
        return None
    except ValueError:
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("project", "?")
    d.setdefault("job", "?")
    d.setdefault("pid", None)
    d.setdefault("started", None)
    d["age_s"] = _silence_s(path)
    return d


def _silence_s(path):
    """Seconds since the holder last proved it was alive."""
    for p in (_beat_path(path), path):
        try:
            return max(0.0, time.time() - os.path.getmtime(p))
        except (IOError, OSError):
            continue
    return 0.0


def status_line(path=None):
    path = path or lock_path()
    h = read_holder(path)
    if not h:
        return "render lock: FREE   (%s)" % path
    return ("render lock: HELD by %s - %s   pid=%s  quiet for %ds%s"
            % (h["project"], h["job"], h["pid"], int(h["age_s"]),
               "   <- LOOKS STALE" if h["age_s"] > STALE_AFTER_S else ""))


# ═══════════════════════════════════════════════════════════════════════════
# taking and giving back
# ═══════════════════════════════════════════════════════════════════════════
def _try_create(path, payload):
    """Atomic create-if-absent. True if we now own it."""
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as e:
        if e.errno in (errno.EEXIST, errno.EACCES):
            return False
        raise
    try:
        os.write(fd, json.dumps(payload, indent=2).encode("utf-8"))
    finally:
        os.close(fd)
    return True


class _Heart(object):
    """Touches the sidecar so waiters can see we are alive. Daemon: it can
    never hold the process open, and it never touches the lock file itself."""

    def __init__(self, path):
        self.beat = _beat_path(path)
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run)
        self._t.daemon = True

    def start(self):
        self._touch()
        self._t.start()
        return self

    def _touch(self):
        try:
            with io.open(self.beat, "w", encoding="utf-8") as f:
                f.write(u"%.0f\n" % time.time())
        except (IOError, OSError):
            pass                      # a missed beat is not worth an abort

    def _run(self):
        while not self._stop.wait(BEAT_EVERY_S):
            self._touch()

    def stop(self):
        self._stop.set()


def acquire(project, job, path=None, wait=True, timeout_s=None, say=print):
    """Own the lock, or raise. Returns a token you must pass back to release().

    wait=False   -> LockBusy immediately if someone else holds it
    timeout_s    -> LockBusy after this long; None waits indefinitely
    A holder that has stopped breathing raises LockStale. WE DO NOT STEAL IT.
    """
    path = path or lock_path()
    token = "%d-%.0f" % (os.getpid(), time.time() * 1000)
    payload = {"project": project, "job": job, "pid": os.getpid(),
               "host": socket.gethostname(),
               "started": time.strftime("%Y-%m-%d %H:%M:%S"),
               "token": token}

    t0 = time.time()
    said = 0.0
    while True:
        if _try_create(path, payload):
            heart = _Heart(path).start()
            _HELD[os.path.abspath(path)] = token
            return {"path": path, "token": token, "heart": heart}

        h = read_holder(path)
        if h is None:
            continue                   # it vanished between create and read

        if h.get("token") == _HELD.get(os.path.abspath(path)):
            # A nested `with hold(...)` inside a block that already owns it.
            # Hand back a BORROWED handle - token None, so release() declines to
            # remove a lock the outer block is still relying on. Without this a
            # nested hold would wait on itself forever, which is a worse bug
            # than the one it guards.
            return {"path": path, "token": None, "heart": None, "borrowed": True}

        if h["age_s"] > STALE_AFTER_S:
            raise LockStale(
                "The render lock is held by %s (%s, pid %s, started %s) but it "
                "has not breathed for %d minutes.\n"
                "NOTHING IS AUTOMATICALLY CLEARED HERE - a wrong guess starts a "
                "second encoder.\n"
                "Check whether that render is really finished, then either let "
                "it finish or run:\n"
                "    python render_lock.py release --force\n"
                "Lock file: %s"
                % (h["project"], h["job"], h["pid"], h["started"],
                   int(h["age_s"] / 60), path))

        if not wait:
            raise LockBusy("%s is rendering (%s). Not waiting." % (h["project"], h["job"]))
        if timeout_s is not None and (time.time() - t0) > timeout_s:
            raise LockBusy("waited %d min for %s (%s); giving up."
                           % (int((time.time() - t0) / 60), h["project"], h["job"]))

        if say and (time.time() - said) >= SAY_EVERY_S:
            said = time.time()
            say("waiting for the render lock: %s is on %s (%d min so far)"
                % (h["project"], h["job"], int((time.time() - t0) / 60)), flush=True)
        # Never sleep past our own deadline, or a 3-second timeout reports back
        # after 20 and looks like the lock misbehaved.
        nap = POLL_S if timeout_s is None else min(
            POLL_S, max(0.5, t0 + timeout_s - time.time()))
        time.sleep(nap)


def release(handle):
    """Give it back — but ONLY if it is still ours. A lock someone else now
    holds is never removed by us; that is how you delete a live render's lock."""
    if not handle:
        return False
    path, token = handle["path"], handle["token"]
    if handle.get("heart"):
        handle["heart"].stop()
    h = read_holder(path)
    if not h or h.get("token") != token:
        return False
    _HELD.pop(os.path.abspath(path), None)
    for p in (_beat_path(path), path):
        try:
            os.remove(p)
        except (IOError, OSError):
            pass
    return True


class hold(object):
    """Context manager. `with hold("IW", "IWEP034 build"):`"""

    def __init__(self, project, job, path=None, wait=True, timeout_s=None, say=print):
        self.args = (project, job, path, wait, timeout_s, say)
        self.handle = None

    def __enter__(self):
        if _disabled():
            (self.args[5] or (lambda *a, **k: None))(
                "render lock DISABLED by EQUEST_RENDER_LOCK_DISABLE - "
                "you are responsible for not starting a second render.")
            return self
        p, j, path, wait, timeout_s, say = self.args
        self.handle = acquire(p, j, path=path, wait=wait, timeout_s=timeout_s, say=say)
        if say:
            say("render lock: HELD by %s - %s" % (p, j), flush=True)
        return self

    def __exit__(self, *exc):
        release(self.handle)
        return False


# ═══════════════════════════════════════════════════════════════════════════
# the command line
# ═══════════════════════════════════════════════════════════════════════════
def _as_a_foreign_process(path):
    """Forget, in memory only, that we own this lock.

    The real case is two SEPARATE processes — IW's build and PP's assembly —
    and `_HELD` is what tells a nested hold apart from a competing one. A test
    living inside one process has to drop that memory or it would be answering
    its own re-entry question, and every 'is a rival refused?' check would pass
    for the wrong reason. Nothing on disk is touched.
    """
    return _HELD.pop(os.path.abspath(path), None)


def _selftest():
    """Proves the five things that matter, in a throwaway directory."""
    d = tempfile.mkdtemp(prefix="locktest-")
    p = os.path.join(d, "render.lock")
    ok = []

    h = acquire("IW", "selftest", path=p)
    ok.append(("a free lock is taken", read_holder(p)["project"] == "IW"))

    mine = _as_a_foreign_process(p)
    try:
        acquire("PP", "other", path=p, wait=False)
        ok.append(("a held lock is refused", False))
    except LockBusy:
        ok.append(("a held lock is refused", True))
    _HELD[os.path.abspath(p)] = mine

    nested = acquire("IW", "selftest nested", path=p, wait=False)
    ok.append(("a nested hold borrows instead of deadlocking",
               nested.get("borrowed") is True))
    ok.append(("releasing a borrowed handle leaves the lock alone",
               release(nested) is False and os.path.exists(p)))

    other = {"path": p, "token": "not-ours"}
    ok.append(("a lock we do not own is not removed",
               release(other) is False and os.path.exists(p)))

    ok.append(("the owner can release it", release(h) is True and not os.path.exists(p)))

    h = acquire("IW", "selftest-stale", path=p)
    h["heart"].stop()
    old = time.time() - (STALE_AFTER_S + 60)
    os.utime(_beat_path(p), (old, old))
    os.utime(p, (old, old))
    _as_a_foreign_process(p)
    try:
        acquire("PP", "other", path=p, wait=False)
        ok.append(("a silent holder raises LockStale, never a steal", False))
    except LockStale:
        ok.append(("a silent holder raises LockStale, never a steal", True))
    except LockBusy:
        ok.append(("a silent holder raises LockStale, never a steal", False))
    release(h)

    for name, passed in ok:
        print("  %s  %s" % ("PASS" if passed else "FAIL", name))
    return 0 if all(p for _, p in ok) else 1


def main(argv):
    cmd = (argv[1] if len(argv) > 1 else "status").lower()
    path = lock_path()

    if cmd == "status":
        print(status_line(path))
        return 0

    if cmd == "selftest":
        return _selftest()

    if cmd == "wait":
        with hold("manual", " ".join(argv[2:]) or "held from the command line"):
            print("lock held. Ctrl-C or close this window to give it back.")
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                pass
        return 0

    if cmd == "release":
        if "--force" not in argv:
            print("This removes a lock this process does not own.\n"
                  + status_line(path)
                  + "\nIf that render really is finished, re-run with --force.")
            return 1
        for p in (_beat_path(path), path):
            try:
                os.remove(p)
            except (IOError, OSError):
                pass
        print("lock cleared by hand:", path)
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
