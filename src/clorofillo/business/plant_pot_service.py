from clorofillo.model.plant_pot import PlantPot, PlantPhoto
from moviepy import ImageSequenceClip
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from time import sleep
from clorofillo.business.utilities import Utilities
import cv2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.units import mm
import os
import re

class PlantPotService:
    def __init__(self, repository: PlantPotRepository):
        self._repository = repository
    
    @property
    def repository(self):
         return self._repository
    
    def timelapse(self, id, date_from, date_to, fps, output_path):
        pot = self._repository.get_by_id(id)
        if pot is None:
            raise Exception("Invalid id")
        if date_to < date_from:
            raise ValueError("date_to cannot be earlier than date_from")
        if fps <= 0:
                raise ValueError("fps must be > 0")
        photos = self._repository.get_photos_by_date_range(pot.id, date_from, date_to)
        photos_domain = [PlantPhoto.from_orm(photo) for photo in photos]
        photos_filenames = [photo.path for photo in photos_domain]

        clip = ImageSequenceClip(photos_filenames, fps=fps)
        clip.write_videofile(output_path)
        

    def insect_diary(self, id):
        pot = PlantPot.from_orm(self._repository.get_by_id(id))
        if pot is None:
            raise Exception("Invalid id")

        photos = pot.get_insect_photos()
        photos_filenames = [photo.path for photo in photos]

        if not photos_filenames:
            raise Exception("No insect photos found for this plant pot.")

        output_path = f"data/diary/{id}_diary.pdf"
        page_width, page_height = A4
        margin = 40

        c = canvas.Canvas(output_path, pagesize=A4)

        # Titolo iniziale
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(colors.darkgreen)
        c.drawCentredString(page_width / 2, page_height - margin, f"🪴 Insect Diary - Pot {id}")
        
        # Spazio iniziale per discesa
        y = page_height - margin - 40

        for i, filepath in enumerate(photos_filenames):
            if y < 150:  # se non c'è abbastanza spazio, nuova pagina
                c.showPage()
                c.setFont("Helvetica-Bold", 24)
                c.setFillColor(colors.darkgreen)
                c.drawCentredString(page_width / 2, page_height - margin, f"🪴 Insect Diary - Pot {id}")
                y = page_height - margin - 40

            filename = os.path.basename(filepath)
            match = re.match(rf"{id}_(.+?)_(\d{{4}})-(\d{{2}})-(\d{{2}})_", filename)
            if match:
                insect_name = match.group(1).replace("_", " ").title()
                date_str = f"{match.group(4)}/{match.group(3)}/{match.group(2)}"
            else:
                insect_name = "Unknown insect"
                date_str = "Unknown date"

            # Draw container
            box_height = 100
            c.setFillColor(colors.whitesmoke)
            c.roundRect(margin, y - box_height, page_width - 2 * margin, box_height, 10, fill=1)

            # Load image
            try:
                img = ImageReader(filepath)
                img_width, img_height = img.getSize()
                scale = min(80 / img_width, 80 / img_height)
                scaled_width = img_width * scale
                scaled_height = img_height * scale
                img_x = margin + 10
                img_y = y - box_height + (box_height - scaled_height) / 2

                c.drawImage(img, img_x, img_y, width=scaled_width, height=scaled_height, mask='auto')

                # Draw text info
                text_x = img_x + scaled_width + 20
                c.setFont("Helvetica-Bold", 14)
                c.setFillColor(colors.black)
                c.drawString(text_x, y - 30, f"{insect_name}")

                c.setFont("Helvetica", 12)
                c.setFillColor(colors.grey)
                c.drawString(text_x, y - 50, f"📅 {date_str}")

            except Exception as e:
                c.setFont("Helvetica", 12)
                c.setFillColor(colors.red)
                c.drawString(margin, y - 30, f"Error loading: {filename}")

            y -= box_height + 20  # spazio tra le schede

        c.save()
        print(f"PDF created: {output_path}")
        return output_path



    def calibrate(self, camera, servo, servo_pin, conf_repo):
        # take photos
        for i in range(0, 181, 10):
            servo.set_servo_pulsewidth(servo_pin, Utilities.angle_to_pulsewidth(i))
            camera.take_photo(f"data/calibration/{i}_.jpg")

        # detection
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        aruco_params = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
        angles = {}
        for i in range(0, 181, 10):
            image_path = f"data/calibration/{i}_.jpg"
            image = cv2.imread(image_path)

            corners, ids, _ = detector.detectMarkers(image)
            if ids is None:
                continue
            
            for marker_corners, marker_id in zip(corners, ids.flatten()):
                if angles.get(marker_id) is not None:
                    continue
                marker_corners = marker_corners.reshape((4, 2))
                top_left, top_right, bottom_right, bottom_left = marker_corners
                cX = int((top_left[0] + bottom_right[0]) / 2.0)
                image_center_x = image.shape[1] // 2
                tolerance = image.shape[1] * 0.1 
                is_centered = abs(cX - image_center_x) <= tolerance
                if is_centered:
                    print(f"ID detected: {marker_id}, angle: {i}")
                    angles[marker_id] = i
        if len(angles) != 3:
            raise Exception("Failed, no enough pot detected")
            return
        for i in range(1, 4):
            pot_orm = self._repository.get_by_id(i)
            pot = PlantPot.from_orm(pot_orm)
            print(i, pot)
            conf_id = pot.configuration.id
            conf = pot.configuration
            conf.position = angles.get(i)
            conf_repo.update(conf_id, conf.to_orm())
            conf_repo.session.commit()
                        


    