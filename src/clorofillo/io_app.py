import sys
sys.path.append('/usr/lib/python3/dist-packages')

import os
import time
from datetime import datetime
from dotenv import load_dotenv

import RPi.GPIO as GPIO
import pigpio
from gpiozero import PWMLED, MCP3008
from picamzero import Camera

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from clorofillo.persistence.orm_models import Base
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository

from clorofillo.model.configuration import Configuration
from clorofillo.model.plant_pot import PlantPot
from clorofillo.model.measurement import Measurement
from clorofillo.model.plant_photo import PlantPhoto

from clorofillo.business.utilities import Utilities
from clorofillo.business.plant_pot_service import PlantPotService
from clorofillo.business.plant_photo_service import PlantPhotoService


humidity_one = MCP3008(0) # read with humidity_one.value()
#humidity_two = MCP3008(1)
#humidity_three = MCP3008(2)
#0.29 max humidiy, 0.82 min umidity

GPIO.setmode(GPIO.BCM)
SERVO_PIN = 17
PUMP_ONE_PIN = 4

GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_ONE_PIN, GPIO.OUT)

pi = pigpio.pi()

# add possibility to disable insect detection
load_dotenv()

engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
conf_repository = ConfigurationRepository(session)
pot_repository = PlantPotRepository(session)
pot_service = PlantPotService(pot_repository)


def main():
    # remember to shut down camera ops when watering (interferenze fra servo e pompe)
    # setta la cofnigurazione dalla repo, se devi innaffiare innaffia e non fare camera, altrimenti fai camera ops
    while (True):
        a = input("calibrate?")
        if (a == "yes"):
            pot_service.calibrate(Camera(), pi, SERVO_PIN, conf_repository)
    
    
    '''
    while (True):
        val = humidity_one.value
        print(val)
        if (val > 0.90):
            GPIO.output(PUMP_ONE_PIN, GPIO.LOW) # do a watering function, more accurate
        else:
            GPIO.output(PUMP_ONE_PIN, GPIO.HIGH) # RELAY shut down at high
        time.sleep(1)
    '''

    '''
    if not pi.connected:
        print("Errore: pigpiod non è attivo. Avvialo con 'sudo pigpiod'")
        return
    
    # il db deve avere gia dentro i tre pot e le loro configurazioni di base
    engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    repo = PlantPotRepository(session)
    photo_repo = PlantPhotoRepository(session)
    service = PlantPhotoService(photo_repo, Camera())


    
    pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(0))
    time.sleep(1)

    last_day = None
    
    try:
        while True:
            pot_one = PlantPot.from_orm(repo.get_by_id(1))
            pot_two = PlantPot.from_orm(repo.get_by_id(2))
            pot_three = PlantPot.from_orm(repo.get_by_id(3))
            insect_freq = 60 / pot_one.configuration.insect_freq
            t_freq_one = pot_one.configuration.shot_freq
            t_freq_two = pot_two.configuration.shot_freq
            t_freq_three = pot_three.configuration.shot_freq

            # Calcola le ore di scatto per ciascun vaso, le aggiorna se scatta il nuovo giorno
            dt = datetime.now()
            now = dt.hour
            current_day = dt.day
            if current_day != last_day:
                last_day = current_day
                hours_one = Utilities.shot_hours(t_freq_one)
                hours_two = Utilities.shot_hours(t_freq_two)
                hours_three = Utilities.shot_hours(t_freq_three)

            # Timelapse photos

            #Se si è nell'ora di scatto scatta la foto e rimuove l'ora dalle ore di scatto
            if now in hours_one:
                hours_one.pop(0)
                pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(0))
                service.timelapse_shot(1, datetime.now())
                time.sleep(2)

            if now in hours_two:
                hours_two.pop(0)
                pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(90))
                service.timelapse_shot(1, datetime.now())
                time.sleep(2)

            if now in hours_three:
                hours_three.pop(0)
                pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(180))
                service.timelapse_shot(1, datetime.now())
                time.sleep(2)

            # Insect detection
            pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(0))
            service.insect_shot(1, datetime.now())
            time.sleep(insect_freq)

            pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(90))
            service.insect_shot(2, datetime.now())
            time.sleep(insect_freq)
            
            #pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(180))
            #service.insect_shot(3, datetime.now())
            #time.sleep(insect_freq)
            

    except KeyboardInterrupt:
        print("Interrotto dall'utente.")

    finally:
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()
        session.close()
        print("Pulizia completata.")
    '''
    

if __name__ == "__main__":
    main()

# per ora, la frequenza di scatto insetto è uguale per tutti i vasi (prende la freq del vaso con id 1)