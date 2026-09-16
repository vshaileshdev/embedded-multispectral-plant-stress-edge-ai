from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
import uuid
from .session import Base

class MeasurementHistory(Base):
    __tablename__ = "measurement_history"

    id = Column(Integer, primary_key=True, index=True)
    measurement_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    plant_species = Column(String, index=True)
    plant_id = Column(String, index=True)
    sensor_profile = Column(String, index=True)
    measurement_timestamp = Column(DateTime, default=datetime.utcnow)
    
    diagnosis = Column(String)
    model_confidence = Column(Float)
    severity = Column(String, nullable=True)
    
    model_id = Column(String)
    is_demo = Column(Boolean, default=False)
