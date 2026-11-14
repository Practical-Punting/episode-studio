---
description: Drive a two-way (Gordon + Steve) Practical Punting episode — or a batch — through its run order, stopping only at Jodie's gates. Usage: /two-way EP57 [EP58 EP59]
---

You are driving two-way episode(s): **$ARGUMENTS**. Work from `C:\Users\jlral\repos\episode-studio`.
The engine of this is `engine/twoway_run.py`. It works out where each episode is FROM DISK and the
rail, runs every code step itself, and stops with one of four things. Your job is to keep it moving
and talk to Jodie only at her gates.

## The loop
1. Run `python engine\twoway_run.py <the episode numbers>` (all of them together for a batch).
2. Read what it printed at the bottom, and act:
   - **🔴 FAULT** — a defect, not a question. Tell Jodie straight away in plain words (a defect is a
     fact, never withheld), fix it if it is a code fault you can fix, then run again.
   - **SESSION STEP** — something only you can do (write the commission, the card pages, the e-book
     body, the thumbnail page, the YouTube copy; generate on Higgsfield through `engine\hf_guard.py`;
     run the fresh-eyes reviewer). Do exactly what it says, following PP-EP56 as the worked example
     and loading the relevant skill (pp-two-way-episode, pp-motion-graphics, pp-episode-script…).
     Then run again. Do not ask Jodie about a session step.
   - **WAITING** — e.g. HeyGen still rendering. Tell Jodie in one line; run again when she says.
   - **❓ ONE QUESTION FOR JODIE** — a gate. Ask her exactly that, in plain words, ONE question,
     with the links/paths it gives. Then stop and wait for her.
3. When she answers a gate, record it IN HER WORDS, then run again:
   `python engine\twoway_run.py --verdict 57 <gate> approved "her words"` — or, if she wants
   changes, `… <gate> changes "her words" --change "change 1" --change "change 2"` (each change its
   own OPEN item — the split-every-verdict rule). Mark them later with
   `--change-status 57 <gate> <n> DONE|DROPPED`. Never record a verdict she did not give.
   Gates: words · render_paste · broll_cover · render_listen · cut_watch · join_listen ·
   title_thumbnail · publish. (The words gate passes when the approved file lands; publish when the
   rail has the YouTube link.)
4. **"clip"** (or when she is ready to paste in HeyGen): run `python engine\twoway_run.py <eps> --clip`
   and relay its message — ONE script on the clipboard each time, never two, never any notes.

## How to talk to Jodie at a gate
- One question, plain words, warm; a clever 15-year-old. End every message with ONE clearly-marked question.
- **Reviews (render listen, cut watch, b-roll, title/thumbnail): free-form first.** Hand over the
  link and the facts only — no verdict of yours, no checklist first. "What do you think?" Then
  stop. Only after she has answered, a short safety-net checklist of what she did not mention.
- A real defect you already know about you say straight away (it is a fact, not a verdict).

## Standing rulings — never ask these
Gordon reads Brian Blackwell, Steve reads Barry Meadow · web addresses in the article are named, not
read (the runner drafts the substitutions by the standing rule and shows them with the words) · a
NARR author bio is split off · soft hyphens stripped · no cadence anywhere · Hugh only for words that
break the approved EP55/EP56 pattern · a list too long for a card shows what fits, the e-book carries
all · stray render words between sentences are cut, with a join WAV for her ear (retake only
mid-sentence) · price is not a gate under 20 minutes · b-roll: people or horses in EVERY clip and at
least one of horses RACING (Jodie, 14 Nov 2026 — replaces "empty track"), plain saddlecloths, four at
most (`broll_prompt_rules.commission_brief()`) · Higgsfield only through hf_guard, inside 110 credits.

## Never
Never press Generate in HeyGen, never start a render by API, never publish, never tick a gate for her,
never spend Higgsfield outside `hf_guard.py`. New words are Cowork's: they arrive approved as
`G:\My Drive\PP Videos\docs\two-way-words-drafts\<Series>-Part-N-new-words-APPROVED.md`, and the runner
copies each into its episode. Commit only your own files, by name; another session may share the repo.
At the end of a substantial piece, update the checkpoint and add a dated line to the foot of PP-ATLAS.md.
