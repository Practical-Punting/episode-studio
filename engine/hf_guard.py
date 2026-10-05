"""The Higgsfield spend guard — every PP generation goes through here.

    python engine/hf_guard.py <ep> <label> [--wait] -- <model> <hf create args…>
    python engine/hf_guard.py <ep> --status

Jodie's ruling, 5 Oct 2026: **Claude Code may generate Higgsfield b-roll and cover heroes for
PP WITHOUT ASKING, up to 110 CREDITS PER EPISODE, every episode. Over that, stop and ask
her.** Enforced HERE, in code, not by anybody remembering it.

WHAT IT DOES, PER JOB
  1. asks Higgsfield what the job will cost (`generate cost`, free);
  2. REFUSES — exit 2, plain words, nothing created — if this episode's spend so far plus
     that estimate would pass 110;
  3. reads the balance, creates the job, reads the balance again, and records the REAL
     credits the balance moved by, in `<episode>/docs/higgsfield-spend.json`;
  4. with --wait, waits for the job and re-reads the balance (a failed job is refunded).
The engine's own two create calls (cover heroes, b-roll) come through `guarded_create`; the
command line above is the door for a person or Claude Code. One ledger, one ceiling.

⚠️ THE BALANCE IS SHARED. The Inspirational Women line generates on the same Higgsfield
account, and the transaction log carries no job id, so "the balance moved by" can include
somebody else's job that ran at the same moment. The ledger therefore records BOTH the
estimate and the measured movement, flags a gap between them, and COUNTS the larger of the
two against the ceiling — an over-count stops PP early, an under-count would let it overspend.

🔒 NEVER PRINTS A KEY. It never reads one: the CLI holds its own login. The account-status
reply also carries an e-mail address; only `credits` is ever read out of it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CEILING = 110.0
"""Credits per PP episode, b-roll AND cover heroes together (Jodie, 5 Oct 2026). Changing it
is a ruling, not a setting — so it is a constant, and there is no override flag."""
LEDGER_NAME = "higgsfield-spend.json"
HF = pathlib.Path(os.environ.get("HF_CLI", r"C:\Users\jlral\tools\hf\hf.exe"))
PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
GAP_NOTE = 0.5      # credits: a balance movement this far from the estimate gets a note


class Refused(Exception):
    """The job would take this episode over the ceiling. Nothing was created."""


class GuardError(Exception):
    """Higgsfield could not be asked, so nothing was created."""


# ── the one door to the CLI (tests replace this) ────────────────────────────────
def _run(args: list[str], timeout: int = 180):
    r = subprocess.run([str(HF), *args, "--json"], capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        raise GuardError(f"hf {' '.join(args[:2])} exited {r.returncode}: "
                         f"{(r.stderr or r.stdout).strip()[-300:]}")
    return json.loads(r.stdout)


def balance() -> float:
    return float(_run(["account", "status"])["credits"])


def estimate(create_args: list[str]) -> float:
    return float(_run(["generate", "cost", *create_args])["credits"])


# ── the ledger ──────────────────────────────────────────────────────────────────
def ledger_path(ep_number: int, pp: pathlib.Path = PP) -> pathlib.Path:
    import ep_paths                                             # noqa: PLC0415
    d = ep_paths.episode_dir(int(ep_number), pp)
    if d is None or not pathlib.Path(d).is_dir():
        raise GuardError(f"there is no PP-EP{int(ep_number):02d} folder under {pp}, so there "
                         f"is nowhere to keep its spend ledger. Nothing was created.")
    return pathlib.Path(d) / "docs" / LEDGER_NAME


def load(path: pathlib.Path, ep_number: int) -> dict:
    if not path.is_file():
        return {"episode": f"EP{int(ep_number):02d}", "ceiling": CEILING, "jobs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def counted(ledger: dict) -> float:
    return round(sum(float(j.get("counted", 0)) for j in ledger.get("jobs", [])), 2)


def _save(path: pathlib.Path, ledger: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(body, encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    if path.read_text(encoding="utf-8") != body:
        raise GuardError(f"the spend ledger {path.name} did not read back as written.")


class _Lock:
    """One guarded job per episode at a time, so two jobs cannot both fit under the ceiling
    on the same reading of the ledger."""

    def __init__(self, path: pathlib.Path, wait_s: float = 120.0, stale_s: float = 1800.0):
        self.p, self.wait_s, self.stale_s = path.with_name(path.name + ".lock"), wait_s, stale_s

    def __enter__(self):
        self.p.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        while True:
            try:
                os.close(os.open(self.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                if time.time() - self.p.stat().st_mtime > self.stale_s:
                    self.p.unlink(missing_ok=True)
                    continue
                if time.time() - t0 > self.wait_s:
                    raise GuardError("another Higgsfield job for this episode is still being "
                                     "recorded; nothing was created. Try again in a minute.")
                time.sleep(1.0)

    def __exit__(self, *exc):
        self.p.unlink(missing_ok=True)


# ── the guarded job ─────────────────────────────────────────────────────────────
def guarded_create(ep_number: int, label: str, create_args: list[str], *,
                   pp: pathlib.Path = PP, wait: bool = False) -> dict:
    """Create ONE Higgsfield job for a PP episode if it fits under the ceiling.

    Returns the ledger entry (with `job_id`). Raises Refused — having created nothing — if it
    does not fit, and GuardError if Higgsfield cannot be asked."""
    if not create_args:
        raise GuardError("no model or prompt was given; nothing was created.")
    path = ledger_path(ep_number, pp)
    with _Lock(path):
        led = load(path, ep_number)
        est = estimate(create_args)
        so_far = counted(led)
        if so_far + est > CEILING + 1e-9:
            raise Refused(
                f"EP{int(ep_number):02d} has used {so_far:g} of its {CEILING:g} Higgsfield "
                f"credits, and '{label}' is estimated at {est:g} more ({so_far + est:g} in "
                f"all). That is over the ceiling Jodie set, so nothing was created. "
                f"Ask Jodie before going on.")
        before = balance()
        job = _run(["generate", "create", *create_args])
        job_id = job[0] if isinstance(job, list) else job.get("id")
        if isinstance(job_id, dict):
            job_id = job_id.get("id")
        after = balance()
        moved = round(before - after, 2)
        entry = {"label": label, "job_id": job_id, "model": create_args[0],
                 "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                 "estimate": est, "balance_before": before, "balance_after": after,
                 "charged": moved, "counted": round(max(moved, est), 2)}
        if abs(moved - est) > GAP_NOTE:
            entry["note"] = (f"the balance moved by {moved:g} against an estimate of {est:g}. "
                             f"The account is shared with the Inspirational Women line, so "
                             f"another job may have run at the same moment; the larger figure "
                             f"is counted against the ceiling.")
        led.setdefault("jobs", []).append(entry)
        led["ceiling"] = CEILING
        led["counted_total"] = counted(led)
        _save(path, led)
    if wait and job_id:
        res = _run(["generate", "wait", str(job_id)], timeout=1800)
        entry["status"] = (res[0] if isinstance(res, list) else res).get("status") \
            if isinstance(res, (dict, list)) and res else None
        entry["balance_after_wait"] = balance()
        entry["result"] = res
        with _Lock(path):
            led = load(path, ep_number)
            for j in led.get("jobs", []):
                if j.get("job_id") == job_id:
                    j["status"] = entry["status"]
                    j["balance_after_wait"] = entry["balance_after_wait"]
                    if entry["balance_after_wait"] > after + GAP_NOTE:
                        j["note"] = (j.get("note", "") + " The balance went back UP after "
                                     "the job finished — a refund, most likely for a failed "
                                     "job. The count is left as it was; a person decides.").strip()
            led["counted_total"] = counted(led)
            _save(path, led)
    return entry


def status(ep_number: int, pp: pathlib.Path = PP) -> str:
    path = ledger_path(ep_number, pp)
    led = load(path, ep_number)
    used = counted(led)
    return (f"EP{int(ep_number):02d}: {used:g} of {CEILING:g} Higgsfield credits counted, "
            f"{max(0.0, CEILING - used):g} left, {len(led.get('jobs', []))} job(s). "
            f"Ledger: {path}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    create_args = []
    if "--" in argv:
        i = argv.index("--")
        argv, create_args = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description="PP Higgsfield spend guard (110 credits/episode).")
    ap.add_argument("ep_number", type=int)
    ap.add_argument("label", nargs="?")
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--pp", default=str(PP))
    a = ap.parse_args(argv)
    pp = pathlib.Path(a.pp)
    try:
        if a.status:
            print(status(a.ep_number, pp))
            return 0
        if not a.label or not create_args:
            print("usage: hf_guard.py <ep> <label> [--wait] -- <model> <hf create args…>")
            return 3
        e = guarded_create(a.ep_number, a.label, create_args, pp=pp, wait=a.wait)
        print(f"created {a.label}: job {e['job_id']}, estimate {e['estimate']:g}, balance moved "
              f"{e['charged']:g}, counted {e['counted']:g}. {status(a.ep_number, pp)}")
        if e.get("note"):
            print("note: " + e["note"])
        if a.wait:
            print(json.dumps({"status": e.get("status"), "result": e.get("result")},
                             ensure_ascii=False)[:4000])
        return 0
    except Refused as r:
        print(f"REFUSED: {r}")
        return 2
    except GuardError as g:
        print(f"NOT CREATED: {g}")
        return 3


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
