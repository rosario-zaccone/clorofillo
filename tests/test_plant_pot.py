import sys
import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path to src
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from clorofillo.persistence.orm_models import Base
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from clorofillo.model.plant_pot import PlantPot
from clorofillo.model.configuration import Configuration
from clorofillo.model.measurement import Measurement
from clorofillo.model.plant_photo import PlantPhoto

def main():
    engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    repo = PlantPotRepository(session)

    config = Configuration(
        threshold=55.0,
        watering_mode=True,
        shot_freq=2,
        insect_freq=5
    )

    measurements = [
        Measurement(datetime.now(), 30.0),
        Measurement(datetime.now(), 45.0)
    ]

    photos = [
        PlantPhoto(datetime.now(), False, '/path/to/flower.jpg'),
        PlantPhoto(datetime.now(), True, '/path/to/insect.jpg')
    ]


    plant_pot_domain = PlantPot(
        id=None,
        size=3.5,
        plant="Ficus",
        configuration=config,
        measurements=measurements,
        photos=photos
    )


    plant_pot_orm = plant_pot_domain.to_orm()


    repo.insert(plant_pot_orm)
    session.commit()

    print(f"PlantPot saved with id: {plant_pot_orm.id}")

    loaded_orm = repo.get_by_id(plant_pot_orm.id)
    loaded_domain = PlantPot.from_orm(loaded_orm)

    print("Loaded PlantPot:")
    print(f"id: {loaded_domain.id}")
    print(f"size: {loaded_domain.size}")
    print(f"plant: {loaded_domain.plant}")
    print(f"Configuration threshold: {loaded_domain.configuration.threshold}")
    print(f"Measurements count: {len(loaded_domain.measurements)}")
    print(f"Photos count: {len(loaded_domain.photos)}")


    session.close()

if __name__ == "__main__":
    main()
