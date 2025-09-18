from sqlalchemy import *
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import declarative_base


Base = declarative_base()

class ConfigurationORM(Base):
    __tablename__ = 'configuration'
    id = Column(Integer, primary_key=True, autoincrement=True)
    threshold = Column(Float, nullable=False)
    watering_mode = Column(Boolean, nullable=False)
    shot_freq = Column(Integer, nullable=False)
    insect_freq = Column(Integer, nullable=False)
    plant_pot = relationship("PlantPotORM", back_populates="configuration", uselist=False)

class PlantPotORM(Base):
    __tablename__ = 'plant_pot'
    id = Column(Integer, primary_key=True, autoincrement=True)
    size = Column(Float, nullable=False)
    plant = Column(String, nullable=False)
    configuration_id = Column(Integer, ForeignKey('configuration.id'), unique=True)
    configuration = relationship("ConfigurationORM", back_populates="plant_pot", uselist=False)
    measurements = relationship("MeasurementORM", back_populates="plant_pot", cascade="all, delete-orphan")
    photos = relationship("PlantPhotoORM", back_populates="plant_pot", cascade="all, delete-orphan")

class MeasurementORM(Base):
    __tablename__ = 'measurements'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    soil_moisture = Column(Float, nullable=False)
    plant_pot_id = Column(Integer, ForeignKey('plant_pot.id'), nullable=False)
    plant_pot = relationship("PlantPotORM", back_populates="measurements")

class PhotoType(Enum):
    TIMELAPSE = "timelapse"
    INSECT = "insect"
    FLOWER = "flower"

class PlantPhotoORM(Base):
    __tablename__ = 'plant_photo'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    is_insect = Column(Boolean, nullable=False)  # booleano al posto di enum
    path = Column(String, nullable=False)
    plant_pot_id = Column(Integer, ForeignKey('plant_pot.id'), nullable=False)
    plant_pot = relationship("PlantPotORM", back_populates="photos")

class NotificationORM(Base):
    __tablename__ = 'notification'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    pot = Column(Integer, ForeignKey('plant_pot.id'), nullable=False)
    description = Column(String, nullable=False)
    plant_pot = relationship("PlantPotORM")
