import httpx
import time

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/v1"

def end_to_end_test():
    print("--- STARTING END-TO-END VERIFICATION ---")
    
    # 1. Open frontend (Check if static files serve)
    res = httpx.get(f"{BASE_URL}/")
    assert res.status_code == 200
    assert "AI Plant Stress Detection" in res.text
    print("1. Frontend serves correctly.")

    # 2. Plant Selection (Tomato) & 3. Plant ID (TOM-003)
    plant_species = "tomato"
    plant_id = "TOM-003"
    print(f"2/3. Selected Plant: {plant_species}, ID: {plant_id}")

    # 4. Load Demo Spectrum
    res = httpx.get(f"{API_URL}/demo/spectrum?day=d2&index=0")
    assert res.status_code == 200
    spectrum = res.json()["spectral_data"]
    print("4. Demo Spectrum loaded.")

    # 5. Confirm 832 bands
    assert len(spectrum) == 832
    print("5. Confirmed exactly 832 bands.")

    # 6. Run Diagnosis
    payload = {
        "plant_species": plant_species,
        "plant_id": plant_id,
        "sensor_profile": "vis_nir_research",
        "spectral_data": spectrum,
        "is_demo": True
    }
    res = httpx.post(f"{API_URL}/diagnose", json=payload)
    assert res.status_code == 200
    result = res.json()
    print("6. Diagnosis executed.")

    # 7/8/9. Confirm diagnosis, confidence, and severity
    assert "diagnosis" in result
    assert "model_confidence" in result
    assert result["severity"] is None
    print(f"7/8/9. Diagnosis: {result['diagnosis']} | Confidence: {result['model_confidence']:.4f} | Severity: {result['severity']}")

    # 10. Confirm history record appears
    res = httpx.get(f"{API_URL}/history/{plant_id}")
    assert res.status_code == 200
    history = res.json()
    assert len(history) >= 1
    print("10. First measurement appears in history.")

    # 11. Test PDF Report Download
    measurement_id = result["measurement_id"]
    res = httpx.get(f"{API_URL}/report/{measurement_id}")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert len(res.content) > 100
    print("11. PDF Report successfully generated and downloaded.")

    # 12. Perform second measurement
    res = httpx.post(f"{API_URL}/diagnose", json=payload)
    assert res.status_code == 200
    print("12. Second measurement executed.")

    # 13. Confirm both appear
    res = httpx.get(f"{API_URL}/history/{plant_id}")
    assert res.status_code == 200
    history2 = res.json()
    assert len(history2) > len(history)
    print("13. Both measurements successfully appear in history.")

    print("--- ALL TESTS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    end_to_end_test()
