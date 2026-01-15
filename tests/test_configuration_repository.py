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


@pytest.fixture
def config_domain_valid():
    return Configuration(
        threshold=60.0,
        watering_mode=True,
        shot_freq=["08:00", "12:00", "18:00"], 
        sighting_freq=8,
        position=88,
        size=10.5,
        plant="Tomato"
    )



@pytest.fixture
def config_orm(config_domain_valid):
    return config_domain_valid.to_orm()


def test_insert_and_get_by_id(in_memory_session, config_orm):
    repo = ConfigurationRepository(in_memory_session)
    repo.insert(config_orm)
    in_memory_session.commit()

    loaded_orm = repo.get_by_id(config_orm.id)
    loaded_domain = Configuration.from_orm(loaded_orm)

    assert loaded_domain.threshold == config_orm.threshold
    assert loaded_domain.watering_mode == config_orm.watering_mode
    assert [ (t.hour, t.minute) for t in loaded_domain.shot_freq ] == [
    (st.hour, st.minute) for st in config_orm.shot_freq ]
    assert loaded_domain.sighting_freq == config_orm.sighting_freq
    assert loaded_domain.position == config_orm.position
    assert loaded_domain.size == config_orm.size
    assert loaded_domain.plant == config_orm.plant


def test_get_all(in_memory_session, config_orm):
    repo = ConfigurationRepository(in_memory_session)

    config_orm_2 = Configuration(
    threshold=50.0,
    watering_mode=False,
    shot_freq=["09:00", "13:00", "17:00", "21:00"],
    sighting_freq=10,
    position=99,
    size=12.5,
    plant="Cucumber"
    ).to_orm()

    repo.insert(config_orm)
    repo.insert(config_orm_2)
    in_memory_session.commit()

    configs = repo.get_all()

    assert len(configs) == 2
    assert configs[0].id == config_orm.id
    assert configs[1].id == config_orm_2.id


def test_get_by_id_not_found(in_memory_session):
    repo = ConfigurationRepository(in_memory_session)
    result = repo.get_by_id(-1)
    assert result is None


def test_remove(in_memory_session, config_orm):
    repo = ConfigurationRepository(in_memory_session)
    repo.insert(config_orm)
    in_memory_session.commit()

    repo.remove(config_orm)
    in_memory_session.commit()

    loaded_orm = repo.get_by_id(config_orm.id)
    assert loaded_orm is None
