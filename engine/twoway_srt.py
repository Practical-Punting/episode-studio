#!/usr/bin/env python3
"""twoway_srt.py — the episode's delivered subtitle file.

    python engine/twoway_srt.py <ep_number> [--pp DIR] [--out FILE]

`renders/merged.srt` is the CONVERSATION's captions on the dialogue clock, tagged
`[BB]` / `[BM]`. What ships beside the video is the same captions on the FINISHED clock,
with the READERS' names on them — the names the audience knows.

🔴 TWO CLOCKS AGAIN, AND THE SHIFT IS THE WHOLE JOB. merged.srt starts at Gordon's first
word; the finished file puts the title card in front of it. Every cue moves by
`TITLE_HEAD_S`, once, here — the same conversion `twoway_end_sequence.place()` makes for
the graphics. CLAUDE.md fault 1b is a number that crossed between the two clocks without
saying so.

🔴 AND THE NAMES ARE THE READERS', NOT THE AUTHORS'. `[BB]` is Brian Blackwell's words
READ BY GORDON. The caption says GORDON, because that is who is speaking and the
on-screen chips, the e-book and the spoken open all say the same thing (build spec A7,
the honesty rule). Taken from `episode.json -> speakers[code].reader` so a third
presenter cannot inherit somebody else's name.

📌 WHY THIS IS A MODULE. It existed as scratch code in the 20 Sep session and the only
copy of it was that session. A step that lives in a temp folder is gone the day the
folder is cleared, and it cannot be tested or re-run — which is exactly the argument
that made `twoway_assemble` a module rather than a scratch script.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ep_paths                                                   # noqa: E402
import twoway_assemble as ta                                      # noqa: E402
import twoway_interleave as ti                                    # noqa: E402

PP = pathlib.Path("G:/My Drive/PP Videos")


def stamp(t: float) -> str:
    """SRT timecode. Milliseconds are TRUNCATED, not rounded, so a cue can never be
    stamped a millisecond ahead of the frame it belongs to."""
    if t < 0:
        t = 0.0
    ms = int(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build(ep_number: int, pp: pathlib.Path = PP) -> str:
    d = ep_paths.episode_dir(ep_number, pp)
    epj = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
    cues = ti.read_srt((d / "renders/merged.srt").read_text(encoding="utf-8"))
    readers = {c: (s.get("reader") or c).upper() for c, s in epj["speakers"].items()}
    head = ta.TITLE_HEAD_S

    out, n = [], 0
    for c in cues:
        text = c["text"]
        m = re.match(r"^\[(\w+)\]\s*(.*)$", text, re.S)
        if m:
            code, body = m.group(1), m.group(2)
            who = readers.get(code)
            if who is None:
                raise SystemExit(
                    f"merged.srt tags a cue `[{code}]` and episode.json -> speakers has "
                    f"no such code, so there is no reader name for it. Not guessing: a "
                    f"caption with the wrong name on it is worse than one with none.")
            text = f"{who}: {body}"
        n += 1
        out.append(f"{n}\n{stamp(c['start'] + head)} --> {stamp(c['end'] + head)}\n"
                   f"{text}\n")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ep_number", type=int)
    ap.add_argument("--pp", default=str(PP))
    ap.add_argument("--out")
    a = ap.parse_args()
    text = build(a.ep_number, pathlib.Path(a.pp))
    if not a.out:
        print(text)
        return 0
    p = pathlib.Path(a.out)
    # ⚠️ TEMP FILE THEN os.replace, never open-for-write over the original. A truncated
    # subtitle file looks like a shorter episode, and `write_text()` truncates BEFORE it
    # encodes — which is how PP-ATLAS.md once went to 0 bytes.
    #
    # 🔴 AND A COPY OF THE OLD ONE WHENEVER IT DIFFERS. The first run of this module
    # reported "CHANGED" and there was nothing left to compare against, so the report
    # was a fact with no explanation attached. A comparison you cannot follow up is
    # half a check.
    was = p.read_bytes() if p.is_file() else None
    tmp = p.with_suffix(p.suffix + ".tmp")
    # 🔴 CRLF, BECAUSE THAT IS WHAT THIS CHANNEL SHIPS. EP48's published subtitle file
    # is 605 CRLF and not one bare LF; the first run of this module wrote LF throughout
    # and changed the file by exactly its 591 line endings. SRT is a CRLF format by
    # convention and players are forgiving, which is precisely why a silent switch would
    # never have been noticed — measured against the published file, not assumed.
    tmp.write_text(text, encoding="utf-8", newline="\r\n")
    if was is not None and was != tmp.read_bytes():
        p.with_suffix(p.suffix + ".bak").write_bytes(was)
    os.replace(tmp, p)
    back = p.read_text(encoding="utf-8")
    print(f"wrote {p}  ({len(text):,} chars, {text.count(chr(10))} lines, "
          f"re-read {'ok' if back == text else 'MISMATCH'})")
    # 📌 The separators are built from `bytes([...])`, not from escapes inside an
    # f-string — the first version printed "0 CRLF, 0 bare LF" on a file that was
    # entirely CRLF, because `b'\r\n'` written inside an f-string reached the counter
    # as four literal characters. A diagnostic that lies is worse than none, and this
    # one would have been read as proof the CRLF fix had failed.
    b = p.read_bytes()
    crlf = b.count(bytes([13, 10]))
    print(f"  line endings: {crlf} CRLF, {b.count(bytes([10])) - crlf} bare LF "
          f"(EP48's published subtitle file is all CRLF)")
    if was is not None:
        same = was == b
        print(f"  against the previous file: "
              f"{'BYTE-IDENTICAL — the speech never moved' if same else 'CHANGED'}"
              + ("" if same else f" (previous kept as {p.name}.bak)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
