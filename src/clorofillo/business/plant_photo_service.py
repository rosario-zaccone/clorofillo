import cv2
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
        before_img = "data/photos/maybe_insect/before_" + pot_id + ".jpeg"
        after_img = "data/photos/maybe_insect/after_" + pot_id + ".jpeg"
        self._camera.take_photo(after_img)
        if os.path.isfile(before_img):
            patches_b64 = detector._detect_insect_patches_base64(before_img, after_img)
            if patches_b64:
                i = 0
                for patch in patches_b64:
                    # ora la salva sempre, in futuro modifica in modo che la salvi solo se l'API individua un insetto
                    img_data = base64.b64decode(patch)
                    output_path = "data/photos/insect/" + pot_id + "_" + readable + "_" + i
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                        photo = PlantPhoto(timestamp, True, output_path)
                        self._repository.insert(photo.to_orm(pot_id))
                    i = i + 1
            os.remove(before_img)
        os.rename(after_img, before_img)
    
    def timelapse_shot(self, pot_id, timestamp): 
        readable = str(timestamp).replace(" ", "_")
        path = "data/photos/timelapse/" + str(pot_id) + "_" + readable + ".jpg"
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