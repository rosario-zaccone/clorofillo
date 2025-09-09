import cv2
import numpy as np
import os
import requests
import base64
from dotenv import load_dotenv
import matplotlib.pyplot as plt


class InsectDetector:
    def __init__(self, api_key=None, api_url=None, scale_superres=3):
        load_dotenv()
        self.API_URL = api_url or "https://insect.kindwise.com/api/v1/identification"
        self.API_KEY = api_key or os.getenv("API_KEY")
        self.scale_superres = scale_superres

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
            if self.is_insect_shape(cnt):
                x, y, w, h = cv2.boundingRect(cnt)
                patch = img2[y : y + h, x : x + w]
                patch_superres = self.classical_superres(patch, scale=self.scale_superres)
                patch_b64 = self.img_to_base64(patch_superres)
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


if __name__ == "__main__":
    before_img = "data/photos/insect/before.png"
    after_img = "data/photos/insect/pippo.png"

    detector = InsectDetector(scale_superres=3)

    print("📸 Detecting and super-resolving potential insect patches...")
    patches_b64 = detector.detect_insect_patches_base64(before_img, after_img)

    print(f"Found {len(patches_b64)} patches.")


    if patches_b64:
        insect_name = detector.call_kindwise_api_with_files([patches_b64[0]])
        print("Identified insect:", insect_name)
    else:
        print("No patches detected.")
