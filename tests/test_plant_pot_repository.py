import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from clorofillo.persistence.orm_models import Base, ConfigurationORM, PlantPotORM, MeasurementORM, PlantPhotoORM, ShotTimeORM

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
        insect_freq=5,
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

def test_insert_measurement(in_memory_session):
    config = ConfigurationORM(
        threshold=55.0,
        watering_mode=False,
        shot_freq=[
            ShotTimeORM(hour=10, minute=0),
            ShotTimeORM(hour=20, minute=0)
        ],
        insect_freq=4,
        position=80,
        size=7.0,
        plant="Rose"
    )
    plant_pot = PlantPotORM(configuration=config)
    in_memory_session.add(plant_pot)
    in_memory_session.commit()
    measurement = MeasurementORM(
        soil_moisture=23.5,
        plant_pot_id=plant_pot.id
    )
    in_memory_session.add(measurement)
    in_memory_session.commit()
    loaded_measurement = in_memory_session.get(MeasurementORM, measurement.id)
    assert loaded_measurement is not None
    assert loaded_measurement.soil_moisture == 23.5
    assert loaded_measurement.plant_pot_id == plant_pot.id

def test_insert_plant_photo(in_memory_session):
    config = ConfigurationORM(
        threshold=50.0,
        watering_mode=True,
        shot_freq=[
            ShotTimeORM(hour=10, minute=0),
            ShotTimeORM(hour=20, minute=0)
        ],
        insect_freq=3,
        position=75,
        size=5.0,
        plant="Lily"
    )
    plant_pot = PlantPotORM(configuration=config)
    in_memory_session.add(plant_pot)
    in_memory_session.commit()
    photo = PlantPhotoORM(
        timestamp=datetime.now(),
        is_insect=False,
        path="data/photos/lily1.jpg",
        plant_pot_id=plant_pot.id
    )
    in_memory_session.add(photo)
    in_memory_session.commit()
    loaded_photo = in_memory_session.get(PlantPhotoORM, photo.id)
    assert loaded_photo is not None
    assert loaded_photo.path == "data/photos/lily1.jpg"
    assert loaded_photo.is_insect is False

def test_plant_pot_with_multiple_measurements_and_photos(in_memory_session):
    config = ConfigurationORM(
        threshold=60.0,
        watering_mode=True,
        shot_freq=[
            ShotTimeORM(hour=10, minute=0),
            ShotTimeORM(hour=20, minute=0)
        ],
        insect_freq=6,
        position=85,
        size=8.0,
        plant="Cactus"
    )
    plant_pot = PlantPotORM(configuration=config)
    in_memory_session.add(plant_pot)
    in_memory_session.commit()
    measurement1 = MeasurementORM(soil_moisture=15.0, plant_pot_id=plant_pot.id)
    measurement2 = MeasurementORM(soil_moisture=18.5, plant_pot_id=plant_pot.id)
    in_memory_session.add_all([measurement1, measurement2])
    in_memory_session.commit()
    photo1 = PlantPhotoORM(timestamp=datetime.now(), is_insect=False, path="data/photos/cactus1.jpg", plant_pot_id=plant_pot.id)
    photo2 = PlantPhotoORM(timestamp=datetime.now(), is_insect=True, path="data/photos/cactus2.jpg", plant_pot_id=plant_pot.id)
    in_memory_session.add_all([photo1, photo2])
    in_memory_session.commit()
    loaded_pot = in_memory_session.get(PlantPotORM, plant_pot.id)
    assert len(loaded_pot.measurements) == 2
    assert len(loaded_pot.photos) == 2
    assert loaded_pot.measurements[0].soil_moisture == 15.0
    assert loaded_pot.photos[0].path == "data/photos/cactus1.jpg"