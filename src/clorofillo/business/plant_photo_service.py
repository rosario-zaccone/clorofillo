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
import os
import cv2
import numpy as np
import base64
from concurrent.futures import ThreadPoolExecutor
from skimage.metrics import structural_similarity as ssim


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


    def _detect_insect_patches_base64(
        self, 
        before_path, 
        after_path, 
        save_patches=True, 
        min_area=500,
        max_area=6000,
        max_width=100,
        max_height=100
    ):
        """
        Confronta due immagini e individua le patch dove ci sono cambiamenti (possibili insetti).
        Restituisce un array di stringhe base64 delle patch "after".
        Salva le patch se save_patches=True.
        Utilizza allineamento ORB per ridurre falsi positivi.
        """
        # Leggi le immagini
        before = cv2.imread(before_path)
        after = cv2.imread(after_path)
        if before is None or after is None:
            raise ValueError("Errore nel caricamento delle immagini")
        
        # Converti in scala di grigi
        before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
        after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
        
        # --- Allineamento tramite ORB ---
        orb = cv2.ORB_create(500)
        kp1, des1 = orb.detectAndCompute(before_gray, None)
        kp2, des2 = orb.detectAndCompute(after_gray, None)
        
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        
        if len(matches) >= 4:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
            M, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts)
            before_aligned = cv2.warpAffine(before, M, (after.shape[1], after.shape[0]))
        else:
            before_aligned = before.copy()
        
        before_gray = cv2.cvtColor(before_aligned, cv2.COLOR_BGR2GRAY)
        
        # --- Differenza immagini ---
        diff = cv2.absdiff(after_gray, before_gray)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Operazioni morfologiche
        kernel = np.ones((3,3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        thresh = cv2.dilate(thresh, kernel, iterations=2)
        
        # Trova contorni
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        patches_base64 = []
        patch_dir = "data/photos/test/patch"
        if save_patches and not os.path.exists(patch_dir):
            os.makedirs(patch_dir)
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            if max_area is not None and area > max_area:
                continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            
            if max_width is not None and w > max_width:
                continue
            if max_height is not None and h > max_height:
                continue
            
            # Ritaglia patch "after"
            patch_after = after[y:y+h, x:x+w]
            patch_after_pil = Image.fromarray(cv2.cvtColor(patch_after, cv2.COLOR_BGR2RGB))
            
            if save_patches:
                patch_after_pil.save(os.path.join(patch_dir, f"patch_{i}_after.png"))
            
            # Converti in base64 e aggiungi all'array
            buffered_after = io.BytesIO()
            patch_after_pil.save(buffered_after, format="PNG")
            base64_after = base64.b64encode(buffered_after.getvalue()).decode("utf-8")
            
            patches_base64.append(base64_after)
        
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
            patches_b64 = self._detect_insect_patches_base64(before_img, after_img, True)
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