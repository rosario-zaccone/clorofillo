#!/usr/bin/env python3
import sys
sys.path.append('/usr/lib/python3/dist-packages')

import os
import time
import redis
import threading
import signal
from datetime import datetime, time as dt_time
from dotenv import load_dotenv

import RPi.GPIO as GPIO
import pigpio
from gpiozero import  MCP3008
from picamzero import Camera

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from clorofillo.model.plant_pot import PlantPot
from clorofillo.service.utilities import Utilities
from clorofillo.service.plant_pot_service import PlantPotService
from clorofillo.service.plant_photo_service import PlantPhotoService

# Load environment variables
load_dotenv()
SERVO_PIN = int(os.getenv("SERVO_PIN", 17))
PUMP_ONE_PIN = int(os.getenv("PUMP_ONE_PIN", 4))
PUMP_TWO_PIN = int(os.getenv("PUMP_TWO_PIN", 23))
PUMP_THREE_PIN = int(os.getenv("PUMP_THREE_PIN", 24))
FLOW_RATE = float(os.getenv("FLOW_RATE", 0.05)) # liters per second

# GPIO and hardware setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(PUMP_ONE_PIN, GPIO.OUT)
GPIO.setup(PUMP_TWO_PIN, GPIO.OUT)
GPIO.setup(PUMP_THREE_PIN, GPIO.OUT)
pi = pigpio.pi()


# Camera and database setup
camera = Camera()
engine = create_engine('sqlite:///data/db.sqlite', echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)

# Redis
r = redis.Redis(host="localhost", port=6379, db=0)

# Event for threads
stop_event = threading.Event()

def get_pots(pot_repository):
    pots = []
    for i in range(1, 4):
        pot = pot_repository.get_by_id(i)
        if pot:
            pots.append(PlantPot.from_orm(pot))
    return pots

# Watering logic
def watering(pot, pump_pin, humidity_channel):
    humidity = Utilities.map_humidity(MCP3008(humidity_channel).value)
    if pot.configuration.watering_mode and humidity < pot.configuration.threshold:
        print(f"Watering pot {pot.id}")
        GPIO.output(PUMP_ONE_PIN, GPIO.HIGH)
        GPIO.output(PUMP_TWO_PIN, GPIO.HIGH)
        GPIO.output(PUMP_THREE_PIN, GPIO.HIGH)
        GPIO.output(pump_pin, GPIO.LOW)
        irrigation_time = 0.15 * pot.configuration.size / FLOW_RATE
        print(f"Irrigation time for pot {pot.id}: {irrigation_time}s")
        time.sleep(irrigation_time)
        GPIO.output(pump_pin, GPIO.HIGH)
        time.sleep(5)

def watering_worker(stop_event):
    session = SessionLocal()
    pot_repository = PlantPotRepository(session)

    last_notification = 0
    notification_interval = 3600  # one notification per hour
    try:
        while not stop_event.is_set():
            pots = get_pots(pot_repository)

            try:
                water_level = int(MCP3008(3).value * 100)
                print("water level", water_level)
            except Exception as e:
                print("Error reading water level MCP3008:", e)
                water_level = 0

            if water_level > 20:
                try:
                    watering(pots[0], PUMP_ONE_PIN, 0)
                    watering(pots[1], PUMP_TWO_PIN, 1)
                    watering(pots[2], PUMP_THREE_PIN, 2)
                except Exception as e:
                    print("Error during watering:", e)
            else:
                now = time.time()
                if now - last_notification > notification_interval:
                    last_notification = now
                    try:
                        r.rpush("rasp_to_bot", 1)
                    except Exception as e:
                        print("Error pushing Redis notification:", e)

            for _ in range(10):
                if stop_event.is_set():
                    break
                time.sleep(1)

    except Exception as e:
        print("Unhandled exception in watering_worker:", e)
    finally:
        try:
            GPIO.output(PUMP_ONE_PIN, GPIO.HIGH)
            GPIO.output(PUMP_TWO_PIN, GPIO.HIGH)
            GPIO.output(PUMP_THREE_PIN, GPIO.HIGH)
            print("Watering worker: pumps set to HIGH (cleanup).")
        except Exception as e:
            print("Error during pump cleanup in watering_worker:", e)
        session.close()

# Photo and sighting detection logic
def photo_worker(stop_event):
    session = SessionLocal()
    conf_repository = ConfigurationRepository(session)
    pot_repository = PlantPotRepository(session)
    pot_service = PlantPotService(pot_repository)
    photo_repository = PlantPhotoRepository(session)
    photo_service = PlantPhotoService(photo_repository, camera)

    shot = False

    try:
        while not stop_event.is_set():
            pots = get_pots(pot_repository)
            try:
                value = r.lpop("bot_to_rasp")
                if value is not None and int(value) == 1:
                    try:
                        pot_service.calibrate(camera, pi, SERVO_PIN, conf_repository)
                        r.rpush("rasp_to_bot", "2")  # calibrazione OK
                    except Exception as e:
                        r.rpush("rasp_to_bot", f"3|{str(e)}")

            except Exception as e:
                print("Error reading Redis for calibration:", e)

            # TIMELAPSE
            dt = datetime.now()
            t = dt_time(hour=dt.hour, minute=dt.minute)
            times = []
            for i in range(len(pots)):
                times.append(pots[i].configuration.shot_freq)
            try:
                for i in range(len(pots)):
                    if not times[i]:
                        continue
                    if t in times[i]:
                        shot = True
                        pi.set_servo_pulsewidth(
                            SERVO_PIN,
                            Utilities.angle_to_pulsewidth(pots[i].configuration.position)
                        )
                        photo_service.timelapse_shot(i + 1, datetime.now())
                        time.sleep(1)
                if (shot):
                    time.sleep(60)
                    shot = False;
            except Exception as e:
                print("Error during timelapse:", e)

            # INSECT detection
            try:
                freqs = [pots[i].configuration.sighting_freq for i in range(len(pots))]
                angles = [pots[i].configuration.position for i in range(len(pots))]

                for i in range(len(pots)):
                    if freqs[i] == 0:
                        photo_service.clean_sighting_detect(i+1)
                    
                
                if any(f != 0 for f in freqs):
                    max_freq = max(f for f in freqs if f != 0)
                    interval = 60 / max_freq

                    for i in range(len(pots)):
                        if freqs[i] != 0:
                            pi.set_servo_pulsewidth(
                                SERVO_PIN,
                                Utilities.angle_to_pulsewidth(angles[i])
                            )
                            photo_service.sighting_shot(i + 1, datetime.now())
                            time.sleep(interval)
            except Exception as e:
                print("Error during sighting detection:", e)
                time.sleep(1)

    except Exception as e:
        print("Unhandled exception in photo_worker:", e)
    finally:
        session.close()


def main():
    try:
        GPIO.output(PUMP_ONE_PIN, GPIO.HIGH)
        GPIO.output(PUMP_TWO_PIN, GPIO.HIGH)
        GPIO.output(PUMP_THREE_PIN, GPIO.HIGH)
    except Exception as e:
        print("Error setting initial pump state:", e)

    if not pi.connected:
        print("Error: pigpiod is not running. Start it with 'sudo pigpiod'")
        return

    def _signal_handler(signum, frame):
        print(f"Received signal {signum}, initiating shutdown...")
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    t_watering = threading.Thread(target=watering_worker, args=(stop_event,), name="watering-thread")
    t_photo = threading.Thread(target=photo_worker, args=(stop_event,), name="photo-thread")

    t_watering.start()
    t_photo.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        stop_event.set()
        t_watering.join(timeout=15)
        t_photo.join(timeout=15)

        try:
            pi.set_servo_pulsewidth(SERVO_PIN, 0)
        except Exception:
            pass

        try:
            pi.stop()
        except Exception:
            pass

        print("Final cleanup completed.")


if __name__ == "__main__":
    main()
