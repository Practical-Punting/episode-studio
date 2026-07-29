/* Prove the BOARD stops lying when the engine dies.
 *
 * B1: a checker is proved by the bad build it refused. So this asserts the ARTEFACT —
 * app.js's own functions, loaded from the real file — against a fabricated row whose
 * heartbeat_at is eleven hours old, which is exactly what the board was rendering as
 * "Working for 1 d 1 hr · render cooking 1 d 1 hr" on the morning of 29 Jul.
 *
 * It touches no network and no live row.
 *   node test_board_stale.mjs
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("./app.js", import.meta.url), "utf8");

/* app.js is a browser script: it makes a Supabase client and touches the DOM at
 * load. Give it just enough of a world to define its functions in. Nothing is
 * stubbed that the functions under test actually use — they are pure. */
const el = new Proxy({}, {                       // any element, any property, no-ops
  get: (_t, k) => (k === "classList" ? el : k === "style" ? el : () => {}),
  set: () => true,
});
const sandbox = {
  supabase: { createClient: () => new Proxy({}, {   // a client that tolerates anything
    get: () => new Proxy(() => undefined, {
      get: () => () => undefined, apply: () => undefined }) }) },
  document: { getElementById: () => el, querySelector: () => el,
              querySelectorAll: () => [], addEventListener: () => {}, body: el },
  window: { addEventListener: () => {}, location: { hash: "", href: "" } },
  location: { hash: "", href: "" },
  setTimeout: () => 0, setInterval: () => 0, clearInterval: () => {},
  console,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "app.js" });

let pass = 0;
const fails = [];
function check(name, fn) {
  try { fn(); pass++; console.log("  ok  " + name); }
  catch (e) { fails.push([name, e.message]); console.log("  !!  " + name + "\n      " + e.message); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

const HOURS = 3600 * 1000;
/* The real thing: EP13's row as the board saw it at 08:56 on 29 Jul. */
const dead = {
  ep_number: 13, title: "The Ratings Game — Part 1", status: "assembling",
  started_at: new Date(Date.now() - 25 * HOURS).toISOString(),
  render_started_at: new Date(Date.now() - 25 * HOURS).toISOString(),
  heartbeat_at: new Date(Date.now() - 11 * HOURS).toISOString(),
  progress_pct: 78, needs_look: false,
};
const alive = { ...dead, heartbeat_at: new Date(Date.now() - 20 * 1000).toISOString() };

check("a stale heartbeat is detected as ENGINE STOPPED", () => {
  assert(sandbox.engineStopped(dead), "engineStopped() returned nothing for an 11-hour-old beat");
  assert(!sandbox.engineStopped(alive), "a 20-second-old beat must NOT read as stopped");
});

check("the CHIP says ENGINE STOPPED, not 'Assembling…'", () => {
  const html = sandbox.cardFor(dead);
  assert(html.includes("ENGINE STOPPED"), "the card never says ENGINE STOPPED");
  assert(!/>\s*Assembling…\s*</.test(html),
    "the chip still shows the status label — it claims the machine is working");
});

check("the elapsed line NEVER says 'Working' or 'render cooking' when stopped", () => {
  const line = sandbox.elapsedLine(dead);
  assert(!line.includes("Working"), "still says 'Working': " + line);
  assert(!line.includes("cooking"),
    "still says 'render cooking' — describing something actively happening: " + line);
  assert(line.includes("ENGINE STOPPED"), "does not say ENGINE STOPPED: " + line);
});

check("a LIVE engine still reads as working (the check is not a blanket alarm)", () => {
  const line = sandbox.elapsedLine(alive);
  assert(line.includes("Working"), "a live engine should read as working: " + line);
  assert(!line.includes("ENGINE STOPPED"), "a live engine was called stopped: " + line);
  assert(!sandbox.cardFor(alive).includes("ENGINE STOPPED"), "live card says stopped");
});

check("it gets the red treatment AND says what fixes it", () => {
  const nl = sandbox.needsLook(dead);
  assert(nl, "needsLook() returned nothing");
  assert(nl.flagged === true,
    "flagged:false — it renders as a grey aside, not the red card. The age of the " +
    "heartbeat in small grey type is not a warning.");
  assert(/engine\.py run --watch/.test(nl.msg), "does not say what fixes it: " + nl.msg);
  assert(/nothing is lost|safe/i.test(nl.msg),
    "does not reassure that the episode is safe: " + nl.msg);
});

check("3 minutes is the line, not 5", () => {
  const justUnder = { ...dead, heartbeat_at: new Date(Date.now() - 2.5 * 60000).toISOString() };
  const justOver = { ...dead, heartbeat_at: new Date(Date.now() - 3.5 * 60000).toISOString() };
  assert(!sandbox.engineStopped(justUnder), "2.5 min was called stopped");
  assert(sandbox.engineStopped(justOver), "3.5 min was NOT called stopped");
});

check("a NON-working status is never called stopped (a parked episode is not dead)", () => {
  const parked = { ...dead, status: "awaiting_approval" };
  assert(!sandbox.engineStopped(parked),
    "an episode waiting on a human was reported as a stopped engine");
});

console.log(`\nboard stale-heartbeat rendering: ${pass} passed, ${fails.length} failed`);
process.exit(fails.length ? 1 : 0);
