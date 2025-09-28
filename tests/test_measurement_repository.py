import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clorofillo.persistence.orm_models import *
from clorofillo.persistence.measurement_repository import MeasurementRepository
from clorofillo.model.measurement import Measurement 

from datetime import datetime
from unittest.mock import MagicMock



@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def measurement_orm():
    return MeasurementORM(
        id=1,
        timestamp=datetime(2023, 9, 28, 14, 0),
        soil_moisture=45.6,
        plant_pot_id=2
    )


@pytest.fixture
def measurement():
    return Measurement(
        timestamp=datetime(2023, 9, 28, 14, 0),
        soil_moisture=45.6,
        id=1
    )


def test_measurement_from_orm(measurement_orm):
    measurement = Measurement.from_orm(measurement_orm)
    assert measurement.id == 1
    assert measurement.timestamp == datetime(2023, 9, 28, 14, 0)
    assert measurement.soil_moisture == 45.6


def test_measurement_to_orm(measurement):
    orm = measurement.to_orm(plant_pot_id=2)
    assert orm.timestamp == measurement.timestamp
    assert orm.soil_moisture == measurement.soil_moisture
    assert orm.plant_pot_id == 2
    assert orm.id == measurement.id


def test_measurement_repository_get_by_id(mock_session, measurement_orm):
    mock_session.get.return_value = measurement_orm
    repo = MeasurementRepository(mock_session)
    measurement = repo.get_by_id(1)
    assert measurement.id == 1
    assert measurement.timestamp == datetime(2023, 9, 28, 14, 0)
    assert measurement.soil_moisture == 45.6


def test_measurement_repository_get_all(mock_session, measurement_orm):
    mock_session.query.return_value.all.return_value = [measurement_orm]
    repo = MeasurementRepository(mock_session)
    measurements = repo.get_all()
    assert len(measurements) == 1
    assert measurements[0].id == 1
    assert measurements[0].timestamp == datetime(2023, 9, 28, 14, 0)
    assert measurements[0].soil_moisture == 45.6


def test_measurement_repository_insert(mock_session, measurement):
    repo = MeasurementRepository(mock_session)
    repo.insert(measurement)
    mock_session.add.assert_called_once_with(measurement)


def test_measurement_repository_remove(mock_session, measurement):
    repo = MeasurementRepository(mock_session)
    repo.remove(measurement)
    mock_session.delete.assert_called_once_with(measurement)
