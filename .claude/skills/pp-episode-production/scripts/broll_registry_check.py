# Automate the b-roll NO-REPEAT check (cross-episode + within-episode) against
# docs/broll-registry.md, using an episode.json's broll[] list.
#   python broll_registry_check.py <broll-registry.md> <episode.json> [--append EP06]
# Default: report exact-target repeats + within-episode dupes + advisory subject
# overlap. --append <EPNN> appends this episode's clips as a new registry section.
import json, re, sys

REG, EPJ = sys.argv[1], sys.argv[2]
APPEND = sys.argv[sys.argv.index("--append")+1] if "--append" in sys.argv else None

reg = open(REG, encoding="utf-8").read()

# 🔴 ONLY THE LEDGER COUNTS AS A REGISTRY ENTRY — everything above "## Used so far"
# is PROSE: standing rules, worked examples, the reasons behind them.
#
# This used to scan the WHOLE FILE for `broll-[a-z0-9-]+`, so the moment a standing
# rule quoted a clip by name as its worked example, that clip was treated as already
# used and the next build halted. It happened the same day the hats rule was written
# (8 Aug 2026): rule A15a names `broll-country-course-gums-and-rail` as the example of
# a uniform crowd, and the guard then refused to regenerate that very clip.
#
#     A GUARD THAT FIRES ON THE TEXT DESCRIBING THE THING IT GUARDS.
#     CLAUDE.md fault 1a, and the reason the rule is written in BOTH directions.
#
# The registry is meant to answer "has this clip been USED", and the ledger is the only
# part of the file that records use. Deriving the answer from the document's own
# structure means prose can be added freely and can never trip the check again.
LEDGER = "## Used so far"
reg_entries = reg.split(LEDGER, 1)[1] if LEDGER in reg else reg

EP = json.load(open(EPJ, encoding="utf-8"))
brolls = EP.get("broll", [])

# 🔴 REGENERATING THIS EPISODE'S OWN CLIP SUPERSEDES ITS ENTRY — IT IS NOT A REPEAT.
# (Jodie, 8 Aug 2026.) The no-repeat rule exists so one episode does not re-use
# ANOTHER episode's footage. Re-making a clip for the episode that already owns it is
# a visual CORRECTION — the white-hat fix on EP18 — and a correction must be
# hands-off, not a hard fail that needs a human to unstick it.
#
# So this episode's own ledger section is excluded from the comparison. Superseding
# is then just "log the new prompt in your own section", which cannot trip the guard.
this_ep = str(EP.get("episode") or "").strip()
_sections = re.split(r"(?m)^### (?=EP)", reg_entries)
_others = [s for s in _sections
           if not (this_ep and re.match(rf"{re.escape(this_ep)}\b", s))]
reg_entries = "\n".join(_others)

existing_targets = set(re.findall(r"broll-[a-z0-9-]+", reg_entries))
# crude subject bag: words from every registry table row / used-up list
STOP = set("the a an of to in on and or is are it its by with for so as at be its".split())
def kw(s): return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 3}
reg_kw = kw(reg_entries)
targets = [b["target"] for b in brolls]

issues = 0
# 🔴 CROSS-EPISODE RE-USE IS ALLOWED (Jodie, 18 September 2026) and is REPORTED, not
# failed. The old law -- "no b-roll is ever repeated from an earlier episode" -- made
# the library write-only: 278 clips nobody could touch. The test is now RELEVANCE to
# the line, which no script can judge, so this prints the re-use and leaves the
# judgement where it belongs. See docs/broll-registry.md, THE NO-REPEAT LAW.
print("=== cross-episode re-use (ALLOWED when it matches the line — review) ===")
reused = 0
for b in brolls:
    t = b["target"]
    if t in existing_targets:
        print(f"  ~ RE-USE: {t} is already in the registry — "
              f"check it matches this line: {b.get('line','')!r}")
        reused += 1
    else:
        print(f"  ok  {t} is new")
if reused:
    print(f"  {reused} re-used clip(s). NOT a failure. "
          f"Within-episode repeats below still are.")

dupes = sorted({t for t in targets if targets.count(t) > 1})
if dupes:
    print(f"=== within-episode duplicate targets — HARD FAIL ===\n  ! {dupes}"); issues += len(dupes)

print("=== advisory: subject overlap with existing registry (review, not a hard fail) ===")
for b in brolls:
    subj = kw(b.get("line", "") + " " + b["target"].replace("broll-", "").replace("-", " "))
    overlap = subj & reg_kw
    # only surface if the DISTINCTIVE subject words are already present
    strong = overlap - {"horse","horses","turf","race","racing","field","finish","weight"}
    if len(strong) >= 3:
        print(f"  ~ {b['target']}: shares [{', '.join(sorted(strong)[:6])}] with the registry — eyeball it")

print(f"\nRESULT: {'CLEAN' if issues == 0 else f'{issues} REPEAT ISSUE(S)'}")

if APPEND:
    rows = "\n".join(f"| {b['target']} | {b.get('line','').strip()[:60]} |" for b in brolls)
    block = f"\n### {APPEND} ({'auto-logged'})\n| File | Subject/line |\n|---|---|\n{rows}\n"
    with open(REG, "a", encoding="utf-8") as f:
        f.write(block)
    print(f"\nAppended {len(brolls)} clips to the registry as section '{APPEND}'.")

sys.exit(1 if issues else 0)
