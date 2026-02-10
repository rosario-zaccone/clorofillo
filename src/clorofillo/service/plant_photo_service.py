import base64, io, os, re
import cv2, numpy as np, redis, requests
from dotenv import load_dotenv
from PIL import Image
from clorofillo.model.plant_photo import PlantPhoto
from clorofillo.persistence.plant_photo_repository import PlantPhotoRepository

load_dotenv()

COMPARISON_DIR = os.getenv("COMPARISON_DIR", "data/photos/comparison")
SIGHTING_PATCH_DIR = os.getenv("SIGHTING_PATCH_DIR", "data/photos/sighting/patch")
TIMELAPSE_PHOTO_DIR = os.getenv("TIMELAPSE_PHOTO_DIR", "data/photos/timelapse")


class PlantPhotoService:
    def __init__(self, repository: PlantPhotoRepository, camera, api_key=None, api_url=None):
        self._repository = repository
        self.camera = camera
        self._API_URL = api_url or "https://insect.kindwise.com/api/v1/identification"
        self._API_KEY = api_key or os.getenv("API_KEY")

    @property
    def repository(self):
        return self._repository


    def clean_sighting_detect(self, pot_id):
        folder_path = COMPARISON_DIR
        file_path = os.path.join(folder_path, "before_" + str(pot_id) + ".jpg")
        if os.path.exists(file_path):
            os.remove(file_path)

    def _detect_sighting_patches_base64(
        self, 
        before_path, 
        after_path, 
        pot_id,
        timestamp,
        min_area=500,
        max_area=6000,
        max_width=100,
        max_height=100,
        margin=100,        # ignored margin
        padding_extra=150  # extra pattern around the patches
    ):
        """
        Compare two images and identify patches where there are changes (possible invertebrates).
        Returns an array of base64 strings of the “after” patches.
        Saves the patches with a unique ID, ORB alignment, and margin + padding.
        """

        before = cv2.imread(before_path)
        after = cv2.imread(after_path)
        if before is None or after is None:
            raise ValueError("Error while loading images")
        
        before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
        after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
        
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
        diff = cv2.absdiff(after_gray, before_gray)
        _, thresh = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)

        kernel = np.ones((3,3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        thresh = cv2.dilate(thresh, kernel, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        patches_base64 = []
        patch_dir = SIGHTING_PATCH_DIR
        os.makedirs(patch_dir, exist_ok=True)

        max_id = -1
        pattern = re.compile(r"^(\d+)_.*\.jpg$")
        for fname in os.listdir(patch_dir):
            m = pattern.match(fname)
            if m:
                idx = int(m.group(1))
                if idx > max_id:
                    max_id = idx
        patch_id = max_id + 1

        img_h, img_w = after.shape[:2]
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or (max_area is not None and area > max_area):
                continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            if (max_width is not None and w > max_width) or (max_height is not None and h > max_height):
                continue
            
            if (x < margin or y < margin or x+w > img_w - margin or y+h > img_h - margin):
                continue

            pad = padding_extra
            x0 = max(x - pad, 0)
            y0 = max(y - pad, 0)
            x1 = min(x + w + pad, img_w)
            y1 = min(y + h + pad, img_h)

            patch_after = after[y0:y1, x0:x1]
            patch_after_pil = Image.fromarray(cv2.cvtColor(patch_after, cv2.COLOR_BGR2RGB))  
            out_path = os.path.join(patch_dir, f"{patch_id}_{pot_id}_{timestamp}.jpg")
            patch_after_pil.save(out_path, format="JPEG")
            buffered_after = io.BytesIO()
            patch_after_pil.save(buffered_after, format="JPEG")
            base64_after = base64.b64encode(buffered_after.getvalue()).decode("utf-8")

            patches_base64.append(base64_after)
            patch_id += 1

        return patches_base64


    def detect_invertebrate(self, patches_base64):
        response = requests.post(
            self._API_URL,
            params={"details": "url,common_names"},
            headers={"Api-Key": self._API_KEY},
            json={"images": patches_base64},
        )
        if response.status_code == 201:
            invertebrates = []
            ok_response = response.json()
            print(ok_response)
            suggestions = ok_response["result"]["classification"]["suggestions"]
            for suggestion in suggestions:
                invertebrates.append(f"{suggestion['name']} {suggestion['probability']*100:.2f}%")

            return invertebrates
        else:
            raise Exception(
                f"Errore API: status code {response.status_code}, response: {response.text}"
            )


    def sighting_shot(self, pot_id, timestamp):
        before_img = os.path.join(COMPARISON_DIR, f"before_{pot_id}.jpg")
        after_img = os.path.join(COMPARISON_DIR, f"after_{pot_id}.jpg")

        os.makedirs(COMPARISON_DIR, exist_ok=True)

        self.camera.take_photo(after_img)

        if os.path.isfile(before_img):
            patches_b64 = self._detect_sighting_patches_base64(
                before_img, after_img, pot_id, timestamp
            )

            if patches_b64:
                # telegram notify redis
                print("OK")
                r = redis.Redis(host="localhost", port=6379, db=0)
                r.rpush("rasp_to_bot", 4)
                r.close()

            os.remove(before_img)

        os.rename(after_img, before_img)


    def timelapse_shot(self, pot_id, timestamp):
        readable = str(timestamp).replace(" ", "_")
        os.makedirs(TIMELAPSE_PHOTO_DIR, exist_ok=True)

        path = os.path.join(
            TIMELAPSE_PHOTO_DIR,
            f"{pot_id}_{readable}.jpg"
        )

        self.camera.take_photo(path)

        photo = PlantPhoto(timestamp, False, path)
        self._repository.insert(photo.to_orm(pot_id))
        self._repository.session.commit()

    
    async def add_sighting(self, photo_file, pot_id, timestamp, file_path):
        await photo_file.download_to_drive(file_path)
        photo = PlantPhoto(timestamp, True, file_path)
        self._repository.insert(photo.to_orm(pot_id))
        self._repository.session.commit()