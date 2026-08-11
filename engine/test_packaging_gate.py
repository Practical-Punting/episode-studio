"""test_packaging_gate.py — the thumbnail and the title card say what the RAIL says.

    THE WORDS WERE CORRECT ON THE RAIL AND THE PICTURES WERE WRONG.
    EP20, 11 Aug 2026. rail title="Bill Benter Professional Gambler",
    rail byline="The power of 'deep state' handicapping" — both right, both approved.
    The built thumbnail put the BYLINE in the big headline, and underneath it a
    sentence in NO rail field at all: "The method used by shrewd computer geeks to
    make millions of dollars on Hong Kong racing". The title card did the same. Both
    reached a human, and both are the first thing a viewer sees.

WHY EVERY EXISTING CHECK PASSED. The builders had a words gate already — the
thumbnail's `l1 + l2 == packaging.hook`, the title card's `title_setup + title_payoff
== packaging.hook`. Every value in those comparisons lives in episode.json, written in
the same pass by the same writer. The file agreed with itself, perfectly, about the
wrong words. The memory has had the name for this since EP16:

    A CONSISTENCY CHECK PROVES SAMENESS, NEVER CORRECTNESS.

CONTROL-FIRST THROUGHOUT. Every case below builds the BAD SHAPE out of the real
templates and proves the gate reports it, before any good shape is trusted to pass.

Run: python engine/test_packaging_gate.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / ".claude/skills/pp-episode-production/scripts"
ASSETS = HERE.parent / ".claude/skills/pp-episode-production/assets"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

import packaging_gate as pg                                     # noqa: E402

PP = Path(os.environ.get("PP_VIDEOS_DIR", str(Path("G:/My Drive") / "PP Videos")))

# EP20's real values — the rail's, and the scramble that shipped past every check.
TITLE = "Bill Benter Professional Gambler"
BYLINE = "The power of 'deep state' handicapping"
INVENTED = ("The method used by shrewd computer geeks to make millions of dollars "
            "on Hong Kong racing")

def episode_dir(n: int) -> Path:
    """Resolve an episode folder BY NUMBER, never by a written-out name.

    The stage-8 close-out renames every published episode's folder, so a literal is a
    fuse. `test_no_hardcoded_episode_paths` caught this suite on its first full run,
    correctly — it had `PP.glob("PP-EP20*")` inline.
    """
    hits = sorted(p for p in PP.glob(f"PP-EP{n:02d}*") if p.is_dir())
    return hits[0] if hits else PP / f"PP-EP{n:02d}"


PASS, FAIL = [], []


def check(name, cond, why=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else "  FAIL ") + name + (f"  <- {why}" if not cond and why else ""))


# --------------------------------------------------------------------------
# Pages are built FROM THE REAL TEMPLATES, not from a fixture written here. A
# hand-written page would drift from the markup the builders substitute into, and
# then this suite would be grading a shape nothing produces.
# --------------------------------------------------------------------------
def thumbnail_page(l1, l2, strap, part=None):
    tpl = (ASSETS / "youtube-thumbnail-template.html").read_text(encoding="utf-8")
    import author_thumbnail as at
    return (tpl.replace(at.SLOT_L1, f'<div class="l1">{l1}</div>')
               .replace(at.SLOT_L2, f'<div class="l2">{l2}</div>')
               .replace(at.SLOT_PART, f'<div class="part">{part}</div>' if part else "")
               .replace(at.SLOT_STRAP, f'<div class="strap">{strap}</div>'))


def title_page(setup, payoff, byline, part=None):
    tpl = (ASSETS / "cards/title-card.html").read_text(encoding="utf-8")
    return (tpl.replace("%%PART_LINE%%",
                        f'  <div id="pt" class="anton pt">{part}</div>' if part else "")
               .replace("%%TITLE_SETUP%%", setup)
               .replace("%%TITLE_BREAK%%", " ")
               .replace("%%TITLE_PAYOFF%%", payoff)
               .replace("%%BYLINE%%", byline))


def cover_page(setup, payoff, subtitle, attribution, part=None):
    tpl = (ASSETS / "ebook-cover-template.html").read_text(encoding="utf-8")
    import author_cover as ac
    title = f'<span class="w">{setup}</span> {payoff}' if setup else payoff
    if part:
        title += f'<span class="part">{part}</span>'
    return (tpl.replace(ac.SLOT_TITLE, f'<div class="title">{title}</div>')
               .replace(ac.SLOT_SUBTITLE, f'<div class="subtitle">{subtitle}</div>')
               .replace(ac.SLOT_BYLINE, f'<div class="byline">{attribution}</div>'))


ATTR = f"{BYLINE} · {pg.COVER_ATTRIBUTION}"


def main():
    print("-- CONTROL: EP20 exactly as it was built, graded against the rail --")
    bad_thumb = thumbnail_page("THE POWER OF", "'DEEP STATE' HANDICAPPING", INVENTED)
    bad_title = title_page("THE POWER OF", "'DEEP STATE' HANDICAPPING", INVENTED)
    for kind, page in (("thumbnail", bad_thumb), ("title_card", bad_title)):
        b = pg.page_faults(kind, page, TITLE, BYLINE)
        joined = " ".join(b)
        check(f"{kind}: it FAILS", len(b) >= 2, "the fault EP20 shipped must be caught")
        check("  (a) the headline is not the title field",
              "the big headline reads" in joined)
        check("      and it says WHICH fault this is — the two are swapped",
              "IT IS THE BYLINE" in joined)
        check("  (b) the small line carries text in NO rail field",
              "appear in NO rail field" in joined)
        check("      and it quotes the invented words back",
              "shrewd" in joined and "geeks" in joined)

    print("\n-- and it PASSES the shape those two were corrected to --")
    good_thumb = thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER", BYLINE)
    good_title = title_page("BILL BENTER", "PROFESSIONAL GAMBLER", BYLINE)
    for kind, page in (("thumbnail", good_thumb), ("title_card", good_title)):
        b = pg.page_faults(kind, page, TITLE, BYLINE)
        check(f"{kind}: zero blockers", not b, f"{b[:1]}")

    print("\n-- each rule fails on its OWN bad shape, so none is carried by another --")
    cases = [
        ("the eyebrow tampered with",
         thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER", BYLINE)
         .replace("How to Win at Horse Racing", "Practical Punting"),
         "fixed series line"),
        ("a headline that is neither field",
         thumbnail_page("SOMETHING", "ELSE ENTIRELY", BYLINE), "big headline reads"),
        ("a sub line that is neither field",
         thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER", "A line somebody liked"),
         "line under the headline"),
        ("a part line invented out of nothing",
         thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER", BYLINE, part="Chapter Four"),
         "appear in NO rail field"),
    ]
    for name, page, needle in cases:
        b = pg.page_faults("thumbnail", page, TITLE, BYLINE)
        check(name, any(needle in x for x in b), f"reported: {b[:1]}")

    print("\n-- a SERIES POSITION is approved by its own source, and only for its zone --")
    # EP12's real shape: the hook drops the part because the part has its own line.
    part_page = thumbnail_page("HIDDEN", "ACES", "What the barrier is really worth",
                               part="Part 2")
    args = ("Hidden Aces", "What the barrier is really worth")
    b = pg.page_faults("thumbnail", part_page, *args)
    check("CONTROL: with no part source, 'Part 2' is words from nowhere", b != [],
          "if this passes, rule 4 is not actually reading the part zone")
    b = pg.page_faults("thumbnail", part_page, *args, "Hidden Aces — Part 2")
    check("  named by packaging.ebook_title, it passes", not b, f"{b[:1]}")
    leak = thumbnail_page("HIDDEN", "ACES", "Part 2 is where the barrier really counts")
    b = pg.page_faults("thumbnail", leak, "Hidden Aces",
                       "What the barrier is really worth", "Hidden Aces — Part 2")
    check("  and its words do NOT leak into the other zones", b != [],
          "part_source must widen the part zone only")

    print("\n-- an EMPTY byline leaves the zone BLANK; it does not license a sentence --")
    b = pg.page_faults("thumbnail", thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER", ""),
                       TITLE, "")
    check("an empty byline with an empty zone passes", not b, f"{b[:1]}")
    b = pg.page_faults("thumbnail",
                       thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER", INVENTED),
                       TITLE, "")
    check("  an empty byline with a WRITTEN zone fails", b != [],
          "an empty field is not permission to write one")

    print("\n-- it compares WORDS, not keystrokes --")
    b = pg.page_faults("thumbnail",
                       thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER",
                                      "The power of \u2018deep state\u2019 handicapping"),
                       TITLE, BYLINE)
    check("curly quotes on the page match straight ones on the rail", not b,
          "a gate that cries wolf on typography is one somebody switches off")
    b = pg.page_faults("thumbnail", thumbnail_page("Bill Benter", "Professional Gambler",
                                                   BYLINE), TITLE, BYLINE)
    check("  and the headline's capitals are styling, not a difference", not b, f"{b[:1]}")

    print("\n-- THE E-BOOK COVER, which has no eyebrow and a THIRD text zone --")
    # It goes on Hugh's website (Jodie, 11 Aug 2026), so it is graded like the others.
    # EP20 carried the invented strap TWICE: as the subtitle, and in front of the
    # standing attribution — the same wrong sentence on one cover in two places.
    bad_cover = cover_page("THE POWER OF", "'DEEP STATE' HANDICAPPING", INVENTED,
                           f"{INVENTED} · {pg.COVER_ATTRIBUTION}")
    b = pg.page_faults("ebook_cover", bad_cover, TITLE, BYLINE)
    joined = " ".join(b)
    check("CONTROL: the cover EP20 shipped FAILS", len(b) >= 3, f"only {len(b)}")
    check("  the headline is not the title field", "the big headline reads" in joined)
    check("  the subtitle is not the byline field", "the line under the headline" in joined)
    check("  and the ATTRIBUTION is called out on its own",
          "the attribution line reads" in joined)
    good_cover = cover_page("BILL BENTER", "PROFESSIONAL GAMBLER", BYLINE, ATTR)
    check("the corrected cover PASSES", not pg.page_faults("ebook_cover", good_cover,
                                                           TITLE, BYLINE),
          f"{pg.page_faults('ebook_cover', good_cover, TITLE, BYLINE)[:1]}")
    check("  a missing eyebrow is not held against it",
          not any("eyebrow" in x for x in
                  pg.page_faults("ebook_cover", good_cover, TITLE, BYLINE)),
          "the cover has no eyebrow zone at all")
    check("  but the thumbnail is STILL failed for a missing one",
          any("eyebrow" in x for x in pg.page_faults(
              "thumbnail",
              thumbnail_page("BILL BENTER", "PROFESSIONAL GAMBLER", BYLINE)
              .replace("How to Win at Horse Racing", ""), TITLE, BYLINE)),
          "if this passes, HAS_EYEBROW has switched the check off for everyone")
    check("  the standing suffix alone is not enough — the byline must lead it",
          pg.page_faults("ebook_cover",
                         cover_page("BILL BENTER", "PROFESSIONAL GAMBLER", BYLINE,
                                    pg.COVER_ATTRIBUTION), TITLE, BYLINE) != [])
    check("  and the suffix's words do NOT leak into the subtitle",
          pg.page_faults("ebook_cover",
                         cover_page("BILL BENTER", "PROFESSIONAL GAMBLER",
                                    "from the Practical Punting archives", ATTR),
                         TITLE, BYLINE) != [])

    print("\n-- THE BUILT EP20 PAGES, as they now stand on disk --")
    d = episode_dir(20)
    if d.is_dir() and (d / "thumbnail").is_dir():
        res = pg.check_episode(d, TITLE, BYLINE, TITLE)
        check("all three pages were found and graded", len(res["checked"]) == 3,
              f"{res['checked']}")
        check("  and all three carry the rail's words", not res["blockers"],
              f"{res['blockers'][:1]}")
    else:
        check("EP20 is on this machine to grade", False)

    print("\n-- the two enforcement points are DIFFERENT checks, on purpose --")
    # The builders grade a page against packaging (catches a builder bug, and works on
    # a hand run). The engine grades the same page against the RAIL (catches the
    # packaging itself being wrong — EP20's actual fault). Proving the weaker one is
    # genuinely weaker is what stops someone deleting the stronger one as a duplicate.
    b_pack = pg.page_faults("title_card", bad_title, "Bill Benter Professional Gambler",
                            INVENTED)
    check("a page that agrees with WRONG packaging still fails the rail gate",
          pg.page_faults("title_card",
                         title_page("BILL BENTER", "PROFESSIONAL GAMBLER", INVENTED),
                         TITLE, BYLINE) != [])
    check("  while the packaging-level gate cannot see it",
          pg.page_faults("title_card",
                         title_page("BILL BENTER", "PROFESSIONAL GAMBLER", INVENTED),
                         "Bill Benter Professional Gambler", INVENTED) == [],
          "if this ever passes, the two gates have become the same check")
    assert b_pack is not None

    print("\n-- ONE NAME EVERYWHERE A VIEWER LOOKS --")
    # `check_one_name` compares FOUR places an episode is named and it caught EP20 at
    # youtube_copy on 11 Aug: seating only the hook had left three of them behind.
    # The convention is read off EP16-EP19, not invented — the rail's TITLE is the
    # episode's NAME and goes in all four; the byline is the promise line, a different
    # thing. EP20's writer had them the other way round, which was the whole fault.
    import tempfile
    import providers
    import youtube_title as ytl
    # ⚠️ THE FIXTURE IS EP20 AT 07:57Z ON 11 AUG, NOT A TIDY INVENTION. The pictures
    # had been corrected and the three NAME fields had not, which is the exact state
    # check_one_name halted on — and a fixture that is internally consistent proves
    # nothing here, because the whole failure mode is fields disagreeing.
    SCRAMBLED = {
        "title": "The Power of 'Deep State' Handicapping",
        "packaging": {"hook": TITLE,
                      "byline": BYLINE,
                      "ebook_title": "The Power of 'Deep State' Handicapping",
                      "youtube_title": "The Power of 'Deep State' Handicapping "
                                       "| How to Win at Horse Racing"},
        "cover": {"title_setup": "BILL BENTER", "title_payoff": "PROFESSIONAL GAMBLER",
                  "byline": f"{INVENTED} · {pg.COVER_ATTRIBUTION}"},
        "thumbnail": {"l1": "BILL BENTER", "l2": "PROFESSIONAL GAMBLER",
                      "strap_break_after": "geeks"},
    }
    faults = ytl.check_one_name(SCRAMBLED)
    check("CONTROL: the file EP20 halted on IS called different things", len(faults) == 1)
    check("  and the halt names the title card against the other three",
          bool(faults) and "BILL BENTER PROFESSIONAL GAMBLER" in faults[0]
          and "Deep State" in faults[0])
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "docs").mkdir()
        (d / "docs/episode.json").write_text(json.dumps(SCRAMBLED), encoding="utf-8")
        said = providers.seat_packaging_from_rail(
            {"title": TITLE, "byline": BYLINE}, d)
        seated = json.loads((d / "docs/episode.json").read_text(encoding="utf-8"))
        check("  seating from the rail settles all four", not ytl.check_one_name(seated))
        for where, got in ytl.episode_names(seated).items():
            check(f"    {where.split('(')[0].strip()} = the rail's title",
                  pg.fold(got) == pg.fold(TITLE), f"{got!r}")
        check("  the YouTube title takes the house form from youtube_title.py",
              seated["packaging"]["youtube_title"] == ytl.derive(TITLE))
        check("  the BYLINE is not overwritten with the name — it is a different thing",
              seated["packaging"]["byline"] == BYLINE)
        check("  the cover attribution is the byline plus the standing suffix",
              seated["cover"]["byline"] == f"{BYLINE} · {pg.COVER_ATTRIBUTION}")
        check("  the strap break word is dropped when it is not in the new byline",
              seated["thumbnail"]["strap_break_after"] is None,
              "'geeks' is not a word of the rail's byline; a stale break halts the build")
        # NOT a count. Every field that actually moved must be NAMED in the sentence
        # that goes in the run log — that is the property a magic number stands in for,
        # and the number would go stale the moment a fixture changes by one field.
        moved = [k for k in ("title", "ebook_title", "youtube_title", "cover.byline",
                             "strap_break_after")
                 if str(SCRAMBLED.get(k) or "") != str(seated.get(k) or "")
                 or k not in SCRAMBLED]
        check("  and it NAMES every field it moved",
              all(k.split(".")[-1] in said for k in moved), f"{said[:160]}")
        check("    including the ones a reader would not have predicted",
              "youtube_title" in said and "strap_break_after" in said)
        again = providers.seat_packaging_from_rail(
            {"title": TITLE, "byline": BYLINE}, d)
        check("  running it twice changes nothing the second time",
              "nothing re-seated" in again, again[:80])

    print("\n-- the engine actually RUNS it, and seats the words first --")
    prov = (HERE / "providers.py").read_text(encoding="utf-8")
    live = [ln for ln in prov.splitlines() if not ln.strip().startswith("#")]
    src = "\n".join(live)
    check("render_cards seats the packaging from the rail",
          src.count("seat_packaging_from_rail(ep, d)") >= 2,
          "both the title card path and the thumbnail path")
    check("  and every path that builds one grades it against the rail",
          src.count("assert_packaging_carries_the_rail(ep, d)") >= 3,
          "cards/title, thumbnail, AND the e-book — the PDF goes on Hugh's website")
    check("  the cover's attribution is DERIVED from the byline, not typed per episode",
          "COVER_ATTRIBUTION" in src, "EP16-EP19 all carry it to the character")
    check("  the seating reads the rail's OWN fields, not episode.json's",
          'ep.get("title")' in src and 'ep.get("byline")' in src)
    for script in ("author_thumbnail.py", "author_title_card.py"):
        s = (SCRIPTS / script).read_text(encoding="utf-8")
        check(f"  {script} grades its own page too",
              "pg.page_faults(" in s, "a hand run must be covered as well")

    print(f"\npackaging gate: {len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
