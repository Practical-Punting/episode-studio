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
const STALE_MS = 5 * 60 * 1000;

/* WORDS GATE (PP-STANDARDS 2026-07-25): a queued episode isn't claimable by the
 * engine until the words (title + byline) are approved — lock words BEFORE any
 * visual is built. The gate is title_approved; the byline travels as a
 * "Byline: …" line in notes. */
function wordsGatePending(ep) {
  return ep.status === "queued" && !ep.title_approved;
}
function bylineOf(ep) {
  const m = /byline:\s*(.+)/i.exec(ep.notes || "");
  return m ? m[1].trim() : null;
}

// ── state ────────────────────────────────────────────────────────────────
let EPISODES = [];
let MSGS = new Map();          // episode_id -> [messages]
let SESSION = null;
let channel = null;
const inflight = new Set();    // idempotency: one write per key at a time
// Survives the full re-render that realtime triggers, so a half-typed note isn't lost.
const UI = { open: new Set(), drafts: new Map(), kinds: new Map() };

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
function needsLook(ep) {
  if (ep.needs_look) {
    return { msg: ep.needs_look_message || "The engine flagged this one — it needs a human.", flagged: true };
  }
  if (WORKING.has(ep.status)) {
    const beat = ep.heartbeat_at || ep.updated_at;
    if (beat && Date.now() - new Date(beat).getTime() > STALE_MS) {
      return { msg: "The engine hasn't checked in for " + ago(beat) +
                    ". It may be stuck — worth a look.", flagged: false };
    }
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
    $("board").hidden = false;
    $("statusbar").hidden = false;
    $("whoami").hidden = false;
    $("who").textContent = session.user.email;
    await loadAll();
    subscribeRealtime();
  } else {
    $("login").hidden = false;
    $("board").hidden = true;
    $("statusbar").hidden = true;
    $("whoami").hidden = true;
  }
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
function renderBoard() {
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
  const st = wordsGatePending(ep)
    ? { label: "Your turn — words", cls: "need", pct: 3 }
    : STATUS[ep.status] || { label: ep.status || "—", cls: "wait", pct: 10 };
  const nl = needsLook(ep);
  const num = ep.ep_number != null ? "PP-EP" + ep.ep_number : "PP-EP?";
  const pct = (WORKING.has(ep.status) && ep.progress_pct > 0) ? ep.progress_pct : st.pct;
  const barCls = nl ? "" : (st.cls === "work" ? " work" : (st.cls === "ok" ? " ok" : ""));

  let h = '<article class="card' + (nl ? " alert" : "") + '">';

  h += '<div class="toprow"><h3><span class="epnum">' + esc(num) + "</span> " +
       esc(ep.title || "Untitled") + "</h3>" +
       '<span class="pill ' + (nl ? "alert" : st.cls) + '">' +
       (nl ? "Needs a look" : esc(st.label)) + "</span></div>";

  h += ep.heygen_name ? '<p class="heygen">' + esc(ep.heygen_name) + "</p>"
                      : '<div style="height:6px"></div>';

  h += '<div class="bar' + barCls + '"><i style="width:' + pct + '%"></i></div>';
  h += '<div class="stage">' +
       esc(ep.progress_step || st.label) + "</div>";
  h += '<div class="elapsed" data-elapsed="' + ep.id + '">' + esc(elapsedLine(ep)) + "</div>";

  if (nl) {
    h += '<div class="needlook"><div class="nl-t">⚠ Needs a look</div>' +
         '<div class="nl-m">' + esc(nl.msg) + "</div>";
    if (nl.flagged) {
      h += '<div class="nl-act"><button class="mini" data-act="clear-look" data-ep="' + ep.id +
           '">It’s sorted — carry on</button></div>';
    }
    h += "</div>";
  }

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
    const base = ep.started_at ? "Working for " + ago(ep.started_at) : "Working";
    const beat = ep.heartbeat_at ? " · last check-in " + ago(ep.heartbeat_at) + " ago" : "";
    return base + beat;
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
function gateFor(ep) {
  if (wordsGatePending(ep)) return gateWords(ep);
  switch (ep.status) {
    case "awaiting_render":   return gateRender(ep);
    case "awaiting_cover":    return gateCover(ep);
    case "awaiting_approval": return gateApprove(ep);
    case "ready":             return gatePublish(ep);
    case "rendering":
      // Covers can be ready before the HeyGen master — let the pick happen
      // early (choice only; the engine advances itself when the master lands).
      return ep.cover_a_url && ep.cover_b_url &&
             ep.cover_choice !== "A" && ep.cover_choice !== "B"
        ? gateCover(ep) : "";
    default:                  return "";
  }
}

function gateWords(ep) {
  const byline = bylineOf(ep);
  return '<div class="gate"><h4>Your turn — approve the words</h4>' +
    '<p class="g-hint">Lock the title + byline BEFORE anything is built — the thumbnail, ' +
    "cover, title card and video all use these words. The engine won’t start until you approve.</p>" +
    '<div class="approvals">' +
    '<div class="appr"><span class="a-n"><b>Title:</b> ' + esc(ep.title || "—") + "</span></div>" +
    '<div class="appr"><span class="a-n"><b>Byline:</b> ' +
      (byline ? esc(byline)
              : '<i class="muted">none yet — add a "Byline: …" line to the episode notes</i>') +
    "</span></div></div>" +
    '<p style="margin-top:12px"><button class="btn" data-act="approve-words" data-ep="' + ep.id +
    '">Approve the words &rarr;</button></p></div>';
}

function gateRender(ep) {
  const name = ep.heygen_name || (ep.ep_number != null ? "PP-EP" + ep.ep_number : "this episode");
  return '<div class="gate"><h4>Your turn — start the render</h4>' +
    '<p class="g-hint">Open HeyGen, find <b>' + esc(name) +
    "</b> and hit render. Then tell the board it’s going.</p>" +
    '<button class="btn" data-act="render-started" data-ep=' + '"' + ep.id + '"' +
    ">I’ve started the render &rarr;</button></div>";
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
  return '<div class="gate"><h4>Your turn — pick the cover</h4>' +
    '<p class="g-hint">Tap the one you want. The engine assembles with it.</p>' +
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
    '<input type="url" id="pub-url-' + ep.id + '" placeholder="Live YouTube URL (https://…)" ' +
    'value="' + esc(ep.published_url || "") + '">' +
    '<input type="url" id="pub-ebook-' + ep.id + '" placeholder="Public e-book link (optional)" ' +
    'value="' + esc(ep.ebook_link || "") + '">' +
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

/* Keep whatever the operator has typed across a realtime-triggered re-render. */
function harvestDrafts() {
  document.querySelectorAll("textarea[id^='chat-']").forEach((t) => {
    const id = t.id.slice(5);
    if (t.value) UI.drafts.set(id, t.value); else UI.drafts.delete(id);
  });
  document.querySelectorAll("select[id^='kind-']").forEach((s) => UI.kinds.set(s.id.slice(5), s.value));
}
function restoreDrafts() {
  UI.drafts.forEach((v, id) => { const t = $("chat-" + id); if (t) t.value = v; });
  UI.kinds.forEach((v, id) => { const s = $("kind-" + id); if (s) s.value = v; });
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

  if (act === "approve-words") {
    if (await writeEpisode(id, { title_approved: true }, id + ":words", btn))
      toast("toast", "Words locked — the engine can start the build.", true);
    return;
  }

  if (act === "render-started") {
    if (await writeEpisode(id, { status: "rendering" }, id + ":render", btn))
      toast("toast", "Render marked as started.", true);
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

  if (act === "clear-look") {
    if (await writeEpisode(id, { needs_look: false, needs_look_message: null }, id + ":look", btn))
      toast("toast", "Cleared.", true);
    return;
  }

  if (act === "publish") {
    const url = ($("pub-url-" + id).value || "").trim();
    const ebook = ($("pub-ebook-" + id).value || "").trim();
    if (!safeUrl(url)) { toast("toast", "Paste the live YouTube URL first (https://…).", false); return; }
    const patch = { status: "published", published_url: url, finished_at: new Date().toISOString() };
    if (ebook) patch.ebook_link = ebook;
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
