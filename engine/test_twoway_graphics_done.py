"""twoway_run.graphics_done: the no-logo title and end card are part of the graphics.

    python engine/test_twoway_graphics_done.py

EP57/58/59 (14 Nov 2026): do_graphics never made ep<n>-title-nologo.mp4, graphics_done said yes,
and every cut halted on the missing clip. CONTROL: with the no-logo title missing, NOT done.
"""
import json, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import twoway_run as tr   # noqa: E402

fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


class FakeEp:
    def __init__(self, d):
        self.d, self.n = d, 99

    def p(self, rel):
        return self.d / rel


tr._card_pages = lambda ep: ["ep99-c01-x.html"]
with tempfile.TemporaryDirectory() as t:
    d = pathlib.Path(t)
    clips = d / "overlay/clips"
    clips.mkdir(parents=True)
    for stem in ("ep99-c01-x", "ep99-title", "end-card-template-nologo"):
        (clips / f"{stem}.mp4").write_bytes(b"x")
    (d / "output/run").mkdir(parents=True)
    (d / "output/run/card-timing.json").write_text(json.dumps({"at": "T1"}), encoding="utf-8")
    (d / "output/run/graphics.json").write_text(json.dumps({"card_timing": "T1"}), encoding="utf-8")
    ep = FakeEp(d)
    check("CONTROL: without ep99-title-nologo.mp4 the graphics are NOT done", not tr.graphics_done(ep))
    (clips / "ep99-title-nologo.mp4").write_bytes(b"x")
    check("with it (and the current card timing), they are done", tr.graphics_done(ep))
    (clips / "end-card-template-nologo.mp4").unlink()
    check("CONTROL: without the no-logo end card, NOT done", not tr.graphics_done(ep))
print(f"\ngraphics done: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
