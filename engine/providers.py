"""providers.py — the engine's external hands: real services vs mock.

The orchestrator (engine.py) never talks to tools directly; it calls a Provider.

MockProvider simulates everything (no credits, no network) — the 2a spine
acceptance ran on it. RealProvider drives the ACTUAL local toolchain (the
pp-episode-production skill's scripts: Chromium card renders, ffmpeg passes,
WeasyPrint e-book, QC). Higgsfield gens (b-roll AND the two cover heroes) go
through the Higgsfield CLI; if it's missing, every gen path falls back to an
honest flag. The HeyGen render itself stays a sacred human step — the engine
only names the project and downloads the finished master.

Spend policy (verify-before-spend): a staged asset is NEVER regenerated. The
credit estimate counts only what's actually missing, and every spend is
previewed and capped first.

Fault injection (mock only), via environment variables:
    MOCK_FAIL_STEP=<step>   that step fails EVERY attempt (shows needs_look)
    MOCK_FAIL_ONCE=<step>   that step fails its FIRST attempt (shows retry)
    MOCK_BALANCE=<n>        pretend Higgsfield balance (default 100)
    MOCK_STEP_SECS=<n>      how long each mock action takes (default 1.5)
    MOCK_BROLL_CLIPS=<n>    clips in the mock plan (default 3)
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import check_page_images                       # the general "does every <img> resolve"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- repo + skill locations (the 28 Jul 2026 move) ---------------------------
# CODE IN GITHUB, MEDIA ON DRIVE (Jodie, 28 Jul 2026). The build recipes, their
# assets and the b-roll registry are versioned here; PP_VIDEOS keeps only episode
# media, the Google Docs and .env (TIER 1, never in the repo).
REPO_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_DIR / ".claude/skills/pp-episode-production"

# --- qc_episode.py integrity gate (26 Jul 2026; git-backed from 28 Jul 2026) -
# qc_episode.py is the checker that judges every finished episode. It once lived
# on Drive outside version control, in TWO copies that had already drifted — the
# spare was missing three hard-fail rules (card word-cue anchoring, b-roll/card
# overlap, midroll visibility). If the wrong one ran, an episode would PASS while
# being judged by weaker rules, and nothing would say so.
#
# It is now in the repo, so the gate compares it against git HEAD rather than a
# checked-in duplicate — see engine/gitgate.py. Checked IMMEDIATELY BEFORE
# shelling out to it. No bypass flag, no environment variable. (Mock mode never
# executes this script — it has its own self_qc — so there is nothing to bypass.)
QC_SCRIPT = "qc_episode.py"
QC_REL = ".claude/skills/pp-episode-production/scripts/qc_episode.py"


class EngineFlag(Exception):
    """Raise to say: a HUMAN is needed. The engine flags needs_look with this
    message (plain English!) and does not retry — it isn't transient.

    `blockers` is OPTIONAL and carries the raw, machine-shaped lines a checker
    produced — card names, keys, source sentences — where a caller needs the
    faults themselves rather than the prose wrapped round them. The episode.json
    repair loop hands them straight back to the writer.

    🔴 THE TWO ARE NOT INTERCHANGEABLE AND THAT IS THE POINT. str(EngineFlag) is
    what a PERSON reads on the board and must stay plain English with no path, no
    file name and no card id (docs/PP-operator-box-rule.md). `.blockers` is for a
    machine and a run log. Different readers; the same text cannot serve both.
    """

    def __init__(self, message, blockers=()):
        super().__init__(message)
        self.blockers = list(blockers)


# --- card authoring (1d, 28 Jul 2026) ----------------------------------------
# The engine used to render cards it never authored, so an episode with no card
# pages halted with "Zero card HTML pages existed — stage them, then clear this
# flag": a message that asks a browser operator to write HTML. That halt is gone.
# Missing pages are now AUTHORED from the template library; missing DATA still
# halts, which is correct — a halt over an unwritten figure is a halt a human
# should clear.
#
# Never overwrite. author_cards.py refuses to touch a page that does not carry
# its generated marker, and the furniture below is copied only when absent, so a
# hand-fixed page survives every subsequent run.
CARD_DEPS = (                       # what an authored page needs beside it
    ("assets/pp-anim.js", "pp-anim.js"),
    ("assets/assets/logo.png", "assets/logo.png"),
)
STANDING_CARDS = (                  # design §4 Layer 3 — copied, never authored
    ("assets/warranty-slide.html", "warranty-slide.html"),
    ("assets/end-card-template.html", "end-card-template.html"),
    # THE MIDROLL CHIP, ADDED 3 AUG 2026 — the third standing asset with no stager.
    # It is byte-identical every episode, exactly like the two above, and nothing
    # rendered it: EP14 halted at pass B on `build.midroll.clip names
    # 'midroll-lowerthird.mp4' but that file is not in overlay/clips`. Staged here,
    # render_cards_batch picks it up with everything else in overlay/export — so this
    # needs no new render step, only the page put where the batch can see it.
    # The title-card hero, the thumbnail hero and this were all found by breaking.
    ("assets/midroll-lowerthird.html", "midroll-lowerthird.html"),
)


def assert_standing_assets() -> str:
    """EVERY standing asset must EXIST, checked at the head of the build.

    🔴 THE HALF OF BUNDLE A THAT DID NOT LAND, AND IT IS FAULT #1 IN CLAUDE.md:
    assert the artefact, not the thing that reports on it. `stage_card_furniture`
    skipped a missing SOURCE silently (`if dst.exists() or not src.is_file(): continue`)
    and the episode carried on — so a standing asset that was not there was found at
    PASS B, hundreds of credits and an hour of ffmpeg later. That is exactly how EP14
    lost its midroll chip.

    THE TITLE-CARD HERO, THE THUMBNAIL HERO AND THE MIDROLL CHIP WERE EACH FOUND BY
    BREAKING, ON THREE SEPARATE EPISODES. They are identical on every episode and their
    absence is knowable before a single credit is spent, so it is checked here, once,
    up front — not discovered one at a time in anger.

    Raises EngineFlag naming every missing file. Returns a one-line all-clear.
    """
    missing = []
    for src_rel, _dst_rel in (*CARD_DEPS, *STANDING_CARDS):
        if not (SKILL_DIR / src_rel).is_file():
            missing.append(str(SKILL_DIR / src_rel))
    if missing:
        raise EngineFlag(
            "A STANDING ASSET IS MISSING FROM THE SKILL, so this build would fail later "
            "and further along than it needs to. These files are identical on every "
            "episode and are copied, never authored:\n"
            + "\n".join(f"      {m}" for m in missing)
            + "\n    Restore them from git — the skill lives in the repo — then clear "
              "this flag. Checked here rather than at Pass B because that is where the "
              "midroll chip was found on EP14, after the whole render had been paid for.")
    return f"standing assets: {len(CARD_DEPS) + len(STANDING_CARDS)} present"


def assert_page_images(export: Path) -> str:
    """EVERY IMAGE EVERY PAGE ASKS FOR MUST EXIST — checked before anything renders.

    The complement of assert_standing_assets(): that one knows a LIST of files and
    checks they are present; this one knows NOTHING and asks each page what it needs.
    A list only ever covers what somebody thought of, which is why EP15's end card got
    through — `ebook-cover.png` was on no list.

    *EP15, 4 Aug 2026:* a correct quarantine removed nine artefacts composed from a
    rejected cover hero, two were never put back, and the end card rendered a grey
    rectangle carrying the browser's ALT TEXT — "The Practical Punting Guide — Killer
    Strategies for the Trifecta", not even that episode's title. The e-book's cover
    page came out blank white from the same hole. `card_check` measures collisions,
    not whether an <img> resolves; `self_qc` returned an honest PASS and reported the
    end card "visible (luma 33)", **because a grey box has a luma.**
    """
    broken = check_page_images.scan_dir(export)
    if broken:
        lines = []
        for page, bad in broken.items():
            for ref, _resolved in bad:
                lines.append(f"      {page.name}  wants  {ref}")
        raise EngineFlag(
            f"{len(lines)} image(s) that pages need are not in the export folder:\n"
            + "\n".join(lines)
            + "\n    A page that cannot find its image does not fail — it draws a grey "
              "box with the image's description written across it, and every later "
              "check still passes because the box has a size and a brightness. Put the "
              "files back, then clear this flag. Retrying without them will not help.")
    n = len(list(export.glob("*.html")))
    return f"page images: {n} page(s), every image they reference is present"


def stage_card_furniture(export: Path) -> list[str]:
    """Copy the standing pages and the assets an authored card needs.

    Returns what it added. Existing files are left exactly as they are — this is
    the same find-or-build policy the rest of RealProvider uses.

    A missing SOURCE is still skipped here, but it can no longer be a surprise:
    assert_standing_assets() has already halted the build if one is absent.
    """
    added = []
    for src_rel, dst_rel in (*CARD_DEPS, *STANDING_CARDS):
        src, dst = SKILL_DIR / src_rel, export / dst_rel
        if dst.exists() or not src.is_file():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        added.append(dst_rel)
    return added


def author_missing_cover(ep_dir: Path) -> str:
    """Author ebook/cover-src/cover.html when it does not exist yet.

    Same guarantees as the cards: a hand-authored page (no generated marker) is
    never touched, nothing is invented, and a DATA problem halts naming the field.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/author_cover.py"),
         str(ep_dir / "docs/episode.json"), str(ep_dir / "ebook/cover-src")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if r.returncode:
        raise EngineFlag(
            "The e-book cover could not be authored from episode.json. This is a DATA "
            "problem, not a missing-file problem — fix the field it names in "
            f"docs/episode.json, then clear this flag.\n{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def cover_canvas(page: Path) -> tuple[int, int]:
    """THE cover canvas, read from the page itself — one place, one number.

    The page used to be built 1588x2238 while render_ebook_cover() rendered it
    1600x2263, so every cover shipped with a 12px white gutter down the right
    edge and 25px along the bottom where the photo should have bled off. EP11 and
    EP12 shipped that way and are NOT being changed — they are published. What
    stops it recurring is that there is no longer a second number to disagree
    with the first: the template declares the canvas, author_cover.py writes it
    into the page, and this reads it back.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/author_cover.py"),
         "--canvas", str(page)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if r.returncode:
        raise EngineFlag(
            f"The cover page does not declare its canvas, so there is no safe size to "
            f"render it at.\n{(r.stderr or r.stdout).strip()[-500:]}")
    w, h = r.stdout.split()
    return int(w), int(h)


def author_missing_thumbnail(ep_dir: Path) -> str:
    """Author thumbnail/<ep>-thumbnail.html when it does not exist yet."""
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/author_thumbnail.py"),
         str(ep_dir / "docs/episode.json"), str(ep_dir / "thumbnail")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if r.returncode:
        raise EngineFlag(
            "The thumbnail could not be authored from episode.json. This is a DATA "
            "problem, not a missing-file problem — fix the field it names in "
            f"docs/episode.json, then clear this flag.\n{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def thumbnail_placement_review(ep_dir: Path, png: Path):
    """Raise the ONE clearable flag this step is meant to raise.

    Placement is the craft: the template's own header says VIEW the hero first,
    then decide. The build does NOT halt waiting for someone to type coordinates
    into episode.json — that would be a halt a browser operator cannot clear, and
    driving that number down is the whole point. It renders at the placement EP11
    and EP12 both settled on and asks a human to LOOK at the picture.

    Raised mid-build on purpose. An episode cannot currently go backwards, so a
    bad crop found at the four approvals is expensive; found here, while the
    engine still owns the episode, it is cheap.

    Flags once. The marker records that a human has seen it, so clearing the flag
    lets the step through instead of re-raising it forever.
    """
    seen = ep_dir / "thumbnail/.placement-reviewed"
    if seen.exists():
        return
    seen.parent.mkdir(parents=True, exist_ok=True)
    seen.write_text("a human has looked at the thumbnail placement\n", encoding="utf-8")
    raise EngineFlag(
        f"Have a look at the thumbnail: {png}\n"
        "It is built at the standard placement (text upper-left over the scrim), which "
        "is what EP11 and EP12 both used. What needs your eye is the HERO CROP — whether "
        "the horses are framed well and every line of text is clear of them.\n"
        "Happy? Clear this flag and the build carries on. Not happy? Say so and the crop "
        "is one value (thumbnail.hero_focus, e.g. \"center 62%\") — EP12 needed 62% "
        "because its field sits low in the frame.")


HEAD_BREATH = 0.4          # silence left before the first word, in seconds
LEAD_SANITY = 20.0         # a lead-in longer than this is not a lead-in


def trim_master_lead_in(master: Path) -> str:
    """Cut the HeyGen master's silent head at INGEST, leaving HEAD_BREATH of air.

    THE DEFECT THIS CLOSES. Avatar IV hands back a master that idles before it speaks
    — MEASURED 6.35s on EP11, 6.36s on EP12, 6.39s on EP13. The assembly then ADDS
    title_head (7.0s) on top: passA pads the video by cloning frame 0, passB delays the
    audio to match. Nothing trimmed the head, so the first word landed at 13.4s and
    Gordon sat motionless for six and a half seconds. EP11 and EP12 are PUBLISHED like
    that. Jodie, watching EP13: "host should start talking about 7 seconds but he sits
    there mute until about 12 or 13. It is weird."

    THE BITTER PART, worth remembering: the number was already being measured.
    build_shot_map.py computes SPEECH_START from silencedetect and the camera push was
    scheduled off it. We knew, used it for framing, and never trimmed on it.

    IT IS MEASURED PER EPISODE, NEVER HARDCODED. The three known values differ by tens
    of milliseconds and a fourth will differ again. A constant here would be the same
    class of bug as the hardcoded limits in DESIGN §16.19 — right until the day it is
    silently wrong.

    Doing it at INGEST rather than at assembly is the whole point: every downstream
    timing — the shot map, every card lead, the b-roll offsets, the midroll, the end
    sequence — is derived FROM the master, so trimming here makes all of them correct
    by construction instead of needing a matching offset applied in six places.
    """
    out = subprocess.run(
        ["ffmpeg", "-t", "40", "-i", str(master),
         "-af", "silencedetect=n=-38dB:d=0.35", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    if not (starts and ends and starts[0] < 0.5):
        return "master lead-in: none to trim (speech starts immediately)"
    lead = ends[0]
    if lead > LEAD_SANITY:
        raise EngineFlag(
            f"The presenter master appears to be silent for its first {lead:.1f}s. That is "
            f"too long to be an avatar's lead-in, so this is not trimmed automatically — it "
            f"is more likely the wrong file, a failed render, or audio that did not attach. "
            f"Check the master, then clear this flag.")
    cut = lead - HEAD_BREATH
    if cut <= 0.05:
        return f"master lead-in: {lead:.2f}s, already within {HEAD_BREATH}s — left alone"
    tmp = master.with_suffix(".trimmed.mp4")
    keep = master.with_name(master.stem + "-untrimmed.mp4")
    # THE VIDEO IS RE-ENCODED, AND IT HAS TO BE. HeyGen's masters carry a keyframe
    # every 10s (measured on EP13: 0, 10, 20 …), and a stream copy can only cut ON a
    # keyframe — so `-c copy -ss 5.99` silently snaps back to 0 and trims NOTHING. It
    # does not fail; it hands back a file the same length as the one you gave it, which
    # is exactly the kind of quiet no-op that shipped the mute opening in the first
    # place. CRF 15 on a talking head is visually transparent, and THE AUDIO IS COPIED
    # UNTOUCHED so the locked ~189 kbps master survives byte-for-byte.
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{cut:.3f}",
         "-i", str(master), "-c:v", "libx264", "-crf", "15", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not tmp.is_file():
        raise EngineFlag(
            f"Could not trim the presenter master's {lead:.2f}s silent head.\n"
            f"{(r.stderr or '').strip()[-600:]}")
    if not keep.exists():                       # keep the original exactly once
        shutil.copyfile(master, keep)
    tmp.replace(master)
    # PROVE THE CUT LANDED. The stream-copy version of this returned success and changed
    # nothing; a trim that reports what it INTENDED rather than what it DID is worthless.
    after = subprocess.run(
        ["ffmpeg", "-t", "40", "-i", str(master),
         "-af", "silencedetect=n=-38dB:d=0.35", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    s2 = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", after)]
    e2 = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", after)]
    now = e2[0] if (s2 and e2 and s2[0] < 0.5) else 0.0
    if now > HEAD_BREATH + 0.35:
        raise EngineFlag(
            f"The presenter master was trimmed by {cut:.2f}s but still starts with "
            f"{now:.2f}s of silence — the cut did not land where it was asked to. The "
            f"untrimmed original is beside it as {keep.name}. Do not assemble on this.")
    return (f"master lead-in: trimmed {cut:.2f}s (was {lead:.2f}s silent, now {now:.2f}s — "
            f"verified after the cut); original kept as {keep.name}")


def derive_timings(ep_dir: Path) -> str:
    """Card leads, the midroll anchor and every overlap check — derived, not guessed.

    Runs with --write, so build.leads and build.midroll.at come from the SRT rather
    than from whatever was last typed into episode.json. It refuses to write if any
    check fails, and that refusal is a HALT here: a build that carries on with stale
    leads produces exactly what EP13 produced — cards ahead of the words, with every
    instrument reporting them on-cue.

    IT MUST RUN AFTER align_to_script. The tool prefers renders/aligned.srt and falls
    back to the constructed SRT with a warning; in a normal build that fallback must
    never be taken, so the absence of aligned.srt is treated as a halt, not a shrug.
    """
    aligned = ep_dir / "renders/aligned.srt"
    if not aligned.is_file():
        raise EngineFlag(
            "renders/aligned.srt is missing, so card timings would be derived from the "
            "CONSTRUCTED SRT — interpolated from spoken-words.txt, measured at a mean "
            "5.15s error and a worst of 12.32s. That is what put nine of EP13's cards "
            "ahead of their spoken cue. align_to_script runs at ingest, right after the "
            "master is trimmed; run it, then clear this flag.")
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/derive_card_timings.py"),
         str(ep_dir), "--write"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode:
        raise EngineFlag(
            "The card timings could not be derived, so nothing was written and the "
            "existing leads are stale. Every problem below is a DECISION — a card that "
            "cannot take its window, an overlap, a cue that is not in the SRT — and the "
            "tool refuses to guess at any of them.\n"
            + "\n".join(l for l in out.splitlines() if l.strip().startswith("!!"))[:900])
    tail = [l for l in out.splitlines() if "leads" in l or "midroll.at" in l]
    return "card timings derived from the aligned SRT — " + ("; ".join(tail)[:240] or "written")


def stage_thumbnail_hero(ep_dir: Path) -> str:
    """Copy the PICKED cover hero into thumbnail/hero.png. Never overwrite.

    The thumbnail hero IS the picked cover hero (Jodie, 28 Jul 2026), and the cover
    gate has already written it to ebook/cover-src/hero.png. Staging it is a file
    copy — a chore, and automation eats chores. It halted EP11, EP12 and EP13 and a
    human did it by hand each time, because a browser operator cannot copy a file.

    NEVER OVERWRITES. A thumbnail hero already on disk may have been placed
    deliberately — a different crop, a hand-picked frame — and silently replacing it
    at build time would be the engine overruling a human. If it is there, it wins.
    """
    dst = ep_dir / "thumbnail/hero.png"
    if dst.is_file():
        return f"thumbnail hero already staged ({dst.name}) — left exactly as it is"
    src = ep_dir / "ebook/cover-src/hero.png"
    if not src.is_file():
        return ("thumbnail hero NOT staged: there is no picked cover hero at "
                "ebook/cover-src/hero.png to copy from")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return f"thumbnail hero staged from the picked cover hero ({src.name} -> {dst.name})"


def stage_title_hero(ep_dir: Path) -> str:
    """Copy the PICKED cover hero into overlay/export/title-hero.png. Never overwrite.

    Same shape as stage_thumbnail_hero, and for the same reason: a browser operator
    cannot copy a file, so the engine does the chore rather than raising a flag about
    it.

    WHICH HERO. EP11 and EP12 deliberately used the UNUSED hero here, so the title
    card and the e-book cover were not the same photograph. EP13 could not — its
    hero B shows horses on both sides of the running rail and is rejected under the
    §B-roll hard-fail list — and Jodie's 28 Jul ruling settled the general case on
    the PICKED hero. So the picked one is the default, and an episode that wants the
    spare puts its own file here: this never overwrites what it finds.
    """
    dst = ep_dir / "overlay/export/title-hero.png"
    if dst.is_file():
        return f"title hero already staged ({dst.name}) — left exactly as it is"
    src = ep_dir / "ebook/cover-src/hero.png"
    if not src.is_file():
        return ("title hero NOT staged: there is no picked cover hero at "
                "ebook/cover-src/hero.png to copy from")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return f"title hero staged from the picked cover hero ({src.name} -> {dst.name})"


def author_missing_title(ep_dir: Path) -> str:
    """Author overlay/export/<ep>-title.html when it does not exist yet.

    A1. The title card halted EP11, EP12 and EP13 with `Card TITLE has no clip in
    overlay/clips` — a message that asks a browser operator to write and place an
    HTML page. It fires on every episode and Hugh cannot clear it. It is now
    authored from episode.json, and only a DATA problem halts.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/author_title_card.py"),
         str(ep_dir / "docs/episode.json"), str(ep_dir / "overlay/export")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode:
        raise EngineFlag(
            "The title card could not be authored from episode.json. This is a DATA "
            "problem, not a missing-file problem — fix the field it names in "
            f"docs/episode.json, then clear this flag.\n{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def title_placement_review(ep_dir: Path, png: Path, url: str | None = None):
    """The ONE clearable flag the title card is meant to raise.

    Everything else on the card is substituted from approved fields and the type
    size is measured. `object-position` is the single genuinely per-image value —
    where the hero sits in the 16:9 window — and it cannot be chosen without
    looking at the picture. So the card is authored at the default, RENDERED, and a
    human is asked to look at a PNG rather than to type a coordinate blind.

    Flags once. The marker records that a human has seen it, so clearing the flag
    lets the step through instead of re-raising it forever.

    ⚠️ `url` IS WHAT MAKES THIS FLAG CLEARABLE BY THE PERSON IT IS FOR (3 Aug 2026).
    Until now the message carried a Windows path — `G:\\My Drive\\…\\title-preview.png`
    — and Hugh has no Windows machine with G: mounted. So the one flag in the whole
    build that was designed to be answered from a browser could only be answered by
    someone sitting at this machine. The PNG is now published to the same public
    bucket the cover A/B choices already use, and the board renders it.
    """
    seen = ep_dir / "overlay/export/.title-placement-reviewed"
    if seen.exists():
        return
    seen.parent.mkdir(parents=True, exist_ok=True)
    seen.write_text("a human has looked at the title card placement\n", encoding="utf-8")
    where = url or str(png)
    raise EngineFlag(
        f"Have a look at the title card: {where}\n"
        "The words are already settled — the headline, the part line and the byline "
        "are the approved packaging, and the type size is measured, not chosen. What "
        "needs your eye is the HERO CROP: whether the horses are framed well in the "
        "16:9 window and every line of text is clear of them.\n"
        "Happy? Clear this flag and the build carries on. Not happy? It is one value "
        'in docs/episode.json — "title_card": {"hero_focus": "center 62%"} — which is '
        "exactly what EP12 needed, because its field sits low in the frame. Say so and "
        "it is one edit and a re-render.")


def title_preview(ep_dir: Path, clip: Path) -> Path:
    """A still of the title card, grabbed from THE CLIP THAT WILL SHIP.

    Not a re-render of the page. Everything on this card animates in over ~2.35s,
    so a screenshot of the page at load shows a half-built card with the byline
    still at opacity 0 — and re-rendering would in any case be a second opinion
    about pixels the video does not use. The frame comes from the rendered clip,
    at the end, where everything has landed.
    """
    out = ep_dir / "overlay/export/title-preview.png"
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(clip)],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    try:
        at = max(0.0, float(dur) - 0.2)
    except ValueError:
        at = 3.0
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", f"{at:.2f}", "-i", str(clip), "-frames:v", "1", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not out.is_file():
        raise EngineFlag(
            f"The title card rendered to {clip.name} but a preview frame could not be "
            f"taken from it, so there is nothing to show you. Look at the clip itself, "
            f"then clear this flag.")
    return out


def check_youtube_title(ep_dir: Path, copy_txt: Path) -> str:
    """The gate on the one string a viewer sees first (A6).

    The YouTube title used to be composed at ~86% — long after `title_approved` was
    already true — so it had NO gate at all. It is now DERIVED from
    `packaging.byline`, which is approved at the Words Gate on turn 1, and this
    checks the file a human actually pastes from: one decided title, on line 1, in
    the house form, appearing exactly once.

    EP13 is why. Its copy file offered a recommendation and two alternatives, none
    of which was the title Jodie wanted; she composed her own and nothing wrote her
    decision back to episode.json.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/youtube_title.py"), "--check",
         str(ep_dir / "docs/episode.json"), str(copy_txt)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if r.returncode:
        raise EngineFlag(
            "The YouTube copy does not carry ONE decided title. The title is derived "
            "from packaging.byline — approved at the Words Gate — so it is not a "
            "choice to be offered here: a file that asks a question is a halt wearing "
            "a text file's clothes.\n"
            f"{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def _shipping_srt(ep_dir: Path):
    """Which SRT goes out beside the video — (path, one line saying which and why).

    aligned.srt carries timings measured from the audio; generated.srt is
    interpolated from spoken-words.txt and was measured at a mean 5.15s error,
    worst 12.32s. The viewer's captions get the good one, and falling back is
    LOUD — a caption track silently a dozen seconds out is not a small thing.
    """
    aligned = ep_dir / "renders/aligned.srt"
    built = ep_dir / "renders/generated.srt"
    if aligned.is_file():
        return aligned, f"{aligned.name} (timings measured from the audio)"
    if built.is_file():
        return built, ("!! renders/aligned.srt is MISSING, so the shipped captions come "
                       "from the CONSTRUCTED SRT — interpolated, measured at a mean 5.15s "
                       "error and a worst of 12.32s. Run align_to_script and re-assemble "
                       "before these captions go anywhere near a viewer.")
    return None, "!! no SRT found — the video ships with NO captions"


def align_to_script(ep_dir: Path) -> str:
    """Write renders/aligned.srt — OUR words, the AUDIO's timings — at ingest.

    A PROMOTION, not a rewrite: this ran as a scratchpad tool on the night EP13's
    timing fault was found, and is now standing so no episode can be built from the
    constructed SRT by default. It verifies itself after writing and raises rather
    than leaving a half-good timing file where everything downstream would trust it.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/align_to_script.py"), str(ep_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    if r.returncode:
        raise EngineFlag(
            "Could not align the script to the master's audio, so renders/aligned.srt was "
            "NOT written. Everything after this — card entries, the camera moves, the "
            "midroll anchor, b-roll placement — would otherwise fall back to timings "
            "INTERPOLATED from the script rather than measured from the audio, which is "
            "what put eleven of EP13's cards ahead of the words.\n"
            f"{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def render_ebook_figures(ep_dir: Path) -> str:
    """Render the e-book figures from the CARD pages — one design, two uses.

    Nothing in the engine ran build_figures.py before this. EP12's twelve figures
    were produced by hand, which is the same shape of gap as the pages the cards
    slice fixed: the engine consumed an artifact it never made.

    Safe to run here, in ASSEMBLING: the figures come from `overlay/export`, which
    `cards_render` filled back in BUILDING. Nothing moves in the locked order.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/build_figures.py"),
         str(ep_dir / "docs/episode.json"), str(ep_dir / "overlay/export"),
         str(ep_dir / "ebook")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode:
        raise EngineFlag(
            "The e-book figures could not be rendered from the card pages. A figure "
            "maps to a card (episode.json -> figures[]), so this is either a mapping "
            "that names a card with no page or a card page that will not render — "
            "both name themselves below. A book with a hole in it is not shippable, "
            f"which is why this stops here.\n{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def author_missing_ebook(ep_dir: Path) -> str:
    """Author the e-book source page, and RUN THE FIDELITY GATE.

    Two jobs in one call, on purpose. The shell, the layout and the figures are
    templated; the article BODY is editorial and is written at script time. What
    replaces the human read of that body is a machine check that hard-fails on any
    departure from the source article beyond a declared list — see the long note at
    the top of author_ebook.py for Jodie's reasoning, and §0a for why it matters
    that "firstup" and lower-case "joie Denise" survive to print.

    The gate runs on EVERY pass, including passes where nothing is written, because
    it is a gate and not an authoring step.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/author_ebook.py"),
         str(ep_dir / "docs/episode.json"), str(ep_dir / "ebook")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if r.returncode:
        raise EngineFlag(
            "The e-book could not be built from episode.json and the article body. "
            "This is a DATA problem, not a missing-file problem — the message below "
            "names either the field to fix or the exact word where the body departs "
            f"from the source article.\n{(r.stderr or r.stdout).strip()[-1400:]}")
    return (r.stdout or "").strip()


def _ebook_vocabulary_note() -> str:
    """The class vocabulary, ASKED OF THE CHECKER THAT ENFORCES IT.

    🔴 DERIVED, NOT RESTATED, AND THE FIRST LIVE RUN IS WHY. The brief pointed at
    PP-STANDARDS §E-book and said "use the class vocabulary". The writer produced
    `<p class="kicker">` — the right class on the WRONG ELEMENT — and the fidelity
    gate refused the whole body after 483s and $2.97. Pointing at a document that
    names the classes does not say which element each one attaches to.

    Restating them here by hand would be fault #2 with extra steps: two lists,
    one edit reaching one of them. So it imports author_ebook's own sets. The day
    somebody adds a class, this brief gains it in the same commit.
    """
    try:
        sys.path.insert(0, str(SKILL_DIR / "scripts"))
        import author_ebook as ae
        p = ", ".join(f'<p class="{k}">' for k in ae.P_CLASSES if k)
        div = ", ".join(f'<div class="{k}">' for k in ae.DIV_CLASSES if k)
        img = ", ".join(f'<img class="{k}">' for k in sorted(ae.IMG_CLASSES))
        return (
            "THE CLASS VOCABULARY IS CLOSED, AND EACH CLASS BELONGS TO ONE "
            "ELEMENT. A right class on the wrong element is refused:\n"
            f"  - a BARE <p> — the article's own prose, and nothing else\n"
            f"  - editorial paragraphs: {p}\n"
            f"  - divs: {div}\n"
            f"  - figures: {img}\n"
            "  - headings: h1.section, h2.rule; and blockquote for a quotation\n"
            "Anything else is refused outright — a new class is not a way round "
            "the fidelity check.\n"
            # 🔴 EP19, 9 Aug 2026. The body typed the Curtis Rating Plan's 3x3 grid as
            # an HTML <table> AND placed figure-3 — the card showing that same grid —
            # immediately underneath it. The gate refused the whole body on <td>.
            # It is an understandable move and the vocabulary list alone does not
            # forbid it: the article really does contain a <table>, and §0a says
            # reproduce the article. Nothing said which ELEMENT carries a grid.
            "⚠️ A TABLE IN THE ARTICLE IS CARRIED BY ITS FIGURE, NOT BY MARKUP. "
            "There is no <table> in this vocabulary — no table, tr, td, th, thead "
            "or tbody — and adding one is refused outright. Where the article "
            "prints a grid, this episode has a CARD for it and that card is one of "
            "the figures[]: place the <img> and let it carry the grid. Do NOT also "
            "re-type the values as text. An episode did both, and the same nine "
            "numbers appeared twice on the page, once in a form the gate rejects.\n\n")
    except Exception:                                  # noqa: BLE001
        return ""      # the brief is still usable; the gate still holds


def _card_vocabulary_note() -> str:
    """The card vocabulary, ASKED OF author_cards, WHICH ENFORCES IT.

    🔴 DERIVED, NOT RESTATED, for the reason the e-book brief learned the hard
    way: a brief that points at a document naming the vocabulary does not say
    which value goes where, and a brief that restates it is a second list nobody
    updates. EP16 carried TWENTY schema and job faults written from memory of
    exactly this vocabulary — four jobs, a job->block map, per-block schemas with
    required/optional/list keys, enums, and "every declared key must be PRESENT,
    null if empty". That is not an argument for trying harder. It is the argument
    for handing the writer the real thing.
    """
    try:
        sys.path.insert(0, str(SKILL_DIR / "scripts"))
        import author_cards as ac
        blocks = sorted(f[:-5] for f in os.listdir(os.path.join(ac.CARDS_DIR, "blocks"))
                        if f.endswith(".html"))
        lines = [
            "THE CARD VOCABULARY IS CLOSED. These are the real values, read from "
            "the code that enforces them — not a summary:\n",
            f"  jobs: {', '.join(ac.JOBS)}   (every card declares exactly one)",
            "  a job constrains which block may render it:",
        ]
        for job, allowed in ac.JOB_BLOCKS.items():
            lines.append(f"    {job:<8} -> "
                         + ("any block" if allowed is None else ", ".join(sorted(allowed))))
        lines.append(f"  blocks available: {', '.join(blocks)}, or \"bespoke\" for a "
                     "hand-authored page (say why in detail)")
        lines.append(f"  R3 CAP: at most {ac.MAX_ASSERTION*100:.0f}% of content cards may "
                     f"use {', '.join(sorted(ac.ASSERTION_BLOCKS))} — measured on the "
                     "BLOCK, never on the declared job, because relabelling does not "
                     "change a picture")
        lines.append(f"  a {', '.join(sorted(ac.LIST_BLOCKS))} claiming job 'relate' must "
                     "also carry relates_to, naming what its items connect to")
        lines.append("\n  EACH BLOCK'S OWN SCHEMA — every declared key must be PRESENT, "
                     "with explicit null for a slot you mean to leave empty. A MISSING "
                     "key halts, because null records a decision and absence records "
                     "nothing:")
        for b in blocks:
            s = ac.load_block(b)["schema"]
            req = ", ".join(s.get("required", [])) or "-"
            opt = ", ".join(s.get("optional", [])) or "-"
            lst = ""
            for name, spec in (s.get("lists") or {}).items():
                f = spec.get("fields")
                lst += (f"\n      list {name}: {spec.get('min',1)}-{spec.get('max',99)} items"
                        + (f", fields {f}" if f else ", plain strings"))
                for k, vals in (spec.get("enum") or {}).items():
                    lst += f", {k} must be one of {vals}"
                for k in spec.get("numeric", []):
                    lst += f", {k} must be a bare number"
            lines.append(f"    {b}: required [{req}]  optional [{opt}]{lst}")
        return "\n".join(lines) + "\n\n"
    except Exception:                                  # noqa: BLE001
        return ""      # the brief is still usable; the gates still hold


def autofit_cards(ep_dir: Path) -> str:
    """Step the type down until the rendered card fits. Runs BETWEEN authoring and
    checking, because it exists to stop `card_check` halting over type size.

    THE HALT CLASS THIS REMOVES IS A NEW ONE, and it matters that it is named
    separately: the four halts 1d closed were all "NOTHING WAS AUTHORED" — an episode
    arrived without pages and the engine asked a browser operator to write HTML. This
    is "THE AUTO-AUTHORED CONTENT DOES NOT FIT": the pages exist, the words are right,
    every figure is traced, and the type is two points too big for its box. Hugh can
    clear the first class about as well as the second — not at all — so it counts, but
    it is a different failure and hiding it inside the old number would flatter the
    road-to-Hugh figure.

    Two episodes hit it before it was fixed: EP12 by hand (the 130->126px and 26->24px
    nudges) and EP13 three times in one episode.

    A card that still will not fit at the floor is a REAL halt and autofit says so —
    the words are longer than the design can hold, which is a human choice between the
    words and the layout, not something to shrink away.
    """
    r = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts/autofit_cards.py"),
         str(ep_dir / "overlay/export")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode:
        raise EngineFlag(
            "A card's text does not fit its box, and stepping the type down to the floor "
            "did not clear it. This is NOT a missing-file problem and NOT a stale-template "
            "problem: the page is authored, the words are right and every figure is traced "
            "— the content is simply longer than the design can hold. That is a choice "
            "between the words and the layout, and it is yours, not the build's.\n"
            f"{(r.stdout or r.stderr).strip()[-1200:]}")
    return (r.stdout or "").strip()


def author_missing_cards(ep_dir: Path) -> str:
    """Author every card page that does not exist yet. Halts are human-shaped.

    author_cards.py exits 2 when a guard fires (unknown block, missing key,
    untraceable figure). That is a real halt and it is kept — but it names the
    card and the key, so it is something a person can act on, unlike "stage the
    pages yourself".
    """
    script = SKILL_DIR / "scripts/author_cards.py"
    r = subprocess.run(
        [sys.executable, str(script), str(ep_dir / "docs/episode.json"),
         str(ep_dir / "overlay/export")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode:
        raise EngineFlag(
            "The card pages could not be authored from episode.json. This is a DATA "
            "problem, not a missing-file problem — fix the field it names in "
            f"docs/episode.json, then clear this flag.\n{(r.stderr or r.stdout).strip()[-900:]}")
    return (r.stdout or "").strip()


def ep_folder(ep) -> str:
    """Working folder name for an episode (bare stem until the Stage-8 rename)."""
    nn = ep.get("ep_number")
    return f"PP-EP{int(nn):02d}" if nn is not None else f"PP-EP-{ep['id'][:8]}"


# --- the §4a source-article capture: ONE LOOKUP, EVERY CALLER ----------------
#
# The capture is the article's own words, saved to PP Videos/docs before anything
# is written from it. FOUR things read it — author_ebook's fidelity gate,
# author_cards' trace check, preflight_cards' marker check, and the episode.json
# commission — and the drafting pass will be the fifth.
#
# 🔴 IT LIVES HERE BECAUSE A SECOND COPY OF A GLOB IS A SECOND THING TO GET WRONG.
# This pattern was written inline inside _commission_episode_json. Adding the
# script's own precondition by copying those three lines would be fault #2 exactly
# — one value in two places, and the fix reaching one reader. The MESSAGES differ
# per caller, on purpose (see below); the LOOKUP does not.
#
# ✅ AND THE GLOB IS ANCHORED, WHICH IS NOT AN ACCIDENT. `EP{nn:02d}-source-article-*`
# zero-pads and carries a literal `-source-article-` immediately after the number,
# so EP01 cannot match EP10's capture and EP09 cannot match EP98's. That is fault
# #0a — the bug that made two outro audits confidently wrong — and it is closed by
# the shape of the pattern rather than by anybody remembering.
def find_capture(pp: Path, ep_number) -> Path | None:
    """The episode's source-article capture, or None. Deterministic when several
    match (sorted, first) so two callers never disagree about which one it is."""
    hits = sorted((Path(pp) / "docs").glob(
        f"EP{int(ep_number):02d}-source-article-*.md"))
    return hits[0] if hits else None


def assert_capture_for_script(pp: Path, ep_number) -> Path:
    """The capture, or HALT. The precondition the drafting pass runs on.

    ⚠️ THE WORDING IS THE SCRIPT'S OWN, AND THAT IS DELIBERATE. The episode.json
    commission raises its own sentence for the same missing file, because the two
    are met at different moments and a message that tries to serve both is wrong
    for whichever it was not written for (the same reasoning `_script_checks`
    already carries). The FILE LOOKUP is shared; the ENGLISH is not.

    A19: this halt is the STUDIO's, not the operator's — nobody holding a browser
    can capture an article. The drafting pass therefore CATCHES this and writes it
    to the run log rather than badging Jodie's queue with a job she cannot do
    (docs/DESIGN-the-pre-claim-drafting-pass.md §4).
    """
    cap = find_capture(pp, ep_number)
    if cap is None:
        raise EngineFlag(
            "The article for this episode hasn't been captured yet, so there is "
            "nothing to write the script from. Nothing has been written.\n"
            "The capture is the article's own words, saved before the script is "
            "drafted. It isn't there yet.\n"
            "Retrying will not help until the article has been captured.")
    return cap


# ==========================================================================

def pasteable_description(text: str) -> str:
    """The part of a -youtube.txt file a human actually pastes.

    The file carries THREE things: the derived title on line 1, the
    description under a "DESCRIPTION — paste from here" banner, and a NOTES
    block the file itself labels "for the record, not for pasting". Only the
    middle one belongs in the rail column: `youtube_copy` is rendered
    straight onto the publish card, and putting the notes there would show
    Jodie two thousand words of hashtag reasoning where the description
    should be.

    ⚠️ IF THE BANNERS ARE NOT THERE, RETURN THE WHOLE FILE. An older episode,
    or a hand-written one, may not have them — and showing everything is a
    visible oddity a person can fix, where showing nothing looks like the
    step failed.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    start = end = None
    for i, ln in enumerate(lines):
        u = ln.upper()
        if start is None and u.startswith("DESCRIPTION"):
            start = i + 1
        elif start is not None and u.startswith("NOTES"):
            end = i
            break
    if start is None:
        return text.strip()
    body = lines[start:end if end is not None else len(lines)]
    # drop the ==== rules that fence the banners, top and bottom
    while body and set(body[0].strip()) <= {"="} :
        body.pop(0)
    while body and (not body[-1].strip() or set(body[-1].strip()) <= {"="}):
        body.pop()
    return "\n".join(body).strip() or text.strip()


class MockProvider:
    """Pretend externals. Artifacts are small text files under .mock/ so every
    step has a real, checkable output path — same shape as a real run."""

    name = "mock"

    def __init__(self, mock_root: Path):
        self.root = mock_root
        self.step_secs = float(os.environ.get("MOCK_STEP_SECS", "1.5"))
        self._fail_always = os.environ.get("MOCK_FAIL_STEP", "")
        self._fail_once = os.environ.get("MOCK_FAIL_ONCE", "")
        self._failed_once: set[str] = set()

    def maybe_fail(self, step: str):
        if self._fail_always == step:
            raise RuntimeError(f"injected failure in {step} (MOCK_FAIL_STEP)")
        if self._fail_once == step and step not in self._failed_once:
            self._failed_once.add(step)
            raise RuntimeError(f"injected one-off failure in {step} (MOCK_FAIL_ONCE)")

    def _artifact(self, folder: str, rel: str, note: str) -> str:
        p = self.root / folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        # A .png stub used to be a text file with a .png name. The end card
        # composites overlay/export/ebook-cover.png, so a fake one renders as an
        # alt-text box and the mock stops resembling a real run. Copy a real
        # image instead — it costs nothing and keeps the mock honest.
        #
        # A cover gets a PORTRAIT placeholder at the real 1:1.414 ratio. This is
        # not fussiness: the end card sizes itself from the cover, and a square
        # stand-in pushed its text out to x=2441 on a 1920px card — card_check
        # caught it, which is exactly what it is for.
        src = SKILL_DIR / "assets/pp-logo-on-dark.png"
        name = Path(rel).name
        if "cover" in name and rel.endswith(".png"):
            src = REPO_DIR / "engine/testdata/mock-ebook-cover.png"
        elif name.startswith("hero") and rel.endswith(".png"):
            # A real photograph, so the cover the mock builds is a cover: the
            # template scrims the hero and sets white type over it, and a
            # transparent logo would leave white-on-white that no geometric
            # check can see.
            src = SKILL_DIR / "assets/marketing-hero.png"
        if rel.endswith(".png") and src.is_file():
            shutil.copyfile(src, p)
        else:
            p.write_text(f"mock artifact: {note}\n", encoding="utf-8")
        return str(p)

    def _work(self):
        time.sleep(self.step_secs)

    # -- plan / credits ------------------------------------------------------
    def broll_plan(self, ep) -> list[str]:
        n = int(os.environ.get("MOCK_BROLL_CLIPS", "3"))
        return [f"broll-{i:02d}" for i in range(1, n + 1)]

    def broll_staged(self, ep, clip: str) -> bool:
        return False                       # mock always "generates"

    def balance(self) -> float:
        return float(os.environ.get("MOCK_BALANCE", "100"))

    def clip_cost(self, ep) -> float:
        return 4.0                         # pretend per-clip credits

    def cover_cost(self, ep) -> float:
        return 4.0                         # two pretend heroes @ 2 credits

    # -- steps ---------------------------------------------------------------
    def fetch_script(self, ep, write=True):
        """Pretend Doc read. Deterministic text so the drift check is stable."""
        self.maybe_fail("script_sync")
        self._work()
        text = (f"Mock script for {ep_folder(ep)}.\n"
                "Gordon says a few plain, wry Australian words about the form.\n")
        if write:
            self._artifact(ep_folder(ep), "docs/spoken-words.txt", "from mock Doc")
            p = self.root / ep_folder(ep) / "docs/spoken-words.txt"
            p.write_text(text, encoding="utf-8")
        return text, sha256_text(text), "the mock Doc"

    def audit_inputs(self, ep) -> dict:
        self.maybe_fail("audit_inputs")
        self._work()
        folder = ep_folder(ep)
        for sub in ("docs", "renders", "overlay/export", "overlay/clips",
                    "broll", "ebook", "thumbnail", "output"):
            (self.root / folder / sub).mkdir(parents=True, exist_ok=True)
        # A REAL episode.json, carrying block/content{}/trace{} exactly as a real
        # one must. Scaffolding the old shape would let a mock run prove the
        # render side works while hiding that a real episode arrives without the
        # fields the authoring needs — which is the trap this step exists to head
        # off. The source article goes beside it so trace-or-halt really runs.
        fixture = REPO_DIR / "engine/testdata/mock-episode.json"
        shutil.copyfile(fixture, self.root / folder / "docs/episode.json")
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_DIR / "engine/testdata/mock-source-article.md",
                        self.root / "docs/mock-source-article.md")
        # The e-book article BODY, as if written at script time. It is editorial —
        # the article reproduced near-verbatim — so the engine never authors it; it
        # gates it. Scaffolding it here is the mock standing in for the create step,
        # exactly as it stands in for the Script Gate and the started render.
        shutil.copyfile(REPO_DIR / "engine/testdata/mock-ebook-body.html",
                        self.root / folder / "ebook/body.html")
        self._artifact(folder, "docs/spoken-words.txt", "script")
        return {"folder": folder}

    def submit_broll(self, ep, clip: str) -> str:
        self.maybe_fail("broll_submit")
        self._work()
        return f"mock-hf-{clip}-{uuid.uuid4().hex[:8]}"

    def poll_broll(self, ep, clip, job_id, polls_so_far):
        self.maybe_fail("broll_collect")
        self._work()
        if polls_so_far < 1:
            return None
        return self._artifact(ep_folder(ep), f"broll/{clip}.mp4", f"job {job_id}")

    def render_ebook_cover(self, ep, choice="A") -> str:
        """Real authoring and a real render, like render_cards — local only.

        Faking this would leave the thing this slice changed unproven: that a
        clean folder with no cover.html now produces a cover instead of a halt
        telling a browser operator to stage one.
        """
        self.maybe_fail("ebook_cover")
        f = ep_folder(ep)
        d = self.root / f
        src = d / "ebook/cover-src/cover.html"
        cover = d / "ebook/cover.png"
        self._artifact(f, "ebook/cover-src/hero.png", f"active hero = {choice}")
        report = author_missing_cover(d)
        w, h = cover_canvas(src)
        try:
            self.run([sys.executable, SKILL_DIR / "scripts/render_still.py",
                      src, cover, str(w), str(h)], cwd=d, timeout=300)
            self.run([sys.executable, SKILL_DIR / "scripts/cover_check.py",
                      src, str(w), str(h)], cwd=d, timeout=180)
        except RuntimeError as e:
            raise EngineFlag(f"Mock cover render failed: {str(e)[-700:]}")
        (d / "overlay/export").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cover, d / "overlay/export/ebook-cover.png")
        print(f"    [mock] {report} — rendered {w}x{h}, cover_check clean")
        return str(cover)

    def render_cards(self, ep) -> list[str]:
        """The one mock step that does REAL work, on purpose.

        Authoring and rendering cards is local Chromium — no credits, no network,
        nothing external. Faking it would mean the mock could not prove the thing
        1d changed: that a clean folder with no card pages now produces cards
        instead of a halt a browser operator cannot clear.
        """
        self.maybe_fail("cards_render")
        f = ep_folder(ep)
        d = self.root / f
        export = d / "overlay/export"
        export.mkdir(parents=True, exist_ok=True)
        added = stage_card_furniture(export)
        hero = stage_title_hero(d)
        report = author_missing_cards(d)
        # The title card too — same order as real. The mock exists to prove that a
        # clean folder produces cards instead of a halt, and TITLE was the last
        # halt in that class, so leaving it out would make the mock lie.
        title = author_missing_title(d)
        fit = autofit_cards(d)          # same order as real: author -> fit -> check
        try:
            self.run([sys.executable, SKILL_DIR / "scripts/card_check.py", export],
                     cwd=d, timeout=600)
            self.run([sys.executable, SKILL_DIR / "scripts/render_cards_batch.py",
                      export, d / "overlay/clips"], cwd=d, timeout=900)
        except RuntimeError as e:
            raise EngineFlag(f"Mock card render failed: {str(e)[-700:]}")
        print(f"    [mock] staged {len(added)} furniture file(s); {report}")
        print(f"    [mock] {hero}")
        print(f"    [mock] {title}")
        print(f"    [mock] {fit}")
        return sorted(str(p) for p in (d / "overlay/clips").glob("*.mp4"))

    # The mock has no public bucket and no board to render on, so it publishes
    # nothing and reviews nothing. Present so `--mock` exercises the same call
    # shape as the real run rather than dying on a missing attribute.
    def publish_title_preview(self, ep):
        return None

    def title_placement_review_for(self, ep, url=None):
        return None

    def run(self, args, cwd, timeout=None, tail=800):
        r = subprocess.run([str(a) for a in args], cwd=str(cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout or 600)
        if r.returncode != 0:
            raise RuntimeError(f"{Path(str(args[1])).name} exited {r.returncode}: "
                               f"…{(r.stderr or r.stdout or '').strip()[-tail:]}")
        return r

    def poll_heygen(self, ep, polls_so_far):
        self.maybe_fail("heygen_download")
        self._work()
        if polls_so_far < 1:
            return None
        return self._artifact(ep_folder(ep), "renders/presenter-master.mp4",
                              f"HeyGen master for {ep.get('heygen_name')}")

    def build_shot_map(self, ep) -> str:
        self.maybe_fail("shot_map")
        self._work()
        return self._artifact(ep_folder(ep), "renders/shot-map.json", "shot map + SRT")

    def publish_artefact(self, ep, local) -> str:
        """Mock: a plausible https URL, nothing uploaded. Present so a step that
        publishes cannot NameError on the mock path — the exact fault
        test_step_call_sites.py exists to catch."""
        self._work()
        return (f"https://mock.invalid/episode-assets/{ep_folder(ep)}/"
                f"{Path(local).name}")

    def make_covers_ab(self, ep):
        self.maybe_fail("covers_ab")
        self._work()
        f = ep_folder(ep)
        self._artifact(f, "ebook/cover-src/hero-a.png", "generated hero A")
        self._artifact(f, "ebook/cover-src/hero-b.png", "generated hero B")
        return (self._artifact(f, "thumbnail/cover-A.png", "cover option A"),
                self._artifact(f, "thumbnail/cover-B.png", "cover option B"))

    def assemble_passA(self, ep) -> str:
        self.maybe_fail("assemble_passA")
        self._work()
        return self._artifact(ep_folder(ep), "overlay/_passA.mp4", "pass A base motion")

    def assemble_passB(self, ep) -> str:
        self.maybe_fail("assemble_passB")
        self._work()
        return self._artifact(ep_folder(ep), "output/FINAL.mp4", "pass B final")

    def self_qc(self, ep, final_path) -> str:
        self.maybe_fail("self_qc")
        self._work()
        return self._artifact(ep_folder(ep), "output/QC-REPORT.md", "self-QC passed")

    def build_ebook(self, ep) -> str:
        """Real authoring, real figures, a real PDF — like the cover and the cards.

        Every part of this is local: Chromium renders the figures from the card
        pages, and WeasyPrint renders the PDF. No credits, no network. Faking it
        would leave the thing this slice changed unproven — that a clean folder
        with no e-book source produces a book instead of a halt asking a browser
        operator to write HTML, and that the fidelity gate really runs.
        """
        self.maybe_fail("ebook_pdf")
        f = ep_folder(ep)
        d = self.root / f
        print(f"    [mock] figures: {render_ebook_figures(d)}")
        print(f"    [mock] {author_missing_ebook(d)}")
        src = d / "ebook" / f"{f}-ebook-source.html"
        out = d / "output" / f"{f}-ebook.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.run([sys.executable, SKILL_DIR / "scripts/build_ebook.py", src, out],
                     cwd=d, timeout=600)
        except RuntimeError as e:
            raise EngineFlag(f"Mock e-book build failed: {str(e)[-700:]}")
        return str(out)

    def build_thumbnail(self, ep) -> str:
        """Real authoring and a real render, like the cover and the cards."""
        self.maybe_fail("thumbnail")
        f = ep_folder(ep)
        d = self.root / f
        self._artifact(f, "thumbnail/hero.png", "thumbnail hero")
        report = author_missing_thumbnail(d)
        pages = list((d / "thumbnail").glob("*thumbnail*.html"))
        out = d / "output" / f"{f}-thumbnail.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.run([sys.executable, SKILL_DIR / "scripts/render_still.py",
                      pages[0], out, "1280", "720"], cwd=d, timeout=300)
        except RuntimeError as e:
            raise EngineFlag(f"Mock thumbnail render failed: {str(e)[-700:]}")
        print(f"    [mock] {report}")
        # Exercise the REAL flag path, then stand in for the human who looks at
        # it — the same shape as cover_pick's auto-pick. The flag is raised and
        # cleared here so the spine is proved end to end rather than skipped.
        try:
            thumbnail_placement_review(d, out)
        except EngineFlag as flag:
            print(f"    [mock] needs_look raised as designed: {str(flag).splitlines()[0]}")
            print("    [mock] no human here — auto-confirming the placement to exercise "
                  "the spine")
        return str(out)

    def save_youtube_copy(self, ep) -> str:
        self.maybe_fail("youtube_copy")
        self._work()
        return self._artifact(ep_folder(ep), "output/youtube.txt", "YT title + description")


# ==========================================================================
class RealProvider:
    """The real toolchain, driven exactly as the pp-episode-production skill
    documents it. Steps find-or-build: an artifact already on disk is used, not
    rebuilt (resumability + no re-spend). What can't run autonomously FLAGS."""

    name = "real"
    PASS_TIMEOUT = 2400          # ffmpeg passes / card batches can take a while

    def __init__(self, pp_videos: Path):
        self.pp = pp_videos                       # MEDIA: episode folders, .env
        self.scripts = SKILL_DIR / "scripts"      # CODE: versioned, in the repo
        self.assets = SKILL_DIR / "assets"
        self.logo = self.assets / "video-logo-chip.png"
        self.music = pp_videos / "PP-EP01-The-Trifecta-Mistake/music" / \
            "ES_Sleeves Full of Aces - Alexandra Woodward.mp3"
        # Higgsfield CLI (B+ wiring, 2026-07-24): hands-off gens on PLAN credits.
        # One-time `hf auth login` per machine; token lives in ~/.config/higgsfield.
        # If the CLI is missing/unauthenticated, every gen path falls back to the
        # honest b-roll gate (Option B) — nothing breaks, a human stages clips.
        self.hf = Path(os.environ.get("HF_CLI", r"C:\Users\jlral\tools\hf\hf.exe"))
        self.broll_model = os.environ.get("ENGINE_BROLL_MODEL", "kling3_0_turbo")
        # Cover heroes: two stills, generated UPFRONT in the gens-first batch
        # (~2 credits each). Portrait 2:3 matches the A4-ish cover canvas.
        self.cover_model = os.environ.get("ENGINE_COVER_MODEL", "nano_banana_pro")
        self.cover_aspect = os.environ.get("ENGINE_COVER_ASPECT", "2:3")
        self.cover_res = os.environ.get("ENGINE_COVER_RES", "2k")
        self.cover_ceiling = float(os.environ.get("ENGINE_COVER_CEILING", "12"))
        self._registry_checked = False
        # let the skill's pp_paths put ffmpeg/ffprobe on PATH for our subprocesses
        sys.path.insert(0, str(self.scripts))
        try:
            import pp_paths
            pp_paths.ensure_path()
        except Exception:
            pass                                     # PATH may already be fine

    # -- Higgsfield CLI ------------------------------------------------------
    def _hf(self, *args, timeout=120):
        """Run the Higgsfield CLI with --json and parse the response."""
        r = subprocess.run([str(self.hf), *args, "--json"], capture_output=True,
                           text=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError(f"hf {' '.join(args[:2])} exited {r.returncode}: "
                               f"{(r.stderr or r.stdout).strip()[-300:]}")
        return json.loads(r.stdout)

    def hf_ready(self) -> bool:
        return self.hf.is_file()

    # -- plumbing ------------------------------------------------------------
    def dir(self, ep) -> Path:
        return self.pp / ep_folder(ep)

    def epjson(self, ep) -> dict:
        return json.loads((self.dir(ep) / "docs/episode.json").read_text(encoding="utf-8"))

    def run(self, args, cwd, timeout=None, tail=800):
        """Run a tool; on failure raise with the stderr tail (goes into the
        plain-English flag if retries exhaust).

        ⚠️ `encoding="utf-8"` IS LOAD-BEARING, FIXED 28 Jul 2026. Without it,
        `text=True` decodes with the locale default — cp1252 on this machine — so a
        child printing an em dash came back as mojibake, went into the EngineFlag
        message, and landed on Jodie's board as unreadable punctuation in the middle
        of an error she was trying to read. Every one of these scripts writes UTF-8
        deliberately (they all call `sys.stdout.reconfigure(encoding="utf-8")`), so
        the reader has to agree with the writers.
        `errors="replace"` because a flag message must never itself raise: the cards
        slice added a strict decode here once and a child's em dash killed the
        engine's reader thread with a UnicodeDecodeError. A stricter decode is a
        behaviour change, not a tidy-up.
        """
        r = subprocess.run([str(a) for a in args], cwd=str(cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout or self.PASS_TIMEOUT)
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip()[-tail:]
            raise RuntimeError(f"{Path(str(args[0])).name if not str(args[0]).endswith('py') else Path(str(args[1])).name} "
                               f"exited {r.returncode}: …{err}")
        return r

    def py(self, script, *args, cwd, timeout=None):
        return self.run([sys.executable, self.scripts / script, *args],
                        cwd=cwd, timeout=timeout)

    def _clip_from_episode_json(self, ep, cid: str, clips: Path):
        """The clip this card NAMES, or None if episode.json cannot say.

        A card's `page` is the promise: render_cards writes `<page stem>.mp4`. Reading
        it here is the difference between "the file this card is" and "a file whose name
        looks about right".
        """
        try:
            epj = self.epjson(ep)          # the one reader, not a second copy of it
        except Exception:                                          # noqa: BLE001
            return None                    # no settings yet — the glob still has a job
        card = next((c for c in epj.get("cards") or [] if c.get("id") == cid), None)
        page = (card or {}).get("page")
        if not page:
            return None
        want = clips / (Path(page).stem + ".mp4")
        return want if want.is_file() else None

    def _clip(self, ep, cid: str) -> Path:
        """Map an episode.json card id (C1, TITLE, END, WARRANTY) to its
        rendered clip in overlay/clips/ (files carry descriptive names).

        🔑 E20's SWEEP: ASK episode.json, DO NOT GUESS FROM THE FILENAME. The card
        already carries `page`, and a clip is that page's stem with .mp4 — so the exact
        name is KNOWN and the glob `*c07*.mp4` was a guess standing in for it. E20 wrote
        the danger down: "a card whose page is renamed stops matching", and at 300
        episodes a two-digit pattern is a collision waiting to happen — `*c07*` matches
        anything with c07 anywhere in it, including a name a human chose.
        The glob stays as a FALLBACK for episodes authored before this, and says so when
        it fires: a silent fallback is the guess again with extra steps.
        """
        clips = self.dir(ep) / "overlay/clips"
        exact = clips / f"{cid}.mp4"
        if exact.is_file():
            return exact
        named = self._clip_from_episode_json(ep, cid, clips)
        if named is not None:
            return named
        pats = {"TITLE": "*title*.mp4", "END": "end-card*.mp4", "WARRANTY": "warranty*.mp4"}
        pat = pats.get(cid) or f"*c{int(cid[1:]):02d}*.mp4"   # C7 -> *c07*.mp4
        hits = [p for p in sorted(clips.glob(pat)) if "lowerthird" not in p.name]
        if len(hits) == 1:
            print(f"    ⚠️ clip for {cid} found by PATTERN {pat!r}, not by name: "
                  f"episode.json does not give this card a `page`, or the file does not "
                  f"match it. Works, but it is a guess — see E20.")
        if len(hits) != 1:
            # An EngineFlag, NOT a RuntimeError: a card that did not land is not a
            # transient fault, so retrying burns three full Chromium batch renders
            # before saying anything. Fail once, in plain English. (Design §16.11.)
            raise EngineFlag(
                f"Card {cid} has no clip in overlay/clips: expected exactly one file "
                f"matching {pat}, found {len(hits)}. Most likely {cid} is marked "
                f'block:"bespoke" in episode.json and its page has not been hand-authored '
                f"yet — bespoke cards are never generated, by design. Otherwise the page "
                f"is named so it does not match, or it failed to render. "
                f"Retrying will not fix any of those.")
        return hits[0]

    def _audio_kbps(self, path: Path) -> float:
        r = self.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                      "-show_entries", "stream=bit_rate", "-of", "csv=p=0", path],
                     cwd=path.parent, timeout=60)
        try:
            return float(r.stdout.strip()) / 1000.0
        except ValueError:
            return 0.0

    # -- plan / credits ------------------------------------------------------
    def broll_plan(self, ep) -> list[str]:
        return [b["target"] for b in self.epjson(ep).get("broll", [])]

    def broll_staged(self, ep, clip: str) -> bool:
        return (self.dir(ep) / "broll" / f"{clip}.mp4").is_file()

    def _broll_prompt(self, ep, clip: str) -> str:
        for b in self.epjson(ep).get("broll", []):
            if b["target"] == clip:
                if not b.get("prompt"):
                    raise EngineFlag(
                        f"B-roll clip '{clip}' has no prompt in episode.json — "
                        "Claude Code writes the b-roll prompts (hats / ethnic-mix / "
                        "turf wording baked in). Add it, then clear this flag.")
                return b["prompt"]
        raise RuntimeError(f"clip {clip} not found in episode.json broll[]")

    def balance(self) -> float:
        if self.hf_ready():
            return float(self._hf("account", "status")["credits"])
        raise EngineFlag(
            "I can't check the Higgsfield balance: the CLI isn't installed on this "
            "machine (see engine/README — install + `hf auth login` once). Either "
            "install it, or confirm credits manually and clear this flag.")

    def clip_cost(self, ep) -> float:
        """Exact per-clip estimate via the CLI's cost preview (no spend)."""
        if not self.hf_ready():
            return 8.0                     # conservative planning figure
        clips = self.broll_plan(ep)
        probe = next((c for c in clips if not self.broll_staged(ep, c)), None)
        if probe is None:
            return 0.0
        return float(self._hf("generate", "cost", self.broll_model,
                              "--prompt", self._broll_prompt(ep, probe))["credits"])

    # -- cover heroes (gens-first batch, alongside the b-roll) ---------------
    def _hero_paths(self, ep):
        """hero-a.png / hero-b.png are the two OPTIONS; hero.png is whichever one
        is currently ACTIVE (what cover.html draws). Older episodes only have
        hero.png + hero-b.png — hero.png IS option A there, so adopt it."""
        src = self.dir(ep) / "ebook/cover-src"
        a, b, active = src / "hero-a.png", src / "hero-b.png", src / "hero.png"
        if active.is_file() and not a.is_file():
            src.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(active, a)
        return a, b, active

    def _cover_prompts(self, ep):
        c = self.epjson(ep).get("cover") or {}
        a, b = c.get("hero_a_prompt"), c.get("hero_b_prompt")
        if not (a and b):
            raise EngineFlag(
                "The two cover-hero prompts are missing from episode.json. Add a "
                '"cover": {"hero_a_prompt": "…", "hero_b_prompt": "…"} block — two '
                "DIFFERENT compositions (Claude Code writes them, with the hats / "
                "ethnic-mix / turf wording baked in). The heroes are generated "
                "UPFRONT with the b-roll so the cover pick reaches you while "
                "Gordon is still rendering. Add them, then clear this flag.")
        return a, b

    def cover_cost(self, ep) -> float:
        """Exact preview of the cover-hero spend (no spend). 0 once both heroes
        are on disk — a staged asset is never regenerated."""
        a, b, _ = self._hero_paths(ep)
        missing = [p for p in (a, b) if not p.is_file()]
        if not missing:
            return 0.0
        if not self.hf_ready():
            return 2.0 * len(missing)      # conservative planning figure
        pa, _pb = self._cover_prompts(ep)  # flags EARLY if the prompts aren't written
        per = float(self._hf("generate", "cost", self.cover_model, "--prompt", pa,
                             "--aspect_ratio", self.cover_aspect,
                             "--resolution", self.cover_res)["credits"])
        return per * len(missing)

    @staticmethod
    def _prompt_key(slot: str, prompt: str) -> str:
        """The ledger key: the SLOT and a hash of the PROMPT that made the image.

        The ledger answers "have I already paid for this?" — and the real question is
        "have I already paid for THIS PROMPT?". A guard that can never be cleared
        becomes a trap. (E16)
        """
        return f"{slot}:{hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:12]}"

    def _generate_heroes(self, ep, want):
        """Fire the missing heroes, checkpointing each job id into
        docs/hero-jobs.json the instant it exists (same double-spend guard as
        the b-roll). Previewed and capped before anything is spent."""
        if not self.hf_ready():
            raise EngineFlag(
                "The two cover heroes aren't on disk and the Higgsfield CLI isn't "
                "installed (see engine/README). Either install it for hands-off "
                "gens, or stage ebook/cover-src/hero-a.png + hero-b.png, then "
                "clear this flag.")
        pa, pb = self._cover_prompts(ep)
        prompts = {"hero_A": pa, "hero_B": pb}
        ledger = self.dir(ep) / "docs/hero-jobs.json"
        book = json.loads(ledger.read_text(encoding="utf-8")) if ledger.is_file() else {}

        per = 0.0
        # E16 — THE LEDGER KEY IS THE SLOT *AND* THE PROMPT.
        # It used to be the slot alone ("hero_A"), so once a job id existed the create
        # was never reached again and `_hf_download` simply re-fetched that job's
        # output. DELETING THE PNGs CANNOT INVALIDATE A STORED JOB ID.
        # EP15, 3-4 Aug 2026: both heroes were looked at and REJECTED — one carried a
        # competitor's brand, the other had a line of the prompt rendered across the
        # sky. The prompts were corrected and the files moved aside; the engine
        # re-downloaded the same two pictures, the board offered them again with
        # nothing to say they had been rejected, and Jodie picked one in good faith.
        # She made a decision on bad information and had no way to know.
        # Same prompt -> same key -> the double-spend guard works exactly as before.
        # Changed prompt -> different key -> a genuine create. Nobody has to remember
        # to clear a file, which is the only kind of fix that holds: the version that
        # relied on remembering failed the first time it mattered.
        lk = {k: self._prompt_key(k, prompts[k]) for k, _ in want}
        todo = [(k, p) for k, p in want if not book.get(lk[k], {}).get("job_id")]
        if todo:
            per = float(self._hf("generate", "cost", self.cover_model,
                                 "--prompt", prompts[todo[0][0]],
                                 "--aspect_ratio", self.cover_aspect,
                                 "--resolution", self.cover_res)["credits"])
            est = per * len(todo)
            if est > self.cover_ceiling:
                raise EngineFlag(
                    f"The cover heroes are estimated at ~{est:.0f} Higgsfield credits, "
                    f"over the cover ceiling of {self.cover_ceiling:.0f}. Raise "
                    "ENGINE_COVER_CEILING or change ENGINE_COVER_MODEL, then clear "
                    "this flag.")
        for key, path in want:
            rec = book.setdefault(lk[key], {})
            if not rec.get("job_id"):
                job = self._hf("generate", "create", self.cover_model,
                               "--prompt", prompts[key],
                               "--aspect_ratio", self.cover_aspect,
                               "--resolution", self.cover_res)
                rec["job_id"] = job[0] if isinstance(job, list) else job["id"]
                rec["model"] = self.cover_model
                rec["credits"] = per
                rec["slot"] = key
                rec["prompt_sha"] = lk[key].split(":", 1)[1]
                rec["note"] = f"engine gens-first batch -> {path.name}"
                ledger.parent.mkdir(parents=True, exist_ok=True)
                ledger.write_text(json.dumps(book, indent=1), encoding="utf-8")
            self._hf_download(rec["job_id"], path, key)

    def _hf_download(self, job_id, dest: Path, label: str):
        """Poll one Higgsfield job to completion and save the result. Stills are
        quick (well under a minute); the heartbeat keeps beating through this."""
        for _ in range(120):               # ~20 min ceiling, then flag honestly
            job = self._hf("generate", "get", job_id)
            status = job.get("status")
            if status in ("failed", "nsfw"):
                raise RuntimeError(f"Higgsfield job for {label} came back {status}")
            if status == "completed":
                url = job.get("result_url")
                if not url:
                    raise RuntimeError(f"job for {label} completed but has no result_url")
                dest.parent.mkdir(parents=True, exist_ok=True)
                # E22 applies here too: these are PAID clips and heroes, and a short
                # one plays. Same guard, same reason — found by asking whether the
                # HeyGen fault had siblings rather than fixing only where it bit.
                self._download_exact(url, dest)
                return str(dest)
            time.sleep(10)
        raise RuntimeError(f"Higgsfield job for {label} never completed ({job_id})")

    # -- the script's ONE home: the RAIL (ruling A5), or a Doc while one exists -
    DOC_ID = re.compile(r"/document/d/([A-Za-z0-9_-]{20,})")

    def _script_checks(self, text: str, where: str) -> str:
        """The RAIL path's guarantees. The Doc path keeps its own, on purpose.

        ⚠️ THE OBVIOUS MOVE HERE IS TO SHARE ONE FUNCTION BETWEEN BOTH PATHS, AND
        IT IS THE WRONG ONE — for two separate reasons, both worth keeping:

        1. **EP01–EP16 must behave IDENTICALLY.** Touching the Doc branch at all
           to refactor it is a change to fifteen live episodes' read path, bought
           for tidiness. The Doc branch is left byte-for-byte alone.
        2. **THE SAME SYMPTOM HAS A DIFFERENT CAUSE ON EACH PATH.** Backslashed
           punctuation off the Doc means the engine read through the wrong
           channel — *"a fault in me, not in your script"*. The same characters in
           the script box mean a human pasted from something that escapes
           markdown. **A halt may not name a cause it has not established**
           (CLAUDE.md #6), so these two must say different things.

        The duplication is two lines of word-count. The alternative is a message
        that is wrong for whichever path it was not written for.
        """
        text = text.replace("\r\n", "\n").strip()
        # THE SCRIPT BOX HOLDS WHAT GORDON SAYS. NOTHING ELSE.
        #
        # A production-notes header is a DOC-ERA artefact: it existed so a person
        # opening a Doc knew what they were looking at, and it described a
        # transport — "THIS DOC IS THE SCRIPT'S ONE HOME. Edit it here" — that no
        # longer exists. On the board it is worse than clutter: the panel says
        # "this is exactly what Gordon says" above text he never speaks, tells her
        # to edit somewhere there is no longer anywhere to edit, and inflates the
        # word count by counting notes as script. All three were on Jodie's screen.
        #
        # ⚠️ DERIVED, NOT RESTATED. This calls render_ready's OWN strip_notes_header
        # — the same function `render_ready`, `build_shot_map` and `heygen_generate`
        # already use — so the definition of "a notes header" cannot drift into a
        # second implementation. A regex here would have been that second one.
        try:
            sys.path.insert(0, str(SKILL_DIR / "scripts"))
            from render_ready import strip_notes_header    # noqa: PLC0415
            spoken = "\n\n".join(strip_notes_header(text)).strip()
        except Exception:                                  # noqa: BLE001
            spoken = text                                  # never block on the import
        if spoken and spoken != text:
            raise EngineFlag(
                "The script has production notes at the top of it — comment lines, "
                "or a \"paste below this line\" marker. The script box holds only "
                "what Gordon says out loud, so the words on screen are the words in "
                "the video and the count is the real one. Move the notes into the "
                "episode's run log and leave the script itself here.")
        if re.search(r"\\[#!*_\[\]()]", text):
            raise EngineFlag(
                "The script has backslashes in front of ordinary punctuation "
                "(things like \\! or \\#). Those would be read out loud. It "
                "usually means the words were pasted from something that escapes "
                "punctuation — a chat window or a markdown editor. Nothing has "
                "been saved. Paste the plain words again.")
        if len(text.split()) < 50:
            raise EngineFlag(
                f"The script in {where} reads as only {len(text.split())} words "
                "— that's not a full episode script. Write or paste the whole "
                "script, then clear this flag.")
        return text

    def _script_from_rail(self, ep, write=True):
        """THE SCRIPT IS A FIELD IN A RECORD, NOT A DOCUMENT. (Ruling A5.)

        `script_snapshot` on the rail is the script's home. There is no fetch, no
        sharing, no permission and nothing to 404 — which is the whole point of
        the ruling: the Doc dragged in sharing, permissions, formats and
        corruption that a text field simply does not have.

        `docs/spoken-words.txt` is still written here, exactly as the Doc path
        writes it, because it is a DERIVED CACHE that `render_ready` reads at
        `audit_inputs`. Rebuilt every build so an operator edit can never be
        silently ignored.
        """
        text = (ep.get("script_snapshot") or "")
        if not text.strip():
            raise EngineFlag(
                "There is no script for this episode yet. The script lives on "
                "the board, in the script box on the words card — write or "
                "paste it there, read it, tick \"I've read the script\" and "
                "approve the words. Nothing builds and nothing renders until "
                "there is a script to build from.")
        text = self._script_checks(text, "the script box")
        if write:
            out = self.dir(ep) / "docs/spoken-words.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
        return text, sha256_text(text), "the script box on the board"

    def _doc_id(self, ep) -> str:
        url = (ep.get("script_doc_url") or "").strip()
        if not url:
            raise EngineFlag(
                "No script Doc is linked to this episode. The script lives as a "
                "Google Doc in the episode's Drive folder — that Doc is the single "
                "source of truth. Paste its link into the words card on the board, "
                "then clear this flag. I will not build from a local draft.")
        m = self.DOC_ID.search(url)
        if not m:
            raise EngineFlag(
                f"The script Doc link doesn't look like a Google Doc URL ({url[:80]}). "
                "It should look like https://docs.google.com/document/d/<id>/edit — "
                "fix the link on the board, then clear this flag.")
        return m.group(1)

    def fetch_script(self, ep, write=True):
        """Read the approved script and (by default) rebuild docs/spoken-words.txt
        from it. Returns (text, sha256, source).

        ONE SCRIPT, ONE HOME — and since ruling A5 that home is THE RAIL.
        spoken-words.txt is a derived cache, rebuilt here every single build, so an
        operator edit can never be silently ignored.

        ### A DOC STILL WINS WHENEVER ONE EXISTS, AND THAT IS DELIBERATE.
        EP01–EP16 all carry a `script_doc_url` and must go on behaving EXACTLY as
        they did — a re-read of EP15 must still fetch EP15's Doc. The rail path is
        reached only when there is no Doc at all, which is true of EP17 onward.
        **So this is not a migration and nothing is rewritten**: the old episodes
        keep their transport, and the new ones simply never acquire one.

        The Doc branch reads the plain-text export URL, which needs the Doc shared
        as "anyone with the link can view" — the manual step A5 exists to delete.
        Anything that isn't real text — a sign-in page, an empty body — FLAGS. We
        never fall back to a stale local draft, on either path."""
        if not (ep.get("script_doc_url") or "").strip():
            return self._script_from_rail(ep, write=write)
        doc_id = self._doc_id(ep)
        url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pp-engine"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                ctype = (r.headers.get("Content-Type") or "").lower()
        except Exception as e:
            raise EngineFlag(
                f"I can't read the script Doc ({e}). The script is the single source "
                "of truth and I will NOT build from a stale local copy. Check the "
                "Doc still exists and is shared so anyone with the link can view it, "
                "then clear this flag.")
        if "text/plain" not in ctype:
            raise EngineFlag(
                "The script Doc didn't come back as plain text — Google returned "
                f"'{ctype or 'nothing'}', which usually means a sign-in page. Share "
                "the Doc so anyone with the link can VIEW it, then clear this flag. "
                "I will not guess at the script or use an old copy.")
        text = raw.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").strip()
        # THE SCRIPT COMES FROM THE EXPORT URL'S RAW BYTES, NEVER FROM A DOCUMENT API'S
        # "text representation" — and this asserts it, because the difference is
        # invisible until somebody reads it aloud.
        # Measured 4 Aug 2026 on EP15's real Doc: read through the Drive API the same
        # script comes back MARKDOWN-ESCAPED — `\#` on every comment line and
        # `Squeeze Those Odds\!` in the title. Read through this URL it is clean.
        # A backslash before every # and ! would be frozen into script_snapshot as the
        # record of what was approved, and spoken by Gordon.
        if re.search(r"\\[#!*_\[\]()]", text):
            raise EngineFlag(
                "The script came back with backslashes in front of ordinary "
                "punctuation (things like \\! or \\#). That is not what is in the "
                "Doc — it is what happens when a script is read through the wrong "
                "channel, and those backslashes would be read out loud. Nothing has "
                "been saved. This is a fault in me, not in your script: tell whoever "
                "looks after the engine, and do not retype anything.")
        if len(text.split()) < 50:
            raise EngineFlag(
                f"The script Doc reads as only {len(text.split())} words — that's not "
                "a full episode script. Check the right Doc is linked and that it has "
                "content, then clear this flag.")
        if write:
            out = self.dir(ep) / "docs/spoken-words.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
        return text, sha256_text(text), f"the script Doc ({doc_id[:10]}…)"

    # -- steps ---------------------------------------------------------------
    def audit_inputs(self, ep) -> dict:
        d = self.dir(ep)
        missing = [rel for rel in ("docs/episode.json", "docs/spoken-words.txt")
                   if not (d / rel).is_file()]
        if missing:
            raise EngineFlag(
                f"Create-inputs are missing for {d.name}: {', '.join(missing)}. "
                "Claude Code writes these at the create step (the create brain is "
                "Phase 4). Stage them, then clear this flag.")
        # RENDER-READY SCAN (PP-STANDARDS 25 Jul 2026): catch a glitch-prone
        # script BEFORE Jodie spends a HeyGen render on it.
        try:
            self.py("render_ready.py", d / "docs/spoken-words.txt",
                    "--episode", d / "docs/episode.json", cwd=d, timeout=120)
        except RuntimeError as e:
            raise EngineFlag(
                f"The spoken-words track is NOT render-ready — fix it before "
                f"Jodie renders. {str(e)[-500:]}")
        for sub in ("renders", "overlay/export", "overlay/clips", "broll",
                    "ebook", "thumbnail", "output"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        return {"folder": str(d)}

    def submit_broll(self, ep, clip: str) -> str:
        if self.broll_staged(ep, clip):
            return f"staged-{clip}"        # already on disk — nothing to spend
        if not self.hf_ready():
            raise EngineFlag(
                f"B-roll clip '{clip}' isn't on disk and the Higgsfield CLI isn't "
                "installed (see engine/README). Either install it for hands-off "
                "gens, or generate/stage the clip into broll/, then clear this flag.")
        if not self._registry_checked:     # NO-REPEAT law: check BEFORE any spend
            self.py("broll_registry_check.py", REPO_DIR / "docs/broll-registry.md",
                    self.dir(ep) / "docs/episode.json", cwd=self.dir(ep), timeout=120)
            self._registry_checked = True
        job = self._hf("generate", "create", self.broll_model,
                       "--prompt", self._broll_prompt(ep, clip))
        return job[0] if isinstance(job, list) else job["id"]

    def poll_broll(self, ep, clip, job_id, polls_so_far):
        p = self.dir(ep) / "broll" / f"{clip}.mp4"
        if p.is_file():
            return str(p)
        if job_id.startswith("staged-"):
            if polls_so_far > 3:           # staged file vanished — don't spin
                raise RuntimeError(f"b-roll clip {clip} is missing from broll/")
            return None
        job = self._hf("generate", "get", job_id)
        status = job.get("status")
        if status in ("failed", "nsfw"):
            raise RuntimeError(f"Higgsfield job for {clip} came back {status}")
        if status != "completed":
            time.sleep(10)                 # pace the polling; heartbeat stays live
            return None
        url = job.get("result_url")
        if not url:
            raise RuntimeError(f"job for {clip} completed but has no result_url")
        # 🔴 E-a: THIS WAS `copyfileobj` + `rename`, WITH NO LENGTH CHECK AT ALL, ON A
        # PAID CLIP. The pre-E22 shape, left behind when the master and the heroes were
        # fixed on 4 Aug — "the sibling was fixed by asking whether the fault had one",
        # and this one was missed. A connection that drops mid-transfer ends the copy
        # WITHOUT RAISING, so a short clip is renamed into place and ships as a cut that
        # ends abruptly. Nothing downstream would say so: ffprobe reads the full
        # duration out of a faststart mp4 whose tail never arrived.
        # Same byte-counting treatment as the master (f1c3eab), same bounded retry.
        self._download_exact(url, p)
        return str(p)

    def broll_contact(self, ep, files) -> str:
        """6-up contact sheet of b-roll stills — the human glance at the render
        gate BEFORE assembly (PP-STANDARDS b-roll HARD-FAIL list, 25 Jul 2026)."""
        d = self.dir(ep)
        out = d / "output/qc/broll-contact.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        n = len(files)
        cols = 3
        def pos(i):
            x = "+".join(["w0"] * (i % cols)) or "0"
            y = "+".join(["h0"] * (i // cols)) or "0"
            return f"{x}_{y}"
        layout = "|".join(pos(i) for i in range(n))
        fc = "".join(f"[{i}:v]scale=640:-1[t{i}];" for i in range(n)) + \
             "".join(f"[t{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}[out]"
        cmd = ["ffmpeg", "-y"]
        for f in files:
            cmd += ["-ss", "2.5", "-i", f]
        cmd += ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", out]
        self.run(cmd, cwd=d, timeout=300)
        return str(out)

    def render_ebook_cover(self, ep, choice="A") -> str:
        """Build the cover FROM THE PICK: activate the chosen hero (cover.html
        always draws hero.png), re-render from cover-src (never trust a handed
        PNG), then propagate to BOTH ebook/cover.png and
        overlay/export/ebook-cover.png — the cover must land before the card
        batch or the end card renders blank."""
        d = self.dir(ep)
        hero_a, hero_b, active = self._hero_paths(ep)
        pick = hero_b if str(choice).strip().upper() == "B" else hero_a
        if pick.is_file():
            shutil.copyfile(pick, active)          # hero.png = the picked hero
        src = d / "ebook/cover-src/cover.html"
        cover = d / "ebook/cover.png"
        # Author the page if it is missing. This is the halt that stopped EP12
        # first and the second of the four Hugh could not clear: it used to say
        # "stage one, then clear this flag" to a browser operator.
        author_missing_cover(d)
        if src.is_file():
            # The canvas comes from the page, which got it from the template.
            # The old hard-coded 1600x2263 (and the cover-src/cover.png override
            # that could disagree with both) are gone — see cover_canvas().
            w, h = cover_canvas(src)
            self.py("render_still.py", src, cover, w, h, cwd=d)
            # Overlap/clip QC (the EP09 cover lesson): fail rather than ship a
            # cover whose text collides or clips.
            self.py("cover_check.py", src, str(w), str(h), cwd=d, timeout=180)
        elif not cover.is_file():
            raise EngineFlag(
                f"No e-book cover for {d.name}: ebook/cover-src/cover.html could not be "
                "authored and no ebook/cover.png exists. Clear this flag once one does.")
        shutil.copyfile(cover, d / "overlay/export/ebook-cover.png")
        return str(cover)

    def render_cards(self, ep) -> list[str]:
        d = self.dir(ep)
        export = d / "overlay/export"
        export.mkdir(parents=True, exist_ok=True)
        # 1. the standing pages + the assets an authored card needs
        stage_card_furniture(export)
        # 1b. the title card's photograph — a file copy, not a decision (A1)
        print(f"    {stage_title_hero(d)}")
        # 2. author whatever is missing; hand-authored pages are left alone
        author_missing_cards(d)
        # 2a. and the TITLE card, which used to be hand-made on every episode and
        #     halted every one of them with "Card TITLE has no clip in overlay/clips"
        print(f"    {author_missing_title(d)}")
        # 2b. step the type down until it fits, BEFORE the checker judges it. Type
        #     size is a measurement, not a judgement (design §11), so it should never
        #     be a halt. Hand-authored pages are left alone here too.
        print(f"    {autofit_cards(d)}")
        # 2c. EVERY IMAGE A PAGE ASKS FOR MUST EXIST — checked HERE, before a single
        #     clip is rendered, because a page that cannot find its image renders ALT
        #     TEXT on a grey box and nothing downstream notices. EP15 shipped the end
        #     card that way: `self_qc` PASSED it and even reported "end card visible
        #     (luma 33)", because a grey box has a luma. The e-book's cover page came
        #     out blank white from the same missing file.
        #     Deliberately GENERAL — no list of expected files, so it cannot go stale
        #     as pages are added. That is why the list-based guards missed it:
        #     assert_standing_assets() names the standing pages, stage_title_hero()
        #     names the title hero, and this file was on neither.
        print(f"    {assert_page_images(export)}")
        # 3. HARD GATE before we spend Chromium on clips: a card with a collision
        #    would ship into the video AND the matching e-book figure (design §12).
        try:
            self.py("card_check.py", export, cwd=d, timeout=600)
        except RuntimeError as e:
            raise EngineFlag(
                "A card page has a layout collision and must not be rendered — it "
                "would ship into the video and the matching e-book figure. Each "
                "problem below names the elements and the overlap.\n"
                f"{str(e)[-900:]}")
        # 4. render every page to a clip
        self.py("render_cards_batch.py", export, d / "overlay/clips", cwd=d)
        epj = self.epjson(ep)
        ids = [c["id"] for c in epj["cards"]]
        clips = [str(self._clip(ep, cid)) for cid in ids]    # verifies every card landed
        # 5. THE REVIEW IS NO LONGER RAISED HERE. It moved to step_cards_render in
        #    engine.py (3 Aug 2026) so the preview's public URL can be written into
        #    build_state BEFORE the flag interrupts the step — a flag raised from
        #    inside this method returns nothing, so the engine never got the chance
        #    to record where the picture lives.
        return clips

    def title_placement_review_for(self, ep, url=None):
        """Raise the placement review for this episode, if it has a title card."""
        d = self.dir(ep)
        png = d / "overlay/export/title-preview.png"
        if not png.is_file():
            return
        title_placement_review(d, png, url)

    def publish_title_preview(self, ep) -> str | None:
        """Put the title-card preview somewhere a BROWSER can open it.

        The review flag used to carry `G:\\My Drive\\…\\title-preview.png`. Hugh has no
        Windows machine with G: mounted, so the one flag in the build designed to be
        answered by looking at a picture could only be answered at this desk. This
        publishes it to the same public episode-assets bucket the cover A/B choices
        already use — no new mechanism, no schema change, and the URL is VERIFIED
        reachable by _publish_asset before it is handed back.

        Returns None (rather than raising) when there is no TITLE card or no clip:
        a missing preview must not become a second failure on top of the first.
        """
        d = self.dir(ep)
        try:
            epj = self.epjson(ep)
            if "TITLE" not in [c["id"] for c in epj.get("cards", [])]:
                return None
            png = title_preview(d, self._clip(ep, "TITLE"))
        except (EngineFlag, RuntimeError, OSError, KeyError):
            return None
        return self._publish_asset(png, f"{ep_folder(ep)}/title-preview.png")

    def poll_heygen(self, ep, polls_so_far):
        """The render is a HUMAN step; we only pick up the finished master via
        the API video_url (the ~189 kbps master — never the web download)."""
        d = self.dir(ep)
        master = d / "renders/presenter-master.mp4"
        if not master.is_file():
            self._heygen_fetch(ep, master)         # returns only when downloaded
        print(f"    {trim_master_lead_in(master)}")
        # STANDING STEP, immediately after the trim (Jodie, 29 Jul 2026). Everything
        # downstream — card leads, the midroll anchor, b-roll offsets, the shot map
        # and the checks that grade them — derives from a transcript, so the good one
        # must exist BEFORE anything can reach for the constructed one. Same move as
        # the standing midroll chip: take what works and make it standing.
        print(f"    {align_to_script(d)}")
        kbps = self._audio_kbps(master)
        # THE FLOOR IS 180 AND IT STAYS 180. An episode may raise a documented
        # exception in its OWN file — never by moving this number (Jodie, 5 Aug 2026,
        # EP16). Measured for reference: EP14 and EP15 masters are both 189.4 kbps.
        floor, why = 180.0, ""
        build = (self.epjson(ep).get("build") or {})
        if "audio_kbps_floor" in build:
            why = str(build.get("_audio_kbps_floor_why") or "").strip()
            if not why:
                # ⚠️ THE REASON IS NOT OPTIONAL. An exception that can exist without a
                # written reason becomes a silent normal — the next author copies the
                # key, nobody remembers why, and the standard has quietly moved.
                raise EngineFlag(
                    "episode.json sets build.audio_kbps_floor but gives no reason, so "
                    "I have not applied it. Lowering the audio standard for one episode "
                    "is allowed; doing it without writing down WHY is not, because the "
                    "next episode copies the key and nobody remembers. Add "
                    "build._audio_kbps_floor_why explaining why THIS episode's master "
                    "is allowed below the standard, then clear this flag.")
            floor = float(build["audio_kbps_floor"])
        if kbps and kbps < floor:
            raise EngineFlag(
                f"The presenter master's audio is {kbps:.0f} kbps — below the "
                f"{floor:.0f} kbps floor (the locked API standard is ~189). It was "
                "probably saved via the web-app Download button. Re-pull it via the "
                "API video_url, then clear this flag. If the API copy is unusable and "
                "this episode has to ship on a lower-bitrate master, that is a decision "
                "for Jodie: it needs build.audio_kbps_floor AND "
                "build._audio_kbps_floor_why in docs/episode.json, written down.")
        if kbps and floor < 180:
            # A USED EXCEPTION MUST BE VISIBLE IN THE RECORD, not only in the input
            # file — otherwise the run log shows a clean pass and the standard looks
            # intact when it was deliberately set aside.
            print(f"    ⚠️ AUDIO BELOW THE STANDARD, ALLOWED BY A WRITTEN EXCEPTION: "
                  f"{kbps:.0f} kbps against the locked 180 floor; this episode sets "
                  f"{floor:.0f}. Reason: {why[:400]}")
        return str(master)

    def _heygen_fetch(self, ep, master: Path):
        key = self._env("HEYGEN_API_KEY")
        vid = ep.get("heygen_video_id")
        if not vid:                        # fall back to poll-by-project-name
            # 🔴 E20, LOGGED ON EP15 AND STILL BITING ON EP19. The rail does not record
            # the id of the thing it PAID FOR: nothing in this repo ever wrote
            # heygen_video_id — the schema says "engine | HeyGen id once picked up" and
            # the engine only ever READ it. So the id stayed null on every episode, and
            # the render was found by listing 100 videos and matching a TITLE.
            #     It works, and it is a guess. On EP19 Jodie could see a finished render
            # and the board showed nothing, which made a 10-second question into an
            # investigation. The named danger is worse than that: "Part 1 / Part 2 of the
            # same article are coming, and at 300 episodes titles will collide. The
            # failure then is not 'not found' — it is THE WRONG EPISODE'S RENDER,
            # silently." EP19 is a Part 1.
            #     The backlog's ideal fix — save the id when the job is created — is not
            # available to us: the render is started BY A HUMAN in HeyGen's own UI, which
            # is why there is no id to save. So: resolve by name ONCE, REFUSE TO GUESS
            # between two, and write the id down the moment it is known.
            name = ep.get("heygen_name") or ""
            req = urllib.request.Request(
                "https://api.heygen.com/v1/video.list?limit=100", headers={"x-api-key": key})
            with urllib.request.urlopen(req, timeout=30) as r:
                vids = json.load(r).get("data", {}).get("videos", [])
            hits = [v for v in vids if name and name in (v.get("video_title") or "")
                    and v.get("status") == "completed"]
            if not hits:
                raise RuntimeError(f"no completed HeyGen render named {name!r} yet")
            if len(hits) > 1:
                # TWO PAID RENDERS AND NO WAY TO TELL WHICH IS THE APPROVED ONE. Taking
                # the newest would be a guess about which one a human meant to keep, and
                # the cost of guessing wrong is the whole episode narrated by the wrong
                # take. A human names it; the id then makes it permanent.
                listed = "\n".join(
                    f"    {v['video_id']}  created {v.get('created_at')}  "
                    f"{(v.get('video_title') or '')[:60]!r}" for v in hits)
                raise EngineFlag(
                    f"There are {len(hits)} completed HeyGen renders matching "
                    f"{name!r}, and I will not guess which one this episode should "
                    f"use — picking wrong means the whole video is the wrong take.\n"
                    f"{listed}\n"
                    f"Put the right one in the episode's heygen_video_id on the rail, "
                    f"then clear this flag. Nothing has been downloaded.")
            vid = hits[0]["video_id"]
            # WRITE IT DOWN NOW. This is the whole point: the next reader of this
            # episode — a person, the board, a re-run after a crash — gets an id
            # instead of repeating the search, and the title stops being load-bearing.
            try:
                import rail
                if ep.get("id"):
                    rail.set_fields(ep["id"], {"heygen_video_id": vid})
                    ep["heygen_video_id"] = vid
                    print(f"    recorded heygen_video_id={vid} on the rail "
                          f"(resolved by title — E20)")
            except Exception as e:                                    # noqa: BLE001
                # Never lose a good render over bookkeeping.
                print(f"    ⚠️ could not record heygen_video_id on the rail: {e}")
        req = urllib.request.Request(
            f"https://api.heygen.com/v1/video_status.get?video_id={vid}",
            headers={"x-api-key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            url = json.load(r).get("data", {}).get("video_url")
        if not url:
            raise RuntimeError("HeyGen render found but no video_url yet")
        self._download_exact(url, master)

    @staticmethod
    def _download_exact(url: str, dest: Path, attempts: int = 3):
        """Download, and refuse to promote a short file to THE MASTER. (E22)

        ⚠️ THIS USED TO BE `copyfileobj` STRAIGHT INTO `.part`, THEN `rename`, WITH NO
        LENGTH CHECK — and a connection that drops mid-transfer ends the copy WITHOUT
        RAISING, so the short file became `presenter-master.mp4`.

        EP15, 4 Aug 2026: HeyGen stated **114,395,315 bytes**; **78,947,138** landed.
        Gordon stopped mid-word at 9:10 of a "13:31" file. **Every other check passed**,
        because an mp4 written with `faststart` carries `moov` at the FRONT, so ffprobe
        reads the full intended duration out of a file whose tail never arrived.
        > A FILE THAT IS THE RIGHT LENGTH IS NOT THE RIGHT FILE.
        > Duration is METADATA. The byte count is the truth — and the server states it.

        And the 35 MB gap had already been SEEN and explained away as re-encoding,
        *because the duration matched*. An observation you explain away is worse than
        one you never made: it leaves you confident. Hence a machine check, not care.
        """
        # 🔴 COUNT WHAT WE RECEIVED. DO NOT ASK THE FILESYSTEM.
        #
        # ══ EP18, 8 Aug 2026 — THIS GUARD FAILED A PERFECT FILE, THREE TIMES ══
        # covers_ab halted with "9,629,496 stated, 9,437,184 arrived" on every
        # attempt, on good home internet. Jodie spotted what made it diagnosable:
        # a dropped connection truncates at a DIFFERENT point each time, and
        # 9,437,184 is EXACTLY 9 MiB. Deterministic, and on a round binary
        # boundary — that is a buffer, not a network.
        #
        # MEASURED, both sides: fetching the same URL returns all 9,629,496 bytes
        # twice, byte-identical. Writing it to C: and stat-ing immediately gives
        # 9,629,496. Writing it to G: and stat-ing immediately gives 9,437,184 —
        # and 9,629,496 three seconds later, with the bytes on disk complete and
        # the sha256 matching the source.
        #     GOOGLE DRIVE'S VIRTUAL FILESYSTEM REPORTS SIZE LAZILY.
        # `shutil.copyfileobj` + `tmp.stat().st_size` asked a filesystem that had
        # not finished thinking, and believed it.
        #
        # ⚠️ AND IT IS THE EXACT INVERSE OF THE FAULT IT WAS BUILT FOR. EP15: a
        # genuinely short file that LOOKED complete. EP18: a complete file that
        # LOOKED short. Both are the same root — trusting something that reports
        # ON the artefact instead of the artefact itself. `stat()` is a proxy.
        # The bytes we counted through our own hands are not.
        #
        # 🔒 THE ORIGINAL GUARANTEE IS UNCHANGED. EP15's master would still be
        # refused: the read stops early, so the running total stops early too.
        # This only stops the filesystem's lag being read as a short download.
        # ── E-c: A DROPPED CONNECTION IS A TRANSIENT. THE MACHINE RETRIES IT. ──
        # Every flag this function ever raised said "retrying is the right move and
        # usually works" — and then asked a HUMAN to press the button that does it.
        # That is a chore, not a decision, and automation eats chores. The bound is
        # what keeps it honest: three verified attempts, then a human, so a genuinely
        # broken URL cannot spin. Nothing is re-charged — the render already exists.
        tmp = dest.with_suffix(".part")
        why = None
        for attempt in range(1, attempts + 1):
            got, stated = 0, None
            try:
                with urllib.request.urlopen(url, timeout=600) as r:
                    stated = r.headers.get("Content-Length")
                    stated = int(stated) if stated and stated.isdigit() else None
                    with open(tmp, "wb") as f:
                        while True:
                            chunk = r.read(1 << 20)
                            if not chunk:
                                break
                            f.write(chunk)
                            got += len(chunk)
            except Exception as e:                                    # noqa: BLE001
                why = (f"the connection failed ({type(e).__name__}: {e})", None, None)
            else:
                if stated is not None and got != stated:
                    why = ("the download stopped early", stated, got)
                elif stated is None and got == 0:
                    why = ("the download produced an empty file and the server did "
                           "not say how big it should have been", None, 0)
                else:
                    tmp.replace(dest)
                    if attempt > 1:
                        print(f"    download recovered on attempt {attempt} of "
                              f"{attempts} — {got:,} bytes, counted in")
                    return
            tmp.unlink(missing_ok=True)
            if attempt < attempts:
                wait = 5 * attempt
                print(f"    {why[0]} (attempt {attempt} of {attempts}) — "
                      f"retrying in {wait}s")
                time.sleep(wait)

        head, stated, got = why
        if stated is not None:
            short = stated - got
            raise EngineFlag(
                f"A download kept stopping early, so I have not kept it. I tried "
                f"{attempts} times. The server said the file is {stated:,} bytes and "
                f"only {got:,} arrived — {short:,} bytes short "
                f"({short / stated:.0%} of it missing).\n\n"
                "This matters more than it looks: a part-downloaded video still PLAYS, "
                "and still reports its full length, so it can look completely normal "
                "while the end of it is silent. Nothing has been charged again. If it "
                "keeps failing the connection is the thing to look at, not the render.")
        raise EngineFlag(
            f"A download failed {attempts} times and nothing usable arrived — {head}. "
            "Nothing has been kept and nothing has been charged again.")

    def _env(self, name):
        env = self.pp / ".env"
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
        raise EngineFlag(f"{name} is missing from PP Videos/.env — add it, then clear this flag.")

    def build_shot_map(self, ep) -> str:
        d = self.dir(ep)
        self.py("build_shot_map.py", d / "renders/presenter-master.mp4",
                d / "docs/spoken-words.txt", d / "renders", cwd=d)
        sm = d / "renders/shot-map.json"
        if not sm.is_file():
            raise RuntimeError("build_shot_map ran but renders/shot-map.json is missing")
        # A2 — DERIVE THE WINDOWS HERE, WHERE THE SRT AND THE SHOT MAP BOTH EXIST AND
        # NOTHING HAS USED THEM YET.
        #
        # derive_card_timings.py said "NOT WIRED INTO THE ENGINE. Run by hand." for
        # three episodes. Nobody ran it on EP13, so nine of thirteen cards entered
        # BEFORE their spoken cue — C1 by 9.6 seconds. A hand-run step is one Hugh
        # cannot perform at all, and it gets skipped exactly when it matters most:
        # after a long build, when everyone is looking at the render.
        print(f"    {derive_timings(d)}")
        return str(sm)

    def make_covers_ab(self, ep):
        """The two cover heroes, made UPFRONT in the gens-first batch so the pick
        reaches the operator DURING the render window (R7, 26 Jul 2026) — the
        build never parks mid-run on 'no e-book cover, needs a look'.

        Missing heroes are generated (previewed, ~2 credits each); staged ones are
        used as-is. Both are then PUBLISHED to Supabase storage, because the board
        renders https URLs only — local paths show as 'No cover yet' (EP09)."""
        d = self.dir(ep)
        hero_a, hero_b, active = self._hero_paths(ep)
        want = [(k, p) for k, p in (("hero_A", hero_a), ("hero_B", hero_b))
                if not p.is_file()]
        if want:
            self._generate_heroes(ep, want)
        if not active.is_file():
            shutil.copyfile(hero_a, active)        # A is active until a pick lands
        a, b = d / "thumbnail/cover-A.png", d / "thumbnail/cover-B.png"
        a.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(hero_a, a)
        shutil.copyfile(hero_b, b)
        folder = ep_folder(ep)
        return (self._publish_asset(a, f"{folder}/cover-A.png"),
                self._publish_asset(b, f"{folder}/cover-B.png"))

    # WHAT EACH KIND OF FILE IS, ASKED OF THE FILE ITSELF. A caller-supplied MIME
    # would be a list somebody maintains, and the one that mattered would be the
    # one nobody updated — fault #7. The suffix already knows.
    #
    # 🔴 IT IS NOT DECORATION. Sent as image/png (which is what this did for every
    # upload until 7 Aug 2026), a PDF DOWNLOADS instead of OPENING, and the e-book
    # link Hugh is given behaves differently from the one he was promised. The
    # upload succeeds either way, which is why it needs asserting rather than
    # assuming.
    CONTENT_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".srt": "text/plain; charset=utf-8",
    }

    def _publish_asset(self, local: Path, obj: str) -> str:
        """Upload to the public episode-assets bucket and return the https URL —
        VERIFIED reachable AND verified to be SERVED AS THE RIGHT KIND OF THING,
        so a cover that wouldn't show on the board, or an e-book that downloads
        instead of opening, flags instead of passing quietly."""
        ctype = self.CONTENT_TYPES.get(local.suffix.lower())
        if ctype is None:
            raise EngineFlag(
                f"I don't know how to publish a {local.suffix or 'file with no'} "
                f"extension to the web, so {local.name} was NOT uploaded. Nothing "
                "is broken and nothing was lost — the file is still on the drive. "
                "Tell whoever looks after the engine which kind of file this is.")
        base = self._env("SUPABASE_URL").rstrip("/")
        key = self._env("SUPABASE_SERVICE_ROLE_KEY")
        req = urllib.request.Request(
            f"{base}/storage/v1/object/episode-assets/{obj}",
            data=local.read_bytes(), method="POST",
            headers={"Authorization": f"Bearer {key}", "apikey": key,
                     "Content-Type": ctype, "x-upsert": "true"})
        with urllib.request.urlopen(req, timeout=300) as r:
            r.read()
        pub = f"{base}/storage/v1/object/public/episode-assets/{obj}"
        with urllib.request.urlopen(pub, timeout=60) as r:      # visibility check
            served = (r.headers.get("Content-Type") or "").split(";")[0].strip()
            if r.status != 200 or not r.read(64):
                raise EngineFlag(
                    f"Published {obj} but the public URL doesn't resolve — the board "
                    "can't show it. Check the episode-assets bucket, then clear this flag.")
        # ASSERT WHAT A PERSON RECEIVES, NOT WHAT WE SENT. The upload reports
        # success whatever it stored, and a PDF served as image/png still returns
        # 200 with bytes — it simply refuses to open in the browser.
        if served != ctype.split(";")[0]:
            raise EngineFlag(
                f"{local.name} is on the web but it is being served as {served!r} "
                f"instead of {ctype.split(';')[0]!r}. A browser would do the wrong "
                "thing with it — most likely download it rather than open it. "
                "Nothing else is affected; the file itself is fine.")
        return pub

    def publish_artefact(self, ep, local: Path | str) -> str:
        """Put a finished artefact on the web and return its https URL.

        The object name is DERIVED from the episode folder and the file's own
        name, so nothing has to be kept in step by hand and two episodes can
        never collide.
        """
        local = Path(local)
        return self._publish_asset(local, f"{ep_folder(ep)}/{local.name}")



    # ---- assembly: emit the graph, then run the documented ffmpeg command ---
    def _emit_graph(self, ep, which: str) -> Path:
        d = self.dir(ep)
        out = d / f"renders/pass{which}_graph.txt"
        r = self.py("assemble_episode.py", d / "docs/episode.json",
                    d / "renders/shot-map.json", which, cwd=d, timeout=120)
        out.write_text(r.stdout, encoding="utf-8")
        return out

    def assemble_passA(self, ep) -> str:
        d = self.dir(ep)
        graph = self._emit_graph(ep, "A")
        # input order: [0]=presenter, [1..N]=broll (broll[] order), [N+1]=logo chip
        cmd = ["ffmpeg", "-y", "-i", d / "renders/presenter-master.mp4"]
        for b in self.epjson(ep)["broll"]:
            cmd += ["-i", d / "broll" / f"{b['target']}.mp4"]
        cmd += ["-i", self.logo, "-filter_complex_script", graph, "-map", "[vout]",
                "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-an",
                d / "overlay/_passA.mp4"]
        self.run(cmd, cwd=d)
        return str(d / "overlay/_passA.mp4")

    def assemble_passB(self, ep) -> str:
        d = self.dir(ep)
        graph = self._emit_graph(ep, "B")
        epj = self.epjson(ep)
        standing = epj["build"].get("standing", {})
        content = [c["id"] for c in epj["cards"] if c["id"] not in standing.values()]
        # input order: [0]=_passA, [1..M]=content cards, then title/endcard/
        # warranty, presenter (audio), music — the layout the graphs are built for
        cmd = ["ffmpeg", "-y", "-i", d / "overlay/_passA.mp4"]
        for cid in content:
            cmd += ["-i", self._clip(ep, cid)]
        for role in ("title", "endcard", "warranty"):
            cmd += ["-i", self._clip(ep, standing[role])]
        cmd += ["-i", d / "renders/presenter-master.mp4", "-i", self.music]
        mid = epj["build"].get("midroll") or {}
        # A4 — A MISSING VALUE MUST NOT QUIETLY DROP THE CHIP.
        # This used to read `if mid.get("composite") and mid.get("clip")`, so a missing
        # `clip` silently assembled a video with NO like/subscribe chip at all — which
        # is exactly what EP13 shipped, while QC reported a chip present because it was
        # checking episode.json rather than the graph. A value nobody set is not a
        # decision to omit the chip; it is an omission, and omissions must be loud.
        if mid.get("composite"):
            clip_name = mid.get("clip")
            if not clip_name:
                raise EngineFlag(
                    "build.midroll.composite is true but build.midroll.clip is not set, so "
                    "the like/subscribe chip would be left out of the assembly entirely. "
                    "The chip is a STANDING asset — the same file every episode — so this "
                    "should have been filled in at authoring. Set it to "
                    "'midroll-lowerthird.mp4' and re-run.")
            clip_path = d / "overlay/clips" / clip_name
            if not clip_path.is_file():
                raise EngineFlag(
                    f"build.midroll.clip names {clip_name!r} but that file is not in "
                    f"overlay/clips. The chip is rendered from the standing "
                    f"assets/midroll-lowerthird.html — render it, then re-run.")
            cmd += ["-i", clip_path]                           # input MUSIC_IN+1
        # early e-book CTA — input MUSIC_IN+2 (or +1 with no chip). The ORDER here is
        # the contract with assemble_episode.py's `cta_in`; append, never insert.
        cta = epj["build"].get("early_cta") or {}
        if cta.get("clip"):
            # A4 again: a named asset that is not there must be LOUD, not dropped.
            cta_path = d / "overlay/clips" / cta["clip"]
            if not cta_path.is_file():
                raise EngineFlag(
                    f"build.early_cta.clip names {cta['clip']!r} but that file is not in "
                    f"overlay/clips, so the e-book card would be silently missing from the "
                    f"early call-to-action while the rest of the video assembled fine. "
                    f"Render the card, then re-run.")
            cmd += ["-i", cta_path]                            # input MUSIC_IN+2
        final = d / "output" / f"{ep_folder(ep)}-FINAL.mp4"
        cmd += ["-filter_complex_script", graph, "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", "-map_metadata", "-1", "-dn", final]
        self.run(cmd, cwd=d)
        # A7 — SHIP THE SRT A VIEWER ACTUALLY READS, AND SHIP THE GOOD ONE.
        #
        # This said `renders/generated.srt` — the CONSTRUCTED file, interpolated from
        # spoken-words.txt, measured at a mean 5.15s error and a worst of 12.32s. The
        # alignment work re-pointed derive_card_timings and qc_episode to aligned.srt
        # and MISSED THIS LINE, so EP13's shipped captions were byte-for-byte the bad
        # file while the good one sat in the same folder, written two hours earlier.
        #
        # THE GENERAL FORM, worth more than the fix: the change reached every
        # INSTRUMENT and missed the ARTEFACT. Ask of every fix — what does a human
        # actually receive, and did the fix reach it?
        src, why = _shipping_srt(d)
        if src:
            shutil.copyfile(src, final.with_suffix(".srt"))
        print(f"    captions: {why}")
        return str(final)

    def _qc_integrity_gate(self):
        """Refuse to run QC unless qc_episode.py is exactly what is committed.
        Returns the HEAD blob sha; on any doubt it never returns."""
        from gitgate import assert_committed
        return assert_committed(
            QC_REL,
            gate="QC INTEGRITY GATE",
            why="qc_episode.py decides whether an episode is good enough to ship.\n"
                "Rather than judge this episode by rules nobody has reviewed, the\n"
                "engine stops here. The build so far is checkpointed and resumes.",
            code=5)

    def self_qc(self, ep, final_path) -> str:
        self._qc_integrity_gate()      # runs before we shell out. No bypass.
        d = self.dir(ep)
        head = str(self.epjson(ep).get("build", {}).get("title_head", 7.0))
        # --episode arms the end-sequence + midroll checks (the EP08 lessons)
        self.py("qc_episode.py", final_path, d / "renders/shot-map.json",
                d / "output/qc", "--head", head,
                "--episode", d / "docs/episode.json", cwd=d, timeout=900)
        return str(d / "output/qc/QC-REPORT.md")

    def build_ebook(self, ep) -> str:
        """Figures from the cards, then the page, then the PDF.

        This was the LAST of the four halts Hugh could not clear. It used to say
        "Claude Code writes the e-book source … stage it, then clear this flag" to
        an operator working from a browser, and it stopped EP12 dead.

        The shell, the layout and the figures are now authored; the article BODY
        stays editorial and is written at script time, gated by the fidelity check
        rather than by a human read (see author_ebook.py's header).

        🆕 AND IF THE BODY IS NOT THERE, IT IS COMMISSIONED RATHER THAN DEMANDED.
        This is the point that halted EP17 with "the e-book article body is
        missing… it is written at SCRIPT time" — a true sentence and no help at
        all to somebody holding a browser. The engine knows the step, knows the
        file, knows the article and knows who writes it; it now asks, the same
        way `youtube_copy` does, and carries on.
        """
        d = self.dir(ep)
        print(f"    figures: {render_ebook_figures(d)}")
        if not (d / "ebook/body.html").is_file():
            import commission as com
            try:
                self._commission_ebook_body(ep, d)
            except com.CommissionHalt as h:
                # The writer's halt is already operator-shaped. The maintainer's
                # half goes to the run log — different readers, same event.
                if h.detail:
                    print(f"    (commission detail, for the log: "
                          f"{com._safe(h.detail)})", flush=True)
                raise EngineFlag(h.message)
        print(f"    {author_missing_ebook(d)}")
        src = d / "ebook" / f"{ep_folder(ep)}-ebook-source.html"
        if not src.exists():
            # Authoring succeeded but the page is not where it should be — that can
            # only be a hand-made source under a different name. Name what we
            # looked for rather than globbing and hoping.
            others = sorted(p.name for p in (d / "ebook").glob("*-ebook-source.html"))
            raise EngineFlag(
                f"The e-book source {src.name} is missing from {d.name}/ebook/."
                + (f" These are there instead: {', '.join(others)} — rename the one you "
                   f"want to {src.name}, or delete the stragglers." if others else
                   " Authoring reported success, so this is unexpected; check the ebook "
                   "folder."))
        out = d / "output" / f"{ep_folder(ep)}-ebook.pdf"
        self.py("build_ebook.py", src, out, cwd=d, timeout=600)
        return str(out)

    def build_thumbnail(self, ep) -> str:
        d = self.dir(ep)
        # Author it if it is missing — the third of the four halts Hugh could not
        # clear. It used to say "stage it, then clear this flag" to a browser.
        author_missing_thumbnail(d)
        pages = list((d / "thumbnail").glob("*thumbnail*.html"))
        if len(pages) != 1:
            raise EngineFlag(
                f"Expected exactly one *thumbnail*.html in {d.name}/thumbnail/, found "
                f"{len(pages)}. Authoring produces one; more than one means an older "
                "hand-made page is still there. Remove the one you do not want.")
        # Standard-template conformance guard (EP08 lesson): the standing thumbnail
        # recipe always carries the PP logo chip. A page without it was hand-rolled
        # off-template — flag rather than render a non-standard thumbnail.
        if "pp-logo-on-dark" not in pages[0].read_text(encoding="utf-8", errors="ignore"):
            raise EngineFlag(
                f"{pages[0].name} doesn't reference pp-logo-on-dark.png — it isn't built "
                "on the standing thumbnail template (assets/youtube-thumbnail-template.html). "
                "Rebuild it from the template, then clear this flag.")
        # THE HERO MUST BE THERE, and this is the guard that says so in words.
        #
        # TIGHTENED 28 Jul 2026. EP13 halted here with
        # `playwright TimeoutError: Page.wait_for_function: Timeout 60000ms exceeded`
        # because thumbnail/hero.png did not exist: render_still waits for every
        # image to reach naturalWidth > 0, a 404 never does, and the 60s timeout
        # became the guard BY ACCIDENT. The right outcome for the wrong reason, and
        # a stack trace no browser operator can act on.
        #
        # The check directly above is the same fault in miniature — it asks whether
        # the PAGE references the logo, which it does whether or not the horse is
        # there. Checking the markup is not checking the artefact. Same lesson as
        # the midroll luma probe.
        # A3 — DO THE COPY, DO NOT ASK A HUMAN TO DO IT.
        #
        # This used to raise a flag reading "It should be copied from
        # ebook/cover-src/hero.png" — asking a person to perform a copy the engine
        # ALREADY PERFORMS ITSELF three hundred lines earlier, at the cover pick
        # (`shutil.copyfile(pick, active)`). A browser operator cannot copy a file at
        # all, so it halted every episode and a human did it by hand on EP11 and EP12.
        # The flag even said so: "a rule with no enforcer". This is the enforcer.
        print(f"    {stage_thumbnail_hero(d)}")
        hero = d / "thumbnail/hero.png"
        if not hero.is_file():
            # Kept LOUD for the case the copy cannot fix: no picked hero to copy FROM.
            raise EngineFlag(
                f"The thumbnail hero is missing: {d.name}/thumbnail/hero.png\n"
                "THE THUMBNAIL HERO IS THE PICKED COVER HERO (Jodie, 28 Jul 2026) — the "
                "one chosen at the cover gate, already generated and already looked at. "
                f"The engine stages it automatically from {d.name}/ebook/cover-src/"
                "hero.png, but that file is not there either — so there is no picked "
                "hero to copy. Pick a cover first; that gate writes it.")
        out = d / "output" / f"{ep_folder(ep)}-thumbnail.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        self.py("render_still.py", pages[0], out, "1280", "720", cwd=d, timeout=300)
        thumbnail_placement_review(d, out)      # look at the picture, then clear
        return str(out)

    # -- the commission: the machine needs an AUTHOR, not an operator ---------
    #
    # `youtube_copy` halts EVERY episode with "Claude Code writes the copy".
    # Hugh cannot clear it: no amount of fixing checks removes a halt that needs
    # PROSE WRITTEN rather than a button pressed. It is one of exactly two such
    # halts (the other is the script itself), and it is the cheapest place to
    # prove the relay — small artefact, an acceptance test that already exists,
    # and it sits at the END of the build, so a bad output costs a retry rather
    # than a render. See docs/DESIGN-engine-commissions-the-script.md.
    #
    # ⏸ STILL OFF — and this is the honest state, not a forgotten switch.
    #
    # Jodie approved switching it on 6 Aug 2026 "once the assertion is in and
    # proved". The WALLET ASSERTION is in and proved. THE COMMISSION ITSELF IS
    # NOT: five real dry runs against EP16's own inputs, and not one of them
    # produced the artefact through this code path. The writer keeps returning
    # PROSE instead of the typed verdict and reporting that its write was
    # declined — while the identical argv, built by build_argv() itself and run
    # with a SHORT prompt, writes the file and returns a conforming verdict every
    # time. THE CAUSE IS NOT ESTABLISHED, so it is not named here.
    #
    #     WRITTEN AND REVIEWED IS NOT LANDED, AND NEITHER IS "IT ALMOST WORKED".
    #
    # Turning it on now would put a step that cannot finish in front of an
    # episode, and the person who met it could not clear it — which is the exact
    # thing this whole job exists to remove.
    #
    # ENGINE_COMMISSION=1 enables it for a controlled test. The default flips to
    # ON in code — never in an environment variable — the day a dry run produces
    # the file end to end. A capability that depends on somebody remembering to
    # export something disappears the first time the supervisor restarts from a
    # different terminal (CLAUDE.md fault #7 in a feature flag).
    #
    # WHAT IT COSTS: rate limits, not money — commissions run on Jodie's Max
    # SUBSCRIPTION (established 6 Aug). ENGINE_COMMISSION_BUDGET_USD is a
    # RUNAWAY-TURN bound, not a spend limit; the number it caps is notional.
    def _commission_youtube_copy(self, ep, d: Path):
        import commission as com

        def find():
            hits = sorted((d / "output").glob("*youtube*.txt"))
            return hits[0] if hits else None

        want = f"{ep_folder(ep)}-youtube.txt"
        # A BRIEF THAT POINTS, NEVER A BRIEF THAT RESTATES. The standards are
        # read from the files themselves via --add-dir, so one edit to the kit
        # reaches this writer and a working session at the same time. Copying
        # the rules in here would be fault #2 with extra steps.
        # 🔴 ABSOLUTE PATHS FOR THE STANDARDS, AND IT IS NOT A STYLE CHOICE.
        # The first live dry run came back saying the repo reads were "refused by
        # the sandbox". They were not: this prompt said `docs/youtube-metadata-kit.md`,
        # the writer resolved it against its cwd — THE EPISODE FOLDER, WHICH HAS
        # ITS OWN docs/ — found nothing, and went looking outside the sandbox,
        # where place scoping correctly refused it. The scoping worked perfectly;
        # the PATH WAS A GUESS. (An id is a promise, a name is a guess — fault #0a,
        # wearing a relative path.) Named absolutely, a probe read it first time.
        docs = REPO_DIR / "docs"
        prompt = (
            "You are writing the YouTube title and description for a Practical "
            "Punting episode. You are running inside this episode's folder.\n\n"
            "READ FIRST, and follow them exactly. These two are ABSOLUTE paths "
            "outside this folder — do not look for them relative to where you "
            "are, and note that this episode has a docs/ folder of its own that "
            "is a DIFFERENT place:\n"
            f"  - {docs / 'youtube-metadata-kit.md'} — the format and house rules\n"
            f"  - {docs / 'PP-STANDARDS.md'} — the YouTube title rule\n"
            "Then, relative to this episode folder:\n"
            "  - docs/episode.json — the decided packaging\n"
            "  - docs/spoken-words.txt — what the episode actually says\n\n"
            f"WRITE the copy to output/{want}\n\n"
            "ONE decided title on line 1. Do NOT offer alternatives: a file that "
            "asks a question is a halt wearing a text file's clothes, and the "
            "title is derived, not chosen.\n"
            "Leave the e-book link as the placeholder the kit specifies — a human "
            "pastes the real one at upload.\n\n"
            + com.verdict_instructions()
        )
        return com.commission(
            prompt=prompt,
            place=d,
            what="the YouTube words",
            find_artefact=find,
            add_dirs=[REPO_DIR / "docs"],
            budget_usd=float(os.environ.get("ENGINE_COMMISSION_BUDGET_USD", "10")),
            timeout=int(os.environ.get("ENGINE_COMMISSION_TIMEOUT", "900")),
            model=os.environ.get("ENGINE_COMMISSION_MODEL") or None,
        )

    # ---- the THIRD call site: episode.json and the cards --------------------
    #
    # This is the halt Jodie met three minutes after approving EP17's words:
    # "Create-inputs are missing… Claude Code writes these at the create step
    # (the create brain is Phase 4). Stage them, then clear this flag." A flag
    # that NAMES ITS OWN AUTHOR and then asks a human to go and fetch him.
    #
    # ⚠️ IT FIRES ONLY WHEN THE SCRIPT IS ALREADY THERE. episode.json's cues must
    # be literal substrings of the approved script, and its beats are the script's
    # paragraphs — writing it without one would be guessing at both. If the script
    # is missing too, this stands aside and the old flag still speaks: that is the
    # NEXT call site, not this one.
    # `followup` IS THE REPAIR LEG. It arrives from commission_with_repair()
    # carrying the gate's own words, and it is appended to THIS brief rather than
    # replacing it, because every repair is a FRESH SPAWN — there is no session to
    # resume, so the writer that fixes the file has never seen the instructions
    # that produced it. Building the follow-up here keeps the brief in one home;
    # commission.py knows what the checks SAID and nothing about episode.json.
    def _commission_episode_json(self, ep, d: Path, *, followup: str | None = None):
        import commission as com
        import preflight_episode_json as pj

        target = d / "docs/episode.json"

        def find():
            return target if target.is_file() else None

        # THE CAPTURE AND THE REFERENCES, NAMED ABSOLUTELY. A relative `docs/…`
        # resolves against the CWD, which IS the episode folder, and the episode
        # has its own docs/. That trap cost the first YouTube run a whole cycle
        # and reported itself as a permissions fault.
        #
        # 🔴 THE LOOKUP IS `find_capture()` AND NOT A GLOB WRITTEN HERE. It used to
        # be three lines of glob in this function; the script's precondition needs
        # the same answer, and two copies of a pattern is one value in two places
        # with the fix reaching one reader. The MESSAGE below stays this call
        # site's own — it is met at a different moment than the script's, and a
        # sentence that serves both is wrong for whichever it was not written for.
        capture = find_capture(self.pp, ep["ep_number"])
        if capture is None:
            raise EngineFlag(
                "I cannot write this episode's settings without the captured "
                "article they describe, and I could not find it. Nothing has "
                "been written.\n"
                "The capture is made when the script is written; it is not there.\n"
                "Retrying will not fix this until the capture is in place.")

        # THE SAME TWO REFERENCES E26 WILL JUDGE IT AGAINST — asked of E26's own
        # resolver, so the brief cannot point at one pair while the gate uses
        # another. Showing real files beats describing a schema.
        refs = []
        for n in range(int(ep["ep_number"]) - 1, 0, -1):
            if len(refs) == 2:
                break
            try:
                p = pj.ep_dir(n) / "docs/episode.json"
                if p.is_file():
                    refs.append(p)
            except Exception:                                  # noqa: BLE001
                continue

        docs = REPO_DIR / "docs"
        prompt = (
            "You are writing episode.json for a Practical Punting episode — the "
            "settings file the whole build reads: the beats, the motion cards, "
            "the b-roll, the cover and thumbnail wording and the e-book "
            "declarations. You are running inside this episode's folder.\n\n"
            "READ FIRST. These are ABSOLUTE paths outside this folder — do not "
            "look for them relative to where you are, and note that this episode "
            "has a docs/ folder of its own that is a DIFFERENT place:\n"
            f"  - {capture} — THE ARTICLE. Every figure you put on a card must be "
            "traceable to a sentence between its ARTICLE TEXT markers.\n"
            f"  - {docs / 'PP-EPISODE-JSON-SPEC.md'} — the file's own contract\n"
            f"  - {docs / 'PP-STANDARDS.md'} — the house rules, §0a and the cards\n"
            + "".join(f"  - {p} — a REAL, SHIPPED example. This episode will be "
                      f"judged for missing keys and changed types against this "
                      f"file.\n" for p in refs)
            + "Then, relative to this episode folder:\n"
            "  - docs/spoken-words.txt — THE APPROVED SCRIPT. The beats ARE its "
            "paragraphs, in order, and every card cue must be a literal substring "
            "of it.\n\n"
            f"WRITE the settings to docs/episode.json\n\n"
            + _card_vocabulary_note() +
            "TRACE OR IT DOES NOT SHIP. Any value carrying a figure needs a "
            "trace{} entry quoting the SOURCE SENTENCE verbatim from the article, "
            "and the figure must actually appear in that sentence. A card once "
            "showed placings inferred from the order four horses were listed in; "
            "every automated check passed and it shipped. trace{} is what stops "
            "that.\n\n"
            "DO NOT INVENT. Never add a fact the article does not state, never "
            "correct one it does, and never round or tidy a figure. If something "
            "looks wrong it stands, and you say so in what_i_saw.\n\n"
            # 🔴 THE SAME RULE THE SCRIPT BRIEF CARRIES, ARRIVING HERE LATE.
            # It was written into _commission_script after five drafts in a row died
            # on a helpful tote conversion, and it worked: EP19's spoken words contain
            # no dollar price at all. Nobody put it in the CARD brief, so EP19 C8
            # shipped "$1.75 to $3.25" over the caption "in tote terms" — Jodie caught
            # it on the finished card, 9 Aug 2026.
            #     AND THE WORDING HAS TO DIFFER, which is why copying the script's
            # sentence would not have saved it. The script's rule is "never ADD a
            # figure the article does not state". Here the article DOES state the
            # conversion, in its own brackets — so that sentence does not forbid this
            # and a careful writer reading it would still put the dollars on the card.
            "AND NEVER PUT A CONVERTED PRICE ON A CARD, EVEN WHEN THE ARTICLE "
            "PRINTS THE CONVERSION ITSELF. Where the article gives odds and then "
            "glosses them — 'odds in the range 8/11 to 9/4 inclusive (that is, in "
            "tote terms, $1.75 to $3.25)' — the CARD carries the odds, 8/11 to 9/4. "
            "Not the dollars, and not 'in tote terms'. A 2004 UK fraction restated "
            "as a tote price is a number the viewer cannot check against anything "
            "they will meet today. The trace{} entry still quotes the WHOLE "
            "sentence, brackets and all: a trace is provenance, not words a viewer "
            "reads. (author_cards.py fails the build on this, so a card that "
            "converts will come back to you.)\n\n"
            + com.verdict_instructions()
        )
        if followup:
            # 🔴 FIX IN PLACE, DO NOT START AGAIN. A writer told only "this was
            # rejected" rewrites the whole 67 KB file and drags in a fresh set of
            # faults; the fault it was asked about is then fixed and two others
            # have appeared. Naming the file as ALREADY PRESENT and forbidding
            # unrequested change is what makes a repair converge.
            #
            # ⚠️ AND IT CANNOT LIE ITS WAY PAST THIS. commission()'s freshness
            # check compares the artefact's mtime against the START of this run,
            # so a writer that reads the complaint, decides the file is fine and
            # writes nothing gets a stale-artefact halt. The proof of a repair is
            # a NEW FILE, never a claim that one was made.
            prompt += (
                "\n\n"
                "======== AN EARLIER ATTEMPT AT THIS FILE WAS REJECTED ========\n"
                "docs/episode.json ALREADY EXISTS in this folder — it is your "
                "earlier attempt. READ IT FIRST, fix what is listed below, and "
                "write the corrected file back to docs/episode.json.\n"
                "Do NOT start again from nothing. Do NOT change anything the list "
                "does not mention: the rest of the file has already been checked "
                "and passed, and every change you make unasked is a new chance to "
                "break something that was right.\n\n"
                + followup
                + "\n\nThen return the verdict object as before."
            )
        verdict = com.commission(
            prompt=prompt,
            place=d,
            what="this episode's settings and cards",
            find_artefact=find,
            add_dirs=[REPO_DIR / "docs", capture.parent]
                     + [p.parent for p in refs],
            budget_usd=float(os.environ.get("ENGINE_COMMISSION_BUDGET_USD", "10")),
            # ⏱ 1800s, NOT THE 900 THE OTHER TWO USE — and the number is measured.
            # The first scratch run TIMED OUT at 900s. It had not stalled: it wrote
            # a complete 67 KB file at about EIGHTEEN MINUTES, so the ceiling cut
            # off a job that was working. This artefact is an order of magnitude
            # bigger than the other two — 27 beats, 16 cards each with content and
            # trace, 7 b-roll prompts, cover and thumbnail wording — and 900s was
            # a number carried over from a 2 KB one.
            # ⚠️ 1800 IS A BOUND WITH MARGIN, NOT A MEASUREMENT OF THE TYPICAL
            # CASE. One observation sets a floor, not a distribution. If a second
            # run lands near it, raise it on that evidence rather than on nerves.
            timeout=int(os.environ.get("ENGINE_COMMISSION_TIMEOUT_EPJSON", "1800")),
            model=os.environ.get("ENGINE_COMMISSION_MODEL") or None,
        )
        return verdict

    # ---- the FOURTH call site: THE SCRIPT ITSELF ----------------------------
    #
    # THE LAST HAND-OFF. The other three call sites fill halts INSIDE a build; this
    # one runs BEFORE the engine can even claim the episode, because claim_next
    # refuses anything without `script_read` — and "I've read the script"
    # presupposes a script exists. See docs/DESIGN-the-pre-claim-drafting-pass.md.
    #
    # 🔴 THE ARTEFACT IS A FILE; THE HOME IS THE RAIL. The writer writes
    # docs/spoken-words.txt — the same derived cache `_script_from_rail` rebuilds
    # every build — so commission()'s existence-and-freshness check works unchanged.
    # The caller then seats those words with rail.seat_script_if_empty(), which is
    # the only way they ever reach script_snapshot.
    #
    # ⚖️ AND WHAT DOES NOT CHANGE: Jodie still reads it and still ticks "I've read
    # the script". The machine drafts; she stays the judge. Automation eats chores,
    # never decisions (A12).
    def _commission_script(self, ep, d: Path, gate=None):
        """`gate()` -> list of blocker strings, EMPTY MEANS PASS.

        🔴 THE FEEDBACK LOOP, AND IT IS NOT A NEW MECHANISM. `commission_with_repair`
        has existed since the episode.json commission was built, on the reasoning that
        a checker that good is a set of instructions — feed it back to the writer. The
        SCRIPT commission never used it: it called plain `commission()`, the engine ran
        the fidelity gate afterwards, and the rejection went to the run log where the
        writer could not see it. So each attempt started from zero, made the same
        mistake, and burned a whole 15-minute drafting cycle doing it. EP19 lost SIX
        drafts that way — five to one tote conversion, and the sixth to something else
        entirely, with the writer never once told what it had done.

        ⚠️ THE GATE IS INJECTED, NOT REIMPLEMENTED. It is the same callable the build
        halts on, passed in by the caller — not a copy living here that can drift from
        it (fault #2). With no gate supplied the behaviour is exactly as before.
        """
        import commission as com

        nn = int(ep["ep_number"])
        capture = assert_capture_for_script(self.pp, nn)      # piece 2's precondition
        spoken = d / "docs/spoken-words.txt"

        def find():
            return spoken if spoken.is_file() else None

        # The episode folder may not exist yet — this runs before the build ever
        # touches it. Making it is not a decision, it is where the work goes.
        spoken.parent.mkdir(parents=True, exist_ok=True)

        # 🔴 EVERY SOURCE BY ABSOLUTE PATH, AND NEVER BY SKILL DISCOVERY.
        # Claude Code finds project skills from the directory the session STARTED
        # in. A commission starts in the EPISODE folder, so walking up finds
        # `G:\My Drive\PP Videos\.claude\skills\` — one signpost, and nothing for
        # pp-episode-script. Commit c7f4e77 records what that costs: a script
        # written without the v1.2 fidelity tightening, "silently absent".
        # A relative `docs/…` is the same trap wearing different clothes: it
        # resolves against the episode folder, which has its own docs/.
        skills = REPO_DIR / ".claude/skills"
        docs = REPO_DIR / "docs"
        prompt = (
            "You are writing the SPOKEN SCRIPT for a Practical Punting episode — "
            "the words Gordon says to camera, and nothing else. You are running "
            "inside this episode's folder.\n\n"
            "READ FIRST, all of them, and follow them exactly. These are ABSOLUTE "
            "paths outside this folder — do not look for them relative to where "
            "you are, and note that this episode has a docs/ folder of its own "
            "that is a DIFFERENT place:\n"
            f"  - {capture} — THE ARTICLE. This is what the episode is made of.\n"
            f"  - {skills / 'pp-episode-script/SKILL.md'} — the craft: the golden "
            "rule (0), who is talking (2), the process (3), and 4A-4K.\n"
            f"  - {skills / 'pp-my-audience-avatar/SKILL.md'} — WHO YOU ARE "
            "WRITING TO. One person, called Dave. Never 'punters in general'.\n"
            f"  - {docs / 'PP-STANDARDS.md'} — the governing standard. If it and "
            "anything else disagree, this wins.\n"
            f"  - {docs / 'midroll-line-pool.md'} — the midroll invitation is "
            "TAKEN from this pool, verbatim. You do not write it.\n"
            f"  - {docs / 'PP-operator-box-rule.md'} — how to word what_i_saw.\n\n"
            f"This is episode {nn}.\n\n"
            f"WRITE the spoken track to docs/spoken-words.txt\n\n"
            # ── THE RULE ABOVE ALL ────────────────────────────────────────────
            "======== THE RULE ABOVE ALL, AND IT OVERRIDES YOUR INSTINCTS ========\n"
            "THE ONLY ORIGINAL PROSE IN THE WHOLE SCRIPT IS: the opening framing "
            "line, the short transitions between beats, the midroll invitation, "
            "and the outro wind-down.\n"
            "EVERYTHING ELSE IS THE ARTICLE'S OWN SENTENCES. Lift them across, "
            "lightly tidied for the ear. Keep the author's actual phrasing wherever "
            "it will play aloud; reword only where the original genuinely will not "
            "lift to the spoken ear, and then as little as possible.\n"
            "A SCRIPT THAT PARAPHRASES THE ARTICLE'S BODY HAS FAILED, HOWEVER GOOD "
            "IT SOUNDS. A heavy rewrite is new, unapproved content and it drifts in "
            "meaning. Craft — hooks, loops, rhythm, signposting — is applied to how "
            "you PRESENT and SEQUENCE the article, never by rewriting its "
            "sentences, inventing facts, or reordering the argument.\n"
            "When craft pulls against fidelity, FIDELITY WINS.\n"
            "And never correct the article: not a figure that looks wrong, not a "
            "date, not a name. If something looks wrong it stands, and you say so "
            "in what_i_saw.\n"
            # 🔴 IN THE BRIEF, NOT ONLY IN THE SKILL. §4B forbids this and the writer
            # is told to read §4B — and it converted the odds anyway, on FIVE
            # consecutive drafts, because "never correct" does not read as "never
            # ADD" and helping an Australian tote audience feels like service, not
            # invention. The gate rejected all five and the bound exhausted twice.
            # A rule the reader has to go and find is not where the hand is.
            "AND NEVER ADD A FIGURE THE ARTICLE DOES NOT STATE — CONVERSION IS "
            "ADDITION. If the article says 8/11, say 'eight to eleven'. Do NOT also "
            "say '$1.75', 'one dollar seventy-five', or 'in tote terms…'. Fractional "
            "odds, decimal odds and tote prices are different notations, and "
            "translating between them asserts an arithmetic the author never "
            "printed. This is the single most common way this script has failed: "
            "five drafts in a row died on one helpful tote conversion. If a decimal "
            "price would genuinely help Dave, the article has to say it — otherwise "
            "it does not go in Gordon's mouth.\n\n"
            # ── the one instruction in the skill that does NOT apply ───────────
            "======== ONE OVERRIDE TO THE SKILL, RULED BY JODIE ========\n"
            "The skill's section 3 Step 2 tells you to run the article through a "
            "'signature concept finder'. DO NOT. There is no such step here.\n"
            "The hook comes from the AVATAR and the ARTICLE directly: find Dave's "
            "wound in this article — the thing he has already tried and failed at, "
            "or the thing he believes that is costing him — and open on it, in his "
            "own language, then let the article answer it.\n\n"
            "HOW YOUR WORK WILL BE JUDGED, so you can meet it exactly:\n"
            "  - NUMBERS AS WORDS. A bare numeral anywhere in the spoken track is a "
            "hard failure — the voice engine guesses and guesses wrong. Write the "
            "words you want to hear (section 4B).\n"
            "  - NO PRODUCTION-NOTES HEADER, no comment lines, no 'paste below this "
            "line' marker. The file holds what Gordon says out loud and nothing "
            "else: it is shown to a person as the script, and counted as the script.\n"
            "  - The midroll line must match the pool VERBATIM.\n"
            "  - The responsible-gambling line is word-for-word locked.\n\n"
            + com.verdict_instructions()
        )
        def _one(followup=None):
            return com.commission(
                # The followup is the gate's OWN WORDS, appended verbatim. The writer
                # is told what it actually did, not a paraphrase of it.
                prompt=prompt + (followup or ""),
                place=d,
                what="this episode's script",
                find_artefact=find,
                # The skills tree is added so the writer can READ it. It is still named
                # by absolute path above — --add-dir grants access, it does not tell
                # anybody where to look.
                add_dirs=[REPO_DIR / "docs", skills, capture.parent],
                budget_usd=float(os.environ.get("ENGINE_COMMISSION_BUDGET_USD", "10")),
                timeout=int(os.environ.get("ENGINE_COMMISSION_TIMEOUT_SCRIPT", "1200")),
                model=os.environ.get("ENGINE_COMMISSION_MODEL") or None,
            )

        if gate is None:
            return _one()
        return com.commission_with_repair(
            attempt=_one, gate=gate, what="this episode's script",
            attempts=int(os.environ.get("ENGINE_SCRIPT_REPAIRS", "3")))

    # ---- the SECOND call site: the e-book article body ----------------------
    #
    # THE THIRD OF THE THREE PLACES THE MACHINE NEEDS AN AUTHOR (Job Zero). It
    # halted EP17 last night at `ebook_pdf` with "the e-book article body is
    # missing… it is written at SCRIPT time" — true, and no help at all to
    # somebody holding a browser. Same shape as the YouTube copy: prose that has
    # to be WRITTEN, not a button to press.
    #
    # ⚠️ AND IT IS THE CHEAPEST SECOND USER, for one reason: the acceptance gate
    # ALREADY EXISTS AND IS THE STRICTEST ONE WE HAVE. `author_ebook --check-only`
    # hard-fails unless every bare <p> is a character-for-character reproduction
    # of a source paragraph, in order, folding nothing — not case, not quotes, not
    # dashes. A commission with a gate that good is a commission whose failure
    # mode is "halt", never "quietly wrong".
    def _commission_ebook_body(self, ep, d: Path):
        import commission as com
        import preflight_cards as pc

        body = d / "ebook/body.html"

        def find():
            return body if body.is_file() else None

        # THE CAPTURE, NAMED ABSOLUTELY. This is the fault the YouTube brief hit
        # on its first live run: a relative `docs/…` resolves against the CWD,
        # which IS THE EPISODE FOLDER, and the episode has its own docs/. The
        # writer then looked outside the sandbox and place scoping correctly
        # refused it — and reported "the sandbox refused my reads", which sent a
        # session hunting a permissions bug that did not exist. An id is a
        # promise; a relative path is a guess.
        epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
        rel = pc.capture_rel(epj)
        capture = (self.pp / rel) if rel else None
        if not capture or not capture.is_file():
            raise EngineFlag(
                "I cannot write the e-book without the captured article to copy "
                "from, and I could not find it. Nothing has been written.\n"
                "The episode's settings name the capture file; that file is not "
                "where it says it is.\n"
                "Retrying will not fix this until the capture is in place.")

        docs = REPO_DIR / "docs"
        prompt = (
            "You are writing the ARTICLE BODY of a Practical Punting e-book. You "
            "are running inside this episode's folder.\n\n"
            "READ FIRST, and follow them exactly. These are ABSOLUTE paths "
            "outside this folder — do not look for them relative to where you "
            "are, and note that this episode has a docs/ folder of its own that "
            "is a DIFFERENT place:\n"
            f"  - {capture} — THE ARTICLE. Everything between the "
            "'---- ARTICLE TEXT BEGINS ----' and '---- ARTICLE TEXT ENDS ----' "
            "markers, and nothing above or below them.\n"
            f"  - {docs / 'PP-STANDARDS.md'} — the E-book section: the class "
            "vocabulary you may use, and §0a on never improving the article.\n"
            "Then, relative to this episode folder:\n"
            "  - docs/episode.json — ebook.departures, ebook.omit_paragraphs and "
            "figures[], which decide what you may change and which figures exist\n\n"
            "WRITE the body to ebook/body.html\n\n"
            "THE ARTICLE BODY ONLY. No <html>, no <style>, no page setup, no "
            "cover, no marketing page, no warranty page — every one of those is "
            "standing furniture and a second copy makes the book print it twice.\n"
            "EVERY BARE <p> MUST BE THE ARTICLE'S OWN PARAGRAPH, CHARACTER FOR "
            "CHARACTER, IN ORDER. Copy them across and resist every instinct to "
            "improve them: do not fix a figure that looks wrong, tidy a date, "
            "correct a name or smooth an inconsistency. An oddity in the source "
            "is the author's and it stands.\n\n"
            + _ebook_vocabulary_note() +
            "HOW YOUR WORK WILL BE JUDGED, so you can meet it exactly. A machine "
            "compares every bare <p> against the article's paragraphs and folds "
            "NOTHING — not case, not curly quotes, not dashes, not punctuation, "
            "not whitespace inside a sentence. One changed character fails it and "
            "names the word. Anything you do not reproduce must be quoted "
            "verbatim in episode.json -> ebook.omit_paragraphs; there is no way "
            "to drop a paragraph silently.\n\n"
            + com.verdict_instructions()
        )
        verdict = com.commission(
            prompt=prompt,
            place=d,
            what="the e-book article body",
            find_artefact=find,
            add_dirs=[REPO_DIR / "docs", capture.parent],
            # 🚫 THE DEFAULT TOOLS, AND DELIBERATELY NO Bash.
            # The obvious move is to let the writer run `author_ebook --check-only`
            # itself and iterate. It is the wrong move: `--add-dir` scopes the FILE
            # tools to a place, and a shell is scoped to nothing — it can cd
            # anywhere and run anything, including git. That trades Jodie's
            # place-and-time rule for a convenience the design does not need,
            # because THE ENGINE RUNS THE GATE ITSELF below. A writer's "I checked
            # and it passed" would be a report, and this whole mechanism exists
            # because a report is not an artefact.
            budget_usd=float(os.environ.get("ENGINE_COMMISSION_BUDGET_USD", "10")),
            timeout=int(os.environ.get("ENGINE_COMMISSION_TIMEOUT", "900")),
            model=os.environ.get("ENGINE_COMMISSION_MODEL") or None,
        )
        # 🔴 THE FOURTH GATE, AND IT IS THE ONE THAT MATTERS HERE.
        # commission() already proved: a valid envelope, a typed verdict of ok,
        # and an artefact that EXISTS and is NEWER than the run. None of that
        # says the words are the ARTICLE'S words. The writer was asked to run
        # this itself — and "I ran it and it passed" is a report, exactly the
        # kind of proxy the whole design refuses. So it is run again, here, by
        # the engine, against the file on disk.
        check = subprocess.run(
            [sys.executable, str(SKILL_DIR / "scripts/author_ebook.py"),
             str(d / "docs/episode.json"), str(d / "ebook"), "--check-only"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180)
        if check.returncode:
            raise EngineFlag(
                "The e-book body was written but it does not reproduce the "
                "article exactly, so it has not been accepted. Nothing "
                "downstream will use it.\n"
                "The message below names the exact word where it departs.\n"
                + (check.stderr or check.stdout).strip()[-1200:])
        print(f"    fidelity gate: {(check.stdout or '').strip().splitlines()[-1]}")
        return verdict

    def save_youtube_copy(self, ep) -> str:
        import commission as com

        d = self.dir(ep)
        hits = list((d / "output").glob("*youtube*.txt"))
        # 🔴 ON BY DEFAULT, IN CODE, FOR THIS ONE STEP — 6 Aug 2026.
        # Jodie: "I want the youtube copy thing fixed please!"
        #
        # The comment above said the default flips ON "the day a dry run
        # produces the file end to end". It did: 6,492 bytes written through
        # the real path on EP17's own inputs, a conforming verdict, status ok,
        # unread_sources empty, and check_youtube_title passing on the result.
        # The five earlier failures were a MANGLED COMMAND LINE, not a writer
        # refusing to write — claude.CMD is a batch shim and cmd.exe ate the
        # brief along with --output-format, --json-schema and --allowedTools.
        # Fixed by commission.strip_prompt_from_argv(); the brief goes on stdin.
        #
        # DEFAULT-ON RATHER THAN AN EXPORT, deliberately: a capability that
        # depends on somebody remembering to set a variable disappears the
        # first time the supervisor restarts from a different terminal.
        # ENGINE_COMMISSION=0 is the off switch and stays.
        #
        # ⚠️ THIS STEP ONLY. The SCRIPT commission is not switched on by this
        # and has no call site yet — one place, proved, before any second one.
        enabled = os.environ.get("ENGINE_COMMISSION", "1") != "0"
        if not hits and enabled:
            try:
                v = self._commission_youtube_copy(ep, d)
            except com.CommissionHalt as h:
                # The writer's halt is ALREADY operator-shaped. The maintainer's
                # half goes to the run log — different readers, same event.
                if h.detail:
                    print(f"    (commission detail, for the log: "
                          f"{com._safe(h.detail)})", flush=True)
                raise EngineFlag(h.message)
            print(f"    commissioned copy cost ${v.get('_cost_usd', 0):.2f} "
                  "— record it against the design's $10-30 guess", flush=True)
            hits = list((d / "output").glob("*youtube*.txt"))
        if not hits:
            extra = ("" if enabled else
                     "\n\n(The studio can write this itself, but that has been "
                     "switched off for this run.)")
            raise EngineFlag(
                "The YouTube title/description file is missing. Claude Code writes the "
                "copy per docs/youtube-metadata-kit.md (Jodie's ruling, 26 Jul 2026 — "
                "ownership moved from Cowork to the build side; Jodie uploads). Save it "
                f"as {d.name}/output/{ep_folder(ep)}-youtube.txt, then clear this flag."
                + extra)
        # THE ACCEPTANCE TEST RUNS WHOEVER WROTE THE FILE. A commissioned draft
        # gets no easier a ride than a hand-written one — that is the whole
        # reason this is the cheapest place to prove the mechanism.
        check_youtube_title(d, hits[0])
        return str(hits[0])
