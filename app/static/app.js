const $ = (id) => document.getElementById(id);
const catalogEl = $("catalog");
const resultsEl = $("results");
const visualsEl = $("visuals");
const summaryEl = $("summary");
const runBtn = $("run");
const countEl = $("productCount");

const LOW_ARC = "#3a4250";

function parseCatalog() {
  const text = catalogEl.value.trim();
  if (!text) throw new Error("Catalog is empty.");
  return JSON.parse(text);
}

function countProducts() {
  try {
    const data = parseCatalog();
    const nodes = Array.isArray(data.products)
      ? data.products
      : data.products?.nodes ?? [];
    countEl.textContent = `${nodes.length} product${nodes.length === 1 ? "" : "s"}`;
  } catch {
    countEl.textContent = "invalid JSON";
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[ch]);
}

function renderValue(value) {
  if (value === null || value === undefined) return "(empty)";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function shortId(productId) {
  const parts = String(productId).split("/");
  return parts[parts.length - 1] || String(productId);
}

function renderPipeline(count, state) {
  const chips = Array.from(
    { length: count },
    (_, i) =>
      `<div class="node agent ${state}"><span class="node-dot"></span>agent ${i + 1}</div>`
  ).join("");

  return `
    <div class="pipeline">
      <div class="node done"><span class="node-dot"></span>catalog<small>${count} product${count === 1 ? "" : "s"}</small></div>
      <div class="conn"></div>
      <div class="node ${state}"><span class="node-dot"></span>orchestrator<small>fan-out</small></div>
      <div class="conn"></div>
      <div class="agents">${chips}</div>
      <div class="conn"></div>
      <div class="node ${state === "done" ? "done" : ""}"><span class="node-dot"></span>diffs<small>${
        state === "done" ? "aggregated" : "pending"
      }</small></div>
    </div>`;
}

function renderStats(diffs) {
  const avg = (values) =>
    values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : 0;

  const before = avg(diffs.map((d) => d.score_before));
  const after = avg(diffs.map((d) => d.score_after));
  const findings = diffs.reduce((n, d) => n + (d.findings?.length ?? 0), 0);
  const patches = diffs.reduce((n, d) => n + (d.patches?.length ?? 0), 0);

  const tile = (value, label, cls = "") =>
    `<div class="stat"><div class="stat-value ${cls}">${value}</div><div class="stat-label">${label}</div></div>`;

  return `
    <div class="stats">
      ${tile(before, "avg score before")}
      ${tile(after, "avg score after", "up")}
      ${tile(`+${after - before}`, "avg lift", "up")}
      ${tile(findings, "findings")}
      ${tile(patches, "patches")}
    </div>`;
}

function renderScoreChart(diffs) {
  const rows = diffs
    .map(
      (d) => `
      <div class="chart-row">
        <div class="chart-label" title="${escapeHtml(d.product_id)}">${escapeHtml(shortId(d.product_id))}</div>
        <div class="chart-bars">
          <div class="bar-track">
            <div class="bar bar-before" style="width:${d.score_before}%"></div>
            <span class="bar-val">${d.score_before}</span>
          </div>
          <div class="bar-track">
            <div class="bar bar-after" style="width:${d.score_after}%"></div>
            <span class="bar-val">${d.score_after}</span>
          </div>
        </div>
        <div class="lift">+${d.score_after - d.score_before}</div>
      </div>`
    )
    .join("");

  return `<div><div class="viz-title">AEO score: before / after</div>${rows}</div>`;
}

function renderSeverityDonut(diffs) {
  const counts = { high: 0, medium: 0, low: 0 };
  diffs.forEach((d) =>
    (d.findings ?? []).forEach((f) => {
      if (counts[f.severity] !== undefined) counts[f.severity] += 1;
    })
  );

  const total = counts.high + counts.medium + counts.low;
  const safeTotal = total || 1;
  const highPct = (counts.high / safeTotal) * 100;
  const medPct = (counts.medium / safeTotal) * 100;
  const gradient =
    `conic-gradient(var(--bad) 0 ${highPct}%, ` +
    `var(--warn) ${highPct}% ${highPct + medPct}%, ` +
    `${LOW_ARC} ${highPct + medPct}% 100%)`;

  const legendRow = (color, label, value) =>
    `<div><span class="swatch" style="background:${color}"></span>${label} <span class="muted">${value}</span></div>`;

  return `
    <div>
      <div class="viz-title">Findings by severity</div>
      <div class="donut-wrap">
        <div class="donut" style="background:${gradient}">
          <div class="donut-center"><b>${total}</b><span>total</span></div>
        </div>
        <div class="legend">
          ${legendRow("var(--bad)", "high", counts.high)}
          ${legendRow("var(--warn)", "medium", counts.medium)}
          ${legendRow(LOW_ARC, "low", counts.low)}
        </div>
      </div>
    </div>`;
}

function renderFieldChart(diffs) {
  const tally = new Map();
  diffs.forEach((d) =>
    (d.patches ?? []).forEach((p) => tally.set(p.path, (tally.get(p.path) ?? 0) + 1))
  );

  const rows = [...tally.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  if (!rows.length) return "";

  const max = rows[0][1];
  const bars = rows
    .map(
      ([path, count]) => `
      <div class="field-row">
        <div class="field-path" title="${escapeHtml(path)}">${escapeHtml(path)}</div>
        <div class="field-bar" style="width:${(count / max) * 100}%"></div>
        <div class="field-count">${count}</div>
      </div>`
    )
    .join("");

  return `<div style="margin-top:16px"><div class="viz-title">Most patched fields</div>${bars}</div>`;
}

function renderVisuals(diffs) {
  return (
    renderPipeline(diffs.length, "done") +
    renderStats(diffs) +
    `<div class="viz-grid">${renderScoreChart(diffs)}${renderSeverityDonut(diffs)}</div>` +
    renderFieldChart(diffs)
  );
}

function renderDiff(diff) {
  const findings = (diff.findings ?? [])
    .map(
      (f) => `
      <div class="finding">
        <span class="sev sev-${escapeHtml(f.severity)}">${escapeHtml(f.severity)}</span>
        <div>
          <span class="code">${escapeHtml(f.code)}</span>
          <div>${escapeHtml(f.message)}</div>
        </div>
      </div>`
    )
    .join("");

  const patches = (diff.patches ?? [])
    .map(
      (p) => `
      <div class="patch">
        <div class="patch-path">${escapeHtml(p.op)} ${escapeHtml(p.path)}</div>
        <div class="diff-line diff-before">- ${escapeHtml(renderValue(p.before))}</div>
        <div class="diff-line diff-after">+ ${escapeHtml(renderValue(p.after))}</div>
        <div class="rationale">${escapeHtml(p.rationale)}</div>
      </div>`
    )
    .join("");

  return `
    <article class="card">
      <div class="card-head">
        <span class="pid">${escapeHtml(diff.product_id)}</span>
        <span class="score">
          <b class="before">${diff.score_before}</b>
          <span class="arrow">&rarr;</span>
          <b class="after">${diff.score_after}</b>
          <span class="muted">AEO score</span>
        </span>
      </div>
      ${findings ? `<div class="section-label">Findings</div>${findings}` : ""}
      ${patches ? `<div class="section-label">Patches</div>${patches}` : ""}
    </article>`;
}

async function loadSample() {
  const res = await fetch("/v1/sample");
  const data = await res.json();
  catalogEl.value = JSON.stringify(data, null, 2);
  countProducts();
}

async function run() {
  let payload;
  try {
    payload = parseCatalog();
  } catch (err) {
    resultsEl.innerHTML = `<div class="card error">${escapeHtml(err.message)}</div>`;
    return;
  }

  const pending = Array.isArray(payload.products)
    ? payload.products
    : payload.products?.nodes ?? [];

  runBtn.disabled = true;
  runBtn.innerHTML = '<span class="spinner"></span>Running agents...';
  summaryEl.textContent = "";
  visualsEl.innerHTML = renderPipeline(pending.length, "running");
  resultsEl.innerHTML = '<p class="empty">Fanning out one agent per product...</p>';

  const started = performance.now();
  try {
    const res = await fetch("/v1/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      visualsEl.innerHTML = '<p class="empty">Run failed.</p>';
      resultsEl.innerHTML = `<div class="card error">${escapeHtml(data.detail ?? res.statusText)}</div>`;
      return;
    }

    const diffs = data.products ?? [];
    const elapsed = ((performance.now() - started) / 1000).toFixed(1);
    summaryEl.textContent = `${diffs.length} product${diffs.length === 1 ? "" : "s"} in ${elapsed}s`;
    visualsEl.innerHTML = diffs.length
      ? renderVisuals(diffs)
      : '<p class="empty">No diffs returned.</p>';
    resultsEl.innerHTML = diffs.length
      ? diffs.map(renderDiff).join("")
      : '<p class="empty">No diffs returned.</p>';
  } catch (err) {
    visualsEl.innerHTML = '<p class="empty">Run failed.</p>';
    resultsEl.innerHTML = `<div class="card error">${escapeHtml(err.message)}</div>`;
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run optimization";
  }
}

async function checkHealth() {
  const pill = $("health");
  try {
    const res = await fetch("/health");
    const ok = res.ok && (await res.json()).status === "ok";
    pill.textContent = ok ? "backend online" : "backend error";
    pill.className = `pill ${ok ? "pill-ok" : "pill-bad"}`;
  } catch {
    pill.textContent = "backend offline";
    pill.className = "pill pill-bad";
  }
}

$("loadSample").addEventListener("click", loadSample);
$("format").addEventListener("click", () => {
  try {
    catalogEl.value = JSON.stringify(parseCatalog(), null, 2);
    countProducts();
  } catch (err) {
    resultsEl.innerHTML = `<div class="card error">${escapeHtml(err.message)}</div>`;
  }
});
runBtn.addEventListener("click", run);
catalogEl.addEventListener("input", countProducts);

checkHealth();
loadSample();
