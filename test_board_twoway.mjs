/* TWO-WAYS ON THE BOARD (migration 009, 13 Nov 2026).
 *
 * A two-way row is driven by Claude Code's runner, not the engine. The board must:
 *  · put it in a lane from its `twoway` record (gate → Your turn; pasted → Waiting;
 *    working → Engine working; published → Done);
 *  · name the stage and WHICH of Jodie's gates is waiting, in words;
 *  · NEVER offer a button that ticks a gate (no data-act on a two-way card);
 *  · never show the single-presenter words panel or the "engine stopped" alarm.
 * CONTROLS: the same stale-heartbeat row as a SINGLE goes "engine stopped"; the same
 * queued, wordless row as a SINGLE asks for the hook and byline.
 *
 * Reads no source. Drives app.js's real functions.
 *   node test_board_twoway.mjs
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
const run = (code) => vm.runInContext(code, sandbox);

let pass = 0; const fails = [];
function check(n, fn) {
  try { fn(); pass++; console.log("  ok  " + n); }
  catch (e) { fails.push([n, e.message]); console.log("  !!  " + n + "\n      " + e.message); }
}
function assert(c, m) { if (!c) throw new Error(m); }

const old = new Date(Date.now() - 60 * 60 * 1000).toISOString();
const base = { id: "x", ep_number: 57, title: "Staking the Heart of the Game Part 4",
               created_at: old, updated_at: old, heartbeat_at: old };
const tw = (status, twoway) => Object.assign({}, base, { status, format: "two-way", twoway });
const rows = {
  pasted:  tw("queued", { stage: 1, step: "pasted", gate: null, readers: { BB: "Gordon", BM: "Steve" } }),
  words:   tw("building", { stage: 1, step: "waiting for the new words", gate: "words",
                            gate_since: old, readers: { BB: "Gordon", BM: "Steve" } }),
  working: tw("building", { stage: 2, step: "planning the cut", gate: null }),
  done:    Object.assign(tw("published", { stage: 5, step: "published", gate: null }),
                         { published_url: "https://youtu.be/ZWF8K-7EIow" }),
};
sandbox.__rows = rows;

check("lanes come from the twoway record", () => {
  const got = run("[__rows.pasted, __rows.words, __rows.working, __rows.done].map(twoWayLane)");
  assert(JSON.stringify(got) === JSON.stringify(["Waiting", "Your turn", "Engine working", "Done"]),
         JSON.stringify(got));
});
check("a waiting gate is named in words, with the stage", () => {
  const h = run("cardFor(__rows.words)");
  assert(h.includes("Your turn — approve the new words"), h.slice(0, 300));
  assert(h.includes("Stage 1 of 5"), "no stage line");
  assert(h.includes("/two-way EP57"), "does not say how to carry on");
});
check("NO two-way card offers a button (the board never ticks a gate)", () => {
  for (const k of Object.keys(rows)) {
    const h = run("cardFor(__rows." + k + ")");
    assert(!/data-act=|<button/.test(h), k + " card has a button: " + h.slice(0, 200));
  }
});
check("a pasted two-way says to start it in Claude Code — not 'Your turn — the words'", () => {
  const h = run("cardFor(__rows.pasted)");
  assert(h.includes("/two-way EP57") && !h.includes("the words</span>"), h.slice(0, 300));
  assert(run("packagingEntryPending(__rows.pasted)") === false, "packaging entry fired");
  assert(run("wordsGatePending(__rows.pasted)") === false, "words gate fired");
  assert(run("studioIsWriting(__rows.pasted)") === false, "writing chip fired");
});
check("CONTROL: the same queued, wordless row as a SINGLE asks for the hook and byline", () => {
  sandbox.__single = Object.assign({}, rows.pasted, { format: "single", twoway: null });
  assert(run("packagingEntryPending(__single)") === true,
         "the control did not reproduce — the two-way check above proves nothing");
});
check("a two-way at 'building' with an hour-old heartbeat is NOT 'engine stopped'", () => {
  assert(run("engineStopped(__rows.working)") === null, "two-way raised the dead-engine alarm");
  assert(!run("cardFor(__rows.working)").includes("ENGINE STOPPED"), "card says engine stopped");
});
check("CONTROL: the same row as a SINGLE IS 'engine stopped'", () => {
  sandbox.__single2 = Object.assign({}, rows.working, { format: "single" });
  assert(run("engineStopped(__single2)") !== null, "the control did not reproduce");
});
check("a published two-way links its YouTube video", () => {
  const h = run("cardFor(__rows.done)");
  assert(h.includes("https://youtu.be/ZWF8K-7EIow") && h.includes("Published"), h.slice(0, 300));
});

console.log(`\ntwo-way board: ${pass} passed, ${fails.length} failed`);
process.exit(fails.length ? 1 : 0);
