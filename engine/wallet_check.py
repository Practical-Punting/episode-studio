#!/usr/bin/env python3
"""wallet_check.py — WOULD A COMMISSION BE ALLOWED TO RUN ON THIS LOGIN?

    python "C:\\Users\\jlral\\repos\\episode-studio\\engine\\wallet_check.py"

WHY THIS EXISTS. The episode engine authenticates to Claude with a LOGIN, not an
API key, and it commissions four times per episode (script, episode.json, e-book
body, YouTube copy). Cancelling the subscription that login belongs to would stop
every build at the first commission. Before changing accounts, the question worth
answering is narrow and factual:

    does the account I am about to move to report authMethod "claude.ai"
    and apiProvider "firstParty"?

Because THAT is what the gate tests. It logs `subscriptionType` and never checks
it — so "max" is not required, a first-party claude.ai login is.

🔴 IT ASKS THE REAL GATE. The verdict line at the bottom is produced by CALLING
`commission.assert_subscription_wallet` — the same function, with the same CLI
path and the same child environment production uses:

    cli        = commission.cli_path()          # env -> PATH -> npm fallback
    child_env  = dict(os.environ)               # commission.py line ~877
    runner     = subprocess.run

Nothing about the rule is re-implemented here. WALLET_OK_METHODS and
WALLET_OK_PROVIDERS are IMPORTED and only ever printed, never compared against.
This studio's recurring failure is proving something about a MODEL of the code
instead of the code; a checker that copied those tuples would keep saying PASS
long after the real gate had changed its mind.

🔒 READ-ONLY, AND DELIBERATELY DULL. It reads `claude auth status` (a local read;
no API call, no tokens spent), reads environment variables, and calls the gate.
It writes nothing, claims nothing, queues nothing, starts no engine, touches no
Supabase, and spawns no commission. Safe to run at any time, including mid-build.

🔒 NEVER PRINTS A SECRET. Environment variables are reported by NAME and
set/not-set only. No value is read, logged or displayed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import commission as com                                           # noqa: E402


def _rule(title: str) -> None:
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def _env_scope_names() -> dict:
    """Where each billing marker is set — SESSION / USER / MACHINE. Names only.

    The gate only ever sees the SESSION environment (`dict(os.environ)`), but a
    User- or Machine-level variable becomes the session's the next time a shell
    or a scheduled task starts, so a clean session with a persisted key is a
    trap that springs later. All three are reported.
    """
    out = {k: [] for k in com._BILLING_ENV_MARKERS}
    for k in com._BILLING_ENV_MARKERS:
        if os.environ.get(k):
            out[k].append("SESSION")
    try:
        import winreg
        for scope, root, path in (
            ("USER", winreg.HKEY_CURRENT_USER, r"Environment"),
            ("MACHINE", winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ):
            try:
                with winreg.OpenKey(root, path) as key:
                    i = 0
                    while True:
                        try:
                            name, _value, _t = winreg.EnumValue(key, i)
                        except OSError:
                            break
                        if name in out:
                            out[name].append(scope)   # NAME only; value ignored
                        i += 1
            except OSError:
                pass
    except ImportError:
        print("  (not Windows: only the SESSION environment was checked)")
    return out


def main() -> int:
    print("WALLET CHECK — would the episode engine be allowed to commission?")
    print("read-only: no writes, no rail, no engine, no commission, no tokens spent")

    # ── the CLI, resolved exactly as commission() resolves it ─────────────────
    _rule("1. THE CLAUDE CLI THIS MACHINE WOULD USE")
    cli = com.cli_path()
    if cli is None:
        print("  NOT FOUND (checked CLAUDE_CLI, then PATH, then the npm fallback)")
        print("\n  VERDICT: FAIL — a commission could not start at all: there is no")
        print("  CLI to ask. This is a setup problem, not an account problem.")
        return 2
    print(f"  {cli}")
    print(f"  (resolved by commission.cli_path(); CLAUDE_CLI is "
          f"{'set' if os.environ.get('CLAUDE_CLI') else 'not set'})")

    # ── who this login is ────────────────────────────────────────────────────
    _rule("2. WHO THIS MACHINE IS SIGNED IN AS")
    status, status_err = None, None
    try:
        r = subprocess.run([str(cli), "auth", "status"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=60)
        status = json.loads((r.stdout or "").strip())
    except Exception as e:                                         # noqa: BLE001
        status_err = f"{type(e).__name__}: {e}"

    if status_err or not isinstance(status, dict):
        print(f"  could not read `claude auth status` ({status_err or 'unreadable'})")
        print("  Nothing below can be reported. Are you signed in?")
    else:
        for label, key in (("logged in", "loggedIn"),
                           ("authMethod", "authMethod"),
                           ("apiProvider", "apiProvider"),
                           ("email", "email"),
                           ("orgName", "orgName"),
                           ("orgId", "orgId"),
                           ("subscriptionType", "subscriptionType")):
            print(f"  {label:18} {status.get(key)!r}")
        print()
        print(f"  For reference, the gate accepts authMethod in "
              f"{com.WALLET_OK_METHODS} and apiProvider in {com.WALLET_OK_PROVIDERS}.")
        print(f"  It does NOT test subscriptionType — {status.get('subscriptionType')!r} "
              f"is logged, never checked.")

    # ── billing env vars, names only ─────────────────────────────────────────
    _rule("3. BILLING ENVIRONMENT VARIABLES (names only — no value is ever read)")
    scopes = _env_scope_names()
    for name, where in scopes.items():
        print(f"  {name:22} {'SET in ' + ', '.join(where) if where else 'not set'}")
    if any(scopes.values()):
        print()
        print("  ⚠️ The gate REFUSES when either of these is visible to the child,")
        print("     because the CLI would then bill an API wallet instead of the")
        print("     subscription. A key does not rescue the engine — it stops it.")

    # ── the verdict, from the REAL gate ──────────────────────────────────────
    _rule("4. THE VERDICT — produced by calling the real gate, not by copying it")
    print("  calling commission.assert_subscription_wallet(cli, dict(os.environ), "
          "runner=subprocess.run)")
    print("  — the same function, CLI and environment a commission uses.\n")
    logged: list[str] = []
    try:
        com.assert_subscription_wallet(
            cli, dict(os.environ), runner=subprocess.run, log=logged.append)
    except com.CommissionHalt as h:
        print("  RESULT: **FAIL** — a commission would HALT on this login.\n")
        print("  What the gate says, verbatim:")
        for line in str(h).splitlines():
            print(f"    {line}")
        detail = getattr(h, "detail", None)
        if detail:
            print("\n  Its detail line, verbatim:")
            for line in str(detail).splitlines():
                print(f"    {line}")
        print("\n  Every episode would stop at its first commission, before writing")
        print("  or spending anything.")
        return 1
    except Exception as e:                                         # noqa: BLE001
        print(f"  RESULT: **FAIL** — the gate could not complete: "
              f"{type(e).__name__}: {e}")
        print("  Treat an unknown wallet exactly as a failing one.")
        return 1

    for line in logged:
        print(f"  gate log: {line.strip()}")
    print()
    print("  RESULT: **PASS** — a commission would be allowed to run on this login.")
    print("  All four per episode (script, episode.json, e-book body, YouTube copy)")
    print("  would proceed, costing rate limits rather than money.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
