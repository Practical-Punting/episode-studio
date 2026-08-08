/* SITTING 3 — the board must stop lying the instant the rail changes.
 *
 * Two faults, one shape: the rail is written, the SCREEN is not, and renderBoard()
 * returns early while any field is dirty (the C1 pause that protects her typing). So
 * on the one card she has been editing, no re-render is coming and Refresh does not
 * rescue it — loadAll() calls renderBoard() unforced and bails on the same line.
 *
 *   (a) tick "I've read the script"  -> "Save & approve" must enable, no reload
 *   (b) click "It's sorted"          -> the ⚠ Needs a look card must go, no reload
 *
 * FAIL-FIRST: each case first runs against a stubbed rail write that FAILS, and
 * asserts the screen does NOT change — because a board that updates itself whether or
 * not the write landed is worse than one that waits. Then the write succeeds and the
 * screen must change.
 *
 *   node test_board_gates_live.mjs
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

/* APP_JS lets this suite be pointed at an OLDER app.js, so the fail-first half can be
 * re-run on demand instead of taken on trust:
 *   git show HEAD~1:app.js > old.js   &&   APP_JS=old.js node test_board_gates_live.mjs
 * The two "must change" assertions then fail, which is the proof that they are
 * measuring the fix and not the weather. */
const src = readFileSync(process.env.APP_JS || new URL("./app.js", import.meta.url), "utf8");

let clickHandler = null;
const generic = new Proxy({}, {
  get: (_t, k) => (k === "classList" || k === "style" ? generic : () => {}),
  set: () => true,
});

/* querySelector answers are set per-case, so the assertions are about the real
 * selectors app.js builds — not about a proxy that says yes to everything. */
let QS = {};

const lanes = {
  addEventListener: (type, fn) => { if (type === "click") clickHandler = fn; },
};

const sandbox = {
  supabase: { createClient: () => new Proxy({}, {
    get: () => new Proxy(() => undefined, {
      get: () => () => undefined, apply: () => undefined }) }) },
  document: {
    getElementById: (id) => (id === "lanes" ? lanes : generic),
    querySelector: (sel) => (sel in QS ? QS[sel] : null),
    querySelectorAll: () => [],
    addEventListener: () => {}, body: generic,
  },
  window: { addEventListener: () => {}, location: { hash: "", href: "" } },
  location: { hash: "", href: "" },
  CSS: { escape: (s) => s },
  setTimeout: (f) => { if (typeof f === "function") f(); return 0; },
  setInterval: () => 0, clearInterval: () => {},
  console,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "app.js" });

let pass = 0; const fails = [];
function check(name, cond, why = "") {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fails.push(name); console.log("  FAIL " + name + (why ? "  <- " + why : "")); }
}

/* one episode on the board */
vm.runInContext('EPISODES = [{ id: "ep-18", ep_number: 18 }];', sandbox);
sandbox.toast = () => {};

/* a button that behaves like a real one for the two things the handler asks of it */
function makeBtn(act, extra = {}) {
  const b = {
    checked: true, disabled: false,
    getAttribute: (k) => (k === "data-act" ? act : k === "data-ep" ? "ep-18" : null),
    closest: (sel) => (sel === "[data-act]" ? b : (extra.closest ? extra.closest(sel) : null)),
    ...extra,
  };
  return b;
}

async function fire(btn) { await clickHandler({ target: btn }); }

console.log("\n=== (a) ticking 'I've read the script' enables Save & approve ===\n");

const APPROVE_SEL = '[data-act="approve-words"][data-ep="ep-18"]';
const HINT_SEL = '[data-tickhint="ep-18"]';

/* FAIL FIRST: the rail write fails -> the screen must NOT move */
sandbox.writeEpisode = async () => false;
let approve = { disabled: true }, hint = { hidden: false };
QS = { [APPROVE_SEL]: approve, [HINT_SEL]: hint };
await fire(makeBtn("script-read"));
check("write fails -> the button stays DISABLED", approve.disabled === true,
      "the board must not promise what the rail did not accept");
check("write fails -> the hint stays visible", hint.hidden === false);

/* now the write lands */
sandbox.writeEpisode = async () => true;
approve = { disabled: true }; hint = { hidden: false };
QS = { [APPROVE_SEL]: approve, [HINT_SEL]: hint };
await fire(makeBtn("script-read"));
check("tick -> Save & approve ENABLES, with no re-render", approve.disabled === false);
check("tick -> the 'tick this first' hint is hidden", hint.hidden === true);

/* and un-ticking must put it back */
approve = { disabled: false }; hint = { hidden: true };
QS = { [APPROVE_SEL]: approve, [HINT_SEL]: hint };
await fire(makeBtn("script-read", { checked: false }));
check("un-tick -> the button DISABLES again", approve.disabled === true,
      "the gate has to close as readily as it opens");
check("un-tick -> the hint comes back", hint.hidden === false);

console.log("\n=== (b) clearing a gate drops the card immediately ===\n");

function needlookBtn() {
  const block = { removed: false, remove() { this.removed = true; } };
  const b = makeBtn("clear-look", {
    closest: (sel) => (sel === ".needlook" ? block : null),
  });
  b.closest = (sel) => (sel === "[data-act]" ? b : sel === ".needlook" ? block : null);
  b.block = block;
  return b;
}

/* FAIL FIRST: the write fails -> the card must STAY */
sandbox.writeEpisode = async () => false;
let b1 = needlookBtn();
await fire(b1);
check("write fails -> the ⚠ card STAYS on screen", b1.block.removed === false,
      "clearing the screen on a failed write hides a flag that is still set");

/* now the write lands */
sandbox.writeEpisode = async () => true;
const b2 = needlookBtn();
await fire(b2);
check("cleared -> the ⚠ card is removed at once", b2.block.removed === true,
      "asked twice is worse than asked late — she clicks again on a live flag");

/* it must not fall over when the markup has no wrapper */
sandbox.writeEpisode = async () => true;
const b3 = makeBtn("clear-look", { closest: () => null });
b3.closest = (sel) => (sel === "[data-act]" ? b3 : null);
let threw = null;
try { await fire(b3); } catch (e) { threw = e; }
check("no .needlook wrapper -> it does not throw", threw === null, String(threw));

console.log("\n=== (c) the render card carries the captions-OFF instruction ===\n");

/* This is the one instruction carried out inside somebody else's product, and the only
 * irreversible one on the card: HeyGen BURNS captions into the picture. The guide has
 * said "Confirm Captions OFF" for weeks; the card she is looking at while she is in
 * HeyGen did not. Assert the RENDERED CARD, not the source — a grep would pass on a
 * comment that merely mentions captions (CLAUDE.md 1a). */
const gate = vm.runInContext(
  'gateRender({ id: "ep-18", ep_number: 18, heygen_name: "PP-EP18", status: "building" })',
  sandbox);
check("the render card mentions captions at all", /caption/i.test(gate),
      gate.slice(0, 160));
check("  and says to turn them OFF", /captions?\s*OFF/i.test(gate));
check("  and says why it cannot be undone",
      /burn/i.test(gate) && /cannot be taken out|cannot be removed/i.test(gate),
      "a step with no reason is a step somebody helpfully skips");
check("  and it is not styled as just another grey hint",
      /class="g-warn"/.test(gate), "it needs to read louder than g-hint");
check("  the copy buttons are still there",
      /data-act="copy-heygen"/.test(gate) && /data-act="copy-script"/.test(gate),
      "the EP17 fault — the card that asks for the one thing it does not give");

console.log(`\n${pass} passed, ${fails.length} failed`);
for (const f of fails) console.log("  FAILED: " + f);
process.exit(fails.length ? 1 : 0);
