/* D13, board side — a STUCK step and a step WAITING ON JODIE must not look the same.
 *
 * Today they do: both show a progress bar, a stage line and a healthy heartbeat.
 * EP14 sat on assemble_passB for three and a half days looking exactly like an
 * episode that was working.
 *
 * Drives app.js's real functions. Reads no source.
 *   node test_board_watchdog.mjs
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("./app.js", import.meta.url), "utf8");
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

const MIN = 60 * 1000, HOUR = 60 * MIN;
const agoIso = (ms) => new Date(Date.now() - ms).toISOString();

const base = {
  id: "z", ep_number: 15, title: "Something — Part 1", status: "assembling",
  progress_pct: 48, needs_look: false, heartbeat_at: agoIso(6 * 1000),
  progress_step: "Assembling — cards + audio (pass B)", build_state: {},
};

/* EP14's actual shape: 3.5 days on one step, heartbeat 6 seconds old. */
const stuck = { ...base, build_state: {
  current: { step: "assemble_passB", started_at: agoIso(84 * HOUR), budget_s: 45 * 60 } } };

/* A legitimate wait: the flag is up and Jodie has not got to it yet. */
const waiting = { ...base, needs_look: true,
  needs_look_message: "Have a look at the title card.",
  build_state: { current: { step: "cards_render", started_at: agoIso(50 * HOUR),
                            budget_s: 30 * 60 } } };

/* Waiting on a human BY DESIGN, no flag: the HeyGen render. */
const rendering = { ...base, status: "rendering", progress_step: "Rendering with HeyGen",
  build_state: { current: { step: "heygen_download", started_at: agoIso(20 * HOUR),
                            budget_s: null } } };

const working = { ...base, build_state: {
  current: { step: "assemble_passB", started_at: agoIso(4 * MIN), budget_s: 45 * 60 } } };

check("a STUCK step is reported as stuck", () => {
  const s = sandbox.stepState(stuck);
  assert(s && s.state === "stuck",
    "three and a half days on one step, no flag, reads as '" +
    (s && s.state) + "'. That is EP14 exactly, and nothing said so.");
});

check("a stuck step says HOW LONG and WHICH step", () => {
  const h = sandbox.cardFor(stuck);
  assert(/assemble_passB/.test(h), "does not name the step that is stuck");
  assert(/3 d|84 hr|3 days/.test(h), "does not say how long it has been stuck: " +
    (h.match(/.{0,60}stuck.{0,80}/i) || [""])[0]);
});

check("a stuck step says NOBODY IS COMING — it is not waiting on anyone", () => {
  const h = sandbox.cardFor(stuck);
  assert(/nobody|no one|not waiting/i.test(h),
    "does not distinguish itself from a legitimate wait, which is the whole point");
});

check("a flagged episode is WAITING, never stuck, however long it waits", () => {
  const s = sandbox.stepState(waiting);
  assert(s && s.state === "waiting",
    "fifty hours on a raised flag reads as '" + (s && s.state) +
    "'. A legitimate wait for Jodie must NEVER raise an alarm.");
});

check("a step that waits on a human BY DESIGN never alarms", () => {
  const s = sandbox.stepState(rendering);
  assert(s && s.state === "waiting",
    "twenty hours waiting for the HeyGen render reads as '" + (s && s.state) +
    "'. That step has no flag and no budget on purpose — Jodie may not run the " +
    "render until tomorrow.");
});

check("a step inside its budget is just working", () => {
  const s = sandbox.stepState(working);
  assert(s && s.state === "working", "four minutes into a 45-minute step is not a fault");
  const h = sandbox.cardFor(working);
  assert(!/stuck/i.test(h), "cried wolf on a healthy step");
});

check("STUCK and WAITING do not render the same", () => {
  const a = sandbox.cardFor(stuck), b = sandbox.cardFor(waiting);
  assert(a !== b, "the two cards are identical markup — the fault is unchanged");
  assert(/stuck/i.test(a), "the stuck card never says stuck");
  assert(!/stuck/i.test(b), "the WAITING card claims to be stuck");
});

check("an episode with no in-flight step is not judged", () => {
  assert(sandbox.stepState({ ...base, build_state: {} }) === null,
    "invented a verdict for an episode with nothing in flight");
  assert(sandbox.stepState({ ...base, status: "published",
    build_state: { current: { step: "x", started_at: agoIso(99 * HOUR), budget_s: 60 } } })
    .state !== "stuck", "called a finished episode stuck");
});

console.log("\nwatchdog (board): " + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
