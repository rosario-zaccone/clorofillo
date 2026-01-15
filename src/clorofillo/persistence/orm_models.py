from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base


Base = declarative_base()

class ShotTimeORM(Base):
    __tablename__ = 'shot_time'

    id = Column(Integer, primary_key=True, autoincrement=True)
    configuration_id = Column(Integer, ForeignKey('configuration.id'), nullable=False)
    hour = Column(Integer, nullable=False)
    minute = Column(Integer, nullable=False)

    configuration = relationship("ConfigurationORM", back_populates="shot_freq")

class ConfigurationORM(Base):
    __tablename__ = 'configuration'

    id = Column(Integer, primary_key=True, autoincrement=True)
    threshold = Column(Float, nullable=False)
    watering_mode = Column(Boolean, nullable=False)
    sighting_freq = Column(Integer, nullable=False)
    position = Column(Integer, nullable=True)
    size = Column(Float, nullable=False)
    plant = Column(String, nullable=False)

    shot_freq = relationship(
        "ShotTimeORM",
        back_populates="configuration",
        cascade="all, delete-orphan"
    )

    plant_pot = relationship("PlantPotORM", back_populates="configuration", uselist=False)


class PlantPotORM(Base):
    __tablename__ = 'plant_pot'
    id = Column(Integer, primary_key=True, autoincrement=True)
    configuration_id = Column(Integer, ForeignKey('configuration.id'), unique=True)
    configuration = relationship("ConfigurationORM", back_populates="plant_pot", uselist=False)
    photos = relationship("PlantPhotoORM", back_populates="plant_pot", cascade="all, delete-orphan")


class PlantPhotoORM(Base):
    __tablename__ = 'plant_photo'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    is_sighting = Column(Boolean, nullable=False)
    path = Column(String, nullable=False)
    plant_pot_id = Column(Integer, ForeignKey('plant_pot.id'), nullable=False)
    plant_pot = relationship("PlantPotORM", back_populates="photos")
