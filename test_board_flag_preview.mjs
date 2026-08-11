/* THE LABEL AND THE PICTURE MUST AGREE. (Jodie, 11 Aug 2026 — flagged twice.)
 *
 * The board's "Needs a look" card renders ONE picture, and `previewFor()` returned
 * `build_state.title_preview_url` no matter which flag was up. So the THUMBNAIL
 * placement review — "Have a look at the thumbnail" — showed the TITLE CARD.
 *
 * It is the same fault the title card itself already fixed, one artefact over. From
 * step_cards_render's own docstring: "the review used to be raised from inside
 * render_cards, which meant the step never returned and the engine never got to record
 * anything — so the preview's location existed only in the flag's prose." The thumbnail
 * kept raising from inside `build_thumbnail`, so it never published a preview at all,
 * and the board had only the title card's URL to show.
 *
 * Reads no source. Drives app.js's real function.
 *   node test_board_flag_preview.mjs
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

const TITLE_PNG = "https://x.supabase.co/storage/v1/object/public/episode-assets/PP-EP20/title-preview.png";
const THUMB_PNG = "https://x.supabase.co/storage/v1/object/public/episode-assets/PP-EP20/thumbnail-preview.png";

/* The two flags as the engine really raises them, word for word. */
const TITLE_MSG =
  "Have a look at the title card: " + TITLE_PNG + "\nThe words are already settled — " +
  "the headline, the part line and the byline are the approved packaging.";
const THUMB_MSG =
  "Have a look at the thumbnail: " + THUMB_PNG + "\nIt is built at the standard " +
  "placement (text upper-left over the scrim), which is what EP11 and EP12 both used.";

function ep(flagStep, msg, previews) {
  return {
    id: "e1", status: "assembling", needs_look: true, needs_look_message: msg,
    build_state: Object.assign({ flag_step: flagStep }, previews),
  };
}

console.log("-- THE BUG: the thumbnail flag showed the title card --");
const thumbFlag = ep("thumbnail", THUMB_MSG,
  { title_preview_url: TITLE_PNG, thumbnail_preview_url: THUMB_PNG });
check("the THUMBNAIL flag shows the THUMBNAIL, not the title card", () => {
  const got = sandbox.previewFor(thumbFlag);
  assert(got !== TITLE_PNG,
    "still showing the TITLE CARD on a flag whose own words say 'the thumbnail' — " +
    "this is the bug, reported twice");
  assert(got === THUMB_PNG, "expected the thumbnail preview, got " + JSON.stringify(got));
});

console.log("\n-- and the title card still shows the title card --");
const titleFlag = ep("cards_render", TITLE_MSG,
  { title_preview_url: TITLE_PNG, thumbnail_preview_url: THUMB_PNG });
check("the TITLE CARD flag shows the title card", () => {
  assert(sandbox.previewFor(titleFlag) === TITLE_PNG,
    "the fix has swapped the fault round instead of removing it");
});

console.log("\n-- it does not guess when it has nothing to show --");
check("no preview recorded -> nothing rendered", () => {
  assert(!sandbox.previewFor(ep("thumbnail", THUMB_MSG, {})),
    "invented a URL out of an empty build_state");
});
check("a flag with no picture at all shows nothing", () => {
  const other = ep("shot_map", "The card timings could not be derived.",
    { title_preview_url: TITLE_PNG, thumbnail_preview_url: THUMB_PNG });
  assert(!sandbox.previewFor(other),
    "showed a stale picture beside a flag that is not about a picture — which is how " +
    "this fault reads to the person looking at it");
});

console.log("\n-- OLDER EPISODES STILL WORK. EP18/EP19 have no flag_step. --");
check("an episode with only title_preview_url and no flag_step still shows it", () => {
  const old = { id: "e2", status: "building", needs_look: true,
                needs_look_message: TITLE_MSG,
                build_state: { title_preview_url: TITLE_PNG } };
  assert(sandbox.previewFor(old) === TITLE_PNG,
    "the fix broke every episode built before it");
});

console.log("\n-- the picture must be a real published URL, never a G: path --");
check("a Windows path is refused", () => {
  const bad = ep("thumbnail", THUMB_MSG,
    { thumbnail_preview_url: "G:\\My Drive\\PP Videos\\PP-EP20\\output\\x.png" });
  assert(!sandbox.previewFor(bad),
    "a local path would render a broken image for everyone without a G: drive — " +
    "which is the whole reason the preview is published in the first place");
});

console.log("\n" + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
