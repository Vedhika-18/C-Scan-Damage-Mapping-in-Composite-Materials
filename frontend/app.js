const form = document.querySelector("#scan-form");
const status = document.querySelector("#status");
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
}[character]));

let inspectionPoints = [];
let geometryPoints = [];
let scanBounds = null;
let scanTransform = { scale: 1, offsetX: 0, offsetY: 0 };
let cloudTransform = { scale: 1, rotation: 0 };

function canvasPoint(canvas, point, transform = scanTransform) {
  const x = (point[0] - scanBounds.x_min) / Math.max(scanBounds.x_max - scanBounds.x_min, 1e-9);
  const y = (point[1] - scanBounds.y_min) / Math.max(scanBounds.y_max - scanBounds.y_min, 1e-9);
  return {
    x: 35 + x * (canvas.width - 55) * transform.scale + transform.offsetX,
    y: canvas.height - 30 - y * (canvas.height - 55) * transform.scale + transform.offsetY,
  };
}

function drawCscan() {
  const canvas = document.querySelector("#cscan-canvas");
  if (!canvas || !scanBounds) return;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#081018";
  context.fillRect(0, 0, canvas.width, canvas.height);
  const signals = inspectionPoints.map((point) => point[2]);
  const minimum = Math.min(...signals);
  const maximum = Math.max(...signals);
  const threshold = Number(document.querySelector("#threshold").value) / 100;
  const cutoff = minimum + (maximum - minimum) * threshold;
  const radius = 3;
  for (const point of inspectionPoints) {
    const position = canvasPoint(canvas, point);
    const relative = (point[2] - minimum) / Math.max(maximum - minimum, 1e-9);
    context.fillStyle = relative >= threshold
      ? `rgb(255, ${Math.round(220 - relative * 130)}, 80)`
      : `rgb(${Math.round(40 + relative * 120)}, ${Math.round(180 - relative * 90)}, ${Math.round(220 - relative * 100)})`;
    context.globalAlpha = relative >= cutoff ? 1 : 0.8;
    context.beginPath();
    context.arc(position.x, position.y, radius, 0, Math.PI * 2);
    context.fill();
  }
  context.globalAlpha = 1;
  context.strokeStyle = "#7e94a5";
  context.strokeRect(35, 15, canvas.width - 55, canvas.height - 45);
  context.fillStyle = "#9aacbb";
  context.font = "12px system-ui";
  context.fillText(`X: ${scanBounds.x_min.toFixed(2)} - ${scanBounds.x_max.toFixed(2)}`, 35, canvas.height - 10);
  context.save();
  context.translate(12, canvas.height - 35);
  context.rotate(-Math.PI / 2);
  context.fillText(`Y: ${scanBounds.y_min.toFixed(2)} - ${scanBounds.y_max.toFixed(2)}`, 0, 0);
  context.restore();
}

function drawPointCloud() {
  const canvas = document.querySelector("#point-cloud");
  if (!canvas || !geometryPoints.length) return;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#081018";
  context.fillRect(0, 0, canvas.width, canvas.height);
  const xs = geometryPoints.map((point) => point[0]);
  const ys = geometryPoints.map((point) => point[1]);
  const zs = geometryPoints.map((point) => point[2]);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const zMin = Math.min(...zs), zMax = Math.max(...zs);
  const size = Number(document.querySelector("#point-size").value);
  for (const point of geometryPoints) {
    const nx = (point[0] - xMin) / Math.max(xMax - xMin, 1e-9) - 0.5;
    const ny = (point[1] - yMin) / Math.max(yMax - yMin, 1e-9) - 0.5;
    const nz = (point[2] - zMin) / Math.max(zMax - zMin, 1e-9) - 0.5;
    const rotatedX = nx * Math.cos(cloudTransform.rotation) - nz * Math.sin(cloudTransform.rotation);
    const rotatedZ = nx * Math.sin(cloudTransform.rotation) + nz * Math.cos(cloudTransform.rotation);
    const x = canvas.width / 2 + rotatedX * canvas.width * cloudTransform.scale;
    const y = canvas.height / 2 - ny * canvas.height * cloudTransform.scale + rotatedZ * 30;
    const shade = Math.round(110 + (nz + 0.5) * 120);
    context.fillStyle = `rgb(83, ${shade}, ${Math.max(120, shade + 10)})`;
    context.fillRect(x, y, size, size);
  }
  context.fillStyle = "#9aacbb";
  context.font = "12px system-ui";
  context.fillText(`X ${xMin.toFixed(2)}–${xMax.toFixed(2)} | Y ${yMin.toFixed(2)}–${yMax.toFixed(2)} | Z ${zMin.toFixed(2)}–${zMax.toFixed(2)}`, 16, 22);
}

function renderIndicationsCsv(csv) {
  const rows = csv.trim().split(/\r?\n/).filter(Boolean).map((line) => line.split(","));
  if (!rows.length) return "<p>No indication data available.</p>";
  return `<table><thead><tr>${rows[0].map((cell) => `<th>${escapeHtml(cell)}</th>`).join("")}</tr></thead><tbody>${rows.slice(1).map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function enableViewers() {
  document.querySelector("#threshold").addEventListener("input", drawCscan);
  document.querySelector("#point-size").addEventListener("input", drawPointCloud);
  document.querySelector("#reset-view").addEventListener("click", () => {
    scanTransform = { scale: 1, offsetX: 0, offsetY: 0 };
    drawCscan();
  });
  const scanCanvas = document.querySelector("#cscan-canvas");
  const cloudCanvas = document.querySelector("#point-cloud");
  let cloudDragging = false;
  let cloudLastX = 0;
  cloudCanvas.addEventListener("mousedown", (event) => { cloudDragging = true; cloudLastX = event.clientX; });
  cloudCanvas.addEventListener("mouseup", () => { cloudDragging = false; });
  cloudCanvas.addEventListener("mouseleave", () => { cloudDragging = false; });
  cloudCanvas.addEventListener("mousemove", (event) => {
    if (!cloudDragging) return;
    cloudTransform.rotation += (event.clientX - cloudLastX) * 0.01;
    cloudLastX = event.clientX;
    drawPointCloud();
  });
  cloudCanvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    cloudTransform.scale = Math.max(0.5, Math.min(3, cloudTransform.scale * (event.deltaY < 0 ? 1.1 : 0.9)));
    drawPointCloud();
  }, { passive: false });
  scanCanvas.addEventListener("mousemove", (event) => {
    if (!inspectionPoints.length) return;
    const rect = scanCanvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const nearest = inspectionPoints.reduce((best, point) => {
      const position = canvasPoint(scanCanvas, point);
      const distance = (position.x - x) ** 2 + (position.y - y) ** 2;
      return distance < best.distance ? { point, distance } : best;
    }, { point: inspectionPoints[0], distance: Infinity }).point;
    document.querySelector("#scan-coordinates").textContent = `X = ${nearest[0]} · Y = ${nearest[1]} · Signal = ${nearest[2]}`;
  });
  let dragging = false;
  let lastX = 0;
  scanCanvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    scanTransform.scale = Math.max(1, Math.min(4, scanTransform.scale * (event.deltaY < 0 ? 1.1 : 0.9)));
    drawCscan();
  }, { passive: false });
  scanCanvas.addEventListener("mousedown", (event) => { dragging = true; lastX = event.clientX; });
  scanCanvas.addEventListener("mouseup", () => { dragging = false; });
  scanCanvas.addEventListener("mouseleave", () => { dragging = false; });
  scanCanvas.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    scanTransform.offsetX += event.clientX - lastX;
    lastX = event.clientX;
    drawCscan();
  });
}

enableViewers();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.textContent = "Validating and processing uploaded inspection data...";
  const result = document.querySelector("#result");
  result.classList.add("hidden");
  try {
    const response = await fetch("/api/generate-cscan", { method: "POST", body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Generation failed.");
    const details = data.details;
    inspectionPoints = details.visualization.inspection_points;
    geometryPoints = details.visualization.geometry_points;
    scanBounds = details.cscan.bounds;
    document.querySelector("#cscan").src = data.cscan_url;
    document.querySelector("#download").href = data.cscan_url;
    document.querySelector("#coverage-download").href = `/api/results/${data.result_id}/coverage`;
    document.querySelector("#coverage").src = `/api/results/${data.result_id}/coverage`;
    document.querySelector("#metadata-download").href = `/api/results/${data.result_id}/metadata`;
    document.querySelector("#indications-download").href = `/api/results/${data.result_id}/indications.csv`;
    document.querySelector("#report-download").href = `/api/results/${data.result_id}/report.html`;
    document.querySelector("#out-plate").textContent = details.plate_id;
    document.querySelector("#out-material").textContent = data.material;
    document.querySelector("#out-thickness").textContent = `${data.thickness} mm`;
    document.querySelector("#out-quality").textContent = `${details.data_quality.score}/100`;
    document.querySelector("#out-indications").textContent = details.potential_indications.length;
    document.querySelector("#out-coverage").textContent = `${Math.round(details.cscan.coverage_ratio * 100)}% measured grid cells`;
    const validation = details.inspection_validation;
    document.querySelector("#validation").innerHTML = Object.entries(validation).map(([name, passed]) => `<div class="${passed ? "passed" : "unavailable"}">${passed ? "✓" : "○"} ${escapeHtml(name.replaceAll("_", " "))}</div>`).join("");
    const capabilities = details.capabilities;
    document.querySelector("#capabilities").innerHTML = `<h3>Analysis availability</h3><ul><li>3D geometry: ${capabilities.three_d_geometry ? "Available" : "Unavailable — no PLY supplied"}</li><li>Depth-resolved analysis: ${capabilities.depth_analysis ? "Available" : "Unavailable — no depth field detected"}</li><li>A-scan: ${capabilities.a_scan ? "Available" : "Unavailable — no signal-vs-time/depth series detected"}</li><li>B-scan: ${capabilities.b_scan ? "Available" : "Unavailable — no line/depth series detected"}</li><li>ML prediction: ${capabilities.ml_prediction ? "Available" : "Unavailable — no validated labelled training set supplied"}</li><li>Reference comparison: Unavailable — no reference C-scan supplied</li><li>Surface registration: Unavailable — no coordinate mapping supplied</li></ul>`;
    const largest = details.potential_indications[0];
    document.querySelector("#explanation").innerHTML = `<h3>Inspection summary</h3><p>${details.potential_indications.length} candidate abnormal region(s) identified. ${largest ? `Largest region centred at X = ${largest.x}, Y = ${largest.y}, with estimated area ${largest.area} mm².` : "No high-response candidate region was identified."} Results are based on computed relative signal response and require appropriate NDT validation.</p>`;
    document.querySelector("#defect-list").innerHTML = details.potential_indications.length
      ? `<h3>Potential damage indications</h3><div class="table-wrap"><table><thead><tr><th>Region</th><th>X</th><th>Y</th><th>Area</th><th>Severity</th></tr></thead><tbody>${details.potential_indications.map((region, index) => `<tr><td>R${index + 1}</td><td>${region.x}</td><td>${region.y}</td><td>${region.area} mm²</td><td>${region.severity}</td></tr>`).join("")}</tbody></table></div>`
      : "<p>No potential high-response regions were identified by the analytical threshold.</p>";
    if (data.surface_image_url) {
      document.querySelector("#surface").src = data.surface_image_url;
      document.querySelector("#surface-wrap").classList.remove("hidden");
    }
    const [metadataResponse, indicationsResponse] = await Promise.all([
      fetch(`/api/results/${data.result_id}/metadata`),
      fetch(`/api/results/${data.result_id}/indications.csv`),
    ]);
    document.querySelector("#metadata-viewer").textContent = JSON.stringify(await metadataResponse.json(), null, 2);
    document.querySelector("#indications-viewer").innerHTML = renderIndicationsCsv(await indicationsResponse.text());
    document.querySelector("#report-viewer").src = `/api/results/${data.result_id}/report.html?inline=true`;
    result.classList.remove("hidden");
    drawCscan();
    drawPointCloud();
    status.textContent = "Inspection processed successfully. Unsupported analysis modes are marked unavailable.";
  } catch (error) {
    status.textContent = error.message;
  }
});
