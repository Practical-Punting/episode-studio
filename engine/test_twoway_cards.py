"""twoway_cards.prove(): a no-logo clip is accepted only if the logo, and only the logo, went.

Built to ATTACK the check (CLAUDE.md 4c), with synthetic clips — a grey card, and a white
214x65 "logo" box in the bottom-right corner where every PP card keeps it:

  · logo hidden properly              -> accepted
  · the hide hid nothing (identical)  -> HALT   (the failure that looks like success)
  · something ELSE moved too          -> HALT   (the layout changed)
  · the change is outside the corner  -> HALT
  · a page with no logo element       -> HALT   (nothing to hide, nothing to prove)

FAIL-FIRST: CARDS=<a copy of twoway_cards.py whose prove() just returns> -> red.

Run: python engine/test_twoway_cards.py
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
path = os.environ.get("CARDS") or str(HERE / "twoway_cards.py")
spec = importlib.util.spec_from_file_location("tcards", path)
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)
fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


def clip(out, boxes):
    vf = ",".join(f"drawbox=x={x}:y={y}:w={w}:h={h}:color={c}:t=fill"
                  for x, y, w, h, c in boxes) or "null"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=0x404040:s=1920x1080:r=30:d=1", "-vf", vf,
                    "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv444p", str(out)],
                   check=True)


LOGO = (1596, 959, 214, 65, "white")
TEXT = (300, 300, 900, 120, "0xE87722")


def outcome(w_boxes, n_boxes):
    with tempfile.TemporaryDirectory() as td:
        w, n = pathlib.Path(td) / "w.mp4", pathlib.Path(td) / "n.mp4"
        clip(w, w_boxes)
        clip(n, n_boxes)
        try:
            return "ok", tc.prove(w, n)
        except tc.Halt as e:
            return "halt", str(e)


r = outcome([TEXT, LOGO], [TEXT])
check(r[0] == "ok", "the logo hidden and nothing else changed -> accepted", r[1][:70])
r = outcome([TEXT, LOGO], [TEXT, LOGO])
check(r[0] == "halt", "the hide hid nothing (frames identical) -> HALT", r[1][:70])
r = outcome([TEXT, LOGO], [(300, 330, 900, 120, "0xE87722")])
check(r[0] == "halt", "the logo went AND the text moved -> HALT", r[1][:70])
r = outcome([TEXT, (200, 900, 214, 65, "white")], [TEXT])
check(r[0] == "halt", "a logo-sized change OUTSIDE the corner -> HALT", r[1][:70])

with tempfile.TemporaryDirectory() as td:
    pg = pathlib.Path(td) / "card.html"
    pg.write_text("<html><head></head><body><div>no mark</div></body></html>",
                  encoding="utf-8")
    try:
        tc.nologo_copy(pg, "_nologo_card.html")
        check(False, "a page with no logo element -> HALT")
    except tc.Halt:
        check(True, "a page with no logo element -> HALT")
    pg.write_text('<html><head></head><body><img id="logo"></body></html>', encoding="utf-8")
    cp = tc.nologo_copy(pg, "_nologo_card.html")
    txt = cp.read_text(encoding="utf-8")
    check(tc.HIDE in txt and txt.index(tc.HIDE) < txt.index("</head>"),
          "the hide rule is injected into the copy's head")
    check(tc.HIDE not in pg.read_text(encoding="utf-8"),
          "and the page itself is never edited")

print(f"\ntwo-way cards: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
