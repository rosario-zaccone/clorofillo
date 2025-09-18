from clorofillo.model.plant_pot import PlantPot, PlantPhoto
from moviepy import ImageSequenceClip
from clorofillo.persistence.plant_pot_repository import PlantPotRepository

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
        photos_filenames = ["data/photos/timelapse/" + photo.path for photo in photos_domain]

        clip = ImageSequenceClip(photos_filenames, fps=fps)
        clip.write_videofile(output_path)
        
    def insect_diary():
        pass

    def add_photo():
        pass
        

    