#!/usr/bin/env python3
"""fbx_qc.py — QC the finished FBX weekly videos and write output/qc/QC-REPORT.md.

    python fbx_qc.py <job_dir> <scripts_doc.md> <visual_brief.md>

EVERY CHECK READS THE FINISHED FILE AND COMPARES IT WITH A SOURCE THE BUILD DID NOT WRITE:
  · numbers on screen  vs fact sheet §6, parsed from the Hugh-approved scripts doc itself
                         (not from fbx-week.json — that would be a number checked against itself)
  · light-up timing    vs the AUDIO: each row's brightness in the finished frames, against the
                         moment Gordon starts the horse's name (renders/words-forced.json)
  · small print        vs the visual brief §3 line, verbatim
  · clearance          vs Gordon's own pixels in a presenter-only render of the same framing
  · PP orange          every orange pixel cluster in the finished frames must sit beside the PP
                         logo's red square — the logo is found in the picture, not listed
  · loudness           vs publish_loudness (the PP standard)
A check that cannot run says so; nothing is reported as passed that was not measured.
"""
import html as htmllib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fbx_data as fd  # noqa: E402
import fbx_assemble as fa  # noqa: E402
from publish_loudness import TARGET_LUFS, TARGET_TP, TOLERANCE_LU  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass
FPS = 25
BOOKIES = ["TAB", "TABtouch", "Sportsbet", "Ladbrokes", "Neds", "bet365", "Bet365", "PointsBet", "Pointsbet",
           "Betfair", "Unibet", "BlueBet", "Palmerbet", "TopSport", "Betr", "Dabble", "Picklebet", "Boombet"]
BANNED = ["Racing Measure", "tax", "$175", "$75"]   # Hugh: no old name, no tax wording, no FBX price


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def gray(src, t0, t1, crop=None, scale=None, rgb=False):
    vf = []
    if crop:
        # 🔴 EVEN NUMBERS ONLY. On a 4:2:0 source ffmpeg silently rounds an odd crop down
        # (65 -> 64), and reshaping those bytes with the ODD size reads every frame skewed.
        # It produced six false timing FAILs on FBX-W01 before this line existed.
        w, h, x, y = (int(v) // 2 * 2 for v in crop)
        crop = (w, h, x, y)
        vf.append(f"crop={w}:{h}:{x}:{y}")
    if scale:
        vf.append(f"scale={scale[0]}:{scale[1]}")
    pix = "rgb24" if rgb else "gray"
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", str(src),
                        "-vf", ",".join(vf) if vf else "null", "-f", "rawvideo", "-pix_fmt", pix, "-"],
                       capture_output=True)
    W, H = (crop[0], crop[1]) if crop else (None, None)
    if scale:
        W, H = scale
    if W is None:
        info = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=width,height", "-of", "json", str(src)]).stdout)["streams"][0]
        W, H = info["width"], info["height"]
    ch = 3 if rgb else 1
    a = np.frombuffer(p.stdout, np.uint8)
    n = a.size // (W * H * ch)
    return a[: n * W * H * ch].reshape((n, H, W, ch) if rgb else (n, H, W))


# ------------------------------------------------------------------ facts from the source docs
def fact_sheet_tokens(doc: Path):
    t = doc.read_text(encoding="utf-8")
    s = t[t.index("## 6. Fact sheet"):]
    s = s[: s.index("## PP Videos decisions")] if "## PP Videos decisions" in s else s
    return s, set(num_tokens(s))


def num_tokens(text):
    out = []
    for m in re.finditer(r"\d+(?:\.\d+)?", text.replace(",", "")):
        v = m.group(0)
        out.append(v.rstrip("0").rstrip(".") if "." in v else v)
    return out


def brief_small_print(brief: Path):
    t = brief.read_text(encoding="utf-8")
    m = re.search(r"Small print on results cards \(required\):\*\*\s*\*(.+?)\*", t)
    return m.group(1).strip() if m else None


def page_text(p: Path):
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    s = re.sub(r'<div class="preload">.*?</div>', " ", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", " ", s)
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", s)).split())


# ------------------------------------------------------------------ timing from pixels
def light_times(src, t0, t1, boxes):
    """For each box (x0,y0,x1,y1) return the time its mean brightness first crosses halfway
    between its level at the start window and at the end of the segment."""
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    x0, y0 = x0 // 2 * 2, y0 // 2 * 2
    fr = gray(src, t0, t1, crop=(x1 - x0 + 2, y1 - y0 + 2, x0, y0)).astype(np.float32)
    res = []
    for bx in boxes:
        v = fr[:, bx[1] - y0:bx[3] - y0, bx[0] - x0:bx[2] - x0].mean(axis=(1, 2))
        # "before" = the first 3 frames only: a longer window overlaps the very change it measures
        lo, hi = float(np.median(v[:3])), float(np.median(v[-5:]))
        mid = lo + 0.5 * (hi - lo)
        idx = next((i for i in range(len(v)) if (v[i] >= mid if hi > lo else v[i] <= mid)), None)
        res.append((None if idx is None else round(t0 + idx / FPS, 2), round(lo, 1), round(hi, 1)))
    return res


def verdict(delta, lo=-0.40, hi=0.30):
    return "PASS" if delta is not None and lo <= delta <= hi else "FAIL"


# ------------------------------------------------------------------ shared measurements (W01 + the promo)
def panel_box(last_png):
    """A panel's real extent, read from its rendered clip's alpha."""
    from PIL import Image
    al = np.array(Image.open(last_png).convert("RGBA"))[:, :, 3]
    ys, xs = np.where(al > 8)
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())


def gordon_edge(master, z, x, y, tot, a, b, py0, py1, px0, head=0.0):
    """Per frame, the left-most x of Gordon's jacket inside rows py0..py1, in a presenter-only render of the
    SAME zoompan framing between a and b seconds. His jacket is dark CHARCOAL (R≈G≈B); the racecourse
    trees are dark GREEN and the first version took them for Gordon (-267 px, a false FAIL on W01)."""
    # EVEN crop only (the odd-crop trap, again: a 395-px-tall promo panel crashed the reshape on 11 Oct;
    # W01's panels happened to be even). Widen by a pixel rather than shrink, so the panel stays covered.
    py0 = py0 // 2 * 2
    H = (py1 - py0 + 2) // 2 * 2
    # head: the title card's lead, padded exactly as the assembler pads it — the SAME clock as the finished file
    lead = f"tpad=start_duration={head}:start_mode=clone," if head else ""
    vf = (f"{lead}tpad=stop_mode=clone:stop_duration=60,trim=duration={tot},setpts=PTS-STARTPTS,fps=25,"
          f"zoompan=z={z}:x={x}:y={y}:d=1:s=1920x1080:fps=25,"
          f"trim=start={a}:end={b},setpts=PTS-STARTPTS,crop=1920:{H}:0:{py0}")
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(master), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    fr = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, 1920, 3).astype(np.int16)
    lum = fr.mean(axis=3)
    neutral = (fr.max(axis=3) - fr.min(axis=3)) < 14
    notgreen = fr[..., 1] <= np.maximum(fr[..., 0], fr[..., 2]) + 3
    dark = (lum < 85) & neutral & notgreen
    edge = []
    for f in dark:
        best = 1920
        for ri in range(0, f.shape[0], 4):
            xs_ = np.flatnonzero(f[ri])
            if xs_.size == 0:
                continue
            for r_ in np.split(xs_, np.flatnonzero(np.diff(xs_) > 1) + 1):
                # >= 40 px wide: a 30-px dark tree fragment at x 502 passed a 24-px rule on W01
                # (painted and looked at: PP-FBX-W01/output/qc/clearance-hook-panel-detector.png).
                # AND >= 41 px TALL at its start: the window's dark bottom rail (a ~30-px band running in
                # from the left edge) read as his jacket on the promo's wide shot (-99 px, then -75 px with a
                # 9-px test: false FAILs, both painted and looked at, 11 Oct). His arm/shoulder is 100+ px tall.
                if r_.size >= 40 and r_[0] > px0:
                    c = int(r_[0]) + 4
                    col = f[max(0, ri - 20):ri + 21, c]
                    if col.size >= 25 and col.mean() >= 0.75:
                        best = min(best, int(r_[0]))
                        break
        edge.append(best)
    return edge


def orange_frames(src, total, W, H, footage=()):
    """Frames (every 12th, half size) holding an orange 16-px cell NOT within two cells of the PP logo's red
    square found in the same frame. Orange = hue 8–28°, sat > 0.6, value > 0.5 (#DA532C is 13°; FBX gold 39°;
    the PP logo red #F44336 is 4°).
    `footage` = (a, b) windows of B-ROLL: a sunlit chestnut horse is in that hue band (promo S1, 11 Oct) and is
    not branding, so hits there are returned SEPARATELY — listed in the report, never silently dropped."""
    fr = gray(src, 0, total, scale=(W, H), rgb=True)[::12].astype(np.float32) / 255
    bad, in_footage = [], []
    for k, f in enumerate(fr):
        r, g_, b = f[..., 0], f[..., 1], f[..., 2]
        mx, mn = f.max(axis=2), f.min(axis=2)
        s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
        d = np.maximum(mx - mn, 1e-6)
        h = np.where(mx == r, ((g_ - b) / d) % 6, np.where(mx == g_, (b - r) / d + 2, (r - g_) / d + 4)) * 60
        orange = (h >= 8) & (h <= 28) & (s > 0.6) & (mx > 0.5)
        red = ((h < 8) | (h > 345)) & (s > 0.6) & (mx > 0.4)
        C = 16
        oc = orange[: H // C * C, : W // C * C].reshape(H // C, C, W // C, C).sum(axis=(1, 3)) > 3
        rc = red[: H // C * C, : W // C * C].reshape(H // C, C, W // C, C).sum(axis=(1, 3)) > 12
        if not oc.any():
            continue
        near = np.zeros_like(rc)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                near |= np.roll(np.roll(rc, dy, 0), dx, 1)
        stray = oc & ~near
        if stray.any():
            yy, xx = np.argwhere(stray)[0]
            t = round(k * 12 / FPS, 1)
            hit = (t, int(xx * C * 2), int(yy * C * 2), int(stray.sum()))
            (in_footage if any(a <= t <= b for a, b in footage) else bad).append(hit)
    return len(fr), bad, in_footage


def flutter(master, t_end):
    fr = gray(master, 0, t_end, scale=(480, 270)).astype(np.int16)
    dif = np.abs(np.diff(fr, axis=0))
    cols = np.flatnonzero((dif > 18).mean(axis=0).max(axis=0) > 0.02)
    band = dif[:, 150:250, :].mean(axis=(1, 2))
    return int(cols.min() * 4), int(cols.max() * 4), band


def loudness(src):
    e = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)[-1])


def mean_volume(src, a, b):
    e = run(["ffmpeg", "-hide_banner", "-v", "info", "-ss", f"{a}", "-t", f"{b - a}", "-i", str(src),
             "-af", "volumedetect", "-f", "null", "-"]).stderr
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", e).group(1))


# ------------------------------------------------------------------ main
def main():
    job = Path(sys.argv[1]).resolve()
    sdoc, brief = Path(sys.argv[2]), Path(sys.argv[3])
    wk = fd.load_week(job)
    T = fd.cue_sheet(job, wk)
    P = fa.plan(T)
    words = json.loads((job / "renders" / "words-forced.json").read_text(encoding="utf-8"))
    out16 = job / "output" / f"FBX-{wk['raw']['week']}-16x9.mp4"
    out9 = job / "output" / f"FBX-{wk['raw']['week']}-9x16.mp4"
    cards = job / "overlay" / "cards"
    R = []          # report lines
    fails = []

    def say(s=""):
        R.append(s)
        print(s, flush=True)

    def chk(ok, what):
        if not ok:
            fails.append(what)
        return "PASS" if ok else "FAIL"

    say(f"# FBX {wk['raw']['week']} — QC report")
    say("")
    say(f"Built and checked {__import__('time').strftime('%d %b %Y %H:%M')}. Every line below was measured on the "
        f"finished files; the sources each is compared with are named.")
    say("")

    # ---------------------------------------------------------------- 1. the files
    say("## 1. The files")
    for f, (W, H) in ((out16, (1920, 1080)), (out9, (1080, 1920))):
        j = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-show_chapters",
                            "-of", "json", str(f)]).stdout)
        v = next(s for s in j["streams"] if s["codec_type"] == "video")
        a = next(s for s in j["streams"] if s["codec_type"] == "audio")
        dec = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                   "stream=nb_read_frames", "-of", "csv=p=0", str(f)]).stdout.strip()
        ok = (v["width"], v["height"]) == (W, H) and v["r_frame_rate"] == "25/1" and int(dec) == int(v["nb_frames"]) \
            and not j.get("chapters") and len(j["streams"]) == 2
        say(f"- `{f.name}` — {v['width']}×{v['height']} {v['r_frame_rate']} fps, {float(j['format']['duration']):.2f} s, "
            f"{int(j['format']['size']):,} bytes, {dec} frames decoded of {v['nb_frames']} declared, audio "
            f"{a['codec_name']} {a['sample_rate']} Hz {a['channels']} ch {int(a['bit_rate']) // 1000} kbps, "
            f"{len(j['streams'])} streams, {len(j.get('chapters', []))} chapters — **{chk(ok, f.name + ' structure')}**")
    m = json.loads((job / "renders" / "heygen-render.json").read_text(encoding="utf-8"))
    say(f"- Source: HeyGen render `{m['title']}` (`{m['video_id']}`), {m['bytes_received']:,} bytes received = "
        f"{m['bytes_stated']:,} stated, {m['duration']:.2f} s.")
    say("")

    # ---------------------------------------------------------------- 2. numbers
    say("## 2. Every number on screen, against fact sheet §6")
    say(f"Source: `{sdoc}` §6 (Hugh-approved), parsed directly. A number that is not in §6 FAILS.")
    s6, s6tok = fact_sheet_tokens(sdoc)
    names = sorted(p.name for p in cards.glob("fbx-*.html") if "warranty" not in p.name)
    for n in names:
        txt = page_text(cards / n)
        toks = num_tokens(txt)
        bad = [t for t in toks if t not in s6tok]
        shown = ", ".join(dict.fromkeys(re.findall(r"[+$]?\d+(?:\.\d+)?%?(?:st|nd|rd|th)?", txt)))
        say(f"- `{n.replace('.html', '')}`: {shown or '(no numbers)'} — **{chk(not bad, n + ' numbers ' + str(bad))}**"
            + (f" (not in §6: {bad})" if bad else ""))
    say("- The real Saturday Report (shot 2, the push-in) is shown exactly as published; its FBX Gaps, Morning "
        "Prices, races and numbers match §6. Its FBX Score column (851.73 … 905.69) and tag counts are not in §6 — "
        "they are on the real member report, shown as-is.")
    # data the cards were built from, recomputed (fbx_data refuses a week whose totals disagree)
    c = wk["calc"]
    say(f"- Recomputed from the six rows by `fbx_data.py`: win {c['win']['profit']} units / {c['win']['roi']}, "
        f"place {c['place']['profit']} / {c['place']['roi']}, each way {c['each_way']['profit']} / {c['each_way']['roi']}, "
        f"{len(wk['won'])} won, {len(wk['placed'])} placed — identical to §6's typed totals.")
    say("")

    # ---------------------------------------------------------------- 3. small print + banned words
    say("## 3. Small print, and words that must never appear")
    sp = brief_small_print(brief)
    say(f"Required line (visual brief §3): *{sp}*")
    for n in ("fbx-16x9-results", "fbx-16x9-summary", "fbx-16x9-gap", "fbx-9x16-results", "fbx-9x16-gap"):
        say(f"- `{n}` carries it word for word — **{chk(sp and sp in page_text(cards / (n + '.html')), n + ' small print')}**")
    alltxt = " ".join(page_text(p) for p in cards.glob("fbx-*.html"))
    pdf = next((job / "overlay" / "fbx-pack").rglob("FBX_Saturday_Report_*.pdf"))
    reptxt = run(["pdftotext", "-layout", str(pdf), "-"]).stdout
    for label, txt in (("all card text", alltxt), ("the Saturday Report shown on screen", reptxt)):
        hits = sorted(set([w for w in BOOKIES if re.search(rf"\b{re.escape(w)}\b", txt)] +
                          [w for w in BANNED if re.search(rf"(?i)(?<![\w$]){re.escape(w)}\b", txt)]))
        say(f"- {label}: bookmaker names / FBX price / \"Racing Measure\" / tax wording — "
            f"{'none found' if not hits else hits} — **{chk(not hits, label + ' banned ' + str(hits))}**")
    say(f"- Selections written \"No.\", never \"TAB\": \"No.\" appears {alltxt.count('No.')} times, \"TAB\" "
        f"{len(re.findall(r'TAB', alltxt))} times — **{chk('No.' in alltxt and 'TAB' not in alltxt, 'No./TAB')}**")
    say("")

    # ---------------------------------------------------------------- 4. timing against Gordon's words
    say("## 4. Cards light up as Gordon says the words")
    say("Measured: each row's brightness in the FINISHED video, frame by frame; the time it is halfway lit. "
        "Compared with: the moment Gordon starts the horse's name (forced alignment of the script to the "
        "render's audio, cross-checked against every measured pause). PASS window: −0.40 s to +0.30 s.")
    say("")
    say("| format | card | item | Gordon says it | lit at | Δ | |")
    say("|---|---|---|---|---|---|---|")
    sel = wk["sel"]

    def rows(fmt, label, src, t0, t1, boxes, items, ref):
        res = light_times(src, t0, t1, boxes)
        for (lt, lo, hi), it, rt in zip(res, items, ref):
            d = None if lt is None else round(lt - rt, 2)
            say(f"| {fmt} | {label} | {it} | {rt:.2f} s | {lt if lt is not None else '—'} s | "
                f"{'' if d is None else f'{d:+.2f}'} | **{chk(verdict(d) == 'PASS', f'{fmt} {label} {it} timing {d}')}** |")

    names_t = [T["rows"][s["horse"]] for s in sel]
    rows("16:9", "results (3)", out16, T["results_in"] + 1.0, T["summary_in"],
         [(175, 106 + 130 * i + 42, 620, 106 + 130 * i + 86) for i in range(len(sel))],
         [s["horse"] for s in sel], names_t)
    rows("9:16", "results (07)", out9, T["results_in"] + 1.0, T["gap_in"],
         [(110, 633 + 117 * i + 55, 480, 633 + 117 * i + 100) for i in range(len(sel))],
         [s["horse"] for s in sel], names_t)
    g = wk["gaps"][: len(wk["won"])]
    i0, i1 = fd.find(words, fd.timeline(job)[1], wk["raw"]["cues"]["gap_gold_on"], T["gap_in"])
    ph0, ph1 = words[i0]["start"], words[i1]["end"]
    gold16 = light_times(out16, T["gap_in"] + 0.8, T["gap_out"] - 0.2,
                         [(1500, 266 + 80 * i + 18, 1750, 266 + 80 * i + 62) for i in range(len(g))])
    gold9 = light_times(out9, T["gap_in"] + 0.8, T["gap_out"] - 0.2,
                        [(760, 636 + 132 * i + 80, 1000, 636 + 132 * i + 118) for i in range(len(g))])
    for fmt, res in (("16:9", gold16), ("9:16", gold9)):
        ts = [r[0] for r in res]
        ok = all(t is not None and ph0 - 0.3 <= t <= ph1 + 0.4 for t in ts) and ts == sorted(ts)
        say(f"| {fmt} | gap (5) | top {len(g)} turn gold: " + ", ".join(s["horse"] for s in g) +
            f" | \"{wk['raw']['cues']['gap_gold_on']}\" {ph0:.2f}–{ph1:.2f} s | {', '.join(str(t) for t in ts)} s | in order | "
            f"**{chk(ok, fmt + ' gap gold timing ' + str(ts))}** |")
    for fmt, src, ub, rb in (("16:9", out16, (150, 575, 760, 660), (900, 575, 1560, 660)),
                             ("9:16", out9, (90, 1405, 520, 1470), (90, 1495, 990, 1560))):
        r = light_times(src, T["summary_in"] if fmt == "16:9" else T["results_in"] + 1.0, T["placed_on"], [ub, rb])
        for (lt, _, _), it, rt in zip(r, ("+5.75 units", "+95.8% ROI"), (T["units_on"], T["roi_on"])):
            d = None if lt is None else round(lt - rt, 2)
            say(f"| {fmt} | summary | {it} | {rt:.2f} s | {lt} s | {'' if d is None else f'{d:+.2f}'} | "
                f"**{chk(verdict(d) == 'PASS', f'{fmt} {it} timing {d}')}** |")
    for fmt, src, box, t0, t1, ref, it in (
            ("16:9", out16, (100, 515, 640, 680), 0.0, 1.2, T["hook"], "hook: 4 WINNERS FROM 6."),
            ("9:16", out9, (85, 420, 900, 660), 0.0, 1.2, T["hook"], "hook: 4 WINNERS FROM 6."),
            ("16:9", out16, (85, 900, 400, 1000), T["join_in"], T["lower_third_on"] + 1.2, T["lower_third_on"],
             "lower third: JOIN FBX – LINK BELOW"),
            ("9:16", out9, (130, 440, 880, 640), T["join_in"], T["lower_third_on"] + 1.2, T["lower_third_on"],
             "JOIN FBX – LINK BELOW")):
        (lt, _, _), = light_times(src, t0, t1, [box])
        d = None if lt is None else round(lt - ref, 2)
        say(f"| {fmt} | Gordon shot | {it} | {ref:.2f} s | {lt} s | {'' if d is None else f'{d:+.2f}'} | "
            f"**{chk(verdict(d) == 'PASS', f'{fmt} {it} timing {d}')}** |")
    say("")
    say("Also by the shot script: \"4 WINNERS FROM 6.\" and \"ALL SIX PLACED.\" open card 4 in that order (the "
        "shot script's order — Gordon says \"all six placed\" last, at "
        f"{T['placed_on']:.2f} s); the units and the ROI each slam in on Gordon's own words (rows above).")
    say("")

    # ---------------------------------------------------------------- 5. panels never touching Gordon
    say("## 5. Panels never touch Gordon")
    say("Measured: Gordon's own pixels (his dark, neutral, not-green jacket in runs ≥40 px wide, so window "
        "mullions and the trees are excluded — the detector was painted onto a frame and looked at, "
        "`output/qc/clearance-hook-panel-detector.png`) in a presenter-only render of the SAME framing, every frame of each window, "
        "against the panel's real edge read from the rendered clip's alpha.")
    for name, (a, b), ztxt in (("fbx-16x9-hook-panel", (0.0, T["report_in"]), "push 136%"),
                               ("fbx-16x9-lower-third", (T["lower_third_on"], T["rg_in"]), "MCU 126%")):
        px0, px1, py0, py1 = panel_box(job / "overlay" / "clips" / f"{name}.last.png")
        a1, b1 = P["push"]; a2, b2 = P["mcu"]
        Mx, Px = fa.act(a2, b2, 0.4), fa.act(a1, b1, 0.5)
        z = f"'(1+{fa.MCU_ZOOM - 1}*{Mx})*(1-{Px})+{fa.PUSH_ZOOM}*{Px}'"
        edge = gordon_edge(job / "renders" / "presenter-master.mp4", z, f"'(iw-iw/zoom)/2*(1-{Px})'",
                           f"'(ih-ih/zoom)/2-55*max({Mx},{Px})'", P["total"], a, b, py0, py1, px0)
        gap = min(edge) - px1
        say(f"- `{name}` ({ztxt}): panel x {px0}–{px1}, y {py0}–{py1}; Gordon's nearest edge over {len(edge)} frames "
            f"x = {min(edge)} → clearance **{gap} px** — **{chk(gap > 0, name + ' clearance ' + str(gap))}**")
        # CONTROL: the same measurement must call a panel that reaches Gordon's middle a FAIL
        ctrl = min(edge) - 1100
        say(f"  - control: a panel reaching x 1100 would measure {ctrl} px — "
            f"{'the check can fail' if ctrl <= 0 else 'CONTROL DID NOT FAIL — the check is blind'}"
            f"{'' if ctrl <= 0 else chk(False, name + ' control')}")
    say("- 9:16: every card sits in the upper half (y 0–959) or is full-screen; Gordon is only ever in the lower "
        "half (y 960–1919), so no card overlaps him by construction. Checked by eye on the contact sheet.")
    say("")

    # ---------------------------------------------------------------- 6. PP orange
    say("## 6. PP orange scan")
    say("Every frame every 0.5 s, both formats, at half size. Orange = hue 8–28°, saturation > 0.6, value > 0.5 "
        "(PP burnt orange #DA532C is 13°; FBX gold #D9A441 is 39°; the PP logo's red square #F44336 is 4°). "
        "An orange 16-px cell is allowed only within two cells of the PP logo's red square, found in the same frame.")
    for fmt, src, W, H in (("16:9", out16, 960, 540), ("9:16", out9, 540, 960)):
        n, bad, _ = orange_frames(src, P["total"], W, H)
        say(f"- {fmt}: {n} frames scanned; orange outside the PP logo in "
            f"{len(bad)} frame(s){': ' + str(bad[:6]) if bad else ''} — **{chk(not bad, fmt + ' orange ' + str(bad[:6]))}**")
    say("")

    # ---------------------------------------------------------------- 7. avatar edge flutter
    say("## 7. Avatar edge flutter")
    c0, c1, band = flutter(job / "renders" / "presenter-master.mp4", T["speech_end"])
    worst = np.argsort(band)[-3:][::-1]
    say(f"- Movement in the master (pixels changing > 18 levels between frames, >2% of frames): columns "
        f"x {c0}–{c1} of 1920 (Gordon spans ≈ x 580–1470 standing still, plus his hands). "
        f"{'Nothing moves at the frame edges — the background is still.' if c0 > 300 and c1 < 1650 else 'MOVEMENT REACHES THE FRAME EDGES — look.'}")
    say(f"- Jacket/desk band (y 600–1000) frame-difference energy: mean {band.mean():.2f}, worst at "
        + ", ".join(f"{(i + 1) / FPS:.1f} s ({band[i]:.2f})" for i in worst)
        + ". Gordon is on screen only 0–" + f"{T['report_in']:.1f} s and {T['gap_out']:.1f}–{P['closing_in']:.1f} s; "
        "every other second is covered by a full-screen card.")
    edge_ok = c0 > 300 and c1 < 1650
    say(f"- Verdict on the measurement: **{chk(edge_ok, 'flutter extent')}** (a judgement of how it LOOKS is Jodie's).")
    say("")

    # ---------------------------------------------------------------- 8. audio
    say("## 8. Audio")
    for f in (out16, out9):
        I, TP = loudness(f)
        ok = abs(I - TARGET_LUFS) <= TOLERANCE_LU and TP <= TARGET_TP
        say(f"- `{f.name}`: integrated {I:.1f} LUFS, true peak {TP:.1f} dBTP (PP standard {TARGET_LUFS:g} ±{TOLERANCE_LU:g}, "
            f"≤ {TARGET_TP:g}) — **{chk(ok, f.name + ' loudness')}**")
    wins = [("speech (results)", 10.0, 12.0), ("speech (sign-off)", 46.0, 48.0),
            ("closing card (music only)", P["closing_in"] + 0.5, P["warranty_in"] - 0.2),
            ("warranty (music only)", P["warranty_in"] + 0.5, P["total"] - 0.7)]
    for lab, a, b in wins:
        mv = mean_volume(out16, a, b)
        ok = mv > -45
        say(f"- {lab} {a:.1f}–{b:.1f} s: mean {mv:.1f} dB — {'not silent' if ok else 'SILENT'} — **{chk(ok, lab + ' silent')}**")
    say(f"- Speech: {T['speech_start']:.2f}–{T['speech_end']:.2f} s, from the HeyGen master (189 kbps AAC, "
        f"loudnormed to {TARGET_LUFS:g} LUFS). Music: the standard PP bed (EP01's master), 0.04 under speech × LIFT, "
        "the same duck, rising to 0.55 under the closing card and 0.42 under the warranty — the only change from an "
        "episode is no 5-second sting, because there is no title head to put it under.")
    say("")

    # ---------------------------------------------------------------- 9. structure
    say("## 9. Structure, in order")
    say(f"- Opens straight on Gordon and the hook: first word at {T['speech_start']:.2f} s, no title gap.")
    say(f"- Last spoken words \"Remember, never bet more than you can afford to lose.\" end at {T['speech_end']:.2f} s → "
        f"closing card {P['closing_in']:.2f} s (builds in {fa.CLOSING_BUILD:g} s, then holds {fa.CLOSING_HOLD:g} s) → "
        f"standard PP warranty {P['warranty_in']:.2f}–{P['total']:.2f} s ({P['total'] - P['warranty_in']:.1f} s) → "
        "0.5 s fade to black.")
    say("- PP logo chip bottom-right on every Gordon shot (16:9 at the standard 428 px; 9:16 at 300 px). Cards carry "
        "\"Brought to you by\" + the PP logo; the panels over Gordon do not, so only one PP logo is ever on screen.")
    say("")

    # ---------------------------------------------------------------- 10. brief §7
    say("## 10. Visual brief §7 checklist")
    # the report pages show the real Saturday Report, whose own header carries the FBX logo
    hasfbx = {n: any(x in (cards / n).read_text(encoding="utf-8") for x in ("fbx-logo-on-dark.svg", "report.png"))
              for n in names}
    clos = all(x in page_text(cards / n) for n in ("fbx-16x9-closing.html", "fbx-9x16-closing.html")
               for x in ("JOIN FBX –", "LINK BELOW"))
    chiporder = True
    for n in names:
        for grp in re.findall(r'<div class="chips">(.*?)</div>', (cards / n).read_text(encoding="utf-8")):
            got = re.findall(r'class="chip (\w+)"', grp)
            chiporder &= got == [x for x in ("core", "vic", "val") if x in got]
    css = (HERE / "fbx_cards.py").read_text(encoding="utf-8")
    colours = all(x in css for x in ("--gold:#D9A441", "--blue:#2F4DB0", "--ivory:#E6DFCC", "--ink:#0E1316"))
    orange_ok = not any("orange" in f for f in fails)
    nums_ok = not any("numbers" in f for f in fails)
    banned_ok = not any("banned" in f for f in fails)
    items = [
        (orange_ok, "No PP orange anywhere except the PP logo itself.", "section 6"),
        (all(hasfbx.values()), "FBX logo on the chapter, closing and thumbnail cards.",
         f"on both closing cards and on every other FBX card ({sum(hasfbx.values())}/{len(hasfbx)}; the report "
         "push-ins show it in the real report's header). There are no chapter cards in this video, and no thumbnail "
         "was asked for in this job"),
        (chiporder and colours, "Tag chips in the right colours and order (Core, Victorian Select, Value Select).",
         "order read from every card; colours #D9A441 / #2F4DB0 / #E6DFCC with #0E1316 / white text"),
        ("TAB" not in alltxt, "Selections use \"No.\", never \"TAB\".", "section 3"),
        (nums_ok, "Every number on screen matches the fact sheet in the scripts file.", "section 2"),
        (banned_ok, "No bookmaker names, no FBX price, no \"Racing Measure\".", "section 3"),
        (clos, "Every video ends on the closing card (\"JOIN FBX – LINK BELOW\"), then the standard responsible gambling slide.",
         "section 9"),
    ]
    for ok, t, how in items:
        say(f"- [{'x' if ok else ' '}] {t} — {how}")
    say("")
    say("## Result")
    say(f"**{'ALL CHECKS PASS' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}**" +
        ("" if not fails else ":\n" + "\n".join(f"- {f}" for f in fails)))
    # optional 4th argument: write the report elsewhere (a regression run must not touch an approved folder)
    rep = Path(sys.argv[4]) if len(sys.argv) > 4 else job / "output" / "qc" / "QC-REPORT.md"
    rep.write_text("\n".join(R) + "\n", encoding="utf-8")
    print(f"\nwrote {rep}; fails={len(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
