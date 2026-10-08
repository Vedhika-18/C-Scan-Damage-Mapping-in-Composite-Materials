const form = document.querySelector("#scan-form");
const status = document.querySelector("#status");
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.textContent = "Processing uploaded inspection data...";
  const result = document.querySelector("#result");
  result.classList.add("hidden");
  try {
    const response = await fetch("/api/generate-cscan", { method: "POST", body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Generation failed.");
    document.querySelector("#cscan").src = data.cscan_url;
    document.querySelector("#download").href = data.cscan_url;
    document.querySelector("#out-material").textContent = data.material;
    document.querySelector("#out-thickness").textContent = `${data.thickness} mm`;
    document.querySelector("#out-method").textContent = data.method;
    const cscan = data.details.cscan;
    document.querySelector("#out-signal").textContent = `${cscan.signal_min.toPrecision(4)} to ${cscan.signal_max.toPrecision(4)}`;
    if (data.surface_image_url) {
      document.querySelector("#surface").src = data.surface_image_url;
      document.querySelector("#surface-wrap").classList.remove("hidden");
    }
    result.classList.remove("hidden");
    status.textContent = "C-scan generated successfully.";
  } catch (error) {
    status.textContent = error.message;
  }
});
