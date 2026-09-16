import httpx
import sys
from pypdf import PdfReader
import io

BASE_URL = "http://127.0.0.1:8000/api/v1"

def verify_pdf():
    print("--- STARTING PDF VERIFICATION ---")
    
    # 1. Generate a measurement
    demo_res = httpx.get(f"{BASE_URL}/demo/spectrum?day=d2&index=0")
    spectrum = demo_res.json()["spectral_data"]
    
    payload = {
        "plant_species": "tomato",
        "plant_id": "TOM-PDF-VERIFY-1",
        "sensor_profile": "vis_nir_research",
        "spectral_data": spectrum,
        "is_demo": True
    }
    diag_res = httpx.post(f"{BASE_URL}/diagnose", json=payload)
    m_id = diag_res.json()["measurement_id"]
    
    # 2. Download the report
    pdf_res = httpx.get(f"{BASE_URL}/report/{m_id}")
    if pdf_res.status_code != 200:
        print(f"Failed to download PDF. Status: {pdf_res.status_code}")
        sys.exit(1)
        
    pdf_bytes = pdf_res.content
    with open("test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
        
    print("PDF Downloaded and saved as test_report.pdf")
    
    # 3. Verify PDF Structure and Text
    reader = PdfReader(io.BytesIO(pdf_bytes))
    num_pages = len(reader.pages)
    print(f"Number of pages: {num_pages}")
    assert num_pages >= 1
    
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
        
    print("\n--- EXTRACTED PDF TEXT ---")
    print(text)
    print("--------------------------\n")
    
    # Assertions
    assert "AI Plant Stress Detection System" in text
    assert m_id in text
    assert "Tomato" in text
    assert "TOM-PDF-VERIFY-1" in text
    assert "vis_nir_research" in text
    assert "tomato_research_rf_v1.0.0" in text
    assert "Not supported in current MVP" in text
    assert "DEMONSTRATION DATA" in text
    assert "Model confidence indicates statistical classification probability. It does NOT represent biological severity." in text
    
    print("All PDF content assertions PASSED.")
    
    # 4. Verify 404 for invalid report
    invalid_res = httpx.get(f"{BASE_URL}/report/invalid-1234")
    assert invalid_res.status_code == 404
    print("Invalid report 404 assertion PASSED.")

if __name__ == "__main__":
    verify_pdf()
