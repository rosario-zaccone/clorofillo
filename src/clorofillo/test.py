import os
import base64
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock
from clorofillo.persistence.orm_models import Base
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from clorofillo.business.plant_photo_service import PlantPhotoService

engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
repo = PlantPhotoRepository(session)
s = PlantPhotoService(repo, MagicMock())

s._detect_insect_patches_base64("data/photos/test/a7.jpg", "data/photos/test/a17.jpg", True)

