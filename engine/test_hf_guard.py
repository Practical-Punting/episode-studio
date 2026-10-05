"""The Higgsfield spend guard allows what fits, refuses what would cross 110, and copes with no
ledger — proved against a FAKE Higgsfield, so nothing is ever spent.

    python engine/test_hf_guard.py

Jodie, 5 Oct 2026: Claude Code may generate PP b-roll and cover heroes without asking, up to
110 credits per episode; over that, stop and ask her — enforced in code. This suite is the
proof the code does it, and the control (run against a guard with the check removed) is the
proof the suite can fail.
"""
from __future__ import annotations

import ast
import io
import json
import pathlib
import sys
import tempfile
from contextlib import redirect_stdout

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hf_guard as G                                                 # noqa: E402

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"\n         <- {why}" if not cond and why else ""))


class FakeHF:
    """Higgsfield, faked: a balance, a fixed price per job, a log of what was created."""
    SECRET = "jodie-secret@example.invalid"

    def __init__(self, balance=500.0, price=13.5, other_spend=0.0):
        self.balance, self.price, self.other = balance, price, other_spend
        self.created, self.calls = [], []

    def __call__(self, args, timeout=180):
        self.calls.append(list(args))
        if args[:2] == ["account", "status"]:
            return {"credits": self.balance, "email": self.SECRET, "subscription_plan_type": "x"}
        if args[:2] == ["generate", "cost"]:
            return {"credits": self.price}
        if args[:2] == ["generate", "create"]:
            self.balance -= self.price + self.other   # `other` = a job on the shared account
            jid = f"job-{len(self.created) + 1}"
            self.created.append(jid)
            return {"id": jid}
        if args[:2] == ["generate", "wait"]:
            return {"id": args[2], "status": "completed"}
        raise AssertionError(f"unexpected hf call {args}")


tmp = pathlib.Path(tempfile.mkdtemp(prefix="hfguard_"))
(tmp / "PP-EP77-Test-Episode" / "docs").mkdir(parents=True)
ARGS = ["kling3_0_turbo", "--prompt", "one horse gallops"]
LEDGER = tmp / "PP-EP77-Test-Episode" / "docs" / G.LEDGER_NAME


def run(fake, label="broll:a", wait=False):
    G._run = fake
    return G.guarded_create(77, label, ARGS, pp=tmp, wait=wait)


print("\n-- 1. a job that fits is allowed, with no ledger yet --")
f = FakeHF()
check("there is no ledger to begin with", not LEDGER.exists())
e = run(f)
check("the job was created", f.created == ["job-1"], f.created)
check("the ledger now exists", LEDGER.is_file())
led = json.loads(LEDGER.read_text(encoding="utf-8"))
check("it records the REAL movement of the balance", led["jobs"][0]["charged"] == 13.5
      and led["jobs"][0]["balance_before"] == 500.0 and led["jobs"][0]["balance_after"] == 486.5,
      led["jobs"][0])
check("and the estimate beside it", led["jobs"][0]["estimate"] == 13.5)
check("and the job id the engine will download by", e["job_id"] == "job-1")

print("\n-- 2. spend accumulates, and the job that would cross 110 is REFUSED --")
for i in range(2, 9):                        # 8 jobs x 13.5 = 108.0
    run(f, f"broll:{i}")
check("eight jobs of 13.5 are allowed (108.0)", G.counted(G.load(LEDGER, 77)) == 108.0,
      G.counted(G.load(LEDGER, 77)))
before_created, before_balance = len(f.created), f.balance
try:
    run(f, "broll:ninth")
    refused = False
except G.Refused as r:
    refused, msg = True, str(r)
check("the ninth (108 + 13.5 = 121.5) is REFUSED", refused)
check("  and NOTHING was created", len(f.created) == before_created and f.balance == before_balance)
check("  and the message says the numbers and to ask Jodie",
      refused and "108" in msg and "110" in msg and "Ask Jodie" in msg, msg if refused else "")
f.price = 2.0
run(f, "cover:a")
check("a job that lands EXACTLY on 110 is allowed (108 + 2)", G.counted(G.load(LEDGER, 77)) == 110.0)

print("\n-- 3. the command line: exit codes, and no secret printed --")
G._run = f
f.price = 1.0
buf = io.StringIO()
with redirect_stdout(buf):
    code = G.main(["77", "broll:over", "--pp", str(tmp), "--", *ARGS])
out = buf.getvalue()
check("over the ceiling the CLI exits 2", code == 2, out)
check("  and says REFUSED in plain words", out.startswith("REFUSED:"), out)
check("  and never prints the account e-mail", FakeHF.SECRET not in out)
buf = io.StringIO()
with redirect_stdout(buf):
    code = G.main(["77", "--status", "--pp", str(tmp)])
check("--status reports what is left", code == 0 and "110 of 110" in buf.getvalue(), buf.getvalue())
buf = io.StringIO()
with redirect_stdout(buf):
    code = G.main(["78", "broll:x", "--pp", str(tmp), "--", *ARGS])
check("an episode with no folder is not created (exit 3)", code == 3, buf.getvalue())

print("\n-- 4. the shared account: count the LARGER of estimate and movement --")
tmp2 = pathlib.Path(tempfile.mkdtemp(prefix="hfguard2_"))
(tmp2 / "PP-EP77-Shared" / "docs").mkdir(parents=True)
f2 = FakeHF(price=10.0, other_spend=6.0)     # an IW job lands at the same moment
G._run = f2
e2 = G.guarded_create(77, "broll:shared", ARGS, pp=tmp2)
check("the balance moved 16 for a 10-credit job, and that is recorded",
      e2["charged"] == 16.0 and e2["estimate"] == 10.0, e2)
check("  the larger is counted against the ceiling", e2["counted"] == 16.0)
check("  and the gap is explained", "Inspirational Women" in e2.get("note", ""))

print("\n-- 5. the engine's own create calls go through the guard --")
src = (HERE / "providers.py").read_text(encoding="utf-8")
direct = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)
          and isinstance(n.func, ast.Attribute) and n.func.attr == "_hf"
          and len(n.args) >= 2 and all(isinstance(a, ast.Constant) for a in n.args[:2])
          and [a.value for a in n.args[:2]] == ["generate", "create"]]
check("providers.py never calls `generate create` directly", not direct,
      f"{len(direct)} direct create call(s)")
guarded = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "guarded_create"]
check("  and it calls hf_guard.guarded_create", bool(guarded))

print(f"\nhf guard: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
