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
        self.camera = camera
        self._API_URL = api_url or "https://insect.kindwise.com/api/v1/identification"
        self._API_KEY = api_key or os.getenv("API_KEY")

    @property
    def repository(self):
        return self._repository

    def _detect_insect_patches_base64(self, before_path, after_path, save_patches=True):
        PATCH_MIN_WIDTH = int(os.getenv("PATCH_MIN_WIDTH", 20))
        PATCH_MIN_HEIGHT = int(os.getenv("PATCH_MIN_HEIGHT", 20))
        PATCH_MAX_WIDTH = int(os.getenv("PATCH_MAX_WIDTH", 300))
        PATCH_MAX_HEIGHT = int(os.getenv("PATCH_MAX_HEIGHT", 300))
        COLOR_DIFF_THRESH = int(os.getenv("COLOR_DIFF_THRESH", 30))

        if not os.path.exists(before_path) or not os.path.exists(after_path):
            return []

        before = cv2.imread(before_path)
        after = cv2.imread(after_path)

        if before is None or after is None:
            return []

        if before.shape != after.shape:
            return []

        diff = cv2.absdiff(before, after)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(diff_gray, COLOR_DIFF_THRESH, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.dilate(cleaned, kernel, iterations=2)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if save_patches:
            os.makedirs("data/photos/test/patch", exist_ok=True)

        patches_b64 = []
        i = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if not (PATCH_MIN_WIDTH <= w <= PATCH_MAX_WIDTH and PATCH_MIN_HEIGHT <= h <= PATCH_MAX_HEIGHT):
                continue

            patch_before = before[y:y+h, x:x+w]
            patch_after = after[y:y+h, x:x+w]

            if cv2.cvtColor(patch_after, cv2.COLOR_BGR2GRAY).std() < 10:
                continue

            _, buf_after = cv2.imencode('.jpg', patch_after)
            b64_after = base64.b64encode(buf_after).decode('utf-8')
            patches_b64.append(b64_after)

            if save_patches:
                path_base = f"data/photos/test/patch/patch_{i}"
                cv2.imwrite(f"{path_base}_before.jpg", patch_before)
                cv2.imwrite(f"{path_base}_after.jpg", patch_after)
                i += 1

        return patches_b64



    def _call_kindwise_api_with_files(self, patches_base64):
        # ritorna il nome dell'insetto se il primo match è buono, altirmenti None
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
        self.camera.take_photo(after_img)
        if os.path.isfile(before_img):
            patches_b64 = self._detect_insect_patches_base64(before_img, after_img, True)
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
                    self._repository.session.commit()
            os.remove(before_img)
        os.rename(after_img, before_img)
    
    def timelapse_shot(self, pot_id, timestamp): 
        readable = str(timestamp).replace(" ", "_")
        path = f"data/photos/timelapse/{pot_id}_{readable}.jpg"
        self.camera.take_photo(path)
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