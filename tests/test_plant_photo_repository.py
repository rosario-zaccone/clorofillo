import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clorofillo.persistence.orm_models import Base, PlantPotORM
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from clorofillo.model.plant_photo import PlantPhoto

# Fixture per il DB in-memory
@pytest.fixture
def in_memory_session():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

# Fixture per inserire un vaso
@pytest.fixture
def plant_pot(in_memory_session):
    pot = PlantPotORM(size=2.5, plant="Ficus")
    in_memory_session.add(pot)
    in_memory_session.commit()
    return pot

def test_insert_and_get_plant_photo(in_memory_session, plant_pot):
    repo = PlantPhotoRepository(in_memory_session)

    timestamp = datetime.now()
    photo_domain = PlantPhoto(
        timestamp=timestamp,
        is_insect=True,
        path='/path/to/photo.jpg'
    )

    photo_orm = photo_domain.to_orm(plant_pot_id=plant_pot.id)
    repo.insert(photo_orm)
    in_memory_session.commit()

    assert photo_orm.id is not None

    loaded_orm = repo.get_by_id(photo_orm.id)
    loaded_domain = PlantPhoto.from_orm(loaded_orm)

    assert loaded_domain.id == photo_orm.id
    assert loaded_domain.timestamp == timestamp
    assert loaded_domain.is_insect is True
    assert loaded_domain.path == '/path/to/photo.jpg'

def test_get_plant_photo_not_found(in_memory_session):
    repo = PlantPhotoRepository(in_memory_session)
    assert repo.get_by_id(-1) is None

def test_get_all_plant_photos(in_memory_session, plant_pot):
    repo = PlantPhotoRepository(in_memory_session)

    photo1 = PlantPhoto(timestamp=datetime.now(), is_insect=False, path='a.jpg').to_orm(plant_pot_id=plant_pot.id)
    photo2 = PlantPhoto(timestamp=datetime.now(), is_insect=True, path='b.jpg').to_orm(plant_pot_id=plant_pot.id)

    repo.insert(photo1)
    repo.insert(photo2)
    in_memory_session.commit()

    all_photos = repo.get_all()
    assert len(all_photos) == 2
    paths = [p.path for p in all_photos]
    assert 'a.jpg' in paths
    assert 'b.jpg' in paths
