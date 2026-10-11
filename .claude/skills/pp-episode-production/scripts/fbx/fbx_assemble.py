#!/usr/bin/env python3
"""fbx_assemble.py — assemble the FBX weekly results video, 16:9 (the email) and 9:16 (the Short).

    python fbx_assemble.py <job_dir> [16x9|9x16|both]

Reads the cue sheet (fbx_data.cue_sheet, measured from the audio) and the card clips that
fbx_cards.py rendered, and writes output/FBX-<week>-16x9.mp4 and/or output/FBX-<week>-9x16.mp4,
plus overlay/edit-plan.json (every window, for the record and for QC to compare against).

WHAT IS DIFFERENT FROM A PP EPISODE (Jodie's FBX decisions, 11 Oct 2026):
  · NO 7-second title head — the video opens on Gordon saying the hook. So there is ONE clock:
    every cue time is the presenter's time AND the finished file's time (no bs() crossing).
  · no B-roll, no e-book end card; the ending is Gordon's RG line → the FBX closing card
    (3 s hold after it builds) → the standard PP warranty slide.
THE SAME AS A PP EPISODE, ON PURPOSE:
  · the audio recipe — speech loudnorm to publish_loudness.TARGET_LUFS, the PP music master,
    the 0.04 bed scaled by LIFT, the same duck, amix normalize=0, alimiter level=0. The only
    change is the opening: the 5-second full-level sting existed to fill the title head, and
    there is no title head, so the bed simply fades up under the first words.
  · eased zoom moves (MCU 126%, panel push 136%) as the only transition on Gordon;
    full-screen cards never cross-fade (the incoming fades over an outgoing held solid).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fbx_data as fd  # noqa: E402
from publish_loudness import TARGET_LUFS, LIFT, LIMIT, DUCK_THRESHOLD_REF  # noqa: E402

ASSETS = HERE.parent.parent / "assets"
FADE = 0.3
CLOSING_BUILD = 1.25     # closing card: arrow lands at 950+300 ms (fbx_cards.closing_spec)
CLOSING_HOLD = 3.0       # shot script: "Hold for 3 seconds"
WARRANTY_TAIL = 6.7      # the PP standard (assemble_episode warranty_tail)
MCU_ZOOM, PUSH_ZOOM = 1.26, 1.36
V_CROP = (1080, 960, 465, 30)   # 9:16: Gordon's centred crop, 1:1 pixels, into the lower half

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass


def plan(T):
    P = {"speech_end": T["speech_end"]}
    P["closing_in"] = round(T["speech_end"] + 0.25, 2)
    P["warranty_in"] = round(P["closing_in"] + CLOSING_BUILD + CLOSING_HOLD, 2)
    P["total"] = round(P["warranty_in"] + WARRANTY_TAIL, 2)
    # (name, in, out, fade_in, fade_out)  — out of a full-screen card that is covered by the
    # next one is the next one's in + FADE, so the outgoing is still solid underneath.
    P["windows16"] = [
        ("hook-panel", 0.0, T["report_in"] + FADE, 0.0, 0.0),
        ("report", T["report_in"], T["results_in"] + FADE, FADE, 0.0),
        ("results", T["results_in"], T["summary_in"] + FADE, FADE, 0.0),
        ("summary", T["summary_in"], T["gap_in"] + FADE, FADE, 0.0),
        ("gap", T["gap_in"], T["gap_out"] + 0.15, FADE, FADE),
        ("lower-third", T["join_in"], T["rg_in"] + 0.15, 0.0, FADE),
        ("closing", P["closing_in"], P["warranty_in"] + 0.6, FADE, 0.0),
        ("warranty", P["warranty_in"], P["total"], 0.6, 0.0),
    ]
    P["windows9"] = [
        ("upper-idle", 0.0, P["total"], 0.0, 0.0),
        ("upper-hook", 0.0, T["report_in"] + FADE, 0.0, 0.0),
        ("report", T["report_in"], T["results_in"] + FADE, FADE, 0.0),
        ("results", T["results_in"], T["gap_in"] + FADE, FADE, 0.0),
        ("gap", T["gap_in"], T["gap_out"] + 0.15, FADE, FADE),
        ("upper-join", T["join_in"], T["rg_in"] + 0.15, FADE, FADE),
        ("closing", P["closing_in"], P["warranty_in"] + 0.6, FADE, 0.0),
        ("warranty", P["warranty_in"], P["total"], 0.6, 0.0),
    ]
    P["push"] = (-1.0, round(T["report_in"] + 1.0, 2))     # shot 1: Gordon pushed right of the panel
    P["mcu"] = (round(T["join_in"] - 0.2, 2), P["total"] + 1)   # shots 8–9
    return P


def ss(e):
    return f"pow(min(max({e},0),1),2)*(3-2*min(max({e},0),1))"


def act(a, b, ease):
    return f"({ss(f'(it-{a})/{ease}')}-{ss(f'(it-{b - ease})/{ease}')})"


def measure_mix(job, P, master, music, gain_db=0.0):
    """Integrated loudness of the finished MIX, rendered audio-only (a few seconds)."""
    g = audio_graph(P, 0, 1, gain_db).replace("[aout]", "[mixed];\n[mixed]ebur128=peak=true[aout]")
    gfile = job / "overlay" / "graph-audio-probe.txt"
    gfile.write_text(g, encoding="utf-8")
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(master), "-i", str(music),
                        "-filter_complex_script", str(gfile), "-map", "[aout]", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    import re
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)[-1])


def audio_graph(P, pres_in, music_in, gain_db=0.0):
    tot, se = P["total"], P["speech_end"]
    head = P.get("head", 0.0)    # a title card in front (the promo, Jodie 11 Oct); W01 has none
    sw0, sw1, blm, soft = round(se - 5.3, 2), round(se - 1.3, 2), P["warranty_in"], round(tot - 0.5, 2)
    tail = (f"if(lt(t,{sw1}),0.04+(t-{sw0})/{round(sw1 - sw0, 2)}*0.51,"
            f"if(lt(t,{blm}),0.55,if(lt(t,{soft}),0.42,max(0,0.42*(1-(t-{soft})/0.5)))))")
    if head:
        # the STANDARD PP title-head sting (assemble_episode.py): full 0.5–5.0 s, down to the 0.04 bed by 6.5 s
        env = f"if(lt(t,0.5),t/0.5,if(lt(t,5.0),1,if(lt(t,6.5),1-(t-5.0)/1.5*0.96,if(lt(t,{sw0}),0.04,{tail}))))"
    else:
        env = f"if(lt(t,0.5),0.04*t/0.5,if(lt(t,{sw0}),0.04,{tail}))"
    delay = f"adelay={int(head * 1000)}|{int(head * 1000)}," if head else ""
    return (f"[{pres_in}:a]{delay}apad=whole_dur={tot},atrim=duration={tot},asetpts=PTS-STARTPTS,"
            f"loudnorm=I={TARGET_LUFS:g}:TP=-1.5:LRA=11,"
            f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,asplit=2[sp][spkey];\n"
            f"[{music_in}:a]aloop=loop=-1:size=6000000,atrim=duration={tot},asetpts=PTS-STARTPTS,"
            f"volume='{LIFT:.6f}*({env})':eval=frame,"
            f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[musraw];\n"
            f"[musraw][spkey]sidechaincompress=threshold={DUCK_THRESHOLD_REF * LIFT:.6f}:ratio=14:attack=12:"
            f"release=420:makeup=1:level_sc=2[mus];\n"
            f"[sp][mus]amix=inputs=2:duration=first:normalize=0,volume={gain_db:.2f}dB,"
            f"alimiter=limit={LIMIT}:level=0[aout]")


def card_chain(idx, name, t_in, t_out, fi, fo, label):
    d = round(t_out - t_in, 3)
    f = (f"[{idx}:v]fps=25,format=yuva444p,tpad=stop_mode=clone:stop_duration={d + 2},"
         f"trim=duration={d},setpts=PTS-STARTPTS")
    if fi:
        f += f",fade=t=in:st=0:d={fi}:alpha=1"
    if fo:
        f += f",fade=t=out:st={round(d - fo, 3)}:d={fo}:alpha=1"
    return f + f",setpts=PTS+{t_in}/TB[{label}];\n"


def build(job: Path, fmt: str, T, P, wk):
    clips = job / "overlay" / "clips"
    pp_videos = job.parents[1]
    music = pp_videos / "PP-EP01-The-Trifecta-Mistake" / "music" / "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"
    chip = ASSETS / "video-logo-chip.png"
    master = job / "renders" / "presenter-master.mp4"
    tot = P["total"]
    windows = P["windows16"] if fmt == "16x9" else P["windows9"]
    inputs = [master, chip]
    for name, *_ in windows:
        c = list(clips.glob(f"fbx-{fmt}-{name}.m*"))
        if len(c) != 1:
            raise fd.Halt(f"expected exactly one clip fbx-{fmt}-{name}.mp4/.mov in {clips}, found {len(c)}")
        inputs.append(c[0])
    inputs.append(music)
    music_in = len(inputs) - 1
    for p in inputs:
        if not Path(p).is_file():
            raise fd.Halt(f"missing input {p}")

    g = ""
    if fmt == "16x9":
        a1, b1 = P["push"]
        a2, b2 = P["mcu"]
        Mx, Px = act(a2, b2, 0.4), act(a1, b1, 0.5)
        z = f"'(1+{MCU_ZOOM - 1}*{Mx})*(1-{Px})+{PUSH_ZOOM}*{Px}'"
        x = f"'(iw-iw/zoom)/2*(1-{Px})'"
        y = f"'(ih-ih/zoom)/2-55*max({Mx},{Px})'"
        g += (f"[0:v]tpad=stop_mode=clone:stop_duration=60,trim=duration={tot},setpts=PTS-STARTPTS,fps=25,"
              f"zoompan=z={z}:x={x}:y={y}:d=1:s=1920x1080:fps=25[zoomed];\n"
              f"[1:v]format=rgba[lg];\n[zoomed][lg]overlay=x=W-w-40:y=H-h-40[v0];\n")
    else:
        w, h, cx, cy = V_CROP
        g += (f"color=c=0x1B2126:s=1080x1920:r=25:d={tot}[base];\n"
              f"[0:v]tpad=stop_mode=clone:stop_duration=60,trim=duration={tot},setpts=PTS-STARTPTS,fps=25,"
              f"crop={w}:{h}:{cx}:{cy}[gord];\n"
              f"[1:v]format=rgba,scale=300:-1[lg];\n"
              f"[base][gord]overlay=x=0:y=960[vg];\n[vg][lg]overlay=x=W-w-28:y=H-h-28[v0];\n")
    cur = "v0"
    for k, (name, t_in, t_out, fi, fo) in enumerate(windows):
        g += card_chain(k + 2, name, round(t_in, 3), round(t_out, 3), fi, fo, f"c{k}")
        g += f"[{cur}][c{k}]overlay=x=0:y=0:eof_action=pass[v{k + 1}];\n"
        cur = f"v{k + 1}"
    g += f"[{cur}]fade=t=out:st={round(tot - 0.5, 2)}:d=0.5,format=yuv420p[vout];\n"
    # 🔴 MAKEUP GAIN, MEASURED. The episode recipe lands at -14 because ten minutes of speech
    # swamp a 10-second music-only ending. In a ONE-minute video that ending is a sixth of the
    # file and pulls the integrated level down (FBX-W01 first cut: -15.1 LUFS, outside -14 ±1).
    # So the finished MIX is measured and lifted as a whole, AFTER the duck and BEFORE the
    # limiter: the voice/music balance and the ducking are untouched, only the level moves.
    I0, _ = measure_mix(job, P, master, music)
    gain = max(-3.0, min(3.0, round(TARGET_LUFS - I0, 2)))
    I1, tp1 = measure_mix(job, P, master, music, gain)
    print(f"  mix loudness {I0:.1f} LUFS -> makeup {gain:+.2f} dB -> {I1:.1f} LUFS, peak {tp1:.1f} dBFS", flush=True)
    P.setdefault("makeup_db", {})[fmt] = gain
    g += audio_graph(P, 0, music_in, gain)

    out = job / "output" / f"FBX-{wk['raw']['week']}-{fmt}.mp4"
    gfile = job / "overlay" / f"graph-{fmt}.txt"
    gfile.write_text(g, encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
    for p in inputs:
        cmd += ["-i", str(p)]
    cmd += ["-filter_complex_script", str(gfile), "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            "-map_metadata", "-1", "-map_chapters", "-1", "-dn", "-t", str(tot), str(out)]
    print(f"assembling {out.name}: {tot:.2f}s, {len(windows)} card windows", flush=True)
    r = subprocess.run(cmd)
    if r.returncode:
        raise fd.Halt(f"ffmpeg failed assembling {out.name}")
    return out


def main():
    job = Path(sys.argv[1]).resolve()
    which = sys.argv[2] if len(sys.argv) > 2 else "both"
    try:
        wk = fd.load_week(job)
        T = fd.cue_sheet(job, wk)
        P = plan(T)
        for fmt in (["16x9", "9x16"] if which == "both" else [which]):
            print("wrote", build(job, fmt, T, P, wk))
        (job / "overlay" / "edit-plan.json").write_text(json.dumps({"cues": T, "plan": P}, indent=1), encoding="utf-8")
    except fd.Halt as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
