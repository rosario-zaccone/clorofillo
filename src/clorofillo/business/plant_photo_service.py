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

    def _detect_insect_patches_base64(self, before_path, after_path, save_patches=True):
        PATCH_MIN_WIDTH = int(os.getenv("PATCH_MIN_WIDTH", 60))
        PATCH_MIN_HEIGHT = int(os.getenv("PATCH_MIN_HEIGHT", 60))
        PATCH_MAX_WIDTH = int(os.getenv("PATCH_MAX_WIDTH", 9999))
        PATCH_MAX_HEIGHT = int(os.getenv("PATCH_MAX_HEIGHT", 9999))
        COLOR_DIFF_THRESH = int(os.getenv("COLOR_DIFF_THRESH", 35))
        BLUR_KERNEL_SIZE = int(os.getenv("BLUR_KERNEL_SIZE", 5))
        MORPH_KERNEL_SIZE = int(os.getenv("MORPH_KERNEL_SIZE", 3))
        MORPH_DILATE_ITER = int(os.getenv("MORPH_DILATE_ITER", 2))

        if not os.path.exists(before_path) or not os.path.exists(after_path):
            return []

        before = cv2.imread(before_path)
        after = cv2.imread(after_path)
        if before is None or after is None:
            return []

        orb = cv2.ORB_create(1000)
        kp1, des1 = orb.detectAndCompute(before, None)
        kp2, des2 = orb.detectAndCompute(after, None)
        if des1 is None or des2 is None:
            return []

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = sorted(bf.match(des1, des2), key=lambda x: x.distance)
        if len(matches) < 4:
            return []

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1,1,2)
        M, _ = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 4.0)
        aligned_after = cv2.warpPerspective(after, M, (before.shape[1], before.shape[0]))

        blur_ksize = (BLUR_KERNEL_SIZE, BLUR_KERNEL_SIZE)
        morph_kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), np.uint8)

        before_blur = cv2.GaussianBlur(before, blur_ksize, 0)
        after_blur = cv2.GaussianBlur(aligned_after, blur_ksize, 0)

        lab_before = cv2.cvtColor(before_blur, cv2.COLOR_BGR2LAB)
        lab_after = cv2.cvtColor(after_blur, cv2.COLOR_BGR2LAB)
        diff = cv2.absdiff(lab_before, lab_after)
        dist = np.sqrt(np.sum(np.square(diff.astype(np.float32)), axis=2)).astype(np.uint8)

        _, mask = cv2.threshold(dist, COLOR_DIFF_THRESH, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, morph_kernel)
        mask = cv2.dilate(mask, None, iterations=MORPH_DILATE_ITER)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if save_patches:
            os.makedirs("data/photos/test/patch", exist_ok=True)

        patches_b64 = []
        i = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            if w < PATCH_MIN_WIDTH or h < PATCH_MIN_HEIGHT:
                continue
            if w > PATCH_MAX_WIDTH or h > PATCH_MAX_HEIGHT:
                continue

            patch = aligned_after[y:y+h, x:x+w]
            patch_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            if patch_gray.std() < 10:
                continue

            _, buffer = cv2.imencode('.jpg', patch)
            b64 = base64.b64encode(buffer).decode('utf-8')
            patches_b64.append(b64)

            if save_patches:
                with open(f"data/photos/test/patch/patch_{i}.jpg", "wb") as f:
                    f.write(base64.b64decode(b64))

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
        self._camera.take_photo(after_img)
        if os.path.isfile(before_img):
            patches_b64 = self._detect_insect_patches_base64(before_img, after_img, False)
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