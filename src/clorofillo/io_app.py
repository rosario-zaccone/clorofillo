#!/usr/bin/env python3
import sys
sys.path.append('/usr/lib/python3/dist-packages')

import os
import time
import redis
import threading
import signal
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

# -----------------------------
# GPIO and hardware setup
# -----------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

SERVO_PIN = 17
PUMP_ONE_PIN = 4
PUMP_TWO_PIN = 23
PUMP_THREE_PIN = 24
FLOW_RATE = 0.05  # liters per second

GPIO.setup(PUMP_ONE_PIN, GPIO.OUT)
GPIO.setup(PUMP_TWO_PIN, GPIO.OUT)
GPIO.setup(PUMP_THREE_PIN, GPIO.OUT)
pi = pigpio.pi()

# Load environment variables
load_dotenv()

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

# -----------------------------
# Watering logic
# -----------------------------
def watering(pot, pump_pin, humidity_channel):
    humidity = Utilities.map_humidity(MCP3008(humidity_channel).value)
    print(f"Pot number {pot.id} has humidity {humidity}%")
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
            except Exception as e:
                print("Error reading water level MCP3008:", e)
                water_level = 0

            if False:  # if water_level > 20:
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

# -----------------------------
# Photo and insect detection logic
# -----------------------------
def photo_worker(stop_event):
    session = SessionLocal()
    conf_repository = ConfigurationRepository(session)
    pot_repository = PlantPotRepository(session)
    pot_service = PlantPotService(pot_repository)
    photo_repository = PlantPhotoRepository(session)
    photo_service = PlantPhotoService(photo_repository, camera)

    last_day = None

    try:
        while not stop_event.is_set():
            pots = get_pots(pot_repository)
            try:
                value = r.lpop("bot_to_rasp")
                if value is not None and int(value) == 1:
                    try:
                        pot_service.calibrate(camera, pi, SERVO_PIN, conf_repository)
                        r.rpush("rasp_to_bot", 2)
                    except Exception:
                        r.rpush("rasp_to_bot", 3)
            except Exception as e:
                print("Error reading Redis for calibration:", e)

            # TIMELAPSE
            dt = datetime.now()
            now_hour = dt.hour
            current_day = dt.day
            hours = []
            if current_day != last_day:
                last_day = current_day
                for i in range(len(pots)):
                    shot_hours = Utilities.shot_hours(pots[i].configuration.shot_freq) or []
                    hours.append(shot_hours)
            try:
                for i in range(len(pots)):
                    if i >= len(hours) or not hours[i]:
                        continue
                    if now_hour in hours[i]:
                        hours[i].pop(0)
                        pi.set_servo_pulsewidth(
                            SERVO_PIN,
                            Utilities.angle_to_pulsewidth(pots[i].configuration.position)
                        )
                        photo_service.timelapse_shot(i + 1, datetime.now())
                        time.sleep(2)
            except Exception as e:
                print("Error during timelapse:", e)

            # INSECT detection
            try:
                freqs = [pots[i].configuration.insect_freq for i in range(len(pots))]
                angles = [pots[i].configuration.position for i in range(len(pots))]

                if all(f == 0 for f in freqs):
                    photo_service.clean_insect_detect()
                else:
                    max_freq = max(f for f in freqs if f != 0)
                    interval = 60 / max_freq

                    for i in range(len(pots)):
                        if freqs[i] != 0:
                            pi.set_servo_pulsewidth(
                                SERVO_PIN,
                                Utilities.angle_to_pulsewidth(angles[i])
                            )
                            photo_service.insect_shot(i + 1, datetime.now())
                            time.sleep(interval)
            except Exception as e:
                print("Error during insect detection:", e)
                time.sleep(1)

    except Exception as e:
        print("Unhandled exception in photo_worker:", e)
    finally:
        session.close()

# -----------------------------
# Main program
# -----------------------------
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
