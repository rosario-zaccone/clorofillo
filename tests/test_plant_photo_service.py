import sys
sys.path.append('/usr/lib/python3/dist-packages')


import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock
from clorofillo.persistence.orm_models import Base, PlantPotORM
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from clorofillo.model.plant_photo import PlantPhoto
from clorofillo.business.plant_photo_service import PlantPhotoService
from picamzero import Camera


# Fixture per il DB in-memory
@pytest.fixture
def in_memory_session():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_camera(in_memory_session):
    service = PlantPhotoService(PlantPhotoRepository(in_memory_session), Camera())
    service.shot("prova.jpg")



