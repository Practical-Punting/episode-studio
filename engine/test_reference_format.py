"""Reference episodes are the SAME FORMAT as the episode being built.

🔴 THE FAULT (EP50, 27 Sep 2026). The episode.json commission is shown "the two most
recent episodes with an episode.json" as REAL, SHIPPED examples, and the shape gate and
config pre-flight judge against the same pair. The two-way EP49 has an episode.json, so
single-presenter EP50 was taught by a two-way and copied its early-CTA clip,
`end-card-template-nologo.mp4`. That copy exists because a two-way draws its corner logo
OVER the cards; a single-presenter episode draws it UNDER them (assemble_episode pass A),
so the no-logo card would have left the screen with no logo at all. Assembly halted on
the missing file — had the file existed, it would have shipped.

Checks the helper on a synthetic tree, that all three readers go through it, and — on
the real Drive — that EP50's references are single-presenter episodes.

PROVED FAIL-FIRST: on the pre-fix code there is no `reference_dirs` and both readers
walk the plain "most recent" loop.

Run: python engine/test_reference_format.py
"""
import json
import pathlib
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import preflight_episode_json as pj  # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


helper = getattr(pj, "reference_dirs", None)
check(helper is not None, "preflight_episode_json has a same-format reference lookup")

if helper:
    root = pathlib.Path(tempfile.mkdtemp(prefix="refs_"))
    try:
        for n, fmt in [(45, None), (46, None), (47, None), (48, None), (49, "two-way"),
                       (50, None)]:
            d = root / f"PP-EP{n}-Some-Title" / "docs"
            d.mkdir(parents=True)
            j = {"episode": f"EP{n}", "build": {}}
            if fmt:
                j["format"] = fmt
            (d / "episode.json").write_text(json.dumps(j), encoding="utf-8")
        got = [n for n, _ in pj.reference_dirs(50, 2, "single", root)]
        check(got == [48, 47], "a single-presenter EP50 is taught by EP48 + EP47, not EP49",
              got)
        got = [n for n, _ in pj.reference_dirs(51, 2, "two-way", root)]
        check(got == [49], "a two-way still finds the two-way (EP49)", got)
        check(pj.fmt_of({}) == "single" and pj.fmt_of({"format": "two-way"}) == "two-way",
              "no format key means single-presenter")
    finally:
        shutil.rmtree(root, ignore_errors=True)

# all three readers go through the helper, and no bare "most recent" loop is left
eng = (HERE / "engine.py").read_text(encoding="utf-8")
prov = (HERE / "providers.py").read_text(encoding="utf-8")
body = eng.split("def _reference_episodes", 1)[1].split("\ndef ", 1)[0]
check("reference_dirs(" in body, "engine._reference_episodes goes through reference_dirs")
check(len(re.findall(r"_reference_episodes\([^)]*fmt=", eng)) == 2,
      "  and both its callers pass the episode's format")
com = prov.split("THE SAME TWO REFERENCES", 1)[1][:1500]
check("reference_dirs(" in com and "fmt_of(ep)" in com,
      "the episode.json commission's examples go through it too")
check('range(int(ep["ep_number"]) - 1, 0, -1)' not in com,
      "  and the old most-recent loop is gone from the commission")

# the real Drive, where it bit
try:
    live = [n for n, _ in pj.reference_dirs(50, 2, "single")] if helper else []
    if live:
        check(49 not in live, f"on the Drive, EP50's references are {live} — no two-way",
              live)
except Exception as e:  # noqa: BLE001
    print(f"  (Drive not readable — live half SKIPPED, not assumed: {e})")

print(f"\nreference format: {'all passed' if not fails else f'{len(fails)} failed'}")
sys.exit(1 if fails else 0)
