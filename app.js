/* Episode Studio — live board for Practical Punting episodes.
 *
 * PUBLIC keys ONLY. The Supabase anon/publishable key is safe to ship in the browser
 * once RLS is enabled on public.episodes (which this project does — see supabase/).
 * NEVER put the Supabase service_role key, HeyGen, or Higgsfield keys in this file or
 * this repo — those live only in the engine's local .env.
 */
const SUPABASE_URL = "https://ydqzdzpyemrqttiyhpwp.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlkcXpkenB5ZW1ycXR0aXlocHdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ3NDI3NjQsImV4cCI6MjEwMDMxODc2NH0.S1fyuA3lSgx_vCZgb5g8JcCvnqXiytUoy1C3WrXPjoY";

const db = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// The 10-status contract, in board order. awaiting_* = a human step.
const STATUSES = [
  "queued", "building", "awaiting_render", "rendering", "awaiting_cover",
  "assembling", "awaiting_approval", "revising", "ready", "published",
];
const HUMAN = new Set(["awaiting_render", "awaiting_cover", "awaiting_approval"]);
const LABEL = {
  queued: "Queued", building: "Building", awaiting_render: "Awaiting render",
  rendering: "Rendering", awaiting_cover: "Awaiting cover", assembling: "Assembling",
  awaiting_approval: "Awaiting approval", revising: "Revising", ready: "Ready",
  published: "Published",
};

const $ = (id) => document.getElementById(id);

// --- routing between login and board --------------------------------------
async function render() {
  const { data: { session } } = await db.auth.getSession();
  if (session) showBoard(session); else showLogin();
}

function showLogin() {
  $("login").hidden = false;
  $("board").hidden = true;
  $("whobar").hidden = true;
}

async function showBoard(session) {
  $("login").hidden = true;
  $("board").hidden = false;
  $("whobar").hidden = false;
  $("who").textContent = session.user.email;
  await loadCards();
  subscribeRealtime();
}

// --- login (magic link) ----------------------------------------------------
$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("email").value.trim();
  const msg = $("login-msg");
  msg.textContent = "Sending link…";
  const { error } = await db.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: window.location.origin + window.location.pathname },
  });
  msg.textContent = error
    ? "Error: " + error.message
    : "Check " + email + " for a login link, then come back here.";
});

$("logout").addEventListener("click", async () => { await db.auth.signOut(); });

// --- the board -------------------------------------------------------------
async function loadCards() {
  const cards = $("cards");
  const { data, error } = await db
    .from("episodes")
    .select("*")
    .order("ep_number", { ascending: true, nullsFirst: false });

  if (error) { cards.innerHTML = `<p class="err">Could not load episodes: ${error.message}</p>`; return; }
  if (!data || !data.length) { cards.innerHTML = `<p class="muted">No episodes yet.</p>`; return; }

  cards.innerHTML = "";
  data.forEach((ep) => cards.appendChild(cardFor(ep)));
}

function cardFor(ep) {
  const el = document.createElement("article");
  el.className = "ep";

  const idx = STATUSES.indexOf(ep.status);
  const human = HUMAN.has(ep.status);
  const num = ep.ep_number != null ? `PP-EP${ep.ep_number}` : "PP-EP?";

  const steps = STATUSES.map((s, i) => {
    let c = "step";
    if (i < idx) c += " done";
    else if (i === idx) c += human ? " now human" : " now";
    return `<span class="${c}" title="${LABEL[s]}"></span>`;
  }).join("");

  const linkFor = (url, label) =>
    url ? `<a href="${url}" target="_blank" rel="noopener">${label}</a>` : "";
  const links = [
    linkFor(ep.video_url, "▶ Video"),
    linkFor(ep.ebook_url, "📘 E-book"),
    linkFor(ep.thumbnail_url, "🖼 Thumbnail"),
  ].join("");

  el.innerHTML = `
    <div class="ep-head">
      <span class="ep-num">${num}</span>
      <span class="ep-title">${escapeHtml(ep.title || "Untitled")}</span>
      <span class="ep-status ${human ? "human" : ""}">${LABEL[ep.status] || ep.status || "—"}</span>
    </div>
    <div class="steps">${steps}</div>
    <div class="steplabel">${idx >= 0 ? `Step ${idx + 1} of ${STATUSES.length}` : "Status: " + (ep.status || "unknown")}${human ? " · waiting on a human" : ""}</div>
    ${links ? `<div class="links">${links}</div>` : ""}
  `;
  return el;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// --- realtime: refresh on any change to the table --------------------------
let channel;
function subscribeRealtime() {
  if (channel) return;
  channel = db
    .channel("episodes-board")
    .on("postgres_changes", { event: "*", schema: "public", table: "episodes" }, () => loadCards())
    .subscribe();
}

// react to login/logout, then do the first render
db.auth.onAuthStateChange(() => render());
render();
