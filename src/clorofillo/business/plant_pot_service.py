from clorofillo.model.plant_pot import PlantPot, PlantPhoto
from moviepy import ImageSequenceClip
from clorofillo.persistence.plant_pot_repository import PlantPotRepository
from picamzero import Camera
from time import sleep
from clorofillo.business.utilities import Utilities
from clorofillo.persistence.configuration_repository import ConfigurationRepository
from clorofillo.model.configuration import Configuration
import cv2

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
        
    def insect_diary():
        pass

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
                    print(f"ID rilevato: {marker_id}, angolo: {i}")
                    angles[marker_id] = i
        if len(angles) != 3:
            print("Failed, no enough pot detected")
            return
        for i in range(1, 4):
            pot_orm = self._repository.get_by_id(i)
            pot = PlantPot.from_orm(pot_orm)
            conf_id = pot.configuration.id
            conf = pot.configuration
            conf.position = angles.get(i)
            conf_repo.update(conf_id, conf.to_orm())
            conf_repo.session.commit()

                #logica se fallisce
                        


    