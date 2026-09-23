from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PlantCreate(BaseModel):
    plant_id: str
    name: str
    species: str
    cultivar: Optional[str] = None
    soil_type: Optional[str] = None
    soil_condition: Optional[str] = None
    soil_ph: Optional[float] = None
    watering_regime: Optional[str] = None
    nutrient_regime: Optional[str] = None
    date_acquired: Optional[str] = None
    growth_stage: Optional[str] = None
    initial_condition: Optional[str] = None
    expected_yield: Optional[str] = None
    yield_notes: Optional[str] = None
    additional_notes: Optional[str] = None

class PlantResponse(PlantCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    active: bool

    class Config:
        from_attributes = True
