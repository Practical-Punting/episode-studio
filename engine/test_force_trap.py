"""test_force_trap.py — a data fix must actually reach the page.

THE FAULT (EP16, 5 Aug 2026). `author_cards.py` skipped any page that already
existed — "already generated, pass --force to redo" — and THE ENGINE NEVER
PASSES --force. So changing episode.json and clearing the flag re-checked the
STALE HTML and returned a byte-identical halt.

    A CORRECT FIX LOOKED LIKE A FAILED ONE, TWICE.

It is the nastiest item on the Job A list because it INVERTS THE EVIDENCE: the
natural next move is to undo a change that was right, or to hunt a second cause
that is not there. On EP16 a layout fix moved a box from (204,838) to (110,787)
and nothing showed it.

    THE CASE THAT PROVES THE FIX is `a changed card reaches the page`.
    Everything else here exists to stop the cure being worse than the disease:
    a bespoke page must still never be touched, and an unchanged card must
    still be a no-op.

Run: python engine/test_force_trap.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
REPO = ENGINE.parent
SCRIPT = REPO / ".claude/skills/pp-episode-production/scripts/author_cards.py"
FIXTURE = ENGINE / "testdata/ep16-cards-BEFORE-FIX.episode.json"

PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


def author(epj_path, out_dir, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(epj_path), str(out_dir), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300)


def first_generated_card(epj):
    """Ask the FILE which card to use — never hard-code an id. A test that names
    C4 breaks the day the episode is re-authored (the fuse in test_youtube_title)."""
    for c in epj.get("cards", []):
        if c.get("block") != "bespoke" and c.get("page"):
            return c
    return None


def main():
    if not FIXTURE.is_file():
        print(f"missing fixture: {FIXTURE}")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="pp-force-"))
    epj = json.loads(FIXTURE.read_text(encoding="utf-8"))

    # MIRROR THE REAL LAYOUT, established by reading source_article_text() rather
    # than guessing: episode.json sits at <root>/<EP>/docs/, and the article is
    # resolved against <root>/docs/ — the SHARED docs folder, not the episode's.
    # The folder name is deliberately NOT an episode name. This suite tripped
    # test_no_hardcoded_episode_paths on its first run — correctly: a literal
    # episode folder name in a test is a fuse waiting on the stage-8 rename,
    # even inside a temp directory. Nothing here depends on what it is called.
    # (And the reworded comment is not squeamishness: that lint matches on plain
    # source text, so a comment ABOUT the forbidden literal trips it too.)
    ep_home = tmp / "EPISODE" / "docs"
    ep_home.mkdir(parents=True)
    (tmp / "docs").mkdir()
    m = re.search(r"(docs/[\w\-.]+\.md)", epj.get("source", ""))
    # The Drive root comes from the environment, the way rail.py resolves it,
    # rather than being written out here a second time.
    pp = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))
    article_src = pp / m.group(1) if m else None
    if article_src and article_src.is_file():
        shutil.copy2(article_src, tmp / m.group(1))
    else:
        print(f"  !! source article not on disk ({article_src}); "
              "the write-path cases cannot run and are NOT proved.")
        return 1

    # The saved fixture is EP16's file as first written, so it HALTS on purpose.
    # Use it to prove the authoring guards still fire, then repair it enough to
    # exercise the write path.
    out0 = tmp / "halting"
    r = author(FIXTURE, out0)
    check("the broken EP16 fixture still HALTS authoring (guards intact)",
          r.returncode == 2, f"rc={r.returncode}")

    # Build the smallest valid episode this script will author: one card, from
    # whatever the fixture's own first generated card happens to be.
    card = first_generated_card(epj)
    if card is None:
        print("fixture has no generated cards")
        return 1

    epj_min = dict(epj)
    epj_min["cards"] = [card]
    src = ep_home / "episode.json"

    def write_epj(obj):
        src.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    write_epj(epj_min)
    out = tmp / "pages"
    r = author(src, out)
    page = out / card["page"]
    if r.returncode != 0 or not page.is_file():
        # The minimal file may still trip a guard; that is the fixture's nature,
        # not a fault in the fix. Say so plainly rather than reporting a pass.
        print("  !! could not author a single card from the fixture; "
              f"rc={r.returncode}")
        print("     " + (r.stderr or r.stdout).strip()[-400:])
        print("     SKIPPING the write-path cases — they are NOT proved.")
        print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} green (write path UNPROVEN)")
        return 1

    check("a first run authors the page", page.is_file())
    original = page.read_text(encoding="utf-8")

    # ---- THE CASE THAT PROVES THE FIX --------------------------------------
    # Change what the card SAYS, re-author with no --force, and require the
    # change to be on disk. This is the exact EP16 shape.
    # MUTATE WHAT THE CARD DISPLAYS, NOT WHAT IT MERELY RECORDS.
    # The first version of this test changed `headline` and reported the trap
    # still open. It was wrong: this card also carries `headline_display`, which
    # is the string that actually reaches the page, so the render was genuinely
    # identical and the skip was correct. A test that mutates a field the
    # renderer ignores proves nothing about whether a change can reach the page.
    changed = json.loads(json.dumps(epj_min))
    needle = "PP-FORCE-TRAP-PROOF"
    c0 = changed["cards"][0]
    display_keys = [k for k in ("headline_display", "eyebrow", "headline")
                    if isinstance(c0.get(k), str)]
    for k in display_keys:
        c0[k] = needle
    changed_key = ", ".join(display_keys) or "(none found)"
    write_epj(changed)

    r = author(src, out)
    after = page.read_text(encoding="utf-8")
    check(f"a changed card ({changed_key}) REACHES THE PAGE without --force",
          needle in after, "the stale page survived - the trap is still open")
    check("  and the page really did change on disk", after != original)
    check("  and the run SAYS it re-authored, so a fix cannot look like a no-op",
          "REDONE" in r.stdout or "re-authored" in r.stdout,
          f"stdout said: {r.stdout.strip()[-200:]}")

    # ---- and the cure must not be worse than the disease --------------------
    r2 = author(src, out)
    check("re-authoring an UNCHANGED card is a no-op",
          "left alone" in r2.stdout and needle in page.read_text(encoding="utf-8"))
    check("  and it says the card is unchanged, not that it needs --force",
          "unchanged" in r2.stdout and "pass --force" not in r2.stdout)

    # A bespoke page is hand-authored and must survive BOTH paths, including
    # --force, which is the one thing a blanket re-author would destroy.
    hand = "<html>HAND AUTHORED, no marker</html>"
    page.write_text(hand, encoding="utf-8")
    author(src, out)
    check("a hand-authored page is never overwritten", page.read_text(encoding="utf-8") == hand)
    author(src, out, "--force")
    check("  not even with --force", page.read_text(encoding="utf-8") == hand)

    # ---- THE TRAP HAD FOUR SIBLINGS, AND A HALF-CLOSED TRAP IS WORSE THAN AN
    # ---- OPEN ONE: somebody reads "the --force trap is fixed", trusts a cover
    # ---- rebuild, and gets a stale PNG. The fix creates the belief.
    #
    # This is a STATIC audit rather than five more end-to-end runs: each script
    # needs its own valid episode fixture and staged assets, and the thing that
    # actually went wrong is a single, identifiable code shape. So assert the
    # shape, in every authoring script, DERIVED by globbing author_*.py — no list
    # for anyone to maintain, so a sixth authoring script cannot be forgotten.
    print()
    scripts = sorted((REPO / ".claude/skills/pp-episode-production/scripts")
                     .glob("author_*.py"))
    check("there are authoring scripts to audit at all", len(scripts) >= 4,
          f"found {len(scripts)}")
    for s in scripts:
        src = s.read_text(encoding="utf-8")
        if "--force" not in src:
            continue
        # Ignore comments. The first version of this check matched the phrase
        # anywhere in the file and failed on the COMMENTS EXPLAINING THE FIX —
        # the same shape as the path lint tripping on a comment about the
        # literal it forbids. What matters is whether the script still TELLS a
        # human to pass --force, so look only at executable lines.
        code = "\n".join(ln for ln in src.splitlines()
                         if not ln.strip().startswith("#"))
        check(f"{s.name}: no longer tells anyone to pass --force",
              "pass --force to redo" not in code,
              "the skip message survives in executable code")
        check(f"{s.name}: decides by COMPARING the rendered page",
              re.search(r"==\s*page\b|page\s*==", src) is not None,
              "nothing compares the render against what is on disk")
        check(f"{s.name}: still protects a hand-authored page",
              "hand-authored" in src)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nforce trap: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
