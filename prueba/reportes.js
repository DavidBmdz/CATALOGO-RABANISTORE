const fileInput = document.querySelector("#reportFile");
const reportSection = document.querySelector("#report");
const fileName = document.querySelector("#fileName");
const message = document.querySelector("#message");
const clearButton = document.querySelector("#clearReports");
const loadedReports = [];
const numberFormat = new Intl.NumberFormat("es-NI");
const chartColors = ["#a74763", "#396c8c", "#598567", "#c27a32", "#7957a5", "#338c88", "#bf5964", "#687382"];

function formatNumber(value, digits = 2) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("es-NI", { maximumFractionDigits: digits }).format(value);
}

function addMetric(label, value) {
  const card = document.createElement("article");
  card.className = "metric-card";
  const title = document.createElement("span");
  title.className = "metric-label";
  title.textContent = label;
  const result = document.createElement("strong");
  result.className = "metric-value";
  result.textContent = value;
  card.append(title, result);
  document.querySelector("#metricCards").append(card);
}

function fillTable(bodyId, rows, emptyId) {
  const body = document.querySelector(bodyId);
  body.replaceChildren();
  for (const cells of rows) {
    const row = document.createElement("tr");
    for (const value of cells) {
      const cell = document.createElement("td");
      cell.textContent = String(value);
      row.append(cell);
    }
    body.append(row);
  }
  if (emptyId) document.querySelector(emptyId).hidden = rows.length > 0;
}

function errorRate(report) {
  const requests = Number(report.requests) || 0;
  return requests ? (Number(report.error_count) || 0) * 100 / requests : 0;
}

function renderReport(report, name) {
  document.querySelector("#reportTitle").textContent = name;
  const date = report.started_at_utc ? new Date(report.started_at_utc) : null;
  document.querySelector("#runTime").textContent = date && !Number.isNaN(date.valueOf())
    ? `Inicio: ${date.toLocaleString("es-NI")}`
    : "Fecha de inicio no disponible";

  const metrics = document.querySelector("#metricCards");
  metrics.replaceChildren();
  addMetric("Usuarios virtuales", numberFormat.format(report.virtual_users ?? 0));
  addMetric("Concurrencia", numberFormat.format(report.concurrency ?? 0));
  addMetric("Solicitudes", numberFormat.format(report.requests ?? 0));
  addMetric("Solicitudes por segundo", formatNumber(report.requests_per_second));
  addMetric("Duración", `${formatNumber(report.elapsed_seconds)} s`);
  addMetric("Errores", numberFormat.format(report.error_count ?? 0));
  addMetric("Latencia media", `${formatNumber(report.latency_ms.mean)} ms`);
  addMetric("Latencia p50", `${formatNumber(report.latency_ms.p50)} ms`);
  addMetric("Latencia p95", `${formatNumber(report.latency_ms.p95)} ms`);
  addMetric("Latencia p99", `${formatNumber(report.latency_ms.p99)} ms`);
  addMetric("Latencia máxima", `${formatNumber(report.latency_ms.max)} ms`);

  fillTable("#statusRows", Object.entries(report.status_counts)
    .map(([status, count]) => [status, numberFormat.format(count)]));
  const errorTypes = report.network_error_types || (
    report.status_counts.network_error
      ? { "Sin desglose (reporte anterior)": report.status_counts.network_error }
      : {}
  );
  fillTable("#errorTypeRows", Object.entries(errorTypes)
    .map(([type, count]) => [type, numberFormat.format(count)]), "#noNetworkErrors");
  fillTable("#sampleErrorRows", (report.sample_errors || [])
    .map((error, index) => [index + 1, error]), "#noSampleErrors");
  document.querySelector("#scopeNote").textContent = [
    report.target ? `Destino: ${report.target}.` : "",
    report.scope_note || "",
  ].filter(Boolean).join(" ");
}

function drawBarChart(canvasId, reports, series, valueFor, unit) {
  const canvas = document.querySelector(`#${canvasId}`);
  const frame = canvas.parentElement;
  const chartWidth = Math.max(frame.clientWidth, reports.length * 92 + 92, 360);
  const chartHeight = 300;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = chartWidth * ratio;
  canvas.height = chartHeight * ratio;
  canvas.style.width = `${chartWidth}px`;
  canvas.style.height = `${chartHeight}px`;

  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, chartWidth, chartHeight);
  context.font = "12px Segoe UI, Arial, sans-serif";

  const left = 62;
  const right = chartWidth - 20;
  const top = 45;
  const bottom = 225;
  const plotWidth = right - left;
  const plotHeight = bottom - top;
  const values = reports.flatMap(entry => series.map(item => valueFor(entry.report, item.key)))
    .filter(value => Number.isFinite(value) && value >= 0);
  const maximum = Math.max(...values, 0);
  const ceiling = maximum === 0 ? 1 : maximum * 1.12;

  context.textAlign = "right";
  context.textBaseline = "middle";
  for (let tick = 0; tick <= 4; tick += 1) {
    const y = top + plotHeight * tick / 4;
    const value = ceiling * (4 - tick) / 4;
    context.strokeStyle = "#eadbdd";
    context.beginPath();
    context.moveTo(left, y);
    context.lineTo(right, y);
    context.stroke();
    context.fillStyle = "#74686a";
    context.fillText(`${formatNumber(value, 1)}${unit}`, left - 8, y);
  }

  const groupWidth = reports.length ? plotWidth / reports.length : plotWidth;
  const barWidth = Math.min(36, groupWidth * 0.62 / series.length);
  reports.forEach((entry, reportIndex) => {
    const center = left + groupWidth * (reportIndex + 0.5);
    series.forEach((item, seriesIndex) => {
      const value = valueFor(entry.report, item.key);
      if (!Number.isFinite(value) || value < 0) return;
      const height = value / ceiling * plotHeight;
      const x = center + (seriesIndex - (series.length - 1) / 2) * barWidth - barWidth / 2;
      context.fillStyle = item.color;
      context.beginPath();
      context.roundRect(x, bottom - height, barWidth - 3, height, [4, 4, 0, 0]);
      context.fill();
    });
    context.fillStyle = "#302526";
    context.textAlign = "center";
    context.textBaseline = "top";
    context.fillText(numberFormat.format(entry.report.virtual_users ?? 0), center, bottom + 10);
  });

  let legendX = left;
  context.textAlign = "left";
  context.textBaseline = "middle";
  series.forEach(item => {
    context.fillStyle = item.color;
    context.fillRect(legendX, 15, 12, 12);
    context.fillStyle = "#302526";
    context.fillText(item.label, legendX + 18, 21);
    legendX += context.measureText(item.label).width + 42;
  });
  context.fillStyle = "#74686a";
  context.textAlign = "center";
  context.textBaseline = "top";
  context.fillText("Usuarios virtuales", (left + right) / 2, 264);
}

function renderComparison() {
  const sorted = [...loadedReports].sort((a, b) =>
    (a.report.virtual_users || 0) - (b.report.virtual_users || 0)
  );
  fillTable("#comparisonRows", sorted.map(({ report, name }) => [
    name,
    numberFormat.format(report.virtual_users ?? 0),
    numberFormat.format(report.concurrency ?? 0),
    formatNumber(report.requests_per_second),
    formatNumber(report.latency_ms.p95),
    formatNumber(report.latency_ms.p99),
    `${formatNumber(errorRate(report))}%`,
  ]));

  drawBarChart("rpsChart", sorted,
    [{ key: "rps", label: "Solicitudes/s", color: chartColors[0] }],
    report => Number(report.requests_per_second), "");
  drawBarChart("latencyChart", sorted,
    [
      { key: "p95", label: "p95", color: chartColors[1] },
      { key: "p99", label: "p99", color: chartColors[4] },
    ],
    (report, key) => Number(report.latency_ms[key]), " ms");
  drawBarChart("errorChart", sorted,
    [{ key: "errorRate", label: "Errores", color: chartColors[3] }],
    report => errorRate(report), "%");
}

function renderAll() {
  if (!loadedReports.length) {
    reportSection.hidden = true;
    fileName.textContent = "Ningún archivo seleccionado";
    clearButton.disabled = true;
    return;
  }
  const last = loadedReports[loadedReports.length - 1];
  renderReport(last.report, last.name);
  renderComparison();
  fileName.textContent = `${numberFormat.format(loadedReports.length)} reporte(s) cargado(s)`;
  clearButton.disabled = false;
  reportSection.hidden = false;
}

fileInput.addEventListener("change", async () => {
  const files = Array.from(fileInput.files || []);
  if (!files.length) return;
  message.textContent = "";
  const errors = [];

  for (const file of files) {
    const alreadyLoaded = loadedReports.some(entry =>
      entry.name === file.name && entry.size === file.size && entry.lastModified === file.lastModified
    );
    if (alreadyLoaded) continue;
    try {
      const report = JSON.parse(await file.text());
      if (!report || typeof report !== "object" || !report.latency_ms || !report.status_counts) {
        throw new Error("no tiene el formato esperado de reporte de carga");
      }
      loadedReports.push({
        report,
        name: file.name,
        size: file.size,
        lastModified: file.lastModified,
      });
    } catch (error) {
      errors.push(`${file.name}: ${error instanceof SyntaxError ? "JSON no válido" : error.message}`);
    }
  }
  renderAll();
  message.textContent = errors.length
    ? `No se pudieron cargar: ${errors.join("; ")}`
    : "";
  fileInput.value = "";
});

clearButton.addEventListener("click", () => {
  loadedReports.length = 0;
  message.textContent = "";
  renderAll();
});

window.addEventListener("resize", () => {
  if (loadedReports.length) renderComparison();
});
