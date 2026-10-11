// AEREO Geospatial Measurement Dashboard Controller

let currentMap = null;
let currentGeojsonLayer = null;
let activeFileId = null;
let activeMeasurementsData = null;

document.addEventListener("DOMContentLoaded", () => {
  initDropzone();
  initTabs();
  initSampleButtons();
  loadFileList();

  document.getElementById("btnRefreshList").addEventListener("click", loadFileList);
  document.getElementById("btnDeleteActive").addEventListener("click", deleteActiveFile);
  document.getElementById("btnDownloadJson").addEventListener("click", downloadJson);
});

// ----------------------------------------------------------------------------
// Dropzone & File Upload
// ----------------------------------------------------------------------------
function initDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });
}

async function handleFileUpload(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (ext !== "zip" && ext !== "kml") {
    alert("Invalid file format. Please upload a .zip (Shapefile) or .kml file.");
    return;
  }

  const progressBar = document.getElementById("uploadProgress");
  progressBar.classList.remove("hidden");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/files/", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to upload file");
    }

    const data = await res.json();
    await loadFileList();
    await selectFile(data.id);
  } catch (error) {
    alert(`Upload Error: ${error.message}`);
  } finally {
    progressBar.classList.add("hidden");
    document.getElementById("fileInput").value = "";
  }
}

// ----------------------------------------------------------------------------
// File List
// ----------------------------------------------------------------------------
async function loadFileList() {
  const listEl = document.getElementById("fileList");
  try {
    const res = await fetch("/api/files/");
    if (!res.ok) return;
    const files = await res.json();

    if (files.length === 0) {
      listEl.innerHTML = `<div class="empty-state">No files uploaded yet.</div>`;
      return;
    }

    listEl.innerHTML = files.map(f => `
      <div class="file-item ${f.id === activeFileId ? 'active' : ''}" onclick="selectFile('${f.id}')">
        <div class="file-item-name" title="${f.filename}">${f.filename}</div>
        <div class="file-item-meta">
          <span>${f.feature_count} features</span>
          <span style="text-transform:uppercase">${f.status}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error("Failed to load files list:", err);
  }
}

// ----------------------------------------------------------------------------
// File Selection & Data Visualization
// ----------------------------------------------------------------------------
async function selectFile(fileId) {
  activeFileId = fileId;
  document.getElementById("noSelectionState").classList.add("hidden");
  document.getElementById("activeDashboard").classList.remove("hidden");

  // Highlight in sidebar
  document.querySelectorAll(".file-item").forEach(item => {
    item.classList.remove("active");
  });
  loadFileList();

  try {
    // Fetch file details, measurements, and geojson
    const [fileRes, measRes, geoRes] = await Promise.all([
      fetch(`/api/files/${fileId}/`),
      fetch(`/api/files/${fileId}/measurements/`),
      fetch(`/api/files/${fileId}/features/`)
    ]);

    const fileData = await fileRes.json();
    const measData = await measRes.json();
    const geoData = await geoRes.json();

    activeMeasurementsData = measData;

    renderFileMeta(fileData, measData);
    renderMeasurementsTable(measData.features);
    renderRawJson(measData);
    renderMap(geoData);

  } catch (err) {
    console.error("Error loading file data:", err);
    alert("Error loading file details.");
  }
}

function renderFileMeta(file, meas) {
  document.getElementById("activeFilename").innerText = file.filename;
  document.getElementById("activeFileId").innerText = file.id;
  document.getElementById("activeFeatureCount").innerText = file.feature_count;
  document.getElementById("activeSourceCrs").innerText = file.crs || "EPSG:4326";
  document.getElementById("activeProjectedCrs").innerText = file.projected_crs || "Not required / N/A";

  const badge = document.getElementById("activeStatusBadge");
  badge.innerText = file.status;
  badge.className = `status-badge ${file.status === "COMPLETED" ? "badge-success" : "badge-failed"}`;

  // KPI Cards
  const summary = meas.summary || {};
  const areaM2 = summary.total_area_sq_meters || 0;
  const areaHa = summary.total_area_hectares || 0;
  const areaKm2 = (areaM2 / 1000000).toFixed(4);

  document.getElementById("kpiAreaSqM").innerHTML = `${areaM2.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} <span class="kpi-unit">m²</span>`;
  document.getElementById("kpiAreaSub").innerText = `${areaHa.toLocaleString('en-US', { minimumFractionDigits: 4 })} ha · ${areaKm2} km²`;

  const lenM = summary.total_length_meters || 0;
  const lenKm = summary.total_length_km || 0;

  document.getElementById("kpiLengthM").innerHTML = `${lenM.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} <span class="kpi-unit">m</span>`;
  document.getElementById("kpiLengthSub").innerText = `${lenKm.toLocaleString('en-US', { minimumFractionDigits: 4 })} km`;

  if (file.projected_crs) {
    document.getElementById("kpiCrsStrategy").innerText = file.projected_crs.split(' ')[0];
    document.getElementById("kpiCrsSub").innerText = file.projected_crs;
  } else {
    document.getElementById("kpiCrsStrategy").innerText = "Standard Projection";
    document.getElementById("kpiCrsSub").innerText = "Point / Geographic geometries";
  }
}

function renderMeasurementsTable(features) {
  const tbody = document.getElementById("featuresTableBody");
  if (!features || features.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No features found in dataset.</td></tr>`;
    return;
  }

  tbody.innerHTML = features.map(f => {
    let measFormatted = '<span style="color: #94a3b8;">None (Point)</span>';
    if (f.measurement) {
      if (f.measurement.area) {
        measFormatted = `<strong>${f.measurement.area.square_meters.toLocaleString()} m²</strong> (${f.measurement.area.hectares} ha)`;
      } else if (f.measurement.length) {
        measFormatted = `<strong>${f.measurement.length.meters.toLocaleString()} m</strong> (${f.measurement.length.kilometers} km)`;
      }
    }

    const badgeClass = f.status === "CALCULATED" ? "badge-calc" : "badge-skip";
    const projCrs = f.projected_crs || '<span style="color: #94a3b8;">-</span>';

    return `
      <tr>
        <td><strong>#${f.feature_index + 1}</strong></td>
        <td>${escapeHtml(f.feature_name || `Feature #${f.feature_index + 1}`)}</td>
        <td><code>${f.geometry_type}</code></td>
        <td>${measFormatted}</td>
        <td><code style="font-size:0.75rem">${projCrs}</code></td>
        <td><span class="${badgeClass}">${f.status}</span></td>
      </tr>
    `;
  }).join('');
}

function renderRawJson(data) {
  document.getElementById("rawJsonContent").innerText = JSON.stringify(data, null, 2);
}

// ----------------------------------------------------------------------------
// Leaflet GIS Map Visualization
// ----------------------------------------------------------------------------
function renderMap(geoData) {
  if (!currentMap) {
    currentMap = L.map("map", { zoomControl: true });

    // Free OpenStreetMap layer (No API key required)
    const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    // Free Esri Satellite Imagery layer (Ideal for drone & mining geospatial data)
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    });

    // Default to OpenStreetMap
    osmLayer.addTo(currentMap);

    // Layer switcher control
    const baseMaps = {
      "OpenStreetMap (Streets)": osmLayer,
      "Satellite Imagery (Aerial)": satelliteLayer
    };
    L.control.layers(baseMaps).addTo(currentMap);
  }

  if (currentGeojsonLayer) {
    currentMap.removeLayer(currentGeojsonLayer);
  }

  if (!geoData.features || geoData.features.length === 0) {
    currentMap.setView([20, 78], 4);
    return;
  }

  currentGeojsonLayer = L.geoJSON(geoData, {
    style: (feature) => {
      const type = feature.geometry.type;
      if (type.includes("Polygon")) {
        return {
          color: "#2563eb",
          weight: 2,
          opacity: 0.9,
          fillColor: "#3b82f6",
          fillOpacity: 0.25
        };
      } else if (type.includes("LineString")) {
        return {
          color: "#059669",
          weight: 3.5,
          opacity: 0.85
        };
      }
    },
    pointToLayer: (feature, latlng) => {
      return L.circleMarker(latlng, {
        radius: 6,
        fillColor: "#d97706",
        color: "#ffffff",
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.9
      });
    },
    onEachFeature: (feature, layer) => {
      const p = feature.properties || {};
      let popupContent = `
        <div style="font-family: 'Inter', sans-serif; font-size: 13px; line-height: 1.5;">
          <h4 style="margin: 0 0 6px 0; font-size: 14px; font-weight: 600; color: #0f172a;">${escapeHtml(p._feature_name || 'Feature')}</h4>
          <p style="margin: 0 0 4px 0; color: #64748b;">Geometry: <strong>${p._geometry_type}</strong></p>
      `;

      if (p._area_sq_meters !== undefined) {
        popupContent += `<p style="margin: 0 0 4px 0; color: #2563eb;">Area: <strong>${p._area_sq_meters.toLocaleString()} m²</strong> (${p._area_hectares} ha)</p>`;
      }
      if (p._length_meters !== undefined) {
        popupContent += `<p style="margin: 0 0 4px 0; color: #059669;">Length: <strong>${p._length_meters.toLocaleString()} m</strong> (${p._length_km} km)</p>`;
      }

      popupContent += `</div>`;
      layer.bindPopup(popupContent);
    }
  }).addTo(currentMap);

  try {
    const bounds = currentGeojsonLayer.getBounds();
    if (bounds.isValid()) {
      currentMap.fitBounds(bounds, { padding: [40, 40] });
    }
  } catch (e) {
    currentMap.setView([20, 78], 5);
  }
}

// ----------------------------------------------------------------------------
// Tabs Navigation
// ----------------------------------------------------------------------------
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.dataset.tab;
      document.getElementById(targetId).classList.add("active");

      // Invalidate map size so Leaflet renders properly on tab switch
      if (targetId === "tabMap" && currentMap) {
        setTimeout(() => currentMap.invalidateSize(), 50);
      }
    });
  });
}

// ----------------------------------------------------------------------------
// Samples & Actions
// ----------------------------------------------------------------------------
function initSampleButtons() {
  document.getElementById("btnSampleKml").addEventListener("click", () => loadPreloadedSample("kml"));
  document.getElementById("btnSampleShp").addEventListener("click", () => loadPreloadedSample("shp"));
}

async function loadPreloadedSample(type) {
  try {
    const endpoint = type === "kml" ? "/api/samples/mining-pit.kml" : "/api/samples/corridor-survey.zip";
    const res = await fetch(endpoint);
    if (!res.ok) {
      alert("Sample files will be created in the sample_data directory.");
      return;
    }
    const blob = await res.blob();
    const filename = type === "kml" ? "sample_mining_pit.kml" : "sample_corridor_survey.zip";
    const file = new File([blob], filename, { type: blob.type });
    await handleFileUpload(file);
  } catch (err) {
    console.error("Error loading sample:", err);
  }
}

async function deleteActiveFile() {
  if (!activeFileId) return;
  if (!confirm("Are you sure you want to delete this file and its measurements?")) return;

  try {
    const res = await fetch(`/api/files/${activeFileId}/`, { method: "DELETE" });
    if (res.ok) {
      activeFileId = null;
      document.getElementById("activeDashboard").classList.add("hidden");
      document.getElementById("noSelectionState").classList.remove("hidden");
      loadFileList();
    }
  } catch (err) {
    alert("Failed to delete file.");
  }
}

function downloadJson() {
  if (!activeMeasurementsData) return;
  const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activeMeasurementsData, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute("href", jsonStr);
  downloadAnchor.setAttribute("download", `${activeMeasurementsData.filename}_measurements.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}

function escapeHtml(text) {
  if (!text) return "";
  return text.toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
