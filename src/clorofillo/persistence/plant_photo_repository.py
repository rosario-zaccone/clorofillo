from .orm_models import PlantPhotoORM
from .repository import Repository

class PlantPhotoRepository(Repository):
    def __init__(self, session):
        super().__init__(session, PlantPhotoORM)

    def get_by_id(self, entity_id):
        return self.session.get(self.entity, entity_id)

    def get_all(self):
        return self.session.query(self.entity).all()

    def insert(self, entity):
        self.session.add(entity)

    def remove(self, entity):
        self.session.delete(entity)

    #DEBUG
    def remove_insect_photos(self):
        try:
            insect_photos = self.session.query(self.entity).filter_by(is_insect=True).all()
            for photo in insect_photos:
                self.session.delete(photo)
            self.session.commit()
            return len(insect_photos)
        except Exception as e:
            self.session.rollback()
            print("Error removing insect photos:", e)
            return 0
    
    def remove_timelapse_photos(self):
        try:
            insect_photos = self.session.query(self.entity).filter_by(is_insect=False).all()
            for photo in insect_photos:
                self.session.delete(photo)
            self.session.commit()
            return len(insect_photos)
        except Exception as e:
            self.session.rollback()
            print("Error removing insect photos:", e)
            return 0
