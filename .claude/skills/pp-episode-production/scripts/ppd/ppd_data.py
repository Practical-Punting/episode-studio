#!/usr/bin/env python3
"""ppd_data.py — load the PPD promo, PROVE the proof day's numbers, and measure every cue.

    python ppd_data.py <job_dir>        prints the proved figures and the cue sheet

Two files, on purpose (Hugh's brief §4: "keep the example as a self-contained mid-section"):
  overlay/ppd-proof-day.json   the proof day — selections, dividends, the two guide strategies
  overlay/ppd-promo.json       every other on-screen word, the swappable offer, the cue phrases

THE RULES (the FBX lessons, enforced here, not remembered):
1. EVERY TOTAL IS RECOMPUTED FROM THE ROWS. `stated` holds what the brief printed; this module adds the
   rows up itself and HALTS on any disagreement. A number on screen is a reading of the data, never a
   second copy of it ("data is lifted, never re-typed").
2. EVERY TIME IS MEASURED. Cue phrases are found, IN ORDER, in renders/words-forced.json (the self-checking
   fbx_align.py). A phrase not found halts with its name. Nothing is estimated.
3. ONE CLOCK. The title head (ppd-promo.json -> title_head, 7.0 s) is added HERE, ONCE. Cards, plan,
   assembly, QC and the SRT all read this sheet (the EP18 lesson: a chip 7 s early because one reader
   skipped the crossing).
"""
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fbx"))
import fbx_data as fd  # noqa: E402  (timeline + phrase finder, shared with FBX)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                             # noqa: BLE001
        pass

Halt = fd.Halt


def D(x):
    return Decimal(str(x))


def money(x, places=2):
    return f"${D(x):,.{places}f}"


def pct(x, places=1):
    q = D(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return ("+" if q >= 0 else "") + f"{q:.{places}f}%"


def bet_name(s):
    """The house format, always in full: 'Flemington Race 8 no.5 Cosmic Crusader' (brief §3)."""
    return f"{s['meeting']} Race {s['race']} no.{s['no']} {s['horse']}"


def load(job: Path):
    promo = json.loads((job / "overlay" / "ppd-promo.json").read_text(encoding="utf-8"))
    day = json.loads((job / "overlay" / "ppd-proof-day.json").read_text(encoding="utf-8"))
    return promo, prove(day)


def prove(day):
    """Recompute every figure from the rows. Returns day + 'calc'; raises Halt listing every disagreement."""
    faults = []
    stake = D(day["stake"])
    sel = day["selections"]
    won = [s for s in sel if s["finish"] == 1]
    placed = [s for s in sel if s.get("place")]
    for s in sel:
        if (s["finish"] == 1) != bool(s.get("win")):
            faults.append(f"{s['horse']}: finish {s['finish']} but win dividend {s.get('win')!r}")
        if s["finish"] > 3 and s.get("place"):
            faults.append(f"{s['horse']}: finished {s['finish']} but has a place dividend")
    n = len(sel)
    win_back = sum((D(s["win"]) * stake for s in won), D(0))
    pl_back = sum((D(s["place"]) * stake for s in placed), D(0))
    calc = {"win": (n * stake, win_back), "place": (n * stake, pl_back), "each_way": (2 * n * stake, win_back + pl_back)}
    out = {}
    for k, (st, back) in calc.items():
        prof = back - st
        mine = {"staked": f"{st:.2f}", "back": f"{back:.2f}", "profit": f"{prof:.2f}", "roi": pct(prof / st * 100)}
        for f, v in mine.items():
            if day["stated"][k][f] != v:
                faults.append(f"{k} {f}: brief says {day['stated'][k][f]}, the rows give {v}")
        out[k] = mine
    sr = pct(D(len(won)) / n * 100).lstrip("+")
    for f, v in (("winners", len(won)), ("selections", n), ("strike_rate", sr)):
        if day["stated"][f] != v:
            faults.append(f"{f}: brief says {day['stated'][f]}, the rows give {v}")

    # the field-for-third trifecta: combinations = (2 x runners) - 4, a hit when the top two fill 1st/2nd either way
    t = day["trifecta"]
    unit = D(t["unit"])
    cost, back, hits = D(0), D(0), 0
    for r in t["races"]:
        r["combos"] = 2 * r["runners"] - 4
        r["cost"] = f"{r['combos'] * unit:.2f}"
        r["hit"] = set(r["result"][:2]) == set(r["top_two"])
        cost += r["combos"] * unit
        hits += r["hit"]
        back += D(r["back"]) if r["hit"] else 0
        if not r["hit"] and D(r["back"]):
            faults.append(f"trifecta {r['meeting']} R{r['race']}: a return with no hit")
    tm = {"cost": f"{cost:.2f}", "back": f"{back:.2f}", "profit": f"{back - cost:.2f}", "roi": pct((back - cost) / cost * 100),
          "hits": hits, "races": len(t["races"])}
    for f, v in tm.items():
        if t["stated"][f] != v:
            faults.append(f"trifecta {f}: brief says {t['stated'][f]}, the races give {v}")

    # backing two: a $10 stake split across the top two; a hit when one of them wins
    b = day["backing_two"]
    st2, back2, hits2 = D(0), D(0), 0
    for r in b["races"]:
        if D(r["a"]["stake"]) + D(r["b"]["stake"]) != D(b["stake"]):
            faults.append(f"backing two {r['meeting']} R{r['race']}: stakes do not add to {b['stake']}")
        st2 += D(b["stake"])
        hit = r["winner"] in (r["a"]["no"], r["b"]["no"])
        hits2 += hit
        back2 += D(r["back"]) if hit else 0
    bm = {"staked": f"{st2:.2f}", "back": f"{back2:.2f}", "profit": f"{back2 - st2:.2f}", "roi": pct((back2 - st2) / st2 * 100),
          "hits": hits2, "races": len(b["races"])}
    for f, v in bm.items():
        if b["stated"][f] != v:
            faults.append(f"backing two {f}: brief says {b['stated'][f]}, the races give {v}")
    # the example race must be one of the races, in both strategies (it is drawn on two cards)
    ex = day["example_race"]
    pick = lambda rs: next((r for r in rs if r["meeting"] == ex["meeting"] and r["race"] == ex["race"]), None)
    if not pick(t["races"]) or not pick(b["races"]):
        faults.append(f"example race {ex} is not in both strategies")
    if faults:
        raise Halt("The proof day does not add up — nothing built:\n  - " + "\n  - ".join(faults))
    bank = D(day["bank"])
    day["calc"] = {**out, "won": won, "missed": [s for s in sel if s["finish"] != 1], "strike_rate": sr,
                   "trifecta": tm, "backing_two": bm, "tri_ex": pick(t["races"]), "b2_ex": pick(b["races"]),
                   "bet_pct": f"{stake / bank * 100:.1f}%", "race_limit": money(bank * D(day['race_limit_pct']) / 100, 0)}
    return day


# ---------------------------------------------------------------------------- cues
def cue_sheet(job: Path, promo):
    """{key: {start, end, pb (mid-pause before), pa (mid-pause after)}} ON THE FINISHED CLOCK (+ title_head)."""
    words, flat = fd.timeline(job)
    head = float(promo.get("title_head", 0.0))
    W = [dict(w, start=w["start"] + head, end=w["end"] + head) for w in words]
    T = {"head": head, "speech_start": round(W[0]["start"], 3), "speech_end": round(W[-1]["end"], 3)}
    after = 0.0
    for key, phrase in promo["cues"]:
        i0, i1 = fd.find(W, flat, phrase, after)
        pb = round((W[i0 - 1]["end"] + W[i0]["start"]) / 2, 3) if i0 else round(W[i0]["start"] - 0.25, 3)
        pa = round((W[i1]["end"] + W[i1 + 1]["start"]) / 2, 3) if i1 + 1 < len(W) else round(W[i1]["end"] + 0.25, 3)
        # every word of the phrase, so a card can reveal a quote word by word on Gordon's own timing
        T[key] = {"start": round(W[i0]["start"], 3), "end": round(W[i1]["end"], 3), "pb": pb, "pa": pa,
                  "words": [[W[i]["word"], round(W[i]["start"], 3), round(W[i]["end"], 3)] for i in range(i0, i1 + 1)]}
        after = W[i0]["start"]
    return T


def main():
    job = Path(sys.argv[1]).resolve()
    try:
        promo, day = load(job)
        T = cue_sheet(job, promo)
    except Halt as e:
        sys.exit(str(e))
    c = day["calc"]
    print(f"proof day OK — {day['label']}, {day['date_label']}: {len(c['won'])} winners from {len(day['selections'])} ({c['strike_rate']})")
    for k in ("win", "each_way", "place"):
        print(f"  {k:9s} {money(c[k]['staked'])} -> {money(c[k]['back'])}  {c[k]['roi']}")
    print(f"  trifecta  {money(c['trifecta']['cost'])} -> {money(c['trifecta']['back'])}  {c['trifecta']['roi']}  "
          f"{c['trifecta']['hits']} from {c['trifecta']['races']}")
    print(f"  backing 2 {money(c['backing_two']['staked'])} -> {money(c['backing_two']['back'])}  {c['backing_two']['roi']}")
    for k, v in T.items():
        if isinstance(v, dict):
            print(f"  {k:16s} {v['start']:8.2f} – {v['end']:8.2f}   pb {v['pb']:8.2f}  pa {v['pa']:8.2f}")
        else:
            print(f"  {k:16s} {v}")


if __name__ == "__main__":
    main()
