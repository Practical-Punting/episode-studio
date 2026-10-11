# FBX weekly results video — the build (from W01, 11 Oct 2026)

A ~1-minute sales video for **FBX – Form Beater Index**, remade every week with that Saturday's
results. Not a PP-EPnn episode: no rail row, no engine. Media lives in
`G:\My Drive\PP Videos\Promotional Videos\PP-FBX-Wnn\`; this folder is the code.

**Next week, only two things change: `overlay/fbx-week.json` and the HeyGen render.**

## The week's folder
```
PP-FBX-Wnn\
  docs\       FBX-Wnn-shot-script.md, FBX-Wnn-heygen-spoken.txt   (from Cowork/Hugh)
  renders\    presenter-master.mp4, heygen-render.json, words-forced.json, aligned.srt, pause-check.txt
  overlay\    fbx-week.json (THE data), fbx-pack\ (the FBX Video Pack unzipped), cards\, clips\, cues.json, edit-plan.json
  output\     FBX-Wnn-16x9.mp4 (+ .srt), FBX-Wnn-9x16.mp4 (+ .srt), qc\QC-REPORT.md, qc\contact-*.png
```

## Steps (each one a plain command; run from anywhere)
`PY` = `C:\Users\jlral\AppData\Local\Programs\Python\Python312\python.exe`, `S` = this folder, `J` = the week's folder.

1. **Human:** Jodie renders Gordon in HeyGen (usual template, captions off) and names it e.g. `FBX-W02 Results 17 Oct`.
2. Put that exact name in `fbx-week.json → heygen_name`, then `PY S\fbx_fetch.py J` — refuses if two renders match,
   byte-checked against HeyGen's stated size → `renders\presenter-master.mp4` + `heygen-render.json` (the id).
3. `PY S\fbx_align.py J` — forced alignment of the **script** to the audio; halts if any measured pause falls inside a word.
4. Copy last week's `overlay\fbx-week.json`, change the selections, `stated_totals` (from the fact sheet), dates and the
   `cues` phrases if the words changed. `PY S\fbx_data.py J` — **halts if any typed total disagrees with the six rows.**
   `PY S\test_fbx_data.py J` — the guard's own controls.
5. `PY S\fbx_locked.py "FBX-Wnn cards" S\fbx_cards.py J` — every card, from data + measured cues, under the render lock.
   READ the `.last.png` of each clip.
6. `PY S\fbx_locked.py "FBX-Wnn assembly" S\fbx_assemble.py J both`
7. `PY S\fbx_qc.py J "G:\My Drive\PP Videos\docs\FBX-VIDEO-SCRIPTS_v4.md" "...\FBX-VIDEO-VISUAL-BRIEF_v1.md"`
   → `output\qc\QC-REPORT.md`. Copy `renders\aligned.srt` beside both MP4s.
8. **Human:** Jodie watches. Nothing is uploaded, published or sent by the build.

## What it will refuse to do (on purpose)
- Build a week whose totals do not add up (`fbx_data.load_week`).
- Guess a cue time — a phrase not found in the words halts, naming it.
- Print "THE N BIGGEST GAPS ALL WON." in a week where they did not — that headline needs a human.

## Facts learned on W01 (do not re-learn)
- **`align_to_script.py` mis-times digit-heavy speech.** It aligns the TRANSCRIPT, which writes "$2.90" as digits that
  wav2vec2 cannot place; the whole results paragraph collapsed into 6–14 s (real: 6–22 s) while it reported 93.8%
  anchored. `fbx_align.py` aligns our spelled-out script instead and checks itself against silencedetect.
  Evidence: `PP-FBX-W01\renders\aligned-transcript-MISTIMED.srt` vs `aligned.srt`.
- A 1-minute video needs **makeup gain**: the 10-s music-only ending is a sixth of the file and pulled the
  episode recipe to −15.1 LUFS. `fbx_assemble` measures the mix and lifts it after the duck (W01: +1.10 dB → −14.2).
- On 4:2:0 video ffmpeg rounds an odd crop size down; reshaping with the odd size reads skewed frames. QC crops are even.
