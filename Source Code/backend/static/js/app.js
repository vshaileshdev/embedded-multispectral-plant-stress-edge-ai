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
    } catch (e) {
        console.error("Failed to load profiles", e);
    }
}

function onPlantChanged() {
    const key = plantSpeciesSelect.value;
    const profile = plantProfiles[key];
    if (!profile) return;
    
    // Auto populate ID
    plantIdInput.value = `${profile.plant_id_prefix}-001`;
    
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

plantSpeciesSelect.addEventListener('change', onPlantChanged);
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
        
        sectionResult.style.display = 'block';
        
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


