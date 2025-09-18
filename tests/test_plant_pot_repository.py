import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clorofillo.persistence.orm_models import PlantPotORM, PlantPhotoORM
from clorofillo.persistence.repository import Repository
from clorofillo.persistence.plant_pot_repository import PlantPotRepository 

@pytest.fixture(scope="function")
def session():
    engine = create_engine("sqlite:///:memory:")
    PlantPotORM.metadata.create_all(engine)
    PlantPhotoORM.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def repository(session):
    return PlantPotRepository(session)

def test_insert_and_get_by_id(repository, session):
    plant_pot = PlantPotORM(size=5.0, plant="Basil")
    repository.insert(plant_pot)
    session.commit()

    fetched = repository.get_by_id(plant_pot.id)
    assert fetched is not None
    assert fetched.plant == "Basil"

def test_get_all(repository, session):
    plant_pot1 = PlantPotORM(size=7.0, plant="Rosemary")
    plant_pot2 = PlantPotORM(size=8.0, plant="Mint")
    repository.insert(plant_pot1)
    repository.insert(plant_pot2)
    session.commit()

    all_pots = repository.get_all()
    assert len(all_pots) == 2

def test_remove(repository, session):
    plant_pot = PlantPotORM(size=4.0, plant="Lavender")
    repository.insert(plant_pot)
    session.commit()

    repository.remove(plant_pot)
    session.commit()

    assert repository.get_by_id(plant_pot.id) is None

def test_get_photos_by_date_range(repository, session):
    # crea un PlantPotORM necessario per la relazione
    plant_pot = PlantPotORM(size=10.0, plant="Tomato")
    session.add(plant_pot)
    session.commit()

    base_date = datetime.now()
    photo1 = PlantPhotoORM(timestamp=base_date - timedelta(days=2), is_insect=False, path="path1.jpg", plant_pot_id=plant_pot.id)
    photo2 = PlantPhotoORM(timestamp=base_date - timedelta(days=1), is_insect=True, path="path2.jpg", plant_pot_id=plant_pot.id)
    photo3 = PlantPhotoORM(timestamp=base_date, is_insect=False, path="path3.jpg", plant_pot_id=plant_pot.id)
    photo4 = PlantPhotoORM(timestamp=base_date + timedelta(days=1), is_insect=False, path="path4.jpg", plant_pot_id=plant_pot.id)
    session.add_all([photo1, photo2, photo3, photo4])
    session.commit()

    results = repository.get_photos_by_date_range(
        plant_pot_id=plant_pot.id,
        date_from=base_date - timedelta(days=3),
        date_to=base_date + timedelta(days=1),
    )

    assert len(results) == 3
    assert all(photo.is_insect is False for photo in results)
    assert results[0].timestamp <= results[1].timestamp <= results[2].timestamp

def test_get_photos_by_date_range_invalid_dates(repository):
    with pytest.raises(ValueError):
        repository.get_photos_by_date_range(1, datetime(2023, 1, 2), datetime(2023, 1, 1))
