import sys
sys.path.append('/usr/lib/python3/dist-packages')

import os
import time, redis
from datetime import datetime
from dotenv import load_dotenv

import RPi.GPIO as GPIO
import pigpio
from gpiozero import PWMLED, MCP3008
from picamzero import Camera

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from clorofillo.persistence.measurement_repository import MeasurementRepository
from clorofillo.model.plant_pot import PlantPot
from clorofillo.business.utilities import Utilities
from clorofillo.business.plant_pot_service import PlantPotService
from clorofillo.business.plant_photo_service import PlantPhotoService


GPIO.setmode(GPIO.BCM)
SERVO_PIN = 17
PUMP_ONE_PIN = 4
PUMP_TWO_PIN = 4 # da cmabaire
PUMP_THREE_PIN = 4 # da cambiare
FLOW_RATE = 0.025 # litri al secondo

GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_ONE_PIN, GPIO.OUT)
pi = pigpio.pi()

# add possibility to disable insect detection
load_dotenv()

camera = Camera()
engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
conf_repository = ConfigurationRepository(session)
pot_repository = PlantPotRepository(session)
pot_service = PlantPotService(pot_repository)
photo_repository = PlantPhotoRepository(session)
photo_service = PlantPhotoService(photo_repository, camera)
measurement_repository  = MeasurementRepository(session)

r = redis.Redis(host="localhost", port=6379, db=0)

def watering(pot, pump_pin, humidity_channel):
    humidity = Utilities.map_humidity(MCP3008(humidity_channel).value)
    print(f"Pot number {pot.id} has humidity {humidity}%")
    if (pot.configuration.watering_mode and humidity < pot.configuration.threshold):
        GPIO.output(pump_pin, GPIO.LOW) # accendi pompa
        irrigation_time = 0.15 * pot.configuration.size / FLOW_RATE
        time.sleep(irrigation_time)
        GPIO.output(pump_pin, GPIO.HIGH)


# before start the program
# sudo pigpiod for the servo, redis-server for redis communication
# install camera libraries
# other things  TODO
def main():
    try:
        if not pi.connected:
            print("Errore: pigpiod non è attivo. Avvialo con 'sudo pigpiod'")
            return
    
    
        start = time.time()
        while True:
            pot_one = PlantPot.from_orm(pot_repository.get_by_id(1))
            pot_two = PlantPot.from_orm(pot_repository.get_by_id(2))
            pot_three = PlantPot.from_orm(pot_repository.get_by_id(3))


            ############################ CALIBRATION ############################
            value = r.lpop("bot_to_rasp")
            if value is not None and int(value) == 1:
                try:
                    pot_service.calibrate(camera, pi, SERVO_PIN, conf_repository)
                    r.rpush("rasp_to_bot", 2)
                except Exception:
                    r.rpush("rasp_to_bot", 3)

            ########################## IRRIGATION ###################################
            water_level = int(MCP3008(3).value * 100)
            if water_level > 20:
                watering(pot_one, PUMP_ONE_PIN, 0)
                watering(pot_two, PUMP_TWO_PIN, 1)
                watering(pot_three, PUMP_THREE_PIN, 2)
            elif time.time() - start > 3600: # Limit to one notification at hour
                start = time.time()
                r.rpush("rasp_to_bot", 1)
            
            ################### TIMELAPSE ###################################################
            insect_freq = 60 / pot_one.configuration.insect_freq
            t_freq_one = pot_one.configuration.shot_freq
            t_freq_two = pot_two.configuration.shot_freq
            t_freq_three = pot_three.configuration.shot_freq
            last_day = None

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
                pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(pot_one.configuration.position))
                photo_service.timelapse_shot(1, datetime.now())
                time.sleep(2)

            if now in hours_two:
                hours_two.pop(0)
                pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(pot_two.configuration.position))
                photo_service.timelapse_shot(1, datetime.now())
                time.sleep(2)

            if now in hours_three:
                hours_three.pop(0)
                pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(pot_three.configuration.position))
                photo_service.timelapse_shot(1, datetime.now())
                time.sleep(2)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Interrotto dall'utente.")
    finally:
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()
        session.close()
        print("Pulizia completata.")

    

if __name__ == "__main__":
    main()

# per ora, la frequenza di scatto insetto è uguale per tutti i vasi (prende la freq del vaso con id 1)












    '''
    last_day = None
    
    try:
        while True:
            pot_one = PlantPot.from_orm(repo.get_by_id(1))
            pot_two = PlantPot.from_orm(repo.get_by_id(2))
            pot_three = PlantPot.from_orm(repo.get_by_id(3))
            

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
    '''