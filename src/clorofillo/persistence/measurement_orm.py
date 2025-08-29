from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, ForeignKey
from .base import Base
from sqlalchemy.orm import relationship

class MeasurementORM(Base):
    __tablename__ = 'measurements'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    soil_moisture = Column(Float, nullable=False)
    plant_pot_id = Column(Integer, ForeignKey('plant_pot.id'), nullable=False)

    plant_pot = relationship("PlantPotORM", back_populates="measurements")