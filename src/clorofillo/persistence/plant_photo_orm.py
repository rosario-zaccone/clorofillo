from enum import Enum
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import Base

class PhotoType(Enum):
    TIMELAPSE = "timelapse"
    INSECT = "insect"
    FLOWER = "flower"

class PlantPhotoORM(Base):
    __tablename__ = 'plant_photo'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    photo_type = Column(
        SQLEnum(PhotoType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    path = Column(String, nullable=False)
    plant_pot_id = Column(Integer, ForeignKey('plant_pot.id'), nullable=False)
    plant_pot = relationship("PlantPotORM", back_populates="photos")