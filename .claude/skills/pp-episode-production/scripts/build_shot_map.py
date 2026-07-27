# Build the shot map (paragraph/shot boundary times) + a proper sentence-level
# SRT from a presenter render whose HeyGen SRT export is unusable (EP02: 8x60s
# auto-chunks with a bogus tail).
#
# Method (EP02-proven): silence-detect real pauses; treat any HeyGen SRT block
# boundaries that land inside a detected silence as trusted anchors; between
# anchors, place paragraph boundaries proportionally by word count and snap
# each to the nearest >=0.55s pause; then time sentence-level SRT cues
# word-proportionally inside each paragraph.
#
# Usage:
#   python build_shot_map.py <presenter.mp4> <spoken-words.txt> <out_dir> [heygen.srt]
# Writes <out_dir>/shot-map.json and <out_dir>/generated.srt
# spoken-words.txt: one paragraph per blank-line-separated block = one shot.
import json, re, subprocess, sys, collections

VID, WORDS, OUTDIR = sys.argv[1], sys.argv[2], sys.argv[3]
HG_SRT = sys.argv[4] if len(sys.argv) > 4 else None

raw = open(WORDS, encoding="utf-8").read()
# Strip a production-notes header if the spoken-words file carries one. Prefer an
# explicit "PASTE ... BELOW ..." marker line (EP03 used one); otherwise drop any
# leading blank-line blocks that are pure comments (every line starts with #).
mk = re.search(r"(?im)^.*paste\b.*\bbelow\b.*$", raw)
if mk:
    raw = raw[mk.end():]
paras = [p.strip() for p in raw.split("\n\n") if p.strip()]
# Drop leading production-note blocks: pure-# comment blocks OR a bracketed
# [SETUP NOTE …] block (Cowork sometimes ships one; it's not a #-comment so it
# would otherwise become a phantom shot 1 — bit us on EP05 v1+v2).
while paras and (all(ln.lstrip().startswith("#") for ln in paras[0].splitlines())
                 or paras[0].lstrip().startswith("[")):
    paras.pop(0)
print(f"{len(paras)} paragraphs")

def norm(s): return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()

# 1. silences
out = subprocess.run(["ffmpeg","-i",VID,"-af","silencedetect=n=-38dB:d=0.55","-f","null","-"],
                     capture_output=True, text=True).stderr
sil = []
for m in re.finditer(r"silence_start: ([\d.]+)(?:.*?silence_end: ([\d.]+))?", out, re.S):
    pass
starts = [float(m.group(1)) for m in re.finditer(r"silence_start: ([\d.]+)", out)]
ends   = [float(m.group(1)) for m in re.finditer(r"silence_end: ([\d.]+)", out)]
sil = [(s,e) for s,e in zip(starts,ends) if e-s >= 0.55]
SPEECH_START = sil[0][1] if sil and sil[0][0] < 0.5 else 0.0   # lead-in silence
SPEECH_END   = sil[-1][0] if sil and ends and ends[-1] > starts[-1] else None
if SPEECH_END is None: SPEECH_END = float(subprocess.run(
    ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",VID],
    capture_output=True,text=True).stdout.strip())
print(f"speech {SPEECH_START:.2f} -> {SPEECH_END:.2f}s, {len(sil)} pauses")

# 2. anchors from HeyGen SRT block ends (only if silence-verified)
anchors = []
if HG_SRT:
    raw = open(HG_SRT, encoding="utf-8-sig").read()
    blocks = [b for b in re.split(r"\r?\n\r?\n", raw.strip()) if b.strip()]
    ts = re.compile(r"--> (\d{2}):(\d{2}):(\d{2}),(\d{3})")
    for b in blocks[:-1]:                     # last block timing is often bogus
        lines = b.splitlines(); m = ts.search(lines[1])
        end = int(m[1])*3600+int(m[2])*60+int(m[3])+int(m[4])/1000
        tail = norm(" ".join(lines[2:]))[-6:]
        for i,p in enumerate(paras):
            if norm(p)[-6:] == tail and any(s-2 < end < e+2 for s,e in sil):
                anchors.append((i, end)); break
print(f"{len(anchors)} silence-verified anchors")

# 3. boundaries: word-proportional between anchors, snapped to pauses
wc = [len(norm(p)) for p in paras]
bounds = {}
pts = [(-1, SPEECH_START)] + anchors + [(len(paras)-1, SPEECH_END)]
for (i0,t0),(i1,t1) in zip(pts, pts[1:]):
    span = sum(wc[i0+1:i1+1]); acc = 0
    for j in range(i0+1, i1):
        acc += wc[j]
        est = t0 + (t1-t0)*acc/span
        near = [ (abs((s+e)/2-est), (s+e)/2) for s,e in sil if abs((s+e)/2-est) <= 3.5 ]
        bounds[j+1] = min(near)[1] if near else est
    bounds[i1+1] = t1
starts_ = [SPEECH_START] + [bounds[i] for i in range(1, len(paras))]

table = []
for i,p in enumerate(paras):
    end = starts_[i+1] if i+1 < len(paras) else SPEECH_END
    fr = "MCU" if (i+1) % 2 == 1 else "WIDE"   # default alternation; adjust to shot script!
    table.append({"shot": i+1, "start": round(starts_[i],2), "end": round(end,2),
                  "framing": fr, "first_words": " ".join(norm(p)[:5])})
json.dump(table, open(f"{OUTDIR}/shot-map.json","w"), indent=1)

# 4. sentence-level SRT, word-proportional inside each paragraph
def fmt(t):
    ms=int(round(t*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
def two(s):
    if len(s)<=42: return s
    mid=len(s)//2; l=s.rfind(" ",0,mid+1); r=s.find(" ",mid)
    cut=l if (r==-1 or (l!=-1 and mid-l<=r-mid)) else r
    return s if cut==-1 else s[:cut]+"\n"+s[cut+1:]
n=1; cues=[]
for sh,p in zip(table, paras):
    sents=[x.strip() for x in re.split(r"(?<=[.!?])\s+", p) if x.strip()]
    parts=[]
    for s in sents:
        while len(s)>84:
            c=max(s.rfind(", ",0,84), s.rfind(" — ",0,84), s.rfind("; ",0,84))
            if c<=0: c=s.rfind(" ",0,84)
            parts.append(s[:c+1].strip()); s=s[c+1:].strip()
        parts.append(s)
    total=sum(len(c) for c in parts); t=sh["start"]; span=sh["end"]-sh["start"]-0.25
    for c in parts:
        d=span*len(c)/total
        cues.append(f"{n}\n{fmt(t)} --> {fmt(min(t+d,sh['end'])-0.05)}\n{two(c)}\n"); t+=d; n+=1
open(f"{OUTDIR}/generated.srt","w",encoding="utf-8-sig",newline="\r\n").write("\n".join(cues))
print(f"wrote shot-map.json ({len(table)} shots) + generated.srt ({n-1} cues)")
print("REMINDER: set per-shot framing from the episode's shot script (default is naive alternation).")
