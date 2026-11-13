#!/usr/bin/env python3
"""twoway_film_qc.py — the WHOLE QC of a finished two-way film, in one command, on the file itself.

    python engine/twoway_film_qc.py <ep_number> <finished.mp4> [--masters] [--no-repeats]

Exit 0 = every machine check passed (the human items are listed, never ticked); 1 = a fault; 2 = could not run.
Writes `output/qc/<film stem>/` (logs + qc-report.json) and `output/qc-frames/<film stem>/` (frames + sheets).

🔴 WHY ONE COMMAND (EP56 cut 3, 13 Nov 2026). The QC used to be a scratch script per cut, and the cut-3 one
got THREE INPUTS wrong while every tool it called was right: it measured sync against the film WITHOUT its
18s end frame (a false "refused"), ran verify_cut BEFORE writing the cut's SRT (a false "0/16 words"), and
fed the repeated-words check both scripts end to end instead of in film order (eight false "repeats"). Cut
2's scratch QC read a STALE assembly-plan.json. Each is now fixed here, in code, once:
  · the plan is REBUILT from the episode (`build_plan`) — never read from a file a render may not have written;
  · sync is measured against the FILE's own length;
  · the SRT is written FIRST;
  · the film's script is merged.srt's text, in the order the film plays it.

THE CHECKS (each on the finished file):
  sync · twoway_qc · verify_cut · loudness · SRT (CRLF) · midroll WAV (the previous one kept) ·
  LOGO every 2s from the first frame to the end card (none after) · every card clear of the corner chip ·
  repeated words on the film (and with --masters, on each presenter master) · the open: host plate on/off
  frames · a full frame every minute · one frame per segment + furniture · contact sheets.
HUMAN ITEMS (listed, never ticked): watch the cut, the midroll listen, and anything twoway_qc calls LISTEN.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

PP = pathlib.Path("G:/My Drive/PP Videos")


def _dur(p: pathlib.Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                 "default=nw=1:nk=1", str(p)], capture_output=True, text=True).stdout)


def film_order_script(d: pathlib.Path) -> str:
    """Both scripts' own words, in the order the film plays them: merged.srt's text, speaker tags off."""
    return "\n".join(re.sub(r"^\[[A-Z]{2}\]\s*", "", l)
                     for l in (d / "renders/merged.srt").read_text(encoding="utf-8").splitlines()
                     if l.strip() and not l.strip().isdigit() and "-->" not in l)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("film")
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--masters", action="store_true", help="also run the repeated-words check on each master")
    ap.add_argument("--no-repeats", action="store_true", help="skip the (slow) repeated-words transcription")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    import ep_paths
    import render_lock
    import twoway_assemble as ta
    import twoway_cards as tcards
    import twoway_render as tr

    pp = pathlib.Path(a.pp)
    d = ep_paths.episode_dir(a.ep_number, pp)
    film = pathlib.Path(a.film)
    if not film.is_file():
        print(f"cannot run: {film} is not there", file=sys.stderr)
        return 2
    Q = d / "output/qc" / film.stem
    F = d / "output/qc-frames" / film.stem
    Q.mkdir(parents=True, exist_ok=True)
    F.mkdir(parents=True, exist_ok=True)
    total = _dur(film)
    R = {"film": film.name, "bytes": film.stat().st_size, "s": round(total, 2), "faults": [], "human": []}

    def run(name, cmd, timeout=3600):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        out = r.stdout + r.stderr
        (Q / f"{name}.log").write_text(out, encoding="utf-8")
        print(f"\n===== {name}: exit {r.returncode}\n{out[-1500:]}", flush=True)
        return r.returncode, out

    def fault(msg):
        R["faults"].append(msg)
        print("  FAULT: " + msg, flush=True)

    py = [sys.executable, "-X", "utf8"]
    print(f"QC of {film.name}: {total:.2f}s, {film.stat().st_size:,} bytes", flush=True)
    with render_lock.hold("PP", f"twoway_film_qc EP{a.ep_number}"):
        plan = ta.build_plan(a.ep_number, pp)          # REBUILT, never read from a file
        # ...and the file twoway_qc reads is re-written by the assembler's own --json, so it is THIS plan
        run("plan", py + [str(HERE / "twoway_assemble.py"), str(a.ep_number), "--json",
                          str(d / "renders/assembly-plan.json")])
        srt = d / "output" / f"{film.stem}.srt"
        run("srt", py + [str(HERE / "twoway_srt.py"), str(a.ep_number), "--out", str(srt)])
        b = srt.read_bytes()
        R["srt"] = {"cues": len(re.findall(rb"\r\n\r\n\d+\r\n", b"\r\n\r\n" + b)),
                    "crlf": b.count(b"\n") == b.count(b"\r\n") > 0}
        if not R["srt"]["crlf"]:
            fault("the SRT is not all CRLF")
        sp = max((d / "renders/_pieces").glob("_speech-*.wav"), key=lambda p: p.stat().st_mtime)
        try:
            R["sync"] = tr.assert_audio_in_step(film, sp, ta.TITLE_HEAD_S, total)   # the FILE's length
        except tr.Unrenderable as e:
            fault(f"sync: {e}")
        print("\n===== sync:", R.get("sync"), flush=True)
        c, out = run("twoway_qc", py + [str(HERE / "twoway_qc.py"), str(a.ep_number), str(film),
                                        "--json", str(Q / "twoway_qc.json")])
        # twoway_qc's own shape: "N fault(s)", then "  ! <fault>" per fault and "  · <pass or note>" per pass.
        # Only "!" is a fault (the first version of this read every "·" pass line as one).
        for line in out.splitlines():
            s = line.strip()
            if "LISTEN" in s:
                R["human"].append(s.lstrip("·! "))
            elif s.startswith("! "):
                fault("twoway_qc: " + s[2:])
        if c and not any(f.startswith("twoway_qc") for f in R["faults"]):
            fault(f"twoway_qc exited {c} with no '!' line — read twoway_qc.log")
        c, out = run("verify_cut", py + [str(HERE / "twoway_verify_cut.py"), str(a.ep_number), str(film)])
        R["verify_cut"] = [l.strip() for l in out.splitlines() if re.match(r"\s*(lips|voice|words)\s*:", l)]
        if c:
            fault("verify_cut failed")
        c, out = run("loudness", ["ffmpeg", "-hide_banner", "-nostats", "-i", str(film), "-filter_complex",
                                  "ebur128=peak=true", "-f", "null", "-"])
        s = out[out.rfind("Summary:"):]
        g = lambda rx: (re.search(rx, s) or [None, None])[1]   # noqa: E731
        R["loudness"] = {"I": g(r"I:\s+(-?[\d.]+) LUFS"), "TP": g(r"Peak:\s+(-?[\d.]+) dBFS"),
                         "LRA": g(r"LRA:\s+(-?[\d.]+) LU")}
        mw = d / "output/qc/midroll-listen.wav"
        if mw.exists():
            shutil.copy2(mw, mw.with_name("midroll-listen-previous.wav"))
        mid = next(f for f in plan["furniture"] if f.get("furniture") == "midroll")
        t0, t1 = mid["from_s"] + ta.TITLE_HEAD_S - 2.0, mid["to_s"] + ta.TITLE_HEAD_S + 2.0
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i",
                        str(film), "-vn", "-c:a", "pcm_s16le", "-ar", "48000", str(mw)], check=True, timeout=300)
        if not any("midroll" in h.lower() for h in R["human"]):     # twoway_qc usually lists it already
            R["human"].append(f"LISTEN to the midroll: {mw} ({t0:.1f}-{t1:.1f}s of the film)")
        geo = tr.corner_logo(json.loads((d / "docs/episode.json").read_text(encoding="utf-8")))
        ec = plan["end_card"]
        end_in = round(ec["from_s"] + ec.get("fade_s", 0.3), 3)
        got = tr.logo_presence(film, geo, 0.0, end_in)
        gaps = [r["t"] for r in got if not r["present"]]
        tail = tr.logo_presence(film, geo, end_in + 1.0, plan["total_s"])
        R["logo"] = {"samples": len(got), "present": len(got) - len(gaps), "gaps_s": gaps,
                     "after_end_card_present": sum(r["present"] for r in tail), "after_end_card_samples": len(tail)}
        (Q / "logo-every-2s.json").write_text(json.dumps(got), encoding="utf-8")
        print(f"\n===== LOGO every 2s, 0-{end_in:.1f}s: {R['logo']['present']} of {len(got)}; gaps {gaps or 'NONE'}",
              flush=True)
        if gaps or not got:
            fault(f"the corner logo is missing at {gaps[:20]}s")
        clips = sorted(set(plan["cards_on_disk"].values()) | {g_["clip"] for g_ in
                       (plan.get("graphics") or {}).values() if isinstance(g_, dict) and g_.get("clip")})
        R["chip_clear"] = {}
        for cpath in clips:
            px, bb = tcards.chip_content_px(pathlib.Path(cpath))
            R["chip_clear"][pathlib.Path(cpath).name] = "picture" if px is None else px
            if px and px > tcards.CHIP_MAX_PX:
                fault(f"{pathlib.Path(cpath).name}: {px} px of content under the corner chip at {bb} "
                      f"(re-render with twoway_cards --keep-clear)")
        print("\n===== cards clear of the chip:", R["chip_clear"], flush=True)

    if not a.no_repeats:
        script = Q / "film-order-script.txt"
        script.write_text(film_order_script(d), encoding="utf-8")
        jobs = [("repeats-film", film, script)]
        if a.masters:
            for code in json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))["speakers"]:
                jobs.append((f"repeats-{code}-master", d / f"renders/{code}-master.mp4",
                             d / f"docs/spoken-words-{code}.txt"))
        for name, media, scr in jobs:
            c, out = run(name, py + [str(HERE / "repeated_words.py"), str(media), str(scr),
                                     "--json", str(Q / f"{name}.json")])
            R[name] = "PASS" if c == 0 else "FAIL"
            if c:
                fault(f"{name}: a run of words is said again that the script does not repeat — see {name}.log")

    hp = tr.host_plate_window(plan, d)
    R["host_plate"] = hp
    grabs = [(0.04, "open/first-frame"), (3.5, "open/title"), (hp["first_word_s"], "open/first-word-plate"),
             (hp["off_s"] + 0.3, "open/plate-gone")]
    oc = (plan.get("graphics") or {}).get("open_card")
    if oc:
        grabs.append((oc["at_s"] + 1.0, "open/open-card"))
    grabs += [(m * 60.0 + 0.04, f"minute/{m:02d}m") for m in range(int(end_in // 60) + 1)]
    for s in plan["segments"]:
        what = s.get("card") or (s.get("broll") or "").replace("broll-", "")[:24] or f"{s['layout']}-t{s.get('turn')}"
        t = s["to_s"] - 0.4 if s.get("card") else (s["from_s"] + s["to_s"]) / 2
        grabs.append((t, f"segments/{t:07.1f}s-{re.sub(r'[^A-Za-z0-9-]+', '-', what)}"))
    grabs += [(ec["from_s"] + 3.0, "segments/end-card"), (plan["warranty"]["from_s"] + 1.0, "segments/warranty"),
              (min(total - 1.0, plan["total_s"] + 5.0), "segments/end-frame")]
    for t, rel in grabs:
        p = F / f"{rel}.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-ss", f"{t:.3f}", "-i", str(film), "-frames:v", "1",
                        str(p)], timeout=120)
    try:
        from PIL import Image, ImageDraw
        for sub in ("open", "minute", "segments"):
            fs = sorted((F / sub).glob("*.png"))
            if not fs:
                continue
            w, h, cols = 480, 270, 4
            sh = Image.new("RGB", (cols * w, ((len(fs) + cols - 1) // cols) * (h + 22)), "white")
            dr = ImageDraw.Draw(sh)
            for i, p in enumerate(fs):
                x, y = (i % cols) * w, (i // cols) * (h + 22)
                sh.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y + 22))
                dr.text((x + 4, y + 4), p.stem[:60], fill="black")
            sh.save(F / f"_sheet-{sub}.png")
    except ImportError:
        pass
    R["human"].insert(0, f"WATCH the cut: {film}")
    R["frames"] = str(F)
    (Q / "qc-report.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"{film.name}: {len(R['faults'])} fault(s)" + ("" if R["faults"] else " — every machine check passed"))
    for x in R["faults"]:
        print("  ! " + x)
    print("For Jodie (never ticked here):")
    for x in R["human"]:
        print("  · " + x)
    print(f"Report: {Q / 'qc-report.json'}   Frames + contact sheets: {F}  (LOOK at them)")
    return 1 if R["faults"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
