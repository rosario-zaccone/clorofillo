import cv2
import numpy as np
import os
import requests
import base64
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from clorofillo.business.utilities import Utilities

class PlantPhotoService:
    def __init__(self, repository, api_key=None, api_url=None):
        load_dotenv()
        self.__repository = repository
        self.__API_URL = api_url or "https://insect.kindwise.com/api/v1/identification"
        self.__API_KEY = api_key or os.getenv("API_KEY")

    def detect_insect_patches_base64(self, img1_path, img2_path):
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)

        if img1 is None or img2 is None:
            raise ValueError("Invalid image path.")

        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=2)
        thresh = cv2.erode(thresh, kernel, iterations=1)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        patches_base64 = []

        for cnt in contours:
            if Utilities.is_insect_shape(cnt):
                x, y, w, h = cv2.boundingRect(cnt)
                patch = img2[y : y + h, x : x + w]
                patch_superres = Utilities.classical_superres(patch, scale=3)
                patch_b64 = Utilities.img_to_base64(patch_superres)
                patches_base64.append(patch_b64)

        return patches_base64

    def call_kindwise_api_with_files(self, patches_base64):
        response = requests.post(
            self.API_URL,
            params={"details": "url,common_names"},
            headers={"Api-Key": self.API_KEY},
            json={"images": patches_base64},
        )

        if response.status_code == 201:
            insect_name = None
            ok_response = response.json()
            suggestions = ok_response["result"]["classification"]["suggestions"]
            if suggestions and suggestions[0]["probability"] > 0.7:
                insect_name = suggestions[0]["name"]
            return insect_name
        else:
            raise Exception(
                f"Errore API: status code {response.status_code}, response: {response.text}"
            )


if __name__ == "__main__":
    before_img = "data/photos/maybe_insect/before.png"
    after_img = "data/photos/maybe_insect/pippo.png"

    detector = PlantPhotoService()

    print("📸 Detecting and super-resolving potential insect patches...")
    patches_b64 = detector.detect_insect_patches_base64(before_img, after_img)

    print(f"Found {len(patches_b64)} patches.")

    '''
    if patches_b64:
        insect_name = detector.call_kindwise_api_with_files([patches_b64[0]])
        print("Identified insect:", insect_name)
    else:
        print("No patches detected.")
        '''
