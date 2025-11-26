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
measurement_repository = MeasurementRepository(session)

r = redis.Redis(host="localhost", port=6379, db=0)

# Event to request clean shutdown of worker threads
stop_event = threading.Event()
# Lock to guard access to the servo (pi.set_servo_pulsewidth)
servo_lock = threading.Lock()


def watering(pot, pump_pin, humidity_channel):
    """
    Single-pot watering routine. Uses MCP3008(humidity_channel).value to compute humidity.
    """
    humidity = Utilities.map_humidity(MCP3008(humidity_channel).value)
    print(f"Pot number {pot.id} has humidity {humidity}%")
    if pot.configuration.watering_mode and humidity < pot.configuration.threshold:
        print(f"Watering pot {pot.id}")
        # set all pumps to HIGH, then enable the requested pump (LOW)
        GPIO.output(PUMP_ONE_PIN, GPIO.HIGH)
        GPIO.output(PUMP_TWO_PIN, GPIO.HIGH)
        GPIO.output(PUMP_THREE_PIN, GPIO.HIGH)
        GPIO.output(pump_pin, GPIO.LOW)
        irrigation_time = 0.15 * pot.configuration.size / FLOW_RATE
        print(f"Irrigation time for pot {pot.id}: {irrigation_time}s")
        time.sleep(irrigation_time)
        GPIO.output(pump_pin, GPIO.HIGH)
        time.sleep(5)  # small pause after irrigation to let soil absorb water


def watering_worker(stop_event):
    """
    Loop that handles irrigation checks and watering.
    The pump cleanup (set pumps to HIGH) is in the finally block so pumps are left in a safe state.
    """
    last_notification = 0
    notification_interval = 3600  # one notification per hour
    try:
        while not stop_event.is_set():
            try:
                pot_one = PlantPot.from_orm(pot_repository.get_by_id(1))
                pot_two = PlantPot.from_orm(pot_repository.get_by_id(2))
                pot_three = PlantPot.from_orm(pot_repository.get_by_id(3))
            except Exception as e:
                print("Error fetching pots in watering_worker:", e)
                # wait a bit then retry
                for _ in range(5):
                    if stop_event.is_set():
                        break
                    time.sleep(1)
                continue

            try:
                water_level = int(MCP3008(3).value * 100)
            except Exception as e:
                print("Error reading water level MCP3008:", e)
                water_level = 0

            # If you'd like to re-enable the water-level gating, restore the condition below.
            if False: #if water_level > 20: 
                try:
                    watering(pot_one, PUMP_ONE_PIN, 0)
                    watering(pot_two, PUMP_TWO_PIN, 1)
                    watering(pot_three, PUMP_THREE_PIN, 2)
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

            # Sleep in small increments so worker can react quickly to shutdown
            for _ in range(10):
                if stop_event.is_set():
                    break
                time.sleep(1)
    except Exception as e:
        print("Unhandled exception in watering_worker:", e)
    finally:
        # Pump cleanup: ensure pumps are left in the safe state (HIGH)
        try:
            GPIO.output(PUMP_ONE_PIN, GPIO.HIGH)
            GPIO.output(PUMP_TWO_PIN, GPIO.HIGH)
            GPIO.output(PUMP_THREE_PIN, GPIO.HIGH)
            print("Watering worker: pumps set to HIGH (cleanup).")
        except Exception as e:
            print("Error during pump cleanup in watering_worker:", e)


def photo_worker(stop_event):
    """
    Loop that handles timelapse, insect detection, and calibration.
    """

    last_day = None
    hours_one = []
    hours_two = []
    hours_three = []

    try:
        while not stop_event.is_set():
            # Calibration command via Redis
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

            # Refresh pots
            try:
                pot_one = PlantPot.from_orm(pot_repository.get_by_id(1))
                pot_two = PlantPot.from_orm(pot_repository.get_by_id(2))
                pot_three = PlantPot.from_orm(pot_repository.get_by_id(3))
            except Exception as e:
                print("Error fetching pots (photo_worker):", e)
                for _ in range(3):
                    if stop_event.is_set():
                        break
                    time.sleep(1)
                continue

            # TIMELAPSE logic
            t_freq_one = pot_one.configuration.shot_freq
            t_freq_two = pot_two.configuration.shot_freq
            t_freq_three = pot_three.configuration.shot_freq

            dt = datetime.now()
            now_hour = dt.hour
            current_day = dt.day

            if current_day != last_day:
                last_day = current_day
                hours_one = Utilities.shot_hours(t_freq_one)
                hours_two = Utilities.shot_hours(t_freq_two)
                hours_three = Utilities.shot_hours(t_freq_three)

            try:
                if now_hour in hours_one:
                    hours_one.pop(0)
                    with servo_lock:
                        pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(pot_one.configuration.position))
                    photo_service.timelapse_shot(1, datetime.now())
                    time.sleep(2)

                if now_hour in hours_two:
                    hours_two.pop(0)
                    with servo_lock:
                        pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(pot_two.configuration.position))
                    photo_service.timelapse_shot(2, datetime.now())
                    time.sleep(2)

                if now_hour in hours_three:
                    hours_three.pop(0)
                    with servo_lock:
                        pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(pot_three.configuration.position))
                    photo_service.timelapse_shot(3, datetime.now())
                    time.sleep(2)
            except Exception as e:
                print("Error during timelapse:", e)

            # INSECT detection (sensitive to fast light changes and wind)
            try:
                if pot_one.configuration.insect_freq != 0:
                    insect_freq = 60 / pot_one.configuration.insect_freq
                    with servo_lock:
                        pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(0))
                    # photo_service.insect_shot(1, datetime.now())  # optional
                    time.sleep(insect_freq)

                    with servo_lock:
                        pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(90))
                    photo_service.insect_shot(2, datetime.now())
                    time.sleep(insect_freq)

                    #with servo_lock:
                    #    pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(180))
                    # photo_service.insect_shot(3, datetime.now())
                    #time.sleep(insect_freq)
                else:
                    photo_service.clean_insect_detect()
            except Exception as e:
                print("Error during insect detection:", e)
            # Small pause to avoid tight loop
            for _ in range(5):
                if stop_event.is_set():
                    break
                time.sleep(1)

    except Exception as e:
        print("Unhandled exception in photo_worker:", e)


def main():
    # Set pumps to HIGH initially (safe state)
    try:
        GPIO.output(PUMP_ONE_PIN, GPIO.HIGH)
        GPIO.output(PUMP_TWO_PIN, GPIO.HIGH)
        GPIO.output(PUMP_THREE_PIN, GPIO.HIGH)
    except Exception as e:
        print("Error setting initial pump state:", e)

    if not pi.connected:
        print("Error: pigpiod is not running. Start it with 'sudo pigpiod'")
        return

    # Signal handler to request shutdown
    def _signal_handler(signum, frame):
        print(f"Received signal {signum}, initiating shutdown...")
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Create and start threads
    t_watering = threading.Thread(target=watering_worker, args=(stop_event,), name="watering-thread")
    t_photo = threading.Thread(target=photo_worker, args=(stop_event,), name="photo-thread")

    t_watering.start()
    t_photo.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user (KeyboardInterrupt).")
        stop_event.set()
    finally:
        # Request threads to stop and wait for them
        stop_event.set()
        print("Waiting for threads to terminate...")
        t_watering.join(timeout=15)
        t_photo.join(timeout=15)

        # Servo cleanup and other final cleanup (pumps cleaned by watering_worker)
        try:
            with servo_lock:
                pi.set_servo_pulsewidth(SERVO_PIN, 0)
        except Exception:
            pass

        try:
            pi.stop()
        except Exception:
            pass

        try:
            session.close()
        except Exception:
            pass

        print("Final cleanup completed.")


if __name__ == "__main__":
    main()