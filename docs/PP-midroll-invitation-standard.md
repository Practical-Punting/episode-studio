# PP — Mid-video like/subscribe invitation (standing rule)
*Added 23 Jul 2026. Hugh's idea, style approved by Jodie. Applies to EVERY episode. Lives in the script-creation step, alongside the standing outro.*

*Copied to the Drive by Cowork on 26 Jul 2026 because Claude Code could not see it: it existed only in the claude.ai project, while the pp-episode-script skill names it as a base standard. That was a dangling reference. It now lives here so both sides can read the same words.*

## The rule
Gordon gives **ONE** gentle, authentic invitation to like & subscribe, placed in the **MIDDLE** of the video — because there's a lot of competing content, and we want the steady, sensible material to reach the right people.

- **Placement:** a natural breath/transition, roughly the middle of the episode (~45–55% through), on a beat boundary with Gordon on camera (MCU). Never over a motion card, never mid-concept, never bunched near the outro. Once per episode, once only.
- **Tone:** the same voice as the standing outro — warm, plain, wry, Australian. **No hype, no "smash that like button", no promises.** A quiet, honest ask tied to value, then straight back to the content.
- **Shape (fixed):** soft value hook ("if **this video** is helping you") → the ask (a like helps others find it; subscribe) → the cadence line → a light, wry nod to the noise out there → return to content ("right — where were we").
- **Name the video at every ask (Jodie, 28 Jul 2026):** "this video", never a bare "this". Narration is exempt — see `PP-STANDARDS.md` §Mid-video for the principle and its origin.

## 🔒 THE WORDING COMES FROM A FIXED POOL OF TEN (Jodie, 28 Jul 2026)
**This SUPERSEDES the previous rule and replaces it entirely. Do not restore the old wording.** The retired clause read: *"Unlike the standing outro (which is verbatim), this line is **reworded slightly each episode** — same shape, beats and tone, fresh phrasing — so it never sounds canned. Rotate a small set of variants or reword each time."*

It asked for fresh prose every episode, which meant the build was writing the ask — and a build that writes its own copy can write anything.

- **Ten pre-approved lines, `L0`…`L9`, in `docs/midroll-line-pool.md`. Episode N takes `L[N mod 10]`, strictly in order.** The pool **wraps** rather than exhausting, so the build never halts for want of a line.
- **They are never rewritten.** Changing one is a new batch approval, not an edit.
- **HARD FAIL if the midroll paragraph is byte-identical to any of the NINE immediately preceding episodes** — nine, not ten, because a ten-line cycle recurs at exactly ten-episode intervals. Full reasoning in `PP-STANDARDS.md` §END SEQUENCE item 4.
- **The on-screen chip is separate and does NOT rotate** — fixed standing furniture, identical every episode.

## Cadence line — LIVE VARIABLE
Current upload cadence is **DAILY** (as of Jul 2026), moving to **weekly** later. The line must reflect the current cadence — e.g. *"a fresh one every day at the moment, weekly down the track."* **Update this note when the cadence actually changes to weekly.**

## The ten lines
**They live in `docs/midroll-line-pool.md`, and only there** — one home, per `PP-STANDARDS.md` §WHERE RULES LIVE. That file also carries the `ep → line id` registry and the chip's locked values.

*The three "example variants" that used to sit here were removed on 28 Jul 2026 and are NOT to be restored. They illustrated a rule that no longer exists, and illustrative prose beside a fixed pool is how someone ends up writing an eleventh line.*

## How it flows through the pipeline
- **Added content beyond the article** → Hugh proposed it (blessed in principle) and Jodie approved the style; the *wording* is now taken verbatim from the pool of ten (was: "the *phrasing* varies per episode" — retired 28 Jul 2026).
- In `episode.json` it's its **own beat** (`cta-midroll`), so timing and assembly place it correctly.
- It's part of the **spoken script Jodie renders in HeyGen** (same avatar/voice/background), so it's baked into the presenter master like any other beat.
- Whoever writes the script — Cowork **or** Claude Code — includes it, because it lives in the shared standards (`pp-standards.md`) both follow.

## Status
Locked into the standards. Style approved by Jodie 23 Jul 2026. **Wording locked to the pool of ten, approved as a batch 28 Jul 2026 — never rewritten** (was: "phrasing varies per episode"). Cadence line currently DAILY; when it moves to weekly the WHOLE POOL needs a fresh batch approval, because the cadence is baked into all ten lines.

---
## EP11 CHECK (26 Jul 2026)
EP11's midroll reads: *"Quick pause before the second one. If you're getting something out of this, a like genuinely helps it find the people it's meant for, and there's a fresh one going up every day just now, weekly a bit further down the road, so subscribe and they'll come to you. Plenty of racing talk out there promising you the world. I'd sooner the careful stuff reached the folk who actually want it. Right — where were we."*
**Assessed against the standard AS IT STOOD THEN: COMPLIANT.** (EP01–EP12 are pre-pool and are NOT retro-fitted.) It follows the fixed shape, it was freshly reworded rather than reused verbatim, and **the cadence line matches the DAILY setting recorded above.** The wry nod to the noise is the standard's own item four. **The only thing to confirm is real-world: is the cadence still daily?**
