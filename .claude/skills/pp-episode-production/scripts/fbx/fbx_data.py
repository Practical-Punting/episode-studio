#!/usr/bin/env python3
"""fbx_data.py — load an FBX week, PROVE its numbers, and turn anchor phrases into a cue sheet.

    python fbx_data.py <job_dir>          prints the validated week + cue sheet,
                                          writes overlay/cues.json

The week lives in overlay/fbx-week.json (one file per week). Two rules, both enforced here:

1. EVERY TOTAL IS RECOMPUTED FROM THE SIX ROWS. The typed totals in `stated_totals` are what
   the fact sheet printed; this module adds up the rows itself and HALTS if a single figure
   disagrees. A number on screen is a reading of the data, never a second copy of it
   (PP: "data is lifted, never re-typed").
2. EVERY TIME IS MEASURED. Cue phrases are found in renders/words-forced.json (fbx_align.py);
   a phrase that is not found HALTS with its name. Nothing is estimated from word counts.
"""
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

NUM_WORDS = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE", 6: "SIX", 7: "SEVEN",
             8: "EIGHT", 9: "NINE", 10: "TEN", 11: "ELEVEN", 12: "TWELVE"}
TAG_ORDER = ["Core", "Victorian Select", "Value Select"]


class Halt(Exception):
    pass


def D(x):
    return Decimal(str(x))


def money(x):
    return f"${D(x):.2f}"


def signed(x, places=2):
    q = D(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return ("+" if q >= 0 else "") + f"{q:.{places}f}"


def load_week(job: Path):
    wk = json.loads((job / "overlay" / "fbx-week.json").read_text(encoding="utf-8"))
    sel = wk["selections"]
    stake = D(wk.get("stake_units", 1))
    faults = []

    for s in sel:
        if s["tags"] != [t for t in TAG_ORDER if t in s["tags"]] or "Core" not in s["tags"]:
            faults.append(f"{s['horse']}: tags {s['tags']} are not Core-first in the order {TAG_ORDER}")
        if s["finish"] == 1 and not s.get("win"):
            faults.append(f"{s['horse']}: finished 1st but has no win price")
        if s["finish"] != 1 and s.get("win"):
            faults.append(f"{s['horse']}: has a win price but did not win")

    n = len(sel)
    won = [s for s in sel if s["finish"] == 1]
    placed = [s for s in sel if s.get("place")]
    win_ret = sum((D(s["win"]) * stake for s in won), D(0))
    pl_ret = sum((D(s["place"]) * stake for s in placed), D(0))
    calc = {
        "win": {"staked": n * stake, "returned": win_ret},
        "place": {"staked": n * stake, "returned": pl_ret},
        "each_way": {"staked": 2 * n * stake, "returned": win_ret + pl_ret},
    }
    for k, v in calc.items():
        v["profit"] = v["returned"] - v["staked"]
        v["roi"] = v["profit"] / v["staked"] * 100
        st = wk["stated_totals"][k]
        mine = {"staked": f"{v['staked']:.2f}", "returned": f"{v['returned']:.2f}",
                "profit": signed(v["profit"]), "roi": signed(v["roi"], 1) + "%"}
        for f, val in mine.items():
            if st[f] != val:
                faults.append(f"{k} {f}: fact sheet says {st[f]}, the six rows add up to {val}")
        v.update(mine)
    for f, val in (("won", len(won)), ("placed", len(placed)), ("runners", n)):
        if wk["stated_totals"][f] != val:
            faults.append(f"{f}: fact sheet says {wk['stated_totals'][f]}, the rows give {val}")
    gaps = sorted(sel, key=lambda s: -D(s["gap"]))
    focus = [s["horse"] for s in sel if s.get("gap_focus")]
    if focus and focus != [gaps[0]["horse"]]:
        faults.append(f"gap_focus is {focus} but the biggest gap is {gaps[0]['horse']}")
    top_won = all(s["finish"] == 1 for s in gaps[:len(won)])
    if faults:
        raise Halt("The week's data does not add up — nothing built:\n  - " + "\n  - ".join(faults))

    up = wk["date_label"].upper()
    fill = {"date_label_upper": up, "won": len(won), "runners": n}
    copy = {k: v.format(**fill) for k, v in wk["copy"].items()}
    head1 = f"{len(won)} WINNER{'S' if len(won) != 1 else ''} FROM {n}."
    head2 = ("ALL " + NUM_WORDS.get(n, str(n)) + " PLACED.") if len(placed) == n else \
        f"{NUM_WORDS.get(len(placed), len(placed))} OF {n} PLACED."
    return {"raw": wk, "sel": sel, "won": won, "placed": placed, "calc": calc, "gaps": gaps,
            "top_gaps_all_won": top_won, "copy": copy, "head1": head1, "head2": head2}


# ---------------------------------------------------------------------------- cues
def toks(word):
    return [t for t in re.split(r"[\s\-]+", re.sub(r"[^a-z0-9\s\-']", "", word.lower())) if t]


def timeline(job: Path):
    words = json.loads((job / "renders" / "words-forced.json").read_text(encoding="utf-8"))
    flat = []   # (token, word_index)
    for i, w in enumerate(words):
        for t in toks(w["word"]):
            flat.append((t, i))
    return words, flat


def find(words, flat, phrase, after=0.0, before=1e9):
    p = toks(phrase)
    for k in range(len(flat) - len(p) + 1):
        if [t for t, _ in flat[k:k + len(p)]] == p:
            i0, i1 = flat[k][1], flat[k + len(p) - 1][1]
            if words[i0]["start"] >= after - 1e-6 and words[i0]["start"] < before:
                return i0, i1
    raise Halt(f"Cue phrase {phrase!r} was not found in this render's words "
               f"(between {after:.2f}s and {min(before, 1e8):.2f}s). Check the phrase in "
               f"overlay/fbx-week.json against the spoken script. No time was guessed.")


def cue_sheet(job: Path, wk):
    words, flat = timeline(job)
    C = wk["raw"]["cues"]

    def at(phrase, after=0.0, before=1e9):
        i0, i1 = find(words, flat, phrase, after, before)
        return words[i0]["start"], words[i1]["end"], i0, i1

    def pause_before(i0):          # the middle of the pause in front of word i0
        return round((words[i0 - 1]["end"] + words[i0]["start"]) / 2, 2) if i0 else 0.0

    def pause_after(i1):
        return round((words[i1]["end"] + words[i1 + 1]["start"]) / 2, 2) if i1 + 1 < len(words) \
            else round(words[i1]["end"] + 0.25, 2)

    T = {}
    T["hook"] = at(C["hook"])[0]
    _, _, i, _ = at(C["report_from"]); T["report_in"] = pause_before(i)
    _, _, i, _ = at(C["results_from"]); T["results_in"] = pause_before(i)
    _, _, i, _ = at(C["summary_from"], T["results_in"]); T["summary_in"] = pause_before(i)
    rows = {}
    for s in wk["sel"]:
        st, _, _, _ = at(s["horse"], T["results_in"], T["summary_in"])
        rows[s["horse"]] = round(st, 2)
    T["rows"] = rows
    T["units_on"] = at(C["units_on"], T["summary_in"])[0]
    T["roi_on"] = at(C["roi_on"], T["summary_in"])[0]
    T["placed_on"] = at(C["placed_on"], T["summary_in"])[0]
    _, _, i, _ = at(C["gap_from"], T["summary_in"]); T["gap_in"] = pause_before(i)
    gs, ge, _, _ = at(C["gap_gold_on"], T["gap_in"])
    nwon = len(wk["won"])
    T["gold"] = [round(gs + k * (ge - gs) / nwon, 2) for k in range(nwon)]
    _, _, _, i1 = at(C["gap_out_after"], T["gap_in"]); T["gap_out"] = pause_after(i1)
    _, _, i, _ = at(C["join_from"], T["gap_out"]); T["join_in"] = pause_before(i)
    T["lower_third_on"] = at(C["lower_third_on"], T["join_in"])[0]
    _, _, i, _ = at(C["rg_from"], T["join_in"]); T["rg_in"] = pause_before(i)
    T["speech_start"] = words[0]["start"]
    T["speech_end"] = words[-1]["end"]
    order = sorted(rows.values())
    if order != sorted(order) or len(set(order)) != len(order):
        raise Halt("two horses resolved to the same moment")
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in T.items()}


def main():
    job = Path(sys.argv[1]).resolve()
    try:
        wk = load_week(job)
        T = cue_sheet(job, wk)
    except Halt as e:
        sys.exit(str(e))
    print("week OK —", wk["head1"], wk["head2"])
    for k, v in wk["calc"].items():
        print(f"  {k:9s} staked {v['staked']} returned {v['returned']} profit {v['profit']} ROI {v['roi']}")
    print("  gap order:", ", ".join(f"{s['horse']} {s['gap']}" for s in wk["gaps"]),
          "| top gaps all won:", wk["top_gaps_all_won"])
    (job / "overlay" / "cues.json").write_text(json.dumps(T, indent=1), encoding="utf-8")
    print(json.dumps(T, indent=1))


if __name__ == "__main__":
    main()
