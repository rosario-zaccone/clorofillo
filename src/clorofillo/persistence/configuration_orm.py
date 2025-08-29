from sqlalchemy import Column, Float, Boolean, Integer
from sqlalchemy.orm import relationship
from .base import Base

class ConfigurationORM(Base):
    __tablename__ = 'configuration'
    id = Column(Integer, primary_key=True, autoincrement=True)
    threshold = Column(Float, nullable=False)
    watering_mode = Column(Boolean, nullable=False)
    shot_freq = Column(Integer, nullable=False)
    insect_freq = Column(Integer, nullable=False)

    # relazione uno-a-uno con PlantPot
    plant_pot = relationship("PlantPotORM", back_populates="configuration", uselist=False)