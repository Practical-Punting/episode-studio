#!/usr/bin/env python3
"""A checker is proved by the bad build it refused (B1).

Two things must BOTH be true, and they pull in opposite directions:
  · a TIMEOUT is an ordinary overnight event — retry, log, survive;
  · a 401 is a real fault — stop, loudly, first time.
A blanket `except Exception` would pass the first test and fail the second, by
trading a loud death for a silent zombie.

Everything here is a FAKE urlopen. It never touches Supabase and never touches the
running engine — Jodie is working against that engine while this runs.
"""
import io
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rail                                                        # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                              # noqa: BLE001
        pass

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def patched(seq):
    """urlopen that walks `seq`: an exception class/instance is raised, bytes are
    returned as a body. Records how many times it was called."""
    calls = {"n": 0}

    def fake(req, timeout=None):
        i = calls["n"]
        calls["n"] += 1
        item = seq[min(i, len(seq) - 1)]
        if isinstance(item, BaseException):
            raise item
        return FakeResponse(item)
    return fake, calls


def run(seq, method="GET"):
    fake, calls = patched(seq)
    real_open, real_sleep = urllib.request.urlopen, rail.time.sleep
    urllib.request.urlopen = fake
    rail.time.sleep = lambda s: None            # do not really wait in a test
    try:
        return rail._request(method, "?select=*"), calls
    finally:
        urllib.request.urlopen = real_open
        rail.time.sleep = real_sleep


# ---- 1. THE FAULT THAT KILLED THE ENGINE ----------------------------------
def _timeout_then_ok():
    out, calls = run([TimeoutError("The read operation timed out"), b"[]"])
    assert out == [], f"expected the retry to succeed, got {out!r}"
    assert calls["n"] == 2, f"expected 2 attempts (fail, then succeed), got {calls['n']}"


case("a read TIMEOUT is retried and the call succeeds", _timeout_then_ok)


def _timeout_sustained_is_not_fatal_type():
    try:
        run([TimeoutError("timed out")] * 20)
        raise AssertionError("a sustained outage should still surface, not hang forever")
    except rail.RailUnavailable:
        pass                                     # the engine's idle loop catches this
    except TimeoutError as e:
        raise AssertionError(
            f"raised the RAW {type(e).__name__} — this is the exception that reached "
            f"the top of the process and killed it overnight") from None


case("a SUSTAINED outage raises RailUnavailable, never the raw TimeoutError",
     _timeout_sustained_is_not_fatal_type)


def _reset_and_dns_retried():
    for exc in (ConnectionResetError("reset by peer"),
                urllib.error.URLError("[Errno 11001] getaddrinfo failed")):
        out, calls = run([exc, b"[]"])
        assert calls["n"] == 2, f"{type(exc).__name__} was not retried"


case("connection reset and DNS failure are retried too", _reset_and_dns_retried)


def _five_hundred_retried():
    out, calls = run([urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"")), b"[]"])
    assert calls["n"] == 2, f"a 503 should be retried, attempts={calls['n']}"


case("a 503 is retried (server-side, transient)", _five_hundred_retried)


# ---- 2. AND A REAL FAULT MUST STILL STOP, FIRST TIME ----------------------
def _401_is_fatal():
    try:
        _, calls = run([urllib.error.HTTPError("u", 401, "Unauthorized", {},
                                               io.BytesIO(b"bad key"))])
        raise AssertionError("a 401 did NOT raise — a bad key would poll in silence")
    except RuntimeError as e:
        if isinstance(e, rail.RailUnavailable):
            raise AssertionError("a 401 was treated as a network blip") from None
        assert "401" in str(e), f"the error should name the status: {e}"


case("a 401 stops immediately and loudly — NOT retried", _401_is_fatal)


def _401_not_retried_once():
    fake, calls = patched([urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b""))])
    real_open, real_sleep = urllib.request.urlopen, rail.time.sleep
    urllib.request.urlopen, rail.time.sleep = fake, (lambda s: None)
    try:
        rail._request("GET", "?select=*")
    except RuntimeError:
        pass
    finally:
        urllib.request.urlopen, rail.time.sleep = real_open, real_sleep
    assert calls["n"] == 1, f"a 401 was attempted {calls['n']} times; it must be tried once"


case("a 401 is attempted exactly ONCE", _401_not_retried_once)


def _404_is_fatal():
    try:
        run([urllib.error.HTTPError("u", 404, "nope", {}, io.BytesIO(b""))])
        raise AssertionError("a 404 did not raise")
    except rail.RailUnavailable:
        raise AssertionError("a 404 was treated as transient") from None
    except RuntimeError:
        pass


case("a 404 stops loudly", _404_is_fatal)


def _post_never_retried():
    fake, calls = patched([TimeoutError("timed out"), b"[]"])
    real_open, real_sleep = urllib.request.urlopen, rail.time.sleep
    urllib.request.urlopen, rail.time.sleep = fake, (lambda s: None)
    raised = None
    try:
        out = rail._request("POST", "", {"x": 1}, write=True)
        raised = f"returned {out!r} instead of raising"
    except rail.RailUnavailable:
        pass
    except BaseException as e:                                     # noqa: BLE001
        raised = f"raised the wrong type: {type(e).__name__}"
    finally:
        urllib.request.urlopen, rail.time.sleep = real_open, real_sleep
    assert calls["n"] == 1, (
        f"a POST was retried {calls['n']} times — a timeout cannot tell us whether the "
        f"insert landed, and a duplicate episode row is worse than a failed one")
    # THE ASSERTION THE FIRST VERSION OF THIS TEST WAS MISSING. It only counted
    # attempts, so it passed while _request fell off the end of its loop and returned
    # None — a failed write reported as a success. Counting calls is not enough:
    # assert what the caller actually receives.
    assert raised is None, f"a failed POST {raised} — a silent failed write"


case("a POST is NEVER retried, and a failed POST RAISES (never returns None)",
     _post_never_retried)

print(f"\nrail transient handling: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
