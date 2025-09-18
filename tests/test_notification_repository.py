import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from clorofillo.persistence.orm_models import Base
from clorofillo.persistence.notification_repository import NotificationRepository
from clorofillo.model.notification import Notification

# Fixture per sessione in-memory
@pytest.fixture
def in_memory_session():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_insert_and_get_notification(in_memory_session):
    repo = NotificationRepository(in_memory_session)

    notif = Notification(
        id=None,
        timestamp=datetime.now(),
        pot=1,
        description="Test: livello acqua basso"
    )

    notif_orm = notif.to_orm()
    repo.insert(notif_orm)
    in_memory_session.commit()

    # Controlla che sia stato assegnato un ID
    assert notif_orm.id is not None

    # Recupera dal DB
    loaded_orm = repo.get_by_id(notif_orm.id)
    loaded_notif = Notification.from_orm(loaded_orm)

    assert loaded_notif.id == notif_orm.id
    assert loaded_notif.pot == 1
    assert loaded_notif.description == "Test: livello acqua basso"
    assert isinstance(loaded_notif.timestamp, datetime)

def test_get_notification_not_found(in_memory_session):
    repo = NotificationRepository(in_memory_session)
    result = repo.get_by_id(-1)
    assert result is None
