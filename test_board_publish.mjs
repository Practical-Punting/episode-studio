/* C1 — the publish card eats what you type. Proved against the REAL app.js.
 *
 * THE SYMPTOM (Jodie): "When I paste the ebook link into the studio it keeps
 * disappearing if I move away from the screen to get the youtube link before I have
 * saved it."
 *
 * WHY THE OBVIOUS WORKAROUND CANNOT WORK: the card asks for the live YouTube URL and
 * the public e-book link. They live in two other places and there is ONE clipboard, so
 * filling the card without leaving the page is not physically possible.
 *
 * B1: this test is written to FAIL on the unfixed app.js, and the failure is the
 * evidence. It touches no network and no live row.
 *   node test_board_publish.mjs
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("./app.js", import.meta.url), "utf8");

/* ---- a DOM just real enough that harvest/restore can be exercised ---------- */
const NODES = new Map();                       // id -> fake element
function mkEl(tag, id, value = "", type = "url") {
  const el = { tagName: tag.toUpperCase(), id, value, type,
               classList: { add(){}, remove(){}, toggle(){} }, style: {},
               addEventListener(){}, scrollTop: 0, scrollHeight: 0,
               set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html || ""; },
               textContent: "", disabled: false, dataset: {} };
  NODES.set(id, el);
  return el;
}
/* A browser supports comma-separated selectors and a bare [id]; the shim has to as
 * well, or it silently reports zero matches and the code under test looks broken.
 * Extending the STAND-IN to what a real DOM does is not weakening the test — the
 * first version of this shim only understood `tag[id^='x']`, so the fix appeared to
 * fail when it was the harness that could not see it. */
function matchAll(sel) {
  const out = [];
  for (const part of sel.split(",").map((s) => s.trim())) {
    let m = /^(\w+)\[id\^='([^']+)'\]$/.exec(part);
    if (m) {
      out.push(...[...NODES.values()].filter(
        (e) => e.tagName === m[1].toUpperCase() && e.id.startsWith(m[2])));
      continue;
    }
    m = /^(\w+)\[id\]$/.exec(part);
    if (m) {
      out.push(...[...NODES.values()].filter(
        (e) => e.tagName === m[1].toUpperCase() && e.id));
    }
  }
  return [...new Set(out)];
}
const el = new Proxy({}, {
  get: (_t, k) => (k === "classList" || k === "style" ? el : () => {}),
  set: () => true,
});
const sandbox = {
  supabase: { createClient: () => new Proxy({}, {
    get: () => new Proxy(() => undefined, {
      get: () => () => undefined, apply: () => undefined }) }) },
  document: {
    getElementById: (id) => NODES.get(id) || el,
    querySelector: () => el,
    querySelectorAll: matchAll,
    addEventListener: () => {}, body: el,
  },
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
function assert(c, m) { if (!c) throw new Error(m); }

const EP = {
  id: "f63f0835", ep_number: 14, title: "The Meaning of Form — Part 1",
  status: "ready", published_url: null, ebook_link: null, youtube_copy: null,
};
const YT = "https://www.youtube.com/watch?v=ABCDEFGHIJK";
const EBOOK = "https://mailchi.mp/practicalpunting/the-meaning-of-form-part-1";

/* Build the card's inputs into the fake DOM exactly as gatePublish names them. */
function renderPublishCard(ep) {
  NODES.clear();
  const html = sandbox.gatePublish(ep);
  for (const m of html.matchAll(/id="(pub-[a-z]+-[^"]+)"[^>]*value="([^"]*)"/g)) {
    mkEl("input", m[1], m[2]);
  }
  // value="" attributes are emitted before the id on some builds; sweep for ids too
  for (const m of html.matchAll(/id="(pub-[a-z]+-[^"]+)"/g)) {
    if (!NODES.has(m[1])) mkEl("input", m[1], "");
  }
  return html;
}

console.log("\n--- the card as rendered ---");
check("the publish card offers both fields", () => {
  const html = renderPublishCard(EP);
  assert(/id="pub-url-/.test(html), "no YouTube URL input");
  assert(/id="pub-ebook-/.test(html), "no e-book link input");
  assert(NODES.size === 2, "expected 2 inputs, built " + NODES.size);
});

check("a re-render takes each field's value straight from the server row", () => {
  const html = sandbox.gatePublish({ ...EP, published_url: YT, ebook_link: EBOOK });
  assert(html.includes(YT) && html.includes(EBOOK),
    "the card does not echo the stored values — the mechanism under test is different");
});

/* ---- THE BUG ------------------------------------------------------------- */
console.log("\n--- typing, then a refresh ---");
check("a typed e-book link SURVIVES one poll-driven re-render", () => {
  renderPublishCard(EP);
  const box = NODES.get("pub-ebook-" + EP.id);
  box.value = EBOOK;                             // she pastes it
  sandbox.harvestDrafts();                       // loadAll() does this first
  renderPublishCard(EP);                         // server still has null
  sandbox.restoreDrafts();                       // renderBoard() does this last
  const after = NODES.get("pub-ebook-" + EP.id).value;
  assert(after === EBOOK,
    "the e-book link was EATEN by the refresh.\n      typed: " + EBOOK +
    "\n      after: " + JSON.stringify(after) +
    "\n      harvestDrafts() does not collect this field, so restoreDrafts() has " +
    "nothing to put back and the card is rebuilt from the server row.");
});

check("a typed YouTube URL survives one re-render", () => {
  renderPublishCard(EP);
  NODES.get("pub-url-" + EP.id).value = YT;
  sandbox.harvestDrafts();
  renderPublishCard(EP);
  sandbox.restoreDrafts();
  assert(NODES.get("pub-url-" + EP.id).value === YT, "the YouTube URL was eaten");
});

check("BOTH fields survive TWO refreshes, ten times running", () => {
  for (let i = 0; i < 10; i++) {
    renderPublishCard(EP);
    NODES.get("pub-ebook-" + EP.id).value = EBOOK;
    NODES.get("pub-url-" + EP.id).value = YT;
    for (let r = 0; r < 2; r++) {                // alt-tab away, two polls land
      sandbox.harvestDrafts();
      renderPublishCard(EP);
      sandbox.restoreDrafts();
    }
    const e = NODES.get("pub-ebook-" + EP.id).value;
    const u = NODES.get("pub-url-" + EP.id).value;
    assert(e === EBOOK && u === YT,
      "round " + (i + 1) + " of 10 lost a field — ebook=" + JSON.stringify(e) +
      " url=" + JSON.stringify(u));
  }
});

/* ---- one field at a time -------------------------------------------------- */
console.log("\n--- saving one field at a time ---");
check("the card offers a per-field save for each link", () => {
  const html = renderPublishCard(EP);
  assert(/data-act="save-pub-ebook"/.test(html),
    "no per-field save for the e-book link — she cannot bank it before leaving " +
    "the page to fetch the YouTube URL, which is the whole complaint");
  assert(/data-act="save-pub-url"/.test(html), "no per-field save for the YouTube URL");
});

check("a field saved on its own survives a FULL reload from the server", () => {
  // she saves the e-book link only; the server row now carries it, url still null
  const saved = { ...EP, ebook_link: EBOOK };
  NODES.clear();
  const html = sandbox.gatePublish(saved);
  assert(html.includes(EBOOK), "the saved e-book link is not echoed back after a reload");
  assert(!html.includes(YT), "the unsaved YouTube URL should NOT be on the server yet");
});

console.log("\npublish card: " + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
