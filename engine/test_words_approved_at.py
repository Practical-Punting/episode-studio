#!/usr/bin/env python3
"""words_approved_at — the moment a HUMAN approved, not the moment the build read it.

    python engine/test_words_approved_at.py

Jodie asked for "approval -> render startable" to become a measured number rather than
an estimate. `script_approved_at` looked like it already did that and does the opposite:
the ENGINE writes it in step_script_sync when the build re-reads the text, so EP19's is
03:41:59 — TWO SECONDS after started_at. The click happened at an unknown earlier time,
so the interval collapses to roughly zero and always looks excellent.

    ⚠️ A MEASUREMENT THAT CANNOT REPORT A DELAY IS NOT A MEASUREMENT.

So the board stamps `words_approved_at` at the click itself, and that is what pairs with
`render_started_at`.

Writes nothing to the rail: it reads the LIVE column definition and the board's source.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:                                                  # noqa: BLE001
        pass

PASS, FAIL = [], []


def case(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ok  {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  !!  {name}\n      {e}")


APP = (REPO / "app.js").read_text(encoding="utf-8")


def approve_words_patch() -> str:
    """The patch object the approve-words handler actually sends.

    Located by its OWN contents (script_read + title_approved together), not by a line
    number: this file is edited constantly and an offset would rot within a week.
    """
    i = APP.index("script_read: true, title_approved: true")
    start = APP.rindex("const patch = {", 0, i)
    end = APP.index("};", i)
    body = APP[start:end]
    # ⚠️ COMMENTS OUT FIRST. The control below asks whether the board writes
    # `script_approved_at`, and the patch carries a comment explaining that it must
    # NOT — so the first version of this failed on its own explanatory prose. A check
    # that reads comments is checking the documentation, not the code.
    return re.sub(r"//[^\n]*", "", body)


def _the_click_is_stamped():
    patch = approve_words_patch()
    assert "words_approved_at" in patch, (
        "the approve-words patch does not set words_approved_at, so the click is not "
        "recorded and the interval cannot be measured:\n" + patch)
    assert "new Date().toISOString()" in patch, (
        "words_approved_at is in the patch but not set to the time of the click:\n"
        + patch)


case("the approve-words CLICK stamps words_approved_at", _the_click_is_stamped)


def _it_is_not_confused_with_the_engines_stamp():
    """CONTROL FOR THE DISTINCTION ITSELF. If the board ever starts writing
    script_approved_at, or the engine starts writing words_approved_at, the two
    measure the same end of the wait again and the number goes back to being ~0."""
    patch = approve_words_patch()
    assert "script_approved_at" not in patch, (
        "the board is writing script_approved_at, which the ENGINE owns. Both stamps "
        "would then record the same moment and the interval collapses again.")
    eng = re.sub(r"#[^\n]*", "", (HERE / "engine.py").read_text(encoding="utf-8"))
    assert "words_approved_at" not in eng, (
        "the ENGINE is writing words_approved_at. It belongs to the board: the engine "
        "cannot know when a human clicked, only when it started reading.")


case("CONTROL — the board's stamp and the engine's stay separate",
     _it_is_not_confused_with_the_engines_stamp)


def _the_column_exists_on_the_live_database():
    """The artefact, not the migration file. A migration that was written and never
    applied looks identical in the repo."""
    import urllib.request
    sys.path.insert(0, str(HERE))
    import rail as _r
    url, key = _r._URL, _r._KEY      # the engine's own connection, not a second one
    req = urllib.request.Request(
        f"{url}/rest/v1/episodes?select=words_approved_at&limit=1",
        headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode()
    assert "words_approved_at" in body or body.strip() in ("[]", "[{}]"), \
        f"the live table did not return the column: {body[:200]}"


case("the column exists on the LIVE database, not just in a migration file",
     _the_column_exists_on_the_live_database)


def _the_schema_doc_says_which_is_which():
    doc = (REPO / "supabase/SCHEMA.md").read_text(encoding="utf-8")
    assert "words_approved_at" in doc, "SCHEMA.md does not mention the new column"
    assert "Not the approval click" in doc, (
        "SCHEMA.md still lets script_approved_at read as the approval time — which is "
        "the confusion that made this column necessary in the first place.")


case("SCHEMA.md distinguishes the two stamps", _the_schema_doc_says_which_is_which)


print(f"\nwords_approved_at: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
