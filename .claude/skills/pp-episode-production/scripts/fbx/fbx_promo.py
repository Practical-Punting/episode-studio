#!/usr/bin/env python3
"""fbx_promo.py — the FBX evergreen promo "What is FBX?": cues, cards, edit plan, assembly.

    python fbx_promo.py <job_dir> cues        print the measured cue sheet (overlay/promo-cues.json)
    python fbx_promo.py <job_dir> cards [names]  author + render the promo's cards (overlay/cards, overlay/clips)
    python fbx_promo.py <job_dir> assemble     output/FBX-PROMO-16x9.mp4 (+ overlay/promo-plan.json)

Data: overlay/fbx-promo.json (every on-screen word, every cue phrase). Timing: renders/words-forced.json
(fbx_align.py — the self-checking aligner). Spec: docs/FBX-PROMO-shot-script.md (22 shots).

REUSED FROM W01, NOT REBUILT: fbx_cards (page/CSS/chips/slam/footer/closing card/JOIN lower third),
fbx_render (seek-and-screenshot clips, alpha), fbx_assemble (the PP audio recipe, the measured makeup
gain, act()/card_chain()), fbx_data (phrase finder). EVERGREEN: no dates and no weekly results on
screen — the Saturday Report's dated header line is blurred in the image before it is ever shown.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fbx_cards as fc  # noqa: E402
import fbx_data as fd  # noqa: E402
import fbx_assemble as fa  # noqa: E402
from fbx_cards import A, fade, slam, wipe, page, fbx_logo, endorse, footer16  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

FADE = 0.3
B_ROLL = {  # slot -> (cue key, file in broll/, seconds on screen; None = until the next cue)
    "S1": ("runs_fifth", "broll-five-runners-strung-out-for-the-placings.mp4", 4.0),
    "S5": ("built", "broll-team-around-printouts.mp4", 5.0),
    "S7": ("one_week", "broll-punter-at-the-rail-with-the-form-guide.mp4", 5.0),
    "S12": ("standout", "broll-the-favourite-clear-at-the-furlong.mp4", None),
}


def load(job):
    return json.loads((job / "overlay" / "fbx-promo.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ cues (measured, never estimated)
def cue_sheet(job, cfg):
    """Every cue, ON THE FINISHED VIDEO'S CLOCK. 🔴 TWO CLOCKS: the words are measured on the presenter's clock;
    the finished file puts the title head (cfg title_head, 7.0 s) in front. The head is added HERE, ONCE, so every
    reader — cards, plan, assembly, QC, the SRT — reads one clock (the EP18 lesson: a chip 7 s early because one
    reader skipped the crossing)."""
    words, flat = fd.timeline(job)
    head = float(cfg.get("title_head", 0.0))
    words = [dict(w, start=w["start"] + head, end=w["end"] + head) for w in words]
    C = cfg["cues"]
    T = {"speech_start": words[0]["start"], "speech_end": words[-1]["end"], "head": head}

    def at(key, after=0.0):
        i0, i1 = fd.find(words, flat, C[key], after)
        return i0, i1

    def gap_before(i0):
        return round((words[i0 - 1]["end"] + words[i0]["start"]) / 2, 2) if i0 else 0.0

    last = 0.0
    for key in C:
        i0, i1 = at(key, last if key in ("the_race", "the_horse", "the_morning_price", "its_tags") else 0.0)
        T[key] = {"start": round(words[i0]["start"], 2), "end": round(words[i1]["end"], 2), "pause_before": gap_before(i0)}
        if key == "the_track":
            last = words[i0]["start"]
        if key in ("the_race", "the_horse", "the_morning_price"):
            last = words[i0]["start"]
    return T


# ------------------------------------------------------------------ cards
def pip_box(inner, width=720, top=322):
    return (f'<div id="pip" class="abs" style="left:48px;top:{top}px;width:{width}px;padding:40px 46px 46px;'
            f'background:rgba(27,33,38,.95);border:1px solid var(--div);border-radius:20px">'
            f'<div id="plogo">{fbx_logo(48)}</div>{inner}</div>')


def c_card1(cfg, T, t0):
    l = cfg["copy"]["card1"]
    inner = (f'<div id="ph" class="h" style="font-size:76px;line-height:1.02;margin-top:26px;transform-origin:left center">'
             f'{l[0]}<br>{l[1]}<br><span class="gold">{l[2]}</span></div>')
    hit = (T["reason"]["start"] - t0) * 1000
    return page(1920, 1080, pip_box(inner), [fade("#pip", 0, 280, dx=-40), fade("#plogo", 120, 300), slam("#ph", hit - 60)],
                bg="transparent", title="FBX card 1")


def c_logo_reveal(cfg, T, t0, job):
    svg = (Path(cfg["pack_dir"]) / "logos" / "fbx-logo-on-dark.svg").read_text(encoding="utf-8")
    svg = svg.replace('width="2010" height="640"', 'width="1206" height="384" id="L"')
    for k in range(4):
        svg = svg.replace("<rect ", f'<rect id="b{k}" class="bar" ', 1)
    svg = svg.replace("<path ", '<path id="lf" ', 1).replace('<path fill="#9AA6AE"', '<path id="ls" fill="#9AA6AE"', 1)
    if 'id="ls"' not in svg:
        raise fd.Halt("logo reveal: could not find the FORM BEATER INDEX path in the FBX logo SVG")
    body = (f'<style>.bar{{transform-box:fill-box;transform-origin:50% 100%}}</style>'
            f'<div class="abs" style="left:357px;top:330px">{svg}</div>'
            f'<div id="cend" class="abs" style="right:140px;bottom:96px">{endorse(22, 52)}</div>')
    fbx = (T["fbx_word"]["start"] - t0) * 1000
    sub = (T["form_beater"]["start"] - t0) * 1000
    spec = [A(f"#b{k}", [{"transform": "scaleY(0)"}, {"transform": "scaleY(1)"}], 80 + 110 * k, 420) for k in range(4)]
    spec += [A("#lf", [{"opacity": 0, "transform": "translateX(-30px)"}, {"opacity": 1, "transform": "translateX(0px)"}],
               max(700, fbx - 80), 420),
             A("#ls", [{"opacity": 0, "transform": "translateY(14px)"}, {"opacity": 1, "transform": "translateY(0px)"}],
               max(1300, sub - 60), 500, "ease-out"),
             fade("#cend", max(1300, sub), 500)]
    return page(1920, 1080, body, spec, title="FBX logo reveal")


def c_lower_gordon(cfg, T, t0):
    c = cfg["copy"]
    body = (f'<div id="lt" class="abs" style="left:48px;bottom:60px;padding:18px 34px 20px 28px;'
            f'background:rgba(27,33,38,.95);border-left:6px solid var(--gold);border-radius:4px 14px 14px 4px;transform-origin:left center">'
            f'<div id="ltl" style="margin-bottom:12px">{fbx_logo(32)}</div>'
            f'<div id="ln" class="h" style="font-size:46px">{c["gordon_name"]}</div>'
            f'<div id="lo" class="t2" style="font-size:22px;font-weight:600;letter-spacing:.22em;margin-top:8px">{c["gordon_org"]}</div></div>')
    on = (T["im_gordon"]["start"] - t0) * 1000 - 100
    spec = [A("#lt", [{"opacity": 0, "transform": "scaleX(0.2)"}, {"opacity": 1, "transform": "scaleX(1)"}], on, 340),
            fade("#ltl", on + 150, 300), fade("#ln", on + 180, 300, dx=-14), fade("#lo", on + 300, 300, dx=-14)]
    return page(1920, 1080, body, spec, bg="transparent", title="Gordon lower third")


def c_chapter(cfg, key, extra_spec=None):
    ch = cfg["copy"][key]
    body = (f'<div class="eyebrow abs" style="left:140px;top:108px;font-size:34px"><span id="erule" class="rule"></span>'
            f'<span id="etext">{ch["eyebrow"]}</span></div>'
            f'<div id="hl" class="h abs" style="left:140px;top:178px;width:1640px;font-size:150px;line-height:.98;'
            f'white-space:normal;transform-origin:left center">{ch["headline"]}</div>'
            f'<div id="sub" class="abs t2" style="left:140px;top:540px;width:1300px;font-size:44px;line-height:1.32">{ch["sub"]}</div>'
            + footer16())
    spec = [wipe("#erule", 0), fade("#etext", 120, 380), slam("#hl", 260), fade("#sub", 900, 500, dy=12),
            fade("#flogo", 300, 400), fade("#fend", 380, 400)] + (extra_spec or [])
    return page(1920, 1080, body, spec, title=f"FBX chapter {key}")


def c_story(cfg, T, t0):
    (a1, a2), (b1, b2) = cfg["copy"]["story"]
    inner = (f'<div id="s1" class="h" style="font-size:70px;line-height:1.02;margin-top:26px;transform-origin:left center">{a1}<br>{a2}</div>'
             f'<div id="s2" class="h gold" style="font-size:70px;line-height:1.02;margin-top:22px;transform-origin:left center">{b1}<br>{b2}</div>')
    s1 = (T["story"]["start"] - t0) * 1000
    s2 = (T["evidence"]["start"] - t0) * 1000
    return page(1920, 1080, pip_box(inner, top=300),
                [fade("#pip", 0, 280, dx=-40), fade("#plogo", 120, 300), slam("#s1", s1 - 60), slam("#s2", s2 - 60)],
                bg="transparent", title="FBX story panel")


def c_gap(cfg, T, t0):
    g = cfg["copy"]["gap"]
    inner = (f'<div id="ge" class="eyebrow" style="font-size:22px;margin-top:24px"><span class="rule" style="width:46px"></span>{g["eyebrow"]}</div>'
             f'<div style="position:relative;margin-top:34px;height:250px">'
             f'<div id="gt" class="t2" style="position:absolute;left:0;top:0;font-size:22px;font-weight:600;letter-spacing:.16em">{g["top"]}</div>'
             f'<div id="gb1" style="position:absolute;left:0;top:34px;width:380px;height:46px;background:#5B6770;border-radius:6px 0 0 6px;transform-origin:left center"></div>'
             f'<div id="gg" style="position:absolute;left:380px;top:34px;width:220px;height:46px;background:var(--gold);border-radius:0 6px 6px 0;transform-origin:left center"></div>'
             f'<div id="gl" class="h gold" style="position:absolute;left:380px;top:-6px;width:220px;text-align:center;font-size:26px;letter-spacing:.06em">{g["label"]}</div>'
             f'<div id="gs" class="t2" style="position:absolute;left:0;top:118px;font-size:22px;font-weight:600;letter-spacing:.16em">{g["second"]}</div>'
             f'<div id="gb2" style="position:absolute;left:0;top:152px;width:380px;height:46px;background:#5B6770;border-radius:6px;transform-origin:left center"></div>'
             f'<div id="gd" style="position:absolute;left:378px;top:24px;width:0;height:186px;border-left:3px dashed var(--gold)"></div>'
             f'</div>')
    c = (T["clear_of"]["start"] - t0) * 1000
    spec = [fade("#pip", 0, 280, dx=-40), fade("#plogo", 120, 300), fade("#ge", 200, 300),
            fade("#gt", 350, 300), wipe("#gb1", 400, 500), fade("#gs", 550, 300), wipe("#gb2", 600, 500),
            fade("#gd", c - 300, 250), wipe("#gg", c - 100, 450), fade("#gl", c + 250, 300, dy=8)]
    return page(1920, 1080, pip_box(inner), spec, bg="transparent", title="FBX gap graphic")


def check_icon(idn):
    return (f'<div id="{idn}" style="flex:none;width:58px;height:58px;border-radius:50%;background:var(--gold);position:relative">'
            f'<div style="position:absolute;left:19px;top:10px;width:14px;height:28px;border-right:7px solid var(--ink);'
            f'border-bottom:7px solid var(--ink);transform:rotate(45deg)"></div></div>')


def c_rules(cfg, T, t0):
    r = cfg["copy"]["rules"]
    row = lambda k, lines: (f'<div id="r{k}" style="display:flex;gap:26px;align-items:flex-start;margin-top:28px">{check_icon(f"c{k}")}'
                            f'<div class="h" style="font-size:52px;line-height:1.04">{lines[0]}<br>'
                            f'<span class="gold">{lines[1]}</span></div></div>')
    inner = (f'<div id="re" class="eyebrow" style="font-size:22px;margin-top:24px"><span class="rule" style="width:46px"></span>{r["eyebrow"]}</div>'
             + row(1, r["r1"]) + row(2, r["r2"]))
    a = (T["four_clear"]["start"] - t0) * 1000
    b = (T["price_rule"]["start"] - t0) * 1000
    spec = [fade("#pip", 0, 280, dx=-40), fade("#plogo", 120, 300), fade("#re", 200, 300),
            fade("#r1", a - 120, 300, dx=-20), slam("#c1", a - 120, 360, 1.6),
            fade("#r2", b - 120, 300, dx=-20), slam("#c2", b - 120, 360, 1.6)]
    return page(1920, 1080, pip_box(inner, top=300), spec, bg="transparent", title="FBX rules panel")


def c_no_standout(cfg, T, t0):
    a, b = cfg["copy"]["no_standout"]
    inner = (f'<div id="n1" class="h" style="font-size:64px;line-height:1.02;margin-top:22px;transform-origin:left center">{a}</div>'
             f'<div id="n2" class="h gold" style="font-size:64px;line-height:1.02;transform-origin:left center">{b}</div>')
    hit = (T["no_bet"]["start"] - t0) * 1000
    return page(1920, 1080, pip_box(inner, width=640, top=360),
                [fade("#pip", 0, 240, dx=-30), fade("#plogo", 100, 300), slam("#n1", 150), slam("#n2", hit - 40)],
                bg="transparent", title="FBX no standout")


def c_selection(cfg, T, t0):
    s = cfg["copy"]["selection"]
    sep = '<span class="sep" style="color:var(--t2);margin:0 22px;font-weight:400">|</span>'
    part = lambda i, txt, extra="": f'<span id="p{i}" style="display:inline-block{extra}">{txt}</span>'
    # style frame 02: Rosehill R6 | No.14 | Satono Glow | Morning $2.40 — a bar between every segment
    row = (part(1, s["track"]) + part(2, sep + s["no"]) + part(3, sep + s["horse"]) + part(4, sep + s["morning"]))
    cols = "".join(
        f'<div id="k{i}" style="width:390px"><div class="h gold" style="font-size:38px;letter-spacing:0">{b[0]}</div>'
        f'<div class="t2" style="font-size:30px;margin-top:12px;line-height:1.3">{b[1]}</div></div>'
        for i, b in enumerate([s["b1"], s["b2"], s["b3"], s["b4"]], 1))
    body = (f'<div class="eyebrow abs" style="left:140px;top:108px;font-size:34px"><span id="erule" class="rule"></span>'
            f'<span id="etext">{s["eyebrow"]}</span></div>'
            f'<div id="panel" class="abs" style="left:140px;top:212px;width:1640px;height:224px;background:var(--panel);border-radius:18px">'
            # until the row builds, the panel says what Gordon is saying — never an empty box for 6 s
            f'<div id="pre" class="abs" style="left:48px;top:0;bottom:0;display:flex;align-items:center">'
            f'<div id="pre2" class="t2" style="font-size:46px">{s["pre"]}</div></div>'
            f'<div class="h abs" style="left:48px;top:44px;font-size:60px;letter-spacing:0">{row}</div>'
            f'<div id="p5" class="abs" style="left:48px;top:128px">{fc.chips(s["tags"], 26)}</div></div>'
            f'<div class="abs" style="left:140px;top:492px;display:flex;gap:28px">{cols}</div>' + footer16())
    tt = {k: (T[k]["start"] - t0) * 1000 for k in ("the_track", "the_race", "the_horse", "the_morning_price", "its_tags")}
    spec = [wipe("#erule", 0), fade("#etext", 120, 380), fade("#panel", 250, 400), fade("#flogo", 300, 400), fade("#fend", 380, 400),
            fade("#pre", 700, 400, dx=-16),
            A("#pre2", [{"opacity": 1}, {"opacity": 0}], tt["the_track"] - 420, 300, "ease-in"),
            fade("#p1", tt["the_track"] - 80, 260, dy=14), fade("#k1", tt["the_track"] - 40, 300, dy=10),
            fade("#p2", tt["the_race"] - 80, 260, dy=14),
            fade("#p3", tt["the_horse"] - 80, 260, dy=14), fade("#k2", tt["the_horse"] - 40, 300, dy=10),
            fade("#p4", tt["the_morning_price"] - 80, 260, dy=14), fade("#k3", tt["the_morning_price"] - 40, 300, dy=10),
            slam("#p5", tt["its_tags"] - 80, 360, 1.4), fade("#k4", tt["its_tags"] - 40, 300, dy=10)]
    return page(1920, 1080, body, spec, title="FBX selection row")


def c_report(cfg, T, t0, t1):
    """The real Saturday Report, its dated header line blurred (evergreen), panning from the header to the
    FBX Gap column. Page units = the 1241-px-wide page; the image is a 400-dpi render shown at that width."""
    dur = (t1 - t0) * 1000 + 400
    a = (1920 / 1241, 0, 0)                    # whole width, header at the top
    b = (2.2, 745 - 960 / 2.2, 750 - 540 / 2.2)   # the selections table, centred on the FBX Gap column

    def tf(k, x, y):
        return f"translate({-x * k:.1f}px,{-y * k:.1f}px) scale({k:.5f})"
    body = (f'<img id="rep" src="assets/report-evergreen.png" class="abs" style="left:0;top:0;width:1241px;'
            f'transform-origin:0 0;transform:{tf(*a)}">')
    return page(1920, 1080, body, [A("#rep", [{"transform": tf(*a)}, {"transform": tf(*b)}], 0, dur, "cubic-bezier(.45,0,.4,1)")],
                title="FBX Saturday Report (evergreen)")


def c_research(cfg, T, t0):
    r = cfg["copy"]["research"]
    finals = {1: str(r["n1"]), 2: str(r["n2"]), 3: f'{r["n3"]:.2f}%'}
    # the page text carries the FINAL figure; the count driver repaints it from the timeline on every frame
    blk = lambda i, gold, lab: (f'<div id="blk{i}" style="width:{440 if i < 3 else 620}px"><div id="n{i}" class="h{" gold" if gold else ""}" '
                                f'style="font-size:128px;font-variant-numeric:tabular-nums;letter-spacing:-.01em">{finals[i]}</div>'
                                f'<div class="t2" style="font-size:28px;font-weight:600;letter-spacing:.22em;margin-top:14px">{lab}</div></div>')
    body = (f'<div class="eyebrow abs" style="left:140px;top:108px;font-size:34px"><span id="erule" class="rule"></span>'
            f'<span id="etext">{r["eyebrow"]}</span></div>'
            f'<div class="abs" style="left:140px;top:230px;display:flex;gap:40px">'
            f'{blk(1, False, r["l1"])}{blk(2, False, r["l2"])}{blk(3, True, r["l3"])}</div>'
            f'<div id="sub" class="abs t2" style="left:140px;top:560px;font-size:40px">{r["sub"]}</div>'
            f'<div id="small" class="abs small" style="left:140px;top:880px;font-size:22px">{r["small_print"]}</div>' + footer16())
    spec = [wipe("#erule", 0), fade("#etext", 120, 380), fade("#small", 200, 400), fade("#flogo", 300, 400),
            fade("#fend", 380, 400), fade("#sub", 700, 500, dy=10)]
    for i, (key, val, dec, suf) in enumerate([("n1", r["n1"], 0, ""), ("n2", r["n2"], 0, ""), ("n3", r["n3"], 2, "%")], 1):
        t = (T[key]["start"] - t0) * 1000
        spec.append(fade(f"#blk{i}", t - 1100, 250, dy=12))
        spec.append({"sel": f"#n{i}", "count": {"from": 0, "to": val, "decimals": dec, "suffix": suf},
                     "opts": {"delay": round(t - 1000), "duration": 1300, "easing": "cubic-bezier(.2,.7,.3,1)"}})
    return page(1920, 1080, body, spec, title="FBX research")


def stage(job, cfg, cards):
    pack = Path(cfg["pack_dir"])
    a = cards / "assets"
    (a / "fonts").mkdir(parents=True, exist_ok=True)
    for w in (400, 600, 800):
        shutil.copyfile(pack / "fonts" / f"Archivo-{w}.woff2", a / "fonts" / f"Archivo-{w}.woff2")
    for n in ("fbx-logo-on-dark.svg", "pp-logo-on-dark.svg"):
        shutil.copyfile(pack / "logos" / n, a / n)
    shutil.copyfile(fc.ASSETS / "pp-anim.js", cards / "pp-anim.js")
    shutil.copyfile(fc.ASSETS / "assets" / "logo.png", a / "logo.png")
    # the report at 400 dpi, then its DATED header line blurred beyond reading (evergreen)
    pdf = next((pack / "reference").glob("FBX_Saturday_Report_*.pdf"))
    raw = cards / "assets" / "report400"
    subprocess.run(["pdftoppm", "-r", "400", "-png", "-singlefile", str(pdf), str(raw)], check=True)
    from PIL import Image, ImageFilter
    im = Image.open(str(raw) + ".png").convert("RGB")
    k = im.width / 1241                       # page units -> pixels
    box = tuple(round(v * k) for v in (660, 120, 1180, 178))   # "Saturday, 10 October 2026"
    region = im.crop(box).filter(ImageFilter.GaussianBlur(radius=round(14 * k)))
    im.paste(region, box)
    im.save(a / "report-evergreen.png")
    return box


def build_cards(job, only=()):
    cfg = load(job)
    T = cue_sheet(job, cfg)
    cards = job / "overlay" / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    stage(job, cfg, cards)
    P = plan(job, cfg, T)
    W = {w["name"]: w for w in P["windows"]}
    wk = {"copy": {"closing_line1": cfg["copy"]["closing_line1"], "closing_line2": cfg["copy"]["closing_line2"]}}
    TJ = {"join_in": W["join-lower-third"]["in"], "lower_third_on": T["lower_third_on"]["start"]}
    builds = [
        ("card1", c_card1(cfg, T, W["card1"]["in"]), True),
        ("logo-reveal", c_logo_reveal(cfg, T, W["logo-reveal"]["in"], job), False),
        ("lower-gordon", c_lower_gordon(cfg, T, W["lower-gordon"]["in"]), True),
        ("chapter-one", c_chapter(cfg, "ch1"), False),
        ("story", c_story(cfg, T, W["story"]["in"]), True),
        ("chapter-two", c_chapter(cfg, "ch2"), False),
        ("gap", c_gap(cfg, T, W["gap"]["in"]), True),
        ("rules", c_rules(cfg, T, W["rules"]["in"]), True),
        ("no-standout", c_no_standout(cfg, T, W["no-standout"]["in"]), True),
        ("selection", c_selection(cfg, T, W["selection"]["in"]), False),
        ("report", c_report(cfg, T, W["report"]["in"], W["report"]["out"]), False),
        ("research", c_research(cfg, T, W["research"]["in"]), False),
        ("join-lower-third", fc.c_lower_third(wk, TJ), True),
        ("closing", fc.c_closing(wk, T), False),
        ("warranty", (fc.ASSETS / "warranty-slide.html").read_text(encoding="utf-8"), False),
    ]
    jobs = []
    for name, html, alpha in builds:
        p = cards / f"promo-{name}.html"
        p.write_text(html, encoding="utf-8")
        if not only or name in only:
            jobs.append((p, 1920, 1080, alpha))
    (job / "overlay" / "promo-cues.json").write_text(json.dumps(T, indent=1), encoding="utf-8")
    print(f"wrote {len(builds)} card pages; rendering {len(jobs)}")
    import fbx_render
    fbx_render.render_all(job / "overlay" / "clips", jobs)


# ------------------------------------------------------------------ the edit plan (the shot script, timed)
def plan(job, cfg, T):
    pb = lambda k: T[k]["pause_before"]
    st = lambda k: T[k]["start"]
    P = {"speech_end": T["speech_end"], "head": T["head"]}
    P["closing_in"] = round(T["speech_end"] + 0.25, 2)
    P["warranty_in"] = round(P["closing_in"] + fa.CLOSING_BUILD + fa.CLOSING_HOLD, 2)
    P["total"] = round(P["warranty_in"] + fa.WARRANTY_TAIL, 2)
    # layer: full = full-screen card; broll; over = panel / lower third over Gordon. (name, in, out, fade_in, fade_out)
    win = []

    def add(name, layer, t_in, t_out, fi=FADE, fo=0.0, src=None):
        win.append({"name": name, "layer": layer, "in": round(t_in, 3), "out": round(t_out, 3), "fi": fi, "fo": fo, "src": src})

    if T["head"]:   # the title card: the approved evergreen thumbnail, held for the head, like a PP episode's title
        add("title", "full", 0.0, T["head"], 0.0, FADE)
    add("card1", "over", pb("reason") - 0.05, pb("thats_fbx") + FADE, FADE, 0)                         # shot 2
    add("logo-reveal", "full", pb("thats_fbx"), pb("im_gordon"), FADE, FADE)                           # shot 3
    add("lower-gordon", "over", pb("im_gordon"), pb("lt_gordon_out_before"), 0, FADE)                  # shot 4
    add("chapter-one", "full", pb("trouble"), st("one_week") + FADE, FADE, 0)                          # shot 6
    add("story", "over", pb("story") - 0.05, pb("gives") + FADE, FADE, 0)                              # shot 8
    add("chapter-two", "full", pb("gives"), pb("gap"), FADE, FADE)                                    # shot 9
    add("gap", "over", pb("gap"), pb("selection_rule") + FADE, FADE, 0)                                # shot 10
    add("rules", "over", pb("selection_rule"), st("standout") + FADE, FADE, 0)                         # shot 11
    add("no-standout", "over", pb("no_bet") - 0.1, pb("nine_thirty") + FADE, FADE, 0)                  # shot 12 (end)
    add("selection", "full", pb("nine_thirty"), pb("report") + FADE, FADE, 0)                          # shot 13
    add("report", "full", pb("report"), pb("tested") + FADE, FADE, 0)                                 # shot 14
    add("research", "full", pb("tested"), pb("history"), FADE, FADE)                                  # shot 15
    add("join-lower-third", "over", pb("join"), pb("rg") + 0.15, 0, FADE)                              # shot 19
    add("closing", "full", P["closing_in"], P["warranty_in"] + 0.6, FADE, 0)                          # shot 21
    add("warranty", "full", P["warranty_in"], P["total"], 0.6, 0)                                      # shot 22
    # b-roll — on top of full-screen cards, so a card can hand straight to a clip without Gordon flashing through
    for slot, (key, fname, dur) in B_ROLL.items():
        t_in = st(key)
        t_out = t_in + dur if dur else pb("no_bet") - 0.05
        add(f"broll-{slot}", "broll", t_in, t_out, FADE, FADE, src=fname)
    P["windows"] = win
    # framing on Gordon — eased zoom moves only (MCU 126%, push 136% for a panel, WIDE 100%)
    # 🔴 THE PUSH FINISHES BEFORE A PANEL APPEARS (11 Oct, found by QC): the first plan started the push-right
    # glide and the story panel's fade together, so for ~0.2 s a half-faded panel sat over his still-moving
    # shoulder (-102 px). Each push now starts 0.6 s before its panel and lands ~0.1 s before it.
    P["mcu"] = [(-1.0, pb("reason") - 0.25), (pb("built"), pb("trouble") + 0.6), (pb("good_run"), pb("story") - 0.2),
                (pb("history") - 0.5, pb("suits")), (pb("like"), P["total"] + 1)]
    P["push"] = [(pb("reason") - 0.65, pb("thats_fbx") + 1.0), (pb("story") - 0.6, pb("gives") + 1.0),
                 (pb("gap") - 0.5, pb("nine_thirty") + 1.0)]
    return P


def zoom_expr(P):
    ss = fa.ss

    def act(ws, ease):
        return "(" + "+".join(f"({ss(f'(it-{a})/{ease}')}-{ss(f'(it-{b - ease})/{ease}')})" for a, b in ws) + ")"
    Mx, Px = act(P["mcu"], 0.4), act(P["push"], 0.5)
    z = f"'(1+{fa.MCU_ZOOM - 1}*{Mx})*(1-{Px})+{fa.PUSH_ZOOM}*{Px}'"
    x = f"'(iw-iw/zoom)/2*(1-{Px})'"
    y = f"'(ih-ih/zoom)/2-55*max({Mx},{Px})'"
    return z, x, y


def assemble(job):
    cfg = load(job)
    T = cue_sheet(job, cfg)
    P = plan(job, cfg, T)
    tot = P["total"]
    master = job / "renders" / "presenter-master.mp4"
    music = job.parents[1] / "PP-EP01-The-Trifecta-Mistake" / "music" / "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"
    chip = fc.ASSETS / "video-logo-chip.png"
    clips = job / "overlay" / "clips"
    # bottom to top: panels over Gordon, then full-screen cards, then b-roll — so every hand-off is an
    # incoming layer fading in OVER an outgoing one held solid (the PP rule: never two cross-fading)
    order = [w for w in P["windows"] if w["layer"] == "over"] + [w for w in P["windows"] if w["layer"] == "full"] + \
            [w for w in P["windows"] if w["layer"] == "broll"]
    inputs = [master, chip]
    for w in order:
        if w["layer"] == "broll":
            src = job / "broll" / w["src"]
        else:
            c = list(clips.glob(f"promo-{w['name']}.m*")) + list(clips.glob(f"promo-{w['name']}.png"))
            if len(c) != 1:
                raise fd.Halt(f"expected one clip promo-{w['name']}.mp4/.mov/.png, found {len(c)}")
            src = c[0]
        if not src.is_file():
            raise fd.Halt(f"missing input {src}")
        inputs.append(src)
    inputs.append(music)
    music_in = len(inputs) - 1
    z, x, y = zoom_expr(P)
    head = P["head"]
    lead = f"tpad=start_duration={head}:start_mode=clone," if head else ""
    g = (f"[0:v]{lead}tpad=stop_mode=clone:stop_duration=60,trim=duration={tot},setpts=PTS-STARTPTS,fps=25,"
         f"zoompan=z={z}:x={x}:y={y}:d=1:s=1920x1080:fps=25[zoomed];\n"
         f"[1:v]format=rgba[lg];\n[zoomed][lg]overlay=x=W-w-40:y=H-h-40[v0];\n")
    cur = "v0"
    for k, w in enumerate(order):
        lbl = f"c{k}"
        if w["layer"] == "broll":
            d = round(w["out"] - w["in"], 3)
            g += (f"[{k + 2}:v]trim=start=0.3:duration={d},setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,"
                  f"format=yuva420p,fade=t=in:st=0:d={w['fi']}:alpha=1,fade=t=out:st={round(d - w['fo'], 3)}:d={w['fo']}:alpha=1,"
                  f"setpts=PTS+{w['in']}/TB[{lbl}];\n")
        else:
            g += fa.card_chain(k + 2, w["name"], w["in"], w["out"], w["fi"], w["fo"], lbl)
        g += f"[{cur}][{lbl}]overlay=x=0:y=0:eof_action=pass[v{k + 1}];\n"
        cur = f"v{k + 1}"
    g += f"[{cur}]fade=t=out:st={round(tot - 0.5, 2)}:d=0.5,format=yuv420p[vout];\n"
    I0, _ = fa.measure_mix(job, P, master, music)
    gain = max(-3.0, min(3.0, round(fa.TARGET_LUFS - I0, 2)))
    I1, tp1 = fa.measure_mix(job, P, master, music, gain)
    print(f"  mix loudness {I0:.1f} LUFS -> makeup {gain:+.2f} dB -> {I1:.1f} LUFS, peak {tp1:.1f} dBFS", flush=True)
    P["makeup_db"] = gain
    g += fa.audio_graph(P, 0, music_in, gain)
    gfile = job / "overlay" / "graph-promo.txt"
    gfile.write_text(g, encoding="utf-8")
    out = job / "output" / "FBX-PROMO-16x9.mp4"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
    for p in inputs:
        cmd += ["-i", str(p)]
    cmd += ["-filter_complex_script", str(gfile), "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            "-map_metadata", "-1", "-map_chapters", "-1", "-dn", "-t", str(tot), str(out)]
    print(f"assembling {out.name}: {tot:.2f}s, {len(order)} windows", flush=True)
    if subprocess.run(cmd).returncode:
        raise fd.Halt("ffmpeg failed")
    (job / "overlay" / "promo-plan.json").write_text(json.dumps({"cues": T, "plan": P}, indent=1), encoding="utf-8")
    write_srt(job, head)
    print("wrote", out)


def write_srt(job, head):
    """output/FBX-PROMO-16x9.srt = renders/aligned.srt moved onto the FINISHED clock (+ the title head)."""
    import re as _re
    src = (job / "renders" / "aligned.srt").read_text(encoding="utf-8-sig")

    def shift(m):
        h, mi, s, ms = (int(v) for v in m.groups())
        t = h * 3600 + mi * 60 + s + ms / 1000 + head
        ms_ = int(round(t * 1000))
        return f"{ms_ // 3600000:02d}:{ms_ // 60000 % 60:02d}:{ms_ // 1000 % 60:02d},{ms_ % 1000:03d}"
    dst = _re.sub(r"(\d\d):(\d\d):(\d\d),(\d\d\d)", shift, src)
    (job / "output" / "FBX-PROMO-16x9.srt").write_text(dst, encoding="utf-8-sig", newline="\r\n")
    print(f"wrote output/FBX-PROMO-16x9.srt (+{head:.1f} s onto the finished clock)")


def main():
    job = Path(sys.argv[1]).resolve()
    mode = sys.argv[2]
    try:
        if mode == "cues":
            cfg = load(job)
            T = cue_sheet(job, cfg)
            P = plan(job, cfg, T)
            (job / "overlay" / "promo-cues.json").write_text(json.dumps(T, indent=1), encoding="utf-8")
            for k, v in T.items():
                print(f"{k:20s} {v}")
            for w in P["windows"]:
                print(f"  {w['layer']:6s} {w['name']:18s} {w['in']:8.2f} -> {w['out']:8.2f}")
            print("mcu", P["mcu"], "\npush", P["push"], "\ntotal", P["total"])
        elif mode == "cards":
            build_cards(job, tuple(sys.argv[3:]))
            sys.stdout.flush()
            import os
            os._exit(0)
        elif mode == "assemble":
            assemble(job)
        elif mode == "title":
            # the approved evergreen thumbnail page, re-rendered at 1.5x = 1920x1080 (same layout, crisp text)
            cfg = load(job)
            import fbx_render
            out = job / "overlay" / "clips" / "promo-title.png"
            fbx_render.still(Path(cfg["title_card_html"]), out, 1280, 720, scale=1.5)
            sys.stdout.flush()
            import os
            os._exit(0)
    except fd.Halt as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
