#!/bin/bash
# PP EP01 final assembly: presenter base + b-roll picture cuts + chroma-keyed
# overlay + music bookends -> output/PP-EP01-FINAL.mp4 (1080p25, h264+aac)
set -e
cd "/c/Users/Jodie Ralph/PP Videos/PP-EP01"
mkdir -p output

PRES="renders/PP EP01 Trifecta-MASTER.mp4"
OVL="overlay/PP-overlay-full.mp4"
B1="broll/ElevenLabs_video_Veo 3.1 Fast_Medium close-up shot, static c.mp4"      # @55
B2="broll/ElevenLabs_video_Veo 3.1 Fast_Medium shot, eye level, adult .mp4"      # @120
B3="broll/ElevenLabs_video_Veo 3.1 Fast_Wide establishing shot, eye le.mp4"      # @220
B4="broll/ElevenLabs_video_Veo 3.1 Fast_Wide shot, low angle, a field .mp4"      # @390 (8s src)
B5="broll/ElevenLabs_video_Seedance 2.0_Aerial drone shot, wide angle,.mp4"      # @445 (720p, 8s src)
B6="broll/ElevenLabs_video_Veo 3.1 Fast_Extreme close-up, macro lens, .mp4"      # @495
MUS="music/ES_Sleeves Full of Aces - Alexandra Woodward.mp3"

# b-roll windows (start = centre-3): 52,117,217,387,442,492
ffmpeg -y -hide_banner -loglevel warning -stats \
  -i "$PRES" -i "$OVL" \
  -i "$B1" -i "$B2" -i "$B3" -i "$B4" -i "$B5" -i "$B6" \
  -i "$MUS" \
  -filter_complex "
[0:v]tpad=stop_mode=clone:stop_duration=6.4,trim=duration=549.7,setpts=PTS-STARTPTS,fps=25[base];

[2:v]trim=duration=6,setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=5.7:d=0.3:alpha=1,setpts=PTS+52/TB[b1];
[3:v]trim=duration=6,setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=5.7:d=0.3:alpha=1,setpts=PTS+117/TB[b2];
[4:v]trim=duration=6,setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=5.7:d=0.3:alpha=1,setpts=PTS+217/TB[b3];
[5:v]trim=start=1:duration=6,setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=5.7:d=0.3:alpha=1,setpts=PTS+387/TB[b4];
[6:v]trim=start=1:duration=6,setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=5.7:d=0.3:alpha=1,setpts=PTS+442/TB[b5];
[7:v]trim=duration=6,setpts=PTS-STARTPTS,fps=25,scale=1920:1080,setsar=1,format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=5.7:d=0.3:alpha=1,setpts=PTS+492/TB[b6];

[base][b1]overlay=eof_action=pass[v1];
[v1][b2]overlay=eof_action=pass[v2];
[v2][b3]overlay=eof_action=pass[v3];
[v3][b4]overlay=eof_action=pass[v4];
[v4][b5]overlay=eof_action=pass[v5];
[v5][b6]overlay=eof_action=pass[v6];

[1:v]chromakey=0x00FF00:0.28:0.06[ovl];
[v6][ovl]overlay=shortest=0:eof_action=pass,format=yuv420p[vout];

[0:a]apad=whole_dur=549.7,atrim=duration=549.7,asetpts=PTS-STARTPTS[speech];
[8:a]atrim=duration=7.2,asetpts=PTS-STARTPTS,volume=0.40,afade=t=in:st=0:d=0.5,afade=t=out:st=5.2:d=2,adelay=22800|22800[m1];
[8:a]atrim=duration=23,asetpts=PTS-STARTPTS,volume=0.25,afade=t=in:st=0:d=1,afade=t=out:st=20:d=3,adelay=520700|520700[m2];
[speech][m1][m2]amix=inputs=3:duration=first:normalize=0[aout]
" \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -preset medium -crf 18 -r 25 \
  -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart \
  output/PP-EP01-FINAL.mp4
echo "ASSEMBLY DONE"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 output/PP-EP01-FINAL.mp4
