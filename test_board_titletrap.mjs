/* THE TITLE TRAP — she must SEE what her title becomes before she approves it.
 *
 * Jodie's 2 Aug ruling made the Words Gate load-bearing: the title approved there now
 * propagates VERBATIM to YouTube. The board pre-fills it from the URL slug, and EP14's
 * arrived as "The Meaning Of Form Part 1" — capital "Of", no em dash. Under the old
 * byline derivation that was harmless. Now it would ship.
 *
 * The preview must be composed from the SAME house form the engine enforces
 * (docs/house-form.json), never a JavaScript copy — a copy is a second source of truth
 * and this project has been bitten by one three times.
 *
 * Reads no source. Drives app.js's real functions.
 *   node test_board_titletrap.mjs
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
  setTimeout: (f) => { if (typeof f === "function") f(); return 0; },
  setInterval: () => 0, clearInterval: () => {}, console,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "app.js" });

/* The house form is FETCHED, so give the page the tick a real browser gives it.
 * app.js exposes the promise precisely so this is a wait, not a sleep. */
await sandbox.houseReady();

let pass = 0; const fails = [];
function check(n, fn) {
  try { fn(); pass++; console.log("  ok  " + n); }
  catch (e) { fails.push([n, e.message]); console.log("  !!  " + n + "\n      " + e.message); }
}
function assert(c, m) { if (!c) throw new Error(m); }

const SLUG = "The Meaning Of Form Part 1";        // exactly what EP14's board produced
const GOOD = "The Meaning of Form — Part 1";

check("the derived title is composed from the SHARED house form", () => {
  const got = sandbox.ytTitleFrom(GOOD);
  assert(got === GOOD + house.separator + house.channel_line,
    "the board does not compose the title from docs/house-form.json. It must use the " +
    "same two strings the engine enforces, or the preview and the shipped title can " +
    "drift — which is the fault this whole rule exists to close. got: " + got);
});

check("the Words Gate SHOWS the title that will ship", () => {
  const h = sandbox.gateWords({ id: "a", status: "queued", title: SLUG,
                                hook: "X", byline: "Y", script_doc_url: null });
  assert(h.includes(SLUG + house.separator + house.channel_line),
    "the gate does not show what the title becomes. She approves a title and only " +
    "meets its consequence on YouTube.");
});

check("a slug-derived title is FLAGGED — capitalised small word", () => {
  const s = sandbox.titleSmell(SLUG);
  assert(s && s.length, "'" + SLUG + "' raised nothing. That is EP14's actual " +
    "pre-fill: capital 'Of' and no em dash before the part.");
  assert(/\bOf\b/.test(s.join(" ")), "does not name the capitalised small word: " + s);
});

check("a slug-derived title is FLAGGED — missing em dash before the part", () => {
  const s = sandbox.titleSmell("Hidden Aces Part 2");
  assert(s && s.some((x) => /dash|—/.test(x)),
    "a bare 'Part 2' with no em dash raised nothing: " + JSON.stringify(s));
});

check("a hyphen where an em dash belongs is FLAGGED", () => {
  const s = sandbox.titleSmell("Hidden Aces - Part 2");
  assert(s && s.some((x) => /dash|—/.test(x)), "a hyphen separator raised nothing");
});

check("a good title raises NOTHING", () => {
  assert(sandbox.titleSmell(GOOD).length === 0,
    "cried wolf on a correct title: " + JSON.stringify(sandbox.titleSmell(GOOD)));
  assert(sandbox.titleSmell("Hidden Aces — Part 2").length === 0, "cried wolf on EP12's");
});

check("the suggestion SUGGESTS — it never blocks approval", () => {
  const h = sandbox.gateWords({ id: "a", status: "queued", title: SLUG, hook: "X",
                                byline: "Y", script_doc_url: "https://docs.google.com/document/d/x/edit",
                                script_read: true });
  assert(/data-act="approve-words"/.test(h), "the approve button vanished");
  const m = /data-act="approve-words"[^>]*>/.exec(h)[0];
  assert(!/disabled/.test(m),
    "a smelly title DISABLED approval. She may legitimately want an odd title one " +
    "day, and the rule is suggest, never block.");
});

check("an empty title neither previews nor cries wolf", () => {
  assert(sandbox.titleSmell("").length === 0, "complained about an empty box");
  assert(sandbox.ytTitleFrom("") === "", "previewed a title for an empty box");
});

console.log("\ntitle trap: " + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
