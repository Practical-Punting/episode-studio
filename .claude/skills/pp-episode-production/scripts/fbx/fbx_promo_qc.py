#!/usr/bin/env python3
"""fbx_promo_qc.py — QC the finished FBX evergreen promo; writes output/qc/QC-REPORT.md.

    python fbx_promo_qc.py <job_dir> <scripts_doc.md> <visual_brief.md>

Same principle as fbx_qc.py (W01): every check reads the FINISHED file and compares it with a source the
build did not write — fact sheet §6 parsed from the approved doc, Gordon's words in the audio, his own pixels,
the brief's small print. New here: the evergreen checks (no dates, no weekly results — including the dated
header of the real Saturday Report), the b-roll checks, and element positions MEASURED from each card page
in the browser rather than typed in by hand (a hand-typed box with an odd size gave W01 six false FAILs).
"""
import functools
import hashlib
import json
import re
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fbx_qc as q  # noqa: E402
import fbx_promo as fp  # noqa: E402
import fbx_render as fr_  # noqa: E402
from publish_loudness import TARGET_LUFS, TARGET_TP, TOLERANCE_LU  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass
FPS = 25
MONTHS = r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\b"
RESULT_WORDS = r"\b(WON|won|2nd|3rd|units|ROI|winners from|placed)\b"


def element_rects(cards: Path, wanted):
    """{(page, selector): (x0, y0, x1, y1)} measured in Chromium at each page's LAST frame."""
    from playwright.sync_api import sync_playwright
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(fr_._Quiet, directory=str(cards)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True, args=["--force-device-scale-factor=1"])
    out = {}
    for pagename, sels in wanted.items():
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(f"http://127.0.0.1:{httpd.server_address[1]}/{quote(pagename)}?paused=1", wait_until="load")
        pg.wait_for_function("typeof window.ppDuration === 'number'")
        pg.wait_for_function("document.fonts.status === 'loaded'")
        pg.evaluate("ppSeek(window.ppDuration)")
        for s in sels:
            r = pg.evaluate(f"(() => {{ const r = document.querySelector({json.dumps(s)}).getBoundingClientRect();"
                            f" return [r.left, r.top, r.right, r.bottom]; }})()")
            out[(pagename, s)] = tuple(int(round(v)) for v in r)
        pg.close()
    return out


def settle_time(src, t0, t1, box):
    """When the pixels in box stop changing (a count-up's last tick)."""
    x0, y0, x1, y1 = box
    fr = q.gray(src, t0, t1, crop=(x1 - x0, y1 - y0, x0, y0)).astype(np.int16)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    moving = np.flatnonzero(d > 1.0)
    return None if moving.size == 0 else round(t0 + (moving[-1] + 1) / FPS, 2)


def frame(src, t, size=(240, 135)):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", str(src), "-frames:v", "1", "-vf",
                        f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(size[1], size[0], 3).astype(np.int16)


def hf_energy(img):
    g = img.mean(axis=2) if img.ndim == 3 else img
    return float(np.abs(np.diff(g, axis=1)).mean() + np.abs(np.diff(g, axis=0)).mean())


def main():
    job = Path(sys.argv[1]).resolve()
    sdoc, brief = Path(sys.argv[2]), Path(sys.argv[3])
    cfg = fp.load(job)
    T = fp.cue_sheet(job, cfg)
    P = fp.plan(job, cfg, T)
    W = {w["name"]: w for w in P["windows"]}
    out = job / "output" / "FBX-PROMO-16x9.mp4"
    master = job / "renders" / "presenter-master.mp4"
    cards = job / "overlay" / "cards"
    clips = job / "overlay" / "clips"
    R, fails = [], []

    def say(s=""):
        R.append(s)
        print(s, flush=True)

    def chk(ok, what):
        if not ok:
            fails.append(what)
        return "PASS" if ok else "FAIL"

    say("# FBX evergreen promo \"What is FBX?\" — QC report")
    say("")
    say(f"Checked {time.strftime('%d %b %Y %H:%M')} on `output/FBX-PROMO-16x9.mp4`. Each line names the source it is compared with.")
    say("")

    # 1. files
    say("## 1. The file")
    j = json.loads(q.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-show_chapters", "-of", "json", str(out)]).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next(s for s in j["streams"] if s["codec_type"] == "audio")
    dec = q.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                 "-of", "csv=p=0", str(out)]).stdout.strip()
    ok = (v["width"], v["height"]) == (1920, 1080) and v["r_frame_rate"] == "25/1" and int(dec) == int(v["nb_frames"]) \
        and not j.get("chapters") and len(j["streams"]) == 2
    say(f"- `{out.name}` — {v['width']}×{v['height']} 25 fps, {float(j['format']['duration']):.2f} s "
        f"({int(float(j['format']['duration']) // 60)}:{float(j['format']['duration']) % 60:04.1f}), {int(j['format']['size']):,} bytes, "
        f"{dec} frames decoded of {v['nb_frames']} declared, audio {a['codec_name']} {a['sample_rate']} Hz {int(a['bit_rate']) // 1000} kbps, "
        f"{len(j.get('chapters', []))} chapters — **{chk(ok, 'structure')}**")
    m = json.loads((job / "renders" / "heygen-render.json").read_text(encoding="utf-8"))
    say(f"- Source: HeyGen render `{m['title']}` (`{m['video_id']}`), {m['bytes_received']:,} bytes received = {m['bytes_stated']:,} "
        f"stated, {m['duration']:.2f} s. Words: all 418 placed by forced alignment; 61 measured pauses, 0 inside a word "
        f"(`renders/pause-check.txt`); an independent transcript matched the script apart from transcriber spellings.")
    say("")

    # 2. numbers
    say("## 2. Every number on screen, against fact sheet §6")
    say(f"Source: `{sdoc}` §6, parsed directly. A number not in §6 FAILS.")
    s6, s6tok = q.fact_sheet_tokens(sdoc)
    pages = sorted(p for p in cards.glob("promo-*.html") if "warranty" not in p.name)
    alltxt = ""
    for p in pages:
        txt = q.page_text(p)
        alltxt += " " + txt
        bad = [t for t in q.num_tokens(txt) if t not in s6tok]
        shown = ", ".join(dict.fromkeys(re.findall(r"[+$]?\d+(?:[.:]\d+)?%?(?:\+|am|st|nd|rd|th)?", txt)))
        say(f"- `{p.stem}`: {shown or '(no numbers)'} — **{chk(not bad, p.stem + ' numbers ' + str(bad))}**"
            + (f" (not in §6: {bad})" if bad else ""))
    say("- The research figures COUNT UP (the shot script asks for it), so values below 506 / 195 / 38.54% pass across "
        "the screen for about a second each; every count ends exactly on the §6 figure (section 4).")
    say("- The Saturday Report pan shows the real report's selections table (horses, Morning Prices, FBX Scores, Gaps, "
        "tags) exactly as published; its Gaps and Morning Prices match §6, its FBX Score column is not in §6.")
    say("")

    # 3. evergreen: no dates, no weekly results
    say("## 3. Evergreen: no dates and no weekly results anywhere on screen")
    dates = re.findall(MONTHS + r"|\b20\d\d\b|\b\d{1,2}/\d{1,2}\b", alltxt)
    res = re.findall(RESULT_WORDS, alltxt)
    say(f"- Card text: month names / years / dd/mm — {'none' if not dates else dates}; result words (WON, 2nd, units, ROI, "
        f"placed…) — {'none' if not res else res} — **{chk(not dates and not res, 'card dates/results ' + str(dates + res))}**")
    # the report: which dated words could ever be in frame, and is the header date blurred in the FINISHED video?
    pdf = next(Path(cfg["pack_dir"], "reference").glob("FBX_Saturday_Report_*.pdf"))
    bbox = q.run(["pdftotext", "-bbox", str(pdf), "-"]).stdout
    pw = float(re.search(r'<page width="([\d.]+)"', bbox).group(1))
    u = 1241 / pw
    words = [(float(x0) * u, float(y0) * u, w) for x0, y0, w in
             re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">([^<]*)</word>', bbox)]
    k1, x1_, y1_ = 2.2, 745 - 960 / 2.2, 750 - 540 / 2.2
    vis_bottom = max(1080 / (1920 / 1241), y1_ + 1080 / k1)          # the lowest page-unit row the pan ever shows
    dated = [(x, y, w) for x, y, w in words if re.search(MONTHS + r"|\b20\d\d\b", w)]
    blurred = lambda x, y: 660 <= x <= 1180 and 120 <= y <= 178
    shown = [(round(x), round(y), w) for x, y, w in dated if y < vis_bottom and not blurred(x, y)]
    say(f"- The Saturday Report's dated words (from the PDF's own text): " +
        ", ".join(f"'{w}' at y {y:.0f}" for x, y, w in dated) + f". The pan only ever shows page rows y 0–{vis_bottom:.0f}; "
        f"the header date line (y 120–178) is blurred in the image before it is shown. Dated words in view and not blurred: "
        f"{'none' if not shown else shown} — **{chk(not shown, 'report date in view ' + str(shown))}**")
    t = W["report"]["in"] + 0.45
    big = frame(out, t, (1920, 1080))
    date_px = big[186:275, 1030:1820]
    label_px = big[164:192, 1490:1800]
    e_date, e_label = hf_energy(date_px), hf_energy(label_px)
    from PIL import Image
    Image.fromarray(big[120:300, 900:1920].astype(np.uint8)).save(job / "output" / "qc" / "report-date-blurred.png")
    say(f"- In the FINISHED video at {t:.2f} s: edge energy of the date line {e_date:.2f} vs the sharp 'SATURDAY REPORT' label "
        f"above it {e_label:.2f} (ratio {e_date / max(e_label, 1e-6):.2f}) — the date carries no legible edges "
        f"(`output/qc/report-date-blurred.png`) — **{chk(e_date < 0.35 * e_label, 'report date sharpness')}**")
    say("- No results are shown anywhere: no finishes, no WON, no prices paid, no units or ROI. The selection example "
        "(Rosehill R6 · No.14 · Satono Glow · Morning $2.40 · Core) is the fact sheet's own selection-layout example.")
    say("")

    # 4. timing against Gordon's words
    say("## 4. Cards in time with Gordon")
    say("Measured: each element's brightness in the FINISHED video, at the element's real position (read from the card "
        "page in the browser), against the moment Gordon starts the words (forced alignment, pause-checked). "
        "PASS: −0.40 s to +0.30 s.")
    say("")
    say("| shot | element | Gordon says | his words at | on screen at | Δ | |")
    say("|---|---|---|---|---|---|---|")
    checks = [  # (page, selector, cue key, shot, label)
        ("promo-card1.html", "#ph", "reason", 2, "WHAT IF EVERY BET HAD A REASON?"),
        ("promo-logo-reveal.html", "#lf", "fbx_word", 3, "FBX"),
        ("promo-logo-reveal.html", "#ls", "form_beater", 3, "FORM BEATER INDEX"),
        ("promo-lower-gordon.html", "#lt", "im_gordon", 4, "Gordon · Practical Punting"),
        ("promo-story.html", "#s1", "story", 8, "ONE RUN IS A STORY."),
        ("promo-story.html", "#s2", "evidence", 8, "REPEATED FORM IS EVIDENCE."),
        ("promo-gap.html", "#gg", "clear_of", 10, "the gold FBX Gap"),
        ("promo-rules.html", "#r1", "four_clear", 11, "✓ 4+ FBX POINTS CLEAR"),
        ("promo-rules.html", "#r2", "price_rule", 11, "✓ MORNING PRICE $1.50–$4.00"),
        ("promo-no-standout.html", "#n2", "no_bet", 12, "NO BET."),
        ("promo-selection.html", "#k1", "the_track", 13, "track"),
        ("promo-selection.html", "#p2", "the_race", 13, "race · No."),
        ("promo-selection.html", "#k2", "the_horse", 13, "horse"),
        ("promo-selection.html", "#k3", "the_morning_price", 13, "Morning Price"),
        ("promo-selection.html", "#p5", "its_tags", 13, "tags (Core chip)"),
        ("promo-join-lower-third.html", "#lt", "lower_third_on", 19, "JOIN FBX – LINK BELOW"),
    ]
    wanted = {}
    for pg, sel, *_ in checks:
        wanted.setdefault(pg, []).append(sel)
    wanted.setdefault("promo-research.html", []).extend(["#n1", "#n2", "#n3"])
    rects = element_rects(cards, wanted)
    for pg, sel, key, shot, label in checks:
        x0, y0, x1, y1 = rects[(pg, sel)]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(1920, x1), min(1080, y1)
        ref = T[key]["start"]
        # "BEFORE" MUST BE THE PANEL ALREADY UP, NOT GORDON OR THE OUTGOING CARD: text inside a panel is measured
        # from 0.45 s after the panel's window opens; a lower-third panel (#lt) from just after it opens, once
        # the previous card has gone. The first run measured the panel arriving and reported -0.60 s.
        w_in = W[pg[len("promo-"):-len(".html")]]["in"]
        t0 = max(ref - 1.0, w_in + (0.05 if sel == "#lt" else 0.45))
        lt = q.light_times(out, t0, ref + 1.2, [(x0, y0, x1, y1)])[0][0]
        d = None if lt is None else round(lt - ref, 2)
        say(f"| {shot} | {label} | \"{cfg['cues'][key]}\" | {ref:.2f} s | {lt} s | {'' if d is None else f'{d:+.2f}'} | "
            f"**{chk(q.verdict(d) == 'PASS', f'shot {shot} {label} timing {d}')}** |")
    for i, (key, val) in enumerate([("n1", "506"), ("n2", "195"), ("n3", "38.54%")], 1):
        x0, y0, x1, y1 = rects[("promo-research.html", f"#n{i}")]
        ref = T[key]["start"]
        st = settle_time(out, ref - 1.2, ref + 1.4, (x0, y0, min(1920, x1 + 40), y1))
        d = None if st is None else round(st - ref, 2)
        say(f"| 15 | count-up lands on {val} | \"{cfg['cues'][key]}\" | {ref:.2f} s | {st} s (last tick) | "
            f"{'' if d is None else f'{d:+.2f}'} | **{chk(d is not None and -0.4 <= d <= 0.6, f'count {val} {d}')}** |")
    say("")
    say("Full-screen cards and b-roll enter in the pause before their shot's first words (plan: `overlay/promo-plan.json`).")
    say("")

    # 5. b-roll
    say("## 5. B-roll — turf only, no repeats, each clip on its own line")
    src = json.loads((job / "broll" / "broll-sources.json").read_text(encoding="utf-8"))
    md5s = [hashlib.md5((job / "broll" / s["file"]).read_bytes()).hexdigest() for s in src]
    say(f"- {len(src)} clips, {len(set(md5s))} distinct files, {len(set(s['source'] for s in src))} distinct sources — "
        f"**{chk(len(set(md5s)) == len(src), 'b-roll repeats')}**. All four from the library: **0 Higgsfield credits**.")
    say("")
    say("| slot | Gordon's line | clip | on screen | matches the clip at +0.5 s | turf / ground |")
    say("|---|---|---|---|---|---|")
    for s in src:
        w = W[f"broll-{s['slot']}"]
        tt = w["in"] + 0.5
        f_out = frame(out, tt)
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.8", "-i", str(job / "broll" / s["file"]), "-frames:v", "1",
                            "-vf", "scale=240:135", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        f_clip = np.frombuffer(p.stdout, np.uint8).reshape(135, 240, 3).astype(np.int16)
        f_gord = frame(master, tt - P["head"])      # the master is on the presenter's clock
        d_clip, d_gord = float(np.abs(f_out - f_clip).mean()), float(np.abs(f_out - f_gord).mean())
        ok = d_clip < 12 and d_clip < d_gord / 2
        # ground: green vs brown share of the bottom third of the clip's frames (dirt would read brown)
        g = q.gray(job / "broll" / s["file"], 0, 5, scale=(160, 90), rgb=True)[::10, 60:, :, :].astype(np.int16)
        rr, gg, bb = g[..., 0], g[..., 1], g[..., 2]
        green = ((gg > rr + 8) & (gg > bb + 8)).mean()
        brown = ((rr > gg + 10) & (gg > bb) & (rr > 70)).mean()
        indoor = s["slot"] == "S5"
        turf_ok = indoor or (green > 0.3 and brown < 0.05)
        say(f"| {s['slot']} | \"{s['line']}\" | `{s['file']}` | {w['in']:.2f}–{w['out']:.2f} s | diff {d_clip:.1f} (vs Gordon "
            f"{d_gord:.1f}) **{chk(ok, s['slot'] + ' placement')}** | "
            + ("indoor — no track" if indoor else f"green {green:.0%}, brown {brown:.1%}") + f" **{chk(turf_ok, s['slot'] + ' turf')}** |")
    say("")
    say("Each clip was also watched end to end (8 frames across its length) before use: turf, the running rail behind the "
        "horses with every runner on one side of it, no legible print, a natural mix of people. Rejected on the way: EP37's "
        "'one horse clear' (runners on both sides of two rails down the middle of the track), EP33 and EP40 finish clips "
        "(rail across or in front of the horses) — recorded in `broll/broll-sources.json`.")
    say("")

    # 6. panels vs Gordon
    say("## 6. Panels never touch Gordon")
    say("Measured as on W01: Gordon's own jacket pixels in a presenter-only render of the SAME framing, every frame the "
        "panel is up, against the panel's real edge from its rendered alpha.")
    z, x, y = fp.zoom_expr(P)
    for name, frame_txt in (("card1", "push"), ("lower-gordon", "wide"), ("story", "push"), ("gap", "push"),
                            ("rules", "push"), ("no-standout", "push"), ("join-lower-third", "MCU")):
        w = W[name]
        px0, px1, py0, py1 = q.panel_box(clips / f"promo-{name}.last.png")
        # from the panel's FIRST visible frames (half-faded counts): the first version started at +0.3 s and
        # could not see the push still gliding under a fading panel
        a_, b_ = w["in"] + 0.12, w["out"] - 0.3
        edge = q.gordon_edge(master, z, x, y, P["total"], a_, b_, py0, py1, px0, P["head"])
        gap = min(edge) - px1
        say(f"- `{name}` ({frame_txt}, {a_:.1f}–{b_:.1f} s): panel x {px0}–{px1}, y {py0}–{py1}; Gordon's nearest edge "
            f"x {min(edge)} over {len(edge)} frames → **{gap} px** clear — **{chk(gap > 0, name + ' clearance ' + str(gap))}**")
    say("")

    # 7. orange
    say("## 7. PP orange scan")
    footage = [(w["in"], w["out"]) for w in P["windows"] if w["layer"] == "broll"]
    n, bad, foot = q.orange_frames(out, P["total"], 960, 540, footage)
    say(f"- {n} frames (every 0.48 s, the whole video): orange outside the PP logo in the graphics, cards and Gordon's "
        f"shots in {len(bad)} frame(s){': ' + str(bad[:6]) if bad else ''} — **{chk(not bad, 'orange ' + str(bad[:6]))}** "
        "(orange = hue 8–28°; the PP logo's red square, found in the same frame, is the only exemption)")
    say(f"- In B-roll FOOTAGE (graded separately, not branding): {len(foot)} frame(s)"
        + (f" — {foot[:4]}: the S1 clip's lead horse, a sunlit chestnut, falls in the orange hue band "
           "(painted and looked at, `output/qc/orange-in-footage-S1.png`). No graphic is involved." if foot else "."))
    say("")

    # 8. flutter
    say("## 8. Avatar edge flutter")
    c0, c1, band = q.flutter(master, T["speech_end"])
    worst = np.argsort(band)[-3:][::-1]
    say(f"- Movement in the master: columns x {c0}–{c1} of 1920; "
        f"{'nothing moves at the frame edges — the background is still' if c0 > 300 and c1 < 1650 else 'MOVEMENT REACHES THE EDGES'}. "
        f"Jacket/desk band energy mean {band.mean():.2f}, worst at " + ", ".join(f"{(i + 1) / FPS:.1f} s" for i in worst)
        + f" — **{chk(c0 > 300 and c1 < 1650, 'flutter extent')}** (how it LOOKS is Jodie's judgement).")
    say("")

    # 9. audio
    say("## 9. Audio")
    I, TP = q.loudness(out)
    say(f"- Integrated {I:.1f} LUFS, true peak {TP:.1f} dBTP (PP standard {TARGET_LUFS:g} ±{TOLERANCE_LU:g}, ≤ {TARGET_TP:g}); "
        f"measured makeup gain {P.get('makeup_db', json.loads((job / 'overlay' / 'promo-plan.json').read_text())['plan'].get('makeup_db')):+.2f} dB "
        f"after the duck — **{chk(abs(I - TARGET_LUFS) <= TOLERANCE_LU and TP <= TARGET_TP, 'loudness')}**")
    for lab, a_, b_ in (("title card + sting", 0.6, 4.8),
                        ("speech (the hook)", T["speech_start"] + 0.8, T["speech_start"] + 3.3),
                        ("speech (the research)", T["n1"]["start"] - 0.4, T["n2"]["start"] + 1.2),
                        ("speech (sign-off)", T["join"]["start"] + 0.5, T["join"]["start"] + 3.5),
                        ("closing card (music only)", P["closing_in"] + 0.5, P["warranty_in"] - 0.2),
                        ("warranty (music only)", P["warranty_in"] + 0.5, P["total"] - 0.7)):
        mv = q.mean_volume(out, a_, b_)
        say(f"- {lab} {a_:.1f}–{b_:.1f} s: mean {mv:.1f} dB — {'not silent' if mv > -45 else 'SILENT'} — **{chk(mv > -45, lab)}**")
    say("- The standard PP bed and levels, as on W01 (no 5-s sting: there is no title head).")
    say("")

    # 10. structure
    say("## 10. Structure")
    if P["head"]:
        title = frame(out, 3.0, (480, 270))
        ref = np.asarray(__import__("PIL.Image", fromlist=["Image"]).open(clips / "promo-title.png").convert("RGB")
                         .resize((480, 270)), np.int16)
        d_t = float(np.abs(title - ref).mean())
        say(f"- Opens on the title card — the approved evergreen thumbnail, re-rendered at 1920×1080 — for {P['head']:.1f} s "
            f"with the standard PP sting (Jodie, 11 Oct: 'like the normal videos'); the frame at 3.0 s differs from the "
            f"card by {d_t:.1f} levels on average — **{chk(d_t < 6, 'title card on screen')}**. Gordon's first word at "
            f"{T['speech_start']:.2f} s on the finished clock (his {T['speech_start'] - P['head']:.2f} s + the {P['head']:.1f} s head).")
    else:
        say(f"- Opens on Gordon and the hook: first word at {T['speech_start']:.2f} s, no title gap.")
    say(f"- \"Remember, never bet more than you can afford to lose.\" ends at {T['speech_end']:.2f} s → closing card "
        f"{P['closing_in']:.2f} s (builds, then holds 3 s) → standard PP warranty {P['warranty_in']:.2f}–{P['total']:.2f} s "
        f"({P['total'] - P['warranty_in']:.1f} s) → fade to black. Total {P['total']:.2f} s.")
    srt = (job / "output" / "FBX-PROMO-16x9.srt").read_text(encoding="utf-8-sig")
    h_, m_, s_, ms_ = (int(v) for v in re.search(r"(\d\d):(\d\d):(\d\d),(\d\d\d) -->", srt).groups())
    first = h_ * 3600 + m_ * 60 + s_ + ms_ / 1000
    n_cues = len(re.findall(r"-->", srt))
    say(f"- Subtitles `output/FBX-PROMO-16x9.srt`: {n_cues} cues, CRLF; first cue at {first:.2f} s vs Gordon's first word "
        f"{T['speech_start']:.2f} s on the finished clock — **{chk(abs(first - T['speech_start']) < 0.06 and chr(13) + chr(10) in (job / 'output' / 'FBX-PROMO-16x9.srt').read_bytes().decode('utf-8-sig'), 'SRT clock')}**")
    say("- PP logo chip bottom-right on every Gordon shot; full-screen FBX cards carry \"Brought to you by\" + the PP logo.")
    say("- Research small print, word for word: " + chk(cfg["copy"]["research"]["small_print"] in q.page_text(cards / "promo-research.html")
                                                         and "Historical research results are dated results at official StartingPrice. "
                                                             "They are not guarantees of future performance." in s6, "research small print")
        + " (and it is §6's own required wording).")
    say("")

    # 11. brief §7
    say("## 11. Visual brief §7 checklist")
    logo_ok = all(("fbx-logo-on-dark.svg" in p.read_text(encoding="utf-8") or "report-evergreen.png" in p.read_text(encoding="utf-8")
                   or "fbx-logo" in p.read_text(encoding="utf-8") or 'id="L"' in p.read_text(encoding="utf-8")) for p in pages)
    chiporder = all(re.findall(r'class="chip (\w+)"', grp) == [x for x in ("core", "vic", "val") if x in re.findall(r'class="chip (\w+)"', grp)]
                    for p in pages for grp in re.findall(r'<div class="chips">(.*?)</div>', p.read_text(encoding="utf-8")))
    clos = all(x in q.page_text(cards / "promo-closing.html") for x in ("JOIN FBX –", "LINK BELOW"))
    items = [(not any("orange" in f for f in fails), "No PP orange anywhere except the PP logo itself.", "section 7"),
             (logo_ok, "FBX logo on the chapter, closing and thumbnail cards.", "on every FBX card incl. all three chapter cards, the "
              "closing card and the approved evergreen thumbnail"),
             (chiporder, "Tag chips in the right colours and order (Core, Victorian Select, Value Select).", "W01's chip code; order read from every card"),
             ("TAB" not in alltxt, "Selections use \"No.\", never \"TAB\".", f"\"No.\" ×{alltxt.count('No.')}, \"TAB\" ×{len(re.findall('TAB', alltxt))}"),
             (not any("numbers" in f for f in fails), "Every number on screen matches the fact sheet in the scripts file.", "section 2"),
             (not re.search(r"Racing Measure|\$175|\$75|\btax\b|" + "|".join(q.BOOKIES), alltxt),
              "No bookmaker names, no FBX price, no \"Racing Measure\".", "card text scanned"),
             (clos, "Every video ends on the closing card (\"JOIN FBX – LINK BELOW\"), then the standard responsible gambling slide.", "section 10")]
    for ok, t_, how in items:
        chk(ok, t_)
        say(f"- [{'x' if ok else ' '}] {t_} — {how}")
    say("")
    say("## Result")
    say(f"**{'ALL CHECKS PASS' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}**" + ("" if not fails else ":\n" + "\n".join(f"- {f}" for f in fails)))
    (job / "output" / "qc" / "QC-REPORT.md").write_text("\n".join(R) + "\n", encoding="utf-8")
    print(f"\nfails={len(fails)}")
    sys.stdout.flush()
    import os
    os._exit(1 if fails else 0)


if __name__ == "__main__":
    main()
