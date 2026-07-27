# Automate the b-roll NO-REPEAT check (cross-episode + within-episode) against
# docs/broll-registry.md, using an episode.json's broll[] list.
#   python broll_registry_check.py <broll-registry.md> <episode.json> [--append EP06]
# Default: report exact-target repeats + within-episode dupes + advisory subject
# overlap. --append <EPNN> appends this episode's clips as a new registry section.
import json, re, sys

REG, EPJ = sys.argv[1], sys.argv[2]
APPEND = sys.argv[sys.argv.index("--append")+1] if "--append" in sys.argv else None

reg = open(REG, encoding="utf-8").read()
existing_targets = set(re.findall(r"broll-[a-z0-9-]+", reg))
# crude subject bag: words from every registry table row / used-up list
STOP = set("the a an of to in on and or is are it its by with for so as at be its".split())
def kw(s): return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 3}
reg_kw = kw(reg)

EP = json.load(open(EPJ, encoding="utf-8"))
brolls = EP.get("broll", [])
targets = [b["target"] for b in brolls]

issues = 0
print("=== exact target repeats vs registry ===")
for b in brolls:
    t = b["target"]
    if t in existing_targets:
        print(f"  ! REPEAT: {t} already logged in the registry"); issues += 1
    else:
        print(f"  ok  {t}")

dupes = sorted({t for t in targets if targets.count(t) > 1})
if dupes:
    print(f"=== within-episode duplicate targets ===\n  ! {dupes}"); issues += len(dupes)

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
