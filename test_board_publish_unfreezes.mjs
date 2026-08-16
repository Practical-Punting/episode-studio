/* THE BOARD FREEZES AFTER A SAVE — reported by Jodie, 16 Aug 2026, while Hugh was
 * publishing.
 *
 *   "We put in the links for the e-book and the YouTube video, we hit save and hit
 *    mark as published, and it just sits there hanging, greyed out slightly, so it's
 *    sort of not updating itself."
 *
 * THE WRITE LANDS. Checked on the real rail before writing a line of this: EP25, EP26
 * and EP27 are all `published` with both links stored. **Every click worked.** What
 * broke is the FEEDBACK, which is worse than it sounds — an operator who cannot tell a
 * save from a hang will click again, or stop trusting the board.
 *
 * THE MECHANISM, and the codebase had already written the rule down:
 *
 *     "A saved field is no longer unsaved, so it must stop pausing the board. Without
 *      this the pause would outlive the edit and the board would freeze until a reload
 *      — a guard that never lets go is its own fault."   (clearWordDrafts, app.js)
 *
 * That release exists and the WORDS gate calls it. The publish card never did. So:
 *   1. typing the two links marks `pub-ebook-<id>` / `pub-url-<id>` dirty;
 *   2. Save writes the row, then renderBoard() sees "she is editing" and RETURNS
 *      EARLY — "the node she is in is never touched" — so the card is never redrawn;
 *   3. writeEpisode() disabled the button and only re-enables it ON ERROR.
 * Greyed out, and not updating. Exactly as described.
 *
 * This drives the REAL listeners app.js registers, with a db stub that records the
 * write. It touches no network and no live row.
 *   node test_board_publish_unfreezes.mjs
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("./app.js", import.meta.url), "utf8");

const NODES = new Map();
function mkEl(tag, id, value = "") {
  const el = {
    tagName: tag.toUpperCase(), id, value, type: "url", disabled: false,
    classList: { add() {}, remove() {}, toggle() {} }, style: {}, dataset: {},
    textContent: "", scrollTop: 0, scrollHeight: 0, hidden: false,
    listeners: {},
    addEventListener(k, fn) { (this.listeners[k] ||= []).push(fn); },
    closest() { return null }, remove() {},
    getAttribute(k) { return this.attrs?.[k] ?? null },
    set innerHTML(v) { this._html = v; this.writes = (this.writes || 0) + 1; },
    get innerHTML() { return this._html || ""; },
  };
  NODES.set(id, el);
  return el;
}

const DOC = { listeners: {} };
const stub = new Proxy({}, {
  get: (_t, k) => (k === "classList" || k === "style" ? stub : () => {}),
  set: () => true,
});

const lanes = mkEl("div", "lanes");
lanes.parentNode = { insertBefore() {} };
mkEl("div", "count");
mkEl("div", "updated");
mkEl("div", "toast");

const WRITES = [];
const ROWS = [];                 // what the "server" holds; loadAll reads this
function dbStub() {
  // ⚠️ THE CHAIN IS THENABLE, and it has to be. `EPISODES` is a module-scope `let`
  // inside app.js, so a test cannot assign it from outside the VM — the only honest
  // way in is the way the app does it: loadAll() awaits this chain and sets
  // EPISODES from what it resolves to. Without `then` the await yields the chain
  // object, EPISODES stays [], every handler returns early on `if (!ep)`, and the
  // test reports a fault in the app that is really a fault in the stub.
  const chain = {
    update(patch) { chain._patch = patch; return chain; },
    eq(_k, id) { WRITES.push({ id, patch: chain._patch }); return Promise.resolve({ error: null }); },
    select() { return chain; },
    order() { return chain; },
    in() { chain._msgs = true; return chain; },        // messages: .in().order()
    insert() { return Promise.resolve({ error: null }); },
    then(res) {
      const msgs = chain._msgs;
      chain._msgs = false;
      res({ data: msgs ? [] : ROWS.slice(), error: null });
    },
  };
  return { from: () => chain,
           auth: { getSession: async () => ({ data: { session: null } }),
                   onAuthStateChange() { return { data: null } },
                   signOut: async () => ({}) } };
}

const sandbox = {
  supabase: { createClient: dbStub },
  document: {
    getElementById: (id) => NODES.get(id) || stub,
    querySelector: () => stub,
    querySelectorAll: () => [],
    createElement: (t) => mkEl(t, "made-" + Math.random()),
    addEventListener(k, fn) { (DOC.listeners[k] ||= []).push(fn); },
    body: stub,
  },
  window: { addEventListener: () => {}, location: { hash: "", href: "" } },
  location: { hash: "", href: "" },
  confirm: () => true,
  setTimeout: (fn) => { if (typeof fn === "function") fn(); return 0 },
  setInterval: () => 0, clearInterval: () => {}, console,
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
function assert(c, m) { if (!c) throw new Error(m); }

const ID = "ep-27";
const YT = "https://youtu.be/225rEsPOfdI";
const EBOOK = "https://pp.practicalpunting.com.au/bet-your-own-prices";

/* Type into a box exactly as a person does — through the delegated `input`
 * listener app.js registers on `document`, so UI.dirty is marked by the real code. */
function typeInto(id, value) {
  const box = NODES.get(id) || mkEl("input", id);
  box.value = value;
  lanes.contains = () => true;
  for (const fn of DOC.listeners.input || []) fn({ target: box });
  return box;
}

/* Click a data-act button through the delegated `click` listener on #lanes. */
async function click(act, id) {
  const btn = { getAttribute: (k) => (k === "data-act" ? act : k === "data-ep" ? id : null),
                disabled: false, closest: () => null };
  const ev = { target: { closest: (sel) => (sel === "[data-act]" ? btn : null) } };
  for (const fn of lanes.listeners.click || []) await fn(ev);
  return btn;
}

ROWS.push({ id: ID, ep_number: 27, status: "ready", title: "Bet Your Own Prices",
            video_ok: true, ebook_ok: true, thumb_ok: true, title_ok: true });
await sandbox.loadAll();          // the app's own way in: EPISODES comes from the row

console.log("\n--- the board must not treat a SAVED field as still being typed ---");

typeInto("pub-ebook-" + ID, EBOOK);
typeInto("pub-url-" + ID, YT);
check("typing the two links marks the card as being edited", () => {
  const editing = sandbox.editingNow();
  assert(editing.includes("pub-ebook-" + ID) && editing.includes("pub-url-" + ID),
    "the board did not notice the typing at all: " + JSON.stringify(editing));
});

check("…and while they are unsaved the card is deliberately NOT redrawn", () => {
  const before = lanes.writes || 0;
  sandbox.renderBoard();
  assert((lanes.writes || 0) === before,
    "the board rebuilt the node she is typing in — that is the fault this " +
    "suppression exists to prevent, and it must stay");
});

const saved = await click("save-pub-ebook", ID);
check("SAVING the e-book link writes it to the row", () => {
  assert(WRITES.some((w) => w.id === ID && w.patch && w.patch.ebook_link === EBOOK),
    "the save did not reach the database: " + JSON.stringify(WRITES));
});

check("🔴 a SAVED field stops pausing the board", () => {
  const editing = sandbox.editingNow();
  assert(!editing.includes("pub-ebook-" + ID),
    "the saved e-book link is STILL counted as unsaved typing, so every later " +
    "render returns early and the card can never update — this is the freeze " +
    "Jodie reported. Still dirty: " + JSON.stringify(editing));
});

check("🔴 …and ONLY that field — the half-typed one beside it is still protected", () => {
  // C1, 2 Aug 2026: "it keeps disappearing if I move away to get the youtube link".
  // The publish card exists so the two links can be banked ONE AT A TIME. Releasing
  // the whole card on a single save would drop the pause guarding the other box and
  // rebuild it mid-type — the same fault, one field over.
  assert(sandbox.editingNow().includes("pub-url-" + ID),
    "saving the e-book link released the YouTube box too, so the next redraw " +
    "would wipe what is typed in it");
});

check("🔴 and the button she pressed is usable again", () => {
  assert(saved.disabled === false,
    "the Save button is still disabled after a successful write, so it reads as " +
    "hung — 'greyed out slightly' were the words. writeEpisode re-enables on " +
    "error and must do the same on success, because the redraw that would have " +
    "replaced the button may legitimately not happen");
});

console.log("\n--- and the same for Mark as published ---");
typeInto("pub-url-" + ID, YT);
const pub = await click("publish", ID);
check("publishing writes the status and the URL", () => {
  const w = WRITES.filter((x) => x.patch && x.patch.status === "published").pop();
  assert(w && w.patch.published_url === YT,
    "publish did not write what it should: " + JSON.stringify(WRITES.slice(-2)));
});
check("🔴 nothing is left marked as unsaved typing afterwards", () => {
  const editing = sandbox.editingNow();
  assert(!editing.some((k) => k.endsWith("-" + ID)),
    "after publishing, the card is still 'being edited' so it will never redraw " +
    "— it goes on showing 'Mark as published' for an episode that IS published, " +
    "which is the stale-surface fault E23c is about. Still dirty: " +
    JSON.stringify(editing));
});
check("🔴 and the publish button is not left dead", () => {
  assert(pub.disabled === false, "still disabled after a successful publish");
});

check("the board can redraw again once nothing is unsaved", () => {
  const before = lanes.writes || 0;
  sandbox.renderBoard();
  assert((lanes.writes || 0) > before,
    "the board still refuses to redraw, so the operator sees no change at all " +
    "until they reload the page");
});

console.log("\npublish unfreeze: " + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
