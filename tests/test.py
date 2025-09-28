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

# Add the src path to sys.path if not already there
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)


def main():
    # Set up the database connection
    engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    repo = PlantPotRepository(session)

    # Create three different configurations for the plant pots
    config1 = Configuration(
        threshold=55.0,
        watering_mode=True,
        shot_freq=2,
        insect_freq=5,
        position=88,
        size=4.5,        # Add size
        plant="Primula"  # Add plant
    )

    config2 = Configuration(
        threshold=60.0,
        watering_mode=True,
        shot_freq=3,
        insect_freq=6,
        position=90,
        size=6.0,        # Add size
        plant="Tulip"    # Add plant
    )

    config3 = Configuration(
        threshold=50.0,
        watering_mode=False,
        shot_freq=1,
        insect_freq=4,
        position=80,
        size=7.2,        # Add size
        plant="Rose"     # Add plant
    )

    # Create three different plant pots with their respective configurations
    plant_pot1 = PlantPot(
        id=None,
        configuration=config1,  # Link to the first configuration
        measurements=[],
        photos=[]
    )

    plant_pot2 = PlantPot(
        id=None,
        configuration=config2,  # Link to the second configuration
        measurements=[],
        photos=[]
    )

    plant_pot3 = PlantPot(
        id=None,
        configuration=config3,  # Link to the third configuration
        measurements=[],
        photos=[]
    )

    # Directory to fetch photo files
    directory = 'data/photos/timelapse/'

    file_names = []
    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path) and filename[0] == "1":
            file_names.append(directory + filename)

    # Add photos to each pot
    for file in file_names:
        photo = PlantPhoto(datetime.strptime(file.split('_')[1].split('.')[0], "%Y-%m-%d"), False, file)
        plant_pot1.add_photo(photo)
        plant_pot2.add_photo(photo)
        plant_pot3.add_photo(photo)

    # Convert the plant pot objects to ORM objects
    plant_pot_orm1 = plant_pot1.to_orm()
    plant_pot_orm2 = plant_pot2.to_orm()
    plant_pot_orm3 = plant_pot3.to_orm()

    # Insert the pots into the database
    repo.insert(plant_pot_orm1)
    repo.insert(plant_pot_orm2)
    repo.insert(plant_pot_orm3)
    session.commit()

    print(f"PlantPot 1 saved with id: {plant_pot_orm1.id}")
    print(f"PlantPot 2 saved with id: {plant_pot_orm2.id}")
    print(f"PlantPot 3 saved with id: {plant_pot_orm3.id}")

    # Retrieve and print the saved plant pots
    loaded_orm1 = repo.get_by_id(plant_pot_orm1.id)
    loaded_domain1 = PlantPot.from_orm(loaded_orm1)
    print(f"Loaded PlantPot 1: {loaded_domain1}")

    loaded_orm2 = repo.get_by_id(plant_pot_orm2.id)
    loaded_domain2 = PlantPot.from_orm(loaded_orm2)
    print(f"Loaded PlantPot 2: {loaded_domain2}")

    loaded_orm3 = repo.get_by_id(plant_pot_orm3.id)
    loaded_domain3 = PlantPot.from_orm(loaded_orm3)
    print(f"Loaded PlantPot 3: {loaded_domain3}")


    service = PlantPotService(repo)
    service.timelapse(1, datetime(2024, 1, 10), datetime(2024, 10, 14), 10, "pippo.mp4")


if __name__ == "__main__":
    main()
