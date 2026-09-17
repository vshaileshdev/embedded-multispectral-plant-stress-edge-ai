from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class MeasurementRequest(BaseModel):
    plant_species: str = Field(..., description="E.g., 'tomato'")
    plant_id: str = Field(..., description="Unique biological plant identifier")
    sensor_profile: str = Field(..., description="E.g., 'vis_nir_research'")
    spectral_data: List[float] = Field(..., description="Raw spectral reflectance values")
    experimental_day: str = Field(..., description="E.g., 'D0', 'D2'")
    sample_id: Optional[str] = Field(None, description="Exact dataset sample ID")
    timestamp: Optional[datetime] = None

class DiagnosisResult(BaseModel):
    measurement_id: str
    plant_species: str
    plant_id: str
    sensor_profile: str
    experimental_day: str
    sample_id: Optional[str] = None
    dataset_source: str
    measurement_timestamp: datetime
    model_id: str
    diagnosis: str
    model_confidence: float
    class_probabilities: Dict[str, float]
    severity: Optional[str] = None
    features: Dict[str, float]
    top_features: List[str]
    interpretation: str
    potential_effects: List[str]
    recommendation: str

    class Config:
        orm_mode = True
        from_attributes = True
