const API_BASE = '/api/v1';

// DOM Elements
const plantIdInput = document.getElementById('plantId');
const plantSpeciesSelect = document.getElementById('plantSpecies');
const sensorProfileSelect = document.getElementById('sensorProfile');

const btnLoadDemo = document.getElementById('btnLoadDemo');
const spectrumContainer = document.getElementById('spectrumContainer');
const btnDiagnose = document.getElementById('btnDiagnose');

const diagnosisResultBox = document.getElementById('diagnosisResult');
const resDiagnosis = document.getElementById('resDiagnosis');
const resConfidence = document.getElementById('resConfidence');
const resInterpretation = document.getElementById('resInterpretation');
const resRecommendation = document.getElementById('resRecommendation');

const btnLoadHistory = document.getElementById('btnLoadHistory');
const historyTableBody = document.querySelector('#historyTable tbody');
const historyEmpty = document.getElementById('historyEmpty');
const btnDownloadReport = document.getElementById('btnDownloadReport');

// State
let currentSpectrum = null;
let chartInstance = null;
let currentMeasurementId = null;

// Initialize Chart
function initChart(data) {
    const ctx = document.getElementById('spectrumChart').getContext('2d');
    
    // Create roughly 832 labels from ~395nm to ~1021nm
    const labels = Array.from({length: data.length}, (_, i) => {
        const wvl = 394.9 + (i * ((1020.8 - 394.9) / 832));
        return Math.round(wvl) + ' nm';
    });

    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Reflectance (Research Spectrum)',
                data: data,
                borderColor: '#5A8252',
                backgroundColor: 'rgba(90, 130, 82, 0.1)',
                borderWidth: 1,
                pointRadius: 0,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: { maxTicksLimit: 10 }
                },
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// 1. Load Demo Spectrum
btnLoadDemo.addEventListener('click', async () => {
    btnLoadDemo.disabled = true;
    btnLoadDemo.textContent = "Loading...";
    try {
        const response = await fetch(`${API_BASE}/demo/spectrum?day=d2&index=0`);
        if (!response.ok) throw new Error('Failed to load spectrum');
        
        const data = await response.json();
        currentSpectrum = data.spectral_data;
        
        spectrumContainer.classList.remove('hidden');
        btnDiagnose.disabled = false;
        
        // Render chart
        initChart(currentSpectrum);
        
    } catch (error) {
        alert("Error loading demo spectrum: " + error.message);
    } finally {
        btnLoadDemo.disabled = false;
        btnLoadDemo.textContent = "Load Demo Spectrum";
    }
});

// Download Report Button (Current Diagnosis)
btnDownloadReport.addEventListener('click', () => {
    if (currentMeasurementId) {
        window.open(`${API_BASE}/report/${currentMeasurementId}`, '_blank');
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
        alert("Please load a spectrum first.");
        return;
    }

    btnDiagnose.disabled = true;
    btnDiagnose.textContent = "Diagnosing...";
    diagnosisResultBox.classList.add('hidden');

    const payload = {
        plant_species: plantSpeciesSelect.value,
        plant_id: plantId,
        sensor_profile: sensorProfileSelect.value,
        spectral_data: currentSpectrum,
        is_demo: true
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

        // Update UI
        resDiagnosis.textContent = result.diagnosis;
        resConfidence.textContent = (result.model_confidence * 100).toFixed(1) + '%';
        resInterpretation.textContent = result.interpretation;
        resRecommendation.textContent = result.recommendation;
        
        diagnosisResultBox.classList.remove('hidden');
        
        // Auto-refresh history
        loadHistory(plantId);
        
    } catch (error) {
        alert("Diagnosis Error: " + error.message);
    } finally {
        btnDiagnose.disabled = false;
        btnDiagnose.textContent = "Run Diagnosis";
    }
});

// 3. Load History
async function loadHistory(plantId) {
    if (!plantId) return;
    
    btnLoadHistory.disabled = true;
    try {
        const response = await fetch(`${API_BASE}/history/${plantId}`);
        if (!response.ok) throw new Error('Failed to fetch history');
        
        const history = await response.json();
        
        historyTableBody.innerHTML = '';
        
        if (history.length === 0) {
            historyEmpty.classList.remove('hidden');
            document.querySelector('table').classList.add('hidden');
        } else {
            historyEmpty.classList.add('hidden');
            document.querySelector('table').classList.remove('hidden');
            
            history.forEach(record => {
                const tr = document.createElement('tr');
                
                const d = new Date(record.measurement_timestamp);
                const timeStr = d.toLocaleString();
                
                const confStr = (record.model_confidence * 100).toFixed(1) + '%';
                
                tr.innerHTML = `
                    <td>${timeStr}</td>
                    <td>${record.plant_id}</td>
                    <td>${record.diagnosis}</td>
                    <td>${confStr}</td>
                    <td>
                        <button class="btn secondary" style="padding: 0.2rem 0.5rem;" onclick="window.open('${API_BASE}/report/${record.measurement_id}', '_blank')">PDF</button>
                    </td>
                `;
                historyTableBody.appendChild(tr);
            });
        }
    } catch (error) {
        console.error("History Error:", error);
    } finally {
        btnLoadHistory.disabled = false;
    }
}

btnLoadHistory.addEventListener('click', () => {
    loadHistory(plantIdInput.value.trim());
});

// Initial history load if ID exists
if (plantIdInput.value.trim()) {
    loadHistory(plantIdInput.value.trim());
}
