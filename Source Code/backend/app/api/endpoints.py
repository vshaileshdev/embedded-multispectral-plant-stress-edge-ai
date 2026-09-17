from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import io

from app.database.session import get_db
from app.database import models
from app.schemas.measurement import MeasurementRequest, DiagnosisResult
from app.diagnosis.service import process_measurement, INTERPRETATION_MAP
from app.core.dataset_loader import get_dataset_spectrum
from app.reports.pdf_generator import DiagnosisReportPDF
from app.core.plant_profiles import PLANT_PROFILES

router = APIRouter()

@router.get("/plants/profiles")
def get_plant_profiles():
    """Returns the configuration for all supported plant species."""
    return {"profiles": PLANT_PROFILES}

@router.post("/diagnose", response_model=DiagnosisResult)
def diagnose_measurement(request: MeasurementRequest, db: Session = Depends(get_db)):
    """
    Accepts a measurement, runs it through the appropriate model pipeline,
    and returns a diagnosis.
    """
    return process_measurement(db, request)

@router.delete("/history/{plant_id}")
def delete_history(plant_id: str, db: Session = Depends(get_db)):
    """
    Clears all measurement history records for a specific plant ID.
    """
    records = db.query(models.MeasurementHistory).filter(
        models.MeasurementHistory.plant_id == plant_id
    ).all()
    
    deleted_count = len(records)
    for r in records:
        db.delete(r)
    db.commit()
    
    return {"plant_id": plant_id, "deleted_count": deleted_count}

@router.get("/history/{plant_id}", response_model=List[DiagnosisResult])
def get_history(plant_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """
    Retrieves the chronological measurement history for a specific biological plant.
    """
    records = db.query(models.MeasurementHistory).filter(
        models.MeasurementHistory.plant_id == plant_id
    ).order_by(models.MeasurementHistory.measurement_timestamp.desc()).limit(limit).all()
    
    results = []
    import json
    for r in records:
        # Reverse map diagnosis string to get interpretation if possible
        mapping = {"interpretation": "", "recommendation": "", "potential_effects": []}
        for key, val in INTERPRETATION_MAP.items():
            if val["diagnosis"] == r.diagnosis:
                mapping = val
                break
                
        features_dict = {}
        top_features_list = []
        class_probabilities = {}
        try:
            if r.features_json:
                features_dict = json.loads(r.features_json)
            if r.top_features_json:
                top_features_list = json.loads(r.top_features_json)
            if r.class_probabilities_json:
                class_probabilities = json.loads(r.class_probabilities_json)
        except Exception:
            pass
                
        results.append(DiagnosisResult(
            measurement_id=r.measurement_id,
            plant_species=r.plant_species,
            plant_id=r.plant_id,
            sensor_profile=r.sensor_profile,
            experimental_day=r.experimental_day or "Unknown",
            sample_id=r.sample_id,
            dataset_source=r.dataset_source or "Unknown",
            measurement_timestamp=r.measurement_timestamp,
            model_id=r.model_id,
            diagnosis=r.diagnosis,
            model_confidence=r.model_confidence,
            class_probabilities=class_probabilities,
            severity=r.severity,
            features=features_dict,
            top_features=top_features_list,
            interpretation=mapping.get("interpretation", ""),
            potential_effects=mapping.get("potential_effects", []),
            recommendation=mapping.get("recommendation", "")
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

from app.reports.progress_report import ProgressReportPDF

@router.get("/report/progress/{plant_id}")
def download_progress_report(plant_id: str, db: Session = Depends(get_db)):
    """
    Generates and downloads a longitudinal Plant Health Progress Report PDF.
    """
    records = db.query(models.MeasurementHistory).filter(
        models.MeasurementHistory.plant_id == plant_id
    ).order_by(models.MeasurementHistory.measurement_timestamp.asc()).all()
    
    if not records:
        raise HTTPException(status_code=404, detail="No measurements found for this plant ID")
        
    species = records[0].plant_species
    pdf = ProgressReportPDF(plant_id, species, records, INTERPRETATION_MAP)
    pdf_bytes = pdf.generate()
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f'attachment; filename="progress_report_{plant_id}.pdf"'}
    )

@router.get("/dataset/spectrum")
def load_dataset_spectrum(day: str = Query("d2")):
    """
    Helper route for the frontend to fetch a valid 832-channel spectrum 
    from the dataset to populate the UI.
    """
    return get_dataset_spectrum(day)

