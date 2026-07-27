#!/bin/bash
# EP02 PASS B v3 -> PP-EP02-FINAL-v3.mp4
#  AUDIO: speech loudnorm to -16 LUFS (YouTube standard); music bed 4% with
#         sidechain ducking keyed off the speech; full sting at head/tail.
#  VIDEO: end card holds solid under the warranty fade-in (kills the ~0.5s
#         window where both cards were transparent and Floyd showed through).
set -e
cd "/c/Users/Jodie Ralph/PP Videos/PP-EP02"
CL=overlay/clips
PRES="renders/PP EP02 Killer Strategies Trifecta - MASTER.mp4"
MUS="../PP-EP01/music/ES_Sleeves Full of Aces - Alexandra Woodward.mp3"

FC=""
EP01_CARDS="8 0.8
9 15.9
10 178.3
11 195.9
12 240.4
13 286.0"
i=0
while read -r idx at; do
  FC+="[$idx:v]fps=25,chromakey=0x00FF00:0.28:0.06,setpts=PTS+$at/TB[e$i];"
  i=$((i+1))
done <<< "$EP01_CARDS"

NEW_PANELS="3 42.1 7.2 3.0
4 76.0 10.0 2.9
6 158.3 11.7 3.533
7 225.9 12.9 3.733"
j=0
while read -r idx at win clip; do
  PAD=$(python -c "print(round($win-$clip,3))")
  FO=$(python -c "print(round($win-0.3,3))")
  FC+="[$idx:v]fps=25,chromakey=0x00FF00:0.28:0.06,scale=810:-1,tpad=stop_mode=clone:stop_duration=$PAD,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=$FO:d=0.3:alpha=1,setpts=PTS+$at/TB[n$j];"
  j=$((j+1))
done <<< "$NEW_PANELS"

FC+="[5:v]fps=25,chromakey=0x00FF00:0.28:0.06,tpad=stop_mode=clone:stop_duration=8.1,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=11.3:d=0.3:alpha=1,setpts=PTS+122.0/TB[rg];"
FC+="[1:v]fps=25,format=yuva420p,tpad=stop_mode=clone:stop_duration=15.5,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=15.7:d=0.3:alpha=1,setpts=PTS+96.0/TB[st];"
# END CARD: hold solid to 396.6 (no fade-out) so the warranty rises on top of it
FC+="[14:v]fps=25,format=yuva420p,tpad=stop_mode=clone:stop_duration=14.0,fade=t=in:st=0:d=0.3:alpha=1,setpts=PTS+379.5/TB[ec];"
# WARRANTY: fades in over the still-solid end card, holds to 401.9
FC+="[2:v]fps=25,format=yuva420p,tpad=stop_mode=clone:stop_duration=5.6,fade=t=in:st=0:d=0.5:alpha=1,setpts=PTS+394.6/TB[wr];"

CH="[0:v]"
k=0
for lbl in e0 e1 e2 e3 e4 e5 n0 n1 n2 n3 rg st ec wr; do
  FC+="$CH[$lbl]overlay=$( [ "${lbl:0:1}" = "n" ] && echo "x=36:y=312" || echo "0:0" ):eof_action=pass[c$k];"
  CH="[c$k]"; k=$((k+1))
done
FC+="${CH}fade=t=out:st=401.9:d=0.4[vout];"

# ---- AUDIO ----
# Speech: normalise to -16 LUFS (YouTube target), then split — one copy to the
# mix, one as the sidechain key. loudnorm resamples to 192k, so force back to 48k.
FC+="[15:a]apad=whole_dur=402.3,atrim=duration=402.3,asetpts=PTS-STARTPTS,"
FC+="loudnorm=I=-16:TP=-1.5:LRA=11,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,asplit=2[sp][spkey];"
# Music: base envelope (full head/tail, 4% bed under speech) ...
FC+="[16:a]aloop=loop=3:size=6000000,atrim=duration=402.3,asetpts=PTS-STARTPTS,"
FC+="volume='if(lt(t,0.35),t/0.35,if(lt(t,4.5),1,if(lt(t,5.5),1-(t-4.5)*0.5,if(lt(t,6.4),0.5,if(lt(t,7.5),0.5-(t-6.4)/1.1*0.46,if(lt(t,378.5),0.04,if(lt(t,380.5),0.04+(t-378.5)/2*0.46,if(lt(t,394.6),0.5,if(lt(t,401.5),0.42,max(0,0.42*(1-(t-401.5)/0.7)))))))))))':eval=frame,"
FC+="aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[musraw];"
# ... then duck it live against the speech: dips the instant he talks, lifts in his pauses.
FC+="[musraw][spkey]sidechaincompress=threshold=0.015:ratio=14:attack=12:release=420:makeup=1:level_sc=2[mus];"
FC+="[sp][mus]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]"

ffmpeg -y -hide_banner -loglevel warning -stats \
  -i overlay/_passA-v2.mp4 \
  -i "$CL/01-survey-stat.mp4" -i "$CL/02-gamble-responsibly.mp4" -i "$CL/03-pull-quote.mp4" \
  -i "$CL/04-common-mistake.mp4" -i "$CL/05-the-other-trap.mp4" -i "$CL/06-structure-the-ticket.mp4" \
  -i "$CL/07-no-banker-no-bet.mp4" \
  -i "$CL/ep01-title.mp4" -i "$CL/ep01-gate.mp4" -i "$CL/ep01-grid.mp4" -i "$CL/ep01-podium.mp4" \
  -i "$CL/ep01-skulk.mp4" -i "$CL/ep01-ceiling.mp4" -i "$CL/08-end-card.mp4" \
  -i "$PRES" -i "$MUS" \
  -filter_complex "$FC" -map "[vout]" -map "[aout]" \
  -c:v libx264 -preset medium -crf 18 -r 25 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
  output/PP-EP02-FINAL-v3.mp4
echo "PASS B v3 DONE"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 output/PP-EP02-FINAL-v3.mp4
