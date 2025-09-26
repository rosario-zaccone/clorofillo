import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.persistence.orm_models import Base
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from clorofillo.model.plant_pot import PlantPot
from clorofillo.model.configuration import Configuration
from clorofillo.model.measurement import Measurement
from clorofillo.model.plant_photo import PlantPhoto
from clorofillo.business.plant_pot_service import PlantPotService

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)


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
        insect_freq=5,
        position = 88
    )


    plant_pot_domain = PlantPot(
        id=None,
        size=4.5,
        plant="Primula",
        configuration=config,
        measurements=[],
        photos=[]
    )

    directory = 'data/photos/timelapse/'


    file_names = []
    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path) and filename[0] == "1":
            file_names.append(directory + filename)

    for file in file_names:
        photo = PlantPhoto(datetime.strptime(file.split('_')[1].split('.')[0], "%Y%m%d"), False, file)
        plant_pot_domain.add_photo(photo)

    plant_pot_orm = plant_pot_domain.to_orm()


    repo.insert(plant_pot_orm)
    session.commit()

    print(f"PlantPot saved with id: {plant_pot_orm.id}")
    
    loaded_orm = repo.get_by_id(1)
    loaded_domain = PlantPot.from_orm(loaded_orm)

    print(loaded_domain)

    service = PlantPotService(repo)
    service.timelapse(1, datetime(2024,1,10), datetime(2024,10,14), 10, "pippo.mp4")

    

if __name__ == "__main__":
    main()
