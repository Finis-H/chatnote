const ROOT = "..";
const DEFAULT_LOCALE = "zh-CN";
const ROUTES = ["control-terminal", "agent-running", "memory-permission", "plugin-center"];
const viewConfig = {
  "control-terminal": { frame: "01-control-terminal", group: "execution", icon: ">_" },
  "agent-running": { frame: "02-agent-running", group: "execution", icon: "<>" },
  "memory-permission": { frame: "03-memory-permission", group: "knowledge", icon: "[]" },
  "plugin-center": { frame: "04-plugin-center", group: "system", icon: "//" },
};
const app = document.querySelector("#app");
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#039;", '"': "&quot;" })[char]);

async function loadJson(path) {
  const response = await fetch(`${ROOT}/${path}`);
  if (!response.ok) throw new Error(path);
  return response.json();
}

async function loadText(path) {
  const response = await fetch(`${ROOT}/${path}`);
  if (!response.ok) throw new Error(path);
  return response.text();
}

function yamlScalar(source, key) {
  return source.match(new RegExp(`^${key}:\\s*(.+)$`, "m"))?.[1]?.trim() || "";
}

function yamlList(source, key) {
  const inline = source.match(new RegExp(`^${key}:\\s*\\[([^\\]]*)\\]`, "m"))?.[1];
  if (inline) return inline.split(",").map((item) => item.trim()).filter(Boolean);
  const block = source.match(new RegExp(`^${key}:\\n([\\s\\S]*?)(?=^[A-Za-z_]+:|(?![\\s\\S]))`, "m"))?.[1] || "";
  return [...block.matchAll(/^\s+-\s+(.+)$/gm)].map((match) => match[1].trim());
}

function yamlValue(value) {
  return value.trim().replace(/^['"]|['"]$/g, "");
}

function parseHandoff(source) {
  const keys = ["annotation", "user_goal", "core_information", "primary_action", "risk_state", "design_rationale", "required_components", "states_to_show", "frontend_codex_acceptance"];
  const start = source.indexOf("handoff:");
  const end = source.indexOf("portfolio_story:", start);
  const block = start < 0 ? "" : source.slice(start, end < 0 ? source.length : end);
  return Object.fromEntries(keys.flatMap((key, index) => {
    const next = keys[index + 1];
    const match = block.match(new RegExp(`\\s{2}${key}:[ \\t]*([\\s\\S]*?)${next ? `(?=\\s{2}${next}:)` : "$"}`));
    if (!match) return [];
    const value = match[1].trim();
    const list = value.match(/^\[(.*)\]$/);
    return [[key, list ? list[1].split(",").map((item) => item.trim()).filter(Boolean) : yamlValue(value)]];
  }));
}

function parseFrame(source) {
  return {
    title: yamlScalar(source, "title"),
    story: yamlScalar(source, "portfolio_story"),
    components: yamlList(source, "components"),
    handoff: parseHandoff(source),
  };
}

function parseComponentNames(source) {
  return [...source.matchAll(/^  ([a-z_]+):\n    purpose:/gm)].map((match) => match[1]);
}

function routeName() {
  const route = location.hash.replace(/^#\/?/, "");
  return ROUTES.includes(route) ? route : "control-terminal";
}

function statusTag(label, tone = "") {
  return `<span class="tag ${tone}">${escapeHtml(label)}</span>`;
}

function permissionLabel(permission, copy) {
  return copy.permissionLabels[permission] || permission;
}

function navLink(route, active, copy) {
  const key = route.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
  return `<a class="nav-link ${route === active ? "is-active" : ""}" href="#${route}"><span class="nav-icon">${viewConfig[route].icon}</span>${escapeHtml(copy.navigation[key])}</a>`;
}

function handoffAnnotation(frame) {
  const fields = [
    ["User Goal", "user_goal"],
    ["Core Information", "core_information"],
    ["Primary Action", "primary_action"],
    ["Risk State", "risk_state"],
    ["Design Rationale", "design_rationale"],
    ["Required Components", "required_components"],
    ["States to Show", "states_to_show"],
    ["Frontend / Codex Acceptance Criteria", "frontend_codex_acceptance"],
  ];
  const value = (item) => Array.isArray(item) ? item.join(", ") : item;
  return `<aside class="handoff-annotation" aria-label="${escapeHtml(frame.handoff.annotation)}"><header class="handoff-heading"><strong>${escapeHtml(frame.handoff.annotation)}</strong><span>Static export overlay</span></header><dl class="handoff-grid">${fields.map(([label, key]) => `<div class="handoff-item"><dt>${label}</dt><dd>${escapeHtml(value(frame.handoff[key] || "—"))}</dd></div>`).join("")}</dl></aside>`;
}

function shell(route, frame, componentNames, copy, content) {
  const groups = ["execution", "knowledge", "system"].map((group) => {
    const routes = ROUTES.filter((item) => viewConfig[item].group === group);
    return `<section class="nav-group"><h2 class="nav-title">${escapeHtml(copy.navigation[group])}</h2>${routes.map((item) => navLink(item, route, copy)).join("")}</section>`;
  }).join("");
  const wsCopy = route === "agent-running" ? copy.status.websocketFixture : copy.status.websocketConnected;
  const state = route === "agent-running" ? "running" : route === "plugin-center" ? "warning" : "";
  const derivedCount = frame.components.filter((name) => componentNames.includes(name)).length;
  const isMemorySync = route === "memory-permission";
  const pageTitle = isMemorySync ? copy.memory.syncTitle : frame.title;
  const viewHeading = route === "memory-permission" ? "" : `<header class="view-head"><div><span class="eyebrow">${escapeHtml(copy.navigation[viewConfig[route].group])}</span><h1>${escapeHtml(frame.title)}</h1></div><p>${escapeHtml(frame.story)}</p><span class="spec-chip">${derivedCount} ${copy.app.componentsFromSpec}</span></header>`;
  return `<section class="app-shell" data-locale="${DEFAULT_LOCALE}">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">V/</div><div class="brand-copy"><strong>${copy.app.brand}</strong><span>${copy.app.brandSubtitle}</span></div></div>
      ${groups}
      <div class="sidebar-foot">${copy.app.prototypeNote}<br>${copy.app.fixtureOnly}</div>
    </aside>
    <section class="workspace">
      <header class="topbar"><div class="topbar-title"><strong>${escapeHtml(pageTitle)}</strong></div><div class="ws-status"><i class="status-dot ${state}"></i>${wsCopy}</div></header>
      <section class="view ${route === "memory-permission" ? "memory-view" : ""}">${viewHeading}${content}</section>
    </section>
  </section>${handoffAnnotation(frame)}`;
}

function controlTerminal(copy) {
  const c = copy.controlTerminal;
  return `<div class="terminal-grid">
    <section class="conversation card"><header class="conversation-head"><p class="panel-title">${c.session}</p>${statusTag(c.ready, "accent")}</header>
      <section class="trace-summary" aria-label="${c.traceSummary}"><div><span class="eyebrow">${c.traceSummary}</span><p>${c.traceDescription}</p></div><div class="trace-stage-list">${c.traceStages.map((stage, index) => `<span class="trace-stage ${index === 2 ? "active" : ""}">${index + 1}. ${stage}</span>`).join("")}</div>${statusTag(copy.status.partial, "warning")}</section>
      <div class="messages"><article class="message user"><small>${c.operator}</small>${c.operatorMessage}</article><article class="message"><small>${c.assistant}</small>${c.assistantMessage}</article><article class="message"><small>${c.boundary}</small>${c.boundaryMessage}</article></div>
      <form class="console" onsubmit="return false"><span>›</span><input aria-label="${c.commandLabel}" value="${c.commandValue}" readonly /><button class="button" type="button" disabled>${copy.status.fixtureData}</button></form>
    </section>
    <aside class="side-stack"><section class="status-card card"><p class="panel-title">${c.workspaceStatus}</p><div class="metric"><span class="muted">${c.connection}</span><strong>${copy.status.websocketConnected}</strong></div><div class="metric"><span class="muted">${c.mainSession}</span><strong>${copy.status.implemented}</strong></div><div class="metric"><span class="muted">${c.localContext}</span><strong>${copy.status.implemented}</strong></div></section><section class="dock-card card"><p class="panel-title">${c.memoryContext}</p><div class="dock-row"><strong>${c.memoryContextDetail}</strong><span class="muted">${copy.status.partial}</span></div></section><section class="status-card card"><p class="panel-title">${c.health}</p><p class="muted">${c.healthDetail}</p></section></aside>
  </div>`;
}

function agentRunning(copy, fixture) {
  const c = copy.agentRunning;
  const steps = fixture.events.map((event) => {
    const status = event.status.toLowerCase();
    const time = event.duration_ms ? `${event.duration_ms} 毫秒` : copy.status.fixtureData;
    const detail = event.status === "DEGRADED" ? c.degradedDetail : c.eventDetail;
    return `<article class="trace-step ${status}"><i class="step-node"></i><div><h3>${escapeHtml(event.label)}</h3><p>${detail}</p></div><span class="trace-time">${time}</span></article>`;
  }).join("");
  const safeguards = [[c.dagPreflight, fixture.feature_status.dag_preflight], [c.redaction, fixture.feature_status.sensitive_redaction], [c.runtimeInterception, fixture.feature_status.runtime_interception], [c.outputIsolation, fixture.feature_status.untrusted_output_isolation]];
  return `<div class="trace-layout"><section class="card"><header class="panel-head"><p class="panel-title">${c.timeline}</p>${statusTag(copy.status.fixtureData, "warning")}</header><p class="fixture-notice">${c.fixtureNotice}</p><div class="trace-timeline">${steps}</div></section><aside class="side-stack"><section class="status-card card"><p class="panel-title">${c.taskState}</p><div class="metric"><span class="muted">${c.request}</span><strong>${c.messageRequest}</strong></div><div class="metric"><span class="muted">${c.transport}</span><strong>${c.websocketTransport}</strong></div><div class="metric"><span class="muted">${c.traceId}</span><strong>001</strong></div></section><section class="status-card card recovery-card"><p class="panel-title">${c.recovery}</p><p class="muted">${c.recoveryDetail}</p></section><section class="status-card card"><p class="panel-title">${c.guarantees}</p>${safeguards.map(([label, status]) => `<div class="metric"><span class="muted">${label}</span>${statusTag(copy.status[status], "warning")}</div>`).join("")}</section></aside></div>`;
}

function memoryPermission(copy, fixture) {
  const c = copy.memory;
  const memoryEvent = fixture.responses.find((event) => event.type === "memory_data");
  const pending = memoryEvent.content.find((item) => item.status === "PENDING");
  const workflow = fixture.workflowSummary;
  const review = fixture.pendingReview;
  return `<section class="memory-sync-layout">
    <header class="memory-sync-head"><div class="memory-sync-title"><span class="memory-sync-mark" aria-hidden="true"></span><div><h1>${c.syncTitle}</h1><p>${escapeHtml(workflow.headerDescription)}</p></div></div></header>
    <section class="memory-flow-card card"><div class="memory-flow-copy"><span class="eyebrow">${c.flow}</span><h2>${escapeHtml(workflow.summaryText)}</h2></div><dl class="memory-flow-metrics"><div><dt>${c.receivedClues}</dt><dd>${workflow.receivedClues}</dd></div><div><dt>${c.pendingConfirmation}</dt><dd>${workflow.pendingConfirmations}</dd></div><div><dt>${c.lastSynced}</dt><dd>${escapeHtml(workflow.lastSyncLabel)}</dd></div></dl></section>
    <nav class="memory-filters" aria-label="${c.filterAriaLabel}"><span class="memory-filter">${c.filterAll}</span><span class="memory-filter is-active" aria-current="page">${c.filterPending} (${workflow.pendingConfirmations})</span><span class="memory-filter">${c.filterHistory}</span></nav>
    <section class="memory-candidate-section" aria-labelledby="memory-candidate-title"><p id="memory-candidate-title" class="panel-title">${c.candidate}</p><article class="memory-candidate-row card"><div class="memory-candidate-content"><div class="memory-candidate-summary"><div><span class="eyebrow">${escapeHtml(pending.category)}</span><h2>${escapeHtml(pending.new_trait)}</h2></div>${statusTag(review.riskLabel, "warning")}</div><div class="memory-candidate-evidence"><div class="memory-candidate-details">${review.fields.map((field) => `<div><span>${escapeHtml(field.label)}</span>${escapeHtml(field.value)}</div>`).join("")}</div><aside class="confirmation-reasons"><p class="panel-title">为什么需要确认</p><ul>${review.confirmationReasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul></aside></div></div><div class="memory-candidate-review"><span class="candidate-review-state">${c.pendingReview}</span><div><span class="muted">${c.deadline}</span><strong>${escapeHtml(review.countdown)}</strong></div><div class="actions"><button class="button danger" type="button" disabled>${c.reject}</button><button class="button" type="button" disabled>${c.accept}</button></div></div></article></section>
  </section>`;
}

function pluginCenter(copy, manifestFixture, requestsFixture) {
  const c = copy.plugin;
  const request = requestsFixture.requestEvents[0];
  const preview = JSON.stringify(request.preview, null, 2);
  return `<div class="plugin-layout"><section class="plugin-center"><section class="plugin-card card"><div class="plugin-name"><div><span class="eyebrow">${c.directoryIdentity}</span><h2>${escapeHtml(manifestFixture.name)}</h2><span class="muted mono">${escapeHtml(manifestFixture.installed_directory_name)}</span></div>${statusTag(copy.status.partial, "warning")}</div><p class="panel-title plugin-section-title">${c.declaration}</p><div class="permission-grid">${manifestFixture.security.permissions.map((permission) => `<div class="permission-cell">${escapeHtml(permissionLabel(permission, copy))}</div>`).join("")}</div><div class="plugin-card-actions" data-plugin-id="${escapeHtml(manifestFixture.plugin_id)}"><button class="button secondary" type="button" disabled aria-label="${escapeHtml(c.settings)} ${escapeHtml(manifestFixture.name)}">${c.settings}</button><button class="button danger" type="button" disabled aria-label="${escapeHtml(c.delete)} ${escapeHtml(manifestFixture.name)}">${c.delete}</button></div></section><p class="trust-note">${c.untrusted}</p><section class="spec-card card"><p class="panel-title">${c.checks}</p><div class="component-list">${[c.dagPreflight, c.runtimeInterception, c.sensitiveDetection, c.outputIsolation].map((label) => statusTag(label)).join("")}</div></section></section><aside class="permission-dialog readonly-panel"><header class="dialog-head"><span class="eyebrow">${copy.status.planned} · ${copy.status.readonly}</span><h2>${c.permissionGovernance}</h2></header><div class="dialog-content"><p class="dialog-copy">${c.planningDetail}</p><p class="dialog-copy">${escapeHtml(request.reason)}</p><div>${request.permissions.map((permission) => statusTag(permissionLabel(permission, copy), "warning")).join(" ")}</div><p class="panel-title">${c.redactedPreview}</p><pre class="preview" aria-label="${c.redactedPreview}">${escapeHtml(preview)}</pre><p class="panel-title">${c.decisionModel}</p><div class="decision-legend">${[c.deny, c.allowOnce, c.allowSession].map((label) => statusTag(label)).join("")}</div></div></aside></div>`;
}

function agentSafeguardEvidence(copy, agentFixture, permissionRequests) {
  const dagRequest = permissionRequests.requestEvents.find((event) => event.request_id === "perm_fixture_dag_001");
  const preflight = dagRequest.preflight;
  const runtime = agentFixture.runtime_interception;
  const inspectedRows = dagRequest.items.map((item) => `<div class="evidence-row"><span>${escapeHtml(item.plugin_name)}</span><strong>${escapeHtml(item.tool_name)}</strong></div>`).join("");
  const groupedPermissions = dagRequest.items.flatMap((item) => item.permissions).filter((permission, index, values) => values.indexOf(permission) === index);
  const runtimePreview = JSON.stringify(runtime.redacted_arguments, null, 2);
  return `<section class="trace-evidence" aria-label="Runtime safeguard evidence"><article class="evidence-card"><header><div><span class="eyebrow">${escapeHtml(preflight.stage)}</span><h3>${escapeHtml(preflight.title)}</h3></div>${statusTag(preflight.result, "warning")}</header><p class="evidence-label">${escapeHtml(preflight.inspected_label)}</p>${inspectedRows}<p class="evidence-label">${escapeHtml(preflight.grouped_request_label)}</p><div class="component-list">${groupedPermissions.map((permission) => statusTag(permissionLabel(permission, copy), "warning")).join("")}</div></article><article class="evidence-card interception-card"><header><div><span class="eyebrow">${escapeHtml(runtime.stage)}</span><h3>${escapeHtml(runtime.title)}</h3></div>${statusTag(runtime.agent_state, "warning")}</header><p class="evidence-label">${escapeHtml(runtime.invocation_label)}</p><div class="evidence-row"><span>${escapeHtml(runtime.plugin_id)}</span><strong>${escapeHtml(runtime.tool_name)}</strong></div><p class="evidence-label">${escapeHtml(runtime.trigger_label)}</p><p class="evidence-copy">${escapeHtml(runtime.trigger)}</p><pre class="evidence-preview">${escapeHtml(runtimePreview)}</pre><div class="evidence-result">${statusTag(runtime.permission_result, "warning")}${statusTag(runtime.agent_state, "warning")}</div></article></section>`;
}

function untrustedOutputCard(output) {
  const payload = JSON.stringify(output.payload, null, 2);
  return `<section class="untrusted-output-card card" aria-label="${escapeHtml(output.label)}"><header><div><span class="eyebrow">${escapeHtml(output.status)}</span><h3>${escapeHtml(output.label)}</h3></div>${statusTag(output.treatment, "warning")}</header><p>${escapeHtml(output.notice)}</p><pre class="output-payload">${escapeHtml(payload)}</pre></section>`;
}

function permissionDecisionRow(copy) {
  const c = copy.plugin;
  const options = [
    [c.deny, c.decisionScopes.deny, "danger"],
    [c.allowOnce, c.decisionScopes.allowOnce, "secondary"],
    [c.allowSession, c.decisionScopes.allowSession, ""],
  ];
  return `<section class="permission-decision-row" aria-label="${escapeHtml(c.decisionModel)}">${options.map(([label, scope, tone]) => `<div class="decision-option"><button class="button ${tone}" type="button" disabled>${escapeHtml(label)}</button><span>${escapeHtml(scope)}</span></div>`).join("")}</section>`;
}

function render(route, resources) {
  const frame = resources.frames[viewConfig[route].frame];
  const content = route === "control-terminal" ? controlTerminal(resources.copy)
    : route === "agent-running" ? agentRunning(resources.copy, resources.agentRun)
      : route === "memory-permission" ? memoryPermission(resources.copy, resources.memory)
        : pluginCenter(resources.copy, resources.pluginManifest, resources.permissionRequests);
  app.innerHTML = shell(route, frame, resources.componentNames, resources.copy, content);
  if (route === "agent-running") {
    app.querySelector(".trace-layout > .card").insertAdjacentHTML("beforeend", agentSafeguardEvidence(resources.copy, resources.agentRun, resources.permissionRequests));
  }
  if (route === "plugin-center") {
    app.querySelector(".plugin-center").insertAdjacentHTML("beforeend", untrustedOutputCard(resources.permissionRequests.third_party_output));
    app.querySelector(".decision-legend").outerHTML = permissionDecisionRow(resources.copy);
  }
}

async function boot() {
  const frameKeys = Object.values(viewConfig).map((config) => config.frame);
  const [copy, componentSource, ...frameSources] = await Promise.all([
    loadJson(`copy/${DEFAULT_LOCALE}.json`),
    loadText("specs/components.yaml"),
    ...frameKeys.map((key) => loadText(`specs/frames/${key}.yaml`)),
  ]);
  const [agentRun, memory, pluginManifest, permissionRequests] = await Promise.all([
    loadJson("fixtures/agent-run-events.json"), loadJson("fixtures/memory-events.json"), loadJson("fixtures/plugin-manifest.json"), loadJson("fixtures/permission-requests.json"),
  ]);
  const frames = Object.fromEntries(frameKeys.map((key, index) => [key, parseFrame(frameSources[index])]));
  const resources = { copy, componentNames: parseComponentNames(componentSource), frames, agentRun, memory, pluginManifest, permissionRequests };
  const update = () => render(routeName(), resources);
  window.addEventListener("hashchange", update);
  update();
}

boot().catch((error) => {
  app.innerHTML = `<section class="error-card"><strong>原型资源无法加载。</strong><p>${escapeHtml(error.message)}</p><p>请通过本地静态 HTTP 服务打开，以读取规格与模拟夹具。</p></section>`;
});
