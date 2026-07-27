# Regenerate this plugin's bundled skill from the LIVE skill (single source of
# truth = .claude/skills/pp-episode-production). Run after changing the skill.
#   python pack.py
import shutil, pathlib
# 28 Jul 2026: the skill moved into this repo ("code in GitHub, media on Drive").
# SRC is now the repo skill. DST is a GITIGNORED build output — the bundle is
# regenerated on demand and is never a checked-in second copy, because that is
# exactly the fork this move removed (the old bundle drifted 7 KB behind).
SRC = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "skills" / "pp-episode-production"
DST = pathlib.Path(__file__).parent / "dist" / "skills" / "pp-episode-production"
DST.parent.mkdir(parents=True, exist_ok=True)
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("desktop.ini", "__pycache__", "*.pyc"))
n = sum(1 for _ in DST.rglob("*") if _.is_file())
print(f"packed {n} files -> {DST}")
