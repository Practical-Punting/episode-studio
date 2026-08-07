#!/usr/bin/env python3
"""I2 — the script is seated only into an EMPTY box, and never overwritten.

THE FAULT IT STANDS AGAINST. `script_snapshot` is about to have two writers: the
board's textarea (A17) and the machine's drafting pass. A machine landing 1,500
words on top of a sentence a human is halfway through typing is EP16's corrupted
script_doc_url with the whole script at stake.

    THIS GUARD PROTECTS THE HUMAN FROM THE MACHINE. NEVER THE REVERSE.

The case that matters most is the one a green suite would never mention:

    the_condition_is_in_the_url   — a Python read-then-write would pass every
                                    behavioural test here and still lose the race,
                                    because the commission takes MINUTES. This
                                    case reads the actual request and fails if the
                                    conditional is not in it.

Nothing here touches the network: `rail._request` is replaced by a recorder.
The REAL rail is exercised separately, against a throwaway ticket and inside a
rolled-back transaction — see the scratchpad proofs named in the run log.

Run: python engine/test_seat_script.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

import rail                                                            # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


class Recorder:
    """Stands in for rail._request and remembers exactly what was asked for."""

    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [{"id": "x", "script_snapshot": "seated"}]
        self.calls = []

    def __call__(self, method, query="", body=None, write=False):
        self.calls.append({"method": method, "query": query, "body": body, "write": write})
        return self.rows


def main():                                                            # noqa: C901
    real_request = rail._request

    print("\n-- it seats words into an empty box --")
    rec = Recorder()
    rail._request = rec
    try:
        out = rail.seat_script_if_empty("EP-ID", "Gordon says something.")
    finally:
        rail._request = real_request
    check("a successful seat returns the ticket", out == rec.rows[0])
    check("  exactly one request was made", len(rec.calls) == 1, f"{len(rec.calls)}")
    call = rec.calls[0]
    check("  it is a PATCH", call["method"] == "PATCH")
    check("  it asks for the row back", call["write"] is True)
    check("  the words are the payload", call["body"]["script_snapshot"] == "Gordon says something.")
    check("  and updated_at is stamped", "updated_at" in call["body"])

    print("\n-- 🔴 THE CONDITION IS IN THE URL, NOT IN PYTHON --")
    # A read-then-write would satisfy every behavioural case in this file and
    # still lose the race, because the drafting commission runs for MINUTES.
    # Only the request itself can prove the check and the set are one statement.
    q = call["query"]
    check("the request carries an is-empty condition", "script_snapshot" in q, q)
    check("  it accepts NULL", "script_snapshot.is.null" in q, q)
    check("  it accepts the empty string", "script_snapshot.eq." in q, q)
    check("  the two are OR'd", q.count("or=(") == 1, q)
    check("  and it is scoped to one episode", "id=eq.EP-ID" in q, q)
    check("  NO unconditional PATCH is ever issued",
          not any(c["method"] == "PATCH" and "script_snapshot.is.null" not in c["query"]
                  for c in rec.calls))
    check("  the guard never READS first (one round trip, no window)",
          not any(c["method"] == "GET" for c in rec.calls))

    print("\n-- an occupied box refuses, and says it did nothing --")
    rec = Recorder(rows=[])          # the server matched no row: already occupied
    rail._request = rec
    try:
        out = rail.seat_script_if_empty("EP-ID", "words the machine wrote")
    finally:
        rail._request = real_request
    check("a refused seat returns None", out is None)
    check("  it still only made the one conditional attempt", len(rec.calls) == 1)
    check("  it did NOT fall back to an unconditional write",
          "script_snapshot.is.null" in rec.calls[0]["query"])

    print("\n-- it refuses to seat nothing --")
    for bad, label in [("", "empty string"), ("   ", "spaces"),
                       ("\n\n", "newlines"), (None, "None")]:
        rec = Recorder()
        rail._request = rec
        try:
            rail.seat_script_if_empty("EP-ID", bad)
            raised = False
        except ValueError:
            raised = True
        finally:
            rail._request = real_request
        check(f"  {label} is refused before any request", raised and not rec.calls)

    print("\n-- the rail's no-delete rule is untouched by this --")
    src = (HERE / "rail.py").read_text(encoding="utf-8")
    fn = src.split("def seat_script_if_empty")[1].split("\ndef ")[0]
    check("seat_script_if_empty issues no DELETE", "DELETE" not in fn)
    check("  and only ever PATCHes", fn.count('_request(') == 1 and '"PATCH"' in fn)

    print("\n-- whitespace in the BOX counts as occupied (a decision, stated) --")
    # There is no filter that could match "whitespace only", so a box holding " "
    # simply fails the is-empty test and the machine writes nothing. The failure
    # direction is "the studio wrote nothing", never "the studio wrote over
    # somebody" — which is the whole point of the guard.
    check("the filter matches NULL and '' only, so ' ' is refused by construction",
          "script_snapshot.eq." in q and "trim" not in q and "ilike" not in q)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED: {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
