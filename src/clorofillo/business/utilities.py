import cv2
import numpy as np
import os
import requests
import base64
from dotenv import load_dotenv
import matplotlib.pyplot as plt

class Utilities:
    @staticmethod
    def classical_superres(img, scale=3):
        height, width = img.shape[:2]
        new_size = (width * scale, height * scale)
        return cv2.resize(img, new_size, interpolation=cv2.INTER_LANCZOS4)

    @staticmethod
    def img_to_base64(img, ext=".png"):
        _, buffer = cv2.imencode(ext, img)
        img_bytes = buffer.tobytes()
        base64_str = base64.b64encode(img_bytes).decode("utf-8")
        return base64_str

    @staticmethod
    def angle_to_pulsewidth(angle):
        return 500 + (angle / 180.0) * 2000 
    
    
    @staticmethod
    def show_base64_images(base64_images):
        for i, b64_str in enumerate(base64_images):
            img_data = base64.b64decode(b64_str)
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            plt.figure()
            plt.imshow(img_rgb)
            plt.title(f"Patch {i+1} super-resolved")
            plt.axis("off")
        plt.show()

    @staticmethod
    def shot_hours(shot_freq):
        unit = 24 / shot_freq
        hours = [0]
        while len(hours) < shot_freq:
            hours.append(hours[-1] + unit)
        return hours
    
    #0.29 max humidiy, 0.82 min umidity
    @staticmethod
    def map_humidity(value):
        value = max(min(value, 0.82), 0.29)
        mapped = (value - 0.29) * (0 - 100) / (0.82 - 0.29) + 100
        return mapped

        
        

    