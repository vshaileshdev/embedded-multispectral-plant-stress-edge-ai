import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.dataset_loader import get_dataset_spectrum

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_dataset_spectrum_endpoint():
    response = client.get("/api/v1/dataset/spectrum?day=d2")
    assert response.status_code == 200
    data = response.json()
    assert "spectral_data" in data
    assert "sample_id" in data
    assert len(data["spectral_data"]) == 832

def test_plant_profiles_endpoint():
    response = client.get("/api/v1/plants/profiles")
    assert response.status_code == 200
    data = response.json()["profiles"]
    assert "tomato" in data
    assert "spinach" in data
    assert data["tomato"]["can_diagnose"] is True
    assert data["spinach"]["can_diagnose"] is False

def test_unsupported_plant_diagnosis():
    res = get_dataset_spectrum("d2")
    payload = {
        "plant_species": "spinach",
        "plant_id": "SPI-001",
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D2",
        "sample_id": "TEST",
        "spectral_data": res["spectral_data"]
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 400
    assert "not yet available" in response.json()["detail"]

def test_valid_inference_and_history():
    # 1. Get a valid dataset spectrum
    res = get_dataset_spectrum("d2")
    spectrum = res["spectral_data"]
    sample_id = res["sample_id"]
    
    # 2. Diagnose
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-TEST-001",
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D2",
        "spectral_data": spectrum,
        "sample_id": "TEST_ID"
    }
    
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 200
    result = response.json()
    
    assert result["plant_species"] == "tomato"
    assert result["plant_id"] == "TOM-TEST-001"
    assert result["sensor_profile"] == "vis_nir_research"
    assert result["experimental_day"] == "D2"
    assert result["diagnosis"] in ["Control (Healthy)", "Water Deficit (Drought)", "Nitrogen Deficit"]
    assert "model_confidence" in result
    assert result["severity"] is None
    assert "features" in result
    
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
        "experimental_day": "D2",
        "spectral_data": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        "sample_id": "TEST_ID"
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
        "experimental_day": "D2",
        "spectral_data": [0.1] * 9,
        "sample_id": "TEST_ID"
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 400

def test_invalid_plant_species():
    payload = {
        "plant_species": "cactus",
        "plant_id": "CAC-TEST-001",
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D2",
        "spectral_data": [0.1] * 832,
        "sample_id": "TEST_ID"
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 400
    assert "Unsupported plant species: cactus" in response.json()["detail"]

def test_invalid_dimensionality():
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-TEST-003",
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D2",
        "spectral_data": [0.1] * 9, # Wrong length
        "sample_id": "TEST_ID"
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 422
    assert "Expected 832, got 9." in response.json()["detail"]

def test_missing_metadata():
    payload = {
        "plant_species": "tomato",
        # Missing plant_id
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D2",
        "spectral_data": [0.1] * 832,
        "sample_id": "TEST_ID"
    }
    response = client.post("/api/v1/diagnose", json=payload)
    assert response.status_code == 422 # FastAPI validation error

def test_delete_history():
    import uuid
    plant_id = f"TOM-DEL-{uuid.uuid4().hex[:6]}"
    
    # Generate a measurement
    res = client.get("/api/v1/dataset/spectrum?day=d2")
    spectrum = res.json()["spectral_data"]
    payload = {
        "plant_species": "tomato",
        "plant_id": plant_id,
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D2",
        "sample_id": "TEST_ID",
        "spectral_data": spectrum
    }
    client.post("/api/v1/diagnose", json=payload)
    
    # Verify it exists
    history_res = client.get(f"/api/v1/history/{plant_id}")
    assert len(history_res.json()) == 1
    
    # Delete it
    del_res = client.delete(f"/api/v1/history/{plant_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted_count"] == 1
    
    # Verify it's gone
    history_res = client.get(f"/api/v1/history/{plant_id}")
    assert len(history_res.json()) == 0
