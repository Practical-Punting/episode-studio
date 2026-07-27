# Robust binary resolution for the PP pipeline on Windows. A fresh tool shell may
# have a stale PATH and bare `python`/`ffmpeg` can miss (Store stub / winget shim
# not yet on PATH). Import this and call ensure_path() at the top of any script
# that shells out to ffmpeg/ffprobe — then bare "ffmpeg" works regardless of shell.
import os, glob, shutil, sys

def _winget(pat):
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    hits = sorted(glob.glob(os.path.join(base, pat), recursive=True))
    return hits[-1] if hits else None   # newest by name sort (version suffix)

def find(name, winget_pat=None, hard=None):
    p = shutil.which(name) or shutil.which(name + ".exe")
    if p:
        return p
    if winget_pat:
        p = _winget(winget_pat)
        if p:
            return p
    for h in (hard or []):
        if os.path.isfile(h):
            return h
    return None

def ffmpeg():  return find("ffmpeg",  "Gyan.FFmpeg*/**/bin/ffmpeg.exe")
def ffprobe(): return find("ffprobe", "Gyan.FFmpeg*/**/bin/ffprobe.exe")
def pdftoppm(): return find("pdftoppm", "oschwartz10612.Poppler*/**/bin/pdftoppm.exe")

def python_exe():
    return sys.executable or find("python", hard=[
        r"C:\Users\jlral\AppData\Local\Programs\Python\Python312\python.exe"])

GTK_BIN = r"C:\Program Files\GTK3-Runtime Win64\bin"

def ensure_path():
    """Prepend the resolved tool bin dirs to this process's PATH so bare
    'ffmpeg'/'ffprobe'/'pdftoppm' subprocess calls succeed."""
    dirs = []
    for fn in (ffmpeg(), ffprobe(), pdftoppm()):
        if fn:
            dirs.append(os.path.dirname(fn))
    if dirs:
        os.environ["PATH"] = os.pathsep.join(dirs) + os.pathsep + os.environ.get("PATH", "")
    return dirs

if __name__ == "__main__":
    ensure_path()
    for n, f in [("ffmpeg", ffmpeg()), ("ffprobe", ffprobe()), ("pdftoppm", pdftoppm()),
                 ("python", python_exe()), ("gtk_bin", GTK_BIN if os.path.isdir(GTK_BIN) else None)]:
        print(f"{n:9} {f or 'NOT FOUND'}")
