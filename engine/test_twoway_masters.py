"""twoway_masters: whole-frame cuts, joins inside pauses, and EP56's two masters rebuilt exactly.

    python engine/test_twoway_masters.py            fast checks only
    python engine/test_twoway_masters.py --slow     + rebuild EP56's two masters (re-encodes, ~minutes)

REAL DATA (--slow): EP56's masters were made by hand on 12–13 Nov (`masters-EP56.json`):
Steve kept frames 89–6081 → 5992 frames; Gordon kept 75–1400 + 2022–end with a 6-frame
dissolve → 8445 frames. The tool, given the same ranges, must produce the same frame
counts, picture and sound within a frame of each other, into a TEMP folder (EP56's
renders are never touched).
CONTROLS: overlapping ranges, a range shorter than the dissolve, and an existing master
without --force must all be refused.
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_masters as tm    # noqa: E402
import ep_paths                # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def refused(label, fn, needle):
    try:
        fn()
        check(label, False, "not refused")
    except tm.MasterError as e:
        check(label, needle in str(e), str(e)[:100])


print("-- fast --")
check("seconds become whole frames at 25 fps",
      tm.frames_for([[3.56, 243.24]], 25, 7000) == [(89, 6081)])
check("'end' means the last frame", tm.frames_for([[80.88, "end"]], 25, 9000) == [(2022, 9000)])
refused("CONTROL: overlapping ranges are refused",
        lambda: tm.frames_for([[0, 10], [9, 20]], 25, 1000), "overlap")
refused("CONTROL: a range shorter than the dissolve is refused",
        lambda: tm.frames_for([[0, 0.1]], 25, 1000), "shorter")
g1 = tm.filter_graph([(89, 6081)], 25)
check("one range: no dissolve, picture passed through", "xfade" not in g1 and "[v0]null[v]" in g1)
g2 = tm.filter_graph([(75, 1400), (2022, 9000)], 25)
check("two ranges: one dissolve, offset = first piece length − half the dissolve",
      g2.count("xfade") == 1 and "offset=52.88" in g2, g2[g2.find("xfade"):g2.find("xfade") + 60])
check("two ranges: the picture pieces overlap the join by half the dissolve each side",
      "trim=start_frame=75:end_frame=1403" in g2 and "trim=start_frame=2019:end_frame=9000" in g2)
g3 = tm.filter_graph([(0, 500), (600, 1000), (1100, 2000)], 25)
check("three ranges: two dissolves, the second offset counts BOTH earlier pieces",
      g3.count("xfade") == 2 and "offset=35.88" in g3)

sand = pathlib.Path(tempfile.mkdtemp(prefix="masters_"))
(sand / "BM-master.mp4").write_bytes(b"x")
ep56 = ep_paths.episode_dir(56, PP)
refused("CONTROL: an existing master is not overwritten without --force",
        lambda: tm.make(56, "BM", [[3.56, 243.24]], ep56 / "renders/PP-EP56-BM-full.mp4",
                        out_dir=sand), "already exists")
(sand / "BM-master.mp4").unlink()

if "--slow" in sys.argv:
    print("\n-- slow: EP56's masters rebuilt into a temp folder --")
    shipped = json.loads((ep56 / "renders/masters-EP56.json").read_text(encoding="utf-8"))
    bm = tm.make(56, "BM", [[3.56, 243.24]], ep56 / "renders/PP-EP56-BM-full.mp4", out_dir=sand)
    check("Steve's master: the same frame count as the one that shipped",
          bm["video_frames"] == shipped["BM"]["video_frames"],
          f"{bm['video_frames']} vs {shipped['BM']['video_frames']}")
    bb = tm.make(56, "BB", [[3.0, 56.0], [80.88, "end"]], ep56 / "renders/PP-EP56-BB-full.mp4",
                 out_dir=sand)
    check("Gordon's master (cut 3): the same frame count as the one that shipped",
          bb["video_frames"] == shipped["BB"]["video_frames"],
          f"{bb['video_frames']} vs {shipped['BB']['video_frames']}")
    check("Gordon's master: picture and sound agree within a frame",
          abs(bb["audio_s"] - bb["video_frames"] / bb["fps"]) <= 1 / bb["fps"],
          f"{bb['audio_s']} s audio, {bb['video_frames'] / bb['fps']:.3f} s picture")
    check("one join WAV for Gordon's one join", len(bb["join_wavs"]) == 1, str(bb["join_wavs"]))
    check("EP56's own renders folder untouched (masters-EP56.json unchanged)",
          json.loads((ep56 / "renders/masters-EP56.json").read_text(encoding="utf-8")) == shipped)

shutil.rmtree(sand, ignore_errors=True)
print(f"\nmasters: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
