#!/usr/bin/env python3
"""twoway_run.py — drive a two-way episode through its run order, and stop only at Jodie's gates.

    python engine/twoway_run.py 57 [58 59]          run each episode as far as it can go
    python engine/twoway_run.py 57 58 59 --status   where each one is; changes nothing
    python engine/twoway_run.py 57 58 59 --clip     put the NEXT HeyGen script on the clipboard
    python engine/twoway_run.py --verdict 57 render_listen approved "her words, verbatim"
    python engine/twoway_run.py --verdict 57 cut_watch changes "her words" --change "fix 1" --change "fix 2"
    python engine/twoway_run.py --change-status 57 cut_watch 2 DONE      (OPEN / DONE / DROPPED)

Called by the repo's `/two-way` command (.claude/commands/two-way.md), which is how Jodie
starts it: she pastes the article on the board with the "two-person" tick, then types
`/two-way EP57` in Claude Code.

🔴 IT WORKS OUT WHERE IT IS FROM DISK, EVERY TIME. Nothing is remembered between runs
except what is written in the episode's own folder and on its rail row, so a restart (or
a new session that knows nothing) carries on exactly where the last one stopped. Each
step below has a DONE test that looks at files, and the first step that is not done is
the next thing to do.

THREE KINDS OF STEP:
  code    — this script runs it (an existing repo tool, never a rewrite of one).
  session — something only a Claude session can do (write the commission, the card pages,
            the e-book body; generate on Higgsfield through hf_guard; the fresh-eyes review).
            The runner says exactly what, and the done test checks it happened.
  gate    — JODIE'S. The runner stops, asks ONE plain question with the links she needs,
            and records the gate on the rail row (`twoway.gate`) so the board shows it.
            It never answers a gate itself. Her answer is recorded with --verdict, in her
            words; a verdict with changes keeps each change as its own OPEN item (the
            standing "split every verdict" rule), and the gate stays shut until none is OPEN.

THE STANDING RULINGS ARE FOLDED IN, NOT ASKED: Gordon reads Brian Blackwell, Steve reads
Barry Meadow; web addresses in the article are named, not read (substitutions drafted by
the standing rule); a NARR author bio is split off and soft hyphens stripped (twoway_split);
no cadence (the pool); Hugh only for words that break the approved pattern (the furniture
step refuses a different close); a list too long for a card shows what fits; stray render
words between sentences are cut with a join WAV (twoway_render_words + twoway_masters);
price is not a gate under 20 minutes; Higgsfield stays inside 110 credits (hf_guard).

It never presses Generate in HeyGen, never spends a Higgsfield credit itself, never
publishes. HeyGen is reached only to LIST and DOWNLOAD finished renders (pre-approved).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
SCRIPTS = REPO / ".claude/skills/pp-episode-production/scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

import ep_paths     # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
DRAFTS = "docs/two-way-words-drafts"
LOCAL_LOGS = pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home()))) / "pp-twoway-runs"
PY = [sys.executable, "-X", "utf8"]
SUBFOLDERS = ("broll", "docs", "ebook", "output", "overlay", "renders", "thumbnail")

SPEAKERS = {   # build spec A2; the readers are standing (Jodie) — never asked
    "BB": {"name": "Brian Blackwell", "role": "editor, Practical Punting", "reader": "Gordon",
           "template": "brian", "side": "left", "host": True},
    "BM": {"name": "Barry Meadow", "role": "US handicapper", "reader": "Steve",
           "template": "barry", "side": "right", "host": False},
}
TEMPLATE_NAMES = {"BB": "Gordon two-way small", "BM": "Barry test 2 small "}
"""The HeyGen TEMPLATE NAMES as they appear in HeyGen (Barry's has a real trailing space).
NAMES, never ids: the ids live only in docs/HEYGEN-HUMAN-STEP.md."""

GATES = {
    "words": "the new words",
    "render_paste": "the HeyGen pastes",
    "broll_cover": "the b-roll and cover picks",
    "render_listen": "the render listen",
    "cut_watch": "the cut",
    "join_listen": "the midroll listen",
    "title_thumbnail": "the title and thumbnail",
    "publish": "publishing",
}


class Stop(Exception):
    """The run stops here: a gate, a session step, a wait, or a fault."""

    def __init__(self, kind: str, step: str, message: str, gate: str | None = None):
        super().__init__(message)
        self.kind, self.step, self.message, self.gate = kind, step, message, gate


# ───────────────────────────────────────────────────────────── the episode ──

class Ep:
    def __init__(self, n: int, pp: pathlib.Path = PP, rail_row: dict | None = None,
                 offline: bool = False):
        self.n, self.pp, self.offline = n, pp, offline
        self.row = rail_row if rail_row is not None else (None if offline else _rail_row(n))
        hits = sorted(pp.glob(f"PP-EP{n:02d}-*"))
        self.dir = hits[0] if len(hits) == 1 else None
        if len(hits) > 1:
            raise Stop("fault", "folder", f"{len(hits)} folders for PP-EP{n:02d}: "
                       f"{[h.name for h in hits]}. One episode, one folder — fix by hand.")

    # paths
    def p(self, rel: str) -> pathlib.Path:
        if self.dir is None:
            raise Stop("fault", "folder", f"PP-EP{self.n:02d} has no folder yet.")
        return self.dir / rel

    @property
    def tag(self) -> str:
        return f"PP-EP{self.n:02d}"

    def capture(self) -> list[pathlib.Path]:
        return sorted((self.pp / "docs").glob(f"EP{self.n:02d}-source-article-*.md"))

    def epj(self) -> dict:
        f = self.p("docs/episode.json")
        return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}

    def gates(self) -> dict:
        f = self.p("docs/twoway-gates.json")
        return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}

    def save_gates(self, g: dict) -> None:
        _write_json(self.p("docs/twoway-gates.json"), g)

    def latest_cut(self) -> int:
        ks = [int(m.group(1)) for f in self.p("output").glob(f"{self.tag}-cut*.mp4")
              if (m := re.fullmatch(rf"{self.tag}-cut(\d+)\.mp4", f.name))]
        return max(ks, default=0)

    def passed(self, gate: str, cut: int | None = None) -> bool:
        v = self.gates().get(gate if cut is None else f"{gate}#{cut}")
        return bool(v) and v.get("verdict") == "approved" and not any(
            c.get("status") == "OPEN" for c in v.get("changes", []))


def _rail_row(n: int) -> dict | None:
    try:
        import rail
        rows = [r for r in rail.list_all() if r.get("ep_number") == n]
    except Exception as e:                                         # noqa: BLE001
        raise Stop("fault", "rail", f"could not read the rail: {e}")
    return rows[0] if rows else None


def _write_json(f: pathlib.Path, d) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, f)


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _run(ep: Ep, step: str, cmd: list, cwd: pathlib.Path | None = None, lock: str | None = None,
         ok_codes=(0,), timeout: int = 6 * 3600) -> int:
    """Run a repo tool; log to C: (a Drive remount once killed a log handle on G:), then copy."""
    LOCAL_LOGS.mkdir(parents=True, exist_ok=True)
    log = LOCAL_LOGS / f"{ep.tag}-{step}.log"
    print(f"  · {step}: {' '.join(str(c) for c in cmd[2:])[:160]}", flush=True)

    # Every tool finds the episodes through PP_VIDEOS_DIR (ep_paths), so the runner hands down
    # ITS root: a sandbox stays a sandbox, and no tool can wander to the real Drive by default.
    env = dict(os.environ, PP_VIDEOS_DIR=str(ep.pp), PYTHONIOENCODING="utf-8")

    def go() -> int:
        with open(log, "w", encoding="utf-8") as f:
            return subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT,
                                  cwd=str(cwd) if cwd else None, timeout=timeout,
                                  env=env).returncode
    if lock:
        import render_lock
        with render_lock.hold("PP", f"{ep.tag} {lock}"):
            rc = go()
    else:
        rc = go()
    if ep.dir is not None:
        dest = ep.dir / "output/run"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(log, dest / log.name)
    if rc not in ok_codes:
        tail = log.read_text(encoding="utf-8", errors="replace")[-1500:]
        raise Stop("fault", step, f"{step} failed (exit {rc}). The end of its log:\n{tail}\n"
                   f"Full log: {ep.dir / 'output/run' / log.name if ep.dir else log}")
    return rc


def _md5(f: pathlib.Path) -> str:
    return hashlib.md5(f.read_bytes()).hexdigest() if f.is_file() else ""


def _set_rail(ep: Ep, stage: int, step: str, gate: str | None, status: str | None = None,
              extra: dict | None = None) -> None:
    if ep.offline or not ep.row:
        return
    import rail
    tw = dict(ep.row.get("twoway") or {})
    if gate != tw.get("gate"):
        tw["gate_since"] = _now() if gate else None
    tw.update({"stage": stage, "step": step, "gate": gate,
               "readers": {c: s["reader"] for c, s in SPEAKERS.items()}})
    fields = {"twoway": tw}
    if status and ep.row.get("status") != status:
        fields["status"] = status
    if ep.dir is not None and ep.row.get("drive_folder") != ep.dir.name:
        fields["drive_folder"] = ep.dir.name
    fields.update(extra or {})
    rail.set_fields(ep.row["id"], fields)
    ep.row.update(fields)


# ─────────────────────────────────────────────────────── stage 1: the words ──

def slug_of(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".html")


def folder_name(n: int, url: str) -> str:
    """PP-EP56-Class-Improvement-and-Bias-Blues-Part-3 from …/class-improvement-…-part-3-20040108."""
    words = re.sub(r"-\d{8}$", "", slug_of(url)).split("-")
    small = {"a", "an", "and", "the", "of", "to", "in", "on", "at", "for", "or", "by"}
    out = [w if w.isdigit() else (w if (i and w in small) else w.capitalize())
           for i, w in enumerate(words)]
    return f"PP-EP{n:02d}-" + "-".join(out)


def part_number(url: str) -> int | None:
    m = re.search(r"part-(\d+)", slug_of(url))
    return int(m.group(1)) if m else None


def do_folder(ep: Ep) -> None:
    if not ep.row or not ep.row.get("source_url"):
        raise Stop("fault", "folder", f"{ep.tag} has no rail row with an article link. Paste the "
                   "article on the board first, with the two-person box ticked.")
    if ep.row.get("format") != "two-way":
        raise Stop("fault", "folder", f"{ep.tag} is on the rail as a SINGLE-presenter episode. "
                   "The runner only drives two-way rows; nothing has been made.")
    d = ep.pp / folder_name(ep.n, ep.row["source_url"])
    for s in SUBFOLDERS:
        (d / s).mkdir(parents=True, exist_ok=True)
    ep.dir = d
    print(f"  · made {d}")


ADDR = r"(?:https?://)?www\.[A-Za-z0-9\-]+(?:\.[A-Za-z]{2,})+(?:/[^\s)]*)?"
ADDR_SHAPES = [re.compile(r" \(" + ADDR + r"\)"), re.compile(r" at " + ADDR),
               re.compile(r", " + ADDR)]
SENT = re.compile(r"(?<=[.!?])\s+")


def draft_substitutions(turns: list[dict]) -> tuple[list[dict], list[str]]:
    """The standing rule (Jodie, 11 Nov 2026): NAME THE SITE, DROP THE ADDRESS. Only the three
    shapes EP56 met are drafted — " (www.x)", " at www.x", ", www.x"; any other shape is listed
    for a human. A NARR row is e-book only (it is never read aloud)."""
    subs, odd, k = [], [], 0
    for t in turns:
        for sent in SENT.split(t["text"]):
            if not re.search(ADDR, sent):
                continue
            hit = next((m for rx in ADDR_SHAPES for m in [rx.search(sent)] if m), None)
            if hit is None:
                odd.append(f"turn {t['n']} ({t['speaker']}): {sent[:120]}")
                continue
            k += 1
            sub = {"id": f"S{k}", "turn": t["n"], "speaker": t["speaker"], "find": hit.group(0),
                   "replace": "", "before": sent, "after": sent.replace(hit.group(0), "", 1),
                   "ruling": "standing rule (Jodie, 11 Nov 2026): name the site, drop the address; "
                             "drafted by twoway_run"}
            if t["speaker"] == "NARR":
                sub["scope"] = "ebook"
            subs.append(sub)
    return subs, odd


def do_split(ep: Ep) -> None:
    """turns.json ONLY, through the repo's own `twoway_split.split_turns` — as EP56's was.

    `twoway_split --write` also writes the scripts, and it (rightly) halts on a web address the
    reading would say aloud; but the substitutions that remove them can only be drafted FROM the
    turns. So the turns come first, the substitutions second, and the scripts are written by the
    furniture step from the reading. turns.json stays the article, verbatim."""
    import twoway_split as ts
    cap = ep.capture()
    turns, speakers, _narr = ts.split_turns(cap[0].read_text(encoding="utf-8"))
    if set(speakers) != set(SPEAKERS):
        raise Stop("fault", "split", f"the byline gives speakers {speakers}, not Brian Blackwell "
                   "and Barry Meadow. A different pair of writers is a new kind of two-way — ask Jodie.")
    body = json.dumps({"turns": turns}, indent=2, ensure_ascii=False) + "\n"
    f = ep.p("docs/turns.json")
    f.write_text(body, encoding="utf-8", newline="\n")
    if f.read_text(encoding="utf-8") != body:
        raise Stop("fault", "split", f"{f} did not read back as written.")
    print(f"  · {len(turns)} rows into turns.json")


def do_substitutions(ep: Ep) -> None:
    turns = json.loads(ep.p("docs/turns.json").read_text(encoding="utf-8"))["turns"]
    subs, odd = draft_substitutions(turns)
    if odd:
        raise Stop("session", "substitutions",
                   "The article has a web address in a shape the standing rule does not cover:\n  "
                   + "\n  ".join(odd) + "\nAdd it to docs/sanctioned-substitutions.json by hand "
                   "(name the site, drop the address), then run me again.")
    _write_json(ep.p("docs/sanctioned-substitutions.json"), {
        "episode": ep.tag,
        "ruling": "Jodie, 11 Nov 2026 (standing): NAME THE SITE, DROP THE ADDRESS.",
        "what_this_is": "SANCTIONED, PER-EPISODE substitutions, drafted by engine/twoway_run.py by "
                        "the standing rule. turns.json and the capture are not edited. Shown to "
                        "Jodie with the new words.",
        "new_words_for_hugh": "Only if Jodie says so (Hugh only for words that break the "
                              "approved pattern).",
        "substitutions": subs})
    print(f"  · {len(subs)} web address(es) dropped by the standing rule")


def subs_done(ep: Ep) -> bool:
    if ep.p("docs/sanctioned-substitutions.json").is_file():
        return True
    turns = json.loads(ep.p("docs/turns.json").read_text(encoding="utf-8"))["turns"]
    return not any(re.search(ADDR, t["text"]) for t in turns)


def do_episode_json(ep: Ep) -> None:
    e = ep.epj()
    e.setdefault("episode", f"EP{ep.n}")
    e["format"] = "two-way"
    e.setdefault("title", (ep.row or {}).get("title") or "")
    cap = ep.capture()
    e.setdefault("source", f"Captured to docs/{cap[0].name}." if cap else "")
    e.setdefault("spoken_words_file", "docs/spoken-words-BB.txt")
    e.setdefault("spoken_words_file_bm", "docs/spoken-words-BM.txt")
    e.setdefault("speakers", SPEAKERS)
    _write_json(ep.p("docs/episode.json"), e)


def words_file(ep: Ep) -> pathlib.Path:
    return ep.p(f"docs/EP{ep.n:02d}-new-words-APPROVED.md")


def do_words(ep: Ep) -> None:
    """THE HAND-OVER: Cowork writes docs/two-way-words-drafts/<Series>-Part-N-new-words-APPROVED.md;
    once its Status line says APPROVED, it is copied into the episode as EPnn-new-words-APPROVED.md."""
    part = part_number((ep.row or {}).get("source_url", ""))
    cands = sorted((ep.pp / DRAFTS).glob(f"*Part-{part}-new-words-APPROVED.md")) if part else []
    if len(cands) > 1:
        raise Stop("fault", "words", f"{len(cands)} approved-words files for Part {part}: "
                   f"{[c.name for c in cands]} — one only.")
    if cands:
        txt = cands[0].read_text(encoding="utf-8")
        status = next((ln for ln in txt.splitlines() if ln.lower().startswith("status:")), "")
        if "APPROVED" in status.upper():
            dest = words_file(ep)
            dest.write_text(txt, encoding="utf-8", newline="\n")
            if dest.read_text(encoding="utf-8") != txt:
                raise Stop("fault", "words", f"{dest} did not read back as written.")
            print(f"  · copied {cands[0].name} -> {dest.name}")
            return
    where = ep.pp / DRAFTS / f"…-Part-{part}-new-words-APPROVED.md"
    raise Stop("gate", "words",
               f"{ep.tag} is waiting for its new words (the open, Steve's handover, the CTA, the "
               f"midroll, the wind-down and the sign-off). Cowork writes them; when you approve "
               f"them, the file lands as\n    {where}\nwith a 'Status: APPROVED' line, and I "
               f"carry on from there.", gate="words")


# ─────────────────────────────────────────── stage 3: the renders, by hand ──

def render_title(ep: Ep, code: str) -> str:
    return f"{ep.tag}-{code}-full"


def do_render_sheet(ep: Ep) -> None:
    lines = [f"# {ep.tag} — THE TWO HEYGEN RENDERS (written by engine/twoway_run.py)", "",
             "> 🔒 Template and voice IDS are not here on purpose — they live only in the repo's",
             "> `docs\\HEYGEN-HUMAN-STEP.md`. This sheet names the templates.", "",
             f"Type `python engine\\twoway_run.py {ep.n} --clip` (or ask Claude) to put each script "
             "on your clipboard — ONE script, nothing else.", ""]
    man = ep.p("docs/script-manifest-BB.json")
    if man.is_file():
        import twoway_furniture as tf
        lid = json.loads(man.read_text(encoding="utf-8")).get("midroll_line_id")
        if lid:
            lines += [f"**The midroll in Gordon's script is pool line {lid}** (drawn from the "
                      f"approved pool):", f"> {tf.pool_lines().get(lid, '')}", ""]
    for code in ("BB", "BM"):
        sp = SPEAKERS[code]
        lines += [f"## {sp['reader']} — reading {sp['name']}", "",
                  f"| | |\n|---|---|\n| **Template** | **`{TEMPLATE_NAMES[code]}`** |",
                  f"| **Script** | `docs\\spoken-words-{code}.txt` (on the clipboard) |",
                  f"| **Title** | **`{render_title(ep, code)}`** |", "| **Captions** | **OFF** |", ""]
    lines += ["## THE STEPS, EACH TIME", "",
              "1. Open the template.",
              "2. **Clear the box first** — select everything in the script box and delete it.",
              "3. Paste (Ctrl+V). Click into the text, press Enter then Backspace — the preview MUST play.",
              "4. Type the Title exactly as above.", "5. Captions OFF (it cannot be undone).",
              "6. Generate.", ""]
    ep.p(f"docs/HEYGEN-RENDER-EP{ep.n:02d}.md").write_text("\n".join(lines), encoding="utf-8")


def _env(key: str) -> str:
    for ln in (PP / ".env").read_text(encoding="utf-8").splitlines():
        if ln.strip().startswith(key + "="):
            return ln.split("=", 1)[1].strip().strip('"').strip("'")
    raise Stop("fault", "env", f"{key} is not in {PP / '.env'}.")


def find_finished(vids: list[dict], title: str) -> tuple[list[dict], list[dict]]:
    """(every render with EXACTLY this title, the completed ones among them). Exact, trimmed
    title only — never a substring: 'PP-EP5-BB-full' must not match 'PP-EP57-BB-full'."""
    hits = [v for v in vids if (v.get("video_title") or "").strip() == title]
    return hits, [v for v in hits if v.get("status") == "completed"]


def heygen_list() -> list[dict]:
    import urllib.request
    req = urllib.request.Request("https://api.heygen.com/v1/video.list?limit=100",
                                 headers={"x-api-key": _env("HEYGEN_API_KEY")})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("data", {}).get("videos", [])


def fetch_renders(ep: Ep) -> list[str]:
    """LIST HeyGen and DOWNLOAD a finished render by its EXACT title. Never starts one. Two
    completed renders with the same title → stop and ask (never guess which take). Returns
    the codes still not ready."""
    import urllib.request
    from providers import RealProvider
    key = _env("HEYGEN_API_KEY")
    vids = heygen_list()
    rec_f = ep.p("renders/heygen-renders.json")
    rec = json.loads(rec_f.read_text(encoding="utf-8")) if rec_f.is_file() else {
        "note": "Jodie's paste and click in the web app; twoway_run fetched only, by exact title.",
        "renders": {}}
    waiting = []
    for code in ("BB", "BM"):
        title = render_title(ep, code)
        dest = ep.p(f"renders/{title}.mp4")
        if dest.is_file():
            continue
        hits, done = find_finished(vids, title)
        if len(done) > 1:
            raise Stop("gate", "fetch_renders",
                       f"There are {len(done)} finished HeyGen renders called {title}, and I will not "
                       f"guess which one is the take you want:\n" + "\n".join(
                           f"    {v['video_id']}  created {v.get('created_at')}" for v in done)
                       + "\nWhich one should I use?", gate="render_paste")
        if not done:
            waiting.append(f"{title} ({hits[0].get('status') if hits else 'not found yet'})")
            continue
        vid = done[0]["video_id"]
        req = urllib.request.Request(f"https://api.heygen.com/v1/video_status.get?video_id={vid}",
                                     headers={"x-api-key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            url = json.load(r).get("data", {}).get("video_url")
        if not url:
            waiting.append(f"{title} (finished, no download link yet)")
            continue
        print(f"  · downloading {title} ({vid})", flush=True)
        RealProvider._download_exact(url, dest)
        rec["renders"][title] = {"video_id": vid, "fetched_at": _now(),
                                 "bytes": dest.stat().st_size}
        _write_json(rec_f, rec)
        if ep.row and not ep.offline:
            import rail
            col = "heygen_video_id" if code == "BB" else "heygen_video_id_2"
            rail.set_fields(ep.row["id"], {col: vid})
    return waiting


def clip_next(eps: list[Ep]) -> str:
    """ONE script on the Windows clipboard — nothing else — and say which template/title it is for."""
    for ep in eps:
        g = ep.gates()
        done = set(g.get("render_paste", {}).get("clipped", []))
        for code in ("BB", "BM"):
            if code in done or ep.p(f"renders/{render_title(ep, code)}.mp4").is_file():
                continue
            f = ep.p(f"docs/spoken-words-{code}.txt")
            text = f.read_text(encoding="utf-8")
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Get-Content -Raw -Encoding UTF8 -LiteralPath $env:PP_CLIP_FILE | "
                                "Set-Clipboard"], env=dict(os.environ, PP_CLIP_FILE=str(f)),
                               capture_output=True, text=True, timeout=60)
            back = subprocess.run(["powershell", "-NoProfile", "-Command",
                                   "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"],
                                  capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
            norm = lambda s: s.replace("\r\n", "\n").strip()            # noqa: E731
            if r.returncode or norm(back) != norm(text):
                raise Stop("fault", "clip", "the clipboard does not hold the script exactly — "
                           "nothing to paste yet. Try again.")
            g.setdefault("render_paste", {}).setdefault("clipped", []).append(code)
            ep.save_gates(g)
            sp = SPEAKERS[code]
            left = sum(1 for e in eps for c in ("BB", "BM")
                       if c not in set(e.gates().get("render_paste", {}).get("clipped", []))
                       and not e.p(f"renders/{render_title(e, c)}.mp4").is_file())
            return (f"{sp['reader']}'s script for {ep.tag} is on your clipboard "
                    f"({len(text.split()):,} words, nothing else in it).\n"
                    f"  Template: {TEMPLATE_NAMES[code].strip()!s}   Title: {render_title(ep, code)}\n"
                    f"  Clear the box first, paste, Enter then Backspace (the preview must play), "
                    f"captions OFF, Generate.\n  {left} script(s) still to paste after this one.")
    return "Every script has been put on the clipboard already. Tell me when the renders are done."


# ─────────────────────────────────────────────────────────── the run order ──
# (stage, id, kind, done(ep) -> bool, action(ep) or message)

def _exists(*rels):
    return lambda ep: all(ep.p(r).exists() for r in rels)


def _cut_file(ep: Ep, k: int | None = None, ext: str = "mp4") -> pathlib.Path:
    k = k or ep.latest_cut() or 1
    return ep.p(f"output/{ep.tag}-cut{k}.{ext}")


def _card_pages(ep: Ep) -> list[str]:
    return sorted({c["page"] for c in ep.epj().get("cards", []) if c.get("page")})


def _session(text: str):
    def act(ep: Ep):
        raise Stop("session", "", text.format(n=ep.n, tag=ep.tag, k=ep.latest_cut() or 1,
                                              dir=ep.dir))
    return act


def _gate(gate: str, question: str, cut: bool = False):
    def done(ep: Ep) -> bool:
        return ep.passed(gate, ep.latest_cut() if cut else None)

    def act(ep: Ep):
        v = ep.gates().get(gate if not cut else f"{gate}#{ep.latest_cut()}")
        q = question.format(n=ep.n, tag=ep.tag, k=ep.latest_cut() or 1, dir=ep.dir)
        if v and any(c.get("status") == "OPEN" for c in v.get("changes", [])):
            opn = [f"{i}. {c['text']}" for i, c in enumerate(v["changes"], 1) if c["status"] == "OPEN"]
            raise Stop("session", gate, f"Jodie's changes on {GATES[gate]} are still OPEN:\n  "
                       + "\n  ".join(opn) + "\nMake them, mark each DONE (or DROPPED) with "
                       f"--change-status, then run me again.")
        raise Stop("gate", gate, q, gate=gate)
    return done, act


def _code(fn):
    return fn


def step_plan_ok(ep: Ep) -> bool:
    f = ep.p("output/run/plan-ok.json")
    return f.is_file() and json.loads(f.read_text(encoding="utf-8")).get("episode_json_md5") \
        == _md5(ep.p("docs/episode.json"))


def do_plan(ep: Ep):
    """STAGE 2's check, on the ESTIMATE clock (no renders yet): `twoway_a17.plan` (which runs
    `twoway_beats.apply` with every A17 card held to its last point), then `twoway_beats`'
    own violations — listening footage, card fit, b-roll floors. A card that cannot fit its
    passage is a SCRIPT fault, decided here while the words can still change — so a violation
    goes back to the session, never into a guessed time. The derived plan is written into
    episode.json (temp file + rename), as EP56's commission did."""
    import twoway_a17 as a17
    import twoway_beats as tb
    f = ep.p("docs/episode.json")
    epj = json.loads(f.read_text(encoding="utf-8"))
    a17.plan(epj)
    bad = tb.violations(epj.get("layout_plan", []), tb.broll_floors(epj))
    t = tb.tally(epj.get("layout_plan", [])) if epj.get("layout_plan") else {}
    _write_json(f, epj)
    if bad:
        raise Stop("session", "plan", "The cut plan does not fit — fix the COMMISSION (or ask Jodie "
                   "if it needs the words changed), then run me again:\n  " + "\n  ".join(bad))
    if t:
        print(f"  · plan fits: dialogue {t['total_s']:.0f}s on the estimate clock")
    _write_json(ep.p("output/run/plan-ok.json"), {"episode_json_md5": _md5(f), "at": _now()})


def do_fetch(ep: Ep):
    waiting = fetch_renders(ep)
    if waiting:
        raise Stop("wait", "fetch_renders", "Not finished in HeyGen yet: " + "; ".join(waiting)
                   + ". Nothing is wrong — run me again when they're done (or tell me they are).")


def do_words_check(ep: Ep):
    for code in ("BB", "BM"):
        out = ep.p(f"renders/words-{code}-full.json")
        if out.is_file():
            continue
        _run(ep, f"words-{code}", PY + [HERE / "twoway_render_words.py",
                                        ep.p(f"renders/{render_title(ep, code)}.mp4"),
                                        ep.p(f"docs/spoken-words-{code}.txt"), "--json", out],
             ok_codes=(0, 1))


def words_need_jodie(ep: Ep) -> list[str]:
    out = []
    for code in ("BB", "BM"):
        f = ep.p(f"renders/words-{code}-full.json")
        if f.is_file():
            out += [f"{SPEAKERS[code]['reader']}: {x}"
                    for x in json.loads(f.read_text(encoding="utf-8")).get("needs_jodie", [])]
    return out


def do_masters(ep: Ep):
    need = words_need_jodie(ep)
    if need and not ep.passed("render_fix"):
        raise Stop("gate", "render_fix",
                   "The renders have something only you can rule on (I have not cut anything):\n  "
                   + "\n  ".join(need) + "\nRetake that part, or shall I cut it anyway?",
                   gate="render_listen")
    for code in ("BB", "BM"):
        if not ep.p(f"renders/{code}-master.mp4").is_file():
            _run(ep, f"master-{code}", PY + [HERE / "twoway_masters.py", ep.n, code, "--words",
                                             ep.p(f"renders/words-{code}-full.json"), "--why",
                                             "twoway_run: cuts from twoway_render_words (head / "
                                             "tail / between sentences only)"])


def masters_checked(ep: Ep) -> bool:
    for code in ("BB", "BM"):
        for f in (f"renders/words-{code}-master.json", f"renders/repeats-{code}-master.json"):
            p = ep.p(f)
            if not p.is_file():
                return False
    return True


def do_masters_check(ep: Ep):
    bad = []
    for code in ("BB", "BM"):
        m, s = ep.p(f"renders/{code}-master.mp4"), ep.p(f"docs/spoken-words-{code}.txt")
        rc1 = _run(ep, f"words-{code}-master", PY + [HERE / "twoway_render_words.py", m, s, "--json",
                                                     ep.p(f"renders/words-{code}-master.json")],
                   ok_codes=(0, 1))
        rc2 = _run(ep, f"repeats-{code}-master", PY + [HERE / "repeated_words.py", m, s, "--json",
                                                       ep.p(f"renders/repeats-{code}-master.json")],
                   ok_codes=(0, 1))
        if rc1 or rc2:
            bad.append(f"{code}-master: " + ("words not the script; " if rc1 else "")
                       + ("a run of words said twice" if rc2 else ""))
    if bad:
        raise Stop("fault", "masters_check", "A master still is not just the script: " + "; ".join(bad)
                   + ". See renders/words-*-master.json and repeats-*-master.json.")


def do_align(ep: Ep):
    import render_lock
    import align_to_script as ats
    with render_lock.hold("PP", f"{ep.tag} align_to_script"):
        for code in ("BB", "BM"):
            ats.build(ep.dir, master=ep.p(f"renders/{code}-master.mp4"),
                      spoken=ep.p(f"docs/spoken-words-{code}.txt"), out=ep.p(f"renders/{code}.srt"))


def replan_done(ep: Ep) -> bool:
    f = ep.p("output/run/replan.json")
    return f.is_file() and json.loads(f.read_text(encoding="utf-8")).get("timeline_md5") \
        == _md5(ep.p("renders/master-timeline.json"))


def do_replan(ep: Ep):
    _run(ep, "replan", PY + [HERE / "twoway_a17.py", ep.n, "--replan", "--write", "--pp", ep.pp])
    _write_json(ep.p("output/run/replan.json"),
                {"timeline_md5": _md5(ep.p("renders/master-timeline.json")), "at": _now()})


def pages_done(ep: Ep) -> bool:
    pages = _card_pages(ep)
    return bool(pages) and all(ep.p(f"overlay/export/{pg}").is_file() for pg in pages) \
        and ep.p(f"overlay/export/ep{ep.n}-title.html").is_file()


def timing_done(ep: Ep) -> bool:
    f = ep.p("output/run/card-timing.json")
    return f.is_file() and json.loads(f.read_text(encoding="utf-8")).get("episode_json_md5") \
        == _md5(ep.p("docs/episode.json"))


def do_card_timing(ep: Ep):
    """A17 ON THE PAGES (found 13 Nov 2026 by the EP58 card helper, before it bit): the replan writes
    the measured point times into episode.json (build.a17), but the card pages were authored before
    there were any, so their points would build on the block's own stagger, not on the reader's words.
    author_cards re-authors every generated page whose content changed — the same step EP56 ran by
    hand — so this runs after the replan and before the graphics render."""
    _run(ep, "card-timing", PY + [SCRIPTS / "author_cards.py", ep.p("docs/episode.json"),
                                  ep.p("overlay/export")])
    _write_json(ep.p("output/run/card-timing.json"), {"episode_json_md5": _md5(ep.p("docs/episode.json")),
                                                      "at": _now()})


def graphics_done(ep: Ep) -> bool:
    clips = ep.p("overlay/clips")
    want = [pathlib.Path(pg).stem for pg in _card_pages(ep)] + [f"ep{ep.n}-title"]
    return clips.is_dir() and all((clips / f"{w}.mp4").is_file() for w in want)


def do_graphics(ep: Ep):
    pages = [pathlib.Path(pg).name for pg in _card_pages(ep)]
    # Cards whose content would sit under the film's corner chip are rendered lifted clear
    # (twoway_cards --keep-clear). The list lives in the episode's own data — build.keep_clear —
    # found by the card check (13 Nov 2026: EP58 C3, EP59 C6/C13), never remembered.
    clear = []
    for pg in (ep.epj().get("build") or {}).get("keep_clear") or []:
        clear += ["--keep-clear", pathlib.Path(pg).name]
    _run(ep, "cards", PY + [HERE / "twoway_cards.py", ep.n, *pages, "end-card-template.html",
                            "--as", "end-card-template.html=end-card-template-nologo.mp4", *clear],
         lock="graphics")
    std = [f"ep{ep.n}-title.html", "warranty-slide.html", "end-card-template.html",
           "midroll-lowerthird.html"]
    _run(ep, "standing-cards", PY + [SCRIPTS / "render_cards_batch.py", ep.p("overlay/export"),
                                     ep.p("overlay/clips"), "0.5", *std], lock="graphics")


def do_chips(ep: Ep):
    _run(ep, "chips-BB", PY + [HERE / "twoway_chips.py", ep.n, "BB", "--pp", ep.pp])
    _run(ep, "chips-BM", PY + [HERE / "twoway_chips.py", ep.n, "BM", "--pp", ep.pp])
    _run(ep, "host-plate", PY + [HERE / "twoway_chips.py", ep.n, "BB", "--host", "--pp", ep.pp])


def cut_needed(ep: Ep) -> bool:
    """A new cut is needed when there is none, or the last cut's watch came back with changes
    that are now all DONE/DROPPED (the next cut carries them)."""
    k = ep.latest_cut()
    if k == 0:
        return True
    v = ep.gates().get(f"cut_watch#{k}")
    return bool(v) and v.get("verdict") == "changes" and not any(
        c.get("status") == "OPEN" for c in v.get("changes", []))


def do_cut(ep: Ep):
    k = ep.latest_cut() + 1
    _run(ep, f"render-cut{k}", PY + ["-u", HERE / "twoway_render.py", ep.n, "--pp", ep.pp, "--out",
                                     ep.p(f"output/{ep.tag}-cut{k}.mp4")], lock=f"cut {k}")
    prev = ep.gates().get(f"cut_watch#{k - 1}")
    changes = [c for c in (prev or {}).get("changes", [])]
    ep.p(f"output/review/cut{k}-changes.json").parent.mkdir(parents=True, exist_ok=True)
    _write_json(ep.p(f"output/review/cut{k}-changes.json"), {"cut": k, "from_watch_of_cut": k - 1,
                                                             "changes": changes})


def do_srt(ep: Ep):
    _run(ep, "srt", PY + [HERE / "twoway_srt.py", ep.n, "--pp", ep.pp, "--out", _cut_file(ep, ext="srt")])


def qc_done(ep: Ep) -> bool:
    return ep.p(f"output/qc/{_cut_file(ep).stem}/qc-report.json").is_file()


def do_qc(ep: Ep):
    rc = _run(ep, f"qc-cut{ep.latest_cut()}", PY + [HERE / "twoway_film_qc.py", ep.n, _cut_file(ep),
                                                    "--masters", "--pp", ep.pp], ok_codes=(0, 1))
    if rc == 1:
        raise Stop("fault", "film_qc", f"The finished-film QC found a fault in cut {ep.latest_cut()} "
                   f"— this is a defect, not a question. Report: output/qc/{_cut_file(ep).stem}/"
                   "qc-report.json. Fix it, then make the next cut.")


def do_cut_page(ep: Ep):
    import twoway_review
    twoway_review.cut_page(ep, ep.latest_cut())


def do_ebook(ep: Ep):
    _run(ep, "ebook-author", PY + [SCRIPTS / "author_ebook.py", ep.p("docs/episode.json"),
                                   ep.p("ebook"), "--force"])
    _run(ep, "ebook-pdf", PY + [SCRIPTS / "build_ebook.py",
                                ep.p(f"ebook/{ep.tag}-ebook-source.html"),
                                ep.p(f"output/{ep.tag}-ebook.pdf")])


def do_thumbnail(ep: Ep):
    out = ep.p(f"output/{ep.tag}-thumbnail.png")
    _run(ep, "thumbnail", PY + [SCRIPTS / "render_still.py", f"ep{ep.n}-thumbnail.html", out,
                                "1280", "720"], cwd=ep.p("thumbnail"))
    proof = ep.p("output/thumbnail-proof")
    proof.mkdir(exist_ok=True)
    for w in (120, 168, 210, 320):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf",
                        f"scale={w}:-1:flags=lanczos", str(proof / f"thumb-{w}.png")],
                       check=True, timeout=120)


def do_broll_page(ep: Ep):
    import twoway_review
    twoway_review.broll_page([ep])


def published(ep: Ep) -> bool:
    return bool(ep.row and (ep.row.get("status") == "published" or ep.row.get("published_url")))


G_RENDER_PASTE = _gate("render_paste",
                       "Time for the two HeyGen renders for {tag}. I'll put ONE script at a time on "
                       "your clipboard — say \"clip\" (or type `python engine\\twoway_run.py {n} --clip`) "
                       "and I'll tell you which template and title it's for. Tell me once both are "
                       "Generating.")
G_BROLL = _gate("broll_cover",
                "The b-roll clips and cover pictures for {tag} are ready to look at, every one at full "
                "size: open output\\review\\broll-review.html, tick the ones you like, press "
                "\"Copy my picks\" and paste them to me. Which do you want?")
G_RENDER_LISTEN = _gate("render_listen",
                        "Both voices for {tag} are ready: renders\\BB-master.mp4 (Gordon) and "
                        "renders\\BM-master.mp4 (Steve), plus the joins in output\\qc\\joins\\. "
                        "What do you think when you listen?")
G_CUT = _gate("cut_watch", "Cut {k} of {tag} is ready to watch: open output\\review\\cut{k}.html. "
                           "What do you think?", cut=True)
G_JOIN = _gate("join_listen", "The midroll of {tag}: listen to output\\qc\\midroll-listen.wav "
                              "(it's on the cut page too). How does it sound?")
G_TITLE = _gate("title_thumbnail", "The title and thumbnail for {tag}: output\\{tag}-thumbnail.png and "
                                   "the title on line 1 of output\\{tag}-youtube.txt. Happy with them?")

STEPS = [
    # ── STAGE 1 — THE WORDS ────────────────────────────────────────────────────
    (1, "folder", "code", lambda ep: ep.dir is not None, do_folder),
    (1, "capture", "code", lambda ep: len(ep.capture()) == 1,
     lambda ep: _run(ep, "capture", PY + [SCRIPTS / "capture_article.py", ep.row["source_url"],
                                          ep.n, "--pp", ep.pp, "--write"])),
    (1, "split", "code", _exists("docs/turns.json"), do_split),
    (1, "episode_json", "code", lambda ep: bool(ep.epj().get("speakers")), do_episode_json),
    (1, "substitutions", "code", subs_done, do_substitutions),
    (1, "words", "gate", lambda ep: words_file(ep).is_file(), do_words),
    (1, "compose", "code", _exists("docs/script-manifest-BB.json", "docs/spoken-words-BM.txt"),
     lambda ep: _run(ep, "compose", PY + [HERE / "twoway_furniture.py", ep.n, "--write", "--pp", ep.pp])),
    # ── THE RENDER GATE OPENS AT THE WORDS (Jodie, 13 Nov 2026 — the LOCKED ORDER, the same as
    # single episodes): the renders are the long pole and need only the approved scripts, so
    # they start the moment the scripts are composed, and the commission, the plan, the cards
    # and the b-roll are all built BEHIND them while HeyGen cooks. Jodie: "The graphics cards
    # etc should be built while heygen generates the video." The plan used to come first here.
    (3, "render_sheet", "code", lambda ep: ep.p(f"docs/HEYGEN-RENDER-EP{ep.n:02d}.md").is_file(),
     do_render_sheet),
    (3, "render_paste", "gate",
     lambda ep: ep.passed("render_paste") or all(
         ep.p(f"renders/{render_title(ep, c)}.mp4").is_file() for c in ("BB", "BM")),
     G_RENDER_PASTE[1]),
    # ── STAGE 2 — PLAN, BEHIND THE RENDERS ─────────────────────────────────────
    (2, "commission", "session",
     lambda ep: all(ep.epj().get(k) for k in ("beats", "cards", "broll", "turn_signals")),
     _session("Write {tag}'s two-way commission into docs/episode.json — beats, cards (A17 points, "
              "each with its `page`), b-roll slots (RIDERLESS racing, empty track, crowd, detail; "
              "never numbered saddlecloths), turn_signals, packaging, cover, title_card, ebook — "
              "following PP-EP56's episode.json and its output/qc/ep56-stage2/commission_ep56.py. "
              "A list too long for a card shows what fits; the e-book carries all. Then run me again.")),
    (2, "plan", "code", step_plan_ok, do_plan),
    # ── STAGE 3 — HIGGSFIELD (inside 110), while the renders cook ──────────────
    (3, "broll_generate", "session", _exists("output/review/broll-candidates.json"),
     _session("Generate {tag}'s b-roll clips and two cover heroes through engine/hf_guard.py ONLY "
              "(110-credit ceiling), from the prompts in docs/episode.json. Then write "
              "output/review/broll-candidates.json: a list of {{id, kind: clip|cover, slot, line, url, "
              "job_id}} — url = the full-size result. Then run me again.")),
    (3, "broll_page", "code", _exists("output/review/broll-review.html"), do_broll_page),
    (3, "broll_cover", "gate", G_BROLL[0], G_BROLL[1]),
    (3, "broll_download", "session", _exists("output/review/broll-downloaded.json"),
     _session("Download ONLY the b-roll and cover Jodie picked (docs/twoway-gates.json, broll_cover) "
              "by job id into broll/ and thumbnail/, byte-exact, and record each in "
              "docs/EP{n}-broll-review.md (one line per clip, her verdict) and "
              "output/review/broll-downloaded.json ({{files: [...]}}). Then run me again.")),
    (3, "fetch_renders", "code",
     lambda ep: all(ep.p(f"renders/{render_title(ep, c)}.mp4").is_file() for c in ("BB", "BM")),
     do_fetch),
    (3, "render_words", "code", _exists("renders/words-BB-full.json", "renders/words-BM-full.json"),
     do_words_check),
    (3, "masters", "code", _exists("renders/BB-master.mp4", "renders/BM-master.mp4"), do_masters),
    (3, "masters_check", "code", masters_checked, do_masters_check),
    (3, "render_listen", "gate", G_RENDER_LISTEN[0], G_RENDER_LISTEN[1]),
    # ── STAGE 4 — THE BUILD ────────────────────────────────────────────────────
    (4, "align", "code", _exists("renders/BB.srt", "renders/BM.srt"), do_align),
    (4, "interleave", "code", _exists("renders/master-timeline.json", "renders/merged.srt"),
     lambda ep: _run(ep, "interleave", PY + [HERE / "twoway_interleave.py", ep.n, "--write", "--pp", ep.pp])),
    (4, "replan", "code", replan_done, do_replan),
    (4, "card_pages", "session", pages_done,
     _session("Author {tag}'s card pages into overlay/export/ — the title card ep{n}-title.html and "
              "one page per card in docs/episode.json (its `page`), with the standing pages "
              "(warranty-slide, end-card-template, midroll-lowerthird, pp-anim.js, assets) copied as "
              "PP-EP56 has them. Load the pp-motion-graphics skill first. Then run me again.")),
    (4, "card_timing", "code", timing_done, do_card_timing),
    (4, "graphics", "code", graphics_done, do_graphics),
    (4, "chips", "code", _exists("overlay/export/twoway-chips-BB.png", "overlay/export/twoway-chips-BM.png"),
     do_chips),
    (4, "cut", "code", lambda ep: not cut_needed(ep), do_cut),
    (4, "srt", "code", lambda ep: _cut_file(ep, ext="srt").is_file(), do_srt),
    (4, "film_qc", "code", qc_done, do_qc),
    (4, "fresh_eyes", "session", lambda ep: ep.p(f"output/review/fresh-eyes-cut{ep.latest_cut()}.md").is_file(),
     _session("Run the fresh-eyes reviewer on cut {k}: spawn the `twoway-fresh-eyes` agent and hand it "
              "ONLY the contact sheets in output/qc-frames/{tag}-cut{k}/ and "
              "docs/twoway-fresh-eyes-brief.md (in the repo) — never the build log. Save its report, "
              "unedited, to output/review/fresh-eyes-cut{k}.md. If it reports a real defect, say so "
              "to Jodie straight away. Then run me again.")),
    (4, "cut_page", "code", lambda ep: ep.p(f"output/review/cut{ep.latest_cut()}.html").is_file(),
     do_cut_page),
    # ── STAGE 5 — APPROVE AND SHIP ─────────────────────────────────────────────
    (5, "cut_watch", "gate", G_CUT[0], G_CUT[1]),
    (5, "join_listen", "gate", G_JOIN[0], G_JOIN[1]),
    (5, "ebook_body", "session", _exists("ebook/body.html"),
     _session("Make {tag}'s e-book body: ebook/body.html COPIED from the capture by code (never "
              "retyped) with the `ebook` block in docs/episode.json, as PP-EP56's "
              "output/qc/ep56-stage4/make_ebook_body.py did; and the cover keys + ebook cover as its "
              "keys_and_cover.py did. Then run me again.")),
    (5, "ebook_pdf", "code", lambda ep: ep.p(f"output/{ep.tag}-ebook.pdf").is_file(), do_ebook),
    (5, "thumbnail_page", "session", lambda ep: ep.p(f"thumbnail/ep{ep.n}-thumbnail.html").is_file(),
     _session("Author {tag}'s thumbnail page thumbnail/ep{n}-thumbnail.html from PP-EP56's (full-bleed; "
              "the chosen cover hero). Then run me again.")),
    (5, "thumbnail", "code", lambda ep: ep.p(f"output/{ep.tag}-thumbnail.png").is_file(), do_thumbnail),
    (5, "youtube", "session", lambda ep: ep.p(f"output/{ep.tag}-youtube.txt").is_file(),
     _session("Write output/{tag}-youtube.txt (title on line 1, then the description between the "
              "banners of docs/youtube-copy-form.json) as PP-EP56's was. Then run me again.")),
    (5, "title_thumbnail", "gate", G_TITLE[0], G_TITLE[1]),
    (5, "publish_pack", "session", lambda ep: ep.p(f"output/{ep.tag}-PUBLISH-PACK.md").is_file(),
     _session("Write output/{tag}-PUBLISH-PACK.md and output/{tag}-cover-lowres.jpg, and copy the "
              "approved cut to its final name, as PP-EP56's were (md5-prove the copy). Then run me "
              "again.")),
    (5, "publish", "gate", published,
     lambda ep: (_ for _ in ()).throw(Stop("gate", "publish",
                 f"{ep.tag} is ready to publish — the pack is output\\{ep.tag}-PUBLISH-PACK.md. "
                 "Publishing is yours (the pp-publish-episode skill). Tell me the YouTube link "
                 "when it's live.", gate="publish"))),
]
STEP_IDS = [s[1] for s in STEPS]


def where(ep: Ep) -> tuple[int, str, str] | None:
    """The first step that is not done: (stage, id, kind). None = finished."""
    for stage, sid, kind, done, _act in STEPS:
        try:
            if not done(ep):
                return stage, sid, kind
        except Stop:
            return stage, sid, kind
        except (OSError, ValueError, KeyError):
            return stage, sid, kind
    return None


def advance(ep: Ep, dry: bool = False) -> Stop | None:
    """Run steps until one stops. Returns the Stop (or None when the episode is published)."""
    for _ in range(len(STEPS) * 2):
        w = where(ep)
        if w is None:
            _set_rail(ep, 5, "published", None, "published")
            return None
        stage, sid, kind = w
        act = next(s[4] for s in STEPS if s[1] == sid)
        status = "awaiting_approval" if stage == 5 else ("queued" if sid == "folder" else "building")
        if dry:
            return Stop(kind, sid, f"next: {sid} ({kind})")
        try:
            print(f"[{ep.tag}] stage {stage} · {sid}", flush=True)
            _set_rail(ep, stage, sid, None, status)
            act(ep)
        except Stop as s:
            s.step = s.step or sid
            gate = s.gate if s.kind == "gate" else None
            _set_rail(ep, stage, sid if not gate else f"waiting on {GATES.get(gate, gate)}",
                      gate, status)
            return s
        if where(ep) == w:
            return Stop("fault", sid, f"{sid} ran and is still not done — its done test still fails. "
                        "Nothing else was attempted.")
    return Stop("fault", "loop", "the runner went round too many times without stopping.")


# ───────────────────────────────────────────────────────────────── verdicts ──

def record_verdict(ep: Ep, gate: str, verdict: str, words: str, changes: list[str],
                   cut: int | None = None) -> dict:
    """Jodie's verdict, in her words, as ONE line; each change as its OWN item, OPEN."""
    if gate not in GATES and gate != "render_fix":
        raise SystemExit(f"unknown gate {gate!r}; one of {', '.join(GATES)}")
    if verdict not in ("approved", "changes"):
        raise SystemExit("verdict is 'approved' or 'changes'")
    g = ep.gates()
    key = gate if gate != "cut_watch" else f"cut_watch#{cut or ep.latest_cut()}"
    g[key] = {"verdict": verdict, "words": words, "at": _now(), "by": "Jodie (relayed in Claude Code)",
              "changes": [{"n": i, "text": c, "status": "OPEN"} for i, c in enumerate(changes, 1)]}
    if gate == "broll_cover":
        g[key]["picks"] = re.findall(r"\b(?:C\d+|cover [A-Z])\b", words)
    ep.save_gates(g)
    return g[key]


# ─────────────────────────────────────────────────────────────────── main ──

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("eps", nargs="*", help="episode numbers: 57 or EP57")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--clip", action="store_true")
    ap.add_argument("--verdict", nargs=4, metavar=("EP", "GATE", "VERDICT", "WORDS"))
    ap.add_argument("--change", action="append", default=[])
    ap.add_argument("--change-status", nargs=4, metavar=("EP", "GATE", "N", "STATUS"))
    ap.add_argument("--pp", default=str(PP))
    a = ap.parse_args()
    pp = pathlib.Path(a.pp)
    num = lambda s: int(re.sub(r"\D", "", s))                          # noqa: E731

    if a.verdict:
        ep = Ep(num(a.verdict[0]), pp)
        v = record_verdict(ep, a.verdict[1], a.verdict[2], a.verdict[3], a.change)
        print(f"recorded {a.verdict[1]} for {ep.tag}: {v['verdict']} — \"{v['words']}\"")
        for c in v["changes"]:
            print(f"  change {c['n']} OPEN: {c['text']}")
        return 0
    if a.change_status:
        ep = Ep(num(a.change_status[0]), pp)
        g = ep.gates()
        key = a.change_status[1] if a.change_status[1] != "cut_watch" else f"cut_watch#{ep.latest_cut()}"
        st = a.change_status[3].upper()
        if st not in ("OPEN", "DONE", "DROPPED"):
            raise SystemExit("status is OPEN, DONE or DROPPED")
        c = next(c for c in g[key]["changes"] if c["n"] == int(a.change_status[2]))
        c["status"], c["at"] = st, _now()
        ep.save_gates(g)
        print(f"{ep.tag} {key} change {c['n']} -> {st}: {c['text']}")
        return 0

    eps = [Ep(num(e), pp) for e in a.eps]
    if not eps:
        ap.error("name at least one episode")
    if a.clip:
        print(clip_next(eps))
        return 0
    if a.status:
        for ep in eps:
            w = where(ep) if ep.dir is not None else (1, "folder", "code")
            gate = (ep.row or {}).get("twoway", {}) or {}
            print(f"{ep.tag}: " + ("published" if w is None else
                                   f"stage {w[0]} · next {w[1]} ({w[2]})")
                  + (f" · waiting on Jodie: {GATES.get(gate.get('gate'), gate.get('gate'))}"
                     if gate.get("gate") else ""))
        return 0

    stops = []
    for ep in eps:
        s = advance(ep)
        stops.append((ep, s))
        print(f"[{ep.tag}] " + ("PUBLISHED — nothing to do." if s is None else
                                f"STOPPED at {s.step} ({s.kind})"), flush=True)
    print("\n" + "═" * 72)
    faults = [(e, s) for e, s in stops if s and s.kind == "fault"]
    if faults:
        for e, s in faults:
            print(f"🔴 {e.tag} — a FAULT at {s.step} (not a question):\n{s.message}\n")
    sessions = [(e, s) for e, s in stops if s and s.kind == "session"]
    for e, s in sessions:
        print(f"SESSION STEP for {e.tag} ({s.step}):\n{s.message}\n")
    waits = [(e, s) for e, s in stops if s and s.kind == "wait"]
    for e, s in waits:
        print(f"WAITING ({e.tag}): {s.message}\n")
    gates = [(e, s) for e, s in stops if s and s.kind == "gate"]
    if gates and not faults and not sessions:
        first = gates[0][1].gate
        same = [(e, s) for e, s in gates if s.gate == first]
        print("❓ ONE QUESTION FOR JODIE:")
        if len(same) > 1 and first == "broll_cover":
            # BATCH: ONE page for every episode waiting on its picks, one sitting.
            import twoway_review
            page = twoway_review.broll_page([e for e, _ in same])
            print(f"   The b-roll and cover pictures for {', '.join(e.tag for e, _ in same)} are "
                  f"ready, every one at full size, on ONE page:\n     {page}\n   Tick the ones you "
                  f"like, press \"Copy my picks\" and paste the line to me. Which do you want?")
            return 0
        if len(same) > 1:
            print(f"   ({len(same)} episodes are at the same gate: "
                  f"{', '.join(e.tag for e, _ in same)} — one sitting.)")
        for e, s in same:
            print(f"   {s.message}")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
