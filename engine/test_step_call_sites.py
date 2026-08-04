#!/usr/bin/env python3
"""No step may reference a name the engine has not bound. And the steps must RUN.

🔴 THE FAULT THIS EXISTS TO STOP — EP15, 3 August 2026, a LIVE BUILD KILLED.
`step_audit_inputs` called `providers.assert_standing_assets()`. engine.py imports
NAMES from providers (`from providers import EngineFlag, ...`) and never the module,
so `providers` was unbound and the line was a guaranteed NameError the moment the step
ran for real. EP15 retried it three times and stopped.

**And `test_bundle_a.py` was green the whole time — because it never mentioned
`assert_standing_assets` at all.** Nine cases passed, about the midroll chip, the
credit ceiling, the copy button and the title preview. The round was reported as proven
on the strength of a number that was measuring something else entirely.

> ## A TEST THAT PROVES A FUNCTION WORKS IS NOT A TEST THAT PROVES THE ENGINE CAN CALL IT.
> And a green suite that never names the thing you changed is not evidence about it.

This closes the CLASS, not the instance:
  1. STATICALLY — every function in engine.py is walked for globals it references, and
     each must be bound in the real module namespace. That covers every step and every
     call site Bundle A and Bundle D added, not just the one that broke.
  2. DYNAMICALLY — `step_audit_inputs` is driven through the REAL dispatch with the
     REAL imports, and must actually reach the standing-asset assertion.

Nothing here touches the live rail, the network, or a running engine.
"""
import ast
import builtins
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine                                                          # noqa: E402
import providers                                                       # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
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


# --------------------------------------------------------------- the checker --
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _shallow(node):
    """Descendants of `node` WITHOUT descending into a nested scope's body.

    ⚠️ The first version of this walked with ast.walk() and had no scope chain at all.
    It reported eight false positives immediately: `before(x, y)` nested inside
    check_locked_order (its parameters looked unbound to the outer scope) and `pos(i)`
    reading `cols` from its enclosing function (a closure looked like a global).
    A checker that cries wolf is a checker someone turns off — the same lesson the
    hard-coded-path lint learned this morning."""
    for c in ast.iter_child_nodes(node):
        yield c
        if not isinstance(c, (*SCOPES, ast.ClassDef)):
            yield from _shallow(c)


def _scope_bound(node):
    """Names bound in THIS scope only: its args, and what its own body binds."""
    out = set()
    if isinstance(node, SCOPES):
        a = node.args
        for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs):
            out.add(arg.arg)
        if a.vararg:
            out.add(a.vararg.arg)
        if a.kwarg:
            out.add(a.kwarg.arg)
    for n in _shallow(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names:
                out.add((al.asname or al.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
    return out


def _label(node):
    return getattr(node, "name", "<lambda>")


def _check_scope(node, visible, bad, owner):
    vis = visible | _scope_bound(node)
    for n in _shallow(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in vis:
            bad.append((owner, n.id, n.lineno))
        elif isinstance(n, ast.ClassDef):
            _check_scope(n, vis, bad, f"{owner}.{n.name}" if owner else n.name)
        elif isinstance(n, SCOPES):
            _check_scope(n, vis, bad,
                         f"{owner} -> {_label(n)}" if owner else _label(n))


def undefined_globals(src: str, namespace) -> list:
    """(where, name, line) for every name used that no enclosing scope binds.

    Scope-aware: a closure reading an enclosing function's local is CORRECT and must
    not be reported, or the check is noise."""
    tree = ast.parse(src)
    module = (set(dir(namespace)) | set(dir(builtins))
              | {"__file__", "__name__", "__doc__"})
    bad = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (*SCOPES, ast.ClassDef)):
            _check_scope(node, module, bad, _label(node))
    return bad


# ------------------------------------------------------------------- 1 static --
def _engine_has_no_unbound_globals():
    src = (HERE / "engine.py").read_text(encoding="utf-8")
    bad = undefined_globals(src, engine)
    assert not bad, (
        "engine.py references names it never bound — each is a NameError waiting for "
        "the first real run of that path:\n      "
        + "\n      ".join(f"engine.py:{ln}  {fn}() -> {nm!r}" for fn, nm, ln in bad))


case("engine.py: no function references an unbound global",
     _engine_has_no_unbound_globals)


def _providers_has_no_unbound_globals():
    src = (HERE / "providers.py").read_text(encoding="utf-8")
    bad = undefined_globals(src, providers)
    assert not bad, (
        "providers.py references names it never bound:\n      "
        + "\n      ".join(f"providers.py:{ln}  {fn}() -> {nm!r}" for fn, nm, ln in bad))


case("providers.py: no function references an unbound global",
     _providers_has_no_unbound_globals)


def _the_checker_catches_the_real_bug():
    """A checker that cannot fail is decoration. Feed it EP15's exact line."""
    broken = ("import os\n"
              "def step_audit_inputs(ctx):\n"
              "    return providers.assert_standing_assets()\n")

    class NS:                       # a namespace WITHOUT `providers`, as engine.py was
        pass

    bad = undefined_globals(broken, NS())
    assert any(nm == "providers" for _, nm, _ in bad), (
        "the checker does NOT catch `providers.assert_standing_assets()` with providers "
        "unbound — which is the exact line that killed EP15's build")
    # The shapes that DID false-positive on the first version — all legal Python.
    ok = ("def step(ctx):\n"
          "    x = [i for i in range(3)]\n"
          "    cols = 3\n"
          "    def pos(i):\n"                      # closure over an enclosing local
          "        return i % cols\n"
          "    def before(a, b):\n"                # nested function's own parameters
          "        return a < b\n"
          "    f = lambda q: q + cols\n"           # lambda parameter
          "    try:\n        pass\n"
          "    except ValueError as e:\n        print(e, x, pos(1), before(1, 2), f(2))\n")
    noise = undefined_globals(ok, NS())
    assert not noise, (
        "the checker false-positives on legal code — closures, nested-function "
        f"parameters, lambdas or except-handlers:\n      {noise}")


case("the checker catches EP15's exact line, and no false positives",
     _the_checker_catches_the_real_bug)


# ------------------------------------------------------------------ 2 dynamic --
def _audit_inputs_really_reaches_the_assertion():
    """Drive the REAL step through the REAL dispatch. Static analysis proves the name
    resolves; only running it proves the step reaches the call at all."""
    called = {"n": 0}
    real = engine.assert_standing_assets

    def spy():
        called["n"] += 1
        return real()

    class Ctx:
        def __init__(self):
            self.ep = {"id": "x", "ep_number": 15, "script_doc_url": "d",
                       "script_approved_at": "2026-08-03T00:00:00+00:00",
                       "script_read": True}
            self.state = {}
            self.provider = self
            # ⚠️ THE REAL Ctx CARRIES THIS AND THE STUB DID NOT, so the E26 config
            # pre-flight added on 4 Aug 2026 hit an AttributeError the first time it
            # ran through real dispatch — caught HERE, by this case, before it reached
            # an episode. The stub must look like the real thing, not like the minimum
            # that made yesterday's step pass; the alternative was a `getattr` default
            # in engine.py, which hides the contract instead of stating it.
            self.mock = True                    # skips the pre-flight's Drive lookups

        def audit_inputs(self, ep):
            return {"folder": "test"}

        def ep_set(self, patch):
            pass

        def save(self):
            pass

    engine.assert_standing_assets = spy
    prev_gate = engine.assert_script_gate
    engine.assert_script_gate = lambda ep: None
    prev_log = engine.log
    engine.log = lambda *a, **k: None
    try:
        engine.step_audit_inputs(Ctx())
    except NameError as e:
        raise AssertionError(
            f"step_audit_inputs raised a NameError through the real dispatch: {e}. "
            f"This is EP15's fault exactly.")
    finally:
        engine.assert_standing_assets = real
        engine.assert_script_gate = prev_gate
        engine.log = prev_log

    assert called["n"] == 1, (
        f"step_audit_inputs did NOT reach the standing-asset assertion "
        f"(called {called['n']} times). Bundle A item 2 is not wired in.")


case("step_audit_inputs runs through real dispatch and reaches the assertion",
     _audit_inputs_really_reaches_the_assertion)


def _every_step_in_the_table_exists_and_is_callable():
    """The dispatch table must not name a step that isn't there."""
    missing = []
    for name in dir(engine):
        if name.startswith("step_") and not callable(getattr(engine, name)):
            missing.append(name)
    assert not missing, f"not callable: {missing}"
    steps = [n for n in dir(engine) if n.startswith("step_")]
    assert len(steps) >= 10, f"only {len(steps)} steps found — is this the right module?"


case("every step_* in engine.py exists and is callable",
     _every_step_in_the_table_exists_and_is_callable)

print(f"\nstep call sites: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
