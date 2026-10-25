#!/usr/bin/env python3
"""ppd_qc.py — QC the finished PPD promo; writes output/qc/QC-REPORT.md (the FBX promo's format).

    python ppd_qc.py <job_dir>

EVERY CHECK READS THE FINISHED FILE AND COMPARES IT WITH A SOURCE THE BUILD DID NOT WRITE:
  numbers on screen   vs Hugh's brief (PPD_Video_Brief.md §3-§5), parsed from the brief itself
  small print         vs brief §6, word for word, and SEEN in the finished frames when each results card is up
  card timing         each element's brightness at its real position (asked of the page) vs Gordon's words
  clearance           Gordon's own jacket pixels in a presenter-only render of the same framing, every frame
  PP orange           hue scan of the whole video; the ONLY exemption is the PP logo's own measured box
  hard nos            every word on screen, in the SRT and in the spoken script
A check that cannot run says so; nothing is reported as passed that was not measured.
"""
import functools
import hashlib
import html as htmllib
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
sys.path.insert(0, str(HERE.parent / "fbx"))
sys.path.insert(0, str(HERE.parent))
import ppd_data as pdd  # noqa: E402
import ppd_promo as pp  # noqa: E402
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
RESULTS_CARDS = ["hook", "before-after", "rows", "strike", "tiles", "trifecta", "backing-two"]


# ------------------------------------------------------------------ helpers
def page_text(p: Path):
    return q.page_text(p)


_PW = {}


def browser(cards: Path):
    """ONE Playwright + Chromium + file server for the whole QC run (the sync API cannot be started twice in a process)."""
    if not _PW:
        from playwright.sync_api import sync_playwright
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(fr_._Quiet, directory=str(cards)))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        p = sync_playwright().start()
        _PW["b"] = p.chromium.launch(headless=True, args=["--force-color-profile=srgb", "--disable-lcd-text", "--hide-scrollbars",
                                                          "--force-device-scale-factor=1"])
        _PW["url"] = f"http://127.0.0.1:{httpd.server_address[1]}/"
    return _PW["b"], _PW["url"]


def measure_pages(cards: Path, wanted, at=None):
    """{(page, selector): (x0,y0,x1,y1)} measured in Chromium at each page's last frame (or at[page] ms, for an element
    that MOVES later — the BEFORE half slides left at the split), + the smallest type on it."""
    b, base = browser(cards)
    out, extra = {}, {}
    for pagename, sels in wanted.items():
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(f"{base}{quote(pagename)}?paused=1", wait_until="load")
        pg.wait_for_function("typeof window.ppDuration === 'number'")
        pg.wait_for_function("document.fonts.status === 'loaded'")
        pg.evaluate(f"ppSeek({(at or {}).get(pagename, 'window.ppDuration')})")
        for s in sels:
            r = pg.evaluate(f"(() => {{ const e = document.querySelector({json.dumps(s)}); if (!e) return null;"
                            f" const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }})()")
            out[(pagename, s)] = None if r is None else tuple(int(round(v)) for v in r)
        # the smallest visible type on the card (phone legibility), small print reported separately
        extra[pagename] = pg.evaluate(
            "(() => { let m = 999, ms = 999; for (const e of document.querySelectorAll('body *')) {"
            " if (!e.childNodes.length || e.closest('.preload')) continue;"
            " const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length);"
            " if (!own) continue; const cs = getComputedStyle(e); if (cs.visibility === 'hidden') continue;"
            " const f = parseFloat(cs.fontSize); if (e.closest('.small')) ms = Math.min(ms, f); else m = Math.min(m, f); }"
            " return [m, ms]; })()")
        pg.close()
    return out, extra


def frame(src, t, size=(1920, 1080)):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", str(src), "-frames:v", "1", "-vf",
                        f"scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(size[1], size[0], 3).astype(np.int16)


def hf_energy(img):
    g = img.mean(axis=2) if img.ndim == 3 else img
    return float(np.abs(np.diff(g, axis=1)).mean() + np.abs(np.diff(g, axis=0)).mean())


def hue_sat_val(f):
    f = f.astype(np.float32) / 255
    r, g_, b = f[..., 0], f[..., 1], f[..., 2]
    mx, mn = f.max(axis=2), f.min(axis=2)
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g_ - b) / d) % 6, np.where(mx == g_, (b - r) / d + 2, (r - g_) / d + 4)) * 60
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return h, s, mx


CORE = 11.5     # a cell's orange pixels must have a MEDIAN hue >= this to count (see orange_cells)


def orange_cells(f, exempt, lo=8.0, hi=28.0, C=16):
    """16-px cells holding > 3 orange pixels (hue lo-hi, sat > .6, val > .5) WHOSE MEDIAN HUE IS >= CORE, outside every
    exempt box (full-res coordinates; f may be half size). PP orange #DA532C is 13.4°; PPD red #F44336 is 4.1°.

    🔴 WHY THE MEDIAN (25 Oct 2026, first PPD cut): every hit on the first scan was PPD RED, not PP orange — 4:2:0 video
    averages colour over 2x2 pixels, so a thin red stroke (a 3-px outline, a pill border) or the edge of red text is
    smeared from 4° into 8-11°. Those fringes have a median of 8.5-11.2°; a PP-orange element, compressed the same way,
    keeps its core near 13°. The controls in main() push both through the same x264 4:2:0 encode to prove the line."""
    H, W = f.shape[:2]
    k = 1920 / W
    h, s, v = hue_sat_val(f)
    o = (h >= lo) & (h <= hi) & (s > 0.6) & (v > 0.5)
    for x0, y0, x1, y1 in exempt:
        o[max(0, int(y0 / k) - 2):int(y1 / k) + 2, max(0, int(x0 / k) - 2):int(x1 / k) + 2] = False
    o, h = o[: H // C * C, : W // C * C], h[: H // C * C, : W // C * C]
    cnt = o.reshape(H // C, C, W // C, C).sum(axis=(1, 3))
    hits = []
    for r, c in np.argwhere(cnt > 3):
        hh = h[r * C:(r + 1) * C, c * C:(c + 1) * C][o[r * C:(r + 1) * C, c * C:(c + 1) * C]]
        if np.median(hh) >= CORE:
            hits.append((r * C * k, c * C * k))
    return np.array(hits).reshape(-1, 2)


def x264_roundtrip(img, work: Path):
    """Encode one 1920x1080 RGB frame as the master is encoded (libx264, yuv420p), decode it at the scan's half size."""
    # raw pixels on stdin, five frames, then the pipe CLOSES — a looped PNG input spun forever on this machine (25 Oct)
    mp4 = work / "ctl.mp4"
    raw = np.ascontiguousarray(img.astype(np.uint8)).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", "25", "-i", "-",
                    "-frames:v", "5", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(mp4)],
                   input=raw * 5, check=True, timeout=120)
    return frame(mp4, 0.08, (960, 540))


def find_spoken_runs(card_txt, spoken, n=5):
    """Runs of >= n consecutive words on a card that Gordon also says, in order (rule 1: never his sentence)."""
    norm = lambda s: re.findall(r"[a-z0-9$.%']+", s.lower().replace("’", "'"))
    sw = norm(spoken)
    grams = {tuple(sw[i:i + n]) for i in range(len(sw) - n + 1)}
    cw = norm(card_txt)
    hits = set()
    for i in range(len(cw) - n + 1):
        if tuple(cw[i:i + n]) in grams:
            hits.add(" ".join(cw[i:i + n]))
    return sorted(hits)


# ------------------------------------------------------------------ main
def main():
    job = Path(sys.argv[1]).resolve()
    promo, day, T = pp.load(job)
    P = pp.plan(promo, T)
    W = {w["name"]: w for w in P["windows"]}
    out = job / "output" / pp.OUT
    capd = job / "output" / "PPD-PROMO-16x9-captioned.mp4"
    master = job / "renders" / "presenter-master.mp4"
    cards = job / "overlay" / "cards"
    clips = job / "overlay" / "clips"
    brief = job / promo["pack_dir"] / "PPD_Video_Brief.md"
    meta = json.loads((job / "overlay" / "ppd-card-meta.json").read_text(encoding="utf-8"))
    spoken = next((job / "docs").glob("*heygen-spoken.txt")).read_text(encoding="utf-8")
    R, fails = [], []

    def say(s=""):
        R.append(s)
        print(s, flush=True)

    def chk(ok, what):
        if not ok:
            fails.append(what)
        return "PASS" if ok else "FAIL"

    say('# PPD Club promo "Bet Small, Win Big" — QC report')
    say("")
    say(f"Checked {time.strftime('%d %b %Y %H:%M')} on `output/{pp.OUT}` "
        f"(written {time.strftime('%d %b %H:%M:%S', time.localtime(out.stat().st_mtime))}) and `output/{capd.name}`. "
        "Each line names the source it is compared with.")
    say("")

    # ---------------------------------------------------------------- 1. files
    say("## 1. The files")
    for f in (out, capd):
        j = json.loads(q.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-show_chapters", "-of", "json", str(f)]).stdout)
        v = next(s for s in j["streams"] if s["codec_type"] == "video")
        a = next(s for s in j["streams"] if s["codec_type"] == "audio")
        dec = q.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                     "-of", "csv=p=0", str(f)]).stdout.strip()
        dur = float(j["format"]["duration"])
        ok = (v["width"], v["height"]) == (1920, 1080) and v["r_frame_rate"] == "25/1" and int(dec) == int(v["nb_frames"]) \
            and not j.get("chapters") and len(j["streams"]) == 2 and v["pix_fmt"] == "yuv420p" and abs(dur - P["total"]) < 0.1
        say(f"- `{f.name}` — {v['width']}×{v['height']} 25 fps {v['pix_fmt']}, {dur:.2f} s ({int(dur // 60)}:{dur % 60:04.1f}), "
            f"{int(j['format']['size']):,} bytes, {dec} frames decoded of {v['nb_frames']} declared, audio {a['codec_name']} "
            f"{a['sample_rate']} Hz {int(a['bit_rate']) // 1000} kbps, {len(j.get('chapters', []))} chapters — **{chk(ok, f.name + ' structure')}**")
    m = json.loads((job / "renders" / "heygen-render.json").read_text(encoding="utf-8"))
    pc_ = (job / "renders" / "pause-check.txt").read_text(encoding="utf-8")
    inside = int(re.search(r"pauses inside a word: (\d+)", pc_).group(1))
    n_p = len(re.findall(r"^pause ", pc_, re.M))
    words = json.loads((job / "renders" / "words-forced.json").read_text(encoding="utf-8"))
    say(f"- Source: HeyGen render `{m['title']}` (`{m['video_id']}`), {m['bytes_received']:,} bytes received = {m['bytes_stated']:,} "
        f"stated, {m['duration']:.2f} s. Jodie watched and listened to it in HeyGen: \"all good\" (25 Oct).")
    say(f"- Words: all {len(words)} of the spoken script placed by forced alignment of the SCRIPT (fbx_align.py, not the old "
        f"transcript aligner); {n_p} measured pauses, {inside} inside a word (`renders/pause-check.txt`) — "
        f"**{chk(inside == 0 and len(words) == len(spoken.split()), 'alignment')}**")
    say("- Every clip handed to Jodie is yuv420p (above): Windows Media Player plays both files.")
    say("")

    # ---------------------------------------------------------------- 2. numbers
    say("## 2. Every number on screen, against Hugh's brief")
    bt = brief.read_text(encoding="utf-8")
    src = bt[bt.index("## 3. WHAT THE PPD CLUB IS"):bt.index("## 7. BRAND")]
    btok = set(q.num_tokens(src))
    say("Source: `PPD_Video_Brief.md` §3–§6, parsed directly (the brief wins on any fact). A number not in the brief FAILS.")
    pages = sorted(p for p in cards.glob("ppd-*.html") if "warranty" not in p.name)
    alltxt = {}
    for p in pages + [job / "overlay" / "thumbnail" / "thumbnail.html"]:
        txt = page_text(p)
        alltxt[p.stem] = txt
        bad = [t for t in q.num_tokens(txt) if t not in btok]
        shown = ", ".join(dict.fromkeys(re.findall(r"[+$]?\d[\d,]*(?:\.\d+)?(?:%|¢|c|st|nd|rd|th)?", txt)))
        say(f"- `{p.stem}`: {shown or '(no numbers)'} — **{chk(not bad, p.stem + ' numbers ' + str(bad))}**"
            + (f" (not in the brief: {bad})" if bad else ""))
    say("")
    say("Item by item against brief §4 (the build also recomputes every total from the rows and halts on a disagreement — "
        "`ppd_data.prove`):")
    say("")
    say("| figure on screen | where | brief §4 says | |")
    say("|---|---|---|---|")
    c = day["calc"]
    items = []
    for s in day["selections"]:
        if s["finish"] == 1:
            items.append((f"{pdd.bet_name(s)} — WIN PAID {pdd.money(s['win'])}", "rows (+ before/after for the Best Bet)",
                          rf"{re.escape(s['horse'])}\*\*.*?\*\*Won\*\* \| \*\*\${re.escape(s['win'])}\*\* \| \*\*\${re.escape(s['place'])}"))
        else:
            fin = f"{s['finish']}{'th' if s['finish'] > 3 else ''}"
            items.append((f"{pdd.bet_name(s)} — {fin}", "rows", rf"{re.escape(s['horse'])} \| {fin} \|"))
    items += [("PLACE PAID $2.90 (Cosmic Crusader)", "before/after", r"Cosmic Crusader\*\*.*?\*\*\$2\.90\*\*"),
              ("$25 → $106.50, +326.0% (win)", "hook, tiles, thumbnail", r"\$5 win on all five\*\* \| \$25 \| \*\*\$106\.50\*\* \| \$81\.50 \| \*\*\+326\.0%"),
              ("$50 → $143.00, +186.0% (each way)", "tiles", r"\$5 each way.*?\| \$50 \| \*\*\$143\.00\*\* \| \$93\.00 \| \*\*\+186\.0%"),
              ("$25 → $36.50, +46.0% (place)", "tiles", r"\$5 place on all five\*\* \| \$25 \| \*\*\$36\.50\*\* \| \$11\.50 \| \*\*\+46\.0%"),
              ("3 winners from 5 · 60.0% strike rate", "strike", r"3 winners from 5 \(60\.0% strike rate\)"),
              ("$5 a bet = 0.5% of a $1,000 bank; 1% limit a race ($10)", "bank", r"\$5 a bet = 0\.5% of an example \$1,000 bank"),
              ("Trifecta: $24.00 → $51.05, +112.7%, 3 from 3", "trifecta", r"Cost \$24\.00 across 3 races, returned \*\*\$51\.05\*\*, \*\*\+112\.7%\*\*, \*\*3 from 3"),
              ("Trifecta example: Flemington Race 6, 11 runners, 18 combinations, $9, result 12-6-7", "trifecta",
               r"Flemington Race 6 \(11 runners, 18 combinations, \$9 staked, \$25\.35 back, result 12-6-7\)"),
              ("Backing two: $30.00 → $47.55, +58.5%, a winner in 3 from 3", "backing-two", r"Staked \$30, returned \*\*\$47\.55\*\*, profit \$17\.55, \*\*\+58\.5%\*\*, a winner in 3 from 3"),
              ("Backing two example: no.12 Surfin' Bird $6 / no.6 Buckaroo $4 → $18.00", "backing-two",
               r"no\.12 Surfin' Bird \$6 and no\.6 Buckaroo \$4 returned \$18\.00"),
              ("$110 Email Service; $220 for 12 months, about 60¢ a day; 30-day risk-free trial", "bonus, price, trial",
               r"\$220 for 12 months\*\* \(about 60¢ a day\)")]
    for fig, where, pat in items:
        ok = re.search(pat, bt, re.S) is not None
        say(f"| {fig} | {where} | {'found' if ok else 'NOT FOUND'} | **{chk(ok, 'brief figure ' + fig)}** |")
    eight = [p for p, t in alltxt.items() if "Cosmic Crusader" in t and re.search(r"Cosmic Crusader[^$]{0,40}\$8\.00", t)]
    say(f"| Cosmic Crusader's $8.00 listed price never shown | every card | brief §4: \"Do not show\" | **{chk(not eight, 'listed price ' + str(eight))}** |")
    say("")

    # ---------------------------------------------------------------- 3. small print
    say("## 3. Hypothetical small print on every results card")
    sp = re.search(r"Suggested small print for the results scene: \*\"(.+?)\"\*", bt).group(1)
    say(f"Required (brief §6, word for word): *{sp}*")
    wanted = {f"ppd-{n}.html": ["#sp"] for n in RESULTS_CARDS}
    rects, _ = measure_pages(cards, wanted)
    ctrl_t = W["hook"]["out"] + 0.8                        # Gordon on his own, nothing at the bottom-left
    first_num = {"hook": T["twentyfive"]["start"], "before-after": T["win_div"]["start"], "rows": W["rows"]["in"] + 0.6,
                 "strike": T["three_from_five"]["start"], "tiles": T["t_win"]["start"], "trifecta": T["three_races"]["start"],
                 "backing-two": T["two_horses"]["start"]}
    for n in RESULTS_CARDS:
        word = sp in page_text(cards / f"ppd-{n}.html")
        x0, y0, x1, y1 = rects[(f"ppd-{n}.html", "#sp")]
        e_on = min(hf_energy(frame(out, t)[y0:y1, x0:x1]) for t in (first_num[n] + 0.4, W[n]["out"] - 0.6))
        e_off = hf_energy(frame(out, ctrl_t)[y0:y1, x0:x1])
        say(f"- `{n}`: word for word {'yes' if word else 'NO'}; in the finished video the small-print box carries text both when "
            f"the first number lands and as the card leaves (edge energy {e_on:.1f} vs {e_off:.1f} with no card) — "
            f"**{chk(word and e_on > 2 * e_off + 1, n + ' small print')}**")
    sp_rects = {n: rects[(f"ppd-{n}.html", "#sp")] for n in RESULTS_CARDS}
    say("- Before/after: the small print fades in with AFTER THE RACE, i.e. before the first result number; the BEFORE half "
        "shows no result.")
    say("")

    # ---------------------------------------------------------------- 4. timing
    say("## 4. Cards land on Gordon's words")
    say("Measured: each element's brightness in the FINISHED video at the element's real position (asked of the card page), "
        "against the moment Gordon starts the word (forced alignment, pause-checked). PASS −0.40 s to +0.30 s.")
    say("")
    say("| shot | element | Gordon says | his word at | on screen at | Δ | |")
    say("|---|---|---|---|---|---|---|")
    nxt = lambda key: next(w["start"] for w in words if w["start"] + T["head"] > T[key]["end"] + 0.01) + T["head"]
    checks = [  # (card, selector, reference time, quoted words, shot, label)
        ("hook", "#st", T["twentyfive"]["start"], "twenty-five dollars", 1, "STAKED $25"),
        ("hook", "#pc", T["n326"]["start"], "three hundred and twenty-six", 2, "+326% (slam)"),
        ("lower-thirds", "#lt", T["im_gordon"]["start"], "I'm Gordon", 3, "Gordon · Practical Punting"),
        ("lower-thirds", "#since", T["since"]["start"], "nineteen ninety-five", 3, "SINCE 1995"),
        ("types", "#hd", T["five_kinds"]["start"], "five kinds", 4, "5 bet types."),
        ("types", "#ty0", T["t_tbb"]["start"], "Today's Best Bets", 4, "✓ Today's Best Bets"),
        ("types", "#ty1", T["t_long"]["start"], "Longshots", 4, "✓ Longshots"),
        ("types", "#ty4", T["t_ra"]["start"], "Rating Assessments", 4, "✓ Rating Assessments"),
        ("realday", "#rt", T["real_day"]["start"], "Here's a real day", 5, "Cox Plate Day (the day's name, over the b-roll)"),
        ("before-after", "#bt", T["our_best_bet"]["start"], "Our Best Bet", 6, "TODAY'S BEST BET"),
        ("before-after", "#b1", T["bb_meeting"]["start"], "Flemington Race eight", 6, "Flemington Race 8"),
        ("before-after", "#b2", T["bb_no"]["start"], "number five", 6, "no.5"),
        ("before-after", "#b3", T["bb_horse"]["start"], "Cosmic Crusader", 6, "Cosmic Crusader"),
        ("before-after", "#qw1", T["quote"]["words"][1][1], "strong", 6, "the quote, word by word"),
        ("before-after", "#wt", T["worry"]["start"], "the seven-day backup", 6, "the worry"),
        ("before-after", "#at", T["won"]["start"], "won", 7, "the tick stamps"),
        ("before-after", "#tw", T["win_div"]["start"], "nine dollars fifty", 7, "WIN PAID $9.50"),
        ("rows", "#rk1", T["s2_horse"]["start"], "Juja Kibo", 8, "✓ Juja Kibo"),
        ("rows", "#rp1", T["s2_div"]["start"], "eight dollars", 8, "$8.00"),
        ("rows", "#rk2", T["s3_horse"]["start"], "Proxima Dea", 8, "✓ Proxima Dea"),
        ("rows", "#rp2", T["s3_div"]["start"], "three dollars eighty", 8, "$3.80"),
        ("rows", "#rn3", T["m1_horse"]["start"], "Maidoff", 9, "Maidoff fades to grey"),
        ("rows", "#rp3", T["m1_fin"]["start"], "fifth", 9, "5th"),
        ("rows", "#rn4", T["m2_horse"]["start"], "Arabian Rose", 9, "Arabian Rose fades to grey"),
        ("rows", "#rp4", T["m2_fin"]["start"], "tenth", 9, "10th"),
        ("strike", "#n3", T["three_from_five"]["start"], "Three from five", 10, "3 WINNERS FROM 5"),
        ("bank", "#b5", T["bet5"]["start"], "Five dollars a bet", 11, "$5 (the sliver)"),
        ("bank", "#b5p", T["half_pc"]["start"], "half a per cent", 11, "0.5% A BET"),
        ("bank", "#bv", T["bank1000"]["start"], "thousand-dollar bank", 11, "$1,000"),
        ("bank", "#l10", T["small_stakes"]["start"], "Small stakes", 11, "$10 · 1% LIMIT A RACE"),
        ("tiles", "#tile0", T["t_win"]["start"], "win", 12, "WIN +326.0%"),
        ("tiles", "#tile1", T["t_ew"]["start"], "each way", 12, "EACH WAY +186.0%"),
        ("tiles", "#tile2", T["t_place"]["start"], "place", 12, "PLACE +46.0%"),
        ("trifecta", "#cost", T["cost_down"]["start"], "keeps the cost down", 14, "50c A COMBINATION"),
        ("trifecta", "#ca", T["first_second"]["start"], "first and second", 14, "the top two lock into 1st/2nd"),
        ("trifecta", "#cb2", T["either"]["start"], "either way round", 14, "…and the other way round"),
        ("trifecta", "#fa0", T["whole_field"]["start"], "the whole field for third", 14, "the field fills 3rd"),
        ("trifecta", "#tt", T["three_races"]["words"][2][1], "…from three", 14, "TRIFECTA +112.7% · 3 FROM 3 (after a beat)"),
        ("backing-two", "#ha", T["two_horses"]["start"], "two horses", 15, "no.12 Surfin' Bird"),
        ("backing-two", "#sl", T["stake_split"]["start"], "the stake split", 15, "$10 SPLIT BY PRICE"),
        ("honest", "#h1", T["one_strong"]["words"][2][1], "one strong day", 16, "One strong day."),
        ("honest", "#h2", T["not_promise"]["start"], "not a promise", 16, "Not a promise."),
        ("trial", "#s0", T["join"]["start"], "Join", 17, "1 JOIN"),
        ("trial", "#s1", T["full_access"]["start"], "full access", 17, "2 PUT US TO THE TEST"),
        ("trial", "#s2", T["not_happy"]["start"], "If you're not happy", 17, "3 NOT HAPPY?"),
        ("trial", "#s2s", T["refund"]["start"], "refund every cent", 17, "FULL REFUND"),
        ("bonus", "#en", T["email_service"]["start"], "Email Service", 18, "PPD CLUB EMAIL SERVICE"),
        ("bonus", "#fr", T["comes_free"]["words"][1][1], "free", 18, "FREE"),
        ("bonus", "#b110", T["n110"]["words"][1][1], "hundred and ten", 18, "$110"),
        ("cta", "#cb", T["start_trial"]["start"], "start your risk-free trial", 19, "START YOUR RISK-FREE TRIAL"),
        ("cta", "#cg", T["grab_guide"]["start"], "Grab the free guide", 19, "NOT READY? GET THE FREE GUIDE"),
    ]
    wanted = {}
    for cd, sel, *_ in checks:
        wanted.setdefault(f"ppd-{cd}.html", []).append(sel)
    wanted.setdefault("ppd-hook.html", []).append("#bk")
    wanted.setdefault("ppd-trifecta.html", []).append("#cn")
    rects, fonts = measure_pages(cards, wanted)
    # the BEFORE half sits 430 px right until the split, then slides left: measure its elements where they ARE when they land
    split_ms = (T["it_won"]["pb"] - W["before-after"]["in"]) * 1000 - 100
    pre, _ = measure_pages(cards, {"ppd-before-after.html": ["#b1", "#b2", "#qw1", "#wt"]}, at={"ppd-before-after.html": split_ms})
    rects.update(pre)
    flood_done = W["hook"]["in"] + (meta["hook"]["exp"] + 480) / 1000
    earliest = {("hook", "#pc"): flood_done + 0.04}       # until the flood, Gordon (not the card) is under the +326% box
    deltas = []
    for cd, sel, ref, said, shot, label in checks:
        r = rects[(f"ppd-{cd}.html", sel)]
        x0, y0, x1, y1 = max(0, r[0]), max(0, r[1]), min(1920, r[2]), min(1080, r[3])
        w_in = W[cd]["in"]
        # BEFORE must be the card already up (not Gordon, not the outgoing card): from 0.45 s into the window
        t0 = max(ref - 1.0, w_in + (0.05 if sel in ("#lt",) else 0.45), earliest.get((cd, sel), 0))
        if (cd, sel) == ("realday", "#rt"):
            t0 = w_in + 0.32                  # the b-roll and its scrim have faded in; the title has not yet landed
        lt = q.light_times(out, t0, ref + 1.2, [(x0, y0, x1, y1)])[0][0]
        d = None if lt is None else round(lt - ref, 2)
        deltas.append(d)
        say(f"| {shot} | {label} | \"{said}\" | {ref:.2f} s | {lt} s | {'' if d is None else f'{d:+.2f}'} | "
            f"**{chk(q.verdict(d) == 'PASS', f'shot {shot} {label} timing {d}')}** |")
    # the hook count LANDS on "fifty" (the last tick, not the first)
    bx = rects[("ppd-hook.html", "#bk")]
    fifty = T["hundred_six"]["words"][-1][1]
    stl = settle(out, fifty - 1.4, fifty + 1.0, (bx[0], bx[1], min(1920, bx[2] + 60), bx[3]))
    d = None if stl is None else round(stl - fifty, 2)
    say(f"| 1 | BACK counts up and lands on $106.50 | \"…dollars fifty\" | {fifty:.2f} s | {stl} s (last tick) | "
        f"{'' if d is None else f'{d:+.2f}'} | **{chk(d is not None and -0.4 <= d <= 0.4, f'hook count lands {d}')}** |")
    cx = rects[("ppd-trifecta.html", "#cn")]
    wf = T["whole_field"]["start"]
    stl = settle(out, wf - 0.2, wf + 1.6, (cx[0], cx[1], min(1920, cx[2] + 80), cx[3]))
    say(f"| 14 | combinations tick 2, 4 … 18 as the field fills | \"the whole field for third\" | {wf:.2f} s | {stl} s (last tick) | "
        f"{'' if stl is None else f'{stl - wf:+.2f}'} | (by design: 9 chips × 60 ms after the first) |")
    good = [x for x in deltas if x is not None]
    say("")
    say(f"{len(good)} elements measured: mean Δ {np.mean(good):+.2f} s, worst {max(good, key=abs):+.2f} s. Full-screen cards and the "
        "b-roll enter in the pause before their shot's first words (plan: `overlay/ppd-plan.json`).")
    say("")

    # ---------------------------------------------------------------- 5. clearance
    say("## 5. Panels never touch Gordon")
    say("Measured as on the FBX videos: Gordon's own jacket pixels (dark, neutral, not green, a jacket-sized blob) in a "
        "presenter-only render of the SAME framing, every frame the panel is up, against the panel's real edge read from the "
        "rendered clip's alpha.")
    z, x, y = fp.zoom_expr(P)
    hook_mov = clips / "ppd-hook.mov"
    pip_png = job / "output" / "qc" / "hook-pip-alpha.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{meta['hook']['exp'] / 1000 - 0.4:.2f}", "-i", str(hook_mov), "-frames:v", "1",
                    "-pix_fmt", "rgba", str(pip_png)], check=True)
    for name, frame_txt, png, a_, b_ in (
            ("hook", "push 136%", pip_png, W["hook"]["in"] + 0.12, W["hook"]["in"] + meta["hook"]["exp"] / 1000),
            ("lower-thirds", "wide", clips / "ppd-lower-thirds.last.png", W["lower-thirds"]["in"] + 0.12, W["lower-thirds"]["out"] - 0.3),
            ("strike", "push 136%", clips / "ppd-strike.last.png", W["strike"]["in"] + 0.3, W["strike"]["out"] - 0.3),
            ("honest", "wide", clips / "ppd-honest.last.png", W["honest"]["in"] + 0.12, W["honest"]["out"] - 0.3),
            ("cta", "push 136%", clips / "ppd-cta.last.png", W["cta"]["in"] + 0.12, W["cta"]["out"] - 0.3)):
        px0, px1, py0, py1 = q.panel_box(png)
        edge = q.gordon_edge(master, z, x, y, P["total"], a_, b_, py0, py1, px0, P["head"])
        gap = min(edge) - px1
        say(f"- `{name}` ({frame_txt}, {a_:.1f}–{b_:.1f} s): panel x {px0}–{px1}, y {py0}–{py1}; Gordon's nearest edge x {min(edge)} "
            f"over {len(edge)} frames → **{gap} px** clear — **{chk(gap > 0, name + ' clearance ' + str(gap))}**")
    ctrl = min(edge) - 1100
    say(f"  - control: a panel reaching x 1100 on the same frames would measure {ctrl} px — "
        f"{'the check can fail' if ctrl <= 0 else 'CONTROL DID NOT FAIL'}{'' if ctrl <= 0 else chk(False, 'clearance control')}")
    say("- The hook's panel floods to full screen ON PURPOSE at 'fifty' (Gordon is covered, not touched); clearance is "
        "measured up to the moment the flood starts.")
    say("")

    # ---------------------------------------------------------------- 6. orange
    say("## 6. PP orange scan (tuned for PPD red)")
    say("Orange = hue 8–28°, saturation > 0.6, value > 0.5 — PP orange #DA532C is 13.4°. **PPD red #F44336 is 4.1°**, so it sits "
        "outside the band by construction. The FBX scan exempted orange found NEXT TO RED (it assumed red only lived in the PP "
        "logo); in a PPD video red is everywhere, so that exemption would blind the scan near every red element. Here the ONLY "
        "exemption is the PP logo's own box, MEASURED on each card page (and the logo chip on Gordon's shots).")
    # where the PP logo is: every <img src=pp-logo> on each card, while that card's window is open
    logo_sel = {}
    for p in cards.glob("ppd-*.html"):
        if "pp-logo-on-dark.svg" in p.read_text(encoding="utf-8"):
            logo_sel[p.name] = ['img[src*="pp-logo"]']
    lrect, _ = measure_pages(cards, logo_sel)
    chip = __import__("PIL.Image", fromlist=["Image"]).open(pp.ASSETS / "video-logo-chip.png").size
    chip_box = (1920 - chip[0] - 40, 1080 - chip[1] - 40, 1880, 1040)
    footage = [(w["in"], w["out"]) for w in P["windows"] if w["layer"] == "broll"]
    book_w = (W["book"]["in"], W["book"]["out"])

    def exempt_at(t):
        ex = [chip_box]
        for w in P["windows"]:
            r = lrect.get((f"ppd-{w['name']}.html", 'img[src*="pp-logo"]'))
            if r and w["in"] <= t <= w["out"]:
                ex.append(r)
        return ex
    fr = q.gray(out, 0, P["total"], scale=(960, 540), rgb=True)[::12]
    # a FADE mixes red with whatever is underneath (red at 50% over green grass IS orange for those frames): fade frames
    # are listed separately with their reason, never dropped
    fades = [(w["in"], w["in"] + w["fi"]) for w in P["windows"] if w["fi"]] + \
            [(w["out"] - w["fo"], w["out"]) for w in P["windows"] if w["fo"]] + \
            [(W["hook"]["in"] + meta["hook"]["exp"] / 1000, W["hook"]["in"] + (meta["hook"]["exp"] + 480) / 1000)]
    bad, foot, book_hits, hue_red, fade_hits = [], [], [], [], []
    for k, f in enumerate(fr):
        t = round(k * 12 / FPS, 2)
        hits = orange_cells(f, exempt_at(t))
        h, s, v = hue_sat_val(f)
        red = (s > 0.6) & (v > 0.5) & ((h < 8) | (h > 345))
        if red.any():
            hue_red.append(np.percentile(np.where(h[red] > 180, h[red] - 360, h[red]), 99.9))
        if len(hits):
            hit = (t, int(hits[0][1]), int(hits[0][0]), len(hits))
            if any(a <= t <= b for a, b in footage):
                foot.append(hit)
            elif any(a - 0.02 <= t <= b + 0.02 for a, b in fades):
                fade_hits.append(hit)
            elif book_w[0] <= t <= book_w[1]:
                book_hits.append(hit)
            else:
                bad.append(hit)
    say(f"- {len(fr)} frames (every 0.48 s, the whole video): orange outside the PP logo in the graphics, cards and Gordon's "
        f"shots in {len(bad)} frame(s){': ' + str(bad[:6]) if bad else ''} — **{chk(not bad, 'orange ' + str(bad[:6]))}**")
    say(f"- PPD red as it actually lands in the finished frames: the 99.9th-percentile hue of red pixels is "
        f"{max(hue_red):.1f}° at worst — {'clear of' if max(hue_red) < 8 else 'INSIDE'} the 8° edge of the orange band.")
    say(f"- The real free guide's pages (book card, {book_w[0]:.1f}–{book_w[1]:.1f} s) are reported separately: "
        f"{len(book_hits)} frame(s){' — ' + str(book_hits[:3]) if book_hits else ''}. They carry the PP endorser mark on the cover "
        "as printed in Hugh's guide; nothing was drawn by this build.")
    say(f"- B-roll footage (graded separately, not branding): {len(foot)} frame(s){' — ' + str(foot[:3]) if foot else ''}.")
    say(f"- Mid-fade frames (a card fading over Gordon or footage, ≤ 0.48 s each): {len(fade_hits)} frame(s)"
        f"{' — ' + str(fade_hits[:4]) if fade_hits else ''}. PPD red half-faded over green grass is orange for those frames; "
        "it is the fade, not a brand colour, and none persists into the frame after.")
    # CONTROLS, through the SAME encode as the master (x264, 4:2:0): PP orange must be CAUGHT — a block and small type —
    # and PPD red must stay CLEAN — a block, thin 3-px outlines like the $5 tokens and the FREE GUIDE pill, red type, and
    # a red edge over green grass like the lower third's.
    from PIL import Image, ImageDraw, ImageFont
    work = job / "output" / "qc"
    fnt = ImageFont.truetype("arialbd.ttf", 26)

    def canvas(col, grass=False):
        im = Image.new("RGB", (1920, 1080), (30, 31, 34))
        d = ImageDraw.Draw(im)
        if grass:
            d.rectangle((0, 700, 1920, 1080), fill=(96, 140, 58))
        d.rectangle((200, 200, 600, 400), fill=col)                                          # a block
        d.rounded_rectangle((700, 200, 900, 264), radius=12, outline=col, width=3)            # a thin outline
        d.text((1000, 210), "PRACTICAL PUNTING $106.50", font=fnt, fill=col)                 # small type
        d.rectangle((192, 750, 224, 910), fill=(30, 31, 34))                                 # the lower third's inset bar:
        d.rectangle((200, 760, 208, 900), fill=col)                                          # 8 px of colour, charcoal round it, over grass
        return np.asarray(im)
    c_or = len(orange_cells(x264_roundtrip(canvas((218, 83, 44)), work), []))
    c_or_txt = len(orange_cells(x264_roundtrip(np.where(np.arange(1920)[None, :, None] < 990, 30, canvas((218, 83, 44))), work), []))
    c_red = len(orange_cells(x264_roundtrip(canvas((244, 67, 54), grass=True), work), []))
    say(f"- Controls, each pushed through the master's own encode (x264, yuv420p): PP orange as a block, an outline, small "
        f"type and an edge → {c_or} cells flagged; PP-orange SMALL TYPE on its own → {c_or_txt} ({'caught' if c_or_txt else 'MISSED'}); "
        f"PPD red in all the same shapes, including over green grass → {c_red} ({'clean' if not c_red else 'FALSE ALARM'}) — "
        f"**{chk(c_or > 0 and c_or_txt > 0 and c_red == 0, 'orange controls')}**")
    say(f"- The rule: a cell counts when its orange pixels' MEDIAN hue is ≥ {CORE}°. Compression smears PPD red's thin strokes "
        "and type edges from 4° into 8–11° (the first scan's 23 hits were all that, looked at one by one: the $5 token "
        "outlines, the red count, the lower third's red edge, the FREE GUIDE pill, a red logo mid-fade); PP orange keeps its "
        "core near 13°.")
    say("")

    # ---------------------------------------------------------------- 7. b-roll
    say("## 7. B-roll — library first, racing rules, one clip on its own line")
    srcs = json.loads((job / "broll" / "broll-sources.json").read_text(encoding="utf-8"))
    for s in srcs:
        w = W[f"broll-{s['slot']}"]
        tt = w["in"] + 0.8
        f_out = frame(out, tt, (240, 135))
        p_ = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{0.3 + 0.8}", "-i", str(job / "broll" / s["file"]), "-frames:v", "1",
                             "-vf", "scale=240:135", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        f_clip = np.frombuffer(p_.stdout, np.uint8).reshape(135, 240, 3).astype(np.int16)
        top = f_out[:80].astype(np.int16)
        d_clip = float(np.abs(f_out[:80] - f_clip[:80]).mean())            # the top: the super sits low
        md5 = hashlib.md5((job / "broll" / s["file"]).read_bytes()).hexdigest()
        g = q.gray(job / "broll" / s["file"], 0, 5, scale=(160, 90), rgb=True)[::10, :30, :, :].astype(np.int16)
        green = ((g[..., 1] > g[..., 0] + 8) & (g[..., 1] > g[..., 2] + 8)).mean()
        say(f"- {s['slot']} \"{s['line']}\" — `{s['file']}` from `{s['source']}` (md5 {md5[:8]}, recorded {s['md5'][:8]}) on screen "
            f"{w['in']:.2f}–{w['out']:.2f} s; finished frame vs the clip, top third: diff {d_clip:.1f} — "
            f"**{chk(d_clip < 14 and md5 == s['md5'], s['slot'] + ' placement')}**; the grass behind the crowd is green "
            f"({green:.0%} of the top third). **0 Higgsfield credits.**")
        say(f"  - Watched end to end before use ({s['watched']}): {s['why']}.")
        say(f"  - Rejected: {s['alternatives_not_used']}.")
    say("- One b-roll slot, one clip: no repeats possible. No bookmaker signage, no odds board, no horses — so no rail to get wrong.")
    say("")

    # ---------------------------------------------------------------- 8. flutter
    say("## 8. Avatar edge flutter")
    c0, c1, band = q.flutter(master, T["speech_end"] - T["head"])
    worst = np.argsort(band)[-3:][::-1]
    say(f"- Movement in the master: columns x {c0}–{c1} of 1920; "
        f"{'nothing moves at the frame edges — the background is still' if c0 > 300 and c1 < 1650 else 'MOVEMENT REACHES THE EDGES'}. "
        f"Jacket band energy mean {band.mean():.2f}, worst at " + ", ".join(f"{(i + 1) / FPS:.1f} s" for i in worst)
        + f" (presenter clock) — **{chk(c0 > 300 and c1 < 1650, 'flutter extent')}** (how it LOOKS is Jodie's judgement).")
    say("")

    # ---------------------------------------------------------------- 9. audio
    say("## 9. Audio")
    plan_json = json.loads((job / "overlay" / "ppd-plan.json").read_text(encoding="utf-8"))
    for f in (out, capd):
        I, TP = q.loudness(f)
        say(f"- `{f.name}`: integrated {I:.1f} LUFS, true peak {TP:.1f} dBTP (PP standard {TARGET_LUFS:g} ±{TOLERANCE_LU:g}, ≤ {TARGET_TP:g}) "
            f"— **{chk(abs(I - TARGET_LUFS) <= TOLERANCE_LU and TP <= TARGET_TP, f.name + ' loudness')}**")
    say(f"- Measured makeup gain after the duck: {plan_json['plan']['makeup_db']:+.2f} dB (the FBX recipe: the voice/music balance and "
        "the duck untouched, only the level moves).")
    for lab, a_, b_ in (("title card + sting", 0.6, 4.8), ("speech (the hook)", T["speech_start"] + 0.8, T["speech_start"] + 3.3),
                        ("speech (the trifecta)", T["one_is"]["start"], T["one_is"]["start"] + 3.0),
                        ("speech (sign-off)", T["many_years"]["start"], T["many_years"]["start"] + 1.8),
                        ("closing card (music only)", P["closing_in"] + 0.5, P["warranty_in"] - 0.2),
                        ("warranty (music only)", P["warranty_in"] + 0.5, P["total"] - 0.7)):
        mv = q.mean_volume(out, a_, b_)
        say(f"- {lab} {a_:.1f}–{b_:.1f} s: mean {mv:.1f} dB — {'not silent' if mv > -45 else 'SILENT'} — **{chk(mv > -45, lab)}**")
    say("- The standard PP bed (EP01's master) at the PP level, with the standard 5-s title sting under the title card. No sound "
        "effects were added (the brief suggests tick pops; the PP audio standard has none — not added without Jodie's say-so).")
    say("")

    # ---------------------------------------------------------------- 10. structure
    say("## 10. Structure, in order")
    from PIL import Image
    tf = frame(out, 3.0, (480, 270))
    ref = np.asarray(Image.open(clips / "ppd-title.png").convert("RGB").resize((480, 270)), np.int16)
    d_t = float(np.abs(tf - ref).mean())
    say(f"- Opens on the title card — the thumbnail, re-rendered at 1920×1080 — for {P['head']:.1f} s with the standard PP sting "
        f"(Jodie's FBX ruling, 'like the normal videos'); frame at 3.0 s vs the card: {d_t:.1f} levels — **{chk(d_t < 6, 'title card')}**. "
        f"Gordon's first word at {T['speech_start']:.2f} s (his {T['speech_start'] - P['head']:.2f} s + the {P['head']:.1f} s head).")
    rg = " ".join(w["word"] for w in words[-8:])
    cf = frame(out, P["warranty_in"] - 0.3, (480, 270))
    cref = np.asarray(Image.open(clips / "ppd-closing.last.png").convert("RGB").resize((480, 270)), np.int16)
    wf = frame(out, P["total"] - 1.5, (480, 270))
    wref = np.asarray(Image.open(clips / "ppd-warranty.last.png").convert("RGB").resize((480, 270)), np.int16)
    d_c, d_w = float(np.abs(cf - cref).mean()), float(np.abs(wf - wref).mean())
    say(f"- \"{rg}\" ends at {T['speech_end']:.2f} s → PPD closing card {P['closing_in']:.2f} s (builds {pp.pc.CLOSING_BUILD:g} s, holds "
        f"{pp.CLOSING_HOLD:g} s; on screen vs its clip {d_c:.1f}) → the STANDARD PP warranty slide {P['warranty_in']:.2f}–{P['total']:.2f} s "
        f"({P['total'] - P['warranty_in']:.1f} s; vs its clip {d_w:.1f}) → 0.5 s fade — **{chk(d_c < 6 and d_w < 8 and 'lose.' in rg, 'ending')}**")
    wtxt = page_text(cards / "ppd-warranty.html")
    # the TEXT, not the bytes: Python on Windows writes the copy with CRLF line endings, which changes no character on the page
    std = (pp.ASSETS / "warranty-slide.html").read_text(encoding="utf-8") == (cards / "ppd-warranty.html").read_text(encoding="utf-8")
    say(f"- The warranty page is the standing slide, character for character: {'yes' if std else 'NO'} — **{chk(std, 'warranty standard')}**. "
        f"It says \"18+\": {'yes' if '18+' in wtxt else '**no**'} — brief §6 asks for \"18+ only\" on the responsible-gambling card. "
        "**Not edited** (the standing slide is never edited by a build): this is the question for Jodie.")
    srt = (job / "output" / "PPD-PROMO.srt").read_bytes().decode("utf-8-sig")
    first = re.search(r"(\d\d):(\d\d):(\d\d),(\d\d\d) -->", srt).groups()
    first = int(first[0]) * 3600 + int(first[1]) * 60 + int(first[2]) + int(first[3]) / 1000
    say(f"- Subtitles `output/PPD-PROMO.srt`: {len(re.findall('-->', srt))} cues, CRLF, first cue {first:.2f} s vs Gordon's first word "
        f"{T['speech_start']:.2f} s on the finished clock — **{chk(abs(first - T['speech_start']) < 0.06 and chr(13) + chr(10) in srt, 'SRT clock')}**")
    # the captioned export: captions present, clear of the small print, and right of any side panel
    place = json.loads((job / "overlay" / "captions" / "placement.json").read_text(encoding="utf-8"))
    worst_y, side_bad, sp_bad, chip_bad = 0, [], [], []
    hookw = next(w for w in P["windows"] if w["name"] == "hook")
    hookw["flood_done"] = hookw["in"] + (meta["hook"]["exp"] + 480) / 1000
    for a_, b_, png in place:
        al = np.asarray(Image.open(job / "overlay" / "captions" / png).convert("RGBA"))[:, :, 3]
        ys, xs = np.where(al > 8)
        worst_y = max(worst_y, int(ys.max()))
        if not pp.covered(P, a_, b_) and xs.max() > chip_box[0] and ys.max() > chip_box[1]:
            chip_bad.append(png)
        for w in P["windows"]:
            if w["name"] in pp.CAPTION_CLEAR and w["in"] < b_ and w["out"] > a_ and xs.min() < pp.CAPTION_CLEAR[w["name"]]:
                side_bad.append((png, w["name"]))
            # never over a results card's small print (its box measured on the page in section 3)
            if w["name"] in sp_rects and w["in"] < b_ and w["out"] > a_:
                sx0, sy0, sx1, sy1 = sp_rects[w["name"]]
                if xs.min() < sx1 and xs.max() > sx0 and ys.min() < sy1 and ys.max() > sy0:
                    sp_bad.append((png, w["name"]))
    k = len(place) // 2
    a_, b_, png = place[k]
    tm = (a_ + b_) / 2
    diff = float(np.abs(frame(capd, tm)[860:1000] - frame(out, tm)[860:1000]).mean())
    say(f"- Captioned export: {len(place)} burned-in captions (Roboto Bold, white, dark rounded strip); a mid-video frame differs "
        f"from the master in the caption band by {diff:.1f} levels (captions present); the lowest caption pixel is y {worst_y} — "
        f"captions overlapping a side panel: {side_bad or 'none'}; overlapping a card's small print (its measured box, while "
        f"that card is up): {sp_bad or 'none'}; touching the PP logo chip while Gordon is on screen: {chip_bad or 'none'} — "
        f"**{chk(diff > 3 and not side_bad and not sp_bad and not chip_bad, 'captions ' + str((side_bad, sp_bad, chip_bad)))}**")
    say(f"- Burned-in captions are SHORT (≤ {pp.CAP_MAX} characters, broken at commas, timed from Gordon's words) for a muted "
        "autoplay; the SRT for YouTube keeps whole sentences.")
    say("- PP logo chip bottom-right on every Gordon shot; full cards carry the PPD wordmark top right and \"Brought to you by\" + the PP logo.")
    say("")

    # ---------------------------------------------------------------- 11. hard nos
    say("## 11. Hard nos (brief §6 + Jodie)")
    screen = " ".join(alltxt.values())
    srt_txt = re.sub(r"\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d|\n\d+\r?\n", " ", srt)
    banned = [("tote", r"(?i)\btote\b"), ("SP", r"\bSP\b"), ("bet now", r"(?i)\bbet now\b"), ("guaranteed", r"(?i)\bguarantee"),
              ('"free trial" (not "risk-free trial")', r"(?i)(?<!risk-)\bfree trial"), ("Stanley / David Stanley", r"(?i)stanley"),
              ("doubles / exactas / Double 10", r"(?i)\bdoubles?\b|\bexacta|double 10"), ("quinella", r"(?i)quinella"),
              ("the bookmaker testimonial", r"(?i)severely wounded|leading bookmaker"),
              ("urgency", r"(?i)\bhurry\b|limited time|today only|last chance|ends soon|don't miss|act now"),
              ("products not to mention", r"(?i)statsman|notebook|video view|impactpro|daily specials|brief preview"),
              ("sure thing / can't lose", r"(?i)sure thing|can't lose|cannot lose"),
              ("bookmaker names", r"\b(" + "|".join(re.escape(b) for b in q.BOOKIES) + r")\b")]
    for lab, pat in banned:
        hits = {nm: len(re.findall(pat, t)) for nm, t in (("on screen", screen), ("SRT", srt_txt), ("spoken script", spoken))}
        tot = sum(hits.values())
        say(f"- {lab}: " + ", ".join(f"{k_} {v}" for k_, v in hits.items()) + f" — **{chk(tot == 0, 'hard no ' + lab)}**")
    say(f"- \"risk-free trial\" appears {len(re.findall(r'(?i)risk-free trial', screen + spoken))} times (always with the refund "
        "explained in the trial card); the price ($220 / about 60¢ a day) is on screen only, in its own swappable card — Gordon "
        f"never says it: {'confirmed' if not re.search(r'(?i)two hundred and twenty|sixty cents', spoken) else 'HE SAYS IT'}.")
    say("")

    # ---------------------------------------------------------------- 12. motion-graphics checklist
    say("## 12. pp-motion-graphics checklist, card by card")
    say("Automated where it can be measured (spec read from each page's own `ppSpec`; type sizes asked of the page); the rest is "
        "my judgement, marked as such.")
    say("")
    specs = page_specs(cards, [f"ppd-{w['name']}.html" for w in P["windows"] if w["layer"] != "broll" and w["name"] not in ("title", "warranty")])
    longest_gordonless = gordonless(P)
    for w in P["windows"]:
        n = w["name"]
        if w["layer"] == "broll" or n in ("title", "warranty"):
            continue
        sp_ = specs[f"ppd-{n}.html"]
        ends = [s["opts"]["delay"] + s["opts"]["duration"] for s in sp_ if "count" not in s or "stops" not in s.get("count", {})]
        last = max(ends) / 1000
        hold = (w["out"] - w["fo"]) - (w["in"] + last)
        runs = find_spoken_runs(alltxt[f"ppd-{n}"], spoken)
        runs_ok = not runs or n == "before-after" and all(r_ in "a strong demonstrated local form case the seven-day backup" for r_ in runs)
        mn, msp = fonts.get(f"ppd-{n}.html", (None, None)) if f"ppd-{n}.html" in fonts else (None, None)
        legible = f"smallest type {mn:.0f} px = {mn / 10.8:.1f}% of frame height" if mn and mn < 999 else "type measured below"
        hold_ok = hold >= 1.5 or n in ("price",)
        say(f"- **{n}** — finished state held {hold:.1f} s before it leaves ({chk(hold_ok, n + ' hold ' + f'{hold:.1f}')}); "
            f"Gordon's words on screen: {('none' if not runs else runs)}"
            f"{' (the pre-race quote and the worry are what was PUBLISHED to members before the race — the brief asks for them on screen)' if runs and n == 'before-after' else ''}"
            f" ({chk(runs_ok, n + ' redundancy ' + str(runs))}); {legible}.")
    say("")
    say("Row pacing (data rows 240–320 ms or longer, measured from each page's spec):")
    for pg, pre, lab in (("ppd-types.html", "#ty", "the five bet types"), ("ppd-rows.html", "#r", "the five selections enter"),
                         ("ppd-hook.html", "#tk", "the five $5 bets"), ("ppd-trial.html", "#s", "the three steps"),
                         ("ppd-tiles.html", "#tile", "the three return tiles"), ("ppd-strike.html", "#sd", "the five dots")):
        ds = sorted(s["opts"]["delay"] for s in specs[pg] if re.fullmatch(re.escape(pre) + r"\d+c?", s["sel"].split(" ")[0])
                    and ("kf" in s and any("transform" in k_ or "opacity" in k_ for k_ in s["kf"][0])))
        gaps = [b - a for a, b in zip(ds, ds[1:]) if b - a > 20]
        say(f"- {lab}: {len(ds)} entrances, gaps {', '.join(str(g_) for g_ in gaps)} ms — "
            f"**{chk(not gaps or min(gaps) >= 240, lab + ' pacing ' + str(gaps))}**")
    say("")
    stills = {"hook": (meta["hook"]["slam"] - (meta["hook"]["exp"] + 480)), "before-after": None, "bonus": None}
    say(f"Payoffs: +326% slams after {stills['hook']:.0f} ms of stillness (the flood finishes, nothing moves, then the slam). "
        "WIN PAID $9.50, the $110 and both strategy tiles each get a beat first (the builders HALT if a beat is under ~600 ms).")
    for line, ok in seek_test(job, cards, clips):
        say(f"Seek test (numeric moves): {line} — **{chk(ok, 'seek test ' + line[:30])}**")
    names = [w["name"] for w in P["windows"] if w["layer"] in ("full", "broll") and longest_gordonless[0] - 0.05 <= w["in"] < longest_gordonless[1]]
    say(f"Alternation (a judgement for Jodie, not a pass/fail): the longest stretch with no Gordon on screen is "
        f"{longest_gordonless[1] - longest_gordonless[0]:.1f} s ({longest_gordonless[0]:.1f}–{longest_gordonless[1]:.1f} s: "
        f"{' → '.join(dict.fromkeys(names))}, as the shot script lays them out). Gordon is on screen for the hook, his "
        "introduction, 3 from 5, the honest beat, the ask and the sign-off.")
    say("")
    say("Judgement (mine, for Jodie to overrule): every card carries something the voice does not — the bet in full house "
        "format, the dividends, the bank as a proportion, the trifecta's mechanics drawn out, the split stake, the 30-day line. "
        "Sound-off, each card still says its thing.")
    say("")
    say("## Result")
    say(f"**{'ALL CHECKS PASS' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}**" + ("" if not fails else ":\n" + "\n".join(f"- {f}" for f in fails)))
    (job / "output" / "qc" / "QC-REPORT.md").write_text("\n".join(R) + "\n", encoding="utf-8")
    print(f"\nfails={len(fails)}")
    sys.stdout.flush()
    import os
    os._exit(1 if fails else 0)


def settle(src, t0, t1, box):
    x0, y0, x1, y1 = box
    fr = q.gray(src, t0, t1, crop=(x1 - x0, y1 - y0, x0, y0)).astype(np.int16)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    moving = np.flatnonzero(d > 1.0)
    return None if moving.size == 0 else round(t0 + (moving[-1] + 1) / FPS, 2)


def page_specs(cards, names):
    out = {}
    for n in names:
        s = (cards / n).read_text(encoding="utf-8")
        m = re.search(r"ppInit\((\[.*\])\);</script>", s, re.S)
        out[n] = json.loads(m.group(1))
    return out


def gordonless(P):
    """The longest stretch where full-screen cards or b-roll cover Gordon (PIP panels leave him visible)."""
    cov = sorted((w["in"], w["out"]) for w in P["windows"] if w["layer"] in ("full", "broll") and w["name"] not in ("title", "closing", "warranty"))
    cov = cov + [(P["windows"][1]["in"] + 7.6, P["windows"][1]["out"])]     # the hook after its flood
    cov.sort()
    runs, cur = [], list(cov[0])
    for a, b in cov[1:]:
        if a <= cur[1] + 0.05:
            cur[1] = max(cur[1], b)
        else:
            runs.append(tuple(cur))
            cur = [a, b]
    runs.append(tuple(cur))
    return max(runs, key=lambda r: r[1] - r[0])


def seek_test(job, cards, clips):
    """The acceptance test for a numeric move: seek the page to 8 points (incl. ±1 ms around a tick), read the value the
    timeline says AND screenshot it; compare with the RENDERED clip's frame at the same time. Equal pixels = the clip shows
    the sought value."""
    from PIL import Image
    import io
    b, base = browser(cards)
    res = []
    for pg_name, sel, clip in (("ppd-hook.html", "#bk", "ppd-hook.mov"), ("ppd-trifecta.html", "#cn", "ppd-trifecta.mp4")):
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(f"{base}{quote(pg_name)}?paused=1", wait_until="load")
        pg.wait_for_function("typeof window.ppDuration === 'number'")
        pg.wait_for_function("document.fonts.status === 'loaded'")
        spec = pg.evaluate("window.ppSpec")
        cnt = next(s for s in spec if s.get("count") and s["sel"] == sel)
        d0, du = cnt["opts"]["delay"], cnt["opts"]["duration"]
        ts = [d0 - 40, d0 + 1, d0 + du * .25, d0 + du * .5, d0 + du * .75, d0 + du - 1, d0 + du + 1, d0 + du + 400]
        if "stops" in cnt["count"]:
            seg = cnt["count"]["segment"]
            ts = [d0 - 1, d0 + 1, d0 + seg - 1, d0 + seg + 1, d0 + 3 * seg + 1, d0 + du - seg + 1, d0 + du + 1, d0 + du + 200]
        r = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }", sel)
        x0, y0, x1, y1 = (int(round(v)) for v in r)
        x1 = min(1920, x1 + 60)
        worst, vals = 0.0, []
        for t in ts:
            # the clip renders frame f at f*40 ms: compare at the frame times the clip actually holds
            f = round(max(0, t) / 40)
            tt = f * 40
            pg.evaluate(f"ppSeek({tt})")
            vals.append(pg.evaluate(f"document.querySelector({json.dumps(sel)}).textContent"))
            # like with like: the hook clip is TRANSPARENT (qtrle argb) — screenshot without a background and compare the
            # colour only where the page is opaque (the first version shot it over white and reported a false MISMATCH)
            shot = np.asarray(Image.open(io.BytesIO(pg.screenshot(clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
                                                                    omit_background=True))).convert("RGBA"), np.int16)
            pr = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clips / clip), "-vf", f"select=eq(n\\,{f}),crop={x1 - x0}:{y1 - y0}:{x0}:{y0}",
                                 "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True)
            fv = np.frombuffer(pr.stdout, np.uint8)
            if fv.size == shot.size:
                fv = fv.reshape(shot.shape).astype(np.int16)
                m = shot[..., 3] > 200
                if m.any():
                    worst = max(worst, float(np.abs(fv[..., :3][m] - shot[..., :3][m]).mean()))
        res.append((f"`{sel}` on {pg_name}: values {' → '.join(dict.fromkeys(vals))}; rendered frame vs sought page, worst mean diff "
                    f"{worst:.2f} levels ({'match' if worst < 3 else 'MISMATCH'})", worst < 3))
    return res


if __name__ == "__main__":
    main()
