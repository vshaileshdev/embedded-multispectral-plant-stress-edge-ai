import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.demo_loader import get_demo_spectrum

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_demo_spectrum_endpoint():
    response = client.get("/api/v1/demo/spectrum?day=d2&index=0")
    assert response.status_code == 200
    data = response.json()
    assert "spectral_data" in data
    assert len(data["spectral_data"]) == 832

def test_valid_inference_and_history():
    # 1. Get a valid demo spectrum
    spectrum = get_demo_spectrum("d2", 0)
    
    # 2. Diagnose
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-TEST-001",
        "sensor_profile": "vis_nir_research",
        "spectral_data": spectrum,
        "is_demo": True
    }
    
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 200
    result = response.json()
    
    assert result["plant_species"] == "tomato"
    assert result["plant_id"] == "TOM-TEST-001"
    assert result["sensor_profile"] == "vis_nir_research"
    assert result["diagnosis"] in ["Control (Healthy)", "Water Deficit (Drought)", "Nitrogen Deficit"]
    assert "model_confidence" in result
    assert result["severity"] is None
    assert result["is_demo"] is True
    
    # 3. Check History
    history_resp = client.get("/api/v1/history/TOM-TEST-001")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) >= 1
    assert history[0]["measurement_id"] == result["measurement_id"]
    
    # 4. Check PDF Generation
    pdf_resp = client.get(f"/api/v1/report/{result['measurement_id']}")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 100 # Should be a non-empty PDF

def test_invalid_report_id():
    response = client.get("/api/v1/report/invalid-uuid-1234")
    assert response.status_code == 404

def test_valid_as7341_inference():
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-AS7341-001",
        "sensor_profile": "as7341",
        "spectral_data": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        "is_demo": True
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 200, response.json()
    result = response.json()
    assert result["sensor_profile"] == "as7341"
    assert "diagnosis" in result

def test_invalid_sensor_profile():
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-TEST-002",
        "sensor_profile": "fake_sensor",
        "spectral_data": [0.1] * 9,
        "is_demo": True
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 400

def test_invalid_plant_species():
    payload = {
        "plant_species": "spinach",
        "plant_id": "SPIN-TEST-001",
        "sensor_profile": "vis_nir_research",
        "spectral_data": [0.1] * 832,
        "is_demo": True
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 400
    assert "Unsupported plant species: spinach" in response.json()["detail"]

def test_invalid_dimensionality():
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-TEST-003",
        "sensor_profile": "vis_nir_research",
        "spectral_data": [0.1] * 9, # Wrong length
        "is_demo": True
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 422
    assert "Expected 832, got 9." in response.json()["detail"]

def test_missing_metadata():
    payload = {
        "plant_species": "tomato",
        # Missing plant_id
        "sensor_profile": "vis_nir_research",
        "spectral_data": [0.1] * 832,
        "is_demo": True
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 422 # FastAPI validation error
