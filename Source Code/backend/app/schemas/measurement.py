from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class MeasurementRequest(BaseModel):
    plant_species: str = Field(..., description="E.g., 'tomato'")
    plant_id: str = Field(..., description="Unique biological plant identifier")
    sensor_profile: str = Field(..., description="E.g., 'vis_nir_research'")
    spectral_data: List[float] = Field(..., description="Raw spectral reflectance values")
    is_demo: bool = Field(False, description="Flag indicating if this is a demo measurement")
    timestamp: Optional[datetime] = None

class DiagnosisResult(BaseModel):
    measurement_id: str
    plant_species: str
    plant_id: str
    sensor_profile: str
    measurement_timestamp: datetime
    model_id: str
    diagnosis: str
    model_confidence: float
    severity: Optional[str] = None
    interpretation: str
    recommendation: str
    is_demo: bool

    class Config:
        orm_mode = True
        from_attributes = True
