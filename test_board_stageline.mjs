/* C2 — THE STALE STATUS LINE. Eleven sightings. Derive it; never store it.
 *
 * `progress_step` is STORED when a flag is raised and never rewritten. Right now
 * EP08-EP12 are all PUBLISHED and all still say "Waiting on you — four approvals".
 * It misled twice on 3 Aug: EP13 read "Waiting on Hugh's Mailchimp e-book link" as it
 * went live, EP14 read "Waiting on you — four approvals" after all four were in.
 *
 * Reads no source. Drives app.js's real functions.
 *   node test_board_stageline.mjs
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

const STALE = "Waiting on you — four approvals";
const beat = new Date().toISOString();

/* EP08-EP12 as they ACTUALLY sit on the rail today. */
const published = { id: "p", ep_number: 12, status: "published",
                    progress_step: STALE, needs_look: false, heartbeat_at: beat,
                    build_state: {} };

check("a PUBLISHED episode never says it is waiting on you", () => {
  const line = sandbox.stageLine(published);
  assert(!/waiting on you/i.test(line),
    "EP08-EP12 are published and every one still reads “" + STALE + "”. The stored " +
    "value was written when a flag was raised and never rewritten. got: " + line);
  assert(/publish/i.test(line), "a published episode should say so. got: " + line);
});

check("the stored value is not read at all", () => {
  const a = sandbox.stageLine(published);
  const b = sandbox.stageLine({ ...published, progress_step: "COMPLETE NONSENSE" });
  assert(a === b,
    "the line changed when the STORED text changed, so it is still being read. " +
    "Derive it from status, needs_look and the step in flight — never from a value " +
    "written once and left behind.");
});

check("a flagged episode says it needs a look", () => {
  const line = sandbox.stageLine({ ...published, status: "assembling",
    needs_look: true, progress_step: STALE });
  assert(/look/i.test(line), "a raised flag is not reflected: " + line);
});

check("a step in flight names what is happening NOW", () => {
  const line = sandbox.stageLine({ ...published, status: "assembling",
    progress_step: STALE,
    build_state: { current: { step: "assemble_passB",
                              started_at: new Date(Date.now() - 60000).toISOString(),
                              budget_s: 2700 } } });
  assert(/pass B|assembl/i.test(line), "does not say what is running: " + line);
  assert(!/waiting on you/i.test(line), "still leaking the stale text: " + line);
});

check("a stuck step says stuck on the stage line too", () => {
  const line = sandbox.stageLine({ ...published, status: "assembling",
    build_state: { current: { step: "assemble_passB",
                              started_at: new Date(Date.now() - 84 * 3600e3).toISOString(),
                              budget_s: 2700 } } });
  assert(/stuck/i.test(line), "three and a half days on one step reads as: " + line);
});

check("an episode with nothing in flight falls back to its status label", () => {
  const line = sandbox.stageLine({ ...published, status: "queued",
    progress_step: STALE, build_state: {} });
  assert(!/waiting on you/i.test(line), "leaked the stale text: " + line);
  assert(line.length > 0, "produced nothing at all");
});

check("the CARD renders the derived line, not the stored one", () => {
  const h = sandbox.cardFor(published);
  assert(!h.includes(STALE),
    "the card still prints the stored text somewhere — the fix has not reached what " +
    "a human actually sees");
});

console.log("\nstage line: " + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
