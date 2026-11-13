"""A "reading" substitution changes what the READER SAYS and never what the e-book PRINTS.

    python engine/test_twoway_reading_scope.py

EP59 (Jodie, 13 Nov 2026, Cowork's reading fixes): Steve says an aside instead of reading the article's
two-horse table aloud, while "the e-book prints the ticket list, both charts and the full table" — and the
e-book still takes the typo fixes ("6/12" → "6/1"). Real data: EP59's own substitutions file.
CONTROL: the same entry with scope "all" WOULD put the aside into the e-book (so the skip is what saves it).
"""
import json, os, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / ".claude/skills/pp-episode-production/scripts"))
import tempfile, shutil   # noqa: E402
import twoway_split as ts  # noqa: E402
import author_ebook as ae  # noqa: E402

PP = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    if not ok:
        fails.append(label)


docs = next(PP.glob("PP-EP59-*")) / "docs"
subs = ts.load_substitutions(docs)
turns = json.loads((docs / "turns.json").read_text(encoding="utf-8"))["turns"]
table = next(s for s in subs if s.get("item") == 15)
check("EP59's table fix is scope 'reading'", table.get("scope") == "reading")
reading = ts.reading_turns(turns, subs)
t18 = next(t for t in reading if t["n"] == 18)["text"]
check("the READER says the aside, not the table", "I won't read it out" in t18 and "|" not in t18)
article = [p for t in turns for p in t["text"].split("\n\n")]
book, done = ae.apply_sanctioned(article, str(docs))
flat = "\n".join(book)
check("the E-BOOK still prints the table", "| YOUR LINE | ODDS NEEDED |" in flat and "I won't read it out" not in flat)
check("the e-book takes the typo fix 6/12 -> 6/1", "rate 6/1 who goes off" in flat and "6/12" not in flat)
check("the e-book takes the ticket-list corrections", "5-3-2, 5-1-23467" in flat and "5-23467-1" in flat)
check("the e-book keeps the article's own figures where only the READING changed", "$112" in flat)

sand = pathlib.Path(tempfile.mkdtemp(prefix="scope_"))
body = json.loads((docs / "sanctioned-substitutions.json").read_text(encoding="utf-8"))
# (item 13 — one paragraph, "If you make a horse 6 / 5 …" said as "six to five": the book must keep "6 / 5")
check("the e-book keeps item 13's printed odds", "If you make a horse 6 / 5" in flat)
body["substitutions"] = [dict(s, scope="all") if s.get("item") == 13 else s for s in body["substitutions"]]
(sand / "sanctioned-substitutions.json").write_text(json.dumps(body), encoding="utf-8")
book2, _ = ae.apply_sanctioned(article, str(sand))
check("CONTROL: the same item-13 fix with scope 'all' WOULD put the spoken words into the book",
      "If you make a horse six to five" in "\n".join(book2))
shutil.rmtree(sand, ignore_errors=True)
print(f"\nreading scope: {'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
sys.exit(1 if fails else 0)
