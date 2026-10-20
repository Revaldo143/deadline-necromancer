/* Deadline Necromancer — frontend logic (vanilla JS, no build step). */
"use strict";

const state = {
  projects: [],
  plans: {}, // path -> ResurrectResponse
  health: null,
  scanning: false,
};

const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function fmtDate(iso) {
  if (!iso) return "unknown";
  const d = new Date(iso);
  return isNaN(d) ? "unknown" : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

function toast(message) {
  const box = $("toasts");
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  box.appendChild(el);
  setTimeout(() => el.remove(), 5200);
}

async function api(path, options) {
  const resp = await fetch(path, options);
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) { /* keep default */ }
    throw new Error(detail);
  }
  return resp.json();
}

/* ---------------- health ---------------- */

async function loadHealth() {
  const pillText = $("ollamaStatusText");
  const dot = document.querySelector("#ollamaStatus .dot");
  try {
    const h = await api("/api/health");
    state.health = h;
    if (h.ollama_reachable && h.model_available) {
      dot.className = "dot dot-on";
      pillText.textContent = `Gemma online · ${h.model}`;
    } else if (h.ollama_reachable) {
      dot.className = "dot dot-off";
      pillText.textContent = `Ollama up · model ${h.model} not pulled — demo mode`;
    } else {
      dot.className = "dot dot-off";
      pillText.textContent = "Demo mode · Ollama offline";
    }
    if (!$("scanPath").value) $("scanPath").value = h.default_scan_path;
    return h;
  } catch (e) {
    dot.className = "dot dot-off";
    pillText.textContent = "Backend unreachable";
    return null;
  }
}

/* ---------------- scan ---------------- */

function renderSkeletons() {
  $("grid").innerHTML = Array.from({ length: 6 }, () => '<div class="skeleton"></div>').join("");
}

async function doScan() {
  if (state.scanning) return;
  const path = $("scanPath").value.trim();
  if (!path) { toast("Enter a folder path to scan."); return; }
  state.scanning = true;
  const btn = $("scanBtn");
  btn.disabled = true;
  btn.textContent = "Digging…";
  $("scanHint").textContent = `Scanning ${path}`;
  $("emptyState").hidden = true;
  renderSkeletons();
  try {
    const data = await api("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    state.projects = data.projects;
    state.scanRoot = data.path;
    renderResults();
    $("scanHint").textContent = `Scanned ${data.path}`;
  } catch (e) {
    $("grid").innerHTML = "";
    $("statsRow").hidden = true;
    $("controlsRow").hidden = true;
    $("scanHint").textContent = "";
    toast(e.message);
  } finally {
    state.scanning = false;
    btn.disabled = false;
    btn.textContent = "Scan the graveyard";
  }
}

/* ---------------- rendering ---------------- */

function sortedProjects() {
  const mode = $("sortSelect").value;
  const arr = [...state.projects];
  const key = {
    "dead-desc": (p) => -p.days_dead,
    "dead-asc": (p) => p.days_dead,
    "todo-desc": (p) => -p.todo_count,
    "commits-desc": (p) => -p.total_commits,
  }[mode] || (() => 0);
  return arr.sort((a, b) => (a.error ? 1 : 0) - (b.error ? 1 : 0) || key(a) - key(b));
}

function renderResults() {
  const projects = state.projects;
  const valid = projects.filter((p) => !p.error);
  $("statsRow").hidden = projects.length === 0;
  $("controlsRow").hidden = projects.length === 0;
  $("emptyState").hidden = projects.length !== 0;

  $("statCorpses").textContent = projects.length;
  $("statDays").textContent = valid.reduce((s, p) => s + p.days_dead, 0).toLocaleString();
  $("statTodos").textContent = valid.reduce((s, p) => s + p.todo_count, 0).toLocaleString();
  updateHoursStat();
  $("resultCount").textContent = projects.length
    ? `${plural(projects.length, "corpse")} in ${state.scanRoot || ""}`
    : "";

  $("grid").innerHTML = sortedProjects().map(cardHTML).join("");
  document.querySelectorAll(".card-btn").forEach((btn) => {
    btn.addEventListener("click", () => openPlan(btn.dataset.path));
  });
}

function updateHoursStat() {
  const saved = Object.values(state.plans).reduce((s, r) => s + (r.hours_saved || 0), 0);
  $("statHours").textContent = saved > 0 ? `${saved.toFixed(1)}h` : "—";
}

function cardHTML(p) {
  if (p.error) {
    return `<article class="card">
      <div class="card-top"><h3 class="card-name">${esc(p.name)}</h3>
      <p class="card-rip">Unreadable</p></div>
      <p class="card-error">${esc(p.error)}</p>
    </article>`;
  }
  const chips = [];
  if (p.primary_language && p.primary_language !== "Unknown")
    chips.push(`<span class="chip">${esc(p.primary_language)}</span>`);
  if (p.uncommitted_changes > 0)
    chips.push(`<span class="chip chip-warn">⚠ ${plural(p.uncommitted_changes, "uncommitted change")}</span>`);
  if (p.stash_count > 0)
    chips.push(`<span class="chip chip-stash">🗄 ${plural(p.stash_count, "stash")}</span>`);
  if (p.todo_count > 0)
    chips.push(`<span class="chip">${plural(p.todo_count, "TODO")}</span>`);
  const cached = state.plans[p.path];
  if (cached)
    chips.push(`<span class="chip chip-saved">✦ saves ${cached.hours_saved.toFixed(1)}h</span>`);

  return `<article class="card">
    <div class="card-top">
      <h3 class="card-name">${esc(p.name)}</h3>
      <p class="card-rip">RIP · ${esc(fmtDate(p.last_commit_at))}</p>
      <p class="card-dead">dead for <b>${p.days_dead}</b> ${p.days_dead === 1 ? "day" : "days"}</p>
    </div>
    <div class="card-meta">
      <span>${plural(p.total_commits, "commit")}</span>
      <span>${plural(p.file_count, "file")}</span>
      <span>${p.branch_count} branch${p.branch_count === 1 ? "" : "es"}</span>
    </div>
    ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
    ${p.last_commit_message ? `<p class="card-words" title="Last commit message">${esc(p.last_commit_message)}</p>` : ""}
    ${p.readme_line ? `<p class="card-readme">${esc(p.readme_line)}</p>` : ""}
    <button class="card-btn" data-path="${esc(p.path)}">${cached ? "View resurrection plan" : "⚱ Resurrect this project"}</button>
  </article>`;
}

/* ---------------- resurrection plan modal ---------------- */

const LOADING_PHRASES = [
  "Consulting the spirits…",
  "Reading the last commits…",
  "Dusting off the tombstone…",
  "Asking Gemma for a resurrection plan…",
  "Measuring the coffin…",
];
let loadingTimer = null;

function openModal(html) {
  $("modalBody").innerHTML = html;
  $("modalBackdrop").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeModal() {
  $("modalBackdrop").classList.add("hidden");
  document.body.style.overflow = "";
  if (loadingTimer) { clearInterval(loadingTimer); loadingTimer = null; }
}

function planLoadingHTML(name) {
  return `<div class="plan-loading">
    <span class="moon">🌕</span>
    <h3 class="plan-title">${esc(name)}</h3>
    <p id="loadingPhrase">${LOADING_PHRASES[0]}</p>
  </div>`;
}

async function openPlan(path, force = false) {
  const project = state.projects.find((p) => p.path === path);
  const name = project ? project.name : path;
  if (!force && state.plans[path]) {
    openModal(planHTML(state.plans[path]));
    wirePlanActions(path);
    animatePayoff();
    return;
  }
  openModal(planLoadingHTML(name));
  let i = 0;
  loadingTimer = setInterval(() => {
    const el = $("loadingPhrase");
    if (el) el.textContent = LOADING_PHRASES[++i % LOADING_PHRASES.length];
  }, 2600);
  try {
    const data = await api("/api/resurrect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, force }),
    });
    state.plans[path] = data;
    if (loadingTimer) { clearInterval(loadingTimer); loadingTimer = null; }
    openModal(planHTML(data));
    wirePlanActions(path);
    animatePayoff();
    renderResults(); // refresh card chips + hours stat
  } catch (e) {
    if (loadingTimer) { clearInterval(loadingTimer); loadingTimer = null; }
    closeModal();
    toast(e.message);
  }
}

function planHTML(data) {
  const { project: p, plan } = data;
  const totalMinutes = plan.steps.reduce((s, st) => s + st.minutes, 0);
  const maxHours = Math.max(plan.revival_hours, plan.restart_hours, 1);
  const difficultyClass = { Easy: "badge-easy", Moderate: "badge-moderate", Herculean: "badge-herculean" }[plan.difficulty] || "";
  const modeBadge = plan.mode === "llm"
    ? `<span class="badge badge-llm">✦ Gemma · local</span>`
    : `<span class="badge">Demo mode · rule-based</span>`;

  const unfinished = plan.unfinished_business.length
    ? `<div class="plan-section"><h4>Unfinished business</h4>
       <ul class="unfinished">${plan.unfinished_business.map((u) => `<li>${esc(u)}</li>`).join("")}</ul></div>`
    : "";

  return `
  <div class="plan-head">
    <div>
      <h3 class="plan-title" id="modalTitle">⚰️ ${esc(p.name)}</h3>
      <div class="badges">
        <span class="badge ${difficultyClass}">${esc(plan.difficulty)} resurrection</span>
        ${modeBadge}
        <span class="badge">dead ${plural(p.days_dead, "day")}</span>
        <span class="badge">${esc(p.primary_language)}</span>
      </div>
    </div>
  </div>

  <div class="plan-section"><h4>Cause of death</h4>
    <p class="cause">${esc(plan.cause_of_death)}</p></div>

  <div class="plan-section"><h4>Autopsy</h4>
    <p class="plan-summary">${esc(plan.autopsy_summary)}</p></div>

  ${unfinished}

  <div class="plan-section"><h4>The resurrection plan — laziest path back</h4>
    <ol class="steps">
      ${plan.steps.map((s) => `<li><span class="step-text">${esc(s.step)}</span><span class="step-min">${s.minutes} min</span></li>`).join("")}
    </ol>
    <p class="steps-total">First session ≈ ${totalMinutes} minutes of small steps. Momentum beats ambition.</p>
  </div>

  <div class="plan-section"><h4>The lazy payoff</h4>
    <div class="payoff">
      <div class="payoff-row"><span class="payoff-label">Revive this repo</span>
        <div class="payoff-track"><div class="payoff-fill fill-revival" data-w="${(plan.revival_hours / maxHours) * 100}"></div></div>
        <span class="payoff-hours">${plan.revival_hours.toFixed(1)}h</span></div>
      <div class="payoff-row"><span class="payoff-label">Start from scratch</span>
        <div class="payoff-track"><div class="payoff-fill fill-restart" data-w="${(plan.restart_hours / maxHours) * 100}"></div></div>
        <span class="payoff-hours">${plan.restart_hours.toFixed(1)}h</span></div>
      <p class="payoff-saved">Reviving saves you ≈ ${data.hours_saved.toFixed(1)} hours</p>
    </div>
  </div>

  <div class="plan-actions">
    <button class="btn-ghost" id="rerunBtn">↻ Re-run necromancy</button>
    <button class="btn-ghost" id="doneBtn">Back to the graveyard</button>
  </div>`;
}

function animatePayoff() {
  requestAnimationFrame(() => {
    setTimeout(() => {
      document.querySelectorAll(".payoff-fill").forEach((el) => {
        el.style.width = `${el.dataset.w}%`;
      });
    }, 60);
  });
}

function wirePlanActions(path) {
  const done = $("doneBtn");
  if (done) done.addEventListener("click", closeModal);
  const rerun = $("rerunBtn");
  if (rerun) rerun.addEventListener("click", () => openPlan(path, true));
}

/* ---------------- wiring ---------------- */

document.addEventListener("DOMContentLoaded", async () => {
  $("scanBtn").addEventListener("click", doScan);
  $("scanPath").addEventListener("keydown", (e) => { if (e.key === "Enter") doScan(); });
  $("sortSelect").addEventListener("change", renderResults);
  $("modalClose").addEventListener("click", closeModal);
  $("modalBackdrop").addEventListener("click", (e) => { if (e.target === $("modalBackdrop")) closeModal(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  const health = await loadHealth();
  if (health && health.default_scan_path) {
    $("scanPath").value = health.default_scan_path;
    doScan();
  }
});
