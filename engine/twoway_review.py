#!/usr/bin/env python3
"""twoway_review.py — the review pages Jodie opens: b-roll + covers, and each cut.

    python engine/twoway_review.py broll 57 [58 59]     one page for one or several episodes
    python engine/twoway_review.py cut 57 [--cut K]

Both are plain local HTML files (no server, no account) that open by double-click.

🔴 B-ROLL AND COVERS AT FULL SIZE, EVERY ONE (EP56, 11–12 Nov 2026). Jodie approved six clips
and a cover at Higgsfield's review size; at full size all three racing clips and the cover
carried saddlecloth NUMBERS. So each candidate plays at its OWN pixel size (the row scrolls
sideways rather than shrinking it), with a one-frame-a-second contact sheet beneath, made
from the full-size file. Each has the line it is for and a tick box. "Copy my picks" puts
ONE short line on the clipboard to paste back — e.g. `EP57: C1 C3 C4 · cover B` — which
`twoway_run.py --verdict … broll_cover approved "<that line>"` records.
And she could not FIND the clips on EP56 (a path in a .md): this is one file, one click.

🔴 A CUT'S PAGE IS THE WHOLE WATCH IN ONE PLACE (EP56 recommendation 3): the video, what
changed since the last cut (her numbered list, each with its status), the midroll WAV and
the join WAVs, the contact sheets, the fresh-eyes report, the gates still open — and a
numbered notes box with the same copy button, so her notes come back numbered.
It never ticks anything. It shows.
"""
from __future__ import annotations

import html
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
E = html.escape

CSS = """
:root{--ink:#1d1a17;--muted:#6c645c;--paper:#faf7f2;--card:#fff;--line:#e6e0d8;--accent:#da532c}
@media (prefers-color-scheme:dark){:root{--ink:#eee8e0;--muted:#a59c92;--paper:#161412;--card:#201d1a;--line:#3a352f}}
*{box-sizing:border-box}body{margin:0;padding:24px 16px 80px;background:var(--paper);color:var(--ink);
font:16px/1.5 system-ui,Segoe UI,sans-serif}h1{font-size:24px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 8px}
.sub{color:var(--muted);margin:0 0 20px}.item{background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:14px;margin:0 0 18px}.row{overflow-x:auto}.media{display:block;max-width:none}
.line{font-weight:600;margin:6px 0}.meta{color:var(--muted);font-size:13px}label.tick{display:flex;gap:10px;
align-items:center;font-size:18px;font-weight:700;margin:10px 0 4px;cursor:pointer}label.tick input{width:22px;height:22px}
.sheet{display:block;max-width:none;margin-top:8px}.bar{position:sticky;bottom:0;background:var(--card);
border-top:2px solid var(--accent);padding:12px 16px;margin:0 -16px -80px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
button{font:inherit;font-weight:800;background:var(--accent);color:#fff;border:0;border-radius:10px;padding:12px 18px;cursor:pointer}
#out{font-family:ui-monospace,monospace;font-size:14px}textarea{width:100%;min-height:140px;font:inherit;padding:10px;
border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
.open{color:#b3261e;font-weight:700}.done{color:#2e7d32;font-weight:700}.dropped{color:var(--muted)}
video{background:#000}.thumbs img{width:240px;margin:4px;border:1px solid var(--line)}
"""

def link(f: pathlib.Path, base: pathlib.Path) -> str:
    """A link from the page to a file: relative when it can be (the folder can move), a full
    file:// link when the two sit on different drives."""
    try:
        return E(os.path.relpath(f, base).replace("\\", "/"))
    except ValueError:
        return E(pathlib.Path(f).resolve().as_uri())


COPY_JS = """
function copyText(t){const o=document.getElementById('out');o.textContent=t;
 (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(
  ()=>{o.textContent=t+'   ✓ copied — paste it to Claude';},()=>{o.textContent=t+'   (select and copy this line)';});}
"""


def _sheet(src: str, out: pathlib.Path) -> bool:
    """One frame a second, at full size, five across — from the full-size file (local or URL)."""
    if out.is_file():
        return True
    out.parent.mkdir(parents=True, exist_ok=True)
    if src.startswith("file:"):                 # ffmpeg wants a path, not a file:// link
        from urllib.parse import unquote, urlparse
        src = unquote(urlparse(src).path).lstrip("/")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", src, "-vf",
                        "fps=1,tile=5x2", "-frames:v", "1", str(out)],
                       capture_output=True, text=True, timeout=600)
    return r.returncode == 0 and out.is_file()


def broll_page(eps: list) -> pathlib.Path:
    """One page for one episode (its output/review/) or several (docs/two-way-reviews/)."""
    if len(eps) == 1:
        page = eps[0].p("output/review/broll-review.html")
    else:
        page = PP / "docs/two-way-reviews" / ("broll-review-" + "-".join(e.tag for e in eps) + ".html")
    page.parent.mkdir(parents=True, exist_ok=True)
    sheets = page.parent / "sheets"
    body = [f"<h1>B-roll and covers — {E(', '.join(e.tag for e in eps))}</h1>",
            "<p class='sub'>Every clip plays at its full size — scroll sideways if it is wider than "
            "your screen. Look for numbers on saddlecloths, extra legs, faces, and anything odd. "
            "Tick the ones you want, then press <b>Copy my picks</b> and paste the line to Claude.</p>"]
    for ep in eps:
        cands = json.loads(ep.p("output/review/broll-candidates.json").read_text(encoding="utf-8"))
        body.append(f"<h2>{E(ep.tag)}</h2>")
        for c in cands:
            cid = str(c["id"])
            pick = (f"cover {cid}" if c.get("kind") == "cover" else cid)
            url = c["url"]
            if c.get("kind") == "cover":
                media = f"<img class='media' src='{E(url)}' alt='cover {E(cid)}'>"
                sheet = ""
            else:
                media = (f"<video class='media' src='{E(url)}' controls loop muted playsinline "
                         f"preload='metadata'></video>")
                sf = sheets / f"{ep.tag}-{re.sub(r'[^A-Za-z0-9]+', '-', cid)}.png"
                ok = _sheet(url, sf)
                sheet = (f"<div class='row'><img class='sheet' src='{link(sf, page.parent)}' "
                         f"alt='one frame a second, full size'></div>" if ok else
                         "<p class='meta'>(could not make a contact sheet from this file)</p>")
            body.append(
                f"<div class='item'><label class='tick'><input type='checkbox' data-ep='{E(ep.tag)}' "
                f"data-pick='{E(pick)}'> {E(pick.upper() if c.get('kind') == 'cover' else cid)}"
                f"{' — ' + E(c.get('slot', '')) if c.get('slot') else ''}</label>"
                f"<p class='line'>{E(c.get('line', ''))}</p><div class='row'>{media}</div>{sheet}"
                f"<p class='meta'>job {E(str(c.get('job_id', '')))}</p></div>")
    js = COPY_JS + """
function picks(){const by={};document.querySelectorAll('input[data-pick]').forEach(b=>{
 if(b.checked){(by[b.dataset.ep]=by[b.dataset.ep]||[]).push(b.dataset.pick);}});
 const parts=Object.keys(by).map(e=>e.replace('PP-','')+': '+by[e].filter(p=>!p.startsWith('cover')).join(' ')
  +(by[e].some(p=>p.startsWith('cover'))?' · '+by[e].filter(p=>p.startsWith('cover')).join(' '):''));
 copyText(parts.length?parts.join('  |  '):'(nothing ticked)');}
"""
    doc = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
           f"content='width=device-width,initial-scale=1'><title>B-roll review</title><style>{CSS}</style>"
           f"</head><body>{''.join(body)}<div class='bar'><button onclick='picks()'>Copy my picks</button>"
           f"<span id='out'></span></div><script>{js}</script></body></html>")
    page.write_text(doc, encoding="utf-8")
    print(f"wrote {page}")
    return page


def cut_page(ep, k: int) -> pathlib.Path:
    page = ep.p(f"output/review/cut{k}.html")
    page.parent.mkdir(parents=True, exist_ok=True)
    rel = lambda f: link(f, page.parent)                                    # noqa: E731
    film = ep.p(f"output/{ep.tag}-cut{k}.mp4")
    body = [f"<h1>{E(ep.tag)} — cut {k}</h1>",
            "<p class='sub'>Watch it through first. Then write what you think — in your own words, "
            "one note per line — and press <b>Copy my notes</b>.</p>",
            f"<div class='row'><video src='{rel(film)}' controls preload='metadata' "
            "style='width:100%;max-width:1280px'></video></div>"]
    ch = ep.p(f"output/review/cut{k}-changes.json")
    if ch.is_file():
        changes = json.loads(ch.read_text(encoding="utf-8")).get("changes", [])
        if changes:
            body.append(f"<h2>What changed since cut {k - 1}</h2><ol>")
            for c in changes:
                st = c.get("status", "OPEN")
                body.append(f"<li>{E(c['text'])} — <span class='{st.lower()}'>{E(st)}</span></li>")
            body.append("</ol>")
    sounds = [ep.p("output/qc/midroll-listen.wav")] + sorted(ep.p("output/qc/joins").glob("*.wav")) \
        if ep.p("output/qc/joins").is_dir() else [ep.p("output/qc/midroll-listen.wav")]
    sounds = [s for s in sounds if s.is_file()]
    if sounds:
        body.append("<h2>To listen to</h2>")
        for s in sounds:
            body.append(f"<p class='line'>{E(s.name)}</p><audio controls src='{rel(s)}'></audio>")
    fe = ep.p(f"output/review/fresh-eyes-cut{k}.md")
    if fe.is_file():
        body.append("<h2>Fresh-eyes reviewer (a helper that saw only the frames)</h2>"
                    f"<pre style='white-space:pre-wrap'>{E(fe.read_text(encoding='utf-8'))}</pre>")
    frames = ep.p(f"output/qc-frames/{film.stem}")
    shots = sorted(frames.glob("*.png")) if frames.is_dir() else []
    if shots:
        body.append(f"<h2>Frames from the finished file ({len(shots)})</h2><div class='thumbs'>")
        body += [f"<a href='{rel(s)}' target='_blank'><img src='{rel(s)}' alt='{E(s.stem)}' "
                 f"title='{E(s.stem)}'></a>" for s in shots]
        body.append("</div>")
    g = json.loads(ep.p("docs/twoway-gates.json").read_text(encoding="utf-8")) \
        if ep.p("docs/twoway-gates.json").is_file() else {}
    open_gates = [x for x in ("cut_watch", "join_listen", "title_thumbnail", "publish")
                  if (g.get(x if x != "cut_watch" else f"cut_watch#{k}") or {}).get("verdict") != "approved"]
    names = {"cut_watch": "the watch of this cut", "join_listen": "the midroll listen",
             "title_thumbnail": "the title and thumbnail", "publish": "publishing"}
    body.append("<h2>Still waiting on you</h2><ul>" + "".join(
        f"<li>{E(names[x])}</li>" for x in open_gates) + "</ul>")
    body.append("<h2>Your notes</h2><textarea id='notes' placeholder='One note per line'></textarea>")
    js = COPY_JS + f"""
function notes(){{const ls=document.getElementById('notes').value.split(/\\n/).map(s=>s.trim()).filter(Boolean);
 copyText('{E(ep.tag)} cut {k} notes:\\n'+ls.map((l,i)=>(i+1)+'. '+l).join('\\n'));}}
"""
    doc = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
           f"content='width=device-width,initial-scale=1'><title>{E(ep.tag)} cut {k}</title>"
           f"<style>{CSS}</style></head><body>{''.join(body)}<div class='bar'>"
           f"<button onclick='notes()'>Copy my notes</button><span id='out'></span></div>"
           f"<script>{js}</script></body></html>")
    page.write_text(doc, encoding="utf-8")
    print(f"wrote {page}")
    return page


def main() -> int:
    import argparse
    import twoway_run as tr
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=("broll", "cut"))
    ap.add_argument("eps", nargs="+")
    ap.add_argument("--cut", type=int)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    eps = [tr.Ep(int(re.sub(r"\D", "", e)), offline=a.offline) for e in a.eps]
    if a.what == "broll":
        broll_page(eps)
    else:
        cut_page(eps[0], a.cut or eps[0].latest_cut())
    return 0


if __name__ == "__main__":
    sys.exit(main())
