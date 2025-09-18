import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clorofillo.persistence.orm_models import Base
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.model.configuration import Configuration

@pytest.fixture
def in_memory_session():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_insert_and_get_by_id(in_memory_session):
    repo = ConfigurationRepository(in_memory_session)

    config_domain = Configuration(
        threshold=60.0,
        watering_mode=True,
        shot_freq=3,
        insect_freq=8
    )

    config_orm = config_domain.to_orm()
    repo.insert(config_orm)
    in_memory_session.commit()

    loaded_orm = repo.get_by_id(config_orm.id)
    loaded_domain = Configuration.from_orm(loaded_orm)

    assert loaded_domain.threshold == 60.0
    assert loaded_domain.watering_mode is True
    assert loaded_domain.shot_freq == 3
    assert loaded_domain.insect_freq == 8

def test_get_by_id_not_found(in_memory_session):
    repo = ConfigurationRepository(in_memory_session)
    result = repo.get_by_id(-1)
    assert result is None
