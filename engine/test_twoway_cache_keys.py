"""Pieces cut from the masters are keyed on the masters' CONTENT (EP58, 14 Nov 2026).

    python engine/test_twoway_cache_keys.py

Steve's master was re-spliced under the same name; the timeline came out the same; the render
served every sound piece (and the whole speech track) from the old build's cache, so the fixed
master was never heard. Now: same name + same timeline + DIFFERENT content = a different key for
the face pieces (`masters_key`) and for the speech track (`speech_path`). CONTROL: unchanged
content keeps the same key (nothing re-renders for nothing).
"""
import os
import pathlib
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_assemble as tas  # noqa: E402
import twoway_render as tr  # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


d = pathlib.Path(tempfile.mkdtemp(prefix="cache_keys_"))
bb, bm = d / "BB-master.mp4", d / "BM-master.mp4"
bb.write_bytes(b"gordon" * 1000)
bm.write_bytes(b"steve-old" * 1000)
tl = [{"speaker": "BB", "source": str(bb), "in_s": 1.0, "from_s": 0.0, "to_s": 5.0},
      {"speaker": "BM", "source": str(bm), "in_s": 2.0, "from_s": 5.0, "to_s": 9.0}]
k1, s1 = tas.masters_key(tl), tr.speech_path(d, tl)
check("CONTROL: the same masters and timeline give the same keys",
      tas.masters_key(tl) == k1 and tr.speech_path(d, tl) == s1)
time.sleep(0.05)
bm.write_bytes(b"steve-new" * 1000)              # re-spliced: same name, same size, new content
os.utime(bm, None)
check("a master re-made under the SAME NAME changes the face-piece key", tas.masters_key(tl) != k1)
check("... and the speech track's name", tr.speech_path(d, tl) != s1)
tl2 = [dict(tl[0], in_s=1.04), tl[1]]
check("a cut moved inside a master changes the key too", tas.masters_key(tl2) != tas.masters_key(tl))

print(f"\ncache keys: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
