const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const number = new Intl.NumberFormat("uk-UA");

const state = {
  hromadas: [], providers: [], metadata: {}, featureById: new Map(),
  selectedId: null, filtered: [], filteredIds: null, providerMarkers: [],
  layers: { boundaries: true, providers: true, distance: false },
};

const controls = {
  oblast: $("#oblast"), raion: $("#raion"), service: $("#service"),
  raionDistance: $("#raion-distance"), oblastDistance: $("#oblast-distance"),
  search: $("#candidate-search"), profile: $("#candidate-profile"),
  remoteness: $("#candidate-remoteness"), sort: $("#sort-candidates"),
  status: $("#map-status"),
};

const map = L.map("map", {
  zoomControl: false, minZoom: 5, maxZoom: 13, preferCanvas: true,
  zoomAnimation: false, fadeAnimation: false, markerZoomAnimation: false,
  maxBounds: [[43.2, 18.0], [53.2, 44.5]], maxBoundsViscosity: 1,
}).setView([48.6, 31.2], 6);
L.control.zoom({ position: "bottomleft" }).addTo(map);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18, attribution: "&copy; OpenStreetMap contributors",
  noWrap: true, detectRetina: false, updateWhenIdle: true,
  updateWhenZooming: false, keepBuffer: 4, crossOrigin: true,
}).addTo(map);

const communityLayer = L.geoJSON(null, {
  style: communityStyle,
  onEachFeature(feature, layer) {
    const p = feature.properties;
    layer.bindTooltip(
      `<strong>${escapeHtml(shortName(p.name))}</strong><br>${p.total} надавачів · ${formatDistance(p.distanceOblastKm)}`,
      { className: "community-tooltip", sticky: true },
    );
    layer.on("click", () => selectCommunity(p.id, true));
  },
});
const oblastLayer = L.geoJSON(null, { style: { color: "#123d39", weight: 1.45, opacity: 0.9, fillOpacity: 0 } });
const providerLayer = L.markerClusterGroup({
  chunkedLoading: true, chunkInterval: 100, showCoverageOnHover: false,
  maxClusterRadius: 42, spiderfyOnMaxZoom: true,
});
communityLayer.addTo(map);
providerLayer.addTo(map);
oblastLayer.addTo(map);

function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function shortName(name) {
  return String(name).replace(" територіальна громада", "").replace(" міська громада", "")
    .replace(" селищна громада", "").replace(" сільська громада", "");
}

function formatDistance(value) {
  return value == null ? "немає даних" : `${number.format(Math.round(value))} км`;
}

function distanceColor(value) {
  if (value == null) return "#d8d8d1";
  if (value >= 220) return "#b94f38";
  if (value >= 150) return "#d77545";
  if (value >= 90) return "#df9d58";
  if (value >= 45) return "#e7c97b";
  return "#dfe6b2";
}

function communityStyle(feature) {
  const p = feature.properties;
  const visible = state.filteredIds == null || state.filteredIds.has(p.id);
  const selected = p.id === state.selectedId;
  return {
    color: selected ? "#d14d35" : "#2b716a",
    weight: selected ? 3 : visible ? 0.75 : 0.35,
    opacity: selected ? 1 : visible ? 0.66 : 0.09,
    fillColor: state.layers.distance ? distanceColor(p.distanceOblastKm) : "#d5e5c6",
    fillOpacity: selected ? 0.18 : state.layers.distance && visible ? 0.27 : visible ? 0.018 : 0,
  };
}

function relevantProviderCount(item) {
  if (controls.service.value === "medical") return item.medical;
  if (controls.service.value === "social") return item.social;
  return item.total;
}

function densityMatches(item) {
  const count = relevantProviderCount(item);
  const density = $('input[name="density"]:checked').value;
  if (density === "low") return count <= 1;
  if (density === "mid") return count >= 2 && count <= 5;
  if (density === "high") return count >= 6;
  return true;
}

function quickFilterMatches(item) {
  const query = controls.search.value.trim().toLocaleLowerCase("uk");
  if (query) {
    const haystack = `${item.name} ${item.raion} ${item.oblast}`.toLocaleLowerCase("uk");
    if (!haystack.includes(query)) return false;
  }
  const profile = controls.profile.value;
  if (profile === "empty" && item.total !== 0) return false;
  if (profile === "noMedical" && item.medical !== 0) return false;
  if (profile === "noSocial" && item.social !== 0) return false;
  if (profile === "both" && (item.medical === 0 || item.social === 0)) return false;
  const remoteness = controls.remoteness.value;
  if (remoteness === "raion30" && (item.distanceRaionKm == null || item.distanceRaionKm < 30)) return false;
  if (remoteness === "raion60" && (item.distanceRaionKm == null || item.distanceRaionKm < 60)) return false;
  if (remoteness === "oblast100" && (item.distanceOblastKm == null || item.distanceOblastKm < 100)) return false;
  if (remoteness === "oblast150" && (item.distanceOblastKm == null || item.distanceOblastKm < 150)) return false;
  return true;
}

function applyFilters({ fit = false } = {}) {
  const oblast = controls.oblast.value;
  const raion = controls.raion.value;
  const minRaion = Number(controls.raionDistance.value);
  const minOblast = Number(controls.oblastDistance.value);
  state.filtered = state.hromadas.filter((item) => {
    if (oblast !== "all" && item.oblast !== oblast) return false;
    if (raion !== "all" && item.raion !== raion) return false;
    if (minRaion > 0 && (item.distanceRaionKm == null || item.distanceRaionKm < minRaion)) return false;
    if (minOblast > 0 && (item.distanceOblastKm == null || item.distanceOblastKm < minOblast)) return false;
    return densityMatches(item) && quickFilterMatches(item);
  });
  state.filteredIds = new Set(state.filtered.map((item) => item.id));
  communityLayer.setStyle(communityStyle);
  const providers = filteredProviders();
  renderProviders(providers); renderMetrics(); renderScatter(); renderTable();
  controls.status.textContent = `${number.format(state.filtered.length)} громад · ${number.format(providers.length)} надавачів`;
  if (fit) fitActiveTerritory();
}

function filteredProviders() {
  return state.providers.filter((provider) => {
    if (!state.filteredIds.has(provider.hromadaId)) return false;
    if (controls.service.value === "medical") return provider.medical;
    if (controls.service.value === "social") return provider.social;
    return true;
  });
}

function providerKind(provider) {
  if (provider.medical && provider.social) return "mixed";
  if (provider.medical) return "medical";
  if (provider.social) return "social";
  return "other";
}

function createProviderMarker(provider) {
  const kind = providerKind(provider);
  const icon = L.divIcon({
    className: "", html: `<span class="provider-marker provider-marker--${kind}" style="display:block;width:10px;height:10px"></span>`,
    iconSize: [10, 10], iconAnchor: [5, 5],
  });
  const marker = L.marker([provider.lat, provider.lon], { icon, keyboard: true });
  const hromada = state.featureById.get(provider.hromadaId)?.properties;
  marker.bindPopup(
    `<strong>${escapeHtml(provider.name)}</strong><br><span>${escapeHtml(hromada ? shortName(hromada.name) : "")}</span><br>` +
    `<small>${provider.medical ? "Медичний" : ""}${provider.medical && provider.social ? " + " : ""}${provider.social ? "Соціальний" : ""}</small><br>` +
    `<small>Точка наближена в межах громади</small>`,
  );
  return marker;
}

function renderProviders(providers = filteredProviders()) {
  providerLayer.clearLayers();
  if (!state.layers.providers) return;
  const markers = providers.map((provider) => state.providerMarkers[provider._markerIndex]);
  providerLayer.addLayers(markers);
}

function renderMetrics() {
  $("#metric-hromadas").textContent = number.format(state.filtered.length);
  $("#metric-empty").textContent = number.format(state.filtered.filter((item) => relevantProviderCount(item) === 0).length);
  $("#metric-medical").textContent = number.format(state.filtered.reduce((sum, item) => sum + item.medical, 0));
  $("#metric-social").textContent = number.format(state.filtered.reduce((sum, item) => sum + item.social, 0));
}

function sortCandidates(items) {
  const sorted = [...items];
  const safe = (value) => value == null ? -1 : value;
  if (controls.sort.value === "raionDistanceDesc") sorted.sort((a, b) => safe(b.distanceRaionKm) - safe(a.distanceRaionKm));
  else if (controls.sort.value === "providersAsc") sorted.sort((a, b) => relevantProviderCount(a) - relevantProviderCount(b) || safe(b.distanceOblastKm) - safe(a.distanceOblastKm));
  else if (controls.sort.value === "providersDesc") sorted.sort((a, b) => relevantProviderCount(b) - relevantProviderCount(a) || safe(b.distanceOblastKm) - safe(a.distanceOblastKm));
  else if (controls.sort.value === "nameAsc") sorted.sort((a, b) => shortName(a.name).localeCompare(shortName(b.name), "uk"));
  else sorted.sort((a, b) => safe(b.distanceOblastKm) - safe(a.distanceOblastKm));
  return sorted;
}

function renderTable() {
  const rows = sortCandidates(state.filtered).slice(0, 200);
  $("#candidate-rows").innerHTML = rows.map((item) => `
    <tr data-id="${item.id}" class="${item.id === state.selectedId ? "is-selected" : ""}">
      <td><span class="candidate-name">${escapeHtml(shortName(item.name))}</span><span class="candidate-place">${escapeHtml(item.raion)} · ${escapeHtml(item.oblast)}</span></td>
      <td>${number.format(item.total)}</td><td>${number.format(item.medical)}</td><td>${number.format(item.social)}</td>
      <td class="${item.distanceRaionKm == null ? "distance-missing" : ""}">${formatDistance(item.distanceRaionKm)}</td>
      <td class="${item.distanceOblastKm == null ? "distance-missing" : ""}">${formatDistance(item.distanceOblastKm)}</td>
    </tr>`).join("");
  $("#table-footnote").textContent = state.filtered.length > 200
    ? `Показано перші 200 із ${number.format(state.filtered.length)} громад. CSV містить повний відфільтрований список.`
    : `Показано всі ${number.format(state.filtered.length)} громад за активними фільтрами.`;
  $$("#candidate-rows tr").forEach((row) => row.addEventListener("click", () => selectCommunity(row.dataset.id, true)));
}

function renderScatter() {
  const items = state.filtered.filter((item) => item.distanceOblastKm != null);
  if (!items.length) {
    $("#scatter").innerHTML = '<p class="table-footnote">Немає громад із доступними відстанями за цими фільтрами.</p>';
    return;
  }
  const width = 520, height = 330, margin = { top: 14, right: 16, bottom: 38, left: 42 };
  const maxX = Math.max(50, ...items.map((item) => item.distanceOblastKm));
  const valuesY = items.map(relevantProviderCount).sort((a, b) => a - b);
  const maxY = Math.max(5, valuesY[Math.floor(valuesY.length * .95)] || 1);
  const x = (value) => margin.left + (value / maxX) * (width - margin.left - margin.right);
  const y = (value) => height - margin.bottom - (Math.min(value, maxY) / maxY) * (height - margin.top - margin.bottom);
  const ticksX = [0, .25, .5, .75, 1].map((fraction) => Math.round(maxX * fraction));
  const ticksY = [0, .25, .5, .75, 1].map((fraction) => Math.round(maxY * fraction));
  const gridX = ticksX.map((tick) => `<line class="grid" x1="${x(tick)}" y1="${margin.top}" x2="${x(tick)}" y2="${height - margin.bottom}"/><text x="${x(tick)}" y="${height - 19}" text-anchor="middle">${tick}</text>`).join("");
  const gridY = ticksY.map((tick) => `<line class="grid" x1="${margin.left}" y1="${y(tick)}" x2="${width - margin.right}" y2="${y(tick)}"/><text x="${margin.left - 8}" y="${y(tick) + 3}" text-anchor="end">${tick}</text>`).join("");
  const points = items.map((item) => `<circle data-id="${item.id}" class="${item.id === state.selectedId ? "is-selected" : ""}" cx="${x(item.distanceOblastKm).toFixed(1)}" cy="${y(relevantProviderCount(item)).toFixed(1)}" r="3"><title>${escapeHtml(shortName(item.name))}: ${relevantProviderCount(item)} надавачів, ${formatDistance(item.distanceOblastKm)}</title></circle>`).join("");
  $("#scatter").innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">${gridX}${gridY}
    <line class="axis" x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" />
    <line class="axis" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" />${points}
    <text x="${(width + margin.left - margin.right) / 2}" y="${height - 3}" text-anchor="middle">до обласного центру, км</text>
    <text transform="translate(10 ${(height - margin.bottom + margin.top) / 2}) rotate(-90)" text-anchor="middle">надавачі</text></svg>`;
  $$("#scatter circle").forEach((point) => point.addEventListener("click", () => selectCommunity(point.dataset.id, true)));
}

function selectCommunity(id, pan = false) {
  const feature = state.featureById.get(id);
  if (!feature) return;
  state.selectedId = id;
  const item = feature.properties;
  $("#community-card").hidden = false;
  $("#community-name").textContent = shortName(item.name);
  $("#community-place").textContent = `${item.raion} · ${item.oblast}`;
  $("#community-total").textContent = number.format(item.total);
  $("#community-medical").textContent = number.format(item.medical);
  $("#community-social").textContent = number.format(item.social);
  $("#community-raion-distance").textContent = formatDistance(item.distanceRaionKm);
  $("#community-oblast-distance").textContent = formatDistance(item.distanceOblastKm);
  $("#community-centre").textContent = item.centre || "немає даних";
  $("#community-method").textContent = item.distanceSource === "KSE Loc Data Hub"
    ? "Відстань по прямій між координатами адміністративних центрів. Координати: KSE Loc Data Hub."
    : "Надійних координат адміністративного центру в джерелі немає; відстань не використовується у фільтрах.";
  communityLayer.setStyle(communityStyle); renderTable(); renderScatter();
  if (pan) {
    const layer = [...communityLayer.getLayers()].find((candidate) => candidate.feature.properties.id === id);
    if (layer) map.fitBounds(layer.getBounds(), { padding: [60, 60], maxZoom: 9 });
  }
}

function updateRaions() {
  const selectedOblast = controls.oblast.value;
  const previous = controls.raion.value;
  const raions = [...new Set(state.hromadas.filter((item) => selectedOblast === "all" || item.oblast === selectedOblast)
    .map((item) => item.raion).filter(Boolean))].sort((a, b) => a.localeCompare(b, "uk"));
  controls.raion.innerHTML = '<option value="all">Усі райони</option>' + raions.map((raion) => `<option value="${escapeHtml(raion)}">${escapeHtml(raion)}</option>`).join("");
  controls.raion.disabled = selectedOblast === "all";
  controls.raion.value = raions.includes(previous) ? previous : "all";
}

function fitActiveTerritory() {
  if (controls.oblast.value === "all") {
    const bounds = oblastLayer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [18, 18] });
    return;
  }
  const layers = communityLayer.getLayers().filter((layer) => layer.feature.properties.oblast === controls.oblast.value);
  if (layers.length) {
    const bounds = layers.reduce((result, layer) => result.extend(layer.getBounds()), L.latLngBounds());
    map.fitBounds(bounds, { padding: [28, 28] });
  }
}

function toggleLayer(button) {
  const key = button.dataset.layer;
  state.layers[key] = !state.layers[key];
  button.classList.toggle("is-active", state.layers[key]);
  button.setAttribute("aria-pressed", String(state.layers[key]));
  if (key === "boundaries") {
    if (state.layers.boundaries) communityLayer.addTo(map); else map.removeLayer(communityLayer);
  } else if (key === "providers") {
    if (state.layers.providers) providerLayer.addTo(map); else map.removeLayer(providerLayer);
    renderProviders();
  } else communityLayer.setStyle(communityStyle);
  oblastLayer.bringToFront();
}

function exportCsv() {
  const header = ["Громада", "Район", "Область", "Надавачі", "Медичні", "Соціальні", "До районного центру, км", "До обласного центру, км", "Адміністративний центр", "КАТОТТГ"];
  const cell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const rows = sortCandidates(state.filtered).map((item) => [shortName(item.name), item.raion, item.oblast, item.total, item.medical, item.social, item.distanceRaionKm, item.distanceOblastKm, item.centre, item.katottg]);
  const csv = `\ufeff${[header, ...rows].map((row) => row.map(cell).join(",")).join("\r\n")}`;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  link.download = "rehab_hromada_candidates.csv"; link.click(); URL.revokeObjectURL(link.href);
}

function bindControls() {
  controls.oblast.addEventListener("change", () => { updateRaions(); applyFilters({ fit: true }); });
  controls.raion.addEventListener("change", () => applyFilters({ fit: true }));
  controls.service.addEventListener("change", () => applyFilters());
  controls.search.addEventListener("input", scheduleFilters);
  controls.profile.addEventListener("change", () => applyFilters());
  controls.remoteness.addEventListener("change", () => applyFilters());
  controls.sort.addEventListener("change", renderTable);
  for (const input of $$('input[name="density"]')) input.addEventListener("change", () => applyFilters());
  for (const range of [controls.raionDistance, controls.oblastDistance]) {
    const output = $(`#${range.id}-value`);
    range.addEventListener("input", () => { output.textContent = `від ${range.value} км`; scheduleFilters(); });
  }
  $("#reset-filters").addEventListener("click", () => {
    controls.oblast.value = "all"; controls.raion.value = "all"; controls.service.value = "all";
    controls.search.value = ""; controls.profile.value = "all"; controls.remoteness.value = "all";
    controls.raionDistance.value = 0; controls.oblastDistance.value = 0;
    $("#raion-distance-value").textContent = "від 0 км"; $("#oblast-distance-value").textContent = "від 0 км";
    $('input[name="density"][value="all"]').checked = true;
    updateRaions(); applyFilters({ fit: true });
  });
  $$(".layer-button").forEach((button) => button.addEventListener("click", () => toggleLayer(button)));
  $("#close-community").addEventListener("click", () => {
    state.selectedId = null; $("#community-card").hidden = true;
    communityLayer.setStyle(communityStyle); renderTable(); renderScatter();
  });
  $("#export-csv").addEventListener("click", exportCsv);
}

let filterTimer;
function scheduleFilters() {
  window.clearTimeout(filterTimer);
  filterTimer = window.setTimeout(() => applyFilters(), 120);
}

async function initialise() {
  try {
    const responses = await Promise.all([
      fetch("./data/hromadas.geojson"), fetch("./data/providers.json"),
      fetch("./data/oblasts.geojson"), fetch("./data/metadata.json"),
    ]);
    if (!responses.every((response) => response.ok)) throw new Error("Частина даних недоступна");
    const [hromadaGeo, providers, oblastGeo, metadata] = await Promise.all(responses.map((response) => response.json()));
    state.hromadas = hromadaGeo.features.map((feature) => feature.properties);
    state.providers = providers.map((provider, index) => ({ ...provider, _markerIndex: index }));
    state.metadata = metadata;
    state.featureById = new Map(hromadaGeo.features.map((feature) => [feature.properties.id, feature]));
    state.providerMarkers = state.providers.map(createProviderMarker);
    communityLayer.addData(hromadaGeo); oblastLayer.addData(oblastGeo);
    const oblasts = [...new Set(state.hromadas.map((item) => item.oblast))].sort((a, b) => a.localeCompare(b, "uk"));
    controls.oblast.innerHTML = '<option value="all">Вся Україна</option>' + oblasts.map((oblast) => `<option value="${escapeHtml(oblast)}">${escapeHtml(oblast === "Київ" ? "Київ — місто" : oblast)}</option>`).join("");
    updateRaions(); bindControls(); applyFilters({ fit: true }); oblastLayer.bringToFront();
    window.requestAnimationFrame(() => map.invalidateSize(false));
  } catch (error) {
    console.error(error); controls.status.textContent = "Не вдалося завантажити dashboard";
    controls.status.style.background = "#a64235";
    $("#table-footnote").textContent = "Спробуйте перезавантажити сторінку. Якщо проблема повторюється, перевірте останню збірку даних.";
  }
}

const mapResizeObserver = new ResizeObserver(() => map.invalidateSize(false));
mapResizeObserver.observe($("#map"));

initialise();
