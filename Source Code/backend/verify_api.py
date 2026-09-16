import httpx
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_tests():
    print("--- RUNNING REAL API VERIFICATION TESTS ---")
    
    # 1. Test Demo Endpoint
    print("\n[GET /demo/spectrum]")
    res = httpx.get(f"{BASE_URL}/demo/spectrum?day=d2&index=0")
    print(f"Status: {res.status_code}")
    demo_data = res.json()
    spec = demo_data.get("spectral_data", [])
    print(f"Spectrum Length: {len(spec)}")
    assert len(spec) == 832, "Demo spectrum should be 832 bands."
    
    # 2. Test Diagnose Endpoint
    print("\n[POST /diagnose]")
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-RUNTIME-1",
        "sensor_profile": "vis_nir_research",
        "spectral_data": spec,
        "is_demo": True
    }
    res = httpx.post(f"{BASE_URL}/diagnose", json=payload)
    print(f"Status: {res.status_code}")
    result = res.json()
    print(json.dumps(result, indent=2))
    assert result["plant_species"] == "tomato"
    assert result["plant_id"] == "TOM-RUNTIME-1"
    assert "diagnosis" in result
    assert "model_confidence" in result
    
    # 3. Test History Endpoint
    print("\n[GET /history/TOM-RUNTIME-1]")
    res = httpx.get(f"{BASE_URL}/history/TOM-RUNTIME-1")
    print(f"Status: {res.status_code}")
    history = res.json()
    print(f"History Length: {len(history)}")
    assert len(history) >= 1
    assert history[0]["plant_id"] == "TOM-RUNTIME-1"
    
    # 4. Test Invalid Plant
    print("\n[POST /diagnose] - Invalid Plant")
    payload["plant_species"] = "potato"
    res = httpx.post(f"{BASE_URL}/diagnose", json=payload)
    print(f"Status: {res.status_code}")
    print(res.json())
    assert res.status_code == 400
    
    # 5. Test Invalid Sensor
    print("\n[POST /diagnose] - Invalid Sensor")
    payload["plant_species"] = "tomato"
    payload["sensor_profile"] = "as7341"
    res = httpx.post(f"{BASE_URL}/diagnose", json=payload)
    print(f"Status: {res.status_code}")
    print(res.json())
    assert res.status_code == 400
    
    # 6. Test Invalid Dimensionality
    print("\n[POST /diagnose] - Invalid Dim")
    payload["sensor_profile"] = "vis_nir_research"
    payload["spectral_data"] = [0.1] * 9
    res = httpx.post(f"{BASE_URL}/diagnose", json=payload)
    print(f"Status: {res.status_code}")
    print(res.json())
    assert res.status_code == 422
    
    print("\n--- ALL VERIFICATION TESTS PASSED ---")

if __name__ == "__main__":
    run_tests()
