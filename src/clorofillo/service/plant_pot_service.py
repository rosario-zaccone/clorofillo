import os, re
from time import sleep
from PIL import Image, ImageEnhance
import numpy as np
import tempfile
import cv2

import cv2
from moviepy import ImageSequenceClip
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from dotenv import load_dotenv

from clorofillo.model.plant_pot import PlantPhoto, PlantPot
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from clorofillo.service.utilities import Utilities

load_dotenv()

DIARY_DIR = os.getenv("DIARY_DIR", "data/diary")
CALIB_DIR = os.getenv("CALIB_DIR", "data/calibration")


class PlantPotService:
    def __init__(self, repository: PlantPotRepository):
        self._repository = repository
    
    @property
    def repository(self):
         return self._repository
    
    def timelapse(self, id, date_from, date_to, fps, output_path, filter_type="none"):
        pot = self._repository.get_by_id(id)
        if pot is None:
            raise Exception("Invalid id")
        if date_to < date_from:
            raise ValueError("date_to cannot be earlier than date_from")
        if fps <= 0:
            raise ValueError("fps must be > 0")
        
        valid_filters = ["none", "bw", "saturation", "contrast", "white_balance"]
        if filter_type not in valid_filters:
            raise ValueError(f"filter_type must be one of {valid_filters}")
        
        photos = self._repository.get_photos_by_date_range(pot.id, date_from, date_to)
        photos_domain = [PlantPhoto.from_orm(photo) for photo in photos]
        photos_filenames = [photo.path for photo in photos_domain]
        
        # Apply filters
        if filter_type != "none":
            photos_filenames = self._apply_filters(photos_filenames, filter_type)
        
        clip = ImageSequenceClip(photos_filenames, fps=fps)
        clip.write_videofile(output_path)

    def _apply_filters(self, photos_filenames, filter_type):
        temp_dir = tempfile.mkdtemp()
        filtered_filenames = []
        
        for idx, photo_path in enumerate(photos_filenames):
            img = Image.open(photo_path)
            
        
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            if filter_type == "bw":
                img = img.convert("L")  # grayscale
                img = Image.merge("RGB", (img, img, img)) 
            
            elif filter_type == "saturation":
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.5)  # +50% saturation
            
            elif filter_type == "contrast":
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)  # +30% contrast
            
            elif filter_type == "white_balance":
                img = self._auto_white_balance(img)
            
            # Save to temp
            temp_path = os.path.join(temp_dir, f"frame_{idx:06d}.png")
            img.save(temp_path)
            filtered_filenames.append(temp_path)
        
        return filtered_filenames

    def _auto_white_balance(self, img):
        img_np = np.asarray(img).astype(np.float32)
        r = img_np[:, :, 0]
        g = img_np[:, :, 1]
        b = img_np[:, :, 2]
        r_mean = np.mean(r)
        g_mean = np.mean(g)
        b_mean = np.mean(b)
        if r_mean == 0 or g_mean == 0 or b_mean == 0:
            return img
        gray_mean = (r_mean + g_mean + b_mean) / 3.0
        r *= gray_mean / r_mean
        g *= gray_mean / g_mean
        b *= gray_mean / b_mean
        balanced = np.stack([r, g, b], axis=2)
        balanced = np.clip(balanced, 0, 255).astype(np.uint8)
        return Image.fromarray(balanced, mode="RGB")



            

    def sighting_diary(self, id):
        pot = PlantPot.from_orm(self._repository.get_by_id(id))
        if pot is None:
            raise Exception("Invalid id")

        photos = pot.get_sighting_photos()
        photos_filenames = [photo.path for photo in photos]

        if not photos_filenames:
            raise Exception("No sighting photos found for this plant pot.")

        output_path = os.path.join(DIARY_DIR, f"{id}_diary.pdf")

        page_width, page_height = A4
        margin = 40

        c = canvas.Canvas(output_path, pagesize=A4)

        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(colors.darkgreen)
        c.drawCentredString(page_width / 2, page_height - margin, f"🪴 Sighting Diary - Pot {id}")
        y = page_height - margin - 40
        for i, filepath in enumerate(photos_filenames):
            if y < 150:
                c.showPage()
                c.setFont("Helvetica-Bold", 24)
                c.setFillColor(colors.darkgreen)
                c.drawCentredString(page_width / 2, page_height - margin, f"🪴 Sighting Diary - Pot {id}")
                y = page_height - margin - 40

            filename = os.path.basename(filepath)
            match = re.match(rf"{id}_(.+?)_(\d{{4}})-(\d{{2}})-(\d{{2}})_", filename)
            if match:
                sighting_name = match.group(1).replace("_", " ").title()
                date_str = f"{match.group(4)}/{match.group(3)}/{match.group(2)}"
            else:
                sighting_name = "Unknown"
                date_str = "Unknown date"

            box_height = 100
            c.setFillColor(colors.whitesmoke)
            c.roundRect(margin, y - box_height, page_width - 2 * margin, box_height, 10, fill=1)
            try:
                img = ImageReader(filepath)
                img_width, img_height = img.getSize()
                scale = min(80 / img_width, 80 / img_height)
                scaled_width = img_width * scale
                scaled_height = img_height * scale
                img_x = margin + 10
                img_y = y - box_height + (box_height - scaled_height) / 2

                c.drawImage(img, img_x, img_y, width=scaled_width, height=scaled_height, mask='auto')

                text_x = img_x + scaled_width + 20
                c.setFont("Helvetica-Bold", 14)
                c.setFillColor(colors.black)
                c.drawString(text_x, y - 30, f"{sighting_name}")

                c.setFont("Helvetica", 12)
                c.setFillColor(colors.grey)
                c.drawString(text_x, y - 50, f"📅 {date_str}")

            except Exception as e:
                c.setFont("Helvetica", 12)
                c.setFillColor(colors.red)
                c.drawString(margin, y - 30, f"Error loading: {filename}")

            y -= box_height + 20 

        c.save()
        print(f"PDF created: {output_path}")
        return output_path



    def calibrate(self, camera, servo, servo_pin, conf_repo):
        for i in range(0, 161, 10):
            servo.set_servo_pulsewidth(servo_pin, Utilities.angle_to_pulsewidth(i))
            path = os.path.join(CALIB_DIR, f"{i}_.jpg")
            camera.take_photo(path)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise RuntimeError(f"Camera failure at {i}°")

        # detection
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        aruco_params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
        angles = {}
        for i in range(0, 161, 10):
            image_path = os.path.join(CALIB_DIR, f"{i}_.jpg")
            image = cv2.imread(image_path)

            corners, ids, _ = detector.detectMarkers(image)
            if ids is None:
                continue
            
            for marker_corners, marker_id in zip(corners, ids.flatten()):
                if angles.get(marker_id) is not None:
                    continue
                marker_corners = marker_corners.reshape((4, 2))

                cX = int(marker_corners[:, 0].mean())
                cY = int(marker_corners[:, 1].mean())

                image_center_x = image.shape[1] // 2
                image_center_y = image.shape[0] // 2

                tolerance_frac = 0.35
                tol_x = image.shape[1] * tolerance_frac
                tol_y = image.shape[0] * tolerance_frac

                is_centered = (abs(cX - image_center_x) <= tol_x) and (abs(cY - image_center_y) <= tol_y)
                if is_centered:
                    print(f"ID detected: {int(marker_id)}, angle: {i}, center=({cX},{cY}), image_center=({image_center_x},{image_center_y}), tol=({tol_x:.1f},{tol_y:.1f})")
                    angles[marker_id] = i
        expected_ids = {1, 2, 3}
        detected_ids = set(angles.keys())
        missing_ids = expected_ids - detected_ids

        if missing_ids:
            raise Exception(f"Failed, pots not detected: {sorted(missing_ids)}")
        for i in range(1, 4):
            pot_orm = self._repository.get_by_id(i)
            pot = PlantPot.from_orm(pot_orm)
            conf_id = pot.configuration.id
            conf = pot.configuration
            conf.position = angles.get(i)
            conf_repo.update(conf_id, conf.to_orm())
            conf_repo.session.commit()
                        

    