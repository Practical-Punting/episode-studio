# Practical Punting — who does what

This file is the contract. If anyone seems confused about their lane, point them here.

## The split, in one line (RULED BY JODIE, 27 JULY 2026)
**Claude Code CREATES AND BUILDS EVERYTHING. Cowork plans, remembers, reviews and checks.
Jodie approves and publishes. Hugh is co-owner and reviewer.**

| Who | What |
|---|---|
| **Claude Code** | **Creates everything that ships**: the script, the motion cards, the b-roll, the e-book body and cover, the thumbnail and its hero, the YouTube copy. Builds, assembles, QCs. |
| **Cowork** | **Planning, memory, review and checking — and nothing else.** No episode assets. No rules. Not one line of anything that ships. |
| **Jodie** | **Approves and publishes**: the Words Gate, the Script Gate tick, the cover hero pick, the four finished artefacts, the upload. |
| **Hugh** | Co-owner and reviewer — and the person the hands-off studio is being built for. |

### Why this changed (27 July 2026)
**It matches what actually happened on EP11 rather than what this document claimed.** On that
episode Claude Code wrote the script, built all sixteen cards, generated the b-roll, wrote the
e-book body, built the thumbnail and wrote the YouTube copy — while this file still said Cowork
did most of it. **The map was describing a territory that no longer existed.**

And the sharper reason: **when two parties can both plausibly own a task, it gets done twice or
not at all.** That is exactly what the YouTube-copy incident was — a ruling that ownership had
moved, recorded in some documents and not others, so the copy was written twice and the stale
rows survived in four places. One owner per task, named here.

Jodie's words: *"These are all now jobs of cc."* And, asked whether that left Cowork any
creative work: *"Your job will be purely planning memory, review and checking."*

| Stage | Owner | Notes |
|---|---|---|
| Article → script (~22 paragraphs) | **Claude Code**, via the `pp-episode-script` skill | Written straight into a **Google Doc in the episode's Drive folder** — that Doc is the script's ONE HOME and the single source of truth. `docs/spoken-words.txt` is a derived cache the engine rebuilds from the Doc at the start of every build. **Superseded 26 Jul 2026** (was: Cowork hand-wrote it, no sign-off). |
| **Script sign-off** | **Jodie / Hugh** — the SCRIPT GATE on the board | Open the Doc from the words card, read it, edit it freely, tick **"I've read the script"**, approve the words. Nothing builds until both are done. Approving the script is a DECISION and stays human forever. |
| Motion-graphic cards (design + code HTML/CSS) | **Claude Code** | Designs AND renders them. **MORE cards per episode from EP04**; Jodie is NOT asked to approve them. Card entry = spoken cue **+3.0s** (PP-STANDARDS §Motion-graphic cards). |
| B-roll (Higgsfield) | **Claude Code** | Writes the prompts and generates them via the engine's gens batch. **NEW every episode; no repeats within an episode; no-repeat law is COMPOSITION, not subject** — check the registry first, append after. ✅ The registry **is in this repo** at `docs/broll-registry.md` (moved 28 Jul 2026; reclassified TIER 3 by Hugh — marketing material, not a trade secret). *(Was: “NOT in this repo: it is Tier 2 and lives at G:\My Drive\PP Videos\docs\broll-registry.md”.)* Jodie is NOT asked to approve it. |
| E-book cover | **Claude Code** | Standing template; **built BEFORE the video** (the end-card motion graphic needs the real cover). Jodie picks the hero from the A/B pair. |
| E-book interior figures | **Claude Code** | **The figures ARE the motion cards** — `build_figures.py` renders each card's print variant. One design, two uses, so the book can never drift from the video. |
| E-book article HTML (body copy) | **Claude Code** | Article body marked up in the standing template's class vocabulary; exactly ONE `*.html` directly in `PP-EPxx/ebook/`. |
| **HeyGen: generate + clean download** | **Jodie generates in the web app; Claude Code downloads via API** | **Generate MANUALLY in the web app on plan credits (near-free), captions OFF** — the API *generate* is pay-as-you-go (~$30/10-min episode), so we don't auto-generate. **🔒 But ALWAYS download the presenter from the API `video_url` (the 189 kbps master), NEVER the web "Download" button** — that button re-encodes to ~123 kbps and sounds compressed/robotic (EP04's bug, fixed 2026-07-21). API retrieval is free. QC gate: presenter track must be ≥ ~180 kbps. Timings via `build_shot_map.py`; the `scripts/heygen_generate.py` API-generate path stays available for hands-off runs only. |
| Shot map | **Claude Code** | `build_shot_map.py` |
| Card rendering → clips | **Claude Code** | `render_card.py` / `render_overlay.py` |
| Video assembly + QC + report | **Claude Code** | Two-pass; `pp-episode-production` skill |
| **E-book PDF build + QC** | **Claude Code** | `build_ebook.py`; WeasyPrint + GTK installed |
| **Thumbnail (hero + composite)** | **Claude Code** | Sources or generates the hero AND composites the title. 1280×720. See `docs/PP-THUMBNAIL-TEMPLATE.md` (canonical) and `docs/PP-STANDARDS.md` §Thumbnail. **Hero must never have been a thumbnail before** — check and log `docs/thumbnail-hero-registry.md`. (`thumbnail-standard.md` is SUPERSEDED and archived at `docs/archive/thumbnail-standard.md`.) |
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
`.claude/skills/pp-episode-production/assets/` **in this repo** (moved off Drive
28 Jul 2026) and is APPROVED
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

## What goes into an e-book — Claude Code builds all of it
*(Was "what Cowork hands over". Nothing is handed over now; Cowork produces no episode assets.)*

Into `PP-EPxx/ebook/`:
1. **`cover.png`** — rendered from `cover-src/cover.html`, built by copying the canonical
   `assets/ebook-cover-template.html`. Never a mock-up, never a handed-over PNG; always
   re-rendered and checked with `cover_check.py`.
2. **Figures** — `figure-N.png`, rendered by `build_figures.py` from the episode's own motion
   cards in print mode. **The figures ARE the cards.** No separate illustration batch.
3. **The article body as HTML** using the template's class vocabulary (`.kicker`, `h1.section`,
   `h2.rule`, `.lead`, `blockquote`, `.pullquote`, `.byline`, `img.illus`, `div.pagebreak`) —
   body only, dropped into the standing shell. Exactly ONE `*.html` directly in `ebook/`.
4. Tall/portrait figures get `class="illus portrait"` — ~57% column width, centred, with each
   heading + text + figure kept **together on one page** (no orphaned headings, EP03 lesson).
   Place each figure **with its section**; the exact page number is secondary.
5. **Page order** (Hugh's change): cover → body (+figures) → **marketing (second-last)** →
   **warranty (last)**.

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

## Where the authority sits (RESET 27 July 2026)
**`docs/PP-STANDARDS.md` in this repo wins. Full stop.** It declares itself canonical and every
other document defers to it. The `pp-episode-production` skill holds the *build recipes* — the
ffmpeg graphs, the music mix, per-card compositing, e-book build details — and must obey the
standards; if the two ever disagree, PP-STANDARDS wins and gets updated.

**Cowork's `pp-episode-pipeline` skill is NO LONGER authoritative on anything.** It previously
held process, approval gates and brand law. Those now live in `docs/PP-STANDARDS.md` in this
repo, because **Cowork never writes rules** (Jodie, 27 Jul 2026) and a rule that lives only
where Claude Code cannot read it is a rule waiting to go wrong — which is precisely how the
YouTube-copy ownership was corrected in one place and stayed wrong in four others.

**Superseded guidance, do not follow:** the old THUMBNAIL instructions (pull an expressive frame
of Gordon; Higgsfield only for backgrounds), any "Claude Design" relay language, and the
hybrid Canva-pictures / code-diagrams split for e-book graphics — the figures are now the motion
cards. Thumbnails follow `docs/PP-THUMBNAIL-TEMPLATE.md` and `docs/PP-STANDARDS.md` §Thumbnail
(the old thumbnail-standard document is archived at `docs/archive/thumbnail-standard.md` and is
not authoritative); YouTube copy follows `docs/youtube-metadata-kit.md`.
