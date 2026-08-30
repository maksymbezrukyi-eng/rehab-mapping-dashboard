const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const I18N = {
  uk: {
    identitySubtitle: "аналіз громад України",
    homeLabel: "На початок сторінки", languageLabel: "Мова інтерфейсу", mapFiltersLabel: "Фільтри карти",
    mapAnalyticsLabel: "Карта та аналітика", metricsLabel: "Результати активних фільтрів",
    mapLayersLabel: "Шари карти", candidateFiltersLabel: "Швидкі фільтри кандидатів",
    purpose: "Робочий простір для порівняння громад за насиченістю послугами та віддаленістю від адміністративних центрів.",
    oblastLabel: "Область", raionLabel: "Район", serviceLabel: "Послуги",
    serviceAll: "Усі надавачі", medical: "Медичні", social: "Соціальні", all: "Усі",
    densityLabel: "Насиченість надавачами", toRaion: "До районного центру",
    toOblast: "До обласного центру", reset: "Скинути фільтри",
    methodTitle: "Методика", methodText: "Відстані рахуються по прямій між адміністративними центрами. Джерело та точність показуються в картці кожної громади.",
    metricHromadas: "Громад за активними фільтрами", metricEmpty: "Без надавачів у цьому списку",
    metricMedical: "Медичних надавачів у цьому списку", metricSocial: "Соціальних надавачів у цьому списку",
    boundaries: "Межі", providers: "Надавачі", remoteness: "Віддаленість", hromada: "Громада",
    allProviders: "усі надавачі", medicalLower: "медичні", socialLower: "соціальні",
    administrativeCentre: "Адміністративний центр", hromadaBoundary: "межа громади",
    accessProfile: "Профіль доступності", servicesAndDistance: "Послуги та віддаленість",
    chartHint: "Кожна точка — громада. Праворуч — далі від обласного центру; вище — більше надавачів.",
    filteredHromadas: "Громади за фільтрами", candidates: "Кандидати для аналізу", search: "Пошук",
    searchPlaceholder: "Назва громади, район або область", serviceProfile: "Профіль послуг",
    anyProfile: "Будь-який профіль", withoutProviders: "Без надавачів", withoutMedical: "Без медичних",
    withoutSocial: "Без соціальних", bothTypes: "Є медичні й соціальні", anyDistance: "Будь-яка відстань",
    raion30: "30+ км до райцентру", raion60: "60+ км до райцентру", oblast100: "100+ км до облцентру",
    oblast150: "150+ км до облцентру", sort: "Сортувати", sortOblast: "Віддалені від області",
    sortRaion: "Віддалені від району", sortFewer: "Менше надавачів", sortMore: "Більше надавачів",
    sortName: "За назвою", downloadCsv: "Завантажити CSV", medicalShort: "Мед.", socialShort: "Соц.",
    toRaionShort: "До району", toOblastShort: "До області", allUkraine: "Вся Україна",
    allRaions: "Усі райони", kyivCity: "Київ — місто", fromKm: "від {value} км", km: "км",
    noData: "немає даних", loading: "Завантажуємо дані…", closeCard: "Закрити картку",
    mapLabel: "Інтерактивна карта України", scatterLabel: "Графік кількості надавачів та віддаленості",
    status: "{hromadas} громад · {providers} надавачів", providerCount: "{count} надавачів",
    medicalProvider: "Медичний", socialProvider: "Соціальний", approximatePoint: "Точка наближена в межах громади",
    allRows: "Показано всі {count} громад за активними фільтрами.",
    limitedRows: "Показано перші 200 із {count} громад. CSV містить повний відфільтрований список.",
    noDistanceRows: "Немає громад із доступними відстанями за цими фільтрами.",
    oblastAxis: "до обласного центру, км", providersAxis: "надавачі",
    pointTitle: "{name}: {count} надавачів, {distance}",
    distanceMethod: "Відстань по прямій між координатами адміністративних центрів. Координати: KSE Loc Data Hub.",
    missingDistanceMethod: "Надійних координат адміністративного центру в джерелі немає; відстань не використовується у фільтрах.",
    csvHromada: "Громада", csvRaion: "Район", csvOblast: "Область", csvProviders: "Надавачі",
    csvMedical: "Медичні", csvSocial: "Соціальні", csvRaionDistance: "До районного центру, км",
    csvOblastDistance: "До обласного центру, км", csvCentre: "Адміністративний центр",
    loadError: "Не вдалося завантажити dashboard",
    loadErrorHint: "Спробуйте перезавантажити сторінку. Якщо проблема повторюється, перевірте останню збірку даних.",
  },
  en: {
    identitySubtitle: "analysis of Ukrainian hromadas",
    homeLabel: "Go to the top", languageLabel: "Interface language", mapFiltersLabel: "Map filters",
    mapAnalyticsLabel: "Map and analysis", metricsLabel: "Results of active filters",
    mapLayersLabel: "Map layers", candidateFiltersLabel: "Quick candidate filters",
    purpose: "A workspace for comparing hromadas by service availability and distance from administrative centres.",
    oblastLabel: "Oblast", raionLabel: "Raion", serviceLabel: "Services",
    serviceAll: "All providers", medical: "Medical", social: "Social", all: "All",
    densityLabel: "Provider availability", toRaion: "Distance to raion centre",
    toOblast: "Distance to oblast centre", reset: "Reset filters",
    methodTitle: "Method", methodText: "Distances are straight-line measurements between administrative centres. The source and precision are shown in each hromada card.",
    metricHromadas: "Hromadas matching active filters", metricEmpty: "Without providers in this list",
    metricMedical: "Medical providers in this list", metricSocial: "Social providers in this list",
    boundaries: "Boundaries", providers: "Providers", remoteness: "Remoteness", hromada: "Hromada",
    allProviders: "all providers", medicalLower: "medical", socialLower: "social",
    administrativeCentre: "Administrative centre", hromadaBoundary: "hromada boundary",
    accessProfile: "Access profile", servicesAndDistance: "Services and remoteness",
    chartHint: "Each dot is a hromada. Farther right means farther from the oblast centre; higher means more providers.",
    filteredHromadas: "Hromadas matching filters", candidates: "Candidates for analysis", search: "Search",
    searchPlaceholder: "Hromada, raion or oblast name", serviceProfile: "Service profile",
    anyProfile: "Any profile", withoutProviders: "Without providers", withoutMedical: "Without medical",
    withoutSocial: "Without social", bothTypes: "Medical and social available", anyDistance: "Any distance",
    raion30: "30+ km to raion centre", raion60: "60+ km to raion centre", oblast100: "100+ km to oblast centre",
    oblast150: "150+ km to oblast centre", sort: "Sort by", sortOblast: "Farthest from oblast centre",
    sortRaion: "Farthest from raion centre", sortFewer: "Fewer providers", sortMore: "More providers",
    sortName: "Name", downloadCsv: "Download CSV", medicalShort: "Med.", socialShort: "Soc.",
    toRaionShort: "To raion", toOblastShort: "To oblast", allUkraine: "All Ukraine",
    allRaions: "All raions", kyivCity: "Kyiv — city", fromKm: "from {value} km", km: "km",
    noData: "no data", loading: "Loading data…", closeCard: "Close card",
    mapLabel: "Interactive map of Ukraine", scatterLabel: "Provider count and remoteness chart",
    status: "{hromadas} hromadas · {providers} providers", providerCount: "{count} providers",
    medicalProvider: "Medical", socialProvider: "Social", approximatePoint: "Approximate point within the hromada",
    allRows: "Showing all {count} hromadas matching the active filters.",
    limitedRows: "Showing the first 200 of {count} hromadas. The CSV contains the full filtered list.",
    noDistanceRows: "No hromadas with available distances match these filters.",
    oblastAxis: "distance to oblast centre, km", providersAxis: "providers",
    pointTitle: "{name}: {count} providers, {distance}",
    distanceMethod: "Straight-line distance between administrative-centre coordinates. Coordinates: KSE Loc Data Hub.",
    missingDistanceMethod: "Reliable administrative-centre coordinates are unavailable; distance is not used in filters.",
    csvHromada: "Hromada", csvRaion: "Raion", csvOblast: "Oblast", csvProviders: "Providers",
    csvMedical: "Medical", csvSocial: "Social", csvRaionDistance: "Distance to raion centre, km",
    csvOblastDistance: "Distance to oblast centre, km", csvCentre: "Administrative centre",
    loadError: "Could not load the dashboard",
    loadErrorHint: "Reload the page. If the problem persists, check the latest data build.",
  },
};

let number = new Intl.NumberFormat("uk-UA");

function t(key, values = {}) {
  let value = I18N[state.lang]?.[key] ?? I18N.uk[key] ?? key;
  for (const [name, replacement] of Object.entries(values)) value = value.replaceAll(`{${name}}`, replacement);
  return value;
}

const state = {
  hromadas: [], providers: [], metadata: {}, featureById: new Map(),
  lang: "uk", selectedId: null, filtered: [], filteredIds: null, providerMarkers: [],
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
    layer.bindTooltip(communityTooltipContent(p), { className: "community-tooltip", sticky: true });
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
  return String(name)
    .replace(/ (територіальна|міська|селищна|сільська) громада$/i, "")
    .replace(/ (terytorialna|miska|selyshchna|silska) hromada$/i, "");
}

function localized(item, field) {
  return state.lang === "en" ? item[`${field}En`] || item[field] : item[field];
}

function displayHromada(item) {
  return shortName(localized(item, "name"));
}

function formatDistance(value) {
  return value == null ? t("noData") : `${number.format(Math.round(value))} ${t("km")}`;
}

function communityTooltipContent(item) {
  return `<strong>${escapeHtml(displayHromada(item))}</strong><br>${t("providerCount", { count: number.format(item.total) })} · ${formatDistance(item.distanceOblastKm)}`;
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
    const haystack = `${item.name} ${item.nameEn} ${item.raion} ${item.raionEn} ${item.oblast} ${item.oblastEn}`.toLocaleLowerCase(state.lang === "en" ? "en" : "uk");
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
  controls.status.textContent = t("status", {
    hromadas: number.format(state.filtered.length), providers: number.format(providers.length),
  });
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
    `<strong>${escapeHtml(provider.name)}</strong><br><span>${escapeHtml(hromada ? displayHromada(hromada) : "")}</span><br>` +
    `<small>${provider.medical ? t("medicalProvider") : ""}${provider.medical && provider.social ? " + " : ""}${provider.social ? t("socialProvider") : ""}</small><br>` +
    `<small>${t("approximatePoint")}</small>`,
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
  else if (controls.sort.value === "nameAsc") sorted.sort((a, b) => displayHromada(a).localeCompare(displayHromada(b), state.lang === "en" ? "en" : "uk"));
  else sorted.sort((a, b) => safe(b.distanceOblastKm) - safe(a.distanceOblastKm));
  return sorted;
}

function renderTable() {
  const rows = sortCandidates(state.filtered).slice(0, 200);
  $("#candidate-rows").innerHTML = rows.map((item) => `
    <tr data-id="${item.id}" class="${item.id === state.selectedId ? "is-selected" : ""}">
      <td><span class="candidate-name">${escapeHtml(displayHromada(item))}</span><span class="candidate-place">${escapeHtml(localized(item, "raion"))} · ${escapeHtml(localized(item, "oblast"))}</span></td>
      <td>${number.format(item.total)}</td><td>${number.format(item.medical)}</td><td>${number.format(item.social)}</td>
      <td class="${item.distanceRaionKm == null ? "distance-missing" : ""}">${formatDistance(item.distanceRaionKm)}</td>
      <td class="${item.distanceOblastKm == null ? "distance-missing" : ""}">${formatDistance(item.distanceOblastKm)}</td>
    </tr>`).join("");
  $("#table-footnote").textContent = state.filtered.length > 200
    ? t("limitedRows", { count: number.format(state.filtered.length) })
    : t("allRows", { count: number.format(state.filtered.length) });
  $$("#candidate-rows tr").forEach((row) => row.addEventListener("click", () => selectCommunity(row.dataset.id, true)));
}

function renderScatter() {
  const items = state.filtered.filter((item) => item.distanceOblastKm != null);
  if (!items.length) {
    $("#scatter").innerHTML = `<p class="table-footnote">${t("noDistanceRows")}</p>`;
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
  const points = items.map((item) => `<circle data-id="${item.id}" class="${item.id === state.selectedId ? "is-selected" : ""}" cx="${x(item.distanceOblastKm).toFixed(1)}" cy="${y(relevantProviderCount(item)).toFixed(1)}" r="3"><title>${t("pointTitle", { name: escapeHtml(displayHromada(item)), count: number.format(relevantProviderCount(item)), distance: formatDistance(item.distanceOblastKm) })}</title></circle>`).join("");
  $("#scatter").innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true">${gridX}${gridY}
    <line class="axis" x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" />
    <line class="axis" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" />${points}
    <text x="${(width + margin.left - margin.right) / 2}" y="${height - 3}" text-anchor="middle">${t("oblastAxis")}</text>
    <text transform="translate(10 ${(height - margin.bottom + margin.top) / 2}) rotate(-90)" text-anchor="middle">${t("providersAxis")}</text></svg>`;
  $$("#scatter circle").forEach((point) => point.addEventListener("click", () => selectCommunity(point.dataset.id, true)));
}

function selectCommunity(id, pan = false) {
  const feature = state.featureById.get(id);
  if (!feature) return;
  state.selectedId = id;
  const item = feature.properties;
  $("#community-card").hidden = false;
  $("#community-name").textContent = displayHromada(item);
  $("#community-place").textContent = `${localized(item, "raion")} · ${localized(item, "oblast")}`;
  $("#community-total").textContent = number.format(item.total);
  $("#community-medical").textContent = number.format(item.medical);
  $("#community-social").textContent = number.format(item.social);
  $("#community-raion-distance").textContent = formatDistance(item.distanceRaionKm);
  $("#community-oblast-distance").textContent = formatDistance(item.distanceOblastKm);
  $("#community-centre").textContent = localized(item, "centre") || t("noData");
  $("#community-method").textContent = item.distanceSource === "KSE Loc Data Hub"
    ? t("distanceMethod") : t("missingDistanceMethod");
  communityLayer.setStyle(communityStyle); renderTable(); renderScatter();
  if (pan) {
    const layer = [...communityLayer.getLayers()].find((candidate) => candidate.feature.properties.id === id);
    if (layer) map.fitBounds(layer.getBounds(), { padding: [60, 60], maxZoom: 9 });
  }
}

function populateOblastOptions() {
  const previous = controls.oblast.value || "all";
  const oblasts = [...new Set(state.hromadas.map((item) => item.oblast))].sort((a, b) => {
    const itemA = state.hromadas.find((item) => item.oblast === a);
    const itemB = state.hromadas.find((item) => item.oblast === b);
    return localized(itemA, "oblast").localeCompare(localized(itemB, "oblast"), state.lang === "en" ? "en" : "uk");
  });
  controls.oblast.innerHTML = `<option value="all">${t("allUkraine")}</option>` + oblasts.map((oblast) => {
    const item = state.hromadas.find((candidate) => candidate.oblast === oblast);
    const label = oblast === "Київ" ? t("kyivCity") : localized(item, "oblast");
    return `<option value="${escapeHtml(oblast)}">${escapeHtml(label)}</option>`;
  }).join("");
  controls.oblast.value = oblasts.includes(previous) ? previous : "all";
}

function updateRaions() {
  const selectedOblast = controls.oblast.value;
  const previous = controls.raion.value;
  const territory = state.hromadas.filter((item) => selectedOblast === "all" || item.oblast === selectedOblast);
  const raions = [...new Set(territory.map((item) => item.raion).filter(Boolean))].sort((a, b) => {
    const itemA = territory.find((item) => item.raion === a);
    const itemB = territory.find((item) => item.raion === b);
    return localized(itemA, "raion").localeCompare(localized(itemB, "raion"), state.lang === "en" ? "en" : "uk");
  });
  controls.raion.innerHTML = `<option value="all">${t("allRaions")}</option>` + raions.map((raion) => {
    const item = territory.find((candidate) => candidate.raion === raion);
    return `<option value="${escapeHtml(raion)}">${escapeHtml(localized(item, "raion"))}</option>`;
  }).join("");
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
  const header = [t("csvHromada"), t("csvRaion"), t("csvOblast"), t("csvProviders"), t("csvMedical"), t("csvSocial"), t("csvRaionDistance"), t("csvOblastDistance"), t("csvCentre"), "КАТОТТГ"];
  const cell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const rows = sortCandidates(state.filtered).map((item) => [displayHromada(item), localized(item, "raion"), localized(item, "oblast"), item.total, item.medical, item.social, item.distanceRaionKm, item.distanceOblastKm, localized(item, "centre"), item.katottg]);
  const csv = `\ufeff${[header, ...rows].map((row) => row.map(cell).join(",")).join("\r\n")}`;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  link.download = `rehab_hromada_candidates_${state.lang}.csv`; link.click(); URL.revokeObjectURL(link.href);
}

function bindControls() {
  controls.oblast.addEventListener("change", () => { updateRaions(); applyFilters({ fit: true }); });
  controls.raion.addEventListener("change", () => applyFilters({ fit: true }));
  controls.service.addEventListener("change", () => applyFilters());
  controls.search.addEventListener("input", scheduleFilters);
  controls.profile.addEventListener("change", () => applyFilters());
  controls.remoteness.addEventListener("change", () => applyFilters());
  controls.sort.addEventListener("change", renderTable);
  $$("[data-language]").forEach((button) => button.addEventListener("click", () => setLanguage(button.dataset.language)));
  for (const input of $$('input[name="density"]')) input.addEventListener("change", () => applyFilters());
  for (const range of [controls.raionDistance, controls.oblastDistance]) {
    const output = $(`#${range.id}-value`);
    range.addEventListener("input", () => { output.textContent = t("fromKm", { value: range.value }); scheduleFilters(); });
  }
  $("#reset-filters").addEventListener("click", () => {
    controls.oblast.value = "all"; controls.raion.value = "all"; controls.service.value = "all";
    controls.search.value = ""; controls.profile.value = "all"; controls.remoteness.value = "all";
    controls.raionDistance.value = 0; controls.oblastDistance.value = 0;
    $("#raion-distance-value").textContent = t("fromKm", { value: 0 });
    $("#oblast-distance-value").textContent = t("fromKm", { value: 0 });
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

function translateStaticUi() {
  document.documentElement.lang = state.lang;
  $$('[data-i18n]').forEach((element) => { element.textContent = t(element.dataset.i18n); });
  $$('[data-i18n-placeholder]').forEach((element) => { element.placeholder = t(element.dataset.i18nPlaceholder); });
  $$('[data-i18n-aria]').forEach((element) => { element.setAttribute("aria-label", t(element.dataset.i18nAria)); });
  $$("[data-language]").forEach((button) => {
    const active = button.dataset.language === state.lang;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $("#raion-distance-value").textContent = t("fromKm", { value: controls.raionDistance.value });
  $("#oblast-distance-value").textContent = t("fromKm", { value: controls.oblastDistance.value });
  $("#map").setAttribute("aria-label", t("mapLabel"));
  $("#scatter").setAttribute("aria-label", t("scatterLabel"));
  $("#close-community").setAttribute("aria-label", t("closeCard"));
  document.title = state.lang === "uk" ? "Rehab Access Map — громади України" : "Rehab Access Map — hromadas of Ukraine";
}

function setLanguage(lang, { persist = true } = {}) {
  if (!I18N[lang]) return;
  state.lang = lang;
  number = new Intl.NumberFormat(lang === "uk" ? "uk-UA" : "en-GB");
  if (persist) localStorage.setItem("rehab-dashboard-language", lang);
  translateStaticUi();
  if (!state.hromadas.length) {
    controls.status.textContent = t("loading");
    return;
  }
  populateOblastOptions();
  updateRaions();
  communityLayer.eachLayer((layer) => layer.setTooltipContent(communityTooltipContent(layer.feature.properties)));
  state.providerMarkers = state.providers.map(createProviderMarker);
  applyFilters();
  if (state.selectedId) selectCommunity(state.selectedId, false);
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
    populateOblastOptions();
    updateRaions(); bindControls(); applyFilters({ fit: true }); oblastLayer.bringToFront();
    window.requestAnimationFrame(() => map.invalidateSize(false));
  } catch (error) {
    console.error(error); controls.status.textContent = t("loadError");
    controls.status.style.background = "#a64235";
    $("#table-footnote").textContent = t("loadErrorHint");
  }
}

const mapResizeObserver = new ResizeObserver(() => map.invalidateSize(false));
mapResizeObserver.observe($("#map"));

const savedLanguage = localStorage.getItem("rehab-dashboard-language");
setLanguage(savedLanguage === "en" ? "en" : "uk", { persist: false });
initialise();
