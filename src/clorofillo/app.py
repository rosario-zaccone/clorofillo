import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from persistence.base import Base
from persistence.configuration_orm import ConfigurationORM
from persistence.measurement_orm import MeasurementORM
from persistence.plant_photo_orm import PlantPhotoORM, PhotoType
from persistence.plant_pot_orm import PlantPotORM

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "test_plantpots.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

def create_db():
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine

def print_plant_pots(session: Session):
    pots = session.query(PlantPotORM).all()
    if not pots:
        print("Nessun plant pot trovato.")
        return
    for pot in pots:
        print(f"ID: {pot.id} | Size: {pot.size} | Plant: {pot.plant} | ConfigurationID: {pot.configuration_id}")

def print_full_plantpot(session: Session, plant_pot_id: int):
    pot = session.query(PlantPotORM).filter_by(id=plant_pot_id).first()
    if not pot:
        print("Plant pot non trovato.")
        return
    print(f"\nPLANT POT")
    print(f"ID: {pot.id}, Size: {pot.size}, Plant: {pot.plant}")
    print(f"Configuration: [ID: {pot.configuration.id}, Threshold: {pot.configuration.threshold}, Watering Mode: {pot.configuration.watering_mode}, Shot Freq: {pot.configuration.shot_freq}, Insect Freq: {pot.configuration.insect_freq}]")
    print("Measurements:")
    for m in pot.measurements:
        print(f"  - ID: {m.id}, Timestamp: {m.timestamp}, Soil Moisture: {m.soil_moisture}")
    print("Photos:")
    for p in pot.photos:
        print(f"  - ID: {p.id}, Timestamp: {p.timestamp}, Type: {p.photo_type}, Path: {p.path}")

def test_plantpot_with_data():
    engine = create_db()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # 1. Create Configuration
    config = ConfigurationORM(
        threshold=45.0,
        watering_mode=False,
        shot_freq=2,
        insect_freq=12
    )
    session.add(config)
    session.commit()
    print(f"Configuration id: {config.id}")

    # 2. Create PlantPot for "Orchidea"
    plant_pot = PlantPotORM(
        size=10.0,
        plant="Orchidea",
        configuration_id=config.id
    )
    session.add(plant_pot)
    session.commit()
    print(f"PlantPot id: {plant_pot.id}")

    # 3. Add 10 measurements (simulate one every 2 hours)
    base_time = datetime(2025, 8, 29, 8, 0, 0)
    measurements = []
    for i in range(10):
        m = MeasurementORM(
            timestamp=base_time + timedelta(hours=2*i),
            soil_moisture=40.0 + i,  # variabile
            plant_pot_id=plant_pot.id
        )
        measurements.append(m)
    session.add_all(measurements)
    session.commit()
    print(f"Measurement ids: {[m.id for m in measurements]}")

    # 4. Add 10 photos (8 timelapse, 2 insect)
    photos = []
    for i in range(8):
        p = PlantPhotoORM(
            timestamp=base_time + timedelta(hours=i),
            photo_type=PhotoType.TIMELAPSE,
            path=f"photos/orchidea_timelapse_{i+1}.jpg",
            plant_pot_id=plant_pot.id
        )
        photos.append(p)
    for i in range(2):
        p = PlantPhotoORM(
            timestamp=base_time + timedelta(hours=8+i),
            photo_type=PhotoType.INSECT,
            path=f"photos/orchidea_insect_{i+1}.jpg",
            plant_pot_id=plant_pot.id
        )
        photos.append(p)
    session.add_all(photos)
    session.commit()
    print(f"Photo ids: {[p.id for p in photos]}")

    # 5. Visualizza dati del vaso appena popolato
    print_full_plantpot(session, plant_pot.id)

    session.close()
    print("\nTest completato. DB file creato in:", DB_PATH)

if __name__ == "__main__":
    test_plantpot_with_data()