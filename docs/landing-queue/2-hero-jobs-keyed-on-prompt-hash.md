# 2 — key `hero-jobs.json` on a hash of the PROMPT, not the slot name

**E16. `providers.py`. NOT LANDED.**

## The fault

`docs/hero-jobs.json` is a double-spend guard. It records a Higgsfield `job_id` the
instant it exists, and on re-run:

```python
rec = book.setdefault(key, {})          # key is "hero_A" / "hero_B"
if not rec.get("job_id"):
    job = self._hf("generate", "create", ...)   # ← never reached once an id exists
    ...
self._hf_download(rec["job_id"], path, key)     # ← always re-downloads that job
```

**A guard that can never be cleared becomes a trap.** It answers *"have I already paid
for this?"* when the real question is *"have I already paid for THIS PROMPT?"*

**What it cost, EP15, 3-4 Aug 2026.** Both cover heroes were looked at and rejected — one
carried a competitor's brand, the other had a line of prompt text rendered into the sky.
The prompts were corrected and the PNGs moved aside. **Deleting the PNGs cannot
invalidate a stored job id**, so the engine re-downloaded the same two pictures, the
board offered them again with nothing to say they had been rejected, and **Jodie picked
one in good faith.** Proven by the balance: 75.22, unchanged. Two heroes cannot be
generated for free.

## The change

```python
def _prompt_key(self, slot: str, prompt: str) -> str:
    """THE LEDGER KEY IS THE SLOT *AND* THE PROMPT.

    Same prompt -> same key -> the double-spend protection this ledger was built for,
    working exactly as before. CHANGED prompt -> different key -> a genuine create.
    Nobody has to remember to clear a file, which is the only kind of fix that holds:
    the version that relied on remembering failed on EP15 the first time it mattered.
    """
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
    return f"{slot}:{h}"
```

and in `_generate_heroes`, replace every bare `key` used against `book` with
`self._prompt_key(key, prompts[key])`:

```python
    for key, path in want:
        lk = self._prompt_key(key, prompts[key])
        rec = book.setdefault(lk, {})
        if not rec.get("job_id"):
            ...create...
            rec["slot"] = key
            rec["prompt_sha"] = lk.split(":", 1)[1]
            rec["rejected"] = False        # E16 change 1: rejection is a RECORDED state
        self._hf_download(rec["job_id"], path, key)
```

`todo` must use the same keying, or the cost preview and the create disagree about what
is new.

## Also required by E16 — do not land this half alone

1. **Rejection must be a RECORDED state, not an absent file.** `rejected: true` on the
   ledger entry, so the guard can tell *"already paid for"* from *"already paid for AND
   no good"*. **Moving a file aside is a convention the code cannot see** — which is
   precisely why deleting the PNGs did nothing.
2. **The board must never re-offer a rejected artefact**, and must say so on the card if
   one is somehow still present.
3. **A regeneration is proven by the BALANCE MOVING.** On EP15 a status field, a fresh
   mtime, a byte count and a "completed" job all said the images were new. Only the
   unchanged balance and a byte-compare said otherwise.

## Proof required after landing

Change a hero prompt on a test episode: a NEW job id must be created and **the balance
must move**. Leave it unchanged: the old id must be reused and **the balance must not
move**. Both directions, or the guard has only been half tested.
