#!/usr/bin/env python3
"""fbx_locked.py — run one FBX build step under the shared PP/IW render lock.

    python fbx_locked.py "<job label>" <script.py> [args ...]

The laptop is shared with the Inspirational Women line; only one CPU-heavy render may run
at a time. This holds the lock as "PP" (waiting, and saying so, if IW has it), runs the
step as a child process, and releases the lock whatever happens. It never steals a lock.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "engine"))
import render_lock  # noqa: E402

if len(sys.argv) < 3:
    sys.exit(__doc__)
label, cmd = sys.argv[1], sys.argv[2:]
with render_lock.hold("PP", label):
    rc = subprocess.run([sys.executable] + cmd).returncode
sys.exit(rc)
