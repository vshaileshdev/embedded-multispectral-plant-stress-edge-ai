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
        "potential_effects": [
            "Normal vegetative growth",
            "Optimal photosynthetic capacity"
        ],
        "recommendation": "Continue monitoring under the current experimental conditions."
    },
    's': {
        "diagnosis": "Water Deficit (Drought)",
        "interpretation": "Spectral signatures indicate water stress (e.g., changes in carotenoid ratios and cellular scattering).",
        "potential_effects": [
            "Reduced vegetative growth",
            "Physiological stress and reduced turgor",
            "Impaired development under prolonged stress",
            "Potential yield reduction under sustained stress"
        ],
        "recommendation": "Assess plant water availability and restore an appropriate irrigation condition. Re-measure after intervention to monitor recovery."
    },
    'n': {
        "diagnosis": "Nitrogen Deficit",
        "interpretation": "Spectral signatures indicate nitrogen stress (e.g., shifts in the red-edge and chlorophyll absorption).",
        "potential_effects": [
            "Reduced vegetative growth",
            "Chlorosis-related symptoms",
            "Reduced photosynthetic capacity",
            "Potential yield/quality effects under prolonged deficiency"
        ],
        "recommendation": "Assess the plant's nutrient-management condition and verify nitrogen availability according to the cultivation protocol. Re-measure after intervention."
    }
}

from app.core.plant_profiles import PLANT_PROFILES

def process_measurement(db: Session, request: MeasurementRequest) -> DiagnosisResult:
    """
    Runs the inference pipeline.
    """
    
    # 0. Check Plant Profile
    profile = PLANT_PROFILES.get(request.plant_species.lower())
    if not profile:
        raise HTTPException(status_code=400, detail=f"Unsupported plant species: {request.plant_species}")
        
    if not profile["can_diagnose"]:
        raise HTTPException(status_code=400, detail="Plant profile available. A validated plant-specific ML model is not yet available for diagnosis.")
        
    # 1. Select Model Pipeline
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
        
    # 3. Perform Inference & Feature Extraction
    sample_2d = np.array(request.spectral_data).reshape(1, -1)
    try:
        pred_class = pipeline.predict(sample_2d)[0]
        probs = pipeline.predict_proba(sample_2d)[0]
        
        # Build class probabilities dictionary mapping short names to friendly names
        class_probabilities = {}
        for idx, cls in enumerate(pipeline.classes_):
            # some models might have int classes, so we stringify cls fallback
            cls_name = str(INTERPRETATION_MAP.get(cls, {}).get("diagnosis", str(cls)))
            class_probabilities[cls_name] = float(probs[idx])
        
        # Get the confidence for the predicted class
        class_idx = list(pipeline.classes_).index(pred_class)
        confidence = float(probs[class_idx])
        
        # Extract features if available
        features_dict = {}
        top_features = []
        if request.sensor_profile == "vis_nir_research" and 'extractor' in pipeline.named_steps:
            feature_names = [
                "NDVI", "GNDVI", "NDRE", "MCARI", "PSRI", "SIPI", "CRI", "ARI", "WBI", "RE_Slope",
                "VIS_Mean", "RedEdge_Mean", "NIR_Mean", "NIR_Water_Mean"
            ]
            raw_features = pipeline.named_steps['extractor'].transform(sample_2d)[0]
            features_dict = {name: float(val) for name, val in zip(feature_names, raw_features)}
            
            # Extract explainability
            if 'clf' in pipeline.named_steps and hasattr(pipeline.named_steps['clf'], 'feature_importances_'):
                importances = pipeline.named_steps['clf'].feature_importances_
                # Get indices of top 3 features
                top_indices = np.argsort(importances)[::-1][:3]
                top_features = [feature_names[i] for i in top_indices]
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
        
    # 4. Map Interpretation
    mapping = INTERPRETATION_MAP.get(pred_class, {
        "diagnosis": "Unknown",
        "interpretation": "No interpretation available.",
        "potential_effects": ["Unknown effects."],
        "recommendation": "No recommendation available."
    })
    
    timestamp = request.timestamp or datetime.now().astimezone()
    measurement_id = str(uuid.uuid4())
    model_id = getattr(pipeline, 'model_id', 'unknown')
    
    # 5. Save to Database
    import json
    db_record = models.MeasurementHistory(
        measurement_id=measurement_id,
        plant_species=request.plant_species,
        plant_id=request.plant_id,
        sensor_profile=request.sensor_profile,
        experimental_day=request.experimental_day,
        measurement_timestamp=timestamp,
        diagnosis=mapping["diagnosis"],
        model_confidence=confidence,
        severity=None,
        features_json=json.dumps(features_dict),
        top_features_json=json.dumps(top_features),
        class_probabilities_json=json.dumps(class_probabilities),
        model_id=model_id,
        dataset_source="Research Dataset",
        sample_id=request.sample_id
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
        experimental_day=request.experimental_day,
        sample_id=request.sample_id,
        dataset_source="Research Dataset",
        measurement_timestamp=timestamp,
        model_id=model_id,
        diagnosis=mapping["diagnosis"],
        model_confidence=confidence,
        class_probabilities=class_probabilities,
        severity=None,
        features=features_dict,
        top_features=top_features,
        interpretation=mapping["interpretation"],
        potential_effects=mapping["potential_effects"],
        recommendation=mapping["recommendation"]
    )
