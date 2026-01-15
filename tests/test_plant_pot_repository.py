import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from clorofillo.persistence.orm_models import Base, ConfigurationORM, PlantPotORM, PlantPhotoORM, ShotTimeORM

@pytest.fixture
def in_memory_session():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_insert_plant_pot_with_configuration(in_memory_session):
    config = ConfigurationORM(
        threshold=60.0,
        watering_mode=True,
        shot_freq=[
            ShotTimeORM(hour=10, minute=0),
            ShotTimeORM(hour=20, minute=0)
        ],
        sighting_freq=5,
        position=90,
        size=6.5,
        plant="Tulip"
    )
    plant_pot = PlantPotORM(configuration=config)
    in_memory_session.add(plant_pot)
    in_memory_session.commit()

    assert plant_pot.id is not None
    assert plant_pot.configuration_id is not None

    loaded_pot = in_memory_session.get(PlantPotORM, plant_pot.id)
    assert loaded_pot is not None
    assert loaded_pot.configuration.plant == "Tulip"

def test_insert_plant_photo(in_memory_session):
    config = ConfigurationORM(
        threshold=50.0,
        watering_mode=True,
        shot_freq=[
            ShotTimeORM(hour=10, minute=0),
            ShotTimeORM(hour=20, minute=0)
        ],
        sighting_freq=3,
        position=75,
        size=5.0,
        plant="Lily"
    )
    plant_pot = PlantPotORM(configuration=config)
    in_memory_session.add(plant_pot)
    in_memory_session.commit()

    photo = PlantPhotoORM(
        timestamp=datetime.now(),
        is_sighting=False,
        path="data/photos/lily1.jpg",
        plant_pot_id=plant_pot.id
    )
    in_memory_session.add(photo)
    in_memory_session.commit()

    loaded_photo = in_memory_session.get(PlantPhotoORM, photo.id)
    assert loaded_photo is not None
    assert loaded_photo.path == "data/photos/lily1.jpg"
    assert loaded_photo.is_sighting is False

def test_plant_pot_with_multiple_photos(in_memory_session):
    config = ConfigurationORM(
        threshold=60.0,
        watering_mode=True,
        shot_freq=[
            ShotTimeORM(hour=10, minute=0),
            ShotTimeORM(hour=20, minute=0)
        ],
        sighting_freq=6,
        position=85,
        size=8.0,
        plant="Cactus"
    )
    plant_pot = PlantPotORM(configuration=config)
    in_memory_session.add(plant_pot)
    in_memory_session.commit()

    photo1 = PlantPhotoORM(
        timestamp=datetime.now(),
        is_sighting=False,
        path="data/photos/cactus1.jpg",
        plant_pot_id=plant_pot.id
    )
    photo2 = PlantPhotoORM(
        timestamp=datetime.now(),
        is_sighting=True,
        path="data/photos/cactus2.jpg",
        plant_pot_id=plant_pot.id
    )
    in_memory_session.add_all([photo1, photo2])
    in_memory_session.commit()

    loaded_pot = in_memory_session.get(PlantPotORM, plant_pot.id)
    assert len(loaded_pot.photos) == 2
    assert loaded_pot.photos[0].path == "data/photos/cactus1.jpg"
