import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clorofillo.persistence.orm_models import Base, PlantPotORM
from clorofillo.persistence.measurement_repository import MeasurementRepository
from clorofillo.model.measurement import Measurement

# Fixture per DB e sessione
@pytest.fixture
def in_memory_session():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

# Fixture per il vaso
@pytest.fixture
def plant_pot(in_memory_session):
    pot = PlantPotORM(size=3.0, plant="Monstera")
    in_memory_session.add(pot)
    in_memory_session.commit()
    return pot

def test_insert_and_get_measurement(in_memory_session, plant_pot):
    repo = MeasurementRepository(in_memory_session)

    measurement_domain = Measurement(
        timestamp=datetime.now(),
        soil_moisture=45.5
    )
    measurement_orm = measurement_domain.to_orm(plant_pot_id=plant_pot.id)

    repo.insert(measurement_orm)
    in_memory_session.commit()

    # Verifica inserimento
    loaded_orm = repo.get_by_id(measurement_orm.id)
    assert loaded_orm is not None

    loaded_domain = Measurement.from_orm(loaded_orm)

    assert loaded_domain.id == measurement_orm.id
    assert loaded_domain.soil_moisture == 45.5

def test_get_by_id_not_found(in_memory_session):
    repo = MeasurementRepository(in_memory_session)
    result = repo.get_by_id(-1)
    assert result is None

def test_get_all_measurements(in_memory_session, plant_pot):
    repo = MeasurementRepository(in_memory_session)

    m1 = Measurement(timestamp=datetime.now(), soil_moisture=30.0).to_orm(plant_pot_id=plant_pot.id)
    m2 = Measurement(timestamp=datetime.now(), soil_moisture=50.0).to_orm(plant_pot_id=plant_pot.id)

    repo.insert(m1)
    repo.insert(m2)
    in_memory_session.commit()

    all_measurements = repo.get_all()
    assert len(all_measurements) == 2

def test_invalid_measurement_value():
    with pytest.raises(ValueError) as e:
        Measurement(timestamp=datetime.now(), soil_moisture=150)

    assert "soil_moisture must be between 0 and 100" in str(e.value)
