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
import RPi.GPIO as GPIO
import time
from clorofillo.business.utilities import Utilities



GPIO.setmode(GPIO.BCM)
SERVO_PIN = 17
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)


def main():
    engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    repo = PlantPotRepository(session)
    try:
        pot_one = PlantPot.from_orm(repo.get_by_id(1))
        pot_two = PlantPot.from_orm(repo.get_by_id(2))
        # pot_three = PlantPot.from_orm(repo.get_by_id(3))  # opzionale
        insect_freq = pot_one.configuration.insect_freq

        pwm.start(Utilities.angle_to_percent(0))  # Posizione iniziale
        time.sleep(1)


        while True:
            pwm.ChangeDutyCycle(Utilities.angle_to_percent(0))
            #shot()
            time.sleep(2)

            pwm.ChangeDutyCycle(Utilities.angle_to_percent(90))
            #shot()
            time.sleep(2)

            pwm.ChangeDutyCycle(Utilities.angle_to_percent(180))
            #shot()
            time.sleep(2)

    except KeyboardInterrupt:
        print("Interrotto dall'utente.")

    finally:
        pwm.stop()
        GPIO.cleanup()
        session.close()
        print("Pulizia completata.")

    

if __name__ == "__main__":
    main()

# per ora, la frequenza di scatto insetto è uguale per tutti i vasi (prende la freq del vaso con id 1)