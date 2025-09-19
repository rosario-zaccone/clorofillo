import cv2
from PIL import Image
import io
import numpy as np
import os, shutil
import requests
import base64
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from time import time
from clorofillo.business.utilities import Utilities
from clorofillo.model.plant_photo import PlantPhoto


class PlantPhotoService:
    def __init__(self, repository, camera, api_key=None, api_url=None):
        load_dotenv()
        self._repository = repository
        self._camera = camera
        self._API_URL = api_url or "https://insect.kindwise.com/api/v1/identification"
        self._API_KEY = api_key or os.getenv("API_KEY")

    @property
    def repository(self):
        return self._repository

    def _detect_insect_patches_base64(self, img1_path, img2_path):
        """
        Compare two images and return a list of base64-encoded PNGs for patches in img2
        that are not present in img1 (potentially insects).

        Args:
            img1_path (str): Path to the first image (background/reference image).
            img2_path (str): Path to the second image (image with possible insects).

        Returns:
            List[str]: List of base64-encoded PNG images (as strings) of detected patches.
        """
        # Load images
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        if img1 is None or img2 is None:
            raise ValueError("One or both image paths are invalid.")

        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Compute absolute difference
        diff = cv2.absdiff(gray2, gray1)

        # Threshold the difference
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        # Morphological operations to remove noise and fill holes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # Find contours (connected components)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        patch_b64_list = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 100:  # Filter out very small regions (tune as needed)
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            patch = img2[y:y+h, x:x+w]
            # Convert to PIL Image for base64 encoding
            patch_pil = Image.fromarray(cv2.cvtColor(patch, cv2.COLOR_BGR2RGB))
            buffered = io.BytesIO()
            patch_pil.save(buffered, format="PNG")
            patch_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            patch_b64_list.append(patch_b64)

        return patch_b64_list


    def _call_kindwise_api_with_files(self, patches_base64):
        response = requests.post(
            self._API_URL,
            params={"details": "url,common_names"},
            headers={"Api-Key": self._API_KEY},
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

    def insect_shot(self, pot_id, timestamp): #timestamp deve essere YY-MM-DD-H-M-S
            # scatta foto after e comparale con before (solo se esiste before)
            # testa i sospetti con api insetti
            # se sono insetti spostali nella cartella insect e mettili nel db
            # rimuovi l avecchia before, fai diventare after la nuova before
        
        # nome file insetto: id_timestamp_eventuale numero se ci sono piu patch per itmestamp
        readable = str(timestamp).replace(" ", "_")
        before_img = f"data/photos/maybe_insect/before_{pot_id}.jpg"
        after_img = f"data/photos/maybe_insect/after_{pot_id}.jpg"
        self._camera.take_photo(after_img)
        if os.path.isfile(before_img):
            patches_b64 = self._detect_insect_patches_base64(before_img, after_img)
            if patches_b64:
                i = 0
                for patch in patches_b64:
                    # ora la salva sempre, in futuro modifica in modo che la salvi solo se l'API individua un insetto
                    img_data = base64.b64decode(patch)
                    output_path = f"data/photos/insect/{pot_id}_{readable}_{i}.jpg"
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                        photo = PlantPhoto(timestamp, True, output_path)
                        self._repository.insert(photo.to_orm(pot_id))
                    i = i + 1
            os.remove(before_img)
        os.rename(after_img, before_img)
    
    def timelapse_shot(self, pot_id, timestamp): 
        readable = str(timestamp).replace(" ", "_")
        path = f"data/photos/timelapse/{pot_id}_{readable}.jpg"
        self._camera.take_photo(path)
        photo = PlantPhoto(timestamp, False, path)
        self._repository.insert(photo.to_orm(pot_id))
        self._repository.session.commit()


if __name__ == "__main__":
    before_img = "data/photos/maybe_insect/before.png"
    after_img = "data/photos/maybe_insect/after.png"


    detector = PlantPhotoService(None)

    '''
    print("📸 Detecting and super-resolving potential insect patches...")
    patches_b64 = detector.detect_insect_patches_base64(before_img, after_img)

    print(f"Found {len(patches_b64)} patches.")
    Utilities.show_base64_images(patches_b64)

    
    if patches_b64:
        insect_name = detector.call_kindwise_api_with_files([patches_b64[0]])
        print("Identified insect:", insect_name)
    else:
        print("No patches detected.")
    '''