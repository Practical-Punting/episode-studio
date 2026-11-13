"""The two-way finish never LOOPS a picture read from the Google Drive mount (EP56, 13 Nov 2026).

`-loop 1` re-opens the image for every frame; on the Drive mount a freshly written file blocks on that
re-open, and cut 3's first finish sat 62 minutes writing nothing (cut 2's took ~2.5). The host plate
now arrives as a clip and the chips are copied to local disk (`_local_copy`).

  (a) REAL EP56: capture the exact final ffmpeg command `finish` builds (not run) — no `-loop` input
      on G:, the corner logo IS looped (one frame was never drawn), the host plate is a .mov clip
  (b) CONTROL: the same check on cut 3's FIRST command (kept in the scratch record as JSON, or rebuilt
      here from (a) by putting the Drive PNG back) -> FAILS
  (c) _local_copy: same bytes, local path, named by content

Skips (a) and says so if EP56 is not on this machine. Run: python engine/test_twoway_finish_inputs.py
"""
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import twoway_render as tr  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def looped_inputs(cmd):
    return [cmd[k + 1] for k, x in enumerate(cmd) if x == "-i" and k >= 4 and cmd[k - 4] == "-loop"]


def on_drive(p):
    return str(p).replace("\\", "/").lower().startswith("g:/")


print("\n-- (c) _local_copy --")
with tempfile.TemporaryDirectory() as td:
    src = pathlib.Path(td) / "x.png"
    src.write_bytes(b"\x89PNG fake bytes")
    q = tr._local_copy(src)
    check(q.read_bytes() == src.read_bytes() and q != src, "same bytes, a different (local) file", q)
    check(not on_drive(q), "the copy is not on G:")

print("\n-- (d) a piece is keyed on the clip it is made from (cut 3: 43 of 44 pieces came from cut 2's cache) --")
w = pathlib.Path(tempfile.gettempdir())
seg = {"n": 28, "from_s": 350.0, "to_s": 358.0, "card": "C8"}
a = tr.piece_path(dict(seg, source_key="aaaa1111"), w)
b = tr.piece_path(dict(seg, source_key="bbbb2222"), w)
check(a != b, "CONTROL: a re-made card at the SAME length is a different piece", (a.name, b.name))
plain = tr.piece_path({"n": 3, "from_s": 10.0, "to_s": 20.0, "layout": "two-box"}, w)
check(plain.name.count("-") == 3, "a segment with no clip keeps its old name (no cache moves)", plain.name)

print("\n-- (a) REAL EP56 finish command --")
EP = pathlib.Path(r"G:\My Drive\PP Videos\PP-EP56-Class-Improvement-and-Bias-Blues-Part-3")
if not (EP / "renders/assembly-plan.json").is_file():
    print("  SKIP  EP56 not on this machine")
else:
    import twoway_assemble as ta
    cap, orig = [], tr.run

    def fake(cmd, *a, **k):
        if "-filter_complex" in cmd and "[lg]" in cmd[cmd.index("-filter_complex") + 1]:
            cap.append(list(cmd))
            return None
        return orig(cmd, *a, **k)
    tr.run = fake
    tr.assert_audio_in_step = lambda *a, **k: "skipped"
    tr.assert_logo_throughout = lambda *a, **k: "skipped"
    try:
        tr.finish(ta.build_plan(56, pathlib.Path(r"G:\My Drive\PP Videos")), EP, EP / "renders/_pieces",
                  pathlib.Path(tempfile.gettempdir()) / "never-written.mp4")
    finally:
        tr.run = orig
    cmd = cap[0]
    loops = looped_inputs(cmd)
    check(loops and not any(on_drive(p) for p in loops), "no looped input is read from G:", loops)
    check(any(p.endswith("video-logo-chip.png") for p in loops), "the corner logo is LOOPED (one frame was never drawn)")
    ins = [cmd[k + 1] for k, x in enumerate(cmd) if x == "-i"]
    check(any(p.endswith("twoway-host-BB.mov") for p in ins), "the host plate arrives as a clip")

    print("\n-- (b) CONTROL: cut 3's first command shape (the host plate PNG looped from G:) --")
    bad = list(cmd)
    k = bad.index("-filter_complex")
    bad[k:k] = ["-loop", "1", "-t", "516.5", "-i", str(EP / "overlay/export/twoway-host-BB.png")]
    check(any(on_drive(p) for p in looped_inputs(bad)), "the check FAILS on a looped Drive picture")

print()
if fails:
    print(f"FAILED {len(fails)}: {fails}")
    raise SystemExit(1)
print("ALL PASS")
