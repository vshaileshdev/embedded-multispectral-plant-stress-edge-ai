// ==========================================
// LANDING PAGE TRANSITION CONTROLLER
// ==========================================
(function() {
    const landingPage = document.getElementById('landing-page');
    const dashboardWrapper = document.getElementById('dashboard-wrapper');
    const btnEnterDashboard = document.getElementById('btnEnterDashboard');

    let isTransitioning = false;
    let touchStartY = 0;

    function triggerTransition() {
        if (isTransitioning) return;
        isTransitioning = true;
        
        if (landingPage) {
            landingPage.classList.add('is-transitioning');
        }
        if (dashboardWrapper) {
            dashboardWrapper.classList.add('dashboard-visible');
        }
        document.body.classList.remove('landing-active');

        setTimeout(() => {
            if (landingPage) {
                landingPage.classList.add('is-hidden');
            }
        }, 1200);
    }

    if (btnEnterDashboard) {
        btnEnterDashboard.addEventListener('click', triggerTransition);
    }

    window.addEventListener('wheel', (e) => {
        if (!isTransitioning && landingPage && !landingPage.classList.contains('is-hidden')) {
            if (e.deltaY > 0) triggerTransition();
        }
    });

    window.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches.length > 0) {
            touchStartY = e.touches[0].clientY;
        }
    }, { passive: true });

    window.addEventListener('touchend', (e) => {
        if (!isTransitioning && landingPage && !landingPage.classList.contains('is-hidden')) {
            if (e.changedTouches && e.changedTouches.length > 0) {
                let touchEndY = e.changedTouches[0].clientY;
                if (touchStartY - touchEndY > 50) triggerTransition();
            }
        }
    });
})();

const API_BASE = '/api/v1';

// DOM Elements
const plantIdInput = document.getElementById('plantId');
const plantSpeciesSelect = document.getElementById('plantSpecies');
const plantProfileInfo = document.getElementById('plantProfileInfo');
const sensorProfileSelect = document.getElementById('sensorProfile');
const experimentalDaySelect = document.getElementById('experimentalDay');

const btnLoadDataset = document.getElementById('btnLoadDataset');
const btnDiagnose = document.getElementById('btnDiagnose');
const acquisitionStatus = document.getElementById('acquisitionStatus');
const spectrumInfoPanel = document.getElementById('spectrumInfoPanel');

const sectionFeatures = document.getElementById('section-features');
const featuresTableBody = document.querySelector('#featuresTable tbody');

const sectionResult = document.getElementById('section-result');
const resDiagnosis = document.getElementById('resDiagnosis');
const resConfidence = document.getElementById('resConfidence');
const classProbsContainer = document.getElementById('classProbsContainer');
const explainabilityContainer = document.getElementById('explainabilityContainer');
const resPotentialEffects = document.getElementById('resPotentialEffects');
const resRecommendation = document.getElementById('resRecommendation');

const btnRefreshHistory = document.getElementById('btnRefreshHistory');
const btnClearHistory = document.getElementById('btnClearHistory');
const historyTableBody = document.getElementById('historyTableBody');
const btnDownloadReport = document.getElementById('btnDownloadReport');
const btnDownloadProgressReport = document.getElementById('btnDownloadProgressReport');

// Info Modals
const infoModal = document.getElementById('infoModal');
const infoModalTitle = document.getElementById('infoModalTitle');
const infoModalText = document.getElementById('infoModalText');
const btnCloseModal = document.getElementById('btnCloseModal');

const btnSystemOverview = document.getElementById('btnSystemOverview');
const overviewModal = document.getElementById('overviewModal');
const btnCloseOverview = document.getElementById('btnCloseOverview');

const deleteModal = document.getElementById('deleteModal');
const btnCancelDelete = document.getElementById('btnCancelDelete');
const btnConfirmDelete = document.getElementById('btnConfirmDelete');
const deleteModalText = document.getElementById('deleteModalText');

// State
let plantProfiles = {};
let currentSpectrum = null;
let currentSampleId = null;
let chartInstance = null;
let timelineChartInstance = null;
let currentMeasurementId = null;

// Registered Plants State & Registry Management
let registeredPlants = [];
let activePlant = {
    plant_id: 'TOM-001',
    name: 'Tomato Alpha',
    species: 'tomato',
    cultivar: 'Standard Research',
    growth_stage: 'Vegetative',
    date_acquired: '2026-03-01',
    soil_type: 'Loam potting mix',
    soil_condition: 'Optimal (pH 6.5)',
    watering_regime: '150ml every 48h',
    nutrient_regime: 'Half-strength Hoagland solution',
    initial_condition: 'Healthy baseline',
    model_status: 'Active (v1.0.0)'
};
let viewedPlant = activePlant;

async function fetchPlants() {
    try {
        const response = await fetch(`${API_BASE}/plants`);
        if (response.ok) {
            const plants = await response.json();
            if (Array.isArray(plants) && plants.length > 0) {
                registeredPlants = plants;
            }
        }
    } catch (e) {
        console.error("Failed to load plants", e);
    }

    // If no plants in DB or TOM-001 missing, ensure TOM-001 is included
    const hasTom001 = registeredPlants.some(p => p.plant_id === 'TOM-001');
    if (!hasTom001) {
        registeredPlants.unshift(activePlant);
    }

    renderRegistryTable();
    updateRegisteredPlantsCount();
}

function renderRegistryTable() {
    const tbody = document.getElementById('registryTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    registeredPlants.forEach(p => {
        const tr = document.createElement('tr');
        const isCurrentActive = activePlant && activePlant.plant_id === p.plant_id;
        const modelBadge = p.species === 'tomato' 
            ? '<span style="color:#5A8252; font-weight:bold;">Active (v1.0.0)</span>' 
            : '<span style="color:#888;">Profile Ready</span>';
        
        tr.innerHTML = `
            <td><strong>${p.plant_id}</strong> ${isCurrentActive ? '<span style="background:var(--highlight); color:#2c3e2a; font-size:0.7rem; padding:2px 6px; border-radius:4px; margin-left:4px; font-weight:bold;">ACTIVE</span>' : ''}</td>
            <td>${p.name || p.species} <em>(${p.species})</em></td>
            <td>${p.cultivar || 'Standard'}</td>
            <td>${p.growth_stage || 'Vegetative'}</td>
            <td>${modelBadge}</td>
            <td>
                <button class="btn secondary" style="padding:4px 8px; font-size:0.8rem; margin-right:6px;" onclick="setActivePlantById('${p.plant_id}')">Select</button>
                <button class="btn" style="padding:4px 8px; font-size:0.8rem; background:var(--bg-light); color:var(--primary-dark);" onclick="viewPlantProfileById('${p.plant_id}')">View Profile</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateRegisteredPlantsCount() {
    const kpiEl = document.getElementById('kpiRegisteredPlants');
    if (kpiEl) kpiEl.textContent = registeredPlants.length;
}

function setActivePlantById(plantId) {
    const plant = registeredPlants.find(p => p.plant_id === plantId) || { plant_id: plantId, species: 'tomato', name: plantId };
    setActivePlant(plant);
}
window.setActivePlantById = setActivePlantById;

function setActivePlant(plant) {
    activePlant = plant;
    viewedPlant = plant;
    
    // Update header and dashboard labels
    const headerEl = document.getElementById('headerActivePlant');
    if (headerEl) headerEl.textContent = plant.plant_id;
    const kpiEl = document.getElementById('kpiActivePlant');
    if (kpiEl) kpiEl.textContent = plant.plant_id;
    const rawEl = document.getElementById('rawPlantId');
    if (rawEl) rawEl.textContent = plant.plant_id;
    const repEl = document.getElementById('reportActivePlantLabel');
    if (repEl) repEl.textContent = plant.plant_id;
    const repIdEl = document.getElementById('reportActivePlantId');
    if (repIdEl) repIdEl.textContent = plant.plant_id;
    if (plantIdInput) plantIdInput.value = plant.plant_id;

    if (plantSpeciesSelect && plant.species && plantSpeciesSelect.value !== plant.species) {
        plantSpeciesSelect.value = plant.species;
        onPlantChanged(false);
    }
    
    renderRegistryTable();
    updatePlantProfileView(plant);
    loadHistory(plant.plant_id);
}

function viewPlantProfileById(plantId) {
    const plant = registeredPlants.find(p => p.plant_id === plantId) || { plant_id: plantId, species: 'tomato', name: plantId };
    viewedPlant = plant;
    updatePlantProfileView(plant);
    navigateToWorkspace('ws-plant-profile');
}
window.viewPlantProfileById = viewPlantProfileById;

function updatePlantProfileView(plant) {
    const headerId = document.getElementById('profHeaderId');
    if (headerId) headerId.textContent = plant.plant_id;
    const pId = document.getElementById('profPlantId');
    if (pId) pId.textContent = plant.plant_id;
    const pName = document.getElementById('profName');
    if (pName) pName.textContent = plant.name || plant.plant_id;
    const pSpec = document.getElementById('profSpecies');
    if (pSpec) pSpec.textContent = plant.species === 'tomato' ? 'Tomato (Solanum lycopersicum)' : plant.species;
    const pCult = document.getElementById('profCultivar');
    if (pCult) pCult.textContent = plant.cultivar || 'Standard Variety';
    const pStage = document.getElementById('profGrowthStage');
    if (pStage) pStage.textContent = plant.growth_stage || 'Vegetative';
    const pDate = document.getElementById('profDateAcquired');
    if (pDate) pDate.textContent = plant.date_acquired || '2026-03-01';
    const pSoil = document.getElementById('profSoilType');
    if (pSoil) pSoil.textContent = plant.soil_type || 'Loam potting mix';
    const pSoilCond = document.getElementById('profSoilCondition');
    if (pSoilCond) pSoilCond.textContent = plant.soil_condition || `Optimal (pH ${plant.soil_ph || 6.5})`;
    const pWater = document.getElementById('profWatering');
    if (pWater) pWater.textContent = plant.watering_regime || '150ml every 48h';
    const pNutr = document.getElementById('profNutrients');
    if (pNutr) pNutr.textContent = plant.nutrient_regime || 'Half-strength Hoagland solution';
    const pInit = document.getElementById('profInitialCondition');
    if (pInit) pInit.textContent = plant.initial_condition || 'Healthy baseline';

    const pModel = document.getElementById('profModelStatus');
    if (pModel) {
        pModel.innerHTML = plant.species === 'tomato' 
            ? '<span style="color:#5A8252; font-weight:bold;">tomato_research_rf_v1.0.0 (Validated)</span>' 
            : '<span style="color:#888;">Profile Ready (Model validation pending)</span>';
    }
}

function setActivePlantFromProfile() {
    if (viewedPlant) {
        setActivePlant(viewedPlant);
        alert(`Specimen ${viewedPlant.plant_id} is now set as the active plant.`);
    }
}
window.setActivePlantFromProfile = setActivePlantFromProfile;

// Initialize
async function fetchProfiles() {
    try {
        const response = await fetch(`${API_BASE}/plants/profiles`);
        const data = await response.json();
        plantProfiles = data.profiles;
        
        plantSpeciesSelect.innerHTML = '';
        for (const [key, profile] of Object.entries(plantProfiles)) {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = `${profile.species} - ${profile.model_status}`;
            plantSpeciesSelect.appendChild(option);
        }
        
        onPlantChanged();
        fetchPlants();
    } catch (e) {
        console.error("Failed to load profiles", e);
    }
}

function onPlantChanged(resetId = true) {
    const key = plantSpeciesSelect.value;
    const profile = plantProfiles[key];
    if (!profile) return;
    
    // Auto populate ID if requested
    if (resetId && (!activePlant || activePlant.species !== key)) {
        plantIdInput.value = `${profile.plant_id_prefix}-001`;
    }
    
    // Render profile info
    plantProfileInfo.innerHTML = `
        <div style="margin-bottom: 5px;"><strong>Scientific name:</strong> <em>${profile.scientific_name}</em></div>
        <div style="margin-bottom: 5px;"><strong>Model status:</strong> ${profile.model_status}</div>
        <div style="margin-bottom: 5px;"><strong>Available stress categories:</strong> ${profile.supported_stresses.join(', ')}</div>
        <div><strong>Sensor profile status:</strong> ${profile.sensor_profile}</div>
    `;
    
    // Toggle acquisition based on can_diagnose
    if (profile.can_diagnose) {
        btnLoadDataset.disabled = false;
    } else {
        btnLoadDataset.disabled = true;
        btnDiagnose.disabled = true;
        acquisitionStatus.style.display = 'block';
        acquisitionStatus.style.color = '#888';
        acquisitionStatus.textContent = "Plant profile available. A validated plant-specific ML model is not yet available for diagnosis.";
    }
    
    // Reset state
    sectionFeatures.style.display = 'none';
    sectionResult.style.display = 'none';
    const diagPlaceholder = document.getElementById('diagnosisPlaceholder');
    if (diagPlaceholder) diagPlaceholder.style.display = 'block';
    const featPlaceholder = document.getElementById('featuresPlaceholder');
    if (featPlaceholder) featPlaceholder.style.display = 'block';

    currentSpectrum = null;
    currentMeasurementId = null;
    if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
    }
    spectrumInfoPanel.innerHTML = '';
    if (profile.can_diagnose) {
        acquisitionStatus.style.display = 'none';
    }
    
    loadHistory(plantIdInput.value.trim());
}

plantSpeciesSelect.addEventListener('change', () => onPlantChanged(true));
plantIdInput.addEventListener('change', () => loadHistory(plantIdInput.value.trim()));


// Initialize Spectrum Chart
function initSpectrumChart(data) {
    const ctx = document.getElementById('spectrumChart').getContext('2d');
    
    const labels = Array.from({length: data.length}, (_, i) => {
        const wvl = 394.9 + (i * ((1020.8 - 394.9) / 832));
        return Math.round(wvl) + ' nm';
    });

    const minVal = Math.min(...data);
    const maxVal = Math.max(...data);
    const padding = (maxVal - minVal) * 0.1;

    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Leaf Reflectance',
                data: data,
                borderColor: '#5A8252',
                backgroundColor: 'rgba(90, 130, 82, 0.1)',
                borderWidth: 1.5,
                pointRadius: 0,
                fill: true,
                tension: 0.2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: 'Wavelength (nm)' },
                    ticks: { maxTicksLimit: 10 },
                    grid: { display: false }
                },
                y: {
                    title: { display: true, text: 'Reflectance' },
                    min: Math.max(0, minVal - padding),
                    max: maxVal + padding,
                    grid: { color: '#e5e5e5' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Update Timeline Chart
function updateTimelineChart(history) {
    const ctx = document.getElementById('timelineChart').getContext('2d');
    
    const labels = history.map(h => {
        const d = new Date(h.measurement_timestamp);
        return `${h.experimental_day.toUpperCase()} (${d.getMonth()+1}/${d.getDate()})`;
    }).reverse();
    const data = history.map(h => h.model_confidence * 100).reverse();
    const bgColors = history.map(h => {
        if (h.diagnosis.includes("Healthy") || h.diagnosis.includes("Control")) return '#5A8252'; 
        if (h.diagnosis.includes("Water")) return '#3b82f6'; 
        if (h.diagnosis.includes("Nitrogen")) return '#f59e0b'; 
        return '#888';
    }).reverse();

    if (timelineChartInstance) {
        timelineChartInstance.destroy();
    }

    timelineChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Model Confidence (%)',
                data: data,
                backgroundColor: bgColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: { display: true, text: 'Confidence (%)' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const record = history[history.length - 1 - ctx.dataIndex];
                            return `${record.diagnosis} (${(record.model_confidence * 100).toFixed(1)}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Info Button Handling
document.querySelectorAll('.info-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const title = btn.getAttribute('data-title');
        const text = btn.getAttribute('data-text');
        infoModalTitle.textContent = title;
        infoModalText.innerHTML = text;
        infoModal.classList.remove('hidden');
    });
});
btnCloseModal.addEventListener('click', () => {
    infoModal.classList.add('hidden');
});

// 1. Acquire Measurement
btnLoadDataset.addEventListener('click', async () => {
    btnLoadDataset.disabled = true;
    btnLoadDataset.textContent = "Acquiring...";
    acquisitionStatus.style.display = 'none';
    
    const day = experimentalDaySelect.value;
    
    try {
        const response = await fetch(`${API_BASE}/dataset/spectrum?day=${day}`);
        if (!response.ok) throw new Error('Failed to acquire measurement');
        
        const data = await response.json();
        currentSpectrum = data.spectral_data;
        currentSampleId = data.sample_id;
        
        acquisitionStatus.style.display = 'block';
        acquisitionStatus.style.color = '#5A8252';
        acquisitionStatus.textContent = "✓ Measurement acquired";
        btnDiagnose.disabled = false;
        
        initSpectrumChart(currentSpectrum);
        spectrumInfoPanel.innerHTML = `
            <strong>Bands:</strong> 832 &nbsp;|&nbsp; 
            <strong>Wavelength range:</strong> ~395–1021 nm &nbsp;|&nbsp; 
            <strong>Exp. Day:</strong> ${day.toUpperCase()} &nbsp;|&nbsp; 
            <strong>Sample ID:</strong> ${currentSampleId} &nbsp;|&nbsp; 
            <strong>Preprocessing:</strong> Savitzky-Golay smoothing
        `;

        // Update Raw Data workspace
        const rawDayEl = document.getElementById('rawExpDay');
        if (rawDayEl) rawDayEl.textContent = day.toUpperCase();
        const rawPlantEl = document.getElementById('rawPlantId');
        if (rawPlantEl) rawPlantEl.textContent = plantIdInput.value.trim() || 'TOM-001';

        // Sample key bands in Raw Data workspace
        if (currentSpectrum && currentSpectrum.length === 832) {
            const getVal = (targetWvl) => {
                const idx = Math.min(831, Math.max(0, Math.round((targetWvl - 394.9) * 832 / (1020.8 - 394.9))));
                return currentSpectrum[idx].toFixed(4);
            };
            const b400 = document.getElementById('rb400'); if (b400) b400.textContent = getVal(400);
            const b450 = document.getElementById('rb450'); if (b450) b450.textContent = getVal(450);
            const b550 = document.getElementById('rb550'); if (b550) b550.textContent = getVal(550);
            const b670 = document.getElementById('rb670'); if (b670) b670.textContent = getVal(670);
            const b705 = document.getElementById('rb705'); if (b705) b705.textContent = getVal(705);
            const b750 = document.getElementById('rb750'); if (b750) b750.textContent = getVal(750);
            const b970 = document.getElementById('rb970'); if (b970) b970.textContent = getVal(970);
        }
        
    } catch (error) {
        alert("Error acquiring measurement: " + error.message);
    } finally {
        btnLoadDataset.disabled = false;
        btnLoadDataset.textContent = "Acquire Measurement";
    }
});

btnDownloadReport.addEventListener('click', () => {
    if (currentMeasurementId) {
        window.open(`${API_BASE}/report/${currentMeasurementId}`, '_blank');
    }
});

btnDownloadProgressReport.addEventListener('click', () => {
    const plantId = plantIdInput.value.trim();
    if (plantId) {
        window.open(`${API_BASE}/report/progress/${plantId}`, '_blank');
    } else {
        alert("Please enter a Plant ID.");
    }
});

// 2. Run Diagnosis
btnDiagnose.addEventListener('click', async () => {
    const plantId = plantIdInput.value.trim();
    if (!plantId) {
        alert("Please enter a Plant ID.");
        return;
    }
    
    if (!currentSpectrum) {
        alert("Please acquire a measurement first.");
        return;
    }

    btnDiagnose.disabled = true;
    btnDiagnose.textContent = "Processing...";
    sectionFeatures.style.display = 'none';
    sectionResult.style.display = 'none';

    const payload = {
        plant_species: plantSpeciesSelect.value,
        plant_id: plantId,
        sensor_profile: sensorProfileSelect.value,
        experimental_day: experimentalDaySelect.value.toUpperCase(),
        sample_id: currentSampleId,
        spectral_data: currentSpectrum
    };

    try {
        const response = await fetch(`${API_BASE}/diagnose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || "Diagnosis failed");
        }

        currentMeasurementId = result.measurement_id;

        // Render Features Table
        featuresTableBody.innerHTML = '';
        if (result.features) {
            for (const [feat, val] of Object.entries(result.features)) {
                let region = "General";
                let desc = "Derived spectral feature";
                
                if (feat === "NDVI") { region = "Visible/NIR"; desc = "Vegetation-related spectral index using Red and NIR"; }
                else if (feat === "GNDVI") { region = "Visible/NIR"; desc = "Vegetation index using Green and NIR"; }
                else if (feat === "NDRE") { region = "Red-Edge"; desc = "Sensitive to changes near the red-edge region"; }
                else if (feat === "WBI") { region = "NIR/Water"; desc = "Water-associated index (not direct moisture)"; }
                else if (["VIS_Mean", "NIR_Mean"].includes(feat)) { region = "Broadband"; desc = "Average reflectance across region"; }
                
                featuresTableBody.innerHTML += `
                    <tr>
                        <td><strong>${feat}</strong></td>
                        <td>${val.toFixed(4)}</td>
                        <td>${region}</td>
                        <td class="text-muted">${desc}</td>
                    </tr>
                `;
            }
        }
        
        const featPlaceholder = document.getElementById('featuresPlaceholder');
        if (featPlaceholder) featPlaceholder.style.display = 'none';
        sectionFeatures.style.display = 'block';

        // Update Diagnosis UI
        resDiagnosis.textContent = result.diagnosis;
        resConfidence.textContent = (result.model_confidence * 100).toFixed(1) + '%';
        
        // Class Probabilities
        classProbsContainer.innerHTML = '';
        if (result.class_probabilities) {
            for (const [cls, prob] of Object.entries(result.class_probabilities)) {
                classProbsContainer.innerHTML += `
                    <div class="prob-row">
                        <span class="prob-label">${cls}</span>
                        <div class="prob-bar-bg"><div class="prob-bar-fill" style="width: ${(prob*100).toFixed(1)}%"></div></div>
                        <span class="prob-val">${(prob*100).toFixed(1)}%</span>
                    </div>
                `;
            }
        }

        // Explainability
        explainabilityContainer.innerHTML = '';
        if (result.top_features && result.top_features.length > 0) {
            result.top_features.forEach((feat, index) => {
                explainabilityContainer.innerHTML += `
                    <div class="feat-rank-card">
                        <strong>#${index + 1}: ${feat}</strong>
                    </div>
                `;
            });
        } else {
            explainabilityContainer.innerHTML = '<em>No explainability data available.</em>';
        }

        // Effects & Recommendation
        resPotentialEffects.innerHTML = result.potential_effects.map(e => `<li>${e}</li>`).join('');
        resRecommendation.textContent = result.recommendation;
        
        const diagPlaceholder = document.getElementById('diagnosisPlaceholder');
        if (diagPlaceholder) diagPlaceholder.style.display = 'none';
        sectionResult.style.display = 'block';

        // Update Overview KPI
        const kpiDiag = document.getElementById('kpiLatestDiagnosis');
        if (kpiDiag) {
            kpiDiag.textContent = result.diagnosis;
            kpiDiag.style.color = result.diagnosis.includes('Healthy') || result.diagnosis.includes('Control') ? '#4ade80' : '#f59e0b';
        }

        // Update AI Analysis Workspace
        const aiPred = document.getElementById('aiKpiPred');
        if (aiPred) {
            aiPred.textContent = result.diagnosis;
            aiPred.style.color = result.diagnosis.includes('Healthy') || result.diagnosis.includes('Control') ? '#4ade80' : '#f59e0b';
        }
        const aiConf = document.getElementById('aiKpiConf');
        if (aiConf) aiConf.textContent = (result.model_confidence * 100).toFixed(1) + '%';
        
        const aiProbs = document.getElementById('aiAnalysisProbsContainer');
        if (aiProbs && result.class_probabilities) {
            aiProbs.innerHTML = '';
            for (const [cls, prob] of Object.entries(result.class_probabilities)) {
                aiProbs.innerHTML += `
                    <div class="prob-row">
                        <span class="prob-label">${cls}</span>
                        <div class="prob-bar-bg"><div class="prob-bar-fill" style="width: ${(prob*100).toFixed(1)}%"></div></div>
                        <span class="prob-val">${(prob*100).toFixed(1)}%</span>
                    </div>
                `;
            }
        }

        const aiFeat = document.getElementById('aiAnalysisFeatContainer');
        if (aiFeat && result.top_features && result.top_features.length > 0) {
            aiFeat.innerHTML = '';
            result.top_features.forEach((feat, index) => {
                aiFeat.innerHTML += `
                    <div class="feat-rank-card">
                        <strong>#${index + 1}: ${feat}</strong>
                    </div>
                `;
            });
        }
        
        loadHistory(plantId);
        
    } catch (error) {
        alert("Diagnosis Error: " + error.message);
    } finally {
        btnDiagnose.disabled = false;
        btnDiagnose.textContent = "Run AI Diagnosis";
    }
});

// 3. Load History
async function loadHistory(plantId) {
    if (!plantId) return;
    
    btnRefreshHistory.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/history/${plantId}`);
        if (!response.ok) throw new Error('Failed to fetch history');
        
        const history = await response.json();
        
        historyTableBody.innerHTML = '';
        
        if (history.length > 0) {
            history.forEach(record => {
                const tr = document.createElement('tr');
                const d = new Date(record.measurement_timestamp);
                const confStr = (record.model_confidence * 100).toFixed(1) + '%';
                
                tr.innerHTML = `
                    <td>${d.toLocaleString()}</td>
                    <td><strong>${record.experimental_day}</strong></td>
                    <td>${record.diagnosis}</td>
                    <td>${confStr}</td>
                    <td>
                        <button class="btn secondary" style="padding: 0.2rem 0.5rem;" onclick="window.open('${API_BASE}/report/${record.measurement_id}', '_blank')">PDF</button>
                    </td>
                `;
                historyTableBody.appendChild(tr);
            });
            
            updateTimelineChart(history);
        } else {
            if (timelineChartInstance) {
                timelineChartInstance.destroy();
                timelineChartInstance = null;
            }
        }
    } catch (error) {
        console.error("History Error:", error);
    } finally {
        btnRefreshHistory.disabled = false;
    }
}

btnRefreshHistory.addEventListener('click', () => {
    loadHistory(plantIdInput.value.trim());
});

// Kickoff
fetchProfiles();

// Modals Setup
if (btnSystemOverview) btnSystemOverview.addEventListener('click', () => { overviewModal.classList.remove('hidden'); });
if (btnCloseOverview) btnCloseOverview.addEventListener('click', () => { overviewModal.classList.add('hidden'); });

if (btnClearHistory) {
    btnClearHistory.addEventListener('click', () => {
        const plantId = plantIdInput.value.trim();
        if (!plantId) {
            alert('Please enter a Plant ID.');
            return;
        }
        deleteModalText.textContent = `This will permanently remove stored measurement records for plant ${plantId}, including its timeline and progress-report data. ML models, plant profiles, and application configuration will not be affected.`;
        deleteModal.classList.remove('hidden');
    });
}

if (btnCancelDelete) btnCancelDelete.addEventListener('click', () => { deleteModal.classList.add('hidden'); });

if (btnConfirmDelete) {
    btnConfirmDelete.addEventListener('click', async () => {
        const plantId = plantIdInput.value.trim();
        if (!plantId) return;
        
        btnConfirmDelete.disabled = true;
        btnConfirmDelete.textContent = 'Deleting...';
        
        try {
            const response = await fetch(`${API_BASE}/history/${plantId}`, {
                method: 'DELETE'
            });
            if (!response.ok) throw new Error('Failed to delete history');
            
            const data = await response.json();
            alert(`Measurement history cleared for ${plantId}. (${data.deleted_count} records removed)`);
            
            // Refresh UI
            loadHistory(plantId);
            deleteModal.classList.add('hidden');
        } catch (error) {
            alert('Delete Error: ' + error.message);
        } finally {
            btnConfirmDelete.disabled = false;
            btnConfirmDelete.textContent = 'Clear History';
        }
    });
}

// Escape key to close modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (infoModal) infoModal.classList.add('hidden');
        if (overviewModal) overviewModal.classList.add('hidden');
        if (deleteModal) deleteModal.classList.add('hidden');
    }
});

// Form Add Plant Handler
const formAddPlant = document.getElementById('formAddPlant');
if (formAddPlant) {
    formAddPlant.addEventListener('submit', async (e) => {
        e.preventDefault();
        const plant_id = document.getElementById('newPlantId').value.trim();
        const name = document.getElementById('newPlantName').value.trim();
        const species = document.getElementById('newPlantSpecies').value;
        const cultivar = document.getElementById('newPlantCultivar').value.trim();
        const growth_stage = document.getElementById('newPlantGrowthStage').value;
        const date_acquired = document.getElementById('newPlantDateAcquired').value;
        const soil_type = document.getElementById('newPlantSoilType').value.trim();
        const soil_ph = parseFloat(document.getElementById('newPlantSoilPh').value) || null;
        const watering_regime = document.getElementById('newPlantWatering').value.trim();
        const nutrient_regime = document.getElementById('newPlantNutrient').value.trim();
        const initial_condition = document.getElementById('newPlantInitialCondition').value.trim();
        const additional_notes = document.getElementById('newPlantNotes').value.trim();
        
        const msgEl = document.getElementById('addPlantMessage');
        const submitBtn = document.getElementById('btnSubmitAddPlant');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Registering...';

        try {
            const payload = {
                plant_id, name, species, cultivar, growth_stage,
                date_acquired: date_acquired || new Date().toISOString().split('T')[0],
                soil_type, soil_ph, watering_regime, nutrient_regime,
                initial_condition, additional_notes
            };
            const res = await fetch(`${API_BASE}/plants`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Registration failed');
            }
            const newPlant = await res.json();
            msgEl.style.display = 'block';
            msgEl.style.color = '#5A8252';
            msgEl.textContent = `✓ Specimen ${plant_id} registered successfully!`;
            await fetchPlants();
            setActivePlant(newPlant);
            setTimeout(() => {
                msgEl.style.display = 'none';
                navigateToWorkspace('ws-plant-registry');
            }, 800);
        } catch (err) {
            msgEl.style.display = 'block';
            msgEl.style.color = '#d9534f';
            msgEl.textContent = 'Error: ' + err.message;
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Register Plant Specimen';
        }
    });
}

// ==========================================
// WORKSPACE NAVIGATION CONTROLLER
// ==========================================
function navigateToWorkspace(targetId) {
    if (!targetId) return;
    const navLinks = document.querySelectorAll('.nav-link[data-workspace]');
    const workspaces = document.querySelectorAll('.workspace');
    
    navLinks.forEach(nl => {
        if (nl.getAttribute('data-workspace') === targetId) {
            nl.classList.add('active');
        } else {
            nl.classList.remove('active');
        }
    });

    workspaces.forEach(ws => {
        if (ws.id === targetId) {
            ws.classList.add('active');
        } else {
            ws.classList.remove('active');
        }
    });
}
window.navigateToWorkspace = navigateToWorkspace;

(function() {
    function initNavigation() {
        const navLinks = document.querySelectorAll('.nav-link[data-workspace]');
        if (!navLinks.length) return;

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('data-workspace');
                if (targetId) {
                    navigateToWorkspace(targetId);
                }
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNavigation);
    } else {
        initNavigation();
    }
})();




