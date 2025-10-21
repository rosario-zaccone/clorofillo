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
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository
from concurrent.futures import ThreadPoolExecutor


class PlantPhotoService:
    def __init__(self, repository: PlantPhotoRepository, camera, api_key=None, api_url=None):
        load_dotenv()
        self._repository = repository
        self.camera = camera
        self._API_URL = api_url or "https://insect.kindwise.com/api/v1/identification"
        self._API_KEY = api_key or os.getenv("API_KEY")

    @property
    def repository(self):
        return self._repository


    def clean_insect_detect(self):
        folder_path = 'data/photos/maybe_insect/'
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def _detect_insect_patches_base64(self, before_path, after_path, save_patches=True, color_thresh=30):

        min_w, min_h = 40, 40
        max_w, max_h = 300, 300
        min_area = 500  # area minima del contorno

        if not (os.path.isfile(before_path) and os.path.isfile(after_path)):
            return []

        img_before = cv2.imread(before_path)
        img_after = cv2.imread(after_path)
        if img_before is None or img_after is None or img_before.shape != img_after.shape:
            return []

        # Riduzione del rumore
        img_before = cv2.medianBlur(img_before, 3)
        img_after = cv2.medianBlur(img_after, 3)

        # Confronto in spazio LAB (più stabile)
        img_before_lab = cv2.cvtColor(img_before, cv2.COLOR_BGR2Lab)
        img_after_lab = cv2.cvtColor(img_after, cv2.COLOR_BGR2Lab)
        diff = cv2.absdiff(img_before_lab, img_after_lab)

        # Maschera delle differenze significative
        mask = np.linalg.norm(diff, axis=2) > color_thresh
        mask = mask.astype(np.uint8) * 255

        # Pulizia rumore
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)

        # Trova contorni delle aree nuove
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if save_patches:
            os.makedirs("data/photos/test/patch", exist_ok=True)

        patch_list = []
        patch_index = 0
        to_save = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)

            if not (min_w <= w <= max_w and min_h <= h <= max_h and area >= min_area):
                continue

            patch_b = img_before[y:y + h, x:x + w]
            patch_a = img_after[y:y + h, x:x + w]

            # Scarta patch troppo piatte (poco contrasto)
            gray_patch = cv2.cvtColor(patch_a, cv2.COLOR_BGR2GRAY)
            if gray_patch.std() < 10:
                continue

            # Scarta patch troppo scure o chiare
            mean_val = gray_patch.mean()
            if mean_val < 20 or mean_val > 235:
                continue

            # Codifica in base64
            success, buffer = cv2.imencode('.jpg', patch_a)
            if not success:
                continue

            b64_patch = base64.b64encode(buffer).decode('utf-8')
            patch_list.append(b64_patch)

            if save_patches:
                base_filename = f"data/photos/test/patch/patch_{patch_index}"
                to_save.append((f"{base_filename}_before.jpg", patch_b))
                to_save.append((f"{base_filename}_after.jpg", patch_a))
                patch_index += 1

        # Salvataggio immagini in parallelo
        if save_patches and to_save:
            with ThreadPoolExecutor() as executor:
                for path, img in to_save:
                    executor.submit(cv2.imwrite, path, img)

        return patch_list





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
            '''
            invia i sospetti a telegram
            if patches_b64:
                i = 0
                for patch in patches_b64:
                    # ora la salva sempre, in futuro modifica in modo che la salvi solo se l'API individua un insetto
                    img_data = base64.b64decode(patch)
                    output_path = f"data/photos/maybe_insect/{pot_id}_{readable}_{i}.jpg"  #salva i sospetti
                    i = i + 1
                # qui va la parte dove scrivi su una lista redis ch eci sono nuovi sospetti. lato telegram bot ci sarà uno scan continuo del canale per capire se ci sono sospetti, e se ci sono ci sarà l'invio del form all'utente. se l'utente conferma, viene chiamata l'api e in caso di esitopositivo salvato su db
            '''
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