/* BUNDLE A, board side — the copy button, the balance, and the picture.
 *
 * Every check drives app.js's REAL functions against a fabricated row and asserts
 * what they RENDER. Nothing greps this repo's source: a check that looks for a
 * string in a file can be satisfied by a comment, and that has bitten twice.
 *
 *   node test_board_bundle_a.mjs
 */
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("./app.js", import.meta.url), "utf8");
const el = new Proxy({}, {
  get: (_t, k) => (k === "classList" || k === "style" ? el : () => {}),
  set: () => true,
});
const sandbox = {
  supabase: { createClient: () => new Proxy({}, {
    get: () => new Proxy(() => undefined, {
      get: () => () => undefined, apply: () => undefined }) }) },
  document: { getElementById: () => el, querySelector: () => el,
              querySelectorAll: () => [], addEventListener: () => {}, body: el },
  window: { addEventListener: () => {}, location: { hash: "", href: "" } },
  location: { hash: "", href: "" },
  navigator: { clipboard: { writeText: async () => {} } },
  setTimeout: () => 0, setInterval: () => 0, clearInterval: () => {},
  console,
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

const NAME = "PP-EP15 — Something — Part 1";
const SHOT = "https://ydqzdzpyemrqttiyhpwp.supabase.co/storage/v1/object/public/" +
             "episode-assets/PP-EP15/title-preview.png";

const base = {
  id: "abc", ep_number: 15, title: "Something — Part 1", status: "assembling",
  heygen_name: NAME, needs_look: false, progress_pct: 40,
  heartbeat_at: new Date().toISOString(), build_state: {},
};

/* ---- stop 5: the project name must be COPYABLE ---------------------------- */
check("the HeyGen project name has a copy control", () => {
  const h = sandbox.cardFor(base);
  assert(h.includes(NAME), "the project name is not shown at all");
  assert(/data-act="copy-heygen"/.test(h),
    "the project name is READ-ONLY TEXT. It must be typed into HeyGen character for " +
    "character — the engine matches on it to find the finished render — and re-typing " +
    "an em dash by hand fails silently: the master is never collected and the board " +
    "shows nothing wrong.");
});

check("an episode with no project name yet offers no copy control", () => {
  const h = sandbox.cardFor({ ...base, heygen_name: null });
  assert(!/data-act="copy-heygen"/.test(h), "offered a copy button with nothing to copy");
});

/* ---- stop 7: show the picture, not a path -------------------------------- */
const flagged = {
  ...base, needs_look: true,
  needs_look_message: "Have a look at the title card: " + SHOT,
  build_state: { title_preview_url: SHOT },
};

check("a flag with a published preview RENDERS THE PICTURE", () => {
  const h = sandbox.cardFor(flagged);
  assert(h.includes("<img"), "no image rendered — the operator is still being asked " +
    "to open a file they cannot reach");
  assert(h.includes(SHOT), "the image does not point at the published preview");
});

check("a Windows path is NEVER rendered as an image", () => {
  const winpath = "G:\\My Drive\\PP Videos\\PP-EP15\\overlay\\export\\title-preview.png";
  const h = sandbox.cardFor({
    ...base, needs_look: true,
    needs_look_message: "Have a look at the title card: " + winpath,
    build_state: { title_preview_url: winpath },
  });
  assert(!h.includes("<img"),
    "a local path was rendered as an image src — safeUrl must refuse anything that " +
    "is not http(s), or the card shows a broken image and hides the real message");
});

check("a flag with no preview still renders, without an image", () => {
  const h = sandbox.cardFor({
    ...base, needs_look: true, needs_look_message: "Something else went wrong.",
  });
  assert(h.includes("Something else went wrong."), "the message itself was lost");
  assert(!h.includes("<img"), "invented an image for a flag that has no picture");
});

/* ---- the credit runway --------------------------------------------------- */
check("the Higgsfield balance reaches the card", () => {
  const h = sandbox.metaFor({
    ...base, build_state: { steps: { credit_check: { meta: { balance: 131.72 } } } },
  });
  assert(h.includes("131.72"),
    "the balance is not shown. At ~56 credits an episode it goes from 'fine' to " +
    "'Top up, then clear this flag' with no warning, and the only place the number " +
    "lived was a CLI nobody on the board can run.");
});

check("a low balance says how many episodes are left", () => {
  const h = sandbox.metaFor({
    ...base, build_state: { steps: { credit_check: { meta: { balance: 131.72 } } } },
  });
  assert(/2 more episodes/.test(h),
    "a low balance does not say what it MEANS. 131.72 credits is a number; " +
    "'about 2 more episodes' is a decision.");
});

check("a healthy balance is shown without an alarm", () => {
  const h = sandbox.metaFor({
    ...base, build_state: { steps: { credit_check: { meta: { balance: 400 } } } },
  });
  assert(h.includes("400"), "the balance vanished when it was healthy");
  assert(!/more episode/.test(h), "cried wolf on a healthy balance");
});

check("an episode that has never run a credit check shows no balance line", () => {
  const h = sandbox.metaFor(base);
  assert(!/Higgsfield/.test(h), "invented a balance for an episode that has none");
});

console.log("\nbundle A (board): " + pass + " passed, " + fails.length + " failed");
process.exit(fails.length ? 1 : 0);
