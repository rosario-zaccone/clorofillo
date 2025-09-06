import sys
import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src'))

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from clorofillo.persistence.orm_models import PlantPhotoORM, PlantPotORM, Base
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from clorofillo.model.plant_photo import PlantPhoto

def main():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    plant_pot = PlantPotORM(size=2.5, plant="Ficus")
    session.add(plant_pot)
    session.commit()  

    repo = PlantPhotoRepository(session)

    timestamp = datetime.now()
    photo_domain = PlantPhoto(
        timestamp=timestamp,
        is_insect=True,
        path='/path/to/photo.jpg'
    )

    photo_orm = photo_domain.to_orm(plant_pot_id=plant_pot.id)

    repo.insert(photo_orm)
    session.commit()

    print(f"PlantPhoto saved with id: {photo_orm.id}")

    loaded_orm = repo.get_by_id(photo_orm.id)
    loaded_domain = PlantPhoto.from_orm(loaded_orm)

    print("Loaded PlantPhoto:")
    print(f"id: {loaded_domain.id}")
    print(f"timestamp: {loaded_domain.timestamp}")
    print(f"is_insect: {loaded_domain.is_insect}")
    print(f"path: {loaded_domain.path}")

    if repo.get_by_id(-1) is None:
        print("Not found")

    all_photos = repo.get_all()
    print(f"Total photos in DB: {len(all_photos)}")

    session.close()

if __name__ == "__main__":
    main()
