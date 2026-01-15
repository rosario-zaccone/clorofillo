import cv2, redis
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
import os, re
import cv2
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor
from skimage.metrics import structural_similarity as ssim
from sklearn.cluster import KMeans

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


    def clean_insect_detect(self, pot_id):
        folder_path = 'data/photos/maybe_insect/'
        file_path = os.path.join(folder_path, "before_" + str(pot_id) + ".jpg")
        if os.path.exists(file_path):
            os.remove(file_path)

    def _detect_insect_patches_base64(
        self,
        before_path,
        after_path,
        pot_id,
        timestamp,
        min_area=500,
        max_area=6000,
        max_width=100,
        max_height=100,
        h_thr=25,           # sensibilità hue (0-179)
        s_thr=30,           # sensibilità saturazione (0-255)
        ):
        patch_dir = "data/photos/insect/patch"
        os.makedirs(patch_dir, exist_ok=True)
        patches_base64 = []

        # ID univoco:
        max_id = -1
        pattern = re.compile(r"^(\d+)_.*\.jpg$")
        for fname in os.listdir(patch_dir):
            m = pattern.match(fname)
            if m:
                idx = int(m.group(1))
                if idx > max_id:
                    max_id = idx
        i = max_id + 1

        before = cv2.imread(before_path)
        after = cv2.imread(after_path)
        if before is None or after is None:
            print("Error loading images")
            return []
        maxdim = 800
        if max(before.shape[0], before.shape[1]) > maxdim:
            scale = maxdim / max(before.shape[0], before.shape[1])
            before = cv2.resize(before, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            after  = cv2.resize(after,  None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        h_img, w_img = after.shape[:2]
        border_ignore = 16

        # Differenza colore HSV
        before_hsv = cv2.cvtColor(before, cv2.COLOR_BGR2HSV)
        after_hsv  = cv2.cvtColor(after,  cv2.COLOR_BGR2HSV)
        delta = cv2.absdiff(after_hsv, before_hsv)
        # Considera nuovi i pixel che variano abbastanza in "H" o "S"
        diff_mask = ((delta[...,0] > h_thr) | (delta[...,1] > s_thr)).astype(np.uint8) * 255

        # Morphology per pulire la maschera
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
        diff_mask = cv2.dilate(diff_mask, kernel, iterations=1)
        diff_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            if (x < border_ignore or y < border_ignore or
                x+w > w_img - border_ignore or y+h > h_img - border_ignore):
                continue
            if min_area <= area <= max_area and w <= max_width and h <= max_height:
                patch_after = after[y:y+h, x:x+w]
                patch_after_pil = Image.fromarray(cv2.cvtColor(patch_after, cv2.COLOR_BGR2RGB))
                out_path = os.path.join(patch_dir, f"{i}_{pot_id}_{timestamp}.jpg")
                patch_after_pil.save(out_path, format="JPEG")
                buffered_after = io.BytesIO()
                patch_after_pil.save(buffered_after, format="JPEG")
                base64_after = base64.b64encode(buffered_after.getvalue()).decode("utf-8")
                patches_base64.append(base64_after)
                i += 1

        return patches_base64



    def _simulate_insect_api(self, base64_input: str) -> str:
        import random
        insect_names = [
            "apis_mellifera",        # Ape europea
            "danaus_plexippus",      # Farfalla monarca
            "coccinella_septempunctata",  # Coccinella
            "anopheles_gambiae",     # Zanzara
            "gryllus_campestris",    # Grillo
            "musca_domestica",       # Mosca domestica
            "bombyx_mori",           # Baco da seta
            "tenebrio_molitor",      # Tarma della farina
            "drosophila_melanogaster", # Moscerino della frutta
            "formica_rufa"           # Formica rossa
        ]
        if random.random() < 0.7:
            return random.choice(insect_names)
        else:
            return None


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

    def insect_shot(self, pot_id, timestamp): 
        readable = str(timestamp).replace(" ", "_")
        before_img = f"data/photos/maybe_insect/before_{pot_id}.jpg"
        after_img = f"data/photos/maybe_insect/after_{pot_id}.jpg"
        self.camera.take_photo(after_img)
        if os.path.isfile(before_img):
            patches_b64 = self._detect_insect_patches_base64(before_img, after_img, pot_id, timestamp)
            if (patches_b64):
                # telegram notify redis
                r = redis.Redis(host="localhost", port=6379, db=0)
                r.rpush("rasp_to_bot", 4)
                r.close()
                '''
            if (patches_b64):
                for patch in patches_b64:
                    #api call
                    insect_name = self._simulate_insect_api(patch)
                    print(insect_name)
                    if (insect_name != None):
                        # file save
                        base_dir = "data/photos/insect"
                        os.makedirs(base_dir, exist_ok=True)
                        image_data = base64.b64decode(patch)
                        readable = str(timestamp).replace(" ", "_")
                        path = os.path.join(base_dir, f"{pot_id}_{insect_name}_{readable}.jpg")
                        if os.path.exists(path):
                            counter = 1
                            while True:
                                new_path = os.path.join(base_dir, f"{pot_id}_{insect_name}_{readable}_{counter}.jpg")
                                if not os.path.exists(new_path):
                                    path = new_path
                                    break
                                counter += 1
                        with open(path, "wb") as f:
                            f.write(image_data)
                        #db save
                        photo = PlantPhoto(timestamp, True, path)
                        self._repository.insert(photo.to_orm(pot_id))
                        self._repository.session.commit()
                        # telegram notify redis
                        r = redis.Redis(host="localhost", port=6379, db=0)
                        r.rpush("rasp_to_bot", 4)
                        r.close()
                        '''
                
                pass
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