#!/usr/bin/env python3
"""OUR COPY OF render_lock.py MUST BE THE OTHER LINE'S COPY, BYTE FOR BYTE.

    python engine/test_render_lock_copy.py

The Inspirational Women line and this one share a render lock, and the contract is
the lock file path, the atomic `O_EXCL` create and the `.beat` sidecar. Their
instruction was *"copy it verbatim, don't edit it, and if it ever changes both
copies change in the same sitting."*

🔴 "IN THE SAME SITTING" IS A HOPE, NOT A RULE — IT IS A LIST SOMEBODY MAINTAINS,
AND CLAUDE.md §7 SAYS THAT IS ALREADY BROKEN, WE HAVE SIMPLY NOT MET THE MISSING
ITEM YET. So drift FAILS here instead of being remembered. Jodie, 30 Aug 2026:
*"reading G: at test time is free; importing from it at engine time is not."*

⚠️ WHY NOT JUST IMPORT IT FROM G: AND HAVE ONE COPY? Because the engine would then
depend on Google Drive at the one moment it is already under memory pressure.
`supervisor.py` refuses to start when Drive is not mounted — it did so four times
after the 23 Aug reboot — and the stale-code guard watches the MTIME of every `.py`
the interpreter imported, so a Drive file whose mtime moves on sync would restart a
running engine at a moment nobody chose (CLAUDE.md §9b). Two copies plus this test
is the cheaper failure.

📌 The dead-pid reclaim discussed on 30 Aug is DELIBERATELY NOT HERE. Jodie ruled it
belongs in the shared module and is therefore a conversation with the other line,
not a local edit: *"I would rather pay [the 15-minute cost] than have two copies of
a shared module that disagree."* If this file ever starts allowing a difference,
that ruling has been quietly reversed.

Touches nothing but two files on disk and a throwaway temp directory.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                  # noqa: BLE001
        pass

import render_lock                                                    # noqa: E402

OURS = HERE / "render_lock.py"
THEIRS = Path(os.environ.get(
    "IW_RENDER_LOCK",
    r"G:\My Drive\Inspirational Women\IW workflow\render_lock.py"))

PASS, FAIL = [], []


def case(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'ok  ' if ok else '!!  '}{name}")
    if not ok and detail:
        print(f"      {detail}")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── 1. THE COMPARISON ───────────────────────────────────────────────────────
case("our copy is where the engine imports it from", OURS.is_file(), str(OURS))
print(f"      ours   {sha(OURS)}  ({OURS.stat().st_size:,} bytes)")

if not THEIRS.is_file():
    # A LOUD SKIP, NOT A QUIET ONE. A guard that cannot run is a guard that is
    # switched off, so it has to say exactly what it did not check.
    print(f"\n  --   NOT COMPARED: {THEIRS} is not readable (Drive not mounted?).\n"
          f"       THE TWO COPIES HAVE NOT BEEN CHECKED AGAINST EACH OTHER THIS RUN.\n"
          f"       Everything below tests OUR copy only.\n")
else:
    print(f"      theirs {sha(THEIRS)}  ({THEIRS.stat().st_size:,} bytes)")
    same = OURS.read_bytes() == THEIRS.read_bytes()
    detail = ""
    if not same:
        diff = list(difflib.unified_diff(
            THEIRS.read_text(encoding="utf-8", errors="replace").splitlines(),
            OURS.read_text(encoding="utf-8", errors="replace").splitlines(),
            fromfile="IW (G:)", tofile="PP (repo)", lineterm="", n=1))
        detail = ("THE TWO COPIES OF THE SHARED MODULE HAVE DIVERGED. Both change in "
                  "the same sitting or neither changes.\n      "
                  + "\n      ".join(diff[:40]))
    case("🔴 our copy is byte-identical to the other line's", same, detail)

# ── 2. OUR COPY WORKS, EVEN WITH DRIVE OFFLINE ──────────────────────────────
# The comparison above can be skipped; this cannot. A locally corrupted copy fails
# here whether or not G: is reachable.
buf = io.StringIO()
with redirect_stdout(buf):
    rc = render_lock._selftest()
out = buf.getvalue()
n_pass = out.count("PASS ")
print(f"\n-- the module's own selftest, run in process: {n_pass} checks --")
for line in out.strip().splitlines():
    print(f"   {line.strip()}")
case("the module's own selftest passes", rc == 0 and "FAIL" not in out, out)
case("  …and it really ran its checks (not an empty pass)", n_pass >= 7, out)

# ── 3. THE SHARED CONTRACT, ASSERTED AS BEHAVIOUR RATHER THAN AS TEXT ───────
print("\n-- the four things the other line named as the contract --")
keep = {k: os.environ.get(k) for k in ("EQUEST_RENDER_LOCK", "LOCALAPPDATA")}
try:
    os.environ.pop("EQUEST_RENDER_LOCK", None)
    os.environ["LOCALAPPDATA"] = r"X:\fake-local"
    default = render_lock.lock_path()
    case("the default lock path is <LOCALAPPDATA>/equest-render/render.lock",
         Path(default) == Path(r"X:\fake-local") / "equest-render" / "render.lock",
         default)
    os.environ["EQUEST_RENDER_LOCK"] = r"X:\override\other.lock"
    case("  …and $EQUEST_RENDER_LOCK overrides it",
         Path(render_lock.lock_path()) == Path(r"X:\override\other.lock"),
         render_lock.lock_path())
finally:
    for k, v in keep.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

case("the liveness signal is a .beat SIDECAR, never the lock file itself",
     render_lock._beat_path("/tmp/x.lock") == "/tmp/x.lock.beat",
     render_lock._beat_path("/tmp/x.lock"))

TREE = ast.parse(OURS.read_text(encoding="utf-8"))


def fn(name):
    for n in ast.walk(TREE):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name} is not in render_lock.py")


flags = [n for n in ast.walk(fn("_try_create"))
         if isinstance(n, ast.Attribute) and n.attr in ("O_CREAT", "O_EXCL")]
case("the create is atomic — O_CREAT | O_EXCL, not a check-then-write",
     len({f.attr for f in flags}) == 2, str([f.attr for f in flags]))

# ── 4. NOTHING ON OUR SIDE STEALS, KILLS OR FORCES IT ──────────────────────
print("\n-- and PP never takes a lock it was not given --")
ENG = ast.parse((HERE / "engine.py").read_text(encoding="utf-8"))


def eng_fn(name):
    for n in ast.walk(ENG):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name} is not in engine.py")


held = eng_fn("render_lock_held")
calls = set()
for n in ast.walk(held):
    if isinstance(n, ast.Call):
        f = n.func
        if isinstance(f, ast.Attribute):
            base = f.value.id if isinstance(f.value, ast.Name) else "?"
            calls.add(f"{base}.{f.attr}")
        elif isinstance(f, ast.Name):
            calls.add(f.id)
# ASKED OF THE CALLS, NOT OF A GREP — this function's own prose says "IT NEVER
# STEALS", and a text search would happily match that sentence (CLAUDE.md §1a).
banned = {c for c in calls
          if c.split(".")[-1] in ("remove", "unlink", "rmtree", "kill", "terminate",
                                  "_try_create", "release")}
case("🔴 the engine's holder never removes, forces or releases another's lock",
     not banned, f"it calls {sorted(banned)}")
case("  …it takes the lock through the module's own context manager",
     "render_lock.hold" in calls, sorted(calls))
case("  …and it reads the holder through the API, never by parsing the message",
     "render_lock.read_holder" in calls, sorted(calls))

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print(f"  FAILED: {f}")
sys.exit(1 if FAIL else 0)
