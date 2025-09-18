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
    def angle_to_percent (angle) :
        if angle > 180 or angle < 0 :
            return False
        start = 4
        end = 12.5
        ratio = (end - start)/180

        angle_as_percent = angle * ratio

        return start + angle_as_percent
    
    @staticmethod
    def is_insect_shape(contour, min_area=30, max_area=500, min_circularity=0.4):
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            return False
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return False
        circularity = 4 * np.pi * (area / (perimeter * perimeter))
        if circularity < min_circularity or circularity > 1.2:
            return False
        return True
    
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

    