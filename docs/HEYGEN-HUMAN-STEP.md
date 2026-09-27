# HeyGen presenter — the human "click" step (bake this into the whole pipeline)

**Purpose of this doc:** the HeyGen presenter render is a *human-in-the-loop* step
by design. Claude prepares everything before it and does everything after it, but
the actual **"Generate" click is Jodie's**. This must be made explicit — and
actively *prompted* — in every layer: the skill, the master workflow/process, any
plugin/automation, the documentation, and the runner interface Claude builds. It
must never be silently assumed or skipped.

---

## The one-line rule
**Generating Gordon (the presenter) = a few clicks by Jodie in the HeyGen web app,
using our locked TEMPLATE. Claude writes the script, tells her exactly what to
click, then takes over the moment it's rendered.**

## The locked HeyGen TEMPLATE (avatar + voice + backdrop baked in)
We use one standing **HeyGen Template** for every episode. A template is a layout
built once in HeyGen Studio that **stores the avatar, the voice, the backdrop, and
the scene**, and exposes a **text slot** for the script. Because the avatar and
voice are baked in, the wrong-voice / wrong-avatar mistakes (e.g. the EP04
ElevenLabs → US-accent bug) **cannot recur** — you only drop in the script.

> ## 🔴 THE PRESENTER WAS REBUILT AGAIN, 20 Aug 2026. THIS TABLE IS THE ONE HOME.
> **20 Aug: a new avatar and a NEW TEMPLATE. The voice id did not change.**
> The 19 Aug rebuild is one day old and already superseded, so **read the date on any
> template id you meet elsewhere before using it.**
>
> | | **NOW — 20 Aug 2026** | was (19 Aug) | was (23 Jul) |
> |---|---|---|---|
> | **template** | **`ac627c3ae2e9443bbbdf520215dbead8`** | `d98c9195befa419290ef955f6149e861` ("PP Template v3 Peter") | `5f4b2ed0e33a4351ae4debfbf804d7f2` ("PP Videos template v2") |
> | **voice** | **`7e157ec62c9c45f1adca12faae72c86f`** | `7e157ec62c9c45f1adca12faae72c86f` — unchanged | the voice baked into v2 |
> | **avatar** | rebuilt 20 Aug — **id not given, do not invent one** | "Peter" | "Floyd" `de774dd2f3ef4a52bc31dee6fc91f118` |
>
> ### 🔴 THE RULE THE REBUILD PRODUCED — WHY THE BACKGROUND ARTEFACTS HAPPENED
> **A PRESENTER AVATAR IS BUILT AGAINST A PLAIN EMPTY WALL, NEVER AGAINST A SCENE.**
> An avatar trained against a scene carries fragments of that scene into every render,
> and they show up as artefacts behind the presenter on every episode built from it.
> The backdrop is the TEMPLATE's job, applied after; it is never baked into the avatar.
> *(Full write-up in the claude.ai project: `claude/PP-presenter-avatar-and-voice.md`.)*
>
> ### ⚠️ TWO THINGS HERE ARE NOT SETTLED — DO NOT GUESS EITHER
> · **The presenter's NAME is unsettled three ways: Gordon / Peter / Luke.** Every
>   script still says "Gordon" and the board's flag copy still says *"Gordon's render is
>   still cooking"*. **Nothing here assumes which one wins — it is Jodie's call.**
> · ✅ **THE VOICE CONFLICT IS RESOLVED (21 Aug 2026) — PATRICK IS CURRENT.**
>   **`7e157ec62c9c45f1adca12faae72c86f` ("Patrick") is the voice.** The conflicting
>   claim lived in `SKILL.md`, which called Patrick *"SUPERSEDED — source of the wrong
>   voice"* and called the **"PP Gordon Floyd" clone `a6d512a13a3c40c1b79fdd39856a2b72`**
>   locked and *"ear-confirmed PERFECT"*.
>   🔴 **IT WAS EXACTLY BACK TO FRONT. The Floyd clone is what produced the AMERICAN
>   ACCENT on EP31 on 19 Aug**, and that is why Hugh and Jodie replaced the avatar, the
>   voice and the background that day. **HeyGen's own UI showed "Voice: Patrick" on
>   EP35's render on 20 Aug — the screen beats the document.** `SKILL.md` is corrected.
>   ⚠️ **The lesson is not "a doc went stale". It is that the stale copy was the one
>   giving INSTRUCTIONS**, naming the working voice as broken and the broken one as
>   locked — so following it would have re-created the fault the rebuild existed to
>   escape. Three homes for one id, and nothing compared them.
>
> **EP31's first render came back in an AMERICAN ACCENT from an untouched template, and
> HeyGen support could not fix it.** That is what started the 19 Aug rebuild. **The old
> renders were DELETED**, so any `heygen_video_id` from before that point points at
> nothing.
>
> ⚠️ **THE AVATAR ID IS NOT RECORDED HERE** because nobody has given it and the template
> list does not expose it. It is baked into the template, so no episode needs it — but
> **do not invent one**, and add it here the day somebody reads it off HeyGen.
> ⚠️ **The EP04 rule stands and is now proved twice:** never ElevenLabs, voice engine
> **Auto**, accent **English (Australia)**. The US accent came back anyway on an
> UNTOUCHED template, which is why the template itself had to be rebuilt.
> ❓ **The host is still written as "Gordon" in every script.** The face and voice have
> changed; whether the NAME changes is Jodie's call and nothing here assumes it has.

- **What it locks (so nobody re-picks it):** the **avatar**, the approved **Australian
  voice** (never ElevenLabs), and the **backdrop**. Only the **script text**
  changes per episode.
- **▶ TEMPLATE ID:** `ac627c3ae2e9443bbbdf520215dbead8` (rebuilt 20 Aug 2026).
  *(Superseded: `d98c9195befa419290ef955f6149e861` "PP Template v3 Peter" 19 Aug 2026;
  `5f4b2ed0e33a4351ae4debfbf804d7f2` "PP Videos template v2" 2026-07-23.)* — once the template is built, give the
  `template_id` to Claude. (Or just say *"list my HeyGen templates"* and Claude will
  fetch it **for free** via `GET /v3/templates` — a metadata call, no render, no cost.)
  Claude then records it in the `heygen-api-setup` memory + the `pp-episode-production`
  skill so every future episode reuses it automatically.
- **Works on both paths:** web app (free plan credits — open the template, paste,
  Generate) and API (`POST /v3/templates/{template_id}` with the script as a text
  variable, `caption:false`; avatar/voice/background inherited).

## 🔴 THE TWO-WAY TEMPLATES (dialogue episodes — Barry Meadow / Brian Blackwell)

**THIS TABLE IS THE ONE HOME FOR THESE IDS**, exactly as the table above is for the
single-presenter template. They are deliberately NOT repeated in
`PP Videos/docs/PP-TWO-WAY-BUILD-SPEC.md` or `PP-TWO-WAY-FORMAT.md` — those name a
template by ROLE (`"barry"`, `"brian"`) and resolve it here. A value with two homes
drifts (fault #2), and this document already carries that exact scar: a July id was still
being quoted as current on 20 Aug, two rebuilds later, six lines below the line that had
already superseded it.

> | role | who | **template id (LIVE)** |
> |---|---|---|
> | **`barry`** | **Steve, reading Barry Meadow** — US handicapper, the guest. Study
> backdrop. **NAMED "Barry test 2 small " IN HEYGEN** *(yes, with a trailing space)*.
> Voice: **Narrative Nolan**. | **`dcd1c7f3b97e4ea08e92df2a3aa60101`** |
> | **`brian`** | **Gordon, reading Brian Blackwell** — PPM editor, the host.
> Commentary-box backdrop. **NAMED "Gordon two-way small" IN HEYGEN.** Voice:
> **Patrick**. 🔴 **A DUPLICATE — the standing single-presenter template is untouched
> and must stay that way.** | **`35adeb00df40420aa02aedaa636aa08b`** |
>
> **Read off the HeyGen API 18 Sep 2026.** Read the date before trusting either id.

### 🔴 THE AVATAR LAYER IS SMALLER IN THESE TEMPLATES, AND THAT IS THE POINT

Jodie's note was *"further back, more space, heads the same size"* — and **it cannot be
done in the composite.** Zooming out only reveals what the camera saw, and the old
renders had no room left to show. So the framing moved INTO the templates: the avatar
layer is shrunk, head about a quarter of the canvas, top of head ~¼ down and chin ~½
down. **The composite's job is to place a head, never to resize one.**

📐 **MEASURED ON THE FIRST RENDERS (18 Sep, crown→chin at 1080p): Steve 368px (34.1% of
frame), Gordon 295px (27.3%) — Steve's head is 1.25× Gordon's.** Eye lines 430 and 402,
28px apart. ⚠️ **They were eyeballed to match and they do not.** Roughly two-thirds of
the gap is Steve's BEARD, which extends his visible chin: to the chin point rather than
the beard he is ~323px, still ~10% larger. **A number worth having before the two-box
is judged by eye — and the fix, if one is wanted, is in the TEMPLATE, not the composite.**

> ### ⛔ SUPERSEDED FOR THE TWO-WAY (still valid for their own uses)
> `4aec07329a8244efb5da4c77a10f7db1` "Barry test 1" and
> `2eea7985fa3d4821856bf6f54f89c892` "Kohler template" were the two-way pair from
> 30 Aug to 16 Sep 2026. **They are the OLD framing. Do not render a two-way on them.**

- **Each template bakes in its own avatar, voice AND backdrop**, so a dialogue episode
  needs no per-episode background handling. Barry's study and Brian's commentary box are
  uploaded into their templates **once**, never referenced per episode.
- ⚠️ **THE TWO VOICES ARE DELIBERATELY DIFFERENT. Barry is AMERICAN.** He is a real US
  author, the article's own standfirst names him as the US expert, and Brian's turns
  ("in some parts of Australia punters have flexi betting…") only make sense against
  that contrast. 🔴 **This is the one place in the studio where an American accent is
  CORRECT.** Do not "fix" Barry toward Australian — the rule guarding Gordon's voice
  does not apply to this template.
- ✅ **THE LOOK IS CONFIRMED CORRECT (30 Aug 2026) — DO NOT GO CHASING IT.** Barry's
  avatar "Barry Meadow PP" carries THREE LOOKS, and the template is on the right one: the
  reframed seated medium shot, mid-chest up with air above the head, squared to the lens,
  in the study. Verified by looking at the template's own preview in the browser pane.
  🔴 THE LOOK IS *NAMED* "Jamie PP in a suit", which is inherited from the source
  avatar and describes nothing. It was briefly reported as the WRONG look on the strength
  of that name alone — a label read as if it were a description, which is fault #1a in
  miniature. **Judge a look by its picture, never by its name.**
- ✅ **THE VOICE IS SETTLED — "Narrative Nolan", voice id
  `958ae81fd0e642f19b8d422293b13033`, on the `barry` template (16 Sep 2026, Jodie
  changed it herself).** Jodie's ear on the pair-test: *"His voice sounds fine."*
  🔴 **THIS IS THE LIVE ID. The two it replaces are recorded so nobody reinstates one:**
  *"William Prescott" `24ec3736b0ef4c67a1c635794629679e` sat on the template briefly on
  16 Sep and was replaced before the first render; "Jamie PP - Voice 1" was the
  30 Aug–16 Sep value and was never a deliberate American voice for a US handicapper.*
  Format doc §8's two rules — mild not regional, dry never salesy — remain the test for
  any future change.
- **Barry never speaks the standing furniture** — no midroll, no e-book CTA, no outro,
  no sign-off. He is an outside author with no stake in this channel.
  See `PP-TWO-WAY-FORMAT.md` §11.

### 📁 WHERE THE TWO-WAY RENDERS LIVE IN HEYGEN

**Folder: "Two person episodes"** (Jodie created it 16 Sep 2026). Every two-way render
goes there — look there, not in My Projects.

### ✅ SSML IS PROVEN ON BOTH VOICES, IN REAL SCRIPT RENDERS (16 Sep 2026)

The 30 Aug proof was a one-line test on one voice. This is the whole thing:
`PP-EP49-BM-pairtest` (Steve / Narrative Nolan, 2m 36s per HeyGen, 42 credits) and
`PP-EP49-BB-pairtestv2` (Gordon / Patrick, 46 credits). **Jodie, by ear: *"they just
pause and don't announce their breaks."*** So both full EP49 scripts can be pasted
exactly as `twoway_split.py` writes them, `<break time="4s"/>` and all.

📐 **MEASURED FROM THE RENDERS (17 Sep, Claude Code):** the delivered gaps are
**4.170s and 3.564s** on Steve, **4.082s and 3.977s** on Gordon — asked 4.000s, mean
3.95s, worst case 0.44s short. ⚠️ **THAT WORST CASE COSTS AN IDLE CLIP.** After the
0.15s handles either side, a 4s pause banks 3.70s of listening footage against a 3.5s
floor — **0.2s of margin** — and Steve's 3.564s gap fell straight through it, so only
3 of the 4 pauses became idle clips. **Asking for 5s instead of 4s would bank every
one, at no extra cost.** Re-run this listen — and this measurement — whenever a
template's voice changes.

### 🔴 THE ROBOTIC VOICE HAS NOW STRUCK FOUR TIMES, AND ONE WAS A TWO-WAY TEST

`PP-EP49-BB-pairtest` — **Gordon's FIRST pair-test — came back ROBOTIC and was
DISCARDED**; `PP-EP49-BB-pairtestv2` replaces it and is the only one to use. That is EP44, EP46, EP46's re-render, **and BOTH of Gordon's first two-way pair-tests — `PP-EP49-BB-pairtest` and `PP-EP49-BB-pairtest-small`: FIVE instances, 18 Sep 2026.** 🔴 **Every Gordon case is the PATRICK voice; Steve's voice has never done it.** The third take, `PP-EP49-BB-pairtest-small-v2`, came back clean — and the only thing that changed was the paste fix above. The 14 Sep finding
(`PP-ATLAS.md`) is that the fault is probably **where HeyGen chops the script
internally**, not the words — which is why a Split Scene at the boundary fixes it.
🚨 **DO NOT PULL OR USE v1** (`bda0d3671539407289aa5563d9a0473f`). It is left in HeyGen
as the record.
📌 **AND IT LANDED ON A 480-WORD TEST**, so "short scripts are safe" is not something
anyone can now say. **Every render is listened to end to end before it is used.**

### The pause button — and why the two-way render wants automating

**HeyGen has NO typed pause token.** Confirmed against HeyGen's own help centre,
30 Aug 2026 (*Script Tips*): *"Click the Pause button under your scene's script box…
Each pause represents a half-second break."* Length is adjusted with + / − icons in
0.5-second steps. There is no bracket, backslash or tag syntax in the script box.

A two-way script needs a 4–5 second silence between every turn — it resets the delivery,
gives the cut a boundary the machine cannot miss, and yields the listening footage for
free. At half a second a click that is **roughly ninety clicks per script, two scripts an
episode**: drudgery for a person, nothing for a browser. **That is the specific reason
the render step is being automated in the browser pane rather than left as a human
click.** See `PP-TWO-WAY-BUILD-SPEC.md` §3.

### ✅ PAUSES GO IN THE SCRIPT TEXT AS SSML. PROVEN BY RENDER, 30 Aug 2026.

**Write `<break time="4s"/>` straight into the script.** It arrives with the paste, the
voice engine honours it, and nothing has to be clicked. Confirmed by an actual test
render on 30 Aug 2026 — not by reading a doc, and not by reasoning about the editor.

    Testing one.<break time="4s"/>Testing two.<break time="6s"/>Testing three.

⚠️ **SSML SUPPORT IS PER VOICE.** HeyGen's own guidance says "if you use SSML-compatible
voices". A result on one voice proves nothing about another, so **re-run the same short
test whenever a template's voice changes** — including Gordon's. The failure mode is
loud and unmistakable: the avatar reads the tag aloud ("break time equals four seconds").
Listen to the test; do not assume it.

📌 Punctuation also shapes pacing — commas make short breaks, full stops longer ones with
a downward inflection — but it cannot produce a measured multi-second gap. Use SSML when
the length matters.

### 🔴 THE EDITOR'S OWN PAUSE OBJECT IS A DIFFERENT THING, AND IT CANNOT BE PASTED

Worth keeping straight, because the two look alike and only one can be automated cheaply.

The script box is a **Tiptap / ProseMirror** editor, and its Pause **button** inserts an
atomic inline node — `pauseBubble`, `attrs {duration, initialized}`, default 0.5s. That
node **cannot be carried in pasted content**: its schema declares
`parseDOM: [{ tag: 'span[data-type="pauseBubble"]' }]` so it *looks* like it should
paste, and it was tested twice with the exact DOM its own `toDOM` emits, bare and inside
a block wrapper. **Both times the text landed and the pauses were stripped.**

📌 **THAT NO LONGER MATTERS, BECAUSE SSML MAKES THE BUTTON UNNECESSARY** — but the
distinction is recorded so nobody confuses "the pause object cannot be pasted" with "a
pause cannot be written into the script". The first is true; the second is false, and an
earlier version of this file said so for about twenty minutes.

✅ **THE EDITOR REPORTS ITS OWN DOCUMENT, so anything inserted can be VERIFIED rather
than assumed** — read the doc back and count. Useful whichever mechanism is in play.

📌 *For the record only:* HeyGen's text-to-speech endpoint accepts SSML, so
`<break time="4s"/>` exists on the API path. That path is closed on cost — see below.

## Why it's manual (the cost reason — don't lose this)
- **Web-app render = plan credits** (already included in the subscription → effectively free per episode).
- **API / MCP render = pay-as-you-go**, roughly **$0.05/sec ≈ ~$30 per 10-minute episode**, on top of the subscription.
- **The final presenter is identical either way** — Claude downloads the same
  **189 kbps master via the API `video_url`** regardless of how it was generated.
- So we keep the human web-app click to stay on free plan credits. Paying for the
  API only buys *hands-off convenience*, not quality.

## Exactly what Jodie clicks (the "few clicks")
When Claude says *"the presenter is ready to generate,"* Jodie:
1. Open the HeyGen web app and open the **locked episode template** (avatar, voice, and grandstand backdrop are already baked in — nothing to pick).
2. **Paste the spoken-words script** Claude provides into the template's script/text slot.
3. Confirm **Captions OFF**. ⚠️ **This one cannot be undone.** HeyGen BURNS captions into
   the picture, so a master rendered with them on is a master with words baked into every
   frame — the only fix is a re-render, which is real money and the long pole of the whole
   build. And the episode ships **its own** `.srt` (A7), so HeyGen's would be a *second*
   set of words on screen, out of step with ours. *The reason is recorded because a step
   with no reason is a step somebody helpfully skips.* **Also shown on the render card in
   the board, where the hand actually is (Bundle F).**
4. 🔴 **THE PASTE FIX — click into the pasted text, press Enter, then Backspace, and
   WAIT FOR THE VOICE PREVIEW TO PLAY.** *(Jodie's find, 16 Sep 2026.)*
   **If the preview refuses — HeyGen says the script is "too long" for a script far
   shorter than ones it previews every day — DO NOT GENERATE. That refusal predicts a
   robotic render.** Gordon went robotic twice in one evening without this step and came
   back clean the third time with it. The theory (unproven) is that pasted text carries
   invisible structure from wherever it was copied, the editor cannot measure it, and the
   synthesiser then chunks it badly — Enter+Backspace makes the editor rebuild the text
   as its own clean document. **The remedy is proven three for three; the theory is not,
   so every render is still listened to end to end.** Read with the 14 Sep chunking entry
   in `PP-ATLAS.md`. **Also on the board's render card (Bundle F).**
5. Click **Generate** and let it finish.
6. Tell Claude **"it's rendered"** (and the `video_id` if it's handy).

That's the whole human task: open the template, paste, Generate. Everything else is
Claude's. (Using the template is what makes this safe *and* short — no avatar/voice/
background to choose or get wrong.)

## What Claude does around the click
- **Before:** writes the spoken-words script, confirms the locked settings, and hands
  Jodie a short, exact checklist of what to click.
- **After:** pulls the finished master via the API `video_url` (**never** the web
  "Download" button — that re-encodes to ~123 kbps and sounds robotic; the API master
  is ~189 kbps), QCs the audio ≥180 kbps, builds the shot map, and assembles the episode.

---

## The requirement — surface + PROMPT this step in every layer
1. **Skill (`pp-episode-production`):** a clear **"⏸ HUMAN STEP — Jodie generates the
   presenter in the web app"** gate in the runbook, with the exact click list above and
   the "wait for her to confirm before continuing" instruction.
2. **Master workflow / process docs (`WHO-DOES-WHAT.md`, operating guide):** list it as a
   named human task with its trigger ("script is ready") and its hand-back ("she says
   it's rendered"). It is the one routine manual step in an otherwise automated pipeline.
3. **Any plugin / automation / cron run:** must **pause and wait** here — never attempt to
   auto-generate — *unless* the paid-API path has been deliberately switched on.
4. **The runner interface Claude builds:** when the pipeline reaches this stage, the UI
   must show Jodie a clear, unmissable prompt — the script to paste, the locked settings
   checklist, and a **"Generate in HeyGen → click here when done"** confirm button — and
   only advance once she confirms. Treat it as a first-class step in the run, not a footnote.
5. **Documentation / onboarding:** a short "human-in-the-loop steps" note so anyone running
   the process knows this click is expected and normal.

## Optional fully-automated alternative (documented for when it's wanted)
If we buy **API credits** and authorize the HeyGen **Video Agent MCP** (custom connector,
`https://mcp.heygen.com/mcp/v1/`, one-time browser OAuth), Claude can generate the presenter
**end-to-end with zero clicks** — at ~$30/episode, same final quality. This is a *toggle*:
default stays the free human-click path; flip to API only for hands-off/overnight batches
where the time saved is worth the spend.

- **Generation is template-based either way.** On the API path Claude calls
  `POST /v3/templates/{TEMPLATE_ID}` with the spoken-words script as the text variable and
  `caption:false`; the avatar, voice, and backdrop come from the template. This keeps the
  API path locked to exactly the same ingredients as the web-app path — no drift.
- Listing/inspecting the template (`GET /v3/templates`, `GET /v3/templates/{TEMPLATE_ID}`)
  is a **free metadata call** — no API render credits — so Claude can fetch the template_id
  and its variable schema even while the render pool is at 0.

### One-time setup clicks (only if enabling the API/MCP path)
- In the Claude desktop app: **Connectors → Add custom connector →** name `HeyGen`,
  URL `https://mcp.heygen.com/mcp/v1/` → **Authorize** in the browser.
- Top up the **pay-as-you-go / API** credit balance in HeyGen billing (separate from plan
  credits — this is what clears the `HTTP 402` on API generation).

## 🎬 EP49 — THE THREE RENDERS THAT ARE IN THE EPISODE

**Pulled 20 September 2026 via the API `video_url`, each verified against the server's
own byte count. Jodie's clicks, on plan credits. No API render was paid for.**

| title | who | template | voice | video id | bytes |
|---|---|---|---|---|---|
| `PP-EP49-BM-full` | Steve | `Barry test 2 small ` | Narrative Nolan | **`8302d0a862334fc6900f11a8ae3461b9`** | 65,139,579 |
| `PP-EP49-BB-full` | Gordon | `Gordon two-way small` | Patrick | **`6b6ab33ec58a484f98b1be28e07a1aea`** | 94,363,643 |
| `PP-EP49-BM-R1b-64s` | Steve, the SECOND reaction bed | `Barry test 2 small ` | — silence track — | **`1703106ccdce4aa982ffe983ce45789c`** | 8,258,669 |
| `PP-EP49-BB-retake-seg6-7` | Gordon, **segments 6-7 only** | `Gordon two-way small` | Patrick | **`c666e44f2d5649b09466fb72e44f3b87`** | 34,714,969 |

✅ **QC, measured on the files themselves:** BM **385.0s** (6:25) and BB **519.7s**
(8:40), both 1920x1080 at 25fps with 189 kbps audio, frame counts matching their
headers. **Every SSML break landed** — 4 of 4 on Steve (4.31, 6.56, 6.39, 5.78s) and
11 of 11 on Gordon (5.97s to 6.81s). Neither came back robotic.

🔴 **THE SECOND BED IS FILED AS `assets/reactions/BM-R1b.mp4`**, byte-identical
to the download. The HeyGen title is the RECEIPT; `twoway_reactions.filename()` is the
CONTRACT (`<BB|BM>-R<n>.mp4`), and a bed under its title alone is a bed the resolver
cannot see — every listen would silently fall back to R1a. Both names are kept.

⚠️ **AND A NUMBER NOBODY HAD BEFORE: `bed_wake_check` FLAGS `BM-R1a.mp4`, the
bed already in use.** Mouth motion **x2.14** after the ten-second Custom Motion window,
against a 2.0x limit, and it outran the head. The new bed **BM-R1b** is **x1.47 and
passes**. The check had never been run on R1a — it had no callers anywhere in the repo.
The mouth box was confirmed to sit on his mouth in BOTH beds before the numbers were
believed, because a guard fed the wrong input manufactures a fault that is not there.
Nothing has been changed on the strength of it; it is Jodie's to rule on.


### 🔴 THE RETAKE, AND WHAT IT SAYS ABOUT LONG PATRICK RENDERS

**Jodie listened to `PP-EP49-BB-full` and found Patrick ROBOTIC from about 4:14 to the
end of segment 7.** Measured against the render's own break map, 4:14 is **inside
segment 6** (the midroll, 244.1–265.5s) and the voice comes good at **segment 8,
415.2s** — exactly where she said it does.

⭐ **AND THIS IS THE FIRST TIME THE FAULT HAS BEEN PARTIAL.** Every previous case
— EP44, EP46, EP46's re-render, and both of Gordon's first two-way pair-tests —
was robotic END TO END. This render is clean for four minutes, robotic for two and a
half, and clean again for the last hundred seconds. **So the fault is per-CHUNK, not
per-render**, which is what the 14 Sep chunking theory predicted and nothing had shown.

⚖️ **THAT REFINES "LONG RENDERS ARE THE RISK" RATHER THAN CONFIRMING IT.** A
480-word pair-test went robotic in August, so length is not necessary. But if each
internal chunk can independently go wrong, **a longer script is more chances to lose** —
a probability, not a cause. 📌 And the fault RECOVERED at an SSML break, which
says the breaks do reset whatever goes wrong.

⚠️ **IT ALSO STARTED MID-SEGMENT, AT A SENTENCE BOUNDARY** — on *"Every
day at the moment…"*, the third sentence of the midroll. The 14 Sep finding says the
robotic sound starts at the BEGINNING of a section; this is consistent, and it locates
HeyGen's internal chunk boundary **inside a paragraph, not at our six-second break.**

**The patch:** `PP-EP49-BB-full-patched.mp4`, **536.4s**, 1920×1080, all eleven
breaks present. Segments 1–5 and 8–12 come from the original; 6–7 from the
retake. **Every cut is inside a six-second silence**, at the OUTER edge of it, so all
eleven breaks sit wholly within one render and no harvested listening pause carries a
seam. 🔴 **The PICTURE still jumps at both seams** — hands and posture
change instantly — because they are two renders of the same man. **Both originals
are kept on disk.**
