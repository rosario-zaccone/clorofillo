from sqlalchemy import (
    Column, Float, Boolean, Integer, DateTime, String,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from .base import Base

class PlantPotORM(Base):
    __tablename__ = 'plant_pot'
    id = Column(Integer, primary_key=True, autoincrement=True)
    size = Column(Float, nullable=False)
    plant = Column(String, nullable=False)
    configuration_id = Column(Integer, ForeignKey('configuration.id'), unique=True)
    configuration = relationship("ConfigurationORM", back_populates="plant_pot", uselist=False)

    # relazione uno-a-molti con Measurement
    measurements = relationship("MeasurementORM", back_populates="plant_pot", cascade="all, delete-orphan")

    # relazione uno-a-molti con PlantPhoto
    photos = relationship("PlantPhotoORM", back_populates="plant_pot", cascade="all, delete-orphan")