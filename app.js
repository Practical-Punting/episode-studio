/* Episode Studio — live operator interface (Phase 1).
 *
 * Reads and writes public.episodes + public.messages (migration 001 + 002).
 * The DB holds the 10-status contract; the friendly lane labels live here, in the UI.
 *
 * PUBLIC keys ONLY. The Supabase anon/publishable key is safe to ship in the browser
 * because RLS is on for both tables (authenticated users only). NEVER put the
 * service_role, HeyGen or Higgsfield keys in this file — those live in the engine's .env.
 */
const SUPABASE_URL = "https://ydqzdzpyemrqttiyhpwp.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlkcXpkenB5ZW1ycXR0aXlocHdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ3NDI3NjQsImV4cCI6MjEwMDMxODc2NH0.S1fyuA3lSgx_vCZgb5g8JcCvnqXiytUoy1C3WrXPjoY";

const db = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
const $ = (id) => document.getElementById(id);

/* ── the status contract → what the operator sees ────────────────────────
 * DB status is the source of truth. These are display-only.                */
const STATUS = {
  queued:            { label: "Waiting",                  cls: "wait", pct: 5  },
  building:          { label: "Building…",           cls: "work", pct: 30 },
  awaiting_render:   { label: "Your turn — render",  cls: "need", pct: 45 },
  rendering:         { label: "Rendering…",          cls: "work", pct: 55 },
  awaiting_cover:    { label: "Your turn — cover",   cls: "need", pct: 62 },
  assembling:        { label: "Assembling…",         cls: "work", pct: 78 },
  revising:          { label: "Revising…",           cls: "work", pct: 85 },
  awaiting_approval: { label: "Your turn — approve", cls: "need", pct: 92 },
  ready:             { label: "Your turn — publish", cls: "need", pct: 97 },
  published:         { label: "Published",                cls: "ok",   pct: 100 },
};

/* The four lanes, in operator priority order. "Your turn" sits at the top on purpose. */
const LANES = [
  { title: "Your turn",      statuses: ["awaiting_render", "awaiting_cover", "awaiting_approval", "ready"] },
  { title: "Engine working", statuses: ["building", "rendering", "assembling", "revising"] },
  { title: "Waiting",        statuses: ["queued"] },
  { title: "Done",           statuses: ["published"] },
];

const WORKING = new Set(["building", "rendering", "assembling", "revising"]);

/* The four separate approval gates (Title is its own gate, per the v3 mockup). */
const APPROVALS = [
  { field: "video_approved",     name: "Video",     url: "video_url"     },
  { field: "ebook_approved",     name: "E-book",    url: "ebook_url"     },
  { field: "thumbnail_approved", name: "Thumbnail", url: "thumbnail_url" },
  { field: "title_approved",     name: "Title",     url: null            },
];

/* A frozen engine can't flag itself, so the BOARD decides staleness client-side. */
const STALE_MS = 3 * 60 * 1000;   // the engine beats every 30s and renews a 3-min
                                 // lease, so 3 minutes of silence is already several
                                 // missed beats — not a slow moment. (29 Jul 2026)

/* WORDS GATE (PP-STANDARDS 2026-07-25): a queued episode isn't claimable by the
 * engine until the words (title + HOOK + byline) are approved — lock words BEFORE
 * any visual is built. The gate is title_approved; byline and hook travel as
 * "Byline: …" / "Hook: …" lines in notes.
 *
 * The hook was added 26 Jul 2026: it becomes the main thumbnail text, and on EP10
 * it was never consciously signed off. Approving the words now means approving the
 * exact words the thumbnail will carry. */
/* SCRIPT GATE (Jodie, 26 Jul 2026): the gate passes only when BOTH halves are
 * done — the words are approved AND "I've read the script" is ticked. Approving
 * the script is a DECISION and stays human forever, even after auto-render lands.
 * Starting a render is a chore and may be automated. Automation eats chores,
 * never decisions. */
function gatePassed(ep) {
  return !!(ep.title_approved && ep.script_read);
}
/* ── THE TITLE TRAP (3 Aug 2026) ──────────────────────────────────────────────
 *
 * Jodie's 2 Aug ruling made this gate LOAD-BEARING: the title approved here now goes
 * to YouTube verbatim. The board pre-fills it from the URL slug, and EP14's arrived as
 * "The Meaning Of Form Part 1" — capital "Of", no em dash. Under the old byline
 * derivation that was harmless; now it would ship.
 *
 * THE HOUSE FORM IS FETCHED, NOT COPIED. docs/house-form.json is the one home for the
 * separator and the channel line, and scripts/youtube_title.py reads the same file. A
 * JavaScript copy would be a second source of truth, and a second source of truth has
 * bitten this project three times — the captions, the self_qc cue check, the shot
 * map's clock. Each time the fix reached one reader and missed another. */
let HOUSE = null;
const HOUSE_READY = (async () => {
  try {
    const r = await fetch("docs/house-form.json", { cache: "no-cache" });
    if (r && r.ok) HOUSE = await r.json();
  } catch (e) { HOUSE = null; }
  // The gate may already be on screen by the time this lands, and a preview that
  // stays blank until she types is the same "find out afterwards" fault in miniature.
  try { if (typeof renderBoard === "function" && EPISODES.length) renderBoard(); }
  catch (e) { /* nothing rendered yet — the first render will pick it up */ }
  return HOUSE;
})();

/* Exposed as a FUNCTION on purpose: a top-level `const` is a lexical binding and does
 * not attach to the global object, so a test that awaited it would await `undefined`
 * and pass by accident. */
function houseReady() { return HOUSE_READY; }

function ytTitleFrom(title) {
  const t = (title || "").trim();
  if (!t || !HOUSE) return "";        // never guess the form; say nothing instead
  return t + HOUSE.separator + HOUSE.channel_line;
}

/* Does this look like it came straight off the URL slug? SUGGEST, NEVER BLOCK — she
 * may legitimately want an odd title one day, and a gate that refuses her judgement
 * is a worse fault than a title with a capital "Of" in it. */
const SMALL_WORDS = ["Of", "The", "A", "An", "And", "But", "Or", "For", "Nor", "At",
                     "By", "In", "On", "To", "Up", "As", "If", "Is"];
function titleSmell(title) {
  const t = (title || "").trim();
  if (!t) return [];
  const out = [];
  const caps = t.split(/\s+/).filter((w, i) => i > 0 && SMALL_WORDS.indexOf(w) !== -1);
  if (caps.length) {
    out.push("“" + caps.join("”, “") + "” looks like slug capitalisation — a small " +
             "word mid-title is usually lower case.");
  }
  if (/\bPart\s+\d/i.test(t) && !/—\s*Part\s+\d/i.test(t)) {
    out.push("the part is not set off with an em dash — the house form is " +
             "“Something — Part 1”, and the cover and title card use that too.");
  }
  return out;
}

function wordsGatePending(ep) {
  return ep.status === "queued" && !gatePassed(ep);
}
/* The words now live in their own columns so the board can EDIT them. Older rows
 * carried them as "Byline: …" / "Hook: …" lines in notes — still read as a
 * fallback so nothing already on the rail loses its words. */
function bylineOf(ep) {
  if (ep.byline) return ep.byline;
  const m = /byline:\s*(.+)/i.exec(ep.notes || "");
  return m ? m[1].trim() : "";
}
function hookOf(ep) {
  if (ep.hook) return ep.hook;
  const m = /hook:\s*(.+)/i.exec(ep.notes || "");
  return m ? m[1].trim() : "";
}

// ── state ────────────────────────────────────────────────────────────────
let EPISODES = [];
let MSGS = new Map();          // episode_id -> [messages]
let SESSION = null;
let channel = null;
const inflight = new Set();    // idempotency: one write per key at a time
// Survives the full re-render that realtime triggers, so a half-typed note isn't lost.
const UI = { open: new Set(), drafts: new Map(), kinds: new Map(), words: new Map(),
             dirty: new Set() };
// What `needs_look` looked like at the last render, so a NEW halt can be spotted
// while the board is paused. Keyed by episode id.
let LAST_FLAGS = new Map();

// ── helpers ──────────────────────────────────────────────────────────────
function esc(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
/* Only ever emit http/https hrefs — never a javascript: URI from a DB field. */
function safeUrl(u) {
  if (!u) return null;
  const s = String(u).trim();
  return /^https?:\/\//i.test(s) ? s : null;
}
function fmtDate(s) {
  if (!s) return "";
  return new Date(s).toLocaleString("en-AU",
    { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
function humanDur(ms) {
  const sec = Math.max(0, Math.floor(ms / 1000));
  if (sec < 60) return sec + " sec";
  const min = Math.floor(sec / 60);
  if (min < 60) return min + " min";
  const hr = Math.floor(min / 60), rm = min % 60;
  if (hr < 24) return rm ? hr + " hr " + rm + " min" : hr + " hr";
  const d = Math.floor(hr / 24), rh = hr % 24;
  return rh ? d + " d " + rh + " hr" : d + " d";
}
function ago(ts) { return ts ? humanDur(Date.now() - new Date(ts).getTime()) : null; }

function toast(el, msg, ok) {
  const t = $(el);
  if (!t) return;
  t.textContent = msg;
  t.className = "toast " + (ok ? "ok" : "err");
  if (ok) setTimeout(() => { t.className = "toast"; }, 4000);
}
function slugToTitle(url) {
  try {
    const parts = url.split("?")[0].split("#")[0].replace(/\/+$/, "").split("/");
    let seg = parts[parts.length - 1] || "";
    seg = seg.replace(/-\d{4,}$/, "").replace(/\.[a-z]+$/i, "");
    if (!seg) return "New episode";
    const words = seg.split("-").filter(Boolean)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1));
    return words.join(" ") || "New episode";
  } catch (e) { return "New episode"; }
}
/* messages.sender is free text; the board is the operator's seat. */
function senderFor(email) {
  const e = (email || "").toLowerCase();
  if (e.includes("jodie")) return "jodie";
  return "hugh";
}

/* "Needs a look" has two sources: the engine set the flag, OR the engine went quiet
 * mid-work (which it could never report itself). Both get the red treatment. */
/* THE ENGINE IS STOPPED — one place that decides it, so the chip, the elapsed line
 * and the alert can never disagree.
 *
 * On 28 Jul the engine died at 22:05 and this board went on saying "Working for
 * 1 d 1 hr · render cooking 1 d 1 hr" until 08:56 the next morning. Everything else
 * on the readiness list stops Hugh doing a task; THIS ONE TOLD HIM A LIE — it said
 * the machine was working while the machine was dead.
 *
 * The age of the heartbeat in small grey type was already on the card. It is not a
 * warning: it only means something to someone who already knows the rule, and Hugh
 * never will. So say it in words, in the chip, where the status normally goes. */
function engineStopped(ep) {
  if (!WORKING.has(ep.status)) return null;
  const beat = ep.heartbeat_at || ep.updated_at;
  if (!beat) return null;
  const age = Date.now() - new Date(beat).getTime();
  if (age <= STALE_MS) return null;
  return { since: beat, age: age };
}

/* The picture the current flag is asking about, if the engine published one.
 * build_state is jsonb and already there — no schema change for a preview URL. */
function previewFor(ep) {
  const bs = ep.build_state || {};
  return safeUrl(bs.title_preview_url || "");
}

/* The Higgsfield balance, as the last credit check measured it. THE RUNWAY MUST NOT
 * BE INVISIBLE: at ~56 credits an episode a 131-credit balance is barely two more,
 * and the only place that number existed was a CLI nobody on the board can run. */
function creditsFor(ep) {
  const st = ((ep.build_state || {}).steps || {}).credit_check || {};
  const b = (st.meta || {}).balance;
  return typeof b === "number" ? b : null;
}

/* ── THE PER-STEP WATCHDOG (D13, 3 Aug 2026) ──────────────────────────────────
 *
 * THE HEARTBEAT PROVES THE ENGINE, NOT THE STEP. EP14 sat on assemble_passB for three
 * and a half days with a six-second heartbeat, a moving progress bar and a stage line
 * that said "Assembling" — indistinguishable from an episode that was working. Jodie
 * noticed. Hugh will not be looking, which is the entire point of this project.
 *
 * Three states currently look identical and only ONE is a fault:
 *   working  — inside its budget, or no budget because it waits on a human by design
 *   waiting  — a flag is up, or the step waits on a human by design. LEGITIMATE, and
 *              may last days. Must NEVER alarm.
 *   stuck    — over budget, no flag, nobody coming. The only fault.
 *
 * The budget comes from the engine (STEP_BUDGET_S), so the board never has to guess
 * what is normal for a step, and a step that waits on a human carries budget_s: null.
 */
const DONE_STATUSES = ["published", "ready"];

function stepState(ep) {
  const cur = (ep.build_state || {}).current;
  if (!cur || !cur.started_at) return null;          // nothing in flight to judge
  const ran = Date.now() - new Date(cur.started_at).getTime();
  const out = { step: cur.step || "this step", ran: ran, budget: cur.budget_s };

  // A finished episode is never stuck, whatever marker was left behind.
  if (DONE_STATUSES.indexOf(ep.status) !== -1) return { ...out, state: "working" };
  // A raised flag IS the answer to "who is it waiting on". Days are fine.
  if (ep.needs_look) return { ...out, state: "waiting", who: "you" };
  // No budget = the step waits on a human by design (the HeyGen render, a cover pick).
  if (cur.budget_s == null) return { ...out, state: "waiting", who: "a human step" };
  if (ran > cur.budget_s * 1000) return { ...out, state: "stuck" };
  return { ...out, state: "working" };
}

/* ── C2 — THE STAGE LINE IS DERIVED, NEVER STORED (3 Aug 2026) ────────────────
 *
 * ELEVEN SIGHTINGS. `progress_step` is written to the rail when a flag is raised and
 * NEVER REWRITTEN, so it goes on describing a moment that has passed. EP08-EP12 are
 * all PUBLISHED and every one of them still says "Waiting on you — four approvals".
 * It misled twice in one day: EP13 read "Waiting on Hugh's Mailchimp e-book link" as
 * it went live, EP14 read "Waiting on you — four approvals" after all four were in.
 *
 * So the line is COMPUTED from things that cannot go stale — the status, the flag, and
 * the step in flight — the same three the watchdog already uses. The stored column is
 * left alone for compatibility and is no longer read anywhere on the board. */
const STEP_LABELS = {
  script_sync: "Reading the script Doc", audit_inputs: "Checking the inputs",
  render_gate: "Waiting for the HeyGen render to be started",
  credit_check: "Checking the credit budget", broll_submit: "Ordering the b-roll",
  broll_collect: "Collecting the b-roll", covers_ab: "Building the two cover options",
  cover_pick: "Waiting on your cover pick", ebook_cover: "Building the e-book cover",
  cards_render: "Rendering the motion cards", heygen_download: "Waiting for Gordon's render",
  shot_map: "Building the shot map", assemble_passA: "Assembling — presenter + b-roll (pass A)",
  assemble_passB: "Assembling — cards + audio (pass B)", ebook_build: "Building the e-book PDF",
  self_qc: "Checking the finished episode", thumbnail: "Building the thumbnail",
  youtube_copy: "Waiting on the YouTube copy",
};

function stageLine(ep) {
  const st = STATUS[ep.status] || { label: ep.status || "—" };
  if (ep.status === "published") return "Published";
  // A DEAD ENGINE OUTRANKS EVERYTHING BELOW. Missing this reintroduced C2b — the
  // stage line went back to "Assembling…" on an episode whose engine had stopped,
  // which is the exact fault C2b was built to end. Caught by its own test.
  if (engineStopped(ep)) return "ENGINE STOPPED — nothing is building";
  const ss = stepState(ep);
  if (ss && ss.state === "stuck") {
    return "Stuck — " + (STEP_LABELS[ss.step] || ss.step);
  }
  if (ep.needs_look) {
    return "Paused — needs a look" +
      (ss && STEP_LABELS[ss.step] ? " (" + STEP_LABELS[ss.step] + ")" : "");
  }
  if (ss && STEP_LABELS[ss.step]) return STEP_LABELS[ss.step];
  return st.label;
}

function needsLook(ep) {
  if (ep.needs_look) {
    return { msg: ep.needs_look_message || "The engine flagged this one — it needs a human.", flagged: true };
  }
  const dead = engineStopped(ep);
  if (dead) {
    return { msg: "ENGINE STOPPED — nothing has been building for " + ago(dead.since) +
                  ". The episode is safe and nothing is lost; it picks up where it left " +
                  "off. Start the engine again on the build machine: " +
                  "python engine/engine.py run --watch", flagged: true };
  }
  return null;
}

// ── routing ──────────────────────────────────────────────────────────────
async function route() {
  const { data: { session } } = await db.auth.getSession();
  SESSION = session;
  if (session) {
    // Magic-link tokens arrive in the URL hash; supabase-js consumes them on load,
    // so once we have a session we tidy the leftover "#..." out of the address bar.
    if (window.location.hash) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    $("login").hidden = true;
    $("board").hidden = SCRIPT_OPEN;          // the editor takes the board's place
    $("script").hidden = !SCRIPT_OPEN;
    $("statusbar").hidden = false;
    $("whoami").hidden = false;
    $("who").textContent = session.user.email;
    await loadAll();
    subscribeRealtime();
  } else {
    $("login").hidden = false;
    $("board").hidden = true;
    $("script").hidden = true;
    $("statusbar").hidden = true;
    $("whoami").hidden = true;
  }
}

/* ── THE SCRIPT EDITOR — A ROUTE, NOT AN OVERLAY ────────────────────────────
 *
 * 🔴 BOARD BUG 1, AND WHY THIS IS THE SHAPE OF THE FIX.
 * `renderBoard()` assigns `host.innerHTML` where `host = $("lanes")`, every 30
 * seconds. Everything inside #lanes is destroyed and rebuilt: caret, selection,
 * scroll position and — the one that matters — THE BROWSER UNDO STACK, which
 * does not survive node replacement. `restoreDrafts()` puts the VALUE back and
 * nothing else, so a long edit silently loses its place mid-sentence.
 *
 * Jodie raised bug 1 from LOW to BLOCKER for this work, and the reasoning is
 * arithmetic: the same bug ate a pasted YouTube URL. Applied to 2,500 words she
 * has just spent twenty minutes on, it destroys twenty minutes with no warning
 * and no undo. "Losing a link is annoying. Losing a script is the kind of thing
 * that makes a person stop trusting the tool entirely."
 *
 * THE EDITOR THEREFORE LIVES OUTSIDE #lanes ENTIRELY — a sibling panel that the
 * rebuild cannot reach, rather than more scaffolding around it. renderBoard()
 * is untouched. (REVIEW §0, §2.1.)
 *
 * ⚠️ AND THE POLL KEEPS RUNNING WHILE SHE TYPES, DELIBERATELY. It refreshes
 * #lanes underneath her; she simply is not in it. Suppressing the poll would be
 * a second mechanism to get wrong, and would leave the board stale the moment
 * she closed the panel. */
let SCRIPT_OPEN = false;

function openScript(id) {
  SCRIPT_OPEN = true;
  $("board").hidden = true;
  $("script").hidden = false;
  $("sc-text").focus();
}

function closeScript() {
  SCRIPT_OPEN = false;
  $("script").hidden = true;
  $("board").hidden = false;
}

// ── auth ─────────────────────────────────────────────────────────────────
$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("email").value.trim();
  toast("login-toast", "Sending your link…", true);
  const { error } = await db.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: window.location.origin + window.location.pathname,
      // Allow-list only: never provision a new account. An address that isn't one of
      // the three pre-created users gets no link (and RLS would block it anyway).
      shouldCreateUser: false,
    },
  });
  if (error) {
    // shouldCreateUser:false makes Supabase reject unknown emails ("Signups not allowed").
    const denied = /signup|not allowed|otp_disabled/i.test(error.message);
    toast("login-toast", denied
      ? "That email isn’t set up for the studio. Ask Jodie to add you."
      : "Couldn’t send it: " + error.message, false);
  } else {
    toast("login-toast", "Check " + email + " for a login link, then come back here.", true);
  }
});

$("logout").addEventListener("click", async () => {
  if (channel) { db.removeChannel(channel); channel = null; }
  await db.auth.signOut();
});

$("refresh").addEventListener("click", () => loadAll());

// ── start a new episode ──────────────────────────────────────────────────
$("start-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("urlin"), btn = $("startbtn");
  let url = (input.value || "").trim();
  if (!url) { toast("toast", "Paste an article link first.", false); return; }
  if (url.indexOf("http") !== 0) url = "https://" + url;

  btn.disabled = true; btn.textContent = "Adding…";
  try {
    // ep_number = max + 1
    const { data: maxRows, error: maxErr } = await db.from("episodes")
      .select("ep_number").order("ep_number", { ascending: false, nullsFirst: false }).limit(1);
    if (maxErr) throw maxErr;
    const nextNum = ((maxRows && maxRows[0] && maxRows[0].ep_number) || 0) + 1;
    const title = slugToTitle(url);

    const { error } = await db.from("episodes").insert({
      title, source_url: url, status: "queued", ep_number: nextNum,
      created_by: SESSION?.user?.email || "studio",
    });
    if (error) throw error;

    input.value = "";
    toast("toast", 'Queued PP-EP' + nextNum + ' — "' + title + '".', true);
    await loadAll();
  } catch (err) {
    toast("toast", "Could not add it: " + err.message, false);
  } finally {
    btn.disabled = false; btn.innerHTML = "Build episode &rarr;";
  }
});

// ── load ─────────────────────────────────────────────────────────────────
async function loadAll() {
  harvestDrafts();
  const { data, error } = await db.from("episodes").select("*")
    .order("ep_number", { ascending: false, nullsFirst: false })
    .order("created_at", { ascending: false });

  if (error) {
    $("count").textContent = "";
    $("lanes").innerHTML = '<div class="error">Could not reach the database.<br><small>' +
      esc(error.message) + "</small></div>";
    setLive(false);
    return;
  }
  EPISODES = data || [];

  // One query for every thread, rather than one per card.
  MSGS = new Map();
  if (EPISODES.length) {
    const { data: msgs } = await db.from("messages").select("*")
      .in("episode_id", EPISODES.map((e) => e.id))
      .order("created_at", { ascending: true });
    (msgs || []).forEach((m) => {
      if (!MSGS.has(m.episode_id)) MSGS.set(m.episode_id, []);
      MSGS.get(m.episode_id).push(m);
    });
  }

  renderBoard();
  setLive(true);
  $("updated").textContent = "Updated " +
    new Date().toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function setLive(ok) {
  $("livedot").className = "livedot" + (ok ? "" : " off");
  $("livetext").textContent = ok ? "Live · connected to your database" : "Connection lost";
}

// ── render ───────────────────────────────────────────────────────────────
/* ═══════════════════════════════════════════════════════════════════════════
 * THE REFRESH MUST NOT DESTROY WHAT A HUMAN IS EDITING.  (Slice 1 of the editor.)
 *
 * `renderBoard()` does `host.innerHTML = out` every 30 seconds. That does not
 * merely reset values — IT DESTROYS THE NODES. `restoreDrafts()` puts back
 * `.value` and nothing else, so caret, selection, scroll and THE BROWSER'S UNDO
 * STACK all die with the element.
 *
 * ⚠️ AND SAVE-AND-RESTORE CANNOT FIX IT. Caret, selection and scroll can be
 * replayed; UNDO CANNOT — it belongs to the destroyed node and no API exposes
 * it. So the only fix that delivers all four is TO NOT DESTROY THE NODE.
 *
 * WHAT IT COST WHEN IT BIT (EP16, 5 Aug 2026): the saved script-Doc URL was 168
 * characters — `https://docs.goog` + the entire correct URL + `le.com/…`. An
 * INSERTION AT OFFSET 17. The value had been restored and THE CARET HAD NOT, so
 * her next paste landed inside the old string. A wipe is visible; a moved caret
 * silently corrupts whatever is typed next.
 *
 * DIRTY, NOT MERELY FOCUSED. Jodie had ALT-TABBED AWAY when it happened, so a
 * focus-only test would have missed it exactly when it mattered.
 *
 * 🔒 WHY PAUSING IS SAFE, AND THE CONDITION IT RESTS ON:
 * `renderBoard()`'s only destructive write is `#lanes`. The script editor is a
 * SEPARATE ROUTE (a sibling of `#board`, like `#login`), so the poll never
 * rebuilds it. Therefore pausing only ever covers SHORT board edits — a hook, a
 * byline, a publish field: seconds to a minute. A board a minute stale is not a
 * problem. **If the editor is ever moved INSIDE `#lanes`, this reasoning breaks
 * and pausing would blind the operator for twenty minutes at a stretch.**
 *
 * 📌 NOTE FOR WHOEVER BUILDS SLICE 4 — NOT A FAULT TODAY, READ IT BEFORE YOU START.
 * WHILE THE BOARD IS PAUSED, THE SCRIPT PANEL IS FROZEN TOO. It lives inside
 * `#lanes`, so a dirty field holds the whole card, script and all.
 *
 * Normally harmless: a script does not change during a gate. **It changed twice
 * during EP17's gate** (Jodie amended the midroll line while sitting at it), and
 * the trap that opens is small but exact — she would have gone on reading the
 * pre-amendment words and approved having read a version that is not what gets
 * built. THE GATE'S WHOLE MEANING IS THAT SHE READ WHAT GETS BUILT. Handled that
 * night by asking her to reload BEFORE reading and before touching a field.
 *
 * ⚠️ WHEN SLICE 4 LANDS THIS STOPS BEING THEORETICAL, because then SHE is the one
 * changing the script while the pause is active, every time. Think it through
 * then: a paused card that is also the thing being edited needs to distinguish
 * "do not clobber what she is typing" from "do not hide what she is approving".
 * ═══════════════════════════════════════════════════════════════════════════ */

/* Anything the operator has touched since it was last saved. Delegated, so it
 * covers fields that do not exist yet — no list to maintain. */
document.addEventListener("input", (e) => {
  const el = e.target;
  if (!el || !el.id || !$("lanes")?.contains(el)) return;
  if (el.type === "checkbox" || el.type === "radio" || el.type === "file") return;
  UI.dirty.add(el.id);
}, true);

/* A human-readable name for a field, ASKED OF THE FIELD rather than kept in a
 * map keyed on id prefixes. A map would be a list somebody maintains, and the
 * next field added would be described as "a field" without anyone noticing. */
function fieldLabel(id) {
  const el = $(id);
  if (!el) return "";
  // 🔴 NO PLACEHOLDER FALLBACK. Found by driving the real board, 6 Aug 2026:
  // the script-Doc field has no label and its placeholder is a SAMPLE URL, so
  // the banner read "unsaved changes to https://docs.google.com/document/d/…".
  // A placeholder is an example VALUE, not a name — echoing it is neither
  // honest nor specific, and it puts a URL in the operator's box, which
  // docs/PP-operator-box-rule.md forbids outright.
  const lab = (el.labels && el.labels[0] && el.labels[0].textContent) ||
    el.getAttribute("aria-label") || "";
  return lab.trim().replace(/[:*]\s*$/, "").toLowerCase();
}

function editingNow() {
  return [...UI.dirty].filter((id) => $(id));
}

/* Episodes that have raised a flag since the last time the board was drawn. */
function newlyFlagged() {
  return EPISODES.filter((e) => e.needs_look && !LAST_FLAGS.get(e.id));
}

function rememberFlags() {
  LAST_FLAGS = new Map(EPISODES.map((e) => [e.id, !!e.needs_look]));
}

/* The banner lives OUTSIDE `#lanes`, so `host.innerHTML` never touches it —
 * which is what lets a halt reach the operator WITHOUT rebuilding the field she
 * is typing in. The flag and the edit are not in competition. */
function pauseBanner(fields, flagged) {
  let bar = $("pausebar");
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "pausebar";
    bar.className = "pausebar";
    $("lanes").parentNode.insertBefore(bar, $("lanes"));
  }
  if (!fields.length) { bar.hidden = true; bar.innerHTML = ""; return; }
  bar.hidden = false;
  // SAY WHAT IS PAUSED AND WHY, NAMING THE FIELD. A deliberate pause is only
  // different from the board describing the past as the present if it SAYS so.
  const names = [...new Set(fields.map(fieldLabel).filter(Boolean))];
  const what = names.length ? names.join(" and ")
    : (fields.length === 1 ? "a box you are filling in" : "boxes you are filling in");
  let msg = '<span class="pausebar-msg">Not updating while you have unsaved ' +
    "changes to " + esc(what) + ".</span>";
  // 🔴 A PAUSED BOARD MUST STILL BREAK THROUGH FOR A NEW FLAG. A stale picture
  // is a small cost; a hidden halt costs an hour, or a night.
  if (flagged.length) {
    msg = '<strong class="pausebar-flag">' +
      esc(flagged.map((e) => "PP-EP" + (e.ep_number ?? "?")).join(", ")) +
      (flagged.length === 1 ? " needs a look — it stopped just now."
        : " need a look — they stopped just now.") + "</strong> " + msg;
  }
  bar.innerHTML = msg +
    '<button type="button" id="pause-refresh" class="pausebar-btn">Refresh anyway</button>';
  $("pause-refresh").onclick = () => { UI.dirty.clear(); renderBoard(true); };
}

function renderBoard(force) {
  const editing = force ? [] : editingNow();
  if (editing.length) {
    pauseBanner(editing, newlyFlagged());
    tickTimers();
    return;                       // the node she is in is never touched
  }
  pauseBanner([], []);
  rememberFlags();
  const host = $("lanes");
  if (!EPISODES.length) {
    $("count").textContent = "";
    host.innerHTML = '<div class="empty">No episodes on the rail yet. ' +
      "Paste an article link above to start one.</div>";
    return;
  }
  const n = EPISODES.length;
  $("count").innerHTML = "<span>" + n + "</span> " +
    (n === 1 ? "episode on the rail" : "episodes on the rail");

  let out = "";
  for (const lane of LANES) {
    // Words-gate episodes are a HUMAN step, so they surface in "Your turn"
    // rather than sitting invisibly in Waiting.
    const eps = EPISODES.filter((e) =>
      lane.title === "Your turn"
        ? (lane.statuses.includes(e.status) || wordsGatePending(e))
        : lane.title === "Waiting"
          ? (e.status === "queued" && !wordsGatePending(e))
          : lane.statuses.includes(e.status));
    if (!eps.length) continue;
    out += '<section class="lane"><div class="lane-head">' +
      "<h2>" + esc(lane.title) + '</h2><span class="n">' + eps.length + "</span></div>" +
      '<div class="grid">' + eps.map(cardFor).join("") + "</div></section>";
  }
  // Any status outside the contract still has to be visible, not silently dropped.
  const known = LANES.flatMap((l) => l.statuses);
  const orphans = EPISODES.filter((e) => !known.includes(e.status));
  if (orphans.length) {
    out += '<section class="lane"><div class="lane-head"><h2>Unknown status</h2>' +
      '<span class="n">' + orphans.length + "</span></div>" +
      '<div class="grid">' + orphans.map(cardFor).join("") + "</div></section>";
  }
  host.innerHTML = out;
  restoreDrafts();
  tickTimers();
}

function cardFor(ep) {
  // THE CHIP MUST NOT SAY "Building…" WHEN NOTHING IS BUILDING. The status column
  // is the truth about the EPISODE; the heartbeat is the truth about the MACHINE,
  // and when they disagree the machine wins — an episode cannot be building if
  // nothing is running.
  const st = engineStopped(ep)
    ? { label: "ENGINE STOPPED", cls: "alert", pct: (ep.progress_pct || 0) }
    : wordsGatePending(ep)
    ? { label: "Your turn — words", cls: "need", pct: 3 }
    : STATUS[ep.status] || { label: ep.status || "—", cls: "wait", pct: 10 };
  const nl = needsLook(ep);
  const num = ep.ep_number != null ? "PP-EP" + ep.ep_number : "PP-EP?";
  const pct = (WORKING.has(ep.status) && ep.progress_pct > 0) ? ep.progress_pct : st.pct;
  const barCls = nl ? "" : (st.cls === "work" ? " work" : (st.cls === "ok" ? " ok" : ""));

  // THE WORDS GATE IS NOT A STATUS CARD. When she is reading a script, this card
  // breaks out of the lane and spans the page: it is the one human decision that
  // can never be automated away, and a 1,500-word script read through a 360px
  // slot is the studio asking for care it has made hard to give.
  // ASKED, NOT LISTED — showsScript() covers the words gate AND the render gate,
  // so a third gate that shows the script gets the reading surface without anyone
  // remembering to widen this line.
  const readingScript = showsScript(ep);
  let h = '<article class="card' + (nl ? " alert" : "") +
          (readingScript ? " wide" : "") + '">';

  h += '<div class="toprow"><h3><span class="epnum">' + esc(num) + "</span> " +
       esc(ep.title || "Untitled") + "</h3>" +
       '<span class="pill ' + (nl ? "alert" : st.cls) + '">' +
       (nl ? "Needs a look" : esc(st.label)) + "</span></div>";

  // THE HEYGEN NAME MUST BE COPYABLE, not just readable. It has to be typed into
  // HeyGen character-for-character — the engine matches on it to find the finished
  // render, and a mistyped name means the master is never collected and the episode
  // waits forever with nothing wrong on the board. Re-typing an em dash by hand is
  // the kind of thing that fails silently. (Stop 5, 3 Aug 2026.)
  h += ep.heygen_name
    ? '<p class="heygen"><span class="hg-name">' + esc(ep.heygen_name) + "</span>" +
      '<button class="mini copy" data-act="copy-heygen" data-ep="' + ep.id +
      '" title="Copy the exact project name">Copy</button></p>'
    : '<div style="height:6px"></div>';

  h += '<div class="bar' + barCls + '"><i style="width:' + pct + '%"></i></div>';
  h += '<div class="stage">' +
       esc(stageLine(ep)) + "</div>";
  h += '<div class="elapsed" data-elapsed="' + ep.id + '">' + esc(elapsedLine(ep)) + "</div>";

  // A STUCK STEP SAYS SO, IN WORDS, WITHOUT ANYONE NOTICING FIRST. It names the step,
  // says how long, and says the thing that separates it from a legitimate wait:
  // nobody is coming. A flagged episode and a by-design wait never reach here.
  const ss = stepState(ep);
  if (ss && ss.state === "stuck") {
    h += '<div class="stuckbox"><div class="stuck-t">⛔ Stuck — nobody is coming</div>' +
      '<div class="stuck-m"><b>' + esc(ss.step) + "</b> has been running for " +
      esc(ago(new Date(Date.now() - ss.ran).toISOString())) +
      ". Normal for this step is about " + Math.round(ss.budget / 60) + " min." +
      " Nothing is waiting on you — no flag is up — so it is not going to finish by " +
      "itself. Restarting the engine picks it up where it left off and loses nothing." +
      "</div></div>";
  }

  if (nl) {
    h += '<div class="needlook"><div class="nl-t">⚠ Needs a look</div>' +
         '<div class="nl-m">' + esc(nl.msg) + "</div>";
    // SHOW THE PICTURE, don't name a file path. A flag that says "have a look at
    // G:\My Drive\…\title-preview.png" is unanswerable by someone with no Windows
    // machine and no G: — which is everyone the board is for. The engine publishes
    // the preview to the public bucket and records the URL in build_state; this
    // renders it. (3 Aug 2026.)
    const shot = previewFor(ep);
    if (shot) {
      h += '<a class="nl-shot" href="' + esc(shot) + '" target="_blank" rel="noopener">' +
           '<img src="' + esc(shot) + '" alt="What the engine is asking you to look at" ' +
           'loading="lazy"></a>';
    }
    if (nl.flagged) {
      h += '<div class="nl-act"><button class="mini" data-act="clear-look" data-ep="' + ep.id +
           '">It’s sorted — carry on</button></div>';
    }
    h += "</div>";
  }

  h += scriptDriftNote(ep);
  h += gateFor(ep);
  h += metaFor(ep);
  h += threadFor(ep);
  h += "</article>";
  return h;
}

function elapsedLine(ep) {
  if (ep.status === "published") {
    if (ep.build_seconds) return "Built in " + humanDur(ep.build_seconds * 1000);
    return ep.finished_at ? "Published " + ago(ep.finished_at) + " ago" : "Published";
  }
  if (WORKING.has(ep.status)) {
    // NEVER say "Working" about a machine that is not running. This line claimed
    // "Working for 1 d 1 hr · render cooking 1 d 1 hr" for eleven hours after the
    // engine died — "render cooking" is the cruellest part, because it describes
    // something actively happening.
    const dead = engineStopped(ep);
    if (dead) return "ENGINE STOPPED — no check-in for " + ago(dead.since);
    const base = ep.started_at ? "Working for " + ago(ep.started_at) : "Working";
    const beat = ep.heartbeat_at ? " · last check-in " + ago(ep.heartbeat_at) + " ago" : "";
    // The long pole runs in parallel — show it, so "Building…" never looks idle.
    const render = ep.render_started_at
      ? " · render cooking " + ago(ep.render_started_at) : "";
    return base + render + beat;
  }
  if (STATUS[ep.status] && STATUS[ep.status].cls === "need") {
    return ep.updated_at ? "Waiting on you for " + ago(ep.updated_at) : "Waiting on you";
  }
  return ep.created_at ? "Queued " + ago(ep.created_at) + " ago" : "";
}

/* Re-tick the elapsed lines every second without rebuilding the DOM
 * (a rebuild would blow away focus and any half-typed note). */
function tickTimers() {
  document.querySelectorAll("[data-elapsed]").forEach((el) => {
    const ep = EPISODES.find((e) => e.id === el.getAttribute("data-elapsed"));
    if (ep) el.textContent = elapsedLine(ep);
  });
}
setInterval(tickTimers, 1000);

// ── the gates ────────────────────────────────────────────────────────────
/* The cover pick is offered the moment BOTH heroes exist — which, under the
 * locked order, is early in the build, while Gordon is still rendering. */
function coverPickOpen(ep) {
  return !!(ep.cover_a_url && ep.cover_b_url &&
            ep.cover_choice !== "A" && ep.cover_choice !== "B");
}

/* ═══ THE SCRIPT PANEL — ONE implementation, TWO gates ═══════════════════════
 * Used by the WORDS gate (read it before approving) and the RENDER gate (see and
 * copy what you are about to render). Written once on purpose: two panels would
 * be two things to keep in step, and the heading is a CLAIM about the content.
 *
 * 🔒 A <pre>, NOT AN INPUT — so harvestDrafts/restoreDrafts and the 30s refresh
 * pause never see it, on either card. Editing is slice 4 and is not this.
 */
function scriptPanel(ep, idPrefix) {
  const script = (ep.script_snapshot || "").trim();
  if (!script) return "";
  const words = script.split(/\s+/).filter(Boolean).length;
  return '<div class="scriptbox" id="' + idPrefix + ep.id + '">' +
    '<div class="sb-head">The script &middot; ' + words + " words &middot; about " +
    Math.round(words / 150) + " minutes &mdash; this is exactly what Gordon says</div>" +
    "<pre>" + esc(script) + "</pre></div>";
}

/* Is this card showing the script right now? Drives the full-width breakout, and
 * it is ASKED rather than listed, so a third gate that shows the script gets the
 * reading surface without anyone remembering to add it here. */
function showsScript(ep) {
  if (!(ep.script_snapshot || "").trim()) return false;
  if (wordsGatePending(ep)) return true;
  if (ep.status === "awaiting_render") return true;
  return ep.status === "building" && !!ep.heygen_name && !ep.render_started_at;
}

function gateFor(ep) {
  if (wordsGatePending(ep)) return gateWords(ep);
  switch (ep.status) {
    case "awaiting_render":   return gateRender(ep);
    case "awaiting_cover":    return gateCover(ep);
    case "awaiting_approval": return gateApprove(ep);
    case "ready":             return gatePublish(ep);
    case "building":
      // THE LOCKED ORDER (26 Jul 2026): human turns 2 and 3 both live here, on
      // top of each other, while the engine works — the render starts early and
      // the cover pick lands during the render window, not after it.
      return (ep.heygen_name && !ep.render_started_at ? gateRender(ep) : "") +
             (coverPickOpen(ep) ? gateCover(ep) : "");
    case "rendering":
      // Fallback path: covers can still be answered here (an episode that came
      // through before the pick was moved into the build).
      return coverPickOpen(ep) ? gateCover(ep) : "";
    default:                  return "";
  }
}

/* The words + script card. The three words are EDITABLE here — the operator is
 * the last word on them, so they change them in place rather than asking someone
 * else to. The script itself lives in a Google Doc (its one home); this card
 * links to it and will not let the gate pass until it's been read. */
function gateWords(ep) {
  const doc = safeUrl(ep.script_doc_url);
  const read = !!ep.script_read;
  const f = (name, label, value, ph) =>
    '<label class="wf"><span>' + esc(label) + "</span>" +
    '<input type="text" id="w-' + name + "-" + ep.id + '" value="' + esc(value || "") +
    '" placeholder="' + esc(ph) + '"></label>';

  let h = '<div class="gate"><h4>Your turn — the script and the words</h4>' +
    '<p class="g-hint">Nothing is built until you have <b>read the script</b> and ' +
    "approved these words. Change anything you like here — the thumbnail, cover, " +
    "title card and video all use exactly what you leave in these boxes. The " +
    "<b>hook</b> is the big text on the thumbnail.</p>";

  // 1 — the script. Its home is the RAIL (ruling A5): script_snapshot is the
  // script, and it is shown right here so she reads it where she approves it.
  // Episodes up to EP16 still carry a Doc and still get the link — nothing about
  // them changes.
  //
  // 🔒 THIS IS A <pre>, NOT A TEXTAREA, AND THAT IS THE WHOLE SAFETY ARGUMENT.
  // It is not an input, so harvestDrafts/restoreDrafts never see it, the 30s
  // refresh pause does not apply to it, and the caret/undo behaviour of the
  // fields below is untouched. Editing here is slice 4 and is NOT this change.
  const script = (ep.script_snapshot || "").trim();
  h += '<div class="scriptrow">';
  if (doc) {
    h += '<a class="doclink" href="' + esc(doc) + '" target="_blank" rel="noopener">' +
         "📄 Open the script &nearr;</a>";
    h += '<input type="url" id="w-doc-' + ep.id + '" value="' + esc(ep.script_doc_url || "") +
         '" placeholder="https://docs.google.com/document/d/…">';
  } else if (script) {
    // THE HEADING IS A CLAIM AND IT HAS TO BE TRUE. It says these are the words
    // Gordon speaks, so the panel may hold nothing else — no notes header, no
    // paste marker — and the count is the count of what is on screen.
    // The invariant is enforced where the script is WRITTEN (providers.
    // _script_checks refuses a script with notes on it, using render_ready's own
    // strip_notes_header), NOT stripped again here: a second implementation of
    // that rule, in another language, is exactly the drift worth avoiding.
    h += scriptPanel(ep, "w-script-");
  } else {
    h += '<div class="doclink none">No script yet. Nothing builds until there is one.</div>';
  }
  // THE GATE DOES NOT WEAKEN: the tick is enabled when there is something to
  // READ — a Doc to open, or the script on screen — and never otherwise.
  const readable = !!doc || !!script;
  h += '<label class="tick"><input type="checkbox" data-act="script-read" data-ep="' + ep.id +
       '"' + (read ? " checked" : "") + (readable ? "" : " disabled") +
       "><span>I've read the script</span></label>";
  if (!readable) h += '<p class="g-hint">There is no script to read yet, so the box stays locked.</p>';
  h += "</div>";

  // 2 — the three words, editable
  h += '<div class="wordsform">' +
    f("hook", "Hook (the big thumbnail text)", hookOf(ep), "e.g. Bet Less, Win More") +
    f("title", "Title", ep.title, "the episode title") +
    f("byline", "Byline", bylineOf(ep), "the one-line promise") +
    "</div>";

  // SHE MUST SEE WHAT THE TITLE BECOMES BEFORE SHE APPROVES IT. Live, from the same
  // house form the engine enforces. Updates as she types (see the input handler).
  const yt = ytTitleFrom(ep.title);
  h += '<div class="ytprev" data-ytprev="' + ep.id + '">' +
    '<span class="yt-l">On YouTube this will be</span>' +
    '<span class="yt-v">' + esc(yt || "—") + "</span></div>";
  const smell = titleSmell(ep.title);
  h += '<div class="ytsmell" data-ytsmell="' + ep.id + '">' +
    (smell.length
      ? "⚑ " + esc(smell.join("  ")) + " <i>Only a suggestion — approve it anyway if " +
        "that is the title you want.</i>"
      : "") + "</div>";

  const ready = read;
  h += '<p style="margin-top:12px">' +
    '<button class="btn" data-act="approve-words" data-ep="' + ep.id + '"' +
    (ready ? "" : " disabled") + ">Save &amp; approve &rarr;</button>" +
    (ready ? "" : ' <span class="muted">— tick “I’ve read the script” to enable</span>') +
    "</p></div>";
  return h;
}

/* Requirement 9: the Doc moved after approval. Say so on the card; never block. */
function scriptDriftNote(ep) {
  if (!ep.script_changed_since_approval) return "";
  const doc = safeUrl(ep.script_doc_url);
  return '<div class="drift">✎ The script Doc has changed since it was approved. ' +
    "This build used the version you approved, not the current Doc." +
    (doc ? ' <a href="' + esc(doc) + '" target="_blank" rel="noopener">Open the script &nearr;</a>' : "") +
    "</div>";
}

/* R8 (26 Jul 2026): the render is the LONG POLE and depends only on the spoken
 * track, which is final at the Words Gate — so this gate is offered as soon as the
 * engine has named the HeyGen project (a few seconds into the build), and the
 * pictures are generated beside it. It is never the last thing to happen. */
/* 🔴 THE RENDER CARD GIVES HER THE SCRIPT. (Jodie, 6 Aug 2026 — THIRD EPISODE.)
 * Her words: "But there was no script given to me so that I can start the render.
 * This is an issue we have discussed several times! And still not fixed."
 *
 * It asked her to go and render and handed her the PROJECT NAME — and not the
 * words, which is the thing HeyGen actually consumes. The words card shows the
 * script, but that card has CLOSED by the time she reaches this one, so at the
 * exact moment she needs the words there were none on screen. Recorded on the
 * EP17 list on 5 August as "the render card asks for the one thing it does not
 * give", and it has now blocked the longest job in the pipeline three times.
 *
 * TWO COPY BUTTONS, EACH SAYING WHAT IT IS FOR. Two unlabelled Copy buttons would
 * be a new confusion replacing an old one. */
function gateRender(ep) {
  const name = ep.heygen_name || (ep.ep_number != null ? "PP-EP" + ep.ep_number : "this episode");
  const parallel = ep.status === "building"
    ? " I’m generating the pictures right now — don’t wait for me, the render is the slow part."
    : "";
  let h = '<div class="gate"><h4>Your turn — start the render</h4>' +
    '<p class="g-hint">Open HeyGen, make the project <b>' + esc(name) +
    "</b>, paste the script below into it and hit render. Then tell the board it’s going." +
    parallel + "</p>";

  h += '<div class="copyrow">' +
    '<button class="mini copy" data-act="copy-heygen" data-ep="' + ep.id + '">' +
    "Copy the project name</button>" +
    '<button class="mini copy" data-act="copy-script" data-ep="' + ep.id + '">' +
    "Copy the whole script</button>" +
    '<span class="copyhint">One copies the name HeyGen asks for. The other copies ' +
    "the words Gordon speaks — all of them, ready to paste.</span></div>";

  h += scriptPanel(ep, "r-script-");

  h += '<button class="btn" data-act="render-started" data-ep=' + '"' + ep.id + '"' +
    ">I’ve started the render &rarr;</button></div>";
  return h;
}

function gateCover(ep) {
  // cover_choice is 'A' | 'B'; older rows may hold other text, so match exactly.
  const choice = ep.cover_choice === "A" || ep.cover_choice === "B" ? ep.cover_choice : null;
  const one = (letter, url) => {
    const safe = safeUrl(url);
    return '<button class="cover' + (choice === letter ? " chosen" : "") + '" ' +
      'data-act="cover" data-ep="' + ep.id + '" data-pick="' + letter + '">' +
      (safe ? '<img src="' + esc(safe) + '" alt="Cover ' + letter + '">'
            : '<div class="noimg">No cover ' + letter + " yet</div>") +
      '<div class="cv-l">' + (choice === letter ? "✓ Cover " + letter : "Cover " + letter) +
      "</div></button>";
  };
  const cooking = (ep.status === "building" || ep.status === "rendering")
    ? " Gordon’s render is still cooking — answering now keeps the build hands-off."
    : "";
  return '<div class="gate"><h4>Your turn — pick the cover</h4>' +
    '<p class="g-hint">Tap the one you want. The e-book cover and the end card are ' +
    "built from your pick." + cooking + "</p>" +
    '<div class="covers">' + one("A", ep.cover_a_url) + one("B", ep.cover_b_url) + "</div></div>";
}

function gateApprove(ep) {
  const done = APPROVALS.filter((a) => ep[a.field]).length;
  let h = '<div class="gate"><h4>Your turn — approve (' + done + " of 4)</h4>" +
    '<p class="g-hint">Each piece is signed off on its own. All four, and it moves to publish.</p>' +
    '<div class="approvals">';

  for (const a of APPROVALS) {
    const ok = !!ep[a.field];
    const link = a.url ? safeUrl(ep[a.url]) : null;
    h += '<div class="appr' + (ok ? " done" : "") + '">' +
      (ok ? '<span class="tick">✓</span>' : "") +
      '<span class="a-n">' + esc(a.name) +
      (link ? ' <a href="' + esc(link) + '" target="_blank" rel="noopener">open ↗</a>' : "") +
      "</span>" +
      (ok
        ? '<button class="undo" data-act="unapprove" data-ep="' + ep.id +
          '" data-field="' + a.field + '">undo</button>'
        : '<button class="mini" data-act="approve" data-ep="' + ep.id +
          '" data-field="' + a.field + '">Approve</button>') +
      "</div>";
  }
  h += "</div>";
  if (done === 4) h += '<p class="allset">All four approved — moving to publish.</p>';
  return h + "</div>";
}

function gatePublish(ep) {
  const yt = ep.youtube_copy
    ? '<p class="g-hint" style="white-space:pre-wrap">' + esc(ep.youtube_copy) + "</p>" : "";
  return '<div class="gate"><h4>Your turn — publish</h4>' +
    '<p class="g-hint">Upload to YouTube, then drop the live link in here to close it off.</p>' + yt +
    // ONE FIELD AT A TIME. The card asks for two values that live in two other
    // places, and there is one clipboard — so it CANNOT be filled without leaving
    // the page. Each link banks on its own: paste the e-book link, Save, go and get
    // the YouTube URL, come back, paste, Save. Nothing is lost either way, and
    // "Mark as published" is then just the last click rather than the only one.
    '<div class="pubrow">' +
      '<input type="url" id="pub-ebook-' + ep.id + '" placeholder="Public e-book link" ' +
      'value="' + esc(ep.ebook_link || "") + '">' +
      '<button class="btn ghost" data-act="save-pub-ebook" data-ep="' + ep.id + '">Save</button>' +
      (ep.ebook_link ? '<span class="saved">saved</span>' : "") +
    "</div>" +
    '<div class="pubrow">' +
      '<input type="url" id="pub-url-' + ep.id + '" placeholder="Live YouTube URL (https://…)" ' +
      'value="' + esc(ep.published_url || "") + '">' +
      '<button class="btn ghost" data-act="save-pub-url" data-ep="' + ep.id + '">Save</button>' +
      (ep.published_url ? '<span class="saved">saved</span>' : "") +
    "</div>" +
    '<button class="btn" data-act="publish" data-ep="' + ep.id + '">Mark as published &rarr;</button>' +
    "</div>";
}

function metaFor(ep) {
  let h = '<div class="meta">';
  h += '<div><span class="lbl">Created</span><span class="val">' + esc(fmtDate(ep.created_at)) + "</span></div>";

  const src = safeUrl(ep.source_url);
  if (src) {
    h += '<div><span class="lbl">Source article</span><span class="val">' +
      '<a href="' + esc(src) + '" target="_blank" rel="noopener">' + esc(src) + "</a></span></div>";
  }
  const links = [["video_url", "Video"], ["ebook_url", "E-book"], ["thumbnail_url", "Thumbnail"],
                 ["published_url", "On YouTube"]]
    .map(([f, label]) => { const u = safeUrl(ep[f]); return u
      ? '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + label + "</a>" : ""; })
    .join("");
  if (links) h += '<div><span class="lbl">Deliverables</span><div class="links">' + links + "</div></div>";

  const c = ep.cost || {};
  const bits = [];
  if (c.higgsfield_credits) bits.push(c.higgsfield_credits + " HF credits");
  if (c.heygen_credits) bits.push(c.heygen_credits + " HeyGen");
  if (c.aud) bits.push("$" + (isNaN(+c.aud) ? c.aud : (+c.aud).toFixed(2)) + " AUD");
  if (bits.length) h += '<div><span class="lbl">Cost</span><span class="val">' +
    esc(bits.join(" · ")) + "</span></div>";

  // THE RUNWAY, IN PLAIN SIGHT. At roughly 56 credits an episode, a balance in the
  // low hundreds is only two or three more — and until now that number lived only in
  // a CLI nobody on the board can run, so it would have gone from "fine" to "Top up,
  // then clear this flag" with no warning. Flagged low at two episodes' worth.
  const bal = creditsFor(ep);
  if (bal !== null) {
    // MEASURED, not a round number: EP14 spent 52.5 on b-roll plus 4.0 on the two
    // cover heroes. Warn while there are fewer than THREE episodes left, so the
    // conversation happens with two in hand rather than on the morning it stops.
    const PER_EPISODE = 56.5;
    const left = Math.floor(bal / PER_EPISODE);
    const low = bal < 3 * PER_EPISODE;
    h += '<div><span class="lbl">Higgsfield</span><span class="val' +
      (low ? " warn" : "") + '">' + esc(bal.toFixed(2)) + " credits" +
      (low ? " · about " + left + " more episode" + (left === 1 ? "" : "s") : "") +
      "</span></div>";
  }

  return h + "</div>";
}

// ── the thread ───────────────────────────────────────────────────────────
function threadFor(ep) {
  const msgs = MSGS.get(ep.id) || [];
  const open = UI.open.has(ep.id);
  let h = '<div class="thread"><button class="thread-toggle" data-act="thread" data-ep="' + ep.id + '">' +
    (open ? "▾" : "▸") + " Thread" +
    (msgs.length ? ' <span class="cnt">' + msgs.length + "</span>" : "") + "</button>";

  if (!open) return h + "</div>";

  h += '<div class="msgs">';
  if (!msgs.length) h += '<p class="nomsg">Nothing here yet. Ask the engine anything.</p>';
  for (const m of msgs) {
    const who = (m.sender || "").toLowerCase();
    h += '<div class="msg ' + (who === "engine" ? "engine" : who === "hugh" ? "hugh" : "") + '">' +
      '<div class="m-h"><span>' + esc(m.sender) + "</span>" +
      (m.kind && m.kind !== "note" ? '<span class="m-k">' + esc(m.kind.replace("_", " ")) + "</span>" : "") +
      "<span>" + esc(fmtDate(m.created_at)) + "</span>" +
      (m.handled ? '<span class="m-done">✓ handled</span>' : "") +
      '</div><div class="m-b">' + esc(m.body) + "</div></div>";
  }
  h += "</div>";

  h += '<div class="chatbox"><textarea id="chat-' + ep.id +
    '" placeholder="Write a note, or ask for a change…" aria-label="Message"></textarea>' +
    '<div class="chatrow"><select id="kind-' + ep.id + '" aria-label="Message type">' +
    '<option value="note">Note</option><option value="change_request">Change request</option>' +
    '</select><button class="btn" data-act="send" data-ep="' + ep.id + '">Send</button></div></div>';

  return h + "</div>";
}

/* The only inputs that must NOT survive a re-render. `urlin` is the new-article box:
 * it is cleared deliberately once an episode is created, and re-filling it would
 * invite a duplicate. `email` is the sign-in box. Everything else is an operator's
 * work in progress and is protected. */
const NEVER_HARVEST = new Set(["urlin", "email", "q", "search"]);

/* Keep whatever the operator has typed across a realtime-triggered re-render. */
function harvestDrafts() {
  document.querySelectorAll("textarea[id^='chat-']").forEach((t) => {
    const id = t.id.slice(5);
    if (t.value) UI.drafts.set(id, t.value); else UI.drafts.delete(id);
  });
  document.querySelectorAll("select[id^='kind-']").forEach((s) => UI.kinds.set(s.id.slice(5), s.value));
  // EVERY input on a card is an edit-in-progress. Keyed by the full input id.
  //
  // 🔴 C1, 2 Aug 2026 — WHY THIS IS NOW A SKIP-LIST AND NOT AN ALLOW-LIST.
  // This line used to read `input[id^='w-']`: only the Words Gate boxes. The publish
  // card's two inputs (`pub-url-…`, `pub-ebook-…`) matched nothing, so they were
  // never harvested, and `renderBoard()` rebuilt them from the server row every time
  // the 30-second poll fired. Jodie: "it keeps disappearing if I move away from the
  // screen to get the youtube link before I have saved it." She was right, and the
  // card is IMPOSSIBLE to fill without leaving the page — it wants the live YouTube
  // URL and the public e-book link, which live in two other places, and there is one
  // clipboard. EP13 was only published because its two values were written straight
  // to the rail, bypassing the card.
  //
  // A HAND-MAINTAINED ALLOW-LIST MEANS EVERY FIELD ADDED LATER IS UNPROTECTED BY
  // DEFAULT, and nobody finds out until an operator loses work. Inverted: everything
  // with an id is protected, and the two shell inputs that must NOT persist are named.
  document.querySelectorAll("input[id], textarea[id]").forEach((i) => {
    if (NEVER_HARVEST.has(i.id) || i.id.startsWith("chat-")) return;
    if (i.type === "checkbox" || i.type === "radio" || i.type === "file") return;
    if (i.value) UI.words.set(i.id, i.value); else UI.words.delete(i.id);
  });
}
/* Once a write lands, the saved row is the truth — drop the in-progress copies
 * for that episode so they can't overwrite what was just stored. */
function clearWordDrafts(id) {
  [...UI.words.keys()].forEach((k) => { if (k.endsWith("-" + id)) UI.words.delete(k); });
  // A saved field is no longer unsaved, so it must stop pausing the board.
  // Without this the pause would outlive the edit and the board would freeze
  // until a reload — a guard that never lets go is its own fault.
  [...UI.dirty].forEach((k) => { if (k.endsWith("-" + id)) UI.dirty.delete(k); });
}
function restoreDrafts() {
  UI.drafts.forEach((v, id) => { const t = $("chat-" + id); if (t) t.value = v; });
  UI.kinds.forEach((v, id) => { const s = $("kind-" + id); if (s) s.value = v; });
  UI.words.forEach((v, id) => { const i = $(id); if (i && v) i.value = v; });
  // Threads read newest-last, so start them scrolled to the bottom.
  document.querySelectorAll(".msgs").forEach((m) => { m.scrollTop = m.scrollHeight; });
}

// ── writes (idempotent: one in-flight write per key, buttons lock) ───────
async function writeEpisode(id, patch, key, btn) {
  const k = key || id + ":" + Object.keys(patch).join(",");
  if (inflight.has(k)) return false;           // swallows the double-click
  inflight.add(k);
  if (btn) btn.disabled = true;
  const { error } = await db.from("episodes").update(patch).eq("id", id);
  inflight.delete(k);
  if (error) {
    toast("toast", "Could not save: " + error.message, false);
    if (btn) btn.disabled = false;
    return false;
  }
  await loadAll();
  return true;
}

/* THE PREVIEW UPDATES AS SHE TYPES. Without this she would see the title her words
 * became only after saving — which is the same "find out afterwards" this fixes. */
$("lanes").addEventListener("input", (e) => {
  const box = e.target;
  if (!box || !box.id || box.id.indexOf("w-title-") !== 0) return;
  const id = box.id.slice("w-title-".length);
  const prev = document.querySelector('[data-ytprev="' + id + '"] .yt-v');
  if (prev) prev.textContent = ytTitleFrom(box.value) || "—";
  const smellBox = document.querySelector('[data-ytsmell="' + id + '"]');
  if (smellBox) {
    const s = titleSmell(box.value);
    smellBox.innerHTML = s.length
      ? "⚑ " + esc(s.join("  ")) + " <i>Only a suggestion — approve it anyway if " +
        "that is the title you want.</i>"
      : "";
  }
});

$("lanes").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-act]");
  if (!btn) return;
  const act = btn.getAttribute("data-act");
  const id = btn.getAttribute("data-ep");
  const ep = EPISODES.find((x) => x.id === id);
  if (!ep) return;

  if (act === "thread") {
    harvestDrafts();
    if (UI.open.has(id)) UI.open.delete(id); else UI.open.add(id);
    renderBoard();
    return;
  }

  if (act === "script-read") {
    // Half of the Script Gate. Never set by anything but this click.
    const on = btn.checked;
    if (!(await writeEpisode(id, { script_read: on }, id + ":read", null))) btn.checked = !on;
    else toast("toast", on ? "Script marked as read." : "Script no longer marked as read.", true);
    return;
  }

  if (act === "approve-words") {
    // Save the operator's edits AND close the gate in one write — what's in the
    // boxes is what gets built, so the two must never drift apart.
    const val = (n) => ($("w-" + n + "-" + id)?.value || "").trim();
    const title = val("title"), doc = val("doc");
    if (!title) { toast("toast", "The title can’t be empty.", false); return; }
    if (doc && !safeUrl(doc)) { toast("toast", "That script link isn’t a valid https URL.", false); return; }
    // THE GATE DOES NOT WEAKEN — it stops asking for a DOC and starts asking for
    // a SCRIPT. Ruling A5: the script's home is the rail, so an episode written
    // in the script box has nothing to link and never will. What is refused is
    // approving words with NO SCRIPT AT ALL, which is the thing that actually
    // matters and is what the old Doc check was standing in for.
    if (!doc && !(ep.script_snapshot || "").trim()) {
      toast("toast", "There’s no script for this episode yet — nothing to read or approve.", false);
      return;
    }
    const patch = {
      title, hook: val("hook"), byline: val("byline"),
      script_read: true, title_approved: true,
    };
    // Only ever WRITE the Doc URL when there is a field for it (an episode that
    // still has a Doc). Sending "" on a rail episode would write an empty string
    // where the column is NULL, and `fetch_script` branches on that value.
    if ($("w-doc-" + id)) patch.script_doc_url = doc;
    if (await writeEpisode(id, patch, id + ":words", btn)) {
      clearWordDrafts(id);      // saved — the DB is now the truth, not the boxes
      toast("toast", "Script read and words approved — the build can start.", true);
    }
    return;
  }

  if (act === "save-doc") {
    const doc = ($("w-doc-" + id)?.value || "").trim();
    if (!safeUrl(doc)) { toast("toast", "Paste the Doc’s https link first.", false); return; }
    if (await writeEpisode(id, { script_doc_url: doc }, id + ":doc", btn)) {
      clearWordDrafts(id);
      toast("toast", "Script Doc linked.", true);
    }
    return;
  }

  if (act === "render-started") {
    // Under the locked order this is usually clicked WHILE the engine is still
    // building, so it records render_started_at and leaves the status alone —
    // the engine reads the stamp and walks itself into `rendering`. Clicked at
    // the awaiting_render park (the fallback path) it also advances the status.
    const patch = { render_started_at: new Date().toISOString() };
    if (ep.status === "awaiting_render") patch.status = "rendering";
    const k = id + ":render";
    if (inflight.has(k)) return;
    inflight.add(k);
    btn.disabled = true;
    let { error } = await db.from("episodes").update(patch).eq("id", id);
    if (error && /render_started_at/.test(error.message || "")) {
      // Migration 003 isn't applied yet — degrade honestly rather than block.
      delete patch.render_started_at;
      error = Object.keys(patch).length
        ? (await db.from("episodes").update(patch).eq("id", id)).error : null;
      inflight.delete(k);
      await loadAll();
      toast("toast", "Render noted, but the board can’t remember it yet — " +
                     "migration 003 (render_started_at) hasn’t been applied.", false);
      return;
    }
    inflight.delete(k);
    if (error) { toast("toast", "Could not save: " + error.message, false); btn.disabled = false; return; }
    await loadAll();
    toast("toast", "Render marked as started — I’ll keep building alongside it.", true);
    return;
  }

  if (act === "cover") {
    const pick = btn.getAttribute("data-pick");
    // At the awaiting_cover gate the pick also advances the episode; picked
    // early (while rendering) it records the choice only — the lane stays
    // truthful and the engine advances itself when the master lands.
    const patch = ep.status === "awaiting_cover"
      ? { cover_choice: pick, status: "assembling" }
      : { cover_choice: pick };
    if (await writeEpisode(id, patch, id + ":cover", btn))
      toast("toast", "Cover " + pick + " chosen" +
        (patch.status ? " — assembling." : " — noted for assembly."), true);
    return;
  }

  if (act === "approve") {
    const field = btn.getAttribute("data-field");
    const patch = {};
    patch[field] = true;
    // Closing the fourth gate advances the episode, in the same write.
    const rest = APPROVALS.filter((a) => a.field !== field);
    if (rest.every((a) => ep[a.field])) patch.status = "ready";
    if (await writeEpisode(id, patch, id + ":" + field, btn)) {
      toast("toast", patch.status === "ready"
        ? "All four approved — ready to publish."
        : "Approved.", true);
    }
    return;
  }

  if (act === "unapprove") {
    const field = btn.getAttribute("data-field");
    const patch = {};
    patch[field] = false;
    if (ep.status === "ready") patch.status = "awaiting_approval";  // pull it back
    if (await writeEpisode(id, patch, id + ":" + field, btn)) toast("toast", "Approval removed.", true);
    return;
  }

  // THE WHOLE SCRIPT, IN ONE ACTION. Copying 1,484 words by dragging a selection
  // across a scrolling panel is not a workflow — and the panel is read-only, so
  // there is no other way to get the words out of it.
  if (act === "copy-script") {
    const script = (ep.script_snapshot || "").trim();
    if (!script) { toast("toast", "There’s no script on this one yet.", false); return; }
    try {
      await navigator.clipboard.writeText(script);
      const n = script.split(/\s+/).filter(Boolean).length;
      toast("toast", "Script copied — all " + n + " words. Paste it into HeyGen.", true);
    } catch (e) {
      toast("toast", "Couldn’t copy automatically — select the script and copy it.", false);
    }
    return;
  }

  if (act === "copy-heygen") {
    const name = ep.heygen_name || "";
    if (!name) { toast("toast", "No project name on this one yet.", false); return; }
    try {
      await navigator.clipboard.writeText(name);
      toast("toast", "Project name copied — paste it into HeyGen.", true);
    } catch (e) {
      // Clipboard access can be refused (no https, no permission). Say so instead
      // of failing silently, and leave the name selectable on the card either way.
      toast("toast", "Couldn't copy automatically — select the name and copy it.", false);
    }
    return;
  }

  if (act === "clear-look") {
    if (await writeEpisode(id, { needs_look: false, needs_look_message: null }, id + ":look", btn))
      toast("toast", "Cleared.", true);
    return;
  }

  // Each link banks on its own, so neither has to be held in the head (or the
  // clipboard) while the other is fetched. C1, 2 Aug 2026.
  if (act === "save-pub-ebook" || act === "save-pub-url") {
    const isEbook = act === "save-pub-ebook";
    const boxId = (isEbook ? "pub-ebook-" : "pub-url-") + id;
    const val = ($(boxId).value || "").trim();
    if (!val) { toast("toast", "Paste the link first.", false); return; }
    if (!safeUrl(val)) { toast("toast", "That doesn't look like a link (https://…).", false); return; }
    const patch = {};
    patch[isEbook ? "ebook_link" : "published_url"] = val;
    if (await writeEpisode(id, patch, id + ":" + act, btn)) {
      // The saved row is now the truth for THIS field, so drop its in-progress copy
      // — otherwise the draft would keep overwriting what was just stored.
      UI.words.delete(boxId);
      toast("toast", isEbook ? "E-book link saved." : "YouTube link saved.", true);
    }
    return;
  }

  if (act === "publish") {
    const url = ($("pub-url-" + id).value || "").trim();
    const ebook = ($("pub-ebook-" + id).value || "").trim();
    if (!safeUrl(url)) { toast("toast", "Paste the live YouTube URL first (https://…).", false); return; }
    // THE E-BOOK LINK IS THE ONE THING THE STUDIO HAS NEVER CAPTURED. In fourteen
    // episodes it has been populated ONCE (EP13), and only because it was written by
    // hand. Seven published episodes have none, and those links now exist only inside
    // the live YouTube descriptions. It is the link that sells the subscriptions.
    // WARN, DO NOT BLOCK — and RECORD that the skip was deliberate, so "no link" can
    // be told apart from "nobody was asked".
    if (!ebook && !confirm(
        "No public e-book link.\n\nThat link is how this episode earns its " +
        "subscriptions, and it is the one field the studio has never reliably " +
        "captured — seven published episodes have none, recoverable only from their " +
        "live YouTube descriptions.\n\nPublish without it anyway?")) {
      return;
    }
    const patch = { status: "published", published_url: url, finished_at: new Date().toISOString() };
    if (ebook) patch.ebook_link = ebook;
    else patch.notes = ((ep.notes ? ep.notes + "\n" : "") +
      "ebook_link skipped deliberately at publish, " + new Date().toISOString().slice(0, 10));
    if (await writeEpisode(id, patch, id + ":publish", btn)) toast("toast", "Published — nice one.", true);
    return;
  }

  if (act === "send") {
    const box = $("chat-" + id);
    const body = (box.value || "").trim();
    if (!body) { toast("toast", "Type something first.", false); return; }
    const kind = $("kind-" + id).value || "note";
    const k = id + ":msg";
    if (inflight.has(k)) return;
    inflight.add(k);
    btn.disabled = true;
    const { error } = await db.from("messages").insert({
      episode_id: id, sender: senderFor(SESSION?.user?.email), kind, body,
    });
    inflight.delete(k);
    if (error) { toast("toast", "Could not send: " + error.message, false); btn.disabled = false; return; }
    box.value = "";
    UI.drafts.delete(id);
    UI.open.add(id);
    await loadAll();
    toast("toast", kind === "change_request" ? "Change request sent." : "Note posted.", true);
  }
});

// ── realtime ─────────────────────────────────────────────────────────────
let reloadTimer = null;
function bumpReload() {                  // a burst of row changes = one reload
  clearTimeout(reloadTimer);
  reloadTimer = setTimeout(loadAll, 250);
}
function subscribeRealtime() {
  if (channel) return;
  channel = db.channel("studio")
    .on("postgres_changes", { event: "*", schema: "public", table: "episodes" }, bumpReload)
    .on("postgres_changes", { event: "*", schema: "public", table: "messages" }, bumpReload)
    .subscribe();
}
// A safety net in case the socket quietly drops.
setInterval(() => { if (SESSION) loadAll(); }, 30000);

db.auth.onAuthStateChange(() => route());
route();
