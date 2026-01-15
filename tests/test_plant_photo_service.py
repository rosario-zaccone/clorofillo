import sys
sys.path.append('/usr/lib/python3/dist-packages')


import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock
from clorofillo.persistence.orm_models import Base
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from clorofillo.service.plant_photo_service import PlantPhotoService


# Fixture per il DB in-memory
@pytest.fixture
def in_memory_session():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_timelapse_shot(in_memory_session):
    service = PlantPhotoService(PlantPhotoRepository(in_memory_session), MagicMock())
    dtime = datetime.now()
    readable = str(dtime).replace(" ", "_")
    service.timelapse_shot(1, dtime)
    path = "data/photos/timelapse/" + str(1) + "_" + readable + ".jpg"
    repo = PlantPhotoRepository(in_memory_session)
    assert repo.get_by_id(1).path == path



