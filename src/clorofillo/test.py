import sys
sys.path.append('/usr/lib/python3/dist-packages')
import cv2
import sys
import RPi.GPIO as GPIO
import time
from clorofillo.business.utilities import Utilities
from picamzero import Camera
import pigpio
from gpiozero import PWMLED, MCP3008
from time import sleep

GPIO.setmode(GPIO.BCM)
SERVO_PIN = 17
pi = pigpio.pi()


def main():
    # take photos
    if not pi.connected:
        print("Errore: pigpiod non è attivo. Avvialo con 'sudo pigpiod'")
        return
    cam = Camera()

    for i in range(0, 180):

        pi.set_servo_pulsewidth(SERVO_PIN, Utilities.angle_to_pulsewidth(i))
        cam.take_photo(f"data/calibration/{i}_.jpg")

    pi.stop()

    # detection
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    for i in range(90, 140):
        image_path = f"data/calibration/{i}_.jpg"
        image = cv2.imread(image_path)

        corners, ids, _ = detector.detectMarkers(image)
        if ids is not None:
            for marker_corners, marker_id in zip(corners, ids.flatten()):
                marker_corners = marker_corners.reshape((4, 2))
                top_left, top_right, bottom_right, bottom_left = marker_corners
                cX = int((top_left[0] + bottom_right[0]) / 2.0)
                image_center_x = image.shape[1] // 2
                tolerance = image.shape[1] * 0.01 
                is_centered = abs(cX - image_center_x) <= tolerance
                if is_centered:
                    print(f"ID rilevato: {marker_id}, angolo: {i}")
                    break

if __name__ == "__main__":
    main()
