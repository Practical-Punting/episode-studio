#!/usr/bin/env python3
"""ppd_cards.py — the PPD Club brand and every card of the "Bet Small, Win Big" promo, as HTML pages.

Each builder returns one page (1920x1080) whose cue times are BAKED IN from Gordon's measured words:
`m(key)` is "milliseconds after this card's window opens until Gordon starts <key>". Nothing is estimated.

THE LOOK IS PPD, NOT PP (Hugh's brief §7): charcoal #1E1F22, card charcoal #2C2D31, PPD red #F44336 as the
ONE hero colour, white, Raleway 800/900 headlines, Roboto body, the red tick. PP appears only as the endorser
("Brought to you by" + the PP logo) and the logo chip on Gordon's shots. No PP orange anywhere.

THE MOVES (pp-motion-graphics): Enter 260 ms, Count 900-1200 ms, Fill 600-800 ms, Slam 1.18 -> 1 in 340 ms,
Travel 520-700 ms, Draw 800 ms. Data rows 240-320 ms apart, structure 90-140 ms. A payoff gets 700-900 ms of
stillness first. The tick STAMPS (circle slams, then the white tick draws) — the signature move.
Everything is Web Animations keyframes driven by ppSeek (pp-anim.js): the renderer SEEKS, it never plays.

Segments (Hugh: "build it modular"): INTRO (hook, lower thirds, bet types) · PROOF (real day, before/after,
the five, 3 from 5, bank, tiles — all from ppd-proof-day.json) · EBOOK (book, trifecta, backing two) ·
OFFER (honest, trial, bonus, price) · END (CTA, closing). Swap the proof day = swap one JSON file.
"""
import json
import html as _h

import ppd_data as pdd

# ------------------------------------------------------------------ brand
CSS = """
@font-face{font-family:Raleway;src:url(assets/fonts/raleway-800.woff2) format('woff2');font-weight:800}
@font-face{font-family:Raleway;src:url(assets/fonts/raleway-900.woff2) format('woff2');font-weight:900}
@font-face{font-family:Roboto;src:url(assets/fonts/roboto-400.woff2) format('woff2');font-weight:400}
@font-face{font-family:Roboto;src:url(assets/fonts/roboto-400i.woff2) format('woff2');font-weight:400;font-style:italic}
@font-face{font-family:Roboto;src:url(assets/fonts/roboto-700.woff2) format('woff2');font-weight:700}
:root{--bg:#1E1F22;--card:#2C2D31;--red:#F44336;--w:#FFFFFF;--lg:#C9CACC;--sg:#8A8B8F;--mg:#5A5B5F;--div:#3A3B40;--off:#F7F7F7}
*{box-sizing:border-box}
html,body{margin:0;padding:0;overflow:hidden}
body{position:relative;width:1920px;height:1080px;font-family:Roboto,sans-serif;color:var(--w);-webkit-font-smoothing:antialiased}
.abs{position:absolute}
.r9{font-family:Raleway;font-weight:900;line-height:1;letter-spacing:-.01em;white-space:nowrap;font-variant-numeric:lining-nums proportional-nums}
.r8{font-family:Raleway;font-weight:800;line-height:1.05;letter-spacing:-.005em;white-space:nowrap;font-variant-numeric:lining-nums proportional-nums}
.tab{font-variant-numeric:lining-nums tabular-nums}
/* Raleway's DEFAULT figures are old-style (the 9 and 5 drop below the line): a scoreboard wants lining figures,
   and a number that COUNTS wants tabular ones too, or its width jitters on every tick */
.eb{display:flex;align-items:center;gap:20px;font-weight:700;color:var(--red);letter-spacing:.22em;text-transform:uppercase;white-space:nowrap}
.eb .bar{width:56px;height:5px;background:var(--red);transform-origin:left center;flex:none}
.lab{font-weight:700;letter-spacing:.2em;text-transform:uppercase;white-space:nowrap;color:var(--sg)}
.red{color:var(--red)} .lg{color:var(--lg)} .sg{color:var(--sg)}
.small{font-weight:400;color:var(--sg);line-height:1.34}
.panel{background:rgba(30,31,34,.96);border:1px solid var(--div);border-radius:22px}
.endorse{display:flex;align-items:center;gap:20px;color:var(--sg);font-weight:700;letter-spacing:.22em;white-space:nowrap}
.pill{display:inline-block;border-radius:999px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;white-space:nowrap}
.preload{position:absolute;left:-9999px;top:0}
"""
PRELOAD = ('<div class="preload"><span class="r8">Aa</span><span class="r9">Aa</span><span style="font-weight:400">Aa</span>'
           '<span style="font-weight:400;font-style:italic">Aa</span><span style="font-weight:700">Aa</span></div>')
EASE_ENTER = "cubic-bezier(0.2,0,0,1)"
EASE_DATA = "cubic-bezier(0.05,0.7,0.1,1)"
FULL_SAFE_BOTTOM = 860      # full cards keep y 860-990 clear: the captioned export puts its strip there


def page(body, spec, title, alpha=False):
    bg = "transparent" if alpha else "var(--bg)"
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>'
            f'<style>{CSS}\nbody{{background:{bg}}}</style><script src="pp-anim.js"></script></head>'
            f'<body>{PRELOAD}{body}<script>ppInit({json.dumps(spec)});</script></body></html>')


def A(sel, kf, ms, dur, easing=EASE_ENTER):
    return {"sel": sel, "kf": kf, "opts": {"delay": max(0, round(ms)), "duration": round(dur), "easing": easing}}


def enter(sel, ms, dx=0, dy=16, dur=260):
    return A(sel, [{"opacity": 0, "transform": f"translate({dx}px,{dy}px)"},
                   {"opacity": 1, "transform": "translate(0px,0px)"}], ms, dur)


def fade(sel, ms, dur=300, to=1.0, frm=0.0):
    return A(sel, [{"opacity": frm}, {"opacity": to}], ms, dur, "ease-out")


def slam(sel, ms, dur=340, s=1.18):
    return A(sel, [{"opacity": 0, "transform": f"scale({s})"},
                   {"opacity": 1, "transform": f"scale({1 + (s - 1) * .55:.3f})", "offset": 0.3},
                   {"opacity": 1, "transform": "scale(1)"}], ms, dur)


def wipe(sel, ms, dur=320, axis="X"):
    return A(sel, [{"transform": f"scale{axis}(0)"}, {"transform": f"scale{axis}(1)"}], ms, dur)


def fill(sel, ms, dur=700):
    return A(sel, [{"transform": "scaleX(0)"}, {"transform": "scaleX(1)"}], ms, dur, EASE_DATA)


def travel(sel, ms, frm, to, dur=600):
    return A(sel, [{"transform": frm}, {"transform": to}], ms, dur, EASE_DATA)


def draw(sel, ms, length, dur=800):
    return A(sel, [{"strokeDashoffset": f"{length}"}, {"strokeDashoffset": "0"}], ms, dur, EASE_ENTER)


def seq(sel, frames):
    """ONE animation through several absolute moments: frames = [(ms, {props}, easing-of-the-next-segment), ...].
    🔴 Why: every keyframe animation here fills BACKWARDS, so two animations on the SAME property of one element
    fight from t=0 and the later one wins — a fade-out written after a fade-in shows the element before it ever
    entered. Any property that changes more than once on one element goes through seq(), never two A()s."""
    t0, t1 = frames[0][0], frames[-1][0]
    dur = max(1.0, t1 - t0)
    kf = []
    for ms, props, *e in frames:
        k = dict(props, offset=round((ms - t0) / dur, 5))
        if e:
            k["easing"] = e[0]
        kf.append(k)
    return {"sel": sel, "kf": kf, "opts": {"delay": max(0, round(t0)), "duration": round(dur), "easing": "linear"}}


def count(sel, ms, frm, to, decimals=2, prefix="", suffix="", dur=1200):
    return {"sel": sel, "count": {"from": frm, "to": to, "decimals": decimals, "prefix": prefix, "suffix": suffix},
            "opts": {"delay": max(0, round(ms)), "duration": dur, "easing": EASE_DATA}}


def ledger(sel, ms, stops, seg, prefix="", suffix=""):
    """A running total that TICKS through real cumulative values (never slides)."""
    return {"sel": sel, "count": {"from": 0, "stops": stops, "segment": seg, "decimals": 0, "prefix": prefix, "suffix": suffix},
            "opts": {"delay": max(0, round(ms)), "duration": round(seg * len(stops)), "easing": "linear"}}


# ------------------------------------------------------------------ the tick
TICK_LEN = 72          # the polyline 27,52 43,68 74,33 in a 100-unit box is 69.4 long


def tick(idn, size, circle="var(--red)", mark="#FFFFFF", style=""):
    return (f'<svg id="{idn}" class="abs" viewBox="0 0 100 100" style="width:{size}px;height:{size}px;overflow:visible;{style}">'
            f'<g id="{idn}c" style="transform-origin:50px 50px;transform-box:view-box"><circle cx="50" cy="50" r="50" fill="{circle}"/></g>'
            f'<polyline id="{idn}p" points="27,52 43,68 74,33" fill="none" stroke="{mark}" stroke-width="11" '
            f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{TICK_LEN}" stroke-dashoffset="{TICK_LEN}"/></svg>')


def stamp(idn, ms):
    """The signature move: the circle SLAMS (1.18 -> 1, 340 ms), then the white tick DRAWS (220 ms)."""
    return [slam(f"#{idn}c", ms), draw(f"#{idn}p", ms + 150, TICK_LEN, 220)]


def tick_static(size, circle="var(--red)", mark="#FFFFFF", style=""):
    return (f'<svg class="abs" viewBox="0 0 100 100" style="width:{size}px;height:{size}px;{style}"><circle cx="50" cy="50" r="50" fill="{circle}"/>'
            f'<polyline points="27,52 43,68 74,33" fill="none" stroke="{mark}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg>')


# ------------------------------------------------------------------ chrome
def bug():
    """The official PPD wordmark, top right. Its baked background is exactly #1E1F22 = the canvas."""
    return '<img id="bug" class="abs" src="assets/ppd-wordmark.png" style="right:140px;top:74px;height:48px" alt="Practical Punting Daily">'


def endorse(px=17, logo_h=40, idn="end", style="right:140px;bottom:30px"):
    return (f'<div id="{idn}" class="endorse abs" style="{style};font-size:{px}px"><span>BROUGHT TO YOU BY</span>'
            f'<img src="assets/pp-logo-on-dark.svg" style="height:{logo_h}px" alt="Practical Punting"></div>')


def eyebrow(text, idn="eb", left=140, top=92, px=24):
    return (f'<div id="{idn}" class="eb abs" style="left:{left}px;top:{top}px;font-size:{px}px">'
            f'<span id="{idn}b" class="bar"></span><span id="{idn}t">{text}</span></div>')


def small_print(text, idn="sp", style="left:140px;bottom:30px;width:1130px", px=18):
    return f'<div id="{idn}" class="small abs" style="{style};font-size:{px}px">{_h.escape(text)}</div>'


def chrome(eb_text, sp_text=None, sp_ms=300, with_bug=True):
    body = eyebrow(eb_text) + (bug() if with_bug else "") + endorse() + (small_print(sp_text) if sp_text else "")
    spec = [wipe("#ebb", 0, 280), enter("#ebt", 110, dx=-12, dy=0), fade("#end", 240, 400)]
    if with_bug:
        spec.append(fade("#bug", 140, 400))
    if sp_text:
        spec.append(fade("#sp", sp_ms, 400))
    return body, spec


class Ctx:
    """One card's clock: m(key) = ms after the window opens until Gordon STARTS the cue; m(key,'end'), m(key,'pa')."""

    def __init__(self, T, t0):
        self.T, self.t0 = T, t0

    def m(self, key, which="start", off=0):
        return (self.T[key][which] - self.t0) * 1000 + off

    def word(self, key, i, off=0):
        return (self.T[key]["words"][i][1] - self.t0) * 1000 + off


# ================================================================== INTRO
def c_hook(promo, day, T, t0):
    """Shots 1-2 in ONE clip. A panel beside Gordon: five $5 bets, STAKED $25, BACK counts to $106.50 as he says it.
    Then the panel floods to full screen with the figures where they were, a beat of stillness, and +326% SLAMS
    with the tick. One timeline, so the hero number never jumps between two clips."""
    c, x = promo["copy"], Ctx(T, t0)
    calc = day["calc"]["win"]
    back = float(calc["back"])
    staked = float(calc["staked"])
    pip = "inset(150px 1172px 150px 48px round 22px)"            # x 48-748, y 150-930: clear of Gordon on the push
    tokens = "".join(f'<div id="tk{i}" class="r9" style="width:100px;height:64px;border:3px solid var(--red);border-radius:12px;'
                     f'display:flex;align-items:center;justify-content:center;font-size:32px">{pdd.money(day["stake"], 0)}</div>'
                     for i in range(len(day["selections"])))
    body = (f'<div id="bgp" class="abs" style="left:0;top:0;width:1920px;height:1080px;background:rgb(30,31,34);'
            f'clip-path:{pip}"></div>'
            f'<div id="pip">'
            + eyebrow(c["hook_eyebrow"][0], "eb", left=96, top=196, px=24)
            + f'<div id="dt" class="lab abs" style="left:96px;top:236px;font-size:21px;color:var(--lg)">{c["hook_eyebrow"][1]}</div>'
            f'<div class="abs" style="left:96px;top:300px;display:flex;gap:14px">{tokens}</div>'
            f'<div id="tkl" class="lab abs" style="left:96px;top:384px;font-size:19px">{len(day["selections"])} SELECTIONS × '
            f'{pdd.money(day["stake"], 0)} EACH</div>'
            f'<div id="stl" class="lab abs" style="left:96px;top:450px;font-size:21px">STAKED</div>'
            f'<div id="st" class="r9 abs" style="left:92px;top:482px;font-size:112px;transform-origin:left center">{pdd.money(staked, 0)}</div>'
            f'<div id="bkl" class="lab abs" style="left:96px;top:622px;font-size:21px">BACK</div>'
            f'<div id="bk" class="r9 tab abs red" style="left:92px;top:654px;font-size:128px">{pdd.money(back)}</div>'
            + small_print(day["small_print"], "sp", "left:96px;top:832px;width:630px", 15.5)
            + '</div>'
            f'<div id="win">{tick("ht", 150, style="left:860px;top:430px")}'
            f'<div id="pc" class="r9 abs red" style="left:1040px;top:410px;font-size:236px;transform-origin:left center">'
            f'{calc["roi"][:-3]}%</div>'
            f'<div id="pcl" class="lab abs" style="left:868px;top:690px;font-size:26px;color:var(--lg)">{c["hook_sub"]}</div></div>'
            + bug() + endorse())
    exp = x.m("hundred_six", "end", -280)          # the count has landed; the panel floods out
    slam_at = x.word("n326", 0, -60)               # "three…" of three hundred and twenty-six
    if slam_at - (exp + 480) < 650:
        raise pdd.Halt(f"hook: only {slam_at - exp - 480:.0f} ms of stillness before +326% (need ~700)")
    full = "inset(0px 0px 0px 0px round 0px)"
    spec = [seq("#bgp", [(0, {"opacity": 0, "clipPath": pip}, "ease-out"), (280, {"opacity": .96, "clipPath": pip}),
                         (exp, {"opacity": .96, "clipPath": pip}, "cubic-bezier(0.65,0,0.35,1)"),
                         (exp + 480, {"opacity": 1, "clipPath": full})]),
            enter("#pip", 0, dx=-40, dy=0, dur=300),
            wipe("#ebb", 120, 280), enter("#ebt", 220, dx=-12, dy=0), enter("#dt", 330, dx=-12, dy=0), fade("#sp", 400, 400),
            enter("#tk0", x.m("five_dollars", off=-80), dy=14)]
    for i in range(1, len(day["selections"])):
        spec.append(enter(f"#tk{i}", x.m("every_sel", off=-80) + 280 * (i - 1), dy=14))
    spec += [fade("#tkl", x.m("every_sel", off=-80) + 280 * (len(day["selections"]) - 1) + 120, 300),
             enter("#stl", x.m("twentyfive", off=-260), dx=-12, dy=0), slam("#st", x.m("twentyfive", off=-60)),
             enter("#bkl", x.m("into", off=-80), dx=-12, dy=0),
             fade("#bk", x.m("hundred_six", off=-120), 200),
             count("#bk", x.m("hundred_six", off=-40), staked, back, 2, "$", "", 1200),
             fade("#bug", exp + 380, 400), fade("#end", exp + 480, 400),
             slam("#pc", slam_at)] + stamp("ht", slam_at + 360) + [enter("#pcl", slam_at + 700, dx=-12, dy=0)]
    return page(body, spec, "PPD hook", alpha=True), {"exp": exp, "slam": slam_at}


def c_lower_thirds(promo, day, T, t0):
    """Shot 3 — 'Gordon · Practical Punting', then the same panel becomes PPD CLUB, and SINCE 1995 stamps on his year."""
    c, x = promo["copy"], Ctx(T, t0)
    # the red bar is INSET with charcoal either side: a red edge straight against the grass is smeared orange by 4:2:0
    # video (the first cut's orange scan, 25 Oct)
    body = (f'<div id="lt" class="abs panel" style="left:48px;bottom:60px;width:516px;height:142px;border-radius:16px;'
            f'overflow:hidden;transform-origin:left center">'
            f'<div class="abs" style="left:8px;top:10px;width:8px;height:122px;background:var(--red);border-radius:3px"></div>'
            f'<div id="l1" class="abs" style="left:30px;top:24px"><div class="r9" style="font-size:56px">{c["gordon_name"]}</div>'
            f'<div class="lab" style="font-size:20px;margin-top:12px;color:var(--lg)">{c["gordon_org"]}</div></div>'
            f'<div id="l2" class="abs" style="left:30px;top:24px;width:440px">'
            + tick("lt", 54, style="left:0;top:2px")
            + f'<div id="l2n" class="r9 abs" style="left:70px;top:6px;font-size:48px">{c["ppd_name"]}</div>'
            f'<div class="lab abs" style="left:0;top:74px;font-size:20px;color:var(--lg)">{c["ppd_sub"]}</div>'
            f'<div id="since" class="pill abs" style="left:316px;top:13px;font-size:16px;padding:8px 12px;background:var(--red);color:#fff;'
            f'transform-origin:center">{c["since"]}</div></div></div>')
    on = x.m("im_gordon", off=-100)
    sw = x.m("ppd_club", off=-120)
    spec = [A("#lt", [{"opacity": 0, "transform": "scaleX(0.2)"}, {"opacity": 1, "transform": "scaleX(1)"}], on, 340),
            seq("#l1", [(on + 140, {"opacity": 0, "transform": "translate(-14px,0px)"}, EASE_ENTER),
                        (on + 400, {"opacity": 1, "transform": "translate(0px,0px)"}),
                        (sw - 200, {"opacity": 1, "transform": "translate(0px,0px)"}, "ease-in"),
                        (sw + 20, {"opacity": 0, "transform": "translate(0px,-30px)"})]),
            A("#l2", [{"opacity": 0}, {"opacity": 1}], sw, 10)] + stamp("lt", sw) + [
            enter("#l2n", sw + 120, dx=-14, dy=0), enter("#l2 .lab", sw + 240, dx=-14, dy=0),
            slam("#since", x.m("since", off=-60))]
    return page(body, spec, "PPD lower thirds", alpha=True)


def c_types(promo, day, T, t0):
    """Shot 4 — the PPD logo stamps in (the official artwork, pieced), settles into the corner, and the five bet types
    tick on as Gordon names them (the two he does not name land between, 300-420 ms apart)."""
    c, x = promo["copy"], Ctx(T, t0)
    W, H = 650, 150                               # the official 1040x240 wordmark at 150 px tall
    k = H / 240
    cx, cy, r = 137 * k, 120 * k, 82 * k          # its tick circle, measured on the artwork
    left, top = (1920 - W) / 2, 440
    s = 48 / H
    tx, ty = 1920 - 140 - W * s - left, 74 - top
    logo = (f'<div id="lg" class="abs" style="left:{left:.1f}px;top:{top}px;width:{W}px;height:{H}px;transform-origin:0 0">'
            f'<img id="lgt" class="abs" src="assets/ppd-wordmark.png" style="left:0;top:0;width:{W}px;height:{H}px;'
            f'clip-path:circle({r + 2:.1f}px at {cx:.1f}px {cy:.1f}px);transform-origin:{cx:.1f}px {cy:.1f}px">'
            f'<img id="lgw" class="abs" src="assets/ppd-wordmark.png" style="left:0;top:0;width:{W}px;height:{H}px;'
            f'clip-path:inset(0px 0px 0px {cx + r + 6:.1f}px)"></div>')
    names = [r_[0] for r_ in c["types"]]
    lands = {0: x.m("t_tbb", off=-80), 1: x.m("t_long", off=-80), 4: x.m("t_ra", off=-80)}
    gap = (lands[4] - lands[1]) / 3
    if gap < 240:
        raise pdd.Halt(f"bet types: only {gap:.0f} ms between the unnamed rows (need >= 240)")
    lands[2], lands[3] = lands[1] + gap, lands[1] + 2 * gap
    rows, spec_rows = "", []
    for i, (nm, desc) in enumerate(c["types"]):
        y = 334 + i * 100
        rows += (f'<div id="ty{i}" class="abs" style="left:140px;top:{y}px;width:1640px;height:88px">'
                 + tick(f"tt{i}", 56, style="left:0;top:16px")
                 + f'<div class="r8 abs" style="left:84px;top:20px;font-size:44px">{_h.escape(nm)}</div>'
                 f'<div class="abs lg" style="left:640px;top:28px;font-size:29px">{_h.escape(desc)}</div>'
                 f'<div id="tl{i}" class="abs" style="left:0;bottom:-6px;width:1640px;height:1px;background:var(--div);transform-origin:left center"></div></div>')
        spec_rows += [enter(f"#ty{i}", lands[i], dx=-18, dy=0)] + stamp(f"tt{i}", lands[i] - 40) + [wipe(f"#tl{i}", lands[i] + 60, 400)]
    head = (f'<div id="hd" class="r9 abs" style="left:140px;top:170px;font-size:104px;transform-origin:left center">'
            f'<span class="red">{c["types_head"][0]}</span> bet types.</div>')
    body = eyebrow(c["types_eyebrow"]) + endorse() + logo + head + rows
    spec = [slam("#lgt", 120, 380, 1.25),
            A("#lgw", [{"clipPath": f"inset(0px {W}px 0px {cx + r + 6:.1f}px)"}, {"clipPath": f"inset(0px 0px 0px {cx + r + 6:.1f}px)"}],
              420, 520, EASE_DATA),
            travel("#lg", 1350, "translate(0px,0px) scale(1)", f"translate({tx:.1f}px,{ty:.1f}px) scale({s:.4f})", 620),
            wipe("#ebb", 1700, 280), enter("#ebt", 1810, dx=-12, dy=0), fade("#end", 1900, 400),
            slam("#hd", x.m("five_kinds", off=-60))] + spec_rows
    if spec[-1]["opts"]["delay"] + 600 > (T["real_day"]["pb"] - t0) * 1000 - 1500:
        raise pdd.Halt("bet types: the last row lands less than 1.5 s before the card leaves")
    return page(body, spec, "PPD bet types")


def c_realday(promo, day, T, t0):
    """Shot 5 — over the race-day crowd: A REAL DAY / Cox Plate Day / the date stamp (the brief allows it here)."""
    c, x = promo["copy"], Ctx(T, t0)
    body = (f'<div id="scrim" class="abs" style="left:0;top:560px;width:1920px;height:520px;'
            f'background:linear-gradient(to top,rgba(30,31,34,.92),rgba(30,31,34,0))"></div>'
            + eyebrow(c["realday_eyebrow"], "eb", left=140, top=742, px=26)
            + f'<div id="rt" class="r9 abs" style="left:134px;top:790px;font-size:118px;transform-origin:left center;'
            f'text-shadow:0 4px 24px rgba(0,0,0,.35)">{day["label"]}</div>'
            f'<div id="rd" class="lab abs" style="left:140px;top:930px;font-size:26px;color:var(--lg)">{day["date_label"].upper()}</div>')
    spec = [fade("#scrim", 0, 300), wipe("#ebb", x.m("real_day", off=-120), 280), enter("#ebt", x.m("real_day", off=-20), dx=-12, dy=0),
            slam("#rt", x.m("real_day", off=100)),           # the day's name lands as he introduces it, so it can HOLD
            enter("#rd", x.m("real_day", off=250), dx=-12, dy=0)]
    return page(body, spec, "PPD real day super", alpha=True)


# ================================================================== PROOF
def c_before_after(promo, day, T, t0):
    """Shots 6-7 — BEFORE THE RACE (the bet in full, what we wrote, the worry) on his words; then a clean split:
    AFTER THE RACE, the tick, WIN PAID $9.50 (red, the payoff) and PLACE PAID $2.90."""
    c, x = promo["copy"], Ctx(T, t0)
    bb = next(s for s in day["selections"] if s["horse"] == day["best_bet"]["horse"])
    q = day["best_bet"]["quote"]
    qwords = q.split()
    spoken = T["quote"]["words"]
    if [w.strip(",.").lower() for w, _, _ in spoken] != [w.strip(",.").lower() for w in qwords]:
        raise pdd.Halt("before/after: the quote on screen is not the words Gordon says for it")
    qhtml = "".join(f'<span id="qw{i}" style="opacity:0">{_h.escape(w)}{"&rdquo;" if i == len(qwords) - 1 else " "}</span>'
                    for i, w in enumerate(qwords))
    split = x.m("it_won", "pb")
    body = (f'<div id="bg" class="abs" style="left:140px;top:0;width:800px;height:900px">'
            f'<div id="bh" class="r9 abs" style="left:0;top:178px;font-size:62px">{c["before_head"]}</div>'
            f'<div id="bs" class="lab abs" style="left:2px;top:256px;font-size:19px">{c["before_sub"]}</div>'
            f'<div id="bt" class="pill abs" style="left:0;top:318px;font-size:19px;padding:8px 16px;background:var(--red)">{bb["tag"]}</div>'
            f'<div class="abs" style="left:0;top:372px;font-size:40px;font-weight:700;white-space:nowrap">'
            f'<span id="b1">{bb["meeting"]} Race {bb["race"]}</span><span id="b2"> no.{bb["no"]}</span></div>'
            f'<div id="b3" class="r9 abs" style="left:-3px;top:428px;font-size:82px;transform-origin:left center">{bb["horse"]}</div>'
            f'<div id="qc" class="abs" style="left:0;top:548px;width:780px;padding:26px 34px 28px 92px;background:var(--card);border-radius:16px">'
            f'<div class="r9 abs red" style="left:26px;top:14px;font-size:96px;line-height:1">&ldquo;</div>'
            f'<div style="font-size:34px;font-style:italic;line-height:1.3">{qhtml}</div></div>'
            f'<div id="wl" class="abs" style="left:0;top:742px;display:flex;align-items:center;gap:14px">'
            f'<svg viewBox="0 0 24 24" style="width:26px;height:26px"><path d="M5 22V3h11l-1.5 4L16 11H7v11z" fill="#8A8B8F"/></svg>'
            f'<span class="lab" style="font-size:20px">{c["worry_label"]}</span></div>'
            f'<div id="wt" class="abs lg" style="left:40px;top:780px;font-size:32px">{_h.escape(day["best_bet"]["worry"])}</div></div>'
            f'<div id="dv" class="abs" style="left:980px;top:178px;width:3px;height:660px;background:var(--red);transform-origin:top center"></div>'
            f'<div id="ag" class="abs" style="left:1040px;top:0;width:740px;height:900px">'
            f'<div id="ah" class="r9 abs" style="left:0;top:178px;font-size:62px">{c["after_head"]}</div>'
            + tick("at", 120, style="left:0;top:296px")
            + f'<div id="a1" class="r9 abs" style="left:150px;top:298px;font-size:118px;transform-origin:left center">1st</div>'
            f'<div id="a2" class="lab abs" style="left:154px;top:424px;font-size:20px;color:var(--lg)">{c["after_result"]}</div>'
            f'<div id="tw" class="abs" style="left:0;top:500px;width:360px;height:216px;background:var(--red);border-radius:16px;transform-origin:center">'
            f'<div class="lab abs" style="left:30px;top:30px;font-size:20px;color:#fff">WIN PAID</div>'
            f'<div class="r9 abs" style="left:26px;top:76px;font-size:108px">{pdd.money(bb["win"])}</div></div>'
            f'<div id="tp" class="abs" style="left:380px;top:500px;width:360px;height:216px;background:var(--card);border-radius:16px">'
            f'<div class="lab abs" style="left:30px;top:30px;font-size:20px;color:var(--lg)">PLACE PAID</div>'
            f'<div class="r9 abs" style="left:26px;top:76px;font-size:108px">{pdd.money(bb["place"])}</div></div>'
            f'<div id="basis" class="abs sg" style="left:0;top:744px;font-size:24px">{day["dividend_basis"]}</div></div>')
    cb, cs = chrome(f'{day["label"].upper()} · {day["date_label"].upper()}', day["small_print"], split + 300)
    spec = cs + [A("#bg", [{"transform": "translateX(430px)"}, {"transform": "translateX(430px)"}], 0, 10),
                 enter("#bh", 120, dx=-14, dy=0), enter("#bs", 240, dx=-14, dy=0),
                 slam("#bt", x.m("our_best_bet", off=60)),
                 enter("#b1", x.m("bb_meeting", off=-80), dy=12), enter("#b2", x.m("bb_no", off=-80), dy=12),
                 slam("#b3", x.m("bb_horse", off=-60)),
                 enter("#qc", x.m("quote", off=-500), dy=14)]
    for i, (_, st, en) in enumerate(spoken):          # the quote appears word by word ON his words
        spec.append(A(f"#qw{i}", [{"opacity": 0}, {"opacity": 1}], (st - t0) * 1000 - 40, 120, "linear"))
    spec += [enter("#wl", x.m("flagged", off=-80), dx=-12, dy=0), enter("#wt", x.m("worry", off=-60), dx=-12, dy=0),
             # the split: BEFORE travels into its half, the red line draws, AFTER builds
             travel("#bg", split, "translateX(430px)", "translateX(0px)", 560),
             wipe("#dv", split + 200, 500, "Y"), enter("#ah", split + 320, dx=-14, dy=0)] + stamp("at", x.m("won", off=-60)) + [
             slam("#a1", x.m("won", off=120)), enter("#a2", x.m("won", off=400), dx=-10, dy=0),
             slam("#tw", x.m("win_div", off=-60)), enter("#tp", x.m("win_div", off=220), dy=16),
             fade("#basis", x.m("win_div", off=560), 400)]
    if x.m("win_div", off=-60) - (x.m("won", off=400) + 260) < 600:
        raise pdd.Halt("before/after: no beat before WIN PAID")
    return page(cb + body, spec, "PPD before and after")


def c_rows(promo, day, T, t0):
    """Shots 8-9 — all five selections, in full. The Best Bet is already ticked; Juja Kibo then Proxima Dea STAMP
    as he names them, their dividends land as he says them; the two misses fade to grey with their finish. No cross."""
    c, x = promo["copy"], Ctx(T, t0)
    keys = {"Juja Kibo": ("s2_horse", "s2_div"), "Proxima Dea": ("s3_horse", "s3_div"),
            "Maidoff": ("m1_horse", "m1_fin"), "Arabian Rose": ("m2_horse", "m2_fin")}
    rows, spec = "", []
    for i, s in enumerate(day["selections"]):
        y = 170 + i * 130
        won = s["finish"] == 1
        first = i == 0
        tagc = "var(--red)" if s["type"] == "Today's Best Bet" else "var(--sg)"
        right = (f'<div id="rp{i}" class="abs" style="right:40px;top:22px;text-align:right">'
                 f'<div class="lab" style="font-size:16px">WIN PAID</div>'
                 f'<div class="r9 red" style="font-size:58px;margin-top:6px">{pdd.money(s["win"])}</div></div>'
                 + tick(f"rk{i}", 62, style="right:250px;top:28px")) if won else \
            (f'<div id="rp{i}" class="r9 abs" style="right:40px;top:30px;font-size:58px;color:var(--sg)">'
             f'{s["finish"]}{"th" if 10 <= s["finish"] % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(s["finish"] % 10, "th")}</div>')
        rows += (f'<div id="r{i}" class="abs" style="left:140px;top:{y}px;width:1640px;height:118px;background:var(--card);border-radius:14px;overflow:hidden">'
                 f'<div id="re{i}" class="abs" style="left:0;top:0;width:7px;height:118px;background:var(--red);transform-origin:top center"></div>'
                 f'<div id="rc{i}" class="abs" style="inset:0">'
                 f'<div class="lab abs" style="left:40px;top:22px;font-size:17px;color:{tagc}">{_h.escape(s["tag"])}</div>'
                 f'<div id="rn{i}" class="r8 abs" style="left:38px;top:52px;font-size:44px">{_h.escape(pdd.bet_name(s))}</div></div>'
                 f'{right}</div>')
        t_in = 120 + 280 * i
        spec.append(enter(f"#r{i}", t_in, dx=-24, dy=0))
        if first:            # already a winner when the card opens: shown lit and ticked from the start
            spec += [wipe("#re0", t_in + 200, 300, "Y")] + stamp("rk0", t_in + 220) + [fade("#rp0", t_in + 260, 300)]
            continue
        spec.append(A(f"#rc{i}", [{"opacity": .38}, {"opacity": .38}], 0, 10))
        k_name, k_res = keys[s["horse"]]
        if won:
            spec += [A(f"#rc{i}", [{"opacity": .38}, {"opacity": 1}], x.m(k_name, off=-120), 260, "ease-out"),
                     wipe(f"#re{i}", x.m(k_name, off=-100), 300, "Y")] + stamp(f"rk{i}", x.m(k_name, off=-60)) + [
                     enter(f"#rp{i}", x.m(k_res, off=-80), dx=22, dy=0)]
            spec.append(A(f"#rk{i}", [{"opacity": 0}, {"opacity": 1}], x.m(k_name, off=-60), 10))
        else:
            spec += [A(f"#rn{i}", [{"color": "#FFFFFF"}, {"color": "#7A7B80"}], x.m(k_name, off=-120), 420, "ease-out"),
                     A(f"#rc{i}", [{"opacity": .38}, {"opacity": 1}], x.m(k_name, off=-120), 420, "ease-out"),
                     A(f"#r{i}", [{"backgroundColor": "#2C2D31"}, {"backgroundColor": "#25262A"}], x.m(k_name, off=-120), 420, "ease-out"),
                     enter(f"#rp{i}", x.m(k_res, off=-80), dx=22, dy=0)]
    for i, s in enumerate(day["selections"]):          # hidden until their moment (a won row's tick, a result)
        if i:
            spec.insert(0, A(f"#rp{i}", [{"opacity": 0}, {"opacity": 0}], 0, 10))
            if s["finish"] == 1:
                spec.insert(0, A(f"#rk{i}", [{"opacity": 0}, {"opacity": 0}], 0, 10))
    cb, cs = chrome(c["rows_eyebrow"], day["small_print"], 300)
    return page(cb + rows, cs + spec, "PPD the five selections")


def c_strike(promo, day, T, t0):
    """Shot 10 — a panel beside Gordon: 3 FROM 5, five dots (three ticked, two grey), the 60.0% strike rate."""
    c, x = promo["copy"], Ctx(T, t0)
    won = [s["finish"] == 1 for s in day["selections"]]
    dots = ""
    for i, w in enumerate(won):
        style = f"left:{96 + i * 92}px;top:556px"
        dots += tick(f"sd{i}", 76, style=style) if w else \
            f'<div id="sd{i}" class="abs" style="{style};width:76px;height:76px;border-radius:50%;border:4px solid var(--mg)"></div>'
    body = (f'<div id="pp" class="abs panel" style="left:48px;top:250px;width:700px;height:680px"></div>'
            + eyebrow(f'{day["label"].upper()}', "eb", left=96, top=296, px=24)
            + f'<div id="n3" class="r9 abs" style="left:90px;top:350px;font-size:190px;transform-origin:left center">{sum(won)}</div>'
            f'<div id="n3l" class="r8 abs" style="left:236px;top:384px;font-size:50px;line-height:1.05">WINNERS<br>FROM {len(won)}</div>'
            + dots
            + f'<div id="srn" class="r9 abs red" style="left:96px;top:676px;font-size:72px">{day["calc"]["strike_rate"]}</div>'
            f'<div id="srl" class="lab abs" style="left:330px;top:704px;font-size:22px;color:var(--lg)">{c["strike_sub"]}</div>'
            + small_print(day["small_print"], "sp", "left:96px;top:800px;width:620px", 15.5))
    a = x.m("three_from_five", off=-60)
    spec = [enter("#pp", 0, dx=-40, dy=0, dur=300), wipe("#ebb", 120, 280), enter("#ebt", 220, dx=-12, dy=0), fade("#sp", 300, 400),
            slam("#n3", a), enter("#n3l", a + 120, dx=-12, dy=0)]
    k = 0
    for i, w in enumerate(won):
        t = a + 420 + 280 * i
        if w:
            spec += stamp(f"sd{i}", t)
            k += 1
        else:
            spec.append(fade(f"#sd{i}", t, 260))
    spec += [enter("#srn", x.m("covered", off=-60), dy=12), enter("#srl", x.m("covered", off=100), dx=-12, dy=0)]
    return page(body, spec, "PPD 3 from 5", alpha=True)


def c_bank(promo, day, T, t0):
    """Shot 11 — the bank as a bar; the $5 bet as the thin red sliver it really is (0.5%); the 1% race limit."""
    c, x = promo["copy"], Ctx(T, t0)
    bw = 1640
    bet_w = bw * day["stake"] / day["bank"]
    lim_w = bw * day["race_limit_pct"] / 100
    body = (f'<div id="hd" class="r9 abs" style="left:136px;top:166px;font-size:116px;transform-origin:left center">{c["bank_head"]}</div>'
            f'<div id="bl" class="lab abs" style="left:140px;top:420px;font-size:22px">{c["bank_label"]}</div>'
            f'<div id="bv" class="r9 abs" style="right:140px;top:380px;font-size:72px">{pdd.money(day["bank"], 0)}</div>'
            f'<div id="bar" class="abs" style="left:140px;top:466px;width:{bw}px;height:110px;background:#3A3B40;border-radius:10px;transform-origin:left center"></div>'
            f'<div id="sl" class="abs" style="left:140px;top:466px;width:{bet_w:.1f}px;height:110px;background:var(--red);transform-origin:left center"></div>'
            f'<div id="lim" class="abs" style="left:140px;top:458px;width:{lim_w:.1f}px;height:126px;border:2px dashed #FFFFFF;border-radius:3px"></div>'
            f'<div id="ld" class="abs" style="left:142px;top:576px;width:3px;height:44px;background:var(--red);transform-origin:top center"></div>'
            f'<div id="b5" class="r9 abs red" style="left:136px;top:630px;font-size:104px;transform-origin:left center">{pdd.money(day["stake"], 0)}</div>'
            f'<div id="b5p" class="r8 abs" style="left:140px;top:752px;font-size:44px">{day["calc"]["bet_pct"]} <span class="sg" style="font-size:30px">{c["bet_label"]}</span></div>'
            f'<div id="l10" class="r9 abs" style="left:700px;top:630px;font-size:104px;transform-origin:left center">{day["calc"]["race_limit"]}</div>'
            f'<div id="l10p" class="r8 abs" style="left:704px;top:752px;font-size:44px">{day["race_limit_pct"]}% <span class="sg" style="font-size:30px">{c["race_label"]}</span></div>')
    cb, cs = chrome(c["bank_eyebrow"])
    spec = cs + [slam("#hd", 160), enter("#bl", 420, dx=-12, dy=0), fill("#bar", 520, 760),
                 A("#sl", [{"opacity": 0}, {"opacity": 0}], 0, 10), A("#lim", [{"opacity": 0}, {"opacity": 0}], 0, 10),
                 fade("#sl", x.m("bet5", off=-120), 200), wipe("#ld", x.m("bet5", off=-20), 220, "Y"), slam("#b5", x.m("bet5", off=60)),
                 enter("#b5p", x.m("half_pc", off=-60), dx=-12, dy=0),
                 slam("#bv", x.m("bank1000", off=-60)),
                 fade("#lim", x.m("small_stakes", off=-100), 300), slam("#l10", x.m("small_stakes", off=60)),
                 enter("#l10p", x.m("small_stakes", off=340), dx=-12, dy=0)]
    return page(cb + body, spec, "PPD bank bar")


def c_tiles(promo, day, T, t0):
    """Shot 12 — the three returns flip in as he says win / each way / place; then a tick on each: all three in profit."""
    c, x = promo["copy"], Ctx(T, t0)
    cc = day["calc"]
    tiles = [("win", "WIN", "t_win", True), ("each_way", "EACH WAY", "t_ew", False), ("place", "PLACE", "t_place", False)]
    body, spec = "", []
    for i, (k, lab, cue, hero) in enumerate(tiles):
        left = 140 + i * 560
        bg, fg, num, sub = ("var(--red)", "#fff", "#fff", "rgba(255,255,255,.88)") if hero else ("var(--off)", "#1E1F22", "var(--red)", "#5A5B5F")
        body += (f'<div class="abs" style="left:{left}px;top:236px;width:520px;height:440px;perspective:1400px">'
                 f'<div id="tile{i}" class="abs" style="inset:0;background:{bg};border-radius:20px;transform-origin:50% 0%;backface-visibility:hidden">'
                 f'<div class="lab abs" style="left:40px;top:40px;font-size:19px;color:{fg}">{pdd.money(day["stake"], 0)} {lab} ON ALL {len(day["selections"])}</div>'
                 f'<div class="r9 abs" style="left:34px;top:120px;font-size:112px;color:{num}">{cc[k]["roi"]}</div>'
                 f'<div class="abs" style="left:40px;top:276px;font-size:28px;font-weight:700;color:{sub}">{pdd.money(cc[k]["staked"], 0)} staked</div>'
                 f'<div class="abs" style="left:40px;top:318px;font-size:28px;font-weight:700;color:{sub}">{pdd.money(cc[k]["back"])} back</div>'
                 + tick(f"tk{i}", 74, circle="#FFFFFF" if hero else "var(--red)", mark="#F44336" if hero else "#FFFFFF",
                        style="right:34px;top:30px")
                 + '</div></div>')
        spec += [A(f"#tile{i}", [{"opacity": 0, "transform": "rotateX(-88deg)"}, {"opacity": 1, "transform": "rotateX(-30deg)", "offset": .4},
                                 {"opacity": 1, "transform": "rotateX(0deg)"}], x.m(cue, off=-100), 460, EASE_ENTER),
                 A(f"#tk{i}", [{"opacity": 0}, {"opacity": 0}], 0, 10)]
        tt = x.m("all_three", off=-40) + 280 * i
        spec += [A(f"#tk{i}", [{"opacity": 0}, {"opacity": 1}], tt, 10)] + stamp(f"tk{i}", tt)
    body += f'<div id="alt" class="abs sg" style="left:140px;top:712px;font-size:26px">Three alternatives, not added together.</div>'
    cb, cs = chrome(c["tiles_eyebrow"], day["small_print"], 300)
    spec += [fade("#alt", x.m("t_place", off=600), 400)]
    return page(cb + body, cs + spec, "PPD three returns")


# ================================================================== EBOOK
def c_book(promo, day, T, t0, pages):
    """Shot 13 — the real free guide floats in 3D (cover readable as he says its title), then three leaves turn
    and the book lies open at the Cox Plate Day spread (pages 6-7)."""
    c, x = promo["copy"], Ctx(T, t0)
    ph, pw = 680, round(680 * 594.96 / 841.92)
    flip0 = x.m("book_title", "end", -100)          # the cover is read while he names it, then the pages turn
    leaves = ""
    for k in range(3):           # leaf k: front = page 2k+1, back = page 2k+2; top leaf highest in Z
        z = 3 - k
        leaves += (f'<div id="lf{k}" class="abs" style="left:0;top:0;width:{pw}px;height:{ph}px;transform-style:preserve-3d;'
                   f'transform-origin:0 50%;transform:rotateY(0deg) translateZ({z}px)">'
                   f'<img src="{pages[2 * k]}" class="abs" style="inset:0;width:{pw}px;height:{ph}px;backface-visibility:hidden'
                   f'{";box-shadow:0 0 0 1px rgba(255,255,255,.16)" if k == 0 else ""}">'   # the charcoal cover's edge on the charcoal canvas
                   f'<img src="{pages[2 * k + 1]}" class="abs" style="inset:0;width:{pw}px;height:{ph}px;backface-visibility:hidden;'
                   f'transform:rotateY(180deg)"></div>')
    # 🔴 NEVER put opacity on the preserve-3d element: any opacity there FLATTENS the 3D, the leaves then paint in DOM
    # order (the last leaf on top) and the cover disappears (found on the first cut, 25 Oct). The fade lives on #bookf,
    # which also carries the perspective; #book only ever animates its transform.
    body = (f'<div id="bookf" class="abs" style="left:0;top:0;width:1920px;height:1080px;perspective:2400px">'
            f'<div id="book" class="abs" style="left:960px;top:{170}px;width:{pw}px;height:{ph}px;transform-style:preserve-3d">'
            f'<div class="abs" style="left:0;top:0;width:{pw}px;height:{ph}px;box-shadow:0 30px 80px rgba(0,0,0,.55)"></div>'
            f'<img src="{pages[6]}" class="abs" style="left:0;top:0;width:{pw}px;height:{ph}px">'
            f'{leaves}</div></div>'
            f'<div id="tag" class="pill abs" style="left:140px;top:180px;font-size:20px;padding:10px 18px;border:2px solid var(--red);color:var(--red)">{c["book_tag"]}</div>')
    cb, cs = chrome("FROM THE PPD CLUB")
    h = -pw / 2
    # ONE animation for the book (seq): it floats in angled, drifts squarer while he names it, then swings square and
    # slides so the open spread sits centred, while three leaves turn 300 ms apart
    spec = cs + [fade("#bookf", 0, 500), seq("#book", [
        (0, {"transform": f"translateX({h:.0f}px) translateY(60px) rotateY(-34deg) rotateX(6deg)"}, EASE_ENTER),
        (700, {"transform": f"translateX({h:.0f}px) translateY(0px) rotateY(-22deg) rotateX(4deg)"}, "ease-in-out"),
        (flip0, {"transform": f"translateX({h:.0f}px) translateY(0px) rotateY(-14deg) rotateX(4deg)"}, "cubic-bezier(0.45,0,0.2,1)"),
        (flip0 + 900, {"transform": "translateX(0px) translateY(0px) rotateY(0deg) rotateX(8deg)"})]),
        enter("#tag", 300, dx=-12, dy=0)]
    for k in range(3):
        z = 3 - k
        spec.append(A(f"#lf{k}", [{"transform": f"rotateY(0deg) translateZ({z}px)"}, {"transform": f"rotateY(-180deg) translateZ({z}px)"}],
                      flip0 + 120 + 300 * k, 620, "cubic-bezier(0.4,0,0.2,1)"))
    return page(cb + body, spec, "PPD free guide"), {"flip0": flip0, "spread": flip0 + 120 + 600 + 620}


def chip(idn, label, kind, style):
    """A saddlecloth chip. Outer div (id) is for TRAVEL; inner div (id + 'i') is for SLAM — two elements, so the
    two transforms never fight (see seq())."""
    if kind == "top":
        b, fg, bd = "var(--red)", "#fff", "var(--red)"
    elif kind == "res":
        b, fg, bd = "#fff", "#1E1F22", "#fff"
    else:
        b, fg, bd = "#3A3B40", "#8A8B8F", "#3A3B40"
    w = 96 if kind == "top" else 62          # the 3rd-placed runner sits IN the field column, at the field's width
    return (f'<div id="{idn}" class="abs" style="{style};width:{w}px;height:76px">'
            f'<div id="{idn}i" class="r9" style="width:{w}px;height:76px;border-radius:12px;background:{b};'
            f'border:3px solid {bd};color:{fg};display:flex;align-items:center;justify-content:center;font-size:{40 if kind != "field" else 28}px">'
            f'{label}</div></div>')


def c_trifecta(promo, day, T, t0):
    """Shot 14 — teaches the bet with the sound off: the top two lock into 1st and 2nd, then swap for the other way
    round; the field fills 3rd and the combinations TICK to 2 x runners - 4; the real result lights; 3 races from 3."""
    c, x = promo["copy"], Ctx(T, t0)
    ex, tm = day["calc"]["tri_ex"], day["calc"]["trifecta"]
    a, b = ex["top_two"]
    nf = ex["runners"] - 2
    third = ex["result"][2]
    X1, X2, X3 = 140, 260, 400            # 1st, 2nd, 3rd column left edges
    RA, RB = 370, 470                     # row tops
    SX, SY = 1180, 290                    # where the top two first appear
    fpos = lambda j: X3 + j * 70
    res_j = nf // 2                       # the field chip that turns out to be 3rd (the field's numbers are not in the brief)
    body = (f'<div id="hd" class="r9 abs" style="left:136px;top:150px;font-size:76px;transform-origin:left center">{c["tri_head"]}</div>'
            f'<div id="cost" class="pill abs" style="right:140px;top:166px;font-size:20px;padding:10px 18px;background:var(--card);color:var(--lg)">{c["tri_cost"]}</div>'
            f'<div id="rl" class="lab abs" style="left:140px;top:262px;font-size:22px;color:var(--lg)">{ex["meeting"].upper()} RACE {ex["race"]} · {ex["runners"]} RUNNERS</div>'
            f'<div id="colh" class="abs lab" style="left:0;top:322px;font-size:20px;width:1920px;height:30px">'
            f'<span class="abs" style="left:{X1 + 22}px">1ST</span><span class="abs" style="left:{X2 + 20}px">2ND</span>'
            f'<span class="abs" style="left:{X3}px">3RD — {c["tri_field"]}</span></div>'
            f'<div id="tpl" class="lab abs" style="left:{SX}px;top:{SY - 40}px;font-size:18px;color:var(--lg)">{c["tri_top"]}</div>'
            + chip("ca", a, "top", f"left:{SX}px;top:{SY}px") + chip("cb", b, "top", f"left:{SX + 116}px;top:{SY}px")
            + chip("cb2", b, "top", f"left:{X2}px;top:{RA}px") + chip("ca2", a, "top", f"left:{X1}px;top:{RA}px"))
    win_row_y = RA if list(ex["result"][:2]) == [a, b] else RB
    for j in range(nf):
        body += chip(f"fa{j}", "", "field", f"left:{fpos(j)}px;top:{RA + 0}px") + chip(f"fb{j}", "", "field", f"left:{fpos(j)}px;top:{RB}px")
        if j == res_j:
            body += chip("fr", third, "res", f"left:{fpos(j)}px;top:{win_row_y}px")
    body += (f'<div id="rowa" class="abs" style="left:{X1 - 14}px;top:{RA - 10}px;width:{fpos(nf) - X1 + 20}px;height:96px;border:3px solid var(--red);border-radius:16px"></div>'
             f'<div id="rowb" class="abs" style="left:{X1 - 14}px;top:{RB - 10}px;width:{fpos(nf) - X1 + 20}px;height:96px;border:3px solid var(--red);border-radius:16px;opacity:0"></div>'
             f'<div class="abs" style="left:1180px;top:{RA - 6}px">'
             f'<div id="cn" class="r9 tab" style="font-size:120px">{ex["combos"]}</div>'
             f'<div id="cnl" class="lab" style="font-size:20px;margin-top:10px;color:var(--lg)">COMBINATIONS</div>'
             f'<div id="cnc" class="r8" style="font-size:36px;margin-top:12px">× {round(float(day["trifecta"]["unit"]) * 100)}¢ = {pdd.money(ex["cost"])}</div></div>')
    races = ""
    for i, r in enumerate(day["trifecta"]["races"]):
        races += (f'<div id="tr{i}" class="abs" style="left:{140 + i * 330}px;top:604px;height:56px;display:flex;align-items:center;gap:12px">'
                  + f'<div style="position:relative;width:44px;height:44px">{tick(f"trk{i}", 44, style="left:0;top:0")}</div>'
                  f'<span class="lab" style="font-size:19px;color:var(--w)">{r["meeting"].upper()} RACE {r["race"]}</span></div>')
    body += races
    body += (f'<div id="tt" class="abs" style="left:140px;top:688px;width:1640px;height:150px;background:var(--red);border-radius:18px;transform-origin:left center">'
             f'<div class="r9 abs" style="left:40px;top:28px;font-size:96px">{tm["roi"]}</div>'
             f'<div class="r9 abs" style="left:560px;top:34px;font-size:44px">TRIFECTA · {tm["hits"]} FROM {tm["races"]}</div>'
             f'<div class="abs" style="left:562px;top:92px;font-size:28px;font-weight:700;color:rgba(255,255,255,.9)">'
             f'{pdd.money(tm["cost"])} staked · {pdd.money(tm["back"])} back</div></div>')
    sp = day["small_print"]            # the stake basis is on the card itself, large: "50c A COMBINATION"
    cb, cs = chrome(c["tri_eyebrow"], sp, 300)
    move = lambda sel, fx, fy, tx_, ty_, ms: travel(sel, ms, f"translate({fx}px,{fy}px)", f"translate({tx_}px,{ty_}px)", 620)
    t_top = x.m("top_two", off=-60)
    t_lock = x.word("first_second", 0, -80)
    t_swap = x.m("either", off=-80)
    t_field = x.m("whole_field", off=-60)
    t_res = x.m("tri_day", off=-60)
    races_t = x.m("three_races", off=-60)
    if not (t_top + 600 < t_lock < t_swap - 500 < t_field - 900 < t_res - 1500):
        raise pdd.Halt(f"trifecta: the steps are too close together to read ({t_top:.0f}, {t_lock:.0f}, {t_swap:.0f}, {t_field:.0f}, {t_res:.0f} ms)")
    # the result row is the WINNING way round (the order the top two actually finished)
    win_row_a = list(ex["result"][:2]) == [a, b]
    dim = "#fb" if win_row_a else "#fa"
    spec = cs + [slam("#hd", 150), enter("#rl", x.m("top_two", off=-400), dx=-12, dy=0), fade("#colh", x.m("top_two", off=-300), 300),
                 slam("#cost", x.m("cost_down", off=-60)),
                 seq("#tpl", [(t_top, {"opacity": 0}), (t_top + 260, {"opacity": 1}), (t_lock, {"opacity": 1}), (t_lock + 300, {"opacity": 0})]),
                 slam("#cai", t_top), slam("#cbi", t_top + 280),
                 # lock into 1st and 2nd (row A)
                 move("#ca", 0, 0, X1 - SX, RA - SY, t_lock), move("#cb", 0, 0, X2 - SX - 116, RA - SY, t_lock + 140),
                 # either way round: copies appear on row A and CROSS into row B (b first, a second)
                 travel("#ca2", t_swap, "translate(0px,0px)", f"translate({X2 - X1}px,{RB - RA}px)", 680),
                 travel("#cb2", t_swap, "translate(0px,0px)", f"translate({X1 - X2}px,{RB - RA}px)", 680),
                 A("#rowa", [{"opacity": 0}, {"opacity": 0}], 0, 10)]
    for sel in ("#ca2", "#cb2"):
        spec.append(seq(sel, [(0, {"opacity": 0}), (t_swap, {"opacity": 0}), (t_swap + 10, {"opacity": 1}),
                              (t_res, {"opacity": 1}), (t_res + 400, {"opacity": .35 if win_row_a else 1})]))
    for j in range(nf):
        for row in ("#fa", "#fb"):
            t = t_field + 60 * j
            spec.append(travel(f"{row}{j}i", t, "translateY(-18px)", "translateY(0px)", 240))
            spec.append(seq(f"{row}{j}", [(0, {"opacity": 0}), (t, {"opacity": 0}), (t + 240, {"opacity": 1}),
                                         (t_res, {"opacity": 1}), (t_res + 400, {"opacity": .35 if row == dim else 1})]))
    spec += [fade("#cn", t_field, 120), ledger("#cn", t_field, list(range(2, ex["combos"] + 1, 2)), 60), fade("#cnl", t_field, 300),
             enter("#cnc", t_field + 60 * nf + 300, dx=-12, dy=0),
             # the real result lights: the winning way round, and the runner that ran 3rd
             fade("#rowa" if win_row_a else "#rowb", t_res, 300), slam("#fri", t_res + 200)]
    for i, r in enumerate(day["trifecta"]["races"]):
        tt = t_res + 700 + 280 * i
        spec += [enter(f"#tr{i}", tt - 80, dx=-12, dy=0)] + (stamp(f"trk{i}", tt) if r["hit"] else [])
    tile = races_t
    if tile - (t_res + 700 + 280 * 2 + 400) < 650:
        tile = t_res + 700 + 280 * 2 + 400 + 700
    spec.append(slam("#tt", tile, 340, 1.08))
    return page(cb + body, spec, "PPD field-for-third trifecta"), {"tile": tile}


def c_backing_two(promo, day, T, t0):
    """Shot 15 — the $10 stake splits by price into two bars beside the two horses; both arrows reach about the same
    collect; the real result; BACKING TWO +58.5%. The mid-roll tag 'FREE GUIDE · LINK BELOW' sits top right."""
    c, x = promo["copy"], Ctx(T, t0)
    ex, bm = day["calc"]["b2_ex"], day["calc"]["backing_two"]
    tot = float(day["backing_two"]["stake"])
    BX, BW = 760, 620
    wa, wb = BW * float(ex["a"]["stake"]) / tot, BW * float(ex["b"]["stake"]) / tot
    YA, YB = 352, 486
    win = ex["a"] if ex["winner"] == ex["a"]["no"] else ex["b"]
    body = (f'<div id="hd" class="r9 abs" style="left:136px;top:150px;font-size:76px;transform-origin:left center">{c["b2_head"]}</div>'
            f'<div id="mr" class="pill abs" style="right:140px;top:166px;font-size:20px;padding:10px 20px;background:var(--red);color:#fff;'
            f'display:flex;align-items:center;gap:12px">{c["midroll"][0]} · {c["midroll"][1]}'
            f'<svg viewBox="0 0 20 20" style="width:18px;height:18px"><path d="M4 7l6 6 6-6" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/></svg></div>'
            f'<div id="rl" class="lab abs" style="left:140px;top:272px;font-size:22px;color:var(--lg)">{ex["meeting"].upper()} RACE {ex["race"]}</div>'
            f'<div id="ha" class="r8 abs" style="left:140px;top:{YA + 10}px;font-size:46px">no.{ex["a"]["no"]} {_h.escape(ex["a"]["horse"])}</div>'
            f'<div id="hb" class="r8 abs" style="left:140px;top:{YB + 10}px;font-size:46px">no.{ex["b"]["no"]} {_h.escape(ex["b"]["horse"])}</div>'
            f'<div id="sl" class="lab abs" style="left:{BX}px;top:272px;font-size:20px;color:var(--lg)">{c["b2_split"]}</div>'
            f'<div id="b10" class="abs r9" style="left:{BX}px;top:{(YA + YB) // 2}px;width:{BW}px;height:76px;background:#3A3B40;border-radius:10px;'
            f'display:flex;align-items:center;padding-left:24px;font-size:40px;transform-origin:left center">{pdd.money(tot, 0)}</div>'
            f'<div id="ba" class="abs r9" style="left:{BX}px;top:{(YA + YB) // 2}px;width:{wa:.0f}px;height:76px;background:var(--red);border-radius:10px;'
            f'display:flex;align-items:center;padding-left:24px;font-size:40px">{pdd.money(ex["a"]["stake"], 0)}</div>'
            f'<div id="bb" class="abs r9" style="left:{BX + wa:.0f}px;top:{(YA + YB) // 2}px;width:{wb:.0f}px;height:76px;background:#F7F7F7;color:#1E1F22;'
            f'border-radius:10px;display:flex;align-items:center;padding-left:24px;font-size:40px">{pdd.money(ex["b"]["stake"], 0)}</div>'
            f'<svg class="abs" style="left:0;top:0;width:1920px;height:1080px;overflow:visible" viewBox="0 0 1920 1080">'
            f'<path id="aa" d="M{BX + wa + 18:.0f} {YA + 38} C 1420 {YA + 38}, 1400 {YA + 100}, 1452 {YA + 100}" stroke="#fff" stroke-width="4" fill="none" '
            f'stroke-dasharray="520" stroke-dashoffset="520" stroke-linecap="round"/>'
            f'<path id="ab" d="M{BX + wb + 18:.0f} {YB + 38} C 1400 {YB + 38}, 1400 {YA + 112}, 1452 {YA + 112}" stroke="#fff" stroke-width="4" fill="none" '
            f'stroke-dasharray="720" stroke-dashoffset="720" stroke-linecap="round"/></svg>'
            f'<div id="cb" class="abs" style="left:1470px;top:{YA + 20}px;width:310px;height:190px;background:var(--card);border-radius:16px;padding:24px 26px">'
            f'<div class="lab" style="font-size:17px;color:var(--lg);white-space:normal;line-height:1.4">ABOUT THE SAME COLLECT, WHICHEVER WINS</div>'
            f'<div id="cw" class="r8" style="font-size:30px;margin-top:16px;line-height:1.15;white-space:normal">no.{win["no"]} won<br>'
            f'<span class="red">{pdd.money(ex["back"])}</span> back</div></div>'
            f'<div id="tt" class="abs" style="left:140px;top:688px;width:1640px;height:150px;background:var(--red);border-radius:18px;transform-origin:left center">'
            f'<div class="r9 abs" style="left:40px;top:28px;font-size:96px">{bm["roi"]}</div>'
            f'<div class="r9 abs" style="left:500px;top:34px;font-size:44px">BACKING TWO · A WINNER IN {bm["hits"]} FROM {bm["races"]}</div>'
            f'<div class="abs" style="left:502px;top:92px;font-size:28px;font-weight:700;color:rgba(255,255,255,.9)">'
            f'{pdd.money(bm["staked"])} staked · {pdd.money(bm["back"])} back</div></div>')
    sp = day["small_print"]            # the stake basis is on the card itself, large: "$10 SPLIT BY PRICE"
    cb, cs = chrome(c["b2_eyebrow"], sp, 300)
    sp_ = x.word("stake_split", 2, -60)               # "split"
    mid = (YA + YB) // 2
    spec = cs + [slam("#hd", 150), enter("#mr", 900, dx=16, dy=0),
                 enter("#rl", x.m("two_horses", off=-300), dx=-12, dy=0),
                 enter("#ha", x.m("two_horses", off=-60), dx=-16, dy=0), enter("#hb", x.m("two_horses", off=220), dx=-16, dy=0),
                 fill("#b10", x.m("stake_split", off=-80), 520), enter("#sl", x.m("stake_split", off=-80), dx=-12, dy=0),
                 A("#ba", [{"opacity": 0}, {"opacity": 0}], 0, 10), A("#bb", [{"opacity": 0}, {"opacity": 0}], 0, 10),
                 A("#b10", [{"opacity": 1}, {"opacity": 0}], sp_, 120, "linear"),
                 A("#ba", [{"opacity": 0}, {"opacity": 1}], sp_, 10), A("#bb", [{"opacity": 0}, {"opacity": 1}], sp_, 10),
                 travel("#ba", sp_ + 40, "translate(0px,0px)", f"translate(0px,{YA - mid}px)", 620),
                 travel("#bb", sp_ + 40, "translate(0px,0px)", f"translate({-wa:.0f}px,{YB - mid}px)", 620),
                 draw("#aa", x.m("collect", off=-60), 520, 700), draw("#ab", x.m("collect", off=40), 720, 700),
                 enter("#cb", x.m("collect", off=500), dx=14, dy=0),
                 A("#cw", [{"opacity": 0}, {"opacity": 0}], 0, 10), fade("#cw", x.m("collect", off=1100), 300)]
    tile = x.m("collect", "end", 50)
    spec.append(slam("#tt", tile, 340, 1.08))
    return page(cb + body, spec, "PPD backing two"), {"tile": tile}


# ================================================================== OFFER
def c_honest(promo, day, T, t0):
    """Shot 16 — a calm panel beside Gordon on the wide shot. No slam: this is the plain-spoken beat."""
    c, x = promo["copy"], Ctx(T, t0)
    body = (f'<div id="hp" class="abs panel" style="left:48px;top:560px;width:500px;height:390px"></div>'
            + eyebrow(c["honest_eyebrow"], "eb", left=88, top=604, px=22)
            + f'<div id="h1" class="r8 abs" style="left:86px;top:658px;font-size:58px">{c["honest_line"][0]}</div>'
            f'<div id="h2" class="r8 abs lg" style="left:86px;top:730px;font-size:58px">{c["honest_line"][1]}</div>'
            f'<div id="h3" class="abs sg" style="left:88px;top:826px;width:430px;font-size:23px;line-height:1.35">'
            f'Past performance is not a reliable indicator of future results.</div>')
    spec = [fade("#hp", 0, 500, to=1), wipe("#ebb", 300, 400), fade("#ebt", 400, 500),
            enter("#h1", x.word("one_strong", 2, -100), dy=8, dur=500), enter("#h2", x.m("not_promise", off=-100), dy=8, dur=500),
            fade("#h3", x.m("no_method", off=-60), 500)]
    return page(body, spec, "PPD honest", alpha=True)


def c_trial(promo, day, T, t0):
    """Shot 17 — the 30-day risk-free trial: three steps land on his words, then the 30-day line draws, and
    FULL REFUND slams on 'refund'."""
    c, x = promo["copy"], Ctx(T, t0)
    o = promo["offer"]
    steps = c["steps"]
    st_t = [x.m("join", off=-80), x.m("full_access", off=-80), x.m("not_happy", off=-80)]
    body = (f'<div id="hd" class="r9 abs" style="left:136px;top:150px;font-size:96px;transform-origin:left center">'
            f'{c["trial_head"][0]} <span class="red">{c["trial_head"][1]}</span></div>')
    spec = []
    for i, (t, sub) in enumerate(steps):
        left = 140 + i * 560
        hero = i == 2
        body += (f'<div id="s{i}" class="abs" style="left:{left}px;top:300px;width:520px;height:250px;background:var(--card);border-radius:18px">'
                 f'<div class="r9 abs" style="left:32px;top:30px;width:64px;height:64px;border-radius:50%;background:var(--red);'
                 f'display:flex;align-items:center;justify-content:center;font-size:36px">{i + 1}</div>'
                 f'<div class="r9 abs" style="left:32px;top:124px;font-size:{42 if len(t) < 14 else 38}px">{t}</div>'
                 f'<div id="s{i}s" class="abs {"r9 red" if hero else "lg"}" style="left:32px;top:{180 if hero else 184}px;'
                 f'font-size:{44 if hero else 28}px;transform-origin:left center">{sub}</div></div>')
        spec.append(enter(f"#s{i}", st_t[i], dy=18))
        if not hero:
            spec.append(fade(f"#s{i}s", st_t[i] + 200 if i else x.m("you_pay", off=-80), 300))
    spec.append(A("#s2s", [{"opacity": 0}, {"opacity": 0}], 0, 10))
    spec.append(slam("#s2s", x.m("refund", off=-60)))
    body += (f'<div id="tl" class="abs" style="left:140px;top:676px;width:1640px;height:6px;background:var(--red);border-radius:3px;transform-origin:left center"></div>'
             f'<div id="d1" class="abs" style="left:140px;top:640px;width:20px;height:78px">'
             f'<div class="abs" style="left:-7px;top:29px;width:20px;height:20px;border-radius:50%;background:var(--red)"></div></div>'
             f'<div id="d1l" class="abs" style="left:140px;top:712px"><div class="r9" style="font-size:36px">{c["day1"][0]}</div>'
             f'<div class="lab" style="font-size:18px;margin-top:8px;color:var(--lg)">{c["day1"][1]}</div></div>'
             f'<div id="d30" class="abs" style="left:1767px;top:669px;width:20px;height:20px;border-radius:50%;background:var(--red)"></div>'
             f'<div id="d30l" class="abs" style="right:140px;top:712px;text-align:right"><div class="r9" style="font-size:36px">{c["day30"][0]}</div>'
             f'<div class="lab" style="font-size:18px;margin-top:8px;color:var(--lg)">{c["day30"][1]}</div></div>')
    spec += [slam("#hd", x.m("ready", off=200)),
             fade("#d1", st_t[1] + 300, 260), enter("#d1l", st_t[1] + 360, dx=-12, dy=0),
             fill("#tl", x.m("first30", off=-80), 900), fade("#d30", x.m("first30", off=760), 200), enter("#d30l", x.m("first30", off=820), dx=12, dy=0)]
    cb, cs = chrome(c["trial_eyebrow"])
    return page(cb + body, cs + spec, "PPD risk-free trial")


def c_bonus(promo, day, T, t0):
    """Shot 18 — the Email Service, FREE, then a beat and the $110 slams with one restrained ring. The price card
    is a SEPARATE clip (c_price) so it can be swapped without touching this one."""
    c, x = promo["copy"], Ctx(T, t0)
    o = promo["offer"]
    hw = x.word("n110", 1, -60)          # "hundred"
    body = (f'<div id="en" class="r9 abs" style="left:136px;top:160px;font-size:72px;transform-origin:left center">{o["bonus_name"]}</div>'
            f'<div id="fr" class="pill abs" style="left:140px;top:258px;font-size:26px;padding:10px 22px;background:var(--red);color:#fff">{c["bonus_free"]}</div>'
            f'<div id="ring" class="abs" style="left:300px;top:300px;width:400px;height:400px;border-radius:50%;border:6px solid var(--red)"></div>'
            f'<div id="b110" class="r9 abs red" style="left:130px;top:322px;font-size:280px;transform-origin:30% 50%">{o["bonus_value"]}</div>'
            f'<div id="bl" class="r8 abs" style="left:860px;top:400px;font-size:64px">{c["bonus_saving"]}</div>'
            f'<div id="bd" class="abs lg" style="left:862px;top:486px;width:900px;font-size:30px;line-height:1.35">{_h.escape(o["bonus_detail"])}</div>')
    if hw - x.m("comes_free", "end", 0) < 500:
        raise pdd.Halt("bonus: no beat before the $110")
    spec = [enter("#en", x.m("email_service", off=-80), dx=-14, dy=0), slam("#fr", x.word("comes_free", 1, -60)),
            slam("#b110", hw, 360, 1.18),
            # ONE restrained ring: invisible, then a single pulse outward that fades — no burst, no sparkle
            A("#ring", [{"opacity": 0, "transform": "scale(.7)"}, {"opacity": .9, "transform": "scale(.74)", "offset": .04},
                        {"opacity": 0, "transform": "scale(1.55)"}], hw + 120, 760, "cubic-bezier(0.2,0,0,1)"),
            enter("#bl", hw + 380, dx=-14, dy=0), fade("#bd", x.m("five_types", off=-60), 400)]
    cb, cs = chrome(c["bonus_eyebrow"])
    return page(cb + body, cs + spec, "PPD email service bonus")


def c_price(promo, day, T, t0):
    """The SWAPPABLE price card (brief §3): a band that rises over the bonus card. On screen only; Gordon never says it."""
    o = promo["offer"]
    body = (f'<div id="pb" class="abs" style="left:140px;top:628px;width:1640px;height:212px;background:var(--card);border-radius:18px;'
            f'border-top:6px solid var(--red)">'
            f'<div class="r9 abs" style="left:40px;top:40px;font-size:104px">{o["price"]}</div>'
            f'<div class="r8 abs" style="left:330px;top:52px;font-size:44px">FOR {o["term"]}</div>'
            f'<div class="r8 abs red" style="left:330px;top:108px;font-size:44px">{o["per_day"]}</div>'
            f'<div class="abs sg" style="left:1060px;top:58px;width:540px;font-size:22px;line-height:1.4">{_h.escape(o["renewal"])}</div></div>')
    spec = [A("#pb", [{"opacity": 0, "transform": "translateY(60px)"}, {"opacity": 1, "transform": "translateY(0px)"}], 0, 420, EASE_ENTER)]
    return page(body, spec, "PPD price card (swappable)", alpha=True)


# ================================================================== END
def c_cta(promo, day, T, t0):
    """Shot 19 — the ask, beside Gordon: the trial button and the URL, then the soft ask for the free guide."""
    c, x = promo["copy"], Ctx(T, t0)
    o = promo["offer"]
    body = (f'<div id="cp" class="abs panel" style="left:48px;top:742px;width:600px;height:258px;border-radius:18px"></div>'
            f'<div id="cb" class="pill abs" style="left:82px;top:776px;font-size:24px;padding:16px 26px;background:var(--red);color:#fff;letter-spacing:.1em">{c["cta_main"]}</div>'
            f'<div id="cu" class="abs" style="left:84px;top:858px;font-size:34px;font-weight:700">{o["url"]}</div>'
            f'<div id="cg" class="pill abs" style="left:82px;top:920px;font-size:18px;padding:10px 18px;border:2px solid #fff;color:#fff">{c["cta_alt"]}</div>')
    on = x.m("start_trial", off=-120)
    spec = [enter("#cp", on - 200, dx=-30, dy=0, dur=300), slam("#cb", on, 340, 1.12), enter("#cu", on + 300, dx=-12, dy=0),
            enter("#cg", x.m("grab_guide", off=-80), dx=-12, dy=0)]
    return page(body, spec, "PPD call to action", alpha=True)


def c_closing(promo, day, T):
    """Shot 22 — the PPD logo, START MY RISK-FREE TRIAL (primary, filled) and GET THE FREE GUIDE (secondary,
    outlined), practicalpunting.com.au. Builds in ~1.3 s, then holds."""
    c, o = promo["copy"], promo["offer"]
    body = (f'<img id="cl" class="abs" src="assets/ppd-wordmark.png" style="left:{(1920 - 693) // 2}px;top:236px;height:160px" alt="Practical Punting Daily">'
            f'<div class="abs" style="left:0;top:500px;width:1920px;display:flex;justify-content:center;gap:36px">'
            f'<div id="k1" class="pill" style="font-size:34px;padding:26px 46px;background:var(--red);color:#fff;letter-spacing:.1em">{c["btn_trial"]}</div>'
            f'<div id="k2" class="pill" style="font-size:34px;padding:23px 43px;border:3px solid var(--red);color:#fff;letter-spacing:.1em">{c["btn_guide"]}</div></div>'
            f'<div id="ku" class="abs" style="left:0;top:680px;width:1920px;text-align:center;font-size:44px;font-weight:700">{o["url"]}</div>'
            + endorse())
    spec = [slam("#cl", 0, 420, 1.12), slam("#k1", 450), enter("#k2", 730, dy=16), enter("#ku", 1010, dy=12), fade("#end", 600, 400)]
    return page(body, spec, "PPD closing card")


CLOSING_BUILD = 1.3       # c_closing: the URL lands at 1010 + 260 ms
