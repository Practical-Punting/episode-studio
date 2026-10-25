#!/usr/bin/env python3
"""ppd_promo.py — the PPD Club promo "Bet Small, Win Big": plan, cards, title, assembly, SRT, captioned export.

    python ppd_promo.py <job_dir> plan             print the cue sheet and every window (dry run, writes nothing big)
    python ppd_promo.py <job_dir> cards [names]    author + render the cards (overlay/cards -> overlay/clips)
    python ppd_promo.py <job_dir> title            the thumbnail page at 1920x1080 -> overlay/clips/ppd-title.png
    python ppd_promo.py <job_dir> assemble         output/PPD-PROMO-16x9.mp4 + output/PPD-PROMO.srt (+ overlay/ppd-plan.json)
    python ppd_promo.py <job_dir> captions         output/PPD-PROMO-16x9-captioned.mp4 (burned in, Roboto Bold, dark rounded strip)
    python ppd_promo.py <job_dir> viewing          yuv420p copies for Windows Media Player -> output/viewing/

Run the heavy steps under the shared render lock: python ../fbx/fbx_locked.py "<label>" ppd_promo.py <job> cards

REUSED, NOT REBUILT (scripts/fbx): fbx_fetch (render by exact name, byte-checked), fbx_align (forced alignment of
the script + the pause self-check), fbx_render (seek-and-screenshot clips, alpha, stills with the card flags),
fbx_assemble (the PP audio recipe with the title-head sting, the measured makeup gain, card_chain), fbx_promo
(zoom_expr: eased MCU/push moves). ONE CLOCK: every time here is on the finished clock (ppd_data.cue_sheet adds
the 7.0 s title head once).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FBX = HERE.parent / "fbx"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FBX))
sys.path.insert(0, str(HERE.parent / "promo"))       # the shared promo toolkit (card_lint, so far)
sys.path.insert(0, str(HERE.parent))
import ppd_data as pdd  # noqa: E402
import ppd_cards as pc  # noqa: E402
import fbx_assemble as fa  # noqa: E402
import fbx_promo as fp  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

ASSETS = HERE.parent.parent / "assets"
FADE = 0.3
CLOSING_HOLD = 3.0
WARRANTY_TAIL = fa.WARRANTY_TAIL          # the PP standard, 6.7 s
BROLL = {"S5": ("broll-race-day-crowd-at-the-rail.mp4",
                r"G:\My Drive\PP Videos\PP-EP37-Don-Scotts-Legacy\broll\broll-a-crowd-on-the-lawn-reacting-as-the-field-passes.mp4")}
# where a burned-in caption may START (x) while each over-Gordon / over-footage panel is up, so it never covers them
CAPTION_CLEAR = {"hook": 790, "lower-thirds": 600, "strike": 790, "honest": 600, "cta": 690, "realday": 860}
OUT = "PPD-PROMO-16x9.mp4"


def load(job):
    promo, day = pdd.load(job)
    return promo, day, pdd.cue_sheet(job, promo)


# ------------------------------------------------------------------ the edit plan
def plan(promo, T):
    pb = lambda k: T[k]["pb"]
    st = lambda k: T[k]["start"]
    en = lambda k: T[k]["end"]
    wd = lambda k, i: T[k]["words"][i][1]
    P = {"head": T["head"], "speech_end": T["speech_end"]}
    P["closing_in"] = round(T["speech_end"] + 0.25, 2)
    P["warranty_in"] = round(P["closing_in"] + pc.CLOSING_BUILD + CLOSING_HOLD, 2)
    P["total"] = round(P["warranty_in"] + WARRANTY_TAIL, 2)
    win = []

    def add(name, layer, t_in, t_out, fi=0.0, fo=0.0, src=None):
        win.append({"name": name, "layer": layer, "in": round(t_in, 3), "out": round(t_out, 3), "fi": fi, "fo": fo, "src": src})

    book_in = wd("its_all", 5) - 0.10                                   # on "guide,"
    b2_in = st("other") + 0.35                    # the trifecta tile holds >= 1.5 s before backing-two covers it
    add("title", "full", 0.0, T["head"], 0.0, FADE)                                      # title card + sting
    add("hook", "over", pb("hook_on") - 0.05, pb("show_you") + FADE, 0.0, FADE)          # shots 1-2 (one clip)
    add("lower-thirds", "over", pb("im_gordon"), pb("every_morning") + FADE)             # shot 3
    add("types", "full", pb("every_morning"), pb("real_day") + FADE, FADE, 0.0)          # shot 4
    add("broll-S5", "broll", pb("real_day"), pb("our_best_bet") + 0.15, FADE, FADE, BROLL["S5"][0])   # shot 5
    add("realday", "top", pb("real_day"), pb("our_best_bet") + 0.15, 0.0, FADE)
    add("before-after", "full", pb("our_best_bet") - 0.15, pb("s2_meeting") + FADE)      # shots 6-7 (under the b-roll)
    add("rows", "full", pb("s2_meeting"), pb("three_from_five"), FADE, FADE)              # shots 8-9
    add("strike", "over", pb("three_from_five") - FADE, pb("idea") + FADE)               # shot 10
    add("bank", "full", pb("idea"), pb("and_on") + FADE, FADE, 0.0)                      # shot 11
    add("tiles", "full", pb("and_on"), book_in + FADE, FADE, 0.0)                        # shot 12
    add("book", "full", book_in, st("one_is") + FADE, FADE, 0.0)                         # shot 13
    add("trifecta", "full", st("one_is"), b2_in + FADE, FADE, 0.0)                       # shot 14
    add("backing-two", "full", b2_in, pb("one_strong"), FADE, FADE)                      # shot 15 (+ mid-roll tag)
    add("honest", "over", pb("one_strong"), pb("ready") + FADE)                          # shot 16
    add("trial", "full", pb("ready"), T["when_join"]["pa"] + FADE, FADE, 0.0)            # shot 17
    add("bonus", "full", T["when_join"]["pa"], pb("tap"), FADE, FADE)                    # shot 18
    add("price", "top", wd("five_types", 0) - 0.15, pb("tap"), 0.0, FADE)                # shot 18: the swappable price card
    add("cta", "over", pb("start_trial") - 0.25, pb("many_years") + 0.5 + FADE, 0.0, FADE)   # shot 19 (holds into the sign-off)
    add("closing", "full", P["closing_in"], P["warranty_in"] + 0.6, FADE, 0.0)            # shot 22
    add("warranty", "full", P["warranty_in"], P["total"], 0.6, 0.0)                       # shot 23
    P["windows"] = win
    W = {w["name"]: w for w in win}
    # Gordon's framing — eased moves only. PUSH (136%, shifted right) under every left panel, and it FINISHES before
    # the panel appears (the FBX promo lesson); MCU (126%) for the sign-off; WIDE for the lower thirds and the honest beat.
    P["push"] = [(-1.0, 16.0), (W["strike"]["in"] - 0.6, W["strike"]["out"] + 0.6), (pb("tap") - 1.0, W["cta"]["out"] + 0.6)]
    P["mcu"] = [(15.6, pb("im_gordon")), (W["cta"]["out"] + 0.1, P["total"] + 1)]
    return P


# ------------------------------------------------------------------ staging + cards
def stage(job, promo):
    pack = job / promo["pack_dir"]
    cards = job / "overlay" / "cards"
    a = cards / "assets"
    (a / "fonts").mkdir(parents=True, exist_ok=True)
    for src, dst in (("raleway-latin-800-normal", "raleway-800"), ("raleway-latin-900-normal", "raleway-900"),
                     ("roboto-latin-400-normal", "roboto-400"), ("roboto-latin-400-italic", "roboto-400i"),
                     ("roboto-latin-700-normal", "roboto-700")):
        shutil.copyfile(pack / "brand" / "fonts" / f"{src}.woff2", a / "fonts" / f"{dst}.woff2")
    shutil.copyfile(pack / "logos" / "PPD-tick-wordmark-onDark_520x120@2x.png", a / "ppd-wordmark.png")
    shutil.copyfile(ASSETS / "pp-logo-on-dark.svg", a / "pp-logo-on-dark.svg")
    shutil.copyfile(ASSETS / "pp-anim.js", cards / "pp-anim.js")
    shutil.copyfile(ASSETS / "assets" / "logo.png", a / "logo.png")          # the standing warranty slide's own logo
    pages = []
    pdf = pack / "ebook" / "PPD_Bet-Small-Win-Big_Free-Guide_v3.pdf"
    for n in range(1, 8):                                                     # cover .. the Cox Plate Day spread (6-7)
        out = a / f"guide-p{n}"
        if not Path(str(out) + ".png").is_file():
            subprocess.run(["pdftoppm", "-r", "150", "-png", "-singlefile", "-f", str(n), "-l", str(n), str(pdf), str(out)], check=True)
        pages.append(f"assets/guide-p{n}.png")
    # the b-roll: LIBRARY first (0 Higgsfield credits). Copied in, with where it came from and why, beside it.
    bdir = job / "broll"
    bdir.mkdir(exist_ok=True)
    rec = []
    import hashlib
    for slot, (name, src) in BROLL.items():
        if not (bdir / name).is_file():
            shutil.copyfile(src, bdir / name)
        rec.append({"slot": slot, "line": "Here's a real day: Cox Plate Day.", "file": name, "source": src,
                    "md5": hashlib.md5((bdir / name).read_bytes()).hexdigest(),
                    "why": "a diverse race-day crowd at the rail reacting as the field passes — hats in a range of natural "
                           "colours, no horses in shot (so no running-rail fault is possible), no signage, one continuous shot",
                    "watched": "8 frames end to end + 4 at full size, 25 Oct 2026",
                    "alternatives_not_used": "EP47 big Saturday field from the stand (every hat the same pale cream; near rail "
                                             "crosses the runners' hooves late) · EP26 field sweeping to the line (~20 abreast, two "
                                             "rails converging down the middle of the track) · EP42 field fanned wide (a runner on the "
                                             "far side of the rail) · EP38 bunched at the turn (a rail section in front of the field) · "
                                             "EP31 full lawn, EP15 cup-day grandstand, EP24 glamour crowd (each cuts to a second shot "
                                             "mid-clip)",
                    "credits": 0})
    (bdir / "broll-sources.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return pages


def build_cards(job, only=()):
    promo, day, T = load(job)
    P = plan(promo, T)
    W = {w["name"]: w for w in P["windows"]}
    cards = job / "overlay" / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    pages = stage(job, promo)
    meta = {}
    hook, meta["hook"] = pc.c_hook(promo, day, T, W["hook"]["in"])
    book, meta["book"] = pc.c_book(promo, day, T, W["book"]["in"], pages)
    tri, meta["trifecta"] = pc.c_trifecta(promo, day, T, W["trifecta"]["in"])
    b2, meta["backing-two"] = pc.c_backing_two(promo, day, T, W["backing-two"]["in"])
    builds = [
        ("hook", hook, True),
        ("lower-thirds", pc.c_lower_thirds(promo, day, T, W["lower-thirds"]["in"]), True),
        ("types", pc.c_types(promo, day, T, W["types"]["in"]), False),
        ("realday", pc.c_realday(promo, day, T, W["realday"]["in"]), True),
        ("before-after", pc.c_before_after(promo, day, T, W["before-after"]["in"]), False),
        ("rows", pc.c_rows(promo, day, T, W["rows"]["in"]), False),
        ("strike", pc.c_strike(promo, day, T, W["strike"]["in"]), True),
        ("bank", pc.c_bank(promo, day, T, W["bank"]["in"]), False),
        ("tiles", pc.c_tiles(promo, day, T, W["tiles"]["in"]), False),
        ("book", book, False),
        ("trifecta", tri, False),
        ("backing-two", b2, False),
        ("honest", pc.c_honest(promo, day, T, W["honest"]["in"]), True),
        ("trial", pc.c_trial(promo, day, T, W["trial"]["in"]), False),
        ("bonus", pc.c_bonus(promo, day, T, W["bonus"]["in"]), False),
        ("price", pc.c_price(promo, day, T, W["price"]["in"]), True),
        ("cta", pc.c_cta(promo, day, T, W["cta"]["in"]), True),
        ("closing", pc.c_closing(promo, day, T), False),
        # the STANDING warranty page, byte-for-byte — unchanged, as every PP episode carries it
        ("warranty", (ASSETS / "warranty-slide.html").read_text(encoding="utf-8"), False),
    ]
    jobs = []
    for name, html, alpha in builds:
        p = cards / f"ppd-{name}.html"
        p.write_text(html, encoding="utf-8")
        if not only or name in only:
            jobs.append((p, 1920, 1080, alpha))
    (job / "overlay" / "ppd-cues.json").write_text(json.dumps(T, indent=1), encoding="utf-8")
    (job / "overlay" / "ppd-card-meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    # the card lint BEFORE any render: the traps that cost re-renders on this promo stop the build here, in plain words
    import card_lint
    faults = card_lint.lint(cards, [p.name for p, *_ in jobs if "warranty" not in p.name])
    print(card_lint.report(faults), flush=True)
    if faults:
        raise pdd.Halt("card lint failed — nothing rendered")
    print(f"wrote {len(builds)} card pages; rendering {len(jobs)}", flush=True)
    import fbx_render
    fbx_render.render_all(job / "overlay" / "clips", jobs)


# ------------------------------------------------------------------ assembly
def assemble(job):
    promo, day, T = load(job)
    P = plan(promo, T)
    tot = P["total"]
    master = job / "renders" / "presenter-master.mp4"
    music = job.parents[1] / "PP-EP01-The-Trifecta-Mistake" / "music" / "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"
    chip = ASSETS / "video-logo-chip.png"
    clips = job / "overlay" / "clips"
    rank = {"over": 0, "full": 1, "broll": 2, "top": 3}
    # bottom to top: panels over Gordon, full-screen cards, b-roll, supers over footage/cards. Every hand-off is an
    # incoming layer fading in OVER an outgoing one held solid (the PP rule: never two cross-fading).
    order = sorted(P["windows"], key=lambda w: rank[w["layer"]])
    inputs = [master, chip]
    for w in order:
        if w["layer"] == "broll":
            src = job / "broll" / w["src"]
        else:
            c = list(clips.glob(f"ppd-{w['name']}.mp4")) + list(clips.glob(f"ppd-{w['name']}.mov")) + list(clips.glob(f"ppd-{w['name']}.png"))
            if len(c) != 1:
                raise pdd.Halt(f"expected one clip ppd-{w['name']}.mp4/.mov/.png in overlay/clips, found {len(c)}")
            src = c[0]
        if not src.is_file():
            raise pdd.Halt(f"missing input {src}")
        inputs.append(src)
    inputs.append(music)
    music_in = len(inputs) - 1
    z, x, y = fp.zoom_expr(P)
    head = P["head"]
    g = (f"[0:v]tpad=start_duration={head}:start_mode=clone,tpad=stop_mode=clone:stop_duration=60,trim=duration={tot},"
         f"setpts=PTS-STARTPTS,fps=25,zoompan=z={z}:x={x}:y={y}:d=1:s=1920x1080:fps=25[zoomed];\n"
         f"[1:v]format=rgba[lg];\n[zoomed][lg]overlay=x=W-w-40:y=H-h-40[v0];\n")
    cur = "v0"
    for k, w in enumerate(order):
        lbl = f"c{k}"
        if w["layer"] == "broll":
            d = round(w["out"] - w["in"], 3)
            g += (f"[{k + 2}:v]trim=start=0.3:duration={d},setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,format=yuva420p,"
                  f"fade=t=in:st=0:d={w['fi']}:alpha=1,fade=t=out:st={round(d - w['fo'], 3)}:d={w['fo']}:alpha=1,"
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
    gfile = job / "overlay" / "graph-ppd.txt"
    gfile.write_text(g, encoding="utf-8")
    out = job / "output" / OUT
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
    for p in inputs:
        if str(p).endswith(".png"):
            cmd += ["-loop", "1", "-framerate", "25", "-t", str(tot), "-i", str(p)]
        else:
            cmd += ["-i", str(p)]
    cmd += ["-filter_complex_script", str(gfile), "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            "-map_metadata", "-1", "-map_chapters", "-1", "-dn", "-t", str(tot), str(out)]
    print(f"assembling {out.name}: {tot:.2f}s, {len(order)} windows", flush=True)
    if subprocess.run(cmd).returncode:
        raise pdd.Halt("ffmpeg failed")
    (job / "overlay" / "ppd-plan.json").write_text(json.dumps({"cues": T, "plan": P}, indent=1), encoding="utf-8")
    write_srt(job, head)
    print("wrote", out)


def write_srt(job, head):
    """output/PPD-PROMO.srt = renders/aligned.srt (fbx_align, pause-checked) moved onto the FINISHED clock."""
    src = (job / "renders" / "aligned.srt").read_text(encoding="utf-8-sig")

    def shift(m):
        h, mi, s, ms = (int(v) for v in m.groups())
        ms_ = int(round((h * 3600 + mi * 60 + s + ms / 1000 + head) * 1000))
        return f"{ms_ // 3600000:02d}:{ms_ // 60000 % 60:02d}:{ms_ // 1000 % 60:02d},{ms_ % 1000:03d}"
    dst = re.sub(r"(\d\d):(\d\d):(\d\d),(\d\d\d)", shift, src)
    (job / "output" / "PPD-PROMO.srt").write_text(dst, encoding="utf-8-sig", newline="\r\n")
    print(f"wrote output/PPD-PROMO.srt (+{head:.1f} s onto the finished clock)")


def srt_cues(path):
    t = Path(path).read_text(encoding="utf-8-sig")
    cues = []
    for blk in re.split(r"\r?\n\r?\n", t.strip()):
        ln = blk.splitlines()
        m = re.match(r"(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)", ln[1])
        v = [int(x) for x in m.groups()]
        a = v[0] * 3600 + v[1] * 60 + v[2] + v[3] / 1000
        b = v[4] * 3600 + v[5] * 60 + v[6] + v[7] / 1000
        cues.append((a, b, ln[2:]))
    return cues


CAP_MAX = 60             # characters per burned-in caption (the SRT for YouTube keeps whole sentences)


def caption_chunks(job, T):
    """Short captions for the muted autoplay (sales page, EDM): each SENTENCE of the script cut at commas / word
    boundaries into pieces of <= CAP_MAX characters, each timed from Gordon's measured words (fbx_align), on the
    finished clock."""
    words = json.loads((job / "renders" / "words-forced.json").read_text(encoding="utf-8"))
    head = T["head"]
    text = next((job / "docs").glob("*heygen-spoken.txt")).read_text(encoding="utf-8")
    sents = [s for p in re.split(r"\n\s*\n", text) if p.strip() for s in re.split(r"(?<=[.!?])\s+", " ".join(p.split())) if s.strip()]
    chunks, i = [], 0
    for s in sents:
        ws = words[i:i + len(s.split())]
        i += len(s.split())
        cur = []
        for k, w in enumerate(ws):
            cur.append(w)
            line = " ".join(x["word"] for x in cur)
            rest = ws[k + 1:]
            nxt_len = len(line) + 1 + (len(rest[0]["word"]) if rest else 0)
            # break after a comma once the piece is a decent length, or before it would overflow
            if rest and ((w["word"].endswith((",", ":")) and len(line) >= 24) or nxt_len > CAP_MAX):
                chunks.append([cur[0]["start"] + head, cur[-1]["end"] + head, line])
                cur = []
        if cur:
            chunks.append([cur[0]["start"] + head, cur[-1]["end"] + head, " ".join(x["word"] for x in cur)])
    if i != len(words):
        raise pdd.Halt("captions: the sentence split did not consume every word")
    for k, c in enumerate(chunks):          # hold to the next caption (or 0.5 s past the words), never overlapping
        nxt = chunks[k + 1][0] if k + 1 < len(chunks) else c[1] + 1.0
        c[1] = min(max(c[1] + 0.35, c[0] + 1.0), nxt - 0.04)
    return chunks


def covered(P, a, b):
    """True when a full-screen card or b-roll covers Gordon for the whole of a..b (the PP logo chip is hidden too)."""
    for w in P["windows"]:
        if w["layer"] in ("full", "broll") and w["name"] != "title" and w["in"] - 0.05 <= a and b <= w["out"] + 0.05:
            return True
    hook = next(w for w in P["windows"] if w["name"] == "hook")
    return hook.get("flood_done", 1e9) <= a and b <= hook["out"]


def captions(job):
    """Burn short captions in: one transparent PNG each (Roboto Bold, white, dark rounded strip), overlaid on its own
    time. Over a full card: at the bottom, clear of the small print. On Gordon's shots: ABOVE the PP logo chip. Beside a
    panel (or a super over footage): starting right of it."""
    promo, day, T = load(job)
    P = plan(promo, T)
    meta = json.loads((job / "overlay" / "ppd-card-meta.json").read_text(encoding="utf-8"))
    hook = next(w for w in P["windows"] if w["name"] == "hook")
    hook["flood_done"] = hook["in"] + (meta["hook"]["exp"] + 480) / 1000
    cues = caption_chunks(job, T)
    capdir = job / "overlay" / "captions"            # stills are overwritten by number; placement.json says which are used
    capdir.mkdir(parents=True, exist_ok=True)
    fonts = capdir / "fonts"
    fonts.mkdir(exist_ok=True)
    shutil.copyfile(job / "overlay" / "cards" / "assets" / "fonts" / "roboto-700.woff2", fonts / "roboto-700.woff2")
    side = [w for w in P["windows"] if w["name"] in CAPTION_CLEAR]
    pages, place = [], []
    for k, (a, b, line) in enumerate(cues):
        x0 = max([CAPTION_CLEAR[w["name"]] for w in side if w["in"] < b and w["out"] > a] + [0])
        left, width = (x0, 1880 - x0) if x0 else (120, 1680)
        # above the PP logo chip (428x140, so its top is y 900) whenever Gordon — and his chip — is on screen
        bottom = 92 if covered(P, a, b) else 1080 - (1080 - 40 - 140) + 16
        html = ('<!doctype html><html><head><meta charset="utf-8"><style>'
                "@font-face{font-family:Roboto;src:url(fonts/roboto-700.woff2) format('woff2');font-weight:700}"
                "html,body{margin:0;padding:0;background:transparent;overflow:hidden}"
                f"body{{width:1920px;height:1080px;position:relative}}"
                f".z{{position:absolute;left:{left}px;width:{width}px;bottom:{bottom}px;display:flex;justify-content:center}}"
                ".s{font-family:Roboto;font-weight:700;font-size:40px;line-height:1.28;color:#fff;text-align:center;text-wrap:balance;"
                "background:rgba(20,21,24,.82);border-radius:16px;padding:10px 26px 12px;max-width:100%}"
                f'</style></head><body><div class="z"><div class="s">{_esc(line)}</div></div></body></html>')
        p = capdir / f"cap-{k:03d}.html"
        p.write_text(html, encoding="utf-8")
        pages.append(p)
        place.append((a, b, capdir / f"cap-{k:03d}.png"))
    _alpha_stills(capdir, pages)
    src = job / "output" / OUT
    out = job / "output" / "PPD-PROMO-16x9-captioned.mp4"
    g, cur = "", "0:v"
    for k, (a, b, png) in enumerate(place):
        g += f"[{cur}][{k + 1}:v]overlay=x=0:y=0:enable='between(t,{a:.3f},{b:.3f})'[q{k}];\n"
        cur = f"q{k}"
    g += f"[{cur}]format=yuv420p[vout]"
    gfile = capdir / "graph-captions.txt"
    gfile.write_text(g, encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats", "-i", str(src)]
    for _, _, png in place:
        cmd += ["-i", str(png)]
    cmd += ["-filter_complex_script", str(gfile), "-map", "[vout]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", "-map_metadata", "-1", str(out)]
    print(f"burning {len(place)} captions -> {out.name}", flush=True)
    if subprocess.run(cmd).returncode:
        raise pdd.Halt("ffmpeg failed burning captions")
    (capdir / "placement.json").write_text(json.dumps([(a, b, str(p.name)) for a, b, p in place], indent=1), encoding="utf-8")
    print("wrote", out)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _alpha_stills(root, pages):
    """Transparent full-frame PNGs, one Chromium session, the card renderer's flags (no LCD fringes)."""
    import functools
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.parse import quote
    import fbx_render as fr
    from playwright.sync_api import sync_playwright
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(fr._Quiet, directory=str(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    p = sync_playwright().start()
    br = p.chromium.launch(headless=True, args=["--force-color-profile=srgb", "--disable-lcd-text", "--hide-scrollbars",
                                                "--force-device-scale-factor=1"])
    pg = br.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    for html in pages:
        pg.goto(f"http://127.0.0.1:{httpd.server_address[1]}/{quote(html.name)}", wait_until="load")
        pg.wait_for_function("document.fonts.status === 'loaded'", timeout=60_000)
        pg.screenshot(path=str(html.with_suffix(".png")), omit_background=True)
    print(f"  {len(pages)} caption stills rendered", flush=True)


def viewing(job):
    """Every clip handed to Jodie is yuv420p (Windows Media Player cannot open 4:4:4)."""
    vd = job / "output" / "viewing"
    vd.mkdir(exist_ok=True)
    for f in (job / "output" / OUT, job / "output" / "PPD-PROMO-16x9-captioned.mp4"):
        if f.is_file():
            pix = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of",
                                  "csv=p=0", str(f)], capture_output=True, text=True).stdout.strip()
            print(f"{f.name}: {pix}")
            if pix != "yuv420p":
                raise pdd.Halt(f"{f.name} is {pix}, not yuv420p")


def main():
    job = Path(sys.argv[1]).resolve()
    mode = sys.argv[2]
    try:
        if mode == "stage":
            promo, day, T = load(job)
            print("staged", len(stage(job, promo)), "guide pages + fonts, logos, b-roll")
        elif mode == "plan":
            promo, day, T = load(job)
            P = plan(promo, T)
            for w in sorted(P["windows"], key=lambda w: w["in"]):
                print(f"  {w['layer']:6s} {w['name']:14s} {w['in']:8.2f} -> {w['out']:8.2f}  ({w['out'] - w['in']:5.2f}s)")
            print("push", P["push"], "\nmcu ", P["mcu"], "\ntotal", P["total"])
        elif mode == "cards":
            build_cards(job, tuple(sys.argv[3:]))
            sys.stdout.flush()
            import os
            os._exit(0)
        elif mode == "title":
            import fbx_render
            out = job / "overlay" / "clips" / "ppd-title.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            # the thumbnail's design + the brief §6 small print (Jodie, 25 Oct: small print on the title card only)
            fbx_render.still(job / "overlay" / "thumbnail" / "title.html", out, 1280, 720, scale=1.5)
            sys.stdout.flush()
            import os
            os._exit(0)
        elif mode == "assemble":
            assemble(job)
        elif mode == "captions":
            captions(job)
            sys.stdout.flush()
            import os
            os._exit(0)
        elif mode == "viewing":
            viewing(job)
    except pdd.Halt as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
