# Generate the PASS A filtergraph: unified zoompan (MCU digital zoom + panel
# push) + b-roll overlays + logo. Write result to a file, run ffmpeg with
# -filter_complex_script (the expressions are too long for the command line).
#
# WHY zoompan and not overlay layers for the zoom/push: trim branches of the
# SAME input buffer the whole main stream until their window arrives -> RAM
# explosion on this 8GB machine, encoder dies with 0 frames (EP02 lesson).
# Overlay layers are safe ONLY for separate-file inputs (b-roll, cards, logo).
#
# Edit the episode data below, then:
#   python gen_passA_graph.py > passA_graph.txt
#   ffmpeg -i presenter.mp4 -i <broll...> -i logo.png \
#     -filter_complex_script passA_graph.txt -map "[vout]" -an \
#     -c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p _passA.mp4
#
# EP02 v2 values shown (approved): MCU 1.26, push 1.36, logo 428px @ 90%.

# ---- EPISODE DATA (edit per episode; times from the shot map) ----
# HEAD_TRIM: seconds of silent lead-in to cut from the presenter so speech lands
# on the intended title window. Leave 0 unless the render's real speech onset
# (silencedetect it) is later than the brief's title window — EP03 came back with
# a 12.9s silent head vs a 7s title, so HEAD_TRIM=5.9. When >0, ALL shot-map/SRT
# times must be on the trimmed timeline (subtract the same offset).
HEAD_TRIM = 0.0
MCU = [(6.39,28.00),(41.54,60.87),(75.06,93.82),(120.89,134.56),(157.64,177.63),
       (195.29,214.23),(225.18,239.75),(257.92,285.39),(302.20,322.85),(348.24,379.22)]
PUSH = [(15.35,27.55),(41.55,49.85),(75.45,86.55),(157.75,170.55),(177.75,213.95),
        (225.35,248.55),(285.45,301.95)]  # merge adjacent panel cues (<2s gap) to avoid jitter
# (input_index, source_trim_start, timeline_position) — inputs 1..N are b-roll files
BROLL = [(4,0.0,8.0),(1,0.5,30.0),(2,0.5,53.0),(3,0.5,113.5),(5,0.0,250.5),(6,0.0,325.5)]
LOGO_INPUT = 7          # logo png input index
TOTAL = 402.3           # speech end + end-card/warranty tail
FREEZE = 8.5            # tpad clone beyond presenter duration
MCU_ZOOM, PUSH_ZOOM = 1.26, 1.36
LOGO_W, LOGO_ALPHA = 428, 0.9   # locked: prominent, ~90% (Jodie, EP02)

# ---- generator (no per-episode edits below) ----
def ss(e): return f"pow(min(max({e},0),1),2)*(3-2*min(max({e},0),1))"
def act(ws, ease):
    return "("+"+".join(f"({ss(f'(it-{a})/{ease}')}-{ss(f'(it-{b-ease})/{ease}')})" for a,b in ws)+")"
M, P = act(MCU,0.4), act(PUSH,0.5)
z = f"'(1+{MCU_ZOOM-1}*{M})*(1-{P})+{PUSH_ZOOM}*{P}'"
x = f"'(iw-iw/zoom)/2*(1-{P})'"           # push slides the crop window left -> avatar right
y = f"'(ih-ih/zoom)/2-55*max({M},{P})'"   # headroom bias when zoomed
head = f"trim=start={HEAD_TRIM},setpts=PTS-STARTPTS," if HEAD_TRIM else ""
fc = (f"[0:v]{head}tpad=stop_mode=clone:stop_duration={FREEZE},trim=duration={TOTAL},"
      f"setpts=PTS-STARTPTS,fps=25,zoompan=z={z}:x={x}:y={y}:d=1:s=1920x1080:fps=25[zoomed];\n")
for i,(idx,s0,at) in enumerate(BROLL):
    fc += (f"[{idx}:v]trim=start={s0}:duration=5,setpts=PTS-STARTPTS,fps=25,scale=1920:1080,"
           f"setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=4.7:d=0.3:alpha=1,"
           f"setpts=PTS+{at}/TB[r{i}];\n")
lh = round(LOGO_W*65/214)
fc += f"[{LOGO_INPUT}:v]scale={LOGO_W}:-1,format=argb,colorchannelmixer=aa={LOGO_ALPHA}[lg];\n"
ch = "[zoomed]"
for i in range(len(BROLL)):
    fc += f"{ch}[r{i}]overlay=eof_action=pass[vr{i}];\n"; ch = f"[vr{i}]"
fc += f"{ch}[lg]overlay=x={1920-LOGO_W-40}:y={1080-lh-40}[vout]"
print(fc)
