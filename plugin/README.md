# pp-production — Practical Punting episode build pipeline (Claude Code plugin)

The **build side** of the PP episode pipeline, packaged for Claude Code. It bundles
the `pp-episode-production` skill plus its scripts and standing assets. It pairs with
Cowork's creative-side plugin: **Cowork creates, this plugin builds.**

## What's inside
`skills/pp-episode-production/` — the skill (SKILL.md) + `scripts/` + `assets/`:
- **Toolkit:** `assemble_episode.py` (episode.json → Pass A/B graphs), `qc_episode.py`
  (one-command QC), `align_srt.py` (WhisperX forced-align), `build_shot_map.py`,
  `build_figures.py` (e-book figures from card HTML), `broll_registry_check.py`,
  `build_ebook.py`, `render_still.py`, `render_card(s).py`, `pp_doctor.py`
  (toolchain check/install), `pp_paths.py` (binary resolver).
- **Assets:** card engine (`pp-anim.js`), logo chip, e-book/warranty/marketing/
  thumbnail templates.

## Prerequisites
Windows box with the toolchain — run once: `python skills/pp-episode-production/scripts/pp_doctor.py --install`
(ffmpeg, Python 3.12, Playwright+Chromium, WeasyPrint+GTK, pymupdf, pillow, poppler, WhisperX).

## Install
**Dev (no install):**
```
claude --plugin-dir "G:/My Drive/PP Videos/pp-production-plugin"
```
**Via marketplace:**
```
/plugin marketplace add "G:/My Drive/PP Videos/pp-production-plugin"
/plugin install pp-production@practical-punting
/reload-plugins
```
Validate: `claude plugin validate "G:/My Drive/PP Videos/pp-production-plugin"`

## The contract
Cowork writes `docs/episode.json` per episode (spec: `docs/PP-EPISODE-JSON-SPEC.md`;
build-side notes: `docs/PP-EPISODE-JSON-NOTES.md`). The assembler reads the spec
fields verbatim + an optional `build` block (build-side tuning). Worked example:
`PP-EP05/docs/episode.json` — validated to reproduce the approved EP05 v2 assembly.

## Maintenance
The bundled skill is a COPY. After editing the live skill
(`.claude/skills/pp-episode-production`), run `python pack.py` to refresh it here.
