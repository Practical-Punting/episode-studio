# The script editor on the board — spec

**Ruled by Jodie, 28 July 2026:** *"I want to be able to edit the words right there on the board in a lovely big pretty space that is easy to navigate."*

This settles the open question in `PP-script-home-design.md` part 2. **Editable, not read-only.** The Google Doc becomes an archive copy written after approval, plus an escape hatch while trust is being built.

---

## 🔴 THE HARD PREREQUISITE — board bug 1, and it is not negotiable
**`PP-board-usability-bugs.md` BUG 1 must be fixed and proven before a single editable character ships.**

Jodie originally set bug 1 to LOW priority because it does not block making episodes. **That priority is now raised to BLOCKER for this work**, and the reason is arithmetic: the bug silently ate a pasted YouTube URL. The same bug applied to a 2,500-word script she has just spent twenty minutes editing destroys twenty minutes of work with no warning and no undo. Losing a link is annoying. Losing a script is the kind of thing that makes a person stop trusting the tool entirely — and Hugh will not be as forgiving as Jodie has been.

**Acceptance test, and it must actually be run:** type into the editor, alt-tab away, wait through at least two board refresh cycles, come back. The text is still there. Ten times, including with the panel open for several minutes.

---

## Safety — because losing a script is worse than any amount of friction
Every one of these exists to make "I lost my work" impossible, not unlikely.

- **Autosave on a debounce** (~2 seconds after typing stops). **No Save button she has to remember.** A Save button is a trap: it works until the one time she alt-tabs first.
- **A visible save state, never silent** — "Saving…" then "Saved 2:14 pm". If it cannot save, it says so loudly and does not pretend.
- **Insert-only version history.** Every save writes a new row to a `script_versions` table rather than overwriting. This matches the rail's standing rule — select/insert/update, **never delete** — and means no edit is ever unrecoverable.
- **"Back to what Claude Code wrote"** is always one click away, however many edits deep she is.
- **Nothing in the editor is destructive.** There is no action that loses text.

---

## The lovely big pretty space
"Big and pretty" is not decoration — it is what makes 2,500 words readable in a browser instead of a downgrade from Google Docs.

- **Takes over the board when open**, closes back to the Words card. Not a small box wedged into a card.
- **Measure of about 70 characters per line.** This is the single biggest lever on long-form readability — wider is genuinely worse, no matter how much screen there is.
- **Generous type:** ~19–20px, line height ~1.7, real paragraph spacing.
- **House colours**, not browser-default grey on white.
- **Full height**, scrolls as one continuous document — not paginated, not a textarea with its own tiny scrollbar.

## Easy to navigate
- **A slim contents rail down one side** with the script's own structure — hook, body sections, midroll, close — that jumps to each. The script already has this shape; the panel should show it.
- **Live counters at the foot:** word count, character count, and estimated spoken duration. Both numbers matter operationally — HeyGen's text variable caps at 10,000 characters (our scripts run ~7,000), and duration drives the credit cost of the render.
- **Find within the script.**
- **"Open in Doc"** stays as an escape hatch until she trusts the panel. It should get *quieter* over time, not be ripped out on day one.

---

## ⚠️ The rule that stops the two writers fighting
Both Claude Code and Jodie can write the script. Without a rule, a CC re-run silently overwrites her edits — the exact class of fault as bug 1, just slower.

**The rule: once a human has edited, the human's version is the truth.**

- The episode row carries `script_edited_by_human_at`.
- If that is set, **the engine must not overwrite `script_snapshot`** — it raises a flag and asks, the same way it does for anything else it cannot decide alone.
- CC may still *read* it freely. Reading is always safe; writing over a person is not.

---

## Order of work
1. **Fix board bug 1** and prove it with the ten-times test. Nothing else starts until this passes.
2. Version history table + autosave + save-state indicator.
3. The panel itself — measure, type, contents rail, counters.
4. `script_edited_by_human_at` and the engine guard.
5. The Doc becomes an after-approval archive write.

**Everything above is ordinary board and rail work.** No new service, no API key, no model call. Claude Code keeps writing the first draft exactly as it does today — this only changes where the words live and who is allowed to overwrite them.
