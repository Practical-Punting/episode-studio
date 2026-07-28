# THUMBNAIL HERO REGISTRY

**Started 26 July 2026, on Jodie's ruling.** Modelled on `broll-registry.md`, which exists
for the same reason: a rule nobody can check is a rule that gets broken.

---

## THE RULE (Jodie, 28 Jul 2026 — RULED, and it supersedes the choosing problem below)

> ### THE THUMBNAIL HERO IS THE PICKED COVER HERO, unless there is a specific reason not to.

It is the house style, not a fallback: matching the thumbnail to the e-book cover **ties the
video to the guide and helps downloads** (Jodie, confirmed EP06). It costs nothing, and the
image has already passed a human eye at the cover-pick gate. Crop to 16:9 at about
`center 60%` and expect to tune it per image. Full rule: `PP-STANDARDS.md` §Thumbnail.

**The older rule below still stands and is now satisfied automatically:**

**Every episode's thumbnail hero must be an image that has NEVER been a thumbnail before.**
*(A picked cover hero is new every episode, so this can no longer be breached by accident —
see §CLOSED further down for why that mattered.)*

- **No reuse at all** — not the same image, and **not a different composition of the same
  subject**. This is deliberately stricter than the b-roll no-repeat law, which allows a
  similar subject shot differently.
- **Why it is stricter:** b-roll flashes past inside an episode. A thumbnail *is* the episode
  in the feed. Two thumbnails that look alike make two different videos look like the same
  video — a viewer scrolls past the second one thinking they have already watched it. That
  costs a view in a way a repeated five-second clip never does.

**Before choosing a hero:** read this file, check `assets/thumbnail-heroes/` for spares, and
only then consider generating a new one. **After the thumbnail is built:** add a row below.

---

**See them, don't just read them:** `docs/thumbnail-hero-survey.png` is a labelled contact
sheet of every hero below — all ten used, both spares, and EP11's two cover heroes — so the
next person can eyeball the whole history in one image before choosing. Regenerate it when
you add a row.

## USED — do not reuse, and do not re-shoot the same subject

| Ep | Subject / composition | Notes |
|---|---|---|
| EP01 | Full field head-on, charging at camera, stormy sky, turf | Also reused as EP08's e-book COVER hero (Jodie's call, 25 Jul 2026 — EP01 was an unpublished test, never posted) |
| EP02 | Three horses driving toward camera past a curved grandstand, strong golden backlight | |
| EP03 | Single leader head-on, dust kicking, low golden light | |
| EP04 | Field strung along the white running rail, one runner clear on the right | |
| EP05 | Single horse head-on, bright blue sky, clean daylight | |
| EP06 | **Presenter at a studio desk**, racecourse through the window | Predates the racing-photo rule (locked 23 Jul 2026). Not a racing photo — do not repeat this style |
| EP07 | Raceday crowd on the lawn in front of a grandstand, no horse in focus | The only crowd-led hero so far |
| EP08 | Full field head-on, tightly bunched, stormy sky | Close to EP01 — logged so the echo is visible, not repeated again |
| EP09 | Single horse rounding a bend past a white rail, golden light | |
| EP10 | Single horse in profile against a dark stormy sky | |
| EP11 | Three horses on a bend, dark grandstand roofline framing the top-left | `three-horses-bend-grandstand` — a **library spare**, not a cover hero. **See the flag below** |
| EP12 | Single chestnut in yellow-and-blue silks clear of the field, coming toward camera on lush turf, crowd along the white rail on the right, soft backlit sky | Its **unused cover hero (`hero-b.png`)**. Row filled in 28 Jul 2026 from the shipped image — it had been missing since EP12 built |
| EP13 | **The PICKED cover hero A** — head-on group at full stride, lead horse centre-left | ✅ **First episode under the new rule.** Its unused hero B was REJECTED as racing-impossible (below), which is exactly why the rule names the PICKED hero and not "the other one". ⚠️ Hero A is a TIGHT head-on with the lead horse centre-left and the thumbnail text sits LEFT, so **expect the crop to need tuning** — the placement flag surfaces the rendered PNG for Jodie to judge |

### 🔴 EP13's UNUSED COVER HERO IS REJECTED — racing-impossible (Jodie, 28 July 2026)

`PP-EP13/ebook/cover-src/hero-b.png` shows **horses running on BOTH SIDES of the running
rail**. Impossible: the rail divides the track and runners are only ever on one side of it.
**Rejected on sight, for every use — not just for the cover it lost.**

**Looked at and confirmed, 28 Jul 2026, so the record is a description and not a repeat of
someone's word for it:** the near rail runs as a hard diagonal from lower-left to upper-right
straight through the middle of the frame; **three runners (orange, green and pale-green silks)
are on the FAR side of it** while the other twelve are on the near side, so the rail passes
*between* members of the same field. A second rail line runs along the top right, and the near
rail's supports splay outward at the bottom left in a way no running rail does. **It is a
beautiful photograph of something that has never happened.**
A `REJECTED-hero-b.md` note sits beside the file so the next session cannot mistake it for a
free image. Rule now in `PP-STANDARDS.md` §B-roll HARD-FAIL list and in `broll-registry.md`.

**⚠️ THE PRECEDENT THAT MADE THIS DANGEROUS.** The unused cover hero is *sometimes* copied to
`thumbnail/hero.png` — **EP12 did exactly that.** EP11 did not; it used a library spare. So
"the unused hero becomes the thumbnail" is **one precedent out of two, not a standing habit**
— but it is enough of a habit that, left alone, a rejected image would have walked onto the
most visible asset of the episode with nobody deciding to put it there.

**AND THE DOCUMENTED STYLE IS NEITHER OF THOSE.** The `thumbnail-style` note Jodie confirmed
on EP06 says: *"Hero = a racing action photo, ideally the SAME hero as the e-book cover
(`PP-EPnn/ebook/cover-src/hero.png`)"*, because matching the thumbnail to the e-book cover
**ties the video and the guide together and helps downloads.** Reusing the PICKED hero is
therefore not a fallback — it is the house style, it costs nothing, and it does not breach the
never-been-a-thumbnail rule below, because a cover hero has never been a thumbnail.

## SPARES — `PP Videos/assets/thumbnail-heroes/`

| File | Subject | Status |
|---|---|---|
| `three-horses-bend-grandstand.png` | Three horses on a bend, grandstand roof across the top-left | **USED — EP11** |
| `lone-leader-stormy-sky-left.png` | Single leader head-on, field strung behind, dark treeline left | FREE — but echoes EP03 and EP01/EP08 at subject level |

---

## ✅ CLOSED — RULED BY JODIE, 28 JULY 2026. The rule below is SUPERSEDED.

> ### THE THUMBNAIL HERO IS THE PICKED COVER HERO, unless there is a specific reason not to.

**This dissolves the open issue rather than answering it.** The question below was *"which
already-used-looking image do we settle for?"* — and it had no good answer, which is why it sat
unruled through EP12. Under the new rule **the hero is new every episode by construction**: the
picked cover hero has never been a thumbnail, so *"must never have been a thumbnail before"* is
satisfied automatically and the search for a non-echoing spare stops being a job at all.

**Why it is the right answer and not just a convenient one** — the `thumbnail-style` note Jodie
confirmed at EP06 already said the hero should ideally be the SAME hero as the e-book cover,
**because matching the two ties the video to the guide and helps e-book downloads.** That is
the point of the free e-book. So this is the house style being written down, not a new
compromise. It also costs nothing and the image has already passed a human eye at the
cover-pick gate.

**"A specific reason not to"** must be a real one, named in the episode's row: the picked hero
crops badly to 16:9, the episode wants deliberate variation, or the picked hero is unusable.
Full rule in `docs/PP-STANDARDS.md` §Thumbnail.

**The three-times-dangling lesson, recorded because it is the actual failure here:** this
question was raised at EP11, marked *"Needs Jodie's ruling before EP12"*, **and EP12 shipped
without it.** An open question in a standards file is not a placeholder — it is a decision that
gets made by default, by whoever is building at the time, without anyone noticing they made it.
**Ask for the ruling, or say plainly that the default is now the rule.**

<details>
<summary>The superseded open issue, kept for the reasoning (click to read)</summary>

## ⚠️ OPEN ISSUE, RAISED AT EP11 (26 Jul 2026) — the rule may not be sustainable as written

EP11 was the first episode to apply this rule, and **nothing available passed it cleanly.**
Under the strict reading (no repeat of subject, even differently composed), both spares are
already echoes: `three-horses-bend-grandstand` echoes EP02 (three horses, grandstand) and
`lone-leader-stormy-sky-left` echoes EP03 (single leader head-on). EP11's own cover heroes
echo EP01/EP08 (field head-on) and EP05/EP10 (single horse).

`three-horses-bend-grandstand` was chosen as **the least-echoing option available at zero
spend** — a wider bend shot with architectural framing, against EP02's tight low three-abreast
in golden backlight. **This is flagged, not hidden.**

**The underlying problem is the one Jodie already identified for b-roll:** across fifty racing
episodes you run out of *subjects* long before you run out of *compositions*. There are only
so many things that happen at a racecourse. The b-roll rule was resolved by allowing a
different composition of a similar subject; the thumbnail rule deliberately closes that door.
Both positions are defensible, but with ten episodes logged the subject space is already thin.

**Needs Jodie's ruling before EP12.** Options, roughly:
1. Keep it strict and **commit to generating a genuinely new hero per episode** (a real, small,
   recurring cost — and eventually the same wall).
2. Soften to the b-roll standard: **different composition of a similar subject is acceptable**,
   the same image never is. Keeps the "two videos don't look alike" protection, which is what
   the rule is actually for.
3. Keep it strict but widen the subject net deliberately — crowd, mounting yard, silks,
   weigh-in, hooves, dusk, rain, night meeting — so each episode claims a genuinely new corner
   of raceday rather than another shot of horses running.

My read: **option 2 or 3.** Option 2 protects what the rule is for while staying achievable;
option 3 keeps the strictness and buys a lot of runway, at the cost of some heroes being less
dramatic than a field at full stride.

</details>

---

**HOW EP13 WAS RESOLVED (28 Jul 2026):** option 1 of the four put to Jodie — reuse the PICKED
hero A as the thumbnail hero, **0 credits**. The unused hero B was racing-impossible and
rejected. Options 2 (the last free spare, an acknowledged echo) and 3 (generate a fresh hero,
2.0 credits, balance 188.22) were declined as unnecessary once the house style was recognised.
