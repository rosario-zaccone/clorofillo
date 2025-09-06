import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src'))

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.persistence.orm_models import ConfigurationORM, Base
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.model.configuration import Configuration

def main():
    # Setup DB
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    repo = ConfigurationRepository(session)

    # Model creation
    config_domain = Configuration(
        threshold=60.0,
        watering_mode=True,
        shot_freq=3,
        insect_freq=8
    )

    config_orm = config_domain.to_orm()

    # Insert in DB
    repo.insert(config_orm)
    session.commit()

    print(f"Configuration saved with id: {config_orm.id}")

    # GET from DB
    loaded_orm = repo.get_by_id(config_orm.id)
    loaded_domain = Configuration.from_orm(loaded_orm)

    print("Loaded Configuration:")
    print(loaded_domain)

    # Test None
    if (repo.get_by_id(-1) == None):
        print("Not found")

    session.close()

if __name__ == "__main__":
    main()
