import sys
sys.path.append('/usr/lib/python3/dist-packages')

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
PUMP_ONE_PIN = 4
GPIO.setup(PUMP_ONE_PIN, GPIO.OUT)

GPIO.output(PUMP_ONE_PIN, GPIO.LOW) # accendi pompa
time.sleep(10)
GPIO.output(PUMP_ONE_PIN, GPIO.HIGH)

GPIO.cleanup()