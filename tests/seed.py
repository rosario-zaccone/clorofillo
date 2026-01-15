import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.persistence.orm_models import Base, ConfigurationORM, PlantPotORM, PlantPhotoORM, ShotTimeORM

DB_PATH = "data/db_test.sqlite"

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=True, future=True)
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

config1 = ConfigurationORM(
    threshold=55.0,
    watering_mode=True,
    sighting_freq=5,
    position=88,
    size=4.5,
    plant="Primula",
    shot_freq=[ShotTimeORM(hour=10, minute=0), ShotTimeORM(hour=20, minute=0)]
)

config2 = ConfigurationORM(
    threshold=60.0,
    watering_mode=True,
    sighting_freq=6,
    position=90,
    size=6.0,
    plant="Tulip",
    shot_freq=[ShotTimeORM(hour=9, minute=0), ShotTimeORM(hour=18, minute=0)]
)

config3 = ConfigurationORM(
    threshold=50.0,
    watering_mode=False,
    sighting_freq=4,
    position=80,
    size=7.2,
    plant="Rose",
    shot_freq=[ShotTimeORM(hour=8, minute=0), ShotTimeORM(hour=19, minute=0)]
)

pot1 = PlantPotORM(configuration=config1, photos=[])
pot2 = PlantPotORM(configuration=config2, photos=[])
pot3 = PlantPotORM(configuration=config3, photos=[])

session.add_all([pot1, pot2, pot3])
session.commit()

print(f"PlantPot 1 ID: {pot1.id}, plant: {pot1.configuration.plant}")
print(f"PlantPot 2 ID: {pot2.id}, plant: {pot2.configuration.plant}")
print(f"PlantPot 3 ID: {pot3.id}, plant: {pot3.configuration.plant}")

session.close()
print("Database creato e popolato correttamente!")
