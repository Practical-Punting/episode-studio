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

- **What it locks (so nobody re-picks it):** avatar **"Floyd"**
  (`avatar_id de774dd2f3ef4a52bc31dee6fc91f118`), the approved **Australian voice**
  (never ElevenLabs), and the **grandstand backdrop**. Only the **script text**
  changes per episode.
- **▶ TEMPLATE ID:** `5f4b2ed0e33a4351ae4debfbf804d7f2`  ("PP Videos template v2", provided 2026-07-23) — once the template is built, give the
  `template_id` to Claude. (Or just say *"list my HeyGen templates"* and Claude will
  fetch it **for free** via `GET /v3/templates` — a metadata call, no render, no cost.)
  Claude then records it in the `heygen-api-setup` memory + the `pp-episode-production`
  skill so every future episode reuses it automatically.
- **Works on both paths:** web app (free plan credits — open the template, paste,
  Generate) and API (`POST /v3/templates/{template_id}` with the script as a text
  variable, `caption:false`; avatar/voice/background inherited).

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
3. Confirm **Captions OFF**.
4. Click **Generate** and let it finish.
5. Tell Claude **"it's rendered"** (and the `video_id` if it's handy).

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
