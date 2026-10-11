#!/usr/bin/env python3
"""fbx_cards.py — author and render every FBX card for one week, from data + measured cues.

    python fbx_cards.py <job_dir> [--html-only]

Inputs : overlay/fbx-week.json  (the week — see fbx_data.py, which proves its numbers)
         renders/words-forced.json (fbx_align.py — the measured word times)
         overlay/fbx-pack/…        (the FBX Video Pack: logos, Archivo fonts, the Saturday Report)
Outputs: overlay/cards/*.html     (one page per card; the cue times are BAKED IN from the audio)
         overlay/clips/*.mp4|.mov (one short clip per card — never one full-length overlay)
         overlay/cues.json        (the cue sheet the assembler reads)

THE LOOK IS FBX, NOT PP (Hugh's ruling): charcoal #1B2126, panels #252D33, gold #D9A441,
text #F2F4F3/#C3CBD1, Archivo 400/600/800, the FBX logo, the tag chips in the fixed order
Core / Victorian Select / Value Select. PP appears only as the endorser. No PP orange.
Animated the PP way: pp-anim.js keyframes only (render SEEKS, it never plays).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fbx_data as fd  # noqa: E402

ASSETS = HERE.parent.parent / "assets"           # the skill's standing assets (pp-anim.js, warranty)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

CSS = """
@font-face{font-family:Archivo;src:url(assets/fonts/Archivo-400.woff2) format('woff2');font-weight:400}
@font-face{font-family:Archivo;src:url(assets/fonts/Archivo-600.woff2) format('woff2');font-weight:600}
@font-face{font-family:Archivo;src:url(assets/fonts/Archivo-800.woff2) format('woff2');font-weight:800}
:root{--bg:#1B2126;--panel:#252D33;--div:#333D45;--gold:#D9A441;--t1:#F2F4F3;--t2:#C3CBD1;
      --win:#2A2A22;--ink:#0E1316;--blue:#2F4DB0;--ivory:#E6DFCC}
*{box-sizing:border-box}
html,body{margin:0;padding:0;overflow:hidden}
body{position:relative;font-family:Archivo,sans-serif;color:var(--t1);-webkit-font-smoothing:antialiased}
.abs{position:absolute}
.eyebrow{display:flex;align-items:center;gap:24px;color:var(--gold);font-weight:600;letter-spacing:.22em;text-transform:uppercase;white-space:nowrap}
.eyebrow .rule{width:70px;height:4px;background:var(--gold);transform-origin:left center;flex:none}
.chips{display:flex;gap:12px}
.chip{display:inline-block;border-radius:999px;font-weight:600;line-height:1;white-space:nowrap}
.chip.core{background:var(--gold);color:var(--ink)}
.chip.vic{background:var(--blue);color:#fff}
.chip.val{background:var(--ivory);color:var(--ink)}
.h{font-weight:800;line-height:1;letter-spacing:-.01em;white-space:nowrap}
.gold{color:var(--gold)}
.t2{color:var(--t2)}
.small{color:var(--t2);font-weight:400}
.endorse{display:flex;align-items:center;gap:22px;color:var(--t2);font-weight:600;letter-spacing:.22em;white-space:nowrap}
.preload{position:absolute;left:-9999px;top:0}
"""
PRELOAD = ('<div class="preload"><span style="font-weight:400">Aa</span>'
           '<span style="font-weight:600">Aa</span><span style="font-weight:800">Aa</span></div>')
CHIPCLS = {"Core": "core", "Victorian Select": "vic", "Value Select": "val"}


def page(W, H, body, spec, bg="var(--bg)", title="FBX card"):
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>'
            f'<style>{CSS}\nbody{{width:{W}px;height:{H}px;background:{bg}}}</style>'
            f'<script src="pp-anim.js"></script></head><body>{PRELOAD}{body}'
            f'<script>ppInit({json.dumps(spec)});</script></body></html>')


def A(sel, kf, ms, dur, easing="cubic-bezier(.2,.8,.2,1)"):
    return {"sel": sel, "kf": kf, "opts": {"delay": max(0, round(ms)), "duration": round(dur), "easing": easing}}


def fade(sel, ms, dur=300, dy=0, dx=0):
    a = {"opacity": 0}
    if dy or dx:
        a["transform"] = f"translate({dx}px,{dy}px)"
    b = {"opacity": 1}
    if dy or dx:
        b["transform"] = "translate(0px,0px)"
    return A(sel, [a, b], ms, dur, "ease-out")


def slam(sel, ms, dur=380, origin_scale=1.32):
    return A(sel, [{"opacity": 0, "transform": f"scale({origin_scale})"},
                   {"opacity": 1, "transform": "scale(0.97)", "offset": 0.7},
                   {"opacity": 1, "transform": "scale(1)"}], ms, dur)


def wipe(sel, ms, dur=380):
    return A(sel, [{"transform": "scaleX(0)"}, {"transform": "scaleX(1)"}], ms, dur)


def chips(tags, px):
    pad = f"{round(px * .28)}px {round(px * .78)}px"
    return '<div class="chips">' + "".join(
        f'<span class="chip {CHIPCLS[t]}" style="font-size:{px}px;padding:{pad}">{t}</span>' for t in tags) + "</div>"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def meta_line(s):
    return f"{s['track']} {s['race']} · No.{s['no']} · Morning {fd.money(s['morning'])}"


def result_main(s, basis=True):
    if s["finish"] == 1:
        return f"WON · {fd.money(s['win'])}" + (f" {s['win_basis']}" if basis else "")
    return ordinal(s["finish"])


def place_line(s):
    return f"Place {fd.money(s['place'])} {s['place_basis']}" if s.get("place") else ""


def endorse(px, logo_h):
    return (f'<div class="endorse" style="font-size:{px}px"><span>BROUGHT TO YOU BY</span>'
            f'<img src="assets/pp-logo-on-dark.svg" style="height:{logo_h}px" alt="Practical Punting"></div>')


def fbx_logo(h, extra=""):
    return f'<img src="assets/fbx-logo-on-dark.svg" style="height:{h}px;display:block{extra}" alt="FBX">'


def footer16(sel_logo="#flogo", sel_end="#fend"):
    return (f'<div id="flogo" class="abs" style="left:140px;bottom:46px">{fbx_logo(58)}</div>'
            f'<div id="fend" class="abs" style="right:140px;bottom:52px">{endorse(19, 46)}</div>')


# ============================================================== 16:9 cards
def c_pip(wk, T):
    """Shot 1 — card 4's headline only, a panel at ~40% width beside Gordon."""
    t0 = 0.0
    body = (f'<div id="pip" class="abs" style="left:48px;top:322px;width:720px;padding:44px 46px 50px;'
            f'background:rgba(27,33,38,.95);border:1px solid var(--div);border-radius:20px">'
            f'<div id="plogo">{fbx_logo(56)}</div>'
            f'<div id="peye" class="eyebrow" style="font-size:24px;margin-top:30px"><span class="rule" style="width:52px"></span>'
            f'{wk["raw"]["date_label"].upper()}</div>'
            f'<div id="phead" class="h" style="font-size:96px;margin-top:22px;transform-origin:left center">'
            f'{wk["head1"].replace(" FROM", "<br>FROM")}</div></div>')
    hook = (T["hook"] - t0) * 1000
    spec = [fade("#pip", 0, 280, dx=-40), fade("#plogo", 120, 300), fade("#peye", 160, 300),
            slam("#phead", hook - 60)]
    return page(1920, 1080, body, spec, bg="transparent", title="FBX hook panel")


def c_report(wk, T, W=1920, H=1080):
    """Shot 2 — a slow push from the Saturday Report's header into 'Today's selections'.
    Page units are the report PNG's own pixels (1241 wide); the image is a 300-dpi render
    of the real PDF shown at that width, so the zoom never upscales."""
    dur = (T["results_in"] - T["report_in"]) * 1000 + 400
    if W > H:
        a = (1920 / 1241, 0, 0)                  # full page width, header at the top
        b = (1920 / 1080, 80, 416)               # the selections table, edge to edge
    else:
        k = 1080 / 1241                          # whole page, centred on the charcoal
        a = (k, 0, -(1920 / k - 1755) / 2)
        b = (1.0, 80, 720 - 960)                 # the selections table (y≈720) centred, edge to edge

    def tf(k, x, y):
        return f"translate({-x * k:.1f}px,{-y * k:.1f}px) scale({k:.5f})"
    body = (f'<img id="rep" src="assets/report.png" class="abs" style="left:0;top:0;width:1241px;'
            f'transform-origin:0 0;transform:{tf(*a)}">')
    spec = [A("#rep", [{"transform": tf(*a)}, {"transform": tf(*b)}], 0, dur, "cubic-bezier(.45,0,.4,1)")]
    return page(W, H, body, spec, title="FBX Saturday Report")


def c_results(wk, T):
    """Shots 3–4 — card 3. Six rows in race order, dimmed; each lights on its horse's name."""
    t0 = T["results_in"]
    rows = ""
    spec = [wipe("#erule", 0), fade("#etext", 120, 380), fade("#panel", 60, 300),
            fade("#small", 300, 400), fade("#flogo", 300, 400), fade("#fend", 380, 400)]
    for i, s in enumerate(wk["sel"]):
        won = s["finish"] == 1
        main_cls = "gold" if won else ""
        rows += (f'<div class="row" style="position:relative;height:130px;border-top:{"0" if i == 0 else "1px solid var(--div)"}">'
                 f'<div id="bg{i}" class="abs" style="inset:0;background:var(--win);opacity:0"></div>'
                 f'<div id="in{i}" class="abs" style="inset:0">'
                 f'<div id="dm{i}" class="abs" style="inset:0;opacity:.28">'
                 f'<div class="abs" style="left:30px;top:12px">'
                 f'<div class="t2" style="font-size:24px;line-height:1.15">{meta_line(s)}</div>'
                 f'<div class="h" style="font-size:38px;margin-top:3px;letter-spacing:0">{s["horse"]}</div>'
                 f'<div style="margin-top:9px">{chips(s["tags"], 21)}</div></div></div>'
                 f'<div id="rs{i}" class="abs" style="right:30px;top:0;bottom:0;display:flex;flex-direction:column;'
                 f'justify-content:center;align-items:flex-end;opacity:0">'
                 f'<div class="h {main_cls}" style="font-size:36px;letter-spacing:0">{result_main(s)}</div>'
                 f'<div class="t2" style="font-size:26px;margin-top:6px">{place_line(s)}</div></div>'
                 f'</div></div>')
        spec.append(fade(f"#in{i}", 160 + 70 * i, 300, dy=12))
        lit = (T["rows"][s["horse"]] - t0) * 1000 - 120
        spec.append(A(f"#dm{i}", [{"opacity": .28}, {"opacity": 1}], lit, 260, "ease-out"))
        if won:
            spec.append(A(f"#bg{i}", [{"opacity": 0}, {"opacity": 1}], lit, 260, "ease-out"))
        spec.append(fade(f"#rs{i}", lit + 60, 320, dx=26))
    body = (f'<div class="eyebrow abs" style="left:140px;top:50px;font-size:31px"><span id="erule" class="rule"></span>'
            f'<span id="etext">{wk["copy"]["results_eyebrow"]}</span></div>'
            f'<div id="panel" class="abs" style="left:140px;top:106px;width:1640px;background:var(--panel);'
            f'border-radius:18px;overflow:hidden">{rows}</div>'
            f'<div id="small" class="abs small" style="left:140px;top:910px;font-size:21px">{wk["raw"]["small_print"]}</div>'
            + footer16())
    return page(1920, 1080, body, spec, title="FBX results")


def c_summary(wk, T):
    """Shot 5 — card 4. Headline, ALL SIX PLACED, then the units and ROI slam in on Gordon's words."""
    t0 = T["summary_in"]
    w, c = wk["calc"]["win"], wk["calc"]
    staked = w["staked"][:-3] if w["staked"].endswith(".00") else w["staked"]
    body = (f'<div class="eyebrow abs" style="left:140px;top:118px;font-size:31px"><span id="erule" class="rule"></span>'
            f'<span id="etext">{wk["copy"]["summary_eyebrow"]}</span></div>'
            f'<div id="h1" class="h abs" style="left:140px;top:172px;font-size:148px;transform-origin:left center">{wk["head1"]}</div>'
            f'<div id="h2" class="h abs gold" style="left:140px;top:322px;font-size:148px;transform-origin:left center">{wk["head2"]}</div>'
            f'<div id="wl" class="abs t2" style="left:140px;top:492px;font-size:40px">Win: {staked} units staked, {w["returned"]} returned</div>'
            f'<div class="abs h" style="left:140px;top:556px;font-size:118px;display:flex;align-items:baseline">'
            f'<span id="un" style="display:inline-block;transform-origin:left center">{w["profit"]} units</span>'
            f'<span id="dt" style="display:inline-block;margin:0 .26em">·</span>'
            f'<span id="ro" class="gold" style="display:inline-block;transform-origin:left center">{w["roi"]} ROI</span></div>'
            f'<div id="pe" class="abs t2" style="left:140px;top:708px;font-size:38px;white-space:nowrap">'
            f'Place {c["place"]["profit"]} units ({c["place"]["roi"]})&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'Each way {c["each_way"]["profit"]} units ({c["each_way"]["roi"]})</div>'
            f'<div id="small" class="abs small" style="left:140px;top:876px;font-size:21px">{wk["raw"]["small_print"]}</div>'
            + footer16())
    u = (T["units_on"] - t0) * 1000
    r = (T["roi_on"] - t0) * 1000
    spec = [wipe("#erule", 0), fade("#etext", 120, 380), slam("#h1", 150), slam("#h2", 850),
            fade("#small", 200, 400), fade("#flogo", 300, 400), fade("#fend", 380, 400),
            fade("#wl", u - 450, 350, dy=10), slam("#un", u - 80),
            fade("#dt", r - 120, 200), slam("#ro", r - 80), fade("#pe", r + 1000, 450, dy=10)]
    return page(1920, 1080, body, spec, title="FBX results summary")


def c_gap(wk, T):
    """Shot 6 — card 5. Sorted by FBX Gap; the top ones turn gold on 'the four that won'."""
    if not wk["top_gaps_all_won"]:
        raise fd.Halt("This week the biggest gaps did NOT all win, so 'THE N BIGGEST GAPS ALL WON.' "
                      "would be false. The gap card needs a new headline — a human decision. Nothing built.")
    t0 = T["gap_in"]
    nwon = len(wk["won"])
    rows = ""
    spec = [wipe("#erule", 0), fade("#etext", 120, 380), slam("#gh", 150), fade("#panel", 250, 300),
            fade("#small", 300, 400), fade("#flogo", 300, 400), fade("#fend", 380, 400)]
    for i, s in enumerate(wk["gaps"]):
        top = i < nwon
        rows += (f'<div style="position:relative;height:80px;border-top:{"0" if i == 0 else "1px solid var(--div)"}">'
                 f'<div id="gb{i}" class="abs" style="inset:0;background:var(--win);opacity:0"></div>'
                 f'<div id="gr{i}" class="abs" style="inset:0;display:flex;align-items:center">'
                 f'<div class="h" style="margin-left:34px;font-size:40px;letter-spacing:0">{s["horse"]}</div>'
                 f'<div class="t2" style="margin-left:18px;font-size:28px;margin-top:6px">{s["track"]} {s["race"]}</div>'
                 f'<div class="h abs" style="right:376px;font-size:44px;letter-spacing:0">{s["gap"]}</div></div>'
                 f'<div id="gx{i}" class="abs h {"gold" if s["finish"] == 1 else ""}" style="right:34px;top:0;bottom:0;'
                 f'display:flex;align-items:center;font-size:37px;letter-spacing:0;opacity:0">{result_main(s, basis=False)}</div>'
                 f'</div>')
        spec.append(fade(f"#gr{i}", 300 + 70 * i, 300, dy=10))
        if top:
            g = (T["gold"][i] - t0) * 1000
            spec += [A(f"#gb{i}", [{"opacity": 0}, {"opacity": 1}], g - 40, 240, "ease-out"),
                     fade(f"#gx{i}", g, 280, dx=22)]
        else:
            spec.append(fade(f"#gx{i}", (T["gold"][-1] - t0) * 1000 + 350, 300))
    body = (f'<div class="eyebrow abs" style="left:140px;top:86px;font-size:31px"><span id="erule" class="rule"></span>'
            f'<span id="etext">{wk["copy"]["gap_eyebrow"]}</span></div>'
            f'<div id="gh" class="h abs" style="left:140px;top:138px;font-size:98px;transform-origin:left center">{wk["copy"]["gap_headline"]}</div>'
            f'<div id="panel" class="abs" style="left:140px;top:266px;width:1640px;background:var(--panel);'
            f'border-radius:18px;overflow:hidden">{rows}</div>'
            f'<div id="small" class="abs small" style="left:140px;top:790px;font-size:21px">{wk["raw"]["small_print"]}</div>'
            + footer16())
    return page(1920, 1080, body, spec, title="FBX gap card")


def c_lower_third(wk, T):
    """Shot 8 — 'JOIN FBX – LINK BELOW', gold Archivo 800, bottom-left, clear of Gordon."""
    t0 = T["join_in"]
    on = (T["lower_third_on"] - t0) * 1000 - 100
    l1, l2 = wk["copy"]["closing_line1"], wk["copy"]["closing_line2"]
    body = (f'<div id="lt" class="abs" style="left:48px;bottom:60px;padding:20px 30px 22px 28px;'
            f'background:rgba(27,33,38,.95);border-left:6px solid var(--gold);border-radius:4px 14px 14px 4px;'
            f'transform-origin:left center">'
            f'<div id="ltl" style="margin-bottom:14px">{fbx_logo(36)}</div>'
            f'<div id="ltx" class="h gold" style="font-size:48px;line-height:1.04">{l1}<br>{l2}</div></div>')
    spec = [A("#lt", [{"opacity": 0, "transform": "scaleX(0.2)"}, {"opacity": 1, "transform": "scaleX(1)"}], on, 340),
            fade("#ltl", on + 150, 300), fade("#ltx", on + 180, 300, dx=-14)]
    return page(1920, 1080, body, spec, bg="transparent", title="FBX lower third")


def closing_spec(arrow_bob_ms=3600):
    spec = [fade("#clogo", 0, 500, dy=24), slam("#c1", 350), slam("#c2", 650), fade("#cend", 500, 400),
            A("#arr", [{"opacity": 0, "transform": "translateY(-24px)"}, {"opacity": 1, "transform": "translateY(0px)"}],
              950, 300, "ease-out")]
    bob = []
    n = 4
    for k in range(n):
        bob += [{"transform": "translateY(0px)", "offset": k / n},
                {"transform": "translateY(16px)", "offset": (k + .5) / n}]
    bob.append({"transform": "translateY(0px)", "offset": 1})
    spec.append(A("#arw", bob, 1250, arrow_bob_ms, "ease-in-out"))
    return spec


def c_closing(wk, T):
    """Shot 10 — card 6. FBX logo, JOIN FBX –, LINK BELOW in gold, a gold arrow bobbing. No price."""
    body = (f'<div id="clogo" class="abs" style="left:140px;top:252px">{fbx_logo(166)}</div>'
            f'<div id="c1" class="h abs" style="left:140px;top:472px;font-size:150px;transform-origin:left center">{wk["copy"]["closing_line1"]}</div>'
            f'<div id="c2" class="h abs gold" style="left:140px;top:618px;font-size:150px;transform-origin:left center">{wk["copy"]["closing_line2"]}</div>'
            f'<div id="arr" class="abs" style="left:140px;top:797px"><div id="arw" style="width:0;height:0;'
            f'border-left:44px solid transparent;border-right:44px solid transparent;border-top:50px solid var(--gold)"></div></div>'
            f'<div id="cend" class="abs" style="right:140px;bottom:96px">{endorse(22, 52)}</div>')
    return page(1920, 1080, body, closing_spec(), title="FBX closing card")


# ============================================================== 9:16 cards
def upper(wk, T, inner, spec, title):
    body = (f'<div id="ulogo" class="abs" style="left:80px;top:96px">{fbx_logo(92)}</div>{inner}')
    return page(1080, 960, body, spec, title=title)


def v_idle(wk, T):
    return upper(wk, T, "", [fade("#ulogo", 0, 10)], "FBX upper idle")


def v_hook(wk, T):
    inner = (f'<div id="ve" class="eyebrow abs" style="left:80px;top:330px;font-size:27px"><span class="rule" style="width:56px"></span>'
             f'{wk["copy"]["results_eyebrow"]}</div>'
             f'<div id="vh" class="h abs" style="left:80px;top:400px;font-size:146px;line-height:.98;transform-origin:left center">'
             f'{wk["head1"].replace(" FROM", "<br>FROM")}</div>')
    hook = T["hook"] * 1000
    return upper(wk, T, inner, [fade("#ulogo", 0, 10), fade("#ve", 60, 300), slam("#vh", hook - 60)], "FBX hook (vertical)")


def v_join(wk, T):
    t0 = T["join_in"]
    on = (T["lower_third_on"] - t0) * 1000 - 100
    inner = (f'<div id="vj" class="abs" style="left:80px;top:420px;padding-left:34px;border-left:8px solid var(--gold)">'
             f'<div id="vj1" class="h gold" style="font-size:118px;line-height:1.04;transform-origin:left center">'
             f'{wk["copy"]["closing_line1"]}<br>{wk["copy"]["closing_line2"]}</div></div>')
    return upper(wk, T, inner, [fade("#ulogo", 0, 10), fade("#vj", on, 300, dx=-30), slam("#vj1", on + 60)],
                 "FBX join (vertical)")


def v_results(wk, T):
    """Style frame 07 — the vertical results, rows lighting on Gordon's words, then the win totals."""
    t0 = T["results_in"]
    w = wk["calc"]["win"]
    rows = ""
    spec = [fade("#vl", 0, 300), slam("#vh", 120), fade("#vd", 300, 300), fade("#panel", 200, 300),
            fade("#small", 400, 400), fade("#vend", 450, 400)]
    for i, s in enumerate(wk["sel"]):
        won = s["finish"] == 1
        rows += (f'<div style="position:relative;height:117px;border-top:{"0" if i == 0 else "1px solid var(--div)"}">'
                 f'<div id="bg{i}" class="abs" style="inset:0;background:var(--win);opacity:0"></div>'
                 f'<div id="in{i}" class="abs" style="inset:0"><div id="dm{i}" class="abs" style="inset:0;opacity:.28">'
                 f'<div class="abs" style="left:30px;top:20px"><div class="t2" style="font-size:26px">'
                 f'{s["track"]} {s["race"]} · No.{s["no"]}</div>'
                 f'<div class="h" style="font-size:40px;margin-top:4px;letter-spacing:0">{s["horse"]}</div></div></div>'
                 f'<div id="rs{i}" class="abs h {"gold" if won else ""}" style="right:30px;top:0;bottom:0;display:flex;'
                 f'align-items:center;font-size:40px;letter-spacing:0;opacity:0">{result_main(s, basis=False)}</div>'
                 f'</div></div>')
        spec.append(fade(f"#in{i}", 260 + 60 * i, 300, dy=10))
        lit = (T["rows"][s["horse"]] - t0) * 1000 - 120
        spec.append(A(f"#dm{i}", [{"opacity": .28}, {"opacity": 1}], lit, 260, "ease-out"))
        if won:
            spec.append(A(f"#bg{i}", [{"opacity": 0}, {"opacity": 1}], lit, 260, "ease-out"))
        spec.append(fade(f"#rs{i}", lit + 60, 320, dx=22))
    u = (T["units_on"] - t0) * 1000
    r = (T["roi_on"] - t0) * 1000
    spec += [slam("#vu", u - 80), slam("#vr", r - 80)]
    body = (f'<div id="vl" class="abs" style="left:80px;top:134px">{fbx_logo(92)}</div>'
            f'<div id="vh" class="h abs" style="left:80px;top:300px;font-size:112px;line-height:.98;transform-origin:left center">'
            f'{wk["head1"].replace(" FROM", "<br>FROM")}</div>'
            f'<div id="vd" class="abs t2" style="left:80px;top:540px;font-size:40px">{wk["raw"]["date_label"]}</div>'
            f'<div id="panel" class="abs" style="left:80px;top:633px;width:920px;background:var(--panel);border-radius:18px;overflow:hidden">{rows}</div>'
            f'<div id="vu" class="h abs" style="left:80px;top:1394px;font-size:84px;transform-origin:left center">{w["profit"]} units</div>'
            f'<div id="vr" class="h abs gold" style="left:80px;top:1482px;font-size:84px;transform-origin:left center">{w["roi"]} ROI on the win</div>'
            f'<div id="small" class="abs small" style="left:80px;top:1606px;width:920px;font-size:24px;line-height:1.35">{wk["raw"]["small_print"]}</div>'
            f'<div id="vend" class="abs" style="left:80px;top:1730px">{endorse(19, 46)}</div>')
    return page(1080, 1920, body, spec, title="FBX vertical results")


def v_gap(wk, T):
    if not wk["top_gaps_all_won"]:
        raise fd.Halt("The biggest gaps did not all win this week — the gap headline needs a human. Nothing built.")
    t0 = T["gap_in"]
    nwon = len(wk["won"])
    rows = ""
    spec = [fade("#vl", 0, 300), fade("#ve", 100, 300), slam("#gh", 150), fade("#panel", 250, 300),
            fade("#small", 400, 400), fade("#vend", 450, 400)]
    for i, s in enumerate(wk["gaps"]):
        rows += (f'<div style="position:relative;height:132px;border-top:{"0" if i == 0 else "1px solid var(--div)"}">'
                 f'<div id="gb{i}" class="abs" style="inset:0;background:var(--win);opacity:0"></div>'
                 f'<div id="gr{i}" class="abs" style="inset:0">'
                 f'<div class="abs" style="left:30px;top:24px"><div class="h" style="font-size:42px;letter-spacing:0">{s["horse"]}</div>'
                 f'<div class="t2" style="font-size:26px;margin-top:8px">{s["track"]} {s["race"]}</div></div>'
                 f'<div class="h abs" style="right:30px;top:22px;font-size:46px;letter-spacing:0">{s["gap"]}</div></div>'
                 f'<div id="gx{i}" class="abs h {"gold" if s["finish"] == 1 else ""}" style="right:30px;top:80px;'
                 f'font-size:30px;letter-spacing:0;opacity:0">{result_main(s, basis=False)}</div></div>')
        spec.append(fade(f"#gr{i}", 300 + 60 * i, 300, dy=10))
        if i < nwon:
            g = (T["gold"][i] - t0) * 1000
            spec += [A(f"#gb{i}", [{"opacity": 0}, {"opacity": 1}], g - 40, 240, "ease-out"), fade(f"#gx{i}", g, 280, dx=20)]
        else:
            spec.append(fade(f"#gx{i}", (T["gold"][-1] - t0) * 1000 + 350, 300))
    head = wk["copy"]["gap_headline"].replace(" GAPS", "<br>GAPS")
    body = (f'<div id="vl" class="abs" style="left:80px;top:134px">{fbx_logo(92)}</div>'
            f'<div id="ve" class="eyebrow abs" style="left:80px;top:318px;font-size:27px"><span class="rule" style="width:56px"></span>'
            f'{wk["copy"]["gap_eyebrow"]}</div>'
            f'<div id="gh" class="h abs" style="left:80px;top:384px;font-size:100px;line-height:1.0;transform-origin:left center">{head}</div>'
            f'<div id="panel" class="abs" style="left:80px;top:636px;width:920px;background:var(--panel);border-radius:18px;overflow:hidden">{rows}</div>'
            f'<div id="small" class="abs small" style="left:80px;top:1460px;width:920px;font-size:24px;line-height:1.35">{wk["raw"]["small_print"]}</div>'
            f'<div id="vend" class="abs" style="left:80px;top:1590px">{endorse(19, 46)}</div>')
    return page(1080, 1920, body, spec, title="FBX vertical gap card")


def v_closing(wk, T):
    body = (f'<div id="clogo" class="abs" style="left:80px;top:470px">{fbx_logo(150)}</div>'
            f'<div id="c1" class="h abs" style="left:80px;top:760px;font-size:128px;transform-origin:left center">{wk["copy"]["closing_line1"]}</div>'
            f'<div id="c2" class="h abs gold" style="left:80px;top:890px;font-size:128px;transform-origin:left center">{wk["copy"]["closing_line2"]}</div>'
            f'<div id="arr" class="abs" style="left:80px;top:1062px"><div id="arw" style="width:0;height:0;'
            f'border-left:44px solid transparent;border-right:44px solid transparent;border-top:50px solid var(--gold)"></div></div>'
            f'<div id="cend" class="abs" style="left:80px;top:1300px">{endorse(22, 52)}</div>')
    return page(1080, 1920, body, closing_spec(), title="FBX vertical closing card")


def v_warranty():
    """The STANDARD PP warranty slide, words and look unchanged, re-laid at 1080x1920."""
    src = (ASSETS / "warranty-slide.html").read_text(encoding="utf-8")
    src = src.replace("body{width:1920px;height:1080px;", "body{width:1080px;height:1920px;")
    src = src.replace("width:1920px;height:1080px;background:#1F1F1F", "width:1080px;height:1920px;background:#1F1F1F")
    src = src.replace("padding:84px 220px 72px", "padding:150px 80px 150px")
    src = src.replace("justify-content:space-between", "justify-content:center;gap:110px")
    src = src.replace("max-width:1420px", "max-width:920px").replace("max-width:1500px", "max-width:920px")
    src = src.replace("font-size:30px;font-weight:600", "font-size:30px;line-height:1.4;font-weight:600")
    return src


# ============================================================== build
def stage_assets(job: Path, cards: Path):
    pack = job / "overlay" / "fbx-pack" / "FBX-Video-Pack_v1"
    a = cards / "assets"
    (a / "fonts").mkdir(parents=True, exist_ok=True)
    for w in (400, 600, 800):
        shutil.copyfile(pack / "fonts" / f"Archivo-{w}.woff2", a / "fonts" / f"Archivo-{w}.woff2")
    for n in ("fbx-logo-on-dark.svg", "pp-logo-on-dark.svg"):
        shutil.copyfile(pack / "logos" / n, a / n)
    shutil.copyfile(ASSETS / "pp-anim.js", cards / "pp-anim.js")
    # the standing warranty page's own logo (for the vertical re-lay) — the engine's CARD_DEPS source
    shutil.copyfile(ASSETS / "assets" / "logo.png", a / "logo.png")
    # the real Saturday Report, rendered from its PDF at 300 dpi (never upscale the 150-dpi PNG)
    pdf = next((pack / "reference").glob("FBX_Saturday_Report_*.pdf"))
    out = a / "report"
    subprocess.run(["pdftoppm", "-r", "300", "-png", "-singlefile", str(pdf), str(out)], check=True)


def main():
    job = Path(sys.argv[1]).resolve()
    html_only = "--html-only" in sys.argv
    try:
        wk = fd.load_week(job)
        T = fd.cue_sheet(job, wk)
    except fd.Halt as e:
        sys.exit(str(e))
    cards = job / "overlay" / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    stage_assets(job, cards)
    (job / "overlay" / "cues.json").write_text(json.dumps(T, indent=1), encoding="utf-8")

    builds = [  # name, html, W, H, alpha
        ("fbx-16x9-hook-panel", c_pip(wk, T), 1920, 1080, True),
        ("fbx-16x9-report", c_report(wk, T), 1920, 1080, False),
        ("fbx-16x9-results", c_results(wk, T), 1920, 1080, False),
        ("fbx-16x9-summary", c_summary(wk, T), 1920, 1080, False),
        ("fbx-16x9-gap", c_gap(wk, T), 1920, 1080, False),
        ("fbx-16x9-lower-third", c_lower_third(wk, T), 1920, 1080, True),
        ("fbx-16x9-closing", c_closing(wk, T), 1920, 1080, False),
        ("fbx-9x16-upper-idle", v_idle(wk, T), 1080, 960, False),
        ("fbx-9x16-upper-hook", v_hook(wk, T), 1080, 960, False),
        ("fbx-9x16-upper-join", v_join(wk, T), 1080, 960, False),
        ("fbx-9x16-report", c_report(wk, T, 1080, 1920), 1080, 1920, False),
        ("fbx-9x16-results", v_results(wk, T), 1080, 1920, False),
        ("fbx-9x16-gap", v_gap(wk, T), 1080, 1920, False),
        ("fbx-9x16-closing", v_closing(wk, T), 1080, 1920, False),
        ("fbx-9x16-warranty", v_warranty(), 1080, 1920, False),
        # the STANDING warranty page, byte-for-byte — unchanged, as every PP episode carries it
        ("fbx-16x9-warranty", (ASSETS / "warranty-slide.html").read_text(encoding="utf-8"), 1920, 1080, False),
    ]
    only = [a for a in sys.argv[2:] if not a.startswith("--")]
    jobs = []
    for name, html, W, H, alpha in builds:
        p = cards / f"{name}.html"
        p.write_text(html, encoding="utf-8")
        if not only or name in only:
            jobs.append((p, W, H, alpha))
    print(f"wrote {len(builds)} card pages -> {cards}")
    if html_only:
        return
    import fbx_render
    fbx_render.render_all(job / "overlay" / "clips", jobs)
    sys.stdout.flush()
    import os
    os._exit(0)


if __name__ == "__main__":
    main()
