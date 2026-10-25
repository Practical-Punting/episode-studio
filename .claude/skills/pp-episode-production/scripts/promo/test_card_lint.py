#!/usr/bin/env python3
"""test_card_lint.py — the card lint's own controls: one page per rule, each with exactly that fault (must be CAUGHT),
and one clean page (must PASS). Optionally also lint a real set of cards, which must be clean.

    python test_card_lint.py [real_cards_dir]
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import card_lint as cl  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass
ANIM = HERE.parent.parent / "assets" / "pp-anim.js"


def page(body, spec, alpha=False):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0}}'
            f'body{{width:1920px;height:1080px;position:relative;background:{"transparent" if alpha else "#1E1F22"};color:#fff;font-family:Roboto}}'
            f'.abs{{position:absolute}}.r9{{font-family:Raleway;font-weight:900}}.lnum{{font-variant-numeric:lining-nums}}'
            f'.small{{font-size:18px;line-height:1.34;width:400px}}</style><script src="pp-anim.js"></script></head>'
            f'<body>{body}<script>ppInit({json.dumps(spec)});</script></body></html>')


def A(sel, kf, delay, dur=300):
    return {"sel": sel, "kf": kf, "opts": {"delay": delay, "duration": dur}}


CASES = {
    "R1": page('<div id="x" class="abs" style="left:100px;top:100px">hello</div>',
               [A("#x", [{"opacity": 0}, {"opacity": 1}], 0), A("#x", [{"opacity": 1}, {"opacity": 0}], 2000)]),
    "R2": page('<div id="bk" class="abs" style="left:100px;top:100px;width:200px;height:200px;transform-style:preserve-3d">'
               '<div style="transform:rotateY(30deg);width:200px;height:200px;background:#fff"></div></div>',
               [A("#bk", [{"opacity": 0}, {"opacity": 1}], 0)]),
    "R3": page('<div class="abs r9" style="left:100px;top:100px;font-size:80px">$9.50</div>', [A("body", [{"opacity": 1}, {"opacity": 1}], 0)]),
    "R4": page('<div class="abs r9 lnum" style="left:100px;top:900px;font-size:40px">Too low</div>', [A("body", [{"opacity": 1}, {"opacity": 1}], 0)]),
    "R5": page('<div class="abs small" style="left:100px;top:100px">' + "Hypothetical returns, not actual member bets. " * 8 + "</div>",
               [A("body", [{"opacity": 1}, {"opacity": 1}], 0)]),
    "R6": page('<div class="abs r9 lnum" style="left:1800px;top:100px;font-size:80px;white-space:nowrap">$106.50</div>',
               [A("body", [{"opacity": 1}, {"opacity": 1}], 0)]),
    "clean": page('<div id="x" class="abs r9 lnum" style="left:100px;top:100px;font-size:80px">$9.50</div>'
                  '<div class="abs small" style="left:100px;top:1000px">Short small print.</div>',
                  [A("#x", [{"opacity": 0}, {"opacity": 1}], 0)]),
    "clean-alpha-low": page('<div class="abs r9 lnum" style="left:100px;top:900px;font-size:40px">Lower third 1995</div>',
                            [A("body", [{"opacity": 1}, {"opacity": 1}], 0)], alpha=True),
}

work = Path(tempfile.mkdtemp(prefix="card-lint-controls-"))
shutil.copyfile(ANIM, work / "pp-anim.js")
for k, html in CASES.items():
    (work / f"{k}.html").write_text(html, encoding="utf-8")
res = cl.lint(work, [f"{k}.html" for k in CASES])
bad = 0
for k in CASES:
    got = res.get(f"{k}.html", [])
    if k.startswith("clean"):
        ok = not got
        print(f"{'ok  ' if ok else 'FAIL'} {k}: {'passes clean' if ok else got}")
    else:
        ok = any(x.startswith(k) for x in got) and all(x.startswith(k) for x in got)
        print(f"{'ok  ' if ok else 'FAIL'} {k}: {got[0] if got else 'NOT CAUGHT'}")
    bad += not ok
if len(sys.argv) > 1:
    real = cl.lint(Path(sys.argv[1]))
    print(cl.report(real))
    bad += bool(real)
print(f"\n{'ALL CONTROLS BEHAVE' if not bad else str(bad) + ' WRONG'}")
sys.exit(1 if bad else 0)
