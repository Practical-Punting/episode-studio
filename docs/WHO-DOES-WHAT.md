# Practical Punting — who does what (Cowork Claude ↔ Claude Code)

Two Claudes work on every episode. This file is the contract between them.
Jodie: if either one seems confused about its lane, point it at this file.

## The split, in one line
**Cowork Claude CREATES the content. Claude Code BUILDS the artefacts.**

| Stage | Owner | Notes |
|---|---|---|
| Article → script (~22 paragraphs) | **Claude Code**, via the `pp-episode-script` skill | Written straight into a **Google Doc in the episode's Drive folder** — that Doc is the script's ONE HOME and the single source of truth. `docs/spoken-words.txt` is a derived cache the engine rebuilds from the Doc at the start of every build. **Superseded 26 Jul 2026** (was: Cowork hand-wrote it, no sign-off). |
| **Script sign-off** | **Jodie / Hugh** — the SCRIPT GATE on the board | Open the Doc from the words card, read it, edit it freely, tick **"I've read the script"**, approve the words. Nothing builds until both are done. Approving the script is a DECISION and stays human forever. |
| Motion-graphic cards (code HTML/CSS) | **Cowork** designs · **Claude Code** renders | **MORE cards per episode from EP04**; Jodie is NOT asked to approve them |
| B-roll (Higgsfield) | **Cowork** | **NEW every episode + no repeats within an episode** (cross-episode registry); Jodie is NOT asked to approve it |
| E-book cover | **Claude Code** | Standing template; **built BEFORE the video** (the end-card motion graphic needs the real cover) |
| E-book interior illustrations | **Cowork** (hybrid) | Canva pictures + code SVG diagrams; one batch → `PP-EPxx/ebook/` |
| E-book article HTML (body copy only) | **Cowork** | Paste into the standing template — see below |
| **HeyGen: generate + clean download** | **Jodie generates in the web app; Claude Code downloads via API** | **Generate MANUALLY in the web app on plan credits (near-free), captions OFF** — the API *generate* is pay-as-you-go (~$30/10-min episode), so we don't auto-generate. **🔒 But ALWAYS download the presenter from the API `video_url` (the 189 kbps master), NEVER the web "Download" button** — that button re-encodes to ~123 kbps and sounds compressed/robotic (EP04's bug, fixed 2026-07-21). API retrieval is free. QC gate: presenter track must be ≥ ~180 kbps. Timings via `build_shot_map.py`; the `scripts/heygen_generate.py` API-generate path stays available for hands-off runs only. |
| Shot map | **Claude Code** | `build_shot_map.py` |
| Card rendering → clips | **Claude Code** | `render_card.py` / `render_overlay.py` |
| Video assembly + QC + report | **Claude Code** | Two-pass; `pp-episode-production` skill |
| **E-book PDF build + QC** | **Claude Code** | `build_ebook.py`; WeasyPrint + GTK installed |
| **Thumbnail** | **Cowork** makes the Higgsfield hero · **Claude Code** composites the title — ⚠️ *this division of labour is STALE; Jodie to rule after EP11* | Hybrid; 1280×720. See `docs/PP-THUMBNAIL-TEMPLATE.md` (canonical) and `docs/PP-STANDARDS.md` §Thumbnail. **`thumbnail-standard.md` is SUPERSEDED and archived** — `docs/archive/thumbnail-standard.md`. |
| **YouTube title + description** | **Claude Code** (Jodie's ruling, 26 Jul 2026 — moved from Cowork) | Writes it to `PP-EPxx/output/PP-EPxx-youtube.txt`; **Jodie uploads**. Lead with "how to win at horse racing"; see `docs/youtube-metadata-kit.md` |
| Publishing, sending to Hugh, Mailchimp | **Jodie** | Never automated |

## What Jodie approves — and what she does NOT (locked from EP03 feedback, 2026-07-21)
Jodie's time is for the FINISHED thing, not the parts.
- **She approves ONLY the finished artefacts:** the finished video, the finished e-book, the finished thumbnail — plus the **cover hero image**.
- **She IS asked to approve the script** (changed 26 Jul 2026 — the SCRIPT GATE). It is a gate on the board, not an email: open the Doc, read it, edit it, tick "I've read the script", approve the words. The engine then re-reads the Doc and builds from exactly what she left there.
- **She is NEVER asked to approve, and the pipeline just proceeds on:** the motion-graphic cards / Higgsfield ideas, the b-roll choices, individual e-book illustrations, and any tool-plumbing check — **Higgsfield balance / credits or `models_explore`, HeyGen steps, file moves.** Handle credits and model choice silently; only surface a tool issue if it genuinely blocks the build.
- **No script email to Hugh** — the gate on the board replaced it. The article is still pre-approved; what's new is that the *script written from it* gets a human read before anything is built or rendered.

## Build order (so nothing waits on itself)
The **e-book cover is generated BEFORE the video**, because the video's end-card "free e-book" motion graphic composites the real cover. Standard order every episode: **script → cards + b-roll → e-book cover → HeyGen generate → shot map → assemble video → full e-book PDF → thumbnail → YouTube title & description.**

## The standing e-book furniture (Claude Code owns these — do not redesign)
Everything below lives in
`PP Videos/.claude/skills/pp-episode-production/assets/` and is APPROVED
(Jodie, 2026-07-20, EP02 "Killer Strategies for the Trifecta"):

- **`ebook-template.html`** — the whole shell: A4 page setup, Georgia body,
  burnt orange `#DA532C`, running footer, page numbers, header logo, cover
  slot, warranty page, marketing page. **Only the ARTICLE BODY changes per
  book.**
- **Warranty page** — identical in every book. Same text as the video's
  warranty slide. Includes the centred grey support box and the copyright /
  `sales@equest.com.au` line.
- **Marketing page** — the LAST page of every book: logo, "Thanks for
  downloading!", hero image, "Over 100,000 members can't be wrong." in burnt
  orange, the closing heading, **JOIN NOW FOR FREE**, and the site link.
  Reusable as-is; only swap the hero if Jodie approves a new one.
- **`ebook-logo-white.png`** — orange icon + charcoal wordmark, transparent
  background, for the top-right of every content page. (The dark chip
  `ebook-logo.png` is for dark/photo backgrounds, e.g. the marketing page.)
- **Live links, every book:** practicalpunting.com.au, gamblinghelponline.org.au,
  sales@equest.com.au. `build_ebook.py` fails QC if any is missing.

## What Cowork Claude hands over for an e-book
Drop into `PP-EPxx/ebook/`:
1. `cover.png` — the real magazine cover (never a mock-up).
2. Interior illustrations as `NN-name@2x.png`, made in ONE batch, print-friendly
   (white background, minimal ink, 1.5px line work, orange + charcoal only).
3. The article body as HTML using the template's class vocabulary
   (`.kicker`, `h1.section`, `h2.rule`, `.lead`, `blockquote`, `.pullquote`,
   `.byline`, `img.illus`, `div.pagebreak`) — **body only**, not a whole
   document. Claude Code drops it into the standing template.
4. Tall/portrait illustrations get `class="illus portrait"` — the template sizes
   them to ~57% column width, centered, and keeps each heading + text + figure
   **together on one page** (no orphaned headings, added EP03). Aim to place each
   figure **with its section**; the exact page number is secondary to the
   section-sits-with-its-graphic goal.

Then tell Claude Code: *"build the EP-xx e-book"*.

## Gotchas that cost us time once (don't repeat)
- The template's global `p { text-align: justify }` silently LEFT-aligns any
  centred single-line `<p>`. Centred paragraphs need their own `text-align`.
- Cover footers are baked into the PNG. To remove a credit line, use
  `scripts/fix_cover_footer.py` (splices original pixels — font matches
  exactly). It needs explicit `--keep` segment indices; guessing produces
  nonsense like "A practicalpunting.com.au". Always open the before/after PNG.
- Browser downloads land in Downloads with random or `.tmp` names. Claude Code
  audits and moves them; Jodie should never have to.
- WeasyPrint needs the Windows GTK runtime (installed 2026-07-20). If it ever
  breaks: github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer

## Where the authority sits when the two skills disagree
The **project skill** (`pp-episode-production`, in this repo) is newer on
technical specifics — music mix (loudnorm + 4% bed + sidechain ducking),
framing transitions (eased zoom moves, not dissolves), per-card compositing,
and all e-book build details. The **master skill** (`pp-episode-pipeline`,
Cowork) is authoritative on process, approval gates, and brand law
(no "tax" framing, turf-only b-roll, the no-repeat rule — NEW b-roll every
episode and none repeated within an episode — crowd diversity, warranty
wording, logo prominence).

**Superseded guidance:** the master skill's older THUMBNAIL instructions (pull an
expressive frame of Gordon; Higgsfield only for backgrounds) and any "Claude
Design" relay language are OUT OF DATE. Thumbnails now follow
`docs/thumbnail-standard.md` (hybrid: Higgsfield hero + code-composited title);
graphics follow the hybrid Canva-pictures / code-diagrams division; YouTube copy
follows `docs/youtube-metadata-kit.md`; the full flow is in
`docs/PP-COWORK-OPERATING-GUIDE.md`.
