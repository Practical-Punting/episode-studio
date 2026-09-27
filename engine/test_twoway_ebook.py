#!/usr/bin/env python3
"""test_twoway_ebook.py — the dialogue body reproduces, and the labels survive.

    python engine/test_twoway_ebook.py

Build spec §7 / build-order step 5. The e-book body of a two-way episode IS a dialogue.
`author_ebook` hard-fails unless every bare `<p>` reproduces a source paragraph character
for character, and a dialogue reproduces fine — what was missing was a STYLE for the
speaker label.

🔴 THE TWO THINGS THAT MUST BOTH BE TRUE AT ONCE, and which pull against each other:
  · `BB:` / `BM:` survive **exactly as printed** — never expanded to "BARRY MEADOW:",
    which is embellishment, not reproduction;
  · and the fidelity gate still passes, which means the marker may add a CLASS and
    nothing else. An inner `<span>` around the label is the tempting edit — it would let
    the label be coloured — and it is the one that reaches inside a bare `<p>`.

Proved against EP49's REAL captured body, not a fixture.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))

import author_ebook as ae                                        # noqa: E402
import twoway_beats as tb                                        # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR",
                                 str(pathlib.Path("G:/My Drive") / "PP Videos")))
PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name
          + (f"  <- {why}" if not cond and why else ""))


def capture_paras() -> list[str]:
    hits = sorted((PP / "docs").glob("EP49-source-article-*.md"))
    if not hits:
        return []
    import script_fidelity as sf
    body = hits[0].read_text(encoding="utf-8").split(sf.MARKER_BEGIN, 1)[1] \
        .split("---- ARTICLE TEXT ENDS ----", 1)[0]
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def main() -> int:
    paras = capture_paras()
    if not paras:
        check("EP49's capture is on this machine", False)
        print(f"\ntwo-way e-book: {len(PASS)} passed, {len(FAIL)} failed")
        return 1

    # The body exactly as author_ebook would receive it: every article paragraph a
    # bare <p>, which is what the fidelity gate demands.
    body = "\n".join(f"<p>{p}</p>" for p in paras if not p.startswith("**"))
    marked = ae.mark_speakers(body)

    print("-- THE LABELS SURVIVE, EXACTLY AS PRINTED --")
    for label in ("BB:", "BM:", "Barry Meadow:", "Brian Blackwell:"):
        check(f"  {label!r} is still in the body", label in marked)
    check("  nothing was expanded to a shouted name",
          "BARRY MEADOW:" not in marked and "BRIAN BLACKWELL:" not in marked)

    print("\n-- IT IS MARKUP, NOT WORDS --")
    stripped_before = re.sub(r"<[^>]+>", "", body)
    stripped_after = re.sub(r"<[^>]+>", "", marked)
    check("  strip the tags and the two bodies are character-for-character identical",
          stripped_before == stripped_after,
          f"{len(stripped_before)} vs {len(stripped_after)} chars")
    check("  no <span>, <b> or <em> was added inside any paragraph",
          not re.search(r"<(span|b|em|strong)\b", marked))
    check("  the only change is a class on the <p>",
          marked.count("<p") == body.count("<p")
          and marked.count("class=\"speaks") > 0)

    print("\n-- EVERY TURN IS MARKED, AND NOTHING ELSE IS --")
    turned = re.findall(r'<p class="speaks spk-([A-Z]+)"[^>]*>\s*([^<:]{0,40}:)', marked)
    codes = {c for c, _ in turned}
    check(f"  {len(turned)} paragraphs marked", len(turned) >= 10, f"{len(turned)}")
    check("  and they are BB and BM, derived from the labels themselves",
          codes == {"BB", "BM"}, f"{sorted(codes)}")
    # 🔴 THE FIRST TWO TURNS ARE LABELLED IN FULL, and a marker that knew only the
    # initials would have left them plain. This is the same trap step 1's splitter hit.
    check("  the full-name labels are marked too, not just the initials",
          any("Barry Meadow:" in t for _, t in turned)
          or any(re.search(r'spk-BM"[^>]*>\s*Barry Meadow:', marked) for _ in [1]),
          f"{[t for _, t in turned][:3]}")
    narr = [p for p in paras
            if not re.match(r"^(BB|BM|Barry Meadow|Brian Blackwell):", p)]
    for n in narr[:4]:
        frag = f"<p>{n}</p>"
        if frag in body:
            check(f"  a NARR paragraph is left plain: {n[:44]!r}", frag in marked)

    print("\n-- THE STYLE EXISTS AND CARRIES BOTH MEN --")
    tpl = (HERE.parent / ".claude/skills/pp-episode-production/assets"
           / "ebook-template.html").read_text(encoding="utf-8")
    check("  p.speaks is styled", "p.speaks {" in tpl or "p.speaks{" in tpl)
    check("  and each man has his own rule colour",
          "p.spk-BB" in tpl and "p.spk-BM" in tpl)
    check("  the label hangs in the gutter rather than being wrapped",
          "text-indent: -" in tpl)

    print("\n-- THE FIDELITY GATE IS UNTOUCHED BY ANY OF IT --")
    # The gate strips tags then compares to the source paragraph. Re-run its own
    # normalisation over every marked paragraph and check it still finds its source.
    norm = getattr(ae, "norm_para", None) or (lambda s: " ".join(
        re.sub(r"<[^>]+>", "", s).split()))
    srcs = {norm(p) for p in paras}
    bodies = re.findall(r"<p[^>]*>(.*?)</p>", marked, re.S)
    lost = [b[:60] for b in bodies if norm(b) not in srcs]
    check("  every marked paragraph still matches a source paragraph", not lost,
          f"{lost[:2]}")

    print(f"\ntwo-way e-book: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
