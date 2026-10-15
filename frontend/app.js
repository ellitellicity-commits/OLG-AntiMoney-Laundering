/* Player Risk Review dashboard: plain JS, no framework.
 *
 * Two views: the alert queue with a tabbed detail panel (Overview, Evidence, Activity,
 * Network, Ask AI), and an Overview screen (queue-wide counts, compliance indicators,
 * emerging-risk trends, the watchlist, the AI model and the audit trail).
 *
 * Data comes from the FastAPI service (backend/app/main.py). If the API cannot be
 * reached, the dashboard falls back to the hand-written frontend/mock/alerts.json.
 * Override the API location with ?api=http://host:port
 */
"use strict";

(() => {
  const params = new URLSearchParams(location.search);
  // Served by the API at /app/ -> same origin. Opened as a file or from another server -> local API.
  const API = params.get("api") ??
    (location.protocol.startsWith("http") && location.pathname.startsWith("/app") ? "" : "http://127.0.0.1:8000");

  const ONTARIO = new Set(["Toronto", "Ottawa", "Hamilton-Niagara", "Southwestern ON", "Eastern ON", "Northern ON"]);
  const BAND_RANK = { Low: 0, Medium: 1, High: 2, Critical: 3 };
  const BAND_FILL = { Low: "#E4E6E9", Medium: "#E8B84A", High: "#B4500F", Critical: "#8E1B1B" };
  const STATUS_FOR = { accept: "In review", escalate: "Escalated", close: "Closed", assign: "In review" };
  const TEAMS = ["AML", "Fraud", "Safer Gambling"];
  const CONFIDENCE = ["High", "Medium", "Low"];
  const DECISION_LABEL = { accept: "Accepted recommendation", escalate: "Escalated", close: "Closed as explained", assign: "Assigned" };
  const TABS = [["overview", "Overview"], ["evidence", "Evidence"], ["activity", "Activity"], ["network", "Network"],
                ["ask", "Ask AI"]];
  const TOP_REASONS = 3;
  const NAME_KEY = "olg.investigator";

  // How to label the comparison values of each reason code.
  const CMP = {
    INCOME_MISMATCH: { unit: "money", base: "own baseline per 30 days", peer: "peer median" },
    OCCUPATION_INCOME_MISMATCH: { unit: "money", base: "own baseline per 30 days", peer: "peer median deposits" },
    CASH_IN_CASH_OUT: { unit: "money", base: "own baseline deposits per 30 days" },
    PEER_DEPOSITS: { unit: "money", base: "own baseline per 30 days", peer: "peer median" },
    PEER_STAKE: { unit: "money", base: "own baseline", peer: "peer median" },
    PEER_BET_FREQUENCY: { unit: "number", base: "own baseline", peer: "peer median" },
    PEER_NET_LOSS: { unit: "money", base: "own baseline per 30 days", peer: "peer median" },
    BEHAVIOUR_PEER_DEPOSITS: { unit: "money", base: "own baseline per 30 days", peer: "behaviour-group median" },
    BEHAVIOUR_PEER_STAKE: { unit: "money", base: "own baseline", peer: "behaviour-group median" },
    IMPOSSIBLE_TRAVEL: { unit: "int", base: "own baseline events" },
    OUT_OF_PROVINCE: { unit: "int", peer: "peer median distinct locations" },
    NEW_DEVICE_OUTSIDE_ONTARIO: { unit: "int", base: "own baseline new devices" },
    DEPOSIT_SURGE: { unit: "money", base: "own baseline per 30 days", peer: "peer median" },
    STAKE_ESCALATION: { unit: "money", base: "own baseline", peer: "peer median" },
    NIGHT_PLAY_SHIFT: { unit: "percent", base: "own baseline", peer: "peer median" },
    LOSS_CHASING: { unit: "money", base: "own baseline per 30 days", peer: "peer median" },
    LINKED_PLAYERS: { unit: "int", peer: "peer median linked accounts" },
    STRUCTURING: { unit: "money", base: "own baseline deposits per 30 days", peer: "peer median deposits" },
    LARGE_TRANSACTION_24H: { unit: "money", base: "own baseline deposits per 30 days" },
    LOW_ODDS_BETTING: { unit: "percent", peer: "typical share" },
    RAPID_CASH_OUT: { unit: "money", base: "own baseline deposits per 30 days" },
    DORMANT_REACTIVATION: { unit: "money", base: "own baseline deposits per 30 days" },
    KYC_UNVERIFIED: { unit: "money", base: "own baseline deposits per 30 days" },
    PEP_EDD: { unit: "money", base: "own baseline deposits per 30 days" },
  };

  const ASK_SUGGESTIONS = ["Why was this player flagged?", "How does this compare with similar players?",
                           "What should I check next?"];

  const state = {
    alerts: [], view: [], selected: 0, openId: null, openAlert: null, detail: null,
    sort: { key: "score", dir: "desc" }, mock: false, mockAlerts: {}, mockDecisions: {},
    meta: null, token: 0, minScore: null, askHistory: [], flaggedOnly: false, tab: "overview",
    includeWatchlist: false, screen: "queue",
  };

  // --- Helpers ------------------------------------------------------------------------

  const $ = (sel, el = document) => el.querySelector(sel);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const cad = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });
  const fmt = {
    money: (v) => (v == null ? "n/a" : cad.format(v)),
    number: (v) => (v == null ? "n/a" : Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2)),
    int: (v) => (v == null ? "n/a" : Math.round(v).toLocaleString("en-CA")),
    percent: (v) => (v == null ? "n/a" : `${Math.round(v * 100)}%`),
  };
  const pctText = (p) => (p == null ? "n/a" : p > 0.99 ? "over 99%" : `${Math.round(p * 100)}%`);

  async function api(path, opts = {}) {
    const res = await fetch(API + path, { headers: { "content-type": "application/json" }, ...opts });
    if (!res.ok) {
      let msg = `${res.status} ${res.statusText}`;
      try { msg = (await res.json()).detail || msg; } catch { /* not JSON */ }
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return res.json();
  }

  function badge(score, band, large = false) {
    const on = BAND_RANK[band] + 1;
    const segs = [0, 1, 2, 3].map((i) => `<i class="${i < on ? "on" : ""}"></i>`).join("");
    return `<span class="risk${large ? " large" : ""}" data-band="${esc(band)}" role="img"
      aria-label="Risk score ${score} out of 100, ${esc(band)}"><span class="risk-score" aria-hidden="true">${score}</span><span
      class="risk-label" aria-hidden="true">${esc(band.toUpperCase())}</span><span class="risk-meter" aria-hidden="true">${segs}</span></span>`;
  }

  const statusTag = (s) => `<span class="tag tag-status" data-status="${esc(s)}">${esc(s)}</span>`;
  const confTag = (c) => (c ? `<span class="conf" data-level="${esc(c)}">${esc(c)} confidence</span>` : "");

  function accountAge(signup, end) {
    const days = (new Date(end) - new Date(signup)) / 86400000;
    if (!isFinite(days)) return "n/a";
    return days >= 365 ? `${(days / 365).toFixed(1)} years` : `${Math.max(1, Math.round(days / 30))} months`;
  }

  function showBanner(text) {
    const b = $("#banner");
    b.textContent = text;
    b.hidden = false;
  }

  const store = {  // localStorage can be unavailable (private windows, blocked storage)
    get(k) { try { return localStorage.getItem(k) || ""; } catch { return ""; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* not persisted */ } },
  };

  // --- Loading --------------------------------------------------------------------------

  function summaryFromFull(a) {
    return {
      alert_id: a.alert_id, player_id: a.player_id, score: a.score, band: a.band, team: a.team,
      status: a.status, anomaly_types: a.anomaly_types, anomaly_type_labels: a.anomaly_type_labels,
      top_reason: a.top_reason, recommended_action: a.recommended_action.action, last_activity: a.last_activity,
      points_total: a.points_total ?? a.score, confidence: a.confidence?.level ?? null, kind: "alert",
      ml_probability: a.ml?.probability ?? null,
    };
  }

  async function init() {
    renderQueueSkeleton();
    $("#investigator").value = store.get(NAME_KEY);
    try {
      const [meta, list] = await Promise.all([api("/meta"), api("/alerts?limit=5000&include_watchlist=true")]);
      state.meta = meta;
      state.alerts = list.alerts;
      $("#window-label").textContent =
        `Activity ${meta.window_start} to ${meta.window_end} · ${meta.players.toLocaleString("en-CA")} players scored`;
    } catch (err) {
      try {
        const res = await fetch("mock/alerts.json");
        if (!res.ok) throw new Error(res.statusText);
        const mock = await res.json();
        state.mock = true;
        state.mockAlerts = Object.fromEntries(mock.alerts.map((a) => [a.alert_id, a]));
        state.alerts = mock.alerts.map(summaryFromFull);
        const types = {};
        mock.alerts.forEach((a) => a.anomaly_types.forEach((t, i) => { types[t] = a.anomaly_type_labels[i]; }));
        state.meta = { bands: Object.keys(BAND_RANK), teams: TEAMS, anomaly_types: types,
                       statuses: ["New", "In review", "Escalated", "Closed"], watchlist: 0 };
        showBanner(`API not reachable at ${API || location.origin} (${err.message}). Showing hand-written mock data ` +
                   "from frontend/mock/alerts.json. Decisions are not saved. Start the API with: " +
                   "uvicorn backend.app.main:app");
      } catch {
        renderQueueError(err);
        return;
      }
    }
    fillFilters();
    $("#ai-search").hidden = state.mock;
    $("#nav-overview").hidden = state.mock;
    $("#watchlist-label").textContent = `Include watchlist (${state.meta.watchlist || 0} below the alert line)`;
    if (!state.mock) {
      renderAiStatus();
      setInterval(refreshAiStatus, 30000); // picks up Ollama starting (or stopping) without a reload
    }
    applyView();
    if (state.view.length) selectRow(0, true);
  }

  const aiLabel = (ai) => (ai?.available ? `AI: ${ai.provider} ${ai.model}${ai.local ? " (local)" : ""}` : "");

  function renderAiStatus() {
    const ai = state.meta.ai, el = $("#ai-status");
    el.hidden = false;
    el.dataset.on = String(!!ai?.available);
    el.textContent = ai?.available ? `AI assistant on · ${ai.model}${ai.local ? " (local)" : ""}` : "AI assistant offline";
    el.title = ai?.available ? `Provider: ${ai.provider}` : (ai?.how_to_enable || "");
    const askNote = $("#ask-status");
    if (askNote) askNote.textContent = askStatusText();
  }

  async function refreshAiStatus() {
    try {
      const ai = await api("/ai/status");
      const changed = ai.available !== state.meta.ai?.available || ai.model !== state.meta.ai?.model;
      state.meta.ai = ai;
      if (changed) renderAiStatus();
    } catch { /* API briefly unreachable: keep the last status */ }
  }

  function fillFilters() {
    const add = (id, entries) => {
      const sel = $(id);
      entries.forEach(([value, label]) => sel.insertAdjacentHTML("beforeend",
        `<option value="${esc(value)}">${esc(label)}</option>`));
    };
    add("#f-band", [...state.meta.bands].reverse().map((b) => [b, b]));
    add("#f-team", state.meta.teams.map((t) => [t, t]));
    add("#f-type", Object.entries(state.meta.anomaly_types).sort((a, b) => a[1].localeCompare(b[1])));
    add("#f-status", state.meta.statuses.map((s) => [s, s]));
    add("#f-confidence", CONFIDENCE.map((c) => [c, c]));
  }

  // --- Queue ------------------------------------------------------------------------------

  const SORTERS = {
    score: (a) => a.score,
    ai: (a) => a.ml_probability ?? 0,
    player_id: (a) => a.player_id,
    top_reason: (a) => a.top_reason.title,
    team: (a) => a.team,
    last_activity: (a) => a.last_activity || "",
    status: (a) => a.status,
  };

  // Equal scores: more total points first, then the AI model's probability, then most recent activity.
  function priorityCompare(a, b) {
    return (b.points_total ?? 0) - (a.points_total ?? 0) || (b.ml_probability ?? 0) - (a.ml_probability ?? 0) ||
      (b.last_activity || "").localeCompare(a.last_activity || "");
  }

  function applyView() {
    const band = $("#f-band").value, team = $("#f-team").value, type = $("#f-type").value;
    const status = $("#f-status").value, conf = $("#f-confidence").value;
    const q = $("#f-search").value.trim().toUpperCase();
    const keep = state.view[state.selected]?.alert_id;
    const { key, dir } = state.sort;
    const sign = dir === "asc" ? 1 : -1;
    state.view = state.alerts
      .filter((a) => (state.includeWatchlist || a.kind !== "watchlist") &&
        (!band || a.band === band) && (!team || a.team === team) &&
        (!type || a.anomaly_types.includes(type)) && (!status || a.status === status) &&
        (!conf || a.confidence === conf) &&
        (state.minScore == null || a.score >= state.minScore) &&
        (!q || a.player_id.includes(q) || a.alert_id.includes(q)))
      .sort((a, b) => {
        const x = SORTERS[key](a), y = SORTERS[key](b);
        if (x < y) return -sign;
        if (x > y) return sign;
        return (key === "score" ? 0 : b.score - a.score) || priorityCompare(a, b) || a.player_id.localeCompare(b.player_id);
      });
    const idx = state.view.findIndex((a) => a.alert_id === keep);
    state.selected = idx >= 0 ? idx : 0;
    renderQueue();
  }

  function renderQueue() {
    const body = $("#queue-body");
    const total = state.alerts.filter((a) => state.includeWatchlist || a.kind !== "watchlist").length;
    $("#queue-count").textContent = `${state.view.length} of ${total} ${state.includeWatchlist ? "alerts + watchlist" : "alerts"}` +
      (state.minScore != null ? ` · score ${state.minScore}+` : "");
    if (!state.view.length) {
      body.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p><strong>No alerts match these filters.</strong></p>
        <p class="muted">Clear a filter or the search to see more.</p></div></td></tr>`;
      return;
    }
    body.innerHTML = state.view.map((a, i) => `
      <tr id="row-${esc(a.alert_id)}" data-index="${i}" tabindex="${i === state.selected ? 0 : -1}"
          aria-selected="${i === state.selected}" class="${a.alert_id === state.openId ? "is-open" : ""}">
        <td>${badge(a.score, a.band)}<div class="row-sub">${a.kind === "watchlist"
          ? `<span class="tag tag-watch">Watchlist</span>` : confTag(a.confidence)}</div></td>
        <td class="nowrap"><div class="mono pid">${esc(a.player_id)}</div><div class="mono date muted">${a.last_activity
          ? esc(a.last_activity) : "n/a"}</div></td>
        <td class="reason-cell"><div>${esc(a.top_reason.title)}</div>${typeTags(a.anomaly_type_labels)}</td>
        <td>${esc(a.team)}</td>
        <td>${statusTag(a.status)}</td>
      </tr>`).join("");
  }

  function typeTags(labels) {
    const shown = labels.slice(0, 2).map((t) => `<span class="tag tag-type">${esc(t)}</span>`).join("");
    const rest = labels.slice(2);
    return `<div class="types">${shown}${rest.length
      ? `<span class="more" title="${esc(rest.join(", "))}">+${rest.length} more<span class="visually-hidden">: ${esc(rest.join(", "))}</span></span>`
      : ""}</div>`;
  }

  function renderQueueSkeleton() {
    $("#queue-body").innerHTML = Array.from({ length: 8 }, () =>
      `<tr class="skeleton" aria-hidden="true">${"<td></td>".repeat(5)}</tr>`).join("");
    $("#queue-count").textContent = "Loading alerts…";
  }

  function renderQueueError(err) {
    $("#queue-count").textContent = "";
    $("#queue-body").innerHTML = `<tr><td colspan="5"><div class="error-state" role="alert">
      <p><strong>Could not load alerts.</strong></p><p class="muted">${esc(err.message)}</p>
      <button type="button" class="btn" id="retry">Retry</button></div></td></tr>`;
    $("#retry").addEventListener("click", init);
  }

  function selectRow(i, focus) {
    if (!state.view.length) return;
    i = Math.max(0, Math.min(state.view.length - 1, i));
    const rows = $("#queue-body").rows;
    rows[state.selected]?.setAttribute("aria-selected", "false");
    rows[state.selected]?.setAttribute("tabindex", "-1");
    state.selected = i;
    const row = rows[i];
    row.setAttribute("aria-selected", "true");
    row.setAttribute("tabindex", "0");
    row.scrollIntoView({ block: "nearest" });
    if (focus) row.focus({ preventScroll: true });
  }

  function focusQueue() {
    $("#queue-body").rows[state.selected]?.focus();
  }

  // --- Detail -------------------------------------------------------------------------------

  async function openAlert(alertId, message) {
    const summary = state.alerts.find((a) => a.alert_id === alertId);
    if (!summary) return;
    state.openId = alertId;
    document.querySelectorAll("#queue-body tr.is-open").forEach((r) => r.classList.remove("is-open"));
    document.getElementById(`row-${alertId}`)?.classList.add("is-open");
    const token = ++state.token;
    const detail = $("#detail");
    if (!message) {
      detail.innerHTML = `<div class="empty-state" role="status"><p>Loading ${esc(summary.player_id)}…</p></div>`;
    }
    try {
      let alert, peers = null, player = null, network = null, timeline = null;
      if (!message) { state.askHistory = []; state.flaggedOnly = false; state.tab = "overview"; }
      if (state.mock) {
        const m = state.mockAlerts[alertId];
        alert = { ...m, ...summary, recommended_action: m.recommended_action,
                  decisions: state.mockDecisions[alertId] || [] };
        if (m.peers) peers = { metrics: m.peers, peer_group: m.peer_group, peer_group_level: m.peer_group_level,
                               peer_group_size: m.peer_group_size };
      } else {
        const pid = encodeURIComponent(summary.player_id);
        [alert, peers, player, network, timeline] = await Promise.all([
          api(`/alerts/${encodeURIComponent(alertId)}`), api(`/players/${pid}/peers`),
          api(`/players/${pid}?limit=25&flagged_only=${state.flaggedOnly}`), api(`/players/${pid}/network`),
          api(`/players/${pid}/timeline`),
        ]);
      }
      if (token !== state.token) return; // a newer alert was opened meanwhile
      state.openAlert = alert;
      state.detail = { alert, peers, player, network, timeline };
      renderDetail(message);
      if (!state.mock) loadSummary(alert.alert_id, token);
    } catch (err) {
      if (token !== state.token) return;
      detail.innerHTML = `<div class="error-state" role="alert"><p><strong>Could not load ${esc(summary.player_id)}.</strong></p>
        <p class="muted">${esc(err.message)}</p><button type="button" class="btn" id="retry-detail">Retry</button></div>`;
      $("#retry-detail").addEventListener("click", () => openAlert(alertId));
    }
  }

  function renderDetail(message) {
    const { alert: a, peers, player, network, timeline } = state.detail;
    const end = a.window?.end_date;
    const p = a.profile;
    const tabs = TABS.filter(([id]) => !(state.mock && (id === "ask" || id === "network" || id === "activity")));
    if (!tabs.some(([id]) => id === state.tab)) state.tab = "overview";
    const compliance = [
      p.kyc_status && p.kyc_status !== "verified" ? `<span class="tag tag-flag-strong">Identity ${esc(p.kyc_status)}</span>` : "",
      p.pep ? `<span class="tag tag-flag-strong">PEP</span>` : "",
      p.sanctions_screening && p.sanctions_screening !== "clear" ? `<span class="tag tag-flag-strong">Sanctions: ${esc(p.sanctions_screening)}</span>` : "",
      a.kind === "watchlist" ? `<span class="tag tag-watch">Watchlist: below the alert line</span>` : "",
    ].join("");
    const panels = {
      overview: () => overviewTab(a, player),
      evidence: () => evidenceTab(a, peers),
      activity: () => `${timeline ? timelineSection(timeline) : ""}${player ? activitySection(player) : ""}`,
      network: () => (network ? networkSection(network) : ""),
      ask: () => askSection(),
    };
    $("#detail").innerHTML = `
      <div class="detail-scroll"><div class="detail-body">
        <header class="player-head">
          <div>
            <h2 id="detail-title"><span class="mono">${esc(a.player_id)}</span>
              <span class="tag tag-synthetic">SYNTHETIC</span></h2>
            <div class="muted">${a.kind === "watchlist" ? "Watchlist entry" : "Alert"} <span class="mono">${esc(a.alert_id)}</span>
              · ${esc(a.team)} · ${statusTag(a.status)}</div>
            <ul class="profile">
              ${[["Age band", p.age_band], ["Occupation", p.occupation], ["Income band", `$${p.income_band}/yr`],
                 ["Home region", p.home_region], ["Account age", accountAge(p.signup_date, end)],
                 ["Peer group", `${a.peer_group} (${a.peer_group_size} players)`],
                 ...(a.behaviour_group ? [["Bets like", `${a.behaviour_group.name} (${a.behaviour_group.size})`]] : [])]
                .map(([k, v]) => `<li><span class="label">${k}</span><span class="v">${esc(v)}</span></li>`).join("")}
            </ul>
            ${compliance ? `<div class="compliance">${compliance}</div>` : ""}
          </div>
          <div class="head-side">
            ${badge(a.score, a.band, true)}
            ${confTag(a.confidence?.level)}
            ${state.mock ? "" : `<a class="btn" href="${esc(API)}/alerts/${encodeURIComponent(a.alert_id)}/report"
              target="_blank" rel="noopener">Case report</a>`}
          </div>
        </header>
        <div class="detail-tabs" role="tablist" aria-label="Alert sections">
          ${tabs.map(([id, label]) => `<button type="button" role="tab" id="tab-${id}" aria-controls="panel-${id}"
            aria-selected="${id === state.tab}" tabindex="${id === state.tab ? 0 : -1}" data-tab="${id}">${label}${
            id === "evidence" ? ` <span class="count">${a.reasons.length}</span>` : ""}</button>`).join("")}
        </div>
        ${tabs.map(([id]) => `<div class="tabpanel" role="tabpanel" id="panel-${id}" aria-labelledby="tab-${id}"
          ${id === state.tab ? "" : "hidden"}>${id === state.tab ? panels[id]() : ""}</div>`).join("")}
      </div></div>
      ${actionBar(a, message)}`;
    state.panels = panels;
    wireTabs();
    wireActionBar(a);
    wirePanel();
  }

  function wireTabs() {
    const tabs = [...document.querySelectorAll(".detail-tabs [role=tab]")];
    const show = (id, focus) => {
      state.tab = id;
      tabs.forEach((t) => {
        const on = t.dataset.tab === id;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        const panel = $(`#panel-${t.dataset.tab}`);
        panel.hidden = !on;
        if (on && !panel.innerHTML.trim()) panel.innerHTML = state.panels[id]();
        if (on && focus) t.focus();
      });
      wirePanel();
      if (id === "overview" && !state.mock) loadSummary(state.openAlert.alert_id, state.token);
    };
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => show(t.dataset.tab));
      t.addEventListener("keydown", (e) => {
        const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (!step) return;
        e.preventDefault();
        show(tabs[(i + step + tabs.length) % tabs.length].dataset.tab, true);
      });
    });
    state.showTab = show;
  }

  // Wire whatever controls the visible panel contains (safe to call repeatedly).
  function wirePanel() {
    const panel = $(`#panel-${state.tab}`);
    if (!panel || panel.dataset.wired) return;
    panel.dataset.wired = "1";
    panel.querySelectorAll("[data-open-alert]").forEach((el) => {
      el.addEventListener("click", () => openLinked(el.dataset.openAlert));
      el.addEventListener("keydown", (e) => { if (e.key === "Enter") openLinked(el.dataset.openAlert); });
    });
    panel.querySelectorAll("[data-goto-tab]").forEach((el) => el.addEventListener("click", () => state.showTab(el.dataset.gotoTab, true)));
    if (state.tab === "ask") wireAsk(state.openAlert);
    if (state.tab === "activity") $("#flagged-toggle")?.addEventListener("click", toggleFlagged);
  }

  // --- Overview tab: everything needed to decide most alerts -----------------------------

  function overviewTab(a, player) {
    const top = a.reasons.slice(0, TOP_REASONS);
    const more = a.reasons.length - top.length;
    return `
      ${state.mock ? "" : summarySection()}
      ${player ? keyFacts(player.summary) : ""}
      ${confidenceSection(a)}
      <section class="section" aria-labelledby="top-h">
        <div class="section-head"><h3 id="top-h">Strongest reasons</h3>
          <span class="score-sum muted">${scoreLine(a)}</span></div>
        <ol class="reasons">${top.map(reasonItem).join("")}</ol>
        ${more > 0 ? `<button type="button" class="btn-link see-all" data-goto-tab="evidence">See all ${a.reasons.length} reasons,
          the peer comparison and the behaviour group →</button>` : ""}
      </section>`;
  }

  function scoreLine(a) {
    return `Points <span class="num">${a.points_total}</span> → score <span class="num">${a.score}</span>`;
  }

  function keyFacts(s) {
    const facts = [
      ["30-day deposits", fmt.money(s.deposits_30d)], ["vs own 90-day baseline", fmt.money(s.deposits_base_30d) + " / 30 days"],
      ["Deposits vs income", s.deposit_income_ratio == null ? "n/a" : `${s.deposit_income_ratio.toFixed(1)}x`],
      ["Withdrawn (30 days)", fmt.money(s.withdrawals_30d)], ["Amount bet (30 days)", fmt.money(s.turnover_30d)],
      ["Net loss (30 days)", fmt.money(s.net_loss_30d)], ["Distinct locations", fmt.int(s.distinct_ip_regions_30d)],
      ["Linked accounts", fmt.int(Math.max(0, (s.network_cluster_size ?? 1) - 1))],
    ];
    return `<section class="section" aria-labelledby="facts-h"><h3 id="facts-h" class="visually-hidden">Key facts</h3>
      <dl class="keyfacts">${facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd class="num">${esc(v)}</dd></div>`).join("")}</dl>
    </section>`;
  }

  function confidenceSection(a) {
    if (!a.confidence) return "";
    const m = a.mitigating || [];
    return `<section class="section confidence" data-level="${esc(a.confidence.level)}" aria-labelledby="conf-h">
      <div class="section-head"><h3 id="conf-h">Does this truly warrant investigation?</h3>${confTag(a.confidence.level)}</div>
      <p class="muted">${esc(a.confidence.basis)}</p>
      ${m.length ? `<p class="label">Reasons it may be innocent</p><ul class="mitigating">${m.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`
        : `<p>No mitigating factors found in the data.</p>`}
    </section>`;
  }

  // --- Evidence tab -------------------------------------------------------------------------

  function evidenceTab(a, peers) {
    return `
      <section class="section" aria-labelledby="why-h">
        <div class="section-head">
          <h3 id="why-h">Why flagged</h3>
          <span class="score-sum muted">${scoreLine(a)}</span>
        </div>
        <p class="muted small">Points count one-for-one up to 70, then progressively less, so strong cases stay ranked
          instead of all reading 100. Within one anomaly type the strongest flag counts in full and the others at half.</p>
        <ol class="reasons">${a.reasons.map(reasonItem).join("")}</ol>
      </section>
      <section class="section peer-chart" aria-labelledby="peer-h">
        <div class="section-head">
          <h3 id="peer-h">Peer comparison</h3>
          <span class="muted">${peers ? `${esc(peers.peer_group)} · ${esc(peers.peer_group_level)} · ${peers.peer_group_size} players` : ""}</span>
        </div>
        ${peers ? peerChart(peers.metrics) : `<p class="muted">Peer data is not available in mock mode for this alert.</p>`}
      </section>
      ${peers?.behaviour_group ? behaviourSection(peers.behaviour_group) : ""}`;
  }

  function behaviourSection(bg) {
    return `<section class="section" aria-labelledby="bg-h">
      <div class="section-head"><h3 id="bg-h">Players who usually bet like them</h3>
        <span class="muted">${esc(bg.name)} · ${bg.size.toLocaleString("en-CA")} players (machine-learning grouping)</span></div>
      <table class="mini-table"><thead><tr><th>Metric</th><th class="right">Last 30 days</th><th class="right">Group median</th>
        <th class="right">z</th></tr></thead><tbody>${bg.metrics.map((m) => `<tr><td>${esc(m.label)}</td>
        <td class="right num">${fmt.money(m.current)}</td><td class="right num">${fmt.money(m.median)}</td>
        <td class="right num">${m.z == null ? "n/a" : m.z.toFixed(1)}</td></tr>`).join("")}</tbody></table>
      <p class="muted small">Groups are found by k-means clustering on how players bet over the previous 90 days, so a
        player is compared with people who share their betting style, not only their demographics.</p>
    </section>`;
  }

  function reasonItem(r) {
    const c = CMP[r.code];
    const parts = [];
    if (c) {
      const f = fmt[c.unit];
      if (c.base && r.comparison.own_baseline != null) parts.push(`${c.base} <span class="num">${f(r.comparison.own_baseline)}</span>`);
      if (c.peer && r.comparison.peer_median != null) parts.push(`${c.peer} <span class="num">${f(r.comparison.peer_median)}</span>`);
    }
    const half = r.overlap_discounted && r.points_full != null
      ? `<div class="points-note">half of ${r.points_full}: overlaps a stronger ${esc(typeLabel(r.anomaly_type).toLowerCase())} flag</div>` : "";
    return `<li class="reason">
      <div class="reason-title">${esc(r.title)}</div>
      <div class="reason-points"><span class="num">+${r.points}</span> pts${half}</div>
      <div class="reason-detail">${esc(r.detail)}</div>
      <div class="reason-meta"><span class="tag tag-type">${esc(typeLabel(r.anomaly_type))}</span></div>
      ${parts.length ? `<div class="reason-compare">Compared with: ${parts.join(" · ")}</div>` : ""}
    </li>`;
  }

  const typeLabel = (t) => state.meta.anomaly_types[t] || t;

  // --- Peer chart (hand-built SVG) --------------------------------------------------------

  function peerChart(metrics) {
    const W = 720, labelW = 230, padR = 28, rowH = 72, x0 = labelW, x1 = W - padR;
    const H = metrics.length * rowH + 8;
    const tf = (unit) => (unit === "percent" ? (v) => v : (v) => Math.sign(v) * Math.log10(1 + Math.abs(v)));
    const summary = [];
    const rows = metrics.map((m, i) => {
      const f = fmt[m.unit], T = tf(m.unit), pr = m.peer;
      const vals = [pr.p05, pr.p95, pr.q1, pr.q3, pr.median, m.current, m.baseline].filter((v) => v != null);
      let lo = T(Math.min(0, ...vals)), hi = T(Math.max(...vals));
      if (m.unit === "percent") hi = Math.max(hi, 0.1);
      if (hi - lo < 1e-9) hi = lo + 1;
      const pad = (hi - lo) * 0.04;
      lo -= pad; hi += pad;
      const X = (v) => x0 + ((T(v) - lo) / (hi - lo)) * (x1 - x0);
      const y = i * rowH + 8, axis = y + 34;
      const anchor = (x) => (x > x1 - 50 ? "end" : x < x0 + 50 ? "start" : "middle");
      const xc = X(m.current), xb = m.baseline != null ? X(m.baseline) : null;
      summary.push(`${m.label}: last 30 days ${f(m.current)}, own baseline ${f(m.baseline)}, peer median ${f(pr.median)}`);
      return `
        <g>
          <text x="0" y="${y + 14}" font-weight="600">${esc(m.label)}${m.z != null ? `<tspan class="t-muted t-mono" font-weight="500"> z ${m.z.toFixed(1)}</tspan>` : ""}</text>
          <text x="0" y="${y + 32}" class="t-muted">Peer median <tspan class="t-mono">${esc(f(pr.median))}</tspan></text>
          <text x="0" y="${y + 48}" class="t-muted">Middle 50% <tspan class="t-mono">${esc(f(pr.q1))}–${esc(f(pr.q3))}</tspan></text>
          <text x="0" y="${y + 64}" class="t-muted">${pr.n} ${pr.active_only ? "active " : ""}peers</text>
          <line x1="${X(pr.p05)}" x2="${X(pr.p95)}" y1="${axis}" y2="${axis}" stroke="#A9A69D" stroke-width="2"/>
          <rect x="${X(pr.q1)}" y="${axis - 7}" width="${Math.max(2, X(pr.q3) - X(pr.q1))}" height="14" fill="#D5D3CC"/>
          <line x1="${X(pr.median)}" x2="${X(pr.median)}" y1="${axis - 11}" y2="${axis + 11}" stroke="#545A62" stroke-width="2"/>
          ${xb != null ? `<circle cx="${xb}" cy="${axis}" r="6" fill="#FFFFFF" stroke="#1A1D21" stroke-width="2"/>
            <text x="${xb}" y="${axis + 26}" text-anchor="${anchor(xb)}" class="t-mono">Baseline ${esc(f(m.baseline))}</text>` : ""}
          <circle cx="${xc}" cy="${axis}" r="6" fill="#1A1D21"/>
          <text x="${xc}" y="${axis - 16}" text-anchor="${anchor(xc)}" class="t-mono" font-weight="600">Now ${esc(f(m.current))}</text>
        </g>`;
    }).join("");
    return `
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`Peer comparison. ${summary.join(". ")}.`)}">${rows}</svg>
      <div class="legend">
        <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="#1A1D21"/></svg>Last 30 days</span>
        <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="#fff" stroke="#1A1D21" stroke-width="2"/></svg>Own 90-day baseline (per 30 days)</span>
        <span><svg width="22" height="14" aria-hidden="true"><rect x="0" y="2" width="22" height="10" fill="#D5D3CC"/><line x1="11" x2="11" y1="0" y2="14" stroke="#545A62" stroke-width="2"/></svg>Middle 50% of peers and median</span>
        <span><svg width="22" height="14" aria-hidden="true"><line x1="0" x2="22" y1="7" y2="7" stroke="#A9A69D" stroke-width="2"/></svg>Peers 5th–95th percentile</span>
        <span>Money and count scales are logarithmic.</span>
      </div>`;
  }

  // --- AI: case summary and Q&A ----------------------------------------------------------
  // The summary sits above the evidence and is never shown without it (DESIGN.md).

  function summarySection() {
    return `<section class="section ai-summary" aria-labelledby="sum-h" aria-busy="true" id="ai-summary">
      <div class="section-head"><h3 id="sum-h">Case summary</h3><span id="sum-actions"></span></div>
      <p class="summary-text" id="sum-text"><span class="skeleton-line"></span></p>
      <p class="muted summary-meta" id="sum-meta">Generating…</p>
      <p class="muted summary-note" id="sum-note" hidden></p>
    </section>`;
  }

  async function loadSummary(alertId, token, refresh = false) {
    const box = $("#ai-summary");
    if (!box || (box.getAttribute("aria-busy") === "false" && !refresh)) return;
    box.setAttribute("aria-busy", "true");
    $("#sum-meta").textContent = refresh ? "Regenerating…" : "Generating…";
    try {
      const s = await api(`/alerts/${encodeURIComponent(alertId)}/summary${refresh ? "?refresh=true" : ""}`);
      if (token !== state.token || !$("#ai-summary")) return;
      const how = s.source === "llm"
        ? `${s.label} · AI (${s.provider} ${s.model}) · numbers checked against the evidence`
        : `${s.label} · built-in template`;
      $("#sum-text").textContent = s.text;
      $("#sum-meta").textContent = how;
      $("#sum-actions").innerHTML = s.source === "llm"
        ? `<button type="button" class="btn-link" id="sum-refresh">Regenerate</button>` : "";
      $("#sum-note").hidden = !s.note;
      $("#sum-note").textContent = s.note || "";
      $("#sum-refresh")?.addEventListener("click", () => loadSummary(alertId, state.token, true));
    } catch (err) {
      if (token !== state.token || !$("#ai-summary")) return;
      $("#sum-text").textContent = "";
      $("#sum-meta").textContent = `Summary unavailable: ${err.message}`;
    } finally {
      $("#ai-summary")?.setAttribute("aria-busy", "false");
    }
  }

  function askStatusText() {
    const ai = state.meta?.ai;
    return ai?.available ? `${aiLabel(ai)} · answers use only this case's evidence`
      : "AI assistant offline: start Ollama, or add a free Groq / Gemini key (see README)";
  }

  function askSection() {
    return `<section class="section" aria-labelledby="ask-h">
      <div class="section-head"><h3 id="ask-h">Ask about this case</h3>
        <span class="muted" id="ask-status">${esc(askStatusText())}</span></div>
      <div class="ask-suggestions">${ASK_SUGGESTIONS.map((q) =>
        `<button type="button" class="tag ask-chip" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>
      <form class="ask-form" id="ask-form">
        <label class="visually-hidden" for="ask-q">Question about this case</label>
        <input id="ask-q" type="search" maxlength="1000" autocomplete="off"
               placeholder="e.g. What changed compared with this player's own history?">
        <button type="submit" class="btn">Ask</button>
      </form>
      <ol class="ask-log" id="ask-log" aria-live="polite">${state.askHistory.reduce((html, t, i, all) =>
        t.role === "user" ? html + `<li><div class="ask-q">${esc(t.content)}</div><div class="ask-a">${esc(all[i + 1]?.content || "")}</div></li>` : html, "")}</ol>
    </section>`;
  }

  function wireAsk(a) {
    const form = $("#ask-form");
    if (!form) return;
    const send = async (question) => {
      if (!question) return;
      const log = $("#ask-log");
      const item = document.createElement("li");
      item.innerHTML = `<div class="ask-q">${esc(question)}</div><div class="ask-a muted">Thinking…</div>`;
      log.append(item);
      $("#ask-q").value = "";
      form.querySelector("button").disabled = true;
      try {
        const res = await api(`/alerts/${encodeURIComponent(a.alert_id)}/ask`, {
          method: "POST", body: JSON.stringify({ question, history: state.askHistory }),
        });
        const warn = res.unverified_numbers?.length
          ? `<div class="ask-warn">Check: ${esc(res.unverified_numbers.join(", "))} not found in the evidence.</div>` : "";
        item.querySelector(".ask-a").outerHTML = `<div class="ask-a">${esc(res.answer)}</div>${warn}`;
        if (res.source === "llm") {
          state.askHistory.push({ role: "user", content: question }, { role: "assistant", content: res.answer });
        }
      } catch (err) {
        item.querySelector(".ask-a").textContent = `Not answered: ${err.message}`;
      } finally {
        form.querySelector("button").disabled = false;
      }
    };
    form.addEventListener("submit", (e) => { e.preventDefault(); send($("#ask-q").value.trim()); });
    $("#detail").querySelectorAll(".ask-chip").forEach((b) => b.addEventListener("click", () => send(b.dataset.q)));
  }

  // --- Activity: weekly timeline and transactions ------------------------------------------

  function toggleFlagged() {
    state.flaggedOnly = !state.flaggedOnly;
    reloadActivity(state.openAlert.player_id);
  }

  async function reloadActivity(playerId) {
    const token = state.token;
    try {
      const player = await api(`/players/${encodeURIComponent(playerId)}?limit=25&flagged_only=${state.flaggedOnly}`);
      if (token !== state.token) return;
      state.detail.player = player;
      $("#activity").outerHTML = activitySection(player);
      $("#flagged-toggle").addEventListener("click", toggleFlagged);
      $("#flagged-toggle").focus();
    } catch (err) {
      $("#activity .section-head .muted").textContent = `Could not reload: ${err.message}`;
    }
  }

  function timelineSection(tl) {
    const W = 720, labelW = 160, padR = 4, rowH = 58, n = tl.weeks.length;
    const bw = (W - labelW - padR) / n;
    const curFrom = new Date(tl.current_window_start), baseFrom = new Date(tl.baseline_start);
    const weekEnd = (w) => new Date(new Date(w.week_start).getTime() + 7 * 86400000);
    const zone = (w) => (weekEnd(w) > curFrom ? "cur" : weekEnd(w) > baseFrom ? "base" : "old");
    const fill = { cur: "#1A1D21", base: "#545A62", old: "#A9A69D" };
    const metrics = [["deposits", "Deposits"], ["turnover", "Amount bet"], ["net_loss", "Net loss"]];
    const sum = (k, z) => tl.weeks.filter((w) => zone(w) === z).reduce((s, w) => s + w[k], 0);
    const rows = metrics.map(([k, label], r) => {
      const vals = tl.weeks.map((w) => w[k]);
      const max = Math.max(1, ...vals.map(Math.abs)), neg = vals.some((v) => v < 0);
      const y0 = r * rowH + 6, h = rowH - 20, zero = neg ? y0 + h / 2 : y0 + h, sc = (neg ? h / 2 : h) / max;
      const bars = tl.weeks.map((w, i) => {
        const v = w[k], bh = Math.max(v ? 1 : 0, Math.abs(v) * sc);
        return `<rect x="${(labelW + i * bw + 1).toFixed(1)}" y="${(v >= 0 ? zero - bh : zero).toFixed(1)}"
          width="${(bw - 2).toFixed(1)}" height="${bh.toFixed(1)}" fill="${fill[zone(w)]}"><title>Week of ${esc(w.week_start)}: ${esc(fmt.money(v))}</title></rect>`;
      }).join("");
      return `<g><text x="0" y="${y0 + 14}" font-weight="600">${label}</text>
        <text x="0" y="${y0 + 30}" class="t-muted">Peak week <tspan class="t-mono">${esc(fmt.money(max))}</tspan></text>
        <line x1="${labelW}" x2="${W - padR}" y1="${zero}" y2="${zero}" stroke="#D5D3CC"/>${bars}</g>`;
    }).join("");
    const H = metrics.length * rowH + 18, firstCur = tl.weeks.findIndex((w) => zone(w) === "cur");
    const xCur = labelW + Math.max(0, firstCur) * bw;
    const desc = metrics.map(([k, label]) =>
      `${label}: last 30 days ${fmt.money(sum(k, "cur"))}, previous 90 days ${fmt.money(sum(k, "base"))}`).join(". ");
    return `<section class="section timeline" aria-labelledby="tl-h">
      <div class="section-head"><h3 id="tl-h">Activity over time</h3>
        <span class="muted">Weekly totals, ${esc(tl.weeks[0].week_start)} to ${esc(tl.weeks[n - 1].week_start)}</span></div>
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`Weekly activity. ${desc}.`)}">${rows}
        <line x1="${xCur}" x2="${xCur}" y1="0" y2="${H - 14}" stroke="#1F4E79" stroke-dasharray="3 3"/>
        <text x="${xCur + 4}" y="${H - 2}" class="t-muted">Last 30 days →</text></svg>
      <div class="legend">
        <span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" fill="#1A1D21"/></svg>Last 30 days</span>
        <span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" fill="#545A62"/></svg>90-day baseline</span>
        <span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" fill="#A9A69D"/></svg>Earlier</span>
      </div>
    </section>`;
  }

  function activitySection(player) {
    const labels = state.meta?.transaction_flags || {};
    const rows = player.transactions.map((t) => {
      const outside = !t.flags && t.ip_region && !ONTARIO.has(t.ip_region); // mock data has no flags
      const flags = (t.flags || []).map((f) => `<span class="tag tag-flag">${esc(labels[f] || f)}</span>`).join(" ");
      const bet = t.sport ? `${esc(t.sport)} · ${esc(t.market)} @ <span class="num">${t.odds.toFixed(2)}</span>` : "";
      return `<tr class="${flags ? "is-flagged" : ""}">
        <td class="mono">${esc(t.timestamp.slice(0, 16))}</td><td>${esc(t.type)}</td>
        <td class="right num">${fmt.money(t.amount_cad)}</td><td>${bet}</td><td>${esc(t.channel)}</td>
        <td>${esc(t.ip_region || "")}${outside ? ` <span class="flag-text">(outside Ontario)</span>` : ""}</td>
        <td class="flags-cell">${flags}</td>
        <td class="mono">${esc(t.device_id || "")}</td><td class="mono">${esc(t.payment_method_id || "")}</td></tr>`;
    }).join("");
    const what = state.flaggedOnly ? "flagged transactions" : "transactions";
    return `<section class="section" aria-labelledby="act-h" id="activity">
      <div class="section-head"><h3 id="act-h">Recent activity</h3>
        <span class="muted">Latest ${player.transactions.length} of ${player.transactions_total.toLocaleString("en-CA")} ${what}
          ${state.mock ? "" : ` · <button type="button" class="btn-link" id="flagged-toggle" aria-pressed="${state.flaggedOnly}">${
            state.flaggedOnly ? "Show all" : "Show flagged only"}</button>`}</span></div>
      <div class="table-wrap"><table class="mini-table">
        <thead><tr><th>Time</th><th>Type</th><th class="right">Amount</th><th>Bet</th><th>Channel</th><th>Location</th><th>Flags</th><th>Device</th><th>Payment method</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="9" class="muted">No ${what}.</td></tr>`}</tbody></table></div>
    </section>`;
  }

  // --- Network: graph + list ------------------------------------------------------------------

  function networkGraph(net) {
    const W = 720, H = 320, cx = W / 2, cy = H / 2, R = 120;
    const linked = net.linked_players.slice(0, 12);
    const self = state.openAlert;
    const pos = linked.map((_, i) => {
      const a = (2 * Math.PI * i) / Math.max(linked.length, 1) - Math.PI / 2;
      return [cx + R * 1.6 * Math.cos(a), cy + R * Math.sin(a)];
    });
    const short = { device: "device", payment_method: "card", address: "address" };
    const labels = linked.map((l) => [...new Set(l.shared.map((s) => short[s.identifier_type] || s.identifier_type))].sort().join(" + "));
    const same = labels.length && labels.every((x) => x === labels[0]);
    const edges = linked.map((l, i) => {
      const [x, y] = pos[i];
      // Label near the outer account (70% along the line) so labels don't pile up in the middle.
      const lx = cx + (x - cx) * 0.7, ly = cy + (y - cy) * 0.7;
      return `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#A9A69D" stroke-width="2"/>
        ${same ? "" : `<text x="${lx}" y="${ly - 6}" text-anchor="middle" class="t-muted edge-label">${esc(labels[i])}</text>`}`;
    }).join("");
    const node = (x, y, pid, score, band, alertId, isSelf) => {
      const canOpen = !isSelf && alertId && state.alerts.some((a) => a.alert_id === alertId);
      const dark = band === "High" || band === "Critical";
      return `<g class="node${canOpen ? " clickable" : ""}" ${canOpen ? `data-open-alert="${esc(alertId)}" tabindex="0" role="button"
        aria-label="Open ${esc(pid)}, score ${score}"` : ""}>
        <circle cx="${x}" cy="${y}" r="${isSelf ? 30 : 24}" fill="${BAND_FILL[band] || "#E4E6E9"}" stroke="#1A1D21"
          stroke-width="${isSelf ? 3 : 1}"/>
        <text x="${x}" y="${y + 4}" text-anchor="middle" class="t-mono" fill="${dark ? "#FFFFFF" : "#1A1D21"}">${score}</text>
        ${isSelf ? `<rect x="${x - 34}" y="${y + 33}" width="68" height="18" fill="#FFFFFF"/>` : ""}
        <text x="${x}" y="${y + (isSelf ? 46 : 40)}" text-anchor="middle" class="t-mono" font-weight="${isSelf ? 600 : 500}">${esc(pid)}</text></g>`;
    };
    return `<svg viewBox="0 0 ${W} ${H}" role="img" class="network-svg"
        aria-label="${esc(`Network: ${self.player_id} shares identifiers with ${linked.length} accounts.`)}">
      ${edges}${linked.map((l, i) => node(pos[i][0], pos[i][1], l.player_id, l.score, l.band, l.alert_id, false)).join("")}
      ${node(cx, cy, self.player_id, self.score, self.band, null, true)}</svg>
      <p class="muted small">${same ? `Every linked account shares: <strong>${esc(labels[0])}</strong>. ` : ""}Circles show each
        account's risk score (bold ring = this player); lines show shared identifiers. Click an account to open it.</p>`;
  }

  function networkSection(net) {
    const items = net.linked_players.map((l) => {
      const shared = l.shared.map((s) => `${s.identifier_type.replace("_", " ")} <span class="mono">${esc(s.identifier_value)}</span>`).join(", ");
      const canOpen = l.alert_id && state.alerts.some((a) => a.alert_id === l.alert_id);
      return `<li>${badge(l.score, l.band)} <span class="mono">${esc(l.player_id)}</span>
        <span class="muted">shares ${shared}</span>
        ${canOpen ? `<button type="button" class="btn-link" data-open-alert="${esc(l.alert_id)}">Open</button>` : ""}</li>`;
    }).join("");
    return `<section class="section" aria-labelledby="net-h">
      <div class="section-head"><h3 id="net-h">Linked players</h3>
        <span class="muted">Cluster <span class="mono">${esc(net.cluster_id)}</span> · ${net.cluster_size} account${net.cluster_size === 1 ? "" : "s"}</span></div>
      ${items ? `${networkGraph(net)}<ul class="linked">${items}</ul>`
              : `<p class="muted">No other account shares a device, payment method or address with this player.</p>`}
    </section>`;
  }

  function openLinked(alertId) {
    if (!state.alerts.some((a) => a.alert_id === alertId)) return;
    if (state.screen !== "queue") showScreen("queue");
    if (alertId.startsWith("WL-") && !state.includeWatchlist) {
      state.includeWatchlist = true;
      $("#f-watchlist").checked = true;
    }
    let idx = state.view.findIndex((a) => a.alert_id === alertId);
    if (idx < 0) { // filtered out: clear filters so the row is visible
      ["#f-band", "#f-team", "#f-type", "#f-status", "#f-confidence", "#f-search"].forEach((s) => { $(s).value = ""; });
      state.minScore = null;
      applyView();
      idx = state.view.findIndex((a) => a.alert_id === alertId);
    } else {
      applyView();
      idx = state.view.findIndex((a) => a.alert_id === alertId);
    }
    selectRow(idx, false);
    openAlert(alertId);
  }

  // --- Decisions -------------------------------------------------------------------------------

  function actionBar(a, message) {
    const rec = a.recommended_action;
    return `<div class="action-bar" role="region" aria-labelledby="rec-h">
      <div class="action-rec"><div>
        <div class="label" id="rec-h">Recommended action · ${esc(rec.team)}</div>
        <div class="what">${esc(rec.action)}</div>
        <div class="muted">${esc(rec.rationale)}</div>
      </div></div>
      <div class="buttons" id="decision-buttons">
        <button type="button" class="btn btn-primary" data-act="accept">Accept recommendation</button>
        <button type="button" class="btn" data-act="escalate">Escalate</button>
        <button type="button" class="btn" data-act="close" aria-expanded="false" aria-controls="close-form">Close as explained…</button>
        <button type="button" class="btn" data-act="assign" aria-expanded="false" aria-controls="assign-form">Assign to team…</button>
        <span class="decision-msg" id="decision-msg" role="status" aria-live="polite">${esc(message || "")}</span>
      </div>
      <form class="close-form" id="close-form" novalidate hidden>
        <label>Reason for closing (required)
          <textarea id="close-note" rows="1" maxlength="1000" required></textarea></label>
        <button type="submit" class="btn btn-primary">Close alert</button>
        <button type="button" class="btn" data-cancel>Cancel</button>
        <span class="form-error" role="alert"></span>
      </form>
      <form class="assign-form" id="assign-form" hidden>
        <label>Team
          <select id="assign-team">${TEAMS.map((t) => `<option ${t === a.team ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <label>Note (optional)
          <input type="search" id="assign-note" maxlength="1000"></label>
        <button type="submit" class="btn btn-primary">Assign</button>
        <button type="button" class="btn" data-cancel>Cancel</button>
      </form>
      ${historyLine(a)}
    </div>`;
  }

  function historyLine(a) {
    const d = a.decisions || [];
    if (!d.length) return `<p class="history-line muted">No decisions recorded yet.</p>`;
    const items = d.slice().reverse().map((x) => `<li><span class="mono">${esc(x.recorded_at)}</span> · ${esc(x.investigator || "name not recorded")}:
      ${esc(DECISION_LABEL[x.decision])}${x.team ? ` to ${esc(x.team)}` : ""} (${esc(x.status)})${x.note ? `. Note: ${esc(x.note)}` : ""}</li>`).join("");
    return `<details class="history-line"><summary>Decision history (${d.length})</summary><ol class="history">${items}</ol></details>`;
  }

  function wireActionBar(a) {
    const closeForm = $("#close-form"), assignForm = $("#assign-form");
    const toggle = (form, btn, show) => {
      form.hidden = !show;
      btn.setAttribute("aria-expanded", String(show));
      if (show) form.querySelector("textarea, select").focus();
    };
    const closeBtn = $('[data-act="close"]'), assignBtn = $('[data-act="assign"]');
    $('[data-act="accept"]').addEventListener("click", () => decide(a, { decision: "accept" }));
    $('[data-act="escalate"]').addEventListener("click", () => decide(a, { decision: "escalate" }));
    closeBtn.addEventListener("click", () => { toggle(assignForm, assignBtn, false); toggle(closeForm, closeBtn, closeForm.hidden); });
    assignBtn.addEventListener("click", () => { toggle(closeForm, closeBtn, false); toggle(assignForm, assignBtn, assignForm.hidden); });
    closeForm.querySelector("[data-cancel]").addEventListener("click", () => { toggle(closeForm, closeBtn, false); closeBtn.focus(); });
    assignForm.querySelector("[data-cancel]").addEventListener("click", () => { toggle(assignForm, assignBtn, false); assignBtn.focus(); });
    closeForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const note = $("#close-note").value.trim();
      if (!note) {
        closeForm.querySelector(".form-error").textContent = "Enter a reason before closing.";
        $("#close-note").focus();
        return;
      }
      decide(a, { decision: "close", note });
    });
    assignForm.addEventListener("submit", (e) => {
      e.preventDefault();
      decide(a, { decision: "assign", team: $("#assign-team").value, note: $("#assign-note").value.trim() });
    });
  }

  async function decide(a, body) {
    const investigator = $("#investigator").value.trim();
    if (!investigator && !state.mock) {
      $("#decision-msg").textContent = "Enter your name in the Investigator box (top right) first: every decision is recorded.";
      $("#investigator").focus();
      return;
    }
    const buttons = document.querySelectorAll(".action-bar button");
    buttons.forEach((b) => { b.disabled = true; });
    try {
      let res;
      if (state.mock) {
        const decision = { ...body, note: body.note || "", team: body.team || null, investigator,
          status: STATUS_FOR[body.decision], recorded_at: new Date().toISOString().slice(0, 19).replace("T", " ") + " UTC" };
        (state.mockDecisions[a.alert_id] ||= []).push(decision);
        res = { status: decision.status, team: body.team || a.team, decision };
      } else {
        res = await api(`/alerts/${encodeURIComponent(a.alert_id)}/decision`,
                        { method: "POST", body: JSON.stringify({ ...body, investigator }) });
      }
      const summary = state.alerts.find((x) => x.alert_id === a.alert_id);
      summary.status = res.status;
      summary.team = res.team;
      applyView();
      const msg = `Recorded: ${DECISION_LABEL[body.decision]}${body.team ? ` to ${body.team}` : ""}. Status is now ${res.status}.`;
      await openAlert(a.alert_id, msg);
      $('[data-act="accept"]')?.focus();
    } catch (err) {
      buttons.forEach((b) => { b.disabled = false; });
      $("#decision-msg").textContent = `Not saved: ${err.message}`;
    }
  }

  // --- Overview screen ---------------------------------------------------------------------

  function showScreen(name) {
    state.screen = name;
    $("#view-queue").hidden = name !== "queue";
    $("#view-overview").hidden = name !== "overview";
    $("#nav-queue").setAttribute("aria-pressed", String(name === "queue"));
    $("#nav-overview").setAttribute("aria-pressed", String(name === "overview"));
    if (name === "overview") renderOverview();
  }

  function bars(obj, order) {
    const entries = (order || Object.keys(obj)).filter((k) => obj[k] != null).map((k) => [k, obj[k]]);
    const max = Math.max(1, ...entries.map(([, v]) => v));
    return `<table class="bars">${entries.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th>
      <td><span class="bar" style="width:${(100 * v / max).toFixed(1)}%"></span></td><td class="num right">${v}</td></tr>`).join("")}</table>`;
  }

  function sparkline(series) {
    const W = 120, H = 26, max = Math.max(1, ...series);
    const pts = series.map((v, i) => `${(i * W / (series.length - 1)).toFixed(1)},${(H - 2 - (v / max) * (H - 4)).toFixed(1)}`).join(" ");
    const x4 = (W * (series.length - 4)) / (series.length - 1);
    return `<svg width="${W}" height="${H}" aria-hidden="true" class="spark"><rect x="${x4}" y="0" width="${W - x4}" height="${H}"
      fill="#EDECE7"/><polyline points="${pts}" fill="none" stroke="#1A1D21" stroke-width="1.5"/></svg>`;
  }

  // "×7" reads better than "+600%", and a flag that was near zero before is simply "new".
  function trendLabel(f) {
    if (f.change == null || f.earlier_weekly_avg < 1) {
      return f.recent_weekly_avg >= 3 ? `<span class="tag tag-rising">New this month</span>` : `<span class="muted">steady</span>`;
    }
    const ratio = f.recent_weekly_avg / f.earlier_weekly_avg;
    if (f.rising) return `<span class="tag tag-rising">Rising ×${ratio >= 10 ? Math.round(ratio) : ratio.toFixed(1)}</span>`;
    return `<span class="muted">${ratio >= 1 ? `×${ratio.toFixed(1)}` : `${Math.round((ratio - 1) * 100)}%`}</span>`;
  }

  async function renderOverview() {
    const root = $("#view-overview");
    root.innerHTML = `<div class="empty-state" role="status"><p>Loading overview…</p></div>`;
    try {
      const [st, wl, audit] = await Promise.all([api("/stats"), api("/watchlist"), api("/audit")]);
      const t = st.trends;
      const m = st.ai_model?.metrics, xs = st.ai_model?.cross_seed?.results || [];
      root.innerHTML = `
        <section class="panel ov-panel"><div class="panel-head"><h2>Queue at a glance</h2>
          <span class="muted">${st.alerts} alerts · ${st.watchlist} on the watchlist · ${st.players.toLocaleString("en-CA")} players</span></div>
          <div class="ov-body ov-cols">
            <div><h3>By risk band</h3>${bars(st.by_band, ["Critical", "High", "Medium"])}</div>
            <div><h3>By team</h3>${bars(st.by_team, TEAMS)}</div>
            <div><h3>By confidence</h3>${bars(st.by_confidence, CONFIDENCE)}</div>
            <div><h3>By status</h3>${bars(st.by_status)}</div>
          </div></section>

        <section class="panel ov-panel"><div class="panel-head"><h2>Regulatory compliance indicators</h2>
          <span class="muted">Alerts carrying each indicator (FINTRAC-style; indicators for review, not filings)</span></div>
          <div class="ov-body">${bars(st.compliance)}</div></section>

        <section class="panel ov-panel"><div class="panel-head"><h2>Emerging risk: transaction flags over time</h2>
          <span class="muted">Weekly counts, ${esc(t.weeks[0])} onward; shaded = last 4 weeks</span></div>
          <div class="ov-body"><table class="mini-table trends"><thead><tr><th>Flag</th><th>13 weeks</th>
            <th class="right">Last 4 weeks / wk</th><th class="right">Before / wk</th><th>Trend</th></tr></thead><tbody>
            ${t.flags.map((f) => `<tr><td>${esc(f.label)}</td><td>${sparkline(f.weekly)}</td>
              <td class="right num">${f.recent_weekly_avg}</td><td class="right num">${f.earlier_weekly_avg}</td>
              <td>${trendLabel(f)}</td></tr>`).join("")}
          </tbody></table></div></section>

        <section class="panel ov-panel"><div class="panel-head"><h2>Watchlist: unusual players below the alert line</h2>
          <span class="muted">Found by the AI models; no rule reached the alert threshold</span></div>
          <div class="ov-body">${wl.alerts.length ? `<table class="mini-table"><tbody>${wl.alerts.map((a) => `<tr>
            <td>${badge(a.score, a.band)}</td><td class="mono">${esc(a.player_id)}</td><td>${esc(a.top_reason.title)}</td>
            <td class="num">AI ${pctText(a.ml_probability)}</td>
            <td><button type="button" class="btn-link" data-open-alert="${esc(a.alert_id)}">Open</button></td></tr>`).join("")}
            </tbody></table>` : `<p class="muted">Nothing on the watchlist.</p>`}</div></section>

        <section class="panel ov-panel"><div class="panel-head"><h2>About the AI risk model</h2>
          <span class="muted">Gradient boosting + SHAP, scored out-of-fold</span></div>
          <div class="ov-body">${m ? `<dl class="keyfacts">
            <div><dt>ROC-AUC</dt><dd class="num">${m.roc_auc.toFixed(3)}</dd></div>
            <div><dt>Average precision</dt><dd class="num">${m.average_precision.toFixed(3)}</dd></div>
            <div><dt>Risky players caught at 50%</dt><dd class="num">${pctText(m["recall_at_0.5"])}</dd></div>
            <div><dt>Normal players above 50%</dt><dd class="num">${(m["false_positive_rate_at_0.5"] * 100).toFixed(2)}%</dd></div></dl>
            <p class="muted">Most influential: ${esc(st.ai_model.top_features.join(", "))}.</p>` : `<p class="muted">Model card unavailable.</p>`}
            ${xs.length ? `<h3>Tested on populations it never saw</h3><table class="mini-table"><thead><tr><th>Population</th>
              <th class="right">Risky caught</th><th class="right">Normal alerted</th><th class="right">Top-100 precision</th>
              <th class="right">AI ROC-AUC</th></tr></thead><tbody>${xs.map((x) => `<tr><td>Seed ${x.seed}</td>
              <td class="right num">${pctText(x.recall_all)}</td><td class="right num">${(x.false_positive_rate * 100).toFixed(2)}%</td>
              <td class="right num">${pctText(x.precision_at_100)}</td><td class="right num">${x.ml_roc_auc.toFixed(3)}</td></tr>`).join("")}
              </tbody></table>` : ""}</div></section>

        <section class="panel ov-panel"><div class="panel-head"><h2>Audit trail</h2>
          <a class="btn" href="${esc(API)}/audit.csv">Download CSV</a></div>
          <div class="ov-body">${audit.decisions.length ? `<table class="mini-table"><thead><tr><th>Recorded</th><th>Investigator</th>
            <th>Alert</th><th>Decision</th><th>Note</th></tr></thead><tbody>${audit.decisions.slice(0, 12).map((d) => `<tr>
            <td class="mono">${esc(d.recorded_at)}</td><td>${esc(d.investigator || "not recorded")}</td><td class="mono">${esc(d.alert_id)}</td>
            <td>${esc(DECISION_LABEL[d.decision] || d.decision)}</td><td>${esc(d.note || "")}</td></tr>`).join("")}</tbody></table>`
            : `<p class="muted">No decisions recorded yet.</p>`}</div></section>`;
      root.querySelectorAll("[data-open-alert]").forEach((b) => b.addEventListener("click", () => openLinked(b.dataset.openAlert)));
    } catch (err) {
      root.innerHTML = `<div class="error-state" role="alert"><p><strong>Could not load the overview.</strong></p>
        <p class="muted">${esc(err.message)}</p></div>`;
    }
  }

  // --- Plain-English queue search ------------------------------------------------------------

  function setSort(key, dir) {
    state.sort = { key, dir };
    document.querySelectorAll(".queue-table th[data-sort]").forEach((h) => {
      if (h.dataset.sort === key) h.setAttribute("aria-sort", dir === "asc" ? "ascending" : "descending");
      else h.removeAttribute("aria-sort");
    });
    // Keep the "Sort by" menu in step; column sorts with no menu entry show as "Custom".
    const sel = $("#f-sort"), value = `${key}:${dir}`;
    sel.value = [...sel.options].some((o) => o.value === value) ? value : "";
  }

  function clearAiFilter() {
    ["#f-band", "#f-team", "#f-type", "#f-status", "#f-confidence", "#f-search", "#ai-q"].forEach((s) => { $(s).value = ""; });
    state.minScore = null;
    setSort("score", "desc");
    $("#ai-search-result").textContent = "";
    applyView();
  }

  $("#ai-search").addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = $("#ai-q").value.trim(), out = $("#ai-search-result");
    if (!query) { clearAiFilter(); return; }
    out.textContent = "Searching…";
    try {
      const res = await api("/ai/search", { method: "POST", body: JSON.stringify({ query }) });
      const f = res.filters;
      $("#f-band").value = f.band || "";
      $("#f-team").value = f.team || "";
      $("#f-type").value = f.type || "";
      $("#f-status").value = f.status || "";
      $("#f-search").value = f.q || "";
      state.minScore = f.min_score ?? null;
      const [key, dir] = f.sort === "-last_activity" ? ["last_activity", "desc"]
        : f.sort === "player_id" ? ["player_id", "asc"] : ["score", "desc"];
      setSort(key, dir);
      applyView();
      const how = res.source === "llm" ? `AI: ${res.provider} ${res.model}` : "keyword match";
      out.innerHTML = `Showing ${state.view.length}: ${esc(res.explanation)} <span class="muted">(${esc(how)})</span>
        <button type="button" class="btn-link" id="ai-clear">Clear</button>`;
      $("#ai-clear").addEventListener("click", clearAiFilter);
    } catch (err) {
      out.textContent = `Search failed: ${err.message}`;
    }
  });

  // --- Events ---------------------------------------------------------------------------------

  ["#f-band", "#f-team", "#f-type", "#f-status", "#f-confidence"].forEach((s) => $(s).addEventListener("change", applyView));
  $("#f-watchlist").addEventListener("change", (e) => { state.includeWatchlist = e.target.checked; applyView(); });
  $("#f-sort").addEventListener("change", (e) => {
    if (!e.target.value) return;
    const [key, dir] = e.target.value.split(":");
    setSort(key, dir);
    applyView();
  });
  $("#f-search").addEventListener("input", applyView);
  $("#f-search").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.target.value = ""; applyView(); focusQueue(); }
    if (e.key === "Enter" || e.key === "ArrowDown") { e.preventDefault(); selectRow(0, true); }
  });
  $("#investigator").addEventListener("change", (e) => store.set(NAME_KEY, e.target.value.trim()));
  $("#nav-queue").addEventListener("click", () => showScreen("queue"));
  $("#nav-overview").addEventListener("click", () => showScreen("overview"));

  $("#queue-body").addEventListener("click", (e) => {
    const row = e.target.closest("tr[data-index]");
    if (!row) return;
    selectRow(Number(row.dataset.index), true);
    openAlert(state.view[state.selected].alert_id);
  });

  $("#queue-body").addEventListener("keydown", (e) => {
    const moves = { ArrowDown: 1, ArrowUp: -1, PageDown: 10, PageUp: -10 };
    if (e.key in moves) {
      e.preventDefault();
      selectRow(state.selected + moves[e.key], true);
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      selectRow(e.key === "Home" ? 0 : state.view.length - 1, true);
    } else if (e.key === "Enter" && state.view.length) {
      e.preventDefault();
      openAlert(state.view[state.selected].alert_id);
    }
  });

  document.querySelector(".queue-table thead").addEventListener("click", (e) => {
    const th = e.target.closest("th[data-sort]");
    if (!th) return;
    const key = th.dataset.sort;
    const textual = ["player_id", "top_reason", "team", "status"].includes(key);
    setSort(key, state.sort.key === key ? (state.sort.dir === "asc" ? "desc" : "asc") : (textual ? "asc" : "desc"));
    applyView();
  });

  document.addEventListener("keydown", (e) => {
    const typing = e.target.matches("input, textarea, select");
    if (e.key === "/" && !typing && state.screen === "queue") {
      e.preventDefault();
      $("#f-search").focus();
    } else if (e.key.toLowerCase() === "d" && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const btn = $('[data-act="accept"]');
      if (btn) { e.preventDefault(); btn.focus(); }
    } else if (e.key === "Escape" && !typing && $("#detail").contains(e.target)) {
      focusQueue();
    }
  });

  init();
})();
