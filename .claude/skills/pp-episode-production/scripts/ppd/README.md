# PPD Club promo "Bet Small, Win Big" — the build (25 Oct 2026)

A ~3-minute SALES video for the **PPD Club** (Practical Punting Daily), presented by Gordon, using Cox Plate Day
(Saturday 24 October 2026) as the worked example. Main ask: the 30-day risk-free trial; second ask: the free guide.
Not a PP-EPnn episode: no rail row, no engine. Media: `G:\My Drive\PP Videos\Promotional Videos\PP-PPD-PROMO\`;
this folder is the code. Built as a SIBLING of `scripts/fbx/` and reuses it (fetch, align, render, audio, zoom).

## The folder
```
PP-PPD-PROMO\
  docs\       PPD-PROMO-shot-script.md (the spec), PPD-PROMO-heygen-spoken.txt (Gordon's 436 words), the script, the brief pack zip
  renders\    presenter-master.mp4, heygen-render.json (id, bytes), words-forced.json, aligned.srt, pause-check.txt
  overlay\    ppd-proof-day.json (THE PROOF DAY — swappable), ppd-promo.json (every other word, the offer, the cues),
              ppd-pack\ (Hugh's brief pack unzipped), cards\, clips\, thumbnail\, captions\, ppd-plan.json
  broll\      the library clip + broll-sources.json (source, why, what was rejected)
  output\     PPD-PROMO-16x9.mp4, PPD-PROMO-16x9-captioned.mp4, PPD-PROMO.srt, PPD-PROMO-thumbnail.png, qc\QC-REPORT.md
```

## Steps (`PY` = Python 3.12, `S` = this folder, `F` = ../fbx, `J` = the job folder)
1. **Human:** Jodie renders Gordon in HeyGen and checks it. Then `PY F\fbx_fetch.py J --name "PPD-PROMO Bet Small Win Big"`
   (exactly one completed render by that name, byte-checked).
2. `PY F\fbx_locked.py "PPD align" F\fbx_align.py J` — forced alignment of the SCRIPT; halts if a pause falls inside a word.
3. `PY S\ppd_data.py J` — proves the proof day (every total recomputed from the rows) and finds every cue IN ORDER.
   `PY S\test_ppd_data.py J` — the guard's controls (each tampered copy must halt).
4. `PY S\ppd_promo.py J stage` → `PY S\ppd_thumbnail.py J <isnet.onnx>` (the thumbnail FIRST) → `PY S\ppd_promo.py J title`.
5. `PY S\ppd_promo.py J plan` (dry run) → `PY F\fbx_locked.py "PPD cards" S\ppd_promo.py J cards`. **LOOK at every `.last.png`.**
6. `PY F\fbx_locked.py "PPD assembly" S\ppd_promo.py J assemble` → `... J captions` → `PY S\ppd_promo.py J viewing`.
7. `PY S\ppd_qc.py J` → `output\qc\QC-REPORT.md`.
8. **Human:** Jodie watches. Then Hugh's legal review. Nothing is uploaded, published or sent by the build.

## A future proof day (Hugh: "keep the example swappable")
Copy `ppd-proof-day.json`, change the selections / dividends / `stated` totals / strategies / `example_race`, and — if
Gordon's words change — the matching `cues` in `ppd-promo.json`. `ppd_data.prove` refuses a day whose figures do not add
up. The offer (price, bonus, renewal) lives in `ppd-promo.json -> offer` and is on screen only, in its own clip (`price`).

## What it refuses to do (on purpose)
- Build a proof day whose totals disagree with its rows (`ppd_data.prove`; `test_ppd_data.py` proves it can fail).
- Guess a cue: a phrase not found after the previous one halts, naming it.
- Build a payoff with no beat before it (hook +326%, WIN PAID, the $110 — ~600-700 ms minimum), unnamed rows landing
  under 240 ms apart, or a trifecta whose steps are too close to read.
- Put a quote on screen that is not the words Gordon says for it.

## Facts learned on this build (do not re-learn)
- **Web Animations fill BACKWARDS.** Two animations on the same property of one element fight from t=0 and the later
  one wins — a fade-out written after a fade-in shows the element before it entered; a travel after a slam erases the
  slam. `ppd_cards.seq()` puts every multi-step property on ONE animation; chips are two elements (travel / slam).
- **Raleway's default numerals are old-style** (the 9 and 5 drop below the line). Cards set `lining-nums`; numbers that
  count also get `tabular-nums` so the width does not jitter.
- **The FBX orange scan's red exemption is blind in a PPD video.** It excused orange next to red, assuming red lived only
  in the PP logo; PPD red is everywhere. `ppd_qc` exempts only the PP logo's MEASURED box, and carries two controls.
- The official PPD wordmark PNG has a baked background of exactly #1E1F22 — the brief's canvas — so it sits on the cards
  seamlessly (not on #2C2D31 tiles).
- The hook is ONE clip: the PIP panel floods to full screen so $106.50 never jumps between clips; clearance is measured
  up to the flood.
