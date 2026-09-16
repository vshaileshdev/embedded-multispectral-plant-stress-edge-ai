from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import io

from app.database.session import get_db
from app.database import models
from app.schemas.measurement import MeasurementRequest, DiagnosisResult
from app.diagnosis.service import process_measurement, INTERPRETATION_MAP
from app.core.demo_loader import get_demo_spectrum
from app.reports.pdf_generator import DiagnosisReportPDF

router = APIRouter()

@router.post("/diagnose", response_model=DiagnosisResult)
def diagnose_measurement(request: MeasurementRequest, db: Session = Depends(get_db)):
    """
    Accepts a measurement, runs it through the appropriate model pipeline,
    and returns a diagnosis.
    """
    return process_measurement(db, request)

@router.get("/history/{plant_id}", response_model=List[DiagnosisResult])
def get_history(plant_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """
    Retrieves the chronological measurement history for a specific biological plant.
    """
    records = db.query(models.MeasurementHistory).filter(
        models.MeasurementHistory.plant_id == plant_id
    ).order_by(models.MeasurementHistory.measurement_timestamp.desc()).limit(limit).all()
    
    results = []
    for r in records:
        # Reverse map diagnosis string to get interpretation if possible
        mapping = {"interpretation": "", "recommendation": ""}
        for key, val in INTERPRETATION_MAP.items():
            if val["diagnosis"] == r.diagnosis:
                mapping = val
                break
                
        results.append(DiagnosisResult(
            measurement_id=r.measurement_id,
            plant_species=r.plant_species,
            plant_id=r.plant_id,
            sensor_profile=r.sensor_profile,
            measurement_timestamp=r.measurement_timestamp,
            model_id=r.model_id,
            diagnosis=r.diagnosis,
            model_confidence=r.model_confidence,
            severity=r.severity,
            interpretation=mapping.get("interpretation", ""),
            recommendation=mapping.get("recommendation", ""),
            is_demo=r.is_demo
        ))
    return results

@router.get("/report/{measurement_id}")
def download_report(measurement_id: str, db: Session = Depends(get_db)):
    """
    Generates and downloads a PDF diagnosis report for a given measurement.
    """
    record = db.query(models.MeasurementHistory).filter(
        models.MeasurementHistory.measurement_id == measurement_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Measurement record not found")
        
    pdf = DiagnosisReportPDF(record, INTERPRETATION_MAP)
    pdf_bytes = pdf.generate()
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f'attachment; filename="report_{measurement_id}.pdf"'}
    )

@router.get("/demo/spectrum")
def load_demo_spectrum(day: str = Query("d2"), index: int = Query(0)):
    """
    Helper route for the frontend to fetch a valid 832-channel spectrum 
    from the raw dataset to populate the demo UI.
    """
    spectrum = get_demo_spectrum(day, index)
    return {"spectral_data": spectrum}

