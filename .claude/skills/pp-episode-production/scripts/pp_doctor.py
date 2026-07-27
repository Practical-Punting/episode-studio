#!/usr/bin/env python3
"""
pp_doctor.py - Toolchain "doctor" for the Practical Punting video pipeline (Windows).

Checks (and optionally installs / path-fixes) every tool the PP episode-production
pipeline depends on:

    ffmpeg + ffprobe    Playwright + Chromium    WeasyPrint    GTK3 runtime
    Python 3.12         pymupdf (fitz)           pillow (PIL)  Poppler (pdftoppm)
    WhisperX

USAGE
    python pp_doctor.py                # check only  (default)
    python pp_doctor.py --install      # install anything missing, then re-check
    python pp_doctor.py --fix-path     # persist tool bin dirs to the USER PATH
    python pp_doctor.py --install --fix-path

On this machine the correct interpreter is:
    C:\\Users\\jlral\\AppData\\Local\\Programs\\Python\\Python312\\python.exe
(a bare `python` hits the Microsoft Store stub - never rely on it).

Exit code: 0 if all good (or after a successful install); non-zero if anything is
still missing in check mode.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys

# --------------------------------------------------------------------------- #
# Known machine locations
# --------------------------------------------------------------------------- #
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
GTK_BIN = r"C:\Program Files\GTK3-Runtime Win64\bin"
MS_PLAYWRIGHT_DIR = os.path.join(LOCALAPPDATA, "ms-playwright")
WINGET_PACKAGES = os.path.join(LOCALAPPDATA, "Microsoft", "WinGet", "Packages")
WINGET_LINKS = os.path.join(LOCALAPPDATA, "Microsoft", "WinGet", "Links")

# The interpreter running this script is the one we install pip packages into.
PYTHON = sys.executable
PYTHON_DIR = os.path.dirname(PYTHON)
PYTHON_SCRIPTS = os.path.join(PYTHON_DIR, "Scripts")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _merge_machine_user_path():
    """
    A fresh tool shell may not have the machine/user PATH merged. Recompute the
    full PATH from the registry (Machine + User) so shutil.which can find winget
    tools like ffmpeg installed after this process started.
    """
    if os.name != "nt":
        return
    try:
        ps = (
            '[System.Environment]::GetEnvironmentVariable("Path","Machine") '
            '+ ";" + '
            '[System.Environment]::GetEnvironmentVariable("Path","User")'
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30,
        )
        merged = (out.stdout or "").strip()
        if merged:
            # Prepend the registry PATH so newly-installed tools are visible.
            os.environ["Path"] = merged + os.pathsep + os.environ.get("Path", "")
    except Exception:
        pass


def _which(name):
    """shutil.which that also checks the winget Links shim dir."""
    p = shutil.which(name)
    if p:
        return p
    cand = os.path.join(WINGET_LINKS, name + ".exe")
    if os.path.isfile(cand):
        return cand
    return None


def _find_winget_ffmpeg(exe):
    """Fall back to the Gyan.FFmpeg winget install location."""
    pattern = os.path.join(WINGET_PACKAGES, "Gyan.FFmpeg*", "**", "bin", exe + ".exe")
    hits = glob.glob(pattern, recursive=True)
    return hits[0] if hits else None


def _run_version(path, args=("-version",)):
    """Return the first meaningful line of a tool's version output, or None."""
    try:
        out = subprocess.run(
            [path, *args], capture_output=True, text=True, timeout=30
        )
        text = (out.stdout or out.stderr or "").strip()
        return text.splitlines()[0].strip() if text else None
    except Exception:
        return None


def _add_gtk_dll_dir():
    """WeasyPrint needs the GTK3 bin dir on the DLL search path."""
    if os.name == "nt" and os.path.isdir(GTK_BIN):
        try:
            os.add_dll_directory(GTK_BIN)
        except Exception:
            pass
        # Also make sure it is on PATH for good measure.
        if GTK_BIN not in os.environ.get("Path", ""):
            os.environ["Path"] = GTK_BIN + os.pathsep + os.environ.get("Path", "")


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #
class Result:
    def __init__(self, name, ok, detail, install_cmd):
        self.name = name              # tool label
        self.ok = ok                  # bool
        self.detail = detail or ""    # version-or-path
        self.install_cmd = install_cmd  # list[str] or None (how to install)

    @property
    def status(self):
        return "OK" if self.ok else "MISSING"


def _safe(fn):
    """Wrap a check so one failure never crashes the rest of the run."""
    try:
        return fn()
    except Exception as e:
        # fn is expected to return a Result; if it blew up, we don't know the
        # name here, so callers pass a name via closure. Re-raise as a sentinel.
        raise e


# --------------------------------------------------------------------------- #
# Individual checks  (each returns a Result; each wrapped by run_checks)
# --------------------------------------------------------------------------- #
def check_ffmpeg():
    path = _which("ffmpeg") or _find_winget_ffmpeg("ffmpeg")
    if path:
        ver = _run_version(path) or path
        return Result("ffmpeg", True, ver, None)
    return Result("ffmpeg", False, "", ["winget", "install", "-e", "--id", "Gyan.FFmpeg"])


def check_ffprobe():
    path = _which("ffprobe") or _find_winget_ffmpeg("ffprobe")
    if path:
        ver = _run_version(path) or path
        return Result("ffprobe", True, ver, None)
    return Result("ffprobe", False, "", ["winget", "install", "-e", "--id", "Gyan.FFmpeg"])


def check_python():
    ver = sys.version.split()[0]
    ok = sys.version_info[:2] == (3, 12)
    detail = f"{ver}  ({PYTHON})"
    # Already present; nothing to install. Report only.
    return Result("Python 3.12", ok, detail if ok else f"found {ver}, want 3.12  ({PYTHON})", None)


def check_playwright():
    import importlib
    try:
        pw = importlib.import_module("playwright")
        ver = getattr(pw, "__version__", "installed")
    except Exception:
        return Result(
            "Playwright", False, "python module not importable",
            [PYTHON, "-m", "pip", "install", "playwright"],
        )
    # Confirm a chromium build exists under %LOCALAPPDATA%\ms-playwright
    chromium = glob.glob(os.path.join(MS_PLAYWRIGHT_DIR, "chromium-*"))
    if chromium:
        return Result("Playwright+Chromium", True, f"{ver}; {os.path.basename(chromium[0])}", None)
    return Result(
        "Playwright+Chromium", False, f"module {ver} but no chromium build",
        [PYTHON, "-m", "playwright", "install", "chromium"],
    )


def check_weasyprint():
    _add_gtk_dll_dir()
    import importlib
    try:
        wp = importlib.import_module("weasyprint")
        return Result("WeasyPrint", True, getattr(wp, "__version__", "installed"), None)
    except Exception as e:
        return Result(
            "WeasyPrint", False, f"import failed: {type(e).__name__}",
            [PYTHON, "-m", "pip", "install", "weasyprint"],
        )


def check_gtk3():
    if os.path.isdir(GTK_BIN):
        return Result("GTK3 runtime", True, GTK_BIN, None)
    return Result(
        "GTK3 runtime", False, "not found",
        ["winget", "install", "-e", "--id", "tschoonj.GTKForWindows"],
    )


def check_pymupdf():
    import importlib
    try:
        fitz = importlib.import_module("fitz")
        ver = getattr(fitz, "__version__", None) or getattr(fitz, "VersionBind", "installed")
        return Result("pymupdf (fitz)", True, str(ver), None)
    except Exception as e:
        return Result(
            "pymupdf (fitz)", False, f"import failed: {type(e).__name__}",
            [PYTHON, "-m", "pip", "install", "pymupdf"],
        )


def check_pillow():
    import importlib
    try:
        PIL = importlib.import_module("PIL")
        return Result("pillow (PIL)", True, getattr(PIL, "__version__", "installed"), None)
    except Exception as e:
        return Result(
            "pillow (PIL)", False, f"import failed: {type(e).__name__}",
            [PYTHON, "-m", "pip", "install", "pillow"],
        )


def check_poppler():
    path = _which("pdftoppm")
    if path:
        ver = _run_version(path, args=("-v",)) or path
        return Result("Poppler (pdftoppm)", True, ver, None)
    return Result(
        "Poppler (pdftoppm)", False, "not found",
        ["winget", "install", "-e", "--id", "oschwartz10612.Poppler"],
    )


def check_whisperx():
    import importlib
    try:
        wx = importlib.import_module("whisperx")
        return Result("WhisperX", True, getattr(wx, "__version__", "installed"), None)
    except Exception as e:
        return Result(
            "WhisperX", False, f"import failed: {type(e).__name__}",
            [PYTHON, "-m", "pip", "install", "whisperx"],
        )


CHECKS = [
    ("ffmpeg", check_ffmpeg),
    ("ffprobe", check_ffprobe),
    ("Python 3.12", check_python),
    ("Playwright+Chromium", check_playwright),
    ("WeasyPrint", check_weasyprint),
    ("GTK3 runtime", check_gtk3),
    ("pymupdf (fitz)", check_pymupdf),
    ("pillow (PIL)", check_pillow),
    ("Poppler (pdftoppm)", check_poppler),
    ("WhisperX", check_whisperx),
]


def run_checks():
    results = []
    for name, fn in CHECKS:
        try:
            results.append(fn())
        except Exception as e:
            results.append(Result(name, False, f"check error: {type(e).__name__}: {e}", None))
    return results


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def print_table(results):
    name_w = max(len("TOOL"), max(len(r.name) for r in results))
    stat_w = max(len("STATUS"), max(len(r.status) for r in results))

    header = f"{'TOOL':<{name_w}} | {'STATUS':<{stat_w}} | VERSION / PATH"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r.name:<{name_w}} | {r.status:<{stat_w}} | {r.detail}")
    print()


def print_summary(results):
    missing = [r for r in results if not r.ok]
    if not missing:
        print("ALL GOOD")
        return True
    print("MISSING:")
    for r in missing:
        cmd = " ".join(r.install_cmd) if r.install_cmd else "(no automatic installer)"
        print(f"  - {r.name}")
        print(f"      install: {cmd}")
    return False


# --------------------------------------------------------------------------- #
# --install
# --------------------------------------------------------------------------- #
def do_install(results):
    missing = [r for r in results if not r.ok and r.install_cmd]
    if not missing:
        print("Nothing to install.\n")
        return
    print(f"Installing {len(missing)} missing tool(s)...\n")
    for r in missing:
        print(f">>> {r.name}: {' '.join(r.install_cmd)}")
        try:
            proc = subprocess.run(r.install_cmd, capture_output=True, text=True, timeout=1800)
            out = (proc.stdout or "") + (proc.stderr or "")
            # Show a trimmed tail of the output so the log stays readable.
            tail = out.strip().splitlines()[-15:]
            for line in tail:
                print("    " + line)
            print(f"    (exit code {proc.returncode})\n")
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}\n")


# --------------------------------------------------------------------------- #
# --fix-path
# --------------------------------------------------------------------------- #
def do_fix_path():
    """
    Append the tool bin dirs to the USER PATH (never replace it). Uses winreg
    to read the existing user PATH and PowerShell SetEnvironmentVariable to
    persist so future shells are clean.
    """
    if os.name != "nt":
        print("--fix-path only applies to Windows.\n")
        return

    wanted = []

    ff = _which("ffmpeg") or _find_winget_ffmpeg("ffmpeg")
    if ff:
        wanted.append(os.path.dirname(ff))
    if os.path.isdir(PYTHON_DIR):
        wanted.append(PYTHON_DIR)
    if os.path.isdir(PYTHON_SCRIPTS):
        wanted.append(PYTHON_SCRIPTS)
    pop = _which("pdftoppm")
    if pop:
        wanted.append(os.path.dirname(pop))
    if os.path.isdir(WINGET_LINKS):
        wanted.append(WINGET_LINKS)
    if os.path.isdir(GTK_BIN):
        wanted.append(GTK_BIN)

    # Read current USER PATH from the registry.
    current = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            current, _ = winreg.QueryValueEx(key, "Path")
    except FileNotFoundError:
        current = ""
    except Exception as e:
        print(f"Could not read USER PATH from registry: {e}")
        current = os.environ.get("Path", "")

    existing = [p for p in current.split(os.pathsep) if p]
    existing_norm = {os.path.normcase(os.path.normpath(p)) for p in existing}

    added = []
    for d in wanted:
        norm = os.path.normcase(os.path.normpath(d))
        if norm not in existing_norm:
            existing.append(d)
            existing_norm.add(norm)
            added.append(d)

    if not added:
        print("USER PATH already contains all tool bin dirs. Nothing to add.\n")
        return

    new_path = os.pathsep.join(existing)
    # Persist via PowerShell SetEnvironmentVariable (User scope) - APPEND result.
    ps = (
        "[Environment]::SetEnvironmentVariable('Path', "
        f"{_ps_quote(new_path)}, 'User')"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=True, capture_output=True, text=True, timeout=60,
        )
        print("Added to USER PATH:")
        for d in added:
            print(f"  + {d}")
        print("\nOpen a new shell for the change to take effect.\n")
    except Exception as e:
        print(f"Failed to persist USER PATH: {e}\n")


def _ps_quote(s):
    """Single-quote a string for PowerShell (double any embedded single quotes)."""
    return "'" + s.replace("'", "''") + "'"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(
        description="Toolchain doctor for the Practical Punting video pipeline."
    )
    parser.add_argument("--install", action="store_true",
                        help="Install anything missing, then re-check.")
    parser.add_argument("--fix-path", action="store_true",
                        help="Persist tool bin dirs to the USER PATH (append-only).")
    args = parser.parse_args()

    print("=" * 60)
    print("  Practical Punting - toolchain doctor")
    print("=" * 60)
    print(f"Interpreter: {PYTHON}\n")

    _merge_machine_user_path()

    results = run_checks()
    print_table(results)
    all_good = print_summary(results)
    print()

    if args.fix_path:
        print("-" * 60)
        print("--fix-path: persisting tool bin dirs to USER PATH")
        print("-" * 60)
        do_fix_path()

    if args.install:
        print("-" * 60)
        print("--install: installing missing tools")
        print("-" * 60)
        do_install(results)
        # Re-merge PATH (winget may have added dirs) and re-check.
        _merge_machine_user_path()
        print("Re-checking after install...\n")
        results = run_checks()
        print_table(results)
        all_good = print_summary(results)
        print()

    # Exit code: 0 if all good, non-zero otherwise.
    sys.exit(0 if all_good else 1)


if __name__ == "__main__":
    main()
