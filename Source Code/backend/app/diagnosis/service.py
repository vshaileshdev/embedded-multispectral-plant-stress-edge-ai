import numpy as np
import uuid
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.measurement import MeasurementRequest, DiagnosisResult
from app.core.model_registry import model_registry
from app.database import models

INTERPRETATION_MAP = {
    'c': {
        "diagnosis": "Control (Healthy)",
        "interpretation": "The plant shows no significant spectral signatures of water or nitrogen deficit.",
        "recommendation": "Plant-specific recommendation configuration pending validation."
    },
    's': {
        "diagnosis": "Water Deficit (Drought)",
        "interpretation": "Spectral signatures indicate water stress (e.g., changes in carotenoid ratios and cellular scattering).",
        "recommendation": "Plant-specific recommendation configuration pending validation."
    },
    'n': {
        "diagnosis": "Nitrogen Deficit",
        "interpretation": "Spectral signatures indicate nitrogen stress (e.g., shifts in the red-edge and chlorophyll absorption).",
        "recommendation": "Plant-specific recommendation configuration pending validation."
    }
}

def process_measurement(db: Session, request: MeasurementRequest) -> DiagnosisResult:
    # 1. Fetch Model Pipeline
    pipeline = model_registry.get_model(request.plant_species, request.sensor_profile)
    
    # 2. Validate Dimensionality
    # For vis_nir_research, we expect exactly 832 bands.
    if request.sensor_profile == "vis_nir_research" and len(request.spectral_data) != 832:
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid spectral dimensionality for {request.sensor_profile}. Expected 832, got {len(request.spectral_data)}."
        )
    # For as7341, we expect exactly 9 bands (F1-F8 + NIR).
    elif request.sensor_profile == "as7341" and len(request.spectral_data) != 9:
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid spectral dimensionality for {request.sensor_profile}. Expected 9, got {len(request.spectral_data)}."
        )
        
    # 3. Perform Inference
    sample_2d = np.array(request.spectral_data).reshape(1, -1)
    try:
        pred_class = pipeline.predict(sample_2d)[0]
        probs = pipeline.predict_proba(sample_2d)[0]
        
        # Get the confidence for the predicted class
        class_idx = list(pipeline.classes_).index(pred_class)
        confidence = float(probs[class_idx])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
        
    # 4. Map Interpretation
    mapping = INTERPRETATION_MAP.get(pred_class, {
        "diagnosis": "Unknown",
        "interpretation": "No interpretation available.",
        "recommendation": "No recommendation available."
    })
    
    timestamp = request.timestamp or datetime.utcnow()
    measurement_id = str(uuid.uuid4())
    model_id = getattr(pipeline, 'model_id', 'unknown')
    
    # 5. Save to Database
    db_record = models.MeasurementHistory(
        measurement_id=measurement_id,
        plant_species=request.plant_species,
        plant_id=request.plant_id,
        sensor_profile=request.sensor_profile,
        measurement_timestamp=timestamp,
        diagnosis=mapping["diagnosis"],
        model_confidence=confidence,
        severity=None,
        model_id=model_id,
        is_demo=request.is_demo
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    
    # 6. Return Result
    return DiagnosisResult(
        measurement_id=measurement_id,
        plant_species=request.plant_species,
        plant_id=request.plant_id,
        sensor_profile=request.sensor_profile,
        measurement_timestamp=timestamp,
        model_id=model_id,
        diagnosis=mapping["diagnosis"],
        model_confidence=confidence,
        severity=None,
        interpretation=mapping["interpretation"],
        recommendation=mapping["recommendation"],
        is_demo=request.is_demo
    )
