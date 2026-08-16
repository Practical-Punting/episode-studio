/* C2, THE LAST OF IT — a FINISHED episode must not describe itself as an unfinished one.
 *
 *   node test_board_finished_line.mjs
 *
 * THIRD SIGHTING IN ONE DAY, and each cost somebody a wrong belief:
 *   1. `progress_step` said "Paused — needs a look" while the engine was rolling.
 *   2. Hugh's Save and Mark-as-published looked hung when every write had landed.
 *   3. EP28 sat with ALL FOUR approvals TRUE, at status `ready`, with the rail
 *      still advertising "Waiting on you — four approvals". Whoever opened it went
 *      looking for four ticks that were already ticked.
 *
 * E23c ruled on this class in three words — DERIVE IT, NEVER STORE IT — and the
 * board obeys it for the working statuses. The FINISHED ones were never covered:
 * `stageLine` returns early only for `published`, so a `ready` episode falls
 * through to whatever step was last in flight and can announce "Saving the
 * YouTube copy" about an episode that is finished and waiting to be published.
 *
 * 🔒 AND THE STORED COLUMN IS CLEARED AT THE MOMENT IT EXPIRES. The board is what
 * moves an episode to `ready` (nothing in the engine ever sets it), so the board is
 * where "waiting on four approvals" stops being true — the same place, and the same
 * rule, as the flag fix this morning: a sentence that is never left behind cannot go
 * stale. The rail column and the engine's own `status` output both read it.
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("./app.js", import.meta.url), "utf8");
const house = JSON.parse(readFileSync(new URL("./docs/house-form.json", import.meta.url), "utf8"));
const el = new Proxy({}, {
  get: (_t, k) => (k === "classList" || k === "style" ? el : () => {}), set: () => true });
const sandbox = {
  supabase: { createClient: () => new Proxy({}, {
    get: () => new Proxy(() => undefined, {
      get: () => () => undefined, apply: () => undefined }) }) },
  document: { getElementById: () => el, querySelector: () => el,
              querySelectorAll: () => [], addEventListener: () => {}, body: el },
  window: { addEventListener: () => {}, location: { hash: "", href: "" } },
  location: { hash: "", href: "" },
  navigator: { clipboard: { writeText: async () => {} } },
  fetch: async () => ({ ok: true, json: async () => house }),
  setTimeout: () => 0, setInterval: () => 0, clearInterval: () => {}, console,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "app.js" });

let pass = 0; const fails = [];
function check(n, fn) {
  try { fn(); pass++; console.log("  ok  " + n); }
  catch (e) { fails.push([n, e.message]); console.log("  !!  " + n + "\n      " + e.message); }
}
function assert(c, m) { if (!c) throw new Error(m); }

const now = new Date().toISOString();
/* EP28 as it actually sat on the rail at 18:45 on 16 Aug 2026: every approval in,
 * status `ready`, and the stored line still asking for the approvals it already has. */
const EP28 = {
  id: "ep-28", ep_number: 28, status: "ready",
  video_approved: true, ebook_approved: true,
  thumbnail_approved: true, title_approved: true,
  progress_step: "Waiting on you — four approvals",
  progress_pct: 92, needs_look: false, heartbeat_at: now,
  build_state: { current: { step: "youtube_copy", started_at: now, budget_s: 300 } },
};

console.log("\n--- a FINISHED episode says what it is waiting for, not what it was ---");

check("🔴 a `ready` episode does NOT advertise the approvals it already has", () => {
  const line = sandbox.stageLine(EP28);
  assert(!/four approvals/i.test(line),
    "the board says " + JSON.stringify(line) + " about an episode whose four " +
    "approvals are all TRUE — whoever opens it goes looking for ticks that are " +
    "already ticked");
});

check("  and it does not announce the last step it happened to run", () => {
  const line = sandbox.stageLine(EP28);
  assert(!/youtube|saving|copy/i.test(line),
    "it says " + JSON.stringify(line) + " — that step finished; the episode is " +
    "waiting on a person now");
});

check("  it says it is waiting to be PUBLISHED", () => {
  const line = sandbox.stageLine(EP28);
  assert(/publish/i.test(line),
    "it says " + JSON.stringify(line) + ", which does not tell the operator the " +
    "one thing left to do");
});

check("a `published` episode still reads Published", () => {
  const line = sandbox.stageLine({ ...EP28, status: "published", heartbeat_at: now });
  assert(line === "Published", JSON.stringify(line));
});

check("🔴 the STORED sentence cannot change what a finished card says", () => {
  const lying = { ...EP28, progress_step: "Assembling — cards + audio (pass B)" };
  const line = sandbox.stageLine(lying);
  assert(!/assembl/i.test(line) && /publish/i.test(line),
    "the stored column reached the card: " + JSON.stringify(line) + ". It is " +
    "derived or it is not — a line that CAN be poisoned by a stale field will be");
});

console.log("\n--- and nothing that still needs a person is quietened ---");

check("an episode genuinely awaiting approval still asks for it", () => {
  const line = sandbox.stageLine({
    ...EP28, status: "awaiting_approval",
    video_approved: true, ebook_approved: false,
    thumbnail_approved: false, title_approved: false,
    build_state: { current: null },
  });
  assert(/approv/i.test(line), JSON.stringify(line) + " — this one DOES want her");
});

check("a raised flag still outranks everything", () => {
  const line = sandbox.stageLine({ ...EP28, needs_look: true });
  assert(/needs a look/i.test(line), JSON.stringify(line));
});

check("a dead engine still outranks the status", () => {
  const dead = { ...EP28, status: "assembling",
                 heartbeat_at: new Date(Date.now() - 3 * 3600e3).toISOString() };
  const line = sandbox.stageLine(dead);
  assert(/engine stopped/i.test(line), JSON.stringify(line));
});

check("a working episode is untouched by any of this", () => {
  const line = sandbox.stageLine({
    id: "x", status: "building", needs_look: false, heartbeat_at: now,
    progress_step: "anything at all",
    build_state: { current: { step: "cards_render", started_at: now, budget_s: 3600 } },
  });
  assert(/motion cards/i.test(line), JSON.stringify(line));
});

console.log("\n--- the stored column is CLEARED where it stops being true ---");
// The board is the only thing that ever sets `ready` (nothing in the engine does),
// so this is the one place "waiting on four approvals" expires. Asserted on the
// source because the click path needs a live DOM; the behavioural half is the
// stageLine cases above, which hold whatever the column says.
check("🔴 closing the fourth approval clears the line it makes untrue", () => {
  const approve = src.slice(src.indexOf('if (act === "approve")'),
                            src.indexOf('if (act === "unapprove")'));
  assert(/patch\.status = "ready"/.test(approve), "the approve handler moved");
  assert(/progress_step/.test(approve),
    "the fourth approval advances the episode to `ready` and leaves the stored " +
    "line saying it is still waiting for approvals — which is exactly what EP28 " +
    "showed. Clear it in the same write that advances the status");
});

console.log("\nfinished line: " + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
