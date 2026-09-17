import httpx
import time
import uuid

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/v1"

def end_to_end_test():
    print("--- STARTING END-TO-END VERIFICATION ---")
    
    # 1. Open frontend (Check if static files serve)
    res = httpx.get(f"{BASE_URL}/")
    assert res.status_code == 200
    assert "Multispectral Plant Stress Classification" in res.text
    print("1. Frontend serves correctly.")

    # 2. Select Plant
    plant_species = "tomato"
    plant_id = f"TOM-E2E-{uuid.uuid4().hex[:6]}"
    print(f"2/3. Selected Plant: {plant_species}, ID: {plant_id}")

    # 4. Load Dataset Spectrum
    res = httpx.get(f"{API_URL}/dataset/spectrum?day=d2")
    assert res.status_code == 200
    spectrum = res.json()["spectral_data"]
    sample_id = res.json()["sample_id"]
    print("4. Dataset Spectrum loaded.")

    # 5. Confirm 832 bands
    assert len(spectrum) == 832
    print("5. Confirmed exactly 832 bands.")

    # 6. Run Diagnosis
    payload = {
        "plant_species": plant_species,
        "plant_id": plant_id,
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D2",
        "sample_id": sample_id,
        "spectral_data": spectrum
    }
    res = httpx.post(f"{API_URL}/diagnose", json=payload)
    assert res.status_code == 200
    diag = res.json()
    measurement_id = diag["measurement_id"]
    print("6. Diagnosis executed.")

    # 7. Check outputs
    assert "Control" in diag["diagnosis"]
    assert diag["model_confidence"] > 0.8
    assert diag["severity"] is None
    print(f"7/8/9. Diagnosis: {diag['diagnosis']} | Confidence: {diag['model_confidence']} | Severity: {diag['severity']}")

    # 10. Check History
    res = httpx.get(f"{API_URL}/history/{plant_id}")
    assert res.status_code == 200
    history = res.json()
    assert len(history) == 1
    assert history[0]["measurement_id"] == measurement_id
    print("10. First measurement appears in history.")

    # 11. Download Individual PDF
    res = httpx.get(f"{API_URL}/report/{measurement_id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    print("11. PDF Report successfully generated and downloaded.")

    # 12. Run a second diagnosis (Day 0)
    res2 = httpx.get(f"{API_URL}/dataset/spectrum?day=d0")
    spectrum2 = res2.json()["spectral_data"]
    payload2 = {
        "plant_species": plant_species,
        "plant_id": plant_id,
        "sensor_profile": "vis_nir_research",
        "experimental_day": "D0",
        "sample_id": res2.json()["sample_id"],
        "spectral_data": spectrum2
    }
    httpx.post(f"{API_URL}/diagnose", json=payload2)
    print("12. Second measurement executed.")

    # 13. Check History Again
    res = httpx.get(f"{API_URL}/history/{plant_id}")
    assert res.status_code == 200
    assert len(res.json()) == 2
    print("13. Both measurements successfully appear in history.")
    
    # 14. Download Progress Report PDF
    res = httpx.get(f"{API_URL}/report/progress/{plant_id}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    print("14. Progress Report PDF successfully generated and downloaded.")

    # 15. Delete History
    res = httpx.delete(f"{API_URL}/history/{plant_id}")
    assert res.status_code == 200
    assert res.json()["deleted_count"] == 2
    print("15. History successfully deleted.")
    
    # 16. Verify Deletion
    res = httpx.get(f"{API_URL}/history/{plant_id}")
    assert res.status_code == 200
    assert len(res.json()) == 0
    print("16. Verified history is empty after deletion.")

    print("--- ALL TESTS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    end_to_end_test()
