# Generalized PP episode assembler — reads episode.json (the agreed contract:
# docs/PP-EPISODE-JSON-SPEC.md) + shot-map.json and emits the Pass A / Pass B
# ffmpeg filtergraphs. Replaces per-episode hand-built generators (proven on EP05 v2).
#
#   python assemble_episode.py <episode.json> <shot-map.json> A > passA_graph.txt
#   python assemble_episode.py <episode.json> <shot-map.json> B > passB_graph.txt
#   python assemble_episode.py <episode.json> <shot-map.json> info   (key times, stderr)
#
# CONTRACT FIELDS consumed verbatim (Cowork writes these):
#   beats[] {n, framing MCU|WIDE, line, card, broll}
#   cards[] {id, beat, eyebrow, headline, detail, hero, layout fullscreen|panel-push}
#   broll[] {target, beat, line, flags, prompt}
#   figures[] {n, card}
# BUILD BLOCK (optional, Claude-Code-side tuning — the "how", per WHO-DOES-WHAT):
#   build {title_head, warranty_tail, mcu_zoom, push_zoom, logo_margin, outro_mcu_from,
#          hero_hold, default_hold, holds{id:sec}, leads{id:sec}, broll_trim, broll_dur,
#          broll_offsets{target:sec}, standing{title,endcard,warranty}, endcard_lead,
#          endcard_beat, warranty_lead, clip_pattern, clips_dir, inputs{...}}
# Standing card roles are matched by id in build.standing (title/endcard/warranty).
import json, sys

EPJ, SMJ, MODE = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "info")
EP = json.load(open(EPJ, encoding="utf-8"))
SM = json.load(open(SMJ, encoding="utf-8"))
B = EP.get("build", {})

HEAD = B.get("title_head", 7.0)
def bs(n): return round(SM[n-1]["start"] + HEAD, 2)
def be(n): return round(SM[n-1]["end"] + HEAD, 2)
SPEECH_END = round(SM[-1]["end"] + HEAD, 2)
END_SETTLE = B.get("end_settle", 3.0)   # breathing room after the last word (outro standard)
TOTAL = round(SPEECH_END + END_SETTLE + B.get("warranty_tail", 6.7), 2)
MCU_ZOOM = B.get("mcu_zoom", 1.26); PUSH_ZOOM = B.get("push_zoom", 1.36)
LOGO_MARGIN = B.get("logo_margin", 40)
BROLL_TRIM = B.get("broll_trim", 0.3); BROLL_DUR = B.get("broll_dur", 5)

beats = {b["n"]: b for b in EP["beats"]}
cards = {c["id"]: c for c in EP["cards"]}
STAND = B.get("standing", {})   # {"title":"title","endcard":"end-card","warranty":"warranty"}
TITLE_ID, END_ID, WAR_ID = STAND.get("title"), STAND.get("endcard"), STAND.get("warranty")
content_ids = [cid for cid in cards if cid not in (TITLE_ID, END_ID, WAR_ID)]

# --- input index layout (must match the ffmpeg -i order the skill runbook documents) ---
# Pass A: [0]=presenter, [1..N]=broll (in broll[] order), [N+1]=logo chip
# Pass B: [0]=_passA, [1..M]=content cards (in cards[] order, excl. standing),
#         [M+1]=title, [M+2]=endcard, [M+3]=warranty, [M+4]=presenter(audio), [M+5]=music
BROLL = EP["broll"]
brindex = {b["target"]: i + 1 for i, b in enumerate(BROLL)}       # 1-based in Pass A
LOGO_INPUT = len(BROLL) + 1
cardindex = {cid: i + 1 for i, cid in enumerate(content_ids)}      # 1-based in Pass B
M = len(content_ids)
TITLE_IN, END_IN, WAR_IN, PRES_A_IN, MUSIC_IN = M + 1, M + 2, M + 3, M + 4, M + 5

MINH = B.get("min_card_hold", 0.0)   # readable-minimum floor (card-sync standard, 25 Jul 2026)
def hold_for(cid):
    raw = (B["holds"][cid] if cid in B.get("holds", {})
           else B.get("hero_hold", 12.0) if cards[cid].get("hero") else B.get("default_hold", 8.0))
    return max(raw, MINH)
def lead_for(cid): return B.get("leads", {}).get(cid, 1.0)

# ---- MCU windows (from beats[].framing) + continuous outro hold ----
outro_from = B.get("outro_mcu_from")
MCU = []
mcu_ns = [n for n in sorted(beats) if beats[n]["framing"] == "MCU" and not (outro_from and n >= outro_from)]
run = []   # merge contiguous MCU beats into one window (avoid a zoom dip between adjacent MCU beats)
for n in mcu_ns:
    if run and n == run[-1] + 1:
        run.append(n)
    else:
        if run: MCU.append((round(bs(run[0])+0.4, 2), round(be(run[-1])-0.4, 2)))
        run = [n]
if run: MCU.append((round(bs(run[0])+0.4, 2), round(be(run[-1])-0.4, 2)))
if outro_from:
    MCU.append((round(bs(outro_from)+0.4, 2), SPEECH_END))
# ---- PUSH windows: one per panel-push card, over its beat ----
PUSH = []
for cid in content_ids:
    if cards[cid].get("layout") == "panel-push":
        n = cards[cid]["beat"]
        PUSH.append((round(bs(n)+lead_for(cid), 2), round(bs(n)+lead_for(cid)+hold_for(cid), 2)))

def ss(e): return f"pow(min(max({e},0),1),2)*(3-2*min(max({e},0),1))"
def act(ws, ease):
    if not ws: return "0"
    return "("+"+".join(f"({ss(f'(it-{a})/{ease}')}-{ss(f'(it-{b-ease})/{ease}')})" for a,b in ws)+")"

def passA():
    Mx, Px = act(MCU, 0.4), act(PUSH, 0.5)
    z = f"'(1+{MCU_ZOOM-1}*{Mx})*(1-{Px})+{PUSH_ZOOM}*{Px}'"
    x = f"'(iw-iw/zoom)/2*(1-{Px})'"
    y = f"'(ih-ih/zoom)/2-55*max({Mx},{Px})'"
    fc = (f"[0:v]tpad=start_duration={HEAD}:start_mode=clone:stop_duration=30:stop_mode=clone,"
          f"trim=duration={TOTAL},setpts=PTS-STARTPTS,fps=25,"
          f"zoompan=z={z}:x={x}:y={y}:d=1:s=1920x1080:fps=25[zoomed];\n")
    for i, br in enumerate(BROLL):
        at = round(bs(br["beat"]) + B.get("broll_offsets", {}).get(br["target"], 1.0), 2)
        idx = brindex[br["target"]]
        fc += (f"[{idx}:v]trim=start={BROLL_TRIM}:duration={BROLL_DUR},setpts=PTS-STARTPTS,fps=25,scale=1920:1080,"
               f"setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={BROLL_DUR-0.3}:d=0.3:alpha=1,"
               f"setpts=PTS+{at}/TB[r{i}];\n")
    fc += f"[{LOGO_INPUT}:v]format=rgba[lg];\n"
    ch = "[zoomed]"
    for i in range(len(BROLL)):
        fc += f"{ch}[r{i}]overlay=eof_action=pass[vr{i}];\n"; ch = f"[vr{i}]"
    fc += f"{ch}[lg]overlay=x=W-w-{LOGO_MARGIN}:y=H-h-{LOGO_MARGIN}[vout]"
    return fc

def passB():
    fc = ""; labels = []
    # title (standing) first — head hold
    title_hold = B.get("holds", {}).get(TITLE_ID, HEAD)
    fc += (f"[{TITLE_IN}:v]fps=25,format=yuva420p,tpad=stop_mode=clone:stop_duration={title_hold},"
           f"fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={round(title_hold-0.3,2)}:d=0.3:alpha=1,"
           f"setpts=PTS+0.0/TB[cdT];\n"); labels.append("cdT")
    # content cards — enter at cue + lead; hold floored by MINH but capped so a
    # card never outstays the NEXT card's entrance (no double-card layering)
    _enters = sorted((round(bs(cards[c]["beat"]) + lead_for(c), 2), c) for c in content_ids)
    _next_enter = {c: (_enters[i + 1][0] if i + 1 < len(_enters) else None)
                   for i, (_t, c) in enumerate(_enters)}
    for k, cid in enumerate(content_ids):
        Ti = round(bs(cards[cid]["beat"]) + lead_for(cid), 2); Hi = hold_for(cid)
        if _next_enter[cid] is not None:
            Hi = max(3.0, min(Hi, round(_next_enter[cid] - Ti - 0.5, 2)))
        idx = cardindex[cid]; lbl = f"cd{k}"; labels.append(lbl)
        if cards[cid].get("layout") == "panel-push":   # left-third green-keyed panel
            fc += (f"[{idx}:v]fps=25,chromakey=0x00FF00:0.28:0.06,scale=810:-1,"
                   f"tpad=stop_mode=clone:stop_duration={Hi},fade=t=in:st=0:d=0.3:alpha=1,"
                   f"fade=t=out:st={round(Hi-0.3,2)}:d=0.3:alpha=1,setpts=PTS+{Ti}/TB[{lbl}];\n")
        else:                                            # fullscreen solid card
            fc += (f"[{idx}:v]fps=25,format=yuva420p,tpad=stop_mode=clone:stop_duration={Hi},"
                   f"fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={round(Hi-0.3,2)}:d=0.3:alpha=1,"
                   f"setpts=PTS+{Ti}/TB[{lbl}];\n")
    # end card: fades in on its beat (e-book promo), fades out before the sign-off
    ec_ti = round(bs(B.get("endcard_beat", cards[END_ID]["beat"])) + B.get("endcard_lead", 1.5), 2)
    ec_hi = (round((bs(B["signoff_beat"]) - 0.3) - ec_ti, 2) if B.get("signoff_beat")
         else B["endcard_hold"] if "endcard_hold" in B
         # default: stay up until the warranty takes over (never leaves before the mention)
         else round((SPEECH_END + B.get("warranty_lead", 0.3) + 0.6) - ec_ti, 2))
    fc += (f"[{END_IN}:v]fps=25,format=yuva420p,tpad=stop_mode=clone:stop_duration={ec_hi},"
           f"fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={round(ec_hi-0.3,2)}:d=0.3:alpha=1,"
           f"setpts=PTS+{ec_ti}/TB[ec];\n"); labels.append("ec")
    # warranty: fades in after the sign-off; final fade-to-black closes it
    war_ti = round(SPEECH_END + B.get("warranty_lead", 0.3), 2)
    fc += (f"[{WAR_IN}:v]fps=25,format=yuva420p,tpad=stop_mode=clone:stop_duration={round(TOTAL - war_ti + 1, 2)},"
           f"fade=t=in:st=0:d=0.6:alpha=1,setpts=PTS+{war_ti}/TB[wr];\n"); labels.append("wr")
    # midroll lower-third (opt-in: build.midroll.composite) — chromakeyed chip
    # over the presenter at the cta beat, gentle fade in/out. Input = MUSIC_IN+1.
    MID = B.get("midroll") or {}
    if MID.get("composite") and MID.get("clip"):
        mid_in = MUSIC_IN + 1
        mt = MID.get("at") or round(bs(MID.get("beat", 1)) + MID.get("offset", 1.0), 2)
        md = MID.get("dur", 5.0); mf = MID.get("fade", 0.4)
        fc += (f"[{mid_in}:v]fps=25,chromakey=0x00FF00:0.28:0.06,"
               f"tpad=stop_mode=clone:stop_duration={md},"
               f"fade=t=in:st=0:d={mf}:alpha=1,fade=t=out:st={round(md - mf, 2)}:d={mf}:alpha=1,"
               f"setpts=PTS+{mt}/TB[mrl];\n"); labels.append("mrl")
    # panel-push cards overlay at x=36:y=312; everything else full-frame 0:0
    ch = "[0:v]"
    for k, lbl in enumerate(labels):
        out = f"[o{k}]" if k < len(labels)-1 else "[vpre]"
        pos = "x=36:y=312" if (lbl.startswith("cd") and lbl != "cdT" and
              cards.get(content_ids[int(lbl[2:])] if lbl[2:].isdigit() else "", {}).get("layout") == "panel-push") else "0:0"
        fc += f"{ch}[{lbl}]overlay={pos}:eof_action=pass{out};\n"; ch = out
    fc += f"[vpre]fade=t=out:st={round(TOTAL-0.5,2)}:d=0.5[vout];\n"
    # AUDIO — speech delayed by HEAD, loudnorm -16; music bed under speech, swells into the settle, soft under warranty
    fc += (f"[{PRES_A_IN}:a]adelay={int(HEAD*1000)}|{int(HEAD*1000)},"
           f"apad=whole_dur={TOTAL},atrim=duration={TOTAL},asetpts=PTS-STARTPTS,"
           f"loudnorm=I=-16:TP=-1.5:LRA=11,"
           f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,asplit=2[sp][spkey];\n")
    sw0 = round(SPEECH_END-5.3, 2); sw1 = round(SPEECH_END-1.3, 2); blm = round(SPEECH_END+2.2, 2); soft = round(TOTAL-0.5, 2)
    env = (f"if(lt(t,0.5),t/0.5,if(lt(t,5.0),1,if(lt(t,6.5),1-(t-5.0)/1.5*0.96,"
           f"if(lt(t,{sw0}),0.04,if(lt(t,{sw1}),0.04+(t-{sw0})/{round(sw1-sw0,2)}*0.51,"
           f"if(lt(t,{blm}),0.55,if(lt(t,{soft}),0.42,max(0,0.42*(1-(t-{soft})/0.5)))))))))")
    # aloop=loop=-1 is INFINITE, bounded by the atrim that follows. It used to be
    # loop=4, which is FIVE plays of the music master — 5 x 117.8s = 589s. That was
    # enough for every episode ever made until EP13 ran 790s, and then the last 201
    # seconds had NO MUSIC AT ALL: the end card and the warranty slide played over
    # ~10s of digital silence, which is exactly what "the end is NEVER silent"
    # (PP-STANDARDS §END SEQUENCE item 3, the EP08 lesson) exists to prevent.
    # A hardcoded loop count is a runtime limit nobody declared. Infinite + atrim has
    # no limit to exceed, so this cannot come back at a longer episode.
    fc += (f"[{MUSIC_IN}:a]aloop=loop=-1:size=6000000,atrim=duration={TOTAL},asetpts=PTS-STARTPTS,"
           f"volume='{env}':eval=frame,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[musraw];\n")
    fc += ("[musraw][spkey]sidechaincompress=threshold=0.015:ratio=14:attack=12:release=420:makeup=1:level_sc=2[mus];\n")
    fc += "[sp][mus]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]"
    return fc

if MODE.upper() == "A": print(passA())
elif MODE.upper() == "B": print(passB())
else:
    import sys as _s
    print(f"episode={EP.get('episode')} HEAD={HEAD} SPEECH_END={SPEECH_END} TOTAL={TOTAL}", file=_s.stderr)
    print(f"content cards={M} broll={len(BROLL)} MCU windows={len(MCU)} PUSH={len(PUSH)}", file=_s.stderr)
    print(f"inputs: passA[0]=pres [1..{len(BROLL)}]=broll [{LOGO_INPUT}]=logochip | "
          f"passB[0]=passA [1..{M}]=cards [{TITLE_IN}]=title [{END_IN}]=endcard [{WAR_IN}]=warranty "
          f"[{PRES_A_IN}]=pres-audio [{MUSIC_IN}]=music", file=_s.stderr)
