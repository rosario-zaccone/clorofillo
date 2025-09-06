import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '..', 'src'))

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from clorofillo.persistence.orm_models import Base, PlantPotORM
from clorofillo.persistence.measurement_repository import MeasurementRepository
from clorofillo.model.measurement import Measurement

def main():
    engine = create_engine('sqlite:///:memory:', echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    plant_pot = PlantPotORM(size=3.0, plant="Monstera")
    session.add(plant_pot)
    session.commit()

    repo = MeasurementRepository(session)

    measurement_domain = Measurement(
        timestamp=datetime.now(),
        soil_moisture=45.5
    )

    measurement_orm = measurement_domain.to_orm(plant_pot_id=plant_pot.id)

    repo.insert(measurement_orm)
    session.commit()

    print(f"Measurement saved with id: {measurement_orm.id}")

    loaded_orm = repo.get_by_id(measurement_orm.id)
    loaded_domain = Measurement.from_orm(loaded_orm)

    print("Loaded Measurement:")
    print(f"id: {loaded_domain.id}")
    print(f"timestamp: {loaded_domain.timestamp}")
    print(f"soil_moisture: {loaded_domain.soil_moisture}")

    if repo.get_by_id(-1) is None:
        print("Not found")

    all_measurements = repo.get_all()
    print(f"Total measurements in DB: {len(all_measurements)}")

    try:
        invalid_measurement = Measurement(timestamp=datetime.now(), soil_moisture=150)
    except ValueError as e:
        print(f"Caught expected exception: {e}")

    session.close()

if __name__ == "__main__":
    main()
